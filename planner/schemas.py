from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ProjectPlan:
    request: str
    project_name: str
    engine: str
    language: str
    framework: str
    game_type: str
    modules: list[str] = field(default_factory=list)
    systems: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    commands: dict[str, str] = field(default_factory=dict)
    acceptance_tests: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectPlan":
        fields = cls.__dataclass_fields__
        clean = {name: data.get(name) for name in fields if name in data}
        return cls(
            request=clean.get("request") or "",
            project_name=clean.get("project_name") or "omnigame-project",
            engine=clean.get("engine") or "Three.js",
            language=clean.get("language") or "JavaScript",
            framework=clean.get("framework") or "Three.js",
            game_type=clean.get("game_type") or "arcade",
            modules=list(clean.get("modules") or []),
            systems=list(clean.get("systems") or []),
            assets=list(clean.get("assets") or []),
            dependencies=dict(clean.get("dependencies") or {}),
            commands=dict(clean.get("commands") or {}),
            acceptance_tests=list(clean.get("acceptance_tests") or []),
            risks=list(clean.get("risks") or []),
            metadata=dict(clean.get("metadata") or {}),
        )
