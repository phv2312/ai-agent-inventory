import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Annotated, Final, Sequence

from agents import Tool, function_tool
from pydantic import BaseModel, Field


TABLE_OF_CONTENT_FILENAME: Final[str] = "table-of-content.md"

SECTION_DIRECTORY_NAME: Final[str] = "sections"


class SummaryReadRequest(BaseModel):
    fileid: str = Field(min_length=1, description="Allowed source-summary file ID")
    relative_path: str = Field(
        min_length=1,
        description="Markdown artifact path below that source summary",
    )


@dataclass
class SummaryPaths:
    root: Path

    @property
    def table_of_content_path(self) -> Path:
        return self.root / TABLE_OF_CONTENT_FILENAME

    @property
    def section_root(self) -> Path:
        return self.root / SECTION_DIRECTORY_NAME

    def resolve_artifact_path(self, relative_path: str) -> Path:
        target_path = (self.root / relative_path).resolve()
        root_path = self.root.resolve()
        if target_path == root_path or root_path not in target_path.parents:
            raise ValueError(f"Path escapes summary directory: {relative_path}")
        return target_path

    def list_rel_paths(self) -> list[Path]:
        return [
            path.relative_to(self.root)
            for path in sorted(self.root.rglob("*.md"))
            if path.is_file()
        ]


class ArtifactRepository:
    def __init__(self, paths: SummaryPaths) -> None:
        self.paths = paths

    @staticmethod
    def _read_file(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError as error:
            raise ValueError(f"Unable to read {path}: {error}") from error

    def read(self, relative_path: str) -> str:
        artifact_path = self.paths.resolve_artifact_path(relative_path)
        if not artifact_path.is_file():
            raise ValueError(f"Artifact does not exist: {relative_path}")
        return self._read_file(artifact_path)

    def _list(self) -> list[Path]:
        return self.paths.list_rel_paths()

    def write(
        self,
        relative_path: str,
        content: str,
    ) -> Path:
        artifact_path = self.paths.resolve_artifact_path(relative_path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(content, encoding="utf-8")
        return artifact_path

    def replace(
        self,
        relative_path: str,
        old_text: str,
        new_text: str,
    ) -> bool:
        content = self.read(relative_path)
        if old_text not in content:
            return False
        self.write(
            relative_path,
            content.replace(old_text, new_text, 1),
        )
        return True

    def append(
        self,
        relative_path: str,
        content: str,
    ) -> Path:
        artifact_path = self.paths.resolve_artifact_path(relative_path)
        existing_content = ""
        if artifact_path.is_file():
            existing_content = self._read_file(artifact_path)
        separator = ""
        if existing_content and not existing_content.endswith("\n"):
            separator = "\n"
        return self.write(
            relative_path,
            f"{existing_content}{separator}{content}",
        )

    def as_relative(self, abs_path: Path) -> Path:
        return abs_path.relative_to(self.paths.root)

    def for_fileid(self, fileid: str) -> "ArtifactRepository":
        """Return the repository rooted at one direct child file-id directory."""
        file_root = (self.paths.root / fileid).resolve()
        root = self.paths.root.resolve()
        if file_root.parent != root:
            raise ValueError(f"Invalid file ID: {fileid}")
        return ArtifactRepository(SummaryPaths(file_root))


def build_summary_read_tools(
    repo: ArtifactRepository,
    file_ids: Sequence[str],
) -> list[Tool]:
    """Build read-only tools limited to summaries for the supplied file IDs."""
    allowed_file_ids = frozenset(file_ids)

    def _repository_for(fileid: str) -> ArtifactRepository:
        if fileid not in allowed_file_ids:
            raise ValueError(f"File ID is not available: {fileid}")
        return repo.for_fileid(fileid)

    @function_tool
    async def list_many(
        fileids: Annotated[
            list[str],
            "Allowed source-summary file IDs to list concurrently.",
        ],
    ) -> str:
        """List artifacts for multiple allowed source summaries concurrently."""

        def _list_one(fileid: str) -> dict[str, object]:
            try:
                return {
                    "fileid": fileid,
                    "files": list(map(str, _repository_for(fileid)._list())),
                }
            except Exception as error:
                return {"fileid": fileid, "error": str(error)}

        results = await asyncio.gather(
            *(asyncio.to_thread(_list_one, fileid) for fileid in fileids),
        )
        return json.dumps(results, ensure_ascii=False)

    @function_tool
    async def read_many(
        requests: Annotated[
            list[SummaryReadRequest],
            "Artifacts to read concurrently from allowed source summaries.",
        ],
    ) -> str:
        """Read artifacts from multiple allowed source summaries concurrently."""

        def _read_one(request: SummaryReadRequest) -> dict[str, str]:
            try:
                return {
                    "fileid": request.fileid,
                    "relative_path": request.relative_path,
                    "content": _repository_for(request.fileid).read(
                        request.relative_path,
                    ),
                }
            except Exception as error:
                return {
                    "fileid": request.fileid,
                    "relative_path": request.relative_path,
                    "error": str(error),
                }

        results = await asyncio.gather(
            *(asyncio.to_thread(_read_one, request) for request in requests),
        )
        return json.dumps(results, ensure_ascii=False)

    return [list_many, read_many]


def build_summary_tools(repo: ArtifactRepository) -> list[Tool]:
    """Build the authoring tool surface for incrementally creating summaries."""

    @function_tool
    async def read(
        relative_path: Annotated[str, "Artifact path under this source summary."],
    ) -> str:
        """Read an existing markdown artifact for the current source."""
        try:
            return repo.read(relative_path)
        except Exception as error:
            return f"Unable to read {relative_path}: {error}"

    @function_tool
    async def _list() -> str:
        """List markdown artifacts for the current source summary."""
        files = list(map(str, repo._list()))
        return "\n".join(files) if files else "No files written yet."

    @function_tool
    async def write(
        relative_path: Annotated[str, "Artifact path under this source summary."],
        content: Annotated[str, "Markdown content to write."],
    ) -> str:
        """Write a markdown artifact for the current source summary."""
        try:
            artifact_path = repo.write(relative_path, content)
        except Exception as error:
            return f"Unable to write {relative_path}: {error}"
        return f"Wrote {repo.as_relative(artifact_path)}"

    @function_tool
    async def replace(
        relative_path: Annotated[str, "Artifact path under this source summary."],
        old_text: Annotated[str, "Exact text to replace."],
        new_text: Annotated[str, "Replacement text."],
    ) -> str:
        """Replace one exact text occurrence in a source markdown artifact."""
        try:
            replaced = repo.replace(relative_path, old_text, new_text)
        except Exception as error:
            return f"Unable to update {relative_path}: {error}"
        return "Updated artifact." if replaced else "Text to replace was not found."

    @function_tool
    async def append(
        relative_path: Annotated[str, "Artifact path under this source summary."],
        content: Annotated[str, "Markdown content to append."],
    ) -> str:
        """Append markdown content to an artifact for the current source."""
        try:
            artifact_path = repo.append(relative_path, content)
        except Exception as error:
            return f"Unable to append {relative_path}: {error}"
        return f"Appended to {repo.as_relative(artifact_path)}"

    return [read, _list, write, replace, append]
