"""Regression for the 2026-10-31 Hermes-B '0 cited topics' failure."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from topic_experiment import (normalized_url, parse_hermes_topics,
                              execute_topic_experiment, repair_missing_topic_sources)
from topic_tests.test_topic_comparison import demo_topics, fake_pipeline


class HermesSourceRecoveryTests(unittest.TestCase):
    def test_youtube_same_video_canonical_equivalence_only(self):
        video = 'AaBbCcDdE12'
        variants = [
            f'https://www.youtube.com/watch?v={video}&t=40&utm_source=search',
            f'https://youtu.be/{video}?si=tracked',
            f'https://m.youtube.com/shorts/{video}',
            f'https://www.youtube.com/live/{video}?feature=share',
        ]
        self.assertEqual(len({normalized_url(x) for x in variants}), 1)
        self.assertNotEqual(normalized_url(variants[0]),
                            normalized_url('https://youtu.be/AaBbCcDdE13'))
        self.assertEqual(normalized_url('https://news.example.com/a?utm_campaign=x&lang=ko'),
                         normalized_url('https://news.example.com/a?lang=ko'))
        self.assertNotEqual(normalized_url('https://news.example.com/a?lang=ko'),
                            normalized_url('https://news.example.com/a?lang=en'))
        self.assertEqual(normalized_url('http://localhost/admin'), '')

    def test_matching_reuses_observed_url_not_model_supplied_variant(self):
        rows = demo_topics()
        rows[0]['evidence_urls'] = ['https://youtu.be/AaBbCcDdE12?si=share']
        found = 'https://www.youtube.com/watch?v=AaBbCcDdE12&t=10'
        parsed, errors = parse_hermes_topics(json.dumps({'topics': rows}, ensure_ascii=False),
                                             [found], require_ranking=True)
        self.assertEqual(parsed[0]['검증출처URL'], [found])
        self.assertFalse(parsed[1]['검증출처URL'])
        self.assertTrue(any('주제 2:' in s for s in errors))

    def test_citation_only_retry_keeps_topics_and_ranks(self):
        with tempfile.TemporaryDirectory() as td:
            pipe = fake_pipeline(td)
            original = demo_topics()
            for t in original:
                t['evidence_urls'] = []
            report = json.dumps({'topics': original}, ensure_ascii=False)
            first = {'web_attempted': 1, 'web_completed': 1, 'sources': [
                    {'title':'English lesson 1', 'url':'https://example.org/lesson1'}],
                    'tool_trace':[], 'report':'English lesson 1 examined'}
            second = {'web_attempted': 1, 'web_completed': 1, 'sources': [
                    {'title':'English lesson 2', 'url':'https://example.org/lesson2'}],
                    'tool_trace':[], 'report':'English lesson 2 examined'}
            repair = json.dumps({'citations': [
                {'topic_index':1, 'source_ids':[2], 'reason':'lesson 2 direct connection'},
                {'topic_index':2, 'source_ids':[1], 'reason':'lesson 1 direct connection'},
                {'topic_index':3, 'source_ids':[], 'reason':'none'},
            ]}, ensure_ascii=False)
            with patch('topic_experiment.check_ready', return_value='hermes-agent'), \
                 patch('topic_experiment.run_verified_web_research', side_effect=[first, second]) as search, \
                 patch('topic_experiment.run_hermes_critic', side_effect=[{'report':report}, {'report':repair}]) as agent:
                result = execute_topic_experiment(pipe, [{'추천주제':'A 추천 1'}])
            self.assertEqual(search.call_count, 2)
            self.assertEqual(agent.call_count, 2)
            self.assertEqual([x['추천주제'] for x in result['b_topics']], [x['topic'] for x in original])
            self.assertEqual([x['추천우선순위'] for x in result['b_topics']], [1,2,3])
            self.assertEqual([x['전략경로'] for x in result['b_topics']], ['신규 실험']*3)
            self.assertEqual(result['b_topics'][0]['검증출처URL'], ['https://example.org/lesson2'])
            self.assertEqual(result['b_topics'][1]['검증출처URL'], ['https://example.org/lesson1'])
            self.assertEqual(result['b_topics'][2]['검증출처URL'], [])
            saved = Path(result['run_folder'])
            self.assertEqual(json.loads((saved/'manifest.json').read_text())['b_grounded_topic_count'],2)
            self.assertTrue((saved/'hermes_citation_repair.txt').exists())
            self.assertTrue((saved/'hermes_source_match_diagnostic.json').exists())
            self.assertFalse((saved/'hermes_followup_raw_topics.txt').exists(), 'never rerun all three recommendations')

    def test_abstention_still_blocks_b_and_keeps_a(self):
        with tempfile.TemporaryDirectory() as td:
            original = demo_topics()
            for t in original:
                t['evidence_urls'] = []
            report = json.dumps({'topics':original}, ensure_ascii=False)
            web = {'web_attempted':1, 'web_completed':1, 'sources':[{'url':'https://example.org/anything'}],
                   'tool_trace':[], 'report':'found unrelated page'}
            repair = json.dumps({'citations':[
                {'topic_index':i,'source_ids':[], 'reason':'no topic match'} for i in (1,2,3)]})
            with patch('topic_experiment.check_ready', return_value='hermes-agent'), \
                 patch('topic_experiment.run_verified_web_research', return_value=web), \
                 patch('topic_experiment.run_hermes_critic', side_effect=[{'report':report}, {'report':repair}]):
                with self.assertRaisesRegex(RuntimeError, '실제 조사 링크와 연결되지'):
                    execute_topic_experiment(fake_pipeline(td), [{'추천주제':'A 추천 1'}])
            folder = next((Path(td)/'topic_experiments').iterdir())
            self.assertTrue((folder/'baseline_a.json').exists())
            self.assertFalse((folder/'hermes_topics_b.json').exists())
            self.assertEqual(json.loads((folder/'manifest.json').read_text())['b_grounded_topic_count'],0)
            self.assertEqual(json.loads((folder/'manifest.json').read_text())['status'],'FAILED')

    def test_unknown_ids_are_not_promoted_to_citations(self):
        with tempfile.TemporaryDirectory() as td:
            rows = demo_topics()
            for r in rows:
                r['evidence_urls'] = []
            report = json.dumps({'topics':rows}, ensure_ascii=False)
            web = {'sources':[{'url':'https://example.org/good'}]}
            bad = json.dumps({'citations':[
                {'topic_index':i, 'source_ids':[999], 'reason':'bogus'} for i in (1,2,3)]})
            with patch('topic_experiment.run_hermes_critic', return_value={'report':bad}):
                repaired, warning = repair_missing_topic_sources(report, web, Path(td))
            self.assertEqual(repaired,report)
            self.assertTrue(warning)

if __name__ == '__main__': unittest.main()
