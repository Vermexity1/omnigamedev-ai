from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from executor.debugger import SelfHealingDebugger
from executor.executor import CommandResult, RunResult
from planner import TaskPlanner
from plugins import PluginManager


class SelfHealAndPluginTests(unittest.TestCase):
    def test_self_heal_adds_missing_pygame_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "requirements.txt").write_text("", encoding="utf-8")
            plan = TaskPlanner().create_plan("build a pygame platformer")
            result = RunResult(
                success=False,
                project_path=str(root),
                command_results=[
                    CommandResult(
                        label="smoke",
                        args=["python", "main.py"],
                        returncode=1,
                        stdout="",
                        stderr="ModuleNotFoundError: No module named 'pygame'",
                        duration_seconds=0.1,
                    )
                ],
                error_summary="No module named 'pygame'",
            )

            fixes = SelfHealingDebugger().heal(root, plan, result)

            self.assertTrue(fixes)
            self.assertIn("pygame>=2.5", (root / "requirements.txt").read_text(encoding="utf-8"))

    def test_plugin_manager_discovers_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = Path(temp_dir) / "phaser"
            plugin.mkdir()
            (plugin / "plugin.json").write_text(
                '{"name":"Phaser 2D","language":"JavaScript","engine":"Phaser"}',
                encoding="utf-8",
            )

            plugins = PluginManager(temp_dir).discover()

            self.assertEqual(len(plugins), 1)
            self.assertEqual(plugins[0].engine, "Phaser")


if __name__ == "__main__":
    unittest.main()
