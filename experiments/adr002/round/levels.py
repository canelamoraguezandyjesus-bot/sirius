"""Niveles 2 y 3 del banco: casos arquitectónicos y ablaciones. **No mide tiempo.**

La ronda primaria ejecutaba el nivel 1 y nada más. El nivel 4 se recuperó en
`discriminant.py`; aquí se recuperan los otros dos, y con ellos lo que faltaba
para que la comparación esté completa.

**Cinco casos arquitectónicos** (`ARQ-CA-01..05`), que `B04` no cubre porque son
propios de la elección técnica: el ciclo físico del índice derivado, su purga sin
fragmento recuperable, la estabilidad de orden, y las dos declaraciones de coste
que la ficha tiene que traer congeladas.

**Siete ablaciones** (`AB-0..AB-6`), que el propio banco declara «instrumentos de
medida; **nunca producen veredicto de conformidad**». Aquí se tratan como tales:
aíslan la aportación de cada señal apagándola, y ninguna adjudica una puerta.

POR QUÉ `ARQ-CA-01` NO ES LA PUERTA 5 QUE YA SE MIDIÓ
=====================================================

``execute_round.borrado_y_regeneracion`` adjudica la puerta 5 con **un** ciclo y
**solo** sobre el sidecar de `B` y `D`; a `A`, `C` y `T0` los da por cumplidos
«por no tener índice propio».

`ARQ-CA-01` es más exigente en las dos direcciones: pide **30/30** y habla de
«todo índice derivado», y el `FTS5` **es** un índice derivado —lo dice
``derived.py``: tablas virtuales, tablas sombra y triggers— que los cinco
participantes usan. De modo que aquí el ciclo se ejecuta también sobre el `FTS5`,
que es lo que la ronda nunca hizo treinta veces.

LO QUE SE COMPARA EN CADA CICLO, Y POR QUÉ NO SON BYTES
=======================================================

Los bytes de un fichero SQLite dependen del orden de escritura de páginas y de
espacio libre reutilizado. Comparar bytes daría falsos rojos que no son defectos
del candidato. Se compara **contenido lógico** —``vectores.volcado_logico`` para
el sidecar; inventario, DDL y filas para el `FTS5`—, que es lo que la puerta
pregunta: que el derivado se reconstruya **desde el canon**, no que el fichero
salga idéntico byte a byte.

TRES ABLACIONES NO SE EJECUTAN, Y SE DICE POR QUÉ
=================================================

`AB-2`, `AB-4` y `AB-5` **no son ejecutables sobre los candidatos congelados**, y
esto se comprobó contra el código, no se supuso. Las razones no son la misma:

- **`AB-2`** —«desactivar la etapa léxica de `RF-16`»— pide quitar `E2` y seguir
  por `E3`. Eso es **un salto de etapa, y `B04-RF-14` lo prohíbe**. El motor lo
  hace cumplir: en cuanto una etapa no está autorizada, ``stops.parada_por_modo``
  devuelve `S2` y el bucle de ``engine.py`` **rompe**. De modo que
  ``espacios_autorizados`` autoriza **un prefijo**, no un conjunto al que se le
  pueda quitar una etapa de en medio. No es una carencia del arnés: es que la
  norma prohíbe la ablación que el banco describe.
- **`AB-4`** —desactivar la validación de polaridad, condición y tiempo
  **manteniendo la señal**— necesita un interruptor que no existe: los dos que los
  candidatos exponen, ``con_senal_relacional`` y ``con_senal_vectorial``, apagan
  **la señal entera**, que es justo lo contrario.
- **`AB-5`** —`G1-G12` de una en una— necesita una máscara que el motor no tiene:
  ``gates.aplicar_previas`` encadena `G1-G10` en orden fijo, y ni ``aplicar_g11``
  ni ``aplicar_g12`` aceptan selección.

Las dos últimas exigirían modificar código congelado y emitir fichas sucesoras, y
eso es un acto de gobierno, no una decisión de este módulo. Fingir cualquiera de
las tres con un sucedáneo sería peor que no correrlas: daría una cifra donde no
hay medición.

`AB-2` estuvo **mal ejecutada** en la primera versión de este módulo: se le pasó
``{E1, E3, E4}`` creyendo que `E2` se saltaría, y lo que hizo el motor fue parar
en `E2`. El resultado era idéntico al de `AB-1` porque **era** `AB-1` con otro
nombre. Se corrigió en cuanto la coincidencia exacta de las dos cifras lo delató.

`AB-4` importa más que las otras, y por eso la carencia se declara y no se
disimula: es la única que separa **la señal** de **su validación**, y sin ella no
puede saberse si lo que aporta una señal tardía lo aporta la señal o lo aporta el
filtro que la limpia.
"""

