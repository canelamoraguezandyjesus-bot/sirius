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
   consecutivas-, no la incidencia (Codex, ronda 3). Y la identidad de un tramo
   es el fichero MAS la racha: el mismo fichero en las rondas 1-3 y otra vez en
   las 5-7 son dos tramos (Codex, ronda 4); una evidencia que solapa con un tramo
   ya visto es ese mismo tramo, que crece (1-3 y luego 1-4). De cada tramo se
   guarda la primera ronda en la que el detector lo marca y el instante de ese
   comentario;
3. un AVISO_FAMILIA_REPETIDA se reconoce por su cabecera (`## AVISO_FAMILIA_REPETIDA`
   al principio de linea; una mencion en prosa no es un aviso) y se lee lo que
   publico: sus lineas «fichero» ... (rondas a-b). Un tramo esta CUBIERTO si algun
   aviso de su incidencia, dentro de la ventana, lista ese fichero con una racha
   que solapa con la del tramo. Comparar solo instantes no vale: tras un
   `continua`, un aviso por otra familia no pudo contener la evidencia anterior
   (Codex, ronda 4).

La clasificacion es una funcion pura (`clasificar`) con sus pruebas en
`tests/automation/test_mina_falsos_negativos.py`; `main` solo lee el volcado
de donde diga `MINA_DATOS` (ver `datos.py`) y la imprime.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analizar import FIN, INICIO, confianza, es_aviso_de_familia
from datos import DATOS, RAW
from reproducir_avisos import evidencias_de_hoy

from sirius_engine.round_history import parse_round_records

#: La linea con la que el motor publica cada evidencia del aviso
#: (`round_family_detector.detectar_familia_repetida`, campo `detalle`).
_EVIDENCIA_PUBLICADA = re.compile(
    r"^- «(?P<archivo>.+?)» recibe hallazgos en \d+ rondas consecutivas "
    r"\(rondas (?P<desde>\d+)-(?P<hasta>\d+)\)",
    re.MULTILINE,
)

Evidencia = tuple[str, tuple[int, ...]]


def evidencias_publicadas(cuerpo: str) -> tuple[Evidencia, ...] | None:
    """Lo que un AVISO_FAMILIA_REPETIDA lista: (fichero, rondas) por evidencia.

    `None` si el comentario no es un aviso (no lleva la cabecera al principio de
    una linea): el propietario que escribe «sobre el AVISO_FAMILIA_REPETIDA...»
    no esta avisando de nada.
    """
    if not es_aviso_de_familia(cuerpo):
        return None
    seccion = cuerpo.split("## AVISO_FAMILIA_REPETIDA", 1)[1]
    return tuple(
        (m["archivo"], tuple(range(int(m["desde"]), int(m["hasta"]) + 1)))
        for m in _EVIDENCIA_PUBLICADA.finditer(seccion)
    )


