"""Las divergencias que el reflector aparta, conservadas entre pasadas (ADR-227, H-216).

La regla de retención es pura y se prueba sola; el cableado en ``sirius-reflejar``
lo prueba ``test_reflect_cli.py`` y la vista, ``test_memoria.py``. La instantánea
sabe además cuánto se puede fiar uno de ella (ronda 2 de Codex en la PR #674).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius_engine.divergencias import (
    FICHERO_DIVERGENCIAS,
    DivergenciaApartada,
    DivergenciaVista,
    Instantanea,
    actualizar,
    cerrar_pasada,
    escribir_instantanea,
    leer_instantanea,
    ruta_de_divergencias,
)

_T1 = datetime(2026, 8, 29, 3, 24, tzinfo=UTC)
_T2 = datetime(2026, 9, 25, 3, 24, tzinfo=UTC)
_VISTA = DivergenciaVista("WI-20260828-122242", 392, "etiquetas que se contradicen")


def _completa(*divergencias: DivergenciaApartada) -> Instantanea:
    return Instantanea(
        tuple(divergencias), interrumpida=False, sin_evaluar=(), perdida_posible=False
    )


def test_una_divergencia_nueva_nace_con_su_primera_vez_y_al_repetirse_la_conserva() -> None:
    primera = actualizar((), [_VISTA], sin_evaluar=(), ahora=_T1)
    assert primera == (
        DivergenciaApartada(
            "WI-20260828-122242",
            392,
            "etiquetas que se contradicen",
            _T1.isoformat(),
            _T1.isoformat(),
            1,
        ),
    )
    segunda = actualizar(primera, [_VISTA], sin_evaluar=(), ahora=_T2)
    assert segunda[0].primera_vez == _T1.isoformat()
    assert segunda[0].ultima_vez == _T2.isoformat()
    assert segunda[0].pasadas == 2


def test_una_entrada_que_la_pasada_evaluo_sin_divergencia_se_retira() -> None:
    anteriores = actualizar((), [_VISTA], sin_evaluar=(), ahora=_T1)
    assert actualizar(anteriores, [], sin_evaluar=(), ahora=_T2) == ()


def test_una_entrada_cuyo_encargo_no_se_pudo_leer_se_conserva_tal_cual() -> None:
    """No saber no es saber que se resolvió: una incidencia ilegible esta pasada
    deja la entrada con su última fecha, no la borra."""
    anteriores = actualizar((), [_VISTA], sin_evaluar=(), ahora=_T1)
    conservadas = actualizar(anteriores, [], sin_evaluar={"WI-20260828-122242"}, ahora=_T2)
    assert conservadas == anteriores


def test_leer_y_escribir_van_y_vuelven_y_sin_fichero_no_hay_instantanea(tmp_path: Path) -> None:
    ruta = ruta_de_divergencias(tmp_path / "diario.jsonl")
    assert ruta.name == FICHERO_DIVERGENCIAS
    assert leer_instantanea(ruta) is None, "sin fichero no hay «ninguna»: hay «nadie escribió»"
    apartadas = actualizar(
        (), [_VISTA, DivergenciaVista("WI-0", None, "hacia atrás")], sin_evaluar=(), ahora=_T1
    )
    instantanea = Instantanea(
        apartadas, interrumpida=True, sin_evaluar=("WI-9", "WI-7"), perdida_posible=True
    )
    escribir_instantanea(ruta, instantanea)
    leida = leer_instantanea(ruta)
    assert leida is not None
    assert leida.divergencias == apartadas and leida.interrumpida and leida.perdida_posible
    assert leida.sin_evaluar == ("WI-7", "WI-9"), "ordenados, para que el fichero sea estable"
    assert leida.completa is False
    assert [d.work_id for d in apartadas] == ["WI-0", "WI-20260828-122242"], "ordenadas por encargo"
    assert not ruta.with_name(ruta.name + ".tmp").exists(), (
        "se escribe en un temporal y se sustituye entero: ninguna pasada deja un JSON a medias"
    )


@pytest.mark.parametrize(
    "texto",
    [
        "[]",
        "{}",
        '{"divergencias": []}',
        '{"pasada": {}, "divergencias": []}',
        '{"pasada": {"interrumpida": false, "sin_evaluar": [], "perdida_posible": false}, '
        '"divergencias": [{"work_id": "WI-1"}]}',
        '{"divergencias": [',
        # Metadatos con el tipo equivocado: coercionarlos haría pasar por
        # completa una pasada corrupta (ronda 3 de Codex en la PR #674).
        '{"pasada": {"interrumpida": "", "sin_evaluar": [], "perdida_posible": false}, '
        '"divergencias": []}',
        '{"pasada": {"interrumpida": false, "sin_evaluar": "", "perdida_posible": false}, '
        '"divergencias": []}',
        '{"pasada": {"interrumpida": false, "sin_evaluar": [1], "perdida_posible": false}, '
        '"divergencias": []}',
        '{"pasada": {"interrumpida": false, "sin_evaluar": [], "perdida_posible": "no"}, '
        '"divergencias": []}',
        '{"pasada": {"interrumpida": 0, "sin_evaluar": [], "perdida_posible": false}, '
        '"divergencias": []}',
    ],
)
def test_un_fichero_que_no_tiene_la_forma_se_declara_en_vez_de_leerse_como_vacio(
    tmp_path: Path, texto: str
) -> None:
    ruta = tmp_path / FICHERO_DIVERGENCIAS
    ruta.write_text(texto, encoding="utf-8")
    with pytest.raises(ValueError, match=FICHERO_DIVERGENCIAS):
        leer_instantanea(ruta)


# --- Cuánto se puede fiar uno de la instantánea (ronda 2 de Codex en la PR #674) --


def test_una_pasada_completa_es_entera_aunque_el_fichero_anterior_fuera_ilegible() -> None:
    """Una pasada que evaluó todos los encargos rehace el conjunto entero: lo que
    hubiera en un fichero roto ya no puede faltar, porque todo se volvió a ver."""
    instantanea = cerrar_pasada(
        None, [_VISTA], anterior_ilegible=True, sin_evaluar=(), interrumpida=False, ahora=_T1
    )
    assert instantanea.completa and not instantanea.perdida_posible
    assert instantanea.divergencias == actualizar((), [_VISTA], sin_evaluar=(), ahora=_T1)


def test_una_pasada_incompleta_sobre_un_fichero_ilegible_deja_dicho_que_pudo_perderse() -> None:
    """El caso de la ronda 2: fichero roto y pasada que no pudo leer una incidencia
    (o murió a medias). Antes se escribía un conjunto vacío o parcial y la vista
    leía «ninguna»; ahora el fichero dice que no se sabe."""
    por_ilegible = cerrar_pasada(
        None, [], anterior_ilegible=True, sin_evaluar={"WI-1"}, interrumpida=False, ahora=_T1
    )
    assert not por_ilegible.completa and por_ilegible.perdida_posible
    assert por_ilegible.sin_evaluar == ("WI-1",)
    por_interrupcion = cerrar_pasada(
        None, [], anterior_ilegible=True, sin_evaluar=(), interrumpida=True, ahora=_T1
    )
    assert not por_interrupcion.completa and por_interrupcion.perdida_posible


def test_la_perdida_posible_se_hereda_hasta_la_primera_pasada_completa() -> None:
    primera = cerrar_pasada(
        None, [], anterior_ilegible=True, sin_evaluar={"WI-1"}, interrumpida=False, ahora=_T1
    )
    segunda = cerrar_pasada(
        primera, [], anterior_ilegible=False, sin_evaluar=(), interrumpida=True, ahora=_T2
    )
    assert segunda.perdida_posible, "sigue sin haber una pasada completa: la duda se hereda"
    tercera = cerrar_pasada(
        segunda, [_VISTA], anterior_ilegible=False, sin_evaluar=(), interrumpida=False, ahora=_T2
    )
    assert tercera.completa and not tercera.perdida_posible
    assert tercera == _completa(*actualizar((), [_VISTA], sin_evaluar=(), ahora=_T2))
