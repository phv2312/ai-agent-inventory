from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReferenceExporter:
    reference_id: str

    @property
    def prefix(self) -> str:
        return f"references/{self.reference_id}"

    def source_key(self, filename: str) -> str:
        return f"{self.prefix}/source/{Path(filename).name}"

    def rendered_page_key(self, page_index: int) -> str:
        if page_index < 1:
            raise ValueError("Page index must be at least 1")
        return f"{self.prefix}/rendered/page-{page_index:03d}.png"
