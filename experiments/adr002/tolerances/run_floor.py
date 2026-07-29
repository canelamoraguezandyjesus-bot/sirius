"""Orquestador de la corrida del suelo de medicion. Fase A: NO se ejecuta.

Este modulo queda preparado en la preinscripcion, pero **no mide nada al
importarse y no mide nada sin ``--execute``**. La medicion real es la
fase D y requiere autorizacion expresa e independiente.

Uso previsto en la fase D, nunca ahora:

    uv run python -m experiments.adr002.tolerances.run_floor \\
        --execute \\
        --preinscription-commit <SHA_A> \\
        --output artifacts/adr002_tolerances/suelo_medicion_v0.1.json

Antes de abrir una sola ventana cronometrada comprueba, fallando cerrado:
arbol de trabajo limpio, HEAD exactamente igual al commit de
preinscripcion, existencia de ese commit, coincidencia de los seis blobs
preinscritos con el arbol, protocolo aprobado intacto, blobs del corpus
congelado intactos y ruta de salida inexistente.
"""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from experiments.adr002.tolerances import floor_probes as sondas
from experiments.adr002.tolerances import floor_protocol as fp

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

CODIGO_OK: Final = 0
CODIGO_BLOQUEADO: Final = 2
CODIGO_SIN_EXECUTE: Final = 3


class EjecucionBloqueadaError(RuntimeError):
    """Una precondicion de custodia o de entorno no se cumple."""


# --------------------------------------------------------------------------
# Acceso a Git, aislado para poder inyectarlo en las pruebas
# --------------------------------------------------------------------------


def _git(*argumentos: str, raiz: Path | None = None) -> str:
    destino = RAIZ_REPOSITORIO if raiz is None else raiz
    completado = subprocess.run(
        ["git", *argumentos],
        cwd=str(destino),
        capture_output=True,
        text=True,
        check=False,
    )
    if completado.returncode != 0:
        msg = f"git {' '.join(argumentos)} fallo: {completado.stderr.strip()}"
        raise EjecucionBloqueadaError(msg)
    return completado.stdout.strip()


def entorno_custodia_real(raiz: Path | None = None) -> fp.EntornoCustodia:
    """Construye el entorno de custodia sobre el repositorio real."""
    destino = RAIZ_REPOSITORIO if raiz is None else raiz

    def leer_bytes(ruta: str) -> bytes:
        return (destino / ruta).read_bytes()

    def es_ancestro(antepasado: str, descendiente: str) -> bool:
        completado = subprocess.run(
            ["git", "merge-base", "--is-ancestor", antepasado, descendiente],
            cwd=str(destino),
            capture_output=True,
            text=True,
            check=False,
        )
        return completado.returncode == 0

    def existe_commit(sha: str) -> bool:
        completado = subprocess.run(
            ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
            cwd=str(destino),
            capture_output=True,
            text=True,
            check=False,
        )
        return completado.returncode == 0

    def head() -> str:
        return _git("rev-parse", "HEAD", raiz=destino)

    def arbol_limpio() -> bool:
        return _git("status", "--porcelain", raiz=destino) == ""

    def diff_vacio(desde: str, hasta: str, rutas: Sequence[str]) -> bool:
        completado = subprocess.run(
            ["git", "diff", "--quiet", f"{desde}..{hasta}", "--", *rutas],
            cwd=str(destino),
            capture_output=True,
            text=True,
            check=False,
        )
        return completado.returncode == 0

    return fp.EntornoCustodia(
        leer_bytes=leer_bytes,
        es_ancestro=es_ancestro,
        existe_commit=existe_commit,
        head=head,
        arbol_limpio=arbol_limpio,
        diff_vacio=diff_vacio,
    )


# --------------------------------------------------------------------------
# Precondiciones
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Precondiciones:
    """Resultado de todas las comprobaciones previas a medir."""

    fallos: tuple[str, ...]

    @property
    def permite_medir(self) -> bool:
        return not self.fallos


