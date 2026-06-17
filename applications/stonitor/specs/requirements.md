# Market Observability Platform

## Overview

Market Observability Platform is an explainable financial intelligence system inspired by modern FinOps and observability platforms.

Instead of acting as a trading bot or stock recommendation engine, the platform focuses on:

* Collecting market telemetry
* Computing deterministic signals
* Detecting anomalies
* Generating alerts
* Producing explainable AI-assisted reports
* Providing evidence for every conclusion

The goal is to demonstrate:

* Product engineering skills
* Agent-driven development workflow
* Background job design
* Idempotent data pipelines
* Observability mindset
* Explainable AI systems

---

# Product Vision

Financial analysis tools often force users to switch between:

* Price charts
* Financial statements
* News sources
* Analyst reports

This platform consolidates those sources into a single explainable workflow.

Users can:

* Analyze a stock
* Monitor a watchlist
* Receive alerts
* Inspect evidence behind every signal

The system never provides investment advice.

The system only summarizes evidence that has already been computed.

---

# Non-Goals

The platform is NOT:

* A trading bot
* A portfolio optimizer
* A high-frequency trading platform
* A buy/sell recommendation system
* A price prediction engine

---

# Core Principles

## Explainability First

Every conclusion must be traceable to:

* Raw market data
* News articles
* Computed indicators

No black-box recommendations.

---

## Deterministic Signals

Signal generation must be deterministic.

Examples:

* SMA crossovers
* RSI thresholds
* MACD signals
* Volatility changes
* Sentiment shifts

---

## Observability

Every background process must be observable.

Users and developers should be able to answer:

* What happened?
* Why did it happen?
* When did it happen?
* What evidence supports it?

---

## AI as Summarizer

LLMs are only allowed to:

* Summarize
* Explain

LLMs are NOT allowed to:

* Predict future prices
* Recommend investments
* Invent facts
* Fill missing data

---

# Architecture

```text
                    Scheduler
                         |
                         v

+----------------+   Raw Store   +----------------+
| Price Ingestor | ----------->  | News Ingestor  |
+----------------+               +----------------+

                         |
                         v

                 +----------------+
                 | Signal Engine  |
                 +----------------+

                  /      |      \
                 /       |       \

         Technical  Fundamental  News

                 \       |       /
                  \      |      /

                 +----------------+
                 | Alert Engine   |
                 +----------------+

                         |
                         v

                 +----------------+
                 | Report Engine  |
                 +----------------+

                         |
                         v

                     Gradio UI
```

---

# Technology Stack

## Backend

* Python 3.12+
* PostgreSQL
* SQLAlchemy
* Alembic

## Data Collection

* yfinance
* RSS feeds
* Optional: NewsAPI

## AI

* OpenAI
* Anthropic
* Azure OpenAI

## UI

* Gradio

## Scheduling

* APScheduler

## Observability

* Prometheus metrics
* Structured logging

---

# Domain Model

## Asset

```python
class Asset:
    ticker: str
    exchange: str
    sector: str
```

---

## Price Snapshot

```python
class PriceSnapshot:
    asset_id
    timestamp

    open
    high
    low
    close

    volume
```

---

## News Article

```python
class NewsArticle:
    asset_id

    title
    source

    url

    sentiment_score

    published_at
```

---

## Signal

```python
class Signal:
    asset_id

    signal_type

    score

    confidence

    created_at
```

---

## Alert

```python
class Alert:
    asset_id

    alert_type

    severity

    status

    created_at
```

---

## Analysis Run

```python
class AnalysisRun:
    id

    ticker

    status

    started_at

    completed_at

    error_message
```

---

# Background Jobs

## Price Ingestion Job

Purpose:

Collect historical market data.

Frequency:

Every 4 hours.

Responsibilities:

* Fetch OHLCV data
* Store snapshots
* Prevent duplicates

---

## News Ingestion Job

Purpose:

