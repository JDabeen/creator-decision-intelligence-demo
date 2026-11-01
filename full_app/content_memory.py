from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable


class ContentMemoryStore:
    """Persistent local memory for content ideas, explanation observations, and Content Edges.

    This is deliberately simple JSON storage so the user can inspect/export it easily.
    It stores both manual notes and automatically extracted research insights.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"version": 1, "items": []})

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("items"), list):
                raise ValueError("invalid content memory format")
            return data
        except Exception:
            return {"version": 1, "items": []}

    def _write(self, data: dict):
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", str(text or "").strip().lower())

    @classmethod
    def _stable_id(cls, kind: str, topic: str, title: str, detail: str) -> str:
        raw = "|".join(map(cls._norm, [kind, topic, title, detail]))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def upsert_items(self, items: Iterable[dict], *, source_kind: str, source_context: str = "") -> list[str]:
        data = self._read()
        existing = {x.get("id"): x for x in data["items"]}
        now = datetime.now().astimezone().isoformat()
        saved_ids: list[str] = []

        for raw in items:
            kind = str(raw.get("kind") or raw.get("종류") or "idea").strip()
            topic = str(raw.get("topic") or raw.get("주제") or "").strip()
            title = str(raw.get("title") or raw.get("제목") or raw.get("엣지") or raw.get("개념") or "").strip()
            detail = str(raw.get("detail") or raw.get("내용") or raw.get("핵심주장") or raw.get("왜특별한가") or "").strip()
            if not (title or detail):
                continue
            item_id = self._stable_id(kind, topic, title, detail)
            saved_ids.append(item_id)

            payload = {
                "id": item_id,
                "kind": kind,
                "topic": topic,
                "title": title,
                "detail": detail,
                "why_valuable": str(raw.get("why_valuable") or raw.get("왜가치있는가") or raw.get("왜특별한가") or "").strip(),
                "next_use": str(raw.get("next_use") or raw.get("다음활용") or raw.get("영상사용위치") or "").strip(),
                "novelty": str(raw.get("novelty") or raw.get("시장에흔한정도") or "").strip(),
                "origin": str(raw.get("origin") or raw.get("발견방식") or "").strip(),
                "risk": str(raw.get("risk") or raw.get("위험") or raw.get("충돌및정확성주의") or "").strip(),
                "evidence": raw.get("evidence") or raw.get("근거") or [],
                "source_kind": source_kind,
                "source_context": source_context,
                "status": str(raw.get("status") or "candidate"),
                "used_in": raw.get("used_in") or [],
                "created_at": now,
                "updated_at": now,
                "times_seen": 1,
            }

            if item_id in existing:
                old = existing[item_id]
                payload["created_at"] = old.get("created_at", now)
                payload["times_seen"] = int(old.get("times_seen", 1)) + 1
                payload["used_in"] = old.get("used_in", [])
                if old.get("status") == "used":
                    payload["status"] = "used"
                # Preserve richer previous fields if the new extraction is sparse.
                for key in ["why_valuable", "next_use", "novelty", "origin", "risk", "evidence"]:
                    if not payload.get(key):
                        payload[key] = old.get(key)
                old.update(payload)
            else:
                data["items"].append(payload)
                existing[item_id] = payload

        self._write(data)
        return saved_ids

    def add_manual_items(self, items: Iterable[dict], source_context: str = "manual note") -> list[str]:
        return self.upsert_items(items, source_kind="manual", source_context=source_context)

    def ingest_design_pack(self, topic: str, design_pack: dict, source_context: str = "research") -> dict:
        items: list[dict] = []
        core = design_pack.get("핵심엣지추천") or {}
        core_id = None
        if core.get("엣지"):
            core_payload = {
                "kind": "core_edge",
                "topic": topic,
                "title": core.get("엣지"),
                "detail": core.get("한줄세일즈포인트") or core.get("선택이유", ""),
                "why_valuable": core.get("선택이유", ""),
                "next_use": "제목/썸네일/오프닝/본문의 중심 약속",
                "risk": "; ".join(core.get("검증할것", []) or []),
                "evidence": core.get("근거", []),
            }
            ids = self.upsert_items([core_payload], source_kind="auto_research", source_context=source_context)
            core_id = ids[0] if ids else None

        for edge in design_pack.get("콘텐츠엣지후보", []) or []:
            items.append({
                "kind": "content_edge",
                "topic": topic,
                "title": edge.get("엣지", ""),
                "detail": edge.get("왜특별한가", ""),
                "why_valuable": edge.get("시청자보상", ""),
                "next_use": edge.get("영상사용위치", ""),
                "novelty": edge.get("시장에흔한정도", ""),
                "origin": edge.get("발견방식", ""),
                "risk": edge.get("위험", ""),
                "evidence": edge.get("근거", []),
            })

        for obs in design_pack.get("자료별특이점", []) or []:
            detail_parts = []
            for key in ["좋은점", "특이점", "겹치는설명", "비어있는점", "가져올원리"]:
                value = obs.get(key)
                if value:
                    detail_parts.append(f"{key}: {value}")
            items.append({
                "kind": "source_observation",
                "topic": topic,
                "title": obs.get("자료", "자료 관찰"),
                "detail": " | ".join(detail_parts),
                "why_valuable": obs.get("가져올원리", ""),
                "risk": obs.get("복제금지요소", ""),
            })

        for cluster in design_pack.get("개념클러스터", []) or []:
            items.append({
                "kind": "common_explanation",
                "topic": topic,
                "title": cluster.get("개념", ""),
                "detail": "공통점: " + "; ".join(cluster.get("공통점", []) or []),
                "why_valuable": cluster.get("새구조기회", ""),
                "risk": "; ".join(cluster.get("충돌", []) or []),
            })

        saved = self.upsert_items(items, source_kind="auto_research", source_context=source_context) if items else []
        return {"core_edge_id": core_id, "saved_ids": saved, "saved_count": len(saved) + (1 if core_id else 0)}

    def mark_used(self, item_id: str | None, used_in: str):
        if not item_id:
            return
        data = self._read()
        changed = False
        now = datetime.now().astimezone().isoformat()
        for item in data["items"]:
            if item.get("id") == item_id:
                item["status"] = "used"
                used = list(item.get("used_in") or [])
                if used_in and used_in not in used:
                    used.append(used_in)
                item["used_in"] = used
                item["updated_at"] = now
                changed = True
                break
        if changed:
            self._write(data)

    def all_items(self) -> list[dict]:
        items = self._read()["items"]
        return sorted(items, key=lambda x: x.get("updated_at", ""), reverse=True)

    def recent(self, limit: int = 20) -> list[dict]:
        return self.all_items()[:limit]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        q = self._norm(query)
        if not q:
            return self.recent(limit)
        q_tokens = set(re.findall(r"[0-9a-zA-Z가-힣]+", q))
        scored = []
        for item in self.all_items():
            hay = self._norm(" ".join([
                str(item.get("topic", "")), str(item.get("title", "")), str(item.get("detail", "")),
                str(item.get("why_valuable", "")), str(item.get("next_use", "")),
            ]))
            tokens = set(re.findall(r"[0-9a-zA-Z가-힣]+", hay))
            score = len(q_tokens & tokens)
            if q and q in hay:
                score += 3
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: (x[0], x[1].get("updated_at", "")), reverse=True)
        return [x[1] for x in scored[:limit]]

    def prompt_context(self, query: str = "", limit: int = 18) -> list[dict]:
        items = self.search(query, limit=limit) if query else self.recent(limit=limit)
        return [
            {
                "종류": x.get("kind"),
                "주제": x.get("topic"),
                "제목": x.get("title"),
                "내용": x.get("detail"),
                "가치": x.get("why_valuable"),
                "다음활용": x.get("next_use"),
                "희소성": x.get("novelty"),
                "발견방식": x.get("origin"),
                "상태": x.get("status"),
                "사용된영상": x.get("used_in"),
                "반복발견횟수": x.get("times_seen", 1),
            }
            for x in items
        ]
