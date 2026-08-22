"""Generador v0.3 · endurecimiento del corpus, el arnés y la distribución.

Ejecuta:

    uv run python -m experiments.adr002.benchmark.build_corpus_v0_3

Qué cierra respecto del v0.2 —que se conserva intacto—:

* **B-01** · lee el canon con ``canonical_source_v0_3``: tablas seleccionadas
  por cabecera e identidad, invariantes de contenido y Anexo B bidireccional.
* **B-02** · sustituye el corpus de rendimiento uniforme por uno **sintético no
  degenerado**: 5.000 mensajes, 500 recuerdos, 50 decisiones y **dos proyectos
  reales**, con vocabulario aproximadamente Zipf, longitudes, fechas, estados,
  entidades, procedencias, criticidad y relaciones distribuidos y declarados.
* **B-03** · el cierre de `B04-CA-47` se **rederiva del corpus** bajo filtros
  declarados; no hay ningún subconjunto escrito a mano.
* **B-04** · solo `PDP-CA-09` y `PDP-CA-22` siguen siendo casos funcionales de
  nivel 1; los seis PDP-CA de disciplina pasan a
  ``pdp_harness_rules_v0_1.json`` como reglas de protocolo del arnés.
* toda previsión frente a T0 sale de los artefactos congelables y vive en
  ``t0_preexecution_projection_v0_1.json``, no normativo y sustituible.

No ejecuta T0, no implementa ni ejecuta `ADR002-A/B/C/D` y no mide nada.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
import statistics
import unicodedata
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from experiments.adr002.benchmark import build_corpus as V1
from experiments.adr002.benchmark import build_corpus_v0_2 as B2
from experiments.adr002.benchmark import canonical_source_v0_3 as CS3
from experiments.adr002.benchmark import schema_v0_3 as S3

AQUI = Path(__file__).resolve().parent

FICHEROS = (
    "conformance_corpus_v0_3.json",
    "performance_corpus_v0_2.json",
    "cases_v0_3.json",
    "references_v0_3.json",
    "pdp_cases_v0_2.json",
    "pdp_harness_rules_v0_1.json",
    "t0_preexecution_projection_v0_1.json",
    "benchmark_manifest_v0_3.json",
)


# ===========================================================================
# 1. Léxico protegido y detección de contaminación (§6.3)
# ===========================================================================


def normalizar(texto: str | None) -> str:
    """Unicode NFKD sin acentos, minúsculas y sin signos."""
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    sin_acentos = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]+", " ", sin_acentos.lower()).strip()


def _tokens(texto: str | None) -> list[str]:
    return [t for t in normalizar(texto).split() if t]


def _informativos(texto: str | None) -> list[str]:
    return [
        t
        for t in _tokens(texto)
        if len(t) >= S3.LONGITUD_TOKEN_INFORMATIVO and t not in S3.VACIAS and not t.isdigit()
    ]


def _raiz(token: str) -> str | None:
    return token[: S3.LONGITUD_RAIZ] if len(token) >= S3.LONGITUD_RAIZ else None


def _relacion_de_sufijo(a: str, b: str) -> bool:
    """Singular/plural o sufijo flexivo: ``turno`` frente a ``turnos``."""
    if a == b:
        return False
    largo, corto = (a, b) if len(a) > len(b) else (b, a)
    if not largo.startswith(corto):
        return False
    return largo[len(corto) :] in S3.SUFIJOS_FLEXIVOS


class LexicoProtegido:
    """Léxico construido **automáticamente** desde el corpus de conformidad.

    Detecta contaminación por coincidencia exacta, relación singular/plural o
    sufijo, raíz común normalizada, nombre o alias de entidad y n-grama.
    """

    def __init__(self) -> None:
        self.tokens: set[str] = set()
        self.raices: set[str] = set()
        self.nombres: set[str] = set()  # entidades, alias y proyectos, normalizados
        self.ngramas: set[str] = set()
        self.frases: set[str] = set()
        self._palabras_por_nombre: int = 1

    # -- construcción --------------------------------------------------------

    def anadir_texto(self, texto: str | None) -> None:
        informativos = _informativos(texto)
        self.tokens.update(informativos)
        for token in informativos:
            raiz = _raiz(token)
            if raiz:
                self.raices.add(raiz)
        crudos = _tokens(texto)
        marca = {t: (t in self.tokens) for t in set(crudos)}
        for n in (2, 3):
            for i in range(len(crudos) - n + 1):
                grupo = crudos[i : i + n]
                if any(marca.get(t) for t in grupo):
                    self.ngramas.add(" ".join(grupo))

    def anadir_nombre(self, nombre: str | None) -> None:
        limpio = normalizar(nombre)
        if limpio:
            self.nombres.add(limpio)
            self._palabras_por_nombre = max(self._palabras_por_nombre, len(limpio.split()))
        self.anadir_texto(nombre)

    def anadir_frase(self, frase: str | None) -> None:
        limpio = normalizar(frase)
        if limpio:
            self.frases.add(limpio)
        self.anadir_texto(frase)

    # -- detección -----------------------------------------------------------

    def _variantes_de_sufijo(self, token: str) -> str | None:
        """Busca por índice, no por barrido: quita y añade cada sufijo flexivo."""
        for sufijo in S3.SUFIJOS_FLEXIVOS:
            si_alarga = token + sufijo
            if si_alarga in self.tokens:
                return si_alarga
            if token.endswith(sufijo):
                si_acorta = token[: -len(sufijo)]
                if si_acorta and si_acorta in self.tokens:
                    return si_acorta
        return None

    def detectar(self, texto: str | None) -> list[dict[str, str]]:
        """Todas las coincidencias, con el mecanismo que las descubrió."""
        hallazgos: list[dict[str, str]] = []
        crudos = _tokens(texto)
        if not crudos:
            return hallazgos
        for token in crudos:
            if len(token) < S3.LONGITUD_TOKEN_INFORMATIVO or token in S3.VACIAS or token.isdigit():
                continue
            if token in self.tokens:
                hallazgos.append({"mecanismo": "TOKEN_EXACTO", "termino": token})
                continue
            pariente = self._variantes_de_sufijo(token)
            if pariente is not None:
                hallazgos.append(
                    {"mecanismo": "SINGULAR_PLURAL_O_SUFIJO", "termino": f"{token}~{pariente}"}
                )
                continue
            raiz = _raiz(token)
            if raiz and raiz in self.raices:
                hallazgos.append({"mecanismo": "RAIZ_COMUN", "termino": f"{token}~{raiz}"})
        for n in range(1, self._palabras_por_nombre + 1):
            for i in range(len(crudos) - n + 1):
                grupo = " ".join(crudos[i : i + n])
                if grupo in self.nombres:
                    hallazgos.append({"mecanismo": "ENTIDAD_O_ALIAS", "termino": grupo})
        for n in (2, 3):
            for i in range(len(crudos) - n + 1):
                grupo = " ".join(crudos[i : i + n])
                if grupo in self.ngramas:
                    hallazgos.append({"mecanismo": "NGRAMA", "termino": grupo})
        vistos: set[tuple[str, str]] = set()
        unicos: list[dict[str, str]] = []
        for h in hallazgos:
            clave = (h["mecanismo"], h["termino"])
            if clave not in vistos:
                vistos.add(clave)
                unicos.append(h)
        return unicos


def construir_lexico(conformidad: dict[str, Any], casos: dict[str, Any]) -> LexicoProtegido:
    """Consultas, resultados, entidades, frases distintivas, tokens y n-gramas."""
    lex = LexicoProtegido()
    for proyecto in conformidad["proyectos"]:
        lex.anadir_nombre(proyecto["nombre"])
        for alias in proyecto["alias"]:
            lex.anadir_nombre(alias)
    for entidad in conformidad["entidades"]:
        lex.anadir_nombre(entidad["nombre_canonico"])
        for alias in entidad["alias"]:
            lex.anadir_nombre(alias)
    for item in conformidad["items"]:
        lex.anadir_texto(item["text"])
        lex.anadir_texto(item.get("condicion"))
        if item.get("criticidad"):
            lex.anadir_texto(item["criticidad"].get("razon"))
    for mensaje in conformidad["mensajes"]:
        lex.anadir_texto(mensaje["texto"])
    for documento in conformidad["documentos"]:
        lex.anadir_frase(documento["titulo"])
        lex.anadir_texto(documento.get("texto"))
        lex.anadir_texto(documento.get("afirmacion_atribuida"))
    for relacion in conformidad["relaciones"]:
        lex.anadir_texto(relacion["nota"])
    for caso in casos["nivel_1"]:
        canonico = caso["canonico"]
        for clave in ("riesgo", "entrada", "resultado_esperado", "fallo_observable"):
            lex.anadir_frase(canonico[clave])
        inst = caso["instanciacion"]
        lex.anadir_frase(inst["consulta"]["valor"])
        lex.anadir_texto(inst["explicacion_esperada"]["valor"])
        for rama in inst["ramas"]:
            lex.anadir_frase(rama["consulta"])
            lex.anadir_texto(rama["objetivo"])
            lex.anadir_texto(rama["esperado_rama"])
    return lex


# ===========================================================================
# 2. Corpus de conformidad v0.3
# ===========================================================================
# Los 94 elementos del v0.2 se conservan. Lo único que cambia es que el cierre
# de CA-47 deja de estar escrito a mano y pasa a derivarse de estos datos.

FILTRO_BASE_CA47: dict[str, Any] = {
    "kind": "DECISION",
    "project_id": "PRJ-BETA",
    "confirmacion": "CONFIRMADA",
    "validez": "VIGENTE",
    "disponibilidad": "DISPONIBLE",
    "sensibilidad": "ORDINARIA",
    "no_usar_como_memoria": False,
}

FILTROS_CA47: dict[str, dict[str, Any]] = {
    "R1": {
        "eje": "occurred_at",
        "operador": "INTERVALO_SEMIABIERTO",
        "desde": "2026-01-01T00:00:00Z",
        "hasta": "2026-02-01T00:00:00Z",
        "descripcion": "occurred_at cae en enero de 2026",
    },
    "R2": {
        "eje": "valid_time",
        "operador": "VIGENTE_EN_INSTANTE",
        "instante": "2026-01-20T00:00:00Z",
        "descripcion": "valid_from <= 20 de enero < valid_to (o valid_to abierto)",
    },
    "R3": {
        "eje": "recorded_at",
        "operador": "CORTE_DE_REGISTRO",
        "hasta": "2026-02-15T00:00:00Z",
        "descripcion": "recorded_at <= 15 de febrero de 2026",
    },
}


def ambito_ca47(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Los elementos que el filtro base deja dentro del ámbito de CA-47."""
    return [
        i for i in items if all(i.get(clave) == valor for clave, valor in FILTRO_BASE_CA47.items())
    ]


def evaluar_filtro_temporal(item: dict[str, Any], filtro: dict[str, Any]) -> bool:
    """Predicado temporal declarado. El validador reimplementa este cálculo."""
    t = item["temporalidad"]
    if filtro["operador"] == "INTERVALO_SEMIABIERTO":
        valor = t.get(filtro["eje"])
        return valor is not None and filtro["desde"] <= valor < filtro["hasta"]
    if filtro["operador"] == "VIGENTE_EN_INSTANTE":
        desde, hasta = t.get("valid_from"), t.get("valid_to")
        if desde is None or desde > filtro["instante"]:
            return False
        return hasta is None or filtro["instante"] < hasta
    if filtro["operador"] == "CORTE_DE_REGISTRO":
        valor = t.get(filtro["eje"])
        return valor is not None and valor <= filtro["hasta"]
    raise ValueError(f"operador temporal desconocido: {filtro['operador']}")


