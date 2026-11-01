"""Tests for the opt-in redesign path. All LLM calls are mocked."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from config import Settings
from critic_agent import ScriptCriticAgent
from yra_tools.llm_tools import LLMTools


class FakeCache:
    def __init__(self):
        self.key = ''
        self.prompt = ''
        self.system_prompt = ''

    def structured_response(self, key, system, prompt, schema):
        self.key, self.system_prompt, self.prompt = key, system, prompt
        return {'오프닝': '독립적인 신규 오프닝'}, {}, False


class RedesignTests(unittest.TestCase):
    def test_critic_prompt_is_independent_and_search_instructed(self):
        with patch('hermes_integration.adapter.run_hermes_critic') as send, \
             patch('hermes_integration.adapter.run_verified_web_research') as pre:
            pre.return_value = dict(report='검색 요약', sources=[{'url':'https://example.org/grammar', 'title':'Grammar'}],
                                    tool_trace=[{'tool':'web_search','status':'도구 응답 확인'}],
                                    web_attempted=1, web_completed=1, usage={})
            send.return_value = dict(report='연구', sources=[], model='Hermes Agent / hermes-agent',
                                     web_enabled=True, web_used=False, usage={}, warning='',
                                     tool_trace=[], web_attempted=0, web_completed=0)
            agent = ScriptCriticAgent(None, Settings())
            result = agent.run({'오프닝': 'A'}, {'selected_candidate': {'주제': '말하기'}},
                               backend='hermes', revision_mode='rebuild')
            self.assertEqual(result.report, '연구')
            instructions, payload = send.call_args.args
            self.assertIn('web_search', instructions)
            self.assertTrue(result.web_used)
            self.assertEqual(result.web_completed, 1)
            self.assertEqual(result.sources[0]['url'], 'https://example.org/grammar')
            self.assertIn('대안 콘셉트', instructions)
            self.assertIn('완전히 다른 교육 전개', payload)
            self.assertIn('"revision_mode": "rebuild"', payload)

    def test_writer_mode_changes_prompt_and_cache_id(self):
        cache = FakeCache()
        writer = LLMTools(cache, Settings(), None)
        writer.write_draft_b({'오프닝': 'A'}, 'Critic', [], {}, revision_mode='rebuild')
        self.assertEqual(cache.key, 'youtube_script_draft_b_v3_market_cognitive')
        self.assertIn('독립 재설계', cache.prompt)
        writer.write_draft_b({'오프닝': 'A'}, 'Critic', [], {}, revision_mode='polish')
        self.assertEqual(cache.key, 'youtube_script_draft_b_v1_agent_critic')

    def test_pipeline_threads_mode_in_source(self):
        content = (ROOT / 'pipeline.py').read_text(encoding='utf-8')
        self.assertIn('revision_mode=revision_mode', content)
        self.assertIn('"revision_mode": revision_mode', content)

    def test_ui_starts_with_summary_after_draft_b(self):
        content = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn('if st.session_state.draft_b_bundle is not None:', content)
        self.assertIn('render_critic_agent_section()\n        back, new = st.columns(2)', content)
        self.assertIn('변경요약', content)
        self.assertIn('### A/B 비교', content)
        self.assertIn('with st.expander("판단 근거 · 데이터 보기")', content)
        self.assertIn('st.download_button("최종 대본 다운로드', content)


if __name__ == '__main__':
    unittest.main()
