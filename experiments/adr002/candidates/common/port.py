"""Puerto de recuperacion sobre el canon de Sirius 0.1 y su FTS5 medido.

Es la unica pieza comun que toca SQLite. El motor no abre conexiones: pide al
puerto. Esa separacion es lo que ``B04-RF-31`` exige —«ninguna obligacion
exige embeddings, RAG, FTS, vectores, grafos o un modelo concreto»—: sustituir
el sustrato no obliga a tocar el motor ni ningun candidato.

**Ninguna ruta ofrece un barrido.** Toda consulta lleva un predicado que la
dirige —clave exacta, termino del indice lexico o prefijo de sujeto— y una
cota de filas. No existe metodo que devuelva el canon entero ni que enumere un
proyecto: el ambito es una **puerta de seguridad**, no un generador de
candidatos, y confundirlos fue el defecto 2 del paquete de correccion 01.

**Toda consulta queda registrada.** Cada llamada anota la operacion, el SQL
ejecutado, sus parametros, la cota aplicada y las filas devueltas, de modo que
la ausencia de barrido se **comprueba** sobre lo que realmente se ejecuto en
vez de deducirse del codigo.

El puerto **no modifica Sirius 0.1**: lee su esquema canonico tal como lo deja
la cadena de Alembic, sin DDL adicional, sin indices nuevos y sin escrituras.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from experiments.adr002.candidates.common.contracts import (
    Clase,
    ClaseDeEvidencia,
    ItemCanonico,
    MaterializacionPorIdentidad,
)

#: Vigencia y disponibilidad tal como las representa el esquema de Sirius 0.1.
_ESTADO_VIGENTE: Final = "current"

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

_SQL_FTS: Final = "SELECT kind, item_id FROM knowledge_fts WHERE knowledge_fts MATCH ? LIMIT ?"

#: Cota dura de filas por consulta dirigida.
LIMITE_POR_CONSULTA: Final = 512

#: Cota de una consulta por prefijo de sujeto. Mas estrecha que la general: un
#: prefijo agrupa una familia de sujetos, no un espacio entero.
LIMITE_POR_PREFIJO: Final = 64

#: Numero maximo de terminos o prefijos admitidos en una sola llamada. Sin
#: esta cota, pedir "todos los terminos del corpus" seria un barrido escrito
#: de otra forma.
ARGUMENTOS_MAXIMOS: Final = 16

#: Marca de las anotaciones que registran que **no se pregunto**. Llevan sufijo
#: propio para que ninguna auditoria de barrido las confunda con una consulta.
_SUFIJO_SIN_CONSULTA: Final = ":sin_consulta"

#: Formato cerrado de la identidad canonica: una clase REAL de ``Clase`` y un
#: entero positivo sin ceros a la izquierda. Nada mas: los ceros iniciales
#: serian codificaciones duplicadas de la misma identidad, y una cadena
#: paralela divergente seria una segunda nocion de identidad.
_FORMATO_DE_IDENTIDAD: Final = re.compile(
    rf"^({'|'.join(re.escape(clase.value) for clase in Clase)}):([1-9][0-9]*)$"
)


@dataclass(frozen=True, slots=True)
class ConsultaRegistrada:
    """Una consulta realmente ejecutada, con su cota y su resultado."""

    operacion: str
    sql: str
    parametros: tuple[str, ...]
    cota: int
    filas: int

    @property
    def ejecutada(self) -> bool:
        """Si llego a tocar SQLite. Lo que no se ejecuto no puede ser barrido."""
        return not self.operacion.endswith(_SUFIJO_SIN_CONSULTA)

    @property
    def dirigida(self) -> bool:
        """Una consulta sin predicado no esta dirigida: es un barrido."""
        if not self.ejecutada:
            return True
        sql = " ".join(self.sql.split()).upper()
        return " WHERE " in sql or " MATCH " in sql


@dataclass(slots=True)
class RegistroDeConsultas:
    """Lo que el puerto ejecuto, para auditar la ausencia de barrido."""

    consultas: list[ConsultaRegistrada] = field(default_factory=list)

    def anotar(self, consulta: ConsultaRegistrada) -> None:
        self.consultas.append(consulta)

    @property
    def filas_totales(self) -> int:
        return sum(c.filas for c in self.consultas)

    def por_operacion(self) -> dict[str, int]:
        conteo: dict[str, int] = {}
        for consulta in self.consultas:
            conteo[consulta.operacion] = conteo.get(consulta.operacion, 0) + consulta.filas
        return conteo


class ConsultaNoDirigidaError(RuntimeError):
    """Se intento una consulta sin predicado o con demasiados argumentos."""


class IdentificadorInvalidoError(ValueError):
    """Identificador canonico malformado, entrada vacia o cota excedida.

    Se lanza ANTES de ejecutar SQL alguno. Un identificador sintacticamente
    valido pero inexistente NO es este error: aparece como ausente en el
    resultado, porque no existir no es estar mal escrito.
    """


class PuertoSqlite:
    """Puerto real sobre una base con el esquema canonico de Sirius 0.1.

    Determinista: toda consulta ordena por identidad estable, de modo que dos
    ejecuciones sobre la misma base devuelven el mismo orden.
    """

    def __init__(self, database_path: Path) -> None:
        self._conexion = sqlite3.connect(str(database_path))
        self._conexion.execute("PRAGMA foreign_keys=ON")
        self._conexion.row_factory = sqlite3.Row
        self.registro = RegistroDeConsultas()

    def close(self) -> None:
        self._conexion.close()

    def __enter__(self) -> PuertoSqlite:
        return self

    def __exit__(self, *_excepcion: object) -> None:
        self.close()

    # -- Ejecucion instrumentada ------------------------------------------

    def _ejecutar(
        self,
        operacion: str,
        sql: str,
        parametros: Sequence[object],
        *,
        cota: int,
    ) -> list[sqlite3.Row]:
        """Ejecuta y **anota**. Rechaza cualquier consulta sin predicado."""
        normalizado = " ".join(sql.split()).upper()
        if " WHERE " not in normalizado and " MATCH " not in normalizado:
            msg = f"{operacion}: consulta sin predicado; el puerto no ofrece barridos"
            raise ConsultaNoDirigidaError(msg)
        filas = self._conexion.execute(sql, tuple(parametros)).fetchall()
        self.registro.anotar(
            ConsultaRegistrada(
                operacion=operacion,
                sql=" ".join(sql.split()),
                parametros=tuple(str(p) for p in parametros),
                cota=cota,
                filas=len(filas),
            )
        )
        return filas

    def _anotar_sin_consulta(self, operacion: str, motivo: str) -> None:
        """Registra que **no se pregunto**, y por que.

        «No pregunte» y «pregunte y no hay» daban los dos una tupla vacia y
        ninguna huella en el registro, de modo que una ruta que descartase
        todos sus argumentos era indistinguible de una consulta sin resultados.
        """
        self.registro.anotar(
            ConsultaRegistrada(
                operacion=f"{operacion}{_SUFIJO_SIN_CONSULTA}",
                sql=f"-- {motivo}",
                parametros=(),
                cota=0,
                filas=0,
            )
        )

    @staticmethod
    def _acotar(valores: Sequence[str], limite: int = ARGUMENTOS_MAXIMOS) -> list[str]:
        """Argumentos ordenados y acotados: pedir "todo" no es una consulta."""
        return sorted({v for v in valores if v})[:limite]

    # -- Lectura de items -------------------------------------------------

    @staticmethod
    def _item_de_fila(clase: Clase, fila: sqlite3.Row) -> ItemCanonico:
        # Ausencia y cadena vacia dejan de colapsar: el canon admite sujeto
        # nulo, y confundirlo con un sujeto en blanco hacia que dos ausencias
        # distintas se agrupasen entre si.
        bruto = fila[1]
        sujeto = None if bruto is None or not str(bruto).strip() else str(bruto)
        return ItemCanonico(
            id=f"{clase.value}:{fila[0]}",
            clase=clase,
            project_id=(None if fila["project_id"] is None else str(fila["project_id"])),
            texto=str(fila["content"] or ""),
            subject_key=sujeto,
            vigente=(str(fila["status"]) == _ESTADO_VIGENTE)
            if clase is Clase.MEMORIA
            else (str(fila["status"]) == "approved"),
            disponible=str(fila["status"]) not in ("deleted", "purged"),
            created_at=str(fila["created_at"]),
            clase_de_evidencia=ClaseDeEvidencia.CANONICA,
        )

    def _items(self, clase: Clase, ids: Sequence[int]) -> list[ItemCanonico]:
        if not ids:
            return []
        acotados = sorted(set(ids))[:LIMITE_POR_CONSULTA]
        marcas = ",".join("?" * len(acotados))
        sql = (_SQL_MEMORIAS if clase is Clase.MEMORIA else _SQL_DECISIONES).format(marcas=marcas)
        filas = self._ejecutar(
            f"materializar:{clase.value}", sql, acotados, cota=LIMITE_POR_CONSULTA
        )
        items = [self._item_de_fila(clase, fila) for fila in filas]
        return sorted(items, key=lambda i: i.id)

    def _por_ids_mixtos(self, pares: Sequence[tuple[str, int]]) -> tuple[ItemCanonico, ...]:
        memorias = [i for k, i in pares if k == "memory"]
        decisiones = [i for k, i in pares if k == "decision"]
        items = [*self._items(Clase.MEMORIA, memorias), *self._items(Clase.DECISION, decisiones)]
        return tuple(sorted(items, key=lambda i: i.id))

    # -- Metodos del puerto -----------------------------------------------

    def por_clave_exacta(self, claves: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E1``: coincidencia literal sobre claves normalizadas."""
        encontrados: list[tuple[str, int]] = []
        utiles = self._acotar(claves)
        if not utiles:
            self._anotar_sin_consulta("clave_exacta", "ninguna clave util: todas vacias")
            return ()
        for clave in utiles:
            for fila in self._ejecutar(
                "clave_exacta:memoria",
                "SELECT id FROM memories WHERE subject_key = ? ORDER BY id LIMIT ?",
                (clave, LIMITE_POR_CONSULTA),
                cota=LIMITE_POR_CONSULTA,
            ):
                encontrados.append(("memory", int(fila[0])))
            for fila in self._ejecutar(
                "clave_exacta:decision",
                "SELECT id FROM decisions WHERE subject = ? ORDER BY id LIMIT ?",
                (clave, LIMITE_POR_CONSULTA),
                cota=LIMITE_POR_CONSULTA,
            ):
                encontrados.append(("decision", int(fila[0])))
        return self._por_ids_mixtos(encontrados)

    def por_termino_lexico(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E1``/``E2``/``E3``: el indice lexico medido, con la consulta saneada.

        Cada termino se cita como literal de FTS5 y se combinan con ``OR``:
        ningun texto de consulta puede alcanzar el parser de FTS5 como
        operador, que es la misma garantia que ya ofrece Sirius 0.1.
        """
        limpios = self._acotar([self._sanear(t) for t in terminos])
        if not limpios:
            self._anotar_sin_consulta("termino_lexico", "ningun termino util tras sanear")
            return ()
        consulta = " OR ".join(f'"{t}"' for t in limpios)
        pares = [
            (str(fila["kind"]), int(fila["item_id"]))
            for fila in self._ejecutar(
                "termino_lexico",
                _SQL_FTS,
                (consulta, LIMITE_POR_CONSULTA),
                cota=LIMITE_POR_CONSULTA,
            )
        ]
        return self._por_ids_mixtos(pares)

    def por_identificadores(self, identificadores: Sequence[str]) -> MaterializacionPorIdentidad:
        """Materializacion dirigida por identidad canonica exacta.

        La unica pregunta que responde es «¿existen exactamente ESTOS?». No
        mira claves de sujeto, ni proyectos, ni el indice lexico: cada clase
        se consulta con un unico ``WHERE id IN (...)`` sobre su clave
        primaria, de modo que el trabajo depende de cuantos identificadores
        se piden y nunca del tamano del canon. Lo ausente se declara en el
        resultado; callarlo fue el defecto del paquete de correccion 02.
        """
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

        items: list[ItemCanonico] = []
        for clase in (Clase.MEMORIA, Clase.DECISION):
            numeros = [numero for nombre, numero in ordenados if nombre == clase.value]
            if not numeros:
                continue
            marcas = ",".join("?" * len(numeros))
            sql = (_SQL_MEMORIAS if clase is Clase.MEMORIA else _SQL_DECISIONES).format(
                marcas=marcas
            )
            filas = self._ejecutar(
                f"por_identidad:{clase.value}", sql, numeros, cota=ARGUMENTOS_MAXIMOS
            )
            items.extend(self._item_de_fila(clase, fila) for fila in filas)

        def _orden_canonico(item: ItemCanonico) -> tuple[str, int]:
            nombre, _, numero = item.id.partition(":")
            return (nombre, int(numero))

        encontrados = tuple(sorted(items, key=_orden_canonico))
        presentes = {item.id for item in encontrados}
        return MaterializacionPorIdentidad(
            pedidos=len(identificadores),
            solicitados=solicitados,
            items=encontrados,
            ausentes=tuple(s for s in solicitados if s not in presentes),
        )

    def por_prefijo_de_sujeto(self, prefijos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E3``: familia de sujetos por prefijo estructural, dirigida.

        El canon de Sirius 0.1 **no materializa entidades como tabla**: la
        relacion que si materializa es la clave de sujeto, y este metodo la
        consulta por prefijo concreto con su propia cota. No recibe ni admite
        identificadores de proyecto: el ambito filtra en la puerta ``G4``, no
        aqui.
        """
        encontrados: list[tuple[str, int]] = []
        utiles = self._acotar(prefijos)
        if not utiles:
            self._anotar_sin_consulta("prefijo_de_sujeto", "ningun prefijo util: todos vacios")
            return ()
        for prefijo in utiles:
            if len(prefijo) < 3:
                self._anotar_sin_consulta(
                    "prefijo_de_sujeto", f"prefijo de {len(prefijo)} caracteres: seria un barrido"
                )
                # Un prefijo de una o dos letras seleccionaria media base: no
                # es una relacion, es un barrido con otro nombre.
                continue
            patron = f"{prefijo}%"
            for fila in self._ejecutar(
                "prefijo_de_sujeto:memoria",
                "SELECT id FROM memories WHERE subject_key LIKE ? ORDER BY id LIMIT ?",
                (patron, LIMITE_POR_PREFIJO),
                cota=LIMITE_POR_PREFIJO,
            ):
                encontrados.append(("memory", int(fila[0])))
            for fila in self._ejecutar(
                "prefijo_de_sujeto:decision",
                "SELECT id FROM decisions WHERE subject LIKE ? ORDER BY id LIMIT ?",
                (patron, LIMITE_POR_PREFIJO),
                cota=LIMITE_POR_PREFIJO,
            ):
                encontrados.append(("decision", int(fila[0])))
        return self._por_ids_mixtos(encontrados)

    def historial_y_fuentes(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """``E4``: historial bruto como **evidencia atribuida no canonica**.

        Los mensajes no son conocimiento confirmado: se devuelven marcados
        como ``ATRIBUIDA`` para que ``B04-RF-13`` se cumpla por construccion y
        ningun candidato pueda presentarlos como verdad canonica.
        """
        limpios = self._acotar([self._sanear(t) for t in terminos])
        if not limpios:
            self._anotar_sin_consulta("historial", "ningun termino util tras sanear")
            return ()
        consulta = " OR ".join(f'"{t}"' for t in limpios)
        filas = self._ejecutar(
            "historial",
            "SELECT m.id, m.content, m.created_at FROM message_fts "
            "JOIN messages AS m ON m.id = message_fts.rowid "
            "WHERE message_fts MATCH ? ORDER BY m.id LIMIT ?",
            (consulta, LIMITE_POR_CONSULTA),
            cota=LIMITE_POR_CONSULTA,
        )
        return tuple(
            ItemCanonico(
                id=f"MENSAJE:{fila[0]}",
                clase=Clase.MEMORIA,
                project_id=None,
                texto=str(fila[1] or ""),
                # **Sin sujeto fabricado.** Un mensaje no tiene clave de sujeto
                # en el canon; inventarle una —``mensaje-<n>``— creaba un sujeto
                # sintetico unico por mensaje que ninguna consulta por clave ni
                # por prefijo podia alcanzar y que ademas mentia al decir que el
                # canon lo declaraba.
                subject_key=None,
                vigente=False,
                disponible=True,
                created_at=str(fila[2]),
                clase_de_evidencia=ClaseDeEvidencia.ATRIBUIDA,
            )
            for fila in filas
        )

    @staticmethod
    def _sanear(texto: str) -> str:
        """Solo alfanumericos: ningun operador de FTS5 sobrevive."""
        return "".join(c for c in texto.lower() if c.isalnum())


def fallos_de_barrido(registro: RegistroDeConsultas, *, universo: int) -> list[str]:
    """Comprueba sobre lo EJECUTADO que ninguna consulta fue un barrido.

    ``universo`` es el numero de items del canon en la base de prueba. Una
    consulta que devuelve el universo entero no esta dirigida por mucho que
    lleve un predicado: el predicado no selecciona nada.
    """
    fallos: list[str] = []
    for consulta in registro.consultas:
        if not consulta.ejecutada:
            continue
        if not consulta.dirigida:
            fallos.append(f"{consulta.operacion}: consulta sin predicado")
        if consulta.filas > consulta.cota:
            fallos.append(
                f"{consulta.operacion}: {consulta.filas} filas sobre cota {consulta.cota}"
            )
        if (
            universo
            and consulta.operacion.startswith("prefijo_de_sujeto")
            and consulta.filas >= universo
        ):
            fallos.append(
                f"{consulta.operacion}: devolvio el universo entero ({consulta.filas}); "
                f"un prefijo que selecciona todo no es una relacion"
            )
    return fallos


__all__ = [
    "ARGUMENTOS_MAXIMOS",
    "LIMITE_POR_CONSULTA",
    "LIMITE_POR_PREFIJO",
    "ConsultaNoDirigidaError",
    "ConsultaRegistrada",
    "IdentificadorInvalidoError",
    "PuertoSqlite",
    "RegistroDeConsultas",
    "fallos_de_barrido",
]