def cierre_ca47(items: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    """Cierre EXHAUSTIVO de las tres ramas de CA-47, calculado sobre el corpus."""
    dentro = ambito_ca47(items)
    universo = sorted(i["id"] for i in dentro)
    salida: dict[str, dict[str, list[str]]] = {}
    for rama, filtro in FILTROS_CA47.items():
        elegibles = sorted(i["id"] for i in dentro if evaluar_filtro_temporal(i, filtro))
        salida[rama] = {
            "elegibles": elegibles,
            "prohibidos": [i for i in universo if i not in elegibles],
            "universo_en_ambito": universo,
        }
    return salida


def _ramas_ca47(cierre: dict[str, dict[str, list[str]]]) -> list[dict[str, Any]]:
    plantilla = {
        "R1": {
            "objetivo": "Consulta por occurred_at: qué ocurrió en enero.",
            "fuente": (
                "B04 §17.1 CA-47 «Consultas por occurred_at … devuelven resultados distintos»"
            ),
            "consulta": "¿Qué decisiones ocurrieron en enero?",
            "esperado": "Solo las decisiones cuyo occurred_at cae en enero.",
            "tiempo_objetivo": S3.AHORA_DECLARADO,
            "corte_registro": None,
        },
        "R2": {
            "objetivo": "Consulta por tiempo válido: qué era aplicable el 20 de enero.",
            "fuente": "B04 §17.1 CA-47 «… valid_time …»",
            "consulta": "¿Qué decisiones eran válidas el 20 de enero?",
            "esperado": "Solo las decisiones aplicables a esa fecha por tiempo válido.",
            "tiempo_objetivo": "2026-01-20T00:00:00Z",
            "corte_registro": None,
        },
        "R3": {
            "objetivo": "Consulta por corte de registro: qué sabía Sirius el 15 de febrero.",
            "fuente": (
                "B04 §17.1 CA-47 «… y recorded_at devuelven resultados distintos y correctos»"
            ),
            "consulta": "¿Qué decisiones había registrado Sirius el 15 de febrero?",
            "esperado": "Solo lo registrado hasta el corte, aunque hoy exista más.",
            "tiempo_objetivo": S3.AHORA_DECLARADO,
            "corte_registro": "2026-02-15T00:00:00Z",
        },
    }
    salida: list[dict[str, Any]] = []
    for sufijo, datos in plantilla.items():
        salida.append(
            {
                "sufijo": sufijo,
                "clase": "CANONICA_REQUERIDA",
                "objetivo": datos["objetivo"],
                "fuente_canonica_de_la_rama": datos["fuente"],
                "modo": "M2",
                "consulta": datos["consulta"],
                "proposito": "revisar_historial",
                "permiso": "AUTORIZADO",
                "ambito": FILTRO_BASE_CA47["project_id"],
                "tiempo_objetivo": datos["tiempo_objetivo"],
                "corte_registro": datos["corte_registro"],
                "candidatos_elegibles": cierre[sufijo]["elegibles"],
                "candidatos_prohibidos": cierre[sufijo]["prohibidos"],
                "esperado_rama": datos["esperado"],
                "estado_suficiencia_esperado": "COMPLETO",
                "tolerancia_pendiente": None,
                "cardinalidad_de_la_rama": "EXHAUSTIVA",
                "cierre": {
                    "filtro_base": FILTRO_BASE_CA47,
                    "filtro_temporal": FILTROS_CA47[sufijo],
                    "universo_en_ambito": cierre[sufijo]["universo_en_ambito"],
                    "regla": (
                        "El conjunto esperado es exactamente el conjunto elegible calculado "
                        "sobre el corpus bajo el filtro base y el filtro temporal declarados. "
                        "No hay ningún subconjunto escrito a mano."
                    ),
                },
            }
        )
    return salida


def ramas_v0_3(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Ramas canónicas del v0.2, con las de CA-47 rederivadas del corpus."""
    salida: dict[str, list[dict[str, Any]]] = {}
    for ca, ramas in B2.RAMAS.items():
        if ca == "B04-CA-47":
            continue
        salida[ca] = [dict(r) for r in ramas]
    salida["B04-CA-47"] = _ramas_ca47(cierre_ca47(items))
    return salida


CA_CARDINALIDAD_EXHAUSTIVA_CERRADA: tuple[str, ...] = ("B04-CA-47",)


def colisiones_por_raiz_entre_anclajes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Raíces compartidas por anclajes de proyectos distintos.

    No son un defecto en sí —el canon exige que `presupuesto` aparezca en más
    de un ámbito— pero deben estar **declaradas**: una colisión nueva y no
    declarada cambia silenciosamente el significado de un caso.
    """
    por_raiz: dict[str, set[str]] = {}
    proyecto: dict[str, str] = {}
    for item in items:
        proyecto[item["id"]] = item["project_id"]
        for token in _informativos(item["text"]):
            raiz = _raiz(token)
            if raiz:
                por_raiz.setdefault(raiz, set()).add(item["id"])
    salida: list[dict[str, Any]] = []
    for raiz, ids in sorted(por_raiz.items()):
        proyectos = {proyecto[i] for i in ids}
        if len(ids) > 1 and len(proyectos) > 1:
            salida.append({"raiz": raiz, "items": sorted(ids), "proyectos": sorted(proyectos)})
    return salida


def _huella(datos: Any) -> str:
    return hashlib.sha256(
        json.dumps(datos, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def identidad_de_colecciones(corpus: dict[str, Any]) -> dict[str, Any]:
    """Huella por colección y por elemento: identidad comprobable, no conteo."""
    salida: dict[str, Any] = {}
    for coleccion, clave in (
        ("items", "id"),
        ("mensajes", "id"),
        ("documentos", "id"),
        ("relaciones", "id"),
        ("entidades", "id"),
        ("proyectos", "id"),
    ):
        elementos = corpus[coleccion]
        salida[coleccion] = {
            "conteo": len(elementos),
            "huella_coleccion": _huella(elementos),
            "huella_por_elemento": {e[clave]: _huella(e) for e in elementos},
        }
    return salida


def construir_corpus_conformidad(canon: CS3.Canon) -> dict[str, Any]:
    base = V1.construir_corpus()
    items = list(base["items"]) + B2.ITEMS_ANADIDOS
    memorias = [i for i in items if i["kind"] == "MEMORIA"]
    decisiones = [i for i in items if i["kind"] == "DECISION"]
    corpus: dict[str, Any] = {
        "documento": "Corpus de CONFORMIDAD del benchmark de ADR-002",
        "proposito": (
            "Adjudicar puertas, exactitud, contaminación, negación, ámbito, tiempo, conflicto, "
            "ausencia y explicación. NO se usa para fijar cifras de rendimiento absoluto."
        ),
        "version": S3.VERSION_CORPUS_CONFORMIDAD,
        "version_contrato": S3.VERSION_CONTRATO,
        "estado": S3.ESTADO_NO_CONGELADO,
        "semilla": S3.SEMILLA,
        "generador": "experiments/adr002/benchmark/build_corpus_v0_3.py",
        "hereda_de": "conformance_corpus_v0_2.json",
        "fuente_canonica": {n: h["sha256_real"] for n, h in sorted(canon.huellas.items())},
        "datos_reales": "ninguno; corpus sintético determinista",
        "red": "no utilizada",
        "ahora_declarado": S3.AHORA_DECLARADO,
        "independencia": (
            "El corpus de conformidad y el de rendimiento son artefactos independientes. "
            "Comparten contrato, semilla y vocabulario de estados; el de rendimiento no "
            "reproduce estos anclajes byte a byte y no crea referencias funcionales."
        ),
        "cierre_exhaustivo_ca47": cierre_ca47(items),
        "colisiones_por_raiz_declaradas": colisiones_por_raiz_entre_anclajes(items),
        "conteos": {
            "proyectos": len(base["proyectos"]),
            "entidades": len(base["entidades"]),
            "items": len(items),
            "recuerdos": len(memorias),
            "decisiones": len(decisiones),
            "mensajes": len(base["mensajes"]),
            "documentos": len(base["documentos"]),
            "relaciones": len(base["relaciones"]),
        },
        "proyectos": base["proyectos"],
        "entidades": base["entidades"],
        "items": items,
        "mensajes": base["mensajes"],
        "documentos": base["documentos"],
        "relaciones": base["relaciones"],
    }
    corpus["identidad"] = identidad_de_colecciones(corpus)
    return corpus


# ===========================================================================
# 3. Campos con fuente, sección, estado y justificación (§4.3)
# ===========================================================================

_RX_MODO = re.compile(r"\bM[1-5]\b")
_RX_ETAPA = re.compile(r"\bE[0-5]\b")
_RX_PARADA = re.compile(r"\bS[1-7]\b")


def _texto_canonico(caso: CS3.CasoCanonico) -> str:
    return " ".join([caso.entrada, caso.resultado_esperado, caso.fallo_observable])


def _campo(
    valor: Any, fuente: str, seccion: str, estado: str, justificacion: str
) -> dict[str, Any]:
    return {
        "valor": valor,
        "fuente": fuente,
        "seccion": seccion,
        "estado": estado,
        "justificacion": justificacion,
    }


def _derivado(valor: Any, justificacion: str, seccion: str = "n/a") -> dict[str, Any]:
    return _campo(valor, S3.FUENTE_INSTANCIACION, seccion, "DERIVADO_PROPUESTO", justificacion)


def _canonico_si_literal(
    valor: Any,
    caso: CS3.CasoCanonico,
    patron: re.Pattern[str] | None,
    fuente_alternativa: str,
    justificacion: str,
) -> dict[str, Any]:
    """`CANONICO` solo si el texto canónico del propio caso fija el valor."""
    if valor is None:
        return _derivado(None, justificacion)
    texto = _texto_canonico(caso)
    literal = (valor in texto) if patron is None else (valor in set(patron.findall(texto)))
    if literal:
        return _campo(
            valor,
            S3.FUENTE_CANONICA_CA,
            caso.seccion,
            "CANONICO",
            "el texto canónico del propio caso nombra este valor literalmente",
        )
    return _campo(valor, fuente_alternativa, "n/a", "DERIVADO_PROPUESTO", justificacion)


# --- §4.4 · condición de insuficiencia por rama ------------------------------

TRANSICIONES: dict[str, dict[str, str]] = {
    "E0->E1": {
        "variables": "resultado_estructurado_exacto|criticos_elegibles_pendientes|cardinalidad",
        "predicado": (
            "el conjunto exacto de E0 no satisface la cardinalidad declarada o deja críticos "
            "elegibles sin recuperar"
        ),
        "umbral": (
            "EXACTA: cero elegibles pendientes; ACOTADA: por debajo del límite declarado; "
            "EXHAUSTIVA: cualquier elegible pendiente autoriza expandir"
        ),
    },
    "E1->E2": {
        "variables": "cobertura_lexica_directa|variantes_y_alias_autorizados_no_explorados",
        "predicado": (
            "la coincidencia léxica directa no cubre la petición y quedan variantes o alias "
            "autorizados sin explorar"
        ),
        "umbral": "insuficiencia contrastada frente a la cardinalidad, no preferencia del motor",
    },
    "E2->E3": {
        "variables": "suficiencia_tras_expansion_lexica|espacio_autorizado_no_agotado",
        "predicado": (
            "tras la expansión léxica la suficiencia sigue sin alcanzarse y el espacio "
            "autorizado no está agotado"
        ),
        "umbral": "G1-G12 ya aplicadas; ninguna señal blanda rescata un elemento excluido",
    },
    "E3->E4": {
        "variables": "ausencia_de_resultado_utilizable|evidencia_no_canonica_atribuible",
        "predicado": (
            "no hay resultado utilizable y existe evidencia no canónica atribuible que el "
            "propósito activo autoriza mostrar"
        ),
        "umbral": "el fallback atribuye y no convierte la evidencia en conocimiento confirmado",
    },
    "E4->E5": {
        "variables": "insuficiencia_persistente_tras_fallback|ultimo_espacio_autorizado",
        "predicado": "la insuficiencia persiste tras el fallback atribuido",
        "umbral": "último espacio autorizado; la parada se declara y se explica",
    },
}

_ORDEN_ETAPAS = ("E0", "E1", "E2", "E3", "E4", "E5")


def _insuficiencia_de_rama(rama: str, etapa: str | None, motivo_no_aplica: str | None) -> Any:
    if motivo_no_aplica is not None:
        return {"rama": rama, "aplica": "NO_APLICA", "razon": motivo_no_aplica}
    if etapa is None:
        return {
            "rama": rama,
            "aplica": "NO_APLICA",
            "razon": "la instanciación no declara etapa de resolución para esta rama",
        }
    if etapa == "E0":
        return {
            "rama": rama,
            "aplica": "NO_APLICA",
            "razon": (
                "la rama resuelve en E0: no existe transición posterior que autorizar, y una "
                "expansión sería una decisión libre prohibida por B04-RF-14"
            ),
        }
    salida: list[dict[str, str]] = []
    for actual, siguiente in itertools.pairwise(_ORDEN_ETAPAS):
        if _ORDEN_ETAPAS.index(actual) >= _ORDEN_ETAPAS.index(etapa):
            break
        datos = TRANSICIONES[f"{actual}->{siguiente}"]
        salida.append(
            {
                "etapa_actual": actual,
                "variables_observadas": datos["variables"].split("|"),
                "predicado": datos["predicado"],
                "umbral_o_condicion_logica": datos["umbral"],
                "siguiente_etapa_permitida": siguiente,
                "fuente": "B04 v1.0 APROBADO §15.1 y §15.2 · B04-RF-14 y B04-RF-16",
                "estado": "DERIVADO_PROPUESTO",
            }
        )
    return {"rama": rama, "aplica": "APLICA", "transiciones": salida}


def condicion_insuficiencia(
    etapa: str | None, ramas: list[dict[str, Any]], sin_vocabulario: bool
) -> list[Any]:
    """Estructura ejecutable por rama; nunca una frase genérica ni una lista vacía."""
    motivo = None
    if sin_vocabulario:
        motivo = (
            "el caso es un arnés de equivalencia entre dos realizaciones, no una consulta de "
            "recuperación: el canon no le asigna etapa de expansión ni parada"
        )
    if not ramas:
        return [_insuficiencia_de_rama("CASO_BASE", etapa, motivo)]
    return [_insuficiencia_de_rama(r["sufijo"], r.get("etapa", etapa), motivo) for r in ramas]


# --- §7.2 · tolerancia frente a valor pendiente ------------------------------

REGLA_TOLERANCIA: dict[str, str] = {
    S3.TOL_ORDEN_EQUIVALENCIA: (
        "Orden y equivalencia B04/B05: mismos críticos, estados, razones y dependencias; "
        "el orden no crítico solo puede variar dentro de una clase de equivalencia prefijada."
    ),
    S3.TOL_BANDA_DIFERENCIAL: (
        "Banda de texto, estado, conteo y tiempo entre una ausencia real y un resultado no "
        "reportable: la salida externa debe ser indistinguible dentro de la banda."
    ),
}
TOLERANCIA_EXACTA = (
    "Conjunto elegible, estados, criticidad y suficiencia exactamente equivalentes; "
    "orden total cuando la instanciación lo declara."
)


def _tolerancias_del_caso(identificador: str) -> dict[str, Any]:
    tolerancia = S3.TOLERANCIA_POR_CASO.get(identificador)
    if tolerancia is None:
        return _campo(
            {
                "tolerancia_id": S3.TOL_BANDA_DIFERENCIAL,
                "valor_pendiente_en": None,
                "regla": TOLERANCIA_EXACTA,
                "condicion_aplicada": "ADR002-TOL-201 condición (1) · equivalencia exacta",
            },
            "SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md",
            "ADR002-TOL-201",
            "DERIVADO_PROPUESTO",
            "la regla de equivalencia existe y su valor no depende de ninguna medición pendiente",
        )
    return _campo(
        {
            "tolerancia_id": tolerancia,
            "valor_pendiente_en": S3.TOL_VALOR_PENDIENTE,
            "regla": REGLA_TOLERANCIA[tolerancia],
            "condicion_aplicada": (
                "la regla está identificada y es canónica; lo que falta es su VALOR, que "
                f"{S3.TOL_VALOR_PENDIENTE} todavía no fija"
            ),
        },
        "SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md",
        f"{tolerancia} / {S3.TOL_VALOR_PENDIENTE}",
        "PENDIENTE_TOL209",
        "no se inventa banda: se distingue la tolerancia aplicable del valor todavía pendiente",
    )


# ===========================================================================
# 4. Casos funcionales de nivel 1
# ===========================================================================


def _tipo_orden(orden: list[str] | None) -> str:
    if orden is None:
        return "CONJUNTO"
    return "VACIO" if not orden else "ORDEN_TOTAL"


def _trazabilidad(fila: dict[str, Any], identificador: str) -> dict[str, Any]:
    asignaciones = CS3.asignaciones_canonicas_por_ca().get(
        identificador, {"red": [], "metricas": [], "familias": [], "metricas_externas": []}
    )
    return {
        "requisito_verificado": fila["rf"],
        "traza_red_canonica_anexo_b": asignaciones["red"],
        "traza_red_adicional_derivada": sorted(set(fila["red"]) - set(asignaciones["red"])),
        "metrica_canonica_anexo_b": asignaciones["metricas"],
        "metrica_canonica_externa_anexo_b": asignaciones["metricas_externas"],
        "metrica_adicional_derivada": sorted(set(fila["m"]) - set(asignaciones["metricas"])),
        "familia_canonica_anexo_b": asignaciones["familias"],
        "familia_adicional_derivada": sorted(set(fila["fam"]) - set(asignaciones["familias"])),
        "fuente_canonica": S3.FUENTE_ANEXO_B,
        "fuente_adicional": S3.FUENTE_INSTANCIACION,
        "nota": (
            "Las asignaciones canónicas del Anexo B no se sustituyen. Las métricas canónicas de "
            "otros bloques se conservan expresamente y no se filtran en silencio."
        ),
    }


def _ficha_pdp7(
    fila: dict[str, Any],
    caso: CS3.CasoCanonico,
    canon: CS3.Canon,
    ramas: list[dict[str, Any]],
    sin_vocabulario: bool,
) -> dict[str, Any]:
    ident = caso.identificador
    asignaciones = CS3.asignaciones_canonicas_por_ca().get(ident, {})
    familias = sorted(set(fila["fam"]) | set(asignaciones.get("familias", [])))
    modos = sorted({fila["modo"]} | {r["modo"] for r in ramas})
    texto = _texto_canonico(caso)
    return {
        "id_y_familia": _derivado(
            {"id": ident, "familias": familias},
            "el canon fija el ID; la familia procede del Anexo B y de la instanciación",
            S3.FUENTE_PDP7,
        ),
        "objetivo": _derivado(
            f"Demostrar o romper: {caso.resultado_esperado}",
            "derivado del resultado esperado canónico; el canon no redacta objetivos de prueba",
            caso.seccion,
        ),
        "entrada": _campo(
            caso.entrada,
            S3.FUENTE_CANONICA_CA,
            caso.seccion,
            "CANONICO",
            "columna «Entrada» del propio caso, carácter a carácter",
        ),
        "unidad_de_trabajo": _derivado(
            {
                "objetivo": f"Adjudicar {ident} sobre el corpus de conformidad congelable.",
                "inicio": "alta de la petición de recuperación instanciada",
                "cierre": "adjudicación registrada de todas las ramas del caso",
            },
            "unidad declarada por el arnés; el canon no la fija para este caso",
            S3.FUENTE_PDP7,
        ),
        "operacion_y_modo": (
            _campo(
                {"modos": modos, "operacion": "recuperacion_b04"},
                S3.FUENTE_CANONICA_CA,
                caso.seccion,
                "CANONICO",
                "el texto canónico del caso nombra literalmente "
                f"{sorted(set(_RX_MODO.findall(texto)))}",
            )
            if _RX_MODO.findall(texto)
            else _derivado(
                {"modos": modos, "operacion": "recuperacion_b04"},
                "el canon no nombra ningún modo en este caso: la elección es de instanciación",
            )
        ),
        "ambito": _derivado(
            sorted({fila["ambito"]} | {r["ambito"] for r in ramas if r["ambito"]}),
            "ámbito sintético del corpus; el canon no nombra proyectos",
        ),
        "tiempo_y_corte": _derivado(
            {
                "tiempo_objetivo": fila["t_obj"],
                "corte_registro": fila["corte"],
                "por_rama": [
                    {
                        "rama": r["sufijo"],
                        "tiempo_objetivo": r["tiempo_objetivo"],
                        "corte_registro": r["corte_registro"],
                    }
                    for r in ramas
                ],
            },
            "fechas sintéticas declaradas; nunca el reloj de ejecución",
        ),
        "referencia": _derivado(
            {
                "resultado_esperado_canonico": caso.resultado_esperado,
                "elegibles": fila["eleg"],
                "prohibidos": fila["prohib"],
                "orden": fila["orden"],
                "tipo_orden": _tipo_orden(fila["orden"]),
            },
            "el esperado es canónico; los identificadores son sintéticos del corpus",
        ),
        "criticidad": _derivado(
            fila["crit"], "adjudicación de prueba del corpus; B04 §6 cuarto origen de criticidad"
        ),
        "tolerancias": _tolerancias_del_caso(ident),
        "senales_observables": _derivado(
            [
                "conjunto de ids elegibles devueltos",
                "ids prohibidos que aparecieron",
                "estado interno de suficiencia adjudicado",
                "estado externo emitido",
                "modo adjudicado y puertas aplicadas",
                "etapas recorridas y parada",
                "razón por resultado y razón de orden",
            ],
            "señales que el arnés puede observar sin revelar contenido protegido",
        ),
        "fallo": _campo(
            caso.fallo_observable,
            S3.FUENTE_CANONICA_CA,
            caso.seccion,
            "CANONICO",
            "columna «Fallo observable» del propio caso, carácter a carácter",
        ),
        "evidencia": _derivado(
            "Registro por rama: petición efectiva, plan, puertas, etapas, parada, suficiencia, "
            "resultado obtenido y esperado, veredicto y razón. No altera la referencia.",
            "el PDP §7 exige evidencia posterior sin alterar la referencia; el contenido lo\n"
            "aporta el arnés",
        ),
        "resultado": _derivado(
            None, "se rellena tras adjudicar; hoy no hay ninguna ejecución", S3.FUENTE_PDP7
        ),
        S3.CAMPO_INSUFICIENCIA: _derivado(
            condicion_insuficiencia(fila["etapa"], ramas, sin_vocabulario),
            "Especificación de benchmark §5 campo 12: condición que autoriza cada transición",
        ),
    }


def _caso_nivel1(
    fila: dict[str, Any], canon: CS3.Canon, ramas_por_ca: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    ident = fila["ca"]
    caso = canon.casos[ident]
    numero = int(ident.rsplit("-", 1)[1])
    ramas = ramas_por_ca.get(ident, [])
    sin_vocabulario = ident in B2.CA_SIN_VOCABULARIO_DE_PARADA
    cardinalidad = None if sin_vocabulario else fila["card"]
    if ident in CA_CARDINALIDAD_EXHAUSTIVA_CERRADA:
        cardinalidad = "EXHAUSTIVA"
    parada = None if sin_vocabulario else fila["parada"]
    return {
        "id": f"N1-{numero:02d}",
        "nivel": 1,
        "clase": "CASO_FUNCIONAL",
        "identificador_canonico": ident,
        "canonico": {
            "fuente": S3.FUENTE_CANONICA_CA,
            "seccion_exacta": caso.seccion,
            "riesgo": caso.riesgo,
            "entrada": caso.entrada,
            "resultado_esperado": caso.resultado_esperado,
            "fallo_observable": caso.fallo_observable,
            "modificable": False,
        },
        "instanciacion": {
            "fuente": S3.FUENTE_INSTANCIACION,
            "estado": S3.ESTADO_NO_CONGELADO,
            "consulta": _derivado(fila["consulta"], "consulta sintética instanciada"),
            "modo": _canonico_si_literal(
                fila["modo"],
                caso,
                _RX_MODO,
                "B04 v1.0 APROBADO §5",
                "modo elegido por la instanciación",
            ),
            "proposito": _derivado(fila["proposito"], "propósito autorizado del arnés"),
            "permiso": _derivado(fila["permiso"], "permiso declarado por el arnés"),
            "ambito": _derivado(fila["ambito"], "ámbito sintético del corpus"),
            "tiempo_objetivo": _derivado(fila["t_obj"], "fecha declarada, no el reloj"),
            "corte_registro": _derivado(fila["corte"], "fecha declarada, no el reloj"),
            "cardinalidad": _canonico_si_literal(
                cardinalidad,
                caso,
                None,
                S3.FUENTE_CARDINALIDAD_B04,
                "elección de instanciación; la regla canónica aplicable es §15.2: si la "
                "instanciación es EXHAUSTIVA, S1 está prohibida",
            ),
            "etapa": _canonico_si_literal(
                fila["etapa"],
                caso,
                _RX_ETAPA,
                "B04 v1.0 APROBADO §15.1",
                "etapa elegida por la instanciación",
            ),
            "parada": _canonico_si_literal(
                parada,
                caso,
                _RX_PARADA,
                S3.FUENTE_PARADAS_B04,
                "parada elegida por la instanciación",
            ),
            "orden": _derivado(
                {"valor": fila["orden"], "tipo": _tipo_orden(fila["orden"])},
                "ids sintéticos; el canon no fija secuencia",
            ),
            "elegibles": _derivado(fila["eleg"], "ids sintéticos del corpus"),
            "prohibidos": _derivado(fila["prohib"], "ids sintéticos del corpus"),
            "explicacion_esperada": _derivado(
                fila["expl"], "explicación mínima exigida por B04-RF-28"
            ),
            "ramas": ramas,
        },
        "trazabilidad": _trazabilidad(fila, ident),
        "ficha_pdp_7": _ficha_pdp7(fila, caso, canon, ramas, sin_vocabulario),
        "t0": dict(T0_NO_MEDIDO),
        "datos_sinteticos": fila["datos"],
        "corpus": "conformidad",
    }


# --- PDP-CA funcionales (§4.2) ----------------------------------------------

INSTANCIACION_PDP_FUNCIONAL: dict[str, dict[str, Any]] = {
    "PDP-CA-09": {
        "objetivo": (
            "Que dos consumidores con librería específica compartida no cuenten como "
            "independientes."
        ),
        "consulta": (
            "¿El contrato de salida se reproduce con dos consumidores realmente independientes?"
        ),
        "senal": "inventario de dependencias de cada implementación del puerto",
        "modo": "M1",
        "etapa": "E1",
        "cardinalidad": "EXACTA",
        "parada": "S1",
        "criticidad": "CRITICO",
    },
    "PDP-CA-22": {
        "objetivo": (
            "Que dos consumidores con el mismo intérprete y distinta configuración cuenten "
            "como uno."
        ),
        "consulta": (
            "¿Dos consumidores con el mismo intérprete y distinta configuración son uno solo?"
        ),
        "senal": "intérprete, versión y configuración de cada consumidor",
        "modo": "M1",
        "etapa": "E1",
        "cardinalidad": "EXACTA",
        "parada": "S1",
        "criticidad": "CRITICO",
    },
}


def _caso_pdp_funcional(
    pdp: str, orden: int, canon: CS3.Canon, anclaje: dict[str, list[str]]
) -> dict[str, Any]:
    caso = canon.casos_pdp[pdp]
    extra = INSTANCIACION_PDP_FUNCIONAL[pdp]
    ficha = {
        "id_y_familia": _derivado(
            {"id": pdp, "familias": anclaje["familias"]},
            "el ID es canónico; la familia procede del Anexo B",
            S3.FUENTE_PDP7,
        ),
        "objetivo": _derivado(
            extra["objetivo"], "derivado del resultado esperado canónico", S3.FUENTE_PDP9
        ),
        "entrada": _campo(
            caso.entrada_adversarial,
            S3.FUENTE_PDP9,
            "PDP §9",
            "CANONICO",
            "columna «Entrada adversarial» del propio caso, carácter a carácter",
        ),
        "unidad_de_trabajo": _derivado(
            {
                "objetivo": f"Adjudicar {pdp} sobre el registro de independencia de consumidores.",
                "inicio": "declaración del inventario de consumidores",
                "cierre": "adjudicación registrada del recuento de consumidores independientes",
            },
            "unidad declarada por el arnés",
            S3.FUENTE_PDP7,
        ),
        "operacion_y_modo": _derivado(
            {"modos": [extra["modo"]], "operacion": "recuperacion_b04"},
            "el canon no nombra ningún modo en este caso: la elección es de instanciación",
        ),
        "ambito": _derivado(["PRJ-ALFA"], "ámbito sintético del corpus"),
        "tiempo_y_corte": _derivado(
            {"tiempo_objetivo": S3.AHORA_DECLARADO, "corte_registro": None, "por_rama": []},
            "fecha declarada, no el reloj",
        ),
        "referencia": _derivado(
            {
                "resultado_esperado_canonico": caso.resultado_esperado,
                "elegibles": [],
                "prohibidos": [],
                "orden": None,
                "tipo_orden": "CONJUNTO",
                "senal_observable": extra["senal"],
            },
            "el esperado es canónico; la señal observable es del arnés",
        ),
        "criticidad": _derivado(extra["criticidad"], "adjudicación de prueba del corpus"),
        "tolerancias": _tolerancias_del_caso("B04-CA-39"),
        "senales_observables": _derivado(
            [extra["senal"], "recuento de consumidores declarados independientes"],
            "señales del registro de ejecución del arnés",
        ),
        "fallo": _campo(
            caso.resultado_esperado,
            S3.FUENTE_PDP9,
            "PDP §9",
            "CANONICO",
            "el resultado esperado canónico define el fallo por negación",
        ),
        "evidencia": _derivado(
            "Inventario de dependencias, intérprete, versión y configuración de cada consumidor.",
            "el PDP §7 exige evidencia posterior sin alterar la referencia",
        ),
        "resultado": _derivado(
            None, "se rellena tras adjudicar; hoy no hay ninguna ejecución", S3.FUENTE_PDP7
        ),
        S3.CAMPO_INSUFICIENCIA: _derivado(
            condicion_insuficiencia(extra["etapa"], [], False),
            "Especificación de benchmark §5 campo 12",
        ),
    }
    return {
        "id": f"N1-PDP-{orden:02d}",
        "nivel": 1,
        "clase": "CASO_FUNCIONAL",
        "identificador_canonico": pdp,
        "canonico": {
            "fuente": S3.FUENTE_PDP9,
            "seccion_exacta": "PDP §9",
            "entrada_adversarial": caso.entrada_adversarial,
            "resultado_esperado": caso.resultado_esperado,
            "modificable": False,
        },
        "anclaje_canonico": {
            "criterio": "ANEXO_B_RED_CON_CASO_O_METRICA_DE_B04",
            "red": anclaje["red"],
            "casos_b04": anclaje["casos_b04"],
            "metricas_b04": anclaje["metricas"],
            "metricas_externas": anclaje["metricas_externas"],
            "familias": anclaje["familias"],
        },
        "instanciacion": {
            "fuente": S3.FUENTE_INSTANCIACION,
            "estado": S3.ESTADO_NO_CONGELADO,
            "consulta": _derivado(extra["consulta"], "consulta sintética instanciada"),
            "modo": _derivado(extra["modo"], "modo elegido por la instanciación"),
            "proposito": _derivado("verificar_fuente", "propósito autorizado del arnés"),
            "permiso": _derivado("AUTORIZADO", "permiso declarado por el arnés"),
            "ambito": _derivado("PRJ-ALFA", "ámbito sintético del corpus"),
            "tiempo_objetivo": _derivado(S3.AHORA_DECLARADO, "fecha declarada, no el reloj"),
            "corte_registro": _derivado(None, "el caso no declara corte de registro"),
            "cardinalidad": _derivado(
                extra["cardinalidad"], "elección de instanciación; el canon no fija cardinalidad"
            ),
            "etapa": _derivado(extra["etapa"], "etapa elegida por la instanciación"),
            "parada": _derivado(extra["parada"], "parada elegida por la instanciación"),
            "orden": _derivado({"valor": None, "tipo": "CONJUNTO"}, "el canon no fija secuencia"),
            "elegibles": _derivado([], "el caso adjudica sobre el registro, no sobre contenido"),
            "prohibidos": _derivado([], "el caso adjudica sobre el registro, no sobre contenido"),
            "explicacion_esperada": _derivado(
                "por qué cada consumidor cuenta o no cuenta como independiente",
                "explicación mínima exigida por B04-RF-28",
            ),
            "ramas": [],
        },
        "ficha_pdp_7": ficha,
        "t0": dict(T0_NO_MEDIDO),
        "corpus": "conformidad",
    }


# --- §4.2 · reglas canónicas de protocolo del arnés --------------------------

REGLAS_DE_ARNES: dict[str, dict[str, str]] = {
    "PDP-CA-02": {
        "fuente_pdp": "PDP §9 · PDP-CA-02",
        "regla_de_ejecucion": (
            "La referencia de cada caso se congela y se sella antes de observar ninguna salida. "
            "Ninguna referencia puede editarse después de ver un resultado."
        ),
        "evidencia_requerida": "huella de la referencia antes y después de cada ejecución",
        "consecuencia": (
            "la ejecución queda invalidada y debe repetirse desde la referencia sellada"
        ),
        "estado_aplicabilidad": "APLICABLE_TRAS_CONGELACION",
        "regla_que_lo_importa": (
            "Registro de Tolerancias v0.4 §9 regla 1 y Especificación de benchmark §3 principio 2"
        ),
    },
    "PDP-CA-03": {
        "fuente_pdp": "PDP §9 · PDP-CA-03",
        "regla_de_ejecucion": (
            "Una repetición solo es válida si declara un cambio o un defecto documentado. "
            "Repetir hasta obtener un resultado favorable está prohibido."
        ),
        "evidencia_requerida": "registro de repeticiones con su causa declarada",
        "consecuencia": "la repetición no computa y la serie de medición queda invalidada",
        "estado_aplicabilidad": "APLICABLE_TRAS_CONGELACION",
        "regla_que_lo_importa": "Protocolo de medición v0.1 §6.5, §6.6 y prohibición 8",
    },
    "PDP-CA-06": {
        "fuente_pdp": "PDP §9 · PDP-CA-06",
        "regla_de_ejecucion": (
            "La ficha del candidato se congela antes de la primera ejecución. Cambiar el "
            "candidato durante la serie invalida la serie completa."
        ),
        "evidencia_requerida": "huella de la ficha de candidato referenciada por cada medición",
        "consecuencia": "toda medición posterior al cambio queda invalidada",
        "estado_aplicabilidad": "APLICABLE_TRAS_CONGELACION",
        "regla_que_lo_importa": (
            "ADR002-TOL-210 · punto de congelación antes de la primera ejecución"
        ),
    },
    "PDP-CA-16": {
        "fuente_pdp": "PDP §9 · PDP-CA-16",
        "regla_de_ejecucion": (
            "Toda evidencia debe reproducir versión de corpus, commit, esquema y protocolo. "
            "Una evidencia que no los reproduce no cuenta."
        ),
        "evidencia_requerida": (
            "versión de corpus, commit, head de esquema y protocolo por registro"
        ),
        "consecuencia": "la evidencia se descarta y el caso queda sin adjudicar",
        "estado_aplicabilidad": "APLICABLE_TRAS_CONGELACION",
        "regla_que_lo_importa": "Protocolo de medición v0.1 §7 · registro obligatorio",
    },
    "PDP-CA-17": {
        "fuente_pdp": "PDP §9 · PDP-CA-17",
        "regla_de_ejecucion": (
            "Cambiar una tolerancia después de observar la salida invalida la ejecución. "
            "La versión del Registro de Tolerancias se sella con cada medición."
        ),
        "evidencia_requerida": "versión del Registro de Tolerancias y de la ficha en cada medición",
        "consecuencia": "la ejecución queda invalidada para todas las cifras afectadas",
        "estado_aplicabilidad": "APLICABLE_TRAS_CONGELACION",
        "regla_que_lo_importa": "Registro de Tolerancias v0.4 §9 reglas 1 y 10",
    },
    "PDP-CA-18": {
        "fuente_pdp": "PDP §9 · PDP-CA-18",
        "regla_de_ejecucion": (
            "Un caso marcado NO EVALUABLE permanece en el denominador. El denominador no se "
            "reduce para mejorar un porcentaje."
        ),
        "evidencia_requerida": "denominador declarado frente a casos adjudicados",
        "consecuencia": "la cifra publicada se recalcula con el denominador completo",
        "estado_aplicabilidad": "APLICABLE_TRAS_CONGELACION",
        "regla_que_lo_importa": "ADR002-TOL-107 · salida NO EVALUABLE permanece en el denominador",
    },
}


def construir_reglas_de_arnes(canon: CS3.Canon) -> dict[str, Any]:
    reglas: list[dict[str, Any]] = []
    for pdp in S3.PDP_CA_REGLAS_DE_ARNES:
        caso = canon.casos_pdp[pdp]
        datos = REGLAS_DE_ARNES[pdp]
        reglas.append(
            {
                "identificador_canonico": pdp,
                "clase": "REGLA_DE_PROTOCOLO_DEL_ARNES",
                "texto_canonico": {
                    "entrada_adversarial": caso.entrada_adversarial,
                    "resultado_esperado": caso.resultado_esperado,
                    "modificable": False,
                },
                "fuente_pdp": datos["fuente_pdp"],
                "regla_que_lo_importa": datos["regla_que_lo_importa"],
                "regla_de_ejecucion": datos["regla_de_ejecucion"],
                "evidencia_requerida": datos["evidencia_requerida"],
                "consecuencia": datos["consecuencia"],
                "estado_aplicabilidad": datos["estado_aplicabilidad"],
            }
        )
    return {
        "documento": "Reglas canónicas de protocolo del arnés de ADR-002",
        "version": "0.1",
        "version_contrato": S3.VERSION_CONTRATO,
        "estado": S3.ESTADO_NO_CONGELADO,
        "fuente": S3.FUENTE_PDP9,
        "regla_de_separacion": (
            "Estas seis reglas gobiernan CÓMO se ejecuta y se registra el benchmark. No son "
            "consultas de recuperación, no tienen conjunto elegible, no tienen etapa ni parada "
            "y no reciben previsión frente a T0. Ninguna de ellas es un caso funcional de "
            "nivel 1: solo PDP-CA-09 y PDP-CA-22 lo son, por su anclaje canónico vía el "
            "Anexo B / RED-017."
        ),
        "campos_prohibidos": list(S3.CAMPOS_PROHIBIDOS_EN_REGLA),
        "conteos": {"reglas": len(reglas)},
        "reglas": reglas,
    }


# ===========================================================================
# 5. Corpus de rendimiento v0.2 · sintético, no degenerado (§6)
# ===========================================================================

# Vocabulario disjunto del léxico protegido del corpus de conformidad. La
# disyunción se comprueba por token, sufijo y raíz: no se declara, se calcula.

SUSTANTIVOS_POR_FAMILIA: dict[str, tuple[str, ...]] = {
    "astronomia": (
        "nebulosa",
        "cometa",
        "eclipse",
        "satelite",
        "galaxia",
        "meteorito",
        "asteroide",
        "crater",
        "penumbra",
        "cenit",
        "ocaso",
        "alba",
        "cielo",
    ),
    "marina": (
        "arrecife",
        "marea",
        "coral",
        "medusa",
        "plancton",
        "boya",
        "muelle",
        "quilla",
        "dique",
        "alga",
        "vela",
        "remo",
        "delfin",
        "orilla",
        "duna",
        "estuario",
        "laguna",
    ),
    "mineral": (
        "basalto",
        "cuarzo",
        "granito",
        "magma",
        "glaciar",
        "arcilla",
        "pizarra",
        "caliza",
        "cantera",
        "guijarro",
        "grava",
        "arena",
        "limo",
        "yeso",
        "risco",
    ),
    "panaderia": (
        "levadura",
        "hogaza",
        "harina",
        "canela",
        "comino",
        "azafran",
        "romero",
        "tomillo",
        "almendra",
        "miel",
        "nuez",
        "pulpa",
        "masa",
        "horno",
    ),
    "musica": (
        "arpegio",
        "timbal",
        "flauta",
        "acorde",
        "melodia",
        "octava",
        "ritmo",
        "bemol",
        "laud",
        "partitura",
        "sonata",
        "octeto",
        "coro",
    ),
    "textil": (
        "urdimbre",
        "telar",
        "brocado",
        "hilatura",
        "sarga",
        "algodon",
        "fieltro",
        "seda",
        "lana",
        "lino",
        "aguja",
        "carrete",
        "bobina",
        "pliegue",
        "madeja",
        "ovillo",
        "trama",
        "peine",
        "carda",
        "lanzadera",
        "husillo",
    ),
    "meteorologia": (
        "nieve",
        "niebla",
        "rocio",
        "escarcha",
        "bruma",
        "llovizna",
        "granizo",
        "relampago",
        "trueno",
        "viento",
        "brisa",
        "racha",
    ),
    "botanica": (
        "musgo",
        "liquen",
        "helecho",
        "junco",
        "cardo",
        "brezo",
        "retama",
        "enebro",
        "abeto",
        "alerce",
        "olmo",
        "sauce",
        "fresno",
        "chopo",
        "aliso",
        "acebo",
        "tejo",
        "hiedra",
        "zarza",
        "espiga",
        "gavilla",
    ),
    "alfareria": (
        "alfar",
        "fragua",
        "yunque",
        "molde",
        "crisol",
        "fuelle",
        "tamiz",
        "criba",
        "cedazo",
        "taller",
        "mesa",
    ),
}
FAMILIAS_TEMATICAS: tuple[str, ...] = tuple(SUSTANTIVOS_POR_FAMILIA)


# Las familias se intercalan: así los rangos —y con ellos los pesos de Zipf— no
# quedan agrupados por tema y ningún tema domina el vocabulario.
def _intercalar(grupos: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    salida: list[str] = []
    for posicion in range(max(len(v) for v in grupos.values())):
        for palabras in grupos.values():
            if posicion < len(palabras) and palabras[posicion] not in salida:
                salida.append(palabras[posicion])
    return tuple(salida)


SUSTANTIVOS: tuple[str, ...] = _intercalar(SUSTANTIVOS_POR_FAMILIA)
_FAMILIA_DE_SUSTANTIVO = {
    palabra: familia
    for familia, palabras in SUSTANTIVOS_POR_FAMILIA.items()
    for palabra in palabras
}

VERBOS: tuple[str, ...] = (
    "reposa",
    "germina",
    "florece",
    "asciende",
    "desciende",
    "brilla",
    "vibra",
    "resuena",
    "cristaliza",
    "sedimenta",
    "madura",
    "fermenta",
    "templa",
    "afina",
    "pule",
    "talla",
    "teje",
    "hila",
    "cose",
    "borda",
    "seca",
    "enfria",
    "calienta",
    "moldea",
    "gira",
    "flota",
    "hunde",
    "arrastra",
    "empuja",
    "brota",
    "serpea",
    "ondula",
    "destella",
    "titila",
    "susurra",
    "cruje",
    "tintinea",
    "rebosa",
    "gotea",
    "amasa",
    "tamiza",
    "funde",
    "forja",
    "lamina",
    "estira",
    "riza",
    "peina",
    "urde",
    "enhebra",
    "rueda",
    "salta",
    "trepa",
    "reflejan",
    "reposan",
    "florecen",
    "vibran",
    "maduran",
    "brillan",
)
ADJETIVOS: tuple[str, ...] = (
    "lento",
    "rapido",
    "suave",
    "aspero",
    "denso",
    "ligero",
    "claro",
    "oscuro",
    "humedo",
    "seco",
    "tibio",
    "calido",
    "frio",
    "profundo",
    "somero",
    "quebradizo",
    "elastico",
    "opaco",
    "translucido",
    "rugoso",
    "pulido",
    "irregular",
    "uniforme",
    "compacto",
    "ambar",
    "cobrizo",
    "verdoso",
    "azulado",
    "grisaceo",
    "nacarado",
    "mate",
    "brillante",
    "poroso",
    "fibroso",
    "quebrado",
    "liso",
)
COMPLEMENTOS: tuple[str, ...] = (
    "en la orilla",
    "bajo el cielo",
    "junto al horno",
    "sobre el telar",
    "entre las dunas",
    "cerca del dique",
    "tras la bruma",
    "al pie del glaciar",
    "en el taller",
    "sobre la mesa",
    "entre las olas",
    "en la cantera",
    "junto al estuario",
    "bajo el granizo",
    "entre los juncos",
)

ESTRUCTURAS: tuple[tuple[str, str], ...] = (
    ("DECLARATIVA", "{s1} {v1} {c1}"),
    ("DECLARATIVA_ADJETIVADA", "{s1}, {a1} y {a2}, {v1} {c1}"),
    ("NEGATIVA", "{s1} no {v1} {c1}"),
    ("INTERROGATIVA", "¿{s1} {v1} {c1}?"),
    ("CONDICIONAL", "si {s1} {v1}, {s2} {v2} {c1}"),
    ("TEMPORAL_SUBORDINADA", "mientras {s1} {v1}, {s2} {v2} {a1}"),
    ("ENUMERATIVA", "{s1}, {s2} y {s3} {v1} {c1}"),
    ("COMPARATIVA", "{s1} {v1} mas {a1} que {s2}"),
    ("CAUSAL", "{s1} {v1} {c1} porque {s2} {v2}"),
    ("CONCESIVA", "aunque {s1} {v1}, {s2} {v2} {c1}"),
    ("PASIVA_REFLEJA", "se {v1} {s1} {c1}"),
    ("IMPERSONAL", "hay {s1} {a1} {c1}"),
)


def _pesos_zipf(n: int, q: float = 5.0) -> list[float]:
    """Zipf-Mandelbrot: peso del rango ``r`` proporcional a ``1/(r+q)``."""
    return [1.0 / (r + q) for r in range(1, n + 1)]


class GeneradorSintetico:
    """Genera texto sintético con vocabulario aproximadamente Zipf.

    El rango de cada palabra es su posición en la lista global; el peso es
    `1/(rango+q)`. No hay plantilla repetida ni número de secuencia: la
    variedad procede de doce estructuras gramaticales combinadas con un
    vocabulario amplio muestreado por rango.
    """

    def __init__(self, semilla: int) -> None:
        self.rng = random.Random(semilla)
        self.orden_global: list[str] = []
        for grupo in (SUSTANTIVOS, VERBOS, ADJETIVOS):
            for palabra in grupo:
                if palabra not in self.orden_global:
                    self.orden_global.append(palabra)
        rango = {palabra: i + 1 for i, palabra in enumerate(self.orden_global)}
        self.clases: dict[str, tuple[list[str], list[float]]] = {}
        for nombre, grupo in (("s", SUSTANTIVOS), ("v", VERBOS), ("a", ADJETIVOS)):
            palabras = sorted(set(grupo), key=lambda p: rango[p])
            pesos = [1.0 / (rango[p] + 5.0) for p in palabras]
            self.clases[nombre] = (palabras, pesos)
        self.complementos = list(COMPLEMENTOS)

    def _elegir(self, clase: str) -> str:
        palabras, pesos = self.clases[clase]
        return self.rng.choices(palabras, weights=pesos, k=1)[0]

    def clausula(self) -> tuple[str, str, str]:
        nombre, plantilla = self.rng.choice(ESTRUCTURAS)
        sustantivos = [self._elegir("s") for _ in range(3)]
        texto = plantilla.format(
            s1=sustantivos[0],
            s2=sustantivos[1],
            s3=sustantivos[2],
            v1=self._elegir("v"),
            v2=self._elegir("v"),
            a1=self._elegir("a"),
            a2=self._elegir("a"),
            c1=self.rng.choice(self.complementos),
        )
        return nombre, texto, _FAMILIA_DE_SUSTANTIVO[sustantivos[0]]

    def texto(self, clausulas: int | None = None) -> tuple[str, list[str], str]:
        n = (
            clausulas
            if clausulas is not None
            else self.rng.choices([1, 2, 3, 4], weights=[0.34, 0.33, 0.22, 0.11], k=1)[0]
        )
        partes: list[str] = []
        estructuras: list[str] = []
        familias: list[str] = []
        for _ in range(n):
            nombre, texto, familia = self.clausula()
            partes.append(texto)
            estructuras.append(nombre)
            familias.append(familia)
        frase = "; ".join(partes)
        frase = frase[0].upper() + frase[1:]
        if not frase.endswith(("?", ".")):
            frase += "."
        return frase, estructuras, familias[0]


_INICIO = date.fromisoformat(S3.RENDIMIENTO_FECHA_INICIO)
_FIN = date.fromisoformat(S3.RENDIMIENTO_FECHA_FIN)
_DIAS = (_FIN - _INICIO).days


def _fecha(rng: random.Random, desplazamiento: int | None = None) -> str:
    dias = desplazamiento if desplazamiento is not None else rng.randrange(_DIAS + 1)
    return (_INICIO + timedelta(days=dias)).isoformat() + "T00:00:00Z"


def _reparto(rng: random.Random, opciones: tuple[tuple[str, float], ...]) -> str:
    valores = [v for v, _ in opciones]
    pesos = [p for _, p in opciones]
    return rng.choices(valores, weights=pesos, k=1)[0]


REPARTO_CONFIRMACION = (
    ("CONFIRMADA", 0.62),
    ("CANDIDATA", 0.20),
    ("RECHAZADA", 0.11),
    ("SUPRIMIDA", 0.07),
)
REPARTO_VALIDEZ = (
    ("VIGENTE", 0.66),
    ("SUSTITUIDA", 0.15),
    ("INVALIDADA", 0.11),
    ("SIN_SOPORTE", 0.08),
)
REPARTO_DISPONIBILIDAD = (
    ("DISPONIBLE", 0.71),
    ("ARCHIVADA", 0.13),
    ("ELIMINADA", 0.07),
    ("PURGADA", 0.05),
    ("NO_GUARDADA", 0.04),
)
REPARTO_SENSIBILIDAD = (("ORDINARIA", 0.84), ("RESTRINGIDA", 0.16))
REPARTO_POLARIDAD = (("AFIRMATIVA", 0.79), ("NEGATIVA", 0.21))
REPARTO_AUTORIDAD = (
    ("ACTO_EXPLICITO_USUARIO", 0.44),
    ("DOCUMENTO_CANONICO", 0.27),
    ("INFORMAL", 0.18),
    ("FUENTE_EXTERNA", 0.11),
)
REPARTO_PROYECTO = ((S3.PROYECTOS_RENDIMIENTO[0], 0.54), (S3.PROYECTOS_RENDIMIENTO[1], 0.46))
REPARTO_CRITICIDAD = (("CRITICO", 0.28), ("IMPORTANTE", 0.42), ("ORDINARIO", 0.30))

PROBABILIDAD = {
    "condicion": 0.19,
    "valid_to": 0.31,
    "occurred_at": 0.46,
    "entidades": 0.38,
    "procedencia": 0.41,
    "criticidad": 0.23,
    "no_usar_como_memoria": 0.06,
    "no_consolidable": 0.07,
    "mensaje_no_guardar": 0.05,
    "mensaje_redactado": 0.04,
}

PROCEDENCIAS: tuple[str, ...] = (
    "PROC-TELAR",
    "PROC-HORNO",
    "PROC-CANTERA",
    "PROC-ORILLA",
    "PROC-ESTUARIO",
    "PROC-TALLER",
)


def _entidades_rendimiento() -> list[dict[str, Any]]:
    """Entidades sintéticas con alias, sin homónimos del corpus de conformidad."""
    salida: list[dict[str, Any]] = []
    for i, sustantivo in enumerate(SUSTANTIVOS[:24]):
        adjetivo = ADJETIVOS[i % len(ADJETIVOS)]
        salida.append(
            {
                "id": f"ENT-P-{i + 1:02d}",
                "nombre_canonico": f"{sustantivo} {adjetivo}",
                "alias": [f"{sustantivo[:4]}. {adjetivo}"] if i % 3 == 0 else [],
                "grupo_homonimo": _FAMILIA_DE_SUSTANTIVO[sustantivo] if i % 5 == 0 else None,
                "nota": "entidad sintética del corpus de rendimiento; sin anclaje canónico",
            }
        )
    return salida


def construir_corpus_rendimiento(canon: CS3.Canon) -> dict[str, Any]:
    """5.000 mensajes, 500 recuerdos, 50 decisiones y **dos proyectos reales**."""
    gen = GeneradorSintetico(S3.SEMILLA)
    rng = gen.rng
    entidades = _entidades_rendimiento()
    ids_entidad = [e["id"] for e in entidades]

    estructuras_usadas: Counter[str] = Counter()
    familias_usadas: Counter[str] = Counter()

    def nuevo_texto() -> str:
        texto, estructuras, familia = gen.texto()
        estructuras_usadas.update(estructuras)
        familias_usadas[familia] += 1
        return texto

    items: list[dict[str, Any]] = []
    for kind, prefijo, cantidad in (
        ("MEMORIA", "MEM-P", S3.ESCALA_RENDIMIENTO["recuerdos"]),
        ("DECISION", "DEC-P", S3.ESCALA_RENDIMIENTO["decisiones"]),
    ):
        for n in range(1, cantidad + 1):
            desplazamiento = rng.randrange(_DIAS + 1)
            valid_from = _fecha(rng, desplazamiento)
            valid_to = (
                _fecha(rng, min(_DIAS, desplazamiento + rng.randrange(10, 240)))
                if rng.random() < PROBABILIDAD["valid_to"]
                else None
            )
            occurred_at = (
                _fecha(rng, max(0, desplazamiento - rng.randrange(0, 90)))
                if rng.random() < PROBABILIDAD["occurred_at"]
                else None
            )
            criticidad = None
            if rng.random() < PROBABILIDAD["criticidad"]:
                criticidad = {
                    "nivel": _reparto(rng, REPARTO_CRITICIDAD),
                    "razon": nuevo_texto(),
                    "fuente": rng.choice(PROCEDENCIAS),
                    "regla": "ADJUDICACION_DE_PRUEBA",
                }
            items.append(
                {
                    "id": f"{prefijo}-{n:05d}",
                    "kind": kind,
                    "project_id": _reparto(rng, REPARTO_PROYECTO),
                    "entity_ids": (
                        rng.sample(ids_entidad, rng.randrange(1, 3))
                        if rng.random() < PROBABILIDAD["entidades"]
                        else []
                    ),
                    "text": nuevo_texto(),
                    "polaridad": _reparto(rng, REPARTO_POLARIDAD),
                    "condicion": (
                        nuevo_texto() if rng.random() < PROBABILIDAD["condicion"] else None
                    ),
                    "confirmacion": _reparto(rng, REPARTO_CONFIRMACION),
                    "validez": _reparto(rng, REPARTO_VALIDEZ),
                    "disponibilidad": _reparto(rng, REPARTO_DISPONIBILIDAD),
                    "sensibilidad": _reparto(rng, REPARTO_SENSIBILIDAD),
                    "temporalidad": {
                        "valid_from": valid_from,
                        "valid_to": valid_to,
                        "occurred_at": occurred_at,
                        "recorded_at": _fecha(
                            rng, min(_DIAS, desplazamiento + rng.randrange(0, 40))
                        ),
                    },
                    "ambito": "PROYECTO",
                    "autoridad": _reparto(rng, REPARTO_AUTORIDAD),
                    "no_usar_como_memoria": rng.random() < PROBABILIDAD["no_usar_como_memoria"],
                    "no_consolidable": rng.random() < PROBABILIDAD["no_consolidable"],
                    "criticidad": criticidad,
                    "procedencia": (
                        rng.sample(PROCEDENCIAS, rng.randrange(1, 3))
                        if rng.random() < PROBABILIDAD["procedencia"]
                        else []
                    ),
                    "traza": ["RENDIMIENTO"],
                }
            )

    mensajes: list[dict[str, Any]] = []
    for n in range(1, S3.ESCALA_RENDIMIENTO["mensajes"] + 1):
        mensajes.append(
            {
                "id": f"MSG-P-{n:05d}",
                "project_id": _reparto(rng, REPARTO_PROYECTO),
                "texto": nuevo_texto(),
                "recorded_at": _fecha(rng),
                "no_guardar": rng.random() < PROBABILIDAD["mensaje_no_guardar"],
                "redactado": rng.random() < PROBABILIDAD["mensaje_redactado"],
                "traza": ["RENDIMIENTO"],
            }
        )

    documentos: list[dict[str, Any]] = []
    for n in range(1, 121):
        accesible = rng.random() > 0.12
        documentos.append(
            {
                "id": f"DOC-P-{n:03d}",
                "titulo": nuevo_texto(),
                "accesible": accesible,
                "texto": nuevo_texto() if accesible else None,
                "afirmacion_atribuida": nuevo_texto() if rng.random() < 0.22 else None,
                "traza": ["RENDIMIENTO"],
            }
        )

    tipos_relacion = ("APOYA", "REFUTA", "CONFLICTO_CON", "CORRIGE", "SUSTITUYE_A", "DERIVA_DE")
    relaciones: list[dict[str, Any]] = []
    ids_item = [i["id"] for i in items]
    for n in range(1, 181):
        origen, destino = rng.sample(ids_item, 2)
        relaciones.append(
            {
                "id": f"REL-P-{n:03d}",
                "tipo": tipos_relacion[n % len(tipos_relacion)],
                "origen": origen,
                "destino": destino,
                "nota": nuevo_texto(),
            }
        )

    proyectos = [
        {
            "id": S3.PROYECTOS_RENDIMIENTO[0],
            "nombre": "Arrecife",
            "alias": ["ARR"],
            "tipo": "PROYECTO",
            "miembros_lista_cerrada": [],
        },
        {
            "id": S3.PROYECTOS_RENDIMIENTO[1],
            "nombre": "Cumbre",
            "alias": ["CUM"],
            "tipo": "PROYECTO",
            "miembros_lista_cerrada": [],
        },
    ]

    corpus: dict[str, Any] = {
        "documento": "Corpus de RENDIMIENTO del benchmark de ADR-002",
        "proposito": (
            "Corpus sintético de estrés neutral para latencia, tamaño, construcción, "
            "reconstrucción y estabilidad a la escala de ADR002-TOL-208. NO representa "
            "producción, NO crea referencias funcionales y NO sustituye al corpus de "
            "conformidad."
        ),
        "version": S3.VERSION_CORPUS_RENDIMIENTO,
        "version_contrato": S3.VERSION_CONTRATO,
        "estado": S3.ESTADO_NO_CONGELADO,
        "semilla": S3.SEMILLA,
        "generador": "experiments/adr002/benchmark/build_corpus_v0_3.py",
        "hereda_de": None,
        "independencia": (
            "Artefacto independiente del corpus de conformidad. Comparte contrato, semilla y "
            "vocabulario de estados; NO reproduce los 94 anclajes byte a byte y su léxico es "
            "disjunto del léxico protegido por token, sufijo y raíz."
        ),
        "datos_reales": "ninguno; corpus sintético determinista",
        "red": "no utilizada",
        "ahora_declarado": S3.AHORA_DECLARADO,
        "escala_declarada": {
            "escala_de_referencia": S3.ESCALA_RENDIMIENTO,
            "fuente_de_la_escala": S3.FUENTE_ESCALA,
            "escalas_proyectables": list(S3.ESCALAS_PROYECCION),
            "intervalo_temporal": {
                "desde": S3.RENDIMIENTO_FECHA_INICIO,
                "hasta": S3.RENDIMIENTO_FECHA_FIN,
                "dias": _DIAS + 1,
            },
        },
        "generacion": {
            "familias_tematicas": list(FAMILIAS_TEMATICAS),
            "estructuras_gramaticales": [n for n, _ in ESTRUCTURAS],
            "uso_de_estructuras": dict(sorted(estructuras_usadas.items())),
            "uso_de_familias": dict(sorted(familias_usadas.items())),
            "modelo_de_vocabulario": "Zipf-Mandelbrot · peso(rango) = 1/(rango+5)",
            "regla": (
                "Ninguna plantilla se reutiliza como texto: doce estructuras gramaticales se "
                "combinan en una a cuatro cláusulas con vocabulario muestreado por rango. "
                "Ningún texto contiene su número de secuencia."
            ),
        },
        "reparto_declarado": {
            "proyecto": dict(REPARTO_PROYECTO),
            "confirmacion": dict(REPARTO_CONFIRMACION),
            "validez": dict(REPARTO_VALIDEZ),
            "disponibilidad": dict(REPARTO_DISPONIBILIDAD),
            "sensibilidad": dict(REPARTO_SENSIBILIDAD),
            "polaridad": dict(REPARTO_POLARIDAD),
            "autoridad": dict(REPARTO_AUTORIDAD),
            "criticidad": dict(REPARTO_CRITICIDAD),
            "probabilidades": PROBABILIDAD,
        },
        "conteos": {
            "proyectos": len(proyectos),
            "entidades": len(entidades),
            "items": len(items),
            "recuerdos": sum(1 for i in items if i["kind"] == "MEMORIA"),
            "decisiones": sum(1 for i in items if i["kind"] == "DECISION"),
            "mensajes": len(mensajes),
            "documentos": len(documentos),
            "relaciones": len(relaciones),
        },
        "proyectos": proyectos,
        "entidades": entidades,
        "items": items,
        "mensajes": mensajes,
        "documentos": documentos,
        "relaciones": relaciones,
    }
    corpus["distribucion_observada"] = medir_distribucion(corpus)
    corpus["identidad"] = identidad_de_colecciones(corpus)
    return corpus


# --- §6.4 · invariantes distributivas, calculadas sobre los datos -----------


def textos_del_corpus(corpus: dict[str, Any]) -> list[str]:
    salida: list[str] = []
    for item in corpus["items"]:
        salida.append(item["text"])
        if item.get("condicion"):
            salida.append(item["condicion"])
        if item.get("criticidad"):
            salida.append(item["criticidad"]["razon"])
    salida.extend(m["texto"] for m in corpus["mensajes"])
    for documento in corpus["documentos"]:
        salida.append(documento["titulo"])
        if documento.get("texto"):
            salida.append(documento["texto"])
        if documento.get("afirmacion_atribuida"):
            salida.append(documento["afirmacion_atribuida"])
    salida.extend(r["nota"] for r in corpus["relaciones"])
    return salida


def pendiente_zipf(frecuencias: list[int]) -> float:
    """Pendiente de la recta de mínimos cuadrados sobre log(rango) y log(frecuencia)."""
    ordenadas = sorted(frecuencias, reverse=True)
    xs = [math.log(r) for r in range(1, len(ordenadas) + 1)]
    ys = [math.log(f) for f in ordenadas]
    n = len(xs)
    media_x, media_y = sum(xs) / n, sum(ys) / n
    numerador = sum((x - media_x) * (y - media_y) for x, y in zip(xs, ys, strict=True))
    denominador = sum((x - media_x) ** 2 for x in xs)
    return numerador / denominador


def medir_distribucion(corpus: dict[str, Any]) -> dict[str, Any]:
    """Todo lo que el manifiesto registra se calcula aquí, sobre los datos."""
    textos = textos_del_corpus(corpus)
    longitudes = [len(t) for t in textos]
    tokens: Counter[str] = Counter()
    for texto in textos:
        tokens.update(_informativos(texto))
    total_tokens = sum(tokens.values())
    fechas: Counter[str] = Counter()
    for item in corpus["items"]:
        for clave in ("valid_from", "valid_to", "occurred_at", "recorded_at"):
            valor = item["temporalidad"].get(clave)
            if valor:
                fechas[valor[:10]] += 1
    for mensaje in corpus["mensajes"]:
        fechas[mensaje["recorded_at"][:10]] += 1

    elementos = corpus["items"] + corpus["mensajes"]
    por_proyecto = Counter(e["project_id"] for e in elementos)
    total_elementos = len(elementos)

    ejes: dict[str, dict[str, float]] = {}
    for eje in S3.EJES_ESTADO:
        conteo: Counter[str] = Counter()
        for item in corpus["items"]:
            if eje == "condicion_presente":
                conteo[str(item["condicion"] is not None)] += 1
            elif eje == "temporalidad_cerrada":
                conteo[str(item["temporalidad"]["valid_to"] is not None)] += 1
            else:
                conteo[str(item[eje])] += 1
        ejes[eje] = {k: round(v / len(corpus["items"]), 4) for k, v in sorted(conteo.items())}

    con_entidades = sum(1 for i in corpus["items"] if i["entity_ids"])
    con_procedencia = sum(1 for i in corpus["items"] if i["procedencia"])
    con_criticidad = sum(1 for i in corpus["items"] if i["criticidad"])
    con_alias = sum(1 for e in corpus["entidades"] if e["alias"])
    tipos_relacion = Counter(r["tipo"] for r in corpus["relaciones"])

    return {
        "conteos_reales": {
            "items": len(corpus["items"]),
            "recuerdos": sum(1 for i in corpus["items"] if i["kind"] == "MEMORIA"),
            "decisiones": sum(1 for i in corpus["items"] if i["kind"] == "DECISION"),
            "mensajes": len(corpus["mensajes"]),
            "documentos": len(corpus["documentos"]),
            "relaciones": len(corpus["relaciones"]),
            "entidades": len(corpus["entidades"]),
            "proyectos": len(corpus["proyectos"]),
            "proyectos_referenciados": len(por_proyecto),
        },
        "longitud_texto": {
            "n": len(longitudes),
            "media": round(statistics.fmean(longitudes), 2),
            "mediana": statistics.median(longitudes),
            "p95": sorted(longitudes)[int(0.95 * (len(longitudes) - 1))],
            "desviacion": round(statistics.pstdev(longitudes), 2),
            "minimo": min(longitudes),
            "maximo": max(longitudes),
            "longitudes_distintas": len(set(longitudes)),
        },
        "vocabulario": {
            "tokens_informativos": total_tokens,
            "tamano": len(tokens),
            "frecuencia_maxima": tokens.most_common(1)[0][1],
            "frecuencia_relativa_maxima": round(tokens.most_common(1)[0][1] / total_tokens, 4),
            "token_mas_frecuente": tokens.most_common(1)[0][0],
            "pendiente_zipf": round(pendiente_zipf(list(tokens.values())), 4),
            "diez_mas_frecuentes": [
                {"token": t, "frecuencia": f} for t, f in tokens.most_common(10)
            ],
        },
        "textos": {
            "total": len(textos),
            "distintos": len(set(textos)),
            "proporcion_distintos": round(len(set(textos)) / len(textos), 4),
        },
        "fechas": {
            "distintas": len(fechas),
            "meses_distintos": len({f[:7] for f in fechas}),
            "minima": min(fechas),
            "maxima": max(fechas),
        },
        "reparto_por_proyecto": {
            p: round(n / total_elementos, 4) for p, n in sorted(por_proyecto.items())
        },
        "reparto_por_eje": ejes,
        "proporciones": {
            "items_con_entidades": round(con_entidades / len(corpus["items"]), 4),
            "items_con_procedencia": round(con_procedencia / len(corpus["items"]), 4),
            "items_con_criticidad": round(con_criticidad / len(corpus["items"]), 4),
            "entidades_con_alias": round(con_alias / len(corpus["entidades"]), 4),
        },
        "relaciones": {
            "tipos": dict(sorted(tipos_relacion.items())),
            "tipos_distintos": len(tipos_relacion),
            "densidad_por_item": round(len(corpus["relaciones"]) / len(corpus["items"]), 4),
        },
    }


# ===========================================================================
# 6. Casos, referencias, PDP y previsión T0
# ===========================================================================

EVIDENCIA_MINIMA = [
    "petición efectiva y operation_id",
    "modo adjudicado y puertas aplicadas",
    "etapas recorridas y condición de insuficiencia de cada transición",
    "resultado obtenido, esperado, veredicto y razón, por rama",
    "por resultado: por qué entró y por qué ocupa esa posición",
    "prohibidos que aparecieron y por qué no fueron excluidos",
    "suficiencia adjudicada y razón de la parada",
    "tolerancia aplicada y su versión, o la dependencia pendiente que la bloquea",
]


T0_NO_MEDIDO = {
    "estado_t0": S3.ESTADO_T0,
    "prevision_en": "t0_preexecution_projection_v0_1.json",
    "nota": (
        "Este artefacto es congelable y no contiene ninguna previsión normativa sobre T0. "
        "T0 no se ha ejecutado."
    ),
}

MOTIVO_SIN_PROYECCION = (
    "El criterio de previsión se define sobre el estado medido de B04-RF-01-32. Este caso no "
    "traza a ningún B04-RF: proyectarlo exigiría inventar un estado que nadie ha medido."
)


def _sin_veredicto_t0(caso: dict[str, Any]) -> dict[str, Any]:
    """Quita el veredicto heredado del v0.1 y deja solo el estado NO_MEDIDO."""
    limpio = {k: v for k, v in caso.items() if k != "t0"}
    limpio["t0"] = dict(T0_NO_MEDIDO)
    return limpio


def construir_casos(canon: CS3.Canon, conformidad: dict[str, Any]) -> dict[str, Any]:
    ramas_por_ca = ramas_v0_3(conformidad["items"])
    nivel1 = [_caso_nivel1(fila, canon, ramas_por_ca) for fila in V1.CA]
    for caso in nivel1:
        caso["evidencia_minima"] = EVIDENCIA_MINIMA
    anclajes = CS3.asignaciones_canonicas_por_pdp_ca()
    nivel1_pdp = [
        _caso_pdp_funcional(pdp, orden, canon, anclajes[pdp])
        for orden, pdp in enumerate(S3.PDP_CA_FUNCIONALES, start=1)
    ]
    for caso in nivel1_pdp:
        caso["evidencia_minima"] = EVIDENCIA_MINIMA
    return {
        "documento": "Casos del benchmark de ADR-002",
        "version": S3.VERSION_CONTRATO,
        "estado": S3.ESTADO_NO_CONGELADO,
        "hereda_de": "cases_v0_2.json",
        "regla_de_separacion": (
            "El bloque `canonico` procede literalmente de las fuentes DOCX y no se reescribe. "
            "El bloque `instanciacion` y los catorce campos de la ficha del PDP §7 registran "
            "fuente, sección, estado y justificación campo a campo. Ningún campo puede "
            "marcarse CANONICO sin texto literal que lo fije."
        ),
        "regla_de_clasificacion": (
            "Solo son casos funcionales de nivel 1 los cincuenta B04-CA y los dos PDP-CA "
            "anclados por el Anexo B vía RED-017. Las seis reglas de disciplina viven en "
            "pdp_harness_rules_v0_1.json y no reciben consulta funcional ni previsión T0."
        ),
        "niveles": {
            "1": (
                "Casos canónicos reutilizados: B04-CA-01-50 y los PDP-CA anclados por el "
                "Anexo B. El benchmark los ejecuta, no los reescribe."
            ),
            "2": "Casos arquitectónicos nuevos. Solo cuando ningún caso canónico los cubre.",
            "3": (
                "Ablaciones técnicas. Instrumentos de medida; nunca producen veredicto de "
                "conformidad, y por eso no llevan ficha de caso del PDP §7."
            ),
        },
        "conteos": {
            "nivel_1_b04": len(nivel1),
            "nivel_1_pdp": len(nivel1_pdp),
            "nivel_2": len(V1.NIVEL2),
            "nivel_3": len(V1.NIVEL3),
            "ramas_canonicas": sum(len(c["instanciacion"]["ramas"]) for c in nivel1),
        },
        "nivel_1": nivel1,
        "nivel_1_pdp": nivel1_pdp,
        "nivel_2": [_sin_veredicto_t0(c) for c in V1.NIVEL2],
        "nivel_3": [_sin_veredicto_t0(c) for c in V1.NIVEL3],
    }


def construir_referencias(casos: dict[str, Any]) -> dict[str, Any]:
    refs: list[dict[str, Any]] = []
    for caso in casos["nivel_1"]:
        inst = caso["instanciacion"]
        refs.append(
            {
                "caso": caso["id"],
                "identificador_canonico": caso["identificador_canonico"],
                "canonico": {
                    "fuente": S3.FUENTE_CANONICA_CA,
                    "seccion_exacta": caso["canonico"]["seccion_exacta"],
                    "riesgo": caso["canonico"]["riesgo"],
                    "entrada": caso["canonico"]["entrada"],
                    "resultado_esperado": caso["canonico"]["resultado_esperado"],
                    "fallo_observable": caso["canonico"]["fallo_observable"],
                    "modificable": False,
                },
                "instanciacion": {
                    "fuente": S3.FUENTE_INSTANCIACION,
                    "estado": S3.ESTADO_NO_CONGELADO,
                    "modificable": True,
                    "ramas": [
                        {
                            "sufijo": r["sufijo"],
                            "clase": r["clase"],
                            "modo": r["modo"],
                            "elegibles": r["candidatos_elegibles"],
                            "prohibidos": r["candidatos_prohibidos"],
                            "estado_suficiencia_esperado": r["estado_suficiencia_esperado"],
                            "tolerancia_pendiente": r["tolerancia_pendiente"],
                            "cierre": r.get("cierre"),
                        }
                        for r in inst["ramas"]
                    ],
                    "cardinalidad": inst["cardinalidad"]["valor"],
                    "etapa": inst["etapa"]["valor"],
                    "parada": inst["parada"]["valor"],
                    "orden": inst["orden"]["valor"]["valor"],
                    "tipo_orden": inst["orden"]["valor"]["tipo"],
                    "elegibles": inst["elegibles"]["valor"],
                    "prohibidos": inst["prohibidos"]["valor"],
                    "fuente_por_campo": {
                        campo: {
                            "fuente": inst[campo]["fuente"],
                            "seccion": inst[campo]["seccion"],
                            "estado": inst[campo]["estado"],
                        }
                        for campo in S3.CAMPOS_INSTANCIACION
                    },
                },
                "tolerancias": caso["ficha_pdp_7"]["tolerancias"]["valor"],
                "t0": {"estado_t0": S3.ESTADO_T0},
            }
        )
    return {
        "documento": "Referencias del benchmark de ADR-002",
        "version": S3.VERSION_CONTRATO,
        "estado": S3.ESTADO_NO_CONGELADO,
        "hereda_de": "references_v0_2.json",
        "regla": (
            "El bloque `canonico` no cambia nunca: procede literalmente de B04 §17/§17.1. El "
            "bloque `instanciacion` está PROPUESTO y NO CONGELADO. Ninguna referencia contiene "
            "previsión normativa sobre T0: solo el estado NO_MEDIDO."
        ),
        "conteos": {
            "referencias_nivel_1": len(refs),
            "referencias_con_ramas": sum(1 for r in refs if r["instanciacion"]["ramas"]),
            "referencias_con_cierre_exhaustivo": sum(
                1 for r in refs if any(rama.get("cierre") for rama in r["instanciacion"]["ramas"])
            ),
        },
        "referencias_nivel_1": refs,
    }


def construir_casos_pdp(canon: CS3.Canon) -> dict[str, Any]:
    anclajes = CS3.asignaciones_canonicas_por_pdp_ca()
    funcionales = {
        pdp: {
            "criterio": "ANEXO_B_RED_CON_CASO_O_METRICA_DE_B04",
            **anclajes[pdp],
        }
        for pdp in S3.PDP_CA_FUNCIONALES
    }
    reglas = {
        pdp: {
            "criterio": "DISCIPLINA_DE_CONGELACION_IMPORTADA_POR_ADR002",
            "regla_que_lo_importa": REGLAS_DE_ARNES[pdp]["regla_que_lo_importa"],
            "artefacto": "pdp_harness_rules_v0_1.json",
        }
        for pdp in S3.PDP_CA_REGLAS_DE_ARNES
    }
    clasificados = set(funcionales) | set(reglas)
    excluidos: dict[str, dict[str, Any]] = {}
    for pdp, caso in sorted(canon.casos_pdp.items()):
        if pdp in clasificados:
            continue
        filas = [f for f in canon.anexo.values() if pdp in f.casos_pdp()]
        familias = sorted({fam for f in filas for fam in f.familias})
        destinos: list[str] = []
        for familia in familias:
            info = canon.destinos.get(familia)
            if info:
                destinos.extend(CS3.expandir_destinos(info["destino"]))
        excluidos[pdp] = {
            "entrada_adversarial": caso.entrada_adversarial,
            "resultado_esperado": caso.resultado_esperado,
            "red_que_lo_asigna": sorted(f.red for f in filas),
            "familias": familias,
            "responsable": sorted(set(destinos)) or ["PDP · Plan de Pruebas completo"],
            "motivo": (
                "Ninguna fila del Anexo B que lo asigna cita un caso B04-CA ni una métrica "
                "B04-M, y ADR-002 no importa su regla. No se afirma cobertura."
            ),
        }

    familias_destino = CS3.familias_destino_adr002()
    tocadas: set[str] = set()
    for fila in V1.CA:
        tocadas.update(fila["fam"])
    for caso in V1.NIVEL2 + V1.NIVEL3:
        tocadas.update(caso.get("fam", []))
    for asignacion in CS3.asignaciones_canonicas_por_ca().values():
        tocadas.update(asignacion["familias"])
    todas = set(canon.familias)
    return {
        "documento": "Casos transversales del Plan de Pruebas y su clasificación en ADR-002",
        "version": "0.2",
        "version_contrato": S3.VERSION_CONTRATO,
        "estado": S3.ESTADO_NO_CONGELADO,
        "fuente": "Plan de Pruebas + RED/PDP v1.0 APROBADO · §9 y Anexo B",
        "advertencia": (
            "ADR-002 NO cubre los 304 casos del Plan completo (276 heredados + 28 "
            "transversales). Aquí se clasifican los 28 PDP-CA en tres clases disjuntas y se "
            "justifica la exclusión del resto."
        ),
        "clases": {
            "CASO_FUNCIONAL_NIVEL_1": (
                "Anclado por una fila del Anexo B que cita un caso B04-CA o una métrica B04-M. "
                "Lleva ficha completa del PDP §7 y consulta funcional."
            ),
            "REGLA_DE_PROTOCOLO_DEL_ARNES": (
                "Disciplina de congelación importada por un artefacto aprobado de ADR-002. "
                "No es una consulta funcional y no recibe previsión frente a T0."
            ),
            "FUERA_DE_ALCANCE": (
                "Ninguna fila del Anexo B que lo asigna cita B04 y ADR-002 no importa su regla."
            ),
        },
        "conteos": {
            "pdp_ca_totales": len(canon.casos_pdp),
            "casos_funcionales_nivel_1": len(funcionales),
            "reglas_de_protocolo_del_arnes": len(reglas),
            "casos_fuera_de_alcance": len(excluidos),
        },
        "casos_funcionales_nivel_1": funcionales,
        "reglas_de_protocolo_del_arnes": reglas,
        "casos_fuera_de_alcance": excluidos,
        "familias_pdp": {
            "advertencia": (
                "No existe una sola cifra de «cobertura de familias de ADR-002». Se reportan "
                "cuatro denominadores distintos, cada uno con su fuente, y no se agregan."
            ),
            "1_destino_directo_adr002_arq00_20": {
                "fuente": S3.FUENTE_ARQ00_20,
                "familias": familias_destino,
                "de": len(todas),
            },
            "2_entradas_obligatorias_declaradas": {
                "fuente": S3.FUENTE_FAMILIAS_ENTRADA,
                "familias": list(S3.FAMILIAS_ENTRADA_ADR002),
                "de": len(todas),
            },
            "3_tocadas_por_casos_sin_atribuir_cierre": {
                "fuente": S3.FUENTE_INSTANCIACION,
                "familias": sorted(tocadas),
                "de": len(todas),
                "nota": (
                    "Que un caso canónico toque una familia no cierra esa familia ni la "
                    "atribuye a ADR-002. El mínimo canónico por familia del PDP §8 exige "
                    "ejecutar todos sus casos asignados del banco de 304."
                ),
            },
            "4_fuera_de_alcance_de_adr002": {
                "fuente": S3.FUENTE_ARQ00_20,
                "familias": sorted(todas - set(familias_destino)),
                "de": len(todas),
                "responsables": {
                    f: CS3.expandir_destinos(canon.destinos[f]["destino"])
                    for f in sorted(todas - set(familias_destino))
                },
            },
        },
        "cobertura_minima_por_familia": {
            f: canon.familias[f]["cobertura_minima"] for f in sorted(canon.familias)
        },
    }


# --- §4.5 · previsión T0, fuera de todo artefacto congelable -----------------


def _requisitos_de(caso: dict[str, Any]) -> list[str]:
    if "trazabilidad" in caso:
        return list(caso["trazabilidad"]["requisito_verificado"])
    return sorted(
        {
            rf
            for fila in V1.CA
            if fila["ca"] in caso.get("anclaje_canonico", {}).get("casos_b04", [])
            for rf in fila["rf"]
        }
    )


def _exige_dos_implementaciones(caso: dict[str, Any]) -> bool:
    ident = caso["identificador_canonico"]
    if ident in S3.CA_REQUIEREN_DOS_IMPLEMENTACIONES:
        return True
    anclados = caso.get("anclaje_canonico", {}).get("casos_b04", [])
    return bool(anclados) and all(c in S3.CA_REQUIEREN_DOS_IMPLEMENTACIONES for c in anclados)


def construir_proyeccion_t0(casos: dict[str, Any]) -> dict[str, Any]:
    """Criterio único, aplicado automáticamente a **todos** los casos funcionales."""
    proyecciones: list[dict[str, Any]] = []
    for caso in casos["nivel_1"] + casos["nivel_1_pdp"]:
        requisitos = _requisitos_de(caso)
        estados = {rf: S3.ESTADO_RF_EN_T0.get(rf, "DESCONOCIDO") for rf in requisitos}
        if _exige_dos_implementaciones(caso):
            prevision = "NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION"
            fundamento = (
                "El enunciado canónico exige dos realizaciones distintas sobre el mismo corpus. "
                "T0 es una sola realización: la comparación no existe."
            )
        elif "AUSENTE" in estados.values():
            ausentes = sorted(rf for rf, e in estados.items() if e == "AUSENTE")
            prevision = "NO_EXPRESABLE_PREVISTO"
            fundamento = (
                f"Dimensiones requeridas inexistentes en la línea base: {', '.join(ausentes)} "
                f"según {S3.FUENTE_INVENTARIO}."
            )
        elif "PARCIAL" in estados.values():
            parciales = sorted(rf for rf, e in estados.items() if e == "PARCIAL")
            prevision = "PARCIALMENTE_EXPRESABLE_PREVISTO"
            fundamento = (
                f"Dimensiones presentes de forma incompleta: {', '.join(parciales)} según "
                f"{S3.FUENTE_INVENTARIO}."
            )
        else:
            prevision = "EXPRESABLE_PREVISTO"
            fundamento = (
                f"Todas las dimensiones requeridas existen en la línea base según "
                f"{S3.FUENTE_INVENTARIO}."
            )
        proyecciones.append(
            {
                "caso": caso["id"],
                "identificador_canonico": caso["identificador_canonico"],
                "clase": caso["clase"],
                "estado_t0": S3.ESTADO_T0,
                "expresabilidad_prevista": prevision,
                "fundamento_de_prevision": fundamento,
                "estado_por_requisito": dict(sorted(estados.items())),
                "ejes_inseguros_medidos": sorted(
                    rf for rf, e in estados.items() if e == "INSEGURO"
                ),
                "no_es_veredicto": True,
            }
        )
    no_proyectados = [
        {"caso": caso["id"], "motivo": MOTIVO_SIN_PROYECCION, "estado_t0": S3.ESTADO_T0}
        for caso in casos["nivel_2"] + casos["nivel_3"]
    ]
    reparto: dict[str, list[str]] = {}
    for p in proyecciones:
        reparto.setdefault(p["expresabilidad_prevista"], []).append(p["identificador_canonico"])
    return {
        "documento": "Previsión de expresabilidad frente a T0 · ADR-002",
        "version": "0.1",
        "version_contrato": S3.VERSION_CONTRATO,
        "estado": S3.ESTADO_NO_NORMATIVO,
        "normativo": False,
        "congelable": False,
        "sustituible_por": (
            "la ejecución real de T0. Este fichero se sustituye ÍNTEGRAMENTE por el resultado "
            "medido; ninguna de sus previsiones sobrevive a la medición."
        ),
        "regla": (
            "Previsión, nunca veredicto. El criterio se aplica automáticamente a todos los "
            "casos funcionales, no a una lista escrita a mano. Las reglas de protocolo del "
            "arnés no aparecen aquí: no reciben previsión frente a T0."
        ),
        "criterio": {
            "fuente_de_los_estados": S3.FUENTE_INVENTARIO,
            "orden_de_aplicacion": [
                "1. si el caso exige dos realizaciones distintas -> "
                "NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION",
                "2. si alguna dimensión requerida es AUSENTE -> NO_EXPRESABLE_PREVISTO",
                "3. si alguna es PARCIAL -> PARCIALMENTE_EXPRESABLE_PREVISTO",
                "4. en otro caso -> EXPRESABLE_PREVISTO",
            ],
        },
        "conteos": {
            "casos_funcionales_proyectados": len(proyecciones),
            "reglas_de_arnes_proyectadas": 0,
            "casos_no_proyectados": len(no_proyectados),
        },
        "no_proyectados": no_proyectados,
        "reparto": {k: sorted(v) for k, v in sorted(reparto.items())},
        "proyecciones": proyecciones,
    }


# ===========================================================================
# 7. Manifiesto y volcado
# ===========================================================================


def construir_manifiesto(
    canon: CS3.Canon,
    conformidad: dict[str, Any],
    rendimiento: dict[str, Any],
    casos: dict[str, Any],
    referencias: dict[str, Any],
    pdp: dict[str, Any],
    reglas: dict[str, Any],
    proyeccion: dict[str, Any],
) -> dict[str, Any]:
    return {
        "documento": "Manifiesto del benchmark de ADR-002",
        "version_contrato": S3.VERSION_CONTRATO,
        "estado": S3.ESTADO_NO_CONGELADO,
        "semilla_compartida": S3.SEMILLA,
        "advertencia": (
            "Ninguna puerta de arranque queda satisfecha por este manifiesto. "
            "ADR002-TOL-207 no está aprobada; TOL-208, TOL-209 y TOL-210 siguen NO SATISFECHAS. "
            "T0 no se ha ejecutado y ADR002-A/B/C/D no se han implementado ni ejecutado."
        ),
        "fuentes_canonicas": canon.huellas,
        "medidas_del_canon": canon.medidas(),
        "tablas_canonicas": CS3.inventario_de_tablas(),
        "metricas_del_anexo_b": CS3.metricas_del_anexo_b(),
        "artefactos": {
            "corpus_conformidad": {
                "fichero": "conformance_corpus_v0_3.json",
                "version": conformidad["version"],
                "conteos": conformidad["conteos"],
            },
            "corpus_rendimiento": {
                "fichero": "performance_corpus_v0_2.json",
                "version": rendimiento["version"],
                "conteos": rendimiento["conteos"],
                "distribucion_observada": rendimiento["distribucion_observada"],
            },
            "casos": {"fichero": "cases_v0_3.json", "conteos": casos["conteos"]},
            "referencias": {"fichero": "references_v0_3.json", "conteos": referencias["conteos"]},
            "casos_pdp": {"fichero": "pdp_cases_v0_2.json", "conteos": pdp["conteos"]},
            "reglas_de_arnes": {
                "fichero": "pdp_harness_rules_v0_1.json",
                "conteos": reglas["conteos"],
            },
            "proyeccion_t0": {
                "fichero": "t0_preexecution_projection_v0_1.json",
                "estado": proyeccion["estado"],
                "normativo": proyeccion["normativo"],
                "congelable": proyeccion["congelable"],
                "conteos": proyeccion["conteos"],
            },
        },
        "relacion_entre_corpus": {
            "regla": (
                "Los dos corpus son INDEPENDIENTES. Comparten versión de contrato, semilla y "
                "vocabulario de estados. El de conformidad adjudica comportamiento sobre 94 "
                "anclajes; el de rendimiento mide magnitudes sobre 5.550 elementos sintéticos y "
                "no reproduce los anclajes byte a byte."
            ),
            "prohibicion": (
                "Prohibido fijar cifras de rendimiento sobre el corpus de conformidad y "
                "prohibido adjudicar conformidad sobre el corpus de rendimiento."
            ),
            "contaminacion": (
                "El léxico del corpus de rendimiento es disjunto del léxico protegido del "
                "corpus de conformidad por token exacto, singular/plural o sufijo, raíz común "
                f"de {S3.LONGITUD_RAIZ} caracteres, nombre o alias de entidad y n-grama."
            ),
        },
        "artefactos_anteriores_conservados": [
            "corpus_v0_1.json",
            "cases_v0_1.json",
            "references_v0_1.json",
            "conformance_corpus_v0_2.json",
            "performance_corpus_v0_1.json",
            "cases_v0_2.json",
            "references_v0_2.json",
            "pdp_cases_v0_1.json",
            "benchmark_manifest_v0_2.json",
        ],
        "hallazgos_de_auditoria_cerrados": {
            "B-01": (
                "Tablas DOCX seleccionadas por cabecera e identidad, con invariantes de "
                "contenido y Anexo B bidireccional. Cero o varias candidatas es un fallo."
            ),
            "B-02": (
                "Corpus de rendimiento sintético no degenerado: 5.000 mensajes, 500 recuerdos, "
                "50 decisiones, 2 proyectos reales y distribuciones publicadas."
            ),
            "B-03": "Cierre EXHAUSTIVO de CA-47 rederivado del corpus y verificado por cálculo.",
            "B-04": (
                "Solo PDP-CA-09 y PDP-CA-22 son casos funcionales; los seis de disciplina son "
                "reglas de protocolo del arnés."
            ),
        },
        "hallazgos_no_tratados_en_esta_ronda": {
            "ADR002-TOL-207": (
                "Presupuesto absoluto de almacenamiento: no se aprueba ni se modifica. Su "
                "cálculo depende de medir sobre este corpus de rendimiento, y T0 no se ha "
                "ejecutado."
            )
        },
    }


def _volcar(ruta: Path, datos: dict[str, Any]) -> int:
    texto = json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=False) + "\n"
    ruta.write_text(texto, encoding="utf-8")
    return len(texto.encode("utf-8"))


def construir_todo() -> dict[str, dict[str, Any]]:
    canon = CS3.cargar_canon()
    conformidad = construir_corpus_conformidad(canon)
    rendimiento = construir_corpus_rendimiento(canon)
    casos = construir_casos(canon, conformidad)
    referencias = construir_referencias(casos)
    pdp = construir_casos_pdp(canon)
    reglas = construir_reglas_de_arnes(canon)
    proyeccion = construir_proyeccion_t0(casos)
    manifiesto = construir_manifiesto(
        canon, conformidad, rendimiento, casos, referencias, pdp, reglas, proyeccion
    )
    return {
        "conformance_corpus_v0_3.json": conformidad,
        "performance_corpus_v0_2.json": rendimiento,
        "cases_v0_3.json": casos,
        "references_v0_3.json": referencias,
        "pdp_cases_v0_2.json": pdp,
        "pdp_harness_rules_v0_1.json": reglas,
        "t0_preexecution_projection_v0_1.json": proyeccion,
        "benchmark_manifest_v0_3.json": manifiesto,
    }


def escribir_en(directorio: Path) -> dict[str, int]:
    """Escribe los artefactos donde se le indique.

    El validador lo usa para regenerar en un directorio temporal: validar nunca
    escribe en el árbol del repositorio (§7.1).
    """
    directorio.mkdir(parents=True, exist_ok=True)
    return {n: _volcar(directorio / n, d) for n, d in construir_todo().items()}


def main() -> None:
    for nombre, tamano in escribir_en(AQUI).items():
        print(f"{nombre}: {tamano} bytes")


if __name__ == "__main__":
    main()
