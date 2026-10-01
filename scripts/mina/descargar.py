"""Volcado reproducible para la mina de septiembre de 2026.

Lee la API de GitHub (solo lectura) a traves del proxy del contenedor y guarda,
por incidencia, TODOS los comentarios con su autor, asociacion y fecha. El
filtro de autor de confianza se aplica despues, en el analisis, para que el
volcado sea el dato crudo y el criterio quede escrito aparte.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = "canelamoraguezandyjesus-bot/sirius"
BASE = f"https://api.github.com/repos/{REPO}"
DESDE = "2026-08-25T00:00:00Z"  # misma ventana de descarga que la edicion del 14-09
sys.path.insert(0, str(Path(__file__).resolve().parent))
from datos import RAW  # noqa: E402

RAW.mkdir(parents=True, exist_ok=True)


def get(url: str) -> tuple[list | dict, dict]:
    for intento in range(5):
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "sirius-mina-2026-09"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read()), dict(r.headers)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 502, 503) and intento < 4:
                time.sleep(2 ** (intento + 1))
                continue
            raise
        except urllib.error.URLError, TimeoutError:
            if intento < 4:
                time.sleep(2 ** (intento + 1))
                continue
            raise
    raise RuntimeError("inalcanzable")


def paginar(url: str) -> list:
    todo: list = []
    pagina = 1
    while True:
        sep = "&" if "?" in url else "?"
        datos, _cab = get(f"{url}{sep}per_page=100&page={pagina}")
        if not isinstance(datos, list):
            raise RuntimeError(f"respuesta inesperada en {url}: {type(datos)}")
        todo.extend(datos)
        if len(datos) < 100:
            return todo
        pagina += 1


def main() -> int:
    t0 = time.time()
    incidencias = paginar(f"{BASE}/issues?state=all&since={DESDE}&sort=updated&direction=desc")
    indice = []
    for inc in incidencias:
        indice.append(
            {
                "number": inc["number"],
                "title": inc["title"],
                "state": inc["state"],
                "created_at": inc["created_at"],
                "updated_at": inc["updated_at"],
                "closed_at": inc.get("closed_at"),
                "comments": inc.get("comments", 0),
                "es_pr": "pull_request" in inc,
                "labels": [etiqueta["name"] for etiqueta in inc.get("labels", [])],
            }
        )
    (RAW / "indice.json").write_text(
        json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        f"indice: {len(indice)} elementos con actividad desde {DESDE} "
        f"({sum(1 for i in indice if i['es_pr'])} son PR)"
    )

    total_comentarios = 0
    for n, inc in enumerate(indice, 1):
        destino = RAW / f"issue_{inc['number']}.json"
        if destino.exists():
            continue
        comentarios = paginar(f"{BASE}/issues/{inc['number']}/comments") if inc["comments"] else []
        limpio = [
            {
                "id": c["id"],
                "login": c["user"]["login"] if c.get("user") else None,
                "author_association": c.get("author_association"),
                "created_at": c["created_at"],
                "updated_at": c.get("updated_at"),
                "body": c.get("body") or "",
            }
            for c in comentarios
        ]
        destino.write_text(
            json.dumps({"issue": inc, "comments": limpio}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        total_comentarios += len(limpio)
        if n % 10 == 0:
            print(
                f"  {n}/{len(indice)} incidencias, {total_comentarios} comentarios, "
                f"{time.time() - t0:.0f}s",
                flush=True,
            )
    print(
        f"hecho: {len(indice)} incidencias, {total_comentarios} comentarios nuevos, "
        f"{time.time() - t0:.0f}s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
