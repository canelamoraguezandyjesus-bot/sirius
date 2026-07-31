"""Recorrido de la rederivacion de T0 (ADR002-TOL-208, paquete 10).

**No mide todavia.** El recorrido comprueba precondiciones y se detiene: la
autorizacion para ejecutar T0 no existe, y su ausencia es una guarda que falla
cerrado, no una advertencia.

    uv run python -m experiments.adr002.rederivation.run_rederivation --plan
    uv run python -m experiments.adr002.rederivation.run_rederivation --check

``--check`` informa de todo lo que falta para poder rederivar. No existe una
bandera que salte la guarda: la autorizacion es un documento del repositorio,
no un argumento de linea de ordenes.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from experiments.adr002.cards import card_protocol as cp
from experiments.adr002.cards import verify_cards as verificacion
from experiments.adr002.rederivation import rederivation_protocol as rp

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

CODIGO_OK: Final = 0
CODIGO_BLOQUEADO: Final = 2
CODIGO_SIN_CHECK: Final = 3

#: Donde vivira el artefacto cuando exista autorizacion. Hoy no existe.
SALIDA_PREVISTA: Final = "artifacts/adr002_tolerances/rederivacion_t0_v0.1.json"


@dataclass(frozen=True, slots=True)
class DependenciasRederivacion:
    """Dependencias externas del recorrido, inyectables en las pruebas."""

    entorno_custodia: rp.EntornoCustodia
    fichas_congeladas: Sequence[cp.FichaConfirmada]


def dependencias_reales(raiz: Path | None = None) -> DependenciasRederivacion:
    """Dependencias sobre el repositorio real."""
    destino = RAIZ_REPOSITORIO if raiz is None else raiz
    deps_fichas = verificacion.dependencias_reales(destino)
    resultado = verificacion.verificar(deps_fichas)
    return DependenciasRederivacion(
        entorno_custodia=deps_fichas.entorno_custodia,
        fichas_congeladas=resultado.confirmadas,
    )


@dataclass(frozen=True, slots=True)
class Resultado:
    """Resultado del recorrido. ``preparado`` nunca significa ``ejecutado``."""

    fallos: tuple[str, ...]
    magnitudes_previstas: tuple[str, ...]

    @property
    def puede_ejecutar(self) -> bool:
        return not self.fallos


def comprobar(dependencias: DependenciasRederivacion) -> Resultado:
    """Comprueba si la rederivacion podria ejecutarse. **No la ejecuta.**"""
    precondiciones = rp.comprobar_precondiciones(
        dependencias.entorno_custodia, fichas_congeladas=dependencias.fichas_congeladas
    )
    return Resultado(fallos=precondiciones.fallos, magnitudes_previstas=rp.magnitudes_previstas())


def construir_parser() -> argparse.ArgumentParser:
    """Parser sin efectos secundarios. **No hay bandera que salte la guarda.**"""
    parser = argparse.ArgumentParser(
        prog="run_rederivation",
        description=(
            "Comprueba las precondiciones de los pasos 2 y 3 de ADR002-TOL-208. "
            "No mide, no ejecuta T0 y no escribe nada."
        ),
    )
    parser.add_argument("--check", action="store_true", help="comprueba precondiciones")
    parser.add_argument("--plan", action="store_true", help="imprime el plan preinscrito")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    dependencias: DependenciasRederivacion | None = None,
) -> int:
    """Punto de entrada. No escribe nada en ningun caso."""
    args = construir_parser().parse_args(argv)

    if args.plan and not args.check:
        print(f"paquete: {rp.PAQUETE}")
        print(f"protocolo: {rp.PROTOCOLO}")
        print(f"corpus congelado: {list(rp.CORPUS_CONGELADO)}")
        print(f"candidato: {rp.CANDIDATO} (head de Alembic {rp.HEAD_T0})")
        print(f"escenarios: {list(rp.ESCENARIOS)}")
        print(f"capas: {list(rp.CAPAS)}")
        print(f"sesiones: {rp.SESIONES_EXIGIDAS} (exactamente)")
        print(f"repeticiones por magnitud: {rp.REPETICIONES}")
        print(f"magnitudes previstas: {len(rp.magnitudes_previstas())}")
        print(f"controles bloqueantes: {len(rp.CONTROLES_BLOQUEANTES)}")
        print(f"salida prevista: {SALIDA_PREVISTA}")
        print(f"autorizacion exigida: {rp.ACTA_DE_AUTORIZACION}")
        return CODIGO_OK

    if not args.check:
        print("run_rederivation no comprueba nada sin --check.")
        return CODIGO_SIN_CHECK

    deps = dependencias_reales() if dependencias is None else dependencias
    resultado = comprobar(deps)

    if not resultado.puede_ejecutar:
        print("la rederivacion de T0 NO puede ejecutarse. Falta:")
        for fallo in resultado.fallos:
            print(f"  - {fallo}")
        print("")
        print("Ejecutar T0 exige autorizacion expresa e independiente.")
        return CODIGO_BLOQUEADO

    print("todas las precondiciones se cumplen.")
    print(f"magnitudes previstas: {len(resultado.magnitudes_previstas)}")
    print("Este recorrido NO ejecuta la medicion: la ejecucion es un acto aparte.")
    return CODIGO_OK


if __name__ == "__main__":
    raise SystemExit(main())
