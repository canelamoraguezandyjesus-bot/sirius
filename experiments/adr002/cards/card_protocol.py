"""Reglas vinculantes de la ficha de candidato (ADR002-TOL-210, paquete 09).

No mide. No abre ficheros. No ejecuta nada al importarse.

POR QUE ESTE PAQUETE EXISTE
===========================

`ADR002-TOL-210` dice dos cosas con consecuencia:

    «Un candidato sin ficha confirmada **no es ejecutable**.»
    «Una ejecucion que no referencie una ficha previa **no es utilizable como
    evidencia**.»

Ambas son comprobables por maquina, y hasta este paquete no las comprobaba
nadie. La plantilla v0.1 describia el contenido en prosa y dejaba el
cumplimiento a la buena fe del que la rellenase. La propia fila del Registro
denuncia ese mismo defecto en la version anterior de la regla: «la regla
senalaba a un contenedor que no podia alojarla, y su cumplimiento no era
auditable». Repetirlo un nivel mas arriba habria sido el mismo error.

QUE SE HACE EJECUTABLE
======================

**Anterioridad.** La congelacion no es una fecha escrita en el documento: es
que el commit que confirma la ficha sea **ancestro estricto** del commit que
ejecuta, y que la huella declarada coincida con el blob de la ficha en ese
commit. Una fecha se escribe; una relacion de ancestro, no.

**Completitud.** Un campo vacio o «pendiente» invalida la ficha. Si un valor
no puede declararse, se declara **por que**, y esa imposibilidad se congela
igual.

**Ausencia de resultados.** La ficha contiene limites y declaraciones, jamas
mediciones del propio candidato. Se hace cumplir **cerrando** todos los
conjuntos de campos: lo que el esquema no preve, no entra. Una lista de
nombres prohibidos se esquivaria renombrando.

**Coherencia con las puertas ya satisfechas.** El presupuesto de TOL-207 y el
perfil de TOL-209 estan aprobados y son enteros conocidos. La ficha no los
reproclama: los **cita**, y el validador comprueba que cita los aprobados.

LO QUE ESTE MODULO NO HACE
==========================

No aprueba ningun candidato, no autoriza ejecutarlo y no fija ningun valor:
los valores los declara y congela cada candidato bajo su propia
responsabilidad. Este modulo solo comprueba que los declaro **antes**, que
los declaro **completos** y que no se contradicen con lo ya aprobado.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, TypeGuard

from experiments.adr002.tolerances import profile_protocol as pp

# --------------------------------------------------------------------------
# Identidad
# --------------------------------------------------------------------------

VERSION_ESQUEMA: Final = "ficha-candidato-0.1"
PAQUETE: Final = "SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_09_TOL210_FICHA_CANDIDATO_v0.1"
PLANTILLA: Final = "SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.3_PROPUESTO.md"

#: Documentos de gobierno vigentes. Los cita toda ficha y el esquema lo exige.
REGISTRO: Final = pp.REGISTRO
PROTOCOLO: Final = pp.PROTOCOLO
ACTA_TOL_209: Final = "SIRIUS_0.2_ADR_002_TOL_209_APROBACION_v1.0.md"
ACTA_TOL_207: Final = "SIRIUS_0.2_ADR_002_TOL_207_APROBACION_v1.0.md"

#: Las plantillas anteriores se conservan sin modificar. Sus blobs los citan
#: el Registro, el paquete 02D y la Resolucion de la particion de candidatos:
#: se versionan en vez de editarse, igual que el protocolo v0.1 y el Registro
#: v0.4 en el paquete 08.
PLANTILLAS_ANTERIORES: Final[Mapping[str, str]] = {
    "SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.1_PROPUESTO.md": (
        "4e9fa861ed6ab22a6b19729ed44066c8d93d863e"
    ),
    "SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.2_PROPUESTO.md": (
        "5bdc0133e6f7f578816969ead4e1ff7498a54a04"
    ),
}

#: Actos que fijan el universo de candidatos. La particion NO es T1-T4.
RESOLUCION_PARTICION: Final = "SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md"
NOTA_SUPERACION: Final = (
    "SIRIUS_0.2_ADR_002_NOTA_SUPERACION_02_PARTICION_CANDIDATOS_v1.0_APROBADA.md"
)

# --------------------------------------------------------------------------
# Constantes heredadas de las puertas ya SATISFECHAS
# --------------------------------------------------------------------------

#: Presupuesto absoluto por candidato aprobado por el acta de TOL-207.
PRESUPUESTO_TOL207_B: Final = 1_610_612_736
#: Perfil aprobado por el acta de TOL-209. La ficha los cita, no los elige.
SM_NS: Final = 17_405
U50_NS: Final = 2_685
SESIONES_EXIGIDAS: Final = pp.SESIONES_EXIGIDAS

#: Minimo de repeticiones del §3.1 del protocolo.
REPETICIONES_MINIMAS: Final = 30

#: Universo de fichas fijado por la Resolucion de la particion de candidatos
#: v1.0: las alternativas minimas de ARQ-00 §23, NO la particion T1-T4 de
#: ADR-002 v0.2 §3. No son la misma particion, y la Resolucion zanjo cual rige.
ALTERNATIVAS: Final[tuple[str, ...]] = ("ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D")
CONTROL: Final = "T0-control"
CANDIDATOS: Final[tuple[str, ...]] = (CONTROL, *ALTERNATIVAS)

PAPEL_CANDIDATO: Final = "CANDIDATO"
PAPEL_CONTROL: Final = "CONTROL_DE_FALSACION"
PAPELES: Final[tuple[str, ...]] = (PAPEL_CANDIDATO, PAPEL_CONTROL)

#: Senal tardia habilitada por cada alternativa minima. Es lo que las
#: distingue, y la ficha no puede declarar una incoherente con la suya.
SENAL_POR_ALTERNATIVA: Final[Mapping[str, str]] = {
    "ADR002-A": "ninguna_adicional",
    "ADR002-B": "semantica_vectorial",
    "ADR002-C": "relacional_explicita",
    "ADR002-D": "ambas_en_etapas_distintas",
}
ETAPAS: Final[tuple[str, ...]] = ("E0", "E1", "E2", "E3", "E4", "E5")

ESTADO_CONGELADA: Final = "CONGELADA"
ESTADO_SUSTITUIDA: Final = "SUSTITUIDA"
ESTADOS: Final[tuple[str, ...]] = (ESTADO_CONGELADA, ESTADO_SUSTITUIDA)

#: Puertas de arranque del §9 del Registro. Ninguna ejecucion sin las cinco.
PUERTAS_DE_ARRANQUE: Final[tuple[str, ...]] = (
    "SRC-ADR002-01",
    "ADR002-TOL-207",
    "ADR002-TOL-208",
    "ADR002-TOL-209",
    "ADR002-TOL-210",
)

#: Acta que satisface cada puerta. ``None`` significa que no existe todavia, y
#: por tanto que la puerta NO esta satisfecha. No es una lista de deseos: el
#: verificador comprueba que el fichero existe.
#:
#: ``SRC-ADR002-01`` no tiene acta propia: la declara satisfecha el §6 del acta
#: de TOL-207, que es donde se registro su estado.
ACTAS_QUE_SATISFACEN: Final[Mapping[str, str | None]] = {
    "SRC-ADR002-01": ACTA_TOL_207,
    "ADR002-TOL-207": ACTA_TOL_207,
    "ADR002-TOL-208": None,
    "ADR002-TOL-209": ACTA_TOL_209,
    "ADR002-TOL-210": None,
}

#: Documentos que fijan el universo de fichas. Se comprueba que existen: sin
#: ellos, la particion vigente no seria acreditable.
DOCUMENTOS_DE_PARTICION: Final[tuple[str, ...]] = (
    RESOLUCION_PARTICION,
    NOTA_SUPERACION,
)

#: Puertas previas comunes del §3.2 de ADR-002: no son ventaja de nadie y
#: ningun candidato puede omitirlas.
PUERTAS_PREVIAS_COMUNES: Final[tuple[str, ...]] = (
    "aislamiento_de_ambito",
    "expansion_escalonada_sin_salto",
    "validacion_de_sujeto_polaridad_condicion_y_tiempo",
    "borrado_y_regeneracion_desde_el_canon",
    "peticion_completa_y_operacion_activa",
    "plan_reproducible_y_explicacion_por_resultado",
)

#: Texto que jamas puede aparecer como valor declarado. «Pendiente» no es una
#: declaracion: es la ausencia de una.
MARCADORES_VACIOS: Final[tuple[str, ...]] = (
    "pendiente",
    "por determinar",
    "tbd",
    "todo",
    "n/a",
    "...",
    # El marcador de hueco de la propia plantilla, escapado para que no se
    # confunda con los signos de menor y mayor al leer el codigo.
    "\u2039\u203a",
)

MOTIVO_SIN_FICHA: Final = "ejecucion_sin_ficha_confirmada"
MOTIVO_FICHA_POSTERIOR: Final = "ficha_no_anterior_a_la_ejecucion"
MOTIVO_HUELLA_DISTINTA: Final = "huella_declarada_distinta_del_blob"
MOTIVO_PUERTA_PENDIENTE: Final = "puerta_de_arranque_no_satisfecha"

NO_EJECUTABLE: Final = "NO_EJECUTABLE"
NO_UTILIZABLE: Final = "NO_UTILIZABLE"
ADMISIBLE: Final = "ADMISIBLE"


class FichaInvalidaError(ValueError):
    """La ficha no cumple el contenido minimo de TOL-210."""


# --------------------------------------------------------------------------
# Contenido minimo, en conjuntos CERRADOS
# --------------------------------------------------------------------------

SECCIONES: Final[tuple[str, ...]] = (
    "documento",
    "version_esquema",
    "estado",
    "plantilla",
    "registro",
    "protocolo",
    "actas_de_puerta",
    "identidad",
    "congelacion",
    "arquitectura",
    "senal_tardia",
    "restriccion_d",
    "componentes",
    "corpus",
    "protocolo_aplicado",
    "sustrato_lexico",
    "indices_no_lexicos",
    "ciclo_de_indice",
    "coste_por_etapa",
    "extremo_a_extremo",
    "almacenamiento",
    "estabilidad",
    "banda_temporal",
    "purga",
    "huella_candidato",
    "declaracion_de_congelacion",
    "no_contiene_resultados",
)

CAMPOS_IDENTIDAD: Final[tuple[str, ...]] = (
    "candidato",
    "papel",
    "version",
    "sustituye_a",
    "motivo_de_sustitucion",
)

CAMPOS_CONGELACION: Final[tuple[str, ...]] = ("commit", "huella", "ruta")

CAMPOS_ARQUITECTURA: Final[tuple[str, ...]] = (
    "alternativa_minima",
    "definicion_canonica_que_asume",
    "sustrato_lexico",
    "materializacion_de_relaciones",
    "puerto_de_acceso",
    "etapas_implementadas",
    "puertas_previas_comunes",
)

#: §2.2 bis. La senal tardia habilitada es lo que distingue a cada
#: alternativa minima. La etapa E3 es obligatoria para TODAS, incluida
#: ADR002-A: B04-RF-31 prohibe convertir una obligacion de comportamiento en
#: una realizacion predeterminada, de modo que una senal vectorial NO es
#: obligatoria y su ausencia no es un deficit.
CAMPOS_SENAL_TARDIA: Final[tuple[str, ...]] = (
    "habilitada",
    "coherente_con_la_alternativa",
    "como_satisface_e3",
    "validacion_en_e3",
    "orden_de_las_etapas_tardias",
    "condicion_de_insuficiencia_por_transicion",
)

#: §2.2 ter. ADR002-D **no es B mas C**: sus tres restricciones son
#: acumulativas y su anclaje es B04-D15.
CAMPOS_RESTRICCION_D: Final[tuple[str, ...]] = (
    "aplica",
    "motivo_de_no_aplicacion",
    "senales_en_etapas_distintas",
    "orden_predefinido",
    "sin_coordinacion_simultanea",
    "como_se_demuestra_en_cada_ejecucion",
    "traza_a_b04_d15",
)

CAMPOS_COMPONENTE: Final[tuple[str, ...]] = (
    "papel",
    "nombre",
    "version",
    "origen",
    "acopla_a_proveedor",
    "ruta_de_sustitucion",
)

CAMPOS_CORPUS: Final[tuple[str, ...]] = (
    "version",
    "mensajes",
    "recuerdos",
    "decisiones",
    "proyectos",
    "longitud_media_y_distribucion",
    "commit",
    "head_de_esquema",
    "t0_rederivada_sobre_este_corpus",
    "referencia_de_la_rederivacion",
)

CAMPOS_PROTOCOLO_APLICADO: Final[tuple[str, ...]] = (
    "protocolo",
    "desviaciones",
    "entorno",
    "semilla",
    "repeticiones_por_magnitud",
)

CAMPOS_SUSTRATO: Final[tuple[str, ...]] = ("es_el_fts5_medido", "motivo", "magnitudes")

CAMPOS_MAGNITUD_SUSTRATO: Final[tuple[str, ...]] = (
    "magnitud",
    "objetivo",
    "limite_duro",
    "fundamento",
)

CAMPOS_INDICE: Final[tuple[str, ...]] = (
    "nombre",
    "tipo",
    "datos_canonicos_que_cubre",
    "numero_de_elementos",
    "estructura",
    "precision",
    "bytes_totales",
    "bytes_por_elemento",
    "ratio_sobre_el_canon",
    "porcentaje_del_fichero",
    "crecimiento_por_escala",
    "construccion_y_reconstruccion",
    "limites_por_magnitud",
    "comportamiento_de_borrado",
    "escala_comun",
)

CAMPOS_OPERACION_CICLO: Final[tuple[str, ...]] = (
    "limite",
    "fundamento",
    "ejecutable_treinta_veces",
    "motivo_de_no_ejecutabilidad",
    "evidencia_alternativa",
)

OPERACIONES_CICLO: Final[tuple[str, ...]] = (
    "tamano",
    "construccion",
    "reconstruccion",
    "borrado",
)

CAMPOS_CICLO: Final[tuple[str, ...]] = (
    "operaciones",
    "reconstruccion_desde_el_canon",
    "desaparicion_completa",
    "tasa_de_exito_del_cien_por_cien",
    "purga_fisica_sin_fragmento",
)

CAMPOS_ETAPA: Final[tuple[str, ...]] = (
    "etapa",
    "coste_local_objetivo_ns",
    "coste_local_limite_ns",
    "operaciones_locales",
    "coste_externo_declarado",
)

CAMPOS_COSTE: Final[tuple[str, ...]] = (
    "etapas",
    "coste_de_la_senal_de_consulta",
    "coste_local_total_ns",
    "coste_externo_total",
    "coste_extremo_a_extremo_ns",
)

CAMPOS_EXTREMO: Final[tuple[str, ...]] = (
    "objetivo_p95_ns",
    "limite_duro_p99_ns",
    "percentil_y_n",
    "fundamento",
    "no_deriva_de_tol_102b",
    "no_invoca_el_barrido_de_t0",
)

CAMPOS_ALMACENAMIENTO: Final[tuple[str, ...]] = (
    "presupuesto_absoluto_b",
    "consumo_declarado_b",
    "porcentaje_por_mil",
    "proyeccion_50000_b",
    "cabe",
)

CAMPOS_ESTABILIDAD: Final[tuple[str, ...]] = (
    "sesiones_previstas",
    "sm_ns",
    "u50_ns",
    "regimen_p50",
    "regimen_p95",
    "sin_umbral_relativo_para_p95",
    "consulta_de_banda",
    "repeticion_unica_y_no_evaluable",
)

CAMPOS_BANDA_TEMPORAL: Final[tuple[str, ...]] = (
    "equivalencia_externa",
    "fraccion_de_signo_pareada",
    "ausencia_de_separacion_material",
    "repeticion_en_sesion_independiente",
    "modelo_de_amenaza",
    "no_hereda_la_indistinguibilidad_de_la_linea_base",
)

CAMPOS_PURGA: Final[tuple[str, ...]] = (
    "secuencia",
    "ficheros_cubiertos",
    "payload_reversible_en_el_derivado",
    "modelo_de_amenaza",
    "comprobacion_propuesta",
)

CAMPOS_HUELLA: Final[tuple[str, ...]] = (
    "commit_del_prototipo",
    "hash_del_arbol_de_fuentes",
    "migraciones_o_ddl",
    "artefactos_y_su_hash",
    "reproduccion",
)

CAMPOS_DECLARACION: Final[tuple[str, ...]] = (
    "texto",
    "responsable",
    "fecha",
    "valores_anteriores_a_la_primera_ejecucion",
)

FICHEROS_DE_PURGA: Final[tuple[str, ...]] = (".db", "-wal", "-shm", "-journal")


# --------------------------------------------------------------------------
# Propiedades comprobables
# --------------------------------------------------------------------------


def es_declaracion(valor: object) -> bool:
    """Un texto no vacio y que no sea un marcador de ausencia.

    «Pendiente» no es una declaracion: es la ausencia de una, y TOL-210 la
    prohibe expresamente. Se compara en minusculas y sin espacios de borde.
    """
    if not isinstance(valor, str):
        return False
    limpio = valor.strip().lower()
    return bool(limpio) and limpio not in MARCADORES_VACIOS


def entero_no_negativo(valor: object) -> TypeGuard[int]:
    """Entero de verdad, no un booleano disfrazado."""
    return isinstance(valor, int) and not isinstance(valor, bool) and valor >= 0


def por_mil(numerador: int, denominador: int) -> int:
    """``numerador / denominador`` en milesimas, truncado, en enteros."""
    if denominador <= 0:
        msg = "el denominador debe ser positivo"
        raise ValueError(msg)
    return 1000 * numerador // denominador


def cabe_en_el_presupuesto(consumo_b: int, presupuesto_b: int) -> bool:
    """El consumo declarado no supera el presupuesto absoluto de TOL-207."""
    return 0 <= consumo_b <= presupuesto_b


def coste_local_coherente(etapas: Sequence[Mapping[str, object]], total_ns: int) -> bool:
    """La suma de los costes locales por etapa explica el total declarado.

    El coste **externo** no entra en la suma: TOL-202 prohibe sumarlo al
    local, y el §2.9 de la plantilla lo declara aparte precisamente para que
    no pueda colarse en el total.
    """
    suma = 0
    for etapa in etapas:
        valor = etapa.get("coste_local_limite_ns")
        if not entero_no_negativo(valor):
            return False
        suma += valor
    return suma == total_ns


def objetivo_no_supera_al_limite(objetivo: int, limite: int) -> bool:
    """Un objetivo por encima de su limite duro no es un objetivo."""
    return 0 <= objetivo <= limite


def estabilidad_conforme_al_perfil(estabilidad: Mapping[str, object]) -> tuple[str, ...]:
    """La ficha cita el perfil aprobado; no propone uno propio.

    ``SM`` y ``U50`` los fijo el acta de TOL-209 sobre la evidencia congelada.
    Una ficha que declarase otros no estaria congelando una tolerancia: la
    estaria cambiando en silencio para su propio candidato.
    """
    fallos: list[str] = []
    if estabilidad.get("sesiones_previstas") != SESIONES_EXIGIDAS:
        fallos.append(
            f"estabilidad.sesiones_previstas debe ser exactamente {SESIONES_EXIGIDAS}: "
            f"un rango de otro tamano de muestra es NO_COMPARABLE"
        )
    if estabilidad.get("sm_ns") != SM_NS:
        fallos.append(f"estabilidad.sm_ns debe citar el aprobado ({SM_NS})")
    if estabilidad.get("u50_ns") != U50_NS:
        fallos.append(f"estabilidad.u50_ns debe citar el aprobado ({U50_NS})")
    if estabilidad.get("sin_umbral_relativo_para_p95") is not True:
        fallos.append(
            "estabilidad.sin_umbral_relativo_para_p95 debe ser True: TOL-107 no crea "
            "umbral relativo para P95 y una ficha no puede reintroducirlo"
        )
    return tuple(fallos)


def papel_coherente(candidato: str, papel: str) -> bool:
    """Solo ``T0`` puede fichar como control de falsacion.

    Marcar ``ADR002-A`` o ``ADR002-C`` como control invalidaria la
    comparacion: son candidatos completos y se juzgan con las mismas puertas
    (Resolucion de la particion v1.0 §2.1 y §2.2). La tentacion existe porque
    A no habilita senal tardia adicional y C no habilita la vectorial, pero no
    declarar una senal **no es un deficit**: es la alternativa que se pone a
    prueba.
    """
    if papel not in PAPELES:
        return False
    if candidato == CONTROL:
        return papel == PAPEL_CONTROL
    return papel == PAPEL_CANDIDATO


def senal_coherente(alternativa: str, habilitada: str) -> bool:
    """La senal declarada debe ser exactamente la de su alternativa minima."""
    return SENAL_POR_ALTERNATIVA.get(alternativa) == habilitada


def restriccion_d_aplicable(alternativa: str) -> bool:
    """El bloque de restricciones acumulativas solo aplica a ``ADR002-D``."""
    return alternativa == "ADR002-D"


def estado_de_las_puertas(entorno: EntornoCustodia) -> dict[str, bool]:
    """Deriva que puertas estan satisfechas de las actas que EXISTEN.

    No se declara: se comprueba. Una puerta sin acta no esta satisfecha por
    mucho que su trabajo tecnico este hecho, y por eso ``ADR002-TOL-208`` y
    ``ADR002-TOL-210`` salen en ``False`` mientras no las apruebe la suya.
    """
    estado: dict[str, bool] = {}
    for puerta, acta in ACTAS_QUE_SATISFACEN.items():
        if acta is None:
            estado[puerta] = False
            continue
        try:
            entorno.leer_bytes(f"docs/architecture/{acta}")
        except OSError:
            estado[puerta] = False
        else:
            estado[puerta] = True
    return estado


def fallos_documentos_de_particion(entorno: EntornoCustodia) -> tuple[str, ...]:
    """Sin los actos de particion, el universo de fichas no es acreditable."""
    fallos: list[str] = []
    for nombre in DOCUMENTOS_DE_PARTICION:
        try:
            entorno.leer_bytes(f"docs/architecture/{nombre}")
        except OSError:
            fallos.append(f"documento de particion ausente: {nombre}")
    return tuple(fallos)


def puertas_de_arranque_satisfechas(declaradas: Mapping[str, object]) -> bool:
    """Las cinco puertas del §9 del Registro, sin margen ni excepcion."""
    return all(declaradas.get(puerta) is True for puerta in PUERTAS_DE_ARRANQUE)


# --------------------------------------------------------------------------
# Admisibilidad de una ejecucion frente a su ficha
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReferenciaEjecucion:
    """Lo que una ejecucion cita de la ficha bajo la que dice ampararse."""

    candidato: str
    version: int
    huella: str
    commit_de_ejecucion: str


@dataclass(frozen=True, slots=True)
class FichaConfirmada:
    """Una ficha ya confirmada en el repositorio, con su blob y su commit."""

    candidato: str
    version: int
    huella: str
    commit: str
    estado: str


@dataclass(frozen=True, slots=True)
class Veredicto:
    """Resultado de contrastar una ejecucion con las fichas confirmadas."""

    resultado: str
    motivo: str | None

    @property
    def utilizable(self) -> bool:
        return self.resultado == ADMISIBLE


def admisibilidad(
    referencia: ReferenciaEjecucion,
    confirmadas: Sequence[FichaConfirmada],
    *,
    es_ancestro: object,
) -> Veredicto:
    """Decide si una ejecucion es utilizable como evidencia. Falla cerrado.

    ``es_ancestro(a, b)`` debe devolver ``True`` cuando ``a`` es ancestro de
    ``b``. Se inyecta para poder comprobar la regla sin depender de Git en las
    pruebas, que es lo que permite ejercitar los casos que Git no produce
    facilmente.

    Las tres condiciones son acumulativas y **ninguna es una fecha**:

    1. existe una ficha confirmada de ese candidato y esa version;
    2. su huella coincide con la citada por la ejecucion;
    3. su commit es ancestro **estricto** del commit que ejecuta.

    La tercera es la que convierte «congelada antes» en algo comprobable.
    Igualdad de commits no basta: la ficha tiene que existir ya cuando la
    ejecucion empieza, no aparecer en el mismo acto.
    """
    if not callable(es_ancestro):
        msg = "es_ancestro debe ser invocable"
        raise TypeError(msg)

    candidatas = [
        f
        for f in confirmadas
        if f.candidato == referencia.candidato
        and f.version == referencia.version
        and f.estado == ESTADO_CONGELADA
    ]
    if not candidatas:
        return Veredicto(resultado=NO_UTILIZABLE, motivo=MOTIVO_SIN_FICHA)

    ficha = candidatas[0]
    if ficha.huella != referencia.huella:
        return Veredicto(resultado=NO_UTILIZABLE, motivo=MOTIVO_HUELLA_DISTINTA)

    if ficha.commit == referencia.commit_de_ejecucion:
        return Veredicto(resultado=NO_UTILIZABLE, motivo=MOTIVO_FICHA_POSTERIOR)
    if not es_ancestro(ficha.commit, referencia.commit_de_ejecucion):
        return Veredicto(resultado=NO_UTILIZABLE, motivo=MOTIVO_FICHA_POSTERIOR)

    return Veredicto(resultado=ADMISIBLE, motivo=None)


def ejecutabilidad(
    candidato: str, confirmadas: Sequence[FichaConfirmada], *, puertas: Mapping[str, object]
) -> Veredicto:
    """Decide si un candidato es ejecutable. Falla cerrado.

    Un candidato sin ficha confirmada no es ejecutable, y ninguna ejecucion
    puede comenzar con una puerta de arranque pendiente.
    """
    if candidato not in CANDIDATOS:
        msg = f"candidato no normativo: {candidato}"
        raise FichaInvalidaError(msg)
    if not puertas_de_arranque_satisfechas(puertas):
        return Veredicto(resultado=NO_EJECUTABLE, motivo=MOTIVO_PUERTA_PENDIENTE)
    vigentes = [f for f in confirmadas if f.candidato == candidato and f.estado == ESTADO_CONGELADA]
    if not vigentes:
        return Veredicto(resultado=NO_EJECUTABLE, motivo=MOTIVO_SIN_FICHA)
    return Veredicto(resultado=ADMISIBLE, motivo=None)


def version_sucesora_valida(anterior: int, nueva: int) -> bool:
    """Las versiones de ficha crecen de una en una y nunca retroceden."""
    return nueva == anterior + 1


# --------------------------------------------------------------------------
# Controles internos preinscritos
# --------------------------------------------------------------------------

CONTROLES_BLOQUEANTES: Final[tuple[str, ...]] = (
    "plantilla_anterior_intacta",
    "contenido_minimo_completo",
    "conjuntos_cerrados",
    "sin_marcadores_vacios",
    "presupuesto_de_tol207_citado",
    "perfil_de_tol209_citado",
    "once_sesiones_exigidas",
    "coste_local_coherente",
    "coste_externo_no_sumado",
    "puertas_previas_declaradas",
    "papel_de_control_reservado_a_t0",
    "senal_tardia_coherente_con_la_alternativa",
    "anterioridad_comprobada_contra_git",
    "ejecucion_sin_ficha_no_utilizable",
)


@dataclass(frozen=True, slots=True)
class ResultadoControles:
    """Resultado agregado de los controles internos preinscritos."""

    fallos: tuple[str, ...]

    @property
    def valido(self) -> bool:
        return not self.fallos


def evaluar_controles(estado: Mapping[str, bool]) -> ResultadoControles:
    """Falla cerrado: un control ausente o distinto de ``True`` es fallido."""
    return ResultadoControles(
        fallos=tuple(c for c in CONTROLES_BLOQUEANTES if estado.get(c) is not True)
    )


# --------------------------------------------------------------------------
# Custodia. Se reutiliza el entorno inyectable de los paquetes anteriores.
# --------------------------------------------------------------------------

EntornoCustodia = pp.EntornoCustodia


def blob_git(contenido: bytes) -> str:
    """SHA-1 del objeto blob de Git para ``contenido``."""
    return pp.blob_git(contenido)


def serializacion_canonica(documento: Mapping[str, object]) -> bytes:
    """Forma canonica del contenido normativo de una ficha.

    Claves ordenadas y sin espacios superfluos, de modo que dos ficheros que
    digan lo mismo produzcan los mismos bytes aunque se hayan escrito con
    distinta indentacion o distinto orden de claves. Es lo que permite que la
    huella identifique **el contenido**, no el formato del fichero.
    """
    return json.dumps(documento, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def huella_canonica(documento: Mapping[str, object]) -> str:
    """Huella de una ficha: blob Git de su forma canonica **sin la huella**.

    El campo de huella se excluye del calculo, y no por comodidad: una huella
    que se incluyese a si misma **no tendria punto fijo**, porque escribirla
    cambia el contenido que la produce. Excluirla es lo unico que la hace
    calculable, y no debilita nada, porque el campo excluido es exactamente el
    que se esta comprobando.

    Lo que ata la ficha al repositorio no es esta huella sino el blob del
    fichero en el commit que declara, que el verificador comprueba aparte. Las
    dos comprobaciones son distintas y ninguna sustituye a la otra: esta dice
    *que* se congelo, aquella dice *cuando*.
    """
    copia = {k: v for k, v in documento.items() if k != "congelacion"}
    congelacion = documento.get("congelacion")
    if isinstance(congelacion, Mapping):
        copia["congelacion"] = {k: v for k, v in congelacion.items() if k != "huella"}
    return blob_git(serializacion_canonica(copia))


def fallos_plantillas_anteriores(entorno: EntornoCustodia) -> tuple[str, ...]:
    """Las plantillas v0.1 y v0.2 no se tocan: se versionan.

    Sus blobs los citan el Registro, el paquete 02D y la Resolucion de la
    particion de candidatos. Editarlas en el sitio haria incomprobable la
    custodia de esa cadena, igual que ocurria con el protocolo v0.1 y el
    Registro v0.4 en el paquete 08.
    """
    fallos: list[str] = []
    for nombre, esperado in PLANTILLAS_ANTERIORES.items():
        ruta = f"docs/architecture/{nombre}"
        try:
            observado = blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"plantilla anterior ilegible: {ruta}")
            continue
        if observado != esperado:
            fallos.append(f"plantilla anterior alterada: {ruta} ({observado} != {esperado})")
    return tuple(fallos)
