from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

from agent.core.storages.files.interface import IFileStorage


@contextmanager
def materialized_file(
    storage: IFileStorage,
    source_key: str,
    filename: str,
) -> Generator[Path, None, None]:
    content = storage.read_bytes(source_key)
    suffix = Path(filename).suffix or ".pdf"
    with NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(content)
        filepath = Path(temp_file.name)

    try:
        yield filepath
    finally:
        filepath.unlink(missing_ok=True)
