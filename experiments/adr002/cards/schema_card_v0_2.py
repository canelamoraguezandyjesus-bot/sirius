"""Esquema v0.2 de la ficha de candidato: la exencion del control (opcion a).

Materializa el acto sucesor 01 de ``ADR002-TOL-210``, que resuelve la decision
de gobierno abierta por el paquete 10: el contrato exigia al **control** lo
mismo que a un **candidato**, y el control no podia darlo sin medir o sin
inventar. La opcion aprobada es la (a): ``T0-control`` queda **exento** de los
campos exclusivos de candidato, pero debe declarar **explicitamente y con
fundamento** cada inaplicabilidad.

Tres reglas de custodia gobiernan este modulo:

1. **La v0.1 no se toca.** ``schema_card_v0_1`` queda byte a byte como lo
   aprobo el acta de TOL-210. Este modulo la **envuelve** para los candidatos
   y anade las reglas del control; no la reescribe.
2. **La exencion es exclusiva de ``T0-control``.** Una ficha de ``ADR002-A``,
   ``B``, ``C`` o ``D`` que declare la seccion de exenciones es invalida: para
   los candidatos rige **integro** el contenido minimo de la v0.1.
3. **Exento no significa mudo.** Cada area eximida exige una declaracion no
   vacia de POR QUE no aplica, y las areas son un conjunto **cerrado**: las
   seis que enumero el acto sucesor, ni una mas.

Falla cerrado y es **total por contrato**: nunca lanza.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final, TypeGuard

from experiments.adr002.cards import card_protocol as cp
from experiments.adr002.cards import schema_card_v0_1 as v01

VERSION_ESQUEMA: Final = "ficha-candidato-0.2"

#: Plantilla vigente tras el acto sucesor. La v0.3 se conserva sin modificar:
#: su blob lo cita el acta de TOL-210 y pasa a la lista de intangibles.
PLANTILLA: Final = "SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.4_PROPUESTO.md"
ACTO_SUCESOR: Final = "SIRIUS_0.2_ADR_002_TOL_210_ACTO_SUCESOR_01_EXENCION_T0_v1.0.md"

#: Toda ficha v0.2 cita las tres actas de puerta y el acto sucesor.
ACTAS_DE_PUERTA: Final[tuple[str, ...]] = (
    cp.ACTA_TOL_207,
    cp.ACTA_TOL_209,
    cp.ACTA_TOL_210,
    ACTO_SUCESOR,
)

#: La plantilla v0.3 pasa a intangible: su blob lo fija el §2.1 del acta de
#: TOL-210 y no puede reescribirse sin invalidar esa acta.
PLANTILLAS_INTANGIBLES_ADICIONALES: Final[Mapping[str, str]] = {
    "SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.3_PROPUESTO.md": (
        "c2beba3e829163ea5fd052c9f1831a13b205873a"
    ),
}

#: Identidad congelada del corpus y de T0, citadas de sus actas. La ficha del
#: control no las elige: las cita, y este esquema comprueba que cita las
#: aprobadas.
CORPUS_COMMIT_CONGELADO: Final = "d27352b9f03dfc6a4d939b855474ce0ad1c2fc86"
HEAD_T0: Final = "61be4bb269bf"

#: Las SEIS areas eximibles, exactamente las que enumera el acto sucesor.
#: Conjunto cerrado: un area no listada no es eximible.
EXENCIONES: Final[tuple[str, ...]] = (
    "alternativa_minima_y_senal_tardia",
    "etapas_e0_e5",
    "limites_locales_por_etapa",
    "limites_extremo_a_extremo",
    "consumo_de_almacenamiento_previo",
    "limites_del_ciclo_de_indice",
)

CAMPOS_EXENCIONES: Final[tuple[str, ...]] = ("limitada_a", *EXENCIONES)

#: Incumplimientos conocidos de T0 frente a B04, medidos e inventariados
#: (Resolucion de la particion §3). El control los declara; no los esconde.
INCUMPLIMIENTOS_CONOCIDOS: Final[tuple[str, ...]] = ("RF-06", "RF-14", "RF-19")

SECCIONES_CONTROL: Final[tuple[str, ...]] = (
    "documento",
    "version_esquema",
    "estado",
    "plantilla",
    "registro",
    "protocolo",
    "actas_de_puerta",
    "identidad",
    "congelacion",
    "arquitectura_de_control",
    "corpus",
    "protocolo_aplicado",
    "escenario_de_control",
    "estabilidad",
    "presupuesto_aplicable",
    "exenciones_de_control",
    "huella_candidato",
    "declaracion_de_congelacion",
    "no_contiene_resultados",
)

CAMPOS_ARQUITECTURA_CONTROL: Final[tuple[str, ...]] = (
    "sustrato_lexico",
    "materializacion_de_relaciones",
    "puerto_de_acceso",
    "incumplimientos_conocidos",
)

#: El escenario del control es el plan del paquete 10, citado literalmente.
CAMPOS_ESCENARIO: Final[tuple[str, ...]] = (
    "fuente_del_plan",
    "escenarios",
    "capas",
    "magnitudes",
)
ESCENARIOS_PLAN: Final[tuple[str, ...]] = (
    "cero_resultados",
    "un_resultado_exacto",
    "muchos_candidatos",
)
CAPAS_PLAN: Final[tuple[str, ...]] = ("solo_indice_fts5", "recuperacion_completa_rank")
FUENTE_DEL_PLAN: Final = "SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_10_TOL208_REDERIVACION_T0_v0.1.md"

CAMPOS_PRESUPUESTO: Final[tuple[str, ...]] = ("presupuesto_absoluto_b", "nota")


def _es_lista(valor: Any) -> TypeGuard[Sequence[Any]]:
    return isinstance(valor, Sequence) and not isinstance(valor, str | bytes)


_HEX: Final = frozenset("0123456789abcdef")


def _es_sha(valor: Any) -> bool:
    return isinstance(valor, str) and len(valor) == 40 and set(valor) <= _HEX


def _ajenos(objeto: Mapping[str, Any], admitidos: Sequence[str], etiqueta: str) -> list[str]:
    sobra = sorted(set(objeto) - set(admitidos))
    return [f"{etiqueta} declara campos ajenos al esquema: {sobra}"] if sobra else []


def _faltan(objeto: Mapping[str, Any], exigidos: Sequence[str], etiqueta: str) -> list[str]:
    ausentes = [c for c in exigidos if c not in objeto]
    return [f"{etiqueta} sin campos {ausentes}"] if ausentes else []


def _declaraciones(objeto: Mapping[str, Any], campos: Sequence[str], etiqueta: str) -> list[str]:
    return [
        f"{etiqueta}.{campo} debe declararse: un campo vacio o «pendiente» invalida la ficha"
        for campo in campos
        if not cp.es_declaracion(objeto.get(campo))
    ]


def _seccion(doc: Mapping[str, Any], nombre: str) -> Mapping[str, Any] | None:
    valor = doc.get(nombre)
    return valor if isinstance(valor, Mapping) else None


# --------------------------------------------------------------------------
# Entrada publica
# --------------------------------------------------------------------------


def fallos_ficha(doc: Mapping[str, Any]) -> list[str]:
    """Valida una ficha v0.2. Lista vacia significa conforme.

    **Total por contrato: nunca lanza.**
    """
    try:
        return _fallos_ficha(doc)
    except Exception as exc:
        return [f"validacion abortada por ficha malformada: {type(exc).__name__}: {exc}"]


def _fallos_ficha(doc: Mapping[str, Any]) -> list[str]:
    if not isinstance(doc, Mapping):
        return ["la ficha debe ser un objeto JSON"]
    if doc.get("version_esquema") != VERSION_ESQUEMA:
        return [f"version_esquema debe ser {VERSION_ESQUEMA}"]

    identidad = _seccion(doc, "identidad")
    candidato = identidad.get("candidato") if identidad is not None else None

    if candidato == cp.CONTROL:
        return _fallos_control(doc)
    return _fallos_candidato(doc)


# --------------------------------------------------------------------------
# Candidatos: rige integro el contenido de la v0.1. La exencion no les alcanza.
# --------------------------------------------------------------------------


def _fallos_candidato(doc: Mapping[str, Any]) -> list[str]:
    """Una ficha v0.2 de candidato es una ficha v0.1 con las citas nuevas.

    Se valida DELEGANDO en el esquema v0.1 congelado, tras normalizar las
    tres citas que la v0.2 actualiza (version, plantilla y actas). Todo lo
    demas —contenido minimo, conjuntos cerrados, coherencias— lo comprueba
    la v0.1 sin cambios: para los candidatos **nada se relaja**.
    """
    fallos: list[str] = []
    if doc.get("plantilla") != PLANTILLA:
        fallos.append(f"la ficha debe declarar la plantilla vigente ({PLANTILLA})")
    actas = doc.get("actas_de_puerta")
    if not _es_lista(actas) or sorted(actas) != sorted(ACTAS_DE_PUERTA):
        fallos.append(
            f"actas_de_puerta debe citar exactamente {sorted(ACTAS_DE_PUERTA)}: las tres "
            f"actas de puerta y el acto sucesor"
        )
    # La exencion es EXCLUSIVA del control. Un candidato que la invoque no
    # esta rellenando una ficha: esta esquivando el contrato.
    if "exenciones_de_control" in doc:
        fallos.append(
            "exenciones_de_control es exclusiva de T0-control: ningun candidato "
            "ADR002-A/B/C/D puede declararse exento de su propio contenido minimo"
        )
        doc = {k: v for k, v in doc.items() if k != "exenciones_de_control"}

    normalizada = {
        **doc,
        "version_esquema": v01.VERSION_ESQUEMA,
        "plantilla": cp.PLANTILLA,
        "actas_de_puerta": [cp.ACTA_TOL_207, cp.ACTA_TOL_209],
    }
    fallos.extend(v01.fallos_ficha(normalizada))
    return fallos


# --------------------------------------------------------------------------
# El control: exento de lo inaplicable, vinculado en todo lo demas.
# --------------------------------------------------------------------------


def _fallos_control(doc: Mapping[str, Any]) -> list[str]:
    fallos = [f"falta la seccion obligatoria: {s}" for s in SECCIONES_CONTROL if s not in doc]
    fallos.extend(_ajenos(doc, SECCIONES_CONTROL, "la ficha de control"))

    if not cp.es_declaracion(doc.get("documento")):
        fallos.append("la ficha debe declarar su titulo")
    if doc.get("estado") not in cp.ESTADOS:
        fallos.append(f"estado debe ser uno de {list(cp.ESTADOS)}")
    if doc.get("plantilla") != PLANTILLA:
        fallos.append(f"la ficha debe declarar la plantilla vigente ({PLANTILLA})")
    if doc.get("registro") != cp.REGISTRO:
        fallos.append(f"la ficha debe declarar el Registro vigente ({cp.REGISTRO})")
    if doc.get("protocolo") != cp.PROTOCOLO:
        fallos.append(f"la ficha debe declarar el protocolo vigente ({cp.PROTOCOLO})")
    actas = doc.get("actas_de_puerta")
    if not _es_lista(actas) or sorted(actas) != sorted(ACTAS_DE_PUERTA):
        fallos.append(f"actas_de_puerta debe citar exactamente {sorted(ACTAS_DE_PUERTA)}")
    if doc.get("no_contiene_resultados") is not True:
        fallos.append("no_contiene_resultados debe ser True: la ficha declara limites, no medidas")

    fallos.extend(_fallos_identidad_control(doc))
    fallos.extend(_fallos_congelacion(doc))
    fallos.extend(_fallos_arquitectura_control(doc))
    fallos.extend(_fallos_corpus_control(doc))
    fallos.extend(_fallos_protocolo_aplicado(doc))
    fallos.extend(_fallos_escenario(doc))
    fallos.extend(_fallos_estabilidad(doc))
    fallos.extend(_fallos_presupuesto(doc))
    fallos.extend(_fallos_exenciones(doc))
    fallos.extend(_fallos_huella(doc))
    fallos.extend(_fallos_declaracion(doc))
    return fallos


def _fallos_identidad_control(doc: Mapping[str, Any]) -> list[str]:
    identidad = _seccion(doc, "identidad")
    if identidad is None:
        return ["identidad ausente o con forma invalida"]
    fallos = _faltan(identidad, cp.CAMPOS_IDENTIDAD, "identidad")
    if fallos:
        return fallos
    fallos.extend(_ajenos(identidad, cp.CAMPOS_IDENTIDAD, "identidad"))
    if identidad["candidato"] != cp.CONTROL:
        fallos.append(f"esta rama del esquema solo valida a {cp.CONTROL}")
    if not cp.papel_coherente(cp.CONTROL, str(identidad["papel"])):
        fallos.append(f"identidad.papel debe ser {cp.PAPEL_CONTROL} para {cp.CONTROL}")
    version = identidad["version"]
    if not cp.entero_no_negativo(version) or version < 1:
        fallos.append("identidad.version debe ser un entero mayor o igual que 1")
        return fallos
    anterior, motivo = identidad["sustituye_a"], identidad["motivo_de_sustitucion"]
    if version == 1:
        if anterior is not None:
            fallos.append("la primera version de una ficha no sustituye a ninguna")
        if motivo is not None:
            fallos.append("la primera version de una ficha no tiene motivo de sustitucion")
    else:
        if not cp.entero_no_negativo(anterior) or not cp.version_sucesora_valida(
            int(anterior), int(version)
        ):
            fallos.append(f"identidad.sustituye_a debe ser {int(version) - 1}")
        if not cp.es_declaracion(motivo):
            fallos.append("una version sucesora debe declarar por que sustituye a la anterior")
    return fallos


def _fallos_congelacion(doc: Mapping[str, Any]) -> list[str]:
    congelacion = _seccion(doc, "congelacion")
    if congelacion is None:
        return ["congelacion ausente o con forma invalida"]
    fallos = _faltan(congelacion, cp.CAMPOS_CONGELACION, "congelacion")
    if fallos:
        return fallos
    fallos.extend(_ajenos(congelacion, cp.CAMPOS_CONGELACION, "congelacion"))
    if not _es_sha(congelacion["commit_de_referencia"]):
        fallos.append(
            "congelacion.commit_de_referencia no tiene forma de SHA: es el commit del acto "
            "sucesor bajo el que la ficha se congela, no el que la contiene"
        )
    if not _es_sha(congelacion["huella"]):
        fallos.append("congelacion.huella no tiene forma de blob Git")
    if not cp.es_declaracion(congelacion["ruta"]):
        fallos.append("congelacion.ruta debe declarar donde vive la ficha")
    return fallos


def _fallos_arquitectura_control(doc: Mapping[str, Any]) -> list[str]:
    arq = _seccion(doc, "arquitectura_de_control")
    if arq is None:
        return ["arquitectura_de_control ausente o con forma invalida"]
    fallos = _faltan(arq, CAMPOS_ARQUITECTURA_CONTROL, "arquitectura_de_control")
    if fallos:
        return fallos
    fallos.extend(_ajenos(arq, CAMPOS_ARQUITECTURA_CONTROL, "arquitectura_de_control"))
    fallos.extend(
        _declaraciones(
            arq,
            ("sustrato_lexico", "materializacion_de_relaciones", "puerto_de_acceso"),
            "arquitectura_de_control",
        )
    )
    # La declaracion de incumplimientos conocidos es parte VINCULANTE de la
    # ficha del control: T0 incumple RF-06, RF-14 y RF-19 (medido), y su
    # ficha lo dice por escrito, uno a uno, en vez de esconderlo.
    incumplimientos = arq.get("incumplimientos_conocidos")
    if not isinstance(incumplimientos, Mapping):
        fallos.append(
            "arquitectura_de_control.incumplimientos_conocidos debe ser un mapa RF -> declaracion"
        )
    else:
        fallos.extend(
            _ajenos(
                incumplimientos,
                INCUMPLIMIENTOS_CONOCIDOS,
                "arquitectura_de_control.incumplimientos_conocidos",
            )
        )
        fallos.extend(
            _declaraciones(
                incumplimientos,
                INCUMPLIMIENTOS_CONOCIDOS,
                "arquitectura_de_control.incumplimientos_conocidos",
            )
        )
    return fallos


def _fallos_corpus_control(doc: Mapping[str, Any]) -> list[str]:
    corpus = _seccion(doc, "corpus")
    if corpus is None:
        return ["corpus ausente o con forma invalida"]
    fallos = _faltan(corpus, cp.CAMPOS_CORPUS, "corpus")
    if fallos:
        return fallos
    fallos.extend(_ajenos(corpus, cp.CAMPOS_CORPUS, "corpus"))
    fallos.extend(_declaraciones(corpus, ("version", "longitud_media_y_distribucion"), "corpus"))
    for campo in ("mensajes", "recuerdos", "decisiones", "proyectos"):
        if not cp.entero_no_negativo(corpus[campo]):
            fallos.append(f"corpus.{campo} debe ser un entero no negativo")
    # El control se ejecuta sobre el corpus CONGELADO, y su ficha lo cita por
    # el commit auditado del acta de congelacion. No es elegible.
    if corpus["commit"] != CORPUS_COMMIT_CONGELADO:
        fallos.append(
            f"corpus.commit debe citar el commit auditado del acta de congelacion v0.4 "
            f"({CORPUS_COMMIT_CONGELADO})"
        )
    if corpus["head_de_esquema"] != HEAD_T0:
        fallos.append(f"corpus.head_de_esquema debe identificar a T0 ({HEAD_T0})")
    rederivada = corpus["t0_rederivada_sobre_este_corpus"]
    if not isinstance(rederivada, bool):
        fallos.append("corpus.t0_rederivada_sobre_este_corpus debe ser booleano")
    elif not cp.es_declaracion(corpus["referencia_de_la_rederivacion"]):
        fallos.append(
            "corpus.referencia_de_la_rederivacion debe citar la rederivacion o declarar "
            "por que todavia no existe"
        )
    return fallos


def _fallos_protocolo_aplicado(doc: Mapping[str, Any]) -> list[str]:
    aplicado = _seccion(doc, "protocolo_aplicado")
    if aplicado is None:
        return ["protocolo_aplicado ausente o con forma invalida"]
    fallos = _faltan(aplicado, cp.CAMPOS_PROTOCOLO_APLICADO, "protocolo_aplicado")
    if fallos:
        return fallos
    fallos.extend(_ajenos(aplicado, cp.CAMPOS_PROTOCOLO_APLICADO, "protocolo_aplicado"))
    if aplicado["protocolo"] != cp.PROTOCOLO:
        fallos.append(f"protocolo_aplicado.protocolo debe ser el aprobado ({cp.PROTOCOLO})")
    fallos.extend(
        _declaraciones(aplicado, ("desviaciones", "entorno", "semilla"), "protocolo_aplicado")
    )
    repeticiones = aplicado["repeticiones_por_magnitud"]
    if not cp.entero_no_negativo(repeticiones) or int(repeticiones) < cp.REPETICIONES_MINIMAS:
        fallos.append(
            f"protocolo_aplicado.repeticiones_por_magnitud debe ser al menos "
            f"{cp.REPETICIONES_MINIMAS} (§3.1 del protocolo)"
        )
    return fallos


def _fallos_escenario(doc: Mapping[str, Any]) -> list[str]:
    escenario = _seccion(doc, "escenario_de_control")
    if escenario is None:
        return ["escenario_de_control ausente o con forma invalida"]
    fallos = _faltan(escenario, CAMPOS_ESCENARIO, "escenario_de_control")
    if fallos:
        return fallos
    fallos.extend(_ajenos(escenario, CAMPOS_ESCENARIO, "escenario_de_control"))
    if escenario["fuente_del_plan"] != FUENTE_DEL_PLAN:
        fallos.append(f"escenario_de_control.fuente_del_plan debe ser {FUENTE_DEL_PLAN}")
    if list(escenario.get("escenarios") or ()) != list(ESCENARIOS_PLAN):
        fallos.append("escenario_de_control.escenarios debe citar el plan del paquete 10")
    if list(escenario.get("capas") or ()) != list(CAPAS_PLAN):
        fallos.append("escenario_de_control.capas debe citar el plan del paquete 10")
    if escenario.get("magnitudes") != len(ESCENARIOS_PLAN) * len(CAPAS_PLAN):
        fallos.append(
            f"escenario_de_control.magnitudes debe ser {len(ESCENARIOS_PLAN) * len(CAPAS_PLAN)}"
        )
    return fallos


def _fallos_estabilidad(doc: Mapping[str, Any]) -> list[str]:
    estabilidad = _seccion(doc, "estabilidad")
    if estabilidad is None:
        return ["estabilidad ausente o con forma invalida"]
    fallos = _faltan(estabilidad, cp.CAMPOS_ESTABILIDAD, "estabilidad")
    if fallos:
        return fallos
    fallos.extend(_ajenos(estabilidad, cp.CAMPOS_ESTABILIDAD, "estabilidad"))
    fallos.extend(list(cp.estabilidad_conforme_al_perfil(estabilidad)))
    fallos.extend(
        _declaraciones(
            estabilidad,
            ("regimen_p50", "regimen_p95", "consulta_de_banda", "repeticion_unica_y_no_evaluable"),
            "estabilidad",
        )
    )
    return fallos


def _fallos_presupuesto(doc: Mapping[str, Any]) -> list[str]:
    presupuesto = _seccion(doc, "presupuesto_aplicable")
    if presupuesto is None:
        return ["presupuesto_aplicable ausente o con forma invalida"]
    fallos = _faltan(presupuesto, CAMPOS_PRESUPUESTO, "presupuesto_aplicable")
    if fallos:
        return fallos
    fallos.extend(_ajenos(presupuesto, CAMPOS_PRESUPUESTO, "presupuesto_aplicable"))
    if presupuesto["presupuesto_absoluto_b"] != cp.PRESUPUESTO_TOL207_B:
        fallos.append(
            f"presupuesto_aplicable.presupuesto_absoluto_b debe citar el aprobado por "
            f"TOL-207 ({cp.PRESUPUESTO_TOL207_B})"
        )
    if not cp.es_declaracion(presupuesto["nota"]):
        fallos.append("presupuesto_aplicable.nota debe declararse")
    return fallos


def _fallos_exenciones(doc: Mapping[str, Any]) -> list[str]:
    """El corazon de la opcion (a): exento no significa mudo.

    Las seis areas eximidas exigen cada una un fundamento no vacio, el
    conjunto esta cerrado, y la exencion se declara limitada a T0-control.
    """
    exenciones = _seccion(doc, "exenciones_de_control")
    if exenciones is None:
        return ["exenciones_de_control ausente o con forma invalida"]
    fallos = _faltan(exenciones, CAMPOS_EXENCIONES, "exenciones_de_control")
    if fallos:
        return fallos
    fallos.extend(_ajenos(exenciones, CAMPOS_EXENCIONES, "exenciones_de_control"))
    if exenciones["limitada_a"] != cp.CONTROL:
        fallos.append(
            f"exenciones_de_control.limitada_a debe ser {cp.CONTROL}: la exencion no es "
            f"transferible a ningun candidato"
        )
    fallos.extend(_declaraciones(exenciones, EXENCIONES, "exenciones_de_control"))
    return fallos


def _fallos_huella(doc: Mapping[str, Any]) -> list[str]:
    huella = _seccion(doc, "huella_candidato")
    if huella is None:
        return ["huella_candidato ausente o con forma invalida"]
    fallos = _faltan(huella, cp.CAMPOS_HUELLA, "huella_candidato")
    if fallos:
        return fallos
    fallos.extend(_ajenos(huella, cp.CAMPOS_HUELLA, "huella_candidato"))
    if not _es_sha(huella["commit_del_prototipo"]):
        fallos.append("huella_candidato.commit_del_prototipo no tiene forma de SHA")
    fallos.extend(
        _declaraciones(
            huella,
            (
                "hash_del_arbol_de_fuentes",
                "migraciones_o_ddl",
                "artefactos_y_su_hash",
                "reproduccion",
            ),
            "huella_candidato",
        )
    )
    return fallos


def _fallos_declaracion(doc: Mapping[str, Any]) -> list[str]:
    declaracion = _seccion(doc, "declaracion_de_congelacion")
    if declaracion is None:
        return ["declaracion_de_congelacion ausente o con forma invalida"]
    fallos = _faltan(declaracion, cp.CAMPOS_DECLARACION, "declaracion_de_congelacion")
    if fallos:
        return fallos
    fallos.extend(_ajenos(declaracion, cp.CAMPOS_DECLARACION, "declaracion_de_congelacion"))
    fallos.extend(
        _declaraciones(declaracion, ("texto", "responsable", "fecha"), "declaracion_de_congelacion")
    )
    if declaracion["valores_anteriores_a_la_primera_ejecucion"] is not True:
        fallos.append(
            "declaracion_de_congelacion.valores_anteriores_a_la_primera_ejecucion debe ser True"
        )
    return fallos
