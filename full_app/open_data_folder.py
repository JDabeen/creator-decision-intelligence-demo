from __future__ import annotations

import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

raw = os.getenv("YRA_DATA_DIR")
if raw:
    data_root = Path(raw).expanduser()
else:
    desktop = Path.home() / "Desktop"
    data_root = (desktop / "youtube_consultant_data") if desktop.exists() else (ROOT / "data")
manual = data_root / "manual"
manual.mkdir(parents=True, exist_ok=True)

try:
    os.startfile(str(manual))  # type: ignore[attr-defined]
except Exception:
    try:
        subprocess.run(["explorer", str(manual)], check=False)
    except Exception:
        print(manual)
