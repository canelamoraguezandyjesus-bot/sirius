"""Falsos negativos del detector de familia repetida en la ventana, derivados.

Para CADA incidencia con alguna ronda en la ventana (las de `resumen.json`):

1. se reconstruye, ronda a ronda, lo que el motor veia en ese instante (los
   comentarios de confianza publicados hasta esa ronda, incluida, y nunca mas
   alla del fin de la ventana) y se le pasa el detector de HOY -el mismo codigo
   que `sirius-familia-repetida`, que mira solo lo que hay tras el ultimo
   marcador de reanudacion-. Evaluar solo el historial final no vale: un
   `continua` posterior borra del tramo vigente una familia que SI habria
   avisado antes (Codex, PR #665 ronda 2);
2. una incidencia «marca» si el detector de hoy marca en algun prefijo;
3. las marcadas que no recibieron ningun AVISO_FAMILIA_REPETIDA en la ventana
   son los falsos negativos de entonces.

La clasificacion es una funcion pura (`clasificar`) con sus pruebas en
`tests/automation/test_mina_falsos_negativos.py`; `main` solo lee el volcado
de donde diga `MINA_DATOS` (ver `datos.py`) y la imprime.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analizar import FIN, confianza
from datos import DATOS, RAW
from reproducir_avisos import detector_de_hoy

from sirius_engine.round_history import parse_round_records


@dataclass(frozen=True)
class Prefijo:
    """El veredicto del detector de hoy sobre lo publicado hasta una ronda."""

    ronda: int | None
    instante: str
    veredicto: str  # «no» o «SI: ...»

    @property
    def marca(self) -> bool:
        return self.veredicto != "no"


@dataclass(frozen=True)
class Clasificacion:
    incidencia: int
    prefijos: tuple[Prefijo, ...]
    avisos: int
    estado: str = field(init=False)  # sin_familia | avisada | falso_negativo

    def __post_init__(self) -> None:
        marcados = [p for p in self.prefijos if p.marca]
        if not marcados:
            estado = "sin_familia"
        elif self.avisos:
            estado = "avisada"
        else:
            estado = "falso_negativo"
        object.__setattr__(self, "estado", estado)

    @property
    def primera_marca(self) -> Prefijo | None:
        return next((p for p in self.prefijos if p.marca), None)


def prefijos(comentarios: Iterable[Mapping[str, str]], *, fin: str) -> tuple[Prefijo, ...]:
    """Un `Prefijo` por comentario que publica una ronda, en orden, hasta `fin`."""
    acumulado: list[str] = []
    salida: list[Prefijo] = []
    for c in sorted(comentarios, key=lambda c: c["created_at"]):
        if c["created_at"] > fin:
            break
        acumulado.append(c["body"])
        registros = parse_round_records(c["body"])
        if not registros:
            continue
        salida.append(
            Prefijo(registros[0].get("round"), c["created_at"], detector_de_hoy(acumulado))
        )
    return tuple(salida)


def clasificar(
    comentarios_por_incidencia: Mapping[int, Iterable[Mapping[str, str]]],
    avisos: Iterable[tuple[int, str]],
    *,
    fin: str,
) -> dict[int, Clasificacion]:
    """La clasificacion de cada incidencia; `avisos` son (incidencia, instante)."""
    avisos_en_ventana: dict[int, int] = {}
    for n, instante in avisos:
        if instante <= fin:
            avisos_en_ventana[int(n)] = avisos_en_ventana.get(int(n), 0) + 1
    return {
        int(n): Clasificacion(int(n), prefijos(cs, fin=fin), avisos_en_ventana.get(int(n), 0))
        for n, cs in comentarios_por_incidencia.items()
    }


def main() -> int:
    resumen = json.loads((DATOS / "resumen.json").read_text(encoding="utf-8"))
    comentarios: dict[int, list[dict[str, str]]] = {}
    for n in resumen["incidencias"]:
        d = json.loads((RAW / f"issue_{int(n)}.json").read_text(encoding="utf-8"))
        comentarios[int(n)] = [c for c in d["comments"] if confianza(c)]
    resultado = clasificar(
        comentarios, [(int(n), t) for n, t in resumen["avisos_familia"]], fin=FIN
    )
    print(
        "| incidencia | primera ronda en la que marca el detector de hoy | "
        "avisos en la ventana | estado |"
    )
    print("|---|---|---|---|")
    for n in sorted(resultado):
        c = resultado[n]
        primera = c.primera_marca
        marca = f"ronda {primera.ronda}: {primera.veredicto}" if primera else "no marca"
        print(f"| #{n} | {marca} | {c.avisos} | {c.estado} |")
    marcadas = sorted(n for n, c in resultado.items() if c.estado != "sin_familia")
    avisadas = sorted(n for n, c in resultado.items() if c.estado == "avisada")
    falsos = sorted(n for n, c in resultado.items() if c.estado == "falso_negativo")
    print(f"\nIncidencias examinadas: {len(resultado)} (historiales hasta {FIN})")
    print(f"El detector de hoy marca en algun prefijo en {len(marcadas)}: {marcadas}")
    print(f"De esas, con aviso publicado en la ventana: {len(avisadas)}: {avisadas}")
    print(f"Sin ningun aviso (falsos negativos de entonces): {len(falsos)}: {falsos}")
    for n in falsos:
        print(f"\n#{n}: ronda a ronda")
        for p in resultado[n].prefijos:
            print(f"  ronda {p.ronda} @ {p.instante}: {p.veredicto}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
