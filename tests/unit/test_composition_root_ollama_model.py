"""La clave ``ollama_model`` de ``settings.json``: el modelo local de lo que aún
clasifica con Ollama fuera de la charla.

Por qué existe: el adaptador de producción llamaba a Ollama con ``llama3.2``
mientras el laboratorio que midió 29/47 usaba ``qwen3:4b-instruct``
(``docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md``, seis
diferencias). El modelo dejó de ser una constante y pasó a ser configurable,
con el del laboratorio por defecto.

Desde ADR-238 (pieza F de ADR-233) el filtro de relevancia y el clasificador de
categoría ya no se montan: el único que lee la clave es el que propone la
criticidad de un recuerdo cuando el propietario lo selecciona.

Se sustituye solo ese adaptador por un registrador que nunca toca la red y se
deja que ``build_conversation_dependencies`` recorra su construcción real.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import pytest

import sirius.composition_root as composition_root
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import (
    _DEFAULT_OLLAMA_MODEL,
    _ollama_model,
    build_conversation_dependencies,
)
from sirius.config.settings import save_settings


class _RecordingCriticalityClassifierAdapter:
    captured: ClassVar[list[str]] = []

    def __init__(self, model: str) -> None:
        type(self).captured.append(model)

    def propose(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        return None


@pytest.mark.parametrize(
    ("ajustes", "esperado"),
    [
        ({}, _DEFAULT_OLLAMA_MODEL),
        ({"category_matching_enabled": True}, _DEFAULT_OLLAMA_MODEL),
        ({"ollama_model": "llama3.2"}, "llama3.2"),
    ],
)
def test_el_clasificador_de_criticidad_recibe_el_modelo_de_la_clave(
    ajustes: dict[str, Any], esperado: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _RecordingCriticalityClassifierAdapter.captured = []
    monkeypatch.setattr(
        composition_root,
        "OllamaCriticalityClassifierAdapter",
        _RecordingCriticalityClassifierAdapter,
    )
    save_settings(ajustes)

    build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert _DEFAULT_OLLAMA_MODEL == "qwen3:4b-instruct"
    assert _RecordingCriticalityClassifierAdapter.captured == [esperado]


def test_valores_vacios_o_de_otro_tipo_caen_al_modelo_por_defecto() -> None:
    assert _ollama_model({}) == _DEFAULT_OLLAMA_MODEL
    assert _ollama_model({"ollama_model": ""}) == _DEFAULT_OLLAMA_MODEL
    assert _ollama_model({"ollama_model": "   "}) == _DEFAULT_OLLAMA_MODEL
    assert _ollama_model({"ollama_model": 7}) == _DEFAULT_OLLAMA_MODEL
    assert _ollama_model({"ollama_model": " gemma3:4b "}) == "gemma3:4b"