from __future__ import annotations

import json
import random
import shutil
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from experiments.adr002.candidates.common import derived
from experiments.adr002.candidates.common.contracts import Etapa

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]
SALIDA: Final = "artifacts/adr002_round/niveles_2_y_3_v0.1.json"

#: `ARQ-CA-01` exige 30 ciclos completos, no uno.
CICLOS_DE_REGENERACION: Final = 30

#: `ARQ-CA-03` exige `n >= 30` intra-sesión y `>= 5` sesiones independientes.
REPETICIONES_DE_ESTABILIDAD: Final = 30
SESIONES_DE_ESTABILIDAD: Final = 5

#: `AB-6` es el suelo de comparación: sin él, una métrica alta no demuestra nada.
#: Fija, porque un suelo que cambiara en cada corrida no sería referencia de nada.
SEMILLA_DEL_SUELO: Final = 20260726

#: Ficheros que `ARQ-CA-02` obliga a inspeccionar tras la purga.
SUFIJOS_DE_SQLITE: Final[tuple[str, ...]] = ("", "-wal", "-shm", "-journal")

#: Quiénes construyen un índice derivado **propio**. `A` y `C` no; los cinco
#: comparten el `FTS5`, que sí es derivado y sí entra en `ARQ-CA-01`.
CON_SIDECAR_PROPIO: Final[frozenset[str]] = frozenset({"ADR002-B", "ADR002-D"})

#: El control declara exenciones en su ficha. No son un aprobado: son la razón
#: por la que el caso **no le aplica**, y el caso se adjudica como tal.
EXENCIONES_DEL_CONTROL: Final[Mapping[str, tuple[str, ...]]] = {
    "ARQ-CA-04": ("limites_del_ciclo_de_indice", "consumo_de_almacenamiento_previo"),
    "ARQ-CA-05": ("limites_locales_por_etapa", "etapas_e0_e5"),
}

ABLACIONES_NO_EJECUTABLES: Final[Mapping[str, str]] = {
    "AB-2": (
        "desactivar la etapa lexica MANTENIENDO las posteriores exigiria saltar de "
        "E1 a E3, y B04-RF-14 prohibe exactamente ese salto. El motor lo hace "
        "cumplir: engine.py rompe el bucle en cuanto una etapa no esta autorizada "
        "(stops.parada_por_modo devuelve S2 y el for hace break), de modo que "
        "espacios_autorizados es una autorizacion por PREFIJO y no un conjunto del "
        "que se pueda quitar una etapa intermedia. No es una carencia del arnes: "
        "es que la norma prohibe la ablacion que el banco describe, y ejecutarla "
        "exigiria un motor que incumpliese RF-14"
    ),
    "AB-4": (
        "desactivar la validacion de polaridad, condicion y tiempo MANTENIENDO la "
        "senal exige un interruptor que ningun candidato congelado tiene: los dos "
        "que exponen (con_senal_relacional y con_senal_vectorial) apagan la senal "
        "entera, que es justo lo contrario. Ejecutarla obligaria a modificar los "
        "cuatro candidatos y emitir fichas sucesoras: es un acto de gobierno, no de "
        "este modulo. Es ademas la unica ablacion que separa la senal de su "
        "validacion, de modo que no poder correrla es una carencia real de esta "
        "ronda y se declara como tal"
    ),
    "AB-5": (
        "desactivar G1-G12 de una en una exige una mascara de puertas que el motor "
        "comun no tiene: gates.aplicar_previas encadena G1-G10 en orden fijo y no "
        "acepta parametro de seleccion, y lo mismo aplicar_g11 y aplicar_g12. "
        "Anadirla tocaria la capa comun, congelada y fijada por blob en la custodia "
        "de las fichas"
    ),
}


