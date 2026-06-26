"""One-click launcher for the event-scraper frontend.

    python run.py

Starts the Streamlit app (New_york.py). Streamlit opens the browser itself.
Override the port with the UI_PORT environment variable.
"""

from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
UI_PORT = os.environ.get("UI_PORT", "8501")
APP = os.path.join(ROOT, "New_york.py")


def main() -> int:
    cmd = [
        sys.executable, "-m", "streamlit", "run", APP,
        "--server.port", str(UI_PORT),
    ]
    print(f"Starting Event Scraper UI -> http://localhost:{UI_PORT}")
    try:
        return subprocess.call(cmd, cwd=ROOT)
    except KeyboardInterrupt:
        print("\nShutting down.")
        return 0
    except FileNotFoundError:
        print("Streamlit is not installed. Run:  pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
