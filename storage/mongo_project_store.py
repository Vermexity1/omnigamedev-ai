from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SKIPPED_NAMES = {"__pycache__", "node_modules", "dist", "build", ".venv"}


@dataclass
class MongoProjectStore:
    """MongoDB-backed project snapshot store.

    Render Free services have an ephemeral filesystem, so generated project files
    need to be persisted outside the container and restored when the service wakes.
    """

    uri: str
    db_name: str = "omnigamedev"

    def __post_init__(self) -> None:
        try:
            from pymongo import MongoClient  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on optional package state
            raise RuntimeError("pymongo is required for MongoDB persistence.") from exc

        self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
        self.client.admin.command("ping")
        db = self.client[self.db_name]
        self.projects = db["projects"]
        self.files = db["project_files"]
        self.projects.create_index("updated_at")
        self.files.create_index("project")
        self.files.create_index([("project", 1), ("path", 1)], unique=True)

    @classmethod
    def from_env(cls) -> "MongoProjectStore | None":
        uri = os.getenv("MONGODB_URI", "").strip()
        if not uri:
            return None
        return cls(uri=uri, db_name=os.getenv("MONGODB_DB", "omnigamedev").strip() or "omnigamedev")

    def save_project(self, project_path: str | Path) -> None:
        root = Path(project_path).resolve()
        if not root.exists() or not root.is_dir():
            return

        now = time.time()
        plan = self._read_json(root / ".omnigamedev" / "plan.json")
        manifest = self._read_json(root / ".omnigamedev" / "manifest.json")
        self.projects.replace_one(
            {"_id": root.name},
            {
                "_id": root.name,
                "name": root.name,
                "plan": plan,
                "manifest": manifest,
                "updated_at": now,
            },
            upsert=True,
        )

        self.files.delete_many({"project": root.name})
        documents = [self._file_document(root, path, now) for path in self._iter_files(root)]
        if documents:
            self.files.insert_many(documents, ordered=False)

    def restore_projects(self, projects_root: str | Path) -> int:
        root = Path(projects_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        restored = 0
        for project in self.projects.find({}, {"_id": 1}):
            name = str(project["_id"])
            if self.restore_project(name, root):
                restored += 1
        return restored

    def restore_project(self, project_name: str, projects_root: str | Path) -> bool:
        project = self.projects.find_one({"_id": project_name})
        if not project:
            return False

        root = (Path(projects_root).resolve() / project_name).resolve()
        root.mkdir(parents=True, exist_ok=True)
        for document in self.files.find({"project": project_name}):
            target = (root / str(document["path"])).resolve()
            if root not in target.parents and target != root:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if document.get("binary"):
                target.write_bytes(base64.b64decode(str(document.get("content", ""))))
            else:
                target.write_text(str(document.get("content", "")), encoding="utf-8")
        return True

    def project_names(self) -> list[str]:
        return [str(item["_id"]) for item in self.projects.find({}, {"_id": 1}).sort("updated_at", -1)]

    def _iter_files(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if any(part in SKIPPED_NAMES for part in relative.parts):
                continue
            files.append(path)
        return files

    def _file_document(self, root: Path, path: Path, updated_at: float) -> dict[str, Any]:
        relative = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
            return {
                "_id": f"{root.name}:{relative}",
                "project": root.name,
                "path": relative,
                "content": text,
                "binary": False,
                "updated_at": updated_at,
            }
        except UnicodeDecodeError:
            return {
                "_id": f"{root.name}:{relative}",
                "project": root.name,
                "path": relative,
                "content": base64.b64encode(raw).decode("ascii"),
                "binary": True,
                "updated_at": updated_at,
            }

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
