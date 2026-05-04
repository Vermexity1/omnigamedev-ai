from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

from agent.llm import LLMProvider, create_llm_from_env
from agent.code_assistant import ProjectCodeAssistant
from executor import ExecutionEngine, RunResult, SelfHealingDebugger
from generator.code_generator import CodeGenerator, GenerationResult
from memory import InternetIngestor, MemoryStore
from planner import ProjectPlan, TaskPlanner


@dataclass(slots=True)
class AgentRunResult:
    plan: ProjectPlan
    generation: GenerationResult
    execution: RunResult | None
    fixes: list[str] = field(default_factory=list)
    reasoning_trace: list[str] = field(default_factory=list)
    memory_hits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_dict(),
            "generation": self.generation.to_dict(),
            "execution": self.execution.to_dict() if self.execution else None,
            "fixes": self.fixes,
            "reasoning_trace": self.reasoning_trace,
            "memory_hits": self.memory_hits,
        }


class OmniGameDevAgent:
    def __init__(
        self,
        root: str | Path,
        llm: LLMProvider | None = None,
        memory_backend: str | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        projects_root = os.getenv("OMNIGAMEDEV_PROJECTS_ROOT")
        memory_root = os.getenv("OMNIGAMEDEV_MEMORY_ROOT")
        self.projects_root = Path(projects_root).expanduser().resolve() if projects_root else self.root / "projects"
        self.llm = llm or create_llm_from_env()
        self.memory = MemoryStore(Path(memory_root).expanduser().resolve() if memory_root else self.root / ".memory", backend=memory_backend)
        self._seed_memory_once()
        self.planner = TaskPlanner(self.llm)
        self.generator = CodeGenerator(self.projects_root)
        self.executor = ExecutionEngine()
        self.debugger = SelfHealingDebugger(self.memory)
        self.code_assistant = ProjectCodeAssistant(self.llm, self.memory)

    def plan(self, request: str) -> ProjectPlan:
        hits = self.memory.search(request, limit=4)
        return self.planner.create_plan(request, [hit.text for hit in hits])

    def build(
        self,
        request: str,
        project_name: str | None = None,
        run_after: bool = True,
        max_retries: int = 2,
        install_dependencies: bool = False,
    ) -> AgentRunResult:
        trace = ["Accepted request and retrieved relevant memory."]
        memory_hits = self.memory.search(request, limit=5)
        trace.append(f"Retrieved {len(memory_hits)} memory item(s).")
        plan = self.planner.create_plan(request, [hit.text for hit in memory_hits])
        if project_name:
            plan.project_name = project_name
        trace.append(f"Selected {plan.engine} with {plan.language} for a {plan.game_type}.")

        generation = self.generator.generate_project(plan)
        trace.append(f"Generated {len(generation.files)} files using {generation.adapter}.")

        execution: RunResult | None = None
        fixes: list[str] = []
        if run_after:
            for attempt in range(max_retries + 1):
                execution = self.executor.run_project(
                    generation.project_path,
                    plan,
                    install_dependencies=install_dependencies and attempt == 0,
                )
                if execution.success:
                    trace.append(f"Smoke test passed on attempt {attempt + 1}.")
                    break
                trace.append(f"Smoke test failed on attempt {attempt + 1}: {execution.error_summary}")
                attempt_fixes = self.debugger.heal(generation.project_path, plan, execution)
                fixes.extend(attempt_fixes)
                if not attempt_fixes:
                    trace.append("No deterministic self-heal rule matched the failure.")
                    break
                trace.append(f"Applied fixes: {'; '.join(attempt_fixes)}")

        self.memory.add(
            self._project_memory(plan, generation, execution, fixes),
            {"kind": "project", "project": plan.project_name, "language": plan.language, "engine": plan.engine},
        )
        return AgentRunResult(
            plan=plan,
            generation=generation,
            execution=execution,
            fixes=fixes,
            reasoning_trace=trace,
            memory_hits=[hit.text[:500] for hit in memory_hits],
        )

    def _seed_memory_once(self) -> None:
        for training in (self.root / "training_context.md", self.root / "game_agent_training_catalog.md"):
            self.memory.seed_from_markdown(training)
        self._seed_urls_from_env()

    def _seed_urls_from_env(self) -> None:
        raw_urls = os.getenv("OMNIGAMEDEV_INGEST_URLS", "").strip()
        if not raw_urls:
            return
        urls = [url.strip() for url in raw_urls.split(",") if url.strip()]
        if urls:
            InternetIngestor(self.memory).ingest_urls(urls)

    def _project_memory(
        self,
        plan: ProjectPlan,
        generation: GenerationResult,
        execution: RunResult | None,
        fixes: list[str],
    ) -> str:
        status = "not run"
        if execution:
            status = "passed" if execution.success else f"failed: {execution.error_summary}"
        return (
            f"Project {plan.project_name}: {plan.game_type} using {plan.engine}/{plan.language}. "
            f"Modules: {', '.join(plan.modules)}. Files: {len(generation.files)}. "
            f"Smoke status: {status}. Fixes: {', '.join(fixes) if fixes else 'none'}."
        )
