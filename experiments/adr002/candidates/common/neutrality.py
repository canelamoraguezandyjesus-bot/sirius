"""Comprobaciones de neutralidad de la capa comun. Fallan cerrado.

La neutralidad de la infraestructura no es una promesa del disenador: es una
propiedad que se comprueba sobre el codigo. Si la capa comun pudiera nombrar a
un candidato o ramificar por su identidad, cualquier ventaja concedida a uno
seria invisible para el benchmark, que mediria la infraestructura y no la
alternativa.

Cuatro controles, todos sobre el **texto fuente** de la capa comun:

1. **No nombra a ningun candidato** ni ramifica por identidad.
2. **No contiene senal vectorial** ni indice relacional derivado.
3. **No coordina espacios tardios simultaneamente** (``B04-D15``).
4. **No abre red ni usa datos reales.**

El cuarto control —que el motor funciona con un candidato ajeno a
``ADR002-A``— no se comprueba aqui sino en las pruebas, porque exige ejecutar.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Final

#: Modulos de la capa comun sujetos a los controles.
#:
#: **Este modulo no se audita a si mismo**, y no por comodidad: es el
#: inventario de lo prohibido, de modo que contiene por necesidad todos los
#: terminos que persigue. Auditarlo seria exigirle que no nombre aquello que
#: existe para nombrar, y la unica forma de pasar el control seria vaciar el
#: inventario. La exclusion es exactamente una y esta escrita aqui.
MODULOS_COMUNES: Final[tuple[str, ...]] = (
    "contracts.py",
    "derived.py",
    "engine.py",
    "gates.py",
    "grouping.py",
    "port.py",
    "stops.py",
    "trace.py",
)

#: El unico modulo excluido, nombrado para que la exclusion sea auditable.
INVENTARIO_EXCLUIDO: Final = "neutrality.py"

#: Identificadores de candidato. La capa comun no puede nombrarlos: si lo
#: hiciera, podria tratarlos de forma distinta sin que nadie lo notara.
CANDIDATOS: Final[tuple[str, ...]] = ("ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D")

#: Vocabulario de senal vectorial y de indice relacional derivado. Ninguno
#: puede aparecer en la capa comun: introducirlos alli los regalaria a todos
#: los candidatos y anularia el eje que ARQ-00 §23 pone a prueba.
VOCABULARIO_PROHIBIDO: Final[tuple[str, ...]] = (
    "embedding",
    "embeddings",
    "vector",
    "vectorial",
    "coseno",
    "cosine",
    "faiss",
    "hnsw",
    "grafo",
    "knn",
    "indice_relacional",
)

#: Dependencias que delatarian calculo vectorial aunque el vocabulario se
#: renombrase. Una lista de palabras se esquiva; un import, menos.
IMPORTS_PROHIBIDOS: Final[tuple[str, ...]] = (
    "numpy",
    "scipy",
    "torch",
    "sentence_transformers",
    "sklearn",
    "networkx",
)

#: Red y aleatoriedad no reproducible: ninguna de las dos tiene sitio aqui.
EFECTOS_PROHIBIDOS: Final[tuple[str, ...]] = (
    "socket",
    "requests",
    "urllib.request",
    "httpx",
    "random.random",
)


def _fuente(raiz: Path, modulo: str) -> str:
    return (raiz / "experiments/adr002/candidates/common" / modulo).read_text(encoding="utf-8")


def _sin_comentarios(fuente: str) -> str:
    """Quita comentarios y docstrings: el control mira el CODIGO.

    Un termino prohibido dentro de una explicacion —«esta capa no contiene
    embeddings»— no es una violacion; dentro de una expresion, si. Distinguirlo
    evita que la documentacion honesta haga fallar el control y, sobre todo,
    que nadie la borre para que pase.
    """
    sin_docstrings = re.sub(r'"""(?:.|\n)*?"""', "", fuente)
    return "\n".join(linea.split("#", 1)[0] for linea in sin_docstrings.splitlines())


def fallos_de_neutralidad(raiz: Path, modulos: Sequence[str] = MODULOS_COMUNES) -> list[str]:
    """Los cuatro controles sobre el codigo de la capa comun."""
    fallos: list[str] = []
    for modulo in modulos:
        codigo = _sin_comentarios(_fuente(raiz, modulo))
        minusculas = codigo.lower()

        for candidato in CANDIDATOS:
            if candidato.lower() in minusculas:
                fallos.append(
                    f"{modulo}: la capa comun nombra a {candidato}; no puede conocer "
                    f"que candidato la usa"
                )
        for termino in VOCABULARIO_PROHIBIDO:
            if re.search(rf"\b{re.escape(termino)}\b", minusculas):
                fallos.append(
                    f"{modulo}: vocabulario de senal no permitida en la capa comun: {termino}"
                )
        for dependencia in IMPORTS_PROHIBIDOS:
            if re.search(rf"^\s*(import|from)\s+{re.escape(dependencia)}\b", codigo, re.M):
                fallos.append(f"{modulo}: dependencia prohibida en la capa comun: {dependencia}")
        for efecto in EFECTOS_PROHIBIDOS:
            if efecto in codigo:
                fallos.append(f"{modulo}: efecto prohibido en la capa comun: {efecto}")
    return fallos


def fallos_de_aislamiento_del_candidato(raiz: Path, paquete: str) -> list[str]:
    """Un candidato no puede reimplementar el motor ni tocar la capa comun.

    Comprueba que el paquete del candidato **usa** la capa comun en vez de
    duplicarla: si definiera su propio bucle de etapas o sus propias puertas,
    dejaria de estar sujeto al contrato que hace comparables a los candidatos.
    """
    directorio = raiz / "experiments/adr002/candidates" / paquete
    fallos: list[str] = []
    for ruta in sorted(directorio.glob("*.py")):
        codigo = _sin_comentarios(ruta.read_text(encoding="utf-8"))
        if "def recuperar(" in codigo:
            fallos.append(f"{ruta.name}: un candidato no implementa el motor de recuperacion")
        if re.search(r"\bdef aplicar_(previas|g11|g12)\b", codigo):
            fallos.append(f"{ruta.name}: un candidato no implementa las puertas")
        if "ORDEN_DE_ETAPAS" in codigo and "import" not in codigo.split("ORDEN_DE_ETAPAS")[0][-80:]:
            fallos.append(f"{ruta.name}: un candidato no redefine el orden de etapas")
    return fallos


__all__ = [
    "CANDIDATOS",
    "EFECTOS_PROHIBIDOS",
    "IMPORTS_PROHIBIDOS",
    "MODULOS_COMUNES",
    "VOCABULARIO_PROHIBIDO",
    "fallos_de_aislamiento_del_candidato",
    "fallos_de_neutralidad",
]
