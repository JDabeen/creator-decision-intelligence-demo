"""Evidence-aware decision history and delayed view-count validation.

Not a search-volume API or a causal view predictor. Treat missing measurements as
missing; never extrapolate a historical 7/28-day snapshot from cumulative views.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import math
import re
import statistics


_STOP = {'영어', '하는', '하는법', '이유', '방법', '영상', '초보', '중장년', '50대', '따라', '가장', '나의', '위한', '이것', '이렇게', '정말', '어떻게'}


def _tokens(raw: str) -> set[str]:
    parts = re.findall(r'[a-zA-Z]{3,}|[가-힣]{2,}', str(raw or '').lower())
    return {p for p in parts if p not in _STOP and len(p) >= 2}


def market_observation(topic: str, market_pool: dict | None) -> dict:
    """Observed PUBLIC-video engagement for matching keywords, NOT searches.

    Search-sampled videos are a biased small candidate pool. Counts and views
    must never be read as monthly search volume, unbiased demand, or a forecast.
    """
    pool = market_pool or {}
    query_tokens = _tokens(topic)
    videos = {}
    for group in pool.values():
        if not isinstance(group, list):
            continue
        for video in group:
            if not isinstance(video, dict):
                continue
            vid = str(video.get('video_id') or '')
            if not vid or vid in videos:
                continue
            videos[vid] = video
    matches = []
    for video in videos.values():
        overlap = query_tokens & _tokens(video.get('제목') or '')
        if overlap and (len(overlap) >= 2 or (len(query_tokens) <= 2 and len(overlap) >= 1)):
            try:
                count = int(video.get('조회수') or 0)
            except (ValueError, TypeError, OverflowError):
                count = 0
            matches.append((video, max(0, count)))
    views = [count for _, count in matches if count > 0]
    return {
        'kind': 'retrieved_youtube_video_consumption_proxy_not_search_volume',
        'sample_pool': len(videos), 'matched_videos': len(matches),
        'median_cumulative_views': int(statistics.median(views)) if views else None,
        'matched_ids': [v.get('video_id') for v, _ in matches[:8]],
        'source': '이번 주제 탐색에서 이미 확보한 YouTube 시장 영상 후보',
        'limitations': '검색으로 고른 편향된 표본, 게시 시점·추천 노출·채널 규모 차이를 보정하지 않음. 검색량·예상 조회수 아님.',
    }


def evidence_for_comparison(comp: dict | None) -> dict:
    """Read frozen evidence only from the selected experiment's run folder."""
    if not comp or not comp.get('run_folder'):
        return {}
    try:
        path = Path(comp['run_folder']) / 'evidence.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _parse_date(s: str):
    try:
        return datetime.fromisoformat(str(s).replace('Z', '+00:00')).date()
    except (ValueError, TypeError):
        return None


def horizon_outcomes(snapshots: list[dict], horizon_days: int = 28, tolerance_days: int = 1) -> dict[str, dict]:
    """Approximate D7/D28 observed since publish, only in a narrow capture window.

    Does not invent early results for uploads that predate tracking. The official
    API exposes today's cumulative public views, not historical day-7 views.
    """
    if horizon_days < 1 or tolerance_days < 0:
        raise ValueError('Invalid measurement window')
    by_id = {}
    for snapshot in snapshots:
        measured = _parse_date(snapshot.get('measured_at'))
        if measured is None:
            continue
        for video in snapshot.get('videos') or []:
            vid = str(video.get('video_id') or '')
            published = _parse_date(video.get('published_date'))
            if not vid or not published:
                continue
            age = (measured - published).days
            if abs(age - horizon_days) > tolerance_days:
                continue
            try:
                views = int(video.get('views'))
            except (TypeError, ValueError, OverflowError):
                continue
            if views < 0:
                continue
            current = by_id.get(vid)
            score = (abs(age - horizon_days), measured)
            if current is None or score < current['_score']:
                by_id[vid] = {'video_id': vid, 'title': str(video.get('title') or ''),
                              'views': views, 'measured_date': measured.isoformat(),
                              'age_days': age, '_score': score}
    for data in by_id.values():
        data.pop('_score', None)
    return by_id


