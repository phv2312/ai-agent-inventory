import logging
from collections.abc import Sequence

from structlog import configure
from structlog.contextvars import merge_contextvars
from structlog.dev import (
    _EVENT_WIDTH,
    Column,
    ConsoleRenderer,
    KeyValueColumnFormatter,
    RichTracebackFormatter,
    _ColorfulStyles,
    _has_colors,
    default_exception_formatter,
    plain_traceback,
    set_exc_info,
)
from structlog.processors import (
    CallsiteParameter,
    CallsiteParameterAdder,
    JSONRenderer,
    StackInfoRenderer,
    TimeStamper,
    UnicodeDecoder,
)
from structlog.stdlib import (
    ExtraAdder,
    LoggerFactory,
    PositionalArgumentsFormatter,
    ProcessorFormatter,
    add_log_level,
    add_logger_name,
)
from structlog.typing import (
    EventDict,
    ExceptionRenderer,
    Processor,
    WrappedLogger,
)

__all__ = [
    "MyConsoleRenderer",
    "configure_logger",
    "merge_module_lineno_function_to_location",
    "override_default_logging",
]


class MyConsoleRenderer(ConsoleRenderer):
    """Customized console renderer."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        pad_event: int = _EVENT_WIDTH,
        colors: bool = _has_colors,
        force_colors: bool = False,
        repr_native_str: bool = False,
        level_styles: dict[str, str] | None = None,
        exception_formatter: ExceptionRenderer = default_exception_formatter,
        sort_keys: bool = True,
        event_key: str = "event",
        timestamp_key: str = "timestamp",
        columns: list[Column] | None = None,
        pad_level: bool = True,
    ) -> None:
        """Initialize the console renderer with custom column ordering.

        Args:
            pad_event: Width to pad the event message to.
            colors: Whether to use colors in the output.
            force_colors: Force colors even if terminal doesn't support them.
            repr_native_str: Whether to repr native strings.
            level_styles: Custom styles for log levels.
            exception_formatter: Formatter for rendering exceptions.
            sort_keys: Whether to sort keys in the output.
            event_key: Key name for the event message in the event dict.
            timestamp_key: Key name for the timestamp in the event dict.
            columns: Custom columns to use for rendering.
            pad_level: Whether to pad the log level for alignment.

        """
        super().__init__(
            pad_event=pad_event,
            colors=colors,
            force_colors=force_colors,
            repr_native_str=repr_native_str,
            level_styles=level_styles,
            exception_formatter=exception_formatter,
            sort_keys=sort_keys,
            event_key=event_key,
            timestamp_key=timestamp_key,
            columns=columns,
            pad_level=pad_level,
        )
        idx_level: int = 1
        idx_logger: int = -1
        idx_logger_name: int = -1

        for idx, col in enumerate(self._columns):
            match col.key:
                case "level":
                    idx_level = idx
                case "logger":
                    idx_logger = idx
                case "logger_name":
                    idx_logger_name = idx
                case _:
                    continue

        moving_cols: list[Column] = []
        if idx_logger_name != -1:
            moving_cols.append(self._columns.pop(idx_logger_name))

        if idx_logger != -1:
            moving_cols.append(self._columns.pop(idx_logger))
        self._columns[idx_level + 1 : idx_level + 1] = moving_cols
        self._columns.insert(
            idx_level + 1 + len(moving_cols),
            Column(
                "location",
                KeyValueColumnFormatter(
                    key_style=None,
                    value_style=(_ColorfulStyles.bright + _ColorfulStyles.level_info),
                    reset_style=_ColorfulStyles.reset,
                    value_repr=str,
                    prefix="(",
                    postfix=")",
                ),
            ),
        )


def merge_module_lineno_function_to_location(
    _logger: WrappedLogger,
    _module_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add line number and function name into event dict."""
    lineno = event_dict.pop(CallsiteParameter.LINENO.value, None)
    func_name = event_dict.pop(CallsiteParameter.FUNC_NAME.value, None)
    event_dict["location"] = f"{func_name}:{lineno}"
    return event_dict


def override_default_logging(
    processors: Sequence[Processor],
    log_renderer: Processor,
    level: str = "INFO",
) -> None:
    """Override Python's logging."""
    handler = logging.StreamHandler()
    formatter = ProcessorFormatter(
        processors=[
            ProcessorFormatter.remove_processors_meta,
            log_renderer,
        ],
        foreign_pre_chain=processors,
    )
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())


def configure_logger(
    *,
    level: str = "INFO",
    enable_json_logs: bool = False,
    use_rich_traceback_formatter: bool = False,
    timestamper_fmt: str = "%H:%M:%S",
) -> None:
    """Configure global logger with supported configs.

    Args:
        level: Log level for the root logger.
        enable_json_logs: Render logs as JSON instead of console output.
        use_rich_traceback_formatter: Opt in to rich's boxed traceback
            renderer. Defaults to False: rich wraps long class names and
            variable reprs into narrow boxed columns, which truncates
            them illegibly on anything but a wide terminal. Plain
            tracebacks stay readable regardless of terminal width.
        timestamper_fmt: strftime format for the log timestamp.

    """
    timestamper: Processor = TimeStamper(fmt=timestamper_fmt, utc=True)
    shared_processors: list[Processor] = [
        merge_contextvars,
        add_log_level,
        add_logger_name,
        PositionalArgumentsFormatter(),
        timestamper,
        CallsiteParameterAdder(
            [
                CallsiteParameter.LINENO,
                CallsiteParameter.FUNC_NAME,
            ],
        ),
        merge_module_lineno_function_to_location,
        StackInfoRenderer(),
        set_exc_info,
        UnicodeDecoder(),
        ExtraAdder(),
    ]

    configure(
        processors=[
            *shared_processors,
            ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    override_default_logging(
        shared_processors,
        JSONRenderer()
        if enable_json_logs
        else (
            MyConsoleRenderer(
                exception_formatter=(
                    RichTracebackFormatter()
                    if use_rich_traceback_formatter
                    else plain_traceback
                ),
            )
        ),
        level=level,
    )
