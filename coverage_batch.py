"""Batch the existing reviewed scanner; index every installed probe without enabling it.

No provider request occurs before RUN. Source evidence is read only. Live results
remain observations; neither a flag nor a clean execution proves security.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
import argparse
import csv
import json
from pathlib import Path
import sys

import openai_cost
import openai_profile
import probe_catalog


def runner():
    # When playbook.py is executed as a script, reuse that module's state.
    main = sys.modules.get("__main__")
    if main and getattr(main, "run_selected", None):
        return main
    import playbook
    return playbook


def add_parsers(sub):
    for action in ("coverage", "batch"):
        p = sub.add_parser(action, help="Collect saved evidence and requirements for every installed probe" if action == "coverage" else "Review and run missing enabled probe/model pairs in one batch")
        p.add_argument("--config", required=True, type=Path)
        p.add_argument("--target", action="append", help="Named target; repeat to choose several. Default: all configured targets, including the existing OpenAI profile.")
        if action == "batch":
            p.add_argument("--completion-tokens", type=int, default=None,
                           help="Override the model/probe-specific OpenAI allowance. Omit to use the release profile (20000 for three tested encoding probes on gpt-5.6-sol, otherwise 1500).")
            p.add_argument("--request-cap", type=int, help="Optional per-run cap including compatibility; off by default.")
            p.add_argument("--spending-alert", help="Optional per-run USD alert; off by default.")
            p.add_argument("--retry-failed", action="store_true", help="Include pairs with only failed/unscored runs. Scored evidence is always credited; no automatic retry of gaps.")
            p.add_argument("--probe", action="append", help="Restrict this batch to exact enabled IDs; repeat as needed.")


def requirements(row, supported, reason):
    name, info = row["name"], row["metadata"]
    family = name.split(".")[1]
    params = info.get("DEFAULT_PARAMS") or {}
    needs = []
    if not supported:
        needs.append(reason)
    if set(info.get("modality", {}).get("in", [])) != {"text"}:
        needs.append("Configure an input path and model supporting " + ", ".join(info.get("modality", {}).get("in", [])) + "; current runner is text chat.")
    if info.get("extra_dependency_names"):
        needs.append("Check/install declared dependencies in the appropriate environment: " + ", ".join(info["extra_dependency_names"]))
    auxiliary = {k: v for k, v in params.items() if k.endswith("_model_type") and v}
    if auxiliary:
        needs.append("Configure/budget auxiliary models separately: " + json.dumps(auxiliary, sort_keys=True))
    if params.get("max_calls_per_conv"):
        needs.append("Review iterative request bound: max_calls_per_conv=" + str(params["max_calls_per_conv"]) + "; prompt cap alone is not a request count.")
    if family == "promptinject":
        needs.append("Source changes generator parameters per attempt; Full variants disable pruning. Add compatible parameter and workload handling before enabling.")
    if name == "probes.suffix.GCG":
        needs.append("Source requires HuggingFace Pipeline, not either configured API chat adapter; a different interface or explicit exception is required.")
    if name == "probes.suffix.BEAST":
        needs.append("Source needs model/tokenizer access and a chat template; API-only adapters do not supply these. Different interface or explicit exception required.")
    if family == "agent_breaker":
        needs.append("Requires agent/tool configuration and an agentic target. Bare-model replies do not establish tool side effects.")
    if family in ("web_injection", "exploitation"):
        needs.append("Output screening alone cannot demonstrate downstream rendering, execution or exfiltration.")
    if family == "test":
        needs.append("Harness diagnostic, not a security result.")
    if family == "fileformats":
        needs.append("Source downloads HuggingFace files; review file output handling, resource limits and detector dependencies before execution.")
    if name.endswith("Full"):
        needs.append("Full variant: validate source-specific pruning behavior and actual workload; do not assume the prompt cap applies.")
    if not supported and info.get("primary_detector"):
        needs.append("Validate primary detector " + info["primary_detector"] + " and its data/model dependencies; successful prompt construction alone is insufficient.")
    if not supported:
        needs.append("Live compatibility UNKNOWN. These are implementation requirements, not observed execution failures or approved exceptions.")
    return needs


def transport_diagnostics(folder):
    """Summarize saved transport outcomes without publishing request/response text."""
    p = runner()
    result = {"http_statuses": {}, "finish_reasons": {}, "scan_response_issues": [], "errors": []}
    local = (folder / "ollama-transport.jsonl").is_file()
    path = folder / ("ollama-transport.jsonl" if local else "openai-transport.jsonl")
    if not path.is_file():
        return result
    http, finishes = Counter(), Counter()
    try:
        with path.open(encoding="utf-8-sig") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("entry_type") == "transport_error":
                    result["errors"].append({"sequence": row.get("sequence"), "type": row.get("error_type")})
                if row.get("entry_type") != "response":
                    continue
                http[str(row.get("http_status"))] += 1
                if row.get("stage") != "scan":
                    continue
                body = row.get("body") or {}
                if local:
                    if row.get("http_status") != 200:
                        result["errors"].append({"sequence": row.get("sequence"), "type": "HTTPError", "http_status": row.get("http_status"), "message": "Full error body retained in ollama-transport.jsonl."})
                    elif isinstance(body, dict):
                        finishes[str(body.get("done_reason"))] += 1
                    continue
                choices = body.get("choices") or []
                for choice in choices:
                    reason = choice.get("finish_reason")
                    finishes[str(reason)] += 1
                    message = choice.get("message") or {}
                    content = message.get("content")
                    nonempty = isinstance(content, str) and bool(content.strip())
                    if reason != "stop" or not nonempty:
                        usage = body.get("usage") or {}
                        result["scan_response_issues"].append({"sequence": row.get("sequence"), "finish_reason": reason,
                            "nonempty_text": nonempty, "refusal_field_present": bool(message.get("refusal")),
                            "completion_tokens": usage.get("completion_tokens"),
                            "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")})
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        result["errors"].append({"type": type(exc).__name__, "message": "Transport inspection incomplete; raw file retained."})
    result.update(http_statuses=dict(http), finish_reasons=dict(finishes), source_sha256=p.sha(path))
    return result


def read_run(folder):
    p = runner()
    manifest = p.read_json(folder / "manifest.json")
    summary_path = folder / "summary.json"
    # Interrupted older runs may have a manifest but no rendered summary.
    # Keep their identity so only that pair is held; never create an original
    # summary, invent its historical outcome, or discard the evidence folder.
    saved = p.read_json(summary_path) if summary_path.is_file() else None
    target = manifest["target"]
    spec = manifest["campaign"]["spec"]
    spec = spec if spec.startswith("probes.") else "probes." + spec
    report = folder / "scan.report.jsonl"
    fresh_manifest = dict(manifest)
    if target["provider"] == "openai":
        fresh_manifest["transport_coverage_gaps"] = p.openai_worker.quality_gaps(folder)
    elif manifest.get("ollama_transport_policy"):
        import ollama_worker
        fresh_manifest["transport_coverage_gaps"] = ollama_worker.quality_gaps(folder)
    computed, _ = p.analyze(report, fresh_manifest)
    hashes = {name: p.sha(folder / name) for name in
              ("manifest.json", "summary.json", "scan.report.jsonl", "openai-session.json", "openai-transport.jsonl", "openai-cost.json", "ollama-session.json", "ollama-transport.jsonl")
              if (folder / name).is_file()}
    warnings = [] if saved is not None else ["Saved summary.json is missing; historical outcome is unverified. Original files retained."]
    if (folder / "checksums.json").is_file():
        recorded = p.read_json(folder / "checksums.json")
        warnings += ["Source hash differs from saved checksums: " + n for n, h in hashes.items() if recorded.get(n) != h]
    else:
        warnings.append("Original checksums missing; evidence integrity not independently established.")
    if saved is not None and saved.get("report_sha256") and hashes.get("scan.report.jsonl") != saved["report_sha256"]:
        warnings.append("Native report does not match the saved summary hash.")
    for field in ("garak_run_id", "execution_status", "attempts", "valid_response_count", "flagged_response_count", "detectors"):
        if saved is not None and saved.get(field) != computed.get(field):
            warnings.append("Saved and current analysis differ: " + field)
    usable = bool(report.is_file() and computed.get("valid_response_count", 0) > 0 and computed.get("detectors") and not warnings)
    return {"provider": target["provider"], "model": target["model"], "endpoint": target["endpoint"], "probe_id": spec,
            "run_id": saved.get("garak_run_id") if saved is not None else computed.get("garak_run_id"), "runner_run_id": manifest.get("runner_run_id", folder.name),
            "evidence_folder": str(folder), "recorded_summary": saved, "recomputed_summary": computed,
            "saved_summary_available": saved is not None,
            "recorded_settings": manifest.get("resolved_garak_config"), "source_sha256": hashes,
            "integrity_warnings": warnings, "credited_live_evidence": usable,
            "diagnostics": transport_diagnostics(folder),
            "cost": p.read_json(folder / "openai-cost.json") if (folder / "openai-cost.json").is_file() else None}


def collect_history(root):
    history, issues = [], []
    for folder in sorted(Path(root).glob("*-scan-*")):
        if not folder.is_dir():
            continue
        try:
            history.append(read_run(folder))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            issues.append({"evidence_folder": str(folder), "error_type": type(exc).__name__,
                           "source_file": str(exc.filename) if isinstance(exc, OSError) and exc.filename else None,
                           "message": "Could not reconcile this run; not silently credited or overwritten."})
    return history, issues


def build_rows(inventory, targets, history):
    result = []
    for row in sorted(inventory["probes"], key=lambda x: x["name"]):
        for target_name, target in targets.items():
            enabled, reason = probe_catalog.assess(row, target, inventory)
            records = [r for r in history if (r["provider"], r["model"], r["endpoint"], r["probe_id"]) ==
                       (target["provider"], target["model"], target["endpoint"], row["name"])]
            live = [r for r in records if r["credited_live_evidence"]]
            state = "live_evidence" if live else "recorded_failure_or_unverified_evidence" if records else "untested"
            result.append({"probe_id": row["name"], "target_profile": target_name, "target": target,
                "runner_enabled": enabled, "evidence_state": state, "runs": records,
                "requirements": requirements(row, enabled, reason), "registry_metadata": row["metadata"],
                "release_accepted": False})
    return result


def make_plan(cfg, args, inventory=None):
    p = runner()
    targets = openai_profile.targets(cfg)
    chosen = getattr(args, "target", None) or list(targets)
    if len(chosen) != len(set(chosen)) or any(n not in targets for n in chosen):
        raise ValueError("Choose distinct configured target names.")
    targets = {n: targets[n] for n in chosen}
    inventory = inventory if inventory is not None else p.installed_inventory(cfg)
    history, issues = collect_history(cfg["evidence_root"])
    rows = build_rows(inventory, targets, history)
    plans = []
    selected = getattr(args, "probe", None)
    if selected:
        if len(selected) != len(set(selected)) or set(selected) - {r["name"] for r in inventory["probes"]}:
            raise ValueError("Probe selection must contain distinct exact installed probe IDs.")
        unavailable = [r for r in rows if r["probe_id"] in selected and not r["runner_enabled"]]
        if unavailable:
            raise ValueError("Selected probe is unavailable: " + unavailable[0]["probe_id"] + ": " + "; ".join(unavailable[0]["requirements"]))
    if args.action == "batch":
        if args.completion_tokens is not None and not 1 <= args.completion_tokens <= 128000:
            raise ValueError("Completion limit must be 1–128000.")
        if args.request_cap is not None and args.request_cap <= 0:
            raise ValueError("Optional request cap must be positive; omit it for OFF.")
        if args.spending_alert is not None:
            openai_cost.money(args.spending_alert, positive=True)
        by_name = {r["name"]: r for r in inventory["probes"]}
        estimates = {}
        for row in rows:
            if not row["runner_enabled"] or (selected and row["probe_id"] not in selected):
                continue
            if row["evidence_state"] == "live_evidence":
                continue
            if row["runs"] and not args.retry_failed:
                continue
            campaign = probe_catalog.campaign_for(by_name[row["probe_id"]], row["target"], inventory)
            name = row["probe_id"]
            if name not in estimates:
                estimates[name] = p.estimate_cloud_workload(cfg, campaign)
            estimate = estimates[name]
            if estimate is None:
                row["requirements"].append("Offline workload construction failed; excluded from this batch, not proven incompatible.")
                continue
            count = estimate["sampled_prompt_count"]
            if type(count) is not int or not 0 < count <= campaign["prompt_cap"]:
                raise ValueError("Invalid independently constructed workload for " + name)
            # Preserve the original workload contract; actual construction is recorded
            # separately. A cap is not silently converted into an expected count.
            campaign["batch_workload_check"] = estimate
            if row["target"]["provider"] == "openai":
                if args.completion_tokens is not None:
                    campaign["max_completion_tokens"] = args.completion_tokens
                campaign = openai_profile.campaign_settings(campaign, row["target"]["model"])
                campaign["workload"]["planned_http_requests"] = count + 1
                campaign["workload"]["http_request_limit"] = args.request_cap
                campaign["input_estimate"] = estimate
                campaign["pricing"] = openai_cost.published_rates(row["target"]["model"])
                campaign["spending_alert_usd"] = args.spending_alert
            plans.append({"target_profile": row["target_profile"], "target": row["target"], "campaign": campaign,
                          "constructed_prompts": count, "cost_estimate": openai_cost.estimate(campaign) if row["target"]["provider"] == "openai" else None})
    # Local batch first; cloud calls start only within the same approved plan.
    plans.sort(key=lambda x: (x["target"]["provider"] == "openai", x["target_profile"], x["campaign"]["spec"]))
    return {"schema_version": 1, "created_at": p.now(), "runner_version": p.VERSION,
            "component_sha256": {n: p.sha(p.ROOT / n) for n in ("playbook.py", "coverage_batch.py", "openai_worker.py", "ollama_worker.py", "probe-support.json")},
            "inventory": inventory, "targets": targets, "rows": rows, "history_read_errors": issues,
            "plans": plans, "results": [], "status": "planned", "publication": "ON HOLD",
            "scope": "Enabled missing pairs only. Excluded probes remain explicit requirements. Scored existing runs are credited, including gaps; not automatically release-accepted.",
            "original_evidence_policy": "Read only. No old report, summary, manifest, handoff or settings are rewritten."}


def show_plan(document):
    p = runner()
    n = len(document["inventory"]["probes"])
    print(f"\nInstalled inventory: {n} probes. Selected targets: {', '.join(document['targets'])}")
    for target in document["targets"]:
        rows = [r for r in document["rows"] if r["target_profile"] == target]
        print(f"{target}: {sum(r['runner_enabled'] for r in rows)} enabled; {sum(not r['runner_enabled'] for r in rows)} unavailable; "
              f"{sum(r['evidence_state'] == 'live_evidence' for r in rows)} pairs with credited live evidence (gaps retained).")
    print("Prior scored runs will not be repeated. Incomplete/gapped results remain open; exclusion is not a compatibility verdict.")
    for row in document["rows"]:
        for run in row["runs"]:
            if run["recorded_summary"] is None:
                disposition = "Usable evidence exists for this pair; no repeat." if row["evidence_state"] == "live_evidence" else "This pair is held unless retry is explicitly selected."
                print(f"Historical evidence gap: {run['evidence_folder']} / summary.json missing. {disposition}")
    for item in document["plans"]:
        c, t = item["campaign"], item["target"]
        print(f"\n{item['target_profile']} / {t['model']} | {c['spec']} | detector {c['detector']}")
        print(f"Constructed prompts: {item['constructed_prompts']}; cap {c['prompt_cap']}; generations 1; sampling seed {c['seed']}; wall time {c['wall_time_seconds']}s; sequential.")
        if t["provider"] == "openai":
            print(f"max_completion_tokens {c['max_completion_tokens']} (reasoning + visible); temperature/generation seed not sent; reasoning effort API default.")
            print(f"Per-run request cap: {c['workload']['http_request_limit'] or 'OFF'}; auxiliary models: none; one compatibility generation per probe; SDK retries 0.")
            p.show_cloud_cost(c, t)
        else:
            print(f"Temperature {c['temperature']}; generation seed {c['seed']}; max_tokens {c['max_tokens']}; local Ollama only, no auxiliary calls.")
            print("Ollama HTTP errors/timeouts stop immediately with the error saved; no error retries. Empty successful responses retain Garak's bounded retries (up to 3 calls).")
            import ollama_worker
            print(ollama_worker.FILE_WRITE_POLICY)
            print("Transport-policy change: generation settings are unchanged, but this is not an exact reproduction of older error/retry behavior.")
    cloud = [i for i in document["plans"] if i["target"]["provider"] == "openai"]
    total = sum((Decimal(i["cost_estimate"]["estimated_usd"]) for i in cloud if i["cost_estimate"]), Decimal(0))
    print(f"\nBatch: {len(document['plans'])} separate scans; {sum(i['constructed_prompts'] for i in document['plans'])} constructed scan prompts.")
    if cloud:
        print(f"Planned OpenAI requests including compatibility: {sum(i['constructed_prompts'] + 1 for i in cloud)}.")
        print("Batch estimated OpenAI cost: " + (f"${total:.6f}" if all(i["cost_estimate"] for i in cloud) else "Estimate unavailable (some rates/input estimates missing)."))
    print("Per-run completion menus are suppressed; ATLAS prompts are still generated. No ATLAS, Kumu or Chroma calls. No settings are changed automatically.")
    print("Authentication/transport failure, operator stop, or environment/preflight failure stops the batch. Scored gaps are recorded; other probes continue. No automatic reruns after errors.")


def display_summary(run):
    # Display labels only; recorded_summary stays JSON null when unavailable.
    return run["recorded_summary"] if run["recorded_summary"] is not None else {
        "execution_status": "unverified (saved summary.json missing)", "detectors": [], "coverage_gaps": []}


def write_report(folder, document):
    p = runner()
    p.write_json(folder / "batch.json", document)
    grouped = defaultdict(list)
    for row in document["rows"]:
        grouped[row["probe_id"]].append(row)
    columns = ["Probe ID", "Runner enabled?"] + [name + " model, result, evidence" for name in document["targets"]] + ["Known blocker"]
    with (folder / "probe-coverage.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns); writer.writeheader()
        for name, rows in sorted(grouped.items()):
            value = {"Probe ID": name, "Runner enabled?": "; ".join(r["target_profile"] + ": " + str(r["runner_enabled"]) for r in rows),
                     "Known blocker": " | ".join(dict.fromkeys(n for r in rows for n in r["requirements"]))}
            for row in rows:
                records = []
                for run in row["runs"]:
                    s = display_summary(run)
                    detectors = s.get("detectors") or []
                    counts = "; ".join(f"{d['detector']}: evaluated {d['evaluated']}, flags {d['flags']}, unscorable {d['unscorable']}" for d in detectors) or "No detector counts; unscored"
                    records.append(f"{s.get('execution_status')}; {counts}; run {run['run_id'] or 'native UUID unavailable'}; {run['evidence_folder']}" + ("; integrity/reanalysis warning" if run["integrity_warnings"] else ""))
                value[row["target_profile"] + " model, result, evidence"] = row["target"]["model"] + "; " + (" | ".join(records) or "UNTESTED; no live evidence in scanned evidence root")
            writer.writerow(value)
    text = ["# Batch coverage report", "", "Status: " + document["status"], "Publication: ON HOLD", "",
            "Original evidence was read only. Flags are screening observations; gaps are not passes. Existing settings/results are preserved in batch.json.", "",
            "| Target | Enabled | Credited live pairs | Untested pairs | Prior failed/unverified pairs |", "|---|---:|---:|---:|---:|"]
    for target in document["targets"]:
        rows = [r for r in document["rows"] if r["target_profile"] == target]
        text.append(f"| {target} | {sum(r['runner_enabled'] for r in rows)} | {sum(r['evidence_state']=='live_evidence' for r in rows)} | {sum(r['evidence_state']=='untested' for r in rows)} | {sum(r['evidence_state']=='recorded_failure_or_unverified_evidence' for r in rows)} |")
    text += ["", "## Runs requiring review", ""]
    for row in document["rows"]:
        for run in row["runs"]:
            s = display_summary(run)
            if s.get("execution_status") == "completed" and not run["integrity_warnings"]:
                continue
            text += [f"- {row['target_profile']} / {row['probe_id']}: **{s.get('execution_status')}**; evidence: {run['evidence_folder']}",
                     "  - " + " | ".join(s.get("coverage_gaps", []) + run["integrity_warnings"]),
                     "  - Saved transport diagnostics: " + json.dumps(run["diagnostics"], ensure_ascii=False)]
    if document["history_read_errors"]:
        text += ["", "## Evidence read errors", "", json.dumps(document["history_read_errors"], indent=2)]
    (folder / "batch-summary.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    p.checksums(folder)


def stop_reason(result):
    p = runner()
    manifest = result["manifest"]
    folder = Path(result["folder"])
    # Repeat the actionable local error at batch completion, where the operator
    # sees it, rather than only in the earlier scanner console stream.
    if manifest.get("ollama_transport_policy") and (folder / "ollama-session.json").is_file():
        session = p.read_json(folder / "ollama-session.json")
        if session.get("status") == "failed":
            return "Ollama stopped: " + session.get("error", "See ollama-session.json.")
    if manifest.get("process_status") != "exited" or manifest.get("exit_code") != 0:
        return "Scanner did not exit successfully; remaining scans were not started. Inspect its saved status and exit code."
    if manifest["target"]["provider"] == "openai":
        if not (folder / "openai-session.json").is_file():
            return "OpenAI session missing; remaining scans were not started."
        session = p.read_json(folder / "openai-session.json")
        if session.get("status") != "scan_returned":
            return "OpenAI worker stopped: " + session.get("error", "Incomplete worker session; inspect saved evidence.")
    if result["summary"].get("execution_status") not in ("completed", "complete_with_gaps"):
        return "Scan did not produce a completed execution record; remaining scans were not started."
    return None


def dispatch(args, cfg):
    p = runner()
    document = make_plan(cfg, args)
    folder = p.new_folder(cfg, "coverage" if args.action == "coverage" else "batch")
    document["batch_id"] = folder.name
    write_report(folder, document)
    print("Coverage report: " + str(folder / "batch-summary.md"))
    print("Full installed-probe matrix: " + str(folder / "probe-coverage.csv"))
    if args.action == "coverage":
        print("Zero model-generation requests. Original evidence unchanged.")
        return 0
    show_plan(document)
    if not document["plans"]:
        print("No missing enabled pairs selected. See existing gaps/requirements in the report; no scan started.")
        return 0
    if document["history_read_errors"]:
        for issue in document["history_read_errors"]:
            print(f"Unresolved evidence error: {issue['evidence_folder']} | {issue['error_type']} | source: {issue.get('source_file') or 'see batch.json'}")
        raise ValueError("Unresolved evidence errors prevent reliable duplicate avoidance. See the paths above; no scan started.")
    if not sys.stdin.isatty():
        raise ValueError("Batch requires interactive RUN confirmation; no scan started.")
    # Optional rates do not alter targets/settings. Missing pricing is not a ban.
    while True:
        try:
            choice = input("RUN: start this exact batch | P: enter optional OpenAI rates | Enter: cancel: ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = ""
        if choice.lower() != "p":
            break
        try:
            incoming = openai_cost.money(input("Input USD per 1M tokens: "))
            outgoing = openai_cost.money(input("Output USD per 1M tokens: "))
            for item in document["plans"]:
                if item["target"]["provider"] == "openai":
                    item["campaign"]["pricing"] = {"model": item["target"]["model"], "input_usd_per_million": str(incoming),
                        "output_usd_per_million": str(outgoing), "cached_input_usd_per_million": str(incoming),
                        "source": "Operator supplied; not independently verified.", "entered_at": p.now()}
                    item["cost_estimate"] = openai_cost.estimate(item["campaign"])
            write_report(folder, document)
            show_plan(document)
        except ValueError as exc:
            print(str(exc))
    if choice != "RUN":
        document["status"] = "cancelled_before_execution"
        write_report(folder, document)
        print("No scan started.")
        return 0
    key = None
    try:
        if any(i["target"]["provider"] == "openai" for i in document["plans"]):
            key = openai_profile.read_session_key()
            if key is None:
                document["status"] = "cancelled_before_execution"
                return 0
        document["status"] = "running"
        write_report(folder, document)
        for index, item in enumerate(document["plans"], 1):
            print(f"\nBatch {index}/{len(document['plans'])}: {item['target_profile']} / {item['campaign']['spec']}")
            result = p.run_selected(cfg, item["target_profile"], item["campaign"], batch_id=folder.name,
                                    session_key=key if item["target"]["provider"] == "openai" else None, interactive=False)
            document["results"].append({"target_profile": item["target_profile"], "probe_id": item["campaign"]["spec"],
                                        "folder": result["folder"], "execution_status": result["summary"]["execution_status"]})
            history, issues = collect_history(cfg["evidence_root"])
            document["rows"] = build_rows(document["inventory"], document["targets"], history)
            document["history_read_errors"] = issues
            reason = stop_reason(result)
            current = next((r for r in history if r["evidence_folder"] == result["folder"]), None)
            if not reason and (current is None or current["integrity_warnings"]):
                reason = "New run evidence failed reconciliation; remaining scans were not started."
            if reason or issues:
                document["status"] = "stopped"
                document["stop_reason"] = reason or "Could not reconcile evidence after execution."
            write_report(folder, document)
            batch_dirs = {r["folder"] for r in document["results"]}
            costs = [r["cost"] for r in history if r["evidence_folder"] in batch_dirs and r["cost"]]
            amounts = [c["estimated_reported_usage_usd"] for c in costs if c.get("estimated_reported_usage_usd") is not None]
            if costs:
                print("Batch cumulative usage-based estimate: " + (f"${sum(map(Decimal, amounts), Decimal(0)):.6f}" if len(amounts) == len(costs) else "Estimate unavailable") +
                      f"; missing usage responses: {sum(c.get('missing_usage_responses', 0) for c in costs)}.")
            if document["status"] == "stopped":
                print(document["stop_reason"])
                break
        else:
            document["status"] = "execution_finished_review_required"
    except KeyboardInterrupt:
        document["status"] = "interrupted"
        print("Batch stopped. Existing evidence retained; no next scan started.")
    except Exception as exc:
        document["status"] = "failed"
        # Do not persist exception text from a scope holding credentials.
        document["error_type"] = type(exc).__name__
        print("Batch stopped: " + type(exc).__name__ + ". Review the batch record; original evidence retained.")
    finally:
        key = None
        document["ended_at"] = p.now()
        write_report(folder, document)
        print("\nConsolidated report: " + str(folder / "batch-summary.md"))
        print("Full coverage matrix: " + str(folder / "probe-coverage.csv"))
        print("Batch record: " + str(folder / "batch.json"))
    return 0 if document["status"] in ("execution_finished_review_required", "cancelled_before_execution") else 2
