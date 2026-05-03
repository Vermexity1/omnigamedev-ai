from __future__ import annotations

import sys
from pathlib import Path

from generator.templates import cpp_template
from language_adapters.base import ExecutionCommand
from planner.schemas import ProjectPlan


class CppAdapter:
    language = "C++"
    engine_names = ("Basic C++ Engine", "Unreal")

    def supports(self, plan: ProjectPlan) -> bool:
        return plan.language.lower() in {"c++", "cpp"} or plan.engine in self.engine_names

    def generate_project_files(self, plan: ProjectPlan) -> dict[str, str]:
        return cpp_template(plan)

    def smoke_commands(self, project_path: Path, install_dependencies: bool = False) -> list[ExecutionCommand]:
        return [
            ExecutionCommand("C++ compile/run smoke", [sys.executable, "tools/smoke.py"], project_path, timeout=60),
        ]
