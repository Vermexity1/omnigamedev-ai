from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory import MemoryStore


class MemoryTests(unittest.TestCase):
    def test_memory_persists_and_retrieves_related_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryStore(Path(temp_dir))
            memory.add("Three.js dungeon projects should include player movement and boss encounters.", {"kind": "pattern"})

            hits = memory.search("boss dungeon movement", limit=1)

            self.assertEqual(len(hits), 1)
            self.assertIn("boss", hits[0].text)

    def test_markdown_seeding_chunks_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "training.md"
            path.write_text("# Heading\n\nThree.js smoke tests need node syntax checks.", encoding="utf-8")
            memory = MemoryStore(Path(temp_dir) / "memory")

            added = memory.seed_from_markdown(path)

            self.assertEqual(added, 1)
            self.assertEqual(memory.count(), 1)


if __name__ == "__main__":
    unittest.main()
