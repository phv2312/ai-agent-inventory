from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PIL import Image


@dataclass
class FileStorage:
    imagedir: Path

    def __post_init__(self) -> None:
        self.imagedir.mkdir(parents=True, exist_ok=True)

    def gen_path(self, reldir: str, name: str | None = None, ext: str = "png") -> str:
        return str(Path(reldir) / f"{name or {str(uuid4())}}.{ext}")

    def save_image(self, image: Image, relpath: str) -> Path:
        imagepath = self.imagedir / relpath
        imagepath.parent.mkdir(parents=True, exist_ok=True)

        if imagepath.exists():
            imagepath.unlink()

        image.save(imagepath)
        return imagepath

    def get_localpath(self, remotepath: str) -> Path:
        return self.imagedir / remotepath
