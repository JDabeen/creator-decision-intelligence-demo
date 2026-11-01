"""Data preparation for measured-only evidence charts; all provenance explicit."""
from __future__ import annotations
from decision_intelligence import _tokens


def _positive_int(x):
    try:
        return max(0, int(x))
    except (ValueError, TypeError, OverflowError):
        return 0


def chart_observations(rec: dict, evidence: dict, limit: int = 7) -> dict:
    """Do not mistake general popular videos for proof of a specific topic."""
    mine = [x for x in (evidence.get('existing_channel_videos') or []) if isinstance(x, dict)]
    market = [x for group in (evidence.get('market_videos') or {}).values()
              if isinstance(group, list) for x in group if isinstance(x, dict)]
    own_ids = set(str(v) for v in (rec.get('근거내채널video_ids') or []))
    market_ids = set(str(v) for v in (rec.get('시장근거video_ids') or []))
    if not market_ids:
        market_ids = {str(x.get('video_id')) for x in (rec.get('시장근거상세') or []) if isinstance(x,dict)}
    mine = [x for x in mine if str(x.get('video_id')) in own_ids]
    market = [x for x in market if str(x.get('video_id')) in market_ids]
    def rows(records):
        seen=set(); result=[]
        for v in sorted(records, key=lambda r:-_positive_int(r.get('조회수'))):
            vid=str(v.get('video_id') or '')
            if not vid or vid in seen: continue
            seen.add(vid)
            result.append({'영상':str(v.get('제목') or vid)[:45],
                           '누적 조회수':_positive_int(v.get('조회수')),
                           '댓글 절대 수':_positive_int(v.get('댓글')),
                           '게시일':str(v.get('업로드날짜') or '')[:10]})
        return result[:limit]
    return {'own':rows(mine),'market':rows(market),
            'own_count':len(mine),'market_count':len(market)}


def interest_bars(interest: dict | None):
    if not interest: return []
    result=[]
    if interest.get('previous_4_avg') is not None:
        result.append({'기간':'이전 4구간','상대 관심도':float(interest['previous_4_avg'])})
    if interest.get('latest_4_avg') is not None:
        result.append({'기간':'최근 4구간','상대 관심도':float(interest['latest_4_avg'])})
    return result
