from __future__ import annotations

import json
import re
from typing import Iterable

from agent.llm import LLMMessage, LLMProvider, NullLLMProvider
from planner.presets import preset_for_request
from planner.schemas import ProjectPlan


class TaskPlanner:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or NullLLMProvider()

    def create_plan(self, request: str, memory_context: Iterable[str] | None = None) -> ProjectPlan:
        memory_text = "\n".join(memory_context or [])
        llm_plan = self._try_llm_plan(request, memory_text)
        if llm_plan:
            return llm_plan
        return self._heuristic_plan(request, memory_text)

    def _try_llm_plan(self, request: str, memory_text: str) -> ProjectPlan | None:
        if not self.llm.available():
            return None

        system = (
            "You are OmniGameDev AI's planner. Return only valid JSON for a game project plan. "
            "Do not reveal hidden reasoning. Include engine, language, framework, game_type, "
            "modules, systems, assets, dependencies, commands, acceptance_tests, risks, and metadata."
        )
        user = {
            "request": request,
            "memory_context": memory_text[:6000],
            "schema_hint": {
                "engine": "Three.js",
                "language": "JavaScript",
                "framework": "Three.js",
                "modules": ["player controller", "enemy AI"],
            },
        }
        try:
            response = self.llm.chat(
                [
                    LLMMessage("system", system),
                    LLMMessage("user", json.dumps(user)),
                ],
                temperature=0.1,
            )
            raw = response.content.strip()
            match = re.search(r"\{.*\}", raw, flags=re.S)
            data = json.loads(match.group(0) if match else raw)
        except Exception:
            return None

        data.setdefault("request", request)
        data.setdefault("project_name", self._slugify(request))
        return ProjectPlan.from_dict(data)

    def _heuristic_plan(self, request: str, memory_text: str = "") -> ProjectPlan:
        lowered = request.lower()
        project_name = self._slugify(request)

        preset = preset_for_request(request)
        game_type = preset.name

        engine = "Three.js"
        language = "JavaScript"
        framework = "Three.js"

        if any(word in lowered for word in ["unity", "c#"]):
            engine, language, framework = "Unity", "C#", "Unity"
        elif any(word in lowered for word in ["unreal", "c++", "cpp"]):
            engine, language, framework = "Basic C++ Engine", "C++", "CMake"
        elif any(word in lowered for word in ["pygame", "python", "2d"]):
            engine, language, framework = "Pygame", "Python", "Pygame"
        elif any(word in lowered for word in ["babylon"]):
            engine, language, framework = "Babylon.js", "JavaScript", "Babylon.js"
        elif any(word in lowered for word in ["3d", "browser", "web", "three"]):
            engine, language, framework = "Three.js", "JavaScript", "Three.js"

        modules = [
            "project bootstrap",
            "game loop",
            "player controller",
            "input manager",
            "collision system",
            "HUD",
            "level loader",
        ]
        systems = [
            "rendering",
            "physics-lite movement",
            "state management",
            "runtime smoke test",
        ]
        assets = [
            "placeholder player material",
            "placeholder enemy material",
            "placeholder environment tiles",
            "asset manifest",
        ]
        modules.extend(preset.modules)
        systems.extend(preset.systems)
        assets.extend(preset.assets)

        keyword_modules = {
            "boss": ("boss encounter system", "boss arena markers"),
            "enemy": ("enemy AI", "enemy spawn points"),
            "dungeon": ("procedural dungeon map", "room and corridor tiles"),
            "rpg": ("inventory shell", "dialogue data"),
            "quest": ("quest tracker", "quest data"),
            "fps": ("camera controller", "weapon controller"),
            "platform": ("jump controller", "platform collision"),
            "multiplayer": ("networking placeholder", "replication boundaries"),
            "ui": ("menu system", "settings panel"),
            "save": ("save system", "persistent profile"),
        }
        for keyword, additions in keyword_modules.items():
            if self._contains_keyword(lowered, keyword):
                modules.append(additions[0])
                assets.append(additions[1])

        modules = self._dedupe(modules)
        systems = self._dedupe(systems)
        assets = self._dedupe(assets)

        dependencies = {
            "runtime": self._runtime_dependencies(language, framework),
            "development": self._development_dependencies(language, framework),
        }
        commands = self._commands_for(language, framework)
        acceptance_tests = [
            "Project files are generated inside projects/<project_name>.",
            "A smoke test command completes without crashing.",
            "Generated source contains a playable loop or engine-ready scripts.",
            "Project manifest records the plan, adapter, and generated files.",
        ]

        return ProjectPlan(
            request=request,
            project_name=project_name,
            engine=engine,
            language=language,
            framework=framework,
            game_type=game_type,
            modules=modules,
            systems=systems,
            assets=assets,
            dependencies=dependencies,
            commands=commands,
            acceptance_tests=acceptance_tests,
            risks=[
                "Full commercial engines such as Unity and Unreal require local editor installations.",
                "Generated browser projects need npm install before Vite dev serving.",
            ],
            metadata={
                "planner": "heuristic-v1",
                "preset": preset.name,
                "memory_used": bool(memory_text),
                "supports_self_heal": True,
            },
        )

    def _runtime_dependencies(self, language: str, framework: str) -> list[str]:
        if language == "JavaScript":
            return ["node >= 18", framework.lower()]
        if language == "Python":
            return ["python >= 3.10", "pygame >= 2.5"]
        if language == "C#":
            return ["Unity 2022 LTS or newer"]
        if language == "C++":
            return ["c++17 compiler", "cmake >= 3.16"]
        return []

    def _development_dependencies(self, language: str, framework: str) -> list[str]:
        if language == "JavaScript":
            return ["vite", "npm"]
        if language == "Python":
            return ["pip", "venv"]
        if language == "C#":
            return ["Unity Editor", "Visual Studio or Rider"]
        if language == "C++":
            return ["g++ or clang++", "cmake"]
        return []

    def _commands_for(self, language: str, framework: str) -> dict[str, str]:
        if language == "JavaScript":
            return {"install": "npm install", "run": "npm run dev", "smoke": "node --check src/main.js"}
        if language == "Python":
            return {"install": "pip install -r requirements.txt", "run": "python main.py", "smoke": "python main.py --smoke"}
        if language == "C#":
            return {"run": "Open the generated folder as a Unity project.", "smoke": "python -m compileall Assets"}
        if language == "C++":
            return {"build": "cmake -S . -B build && cmake --build build", "smoke": "python tools/smoke.py"}
        return {}

    def _slugify(self, request: str) -> str:
        words = re.findall(r"[a-zA-Z0-9]+", request.lower())
        stop = {"build", "make", "create", "a", "an", "the", "game", "with", "and", "for", "in"}
        useful = [word for word in words if word not in stop][:6]
        slug = "-".join(useful) or "omnigame-project"
        return slug[:64].strip("-")

    def _dedupe(self, values: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.lower()
            if key not in seen:
                result.append(value)
                seen.add(key)
        return result

    def _contains_keyword(self, lowered: str, keyword: str) -> bool:
        if " " in keyword:
            return keyword in lowered
        return re.search(rf"\b{re.escape(keyword)}\b", lowered) is not None
