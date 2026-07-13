"""Local diagnostic logging (SIRIUS-ARQ-0.1 S13 "Observabilidad local y diagnóstico").

One rotating file, ``logs/application.log``, 5 files of 5 MB each ("5
archivos de 5 MB"): startup, shutdown, selected provider, operations
(``operation_id``), and errors — never full message content, never secrets.

The redaction filter below is a *defensive last resort*, not the primary
safeguard: call sites must never pass an API key, header, or full prompt/
response text to a log call in the first place. The filter exists in case
something secret-shaped slips through anyway.
"""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "sirius"
LOG_FILE_NAME = "application.log"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 4  # + the active file itself = 5 files total, per S13.

_REDACTED = "[REDACTADO]"

_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),  # OpenAI-style API keys.
    re.compile(r"(?i)bearer\s+\S+"),  # Authorization headers.
    re.compile(r"(?i)(api[-_]?key)\s*[:=]\s*\S+"),  # "api_key=..." / "apikey: ...".
)


def _redact(message: str) -> str:
    for pattern in _SECRET_PATTERNS:
        message = pattern.sub(_REDACTED, message)
    return message


class _RedactingFilter(logging.Filter):
    """Rewrites a record's rendered message, replacing secret-shaped substrings."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(record.getMessage())
        record.args = ()
        return True


def configure_logging(logs_dir: Path, *, level: int = logging.INFO) -> logging.Logger:
    """Attach a rotating file handler to the ``sirius`` logger, once.

    Safe to call more than once (e.g. across tests): re-invoking with a new
    ``logs_dir`` replaces the handler instead of stacking duplicates.
    """
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    handler = RotatingFileHandler(
        logs_dir / LOG_FILE_NAME,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(_RedactingFilter())
    logger.addHandler(handler)
    return logger


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """Return a child (or the root) Sirius logger; never configures handlers itself."""
    return logging.getLogger(name)
