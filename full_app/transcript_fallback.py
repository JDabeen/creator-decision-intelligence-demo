"""Optional hosted transcript retrieval for market evidence only.

Native captions only; no automatic paid AI transcription and no IP-ban bypass logic.
User must opt in by saving their own provider key outside the package.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib import error, parse, request

BASE = 'https://api.supadata.ai/v1/transcript'

class TranscriptProviderError(RuntimeError):
    pass


def read_provider_key(cache_root: Path) -> str:
    env = os.environ.get('SUPADATA_API_KEY', '').strip()
    if env:
        return env
    path = Path(cache_root).parent / 'supadata_key.txt'
    try:
        return path.read_text(encoding='utf-8').strip()
    except OSError:
        return ''


def _read_json(url: str, key: str, timeout: int = 25):
    req = request.Request(url, headers={'x-api-key': key, 'accept': 'application/json', 'user-agent': 'YoutubeContentConsultant/1.0'})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), json.loads(resp.read(8_000_000).decode('utf-8'))
    except error.HTTPError as exc:
        # Never disclose the provider key, response headers, or full network exception.
        raise TranscriptProviderError(f'Supadata HTTP {exc.code}') from None
    except (OSError, ValueError) as exc:
        raise TranscriptProviderError(f'Supadata 연결/응답 오류: {type(exc).__name__}') from None


def fetch_native_transcript(video_id: str, key: str, *, poll_seconds: int = 40) -> dict:
    """Fetch existing published captions. API usage: 1 credit per native query.

    Does NOT request mode=auto (which could spend 2 credits/minute for AI ASR).
    """
    if not video_id or not key:
        raise TranscriptProviderError('Supadata API 키 또는 영상 ID 없음')
    video_url = 'https://www.youtube.com/watch?v=' + str(video_id)
    url = BASE + '?' + parse.urlencode({'url': video_url, 'mode': 'native', 'text': 'false'})
    status, data = _read_json(url, key)
    if status == 202 or (isinstance(data, dict) and data.get('jobId')):
        job_id = str(data.get('jobId', '')).strip()
        if not job_id:
            raise TranscriptProviderError('Supadata 응답에 작업 ID 없음')
        deadline = time.monotonic() + poll_seconds
        while time.monotonic() < deadline:
            time.sleep(2)
            status, data = _read_json(BASE + '/' + parse.quote(job_id, safe=''), key)
            if data.get('status') == 'failed':
                raise TranscriptProviderError('Supadata 자막 작업 실패')
            if data.get('status') == 'completed':
                break
        else:
            raise TranscriptProviderError('Supadata 자막 작업 대기 시간 초과')
    if not isinstance(data, dict):
        raise TranscriptProviderError('Supadata 응답 형식 불일치')
    raw = data.get('content')
    segments = []
    if isinstance(raw, list):
        for chunk in raw:
            if not isinstance(chunk, dict):
                continue
            body = str(chunk.get('text', '')).strip()
            if body:
                segments.append({
                    '시작초': float(chunk.get('offset', 0) or 0)/1000,
                    '길이초': float(chunk.get('duration', 0) or 0)/1000,
                    '텍스트': body,
                })
    elif isinstance(raw, str) and raw.strip():
        segments = [{'시작초': 0.0, '길이초': 0.0, '텍스트': raw.strip()}]
    full_text = ' '.join(s['텍스트'].replace('\n', ' ') for s in segments)
    if len(full_text) < 120:
        raise TranscriptProviderError('Supadata 자막이 없거나 지나치게 짧음')
    return {
        'video_id': str(video_id), '상태': '성공',
        '언어': str(data.get('lang', '') or '미확인'),
        '언어코드': str(data.get('lang', '') or ''),
        '자동자막': None, '대본글자수': len(full_text),
        '전체대본': full_text, 'segments': segments,
        '오류': None, '획득경로': 'Supadata native captions'
    }


def import_pasted_transcript(cache, video_id: str, text: str) -> int:
    video_id = str(video_id).strip()
    content = ' '.join(str(text or '').split())
    if not video_id or '/' in video_id or '\\' in video_id or len(video_id) > 30:
        raise ValueError('유효하지 않은 영상 ID입니다.')
    if len(content) < 300:
        raise ValueError('자막 원문이 300자보다 짧습니다. 영상의 전체 스크립트를 입력하세요.')
    payload = {
        'video_id': video_id, '상태': '성공', '언어': '사용자 입력', '언어코드': None,
        '자동자막': None, '대본글자수': len(content), '전체대본': content,
        'segments': [{'시작초': 0.0, '길이초': 0.0, '텍스트': content}],
        '오류': None, '획득경로': '사용자 제공 영상 자막'
    }
    cache.safe_json_dump(payload, cache.root / 'transcripts' / f'{video_id}.json')
    return len(content)
