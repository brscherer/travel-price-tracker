from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_dashboard() -> None:
    app_path = Path(__file__).parent / "app.py"
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=False)
    except FileNotFoundError:
        print("streamlit not installed. Run: pip install -e '.[dashboard]'")
        sys.exit(1)
