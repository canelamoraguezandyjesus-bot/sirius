"""El contador de los siete días (D1b, incidencia #268): registro y racha.

El verificador de proyección (D1a, :mod:`sirius_engine.projection_verifier`)
sabe comparar el motor con su incidencia UNA vez y decir si un día es verde.
Este módulo es lo que hace falta para convertir esa comparación puntual en la
medición que exige el contrato §11.2: **siete días naturales consecutivos en
verde, y cero correcciones manuales**, por clase de trabajo. **No conmuta
nada** -eso es un acto separado del propietario, en otro bloque.

Tres piezas, en el orden en que las usa el punto de entrada
(:mod:`sirius_engine.seven_day_streak_cli`):

1. **El registro** (:func:`leer_registro`, :func:`anadir_lineas`): un fichero
   JSONL versionado, que solo crece. Añadir la misma línea dos veces -misma
   entrada, mismo texto exacto- no duplica nada (requisito 6).
2. **El detector de correcciones manuales** (:func:`detectar_correcciones_manuales`):
   la condición 2 del contrato hoy no es medible con disciplina humana -nada
   registra que alguien arregló a mano el almacén o las etiquetas- así que se
   deriva de dos cosas que el sistema YA observa: el propio registro (qué
   ejes divergían y dejaron de hacerlo) y el diario de eventos del motor
   (:class:`sirius_engine.domain.events.Event`, arquitectura §3.5/§12, que es
   la única fuente donde una transición LEGÍTIMA del motor queda escrita). Una
   `DIVERGENCIA` que se resuelve a `COINCIDE` sin que el diario registre
   ninguna transición del motor en el intervalo es exactamente la huella que
   la nota de arranque de la incidencia pide: nadie tuvo que anotar nada para
   que apareciera.
3. **El contador** (:func:`evaluar_racha`): camina hacia atrás desde el día de
   la pasada. Cada día exige línea presente, verde, y sin huella de
   corrección -la primera vez que falla cualquiera de los tres, la racha
   vuelve a cero, con el motivo exacto conservado (requisito 7).

Una cuarta pieza, independiente de las tres anteriores pero con la misma
exigencia de no inventar números: :func:`hora_recomendada_pasada` deriva, de
los `schedule: cron:` reales de `.github/workflows/*.yml`, la hora del día
más alejada de cualquier disparo periódico -el punto medio del mayor hueco
libre-, y la valida contra la ventana de tolerancia de etiqueta de máquina
(:func:`sirius_engine.projection_verifier.ventana_tolerancia_etiqueta_maquina`).
El cierre de la incidencia #265 midió que, con la tolerancia vigente, un día
solo puede salir verde si nada se movió en las tres horas previas a la
pasada: elegir la hora a ojo desoiría esa medición.

Determinista y sin red: todo lo que sigue trabaja sobre lo que ya se leyó -el
registro, el diario de eventos, los ficheros YAML del propio repositorio-,
igual que exige :mod:`sirius_engine.projection_verifier`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml

from sirius_engine.domain.events import AggregateType, Event
from sirius_engine.domain.work_item import WorkItemClass
from sirius_engine.projection_verifier import (
    EJE_ESTADO,
    EJE_FASE,
    LineaRegistro,
    ResultadoEje,
    VeredictoEje,
    formatear_linea,
    ventana_tolerancia_etiqueta_maquina,
)

#: Cuántos días naturales consecutivos en verde exige el contrato §11.2.
DIAS_REQUERIDOS = 7

_WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"


# --- 1. El registro: JSONL versionado, solo crece ---------------------------


def _parsear_linea(texto: str) -> LineaRegistro:
    datos: dict[str, Any] = json.loads(texto)
    return LineaRegistro(
        instante=datetime.fromisoformat(datos["instante"]),
        clase=WorkItemClass(datos["clase"]),
        work_id=datos["work_id"],
        veredictos=tuple(
            VeredictoEje(
                eje=eje["eje"],
                resultado=ResultadoEje(eje["resultado"]),
                motivo=eje["motivo"],
            )
            for eje in datos["ejes"]
        ),
    )


def leer_registro(ruta: Path) -> tuple[LineaRegistro, ...]:
    """Todas las líneas del registro, en el orden en que se escribieron.

    Un registro que no existe todavía se lee como vacío -es el caso
    degenerado de "sin línea registrada", no un error: la primera pasada de
    verdad lo crea.
    """
    if not ruta.exists():
        return ()
    lineas = [linea.strip() for linea in ruta.read_text(encoding="utf-8").splitlines()]
    return tuple(_parsear_linea(linea) for linea in lineas if linea)


def anadir_lineas(ruta: Path, lineas: Sequence[LineaRegistro]) -> int:
    """Añade ``lineas`` nuevas al final del registro. Devuelve cuántas se escribieron de verdad.

    Determinista y solo-crece (requisito 6): nunca reescribe ni reordena lo
    que ya había. Una línea cuyo texto exacto -mismo instante, misma clase,
    mismo work_id, mismos veredictos- ya está en el fichero no se repite: así
    dos pasadas idénticas (mismo ``instante`` congelado, típicamente en
    pruebas) no duplican ni pierden líneas. Dos pasadas reales, en cambio,
    llevan cada una su propio ``instante``, así que nunca coinciden por
    accidente.
    """
    existentes = set()
    if ruta.exists():
        existentes = {
            texto.strip()
            for texto in ruta.read_text(encoding="utf-8").splitlines()
            if texto.strip()
        }

    vistas = set(existentes)
    nuevas: list[str] = []
    for linea in lineas:
        texto = formatear_linea(linea)
        if texto in vistas:
            continue
        vistas.add(texto)
        nuevas.append(texto)

    if not nuevas:
        return 0

    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as fichero:
        for texto in nuevas:
            fichero.write(texto)
            fichero.write("\n")
    return len(nuevas)


# --- 2. La huella de una corrección manual, derivada -------------------------


#: Qué eje puede explicar cada ``kind`` de :class:`Event` -derivado de qué
#: campo toca cada transición tipada en :mod:`sirius_engine.domain.work_item`
#: (``activate``, ``begin_execution``, ``reprioritize``...). Un ``kind``
#: ausente de los dos conjuntos -``work_item_reprioritized`` (no toca fase ni
#: estado) o ``work_item_budget_cutoff_started`` (anexa la instantánea sin
#: transicionarla)- no explica NINGUNA resolución: así una repriorización
#: normal, o cualquier ``kind`` futuro sin mapeo aquí, no puede ocultar una
#: corrección manual del eje que de verdad se resolvió (CODEX-001, ronda 2).
_KINDS_QUE_EXPLICAN_ESTADO: frozenset[str] = frozenset(
    {
        "work_item_created",
        "work_item_created_needing_decision",
        "work_item_activated",
        "work_item_cancelled",
        "work_item_escalated",
        "work_item_decision_resolved",
        "work_item_dispatched_async",
        "work_item_observed_external_fact",
        "work_item_failed_safely",
        "work_item_reactivated",
        "work_item_delivered",
        "work_item_paused",
        "work_item_resumed",
        "work_item_budget_cutoff_stopped_waiting",
    }
)

_KINDS_QUE_EXPLICAN_FASE: frozenset[str] = frozenset(
    {
        "work_item_created",
        "work_item_created_needing_decision",
        "work_item_execution_started",
        "work_item_check_started",
        "work_item_review_started",
        "work_item_review_approved",
        "work_item_repair_requested",
        "work_item_repair_resumed",
        "work_item_scope_changed",
    }
)

#: Ejes que este detector sabe explicar. Uno ausente de aquí -hoy,
#: :data:`~sirius_engine.projection_verifier.EJE_FIDELIDAD_PROYECCION`, que no
#: se repite tras el despacho- nunca tiene un ``kind`` que lo explique, así
#: que cualquier resolución suya se trata, con razón, como sin explicar.
_KINDS_POR_EJE: dict[str, frozenset[str]] = {
    EJE_FASE: _KINDS_QUE_EXPLICAN_FASE,
    EJE_ESTADO: _KINDS_QUE_EXPLICAN_ESTADO,
}


@dataclass(frozen=True, slots=True)
class HuellaCorreccionManual:
    """Un eje que dejó de divergir sin que el diario de eventos lo explique.

    No es una prueba de que alguien tocó el almacén a mano: es la señal
    derivable más cercana que el sistema ya observa (requisito 3). El motor
    solo cambia su propio estado a través de sus transiciones tipadas, y CADA
    una de ellas queda en :class:`~sirius_engine.domain.events.Event`
    (arquitectura §3.5/§12) -así que una divergencia que se resuelve sin
    ninguna transición del motor QUE TOQUE ESE EJE en el intervalo no puede
    explicarse por el camino normal: algo la resolvió por fuera de él.
    """

    work_id: str
    eje: str
    dia: date
    motivo: str


def detectar_correcciones_manuales(
    lineas: Sequence[LineaRegistro], eventos: Sequence[Event]
) -> tuple[HuellaCorreccionManual, ...]:
    """Recorre el registro por ``work_id`` buscando divergencias que se resuelven solas.

    Compara cada línea con la SIGUIENTE del mismo ``work_id`` (en orden de
    ``instante``): si un eje daba ``DIVERGENCIA`` y pasa a ``COINCIDE``, hace
    falta que el diario de eventos tenga AL MENOS una transición **del propio
    ``WorkItem`` (:data:`~sirius_engine.domain.events.AggregateType.WORK_ITEM`)
    y cuyo ``kind`` sea capaz de tocar ESE eje** (:data:`_KINDS_POR_EJE`) en el
    intervalo -un evento ajeno al eje resuelto, como una repriorización entre
    dos días de fase, no cuenta como explicación-. Sin eso, se registra la
    huella.

    Deliberadamente no intenta cubrir todos los caminos por los que una
    corrección manual podría ocultarse -por ejemplo, una que además
    reescribiera el diario de eventos no dejaría huella aquí, y una hecha
    invocando la MISMA transición tipada que usaría el camino automático es
    indistinguible de esta con los datos que el diario guarda hoy (el evento
    no lleva quién ni por qué la disparó)-. La nota de arranque no pide un
    detector completo: pide uno derivado de lo que el sistema observa, no de
    que una persona se acuerde de anotarlo.
    """
    por_work_id: dict[str, list[LineaRegistro]] = {}
    for linea in lineas:
        por_work_id.setdefault(linea.work_id, []).append(linea)

    huellas: list[HuellaCorreccionManual] = []
    for work_id, entradas in por_work_id.items():
        ordenadas = sorted(entradas, key=lambda linea: linea.instante)
        eventos_del_trabajo = sorted(
            (
                e
                for e in eventos
                if e.aggregate_type is AggregateType.WORK_ITEM and e.aggregate_id == work_id
            ),
            key=lambda e: e.occurred_at,
        )
        for anterior, siguiente in pairwise(ordenadas):
            veredictos_antes = {v.eje: v for v in anterior.veredictos}
            veredictos_despues = {v.eje: v for v in siguiente.veredictos}
            for eje, v_antes in veredictos_antes.items():
                v_despues = veredictos_despues.get(eje)
                if v_despues is None or v_antes.resultado is not ResultadoEje.DIVERGENCIA:
                    continue
                if v_despues.resultado is not ResultadoEje.COINCIDE:
                    continue
                kinds_que_explican = _KINDS_POR_EJE.get(eje, frozenset())
                hay_transicion_del_motor = any(
                    anterior.instante < evento.occurred_at <= siguiente.instante
                    and evento.kind in kinds_que_explican
                    for evento in eventos_del_trabajo
                )
                if hay_transicion_del_motor:
                    continue
                huellas.append(
                    HuellaCorreccionManual(
                        work_id=work_id,
                        eje=eje,
                        dia=siguiente.instante.date(),
                        motivo=(
                            f"{eje} pasó de DIVERGENCIA ({v_antes.motivo}) a COINCIDE entre "
                            f"{anterior.instante.isoformat()} y {siguiente.instante.isoformat()} "
                            "sin ninguna transición del motor que toque ese eje registrada en "
                            "el diario de eventos en ese intervalo"
                        ),
                    )
                )
    return tuple(huellas)


# --- 3. El contador: camina hacia atrás, se rompe en el primer fallo --------


@dataclass(frozen=True, slots=True)
class EvaluacionRacha:
    """El veredicto del contador para una clase: cumple o no, y por qué.

    ``dias_consecutivos`` no se limita a :data:`DIAS_REQUERIDOS`: sigue
    contando mientras la racha aguante, para que "llevamos doce días" sea
    distinguible de "llevamos siete justos" (auditabilidad, requisito 7).
    """

    clase: WorkItemClass
    cumple: bool
    dias_consecutivos: int
    motivo: str


def evaluar_racha(
    *,
    lineas: Sequence[LineaRegistro],
    eventos: Sequence[Event],
    clase: WorkItemClass,
    hoy: date,
    dias_requeridos: int = DIAS_REQUERIDOS,
) -> EvaluacionRacha:
    """Cuenta la racha vigente de ``clase`` hacia atrás desde ``hoy``, sin conmutar nada.

    Un día cuenta si, y solo si, las tres condiciones se cumplen A LA VEZ:

    1. Hay al menos una línea registrada ese día natural para ``clase``
       (requisito 2: un día sin línea no es un día verde).
    2. TODAS las líneas de ese día son verdes
       (:attr:`~sirius_engine.projection_verifier.LineaRegistro.es_verde`,
       que ya excluye ``NO_COMPARABLE``, requisito 4).
    3. Ninguna huella de corrección manual (:func:`detectar_correcciones_manuales`)
       apunta a ese día.

    La primera vez que un día falla cualquiera de las tres, la racha se
    rompe ahí: el contador nunca mira más allá de esa frontera, así que un
    día verde ANTES de una racha rota no la resucita (requisito 1: el
    contador sabe volver a cero).
    """
    lineas_clase = [linea for linea in lineas if linea.clase is clase]
    por_dia: dict[date, list[LineaRegistro]] = {}
    for linea in lineas_clase:
        por_dia.setdefault(linea.instante.date(), []).append(linea)

    huellas_por_dia: dict[date, list[HuellaCorreccionManual]] = {}
    for huella in detectar_correcciones_manuales(lineas_clase, eventos):
        huellas_por_dia.setdefault(huella.dia, []).append(huella)

    dias_consecutivos = 0
    cursor = hoy
    motivo = f"sin ninguna línea registrada para {clase.value}"
    while True:
        lineas_dia = por_dia.get(cursor)
        if not lineas_dia:
            motivo = f"sin línea registrada el {cursor.isoformat()}"
            break
        no_verdes = [
            f"{v.eje}={v.resultado.value} ({v.motivo})"
            if v.motivo
            else f"{v.eje}={v.resultado.value}"
            for linea_del_dia in lineas_dia
            for v in linea_del_dia.veredictos
            if v.resultado is not ResultadoEje.COINCIDE
        ]
        if no_verdes:
            motivo = f"día no verde el {cursor.isoformat()}: {', '.join(no_verdes)}"
            break
        huellas_dia = huellas_por_dia.get(cursor)
        if huellas_dia:
            motivo = f"corrección manual detectada el {cursor.isoformat()}: " + "; ".join(
                h.motivo for h in huellas_dia
            )
            break
        dias_consecutivos += 1
        cursor = cursor - timedelta(days=1)

    cumple = dias_consecutivos >= dias_requeridos
    if cumple:
        motivo = (
            f"{dias_consecutivos} días naturales consecutivos en verde hasta "
            f"{hoy.isoformat()} (>= {dias_requeridos} requeridos), sin corrección manual "
            "detectada"
        )
    return EvaluacionRacha(
        clase=clase, cumple=cumple, dias_consecutivos=dias_consecutivos, motivo=motivo
    )


# --- 4. La hora de la pasada, derivada del schedule real ---------------------


def _expandir_campo(campo: str, tope: int) -> list[int]:
    """Expande un campo ``cron`` (minuto o hora) a los enteros que denota, en ``[0, tope)``."""
    if campo == "*":
        return list(range(tope))
    if campo.startswith("*/"):
        paso = int(campo[2:])
        return list(range(0, tope, paso))
    if "," in campo:
        return sorted(int(valor) for valor in campo.split(","))
    if "-" in campo:
        inicio_texto, fin_texto = campo.split("-")
        return list(range(int(inicio_texto), int(fin_texto) + 1))
    return [int(campo)]


def _horas_de_disparo(expresion_cron: str) -> list[time]:
    """Minuto y horas de disparo de una expresión ``cron`` de 5 campos.

    Solo interpreta minuto y hora -los tres campos restantes (día del mes,
    mes, día de la semana) no cambian LA HORA del día en que dispara, que es
    lo único que a este módulo le hace falta derivar-. Los dos campos pueden
    llevar cualquier forma real de ``cron`` (``*``, ``*/N``, lista, rango),
    no solo un entero suelto: un ``schedule`` tan frecuente como ``*/30 * * *
    *`` lleva ``*/30`` en el campo de minuto, no en el de hora.
    """
    campos = expresion_cron.split()
    if len(campos) != 5:
        raise ValueError(f"expresión cron no reconocida: {expresion_cron!r}")
    minutos = _expandir_campo(campos[0], 60)
    horas = _expandir_campo(campos[1], 24)
    return [time(hour=hora, minute=minuto) for hora in horas for minuto in minutos]


def hora_recomendada_pasada(workflows_dir: Path = _WORKFLOWS_DIR) -> tuple[time, str]:
    """La hora del día más alejada de cualquier disparo `schedule: cron:` real.

    Deriva, nunca escribe a ojo (criterio de parada (b) de la nota de
    arranque): lee los `schedule: cron:` reales de
    `.github/workflows/*.yml`, calcula el mayor hueco libre entre disparos
    consecutivos (circular: el hueco entre el último y el primero cuenta) y
    devuelve su punto medio -la hora más alejada de CUALQUIER disparo
    periódico, antes o después-.

    Se valida contra
    :func:`sirius_engine.projection_verifier.ventana_tolerancia_etiqueta_maquina`:
    el cierre de la incidencia #265 midió que, con la tolerancia vigente, un
    día solo puede salir verde si nada se movió en las tres horas previas a
    la pasada. Si el hueco más ancho no alcanza para dejar esa ventana
    tranquila antes de la hora propuesta, no hay hora que produzca días
    verdes con el ritmo real del repositorio: se lanza en vez de fingir una
    hora que no serviría (criterio de parada (b)).
    """
    disparos: list[time] = []
    for wf in sorted(workflows_dir.glob("*.yml")):
        doc: Any = yaml.safe_load(wf.read_text(encoding="utf-8"))
        activadores = doc.get("on") if isinstance(doc, dict) else None
        # PyYAML interpreta la clave YAML `on:` sin comillas como el booleano
        # `True`: `.get("on")` falla en silencio si no se contempla también
        # esa forma, y el disparador real de estos workflows lleva `on:` sin
        # comillas.
        if activadores is None and isinstance(doc, dict):
            activadores = doc.get(True)
        if not isinstance(activadores, dict):
            continue
        for entrada in activadores.get("schedule") or []:
            expresion = entrada.get("cron") if isinstance(entrada, dict) else None
            if expresion:
                disparos.extend(_horas_de_disparo(expresion))

    if not disparos:
        raise ValueError(
            f"no encontré ningún `schedule: cron:` en {workflows_dir}: no hay de qué derivar "
            "la hora tranquila"
        )

    minutos_disparo = sorted({disparo.hour * 60 + disparo.minute for disparo in disparos})
    huecos: list[tuple[int, int]] = []
    for indice, inicio in enumerate(minutos_disparo):
        siguiente = minutos_disparo[(indice + 1) % len(minutos_disparo)]
        duracion = (siguiente - inicio) % (24 * 60)
        if duracion == 0:
            duracion = 24 * 60
        huecos.append((duracion, inicio))
    # Empate en duración -disparos regulares, como el `*/6` real, dejan
    # huecos idénticos- se resuelve por el `inicio` MÁS PEQUEÑO: el primer
    # hueco del día, para que el resultado sea predecible y no dependa del
    # orden de iteración.
    duracion_max = max(duracion for duracion, _inicio in huecos)
    inicio_max = min(inicio for duracion, inicio in huecos if duracion == duracion_max)

    tolerancia = ventana_tolerancia_etiqueta_maquina(workflows_dir)
    if (duracion_max // 2) < (tolerancia.total_seconds() // 60):
        raise ValueError(
            f"el mayor hueco libre de disparos periódicos ({duracion_max} min) no deja ni su "
            f"mitad ({duracion_max // 2} min) por delante de la ventana de tolerancia "
            f"({tolerancia}): ninguna hora produciría días verdes con el ritmo real del "
            "repositorio"
        )

    punto_medio = (inicio_max + duracion_max // 2) % (24 * 60)
    hora = time(hour=punto_medio // 60, minute=punto_medio % 60)
    motivo = (
        f"punto medio del mayor hueco libre de disparos periódicos "
        f"({duracion_max} min, tras las "
        f"{time(hour=inicio_max // 60, minute=inicio_max % 60).isoformat(timespec='minutes')} UTC)"
    )
    return hora, motivo
