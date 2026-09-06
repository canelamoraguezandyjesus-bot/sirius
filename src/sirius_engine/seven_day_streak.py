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
libre, sin contar los disparos del propio workflow del contador, que es quien
consume esa hora (ADR-144)-, y la valida contra la ventana de tolerancia de
etiqueta de máquina
(:func:`sirius_engine.projection_verifier.ventana_tolerancia_etiqueta_maquina`).
El cierre de la incidencia #265 midió que, con la tolerancia vigente, un día
solo puede salir verde si nada se movió en las tres horas previas a la
pasada: elegir la hora a ojo desoiría esa medición.

Y una quinta, que es la otra mitad de esa cuarta (ADR-151): derivar la hora
tranquila no sirve de nada si la pasada no llega a ella.
:func:`medir_entrega_de_la_pasada` mide con cuánto retraso llegó de verdad
-`ahora` contra la hora derivada- y si su ventana previa estuvo tranquila
según los runs reales de Actions; :func:`declarar_entrega_de_la_pasada` lo pone
en palabras para el ``motivo``. **Mide y declara, no juzga**: ningún veredicto
de ningún eje cambia por esto.

Determinista y sin red: todo lo que sigue trabaja sobre lo que ya se leyó -el
registro, el diario de eventos, los ficheros YAML del propio repositorio-,
igual que exige :mod:`sirius_engine.projection_verifier`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml

from sirius_engine.domain.events import AggregateType, Event
from sirius_engine.domain.work_item import WorkItemClass
from sirius_engine.ports.github_mirror import LecturaEstado, LecturaRunsEnVentana
from sirius_engine.projection_verifier import (
    EJE_ESTADO,
    EJE_FASE,
    EntregaDeLaPasada,
    LineaRegistro,
    ResultadoEje,
    VeredictoEje,
    formatear_linea,
    ventana_tolerancia_etiqueta_maquina,
)

#: Cuántos días naturales consecutivos en verde exige el contrato §11.2.
DIAS_REQUERIDOS = 7

_WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"

#: El workflow que CONSUME la hora que :func:`hora_recomendada_pasada` deriva
#: -la pasada diaria de ``sirius-racha``-, y por eso el único cuyos disparos
#: esa función NO cuenta (ADR-144). La exclusión es NOMBRADA a propósito: no
#: adivina quién consume la hora mirando lo que cada workflow ejecuta, así que
#: se lee y se audita de un vistazo. El precio, declarado: si este fichero se
#: renombra, sus disparos vuelven a contarse -degrada al comportamiento
#: anterior, nunca a un error-.
NOMBRE_DEL_WORKFLOW_DEL_CONTADOR = "contador-siete-dias.yml"


# --- 1. El registro: JSONL versionado, solo crece ---------------------------


def _parsear_entrega(datos: dict[str, Any]) -> EntregaDeLaPasada | None:
    """La ``entrega`` de una línea, o ``None`` si esa línea no la trae.

    El campo es POSTERIOR al registro (ADR-151) y el registro solo crece: las
    líneas escritas antes no lo llevan y se siguen leyendo exactamente igual.
    Ausente no es "cero minutos de retraso y ventana tranquila" -eso sería
    inventar una medida que nadie tomó-: es "no medido", y por eso ``None``.
    """
    crudo = datos.get("entrega")
    if crudo is None:
        return None
    return EntregaDeLaPasada(
        retraso_min=int(crudo["retraso_min"]),
        runs_en_ventana=tuple(str(run) for run in crudo["runs_en_ventana"]),
        lectura_de_runs=LecturaEstado(crudo["lectura_de_runs"]),
    )


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
        entrega=_parsear_entrega(datos),
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
    lecturas_caidas_hoy: Sequence[str] = (),
    entrega_hoy: str | None = None,
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

    ``lecturas_caidas_hoy`` son descripciones, ya formadas por quien invoca,
    de qué no se pudo leer en la PASADA que llama a esta función -esta
    función solo ve el registro histórico (``lineas``) y el diario de
    eventos (``eventos``), ninguno de los cuales guarda una lectura caída
    (ADR-036: una lectura caída no deja línea, así que no hay nada de lo que
    derivarla aquí). El contrato §11.2 clasifica un fallo de un servicio
    externo como avería operativa -no como discrepancia, que es lo único que
    la condición mide- así que no rompe la racha (ADR-084); pero se declara
    en ``motivo`` para que un ``CUMPLE`` nunca calle que esta pasada tuvo
    lecturas caídas.

    ``entrega_hoy`` es del mismo molde: una descripción ya formada por quien
    invoca -:func:`declarar_entrega_de_la_pasada`- de CÓMO llegó esta pasada
    (con cuánto retraso sobre su hora programada, y si su ventana previa estuvo
    tranquila). Tampoco toca el conteo: el retraso de entrega no es una
    discrepancia entre el motor y su incidencia, que es lo único que la
    condición del §11.2 mide. Se anexa al ``motivo`` por la misma razón que las
    lecturas caídas: un ``CUMPLE`` que calle que la pasada llegó cinco horas
    tarde a una ventana sucia afirma más de lo que el dato sostiene (ADR-151).
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
    if lecturas_caidas_hoy:
        motivo = (
            f"{motivo} — aviso: esta pasada no pudo leer "
            f"{', '.join(lecturas_caidas_hoy)} (no interrumpe el contador, contrato §11.2)"
        )
    if entrega_hoy:
        motivo = f"{motivo} — entrega: {entrega_hoy}"
    return EvaluacionRacha(
        clase=clase, cumple=cumple, dias_consecutivos=dias_consecutivos, motivo=motivo
    )


