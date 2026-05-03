from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class EnginePlugin:
    name: str
    language: str
    engine: str
    path: Path
    metadata: dict[str, Any]


class PluginManager:
    """Loads engine plugins from folders containing plugin.json and optional adapter.py."""

    def __init__(self, plugin_root: str | Path) -> None:
        self.plugin_root = Path(plugin_root)
        self.plugin_root.mkdir(parents=True, exist_ok=True)

    def discover(self) -> list[EnginePlugin]:
        plugins: list[EnginePlugin] = []
        for manifest_path in self.plugin_root.glob("*/plugin.json"):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            plugins.append(
                EnginePlugin(
                    name=data.get("name", manifest_path.parent.name),
                    language=data.get("language", "unknown"),
                    engine=data.get("engine", "unknown"),
                    path=manifest_path.parent,
                    metadata=data,
                )
            )
        return plugins

    def load_adapter_module(self, plugin: EnginePlugin) -> Any | None:
        adapter_path = plugin.path / "adapter.py"
        if not adapter_path.exists():
            return None
        spec = importlib.util.spec_from_file_location(f"omnigamedev_plugin_{plugin.name}", adapter_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
