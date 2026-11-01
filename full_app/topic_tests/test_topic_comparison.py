import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from topic_experiment import (freeze_shared_evidence, hermes_topic_prompt,
                              parse_hermes_topics, execute_topic_experiment,
                              save_selection, load_latest_topic_comparison)


def demo_topics():
    return [
        dict(topic=f'중년을 위한 영어 말하기 고민 {i}', viewer_problem='문장 순서가 헷갈린다',
             market_reason='관련 영상이 조회됐다. 수요 자체는 미검증',
             channel_gap='기존 설명과 중복 여부 미검증', differentiation='짧은 비교',
             risk='성과 불확실', search_query='영어 어순 학습',
             goal='Pulling', strategy_route='신규 실험', strategy_reason='외부 수요 가설', anchor_video_ids=[], evidence_urls=['https://example.org/article'],
             priority_rank=i, ranking_reason=f'이것은 {i}순위 시장/채널 근거', relative_tradeoff=f'후보 {i}의 비교 기회비용')
        for i in range(1, 4)
    ]


def fake_pipeline(root):
    import pandas as pd
    return SimpleNamespace(
        data_root=root,
        last_home_scout_candidates=pd.DataFrame([
            {'video_id':'abc123', '제목':'영어 어순', '조회수':12000, '채널':'A',
             '영상링크':'https://www.youtube.com/watch?v=abc123'},
            {'video_id':'def456', '제목':'영어 회화', '조회수':30000, '채널':'B',
             '영상링크':'https://www.youtube.com/watch?v=def456'},
            {'video_id':'ghi789', '제목':'생활 발음', '조회수':22000, '채널':'C',
             '영상링크':'https://www.youtube.com/watch?v=ghi789'}]),
        last_home_recent_candidates=pd.DataFrame(),
        last_home_global_candidates=pd.DataFrame(),
        my_catalog_df=pd.DataFrame([{'video_id':'mine01','제목':'어순 설명','조회수':60000}]),
        my_content_df=pd.DataFrame([{'video_id':'mine01','제목':'어순 설명','전체대본':'나의 과거 공개 영상 설명'}]),
    )


class TopicFirstTests(unittest.TestCase):
    def test_evidence_has_channel_and_observations_but_not_A_recs_or_draft(self):
        with tempfile.TemporaryDirectory() as td:
            pipe = fake_pipeline(td)
            pipe.private_A_rec='SUPER_SECRET_A_RANKING'
            pipe.draft_a='SUPER_SECRET_A_SCRIPT'
            evidence, warnings=freeze_shared_evidence(pipe)
            dump=json.dumps(evidence,ensure_ascii=False)
            self.assertIn('나의 과거 공개 영상 설명',dump)
            self.assertIn('영어 어순',dump)
            self.assertNotIn('SUPER_SECRET_A',dump)
            self.assertEqual(warnings,[])
            inst, prompt=hermes_topic_prompt(evidence,{'web_completed':2, 'sources':[{'url':'https://example.org/article'}]})
            self.assertNotIn('SUPER_SECRET_A',prompt)
            self.assertIn('대본을 쓰지 마라',inst)

    def test_strict_topics_parsing_and_citation_allowlist(self):
        text='<TOPIC_JSON>'+json.dumps({'topics':demo_topics()},ensure_ascii=False)+'</TOPIC_JSON>'
        topics,warnings=parse_hermes_topics(text,['https://example.org/article'])
        self.assertEqual(len(topics),3)
        self.assertEqual(warnings,[])
        self.assertEqual(topics[0]['검증출처URL'],['https://example.org/article'])
        data=demo_topics()
        data[0]['evidence_urls']=['https://unseen.example.com/bogus']
        topics, warnings=parse_hermes_topics('<TOPIC_JSON>'+json.dumps({'topics':data},ensure_ascii=False)+'</TOPIC_JSON>', ['https://example.org/article'])
        self.assertEqual(topics[0]['검증출처URL'],[])
        self.assertIn('미확보',topics[0]['증거상태'])
        self.assertTrue(warnings)

    def test_invalid_or_missing_topic_does_not_pass(self):
        with self.assertRaises(ValueError):
            parse_hermes_topics('{"topics":[{"topic":"제목"}]}', ['https://example.org/article'])
        with self.assertRaises(ValueError):
            parse_hermes_topics('검색했습니다. 증거가 있습니다.', ['https://example.org/article'])

    def test_full_success_captures_human_decision(self):
        with tempfile.TemporaryDirectory() as td:
            pipe=fake_pipeline(td)
            a=[{'추천주제':'새로운 주제', '추천근거요약':'조회수'}]
            web={'web_attempted':2,'web_completed':1,'sources':[{'url':'https://example.org/article','title':'Source'}],
                 'tool_trace':[{'tool':'web_search','status':'도구 응답 확인'}], 'report':'경쟁 영상 근거'}
            hermes='<TOPIC_JSON>'+json.dumps({'topics':demo_topics()},ensure_ascii=False)+'</TOPIC_JSON>'
            with patch('topic_experiment.check_ready',return_value='hermes-agent'), \
                 patch('topic_experiment.run_verified_web_research',return_value=web) as search, \
                 patch('topic_experiment.run_hermes_critic',return_value={'report':hermes}) as write:
                result=execute_topic_experiment(pipe,a)
            self.assertEqual(result['status'],'TOPICS_READY')
            self.assertEqual(len(result['b_topics']),3)
            self.assertEqual(result['web_verified_calls'],1)
            search.assert_called_once()
            _, kwargs = search.call_args
            self.assertEqual(kwargs['purpose'],'youtube_topics')
            self.assertNotIn('새로운 주제',write.call_args.args[1])
            save_selection(result,result['b_topics'][0],'B')
            folder=Path(result['run_folder'])
            self.assertEqual(json.loads((folder/'manifest.json').read_text())['status'],'COMPLETE')
            self.assertEqual(json.loads((folder/'human_selection.json').read_text())['chosen_source'],'B')
            self.assertTrue((folder/'evidence.json').is_file())
            resumed=load_latest_topic_comparison(td)
            self.assertEqual(resumed['b_topics'][0]['추천주제'], result['b_topics'][0]['추천주제'])
            self.assertEqual(resumed['a_topics'][0]['추천주제'], '새로운 주제')

    def test_web_failure_is_fail_closed_and_preserves_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            pipe=fake_pipeline(td)
            with patch('topic_experiment.check_ready',return_value='hermes-agent'), \
                 patch('topic_experiment.run_verified_web_research',side_effect=RuntimeError('웹 호출 0회')), \
                 patch('topic_experiment.run_hermes_critic') as writer:
                with self.assertRaisesRegex(RuntimeError,'웹 호출 0회'):
                    execute_topic_experiment(pipe,[{'추천주제':'기존 추천'}])
                writer.assert_not_called()
            files=list((Path(td)/'topic_experiments').glob('*/manifest.json'))
            self.assertEqual(len(files),1)
            self.assertEqual(json.loads(files[0].read_text())['status'],'FAILED')
            self.assertTrue((files[0].parent/'baseline_a.json').is_file())
            self.assertFalse((files[0].parent/'hermes_topics_b.json').exists())

if __name__=='__main__':
    unittest.main()
