# YouTube Content Consultant — Docker Hermes Critic 통합

## 한 번에 실행

**이미 Windows에서 기존 앱을 돌려봤다면**, 앱을 종료한 뒤 이 폴더 최상위의 **`0_START_WITH_HERMES.bat`** 파일을 더블클릭하세요.

최초 준비 사항: **Docker Desktop (WSL2 엔진)** 이 설치·실행되어 있어야 하고, 기존 `.env`에 `OPENAI_API_KEY`와 `YOUTUBE_API_KEY`가 있어야 합니다. Docker Desktop은 별도로 설치해야 하며, 관리자 권한/재부팅/사용자 약관 승인을 이 앱이 대신 처리하지 않습니다.

이 실행 파일 하나가 다음을 처리합니다.

1. 기존 Python 가상환경 설치 여부 확인(없으면 기존 설치 스크립트 사용)
2. Docker 실행 상태 확인(설치돼 있으나 꺼져 있으면 시작 시도)과 기존 `.env`의 OpenAI 키 확인
3. 별도 격리 데이터 폴더/랜덤 Hermes 인증 키 생성
4. 확인된 Hermes `main` 이미지를 고정된 SHA256 digest로 실행 (2026-10-11 사용자 환경에서 서비스 시작 확인, 개발판이므로 기능 안정성은 별도 검증 필요)
5. 인증 및 허용된 도구 확인
6. 기존 Streamlit 앱 실행(기본 Critic 엔진: Hermes)

Draft A까지는 기존과 **동일하게 작동**하고, Draft B 화면에서 `Hermes Agent (Docker)` 또는 `기존 OpenAI Critic` 중 선택할 수 있습니다. Hermes가 실패해도 자동으로 기존 엔진 결과인 척하지 않습니다.

## 구조

```text
Windows Streamlit / Research / YouTube Transcript / RAG / Draft A
    | 텍스트 프롬프트만 HTTP로 전달 (127.0.0.1:8642, Bearer 인증)
    v
Docker Hermes Agent (read-only web toolset / model provider)
    | Critic Report (근거/확인 사항/검토 의견)
    v
Windows 기존 Draft B 작성기 → A/B 비교 → Final
```

- 기존 `0_START_HERE.bat`, `1_SETUP_ONCE.bat`, `2_RUN_APP.bat`은 바꾸지 않았습니다.
- 기존 데이터/Transcript 캐시 폴더는 바꾸지 않았습니다.
- Docker에는 **개인 Windows 폴더나 앱 프로젝트를 마운트하지 않습니다**. Hermes 전용 폴더만 마운트합니다.
- Docker 볼륨 디렉터리: `%USERPROFILE%\youtube_consultant_hermes_data` (원본 앱의 데이터와 분리됨)
- Hermes 인증 토큰: `%USERPROFILE%\.youtube_consultant_hermes_gateway_key` (컨테이너 외부)
- API는 Windows 자신에게만 공개 (`127.0.0.1:8642`). 원격 접근·브라우저 CORS·대시보드 없음.
- Hermes 도구는 `platform_toolsets.api_server: [web]` 설정으로 `web_search` / `web_extract`만 허용하도록 지정(도구 사용 가능 여부는 외부 검색 서비스 설정에 의존). 실행 시 `/v1/toolsets`로 실제 허용 도구 검사. 그 검사에서 미허용 도구가 나오면 앱 실행 전에 중단합니다.
- Docker가 탈취되거나 모델이 잘못된 판단을 할 가능성을 완전히 제거할 수는 없습니다. Hermes의 OpenAI API 키는 컨테이너 환경변수로 전달되므로 Docker Desktop 관리자에게 노출될 수 있습니다.

## 웹 검색 사용 (선택)

**OpenAI API 키만 있으면 Hermes의 LLM 검토는 가능하지만, Hermes 전용 `web_search`는 별도 검색 서비스 설정을 요구할 수 있습니다.** 공식 Hermes 문서의 검색 제공업체(예: Tavily 또는 Exa)를 이용할 경우 기존 `.env`에 아래 한 줄을 추가할 수 있습니다.

```env
TAVILY_API_KEY=사용자_키
# 또는 EXA_API_KEY=사용자_키
# 선택: Hermes 내부 LLM (기본 gpt-4.1)
YRA_HERMES_MODEL=gpt-4.1
```

키를 추가한 후 `0_START_WITH_HERMES.bat`을 다시 실행하면 컨테이너 환경변수가 갱신됩니다. 추가 서비스를 사용하면 해당 업체의 요금이 발생할 수 있습니다. **웹 검증 자료가 확인되지 않으면 UI에 경고**를 띄웁니다. 검색용 키가 없다고 해서 비평 결과가 완전히 무가치한 것은 아니지만, 추가 웹 조사를 했다고 주장하면 안 됩니다.

## 종료/되돌리기

- Hermes만 중지: `6_STOP_HERMES.bat`
- 원래 앱만 실행: `0_START_HERE.bat`
- Docker Hermes 데이터는 앱 폴더 밖에 있으므로, 앱 업데이트 시 캐시와 별도로 유지됩니다.
- **예전 파일 삭제 / 데이터 폴더 삭제 / Docker 볼륨 정리 명령은 실행하지 않습니다.**

## 실행 검증 수준과 제한

- Python 정적 검사, 원본 파일 보존 확인, HTTP 모의 API 연결 테스트로 패키지를 검증했습니다.
- **이 패키지는 제작 환경에서 실제 Windows Docker Desktop + Hermes 컨테이너 + OpenAI 계정으로 종단 간 검증하지 못했습니다.**
- 사용자의 첫 실행에서 Hermes 공식 이미지/설정에 변경이 생겼다면 오류 메시지와 Docker 로그를 보고 호환 조정을 해야 합니다. 실제 성공이라고 확정하려면 Draft B의 `Critic model · Hermes Agent / ...` 표기가 보이고 Critic Report가 생성되어야 합니다.
- Hermes 비평은 최대 240초 기다리도록 되어 있습니다. 장시간 복잡한 작업은 시간 초과될 수 있습니다.

## 2026-10-11 이미지 실행 오류 수정

사용자 PC에서 `nousresearch/hermes-agent:latest`를 실행할 때 `unable to find user root` 오류가 발생했고, `nousresearch/hermes-agent:main` 이미지는 s6 초기화 및 `main-hermes` 서비스 시작까지 확인되었습니다. `hermes version`은 유효한 CLI 명령이 아니며, 그 오류만으로 실행 실패로 판단하지 않습니다.

이번 배포본은 사용자 측에서 서비스 초기화가 확인된 **main digest를 고정**했으므로 이미지 변경으로 같은 오류가 재발할 위험을 줄입니다. `main`은 개발판으로, OpenAI API 연결과 Draft B 실제 완성까지 검증한 상태는 아닙니다. Docker가 정상이어도 인터넷/모델 키/도구 설정 때문에 연결 실패가 날 수 있습니다.

새 폴더에 풀고 기존 `.env`를 넣은 뒤 `0_START_WITH_HERMES.bat`을 실행하세요. **기존 폴더와 캐시는 삭제하지 마세요.** 예전 Docker Hermes 컨테이너는 같은 Compose 프로젝트명으로 관리하므로 실행 시 새 이미지로 갱신될 수 있습니다. 문제가 나면 검은 창의 마지막 오류 메시지를 보내 주세요.
