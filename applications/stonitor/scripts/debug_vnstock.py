"""Debug vnstock API calls with .env loaded.

Run from repo root:

    uv run python -m applications.stonitor.scripts.debug_vnstock
    uv run python -m applications.stonitor.scripts.debug_vnstock --call list
    uv run python -m applications.stonitor.scripts.debug_vnstock --call ohlcv --ticker VNM
    uv run python -m applications.stonitor.scripts.debug_vnstock --call all --ticker FPT
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
import traceback
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from vnstock import Fundamental, Market, Reference, register_user

from applications.stonitor.config import StonitorSettings
from applications.stonitor.deps import StonitorDeps
from applications.stonitor.market.ingestion import VnstockClient
from applications.stonitor.market.models.dto import EvidenceRegistry

_CALLS = ("register", "list", "ohlcv", "news", "fundamentals", "all")


def _find_env_file() -> Path:
    for parent in (Path.cwd(), *Path.cwd().parents):
        env_file = parent / ".env"
        if env_file.is_file():
            return env_file
        if (parent / "pyproject.toml").is_file():
            return env_file
    return Path(".env")


def _load_settings() -> StonitorSettings:
    env_file = _find_env_file()
    load_dotenv(env_file, override=False)
    settings = StonitorSettings()
    print(f"Loaded env: {env_file.resolve()}")
    print(f"VNSTOCK_API_KEY set: {bool(settings.VNSTOCK_API_KEY.strip())}")
    if settings.VNSTOCK_API_KEY.strip():
        masked = f"{settings.VNSTOCK_API_KEY[:4]}***"
        print(f"VNSTOCK_API_KEY prefix: {masked}")
    return settings


def _print_df(label: str, df: pd.DataFrame | None) -> None:
    print(f"\n=== {label} ===")
    if df is None:
        print("result: None")
        return
    print(f"shape: {df.shape}")
    print(f"columns: {list(df.columns)}")
    if df.empty:
        print("rows: EMPTY")
        return
    print("head:")
    print(df.head(3).to_string())


def _run_call(
    name: str,
    fn,
) -> bool:
    print(f"\n--- {name} ---")
    started = time.perf_counter()
    try:
        result = fn()
        elapsed = time.perf_counter() - started
        print(f"OK in {elapsed:.2f}s")
        if isinstance(result, pd.DataFrame):
            _print_df(name, result)
        elif isinstance(result, dict):
            print(result)
        else:
            print(result)
        return True
    except Exception as exc:
        elapsed = time.perf_counter() - started
        print(f"FAILED in {elapsed:.2f}s: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Call vnstock endpoints used by Stonitor for debugging.",
    )
    parser.add_argument(
        "--call",
        choices=_CALLS,
        default="all",
        help="Which API call to run (default: all)",
    )
    parser.add_argument(
        "--ticker",
        default="VNM",
        help="Ticker for ohlcv/news/fundamentals (default: VNM)",
    )
    args = parser.parse_args(argv)
    settings = _load_settings()
    api_key = settings.VNSTOCK_API_KEY.strip()
    if not api_key:
        print("ERROR: VNSTOCK_API_KEY is empty. Set it in .env first.")
        return 1

    ticker = args.ticker.strip().upper()
    end = date.today()
    start = end - timedelta(days=90)
    calls = (
        _CALLS[:-1]
        if args.call == "all"
        else (args.call,)
    )

    ok = True
    registered = False

    if "register" in calls:
        ok &= _run_call(
            "register_user",
            lambda: register_user(api_key=api_key) or "registered",
        )
        registered = True

    if not registered and any(c in calls for c in ("list", "ohlcv", "news", "fundamentals")):
        ok &= _run_call(
            "register_user",
            lambda: register_user(api_key=api_key) or "registered",
        )

    if "list" in calls:
        ok &= _run_call(
            "Reference().equity.list()",
            lambda: Reference().equity.list(),
        )

    if "ohlcv" in calls:
        ok &= _run_call(
            f'Market().equity("{ticker}").ohlcv()',
            lambda: Market().equity(ticker).ohlcv(
                start=start.isoformat(),
                end=end.isoformat(),
            ),
        )

    if "news" in calls:
        ok &= _run_call(
            f'Reference().company("{ticker}").news()',
            lambda: Reference().company(ticker).news(),
        )

    if "fundamentals" in calls:
        ok &= _run_call(
            f'Fundamental().equity("{ticker}").ratios(period="year")',
            lambda: Fundamental().equity(ticker).ratios(period="year"),
        )

    print("\nDone.")
    return 0 if ok else 2


async def search_news_tavily() -> None:
    from tavily import AsyncTavilyClient
    client = AsyncTavilyClient("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")
    response = await client.search(
        query="tin tức mới nhất về cổ phiếu KBC, tổng hợp",
        include_answer="advanced",
        search_depth="advanced",
        time_range="week",
        chunks_per_source=5,
        country="vietnam"
    )
    
    answer = response["answer"]
    print(f"Answer: {answer}")
    for new in response["results"]:
        url = new["url"]
        content = new["content"]
        title = new["title"]
        score = new["score"]
        print(f"URL: {url}")
        print(f"Content: {content}")
        print(f"Title: {title}")
        print(f"Score: {score}")
        print("-" * 100)



async def custom() -> None:
    settings = _load_settings()
    client = VnstockClient(settings)
    news = await client.fetch_news("KBC")

    for idx, row in news.iterrows():
        print(row)

    print(news.head(5))


    # OHLCV
    # df = await client.fetch_ohlcv(ticker="VNM", start=date.today() - timedelta(days=10), end=date.today())
    # print(df)

    # News
    # df = await client.fetch_news(ticker="KBC")
    # print(df)

    # fundamentals
    # fundamentals = await client.fetch_fundamentals(ticker="KBC")
    # print(fundamentals)

    # deps = StonitorDeps(settings)
    # report = await deps.analysis.analyze("VNM")

    # registry = EvidenceRegistry.model_validate_json('{"records":{"TECH-001":{"id":"TECH-001","category":"technical","label":"trend: bearish","value":"sma_20=30.525, sma_50=32.35, close=30.7, bars_used=79","source":null,"captured_at":"2026-06-13T13:02:25.625335Z"},"TECH-002":{"id":"TECH-002","category":"technical","label":"volatility: normal","value":"rolling_std=0.019540319562046334, baseline_std=0.02456619279354721, window=20","source":null,"captured_at":"2026-06-13T13:02:25.625335Z"},"TECH-003":{"id":"TECH-003","category":"technical","label":"momentum: negative","value":"rsi=44.6280991735537, period=14","source":null,"captured_at":"2026-06-13T13:02:25.625335Z"},"FUND-001":{"id":"FUND-001","category":"fundamental","label":"fundamental: strong_growth","value":"metric=revenue_growth, value=1.4091, source=vnstock/KBS, ingested_at=2026-06-13T13:02:25.614660","source":"vnstock/KBS","captured_at":"2026-06-13T13:02:25.629594Z"},"FUND-002":{"id":"FUND-002","category":"fundamental","label":"fundamental: strong","value":"metric=eps, value=2478.54, source=vnstock/KBS, ingested_at=2026-06-13T13:02:25.614660","source":"vnstock/KBS","captured_at":"2026-06-13T13:02:25.629594Z"},"FUND-003":{"id":"FUND-003","category":"fundamental","label":"fundamental: high","value":"metric=net_margin, value=0.33020000000000005, source=vnstock/KBS, ingested_at=2026-06-13T13:02:25.614660","source":"vnstock/KBS","captured_at":"2026-06-13T13:02:25.629594Z"},"FUND-004":{"id":"FUND-004","category":"fundamental","label":"fundamental: moderate","value":"metric=pe_ratio, value=14.26, source=vnstock/KBS, ingested_at=2026-06-13T13:02:25.614660","source":"vnstock/KBS","captured_at":"2026-06-13T13:02:25.629594Z"},"FUND-005":{"id":"FUND-005","category":"fundamental","label":"Tăng trưởng doanh thu","value":"1.409","source":"vnstock/KBS","captured_at":"2026-06-13T13:02:25.614660"},"FUND-006":{"id":"FUND-006","category":"fundamental","label":"EPS","value":"2479","source":"vnstock/KBS","captured_at":"2026-06-13T13:02:25.614660"},"FUND-007":{"id":"FUND-007","category":"fundamental","label":"Biên lợi nhuận ròng","value":"0.3302","source":"vnstock/KBS","captured_at":"2026-06-13T13:02:25.614660"},"FUND-008":{"id":"FUND-008","category":"fundamental","label":"Hệ số P/E","value":"14.26","source":"vnstock/KBS","captured_at":"2026-06-13T13:02:25.614660"}}}')
    # summary = await deps.report_summary_program.generate(registry)

    # print(summary)

    # report = await deps.analysis.analyze("KBC")
    # print(report)





if __name__ == "__main__":
    asyncio.run(search_news_tavily())

    # sys.exit(main())
