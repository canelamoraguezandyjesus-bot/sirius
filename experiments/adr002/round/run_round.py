"""Recorrido de la ronda primaria de ADR-002. **No mide todavía.**

    uv run python -m experiments.adr002.round.run_round --plan
    uv run python -m experiments.adr002.round.run_round --check

``--plan`` imprime el plan preinscrito: participantes, orden, semilla, sesiones,
repeticiones y registro obligatorio. ``--check`` informa de todo lo que falta
para poder medir.

**No existe una bandera que salte la guarda.** La autorización de la ronda
primaria es un documento del repositorio, no un argumento de línea de órdenes,
y hoy ese documento no existe.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from experiments.adr002.candidates.common import neutrality
from experiments.adr002.cards import card_protocol as cp
from experiments.adr002.cards import verify_cards as verificacion
from experiments.adr002.round import round_protocol as rp

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

CODIGO_OK: Final = 0
CODIGO_BLOQUEADO: Final = 2
CODIGO_SIN_ORDEN: Final = 3

#: Paquetes de candidato cuyo aislamiento se comprueba. `t0_control` no está:
#: no es un candidato, es el arnés del control, y su propia suite lo vigila.
PAQUETES_DE_CANDIDATO: Final[tuple[str, ...]] = (
    "adr002_a",
    "adr002_b",
    "adr002_c",
    "adr002_d",
)

#: Donde vivirá el artefacto cuando exista autorización. Hoy no existe, y este
#: recorrido no lo crea.
SALIDA_PREVISTA: Final = "artifacts/adr002_round/ronda_primaria_v0.1.json"


@dataclass(frozen=True, slots=True)
class DependenciasRonda:
    """Dependencias externas del recorrido, inyectables en las pruebas."""

    entorno_custodia: rp.EntornoCustodia
    fichas_congeladas: Sequence[cp.FichaConfirmada]
    neutralidad: Sequence[str]
    aislamiento: Mapping[str, Sequence[str]]


def dependencias_reales(raiz: Path | None = None) -> DependenciasRonda:
    """Dependencias sobre el repositorio real."""
    destino = RAIZ_REPOSITORIO if raiz is None else raiz
    deps_fichas = verificacion.dependencias_reales(destino)
    resultado = verificacion.verificar(deps_fichas)
    return DependenciasRonda(
        entorno_custodia=deps_fichas.entorno_custodia,
        fichas_congeladas=resultado.confirmadas,
        neutralidad=neutrality.fallos_de_neutralidad(destino),
        aislamiento={
            paquete: neutrality.fallos_de_aislamiento_del_candidato(destino, paquete)
            for paquete in PAQUETES_DE_CANDIDATO
        },
    )


@dataclass(frozen=True, slots=True)
class Resultado:
    """Resultado del recorrido. ``preparado`` nunca significa ``ejecutado``."""

    fallos: tuple[str, ...]
    participantes: tuple[str, ...]

    @property
    def puede_ejecutar(self) -> bool:
        return not self.fallos


def comprobar(dependencias: DependenciasRonda) -> Resultado:
    """Comprueba si la ronda podría ejecutarse. **No la ejecuta.**"""
    precondiciones = rp.comprobar_precondiciones(
        dependencias.entorno_custodia,
        fichas_congeladas=dependencias.fichas_congeladas,
        neutralidad=dependencias.neutralidad,
        aislamiento=dependencias.aislamiento,
    )
    return Resultado(fallos=precondiciones.fallos, participantes=rp.PARTICIPANTES)


def _lineas_del_plan() -> list[str]:
    """El plan preinscrito, tal como se congela antes de medir."""
    lineas = [
        "ronda primaria de ADR-002 — PREINSCRITA, NO EJECUTADA",
        f"  esquema           : {rp.VERSION_ESQUEMA}",
        f"  protocolo         : {rp.PROTOCOLO}",
        f"  especificacion    : {rp.ESPECIFICACION}",
        f"  participantes     : {', '.join(rp.PARTICIPANTES)}  (sin reduccion)",
        f"  sesiones          : {rp.SESIONES_EXIGIDAS} exactas",
        f"  repeticiones      : {rp.REPETICIONES} por escenario y magnitud",
        f"  warm-up           : {rp.WARMUP}, declarado y descartado integro",
        f"  semilla           : {rp.SEMILLA}",
        f"  reloj             : {rp.RELOJ}",
        f"  sustrato          : {rp.SUSTRATO}  (los cinco sobre el MISMO fichero)",
        f"  origen del sustrato: {rp.SUSTRATO_ORIGEN}",
        f"  salida prevista   : {SALIDA_PREVISTA}",
        "",
        "  fichas vigentes preinscritas:",
    ]
    for participante in rp.PARTICIPANTES:
        version, huella = rp.FICHAS_VIGENTES[participante]
        lineas.append(f"    {participante:12} v{version}  {huella}")
    lineas.extend(["", "  orden intercalado y rotado (§5.2), primeras cuatro combinaciones:"])
    for sesion, repeticion in ((1, 1), (1, 2), (2, 1), (2, 2)):
        orden = rp.orden_de_ejecucion(sesion, repeticion)
        lineas.append(f"    sesion {sesion} repeticion {repeticion}: {' -> '.join(orden)}")
    lineas.extend(["", "  controles bloqueantes preinscritos:"])
    lineas.extend(f"    - {control}" for control in rp.CONTROLES_BLOQUEANTES)
    return lineas


def main(
    argv: Sequence[str] | None = None, *, dependencias: DependenciasRonda | None = None
) -> int:
    analizador = argparse.ArgumentParser(
        prog="run_round",
        description="Recorrido preinscrito de la ronda primaria de ADR-002. No mide.",
    )
    analizador.add_argument("--plan", action="store_true", help="imprime el plan preinscrito")
    analizador.add_argument("--check", action="store_true", help="comprueba las precondiciones")
    argumentos = analizador.parse_args(argv)

    if not argumentos.plan and not argumentos.check:
        analizador.print_help()
        return CODIGO_SIN_ORDEN

    if argumentos.plan:
        for linea in _lineas_del_plan():
            print(linea)

    if not argumentos.check:
        return CODIGO_OK

    if argumentos.plan:
        print()
    resultado = comprobar(dependencias or dependencias_reales())
    if resultado.puede_ejecutar:
        # No se alcanza mientras la autorizacion no exista, y cuando exista
        # seguira sin medir: ejecutar es otro acto, no un efecto de comprobar.
        print("precondiciones satisfechas; la ejecucion es un acto aparte y NO ocurre aqui")
        return CODIGO_OK
    print(f"ronda primaria BLOQUEADA: {len(resultado.fallos)} precondicion(es) sin satisfacer")
    for fallo in resultado.fallos:
        print(f"  - {fallo}")
    return CODIGO_BLOQUEADO


if __name__ == "__main__":  # pragma: no cover - punto de entrada
    raise SystemExit(main())
