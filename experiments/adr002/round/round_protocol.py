"""Ronda primaria de ADR-002, **preinscrita**: cinco participantes, sin ejecutar.

No mide. No abre ficheros. No ejecuta nada al importarse. Este modulo declara
**antes** de que exista la autorizacion cómo se ejecutará la ronda, y comprueba
que todo lo que la ronda necesita está en su sitio.

QUE FALTA PARA EJECUTAR LA RONDA
================================

Exactamente una cosa: **la autorizacion**. Los cinco participantes tienen ficha
congelada y aprobación de gobierno; las cinco puertas de arranque están
satisfechas por actas que existen; el corpus está congelado; la línea base está
rederivada sobre ese mismo corpus. Lo único que no existe es el acta que
autorice medir, y su ausencia **bloquea** el recorrido.

POR QUE SE PREINSCRIBE ANTES DE PEDIR LA AUTORIZACION
=====================================================

Porque una autorización sobre un arnés que todavía no existe sería una
autorización a ciegas. El precedente es `ADR002-TOL-208`: allí el arnés real de
medición se preinscribió **antes** de ejecutar, y la ejecución vino después. Lo
que aquí se congela —participantes, orden, semilla, sesiones, repeticiones,
warm-up y registro obligatorio— es exactamente lo que el protocolo v0.2 §8.1
prohíbe cambiar después de observar resultados.

LA GUARDA
=========

`ACTA_DE_AUTORIZACION` no existe en el repositorio, y por eso
`comprobar_precondiciones` devuelve fallos. **No hay bandera de línea de
órdenes que la salte**: la autorización es un documento del repositorio, no un
argumento. Es la misma guarda que TOL-208 usó para `T0`, por el mismo motivo.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from experiments.adr002.cards import card_protocol as cp
from experiments.adr002.tolerances import profile_protocol as pp

# --------------------------------------------------------------------------
# Identidad
# --------------------------------------------------------------------------

VERSION_ESQUEMA: Final = "ronda-primaria-adr002-0.1"
PROTOCOLO: Final = pp.PROTOCOLO
REGISTRO: Final = pp.REGISTRO
ESPECIFICACION: Final = "SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.3_PROPUESTO.md"
MATRIZ: Final = "SIRIUS_0.2_ADR_002_MATRIZ_CANONICA_BENCHMARK_v0.4_PROPUESTO.md"

#: Acta que autorizaría ejecutar la ronda primaria. **No existe todavía**, y por
#: eso el recorrido se bloquea. Su ausencia es la guarda, no un comentario.
ACTA_DE_AUTORIZACION: Final = "SIRIUS_0.2_ADR_002_AUTORIZACION_RONDA_PRIMARIA_v1.0.md"

# --------------------------------------------------------------------------
# Los cinco participantes. Sin reducción.
# --------------------------------------------------------------------------

#: La ronda primaria es `T0 + A + B + C + D` y la Resolución de la partición
#: §2.2 prohíbe retirar una alternativa mínima del universo de candidatos. El
#: control va **primero** por convención de lectura, no por ventaja: el orden
#: real de ejecución lo fija `orden_de_ejecucion`, que rota.
PARTICIPANTES: Final[tuple[str, ...]] = cp.CANDIDATOS

#: Ficha vigente de cada participante en el momento de preinscribir la ronda,
#: con la huella que el verificador recomputa. Una discrepancia bloquea: medir
#: bajo una ficha distinta de la declarada produce evidencia no utilizable
#: (`ADR002-TOL-210`).
FICHAS_VIGENTES: Final[Mapping[str, tuple[int, str]]] = {
    "T0-control": (1, "d47a767e61b30729e15f48c9924413f6fddc9429"),
    "ADR002-A": (7, "653f216f67d389fdf0472159eea896366e623484"),
    "ADR002-B": (9, "93b9cf6c3a49ccd2ad0ef455ddf4a880c78a6d05"),
    "ADR002-C": (4, "5801987de7574c0b416c7b9c74acc6b527652f79"),
    "ADR002-D": (4, "35074ebdac69426a50a72a78c3726fb3b47e91bd"),
}

#: Version que el acta de preparacion de cada candidato aprueba. Sin esto, la
#: comprobacion solo miraba que el acta **existiera**, y un acta que aprobo la
#: v5 dejaba correr la v6: la ronda habria medido bajo una ficha que nadie
#: aprobo. Congelar es tecnico, preparar es de gobierno, y el gobierno se
#: pronuncia sobre **una** version, no sobre un nombre de candidato.
VERSION_APROBADA_POR_ACTA: Final[Mapping[str, int]] = {
    "ADR002-A": 7,
    "ADR002-B": 9,
    "ADR002-C": 4,
    "ADR002-D": 4,
}

#: Actas de gobierno que declaran preparado a cada participante. El control no
#: tiene acta de preparación: la suya es la de autorización de `T0` bajo
#: TOL-208, que ya se ejecutó, y su ficha basta.
ACTAS_DE_PREPARACION: Final[Mapping[str, str]] = {
    "ADR002-A": "SIRIUS_0.2_ADR_002_APROBACION_SUCESORAS_DEL_CIERRE_v1.0.md",
    "ADR002-B": "SIRIUS_0.2_ADR_002_APROBACION_SUCESORAS_DEL_CIERRE_v1.0.md",
    "ADR002-C": "SIRIUS_0.2_ADR_002_APROBACION_SUCESORAS_DEL_CIERRE_v1.0.md",
    "ADR002-D": "SIRIUS_0.2_ADR_002_APROBACION_SUCESORAS_DEL_CIERRE_v1.0.md",
}

# --------------------------------------------------------------------------
# Entrada congelada
# --------------------------------------------------------------------------

#: Corpus definitivo, congelado por su acta. Los cinco se miden sobre EL MISMO,
#: o no es una comparación (protocolo §5.4, `ADR002-TOL-208`).
CORPUS_CONGELADO: Final[Mapping[str, str]] = {
    "experiments/adr002/benchmark/conformance_corpus_v0_4.json": (
        "c21b702cbe613d70ce76b6a8b2e72baf2d4e8a48"
    ),
    "experiments/adr002/benchmark/performance_corpus_v0_2.json": (
        "4e9e2746e49b158a43eda7826b47c78c41b36e90"
    ),
}

#: Línea base rederivada sobre ese mismo corpus, y su repetición controlada.
#: Sin ella no hay contra qué comparar: es el paso 3 de `ADR002-TOL-208`.
LINEA_BASE_REDERIVADA: Final[Mapping[str, str]] = {
    "artifacts/adr002_tolerances/rederivacion_t0_v0.1.json": (
        "781132bfe0365f6b7ebcb9139330d10dc76fd0db"
    ),
    "artifacts/adr002_tolerances/rederivacion_t0_v0.2.json": (
        "9140c1c031ed4bff891fc0fdabb04b4480a8d817"
    ),
}

#: Familia de conformidad **vigente**, congelada por su acta v0.6, con los
#: cuatro congelables propios y los tres que hereda por blob. Es la entrada que
#: la ronda lee de verdad: de ella sale la proyección sobre la que se mide.
#:
#: El cierre previo fijaba el corpus de rendimiento pero no esta familia, y era
#: un hueco: la ronda habría medido sobre una entrada sin verificar. Se tapa
#: **antes** de medir, que es cuando se puede tapar sin sospecha —añadir un
#: control que bloquea más no favorece a ningún participante—.
FAMILIA_DE_CONFORMIDAD: Final[Mapping[str, str]] = {
    "experiments/adr002/benchmark/conformance_corpus_v0_6.json": (
        "561d9dee8f215e4692d22f194c5972b09b5d3027"
    ),
    "experiments/adr002/benchmark/subject_keys_v0_2.json": (
        "f6c0f49b4f084d8b5d364d7ec6e1ba7562a5e302"
    ),
    "experiments/adr002/benchmark/property_keys_v0_2.json": (
        "321383be53dc65859000cf557b5b78e8dafc1901"
    ),
    "experiments/adr002/benchmark/benchmark_manifest_v0_6.json": (
        "c709ecabe493ef4c6f6514edf31f9726823e1508"
    ),
    "experiments/adr002/benchmark/applied_criticality_v0_1.json": (
        "7dcbba0031e76d4f0763e0d0b853e59584fe3077"
    ),
    "experiments/adr002/benchmark/cases_v0_5.json": ("26919e1016c414697664f93455258cb6492ca48c"),
    "experiments/adr002/benchmark/references_v0_5.json": (
        "4694ef3bba3a87cae0412895da992ce5e2b54f45"
    ),
}

#: El fichero sobre el que miden **los cinco**. No es «el mismo corpus»: es el
#: mismo fichero, y por eso el §5.4 se cumple en su forma más estricta.
#:
#: Lleva el esquema canónico de Sirius 0.1 sin DDL adicional, de modo que `T0`
#: —que es Sirius 0.1— corre sobre él igual que los candidatos. El corpus de
#: rendimiento no puede alojarlos: sus identificadores no pasan la biyección de
#: identidad canónica y no tiene canales de sujeto ni de propiedad. Ver el §3.1
#: del acta de autorización.
SUSTRATO: Final = "entrada.sqlite3"
SUSTRATO_ORIGEN: Final = "experiments/adr002/benchmark/conformance_corpus_v0_6.json"

#: Perfil de tolerancias y suelo del instrumento, de los que salen las bandas y
#: `SM`. El protocolo §6.6 exige que estén congelados **antes** del benchmark.
PERFIL_Y_SUELO: Final[Mapping[str, str]] = {
    "artifacts/adr002_tolerances/perfil_tolerancias_v0.1.json": (
        "41003495620aaf9cd37404b45bf359410c4e7504"
    ),
    "artifacts/adr002_tolerances/suelo_medicion_v0.3.json": (
        "7273264879ec0d45861160066555c1f08b5882bc"
    ),
}

# --------------------------------------------------------------------------
# Plan de ejecución, congelado antes de medir
# --------------------------------------------------------------------------

#: Exactamente once, por `TOL-107` y el §3.3 del protocolo. No «al menos»: un
#: rango de otro tamaño de muestra es `NO_COMPARABLE` y no recibe veredicto.
SESIONES_EXIGIDAS: Final = pp.SESIONES_EXIGIDAS

#: §3.2: cien cuando el coste es bajo, y una recuperación lo es frente a la
#: preparación de su base.
REPETICIONES: Final = 100
REPETICIONES_MINIMAS: Final = cp.REPETICIONES_MINIMAS

#: §2.3: se declara su número y se descarta íntegro. Nunca se mezcla.
WARMUP: Final = 10

#: §5.3: semilla fija, declarada antes. Es la del corpus congelado, para que la
#: ronda no introduzca una fuente de aleatoriedad propia.
SEMILLA: Final = "20260726"

#: §2.1: reloj monotónico. Se declara el nombre, no se llama aquí.
RELOJ: Final = "time.perf_counter_ns"


def orden_de_ejecucion(sesion: int, repeticion: int) -> tuple[str, ...]:
    """Orden intercalado de los cinco participantes (§5.2), rotando.

    El protocolo prohíbe ejecutar todos los bloques de un candidato seguidos de
    todos los de otro, porque la deriva del entorno se convertiría en ventaja.
    Rotar por ``sesion + repeticion`` hace además que **ningún participante
    ocupe siempre la misma posición**: quien va primero paga la caché fría, y
    fijar quién la paga sería regalar una ventaja constante.

    Es determinista y sin aleatoriedad: misma sesión y misma repetición
    producen siempre el mismo orden, que es lo que §5.3 exige.
    """
    if sesion < 1 or repeticion < 1:
        msg = f"sesion y repeticion se numeran desde 1: ({sesion}, {repeticion})"
        raise ValueError(msg)
    desplazamiento = (sesion + repeticion) % len(PARTICIPANTES)
    return PARTICIPANTES[desplazamiento:] + PARTICIPANTES[:desplazamiento]


#: §7: lo que toda medición registra. Se preinscribe la lista, no los valores.
REGISTRO_OBLIGATORIO: Final[tuple[str, ...]] = (
    "ficha_de_candidato_id_version_huella",
    "corpus_version_volumenes_commit",
    "entorno_maquina_so_bibliotecas_head_carga",
    "protocolo_version_y_desviaciones",
    "escenario_y_magnitud_con_n_y_warmup",
    "distribucion_p50_p95_p99_min_max_media_n",
    "resolucion_del_percentil_para_ese_n",
    "sesiones_y_variacion_por_la_formula_6_1",
    "regimen_aplicado_y_umbral_en_vigor",
    "veredicto_de_validez_y_repeticion_unica",
    "incidencias_del_entorno_en_la_ventana",
)

#: §10 de la especificación: evidencia mínima por ejecución. La entrada 10 es
#: **propia de `ADR002-D`** y no aplica a los demás.
EVIDENCIA_MINIMA: Final[tuple[str, ...]] = (
    "versiones_de_corpus_casos_y_referencias_con_nivel",
    "identificacion_de_la_linea_base",
    "candidato_y_ablacion_con_ficha_por_id_version_huella",
    "por_caso_entrada_resultado_esperado_veredicto_y_razon",
    "por_resultado_por_que_entro_y_por_que_ocupa_esa_posicion",
    "plan_ejecutado_espacios_puertas_etapas_expansiones_parada",
    "suficiencia_adjudicada_y_cardinalidad_con_razon_de_parada",
    "metricas_con_su_puerta_y_procedencia",
    "casos_no_expresables_marcados_como_incapacidad_de_la_linea_base",
    "para_adr002_d_la_etapa_de_cada_senal_tardia_y_la_no_coordinacion",
    "toda_desviacion_respecto_de_la_especificacion",
)

#: Entrada de `EVIDENCIA_MINIMA` que solo `ADR002-D` puede satisfacer, porque
#: es el único con dos señales tardías que separar.
EVIDENCIA_PROPIA_DE_D: Final = "para_adr002_d_la_etapa_de_cada_senal_tardia_y_la_no_coordinacion"

MOTIVO_SIN_AUTORIZACION: Final = "ejecutar_la_ronda_primaria_no_esta_autorizado"
MOTIVO_PUERTA_PENDIENTE: Final = "acta_de_puerta_ausente"
MOTIVO_ACTA_PENDIENTE: Final = "acta_de_preparacion_ausente"
MOTIVO_CORPUS_ALTERADO: Final = "corpus_congelado_alterado"
MOTIVO_LINEA_BASE_ALTERADA: Final = "linea_base_rederivada_alterada"
MOTIVO_PERFIL_ALTERADO: Final = "perfil_o_suelo_alterado"
MOTIVO_FAMILIA_ALTERADA: Final = "familia_de_conformidad_alterada"
MOTIVO_FICHA: Final = "ficha_de_participante_no_utilizable"
MOTIVO_REDUCCION: Final = "ronda_reducida"
MOTIVO_NEUTRALIDAD: Final = "capa_comun_no_neutral"
MOTIVO_AISLAMIENTO: Final = "candidato_no_aislado"

# --------------------------------------------------------------------------
# Precondiciones. Todas se comprueban ANTES de medir, y fallan cerrado.
# --------------------------------------------------------------------------

EntornoCustodia = pp.EntornoCustodia


def blob_git(contenido: bytes) -> str:
    """SHA-1 del objeto blob de Git para ``contenido``."""
    return pp.blob_git(contenido)


def _existe(entorno: EntornoCustodia, ruta: str) -> bool:
    try:
        entorno.leer_bytes(ruta)
    except OSError:
        return False
    return True


def _fallos_de_blobs(
    entorno: EntornoCustodia, esperados: Mapping[str, str], motivo: str
) -> tuple[str, ...]:
    """Cada artefacto, byte a byte. Uno distinto invalida su congelación."""
    fallos: list[str] = []
    for ruta, esperado in esperados.items():
        try:
            observado = blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"{motivo}: {ruta} ilegible")
            continue
        if observado != esperado:
            fallos.append(f"{motivo}: {ruta} ({observado} != {esperado})")
    return tuple(fallos)


def fallos_de_autorizacion(entorno: EntornoCustodia) -> tuple[str, ...]:
    """Sin acta de autorización, la ronda no se ejecuta. Sin excepción.

    Es la guarda que separa «preparado» de «ejecutado». Se comprueba contra el
    repositorio: la autorización es un documento que existe o no existe, no una
    bandera que cualquiera pueda pasar.
    """
    if not _existe(entorno, f"docs/architecture/{ACTA_DE_AUTORIZACION}"):
        return (
            f"{MOTIVO_SIN_AUTORIZACION}: falta {ACTA_DE_AUTORIZACION}. Medir la ronda "
            f"primaria exige autorizacion expresa e independiente, y ninguna acta la ha dado",
        )
    return ()


def fallos_de_puertas(entorno: EntornoCustodia) -> tuple[str, ...]:
    """Las cinco puertas de arranque, cada una por el acta que la satisface."""
    fallos: list[str] = []
    for puerta in cp.PUERTAS_DE_ARRANQUE:
        acta = cp.ACTAS_QUE_SATISFACEN.get(puerta)
        if acta is None or not _existe(entorno, f"docs/architecture/{acta}"):
            fallos.append(f"{MOTIVO_PUERTA_PENDIENTE}: {puerta} sin acta presente")
    return tuple(fallos)


def fallos_de_preparacion(entorno: EntornoCustodia) -> tuple[str, ...]:
    """Cada candidato necesita su acta de PREPARADO PARA BENCHMARK.

    Que la ficha esté congelada no basta: congelar es un acto técnico y
    preparar es un acto de gobierno. Un candidato con ficha y sin acta no puede
    entrar en la ronda.
    """
    return tuple(
        f"{MOTIVO_ACTA_PENDIENTE}: {candidato} sin {acta}"
        for candidato, acta in ACTAS_DE_PREPARACION.items()
        if not _existe(entorno, f"docs/architecture/{acta}")
    )


def fallos_de_corpus(entorno: EntornoCustodia) -> tuple[str, ...]:
    """El corpus congelado, byte a byte. Otro corpus es otra medición."""
    return _fallos_de_blobs(entorno, CORPUS_CONGELADO, MOTIVO_CORPUS_ALTERADO)


def fallos_de_linea_base(entorno: EntornoCustodia) -> tuple[str, ...]:
    """La rederivación de `T0` sobre el corpus definitivo, intacta."""
    return _fallos_de_blobs(entorno, LINEA_BASE_REDERIVADA, MOTIVO_LINEA_BASE_ALTERADA)


def fallos_de_perfil(entorno: EntornoCustodia) -> tuple[str, ...]:
    """Perfil y suelo congelados antes del benchmark (protocolo §6.6)."""
    return _fallos_de_blobs(entorno, PERFIL_Y_SUELO, MOTIVO_PERFIL_ALTERADO)


def fallos_de_familia(entorno: EntornoCustodia) -> tuple[str, ...]:
    """La familia de conformidad vigente, byte a byte.

    Es la entrada de la que sale el sustrato: medir sobre una familia alterada
    sería medir otra cosa y llamarla lo mismo.
    """
    return _fallos_de_blobs(entorno, FAMILIA_DE_CONFORMIDAD, MOTIVO_FAMILIA_ALTERADA)


def fallos_de_fichas(fichas_congeladas: Sequence[cp.FichaConfirmada]) -> tuple[str, ...]:
    """Una sola ficha CONGELADA por participante, con la huella declarada.

    Tres cosas distintas, y las tres bloquean: que falte, que haya más de una,
    y que la huella no sea la que esta ronda preinscribió. La tercera es la que
    impide medir bajo una ficha que cambió después de declarar el plan.
    """
    fallos: list[str] = []
    for participante in PARTICIPANTES:
        vigentes = [
            f
            for f in fichas_congeladas
            if f.candidato == participante and f.estado == cp.ESTADO_CONGELADA
        ]
        if not vigentes:
            fallos.append(f"{MOTIVO_FICHA}: {participante} no tiene ficha CONGELADA")
            continue
        if len(vigentes) > 1:
            fallos.append(f"{MOTIVO_FICHA}: {participante} tiene {len(vigentes)} fichas CONGELADAS")
            continue
        version, huella = FICHAS_VIGENTES[participante]
        ficha = vigentes[0]
        if ficha.version != version or ficha.huella != huella:
            fallos.append(
                f"{MOTIVO_FICHA}: {participante} declara v{version}/{huella} y el repositorio "
                f"tiene v{ficha.version}/{ficha.huella}"
            )
    return tuple(fallos)


def fallos_de_reduccion(participantes: Sequence[str]) -> tuple[str, ...]:
    """La ronda primaria no se reduce. La Resolución de la partición §2.2 lo prohíbe."""
    faltan = [p for p in PARTICIPANTES if p not in participantes]
    sobran = [p for p in participantes if p not in PARTICIPANTES]
    fallos = [f"{MOTIVO_REDUCCION}: falta {p}" for p in faltan]
    fallos.extend(f"{MOTIVO_REDUCCION}: {p} no es participante de la ronda" for p in sobran)
    return tuple(fallos)


def fallos_de_neutralidad(
    neutralidad: Sequence[str], aislamiento: Mapping[str, Sequence[str]]
) -> tuple[str, ...]:
    """La infraestructura común neutral y cada candidato aislado.

    Se reciben ya calculados en vez de calcularlos aquí: este módulo no lee el
    sistema de ficheros, y así la comprobación es la misma que las pruebas de
    cada candidato ya ejecutan, no una segunda implementación que pudiera
    discrepar.
    """
    fallos = [f"{MOTIVO_NEUTRALIDAD}: {fallo}" for fallo in neutralidad]
    for paquete, hallazgos in sorted(aislamiento.items()):
        fallos.extend(f"{MOTIVO_AISLAMIENTO}: {paquete}: {hallazgo}" for hallazgo in hallazgos)
    return tuple(fallos)


@dataclass(frozen=True, slots=True)
class Precondiciones:
    """Resultado de todas las comprobaciones previas a medir."""

    fallos: tuple[str, ...]

    @property
    def permite_ejecutar(self) -> bool:
        return not self.fallos


def comprobar_precondiciones(
    entorno: EntornoCustodia,
    *,
    fichas_congeladas: Sequence[cp.FichaConfirmada],
    participantes: Sequence[str] = PARTICIPANTES,
    neutralidad: Sequence[str] = (),
    aislamiento: Mapping[str, Sequence[str]] | None = None,
) -> Precondiciones:
    """Todas las guardas, en orden, sin cortocircuito.

    No se corta en el primer fallo a propósito: quien prepare la ejecución debe
    ver **todo** lo que le falta, no descubrirlo de uno en uno.
    """
    fallos: list[str] = []
    fallos.extend(fallos_de_autorizacion(entorno))
    fallos.extend(fallos_de_puertas(entorno))
    fallos.extend(fallos_de_preparacion(entorno))
    fallos.extend(fallos_de_corpus(entorno))
    fallos.extend(fallos_de_linea_base(entorno))
    fallos.extend(fallos_de_perfil(entorno))
    fallos.extend(fallos_de_familia(entorno))
    fallos.extend(fallos_de_fichas(fichas_congeladas))
    fallos.extend(fallos_de_reduccion(participantes))
    fallos.extend(fallos_de_neutralidad(neutralidad, aislamiento or {}))
    return Precondiciones(fallos=tuple(dict.fromkeys(fallos)))


# --------------------------------------------------------------------------
# Controles internos preinscritos
# --------------------------------------------------------------------------

CONTROLES_BLOQUEANTES: Final[tuple[str, ...]] = (
    "autorizacion_expresa_presente",
    "actas_de_puerta_presentes",
    "actas_de_preparacion_presentes",
    "corpus_congelado_intacto",
    "linea_base_rederivada_intacta",
    "perfil_y_suelo_congelados",
    "familia_de_conformidad_intacta",
    "los_cinco_sobre_el_mismo_fichero",
    "una_sola_ficha_congelada_por_participante",
    "huellas_declaradas_iguales_a_las_del_repositorio",
    "ronda_sin_reduccion",
    "capa_comun_neutral",
    "candidatos_aislados",
    "orden_intercalado_y_rotado",
    "semilla_fija_declarada",
    "once_sesiones_exigidas",
    "warmup_declarado_y_descartado",
    "percentiles_por_rango_mas_cercano",
    "registro_obligatorio_completo",
)


__all__ = [
    "ACTAS_DE_PREPARACION",
    "ACTA_DE_AUTORIZACION",
    "CONTROLES_BLOQUEANTES",
    "CORPUS_CONGELADO",
    "EVIDENCIA_MINIMA",
    "EVIDENCIA_PROPIA_DE_D",
    "FAMILIA_DE_CONFORMIDAD",
    "FICHAS_VIGENTES",
    "LINEA_BASE_REDERIVADA",
    "PARTICIPANTES",
    "PERFIL_Y_SUELO",
    "REGISTRO_OBLIGATORIO",
    "REPETICIONES",
    "SEMILLA",
    "SESIONES_EXIGIDAS",
    "SUSTRATO",
    "SUSTRATO_ORIGEN",
    "VERSION_APROBADA_POR_ACTA",
    "WARMUP",
    "EntornoCustodia",
    "Precondiciones",
    "blob_git",
    "comprobar_precondiciones",
    "fallos_de_autorizacion",
    "fallos_de_corpus",
    "fallos_de_familia",
    "fallos_de_fichas",
    "fallos_de_linea_base",
    "fallos_de_neutralidad",
    "fallos_de_perfil",
    "fallos_de_preparacion",
    "fallos_de_puertas",
    "fallos_de_reduccion",
    "orden_de_ejecucion",
]
