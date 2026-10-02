"""Las divergencias que el reflector aparta para una persona, escritas junto al diario.

El reflector (:mod:`sirius_engine.reflect`) no toca nada ante una contradicción
de etiquetas, un camino hacia atrás o una parada sin permiso: devuelve el
motivo y sigue. Hasta ADR-227 ese motivo vivía solo en el log del run
(``reflect_cli.py``, una línea por pasada) y ``DESENLACES.md`` contaba el
encargo como «1 activo»: ``WI-20260828-122242`` estuvo así 27 días hasta que
una auditoría lo encontró (H-216, incidencia #662).

Este módulo no decide nada del reflejo. Conserva lo que la pasada declaró, en
``divergencias.json`` junto al diario, y lo deja leer a la vista de desenlaces.
La regla de retención es toda su lógica:

- una divergencia vista en esta pasada se escribe, con la primera vez que se
  vio, la última y cuántas pasadas la han visto;
- una entrada anterior se retira si la pasada evaluó ese encargo y no vio
  divergencia, o si el encargo ya no está entre los que se reflejan
  (terminal, clase que no se despacha, sin episodio);
- una entrada cuyo encargo no se pudo evaluar —incidencia ilegible esta
  pasada, o pasada que murió antes de llegar a él— se conserva con su última
  fecha: no saber no es saber que se resolvió.

Y el fichero dice **cuánto se puede fiar uno de él** (ronda 2 de Codex en la
PR #674): una pasada que no evaluó todos los encargos, o que se interrumpió,
deja escrito que su conocimiento es incompleto y de quién; y si el fichero
anterior era ilegible, lo que hubiera en él puede haberse perdido hasta que una
pasada completa lo rehaga entera. Sin eso, la vista leía «ninguna» donde lo
cierto era «no se sabe».
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

#: Junto al diario, en la rama de memoria; lo confirma el mismo paso que el diario.
FICHERO_DIVERGENCIAS = "divergencias.json"


@dataclass(frozen=True, slots=True)
class DivergenciaVista:
    """Lo que una pasada declara de un encargo: su incidencia y el motivo."""

    work_id: str
    incidencia: int | None
    motivo: str


@dataclass(frozen=True, slots=True)
class DivergenciaApartada:
    """Una divergencia conservada entre pasadas."""

    work_id: str
    incidencia: int | None
    motivo: str
    primera_vez: str
    ultima_vez: str
    pasadas: int


@dataclass(frozen=True, slots=True)
class Instantanea:
    """Lo que la última pasada dejó escrito, y cuánto se puede fiar uno de ello.

    ``interrumpida``: la pasada murió antes de llegar a todos los encargos.
    ``sin_evaluar``: los encargos de los que no pudo concluir nada (incidencia
    ilegible, o entrada anterior a la que no llegó). ``perdida_posible``: el
    fichero anterior era ilegible y ninguna pasada completa ha rehecho el
    conjunto desde entonces, así que lo que hubiera en él puede faltar aquí.
    """

    divergencias: tuple[DivergenciaApartada, ...]
    interrumpida: bool
    sin_evaluar: tuple[str, ...]
    perdida_posible: bool

    @property
    def completa(self) -> bool:
        """La pasada evaluó todos los encargos que se reflejan: el conjunto es entero."""
        return not self.interrumpida and not self.sin_evaluar


def ruta_de_divergencias(diario: Path) -> Path:
    return diario.with_name(FICHERO_DIVERGENCIAS)


def leer_instantanea(ruta: Path) -> Instantanea | None:
    """La instantánea conservada; ``None`` si el fichero no existe.

    ``None`` no es «ninguna divergencia»: es que ninguna pasada ha escrito
    todavía, y la vista lo dice así. Un fichero que no tiene la forma esperada
    es un error, no «ninguna»: lo escribe solo :func:`escribir_instantanea`, y
    leerlo como vacío borraría en silencio lo que una pasada anterior dejó.
    """
    if not ruta.is_file():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{ruta}: no es JSON ({error})") from error
    entradas = datos.get("divergencias") if isinstance(datos, Mapping) else None
    pasada = datos.get("pasada") if isinstance(datos, Mapping) else None
    if not isinstance(entradas, list) or not isinstance(pasada, Mapping):
        raise ValueError(f'{ruta}: no tiene la forma {{"pasada": {{...}}, "divergencias": [...]}}')
    # Tipos exactos, sin coerción: `bool("")` es `False` y `tuple("")` es `()`,
    # así que un fichero con metadatos rotos pasaría por una pasada completa y la
    # vista diría «ninguna» donde debía declarar corrupción (ronda 3 de Codex en
    # la PR #674).
    interrumpida = pasada.get("interrumpida")
    sin_evaluar = pasada.get("sin_evaluar")
    perdida_posible = pasada.get("perdida_posible")
    if (
        not isinstance(interrumpida, bool)
        or not isinstance(perdida_posible, bool)
        or not isinstance(sin_evaluar, list)
        or not all(isinstance(w, str) and w for w in sin_evaluar)
    ):
        raise ValueError(
            f"{ruta}: la pasada está mal formada (interrumpida y perdida_posible tienen que "
            "ser booleanos y sin_evaluar una lista de encargos)"
        )
    return Instantanea(
        divergencias=tuple(_desde_json(ruta, entrada) for entrada in entradas),
        interrumpida=interrumpida,
        sin_evaluar=tuple(sin_evaluar),
        perdida_posible=perdida_posible,
    )


def _desde_json(ruta: Path, entrada: object) -> DivergenciaApartada:
    if not isinstance(entrada, Mapping):
        raise ValueError(f"{ruta}: una entrada no es un objeto")
    try:
        incidencia = entrada["incidencia"]
        return DivergenciaApartada(
            work_id=str(entrada["work_id"]),
            incidencia=int(incidencia) if incidencia is not None else None,
            motivo=str(entrada["motivo"]),
            primera_vez=str(entrada["primera_vez"]),
            ultima_vez=str(entrada["ultima_vez"]),
            pasadas=int(entrada["pasadas"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{ruta}: entrada incompleta o mal formada ({error})") from error


def escribir_instantanea(ruta: Path, instantanea: Instantanea) -> None:
    """Escribe el fichero entero o no lo toca: primero un temporal al lado y
    después un `os.replace`, para que una pasada que muera escribiendo no deje
    un JSON a medias que el paso de confirmar del workflow (`git add -A`,
    `if: always()`) confirmaría tal cual."""
    carga: dict[str, Any] = {
        "pasada": {
            "interrumpida": instantanea.interrumpida,
            "sin_evaluar": sorted(instantanea.sin_evaluar),
            "perdida_posible": instantanea.perdida_posible,
        },
        "divergencias": [
            asdict(d) for d in sorted(instantanea.divergencias, key=lambda d: d.work_id)
        ],
    }
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(
        json.dumps(carga, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporal, ruta)


def actualizar(
    anteriores: Iterable[DivergenciaApartada],
    vistas: Iterable[DivergenciaVista],
    *,
    sin_evaluar: Iterable[str],
    ahora: datetime,
) -> tuple[DivergenciaApartada, ...]:
    """La regla de retención, pura: qué queda escrito tras esta pasada.

    ``sin_evaluar`` son los encargos de los que esta pasada no pudo concluir
    nada: su incidencia no se pudo leer, o la pasada murió antes de llegar a
    ellos. Sus entradas anteriores se conservan tal cual. Cualquier otra
    entrada que la pasada no haya vuelto a ver se retira: el encargo se
    evaluó sin divergencia, o ya no está entre los que se reflejan (terminal,
    clase que no se despacha, sin episodio).
    """
    instante = ahora.isoformat()
    previas = {d.work_id: d for d in anteriores}
    conservar = set(sin_evaluar)
    resultado: dict[str, DivergenciaApartada] = {}
    for vista in vistas:
        previa = previas.get(vista.work_id)
        resultado[vista.work_id] = DivergenciaApartada(
            work_id=vista.work_id,
            incidencia=vista.incidencia,
            motivo=vista.motivo,
            primera_vez=previa.primera_vez if previa is not None else instante,
            ultima_vez=instante,
            pasadas=(previa.pasadas + 1) if previa is not None else 1,
        )
    for work_id, previa in previas.items():
        if work_id not in resultado and work_id in conservar:
            resultado[work_id] = previa
    return tuple(resultado[k] for k in sorted(resultado))


def cerrar_pasada(
    anterior: Instantanea | None,
    vistas: Iterable[DivergenciaVista],
    *,
    anterior_ilegible: bool,
    sin_evaluar: Iterable[str],
    interrumpida: bool,
    ahora: datetime,
) -> Instantanea:
    """La instantánea que deja esta pasada, pura: la retención de
    :func:`actualizar` más lo que se puede fiar uno de ella.

    ``perdida_posible`` nace cuando el fichero anterior era ilegible y se
    hereda mientras las pasadas sigan incompletas: solo una pasada completa
    rehace el conjunto entero y lo apaga.
    """
    anteriores = anterior.divergencias if anterior is not None else ()
    sin_evaluar = tuple(sorted(set(sin_evaluar)))
    completa = not interrumpida and not sin_evaluar
    heredada = anterior is not None and anterior.perdida_posible
    return Instantanea(
        divergencias=actualizar(anteriores, vistas, sin_evaluar=sin_evaluar, ahora=ahora),
        interrumpida=interrumpida,
        sin_evaluar=sin_evaluar,
        perdida_posible=(anterior_ilegible or heredada) and not completa,
    )


def dias_parado(ultimo_suceso: str, ultima_pasada: str) -> str:
    """Días entre el último suceso del encargo en el diario y la última pasada que lo apartó.

    Vive aquí y no en la vista porque la vista no puede ni nombrar el reloj
    (ADR-171, criterio (a)); esto no lo mira: solo resta dos instantes escritos.
    """
    try:
        desde = datetime.fromisoformat(ultimo_suceso)
        hasta = datetime.fromisoformat(ultima_pasada)
    except ValueError:
        return "?"
    if (desde.tzinfo is None) != (hasta.tzinfo is None):
        return "?"
    return str(max((hasta - desde).days, 0))
