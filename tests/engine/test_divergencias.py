"""Las divergencias que el reflector aparta, conservadas entre pasadas (ADR-227, H-216).

La regla de retención es pura y se prueba sola; el cableado en ``sirius-reflejar``
lo prueba ``test_reflect_cli.py`` y la vista, ``test_memoria.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius_engine.divergencias import (
    FICHERO_DIVERGENCIAS,
    DivergenciaApartada,
    DivergenciaVista,
    actualizar,
    escribir_divergencias,
    leer_divergencias,
    ruta_de_divergencias,
)

_T1 = datetime(2026, 8, 29, 3, 24, tzinfo=UTC)
_T2 = datetime(2026, 9, 25, 3, 24, tzinfo=UTC)
_VISTA = DivergenciaVista("WI-20260828-122242", 392, "etiquetas que se contradicen")


def test_una_divergencia_nueva_nace_con_su_primera_vez_y_al_repetirse_la_conserva() -> None:
    primera = actualizar((), [_VISTA], ilegibles=(), ahora=_T1)
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
    segunda = actualizar(primera, [_VISTA], ilegibles=(), ahora=_T2)
    assert segunda[0].primera_vez == _T1.isoformat()
    assert segunda[0].ultima_vez == _T2.isoformat()
    assert segunda[0].pasadas == 2


def test_una_entrada_que_la_pasada_evaluo_sin_divergencia_se_retira() -> None:
    anteriores = actualizar((), [_VISTA], ilegibles=(), ahora=_T1)
    assert actualizar(anteriores, [], ilegibles=(), ahora=_T2) == ()


def test_una_entrada_cuyo_encargo_no_se_pudo_leer_se_conserva_tal_cual() -> None:
    """No saber no es saber que se resolvió: una incidencia ilegible esta pasada
    deja la entrada con su última fecha, no la borra."""
    anteriores = actualizar((), [_VISTA], ilegibles=(), ahora=_T1)
    conservadas = actualizar(anteriores, [], ilegibles={"WI-20260828-122242"}, ahora=_T2)
    assert conservadas == anteriores


def test_leer_y_escribir_van_y_vuelven_y_sin_fichero_no_hay_nada(tmp_path: Path) -> None:
    ruta = ruta_de_divergencias(tmp_path / "diario.jsonl")
    assert ruta.name == FICHERO_DIVERGENCIAS
    assert leer_divergencias(ruta) == ()
    apartadas = actualizar(
        (), [_VISTA, DivergenciaVista("WI-0", None, "hacia atrás")], ilegibles=(), ahora=_T1
    )
    escribir_divergencias(ruta, apartadas)
    assert leer_divergencias(ruta) == apartadas
    assert [d.work_id for d in apartadas] == ["WI-0", "WI-20260828-122242"], "ordenadas por encargo"


@pytest.mark.parametrize("texto", ["[]", "{}", '{"divergencias": [{"work_id": "WI-1"}]}'])
def test_un_fichero_que_no_tiene_la_forma_se_declara_en_vez_de_leerse_como_vacio(
    tmp_path: Path, texto: str
) -> None:
    ruta = tmp_path / FICHERO_DIVERGENCIAS
    ruta.write_text(texto, encoding="utf-8")
    with pytest.raises(ValueError, match=FICHERO_DIVERGENCIAS):
        leer_divergencias(ruta)
