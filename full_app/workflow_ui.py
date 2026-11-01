"""Presentation-only stage availability and candidate mapping.

This module never starts research, accesses APIs or modifies persistent records.
Enables deterministic UI behavior and simple regression testing.
"""
from __future__ import annotations
from typing import Any, Mapping

FLOW_STAGES = ("find", "compare", "research", "draft")


def available_stages(state: Mapping[str, Any]) -> set[str]:
    available = {"find"}
    if state.get("home_recommendations"):
        available.add("compare")
    if state.get("research") is not None:
        available.add("research")
    if state.get("draft_a_bundle") is not None:
        available.add("draft")
    return available


def topic_choices(a_topics: list[dict], b_topics: list[dict] | None) -> list[tuple[str, str, str, dict, int]]:
    """Return distinct choices with stable A/B source identities.

    Each tuple is (widget value, display source label, source id, original dict, rank).
    """
    choices = []
    for source, recs in (("A", a_topics), ("B", b_topics or [])):
        for rank, rec in enumerate((recs or [])[:3], 1):
            if isinstance(rec, dict) and str(rec.get("추천주제") or "").strip():
                priority = rec.get("추천우선순위")
                label = f"{source} {priority}순위" if type(priority) is int and priority == rank else f"{source}{rank}"
                choices.append((f"{source}-{rank}", label, source, rec, rank))
    return choices
