"""Ranking requirements for separate A/Hermes candidate proposals (no external APIs)."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from topic_ranking import order_recommendations, priority_label
from topic_experiment import parse_hermes_topics, save_selection
from topic_tests.test_topic_comparison import demo_topics
from workflow_ui import topic_choices


class IndependentRankingTests(unittest.TestCase):
    def setUp(self):
        self.a = [
            {"추천주제": "후보 삼", "추천우선순위": 3, "순위선정근거": "낮은 채널 적합성", "차순위비교": "상대적으로 검증 부족"},
            {"추천주제": "후보 일", "추천우선순위": 1, "순위선정근거": "반복 가능한 검증", "차순위비교": "두 후보보다 근거가 풍부"},
            {"추천주제": "후보 이", "추천우선순위": 2, "순위선정근거": "외부 경쟁 성과", "차순위비교": "A1보다 부족 A3보다 풍부"},
        ]

    def test_a_explicit_order_reorders_and_preserves_rationale(self):
        ranked = order_recommendations(self.a, require_rank=True)
        self.assertEqual([i['추천우선순위'] for i in ranked], [1, 2, 3])
        self.assertEqual(ranked[0]['추천주제'], '후보 일')
        self.assertIn('두 후보', ranked[0]['차순위비교'])
        self.assertEqual(priority_label(ranked[0], 1), '1순위')
        self.assertEqual([i[1] for i in topic_choices(ranked, [])], ['A 1순위', 'A 2순위', 'A 3순위'])

    def test_duplicate_rank_or_missing_relative_reason_rejected(self):
        items = [dict(item) for item in self.a]
        items[0]['추천우선순위'] = 1
        with self.assertRaisesRegex(ValueError, '중복 없이'):
            order_recommendations(items, require_rank=True)
        items = [dict(item) for item in self.a]
        items[2]['차순위비교'] = ''
        with self.assertRaisesRegex(ValueError, '비교한 기회비용'):
            order_recommendations(items, require_rank=True)

    def test_old_saved_run_never_invents_ranking(self):
        old = [{"추천주제": f"옛 후보 {i}"} for i in range(3)]
        self.assertEqual(order_recommendations(old), old)
        self.assertIn('이전 결과', priority_label(old[0], 1))

    def test_hermes_own_rank_sorts_and_does_not_know_a(self):
        items = demo_topics()
        for i, new_rank in enumerate([3, 1, 2]):
            items[i]['priority_rank'] = new_rank
            items[i]['ranking_reason'] = f'B 자체 검증 {new_rank}순위 근거'
            items[i]['relative_tradeoff'] = '다른 B 후보와 비교한 위험'
        content = '<TOPIC_JSON>' + json.dumps({'topics': items}, ensure_ascii=False) + '</TOPIC_JSON>'
        ranked, _ = parse_hermes_topics(content, ['https://example.org/article'], require_ranking=True)
        self.assertEqual([r['추천우선순위'] for r in ranked], [1, 2, 3])
        self.assertIn('B 자체', ranked[0]['순위선정근거'])
        self.assertEqual([r[1] for r in topic_choices([], ranked)], ['B 1순위', 'B 2순위', 'B 3순위'])

    def test_hermes_missing_rank_fails_when_new_run(self):
        items = demo_topics()
        items[0].pop('ranking_reason')
        txt = '<TOPIC_JSON>' + json.dumps({'topics': items}, ensure_ascii=False) + '</TOPIC_JSON>'
        with self.assertRaisesRegex(ValueError, '순위 결정 근거'):
            parse_hermes_topics(txt, ['https://example.org/article'], require_ranking=True)

    def test_chosen_rank_and_reason_persist_without_leaking_other_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = {'run_folder': tmp}
            rec = order_recommendations(self.a, require_rank=True)[0]
            save_selection(result, rec, 'A')
            saved = json.loads((Path(tmp) / 'human_selection.json').read_text(encoding='utf-8'))
            self.assertEqual(saved['source_priority_rank'], 1)
            self.assertEqual(saved['chosen_source'], 'A')
            self.assertEqual(saved['rank_justification'], '반복 가능한 검증')

    def test_ui_has_single_candidate_choice_with_comparative_reasons_in_evidence(self):
        app = (Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8')
        self.assertIn('topic_choices(recs, b_topics)', app)
        self.assertIn('A/B 추천 · 제작할 주제 하나 선택', app)
        self.assertIn('판단 근거 · 데이터 보기', app)
        self.assertIn('rank_reason(item)', app)
        self.assertIn('relative_reason(item)', app)


if __name__ == '__main__':
    unittest.main()
