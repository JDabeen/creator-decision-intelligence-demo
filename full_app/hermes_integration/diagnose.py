"""Local, read-only Hermes diagnostics; does not print credentials."""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from hermes_integration import adapter


def main() -> int:
    print('Hermes API 진단 (개인 키는 출력하지 않음)', flush=True)
    print('대상: http://127.0.0.1:8642', flush=True)
    try:
        with urlopen(adapter.DEFAULT_URL + '/health', timeout=5) as r:
            print('HTTP 상태: ' + str(r.status), flush=True)
    except Exception as exc:
        print('HTTP 상태 확인 실패: ' + type(exc).__name__ + ': ' + str(exc)[:150], flush=True)
    try:
        name = adapter.check_ready()
        print('인증 + 도구 안전 검사: 성공', flush=True)
        print('API 모델: ' + name, flush=True)
        print('다음 단계: 0_START_WITH_HERMES.bat 실행', flush=True)
        return 0
    except Exception as exc:
        print('인증 + 도구 안전 검사: 실패', flush=True)
        print('구체적 원인: ' + type(exc).__name__ + ': ' + str(exc)[:350], flush=True)
        print('주의: 임의로 Hermes 도구 제한을 풀지 마세요.', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
