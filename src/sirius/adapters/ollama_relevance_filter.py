"""Local-only Ollama adapter for the relevance filter (D7, SIRIUS-ARQ-0.2 §6.3).

Mirrors ``OllamaCategoryClassifierAdapter``'s structural property: points
exclusively at ``localhost``, with no constructor parameter that could
redirect it to a remote host, and fails open on every kind of problem —
Ollama not installed, connection refused, accepted-but-never-answered until
the time budget is exhausted, or a response outside the expected shape — by
returning ``candidates`` unmodified, never raising. The candado that
protects a critical or not-yet-classified candidate from this filter's
verdict is deliberately not this adapter's job — see
``ContextBuilder._rank_related_knowledge`` (§6.3): "the filter with a model
never decides alone".
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import httpx

from sirius.domain.relevance import RankedKnowledge
from sirius.infrastructure.logging import get_logger

__all__ = ["OllamaRelevanceFilterAdapter"]

_logger = get_logger(__name__)

_OLLAMA_LOCAL_BASE_URL = "http://localhost:11434"
_DEFAULT_TIMEOUT_SECONDS = 5.0


class OllamaRelevanceFilterAdapter:
    """Implements ``RelevanceFilterPort`` against a local Ollama model."""

    def __init__(
        self,
        model: str,
        *,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        client: httpx.Client | None = None,
    ) -> None:
        self._model = model
        # ``client`` exists only as a test seam (an ``httpx.MockTransport``
        # never leaves the process); production code always falls back to a
        # client hardcoded to localhost — no parameter anywhere accepts a
        # remote host. ``timeout_seconds`` only shapes that fallback client;
        # M11 (§6.4) is the one that measures and fixes its real value.
        self._client = client or httpx.Client(
            base_url=_OLLAMA_LOCAL_BASE_URL, timeout=timeout_seconds
        )

    def filter_candidates(
        self, query_text: str, candidates: Sequence[RankedKnowledge]
    ) -> Sequence[RankedKnowledge]:
        if not candidates:
            return candidates
        try:
            # Absolute URL, not a path relative to ``self._client``'s own
            # ``base_url``: an injected client's ``base_url`` must never be
            # able to redirect the actual request away from localhost.
            response = self._client.post(
                f"{_OLLAMA_LOCAL_BASE_URL}/api/generate",
                json={
                    "model": self._model,
                    "prompt": _build_prompt(query_text, candidates),
                    "stream": False,
                },
            )
            response.raise_for_status()
            kept_positions = _parse_kept_positions(response.json(), len(candidates))
        except Exception as exc:  # Fails open by contract (RelevanceFilterPort).
            _logger.warning(
                "Filtro de relevancia no disponible, se falla abierto (%s)",
                type(exc).__name__,
            )
            return candidates
        return tuple(
            candidate
            for position, candidate in enumerate(candidates, start=1)
            if position in kept_positions
        )


def _build_prompt(query_text: str, candidates: Sequence[RankedKnowledge]) -> str:
    items = "\n".join(
        f"{position}. {candidate.item.current_revision.content}"
        for position, candidate in enumerate(candidates, start=1)
    )
    return (
        "Dada la consulta y la lista numerada de candidatos, responde "
        'únicamente con un JSON de la forma {"keep": [n, ...]} con los '
        "números de los candidatos relevantes para la consulta. Incluye "
        "solo los relevantes; omite el resto.\n\n"
        f"Consulta: {query_text}\n\nCandidatos:\n{items}"
    )


def _parse_kept_positions(payload: object, candidate_count: int) -> set[int]:
    if not isinstance(payload, dict):
        msg = "la respuesta de Ollama no es un objeto JSON"
        raise ValueError(msg)
    raw_text = payload.get("response")
    if not isinstance(raw_text, str):
        msg = "la respuesta de Ollama no trae el campo 'response'"
        raise ValueError(msg)
    decision = json.loads(raw_text)
    if not isinstance(decision, dict):
        msg = "el texto del modelo no es un objeto JSON"
        raise ValueError(msg)
    kept = decision.get("keep")
    if not isinstance(kept, list) or not all(
        isinstance(value, int) and not isinstance(value, bool) for value in kept
    ):
        msg = "'keep' no es una lista de enteros"
        raise ValueError(msg)
    if any(value < 1 or value > candidate_count for value in kept):
        msg = "'keep' referencia una posición fuera de rango"
        raise ValueError(msg)
    return set(kept)
