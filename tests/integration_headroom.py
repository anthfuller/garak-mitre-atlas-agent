"""Real Garak/SDK, synthetic 80/96 baseline and 96/96 retest. Network denied."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbook as p
import headroom_retest as h

BOOTSTRAP = '''import sys,json
sys.path.insert(0, RUNNER_ROOT)
def deny(event,args):
    if event in ("socket.connect","socket.connect_ex","socket.getaddrinfo","socket.sendto"):
        raise AssertionError("Offline integration prohibits network")
sys.addaudithook(deny)
import httpx
import openai_worker as w
calls=0
def response(request):
    global calls
    calls+=1
    body=json.loads(request.content)
    gaps={"probes.encoding.InjectAscii85":8,"probes.encoding.InjectBase32":7,"probes.encoding.InjectBase64":1}
    spec=sys.argv[sys.argv.index("--spec")+1]
    gap=body["max_completion_tokens"]==1500 and 2<=calls<=gaps[spec]+1
    if FAIL_RETEST and body["max_completion_tokens"]==20000 and calls==3:
        return httpx.Response(500,json={"error":{"message":"SYNTHETIC retest failure"}})
    content="" if gap else ("OK" if calls==1 else "SYNTHETIC visible answer 📜")
    completion=1500 if gap else (100 if body["max_completion_tokens"]==1500 else 2100) if calls>1 else 5
    reasoning=1500 if gap else (80 if body["max_completion_tokens"]==1500 else 2000) if calls>1 else 0
    return httpx.Response(200,json={"id":"SYNTHETIC","object":"chat.completion","created":1,"model":"gpt-5.6-sol",
        "choices":[{"index":0,"message":{"role":"assistant","content":content},"finish_reason":"length" if gap else "stop"}],
        "usage":{"prompt_tokens":10,"completion_tokens":completion,"total_tokens":completion+10,"completion_tokens_details":{"reasoning_tokens":reasoning}}})
original=w.run
w.run=lambda args,key:original(args,key,test_transport=httpx.MockTransport(response))
raise SystemExit(w.main())
'''


def main(failure=False):
    def deny(event,args):
        if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo','socket.sendto'):
            raise AssertionError('Offline integration prohibits network')
    sys.addaudithook(deny)
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        cfg={'schema_version':1,'garak_python':sys.executable,'evidence_root':str(root/'evidence'),
             'xdg_data_home':str(root/'data'),'targets':{'openai-reasoning':dict(p.openai_profile.TARGET)}}
        script=root/'mock_worker.py'
        script.write_text(BOOTSTRAP.replace('RUNNER_ROOT',repr(str(p.ROOT))).replace('FAIL_RETEST',repr(failure)),encoding='utf-8')
        real=p.command
        def command(*args):
            result=real(*args);result[1]=str(script);return result
        inventory=p.installed_inventory(cfg)
        baseline={'baselines':[]}
        key='sk-DUMMY-HEADROOM-NOT-A-REAL-KEY'
        output=io.StringIO()
        with patch.object(p,'command',side_effect=command), contextlib.redirect_stdout(output):
            for spec,count in zip(h.SPECS,(24,25,31)):
                row=next(r for r in inventory['probes'] if r['name']==spec)
                campaign=p.probe_catalog.campaign_for(row,p.openai_profile.TARGET,inventory)
                campaign['pricing']=p.openai_cost.published_rates('gpt-5.6-sol')
                result=p.run_selected(cfg,'openai-reasoning',campaign,session_key=key)
                folder=Path(result['folder'])
                require=result['summary']['detectors'][0]['evaluated']==count
                assert require,(spec,result,output.getvalue())
                baseline['baselines'].append({'probe':spec,'folder':str(folder),'run_id':result['summary']['garak_run_id'],'scorable':count})
            with patch('builtins.input',return_value='RUN'),patch.object(h.openai_profile,'read_session_key',return_value=key):
                code=h.execute(cfg,baseline)
        print(output.getvalue() if code else 'Synthetic baseline and retest finished.')
        assert code==(2 if failure else 0),output.getvalue()
        batch=next(Path(cfg['evidence_root']).glob('*-headroom-*'))
        doc=p.read_json(batch/'comparison.json')
        assert [r['baseline_scorable'] for r in doc['rows']]==[24,25,31]
        if failure:
            receipt=p.read_json(batch/'headroom.json')
            assert receipt['status']=='stopped' and len(receipt['results'])==1,receipt
            assert sum(r['not_attempted'] for r in doc['rows'])==94,doc
            assert all(r['baseline_unchanged'] for r in doc['rows'])
            assert 'No default recommendation' in doc['recommendation']
            print('PASS headroom failure: one compatibility + two synthetic scan requests; HTTP 500 stopped batch; 94 inputs not attempted; partial comparison preserved; no live calls.')
            return
        assert [r['retest_scorable'] for r in doc['rows']]==[32,32,32]
        assert [r['recovered'] for r in doc['rows']]==[8,7,1]
        assert all(r['newly_unscorable']==r['not_attempted']==0 and r['baseline_unchanged'] for r in doc['rows'])
        gaps=[t['retest'] for r in doc['rows'] for t in r['transitions'] if not t['baseline']['scorable']]
        assert len(gaps)==16 and all(g['completion_tokens']==2100 and g['reasoning_tokens']==2000 and g['visible_text'] and g['finish_reason']=='stop' for g in gaps)
        calls=0
        for r in doc['rows']:
            session=p.read_json(Path(r['retest_folder'])/'openai-session.json');calls+=session['http_requests']
            assert (Path(r['retest_folder'])/'atlas_handoff.md').is_file()
        assert calls==99
        # Guard rejection must happen before HTTP, including after compatibility.
        plan=p.read_json(batch/'headroom.json')['plans'][0]
        for index, expected_calls in ((0,0),(1,1)):
            campaign=json.loads(json.dumps(plan['campaign']))
            campaign['headroom_request_guard'][index]['messages']=[{'role':'user','content':'WRONG SAVED INPUT'}]
            with patch.object(p,'command',side_effect=command),contextlib.redirect_stdout(io.StringIO()):
                blocked=p.run_selected(cfg,'openai-reasoning',campaign,session_key=key)
            session=p.read_json(Path(blocked['folder'])/'openai-session.json')
            assert session['http_requests']==expected_calls and session['status']=='failed',session
            assert 'request blocked' in session['error'],session
        for f in root.rglob('*'):
            if f.is_file(): assert key.encode() not in f.read_bytes(),str(f)
        print('PASS headroom: real Garak 0.17.0; 99 synthetic retest requests; exact 96-input matching; 80 -> 96 scorable; 16 paired token/finish records; evidence unchanged; mismatched compatibility/scan inputs blocked before HTTP. No live model calls.')
        print((batch/'comparison.md').read_text(encoding='utf-8'))

if __name__=='__main__': main(failure='failure' in sys.argv[1:])
