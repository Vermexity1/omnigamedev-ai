from __future__ import annotations

import json
import re
from pathlib import Path

from executor.executor import RunResult
from memory import MemoryStore
from planner.schemas import ProjectPlan


class SelfHealingDebugger:
    def __init__(self, memory: MemoryStore | None = None) -> None:
        self.memory = memory

    def heal(self, project_path: str | Path, plan: ProjectPlan, result: RunResult) -> list[str]:
        root = Path(project_path)
        diagnostic = "\n".join([result.stderr, result.stdout, result.error_summary]).lower()
        fixes: list[str] = []

        if "no module named 'pygame'" in diagnostic or 'no module named "pygame"' in diagnostic:
            requirements = root / "requirements.txt"
            existing = requirements.read_text(encoding="utf-8") if requirements.exists() else ""
            if "pygame" not in existing.lower():
                requirements.write_text((existing.rstrip() + "\npygame>=2.5\n").lstrip(), encoding="utf-8")
                fixes.append("Added pygame dependency to requirements.txt.")

        if "cannot find module" in diagnostic and plan.language == "JavaScript":
            package_json = root / "package.json"
            if package_json.exists():
                data = json.loads(package_json.read_text(encoding="utf-8"))
                dependencies = data.setdefault("dependencies", {})
                if "three" not in dependencies and plan.framework.lower().startswith("three"):
                    dependencies["three"] = "^0.160.0"
                    package_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
                    fixes.append("Added missing Three.js dependency to package.json.")

        if "syntaxerror" in diagnostic:
            fixes.extend(self._remove_smart_quotes(root, plan))

        if "missing" in diagnostic and "plan.json" in diagnostic:
            meta_dir = root / ".omnigamedev"
            meta_dir.mkdir(parents=True, exist_ok=True)
            (meta_dir / "plan.json").write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")
            fixes.append("Restored missing .omnigamedev/plan.json.")

        if fixes and self.memory is not None:
            self.memory.add(
                f"Self-heal for {plan.language}/{plan.framework}: {'; '.join(fixes)}\nDiagnostic: {result.error_summary}",
                {"kind": "self_heal", "project": plan.project_name, "language": plan.language},
            )
        return fixes

    def _remove_smart_quotes(self, root: Path, plan: ProjectPlan) -> list[str]:
        extensions = {
            "Python": [".py"],
            "JavaScript": [".js", ".jsx", ".html", ".css"],
            "C#": [".cs"],
            "C++": [".cpp", ".hpp", ".h"],
        }.get(plan.language, [])
        if not extensions:
            return []
        replacements = {
            "\u201c": '"',
            "\u201d": '"',
            "\u2018": "'",
            "\u2019": "'",
        }
        changed: list[str] = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in extensions:
                continue
            text = path.read_text(encoding="utf-8")
            fixed = re.sub("|".join(map(re.escape, replacements)), lambda match: replacements[match.group(0)], text)
            if fixed != text:
                path.write_text(fixed, encoding="utf-8")
                changed.append(path.relative_to(root).as_posix())
        return [f"Normalized smart quotes in {', '.join(changed)}."] if changed else []
