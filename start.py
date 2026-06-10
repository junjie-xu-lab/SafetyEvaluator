"""Cross-platform launcher for SafetyEvaluator.

This helper creates a local virtual environment, installs dependencies, and
starts the Streamlit app without requiring shell activation scripts.
"""

from __future__ import annotations

import os
import subprocess
import venv
from argparse import ArgumentParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"


def main() -> int:
    """Create the local environment and start SafetyEvaluator."""

    args = _parse_args()
    venv_python = _venv_python()
    if not venv_python.exists():
        print("Creating virtual environment...")
        venv.create(VENV_DIR, with_pip=True)

    print("Installing dependencies...")
    install_command = [str(venv_python), "-m", "pip", "install", "-r", str(PROJECT_ROOT / "requirements.txt")]
    if args.pip_index_url:
        install_command.extend(["-i", args.pip_index_url])
    if _run(install_command) != 0:
        _print_dependency_help(args.pip_index_url)
        return 1

    print("Starting SafetyEvaluator...")
    return _run([str(venv_python), "-m", "streamlit", "run", str(PROJECT_ROOT / "app.py")])


def _parse_args():
    """Parse launcher options."""

    parser = ArgumentParser(description="Start the SafetyEvaluator Streamlit app.")
    parser.add_argument(
        "--pip-index-url",
        help="Use a custom Python package index when the default PyPI connection is blocked or unstable.",
    )
    return parser.parse_args()


def _venv_python() -> Path:
    """Return the platform-specific virtual-environment Python path."""

    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _run(command: list[str]) -> int:
    """Run a command in the project root."""

    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    return completed.returncode


def _print_dependency_help(pip_index_url: str | None) -> None:
    """Print dependency installation troubleshooting guidance."""

    print()
    print("Could not install dependencies from requirements.txt.")
    print("SafetyEvaluator was not started because required packages are missing.")
    print()
    print("This is usually caused by a network, proxy, firewall, or SSL problem when connecting to PyPI.")
    print("Try one of these fixes, then run the launcher again:")
    print()
    if os.name == "nt":
        print("1. Use a Python package mirror:")
        print("   python start.py --pip-index-url https://pypi.tuna.tsinghua.edu.cn/simple")
        print()
        print("2. Or install dependencies manually with the mirror:")
        print("   .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
    else:
        print("1. Use a Python package mirror:")
        print("   python start.py --pip-index-url https://pypi.tuna.tsinghua.edu.cn/simple")
        print()
        print("2. Or install dependencies manually with the mirror:")
        print("   .venv/bin/python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
    print()
    print("If the mirror also fails, check the network connection, proxy settings, and system time.")
    if pip_index_url:
        print(f"The failed package index was: {pip_index_url}")


if __name__ == "__main__":
    raise SystemExit(main())
