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

from pathlib import Path
from typing import Any, ClassVar

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
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.composition_root import (
    _CATEGORY_VOCABULARY,
    _MAX_CRITICALITY_CATEGORY,
    _RELEVANCE_FILTER_MODEL,
    _RELEVANCE_FILTER_TIMEOUT_SECONDS,
    build_conversation_dependencies,
)
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


class _RecordingRelevanceFilterAdapter:
    """Stands in for ``OllamaRelevanceFilterAdapter``: never touches the
    network, just records the constructor arguments composition_root passed
    and behaves like a filter that never excludes anything, so the rest of
    the wiring still completes normally."""

    captured: ClassVar[list[tuple[str, float]]] = []

    def __init__(self, model: str, *, timeout_seconds: float) -> None:
        type(self).captured.append((model, timeout_seconds))

    def filter_candidates(
        self, query_text: str, candidates: Any
    ) -> Any:  # pragma: no cover - never exercised here
        return candidates


def _patch_recorders(monkeypatch: Any) -> None:
    _RecordingRankUseCase.captured = []
    _RecordingContextBuilder.captured = []
    _RecordingRelevanceFilterAdapter.captured = []
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
