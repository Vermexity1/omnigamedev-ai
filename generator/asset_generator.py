from __future__ import annotations

import json
from planner.schemas import ProjectPlan


class AssetGenerator:
    def files_for_plan(self, plan: ProjectPlan) -> dict[str, str]:
        palette = {
            "player": "#5eead4",
            "enemy": "#f97316",
            "boss": "#ef4444",
            "floor": "#2f3a3d",
            "wall": "#7c6f64",
            "accent": "#facc15",
        }
        manifest = {
            "generated_by": "OmniGameDev AI",
            "project": plan.project_name,
            "assets": plan.assets,
            "palette": palette,
            "note": "These placeholders are intentionally simple and safe to replace with production art.",
        }
        return {
            "assets/manifest.json": json.dumps(manifest, indent=2, ensure_ascii=True),
            "assets/player.svg": self._svg_tile("PLAYER", palette["player"], "#0f172a"),
            "assets/enemy.svg": self._svg_tile("ENEMY", palette["enemy"], "#111827"),
            "assets/boss.svg": self._svg_tile("BOSS", palette["boss"], "#1f2937"),
            "assets/floor.svg": self._svg_pattern("FLOOR", palette["floor"], "#111827"),
            "assets/wall.svg": self._svg_pattern("WALL", palette["wall"], "#27221d"),
        }

    def _svg_tile(self, label: str, fill: str, background: str) -> str:
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <rect width="256" height="256" fill="{background}"/>
  <rect x="32" y="32" width="192" height="192" rx="24" fill="{fill}"/>
  <text x="128" y="142" font-family="Arial, sans-serif" font-size="32" text-anchor="middle" fill="#ffffff">{label}</text>
</svg>
"""

    def _svg_pattern(self, label: str, fill: str, stroke: str) -> str:
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <rect width="256" height="256" fill="{fill}"/>
  <path d="M0 64H256M0 128H256M0 192H256M64 0V256M128 0V256M192 0V256" stroke="{stroke}" stroke-width="8"/>
  <text x="128" y="142" font-family="Arial, sans-serif" font-size="28" text-anchor="middle" fill="#ffffff">{label}</text>
</svg>
"""