class Veredicto(StrEnum):
    """Tres valores, no dos.

    `NO_APLICABLE` no es un aprobado encubierto: es lo que corresponde a quien
    tiene la exención **declarada en su ficha antes de medir**. Colapsarlo en
    `PASA` regalaría un aprobado; colapsarlo en `FALLA` castigaría al control
    por ser el control.
    """

    PASA = "PASA"
    FALLA = "FALLA"
    NO_APLICABLE = "NO_APLICABLE"


@dataclass(frozen=True, slots=True)
class ResultadoArquitectonico:
    """Un caso de nivel 2: qué dio, para quién, y por qué."""

    caso: str
    titulo: str
    puerta: str
    participante: str
    veredicto: Veredicto
    detalle: str


@dataclass(frozen=True, slots=True)
class ResultadoDeAblacion:
    """Una ablación: qué apagó y qué dejó de acertar.

    No lleva veredicto **a propósito**: el banco declara que las ablaciones
    «nunca producen veredicto de conformidad».
    """

    ablacion: str
    participante: str
    ejecutada: bool
    exactos: int
    casos: int
    perdidos_respecto_de_la_completa: tuple[str, ...]
    ganados_respecto_de_la_completa: tuple[str, ...]
    motivo_si_no_se_ejecuta: str = ""
    #: Qué lectura de la ablación produjo esta fila, cuando el banco admite más
    #: de una. Vacío cuando solo hay una.
    lectura: str = ""


# --------------------------------------------------------------------------
# Nivel 2 · los cinco casos arquitectónicos
# --------------------------------------------------------------------------


def _estado_del_fts5(conexion: sqlite3.Connection) -> tuple[Any, dict[str, int]]:
    return derived.inventariar(conexion), derived.filas_indexadas(conexion)


def ciclo_del_fts5(ruta_canon: Path, ciclos: int = CICLOS_DE_REGENERACION) -> tuple[bool, str]:
    """Borra y regenera el `FTS5` entero `n` veces, contra el canon.

    Se comprueban las tres cosas que ``derived.py`` distingue —tablas, sombras
    y triggers—, porque reconstruir solo las tablas deja un índice que nadie
    mantiene y una comprobación ingenua no lo vería.
    """
    conexion = sqlite3.connect(str(ruta_canon))
    try:
        ddl = derived.leer_ddl_canonico(conexion)
        antes, filas_antes = _estado_del_fts5(conexion)
        if not antes.completo:
            return False, "el canon no trae el derivado completo antes de empezar"
        nombres = (*antes.tablas, *antes.sombras, *antes.triggers)

        for ciclo in range(1, ciclos + 1):
            derived.borrar_derivado(conexion)
            residuos = derived.objetos_residuales(conexion, nombres)
            if residuos:
                return False, f"ciclo {ciclo}: quedaron objetos tras el borrado: {residuos[:4]}"
            derived.reconstruir_derivado(conexion, ddl)
            despues, filas_despues = _estado_del_fts5(conexion)
            fallos = derived.fallos_de_reconstruccion(antes, despues)
            if fallos:
                return False, f"ciclo {ciclo}: {fallos[0]}"
            if filas_despues != filas_antes:
                return False, f"ciclo {ciclo}: filas {filas_despues} != {filas_antes}"
        return True, f"{ciclos}/{ciclos} ciclos del FTS5 con inventario y filas restaurados"
    finally:
        conexion.close()


