"""Offline evidence and tool-trace regression tests. No live API cost."""
from __future__ import annotations
import sys, unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from market_audit import build_market_audit, parse_topic_decision
from hermes_integration.adapter import _flatten_response
from critic_agent import ScriptCriticAgent
from config import Settings

class MarketTests(unittest.TestCase):
    def setUp(self):
        self.candidates = pd.DataFrame([
            {"video_id":"12345678901", "제목":"test A", "채널":"A", "조회수":50000, "채널배수":3.7},
            {"video_id":"abcdefghijk", "제목":"test B", "채널":"B", "조회수":10000, "채널배수":1.2},
        ])
        self.transcripts = pd.DataFrame([
            {"video_id":"12345678901", "대본상태":"성공"},
            {"video_id":"abcdefghijk", "대본상태":"IpBlocked"},
        ])

    def test_market_observations_preserve_real_numbers_and_provenance(self):
        audit=build_market_audit(self.candidates,self.transcripts,"English")
        self.assertEqual(audit['시장후보수'],2)
        self.assertEqual(audit['서로다른채널수'],2)
        self.assertEqual(audit['실제자막확보수'],1)
        self.assertEqual(audit['경쟁영상'][0]['채널배수'],3.7)
        self.assertFalse(audit['경쟁영상'][1]['원문확보'])
        self.assertIn('미래 조회수',audit['해석한계'])

    def test_new_topic_is_not_mistaken_for_validated_market(self):
        text='''<TOPIC_DECISION_JSON>{"action":"RESEARCH_NEW", "topic":"새 영어 주제", "reason":"현재 비교 근거가 약함", "confidence":"HIGH", "evidence_video_ids":["fake-id","12345678901"]}</TOPIC_DECISION_JSON>'''
        v=parse_topic_decision(text,{'12345678901'})
        self.assertTrue(v['valid'])
        self.assertEqual(v['action'],'RESEARCH_NEW')
        self.assertEqual(v['evidence_video_ids'],['12345678901'])
        self.assertIn('시장',v['warning'])

    def test_unstructured_decision_not_marked_as_verified(self):
        self.assertFalse(parse_topic_decision('주제는 좋아요',{'12345678901'})['valid'])
        self.assertFalse(parse_topic_decision('<TOPIC_DECISION_JSON>{bad}</TOPIC_DECISION_JSON>')['valid'])

    def test_web_attempt_is_not_success(self):
        reply={'output':[{'type':'function_call','name':'web_search','call_id':'c1','arguments':'{"query":"grammar"}'},
                         {'type':'function_call_output','call_id':'c1','status':'failed','output':'error: no provider'},
                         {'type':'message','role':'assistant','content':[{'type':'output_text','text':'검색했다는 말'}]}]}
        report,sources,used,trace,attempted,completed=_flatten_response(reply)
        self.assertEqual(report,'검색했다는 말')
        self.assertEqual(attempted,1)
        self.assertEqual(completed,0)
        self.assertFalse(used)
        self.assertEqual(sources,[])
        self.assertEqual(trace[0]['status'],'오류')

    def test_error_json_tool_result_is_not_counted_as_success(self):
        reply={'output':[{'type':'function_call','name':'web_search','call_id':'x'},
                         {'type':'function_call_output','call_id':'x','output':'{"error":"no TAVILY_API_KEY"}'}]}
        _,sources,used,trace,attempted,completed=_flatten_response(reply)
        self.assertFalse(used)
        self.assertEqual((attempted,completed),(1,0))
        self.assertEqual(trace[0]['status'],'오류')

    def test_missing_web_tool_result_is_never_counted_as_used(self):
        reply={'output':[{'type':'function_call','name':'web_search','call_id':'x'},
                         {'type':'message','role':'assistant','content':[{'type':'output_text','text':'검색 완료'}]}]}
        _,sources,used,trace,attempted,completed=_flatten_response(reply)
        self.assertFalse(used)
        self.assertEqual((attempted,completed),(1,0))
        self.assertEqual(trace[0]['status'],'응답 미확인')

    def test_web_success_requires_output(self):
        reply={'output':[{'type':'function_call','name':'web_search','call_id':'c1','arguments':'{"query":"prepositions"}'},
                         {'type':'function_call_output','call_id':'c1','output':'found https://dictionary.cambridge.org/grammar/'},
                         {'type':'message','role':'assistant','content':[{'type':'output_text','text':'done'}]}]}
        _,sources,used,trace,attempted,completed=_flatten_response(reply)
        self.assertEqual((attempted,completed),(1,1))
        self.assertTrue(used)
        self.assertEqual(len(sources),1)
        self.assertEqual(trace[0]['request'],'prepositions')

    def test_topic_audit_before_draft_no_claimed_success(self):
        # No real LLM calls and no file writes: ensure market snapshot is actually
        # forwarded into the topic-review job, not just shown decoratively.
        try:
            from pipeline import ResearchPipeline
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional runtime dependency missing in offline test environment: {exc.name}")
        pipeline=ResearchPipeline.__new__(ResearchPipeline)
        class FakeAgent:
            def run(self, draft, package, **kwargs):
                self.seen=package
                assert draft=={}
                assert kwargs['purpose']=='topic_only'
                return type('Result',(),{'report':'No structured verdict','web_attempted':0,'web_completed':0,'tool_trace':[],'warning':'No web'})()
        pipeline.critic_agent=FakeAgent()
        result=pipeline.review_topic_before_draft({
            'research_ready':True, 'content_candidates':[{'주제':'중급 영어'}],
            'candidate_df':self.candidates, 'transcript_df':self.transcripts,
            'analysis_df':pd.DataFrame([{'video_id':'12345678901','제목':'A','대본상태':'성공','전체대본':'This is a real transcript.'}]),
            'video_analysis_df':pd.DataFrame(),
        },0)
        self.assertEqual(pipeline.critic_agent.seen['market_audit']['시장후보수'],2)
        self.assertEqual(pipeline.critic_agent.seen['market_sources'].iloc[0]['텍스트'],'This is a real transcript.')
        self.assertFalse(result['verdict']['valid'])

if __name__=='__main__': unittest.main()
