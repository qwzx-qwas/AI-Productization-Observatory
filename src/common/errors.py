"""Error hierarchy that keeps processing failures separate from review issues."""

from __future__ import annotations


class ObservatoryError(Exception):
    """Base class for all local project errors."""


class ConfigError(ObservatoryError):
    """Raised when configuration paths or required environment variables are invalid."""


class ContractValidationError(ObservatoryError):
    """Raised when a config, schema, or module contract is violated."""


class ProcessingError(ObservatoryError):
    """Technical failures that should route to processing_error."""

    def __init__(self, error_type: str, message: str) -> None:
        super().__init__(message)
        self.error_type = error_type


class ReviewIssueError(ObservatoryError):
    """Semantic uncertainty that should route to review_issue."""

    def __init__(self, issue_type: str, message: str) -> None:
        super().__init__(message)
        self.issue_type = issue_type


class BlockedReplayError(ObservatoryError):
    """Raised when replay basis is unsafe and the new task must remain blocked."""
