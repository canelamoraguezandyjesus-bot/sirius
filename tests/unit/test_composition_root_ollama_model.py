"""La clave ``ollama_model`` de ``settings.json``: un solo modelo local, leído
una sola vez, para el filtro de relevancia y para el clasificador de categoría.

Por qué existe: el adaptador de producción llamaba a Ollama con ``llama3.2``
mientras el laboratorio que midió 29/47 usaba ``qwen3:4b-instruct``
(``docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md``, seis
diferencias). El modelo deja de ser una constante y pasa a ser configurable,
con el del laboratorio por defecto. El comentario de ``_RELEVANCE_FILTER_MODEL``
exige que filtro y clasificador usen el mismo modelo; por eso las pruebas
comprueban que los dos reciben exactamente el mismo valor, no cada uno el suyo.

Misma técnica que ``test_composition_root_relevance_gate.py``: se sustituyen
solo los dos adaptadores de Ollama por registradores que nunca tocan la red y
se deja que ``build_conversation_dependencies`` recorra su construcción real.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import sirius.composition_root as composition_root
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import (
    _DEFAULT_OLLAMA_MODEL,
    _ollama_model,
    build_conversation_dependencies,
)
from sirius.config.settings import save_settings


class _RecordingRelevanceFilterAdapter:
    captured: ClassVar[list[str]] = []

    def __init__(self, model: str, *, timeout_seconds: float) -> None:
        type(self).captured.append(model)

    def filter_candidates(self, query_text: str, candidates: Any) -> Any:  # pragma: no cover
        return candidates


class _RecordingCategoryClassifierAdapter:
    captured: ClassVar[list[str]] = []

    def __init__(self, model: str, vocabulary: Any) -> None:
        type(self).captured.append(model)

    def classify(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        return None


def _patch_recorders(monkeypatch: Any) -> None:
    _RecordingRelevanceFilterAdapter.captured = []
    _RecordingCategoryClassifierAdapter.captured = []
    monkeypatch.setattr(
        composition_root, "OllamaRelevanceFilterAdapter", _RecordingRelevanceFilterAdapter
    )
    monkeypatch.setattr(
        composition_root, "OllamaCategoryClassifierAdapter", _RecordingCategoryClassifierAdapter
    )


def _build(tmp_path: Path) -> None:
    build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )


def test_sin_clave_los_dos_consumidores_usan_el_modelo_del_laboratorio(
    tmp_path: Path, monkeypatch: Any
) -> None:
    _patch_recorders(monkeypatch)
    save_settings({"category_matching_enabled": True})

    _build(tmp_path)

    assert _DEFAULT_OLLAMA_MODEL == "qwen3:4b-instruct"
    assert _RecordingRelevanceFilterAdapter.captured == [_DEFAULT_OLLAMA_MODEL]
    assert _RecordingCategoryClassifierAdapter.captured == [_DEFAULT_OLLAMA_MODEL]


def test_con_clave_los_dos_consumidores_reciben_el_mismo_modelo_configurado(
    tmp_path: Path, monkeypatch: Any
) -> None:
    _patch_recorders(monkeypatch)
    save_settings({"category_matching_enabled": True, "ollama_model": "llama3.2"})

    _build(tmp_path)

    assert _RecordingRelevanceFilterAdapter.captured == ["llama3.2"]
    assert _RecordingCategoryClassifierAdapter.captured == ["llama3.2"]


def test_con_la_puerta_cerrada_el_clasificador_sigue_leyendo_la_clave(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """La puerta cerrada no construye el filtro (ver el test de la puerta),
    pero el clasificador de categoría existe siempre (D7) y debe leer la
    misma clave: no hay un segundo camino con el modelo antiguo."""
    _patch_recorders(monkeypatch)
    save_settings({"ollama_model": "otro-modelo"})

    _build(tmp_path)

    assert _RecordingRelevanceFilterAdapter.captured == []
    assert _RecordingCategoryClassifierAdapter.captured == ["otro-modelo"]


def test_valores_vacios_o_de_otro_tipo_caen_al_modelo_por_defecto() -> None:
    assert _ollama_model({}) == _DEFAULT_OLLAMA_MODEL
    assert _ollama_model({"ollama_model": ""}) == _DEFAULT_OLLAMA_MODEL
    assert _ollama_model({"ollama_model": "   "}) == _DEFAULT_OLLAMA_MODEL
    assert _ollama_model({"ollama_model": 7}) == _DEFAULT_OLLAMA_MODEL
    assert _ollama_model({"ollama_model": " gemma3:4b "}) == "gemma3:4b"