# --- 4. La hora de la pasada, derivada del schedule real ---------------------


#: Las cinco formas -y no hay más- del dialecto ``cron`` de este repositorio
#: para los campos minuto y hora (ADR-143). Se enuncia una sola vez, aquí,
#: porque va literalmente en cada mensaje de rechazo: quien lo lea sabrá qué
#: podía haber escrito sin ir a buscar la documentación.
_DIALECTO_CRON = (
    "el dialecto de este repositorio admite '*', '*/N', un entero suelto, un rango 'a-b' "
    "y listas por comas cuyos elementos son enteros o rangos"
)

_ENTERO_CRON = re.compile(r"[0-9]+")


def _rechazo_de_campo(*, nombre: str, campo: str, forma: str, motivo: str) -> ValueError:
    """El rechazo RUIDOSO del dialecto: dice el campo, la forma y qué se admitía.

    Existe para que ningún camino de :func:`_expandir_campo` acabe en un
    ``int()`` pelado. Los dos rojos de la noche del 04/05-09-2026 (ADR-139)
    llegaron como ``invalid literal for int() with base 10: '4-23'``, un
    mensaje que no dice ni qué campo se estaba leyendo ni qué forma sobraba.
    """
    detalle = f"{forma!r}" if forma == campo else f"{forma!r} (dentro de {campo!r})"
    return ValueError(f"campo {nombre} de cron: {motivo} {detalle}; {_DIALECTO_CRON}")


def _entero_de_campo(texto: str, *, nombre: str, campo: str, tope: int) -> int:
    """Un entero del dialecto: solo dígitos, y dentro de ``[0, tope)``."""
    if not _ENTERO_CRON.fullmatch(texto):
        raise _rechazo_de_campo(nombre=nombre, campo=campo, forma=texto, motivo="forma no admitida")
    valor = int(texto)
    if valor >= tope:
        raise _rechazo_de_campo(
            nombre=nombre,
            campo=campo,
            forma=texto,
            motivo=f"valor fuera de [0, {tope}) en",
        )
    return valor


def _expandir_elemento(elemento: str, tope: int, nombre: str, campo: str) -> list[int]:
    """Un elemento del dialecto que puede ir suelto o dentro de una lista: entero o rango."""
    if "-" in elemento:
        partes = elemento.split("-")
        if len(partes) != 2:
            raise _rechazo_de_campo(
                nombre=nombre, campo=campo, forma=elemento, motivo="rango mal formado"
            )
        inicio = _entero_de_campo(partes[0], nombre=nombre, campo=campo, tope=tope)
        fin = _entero_de_campo(partes[1], nombre=nombre, campo=campo, tope=tope)
        if inicio > fin:
            raise _rechazo_de_campo(
                nombre=nombre, campo=campo, forma=elemento, motivo="rango descendente"
            )
        return list(range(inicio, fin + 1))
    return [_entero_de_campo(elemento, nombre=nombre, campo=campo, tope=tope)]


