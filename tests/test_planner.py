from __future__ import annotations

import unittest

from planner import TaskPlanner


class PlannerTests(unittest.TestCase):
    def test_three_dungeon_plan_uses_three_and_boss_modules(self) -> None:
        plan = TaskPlanner().create_plan("build a 3D dungeon game with bosses")

        self.assertEqual(plan.engine, "Three.js")
        self.assertEqual(plan.language, "JavaScript")
        self.assertEqual(plan.game_type, "dungeon crawler")
        self.assertIn("procedural dungeon map", plan.modules)
        self.assertIn("boss encounter system", plan.modules)

    def test_ui_keyword_does_not_match_build_substring(self) -> None:
        plan = TaskPlanner().create_plan("build a 3D dungeon game with bosses")

        self.assertNotIn("menu system", plan.modules)
        self.assertNotIn("settings panel", plan.assets)

    def test_explicit_pygame_selects_python(self) -> None:
        plan = TaskPlanner().create_plan("make a 2D pygame platformer")

        self.assertEqual(plan.engine, "Pygame")
        self.assertEqual(plan.language, "Python")
        self.assertEqual(plan.game_type, "platformer")


if __name__ == "__main__":
    unittest.main()
