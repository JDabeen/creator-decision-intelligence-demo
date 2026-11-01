"""Regression checks: benchmark opt-in and closed script endings."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from benchmark_reference import make_benchmark_reference, SCRIPT_CLOSING_GUIDE
from closing_quality import ending_warnings
from critic_agent import ScriptCriticAgent
from yra_tools.llm_tools import LLMTools


class CaptureCache:
    def __init__(self):
        self.calls = []

    def structured_response(self, namespace, system_prompt, user_prompt, schema):
        self.calls.append((namespace, system_prompt, user_prompt, schema))
        return {}, {}, False


class FakeResponses:
    def __init__(self):
        self.last = {}

    def create(self, **kwargs):
        self.last = kwargs
        return SimpleNamespace(output_text="비평 완료", usage=SimpleNamespace(input_tokens=12, output_tokens=8, total_tokens=20))


class TestBenchmarkClosing(unittest.TestCase):
    def setUp(self):
        self.ref = make_benchmark_reference("시청자가 바로 한 문장 완성하는 점 참고")
        self.settings = SimpleNamespace(llm_model="test-model", channel_profile="우리 영어 채널", content_design_principles="정확하고 간단히")
        self.cache = CaptureCache()
        self.writer = LLMTools(self.cache, self.settings, None)

    def test_benchmark_is_limited_to_public_metadata(self):
        self.assertEqual(self.ref["channel_id"], "UCTw50WTknLa1G6m48kkkEhw")
        self.assertIn("Transcript", self.ref["evidence_limit"])
        self.assertIn("2026-10-31", self.ref["verified_as_of"])
        self.assertNotIn("실제 조회수", json.dumps(self.ref, ensure_ascii=False))

    def test_draft_a_and_final_revision_require_educational_closure(self):
        self.writer.write_script({}, {}, {}, pd.DataFrame(columns=["제목", "텍스트"]), {})
        self.assertIn("댓글을 달라고", self.cache.calls[-1][2])
        self.writer.revise_script({"마무리":"댓글 달아주세요"}, "끝을 고쳐줘")
        self.assertIn("첫 15초", self.cache.calls[-1][2])

    def test_draft_b_has_opt_in_benchmark(self):
        self.writer.write_draft_b({}, "비평", [], {}, benchmark_reference=self.ref)
        self.assertIn("180도 스피킹", self.cache.calls[-1][2])
        self.assertIn("실제 Transcript", self.cache.calls[-1][2])
        self.assertIn("댓글을 달라고", self.cache.calls[-1][2])
        self.writer.write_draft_b({}, "비평", [], {}, benchmark_reference=None)
        self.assertNotIn("180도 스피킹", self.cache.calls[-1][2])
        self.assertIn("댓글을 달라고", self.cache.calls[-1][2])

    def test_critic_web_free_is_bounded_and_opt_in(self):
        responses = FakeResponses()
        client = SimpleNamespace(responses=responses)
        with patch.dict("os.environ", {"YRA_CRITIC_WEB_SEARCH": "0"}):
            critic = ScriptCriticAgent(client, self.settings)
        critic.run({}, {}, backend="openai", revision_mode="polish", benchmark_reference=self.ref)
        self.assertIn("채널 소개/영상 제목", responses.last["instructions"])
        self.assertIn("180도 스피킹", responses.last["input"])
        critic.run({}, {}, backend="openai", revision_mode="polish")
        self.assertNotIn("180도 스피킹", responses.last["input"])
        self.assertIn("마무리", responses.last["instructions"])

    def test_closing_linter_flags_open_ending_not_normal_ending(self):
        self.assertTrue(ending_warnings({"마무리":"오늘 배운 내용이 궁금하면 댓글 달아 주세요."}))
        self.assertEqual([], ending_warnings({"마무리":"이제 짧은 문장으로 질문에 대답하고 한 번 더 이어 갈 수 있습니다. 오늘은 그 세 단계만 실제 대화에 적용해보세요. 여기까지입니다."}))

    def test_ui_final_no_longer_requires_comment_or_feedback(self):
        from pathlib import Path
        app_source = (Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
        self.assertIn("final_script_direct_confirm", app_source)
        self.assertIn("[\"Draft B\", \"Draft A\"]", app_source)
        self.assertIn("최종 원고 선택", app_source)
        self.assertIn('"cached": True', app_source)


if __name__ == "__main__":
    unittest.main()
