import json
import tempfile
import unittest
from pathlib import Path
from export_public_portfolio import export_latest

class PublicExportTests(unittest.TestCase):
    def test_output_does_not_contain_raw_titles_urls_scripts_or_private_studio(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            folder=root/'topic_experiments'/'run1'
            folder.mkdir(parents=True)
            (folder/'manifest.json').write_text(json.dumps({
                'status':'COMPLETE','version':'test','evidence_sha256':'X'*64,
                'web_completed':2,'web_source_count':4
            }),encoding='utf-8')
            (folder/'comparison.json').write_text(json.dumps({
                'a_topics':[{'추천주제':'SECRET_CHANNEL_TITLE'}],
                'b_topics':[{'추천주제':'SECRET_HERMES_TITLE'}],
                'evidence_audit':{'a':[{'status':'시장 영상 연결'}],
                                  'b':[{'status':'조사 링크 확보'}]},
                'private_studio':'PRIVATE_REVENUE_DATA',
                'urls':['https://secret.example.com']
            },ensure_ascii=False),encoding='utf-8')
            out=export_latest(root,root/'share'/'safe.json')
            content=out.read_text(encoding='utf-8')
            self.assertIn('시장 영상 연결',content)
            for secret in ('SECRET_CHANNEL_TITLE','SECRET_HERMES_TITLE',
                           'PRIVATE_REVENUE_DATA','secret.example.com'):
                self.assertNotIn(secret,content)

if __name__=='__main__':unittest.main()
