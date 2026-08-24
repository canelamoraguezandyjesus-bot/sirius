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

import re
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
WORKFLOWS = RAIZ / ".github" / "workflows"
PYPROJECT = RAIZ / "pyproject.toml"

#: Cualquier forma de invocar al motor: sus comandos instalados, el módulo por
#: `python -m`, o el paquete a secas.
_PAQUETE = "sirius_engine"


def _comandos_del_motor() -> frozenset[str]:
    """Los `[project.scripts]` cuyo destino vive en el paquete del motor."""
    datos = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    scripts: dict[str, str] = datos.get("project", {}).get("scripts", {})
    return frozenset(
        nombre for nombre, destino in scripts.items() if destino.startswith(f"{_PAQUETE}.")
    )


def _invoca_al_motor(texto: str) -> bool:
    """¿Este workflow EJECUTA el motor, o solo lo nombra?

    Se exige que el comando aparezca como una orden -principio de línea o tras
    un `run:`, un `uv run`, un `&&` o similar- y no dentro de una frase. Un
    comentario que diga «esto todavía no llama a `sirius-motor`» no cuenta.
    """
    for comando in _comandos_del_motor():
        if re.search(rf"(?m)(?:^|[|&;]|\brun:|\buv run )\s*{re.escape(comando)}\b", texto):
            return True
    if re.search(rf"(?m)python3?\s+-m\s+{re.escape(_PAQUETE)}\b", texto):
        return True
    return False


def _workflows() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml"))


def _los_que_invocan_al_motor() -> list[Path]:
    return [w for w in _workflows() if _invoca_al_motor(w.read_text(encoding="utf-8"))]


def _bloque_concurrency(texto: str) -> str | None:
    """El bloque `concurrency:` de nivel workflow, si lo hay."""
    casa = re.search(r"(?m)^concurrency:\s*$((?:\n[ \t]+.*|\n)*)", texto)
    return casa.group(1) if casa else None


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


def test_todo_workflow_que_invoca_al_motor_declara_un_grupo_de_concurrencia() -> None:
    sin_grupo = [
        w.name
        for w in _los_que_invocan_al_motor()
        if _bloque_concurrency(w.read_text("utf-8")) is None
    ]
    assert sin_grupo == [], (
        f"estos workflows invocan al motor y no serializan sus invocaciones: {sin_grupo}. "
        "Dos a la vez despachan el mismo trabajo dos veces (ADR-082); la medición "
        "está en tests/engine/test_exclusion_entre_invocaciones.py."
    )


def test_el_grupo_de_concurrencia_del_motor_es_constante() -> None:
    """Un grupo que varía por evento no serializa nada: cada invocación va al suyo."""
    variables = []
    for w in _los_que_invocan_al_motor():
        bloque = _bloque_concurrency(w.read_text("utf-8"))
        if bloque is None:
            continue
        grupo = re.search(r"(?m)^\s*group:\s*(.+)$", bloque)
        if grupo and "${{" in grupo.group(1):
            variables.append((w.name, grupo.group(1).strip()))
    assert variables == [], (
        f"el grupo de concurrencia del motor varía por evento: {variables}. "
        "Dos invocaciones distintas caerían en grupos distintos y no se "
        "serializarían entre sí, que es justo lo que hay que impedir."
    )


def test_el_motor_espera_su_turno_en_vez_de_matar_al_que_va() -> None:
    """`cancel-in-progress: true` dejaría el diario a medias en vez de protegerlo."""
    cancelan = []
    for w in _los_que_invocan_al_motor():
        bloque = _bloque_concurrency(w.read_text("utf-8"))
        if bloque is None:
            continue
        if re.search(r"(?m)^\s*cancel-in-progress:\s*true\b", bloque):
            cancelan.append(w.name)
    assert cancelan == [], (
        f"estos workflows cancelan la invocación en curso del motor: {cancelan}. "
        "Cancelar no protege el diario: lo deja a medias. Se espera, no se mata."
    )
