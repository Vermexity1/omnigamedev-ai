from __future__ import annotations

import io
import json
import mimetypes
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import OmniGameDevAgent  # noqa: E402
from executor import ExecutionEngine  # noqa: E402
from planner.presets import PRESETS  # noqa: E402
from planner import ProjectPlan  # noqa: E402
from plugins import PluginManager  # noqa: E402
from storage import MongoProjectStore  # noqa: E402


app = FastAPI(title="OmniGameDev AI IDE API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)


API_TOKEN = os.getenv("OMNIGAMEDEV_API_TOKEN", "").strip()


def browser_cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-OmniGameDev-Token,Authorization",
        "Access-Control-Allow-Private-Network": "true",
    }


@app.middleware("http")
async def access_token_guard(request: Request, call_next):
    path = request.url.path
    is_preview_asset = request.method == "GET" and path.startswith("/api/projects/") and "/preview" in path
    if request.method == "OPTIONS":
        return Response(status_code=204, headers=browser_cors_headers())
    if path == "/api/health" or is_preview_asset or not API_TOKEN:
        return await call_next(request)
    supplied = (request.headers.get("x-omnigamedev-token") or request.query_params.get("token") or "").strip()
    if supplied != API_TOKEN:
        return JSONResponse(
            status_code=401,
            content={"detail": "Backend access code required."},
            headers=browser_cors_headers(),
        )
    return await call_next(request)


@app.middleware("http")
async def private_network_access_headers(request, call_next):
    response = await call_next(request)
    for key, value in browser_cors_headers().items():
        response.headers[key] = value
    return response

agent = OmniGameDevAgent(ROOT)
executor = ExecutionEngine()
PROJECTS_ROOT = agent.projects_root
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
PROJECT_STORE_ERROR = ""
try:
    project_store = MongoProjectStore.from_env()
except Exception as exc:  # pragma: no cover - depends on deployed environment
    project_store = None
    PROJECT_STORE_ERROR = str(exc)


class PlanRequest(BaseModel):
    prompt: str = Field(min_length=1)


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    project_name: str | None = None
    run_after: bool = True
    install_dependencies: bool = False


class SaveFileRequest(BaseModel):
    path: str
    content: str


class OpenFolderRequest(BaseModel):
    folder_path: str = Field(min_length=1)


class AiActionRequest(BaseModel):
    mode: str = Field(pattern="^(review|improve|edit)$")
    prompt: str = ""
    path: str | None = None
    content: str | None = None


@app.on_event("startup")
def restore_persisted_projects() -> None:
    if project_store is not None:
        project_store.restore_projects(PROJECTS_ROOT)


def safe_project(project: str) -> Path:
    path = (PROJECTS_ROOT / project).resolve()
    if (not path.exists()) and project_store is not None:
        project_store.restore_project(project, PROJECTS_ROOT)
    if not is_inside(PROJECTS_ROOT.resolve(), path) or not path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    return path


def safe_file(project_path: Path, relative_path: str) -> Path:
    target = (project_path / relative_path).resolve()
    if not is_inside(project_path.resolve(), target):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return target


def is_inside(root: Path, target: Path) -> bool:
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def read_plan(project_path: Path) -> ProjectPlan:
    plan_path = project_path / ".omnigamedev" / "plan.json"
    if not plan_path.exists():
        return infer_plan_for_folder(project_path)
    return ProjectPlan.from_dict(json.loads(plan_path.read_text(encoding="utf-8")))


def build_tree(project_path: Path) -> list[dict[str, Any]]:
    hidden_names = {"__pycache__", "node_modules", "dist", "build", ".venv"}

    def node_for(path: Path) -> dict[str, Any]:
        if path.is_dir():
            return {
                "name": path.name,
                "path": path.relative_to(project_path).as_posix(),
                "type": "directory",
                "children": [
                    node_for(child)
                    for child in sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
                    if child.name not in hidden_names
                ],
            }
        return {
            "name": path.name,
            "path": path.relative_to(project_path).as_posix(),
            "type": "file",
        }

    visible = [
        item
        for item in sorted(project_path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        if item.name not in hidden_names
    ]
    return [node_for(item) for item in visible]


def persist_project(project_path: Path) -> None:
    if project_store is not None:
        project_store.save_project(project_path)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "root": str(ROOT),
        "projects_root": str(PROJECTS_ROOT),
        "memory_records": agent.memory.count(),
        "auth_required": bool(API_TOKEN),
        "project_store": "mongodb" if project_store is not None else "filesystem",
        "project_store_error": PROJECT_STORE_ERROR,
    }


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


@app.post("/api/plan")
def plan(request: PlanRequest) -> dict[str, Any]:
    return agent.plan(request.prompt).to_dict()


