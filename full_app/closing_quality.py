"""Cheap, conservative script ending warnings; not a semantic-quality oracle."""
from __future__ import annotations
import re


def ending_warnings(script: dict | None) -> list[str]:
    closing = str((script or {}).get("마무리") or "").strip()
    if not closing:
        return ["마무리가 비어 있습니다. 첫 문제의 답과 학습 성취를 회수해 주세요."]
    notes = []
    if len(closing) < 40:
        notes.append("마무리가 매우 짧습니다. 도입 문제를 회수했는지 확인하세요.")
    tail = re.sub(r"\s+", " ", closing[-100:]).strip()
    if re.search(r"(?:댓글|코멘트|comment)[^.!?。]*?(?:남겨|달아|적어|주세요|봐요|주시면|주십시오)", tail, flags=re.IGNORECASE):
        notes.append("댓글 요청이 결말을 대신할 수 있습니다. 교육적 결론을 먼저 끝내세요.")
    if closing.endswith(("?", "？")):
        notes.append("마지막 문장이 질문형입니다. 해답 없이 열린 결말로 끝나지 않는지 확인하세요.")
    return notes
