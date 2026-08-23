"""La reversión automática de la autoridad de una clase (D1c, incidencia #276, contrato §11.4).

D1a (:mod:`sirius_engine.projection_verifier`) sabe comparar motor e
incidencia y decir, por eje, si coinciden, divergen o no fue comparable. D1b
(:mod:`sirius_engine.seven_day_streak`) convierte esa comparación puntual en
una racha. Ninguno de los dos conmuta nada -es deliberado, y sigue siéndolo
aquí para la mitad "hacia delante": este módulo **no conmuta clases hacia
el motor**, eso es el contador de §11.2 y no tiene datos reales que contar
todavía (incidencia #270).

Lo que este módulo sí hace es la otra mitad, la que el contrato permite
ejecutar sin esperar a que la primera tenga datos: **la salida de
emergencia** (§11.4). Para una clase ya conmutada (autoridad ``MOTOR`` en
:mod:`sirius_engine.domain.authority`), una sola divergencia real -nunca un
``NO_COMPARABLE``, que solo significa "no se pudo mirar"- basta para
devolverla a la vía GitHub: "no se espera a un patrón ni a una segunda
ocurrencia" (contrato §11.4, literal).

Por qué un ``NO_COMPARABLE`` no puede disparar esto: mientras la etiqueta de
máquina sea reciente, la ventana 4 de D1a declara ``NO_COMPARABLE`` cualquier
comparación -medido en el cierre de la #265-, así que contarlo como
divergencia dispararía la reversión sobre el caso MÁS FRECUENTE, no sobre
una excepción. Es precisamente el riesgo que la nota de arranque de esta
incidencia señaló como el primero de los dos.

La idempotencia (requisito 7) no se consigue comparando texto: se consigue
porque revertir es un cambio de estado. Una vez que la entrada de reversión
se añade al registro, :func:`~sirius_engine.domain.authority.autoridad_de_clase`
ya no devuelve ``MOTOR`` para esa clase -vuelve a ``INCIDENCIA``-, así que una
segunda pasada sobre la misma divergencia encuentra "no aplica" en
:func:`evaluar_reversion` antes de llegar a construir nada. Ninguna llamada
de este módulo re-cuenta ni re-avisa una reversión que ya ocurrió.

Determinista y sin red (requisito 9): recibe el registro de conmutaciones y
las líneas del verificador ya leídos -no los busca, no llama a GitHub-. Leer
y escribir el fichero del registro (:func:`leer_registro_conmutaciones`,
:func:`anadir_entradas`) es la única E/S de este módulo, sobre una ruta que
el llamador decide; ninguna de las dos funciones de decisión
(:func:`evaluar_reversion`) toca disco.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sirius_engine.domain.authority import (
    Autoridad,
    EntradaConmutacion,
    autoridad_de_clase,
    formatear_entrada_conmutacion,
    parsear_entrada_conmutacion,
)
from sirius_engine.domain.work_item import WorkItemClass
from sirius_engine.projection_verifier import LineaRegistro, ResultadoEje

# --- El registro de conmutaciones: mismo formato append-only que la racha ---


def leer_registro_conmutaciones(ruta: Path) -> tuple[EntradaConmutacion, ...]:
    """Todas las entradas del registro de conmutaciones, en el orden en que se escribieron.

    Un registro que no existe todavía se lee como vacío -sin conmutación
    previa, toda clase sigue con la autoridad de la tabla estática- igual
    que :func:`sirius_engine.seven_day_streak.leer_registro`.
    """
    if not ruta.exists():
        return ()
    lineas = [linea.strip() for linea in ruta.read_text(encoding="utf-8").splitlines()]
    return tuple(parsear_entrada_conmutacion(linea) for linea in lineas if linea)


def anadir_entradas(ruta: Path, entradas: Sequence[EntradaConmutacion]) -> int:
    """Añade ``entradas`` nuevas al final del registro. Devuelve cuántas se escribieron de verdad.

    Determinista y solo-crece (requisito 8): nunca reescribe ni reordena lo
    que ya había. Una entrada cuyo texto exacto ya está en el fichero no se
    repite -mismo criterio que
    :func:`sirius_engine.seven_day_streak.anadir_lineas`, sobre
    :func:`~sirius_engine.domain.authority.formatear_entrada_conmutacion` en
    vez de ``formatear_linea``.
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
    for entrada in entradas:
        texto = formatear_entrada_conmutacion(entrada)
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


# --- La decisión: una divergencia real, sobre una clase ya conmutada -------


@dataclass(frozen=True, slots=True)
class ResultadoReversion:
    """El veredicto de este módulo para una clase: revierte, o no aplica, y por qué.

    ``entrada``/``aviso`` son ``None`` exactamente cuando ``revierte`` es
    ``False`` -"no aplica" tiene que ser distinguible de "revertí" sin mirar
    el motivo en prosa (requisito 6).
    """

    clase: WorkItemClass
    revierte: bool
    motivo: str
    entrada: EntradaConmutacion | None
    aviso: str | None


