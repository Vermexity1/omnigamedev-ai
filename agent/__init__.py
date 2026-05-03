from __future__ import annotations

__all__ = ["AgentRunResult", "OmniGameDevAgent"]


def __getattr__(name: str):
    if name in __all__:
        from .agent import AgentRunResult, OmniGameDevAgent

        return {"AgentRunResult": AgentRunResult, "OmniGameDevAgent": OmniGameDevAgent}[name]
    raise AttributeError(name)
