"""Optional paid Google Trends YouTube Search relative-interest snapshots.

SerpApi is NOT Google's official Trends API. No API calls without an explicit
SERPAPI_API_KEY. Compare values only inside the same query batch: 0..100 is
re-normalized per request, geography and time window.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from research_resilience import safe_error

BASE = 'https://serpapi.com/search.json'


def _keys(recs_a: list[dict], recs_b: list[dict]) -> list[str]:
    result = []
    for rec in (recs_a or [])[:3] + (recs_b or [])[:3]:
        term = ' '.join(str(rec.get('추천검색어') or rec.get('추천주제') or '').split())[:80]
        if term and term not in result:
            result.append(term)
    return result


def _extract(payload: dict, terms: list[str]) -> dict:
    if payload.get('error'):
        raise RuntimeError(str(payload.get('error'))[:200])
    timeline = (payload.get('interest_over_time') or {}).get('timeline_data') or []
    series = {name: [] for name in terms}
    for period in timeline:
        for v in period.get('values') or []:
            name = str(v.get('query') or '')
            if name not in series:
                continue
            raw = v.get('extracted_value', v.get('value'))
            try:
                number = int(str(raw).replace(',', ''))
            except (ValueError, TypeError):
                continue
            if 0 <= number <= 100:
                series[name].append(number)
    if not any(series.values()):
        raise RuntimeError('Google Trends 상대 관심도 시계열 데이터가 반환되지 않았습니다.')
    return {term: {
        'points':len(points),
        'latest_4_avg':round(sum(points[-4:])/len(points[-4:]), 1) if points else None,
        'previous_4_avg':round(sum(points[-8:-4])/len(points[-8:-4]), 1) if len(points)>=8 else None,
        'all_period_avg':round(sum(points)/len(points), 1) if points else None,
        'status':'measured_relative_interest' if points else 'no_data',
    } for term, points in series.items()}


def _fetch_serpapi(params: dict, key: str) -> dict:
    # URL is never logged or persisted. Request goes only to declared SerpApi.
    args = dict(params, api_key=key)
    with urlopen(BASE + '?' + urlencode(args), timeout=25) as res:
        body = res.read(2_000_000)
    return json.loads(body.decode('utf-8'))


def capture_topic_trends(a_topics: list[dict], b_topics: list[dict], root: str | Path,
                         key: str = '', fetcher=None, cache_days: int = 7,
                         now: datetime | None = None) -> dict:
    """Two <=5-term batches. Not directly comparable across batches.

    This may incur charges. Cache each batch by key terms/region/time period.
    Store only small aggregate values, never API key, raw source JSON or cookies.
    """
    key = key or os.getenv('SERPAPI_API_KEY', '').strip()
    if not key:
        return {'status':'NO_KEY', 'batches':[], 'note':'SerpApi 키 없음 · 실제 검색 관심도 미수집'}
    terms = _keys(a_topics, b_topics)
    if not terms:
        return {'status':'NO_TERMS', 'batches':[]}
    root = Path(root) / 'trend_snapshots'
    root.mkdir(parents=True, exist_ok=True)
    current = now or datetime.now(timezone.utc)
    # The second batch shares an anchor, but do not treat indices across batches
    # as directly comparable. Anchor serves only as a human visual reference.
    batches = [terms[:5]]
    if len(terms)>5:
        batches.append([terms[0]] + terms[5:])
    result = []
    for i, items in enumerate(batches):
        params = {'engine':'google_trends', 'data_type':'TIMESERIES', 'q':','.join(items),
                  'date':'today 12-m', 'geo':'KR', 'gprop':'youtube', 'tz':'-540'}
        fingerprint = hashlib.sha256(json.dumps(params, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:18]
        cache = root / f'{fingerprint}.json'
        old = {}
        if cache.is_file():
            try:
                old = json.loads(cache.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                pass
        cached_at = old.get('retrieved_at')
        if cached_at:
            try:
                age = (current - datetime.fromisoformat(cached_at)).total_seconds()
                if 0 <= age <= cache_days*86400 and old.get('terms')==items:
                    result.append(old)
                    continue
            except (ValueError, TypeError):
                pass
        try:
            data = (fetcher or _fetch_serpapi)(params, key)
            stats = _extract(data, items)
            entry = {'batch':i+1, 'terms':items, 'retrieved_at':current.isoformat(),
                     'comparison_scope':'KR YouTube Search / past 12 months / batch-local normalized 0..100',
                     'provider':'SerpApi Google Trends (3rd party, may charge)',
                     'statistics':stats,
                     'note':'상대 관심도; 절대 검색 횟수나 추천 노출/예상 조회수 아님. 별도 배치의 숫자는 직접 비교 금지.'}
            # Durable atomic save.
            tmp = cache.with_suffix('.tmp')
            tmp.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(tmp, cache)
            result.append(entry)
        except Exception as e:
            # Do not erase existing evidence on provider failure.
            return {'status':'ERROR', 'batches':result, 'error':safe_error(e),
                    'note':'관심도 제공자 실패 · 추정값으로 대체하지 않음'}
    return {'status':'MEASURED', 'batches':result, 'note':'상대 관심도 실측 · 배치 간 직접 비교 금지'}


def lookup_term(result: dict | None, term: str) -> dict | None:
    term = ' '.join(str(term or '').split())[:80]
    for batch in (result or {}).get('batches') or []:
        if term in batch.get('statistics', {}):
            return {'term':term, 'batch':batch.get('batch'),
                    'retrieved_at':batch.get('retrieved_at'),
                    **batch['statistics'][term]}
    return None
