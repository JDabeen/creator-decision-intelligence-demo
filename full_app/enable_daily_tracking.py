"""Opt-in Windows Task Scheduler installer. Does not create tasks on import."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TASK = 'YT_Channel_Strategy_Public_Daily'
ROOT = Path(__file__).resolve().parent


def task_command() -> str:
    # If app moves to a new folder, re-run installer to update task command.
    return f'"{sys.executable}" "{ROOT / "daily_snapshot.py"}"'


def main():
    if os.name != 'nt':
        raise RuntimeError('Windows Task Scheduler required')
    if not (ROOT / 'daily_snapshot.py').is_file():
        raise RuntimeError('daily_snapshot.py not found')
    action = 'delete' if '--disable' in sys.argv else 'create'
    if action == 'create':
        args=['schtasks', '/Create', '/F', '/SC', 'DAILY', '/ST','09:00',
              '/TN',TASK,'/TR',task_command()]
    else:
        args=['schtasks','/Delete','/F','/TN',TASK]
    result=subprocess.run(args,capture_output=True,text=True,errors='replace',check=False)
    if result.returncode:
        print('Windows Task Scheduler failed:',result.stderr[-300:] or result.stdout[-300:])
        raise SystemExit(1)
    print('Daily tracking schedule', 'disabled' if action=='delete' else 'registered (09:00 local, PC must be awake)')
    print('Google API public metrics only. No LLM/Hermes. Scheduled task is optional.')


if __name__=='__main__':
    main()
