import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from strategy_hub import StrategyStore, consult_strategy


class Frame:
    def to_dict(self, mode):
        assert mode == 'records'
        return [{"video_id":"baIZqF8thi0", "제목":"어순 설명", "업로드날짜":"2026-10-01",
                 "조회수":50, "좋아요":2, "댓글":1}]

class YouTube:
    calls=0
    def load_channel_catalog(self, handle):
        self.calls += 1
        return {"channel_id":"UCdemo", "channel_title":"demo", "videos":Frame()}

class BrokenYouTube:
    calls=0
    def load_channel_catalog(self, handle):
        self.calls += 1
        raise RuntimeError('quota')

class FakeResponses:
    def create(self, **kwargs):
        self.args = kwargs
        return type('Resp', (), {'output_text':'판단: 업로드 주기를 실험하라.'})()
class FakeClient:
    def __init__(self): self.responses=FakeResponses()

class StrategyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=StrategyStore(Path(self.tmp.name)/'YT_Channel_Strategy')
    def tearDown(self): self.tmp.cleanup()
    def test_separate_persistent_store(self):
        assert (self.store.root/'operating_principles.txt').exists()
        assert (self.store.root/'public_snapshots').exists()
        assert (self.store.root/'README_내_채널_전략_기록.txt').exists()
        same=StrategyStore(self.store.root)
        assert same.principles()==self.store.principles()
    def test_consultation_never_auto_adopted(self):
        a=self.store.add_consultation('주 1편?', '주 1편 실험', 'gpt')
        assert not self.store.decisions()
        assert '주 1편 실험' not in self.store.decision_context()
        assert self.store.accept_decision(a['id']) is True
        assert self.store.accept_decision(a['id']) is False
        assert len(self.store.decisions())==1
        assert '주 1편 실험' in StrategyStore(self.store.root).decision_context()
    def test_daily_auto_sync_and_history(self):
        youtube=YouTube(); day=datetime(2026,10,22,1,tzinfo=timezone.utc)
        first=self.store.sync_public(youtube,'@demo',clock=day)
        assert first['status']=='updated' and youtube.calls==1
        within=self.store.sync_public(youtube,'@demo',clock=day+timedelta(hours=2))
        assert within['status']=='cached' and youtube.calls==1
        next_day=self.store.sync_public(youtube,'@demo',clock=day+timedelta(days=1))
        assert next_day['status']=='updated' and youtube.calls==2
        assert len(self.store.snapshots())==2
        assert self.store.metrics_summary()['count']==1
        assert self.store.metrics_summary()['videos'][0]['views_change_since_previous_snapshot']==0
    def test_failed_sync_preserves_snapshot(self):
        day=datetime(2026,10,22,1,tzinfo=timezone.utc)
        self.store.sync_public(YouTube(),'@demo',clock=day)
        result=self.store.sync_public(BrokenYouTube(),'@demo',force=True,clock=day+timedelta(hours=1))
        assert result['status']=='error' and len(result['snapshot']['videos'])==1
        assert len(self.store.snapshots())==1
    def test_never_autolink_video(self):
        self.store.sync_public(YouTube(),'@demo')
        assert self.store.metrics_summary()['videos'][0]['linked_to_topic'] is False
        with self.assertRaises(ValueError): self.store.link_video('어순','invalid')
        self.store.link_video('어순','baIZqF8thi0')
        assert self.store.metrics_summary()['videos'][0]['linked_to_topic'] is True
    def test_advice_is_concise_not_false_reported_live(self):
        client=FakeClient()
        answer=consult_strategy(client,'gpt','주 1편이 좋을까?',self.store)
        assert '판단' in answer
        assert '실제' not in client.responses.args['input'][-25:]
        assert not self.store.conversations() # caller explicitly persists only after successful response
        assert '검색·비공개 YouTube Studio 데이터에 접근하지 않았다면' in client.responses.args['instructions']
    def test_strategic_user_principles_survive_reopen(self):
        self.store.set_principles('시그니처 형식 반복 여부를 3편으로 검증')
        assert '3편' in StrategyStore(self.store.root).principles()
        with self.assertRaises(ValueError): self.store.set_principles('a'*5001)

if __name__=='__main__': unittest.main()
