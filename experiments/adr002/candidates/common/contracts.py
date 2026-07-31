"""Contrato comun de recuperacion para ADR-002 (B04 v1.0).

Define **que** intercambian el motor escalonado y un candidato, sin decidir
**con que senales** responde ninguno. Es deliberadamente pobre en logica: todo
lo que aqui se declare como estructura sera igual para ``ADR002-A``, ``B``,
``C`` y ``D``, y por eso este modulo no puede mencionar a ninguno.

Tres piezas:

1. **La peticion** (``B04-RF-01``, ``B04-Q02``): operacion, consulta,
   proposito, modo ``M1-M5``, ambito, tiempo objetivo, estados, criticidad,
   espacios autorizados, cardinalidad, limites y nivel de traza.
2. **El puerto** (``PuertoDeRecuperacion``): la interfaz estrecha sobre el
   canon y su indice lexico. El motor **nunca** abre SQLite por su cuenta;
   sustituir el sustrato no obliga a tocar el motor, que es lo que
   ``B04-RF-31`` exige.
3. **El candidato** (``SenalesDeCandidato``): lo unico que cada alternativa
   minima aporta —las senales de cada etapa—. **No controla el bucle**: el
   orden de etapas, las puertas y la parada los decide el motor comun, y esa
   es la razon estructural por la que ningun candidato puede saltarse
   ``E0-E5``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, Protocol, runtime_checkable

# --------------------------------------------------------------------------
# Vocabulario normativo de B04
# --------------------------------------------------------------------------


class Modo(StrEnum):
    """Modos ``M1-M5`` de ``B04 §10``. Se adjudica antes de recuperar."""

    M1_ORDINARIO = "M1"
    M2_HISTORICO = "M2"
    M3_FUENTE = "M3"
    M4_GESTION = "M4"
    M5_CONFLICTO = "M5"


class Cardinalidad(StrEnum):
    """``B04 §15.2``. Gobierna si ``S1`` puede adjudicarse."""

    EXACTA = "EXACTA"
    ACOTADA = "ACOTADA"
    EXHAUSTIVA = "EXHAUSTIVA"


class Etapa(StrEnum):
    """Las seis etapas normativas de ``B04 §15.1``, en orden."""

    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"
    E5 = "E5"


#: Orden canonico. El motor lo recorre entero y sin saltos (``B04-RF-14``).
ORDEN_DE_ETAPAS: Final[tuple[Etapa, ...]] = (
    Etapa.E0,
    Etapa.E1,
    Etapa.E2,
    Etapa.E3,
    Etapa.E4,
    Etapa.E5,
)

#: Etapas que aportan candidatas. ``E0`` prepara y ``E5`` adjudica.
ETAPAS_DE_EXPANSION: Final[tuple[Etapa, ...]] = (Etapa.E1, Etapa.E2, Etapa.E3, Etapa.E4)


class Clase(StrEnum):
    """Clase de un elemento del canon."""

    MEMORIA = "MEMORIA"
    DECISION = "DECISION"


class Polaridad(StrEnum):
    """``B04-RF-19``: una negacion no se pierde en expansion ni ranking."""

    AFIRMATIVA = "AFIRMATIVA"
    NEGATIVA = "NEGATIVA"


class ClaseDeEvidencia(StrEnum):
    """``B04-RF-13``: lo externo es evidencia atribuida, no verdad canonica."""

    CANONICA = "CANONICA"
    ATRIBUIDA = "ATRIBUIDA"


class Criticidad(StrEnum):
    """``B04-RF-23``: se propaga con su razon; nunca se auto-marca libremente."""

    ORDINARIA = "ORDINARIA"
    CRITICA = "CRITICA"


# --------------------------------------------------------------------------
# Ambito y tiempo
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Ambito:
    """``G4``: global, proyecto o lista cerrada. Nunca se infiere por categoria."""

    global_: bool
    proyectos: tuple[str, ...]

    def autoriza(self, project_id: str | None) -> bool:
        """Un item fuera de ambito no contamina, ni siquiera para descartarse."""
        if self.global_:
            return True
        return project_id is not None and project_id in self.proyectos


@dataclass(frozen=True, slots=True)
class VentanaTemporal:
    """``G8``: aplicabilidad respecto del tiempo objetivo y corte de registro."""

    tiempo_objetivo: str
    corte_de_registro: str | None = None


# --------------------------------------------------------------------------
# La peticion
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Peticion:
    """Peticion minima de ``B04-Q02``.

    Un campo puede quedar desconocido **solo si no cambia elegibilidad,
    privacidad ni significado**; los que si lo cambian son obligatorios aqui
    por construccion, no por convencion.
    """

    operation_id: str
    consulta: str
    proposito: str
    modo: Modo
    ambito: Ambito
    ventana: VentanaTemporal
    cardinalidad: Cardinalidad
    limite_objetivo: int
    limite_duro: int
    #: Espacios que el modo autoriza a consultar, por etapa.
    espacios_autorizados: frozenset[Etapa] = field(
        default_factory=lambda: frozenset(ETAPAS_DE_EXPANSION)
    )
    #: Estados elegibles ademas de los vigentes, si el modo los admite.
    admite_no_vigentes: bool = False
    #: Cuota de ``ACOTADA``. En ``EXACTA`` son los objetivos identificados.
    objetivos: int = 1
    traza_detallada: bool = True


# --------------------------------------------------------------------------
# Lo que el canon devuelve
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ItemCanonico:
    """Un elemento del canon, tal como el puerto lo entrega.

    Contiene **lo que el canon sabe**: identidad, clase, ambito, texto vigente,
    vigencia, marcas temporales y sensibilidad. No contiene polaridad ni
    condicion: derivarlas es trabajo del candidato, y como las derive es
    justamente parte de la alternativa que se pone a prueba.
    """

    id: str
    clase: Clase
    project_id: str | None
    texto: str
    subject_key: str
    vigente: bool
    disponible: bool
    created_at: str
    entity_ids: tuple[str, ...] = ()
    clase_de_evidencia: ClaseDeEvidencia = ClaseDeEvidencia.CANONICA
    criticidad: Criticidad = Criticidad.ORDINARIA


@dataclass(frozen=True, slots=True)
class LecturaSemantica:
    """Lo que un candidato afirma haber validado de un item (``B04-RF-17``).

    El contrato exige **que se valide**; no impone **como**. Un candidato
    lexico-estructurado y uno vectorial rellenan esto por vias distintas y el
    motor los trata igual: por eso esta estructura vive en la capa comun y su
    calculo no.
    """

    sujeto: str
    polaridad: Polaridad
    condicion: str | None
    tiempo: str | None
    #: Como se obtuvo cada valor. La traza lo registra; el motor lo exige.
    medio: str


@dataclass(frozen=True, slots=True)
class Candidata:
    """Un item propuesto por una etapa, con su lectura semantica y su razon."""

    item: ItemCanonico
    etapa: Etapa
    lectura: LecturaSemantica
    #: Por que esta candidata responde a la consulta. Alimenta ``RF-28``.
    razon: str
    #: Senal concreta que la produjo (clave exacta, alias, relacion...).
    senal: str


# --------------------------------------------------------------------------
# Lo que el motor entrega
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Explicacion:
    """``B04-RF-28``: explicacion minima **por resultado**."""

    item_id: str
    coincidencia: str
    ambito: str
    tiempo: str
    estado: str
    procedencia: str
    criticidad: str
    razon_de_orden: str


@dataclass(frozen=True, slots=True)
class Resultado:
    """Un elegible ordenado, con su explicacion."""

    item: ItemCanonico
    etapa_de_origen: Etapa
    lectura: LecturaSemantica
    explicacion: Explicacion


class Suficiencia(StrEnum):
    """``B04-RF-25``: estado interno detallado; el externo es unico."""

    COMPLETA = "COMPLETA"
    PARCIAL = "PARCIAL"
    NINGUNA_EN_AMBITO = "NINGUNA_EN_AMBITO"
    SOLO_HISTORICO = "SOLO_HISTORICO"
    NO_REPORTABLE = "NO_REPORTABLE"


#: Estado externo unico. ``B04-RF-25`` y ``RF-26``: ausencia y no-reportable
#: comparten redaccion para no filtrar existencia.
ESTADO_EXTERNO_SIN_RESULTADO: Final = "SIN_RESULTADO_UTILIZABLE"


# --------------------------------------------------------------------------
# Puerto de acceso
# --------------------------------------------------------------------------


@runtime_checkable
class PuertoDeRecuperacion(Protocol):
    """Interfaz estrecha sobre el canon y su indice lexico.

    Equivalente a ``KnowledgeSearchRepository`` y obligatorio por
    ``B04-RF-31``. **Ningun metodo devuelve el canon entero**: un barrido
    completo es exactamente lo que ``B04-RF-14`` prohibe, y un puerto que lo
    ofreciera invitaria a saltarse las etapas.
    """

    def por_clave_exacta(self, claves: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """Coincidencia literal sobre claves normalizadas (``E1``)."""
        ...

    def por_termino_lexico(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """Coincidencia del indice lexico medido (``E1``/``E2``)."""
        ...

    def por_entidad(self, entity_ids: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """Items relacionados con entidades resueltas, desde el canon (``E3``)."""
        ...

    def historial_y_fuentes(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """Evidencia atribuida no canonica (``E4``)."""
        ...


# --------------------------------------------------------------------------
# Lo que aporta un candidato
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ContextoDeEtapa:
    """Lo que el motor entrega a una etapa del candidato.

    Incluye lo ya recuperado para que el candidato **no repita** trabajo, pero
    no le permite decidir si continua: eso lo adjudica el motor.
    """

    peticion: Peticion
    puerto: PuertoDeRecuperacion
    etapa: Etapa
    ya_recuperados: frozenset[str]


@runtime_checkable
class SenalesDeCandidato(Protocol):
    """Lo unico que una alternativa minima aporta: sus senales por etapa.

    El candidato **no** decide el orden, ni las puertas, ni la parada. Devuelve
    candidatas cuando el motor le pregunta por una etapa, y declara que senal
    tardia habilita —lo que ``ARQ-00 §23`` pone a prueba—.
    """

    @property
    def identificador(self) -> str:
        """Identidad del candidato. El motor la registra; no ramifica por ella."""
        ...

    @property
    def senal_tardia_habilitada(self) -> str:
        """``ninguna_adicional``, ``semantica_vectorial``, ``relacional_explicita``..."""
        ...

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        """Candidatas que el candidato aporta en ``contexto.etapa``."""
        ...

    def leer(self, item: ItemCanonico, consulta: str) -> LecturaSemantica:
        """Sujeto, polaridad, condicion y tiempo del item (``B04-RF-17``)."""
        ...


__all__ = [
    "ESTADO_EXTERNO_SIN_RESULTADO",
    "ETAPAS_DE_EXPANSION",
    "ORDEN_DE_ETAPAS",
    "Ambito",
    "Candidata",
    "Cardinalidad",
    "Clase",
    "ClaseDeEvidencia",
    "ContextoDeEtapa",
    "Criticidad",
    "Etapa",
    "Explicacion",
    "ItemCanonico",
    "LecturaSemantica",
    "Modo",
    "Peticion",
    "Polaridad",
    "PuertoDeRecuperacion",
    "Resultado",
    "SenalesDeCandidato",
    "Suficiencia",
    "VentanaTemporal",
]
