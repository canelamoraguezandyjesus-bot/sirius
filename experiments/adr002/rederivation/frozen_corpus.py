"""Carga del corpus congelado v0.4 en el esquema real de T0 (TOL-208, pasos 2 y 3).

Este modulo materializa el corpus congelado ``performance_corpus_v0_2.json``
—citado POR BLOB por el acta de congelacion v0.4— en una base de datos con el
esquema canonico de Sirius 0.1 (cadena de Alembic hasta ``61be4bb269bf``, sin
modificarla). No genera datos: **traduce** los del corpus congelado con reglas
deterministas preinscritas aqui, antes de ejecutar nada.

Reglas de traduccion, congeladas antes de la ejecucion:

1. **Proyectos**: los dos del corpus, en su orden; el primero es el activo.
2. **Items ``MEMORIA``** -> ``memories`` + una revision vigente con el texto
   literal. ``status`` es ``current`` si y solo si ``validez == VIGENTE`` y
   ``disponibilidad == DISPONIBLE``; en otro caso ``archived``.
3. **Items ``DECISION``** -> ``decisions`` + una revision vigente con el texto
   literal. ``status`` es ``approved`` si y solo si
   ``confirmacion == CONFIRMADA``; en otro caso ``proposed``.
4. **Mensajes**: los cinco mil, en su orden, en una unica conversacion
   principal; el rol alterna ``user``/``sirius`` como en la linea base.
5. **Entidades, documentos y relaciones** del corpus **no se cargan**: el
   esquema de T0 no tiene tablas para ellos, y esa carencia es exactamente lo
   que T0 es —la Resolucion de la particion §3 declara que T0 no materializa
   relaciones—. Se declara; no se disimula.

Las consultas de control de cada escenario NO se eligen a mano: se **derivan**
del corpus congelado con la regla cerrada de ``derivar_consultas`` y despues
se **verifican funcionalmente** contra el indice FTS5 real construido. Una
discrepancia bloquea la ejecucion: no se mide un escenario que no es el que
dice ser.
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from experiments.adr002.rederivation import rederivation_protocol as rp

from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)

RUTA_CORPUS: Final = "experiments/adr002/benchmark/performance_corpus_v0_2.json"
BLOB_CORPUS: Final = rp.CORPUS_CONGELADO[RUTA_CORPUS]

#: Token del escenario ``cero_resultados``: el mismo de la linea base
#: historica. Su ausencia del corpus congelado se verifica, no se supone.
TOKEN_CERO: Final = "zetaausentenoindexado"

#: Marca de tiempo base para los campos que el corpus no declara.
_BASE_TS: Final = "2026-06-15T00:00:00"

#: Corrida alfanumerica completa, como tokeniza ``unicode61``: el token es la
#: corrida entera, nunca un fragmento de ella. Despues se pliega igual que
#: ``remove_diacritics 2`` —se descomponen y descartan las marcas diacriticas—
#: y solo sobreviven los tokens que quedan en ASCII ``[a-z]+`` puro: para esos,
#: y solo para esos, esta regla y la del indice coinciden exactamente, y la
#: coincidencia ademas se VERIFICA contra el indice real antes de medir.
_CORRIDA: Final = re.compile(r"[^\W_]+", re.UNICODE)
_ASCII: Final = re.compile(r"[a-z]+\Z")


def _plegar(palabra: str) -> str:
    """Pliegue de diacriticos equivalente a ``remove_diacritics 2`` en latin."""
    descompuesta = unicodedata.normalize("NFKD", palabra.lower())
    return "".join(c for c in descompuesta if not unicodedata.combining(c))


class CorpusInvalidoError(RuntimeError):
    """El corpus congelado no es el congelado, o no permite derivar consultas."""


def cargar_corpus_congelado(raiz: Path) -> Mapping[str, Any]:
    """Lee el corpus congelado verificando su blob byte a byte. Falla cerrado."""
    ruta = raiz / RUTA_CORPUS
    crudo = ruta.read_bytes()
    observado = rp.blob_git(crudo)
    if observado != BLOB_CORPUS:
        msg = f"{RUTA_CORPUS} no es el corpus congelado: {observado} != {BLOB_CORPUS}"
        raise CorpusInvalidoError(msg)
    datos = json.loads(crudo)
    if not isinstance(datos, dict):
        msg = f"{RUTA_CORPUS} no contiene un objeto JSON"
        raise CorpusInvalidoError(msg)
    return datos


def tokens_ascii(texto: str) -> list[str]:
    """Tokens ASCII de un texto, con la regla cerrada del modulo.

    Cada corrida alfanumerica es UN token —igual que en ``unicode61``—, se
    pliega el diacritico y solo se conserva si el resultado es ``[a-z]+``
    puro. Una corrida con digitos o con letras fuera del latin plegable se
    descarta ENTERA: nunca se toma un fragmento de un token del indice.
    """
    return [
        plegada
        for plegada in (_plegar(p) for p in _CORRIDA.findall(texto))
        if _ASCII.match(plegada)
    ]


def conteo_por_item(items: Sequence[Mapping[str, Any]]) -> Counter[str]:
    """En cuantos ITEMS aparece cada token ASCII. Presencia, no frecuencia.

    El universo es el de ``knowledge_fts``: el texto vigente de cada item.
    Un token repetido dentro del mismo texto cuenta una sola vez, porque el
    indice devuelve filas y cada item es una fila.
    """
    conteo: Counter[str] = Counter()
    for item in items:
        conteo.update(set(tokens_ascii(str(item.get("text", "")))))
    return conteo


@dataclass(frozen=True, slots=True)
class ConsultasDeControl:
    """Las tres consultas derivadas, con su conteo esperado sobre los items."""

    cero_resultados: str
    un_resultado_exacto: str
    muchos_candidatos: str
    esperados: Mapping[str, int]

    def por_escenario(self) -> dict[str, str]:
        return {
            "cero_resultados": self.cero_resultados,
            "un_resultado_exacto": self.un_resultado_exacto,
            "muchos_candidatos": self.muchos_candidatos,
        }


def derivar_consultas(corpus: Mapping[str, Any]) -> ConsultasDeControl:
    """Deriva las consultas de control del corpus congelado. Determinista.

    - ``cero_resultados``: ``TOKEN_CERO``, cuya ausencia se comprueba aqui y
      se reverifica contra el indice real.
    - ``un_resultado_exacto``: el primer token por orden alfabetico presente
      en exactamente UN item.
    - ``muchos_candidatos``: el token presente en MAS items; a igualdad, el
      primero por orden alfabetico.
    """
    items = corpus.get("items")
    if not isinstance(items, Sequence) or not items:
        msg = "el corpus congelado no declara items"
        raise CorpusInvalidoError(msg)
    conteo = conteo_por_item(items)

    if conteo.get(TOKEN_CERO):
        msg = f"el token de cero resultados aparece en el corpus: {TOKEN_CERO}"
        raise CorpusInvalidoError(msg)

    unicos = sorted(token for token, veces in conteo.items() if veces == 1)
    if not unicos:
        msg = "ningun token ASCII aparece en exactamente un item del corpus"
        raise CorpusInvalidoError(msg)
    unico = unicos[0]

    maximo = max(conteo.values())
    if maximo < 2:  # pragma: no cover - imposible con el corpus congelado
        msg = "ningun token ASCII aparece en dos o mas items del corpus"
        raise CorpusInvalidoError(msg)
    frecuente = sorted(token for token, veces in conteo.items() if veces == maximo)[0]

    return ConsultasDeControl(
        cero_resultados=TOKEN_CERO,
        un_resultado_exacto=unico,
        muchos_candidatos=frecuente,
        esperados={
            "cero_resultados": 0,
            "un_resultado_exacto": 1,
            "muchos_candidatos": maximo,
        },
    )


# --------------------------------------------------------------------------
# Materializacion en el esquema real de T0
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConteosCargados:
    """Lo que la carga materializo, para verificarlo contra el corpus."""

    proyectos: int
    mensajes: int
    memorias: int
    memorias_vigentes: int
    decisiones: int
    filas_fts: int
    no_cargados: Mapping[str, int]


def construir_base_de_referencia(corpus: Mapping[str, Any], destino: Path) -> ConteosCargados:
    """Esquema canonico de Alembic + corpus congelado traducido. Sin medir.

    Todo ocurre FUERA de cualquier cronometro: esta funcion prepara la base
    de referencia que cada sesion copiara despues.
    """
    upgrade_to_head(destino)
    conexion = sqlite3.connect(str(destino))
    conexion.execute("PRAGMA foreign_keys=ON")
    conexion.execute("PRAGMA synchronous=FULL")
    try:
        cursor = conexion.cursor()

        cursor.execute("INSERT INTO conversations (created_at, is_main) VALUES (?, 1)", (_BASE_TS,))
        conversation_id = int(cursor.lastrowid or 0)

        cursor.execute("INSERT INTO identities (created_at) VALUES (?)", (_BASE_TS,))
        identity_id = int(cursor.lastrowid or 0)
        cursor.execute(
            "INSERT INTO identity_versions (identity_id, version, name, description, "
            "personality_instructions, is_current, created_at) VALUES (?, 1, ?, ?, ?, 1, ?)",
            (identity_id, "Sirius", "identidad del control", "sin instrucciones", _BASE_TS),
        )

        proyectos = list(corpus.get("proyectos") or ())
        ids_de_proyecto: dict[str, int] = {}
        for indice, proyecto in enumerate(proyectos):
            cursor.execute(
                "INSERT INTO projects (name, objective, current_state, next_step, is_active, "
                "created_at, updated_at, blockers, status) VALUES (?, ?, ?, ?, ?, ?, ?, '', "
                "'active')",
                (
                    str(proyecto["nombre"]),
                    "objetivo del corpus congelado",
                    "estado declarado por el corpus",
                    "sin siguiente paso",
                    1 if indice == 0 else 0,
                    _BASE_TS,
                    _BASE_TS,
                ),
            )
            ids_de_proyecto[str(proyecto["id"])] = int(cursor.lastrowid or 0)
            cursor.execute(
                "INSERT INTO project_revisions (project_id, version, objective, state_summary, "
                "blockers_json, next_step, source_event_id, created_at) "
                "VALUES (?, 1, ?, ?, '[]', ?, NULL, ?)",
                (
                    ids_de_proyecto[str(proyecto["id"])],
                    "objetivo del corpus congelado",
                    "estado declarado por el corpus",
                    "sin siguiente paso",
                    _BASE_TS,
                ),
            )

        cursor.execute(
            "INSERT INTO events (event_type, actor, message_id, created_at) "
            "VALUES ('memory.created', 'user', NULL, ?)",
            (_BASE_TS,),
        )
        event_id = int(cursor.lastrowid or 0)

        mensajes = list(corpus.get("mensajes") or ())
        cursor.executemany(
            "INSERT INTO messages (conversation_id, sequence, role, content, created_at, "
            "operation_id, identity_version, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    conversation_id,
                    indice,
                    "user" if indice % 2 == 0 else "sirius",
                    str(mensaje["texto"]),
                    _BASE_TS,
                    str(mensaje["id"]),
                    1,
                    "completed",
                )
                for indice, mensaje in enumerate(mensajes)
            ],
        )

        memorias = 0
        memorias_vigentes = 0
        decisiones = 0
        for item in corpus.get("items") or ():
            texto = str(item["text"])
            project_id = ids_de_proyecto.get(str(item.get("project_id")))
            if item.get("kind") == "MEMORIA":
                vigente = (
                    item.get("validez") == "VIGENTE" and item.get("disponibilidad") == "DISPONIBLE"
                )
                cursor.execute(
                    "INSERT INTO memories (status, created_at, updated_at, subject_key, "
                    "project_id) VALUES (?, ?, ?, ?, ?)",
                    (
                        "current" if vigente else "archived",
                        _BASE_TS,
                        _BASE_TS,
                        str(item["id"]),
                        project_id,
                    ),
                )
                memory_id = int(cursor.lastrowid or 0)
                cursor.execute(
                    "INSERT INTO memory_revisions (memory_id, version, content, origin, "
                    "is_current, created_at, source_event_id) VALUES (?, 1, ?, 'corpus', 1, ?, ?)",
                    (memory_id, texto, _BASE_TS, event_id),
                )
                memorias += 1
                memorias_vigentes += int(vigente)
            elif item.get("kind") == "DECISION":
                aprobada = item.get("confirmacion") == "CONFIRMADA"
                cursor.execute(
                    "INSERT INTO decisions (subject, project_id, status, created_at, updated_at, "
                    "supersedes_decision_id) VALUES (?, ?, ?, ?, ?, NULL)",
                    (
                        str(item["id"]),
                        project_id,
                        "approved" if aprobada else "proposed",
                        _BASE_TS,
                        _BASE_TS,
                    ),
                )
                decision_id = int(cursor.lastrowid or 0)
                cursor.execute(
                    "INSERT INTO decision_revisions (decision_id, version, content, "
                    "source_event_id, is_current, created_at) VALUES (?, 1, ?, NULL, 1, ?)",
                    (decision_id, texto, _BASE_TS),
                )
                decisiones += 1
            else:
                msg = f"item con kind desconocido: {item.get('kind')!r}"
                raise CorpusInvalidoError(msg)

        cursor.execute(
            "INSERT INTO llm_usage (year_month, spent_usd, updated_at) VALUES ('2026-06', 0.0, ?)",
            (_BASE_TS,),
        )
        conexion.commit()

        filas_fts = int(conexion.execute("SELECT count(*) FROM knowledge_fts").fetchone()[0])
    finally:
        conexion.close()

    return ConteosCargados(
        proyectos=len(proyectos),
        mensajes=len(mensajes),
        memorias=memorias,
        memorias_vigentes=memorias_vigentes,
        decisiones=decisiones,
        filas_fts=filas_fts,
        no_cargados={
            "entidades": len(corpus.get("entidades") or ()),
            "documentos": len(corpus.get("documentos") or ()),
            "relaciones": len(corpus.get("relaciones") or ()),
        },
    )


def fallos_de_conteos(corpus: Mapping[str, Any], conteos: ConteosCargados) -> list[str]:
    """La carga debe reflejar exactamente los conteos declarados del corpus."""
    declarados = corpus.get("conteos")
    if not isinstance(declarados, Mapping):
        return ["el corpus congelado no declara conteos"]
    fallos: list[str] = []
    esperables = {
        "mensajes": conteos.mensajes,
        "recuerdos": conteos.memorias,
        "decisiones": conteos.decisiones,
        "proyectos": conteos.proyectos,
    }
    for clave, observado in esperables.items():
        if declarados.get(clave) != observado:
            fallos.append(
                f"conteo de {clave}: cargado {observado} != declarado {declarados.get(clave)}"
            )
    if conteos.filas_fts != conteos.memorias + conteos.decisiones:
        fallos.append(
            f"knowledge_fts tiene {conteos.filas_fts} filas y deberian ser "
            f"{conteos.memorias + conteos.decisiones}: una revision vigente por item"
        )
    return fallos


def fallos_de_consultas(base: Path, consultas: ConsultasDeControl) -> list[str]:
    """Verificacion FUNCIONAL de los escenarios contra el indice real.

    No cronometra nada: cuenta resultados. El conteo observado en FTS5 debe
    coincidir exactamente con el derivado del corpus congelado; si no, el
    escenario no es el que dice ser y la ejecucion se bloquea.
    """
    fallos: list[str] = []
    busqueda = build_sqlite_knowledge_search_repository(base)
    try:
        for escenario, consulta in consultas.por_escenario().items():
            observado = len(busqueda.search_knowledge(consulta))
            esperado = consultas.esperados[escenario]
            if observado != esperado:
                fallos.append(
                    f"{escenario}: la consulta {consulta!r} devuelve {observado} "
                    f"resultados y el corpus congelado exige {esperado}"
                )
    finally:
        busqueda.close()
    return fallos