def _instante_ultima_conmutacion_a_motor(
    clase: WorkItemClass, registro_conmutaciones: Sequence[EntradaConmutacion]
) -> datetime | None:
    """El instante desde el que la clase es autoridad del motor, si lo es.

    Solo las divergencias registradas DESPUÉS de esa conmutación cuentan
    para la reversión: una divergencia de cuando la incidencia todavía era
    la autoridad no es un defecto del motor, es historia de antes de que
    hubiera algo que vigilar.
    """
    entradas = tuple(
        entrada
        for entrada in registro_conmutaciones
        if entrada.clase is clase and entrada.autoridad is Autoridad.MOTOR
    )
    if not entradas:
        return None
    return max(entrada.instante for entrada in entradas)


def formatear_aviso_reversion(entrada: EntradaConmutacion) -> str:
    """El anuncio del contrato §11.4, en español y compatible con GitHub Mobile (§7).

    Texto plano, sin marcado que dependa de renderizado de escritorio: el
    mismo criterio que ya exige §7 para las notificaciones de estado. Este
    módulo produce el texto -determinista, sin red (requisito 9)-; publicarlo
    en el canal real es cableado (``.github/**``) y queda fuera de este
    bloque, igual que la hora del cron quedó fuera de D1b.
    """
    return (
        f"Reversión automática de autoridad — clase {entrada.clase.value} "
        f"(contrato §11.4)\n"
        f"La incidencia vuelve a ser la fuente de verdad para {entrada.clase.value}: "
        f"{entrada.motivo}\n"
        f"Fecha: {entrada.instante.isoformat()}\n"
        "El motor vuelve a ser espejo no autoritativo; el contador de siete días "
        "(contrato §11.2) empieza de nuevo desde cero."
    )


def evaluar_reversion(
    *,
    clase: WorkItemClass,
    registro_conmutaciones: Sequence[EntradaConmutacion],
    lineas_verificador: Sequence[LineaRegistro],
    instante: datetime,
) -> ResultadoReversion:
    """Decide si ``clase`` revierte a autoridad ``INCIDENCIA``, sin escribir nada.

    Solo se dispara si, A LA VEZ:

    1. ``clase`` es hoy autoridad ``MOTOR`` según
       :func:`~sirius_engine.domain.authority.autoridad_de_clase` sobre
       ``registro_conmutaciones`` -una clase que nunca conmutó, o que ya
       revirtió, no tiene autoridad del motor de la que salir (requisito 6).
    2. Existe, entre las líneas de ``lineas_verificador`` de esa clase
       registradas DESPUÉS de la conmutación, al menos un eje en
       ``DIVERGENCIA`` -nunca ``NO_COMPARABLE`` (requisito 2, criterio de
       parada (a) de la nota de arranque): una ausencia de comparación no es
       evidencia de que el motor se equivocara.

    Con las dos, revierte a la primera divergencia encontrada (por
    ``instante``, requisito 5: "a la primera, no a la segunda"), y
    construye la entrada fechada y el aviso -sin escribir ninguno de los
    dos: eso es cosa de quien orqueste esta llamada con
    :func:`anadir_entradas`.
    """
    if autoridad_de_clase(clase, registro=registro_conmutaciones) is not Autoridad.MOTOR:
        return ResultadoReversion(
            clase=clase,
            revierte=False,
            motivo=(
                f"{clase.value} no es hoy autoridad del motor: no hay conmutación de la que "
                "revertir"
            ),
            entrada=None,
            aviso=None,
        )

    desde = _instante_ultima_conmutacion_a_motor(clase, registro_conmutaciones)
    lineas_relevantes = tuple(
        linea
        for linea in lineas_verificador
        if linea.clase is clase and (desde is None or linea.instante > desde)
    )

    divergencias = tuple(
        (linea, veredicto)
        for linea in lineas_relevantes
        for veredicto in linea.veredictos
        if veredicto.resultado is ResultadoEje.DIVERGENCIA
    )
    if not divergencias:
        return ResultadoReversion(
            clase=clase,
            revierte=False,
            motivo=(
                f"{clase.value}: ninguna divergencia registrada desde la conmutación "
                f"({len(lineas_relevantes)} línea(s) revisada(s)); nada que revertir"
            ),
            entrada=None,
            aviso=None,
        )

    linea, veredicto = min(divergencias, key=lambda par: par[0].instante)
    motivo = (
        f"divergencia en el eje {veredicto.eje} ({veredicto.motivo}) del work_id "
        f"{linea.work_id!r} registrada el {linea.instante.isoformat()}; contrato §11.4: no se "
        "espera a una segunda ocurrencia"
    )
    entrada = EntradaConmutacion(
        instante=instante, clase=clase, autoridad=Autoridad.INCIDENCIA, motivo=motivo
    )
    return ResultadoReversion(
        clase=clase,
        revierte=True,
        motivo=motivo,
        entrada=entrada,
        aviso=formatear_aviso_reversion(entrada),
    )
