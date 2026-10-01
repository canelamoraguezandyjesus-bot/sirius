"""Falsos negativos del detector de familia repetida en la ventana, derivados.

Para CADA incidencia con alguna ronda en la ventana (las de `resumen.json`):
1. se pasa el detector de HOY -el mismo codigo que `sirius-familia-repetida`,
   tras el ultimo marcador de reanudacion- por su historial completo de
   comentarios de confianza;
2. se cruza con los AVISO_FAMILIA_REPETIDA publicados en la ventana;
3. las que el detector marca y no recibieron aviso son los falsos negativos de
   entonces, y para cada una se reconstruye ronda a ronda en que instante
   habria avisado el detector de hoy y si el ciclo publico algo desde ahi.

Lee el volcado y `resumen.json` de donde diga `MINA_DATOS` (ver `datos.py`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analizar import confianza
from datos import DATOS, RAW
from reproducir_avisos import detector_de_hoy

from sirius_engine.round_history import parse_round_records


def main() -> int:
    resumen = json.loads((DATOS / "resumen.json").read_text(encoding="utf-8"))
    incidencias = [int(n) for n in resumen["incidencias"]]
    avisadas = {int(n) for n, _t in resumen["avisos_familia"]}
    marcadas: dict[int, str] = {}
    comentarios: dict[int, list[dict]] = {}
    print("| incidencia | detector de hoy (historial completo) | avisos en la ventana |")
    print("|---|---|---|")
    for n in incidencias:
        d = json.loads((RAW / f"issue_{n}.json").read_text(encoding="utf-8"))
        cs = sorted([c for c in d["comments"] if confianza(c)], key=lambda c: c["created_at"])
        comentarios[n] = cs
        veredicto = detector_de_hoy([c["body"] for c in cs])
        if veredicto != "no":
            marcadas[n] = veredicto
        avisos = sum(1 for m, _t in resumen["avisos_familia"] if int(m) == n)
        print(f"| #{n} | {veredicto} | {avisos} |")
    falsos_negativos = sorted(n for n in marcadas if n not in avisadas)
    print(f"\nIncidencias examinadas: {len(incidencias)}")
    print(f"El detector de hoy marca familia en {len(marcadas)}: {sorted(marcadas)}")
    print(f"De esas, con aviso publicado en su dia: {len([n for n in marcadas if n in avisadas])}")
    print(
        f"Sin ningun aviso (falsos negativos de entonces): {len(falsos_negativos)}: "
        f"{falsos_negativos}"
    )
    for n in falsos_negativos:
        cs = comentarios[n]
        print(f"\n#{n}: en que ronda habria avisado el detector de hoy")
        acumulado: list[str] = []
        for c in cs:
            acumulado.append(c["body"])
            registros = parse_round_records(c["body"])
            if not registros:
                continue
            veredicto = detector_de_hoy(acumulado)
            aviso_despues = any(
                "AVISO_FAMILIA_REPETIDA" in x["body"]
                for x in cs
                if x["created_at"] >= c["created_at"]
            )
            print(
                f"  ronda {registros[0].get('round')} @ {c['created_at']}: {veredicto} | "
                f"aviso publicado desde ese instante: {'si' if aviso_despues else 'NO'}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
