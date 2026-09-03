"""Local-only Ollama adapter for automatic criticality proposal (M21a,
ADR-130).

Calcado de ``OllamaCategoryClassifierAdapter``: points exclusively at
``localhost``, with no constructor parameter that could redirect it to a
remote host, and fails open on every kind of problem — Ollama not installed,
connection refused, timed out, or a response outside the two-level
vocabulary — by returning ``None``, never raising. The model is asked for
exactly one of three words (CRITICO, IMPORTANTE, ORDINARIO); ORDINARIO and
anything else become ``None`` — only CRITICO/IMPORTANTE are proposals (D7,
SIRIUS-ARQ-0.2 §6.1's fail-open contract, mirrored here for criticality).
"""

from __future__ import annotations

import httpx

from sirius.domain.criticality import Criticality
from sirius.infrastructure.logging import get_logger

__all__ = ["OllamaCriticalityClassifierAdapter"]

_logger = get_logger(__name__)

_OLLAMA_LOCAL_BASE_URL = "http://localhost:11434"
_REQUEST_TIMEOUT_SECONDS = 5.0

_ORDINARIO = "ORDINARIO"
_VOCABULARY = frozenset({Criticality.CRITICO.value, Criticality.IMPORTANTE.value, _ORDINARIO})


class OllamaCriticalityClassifierAdapter:
    """Implements ``CriticalityClassifierPort`` against a local Ollama model."""

    def __init__(self, model: str, *, client: httpx.Client | None = None) -> None:
        self._model = model
        # ``client`` exists only as a test seam (an ``httpx.MockTransport``
        # never leaves the process); production code always falls back to a
        # client hardcoded to localhost — no parameter anywhere accepts a
        # remote host.
        self._client = client or httpx.Client(
            base_url=_OLLAMA_LOCAL_BASE_URL, timeout=_REQUEST_TIMEOUT_SECONDS
        )

    def propose(self, content: str) -> Criticality | None:
        try:
            response = self._client.post(
                "/api/generate",
                json={
                    "model": self._model,
                    "prompt": _build_prompt(content),
                    "stream": False,
                },
            )
            response.raise_for_status()
            candidate = str(response.json().get("response", "")).strip()
        except Exception as exc:  # Fails open by contract (CriticalityClassifierPort).
            _logger.warning(
                "Propuesta de criticidad no disponible, se falla abierto (%s)",
                type(exc).__name__,
            )
            return None
        if candidate not in _VOCABULARY or candidate == _ORDINARIO:
            return None
        return Criticality(candidate)


def _build_prompt(content: str) -> str:
    return (
        "Clasifica el siguiente contenido en exactamente una de estas "
        "opciones: CRITICO, IMPORTANTE, ORDINARIO. Responde únicamente con "
        "el nombre exacto de la opción, sin explicación.\n\nContenido:\n"
        f"{content}"
    )
