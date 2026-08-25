"""La hora del contador de los siete días no se elige a ojo: se deriva o no vale.

`sirius-racha` mide si el motor y sus incidencias dicen lo mismo, y esa medición
**solo puede salir verde si nada se movió durante la ventana de tolerancia
previa a la pasada** -lo midió el cierre de la incidencia #265-. Con etiquetas
más frescas que esa ventana, el verificador no distingue una divergencia real de
una etiqueta que todavía no ha aterrizado, así que se declara `NO_COMPARABLE` y
el día no cuenta.

Por eso cablear este contador a una hora cualquiera no lo rompe de forma
ruidosa: lo rompe **en silencio**. La pasada correría cada día, saldría en verde
-`sirius-racha` devuelve 0 tanto si CUMPLE como si no- y la racha simplemente no
se completaría nunca. D1 quedaría inalcanzable sin que ningún rojo lo dijera.

Ya pasó una vez con el motor: un cron en el minuto 47 partía el hueco tranquilo
y `hora_recomendada_pasada` dejaba de encontrar hora. Lo cazó
`tests/automation/test_turno_programado_actua.py`. Este fichero es su hermano
para el contador, y protege además algo que aquel no puede ver:

**el margen es de DOS MINUTOS.** La tolerancia se deriva de
``max(timeout-minutes) x 2``; hoy vale 170, y la tranquilidad previa a las 03:24
son 172. Que alguien suba un `timeout-minutes` de 85 a 87 -un gesto inocente en
cualquier otro workflow- deja a D1 sin ninguna hora posible. Esta batería existe
para que ese día salga en ROJO aquí, y no como una racha que nunca avanza.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from sirius_engine.projection_verifier import ventana_tolerancia_etiqueta_maquina
from sirius_engine.seven_day_streak import _horas_de_disparo

RAIZ = Path(__file__).resolve().parents[2]
WORKFLOWS = RAIZ / ".github" / "workflows"
CONTADOR = WORKFLOWS / "contador-siete-dias.yml"

MINUTOS_DEL_DIA = 24 * 60


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


def _minutos_de(doc: dict[Any, Any]) -> list[int]:
    """Los minutos del día en que este workflow dispara periódicamente."""
    minutos: list[int] = []
    for entrada in _disparadores(doc).get("schedule") or []:
        if isinstance(entrada, dict) and entrada.get("cron"):
            for hora in _horas_de_disparo(str(entrada["cron"])):
                minutos.append(hora.hour * 60 + hora.minute)
    return minutos


def _todos_los_disparos() -> set[int]:
    """Todos los disparos periódicos del repositorio, en minutos del día."""
    todos: set[int] = set()
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        todos.update(_minutos_de(_doc(wf)))
    return todos


def _tranquilidad_antes_de(minuto: int, disparos: set[int]) -> int:
    """Minutos libres de disparos justo ANTES de ``minuto``, circularmente.

    Se excluye el propio ``minuto``: un workflow no se estorba a sí mismo, y
    contarlo daría siempre cero.
    """
    otros = sorted(disparos - {minuto})
    if not otros:
        return MINUTOS_DEL_DIA
    return min((minuto - otro) % MINUTOS_DEL_DIA for otro in otros)


def test_el_contador_existe_y_tiene_horario() -> None:
    """Anti-vacua: sin horario, las demás pruebas medirían un contador que no corre."""
    assert CONTADOR.is_file(), (
        f"falta {CONTADOR.name}: `sirius-racha` volvería a ser una pieza correcta "
        "a la que no llama nadie, que es como llevaba desde el 23-08-2026"
    )
    disparadores = _disparadores(_doc(CONTADOR))
    assert "schedule" in disparadores, (
        "el contador perdió su horario. Sin él, D1 no puede completarse: los siete "
        "días del contrato §11.2 exigen una pasada diaria, no una a mano"
    )
    assert [e["cron"] for e in disparadores["schedule"]], "el horario no declara ningún cron"


def test_la_hora_del_contador_deja_pasar_la_ventana_de_tolerancia() -> None:
    """La propiedad que da sentido a este fichero, derivada y nunca escrita a mano.

    Un día solo puede salir VERDE si nada se movió durante la ventana de
    tolerancia previa a la pasada (#265). Si la tranquilidad previa al cron del
    contador no alcanza esa ventana, la racha no avanzaría **nunca**, y lo haría
    en verde.
    """
    disparos = _todos_los_disparos()
    minutos_contador = _minutos_de(_doc(CONTADOR))
    assert minutos_contador, "el contador no declara ningún disparo periódico"

    tolerancia = int(ventana_tolerancia_etiqueta_maquina(WORKFLOWS).total_seconds() // 60)

    for minuto in minutos_contador:
        tranquilidad = _tranquilidad_antes_de(minuto, disparos)
        hh, mm = divmod(minuto, 60)
        assert tranquilidad >= tolerancia, (
            f"el contador dispara a las {hh:02d}:{mm:02d} UTC y solo deja "
            f"{tranquilidad} min tranquilos por delante, cuando la tolerancia "
            f"vigente es de {tolerancia} min.\n"
            "  Con etiquetas más frescas que la tolerancia el verificador declara "
            "NO_COMPARABLE, así que ningún día contaría y la racha no avanzaría "
            "NUNCA -en verde, porque `sirius-racha` devuelve 0 igual-.\n"
            "  La tolerancia es `max(timeout-minutes de TODOS los jobs) x 2`: si "
            "acabas de subir un tope, ÉSA es la causa. Vuelve a derivar la hora con "
            "`uv run sirius-racha --hora-recomendada` y mueve el cron, o baja el tope."
        )


def test_el_contador_se_serializa_con_el_motor() -> None:
    """Abrir el diario del motor para «solo leer» no es solo leer.

    `sirius-racha` construye un `DurableWorkEngineStore`, y construirlo reproduce
    el diario y reconcilia los cortes por presupuesto a medias -lo que **anexa
    eventos**-. Dos invocaciones simultáneas sobre ese diario se pisan
    (`tests/engine/test_exclusion_entre_invocaciones.py`). Compartir el grupo
    global es lo único que lo impide.
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


def test_el_tope_del_propio_contador_no_se_muerde_la_cola() -> None:
    """El `timeout-minutes` de este job entra en la tolerancia que lo juzga.

    Es una trampa real y no teórica: la tolerancia sale del MAYOR
    `timeout-minutes` del repositorio, así que subir el de este mismo fichero
    ensancha la ventana que su propia hora tiene que dejar libre. Se comprueba
    que no es él quien manda, porque si lo fuera cualquier ajuste suyo movería
    la vara con la que se mide.
    """
    doc = _doc(CONTADOR)
    topes_contador = [
        job["timeout-minutes"]
        for job in (doc.get("jobs") or {}).values()
        if isinstance(job, dict) and isinstance(job.get("timeout-minutes"), int)
    ]
    assert topes_contador, "el job del contador no declara `timeout-minutes`"

    topes_del_resto: list[int] = []
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        if wf == CONTADOR:
            continue
        for job in (_doc(wf).get("jobs") or {}).values():
            if isinstance(job, dict) and isinstance(job.get("timeout-minutes"), int):
                topes_del_resto.append(job["timeout-minutes"])

    assert max(topes_contador) <= max(topes_del_resto), (
        f"el contador declara un tope de {max(topes_contador)} min, por encima del "
        f"mayor del resto del repositorio ({max(topes_del_resto)} min). Eso hace que "
        "sea ÉL quien fija la tolerancia con la que se juzga su propia hora: el "
        "trabajo mordiéndose la cola. Bájalo."
    )


# --- Anti-vacuas: el criterio tiene que saber decir que NO ------------------


@pytest.mark.parametrize(
    ("minuto", "disparos", "esperado"),
    [
        # El caso real de hoy: 03:24 con el disparo previo a las 00:32.
        (3 * 60 + 24, {17, 32, 3 * 60 + 24, 6 * 60 + 17, 6 * 60 + 32}, 172),
        # Pegado al disparo anterior: un minuto de tranquilidad.
        (33, {32, 33}, 1),
        # El hueco circular cuenta: 00:10 con el último disparo a las 23:50.
        (10, {10, 23 * 60 + 50}, 20),
        # Sin ningún otro disparo, el día entero está tranquilo.
        (600, {600}, MINUTOS_DEL_DIA),
    ],
)
def test_la_tranquilidad_se_calcula_bien(minuto: int, disparos: set[int], esperado: int) -> None:
    """Si este cálculo estuviera mal, la prueba de arriba pasaría diciendo nada."""
    assert _tranquilidad_antes_de(minuto, disparos) == esperado


def test_el_criterio_rechaza_una_hora_mala() -> None:
    """La mutación, fijada: una hora pegada a otro disparo tiene que caer.

    Sin esta prueba, un `_tranquilidad_antes_de` que devolviera siempre un número
    grande dejaría la comprobación principal en verde para cualquier hora.
    """
    tolerancia = int(ventana_tolerancia_etiqueta_maquina(WORKFLOWS).total_seconds() // 60)
    disparos = _todos_los_disparos()
    # Un minuto después de un disparo real: la peor hora posible del día.
    pegado = (min(disparos) + 1) % MINUTOS_DEL_DIA
    assert _tranquilidad_antes_de(pegado, disparos | {pegado}) < tolerancia, (
        "una hora pegada a otro disparo tiene que quedar por debajo de la "
        "tolerancia; si no, el criterio no está midiendo nada"
    )