Collect news related to tracked assets.

Frequency:

Every hour.

Responsibilities:

* Fetch articles
* Extract metadata
* Calculate sentiment

---

## Signal Calculation Job

Purpose:

Generate technical and market signals.

Triggered after data ingestion.

---

## Alert Generation Job

Purpose:

Detect unusual events.

Triggered after signal calculation.

---

# Idempotency Requirements

Every job must be safely retryable.

Running the same job twice must not create duplicate records.

Required uniqueness constraints:

```sql
(source, ticker, timestamp)
```

Examples:

* Same article fetched twice
* Same market data fetched twice
* Scheduler retry after failure

All should be handled safely.

---

# Signal Engine

## Technical Signals

### Trend

Based on:

* SMA20
* SMA50

Outputs:

* Bullish
* Neutral
* Bearish

---

### Momentum

Based on:

* RSI
* MACD

Outputs:

* Positive
* Neutral
* Negative

---

### Volatility

Based on:

Rolling standard deviation.

Outputs:

* Low
* Normal
* High

---

# Fundamental Signals

Initial version may use mocked or manually loaded data.

Metrics:

* Revenue Growth
* EPS
* Net Margin
* PE Ratio

Store historical snapshots when available.

---

# News Signals

Every article receives:

```python
sentiment_score
```

Range:

```text
-1.0 -> +1.0
```

Aggregate into:

```python
daily_sentiment
```

for anomaly detection.

---

# Anomaly Detection

## Volume Spike

```python
zscore(volume) > 3
```

---

## Volatility Spike

```python
zscore(volatility) > 3
```

---

## Sentiment Spike

```python
abs(zscore(sentiment)) > 3
```

---

## Trend Reversal

Generated when:

```text
SMA20 crosses SMA50
```

---

# Alert Engine

Supported alerts:

* volume_spike
* volatility_spike
* sentiment_spike
* trend_reversal

Severity:

* LOW
* MEDIUM
* HIGH

---

# Alert Deduplication

The same alert should not be generated repeatedly.

Dedup rule:

```text
same ticker
same alert type
within 24 hours
```

Result:

Only one active alert.

---

# Report Engine

Input:

```python
ticker
```

Output:

```json
{
  "technical": {},
  "fundamental": {},
  "news": {},
  "summary": "",
  "evidence": []
}
```

---

# Evidence Requirements

Every signal must include evidence.

Example:

## Bullish Trend

Evidence:

| Metric | Value |
| ------ | ----- |
| SMA20  | 142.4 |
| SMA50  | 137.1 |
| RSI    | 68    |

---

## Positive News Sentiment

Evidence:

| Article                    | Score |
| -------------------------- | ----- |
| Earnings Beat Expectations | 0.84  |

---

No conclusion should appear without evidence.

---

# LLM Constraints

Prompt requirements:

```text
You are a financial analyst.

You may only use the provided evidence.

Never provide investment advice.

Never predict future prices.

Never invent missing information.

If evidence is insufficient,
respond with "Insufficient evidence."
```

---

# Gradio UI

## Tab 1 — Analyze

Input:

```text
Ticker: NVDA
```

Button:

```text
Analyze
```

Workflow:

```text
Fetch Data
    ↓
Calculate Signals
    ↓
Detect Anomalies
    ↓
Generate Report
```

Display:

* Technical Summary
* Fundamental Summary
* News Summary
* AI Explanation
* Evidence

---

## Tab 2 — Watchlist

Features:

* Add ticker
* Remove ticker
* View latest status

Columns:

* Ticker
* Trend
* Active Alerts
* Last Updated

---

## Tab 3 — Alerts

Display:

* Alert Type
* Severity
* Ticker
* Timestamp

Actions:

* Acknowledge

---

## Tab 4 — Runs

Display:

* Run ID
* Status
* Duration
* Failure Reason

Purpose:

Operational visibility.

---

## Tab 5 — Evidence Explorer

