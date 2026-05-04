from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[a-zA-Z0-9_+#.]+")


@dataclass(slots=True)
class MemoryRecord:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(
            {
                "id": self.id,
                "text": self.text,
                "metadata": self.metadata,
                "created_at": self.created_at,
            },
            ensure_ascii=True,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryRecord":
        return cls(
            id=str(data["id"]),
            text=str(data["text"]),
            metadata=dict(data.get("metadata") or {}),
            created_at=float(data.get("created_at") or time.time()),
        )


class MemoryStore:
    """Persistent retrieval memory with Chroma support and a zero-config local vector fallback."""

    def __init__(self, root: str | Path, backend: str | None = None, dimensions: int = 512) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.dimensions = dimensions
        self.records_path = self.root / "records.jsonl"
        self.backend_name = backend or os.getenv("OMNIGAMEDEV_MEMORY_BACKEND", "local")
        self._chroma_collection = None
        self._mongo_collection = None
        if self.backend_name == "chroma":
            self._init_chroma()
        elif self.backend_name == "mongo":
            self._init_mongo()

    def _init_chroma(self) -> None:
        try:
            import chromadb  # type: ignore

            client = chromadb.PersistentClient(path=str(self.root / "chroma"))
            self._chroma_collection = client.get_or_create_collection("omnigamedev_memory")
        except Exception:
            self._chroma_collection = None
            self.backend_name = "local"

    def _init_mongo(self) -> None:
        uri = os.getenv("MONGODB_URI", "").strip()
        if not uri:
            self.backend_name = "local"
            return
        try:
            from pymongo import MongoClient  # type: ignore

            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            db = client[os.getenv("MONGODB_DB", "omnigamedev").strip() or "omnigamedev"]
            self._mongo_collection = db["memory_records"]
            self._mongo_collection.create_index("created_at")
        except Exception:
            self._mongo_collection = None
            self.backend_name = "local"

    def count(self) -> int:
        if self._mongo_collection is not None:
            try:
                return int(self._mongo_collection.count_documents({}))
            except Exception:
                pass
        if not self.records_path.exists():
            return 0
        with self.records_path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())

    def add(self, text: str, metadata: dict[str, Any] | None = None, record_id: str | None = None) -> MemoryRecord:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Cannot store empty memory text.")

        record = MemoryRecord(
            id=record_id or self._record_id(clean_text, metadata or {}),
            text=clean_text,
            metadata=metadata or {},
        )
        existing = {item.id for item in self._read_records()}
        if record.id not in existing:
            with self.records_path.open("a", encoding="utf-8") as handle:
                handle.write(record.to_json() + "\n")

        if self._chroma_collection is not None:
            try:
                self._chroma_collection.add(
                    ids=[record.id],
                    documents=[record.text],
                    metadatas=[record.metadata],
                )
            except Exception:
                pass
        if self._mongo_collection is not None:
            try:
                payload = {
                    "_id": record.id,
                    "id": record.id,
                    "text": record.text,
                    "metadata": record.metadata,
                    "created_at": record.created_at,
                }
                self._mongo_collection.replace_one({"_id": record.id}, payload, upsert=True)
            except Exception:
                pass
        return record

    def search(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        if self._chroma_collection is not None:
            try:
                result = self._chroma_collection.query(query_texts=[query], n_results=limit)
                ids = result.get("ids", [[]])[0]
                docs = result.get("documents", [[]])[0]
                metas = result.get("metadatas", [[]])[0]
                return [
                    MemoryRecord(id=item_id, text=doc, metadata=dict(meta or {}))
                    for item_id, doc, meta in zip(ids, docs, metas)
                ]
            except Exception:
                pass

        query_vector = self._embed(query)
        scored: list[tuple[float, MemoryRecord]] = []
        for record in self._read_records():
            score = self._cosine(query_vector, self._embed(record.text))
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:limit]]

    def seed_from_markdown(self, markdown_path: str | Path, chunk_size: int = 2200) -> int:
        path = Path(markdown_path)
        if not path.exists():
            return 0
        text = path.read_text(encoding="utf-8")
        chunks = self._chunk_markdown(text, chunk_size)
        added = 0
        for index, chunk in enumerate(chunks):
            before = self.count()
            self.add(
                chunk,
                {
                    "source": str(path.name),
                    "kind": "training_context",
                    "chunk": index,
                },
                record_id=self._record_id(chunk, {"source": str(path.name), "chunk": index}),
            )
            if self.count() > before:
                added += 1
        return added

    def _read_records(self) -> list[MemoryRecord]:
        if self._mongo_collection is not None:
            try:
                return [
                    MemoryRecord.from_dict(item)
                    for item in self._mongo_collection.find({}, {"_id": 0, "id": 1, "text": 1, "metadata": 1, "created_at": 1})
                ]
            except Exception:
                pass
        if not self.records_path.exists():
            return []
        records: list[MemoryRecord] = []
        with self.records_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    records.append(MemoryRecord.from_dict(json.loads(line)))
                except json.JSONDecodeError:
                    continue
        return records

    def _chunk_markdown(self, text: str, chunk_size: int) -> list[str]:
        blocks = re.split(r"\n(?=##? )", text)
        chunks: list[str] = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if len(block) <= chunk_size:
                chunks.append(block)
                continue
            paragraphs = block.split("\n\n")
            current: list[str] = []
            current_length = 0
            for paragraph in paragraphs:
                if current_length + len(paragraph) > chunk_size and current:
                    chunks.append("\n\n".join(current))
                    current = []
                    current_length = 0
                current.append(paragraph)
                current_length += len(paragraph)
            if current:
                chunks.append("\n\n".join(current))
        return chunks

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % self.dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def _cosine(self, left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right))

    def _record_id(self, text: str, metadata: dict[str, Any]) -> str:
        digest = hashlib.sha1()
        digest.update(text.encode("utf-8"))
        digest.update(json.dumps(metadata, sort_keys=True, default=str).encode("utf-8"))
        return digest.hexdigest()
