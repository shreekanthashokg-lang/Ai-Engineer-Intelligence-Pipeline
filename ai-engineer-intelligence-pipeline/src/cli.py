"""CLI entry point.

Usage:
  python -m src.cli demo            # runs the credential-free / low-network demo
  python -m src.cli export          # exports data/processed -> data/exports (6 tabs)
  python -m src.cli test            # runs the unit test suite
"""
from __future__ import annotations

import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "demo":
        subprocess.run([sys.executable, "scripts/generate_demo_data_report.py"], check=True)
    elif cmd == "export":
        subprocess.run([sys.executable, "scripts/export_google_sheets.py", "--dry-run"], check=True)
    elif cmd == "test":
        subprocess.run([sys.executable, "-m", "pytest", "tests/unit", "-v"], check=True)
    else:
        print(f"Unknown command: {cmd}\n\n{__doc__}")


if __name__ == "__main__":
    main()
