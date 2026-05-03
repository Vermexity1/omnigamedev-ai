from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from planner.schemas import ProjectPlan


@dataclass(slots=True)
class ExecutionCommand:
    label: str
    args: list[str]
    cwd: Path
    timeout: int = 30
    env: dict[str, str] = field(default_factory=dict)


class LanguageAdapter(Protocol):
    language: str
    engine_names: tuple[str, ...]

    def supports(self, plan: ProjectPlan) -> bool:
        ...

    def generate_project_files(self, plan: ProjectPlan) -> dict[str, str]:
        ...

    def smoke_commands(self, project_path: Path, install_dependencies: bool = False) -> list[ExecutionCommand]:
        ...
