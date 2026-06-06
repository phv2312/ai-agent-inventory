from collections.abc import Iterator
from typing import TypeVar

from pydantic import RootModel

T = TypeVar("T")


class ListModel(RootModel[list[T]]):
    def iter(self) -> Iterator[T]:
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)
