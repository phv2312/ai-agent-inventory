"""Market domain repositories."""

from applications.stonitor.market.repositories.analysis_run import (
    AnalysisRunRepository,
)
from applications.stonitor.market.repositories.asset import AssetRepository
from applications.stonitor.market.repositories.fundamental_snapshot import (
    FundamentalSnapshotRepository,
)
from applications.stonitor.market.repositories.news_article import (
    NewsArticleRepository,
)
from applications.stonitor.market.repositories.price_snapshot import (
    PriceSnapshotRepository,
)
from applications.stonitor.market.repositories.protocols import (
    IAnalysisRunRepository,
    IAssetRepository,
    IFundamentalSnapshotRepository,
    INewsArticleRepository,
    IPriceSnapshotRepository,
    ISignalRepository,
)
from applications.stonitor.market.repositories.signal import SignalRepository

__all__ = [
    "AnalysisRunRepository",
    "AssetRepository",
    "FundamentalSnapshotRepository",
    "IAnalysisRunRepository",
    "IAssetRepository",
    "IFundamentalSnapshotRepository",
    "INewsArticleRepository",
    "IPriceSnapshotRepository",
    "ISignalRepository",
    "NewsArticleRepository",
    "PriceSnapshotRepository",
    "SignalRepository",
]
