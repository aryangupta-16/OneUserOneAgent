"""Model provider abstraction (interface)."""
from __future__ import annotations

from typing import Any, Optional, Protocol


class ModelProvider(Protocol):
    """Interface for model providers."""

    def call(self, trigger_event_id: str, user_id: str, context: dict) -> dict:
        """Call the model with context. Returns a dict with the model's response.

        May raise TimeoutError or ModelError for fault reproduction.
        """
        ...


class ModelError(Exception):
    """Raised when the model returns an error."""
    pass
