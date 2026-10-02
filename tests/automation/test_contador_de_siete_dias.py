"""El contador de los siete días no tiene horario desde ADR-225, y este fichero lo vigila.

La línea del contador quedó cancelada por decisión del propietario el 13-09-2026
(incidencia #610; ADR-225): sin la pieza que cablearía el retorno del desenlace
al almacén, `CLASES_CON_ESTADO_PROPIO` está vacío y cada pasada solo puede
escribir `no_comparable`. Medido en el registro de la rama de memoria antes de
retirar el horario: 19 pasadas programadas entre el 13-09 y el 01-10, 44 ejes,
los 44 `no_comparable`.

Hasta ADR-225 este fichero vigilaba lo contrario: que el contador TUVIERA
horario, que su cron fuera exactamente la hora derivada por
`hora_recomendada_pasada` (ADR-144) y que esa hora dejara por delante la
ventana de tolerancia (`max(timeout-minutes) x 2`), con un margen de dos
minutos que ataba a 85 el tope de todos los jobs del repositorio. Esas guardas
protegían un objetivo que ya no está autorizado y bloqueaban cambios legítimos
en otros workflows (ronda 2 de Codex en la PR #672); se fueron con el horario.
La derivación sigue probada sola en `tests/engine/test_seven_day_streak.py`, y
si la línea vuelve -otro ADR, por decisión del propietario- habrá que volver a
cablear el cron derivado y volver a traer las guardas.

Lo que queda aquí: que el fichero exista y se pueda lanzar a mano, que NO tenga
horario (si vuelve a tenerlo, alguien retomó la línea sin la decisión que
ADR-225 exige, o sin derivar la hora), y que siga serializado con el motor,
porque abrir el diario puede escribir en él.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
WORKFLOWS = RAIZ / ".github" / "workflows"
CONTADOR = WORKFLOWS / "contador-siete-dias.yml"


def _doc(ruta: Path) -> dict[Any, Any]:
    return dict(yaml.safe_load(ruta.read_text(encoding="utf-8")))


def _disparadores(doc: dict[Any, Any]) -> dict[str, Any]:
    """Los disparadores de un workflow, sorteando la rareza de YAML.

    YAML 1.1 lee la clave ``on:`` sin comillas como el booleano ``True``, no
    como el texto ``"on"``. Mismo convenio que ya siguen sus hermanas.
    """
    disparo = doc.get("on") or doc.get(True)
    assert isinstance(disparo, dict), f"el workflow no declara disparadores: {disparo!r}"
    return dict(disparo)


def test_el_contador_existe_y_se_lanza_solo_a_mano() -> None:
    """ADR-225: la pasada queda disponible a mano y sin reloj."""
    assert CONTADOR.is_file(), (
        f"falta {CONTADOR.name}: `sirius-racha` volvería a ser una pieza correcta "
        "a la que no llama nadie, que es como llevaba desde el 23-08-2026"
    )
    disparadores = _disparadores(_doc(CONTADOR))
    assert "workflow_dispatch" in disparadores, "la pasada tiene que poder lanzarse a mano"
    assert "schedule" not in disparadores, (
        "el contador vuelve a tener horario. La línea de los siete días quedó cancelada "
        "por el propietario el 13-09-2026 (#610, ADR-225) y cada pasada solo puede escribir "
        "`no_comparable`; si la línea vuelve, hace falta su ADR, derivar la hora con "
        "`uv run sirius-racha --hora-recomendada` y volver a traer las guardas del cron"
    )


def test_el_contador_se_serializa_con_el_motor() -> None:
    """Abrir el diario del motor para «solo leer» no es solo leer.

    `sirius-racha` construye un `DurableWorkEngineStore`, y construirlo reproduce
    el diario y reconcilia los cortes por presupuesto a medias -lo que **anexa
    eventos**-. Dos invocaciones simultáneas sobre ese diario se pisan
    (`tests/engine/test_exclusion_entre_invocaciones.py`). Compartir el grupo
    global es lo único que lo impide, también en una pasada a mano.
    """
    concurrencia = _doc(CONTADOR).get("concurrency")
    assert isinstance(concurrencia, dict), "el contador no declara bloque `concurrency`"
    assert concurrencia.get("group") == "motor-sirius", (
        "el contador tiene que compartir el grupo global `motor-sirius` con el motor "
        f"y el despachador, no {concurrencia.get('group')!r}: los tres abren el mismo "
        "diario, y abrirlo puede escribir en él"
    )
    assert concurrencia.get("cancel-in-progress") is False, (
        "cancelar la invocación en marcha no protege el diario: lo deja a medias"
    )