def ciclo_del_sidecar(
    ruta_canon: Path, destino: Path, ciclos: int = CICLOS_DE_REGENERACION
) -> tuple[bool, str]:
    """Borra y regenera el sidecar vectorial `n` veces, desde el canon.

    Compara el **volcado lógico**, no los bytes: el contenido es lo que la
    puerta pregunta, y los bytes de SQLite dependen de detalles de paginación
    que no son del candidato.
    """
    from experiments.adr002.candidates.adr002_b import vectores

    destino.parent.mkdir(parents=True, exist_ok=True)
    vectores.construir(ruta_canon, destino)
    referencia = vectores.volcado_logico(destino)

    for ciclo in range(1, ciclos + 1):
        vectores.borrar(destino)
        if destino.exists() or vectores.residuos(destino):
            return False, f"ciclo {ciclo}: quedaron residuos tras el borrado del sidecar"
        vectores.construir(ruta_canon, destino)
        if vectores.volcado_logico(destino) != referencia:
            return False, f"ciclo {ciclo}: la reconstruccion del sidecar no es equivalente"
    return True, f"{ciclos}/{ciclos} ciclos del sidecar con volcado logico identico"


def arq_ca_01(
    participante: str, ruta_canon: Path, trabajo: Path, ciclos: int = CICLOS_DE_REGENERACION
) -> tuple[Veredicto, str]:
    """Borrado y regeneración completos de **todo** índice derivado, 30/30."""
    bien_fts, detalle_fts = ciclo_del_fts5(ruta_canon, ciclos)
    if not bien_fts:
        return Veredicto.FALLA, f"FTS5: {detalle_fts}"
    if participante not in CON_SIDECAR_PROPIO:
        return Veredicto.PASA, f"{detalle_fts}; sin indice propio que regenerar"
    bien_side, detalle_side = ciclo_del_sidecar(ruta_canon, trabajo / "vectores.sqlite3", ciclos)
    if not bien_side:
        return Veredicto.FALLA, f"sidecar: {detalle_side}"
    return Veredicto.PASA, f"{detalle_fts}; {detalle_side}"


def fragmentos_recuperables(fichero: Path, cargas: Sequence[str]) -> tuple[str, ...]:
    """Busca las cargas en los **bytes crudos** de un fichero y sus auxiliares.

    En bytes y no en tablas: una fila borrada de la que quedara rastro en una
    página libre seguiría siendo un fragmento recuperable, y es exactamente lo
    que la puerta 5 prohíbe.
    """
    encontrados: list[str] = []
    for sufijo in SUFIJOS_DE_SQLITE:
        auxiliar = Path(str(fichero) + sufijo)
        if not auxiliar.exists():
            continue
        crudo = auxiliar.read_bytes()
        encontrados.extend(
            f"{auxiliar.name}:{carga}" for carga in cargas if carga.encode("utf-8") in crudo
        )
    return tuple(encontrados)


def arq_ca_02(
    participante: str, trabajo: Path, ruta_canon: Path, cargas: Sequence[str]
) -> tuple[Veredicto, str]:
    """Purga física: tras checkpoint, journal y `VACUUM`, ni un fragmento.

    El caso nombra las tres operaciones y aquí se ejecutan: sin el `VACUUM` una
    página liberada conserva su contenido y la inspección diría «limpio» sobre
    un fichero que no lo está.
    """
    from experiments.adr002.candidates.adr002_b import vectores

    if participante not in CON_SIDECAR_PROPIO:
        return Veredicto.NO_APLICABLE, (
            "no construye indice derivado propio: no hay derivado que purgar. El FTS5 "
            "es del canon y su purga no es una obligacion de este candidato"
        )

    destino = trabajo / "purga" / "vectores.sqlite3"
    destino.parent.mkdir(parents=True, exist_ok=True)
    vectores.construir(ruta_canon, destino)

    conexion = sqlite3.connect(str(destino))
    try:
        conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conexion.execute("VACUUM")
        conexion.commit()
    finally:
        conexion.close()

    vectores.borrar(destino)
    supervivientes = fragmentos_recuperables(destino, cargas)
    if supervivientes:
        return Veredicto.FALLA, f"fragmentos recuperables: {list(supervivientes[:5])}"
    return Veredicto.PASA, (
        f"tras checkpoint, journal y VACUUM no queda .db, -wal, -shm ni -journal, "
        f"ni rastro de {len(cargas)} cargas buscadas en bytes crudos"
    )


