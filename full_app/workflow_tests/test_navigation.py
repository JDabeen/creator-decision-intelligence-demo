import unittest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from workflow_ui import FLOW_STAGES, available_stages, topic_choices

class WorkflowTest(unittest.TestCase):
    def test_initial_only_discovery(self):
        self.assertEqual(available_stages({}), {"find"})
    def test_a_success_without_hermes_keeps_comparison_accessible(self):
        state={"home_recommendations":[{"추천주제":"test"}], "topic_comparison":None}
        self.assertEqual(available_stages(state), {"find", "compare"})
    def test_research_is_only_available_after_research_result(self):
        state={"home_recommendations":[{"추천주제":"test"}], "research":{"research_ready":False}}
        self.assertIn("research", available_stages(state))
        self.assertNotIn("draft", available_stages(state))
    def test_draft_stage_requires_generated_draft(self):
        state={"home_recommendations":[{"추천주제":"test"}], "research":{}, "draft_a_bundle":{"script":{}}}
        self.assertEqual(available_stages(state), set(FLOW_STAGES))
    def test_stage_order_is_unchanging(self):
        self.assertEqual(FLOW_STAGES, ("find", "compare", "research", "draft"))
    def test_choice_mapping_separates_a_and_b(self):
        a=[{"추천주제":"A topic 1"},{"추천주제":"A topic 2"}]
        b=[{"추천주제":"B topic 1"}]
        choices=topic_choices(a,b)
        self.assertEqual([c[0] for c in choices], ["A-1","A-2","B-1"])
        self.assertEqual(choices[2][2], "B")
        self.assertIs(choices[2][3], b[0])
    def test_bad_candidates_ignored(self):
        self.assertEqual(len(topic_choices([{},"bad",{"추천주제":""}],None)), 0)
    def test_keeps_three_max_per_source(self):
        x=[{"추천주제":str(i)} for i in range(7)]
        self.assertEqual(len(topic_choices(x,x)), 6)

class RoutingRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT / 'app.py').read_text(encoding='utf-8')
    def test_mutually_exclusive_screen_routes(self):
        self.assertIn('elif st.session_state.flow_stage == "compare":', self.source)
        self.assertIn('elif st.session_state.flow_stage == "research":', self.source)
        self.assertIn('render_stage_find()', self.source)
    def test_one_click_a_then_hermes(self):
        self.assertIn('pipeline.recommend_home(progress=cb)',self.source)
        self.assertIn('execute_topic_experiment(pipeline, recs, st.session_state.content_mode)', self.source)
        self.assertIn('Hermes 조사 재시도',self.source)
    def test_draft_not_automatically_generated_in_research(self):
        body=self.source.split('def render_stage_research():',1)[1].split('missing = [',1)[0]
        self.assertIn('if st.button("이 방향으로 대본 만들기"', body)
        self.assertIn('make_draft_from_candidate(chosen)',body)
    def test_no_stacked_research_after_comparison(self):
        route=self.source.split('if st.session_state.flow_stage == "draft"',1)[1].split('with st.sidebar:',1)[0]
        self.assertIn('elif st.session_state.flow_stage == "research":',route)
        self.assertNotIn('if st.session_state.research is not None:',route)

if __name__=='__main__': unittest.main()
