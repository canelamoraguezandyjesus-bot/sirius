"""Puerto de recuperación del motor por etapas sobre el canon de Sirius 0.1
y su FTS5 medido. Adaptado desde
``experiments/adr002/candidates/common/port.py`` (rama
``evidence/adr001-spikes``, PR #117), incidencia #457/ADR-109 — mismo
esquema (``memories``/``memory_revisions``/``decisions``/
``decision_revisions``/``knowledge_fts``), mismo estilo de acceso
(``sqlalchemy.text`` vía ``session_scope``, como
``sqlite_knowledge_search_repository``) en vez de ``sqlite3`` crudo.

**Ninguna ruta ofrece un barrido.** Toda consulta lleva un predicado que la
dirige —clave exacta, término del índice léxico medido o prefijo de
sujeto— y una cota de filas; no existe método que devuelva el canon entero
ni que enumere un proyecto: el ámbito es una puerta de seguridad
(``sirius.domain.staged_engine_gates.aplicar_previas``/``G4``), no un
generador de candidatas.

``historial_y_fuentes`` (``E4``, evidencia atribuida no canónica) siempre
devuelve vacío aquí: ``sirius.domain.relevance.RankedKnowledge`` solo modela
``Memory``/``Decision`` (su invariante de construcción lo exige), así que un
resultado sintético ``MENSAJE:n`` no tiene a qué objeto de dominio real
volver. Cablear el historial de conversación como evidencia de contexto es
una decisión de producto propia, fuera del alcance de esta incidencia.

Sobre los ejes P2 que el esquema canónico no persiste (``ambito``,
``sensibilidad``, ``property_key``, confirmación/validez granular, ventana
de vigencia): en el camino real del producto, ``build_staged_engine_port``
nunca puebla ``ejes_por_identidad`` — no hay migración para esos ejes, y
esta incidencia prohíbe expresamente añadir una. Todo item real que este
puerto entrega lleva ``ejes=SIN_EJES``; las puertas que los necesitan
degradan (ver ``staged_engine_gates``). El banco de 47 casos, en cambio,
instancia ``StagedEnginePort`` directamente con ``ejes_por_identidad``
poblado desde el corpus congelado
(``tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py``).
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Final

from sqlalchemy import Engine, RowMapping, text
from sqlalchemy.orm import Session, sessionmaker

from sirius.adapters.persistence.database import build_engine, build_session_factory, session_scope
from sirius.domain.staged_engine_contracts import (
    Clase,
    ClaseDeEvidencia,
    EjesDeclarados,
    ItemCanonico,
    MaterializacionPorIdentidad,
)

__all__ = [
    "ARGUMENTOS_MAXIMOS",
    "LIMITE_POR_CONSULTA",
    "LIMITE_POR_PREFIJO",
    "IdentificadorInvalidoError",
    "StagedEnginePort",
    "build_staged_engine_port",
]

_ESTADO_MEMORIA_VIGENTE: Final = "current"
_ESTADO_MEMORIA_BORRADA: Final = "deleted"
_ESTADO_DECISION_VIGENTE: Final = "approved"

_SQL_MEMORIAS: Final = """
SELECT m.id, m.subject_key, m.status, m.project_id, m.created_at, r.content
FROM memories AS m
JOIN memory_revisions AS r ON r.memory_id = m.id AND r.is_current = 1
WHERE m.id IN ({marcas})
"""

_SQL_DECISIONES: Final = """
SELECT d.id, d.subject, d.status, d.project_id, d.created_at, r.content
FROM decisions AS d
JOIN decision_revisions AS r ON r.decision_id = d.id AND r.is_current = 1
WHERE d.id IN ({marcas})
"""

#: Cota dura de filas por consulta dirigida.
LIMITE_POR_CONSULTA: Final = 512

#: Cota de una consulta por prefijo de sujeto: más estrecha que la general.
LIMITE_POR_PREFIJO: Final = 64

#: Número máximo de términos o prefijos admitidos en una sola llamada. Sin
#: esta cota, pedir "todos los términos del corpus" sería un barrido
#: escrito de otra forma.
ARGUMENTOS_MAXIMOS: Final = 16

#: Formato cerrado de la identidad canónica: una clase real de ``Clase`` y
#: un entero positivo sin ceros a la izquierda.
_FORMATO_DE_IDENTIDAD: Final = re.compile(
    rf"^({'|'.join(re.escape(clase.value) for clase in Clase)}):([1-9][0-9]*)$"
)


class IdentificadorInvalidoError(ValueError):
    """Identificador canónico malformado, entrada vacía o cota excedida."""


def _acotar(valores: Sequence[str], limite: int = ARGUMENTOS_MAXIMOS) -> list[str]:
    """Argumentos acotados conservando el orden en que llegaron.

    Acotar por alfabeto elegiría por casualidad de qué letra empieza cada
    término, no por prioridad de quien llama; acotar por orden de llegada
    respeta esa prioridad.
    """
    vistos: dict[str, None] = {}
    for valor in valores:
        if valor and valor not in vistos:
            vistos[valor] = None
    return list(vistos)[:limite]


def _sanear(texto: str) -> str:
    """Solo alfanuméricos: ningún operador de FTS5 sobrevive."""
    return "".join(c for c in texto.lower() if c.isalnum())


def _item_de_fila_memoria(fila: RowMapping) -> ItemCanonico:
    bruto = fila["subject_key"]
    sujeto = None if bruto is None or not str(bruto).strip() else str(bruto)
    status = str(fila["status"])
    project_id = fila["project_id"]
    return ItemCanonico(
        id=f"{Clase.MEMORIA.value}:{fila['id']}",
        clase=Clase.MEMORIA,
        project_id=None if project_id is None else str(project_id),
        texto=str(fila["content"] or ""),
        subject_key=sujeto,
        vigente=status == _ESTADO_MEMORIA_VIGENTE,
        disponible=status != _ESTADO_MEMORIA_BORRADA,
        created_at=str(fila["created_at"]),
        clase_de_evidencia=ClaseDeEvidencia.CANONICA,
    )


def _item_de_fila_decision(fila: RowMapping) -> ItemCanonico:
    bruto = fila["subject"]
    sujeto = None if bruto is None or not str(bruto).strip() else str(bruto)
    status = str(fila["status"])
    project_id = fila["project_id"]
    return ItemCanonico(
        id=f"{Clase.DECISION.value}:{fila['id']}",
        clase=Clase.DECISION,
        project_id=None if project_id is None else str(project_id),
        texto=str(fila["content"] or ""),
        subject_key=sujeto,
        vigente=status == _ESTADO_DECISION_VIGENTE,
        # Sirius 0.1 no modela eliminación de decisiones (solo de memorias):
        # una decisión existe siempre que la fila existe.
        disponible=True,
        created_at=str(fila["created_at"]),
        clase_de_evidencia=ClaseDeEvidencia.CANONICA,
    )


class StagedEnginePort:
    """Puerto real sobre una base con el esquema canónico de Sirius 0.1.

    Determinista: toda consulta ordena por identidad estable, de modo que
    dos ejecuciones sobre la misma base devuelven el mismo orden.

    ``ejes_por_identidad`` es el único canal por el que un item real puede
    llevar ejes distintos de ``SIN_EJES``. ``build_staged_engine_port``
    (el camino real del producto) nunca lo puebla (queda ``{}`` por
    defecto); el banco de 47 casos instancia esta clase directamente con
    los ejes que el corpus congelado declara.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None,
        engine: Engine | None,
        *,
        ejes_por_identidad: Mapping[str, EjesDeclarados] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._engine = engine
        self._ejes_por_identidad = ejes_por_identidad or {}

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

    @contextmanager
    def _scope(self) -> Iterator[Session]:
        assert self._session_factory is not None
        with session_scope(self._session_factory) as session:
            yield session

    def _con_ejes(self, item: ItemCanonico) -> ItemCanonico:
        ejes = self._ejes_por_identidad.get(item.id)
        return item if ejes is None else replace(item, ejes=ejes)

    def _por_ids_mixtos(
        self, session: Session, pares: Sequence[tuple[str, int]]
    ) -> list[ItemCanonico]:
        memorias = sorted({i for k, i in pares if k == "memory"})[:LIMITE_POR_CONSULTA]
        decisiones = sorted({i for k, i in pares if k == "decision"})[:LIMITE_POR_CONSULTA]
        items: list[ItemCanonico] = []
        if memorias:
            marcas = ",".join(f":m{i}" for i in range(len(memorias)))
            sql = _SQL_MEMORIAS.format(marcas=marcas)
            parametros = {f"m{i}": valor for i, valor in enumerate(memorias)}
            for fila in session.execute(text(sql), parametros).mappings():
                items.append(self._con_ejes(_item_de_fila_memoria(fila)))
        if decisiones:
            marcas = ",".join(f":d{i}" for i in range(len(decisiones)))
            sql = _SQL_DECISIONES.format(marcas=marcas)
            parametros = {f"d{i}": valor for i, valor in enumerate(decisiones)}
            for fila in session.execute(text(sql), parametros).mappings():
                items.append(self._con_ejes(_item_de_fila_decision(fila)))
        return sorted(items, key=lambda i: i.id)

    # -- Métodos del puerto -------------------------------------------------

    def por_clave_exacta(self, claves: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E1``: coincidencia literal sobre claves normalizadas."""
        utiles = _acotar(claves)
        if not utiles:
            return ()
        with self._scope() as session:
            encontrados: list[tuple[str, int]] = []
            for clave in utiles:
                for fila in session.execute(
                    text(
                        "SELECT id FROM memories WHERE subject_key = :clave ORDER BY id LIMIT :cota"
                    ),
                    {"clave": clave, "cota": LIMITE_POR_CONSULTA},
                ).all():
                    encontrados.append(("memory", int(fila[0])))
                for fila in session.execute(
                    text("SELECT id FROM decisions WHERE subject = :clave ORDER BY id LIMIT :cota"),
                    {"clave": clave, "cota": LIMITE_POR_CONSULTA},
                ).all():
                    encontrados.append(("decision", int(fila[0])))
            return tuple(self._por_ids_mixtos(session, encontrados))

    def por_termino_lexico(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E1``/``E2``/``E3``: el índice léxico medido, con la consulta
        saneada. Cada término se cita como literal de FTS5 y se combinan
        con ``OR``, igual que ``sanitize_fts5_query``."""
        limpios = _acotar([_sanear(t) for t in terminos])
        if not limpios:
            return ()
        consulta = " OR ".join(f'"{t}"' for t in limpios)
        with self._scope() as session:
            filas = session.execute(
                text(
                    "SELECT kind, item_id FROM knowledge_fts WHERE knowledge_fts MATCH :query "
                    "LIMIT :cota"
                ),
                {"query": consulta, "cota": LIMITE_POR_CONSULTA},
            ).all()
            pares = [
                ("memory" if str(fila[0]) == "memory" else "decision", int(fila[1]))
                for fila in filas
            ]
            return tuple(self._por_ids_mixtos(session, pares))

    def por_prefijo_de_sujeto(self, prefijos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E3``: familia de sujetos por prefijo estructural, dirigida."""
        utiles = _acotar(prefijos)
        if not utiles:
            return ()
        with self._scope() as session:
            encontrados: list[tuple[str, int]] = []
            for prefijo in utiles:
                if len(prefijo) < 3:
                    # Un prefijo de una o dos letras seleccionaria media
                    # base: no es una relacion, es un barrido con otro nombre.
                    continue
                patron = f"{prefijo}%"
                for fila in session.execute(
                    text(
                        "SELECT id FROM memories WHERE subject_key LIKE :patron "
                        "ORDER BY id LIMIT :cota"
                    ),
                    {"patron": patron, "cota": LIMITE_POR_PREFIJO},
                ).all():
                    encontrados.append(("memory", int(fila[0])))
                for fila in session.execute(
                    text(
                        "SELECT id FROM decisions WHERE subject LIKE :patron "
                        "ORDER BY id LIMIT :cota"
                    ),
                    {"patron": patron, "cota": LIMITE_POR_PREFIJO},
                ).all():
                    encontrados.append(("decision", int(fila[0])))
            return tuple(self._por_ids_mixtos(session, encontrados))

    def por_identificadores(self, identificadores: Sequence[str]) -> MaterializacionPorIdentidad:
        """Materialización dirigida por identidad canónica exacta."""
        if not identificadores:
            msg = "por_identificadores: entrada vacia; materializar nada no es una consulta"
            raise IdentificadorInvalidoError(msg)
        analizados: set[tuple[str, int]] = set()
        for crudo in identificadores:
            forma = _FORMATO_DE_IDENTIDAD.match(str(crudo))
            if forma is None:
                msg = (
                    f"identificador canonico invalido: {str(crudo)[:64]!r}; el formato "
                    f"cerrado es <clase de Clase>:<entero positivo sin ceros iniciales>"
                )
                raise IdentificadorInvalidoError(msg)
            analizados.add((forma.group(1), int(forma.group(2))))
        if len(analizados) > ARGUMENTOS_MAXIMOS:
            msg = (
                f"por_identificadores: {len(analizados)} identificadores unicos sobre la "
                f"cota de {ARGUMENTOS_MAXIMOS}; la cota rechaza, no trunca"
            )
            raise IdentificadorInvalidoError(msg)
        ordenados = sorted(analizados)
        solicitados = tuple(f"{clase}:{numero}" for clase, numero in ordenados)
        pares = [
            ("memory" if clase == Clase.MEMORIA.value else "decision", numero)
            for clase, numero in ordenados
        ]
        with self._scope() as session:
            encontrados = tuple(self._por_ids_mixtos(session, pares))
        presentes = {item.id for item in encontrados}
        return MaterializacionPorIdentidad(
            pedidos=len(identificadores),
            solicitados=solicitados,
            items=encontrados,
            ausentes=tuple(s for s in solicitados if s not in presentes),
        )

    def historial_y_fuentes(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E4``: sin objetivo real en Sirius 0.1 (ver docstring del
        módulo). Siempre vacío."""
        return ()


def build_staged_engine_port(
    database_path: Path,
    *,
    ejes_por_identidad: Mapping[str, EjesDeclarados] | None = None,
) -> StagedEnginePort:
    """Construye un puerto sobre una base SQLite en la ruta dada."""
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return StagedEnginePort(session_factory, engine, ejes_por_identidad=ejes_por_identidad)
