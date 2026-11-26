import contextlib
from copy import deepcopy
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import headroom_retest as h


def attempt(key,scorable,occurrence=1,**extra):
    return dict(input_sha256=key,occurrence=occurrence,scorable=scorable,attempt_id=key,**extra)


class HeadroomTests(unittest.TestCase):
    def test_pair_recovered_lost_and_not_attempted_are_distinct(self):
        base={'paired':[attempt('a',False),attempt('b',True),attempt('c',True)]}
        new={'paired':[attempt('a',True),attempt('b',False)]}
        result=h.compare_pair(base,new)
        self.assertEqual([result[k] for k in ('baseline_scorable','retest_scorable','recovered','newly_unscorable','not_attempted')],[2,1,1,1,1])

    def test_exact_input_occurrence_not_uuid_pairs_duplicate_prompts(self):
        base={'paired':[attempt('same',False,1),attempt('same',True,2)]}
        new={'paired':[attempt('same',True,1),attempt('same',False,2)]}
        self.assertEqual(h.compare_pair(base,new)['recovered'],1)
        self.assertEqual(h.compare_pair(base,new)['newly_unscorable'],1)

    def test_different_retest_inputs_rejected(self):
        with self.assertRaisesRegex(h.p.PlaybookError,'not present'):
            h.compare_pair({'paired':[attempt('a',True)]},{'paired':[attempt('b',True)]})

    def test_absent_retest_is_unknown_not_new_loss(self):
        result=h.compare_pair({'paired':[attempt('a',True)]},None)
        self.assertEqual(result['not_attempted'],1)
        self.assertEqual(result['newly_unscorable'],0)

    def test_prompt_roles_and_exact_unicode_whitespace_preserved(self):
        value='\n 📜 é\n x '
        native={'turns':[{'role':'user','content':{'text':value}}]}
        self.assertEqual(h.prompt_messages(native),[{'role':'user','content':value}])
        self.assertNotEqual(h.fingerprint(h.prompt_messages(native)),h.fingerprint(h.prompt_messages(value.strip())))
        with self.assertRaises(h.p.PlaybookError): h.prompt_messages({'turns':[{'role':'system','content':{'text':value}}]})

    def test_review_99_requests_and_cost_flag_at_100(self):
        items=[{'probe':s,'baseline':{'paired':[]},'campaign':{}} for s in h.SPECS]
        out=io.StringIO()
        with contextlib.redirect_stdout(out),patch.object(h.p,'show_cloud_cost'),patch.object(h.openai_cost,'estimate',return_value={'estimated_usd':'33.333334'}):
            h.review(items)
        self.assertIn('99 (96 tests + 3',out.getvalue())
        self.assertIn('reaches or exceeds $100',out.getvalue())
        out=io.StringIO()
        with contextlib.redirect_stdout(out),patch.object(h.p,'show_cloud_cost'),patch.object(h.openai_cost,'estimate',return_value={'estimated_usd':'13.3'}): h.review(items)
        self.assertNotIn('ATTENTION',out.getvalue())

    def test_unknown_estimate_is_not_zero_and_run_remains_available(self):
        out=io.StringIO()
        items=[{'probe':s,'baseline':{'paired':[]},'campaign':{}} for s in h.SPECS]
        with contextlib.redirect_stdout(out),patch.object(h.p,'show_cloud_cost'),patch.object(h.openai_cost,'estimate',return_value=None):
            self.assertIsNone(h.review(items))
        self.assertIn('Estimate unavailable',out.getvalue())
        self.assertIn('RUN remains available',out.getvalue())

    def test_cancellation_and_prepare_failure_create_receipt_without_key_or_scan(self):
        for failure in (False,True):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                cfg={'evidence_root':temp}
                with patch.object(h,'prepare',side_effect=ValueError('synthetic evidence mismatch') if failure else None,return_value=[]),patch.object(h,'review'),patch('builtins.input',return_value=''),patch.object(h.openai_profile,'read_session_key') as key,patch.object(h.p,'run_selected') as scan,contextlib.redirect_stdout(io.StringIO()):
                    code=h.execute(cfg,{'baselines':[]})
                key.assert_not_called();scan.assert_not_called()
                receipt=h.p.read_json(next(Path(temp).glob('*/headroom.json')))
                self.assertEqual(receipt['status'],'failed' if failure else 'cancelled')
                self.assertEqual(code,2 if failure else 0)

    def test_wrong_scope_rejected_before_snapshot(self):
        with patch.object(h,'snapshot') as read:
            with self.assertRaises(h.p.PlaybookError): h.prepare({}, {'baselines':[]},Path('.'))
        read.assert_not_called()

    def test_no_default_recommendation_for_unattempted(self):
        self.assertIn('No default recommendation',h.recommendation([{'retest_scorable':0,'not_attempted':32}]))
        self.assertIn('provisional',h.recommendation([{'retest_scorable':96,'not_attempted':0}]))
        self.assertIn('still has unscorable',h.recommendation([{'retest_scorable':90,'not_attempted':0}]))

    def test_missing_usage_remains_unknown_in_original_gap_table(self):
        row=h.compare_pair({'paired':[attempt('a',False)]},{'paired':[attempt('a',False,completion_tokens=None,reasoning_tokens=None,visible_text=False,finish_reason='length')]})
        row.update(probe=h.SPECS[0],baseline_run_id='old',retest_run_id='new',baseline_folder='old',retest_folder='new',baseline_status='complete_with_gaps',retest_status='complete_with_gaps',baseline_cost={},retest_cost={},baseline_elapsed_seconds=1,retest_elapsed_seconds=2,baseline_unchanged=True,retest_coverage_gaps=[])
        with tempfile.TemporaryDirectory() as temp:
            h.write_comparison(Path(temp),{'rows':[row],'recommendation':'No default change.','limitations':[]})
            text=(Path(temp)/'comparison.md').read_text(encoding='utf-8')
            self.assertIn('| unknown | unknown | False | length | False |',text)
            self.assertIsNone(h.p.read_json(Path(temp)/'comparison.json')['rows'][0]['transitions'][0]['retest']['completion_tokens'])

if __name__=='__main__': unittest.main()
