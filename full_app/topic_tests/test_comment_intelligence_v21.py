import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from comment_intelligence import (
    CATEGORIES, absolute_comment_leaderboard, classify_comment_sample,
    fetch_top_level_comments, safe_report,
)
from strategy_hub import StrategyStore


class CommentIntelligenceTests(unittest.TestCase):
    def test_absolute_not_ratio(self):
        data = [
            {'video_id':'aaaaaaaaaaa','title':'A','views':100000,'comments':200},
            {'video_id':'bbbbbbbbbbb','title':'B','views':100,'comments':100},
        ]
        result = absolute_comment_leaderboard(data)
        self.assertEqual([x['video_id'] for x in result], ['aaaaaaaaaaa', 'bbbbbbbbbbb'])
        self.assertFalse(any('rate' in str(k) or 'ratio' in str(k) for x in result for k in x))

    def test_fetch_one_page_no_author_fields(self):
        y = MagicMock()
        y.commentThreads.return_value.list.return_value.execute.return_value = {
            'items':[{'snippet':{'topLevelComment':{'snippet':{'textOriginal':'배웠습니다', 'authorDisplayName':'PRIVATE'}}}}]
        }
        found = fetch_top_level_comments(y, 'AAAAAAAAAAA', 60)
        self.assertEqual(found, [{'index':0,'text':'배웠습니다'}])
        self.assertEqual(y.commentThreads.return_value.list.call_args.kwargs['maxResults'],60)
        self.assertNotIn('PRIVATE',str(found))
        with self.assertRaises(ValueError):
            fetch_top_level_comments(y, 'evil/../')

    def test_classification_counts_computed_only(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(output_text=json.dumps({
            'labels': [{'index':0,'category':'구체적 이해·칭찬'},
                       {'index':1,'category':'강의·상품 관심'}]
        }, ensure_ascii=False))
        report = classify_comment_sample(client, 'mock-model', [
            {'text':'이해했어요'}, {'text':'강의 신청은 어디서 하나요?'}
        ], 'AAAAAAAAAAA')
        self.assertEqual(report['sample_count'], 2)
        self.assertEqual(report['category_counts']['구체적 이해·칭찬'],1)
        self.assertEqual(report['category_counts']['강의·상품 관심'],1)
        self.assertEqual(sum(report['category_counts'].values()),2)
        self.assertEqual(set(report['category_counts']),set(CATEGORIES))
        self.assertNotIn('_transient_examples',safe_report(report))

    def test_wrong_llm_response_fails_closed(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(output_text='{"labels": []}')
        with self.assertRaises(ValueError):
            classify_comment_sample(client,'mock',[{'text':'hello'}],'AAAAAAAAAAA')

    def test_store_aggregates_without_comments_or_identity(self):
        with tempfile.TemporaryDirectory() as d:
            store = StrategyStore(Path(d))
            payload = {'video_id':'AAAAAAAAAAA','measured_at':'2026-10-23T00:00:00Z',
                       'sample_count':1,'category_counts':{'기타':1},
                       'classification_status':'AI_CLASSIFICATION_UNVERIFIED',
                       'method':'test','_transient_examples':{'기타':['secret PRIVATE']},
                       'author_id':'SECRET'}
            path=store.save_comment_review(payload)
            text=path.read_text(encoding='utf-8')
            self.assertNotIn('PRIVATE',text)
            self.assertNotIn('SECRET',text)
            self.assertEqual(len(store.comment_reviews()),1)
            self.assertIn('top_videos',store.comment_context())

    def test_demo_fictional_fixture(self):
        root = Path(__file__).resolve().parents[1]
        fixture=json.loads((root/'public_demo'/'demo_data.json').read_text(encoding='utf-8'))
        self.assertIn('fictional',fixture['data_notice'])
        for r in fixture['channel']['review_samples'].values():
            self.assertEqual(sum(r['categories'].values()),r['sample_count'])
        for name in ('A','Hermes'):
            self.assertEqual([v['rank'] for v in fixture['recommendations'][name]],[1,2,3])


if __name__ == '__main__':
    unittest.main()
