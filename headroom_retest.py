"""Opt-in, paired OpenAI encoding diagnostic; does not alter default profiles."""
from __future__ import annotations
import argparse
from collections import defaultdict, deque
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import coverage_batch
import openai_cost
import openai_profile
import playbook as p

SPECS = tuple('probes.encoding.' + n for n in ('InjectAscii85', 'InjectBase32', 'InjectBase64'))
DETECTOR = 'encoding.DecodeMatch'
BASE_CAP = 1500
RETEST_CAP = 20000


def require(condition, message):
    if not condition:
        raise p.PlaybookError(message)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def json_lines(path):
    return [json.loads(s) for s in Path(path).read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def tree_hashes(folder):
    return {str(f.relative_to(folder)): p.sha(f) for f in sorted(folder.rglob('*')) if f.is_file()}


def prompt_messages(prompt):
    if isinstance(prompt, str):
        return [{'role': 'user', 'content': prompt}]
    turns = prompt.get('turns', []) if isinstance(prompt, dict) else []
    require(len(turns) == 1 and turns[0].get('role') == 'user', 'Baseline prompt is not the audited single-user text input.')
    text = p.message_text(turns[0].get('content'))
    require(isinstance(text, str), 'Unsupported native prompt text.')
    return [{'role': 'user', 'content': text}]


def snapshot(folder, *, baseline=False):
    """Join native scoring to audited HTTP by exact input plus occurrence, never UUID across runs."""
    folder = Path(folder)
    manifest = p.read_json(folder / 'manifest.json')
    fresh = deepcopy(manifest)
    fresh['transport_coverage_gaps'] = p.openai_worker.quality_gaps(folder)
    summary, observations = p.analyze(folder / 'scan.report.jsonl', fresh)
    rows = json_lines(folder / 'openai-transport.jsonl') if (folder / 'openai-transport.jsonl').is_file() else []
    requests = [r for r in rows if r.get('entry_type') == 'request']
    responses = {r['sequence']: r for r in rows if r.get('entry_type') == 'response'}
    require(len(responses) == len([r for r in rows if r.get('entry_type') == 'response']), 'Duplicate HTTP response sequence.')
    require(len({r['sequence'] for r in requests}) == len(requests), 'Duplicate HTTP request sequence.')
    buckets = defaultdict(deque)
    for ob in observations:
        require(ob['output_index'] == 0, 'Only one output per input is comparable in this diagnostic.')
        buckets[fingerprint(prompt_messages(ob['prompt']))].append(ob)
    paired, occurrences = [], defaultdict(int)
    for request in requests:
        if request['stage'] != 'scan':
            continue
        key = fingerprint(request['body']['messages'])
        occurrences[key] += 1
        ob = buckets[key].popleft() if buckets[key] else None
        response = responses.get(request['sequence'])
        body = response.get('body', {}) if response else {}
        choices = body.get('choices') or []
        choice = choices[0] if len(choices) == 1 else {}
        text = choice.get('message', {}).get('content')
        visible = isinstance(text, str) and bool(text.strip())
        if ob is not None and response is not None and len(choices) == 1:
            native_text = p.message_text(ob['output'])
            require(native_text == text or (not native_text and not text), 'Native output does not match its HTTP response; pairing rejected.')
        disposition = ob['detector_results'].get(DETECTOR, {}).get('disposition') if ob else None
        require(not ob or set(ob['detector_results']) <= {DETECTOR}, 'Unexpected detector in native evidence.')
        usage = body.get('usage') or {}
        paired.append({'input_sha256': key, 'occurrence': occurrences[key], 'sequence': request['sequence'],
            'attempt_id': ob['attempt_id'] if ob else None, 'scorable': disposition in ('flagged', 'not_flagged'),
            'detector_disposition': disposition, 'visible_text': visible if response else None,
            'finish_reason': choice.get('finish_reason'), 'completion_tokens': usage.get('completion_tokens'),
            'reasoning_tokens': (usage.get('completion_tokens_details') or {}).get('reasoning_tokens'),
            'response_model': body.get('model'), 'system_fingerprint': body.get('system_fingerprint'),
            'http_status': response.get('http_status') if response else None,
            'http_elapsed_seconds': response.get('elapsed_seconds') if response else None})
    require(not any(buckets.values()), 'Native attempts have no matching HTTP request.')
    cost = p.read_json(folder / 'openai-cost.json') if (folder / 'openai-cost.json').is_file() else {}
    if baseline:
        audited = coverage_batch.read_run(folder)
        require(not audited['integrity_warnings'], 'Baseline evidence reconciliation failed: ' + '; '.join(audited['integrity_warnings']))
        require(summary['execution_status'] in ('completed', 'complete_with_gaps'), 'Baseline did not finish.')
        require(len(paired) == 32 and len(requests) == 33 and len(responses) == 33, 'Baseline must have exactly 32 scan requests and one compatibility request, all with responses.')
        require(requests[0]['stage'] == 'compatibility' and all(r['stage'] == 'scan' for r in requests[1:]), 'Baseline request stages differ.')
        require(all(r['http_status'] == 200 and r['attempt_id'] for r in paired), 'Baseline contains an unpaired or failed request.')
        require(sum(x['scorable'] for x in paired) == sum(x['evaluated'] for x in summary['detectors']), 'Baseline scorable counts disagree.')
    return {'folder': str(folder), 'manifest': manifest, 'summary': summary, 'requests': requests,
            'paired': paired, 'cost': cost, 'hashes': tree_hashes(folder)}


def prepare(cfg, baseline_config, batch_folder):
    entries = baseline_config['baselines']
    require(len(entries) == 3 and [x['probe'] for x in entries] == list(SPECS), 'This diagnostic requires exactly Ascii85, Base32, Base64 in that order.')
    items = []
    for entry in entries:
        folder = Path(entry['folder'])
        require(folder.is_absolute() and folder.is_dir(), 'Baseline folder missing: ' + str(folder))
        for name, digest in entry.get('sha256', {}).items():
            require(Path(name).name == name and p.sha(folder / name) == digest, 'Pinned baseline hash mismatch: ' + name)
        base = snapshot(folder, baseline=True)
        m = base['manifest']
        require(base['summary']['garak_run_id'] == entry['run_id'], 'Wrong baseline run ID.')
        require(m['target'] == openai_profile.TARGET, 'Baseline must use the recorded OpenAI gpt-5.6-sol profile.')
        spec = m['campaign']['spec']
        require(spec.removeprefix('probes.') == entry['probe'].removeprefix('probes.'), 'Wrong baseline probe.')
        require(m['campaign']['detector'].removeprefix('detectors.') == DETECTOR, 'Wrong baseline detector.')
        require(sum(x['scorable'] for x in base['paired']) == entry['scorable'], 'Baseline count differs from the selected experiment.')
        for request in base['requests']:
            body = request['body']
            require(set(body) == {'model', 'messages', 'max_completion_tokens'} and body['model'] == m['target']['model'] and body['max_completion_tokens'] == BASE_CAP, 'Baseline request parameters differ from the 1500-token experiment.')
        campaign = deepcopy(m['campaign'])
        require(campaign['seed'] == 42 and campaign['prompt_cap'] == 32 and campaign['wall_time_seconds'] == 1800, 'Baseline sampling or wall-time differs from this diagnostic.')
        require(campaign['workload'].get('http_request_limit') is None and not campaign.get('spending_alert_usd'), 'Baseline has optional controls requiring explicit reconciliation.')
        campaign['max_completion_tokens'] = RETEST_CAP
        campaign.setdefault('catalog_selection', {'name': entry['probe'], 'source': 'saved baseline'})
        campaign['spec'] = entry['probe']
        campaign['headroom_request_guard'] = [r['body'] | {'max_completion_tokens': RETEST_CAP} for r in base['requests']]
        campaign['headroom_baseline'] = {'run_id': entry['run_id'], 'folder': str(folder), 'source_sha256': base['hashes'],
            'change': 'Only max_completion_tokens changes from 1500 to 20000. Diagnostic, not a new default.'}
        target_name = m.get('target_profile', openai_profile.NAME)
        require(openai_profile.targets(cfg).get(target_name) == m['target'], 'Configured target differs from baseline.')
        target, campaign = p.select(cfg, target_name, campaign)
        expected = deepcopy(m['resolved_garak_config'])
        expected['plugins']['generators']['openai']['OpenAIReasoningGenerator']['max_completion_tokens'] = RETEST_CAP
        require(p.garak_config(target, campaign) == expected, 'Effective configuration would change beyond the token cap.')
        estimate = p.estimate_cloud_workload(cfg, campaign)
        require(estimate is not None and estimate.get('scan_messages') == [r['body']['messages'] for r in base['requests'][1:]], 'Installed probe would generate different inputs/order. No paid call made; saved prompts were not replaced.')
        campaign['input_estimate'] = estimate
        campaign['pricing'] = openai_cost.published_rates(target['model'])
        inspection = batch_folder / ('preflight-' + entry['probe'].split('.')[-1])
        inspection.mkdir()
        p.preflight(cfg, target_name, campaign, inspection)
        old_install = p.read_json(folder / 'installation.json')
        new_install = p.read_json(inspection / 'installation.json')
        require(old_install['packages'] == new_install['packages'], 'Installed package versions differ from baseline; no paid call made.')
        require(all(new_install['source_sha256'].get(n) == h for n, h in old_install['source_sha256'].items()), 'Installed scanner source differs from baseline.')
        items.append({'probe': entry['probe'], 'baseline': base, 'campaign': campaign, 'target_profile': target_name})
    require(sum(x['scorable'] for item in items for x in item['baseline']['paired']) == 80, 'Expected original 80/96 scorable responses.')
    return items


def review(items):
    print('\nOpenAI-only paired diagnostic: max_completion_tokens 1500 -> 20000 (reasoning + visible).')
    print('Model: gpt-5.6-sol | detector: encoding.DecodeMatch | unchanged 96 exact inputs/order.')
    print('Sampling seed 42; one generation; sequential; generation temperature/seed and reasoning effort still not sent.')
    print('Existing time limits preserved: 120s per HTTP request; 1800s per probe. No automatic retries.')
    totals = []
    for item in items:
        estimate = openai_cost.estimate(item['campaign'])
        print(f"{item['probe']}: 32 scan prompts + 1 compatibility request; baseline {sum(x['scorable'] for x in item['baseline']['paired'])}/32 scorable.")
        p.show_cloud_cost(item['campaign'], openai_profile.TARGET)
        totals.append(Decimal(estimate['estimated_usd']) if estimate else None)
    total = sum(totals) if all(x is not None for x in totals) else None
    print('Planned requests: 99 (96 tests + 3 compatibility checks). No Ollama/ATLAS/Kumu/Chroma calls.')
    print('Estimated total: ' + (f'${total:.6f} USD; planning estimate, not a bill or dollar cap.' if total is not None else 'Estimate unavailable. P lets you enter rates; RUN remains available.'))
    if total is not None and total >= 100:
        print('ATTENTION: Estimated total reaches or exceeds $100. Review this amount before RUN.')
    print('One RUN starts all three probes. Saved defaults and original evidence remain unchanged.')
    return total


def compare_pair(base, retest):
    new = {(x['input_sha256'], x['occurrence']): x for x in retest['paired']} if retest else {}
    require(not retest or len(new) == len(retest['paired']), 'Duplicate retest input occurrence.')
    old_keys = {(x['input_sha256'], x['occurrence']) for x in base['paired']}
    require(set(new) <= old_keys, 'Retest contains inputs not present in baseline.')
    transitions = []
    for old in base['paired']:
        result = new.get((old['input_sha256'], old['occurrence']))
        transitions.append({'baseline': old, 'retest': result})
    return {'baseline_scorable': sum(x['scorable'] for x in base['paired']),
        'retest_scorable': sum(x['scorable'] for x in new.values()),
        'recovered': sum(not x['baseline']['scorable'] and x['retest'] is not None and x['retest']['scorable'] for x in transitions),
        'newly_unscorable': sum(x['baseline']['scorable'] and x['retest'] is not None and not x['retest']['scorable'] for x in transitions),
        'not_attempted': sum(x['retest'] is None for x in transitions),
        'transitions': transitions}


def recommendation(rows):
    scored = sum(r['retest_scorable'] for r in rows)
    missing = sum(r['not_attempted'] for r in rows)
    if missing or any(r.get('retest_status', 'completed') not in ('completed', 'complete_with_gaps') or not r.get('baseline_unchanged', True) for r in rows):
        return 'No default recommendation: retest is incomplete; unattempted inputs are not failures or passes.'
    if scored == 96:
        return ('Recommend 20000 as a provisional tested allowance for this model and these three probes. '
                'All 96 inputs were scorable in this retest. A smaller allowance inferred from token usage is not validated. '
                'Do not change the other 11 probe defaults from this experiment alone.')
    return ('Do not adopt a universal default from this result. The 20000-token retest still has unscorable responses; '
            'review their finish reasons, errors and usage before another change. No automatic rerun.')


def build_comparison(items, results):
    rows = []
    for item in items:
        base = item['baseline']
        result = next((x for x in results if x['probe'] == item['probe']), None)
        retest = snapshot(result['folder']) if result else None
        if retest:
            require(retest['manifest']['resolved_garak_config'] == p.garak_config(retest['manifest']['target'], item['campaign']), 'Retest settings differ from reviewed plan.')
            require([r['body'] for r in retest['requests']] == item['campaign']['headroom_request_guard'][:len(retest['requests'])], 'Retest HTTP inputs/parameters differ from baseline.')
        row = compare_pair(base, retest)
        row.update(probe=item['probe'], baseline_run_id=base['summary']['garak_run_id'], baseline_folder=base['folder'],
            retest_run_id=retest['summary'].get('garak_run_id') if retest else None,
            retest_folder=retest['folder'] if retest else None,
            baseline_status=base['summary']['execution_status'], retest_status=retest['summary']['execution_status'] if retest else 'not_attempted',
            baseline_cost=base['cost'], retest_cost=retest['cost'] if retest else {},
            baseline_elapsed_seconds=base['manifest'].get('elapsed_seconds'),
            retest_elapsed_seconds=retest['manifest'].get('elapsed_seconds') if retest else None,
            retest_coverage_gaps=retest['summary'].get('coverage_gaps', []) if retest else [],
            baseline_unchanged=tree_hashes(Path(base['folder'])) == base['hashes'])
        rows.append(row)
    return {'rows': rows, 'recommendation': recommendation(rows),
        'limitations': ['Single stochastic retest, not causal proof or broad resistance evidence.',
            'Scorable means the detector had valid output and a numeric score; flags require analyst review.',
            'Completion tokens include reasoning; missing usage remains unknown, never zero.',
            'Time limits are unchanged; model aliases and provider defaults can change remotely.',
            'No default profile was modified.']}


def write_comparison(folder, comparison):
    p.write_json(folder / 'comparison.json', comparison)
    rows = comparison['rows']
    fields = ['baseline_scorable', 'retest_scorable', 'recovered', 'newly_unscorable', 'not_attempted']
    text = ['# OpenAI headroom diagnostic', '',
        '| Probe | Scorable at 1500 | Scorable at 20000 | Recovered gaps | Newly unscorable | Not attempted | Retest execution |',
        '|---|---:|---:|---:|---:|---:|---|']
    for r in rows:
        text.append('| ' + r['probe'].split('.')[-1] + ' | ' + ' | '.join(str(r[k]) for k in fields) + ' | ' + r['retest_status'] + ' |')
    text += ['| Overall | ' + ' | '.join(str(sum(r[k] for r in rows)) for k in fields) + ' | See individual statuses |', '',
        'Scorable responses are counted independently from native Garak evidence, not its headline attack-success rate.', '',
        '## Original 16 gaps', '',
        '| Probe / baseline attempt | Retest attempt / HTTP sequence | Completion tokens | Reasoning tokens | Visible text | Finish reason | Scorable |',
        '|---|---|---:|---:|---|---|---|']
    for r in rows:
        for pair in r['transitions']:
            if pair['baseline']['scorable']:
                continue
            new = pair['retest'] or {}
            values = [r['probe'].split('.')[-1] + ' / ' + str(pair['baseline']['attempt_id']),
                f"{new.get('attempt_id', 'not attempted')} / {new.get('sequence', 'n/a')}",
                new.get('completion_tokens'), new.get('reasoning_tokens'), new.get('visible_text'), new.get('finish_reason'), new.get('scorable')]
            text.append('| ' + ' | '.join('unknown' if v is None else str(v) for v in values) + ' |')
    text += ['', '## Usage and elapsed time', '',
        '| Probe | Baseline usage USD | Retest usage USD | Retest missing usage | Baseline seconds | Retest seconds |',
        '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        vals = [r['probe'].split('.')[-1], r['baseline_cost'].get('estimated_reported_usage_usd'), r['retest_cost'].get('estimated_reported_usage_usd'),
                r['retest_cost'].get('missing_usage_responses'), r['baseline_elapsed_seconds'], r['retest_elapsed_seconds']]
        text.append('| ' + ' | '.join('unknown' if v is None else str(v) for v in vals) + ' |')
    def total(cost_key):
        values = [r[cost_key].get('estimated_reported_usage_usd') for r in rows]
        return str(sum(Decimal(v) for v in values)) if all(v is not None for v in values) else 'unknown (see partial costs above)'
    text += ['', f"Overall usage-based estimates: baseline ${total('baseline_cost')}; retest ${total('retest_cost')}.",
        'Includes compatibility checks and all reported request usage; not an invoice. Per-run rates and usage are retained in comparison.json.',
        'Where usage is missing, the displayed cost is a partial estimate, not a zero-cost response. Reasoning tokens are included in completion tokens, not charged a second time.']
    for side in ('baseline', 'retest'):
        elapsed = [r[side + '_elapsed_seconds'] for r in rows]
        total_seconds = round(sum(elapsed), 3) if all(isinstance(x, (int, float)) for x in elapsed) else 'unknown'
        text += [f'Overall {side} scan elapsed seconds (including compatibility): {total_seconds}.']
    text += ['', '## Retest token consumption', '', '| Scope | Completion values reported | Median | P95 | Maximum |', '|---|---:|---:|---:|---:|']
    scopes = [(r['probe'].split('.')[-1], r['transitions']) for r in rows]
    scopes.append(('Overall', [t for r in rows for t in r['transitions']]))
    for label, pairs in scopes:
        values = sorted(t['retest']['completion_tokens'] for t in pairs if t['retest'] and type(t['retest'].get('completion_tokens')) is int)
        n = len(values)
        stats = [(values[(n-1)//2] + values[n//2]) / 2, values[math.ceil(.95*n)-1], values[-1]] if n else ['unknown'] * 3
        text += ['| ' + label + ' | ' + str(n) + ' | ' + ' | '.join(str(x) for x in stats) + ' |']
    text += ['', 'Token statistics cover scan responses only; compatibility usage is included in costs above. P95 uses the nearest-rank method.',
        '', '## Recommendation', '', comparison['recommendation'], '', '## Evidence and limitations', '']
    for r in rows:
        text += [f"- {r['probe']}: baseline {r['baseline_run_id']} at `{r['baseline_folder']}`; retest {r['retest_run_id']} at `{r['retest_folder']}`.",
                 f"  Original evidence unchanged: {r['baseline_unchanged']}. Coverage gaps: {json.dumps(r['retest_coverage_gaps'], ensure_ascii=False)}"]
    text += [''] + ['- ' + s for s in comparison['limitations']]
    (folder / 'comparison.md').write_text('\n'.join(text) + '\n', encoding='utf-8')


def execute(cfg, baseline_config):
    folder = p.new_folder(cfg, 'headroom')
    receipt = {'status': 'preparing', 'started_at': p.now(), 'retest_cap': RETEST_CAP,
               'baseline_cap': BASE_CAP, 'planned_requests': 99, 'results': [],
               'runner_version': p.VERSION, 'script_sha256': p.sha(Path(__file__)), 'baseline_config': baseline_config}
    p.write_json(folder / 'headroom.json', receipt)
    items = []
    started = time.monotonic()
    try:
        items = prepare(cfg, baseline_config, folder)
        receipt['plans'] = [{'probe': x['probe'], 'target_profile': x['target_profile'], 'campaign': x['campaign']} for x in items]
        while True:
            review(items)
            p.write_json(folder / 'headroom.json', receipt)
            answer = input('RUN: Start diagnostic | P: Enter rates | Enter: Cancel: ').strip()
            if answer == 'P':
                campaign = {}
                p.edit_cloud_controls(campaign, 'p', openai_profile.TARGET['model'])
                for item in items:
                    item['campaign']['pricing'] = deepcopy(campaign['pricing'])
                continue
            if answer != 'RUN':
                receipt['status'] = 'cancelled'
                return 0
            break
        key = openai_profile.read_session_key()
        if not key:
            receipt['status'] = 'cancelled'
            return 0
        # Recheck evidence after confirmation; no paid call if it changed while review was open.
        require(all(tree_hashes(Path(x['baseline']['folder'])) == x['baseline']['hashes'] for x in items), 'Baseline changed after review; no scan started.')
        receipt['status'] = 'running'
        p.write_json(folder / 'headroom.json', receipt)
        try:
            for item in items:
                result = p.run_selected(cfg, item['target_profile'], item['campaign'], interactive=False, batch_id=folder.name, session_key=key)
                receipt['results'].append({'probe': item['probe'], 'folder': str(result['folder'])})
                p.write_json(folder / 'headroom.json', receipt)
                stop = coverage_batch.stop_reason(result)
                if stop:
                    receipt.update(status='stopped', reason=stop)
                    break
            else:
                receipt['status'] = 'finished'
        finally:
            key = None
        comparison = build_comparison(items, receipt['results'])
        write_comparison(folder, comparison)
        require(all(r['baseline_unchanged'] for r in comparison['rows']), 'Original evidence preservation check failed.')
        print('Comparison: ' + str(folder / 'comparison.md'))
        print('Machine-readable comparison: ' + str(folder / 'comparison.json'))
        print(comparison['recommendation'])
        return 0 if receipt['status'] == 'finished' else 2
    except (EOFError, KeyboardInterrupt):
        receipt['status'] = 'cancelled'
        return 2
    except Exception as exc:
        receipt.update(status='failed', error=type(exc).__name__ + ': ' + str(exc))
        print('Diagnostic stopped: ' + receipt['error'])
        return 2
    finally:
        receipt.update(ended_at=p.now(), elapsed_seconds=round(time.monotonic() - started, 3))
        if items:
            receipt['original_evidence_unchanged'] = all(tree_hashes(Path(x['baseline']['folder'])) == x['baseline']['hashes'] for x in items)
        p.write_json(folder / 'headroom.json', receipt)
        p.checksums(folder)
        print('Diagnostic receipt: ' + str(folder / 'headroom.json'))
        print('No defaults changed. Original scans retained. No automatic rerun.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--baselines', type=Path, required=True)
    args = parser.parse_args()
    return execute(p.load_config(args.config), p.read_json(args.baselines))


if __name__ == '__main__':
    raise SystemExit(main())
