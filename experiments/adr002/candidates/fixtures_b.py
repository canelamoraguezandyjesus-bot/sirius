"""Fixture tecnico propio para las pruebas de ``ADR002-B``.

**No es el corpus oficial del benchmark** y no puede serlo: evaluar al
candidato con el corpus congelado v0.4 exige una autorizacion que no existe.
Es un fixture pequeno cuya relacion semantica **emerge de contextos de
coocurrencia declarados**, no de una tabla de sinonimos ni de una etiqueta
esperada:

- ``faro`` y ``baliza`` **no coocurren en ningun elemento**. Lo que los une es
  de segundo orden: ambos coocurren con ``senala`` y ``oscuridad`` en
  elementos distintos (los documentos puente 2-3 para ``faro`` y 4, 7, 10 y
  11 para ``baliza``).
- El objetivo exclusivo de B (``baliza-espigon``) no comparte con la consulta
  ``faro`` ni un token, ni una variante morfologica, ni un termino puente de
  las semillas, ni una familia de sujeto: ``ADR002-A`` no puede alcanzarlo
  por construccion, y la unica via es la similitud distribucional.
- Los controles de puertas son igual de deliberados: un elemento proximo
  fuera de ambito solo alcanzable por vector (``baliza-forastera``), uno
  proximo no vigente (``baliza-retirada``), uno proximo con polaridad opuesta
  solo alcanzable por vector (``baliza-averiada``) y uno posterior al corte
  temporal (``baliza-futura``).

El esquema es el canonico de Sirius 0.1 —la cadena de Alembic hasta
``61be4bb269bf``— y el sidecar vectorial se construye aparte, con el ciclo de
vida de ``adr002_b.vectores``.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from experiments.adr002.candidates.adr002_b import vectores

from sirius.adapters.persistence.migrations import upgrade_to_head

_TS: Final = "2026-06-01T00:00:00"
_TS_TARDIO: Final = "2026-09-01T00:00:00"

PROYECTO_ACTIVO: Final = "1"
PROYECTO_AJENO: Final = "2"

#: El elemento que SOLO la senal vectorial de B puede alcanzar desde "faro".
OBJETIVO_SOLO_B: Final = "baliza-espigon"

#: (subject_key, texto, vigente, proyecto_activo, created_at)
_MEMORIAS: Final[tuple[tuple[str, str, bool, bool, str], ...]] = (
    # Semilla E1 para la consulta "faro". Sus tokens restantes son df=1.
    ("faro-costa", "el faro ilumina la costa cada noche", True, True, _TS),
    # Documentos puente del lado "faro": coocurre con senala/oscuridad.
    ("faro-bocana", "el faro senala la bocana en la oscuridad", True, True, _TS),
    ("faro-darsena", "el faro senala la darsena en la oscuridad", True, True, _TS),
    # Documentos puente del lado "baliza": coocurre con senala/oscuridad.
    # Alcanzables por la E3 lexica de A via terminos puente (senala, oscuridad).
    ("baliza-canal", "la baliza senala el canal en la oscuridad", True, True, _TS),
    # OBJETIVO SOLO B. Ni un token compartido con las semillas ni con sus
    # puentes; prefijo de sujeto distinto de "faro". Su vector es vec(baliza).
    ("baliza-espigon", "la baliza del espigon parpadea con destellos rojos", True, True, _TS),
    # CONTROL NEGATIVO: sin relacion lexica NI distribucional (todo df=1).
    ("almacen-repuestos", "el almacen guarda repuestos de maquinaria pesada", True, True, _TS),
    # Fuera de ambito, alcanzable tambien por la base (puente): G4 la corta.
    ("baliza-vecina", "la baliza del puerto vecino senala en la oscuridad", True, False, _TS),
    # No vigente: NO entra en el indice vectorial (solo vigentes) y ademas
    # G6/G7 la excluirian.
    ("baliza-retirada", "la baliza antigua senala la darsena en la oscuridad", False, True, _TS),
    # Polaridad NEGATIVA, alcanzable SOLO por vector (tokens df=1 salvo
    # baliza): la similitud no puede fusionarla ni voltearla.
    ("baliza-averiada", "la baliza no destella jamas en el dique", True, True, _TS),
    # Posterior al corte de registro: G8 la corta cuando hay corte.
    ("baliza-futura", "la baliza nueva senala la oscuridad del muelle", True, True, _TS_TARDIO),
    # Refuerzo del lado "baliza" para que la coocurrencia quede por encima
    # de la independencia (PPMI > 0 con margen).
    ("baliza-rompeolas", "la baliza senala el rompeolas en la oscuridad", True, True, _TS),
    # Fuera de ambito y alcanzable SOLO por vector: la prueba de que una
    # similitud alta no supera G4 por el canal vectorial.
    (
        "baliza-forastera",
        "la baliza forastera del atraque brilla intermitente",
        True,
        False,
        _TS,
    ),
)

#: (subject, texto, aprobada, proyecto_activo). La aprobada se indexa; la
#: propuesta NO (el indice solo admite decisiones aprobadas).
_DECISIONES: Final[tuple[tuple[str, str, bool, bool], ...]] = (
    ("luces-mantenimiento", "se aprueba el mantenimiento anual de las luces", True, True),
    ("boya-retirada", "se propone retirar la boya del canal", False, True),
)

#: Historial: nunca entra en el indice vectorial.
_MENSAJES: Final[tuple[str, ...]] = (
    "el patron comento la marejada de ayer",
    "alguien pregunto por el estado del puerto",
)


@dataclass(frozen=True, slots=True)
class FixtureB:
    """Base canonica, ruta del sidecar y textos que la traza NO debe filtrar."""

    ruta: Path
    sidecar: Path
    textos: tuple[str, ...]


def construir_base(destino: Path) -> FixtureB:
    """Base con el esquema canonico y el fixture de B. No construye el sidecar."""
    upgrade_to_head(destino)
    conexion = sqlite3.connect(str(destino))
    conexion.execute("PRAGMA foreign_keys=ON")
    try:
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO conversations (created_at, is_main) VALUES (?, 1)", (_TS,))
        conversation_id = int(cursor.lastrowid or 0)
        cursor.execute("INSERT INTO identities (created_at) VALUES (?)", (_TS,))
        identity_id = int(cursor.lastrowid or 0)
        cursor.execute(
            "INSERT INTO identity_versions (identity_id, version, name, description, "
            "personality_instructions, is_current, created_at) VALUES (?, 1, ?, ?, ?, 1, ?)",
            (identity_id, "Sirius", "pruebas tecnicas de B", "sin instrucciones", _TS),
        )
        for nombre, activo in (("Proyecto activo", 1), ("Proyecto ajeno", 0)):
            cursor.execute(
                "INSERT INTO projects (name, objective, current_state, next_step, is_active, "
                "created_at, updated_at, blockers, status) VALUES (?, ?, ?, ?, ?, ?, ?, '', "
                "'active')",
                (nombre, "objetivo", "estado", "siguiente", activo, _TS, _TS),
            )
        cursor.execute(
            "INSERT INTO events (event_type, actor, message_id, created_at) "
            "VALUES ('memory.created', 'user', NULL, ?)",
            (_TS,),
        )
        event_id = int(cursor.lastrowid or 0)

        for clave, texto, vigente, activo, creado in _MEMORIAS:
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

        for asunto, texto, aprobada, activo in _DECISIONES:
            cursor.execute(
                "INSERT INTO decisions (subject, project_id, status, created_at, updated_at, "
                "supersedes_decision_id) VALUES (?, ?, ?, ?, ?, NULL)",
                (
                    asunto,
                    int(PROYECTO_ACTIVO) if activo else int(PROYECTO_AJENO),
                    "approved" if aprobada else "proposed",
                    _TS,
                    _TS,
                ),
            )
            decision_id = int(cursor.lastrowid or 0)
            cursor.execute(
                "INSERT INTO decision_revisions (decision_id, version, content, "
                "source_event_id, is_current, created_at) VALUES (?, 1, ?, NULL, 1, ?)",
                (decision_id, texto, _TS),
            )

        for indice, texto in enumerate(_MENSAJES):
            cursor.execute(
                "INSERT INTO messages (conversation_id, sequence, role, content, created_at, "
                "operation_id, identity_version, status) VALUES (?, ?, 'user', ?, ?, ?, 1, "
                "'completed')",
                (conversation_id, indice, texto, _TS, f"op-b-{indice}"),
            )
        conexion.commit()
    finally:
        conexion.close()

    textos = (
        *(t for _c, t, _v, _a, _f in _MEMORIAS),
        *(t for _s, t, _ap, _a in _DECISIONES),
        *_MENSAJES,
    )
    return FixtureB(
        ruta=destino,
        sidecar=Path(f"{destino}.vectores.db"),
        textos=textos,
    )


def construir_sidecar(fixture: FixtureB) -> None:
    """Construye el indice vectorial del fixture con el ciclo de vida real."""
    vectores.construir(fixture.ruta, fixture.sidecar)


def identificador_de(ruta: Path, clave: str) -> str:
    """El identificador canonico ``MEMORIA:<id>`` de una clave de sujeto."""
    conexion = sqlite3.connect(str(ruta))
    try:
        fila = conexion.execute(
            "SELECT id FROM memories WHERE subject_key = ? ORDER BY id LIMIT 1", (clave,)
        ).fetchone()
        if fila is None:
            msg = f"clave sin memoria en el fixture: {clave}"
            raise LookupError(msg)
        return f"MEMORIA:{int(fila[0])}"
    finally:
        conexion.close()


def anadir_memoria(ruta: Path, clave: str | None, texto: str, *, activo: bool = True) -> int:
    """Inserta una memoria vigente y devuelve su id canonico numerico.

    ``clave`` admite ``None``: el canon real contiene memorias sin clave de
    sujeto, y las pruebas del paquete de correccion 02 necesitan exactamente
    ese caso para demostrar que una clave vacia ya no pierde coincidencias.
    """
    conexion = sqlite3.connect(str(ruta))
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO memories (status, created_at, updated_at, subject_key, project_id) "
            "VALUES ('current', ?, ?, ?, ?)",
            (_TS, _TS, clave, int(PROYECTO_ACTIVO) if activo else int(PROYECTO_AJENO)),
        )
        memory_id = int(cursor.lastrowid or 0)
        cursor.execute(
            "INSERT INTO memory_revisions (memory_id, version, content, origin, is_current, "
            "created_at, source_event_id) VALUES (?, 1, ?, 'fixture', 1, ?, NULL)",
            (memory_id, texto, _TS),
        )
        conexion.commit()
        return memory_id
    finally:
        conexion.close()


def anadir_memorias_en_bloque(ruta: Path, clave: str, textos: list[str]) -> list[int]:
    """Inserta muchas memorias vigentes con la MISMA clave de sujeto.

    Es el fixture del limite de 512 filas por clave: el objetivo se situa
    despues de las primeras 512 por orden estable de id, que era exactamente
    lo que la materializacion por clave perdia sin traza.
    """
    conexion = sqlite3.connect(str(ruta))
    try:
        cursor = conexion.cursor()
        identificadores: list[int] = []
        for texto in textos:
            cursor.execute(
                "INSERT INTO memories (status, created_at, updated_at, subject_key, "
                "project_id) VALUES ('current', ?, ?, ?, ?)",
                (_TS, _TS, clave, int(PROYECTO_ACTIVO)),
            )
            memory_id = int(cursor.lastrowid or 0)
            cursor.execute(
                "INSERT INTO memory_revisions (memory_id, version, content, origin, "
                "is_current, created_at, source_event_id) VALUES (?, 1, ?, 'fixture', 1, "
                "?, NULL)",
                (memory_id, texto, _TS),
            )
            identificadores.append(memory_id)
        conexion.commit()
        return identificadores
    finally:
        conexion.close()


def anadir_memoria_inerte(ruta: Path, clave: str, texto: str) -> int:
    """Inserta una memoria vigente de tokens irrelevantes (df=1).

    Sirve para demostrar el desfase del indice: cambia la huella del canon
    sin alterar el vocabulario util, de modo que tras reconstruir el indice
    los resultados vuelven a ser los mismos.
    """
    conexion = sqlite3.connect(str(ruta))
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO memories (status, created_at, updated_at, subject_key, project_id) "
            "VALUES ('current', ?, ?, ?, ?)",
            (_TS, _TS, clave, int(PROYECTO_ACTIVO)),
        )
        memory_id = int(cursor.lastrowid or 0)
        cursor.execute(
            "INSERT INTO memory_revisions (memory_id, version, content, origin, is_current, "
            "created_at, source_event_id) VALUES (?, 1, ?, 'fixture', 1, ?, NULL)",
            (memory_id, texto, _TS),
        )
        conexion.commit()
        return memory_id
    finally:
        conexion.close()


__all__ = [
    "OBJETIVO_SOLO_B",
    "PROYECTO_ACTIVO",
    "PROYECTO_AJENO",
    "FixtureB",
    "anadir_memoria",
    "anadir_memoria_inerte",
    "anadir_memorias_en_bloque",
    "construir_base",
    "construir_sidecar",
    "identificador_de",
]
