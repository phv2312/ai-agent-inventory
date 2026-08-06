from .interface import IExtractor
from .impl.pdf import PDFExtractor


__all__ = [
    "IExtractor",
    "PDFExtractor",
]