def _expandir_campo(campo: str, tope: int, nombre: str) -> list[int]:
    """Expande un campo ``cron`` (minuto u hora) a los enteros que denota, en ``[0, tope)``.

    **Este docstring es la definición del dialecto** (ADR-143), el único sitio
    donde se enuncia. Hay DOS lectores de ``cron`` en el repositorio -este y el
    del guardián-oráculo de `tests/engine/test_seven_day_streak.py`, que
    conserva su independencia («YAML aparte») y por eso no importa este código-,
    y los dos implementan estas cinco formas ÍNTEGRAS, ni una más:

    - ``*``: todos los valores de ``[0, tope)``.
    - ``*/N``: desde 0, de N en N, con ``1 <= N <= tope``.
    - un entero suelto, dentro de ``[0, tope)``.
    - un rango ``a-b``, con ``a <= b`` y ambos dentro de ``[0, tope)``.
    - una lista por comas cuyos elementos son enteros o rangos: la forma
      ``0,4-23``, que GitHub admite y que quemó los rojos 2 y 3 de ADR-139.

    Fuera del dialecto -el paso sobre rango ``8-18/2``, los nombres (``JAN``,
    ``MON``), ``?``, ``L``, ``#``, ``W``, un ``*`` dentro de una lista, un valor
    fuera de tope, un rango descendente-: rechazo RUIDOSO
    (:func:`_rechazo_de_campo`), que nombra el campo y la forma no admitida.
    Nunca un ``int()`` pelado.

    Que los dos lectores no puedan volver a divergir en silencio no lo
    garantiza este docstring, sino
    ``test_los_dos_lectores_de_cron_expanden_y_rechazan_igual``: una tabla de
    expresiones sobre la que ambos deben expandir igual y rechazar lo mismo.
    """
    if campo == "*":
        return list(range(tope))
    if campo.startswith("*/"):
        paso_texto = campo[2:]
        if not _ENTERO_CRON.fullmatch(paso_texto) or not 1 <= int(paso_texto) <= tope:
            raise _rechazo_de_campo(
                nombre=nombre,
                campo=campo,
                forma=campo,
                motivo=f"paso no admitido (se espera un entero de 1 a {tope}) en",
            )
        return list(range(0, tope, int(paso_texto)))
    if "," in campo:
        valores: set[int] = set()
        for elemento in campo.split(","):
            valores.update(_expandir_elemento(elemento, tope, nombre, campo))
        return sorted(valores)
    return _expandir_elemento(campo, tope, nombre, campo)


def _horas_de_disparo(expresion_cron: str) -> list[time]:
    """Minuto y horas de disparo de una expresión ``cron`` de 5 campos.

    Solo interpreta minuto y hora -los tres campos restantes (día del mes,
    mes, día de la semana) no cambian LA HORA del día en que dispara, que es
    lo único que a este módulo le hace falta derivar-. Los dos campos llevan
    cualquier forma del dialecto de :func:`_expandir_campo` (``*``, ``*/N``,
    entero, rango y listas de enteros o rangos), no solo un entero suelto: un
    ``schedule`` tan frecuente como ``*/30 * * * *`` lleva ``*/30`` en el
    campo de minuto, no en el de hora.
    """
    campos = expresion_cron.split()
    if len(campos) != 5:
        raise ValueError(f"expresión cron no reconocida: {expresion_cron!r}")
    minutos = _expandir_campo(campos[0], 60, "minuto")
    horas = _expandir_campo(campos[1], 24, "hora")
    return [time(hour=hora, minute=minuto) for hora in horas for minuto in minutos]


def _expresiones_cron(workflow: Path) -> list[str]:
    """Las expresiones `schedule: cron:` escritas en un fichero de workflow.

    Sin interpretarlas: devuelve el texto tal cual, para que quien llame decida
    si las cuenta o solo mira si las hay.
    """
    doc: Any = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    activadores = doc.get("on") if isinstance(doc, dict) else None
    # PyYAML interpreta la clave YAML `on:` sin comillas como el booleano
    # `True`: `.get("on")` falla en silencio si no se contempla también esa
    # forma, y el disparador real de estos workflows lleva `on:` sin comillas.
    if activadores is None and isinstance(doc, dict):
        activadores = doc.get(True)
    if not isinstance(activadores, dict):
        return []
    expresiones: list[str] = []
    for entrada in activadores.get("schedule") or []:
        expresion = entrada.get("cron") if isinstance(entrada, dict) else None
        if expresion:
            expresiones.append(expresion)
    return expresiones


