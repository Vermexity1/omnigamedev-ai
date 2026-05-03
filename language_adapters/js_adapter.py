from __future__ import annotations

import sys
from pathlib import Path

from generator.templates import three_js_template
from language_adapters.base import ExecutionCommand
from planner.schemas import ProjectPlan


class JavaScriptAdapter:
    language = "JavaScript"
    engine_names = ("Three.js", "Babylon.js")

    def supports(self, plan: ProjectPlan) -> bool:
        return plan.language.lower() in {"javascript", "typescript"} or plan.engine in self.engine_names

    def generate_project_files(self, plan: ProjectPlan) -> dict[str, str]:
        return three_js_template(plan)

    def smoke_commands(self, project_path: Path, install_dependencies: bool = False) -> list[ExecutionCommand]:
        commands: list[ExecutionCommand] = []
        if install_dependencies:
            commands.append(ExecutionCommand("Install npm dependencies", ["npm", "install"], project_path, timeout=180))
        commands.append(ExecutionCommand("JavaScript syntax check", ["node", "--check", "src/main.js"], project_path, timeout=30))
        commands.append(
            ExecutionCommand(
                "Project metadata check",
                [sys.executable, "-c", "from pathlib import Path; assert Path('package.json').exists(); assert Path('index.html').exists(); print('metadata ok')"],
                project_path,
                timeout=10,
            )
        )
        return commands
