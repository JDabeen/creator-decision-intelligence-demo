"""Optional standalone public metric sync; no LLM, Hermes, Studio or search API."""
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    key = os.getenv('YOUTUBE_API_KEY', '').strip()
    if not key:
        raise RuntimeError('YOUTUBE_API_KEY missing; refusing sync')
    from googleapiclient.discovery import build
    from config import Settings
    from strategy_hub import StrategyStore
    from yra_tools.youtube_tools import YouTubeResearchTools
    tools = YouTubeResearchTools(build('youtube', 'v3', developerKey=key), Settings())
    store = StrategyStore()
    result = store.sync_public(tools, Settings().my_channel_handle, force=False, hours=20)
    line = f"{datetime.now().isoformat(timespec='seconds')} {result['status']} {str(result.get('error') or '')[:240]}"
    path = store.root / 'daily_sync_status.txt'
    path.write_text(line + '\n', encoding='utf-8')
    if result['status'] == 'error':
        raise RuntimeError('Daily public sync failed; last snapshot kept')
    print('Daily YouTube public metrics:', result['status'])


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        # Never print a credential or a full URL that might contain one.
        print('Daily snapshot failed:', type(ex).__name__)
        raise SystemExit(1)
