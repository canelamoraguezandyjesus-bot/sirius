"""Contrato del motor por etapas E0-E5, portado desde
``experiments/adr002/candidates/common/contracts.py`` (rama
``evidence/adr001-spikes``, PR #117), incidencia #457/ADR-109.

Define **qué** intercambian el motor por etapas y una fuente de candidatas
(``SenalesDeCandidato``), sin decidir **con qué señales** responde ninguna.
ADR-109 diagnosticó que la brecha restante del banco de 47 casos tras portar
el tratamiento léxico (incidencia #455/#456) no es de cobertura sino de
precisión, y que cerrarla exige las doce puertas ``G1-G12``
(``staged_engine_gates``), la agrupación de equivalentes
(``staged_engine_grouping``) y el motor que las orquesta
(``staged_engine``) — las tres dependen de este vocabulario común.

Traducción deliberada de nombres, sin alterar la lógica: el laboratorio usa
español para ``B04`` porque el propio contrato normativo (Producto 0.2,
Arquitectura Técnica 0.2 §6.5) está en español, y este módulo conserva esos
nombres para que citarlos contra la fuente original sea directo.

Sobre los ejes que el esquema canónico de Sirius 0.1 no persiste hoy
(``ambito``, ``sensibilidad``, ``property_key``, confirmación/validez
granular, ventana de vigencia): ``EjesDeclarados`` los modela exactamente
como el laboratorio — todos opcionales, con ``None`` significando "el
sustrato no los declara" — y ``SIN_EJES`` es el valor por defecto que todo
candidato real del producto recibe hasta que exista una migración que los
persista (fuera del alcance de esta incidencia, que expresamente la
prohíbe). El banco de 47 casos los suministra desde el corpus congelado
(``tests/acceptance/fixtures/evidence_bank_47_casos.json``, enriquecido con
los ejes que ``experiments/adr002/benchmark/conformance_corpus_v0_6.json``
y ``experiments/adr002/benchmark/property_keys_v0_2.json`` declaran en
``evidence/adr001-spikes``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final, Protocol, runtime_checkable

# --------------------------------------------------------------------------
# Vocabulario normativo
# --------------------------------------------------------------------------


class Modo(StrEnum):
    """Modos ``M1-M5``. Se adjudica antes de recuperar."""

    M1_ORDINARIO = "M1"
    M2_HISTORICO = "M2"
    M3_FUENTE = "M3"
    M4_GESTION = "M4"
    M5_CONFLICTO = "M5"


class Cardinalidad(StrEnum):
    """Gobierna si ``S1`` (suficiencia) puede adjudicarse."""

    EXACTA = "EXACTA"
    ACOTADA = "ACOTADA"
    EXHAUSTIVA = "EXHAUSTIVA"


class Etapa(StrEnum):
    """Las seis etapas normativas, en orden."""

    E0 = "E0"
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"
    E5 = "E5"


#: Orden canónico. El motor lo recorre entero y sin saltos.
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
    """Una negación no se pierde en expansión ni en ranking."""

    AFIRMATIVA = "AFIRMATIVA"
    NEGATIVA = "NEGATIVA"


class ClaseDeEvidencia(StrEnum):
    """Lo externo es evidencia atribuida, no verdad canónica."""

    CANONICA = "CANONICA"
    ATRIBUIDA = "ATRIBUIDA"


class Criticidad(StrEnum):
    """Tres niveles: con dos, ``IMPORTANTE`` sería indistinguible de
    ``ORDINARIA`` y el nivel llegaría reinterpretado."""

    ORDINARIA = "ORDINARIA"
    IMPORTANTE = "IMPORTANTE"
    CRITICA = "CRITICA"


#: De menor a mayor. El desempate y la preservación bajo límite lo recorren.
ORDEN_DE_CRITICIDAD: Final[tuple[Criticidad, ...]] = (
    Criticidad.ORDINARIA,
    Criticidad.IMPORTANTE,
    Criticidad.CRITICA,
)


# --------------------------------------------------------------------------
# Ámbito y tiempo
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Ambito:
    """``G4``: global, proyecto o lista cerrada. Nunca se infiere por categoría."""

    global_: bool
    proyectos: tuple[str, ...]

    def autoriza(self, project_id: str | None) -> bool:
        """Un item fuera de ámbito no contamina, ni siquiera para descartarse."""
        if self.global_:
            return True
        return project_id is not None and project_id in self.proyectos


@dataclass(frozen=True, slots=True)
class VentanaTemporal:
    """``G8``: aplicabilidad respecto del tiempo objetivo y corte de registro."""

    tiempo_objetivo: str
    corte_de_registro: str | None = None


# --------------------------------------------------------------------------
# La petición
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Peticion:
    """Petición mínima que el motor necesita para recuperar.

    Un campo puede quedar desconocido solo si no cambia elegibilidad,
    privacidad ni significado; los que sí lo cambian son obligatorios aquí
    por construcción, no por convención.
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
    #: Estados elegibles además de los vigentes, si el modo los admite.
    admite_no_vigentes: bool = False
    #: Cuota de ``ACOTADA``. En ``EXACTA`` son los objetivos identificados.
    objetivos: int = 1
    traza_detallada: bool = True


