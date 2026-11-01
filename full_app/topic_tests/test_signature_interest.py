import json
import unittest
from urllib.parse import parse_qs, urlsplit
from pathlib import Path
from topic_interest import youtube_trends_url, format_hypothesis_status
from topic_experiment import hermes_topic_prompt, parse_hermes_topics


class SignatureInterestTests(unittest.TestCase):
    def test_google_trends_link_is_relative_youtube_search_not_automated_volume(self):
        u=youtube_trends_url('  영어   어순   ')
        data=parse_qs(urlsplit(u).query)
        self.assertEqual(data['geo'], ['KR'])
        self.assertEqual(data['gprop'], ['youtube'])
        self.assertEqual(data['q'], ['영어 어순'])
        with self.assertRaises(ValueError):
            youtube_trends_url('   ')

    def test_signature_status_is_never_a_validation_badge(self):
        self.assertIn('미검증', format_hypothesis_status({'반복형식가설':'비유→연습'}))
        self.assertIn('부족', format_hypothesis_status({}))

    def test_hermes_prompt_is_blind_and_separates_topic_and_format(self):
        instructions, body=hermes_topic_prompt({'existing_channel_videos': [{'제목':'어순','조회수':100}]}, {'sources': [], 'web_completed':0})
        self.assertIn('signature_format', instructions)
        self.assertIn('검색량', instructions)
        self.assertNotIn('SUPER_SECRET_DRAFT_A', body)

    def test_hermes_parser_accepts_signature_without_faking_demand(self):
        item={'topic':'한 문장으로 영어 어순 쉽게 이해하기','viewer_problem':'어순 혼란',
              'strategy_route':'승자 심화','signature_format':'상황→비유→5초 연습',
              'format_variation':'새 주어로 즉답','format_evidence_limit':'단일 히트라 원인 미확인'}
        payload='<TOPIC_JSON>'+json.dumps({'topics':[dict(item,topic=item['topic']+str(i)) for i in range(3)]},ensure_ascii=False)+'</TOPIC_JSON>'
        topics,warnings=parse_hermes_topics(payload,[])
        self.assertEqual(len(topics),3)
        self.assertEqual(topics[0]['반복형식가설'],'상황→비유→5초 연습')
        self.assertIn('원인 미확인',topics[0]['형식검증한계'])
        self.assertNotIn('검증',topics[0]['증거상태'].split(' · ')[0])

    def test_baseline_schema_keeps_format_hypotheses_required(self):
        text=(Path(__file__).resolve().parents[1]/'yra_tools'/'llm_tools.py').read_text(encoding='utf-8')
        self.assertIn('home_recommendations_v14_absolute_comment_actions',text)
        self.assertIn('"반복형식가설": {"type": "string"}',text)
        self.assertIn('"형식변주실험": {"type": "string"}',text)
        self.assertIn('"형식검증한계": {"type": "string"}',text)


if __name__ == '__main__':
    unittest.main()
