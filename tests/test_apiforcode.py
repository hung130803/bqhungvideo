"""No-network APIforcode protocol, quota and evidence tests."""
import os,sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
AREA=Path(tempfile.mkdtemp(prefix='bq_api_'))
os.environ.update(BQ_DATA_DIR=str(AREA),BQ_DB_PATH=str(AREA/'test.db'),BQ_QSETTINGS_INI=str(AREA/'settings.ini'),BQ_BO_MANG='1',QT_QPA_PLATFORM='offscreen')
import _test_guard
from config import settings,Settings,update_env
from app.ai import llm,apiforcode as api,story_quality as q
from app.core.pipeline import is_configuration_error,is_content_block_error
KEY='sk-fixture-only-123456789012345'
def reply(content='{"visible":"blue card","uncertain":""}',finish='stop',status=200):
    response=Mock(ok=status<300,status_code=status)
    response.json.return_value={'choices':[{'finish_reason':finish,'message':{'content':content}}],'usage':{'prompt_tokens':23,'completion_tokens':12}}
    return response

class APITests(unittest.TestCase):
    def setUp(self):
        self.image=AREA/'frame.png';self.image.write_bytes(b'\x89PNG fixture')
        self.patches=[patch.object(Settings,'LLM_PROVIDER','apiforcode'),patch.object(Settings,'APIFORCODE_API_KEY',KEY),
            patch.object(Settings,'APIFORCODE_KEYS_FILE',''),patch.object(Settings,'APIFORCODE_MODEL','claude-opus-5-on'),
            patch.object(Settings,'APIFORCODE_VISION_MODEL','claude-opus-5-on'),patch.object(Settings,'USE_VISION',True)]
        for p in self.patches:p.start();self.addCleanup(p.stop)

    def test_key_file_utf8_and_utf16_without_copying_secret_to_settings(self):
        for enc in ('utf-8-sig','utf-16'):
            file=AREA/(enc+'.txt');file.write_text(KEY+'\n',encoding=enc)
            with patch.object(Settings,'APIFORCODE_API_KEY',''),patch.object(Settings,'APIFORCODE_KEYS_FILE',str(file)):
                self.assertEqual(settings.llm_keys_for('apiforcode'),[KEY])

    def test_purchased_key_line_with_label_and_account(self):
        for enc in ('utf-8-sig','utf-16'):
            for text in ('account@example | '+KEY, 'API key: "'+KEY+'"', 'Key='+KEY+'\n'+KEY):
                file=AREA/'purchased.txt';file.write_text(text,encoding=enc)
                with patch.object(Settings,'APIFORCODE_API_KEY',''),patch.object(Settings,'APIFORCODE_KEYS_FILE',str(file)):
                    self.assertEqual(settings.llm_keys_for('apiforcode'),[KEY])

    def test_chat_route_and_no_redirect(self):
        with patch.object(api.requests,'post',return_value=reply()) as post:
            out=llm.complete_json('Fixture only',provider='apiforcode',strict_object=True)
        self.assertEqual(out['visible'],'blue card')
        self.assertEqual(post.call_count,1)
        self.assertEqual(post.call_args.args[0],'https://api.apiforcode.com/v1/chat/completions')
        self.assertFalse(post.call_args.kwargs['allow_redirects'])
        self.assertEqual(post.call_args.kwargs['json']['model'],'claude-opus-5-on')

    def test_vision_uses_image_bytes_and_vision_model(self):
        with patch.object(Settings,'APIFORCODE_VISION_MODEL','fixture-vision'),patch.object(api.requests,'post',return_value=reply()) as post:
            self.assertTrue(llm.vision_available())
            self.assertEqual(llm.vision_max_images(),8)
            result=llm.complete_vision_json('Fixture',[str(self.image)],request_timeout=12)
        self.assertEqual(result['visible'],'blue card')
        body=post.call_args.kwargs['json'];self.assertEqual(body['model'],'fixture-vision')
        self.assertTrue(body['messages'][0]['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))
        self.assertEqual(post.call_args.kwargs['timeout'][1],12)

    def test_truncated_vision_is_not_accepted(self):
        with patch.object(api.requests,'post',return_value=reply(finish='length')),self.assertRaises(llm.LLMInvalidVision):
            llm.complete_vision_json('Fixture',[str(self.image)])

    def test_empty_does_not_spend_retries(self):
        with patch.object(api.requests,'post',return_value=reply('')) as post,self.assertRaises(llm.LLMError) as raised:
            llm.complete_json('Fixture',provider='apiforcode')
        self.assertEqual(post.call_count,1);self.assertTrue(is_configuration_error(str(raised.exception)))

    def test_network_uncertainty_is_not_retried_by_evidence_layer(self):
        with patch.object(api.requests,'post',side_effect=api.requests.Timeout('fixture')) as post,self.assertRaises(llm.LLMError) as raised:
            q.provider_call(lambda:llm.complete_text('Fixture',provider='apiforcode'))
        self.assertEqual(post.call_count,1);self.assertTrue(is_configuration_error(str(raised.exception)))

    def test_exhausted_not_retried(self):
        response=reply(status=402);response.json.return_value={'error':{'message':'insufficient_quota'}}
        with patch.object(api.requests,'post',return_value=response) as post,self.assertRaises(llm.LLMError) as raised:
            llm.complete_text('Fixture',provider='apiforcode')
        self.assertEqual(post.call_count,1);self.assertTrue(is_configuration_error(str(raised.exception)))

    def test_refusal_no_provider_fallback(self):
        with patch.object(api.requests,'post',return_value=reply('',finish='content_filter')) as post,self.assertRaises(llm.LLMContentBlocked) as raised:
            llm.complete_text('Fixture',provider='apiforcode')
        self.assertEqual(post.call_count,1);self.assertIn('APIforcode',str(raised.exception));self.assertTrue(is_content_block_error(raised.exception))

    def test_errors_redact_key(self):
        response=reply(status=400);response.json.return_value={'error':{'message':'bad '+KEY}}
        with patch.object(api.requests,'post',return_value=response),self.assertRaises(RuntimeError) as raised:
            api.chat(KEY,'fixture','Fixture')
        self.assertNotIn(KEY,str(raised.exception))

    def test_canceled_budget_does_not_send_images(self):
        from app.queue.worker import CanceledError
        def cancel():raise CanceledError()
        with llm.bounded_call(5,cancel),patch.object(api.requests,'post') as post,self.assertRaises(CanceledError):
            llm.complete_vision_json('Fixture',[str(self.image)])
        post.assert_not_called()


    def test_eight_images_one_request_nine_rejected(self):
        with patch.object(api.requests,'post',return_value=reply()) as post:
            api.chat(KEY,'fixture','Fixture',image_paths=[str(self.image)]*8)
            self.assertEqual(post.call_count,1)
            body=post.call_args.kwargs['json']
            self.assertEqual(len(body['messages'][0]['content']),9)
            self.assertEqual(body['max_tokens'],4800)
            with self.assertRaises(llm.LLMTooLarge):
                api.chat(KEY,'fixture','Fixture',image_paths=[str(self.image)]*9)
            self.assertEqual(post.call_count,1)

    def test_scene_sample_prompt_preserves_interval_speech(self):
        response={'frames':[{'id':i,'visible':'fixture','uncertain':''} for i in range(3)]}
        from types import SimpleNamespace
        ctx=SimpleNamespace(check_canceled=lambda:None)
        with patch.object(q,'frame_paths',side_effect=lambda *a:[str(self.image)]),patch.object(api.requests,'post',return_value=reply(json.dumps(response))) as post:
            value=q.visual_evidence('fixture',{'id':7,'start':10.,'end':20.},'SOURCE_SPEECH',ctx,(.1,.5,.9))
        self.assertEqual(post.call_count,1)
        prompt=post.call_args.kwargs['json']['messages'][-1]['content'][0]['text']
        self.assertEqual(prompt.count('SOURCE_SPEECH'),3)
        self.assertEqual([x['at'] for x in value['observations']],[11.,15.,19.])

    def test_build_evidence_persists_and_reuses_batch(self):
        from app.core import analysis
        src=AREA/'source.fixture';src.write_bytes(b'fixture')
        saved={};writes=[]
        def save(video_id,kind,status,value,**kwargs):
            saved.clear();saved.update(json.loads(json.dumps(value)));writes.append(value['complete'])
        value={'frames':[{'id':i,'visible':'fixture','uncertain':''} for i in range(3)]}
        with patch.object(analysis,'get_analysis',side_effect=lambda *a:json.loads(json.dumps(saved))),patch.object(analysis,'_set',side_effect=save),patch.object(q,'frame_paths',side_effect=lambda *a:[str(self.image)]),patch.object(api.requests,'post',return_value=reply(json.dumps(value))) as post:
            first=q.build_evidence(1,str(src),36.,[],{},Mock())
            second=q.build_evidence(1,str(src),36.,[],{},Mock())
        self.assertEqual(post.call_count,1)
        self.assertEqual(first,second)
        self.assertEqual(writes,[False,True,True])

    def test_server_failure_and_malformed_shape_stop_paid_retry(self):
        cases=[(503,{'error':'overloaded'}),(200,[]),(200,{'choices':'invalid'}),(200,{'choices':[{'message':[]}]})]
        for status,body in cases:
            response=reply(status=status);response.json.return_value=body
            with patch.object(api.requests,'post',return_value=response) as post,self.assertRaises(llm.LLMError) as raised:
                q.provider_call(lambda:llm.complete_text('Fixture',provider='apiforcode'))
            self.assertEqual(post.call_count,1)
            self.assertTrue(is_configuration_error(str(raised.exception)))


    def test_paid_json_invalid_truncated_or_wrong_shape_not_retried(self):
        for content,finish in [('not JSON','stop'),('[]','stop'),('{}','length')]:
            with patch.object(api.requests,'post',return_value=reply(content,finish)) as post,self.assertRaises(llm.LLMError) as raised:
                llm.complete_json('Fixture',provider='apiforcode',strict_object=True)
            self.assertEqual(post.call_count,1)
            self.assertTrue(is_configuration_error(str(raised.exception)))

    def test_paid_vision_invalid_truncated_not_queue_retried(self):
        for content,finish in [('not JSON','stop'),('[]','stop'),('{}','length')]:
            with patch.object(api.requests,'post',return_value=reply(content,finish)) as post,self.assertRaises(llm.LLMInvalidVision) as raised:
                llm.complete_vision_json('Fixture',[str(self.image)])
            self.assertEqual(post.call_count,1)
            self.assertTrue(is_configuration_error(str(raised.exception)))


    def test_text_uses_remaining_budget_and_vision_stays_120(self):
        with llm.bounded_call(180),patch.object(api.requests,'post',return_value=reply()) as post:
            llm.complete_json('Fixture',provider='apiforcode',strict_object=True)
            self.assertGreater(post.call_args.kwargs['timeout'][1],179)
            self.assertLessEqual(post.call_args.kwargs['timeout'][1],180)
            llm.complete_vision_json('Fixture',[str(self.image)])
            self.assertEqual(post.call_args.kwargs['timeout'],(15,120))

    def test_timeout_respects_remaining_budget_and_other_provider_default(self):
        with patch.object(llm.time,'monotonic',return_value=100.):
            with llm.bounded_call(180):
                self.assertEqual(llm._check_call_budget(),45.)
                self.assertEqual(llm._check_call_budget(120.),120.)
            with llm.bounded_call(12),patch.object(api.requests,'post',return_value=reply()) as post:
                llm.complete_json('Fixture',provider='apiforcode',strict_object=True)
                self.assertEqual(post.call_args.kwargs['timeout'],(15,12))

    def test_read_and_connect_timeouts_explained_without_resend(self):
        for error,label in [(api.requests.ConnectTimeout('secret fixture'),'kết nối'),(api.requests.ReadTimeout('secret fixture'),'180 giây')]:
            with llm.bounded_call(180),patch.object(api.requests,'post',side_effect=error) as post,self.assertRaises(llm.LLMError) as raised:
                q.provider_call(lambda:llm.complete_json('Fixture',provider='apiforcode',strict_object=True))
            self.assertEqual(post.call_count,1)
            self.assertIn(label,str(raised.exception))
            self.assertNotIn('secret fixture',str(raised.exception))
            self.assertTrue(is_configuration_error(str(raised.exception)))

if __name__=='__main__':unittest.main(verbosity=2)