# --------------------------------------------------------------------------
# Lo que el canon devuelve
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EjesDeclarados:
    """Los ejes que el esquema canónico de Sirius 0.1 no persiste hoy.

    Un eje a ``None`` significa que el sustrato no lo declara, y la puerta
    que lo necesita degrada al estado colapsado (``status``/``vigente``/
    ``disponible``) dejando constancia. No significa que el eje sea
    permisivo — ver cada puerta en ``staged_engine_gates``.
    """

    confirmacion: str | None = None
    validez: str | None = None
    disponibilidad: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    sensibilidad: str | None = None
    autoridad: str | None = None
    ambito: str | None = None
    no_usar_como_memoria: bool | None = None
    no_consolidable: bool | None = None
    procedencia: tuple[str, ...] = ()
    #: Proyectos que una lista cerrada abarca. Una sola clave foránea no
    #: puede expresar un ámbito multiproyecto, y ``G4`` necesita los miembros.
    miembros_de_ambito: tuple[str, ...] = ()

    @property
    def declarados(self) -> bool:
        """Si el sustrato aportó ejes. Sin ellos, las puertas degradan."""
        return self.confirmacion is not None or self.validez is not None


#: Ejes ausentes: el sustrato no los declara y las puertas degradan al estado
#: colapsado. Es el valor que todo candidato real del producto recibe hoy.
SIN_EJES: Final = EjesDeclarados()

#: Vocabularios que las puertas comparan.
CONFIRMACION_VISIBLE_SIEMPRE: Final = "CONFIRMADA"
VALIDEZ_QUE_NO_ENTRA_EN_M1: Final[frozenset[str]] = frozenset({"SUSTITUIDA", "SIN_SOPORTE"})
SENSIBILIDAD_PROTEGIDA: Final[frozenset[str]] = frozenset({"RESTRINGIDA"})
DISPONIBILIDAD_QUE_NO_ENTRA_EN_MODOS_ORDINARIOS: Final[frozenset[str]] = frozenset({"ARCHIVADA"})
AMBITO_GLOBAL: Final = "GLOBAL"
AMBITO_MULTIPROYECTO: Final = "MULTI_PROYECTO_CERRADO"


@dataclass(frozen=True, slots=True)
class ItemCanonico:
    """Un elemento del canon, tal como el puerto lo entrega.

    No contiene criticidad: la criticidad aplicada vive en el plano común,
    indexada por identidad, y solo el motor la consulta — ningún candidato
    puede leerla ni usarla para generar candidatas o alterar similitud.
    """

    id: str
    clase: Clase
    project_id: str | None
    texto: str
    subject_key: str | None
    vigente: bool
    disponible: bool
    created_at: str
    entity_ids: tuple[str, ...] = ()
    clase_de_evidencia: ClaseDeEvidencia = ClaseDeEvidencia.CANONICA
    ejes: EjesDeclarados = SIN_EJES

    @property
    def sujeto_determinado(self) -> bool:
        """Un sujeto ausente o en blanco no está determinado: no agrupa."""
        return bool(self.subject_key and self.subject_key.strip())


@dataclass(frozen=True, slots=True)
class CriticidadAplicada:
    """Los cuatro campos que llegan íntegros hasta el handoff posterior.

    Se asigna antes de ejecutar. Ninguna etapa puede crear un nivel: sin
    entrada en el plano común, el elemento es ordinario.
    """

    nivel: Criticidad
    razon_segura: str
    fuente_de_politica: str
    regla_de_politica: str


