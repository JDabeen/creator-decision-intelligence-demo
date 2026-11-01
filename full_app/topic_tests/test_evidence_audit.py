import json
import unittest
from topic_quality import public_source_url, assess_topic, audit_comparison
from topic_experiment import parse_hermes_topics


class EvidenceAuditTests(unittest.TestCase):
    def setUp(self):
        self.evidence = {
            'existing_channel_videos': [{'video_id': 'OWN1', '조회수': 60000, '제목':'영어 어순'}],
            'market_videos': {'domestic': [{'video_id':'MKT1', '제목':'영어 어순 설명', '조회수':30000}]},
        }
        self.web = {'sources':[{'url':'https://www.youtube.com/watch?v=MKT1'}]}

    def test_source_addresses_must_be_public_and_never_local(self):
        bad = ['http://youtube.com/watch?v=x', 'https://localhost/',
               'https://127.0.0.1/', 'https://169.254.169.254/latest/meta-data/',
               'https://host.docker.internal/', 'https://user:password@youtube.com/',
               'https://internal.local/', 'file:///etc/passwd',
               'https://192.168.1.15/', 'https://10.2.3.4/',
               'https://example.com:8080/']
        self.assertTrue(all(not public_source_url(v) for v in bad))
        self.assertTrue(public_source_url('https://www.youtube.com/watch?v=abc'))

    def test_a_has_market_api_evidence_but_no_guaranteed_demand(self):
        a = {'시장근거video_ids':['MKT1','invented'], '전략경로':'승자 심화',
             '근거내채널video_ids':['OWN1']}
        result = assess_topic(a, 'A', self.evidence)
        self.assertEqual(result['market_video_ids'],['MKT1'])
        self.assertEqual(result['status'],'시장 영상 연결')
        self.assertFalse(result['demand_confirmed'])
        self.assertIsNone(result['expected_views'])

    def test_a_source_outside_shared_slice_is_not_lost_or_called_same_input(self):
        a = {'시장근거상세': [{'video_id':'from_api_extra',
                            '영상링크':'https://www.youtube.com/watch?v=from_api_extra'}]}
        record = assess_topic(a, 'A', self.evidence)
        self.assertEqual(record['status'], '시장 영상 연결')
        self.assertEqual(record['a_only_market_video_ids'], ['from_api_extra'])
        self.assertTrue(any('공유' in v for v in record['limitations']))

    def test_b_urls_are_discovered_not_performance_proof(self):
        b = {'검증출처URL':['https://www.youtube.com/watch?v=MKT1'],
             '전략경로':'신규 실험'}
        result = assess_topic(b, 'B', self.evidence, self.web)
        self.assertEqual(result['status'],'조사 링크 확보')
        self.assertIn('수요', ''.join(result['limitations']))

    def test_hallucinated_b_links_never_validate(self):
        b = {'검증출처URL':['https://www.youtube.com/watch?v=fake'], '전략경로':'신규 실험'}
        result = assess_topic(b, 'B', self.evidence, self.web)
        self.assertEqual(result['status'],'직접 조사 근거 부족')
        self.assertEqual(result['tool_observed_urls'],[])

    def test_invalid_anchor_cannot_pass_as_proof(self):
        b = {'검증출처URL':[], '근거내채널video_ids':['HALLUCINATED'], '전략경로':'승자 심화'}
        result = assess_topic(b, 'B', self.evidence, self.web)
        self.assertFalse(result['channel_video_ids'])
        self.assertTrue(any('ID' in e for e in result['limitations']))

    def test_comparison_declares_non_experimental_design(self):
        report = audit_comparison([{'추천주제':'A'}], [{'추천주제':'B'}], self.evidence, self.web)
        self.assertEqual(len(report['a']),1)
        self.assertEqual(len(report['b']),1)
        self.assertIn('동일', report['comparison_kind'])


if __name__ == '__main__':
    unittest.main()
