import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from strategy_hub import StrategyStore, consult_strategy

class FakeClient:
    class Responses:
        def create(self,**kw):
            self.last=kw
            return type('Result',(),{'output_text':'권고 결론: 자료 부족이니 보류.'})()
    def __init__(self): self.responses=self.Responses()

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=StrategyStore(Path(self.tmp.name)/'YT_Channel_Strategy')
    def tearDown(self): self.tmp.cleanup()
    def test_decision_logged_before_upload_and_deduplicated(self):
        rec={'추천주제':'어순 이어 말하기','추천검색어':'어순','전략경로':'승자 심화'}
        one=self.store.record_topic_choice(rec,'A',{'matched_videos':3},'case_01')
        self.assertEqual(one['prior_at_decision']['status'],'INSUFFICIENT')
        self.assertEqual(one['outcome_status'],'UNOBSERVED')
        two=self.store.record_topic_choice(rec,'A',{'matched_videos':3},'case_01')
        self.assertEqual(two['id'],one['id'])
        self.assertEqual(len(StrategyStore(self.store.root).topic_choices()),1)
        self.assertEqual(self.store.forecast_context()['past_decision_outcomes']['observed_28d'],0)
    def test_critical_prompt_does_not_claim_search(self):
        client=FakeClient()
        answer=consult_strategy(client,'gpt','내가 좋아하는 주제가 더 잘된다',self.store)
        self.assertIn('자료 부족',answer)
        instructions=client.responses.last['instructions']
        self.assertIn('동조하는 상담원이 아니다',instructions)
        self.assertIn('검색 횟수',instructions)
        self.assertIn('N<8',instructions)
        self.assertIn('outcome_calibration_and_sample_size',client.responses.last['input'])

if __name__=='__main__': unittest.main()
