from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


class ContentPatternMemoryStore:
    """Persistent market-learned content pattern memory.

    The system does not force videos into a fixed taxonomy. Each Deep Research run
    extracts a Content DNA for transcript-backed videos, asks the LLM to cluster the
    observed structures, and stores those discovered clusters here. The store is
    intentionally JSON so it can be inspected or exported later.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"version": 1, "patterns": [], "runs": []})

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("invalid content pattern memory")
            data.setdefault("patterns", [])
            data.setdefault("runs", [])
            return data
        except Exception:
            return {"version": 1, "patterns": [], "runs": []}

    def _write(self, data: dict):
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", str(text or "").strip().lower())

    @classmethod
    def _pattern_id(cls, pattern: dict) -> str:
        signature = "|".join([
            cls._norm(pattern.get("클러스터명", "")),
            cls._norm(pattern.get("핵심구조", "")),
            cls._norm(pattern.get("핵심보상", "")),
            cls._norm(pattern.get("참여방식", "")),
        ])
        return hashlib.sha1(signature.encode("utf-8")).hexdigest()[:16]

    def ingest_run(self, query: str, clusters: list[dict], video_dna: list[dict], coverage: dict | None = None) -> dict:
        data = self._read()
        now = datetime.now().astimezone().isoformat()
        existing = {p.get("id"): p for p in data["patterns"]}
        saved_ids = []

        for raw in clusters or []:
            pid = self._pattern_id(raw)
            saved_ids.append(pid)
            evidence_ids = list(dict.fromkeys(raw.get("video_ids") or []))
            payload = {
                "id": pid,
                "name": raw.get("클러스터명", ""),
                "description": raw.get("설명", ""),
                "audience_problem": raw.get("시청자문제", ""),
                "promise": raw.get("핵심약속", ""),
                "knowledge_role": raw.get("지식역할", ""),
                "structure": raw.get("핵심구조", ""),
                "reward": raw.get("핵심보상", ""),
                "participation": raw.get("참여방식", ""),
                "evidence_device": raw.get("증거장치", ""),
                "result": raw.get("시청자결과", ""),
                "title_promise": raw.get("제목약속", ""),
                "audience_age_context": raw.get("예상연령맥락", ""),
                "audience_knowledge": raw.get("예상지식수준", ""),
                "audience_performance": raw.get("예상수행수준", ""),
                "common_points": raw.get("공통점", []),
                "variations": raw.get("변형", []),
                "video_ids": evidence_ids,
                "performance_note": raw.get("성과해석", ""),
                "recent_note": raw.get("최근신호", ""),
                "confidence": raw.get("확신", "낮음"),
                "query_examples": [query] if query else [],
                "times_seen": 1,
                "created_at": now,
                "updated_at": now,
            }
            if pid in existing:
                old = existing[pid]
                old["updated_at"] = now
                old["times_seen"] = int(old.get("times_seen", 1)) + 1
                old["video_ids"] = list(dict.fromkeys((old.get("video_ids") or []) + evidence_ids))[:80]
                old["query_examples"] = list(dict.fromkeys((old.get("query_examples") or []) + ([query] if query else [])))[:20]
                for key, value in payload.items():
                    if key not in {"id", "created_at", "times_seen", "video_ids", "query_examples"} and value:
                        old[key] = value
            else:
                data["patterns"].append(payload)
                existing[pid] = payload

        data["runs"].append({
            "query": query,
            "created_at": now,
            "coverage": coverage or {},
            "cluster_ids": saved_ids,
            "video_dna": video_dna or [],
        })
        data["runs"] = data["runs"][-50:]
        self._write(data)
        return {"saved_pattern_ids": saved_ids, "pattern_count": len(data["patterns"])}

    def recent_patterns(self, limit: int = 12) -> list[dict]:
        patterns = self._read().get("patterns", [])
        return sorted(patterns, key=lambda x: (x.get("updated_at", ""), x.get("times_seen", 0)), reverse=True)[:limit]

    def prompt_context(self, limit: int = 12) -> list[dict]:
        out = []
        for p in self.recent_patterns(limit):
            out.append({
                "클러스터명": p.get("name"),
                "설명": p.get("description"),
                "시청자문제": p.get("audience_problem"),
                "핵심약속": p.get("promise"),
                "지식역할": p.get("knowledge_role"),
                "핵심구조": p.get("structure"),
                "핵심보상": p.get("reward"),
                "참여방식": p.get("participation"),
                "성과해석": p.get("performance_note"),
                "최근신호": p.get("recent_note"),
                "예상연령맥락": p.get("audience_age_context"),
                "예상지식수준": p.get("audience_knowledge"),
                "예상수행수준": p.get("audience_performance"),
                "반복발견횟수": p.get("times_seen", 1),
                "확신": p.get("confidence", "낮음"),
            })
        return out

    def stats(self) -> dict:
        data = self._read()
        return {"patterns": len(data.get("patterns", [])), "runs": len(data.get("runs", []))}