def arq_ca_03(
    repeticiones_por_sesion: Sequence[int],
    ordenes_distintos: Sequence[Sequence[Sequence[str]]],
) -> tuple[Veredicto, str]:
    """Estabilidad: **un** orden y **un** conjunto, dentro y entre sesiones.

    Recibe los vectores de respuesta **distintos** observados, no la lista
    entera repetida: un participante determinista produce un solo vector y
    guardar treinta copias iguales no añadiría evidencia. Lo que sí hace falta
    es el recuento real por sesión, y por eso viaja aparte: sin él, «un solo
    orden» podría significar «una sola repetición».

    Orden y conjunto se comprueban por separado a propósito: un candidato
    podría devolver siempre el mismo conjunto en distinto orden, y `B04-RF-22`
    pide estabilidad de orden, no solo de contenido.
    """
    if len(repeticiones_por_sesion) < SESIONES_DE_ESTABILIDAD:
        return Veredicto.FALLA, (
            f"{len(repeticiones_por_sesion)} sesiones independientes; se exigen "
            f"{SESIONES_DE_ESTABILIDAD}"
        )
    escasas = [n for n in repeticiones_por_sesion if n < REPETICIONES_DE_ESTABILIDAD]
    if escasas:
        return Veredicto.FALLA, (
            f"sesiones con {escasas} repeticiones; se exigen {REPETICIONES_DE_ESTABILIDAD}"
        )
    if not ordenes_distintos:
        return Veredicto.FALLA, "no se observo ninguna respuesta"
    conjuntos = {tuple(tuple(sorted(caso)) for caso in vector) for vector in ordenes_distintos}
    if len(conjuntos) != 1:
        return Veredicto.FALLA, f"{len(conjuntos)} conjuntos distintos entre repeticiones"
    if len(ordenes_distintos) != 1:
        return Veredicto.FALLA, (
            f"1 conjunto pero {len(ordenes_distintos)} ordenes distintos entre repeticiones"
        )
    return Veredicto.PASA, (
        f"1 orden y 1 conjunto en {len(repeticiones_por_sesion)} sesiones independientes "
        f"de {repeticiones_por_sesion[0]} repeticiones cada una"
    )


def _exencion_declarada(ficha: Mapping[str, Any], caso: str) -> str | None:
    """La exención del control, si su ficha la declara para este caso."""
    exenciones = ficha.get("exenciones_de_control")
    if not isinstance(exenciones, Mapping):
        return None
    citadas = [
        f"«{clave}: {exenciones[clave]}»"
        for clave in EXENCIONES_DEL_CONTROL.get(caso, ())
        if clave in exenciones
    ]
    return " ".join(citadas) or None