@runtime_checkable
class PlanoComun(Protocol):
    """Canal lateral que solo la capa común abre, indexado por identidad.

    Ningún candidato lo recibe: el motor lo toma como parámetro propio y
    nunca lo pasa a ``candidatas()`` ni a ``leer()``.
    """

    def property_key(self, identidad: str) -> str | None:
        """Clave de propiedad, o ``None`` si el canal no la determina."""
        ...

    def criticidad_aplicada(self, identidad: str) -> CriticidadAplicada | None:
        """Criticidad congelada del elemento, o ``None`` si no tiene."""
        ...


class PlanoComunVacio:
    """Plano sin canal lateral: nada está determinado.

    Sin ``property_key`` no se agrupa y sin criticidad aplicada nada es
    crítico. Es el valor por defecto para los sustratos que no declaran
    canal lateral.
    """

    def property_key(self, identidad: str) -> str | None:
        return None

    def criticidad_aplicada(self, identidad: str) -> CriticidadAplicada | None:
        return None


PLANO_COMUN_VACIO: Final = PlanoComunVacio()


@dataclass(frozen=True, slots=True)
class LecturaSemantica:
    """Lo que una fuente de candidatas afirma haber validado de un item.

    El contrato exige que se valide; no impone cómo.
    """

    sujeto: str
    polaridad: Polaridad
    condicion: str | None
    tiempo: str | None
    #: Cómo se obtuvo cada valor. La traza lo registra; el motor lo exige.
    medio: str


@dataclass(frozen=True, slots=True)
class Candidata:
    """Un item propuesto por una etapa, con su lectura semántica y su razón."""

    item: ItemCanonico
    etapa: Etapa
    lectura: LecturaSemantica
    #: Por qué esta candidata responde a la consulta.
    razon: str
    #: Señal concreta que la produjo (clave exacta, alias, relación...).
    senal: str


# --------------------------------------------------------------------------
# Lo que el motor entrega
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Explicacion:
    """Explicación mínima por resultado."""

    item_id: str
    coincidencia: str
    ambito: str
    tiempo: str
    estado: str
    procedencias: tuple[str, ...]
    criticidad: str
    razon_de_orden: str
    grupo: str = ""


@dataclass(frozen=True, slots=True)
class GrupoDeEquivalentes:
    """Identidades distintas que responden a una misma necesidad.

    Conserva a todos sus miembros: el representante encabeza, no reemplaza
    ni elimina.
    """

    identificador: str
    representante: str
    miembros: tuple[str, ...]
    procedencias_adicionales: tuple[str, ...]
    diferencias_materiales: tuple[str, ...]
    relaciones_entre_miembros: tuple[str, ...]
    razon_del_representante: str
    estado_historico_por_miembro: tuple[tuple[str, str], ...]
    ejes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.representante not in self.miembros:
            msg = f"{self.identificador}: el representante no esta entre sus miembros"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Resultado:
    """Un elegible ordenado, con su explicación y su grupo si lo tiene."""

    item: ItemCanonico
    etapa_de_origen: Etapa
    lectura: LecturaSemantica
    explicacion: Explicacion
    posicion: int = 0
    grupo: GrupoDeEquivalentes | None = None
    criticidad: CriticidadAplicada | None = None

    @property
    def es_representante(self) -> bool:
        return self.grupo is not None and self.grupo.representante == self.item.id


@dataclass(frozen=True, slots=True)
class Cardinalidades:
    """Los dos contadores, que no son intercambiables.

    - Semántica: necesidades distintas. Un grupo de equivalentes cuenta una
      vez.
    - Documental: elementos entregables. Un grupo cuenta tantos como
      miembros entregados.
    """

    semantica: int
    documental: int


class Suficiencia(StrEnum):
    """Estado interno detallado; el externo es único."""

    COMPLETA = "COMPLETA"
    PARCIAL = "PARCIAL"
    NINGUNA_EN_AMBITO = "NINGUNA_EN_AMBITO"
    SOLO_HISTORICO = "SOLO_HISTORICO"
    NO_REPORTABLE = "NO_REPORTABLE"


#: Estado externo único. Ausencia y no-reportable comparten redacción para
#: no filtrar existencia.
ESTADO_EXTERNO_SIN_RESULTADO: Final = "SIN_RESULTADO_UTILIZABLE"


