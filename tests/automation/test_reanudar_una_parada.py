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
2. el invariante general —**todo estado que deja el ciclo esperando a una
   persona declara quién lo levanta**—, deduciendo las paradas de la
   enumeración real de estados en vez de escribirlas aquí, para que una parada
   nueva no pueda nacer sin salida. La primera versión de este módulo decía
   hacerlo y en realidad enumeraba una sola parada a mano; la #193 encontró el
   hueco al día siguiente (ADR-035).
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
# La lista de estados se LEE del código. La versión anterior de este módulo
# afirmaba hacerlo y no lo hacía: enumeraba a mano
# `{"sirius:blocked-decision": "continua"}` y dejaba fuera
# `sirius:failed-safely` con esta razón escrita: «su salida está documentada en
# `sirius_validate_activation.sh` (línea 46) y consiste en retirar la etiqueta
# tras leer el diagnóstico».
#
# Esa razón era falsa por dos vías independientes: la línea 46 habla de
# reactivar el trabajo DESDE CERO con `sirius:implement-requested`, no de
# retomar la ronda interrumpida; y ningún workflow escucha `unlabeled`, así que
# retirar la etiqueta no dispara nada. La #193 lo pagó al día siguiente: una
# parada segura por un timeout de Codex, sobre una PR con Quality en verde y
# tres rondas de trabajo acumulado, sin ninguna vía de vuelta que no fuese
# cirugía manual.
#
# Una lista escrita a mano solo protege de los olvidos que ya recordaste. Por
# eso los estados salen ahora de `INCOMPATIBLE_STATES` —la enumeración real que
# mantiene la automatización viva— y las exclusiones son ESTRUCTURALES: se
# descarta lo que por su forma no puede estar esperando a nadie, y todo lo que
# quede tiene que declarar quién lo levanta.

ACTIVACION = SCRIPTS_DIR / "sirius_validate_activation.sh"
REANUDAR = SCRIPTS_DIR / "sirius_resume_on_command.sh"

# Un `sirius:*-requested` es un EVENTO: aplicarlo dispara un workflow, así que
# por construcción no deja nada esperando a una persona.
_ES_EVENTO = re.compile(r"^sirius:.+-requested$")
# Fases en curso: hay un job corriendo y el ciclo avanza solo.
_EN_CURSO = frozenset(
    {"sirius:implementing", "sirius:reviewing", "sirius:repairing", "sirius:ci-pending"}
)
# Fin del recorrido: no hay nada que reanudar.
_TERMINAL = frozenset({"sirius:completed"})


def _estados_sirius_del_codigo() -> list[str]:
    """Los estados `sirius:*` que la automatización viva reconoce."""
    texto = ACTIVACION.read_text(encoding="utf-8")
    match = re.search(r'INCOMPATIBLE_STATES="([^"]+)"', texto)
    assert match, f"no se encontró INCOMPATIBLE_STATES en {ACTIVACION.name}"
    return match.group(1).split()


def _codigo_sin_comentarios(script: Path) -> str:
    """El guion sin sus líneas de comentario.

    Buscar la etiqueta en el fichero entero no vale, y no es teórico: la primera
    versión de esta prueba lo hacía y la mutación de control —sacar
    `sirius:failed-safely` del conjunto de paradas y de su rama `case`— pasó en
    verde, porque el nombre seguía apareciendo en el comentario de cabecera que
    explica la historia. Una prueba que se conforma con que algo se MENCIONE
    certifica documentación, no comportamiento.
    """
    return "\n".join(
        linea
        for linea in script.read_text(encoding="utf-8").splitlines()
        if not linea.lstrip().startswith("#")
    )


def _paradas_que_esperan_a_una_persona() -> list[str]:
    return [
        estado
        for estado in _estados_sirius_del_codigo()
        if not _ES_EVENTO.match(estado) and estado not in _EN_CURSO and estado not in _TERMINAL
    ]


def test_la_lista_de_estados_se_lee_de_verdad_del_codigo() -> None:
    """Si el `grep` de arriba fallara, lo de abajo pasaría sin comprobar nada."""
    estados = _estados_sirius_del_codigo()
    assert len(estados) >= 8, f"se leyeron demasiado pocos estados: {estados}"
    assert "sirius:blocked-decision" in estados
    assert "sirius:failed-safely" in estados


