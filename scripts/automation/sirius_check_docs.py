#!/usr/bin/env python3
"""Comprobador determinista de documentos de Sirius (bloque C3a, incidencia #246).

Solo implementa las tres comprobaciones que se midieron encontrando defectos
reales sobre este árbol (ver el comentario de medición de la incidencia y
ADR-001): referencias a fichero que no resuelven (incluyendo enlaces vacíos,
dentro de esa misma comprobación, a coste nulo), más de un `h1` por
documento, y saltos de nivel de encabezado. Otras candidatas medidas y
descartadas explícitamente por baja precisión (citas `§N`, `ADR-NNN`, líneas
largas) no están aquí a propósito: no se añaden "ya que estamos".

Una comprobación de anclas (`#slug`) llegó a existir y se **retiró**: sobre los
114 documentos del árbol no había ni un solo enlace de ancla pura, ni un enlace
local con codificación `%XX`, ni una colisión de identificadores; encontró cero
defectos reales, produjo un falso positivo sobre un enlace correcto y consumió
cinco hallazgos de revisión en tres rondas. El criterio de parada de la
incidencia #246 —«una comprobación solo entra si encuentra más defectos reales
que falsos positivos»— decide. Si algún día el repositorio empieza a usar
enlaces de ancla, se vuelve a medir y se decide con datos nuevos.

Alcance de ejecución: **solo los ficheros que se pasan por argumento**, nunca
`docs/**` entero — encenderlo repo-wide exige antes fijar los residuales
heredados que ADR-052 ya fijó para los ADR, y eso es otro trabajo.

Determinista: lee ficheros y, para la clasificación por rama de una cita
rota, consulta referencias de git ya conocidas por el repositorio local (sin
red). No invoca ningún modelo.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# Mismo filtro que `tests/automation/test_citas_de_los_adr.py`: una cita solo
# cuenta si empieza por una de estas raíces. Ramas, repositorios de terceros y
# módulos de Python no se pueden distinguir con certeza, así que no se miran.
RAICES_DEL_REPOSITORIO = (
    ".claude/",
    ".github/",
    "docs/",
    "experiments/",
    "migrations/",
    "scripts/",
    "src/",
    "tests/",
)

# Globos, URLs, plantillas de API y rutas con puntos suspensivos (`...`, `…`)
# no son rutas concretas que se puedan abrir: se descartan enteras. El filtro
# de puntos suspensivos está medido en la incidencia #246: -2 falsos
# positivos sobre este árbol.
NO_ES_UNA_RUTA_CONCRETA = ("://", "*", "{", "}", "<", ">", "...", "…")

CODIGO_EN_LINEA = re.compile(r"`([^`\n]+)`")
ENLACE_MD = re.compile(r"!?\[[^\]]*\]\(([^)]*)\)")
# `fichero.py:95`, `workflow.yml:67-81`, `test_x.py::test_caso`.
SUFIJO_DE_CITA = re.compile(r"::.*$|:\d[\d,\-]*$")
ENCABEZADO = re.compile(r"^(#{1,6})(?:\s+(.*))?$", re.MULTILINE)

# El otro filtro medido en la incidencia #246: la palabra «rama» en los 40
# caracteres previos a la cita descarta 3 falsos positivos sobre este árbol
# (frases que ya declaran de qué rama viene el fichero, como el defecto real
# número 2 que este mismo bloque corrige).
_VENTANA_RAMA = 40

# --- La excepción, fijada por nombre ------------------------------------------
#
# Mismo patrón que `TODAVIA_NO_EXISTEN` en `tests/automation/test_citas_de_los_adr.py`:
# un fichero de excepciones declarado, no un comentario HTML. `sanitize_untrusted_json`
# (`scripts/automation/sirius_issue.sh`) convierte `<!--` en `&lt;!--` al pasar
# por el veredicto, así que una excepción marcada con un comentario HTML en el
# propio documento nunca satisfaría al comprobador. Vacío hoy: el defecto real
# número 2 de la incidencia #246 se resolvió declarando la rama en la propia
# frase (filtro de arriba), no con una excepción — se deja declarada aquí para
# el caso, ya anticipado por la incidencia, en el que una cita rota deba
# tolerarse sin que la frase pueda nombrar la rama.
CITAS_EXCEPCIONADAS: dict[tuple[str, str], str] = {}


@dataclass(frozen=True)
class Hallazgo:
    fichero: Path
    linea: int
    mensaje: str

    def __str__(self) -> str:
        try:
            ruta = self.fichero.relative_to(RAIZ)
        except ValueError:
            ruta = self.fichero
        return f"{ruta}:{self.linea}: {self.mensaje}"


def _enmascarar_bloques(texto: str) -> str:
    """Sustituye el contenido de los bloques de código por espacios.

    Conserva longitud, líneas y columnas exactas, así que los desplazamientos
    calculados sobre el texto enmascarado siguen sirviendo para reportar la
    línea real. Al dudar (una valla sin cerrar), se enmascara todo lo que
    queda: ahí viven salidas de comandos pegadas y rutas de otra máquina.
    """
    salida: list[str] = []
    dentro = False
    for linea in texto.splitlines(keepends=True):
        cuerpo = linea.splitlines()[0] if linea.splitlines() else linea
        resto = linea[len(cuerpo) :]
        if cuerpo.lstrip().startswith(("```", "~~~")):
            dentro = not dentro
            salida.append(" " * len(cuerpo) + resto)
            continue
        salida.append((" " * len(cuerpo) + resto) if dentro else linea)
    return "".join(salida)


def _linea_de(texto: str, offset: int) -> int:
    return texto.count("\n", 0, offset) + 1


def _precedida_por_rama(texto: str, offset: int) -> bool:
    inicio = max(0, offset - _VENTANA_RAMA)
    return "rama" in texto[inicio:offset].lower()


def _contenida_en_raiz(ruta_relativa: str) -> str | None:
    """`ruta_relativa` resuelta y comprobada dentro de RAIZ, o None si se sale.

    Sin esto, una cita como `docs/../../../../etc/hostname` supera el filtro
    de prefijos de RAICES_DEL_REPOSITORIO intacta (empieza por `docs/`) y
    `(RAIZ / ruta).exists()` la resolvería fuera del árbol del repositorio,
    consultando el sistema de ficheros del runner. Mismo patrón que ya usaba
    la rama relativa-al-documento de `_ruta_de_enlace`.
    """
    try:
        return str((RAIZ / ruta_relativa).resolve().relative_to(RAIZ))
    except ValueError:
        return None  # '..' se sale del repositorio: no se comprueba


def ruta_citada(bruto: str) -> str | None:
    """La ruta del repositorio que hay en un `código en línea`, o None.

    None significa «esto no lo sé juzgar», que es la respuesta por defecto.
    """
    texto = bruto.strip()
    if not texto or any(c.isspace() for c in texto):
        return None  # una orden entera, no una cita: `git checkout -- src/x.py`
    if any(marca in texto for marca in NO_ES_UNA_RUTA_CONCRETA):
        return None
    texto = SUFIJO_DE_CITA.sub("", texto.rstrip(".,;:)"))
    texto = texto.removeprefix("./")
    if not texto.startswith(RAICES_DEL_REPOSITORIO):
        return None
    return _contenida_en_raiz(texto)


def _ruta_de_enlace(objetivo: str, documento: Path) -> str | None:
    """La ruta del repositorio citada por un enlace relativo `(...)`, o None.

    Prueba primero la convención rooted-at-repo que ya usan las citas en
    línea de este árbol (`docs/decisions/ADR-001.md`); si no encaja, prueba
    la convención estándar de Markdown, relativa al directorio del propio
    documento (`../decisions/ADR-001.md`).
    """
    parte_ruta = objetivo.strip().partition("#")[0].strip()
    if not parte_ruta:
        return None  # enlace vacío o ancla pura: no es una ruta de fichero
    if any(marca in parte_ruta for marca in NO_ES_UNA_RUTA_CONCRETA):
        return None
    if parte_ruta.startswith(("http://", "https://", "mailto:")):
        return None
    parte_ruta = parte_ruta.removeprefix("./")
    if parte_ruta.startswith("/"):
        candidato = parte_ruta.lstrip("/")
        return (
            _contenida_en_raiz(candidato) if candidato.startswith(RAICES_DEL_REPOSITORIO) else None
        )
    if parte_ruta.startswith(RAICES_DEL_REPOSITORIO):
        return _contenida_en_raiz(parte_ruta)
    try:
        absoluta = (documento.parent / parte_ruta).resolve()
        return str(absoluta.relative_to(RAIZ))
    except ValueError:
        return None  # fuera del repositorio: no se comprueba


def _ramas_con_ruta(ruta: str) -> list[str]:
    """Ramas locales o remotas ya conocidas por este repositorio donde existe `ruta`.

    Sin red: solo mira referencias que git ya tiene (`for-each-ref`). Si el
    runner no ha traído una rama remota, esta función simplemente no la ve —
    y el diseño medido de esta comprobación ya cuenta con ese silencio: «si
    el fichero no existe en ninguna rama [conocida], no se avisa» (0 % de
    precisión medido para ese caso, 4 de 7 avisos sin filtro de rama).
    """
    try:
        listado = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/", "refs/remotes/"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    # Dos cláusulas y no `except (A, B):` a propósito: `ruff format` con
    # `target-version = "py314"` quita los paréntesis y deja sintaxis de PEP 758,
    # que el `python3` del runner (3.12) no entiende. Es la forma en que esta
    # sintaxis se coló ya una vez en `sirius_convergence.py`. Dos cláusulas
    # sobreviven al formateador y compilan en las dos versiones.
    except OSError:
        return []
    except subprocess.SubprocessError:
        return []
    ramas: list[str] = []
    for rama in listado.stdout.splitlines():
        rama = rama.strip()
        if not rama or rama.endswith("/HEAD"):
            continue
        comprobacion = subprocess.run(
            ["git", "cat-file", "-e", f"{rama}:{ruta}"],
            cwd=RAIZ,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if comprobacion.returncode == 0:
            ramas.append(rama)
    return ramas


def _citas_en(visible: str, documento: Path) -> Iterator[tuple[int, str]]:
    """(offset, ruta) de cada cita de fichero encontrada, en las dos sintaxis."""
    for span in CODIGO_EN_LINEA.finditer(visible):
        if _precedida_por_rama(visible, span.start()):
            continue
        ruta = ruta_citada(span.group(1))
        if ruta is not None:
            yield span.start(), ruta
    for span in ENLACE_MD.finditer(visible):
        if _precedida_por_rama(visible, span.start()):
            continue
        ruta = _ruta_de_enlace(span.group(1), documento)
        if ruta is not None:
            yield span.start(), ruta


def _citas_rotas(documento: Path, texto: str, visible: str) -> list[Hallazgo]:
    hallazgos: list[Hallazgo] = []
    cache_ramas: dict[str, list[str]] = {}
    try:
        doc_relativo = str(documento.relative_to(RAIZ))
    except ValueError:
        doc_relativo = str(documento)
    for offset, ruta in _citas_en(visible, documento):
        if (RAIZ / ruta).exists():
            continue
        if (doc_relativo, ruta) in CITAS_EXCEPCIONADAS:
            continue
        if ruta not in cache_ramas:
            cache_ramas[ruta] = _ramas_con_ruta(ruta)
        ramas = cache_ramas[ruta]
        if not ramas:
            continue  # no existe en ninguna rama conocida: no se avisa (medido)
        hallazgos.append(
            Hallazgo(
                documento,
                _linea_de(texto, offset),
                f"cita `{ruta}` que no resuelve en este árbol; existe en: "
                f"{', '.join(ramas)}. Si es la fuente correcta, nombra la rama en la "
                "propia frase; si ya no aplica, actualiza o retira la cita.",
            )
        )
    return hallazgos


def _enlaces_vacios(documento: Path, texto: str, visible: str) -> list[Hallazgo]:
    hallazgos: list[Hallazgo] = []
    for span in ENLACE_MD.finditer(visible):
        if not span.group(1).strip():
            hallazgos.append(
                Hallazgo(
                    documento,
                    _linea_de(texto, span.start()),
                    "enlace vacío: falta la ruta o URL de destino entre paréntesis",
                )
            )
    return hallazgos


def _encabezados_de(texto: str, visible: str) -> list[tuple[int, int, str]]:
    """(línea, nivel, título) de cada encabezado ATX fuera de bloques de código."""
    resultado = []
    for m in ENCABEZADO.finditer(visible):
        nivel = len(m.group(1))
        titulo = (m.group(2) or "").strip().rstrip("#").strip()
        resultado.append((_linea_de(texto, m.start()), nivel, titulo))
    return resultado


def _un_solo_h1(documento: Path, encabezados: list[tuple[int, int, str]]) -> list[Hallazgo]:
    h1 = [(linea, titulo) for linea, nivel, titulo in encabezados if nivel == 1]
    if len(h1) == 1:
        return []
    if not h1:
        return [
            Hallazgo(
                documento,
                1,
                "el documento no tiene ningún encabezado de nivel 1 (`#`); "
                "se esperaba exactamente uno",
            )
        ]
    lineas = ", ".join(str(linea) for linea, _ in h1)
    return [
        Hallazgo(
            documento,
            h1[1][0],
            f"el documento tiene {len(h1)} encabezados de nivel 1 (`#`) en las líneas "
            f"{lineas}; se esperaba exactamente uno",
        )
    ]


def _sin_saltos_de_nivel(
    documento: Path, encabezados: list[tuple[int, int, str]]
) -> list[Hallazgo]:
    hallazgos: list[Hallazgo] = []
    anterior: int | None = None
    for linea, nivel, titulo in encabezados:
        if anterior is not None and nivel > anterior + 1:
            hallazgos.append(
                Hallazgo(
                    documento,
                    linea,
                    f'salto de nivel de encabezado: de h{anterior} a h{nivel} ("{titulo}"); '
                    f"se esperaba como mucho h{anterior + 1}",
                )
            )
        anterior = nivel
    return hallazgos


def comprobar_documento(documento: Path) -> list[Hallazgo]:
    """Las tres comprobaciones que la medición sostiene, sobre un documento."""
    texto = documento.read_text(encoding="utf-8")
    visible = _enmascarar_bloques(texto)
    encabezados = _encabezados_de(texto, visible)
    hallazgos: list[Hallazgo] = []
    hallazgos += _citas_rotas(documento, texto, visible)
    hallazgos += _enlaces_vacios(documento, texto, visible)
    hallazgos += _un_solo_h1(documento, encabezados)
    hallazgos += _sin_saltos_de_nivel(documento, encabezados)
    return sorted(hallazgos, key=lambda h: h.linea)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Comprobador determinista de documentos de Sirius. Solo mira los "
            "ficheros pasados por argumento, nunca docs/** entero."
        )
    )
    parser.add_argument("documentos", nargs="+", help="Rutas a ficheros Markdown a comprobar.")
    args = parser.parse_args(argv)

    total = 0
    for bruto in args.documentos:
        ruta = Path(bruto).resolve()
        if not ruta.is_file():
            print(f"{bruto}: no es un fichero", file=sys.stderr)
            total += 1
            continue
        for hallazgo in comprobar_documento(ruta):
            print(str(hallazgo))
            total += 1
    if total:
        print(f"\n{total} defecto(s) documental(es) encontrados.", file=sys.stderr)
        return 1
    print("Sin defectos documentales en los ficheros comprobados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
