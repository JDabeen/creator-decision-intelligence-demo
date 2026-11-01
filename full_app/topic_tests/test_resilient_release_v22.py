"""Offline regression of actual failure modes: quota, cached evidence, key leaks and state."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from research_resilience import SearchQuotaExhausted, safe_error, source_video_ids
from evidence_charts import chart_observations, interest_bars
from strategy_hub import StrategyStore
from yra_tools.youtube_tools import YouTubeResearchTools
from research_resilience import source_video_ids as ids_from_sources


def isolated_research_pipeline_for_offline_test():
    """Execute the EXACT research_topic method AST without requiring paid SDKs."""
    import ast
    import pandas as pd
    script=(Path(__file__).resolve().parents[1] / 'pipeline.py').read_text(encoding='utf-8')
    module=ast.parse(script)
    source=next(x for x in module.body if isinstance(x,ast.ClassDef) and x.name=='ResearchPipeline')
    fn=next(x for x in source.body if isinstance(x,ast.FunctionDef) and x.name=='research_topic')
    stripped=ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')],level=0),
        ast.ClassDef(name='ResearchSubset',bases=[],keywords=[],body=[fn],decorator_list=[])],type_ignores=[])
    scope={'pd':pd, 'source_video_ids':ids_from_sources}
    exec(compile(ast.fix_missing_locations(stripped),'<pipeline-test>','exec'),scope)
    pipe=scope['ResearchSubset']()
    pipe._emit=lambda *a,**kw:None
    pipe._merge_market_maps=lambda *dfs:pd.concat([df for df in dfs if df is not None and not df.empty],ignore_index=True) \
        if any(df is not None and not df.empty for df in dfs) else pd.DataFrame()
    pipe._reference_filter_by_queries=lambda df,queries,max_rows=18:df.copy()
    pipe._transcript_coverage=lambda transcripts,n:{'total':n,'success':0,'cached_success':0,'ratio':0.,'ready':False,'blocked':False,'errors':[]}
    return pipe


class HTTPQuotaError(Exception):
    def __init__(self):
        self.resp = SimpleNamespace(status=429)
    def __str__(self):
        return "<HttpError 429 https://youtube.googleapis.com/youtube/v3/search?key=MOCK_SECRET_VALUE -- Quota exceeded for Search Queries per day>"


class SearchStub:
    def __init__(self, fail_after=0):
        self.calls = 0
        self.fail_after = fail_after
    def search(self):
        return self
    def list(self, **kwargs):
        return self
    def execute(self):
        self.calls += 1
        if self.fail_after and self.calls >= self.fail_after:
            raise HTTPQuotaError()
        return {'items': [{'id':{'videoId':'aaaaaaaaaaa'}}]}


class ReleaseTests(unittest.TestCase):
    def test_search_quota_error_does_not_expose_key(self):
        self.assertNotIn('MOCK_SECRET_VALUE', safe_error(HTTPQuotaError()))
        self.assertIn('할당량', safe_error(HTTPQuotaError()))
        self.assertNotIn('SECRET_VALUE', safe_error(ValueError('api_key=SECRET_VALUE')))

    def test_cached_queries_skip_new_search_calls(self):
        with tempfile.TemporaryDirectory() as td:
            stub=SearchStub()
            worker=YouTubeResearchTools(stub, SimpleNamespace(),search_cache_root=td)
            self.assertEqual(worker.search_video_ids('영어 어순'), ['aaaaaaaaaaa'])
            self.assertEqual(stub.calls,2)
            worker2=YouTubeResearchTools(stub, SimpleNamespace(),search_cache_root=td)
            self.assertEqual(worker2.search_video_ids('영어 어순'), ['aaaaaaaaaaa'])
            self.assertEqual(stub.calls,2)
            saved=list(Path(td).glob('*.json'))
            self.assertEqual(len(saved),2)
            self.assertNotIn('AIza', ''.join(p.read_text() for p in saved))

    def test_first_search_429_blocks_subsequent_requests(self):
        with tempfile.TemporaryDirectory() as td:
            stub=SearchStub(fail_after=1)
            worker=YouTubeResearchTools(stub, SimpleNamespace(), search_cache_root=td)
            with self.assertRaises(SearchQuotaExhausted):
                worker.search_video_ids('어순')
            with self.assertRaises(SearchQuotaExhausted):
                worker.search_video_ids('여행')
            self.assertEqual(stub.calls,1)

    def test_second_search_429_preserves_first_duration(self):
        with tempfile.TemporaryDirectory() as td:
            stub=SearchStub(fail_after=2)
            worker=YouTubeResearchTools(stub, SimpleNamespace(),search_cache_root=td)
            self.assertEqual(worker.search_video_ids('문장'), ['aaaaaaaaaaa'])
            self.assertTrue(worker.search_quota_blocked)
            self.assertEqual(stub.calls,2)

    def test_reuse_ids_are_only_actual_title_matches_or_seed_ids(self):
        observed={'domestic':[{'video_id':'aaaaaaaaaaa','제목':'긴 영어 문장 만들기'},
                              {'video_id':'bbbbbbbbbbb','제목':'여행 가방 준비'}]}
        self.assertEqual(source_video_ids(observed, '긴 영어 문장'), ['aaaaaaaaaaa'])
        self.assertEqual(source_video_ids(observed,'무관한 이야기', ['ccccccccccc']), ['ccccccccccc'])
        self.assertEqual(source_video_ids(observed,'무관한 이야기', ['not-a-valid-id']), [])

    def test_graphs_grounded_ids_only_and_never_make_scores(self):
        evidence={'existing_channel_videos':[
            {'video_id':'aaaaaaaaaaa','제목':'어순','조회수':60818,'댓글':91},
            {'video_id':'bbbbbbbbbbb','제목':'여행','조회수':10000,'댓글':19}],
            'market_videos':{'domestic':[{'video_id':'ccccccccccc','제목':'시장 예시',
                                           '조회수':40000,'댓글':200}]}}
        data=chart_observations({'근거내채널video_ids':['aaaaaaaaaaa'],
                                 '시장근거video_ids':['ccccccccccc']},evidence)
        self.assertEqual(len(data['own']),1)
        self.assertEqual(data['own'][0]['댓글 절대 수'],91)
        self.assertEqual(data['market'][0]['누적 조회수'],40000)
        self.assertEqual(chart_observations({},evidence)['own'],[])
        self.assertEqual(interest_bars(None),[])
        self.assertEqual(len(interest_bars({'latest_4_avg':42.5})),1)

    def test_pipeline_quota_without_prior_data_returns_honest_partial_not_exception(self):
        import pandas as pd
        pipe=isolated_research_pipeline_for_offline_test()
        pipe.prepare_my_index=lambda progress=None: None
        pipe._collect_market_map=lambda *args, **kwargs: pd.DataFrame()
        pipe.youtube=SimpleNamespace(search_quota_blocked=True)
        pipe.last_reference_markets={'domestic':pd.DataFrame(),'global':pd.DataFrame()}
        pipe.last_reference_diagnostics={}
        result=pipe.research_topic('영어 어순', prefetched_market={})
        self.assertFalse(result['research_ready'])
        self.assertEqual(result['research_limitation'],'SEARCH_QUOTA_NO_REUSABLE_EVIDENCE')
        self.assertEqual(len(result['content_candidates']),0)

    def test_pipeline_quota_reuses_seed_video_without_search(self):
        import pandas as pd
        pipe=isolated_research_pipeline_for_offline_test()
        pipe.prepare_my_index=lambda progress=None: None
        pipe._collect_market_map=lambda *args, **kwargs: pd.DataFrame()
        vid='aaaaaaaaaaa'
        frame=pd.DataFrame([{'video_id':vid,'제목':'긴 영어 문장 만들기',
            '조회수':12000,'댓글':10,'업로드날짜':'2026-04-01',
            '채널':'예시','길이_초':600,'영상링크':'https://www.youtube.com/watch?v='+vid}])
        selected=[]
        def fetch(ids, discovery_label):
            selected.extend(ids)
            return frame.copy()
        pipe.youtube=SimpleNamespace(search_quota_blocked=True,
            market_map_from_video_ids=fetch,
            select_research_candidates=lambda data, top_n=6: data.copy())
        pipe.last_reference_markets={'domestic':pd.DataFrame(),'global':pd.DataFrame()}
        pipe.last_reference_diagnostics={}
        pipe.settings=SimpleNamespace(market_transcript_min_count=3,market_transcript_min_ratio=0.5)
        pipe.evidence=SimpleNamespace(transcript_blocked=False,
            collect_market_evidence=lambda c:(c.copy(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame()))
        result=pipe.research_topic('긴 영어 문장', prefetched_market={'domestic':[{'video_id':vid,'제목':'긴 영어 문장 만들기'}]})
        self.assertFalse(result['research_ready'])
        self.assertEqual(selected,[vid])
        self.assertEqual(len(result['candidate_df']),1)
        self.assertEqual(result['transcript_coverage']['success'],0)

    def test_exploration_never_marks_publication_decision(self):
        with tempfile.TemporaryDirectory() as td:
            store=StrategyStore(root=td)
            event=store.record_topic_exploration({'추천주제':'어순 챌린지'},'B',1,False)
            self.assertFalse(event['production_decision'])
            self.assertEqual(store.topic_choices(), [])
            self.assertEqual(len(json.loads((Path(td)/'topic_explorations.json').read_text())),1)


if __name__=='__main__': unittest.main()