def test_toda_parada_que_espera_a_una_persona_declara_quien_la_levanta() -> None:
    """Un estado de parada sin salida es un defecto de diseño, no un accidente.

    Nada aquí nombra las paradas: salen de restarle, a la enumeración real de
    estados, las que por su forma no esperan a nadie. Una parada nueva que
    alguien añada mañana entra sola en esta prueba y tendrá que traer su orden.
    """
    paradas = _paradas_que_esperan_a_una_persona()
    assert paradas, "no se dedujo ninguna parada; la deducción está rota"
    ejecutores = sorted(SCRIPTS_DIR.glob("sirius_*_on_command.sh"))
    assert ejecutores, "no hay ningún ejecutor de órdenes que comprobar"
    for estado in paradas:
        quien = [s for s in ejecutores if estado in _codigo_sin_comentarios(s)]
        assert quien, (
            f"{estado} deja el ciclo esperando a una persona y ningún ejecutor "
            f"de órdenes lo levanta: es una parada sin salida"
        )


def test_una_parada_segura_vuelve_a_la_fase_que_se_detuvo() -> None:
    """`failed-safely` lo emite cualquiera de los tres roles, no solo el corrector.

    Devolverla siempre a `repair-requested` haría que una revisión caída se
    «reanudase» corrigiendo observaciones que nadie escribió. La fase se lee del
    historial —el marcador del veredicto lleva el rol— en vez de suponerse.
    """
    texto = REANUDAR.read_text(encoding="utf-8")
    assert "sirius:failed-safely" in texto
    for rol, destino in (
        ("implementer", "sirius:implement-requested"),
        ("reviewer", "sirius:review-requested"),
        ("corrector", "sirius:repair-requested"),
    ):
        assert re.search(rf"{rol}\)\s*printf '{re.escape(destino)}", texto), (
            f"no hay vuelta declarada para el rol {rol}"
        )
    assert "FAILED_SAFELY|precheck" in texto, (
        "las paradas `precheck` también dejan la incidencia en failed-safely, "
        "y también hay que saber de qué fase vinieron"
    )


def test_una_parada_segura_no_mueve_el_liston_de_convergencia() -> None:
    """Reanudar una fase caída no puede perdonar rondas.

    `sirius-convergence-reset` desplaza la frontera que mide el progreso. Vale
    para `blocked-decision`, que es una parada POR falta de progreso. En un
    `failed-safely` no hay rondas que perdonar, y publicarlo ahí borraría el
    listón sin que nadie lo pidiera: un ciclo de verdad estancado podría correr
    para siempre.
    """
    texto = REANUDAR.read_text(encoding="utf-8")
    # PR #477 (H-33): la rama de bloqueo exige ademas que el bloqueo vigente
    # sea DE CONVERGENCIA — un bloqueo emitido por un rol se reanuda sin
    # perdonar rondas, que es una segunda cara del mismo invariante.
    inicio = texto.index(
        'elif [ "$parada" = "sirius:blocked-decision" ] '
        '&& [ "${bloqueo_de_convergencia:-true}" = "true" ]; then'
    )
    fin = texto.index("# --- 5)", inicio)
    rama_bloqueo, rama_operativa = texto[inicio:fin].split("else", 1)
    assert "sirius-convergence-reset" in rama_bloqueo, (
        "la parada por convergencia sí necesita mover el listón"
    )
    assert "sirius-convergence-reset" not in rama_operativa, (
        "una parada operativa no puede publicar el marcador que perdona rondas"
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


def test_el_workflow_deja_pasar_todas_las_paradas_que_el_guion_sabe_levantar() -> None:
    """El guion y su workflow tienen que estar de acuerdo, o el guion no corre.

    El `if:` del job filtra por etiqueta, así que una parada que el guion sabe
    levantar pero el workflow no deja pasar produce exactamente lo que ADR-030
    vino a eliminar —una orden del propietario que no llega a ninguna parte— y
    encima **sin dejar rastro**, porque el job ni siquiera arranca: no hay run
    que mirar ni comentario que leer, la orden simplemente no hace nada.

    Se descubrió al ampliar el guion a `sirius:failed-safely` (ADR-035): el
    cambio del guion, por sí solo, habría sido inerte, y no lo habría notado
    nadie hasta la siguiente parada.
    """
    import yaml

    workflow = REPO_ROOT / ".github" / "workflows" / "resume-sirius-on-command.yml"
    doc = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    condicion = " ".join(str(job.get("if") or "") for job in doc["jobs"].values())
    assert condicion.strip(), f"{workflow.name} no filtra nada; revisa la lectura"

    codigo = _codigo_sin_comentarios(REANUDAR)
    match = re.search(r'SIRIUS_PARADAS_REANUDABLES="([^"]+)"', codigo)
    assert match, f"no se encontró SIRIUS_PARADAS_REANUDABLES en {REANUDAR.name}"
    for estado in match.group(1).split():
        assert estado in condicion, (
            f"{workflow.name} no deja pasar {estado}, así que el guion nunca "
            f"llegaría a levantarla: hay que pegar el workflow actualizado"
        )
