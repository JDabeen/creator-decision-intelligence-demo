"""Mandatory actual-web-research gate. Pure offline tests; no paid calls."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hermes_integration import adapter


class WebGateTests(unittest.TestCase):
    @patch.object(adapter, 'check_ready', return_value='hermes-agent')
    @patch.object(adapter, '_call', return_value={
        'output':[{'type':'message','role':'assistant',
                   'content':[{'type':'output_text','text':'검색 완료라고 주장'}]}]
    })
    def test_no_real_tool_call_is_rejected(self, fake_call, ready):
        with self.assertRaisesRegex(adapter.HermesConnectionError, '0회'):
            adapter.run_verified_web_research('리스닝')
        ready.assert_called_once_with(require_web=True)

    @patch.object(adapter, 'check_ready', return_value='hermes-agent')
    @patch.object(adapter, '_call', return_value={
        'output':[{'type':'function_call','name':'web_search','call_id':'a'},
                  {'type':'function_call_output','call_id':'a','output':'{"success":false,"message":"quota"}'}]
    })
    def test_failed_tool_call_is_not_accepted(self, fake_call, ready):
        with self.assertRaisesRegex(adapter.HermesConnectionError, '성공한 응답은 0회'):
            adapter.run_verified_web_research('리스닝')

    @patch.object(adapter, 'check_ready', return_value='hermes-agent')
    @patch.object(adapter, '_call', return_value={
        'output':[{'type':'function_call','name':'web_search','call_id':'a'},
                  {'type':'function_call_output','call_id':'a','output':'success but no link'},
                  {'type':'message','role':'assistant','content':[{'type':'output_text','text':'완료'}]}]
    })
    def test_no_source_url_is_rejected(self, fake_call, ready):
        with self.assertRaisesRegex(adapter.HermesConnectionError, 'URL이 없습니다'):
            adapter.run_verified_web_research('리스닝')

    @patch.object(adapter, 'check_ready', return_value='hermes-agent')
    @patch.object(adapter, '_call', return_value={
        'output':[{'type':'function_call','name':'web_search','call_id':'a'},
                  {'type':'function_call_output','call_id':'a','output':'https://dictionary.cambridge.org/grammar/'},
                  {'type':'message','role':'assistant','content':[{'type':'output_text','text':'찾았음'}]}]
    })
    def test_actual_tool_and_source_url_pass(self, fake_call, ready):
        r = adapter.run_verified_web_research('리스닝')
        self.assertEqual(r['web_attempted'],1)
        self.assertEqual(r['web_completed'],1)
        self.assertIn('cambridge',r['sources'][0]['url'])

class BrowserResearchTests(unittest.TestCase):
    @patch.object(adapter, 'check_ready', return_value='hermes-agent')
    @patch.object(adapter, '_call', return_value={
        'output': [
            {'type':'function_call', 'name':'browser_navigate','call_id':'n',
             'arguments':'{"url":"https://dictionary.cambridge.org/grammar"}'},
            {'type':'function_call_output','call_id':'n','output':'Navigated to Cambridge'},
            {'type':'function_call','name':'browser_snapshot','call_id':'s'},
            {'type':'function_call_output','call_id':'s','output':'Grammar entries visible'},
            {'type':'message','role':'assistant','content':[{'type':'output_text','text':'페이지 확인'}]},
        ]
    })
    def test_public_browser_navigation_and_snapshot_count_as_research(self, call, ready):
        result=adapter.run_verified_web_research('전치사')
        self.assertEqual(result['web_completed'],2)
        self.assertEqual(result['sources'][0]['url'], 'https://dictionary.cambridge.org/grammar')

    @patch.object(adapter, 'check_ready', return_value='hermes-agent')
    @patch.object(adapter, '_call', return_value={
        'output': [
            {'type':'function_call', 'name':'browser_navigate','call_id':'n',
             'arguments':'{"url":"file:///opt/data/.env"}'},
            {'type':'function_call_output','call_id':'n','output':'opened'},
            {'type':'function_call', 'name':'browser_snapshot','call_id':'s'},
            {'type':'function_call_output','call_id':'s','output':'text'}]
    })
    def test_file_scheme_never_qualifies_as_external_evidence(self, call, ready):
        with self.assertRaisesRegex(adapter.HermesConnectionError, '출처 URL'):
            adapter.run_verified_web_research('전치사')

    @patch.object(adapter, 'check_ready', return_value='hermes-agent')
    @patch.object(adapter, '_call', return_value={
        'output':[{'type':'function_call','name':'browser_navigate','call_id':'n',
                   'arguments':'{"url":"https://example.com"}'},
                  {'type':'function_call_output','call_id':'n','output':'navigated'}]
    })
    def test_navigate_without_snapshot_is_unverified(self, call, ready):
        with self.assertRaisesRegex(adapter.HermesConnectionError, '출처 URL'):
            adapter.run_verified_web_research('전치사')

if __name__ == '__main__': unittest.main()
