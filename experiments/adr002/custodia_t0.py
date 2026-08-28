"""Custodia de ``T0``: que la linea base siga siendo la misma que se congelo.

Los arneses experimentales comprobaban esto midiendo el arbol Git de
``src/sirius`` **en HEAD** contra el que la ficha de ``T0-control v1``
declara. Esa comprobacion mezclaba dos cosas distintas:

- que **este trabajo** no toque Sirius 0.1 productivo, que es lo que hay que
  garantizar;
- que **nadie** lo toque nunca, que no esta en manos de esta rama: ``main``
  avanza por su cuenta, y cuando la PR se pone al dia con el, el arbol de
  ``src/sirius`` cambia sin que ADR-002 haya escrito una linea.

Ocurrio: ``main`` avanzo durante la PR #117 y el arbol paso a ser otro. La
comprobacion vieja daba rojo sin que ninguna pieza que ``T0`` ejecuta hubiera
cambiado, y una comprobacion que falla por algo que no vigila deja de ser una
garantia y pasa a ser ruido.

Lo que aqui se comprueba es **mas estrecho y mas fuerte a la vez**:

1. la **cadena canonica de Alembic** —que es la identidad canonica de ``T0``,
   «la linea base de Sirius 0.1 identificada por el head ``61be4bb269bf``»— es
   byte a byte la del commit del prototipo;
2. **cada modulo que el arnes de ``T0`` ejecuta de verdad** es byte a byte el
   del commit del prototipo;
3. la excepcion declarada —``domain/decision.py``— sigue exponiendo la MISMA
   estructura de ``Decision``, que es lo unico que el arnes usa de ese modulo.

La fe de erratas 07 registra el hecho y su adjudicacion.
"""

from __future__ import annotations

import ast
import subprocess
from dataclasses import fields
from pathlib import Path
from typing import Final

#: Commit que la ficha de ``T0-control v1`` declara como el del prototipo. Es
#: historia de Git y por tanto inmutable: lo que se afirma de el se puede
#: seguir comprobando aunque HEAD avance.
COMMIT_DEL_PROTOTIPO: Final = "c881fce697009d294121c5b99d23ba6af5b8b173"

#: Arbol de ``src/sirius`` que la ficha declara, **en el commit del prototipo**.
ARBOL_DE_FUENTES_CONGELADO: Final = "6d8558ef1fe4994cb15a12967525bf3496b3c0b8"

#: Modulos de Sirius 0.1 que el arnes de ``T0`` importa y ejecuta. La lista sale
#: de leer sus imports, no de suponerlos: si el arnes importase uno mas, habria
#: que anadirlo aqui y volver a comprobarlo contra el commit del prototipo.
SUPERFICIE_QUE_T0_EJECUTA: Final[tuple[str, ...]] = (
    "src/sirius/adapters/persistence/migrations.py",
    "src/sirius/adapters/persistence/sqlite_knowledge_search_repository.py",
    "src/sirius/adapters/persistence/sqlite_memory_repository.py",
    "src/sirius/adapters/persistence/sqlite_decision_repository.py",
    "src/sirius/adapters/persistence/sqlite_project_repository.py",
    "src/sirius/application/rank_relevant_knowledge.py",
    "src/sirius/domain/memory.py",
    "src/sirius/domain/relevance.py",
)

#: Modulo que el arnes importa pero del que solo usa una estructura de datos.
#: Se declara aparte, con su motivo, en vez de meterlo en la lista de arriba y
#: relajar la igualdad para todos.
EXCEPCION_DECLARADA: Final = "src/sirius/domain/decision.py"

#: Nombre de la estructura que el arnes recibe del repositorio. Es lo unico
#: que usa de ``EXCEPCION_DECLARADA``, y por eso es lo unico que hay que fijar.
#: Sus campos NO se transcriben aqui: se leen del fichero congelado, para que
#: la comparacion sea contra el commit del prototipo y no contra una copia a
#: mano que podria envejecer sin que nadie lo note.
ESTRUCTURA_QUE_T0_USA: Final = "Decision"


