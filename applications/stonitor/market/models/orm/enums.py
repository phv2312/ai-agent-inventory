"""Shared ORM enumerations."""

import enum


class Exchange(str, enum.Enum):
    HOSE = "HOSE"
    HNX = "HNX"
    UPCOM = "UPCOM"


class SignalType(str, enum.Enum):
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"


class SignalCategory(str, enum.Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    NEWS = "news"


class RunType(str, enum.Enum):
    ANALYSIS = "analysis"
    PRICE_INGEST = "price_ingest"
    NEWS_INGEST = "news_ingest"
    SIGNAL_CALC = "signal_calc"
    ALERT_GEN = "alert_gen"


class RunStatus(str, enum.Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