# --------------------------------------------------------------------------
# Puerto de acceso
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MaterializacionPorIdentidad:
    """Resultado cerrado de materializar identificadores canónicos exactos."""

    #: Entradas recibidas, duplicados incluidos.
    pedidos: int
    #: Identificadores normalizados, únicos y en orden canónico.
    solicitados: tuple[str, ...]
    #: Los solicitados que existen en el canon, en orden canónico estable.
    items: tuple[ItemCanonico, ...]
    #: Los solicitados que el canon no contiene. Declarados, nunca callados.
    ausentes: tuple[str, ...]

    @property
    def encontrados(self) -> int:
        return len(self.items)

    @property
    def completa(self) -> bool:
        return not self.ausentes


#: Identidades que ``por_identificadores`` admite en una sola llamada.
IDENTIDADES_POR_LLAMADA: Final = 16


@runtime_checkable
class PuertoDeRecuperacion(Protocol):
    """Interfaz estrecha sobre el canon y su índice léxico.

    Ningún método devuelve el canon entero: un barrido completo saltaría el
    control por etapas, y un puerto que lo ofreciera invitaría a saltárselas.
    """

    def por_clave_exacta(self, claves: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """Coincidencia literal sobre claves normalizadas (``E1``)."""
        ...

    def por_termino_lexico(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """Coincidencia del índice léxico (``E1``/``E2``)."""
        ...

    def por_prefijo_de_sujeto(self, prefijos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """Items cuya clave de sujeto empieza por un prefijo concreto (``E3``)."""
        ...

    def por_identificadores(self, identificadores: Sequence[str]) -> MaterializacionPorIdentidad:
        """Materialización dirigida por identidad canónica exacta."""
        ...

    def historial_y_fuentes(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """Evidencia atribuida no canónica (``E4``)."""
        ...


# --------------------------------------------------------------------------
# Lo que aporta una fuente de candidatas
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ContextoDeEtapa:
    """Lo que el motor entrega a una etapa de la fuente de candidatas.

    ``semillas`` son las candidatas admitidas en etapas anteriores: permiten
    que una etapa tardía expanda desde lo recuperado con consultas
    dirigidas, en vez de enumerar un espacio entero y filtrar después.
    """

    peticion: Peticion
    puerto: PuertoDeRecuperacion
    etapa: Etapa
    ya_recuperados: frozenset[str]
    semillas: tuple[Candidata, ...] = ()


@runtime_checkable
class SenalesDeCandidato(Protocol):
    """Lo único que una fuente de candidatas aporta: sus señales por etapa.

    No decide el orden, ni las puertas, ni la parada: los decide el motor.
    """

    @property
    def identificador(self) -> str:
        """Identidad de la fuente. El motor la registra; no ramifica por ella."""
        ...

    @property
    def senal_tardia_habilitada(self) -> str:
        """``ninguna_adicional``, ``semantica_vectorial``, ``relacional_explicita``..."""
        ...

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        """Candidatas que la fuente aporta en ``contexto.etapa``."""
        ...

    def leer(self, item: ItemCanonico, consulta: str) -> LecturaSemantica:
        """Sujeto, polaridad, condición y tiempo del item."""
        ...


__all__ = [
    "AMBITO_GLOBAL",
    "AMBITO_MULTIPROYECTO",
    "CONFIRMACION_VISIBLE_SIEMPRE",
    "DISPONIBILIDAD_QUE_NO_ENTRA_EN_MODOS_ORDINARIOS",
    "ESTADO_EXTERNO_SIN_RESULTADO",
    "ETAPAS_DE_EXPANSION",
    "IDENTIDADES_POR_LLAMADA",
    "ORDEN_DE_CRITICIDAD",
    "ORDEN_DE_ETAPAS",
    "PLANO_COMUN_VACIO",
    "SENSIBILIDAD_PROTEGIDA",
    "SIN_EJES",
    "VALIDEZ_QUE_NO_ENTRA_EN_M1",
    "Ambito",
    "Candidata",
    "Cardinalidad",
    "Cardinalidades",
    "Clase",
    "ClaseDeEvidencia",
    "ContextoDeEtapa",
    "Criticidad",
    "CriticidadAplicada",
    "EjesDeclarados",
    "Etapa",
    "Explicacion",
    "GrupoDeEquivalentes",
    "ItemCanonico",
    "LecturaSemantica",
    "MaterializacionPorIdentidad",
    "Modo",
    "Peticion",
    "PlanoComun",
    "PlanoComunVacio",
    "Polaridad",
    "PuertoDeRecuperacion",
    "Resultado",
    "SenalesDeCandidato",
    "Suficiencia",
    "VentanaTemporal",
]
