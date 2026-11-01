"""Bounded real-search recovery in the topic stage; all APIs mocked."""
import json
import tempfile
import unittest
from unittest.mock import patch
from topic_experiment import execute_topic_experiment
from topic_tests.test_topic_comparison import fake_pipeline, demo_topics


def message(url):
    topics = demo_topics()
    for topic in topics:
        topic['evidence_urls'] = [url]
    return {'report': '<TOPIC_JSON>' + json.dumps({'topics': topics}, ensure_ascii=False) + '</TOPIC_JSON>'}


def research(url):
    return {'web_attempted': 1, 'web_completed':1, 'sources':[{'url':url, 'title':'Observed'}],
            'tool_trace':[{'tool':'web_search', 'status':'도구 응답 확인'}], 'report':'External discovery'}


class RetryTests(unittest.TestCase):
    def test_second_search_only_when_first_citation_is_missing(self):
        with tempfile.TemporaryDirectory() as td:
            pipe = fake_pipeline(td)
            with patch('topic_experiment.check_ready', return_value='hermes-agent'), \
                 patch('topic_experiment.run_verified_web_research', side_effect=[
                     research('https://www.youtube.com/watch?v=first'),
                     research('https://www.youtube.com/watch?v=second')]) as search, \
                 patch('topic_experiment.run_hermes_critic', side_effect=[
                     message('https://unseen.example.com/unknown'),
                     {'report': json.dumps({'citations': [
                         {'topic_index':i, 'source_ids':[2], 'reason':'Observed relevant source'}
                         for i in (1,2,3)]})}]) as write:
                report=execute_topic_experiment(pipe, [{'추천주제':'기존 A'}])
            self.assertEqual(search.call_count, 2)
            self.assertEqual(write.call_count, 2)
            self.assertEqual(report['web_verified_calls'], 2)
            self.assertEqual(report['web_source_count'], 2)
            self.assertEqual(report['b_topics'][0]['증거상태'], '웹 도구에서 링크 발견 · 주제 수요 미검증')
            self.assertNotIn('기존 A', write.call_args.args[1])

    def test_no_citations_after_second_search_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            pipe=fake_pipeline(td)
            with patch('topic_experiment.check_ready', return_value='hermes-agent'), \
                 patch('topic_experiment.run_verified_web_research', side_effect=[
                     research('https://www.youtube.com/watch?v=first'),
                     research('https://www.youtube.com/watch?v=second')]), \
                 patch('topic_experiment.run_hermes_critic', return_value=message('https://fake.example.com')):
                with self.assertRaisesRegex(RuntimeError,'모두 실제 조사 링크'):
                    execute_topic_experiment(pipe, [{'추천주제':'기존 A'}])


if __name__ == '__main__': unittest.main()
