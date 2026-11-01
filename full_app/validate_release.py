"""Deterministic release health checks; never uses internet, Docker, or paid APIs."""
from __future__ import annotations
import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUITES = ('topic_tests', 'workflow_tests', 'strategy_tests', 'hermes_integration/tests', 'hermes_experiment/tests')


def validate() -> int:
    print('1/3 Python syntax scan ...', flush=True)
    paths = list(ROOT.glob('*.py')) + list((ROOT / 'hermes_integration').glob('*.py'))
    paths += list((ROOT / 'yra_tools').glob('*.py'))
    if not all(compileall.compile_file(str(f), quiet=1) for f in paths):
        return 1
    print('2/3 Offline unit & mock integration tests ...', flush=True)
    for suite in SUITES:
        proc = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', suite, '-q'],
                              cwd=ROOT, check=False)
        if proc.returncode:
            print('[FAIL]', suite, flush=True)
            return proc.returncode
    print('3/3 Check for accidentally packaged secrets ...', flush=True)
    for candidate in (ROOT / '.env', ROOT / 'youtube_consultant_data'):
        if candidate.exists():
            print('Caution: local private data present (not intended for public distribution):', candidate.name)
    print('[OK] Offline checks passed. Not a live Hermes / YouTube / Windows E2E proof.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(validate())
