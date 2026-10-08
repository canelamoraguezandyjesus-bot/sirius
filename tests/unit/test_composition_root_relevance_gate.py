"""La raíz de composición ya no lee las puertas viejas de la memoria (ADR-238).

Hasta la pieza F de ADR-233, ``category_matching_enabled`` y sus tres
interruptores (ADR-185) montaban el motor por etapas, el intérprete de la
pregunta con Ollama y el filtro de relevancia con Ollama dentro de cada turno.
Desde ADR-238, la charla busca los recuerdos por palabras y por significado y
nada de eso se monta, abra quien abra las puertas: estas pruebas lo fijan con
cada combinación de claves.

Las dos clases de verdad se heredan en vez de sustituirse, así que
``build_conversation_dependencies`` sigue recorriendo su construcción real; la
subclase solo apunta los argumentos con los que se construyó.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any, ClassVar

import pytest

import sirius.composition_root as composition_root
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.context import ContextBuilder
from sirius.application.memory_search import MemorySearch
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.composition_root import build_conversation_dependencies
from sirius.config.memory_gates import puertas_de_memoria
from sirius.config.settings import save_settings


class _RecordingRankUseCase(RankRelevantKnowledgeUseCase):
    captured: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        type(self).captured.append(kwargs)
        super().__init__(*args, **kwargs)


class _RecordingContextBuilder(ContextBuilder):
    captured: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        type(self).captured.append(kwargs)
        super().__init__(*args, **kwargs)


_TODAS_LAS_COMBINACIONES = [
    {},
    {"category_matching_enabled": False},
    {"category_matching_enabled": True},
    {"staged_engine_enabled": True},
    {"staged_engine_enabled": True, "query_intent_enabled": True},
    {"relevance_filter_enabled": True},
    {
        "category_matching_enabled": True,
        "staged_engine_enabled": True,
        "query_intent_enabled": True,
        "relevance_filter_enabled": True,
    },
]


@pytest.mark.parametrize("ajustes", _TODAS_LAS_COMBINACIONES)
def test_las_puertas_viejas_ya_no_cambian_lo_que_se_monta(
    ajustes: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _RecordingRankUseCase.captured = []
    _RecordingContextBuilder.captured = []
    monkeypatch.setattr(composition_root, "RankRelevantKnowledgeUseCase", _RecordingRankUseCase)
    monkeypatch.setattr(composition_root, "ContextBuilder", _RecordingContextBuilder)
    save_settings(ajustes)

    build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    [rank_kwargs] = _RecordingRankUseCase.captured
    assert set(rank_kwargs) == {
        "memory_repository",
        "decision_repository",
        "project_repository",
        "knowledge_search_repository",
        "memory_search",
    }
    assert isinstance(rank_kwargs["memory_search"], MemorySearch)
    [context_kwargs] = _RecordingContextBuilder.captured
    for viejo in ("relevance_filter_port", "max_criticality_category", "category_matching_enabled"):
        assert viejo not in context_kwargs


def test_la_raiz_de_composicion_no_importa_ningun_filtro_ni_clasificador_de_cada_turno() -> None:
    """Ni el filtro de relevancia ni el intérprete de la pregunta: no hay con qué montarlos."""
    for nombre in ("OllamaRelevanceFilterAdapter", "OllamaQueryIntentClassifierAdapter"):
        assert not hasattr(composition_root, nombre)


def test_puertas_de_memoria_lee_las_cuatro_claves_en_tabla() -> None:
    """La función pura, sin construir nada: ausente, ``False``, ``True``, un
    valor truthy no booleano y la maestra. La regla de lectura es la de la
    clave de siempre — solo el literal ``True`` cuenta — y la maestra
    enciende las tres piezas."""
    casos: list[tuple[dict[str, Any], tuple[bool, bool, bool]]] = [
        # ajustes                                              motor, petición, filtro
        ({}, (False, False, False)),
        ({"category_matching_enabled": False}, (False, False, False)),
        ({"staged_engine_enabled": False}, (False, False, False)),
        ({"query_intent_enabled": False}, (False, False, False)),
        ({"relevance_filter_enabled": False}, (False, False, False)),
        ({"staged_engine_enabled": True}, (True, False, False)),
        ({"relevance_filter_enabled": True}, (False, False, True)),
        # Encendido pero inerte no existe: sin motor, la petición propia no se
        # enciende, porque el clasificador nunca llegaría a consultarse.
        ({"query_intent_enabled": True}, (False, False, False)),
        ({"query_intent_enabled": True, "staged_engine_enabled": True}, (True, True, False)),
        # Truthy pero no booleano es apagado, en la maestra y en las tres nuevas.
        ({"category_matching_enabled": "true"}, (False, False, False)),
        ({"staged_engine_enabled": "true"}, (False, False, False)),
        ({"query_intent_enabled": 1}, (False, False, False)),
        ({"relevance_filter_enabled": "false"}, (False, False, False)),
        ({"staged_engine_enabled": None}, (False, False, False)),
        # La maestra enciende las tres a la vez: el significado de §6.3, intacto.
        ({"category_matching_enabled": True}, (True, True, True)),
        (
            {"category_matching_enabled": True, "staged_engine_enabled": False},
            (True, True, True),
        ),
    ]

    for ajustes, esperado in casos:
        puertas = puertas_de_memoria(ajustes)
        assert (
            puertas.motor_por_etapas,
            puertas.peticion_propia,
            puertas.filtro_de_relevancia,
        ) == esperado, ajustes


def test_puertas_de_memoria_es_inmutable() -> None:
    """Se lee una vez en el arranque y se reparte por el cableado: que nadie
    pueda cambiarla a mitad de la construcción es lo que hace comprobable,
    mirando un solo sitio, que el estado cerrado no se mueve."""
    puertas = puertas_de_memoria({})

    with pytest.raises(FrozenInstanceError):
        puertas.motor_por_etapas = True  # type: ignore[misc]
