from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent.code_assistant import ProjectCodeAssistant
from planner import TaskPlanner


class CodeAssistantTests(unittest.TestCase):
    def test_review_finds_missing_smoke_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "package.json").write_text('{"scripts":{"dev":"vite"}}', encoding="utf-8")

            result = ProjectCodeAssistant().review_project(root)

            self.assertTrue(any("smoke script" in finding.message for finding in result.findings))

    def test_improve_three_js_project_adds_graphics_systems(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = TaskPlanner().create_plan("build a 3D dungeon game with bosses")
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "style.css").write_text(".hud { color: white; }\n", encoding="utf-8")
            (root / "src" / "main.js").write_text(
                """import * as THREE from "three";
function material(color, roughness = 0.78) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.04 });
}
function buildDungeon(scene) {
  const enemies = [];
  let playerStart = new THREE.Vector3(0, 0, 0);
  let boss = null;
  const floor = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), material(0xffffff));
  scene.add(floor);
  return { walls, enemies, boss, playerStart };
}
function attack(player, enemies, boss, hud) {}
export function createGame(root = document.getElementById("app")) {
  const scene = new THREE.Scene();
  const { walls, enemies, boss, playerStart } = buildDungeon(scene);
  function animate() {
    const delta = 0.016;
    updateEnemies(player, enemies, boss, walls, delta);
    updateCamera(camera, player);
  }
}
""",
                encoding="utf-8",
            )

            result = ProjectCodeAssistant().improve_project(root, plan, "make the graphics better")
            main = (root / "src" / "main.js").read_text(encoding="utf-8")

            self.assertIn("src/main.js", result.changed_files)
            self.assertIn("createTorch", main)
            self.assertIn("createPickup", main)

    def test_edit_file_can_add_documentation_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "main.py"
            target.write_text("print('hello')\n", encoding="utf-8")

            result = ProjectCodeAssistant().edit_file(root, "main.py", "add comments")

            self.assertIn("main.py", result.changed_files)
            self.assertTrue(target.read_text(encoding="utf-8").startswith('"""Generated'))


if __name__ == "__main__":
    unittest.main()
