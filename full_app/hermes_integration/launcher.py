"""Windows/Docker bootstrap for isolated Hermes. Python stdlib only.

Original app startup scripts remain unchanged. Only starts Hermes on explicit
0_START_WITH_HERMES.bat use. No unattended Docker Desktop installation.
"""
from __future__ import annotations

import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_DIR = HERE.parent
COMPOSE = HERE / "docker-compose.yml"
HERMES_DIR = Path.home() / "youtube_consultant_hermes_data"
SECRET_FILE = Path.home() / ".youtube_consultant_hermes_gateway_key"


def read_app_env() -> dict[str, str]:
    result = {}
    file = APP_DIR / ".env"
    if not file.is_file():
        raise RuntimeError("기존 앱 .env가 없습니다. 0_START_HERE.bat로 먼저 설정하세요.")
    for line in file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", key):
            result[key] = val
    return result


def gateway_secret() -> str:
    if SECRET_FILE.is_file():
        value = SECRET_FILE.read_text(encoding="utf-8").strip()
        if len(value) >= 32:
            return value
    value = secrets.token_hex(32)
    SECRET_FILE.write_text(value, encoding="utf-8")
    try:
        SECRET_FILE.chmod(0o600)
    except OSError:
        pass
    return value


def write_hermes_config(model: str, web_backend: str = "auto", browser_enabled: bool = True) -> bool:
    HERMES_DIR.mkdir(parents=True, exist_ok=True)
    if not re.fullmatch(r"[A-Za-z0-9._:/-]+", model):
        raise RuntimeError("Hermes 모델 이름에 허용되지 않은 문자가 있습니다.")
    if web_backend not in {"auto", "ddgs", "firecrawl", "tavily", "exa", "brave-free", "searxng"}:
        raise RuntimeError("지원하지 않는 Hermes 웹 검색 제공자입니다.")
    web_config = (f'web:\n  backend: "{web_backend}"\n' if web_backend != "auto" else "")
    # Browser runs INSIDE this dedicated container (not the Windows browser).
    # Enabling the whole browser toolset includes navigation AND clicks/typing;
    # it is not an absolute read-only security boundary. No host browser profile
    # or personal directories are mounted into the container.
    # Hermes also exposes five browser_vault_* tools with browser. Their names
    # are accepted by the gateway API audit (not a per-tool permission gate).
    # Do not give Hermes account credentials or mount personal browser profiles.
    enabled_api_toolsets = "[web, browser]" if browser_enabled else "[web]"
    browser_disable_line = "" if browser_enabled else "    - browser\n"
    # This config is controlled by the bootstrap, not by Hermes or other chats.
    # It is intentionally regenerated: a stray permissive setting must not persist.
    config = f'''# Dedicated internet research critic profile; managed by launcher.py
model:
  default: {model}
  provider: openai-api
{web_config}# Explicit API-server allowlist: its default normally enables terminal and files.
# The top-level `toolsets` key alone does not restrict API-server tools.
platform_toolsets:
  api_server: {enabled_api_toolsets}
agent:
  disabled_toolsets:
    - terminal
    - file
    - code_execution
    - skills
    - memory
    - cronjob
    - delegation
{browser_disable_line}    - computer_use
    - desktop_ui
    - project
    - catalog
    - homeassistant
    - todo
    - tts
    - image_gen
    - video_gen
    - session_search
    - discord
    - discord_admin
    - kanban
    - clarify
tool_loop_guardrails:
  warnings_enabled: true
  hard_stop_enabled: true
  hard_stop_after:
    exact_failure: 4
    idempotent_no_progress: 4
  loop_caps:
    max_web_searches: 5
    max_subagents: 1
'''
    dest = HERMES_DIR / "config.yaml"
    changed = not dest.is_file() or dest.read_text(encoding="utf-8") != config
    if changed:
        dest.write_text(config, encoding="utf-8")
    return changed


def docker(*args: str, env: dict) -> subprocess.CompletedProcess:
    cmd = ["docker", "compose", "-f", str(COMPOSE), *args]
    return subprocess.run(cmd, env=env, cwd=str(APP_DIR), text=True, check=False)


