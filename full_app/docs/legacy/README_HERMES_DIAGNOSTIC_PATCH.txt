Hermes API 연결 진단 패치 (기존 앱 및 데이터 보존)

기존 youtube_content_consultant_CURRENT 폴더에 이 패치 ZIP을 압축 해제하고, 같은 이름의 hermes_integration 파일 2개는 덮어쓰세요.
기존 0_START_HERE.bat / 0_START_WITH_HERMES.bat / .env / Docker 이미지 / RAG / Transcript 캐시는 변경하지 않습니다.

먼저 7_CHECK_HERMES.bat을 더블클릭하면 현재 Hermes API가 왜 준비되지 않았는지 5~10초 안에 검사할 수 있습니다.
검사에 성공하면 0_START_WITH_HERMES.bat을 다시 실행하세요.
실패 시 '구체적 원인' 한 줄만 복사해 주면 됩니다. 인증 키/환경변수/전체 비밀 파일을 보내지 마세요.

현재 문제: Hermes Gateway는 실행됐지만 기존 실행기는 내부 API 상태 검사 예외를 숨겨 90초 동안 준비 대기만 표시함.
이 패치는 예외 종류/HTTP 코드를 즉시 표시합니다. Hermes API 자체의 문제를 해결했다고 주장하지 않습니다.
