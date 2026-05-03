from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class LLMMessage:
    role: str
    content: str


@dataclass(slots=True)
class LLMResponse:
    content: str
    model: str
    provider: str


class LLMProvider(Protocol):
    name: str

    def available(self) -> bool:
        ...

    def chat(self, messages: list[LLMMessage], temperature: float = 0.2) -> LLMResponse:
        ...


class NullLLMProvider:
    name = "local-heuristic"

    def available(self) -> bool:
        return False

    def chat(self, messages: list[LLMMessage], temperature: float = 0.2) -> LLMResponse:
        return LLMResponse(
            content="",
            model="none",
            provider=self.name,
        )


class OpenAICompatibleProvider:
    """Small OpenAI-compatible chat client without a hard SDK dependency."""

    name = "openai-compatible"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        self.base_url = (base_url or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.getenv("OMNIGAMEDEV_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[LLMMessage], temperature: float = 0.2) -> LLMResponse:
        if not self.available():
            raise RuntimeError("No LLM API key configured. Set OPENAI_API_KEY or LLM_API_KEY.")

        payload = {
            "model": self.model,
            "messages": [message.__dict__ for message in messages],
            "temperature": temperature,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed: HTTP {exc.code}: {detail}") from exc

        content = body["choices"][0]["message"]["content"]
        return LLMResponse(content=content, model=self.model, provider=self.name)


def create_llm_from_env() -> LLMProvider:
    provider = OpenAICompatibleProvider()
    if provider.available():
        return provider
    return NullLLMProvider()
