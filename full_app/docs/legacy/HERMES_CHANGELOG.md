# Hermes Docker bridge — changes on top of CURRENT_COMPLETE

## Changes (minimal integration)

- NEW: `0_START_WITH_HERMES.bat` — optional one-click Docker Hermes + Streamlit launch.
- NEW: `6_STOP_HERMES.bat` — stops only Hermes Docker container.
- NEW: `hermes_integration/` — authenticated localhost bridge, Docker Compose, startup, read-only config, tests, docs.
- EDITED: `critic_agent.py` — when explicitly selected, sends the **same** Draft A/Research/rubric to Hermes, then maps the result back to existing CriticAgentResult. Old OpenAI Critic path unchanged.
- EDITED: `pipeline.py` — passes critic backend choice to agent.
- EDITED: `app.py` — one radio control to select Hermes or existing OpenAI Critic before Draft B.

## Left unchanged

- `0_START_HERE.bat`, `1_SETUP_ONCE.bat`, `2_RUN_APP.bat`, `3_RUN_PUBLIC_DEMO.bat`
- Existing YouTube data collection, RAG, Transcript Coverage Gate, Research, Draft A, Draft B writing and A/B comparing, user feedback.
- All cache/storage modules and persistent data defaults.

## Limitations

This environment cannot execute the user's Windows Docker Desktop, Hermes official container, or their paid OpenAI credentials. All verification is offline/static/mock, not live end-to-end. External web search requires separately configured Hermes web-search provider.

## Hermes Docker image hotfix (2026-10-11)
- Pinned `main` digest c56a1bd1... after user-reported `latest` root passwd failure and `main` boot success.
- Restrict `api_server` toolsets explicitly to web (not only generic top-level setting).
- Print latest Hermes logs if authenticated readiness check fails.
- No changes to existing 0_START_HERE/1_SETUP_ONCE/2_RUN_APP, core research/cache, or Draft logic.
- This patch passed offline/static checks, not an actual Docker-to-OpenAI Critic run.

## 2026-10-11 · 시장 Transcript IP 차단 복구
- 전체 시장 Transcript Coverage 기준(>=2건, >=35%) 유지
- 기존 성공 캐시 우선 사용. YouTube 자막 IP 차단/비활성 시 Supadata native captions 예비 API (사용자 Opt-in)
- 외부 API 키는 개인 data/cache 상위 디렉터리에 저장. 내 채널 수집에는 예비 API를 사용하지 않음
- '자막 수집 복구' 화면: API 키 등록 후 재조사 또는 타사 영상 자막 원문 수동 입력
- 외부 ASR/AI 재전사 호출 금지 (mode=native 명시)
