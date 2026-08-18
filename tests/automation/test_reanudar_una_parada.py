"""Una parada del ciclo tiene que poder levantarse con una orden, no con cirugía.

El ciclo de A2 (#186 / PR #189) se detuvo tres veces y las tres hizo falta una
persona. La tercera es la que motiva este módulo: tras tres rondas en el par
(1, 2) saltó `sin-progreso`, correctamente. El propietario autorizó una ronda
más — y **no había forma de dársela a la máquina**, porque `decide()` mide sobre
todo el historial publicado y reponer la etiqueta disparadora volvía a bloquear
en el acto. La ronda se acabó haciendo a mano, fuera del ciclo.

Estas pruebas cubren las dos mitades del arreglo:

1. la frontera de historial que hace la orden efectiva
   (`history_after_last_resume`), y que **no debilita** la política: una parada
   real vuelve a saltar a partir del marcador;
2. el invariante general —**todo estado que exige una decisión humana declara la
   orden que lo levanta**—, recorriendo la lista en vez de enumerarla a mano,
   para que un estado de parada nuevo no pueda nacer sin salida.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "automation"
SCRIPT = SCRIPTS_DIR / "sirius_convergence.py"


def _module() -> Any:
    """Mismo cargador que `test_sirius_convergence.py`.

    El guion vive fuera de un paquete importable, así que se carga por ruta.
    Se reutiliza el nombre de módulo de las pruebas existentes para no tener dos
    copias del mismo fichero cargadas a la vez con estado independiente.
    """
    name = "sirius_convergence_under_test"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _decidir(texto: str) -> dict[str, Any]:
    """La decisión tal como la toma `cmd_decide`: corte primero, dos medidas después."""
    convergencia = _module()
    vigente = convergencia.history_after_last_resume(texto)
    resultado: dict[str, Any] = convergencia.decide(
        convergencia.parse_round_records(vigente),
        ci_failures=convergencia.ci_failure_streak(vigente),
    )
    return resultado


def _ronda(numero: int, head: str, huellas: list[tuple[str, str]]) -> str:
    """Un comentario de ronda como el que publica el revisor."""
    registro = {
        "round": numero,
        "head": head,
        "findings": [
            {"fingerprint": h, "severity": s, "source": "CODEX", "file": "x.py"} for h, s in huellas
        ],
        "pending": len(huellas),
        "severity_total": 0,
    }
    return (
        f"<!-- sirius-round:{numero} -->\n\n"
        f"## RONDA_HALLAZGOS\n```json\n{json.dumps(registro)}\n```\n"
    )


# Tres rondas planas: exactamente la forma del estancamiento que detuvo la #186.
ESTANCADO = (
    _ronda(1, "aaa1", [("h1", "P1")])
    + _ronda(2, "bbb2", [("h2", "P1")])
    + _ronda(3, "ccc3", [("h3", "P1")])
)


def test_sin_la_orden_el_historial_estancado_sigue_bloqueando() -> None:
    """El punto de partida: sin marcador, la política bloquea — y debe hacerlo."""
    resultado = _decidir(ESTANCADO)
    assert resultado["decision"] == "BLOCK"
    assert resultado["reason"] == "sin-progreso"


def test_la_orden_del_propietario_reinicia_la_medida_sin_borrar_el_historial() -> None:
    """Lo que la orden cambia, y lo que deliberadamente no cambia.

    El texto completo sigue conteniendo las tres rondas anteriores —la
    incidencia no pierde nada y sigue siendo auditable—; lo único que cambia es
    dónde empieza a medir la política.
    """
    texto = ESTANCADO + "<!-- sirius-convergence-reset:ddd4 -->\n"

    assert "sirius-round:1" in texto, "el historial anterior no se borra"
    vigente = _module().history_after_last_resume(texto)
    assert "sirius-round:1" not in vigente, "pero deja de contar como listón"

    assert _decidir(texto)["decision"] == "CONTINUE"


def test_tras_la_orden_un_estancamiento_nuevo_vuelve_a_bloquear() -> None:
    """La salvaguarda no se debilita: se le da una entrada.

    Sin esto, `history_after_last_resume` sería una forma elegante de desactivar
    la política — bastaría con una orden para que el ciclo girase sin fin. Lo
    que la orden compra son rondas nuevas, no impunidad.
    """
    texto = (
        ESTANCADO
        + "<!-- sirius-convergence-reset:ddd4 -->\n"
        + _ronda(4, "ddd4", [("h4", "P1")])
        + _ronda(5, "eee5", [("h5", "P1")])
        + _ronda(6, "fff6", [("h6", "P1")])
    )
    resultado = _decidir(texto)
    assert resultado["decision"] == "BLOCK"
    assert resultado["reason"] == "sin-progreso"


def test_la_orden_reinicia_tambien_la_racha_de_fallos_de_ci() -> None:
    """El ciclo tiene dos motores y la orden levanta los dos.

    Reiniciar solo las rondas de revisión dejaría al otro motor —la racha de
    Quality en rojo— condenando el trabajo que el propietario acaba de
    autorizar, y la parada seguiría en pie por un motivo distinto. Desde fuera
    eso es indistinguible de que la orden no funcione.
    """
    convergencia = _module()
    rojos = "".join(f"<!-- sirius-quality:{h}:failure -->\n" for h in ("a1", "b2", "c3"))
    assert convergencia.ci_failure_streak(rojos) == 3

    texto = rojos + "<!-- sirius-convergence-reset:ddd4 -->\n"
    vigente = convergencia.history_after_last_resume(texto)
    assert convergencia.ci_failure_streak(vigente) == 0
    assert _decidir(texto)["decision"] == "CONTINUE"


def test_solo_cuenta_la_ultima_orden() -> None:
    """Dos órdenes seguidas no son dos permisos acumulados: manda la última."""
    texto = (
        "<!-- sirius-convergence-reset:aaa1 -->\n"
        + _ronda(1, "bbb2", [("h1", "P1")])
        + "<!-- sirius-convergence-reset:ccc3 -->\n"
        + _ronda(2, "ddd4", [("h2", "P1")])
    )
    convergencia = _module()
    vigente = convergencia.history_after_last_resume(texto)
    assert [r["round"] for r in convergencia.parse_round_records(vigente)] == [2]


# --- El invariante general ----------------------------------------------------
#
# La lista se lee del propio script de reconciliación, no se escribe a mano: una
# lista copiada habría que acordarse de ampliarla, que es exactamente el olvido
# que esta prueba existe para hacer imposible.

PARADAS_QUE_EXIGEN_DECISION = {
    # estado terminal que espera a una persona -> orden exacta que lo levanta
    "sirius:blocked-decision": "continua",
}


def test_todo_estado_de_parada_declara_la_orden_que_lo_levanta() -> None:
    """Un estado de parada sin salida es un defecto de diseño, no un accidente.

    `sirius:failed-safely` no aparece aquí a propósito: su salida está
    documentada y probada en `sirius_validate_activation.sh` (línea 46, «exige
    revisar el diagnóstico»), y consiste en retirar la etiqueta tras leerlo.
    Tiene vía de vuelta. `sirius:blocked-decision` no la tenía.
    """
    for estado, orden in PARADAS_QUE_EXIGEN_DECISION.items():
        ejecutores = [
            script
            for script in SCRIPTS_DIR.glob("sirius_*_on_command.sh")
            if estado in script.read_text(encoding="utf-8")
        ]
        assert ejecutores, f"{estado} no tiene ningún ejecutor de orden que lo levante"
        for script in ejecutores:
            texto = script.read_text(encoding="utf-8")
            assert f'"{orden}"' in texto, (
                f"{script.name} atiende a {estado} pero no comprueba la orden exacta {orden!r}"
            )


@pytest.mark.parametrize(
    "script",
    sorted(SCRIPTS_DIR.glob("sirius_*_on_command.sh")),
    ids=lambda p: p.name,
)
def test_toda_orden_por_comentario_se_reverifica_por_rest(script: Path) -> None:
    """El evento describe el pasado; la decisión se toma sobre el presente.

    El workflow filtra por `author_association` en el evento, pero entre ese
    comentario y la ejecución cabe cualquier cambio de estado. Todo ejecutor de
    órdenes vuelve a leer las etiquetas por REST antes de actuar, y distingue un
    fallo de lectura de un estado ausente — tratar un 503 como «no está
    bloqueada» dejaría la orden del propietario tirada en silencio.
    """
    texto = script.read_text(encoding="utf-8")
    assert re.search(r"sirius_retry gh api .*issues/\$\{ISSUE\}", texto), (
        f"{script.name} no reverifica el estado por REST antes de actuar"
    )
    assert "orden exacta" in texto, f"{script.name} no exige una orden exacta"