@app.post("/api/generate")
def generate(request: GenerateRequest) -> dict[str, Any]:
    result = agent.build(
        request.prompt,
        project_name=request.project_name,
        run_after=request.run_after,
        install_dependencies=request.install_dependencies,
    )
    project_name = Path(result.generation.project_path).name
    persist_project(Path(result.generation.project_path))
    return {
        **result.to_dict(),
        "project_name": project_name,
        "tree": build_tree(Path(result.generation.project_path)),
    }


@app.post("/api/open-folder")
def open_folder(request: OpenFolderRequest) -> dict[str, Any]:
    source = Path(request.folder_path).expanduser().resolve()
    validate_import_source(source)
    target = unique_project_path(source.name)
    ignore = shutil.ignore_patterns(".git", "node_modules", ".venv", "__pycache__", "dist", "build", ".memory", ".logs")
    shutil.copytree(source, target, ignore=ignore)
    ensure_project_manifest(target, source)
    persist_project(target)
    return {
        "project_name": target.name,
        "project_path": str(target),
        "tree": build_tree(target),
        "message": f"Opened folder by importing a working copy from {source}",
    }


@app.get("/api/projects")
def projects() -> list[dict[str, Any]]:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(PROJECTS_ROOT.iterdir(), key=project_updated_at, reverse=True):
        if not path.is_dir():
            continue
        plan_path = path / ".omnigamedev" / "plan.json"
        plan_data: dict[str, Any] = {}
        if plan_path.exists():
            plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "name": path.name,
                "path": str(path),
                "engine": plan_data.get("engine", ""),
                "language": plan_data.get("language", ""),
                "game_type": plan_data.get("game_type", ""),
                "updated_at": project_updated_at(path),
            }
        )
    return rows


@app.get("/api/presets")
def presets() -> list[dict[str, Any]]:
    return [
        {
            "name": preset.name,
            "triggers": list(preset.triggers),
            "modules": list(preset.modules),
            "systems": list(preset.systems),
            "assets": list(preset.assets),
        }
        for preset in PRESETS
    ]


@app.get("/api/plugins")
def plugins() -> list[dict[str, Any]]:
    return [
        {
            "name": plugin.name,
            "language": plugin.language,
            "engine": plugin.engine,
            "path": str(plugin.path),
            "metadata": plugin.metadata,
        }
        for plugin in PluginManager(ROOT / "plugins").discover()
    ]


def project_updated_at(path: Path) -> float:
    manifest = path / ".omnigamedev" / "manifest.json"
    if manifest.exists():
        return manifest.stat().st_mtime
    return path.stat().st_mtime


def unique_project_path(name: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name).strip("-") or "opened-folder"
    candidate = PROJECTS_ROOT / safe
    index = 2
    while candidate.exists():
        candidate = PROJECTS_ROOT / f"{safe}-{index}"
        index += 1
    return candidate


def validate_import_source(source: Path) -> None:
    if not source.exists() or not source.is_dir():
        raise HTTPException(status_code=404, detail="Folder does not exist.")
    if is_inside(PROJECTS_ROOT.resolve(), source):
        return
    home = Path.home().resolve()
    blocked = {home, ROOT.resolve(), PROJECTS_ROOT.resolve()}
    if source.anchor:
        blocked.add(Path(source.anchor).resolve())
    if source in blocked:
        raise HTTPException(status_code=400, detail="Choose a specific project folder, not a root or home folder.")
    files = [item for item in source.rglob("*") if item.is_file()]
    if len(files) > 1200:
        raise HTTPException(status_code=400, detail="Folder is too large to import into the IDE safely.")


def infer_plan_for_folder(project_path: Path) -> ProjectPlan:
    if (project_path / "package.json").exists():
        return ProjectPlan(
            request=f"opened existing JavaScript project {project_path.name}",
            project_name=project_path.name,
            engine="Three.js",
            language="JavaScript",
            framework="JavaScript",
            game_type="existing project",
            modules=["opened folder", "code review", "manual editing"],
            systems=["smoke execution"],
            assets=[],
            dependencies={"runtime": ["node"], "development": ["npm"]},
            commands={"smoke": "node --check src/main.js"},
            acceptance_tests=["Project can be browsed and edited in the IDE."],
        )
    if (project_path / "main.py").exists() or (project_path / "requirements.txt").exists():
        return ProjectPlan(
            request=f"opened existing Python project {project_path.name}",
            project_name=project_path.name,
            engine="Pygame",
            language="Python",
            framework="Python",
            game_type="existing project",
            modules=["opened folder", "code review", "manual editing"],
            systems=["smoke execution"],
            assets=[],
            dependencies={"runtime": ["python"], "development": ["pip"]},
            commands={"smoke": "python -m py_compile main.py"},
            acceptance_tests=["Project can be browsed and edited in the IDE."],
        )
    if (project_path / "Assets" / "Scripts").exists():
        return ProjectPlan(
            request=f"opened existing Unity project {project_path.name}",
            project_name=project_path.name,
            engine="Unity",
            language="C#",
            framework="Unity",
            game_type="existing project",
            modules=["opened folder", "code review", "manual editing"],
            systems=["layout validation"],
            assets=[],
            dependencies={"runtime": ["Unity"], "development": ["Unity Editor"]},
            commands={"smoke": "validate script layout"},
            acceptance_tests=["Unity scripts can be browsed and edited in the IDE."],
        )
    return ProjectPlan(
        request=f"opened existing project {project_path.name}",
        project_name=project_path.name,
        engine="Generic",
        language="Text",
        framework="Unknown",
        game_type="existing project",
        modules=["opened folder", "code review", "manual editing"],
        systems=["static analysis"],
        assets=[],
        dependencies={},
        commands={},
        acceptance_tests=["Project can be browsed and edited in the IDE."],
    )


