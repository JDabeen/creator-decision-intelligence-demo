"""Auditable public market observations for script strategy.

No prediction of future YouTube views is made here; observations may be
selection-biased. Only metadata supplied by the existing YouTube research
pipeline is accepted. Never invent a market result for a proposed new topic.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

import pandas as pd

COLUMNS = ["video_id", "제목", "채널", "조회수", "업로드날짜", "영상나이_일",
           "채널배수", "조회수_구독자배수", "시장범위", "선정이유", "영상링크"]
VALID_ACTIONS = {"KEEP", "REFRAME", "RESEARCH_NEW"}


def _scalar(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (bool, str, int)):
        return v
    if isinstance(v, float):
        return round(v, 3) if math.isfinite(v) else None
    try:
        if pd.isna(v):
            return None
    except (ValueError, TypeError):
        pass
    if hasattr(v, "item"):
        return _scalar(v.item())
    if isinstance(v, (list, dict)):
        return str(v)[:120]
    return str(v)[:300]


def build_market_audit(candidates: Any, transcript_df: Any, topic: str) -> dict:
    """Freeze independently checkable observations at draft-selection time."""
    df = candidates if isinstance(candidates, pd.DataFrame) else pd.DataFrame()
    tdf = transcript_df if isinstance(transcript_df, pd.DataFrame) else pd.DataFrame()
    transcript_ids: set[str] = set()
    if not tdf.empty and {"video_id", "대본상태"}.issubset(tdf.columns):
        transcript_ids = set(tdf.loc[tdf["대본상태"].eq("성공"), "video_id"].astype(str))
    rows = []
    for _, row in df.head(14).iterrows():
        obs = {key: _scalar(row.get(key)) for key in COLUMNS if key in df.columns}
        obs["video_id"] = str(obs.get("video_id") or "")
        obs["원문확보"] = obs["video_id"] in transcript_ids
        if not obs.get("영상링크") and re.fullmatch(r"[A-Za-z0-9_-]{11}", obs["video_id"]):
            obs["영상링크"] = "https://www.youtube.com/watch?v=" + obs["video_id"]
        rows.append(obs)
    return {
        "검토주제": str(topic or "")[:200],
        "시장후보수": len(rows),
        "서로다른채널수": len(set(str(r.get("채널")) for r in rows if r.get("채널"))),
        "실제자막확보수": sum(bool(r["원문확보"]) for r in rows),
        "경쟁영상": rows,
        "해석한계": (
            "이 자료는 검색/추천 후보 표본이며 시장 전체가 아님. 조회수는 업로드 기간과 채널 규모 영향을 받음. "
            "조회수나 채널배수만으로 성공 원인이나 미래 조회수를 증명하지 못함. "
            "Transcript가 없는 영상의 내부 구성은 검증하지 못함. 새로운 주제는 별도 검색·자막 수집이 필요함."
        ),
    }


def parse_topic_decision(report: str, allowed_video_ids: set[str] | None = None) -> dict:
    """Accept machine-readable decisions only; never manufacture one."""
    m = re.search(r"<TOPIC_DECISION_JSON>\s*(\{.*?\})\s*</TOPIC_DECISION_JSON>",
                  str(report or ""), re.DOTALL)
    if not m:
        return {"valid": False, "error": "주제 결정 구조화 결과가 없습니다. 보고서 원문을 확인하세요."}
    try:
        obj = json.loads(m.group(1))
    except (json.JSONDecodeError, TypeError):
        return {"valid": False, "error": "주제 결정 JSON 형식이 올바르지 않습니다."}
    if not isinstance(obj, dict) or obj.get("action") not in VALID_ACTIONS:
        return {"valid": False, "error": "주제 결정 값이 유효하지 않습니다."}
    topic = str(obj.get("topic") or "").strip()[:200]
    if obj["action"] != "KEEP" and len(topic) < 3:
        return {"valid": False, "error": "변경할 주제가 명시되지 않았습니다."}
    raw_ids = obj.get("evidence_video_ids") or []
    if not isinstance(raw_ids, list):
        raw_ids = []
    allowed = allowed_video_ids if allowed_video_ids is not None else set()
    verified_ids = [str(v) for v in raw_ids if str(v) in allowed][:10]
    confidence = obj.get("confidence") if obj.get("confidence") in {"HIGH", "MEDIUM", "LOW"} else "LOW"
    return {
        "valid": True,
        "action": obj["action"], "topic": topic,
        "reason": str(obj.get("reason") or "")[:550],
        "evidence_video_ids": verified_ids,
        "confidence": confidence,
        "warning": "시장 검증된 신규 주제라는 뜻이 아님" if obj["action"] == "RESEARCH_NEW" else "",
    }
