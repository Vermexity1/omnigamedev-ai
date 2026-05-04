from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storage.mongo_project_store import MongoProjectStore


class FakeCollection:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def replace_one(self, filter_doc, replacement, upsert=False):
        self.rows[str(filter_doc["_id"])] = dict(replacement)

    def delete_many(self, filter_doc):
        project = filter_doc.get("project")
        self.rows = {key: value for key, value in self.rows.items() if value.get("project") != project}

    def insert_many(self, documents, ordered=False):
        for document in documents:
            self.rows[str(document["_id"])] = dict(document)

    def find_one(self, filter_doc):
        return self.rows.get(str(filter_doc["_id"]))

    def find(self, filter_doc=None, projection=None):
        filter_doc = filter_doc or {}
        rows = list(self.rows.values())
        if "project" in filter_doc:
            rows = [row for row in rows if row.get("project") == filter_doc["project"]]
        return rows

    def create_index(self, *args, **kwargs):
        return None


class MongoProjectStoreTests(unittest.TestCase):
    def make_store(self) -> MongoProjectStore:
        store = object.__new__(MongoProjectStore)
        store.uri = "mongodb://example"
        store.db_name = "omnigamedev"
        store.projects = FakeCollection()
        store.files = FakeCollection()
        return store

    def test_project_snapshots_restore_text_and_binary_files(self) -> None:
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as restore_dir:
            project = Path(source_dir) / "sample-game"
            (project / ".omnigamedev").mkdir(parents=True)
            (project / ".omnigamedev" / "plan.json").write_text(json.dumps({"engine": "Three.js"}), encoding="utf-8")
            (project / "README.md").write_text("# Sample", encoding="utf-8")
            (project / "assets").mkdir()
            (project / "assets" / "sprite.bin").write_bytes(b"\x00\x01\x02")
            (project / "node_modules").mkdir()
            (project / "node_modules" / "skip.js").write_text("ignored", encoding="utf-8")

            store = self.make_store()
            store.save_project(project)

            self.assertTrue(store.restore_project("sample-game", restore_dir))
            restored = Path(restore_dir) / "sample-game"
            self.assertEqual((restored / "README.md").read_text(encoding="utf-8"), "# Sample")
            self.assertEqual((restored / "assets" / "sprite.bin").read_bytes(), b"\x00\x01\x02")
            self.assertFalse((restored / "node_modules" / "skip.js").exists())


if __name__ == "__main__":
    unittest.main()