def ensure_project_manifest(target: Path, source: Path) -> None:
    meta_dir = target / ".omnigamedev"
    meta_dir.mkdir(parents=True, exist_ok=True)
    plan = infer_plan_for_folder(target)
    (meta_dir / "plan.json").write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")
    manifest = {
        "schema": "omnigamedev.project.v1",
        "opened_from": str(source),
        "plan": plan.to_dict(),
        "adapter": "OpenedFolder",
    }
    (meta_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


@app.get("/api/projects/{project}/tree")
def tree(project: str) -> list[dict[str, Any]]:
    return build_tree(safe_project(project))


@app.get("/api/projects/{project}/file")
def file(project: str, path: str = Query(...)) -> dict[str, str]:
    project_path = safe_project(project)
    target = safe_file(project_path, path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": path, "content": target.read_text(encoding="utf-8")}


@app.put("/api/projects/{project}/file")
def save_file(project: str, request: SaveFileRequest) -> dict[str, Any]:
    project_path = safe_project(project)
    target = safe_file(project_path, request.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(request.content, encoding="utf-8")
    persist_project(project_path)
    return {"ok": True, "path": request.path, "tree": build_tree(project_path)}


@app.post("/api/projects/{project}/ai-action")
def ai_action(project: str, request: AiActionRequest) -> dict[str, Any]:
    project_path = safe_project(project)
    plan_data = read_plan(project_path)

    if request.mode == "review":
        result = agent.code_assistant.review_project(project_path, plan_data)
        run_result = executor.run_project(project_path, plan_data)
        payload = result.to_dict()
        payload["execution"] = run_result.to_dict()
        payload["tree"] = build_tree(project_path)
        return payload

    if request.mode == "improve":
        result = agent.code_assistant.improve_project(project_path, plan_data, request.prompt)
        run_result = executor.run_project(project_path, plan_data)
        persist_project(project_path)
        payload = result.to_dict()
        payload["execution"] = run_result.to_dict()
        payload["tree"] = build_tree(project_path)
        return payload

    if not request.path:
        raise HTTPException(status_code=400, detail="Edit mode requires a selected file path.")
    target = safe_file(project_path, request.path)
    if request.content is not None:
        target.write_text(request.content, encoding="utf-8")
    result = agent.code_assistant.edit_file(project_path, request.path, request.prompt, request.content)
    persist_project(project_path)
    payload = result.to_dict()
    payload["tree"] = build_tree(project_path)
    if target.exists():
        payload["file"] = {"path": request.path, "content": target.read_text(encoding="utf-8")}
    return payload


@app.post("/api/projects/{project}/run")
def run_project(project: str) -> dict[str, Any]:
    project_path = safe_project(project)
    plan_data = read_plan(project_path)
    return executor.run_project(project_path, plan_data).to_dict()


@app.get("/api/projects/{project}/zip")
def export_zip(project: str) -> StreamingResponse:
    project_path = safe_project(project)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in project_path.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(project_path).as_posix())
    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{project}.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


@app.get("/api/projects/{project}/preview")
@app.get("/api/projects/{project}/preview/{relative_path:path}")
def preview(project: str, relative_path: str = "") -> Response:
    project_path = safe_project(project)
    if not relative_path:
        if (project_path / "index.html").exists():
            relative_path = "index.html"
        else:
            return HTMLResponse(_non_browser_preview(project_path))

    target = safe_file(project_path, relative_path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Preview asset not found")
    content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    if content_type.startswith("text/") or target.suffix in {".js", ".css", ".html", ".json", ".svg"}:
        return Response(target.read_text(encoding="utf-8"), media_type=content_type)
    return Response(target.read_bytes(), media_type=content_type)


def _non_browser_preview(project_path: Path) -> str:
    readme = project_path / "README.md"
    title = project_path.name
    body = readme.read_text(encoding="utf-8") if readme.exists() else "No browser preview is available for this engine."
    escaped = (
        body.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      body {{ margin: 0; padding: 24px; background: #101416; color: #eef7f7; font: 14px/1.6 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
      pre {{ white-space: pre-wrap; }}
    </style>
    <title>{title}</title>
  </head>
  <body><pre>{escaped}</pre></body>
</html>"""
