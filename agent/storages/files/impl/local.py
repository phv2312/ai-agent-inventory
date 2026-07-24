from pathlib import Path, PurePosixPath
from shutil import rmtree

from agent.storages.files.exceptions import (
    StorageKeyError,
    StorageObjectNotFoundError,
)


class LocalFileStorage:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir.resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, key: str, content: bytes) -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return self._normalize_key(key)

    def read_bytes(self, key: str) -> bytes:
        path = self._path_for(key)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise StorageObjectNotFoundError(key) from exc

    def exists(self, key: str) -> bool:
        return self._path_for(key).is_file()

    def delete(self, key: str) -> None:
        path = self._path_for(key)
        if path.is_file():
            path.unlink()

    def delete_prefix(self, prefix: str) -> None:
        path = self._path_for(prefix)
        if path.is_dir():
            rmtree(path)
        elif path.is_file():
            path.unlink()

    def _path_for(self, key: str) -> Path:
        normalized = self._normalize_key(key)
        return self._base_dir.joinpath(*PurePosixPath(normalized).parts)

    @staticmethod
    def _normalize_key(key: str) -> str:
        if not key or key != key.strip() or "\\" in key:
            raise StorageKeyError("Storage key must be a non-empty POSIX path")

        path = PurePosixPath(key)
        if path.is_absolute() or any(part in {".", ".."} for part in path.parts):
            raise StorageKeyError("Storage key must be a normalized relative path")

        return path.as_posix()