def arq_ca_04(ficha: Mapping[str, Any]) -> tuple[Veredicto, str]:
    """La ficha declara tamaño y ciclo de todo índice adicional, congelada.

    No se mide nada: se lee la ficha. Es un caso de **gobierno**, y lo que
    comprueba es que la declaración existiera **antes** de la primera ejecución.
    """
    if ficha.get("estado") != "CONGELADA":
        return Veredicto.FALLA, "la ficha vigente no esta CONGELADA"
    congelacion = ficha.get("declaracion_de_congelacion")
    if not isinstance(congelacion, Mapping):
        return Veredicto.FALLA, "la ficha no trae declaracion de congelacion"
    if congelacion.get("valores_anteriores_a_la_primera_ejecucion") is not True:
        return Veredicto.FALLA, "la ficha no declara valores anteriores a la primera ejecucion"
    if ficha.get("no_contiene_resultados") is not True:
        return Veredicto.FALLA, "la ficha no declara estar libre de resultados"

    indices = ficha.get("indices_no_lexicos")
    if not indices:
        exencion = _exencion_declarada(ficha, "ARQ-CA-04")
        if exencion:
            return Veredicto.NO_APLICABLE, f"exencion declarada en la ficha: {exencion}"
        return Veredicto.PASA, (
            "ficha congelada y sin indice adicional que declarar: nada que acotar por magnitud"
        )

    for indice in indices:
        if not isinstance(indice, Mapping):
            return Veredicto.FALLA, "un indice adicional no es un objeto declarable"
        limites = indice.get("limites_por_magnitud")
        if not isinstance(limites, Mapping) or "almacenamiento_b" not in limites:
            return Veredicto.FALLA, f"{indice.get('nombre')}: sin limite por magnitud"
        if not indice.get("comportamiento_de_borrado"):
            return Veredicto.FALLA, f"{indice.get('nombre')}: sin comportamiento de borrado"
        if not indice.get("construccion_y_reconstruccion"):
            return Veredicto.FALLA, f"{indice.get('nombre')}: sin ciclo de construccion"
    ciclo = ficha.get("ciclo_de_indice")
    if not isinstance(ciclo, Mapping) or not ciclo.get("operaciones"):
        return Veredicto.FALLA, "la ficha no declara operaciones del ciclo de indice"
    return Veredicto.PASA, (
        f"{len(indices)} indice(s) con limite por magnitud, borrado y ciclo declarados "
        f"y congelados antes de la primera ejecucion"
    )


def arq_ca_05(ficha: Mapping[str, Any]) -> tuple[Veredicto, str]:
    """Coste local y externo separados por etapa, y la suma explica el total.

    El coste externo se declara en **texto**, no en nanosegundos, y eso no es
    un hueco: `ADR002-TOL-202` prohíbe sumar coste externo al local, de modo
    que un candidato sin llamadas externas no tiene un número que declarar. Lo
    que se exige es que **esté separado y dicho**, y eso sí se comprueba.
    """
    coste = ficha.get("coste_por_etapa")
    if not isinstance(coste, Mapping):
        exencion = _exencion_declarada(ficha, "ARQ-CA-05")
        if exencion:
            return Veredicto.NO_APLICABLE, f"exencion declarada en la ficha: {exencion}"
        return Veredicto.FALLA, "la ficha no declara coste por etapa"

    etapas = coste.get("etapas")
    if not isinstance(etapas, Sequence) or isinstance(etapas, str):
        return Veredicto.FALLA, "el coste por etapa no es una secuencia"
    declaradas = {str(e.get("etapa")) for e in etapas if isinstance(e, Mapping)}
    faltan = {e.value for e in Etapa} - declaradas
    if faltan:
        return Veredicto.FALLA, f"faltan etapas en el coste declarado: {sorted(faltan)}"
    sin_externo = [
        str(e.get("etapa"))
        for e in etapas
        if isinstance(e, Mapping) and not e.get("coste_externo_declarado")
    ]
    if sin_externo:
        return Veredicto.FALLA, f"etapas sin coste externo separado: {sorted(sin_externo)}"

    local = sum(int(e.get("coste_local_limite_ns", 0)) for e in etapas if isinstance(e, Mapping))
    total = coste.get("coste_local_total_ns")
    extremo = coste.get("coste_extremo_a_extremo_ns")
    if local != total:
        return Veredicto.FALLA, f"la suma por etapa ({local}) no explica el total ({total})"
    if total != extremo:
        return Veredicto.FALLA, (
            f"el total local ({total}) no explica el extremo a extremo ({extremo})"
        )
    return Veredicto.PASA, (
        f"seis etapas con local y externo separados; la suma local {local} ns explica "
        f"el extremo a extremo declarado"
    )


