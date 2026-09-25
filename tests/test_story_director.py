"""Editorial contracts, bounded scanning and real music envelopes, isolated."""
import os,sys,tempfile,json,unittest,threading,time,subprocess,wave,math,struct
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];AREA=Path(tempfile.mkdtemp(prefix='bq_director_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_QSETTINGS_INI=str(AREA/'settings.ini'),QT_QPA_PLATFORM='offscreen',BQ_BO_MANG='1')
sys.path.insert(0,str(ROOT))
import _test_guard  # noqa: F401,E402
from app.ai import story_director as d,story_quality as q
from app.database import db
from app import services
from config import settings

def units():
 return [dict(u,safe_orig=True,transcript=f"{u['start']:.2f}-{u['end']:.2f}: The speaker describes a real event.",
  observations=[{'at':(u['start']+u['end'])/2,'visible':'A person holds a bowl.','uncertain':'Ingredients unknown.'}]) for u in q.coverage(240)]

def edit(ids=(0,2,5,9,14,18)):
 return {'title':'A real contrast','angle':'Preparation and outcome','shots':[{'source_id':i,'role':'hook' if n==0 else 'payoff' if n==len(ids)-1 else 'build',
  'reason':'Shows the setup or its consequence','mode':'narrate','sfx':'none'} for n,i in enumerate(ids)]}

class Director(unittest.TestCase):
 def setUp(self):self.ctx=Mock()

 def test_shortlist_normalizes_numeric_strings_and_duplicates(self):
  self.assertEqual(d.shortlist_ids({'ids':['12',12,' 19 ']},{12,19,27},2),[12,19])

 def test_shortlist_rejects_unknown_ids_and_malformed_values(self):
  for raw in ({'ids':[999]},{'ids':[True]},{'ids':[{'id':12}]},{'ids':'12'},
              {'ids':[]},{'ids':[12.0]},None,{'ids':[12,19,27]}):
   with self.subTest(raw=raw),self.assertRaises(ValueError):d.shortlist_ids(raw,{12,19,27},2)

 def test_malformed_shortlist_keeps_evidence_instead_of_failing_video(self):
  cards=[{'id':i,'event':'Supported speech with setup and outcome. '*6,'interest':3} for i in range(73)]
  batches=q.evidence_batches(cards,limit=5500)
  with patch.object(q,'ask',return_value={'ids':[{'wrong':'schema'}]}) as ask:
   result=d.planning_cards(cards,self.ctx)
  self.assertEqual(result,cards);self.assertEqual(ask.call_count,2*len(batches))

 def test_shortlist_repairs_only_with_ids_in_each_original_batch(self):
  cards=[{'id':100+i,'event':'Supported speech with setup and outcome. '*6,'interest':3} for i in range(73)]
  repaired=[]
  def reply(prompt):
   data=json.loads(prompt.split('\n',1)[1]);block=data['events']
   if not data['repair']:return {'ids':[-1]}
   repaired.append(data['repair']);return {'ids':[str(c['id']) for c in block[:max(2,len(block)//2)]]}
  with patch.object(q,'ask',side_effect=reply) as ask:result=d.planning_cards(cards,self.ctx)
  self.assertTrue(repaired);self.assertLess(len(result),len(cards));self.assertGreaterEqual(len(result),8)
  self.assertTrue(all(c in cards for c in result));self.assertLess(ask.call_count,100)

 def test_shortlist_provider_and_cancel_errors_are_not_hidden(self):
  cards=[{'id':i,'event':'Supported event. '*20,'interest':3} for i in range(73)]
  with patch.object(q,'ask',side_effect=q.llm.LLMError('provider unavailable')):
   with self.assertRaises(q.llm.LLMError):d.planning_cards(cards,self.ctx)
  self.ctx.check_canceled.side_effect=RuntimeError('canceled')
  with patch.object(q,'ask') as ask:
   with self.assertRaisesRegex(RuntimeError,'canceled'):d.planning_cards(cards,self.ctx)
   ask.assert_not_called()

 def test_fifteen_minute_notes_preserve_every_source_id_without_shortlisting(self):
  source=q.coverage(871.050159);lookup={u['id']:u for u in source}
  cards=[{'id':u['id'],'event':'The speaker describes a specific setup and its later outcome with uncertainty. '*4,'interest':3} for u in source]
  with patch.object(d,'planning_cards',side_effect=AssertionError('Unnecessary shortlist')):
   result,notes=d.planning_notes(cards,lookup,self.ctx)
  self.assertEqual(result,cards);self.assertEqual([r[0] for r in notes],[c['id'] for c in cards])
  self.assertLessEqual(q.token_size(notes),3300)

 def test_deadline_does_not_rotate_forever_and_is_thread_local(self):
  with q.llm.bounded_call(-1):
   with self.assertRaisesRegex(q.llm.LLMError,'quá lâu'):q.llm._check_call_budget()
  self.assertIsNone(q.llm._check_call_budget())
  cancel=Mock(side_effect=RuntimeError('canceled'))
  with q.llm.bounded_call(60,cancel):
   with self.assertRaisesRegex(RuntimeError,'canceled'):q.llm._retry_sleep(30)

 def test_rate_wait_preserves_work_and_checks_cancel(self):
  call=Mock(side_effect=[q.llm.LLMError('Error code: 429 rate limit'),{'ok':True}])
  with patch.object(q.llm,'soonest_ready_wait',return_value=1),patch.object(q.time,'sleep'):
   self.assertEqual(q.provider_call(call,self.ctx.check_canceled,scope='vision'),{'ok':True})
  self.assertGreater(self.ctx.check_canceled.call_count,2)

 def test_parallel_vision_wait_never_writes_a_lower_progress(self):
  child=q.VisionContext(self.ctx);child.wait_for_provider(20)
  self.assertIn('Groq',child.status());self.ctx.progress.assert_not_called()
  child.check_canceled();self.ctx.check_canceled.assert_called_once()

 def test_script_retry_keeps_progress_but_updates_stage_message(self):
  context=q.StoryContext(self.ctx);context.progress(.75,'audit');context.progress(.70,'rewrite')
  self.ctx.progress.assert_called_with(.75,'rewrite')

 def test_voice_validation_rejects_wrong_language_before_render(self):
  with self.assertRaises(ValueError):q.validate_voice('vi-VN-NamMinhNeural','en')
  q.validate_voice('en-US-GuyNeural','en');q.validate_voice('en-US-AndrewMultilingualNeural','vi')

 def test_speech_evidence_never_leaks_words_from_next_scene(self):
  segments=[{'start':10,'end':16,'text':'Setup and a later reveal'}]
  words=[{'start':10,'end':11,'word':'Setup'},{'start':13,'end':14,'word':'reveal'}]
  self.assertEqual(q.text_for(segments,0,12,words),'10.00-11.00: Setup')
  self.assertEqual(q.text_for(segments,0,12),'')

 def test_planner_checks_each_story_against_original_speech(self):
  first=edit();second=edit((1,3,6,10,15,19))
  for raw in (first,second):
   for shot in raw['shots']:shot.pop('role')
  cards=[{'id':u['id'],'event':'A real event involving the same object','interest':3} for u in units()]
  with patch.object(q,'ask',side_effect=[first,{'approved':True},second,{'approved':True,'distinct_from_previous':True}]) as ask:
   plans=d.choose_edits(units(),cards,set(),{},2,self.ctx)
  self.assertEqual(len(plans),2);self.assertEqual(ask.call_count,4)
  self.assertIn('The speaker describes a real event',ask.call_args_list[1].args[0])
  self.assertEqual(plans[0]['parts'][0]['role'],'hook');self.assertEqual(plans[0]['parts'][-1]['role'],'payoff')
  self.assertTrue(set(p['source_id'] for p in plans[0]['parts']).isdisjoint(p['source_id'] for p in plans[1]['parts']))

 def test_auto_count_does_not_force_duplicate_stories(self):
  first=edit();second=edit((1,3,6,10,15,19))
  cards=[{'id':u['id'],'event':'Same incident','interest':3} for u in units()]
  calls=[first,{'approved':True}]+[second,{'approved':True,'distinct_from_previous':False,'issues':'Same question and payoff'}]*3
  with patch.object(q,'ask',side_effect=calls):plans=d.choose_edits(units(),cards,set(),{},2,self.ctx)
  self.assertEqual(len(plans),1)
  with patch.object(q,'ask',side_effect=calls):plans=d.choose_edits(units(),cards,set(),{'recap_count':2},2,self.ctx)
  self.assertEqual(len(plans),2);self.assertTrue(plans[1]['selection_review']['duplicate'])
  self.assertFalse(plans[1]['selection_review']['approved'])

 def test_unknown_diversity_is_visible_not_silently_certified(self):
  cards=[{'id':u['id'],'event':'Same incident','interest':3} for u in units()]
  calls=[edit(),{'approved':True}]+[edit((1,3,6,10,15,19)),{'approved':True}]*3
  with patch.object(q,'ask',side_effect=calls):plans=d.choose_edits(units(),cards,set(),{},2,self.ctx)
  self.assertFalse(plans[1]['selection_review']['approved']);self.assertFalse(plans[1]['selection_review']['duplicate'])

 def test_anchor_checks_are_time_based_and_reuse_cache(self):
  u=dict(id=1,start=10.,end=22.,transcript='Local words',observations=[{'at':16.,'visible':'center'},{'at':16.01,'visible':'same center'}])
  def see(src,unit,text,ctx,fractions):
   return dict(unit,observations=[{'at':unit['start']+(unit['end']-unit['start'])*f,'visible':'frame'} for f in fractions])
  with patch.object(q,'visual_evidence',side_effect=see) as vision:
   result=d.enrich_scene('src',u,self.ctx,(.15,.5,.85))
   d.enrich_scene('src',result,self.ctx,(.15,.5,.85))
  self.assertEqual(vision.call_count,1);self.assertEqual(vision.call_args.kwargs['fractions'],(.15,.85))

 def test_extra_inspection_only_disputed_scene_and_no_repeat(self):
  plan=d.validate_edit(edit(),units(),set(),61,119)
  checks=[{'source_id':0,'supported':True,'scene_match':True},{'source_id':2,'supported':False,'scene_match':True}]
  def see(src,unit,text,ctx,fractions):
   return dict(unit,observations=[{'at':unit['start']+(unit['end']-unit['start'])*f,'visible':'frame'} for f in fractions])
  with patch.object(q,'visual_evidence',side_effect=see) as vision:
   d.inspect_disputed(plan,checks,'src',self.ctx);d.inspect_disputed(plan,checks,'src',self.ctx)
  self.assertEqual(vision.call_count,1);self.assertEqual(vision.call_args.args[1]['id'],2)

 def test_story_sounds_follow_approved_beats_after_edit_and_speed(self):
  from app.core.ffmpeg_utils import story_accent_points
  parts=[{'start':100,'end':112,'sfx':'reveal','sfx_offset':3},
         {'start':200,'end':212,'sfx':'comedy','sfx_offset':8}]
  self.assertEqual(story_accent_points(parts,[(100,112),(200,212)],2),[(1.5,'reveal','tình tiết'),(10.,'comedy','tình tiết')])
  self.assertEqual(story_accent_points([dict(parts[0],sfx_offset=20)],[(100,112)]),[])
  self.assertEqual(story_accent_points([dict(parts[0],sfx='none')],[(100,112)]),[])

 def test_rewrite_sees_end_of_scene_after_extra_inspection(self):
  frames=[{'at':t,'visible':str(t)} for t in (11,3,5,1,9)]
  self.assertEqual([o['at'] for o in d.representative_observations(frames)],[1,5,11])

 def test_planner_restores_source_chronology_before_semantic_audit(self):
  raw=edit();raw['shots'][2],raw['shots'][3]=raw['shots'][3],raw['shots'][2]
  cards=[{'id':u['id'],'event':'Same incident at this source time','interest':3} for u in units()]
  with patch.object(q,'ask',side_effect=[raw,{'approved':True}]) as ask:
   result=d.choose_edits(units(),cards,set(),{},1,self.ctx)
  self.assertEqual([p['source_id'] for p in result[0]['parts']],[0,2,5,9,14,18])
  self.assertEqual(ask.call_count,2)

 def test_claim_repair_changes_only_flagged_sentence_and_requires_quote(self):
  plan=d.validate_edit(edit(),units(),set(),61,119)
  for p in plan['parts']:p['text']='Original words.'
  problem=d.AuditFailure('Invented claim',[{'source_id':2,'supported':False,'scene_match':False,'issue':'No source'}])
  raw={'shots':[{'source_id':2,'text':'The speaker describes an event.','support_quote':'The speaker describes a real event.'}]}
  with patch.object(q,'ask',return_value=raw):fixed=d.repair_claims(plan,problem,'English',self.ctx)
  self.assertEqual(fixed['parts'][0]['text'],'Original words.')
  self.assertEqual(fixed['parts'][1]['text'],'The speaker describes an event.')
  self.assertEqual(plan['parts'][1]['text'],'Original words.')
  raw['shots'][0]['support_quote']='A quote that does not exist'
  with patch.object(q,'ask',return_value=raw):
   with self.assertRaisesRegex(ValueError,'căn cứ'):d.repair_claims(plan,problem,'English',self.ctx)

 def test_global_nonadjacent_story_and_cross_part_no_reuse(self):
  p=d.validate_edit(edit(),units(),set(),61,119)
  self.assertEqual(p['duration'],72);self.assertEqual(p['windows'][-1],[216,228])
  self.assertGreater(sum(b[0]>a[1] for a,b in zip(p['windows'],p['windows'][1:])),2)
  with self.assertRaises(ValueError):d.validate_edit(edit(),units(),{2},61,119)

 def test_reject_reversed_timeline_outside_crop_missing_payoff_and_short(self):
  for raw in (edit((2,0,5,9,14,18)),edit((0,1,2,3))):
   with self.assertRaises(ValueError):d.validate_edit(raw,units(),set(),61,119)
  raw=edit();raw['shots'][0]['start']=-1
  with self.assertRaises(ValueError):d.validate_edit(raw,units(),set(),61,119)
  raw=edit();raw['shots'][-1]['role']='build'
  with self.assertRaises(ValueError):d.validate_edit(raw,units(),set(),61,119)

 def test_contiguous_action_needs_reason_not_random_mandatory_cuts(self):
  raw=edit((0,1,2,3,4,5))
  with self.assertRaisesRegex(ValueError,'liền'):d.validate_edit(raw,units(),set(),61,119)
  raw['continuous_reason']='The complete unbroken action is necessary to understand its outcome.'
  self.assertEqual(d.validate_edit(raw,units(),set(),61,119)['duration'],72)

 def test_original_speech_cannot_be_cut_in_middle(self):
  raw=edit();raw['shots'][1].update(mode='orig',start=25)
  with self.assertRaisesRegex(ValueError,'trọn vẹn'):d.validate_edit(raw,units(),set(),61,119)

 def test_catalogue_requires_every_interval(self):
  with patch.object(q,'ask',return_value={'events':[{'id':0,'event':'An event','interest':3}]}):
   with self.assertRaisesRegex(RuntimeError,'thiếu cảnh'):d.catalogue(units(),self.ctx)

 def test_crop_verification_does_not_use_images_outside_export(self):
  source=units();plan=d.validate_edit(edit(),source,set(),61,119)
  p=plan['parts'][0];p.update(start=0,end=4)
  seen=[]
  def see(src,u,transcript,ctx,fractions):
   seen.append((u['start'],u['end'],fractions))
   return dict(u,observations=[{'at':u['start']+(u['end']-u['start'])*f,'visible':'Bowl','uncertain':''} for f in fractions])
  with patch.object(q,'visual_evidence',side_effect=see):d.refine([plan],source,'source',self.ctx)
  actual=json.loads(p['evidence'])['observations']
  self.assertTrue(all(0<=o['at']<=4 for o in actual));self.assertEqual(len(actual),3)
  self.assertIn((0,4,(.15,.5,.85)),seen)

 def test_broken_second_script_preserves_first_structural_draft(self):
  plan=d.validate_edit(edit(),units(),set(),61,119)
  good={'hooks':['A concrete hook.','Another hook.','Third hook.'],'selected_hook':0,
   'shots':[{'source_id':p['source_id'],'text':'A concrete hook. Some supported words.','sfx':'none','support_quote':'The speaker describes a real event.'} for p in plan['parts']]}
  bad=json.loads(json.dumps(good));bad['shots'][0]['text']='Corrupt first sentence';bad['shots'][-1]['source_id']=999
  with patch.object(q,'ask',side_effect=[good,bad,bad]),patch.object(d,'audit',side_effect=ValueError('Needs human review')):
   result=d.script(plan,{},'English',self.ctx,0,1)
  self.assertTrue(result['parts'][0]['text'].startswith('A concrete hook.'))
  self.assertFalse(result['review']['approved']);self.assertEqual(plan['parts'][0]['text'],'')

 def test_malformed_audit_is_review_failure(self):
  plan=d.validate_edit(edit(),units(),set(),61,119)
  with patch.object(q,'ask',return_value={'checks':[None]*6}):
   with self.assertRaises(ValueError):d.audit(plan,self.ctx)

 def test_ten_minute_coarse_scan_fifty_calls_bounded_and_cached(self):
  source=AREA/'coarse.mp4';source.write_bytes(b'fixture')
  pid=services.create_project('scan','tests');vid=db.insert('INSERT INTO videos(project_id,src_path,duration) VALUES(?,?,600)',(pid,str(source)))
  active=0;maximum=0;lock=threading.Lock()
  def inspect(src,u,text,ctx):
   nonlocal active,maximum
   with lock:active+=1;maximum=max(maximum,active)
   time.sleep(.005)
   with lock:active-=1
   return dict(u,observations=[{'at':(u['start']+u['end'])/2,'visible':'A scene','uncertain':''}],transcript=text)
  with patch.object(q.llm,'active_provider',return_value='groq'),patch.object(q,'visual_evidence',side_effect=inspect) as vision:
   first=q.build_evidence(vid,str(source),600,[],{},self.ctx)
   q.build_evidence(vid,str(source),600,[],{},self.ctx)
  self.assertEqual(len(first[0]),50);self.assertEqual(vision.call_count,50);self.assertEqual(maximum,2)

 def test_real_ffmpeg_music_duck_and_fade(self):
  from app.core.ffmpeg_utils import story_music_filters
  path=AREA/'mixed.wav'
  subprocess.run([settings.FFMPEG_PATH,'-y','-v','error','-f','lavfi','-i','sine=frequency=400:sample_rate=16000:duration=8',
   '-af',story_music_filters(8,.5,[(2,4)]),'-c:a','pcm_s16le',str(path)],check=True,timeout=20)
  with wave.open(str(path),'rb') as w:
   rate=w.getframerate();samples=struct.unpack('<'+'h'*w.getnframes(),w.readframes(w.getnframes()))
  def rms(a,b):
   values=samples[int(a*rate):int(b*rate)];return math.sqrt(sum(v*v for v in values)/len(values))
  self.assertLess(rms(2.5,3.5),rms(5,6)*.4)
  self.assertLess(rms(0,.1),rms(1,1.5)*.15)
  self.assertLess(rms(7.9,8),rms(5,6)*.15)

 def test_voice_only_picker_retains_voice_without_changing_settings(self):
  from PyQt6.QtWidgets import QApplication
  from app.ui.recap_settings import RecapSettingsDialog
  app=QApplication.instance() or QApplication([])
  with patch.object(RecapSettingsDialog,'_fill_voices_bg',lambda s:s._set_voices([('Guy','en-US-GuyNeural')])):
   dialog=RecapSettingsDialog(voice_only=True,initial_voice='en-US-GuyNeural')
   self.assertEqual(dialog.voice.currentData(),'en-US-GuyNeural');self.assertEqual(dialog.pace.currentData(),'normal')
   dialog.reject();app.processEvents()

if __name__=='__main__':unittest.main(verbosity=2)
