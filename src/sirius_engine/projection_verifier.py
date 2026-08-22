"""El verificador de proyección (D1a, incidencia #265): compara motor e incidencia.

Compara lo que el motor tiene con lo que su incidencia proyecta, y registra
cada ejecución para que después se pueda comprobar si hubo siete días
continuos en verde (contrato §11.2). **No conmuta nada**: eso es un acto
separado, del propietario, en otro bloque.

El riesgo que este módulo existe para evitar no es que falle: es que **dé
verde sin comprobar nada** y autorice la conmutación con eso. Por eso cada eje
que declara -:data:`EJE_FASE`, :data:`EJE_ESTADO`,
:data:`EJE_FIDELIDAD_PROYECCION`- tiene, en la suite, al menos un caso donde
da ``DIVERGENCIA`` y otro donde da ``COINCIDE``: un eje que solo pudiera decir
que sí no sería un eje, sería ``f(x) == f(x)`` (incidencia #250, nota de
arranque).

Tres ejes, y solo estos:

- **fase** (:data:`EJE_FASE`) y **estado** (:data:`EJE_ESTADO`): a diario.
  Fase es el único que distingue de verdad -ocho de las trece etiquetas del
  vocabulario colapsan a ``ACTIVE``-; estado cubre lo que fase no puede
  (``NEEDS_DECISION``, ``FAILED_SAFELY``, los terminales).
- **fidelidad de la proyección** (:data:`EJE_FIDELIDAD_PROYECCION`): UNA vez,
  al despachar, no a diario. Compara lo que el cuerpo de la incidencia
  declaraba con el ``WorkItem`` que el motor tenía en ese instante. No se
  repite cada día porque nada en el repositorio edita el cuerpo después de
  publicado: compararlo a diario sería constante contra constante.

Fuera de cuatro ventanas -medidas, no inventadas-, una divergencia es un
defecto. Dentro, no se compara, y **se registra que no se comparó**
(``NO_COMPARABLE`` con su motivo): un día sin comparar no es un día en verde.

Determinista y sin red: recibe el ``WorkItem`` del motor y el
``MirroredWorkItem`` del espejo ya leídos -no los lee, no llama a GitHub- y
la ventana de tolerancia de la etiqueta de máquina ya calculada por
:func:`ventana_tolerancia_etiqueta_maquina`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from sirius_engine.domain.mirror import MirroredWorkItem
from sirius_engine.domain.work_item import WorkItem, WorkItemClass, WorkItemPhase, WorkItemState
from sirius_engine.issue_body_parsing import CuerpoDeclarado

#: Nombre de cada eje, tal y como aparece en :class:`VeredictoEje` y en el
#: registro. Cadenas, no un enum: viajan tal cual al log y a los mensajes de
#: prueba, y una prueba (requisito 1) recorre esta misma tupla para exigir
#: que cada uno tenga su caso rojo -si se añade un eje aquí sin su caso, esa
#: prueba lo dice.
EJE_FASE = "fase"
EJE_ESTADO = "estado"
EJE_FIDELIDAD_PROYECCION = "fidelidad_proyeccion"

#: Los ejes que este módulo declara cubrir. Ni uno más -comparar los diez
#: campos del WorkItem que el cuerpo no lleva está fuera de alcance (nota de
#: arranque, pregunta 2)-, ni uno menos.
EJES_DECLARADOS: tuple[str, ...] = (EJE_FASE, EJE_ESTADO, EJE_FIDELIDAD_PROYECCION)

#: Estados para los que el vocabulario de etiquetas `sirius:*` no tiene forma
#: de expresarse (ventana no comparable 2): no hay `sirius:waiting`,
#: `sirius:paused` ni `sirius:cancelled`.
_ESTADOS_SIN_ETIQUETA = frozenset(
    {WorkItemState.WAITING, WorkItemState.PAUSED, WorkItemState.CANCELLED}
)

_WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"


class ResultadoEje(StrEnum):
    """Los tres resultados posibles de comparar un eje. Solo tres."""

    COINCIDE = "coincide"
    DIVERGENCIA = "divergencia"
    NO_COMPARABLE = "no_comparable"


@dataclass(frozen=True, slots=True)
class VeredictoEje:
    """El resultado de comparar un eje, con su motivo cuando no es un simple sí.

    ``motivo`` es ``None`` solo cuando ``resultado`` es ``COINCIDE``: un
    ``NO_COMPARABLE`` sin motivo o una ``DIVERGENCIA`` sin decir en qué
    difieren no serían auditables después.
    """

    eje: str
    resultado: ResultadoEje
    motivo: str | None = None

    def __post_init__(self) -> None:
        if self.resultado is not ResultadoEje.COINCIDE and self.motivo is None:
            raise ValueError(f"eje {self.eje!r}: {self.resultado.value} sin motivo no es auditable")


@dataclass(frozen=True, slots=True)
class ContextoEjesDiarios:
    """Lo que hace falta, más allá de las dos lecturas, para reconocer las ventanas.

    No es una tercera lectura que este módulo haga: es metadato ya conocido
    por quien orquesta la verificación (cuándo se aplicó la etiqueta de
    máquina vigente en la incidencia). ``None`` cuando no se sabe -y en ese
    caso la ventana de residencia (4) simplemente no se aplica: sin ese dato,
    tratar algo como "no comparable" sería una suposición, no una lectura.
    """

    edad_etiqueta_maquina: timedelta | None = None


@dataclass(frozen=True, slots=True)
class LineaRegistro:
    """Una línea del registro: lo que exige el objetivo del bloque.

    Instante, clase, ``work_id`` y el resultado por eje. Sin esto, "siete
    días continuos" (contrato §11.2) no sería comprobable después.
    """

    instante: datetime
    clase: WorkItemClass
    work_id: str
    veredictos: tuple[VeredictoEje, ...]

    @property
    def es_verde(self) -> bool:
        """Verde solo si TODOS los ejes registrados coinciden.

        Un ``NO_COMPARABLE`` no cuenta como verde (requisito 5): la ausencia
        de comparación no es evidencia de que las dos fuentes dijeran lo
        mismo, así que no puede contar como si lo fuera.
        """
        return all(v.resultado is ResultadoEje.COINCIDE for v in self.veredictos)


def ventana_tolerancia_etiqueta_maquina(workflows_dir: Path = _WORKFLOWS_DIR) -> timedelta:
    """La ventana 4, derivada del mayor ``timeout-minutes`` real, nunca escrita a mano.

    Mismo criterio de margen que ``RECON-STUCK-006`` usa para
    ``SIRIUS_STUCK_MINUTES``: el doble del job más largo declarado en
    ``.github/workflows/*.yml``. Un número fijo en el código se queda
    desactualizado en cuanto alguien sube un ``timeout-minutes``, exactamente
    el defecto que ese criterio existe para atrapar (criterio de parada (b)
    de la nota de arranque: no se inventa, se deriva).
    """
    topes: list[int] = []
    for wf in sorted(workflows_dir.glob("*.yml")):
        doc: Any = yaml.safe_load(wf.read_text(encoding="utf-8"))
        for job in (doc.get("jobs") or {}).values():
            if isinstance(job, dict) and isinstance(job.get("timeout-minutes"), int):
                topes.append(job["timeout-minutes"])
    if not topes:
        raise ValueError(
            f"no encontré ningún tope de job en {workflows_dir}: no hay de qué derivar"
        )
    return timedelta(minutes=max(topes) * 2)


def _ventana_residencia_o_fusion(
    motor: WorkItem,
    espejo: MirroredWorkItem,
    contexto: ContextoEjesDiarios,
    ventana_tolerancia: timedelta,
) -> str | None:
    """Ventanas 3 y 4: comunes a fase y estado."""
    if espejo.estado is WorkItemState.DELIVERED and motor.fase is not WorkItemPhase.ENTREGAR:
        # Ventana 3: el ciclo aplica `sirius:completed` desde donde esté; el
        # motor se niega a llamar "entregado" a algo que no pasó por
        # `approve_review`. Es una garantía deliberada, no un defecto.
        return (
            "fusión sin pasar por ready-for-merge: el motor no llama entregado a lo que no revisó"
        )
    if (
        contexto.edad_etiqueta_maquina is not None
        and contexto.edad_etiqueta_maquina < ventana_tolerancia
    ):
        # Ventana 4: el desfase entre que el ciclo mueve una etiqueta y el
        # motor lo observa es real, y se acota con la misma derivación que
        # RECON-STUCK-006.
        return (
            "residencia normal de etiqueta de máquina "
            f"(hace {contexto.edad_etiqueta_maquina}, tolerancia {ventana_tolerancia})"
        )
    return None


def _ventana_no_comparable_estado(
    motor: WorkItem,
    espejo: MirroredWorkItem,
    contexto: ContextoEjesDiarios,
    ventana_tolerancia: timedelta,
) -> str | None:
    if motor.estado in _ESTADOS_SIN_ETIQUETA:
        # Ventana 2.
        return f"motor en {motor.estado.value}: el vocabulario de etiquetas no puede expresarlo"
    if motor.estado is WorkItemState.ACTIVE and espejo.estado is WorkItemState.PLANNED:
        # Ventana 1: el despachador exige ACTIVE y la incidencia recién
        # creada todavía proyecta PLANNED hasta que el ciclo mueve la
        # primera etiqueta (medido en la #186: más de una hora).
        return "despacho reciente: el ciclo aún no ha movido la primera etiqueta desde PLANNED"
    return _ventana_residencia_o_fusion(motor, espejo, contexto, ventana_tolerancia)


def _ventana_no_comparable_fase(
    motor: WorkItem,
    espejo: MirroredWorkItem,
    contexto: ContextoEjesDiarios,
    ventana_tolerancia: timedelta,
) -> str | None:
    # Ni la ventana 1 ni la 2 afectan a fase: `activate()` y `pause()` no
    # tocan `fase`, así que la fase del motor sigue coincidiendo con la que
    # proyecta la última etiqueta de máquina vigente durante esas dos.
    return _ventana_residencia_o_fusion(motor, espejo, contexto, ventana_tolerancia)


def _comparar(
    eje: str, motor: object, espejo: object | None, no_comparable: str | None
) -> VeredictoEje:
    if no_comparable is not None:
        return VeredictoEje(eje=eje, resultado=ResultadoEje.NO_COMPARABLE, motivo=no_comparable)
    if motor == espejo:
        return VeredictoEje(eje=eje, resultado=ResultadoEje.COINCIDE)
    return VeredictoEje(
        eje=eje,
        resultado=ResultadoEje.DIVERGENCIA,
        motivo=f"motor={motor!r} incidencia={espejo!r}",
    )


def verificar_eje_fase(
    *,
    motor: WorkItemPhase,
    espejo: WorkItemPhase | None,
    no_comparable: str | None = None,
) -> VeredictoEje:
    """Compara la fase del motor con la que proyecta la incidencia.

    El eje que de verdad discrimina: de las trece etiquetas del vocabulario,
    ocho colapsan a ``ACTIVE``, así que sin fase el estado no distingue
    implementar de comprobar de revisar de reparar de entregar.
    """
    return _comparar(EJE_FASE, motor, espejo, no_comparable)


def verificar_eje_estado(
    *,
    motor: WorkItemState,
    espejo: WorkItemState | None,
    no_comparable: str | None = None,
) -> VeredictoEje:
    """Compara el estado del motor con el que proyecta la incidencia.

    Cubre lo que fase no puede: los estados sin fase
    (``NEEDS_DECISION``, ``FAILED_SAFELY``) y los terminales.
    """
    return _comparar(EJE_ESTADO, motor, espejo, no_comparable)


def verificar_fidelidad_proyeccion(
    *, despachado: WorkItem, declarado: CuerpoDeclarado
) -> VeredictoEje:
    """Eje 3: ¿el cuerpo publicado declara lo mismo que el motor despachó?

    UNA vez, no a diario (nada edita el cuerpo después de publicado). Un
    campo declarado como ``None`` -sección ausente o vacía- no se compara:
    "no se pudo leer" no es "divergía". Si NINGÚN campo comparable se pudo
    leer, no hay nada que decir que sí: es ``NO_COMPARABLE``, no ``COINCIDE``.
    """
    campos: tuple[tuple[str, str | None, str], ...] = (
        ("work_id", declarado.work_id, despachado.work_id),
        ("objetivo", declarado.objetivo, despachado.objetivo),
        ("alcance permitido", declarado.entregable, despachado.entregable),
    )
    leidos = [c for c in campos if c[1] is not None]
    if not leidos:
        return VeredictoEje(
            eje=EJE_FIDELIDAD_PROYECCION,
            resultado=ResultadoEje.NO_COMPARABLE,
            motivo=(
                "el cuerpo no declara ninguno de los campos comparables (work_id/objetivo/alcance)"
            ),
        )
    divergencias = [
        f"{nombre}: motor={motor_valor!r} cuerpo={cuerpo_valor!r}"
        for nombre, cuerpo_valor, motor_valor in leidos
        if cuerpo_valor != motor_valor
    ]
    if divergencias:
        return VeredictoEje(
            eje=EJE_FIDELIDAD_PROYECCION,
            resultado=ResultadoEje.DIVERGENCIA,
            motivo="; ".join(divergencias),
        )
    return VeredictoEje(eje=EJE_FIDELIDAD_PROYECCION, resultado=ResultadoEje.COINCIDE)


def verificar_dia(
    *,
    motor: WorkItem,
    espejo: MirroredWorkItem,
    contexto: ContextoEjesDiarios,
    ventana_tolerancia: timedelta,
    instante: datetime,
) -> LineaRegistro:
    """La comparación diaria: ejes fase y estado, con sus ventanas aplicadas."""
    no_comparable_fase = _ventana_no_comparable_fase(motor, espejo, contexto, ventana_tolerancia)
    no_comparable_estado = _ventana_no_comparable_estado(
        motor, espejo, contexto, ventana_tolerancia
    )
    return LineaRegistro(
        instante=instante,
        clase=motor.clase,
        work_id=motor.work_id,
        veredictos=(
            verificar_eje_fase(
                motor=motor.fase, espejo=espejo.fase, no_comparable=no_comparable_fase
            ),
            verificar_eje_estado(
                motor=motor.estado, espejo=espejo.estado, no_comparable=no_comparable_estado
            ),
        ),
    )


def verificar_despacho(
    *, despachado: WorkItem, declarado: CuerpoDeclarado, instante: datetime
) -> LineaRegistro:
    """La comparación de fidelidad, una vez, al despachar."""
    return LineaRegistro(
        instante=instante,
        clase=despachado.clase,
        work_id=despachado.work_id,
        veredictos=(verificar_fidelidad_proyeccion(despachado=despachado, declarado=declarado),),
    )


def formatear_linea(linea: LineaRegistro) -> str:
    """Serializa una línea del registro a JSON determinista (misma entrada, mismo texto)."""
    return json.dumps(
        {
            "instante": linea.instante.isoformat(),
            "clase": linea.clase.value,
            "work_id": linea.work_id,
            "ejes": [
                {"eje": v.eje, "resultado": v.resultado.value, "motivo": v.motivo}
                for v in linea.veredictos
            ],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
