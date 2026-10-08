"""Reversible masking for customer PII at external LLM boundaries."""

from __future__ import annotations

import re


class PIIProtector:
    """Mask and restore customer PII for one request.

    Operational network identifiers such as tower IDs and tower names are
    intentionally not matched, so diagnostic agents retain useful context.
    """

    _patterns = (
        ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
        ("PHONE", re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)")),
        ("CUSTOMER_ID", re.compile(r"\bCUST-\d{5}\b", re.IGNORECASE)),
    )

    def __init__(self) -> None:
        self._token_by_value: dict[tuple[str, str], str] = {}
        self._value_by_token: dict[str, str] = {}

    def protect(self, text: str) -> str:
        """Replace detected customer PII with request-local tokens."""
        protected = text
        for kind, pattern in self._patterns:
            protected = pattern.sub(lambda match: self._token(kind, match.group(0)), protected)
        return protected

    def restore(self, text: str) -> str:
        """Restore request-local tokens in model output."""
        restored = text
        for token, value in self._value_by_token.items():
            restored = restored.replace(token, value)
        return restored

    def _token(self, kind: str, value: str) -> str:
        key = (kind, value)
        token = self._token_by_value.get(key)
        if token is None:
            token = f"<PII_{kind}_{len(self._token_by_value) + 1}>"
            self._token_by_value[key] = token
            self._value_by_token[token] = value
        return token