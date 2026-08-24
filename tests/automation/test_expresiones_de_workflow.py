"""Un workflow que GitHub no sabe leer no puede pasar en verde (D2, #296).

El 24-08-2026 se fusionó un cambio en `motor-sirius.yml` con
``${{ runner.temp }}`` en el bloque ``env:`` **del trabajo**. GitHub rechaza ese
fichero al leerlo -«Unrecognized named-value: 'runner'»-, así que el workflow
dejó de arrancar.

Y pasó por Quality en verde, porque **Quality no mira los ficheros de workflow**.
Ni valida su sintaxis ni sus expresiones. El error solo se vio al intentar
lanzarlo, y para entonces ya estaba en `main`.

Esta batería cierra ese hueco para la clase concreta que costó el fallo. No
pretende validar todo lo que GitHub valida -eso sería reimplementar su
intérprete- y ese límite está escrito, no escondido.

**Lo que NO cubre, y conviene saberlo:** el segundo intento de arreglo puso
``${RUNNER_TEMP}`` en ese mismo sitio. Para GitHub es válido -es texto- pero
bash no expande el CONTENIDO de una variable, así que la ruta habría quedado
literal con el dólar dentro. Un fallo peor, porque parece correcto. Esta guarda
no lo caza: eso lo caza ejecutar el workflow, y por eso ejecutarlo sigue siendo
obligatorio antes de dar nada por bueno.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
WORKFLOWS = RAIZ / ".github" / "workflows"

#: Contextos que GitHub NO conoce al evaluar el `env:` de un trabajo: se
#: resuelven ya dentro de un paso. La lista es corta a propósito -solo lo que se
#: ha visto romper- en vez de una copia de la documentación.
PROHIBIDOS_EN_ENV_DE_TRABAJO = frozenset({"runner", "steps", "job"})

_EXPRESION = re.compile(r"\$\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\.")


def _workflows() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml"))


def _contextos(valor: object) -> set[str]:
    return set(_EXPRESION.findall(str(valor)))


def _env_de_trabajos(datos: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(trabajo, variable, valor) por cada variable del `env:` de un trabajo."""
    encontradas = []
    for nombre, trabajo in (datos.get("jobs") or {}).items():
        if not isinstance(trabajo, dict):
            continue
        for clave, valor in (trabajo.get("env") or {}).items():
            encontradas.append((str(nombre), str(clave), str(valor)))
    return encontradas


# --- Anti-vacuas: el detector no puede quedarse inerte --------------------

MALO = "${{ runner.temp }}/memoria"
BUENO = "${{ github.workspace }}/memoria"


def test_el_detector_distingue_el_contexto_prohibido_del_permitido() -> None:
    assert _contextos(MALO) & PROHIBIDOS_EN_ENV_DE_TRABAJO, (
        "el detector ya no reconoce el contexto que costó el fallo"
    )
    assert not _contextos(BUENO) & PROHIBIDOS_EN_ENV_DE_TRABAJO, (
        "el detector marca como prohibido un contexto que sí vale ahí"
    )


def test_hay_workflows_que_revisar() -> None:
    assert len(_workflows()) > 5, "no se encontraron workflows: la batería pasaría en vacío"


# --- Lo que se exige ------------------------------------------------------


def test_ningun_env_de_trabajo_usa_un_contexto_que_github_no_conoce_ahi() -> None:
    culpables: list[str] = []
    for ruta in _workflows():
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        for trabajo, clave, valor in _env_de_trabajos(datos):
            malos = sorted(_contextos(valor) & PROHIBIDOS_EN_ENV_DE_TRABAJO)
            if malos:
                culpables.append(f"{ruta.name}:{trabajo}.env.{clave} usa {malos}")
    assert culpables == [], (
        "estos workflows no los puede leer GitHub:\n  "
        + "\n  ".join(culpables)
        + "\n\nEsos contextos solo existen dentro de un paso. Publica el valor "
        "desde el primer paso con `>> $GITHUB_ENV`, que es donde `$RUNNER_TEMP` "
        "ya está resuelto."
    )


def test_todos_los_workflows_son_yaml_valido() -> None:
    """Lo mínimo, y hasta hoy tampoco lo comprobaba nadie."""
    rotos: list[str] = []
    for ruta in _workflows():
        try:
            yaml.safe_load(ruta.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            rotos.append(f"{ruta.name}: {error}")
    assert rotos == [], "workflows que no son YAML válido:\n  " + "\n  ".join(rotos)
