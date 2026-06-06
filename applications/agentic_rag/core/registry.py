"""Persistent registry of indexed files."""

import json
from pathlib import Path

from applications.agentic_rag.core.models import IndexedFile


class FileRegistry:
    """JSON-backed store of indexed file metadata."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("data/indexed_files.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._files: dict[str, IndexedFile] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for item in raw:
            record = IndexedFile.model_validate(item)
            self._files[record.fileid] = record

    def _save(self) -> None:
        payload = [f.model_dump(mode="json") for f in self._files.values()]
        self.path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    def list_files(self) -> list[IndexedFile]:
        return sorted(
            self._files.values(),
            key=lambda f: f.date_created,
            reverse=True,
        )

    def get(self, fileid: str) -> IndexedFile | None:
        return self._files.get(fileid)

    def add(self, record: IndexedFile) -> None:
        self._files[record.fileid] = record
        self._save()

    def remove(self, fileid: str) -> IndexedFile | None:
        removed = self._files.pop(fileid, None)
        if removed is not None:
            self._save()
        return removed

    def filter_by_name(self, query: str) -> list[IndexedFile]:
        if not query.strip():
            return self.list_files()
        needle = query.strip().lower()
        return [f for f in self.list_files() if needle in f.name.lower()]
