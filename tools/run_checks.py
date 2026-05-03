from __future__ import annotations

import subprocess
import sys
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "ide" / "frontend"


def run(label: str, args: list[str], cwd: Path = ROOT) -> None:
    print(f"\n== {label} ==")
    completed = subprocess.run(args, cwd=cwd)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    python_targets = [
        "agent",
        "planner",
        "generator",
        "executor",
        "memory",
        "language_adapters",
        "plugins",
        "tests",
        "main.py",
        "ide/backend/app.py",
    ]
    run("Python compile", [sys.executable, "-m", "compileall", *python_targets])
    run("Unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])

    if (FRONTEND / "node_modules").exists():
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if npm is None:
            print("\n== Frontend build ==\nSkipped because npm is not on PATH.")
        else:
            run("Frontend build", [npm, "run", "build"], FRONTEND)
    else:
        print("\n== Frontend build ==\nSkipped because ide/frontend/node_modules is missing.")


if __name__ == "__main__":
    main()
