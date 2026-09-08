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

Sobre los ejes P2 (ADR-165, palanca 2 de ADR-148): **sin migración**, este
puerto deriva de las filas que ya consulta los tres únicos que salen de
datos que el esquema canónico guarda hoy —``valid_from``, ``valid_to`` y
``autoridad``, ver ``_ejes_de_memoria``/``_ejes_de_decision``—, y deja
``None`` todo lo demás (``ambito``, ``sensibilidad``, ``confirmacion``,
``validez``, ``disponibilidad``, ``no_usar_como_memoria``,
``no_consolidable``, ``procedencia``, ``miembros_de_ambito``, y
``property_key``, que ni siquiera vive aquí sino en ``PlanoComun``). Un eje
que el sustrato no sabe se queda sin derivar: las puertas que lo necesitan
degradan (ver ``staged_engine_gates``), que es un comportamiento declarado,
mientras que un valor inventado sería una afirmación sin dato detrás.

Hasta ADR-165, ``build_staged_engine_port`` no poblaba ``ejes_por_identidad``
y todo item real llegaba con ``ejes=SIN_EJES``. ``ejes_por_identidad`` sigue
existiendo y sigue **mandando** sobre lo derivado: es el canal con el que el
arnés de examen del banco de 47 casos inyecta los ejes del corpus congelado
(``tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py``).
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
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
    "AUTORIDAD_POR_ORIGEN",
    "FORMATO_DEL_REGISTRO",
    "FORMATO_DE_LA_VIGENCIA",
    "LIMITE_POR_CONSULTA",
    "LIMITE_POR_PREFIJO",
    "IdentificadorInvalidoError",
    "StagedEnginePort",
    "build_staged_engine_port",
]

_ESTADO_MEMORIA_VIGENTE: Final = "current"
_ESTADO_MEMORIA_BORRADA: Final = "deleted"
_ESTADO_DECISION_VIGENTE: Final = "approved"
_ESTADO_DECISION_SUSTITUIDA: Final = "superseded"

#: ``revision_created_at``/``revision_origin`` son los dos datos de los que
#: ADR-165 deriva la vigencia y la autoridad de un recuerdo. No añaden una
#: consulta: la revisión vigente ya se unía para leer ``content``.
_SQL_MEMORIAS: Final = """
SELECT m.id, m.subject_key, m.status, m.project_id, m.created_at, r.content,
       r.created_at AS revision_created_at, r.origin AS revision_origin
FROM memories AS m
JOIN memory_revisions AS r ON r.memory_id = m.id AND r.is_current = 1
WHERE m.id IN ({marcas})
"""