def hora_recomendada_pasada(workflows_dir: Path = _WORKFLOWS_DIR) -> tuple[time, str]:
    """La hora del día más alejada de cualquier disparo `schedule: cron:` real.

    Deriva, nunca escribe a ojo (criterio de parada (b) de la nota de
    arranque): lee los `schedule: cron:` reales de
    `.github/workflows/*.yml`, calcula el mayor hueco libre entre disparos
    consecutivos (circular: el hueco entre el último y el primero cuenta) y
    devuelve su punto medio -la hora más alejada de CUALQUIER disparo
    periódico, antes o después-.

    **Con una excepción nombrada: el propio contador** (ADR-144). Los disparos
    de :data:`NOMBRE_DEL_WORKFLOW_DEL_CONTADOR` -el workflow que ejecuta la
    pasada para la que se deriva esta hora- no cuentan. La pregunta que esta
    función responde es «¿cuál es la hora más tranquila para la PASADA del
    contador?», y la propia pasada no puede estorbarse a sí misma: es la misma
    propiedad que ``tests/automation/test_contador_de_siete_dias.py`` ya
    aplicaba por su lado («un workflow no se estorba a sí mismo, y contarlo
    daría siempre cero») y que aquí faltaba. Sin ella, cablear la hora derivada
    la invalidaba en el acto: al programar 03:24 UTC -punto medio de un hueco
    de 345 min, derivado el 25-08-2026, cuando el workflow aún no existía- su
    propio disparo partió ese hueco y la derivación saltó al siguiente hueco de
    345, las 09:24 (medido en ADR-143). Solo se restan sus DISPAROS: su
    ``timeout-minutes`` sigue contando para la ventana de tolerancia, porque un
    job largo del contador retrasa etiquetas igual que cualquier otro.

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
    # Si lo que se saltó tenía `cron`, el mensaje de «no hay nada que contar»
    # tiene que decirlo: lo que ese directorio contenga puede no ser vacío
    # -puede ser justo lo que esta función excluye a propósito-. La condición
    # es que el fichero excluido TRAIGA disparos, no que exista: un
    # `contador-siete-dias.yml` con solo `workflow_dispatch` no esconde ningún
    # `schedule: cron:`, y culpar a la exclusión mandaría a buscar un
    # disparador que nadie escribió.
    se_excluyo_algun_cron_del_contador = False
    for wf in sorted(workflows_dir.glob("*.yml")):
        expresiones = _expresiones_cron(wf)
        if wf.name == NOMBRE_DEL_WORKFLOW_DEL_CONTADOR:
            # Se lee para saber SI traía `cron`, nunca para contarlo: sus
            # disparos no entran en `disparos` (ADR-144).
            se_excluyo_algun_cron_del_contador = bool(expresiones)
            continue
        for expresion in expresiones:
            disparos.extend(_horas_de_disparo(expresion))

    if not disparos:
        if se_excluyo_algun_cron_del_contador:
            # Decir aquí «no encontré ningún `schedule: cron:` en el
            # directorio» sería falso: puede haberlo, en el fichero que esta
            # función acaba de saltarse. La causa se nombra para que quien lea
            # el error no busque un disparador que sí está escrito.
            raise ValueError(
                f"no quedó ningún `schedule: cron:` que contar en {workflows_dir}: se "
                f"excluyeron los disparos de {NOMBRE_DEL_WORKFLOW_DEL_CONTADOR}, que esta "
                "función no cuenta a propósito (ADR-144: la pasada del contador no se "
                "estorba a sí misma). No hay de qué derivar la hora tranquila"
            )
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


# --- 5. La entrega de la pasada: con cuánto retraso llegó, y a qué ventana ---


def _minutos_de_desfase(*, ahora: datetime, hora_programada: time) -> int:
    """Minutos entre la hora programada de HOY y ``ahora``. Negativo = llegó antes.

    El día natural sale de ``ahora``, no de un calendario aparte: la hora
    programada es diaria (``24 3 * * *``), así que la del día de la pasada es
    la única con la que tiene sentido compararla.
    """
    programada = datetime.combine(ahora.date(), hora_programada, tzinfo=ahora.tzinfo)
    return int((ahora - programada).total_seconds() // 60)


def medir_entrega_de_la_pasada(
    *,
    ahora: datetime,
    hora_programada: time,
    lectura_runs: LecturaRunsEnVentana,
) -> EntregaDeLaPasada:
    """Qué retraso trajo esta pasada y con qué se cruzó en su ventana previa.

    Dos medidas, ninguna de ellas un veredicto (ADR-151):

    1. **El retraso**, contra la hora que :func:`hora_recomendada_pasada`
       deriva -la misma que el guardián de ADR-144 mantiene igual al ``cron``
       cableado-. Nunca negativo: una pasada lanzada a mano antes de su hora no
       llegó tarde, y decir que llegó con "-45 minutos de retraso" sería un
       número con el signo haciendo de explicación.
    2. **La higiene de la ventana previa**, según ``lectura_runs``: los runs
       ajenos al propio contador que empezaron o terminaron en ella. Los del
       contador no cuentan, por el mismo criterio NOMBRADO que ADR-144
       (:data:`NOMBRE_DEL_WORKFLOW_DEL_CONTADOR`): una pasada no se estorba a
       sí misma, y contarla daría siempre "ventana sucia".

    Una lectura caída **no** produce "ventana tranquila": produce
    ``lectura_de_runs = NO_DISPONIBLE`` con la lista vacía, que es un valor
    distinto y se declara como tal.
    """
    retraso = max(0, _minutos_de_desfase(ahora=ahora, hora_programada=hora_programada))
    if lectura_runs.estado is not LecturaEstado.OK or lectura_runs.runs is None:
        return EntregaDeLaPasada(
            retraso_min=retraso,
            runs_en_ventana=(),
            lectura_de_runs=LecturaEstado.NO_DISPONIBLE,
        )
    ajenos = tuple(
        f"{run.workflow}#{run.run_id}"
        for run in lectura_runs.runs
        if run.workflow != NOMBRE_DEL_WORKFLOW_DEL_CONTADOR
    )
    return EntregaDeLaPasada(
        retraso_min=retraso, runs_en_ventana=ajenos, lectura_de_runs=LecturaEstado.OK
    )


def declarar_entrega_de_la_pasada(
    entrega: EntregaDeLaPasada, *, ahora: datetime, hora_programada: time
) -> str:
    """La medida de :func:`medir_entrega_de_la_pasada`, en palabras para el ``motivo``.

    Se separa de la medida porque el texto dice una cosa que el dato no guarda:
    una pasada lanzada a mano ANTES de su hora tiene ``retraso_min = 0`` igual
    que una puntual, y son dos cosas distintas. El texto lo distingue mirando el
    desfase con signo; el registro guarda la medida, que es lo que no envejece.
    """
    programada = hora_programada.isoformat(timespec="minutes")
    desfase = _minutos_de_desfase(ahora=ahora, hora_programada=hora_programada)
    if entrega.retraso_min > 0:
        cuando = (
            f"pasada entregada con {entrega.retraso_min} min de retraso sobre las "
            f"{programada} UTC programadas"
        )
    elif desfase < 0:
        cuando = (
            f"pasada entregada {-desfase} min ANTES de las {programada} UTC programadas "
            "(fuera de hora, no es un retraso)"
        )
    else:
        cuando = f"pasada entregada a su hora programada ({programada} UTC)"

    if entrega.lectura_de_runs is not LecturaEstado.OK:
        ventana = "no se pudieron leer los runs de la ventana previa"
    elif entrega.runs_en_ventana:
        ventana = (
            f"ventana previa NO tranquila: {len(entrega.runs_en_ventana)} runs "
            f"({', '.join(entrega.runs_en_ventana)})"
        )
    else:
        ventana = "ventana previa tranquila: 0 runs"
    return f"{cuando}; {ventana}"
