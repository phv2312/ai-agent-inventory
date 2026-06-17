"""Gradio Analyze tab."""

from __future__ import annotations

import asyncio

import gradio as gr

from applications.stonitor.deps import StonitorDeps
from applications.stonitor.market.exc import (
    DataUnavailableError,
    InsufficientEvidenceError,
    InvalidTickerError,
    MarketError,
)
from applications.stonitor.market.models.dto import (
    EvidenceRecord,
    EvidenceRegistry,
    Report,
)
from applications.stonitor.ui.formatters import parse_news_record

_CATEGORY_LABELS = {
    "technical": "Kỹ thuật",
    "fundamental": "Cơ bản",
    "news": "Tin tức",
}

_EVIDENCE_EMPTY = "_Chưa có bằng chứng. Chạy phân tích để xem._"
_NEWS_EMPTY = "_Chưa có tin tức. Chạy phân tích để xem._"

_SENTIMENT_COLORS = {
    "negative": "#fecaca",
    "positive": "#bbf7d0",
    "neutral": "#e2e8f0",
}


def _format_ai_response(report: Report) -> str:
    return (
        f"{report.ai_explanation}\n\n"
        f"_Cập nhật: {report.generated_at.isoformat()}_"
    )


def _format_evidence_body(record: EvidenceRecord) -> str:
    category = _CATEGORY_LABELS.get(record.category, record.category)
    return (
        f"**Danh mục:** {category}\n\n"
        f"**Nhãn:** {record.label}\n\n"
        f"**Giá trị:** {record.value}\n\n"
        f"**Nguồn:** {record.source or 'N/A'}\n\n"
        f"**Thời điểm:** {record.captured_at.isoformat()}"
    )


def _format_run_status(report: Report | None, error: str | None) -> str:
    if error:
        return f"**Trạng thái:** Thất bại — {error}"
    if report is None:
        return "**Trạng thái:** Chưa chạy phân tích"
    return (
        f"**Trạng thái:** Hoàn thành — {report.ticker} "
        f"({report.generated_at.strftime('%H:%M:%S %d/%m/%Y')})"
    )


def _format_news_article_body(record: EvidenceRecord) -> str:
    fields = parse_news_record(record)
    color = _SENTIMENT_COLORS.get(fields.sentiment.lower(), "#fef08a")
    sentiment_mark = (
        f'<mark style="background:{color}; color: green;">{fields.sentiment}</mark>'
    )
    content = fields.content or "_Không có nội dung._"
    url_line = (
        f"**Link:** [{fields.url}]({fields.url})  \n"
        if fields.url
        else ""
    )
    return (
        f"**Ngày:** {fields.day} &nbsp;|&nbsp; "
        f"**Sentiment:** {sentiment_mark} &nbsp;|&nbsp; "
        f"**Nguồn:** {record.source or 'N/A'}  \n"
        f"{url_line}"
        f"\n---\n\n"
        f"{content}"
    )


def render(deps: StonitorDeps) -> None:
    """Render the Phân tích tab."""

    async def run_analysis(
        ticker: str,
    ) -> tuple[str, str, EvidenceRegistry | None]:
        symbol = ticker.strip().upper()
        if not symbol:
            return (
                "",
                _format_run_status(None, "Vui lòng nhập mã CP"),
                None,
            )
        try:
            report = await deps.analysis.analyze(symbol)
            return (
                _format_ai_response(report),
                _format_run_status(report, None),
                report.evidence_registry,
            )
        except InvalidTickerError as exc:
            return "", _format_run_status(None, str(exc)), None
        except DataUnavailableError as exc:
            return "", _format_run_status(None, str(exc)), None
        except InsufficientEvidenceError:
            return (
                "Insufficient evidence.",
                _format_run_status(None, "Insufficient evidence."),
                None,
            )
        except MarketError as exc:
            return "", _format_run_status(None, str(exc)), None

    def sync_run_analysis(
        ticker: str,
    ) -> tuple[str, str, EvidenceRegistry | None]:
        return asyncio.run(run_analysis(ticker))

    with gr.Tab("Phân tích", id="analyze"):
        gr.Markdown(
            "### Phân tích cổ phiếu\n"
            "Nhập mã CP Việt Nam (VD: VNM, FPT) và bấm Phân tích.",
        )
        with gr.Row():
            ticker_input = gr.Textbox(
                label="Mã CP",
                placeholder="VNM",
                scale=2,
            )
            analyze_btn = gr.Button("Phân tích", variant="primary", scale=1)
        run_status = gr.Markdown(_format_run_status(None, None))
        evidence_registry = gr.State(None)

        with gr.Row():
            with gr.Column(scale=5):
                gr.Markdown("#### Giải thích AI")
                ai_output = gr.Markdown(
                    value="",
                    sanitize_html=False,
                    elem_classes=["stonitor-mark-panel"],
                )

            with gr.Column(scale=5):
                gr.Markdown("#### Tin tức")

                @gr.render(inputs=evidence_registry)
                def render_news_accordions(
                    registry: EvidenceRegistry | None,
                ) -> None:
                    news_records = [
                        record
                        for record in (registry.records.values() if registry else [])
                        if record.category == "news"
                    ]
                    if not news_records:
                        gr.Markdown(_NEWS_EMPTY)
                        return
                    for record in sorted(
                        news_records, key=lambda record: record.id
                    ):
                        fields = parse_news_record(record)
                        label = fields.title or record.label
                        heading = (
                            f"{record.id} — {label[:120]}…"
                            if len(label) > 120
                            else f"{record.id} — {label}"
                        )
                        with gr.Accordion(heading, open=False):
                            gr.Markdown(
                                _format_news_article_body(record),
                                sanitize_html=False,
                            )

                gr.Markdown("#### Bằng chứng")

                @gr.render(inputs=evidence_registry)
                def render_evidence_accordions(
                    registry: EvidenceRegistry | None,
                ) -> None:
                    if registry is None or not registry.records:
                        gr.Markdown(_EVIDENCE_EMPTY)
                        return
                    for record in sorted(
                        registry.records.values(),
                        key=lambda record: record.id,
                    ):
                        if record.category == "news":
                            continue
                        title = f"{record.id} — {record.label}"
                        with gr.Accordion(title, open=False):
                            gr.Markdown(
                                _format_evidence_body(record),
                                sanitize_html=False,
                            )

        analyze_btn.click(
            fn=sync_run_analysis,
            inputs=ticker_input,
            outputs=[ai_output, run_status, evidence_registry],
        )
