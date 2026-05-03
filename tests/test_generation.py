from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from executor import ExecutionEngine
from generator.code_generator import CodeGenerator
from planner import TaskPlanner


class GenerationTests(unittest.TestCase):
    def test_javascript_project_generates_and_smokes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = TaskPlanner().create_plan("build a 3D dungeon game with bosses")
            result = CodeGenerator(Path(temp_dir)).generate_project(plan)

            root = Path(result.project_path)
            self.assertTrue((root / "index.html").exists())
            self.assertTrue((root / "src" / "main.js").exists())
            manifest = json.loads((root / ".omnigamedev" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["adapter"], "JavaScriptAdapter")

            run = ExecutionEngine().run_project(root, plan)
            self.assertTrue(run.success, run.error_summary)

    def test_unity_project_generates_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = TaskPlanner().create_plan("build a Unity dungeon RPG with boss fights")
            result = CodeGenerator(Path(temp_dir)).generate_project(plan)
            root = Path(result.project_path)

            self.assertTrue((root / "Assets" / "Scripts" / "PlayerController.cs").exists())
            self.assertTrue((root / "Assets" / "Scripts" / "EnemyAI.cs").exists())
            self.assertTrue((root / "Assets" / "OmniGameDev" / "SceneSetup.md").exists())


if __name__ == "__main__":
    unittest.main()
