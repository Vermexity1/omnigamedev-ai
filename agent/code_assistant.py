from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.llm import LLMMessage, LLMProvider, NullLLMProvider
from memory import MemoryStore
from planner.schemas import ProjectPlan


@dataclass(slots=True)
class CodeFinding:
    file: str
    line: int
    severity: str
    message: str


@dataclass(slots=True)
class CodeActionResult:
    message: str
    findings: list[CodeFinding] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "findings": [finding.__dict__ for finding in self.findings],
            "changed_files": self.changed_files,
            "notes": self.notes,
        }


class ProjectCodeAssistant:
    """Codex-like project helper for review, deterministic improvement, and file edits."""

    text_extensions = {".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".html", ".json", ".md", ".cs", ".cpp", ".h", ".hpp"}
    color_words = {
        "green": "0x22c55e",
        "lime": "0x84cc16",
        "emerald": "0x10b981",
        "red": "0xef4444",
        "blue": "0x3b82f6",
        "cyan": "0x06b6d4",
        "teal": "0x14b8a6",
        "purple": "0x8b5cf6",
        "violet": "0x7c3aed",
        "pink": "0xec4899",
        "orange": "0xf97316",
        "yellow": "0xfacc15",
        "gold": "0xf59e0b",
        "white": "0xf8fafc",
        "black": "0x020617",
        "gray": "0x64748b",
        "grey": "0x64748b",
        "brown": "0x854d0e",
    }

    def __init__(self, llm: LLMProvider | None = None, memory: MemoryStore | None = None) -> None:
        self.llm = llm or NullLLMProvider()
        self.memory = memory

    def review_project(self, project_path: Path, plan: ProjectPlan | None = None) -> CodeActionResult:
        findings: list[CodeFinding] = []
        files = self._source_files(project_path)

        if not (project_path / "README.md").exists():
            findings.append(CodeFinding("README.md", 1, "warning", "Project is missing a README with run instructions."))
        if not (project_path / ".omnigamedev" / "plan.json").exists():
            findings.append(CodeFinding(".omnigamedev/plan.json", 1, "error", "Project is missing the OmniGameDev plan manifest."))

        package_json = project_path / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {})
                if "smoke" not in scripts:
                    findings.append(CodeFinding("package.json", 1, "warning", "Add a smoke script so the agent can validate JavaScript projects quickly."))
            except json.JSONDecodeError as exc:
                findings.append(CodeFinding("package.json", exc.lineno, "error", f"package.json is invalid JSON: {exc.msg}."))

        for relative, path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            findings.extend(self._scan_text(relative, text))

        if plan and plan.language == "JavaScript" and (project_path / "src" / "main.js").exists():
            main_text = (project_path / "src" / "main.js").read_text(encoding="utf-8", errors="replace")
            if "window.omniGame" not in main_text:
                findings.append(CodeFinding("src/main.js", 1, "info", "Expose window.omniGame to make browser verification and debugging easier."))
            if "requestAnimationFrame" not in main_text:
                findings.append(CodeFinding("src/main.js", 1, "error", "No animation loop found for the browser game."))
            if "PointLight" not in main_text:
                findings.append(CodeFinding("src/main.js", 1, "info", "Add local lights or effects to make the generated game feel more complete."))

        summary = "No obvious issues found." if not findings else f"Found {len(findings)} possible issue(s) or improvement(s)."
        return CodeActionResult(summary, findings=findings)

    def improve_project(self, project_path: Path, plan: ProjectPlan, prompt: str = "") -> CodeActionResult:
        if plan.language == "JavaScript" and (project_path / "src" / "main.js").exists():
            return self._improve_three_js_project(project_path, prompt)
        if plan.language == "Python" and (project_path / "main.py").exists():
            return self._improve_python_project(project_path)

        review = self.review_project(project_path, plan)
        review.message = "No deterministic project improver exists for this engine yet; review results are shown instead."
        return review

    def edit_project(
        self,
        project_path: Path,
        plan: ProjectPlan,
        instruction: str,
        selected_path: str | None = None,
        current_content: str | None = None,
    ) -> CodeActionResult:
        """Apply a project-level feature request to the right implementation files.

        This is intentionally tried before selected-file editing because users often
        describe game behavior while a README or asset is selected.
        """

        if selected_path and current_content is not None:
            target = (project_path / selected_path).resolve()
            if target.exists() and target.suffix in self.text_extensions:
                target.write_text(current_content, encoding="utf-8")

        lowered = instruction.lower()
        if plan.language == "JavaScript" and (project_path / "src" / "main.js").exists():
            result = self._edit_three_js_project(project_path, lowered)
            if result.changed_files:
                self._remember(f"Applied Three.js semantic edit: {instruction}; changed {', '.join(result.changed_files)}")
                return result

        if plan.language == "Python" and (project_path / "main.py").exists():
            result = self._edit_python_project(project_path, lowered)
            if result.changed_files:
                self._remember(f"Applied Python semantic edit: {instruction}; changed {', '.join(result.changed_files)}")
                return result

        if selected_path:
            return self.edit_file(project_path, selected_path, instruction, current_content)
        return CodeActionResult(
            "No project-level edit rule matched that request. I need a more specific gameplay target or file selection.",
            notes=["Reviewed the project plan and source tree before declining the edit."],
        )

    def edit_file(self, project_path: Path, relative_path: str, instruction: str, current_content: str | None = None) -> CodeActionResult:
        target = (project_path / relative_path).resolve()
        if not target.exists() or target.suffix not in self.text_extensions:
            return CodeActionResult(f"Cannot edit unsupported or missing file: {relative_path}")

        original = current_content if current_content is not None else target.read_text(encoding="utf-8")
        if self.llm.available():
            edited = self._llm_edit(relative_path, original, instruction)
            if edited and edited != original:
                target.write_text(edited, encoding="utf-8")
                self._remember(f"Edited {relative_path} with LLM instruction: {instruction}")
                return CodeActionResult("Applied LLM edit to the selected file.", changed_files=[relative_path])

        edited = self._deterministic_file_edit(relative_path, original, instruction)
        if edited != original:
            target.write_text(edited, encoding="utf-8")
            self._remember(f"Edited {relative_path} with deterministic instruction: {instruction}")
            return CodeActionResult("Applied deterministic edit to the selected file.", changed_files=[relative_path])

        return CodeActionResult("No safe automatic edit matched that instruction. Try Improve Project or be more specific.")

    def _llm_edit(self, relative_path: str, content: str, instruction: str) -> str | None:
        system = (
            "You are OmniGameDev AI acting as a coding agent. Return only the full edited file content. "
            "Do not wrap it in markdown. Preserve working behavior and keep changes scoped to the user's instruction."
        )
        user = f"File: {relative_path}\nInstruction: {instruction}\n\nCurrent file:\n{content[:30000]}"
        try:
            response = self.llm.chat([LLMMessage("system", system), LLMMessage("user", user)], temperature=0.15)
            edited = response.content.strip()
            if edited.startswith("```"):
                edited = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", edited)
                edited = re.sub(r"\n```$", "", edited)
            return edited
        except Exception:
            return None

    def _deterministic_file_edit(self, relative_path: str, content: str, instruction: str) -> str:
        lowered = instruction.lower()
        if any(word in lowered for word in ["comment", "explain", "document"]):
            return self._add_file_header(relative_path, content)
        if relative_path.endswith(".js") and any(word in lowered for word in ["debug", "verify", "test"]):
            if "window.omniGame" not in content and "createGame" in content:
                return content.replace("createGame();", "window.omniGame = createGame();")
        if relative_path.endswith(".css") and any(word in lowered for word in ["button", "text", "fit", "layout"]):
            return content + "\nbutton { min-width: 0; }\n"
        return content

    def _edit_three_js_project(self, project_path: Path, lowered: str) -> CodeActionResult:
        main_path = project_path / "src" / "main.js"
        style_path = project_path / "src" / "style.css"
        main = main_path.read_text(encoding="utf-8")
        style = style_path.read_text(encoding="utf-8") if style_path.exists() else ""
        changed: list[str] = []
        notes: list[str] = []

        color = self._requested_color(lowered)
        material_target = self._material_target(lowered)
        if color and material_target:
            main, did_change = self._set_three_material(main, material_target, color)
            if did_change:
                changed.append("src/main.js")
                notes.append(f"Changed the {material_target} material color to {color}.")

        if any(phrase in lowered for phrase in ["first person", "first-person", "fps", "camera view", "player view", "through the player"]):
            main, did_change = self._apply_first_person_three_js(main)
            if did_change:
                changed.append("src/main.js")
                notes.append("Changed camera, mouse-look, and WASD movement to first-person controls.")
                if "Click preview to look" not in style:
                    style += "\ncanvas { cursor: crosshair; }\n"
                    changed.append("src/style.css")

        speed = self._requested_speed(lowered)
        if speed is not None:
            main, did_change = re.subn(r"const player = new Combatant\(playerMesh, 100, [0-9.]+\);", f"const player = new Combatant(playerMesh, 100, {speed});", main, count=1)
            if did_change:
                changed.append("src/main.js")
                notes.append(f"Changed player movement speed to {speed}.")

        if any(word in lowered for word in ["brighter", "brighten", "more light", "lighter"]):
            main, did_change = re.subn(r"new THREE\.HemisphereLight\((0x[0-9a-fA-F]+), (0x[0-9a-fA-F]+), [0-9.]+\)", r"new THREE.HemisphereLight(\1, \2, 1.8)", main, count=1)
            if did_change:
                changed.append("src/main.js")
                notes.append("Increased ambient hemisphere light intensity.")

        if any(word in lowered for word in ["darker", "darken", "scarier", "spooky"]):
            main, did_change = re.subn(r"scene\.fog = new THREE\.Fog\((0x[0-9a-fA-F]+), [0-9.]+, [0-9.]+\);", r"scene.fog = new THREE.Fog(\1, 6, 24);", main, count=1)
            if did_change:
                changed.append("src/main.js")
                notes.append("Moved fog closer for a darker dungeon atmosphere.")

        if not changed:
            return CodeActionResult("No Three.js semantic edit matched that instruction.")

        main_path.write_text(main, encoding="utf-8")
        if style_path.exists() or "src/style.css" in changed:
            style_path.write_text(style, encoding="utf-8")
        return CodeActionResult(
            "Applied gameplay-aware Three.js code changes.",
            changed_files=sorted(set(changed)),
            notes=notes,
        )

    def _edit_python_project(self, project_path: Path, lowered: str) -> CodeActionResult:
        main_path = project_path / "main.py"
        text = main_path.read_text(encoding="utf-8")
        changed = False
        notes: list[str] = []

        color = self._requested_rgb(lowered)
        if color and any(word in lowered for word in ["wall", "walls", "block", "blocks"]):
            text, count = re.subn(r"pygame\.draw\.rect\(screen, \([0-9,\s]+\), wall\)", f"pygame.draw.rect(screen, {color}, wall)", text)
            changed = changed or bool(count)
            if count:
                notes.append(f"Changed Pygame wall draw color to {color}.")

        speed = self._requested_speed(lowered)
        if speed is not None:
            text, count = re.subn(r"player = Actor\(pygame\.Rect\(0, 0, 30, 30\), 100, [0-9.]+,", f"player = Actor(pygame.Rect(0, 0, 30, 30), 100, {speed * 45:.0f},", text)
            changed = changed or bool(count)
            if count:
                notes.append("Changed Pygame player movement speed.")

        if not changed:
            return CodeActionResult("No Pygame semantic edit matched that instruction.")
        main_path.write_text(text, encoding="utf-8")
        return CodeActionResult("Applied gameplay-aware Pygame code changes.", changed_files=["main.py"], notes=notes)

    def _set_three_material(self, main: str, target: str, color: str) -> tuple[str, bool]:
        variable = {
            "wall": "wallMaterial",
            "floor": "floorMaterial",
            "enemy": "enemyMaterial",
            "boss": "bossMaterial",
            "player": "player",
            "background": "background",
            "sky": "background",
            "fog": "fog",
        }[target]
        if target == "player":
            updated, count = re.subn(r"new THREE\.CapsuleGeometry\(([^)]+)\), material\(0x[0-9a-fA-F]+\)", rf"new THREE.CapsuleGeometry(\1), material({color})", main, count=1)
            return updated, bool(count)
        if target in {"background", "sky"}:
            updated, count = re.subn(r"scene\.background = new THREE\.Color\(0x[0-9a-fA-F]+\);", f"scene.background = new THREE.Color({color});", main, count=1)
            return updated, bool(count)
        if target == "fog":
            updated, count = re.subn(r"scene\.fog = new THREE\.Fog\(0x[0-9a-fA-F]+,", f"scene.fog = new THREE.Fog({color},", main, count=1)
            return updated, bool(count)
        updated, count = re.subn(rf"const {variable} = material\(0x[0-9a-fA-F]+", f"const {variable} = material({color}", main, count=1)
        return updated, bool(count)

    def _apply_first_person_three_js(self, main: str) -> tuple[str, bool]:
        changed = False
        if "const pointer = { yaw: 0, pitch: 0 };" not in main:
            main = main.replace("const clock = new THREE.Clock();", "const clock = new THREE.Clock();\nconst pointer = { yaw: 0, pitch: 0 };")
            changed = True

        first_person_camera = """function updateCamera(camera, player) {
  const target = player.mesh.position;
  camera.position.lerp(new THREE.Vector3(target.x, 1.55, target.z), 0.35);
  camera.rotation.order = "YXZ";
  camera.rotation.y = pointer.yaw;
  camera.rotation.x = pointer.pitch;
  player.mesh.visible = false;
}
"""
        main, count = re.subn(r"function updateCamera\(camera, player\) \{[\s\S]*?\n\}\n\nfunction moveWithCollision", first_person_camera + "\nfunction moveWithCollision", main, count=1)
        changed = changed or bool(count)

        first_person_player = """function updatePlayer(player, walls, delta) {
  const forward = new THREE.Vector3(-Math.sin(pointer.yaw), 0, -Math.cos(pointer.yaw));
  const right = new THREE.Vector3(Math.cos(pointer.yaw), 0, -Math.sin(pointer.yaw));
  const direction = new THREE.Vector3();
  if (keys.has("KeyW") || keys.has("ArrowUp")) direction.add(forward);
  if (keys.has("KeyS") || keys.has("ArrowDown")) direction.sub(forward);
  if (keys.has("KeyA") || keys.has("ArrowLeft")) direction.sub(right);
  if (keys.has("KeyD") || keys.has("ArrowRight")) direction.add(right);
  if (direction.length() > 0) {
    direction.normalize().multiplyScalar(player.speed * delta);
    moveWithCollision(player, direction, walls);
  }
  player.mesh.rotation.y = pointer.yaw;
}
"""
        main, count = re.subn(r"function updatePlayer\(player, walls, delta\) \{[\s\S]*?\n\}\n\nfunction attack", first_person_player + "\nfunction attack", main, count=1)
        changed = changed or bool(count)

        if "function handleMouseLook" not in main:
            mouse_code = """function handleMouseLook(event) {
  if (document.pointerLockElement === event.currentTarget || document.pointerLockElement) {
    pointer.yaw -= event.movementX * 0.0022;
    pointer.pitch = Math.max(-1.2, Math.min(1.2, pointer.pitch - event.movementY * 0.002));
  }
}

"""
            main = main.replace("export function createGame", mouse_code + "export function createGame")
            changed = True

        if "renderer.domElement.requestPointerLock" not in main:
            main = main.replace(
                "  window.addEventListener(\"resize\", resize);\n",
                "  window.addEventListener(\"resize\", resize);\n"
                "  renderer.domElement.addEventListener(\"click\", () => renderer.domElement.requestPointerLock());\n"
                "  window.addEventListener(\"mousemove\", handleMouseLook);\n",
            )
            changed = True

        main = main.replace("Explore the dungeon", "Click preview to look; WASD move, Space attack")
        return main, changed

    def _requested_color(self, lowered: str) -> str | None:
        explicit_hex = re.search(r"(?:#|0x)([0-9a-fA-F]{6})", lowered)
        if explicit_hex:
            return f"0x{explicit_hex.group(1)}"
        for word, value in self.color_words.items():
            if re.search(rf"\b{re.escape(word)}\b", lowered):
                return value
        return None

    def _requested_rgb(self, lowered: str) -> str | None:
        color = self._requested_color(lowered)
        if not color:
            return None
        value = int(color, 16)
        return f"({(value >> 16) & 255}, {(value >> 8) & 255}, {value & 255})"

    def _material_target(self, lowered: str) -> str | None:
        targets = {
            "wall": ["wall", "walls", "brick", "bricks", "block", "blocks"],
            "floor": ["floor", "ground"],
            "enemy": ["enemy", "enemies", "monster", "monsters"],
            "boss": ["boss"],
            "player": ["player", "hero"],
            "background": ["background", "sky"],
            "fog": ["fog", "mist"],
        }
        for target, words in targets.items():
            if any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in words):
                return target
        return None

    def _requested_speed(self, lowered: str) -> float | None:
        match = re.search(r"(?:speed|move speed|movement speed)\D+([0-9]+(?:\.[0-9]+)?)", lowered)
        if match:
            return max(1.0, min(12.0, float(match.group(1))))
        if any(word in lowered for word in ["faster", "fast", "quicker", "speed up"]):
            return 6.2
        if any(word in lowered for word in ["slower", "slow down"]):
            return 2.6
        return None

    def _add_file_header(self, relative_path: str, content: str) -> str:
        if relative_path.endswith(".py"):
            header = '"""Generated and maintained by OmniGameDev AI."""\n'
        elif relative_path.endswith((".js", ".jsx", ".ts", ".tsx", ".css", ".cs", ".cpp", ".h", ".hpp")):
            header = "/* Generated and maintained by OmniGameDev AI. */\n"
        elif relative_path.endswith(".html"):
            header = "<!-- Generated and maintained by OmniGameDev AI. -->\n"
        else:
            header = "<!-- Generated and maintained by OmniGameDev AI. -->\n"
        return content if content.startswith(header) else header + content

    def _improve_three_js_project(self, project_path: Path, prompt: str) -> CodeActionResult:
        main_path = project_path / "src" / "main.js"
        style_path = project_path / "src" / "style.css"
        main = main_path.read_text(encoding="utf-8")
        style = style_path.read_text(encoding="utf-8") if style_path.exists() else ""
        changed: list[str] = []

        if "function createTorch" not in main:
            main = main.replace(
                "function material(color, roughness = 0.78) {\n  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.04 });\n}\n",
                "function material(color, roughness = 0.78) {\n  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.04 });\n}\n\n"
                "function emissiveMaterial(color, intensity = 0.8) {\n"
                "  return new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: intensity, roughness: 0.45 });\n"
                "}\n\n"
                "function createTorch(scene, x, z) {\n"
                "  const group = new THREE.Group();\n"
                "  const post = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 1.2, 8), material(0x3b2f2f));\n"
                "  const flame = new THREE.Mesh(new THREE.SphereGeometry(0.22, 14, 10), emissiveMaterial(0xfacc15, 1.4));\n"
                "  const light = new THREE.PointLight(0xf59e0b, 2.6, 7, 1.7);\n"
                "  post.position.y = 0.6;\n"
                "  flame.position.y = 1.35;\n"
                "  light.position.y = 1.35;\n"
                "  group.add(post, flame, light);\n"
                "  group.position.set(x, 0, z);\n"
                "  scene.add(group);\n"
                "  return { group, flame, light, seed: Math.random() * 100 };\n"
                "}\n\n"
                "function createPickup(scene, x, z, index) {\n"
                "  const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.34), emissiveMaterial(index % 2 ? 0x5eead4 : 0xfacc15, 0.9));\n"
                "  gem.position.set(x, 0.7, z);\n"
                "  gem.castShadow = true;\n"
                "  scene.add(gem);\n"
                "  return gem;\n"
                "}\n\n"
                "function createPortal(scene) {\n"
                "  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.78, 0.08, 12, 32), emissiveMaterial(0x8b5cf6, 1.1));\n"
                "  ring.position.set(8, 1.0, 6);\n"
                "  ring.rotation.x = Math.PI / 2;\n"
                "  scene.add(ring);\n"
                "  return ring;\n"
                "}\n",
            )
            changed.append("src/main.js")

        if "decorativeLights" not in main:
            main = main.replace(
                "  const enemies = [];\n  let playerStart = new THREE.Vector3(0, 0, 0);\n  let boss = null;\n",
                "  const enemies = [];\n  const decorativeLights = [];\n  const pickups = [];\n  let portal = null;\n  let playerStart = new THREE.Vector3(0, 0, 0);\n  let boss = null;\n",
            )
            main = main.replace(
                "  scene.add(floor);\n",
                "  scene.add(floor);\n\n"
                "  decorativeLights.push(createTorch(scene, -8, -6), createTorch(scene, 8, -6), createTorch(scene, -8, 6), createTorch(scene, 8, 6));\n"
                "  pickups.push(createPickup(scene, -4, -2, 0), createPickup(scene, 2, 4, 1), createPickup(scene, 6, -2, 2));\n"
                "  portal = createPortal(scene);\n",
                1,
            )
            main = main.replace(
                "  return { walls, enemies, boss, playerStart };\n",
                "  return { walls, enemies, boss, playerStart, decorativeLights, pickups, portal };\n",
            )
            main = main.replace(
                "function attack(player, enemies, boss, hud) {\n",
                "function updateDecorations(decorativeLights, pickups, portal, delta) {\n"
                "  decorativeLights.forEach((torch) => {\n"
                "    torch.flame.scale.setScalar(0.85 + Math.sin(performance.now() * 0.007 + torch.seed) * 0.12);\n"
                "    torch.light.intensity = 2.2 + Math.sin(performance.now() * 0.006 + torch.seed) * 0.5;\n"
                "  });\n"
                "  pickups.forEach((pickup, index) => {\n"
                "    if (!pickup.visible) return;\n"
                "    pickup.rotation.y += delta * (1.8 + index * 0.2);\n"
                "    pickup.position.y = 0.7 + Math.sin(performance.now() * 0.003 + index) * 0.12;\n"
                "  });\n"
                "  if (portal) {\n"
                "    portal.rotation.z += delta * 1.3;\n"
                "  }\n"
                "}\n\n"
                "function collectPickups(player, pickups, hud) {\n"
                "  pickups.forEach((pickup) => {\n"
                "    if (pickup.visible && pickup.position.distanceTo(player.mesh.position) < 1.2) {\n"
                "      pickup.visible = false;\n"
                "      player.health = Math.min(player.maxHealth, player.health + 12);\n"
                "      hud.status.textContent = \"Relic collected\";\n"
                "    }\n"
                "  });\n"
                "}\n\n"
                "function attack(player, enemies, boss, hud) {\n",
            )
            main = main.replace(
                "  const { walls, enemies, boss, playerStart } = buildDungeon(scene);\n",
                "  const { walls, enemies, boss, playerStart, decorativeLights, pickups, portal } = buildDungeon(scene);\n",
            )
            main = main.replace(
                "    updateEnemies(player, enemies, boss, walls, delta);\n    updateCamera(camera, player);\n",
                "    updateEnemies(player, enemies, boss, walls, delta);\n    updateDecorations(decorativeLights, pickups, portal, delta);\n    collectPickups(player, pickups, hud);\n    updateCamera(camera, player);\n",
            )
            if "src/main.js" not in changed:
                changed.append("src/main.js")

        if ".hud kbd" not in style:
            style += """

.hud kbd {
  border: 1px solid rgba(148, 163, 184, 0.38);
  border-radius: 4px;
  padding: 1px 5px;
  color: #facc15;
  background: rgba(15, 23, 42, 0.9);
}
"""
            changed.append("src/style.css")

        if changed:
            main_path.write_text(main, encoding="utf-8")
            style_path.write_text(style, encoding="utf-8")
            self._remember(f"Improved Three.js project graphics: {', '.join(changed)}. Prompt: {prompt}")
            return CodeActionResult(
                "Improved the Three.js project with torches, pickup relics, animated portal, emissive materials, and richer lighting.",
                changed_files=sorted(set(changed)),
            )
        return CodeActionResult("This Three.js project already has the advanced graphics upgrade.")

    def _improve_python_project(self, project_path: Path) -> CodeActionResult:
        main_path = project_path / "main.py"
        text = main_path.read_text(encoding="utf-8")
        if "def clamp(" in text:
            return CodeActionResult("Python project already has the deterministic helper upgrade.")
        helper = "\n\ndef clamp(value, low, high):\n    return max(low, min(high, value))\n"
        insert_at = text.find("\n\ndef smoke()")
        if insert_at == -1:
            text += helper
        else:
            text = text[:insert_at] + helper + text[insert_at:]
        main_path.write_text(text, encoding="utf-8")
        self._remember("Improved Python project with shared clamp helper.")
        return CodeActionResult("Improved Python project with a shared clamp helper for safer game-state math.", changed_files=["main.py"])

    def _scan_text(self, relative: str, text: str) -> list[CodeFinding]:
        findings: list[CodeFinding] = []
        for index, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            if "todo" in lowered or "fixme" in lowered:
                findings.append(CodeFinding(relative, index, "info", "Unresolved TODO/FIXME marker."))
            if "\t" in line and relative.endswith((".py", ".js", ".jsx", ".ts", ".tsx")):
                findings.append(CodeFinding(relative, index, "info", "Tab indentation found; keep formatting consistent."))
            if len(line) > 140 and relative.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".cs", ".cpp")):
                findings.append(CodeFinding(relative, index, "info", "Long line may be harder to maintain."))
        return findings[:80]

    def _source_files(self, project_path: Path) -> list[tuple[str, Path]]:
        ignored = {"node_modules", ".venv", "__pycache__", "dist", "build", ".git"}
        files: list[tuple[str, Path]] = []
        for path in project_path.rglob("*"):
            if not path.is_file() or path.suffix not in self.text_extensions:
                continue
            if any(part in ignored for part in path.parts):
                continue
            files.append((path.relative_to(project_path).as_posix(), path))
        return files

    def _remember(self, text: str) -> None:
        if self.memory is not None:
            self.memory.add(text, {"kind": "code_assistant"})
