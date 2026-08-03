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
    """``B04-RF-23``: se propaga con su razon; nunca se auto-marca libremente.

    **Tres niveles, no dos.** Con dos, ``IMPORTANTE`` era indistinguible de
    ``ORDINARIA`` y los 19 items del corpus que declaran nivel se aplastaban en
    dos clases: el nivel llegaba a ``B05`` reinterpretado, que es exactamente lo
    que el traspaso integro prohibe.
    """

    ORDINARIA = "ORDINARIA"
    IMPORTANTE = "IMPORTANTE"
    CRITICA = "CRITICA"


#: De menor a mayor. El orden es dato, no convencion: el desempate y la
#: preservacion bajo limite lo recorren, y una comparacion por literal de
#: cadena —el defecto que esto elimina— no puede expresarlo.
ORDEN_DE_CRITICIDAD: Final[tuple[Criticidad, ...]] = (
    Criticidad.ORDINARIA,
    Criticidad.IMPORTANTE,
    Criticidad.CRITICA,
)


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
class EjesDeclarados:
    """Los ejes P2 que el esquema canonico de Sirius 0.1 **no puede sostener**.

    ``memories.status`` tiene tres valores y ``decisions.status`` cuatro; el
    corpus declara confirmacion, validez y disponibilidad por separado, mas
    sensibilidad, autoridad, ambito y las dos marcas de no uso. Colapsarlos en
    un estado hacia que ``G3``, ``G6``, ``G7`` y ``G9`` leyesen los mismos dos
    booleanos y no pudieran distinguir una memoria candidata de una rechazada,
    ni una sustituida de una purgada.

    Un eje a ``None`` significa **el sustrato no lo declara**, y la puerta que
    lo necesita degrada al estado colapsado dejando constancia. No significa
    que el eje sea permisivo.
    """

    confirmacion: str | None = None
    validez: str | None = None
    disponibilidad: str | None = None
    sensibilidad: str | None = None
    autoridad: str | None = None
    ambito: str | None = None
    no_usar_como_memoria: bool | None = None
    no_consolidable: bool | None = None
    procedencia: tuple[str, ...] = ()
    #: Proyectos que una lista cerrada abarca. Una sola clave foranea no puede
    #: expresar un ambito multiproyecto, y ``G4`` necesita los miembros.
    miembros_de_ambito: tuple[str, ...] = ()

    @property
    def declarados(self) -> bool:
        """Si el sustrato aporto ejes. Sin ellos, las puertas degradan."""
        return self.confirmacion is not None or self.validez is not None


#: Ejes ausentes: el sustrato no los declara y las puertas degradan al estado.
SIN_EJES: Final = EjesDeclarados()

#: Vocabularios P2 que las puertas comparan. Se declaran aqui, en la capa
#: comun, porque las puertas los aplican; su **asignacion** a cada item es de
#: la proyeccion, que es quien conoce el corpus.
CONFIRMACION_VISIBLE_SIEMPRE: Final = "CONFIRMADA"
VALIDEZ_QUE_NO_ENTRA_EN_M1: Final[frozenset[str]] = frozenset({"SUSTITUIDA", "SIN_SOPORTE"})
SENSIBILIDAD_PROTEGIDA: Final[frozenset[str]] = frozenset({"RESTRINGIDA"})
AMBITO_GLOBAL: Final = "GLOBAL"
AMBITO_MULTIPROYECTO: Final = "MULTI_PROYECTO_CERRADO"


