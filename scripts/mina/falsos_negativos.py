"""Falsos negativos del detector de familia repetida en la ventana, derivados por TRAMO.

Para CADA incidencia con alguna ronda en la ventana (las de `resumen.json`):

1. se reconstruye, ronda a ronda, lo que el motor veia en ese instante (los
   comentarios de confianza publicados hasta esa ronda, incluida, y nunca mas
   alla del fin de la ventana) y se le pasa el detector de HOY -el mismo codigo
   que `sirius-familia-repetida`, que mira solo lo que hay tras el ultimo
   marcador de reanudacion-. Evaluar solo el historial final no vale: un
   `continua` posterior borra del tramo vigente una familia que SI habria
   avisado antes (Codex, PR #665 ronda 2);
2. la unidad es el TRAMO -un fichero con hallazgos en tres o mas rondas
   consecutivas-, no la incidencia: #570 tiene dos tramos reales distintos
   (1-3 y 2-4) y la edicion del 14-09 ya contaba «6 falsos negativos en 5
   incidencias» (Codex, PR #665 ronda 3). De cada tramo se guarda la primera
   ronda en la que el detector lo marca y el instante de ese comentario;
3. un AVISO_FAMILIA_REPETIDA de la ventana CUBRE los tramos de su incidencia
   marcados hasta su instante (el aviso lista todas las evidencias que el
   detector vio); un tramo marcado despues del ultimo aviso -o en una
   incidencia sin avisos- es un falso negativo de entonces.

La clasificacion es una funcion pura (`clasificar`) con sus pruebas en
`tests/automation/test_mina_falsos_negativos.py`; `main` solo lee el volcado
de donde diga `MINA_DATOS` (ver `datos.py`) y la imprime.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analizar import FIN, confianza
from datos import DATOS, RAW
from reproducir_avisos import evidencias_de_hoy

from sirius_engine.round_history import parse_round_records


@dataclass(frozen=True)
class Tramo:
    """Una familia que el detector de hoy marca: el fichero, el tramo mas largo
    visto y la primera ronda (y su instante) en la que se marco."""

    archivo: str
    rondas: tuple[int, ...]
    primera_ronda: int | None
    primer_instante: str
    cubierto_por_aviso: bool

    @property
    def nombre(self) -> str:
        return self.archivo.split("/")[-1][:40]


@dataclass(frozen=True)
class Clasificacion:
    incidencia: int
    rondas_evaluadas: int
    tramos: tuple[Tramo, ...]
    avisos: int

    @property
    def sin_aviso(self) -> tuple[Tramo, ...]:
        return tuple(t for t in self.tramos if not t.cubierto_por_aviso)

    @property
    def estado(self) -> str:
        if not self.tramos:
            return "sin_familia"
        return "falso_negativo" if self.sin_aviso else "avisada"


def tramos_de(
    comentarios: Iterable[Mapping[str, str]], avisos: Iterable[str], *, fin: str
) -> tuple[int, tuple[Tramo, ...]]:
    """(rondas evaluadas, tramos) de una incidencia, evaluando cada prefijo hasta `fin`."""
    instantes_de_aviso = sorted(a for a in avisos if a <= fin)
    acumulado: list[str] = []
    evaluadas = 0
    primera: dict[str, tuple[int | None, str]] = {}
    mas_largo: dict[str, tuple[int, ...]] = {}
    for c in sorted(comentarios, key=lambda c: c["created_at"]):
        if c["created_at"] > fin:
            break
        acumulado.append(c["body"])
        registros = parse_round_records(c["body"])
        if not registros:
            continue
        evaluadas += 1
        for archivo, rondas in evidencias_de_hoy(acumulado):
            primera.setdefault(archivo, (registros[0].get("round"), c["created_at"]))
            if len(rondas) > len(mas_largo.get(archivo, ())):
                mas_largo[archivo] = rondas
    tramos = tuple(
        Tramo(
            archivo=archivo,
            rondas=mas_largo[archivo],
            primera_ronda=ronda,
            primer_instante=instante,
            cubierto_por_aviso=any(a >= instante for a in instantes_de_aviso),
        )
        for archivo, (ronda, instante) in primera.items()
    )
    return evaluadas, tramos


def clasificar(
    comentarios_por_incidencia: Mapping[int, Iterable[Mapping[str, str]]],
    avisos: Iterable[tuple[int, str]],
    *,
    fin: str,
) -> dict[int, Clasificacion]:
    """La clasificacion de cada incidencia; `avisos` son (incidencia, instante)."""
    por_incidencia: dict[int, list[str]] = {}
    for n, instante in avisos:
        por_incidencia.setdefault(int(n), []).append(instante)
    resultado: dict[int, Clasificacion] = {}
    for n, cs in comentarios_por_incidencia.items():
        avisos_n = por_incidencia.get(int(n), [])
        evaluadas, tramos = tramos_de(cs, avisos_n, fin=fin)
        resultado[int(n)] = Clasificacion(
            int(n), evaluadas, tramos, len([a for a in avisos_n if a <= fin])
        )
    return resultado


def main() -> int:
    resumen = json.loads((DATOS / "resumen.json").read_text(encoding="utf-8"))
    comentarios: dict[int, list[dict[str, str]]] = {}
    for n in resumen["incidencias"]:
        d = json.loads((RAW / f"issue_{int(n)}.json").read_text(encoding="utf-8"))
        comentarios[int(n)] = [c for c in d["comments"] if confianza(c)]
    avisos = [(int(n), t) for n, t in resumen["avisos_familia"]]
    resultado = clasificar(comentarios, avisos, fin=FIN)
    print(
        "| incidencia | tramo (fichero, rondas) | primera ronda en la que marca | "
        "aviso que lo cubre | estado |"
    )
    print("|---|---|---|---|---|")
    for n in sorted(resultado):
        c = resultado[n]
        if not c.tramos:
            print(f"| #{n} | — | no marca | — | sin_familia |")
        for t in c.tramos:
            cubierto = "si" if t.cubierto_por_aviso else "NO"
            print(
                f"| #{n} | `{t.nombre}` {t.rondas} | ronda {t.primera_ronda} @ "
                f"{t.primer_instante} | {cubierto} | {c.estado} |"
            )
    tramos = [(n, t) for n, c in sorted(resultado.items()) for t in c.tramos]
    sin_aviso = [(n, t) for n, t in tramos if not t.cubierto_por_aviso]
    marcadas = sorted({n for n, _ in tramos})
    con_falso_negativo = sorted({n for n, _ in sin_aviso})
    print(f"\nIncidencias examinadas: {len(resultado)} (historiales hasta {FIN})")
    print(
        f"Tramos que el detector de hoy marca en alguna ronda: {len(tramos)}, "
        f"en {len(marcadas)} incidencias: {marcadas}"
    )
    print(f"Tramos cubiertos por un aviso de la ventana: {len(tramos) - len(sin_aviso)}")
    print(
        f"Tramos sin aviso (falsos negativos de entonces): {len(sin_aviso)}, "
        f"en {len(con_falso_negativo)} incidencias: {con_falso_negativo}"
    )
    for n, t in sin_aviso:
        print(
            f"  #{n} `{t.nombre}` {t.rondas}: marcado desde la ronda {t.primera_ronda} "
            f"({t.primer_instante})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
