from __future__ import annotations

from typing import Any


def bullet_lines(items):
    return "\n".join(f"- {x}" for x in (items or [])) or "- 없음"


def script_to_markdown(script: dict, title: str = "Draft A") -> str:
    lines = [f"# {title}", ""]
    if script.get("핵심세일즈포인트"):
        lines += ["## 핵심 세일즈 포인트", script.get("핵심세일즈포인트", ""), ""]
    lines += ["## 제목 후보", bullet_lines(script.get("제목후보")), ""]
    lines += ["## 썸네일 문구 후보", bullet_lines(script.get("썸네일문구후보")), ""]
    lines += ["## 오프닝", script.get("오프닝", ""), ""]

    for i, part in enumerate(script.get("파트별대본", []), start=1):
        lines += [f"## {i}. {part.get('파트', f'파트 {i}')}" ]
        purpose = part.get("목적")
        if purpose:
            lines += [f"**목적:** {purpose}", ""]
        lines += [part.get("대본", ""), ""]
        rewards = part.get("보상포인트", [])
        if rewards:
            lines += ["**보상 포인트**", bullet_lines(rewards), ""]
        examples = part.get("예시또는화면", [])
        if examples:
            lines += ["**예시 / 화면 아이디어**", bullet_lines(examples), ""]

    if script.get("최종지도"):
        lines += ["## 최종 지도", script.get("최종지도", ""), ""]
    lines += ["## 마무리", script.get("마무리", ""), ""]
    caution = script.get("근거상주의할점", [])
    if caution:
        lines += ["## 근거상 주의할 점", bullet_lines(caution), ""]
    room = script.get("촬영여백", [])
    if room:
        lines += ["## 촬영 여백", bullet_lines(room), ""]
    return "\n".join(lines).strip() + "\n"


def structure_to_markdown(structure: dict) -> str:
    lines = ["# Structure Blueprint", ""]
    for key in ["콘텐츠유형", "핵심문제", "시청자변화", "핵심보상", "핵심엣지", "오프닝약속"]:
        if key in structure:
            lines += [f"## {key}", str(structure.get(key, "")), ""]

    if structure.get("보조엣지"):
        lines += ["## 보조 Edge", bullet_lines(structure.get("보조엣지")), ""]
    if structure.get("오프닝문제"):
        lines += ["## 오프닝문제", bullet_lines(structure.get("오프닝문제")), ""]

    for key in ["유지할것", "개선할것", "시장에서참고할것", "새로추가할것", "이번영상핵심과제", "보상감사", "피해야할것"]:
        if key in structure:
            lines += [f"## {key}", bullet_lines(structure.get(key, [])), ""]

    for i, part in enumerate(structure.get("구조블루프린트", []), start=1):
        lines += [f"## {i}. {part.get('파트', '')}"]
        lines += [f"**목적:** {part.get('목적', '')}"]
        lines += [f"**시청자 상태:** {part.get('시청자상태', '')}", ""]
        lines += ["**핵심 내용**", bullet_lines(part.get("핵심내용", [])), ""]
        if part.get("사용할보상"):
            lines += ["**사용할 보상**", bullet_lines(part.get("사용할보상", [])), ""]
        lines += [f"**다음 파트 연결:** {part.get('다음파트연결', '')}", ""]

    if structure.get("최종지도"):
        lines += ["## 최종 지도", structure.get("최종지도", ""), ""]
    return "\n".join(lines).strip() + "\n"


def short_text(value: Any, limit: int = 220) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"