@dataclass(frozen=True, slots=True)
class ItemCanonico:
    """Un elemento del canon, tal como el puerto lo entrega.

    Contiene **lo que el canon sabe**: identidad, clase, ambito, texto vigente,
    vigencia y marcas temporales. No contiene polaridad ni condicion: derivarlas
    es trabajo del candidato, y como las derive es justamente parte de la
    alternativa que se pone a prueba.

    **Tampoco contiene criticidad.** La criticidad aplicada es ``HANDOFF_A_B05``
    y su lectura por un candidato esta prohibida por la clasificacion aprobada:
    tenerla aqui la ponia al alcance de cualquiera que recibiese un item, y un
    candidato podria haberla usado para generar candidatas o alterar similitud.
    Vive en el plano comun, indexada por identidad, y solo el motor la consulta.

    ``subject_key`` es **opcional de verdad**. ``None`` significa que el canon
    no declara sujeto; la cadena vacia significaba lo mismo y ademas se
    confundia con un sujeto en blanco, de modo que dos ausencias distintas
    acababan agrupadas entre si.
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
    #: Ejes P2 que el esquema canonico no sostiene. ``SIN_EJES`` cuando el
    #: sustrato no los declara: las puertas degradan y lo hacen constar.
    ejes: EjesDeclarados = SIN_EJES

    @property
    def sujeto_determinado(self) -> bool:
        """Un sujeto ausente o en blanco **no esta determinado**: no agrupa."""
        return bool(self.subject_key and self.subject_key.strip())


@dataclass(frozen=True, slots=True)
class CriticidadAplicada:
    """Los cuatro campos seguros que llegan **integros** hasta ``B05``.

    ``B04-Q21`` pide procedencia de politica «con ID y evidencia»: el ID es
    ``regla_de_politica`` y la evidencia es ``razon_segura``. La fuente bruta
    del arnes no viaja: porta identificadores de caso del banco, y transportarla
    convertiria el traspaso en una filtracion del oraculo.

    Se asigna **antes de ejecutar**. Ninguna etapa puede crear un nivel: sin
    entrada en el plano comun, el elemento es ordinario, que es lo que
    «cero auto-marcados sin regla» significa.
    """

    nivel: Criticidad
    razon_segura: str
    fuente_de_politica: str
    regla_de_politica: str


#: Lo que el motor puede hacer con la criticidad aplicada, y lo que no. La lista
#: no es decorativa: la prueba de neutralidad la recorre.
USOS_PERMITIDOS_DE_CRITICIDAD: Final[tuple[str, ...]] = (
    "G12",
    "tratamiento previo al limite",
    "desempate estable y registrado",
    "explicacion autorizada",
    "estado PARCIAL por desbordamiento critico",
    "handoff integro a B05",
)
USOS_PROHIBIDOS_DE_CRITICIDAD: Final[tuple[str, ...]] = (
    "generar candidatas",
    "alterar similitud",
    "saltar etapas",
    "rescatar un elemento que no paso las puertas",
    "favorecer a un candidato",
)


@runtime_checkable
class PlanoComun(Protocol):
    """Canal lateral que **solo la capa comun** abre, indexado por identidad.

    Ningun candidato lo recibe. No es una prohibicion escrita: el motor lo toma
    como parametro propio y nunca lo pasa a ``candidatas()`` ni a ``leer()``,
    de modo que un candidato no tiene por donde alcanzarlo.
    """

    def property_key(self, identidad: str) -> str | None:
        """Clave de propiedad, o ``None`` si el canal no la determina."""
        ...

    def criticidad_aplicada(self, identidad: str) -> CriticidadAplicada | None:
        """Criticidad congelada del elemento, o ``None`` si no tiene."""
        ...


class PlanoComunVacio:
    """Plano sin canal lateral: **nada esta determinado**.

    No es un plano permisivo. Sin ``property_key`` no se agrupa —la duda no
    fusiona— y sin criticidad aplicada nada es critico, que es justamente lo
    que «ninguna etapa crea un nivel» exige. Es el valor por defecto para los
    sustratos que no declaran canal lateral.
    """

    def property_key(self, identidad: str) -> str | None:
        return None

    def criticidad_aplicada(self, identidad: str) -> CriticidadAplicada | None:
        return None


PLANO_COMUN_VACIO: Final = PlanoComunVacio()


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
    """``B04-RF-28``: explicacion minima **por resultado**.

    ``procedencias`` es plural porque un grupo de equivalentes aporta las de
    todos sus miembros: con una sola, las procedencias adicionales que el
    contrato de salida exige se perdian al elegir representante.
    """

    item_id: str
    coincidencia: str
    ambito: str
    tiempo: str
    estado: str
    procedencias: tuple[str, ...]
    criticidad: str
    razon_de_orden: str
    #: Grupo al que pertenece, si pertenece a alguno. Vacio si va suelto.
    grupo: str = ""


@dataclass(frozen=True, slots=True)
class GrupoDeEquivalentes:
    """``B04-Q13``: identidades **distintas** que responden a una necesidad.

    Conserva a todos sus miembros. El representante **no los reemplaza ni los
    elimina**: encabeza el grupo, y cada miembro sigue siendo citable, contable
    e inspeccionable por ``G12``. Un grupo que borrase a sus miembros seria una
    deduplicacion disfrazada, y perderia justo lo que ``RF-20`` manda conservar.
    """

    identificador: str
    representante: str
    miembros: tuple[str, ...]
    procedencias_adicionales: tuple[str, ...]
    diferencias_materiales: tuple[str, ...]
    relaciones_entre_miembros: tuple[str, ...]
    razon_del_representante: str
    estado_historico_por_miembro: tuple[tuple[str, str], ...]
    #: Ejes que decidieron la pertenencia. Sin esto la agrupacion es opaca.
    ejes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.representante not in self.miembros:
            msg = f"{self.identificador}: el representante no esta entre sus miembros"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Resultado:
    """Un elegible ordenado, con su explicacion y su grupo si lo tiene."""

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
    """Los **dos** contadores de ``§7.5``, que no son intercambiables.

    - **Semantica**: necesidades distintas. Un grupo de equivalentes cuenta
      **una vez**, porque sus miembros sirven a una sola necesidad.
    - **Documental**: elementos entregables. Un grupo cuenta **tantos como
      miembros entregados**, porque el limite duro se aplica sobre resultados.

    Confundirlos permitia satisfacer una cuota de necesidades semanticas
    distintas repitiendo equivalentes, que es lo que la regla 7 prohibe.
    """

    semantica: int
    documental: int


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


@dataclass(frozen=True, slots=True)
class MaterializacionPorIdentidad:
    """Resultado cerrado de materializar identificadores canonicos exactos.

    Distingue lo pedido, lo encontrado y lo ausente sin que ningun candidato
    tenga que reconstruir esa diferencia a mano: un identificador ausente no
    es un error de formato ni una consulta sin resultados, y confundir esos
    tres casos fue el defecto que el paquete de correccion 02 elimina.
    """

    #: Entradas recibidas, duplicados incluidos.
    pedidos: int
    #: Identificadores normalizados, unicos y en orden canonico.
    solicitados: tuple[str, ...]
    #: Los solicitados que existen en el canon, en orden canonico estable.
    items: tuple[ItemCanonico, ...]
    #: Los solicitados que el canon no contiene. Declarados, nunca callados.
    ausentes: tuple[str, ...]

    @property
    def encontrados(self) -> int:
        return len(self.items)

    @property
    def completa(self) -> bool:
        return not self.ausentes


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

    def por_prefijo_de_sujeto(self, prefijos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        """Items cuya clave de sujeto empieza por un prefijo concreto (``E3``).

        Sustituye a un ``por_entidad`` que recibia identificadores de proyecto:
        el ambito es una **puerta de seguridad**, no un generador de
        candidatos, y enumerar un proyecto entero para filtrar despues era el
        barrido que ``B04-RF-14`` prohibe. Un prefijo de sujeto es una
        relacion que el canon ya materializa y se consulta dirigida.
        """
        ...

    def por_identificadores(self, identificadores: Sequence[str]) -> MaterializacionPorIdentidad:
        """Materializacion dirigida por identidad canonica exacta.

        Acepta unicamente identificadores cerrados construidos desde los
        valores reales de ``Clase`` (``MEMORIA:<n>``, ``DECISION:<n>``, con
        ``n`` entero positivo sin ceros a la izquierda). El formato invalido,
        la entrada vacia y el exceso de cota fallan tipados **antes** de
        consultar; un identificador valido pero inexistente no es un error de
        formato: queda declarado en ``ausentes``. El trabajo depende de
        cuantos identificadores se piden, nunca del tamano del canon.
        """
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

    ``semillas`` son las candidatas admitidas en etapas anteriores. Sin ellas,
    una etapa tardia solo podria expandir desde la consulta —lo que ya hace
    ``E2``— o enumerar un espacio entero y filtrar despues, que es el barrido
    que ``B04-RF-14`` prohibe. Entregarlas permite expandir **desde lo
    recuperado** con consultas dirigidas, y esta disponible por igual para
    cualquier candidato.
    """

    peticion: Peticion
    puerto: PuertoDeRecuperacion
    etapa: Etapa
    ya_recuperados: frozenset[str]
    semillas: tuple[Candidata, ...] = ()


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
    "AMBITO_GLOBAL",
    "AMBITO_MULTIPROYECTO",
    "CONFIRMACION_VISIBLE_SIEMPRE",
    "ESTADO_EXTERNO_SIN_RESULTADO",
    "ETAPAS_DE_EXPANSION",
    "ORDEN_DE_CRITICIDAD",
    "ORDEN_DE_ETAPAS",
    "PLANO_COMUN_VACIO",
    "SENSIBILIDAD_PROTEGIDA",
    "SIN_EJES",
    "USOS_PERMITIDOS_DE_CRITICIDAD",
    "USOS_PROHIBIDOS_DE_CRITICIDAD",
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