# --------------------------------------------------------------------------
# Nivel 3 · las ablaciones
# --------------------------------------------------------------------------

#: Espacios que cada ablación deja autorizados. `AB-0` no se parametriza así:
#: es `T0`, la línea base congelada de 0.1, y ya está medida.
ESPACIOS_POR_ABLACION: Final[Mapping[str, frozenset[Etapa]]] = {
    #: «Todo salvo E0/E1 estructurado y exacto». Es un **prefijo**, y por eso
    #: sí se puede pedir: se recorre `E1` y se para.
    "AB-1": frozenset({Etapa.E1}),
}

#: `AB-3` —«etapa de significado/relaciones de RF-17»— **no** se hace quitando
#: `E3` del conjunto de espacios: en `A` y en `C` la `E3` contiene además la
#: expansión léxico-estructurada por términos puente, que no es señal tardía.
#: Apagar `E3` entera mediría dos cosas y atribuiría las dos a la señal. Los
#: interruptores congelados apagan exactamente la señal tardía, que es lo que
#: el banco dice que `AB-3` aísla.
AB_3_POR_INTERRUPTOR: Final = (
    "AB-3 apaga la senal tardia con los interruptores congelados del propio "
    "candidato (con_senal_relacional / con_senal_vectorial), no retirando E3 del "
    "conjunto de espacios: en A y C la E3 contiene tambien expansion "
    "lexico-estructurada por terminos puente, que no es senal tardia, y apagar la "
    "etapa entera atribuiria a la senal algo que no es suyo"
)


#: `AB-6` dice dos cosas a la vez —«**orden** aleatorizado con semilla fija» y
#: «aísla: **suelo** de comparación»— y no son la misma medida. Se ejecutan las
#: dos, con su nombre, en vez de elegir una en silencio.
LECTURAS_DE_AB_6: Final[Mapping[str, str]] = {
    "conjunto": (
        "seleccion al azar sobre el canon entero, tantos elementos como espera el "
        "caso: es el suelo del acierto exacto, y responde «cuanto de este 23/47 lo "
        "consigue cualquiera»"
    ),
    "orden": (
        "el conjunto correcto entregado en orden barajado: es el suelo del acierto "
        "de ORDEN, y responde «cuanto del orden correcto es merito y cuanto azar». "
        "Es la lectura literal de «orden aleatorizado con semilla fija»"
    ),
}


def suelo_aleatorio(universo: Sequence[str], cuantos: int, semilla: int) -> tuple[str, ...]:
    """`AB-6`: el suelo. Sin él, una métrica alta no demuestra nada.

    El universo tiene que ser **el canon**, no los elegibles del caso: en las
    consultas `EXHAUSTIVA` el propio banco define ``resultado_esperado ==
    elegibles_semanticos``, de modo que sacar `n` de `n` elegibles devuelve la
    respuesta **siempre** y el suelo saldría del 100 %. Un suelo que acierta
    todo no es un suelo: es el oráculo prestado al azar.
    """
    generador = random.Random(semilla)
    muestra = list(universo)
    generador.shuffle(muestra)
    return tuple(muestra[:cuantos])


def orden_barajado(esperado: Sequence[str], semilla: int) -> tuple[str, ...]:
    """El conjunto correcto, en orden al azar. Suelo del acierto de orden."""
    generador = random.Random(semilla)
    muestra = list(esperado)
    generador.shuffle(muestra)
    return tuple(muestra)


def perdido(completa: Sequence[str], ablacionada: Sequence[str]) -> tuple[str, ...]:
    """Lo que la ablación dejó de acertar. Es la aportación que aísla."""
    presentes = frozenset(ablacionada)
    return tuple(i for i in completa if i not in presentes)


# --------------------------------------------------------------------------
# Documento
# --------------------------------------------------------------------------


