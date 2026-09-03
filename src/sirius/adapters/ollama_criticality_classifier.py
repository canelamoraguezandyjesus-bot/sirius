"""Local-only Ollama adapter for automatic criticality proposal (M21a,
ADR-130).

Points exclusively at ``localhost``, with no constructor parameter that could
redirect it to a remote host, and fails open on every kind of problem —
Ollama not installed, connection refused, timed out, or a response outside
the closed vocabulary — by returning ``None``, never raising. The model is
asked for exactly one of three levels (CRITICO, IMPORTANTE, ORDINARIO);
ORDINARIO and anything else become ``None`` — only CRITICO/IMPORTANTE are
proposals (D7, SIRIUS-ARQ-0.2 §6.1's fail-open contract, mirrored here for
criticality).

The HTTP contract is the one this repository already validated against the
real local model (ADR-125, ``OllamaRelevanceFilterAdapter``): ``/api/chat``
with reasoning explicitly switched off (``think: false``), a closed JSON
schema for the answer (``format``), a low temperature and ``keep_alive`` —
not ``/api/generate`` with a free-text prompt, which with the default Qwen3
model reasons for minutes and answers outside the vocabulary (ADR-125;
CODEX-001 of incidencia #518). The request goes to an absolute localhost URL
with ``follow_redirects=False`` for the same reason the relevance filter
does (CODEX-001 of PR #452): neither an injected client's ``base_url`` nor a
307/308 from localhost may ever carry a memory's content off the machine.
"""

from __future__ import annotations

import json

import httpx

from sirius.domain.criticality import Criticality
from sirius.infrastructure.logging import get_logger

__all__ = ["OllamaCriticalityClassifierAdapter"]

_logger = get_logger(__name__)

_OLLAMA_LOCAL_BASE_URL = "http://localhost:11434"
#: Same ceiling as the relevance filter's client (ADR-125): the only value
#: this repository has measured for this model with ``think: false``. The
#: real cost of a criticality proposal is for the owner to measure in use
#: (M21b); a cold model load is the case a shorter ceiling would cut off.
_REQUEST_TIMEOUT_SECONDS = 30.0

_ORDINARIO = "ORDINARIO"
_NIVELES = (Criticality.CRITICO.value, Criticality.IMPORTANTE.value, _ORDINARIO)
_VOCABULARY = frozenset(_NIVELES)

#: Closed answer schema: Ollama constrains the model's output to it, so the
#: answer is one of the three levels by construction, never prose around it.
_ESQUEMA_RESPUESTA: dict[str, object] = {
    "type": "object",
    "properties": {"nivel": {"type": "string", "enum": list(_NIVELES)}},
    "required": ["nivel"],
}

_INSTRUCCION = (
    "Eres el clasificador de criticidad de una memoria personal. Recibes el "
    "contenido de un recuerdo o de una decision y dices cuanto importa que no "
    "se pierda.\n\n"
    "Niveles:\n"
    "- CRITICO: perderlo o contradecirlo causa un dano real: prohibiciones, "
    "salud, seguridad, dinero, plazos legales, compromisos que no admiten "
    "excepcion.\n"
    "- IMPORTANTE: conviene tenerlo presente cuando venga al caso: "
    "preferencias firmes, acuerdos, restricciones de trabajo, datos que se "
    "consultan a menudo.\n"
    "- ORDINARIO: todo lo demas.\n\n"
    "Responde solo con el nivel, en el formato pedido."
)

#: Reasoning explicitly off: with it on, the default Qwen3 model takes minutes
#: to answer a one-word question (ADR-125).
_PENSAMIENTO_APAGADO = False
_TEMPERATURA = 0.1
_TAMANO_DE_CONTEXTO = 8192
_PERMANENCIA_DEL_MODELO = "15m"


class OllamaCriticalityClassifierAdapter:
    """Implements ``CriticalityClassifierPort`` against a local Ollama model."""

    def __init__(self, model: str, *, client: httpx.Client | None = None) -> None:
        self._model = model
        # ``client`` exists only as a test seam (an ``httpx.MockTransport``
        # never leaves the process); production code always falls back to a
        # client hardcoded to localhost — no parameter anywhere accepts a
        # remote host, and ``propose`` never trusts the client's ``base_url``.
        self._client = client or httpx.Client(
            base_url=_OLLAMA_LOCAL_BASE_URL, timeout=_REQUEST_TIMEOUT_SECONDS
        )

    def propose(self, content: str) -> Criticality | None:
        try:
            # Absolute URL, not a path relative to ``self._client``'s own
            # ``base_url``: an injected client's ``base_url`` must never be
            # able to redirect the actual request away from localhost.
            # ``follow_redirects=False`` overrides any injected client that
            # sets ``follow_redirects=True``: a 307/308 from localhost must
            # never resend this request (and the content) to a remote host.
            response = self._client.post(
                f"{_OLLAMA_LOCAL_BASE_URL}/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": _INSTRUCCION},
                        {"role": "user", "content": content},
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
            candidate = _parse_level(response.json())
        except Exception as exc:  # Fails open by contract (CriticalityClassifierPort).
            _logger.warning(
                "Propuesta de criticidad no disponible, se falla abierto (%s)",
                type(exc).__name__,
            )
            return None
        if candidate not in _VOCABULARY or candidate == _ORDINARIO:
            return None
        return Criticality(candidate)


def _parse_level(payload: object) -> str:
    """Extract the level from an ``/api/chat`` answer constrained by
    ``_ESQUEMA_RESPUESTA``. Anything unexpected raises, and ``propose``
    turns that into ``None`` like every other failure."""
    if not isinstance(payload, dict):
        raise ValueError("respuesta de Ollama sin objeto")
    message = payload.get("message")
    if not isinstance(message, dict):
        raise ValueError("respuesta de Ollama sin message")
    answer = json.loads(str(message.get("content", "")))
    if not isinstance(answer, dict):
        raise ValueError("respuesta de Ollama fuera del esquema")
    return str(answer.get("nivel", "")).strip()
