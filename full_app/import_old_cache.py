from __future__ import annotations
import os, shutil
from pathlib import Path

root = Path(os.getenv('YRA_DATA_DIR') or (Path.home() / 'Desktop' / 'youtube_consultant_data'))
dst = root / 'cache'
dst.mkdir(parents=True, exist_ok=True)
raw = input('Old cache folder path (the folder containing transcripts/comments/llm): ').strip().strip('"')
src = Path(raw).expanduser()
if not src.exists():
    raise SystemExit(f'Not found: {src}')
if (src / 'cache').exists() and not (src / 'transcripts').exists():
    src = src / 'cache'
print(f'Copy: {src} -> {dst}')
for name in ['transcripts','comments','llm']:
    s = src / name
    d = dst / name
    if s.exists():
        d.mkdir(parents=True, exist_ok=True)
        for f in s.glob('*.json'):
            target = d / f.name
            if not target.exists():
                shutil.copy2(f, target)
emb = src / 'embeddings.pkl'
if emb.exists() and not (dst / 'embeddings.pkl').exists():
    shutil.copy2(emb, dst / 'embeddings.pkl')
print('Done. External data folder:', root)
