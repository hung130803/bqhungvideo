import contextlib,importlib.util,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ai import story_vision_batch as batch

def units(n):return [dict(id=i,start=i*12,end=(i+1)*12) for i in range(n)]
def rows(n):return [{'unit':u,'transcript':'speech'} for u in units(n)]
def answer(ids):return {'frames':[dict(id=i,visible=f'frame {i}',uncertain='blur') for i in ids]}
class Tests(unittest.TestCase):
    def test_fifty_frames_need_seven_groups(self):
        groups=list(batch.groups(units(50),lambda u:'speech',lambda v:len(json.dumps(v))//4))
        self.assertEqual([len(g) for g in groups],[8,8,8,8,8,8,2])
        self.assertEqual([r['unit']['id'] for g in groups for r in g],list(range(50)))
    def test_budget_split_never_truncates_speech(self):
        groups=list(batch.groups(units(4),lambda u:'x'*1600,lambda v:len(json.dumps(v))))
        self.assertEqual(len(groups),4)
        self.assertTrue(all(len(g[0]['transcript'])==1600 for g in groups))
    def test_reordered_responses_use_ids_and_source_timestamps(self):
        valid,error=batch.validate(answer([2,0,1]),rows(3));self.assertFalse(error)
        self.assertEqual(valid[2]['observations'][0]['at'],30)
        self.assertEqual(valid[0]['observations'][0]['visible'],'frame 0')
    def test_missing_duplicate_and_unknown_are_not_guessed(self):
        value=answer([0,1,1,9]);valid,error=batch.validate(value,rows(3))
        self.assertEqual(set(valid),{0});self.assertIn('id trùng',error);self.assertIn('ngoài nhóm',error)
    def test_bad_shape_and_blank_rejected(self):
        self.assertTrue(batch.validate([],rows(1))[1])
        value=answer([0]);value['frames'][0]['visible']=' '
        self.assertEqual(batch.validate(value,rows(1))[0],{})
    def test_selected_scene_samples_batched_and_timed(self):
        q=types.ModuleType('app.ai.story_quality');q.SYSTEM='fixture'
        q.text_for=lambda *a:'speech';q.token_size=lambda v:len(json.dumps(v))//4
        q.frame_paths=Mock(side_effect=lambda src,u,folder,f:[f'frame-{u["start"]}.jpg'])
        q.provider_call=lambda call,*a,**kw:call()
        q.llm=types.SimpleNamespace(bounded_call=lambda *a:contextlib.nullcontext(),complete_vision_json=Mock(return_value=answer([2,0,1])))
        fakeai=types.ModuleType('app.ai');fakeai.story_quality=q
        ctx=types.SimpleNamespace(check_canceled=Mock())
        with patch.dict(sys.modules,{'app':types.ModuleType('app'),'app.ai':fakeai,'app.ai.story_quality':q}),patch.object(batch.tempfile,'TemporaryDirectory',lambda **kw:contextlib.nullcontext('fixture')):
            value=batch.inspect('fixture',dict(id=45,start=120,end=132),'speech',ctx,(.15,.5,.85))
        self.assertEqual(value['id'],45)
        self.assertEqual([r['at'] for r in value['observations']],[121.8,126,130.2])
        self.assertEqual(q.llm.complete_vision_json.call_count,1)
    def test_partial_saved_then_resume_only_missing(self):
        q=types.ModuleType('app.ai.story_quality');q.SYSTEM='fixture'
        q.text_for=lambda *a:'speech';q.token_size=lambda v:len(json.dumps(v))//4
        q.frame_paths=lambda src,u,folder,f:[f'frame-{u["id"]}.jpg']
        q.provider_call=lambda call,*a,**kw:call()
        q.llm=types.SimpleNamespace(bounded_call=lambda *a:contextlib.nullcontext(),complete_vision_json=Mock(return_value=answer([0,2])))
        fakeapp=types.ModuleType('app');fakeai=types.ModuleType('app.ai');fakeai.story_quality=q
        cache={};ctx=Mock();commit=Mock()
        # No disk artifacts required for protocol/state-machine checks.
        with patch.dict(sys.modules,{'app':fakeapp,'app.ai':fakeai,'app.ai.story_quality':q}),patch.object(batch.tempfile,'TemporaryDirectory',lambda **kw:contextlib.nullcontext('fixture')):
            with self.assertRaisesRegex(RuntimeError,'không tự gọi lại'):batch.build('fixture',units(3),cache,[],None,ctx,commit)
            self.assertEqual(set(cache),{'0','2'});commit.assert_called_once()
            q.llm.complete_vision_json.return_value=answer([1])
            result=batch.build('fixture',units(3),cache,[],None,ctx,commit)
            self.assertEqual([r['id'] for r in result],[0,1,2])
            self.assertEqual(q.llm.complete_vision_json.call_args.args[1],['frame-1.jpg'])
    def test_no_calls_if_cached(self):
        q=types.ModuleType('app.ai.story_quality');q.llm=Mock();q.token_size=lambda v:len(json.dumps(v))//4
        fakeai=types.ModuleType('app.ai');fakeai.story_quality=q
        cache={str(u['id']):u for u in units(4)}
        with patch.dict(sys.modules,{'app':types.ModuleType('app'),'app.ai':fakeai,'app.ai.story_quality':q}):
            result=batch.build('fixture',units(4),cache,[],None,Mock(),Mock())
        self.assertEqual(len(result),4);q.llm.complete_vision_json.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)