class CustodiaNoComprobableError(RuntimeError):
    """Falta historial de Git para comprobar la custodia. No es un aprobado."""


def _objeto(raiz: Path, referencia: str) -> str:
    resultado = subprocess.run(
        ["git", "rev-parse", referencia],
        cwd=str(raiz),
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode != 0:
        msg = f"no se pudo resolver {referencia}: {resultado.stderr.strip()}"
        raise CustodiaNoComprobableError(msg)
    return resultado.stdout.strip()


def fallos_de_custodia_de_t0(raiz: Path) -> list[str]:
    """Los tres controles del encabezado. Lista vacia = custodia intacta."""
    fallos: list[str] = []

    declarado = _objeto(raiz, f"{COMMIT_DEL_PROTOTIPO}:src/sirius")
    if declarado != ARBOL_DE_FUENTES_CONGELADO:
        fallos.append(
            f"el arbol de src/sirius en el commit del prototipo es {declarado} y la "
            f"ficha de T0 declara {ARBOL_DE_FUENTES_CONGELADO}"
        )

    congelada = _objeto(raiz, f"{COMMIT_DEL_PROTOTIPO}:migrations")
    vigente = _objeto(raiz, "HEAD:migrations")
    if congelada != vigente:
        fallos.append(
            f"la cadena canonica de Alembic cambio: {congelada} en el commit del "
            f"prototipo y {vigente} en HEAD; T0 esta identificada por ese head"
        )

    for modulo in SUPERFICIE_QUE_T0_EJECUTA:
        antes = _objeto(raiz, f"{COMMIT_DEL_PROTOTIPO}:{modulo}")
        ahora = _objeto(raiz, f"HEAD:{modulo}")
        if antes != ahora:
            fallos.append(f"{modulo} cambio desde el commit del prototipo: {antes} -> {ahora}")

    return fallos


def _campos_congelados(raiz: Path) -> tuple[str, ...]:
    """Campos de ``Decision`` leidos del fichero **del commit del prototipo**."""
    resultado = subprocess.run(
        ["git", "show", f"{COMMIT_DEL_PROTOTIPO}:{EXCEPCION_DECLARADA}"],
        cwd=str(raiz),
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode != 0:
        msg = f"no se pudo leer {EXCEPCION_DECLARADA} congelado: {resultado.stderr.strip()}"
        raise CustodiaNoComprobableError(msg)
    arbol = ast.parse(resultado.stdout)
    for nodo in arbol.body:
        if isinstance(nodo, ast.ClassDef) and nodo.name == ESTRUCTURA_QUE_T0_USA:
            return tuple(
                campo.target.id
                for campo in nodo.body
                if isinstance(campo, ast.AnnAssign) and isinstance(campo.target, ast.Name)
            )
    msg = f"{ESTRUCTURA_QUE_T0_USA} no existe en el fichero congelado"
    raise CustodiaNoComprobableError(msg)


def fallos_de_la_excepcion_declarada(raiz: Path) -> list[str]:
    """``Decision`` conserva su estructura: es lo unico que el arnes usa de ella.

    La comparacion es contra el fichero **del commit del prototipo**, no contra
    una lista transcrita a mano: una copia a mano envejeceria en silencio y
    dejaria de comprobar lo que dice comprobar.
    """
    from sirius.domain.decision import Decision

    congelados = _campos_congelados(raiz)
    observados = tuple(campo.name for campo in fields(Decision))
    if observados != congelados:
        return [
            f"la estructura de {ESTRUCTURA_QUE_T0_USA} cambio: {observados} en vez de "
            f"{congelados}; el arnes de T0 la recibe del repositorio y depende de ella"
        ]
    return []


__all__ = [
    "ARBOL_DE_FUENTES_CONGELADO",
    "COMMIT_DEL_PROTOTIPO",
    "ESTRUCTURA_QUE_T0_USA",
    "EXCEPCION_DECLARADA",
    "SUPERFICIE_QUE_T0_EJECUTA",
    "CustodiaNoComprobableError",
    "fallos_de_custodia_de_t0",
    "fallos_de_la_excepcion_declarada",
]