def main(command: str) -> int:
    if command not in {"start", "stop", "status"}:
        print("Usage: launcher.py start|stop|status")
        return 2
    if command == "stop":
        if not shutil_which("docker"):
            print("Docker가 없습니다.")
            return 1
        # stop must work without a .env (env defaults are irrelevant to stopping)
        env = dict(os.environ, HERMES_DATA_DIR=str(HERMES_DIR), HERMES_GATEWAY_KEY="stopping", OPENAI_API_KEY="stopping")
        result = docker("down", env=env)
        if result.returncode == 0:
            print("Hermes만 종료했습니다. 기존 YouTube 앱/캐시는 그대로입니다.")
        return result.returncode

    try:
        app_env = read_app_env()
        api_key = (app_env.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError(".env에 OPENAI_API_KEY를 넣어주세요.")
        if not shutil_which("docker"):
            raise RuntimeError("Docker Desktop이 설치되지 않았습니다. https://www.docker.com/products/docker-desktop/ 에서 먼저 설치하세요.")
        info = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=20)
        if info.returncode:
            # Docker Desktop is installed but closed: try starting it once.
            # On a first-time WSL2/terms/admin prompt, the user still must approve.
            candidates = [
                Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Docker" / "Docker" / "Docker Desktop.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop" / "Docker Desktop.exe",
            ]
            docker_exe = next((c for c in candidates if c.is_file()), None)
            if not docker_exe:
                raise RuntimeError("Docker Desktop 엔진이 꺼져 있습니다. Docker Desktop을 직접 실행한 뒤 재시도하세요.")
            print("[Hermes] Docker Desktop 자동 시작 중 (처음 실행이면 이용약관/WSL2 확인 필요)...")
            subprocess.Popen([str(docker_exe)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for i in range(45):
                time.sleep(3)
                info = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"],
                                      capture_output=True, text=True, timeout=12)
                if info.returncode == 0:
                    break
            if info.returncode:
                raise RuntimeError("Docker Desktop 준비가 끝나지 않았습니다. Docker Desktop 화면의 초기 설정을 완료하고 다시 실행하세요.")
        model = (app_env.get("YRA_HERMES_MODEL") or "gpt-4.1").strip()
        web_backend = (app_env.get("YRA_HERMES_WEB_BACKEND") or "auto").strip().lower()
        browser_enabled = (app_env.get("YRA_HERMES_BROWSER") or "1").strip().lower() not in {"0", "false", "off", "no"}
        config_changed = write_hermes_config(model, web_backend, browser_enabled=browser_enabled)
        print("[Hermes] Docker 내부 브라우저: " + ("허용" if browser_enabled else "차단"), flush=True)
        env = dict(os.environ, **app_env)
        env.update({"OPENAI_API_KEY": api_key,
                    "HERMES_DATA_DIR": str(HERMES_DIR),
                    "HERMES_GATEWAY_KEY": gateway_secret()})
        print("[Hermes] Docker 격리 컨테이너 시작 (처음에는 이미지 다운로드로 시간이 걸릴 수 있음)...")
        # Docker Compose does not recreate a running container when only the
        # bind-mounted Hermes config.yaml changes. Restart ONLY in that case.
        up_args = ["up", "-d", "--remove-orphans"]
        if config_changed:
            up_args.append("--force-recreate")
            print("[Hermes] 설정이 변경되어 기존 데이터는 유지한 채 컨테이너만 갱신합니다.", flush=True)
        result = docker(*up_args, env=env)
        if result.returncode:
            raise RuntimeError("Docker Compose 시작 실패. 위 출력과 Docker Desktop 상태를 확인하세요.")
        if command == "status":
            return docker("ps", env=env).returncode
        # Do not use unauthenticated /health alone as success proof.
        # Earlier builds swallowed ALL readiness errors and falsely labeled even
        # 401, 404 and unsafe toolsets as "starting" for 90 seconds.
        from hermes_integration.adapter import check_ready
        last_issue = None
        repeated_hard_error = 0
        for i in range(45):
            try:
                name = check_ready()
                print(f"[Hermes] 인증된 API 연결 성공: {name} / localhost:8642", flush=True)
                print("[Hermes] 앱에서 전달한 연구 텍스트만 사용. Windows 개인 폴더는 Docker에 연결하지 않았습니다.", flush=True)
                return 0
            except Exception as exc:
                # No keys are printed; only the exception class and a bounded
                # message from our localhost connector are displayed.
                from research_resilience import safe_error
                summary = safe_error(exc)
                if summary != last_issue:
                    print(f"[Hermes][API 점검] {summary}", flush=True)
                    repeated_hard_error = 0
                last_issue = summary
                # Auth mismatch, route mismatch, and any unsafe tool permission
                # will not become safe after a long wait. Fail clearly.
                hard = any(w in summary for w in (
                    "HTTP 401", "HTTP 403", "HTTP 404", "격리 정책 위반",
                    "응답 형식", "도구 항목 형식", "상세 목록",
                ))
                repeated_hard_error = repeated_hard_error + 1 if hard else 0
                if repeated_hard_error >= 3:
                    print("[Hermes] 계속 재시도해도 해결되지 않는 API/권한 문제입니다.", flush=True)
                    break
                if i % 10 == 0:
                    print("[Hermes] API 준비 대기 중 (컨테이너 Running만으로는 연결 성공이 아닙니다)...", flush=True)
                time.sleep(2)
        print("[Hermes] API 연결에 실패했습니다. 위 [API 점검]의 구체적 원인이 우선입니다.")
        print("[Hermes] 추가 로그 (최근 35줄, API 토큰 공개하지 마세요):")
        docker("logs", "--tail", "35", "gateway", env=env)
        raise RuntimeError(
            "Hermes 인증/API/도구 안전 검사가 통과하지 못했습니다. "
            f"마지막 점검: {last_issue or '응답 없음'}. 기존 앱은 변경하지 않았습니다."
        )
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as err:
        print("[Hermes ERROR] " + str(err))
        return 1


def shutil_which(name: str) -> bool:
    from shutil import which
    return which(name) is not None


if __name__ == "__main__":
    sys.path.insert(0, str(APP_DIR))
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "start"))