def comprobar_precondiciones(
    entorno: fp.EntornoCustodia,
    *,
    sha_a: str,
    salida: Path,
    salida_existe: bool | None = None,
) -> Precondiciones:
    """Comprueba custodia y entorno. Falla cerrado y no mide nada."""
    existe = salida.exists() if salida_existe is None else salida_existe
    fallos = list(fp.verificar_precondiciones_ejecucion(entorno, sha_a=sha_a, salida_existe=existe))

    blobs_preinscritos: dict[str, str] = {}
    for ruta in fp.ARCHIVOS_PREINSCRITOS:
        try:
            blobs_preinscritos[ruta] = fp.blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"fichero preinscrito ilegible: {ruta}")

    try:
        blob_arnes = fp.blob_git(entorno.leer_bytes(fp.ARCHIVO_ARNES_HEREDADO))
    except OSError:
        blob_arnes = ""
        fallos.append(f"arnes heredado ilegible: {fp.ARCHIVO_ARNES_HEREDADO}")

    try:
        ruta_protocolo = f"docs/architecture/{fp.PROTOCOLO}"
        if fp.blob_git(entorno.leer_bytes(ruta_protocolo)) != fp.BLOB_PROTOCOLO_APROBADO:
            fallos.append("el protocolo aprobado ha sido modificado")
    except OSError:
        fallos.append("protocolo aprobado ilegible")

    if blobs_preinscritos and blob_arnes:
        fallos.extend(
            fp.verificar_custodia(
                entorno,
                sha_a=sha_a,
                blobs_preinscritos=blobs_preinscritos,
                blob_arnes=blob_arnes,
            )
        )

    return Precondiciones(fallos=tuple(dict.fromkeys(fallos)))


# --------------------------------------------------------------------------
# Plan de la corrida. Describe la fase D sin ejecutarla.
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlanCorrida:
    """Plan declarado de la corrida futura. No contiene ninguna observacion."""

    procesos: int
    n_por_sonda: int
    warmup_por_sonda: int
    n_reloj: int
    warmup_reloj: int
    semilla: int
    sondas_normativas: tuple[str, ...]
    diagnosticos: tuple[str, ...]
    orden: tuple[str, ...]


def plan_de_corrida(rondas: int = 1) -> PlanCorrida:
    """Construye el plan declarado. Puro: no mide, no abre ficheros."""
    return PlanCorrida(
        procesos=fp.PROCESOS_MINIMOS,
        n_por_sonda=fp.N_SONDA_F,
        warmup_por_sonda=fp.WARMUP_SONDA_F,
        n_reloj=fp.N_SONDA_RELOJ,
        warmup_reloj=fp.WARMUP_SONDA_RELOJ,
        semilla=fp.SEMILLA,
        sondas_normativas=fp.F_NORMATIVO,
        diagnosticos=fp.DIAGNOSTICOS,
        orden=tuple(sondas.orden_round_robin(fp.F_NORMATIVO, rondas)),
    )


# --------------------------------------------------------------------------
# Interfaz de linea de ordenes
# --------------------------------------------------------------------------


def construir_parser() -> argparse.ArgumentParser:
    """Parser sin efectos secundarios."""
    parser = argparse.ArgumentParser(
        prog="run_floor",
        description=(
            "Corrida del suelo de medicion LAB-LINUX para ADR002-TOL-209. "
            "Sin --execute no mide nada."
        ),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="autoriza expresamente la medicion real (fase D)",
    )
    parser.add_argument(
        "--preinscription-commit",
        dest="preinscription_commit",
        default=None,
        help="SHA del commit A de preinscripcion",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help="ruta del artefacto de evidencia a producir",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="imprime el plan declarado de la corrida sin medir",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada. Sin ``--execute`` nunca mide."""
    args = construir_parser().parse_args(argv)

    if args.plan and not args.execute:
        plan = plan_de_corrida()
        print(f"procesos minimos: {plan.procesos}")
        print(f"sondas normativas (F): {list(plan.sondas_normativas)}")
        print(f"diagnosticos (fuera de F): {list(plan.diagnosticos)}")
        print(f"n por sonda de F: {plan.n_por_sonda} · warm-up {plan.warmup_por_sonda}")
        print(f"n de la sonda de reloj: {plan.n_reloj} · warm-up {plan.warmup_reloj}")
        print(f"U = {fp.FACTOR_U} * B · m = {fp.MARGEN_M}")
        return CODIGO_OK

    if not args.execute:
        print(
            "run_floor no mide sin --execute. La medicion es la fase D y "
            "requiere autorizacion expresa e independiente."
        )
        return CODIGO_SIN_EXECUTE

    if not args.preinscription_commit or not args.output:
        print("--execute exige ademas --preinscription-commit y --output")
        return CODIGO_BLOQUEADO

    precondiciones = comprobar_precondiciones(
        entorno_custodia_real(),
        sha_a=args.preinscription_commit,
        salida=Path(args.output),
    )
    if not precondiciones.permite_medir:
        print("corrida bloqueada; no se ha medido nada:")
        for fallo in precondiciones.fallos:
            print(f"  - {fallo}")
        return CODIGO_BLOQUEADO

    print(
        "precondiciones satisfechas. La ejecucion de la medicion pertenece a "
        "la fase D y no esta autorizada por el paquete de preinscripcion."
    )
    return CODIGO_BLOQUEADO


if __name__ == "__main__":
    raise SystemExit(main())
