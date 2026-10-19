"""Lo que el modelo lee de quién hay: quién le habla y a quiénes tiene delante (pieza E de
la 0.4, ADR-263).

Va en las instrucciones de cada petición, en «# Quién hay», detrás de lo que sabe y antes
del recordatorio. Quien no ha dado permiso para que le reconozca es «alguien sin
identificar»: el modelo no le pone nombre, aunque se lo diga.

- **Quién le habla** solo en un turno de voz, de la voz de ese turno. Lo escrito en la
  ventana no lleva quién lo escribe: la vista no sabe quién teclea.
- **A quiénes tiene delante**, de lo último que vio la cámara, uno por línea; sin cámara,
  nada, que no sabe quién hay.
- **Un nombre solo va si quien lo lleva tiene permiso al escribir la petición**: el de
  quien lo quitó después de que se le reconociera, por la voz o por la cara, es alguien
  sin identificar (ronda 3 de Codex sobre la PR #703).
"""

from __future__ import annotations

from collections.abc import Collection, Sequence

from sirius.application.recognition import UNKNOWN

#: Cómo se nombra a quien no se sabe quién es.
SOMEONE = "alguien sin identificar"
#: El título de la sección.
HEADING = "# Quién hay"
#: Cómo se dice quién le habla, a quién tiene delante y que no tiene a nadie.
SPEAKER_LINE = "Te habla {who}."
IN_FRONT_LINE = "Tienes delante a {who}."
NOBODY_LINE = "No tienes a nadie delante."
#: Lo que lleva siempre la sección.
RULE = (
    "Solo reconoces, por la cara y por la voz, a quien te ha dado permiso para reconocerle. "
    "A los demás no los reconoces: son alguien sin identificar, y aunque te digan quiénes "
    "son, no dices que los reconoces."
)


def presence_block(
    *, speaker: str | None, in_front: Sequence[str | None] | None, allowed: Collection[str]
) -> str:
    """La sección «# Quién hay»; vacía si no hay nada que decir.

    ``speaker`` es quien habla en un turno de voz, su nombre o «sin identificar»; ``None``
    si no es un turno de voz. ``in_front``, quiénes ve la cámara, su nombre o ``None`` por
    cada uno; ``None`` si no ve. ``allowed``, quiénes tienen permiso ahora: el nombre de
    quien no está ahí es alguien sin identificar.
    """
    lines: list[str] = []
    if speaker is not None:
        lines.append(SPEAKER_LINE.format(who=_named(speaker, allowed)))
    if in_front is not None:
        if not in_front:
            lines.append(NOBODY_LINE)
        lines.extend(
            IN_FRONT_LINE.format(who=_named(who, allowed)) for who in _ordered(in_front, allowed)
        )
    if not lines:
        return ""
    return "\n".join([HEADING, *lines, RULE])


def _named(who: str | None, allowed: Collection[str]) -> str:
    return who if who is not None and _has_name(who, allowed) else SOMEONE


def _has_name(who: str | None, allowed: Collection[str]) -> bool:
    """Si ``who`` se dice por su nombre: lo tiene, y tiene permiso ahora."""
    return who is not None and who != UNKNOWN and who in allowed


def _ordered(in_front: Sequence[str | None], allowed: Collection[str]) -> list[str | None]:
    """Primero los que tienen nombre, por orden, y después los que no."""
    named = sorted(who for who in in_front if who is not None and _has_name(who, allowed))
    return [*named, *(None for who in in_front if not _has_name(who, allowed))]
