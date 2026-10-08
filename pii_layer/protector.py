"""Authenticated encryption for customer PII at external LLM boundaries."""

from __future__ import annotations

import re

from cryptography.fernet import Fernet


class PIIProtector:
    """Encrypt and restore customer PII for one request.

    Operational network identifiers such as tower IDs and tower names are
    intentionally not matched, so diagnostic agents retain useful context.
    """

    _patterns = (
        ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
        ("PHONE", re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)")),
        ("CUSTOMER_ID", re.compile(r"\bCUST-\d{5}\b", re.IGNORECASE)),
    )

    def __init__(self) -> None:
        self._cipher = Fernet(Fernet.generate_key())
        self._token_by_value: dict[tuple[str, str], str] = {}
        self._encrypted_by_token: dict[str, bytes] = {}

    def protect(self, text: str) -> str:
        """Encrypt detected customer PII and replace it with opaque tokens."""
        protected = text
        for kind, pattern in self._patterns:
            protected = pattern.sub(lambda match: self._token(kind, match.group(0)), protected)
        return protected

    def restore(self, text: str) -> str:
        """Decrypt and restore request-local tokens in model output."""
        restored = text
        for token, encrypted_value in self._encrypted_by_token.items():
            value = self._cipher.decrypt(encrypted_value).decode("utf-8")
            restored = restored.replace(token, value)
        return restored

    @property
    def has_protected_pii(self) -> bool:
        """Return True if any customer PII was detected and encrypted."""
        return len(self._encrypted_by_token) > 0

    @property
    def tokens(self) -> list[str]:
        """Return list of generated token placeholders."""
        return list(self._encrypted_by_token.keys())

    @property
    def encrypted_payloads(self) -> dict[str, str]:
        """Return opaque Fernet ciphertexts for safe audit display."""
        return {
            token: encrypted.decode("ascii")
            for token, encrypted in self._encrypted_by_token.items()
        }

    def audit_summary(self, text: str | None = None) -> str:
        """Describe detected PII categories without exposing their values."""
        if text is not None:
            masked_categories = []
            for kind, pattern in self._patterns:
                count = len(pattern.findall(text))
                if count:
                    masked_categories.append(f"{kind} x{count}")
            return ", ".join(masked_categories) if masked_categories else "none detected"

        if not self._token_by_value:
            return "none detected"
        counts: dict[str, int] = {}
        for (kind, _) in self._token_by_value.keys():
            counts[kind] = counts.get(kind, 0) + 1
        return ", ".join(f"{kind} x{count}" for kind, count in counts.items())

    def _token(self, kind: str, value: str) -> str:
        key = (kind, value.upper() if kind == "CUSTOMER_ID" else value)
        token = self._token_by_value.get(key)
        if token is None:
            token = f"<PII_ENCRYPTED_{kind}_{len(self._token_by_value) + 1}>"
            self._token_by_value[key] = token
            self._encrypted_by_token[token] = self._cipher.encrypt(value.encode("utf-8"))
        return token