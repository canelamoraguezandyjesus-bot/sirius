"""Los ejemplos de la semilla que ve cada petición (ADR-240)."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field

import pytest

from sirius.application.memory_search import EMBED_BATCH
from sirius.application.seed_examples import SHOWN, SeedExamplePicker, _cosine
from sirius.domain.identity import SeedExample

_EJEMPLOS = tuple(
    SeedExample("Él", dicho, f"Respuesta a «{dicho}».")
    for dicho in (
        "Me voy a pedir otra pizza.",
        "Se ha muerto mi abuelo esta mañana.",
        "¿Qué tiempo va a hacer mañana?",
        "Dime algo bonito.",
        "Ayúdame a arreglar este código, que no compila.",
        "Te presento a mi abuela.",
    )
)


@dataclass
class _Huellas:
    """Hace del servicio de huellas: cada texto tiene la suya, fija."""

    huellas: dict[str, list[float]]
    modelo: str = "huellas"
    sin_pregunta: bool = False
    sin_textos: bool = False
    #: La tanda, desde 1, que falla una vez.
    falla_la_tanda: int | None = None
    preguntas: list[str] = field(default_factory=list)
    textos: list[list[str]] = field(default_factory=list)

    @property
    def query_model_name(self) -> str:
        return self.modelo

    def embed_query(self, query_text: str) -> list[float] | None:
        self.preguntas.append(query_text)
        return None if self.sin_pregunta else self.huellas[query_text]

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]] | None:
        self.textos.append(list(texts))
        if len(self.textos) == self.falla_la_tanda:
            self.falla_la_tanda = None
            return None
        return None if self.sin_textos else [self.huellas[t] for t in texts]


def _huellas(pregunta: str, cercanos: Sequence[int]) -> _Huellas:
    """``pregunta`` se parece a los ejemplos ``cercanos``, más al primero, y a nada más."""
    huellas = {pregunta: [1.0, 0.0, 0.0]}
    for posicion, ejemplo in enumerate(_EJEMPLOS):
        if posicion in cercanos:
            parecido = 1.0 - 0.1 * cercanos.index(posicion)
            huellas[ejemplo.said] = [parecido, 1.0 - parecido, 0.0]
        else:
            huellas[ejemplo.said] = [0.0, 0.0, 1.0]
    return _Huellas(huellas)


def _selector(huellas: _Huellas | None = None, semilla: int = 1) -> SeedExamplePicker:
    return SeedExamplePicker(huellas, rng=random.Random(semilla))  # type: ignore[arg-type]


def test_nunca_lleva_mas_de_tres() -> None:
    assert SHOWN == 3
    assert len(_selector().pick(_EJEMPLOS, "hola")) == SHOWN


@pytest.mark.parametrize("cuantos", [0, 1, 2, 3])
def test_con_tres_o_menos_van_todos(cuantos: int) -> None:
    elegidos = _selector().pick(_EJEMPLOS[:cuantos], "hola")

    assert sorted(elegidos, key=_EJEMPLOS.index) == list(_EJEMPLOS[:cuantos])


def test_por_significado_van_los_tres_que_mas_se_parecen() -> None:
    huellas = _huellas("Hoy estoy hecho polvo.", cercanos=[1, 3, 5])

    elegidos = _selector(huellas).pick(_EJEMPLOS, "Hoy estoy hecho polvo.")

    assert {e.said for e in elegidos} == {_EJEMPLOS[i].said for i in (1, 3, 5)}


def test_cuarto_por_parecido_se_queda_fuera() -> None:
    huellas = _huellas("Hoy estoy hecho polvo.", cercanos=[4, 0, 2, 5])

    elegidos = _selector(huellas).pick(_EJEMPLOS, "Hoy estoy hecho polvo.")

    assert _EJEMPLOS[5] not in elegidos
    assert set(elegidos) == {_EJEMPLOS[4], _EJEMPLOS[0], _EJEMPLOS[2]}


def test_las_huellas_de_los_ejemplos_se_piden_una_vez() -> None:
    huellas = _huellas("Hoy estoy hecho polvo.", cercanos=[1, 3, 5])
    selector = _selector(huellas)

    selector.pick(_EJEMPLOS, "Hoy estoy hecho polvo.")
    selector.pick(_EJEMPLOS, "Hoy estoy hecho polvo.")

    pedidos = [said for tanda in huellas.textos for said in tanda]
    assert sorted(pedidos) == sorted(e.said for e in _EJEMPLOS)
    assert all(len(tanda) <= EMBED_BATCH for tanda in huellas.textos)
    assert huellas.preguntas == ["Hoy estoy hecho polvo."] * 2


def test_si_una_tanda_falla_se_queda_lo_calculado_y_la_siguiente_vez_pide_solo_lo_que_falta() -> (
    None
):
    huellas = _huellas("Hoy estoy hecho polvo.", cercanos=[1, 3, 5])
    huellas.falla_la_tanda = 2
    selector = _selector(huellas)

    assert len(selector.pick(_EJEMPLOS, "Hoy estoy hecho polvo.")) == SHOWN
    primera_tanda = huellas.textos[0]

    elegidos = selector.pick(_EJEMPLOS, "Hoy estoy hecho polvo.")

    assert {e.said for e in elegidos} == {_EJEMPLOS[i].said for i in (1, 3, 5)}
    pedidos_despues = [said for tanda in huellas.textos[1:] for said in tanda]
    assert not set(primera_tanda) & set(pedidos_despues)


def test_sin_huella_de_la_pregunta_van_por_palabras_en_comun() -> None:
    huellas = _huellas("x", cercanos=[1, 3, 5])
    huellas.sin_pregunta = True

    elegidos = _selector(huellas).pick(_EJEMPLOS, "Me voy a pedir otra pizza familiar.")

    assert _EJEMPLOS[0] in elegidos
    assert huellas.textos == [], "sin la de la pregunta no se piden las de los ejemplos"


def test_sin_huellas_de_los_ejemplos_van_por_palabras_y_se_vuelven_a_pedir_despues() -> None:
    huellas = _huellas("Me voy a pedir otra pizza familiar.", cercanos=[1, 3, 5])
    huellas.sin_textos = True
    selector = _selector(huellas)

    assert _EJEMPLOS[0] in selector.pick(_EJEMPLOS, "Me voy a pedir otra pizza familiar.")

    huellas.sin_textos = False
    elegidos = selector.pick(_EJEMPLOS, "Me voy a pedir otra pizza familiar.")
    assert {e.said for e in elegidos} == {_EJEMPLOS[i].said for i in (1, 3, 5)}


def test_sin_servicio_de_huellas_van_por_palabras_en_comun() -> None:
    elegidos = _selector().pick(_EJEMPLOS, "¿Mañana qué tiempo hará?")

    assert _EJEMPLOS[2] in elegidos


def test_sin_palabras_en_comun_los_elige_el_azar() -> None:
    vistos = {frozenset(_selector(semilla=semilla).pick(_EJEMPLOS, "zzz")) for semilla in range(20)}

    assert len(vistos) > 1


def test_los_mismos_tres_salen_en_distinto_orden() -> None:
    huellas = _huellas("Hoy estoy hecho polvo.", cercanos=[1, 3, 5])
    selector = _selector(huellas)

    ordenes = {selector.pick(_EJEMPLOS, "Hoy estoy hecho polvo.") for _ in range(12)}

    assert {frozenset(orden) for orden in ordenes} == {frozenset(_EJEMPLOS[i] for i in (1, 3, 5))}
    assert len(ordenes) > 1


def test_el_coseno_tolera_huellas_de_distinto_largo_y_vacias() -> None:
    assert _cosine([1.0, 0.0], [1.0]) == pytest.approx(1.0)
    assert _cosine([0.0, 1.0], [1.0]) == 0.0
    assert _cosine([0.0], [1.0]) == 0.0
