from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def _safe(value):
    if isinstance(value, pd.DataFrame):
        return [_safe(x) for x in value.to_dict("records")]
    if isinstance(value, pd.Series):
        return [_safe(x) for x in value.tolist()]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe(v) for v in value]
    return value


def slugify(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", str(text or "").strip())
    return text.strip("_")[:50] or "run"


class RunStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_a_product_run(self, research: dict, package: dict, draft_a: dict) -> Path:
        now = datetime.now().astimezone()
        query = research.get("query", "run")
        run_id = now.strftime("%Y%m%d_%H%M%S") + "_" + slugify(query)
        path = self.root / f"{run_id}.json"

        # Embedding/원문 전체를 복제하지 않고, 재현·비교에 필요한 결과만 저장한다.
        payload = {
            "run_id": run_id,
            "created_at": now.isoformat(),
            "query": query,
            "idea_brief": research.get("idea_brief"),
            "market_result": research.get("market_result"),
            "opportunities": research.get("opportunity_df"),
            "content_candidates": research.get("content_candidates"),
            "selected_content_index": package.get("selected_content_index"),
            "selected_candidate": package.get("selected_candidate"),
            "design_pack": package.get("design_pack"),
            "memory_ingest": package.get("memory_ingest"),
            "structure_result": package.get("structure_result"),
            "transcript_coverage": research.get("transcript_coverage"),
            "content_patterns": research.get("content_patterns"),
            "studio_context": package.get("studio_context"),
            # Freeze common research evidence for independent Hermes/A comparison.
            # No Draft A, A-derived blueprint or credentials are included in this pack.
            "experiment_evidence": {
                "market_audit": package.get("market_audit") or {},
                "market_sources": [
                    {"video_id": r.get("video_id"), "제목": r.get("제목"),
                     "텍스트": str(r.get("텍스트") or "")[:1300]}
                    for r in (_safe(package.get("market_sources")) or [])[:16] if isinstance(r, dict)
                ],
                "my_sources": [
                    {"video_id": r.get("video_id"), "제목": r.get("제목"),
                     "텍스트": str(r.get("텍스트") or "")[:1300]}
                    for r in (_safe(package.get("my_sources")) or [])[:10] if isinstance(r, dict)
                ],
                "market_video_analysis": (_safe(package.get("relevant_market_analysis")) or [])[:12],
            },
            "draft_a": draft_a,
            # Draft B Critic/Final은 생성되는 즉시 같은 run 파일에 이어서 저장한다.
            "critic_report": None,
            "draft_b": None,
            "human_feedback": None,
            "final_script": None,
        }
        path.write_text(json.dumps(_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")
        return path
    def append_revision(self, path: str | Path, feedback: str, revised_script: dict) -> None:
        path = Path(path)
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        revisions = payload.setdefault("draft_a_revisions", [])
        revisions.append({
            "created_at": datetime.now().astimezone().isoformat(),
            "feedback": feedback,
            "script": _safe(revised_script),
        })
        payload["human_feedback"] = feedback
        path.write_text(json.dumps(_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")


    def save_agent_outputs(self, path: str | Path, agent_bundle: dict) -> None:
        path = Path(path)
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        payload["benchmark_reference"] = _safe(agent_bundle.get("benchmark_reference"))
        payload["critic_report"] = agent_bundle.get("critic_report")
        payload["critic_sources"] = _safe(agent_bundle.get("critic_sources") or [])
        payload["critic_model"] = agent_bundle.get("critic_model")
        payload["critic_web_used"] = agent_bundle.get("critic_web_used")
        payload["critic_tool_trace"] = _safe(agent_bundle.get("critic_tool_trace") or [])
        payload["critic_web_attempted"] = agent_bundle.get("critic_web_attempted", 0)
        payload["critic_web_completed"] = agent_bundle.get("critic_web_completed", 0)
        payload["topic_decision"] = _safe(agent_bundle.get("topic_decision") or {})
        payload["market_audit"] = _safe(agent_bundle.get("market_audit") or {})
        payload["draft_b"] = _safe(agent_bundle.get("draft_b"))
        payload["ab_comparison"] = _safe(agent_bundle.get("comparison"))
        path.write_text(json.dumps(_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")

    def save_final_script(self, path: str | Path, feedback: str, final_script: dict) -> None:
        path = Path(path)
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return
        payload["human_feedback"] = feedback
        payload["final_script"] = _safe(final_script)
        path.write_text(json.dumps(_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")
