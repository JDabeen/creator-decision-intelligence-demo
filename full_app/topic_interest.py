"""Public, optional search-interest cross-check. No Trends scraping or API calls.

Google Trends YouTube-search charts are relative indices (0-100), not
absolute search counts or projected YouTube views.
"""
from __future__ import annotations
from urllib.parse import urlencode


def youtube_trends_url(query: str) -> str:
    """Build a KR / past-12-month YouTube Search comparison link, no network."""
    clean = ' '.join(str(query or '').split())[:80]
    if not clean:
        raise ValueError('검색어가 필요합니다.')
    return 'https://trends.google.com/trends/explore?' + urlencode({
        'date': 'today 12-m', 'geo': 'KR', 'gprop': 'youtube', 'q': clean,
    })


def format_hypothesis_status(rec: dict) -> str:
    """Never certify that a single winning video validates a repeatable format."""
    return '반복 형식 가설 · 성공 원인 미검증' if rec.get('반복형식가설') else '반복 형식 자료 부족'
