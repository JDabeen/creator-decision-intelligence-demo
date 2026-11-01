"""UI regression checks: progressive disclosure without changing pipeline decisions."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'app.py').read_text(encoding='utf-8')
TREE = ast.parse(SRC)
FUNCS = {node.name: node for node in TREE.body if isinstance(node, ast.FunctionDef)}


def function_source(name):
    node = FUNCS[name]
    return '\n'.join(SRC.splitlines()[node.lineno - 1:node.end_lineno])


class MinimalProductUITests(unittest.TestCase):
    def test_original_neutral_theme_not_blue(self):
        css = SRC.split('<style>', 1)[1].split('</style>', 1)[0]
        self.assertIn('--cdi-bg:#101112', css)
        self.assertNotIn('--cdi-accent', css)
        self.assertNotIn('#0d1117', css)

    def test_main_screen_has_one_job(self):
        find = function_source('render_stage_find')
        self.assertIn('내 채널에 맞는 다음 주제 찾기', find)
        self.assertIn('신규 유입', find)
        self.assertIn('신뢰 형성', find)
        self.assertIn('find_chat_form', find)
        self.assertNotIn('Pulling ·', find)
        self.assertNotIn('현재 단계 ·', find)
        self.assertNotIn('st.expander(', find)
        self.assertNotIn('render_flow_navigation()', SRC)

    def test_each_normal_stage_has_single_evidence_disclosure(self):
        for stage in ('render_stage_compare', 'render_stage_research', 'render_draft_workspace'):
            body = function_source(stage)
            self.assertEqual(body.count('with st.expander('), 1, stage)
            self.assertIn('with st.expander("판단 근거 · 데이터 보기")', body)
        critic = function_source('render_critic_agent_section')
        self.assertEqual(critic.count('with st.expander('), 1)  # details only after Draft B
        self.assertIn('        return\n\n    bundle =', critic)

    def test_actions_and_evidence_gates_remain(self):
        self.assertIn('pipeline.recommend_home(progress=cb)', SRC)
        self.assertIn('execute_topic_experiment(pipeline, recs, st.session_state.content_mode)', SRC)
        self.assertIn('research.get("research_ready", False)', SRC)
        self.assertIn('make_draft_from_candidate(chosen)', SRC)
        self.assertIn('pipeline.build_draft_b(', SRC)
        self.assertIn('final_script_direct_confirm', SRC)
        self.assertIn('ending_warnings(', SRC)


if __name__ == '__main__':
    unittest.main()
