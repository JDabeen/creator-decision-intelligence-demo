"""Small, deterministic helpers for quota errors, secret-safe UI and old evidence reuse."""
from __future__ import annotations
import re
from datetime import datetime, timezone

VIDEO_ID = re.compile(r"^[a-zA-Z0-9_-]{11}$")


class SearchQuotaExhausted(RuntimeError):
    """Quota reached or conservatively paused. Do not expose raw HTTP request URLs."""


def is_search_quota_error(exc: Exception) -> bool:
    status = getattr(getattr(exc, 'resp', None), 'status', None)
    message = str(exc).lower()
    return status in (403, 429) and any(x in message for x in ('quota', 'rate limit', 'ratelimit', 'dailylimit', 'search queries'))


def safe_error(exc: Exception) -> str:
    """Never return tracebacks/URLs/API keys to Streamlit or run manifests."""
    if isinstance(exc, SearchQuotaExhausted) or is_search_quota_error(exc):
        return 'YouTube 검색 할당량이 부족합니다. 저장된 시장 근거와 영상 ID를 우선 재사용하세요.'
    # Avoid exposing HTTP error objects, which embed Google API keys in request URLs.
    if getattr(exc, 'resp', None) is not None:
        return f'외부 API 요청 실패 ({type(exc).__name__}). 연결 상태와 서비스 제한을 확인하세요.'
    text = str(exc or '').replace('\n', ' ').replace('\r', ' ')[:240]
    text = re.sub(r'(?i)(?:AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z_-]{12,})', '[SECRET]', text)
    text = re.sub(r'(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*[^\s&]+', r'\1=[REDACTED]', text)
    text = re.sub(r'https?://[^\s]+', '[URL OMITTED]', text)
    return f'{type(exc).__name__}: {text}'


def source_video_ids(source: dict, keywords: str, seed_ids: list[str] | None = None, limit: int = 22) -> list[str]:
    """Only return observed video IDs. Do not fabricate semantic relevance from AI prose."""
    from decision_intelligence import _tokens
    terms = _tokens(keywords)
    ids = [str(v) for v in (seed_ids or []) if VIDEO_ID.fullmatch(str(v))]
    matched = []
    for group in (source or {}).values():
        if not isinstance(group, list):
            continue
        for row in group:
            if not isinstance(row, dict):
                continue
            vid = str(row.get('video_id') or '')
            if not VIDEO_ID.fullmatch(vid):
                continue
            overlap = terms & _tokens(row.get('제목') or '')
            if overlap and (len(overlap) >= 2 or len(terms) <= 2):
                matched.append(vid)
    for video_id in matched:
        if video_id not in ids:
            ids.append(video_id)
    return ids[:limit]
