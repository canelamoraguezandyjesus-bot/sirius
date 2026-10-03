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
from analizar import FIN, Evidencia, confianza, evidencias_publicadas
from datos import DATOS, RAW, editado_tras, exigir_misma_captura

from sirius_engine.round_family_detector import detectar_familia_repetida
from sirius_engine.round_history import history_after_last_resume, parse_round_records


def evidencias_de_hoy(cuerpos: list[str]) -> list[tuple[str, tuple[int, ...]]]:
    """(archivo, rondas) por familia que el detector instalado en este arbol marca
    sobre lo publicado, tras el ultimo marcador de reanudacion; vacio si no marca."""
    registros = parse_round_records(history_after_last_resume("\n\n".join(cuerpos)))
    deteccion = detectar_familia_repetida(registros)
    if not deteccion.hay_familia_repetida:
        return []
    return [(e.archivo, tuple(int(n) for n in e.rondas)) for e in deteccion.evidencias]


def coinciden(publicadas: tuple[Evidencia, ...], hoy: list[Evidencia]) -> bool:
    """Un aviso se reproduce solo si CADA evidencia que publico (fichero y tramo)
    tiene hoy una evidencia del mismo fichero cuyo tramo CONTIENE el publicado.
    Que el detector encuentre cualquier familia en el historial no basta: con
    varias familias en una incidencia contaria como reproducido un aviso cuyo
    fichero y tramo el detector de hoy ya no ve (Codex, PR #665, ronda 8); y
    que solape no basta: un aviso de las rondas 1-3 con el detector de hoy en
    3-5 compartiria una ronda y habria perdido dos (ronda 9)."""
    if not publicadas:
        return False
    return all(
        any(archivo == a and set(rondas) <= set(r) for a, r in hoy)
        for archivo, rondas in publicadas
    )


def detector_de_hoy(cuerpos: list[str]) -> str:
    """«SI: fichero rondas; ...» o «no»: la misma deteccion, para imprimir."""
    evidencias = evidencias_de_hoy(cuerpos)
    if not evidencias:
        return "no"
    return "SI: " + "; ".join(f"{a.split('/')[-1][:40]} {r}" for a, r in evidencias)


def main() -> int:
    resumen = json.loads((DATOS / "resumen.json").read_text(encoding="utf-8"))
    # El resumen solo vale con la foto de la que salio (rondas 16 y 17): parar si no.
    exigir_misma_captura("resumen.json", resumen.get("captura"), RAW)
    avisos = resumen["avisos_familia"]
    reproducidos = 0
    print(
        "| incidencia | aviso publicado | lo que el aviso publico | "
        "detector de hoy sobre el historial de ese instante | coincide fichero y tramo |"
    )
    print("|---|---|---|---|---|")
    for n, t in avisos:
        d = json.loads((RAW / f"issue_{n}.json").read_text(encoding="utf-8"))
        # Fuera los editados despues de la ventana, como en `analizar.py`
        # (Codex, PR #665, ronda 13): su cuerpo no es el de aquel instante.
        de_confianza = [
            c
            for c in sorted(d["comments"], key=lambda c: c["created_at"])
            if confianza(c) and not editado_tras(c, FIN)
        ]
        previos = [c["body"] for c in de_confianza if c["created_at"] <= t]
        publicadas: tuple[Evidencia, ...] = ()
        for c in de_confianza:
            if c["created_at"] == t and (lo := evidencias_publicadas(c["body"])) is not None:
                publicadas = lo
        hoy = evidencias_de_hoy(previos)
        coincide = coinciden(publicadas, hoy)
        reproducidos += coincide
        lo_publicado = (
            "; ".join(f"{a.split('/')[-1][:40]} {r}" for a, r in publicadas) or "(sin evidencias)"
        )
        casa = "si" if coincide else "NO"
        print(f"| #{n} | {t} | {lo_publicado} | {detector_de_hoy(previos)} | {casa} |")
    print(
        f"\nAvisos reproducidos por el detector de hoy (mismo fichero y tramo publicado "
        f"contenido en el de hoy): {reproducidos} de {len(avisos)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
