from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.code_assistant import ProjectCodeAssistant
from generator.code_generator import CodeGenerator
from planner import TaskPlanner


@dataclass(slots=True)
class BenchmarkCase:
    name: str
    instruction: str
    checks: dict[str, str]


CASES = [
    BenchmarkCase(
        "first_person_camera",
        "change the game to first person",
        {
            "src/main.js": "requestPointerLock",
            "src/main.js#2": "camera.rotation.order = \"YXZ\"",
            "src/main.js#3": "direction.add(forward)",
        },
    ),
    BenchmarkCase(
        "green_walls",
        "make the walls green",
        {"src/main.js": "const wallMaterial = material(0x22c55e);"},
    ),
    BenchmarkCase(
        "blue_enemies",
        "make enemies blue",
        {"src/main.js": "const enemyMaterial = material(0x3b82f6);"},
    ),
    BenchmarkCase(
        "faster_player",
        "make the player faster",
        {"src/main.js": "const player = new Combatant(playerMesh, 100, 6.2);"},
    ),
]


def run_benchmark() -> dict:
    planner = TaskPlanner()
    plan = planner.create_plan("build a 3D dungeon game with bosses")
    assistant = ProjectCodeAssistant()
    rows = []

    for case in CASES:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = CodeGenerator(Path(temp_dir)).generate_project(plan)
            project_path = Path(project.project_path)
            result = assistant.edit_project(project_path, plan, case.instruction, "README.md", "Text-only baseline target.\n")
            failed_checks = []
            for key, expected in case.checks.items():
                file_name = key.split("#", 1)[0]
                text = (project_path / file_name).read_text(encoding="utf-8")
                if expected not in text:
                    failed_checks.append({"file": file_name, "expected": expected})
            readme_text = (project_path / "README.md").read_text(encoding="utf-8")
            changed_readme_only = result.changed_files == ["README.md"] or case.instruction in readme_text
            rows.append(
                {
                    "case": case.name,
                    "instruction": case.instruction,
                    "passed": not failed_checks and not changed_readme_only,
                    "changed_files": result.changed_files,
                    "failed_checks": failed_checks,
                    "message": result.message,
                    "notes": result.notes,
                }
            )

    passed = sum(1 for row in rows if row["passed"])
    return {
        "suite": "game_edit_semantics_v1",
        "agent": "OmniGameDev deterministic semantic editor",
        "passed": passed,
        "total": len(rows),
        "score": passed / len(rows),
        "cases": rows,
        "openai_model_comparison": {
            "status": "not_run",
            "reason": "No OpenAI API model calls were run in this benchmark. Do not infer GPT-5.2 or other model scores from this local test.",
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_benchmark(), indent=2))
