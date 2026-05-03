from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from language_adapters import CSharpAdapter, CppAdapter, JavaScriptAdapter, LanguageAdapter, PythonAdapter
from planner.schemas import ProjectPlan


@dataclass(slots=True)
class CommandResult:
    label: str
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float


@dataclass(slots=True)
class RunResult:
    success: bool
    project_path: str
    command_results: list[CommandResult] = field(default_factory=list)
    error_summary: str = ""
    performance: dict[str, float] = field(default_factory=dict)

    @property
    def stdout(self) -> str:
        return "\n".join(result.stdout for result in self.command_results if result.stdout)

    @property
    def stderr(self) -> str:
        return "\n".join(result.stderr for result in self.command_results if result.stderr)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "project_path": self.project_path,
            "error_summary": self.error_summary,
            "performance": self.performance,
            "commands": [
                {
                    "label": result.label,
                    "args": result.args,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration_seconds": result.duration_seconds,
                }
                for result in self.command_results
            ],
        }


class ExecutionEngine:
    def __init__(self, adapters: list[LanguageAdapter] | None = None) -> None:
        self.adapters = adapters or [JavaScriptAdapter(), PythonAdapter(), CSharpAdapter(), CppAdapter()]

    def run_project(
        self,
        project_path: str | Path,
        plan: ProjectPlan,
        install_dependencies: bool = False,
    ) -> RunResult:
        root = Path(project_path).resolve()
        adapter = self._adapter_for(plan)
        commands = adapter.smoke_commands(root, install_dependencies=install_dependencies)
        command_results: list[CommandResult] = []
        started = time.perf_counter()

        for command in commands:
            command_started = time.perf_counter()
            env = os.environ.copy()
            env.update(command.env)
            try:
                completed = subprocess.run(
                    command.args,
                    cwd=str(command.cwd),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=command.timeout,
                )
                duration = time.perf_counter() - command_started
                result = CommandResult(
                    label=command.label,
                    args=command.args,
                    returncode=completed.returncode,
                    stdout=completed.stdout.strip(),
                    stderr=completed.stderr.strip(),
                    duration_seconds=duration,
                )
            except FileNotFoundError as exc:
                duration = time.perf_counter() - command_started
                result = CommandResult(
                    label=command.label,
                    args=command.args,
                    returncode=127,
                    stdout="",
                    stderr=str(exc),
                    duration_seconds=duration,
                )
            except subprocess.TimeoutExpired as exc:
                duration = time.perf_counter() - command_started
                result = CommandResult(
                    label=command.label,
                    args=command.args,
                    returncode=124,
                    stdout=(exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
                    stderr=(exc.stderr or "").strip() if isinstance(exc.stderr, str) else "Command timed out.",
                    duration_seconds=duration,
                )
            command_results.append(result)
            if result.returncode != 0:
                return RunResult(
                    success=False,
                    project_path=str(root),
                    command_results=command_results,
                    error_summary=self._summarize_error(result),
                    performance={"total_seconds": time.perf_counter() - started},
                )

        return RunResult(
            success=True,
            project_path=str(root),
            command_results=command_results,
            performance={"total_seconds": time.perf_counter() - started},
        )

    def _adapter_for(self, plan: ProjectPlan) -> LanguageAdapter:
        for adapter in self.adapters:
            if adapter.supports(plan):
                return adapter
        return JavaScriptAdapter()

    def _summarize_error(self, result: CommandResult) -> str:
        text = result.stderr or result.stdout or "Command failed without output."
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines[-1] if lines else text.strip()
