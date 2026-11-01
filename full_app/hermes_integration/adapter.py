"""Narrow HTTP bridge to the Docker-isolated Hermes API server.

Only the preselected Research/Draft A TEXT is sent through this bridge.
No project directories, Windows paths, credentials or host OS tools are exposed.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from topic_quality import public_source_url

DEFAULT_URL = "http://127.0.0.1:8642"


class HermesConnectionError(RuntimeError):
    """Explicitly report an unavailable Hermes rather than silently fallback."""


def _secret_file() -> Path:
    return Path.home() / ".youtube_consultant_hermes_gateway_key"


def get_gateway_key() -> str:
    key = os.getenv("YRA_HERMES_API_KEY", "").strip()
    if not key and _secret_file().is_file():
        key = _secret_file().read_text(encoding="utf-8").strip()
    if not key:
        raise HermesConnectionError("Hermes 인증 키가 없습니다. 0_START_WITH_HERMES.bat을 먼저 실행하세요.")
    return key


def _endpoint(path: str) -> str:
    # The address is deliberately fixed to localhost to avoid accidentally
    # sending private transcript snippets to a remote endpoint.
    return DEFAULT_URL + path


def _call(path: str, method: str, data: dict | None, timeout: int = 10) -> dict:
    headers = {"Authorization": "Bearer " + get_gateway_key(), "Content-Type": "application/json"}
    request = Request(
        _endpoint(path),
        data=json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(3 * 1024 * 1024)
        return json.loads(raw.decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read(400).decode("utf-8", "replace")
        raise HermesConnectionError(f"Hermes API HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        # Helpful localhost diagnostics, without including authentication tokens.
        reason = str(getattr(exc, "reason", exc))[:130]
        raise HermesConnectionError(
            "Hermes localhost API 연결 실패 (" + type(exc).__name__ + "): " + reason
        ) from exc
    except (ValueError, UnicodeError) as exc:
        raise HermesConnectionError("Hermes API 응답을 JSON으로 읽지 못했습니다.") from exc


def check_ready(*, require_web: bool = False) -> str:
    """Authenticated readiness and bounded tool policy verification.

    Fail closed if the active Hermes agent exposes file/terminal/etc tools,
    even if our generated YAML attempted to disable them.
    """
    toolsets = _call("/v1/toolsets", "GET", None, timeout=10)
    # Hermes API versions return either a raw list or an OpenAI-style
    # {"object":"list", "data":[...]} response. Older builds also used
    # {"toolsets":[...]}. Never bypass the tool audit on unfamiliar shapes.
    if isinstance(toolsets, list):
        rows = toolsets
    elif isinstance(toolsets, dict):
        rows = toolsets.get("data")
        if rows is None:
            rows = toolsets.get("toolsets")
    else:
        rows = None
    if not isinstance(rows, list) or not rows:
        shape = ",".join(sorted(toolsets.keys())) if isinstance(toolsets, dict) else type(toolsets).__name__
        raise HermesConnectionError(
            "Hermes 도구 목록 응답 형식을 확인할 수 없어 연결을 차단했습니다 "
            f"(응답 필드: {shape[:100]})."
        )
    active_tools: set[str] = set()
    for group in rows:
        if not isinstance(group, dict) or not isinstance(group.get("enabled"), bool):
            raise HermesConnectionError("Hermes 도구 항목 형식이 예상과 달라 연결을 차단했습니다.")
        if group["enabled"]:
            tools = group.get("tools")
            if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
                raise HermesConnectionError("Hermes 활성 도구의 상세 목록이 누락되어 연결을 차단했습니다.")
            active_tools.update(tools)
    # Browser capability names are explicitly bounded; unknown and OS/desktop
    # tools still trigger a fail-closed error. Hermes includes browser_vault_*
    # in the built-in browser toolset; their presence does NOT mean any login
    # was saved or that the host Chrome profile is available. Do not confuse
    # an API tool-list audit with a per-tool execution policy: Hermes currently
    # configures its built-in browser tools as a group, not individually.
    # Internet-enabled agents can still transmit received data externally.
    browser_tools = {
        "browser_navigate", "browser_snapshot", "browser_scroll", "browser_back",
        "browser_click", "browser_type", "browser_press", "browser_vision",
        "browser_get_images", "browser_dialog", "browser_cdp", "browser_console",
        "browser_exec", "browser_tabs", "browser_tab_activate",
        "browser_screenshot",
        # The five official built-in browser-vault tools accompany the
        # browser toolset even when no credential vault has been configured.
        # Explicit names only: new/unrecognized tools still fail closed.
        "browser_vault_enter_code", "browser_vault_fill",
        "browser_vault_list", "browser_vault_save_login",
        "browser_vault_unlock",
    }
    allowed = {"web_search", "web_extract", "tool_search"} | browser_tools
    unsafe = active_tools - allowed
    vault_tools = {name for name in active_tools if name.startswith("browser_vault_")}
    if vault_tools and "browser_navigate" not in active_tools:
        raise HermesConnectionError(
            "Hermes 격리 정책 위반: 브라우저 탐색 도구 없이 vault 도구만 노출됐습니다. "
            "Hermes 설정을 다시 확인하세요."
        )
    if unsafe:
        raise HermesConnectionError(
            "Hermes 격리 정책 위반: 허용하지 않은 도구 감지 (" + ", ".join(sorted(unsafe)[:8]) + "). "
            "Hermes 설정을 다시 확인하세요."
        )
    if require_web and not ("web_search" in active_tools or {"browser_navigate", "browser_snapshot"} <= active_tools):
        raise HermesConnectionError(
            "Hermes API 연결은 됐지만 웹 검색/브라우저 탐색 도구가 비활성화됐습니다. "
            "Hermes API 도구 설정(platform_toolsets.api_server)을 확인하세요."
        )
    models = _call("/v1/models", "GET", None, timeout=10)
    data = models.get("data", [])
    if not isinstance(data, list) or not data:
        raise HermesConnectionError("Hermes API가 실행 중이지만 모델 목록이 비어 있습니다.")
    return str(data[0].get("id") or "hermes-agent")


def _flatten_response(reply: dict) -> tuple[str, list[dict], bool, list[dict], int, int]:
    """Audit actual Hermes tool events, not the agent's prose about web use.

    Response API may omit tool outputs or expose a failed call. Such cases are
    shown as 'attempted/unverified', never as successful research.
    """
    reports: list[str] = []
    events: list[dict] = []
    indexed: dict[str, int] = {}
    sources: list[dict] = []
    seen_urls: set[str] = set()
    attempts = completed = 0
    browser_page_url = ""
    browser_snapshot_ok = False
    browser_nav_ok = False
    for item in reply.get("output", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        event_type = str(item.get("type") or "")
        if event_type == "function_call" and name in {"web_search", "web_extract", "browser_navigate", "browser_snapshot"}:
            attempts += 1
            call_id = str(item.get("call_id") or "")
            args = item.get("arguments") or {}
            try:
                args = json.loads(args) if isinstance(args, str) else args
            except (TypeError, ValueError):
                args = {}
            # Never display raw tool args, which could contain private context.
            request = ""
            if isinstance(args, dict):
                request = str(args.get("query") or args.get("queries") or args.get("url") or args.get("search_query") or "")[:180]
            if name == "browser_navigate" and isinstance(args, dict):
                browser_page_url = str(args.get("url") or "")[:2048]
            event = {"tool": name, "request": request, "status": "응답 미확인", "sources": []}
            if call_id:
                indexed[call_id] = len(events)
            events.append(event)
        elif event_type == "function_call_output":
            call_id = str(item.get("call_id") or "")
            idx = indexed.get(call_id) if call_id else None
            if idx is None and events:
                # Some older responses omit call_id; only use a single
                # outstanding call, so evidence never attaches ambiguously.
                pending = [i for i, e in enumerate(events) if e["status"] == "응답 미확인"]
                if len(pending) == 1:
                    idx = pending[0]
            if idx is None:
                continue
            output = item.get("output")
            result = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False, default=str)
            status = str(item.get("status") or "").lower()
            error_obj = False
            if isinstance(output, dict):
                error_obj = bool(output.get("error") or output.get("errors") or output.get("success") is False)
            elif isinstance(output, str) and output.lstrip().startswith("{"):
                try:
                    parsed = json.loads(output)
                    error_obj = isinstance(parsed, dict) and bool(parsed.get("error") or parsed.get("errors") or parsed.get("success") is False)
                except (ValueError, TypeError):
                    pass
            failed = bool(error_obj or status in {"failed", "error"} or re.search(
                r"^\s*(?:error:|failed:|tool error:|traceback|unauthorized|rate limit exceeded)", result, re.I))
            if failed:
                events[idx]["status"] = "오류"
                continue
            completed += 1
            if events[idx]["tool"] == "browser_navigate":
                browser_nav_ok = True
            elif events[idx]["tool"] == "browser_snapshot":
                browser_snapshot_ok = True
            events[idx]["status"] = "도구 응답 확인"
            urls = re.findall(r"https?://[^\s\"'<>]+", result)
            for url in urls[:15]:
                url = url.rstrip(".,);]}")
                if url not in seen_urls and public_source_url(url):
                    seen_urls.add(url)
                    sources.append({"title": url, "url": url})
                    events[idx]["sources"].append(url)
        elif event_type == "message" and item.get("role") == "assistant":
            for part in item.get("content", []):
                if isinstance(part, dict) and part.get("type") in {"output_text", "text"}:
                    reports.append(str(part.get("text", "")))
    # A browser URL is evidence only if both navigation AND a page snapshot
    # were actually returned. The navigation command alone is insufficient.
    if browser_nav_ok and browser_snapshot_ok and public_source_url(browser_page_url):
        if browser_page_url not in seen_urls:
            sources.append({"title": browser_page_url, "url": browser_page_url})
            seen_urls.add(browser_page_url)
    report = "\n".join(reports).strip() or str(reply.get("output_text") or "").strip()
    return report, sources[:20], completed > 0, events[:12], attempts, completed


def run_verified_web_research(topic: str, *, purpose: str = "general") -> dict:
    """Run one focused Hermes tool-using turn and require *observable* web evidence.

    No answer-only response can pass. Verified web_search, or browser page read
    as a fallback. No terminal, local files, project mounts, or provider changes.
    """
    model = check_ready(require_web=True)
    title = str(topic or "영어 교육").strip()[:150]
    purpose_note = (
        "이번 검색의 목적은 기존 채널의 잘된 주제와 후속/인접 수요를 검증하고, 필요할 때 새로운 시청자 수요를 조사하는 것이다. "
        "이미 잘된 주제를 더 발전시키는 경쟁 사례와 새 주제 사례를 함께 조사하되 새로움 자체를 목표로 하지 마라. "
        "검색 결과의 채널·영상 URL을 확인하지 않고 그 성과를 주장하지 마라. "
        if purpose == "youtube_topics" else ""
    )
    response = _call(
        "/v1/responses", "POST",
        {
            "model": model,
            "instructions": (
                "너는 근거를 수집하는 조사 에이전트다. 이 요청은 도구 작동 진단을 겸한다. "
                "말로 검색했다고 주장하지 말고 실제 web_search를 호출하라. 검색을 사용할 수 없을 때만 browser_navigate와 browser_snapshot으로 공개 웹페이지를 확인하라. "
                "도구를 사용할 수 없다면 사용할 수 없다고 답하라. "
                "terminal, 파일, 컴퓨터 제어, 계정 로그인, 양식 제출, 구매, 댓글 작성은 금지한다. 댓글 절대 수는 수요 반응 단서로만 참고하고, 댓글/조회수 비율이나 구매 확률을 생성하지 않는다. "
                "browser_vault_* 비밀번호/로그인 관리 도구는 사용하지 마라. "
                "file://, localhost, 내부 주소 대신 공개 https 웹페이지만 읽어라. "
                "검색 결과를 확인하지 않은 내용은 검증됐다고 주장하지 말라." + purpose_note
            ),
            "input": (
                f"조사 주제: {title}\n"
                "영어교육 관련 신뢰할 수 있는 공개 자료를 web_search로 검색하라. 불가능하면 browser_navigate와 browser_snapshot을 사용하라. "
                + ("유튜브 경쟁 영상 및 학습자 질문 관련 검색 질의 2개를 시도하라. " if purpose == "youtube_topics" else "가능하면 검색 질의 2개(학습 원리, 실제 경쟁 콘텐츠)를 순서대로 시도하라. ")
                + "실제 검색 결과를 바탕으로 제목·URL·핵심 요약만 간결하게 알려줘. "
                "검색 도구 사용이 불가하다면 즉시 불가 사유를 말하라."
            ),
            "store": False,
        },
        timeout=int(os.getenv("YRA_HERMES_TIMEOUT", "240")),
    )
    report, sources, used, trace, attempted, completed = _flatten_response(response)
    if attempted == 0:
        raise HermesConnectionError(
            "Hermes는 비평 답변만 생성했고 실제 웹 검색/페이지 읽기 호출은 0회였습니다. "
            "API의 웹 도구가 비평 모델에 노출/선택되는지 확인해야 합니다. "
            "웹 검색이 없는 대본을 시장 추가 조사 완료로 처리하지 않습니다."
        )
    if completed == 0:
        raise HermesConnectionError(
            "Hermes가 웹 도구 호출을 시도했으나 성공한 응답은 0회입니다. "
            "Hermes web backend의 설정·사용량·접속을 확인하세요. "
            "검색 실패 기록: " + ", ".join(e.get('status', '?') for e in trace)[:100]
        )
    if not sources:
        raise HermesConnectionError(
            "Hermes 외부 조사 도구 호출은 확인됐지만 확인 가능한 출처 URL이 없습니다. "
            "실제 외부 근거가 확인되지 않아 시장 재설계를 중단합니다."
        )
    return {"report": report[:8000], "sources": sources, "tool_trace": trace,
            "web_attempted": attempted, "web_completed": completed,
            "usage": response.get("usage") or {}}


def run_hermes_critic(instructions: str, user_prompt: str) -> dict:
    model = check_ready()
    if len(user_prompt) > 180_000:
        raise ValueError("Hermes 입력 데이터가 너무 큽니다. Research 자료량을 줄여주세요.")
    response = _call(
        "/v1/responses", "POST",
        {
            "model": model,
            "instructions": instructions + (
                "\nHermes는 read-only 연구 비평가다. 로컬 파일 수정, 터미널, 시스템 제어, "
                "스킬 설치, browser_vault_* 로그인 도구, 계정 로그인, 개인 데이터 요청 없이 "
                "전달받은 근거와 허용된 공개 웹 검색/브라우저 읽기만 사용한다. "
                "최종 Critic Report는 한국어로 작성한다."
            ),
            "input": user_prompt,
            "store": False,
        },
        timeout=int(os.getenv("YRA_HERMES_TIMEOUT", "240")),
    )
    report, sources, web_used, trace, attempts, completed = _flatten_response(response)
    if not report:
        raise HermesConnectionError("Hermes는 응답했지만 Critic Report가 비어 있습니다. Docker 로그를 확인하세요.")
    usage_obj = response.get("usage") or {}
    usage = {
        "input_tokens": usage_obj.get("input_tokens", 0),
        "output_tokens": usage_obj.get("output_tokens", 0),
        "total_tokens": usage_obj.get("total_tokens", 0),
    }
    return {
        "report": report,
        "sources": sources,
        "model": "Hermes Agent / " + model,
        "web_enabled": True,
        "web_used": web_used,
        "usage": usage,
        "tool_trace": trace,
        "web_attempted": attempts,
        "web_completed": completed,
        "warning": "" if web_used else (
            "Hermes 웹 도구를 호출했지만 성공한 도구 응답을 확인하지 못했습니다."
            if attempts else
            "Hermes의 실제 웹 검색 호출 기록이 없습니다. 이 결과는 내부 시장 자료 기반입니다."
        ),
    }
