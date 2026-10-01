"""Para cada AVISO_FAMILIA_REPETIDA publicado en la ventana: reconstruir el
historial que el motor veia en ese instante (comentarios de confianza
anteriores al aviso, tras el ultimo marcador de reanudacion) y pasar el
detector de HOY. Asi se separa «el detector cambio» de «el historial cambio»."""

import json
import subprocess
import tempfile
from pathlib import Path

from analizar import RAW, confianza

from sirius_engine.round_history import history_after_last_resume

r = json.loads(Path("resumen.json").read_text(encoding="utf-8"))
avisos = r["avisos_familia"]
print("| incidencia | aviso publicado | detector de hoy sobre el historial de ese instante |")
for n, t in avisos:
    d = json.loads(Path(RAW / f"issue_{n}.json").read_text(encoding="utf-8"))
    previos = [
        c["body"]
        for c in sorted(d["comments"], key=lambda c: c["created_at"])
        if confianza(c) and c["created_at"] <= t
    ]
    texto = history_after_last_resume("\n\n".join(previos))
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(texto)
        ruta = f.name
    out = subprocess.run(
        ["uv", "run", "--no-sync", "sirius-familia-repetida", "--historial", ruta],
        cwd="/home/user/sirius",
        capture_output=True,
        text=True,
    )
    try:
        v = json.loads(out.stdout)
        res = (
            "SI: "
            + "; ".join(
                f"{e['archivo'].split('/')[-1][:40]} {e['rondas']}" for e in v.get("evidencias", [])
            )
            if v.get("hay_familia_repetida")
            else "no"
        )
    except Exception:
        res = f"error: {out.stdout[:80]} {out.stderr[:80]}"
    print(f"| #{n} | {t} | {res} |")
