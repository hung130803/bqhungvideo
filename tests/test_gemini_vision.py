"""Gemini evidence failures, rotation and retry contracts; no API/network calls."""
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
AREA=NS(name=tempfile.mkdtemp(prefix='bq-gemini-vision-'))
os.environ.update(BQ_DATA_DIR=AREA.name,BQ_DB_PATH=str(Path(AREA.name)/'test.db'),
    BQ_QSETTINGS_INI=str(Path(AREA.name)/'settings.ini'),BQ_BO_MANG='1')
import _test_guard
import google.generativeai as genai
from app.ai import llm,story_quality as q
from app.queue.worker import CanceledError


def response(text='{"visible":"A blue card.","uncertain":"Identity unknown."}',finish=1,block=0):
    return NS(text=text,candidates=[NS(finish_reason=finish)],
        prompt_feedback=NS(block_reason=block),usage_metadata=None)


class GeminiVisionTests(unittest.TestCase):
    def setUp(self):
        self.keys=['fixture-gemini-one','fixture-gemini-two']
        self.model=Mock();self.model.generate_content.return_value=response()
        self.image=Path(AREA.name)/'frame.jpg';self.image.write_bytes(b'fixture-only')
        self.patches=[patch.object(llm.settings,'llm_keys_for',return_value=self.keys),
            patch.object(llm,'active_provider',return_value='gemini'),
            patch.dict(llm._KEY_STATE,{},clear=True),
            patch.object(genai,'configure'),
            patch.object(genai,'GenerativeModel',return_value=self.model)]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda:[p.stop() for p in reversed(self.patches)])

    def call(self,**kw):
        return llm.complete_vision_json('Describe image',[str(self.image)],provider='gemini',**kw)

    def evidence(self):
        with patch.object(q,'frame_paths',return_value=[str(self.image)]):
            return q.visual_evidence('unused',{'id':0,'start':0,'end':12},'',Mock())

    def test_actual_sdk_accepts_evidence_schema(self):
        from google.generativeai.types.generation_types import to_generation_config_dict
        value=to_generation_config_dict({'response_mime_type':'application/json',
            'response_schema':q.VISUAL_SCHEMA,'max_output_tokens':8192})
        self.assertIn('response_schema',value)

    def test_schema_timeout_and_success_scope(self):
        with patch.object(llm,'mark_ok') as good, llm.bounded_call(10):
            self.call(response_schema=q.VISUAL_SCHEMA,request_timeout=4)
        args=self.model.generate_content.call_args.kwargs
        self.assertEqual(args['generation_config']['response_schema'],q.VISUAL_SCHEMA)
        self.assertEqual(args['request_options']['timeout'],4)
        self.assertIsNone(args['request_options']['retry'])
        good.assert_called_once_with('gemini',self.keys[0],scope='vision')

    def test_429_rotates_and_does_not_mark_key_invalid(self):
        self.model.generate_content.side_effect=[RuntimeError('429 quota retry-after: 20'),response()]
        self.assertEqual(self.call()['visible'],'A blue card.')
        self.assertEqual(self.model.generate_content.call_count,2)
        self.assertFalse(llm._is_invalid(llm._KEY_STATE[('gemini',self.keys[0])]))
        self.assertEqual(llm._KEY_STATE[('gemini',self.keys[0])]['limited_scope'],'vision')

    def test_invalid_key_rotates(self):
        self.model.generate_content.side_effect=[RuntimeError('400 API key not valid'),response()]
        self.call()
        self.assertTrue(llm._is_invalid(llm._KEY_STATE[('gemini',self.keys[0])]))

    def test_start_index_selects_another_key(self):
        self.call(key_dau=1)
        genai.configure.assert_called_once_with(api_key=self.keys[1])

    def test_all_keys_limited_return_actionable_wait(self):
        self.model.generate_content.side_effect=RuntimeError('429 quota retry-after: 12')
        with self.assertRaisesRegex(llm.LLMError,'retry-after'):self.call()
        self.assertEqual(self.model.generate_content.call_count,2)

    def test_cancellation_while_waiting_for_sdk_lock(self):
        count=0
        def check():
            nonlocal count
            count+=1
            if count>=2:raise CanceledError()
        lock=Mock();lock.acquire.return_value=False
        with patch.object(llm,'_GEMINI_LOCK',lock),llm.bounded_call(5,check),self.assertRaises(CanceledError):
            self.call()
        self.model.generate_content.assert_not_called()

    def test_cooling_keys_are_not_called(self):
        for key in self.keys:llm.mark_limited('gemini',key,'429',retry_after=20,scope='vision')
        with self.assertRaisesRegex(llm.LLMError,'429'):self.call()
        self.model.generate_content.assert_not_called()

    def test_permission_error_is_not_bad_key_or_quota(self):
        self.model.generate_content.side_effect=RuntimeError('403 permission denied '+self.keys[0])
        with self.assertRaises(llm.LLMError) as err:self.call()
        self.assertNotIn(self.keys[0],str(err.exception))
        self.assertFalse(llm._is_invalid(llm._KEY_STATE[('gemini',self.keys[0])]))
        self.assertEqual(self.model.generate_content.call_count,1)

    def test_wrong_shape_retried_on_same_image(self):
        self.model.generate_content.side_effect=[response('[]'),response()]
        result=self.evidence()
        self.assertEqual(result['observations'][0]['visible'],'A blue card.')
        calls=self.model.generate_content.call_args_list
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[0].args[0][1],calls[1].args[0][1])
        self.assertIn('nonempty',calls[1].args[0][0])

    def test_empty_visible_stops_after_two_attempts(self):
        self.model.generate_content.return_value=response('{"visible":" ","uncertain":""}')
        with self.assertRaisesRegex(RuntimeError,'6.0s.*2 lần'):self.evidence()
        self.assertEqual(self.model.generate_content.call_count,2)

    def test_malformed_json_retries(self):
        self.model.generate_content.side_effect=[response('{"visible":"cut'),response()]
        self.evidence()
        self.assertEqual(self.model.generate_content.call_count,2)

    def test_truncated_even_if_valid_json_is_not_accepted(self):
        self.model.generate_content.side_effect=[response(finish=2),response()]
        self.evidence()
        self.assertEqual(self.model.generate_content.call_count,2)

    def test_content_block_not_retried_or_marked_bad_key(self):
        self.model.generate_content.return_value=response(block=1)
        with self.assertRaisesRegex(llm.LLMError,'block_reason'):self.evidence()
        self.assertEqual(self.model.generate_content.call_count,1)

    def test_uncertain_wrong_type_rejected(self):
        self.model.generate_content.return_value=response('{"visible":"card","uncertain":[]}')
        with self.assertRaises(RuntimeError):self.evidence()
        self.assertEqual(self.model.generate_content.call_count,2)

    def test_cancellation_survives(self):
        def canceled():raise CanceledError()
        with llm.bounded_call(10,canceled),self.assertRaises(CanceledError):self.call()
        self.model.generate_content.assert_not_called()

    def test_deadline_after_lock_wait_stops_request(self):
        with llm.bounded_call(-1),self.assertRaises(llm.LLMError):self.call()
        self.model.generate_content.assert_not_called()

    def test_wait_label_identifies_gemini(self):
        context=q.VisionContext(Mock());context.wait_for_provider(5)
        self.assertIn('Gemini',context.status())
        self.assertNotIn('Groq',context.status())

    def test_gemini_service_unavailable_retries_without_condemning_key(self):
        self.model.generate_content.side_effect=[RuntimeError('503 Service unavailable'),response()]
        with patch.object(q.time,'sleep'):
            self.evidence()
        self.assertEqual(self.model.generate_content.call_count,2)
        self.assertFalse(llm._is_invalid(llm._KEY_STATE[('gemini',self.keys[0])]))

    def test_valid_generic_json_preserves_array_callers(self):
        self.model.generate_content.return_value=response('[{"score":7}]')
        self.assertEqual(self.call(),[{'score':7}])


if __name__=='__main__':unittest.main(verbosity=2)
