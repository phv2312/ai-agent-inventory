from pathlib import Path
from shutil import rmtree


class ReferenceFileStorage:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def reference_dir(self, reference_id: str) -> Path:
        path = self.base_dir / reference_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_pdf(self, reference_id: str, filename: str, content: bytes) -> Path:
        safe_name = Path(filename).name
        dest = self.reference_dir(reference_id) / safe_name
        dest.write_bytes(content)
        return dest

    def resolve_path(self, file_path: str) -> Path:
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self.base_dir.parent / file_path

    def delete_reference(self, reference_id: str) -> None:
        """Remove all persisted files belonging to a reference."""
        reference_dir = self.base_dir / reference_id
        if reference_dir.exists():
            rmtree(reference_dir)
