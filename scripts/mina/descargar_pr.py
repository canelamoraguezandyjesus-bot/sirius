"""Segunda poblacion de la mina de septiembre: las revisiones de Codex sobre PR.

En la segunda quincena el trabajo salio del ciclo del motor (RONDA_HALLAZGOS en
incidencias) y paso a PR de sesion revisadas por Codex directamente. Esas
rondas viven en /pulls/N/reviews (una review de chatgpt-codex-connector[bot]
por ronda) y sus hallazgos en /pulls/N/comments (comentarios en linea con
insignia P1/P2/P3). Se descargan para todas las PR del indice.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from descargar import BASE, RAW, get, paginar

PRDIR = Path(__file__).parent / "raw_pr"
PRDIR.mkdir(exist_ok=True)


def main() -> int:
    indice = json.loads((RAW / "indice.json").read_text(encoding="utf-8"))
    prs = [i for i in indice if i["es_pr"]]
    print(f"PR en el indice: {len(prs)}")
    for k, pr in enumerate(prs, 1):
        n = pr["number"]
        destino = PRDIR / f"pr_{n}.json"
        if destino.exists():
            continue
        reviews = paginar(f"{BASE}/pulls/{n}/reviews")
        comentarios = paginar(f"{BASE}/pulls/{n}/comments")
        detalle, _ = get(f"{BASE}/pulls/{n}")
        destino.write_text(
            json.dumps(
                {
                    "pr": {
                        "number": n,
                        "title": pr["title"],
                        "state": pr["state"],
                        "created_at": pr["created_at"],
                        "merged_at": detalle.get("merged_at"),
                        "closed_at": detalle.get("closed_at"),
                        "head": (detalle.get("head") or {}).get("ref"),
                        "user": (detalle.get("user") or {}).get("login"),
                    },
                    "reviews": [
                        {
                            "id": r["id"],
                            "login": (r.get("user") or {}).get("login"),
                            "state": r.get("state"),
                            "submitted_at": r.get("submitted_at"),
                            "commit_id": r.get("commit_id"),
                            "body": r.get("body") or "",
                        }
                        for r in reviews
                    ],
                    "comments": [
                        {
                            "id": c["id"],
                            "login": (c.get("user") or {}).get("login"),
                            "created_at": c["created_at"],
                            "path": c.get("path"),
                            "line": c.get("line") or c.get("original_line"),
                            "commit_id": c.get("commit_id"),
                            "in_reply_to_id": c.get("in_reply_to_id"),
                            "body": c.get("body") or "",
                        }
                        for c in comentarios
                    ],
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        if k % 10 == 0:
            print(f"  {k}/{len(prs)}", flush=True)
    print("hecho")
    return 0


if __name__ == "__main__":
    sys.exit(main())
