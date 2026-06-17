"""Market data ingestion services."""

from applications.stonitor.market.ingestion.fundamental import (
    FundamentalIngestionService,
)
from applications.stonitor.market.ingestion.news import NewsIngestionService
from applications.stonitor.market.ingestion.price import PriceIngestionService
from applications.stonitor.market.ingestion.tavily_client import TavilyNewsClient
from applications.stonitor.market.ingestion.vnstock_client import VnstockClient

__all__ = [
    "FundamentalIngestionService",
    "NewsIngestionService",
    "PriceIngestionService",
    "TavilyNewsClient",
    "VnstockClient",
]
