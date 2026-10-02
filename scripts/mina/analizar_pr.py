"""Segunda poblacion: rondas de Codex sobre PR, 01 -> 30-09-2026.

Una ronda = una review de chatgpt-codex-connector[bot] (state COMMENTED o
APPROVED) con submitted_at en la ventana. Limpia = su cuerpo dice «Didn't find
any major issues» o no deja comentarios en linea con insignia. Un hallazgo = un
comentario en linea de ese bot con insignia P0..P4, que no sea respuesta
(in_reply_to_id nulo), creado en la ventana.
"""

from __future__ import annotations

import glob
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from datos import DATOS, PRDIR, RAW, avisos_de_los_volcados

INICIO = "2026-09-01T00:00:00Z"
FIN = "2026-09-30T23:59:59Z"
MITAD = "2026-09-14T23:59:59Z"
CODEX = "chatgpt-codex-connector[bot]"
BADGE = re.compile(r"!\[(P[0-4]) Badge\]")


def tipo(path: str) -> str:
    p = (path or "").lower()
    if p.endswith(".py"):
        return "codigo (.py)"
    if p.endswith(".md"):
        return "documentos (.md)"
    if p.endswith((".yml", ".yaml")):
        return "workflows (.yml)"
    if p.endswith((".sh", ".ps1")):
        return "guiones (.sh/.ps1)"
    return "otros"


def main() -> None:
    # Avisos de TODOS los volcados antes de leer nada: este analizador lee
    # `raw_pr` y tambien `raw` (las rondas limpias), y una foto vieja de
    # cualquiera de los dos sacaba cifras obsoletas en §5 sin aviso (Codex,
    # PR #665, rondas 10 y 11).
    for aviso in avisos_de_los_volcados():
        print(aviso, file=sys.stderr)
    prs = {}
    for f in glob.glob(str(PRDIR / "pr_*.json")):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        prs[d["pr"]["number"]] = d
    filas = []
    for n, d in sorted(prs.items()):
        reviews = [
            r
            for r in d["reviews"]
            if r["login"] == CODEX
            and r["state"] in ("COMMENTED", "APPROVED", "CHANGES_REQUESTED")
            and INICIO <= (r["submitted_at"] or "") <= FIN
        ]
        hallazgos = [
            c
            for c in d["comments"]
            if c["login"] == CODEX
            and not c["in_reply_to_id"]
            and BADGE.search(c["body"])
            and INICIO <= c["created_at"] <= FIN
        ]
        # Las rondas LIMPIAS no son reviews: Codex las publica como comentario
        # de la conversacion de la PR («Didn't find any major issues»), que vive
        # en raw/issue_<N>.json. Sin esto, una PR aprobada a la primera no cuenta.
        limpias_coment = []
        ruta_issue = RAW / f"issue_{n}.json"
        if ruta_issue.exists():
            di = json.loads(Path(ruta_issue).read_text(encoding="utf-8"))
            limpias_coment = [
                c
                for c in di["comments"]
                if c["login"] == CODEX
                and "find any major issues" in c["body"]
                and INICIO <= c["created_at"] <= FIN
            ]
        if not reviews and not hallazgos and not limpias_coment:
            continue
        limpias = len(limpias_coment)
        reviews = reviews + [
            {"submitted_at": c["created_at"], "body": c["body"]} for c in limpias_coment
        ]
        reviews.sort(key=lambda r: r["submitted_at"])
        filas.append(
            {
                "pr": n,
                "titulo": d["pr"]["title"][:80],
                "rama": d["pr"]["head"],
                "autor": d["pr"]["user"],
                "creada": d["pr"]["created_at"],
                "fusionada": d["pr"]["merged_at"],
                "rondas": len(reviews),
                "limpias": limpias,
                "hallazgos": len(hallazgos),
                "por_gravedad": Counter(BADGE.search(c["body"]).group(1) for c in hallazgos),
                "por_tipo": Counter(tipo(c["path"]) for c in hallazgos),
                "primera_mitad": (
                    reviews[0]["submitted_at"] if reviews else hallazgos[0]["created_at"]
                )
                <= MITAD,
            }
        )
    print(f"PR con alguna ronda de Codex en la ventana: {len(filas)}")
    for mitad, nombre in ((True, "01->14"), (False, "15->30")):
        fs = [f for f in filas if f["primera_mitad"] == mitad]
        if not fs:
            print(f"  [{nombre}] ninguna")
            continue
        rondas = [f["rondas"] for f in fs]
        print(
            f"  [{nombre}] PR={len(fs)} rondas={sum(rondas)} "
            f"media={statistics.mean(rondas):.2f} mediana={statistics.median(rondas)} "
            f"hallazgos={sum(f['hallazgos'] for f in fs)} "
            f"rondas_limpias={sum(f['limpias'] for f in fs)}"
        )
    print("\n| PR | rama | rondas (limpias) | hallazgos | por gravedad | fusionada |")
    for f in sorted(filas, key=lambda f: -f["rondas"]):
        print(
            f"| #{f['pr']} | {f['rama']} | {f['rondas']} ({f['limpias']}) | {f['hallazgos']} | "
            f"{dict(f['por_gravedad'])} | {(f['fusionada'] or 'no')[:10]} |"
        )
    grav = Counter()
    tip = Counter()
    for f in filas:
        grav.update(f["por_gravedad"])
        tip.update(f["por_tipo"])
    print("\nhallazgos por gravedad:", dict(grav))
    print("hallazgos por tipo de fichero:", dict(tip))
    (DATOS / "resumen_pr.json").write_text(
        json.dumps(filas, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
