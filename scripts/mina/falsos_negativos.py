"""Las incidencias que el detector de HOY marca sobre el historial completo pero
que no recibieron ningun AVISO_FAMILIA_REPETIDA en la ventana: en que instante
(que ronda) habria avisado el detector de hoy, y si en ese instante el ciclo
publico algo."""

import json
import subprocess
import tempfile
from pathlib import Path

from analizar import RAW, confianza

from sirius_engine.round_history import history_after_last_resume, parse_round_records

for n in (566, 570, 599, 601):
    d = json.loads(Path(RAW / f"issue_{n}.json").read_text(encoding="utf-8"))
    cs = sorted([c for c in d["comments"] if confianza(c)], key=lambda c: c["created_at"])
    print(f"\n#{n} {d['issue']['title'][:70]}")
    acumulado = []
    for c in cs:
        acumulado.append(c["body"])
        regs = parse_round_records(c["body"])
        if not regs:
            continue
        ronda = regs[0].get("round")
        texto = history_after_last_resume("\n\n".join(acumulado))
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(texto)
            ruta = f.name
        out = subprocess.run(
            ["uv", "run", "--no-sync", "sirius-familia-repetida", "--historial", ruta],
            cwd="/home/user/sirius",
            capture_output=True,
            text=True,
        )
        v = json.loads(out.stdout) if out.stdout.strip().startswith("{") else {}
        marca = (
            "SI "
            + "; ".join(
                f"{e['archivo'].split('/')[-1][:35]} {e['rondas']}" for e in v.get("evidencias", [])
            )
            if v.get("hay_familia_repetida")
            else "no"
        )
        aviso_despues = any(
            "AVISO_FAMILIA_REPETIDA" in x["body"] for x in cs if x["created_at"] >= c["created_at"]
        )
        print(
            f"  ronda {ronda} @ {c['created_at']}: detector de hoy -> {marca} | "
            f"aviso publicado desde ese instante: {'si' if aviso_despues else 'NO'}"
        )
