"""Deterministic secret redaction applied before and after provider calls."""

from __future__ import annotations

import re
from dataclasses import dataclass

REDACTED = "[REDACTED]"


@dataclass(frozen=True)
class RedactionResult:
    """Redacted text and the number of substitutions."""

    text: str
    count: int


class SecretRedactor:
    """Remove common credentials without retaining or hashing their values."""

    _patterns = (
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,;]+"),
        re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"),
        re.compile(
            r"(?i)\b(api[_-]?key|token|password|passwd|secret)\b(\s*[:=]\s*)"
            r"([^\s,;]+)"
        ),
        re.compile(r"(?i)(postgres(?:ql)?://[^:\s/@]+:)[^@\s/]+(@)"),
        re.compile(r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"),
    )

    def redact(self, value: str) -> RedactionResult:
        """Return a value safe to place in provider input or API output."""
        text = value
        total = 0
        for index, pattern in enumerate(self._patterns):
            if index == 2:
                text, count = pattern.subn(r"\1\2" + REDACTED, text)
            elif index == 3:
                text, count = pattern.subn(r"\1" + REDACTED + r"\2", text)
            elif index == 4:
                text, count = pattern.subn(REDACTED, text)
            else:
                text, count = pattern.subn(r"\1" + REDACTED, text)
            total += count
        return RedactionResult(text=text, count=total)
