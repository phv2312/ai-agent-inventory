"""Domain exceptions for evaluation workflows."""


class EvaluationError(Exception):
    """Base class for evaluation workflow failures."""


class DatasetValidationError(EvaluationError):
    """Raised when a dataset file violates the dataset contract."""


class TraceCaptureError(EvaluationError):
    """Raised when dataset query trace capture cannot complete."""


class PhoenixTraceError(EvaluationError):
    """Raised when Phoenix trace loading cannot complete."""


class JudgeError(EvaluationError):
    """Raised when an LLM judge result is invalid or unavailable."""


class VisualizationError(EvaluationError):
    """Raised when visualization parsing or execution fails unexpectedly."""


class ExportError(EvaluationError):
    """Raised when report or artifact export cannot complete."""
