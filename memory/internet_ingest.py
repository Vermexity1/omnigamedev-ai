from __future__ import annotations

import re
import urllib.request
from html.parser import HTMLParser
from typing import Iterable

from memory.memory import MemoryStore


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        clean = re.sub(r"\s+", " ", data).strip()
        if clean:
            self.parts.append(clean)

    def text(self) -> str:
        return "\n".join(self.parts)


class InternetIngestor:
    """Fetches user-approved web pages and stores short context chunks in memory."""

    def __init__(self, memory: MemoryStore, user_agent: str = "OmniGameDevAI/0.1") -> None:
        self.memory = memory
        self.user_agent = user_agent

    def ingest_urls(self, urls: Iterable[str], max_chars: int = 12000, chunk_size: int = 2200) -> int:
        added = 0
        for url in urls:
            text = self._fetch_text(url, max_chars=max_chars)
            chunks = self._chunks(text, chunk_size=chunk_size)
            for index, chunk in enumerate(chunks):
                self.memory.add(
                    chunk,
                    {"kind": "internet_context", "source": url, "chunk": index},
                    record_id=self.memory._record_id(chunk, {"source": url, "chunk": index}),
                )
                added += 1
        return added

    def _fetch_text(self, url: str, max_chars: int) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(request, timeout=20) as response:
            content_type = response.headers.get("content-type", "")
            raw = response.read(max_chars * 4)
        decoded = raw.decode("utf-8", errors="replace")
        if "html" in content_type:
            parser = _TextExtractor()
            parser.feed(decoded)
            decoded = parser.text()
        return decoded[:max_chars]

    def _chunks(self, text: str, chunk_size: int) -> list[str]:
        paragraphs = [item.strip() for item in re.split(r"\n{2,}", text) if item.strip()]
        chunks: list[str] = []
        current: list[str] = []
        current_length = 0
        for paragraph in paragraphs:
            if current and current_length + len(paragraph) > chunk_size:
                chunks.append("\n\n".join(current))
                current = []
                current_length = 0
            current.append(paragraph)
            current_length += len(paragraph)
        if current:
            chunks.append("\n\n".join(current))
        return chunks or ([text.strip()] if text.strip() else [])
