"""Los cinco participantes, ejecutables tras una sola interfaz. **No mide.**

Cuatro candidatos pasan por el motor común; el control es Sirius 0.1 y no tiene
motor. Este módulo los pone tras la misma llamada —``responder(caso)``— sin
disimular la diferencia: lo que `T0` no tiene sigue faltando en lo que devuelve,
y falta **declarado**.

POR QUÉ EL CONTROL NO SE ENVUELVE HASTA PARECER UN CANDIDATO
============================================================

Rellenar los huecos de `T0` —darle etapas, puertas, paradas y explicación—
convertiría al control de falsación en un quinto candidato, y el benchmark
mediría el adaptador. `T0` responde con lo que produce y declara lo que
descarta; sus incumplimientos salen como **resultado**, no como excepción.

Concretamente: `T0` no recorre `E0-E5`, de modo que su conformidad de etapa no
es «verdadera por defecto» ni «falsa por castigo». Es **falsa con su razón
medida**: `rank()` recorre todo el canon vigente para responder, y eso es el
barrido que `RF-14` prohíbe, observado por un contador que no filtra ni
reordena.

LO QUE CUESTA CADA SEÑAL, Y CUÁNDO SE PAGA
==========================================

`ADR002-B` y `ADR002-D` necesitan su sidecar vectorial construido; `ADR002-C` y
`ADR002-D` leen el plano relacional de la proyección. Todo eso se prepara
**antes** de responder y fuera de cualquier ventana cronometrada, igual para
quien lo necesita. Cobrar la construcción del índice dentro de la medida
mediría la preparación, no la recuperación.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Final, Protocol

from experiments.adr002.candidates.adr002_a import candidate as ca
from experiments.adr002.candidates.adr002_b import candidate as cb
from experiments.adr002.candidates.adr002_b import vectores
from experiments.adr002.candidates.adr002_c import candidate as cc
from experiments.adr002.candidates.adr002_d import candidate as cd
from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.contracts import Peticion, Polaridad
from experiments.adr002.candidates.common.port import PuertoSqlite
from experiments.adr002.candidates.t0_control import conformance as t0
from experiments.adr002.projection.contracts import Plano, ProyeccionExperimental
from experiments.adr002.projection.plane import PlanoReservado
from experiments.adr002.round.metrics import ELEMENTOS_DE_RF_28

#: Nombre del sidecar vectorial dentro del directorio de trabajo del
#: participante. Cada uno tiene el suyo: compartirlo acoplaría dos medidas.
SIDECAR: Final = "vectores.sqlite3"

#: Razón por la que el control no puede tener conformidad de etapa. No es una
#: penalización: es lo que la ficha de `T0` ya declara y el contador confirma.
RAZON_DEL_CONTROL: Final = (
    "T0 no implementa E0-E5: rank() recorre todo el canon vigente para responder, "
    "que es el barrido completo que RF-14 prohibe (incumplimiento declarado en su ficha)"
)


@dataclass(frozen=True, slots=True)
class Observacion:
    """Lo observado de un participante ante un caso. Nada interpretado aún.

    Es deliberadamente descriptiva: quien juzga es ``metrics``, y separarlo
    evita que el ejecutor pueda decidir a la vez qué pasó y si estuvo bien.
    """

    ids: tuple[str, ...]
    etapas_recorridas: tuple[str, ...]
    etapa_de_resolucion: str | None
    suficiencia: str
    estado_externo: str
    parada: str
    polaridad_leida: Mapping[str, Polaridad]
    explicaciones_completas: int
    #: Elementos del canon que el participante recorrió para responder. Es
    #: `RF-14` medido sobre lo ejecutado, no deducido del código.
    universo_recorrido: int
    #: Etapa en que actuó cada señal tardía, cuando el participante declara
    #: alguna. Vacío para quien no tiene. Es la evidencia 10 del §10.
    etapa_por_senal_tardia: Mapping[str, str] = field(default_factory=dict)


class Participante(Protocol):
    """Lo único que la ronda necesita de un participante."""

    @property
    def identificador(self) -> str: ...

    def responder(self, peticion: Peticion) -> Observacion: ...

    def close(self) -> None: ...


def _explicaciones_completas(recuperacion: engine.Recuperacion) -> int:
    """Resultados con los siete elementos de `RF-28` realmente rellenos."""
    completas = 0
    for resultado in recuperacion.resultados:
        explicacion = resultado.explicacion
        if all(getattr(explicacion, elemento, None) for elemento in ELEMENTOS_DE_RF_28):
            completas += 1
    return completas


def _etapa_de_resolucion(recuperacion: engine.Recuperacion) -> str | None:
    """La etapa más tardía que aportó un resultado entregado.

    No es la última etapa recorrida: recorrer `E4` sin que aporte nada no
    convierte a `E4` en la etapa que resolvió el caso.
    """
    etapas = [r.etapa_de_origen.value for r in recuperacion.resultados]
    if not etapas:
        return None
    orden = ("E0", "E1", "E2", "E3", "E4", "E5")
    return max(etapas, key=orden.index)


class _Candidato:
    """Un candidato cualquiera, a través del motor común. Igual para los cuatro."""

    def __init__(
        self,
        identificador: str,
        proyeccion: ProyeccionExperimental,
        senales: object,
        *,
        etapa_por_senal_tardia: Mapping[str, str] | None = None,
    ) -> None:
        self._identificador = identificador
        self._senales = senales
        self._etapas_tardias = dict(etapa_por_senal_tardia or {})
        self._plano = PlanoReservado(proyeccion)
        self._puerto = PuertoSqlite(proyeccion.ruta_de_entrada(), proyeccion.ruta(Plano.EJES_P2))

    @property
    def identificador(self) -> str:
        return self._identificador

    def responder(self, peticion: Peticion) -> Observacion:
        antes = self._puerto.registro.filas_totales
        recuperacion = engine.recuperar(peticion, self._puerto, self._senales, self._plano)  # type: ignore[arg-type]
        return Observacion(
            ids=recuperacion.ids,
            etapas_recorridas=tuple(paso.etapa.value for paso in recuperacion.traza.pasos),
            etapa_de_resolucion=_etapa_de_resolucion(recuperacion),
            suficiencia=recuperacion.suficiencia.value,
            estado_externo=recuperacion.estado_externo,
            parada=recuperacion.parada.identificador,
            polaridad_leida={r.item.id: r.lectura.polaridad for r in recuperacion.resultados},
            explicaciones_completas=_explicaciones_completas(recuperacion),
            universo_recorrido=self._puerto.registro.filas_totales - antes,
            etapa_por_senal_tardia=dict(self._etapas_tardias),
        )

    def close(self) -> None:
        self._puerto.close()
        self._plano.close()

    def __enter__(self) -> _Candidato:
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        valor: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        self.close()


class _Control:
    """`T0-control`: Sirius 0.1 tal cual, sin nada añadido."""

    def __init__(self, ruta_canon: Path) -> None:
        self._ruta = ruta_canon
        self._control = t0.control()

    @property
    def identificador(self) -> str:
        return t0.IDENTIFICADOR

    def responder(self, peticion: Peticion) -> Observacion:
        respuesta = self._control.responder(peticion, self._ruta)
        return Observacion(
            ids=respuesta.ids,
            #: Sin etapas: no las tiene. Declararlas vacías es lo honesto;
            #: inventar una lista lo convertiría en un quinto candidato.
            etapas_recorridas=(),
            etapa_de_resolucion=None,
            suficiencia="NO_ADJUDICA",
            estado_externo="" if respuesta.ids else "SIN_RESULTADO_UTILIZABLE",
            parada="NO_ADJUDICA",
            #: Sin lectura semántica: `RF-19` no está implementado, y su ficha
            #: lo declara. Un diccionario vacío no es «todo afirmativo».
            polaridad_leida={},
            explicaciones_completas=0,
            universo_recorrido=respuesta.universo_recorrido,
        )

    def close(self) -> None:
        return None


def _preparar_sidecar(proyeccion: ProyeccionExperimental, trabajo: Path) -> Path:
    """Construye el sidecar vectorial **fuera** de toda ventana cronometrada."""
    trabajo.mkdir(parents=True, exist_ok=True)
    destino = trabajo / SIDECAR
    vectores.construir(proyeccion.ruta_de_entrada(), destino)
    return destino


def construir(
    identificador: str,
    proyeccion: ProyeccionExperimental,
    trabajo: Path,
    *,
    con_senal_relacional: bool = True,
    con_senal_vectorial: bool = True,
    con_validacion_semantica: bool = True,
) -> Participante:
    """El participante pedido, con lo suyo ya preparado.

    Los dos interruptores solo alcanzan a quien tiene esa señal; pedir una
    ablación a quien no la tiene no es un error silencioso, es que no hay nada
    que apagar, y la especificación §8 lo declara «no aplicable por
    construcción» sin penalización.
    """
    entrada = proyeccion.ruta_de_entrada()
    relacional = proyeccion.ruta(Plano.EJES_P2)

    if identificador == t0.IDENTIFICADOR:
        return _Control(entrada)
    if identificador == ca.IDENTIFICADOR:
        de_a = ca.candidato(con_validacion_semantica=con_validacion_semantica)
        return _Candidato(identificador, proyeccion, de_a)
    if identificador == cb.IDENTIFICADOR:
        de_b = cb.candidato(
            entrada,
            _preparar_sidecar(proyeccion, trabajo),
            con_senal_vectorial=con_senal_vectorial,
            con_validacion_semantica=con_validacion_semantica,
        )
        return _Candidato(
            identificador,
            proyeccion,
            de_b,
            etapa_por_senal_tardia={cb.SENAL_TARDIA: "E4"} if con_senal_vectorial else {},
        )
    if identificador == cc.IDENTIFICADOR:
        de_c = cc.candidato(
            relacional,
            con_senal_relacional=con_senal_relacional,
            con_validacion_semantica=con_validacion_semantica,
        )
        return _Candidato(
            identificador,
            proyeccion,
            de_c,
            etapa_por_senal_tardia={cc.SENAL_TARDIA: "E3"} if con_senal_relacional else {},
        )
    if identificador == cd.IDENTIFICADOR:
        de_d = cd.candidato(
            entrada,
            _preparar_sidecar(proyeccion, trabajo),
            relacional,
            con_senal_relacional=con_senal_relacional,
            con_senal_vectorial=con_senal_vectorial,
            con_validacion_semantica=con_validacion_semantica,
        )
        #: Las dos etapas salen del **orden congelado** del candidato, no de
        #: una lista escrita aquí: duplicarla permitiría que divergieran.
        return _Candidato(
            identificador,
            proyeccion,
            de_d,
            etapa_por_senal_tardia={
                senal: etapa.value
                for etapa, senal in cd.ORDEN_CONGELADO
                if (senal == cd.SENAL_RELACIONAL and con_senal_relacional)
                or (senal == cd.SENAL_VECTORIAL and con_senal_vectorial)
            },
        )

    msg = f"participante desconocido: {identificador!r}"
    raise ValueError(msg)


def razon_sin_etapas(identificador: str) -> str:
    """Por qué un participante no puede tener conformidad de etapa."""
    return RAZON_DEL_CONTROL if identificador == t0.IDENTIFICADOR else ""


def polaridades_del_canon(corpus: Mapping[str, object]) -> dict[str, Polaridad]:
    """Polaridad declarada por el corpus, por identidad canónica.

    Es la referencia contra la que se mide la confusión de `RF-19`: sin ella
    solo podría comprobarse que el participante marcó *algo*, no que marcara
    **lo mismo que el canon dice**.
    """
    from experiments.adr002.projection import contracts as pc

    declaradas: dict[str, Polaridad] = {}
    items = corpus.get("items")
    if not isinstance(items, Sequence):
        return declaradas
    for item in items:
        if not isinstance(item, Mapping):
            continue
        identidad = pc.referencia_canonica(str(item.get("id")))
        declarada = item.get("polaridad")
        if identidad is None or not isinstance(declarada, str):
            continue
        try:
            declaradas[identidad] = Polaridad(declarada)
        except ValueError:
            continue
    return declaradas


def proyectos_del_canon(corpus: Mapping[str, object]) -> dict[str, str | None]:
    """Proyecto real de cada elemento, numerado como la proyección lo numera."""
    from experiments.adr002.projection import contracts as pc

    proyectos = corpus.get("proyectos")
    numeros: dict[str, int] = {}
    if isinstance(proyectos, Sequence):
        for posicion, proyecto in enumerate(proyectos, start=1):
            if isinstance(proyecto, Mapping):
                numeros[str(proyecto.get("id"))] = posicion

    por_identidad: dict[str, str | None] = {}
    items = corpus.get("items")
    if not isinstance(items, Sequence):
        return por_identidad
    for item in items:
        if not isinstance(item, Mapping):
            continue
        identidad = pc.referencia_canonica(str(item.get("id")))
        if identidad is None:
            continue
        declarado = item.get("project_id")
        numero = numeros.get(str(declarado)) if declarado is not None else None
        por_identidad[identidad] = None if numero is None else str(numero)
    return por_identidad


__all__ = [
    "RAZON_DEL_CONTROL",
    "SIDECAR",
    "Observacion",
    "Participante",
    "construir",
    "polaridades_del_canon",
    "proyectos_del_canon",
    "razon_sin_etapas",
]
