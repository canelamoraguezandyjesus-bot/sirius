"""Runner completo de medicion de la linea base FTS5.

    uv run python -m experiments.adr002.tolerances.run_measurements

Produce ``artifacts/adr002_tolerances/mediciones_linea_base.json`` con el
entorno, la metodologia y todos los escenarios del §5.2 del paquete 02.

No ejecuta T1-T4, no usa red, no usa datos reales y no toca ningun
fichero productivo.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from experiments.adr002.tolerances import corpus, measurements
from experiments.adr002.tolerances.harness import (
    REPETICIONES_MINIMAS,
    REPS_BARATO,
    REPS_CARO,
)

ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "adr002_tolerances"
FICHERO = "mediciones_linea_base.json"


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
    }


def _metodologia() -> dict[str, Any]:
    return {
        "reloj": "time.perf_counter_ns (monotonico)",
        "warmup_por_escenario": measurements.WARMUP,
        "repeticiones_minimas_exigidas": REPETICIONES_MINIMAS,
        "repeticiones_escenario_barato": REPS_BARATO,
        "repeticiones_escenario_caro": REPS_CARO,
        "percentil": "rango mas cercano (nearest-rank); nunca interpolado",
        "fixtures_fuera_del_cronometro": (
            "el corpus y los repositorios se construyen antes de medir; su coste nunca entra en "
            "la latencia de consulta"
        ),
        "pareado": "las ramas de TOL-002 se muestrean intercaladas para anular la deriva",
        "aleatoriedad": "ninguna; el corpus es determinista y no usa semillas",
        "aislamiento": "una unica maquina y un unico proceso para todas las comparaciones",
        "codigo_medido": (
            "codigo real de Sirius 0.1 sin modificar: SqliteKnowledgeSearchRepository y "
            "RankRelevantKnowledgeUseCase, sobre el esquema de la cadena canonica de Alembic"
        ),
    }


def main() -> int:
    inicio = time.perf_counter()
    print("preparando el corpus de referencia (5.000 mensajes, 500 recuerdos)...")
    banco = measurements.preparar_banco()
    try:
        head = _head_alembic(banco.database_path)
        print(f"  corpus listo: head={head}, memorias vigentes={banco.ids.memorias_vigentes}")

        print("midiendo latencias por escenario...")
        latencias = measurements.medir_latencias(banco)

        print("midiendo indistinguibilidad temporal (TOL-002)...")
        indistinguibilidad = measurements.medir_indistinguibilidad(banco)

        print("midiendo estabilidad de conjunto y orden...")
        estabilidad = measurements.medir_estabilidad(banco)

        print("midiendo tamano fisico de los indices...")
        tamano = measurements.medir_tamano(banco.database_path)

        print("midiendo construccion, reconstruccion y borrado...")
        ciclo = measurements.medir_construccion_y_reconstruccion(banco.database_path)

        print("confirmando el control de fuga de ambito al volumen de referencia...")
        fuga = measurements.medir_fuga_de_ambito(banco)

        payload: dict[str, Any] = {
            "documento": "Mediciones de linea base FTS5 para ADR-002",
            "estado": "PROPUESTO",
            "paquete": "SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02_TOLERANCIAS_Y_MEDICION_v0.1",
            "entorno": _entorno(),
            "metodologia": _metodologia(),
            "corpus": {
                "mensajes": banco.ids.mensajes,
                "recuerdos": corpus.RECUERDOS,
                "memorias_vigentes": banco.ids.memorias_vigentes,
                "memorias_con_token_frecuente": banco.ids.memorias_frecuentes,
                "decisiones_aprobadas": banco.ids.decisiones_aprobadas,
                "proyectos": 2,
                "head_alembic": head,
                "tokens_de_control": {
                    "ausencia_real": corpus.TOKEN_AUSENTE,
                    "resultado_unico": corpus.TOKEN_UNICO,
                    "alta_frecuencia": corpus.TOKEN_FRECUENTE,
                    "no_reportable_archivado": corpus.TOKEN_NO_REPORTABLE,
                    "proyecto_ajeno": corpus.TOKEN_AJENO,
                },
            },
            "escenarios": {
                **latencias,
                "E-TOL002_indistinguibilidad": indistinguibilidad,
                "E-ESTABILIDAD": estabilidad,
                "E-TAMANO": tamano,
                **ciclo,
                "E-CONTROL_fuga_de_ambito": fuga,
            },
            "no_medido": {
                "coste_incremental_por_etapa_E0_E5": (
                    "NO MEDIBLE EN LA LINEA BASE: Sirius 0.1 no tiene etapas. Resuelve en una "
                    "sola pasada mas un barrido completo, que es exactamente el salto que "
                    "B04-RF-14 prohibe. Este valor solo puede medirse contra un candidato que "
                    "implemente E0-E5."
                ),
                "coste_externo": "ninguno: no se ha usado red, API ni modelo externo",
                "T1_a_T4": "no ejecutadas en esta ronda",
            },
        }

        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        destino = ARTIFACTS_DIR / FICHERO
        destino.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        _resumen(payload)
        print(f"\nmediciones: {destino}")
        print(f"duracion total: {time.perf_counter() - inicio:.1f} s")
        return 0
    finally:
        banco.cerrar()


def _head_alembic(database_path: Path) -> str:
    import sqlite3

    connection = sqlite3.connect(str(database_path))
    try:
        return str(connection.execute("SELECT version_num FROM alembic_version").fetchone()[0])
    finally:
        connection.close()


def _resumen(payload: dict[str, Any]) -> None:
    escenarios = payload["escenarios"]
    print("\nLATENCIA (ms)")
    print(f"  {'escenario':<34} {'capa':<12} {'P50':>9} {'P95':>9} {'P99':>9}")
    for nombre in (
        "E-LAT-0_cero_resultados",
        "E-LAT-1_un_resultado_exacto",
        "E-LAT-N_muchos_candidatos",
    ):
        for clave, etiqueta in (
            ("solo_indice_fts5", "FTS5"),
            ("recuperacion_completa_rank", "rank()"),
        ):
            d = escenarios[nombre][clave]
            print(
                f"  {nombre:<34} {etiqueta:<12} "
                f"{d['p50_ms']:>9.3f} {d['p95_ms']:>9.3f} {d['p99_ms']:>9.3f}"
            )

    barrido = escenarios["E-BARRIDO_coste_del_barrido_completo"]
    print(
        f"\nBARRIDO  p50 total {barrido['p50_recuperacion_completa_ms']:.3f} ms; "
        f"atribuible al barrido {barrido['p50_barrido_ms']:.3f} ms "
        f"({barrido['fraccion_del_coste_atribuible_al_barrido']:.1%})"
    )

    tol = escenarios["E-TOL002_indistinguibilidad"]
    print("\nTOL-002 indistinguibilidad")
    print(f"  estado/conteo externos equivalentes : {tol['conteo_externo_equivalente']}")
    print(f"  texto externo equivalente           : {tol['texto_externo_equivalente']}")
    for capa, clave in (
        ("rank()", "tiempo_recuperacion_completa"),
        ("FTS5", "tiempo_solo_indice_fts5"),
    ):
        d = tol[clave]
        signo = d["fraccion_de_signo"]
        print(
            f"  {capa:<8} dif P50 {d['diferencia_p50_ms']:+.4f} ms "
            f"({d['diferencia_relativa_p50']:+.1%}) · fraccion de signo {signo:.2f}"
        )

    est = escenarios["E-ESTABILIDAD"]["resumen"]
    print(
        f"\nESTABILIDAD  orden {est['orden_estable_en_todos_los_escenarios']} · "
        f"conjunto {est['conjunto_estable_en_todos_los_escenarios']}"
    )

    tam = escenarios["E-TAMANO"]
    print(
        f"\nTAMANO  knowledge_fts {tam['knowledge_fts_bytes']:,} B "
        f"(x{tam['ratio_knowledge_fts_sobre_canon']} sobre canon) · "
        f"message_fts {tam['message_fts_bytes']:,} B "
        f"(x{tam['ratio_message_fts_sobre_canon']} sobre canon)"
    )

    print(
        f"\nCICLO  construccion {escenarios['E-CONSTRUCCION_inicial_desde_canon']['ms']:.1f} ms · "
        f"rebuild {escenarios['E-RECONSTRUCCION']['rebuild_interno_ms']:.1f} ms · "
        f"desde canon {escenarios['E-RECONSTRUCCION']['desde_canon_ms']:.1f} ms · "
        f"borrado {escenarios['E-BORRADO_desaparicion_del_derivado']['ms']:.1f} ms"
    )
    print(
        f"  desaparicion completa del derivado: "
        f"{escenarios['E-BORRADO_desaparicion_del_derivado']['desaparicion_completa']}"
    )
    print(f"\nCONTROL fuga de ambito: {escenarios['E-CONTROL_fuga_de_ambito']['hay_fuga']}")


if __name__ == "__main__":
    raise SystemExit(main())
