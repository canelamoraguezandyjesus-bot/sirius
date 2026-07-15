"""Composition tests for credential validation wiring."""

from __future__ import annotations

from pathlib import Path

from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.validate_and_save_api_key import ValidateAndSaveApiKeyUseCase
from sirius.composition_root import build_conversation_dependencies


def test_dependencies_expose_validate_before_save_use_case(tmp_path: Path) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db",
        tmp_path / "backups",
        secret_store=FakeSecretStore(),
    )

    assert isinstance(
        dependencies.validate_and_save_api_key_use_case,
        ValidateAndSaveApiKeyUseCase,
    )
