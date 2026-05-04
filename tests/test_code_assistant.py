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

    def test_project_edit_changes_wall_material_not_readme(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = TaskPlanner().create_plan("build a 3D dungeon game with bosses")
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "README.md").write_text("Walls are normal.\n", encoding="utf-8")
            (root / "src" / "main.js").write_text(
                """import * as THREE from "three";
function material(color, roughness = 0.78) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.04 });
}
function buildDungeon(scene) {
  const wallMaterial = material(0x7c6f64);
  return { walls: [], enemies: [], boss: null, playerStart: new THREE.Vector3(0, 0, 0) };
}
""",
                encoding="utf-8",
            )

            result = ProjectCodeAssistant().edit_project(root, plan, "make the walls green", "README.md", "Walls are normal.\n")
            main = (root / "src" / "main.js").read_text(encoding="utf-8")

            self.assertIn("src/main.js", result.changed_files)
            self.assertIn("const wallMaterial = material(0x22c55e);", main)
            self.assertEqual((root / "README.md").read_text(encoding="utf-8"), "Walls are normal.\n")

    def test_project_edit_changes_first_person_camera_and_movement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = TaskPlanner().create_plan("build a 3D dungeon game with bosses")
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "style.css").write_text("", encoding="utf-8")
            (root / "src" / "main.js").write_text(
                """import * as THREE from "three";
const clock = new THREE.Clock();
function updateCamera(camera, player) {
  const target = player.mesh.position;
  camera.position.lerp(new THREE.Vector3(target.x + 6, 7, target.z + 8), 0.08);
  camera.lookAt(target.x, 0.6, target.z);
}

function moveWithCollision(entity, deltaMove, walls) {}

function updatePlayer(player, walls, delta) {
  const direction = new THREE.Vector3();
  if (keys.has("KeyW") || keys.has("ArrowUp")) direction.z -= 1;
  if (keys.has("KeyS") || keys.has("ArrowDown")) direction.z += 1;
  if (keys.has("KeyA") || keys.has("ArrowLeft")) direction.x -= 1;
  if (keys.has("KeyD") || keys.has("ArrowRight")) direction.x += 1;
  if (direction.length() > 0) {
    direction.normalize().multiplyScalar(player.speed * delta);
    moveWithCollision(player, direction, walls);
  }
  player.mesh.rotation.y += delta * 1.5;
}

function attack(player, enemies, boss, hud) {}
export function createGame(root = document.getElementById("app")) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  window.addEventListener("resize", resize);
}
""",
                encoding="utf-8",
            )

            result = ProjectCodeAssistant().edit_project(root, plan, "change it to first person")
            main = (root / "src" / "main.js").read_text(encoding="utf-8")

            self.assertIn("src/main.js", result.changed_files)
            self.assertIn("const pointer = { yaw: 0, pitch: 0 };", main)
            self.assertIn("requestPointerLock", main)
            self.assertIn("camera.rotation.order = \"YXZ\"", main)
            self.assertIn("direction.add(forward)", main)


if __name__ == "__main__":
    unittest.main()
