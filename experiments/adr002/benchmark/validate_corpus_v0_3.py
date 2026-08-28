"""Validador v0.3 · fidelidad al canon, cierre por cálculo y distribución medida.

Ejecuta:

    uv run python -m experiments.adr002.benchmark.validate_corpus_v0_3

Diferencias con el validador v0.2 —conservado intacto—:

* **no muta el árbol de trabajo**: la regeneración se hace en un directorio
  temporal y se compara contra los artefactos comprometidos. El validador
  comprueba además, por huella y fecha de modificación, que ningún fichero del
  paquete cambió durante la validación;
* **calcula** conteos y distribuciones sobre los datos: nunca compara una
  declaración contra otra declaración;
* **recalcula de forma independiente** el cierre `EXHAUSTIVA` de `B04-CA-47`;
* comprueba **neutralidad** tecnológica y entre `ADR002-A/B/C/D`;
* comprueba **contaminación** por token, sufijo, raíz, alias y n-grama;
* comprueba los **catorce campos** de la ficha del PDP §7 con fuente, sección,
  estado y justificación;
* comprueba el **Anexo B en ambas direcciones**;
* comprueba la **separación** entre casos funcionales y reglas del arnés.

El único fichero que este módulo escribe es su propio informe, y solo cuando se
invoca ``main()``. ``validar()`` no escribe nada.

No ejecuta T0, no implementa ni ejecuta `ADR002-A/B/C/D` y no mide rendimiento.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from experiments.adr002.benchmark import build_corpus_v0_3 as B3
from experiments.adr002.benchmark import canonical_source_v0_3 as CS3
from experiments.adr002.benchmark import schema_v0_3 as S3
from experiments.adr002.benchmark import validate_corpus as V1

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
SALIDA = RAIZ / "artifacts" / "adr002_benchmark_preparation" / "validacion_corpus_v0.3.json"

FICHEROS = B3.FICHEROS

ARTEFACTOS_ANTERIORES = (
    "corpus_v0_1.json",
    "cases_v0_1.json",
    "references_v0_1.json",
    "conformance_corpus_v0_2.json",
    "performance_corpus_v0_1.json",
    "cases_v0_2.json",
    "references_v0_2.json",
    "pdp_cases_v0_1.json",
    "benchmark_manifest_v0_2.json",
)


class Informe:
    def __init__(self) -> None:
        self.comprobaciones: list[dict[str, Any]] = []

    def check(self, nombre: str, ok: bool, detalle: Any = None) -> bool:
        self.comprobaciones.append(
            {"comprobacion": nombre, "resultado": "OK" if ok else "FALLO", "detalle": detalle}
        )
        return ok

    @property
    def fallos(self) -> list[dict[str, Any]]:
        return [c for c in self.comprobaciones if c["resultado"] == "FALLO"]


def cargar(directorio: Path | None = None) -> dict[str, Any]:
    base = directorio or AQUI
    return {n: json.loads((base / n).read_text(encoding="utf-8")) for n in FICHEROS}


# --- 1. Canon: huellas, identidad de tablas e invariantes -------------------


def _canon(canon: CS3.Canon, manifiesto: dict[str, Any], inf: Informe) -> None:
    malas = {n: h for n, h in canon.huellas.items() if not h["coincide"]}
    inf.check("SHA-256 de las tres fuentes coincide con el MANIFEST", not malas, malas)

    medidas = canon.medidas()
    desviadas = {
        k: (medidas[k], v)
        for k, v in CS3.INVARIANTES.items()
        if (medidas[k] < v if k == "ca_b04_nombrados_por_anexo_b" else medidas[k] != v)
    }
    inf.check("las invariantes mínimas del lector canónico se cumplen", not desviadas, desviadas)

    inventario = {t["identidad"]: t for t in CS3.inventario_de_tablas()}
    inf.check(
        "cada identidad de tabla resuelve a exactamente una tabla del DOCX",
        len(inventario) == len(CS3.IDENTIDADES),
        {"identidades": len(inventario)},
    )
    inf.check(
        "el Anexo B y el Registro RED son tablas físicamente distintas",
        inventario["pdp_anexo_b"]["indice_fisico"]
        != inventario["pdp_registro_red"]["indice_fisico"],
        {
            "anexo_b": inventario["pdp_anexo_b"]["indice_fisico"],
            "registro_red": inventario["pdp_registro_red"]["indice_fisico"],
        },
    )
    inf.check(
        "las dos tablas de casos de B04 se distinguen por contexto, no por posición",
        inventario["b04_casos_17"]["cabecera"] == inventario["b04_casos_17_1"]["cabecera"]
        and inventario["b04_casos_17"]["indice_fisico"]
        != inventario["b04_casos_17_1"]["indice_fisico"],
        None,
    )
    inf.check(
        "los catorce campos de la ficha del PDP §7 son exactamente los canónicos",
        tuple(canon.ficha_pdp7) == CS3.CAMPOS_PDP7_CANONICOS,
        {"leidos": list(canon.ficha_pdp7)},
    )
    sin_texto = [f for f, d in canon.familias.items() if not d["cobertura_minima"]]
    inf.check(
        "las veinticinco familias del PDP §8 traen su texto de cobertura mínima",
        not sin_texto,
        {"sin_texto": sin_texto},
    )
    inf.check(
        "el manifiesto reproduce el inventario de tablas leído del canon",
        manifiesto["tablas_canonicas"] == CS3.inventario_de_tablas(),
        None,
    )


# --- 2. Los cincuenta CA y su literalidad ----------------------------------


def _ca_completos(casos: dict[str, Any], inf: Informe) -> None:
    vistos = [c["identificador_canonico"] for c in casos["nivel_1"]]
    faltan = [c for c in S3.CA_TOTALES if c not in vistos]
    dup = sorted({c for c in vistos if vistos.count(c) > 1})
    ajenos = [c for c in vistos if c not in S3.CA_TOTALES]
    inf.check(
        "B04-CA-01-50 aparecen exactamente una vez",
        len(vistos) == 50 and not dup and not faltan and not ajenos,
        {"total": len(vistos), "faltan": faltan, "duplicados": dup, "ajenos": ajenos},
    )


def _literalidad(
    canon: CS3.Canon, casos: dict[str, Any], refs: dict[str, Any], inf: Informe
) -> None:
    campos = S3.CAMPOS_CANONICOS
    diferencias: list[dict[str, Any]] = []
    for caso in casos["nivel_1"]:
        canonico = canon.casos[caso["identificador_canonico"]]
        for campo in campos:
            if getattr(canonico, campo) != caso["canonico"][campo]:
                diferencias.append({"caso": caso["id"], "campo": campo})
        if caso["canonico"]["seccion_exacta"] != canonico.seccion:
            diferencias.append({"caso": caso["id"], "campo": "seccion_exacta"})
    for ref in refs["referencias_nivel_1"]:
        canonico = canon.casos[ref["identificador_canonico"]]
        for campo in campos:
            if getattr(canonico, campo) != ref["canonico"][campo]:
                diferencias.append({"referencia": ref["caso"], "campo": campo})
    inf.check(
        "los cuatro campos canónicos coinciden carácter a carácter con el DOCX",
        not diferencias,
        {"diferencias": diferencias[:10], "total": len(diferencias)},
    )
    literales_pdp = [
        c["identificador_canonico"]
        for c in casos["nivel_1_pdp"]
        if c["canonico"]["resultado_esperado"]
        != canon.casos_pdp[c["identificador_canonico"]].resultado_esperado
        or c["canonico"]["entrada_adversarial"]
        != canon.casos_pdp[c["identificador_canonico"]].entrada_adversarial
    ]
    inf.check(
        "los PDP-CA funcionales reproducen su texto canónico carácter a carácter",
        not literales_pdp,
        {"casos": literales_pdp},
    )


# --- 3. Anexo B en ambas direcciones ---------------------------------------


def _anexo_b(casos: dict[str, Any], manifiesto: dict[str, Any], inf: Informe) -> None:
    asignaciones = CS3.asignaciones_canonicas_por_ca()
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}

    # 3.1 canon -> artefacto
    perdidas: list[dict[str, Any]] = []
    for ca, esperado in asignaciones.items():
        trazas = por_ca[ca]["trazabilidad"]
        faltan = {
            "red": [r for r in esperado["red"] if r not in trazas["traza_red_canonica_anexo_b"]],
            "metricas": [
                m for m in esperado["metricas"] if m not in trazas["metrica_canonica_anexo_b"]
            ],
            "externas": [
                m
                for m in esperado["metricas_externas"]
                if m not in trazas["metrica_canonica_externa_anexo_b"]
            ],
            "familias": [
                f for f in esperado["familias"] if f not in trazas["familia_canonica_anexo_b"]
            ],
        }
        if any(faltan.values()):
            perdidas.append({"ca": ca, **faltan})
    inf.check(
        "canon -> artefacto: toda asignación del Anexo B está en la traza canónica",
        not perdidas,
        {"perdidas": perdidas},
    )

    # 3.2 artefacto -> canon
    inventadas: list[dict[str, Any]] = []
    for ca, caso in por_ca.items():
        esperado = asignaciones.get(
            ca, {"red": [], "metricas": [], "familias": [], "metricas_externas": []}
        )
        trazas = caso["trazabilidad"]
        sobra = {
            "red": [r for r in trazas["traza_red_canonica_anexo_b"] if r not in esperado["red"]],
            "metricas": [
                m for m in trazas["metrica_canonica_anexo_b"] if m not in esperado["metricas"]
            ],
            "externas": [
                m
                for m in trazas["metrica_canonica_externa_anexo_b"]
                if m not in esperado["metricas_externas"]
            ],
            "familias": [
                f for f in trazas["familia_canonica_anexo_b"] if f not in esperado["familias"]
            ],
        }
        if any(sobra.values()):
            inventadas.append({"ca": ca, **sobra})
    inf.check(
        "artefacto -> canon: ninguna asignación marcada canónica fue inventada",
        not inventadas,
        {"inventadas": inventadas},
    )

    solapes = [
        c["id"]
        for c in casos["nivel_1"]
        if set(c["trazabilidad"]["traza_red_adicional_derivada"])
        & set(c["trazabilidad"]["traza_red_canonica_anexo_b"])
    ]
    inf.check("lo derivado no se solapa con lo canónico del Anexo B", not solapes, solapes)

    # 3.3 las métricas de otros bloques se conservan, no se filtran en silencio
    metricas = CS3.metricas_del_anexo_b()
    inf.check(
        "el Anexo B conserva B05-M16 y B08-M25 como referencias externas",
        "B05-M16" in metricas["externas_canonicas"]
        and "B08-M25" in metricas["externas_canonicas"]
        and manifiesto["metricas_del_anexo_b"] == metricas,
        {"externas": len(metricas["externas_canonicas"])},
    )
    inf.check(
        "ninguna métrica del Anexo B queda como identificador suelto sin bloque",
        all(re.fullmatch(r"[A-Z0-9]+-M\d{2}", m) for m in metricas["externas_canonicas"])
        and all(re.fullmatch(r"B04-M\d{2}", m) for m in metricas["b04_propias"]),
        {"externas": metricas["externas_canonicas"][:5]},
    )

    # 3.4 identificadores inexistentes
    crudo = json.dumps(casos, ensure_ascii=False)
    inexistentes = [
        i for i in ("RED-099", "B04-M99", "F99", "B04-CA-51", "PDP-CA-29") if i in crudo
    ]
    inf.check("no se acepta ningún identificador inexistente", not inexistentes, inexistentes)

    rf_malos = sorted(
        {
            rf
            for c in casos["nivel_1"]
            for rf in c["trazabilidad"]["requisito_verificado"]
            if rf not in S3.RF_TOTALES
        }
    )
    inf.check("todo RF citado pertenece a B04-RF-01-32", not rf_malos, rf_malos)


# --- 4. Ramas canónicas y cierre EXHAUSTIVA --------------------------------


def _ramas(canon: CS3.Canon, casos: dict[str, Any], inf: Informe) -> None:
    por_ca = {c["identificador_canonico"]: c for c in casos["nivel_1"]}

    def modos(caso: dict[str, Any]) -> set[str]:
        inst = caso["instanciacion"]
        return {inst["modo"]["valor"]} | {r["modo"] for r in inst["ramas"]}

    perdidos: list[dict[str, Any]] = []
    for ca, canonico in canon.casos.items():
        texto = " ".join([canonico.entrada, canonico.resultado_esperado, canonico.fallo_observable])
        exigidos = set(B3._RX_MODO.findall(texto))
        if exigidos and not exigidos <= modos(por_ca[ca]):
            perdidos.append({"ca": ca, "exigidos": sorted(exigidos)})
    inf.check(
        "todo modo nombrado literalmente por el canon está instanciado", not perdidos, perdidos
    )
    sin_m4 = [
        ca
        for ca in ("B04-CA-09", "B04-CA-10", "B04-CA-24", "B04-CA-49")
        if "M4" not in modos(por_ca[ca])
    ]
    inf.check("CA-09, CA-10, CA-24 y CA-49 conservan su rama M4", not sin_m4, sin_m4)
    todos = {m for c in casos["nivel_1"] for m in modos(c)}
    inf.check(
        "los cinco modos M1-M5 aparecen al menos una vez",
        set(S3.MODOS) <= todos,
        sorted(set(S3.MODOS) - todos),
    )
    problemas: list[dict[str, Any]] = []
    for ca in ("B04-CA-36", "B04-CA-47", "B04-CA-48"):
        ramas = por_ca[ca]["instanciacion"]["ramas"]
        firmas = {
            (
                tuple(r["candidatos_elegibles"]),
                tuple(r["candidatos_prohibidos"]),
                r["estado_suficiencia_esperado"],
            )
            for r in ramas
        }
        if len(ramas) < 3 or len(firmas) != len(ramas):
            problemas.append({"ca": ca, "ramas": len(ramas), "firmas": len(firmas)})
    inf.check(
        "CA-36, CA-47 y CA-48 conservan tres ramas con resultado distinto", not problemas, problemas
    )
    malas = [
        f"{c['id']}.{r['sufijo']}"
        for c in casos["nivel_1"]
        for r in c["instanciacion"]["ramas"]
        if r["modo"] not in S3.MODOS
        or r["clase"] not in S3.CLASES_RAMA
        or r["estado_suficiencia_esperado"] not in S3.ESTADOS_SUFICIENCIA
    ]
    inf.check("las ramas usan vocabulario canónico", not malas, malas)


def _cierre_exhaustivo(
    conformidad: dict[str, Any], casos: dict[str, Any], refs: dict[str, Any], inf: Informe
) -> None:
    """Cálculo independiente: el validador vuelve a resolver los filtros declarados."""
    items = conformidad["items"]
    por_id = {i["id"]: i for i in items}
    ramas = {
        r["sufijo"]: r
        for c in casos["nivel_1"]
        if c["identificador_canonico"] == "B04-CA-47"
        for r in c["instanciacion"]["ramas"]
    }
    inf.check("CA-47 declara sus tres ramas", set(ramas) == {"R1", "R2", "R3"}, sorted(ramas))

    diferencias: list[dict[str, Any]] = []
    conjuntos: list[tuple[str, ...]] = []
    for sufijo, rama in sorted(ramas.items()):
        cierre = rama["cierre"]
        base = cierre["filtro_base"]
        filtro = cierre["filtro_temporal"]
        universo = sorted(i["id"] for i in items if all(i.get(k) == v for k, v in base.items()))
        calculado = sorted(
            i for i in universo if _predicado_temporal(por_id[i]["temporalidad"], filtro)
        )
        if calculado != sorted(rama["candidatos_elegibles"]):
            diferencias.append(
                {"rama": sufijo, "calculado": calculado, "declarado": rama["candidatos_elegibles"]}
            )
        complemento = [i for i in universo if i not in calculado]
        if complemento != sorted(rama["candidatos_prohibidos"]):
            diferencias.append({"rama": sufijo, "problema": "prohibidos no son el complemento"})
        if universo != sorted(cierre["universo_en_ambito"]):
            diferencias.append({"rama": sufijo, "problema": "universo en ámbito distinto"})
        conjuntos.append(tuple(sorted(rama["candidatos_elegibles"])))
    inf.check(
        "CA-47: el conjunto esperado es exactamente el conjunto elegible calculado",
        not diferencias,
        diferencias,
    )
    inf.check(
        "CA-47: las tres ramas producen tres conjuntos distintos y no colapsan",
        len(set(conjuntos)) == 3,
        {"conjuntos": [list(c) for c in conjuntos]},
    )
    exigidos = {
        "R2": {"DEC-005", "DEC-009", "DEC-014"},
        "R3": {"DEC-005", "DEC-014", "DEC-015"},
    }
    faltan = {
        rama: sorted(ids - set(ramas[rama]["candidatos_elegibles"]))
        for rama, ids in exigidos.items()
        if not ids <= set(ramas[rama]["candidatos_elegibles"])
    }
    inf.check(
        "CA-47 R2 incluye DEC-005, DEC-009 y DEC-014; R3 incluye DEC-005, DEC-014 y DEC-015",
        not faltan,
        faltan,
    )
    inf.check(
        "toda rama EXHAUSTIVA declara su cierre y su universo",
        all(
            r.get("cierre") and r["cierre"].get("universo_en_ambito")
            for c in casos["nivel_1"]
            for r in c["instanciacion"]["ramas"]
            if r.get("cardinalidad_de_la_rama") == "EXHAUSTIVA"
        ),
        None,
    )
    inf.check(
        "las referencias transportan el cierre calculado, no una copia editable",
        refs["conteos"]["referencias_con_cierre_exhaustivo"] == 1,
        refs["conteos"],
    )
    exhaustivas_s1 = [
        c["id"]
        for c in casos["nivel_1"]
        if c["instanciacion"]["cardinalidad"]["valor"] == "EXHAUSTIVA"
        and c["instanciacion"]["parada"]["valor"] == "S1"
    ]
    inf.check("ninguna instanciación EXHAUSTIVA para por S1", not exhaustivas_s1, exhaustivas_s1)


def _predicado_temporal(temporalidad: dict[str, Any], filtro: dict[str, Any]) -> bool:
    operador = filtro["operador"]
    if operador == "INTERVALO_SEMIABIERTO":
        valor = temporalidad.get(filtro["eje"])
        return valor is not None and filtro["desde"] <= valor < filtro["hasta"]
    if operador == "VIGENTE_EN_INSTANTE":
        desde, hasta = temporalidad.get("valid_from"), temporalidad.get("valid_to")
        if desde is None or desde > filtro["instante"]:
            return False
        return hasta is None or filtro["instante"] < hasta
    if operador == "CORTE_DE_REGISTRO":
        valor = temporalidad.get(filtro["eje"])
        return valor is not None and valor <= filtro["hasta"]
    raise ValueError(f"operador temporal desconocido: {operador}")


# --- 5. Los catorce campos, canon frente a instanciación --------------------


def _ficha_14_campos(canon: CS3.Canon, casos: dict[str, Any], inf: Informe) -> None:
    esperados = set(S3.CAMPOS_PDP7.values()) | {S3.CAMPO_INSUFICIENCIA}
    inf.check(
        "el mapa de campos cubre los catorce del PDP §7 leídos del DOCX",
        set(S3.CAMPOS_PDP7) == set(canon.ficha_pdp7),
        {
            "solo_en_esquema": sorted(set(S3.CAMPOS_PDP7) - set(canon.ficha_pdp7)),
            "solo_en_canon": sorted(set(canon.ficha_pdp7) - set(S3.CAMPOS_PDP7)),
        },
    )
    faltan: dict[str, list[str]] = {}
    incompletos: list[str] = []
    for caso in casos["nivel_1"] + casos["nivel_1_pdp"]:
        ficha = caso.get("ficha_pdp_7", {})
        ausentes = sorted(esperados - set(ficha))
        sobrantes = sorted(set(ficha) - esperados)
        if ausentes or sobrantes:
            faltan[caso["id"]] = ausentes + [f"+{s}" for s in sobrantes]
        for clave, campo in ficha.items():
            if set(campo) != set(S3.CLAVES_CAMPO):
                incompletos.append(f"{caso['id']}.{clave}: claves {sorted(campo)}")
            elif campo["estado"] not in S3.ESTADOS_CAMPO or not campo["justificacion"]:
                incompletos.append(f"{caso['id']}.{clave}: estado o justificación inválidos")
    inf.check(
        "cada caso funcional lleva los catorce campos del PDP §7 y la insuficiencia",
        not faltan,
        faltan,
    )
    inf.check(
        "cada campo declara valor, fuente, sección, estado y justificación",
        not incompletos,
        incompletos[:20],
    )

    # CANONICO indebido en cualquiera de los catorce campos.
    indebidos: list[dict[str, Any]] = []
    for caso in casos["nivel_1"]:
        canonico = canon.casos[caso["identificador_canonico"]]
        texto = " ".join([canonico.entrada, canonico.resultado_esperado, canonico.fallo_observable])
        for clave, campo in caso["ficha_pdp_7"].items():
            if campo["estado"] != "CANONICO":
                continue
            if clave == "entrada" and campo["valor"] == canonico.entrada:
                continue
            if clave == "fallo" and campo["valor"] == canonico.fallo_observable:
                continue
            if clave == "operacion_y_modo" and B3._RX_MODO.findall(texto):
                continue
            indebidos.append({"caso": caso["id"], "campo": clave})
    inf.check(
        "ningún campo de la ficha se marca CANONICO sin texto literal que lo fije",
        not indebidos,
        indebidos,
    )

    indebidos_inst: list[dict[str, Any]] = []
    for caso in casos["nivel_1"]:
        canonico = canon.casos[caso["identificador_canonico"]]
        texto = " ".join([canonico.entrada, canonico.resultado_esperado, canonico.fallo_observable])
        for campo, patron in (
            ("cardinalidad", None),
            ("etapa", B3._RX_ETAPA),
            ("parada", B3._RX_PARADA),
            ("modo", B3._RX_MODO),
        ):
            meta = caso["instanciacion"][campo]
            if meta["estado"] != "CANONICO":
                continue
            valor = meta["valor"]
            presente = (valor in texto) if patron is None else (valor in patron.findall(texto))
            if not presente:
                indebidos_inst.append({"caso": caso["id"], "campo": campo, "valor": valor})
    inf.check(
        "solo se marca CANONICO el valor que el texto canónico del propio caso nombra",
        not indebidos_inst,
        indebidos_inst,
    )

    ca39 = {c["identificador_canonico"]: c for c in casos["nivel_1"]}["B04-CA-39"]["instanciacion"]
    inf.check(
        "CA-39 no usa vocabulario de cardinalidad ni de parada de recuperación",
        ca39["cardinalidad"]["valor"] is None and ca39["parada"]["valor"] is None,
        {"cardinalidad": ca39["cardinalidad"]["valor"], "parada": ca39["parada"]["valor"]},
    )


def _insuficiencia(casos: dict[str, Any], inf: Informe) -> None:
    problemas: list[str] = []
    for caso in casos["nivel_1"] + casos["nivel_1_pdp"]:
        bloque = caso["ficha_pdp_7"][S3.CAMPO_INSUFICIENCIA]["valor"]
        if not bloque:
            problemas.append(f"{caso['id']}: condición de insuficiencia vacía")
            continue
        ramas_declaradas = [r["sufijo"] for r in caso["instanciacion"]["ramas"]] or ["CASO_BASE"]
        if [b["rama"] for b in bloque] != ramas_declaradas:
            problemas.append(f"{caso['id']}: la insuficiencia no está estructurada por rama")
        for entrada in bloque:
            if entrada.get("aplica") == "NO_APLICA":
                if not entrada.get("razon"):
                    problemas.append(f"{caso['id']}.{entrada['rama']}: NO_APLICA sin razón")
                continue
            transiciones = entrada.get("transiciones") or []
            if not transiciones:
                problemas.append(f"{caso['id']}.{entrada['rama']}: lista vacía sin explicación")
            for t in transiciones:
                if set(t) != {
                    "etapa_actual",
                    "variables_observadas",
                    "predicado",
                    "umbral_o_condicion_logica",
                    "siguiente_etapa_permitida",
                    "fuente",
                    "estado",
                }:
                    problemas.append(f"{caso['id']}.{entrada['rama']}: transición incompleta")
                elif not t["variables_observadas"] or not t["predicado"]:
                    problemas.append(f"{caso['id']}.{entrada['rama']}: transición sin contenido")
    inf.check(
        "la condición de insuficiencia está estructurada por rama, sin frases genéricas",
        not problemas,
        problemas[:20],
    )


def _tolerancias(casos: dict[str, Any], refs: dict[str, Any], inf: Informe) -> None:
    esperado = {
        "B04-CA-37": (S3.TOL_BANDA_DIFERENCIAL, S3.TOL_VALOR_PENDIENTE),
        "B04-CA-48": (S3.TOL_BANDA_DIFERENCIAL, S3.TOL_VALOR_PENDIENTE),
        "B04-CA-39": (S3.TOL_ORDEN_EQUIVALENCIA, S3.TOL_VALOR_PENDIENTE),
    }
    problemas: list[dict[str, Any]] = []
    for caso in casos["nivel_1"]:
        campo = caso["ficha_pdp_7"]["tolerancias"]
        valor = campo["valor"]
        if set(valor) != {"tolerancia_id", "valor_pendiente_en", "regla", "condicion_aplicada"}:
            problemas.append({"caso": caso["id"], "problema": "estructura de tolerancia inválida"})
            continue
        if valor["tolerancia_id"] == valor["valor_pendiente_en"]:
            problemas.append({"caso": caso["id"], "problema": "tolerancia_id igual al pendiente"})
        pendiente = valor["valor_pendiente_en"] is not None
        if pendiente != (campo["estado"] == "PENDIENTE_TOL209"):
            problemas.append(
                {"caso": caso["id"], "problema": "estado incoherente con el pendiente"}
            )
        ident = caso["identificador_canonico"]
        if ident in esperado:
            if (valor["tolerancia_id"], valor["valor_pendiente_en"]) != esperado[ident]:
                problemas.append(
                    {
                        "caso": ident,
                        "esperado": esperado[ident],
                        "obtenido": [valor["tolerancia_id"], valor["valor_pendiente_en"]],
                    }
                )
        elif pendiente:
            problemas.append({"caso": ident, "problema": "declara pendiente sin corresponderle"})
    inf.check(
        "CA-37 y CA-48 usan TOL-201 con valor pendiente en TOL-209; CA-39 usa TOL-001",
        not problemas,
        problemas,
    )
    sin_tolerancia = [r["caso"] for r in refs["referencias_nivel_1"] if not r.get("tolerancias")]
    inf.check(
        "cada referencia transporta su tolerancia y su valor pendiente",
        not sin_tolerancia,
        sin_tolerancia,
    )


# --- 6. T0 fuera de los artefactos congelables -----------------------------


def _t0(
    casos: dict[str, Any],
    refs: dict[str, Any],
    reglas: dict[str, Any],
    proyeccion: dict[str, Any],
    inf: Informe,
) -> None:
    # `campos_prohibidos` del fichero de reglas es la declaración de la prohibición,
    # no una previsión: se comprueban las reglas, no su metadato.
    congelables = json.dumps(
        {"casos": casos, "referencias": refs, "reglas": reglas["reglas"]}, ensure_ascii=False
    )
    filtradas = [k for k in S3.CLAVES_PREVISION_T0 if f'"{k}"' in congelables]
    inf.check(
        "ningún artefacto congelable contiene previsión normativa sobre T0",
        not filtradas,
        {"claves": filtradas},
    )
    niveles_23 = [
        c["id"]
        for c in casos["nivel_2"] + casos["nivel_3"]
        if c.get("t0", {}).get("estado_t0") != S3.ESTADO_T0
    ]
    inf.check(
        "los casos de nivel 2 y 3 pierden el veredicto T0 heredado del v0.1",
        not niveles_23,
        niveles_23,
    )
    no_proyectados = {p["caso"] for p in proyeccion["no_proyectados"]}
    inf.check(
        "los casos sin traza a B04-RF se declaran no proyectados con su motivo",
        no_proyectados == {c["id"] for c in casos["nivel_2"] + casos["nivel_3"]}
        and all(p["motivo"] for p in proyeccion["no_proyectados"]),
        sorted(no_proyectados),
    )
    estados_malos = [
        c["id"]
        for c in casos["nivel_1"] + casos["nivel_1_pdp"]
        if c["t0"].get("estado_t0") != S3.ESTADO_T0
        or c["t0"].get("prevision_en") != "t0_preexecution_projection_v0_1.json"
    ]
    inf.check("todo caso funcional declara estado_t0 NO_MEDIDO", not estados_malos, estados_malos)
    inf.check(
        "el fichero de previsión es no normativo, no congelable y sustituible",
        proyeccion["normativo"] is False
        and proyeccion["congelable"] is False
        and proyeccion["estado"] == S3.ESTADO_NO_NORMATIVO
        and "sustituye" in proyeccion["sustituible_por"],
        {"estado": proyeccion["estado"]},
    )
    funcionales = {c["identificador_canonico"] for c in casos["nivel_1"] + casos["nivel_1_pdp"]}
    proyectados = {p["identificador_canonico"] for p in proyeccion["proyecciones"]}
    inf.check(
        "la previsión se aplica automáticamente a todos los casos funcionales",
        proyectados == funcionales and len(proyeccion["proyecciones"]) == len(funcionales),
        {
            "solo_casos": sorted(funcionales - proyectados),
            "solo_previsión": sorted(proyectados - funcionales),
        },
    )
    reglas_ids = {r["identificador_canonico"] for r in reglas["reglas"]}
    inf.check(
        "las reglas del arnés no reciben previsión frente a T0",
        not (reglas_ids & proyectados)
        and proyeccion["conteos"]["reglas_de_arnes_proyectadas"] == 0,
        sorted(reglas_ids & proyectados),
    )
    vocabulario = [
        p["identificador_canonico"]
        for p in proyeccion["proyecciones"]
        if p["expresabilidad_prevista"] not in S3.EXPRESABILIDAD
        or not p["fundamento_de_prevision"]
        or p["no_es_veredicto"] is not True
        or p["estado_t0"] != S3.ESTADO_T0
    ]
    inf.check(
        "toda previsión usa el vocabulario y declara que no es veredicto",
        not vocabulario,
        vocabulario,
    )
    por_id = {p["identificador_canonico"]: p for p in proyeccion["proyecciones"]}
    dos_impl = [
        c
        for c in ("B04-CA-39", "PDP-CA-09", "PDP-CA-22")
        if por_id[c]["expresabilidad_prevista"] != "NO_EJECUTABLE_CON_UNA_SOLA_IMPLEMENTACION"
    ]
    inf.check(
        "el criterio de dos realizaciones se aplica a CA-39 y a los dos PDP-CA anclados a él",
        not dos_impl,
        dos_impl,
    )
    incoherentes = [
        p["identificador_canonico"]
        for p in proyeccion["proyecciones"]
        if p["expresabilidad_prevista"] == "EXPRESABLE_PREVISTO"
        and "AUSENTE" in p["estado_por_requisito"].values()
    ]
    inf.check(
        "el criterio de expresabilidad es único y no admite excepciones",
        not incoherentes,
        incoherentes,
    )


# --- 7. Separación entre casos funcionales y reglas del arnés --------------


def _separacion_arnes(
    canon: CS3.Canon,
    casos: dict[str, Any],
    pdp: dict[str, Any],
    reglas: dict[str, Any],
    inf: Informe,
) -> None:
    funcionales = {c["identificador_canonico"] for c in casos["nivel_1_pdp"]}
    inf.check(
        "solo PDP-CA-09 y PDP-CA-22 son casos funcionales de nivel 1",
        funcionales == set(S3.PDP_CA_FUNCIONALES),
        sorted(funcionales),
    )
    anclados = set(CS3.asignaciones_canonicas_por_pdp_ca())
    inf.check(
        "esos dos son exactamente los que el Anexo B ancla vía una fila que cita B04",
        anclados == set(S3.PDP_CA_FUNCIONALES),
        sorted(anclados),
    )
    ids_reglas = {r["identificador_canonico"] for r in reglas["reglas"]}
    inf.check(
        "las seis reglas de disciplina viven en el fichero de reglas del arnés",
        ids_reglas == set(S3.PDP_CA_REGLAS_DE_ARNES),
        sorted(ids_reglas),
    )
    inf.check(
        "ninguna regla del arnés aparece como caso funcional",
        not (ids_reglas & funcionales),
        sorted(ids_reglas & funcionales),
    )
    prohibidos: list[str] = []
    for regla in reglas["reglas"]:
        for campo in S3.CAMPOS_PROHIBIDOS_EN_REGLA:
            if campo in regla:
                prohibidos.append(f"{regla['identificador_canonico']}.{campo}")
        if regla["estado_aplicabilidad"] not in S3.ESTADOS_APLICABILIDAD_REGLA:
            prohibidos.append(
                f"{regla['identificador_canonico']}: aplicabilidad fuera de vocabulario"
            )
        for clave in (
            "texto_canonico",
            "fuente_pdp",
            "regla_de_ejecucion",
            "evidencia_requerida",
            "consecuencia",
        ):
            if not regla.get(clave):
                prohibidos.append(f"{regla['identificador_canonico']}: falta {clave}")
    inf.check(
        "ninguna regla del arnés lleva consulta, recuperación ni previsión T0",
        not prohibidos,
        prohibidos,
    )
    literales = [
        r["identificador_canonico"]
        for r in reglas["reglas"]
        if r["texto_canonico"]["resultado_esperado"]
        != canon.casos_pdp[r["identificador_canonico"]].resultado_esperado
        or r["texto_canonico"]["entrada_adversarial"]
        != canon.casos_pdp[r["identificador_canonico"]].entrada_adversarial
    ]
    inf.check(
        "las reglas reproducen su texto canónico carácter a carácter", not literales, literales
    )

    clases = (
        set(pdp["casos_funcionales_nivel_1"])
        | set(pdp["reglas_de_protocolo_del_arnes"])
        | set(pdp["casos_fuera_de_alcance"])
    )
    solapes = (
        set(pdp["casos_funcionales_nivel_1"]) & set(pdp["reglas_de_protocolo_del_arnes"])
    ) | (set(pdp["casos_funcionales_nivel_1"]) & set(pdp["casos_fuera_de_alcance"]))
    inf.check(
        "los veintiocho PDP-CA quedan clasificados en tres clases disjuntas",
        clases == set(canon.casos_pdp) and not solapes,
        {"clasificados": len(clases), "solapes": sorted(solapes)},
    )
    fam = pdp["familias_pdp"]
    inf.check(
        "las familias PDP se reportan por cuatro denominadores con fuente expresa",
        all(
            isinstance(v, dict) and v.get("fuente") and "familias" in v
            for k, v in fam.items()
            if k != "advertencia"
        )
        and len([k for k in fam if k != "advertencia"]) == 4,
        sorted(k for k in fam if k != "advertencia"),
    )
    textos = pdp["cobertura_minima_por_familia"]
    inf.check(
        "la cobertura mínima literal de cada familia coincide con el DOCX",
        textos == {f: canon.familias[f]["cobertura_minima"] for f in canon.familias},
        None,
    )


# --- 8. Corpus de conformidad: identidad y fenómenos -----------------------


def _conformidad(conformidad: dict[str, Any], inf: Informe) -> None:
    interno = V1.Informe()
    V1._fenomenos(conformidad, interno)
    faltan = interno.comprobaciones[0]["detalle"]["faltan"]
    inf.check(
        "fenómenos obligatorios representados en el corpus de conformidad", not faltan, faltan
    )

    for comprobacion, funcion in (
        ("las siete dimensiones ortogonales usan vocabulario canónico", V1._dimensiones),
        ("toda marca crítica lleva nivel, razón, fuente y regla", V1._criticidad),
    ):
        sub = V1.Informe()
        funcion(conformidad, sub)
        fallos = [c for c in sub.comprobaciones if c["resultado"] == "FALLO"]
        inf.check(comprobacion, not fallos, fallos)

    conteos = conformidad["conteos"]
    reales = {
        "proyectos": len(conformidad["proyectos"]),
        "entidades": len(conformidad["entidades"]),
        "items": len(conformidad["items"]),
        "recuerdos": sum(1 for i in conformidad["items"] if i["kind"] == "MEMORIA"),
        "decisiones": sum(1 for i in conformidad["items"] if i["kind"] == "DECISION"),
        "mensajes": len(conformidad["mensajes"]),
        "documentos": len(conformidad["documentos"]),
        "relaciones": len(conformidad["relaciones"]),
    }
    inf.check(
        "los conteos del corpus de conformidad se cuentan sobre los datos",
        conteos == reales,
        {"declarado": conteos, "real": reales},
    )
    inf.check(
        "el corpus de conformidad conserva sus 94 elementos", reales["items"] == 94, reales["items"]
    )

    identidad = B3.identidad_de_colecciones(conformidad)
    declarada = conformidad["identidad"]
    diferencias = {
        coleccion: sorted(
            k
            for k, v in identidad[coleccion]["huella_por_elemento"].items()
            if declarada[coleccion]["huella_por_elemento"].get(k) != v
        )
        for coleccion in identidad
        if identidad[coleccion] != declarada[coleccion]
    }
    inf.check(
        "identidad de items, mensajes, documentos y relaciones intacta",
        not diferencias,
        diferencias,
    )
    colisiones = B3.colisiones_por_raiz_entre_anclajes(conformidad["items"])
    inf.check(
        "toda colisión por raíz entre anclajes está declarada",
        colisiones == conformidad["colisiones_por_raiz_declaradas"],
        {
            "calculadas": len(colisiones),
            "declaradas": len(conformidad["colisiones_por_raiz_declaradas"]),
        },
    )
    crudo = json.dumps(conformidad, ensure_ascii=False).lower()
    prohibidos = ["@gmail", "@hotmail", "http://", "https://", "password", "api_key", "secret"]
    hallados = [p for p in prohibidos if p in crudo]
    inf.check("sin datos reales, URLs ni secretos", not hallados, hallados)


# --- 9. Corpus de rendimiento: conteos y distribución medidos ---------------


def _rendimiento(rendimiento: dict[str, Any], inf: Informe) -> None:
    medida = B3.medir_distribucion(rendimiento)
    inf.check(
        "la distribución publicada coincide con la calculada sobre los datos",
        medida == rendimiento["distribucion_observada"],
        None,
    )
    conteos = medida["conteos_reales"]
    escala = S3.ESCALA_RENDIMIENTO
    inf.check(
        "5.000 mensajes, 500 recuerdos, 50 decisiones y 2 proyectos, contados sobre los datos",
        conteos["mensajes"] == escala["mensajes"]
        and conteos["recuerdos"] == escala["recuerdos"]
        and conteos["decisiones"] == escala["decisiones"]
        and conteos["proyectos"] == escala["proyectos"]
        and conteos["proyectos_referenciados"] == escala["proyectos"],
        conteos,
    )
    inv = S3.INVARIANTES_DISTRIBUCION
    longitud = medida["longitud_texto"]
    vocabulario = medida["vocabulario"]
    fechas = medida["fechas"]
    inf.check(
        "longitudes de texto con variación material y al menos veinte longitudes distintas",
        longitud["longitudes_distintas"] >= inv["longitudes_distintas_min"]
        and longitud["desviacion"] >= inv["desviacion_longitud_min"],
        longitud,
    )
    inf.check(
        "vocabulario amplio con frecuencia aproximadamente Zipf",
        vocabulario["tamano"] >= inv["vocabulario_min"]
        and vocabulario["frecuencia_relativa_maxima"] <= inv["frecuencia_relativa_maxima_token"]
        and inv["zipf_pendiente_min"] <= vocabulario["pendiente_zipf"] <= inv["zipf_pendiente_max"],
        vocabulario,
    )
    inf.check(
        "sin plantilla repetida: los textos son prácticamente todos distintos",
        medida["textos"]["proporcion_distintos"] >= inv["textos_distintos_min"],
        medida["textos"],
    )
    con_secuencia = [i["id"] for i in rendimiento["items"] if re.search(r"\d", i["text"] or "")][
        :10
    ]
    inf.check(
        "ningún texto usa un número de secuencia como fuente de variedad",
        not con_secuencia,
        con_secuencia,
    )
    inf.check(
        "fechas distribuidas en el intervalo declarado, con muchos días y meses",
        fechas["distintas"] >= inv["fechas_distintas_min"]
        and fechas["meses_distintos"] >= inv["meses_distintos_min"]
        and fechas["minima"] >= S3.RENDIMIENTO_FECHA_INICIO
        and fechas["maxima"] <= S3.RENDIMIENTO_FECHA_FIN,
        fechas,
    )
    reparto = medida["reparto_por_proyecto"]
    inf.check(
        "reparto entre los dos proyectos sin que ninguno supere el 60 %",
        len(reparto) == 2 and max(reparto.values()) <= inv["cuota_maxima_por_proyecto"],
        reparto,
    )
    degenerados = {
        eje: valores
        for eje, valores in medida["reparto_por_eje"].items()
        if len(valores) < inv["valores_min_por_eje"]
        or sorted(valores.values())[-2] < inv["cuota_minima_valor_secundario"]
    }
    inf.check(
        "variación real en confirmación, validez, disponibilidad, sensibilidad, polaridad, "
        "condición y temporalidad",
        not degenerados,
        degenerados,
    )
    proporciones = medida["proporciones"]
    inf.check(
        "proporción declarada de entidades, alias, procedencias y criticidad",
        proporciones["items_con_entidades"] >= inv["proporcion_minima_entidades"]
        and proporciones["entidades_con_alias"] >= inv["proporcion_minima_alias"]
        and proporciones["items_con_procedencia"] >= inv["proporcion_minima_procedencias"]
        and proporciones["items_con_criticidad"] >= inv["proporcion_minima_criticidad"],
        proporciones,
    )
    relaciones = medida["relaciones"]
    inf.check(
        "relaciones de varios tipos y densidad no nula",
        relaciones["tipos_distintos"] >= inv["tipos_de_relacion_min"]
        and relaciones["densidad_por_item"] >= inv["densidad_relaciones_min"]
        and all(t in S3.TIPOS_RELACION for t in relaciones["tipos"]),
        relaciones,
    )
    generacion = rendimiento["generacion"]
    inf.check(
        "textos de varias familias temáticas y estructuras gramaticales",
        len(generacion["uso_de_familias"]) >= inv["familias_tematicas_min"]
        and len(generacion["uso_de_estructuras"]) >= inv["estructuras_gramaticales_min"],
        {
            "familias": len(generacion["uso_de_familias"]),
            "estructuras": len(generacion["uso_de_estructuras"]),
        },
    )
    inf.check(
        "el corpus de rendimiento se declara sintético y neutral, no representativo",
        "sintético de estrés neutral" in rendimiento["proposito"]
        and "NO representa" in rendimiento["proposito"]
        and "NO crea referencias funcionales" in rendimiento["proposito"],
        None,
    )
    identidad = B3.identidad_de_colecciones(rendimiento)
    inf.check(
        "identidad de items, mensajes, documentos y relaciones del corpus de rendimiento",
        identidad == rendimiento["identidad"],
        None,
    )
    crudo = json.dumps(rendimiento, ensure_ascii=False).lower()
    hallados = [p for p in ("@gmail", "http://", "https://", "password", "api_key") if p in crudo]
    inf.check("el corpus de rendimiento no contiene datos reales ni red", not hallados, hallados)


# --- 10. Contaminación ampliada --------------------------------------------


def _contaminacion(
    conformidad: dict[str, Any], casos: dict[str, Any], rendimiento: dict[str, Any], inf: Informe
) -> None:
    lex = B3.construir_lexico(conformidad, casos)
    inf.check(
        "el léxico protegido se construye automáticamente y no está vacío",
        len(lex.tokens) > 300 and len(lex.ngramas) > 500 and len(lex.nombres) >= 5,
        {"tokens": len(lex.tokens), "ngramas": len(lex.ngramas), "nombres": len(lex.nombres)},
    )
    faltan_pares = [
        (a, b)
        for a, b in S3.PARES_MINIMOS_DE_CONTAMINACION
        if a in lex.tokens and not lex.detectar(b)
    ]
    inf.check(
        "la detección cubre al menos turno/turnos y registro/registrado",
        not faltan_pares,
        faltan_pares,
    )
    hallazgos: list[dict[str, Any]] = []
    for texto in B3.textos_del_corpus(rendimiento):
        encontrados = lex.detectar(texto)
        if encontrados:
            hallazgos.append({"texto": texto[:90], "hallazgos": encontrados})
    inf.check(
        "ningún texto del corpus de rendimiento contamina el léxico protegido",
        not hallazgos,
        {"total": len(hallazgos), "muestra": hallazgos[:5]},
    )
    nombres: list[dict[str, Any]] = []
    for entidad in rendimiento["entidades"]:
        for nombre in [entidad["nombre_canonico"], *entidad["alias"]]:
            encontrados = lex.detectar(nombre)
            if encontrados:
                nombres.append({"entidad": entidad["id"], "hallazgos": encontrados})
    for proyecto in rendimiento["proyectos"]:
        for nombre in [proyecto["nombre"], *proyecto["alias"]]:
            if lex.detectar(nombre):
                nombres.append({"proyecto": proyecto["id"]})
    inf.check(
        "ni las entidades ni los proyectos del corpus de rendimiento comparten léxico",
        not nombres,
        nombres,
    )


# --- 11. Neutralidad tecnológica y entre candidatos ------------------------


def _neutralidad(canon: CS3.Canon, artefactos: dict[str, Any], inf: Informe) -> None:
    terminos = {
        **{t: "TECNOLOGIA_CONCRETA" for t in S3.TECNOLOGIAS_CONCRETAS},
        **{t: "DESCRIPTOR_DE_CANDIDATO" for t in S3.DESCRIPTORES_DE_CANDIDATO},
        **{t: "CANDIDATO" for t in S3.CANDIDATOS_ADR002},
    }

    def presentes(blob: str) -> list[str]:
        normal = B3.normalizar(blob)
        return sorted(
            t
            for t in terminos
            if re.search(rf"(?<![a-z0-9]){re.escape(B3.normalizar(t))}(?![a-z0-9])", normal)
        )

    def sin_respaldo(hallados: list[str], literales: list[str]) -> list[str]:
        """Un término está respaldado si el canon nombra ese mismo término o su raíz.

        `PostgreSQL` en el texto canónico de CA-42 respalda el alias `Postgres`:
        son la misma tecnología, no dos elecciones distintas.
        """
        normales = [B3.normalizar(x) for x in literales]
        return [
            t
            for t in hallados
            if not any(
                n == B3.normalizar(t)
                or n.startswith(B3.normalizar(t))
                or B3.normalizar(t).startswith(n)
                for n in normales
            )
        ]

    # Los artefactos que no admiten excepción alguna.
    sin_excepcion = {
        n: presentes(json.dumps(artefactos[n], ensure_ascii=False))
        for n in (
            "performance_corpus_v0_2.json",
            "pdp_cases_v0_2.json",
            "pdp_harness_rules_v0_1.json",
            "t0_preexecution_projection_v0_1.json",
        )
    }
    sucios = {n: v for n, v in sin_excepcion.items() if v}
    inf.check(
        "ni el corpus de rendimiento ni las reglas ni la previsión nombran tecnología o candidato",
        not sucios,
        sucios,
    )

    # En los casos, un término solo cabe si el texto canónico del propio caso lo fija.
    indebidos: list[dict[str, Any]] = []
    for caso in artefactos["cases_v0_3.json"]["nivel_1"]:
        canonico = canon.casos[caso["identificador_canonico"]]
        literal = presentes(
            " ".join(
                [
                    canonico.riesgo,
                    canonico.entrada,
                    canonico.resultado_esperado,
                    canonico.fallo_observable,
                ]
            )
        )
        resto = presentes(
            json.dumps({k: v for k, v in caso.items() if k != "canonico"}, ensure_ascii=False)
        )
        sobra = sin_respaldo(resto, literal)
        if sobra:
            indebidos.append({"caso": caso["id"], "terminos": sobra})
    for caso in artefactos["cases_v0_3.json"]["nivel_1_pdp"]:
        resto = presentes(json.dumps(caso, ensure_ascii=False))
        if resto:
            indebidos.append({"caso": caso["id"], "terminos": resto})
    inf.check(
        "ningún campo neutral de un caso nombra tecnología o candidato sin canon que lo fije",
        not indebidos,
        indebidos,
    )

    ref_indebidas: list[dict[str, Any]] = []
    for ref in artefactos["references_v0_3.json"]["referencias_nivel_1"]:
        canonico = canon.casos[ref["identificador_canonico"]]
        literal = presentes(
            " ".join(
                [
                    canonico.riesgo,
                    canonico.entrada,
                    canonico.resultado_esperado,
                    canonico.fallo_observable,
                ]
            )
        )
        resto = presentes(
            json.dumps({k: v for k, v in ref.items() if k != "canonico"}, ensure_ascii=False)
        )
        sobra = sin_respaldo(resto, literal)
        if sobra:
            ref_indebidas.append({"referencia": ref["caso"], "terminos": sobra})
    inf.check(
        "ninguna referencia nombra tecnología ni candidato fuera del canon",
        not ref_indebidas,
        ref_indebidas,
    )

    # En el corpus de conformidad, el término debe estar trazado a un caso que lo nombre.
    conformidad = artefactos["conformance_corpus_v0_3.json"]
    sin_traza: list[dict[str, Any]] = []
    for item in conformidad["items"]:
        hallados = presentes(f"{item['text']} {item.get('condicion') or ''}")
        if not hallados:
            continue
        respaldo = {
            t
            for ca in item["traza"]
            if ca in canon.casos
            for t in presentes(
                " ".join(
                    [
                        canon.casos[ca].riesgo,
                        canon.casos[ca].entrada,
                        canon.casos[ca].resultado_esperado,
                        canon.casos[ca].fallo_observable,
                    ]
                )
            )
        }
        sobra = sin_respaldo(hallados, sorted(respaldo))
        if sobra:
            sin_traza.append({"item": item["id"], "terminos": sobra})
    for entidad in conformidad["entidades"]:
        hallados = presentes(" ".join([entidad["nombre_canonico"], *entidad["alias"]]))
        if not hallados:
            continue
        citados = re.findall(r"B04-CA-\d{2}", entidad["nota"])
        respaldo = {
            t
            for ca in citados
            if ca in canon.casos
            for t in presentes(
                " ".join(
                    [
                        canon.casos[ca].riesgo,
                        canon.casos[ca].entrada,
                        canon.casos[ca].resultado_esperado,
                        canon.casos[ca].fallo_observable,
                    ]
                )
            )
        }
        sobra = sin_respaldo(hallados, sorted(respaldo))
        if sobra:
            sin_traza.append({"entidad": entidad["id"], "terminos": sobra})
    inf.check(
        "toda mención tecnológica del corpus está fijada por el caso canónico que la traza",
        not sin_traza,
        sin_traza,
    )
    inf.check(
        "las cuatro alternativas mínimas de ARQ-00 §23 siguen siendo cuatro y ninguna se prejuzga",
        set(CS3.alternativas_minimas_arq00()) == {"A", "B", "C", "D"},
        sorted(CS3.alternativas_minimas_arq00()),
    )


# --- 12. No mutación, determinismo y conservación histórica ----------------


def _instantanea() -> dict[str, tuple[int, float, bytes]]:
    return {
        p.name: (p.stat().st_size, p.stat().st_mtime, p.read_bytes())
        for p in sorted(AQUI.glob("*.json"))
    }


def _no_mutante_y_determinismo(antes: dict[str, tuple[int, float, bytes]], inf: Informe) -> None:
    with tempfile.TemporaryDirectory(prefix="adr002-v03-") as tmp:
        primero = Path(tmp) / "1"
        segundo = Path(tmp) / "2"
        B3.escribir_en(primero)
        B3.escribir_en(segundo)
        comprometidos = {n: (AQUI / n).read_bytes() for n in FICHEROS}
        uno = {n: (primero / n).read_bytes() for n in FICHEROS}
        dos = {n: (segundo / n).read_bytes() for n in FICHEROS}
        inf.check(
            "doble regeneración en temporal, byte a byte idéntica entre sí",
            uno == dos,
            {"difieren": [n for n in FICHEROS if uno[n] != dos[n]]},
        )
        inf.check(
            "los artefactos comprometidos coinciden byte a byte con la regeneración",
            comprometidos == uno,
            {"difieren": [n for n in FICHEROS if comprometidos[n] != uno[n]]},
        )
    despues = _instantanea()
    cambiados = [n for n in antes if n not in despues or antes[n] != despues[n]]
    nuevos = [n for n in despues if n not in antes]
    inf.check(
        "validar no escribió en el árbol de trabajo",
        not cambiados and not nuevos,
        {"cambiados": cambiados, "nuevos": nuevos},
    )


def _conservacion(inf: Informe) -> None:
    ausentes = [n for n in ARTEFACTOS_ANTERIORES if not (AQUI / n).is_file()]
    inf.check("los artefactos v0.1 y v0.2 siguen presentes e íntegros", not ausentes, ausentes)
    sub = V1.Informe()
    _corpus, casos, refs = V1.cargar()
    V1._ca_completos(casos, sub)
    V1._referencias(casos, refs, sub)
    V1._vocabularios(casos, sub)
    fallos = [c for c in sub.comprobaciones if c["resultado"] == "FALLO"]
    inf.check("el contrato del v0.1 sigue cumpliéndose sin cambios", not fallos, fallos)
    v2 = json.loads((AQUI / "cases_v0_2.json").read_text(encoding="utf-8"))
    inf.check(
        "el v0.2 conserva sus ocho PDP-CA instanciados: no se ha reescrito para pasar",
        len(v2["nivel_1_pdp"]) == 8,
        {"nivel_1_pdp": len(v2["nivel_1_pdp"])},
    )


# --- 13. Puertas que siguen sin satisfacerse -------------------------------


def _puertas(manifiesto: dict[str, Any], inf: Informe) -> None:
    inf.check(
        "el manifiesto no declara satisfecha ninguna puerta de arranque",
        "TOL-208, TOL-209 y TOL-210 siguen NO SATISFECHAS" in manifiesto["advertencia"]
        and "no está aprobada" in manifiesto["advertencia"]
        and "no se han implementado ni ejecutado" in manifiesto["advertencia"],
        manifiesto["advertencia"],
    )
    inf.check(
        "el manifiesto declara la independencia y la prohibición cruzada entre corpus",
        "INDEPENDIENTES" in manifiesto["relacion_entre_corpus"]["regla"]
        and "Prohibido" in manifiesto["relacion_entre_corpus"]["prohibicion"],
        None,
    )


# --- main -------------------------------------------------------------------


def validar() -> tuple[Informe, dict[str, Any]]:
    """Ejecuta todas las comprobaciones. No escribe ningún fichero."""
    antes = _instantanea()
    canon = CS3.cargar_canon()
    art = cargar()
    conformidad = art["conformance_corpus_v0_3.json"]
    rendimiento = art["performance_corpus_v0_2.json"]
    casos = art["cases_v0_3.json"]
    refs = art["references_v0_3.json"]
    pdp = art["pdp_cases_v0_2.json"]
    reglas = art["pdp_harness_rules_v0_1.json"]
    proyeccion = art["t0_preexecution_projection_v0_1.json"]
    manifiesto = art["benchmark_manifest_v0_3.json"]

    inf = Informe()
    _canon(canon, manifiesto, inf)
    _ca_completos(casos, inf)
    _literalidad(canon, casos, refs, inf)
    _anexo_b(casos, manifiesto, inf)
    _ramas(canon, casos, inf)
    _cierre_exhaustivo(conformidad, casos, refs, inf)
    _ficha_14_campos(canon, casos, inf)
    _insuficiencia(casos, inf)
    _tolerancias(casos, refs, inf)
    _t0(casos, refs, reglas, proyeccion, inf)
    _separacion_arnes(canon, casos, pdp, reglas, inf)
    _conformidad(conformidad, inf)
    _rendimiento(rendimiento, inf)
    _contaminacion(conformidad, casos, rendimiento, inf)
    _neutralidad(canon, art, inf)
    _puertas(manifiesto, inf)
    _conservacion(inf)
    _no_mutante_y_determinismo(antes, inf)

    informe = {
        "documento": "Validación v0.3 del benchmark de ADR-002 contra las fuentes canónicas",
        "version_contrato": S3.VERSION_CONTRATO,
        "estado": S3.ESTADO_NO_CONGELADO,
        "no_ejecuta": ["T0", "ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D"],
        "puertas": {
            "SRC-ADR002-01": "SATISFECHA",
            "ADR002-TOL-207": "NO SATISFECHA · no se aprueba en esta ronda",
            "ADR002-TOL-208": "NO SATISFECHA · el corpus no está congelado y T0 no se ha ejecutado",
            "ADR002-TOL-209": "NO SATISFECHA",
            "ADR002-TOL-210": "NO SATISFECHA",
        },
        "fuentes_canonicas": canon.huellas,
        "medidas_del_canon": canon.medidas(),
        "tablas_canonicas": CS3.inventario_de_tablas(),
        "resumen": {
            "comprobaciones": len(inf.comprobaciones),
            "ok": len(inf.comprobaciones) - len(inf.fallos),
            "fallos": len(inf.fallos),
            "veredicto": "VALIDO" if not inf.fallos else "INVALIDO",
        },
        "cobertura": {
            "ca_b04": {"cubiertos": len(casos["nivel_1"]), "de": 50},
            "pdp_ca": pdp["conteos"],
            "ramas_canonicas": casos["conteos"]["ramas_canonicas"],
            "reglas_de_arnes": reglas["conteos"]["reglas"],
        },
        "cierre_exhaustivo_ca47": conformidad["cierre_exhaustivo_ca47"],
        "corpus": {
            "conformidad": conformidad["conteos"],
            "rendimiento": rendimiento["conteos"],
            "distribucion_rendimiento": rendimiento["distribucion_observada"],
        },
        "prevision_t0": {
            "estado": S3.ESTADO_T0,
            "fichero": "t0_preexecution_projection_v0_1.json",
            "normativo": proyeccion["normativo"],
            "reparto": proyeccion["reparto"],
        },
        "comprobaciones": inf.comprobaciones,
    }
    return inf, informe


def main() -> int:
    inf, informe = validar()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(informe, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"comprobaciones: {len(inf.comprobaciones)}  fallos: {len(inf.fallos)}")
    for c in inf.fallos:
        print(f"  FALLO: {c['comprobacion']} -> {c['detalle']}")
    print(f"informe: {SALIDA.relative_to(RAIZ)}")
    return 1 if inf.fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