def _solapan(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    return bool(set(a) & set(b))


@dataclass(frozen=True)
class Tramo:
    """Una familia que el detector de hoy marca: el fichero, la racha completa
    vista y la primera ronda (y su instante) en la que se marco."""

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


@dataclass
class _TramoEnCurso:
    archivo: str
    rondas: tuple[int, ...]
    primera_ronda: int | None
    primer_instante: str
    #: Crecio dentro de la ventana desde una evidencia que ya existia al corte:
    #: el aviso anterior que cubria aquella lo sigue cubriendo.
    heredado: bool = False

    def es_el_mismo(self, archivo: str, rondas: tuple[int, ...]) -> bool:
        return archivo == self.archivo and _solapan(rondas, self.rondas)

    def crece_hasta(self, rondas: tuple[int, ...]) -> None:
        juntas = set(self.rondas) | set(rondas)
        self.rondas = tuple(range(min(juntas), max(juntas) + 1))


def tramos_de(
    comentarios: Iterable[Mapping[str, str]], *, inicio: str, fin: str
) -> tuple[int, tuple[Tramo, ...], int]:
    """(rondas evaluadas, tramos, avisos) de una incidencia, evaluando cada prefijo
    publicado dentro de la ventana [`inicio`, `fin`].

    Lo anterior a `inicio` es CONTEXTO: entra en el historial que ve el detector
    (una familia puede empezar en agosto y marcarse en septiembre), pero no
    cuenta como ronda evaluada, no abre tramos y sus avisos no cuentan como
    avisos de la ventana (Codex, PR #665, ronda 6: evaluar tambien los prefijos
    de agosto atribuia a la medicion 01->30-09 tramos y avisos de fuera de ella).

    Y lo que el detector de hoy ya marcaba AL CORTE -con solo lo publicado antes
    de `inicio`- es un hecho de antes de la ventana: no abre tramo salvo que
    crezca dentro de ella, y si crece lo cubre tambien el aviso anterior que ya
    lo cubria, porque la familia ya estaba avisada (Codex, PR #665, ronda 7: tres
    rondas de agosto sobre un fichero y una de septiembre sobre otro atribuian a
    septiembre el tramo entero de agosto).
    """
    acumulado: list[str] = []
    evaluadas = 0
    en_curso: list[_TramoEnCurso] = []
    publicadas: list[Evidencia] = []
    heredados: list[Evidencia] = []
    al_corte: tuple[Evidencia, ...] | None = None
    avisos = 0
    for c in sorted(comentarios, key=lambda c: c["created_at"]):
        if c["created_at"] > fin:
            break
        if c["created_at"] < inicio:
            acumulado.append(c["body"])
            lo_que_aviso = evidencias_publicadas(c["body"])
            if lo_que_aviso is not None:
                heredados.extend(lo_que_aviso)
            continue
        if al_corte is None:
            al_corte = tuple(evidencias_de_hoy(acumulado))
        acumulado.append(c["body"])
        lo_que_aviso = evidencias_publicadas(c["body"])
        if lo_que_aviso is not None:
            avisos += 1
            publicadas.extend(lo_que_aviso)
        registros = parse_round_records(c["body"])
        if not registros:
            continue
        evaluadas += 1
        for archivo, rondas in evidencias_de_hoy(acumulado):
            de_antes = [r for a, r in al_corte if a == archivo and _solapan(rondas, r)]
            if any(set(rondas) <= set(r) for r in de_antes):
                continue  # ya estaba entero antes de la ventana y no ha crecido
            mismo = next((t for t in en_curso if t.es_el_mismo(archivo, rondas)), None)
            if mismo is None:
                en_curso.append(
                    _TramoEnCurso(
                        archivo,
                        rondas,
                        registros[0].get("round"),
                        c["created_at"],
                        heredado=bool(de_antes),
                    )
                )
            else:
                mismo.crece_hasta(rondas)
    tramos = tuple(
        Tramo(
            archivo=t.archivo,
            rondas=t.rondas,
            primera_ronda=t.primera_ronda,
            primer_instante=t.primer_instante,
            cubierto_por_aviso=any(
                archivo == t.archivo and _solapan(rondas, t.rondas)
                for archivo, rondas in (publicadas + heredados if t.heredado else publicadas)
            ),
        )
        for t in en_curso
    )
    return evaluadas, tramos, avisos


def clasificar(
    comentarios_por_incidencia: Mapping[int, Iterable[Mapping[str, str]]],
    *,
    inicio: str,
    fin: str,
) -> dict[int, Clasificacion]:
    """La clasificacion de cada incidencia a partir de sus comentarios de confianza."""
    resultado: dict[int, Clasificacion] = {}
    for n, cs in comentarios_por_incidencia.items():
        evaluadas, tramos, avisos = tramos_de(cs, inicio=inicio, fin=fin)
        resultado[int(n)] = Clasificacion(int(n), evaluadas, tramos, avisos)
    return resultado


def main() -> int:
    resumen = json.loads((DATOS / "resumen.json").read_text(encoding="utf-8"))
    comentarios: dict[int, list[dict[str, str]]] = {}
    for n in resumen["incidencias"]:
        d = json.loads((RAW / f"issue_{int(n)}.json").read_text(encoding="utf-8"))
        comentarios[int(n)] = [c for c in d["comments"] if confianza(c)]
    resultado = clasificar(comentarios, inicio=INICIO, fin=FIN)
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
    avisos = sum(c.avisos for c in resultado.values())
    print(f"\nIncidencias examinadas: {len(resultado)} (rondas y avisos entre {INICIO} y {FIN})")
    print(
        f"Avisos reconocidos por su cabecera: {avisos} "
        f"(resumen.json lista {len(resumen['avisos_familia'])})"
    )
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
