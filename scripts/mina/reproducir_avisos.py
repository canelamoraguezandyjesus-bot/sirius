"""Para cada AVISO_FAMILIA_REPETIDA publicado en la ventana: reconstruir el
historial que el motor veia en ese instante (comentarios de confianza hasta el
que llevo el aviso, incluido) y pasarle el detector de HOY, el mismo codigo que
ejecuta `sirius-familia-repetida` (tras el ultimo marcador de reanudacion). Asi
se separa «el detector cambio» de «el historial cambio».

Lee `resumen.json` y el volcado de donde diga `MINA_DATOS` (ver `datos.py`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analizar import confianza
from datos import DATOS, RAW

from sirius_engine.round_family_detector import detectar_familia_repetida
from sirius_engine.round_history import history_after_last_resume, parse_round_records


def detector_de_hoy(cuerpos: list[str]) -> str:
    """«SI: fichero rondas; ...» o «no», con el detector instalado en este arbol."""
    registros = parse_round_records(history_after_last_resume("\n\n".join(cuerpos)))
    deteccion = detectar_familia_repetida(registros)
    if not deteccion.hay_familia_repetida:
        return "no"
    return "SI: " + "; ".join(
        f"{e.archivo.split('/')[-1][:40]} {e.rondas}" for e in deteccion.evidencias
    )


def main() -> int:
    resumen = json.loads((DATOS / "resumen.json").read_text(encoding="utf-8"))
    avisos = resumen["avisos_familia"]
    reproducidos = 0
    print("| incidencia | aviso publicado | detector de hoy sobre el historial de ese instante |")
    print("|---|---|---|")
    for n, t in avisos:
        d = json.loads((RAW / f"issue_{n}.json").read_text(encoding="utf-8"))
        previos = [
            c["body"]
            for c in sorted(d["comments"], key=lambda c: c["created_at"])
            if confianza(c) and c["created_at"] <= t
        ]
        veredicto = detector_de_hoy(previos)
        reproducidos += veredicto != "no"
        print(f"| #{n} | {t} | {veredicto} |")
    print(f"\nAvisos reproducidos por el detector de hoy: {reproducidos} de {len(avisos)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
