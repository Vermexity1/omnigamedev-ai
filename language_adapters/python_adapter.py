from __future__ import annotations

import sys
from pathlib import Path

from generator.templates import pygame_template
from language_adapters.base import ExecutionCommand
from planner.schemas import ProjectPlan


class PythonAdapter:
    language = "Python"
    engine_names = ("Pygame", "Panda3D")

    def supports(self, plan: ProjectPlan) -> bool:
        return plan.language.lower() == "python" or plan.engine in self.engine_names

    def generate_project_files(self, plan: ProjectPlan) -> dict[str, str]:
        return pygame_template(plan)

    def smoke_commands(self, project_path: Path, install_dependencies: bool = False) -> list[ExecutionCommand]:
        commands: list[ExecutionCommand] = []
        if install_dependencies:
            commands.append(ExecutionCommand("Install Python dependencies", [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], project_path, timeout=180))
        commands.append(ExecutionCommand("Python compile check", [sys.executable, "-m", "py_compile", "main.py"], project_path, timeout=20))
        commands.append(ExecutionCommand("Pygame smoke test", [sys.executable, "main.py", "--smoke"], project_path, timeout=20))
        return commands
