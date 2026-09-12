"""El workflow que invoca al motor no puede dejar de serializar sus invocaciones (D2, #296).

`test_exclusion_entre_invocaciones.py` mide el peligro: dos lecturas
independientes del diario crean el mismo trabajo dos veces, con la misma clave
de idempotencia y el mismo número de secuencia, y el almacén relee ese diario
sin quejarse. ADR-082 concluye de ahí que serializar dejó de ser una precaución
para pasar a ser **la única protección**.

Esta batería es la otra mitad: que esa protección **no se pueda quitar sin que
algo se rompa**. Una salvaguarda que depende de que nadie la borre dura hasta el
primer despiste, y este repositorio lleva una semana midiendo justo eso.

Dos exigencias, y la segunda es la que se olvida:

1. El workflow declara un bloque ``concurrency``.
2. Su ``group`` es **constante**. Un grupo que varíe por evento -como
   ``...-${{ github.event.pull_request.number }}``, que es correcto en el
   workflow de fusión y veneno aquí- mete cada invocación en un grupo distinto,
   así que NO se serializan entre sí y la protección es decorativa.

Y ``cancel-in-progress: false``: cancelar la invocación que va no protege el
diario, lo deja a medias. Se espera, no se mata.

La lista de comandos del motor se **deriva** de ``[project.scripts]`` de
``pyproject.toml`` en vez de escribirse a mano: una tupla escrita a mano se
queda corta en cuanto alguien añade un punto de entrada, que es la familia que
ADR-033 nombró y que en este repositorio ha mordido cuatro veces.
"""

from __future__ import annotations

import ast
import re
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
WORKFLOWS = RAIZ / ".github" / "workflows"
FUENTE = RAIZ / "src" / "sirius_engine"
PYPROJECT = RAIZ / "pyproject.toml"

#: Cualquier forma de invocar al motor: sus comandos instalados, el módulo por
#: `python -m`, o el paquete a secas.
_PAQUETE = "sirius_engine"


#: Los puertos por los que se llega al estado del motor: el almacén de
#: `WorkItem` y el diario de despacho. Alcanzar cualquiera de los dos es poder
#: CREAR o MOVER trabajo, que es el peligro exacto que esta batería vigila.
_PUERTAS_DEL_ESTADO = (
    "sirius_engine.adapters.durable",
    "sirius_engine.ports.store",
    "sirius_engine.ports.dispatch_journal",
)