def documento(
    arquitectonicos: Sequence[ResultadoArquitectonico],
    ablaciones: Sequence[ResultadoDeAblacion],
) -> dict[str, Any]:
    """El artefacto. Publica también lo que no se pudo ejecutar."""
    return {
        "documento": "Niveles 2 y 3 del banco de ADR-002",
        "version_esquema": "niveles-2-y-3-adr002-0.1",
        "estado": "EVIDENCIA",
        "por_que_faltaban": (
            "la ronda primaria ejecutaba el nivel 1 y nada mas; el nivel 4 se recupero "
            "en discriminante_relacional_v0.1.json y estos dos, aqui"
        ),
        "no_mide_tiempo": (
            "ninguna cifra de latencia sale de este artefacto: las publicadas en v0.1 y "
            "v0.2 son las unicas, y estas comprobaciones no las tocan"
        ),
        "arquitectonicos": [
            {
                "caso": r.caso,
                "titulo": r.titulo,
                "puerta": r.puerta,
                "participante": r.participante,
                "veredicto": r.veredicto.value,
                "detalle": r.detalle,
            }
            for r in arquitectonicos
        ],
        "ablaciones": [
            {
                "ablacion": a.ablacion,
                "participante": a.participante,
                "ejecutada": a.ejecutada,
                "exactos": a.exactos,
                "casos": a.casos,
                "perdidos_respecto_de_la_completa": list(a.perdidos_respecto_de_la_completa),
                "ganados_respecto_de_la_completa": list(a.ganados_respecto_de_la_completa),
                "motivo_si_no_se_ejecuta": a.motivo_si_no_se_ejecuta,
                "lectura": a.lectura,
            }
            for a in ablaciones
        ],
        "ablaciones_no_ejecutables": dict(ABLACIONES_NO_EJECUTABLES),
        "lectura_de_ab_3": AB_3_POR_INTERRUPTOR,
        "lecturas_de_ab_6": dict(LECTURAS_DE_AB_6),
        "las_ablaciones_no_adjudican": (
            "el banco declara el nivel 3 «instrumentos de medida; nunca producen "
            "veredicto de conformidad, y por eso no llevan ficha de caso del PDP §7». "
            "Aqui no llevan veredicto por eso mismo"
        ),
        "no_elige": (
            "los casos arquitectonicos adjudican puertas y las ablaciones son "
            "instrumentos: ninguna de las dos cosas elige alternativa"
        ),
    }


def escribir(destino: Path, contenido: Mapping[str, Any]) -> None:
    """Escritura atómica, sin sobrescribir en silencio."""
    from experiments.adr002.tolerances.run_envelope import escribir_json_atomico

    escribir_json_atomico(destino, dict(contenido))


def limpiar(directorio: Path) -> None:
    shutil.rmtree(directorio, ignore_errors=True)


def cargar_ficha(candidato: str, version: int) -> dict[str, Any]:
    ruta = RAIZ_REPOSITORIO / f"artifacts/adr002_cards/ficha_{candidato}_v{version}.json"
    datos: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return datos


__all__ = [
    "ABLACIONES_NO_EJECUTABLES",
    "AB_3_POR_INTERRUPTOR",
    "CICLOS_DE_REGENERACION",
    "CON_SIDECAR_PROPIO",
    "ESPACIOS_POR_ABLACION",
    "EXENCIONES_DEL_CONTROL",
    "REPETICIONES_DE_ESTABILIDAD",
    "SALIDA",
    "SEMILLA_DEL_SUELO",
    "SESIONES_DE_ESTABILIDAD",
    "SUFIJOS_DE_SQLITE",
    "ResultadoArquitectonico",
    "ResultadoDeAblacion",
    "Veredicto",
    "arq_ca_01",
    "arq_ca_02",
    "arq_ca_03",
    "arq_ca_04",
    "arq_ca_05",
    "cargar_ficha",
    "ciclo_del_fts5",
    "ciclo_del_sidecar",
    "documento",
    "escribir",
    "fragmentos_recuperables",
    "limpiar",
    "perdido",
    "suelo_aleatorio",
]
