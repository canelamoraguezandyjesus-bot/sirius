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

#: Esquema que el servidor impone AL GENERAR, portado literal del laboratorio
#: (``experiments/adr002/modelo_local/filtro.py:139``, rama
#: ``evidence/adr001-spikes``). El laboratorio lo declara necesario, no
#: cosmético: «la versión anterior pedía el formato por escrito en la
#: instrucción y confiaba en que el modelo obedeciera; con un modelo pequeño
#: eso falla».
_ESQUEMA_RESPUESTA: dict[str, object] = {
    "type": "object",
    "properties": {"responden": {"type": "array", "items": {"type": "integer"}}},
    "required": ["responden"],
}

#: Instrucción portada literal del laboratorio (``filtro.py:148``). Cada regla
#: corresponde a un caso medido del banco de 47; no es prosa decorativa.
_INSTRUCCION = (
    "Eres el filtro de relevancia de una memoria personal. Recibes una PREGUNTA "
    "y una lista numerada de FRASES guardadas. Dices cuales responden a la "
    "pregunta.\n\n"
    "Reglas:\n"
    "- Devuelve solo los numeros de las frases que responden a la pregunta.\n"
    "- Una prohibicion SI responde a una pregunta sobre si algo se puede hacer: "
    "a «¿puedo usar vuelos con escala?», la frase «no uses vuelos con escala» "
    "es la respuesta, y es que no. Incluyela.\n"
    "- Si hay dos frases opuestas sobre lo mismo, devuelve LAS DOS: quien "
    "pregunta tiene que ver que hay un permiso y una prohibicion.\n"
    "- Respeta el tiempo: si preguntan solo por lo ANTERIOR, lo vigente no "
    "responde; si preguntan solo por lo vigente, lo derogado no responde. Pero "
    "si piden LAS DOS —«cual es la actual y cual reemplazo»—, devuelve las dos.\n"
    "- Si la pregunta pide VARIAS cosas o una lista —«todas las restricciones», "
    "«el presupuesto y la preferencia»—, devuelve TODAS las frases que hagan "
    "falta. No elijas la mejor: la respuesta completa son todas.\n"
    "- Frases parecidas entre si NO son repeticiones. Si cinco frases dicen "
    "«restriccion numero 1», «numero 2»... y la pregunta las pide, son cinco "
    "respuestas distintas y van las cinco.\n"
    "- Una frase que habla del mismo tema pero no responde a la pregunta no "
    "cuenta.\n"
    "- Si ninguna frase responde, devuelve la lista vacia.\n"
    "- Ante duda razonable, incluyela: es peor perder algo importante que "
    "entregar de mas."
)

#: Apaga el modo razonador. Sin esto, un modelo de la familia Qwen3 escribe su
#: pensamiento antes de contestar y la tarea pasa de segundos a minutos
#: (``puerto.py:316``).
_PENSAMIENTO_APAGADO = False
#: El laboratorio midió con estos valores (``puerto.py:78-86``).
_TEMPERATURA = 0.1
_TAMANO_DE_CONTEXTO = 8192
_PERMANENCIA_DEL_MODELO = "15m"


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
            # ``follow_redirects=False`` overrides any injected client that
            # sets ``follow_redirects=True``: a 307/308 from localhost must
            # never resend this request (and its body) to a remote host.
            response = self._client.post(
                f"{_OLLAMA_LOCAL_BASE_URL}/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": _INSTRUCCION},
                        {"role": "user", "content": _build_entry(query_text, candidates)},
                    ],
                    "stream": False,
                    "format": dict(_ESQUEMA_RESPUESTA),
                    "think": _PENSAMIENTO_APAGADO,
                    "keep_alive": _PERMANENCIA_DEL_MODELO,
                    "options": {
                        "temperature": _TEMPERATURA,
                        "num_ctx": _TAMANO_DE_CONTEXTO,
                    },
                },
                follow_redirects=False,
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


def _build_entry(query_text: str, candidates: Sequence[RankedKnowledge]) -> str:
    items = "\n".join(
        f"{position}. {candidate.item.current_revision.content}"
        for position, candidate in enumerate(candidates, start=1)
    )
    return f"Pregunta: {query_text}\n\nFrases guardadas:\n{items}"


def _parse_kept_positions(payload: object, candidate_count: int) -> set[int]:
    if not isinstance(payload, dict):
        msg = "la respuesta de Ollama no es un objeto JSON"
        raise ValueError(msg)
    message = payload.get("message")
    raw_text = message.get("content") if isinstance(message, dict) else None
    if not isinstance(raw_text, str) or not raw_text.strip():
        msg = "la respuesta de Ollama no trae 'message.content'"
        raise ValueError(msg)
    decision = json.loads(raw_text)
    if not isinstance(decision, dict):
        msg = "el texto del modelo no es un objeto JSON"
        raise ValueError(msg)
    kept = decision.get("responden")
    if not isinstance(kept, list) or not all(
        isinstance(value, int) and not isinstance(value, bool) for value in kept
    ):
        msg = "'responden' no es una lista de enteros"
        raise ValueError(msg)
    if any(value < 1 or value > candidate_count for value in kept):
        msg = "'responden' referencia una posición fuera de rango"
        raise ValueError(msg)
    return set(kept)
