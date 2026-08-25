"""``sirius-supervisar``: el interruptor del motor (D2, #296).

La cáscara no decide nada, así que lo que hay que fijar es exactamente eso: que
resuelve bien las rutas, que el ensayo no toca nada, que sin ensayo llama a la
supervisión **una sola vez** y con lo que le corresponde, y que un error se ve
en el código de salida en vez de pasar desapercibido.

Y una propiedad que no es de estilo: **la hora entra por aquí y solo por aquí**.
El motor es determinista porque nunca lee el reloj; si esta cáscara dejara de
pasarle un ``now`` explícito, esa garantía se rompería sin que nada avisara.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from sirius_engine import supervise_cli
from sirius_engine.recovery import RecoverySweepResult, UnobservedRun
from sirius_engine.supervisor import SupervisionError, SupervisionSweepResult

AHORA = datetime(2026, 8, 24, 13, 0, tzinfo=UTC)


def _resultado_vacio() -> SupervisionSweepResult:
    return SupervisionSweepResult(
        recovery=RecoverySweepResult(reconciled_run_ids=(), released_work_item_ids=())
    )


def _ejecutar(
    argv: list[str], *, entorno: dict[str, str] | None = None, ahora: datetime | None = AHORA
) -> tuple[int, str]:
    salida = io.StringIO()
    codigo = supervise_cli.main(argv, salida=salida, entorno=entorno or {}, ahora=ahora)
    return codigo, salida.getvalue()


# --- El ensayo no toca nada ------------------------------------------------


def test_el_ensayo_no_supervisa_ni_crea_ficheros(tmp_path: Path, monkeypatch: Any) -> None:
    diario = tmp_path / "sub" / "diario.jsonl"
    llamadas: list[object] = []
    monkeypatch.setattr(supervise_cli, "supervise_runs", lambda *a, **k: llamadas.append(a))

    codigo, texto = _ejecutar(["--ensayo", "--diario", str(diario)])

    assert codigo == 0
    assert llamadas == [], "el ensayo no puede llamar a la supervisión"
    assert not diario.parent.exists(), "el ensayo no puede crear ni el directorio"
    assert "ENSAYO" in texto


def test_el_ensayo_dice_que_rutas_usaria(tmp_path: Path, monkeypatch: Any) -> None:
    diario = tmp_path / "diario.jsonl"
    monkeypatch.setattr(supervise_cli, "supervise_runs", lambda *a, **k: _resultado_vacio())

    _, texto = _ejecutar(["--ensayo", "--diario", str(diario)])

    assert str(diario) in texto
    assert str(supervise_cli.diario_de_supervision(diario)) in texto


# --- Sin ensayo, supervisa ------------------------------------------------


def test_sin_ensayo_llama_a_la_supervision_una_sola_vez(tmp_path: Path, monkeypatch: Any) -> None:
    diario = tmp_path / "diario.jsonl"
    llamadas: list[tuple[Any, ...]] = []

    def espia(*args: Any, **kwargs: Any) -> SupervisionSweepResult:
        llamadas.append((args, kwargs))
        return _resultado_vacio()

    monkeypatch.setattr(supervise_cli, "supervise_runs", espia)

    codigo, _ = _ejecutar(["--diario", str(diario)])

    assert codigo == 0
    assert len(llamadas) == 1, f"se esperaba una sola pasada, hubo {len(llamadas)}"


def test_la_hora_entra_por_la_cascara_y_llega_a_la_supervision(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """El motor no lee el reloj: si esta cáscara dejara de pasarlo, se rompería."""
    recibido: dict[str, Any] = {}

    def espia(*args: Any, **kwargs: Any) -> SupervisionSweepResult:
        recibido.update(kwargs)
        return _resultado_vacio()

    monkeypatch.setattr(supervise_cli, "supervise_runs", espia)

    _ejecutar(["--diario", str(tmp_path / "diario.jsonl")], ahora=AHORA)

    assert recibido.get("now") == AHORA, (
        "la supervisión tiene que recibir un `now` explícito; si no, el motor "
        "acabaría leyendo el reloj y dejaría de ser determinista"
    )


def test_el_directorio_del_diario_se_crea_al_supervisar(tmp_path: Path, monkeypatch: Any) -> None:
    diario = tmp_path / "aun-no-existe" / "diario.jsonl"
    monkeypatch.setattr(supervise_cli, "supervise_runs", lambda *a, **k: _resultado_vacio())

    _ejecutar(["--diario", str(diario)])

    assert diario.parent.is_dir(), "sin el directorio, la primera pasada moriría al escribir"


# --- Un error se ve, no se traga ------------------------------------------


def test_un_error_de_supervision_sale_por_el_codigo_de_salida(
    tmp_path: Path, monkeypatch: Any
) -> None:
    resultado = SupervisionSweepResult(
        recovery=RecoverySweepResult(reconciled_run_ids=(), released_work_item_ids=()),
        errors=(SupervisionError(run_id="run-1", mensaje="no se pudo"),),
    )
    monkeypatch.setattr(supervise_cli, "supervise_runs", lambda *a, **k: resultado)

    codigo, texto = _ejecutar(["--diario", str(tmp_path / "diario.jsonl")])

    assert codigo == 1, "un error tiene que poner el workflow en rojo, no pasar en verde"
    assert "ERROR" in texto


def test_sin_errores_el_codigo_de_salida_es_cero(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(supervise_cli, "supervise_runs", lambda *a, **k: _resultado_vacio())

    codigo, _ = _ejecutar(["--diario", str(tmp_path / "diario.jsonl")])

    assert codigo == 0


def test_una_pasada_que_no_pudo_observar_no_se_ve_como_un_turno_limpio(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """H-2/ADR-053: `unobserved_runs` lo calcula recovery.py precisamente para
    que una lectura caída no se calle. Si `_resumen` no lo publica, el
    propietario lee puros ceros sobre una pasada que no pudo mirar nada."""
    resultado = SupervisionSweepResult(
        recovery=RecoverySweepResult(
            reconciled_run_ids=(),
            released_work_item_ids=("wi-1",),
            unobserved_runs=(
                UnobservedRun(
                    run_id="9999999999",
                    diagnostico="[Errno 2] No such file or directory: 'gh'",
                ),
            ),
        )
    )
    monkeypatch.setattr(supervise_cli, "supervise_runs", lambda *a, **k: resultado)

    _, texto = _ejecutar(["--diario", str(tmp_path / "diario.jsonl")])

    assert "no observados:      1" in texto, (
        "el contador de no observados tiene que aparecer, y no como cero: "
        f"salida completa:\n{texto}"
    )
    assert "9999999999" in texto, "el run_id no observado tiene que verse"
    assert "gh" in texto, "el diagnóstico del fallo de lectura tiene que verse"
    assert "liberados:          1" in texto, "released_work_item_ids también falta hoy"


# --- Las rutas ------------------------------------------------------------


def test_el_diario_del_supervisor_es_hermano_del_diario_del_motor() -> None:
    """Dos mitades de la misma memoria: separarlas por configuración solo crea
    formas de que no coincidan."""
    diario = Path("/algun/sitio/diario.jsonl")

    hermano = supervise_cli.diario_de_supervision(diario)

    assert hermano.parent == diario.parent
    assert hermano.name == supervise_cli.NOMBRE_DIARIO_SUPERVISOR


@pytest.mark.parametrize(
    ("argv", "entorno"),
    [
        (["--diario", "{ruta}"], {}),
        ([], {"SIRIUS_MOTOR_DIARIO": "{ruta}"}),
    ],
)
def test_el_diario_se_fija_por_argumento_o_por_entorno(
    tmp_path: Path, monkeypatch: Any, argv: list[str], entorno: dict[str, str]
) -> None:
    """Es lo que permite que el workflow apunte al fichero versionado sin tocar código."""
    diario = tmp_path / "diario.jsonl"
    monkeypatch.setattr(supervise_cli, "supervise_runs", lambda *a, **k: _resultado_vacio())

    _, texto = _ejecutar(
        [a.format(ruta=str(diario)) for a in argv],
        entorno={k: v.format(ruta=str(diario)) for k, v in entorno.items()},
    )

    assert str(diario) in texto
