"""El estado de V8 vive en un solo sitio (ADR-005).

Tres documentos guardaban cada uno una copia del estado de los bloques de V8 y
el 10 de agosto de 2026 decían tres cosas distintas; el catálogo de defectos y
la tabla de bloques llegaron a contradecirse dentro del mismo archivo. La causa
no fue un descuido: el implementador automático solo puede escribir
`docs/implementation/**`, así que cualquier estado guardado en la raíz se queda
atrás por construcción.

Estas pruebas fijan la disposición que lo corrige. No comprueban que la tabla
diga la verdad —eso no lo puede comprobar una prueba—, sino que el estado esté
declarado en un único lugar, que es lo que hace posible mantenerlo al día.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

REGISTRO_AUTORITATIVO = REPO_ROOT / "docs" / "implementation" / "V8_EXECUTION.md"

# Documentos que describen el plan y lo construido, pero que no deben declarar
# en qué punto está cada bloque. Deliberadamente NO se incluyen `docs/audits/`
# ni `docs/evolution/`: son registros fechados y deben quedar congelados.
DOCUMENTOS_SIN_ESTADO = (
    REPO_ROOT / "REPOSITORY_STATUS.md",
    REPO_ROOT / "docs" / "implementation" / "PLAN.md",
)

# Fila de tabla cuya primera celda es exactamente un identificador de bloque
# (`| B4 | ... |`). Es la forma que toma una tabla de estado por bloque.
FILA_DE_BLOQUE = re.compile(r"^\|\s*B\d{1,2}[a-f]?\s*\|", re.MULTILINE)

# Afirmación de estado en prosa: «B5 está completado», «B12 queda pendiente».
# La ventana intermedia existe porque la frase que se coló decía «Completarlo
# es el contenido de B12, que es el único bloque de V8.1 que sigue pendiente»:
# el verbo no va pegado al identificador. Se acota a 80 caracteres y no puede
# cruzar el final de una frase, para no morder prosa legítima de la siguiente.
#
# El punto se admite SOLO cuando le sigue un dígito. Sin esa excepción el
# patrón no caza nada: «V8.1» está justo en medio de la frase que se coló, y su
# punto cortaba la ventana. Se comprobó midiendo, no razonando.
ESTADO_EN_PROSA = re.compile(
    r"\bB\d{1,2}[a-f]?\b(?:[^.\n]|\.(?=\d)){0,80}?"
    r"\b(?:est[áa]|queda|permanece|sigue)\s+"
    r"(?:completad|pendiente|bloquead|en curso|iniciad|terminad)",
    re.IGNORECASE,
)

# Una cuenta de ficheros escrita a mano caduca en el siguiente merge y vuelve a
# afirmar lo que ya no es cierto. La trazabilidad se lee en
# `TRAZABILIDAD_PA_SP.md`, que sí se comprueba por máquina (ADR-006).
CUENTA_DE_FICHEROS_A_MANO = re.compile(
    r"\b\d{1,3}\s+de\s+los\s+\d{1,3}\s+archivos de prueba",
    re.IGNORECASE,
)

# Fila del catálogo de defectos que declara estado propio. El estado de un
# defecto es el del bloque que lo cierra: tenerlo también aquí fue exactamente
# lo que dejó las dos tablas de `V8_EXECUTION.md` contradiciéndose.
DEFECTO_CON_ESTADO = re.compile(
    r"^\|\s*(?:D-\d{2}|A-\d{2})\s*\|.*\|\s*(?:Abierto|Cerrado)\b",
    re.MULTILINE | re.IGNORECASE,
)


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


@pytest.mark.parametrize("documento", DOCUMENTOS_SIN_ESTADO, ids=lambda ruta: ruta.name)
def test_ningun_documento_salvo_el_registro_declara_estado_por_bloque(
    documento: Path,
) -> None:
    filas = FILA_DE_BLOQUE.findall(_texto(documento))
    assert not filas, (
        f"{documento.relative_to(REPO_ROOT)} contiene una tabla de estado por "
        f"bloque ({len(filas)} filas). Por ADR-005 el estado de V8 se declara "
        f"solo en {REGISTRO_AUTORITATIVO.relative_to(REPO_ROOT)}; aquí debe ir "
        "un enlace, no una copia."
    )


@pytest.mark.parametrize("documento", DOCUMENTOS_SIN_ESTADO, ids=lambda ruta: ruta.name)
def test_ningun_documento_salvo_el_registro_afirma_estado_en_prosa(
    documento: Path,
) -> None:
    afirmaciones = ESTADO_EN_PROSA.findall(_texto(documento))
    assert not afirmaciones, (
        f"{documento.relative_to(REPO_ROOT)} afirma el estado de un bloque en "
        f"prosa: {afirmaciones}. Una frase suelta se queda igual de obsoleta "
        "que una tabla y es más difícil de encontrar."
    )


def test_el_registro_autoritativo_conserva_su_tabla_de_bloques() -> None:
    # Sin esta prueba, las dos anteriores se podrían satisfacer borrando la
    # tabla en vez de centralizándola.
    texto = _texto(REGISTRO_AUTORITATIVO)
    assert "## Bloques operativos" in texto
    filas = FILA_DE_BLOQUE.findall(texto)
    assert len(filas) >= 16, (
        f"La tabla de bloques operativos debe cubrir B1 a B16; se encontraron {len(filas)} filas."
    )


def test_el_catalogo_de_defectos_no_declara_estado_propio() -> None:
    filas = DEFECTO_CON_ESTADO.findall(_texto(REGISTRO_AUTORITATIVO))
    assert not filas, (
        "El catálogo de defectos volvió a declarar estado propio "
        f"({len(filas)} filas con Abierto/Cerrado). El estado de un defecto es "
        "el del bloque que lo cierra; dos tablas del mismo hecho fue lo que "
        "las dejó contradiciéndose."
    )


def test_ningun_documento_vigente_cuenta_ficheros_de_prueba_a_mano() -> None:
    """Una cuenta escrita a mano caduca en el siguiente merge.

    «Solo 15 de los 127 archivos de prueba mencionan un identificador PA o SP»
    era cierto cuando se escribió y falso poco después, y estaba duplicada en
    dos documentos vigentes. La trazabilidad se declara en
    `TRAZABILIDAD_PA_SP.md` y se comprueba por máquina (ADR-006); ahí no
    caduca porque la comprobación falla cuando deja de ser cierta.
    """
    for documento in (REPO_ROOT / "REPOSITORY_STATUS.md", REGISTRO_AUTORITATIVO):
        encontrado = CUENTA_DE_FICHEROS_A_MANO.findall(_texto(documento))
        assert not encontrado, (
            f"{documento.relative_to(REPO_ROOT)} cuenta ficheros de prueba a mano "
            f"({encontrado}). Esa cifra caduca sola; la trazabilidad se lee en "
            "docs/implementation/TRAZABILIDAD_PA_SP.md (ADR-006)."
        )