Display all evidence used to generate signals.

Users can inspect:

* Indicators
* News
* Sentiment
* Data freshness

---

# Metrics

Expose application metrics.

Examples:

```text
analysis_runs_total

analysis_run_failures_total

alerts_generated_total

signal_calculation_duration_seconds

report_generation_duration_seconds

news_ingestion_duration_seconds
```

---

# Acceptance Criteria

The project is considered complete when:

* User can analyze a ticker end-to-end
* Signals are generated successfully
* Alerts are generated successfully
* Alert deduplication works
* Analysis runs are visible
* Evidence is visible
* AI summaries are evidence-based
* Jobs are retryable
* No duplicate data is created
* System behavior is observable

---

# Interview Narrative

This project is intentionally designed as an observability platform rather than a stock picker.

The purpose is to demonstrate:

* Clean product thinking
* Background job architecture
* Idempotent data pipelines
* Alerting systems
* Explainable AI
* Agent-driven software development

The financial market serves only as the domain.

The real focus is building a trustworthy analytics platform that ingests telemetry, computes signals, detects anomalies, and produces explainable reports.

# Evidence-Based Summary and Citation Requirements

## Motivation

AI-generated summaries must be traceable.

Users should be able to verify every important statement against supporting evidence.

The system prioritizes trustworthiness over fluency.

---

## Citation Requirement

Every factual statement generated by the LLM must include at least one citation.

Example:

```text
Revenue growth remains strong at 24.3% YoY [FUND-001].

Recent sentiment has improved following earnings guidance updates [NEWS-014][NEWS-019].

The asset remains in a bullish trend because SMA20 is above SMA50 [TECH-003].
```

---

## Citation Types

### Technical Indicator Citation

```text
[TECH-001]
RSI = 68.4

[TECH-002]
MACD = 1.23

[TECH-003]
SMA20 > SMA50
```

---

### Fundamental Citation

```text
[FUND-001]
Revenue Growth = 24.3%

[FUND-002]
EPS = 3.84
```

---

### News Citation

```text
[NEWS-014]
NVIDIA raises guidance after strong AI demand

Source: Reuters
Published: 2026-06-10

[NEWS-019]
Data center revenue exceeds expectations

Source: Bloomberg
Published: 2026-06-09
```

---

## Evidence Registry

Before report generation, the system must create an evidence registry.

Example:

```json
{
  "TECH-003": {
    "type": "technical",
    "metric": "SMA crossover",
    "value": "SMA20 > SMA50"
  },

  "NEWS-014": {
    "type": "news",
    "title": "NVIDIA raises guidance"
  }
}
```

The LLM receives both:

1. Structured evidence
2. Evidence identifiers

The LLM must reference identifiers rather than raw source text.

---

## Prompt Constraint

The report generator must enforce:

* Every claim requires citation.
* No uncited factual statements allowed.
* No citation → remove the statement.
* If evidence is insufficient → return "Insufficient evidence."

---

## UI Requirements

### Summary Panel

Display:

```text
NVIDIA remains in a bullish trend because SMA20 remains above SMA50 [TECH-003].

Recent positive sentiment is driven by strong earnings guidance and AI demand growth [NEWS-014][NEWS-019].
```

---

### Evidence Drawer

Clicking:

```text
[TECH-003]
```

opens:

```text
Indicator:
SMA20 = 142.4

SMA50 = 137.1

Updated:
2026-06-10 09:00 UTC
```

Clicking:

```text
[NEWS-014]
```

opens:

```text
Title:
NVIDIA raises guidance after strong AI demand

Source:
Reuters

Published:
2026-06-10
```

---

## Acceptance Criteria

The system must guarantee:

* Every generated claim contains at least one citation.
* Every citation maps to a valid evidence record.
* Clicking a citation reveals underlying evidence.
* No unsupported statements are shown to users.
* Reports remain understandable even when citations are displayed.

```
```
