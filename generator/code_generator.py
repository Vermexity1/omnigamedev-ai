from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from generator.asset_generator import AssetGenerator
from generator.project_manager import ProjectManager
from language_adapters import CSharpAdapter, CppAdapter, JavaScriptAdapter, LanguageAdapter, PythonAdapter
from planner.schemas import ProjectPlan


@dataclass(slots=True)
class GenerationResult:
    project_path: str
    files: list[str]
    adapter: str
    plan: ProjectPlan

    def to_dict(self) -> dict:
        return {
            "project_path": self.project_path,
            "files": self.files,
            "adapter": self.adapter,
            "plan": self.plan.to_dict(),
        }


class CodeGenerator:
    def __init__(self, projects_root: str | Path, adapters: list[LanguageAdapter] | None = None) -> None:
        self.project_manager = ProjectManager(projects_root)
        self.asset_generator = AssetGenerator()
        self.adapters = adapters or [JavaScriptAdapter(), PythonAdapter(), CSharpAdapter(), CppAdapter()]

    def generate_project(self, plan: ProjectPlan) -> GenerationResult:
        adapter = self._adapter_for(plan)
        files = adapter.generate_project_files(plan)
        files.update(self.asset_generator.files_for_plan(plan))
        manifest = {
            "schema": "omnigamedev.project.v1",
            "plan": plan.to_dict(),
            "adapter": adapter.__class__.__name__,
            "generated_file_count": len(files),
        }
        written = self.project_manager.write_project(plan.project_name, files, manifest)
        return GenerationResult(
            project_path=str(written.path),
            files=written.files,
            adapter=adapter.__class__.__name__,
            plan=plan,
        )

    def _adapter_for(self, plan: ProjectPlan) -> LanguageAdapter:
        for adapter in self.adapters:
            if adapter.supports(plan):
                return adapter
        return JavaScriptAdapter()
