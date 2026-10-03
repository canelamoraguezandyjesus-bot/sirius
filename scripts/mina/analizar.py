"""Analisis reproducible de la mina de septiembre de 2026 sobre el volcado de `descargar.py`.

Criterios (escritos en la nota de arranque del 01-10-2026 04:45 UTC, antes de
ejecutar esto):
- autor de confianza: author_association == OWNER o login == github-actions[bot]
  (el mismo filtro que scripts/automation/sirius_issue.sh usa en produccion);
- una ronda entra en la ventana si el comentario que la publico cae dentro;
- una incidencia entra si tiene al menos una ronda dentro.
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from sirius_engine.drip_guard import parse_archivo_location
from sirius_engine.round_history import parse_round_records

sys.path.insert(0, str(Path(__file__).resolve().parent))
from datos import (
    DATOS,
    HISTORIALES,
    RAW,
    avisos_de_editados,
    avisos_de_los_volcados,
    captura_de,
    editado_tras,
    exigir_volcado,
)

INICIO = "2026-09-01T00:00:00Z"
FIN = "2026-09-30T23:59:59Z"
MITAD = "2026-09-14T23:59:59Z"  # fin de la ventana de la edicion del 14-09

OBS_RE = re.compile(r"##\s*OBSERVACIONES_ESTRUCTURADAS\s*```json\s*(.*?)\s*```", re.DOTALL)
GUARDIAN_RE = re.compile(r"Guardi[aá]n de goteo")
NEGACIONES = (
    "no es goteo",
    "no se trata de goteo",
    "no visible en la ronda",
    "no por goteo",
    "no es un goteo",
    "sin goteo",
)


def confianza(c: dict) -> bool:
    return c.get("author_association") == "OWNER" or c.get("login") == "github-actions[bot]"


def tipo_fichero(ruta: str) -> str:
    r = (ruta or "").strip().lower()
    r = re.split(r"[:\s(]", r)[0]
    if r.endswith(".py"):
        return "codigo (.py)"
    if r.endswith(".md"):
        return "documentos (.md)"
    if r.endswith((".yml", ".yaml")):
        return "workflows (.yml)"
    if r.endswith((".sh", ".ps1")):
        return "guiones (.sh/.ps1)"
    if r.endswith((".json", ".yml", ".toml")):
        return "datos (.json/.toml)"
    if not r:
        return "sin fichero"
    return "otros"


def declara_goteo(problema: str) -> bool:
    p = (problema or "").lower()
    if "goteo" not in p:
        return False
    return not any(n in p for n in NEGACIONES)


#: La cabecera con la que `sirius_apply_verdict.sh` publica el aviso, al
#: principio de linea. Mencionarlo en prosa no es avisar: el propietario
#: escribio «Sobre el `AVISO_FAMILIA_REPETIDA`: es exacto...» en #520 (03-09,
#: 17:12 UTC) y una busqueda por subcadena lo contaba como un aviso mas.
_CABECERA_DE_AVISO = re.compile(r"^## AVISO_FAMILIA_REPETIDA\s*$", re.MULTILINE)


def es_aviso_de_familia(cuerpo: str) -> bool:
    return _CABECERA_DE_AVISO.search(cuerpo) is not None


#: Una evidencia de un aviso: (fichero, rondas). Compartida por
#: `falsos_negativos.py` y `reproducir_avisos.py`.
Evidencia = tuple[str, tuple[int, ...]]

#: La linea con la que el motor publica cada evidencia del aviso
#: (`round_family_detector.detectar_familia_repetida`, campo `detalle`).
_EVIDENCIA_PUBLICADA = re.compile(
    r"^- «(?P<archivo>.+?)» recibe hallazgos en \d+ rondas consecutivas "
    r"\(rondas (?P<desde>\d+)-(?P<hasta>\d+)\)",
    re.MULTILINE,
)


def evidencias_publicadas(cuerpo: str) -> tuple[Evidencia, ...] | None:
    """Lo que un AVISO_FAMILIA_REPETIDA lista: (fichero, rondas) por evidencia.

    `None` si el comentario no es un aviso (no lleva la cabecera al principio de
    una linea): el propietario que escribe «sobre el AVISO_FAMILIA_REPETIDA...»
    no esta avisando de nada.
    """
    if not es_aviso_de_familia(cuerpo):
        return None
    seccion = cuerpo.split("## AVISO_FAMILIA_REPETIDA", 1)[1]
    return tuple(
        (m["archivo"], tuple(range(int(m["desde"]), int(m["hasta"]) + 1)))
        for m in _EVIDENCIA_PUBLICADA.finditer(seccion)
    )


def main() -> int:
    for aviso in avisos_de_los_volcados():
        print(aviso, file=sys.stderr)
    incidencias = {}
    for f in exigir_volcado(RAW, "descargar.py", "issue_*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        incidencias[d["issue"]["number"]] = d

    rondas = []  # una fila por ronda publicada en la ventana
    avisos_familia = []
    marcas_guardian = []
    historiales = defaultdict(list)
    juzgados = []  # los comentarios de confianza creados hasta FIN
    editados = []  # (incidencia, id, creado, editado): editados tras FIN, fuera
    for numero, d in incidencias.items():
        # Una ronda cuenta UNA vez por numero, como en `parse_round_records`:
        # GitHub puede publicar dos veces el mismo `sirius-round:N` tras una
        # respuesta ambigua, y analizando cada comentario por separado el
        # parser reiniciaba su conjunto de rondas vistas en cada cuerpo y las
        # dos copias entraban en los totales (Codex, PR #665, ronda 8).
        rondas_vistas: set[int] = set()
        for c in sorted(d["comments"], key=lambda c: c["created_at"]):
            if not confianza(c):
                continue
            if c["created_at"] <= FIN:
                juzgados.append(c)
                # Editado despues de la ventana: el cuerpo que tenemos no es el
                # de septiembre y no se puede reconstruir (Codex, PR #665, ronda
                # 13). Fuera de la evidencia, de los historiales y de los totales.
                if editado_tras(c, FIN):
                    editados.append((numero, c["id"], c["created_at"], c["updated_at"]))
                    continue
            body = c["body"]
            en_ventana = INICIO <= c["created_at"] <= FIN
            # El historial que se guarda termina donde termina la ventana: un
            # volcado regenerado en octubre no puede cambiar lo medido en septiembre.
            if c["created_at"] <= FIN:
                historiales[numero].append(body)
            if es_aviso_de_familia(body) and en_ventana:
                avisos_familia.append((numero, c["created_at"]))
            registros = [
                r for r in parse_round_records(body) if int(r["round"]) not in rondas_vistas
            ]
            rondas_vistas.update(int(r["round"]) for r in registros)
            if not registros:
                continue
            obs = []
            m = OBS_RE.search(body)
            if m:
                try:
                    obs = json.loads(m.group(1))
                except json.JSONDecodeError:
                    obs = []
            for r in registros:
                if not en_ventana:
                    continue
                n_guardian = len(GUARDIAN_RE.findall(body))
                if n_guardian:
                    marcas_guardian.append((numero, r.get("round"), n_guardian))
                rondas.append(
                    {
                        "incidencia": numero,
                        "titulo": d["issue"]["title"][:90],
                        "ronda": r.get("round"),
                        "fecha": c["created_at"],
                        "primera_mitad": c["created_at"] <= MITAD,
                        "hallazgos": r.get("findings") or [],
                        "observaciones": obs,
                    }
                )

    for aviso in avisos_de_editados("las incidencias", FIN, juzgados):
        print(aviso, file=sys.stderr)
    # El denominador sale de aqui, no de una cuenta a mano (Codex, PR #665, ronda
    # 14): los de la ventana, los anteriores a ella (contexto de los historiales)
    # y los editados despues de FIN, que quedan fuera.
    comentarios_de_confianza = {
        "en_ventana": sum(1 for c in juzgados if c["created_at"] >= INICIO),
        "anteriores_a_la_ventana": sum(1 for c in juzgados if c["created_at"] < INICIO),
        "editados_tras_fin": len(editados),
    }
    print(
        f"Comentarios de confianza: en la ventana {comentarios_de_confianza['en_ventana']}, "
        f"anteriores a ella {comentarios_de_confianza['anteriores_a_la_ventana']}, "
        f"editados despues de FIN (fuera) {len(editados)}"
    )

    # --- Poblacion -------------------------------------------------------
    por_incidencia = defaultdict(list)
    for r in rondas:
        por_incidencia[r["incidencia"]].append(r)
    print(f"Incidencias con al menos una ronda en la ventana: {len(por_incidencia)}")
    print(f"Rondas publicadas en la ventana: {len(rondas)}")
    hallazgos = [(r, h) for r in rondas for h in r["hallazgos"]]
    print(f"Hallazgos en RONDA_HALLAZGOS: {len(hallazgos)}")

    def bloque(nombre, filtro):
        rs = [r for r in rondas if filtro(r)]
        incs = {r["incidencia"] for r in rs}
        hs = [h for r in rs for h in r["hallazgos"]]
        print(f"  [{nombre}] incidencias={len(incs)} rondas={len(rs)} hallazgos={len(hs)}")

    bloque("01->14 (reproduccion de la edicion del 14-09)", lambda r: r["primera_mitad"])
    bloque("15->30 (segunda quincena)", lambda r: not r["primera_mitad"])

    # --- 1. Distribucion ---------------------------------------------------
    print("\n## 1.1 Por fuente")
    fuente = Counter((h.get("source") or "?").upper() for _, h in hallazgos)
    for k, v in fuente.most_common():
        print(f"  {k}: {v} ({100 * v / len(hallazgos):.1f}%)")
    print("\n## 1.2 Por gravedad dentro de cada fuente")
    grav = Counter(
        ((h.get("source") or "?").upper(), str(h.get("severity") or "?").lower())
        for _, h in hallazgos
    )
    for (f_, g), v in sorted(grav.items(), key=lambda kv: (kv[0][0], -kv[1])):
        print(f"  {f_} {g}: {v}")
    print("\n## 1.3 Por tipo de fichero")
    tipo = Counter(tipo_fichero(h.get("file") or h.get("archivo") or "") for _, h in hallazgos)
    for k, v in tipo.most_common():
        print(f"  {k}: {v} ({100 * v / len(hallazgos):.1f}%)")

    # --- 3.4 Alcance del guardian de goteo ---------------------------------
    # El guardian solo juzga una observacion cuyo campo de fichero lleve una
    # linea que parse_archivo_location reconozca (ADR-123, incidencia #523 G3).
    # Se mide con la MISMA funcion que usa el guardian en produccion.
    print("\n## 3.4 Alcance del guardian: hallazgos con fichero:linea reconocible")
    alcance: Counter[str] = Counter()
    con_linea: Counter[str] = Counter()
    for _, h in hallazgos:
        src = (h.get("source") or "?").upper()
        alcance[src] += 1
        _ruta, linea = parse_archivo_location(h.get("file") or h.get("archivo") or "")
        if linea is not None:
            con_linea[src] += 1
    for src in sorted(alcance):
        pct = 100 * con_linea[src] / alcance[src]
        print(f"  {src}: {con_linea[src]} de {alcance[src]} ({pct:.1f}%)")

    # --- 2. Rondas por incidencia -----------------------------------------
    print("\n## 2 Rondas por incidencia (en la ventana)")
    conteo = {n: len(set(r["ronda"] for r in rs)) for n, rs in por_incidencia.items()}
    vals = sorted(conteo.values())
    print(f"  media={statistics.mean(vals):.2f} mediana={statistics.median(vals)} max={max(vals)}")
    dist = Counter(vals)
    print("  distribucion:", ", ".join(f"{k}->{v}" for k, v in sorted(dist.items())))
    print(f"  con mas de una ronda: {sum(1 for v in vals if v > 1)} de {len(vals)}")
    peores = sorted(conteo.items(), key=lambda kv: -kv[1])[:8]
    for n, v in peores:
        print(f"  #{n}: {v} rondas  — {incidencias[n]['issue']['title'][:70]}")
    for nombre, filtro in (
        ("01->14", lambda r: r["primera_mitad"]),
        ("15->30", lambda r: not r["primera_mitad"]),
    ):
        c2 = defaultdict(set)
        for r in rondas:
            if filtro(r):
                c2[r["incidencia"]].add(r["ronda"])
        v2 = sorted(len(s) for s in c2.values())
        if v2:
            media2, mediana2 = statistics.mean(v2), statistics.median(v2)
            print(f"  [{nombre}] incidencias={len(v2)} media={media2:.2f} mediana={mediana2}")

    # --- 3. Goteo ----------------------------------------------------------
    print("\n## 3 Goteo")
    n_mas_1 = [(r, o) for r in rondas if (r["ronda"] or 0) > 1 for o in r["observaciones"]]
    print(f"  observaciones en rondas N>1: {len(n_mas_1)}")
    por_fuente = Counter()
    declaradas = Counter()
    for _r, o in n_mas_1:
        src = "CODEX" if str(o.get("id", "")).upper().startswith("CODEX") else "CLAUDE"
        por_fuente[src] += 1
        if declara_goteo(o.get("problema", "")):
            declaradas[src] += 1
    for src in ("CLAUDE", "CODEX"):
        t = por_fuente[src]
        pct = (100 * declaradas[src] / t) if t else 0
        print(f"  {src}: N>1={t} declaran goteo={declaradas[src]} ({pct:.1f}%)")
    n_marcas = sum(m[2] for m in marcas_guardian)
    n_incs = len({m[0] for m in marcas_guardian})
    print(f"  marcas del guardian en rondas de la ventana: {n_marcas} en {n_incs} incidencias")
    con_clave = sum(1 for _, o in n_mas_1 if "posible_goteo" in o)
    print(f"  observaciones N>1 con la clave posible_goteo en el JSON: {con_clave}")

    # --- 4. Avisos del detector -------------------------------------------
    print("\n## 4 AVISO_FAMILIA_REPETIDA publicados en la ventana")
    print(f"  total={len(avisos_familia)} en incidencias={sorted({a[0] for a in avisos_familia})}")

    # --- Historiales para el detector --------------------------------------
    hdir = HISTORIALES
    hdir.mkdir(parents=True, exist_ok=True)
    for n in por_incidencia:
        (hdir / f"historial_{n}.txt").write_text("\n\n".join(historiales[n]), encoding="utf-8")
    print(f"\nHistoriales escritos para {len(por_incidencia)} incidencias en {hdir}")

    resumen = {
        # La captura de la que sale: `falsos_negativos.py` y `reproducir_avisos.py`
        # la exigen antes de leer la foto (Codex, PR #665, ronda 16).
        "captura": captura_de(RAW),
        "ventana": [INICIO, FIN],
        "incidencias": sorted(por_incidencia),
        "rondas": len(rondas),
        "hallazgos": len(hallazgos),
        "fuente": dict(fuente),
        "tipo_fichero": dict(tipo),
        "rondas_por_incidencia": conteo,
        "avisos_familia": avisos_familia,
        "comentarios_de_confianza": comentarios_de_confianza,
        "editados_tras_la_ventana": editados,
        "marcas_guardian": marcas_guardian,
        "alcance_guardian": {src: [con_linea[src], alcance[src]] for src in sorted(alcance)},
    }
    (DATOS / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
