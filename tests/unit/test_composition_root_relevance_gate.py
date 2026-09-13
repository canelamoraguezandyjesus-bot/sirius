"""Unit tests for the composition root's M11 wiring: D7 punto 6's activation
gate (SIRIUS-ARQ-0.2 §6.3, §8-M11) — ``category_matching_enabled``, read once
from ``settings.json``, threaded into both ``RankRelevantKnowledgeUseCase``
and ``ContextBuilder``.

Both real classes are subclassed rather than replaced outright, so
``build_conversation_dependencies`` still exercises its full, real
construction path (a broken wiring would still surface as a constructor
``TypeError``); the subclasses only add a side channel that records the
keyword arguments composition_root actually passed, which the two use cases
never expose again afterwards.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any, ClassVar

import pytest

import sirius.composition_root as composition_root
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_identity_repository import (
    build_sqlite_identity_repository,
)
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.context import ContextBuilder
from sirius.application.interpret_query_request import InterpreteDePeticion
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.composition_root import (
    _CATEGORY_VOCABULARY,
    _CRITICALITY_VOCABULARY,
    _MAX_CRITICALITY_CATEGORY,
    _RELEVANCE_FILTER_MODEL,
    _RELEVANCE_FILTER_TIMEOUT_SECONDS,
    build_conversation_dependencies,
)
from sirius.config.memory_gates import puertas_de_memoria
from sirius.config.settings import save_settings
from sirius.domain.staged_engine_contracts import Cardinalidad, Modo


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


class _RecordingRelevanceFilterAdapter:
    """Stands in for ``OllamaRelevanceFilterAdapter``: never touches the
    network, just records the constructor arguments composition_root passed
    and behaves like a filter that never excludes anything, so the rest of
    the wiring still completes normally."""

    captured: ClassVar[list[tuple[str, float]]] = []

    def __init__(self, model: str, *, timeout_seconds: float) -> None:
        type(self).captured.append((model, timeout_seconds))

    def filter_candidates(
        self, query_text: str, candidates: Any, *, cupo: int | None = None
    ) -> Any:  # pragma: no cover - never exercised here
        return candidates


class _RecordingQueryIntentAdapter:
    """Stands in for ``OllamaQueryIntentClassifierAdapter`` (ADR-164): never
    touches the network, just records the model composition_root passed, and
    behaves like a model that could not decide, so the interpreter falls back
    to the uniform petition and the rest of the wiring completes normally."""

    captured: ClassVar[list[str]] = []

    def __init__(self, model: str) -> None:
        type(self).captured.append(model)

    def classify_intent(self, query_text: str) -> None:  # pragma: no cover
        return None


def _patch_recorders(monkeypatch: Any) -> None:
    _RecordingRankUseCase.captured = []
    _RecordingContextBuilder.captured = []
    _RecordingRelevanceFilterAdapter.captured = []
    _RecordingQueryIntentAdapter.captured = []
    monkeypatch.setattr(
        composition_root, "OllamaQueryIntentClassifierAdapter", _RecordingQueryIntentAdapter
    )
    monkeypatch.setattr(composition_root, "RankRelevantKnowledgeUseCase", _RecordingRankUseCase)
    monkeypatch.setattr(composition_root, "ContextBuilder", _RecordingContextBuilder)
    monkeypatch.setattr(
        composition_root, "OllamaRelevanceFilterAdapter", _RecordingRelevanceFilterAdapter
    )


def test_gate_closed_by_default_builds_exactly_todays_construction(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """With no ``category_matching_enabled`` key at all — the default,
    unmodified ``settings.json`` — both use cases must be built with exactly
    the arguments their own defaults already produce, and the Ollama
    relevance filter must never even be instantiated."""
    _patch_recorders(monkeypatch)

    build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert _RecordingRelevanceFilterAdapter.captured == []
    assert len(_RecordingRankUseCase.captured) == 1
    rank_kwargs = _RecordingRankUseCase.captured[0]
    assert rank_kwargs["category_vocabulary"] == frozenset()
    assert rank_kwargs["category_matching_enabled"] is False
    assert len(_RecordingContextBuilder.captured) == 1
    context_kwargs = _RecordingContextBuilder.captured[0]
    assert context_kwargs["relevance_filter_port"] is None
    assert context_kwargs["max_criticality_category"] is None
    # M15 (§11.2/§11.5, incidencia #490): the same gate now also threads
    # into ContextBuilder's own RF-25/RF-26 switch.
    assert context_kwargs["category_matching_enabled"] is False


def test_gate_closed_explicitly_in_settings_builds_the_same_way(
    tmp_path: Path, monkeypatch: Any
) -> None:
    _patch_recorders(monkeypatch)
    save_settings({"category_matching_enabled": False})

    build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert _RecordingRelevanceFilterAdapter.captured == []
    assert _RecordingRankUseCase.captured[0]["category_matching_enabled"] is False


def test_gate_stays_closed_on_a_truthy_but_non_boolean_value(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Incidencia #471/CODEX-001: una edición manual de ``settings.json`` que
    deje ``category_matching_enabled`` como una cadena no vacía —p. ej.
    ``"false"``, truthy en Python aunque su intención sea evidentemente
    cerrar la puerta— no debe abrirla. Solo el booleano JSON ``true`` exacto
    lo hace; cualquier otro valor truthy pero no booleano se trata como
    cerrado."""
    _patch_recorders(monkeypatch)
    save_settings({"category_matching_enabled": "false"})

    build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert _RecordingRelevanceFilterAdapter.captured == []
    assert _RecordingRankUseCase.captured[0]["category_matching_enabled"] is False
    assert _RecordingRankUseCase.captured[0]["category_vocabulary"] == frozenset()
    assert _RecordingContextBuilder.captured[0]["relevance_filter_port"] is None
    assert _RecordingContextBuilder.captured[0]["max_criticality_category"] is None
    assert _RecordingContextBuilder.captured[0]["category_matching_enabled"] is False


