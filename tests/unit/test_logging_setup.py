"""Unit tests for local diagnostic logging (SIRIUS-ARQ-0.1 S13)."""

from __future__ import annotations

import logging
from pathlib import Path

from sirius.infrastructure.logging import (
    BACKUP_COUNT,
    LOG_FILE_NAME,
    MAX_BYTES,
    configure_logging,
    get_logger,
)


def test_configure_logging_creates_the_log_file(tmp_path: Path) -> None:
    configure_logging(tmp_path)

    log_file = tmp_path / LOG_FILE_NAME
    assert log_file.name == "application.log"
    logger = get_logger("sirius.test.create")
    logger.info("arranque de prueba")
    for handler in logging.getLogger("sirius").handlers:
        handler.flush()

    assert log_file.is_file()
    assert "arranque de prueba" in log_file.read_text(encoding="utf-8")


def test_rotation_limits_match_the_canonical_five_files_of_five_mb(tmp_path: Path) -> None:
    configure_logging(tmp_path)

    assert MAX_BYTES == 5 * 1024 * 1024
    assert BACKUP_COUNT == 4  # + the active file = 5 total, per S13.

    handler = logging.getLogger("sirius").handlers[0]
    assert handler.maxBytes == MAX_BYTES  # type: ignore[attr-defined]
    assert handler.backupCount == BACKUP_COUNT  # type: ignore[attr-defined]


def test_reconfiguring_does_not_stack_duplicate_handlers(tmp_path: Path) -> None:
    configure_logging(tmp_path)
    configure_logging(tmp_path)

    assert len(logging.getLogger("sirius").handlers) == 1


def test_openai_style_key_is_redacted(tmp_path: Path) -> None:
    configure_logging(tmp_path)
    logger = get_logger("sirius.test.redact")

    logger.info("clave detectada: sk-abcdefghijklmnopqrstuvwxyz")
    for handler in logging.getLogger("sirius").handlers:
        handler.flush()

    content = (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in content
    assert "[REDACTADO]" in content


def test_bearer_header_is_redacted(tmp_path: Path) -> None:
    configure_logging(tmp_path)
    logger = get_logger("sirius.test.redact_bearer")

    logger.info("cabecera: Bearer sk-abcd1234efgh5678")
    for handler in logging.getLogger("sirius").handlers:
        handler.flush()

    content = (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "sk-abcd1234efgh5678" not in content
    assert "[REDACTADO]" in content


def test_api_key_assignment_pattern_is_redacted(tmp_path: Path) -> None:
    configure_logging(tmp_path)
    logger = get_logger("sirius.test.redact_assignment")

    logger.info("config: api_key=sk-should-not-appear")
    for handler in logging.getLogger("sirius").handlers:
        handler.flush()

    content = (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "sk-should-not-appear" not in content


def test_operation_id_is_not_redacted(tmp_path: Path) -> None:
    """Canonical requirement: technical logs keep operation_id/provider_request_id."""
    configure_logging(tmp_path)
    logger = get_logger("sirius.test.keep_ids")

    logger.info("Operación %s finalizada: completed", "11111111-2222-3333-4444-555555555555")
    for handler in logging.getLogger("sirius").handlers:
        handler.flush()

    content = (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "11111111-2222-3333-4444-555555555555" in content
