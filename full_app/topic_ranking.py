"""Candidate-specific editorial priorities, never predicted views/probabilities.

No cross-agent winner is declared: A and Hermes rank only their own three topics.
Legacy comparisons are displayed as *order*, not retroactively labelled ranked.
"""
from __future__ import annotations


def explicit_priority(item: dict) -> int | None:
    value = item.get("추천우선순위")
    # Reject bool (a subclass of int) and strings to avoid accidental coercion.
    return value if type(value) is int and 1 <= value <= 3 else None


def order_recommendations(items: list[dict], *, require_rank: bool = False) -> list[dict]:
    """Order ranked candidates; reject duplicate/partial ranks rather than inventing one."""
    result = list(items or [])
    if len(result) != 3:
        if require_rank:
            raise ValueError("추천 후보는 정확히 3개여야 합니다.")
        return result
    priorities = [explicit_priority(x) for x in result]
    if all(p is None for p in priorities) and not require_rank:
        return result  # old stored runs; old list order is not a measured priority
    if sorted(p for p in priorities if p is not None) != [1, 2, 3]:
        raise ValueError("주제별 우선순위는 1·2·3을 중복 없이 하나씩 사용해야 합니다.")
    if require_rank:
        for item in result:
            if not str(item.get("순위선정근거") or "").strip():
                raise ValueError("각 주제의 우선순위 결정 근거가 필요합니다.")
            if not str(item.get("차순위비교") or "").strip():
                raise ValueError("다른 후보와 비교한 기회비용 설명이 필요합니다.")
    return sorted(result, key=lambda x: explicit_priority(x) or 4)


def priority_label(item: dict, position: int) -> str:
    priority = explicit_priority(item)
    return f"{priority}순위" if priority is not None else f"{position}번 후보 · 이전 결과"


def rank_reason(item: dict) -> str:
    return str(item.get("순위선정근거") or "").strip()


def relative_reason(item: dict) -> str:
    return str(item.get("차순위비교") or "").strip()
