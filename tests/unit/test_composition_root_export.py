"""Unit test for the composition root's structured-export wiring (B9a).

Only checks that the use case comes out wired with the right type; behavior
is covered by the adapter and use-case tests. No presentation code calls
this use case yet (B9b), so there is nothing to wire beyond this.
"""

from __future__ import annotations

from pathlib import Path

from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.export_structured import ExportStructuredUseCase
from sirius.composition_root import build_conversation_dependencies


def test_build_conversation_dependencies_wires_the_export_structured_use_case(
    tmp_path: Path,
) -> None:
    dependencies = build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert isinstance(dependencies.export_structured_use_case, ExportStructuredUseCase)
