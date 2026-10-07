"""La memoria de Sirius no usa Mem0, Letta, Graphiti ni LangMem (ADR-233).

El plan del robot lo dice en la sección 0.2 (``docs/evolution/PLAN_DEL_ROBOT.md``,
§4, «No se usa»): «Sus cifras las publica quien los vende y no ganan a un buen
sistema sencillo. Se copian sus ideas». Es una decisión, no una prueba de
comportamiento, así que no va en la tabla de ``docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md``:
la vigila esta guarda, que la tabla nombra.

Estática: lee ``pyproject.toml``, ``uv.lock`` y los ``import`` de ``src/`` con
``ast``, sin instalar ni importar nada.

Lo que NO ve: un servicio de esas bibliotecas al que se llamara por red sin su
paquete, o su código copiado dentro de ``src/`` con otro nombre.
"""

from __future__ import annotations

import ast
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[2]

#: Cómo empiezan sus paquetes (mem0ai, letta, letta-client, graphiti-core,
#: langmem) y sus módulos (mem0, letta, letta_client, graphiti_core, langmem).
EXCLUIDAS: tuple[str, ...] = ("mem0", "letta", "graphiti", "langmem")


def _normaliza(nombre: str) -> str:
    return re.sub(r"[-_.]+", "-", nombre).lower()


def excluidas(nombres: Iterable[str]) -> list[str]:
    """Los nombres de paquete o de módulo que son de una biblioteca excluida."""
    return sorted({nombre for nombre in nombres if _normaliza(nombre).startswith(EXCLUIDAS)})


def _requisito(texto: str) -> str:
    """El nombre de un requisito de PEP 508: «httpx>=0.27» da «httpx»."""
    return re.split(r"[\s<>=!~;\[(]", texto.strip(), maxsplit=1)[0]


def _paquetes() -> list[str]:
    proyecto = tomllib.loads((_RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    requisitos: list[str] = list(proyecto.get("project", {}).get("dependencies", []))
    for grupo in proyecto.get("project", {}).get("optional-dependencies", {}).values():
        requisitos += grupo
    for grupo in proyecto.get("dependency-groups", {}).values():
        requisitos += [r for r in grupo if isinstance(r, str)]
    bloqueo = tomllib.loads((_RAIZ / "uv.lock").read_text(encoding="utf-8"))
    return [_requisito(r) for r in requisitos] + [p["name"] for p in bloqueo["package"]]


def _modulos_importados() -> list[str]:
    modulos: list[str] = []
    for fichero in sorted((_RAIZ / "src").rglob("*.py")):
        arbol = ast.parse(fichero.read_text(encoding="utf-8"), filename=str(fichero))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                modulos += [alias.name.split(".")[0] for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
                modulos.append(nodo.module.split(".")[0])
    return modulos


def test_ninguna_dependencia_es_una_biblioteca_de_memoria_excluida() -> None:
    assert excluidas(_paquetes()) == []


def test_ningun_modulo_de_src_importa_una_biblioteca_de_memoria_excluida() -> None:
    assert excluidas(_modulos_importados()) == []


def test_la_guarda_reconoce_cada_biblioteca_excluida_y_nada_mas() -> None:
    assert excluidas(
        [
            "mem0ai",
            "letta-client",
            "letta_client",
            "graphiti-core",
            "LangMem",
            "httpx",
            "sqlite-vec",
        ]
    ) == ["LangMem", "graphiti-core", "letta-client", "letta_client", "mem0ai"]
