from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
compiler = shutil.which("g++") or shutil.which("clang++")
if compiler is None:
    print("No C++ compiler found; source files are present for engine import.")
    raise SystemExit(0)

binary = root / "omnigame-smoke.exe"
subprocess.run([compiler, "main.cpp", "-std=c++17", "-O2", "-o", str(binary)], cwd=root, check=True)
subprocess.run([str(binary), "--smoke"], cwd=root, check=True)
