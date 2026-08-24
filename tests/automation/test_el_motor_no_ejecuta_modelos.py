"""El motor es determinista, y eso tiene que seguir siendo verdad (D2, #296).

ADR-082 apoya una decisión de seguridad en un hecho: **el motor no ejecuta
ningún modelo**. De ahí sale que un solo trabajo con permiso de escritura
cumple sola la propiedad de ADR-016 —«el trabajo que ejecuta el modelo no puede
escribir»—, y que partir el cableado en dos no compra nada.

Ese hecho se comprobó a mano el 24-08-2026 y **nada lo sostenía**. Lo señaló el
revisor independiente, con razón: una premisa que sostiene una decisión de
seguridad y que solo vive en la prosa de un ADR se vuelve falsa el día en que
alguien añada un `import`, y nadie se entera. La guarda que debería avisar
—`test_auditor_workflow.py`— reconoce un modelo solo por el campo ``uses:`` de
un paso de workflow, así que al motor no lo mira siquiera.

Esta batería lo convierte en algo que se rompe. No dice que ejecutar un modelo
esté mal: dice que **si el motor empieza a poder hacerlo, ADR-082 hay que
releerlo**, porque su decisión estaba tomada sobre lo contrario.

Lo que NO cubre, dicho aquí para que nadie lo lea de más: que el motor invoque
un modelo a través de algo que ya está permitido —un `gh` que dispare una acción
con modelo, por ejemplo—. Eso no es un import y esta prueba no lo ve. Cubre la
vía directa, que es la que la decisión daba por cerrada.
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "src" / "sirius_engine"

#: Bibliotecas por las que un programa habla con un modelo, o con cualquier cosa
#: por HTTP. Se incluye el HTTP genérico a propósito: el motor solo sale al
#: exterior por `gh` y `git`, así que una biblioteca de red aquí ya es la señal
#: de que esa frontera se movió, sea para hablar con un modelo o no.
RAICES_PROHIBIDAS = frozenset(
    {
        "anthropic",
        "openai",
        "google",
        "cohere",
        "mistralai",
        "litellm",
        "langchain",
        "transformers",
        "ollama",
        "httpx",
        "requests",
        "aiohttp",
        "urllib3",
    }
)

#: Los únicos binarios que el motor puede lanzar. `gh` para hablar con GitHub y
#: `git` para el árbol; cualquier otro es una vía nueva al exterior.
BINARIOS_PERMITIDOS = frozenset({"gh", "git"})


def _modulos() -> list[Path]:
    return sorted(p for p in MOTOR.rglob("*.py") if "__pycache__" not in p.parts)


def _raices_importadas(codigo: str) -> set[str]:
    """La primera parte de cada módulo importado por este fichero."""
    raices: set[str] = set()
    for nodo in ast.walk(ast.parse(codigo)):
        if isinstance(nodo, ast.Import):
            raices.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            raices.add(nodo.module.split(".")[0])
    return raices


def _binarios_lanzados(codigo: str) -> set[str]:
    """El primer elemento de cada lista literal pasada a `subprocess.*`."""
    binarios: set[str] = set()
    for nodo in ast.walk(ast.parse(codigo)):
        if not isinstance(nodo, ast.Call):
            continue
        objetivo = nodo.func
        if not isinstance(objetivo, ast.Attribute):
            continue
        if not (isinstance(objetivo.value, ast.Name) and objetivo.value.id == "subprocess"):
            continue
        for argumento in nodo.args:
            if isinstance(argumento, ast.List) and argumento.elts:
                primero = argumento.elts[0]
                if isinstance(primero, ast.Constant) and isinstance(primero.value, str):
                    binarios.add(primero.value)
    return binarios


# --- Anti-vacuas: los detectores no pueden quedarse inertes ----------------

MUESTRA_CON_MODELO = "import anthropic\nx = anthropic.Anthropic()\n"
MUESTRA_CON_RED = "from httpx import AsyncClient\n"
MUESTRA_LIMPIA = "import json\nfrom pathlib import Path\n"

MUESTRA_LANZA_OTRO = "import subprocess\nsubprocess.run(['curl', 'https://x'], check=False)\n"
MUESTRA_LANZA_GH = "import subprocess\nsubprocess.run(['gh', 'issue', 'view'], check=False)\n"


def test_el_detector_de_importaciones_reconoce_lo_que_debe() -> None:
    assert _raices_importadas(MUESTRA_CON_MODELO) & RAICES_PROHIBIDAS
    assert _raices_importadas(MUESTRA_CON_RED) & RAICES_PROHIBIDAS
    assert not _raices_importadas(MUESTRA_LIMPIA) & RAICES_PROHIBIDAS


def test_el_detector_de_binarios_reconoce_lo_que_debe() -> None:
    assert _binarios_lanzados(MUESTRA_LANZA_OTRO) - BINARIOS_PERMITIDOS == {"curl"}
    assert _binarios_lanzados(MUESTRA_LANZA_GH) - BINARIOS_PERMITIDOS == set()


def test_hay_modulos_del_motor_que_revisar() -> None:
    """Si el paquete se mueve de sitio, esta batería no puede pasar en vacío."""
    modulos = _modulos()
    assert len(modulos) > 20, f"solo se encontraron {len(modulos)} módulos en {MOTOR}"


# --- La propiedad que ADR-082 da por cierta --------------------------------


def test_el_motor_no_importa_ninguna_via_directa_a_un_modelo() -> None:
    culpables: list[str] = []
    for modulo in _modulos():
        prohibidas = _raices_importadas(modulo.read_text(encoding="utf-8")) & RAICES_PROHIBIDAS
        if prohibidas:
            culpables.append(f"{modulo.relative_to(RAIZ)}: {sorted(prohibidas)}")
    assert culpables == [], (
        "el motor ha adquirido una vía directa a un modelo o a la red:\n  "
        + "\n  ".join(culpables)
        + "\n\nADR-082 decidió los permisos del cableado sobre la premisa de que "
        "esto no ocurría. Si de verdad tiene que ocurrir, hay que releer esa "
        "decisión antes de seguir, no ajustar esta prueba."
    )


def test_el_motor_solo_lanza_gh_y_git() -> None:
    culpables: list[str] = []
    for modulo in _modulos():
        otros = _binarios_lanzados(modulo.read_text(encoding="utf-8")) - BINARIOS_PERMITIDOS
        if otros:
            culpables.append(f"{modulo.relative_to(RAIZ)}: {sorted(otros)}")
    assert culpables == [], (
        "el motor lanza binarios fuera de los dos permitidos:\n  "
        + "\n  ".join(culpables)
        + "\n\nMisma advertencia: la premisa de ADR-082 era que el motor solo "
        "sale al exterior por `gh` y `git`."
    )
