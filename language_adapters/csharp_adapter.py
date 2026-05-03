from __future__ import annotations

import sys
from pathlib import Path

from generator.templates import unity_template
from language_adapters.base import ExecutionCommand
from planner.schemas import ProjectPlan


class CSharpAdapter:
    language = "C#"
    engine_names = ("Unity",)

    def supports(self, plan: ProjectPlan) -> bool:
        return plan.language.lower() in {"c#", "csharp"} or plan.engine in self.engine_names

    def generate_project_files(self, plan: ProjectPlan) -> dict[str, str]:
        return unity_template(plan)

    def smoke_commands(self, project_path: Path, install_dependencies: bool = False) -> list[ExecutionCommand]:
        script = (
            "from pathlib import Path; "
            "required=['Assets/Scripts/OmniGameManager.cs','Assets/Scripts/PlayerController.cs','Assets/Scripts/EnemyAI.cs']; "
            "missing=[p for p in required if not Path(p).exists()]; "
            "assert not missing, 'missing Unity scripts: '+','.join(missing); "
            "print('unity script layout ok')"
        )
        return [ExecutionCommand("Unity script layout smoke", [sys.executable, "-c", script], project_path, timeout=20)]
