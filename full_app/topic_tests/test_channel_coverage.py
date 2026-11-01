import unittest
from types import SimpleNamespace
import pandas as pd
from topic_experiment import freeze_shared_evidence, hermes_topic_prompt


class ChannelCoverageTests(unittest.TestCase):
    def test_all_eligible_video_metadata_not_just_first_30(self):
        catalog = pd.DataFrame([
            {'video_id': f'id_{i}', '제목': f'영어학습 {i}', '조회수': i * 500,
             '업로드날짜': '2026-05-01', '좋아요': 5, '댓글': 0, '설명': '설명'*200}
            for i in range(38)])
        scripts = pd.DataFrame([
            {'video_id': f'id_{i}', '제목': f'영어학습 {i}', '전체대본': '연습 방법 안내 '*100,
             '대본상태': '성공'} for i in range(20)])
        fake = SimpleNamespace(my_catalog_df=catalog, my_content_df=scripts,
            last_home_scout_candidates=pd.DataFrame(), last_home_recent_candidates=pd.DataFrame(),
            last_home_global_candidates=pd.DataFrame(), manual_data=None)
        data, warnings = freeze_shared_evidence(fake)
        prov = data['provenance']
        self.assertEqual(prov['channel_catalog_longform_total'], 38)
        self.assertEqual(prov['channel_video_rows'], 38)
        self.assertEqual(prov['historical_script_excerpts'], 20)
        self.assertEqual(prov['channel_video_rows_omitted'], 0)
        self.assertEqual(prov['historical_scripts_omitted'], 0)
        self.assertLessEqual(len(data['existing_channel_videos'][0]['설명']), 280)
        self.assertEqual(data['existing_channel_videos'][-1]['video_id'], 'id_37')
        self.assertNotIn('내 채널 영상 38개 중', ' '.join(warnings))
        inst, prompt = hermes_topic_prompt(data, {'sources': [], 'web_completed': 0})
        self.assertIn('id_37', prompt)
        self.assertIn('id_19', prompt)
        self.assertNotIn('SECRET_CURRENT_DRAFT', prompt)

    def test_studio_manual_rows_only(self):
        class Manual:
            def studio_context(self, max_rows):
                return {'latest_audience_snapshot': {'age_55_64_pct': 53},
                        'latest_video_performance': [{'video_id': 'v1', 'ctr_pct': 5.2}]}
        fake = SimpleNamespace(my_catalog_df=pd.DataFrame([{'video_id':'v1','제목':'어순','조회수':100}]),
            my_content_df=pd.DataFrame(), last_home_scout_candidates=pd.DataFrame(),
            last_home_recent_candidates=pd.DataFrame(), last_home_global_candidates=pd.DataFrame(), manual_data=Manual())
        data, _ = freeze_shared_evidence(fake)
        self.assertEqual(data['provenance']['studio_performance_rows'], 1)
        self.assertEqual(data['user_provided_studio_data']['latest_video_performance'][0]['ctr_pct'], 5.2)

    def test_large_catalog_limits_are_reported(self):
        fake = SimpleNamespace(my_catalog_df=pd.DataFrame([{'video_id': f'v{i}', '제목': '영어','조회수':i} for i in range(205)]),
            my_content_df=pd.DataFrame(), last_home_scout_candidates=pd.DataFrame(),
            last_home_recent_candidates=pd.DataFrame(), last_home_global_candidates=pd.DataFrame(), manual_data=None)
        data, warnings = freeze_shared_evidence(fake)
        self.assertEqual(data['provenance']['channel_video_rows_omitted'], 5)
        self.assertTrue(any('205개 중 200개' in w for w in warnings))


if __name__ == '__main__':
    unittest.main()
