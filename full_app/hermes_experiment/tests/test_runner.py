import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from hermes_experiment import runner
from storage import RunStore


def run_fixture():
    return {
        'query':'직관적 리스닝',
        'selected_candidate':{'주제':'영어 리스닝 이해'},
        'draft_a':{'오프닝':'오늘은 영어 리스닝을 해요', '파트별대본':[{'파트':'설명','대본':'소리를 들어요'}], '마무리':'내일 해요'},
        'market_audit':{'경쟁영상':[{'video_id':'abcdefghijk', '조회수': 18000}]},
        'transcript_coverage':{'ready':True},
    }

class BlindPilotTests(unittest.TestCase):
    def test_blind_writer_never_receives_draft_a_or_blueprint(self):
        data=run_fixture()
        data['draft_a']['오프닝']='PRIVATE_CURRENT_DRAFT_A_DO_NOT_SHOW'
        data['design_pack']={'hidden':'PRIVATE_A_BLUEPRINT'}
        data['experiment_evidence']={'market_audit':data['market_audit'],
                                     'market_sources':[{'video_id':'abcdefghijk','텍스트':'시장 근거'}],
                                     'my_sources':[{'video_id':'myvid123456','텍스트':'이전 내 영상 원문'}]}
        e, warnings=runner.freeze_evidence(data)
        instr,prompt=runner.blind_prompt(e,{'web_attempted':1,'web_completed':1,'sources':[{'url':'https://example.org','title':'example'}]})
        self.assertNotIn('PRIVATE_CURRENT_DRAFT_A_DO_NOT_SHOW', prompt)
        self.assertNotIn('PRIVATE_A_BLUEPRINT',prompt)
        self.assertIn('이전 내 영상 원문',prompt)
        self.assertIn('시장 근거',prompt)
        self.assertEqual(warnings,[])

    def test_old_run_warns_missing_evidence(self):
        e,w=runner.freeze_evidence(run_fixture())
        self.assertTrue(w)
        self.assertFalse(e['market_transcript_excerpts'])

    def test_judge_labels_are_blind_and_deterministic(self):
        e,_=runner.freeze_evidence(run_fixture())
        inst,prompt,labels=runner.eval_prompt(e,'A_STRING','B_STRING',runner.sha(e))
        self.assertIn('A_STRING',prompt)
        self.assertIn('B_STRING',prompt)
        self.assertEqual(set(labels.values()),{'Original A','Hermes B'})
        self.assertNotIn('Hermes B',prompt)
        self.assertNotIn('Original A',prompt)

    def test_dry_run_writes_manifest_without_api(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            runs=root/'runs';runs.mkdir()
            example=runs/'run1.json';example.write_text(json.dumps(run_fixture(),ensure_ascii=False),encoding='utf-8')
            with patch.object(runner,'runs_dir',return_value=runs), patch.object(runner,'run_verified_web_research') as web, patch.object(runner,'run_hermes_critic') as agent:
                dest=runner.execute(example,dry_run=True)
                self.assertTrue((dest/'evidence.json').exists())
                self.assertTrue((dest/'draft_a.md').exists())
                self.assertEqual(json.loads((dest/'manifest.json').read_text(encoding='utf-8'))['status'],'DRY_RUN_NO_API_CALLS')
                web.assert_not_called();agent.assert_not_called()

    def test_failed_live_web_stops_before_draft_b(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);runs=root/'runs';runs.mkdir()
            example=runs/'run1.json';example.write_text(json.dumps(run_fixture(),ensure_ascii=False),encoding='utf-8')
            with patch.object(runner,'runs_dir',return_value=runs), patch.object(runner,'check_ready',return_value='hermes-agent'),\
                 patch.object(runner,'run_verified_web_research',side_effect=RuntimeError('0회')),\
                 patch.object(runner,'run_hermes_critic') as agent:
                with self.assertRaisesRegex(RuntimeError,'0회'):
                    runner.execute(example)
                agent.assert_not_called()
                folders=list((root/'experiments').iterdir());self.assertEqual(len(folders),1)
                self.assertFalse((folders[0]/'draft_b_hermes.md').exists())
                self.assertEqual(json.loads((folders[0]/'manifest.json').read_text(encoding='utf-8'))['status'],'FAILED')

    def test_verified_workflow_returns_b_and_comparison(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);runs=root/'runs';runs.mkdir()
            example=runs/'run1.json';example.write_text(json.dumps(run_fixture(),ensure_ascii=False),encoding='utf-8')
            web={'web_attempted':1,'web_completed':1,'sources':[{'url':'https://bbc.co.uk','title':'BBC'}],
                 'report':'검증됨','tool_trace':[{'tool':'web_search'}]}
            with patch.object(runner,'runs_dir',return_value=runs),\
                 patch.object(runner,'check_ready',return_value='hermes-agent'),\
                 patch.object(runner,'run_verified_web_research',return_value=web),\
                 patch.object(runner,'run_hermes_critic',return_value={'report':'# 주제\n' + '검증된 데이터에 기반한 대본.'*35,'tool_trace':[]}),\
                 patch.object(runner,'independent_judge',return_value='# 비교\n두 대본 비교'):
                dest=runner.execute(example)
            self.assertTrue((dest/'draft_b_hermes.md').exists())
            self.assertIn('평가 라벨 공개', (dest/'comparison.md').read_text(encoding='utf-8'))
            manifest=json.loads((dest/'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['status'],'COMPLETE')
            self.assertTrue(manifest['live_web_verified'])
            self.assertTrue(manifest['judge_completed'])

    def test_runstore_saves_market_and_my_history_excerpts(self):
        import pandas as pd
        with tempfile.TemporaryDirectory() as d:
            store=RunStore(d)
            market=pd.DataFrame([{'video_id':'abc','제목':'경쟁 영상','텍스트':'시장 자막'}])
            mine=pd.DataFrame([{'video_id':'me1','제목':'예전 영상','텍스트':'예전 내 대본'}])
            market_analysis=pd.DataFrame([{'video_id':'abc','조회수':123}])
            package={'selected_candidate':{'주제':'해석 훈련'},'market_sources':market,
                     'my_sources':mine, 'relevant_market_analysis': market_analysis,
                     'market_audit': {'경쟁영상':[{'video_id':'abc','조회수':123}]}}
            p=store.save_a_product_run({'query':'해석 훈련'},package,run_fixture()['draft_a'])
            saved=json.loads(p.read_text(encoding='utf-8'))
            exp=saved['experiment_evidence']
            self.assertEqual(exp['my_sources'][0]['텍스트'],'예전 내 대본')
            self.assertEqual(exp['market_sources'][0]['텍스트'],'시장 자막')
            self.assertEqual(exp['market_audit']['경쟁영상'][0]['조회수'],123)

if __name__=='__main__':unittest.main()