#: ``updated_at`` es el sello de la última transición de estado de la decisión
#: —lo escriben ``create_proposal``, ``approve_decision``,
#: ``supersede_decision`` y ``archive_decision``, y nadie más—, del que ADR-165
#: deriva la aprobación y la sustitución.
_SQL_DECISIONES: Final = """
SELECT d.id, d.subject, d.status, d.project_id, d.created_at, d.updated_at, r.content
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


#: Forma en la que ``G8`` compara el instante de registro. ADR-164 emite el
#: corte de registro exactamente así (``AAAA-MM-DD hh:mm:ss.ffffff``), y
#: ``created_at`` se canoniza a ella para que la comparación —que es de
#: CADENAS— no dependa de con cuántos decimales se escribiera la fila.
FORMATO_DEL_REGISTRO: Final = "%Y-%m-%d %H:%M:%S.%f"

#: Forma en la que ``G8`` compara la ventana de vigencia con el tiempo
#: objetivo. Ver ``_vigencia`` para por qué los seis dígitos son fijos.
FORMATO_DE_LA_VIGENCIA: Final = "%Y-%m-%dT%H:%M:%S.%f"

#: Autoridad por origen de la revisión vigente de un recuerdo (ADR-165). La
#: tabla es CERRADA a los tres orígenes que el producto escribe hoy
#: (``sirius.application.save_manual_memory.MANUAL_MEMORY_ORIGIN``,
#: ``correct_memory.MEMORY_CORRECTION_ORIGIN`` y
#: ``confirm_memory_suggestion.CONFIRMED_MEMORY_SUGGESTION_ORIGIN``; el
#: guardián ``test_la_tabla_de_autoridad_cubre_los_tres_origenes_del_producto``
#: la ata a esas constantes en vez de dejarlas coincidir por casualidad).
#: Un origen que no esté aquí deja la autoridad SIN DERIVAR.
#:
#: Una sugerencia confirmada es ``INFORMAL`` y no un acto explícito porque la
#: autoridad es la del ORIGEN DEL CONTENIDO —lo que Sirius recogió de la
#: conversación (SIRIUS-ARQ-0.2 §3.3)—, y que el usuario la confirmara es el
#: eje ``confirmacion``, que este puerto no deriva. Es como el corpus congelado
#: adjudica ``MEM-017``: ``CONFIRMADA`` e ``INFORMAL`` a la vez.
AUTORIDAD_POR_ORIGEN: Final[Mapping[str, str]] = {
    "Guardado manual del usuario": "ACTO_EXPLICITO_USUARIO",
    "Corrección manual del usuario": "ACTO_EXPLICITO_USUARIO",
    "Sugerencia confirmada por el usuario": "INFORMAL",
}


def _instante(bruto: object) -> datetime | None:
    """El instante que la fila trae, o ``None`` si no hay ninguno legible.

    Nunca inventa: un valor ausente, en blanco o que no sea ISO-8601 sale
    como ``None``, y quien llame decidirá que ese eje queda sin derivar.
    """
    if bruto is None:
        return None
    if isinstance(bruto, datetime):
        momento = bruto
    else:
        crudo = str(bruto).strip()
        if not crudo:
            return None
        try:
            momento = datetime.fromisoformat(crudo)
        except ValueError:
            return None
    if momento.tzinfo is not None:
        momento = momento.astimezone(UTC).replace(tzinfo=None)
    return momento


def _registro(bruto: object) -> str:
    """El instante de registro en la forma con la que ``G8`` lo compara.

    Si el valor no se puede interpretar sale VERBATIM: degradar a lo que este
    puerto entregaba antes de ADR-165 es honesto; escribir un instante que la
    fila no dice, no.
    """
    momento = _instante(bruto)
    if momento is None:
        return "" if bruto is None else str(bruto)
    return momento.strftime(FORMATO_DEL_REGISTRO)


def _vigencia(bruto: object) -> str | None:
    """Un extremo de la ventana de vigencia, o ``None`` si el dato falta.

    Sale en ISO-8601 UTC con sufijo ``Z`` y **siempre los seis dígitos de
    microsegundo**, porque ``G8`` compara ``valid_from > objetivo`` y
    ``valid_to <= objetivo`` como CADENAS y el tiempo objetivo llega hoy en
    dos anchos distintos: el del corpus y el de una fecha interpretada
    (``2026-06-15T00:00:00Z``, sin fracción) y el del respaldo «ahora» de
    ``InterpreteDePeticion``, que es ``datetime.isoformat()`` y sí la lleva
    (``2026-09-08T12:00:57.004344Z``, ADR-164).

    El ancho fijo es la única escritura que ordena bien contra los dos:
    contra un objetivo CON fracción la comparación es dígito a dígito y sale
    exacta; contra uno SIN fracción, el ``.`` (``0x2E``) ordena antes que la
    ``Z`` (``0x5A``), así que un item del mismo segundo se lee como
    inmediatamente anterior — que admite en ``valid_from`` y da por terminada
    en ``valid_to``, el lado seguro en los dos.

    Truncar al segundo, en cambio, **rompe**: ``"…:00Z"`` ordena DESPUÉS de
    ``"…:00.123456Z"``, de modo que un item registrado ANTES de la consulta
    saldría «aún no vigente» cada vez que el respaldo cayera en su mismo
    segundo.
    """
    momento = _instante(bruto)
    if momento is None:
        return None
    return f"{momento.strftime(FORMATO_DE_LA_VIGENCIA)}Z"


def _autoridad_de_origen(bruto: object) -> str | None:
    """La autoridad que declara el origen de la revisión, o ``None``.

    ``FUENTE_EXTERNA`` no aparece porque ningún camino del producto escribe
    hoy un origen de fuente externa: es el hueco H3 de ADR-148, que espera una
    decisión de producto del propietario.
    """
    if bruto is None:
        return None
    return AUTORIDAD_POR_ORIGEN.get(str(bruto))


def _ejes_de_memoria(fila: RowMapping) -> EjesDeclarados:
    """Los ejes que las filas de un recuerdo declaran (ADR-165).

    ``valid_from`` es el instante de la revisión VIGENTE: cuándo entró en
    vigor el contenido que este puerto entrega. ``valid_to`` se queda sin
    derivar siempre — Sirius 0.1 no sustituye recuerdos: una corrección crea
    una revisión nueva y el puerto entrega la vigente, que no tiene fin.
    """
    return EjesDeclarados(
        valid_from=_vigencia(fila["revision_created_at"]),
        autoridad=_autoridad_de_origen(fila["revision_origin"]),
    )


def _ejes_de_decision(fila: RowMapping) -> EjesDeclarados:
    """Los ejes que las filas de una decisión declaran (ADR-165).

    ``updated_at`` es el sello de la última transición de estado, así que
    significa una cosa distinta según el estado en el que la decisión quedó:

    - ``approved``: es la APROBACIÓN → ``valid_from``.
    - ``superseded``: es la SUSTITUCIÓN → ``valid_to``. Se lee del sello de la
      propia decisión sustituida y no del de la que la sustituye porque en una
      cadena ``D1 → D2 → D3`` el sello de ``D2`` ya se habría movido a la
      segunda sustitución y le atribuiría a ``D1`` un fin que no es el suyo.
      El estado es terminal (``ensure_can_archive`` solo admite ``APPROVED``,
      y ``DecisionStatus`` no tiene camino de vuelta), así que no se mueve más.
      El instante de su aprobación ya no se persiste en ninguna parte, de modo
      que su ``valid_from`` queda sin derivar; ``created_at`` no lo sustituye,
      porque proponer no es aprobar.
    - ``proposed``: nunca se aprobó, y ``archived``: el sello es el del
      archivado. En los dos, la ventana entera queda sin derivar.

    Una decisión SIN SUSTITUCIÓN nunca recibe ``valid_to``: no hay dato del
    que sacarlo y no se inventa.
    """
    status = str(fila["status"])
    sello = fila["updated_at"]
    return EjesDeclarados(
        valid_from=_vigencia(sello) if status == _ESTADO_DECISION_VIGENTE else None,
        valid_to=_vigencia(sello) if status == _ESTADO_DECISION_SUSTITUIDA else None,
    )


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
        created_at=_registro(fila["created_at"]),
        clase_de_evidencia=ClaseDeEvidencia.CANONICA,
        ejes=_ejes_de_memoria(fila),
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
        created_at=_registro(fila["created_at"]),
        clase_de_evidencia=ClaseDeEvidencia.CANONICA,
        ejes=_ejes_de_decision(fila),
    )


class StagedEnginePort:
    """Puerto real sobre una base con el esquema canónico de Sirius 0.1.

    Determinista: toda consulta ordena por identidad estable, de modo que
    dos ejecuciones sobre la misma base devuelven el mismo orden.

    Desde ADR-165 los ejes que el esquema ya sabe —``valid_from``,
    ``valid_to`` y ``autoridad``— se derivan de las propias filas (ver el
    docstring del módulo). ``ejes_por_identidad`` sigue siendo el canal por el
    que un llamante DECLARA ejes, y lo declarado manda sobre lo derivado: el
    banco de 47 casos instancia esta clase directamente con los ejes que el
    corpus congelado declara, y ``build_staged_engine_port`` (el camino real
    del producto) sigue sin poblarlo.
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
        """Lo DECLARADO por quien llama manda sobre lo derivado de la fila.

        Sin esta precedencia, ADR-165 habría cambiado en silencio lo que el
        arnés de examen del banco mide: inyectar los ejes del corpus dejaría
        de ser inyectarlos.
        """
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
        """``E1``: coincidencia literal sobre claves normalizadas, en una
        sola sentencia SQL por tabla (``UNION ALL`` de una subconsulta por
        clave, cada una con su propio ``ORDER BY id LIMIT``) en vez de dos
        consultas por clave (ADR-122/M13): el número de sentencias deja de
        crecer con el número de claves de una llamada, y cada clave conserva
        su propia cota de filas (``LIMITE_POR_CONSULTA``) sin que el volumen
        de coincidencias de una clave pueda desplazar las de otra dentro de
        la misma llamada (``subject_key`` no es único: CLAUDE-M13-001/
        CODEX-001)."""
        utiles = _acotar(claves)
        if not utiles:
            return ()
        with self._scope() as session:
            encontrados: list[tuple[str, int]] = []
            parametros: dict[str, str | int] = {f"c{i}": valor for i, valor in enumerate(utiles)}
            parametros["cota"] = LIMITE_POR_CONSULTA
            consulta_memorias = " UNION ALL ".join(
                f"SELECT id FROM (SELECT id FROM memories WHERE subject_key = :c{i} "
                "ORDER BY id LIMIT :cota)"
                for i in range(len(utiles))
            )
            for fila in session.execute(text(consulta_memorias), parametros).all():
                encontrados.append(("memory", int(fila[0])))
            consulta_decisiones = " UNION ALL ".join(
                f"SELECT id FROM (SELECT id FROM decisions WHERE subject = :c{i} "
                "ORDER BY id LIMIT :cota)"
                for i in range(len(utiles))
            )
            for fila in session.execute(text(consulta_decisiones), parametros).all():
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
        """``E3``: familia de sujetos por prefijo estructural, dirigida, en
        una sola sentencia SQL por tabla (``UNION ALL`` de una subconsulta
        por prefijo, cada una con su propio ``ORDER BY id LIMIT``) en vez de
        dos consultas por prefijo (ADR-122/M13): el número de sentencias deja
        de crecer con el número de prefijos de una llamada, y cada prefijo
        conserva su propia cota de filas (``LIMITE_POR_PREFIJO``) sin que el
        volumen de coincidencias de un prefijo pueda desplazar las de otro
        dentro de la misma llamada (``subject_key``/``subject`` no son
        únicos: CLAUDE-M13-001/CODEX-001)."""
        # Un prefijo de una o dos letras seleccionaria media base: no es una
        # relacion, es un barrido con otro nombre.
        utiles = [prefijo for prefijo in _acotar(prefijos) if len(prefijo) >= 3]
        if not utiles:
            return ()
        with self._scope() as session:
            encontrados: list[tuple[str, int]] = []
            parametros: dict[str, str | int] = {
                f"p{i}": f"{prefijo}%" for i, prefijo in enumerate(utiles)
            }
            parametros["cota"] = LIMITE_POR_PREFIJO
            consulta_memorias = " UNION ALL ".join(
                f"SELECT id FROM (SELECT id FROM memories WHERE subject_key LIKE :p{i} "
                "ORDER BY id LIMIT :cota)"
                for i in range(len(utiles))
            )
            for fila in session.execute(text(consulta_memorias), parametros).all():
                encontrados.append(("memory", int(fila[0])))
            consulta_decisiones = " UNION ALL ".join(
                f"SELECT id FROM (SELECT id FROM decisions WHERE subject LIKE :p{i} "
                "ORDER BY id LIMIT :cota)"
                for i in range(len(utiles))
            )
            for fila in session.execute(text(consulta_decisiones), parametros).all():
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
    """Construye un puerto sobre una base SQLite en la ruta dada.

    El camino real del producto: ``ejes_por_identidad`` se queda vacío y cada
    item llega con los ejes que ADR-165 deriva de sus propias filas.
    """
    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    return StagedEnginePort(session_factory, engine, ejes_por_identidad=ejes_por_identidad)
