from .interface import IWebSearch
from .impl.tavily import TavilyWebSearch
from .impl.duckduckgo import DuckduckgoWebSearch


__all__ = [
    "IWebSearch",
    "TavilyWebSearch",
    "DuckduckgoWebSearch",
]
