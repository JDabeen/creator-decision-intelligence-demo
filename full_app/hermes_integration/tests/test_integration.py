import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hermes_integration import adapter  # noqa
from hermes_integration.launcher import read_app_env, write_hermes_config  # noqa
from critic_agent import ScriptCriticAgent  # noqa
from config import Settings  # noqa


class MockGatewayHandler(BaseHTTPRequestHandler):
    requests = []
    active_tools = ['web_search', 'web_extract']
    toolset_shape = 'raw'

    def log_message(self, *args):
        pass

    def reply(self, status, obj):
        blob = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def do_GET(self):
        if self.headers.get('Authorization') != 'Bearer test-only-key':
            return self.reply(401, {'error': 'no auth'})
        if self.path == '/v1/models':
            return self.reply(200, {'data': [{'id': 'hermes-agent'}]})
        if self.path == '/v1/toolsets':
            rows = [{'name': 'web', 'enabled': True, 'tools': self.active_tools},
                    {'name': 'terminal', 'enabled': False, 'tools': ['terminal']}]
            if self.toolset_shape == 'wrapped':
                return self.reply(200, {'object': 'list', 'data': rows})
            if self.toolset_shape == 'bad':
                return self.reply(200, {'unexpected': rows})
            if self.toolset_shape == 'missing_tools':
                rows[0].pop('tools')
            return self.reply(200, rows)
        return self.reply(404, {})

    def do_POST(self):
        if self.headers.get('Authorization') != 'Bearer test-only-key':
            return self.reply(401, {})
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.requests.append(data)
        if self.path == '/v1/responses':
            return self.reply(200, {'output': [
                {'type': 'function_call', 'name': 'web_search'},
                {'type': 'function_call_output', 'output': 'See https://dictionary.cambridge.org/dictionary/english/been'},
                {'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': '유지해야 할 것: 정확한 표현. 개선할 점: 사례 보강.'}]}
            ], 'usage': {'input_tokens': 20, 'output_tokens': 30, 'total_tokens': 50}})
        return self.reply(404, {})


class HermesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), MockGatewayHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def setUp(self):
        MockGatewayHandler.requests = []
        MockGatewayHandler.active_tools = ['web_search', 'web_extract']
        MockGatewayHandler.toolset_shape = 'raw'
        self.patch_url = patch.object(adapter, 'DEFAULT_URL', f'http://127.0.0.1:{self.server.server_port}')
        self.patch_key = patch.dict(os.environ, {'YRA_HERMES_API_KEY': 'test-only-key'})
        self.patch_url.start()
        self.patch_key.start()

    def tearDown(self):
        self.patch_url.stop()
        self.patch_key.stop()

    def test_real_critic_adapter_mock_server(self):
        fake_client = object()  # Should never call OpenAI directly for Hermes mode
        result = ScriptCriticAgent(fake_client, Settings()).run(
            {'본문': 'I have been there.'},
            {'selected_candidate': {'주제': '현재완료'}, 'transcript_coverage': {'ratio': 0.8}},
            backend='hermes',
        )
        self.assertIn('개선할 점', result.report)
        self.assertEqual(result.model, 'Hermes Agent / hermes-agent')
        self.assertTrue(result.web_used)
        self.assertEqual(result.usage['total_tokens'], 50)
        self.assertIn('dictionary.cambridge.org', result.sources[0]['url'])
        prompt = MockGatewayHandler.requests[0]
        self.assertIn('I have been there.', prompt['input'])
        self.assertNotIn('OPENAI_API_KEY', prompt['input'])
        self.assertEqual(prompt['store'], False)

    def test_api_toolsets_data_wrapper_supported(self):
        # Current Hermes versions can return an OpenAI list envelope.
        MockGatewayHandler.toolset_shape = 'wrapped'
        self.assertEqual(adapter.check_ready(), 'hermes-agent')

    def test_wrapped_unsafe_tools_still_blocked(self):
        MockGatewayHandler.toolset_shape = 'wrapped'
        MockGatewayHandler.active_tools = ['web_search', 'terminal', 'write_file']
        with self.assertRaisesRegex(adapter.HermesConnectionError, '격리 정책 위반'):
            adapter.check_ready()

    def test_unexpected_toolset_shape_fails_closed(self):
        MockGatewayHandler.toolset_shape = 'bad'
        with self.assertRaisesRegex(adapter.HermesConnectionError, '응답 형식'):
            adapter.check_ready()

    def test_missing_active_tool_details_fails_closed(self):
        MockGatewayHandler.toolset_shape = 'missing_tools'
        with self.assertRaisesRegex(adapter.HermesConnectionError, '상세 목록'):
            adapter.check_ready()

    def test_unsafe_hermes_tools_fail_closed(self):
        MockGatewayHandler.active_tools = ['web_search', 'write_file']
        with self.assertRaisesRegex(adapter.HermesConnectionError, '격리 정책 위반'):
            adapter.check_ready()

    def test_browser_api_tools_allowed_inside_container(self):
        MockGatewayHandler.active_tools = ['web_search', 'web_extract', 'browser_navigate', 'browser_snapshot', 'browser_click']
        self.assertEqual(adapter.check_ready(require_web=True), 'hermes-agent')

    def test_official_hermes_browser_vault_tools_do_not_block_readiness(self):
        # Regression: the real gateway exposes these with the browser toolset;
        # this is a tool catalog compatibility check, NOT a vault permission grant.
        MockGatewayHandler.active_tools = [
            'web_search', 'web_extract', 'browser_navigate', 'browser_snapshot',
            'browser_vault_enter_code', 'browser_vault_fill', 'browser_vault_list',
            'browser_vault_save_login', 'browser_vault_unlock',
        ]
        self.assertEqual(adapter.check_ready(require_web=True), 'hermes-agent')

    def test_unknown_vault_tool_still_fails_closed(self):
        MockGatewayHandler.active_tools = [
            'web_search', 'browser_navigate', 'browser_vault_export_secrets',
        ]
        with self.assertRaisesRegex(adapter.HermesConnectionError, '격리 정책 위반'):
            adapter.check_ready(require_web=True)

    def test_browser_vault_without_browser_navigation_fails_closed(self):
        MockGatewayHandler.active_tools = ['web_search', 'browser_vault_list']
        with self.assertRaisesRegex(adapter.HermesConnectionError, '격리 정책 위반'):
            adapter.check_ready(require_web=True)

    def test_official_browser_bundle_does_not_allow_unsafe_host_tools(self):
        MockGatewayHandler.active_tools = [
            'web_search', 'browser_navigate', 'browser_snapshot',
            'browser_vault_list', 'terminal', 'write_file',
        ]
        with self.assertRaisesRegex(adapter.HermesConnectionError, '격리 정책 위반'):
            adapter.check_ready(require_web=True)

    def test_browser_never_enables_host_terminal(self):
        MockGatewayHandler.active_tools = ['browser_navigate', 'browser_snapshot', 'terminal']
        with self.assertRaisesRegex(adapter.HermesConnectionError, '격리 정책 위반'):
            adapter.check_ready(require_web=True)

    def test_model_list_requires_authentication(self):
        with patch.dict(os.environ, {'YRA_HERMES_API_KEY': 'wrong-token'}):
            with self.assertRaisesRegex(adapter.HermesConnectionError, '401'):
                adapter.check_ready()

    def test_explicit_error_no_silent_fallback(self):
        with patch.object(adapter, 'DEFAULT_URL', 'http://127.0.0.1:1'):
            with self.assertRaises(adapter.HermesConnectionError):
                adapter.run_hermes_critic('Test', 'Test')

    def test_config_safe_toolset(self):
        from tempfile import TemporaryDirectory
        from hermes_integration import launcher
        with TemporaryDirectory() as d, patch.object(launcher, 'HERMES_DIR', Path(d)):
            launcher.write_hermes_config('gpt-4.1')
            config = (Path(d) / 'config.yaml').read_text()
            self.assertIn('  api_server: [web, browser]', config)
            self.assertIn('    - terminal', config)
            self.assertIn('platform_toolsets:', config)
            self.assertIn('  provider: openai-api', config)
            self.assertNotIn('OPENAI_API_KEY=', config)
            launcher.write_hermes_config('gpt-4.1', browser_enabled=False)
            closed = (Path(d) / 'config.yaml').read_text()
            self.assertIn('  api_server: [web]', closed)
            self.assertIn('    - browser', closed)


if __name__ == '__main__':
    unittest.main()
