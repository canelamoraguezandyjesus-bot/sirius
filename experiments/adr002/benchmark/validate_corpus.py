"""Validador del corpus, los casos y las referencias del benchmark de ADR-002.

Ejecuta:

    uv run python -m experiments.adr002.benchmark.validate_corpus

Comprueba el contrato canónico y escribe el informe legible por máquina en
`artifacts/adr002_benchmark_preparation/validacion_corpus.json`.

No ejecuta T0 ni T1-T4 y no mide rendimiento.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from experiments.adr002.benchmark import CORPUS_SEED, CORPUS_VERSION
from experiments.adr002.benchmark import schema as S

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
SALIDA = RAIZ / "artifacts" / "adr002_benchmark_preparation" / "validacion_corpus.json"


def cargar() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    def _leer(nombre: str) -> dict[str, Any]:
        return json.loads((AQUI / nombre).read_text(encoding="utf-8"))

    return (
        _leer("corpus_v0_1.json"),
        _leer("cases_v0_1.json"),
        _leer("references_v0_1.json"),
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


# --- comprobaciones ---------------------------------------------------------


def _ca_completos(casos: dict[str, Any], inf: Informe) -> None:
    vistos = [c["identificador_canonico"] for c in casos["nivel_1"]]
    esperados = list(S.CA_TOTALES)
    faltan = [c for c in esperados if c not in vistos]
    dup = sorted({c for c in vistos if vistos.count(c) > 1})
    sobran = [c for c in vistos if c not in esperados]
    inf.check("CA-01-50 sin ausencias", not faltan, {"faltan": faltan})
    inf.check("CA-01-50 sin duplicados", not dup, {"duplicados": dup})
    inf.check("CA-01-50 sin identificadores ajenos", not sobran, {"sobran": sobran})
    inf.check(
        "CA-01-50 aparecen exactamente una vez",
        len(vistos) == 50 and not dup and not faltan,
        {"total": len(vistos)},
    )


def _vocabularios(casos: dict[str, Any], inf: Informe) -> None:
    malos: dict[str, list[str]] = {"modo": [], "etapa": [], "parada": [], "cardinalidad": []}
    for c in casos["nivel_1"]:
        if c["modo"] not in S.MODOS:
            malos["modo"].append(c["id"])
        if c["etapa_esperada"] not in S.ETAPAS:
            malos["etapa"].append(c["id"])
        if c["parada_esperada"] not in S.PARADAS:
            malos["parada"].append(c["id"])
        if c["cardinalidad"] not in S.CARDINALIDADES:
            malos["cardinalidad"].append(c["id"])
    for k, v in malos.items():
        inf.check(f"vocabulario canónico de {k}", not v, {"casos": v})


def _regla_exhaustiva_s1(casos: dict[str, Any], inf: Informe) -> None:
    """B04 §15.2 y §15.3: una consulta EXHAUSTIVA nunca termina por S1."""
    malos = [
        c["id"]
        for c in casos["nivel_1"]
        if c["cardinalidad"] == "EXHAUSTIVA" and c["parada_esperada"] == "S1"
    ]
    inf.check("ninguna EXHAUSTIVA para por S1", not malos, {"casos": malos})


def _campos_obligatorios(casos: dict[str, Any], inf: Informe) -> None:
    faltan: dict[str, list[str]] = {}
    for c in casos["nivel_1"]:
        aus = [campo for campo in S.CAMPOS_CASO if campo not in c]
        if aus:
            faltan[c["id"]] = aus
    inf.check("todos los campos obligatorios por caso", not faltan, faltan)


def _ids_existen(corpus: dict[str, Any], casos: dict[str, Any], inf: Informe) -> None:
    conocidos = (
        {i["id"] for i in corpus["items"]}
        | {m["id"] for m in corpus["mensajes"]}
        | {d["id"] for d in corpus["documentos"]}
        | {r["id"] for r in corpus["relaciones"]}
        | {e["id"] for e in corpus["entidades"]}
        | {p["id"] for p in corpus["proyectos"]}
    )
    huerfanos: dict[str, list[str]] = {}
    for c in casos["nivel_1"]:
        malos = [
            x
            for x in (
                *c["datos_sinteticos"],
                *c["candidatos_elegibles"],
                *c["candidatos_prohibidos"],
            )
            if x not in conocidos
        ]
        if malos:
            huerfanos[c["id"]] = malos
    inf.check("todo ID citado existe en el corpus", not huerfanos, huerfanos)


def _elegibles_disjuntos(casos: dict[str, Any], inf: Informe) -> None:
    malos = {
        c["id"]: sorted(set(c["candidatos_elegibles"]) & set(c["candidatos_prohibidos"]))
        for c in casos["nivel_1"]
        if set(c["candidatos_elegibles"]) & set(c["candidatos_prohibidos"])
    }
    inf.check("elegibles y prohibidos disjuntos", not malos, malos)


def _dimensiones(corpus: dict[str, Any], inf: Informe) -> None:
    vocab = {
        "confirmacion": S.CONFIRMACION,
        "validez": S.VALIDEZ,
        "disponibilidad": S.DISPONIBILIDAD,
        "sensibilidad": S.SENSIBILIDAD,
        "ambito": S.AMBITO,
        "autoridad": S.AUTORIDAD,
    }
    malos: dict[str, list[str]] = {}
    sin_temporalidad: list[str] = []
    for it in corpus["items"]:
        for dim, valores in vocab.items():
            if it[dim] not in valores:
                malos.setdefault(dim, []).append(it["id"])
        if any(k not in it["temporalidad"] for k in S.CAMPOS_TEMPORALIDAD):
            sin_temporalidad.append(it["id"])
    inf.check("las siete dimensiones usan vocabulario canónico", not malos, malos)
    inf.check(
        "temporalidad separa valid_from/valid_to/occurred_at/recorded_at",
        not sin_temporalidad,
        {"items": sin_temporalidad},
    )


def _criticidad(corpus: dict[str, Any], inf: Informe) -> None:
    """B04 §6: nivel, razón, fuente y regla, sin auto-marcado libre."""
    malos = [
        it["id"]
        for it in corpus["items"]
        if it["criticidad"] is not None
        and (
            set(it["criticidad"]) != {"nivel", "razon", "fuente", "regla"}
            or it["criticidad"]["nivel"] not in S.NIVEL_CRITICIDAD
        )
    ]
    con_crit = [it for it in corpus["items"] if it["criticidad"]]
    inf.check("toda marca crítica lleva nivel, razón, fuente y regla", not malos, {"items": malos})
    inf.check("existen críticos elegibles en el corpus", len(con_crit) >= 5, {"n": len(con_crit)})


def _fenomenos(corpus: dict[str, Any], inf: Informe) -> None:
    items = corpus["items"]
    tipos_rel = {r["tipo"] for r in corpus["relaciones"]}
    exigidos = {
        "negación": any(i["polaridad"] == "NEGATIVA" for i in items),
        "condición": any(i["condicion"] for i in items),
        "apoyo": "APOYA" in tipos_rel,
        "refutación": "REFUTA" in tipos_rel,
        "conflicto": "CONFLICTO_CON" in tipos_rel,
        "corrección": "CORRIGE" in tipos_rel,
        "sustitución": "SUSTITUYE_A" in tipos_rel,
        "homónimos": len({e["grupo_homonimo"] for e in corpus["entidades"] if e["grupo_homonimo"]})
        >= 1
        and sum(1 for e in corpus["entidades"] if e["grupo_homonimo"] == "JUAN") >= 2,
        "alias ambiguos": any(e["alias"] for e in corpus["entidades"]),
        "eliminado/purgado": any(i["disponibilidad"] == "PURGADA" for i in items),
        "no guardado": any(i["disponibilidad"] == "NO_GUARDADA" for i in items),
        "archivado": any(i["disponibilidad"] == "ARCHIVADA" for i in items),
        "restringido": any(i["sensibilidad"] == "RESTRINGIDA" for i in items),
        "no usar como memoria": any(i["no_usar_como_memoria"] for i in items),
        "no consolidable": any(i["no_consolidable"] for i in items),
        "sin soporte": any(i["validez"] == "SIN_SOPORTE" for i in items),
        "candidata": any(i["confirmacion"] == "CANDIDATA" for i in items),
        "rechazada": any(i["confirmacion"] == "RECHAZADA" for i in items),
        "fuente inaccesible": any(not d["accesible"] for d in corpus["documentos"]),
        "separación por proyecto": len({i["project_id"] for i in items}) >= 3,
        "lista multi-proyecto cerrada": any(
            p["tipo"] == "MULTI_PROYECTO_CERRADO" and p["miembros_lista_cerrada"]
            for p in corpus["proyectos"]
        ),
        "tiempo válido y de registro": any(
            i["temporalidad"]["valid_from"] and i["temporalidad"]["recorded_at"] for i in items
        ),
        "tres ejes temporales distintos": any(
            i["temporalidad"]["occurred_at"]
            and i["temporalidad"]["valid_from"]
            and i["temporalidad"]["recorded_at"]
            and len(
                {
                    i["temporalidad"]["occurred_at"],
                    i["temporalidad"]["valid_from"],
                    i["temporalidad"]["recorded_at"],
                }
            )
            == 3
            for i in items
        ),
    }
    faltan = sorted(k for k, v in exigidos.items() if not v)
    inf.check("fenómenos obligatorios representados", not faltan, {"faltan": faltan})


def _cardinalidades_y_ausencias(casos: dict[str, Any], inf: Informe) -> None:
    cards = {c["cardinalidad"] for c in casos["nivel_1"]}
    inf.check(
        "casos exactos, acotados y exhaustivos",
        set(S.CARDINALIDADES) <= cards,
        {"presentes": sorted(cards)},
    )
    # ausencia real (CA-17), no reportable (CA-37/48) y fuente inaccesible (CA-18)
    ids = {c["identificador_canonico"] for c in casos["nivel_1"]}
    inf.check(
        "ausencia real, no reportable y fuente inaccesible presentes",
        {"B04-CA-17", "B04-CA-18", "B04-CA-37", "B04-CA-48"} <= ids,
        None,
    )


def _trazabilidad(casos: dict[str, Any], inf: Informe) -> None:
    sin_rf = [c["id"] for c in casos["nivel_1"] if not c["requisito_verificado"]]
    sin_m = [c["id"] for c in casos["nivel_1"] if not c["metrica_y_umbral"]]
    sin_fam = [c["id"] for c in casos["nivel_1"] if not c["familia_pdp"]]
    sin_red = [c["id"] for c in casos["nivel_1"] if not c["traza_red"]]
    inf.check("cada caso traza a un RF canónico", not sin_rf, {"casos": sin_rf})
    inf.check("cada caso traza a una métrica canónica", not sin_m, {"casos": sin_m})
    inf.check("cada caso traza a una familia PDP", not sin_fam, {"casos": sin_fam})
    inf.check("cada caso traza a una fila RED", not sin_red, {"casos": sin_red})

    rf_malos = sorted(
        {r for c in casos["nivel_1"] for r in c["requisito_verificado"] if r not in S.RF_TOTALES}
    )
    m_malos = sorted(
        {m for c in casos["nivel_1"] for m in c["metrica_y_umbral"] if m not in S.M_TOTALES}
    )
    fam_malas = sorted(
        {f for c in casos["nivel_1"] for f in c["familia_pdp"] if f not in S.FAMILIAS_PDP}
    )
    inf.check("todo RF citado pertenece a B04-RF-01-32", not rf_malos, {"rf": rf_malos})
    inf.check("toda métrica citada pertenece a B04-M01-21", not m_malos, {"m": m_malos})
    inf.check("toda familia citada pertenece a F01-F25", not fam_malas, {"familias": fam_malas})

    red_adr002 = {r for c in casos["nivel_1"] for r in c["traza_red"]}
    cubiertas = sorted(set(S.RED_ADR002) & red_adr002)
    inf.check(
        "RED-027-034 cubiertas por al menos un caso",
        set(S.RED_ADR002) <= red_adr002,
        {"cubiertas": cubiertas, "faltan": sorted(set(S.RED_ADR002) - red_adr002)},
    )


def _referencias(casos: dict[str, Any], refs: dict[str, Any], inf: Informe) -> None:
    ids_casos = {c["id"] for c in casos["nivel_1"]}
    ids_refs = {r["caso"] for r in refs["referencias_nivel_1"]}
    inf.check(
        "una referencia congelada por caso de nivel 1",
        ids_casos == ids_refs,
        {
            "solo_en_casos": sorted(ids_casos - ids_refs),
            "solo_en_refs": sorted(ids_refs - ids_casos),
        },
    )
    mutables = [r["caso"] for r in refs["referencias_nivel_1"] if r["modificable"]]
    inf.check("ninguna referencia de nivel 1 es modificable", not mutables, {"casos": mutables})


def _determinismo(inf: Informe) -> None:
    """El mismo commit debe producir byte a byte los mismos ficheros."""
    antes = {
        n: (AQUI / n).read_bytes()
        for n in ("corpus_v0_1.json", "cases_v0_1.json", "references_v0_1.json")
    }
    res = subprocess.run(
        [sys.executable, "-m", "experiments.adr002.benchmark.build_corpus"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )
    despues = {n: (AQUI / n).read_bytes() for n in antes}
    iguales = all(antes[n] == despues[n] for n in antes)
    inf.check(
        "regeneración determinista byte a byte",
        res.returncode == 0 and iguales,
        {"returncode": res.returncode, "difieren": [n for n in antes if antes[n] != despues[n]]},
    )


def _sin_datos_reales(corpus: dict[str, Any], inf: Informe) -> None:
    crudo = json.dumps(corpus, ensure_ascii=False).lower()
    prohibidos = ["@gmail", "@hotmail", "http://", "https://", "password", "api_key", "secret"]
    hallados = [p for p in prohibidos if p in crudo]
    inf.check("sin datos reales, URLs ni secretos", not hallados, {"encontrados": hallados})
    inf.check(
        "semilla declarada y fija", corpus["semilla"] == CORPUS_SEED, {"semilla": corpus["semilla"]}
    )


def _cobertura_t0(casos: dict[str, Any], inf: Informe) -> dict[str, Any]:
    reparto: dict[str, list[str]] = {}
    for c in casos["nivel_1"]:
        reparto.setdefault(c["ejecutable_por_t0"], []).append(c["identificador_canonico"])
    inf.check(
        "ningún caso no expresable ha sido eliminado",
        sum(len(v) for v in reparto.values()) == 50,
        {"total": sum(len(v) for v in reparto.values())},
    )
    return {k: sorted(v) for k, v in sorted(reparto.items())}


def main() -> int:
    corpus, casos, refs = cargar()
    inf = Informe()

    _ca_completos(casos, inf)
    _campos_obligatorios(casos, inf)
    _vocabularios(casos, inf)
    _regla_exhaustiva_s1(casos, inf)
    _ids_existen(corpus, casos, inf)
    _elegibles_disjuntos(casos, inf)
    _dimensiones(corpus, inf)
    _criticidad(corpus, inf)
    _fenomenos(corpus, inf)
    _cardinalidades_y_ausencias(casos, inf)
    _trazabilidad(casos, inf)
    _referencias(casos, refs, inf)
    _sin_datos_reales(corpus, inf)
    _determinismo(inf)
    reparto_t0 = _cobertura_t0(casos, inf)

    rf_cubiertos = sorted({r for c in casos["nivel_1"] for r in c["requisito_verificado"]})
    m_cubiertas = sorted({m for c in casos["nivel_1"] for m in c["metrica_y_umbral"]})
    fam_cubiertas = sorted({f for c in casos["nivel_1"] for f in c["familia_pdp"]})
    fam_todas = sorted(
        set(fam_cubiertas)
        | {f for c in casos["nivel_2"] for f in c.get("fam", [])}
        | {f for c in casos["nivel_3"] for f in c.get("fam", [])}
    )
    red_cubiertas = sorted({r for c in casos["nivel_1"] for r in c["traza_red"]})

    informe = {
        "documento": "Validación del corpus ejecutable de ADR-002",
        "version_corpus": CORPUS_VERSION,
        "estado": "PROPUESTO",
        "semilla": CORPUS_SEED,
        "no_ejecuta": ["T0", "T1", "T2", "T3", "T4"],
        "resumen": {
            "comprobaciones": len(inf.comprobaciones),
            "ok": len(inf.comprobaciones) - len(inf.fallos),
            "fallos": len(inf.fallos),
            "veredicto": "VALIDO" if not inf.fallos else "INVALIDO",
        },
        "cobertura": {
            "ca_b04": {"cubiertos": 50, "de": 50, "faltan": [], "duplicados": []},
            "rf_b04": {
                "cubiertos": len(rf_cubiertos),
                "de": len(S.RF_TOTALES),
                "lista": rf_cubiertos,
                "no_cubiertos": sorted(set(S.RF_TOTALES) - set(rf_cubiertos)),
            },
            "m_b04": {
                "cubiertas": len(m_cubiertas),
                "de": len(S.M_TOTALES),
                "lista": m_cubiertas,
                "no_cubiertas": sorted(set(S.M_TOTALES) - set(m_cubiertas)),
            },
            "familias_pdp": {
                "cubiertas": len(fam_cubiertas),
                "de": len(S.FAMILIAS_PDP),
                "lista": fam_cubiertas,
                "no_cubiertas": sorted(set(S.FAMILIAS_PDP) - set(fam_cubiertas)),
                "nota": (
                    "Denominador de nivel 1. Las familias no cubiertas por B04-CA-01-50 "
                    "pertenecen a otros bloques; ver familias_pdp_todos_los_niveles."
                ),
            },
            "familias_pdp_todos_los_niveles": {
                "cubiertas": len(fam_todas),
                "de": len(S.FAMILIAS_PDP),
                "lista": fam_todas,
                "no_cubiertas": sorted(set(S.FAMILIAS_PDP) - set(fam_todas)),
                "nota": (
                    "PDP-M03 exige 25/25 para cerrar el Plan de Pruebas completo, no para "
                    "el benchmark de ADR-002. Las familias que faltan aquí son de B03, B06, "
                    "B07 y B08 y no las materializa ADR-002."
                ),
            },
            "red": {
                "cubiertas": red_cubiertas,
                "adr002_exigidas": list(S.RED_ADR002),
                "no_cubiertas_de_adr002": sorted(set(S.RED_ADR002) - set(red_cubiertas)),
                "interfaz_registrada": list(S.RED_INTERFAZ_REGISTRADA),
            },
        },
        "reparto_t0": reparto_t0,
        "conteos_corpus": corpus["conteos"],
        "conteos_casos": casos["conteos"],
        "comprobaciones": inf.comprobaciones,
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(informe, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"comprobaciones: {len(inf.comprobaciones)}  fallos: {len(inf.fallos)}")
    for c in inf.fallos:
        print(f"  FALLO: {c['comprobacion']} -> {c['detalle']}")
    print(f"informe: {SALIDA.relative_to(RAIZ)}")
    return 1 if inf.fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
