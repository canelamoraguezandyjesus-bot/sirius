"""Fixture tecnico propio de ``ADR002-D``: dos senales, cada una falsable.

**No es el corpus oficial del benchmark** y no puede serlo: evaluar a un
candidato con el corpus congelado exige una autorizacion que no existe. Es un
fixture pequeno construido **por composicion sobre el de `ADR002-B`**, que ya
tiene la unica pieza dificil —una relacion de segundo orden que emerge de
coocurrencias declaradas y no de una tabla de sinonimos—, y le anade lo que
`ADR002-D` necesita y `ADR002-B` no tenia: un **plano relacional** y elementos
que **solo** una arista explicita puede alcanzar.

El fixture esta disenado para que las dos senales de `D` se puedan falsar por
separado, que es la unica forma de demostrar que `D` tiene dos y no una:

- ``baliza-espigon`` (heredado de `B`) **solo** se alcanza por similitud
  distribucional: no comparte con ``faro`` ni un token, ni una variante, ni un
  termino puente de las semillas, ni familia de sujeto.
- ``almacen-repuestos`` (heredado de `B` como control negativo, aqui ascendido
  a objetivo) **solo** se alcanza por **arista explicita**: su vocabulario es
  entero de frecuencia uno, de modo que no comparte ninguna dimension con la
  consulta y la senal vectorial no puede verlo.

Los demas elementos propios de `D` son **controles de puerta por el canal
relacional**: fuera de ambito, polaridad opuesta, no vigente y posterior al
corte. Todos con vocabulario propio de frecuencia uno, para que su presencia
no altere la estadistica distribucional que sostiene el discriminante de `B`.

El esquema es el canonico de Sirius 0.1 —la cadena de Alembic hasta
``61be4bb269bf``—; el sidecar vectorial se construye con el ciclo de vida de
``adr002_b.vectores`` y el plano relacional con la misma forma de tabla que
lee ``adr002_c.relaciones``.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from experiments.adr002.candidates import fixtures_b
from experiments.adr002.candidates.adr002_b import vectores

_TS: Final = "2026-06-01T00:00:00"
_TS_TARDIO: Final = "2026-09-01T00:00:00"

PROYECTO_ACTIVO: Final = fixtures_b.PROYECTO_ACTIVO
PROYECTO_AJENO: Final = fixtures_b.PROYECTO_AJENO

#: El elemento que SOLO la senal vectorial de D puede alcanzar desde "faro".
OBJETIVO_SOLO_VECTORIAL: Final = fixtures_b.OBJETIVO_SOLO_B

#: El elemento que SOLO la senal relacional de D puede alcanzar desde "faro".
#: En el fixture de `B` es el control negativo justamente porque no tiene
#: relacion lexica NI distribucional con la consulta: por eso sirve aqui.
OBJETIVO_SOLO_RELACIONAL: Final = "almacen-repuestos"

#: La semilla desde la que salen todas las aristas del fixture. La alcanza
#: ``E1`` por coincidencia literal de la consulta.
SEMILLA: Final = "faro-costa"

#: Memorias propias de `D`. Vocabulario entero de frecuencia uno: ninguna
#: comparte token con ``faro``, con ``baliza`` ni entre si, de modo que
#: ninguna es alcanzable por via lexica ni distribucional desde la consulta.
#: (clave, texto, vigente, proyecto_activo, created_at)
_MEMORIAS_DE_D: Final[tuple[tuple[str, str, bool, bool, str], ...]] = (
    # Fuera de ambito, alcanzable SOLO por arista: G4 debe cortarla igual que
    # corta a la vectorial ``baliza-forastera``.
    ("archivo-forastero", "el archivo custodia legajos antiguos del condado", True, False, _TS),
    # Polaridad NEGATIVA, alcanzable SOLO por arista: la relacion no puede
    # voltear ni fusionar la postura.
    ("taller-clausurado", "el taller no repara tornos desgastados", True, True, _TS),
    # No vigente, alcanzable SOLO por arista: G6/G7 deben cortarla.
    ("bodega-retirada", "la bodega guardaba barricas robledas", False, True, _TS),
    # Posterior al corte de registro, alcanzable SOLO por arista: G8 la corta
    # cuando la peticion declara corte.
    ("cantera-posterior", "la cantera extrae granito veteado", True, True, _TS_TARDIO),
    # Destino de una arista de tipo NO expansivo: no debe alcanzarse.
    ("sala-sustituida", "la sala exhibia maquetas navales", True, True, _TS),
    # Destino de la otra arista de tipo NO expansivo: tampoco.
    ("sala-conflictiva", "la sala discutia presupuestos municipales", True, True, _TS),
    # ORIGEN de una arista ENTRANTE a la semilla: la direccion se respeta y
    # este elemento NO debe alcanzarse siguiendo aristas salientes.
    ("patio-remoto", "el patio acumula chatarra oxidada", True, True, _TS),
)

#: Aristas del plano relacional. ``(id, tipo, clave_origen, clave_destino)``.
#: Todas salen de la semilla salvo la ultima, que entra en ella a proposito.
_ARISTAS: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("REL-D01", "DERIVA_DE", SEMILLA, OBJETIVO_SOLO_RELACIONAL),
    ("REL-D02", "APOYA", SEMILLA, "archivo-forastero"),
    ("REL-D03", "APOYA", SEMILLA, "taller-clausurado"),
    ("REL-D04", "APOYA", SEMILLA, "bodega-retirada"),
    ("REL-D05", "APOYA", SEMILLA, "cantera-posterior"),
    ("REL-D06", "SUSTITUYE_A", SEMILLA, "sala-sustituida"),
    ("REL-D07", "CONFLICTO_CON", SEMILLA, "sala-conflictiva"),
    ("REL-D08", "APOYA", "patio-remoto", SEMILLA),
)

#: Extremo legitimo que el puerto **no** materializa: un documento no es un
#: elemento del canon, y una arista hacia el se declara en vez de romper.
_ARISTA_A_DOCUMENTO: Final = ("REL-D09", "APOYA", SEMILLA, "DOC-1")

_DDL_PLANO: Final = """
CREATE TABLE relaciones (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    origen TEXT NOT NULL,
    destino TEXT NOT NULL,
    origen_canonico TEXT,
    destino_canonico TEXT
);
"""


@dataclass(frozen=True, slots=True)
class FixtureD:
    """Base canonica, sidecar vectorial, plano relacional y textos protegidos."""

    ruta: Path
    sidecar: Path
    plano: Path
    textos: tuple[str, ...]

    def identidad(self, clave: str) -> str:
        """El identificador canonico ``MEMORIA:<id>`` de una clave de sujeto."""
        return fixtures_b.identificador_de(self.ruta, clave)


def construir_base(destino: Path) -> FixtureD:
    """Base canonica con el fixture de `B` mas las memorias propias de `D`.

    **No** construye el sidecar ni el plano: quien los quiera los pide, y las
    pruebas de activacion tardia usan a proposito rutas inexistentes.
    """
    base = fixtures_b.construir_base(destino)
    conexion = sqlite3.connect(str(destino))
    conexion.execute("PRAGMA foreign_keys=ON")
    try:
        cursor = conexion.cursor()
        fila = cursor.execute("SELECT id FROM events ORDER BY id LIMIT 1").fetchone()
        event_id = None if fila is None else int(fila[0])
        for clave, texto, vigente, activo, creado in _MEMORIAS_DE_D:
            cursor.execute(
                "INSERT INTO memories (status, created_at, updated_at, subject_key, project_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    "current" if vigente else "archived",
                    creado,
                    creado,
                    clave,
                    int(PROYECTO_ACTIVO) if activo else int(PROYECTO_AJENO),
                ),
            )
            memory_id = int(cursor.lastrowid or 0)
            cursor.execute(
                "INSERT INTO memory_revisions (memory_id, version, content, origin, is_current, "
                "created_at, source_event_id) VALUES (?, 1, ?, 'fixture', 1, ?, ?)",
                (memory_id, texto, creado, event_id),
            )
        conexion.commit()
    finally:
        conexion.close()
    return FixtureD(
        ruta=destino,
        sidecar=base.sidecar,
        plano=Path(f"{destino}.relaciones.db"),
        textos=(*base.textos, *(t for _c, t, _v, _a, _f in _MEMORIAS_DE_D)),
    )


def construir_sidecar(fixture: FixtureD) -> None:
    """Construye el indice vectorial con el ciclo de vida real de ``ADR002-B``."""
    vectores.construir(fixture.ruta, fixture.sidecar)


def construir_plano(
    fixture: FixtureD,
    *,
    aristas: tuple[tuple[str, str, str, str], ...] = _ARISTAS,
    incluir_documento: bool = True,
    destino: Path | None = None,
) -> Path:
    """Escribe el plano relacional del fixture, resolviendo identidades reales.

    Las claves de sujeto se traducen a identidades canonicas ``MEMORIA:<id>``
    leyendo la base: el plano nunca inventa una identidad, y una arista cuyo
    extremo no exista queda con ``destino_canonico`` a ``NULL``, que es
    exactamente lo que la fuente relacional declara como no materializable.
    """
    ruta = destino if destino is not None else fixture.plano
    if ruta.exists():
        ruta.unlink()
    conexion = sqlite3.connect(str(ruta))
    try:
        conexion.executescript(_DDL_PLANO)
        filas = [
            (
                identificador,
                tipo,
                origen,
                destino_clave,
                _identidad_opcional(fixture, origen),
                _identidad_opcional(fixture, destino_clave),
            )
            for identificador, tipo, origen, destino_clave in aristas
        ]
        if incluir_documento:
            identificador, tipo, origen, destino_clave = _ARISTA_A_DOCUMENTO
            filas.append(
                (
                    identificador,
                    tipo,
                    origen,
                    destino_clave,
                    _identidad_opcional(fixture, origen),
                    "DOCUMENTO:1",
                )
            )
        conexion.executemany(
            "INSERT INTO relaciones (id, tipo, origen, destino, origen_canonico, "
            "destino_canonico) VALUES (?, ?, ?, ?, ?, ?)",
            filas,
        )
        conexion.commit()
    finally:
        conexion.close()
    return ruta


def _identidad_opcional(fixture: FixtureD, clave: str) -> str | None:
    try:
        return fixture.identidad(clave)
    except LookupError:
        return None


__all__ = [
    "OBJETIVO_SOLO_RELACIONAL",
    "OBJETIVO_SOLO_VECTORIAL",
    "PROYECTO_ACTIVO",
    "PROYECTO_AJENO",
    "SEMILLA",
    "FixtureD",
    "construir_base",
    "construir_plano",
    "construir_sidecar",
]
