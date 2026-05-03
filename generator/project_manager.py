from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class WrittenProject:
    path: Path
    files: list[str]


class ProjectManager:
    def __init__(self, projects_root: str | Path) -> None:
        self.projects_root = Path(projects_root).resolve()
        self.projects_root.mkdir(parents=True, exist_ok=True)

    def project_path(self, project_name: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in project_name).strip("-")
        safe = safe or "omnigame-project"
        return (self.projects_root / safe).resolve()

    def write_project(self, project_name: str, files: dict[str, str], manifest: dict) -> WrittenProject:
        project_path = self.project_path(project_name)
        project_path.mkdir(parents=True, exist_ok=True)
        files = dict(files)
        files[".omnigamedev/manifest.json"] = json.dumps(manifest, indent=2, ensure_ascii=True)
        files[".omnigamedev/plan.json"] = json.dumps(manifest.get("plan", {}), indent=2, ensure_ascii=True)

        written: list[str] = []
        for relative_path, content in files.items():
            target = (project_path / relative_path).resolve()
            if not self._is_inside(project_path, target):
                raise ValueError(f"Refusing to write outside project root: {relative_path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            written.append(relative_path.replace("\\", "/"))
        return WrittenProject(path=project_path, files=sorted(written))

    def list_files(self, project_path: str | Path) -> list[str]:
        root = Path(project_path).resolve()
        if not self._is_inside(self.projects_root, root):
            raise ValueError("Project path is outside projects root.")
        files: list[str] = []
        for item in root.rglob("*"):
            if item.is_file():
                files.append(item.relative_to(root).as_posix())
        return sorted(files)

    def _is_inside(self, root: Path, target: Path) -> bool:
        try:
            target.relative_to(root)
            return True
        except ValueError:
            return False
