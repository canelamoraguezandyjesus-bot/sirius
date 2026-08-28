"""Adaptador de conformidad de ``T0-control``: honesto por construccion.

``T0`` es Sirius 0.1 tal cual. No implementa ``E0-E5``, no tiene puertas, no
adjudica paradas, no explica por resultado y no agrupa. Este adaptador **no le
anade nada de eso**: recibe la misma ``Peticion`` que reciben los candidatos,
la traduce a lo unico que el caso de uso productivo acepta —``query_text``— y
**declara como resultado** cada campo que T0 descarta por el camino.

Esa asimetria es el punto. Un adaptador que rellenase los huecos convertiria
al control de falsacion en un quinto candidato y el benchmark mediria el
adaptador en vez de la linea base.

**Que NO hace este modulo, y es deliberado:**

* no implementa ``SenalesDeCandidato`` ni se pasa a ``engine.recuperar``;
* no aplica ``G1-G12`` ni ninguna puerta;
* no trunca por limite duro: T0 no conoce el limite, y truncarlo aqui
  ocultaria justo el incumplimiento que el control existe para exhibir;
* no filtra por ambito de la peticion: T0 usa el **proyecto activo global**,
  que es su incumplimiento declarado de ``RF-06``;
* no toca ``src/sirius``. El arbol de fuentes de T0 permanece byte a byte, y
  por eso este arnes **no es una modificacion de la implementacion de T0**.

Los repositorios productivos se envuelven en contadores de solo lectura. Un
contador **observa**; no cambia comportamiento, y es lo que permite medir el
barrido completo de ``RF-14`` sobre lo realmente ejecutado en vez de deducirlo
del codigo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from experiments.adr002.candidates.common.contracts import Peticion

from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import (
    build_sqlite_memory_repository,
)
from sirius.adapters.persistence.sqlite_project_repository import (
    build_sqlite_project_repository,
)
from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase
from sirius.domain.decision import Decision
from sirius.domain.memory import Memory
from sirius.domain.relevance import KnowledgeKind, RankedKnowledge

IDENTIFICADOR: Final = "T0-control"

#: Definicion canonica, literal, de la Resolucion de la particion §3.
DEFINICION_CANONICA: Final = (
    "T0 es unicamente la linea base congelada de Sirius 0.1, identificada por "
    "el head de Alembic 61be4bb269bf. Es control de falsacion, no una quinta "
    "alternativa de arquitectura y no candidata."
)

#: Head de Alembic que identifica a T0.
HEAD_T0: Final = "61be4bb269bf"

#: Campos de la peticion comun que el caso de uso productivo **no recibe**.
#: No es una lista de deseos: es la firma real de ``RankRelevantKnowledgeUseCase
#: .rank(query_text: str)``, que solo acepta el texto de la consulta.
CAMPOS_DE_PETICION_QUE_T0_IGNORA: Final[tuple[str, ...]] = (
    "proposito",
    "modo",
    "ambito",
    "ventana",
    "cardinalidad",
    "limite_objetivo",
    "limite_duro",
    "espacios_autorizados",
    "admite_no_vigentes",
    "objetivos",
)

#: Incumplimientos que la ficha congelada de T0 ya declara. Se reproducen aqui
#: **verbatim desde la ficha** para que el resultado del control los exhiba en
#: vez de que haya que ir a buscarlos.
INCUMPLIMIENTOS_DECLARADOS: Final[dict[str, str]] = {
    "RF-06": (
        "aislamiento de ambito no implementado: la busqueda no aisla por proyecto; "
        "medido e inventariado por la Resolucion de la particion §3"
    ),
    "RF-14": (
        "barrido completo prohibido presente: rank() recorre todos los candidatos "
        "del indice; es la razon de ser del control de falsacion"
    ),
    "RF-19": (
        "validacion explicita de sujeto, polaridad, condicion y tiempo no "
        "implementada; medido e inventariado por la Resolucion de la particion §3"
    ),
}

#: Capacidades del contrato comun que T0 **no** tiene. Se declaran para que
#: ninguna comparacion las de por ausentes sin decirlo.
CAPACIDADES_AUSENTES: Final[tuple[str, ...]] = (
    "etapas_E0_E5",
    "puertas_G1_G12",
    "paradas_S1_S7",
    "explicacion_por_resultado",
    "criticidad_aplicada",
    "agrupacion_de_equivalentes",
    "traza_de_transiciones",
)


class ControlNoEjecutableError(RuntimeError):
    """La base del control no permite ejecutar el caso de uso productivo."""


@dataclass(slots=True)
class _Contador:
    """Envuelve un repositorio productivo y cuenta lo que devuelve.

    Observa; no filtra, no reordena y no modifica. Sin el, el barrido de
    ``RF-14`` habria que deducirlo del codigo en vez de medirlo sobre lo que
    la ejecucion realmente recorrio.
    """

    memorias_recorridas: int = 0
    decisiones_recorridas: int = 0

    @property
    def universo_recorrido(self) -> int:
        return self.memorias_recorridas + self.decisiones_recorridas


class _MemoriasContadas:
    def __init__(self, repositorio: object, contador: _Contador) -> None:
        self._repositorio = repositorio
        self._contador = contador

    def list_current_memories(self) -> list[Memory]:
        memorias: list[Memory] = self._repositorio.list_current_memories()  # type: ignore[attr-defined]
        self._contador.memorias_recorridas = len(memorias)
        return memorias


class _DecisionesContadas:
    def __init__(self, repositorio: object, contador: _Contador) -> None:
        self._repositorio = repositorio
        self._contador = contador

    def list_current_decisions(self) -> list[Decision]:
        decisiones: list[Decision] = self._repositorio.list_current_decisions()  # type: ignore[attr-defined]
        self._contador.decisiones_recorridas = len(decisiones)
        return decisiones


@dataclass(frozen=True, slots=True)
class RespuestaDeControl:
    """Lo que T0 realmente produce ante un caso de conformidad.

    Deliberadamente **no** es ``Recuperacion``: T0 no adjudica suficiencia, no
    para y no explica, y devolver su estructura obligaria a inventar campos.
    """

    #: Identificadores canonicos, en el orden que S7.5 produce.
    ids: tuple[str, ...]
    #: Cuantos elementos vigentes recorrio para responder. Es ``RF-14`` medido.
    universo_recorrido: int
    #: Cuantos sobrevivieron al filtro de relacion de S7.5.
    devueltos: int
    #: Campos de la peticion que el caso de uso productivo no recibio.
    campos_ignorados: tuple[str, ...]
    #: Capacidades del contrato comun que T0 no tiene.
    capacidades_ausentes: tuple[str, ...]
    #: Incumplimientos declarados por la ficha congelada.
    incumplimientos: dict[str, str] = field(default_factory=dict)

    @property
    def hubo_barrido_completo(self) -> bool:
        """``RF-14``: recorrer todo el canon vigente para responder una consulta."""
        return self.universo_recorrido > self.devueltos


def _identidad_canonica(resultado: RankedKnowledge) -> str:
    """La misma identidad que el puerto comun entrega: ``CLASE:<n>``.

    Se reutiliza el espacio de identidad del canon en vez de inventar uno: sin
    esto, comparar el resultado de T0 con el de un candidato exigiria una
    traduccion que nadie podria auditar.
    """
    clase = "MEMORIA" if resultado.kind is KnowledgeKind.MEMORY else "DECISION"
    return f"{clase}:{resultado.item_id}"


class ControlT0:
    """Ejecuta el caso de uso **productivo** de Sirius 0.1, sin envolverlo."""

    identificador: Final = IDENTIFICADOR

    @property
    def senal_tardia_habilitada(self) -> str:
        """T0 no declara senal tardia: no es una alternativa minima."""
        return "no_aplica_no_es_candidato"

    def responder(self, peticion: Peticion, ruta_db: Path) -> RespuestaDeControl:
        """Responde con lo que T0 produce, y declara lo que descarta."""
        if not ruta_db.exists():
            msg = f"la base del control no existe: {ruta_db}"
            raise ControlNoEjecutableError(msg)

        contador = _Contador()
        memorias = build_sqlite_memory_repository(ruta_db)
        decisiones = build_sqlite_decision_repository(ruta_db)
        proyectos = build_sqlite_project_repository(ruta_db)
        indice = build_sqlite_knowledge_search_repository(ruta_db)
        try:
            caso_de_uso = RankRelevantKnowledgeUseCase(
                _MemoriasContadas(memorias, contador),  # type: ignore[arg-type]
                _DecisionesContadas(decisiones, contador),  # type: ignore[arg-type]
                proyectos,
                indice,
            )
            # **Solo la consulta.** Todo lo demas de la peticion se descarta
            # aqui, y esa perdida es exactamente lo que el control mide.
            ordenados = caso_de_uso.rank(peticion.consulta)
        finally:
            indice.close()

        return RespuestaDeControl(
            ids=tuple(_identidad_canonica(r) for r in ordenados),
            universo_recorrido=contador.universo_recorrido,
            devueltos=len(ordenados),
            campos_ignorados=CAMPOS_DE_PETICION_QUE_T0_IGNORA,
            capacidades_ausentes=CAPACIDADES_AUSENTES,
            incumplimientos=dict(INCUMPLIMIENTOS_DECLARADOS),
        )


def control() -> ControlT0:
    """Instancia del control. Sin estado ni configuracion oculta."""
    return ControlT0()


__all__ = [
    "CAMPOS_DE_PETICION_QUE_T0_IGNORA",
    "CAPACIDADES_AUSENTES",
    "DEFINICION_CANONICA",
    "HEAD_T0",
    "IDENTIFICADOR",
    "INCUMPLIMIENTOS_DECLARADOS",
    "ControlNoEjecutableError",
    "ControlT0",
    "RespuestaDeControl",
    "control",
]
