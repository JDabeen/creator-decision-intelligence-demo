"""Offline backup: preserve the Desktop strategy journal independently of app ZIP."""
from __future__ import annotations
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
import os
from strategy_hub import desktop_root


def run():
    folder = desktop_root()
    dest = folder / 'backups'
    dest.mkdir(parents=True, exist_ok=True)
    name = dest / ('YT_Strategy_Backup_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.zip')
    with ZipFile(name,'w',compression=ZIP_DEFLATED) as z:
        for f in folder.rglob('*'):
            if f.is_file() and not f.is_relative_to(dest) and f.suffix.lower() in ('.json','.txt','.csv','.md'):
                z.write(f, 'YT_Channel_Strategy/' + str(f.relative_to(folder)))
        data_dir = Path(os.getenv('YRA_DATA_DIR') or (folder.parent / 'youtube_consultant_data'))
        if data_dir.is_dir():
            for f in data_dir.rglob('*'):
                if not f.is_file() or f.suffix.lower() != '.json':
                    continue
                rel = f.relative_to(data_dir)
                # Preserve decisions, research evidence and knowledge, not huge API caches.
                if (rel.parts and rel.parts[0] == 'topic_experiments') or rel.name in ('content_memory.json','content_pattern_memory.json'):
                    z.write(f, 'youtube_consultant_data/' + str(rel))
    print('백업 완료:', name)
    print('주의: 개인 전략/연구 기록과 대본 발췌가 포함될 수 있습니다. GitHub에 올리지 마세요.')
    return name

if __name__ == '__main__': run()
