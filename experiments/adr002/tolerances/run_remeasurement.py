"""Runner de remedicion del paquete 02B.

    uv run python -m experiments.adr002.tolerances.run_remeasurement

Produce ``artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json``:

- **arrastra literalmente** del v0.1 toda la evidencia que el 02B no
  corrige (latencias, barrido, TOL-002, tamano, estabilidad intra-sesion
  y control de fuga de ambito);
- **remide** el ciclo del indice con al menos 30 repeticiones sobre
  copias limpias y la variacion entre al menos 5 sesiones independientes;
- **marca el alcance**: todas las cifras son LAB-LINUX; la aceptacion
  sobre Windows queda pendiente.

El artefacto v0.1 no se modifica ni se borra. No ejecuta T1-T4, no usa
red, no usa datos reales y no toca ningun fichero productivo.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from experiments.adr002.tolerances import corpus, remeasurement
from experiments.adr002.tolerances.harness import REPETICIONES_MINIMAS, REPS_BARATO, REPS_CARO

ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "adr002_tolerances"
FICHERO_V01 = "mediciones_linea_base.json"
FICHERO_V02 = "mediciones_linea_base_v0.2.json"

# Secciones del v0.1 que el 02B NO corrige y se arrastran literalmente.
ARRASTRADAS = (
    "E-LAT-0_cero_resultados",
    "E-LAT-1_un_resultado_exacto",
    "E-LAT-N_muchos_candidatos",
    "E-BARRIDO_coste_del_barrido_completo",
    "E-TOL002_indistinguibilidad",
    "E-ESTABILIDAD",
    "E-TAMANO",
    "E-CONTROL_fuga_de_ambito",
)

ALCANCE = {
    "LAB-LINUX": (
        "Todas las cifras de esta ronda son umbrales del LABORATORIO COMPARATIVO LINUX. Sirven "
        "para comparar T1-T4 entre si en el mismo entorno, y solo para eso."
    ),
    "ACEPTACION-WINDOWS": (
        "PENDIENTE. Ninguna cifra absoluta de latencia, tamano o ciclo se traslada "
        "automaticamente a Windows. La aceptacion del producto exige confirmar el "
        "comportamiento sobre el ejecutable o el entorno de referencia Windows, incluidos el "
        "tokenizador, secure_delete y la secuencia de purga que ADR-001 dejo pendientes."
    ),
    "que_si_es_trasladable": (
        "Las comprobaciones booleanas: restitucion identica, integrity-check, desaparicion "
        "completa del derivado y estabilidad de orden y conjunto. Son propiedades de "
        "comportamiento, no cifras de rendimiento."
    ),
}


def _entorno() -> dict[str, Any]:
    import sqlite3

    import alembic
    import sqlalchemy

    try:
        commit = (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=Path(__file__).resolve().parents[3],
            ).stdout.strip()
            or "desconocido"
        )
    except OSError, subprocess.CalledProcessError:  # pragma: no cover - defensivo
        commit = "desconocido"

    return {
        "python": sys.version.split()[0],
        "sqlite_biblioteca": sqlite3.sqlite_version,
        "sqlalchemy": sqlalchemy.__version__,
        "alembic": alembic.__version__,
        "plataforma": platform.system().lower(),
        "maquina": platform.machine(),
        "commit": commit,
        "red": "no utilizada",
        "datos_reales": "ninguno; corpus sintetico determinista",
        "embeddings_o_modelos_externos": "ninguno",
        "alcance": "LAB-LINUX",
    }


def _metodologia() -> dict[str, Any]:
    return {
        "reloj": "time.perf_counter_ns (monotonico)",
        "percentil": "rango mas cercano (nearest-rank); nunca interpolado",
        "repeticiones_minimas_de_consulta": REPETICIONES_MINIMAS,
        "repeticiones_escenario_barato": REPS_BARATO,
        "repeticiones_escenario_caro": REPS_CARO,
        "ciclo_de_indice": (
            f"minimo {remeasurement.CICLOS_MINIMOS} repeticiones, cada una sobre una copia "
            f"limpia e independiente preparada FUERA del cronometro; "
            f"{remeasurement.WARMUP_CICLO} de warm-up descartadas"
        ),
        "sesiones": (
            f"minimo {remeasurement.SESIONES_MINIMAS} sesiones completas independientes, cada "
            f"una con fichero, motor, cache y warm-up propios"
        ),
        "formula_de_variacion": "(max - min) / min sobre el mismo percentil en todas las sesiones",
        "fixtures_fuera_del_cronometro": (
            "copias, conexiones, lectura de DDL y verificaciones nunca entran en el tiempo medido"
        ),
        "codigo_medido": (
            "codigo real de Sirius 0.1 sin modificar, sobre el esquema de la cadena canonica "
            "de Alembic"
        ),
    }


def main() -> int:
    inicio = time.perf_counter()

    v01_path = ARTIFACTS_DIR / FICHERO_V01
    if not v01_path.exists():
        print(f"falta la evidencia del paquete 02: {v01_path}")
        return 1
    v01 = json.loads(v01_path.read_text(encoding="utf-8"))

    print("preparando el corpus de referencia (5.000 mensajes, 500 recuerdos)...")
    database_path, ids = corpus.corpus_de_referencia("adr002_remed_")
    print(f"  corpus listo: memorias vigentes={ids.memorias_vigentes}")

    print(f"midiendo el ciclo del indice ({remeasurement.CICLOS_MINIMOS} repeticiones)...")
    ciclo = remeasurement.medir_ciclo_repetido(database_path)

    print(f"midiendo {remeasurement.SESIONES_MINIMAS} sesiones independientes...")
    sesiones = remeasurement.medir_sesiones(database_path, ids)

    payload: dict[str, Any] = {
        "documento": "Mediciones de linea base FTS5 para ADR-002 — remedicion 02B",
        "version": "0.2",
        "estado": "PROPUESTO",
        "paquete": "SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02B_CORRECCION_TOLERANCIAS_v0.1",
        "sustituye_a": FICHERO_V01,
        "conserva_sin_modificar": FICHERO_V01,
        "alcance": ALCANCE,
        "entorno": _entorno(),
        "metodologia": _metodologia(),
        "corpus": v01["corpus"],
        "evidencia_arrastrada_del_paquete_02": {
            "procedencia": (
                f"{FICHERO_V01}, commit {v01['entorno']['commit']}. Secciones que el 02B no "
                f"corrige, copiadas literalmente y NO reejecutadas."
            ),
            **{clave: v01["escenarios"][clave] for clave in ARRASTRADAS},
        },
        "escenarios_remedidos": {
            "E-CICLO-30_borrado_construccion_reconstruccion": ciclo,
            "E-SESIONES-5_variacion_entre_ejecuciones": sesiones,
        },
        "no_medido": {
            "coste_incremental_por_etapa_E0_E5": (
                "NO MEDIBLE EN LA LINEA BASE: Sirius 0.1 no tiene etapas. Resuelve en una sola "
                "pasada mas un barrido completo, que es exactamente el salto que B04-RF-14 "
                "prohibe. Solo puede medirse contra un candidato que implemente E0-E5."
            ),
            "aceptacion_windows": ALCANCE["ACEPTACION-WINDOWS"],
            "variacion_entre_procesos_o_maquinas": (
                "Las sesiones son independientes dentro del mismo proceso. La variacion entre "
                "procesos distintos y entre maquinas distintas NO se ha medido."
            ),
            "coste_externo": "ninguno: no se ha usado red, API ni modelo externo",
            "T1_a_T4": "no ejecutadas en esta ronda",
        },
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    destino = ARTIFACTS_DIR / FICHERO_V02
    destino.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    _resumen(ciclo, sesiones)
    print(f"\nmediciones v0.2: {destino}")
    print(f"v0.1 conservado sin modificar: {v01_path}")
    print(f"duracion total: {time.perf_counter() - inicio:.1f} s")
    return 0


def _resumen(ciclo: dict[str, Any], sesiones: dict[str, Any]) -> None:
    print(f"\nCICLO DEL INDICE — {ciclo['repeticiones']} repeticiones sobre copias limpias (ms)")
    print(f"  {'operacion':<34} {'P50':>9} {'P95':>9} {'P99':>9} {'min':>9} {'max':>9}")
    for clave in ("borrado", "construccion_desde_canon", "reconstruccion_desde_canon"):
        d = ciclo[clave]
        print(
            f"  {clave:<34} {d['p50_ms']:>9.3f} {d['p95_ms']:>9.3f} {d['p99_ms']:>9.3f} "
            f"{d['min_ms']:>9.3f} {d['max_ms']:>9.3f}"
        )
    obs = ciclo["observacion_rebuild_interno"]
    print(
        f"  {'(obs.) rebuild interno':<34} {obs['p50_ms']:>9.3f} {obs['p95_ms']:>9.3f} "
        f"{obs['p99_ms']:>9.3f} {obs['min_ms']:>9.3f} {obs['max_ms']:>9.3f}"
    )
    print("\n  tasas de exito:")
    for clave, valor in ciclo["tasas_de_exito"].items():
        print(f"    {clave:<34} {valor['exitos']:>3}/{valor['de']:<3} = {valor['tasa']:.0%}")
    print(f"  todas al 100 %: {ciclo['todas_las_comprobaciones_al_100']}")

    print(f"\nSESIONES — {sesiones['sesiones']} independientes")
    print(f"  {'escenario':<22} {'capa':<10} {'P50 por sesion (ms)':<44} {'var. max':>9}")
    variacion = sesiones["variacion_entre_sesiones"]
    for escenario in ("cero_resultados", "un_resultado_exacto", "muchos_candidatos"):
        for capa, etiqueta in (
            ("solo_indice_fts5", "FTS5"),
            ("recuperacion_completa_rank", "rank()"),
        ):
            entrada = variacion[escenario][f"{capa}__p50_ms"]
            valores = " ".join(f"{v:.3f}" for v in entrada["valores_por_sesion"])
            print(
                f"  {escenario:<22} {etiqueta:<10} {valores:<44} "
                f"{entrada['variacion_max_relativa']:>8.1%}"
            )
    peor = variacion["peor_variacion_relativa_observada"]
    print(f"\n  peor variacion relativa observada: {peor:.1%}")
    estabilidad = sesiones["estabilidad_entre_sesiones"]["resumen"]
    print(
        f"  orden estable entre sesiones: {estabilidad['orden_estable_entre_sesiones']} · "
        f"conjunto estable: {estabilidad['conjunto_estable_entre_sesiones']}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