def test_gate_open_wires_the_real_vocabulary_and_the_ollama_relevance_filter(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """D7 punto 6, §6.3: once the owner registers the matching threshold in
    ``STATUS.md`` and someone flips this key by hand, composition_root must
    build ``RankRelevantKnowledgeUseCase`` with the real category vocabulary
    and ``ContextBuilder`` with a real ``RelevanceFilterPort`` plus the
    max-criticality category the candado protects."""
    _patch_recorders(monkeypatch)
    save_settings({"category_matching_enabled": True})

    build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert _RecordingRelevanceFilterAdapter.captured == [
        (_RELEVANCE_FILTER_MODEL, _RELEVANCE_FILTER_TIMEOUT_SECONDS)
    ]
    rank_kwargs = _RecordingRankUseCase.captured[0]
    assert rank_kwargs["category_vocabulary"] == _CATEGORY_VOCABULARY
    assert rank_kwargs["category_matching_enabled"] is True
    context_kwargs = _RecordingContextBuilder.captured[0]
    assert isinstance(context_kwargs["relevance_filter_port"], _RecordingRelevanceFilterAdapter)
    assert context_kwargs["max_criticality_category"] == _MAX_CRITICALITY_CATEGORY
    assert context_kwargs["category_matching_enabled"] is True


def test_gate_wiring_never_breaks_the_relevance_filter_port_contract(tmp_path: Path) -> None:
    """Sanity check independent of the recording doubles above: the real
    ``OllamaRelevanceFilterAdapter`` composition_root builds when the gate is
    open still satisfies ``RelevanceFilterPort`` structurally."""
    database_path = tmp_path / "sirius.db"
    upgrade_to_head(database_path)
    build_sqlite_conversation_repository(database_path).get_or_create_main_conversation()
    build_sqlite_identity_repository(database_path).get_or_create_current_identity()
    save_settings({"category_matching_enabled": True})

    dependencies = build_conversation_dependencies(
        database_path, tmp_path / "backups", secret_store=FakeSecretStore()
    )

    # Never crashes even though no real Ollama is reachable in CI: the
    # adapter fails open, exactly like it would against a real, unreachable
    # local Ollama.
    result = dependencies.send_message_use_case.send_message("hola")
    assert result.user_message.content == "hola"


def test_gate_closed_builds_the_interpreter_without_a_model(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """ADR-164 (palanca 1 de ADR-148): el intérprete de peticiones va detrás
    de la MISMA puerta cerrada por defecto. Con ella cerrada, el adaptador
    local ni siquiera se instancia y el intérprete se construye sin
    clasificador — es decir, emitiendo exactamente la petición uniforme de
    antes de ADR-164."""
    _patch_recorders(monkeypatch)

    build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert _RecordingQueryIntentAdapter.captured == []
    interprete = _RecordingRankUseCase.captured[0]["query_request_interpreter"]
    assert isinstance(interprete, InterpreteDePeticion)
    peticion = interprete.interpretar("consulta", "op-1", active_project_id=None)
    assert peticion.modo is Modo.M1_ORDINARIO
    assert peticion.cardinalidad is Cardinalidad.EXHAUSTIVA
    assert peticion.ventana.corte_de_registro is None


def test_gate_open_wires_the_local_query_intent_model(tmp_path: Path, monkeypatch: Any) -> None:
    """Con la puerta abierta, el intérprete recibe el adaptador local — el
    MISMO modelo Ollama que ya usan el filtro de relevancia y el
    clasificador (D7 punto 5), nunca el proveedor de pago."""
    _patch_recorders(monkeypatch)
    save_settings({"category_matching_enabled": True})

    build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    assert _RecordingQueryIntentAdapter.captured == [_RELEVANCE_FILTER_MODEL]
    assert isinstance(
        _RecordingRankUseCase.captured[0]["query_request_interpreter"], InterpreteDePeticion
    )


# --------------------------------------------------------------------------
# Incidencia #603 (WI-20260913-PUERTA-1): la puerta única se parte en tres
# interruptores nombrados, todos apagados por defecto. Las siete pruebas de
# arriba quedan intactas a propósito: son la definición de «idéntico a hoy»,
# y si una sola de ellas hubiera tenido que cambiar, el cableado nuevo habría
# movido el estado cerrado —que es justo lo que este encargo prohíbe—.
# --------------------------------------------------------------------------


def _gate_snapshot() -> dict[str, Any]:
    """Lo único que las puertas pueden mover en la construcción.

    Compara valores, no objetos: los repositorios y el candidato del motor son
    instancias nuevas en cada construcción, así que una igualdad cruda entre
    dos ``kwargs`` completos sería siempre falsa y no diría nada. Lo que sí
    tiene que coincidir —y es lo que esta foto captura— es cada argumento que
    la puerta gobierna, más el hecho de que los dos que NO gobierna
    (``staged_engine_port`` y ``staged_engine_candidate``) siguen pasándose
    igual con la puerta abierta o cerrada.
    """
    rank_kwargs = _RecordingRankUseCase.captured[0]
    context_kwargs = _RecordingContextBuilder.captured[0]
    interprete = rank_kwargs["query_request_interpreter"]
    return {
        "category_vocabulary": rank_kwargs["category_vocabulary"],
        "criticality_vocabulary": rank_kwargs["criticality_vocabulary"],
        "rank_category_matching_enabled": rank_kwargs["category_matching_enabled"],
        "staged_engine_port": type(rank_kwargs["staged_engine_port"]).__name__,
        "staged_engine_candidate": type(rank_kwargs["staged_engine_candidate"]).__name__,
        "interprete": type(interprete).__name__,
        "intent_classifiers": list(_RecordingQueryIntentAdapter.captured),
        "relevance_filters": list(_RecordingRelevanceFilterAdapter.captured),
        "max_criticality_category": context_kwargs["max_criticality_category"],
        "context_category_matching_enabled": context_kwargs["category_matching_enabled"],
    }


def _build_with(settings: dict[str, Any], tmp_path: Path, monkeypatch: Any) -> dict[str, Any]:
    _patch_recorders(monkeypatch)
    save_settings(settings)

    build_conversation_dependencies(
        tmp_path / "sirius.db", tmp_path / "backups", secret_store=FakeSecretStore()
    )

    return _gate_snapshot()


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


def test_staged_engine_switch_alone_wires_only_the_engine(tmp_path: Path, monkeypatch: Any) -> None:
    """``staged_engine_enabled`` enciende el motor por etapas con sus dos
    vocabularios —y con ellos los índices de categoría y criticidad y la
    siembra M20—, y NADA más: el intérprete sigue sin clasificador y el
    ``ContextBuilder`` sigue en su camino de puerta cerrada."""
    snapshot = _build_with({"staged_engine_enabled": True}, tmp_path, monkeypatch)

    assert snapshot["category_vocabulary"] == _CATEGORY_VOCABULARY
    assert snapshot["criticality_vocabulary"] == _CRITICALITY_VOCABULARY
    assert snapshot["rank_category_matching_enabled"] is True
    # Los otros dos, en los valores de puerta cerrada.
    assert snapshot["intent_classifiers"] == []
    assert snapshot["relevance_filters"] == []
    assert _RecordingContextBuilder.captured[0]["relevance_filter_port"] is None
    assert snapshot["max_criticality_category"] is None
    assert snapshot["context_category_matching_enabled"] is False


def test_relevance_filter_switch_alone_wires_only_the_filter(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """``relevance_filter_enabled`` enciende el filtro local y el camino de
    puerta abierta del ``ContextBuilder`` —G8, cota dura y rescate por
    criticidad, con su techo—, y NADA más: el caso de uso sigue con los
    vocabularios vacíos y sin clasificador."""
    snapshot = _build_with({"relevance_filter_enabled": True}, tmp_path, monkeypatch)

    assert snapshot["relevance_filters"] == [
        (_RELEVANCE_FILTER_MODEL, _RELEVANCE_FILTER_TIMEOUT_SECONDS)
    ]
    assert isinstance(
        _RecordingContextBuilder.captured[0]["relevance_filter_port"],
        _RecordingRelevanceFilterAdapter,
    )
    assert snapshot["max_criticality_category"] == _MAX_CRITICALITY_CATEGORY
    assert snapshot["context_category_matching_enabled"] is True
    # Los otros dos, en los valores de puerta cerrada.
    assert snapshot["category_vocabulary"] == frozenset()
    assert snapshot["criticality_vocabulary"] == frozenset()
    assert snapshot["rank_category_matching_enabled"] is False
    assert snapshot["intent_classifiers"] == []


def test_query_intent_switch_with_the_engine_wires_only_the_interpreter(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """``query_intent_enabled`` sobre el motor encendido añade el clasificador
    local de ADR-164 —el MISMO modelo Ollama de D7 punto 5, nunca el
    proveedor de pago— y NADA más: el filtro de relevancia sigue sin
    construirse."""
    snapshot = _build_with(
        {"query_intent_enabled": True, "staged_engine_enabled": True}, tmp_path, monkeypatch
    )

    assert snapshot["intent_classifiers"] == [_RELEVANCE_FILTER_MODEL]
    assert snapshot["interprete"] == InterpreteDePeticion.__name__
    assert snapshot["rank_category_matching_enabled"] is True
    # El tercero, en los valores de puerta cerrada.
    assert snapshot["relevance_filters"] == []
    assert _RecordingContextBuilder.captured[0]["relevance_filter_port"] is None
    assert snapshot["max_criticality_category"] is None
    assert snapshot["context_category_matching_enabled"] is False


def test_query_intent_without_the_engine_never_builds_the_classifier(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Un interruptor nunca queda «encendido pero inerte»: el clasificador
    solo tiene efecto si el motor corre (``_peticion`` solo se llama desde
    ``_recuperar_por_etapas``), así que con ``query_intent_enabled`` a solas
    el adaptador ni se instancia y el intérprete emite la política uniforme
    de antes de ADR-164."""
    snapshot = _build_with({"query_intent_enabled": True}, tmp_path, monkeypatch)

    assert _RecordingQueryIntentAdapter.captured == []
    assert snapshot["rank_category_matching_enabled"] is False
    interprete = _RecordingRankUseCase.captured[0]["query_request_interpreter"]
    assert isinstance(interprete, InterpreteDePeticion)
    peticion = interprete.interpretar("consulta", "op-1", active_project_id=None)
    assert peticion.modo is Modo.M1_ORDINARIO
    assert peticion.cardinalidad is Cardinalidad.EXHAUSTIVA
    assert peticion.ventana.corte_de_registro is None


def test_the_master_key_alone_equals_the_three_switches_together(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """§6.3 intacto: ``category_matching_enabled`` sigue significando
    exactamente «las tres piezas», ni una más ni una menos."""
    maestra = _build_with({"category_matching_enabled": True}, tmp_path / "a", monkeypatch)
    tres = _build_with(
        {
            "staged_engine_enabled": True,
            "query_intent_enabled": True,
            "relevance_filter_enabled": True,
        },
        tmp_path / "b",
        monkeypatch,
    )

    assert maestra == tres


def test_all_four_keys_false_builds_exactly_todays_closed_construction(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Identidad cerrada con las cuatro claves escritas en ``False``: la misma
    foto que sin ninguna clave en absoluto."""
    sin_claves = _build_with({}, tmp_path / "a", monkeypatch)
    cuatro_en_false = _build_with(
        {
            "category_matching_enabled": False,
            "staged_engine_enabled": False,
            "query_intent_enabled": False,
            "relevance_filter_enabled": False,
        },
        tmp_path / "b",
        monkeypatch,
    )

    assert cuatro_en_false == sin_claves
    assert cuatro_en_false["category_vocabulary"] == frozenset()
    assert cuatro_en_false["rank_category_matching_enabled"] is False
    assert cuatro_en_false["relevance_filters"] == []
    assert cuatro_en_false["intent_classifiers"] == []
    assert cuatro_en_false["max_criticality_category"] is None
    assert cuatro_en_false["context_category_matching_enabled"] is False


def test_a_truthy_non_boolean_value_leaves_each_new_switch_closed(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """La regla de la incidencia #471/CODEX-001 se hereda tal cual en las tres
    claves nuevas: una edición manual que deje ``"true"`` o ``1`` no abre
    nada, aunque sea truthy en Python."""
    sin_claves = _build_with({}, tmp_path / "cerrada", monkeypatch)
    for indice, clave in enumerate(
        ("staged_engine_enabled", "query_intent_enabled", "relevance_filter_enabled")
    ):
        for valor in ("true", 1):
            snapshot = _build_with(
                {clave: valor}, tmp_path / f"{clave}-{indice}-{valor}", monkeypatch
            )
            assert snapshot == sin_claves, (clave, valor)
