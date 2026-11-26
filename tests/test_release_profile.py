"""Release defaults are model/probe-specific; original evidence and overrides survive."""
import argparse
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import playbook as p
import coverage_batch as b
import openai_profile as profile
from test_probe_browser import inventory_fixture

class ReleaseProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.cfg={'schema_version':1,'garak_python':sys.executable,'evidence_root':str(self.root/'evidence'),
                  'xdg_data_home':str(self.root/'data'),'targets':{'openai-reasoning':dict(profile.TARGET),'local':{'provider':'ollama','model':'synthetic:only','endpoint':'http://127.0.0.1:11434'}}}
        self.inv=inventory_fixture()

    def campaign(self,spec,target=None):
        row=next(r for r in self.inv['probes'] if r['name']==spec)
        return p.probe_catalog.campaign_for(row,target or profile.TARGET,self.inv)

    def test_exactly_three_of_fourteen_cloud_probe_defaults_change(self):
        count=0
        for spec in p.probe_catalog.policy()['probes']:
            result=self.campaign(spec)
            expected=20000 if spec.removeprefix('probes.') in profile.ENCODING_HEADROOM_PROBES else 1500
            self.assertEqual(result['max_completion_tokens'],expected,spec)
            count+=expected==20000
        self.assertEqual(count,3)
        self.assertEqual(len(p.probe_catalog.policy()['probes']),14)

    def test_other_model_retains_1500_in_browser_and_plan(self):
        target=dict(profile.TARGET,model='synthetic-other-model')
        self.assertEqual(self.campaign('probes.encoding.InjectBase64',target)['max_completion_tokens'],1500)
        cfg=copy.deepcopy(self.cfg);cfg['targets']['openai-reasoning']=target
        self.assertEqual(p.plan(cfg,'openai-reasoning','base64-32')['campaign']['max_completion_tokens'],1500)

    def test_existing_campaign_and_browser_agree_without_rewriting_config(self):
        before=copy.deepcopy(self.cfg)
        self.assertEqual(p.plan(self.cfg,'openai-reasoning','base64-32')['campaign']['max_completion_tokens'],20000)
        self.assertEqual(p.plan(self.cfg,'openai-reasoning','dan-wild-32')['campaign']['max_completion_tokens'],1500)
        self.assertEqual(self.cfg,before)

    def test_explicit_cap_including_historical_1500_is_preserved(self):
        c=self.campaign('probes.encoding.InjectBase64')
        for cap in (1500,777,20000):
            c['max_completion_tokens']=cap
            self.assertEqual(p.plan(self.cfg,'openai-reasoning',c)['campaign']['max_completion_tokens'],cap)
        self.assertEqual(c['max_completion_tokens'],20000)

    def test_ollama_generation_settings_unchanged(self):
        c=self.campaign('probes.encoding.InjectBase64',self.cfg['targets']['local'])
        self.assertEqual((c['max_tokens'],c['temperature'],c['seed']),(256,0,42))
        self.assertNotIn('max_completion_tokens',c)

    def test_batch_cli_omission_uses_profile_explicit_value_overrides(self):
        parser=argparse.ArgumentParser();b.add_parsers(parser.add_subparsers(dest='action',required=True))
        args=parser.parse_args(['batch','--config','unused.json','--target','openai-reasoning'])
        self.assertIsNone(args.completion_tokens)
        estimate=lambda cfg,c:{'sampled_prompt_count':c['workload'].get('expected_attempts') or 32,'max_input_units_per_request':250}
        with patch.object(p,'estimate_cloud_workload',side_effect=estimate):
            plan=b.make_plan(self.cfg,args,inventory=self.inv)
            self.assertEqual(len(plan['plans']),14)
            self.assertEqual(sum(x['campaign']['max_completion_tokens']==20000 for x in plan['plans']),3)
            args.completion_tokens=1500
            old=b.make_plan(self.cfg,args,inventory=self.inv)
            self.assertTrue(all(x['campaign']['max_completion_tokens']==1500 for x in old['plans']))

if __name__=='__main__':unittest.main()
