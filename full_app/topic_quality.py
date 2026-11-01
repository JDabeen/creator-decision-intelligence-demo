"""Evidence audit for topic recommendations, NOT a prediction of views.

Pure, deterministic checks: does a recommendation refer to source records we
actually have? URLs found by a web tool are *discoveries*, not endorsements.
No AI calls, HTTP requests or opaque numeric 'success scores'.
"""
from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

BLOCKED_HOSTS = frozenset({'localhost', 'localhost.localdomain', 'host.docker.internal',
                           'gateway.docker.internal', 'metadata.google.internal'})


def public_source_url(url: str) -> bool:
    """Conservative URL eligibility for citations; no DNS/network claims."""
    if not isinstance(url, str) or len(url) > 2048:
        return False
    try:
        parsed = urlsplit(url.strip())
        host = (parsed.hostname or '').lower().rstrip('.')
        if parsed.scheme != 'https' or not host or '.' not in host:
            return False
        if parsed.username or parsed.password or parsed.port not in (None, 443):
            return False
        if host in BLOCKED_HOSTS or host.endswith(('.local', '.internal', '.localhost', '.test', '.invalid')):
            return False
        try:
            address = ipaddress.ip_address(host.strip('[]'))
            return bool(address.is_global)
        except ValueError:
            return True
    except (TypeError, ValueError):
        return False


def _source_ids(evidence: dict) -> tuple[set[str], set[str]]:
    mine = {str(v.get('video_id')) for v in evidence.get('existing_channel_videos', [])
            if isinstance(v, dict) and v.get('video_id')}
    market = {str(v.get('video_id'))
              for collection in (evidence.get('market_videos') or {}).values()
              for v in collection if isinstance(v, dict) and v.get('video_id')}
    return mine, market


def assess_topic(rec: dict, source: str, evidence: dict, web: dict | None = None) -> dict:
    """Audit evidence traceability; this never asserts demand or video performance."""
    own_ids, market_ids = _source_ids(evidence)
    web_sources = {str(s.get('url')).strip().rstrip('/')
                   for s in ((web or {}).get('sources') or [])
                   if isinstance(s, dict) and public_source_url(s.get('url'))}
    anchor_refs = rec.get('근거내채널video_ids') or []
    cited_market = rec.get('시장근거video_ids') or []
    if not cited_market and source == 'A':
        cited_market = [r.get('video_id') for r in (rec.get('시장근거상세') or [])
                        if isinstance(r, dict)]
    links = [x for x in (rec.get('검증출처URL') or []) if public_source_url(x)]
    valid_own = list(dict.fromkeys(str(i) for i in anchor_refs if str(i) in own_ids))
    valid_market = list(dict.fromkeys(str(i) for i in cited_market if str(i) in market_ids))
    # The baseline sometimes cites a valid API video outside the 16-per-segment
    # Hermes common evidence snapshot. Preserve it as A-only provenance, rather
    # than mislabeling a source backed by pipeline._attach_grounded_evidence as fake.
    a_only = []
    if source == 'A':
        for detail in (rec.get('시장근거상세') or []):
            if not isinstance(detail, dict):
                continue
            video_id = str(detail.get('video_id') or '')
            if video_id and video_id not in market_ids and public_source_url(detail.get('영상링크', '')):
                a_only.append(video_id)
    a_only = list(dict.fromkeys(a_only))
    valid_links = list(dict.fromkeys(x for x in links if x.rstrip('/') in web_sources))
    # A's references originate in its own API data, not Hermes's web sources.
    if source == 'A':
        linked = bool(valid_market or a_only)
        status = '시장 영상 연결' if linked else '근거 연결 부족'
    else:
        linked = bool(valid_links)
        status = '조사 링크 확보' if linked else '직접 조사 근거 부족'
    warnings = []
    if not linked:
        warnings.append('이 주제에 연결된 직접적인 외부 영상/웹 출처가 부족합니다.')
    if a_only:
        warnings.append('A 근거 영상 중 일부는 Hermes와 공유한 시장 샘플 밖에 있습니다. 통제된 모델 비교로 해석할 수 없습니다.')
    if rec.get('전략경로') in ('승자 심화', '인접 확장') and not valid_own:
        warnings.append('기존 인기 영상과 연결된 구체적인 내 채널 ID가 없습니다.')
    if source == 'B' and valid_links:
        warnings.append('링크 확보는 해당 주제의 시청자 수요나 추천 성공을 증명하지 않습니다.')
    return {
        'status': status,
        'source': source,
        'channel_video_ids': valid_own,
        'market_video_ids': valid_market,
        'a_only_market_video_ids': a_only,
        'tool_observed_urls': valid_links,
        'limitations': warnings,
        'demand_confirmed': False,
        'expected_views': None,
    }


def audit_comparison(a_recs: list[dict], b_recs: list[dict], evidence: dict, web: dict) -> dict:
    """Apply the same inspectable rubric to both recommendation pipelines."""
    return {
        'method': 'evidence_traceability_not_performance_prediction',
        'comparison_kind': '두 워크플로의 후보 비교; 동일 모델/동일 도구 통제 실험 아님',
        'a': [assess_topic(rec, 'A', evidence, web) for rec in a_recs],
        'b': [assess_topic(rec, 'B', evidence, web) for rec in b_recs],
        'limits': [
            'A와 B는 동일 시점의 관측 원자료를 공유하지만 A에는 RAG/내부 메모리, B에는 추가 웹 검색이 있어 독립 워크플로 비교입니다.',
            '조회수는 영상 나이·노출·제목·썸네일 등의 영향을 받습니다. 추천의 성과는 업로드 후에만 평가할 수 있습니다.',
            'URL은 도구 결과에 나타났다는 의미이며, 본문을 검증하거나 조회수·수요가 입증됐다는 의미가 아닙니다.',
        ],
    }
