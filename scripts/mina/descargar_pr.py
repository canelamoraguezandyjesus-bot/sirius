"""Segunda poblacion de la mina de septiembre: las revisiones de Codex sobre PR.

En la segunda quincena el trabajo salio del ciclo del motor (RONDA_HALLAZGOS en
incidencias) y paso a PR de sesion revisadas por Codex directamente. Esas
rondas viven en /pulls/N/reviews (una review de chatgpt-codex-connector[bot]
por ronda) y sus hallazgos en /pulls/N/comments (comentarios en linea con
insignia P1/P2/P3). Se descargan para todas las PR del indice.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from datos import (
    PRDIR_LOGICO,
    RAW,
    copiar_marca_de_captura,
    parcial_de,
    publicar_volcado,
)
from descargar import BASE, get, paginar


def main(prdir: Path = PRDIR_LOGICO, raw: Path = RAW) -> int:
    indice = json.loads((raw / "indice.json").read_text(encoding="utf-8"))
    prs = [i for i in indice if i["es_pr"]]
    print(f"PR en el indice: {len(prs)}")
    # Misma garantia que `descargar.py`: se descarga en `raw_pr.parcial` y se
    # publica entero al terminar (Codex, PR #665, ronda 6).
    parcial = parcial_de(prdir)
    shutil.rmtree(parcial, ignore_errors=True)
    parcial.mkdir(parents=True)
    for k, pr in enumerate(prs, 1):
        n = pr["number"]
        destino = parcial / f"pr_{n}.json"
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
                            # La fecha de edicion: sin ella no se puede saber si
                            # el cuerpo es el de la ventana (Codex, PR #665, ronda 13).
                            "updated_at": c.get("updated_at"),
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
    # Misma captura que el `raw` junto al que se descarga, o nada (ronda 12).
    # Y una captura empareja un solo volcado de PR: si el publicado ya lleva la
    # marca de este raw, no se copia (rondas 14 y 15).
    copiar_marca_de_captura(raw, parcial, prdir)
    publicar_volcado(parcial, prdir)
    print(f"hecho; volcado de PR publicado entero en {prdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