def _importados(ruta: Path) -> set[str]:
    """Los módulos que un fichero importa, leídos del árbol sintáctico."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module)
        elif isinstance(nodo, ast.Import):
            nombres.update(alias.name for alias in nodo.names)
    return nombres


def _fichero_de(modulo: str) -> Path | None:
    if not modulo.startswith(_PAQUETE):
        return None
    resto = modulo.split(".")[1:]
    suelto = FUENTE.joinpath(*resto).with_suffix(".py")
    if suelto.is_file():
        return suelto
    paquete = FUENTE.joinpath(*resto, "__init__.py")
    return paquete if paquete.is_file() else None


def _importados_de_modulo(modulo: str) -> set[str]:
    """Lo que importa un módulo del motor, o nada si no se encuentra su fichero."""
    fichero = _fichero_de(modulo)
    return _importados(fichero) if fichero is not None else set()


def _alcanza_el_estado(
    modulo: str, *, importados: Callable[[str], set[str]] = _importados_de_modulo
) -> bool:
    """¿Este punto de entrada puede llegar al almacén o al diario de despacho?

    Recorre sus imports **hacia dentro**, no solo el primer nivel, y solo dentro
    del paquete del motor. No es una lista escrita a mano -que es la familia de
    defecto que ADR-033 nombró y que aquí ha mordido cuatro veces-: se deriva
    del código, así que un comando nuevo queda clasificado sin que nadie lo
    apunte.

    Hoy, en este árbol, TODOS los comandos que alcanzan el almacén lo importan
    directamente, así que el recorrido en profundidad no lo ejercita ningún
    comando real. Se conserva igual, y se prueba con un grafo de mentira
    (``importados`` es inyectable por eso), porque el error que evita va en la
    dirección peligrosa: un comando que llegara al almacén a través de un
    ayudante se clasificaría como de solo lectura y **perdería** su grupo
    constante sin que nadie lo notara.
    """
    vistos: set[str] = set()
    pendientes = [modulo]
    while pendientes:
        actual = pendientes.pop()
        if actual in vistos:
            continue
        vistos.add(actual)
        if any(actual.startswith(puerta) for puerta in _PUERTAS_DEL_ESTADO):
            return True
        for hijo in importados(actual):
            if any(hijo.startswith(puerta) for puerta in _PUERTAS_DEL_ESTADO):
                return True
            if hijo.startswith(_PAQUETE):
                pendientes.append(hijo)
    return False


def _comandos_del_motor() -> frozenset[str]:
    """Los `[project.scripts]` cuyo destino vive en el paquete del motor."""
    datos = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    scripts: dict[str, str] = datos.get("project", {}).get("scripts", {})
    return frozenset(
        nombre for nombre, destino in scripts.items() if destino.startswith(f"{_PAQUETE}.")
    )


def _comandos_que_mutan_el_estado() -> frozenset[str]:
    """De los comandos del motor, los que pueden crear o mover trabajo.

    **Por qué esta distinción existe** (ADR-175, tercera ronda de revisión). El
    peligro que mide `test_exclusion_entre_invocaciones.py` y que ADR-082
    convirtió en la única protección es concreto: dos lecturas independientes
    del diario crean el mismo trabajo dos veces. Ese peligro lo tiene quien
    puede llegar al almacén o al diario de despacho; quien solo LEE el espejo
    de GitHub y escribe un comentario no lo tiene, y exigirle el mismo grupo
    constante obliga a serializar entre sí cosas que no comparten nada -y eso
    tuvo su propio precio: un tablero por incidencia con un grupo común pierde
    actualizaciones de otras incidencias-.

    La distinción **se deriva del código**, no se declara: lo que la sostiene
    es `_alcanza_el_estado`, y las pruebas de abajo fijan los dos lados con
    comandos reales del árbol.
    """
    datos = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    scripts: dict[str, str] = datos.get("project", {}).get("scripts", {})
    return frozenset(
        nombre
        for nombre, destino in scripts.items()
        if destino.startswith(f"{_PAQUETE}.") and _alcanza_el_estado(destino.split(":")[0])
    )


def _invoca_al_motor(texto: str) -> bool:
    """¿Este workflow EJECUTA el motor, o solo lo nombra?

    Se exige que el comando aparezca como una orden -principio de línea o tras
    un `run:`, un `uv run`, un `&&` o similar- y no dentro de una frase. Un
    comentario que diga «esto todavía no llama a `sirius-motor`» no cuenta.
    """
    for comando in _comandos_que_mutan_el_estado():
        if re.search(rf"(?m)(?:^|[|&;]|\brun:|\buv run )\s*{re.escape(comando)}\b", texto):
            return True
    return bool(re.search(rf"(?m)python3?\s+-m\s+{re.escape(_PAQUETE)}\b", texto))


def _workflows() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml"))


def _pasos_de(trabajo: Mapping[str, Any]) -> str:
    """Todo el texto ejecutable de un trabajo, para buscar la invocación."""
    pasos = trabajo.get("steps") or []
    trozos: list[str] = []
    for paso in pasos:
        if isinstance(paso, Mapping):
            trozos.extend(str(v) for k, v in paso.items() if k in {"run", "uses", "with"})
    return "\n".join(trozos)


def _concurrency_efectiva(datos: Mapping[str, Any], trabajo: Mapping[str, Any]) -> Any:
    """La que de verdad protege a ese trabajo.

    GitHub admite `concurrency` a nivel de workflow y a nivel de trabajo, y las
    dos serializan. Mirar solo la de arriba señalaría como desprotegido un
    workflow correctamente protegido por trabajo -un falso positivo-, y una
    guarda que grita donde no debe acaba desactivada. La del trabajo manda sobre
    la del workflow, que es como lo resuelve GitHub.
    """
    propia = trabajo.get("concurrency")
    return propia if propia is not None else datos.get("concurrency")


#: Un `git push` dentro de un workflow del motor muta el mismo estado compartido
#: que el motor: el diario versionado. Tiene que estar serializado igual.
_EMPUJA = re.compile(r"(?m)\bgit\s+push\b")


def _toca_el_estado_compartido(trabajo: Mapping[str, Any]) -> bool:
    """¿Este trabajo invoca al motor, o confirma su memoria?

    Las dos cosas mutan lo mismo. Mirar solo la primera dejaba fuera al trabajo
    que hace `git push` del diario -exactamente el que existiria si alguien
    partiera el cableado en dos-, y ese es el que de verdad escribe. Lo encontro
    un escéptico al que se le pidió tumbar la separación en dos trabajos, y
    tenía razón: la guarda vigilaba al que decide, no al que muta.
    """
    texto = _pasos_de(trabajo)
    return _invoca_al_motor(texto) or bool(_EMPUJA.search(texto))


def _invocaciones_del_motor() -> list[tuple[str, str, Any]]:
    """(workflow, trabajo, concurrency efectiva) por cada trabajo a vigilar.

    El workflow entra en el alcance si INVOCA al motor; dentro de él se vigila
    todo trabajo que invoque al motor o que empuje al repositorio.
    """
    encontradas: list[tuple[str, str, Any]] = []
    for ruta in _workflows():
        texto = ruta.read_text(encoding="utf-8")
        if not _invoca_al_motor(texto):
            continue
        datos = yaml.safe_load(texto) or {}
        trabajos = datos.get("jobs") or {}
        for nombre, trabajo in trabajos.items():
            if not isinstance(trabajo, Mapping):
                continue
            if _toca_el_estado_compartido(trabajo):
                encontradas.append((ruta.name, str(nombre), _concurrency_efectiva(datos, trabajo)))
    return encontradas


# --- Anti-vacua que NO depende del árbol -----------------------------------
#
# Las pruebas de abajo recorren los workflows que invocan al motor. Hoy pueden
# ser cero -el cableado es este mismo bloque-, y una batería que recorre una
# lista vacía pasa en verde sin comprobar nada. Esta prueba corre siempre y
# sobre muestras fijas, así que si el detector se queda inerte se rompe aquí.

INVOCACIONES_DE_VERDAD = (
    "      run: sirius-motor avanzar",
    "      run: uv run sirius-despachar --ensayo",
    "        run: |\n          cd x && sirius-racha contar",
    "      run: python -m sirius_engine.cli",
)

SOLO_MENCIONES = (
    "# este workflow todavia no invoca sirius-motor",
    "      # pendiente: cablear sirius_engine aqui (D2)",
    "      run: echo 'el motor se llama sirius-motor'",
)


def test_el_detector_reconoce_una_invocacion_y_no_una_mera_mencion() -> None:
    for muestra in INVOCACIONES_DE_VERDAD:
        assert _invoca_al_motor(muestra), f"el detector ya no reconoce una invocación: {muestra!r}"

    for muestra in SOLO_MENCIONES:
        assert not _invoca_al_motor(muestra), (
            f"el detector confunde nombrar con invocar: {muestra!r}. Con ese "
            "criterio, un comentario obligaría a poner un grupo de concurrencia."
        )


def test_los_comandos_del_motor_se_derivan_y_no_estan_vacios() -> None:
    """Anti-vacua de la derivación: si `[project.scripts]` cambia de forma, salta."""
    comandos = _comandos_del_motor()
    assert comandos, (
        "no se derivó ningún comando del motor de pyproject.toml: la derivación "
        "se rompió y con ella el detector entero"
    )
    assert "sirius-motor" in comandos, f"falta el comando del motor; derivados: {sorted(comandos)}"


# --- Lo que se exige al cableado -------------------------------------------


def test_toda_invocacion_del_motor_esta_serializada() -> None:
    sin_proteger = [
        f"{w}:{j}" for w, j, conc in _invocaciones_del_motor() if not isinstance(conc, Mapping)
    ]
    assert sin_proteger == [], (
        f"estos trabajos mutan el estado del motor -lo invocan o empujan su "
        f"diario- sin grupo de concurrencia: {sin_proteger}. "
        "Dos a la vez despachan el mismo trabajo dos veces (ADR-082); la medición "
        "está en tests/engine/test_exclusion_entre_invocaciones.py."
    )


def test_el_grupo_de_concurrencia_del_motor_es_constante() -> None:
    """Un grupo que varía por evento no serializa nada: cada invocación va al suyo."""
    variables = [
        (f"{w}:{j}", str(conc.get("group")))
        for w, j, conc in _invocaciones_del_motor()
        if isinstance(conc, Mapping) and "${{" in str(conc.get("group", ""))
    ]
    assert variables == [], (
        f"el grupo de concurrencia del motor varía por evento: {variables}. "
        "Dos invocaciones distintas caerían en grupos distintos y no se "
        "serializarían entre sí, que es justo lo que hay que impedir."
    )


def test_el_motor_espera_su_turno_en_vez_de_matar_al_que_va() -> None:
    """`cancel-in-progress: true` dejaría el diario a medias en vez de protegerlo."""
    cancelan = [
        f"{w}:{j}"
        for w, j, conc in _invocaciones_del_motor()
        if isinstance(conc, Mapping) and conc.get("cancel-in-progress") is True
    ]
    assert cancelan == [], (
        f"estos trabajos cancelan una ejecución en curso del motor: {cancelan}. "
        "Cancelar no protege el diario: lo deja a medias. Se espera, no se mata."
    )


def test_los_dos_lados_de_la_distincion_existen_de_verdad() -> None:
    """Anti-vacua de la derivación, con comandos reales de este árbol.

    Si `_alcanza_el_estado` se rompiera y devolviera siempre `False`, la puerta
    entera dejaría de vigilar nada y todas las pruebas de arriba pasarían en
    vacío. Si devolviera siempre `True`, volveríamos al criterio ancho sin que
    nadie se enterase. Esto fija los dos lados.
    """
    mutan = _comandos_que_mutan_el_estado()
    todos = _comandos_del_motor()

    assert mutan, "ningún comando del motor alcanza el almacén: la derivación se rompió"
    assert mutan < todos, (
        "todos los comandos del motor alcanzan el almacén: la derivación no distingue nada"
    )
    # `sirius-reflejar` escribe en el almacén; `sirius-tablero` solo lee el
    # espejo de GitHub y escribe un comentario.
    assert "sirius-reflejar" in mutan
    assert "sirius-motor" in mutan
    assert "sirius-tablero" in todos
    assert "sirius-tablero" not in mutan


def test_la_derivacion_sigue_los_imports_hacia_dentro() -> None:
    """El almacén a dos saltos también cuenta, con un grafo de mentira.

    En este árbol no hay hoy ningún comando que llegue al almacén sin
    importarlo directamente, así que el recorrido en profundidad no lo
    ejercita nada real y sin esta prueba sería una rama muerta que nadie ve
    romperse. El error que evita va en la dirección peligrosa: clasificar como
    de solo lectura algo que sí puede mover trabajo.
    """
    grafo = {
        "sirius_engine.entrada_falsa": {"sirius_engine.ayudante_falso"},
        "sirius_engine.ayudante_falso": {"sirius_engine.ports.store"},
        "sirius_engine.entrada_inocua": {"sirius_engine.otro_inocuo"},
        "sirius_engine.otro_inocuo": {"json"},
    }
    importados = grafo.get

    assert _alcanza_el_estado(
        "sirius_engine.entrada_falsa", importados=lambda m: importados(m, set())
    )
    assert not _alcanza_el_estado(
        "sirius_engine.entrada_inocua", importados=lambda m: importados(m, set())
    )


def test_la_derivacion_no_se_cuelga_con_imports_circulares() -> None:
    """Dos módulos que se importan entre sí no pueden dejar la puerta girando."""
    grafo = {
        "sirius_engine.uno": {"sirius_engine.dos"},
        "sirius_engine.dos": {"sirius_engine.uno"},
    }
    assert not _alcanza_el_estado("sirius_engine.uno", importados=lambda m: grafo.get(m, set()))
