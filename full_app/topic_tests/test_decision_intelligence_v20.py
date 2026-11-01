import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from decision_intelligence import market_observation, horizon_outcomes, channel_prior, selection_outcomes, evidence_for_comparison
from trend_provider import capture_topic_trends, lookup_term


def samples(n=9, days=(7,28)):
    videos = []
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    for i in range(n):
        pub = start+timedelta(days=i)
        videos.append((f'v{i:010d}', pub))
    snapshots = []
    for d in days:
        for vid, pub in videos:
            snapshots.append({'measured_at':(pub+timedelta(days=d)).isoformat(),
                              'videos':[{'video_id':vid, 'title':'어순',
                                         'published_date':pub.date().isoformat(),
                                         'views':(d * 100)+(int(vid[1:]) * 5)}]})
    return snapshots

class DecisionIntelligenceTests(unittest.TestCase):
    def test_no_retrospective_28_day_metrics(self):
        s = [{'measured_at':'2026-10-22T00:00:00+00:00','videos':[{'video_id':'v123',
            'published_date':'2026-07-01','views':100000}]}]
        self.assertFalse(horizon_outcomes(s,28))
        self.assertEqual(channel_prior(s,28)['status'],'INSUFFICIENT')
    def test_channel_prior_demands_sample_size(self):
        s=samples(8)
        self.assertEqual(channel_prior(s,28)['status'],'DESCRIPTIVE_BASELINE')
        self.assertEqual(channel_prior(samples(7),28)['status'],'INSUFFICIENT')
        self.assertEqual(channel_prior(s,28)['range'],[2807,2828])
    def test_selected_topic_not_auto_linked(self):
        choices=[{'topic':'어순','id':'abc'}]
        out=selection_outcomes(choices,[],samples(8))
        self.assertEqual(out['observed_28d'],0)
        out=selection_outcomes(choices,[{'topic':'어순','video_id':'v0000000001'}],samples(8))
        self.assertEqual(out['observed_28d'],1)
    def test_market_proxy_no_guess_search_volume(self):
        pool={'domestic':[{'video_id':'aa','제목':'어순 쉬운 훈련','조회수':4000},
                          {'video_id':'bb','제목':'어순 실전 문장','조회수':6000},
                          {'video_id':'cc','제목':'세계 뉴스','조회수':500}]}
        o=market_observation('어순 실전',pool)
        self.assertEqual(o['matched_videos'],2)
        self.assertEqual(o['median_cumulative_views'],5000)
        self.assertIn('not_search_volume',o['kind'])
        self.assertEqual(market_observation('무엇도없는주제',pool)['matched_videos'],0)
    def test_no_evidence_is_empty(self):
        self.assertEqual(evidence_for_comparison({'run_folder':'/missing'}),{})

class TrendsTests(unittest.TestCase):
    def setUp(self): self.temp=tempfile.TemporaryDirectory()
    def tearDown(self): self.temp.cleanup()
    def test_no_key_never_calls_network(self):
        def forbidden(*a): raise RuntimeError('should not call')
        value=capture_topic_trends([{'추천검색어':'영어 어순'}],[],self.temp.name, key='',fetcher=forbidden)
        self.assertEqual(value['status'],'NO_KEY')
    def test_paid_provider_cache_no_key_storage(self):
        called=[]
        def fake(params,key):
            called.append((params,key))
            queries=params['q'].split(',')
            return {'interest_over_time':{'timeline_data':[
                {'values':[{'query':q,'extracted_value':30+i+step} for i,q in enumerate(queries)]}
                for step in range(8)]}}
        a=[{'추천검색어':'영어 어순'},{'추천검색어':'기초 문법'},{'추천검색어':'리스닝 훈련'}]
        b=[{'추천검색어':'발음 교정'},{'추천검색어':'여행 영어'},{'추천검색어':'시제 연습'}]
        ts=datetime(2026,10,22,tzinfo=timezone.utc)
        r=capture_topic_trends(a,b,self.temp.name,key='SECRET_KEY',fetcher=fake,now=ts)
        self.assertEqual(r['status'],'MEASURED')
        self.assertEqual(len(r['batches']),2)
        self.assertEqual(len(called),2)
        self.assertIsNotNone(lookup_term(r,'시제 연습'))
        again=capture_topic_trends(a,b,self.temp.name,key='SECRET_KEY',fetcher=fake,now=ts+timedelta(days=1))
        self.assertEqual(again['status'],'MEASURED')
        self.assertEqual(len(called),2)
        saved=''.join(x.read_text(encoding='utf-8') for x in (Path(self.temp.name)/'trend_snapshots').glob('*.json'))
        self.assertNotIn('SECRET_KEY',saved)
        self.assertIn('배치',saved)
    def test_trend_provider_errors_are_not_fabricated(self):
        def bad(*a): return {'error':'quota exceeded'}
        r=capture_topic_trends([{'추천검색어':'영어 어순'}],[],self.temp.name,key='MOCK',fetcher=bad)
        self.assertEqual(r['status'],'ERROR')
        self.assertFalse(r['batches'])

if __name__=='__main__': unittest.main()
