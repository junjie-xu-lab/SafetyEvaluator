"""Cross-platform launcher for SafetyEvaluator.

This helper creates a local virtual environment, installs dependencies, and
starts the Streamlit app without requiring shell activation scripts.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"


def main() -> int:
    """Create the local environment and start SafetyEvaluator."""

    venv_python = _venv_python()
    if not venv_python.exists():
        print("Creating virtual environment...")
        venv.create(VENV_DIR, with_pip=True)

    print("Installing dependencies...")
    _run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    _run([str(venv_python), "-m", "pip", "install", "-r", str(PROJECT_ROOT / "requirements.txt")])

    print("Starting SafetyEvaluator...")
    return _run([str(venv_python), "-m", "streamlit", "run", str(PROJECT_ROOT / "app.py")])


def _venv_python() -> Path:
    """Return the platform-specific virtual-environment Python path."""

    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _run(command: list[str]) -> int:
    """Run a command in the project root."""

    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
