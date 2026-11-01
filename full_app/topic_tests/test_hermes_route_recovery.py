"""Regression: a single malformed Hermes route must not waste otherwise sound research."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from topic_experiment import (HermesTopicRouteError, normalize_strategy_route,
                              parse_hermes_topics, execute_topic_experiment)
from topic_tests.test_topic_comparison import demo_topics, fake_pipeline


class HermesRouteRecoveryTests(unittest.TestCase):
    def test_only_unambiguous_route_typography_is_normalized(self):
        for raw, expected in [
            ('승자 심화', '승자 심화'), (' 승자심화 ', '승자 심화'),
            ('인접  확장', '인접 확장'), ('`인접 확장`', '인접 확장'),
            ('신규실험형', '신규 실험'), ('인접 확장 전략', '인접 확장'),
        ]:
            self.assertEqual(normalize_strategy_route(raw), expected)
        for raw in ['', None, [], '무조건 성공', '후속 콘텐츠', '병원영어']:
            self.assertEqual(normalize_strategy_route(raw), '')
        items = demo_topics()
        items[1]['strategy_route'] = '인접 확장 전략'
        topics, warnings = parse_hermes_topics(json.dumps({'topics': items}, ensure_ascii=False),
                                              ['https://example.org/article'], require_ranking=True)
        self.assertEqual(topics[1]['전략경로'], '인접 확장')
        self.assertTrue(any('기존 성공 영상과의 연결' in w for w in warnings))

    def test_missing_route_recovered_without_changing_titles_ranking_or_citations(self):
        with tempfile.TemporaryDirectory() as td:
            pipe = fake_pipeline(td)
            items = demo_topics()
            items[1].pop('strategy_route')
            items[1]['strategy_reason'] = '기존 어순 영상의 활용을 실제 대화로 확장'
            first = '<TOPIC_JSON>' + json.dumps({'topics': items}, ensure_ascii=False) + '</TOPIC_JSON>'
            repair = json.dumps({'routes': [{'index': 2, 'strategy_route': '인접 확장',
                                             'evidence_urls': ['https://not-allowed.example.com']}]}, ensure_ascii=False)
            web = {'web_attempted': 1, 'web_completed': 1,
                   'sources': [{'url': 'https://example.org/article', 'title': 'Observed'}],
                   'tool_trace': [], 'report': 'web search returned source'}
            with patch('topic_experiment.check_ready', return_value='hermes-agent'), \
                 patch('topic_experiment.run_verified_web_research', return_value=web) as search, \
                 patch('topic_experiment.run_hermes_critic', side_effect=[{'report': first}, {'report': repair}]) as writer:
                result = execute_topic_experiment(pipe, [{'추천주제': 'A 검증 주제'}])
            self.assertEqual(result['status'], 'TOPICS_READY')
            self.assertEqual(len(result['b_topics']), 3)
            self.assertEqual(writer.call_count, 2)
            search.assert_called_once()
            self.assertEqual(result['b_topics'][1]['전략경로'], '인접 확장')
            self.assertEqual(result['b_topics'][1]['추천주제'], items[1]['topic'])
            self.assertEqual(result['b_topics'][1]['추천우선순위'], 2)
            self.assertEqual(result['b_topics'][1]['검증출처URL'], ['https://example.org/article'])
            self.assertTrue(any('추가 검토 후 보정' in w for w in result['warnings']))
            dest = Path(result['run_folder'])
            self.assertEqual((dest / 'hermes_raw_topics.txt').read_text(encoding='utf-8'), first)
            self.assertEqual((dest / 'hermes_strategy_route_repair.txt').read_text(encoding='utf-8'), repair)
            self.assertTrue((dest / 'hermes_corrected_topics.json').is_file())
            self.assertEqual(json.loads((dest / 'manifest.json').read_text(encoding='utf-8'))['status'], 'COMPLETE')

    def test_invalid_repair_still_blocks_b_and_preserves_a(self):
        with tempfile.TemporaryDirectory() as td:
            pipe = fake_pipeline(td)
            items = demo_topics()
            items[1]['strategy_route'] = '아무 경로나'
            first = json.dumps({'topics': items}, ensure_ascii=False)
            web = {'web_attempted': 1, 'web_completed': 1,
                   'sources': [{'url': 'https://example.org/article'}], 'tool_trace': [], 'report': 'found'}
            with patch('topic_experiment.check_ready', return_value='hermes-agent'), \
                 patch('topic_experiment.run_verified_web_research', return_value=web), \
                 patch('topic_experiment.run_hermes_critic', side_effect=[
                     {'report': first}, {'report': '{"routes":[{"index":2,"strategy_route":"사실 없음"}]}'}]) as writer:
                with self.assertRaisesRegex(RuntimeError, '전략 경로 보정 응답도 유효하지'):
                    execute_topic_experiment(pipe, [{'추천주제': 'A 기존 주제'}])
            self.assertEqual(writer.call_count, 2)
            dest = next((Path(td) / 'topic_experiments').iterdir())
            self.assertTrue((dest / 'baseline_a.json').is_file())
            self.assertTrue((dest / 'hermes_raw_topics.txt').is_file())
            self.assertFalse((dest / 'hermes_topics_b.json').exists())
            self.assertEqual(json.loads((dest / 'manifest.json').read_text(encoding='utf-8'))['status'], 'FAILED')

    def test_unknown_route_without_correction_is_not_silently_accepted(self):
        items = demo_topics()
        items[1]['strategy_route'] = '아무 경로나'
        with self.assertRaises(HermesTopicRouteError):
            parse_hermes_topics(json.dumps({'topics': items}, ensure_ascii=False), [])


if __name__ == '__main__':
    unittest.main()
