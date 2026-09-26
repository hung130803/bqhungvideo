"""Regressions for mixed incidents and untranslated narration, no private fixtures."""
import os,sys,tempfile,json,unittest
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];AREA=Path(tempfile.mkdtemp(prefix='bq_context_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_QSETTINGS_INI=str(AREA/'settings.ini'),QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
sys.path.insert(0,str(ROOT))
import _test_guard  # noqa: F401,E402
from app.core import story_checks as check
from app.ai import story_director as d,story_quality as q

def unit(i,date,place='A road at night.'):
    return dict(id=i,start=i*12,end=(i+1)*12,safe_orig=True,transcript='A person says I am going to try this product now.',
        observations=[dict(at=i*12+t,visible=f'{place} Timestamp {date}.',uncertain='Identity unknown.') for t in (2,6,10)])

def part(u,text='Người nói muốn thử sản phẩm.'):
    return dict(source_id=u['id'],start=u['start'],end=u['end'],mode='narrate',role='build',reason='A supported local detail',text=text,evidence=json.dumps(u))

class Context(unittest.TestCase):
    def test_compaction_keeps_every_scene_and_date(self):
        rows=[dict(source_id=i,speech='A local word. '*80,scene_context=check.context(unit(i,'2020-10-31'))) for i in range(24)]
        result=d.compact_context_rows(rows)
        self.assertEqual([r['source_id'] for r in result],list(range(24)))
        self.assertLessEqual(q.token_size(result),3600)
        self.assertTrue(all(r['scene_context']['observed_dates']==['2020-10-31'] for r in result))

    def test_two_incidents_on_different_dates_are_flagged(self):
        parts=[part(unit(1,'2020-10-31')),part(unit(70,'2024-01-14','An airport terminal.'))]
        notes=check.continuity_issues(parts)
        self.assertEqual(len(notes),1);self.assertIn('2024-01-14',notes[0])
        self.assertIn('có thể',notes[0])

    def test_same_date_and_uncertain_single_frame_do_not_prove_a_mismatch(self):
        self.assertEqual(check.continuity_issues([part(unit(0,'2020-10-31')),part(unit(1,'2020-10-31'))]),[])
        u=unit(1,'2024-01-14');u['observations']=u['observations'][:1]
        self.assertEqual(check.continuity_issues([part(unit(0,'2020-10-31')),part(u)]),[])
        self.assertEqual(check.continuity_issues([{'evidence':'broken'}]),[])

    def test_copied_english_phrase_detected_but_names_and_english_target_allowed(self):
        p=part(unit(0,'2020-10-31'),'Cô nói “I am going to try this product now” rồi mở hộp.')
        self.assertTrue(check.language_issues([p],'vi'))
        self.assertEqual(check.language_issues([p],'English'),[])
        for text in ('Người nói quyết định thử sản phẩm.','Cô giới thiệu sản phẩm của New York City Museum.','Một cú zoom nhỏ.'):
            self.assertEqual(check.language_issues([dict(p,text=text)],'vi'),[])

    def test_local_language_failure_cannot_receive_ai_green_check(self):
        plan=dict(parts=[part(unit(0,'2020-10-31'),'Cô nói “I am going to try this product now”.')],target_language='Vietnamese')
        with patch.object(q,'ask') as ask:
            with self.assertRaisesRegex(ValueError,'tiếng Việt'):d.audit(plan,Mock())
            ask.assert_not_called()

    def test_global_audit_sees_visual_context_and_cannot_hide_date_conflict(self):
        parts=[part(unit(0,'2020-10-31')),part(unit(70,'2024-01-14','An airport terminal.'))]
        plan=dict(title='Two details',angle='A test',parts=parts,target_language='Vietnamese')
        rows=[dict(source_id=p['source_id'],supported=True,scene_match=True,issue='') for p in parts]
        with patch.object(q,'ask',side_effect=[{'checks':rows},{'approved':True,'issues':[]}]) as ask:
            result=d.audit(plan,Mock())
        self.assertFalse(result['approved']);prompt=ask.call_args.args[0]
        self.assertIn('airport terminal',prompt);self.assertIn('2020-10-31',prompt)

    def test_selection_retries_mixed_dates_instead_of_claiming_success(self):
        units=[unit(i,'2020-10-31' if i<5 else '2024-01-14') for i in range(12)]
        cards=[dict(id=u['id'],event='A police interaction',interest=3) for u in units]
        raw=dict(title='One incident',angle='A question',shots=[dict(source_id=i,reason='Connect setup to consequence',mode='narrate') for i in (0,2,4,7,9,11)])
        with patch.object(q,'ask',side_effect=[raw,{'approved':True}]*3) as ask:
            plans=d.choose_edits(units,cards,set(),{},1,Mock())
        self.assertFalse(plans[0]['selection_review']['approved']);self.assertEqual(ask.call_count,6)
        self.assertIn('scene_context',ask.call_args_list[1].args[0])

    def test_script_repairs_untranslated_quote_before_returning_success(self):
        p=part(unit(0,'2020-10-31'));p['role']='hook'
        plan=dict(title='Thử sản phẩm',angle='Thử',parts=[p])
        bad='Cô nói I am going to try this product now.';good='Cô quyết định thử sản phẩm này.'
        def draft(text):return dict(hooks=[text,'Một lựa chọn.','Một sản phẩm.'],selected_hook=0,
            shots=[dict(source_id=0,text=text,sfx='none',support_quote='try this product now')])
        calls=[]
        def ask(prompt,**kwargs):
            calls.append(prompt)
            if prompt.startswith('Write an engaging'):return draft(good if len(calls)>1 else bad)
            if prompt.startswith('Audit EACH'):return {'checks':[dict(source_id=0,supported=True,scene_match=True)]}
            return {'approved':True,'issues':[]}
        with patch.object(q,'ask',side_effect=ask):result=d.script(plan,{},'Vietnamese',Mock(),0,1)
        self.assertEqual(result['parts'][0]['text'],good);self.assertTrue(result['review']['approved'])
        self.assertEqual(len([c for c in calls if c.startswith('Write an engaging')]),2)

if __name__=='__main__':unittest.main(verbosity=2)