def percentile(values: list[int], p: float) -> int:
    ordered = sorted(values)
    if not ordered:
        raise ValueError('No data')
    k = (len(ordered)-1)*p
    low, high = math.floor(k), math.ceil(k)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (k - low))


def channel_prior(snapshots: list[dict], days: int = 28, minimum: int = 8) -> dict:
    observations = horizon_outcomes(snapshots, days)
    values = [x['views'] for x in observations.values()]
    if len(values) < minimum:
        return {'status':'INSUFFICIENT', 'n':len(values), 'required':minimum,
                'days':days, 'range':None,
                'explanation': '발행 후 같은 시점의 관측값이 부족해 수치 예측을 보류함'}
    return {'status':'DESCRIPTIVE_BASELINE', 'n':len(values), 'days':days,
            'range':[percentile(values, .2), percentile(values, .8)],
            'median':percentile(values, .5),
            'explanation':'과거 채널 영상의 같은 시점 조회수 20~80백분위; 이번 주제의 확률 예측이나 조회수 보장이 아님'}


def selection_outcomes(choices: list[dict], links: list[dict], snapshots: list[dict]) -> dict:
    """Match only user-confirmed video IDs, and only measurements observed later."""
    linked_by_topic = {}
    for link in links:
        key = str(link.get('topic') or '').strip()
        if key and re.fullmatch(r'[A-Za-z0-9_-]{11}', str(link.get('video_id') or '')):
            linked_by_topic.setdefault(key, set()).add(link['video_id'])
    observed_7 = horizon_outcomes(snapshots, 7)
    observed_28 = horizon_outcomes(snapshots, 28)
    selected = []
    for choice in choices:
        topic = str(choice.get('topic') or '').strip()
        vids = linked_by_topic.get(topic, set())
        selected.append({'topic':topic, 'choice_id':choice.get('id'),
                         'selected_at':choice.get('selected_at'),
                         'video_ids':sorted(vids),
                         'day_7':{vid:observed_7[vid]['views'] for vid in vids if vid in observed_7},
                         'day_28':{vid:observed_28[vid]['views'] for vid in vids if vid in observed_28},
                         'initial_market_signal':choice.get('initial_market_signal') or {},
                         'prior_at_decision':choice.get('prior_at_decision') or {},
                         'status':'관측됨' if any(v in observed_28 for v in vids) else ('영상 연결됨 · 28일 관측 대기' if vids else '업로드 영상 미연결')})
    observed_count = sum(bool(row['day_28']) for row in selected)
    # Check whether earlier, already-recorded channel-wide benchmark covered
    # subsequent actual outcomes. Do not backfill predictions from new data.
    comparisons = []
    seen = set()
    for row in selected:
        prior = row.get('prior_at_decision') or {}
        band = prior.get('range') if prior.get('status') == 'DESCRIPTIVE_BASELINE' else None
        if not isinstance(band, list) or len(band) != 2:
            continue
        for vid, views in row['day_28'].items():
            pair = (row['topic'], vid)
            if pair in seen:
                continue
            seen.add(pair)
            comparisons.append({'video_id':vid, 'topic':row['topic'], 'views':views,
                                'inside_historical_20_80_percentile':band[0] <= views <= band[1]})
    calibration = {'status':'INSUFFICIENT' if len(comparisons) < 5 else 'OBSERVED_BASELINE_CHECK',
                   'n':len(comparisons), 'min_required':5,
                   'inside_percent':round(100*sum(bool(r['inside_historical_20_80_percentile']) for r in comparisons)/len(comparisons),1) if len(comparisons)>=5 else None,
                   'note':'과거 채널 분포의 범위 포함 비율이며, 주제 예측 모델의 정확도나 추천 성공확률이 아님'}
    return {'total_decisions':len(selected), 'observed_28d':observed_count,
            'baseline_check':calibration, 'rows':selected[-20:],
            'warning':'조회수는 제목·썸네일·노출·시기·영상 품질의 영향을 받음. 주제 선택의 인과 효과나 통계적 승률 아님.'}
