"""Repeticion unica controlada del §6.8 para ADR002-TOL-208 (evidencia v0.2).

Ejecuta EXACTAMENTE UNA corrida completa de la comparacion de T0, bajo las
condiciones controladas congeladas en ``controlled_conditions`` y con el
arnes de la v0.1 **sin cambios**: mismos escenarios, capas, magnitudes,
sesiones, repeticiones, cronometro, percentiles, perfil, esquema y criterio
de veredicto. Lo UNICO nuevo es el control ambiental —esperas de
asentamiento, registro de arranque— y las rutas v0.2 de salida.

    uv run python -m experiments.adr002.rederivation.execute_repetition --execute

Garantias:

- **Una corrida, y ninguna mas.** No existe bucle de reintento: si la corrida
  resulta invalida —funcional o instrumentalmente— tras abrirse la primera
  ventana cronometrada, la repeticion queda CONSUMIDA, no se escribe ningun
  artefacto y el resultado es ``NO_EVALUABLE`` conforme al §6.9. No hay
  tercera corrida y este modulo no ofrece ninguna puerta para ella.
- **La operacion medida es identica a la de la v0.1.** Cada sesion es el
  MISMO worker de ``execute_rederivation`` invocado con la MISMA orden; este
  modulo no anade ni una linea dentro de la ventana cronometrada.
- **La evidencia v0.1 es intangible.** Sus tres blobs se comprueban antes de
  medir y despues de escribir; las salidas v0.2 se exigen inexistentes.
- El veredicto de cada magnitud lo recomputa el perfil aprobado, como
  siempre; el estado FINAL tras consumir la repeticion lo fija la regla
  ``estado_final_6_9`` congelada antes de medir: pasa -> ``VALIDA``; no pasa
  -> ``NO_EVALUABLE`` en rendimiento. ``INVALIDA`` no es publicable como
  estado definitivo de estabilidad.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from experiments.adr002.rederivation import controlled_conditions as cc
from experiments.adr002.rederivation import execute_rederivation as arnes
from experiments.adr002.rederivation import frozen_corpus as fc
from experiments.adr002.rederivation import rederivation_protocol as rp
from experiments.adr002.rederivation import run_rederivation as recorrido
from experiments.adr002.rederivation import schema_rederivation_v0_1 as esquema
from experiments.adr002.tolerances.run_envelope import (
    entorno_custodia_real,
    escribir_json_atomico,
)

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

CODIGO_OK: Final = arnes.CODIGO_OK
CODIGO_BLOQUEADO: Final = arnes.CODIGO_BLOQUEADO
CODIGO_SIN_EXECUTE: Final = arnes.CODIGO_SIN_EXECUTE
CODIGO_NO_EVALUABLE: Final = arnes.CODIGO_NO_EVALUABLE

SALIDA_V02: Final = "artifacts/adr002_tolerances/rederivacion_t0_v0.2.json"
SALIDA_MUESTRAS_V02: Final = "artifacts/adr002_tolerances/rederivacion_t0_v0.2_muestras.json"

DOCUMENTO_V02: Final = (
    "Repeticion unica controlada (§6.8) de la rederivacion de la linea base "
    "sobre el corpus congelado v0.4 (ADR002-TOL-208)"
)


def ejecutor_sesiones_controladas(
    base_referencia: Path,
    consultas: Mapping[str, str],
    registro: cc.RegistroCondiciones,
) -> list[Mapping[str, Any]]:
    """Once sesiones secuenciales con asentamiento de carga entre ellas.

    La orden del worker es EXACTAMENTE la de la v0.1: el proceso hijo ejecuta
    ``execute_rederivation --execute --worker``, el modulo congelado, de modo
    que la operacion medida no cambia ni un byte. Lo unico que este ejecutor
    anade ocurre FUERA de los procesos de medicion: la espera de asentamiento
    previa a cada sesion, registrada entera.
    """
    resultados: list[Mapping[str, Any]] = []
    orden = [
        sys.executable,
        "-m",
        "experiments.adr002.rederivation.execute_rederivation",
        "--execute",
        "--worker",
        "--db",
        str(base_referencia),
        "--queries",
        json.dumps(dict(consultas), separators=(",", ":")),
    ]
    for numero in range(1, rp.SESIONES_EXIGIDAS + 1):
        espera = cc.esperar_asentamiento(
            f"antes de la sesion {numero}",
            plazo_s=cc.PLAZO_ASENTAMIENTO_ENTRE_SESIONES_S,
        )
        registro.esperas.append(espera)
        if not espera.alcanzado:
            registro.incidencias.append(
                f"asentamiento no alcanzado antes de la sesion {numero}: carga "
                f"{espera.serie[-1]} > {espera.umbral} tras {espera.duracion_s} s; "
                f"la corrida continua y la incidencia queda registrada"
            )
        completado = subprocess.run(
            orden,
            cwd=str(RAIZ_REPOSITORIO),
            capture_output=True,
            text=True,
            check=False,
        )
        if completado.returncode != 0:
            msg = (
                f"sesion {numero} fallida (rc={completado.returncode}): "
                f"{completado.stderr.strip()[:500]}"
            )
            raise arnes.EjecucionBloqueadaError(msg)
        resultados.append(json.loads(completado.stdout))
    return resultados


def documento_v02(
    magnitudes: Sequence[Mapping[str, Any]], controles: Mapping[str, bool]
) -> dict[str, Any]:
    """El artefacto v0.2: el mismo contrato congelado, otro documento."""
    return {
        **arnes.construir_documento(magnitudes=magnitudes, controles=controles),
        "documento": DOCUMENTO_V02,
    }


def muestras_v02(
    *,
    head: str,
    consultas: fc.ConsultasDeControl,
    conteos: fc.ConteosCargados,
    resultados: Sequence[Mapping[str, Any]],
    magnitudes: Sequence[Mapping[str, Any]],
    registro: cc.RegistroCondiciones,
) -> dict[str, Any]:
    """Muestras crudas v0.2 + condiciones controladas + estado final §6.9."""
    base = arnes.documento_de_muestras(
        head=head,
        consultas=consultas,
        conteos=conteos,
        resultados=resultados,
        repeticion_unica_ejercitada=True,
        boot_id=registro.boot_id_inicio,
    )
    return {
        **base,
        "documento": (
            "Muestras crudas de la repeticion unica controlada (§6.8) de la "
            "rederivacion de T0 (ADR002-TOL-208)"
        ),
        "artefacto_normativo": SALIDA_V02,
        "acta_de_repeticion": cc.ACTA_REPETICION,
        "condiciones_controladas": registro.como_dict(),
        "estado_final_6_9_por_magnitud": {
            str(m["magnitud"]): cc.estado_final_6_9(str(m["resultado"])) for m in magnitudes
        },
        "regla_6_9": (
            "la repeticion unica queda consumida con esta corrida: una magnitud que "
            "pasa P50 y P95 es VALIDA; cualquier otra queda NO_EVALUABLE en "
            "rendimiento, e INVALIDA no es publicable como estado definitivo"
        ),
    }


def ejecutar(salida: Path, salida_muestras: Path) -> int:
    """La repeticion unica completa. Una corrida; sin segunda oportunidad."""
    entorno = entorno_custodia_real()
    deps = recorrido.dependencias_reales()

    precondiciones = rp.comprobar_precondiciones(
        deps.entorno_custodia, fichas_congeladas=deps.fichas_congeladas
    )
    head = entorno.head()
    fallos = list(precondiciones.fallos)
    fallos.extend(
        arnes.fallos_adicionales(
            deps.entorno_custodia,
            fichas=deps.fichas_congeladas,
            head=head,
            arbol_limpio=entorno.arbol_limpio(),
            salida_existe=salida.exists(),
            muestras_existen=salida_muestras.exists(),
            es_ancestro=entorno.es_ancestro,
        )
    )
    fallos.extend(cc.fallos_de_acta_de_repeticion(deps.entorno_custodia))
    fallos.extend(cc.fallos_de_evidencia_v01(deps.entorno_custodia))
    if fallos:
        print("la repeticion unica NO puede ejecutarse. Falta:")
        for fallo in fallos:
            print(f"  - {fallo}")
        return CODIGO_BLOQUEADO

    perfil = arnes.perfil_aprobado(RAIZ_REPOSITORIO)
    registro = cc.RegistroCondiciones()

    corpus = fc.cargar_corpus_congelado(RAIZ_REPOSITORIO)
    consultas = fc.derivar_consultas(corpus)

    directorio = Path(tempfile.mkdtemp(prefix="adr002_t0_repeticion_"))
    base_referencia = directorio / "referencia.db"
    try:
        conteos = fc.construir_base_de_referencia(corpus, base_referencia)
        fallos_previos = fc.fallos_de_conteos(corpus, conteos)
        fallos_previos.extend(fc.fallos_de_consultas(base_referencia, consultas))
        if fallos_previos:
            print("la base de referencia NO es fiel al corpus congelado:")
            for fallo in fallos_previos:
                print(f"  - {fallo}")
            return CODIGO_BLOQUEADO

        print(f"consultas derivadas: {consultas.por_escenario()}")
        print(f"conteos esperados: {dict(consultas.esperados)}")

        # Asentamiento PREVIO: si no se alcanza, la corrida no se inicia y la
        # repeticion NO se consume, porque nada se ha medido.
        previa = cc.esperar_asentamiento(
            "previa a la corrida", plazo_s=cc.PLAZO_ASENTAMIENTO_PREVIO_S
        )
        registro.esperas.append(previa)
        if not previa.alcanzado:
            print(
                f"asentamiento previo no alcanzado (carga {previa.serie[-1]} > "
                f"{previa.umbral} tras {previa.duracion_s} s): la corrida NO se "
                f"inicia y la repeticion NO queda consumida."
            )
            return CODIGO_BLOQUEADO

        registro.boot_id_inicio = cc.boot_id_actual()
        print(
            f"condiciones controladas: carga {previa.serie[-1]} <= {previa.umbral}; "
            f"boot {registro.boot_id_inicio}; corrida unica del §6.8..."
        )

        # ------- Desde aqui la repeticion queda CONSUMIDA. Una corrida. -------
        resultados = ejecutor_sesiones_controladas(
            base_referencia, consultas.por_escenario(), registro
        )
    finally:
        shutil.rmtree(directorio, ignore_errors=True)

    registro.boot_id_final = cc.boot_id_actual()
    if not registro.arranque_estable:
        print(
            f"el arranque cambio durante la corrida ({registro.boot_id_inicio} -> "
            f"{registro.boot_id_final}): repeticion consumida e invalida. "
            f"Conforme al §6.9, rendimiento NO_EVALUABLE; no se escribe artefacto."
        )
        return CODIGO_NO_EVALUABLE

    invalida = arnes.fallos_de_corrida(resultados, esperados=consultas.esperados)
    if invalida:
        print("la corrida de la repeticion es invalida; conforme al §6.9 no hay otra:")
        for fallo in invalida:
            print(f"  - {fallo}")
        print("rendimiento NO_EVALUABLE. No se escribe artefacto ni cifra alguna.")
        return CODIGO_NO_EVALUABLE

    magnitudes = arnes.magnitudes_rederivadas(resultados, perfil=perfil)

    fallos_base = rp.fallos_de_linea_base(deps.entorno_custodia)
    fallos_evidencia = cc.fallos_de_evidencia_v01(deps.entorno_custodia)
    controles = {
        "autorizacion_expresa_presente": not rp.fallos_de_autorizacion(deps.entorno_custodia)
        and not cc.fallos_de_acta_de_repeticion(deps.entorno_custodia),
        "actas_de_puerta_presentes": not rp.fallos_de_puertas(deps.entorno_custodia),
        "corpus_congelado_intacto": not rp.fallos_de_corpus(deps.entorno_custodia),
        "linea_base_historica_intacta": not fallos_base,
        "ficha_de_t0_congelada_y_anterior": arnes.ficha_de_t0(deps.fichas_congeladas) is not None
        and not arnes.fallos_adicionales(
            deps.entorno_custodia,
            fichas=deps.fichas_congeladas,
            head=head,
            arbol_limpio=True,
            salida_existe=False,
            muestras_existen=False,
            es_ancestro=entorno.es_ancestro,
        ),
        "once_sesiones_completas": len(resultados) == rp.SESIONES_EXIGIDAS,
        "repeticiones_suficientes": all(
            len(r["magnitudes"][m]["muestras_ns"]) == rp.REPETICIONES
            for r in resultados
            for m in rp.magnitudes_previstas()
        ),
        "percentiles_por_rango_mas_cercano": all(
            r["magnitudes"][m]["p50_ns"] == arnes.pp.p50_ns(r["magnitudes"][m]["muestras_ns"])
            and r["magnitudes"][m]["p95_ns"] == arnes.pp.p95_ns(r["magnitudes"][m]["muestras_ns"])
            for r in resultados
            for m in rp.magnitudes_previstas()
        ),
        "escenarios_y_capas_identicos_a_la_linea_base": [m["magnitud"] for m in magnitudes]
        == list(rp.magnitudes_previstas()),
        "veredictos_delegados_al_perfil_aprobado": all(
            m["resultado"]
            == rp.evaluar_magnitud_rederivada(
                list(m["p50_por_sesion_ns"]), list(m["p95_por_sesion_ns"]), perfil=perfil
            ).resultado
            for m in magnitudes
        ),
        "sin_sustituir_la_linea_base_historica": not fallos_base and not fallos_evidencia,
    }
    evaluacion = rp.evaluar_controles(controles)
    if not evaluacion.valido:
        print("controles bloqueantes fallidos tras la corrida unica (§6.9):")
        for fallo in evaluacion.fallos:
            print(f"  - {fallo}")
        print("rendimiento NO_EVALUABLE. No se escribe artefacto.")
        return CODIGO_NO_EVALUABLE

    documento = documento_v02(magnitudes, controles)
    invalido = esquema.fallos_rederivacion(documento, perfil=perfil)
    if invalido:
        print("el documento NO valida contra el esquema congelado: no se escribe.")
        for fallo in invalido:
            print(f"  - {fallo}")
        return CODIGO_NO_EVALUABLE

    muestras = muestras_v02(
        head=head,
        consultas=consultas,
        conteos=conteos,
        resultados=resultados,
        magnitudes=magnitudes,
        registro=registro,
    )

    escribir_json_atomico(salida, documento)
    escribir_json_atomico(salida_muestras, muestras)

    releido = json.loads(salida.read_text(encoding="utf-8"))
    revalidacion = esquema.fallos_rederivacion(releido, perfil=perfil)
    if revalidacion:  # pragma: no cover - la escritura atomica lo impide
        print("la relectura NO valida: evidencia corrupta en disco.")
        for fallo in revalidacion:
            print(f"  - {fallo}")
        return CODIGO_BLOQUEADO

    fallos_finales = cc.fallos_de_evidencia_v01(deps.entorno_custodia)
    if fallos_finales:  # pragma: no cover - nada de esta corrida la escribe
        print("la evidencia v0.1 no esta intacta tras la corrida:")
        for fallo in fallos_finales:
            print(f"  - {fallo}")
        return CODIGO_BLOQUEADO

    print(f"artefacto v0.2 escrito y revalidado: {salida}")
    print(f"muestras crudas v0.2 escritas: {salida_muestras}")
    for magnitud in magnitudes:
        final = cc.estado_final_6_9(str(magnitud["resultado"]))
        print(
            f"  {magnitud['magnitud']}: veredicto {magnitud['resultado']} -> "
            f"estado final §6.9: {final}"
        )
    print("La repeticion unica del §6.8 queda CONSUMIDA. No existe tercera corrida.")
    print("Esta ejecucion NO aprueba ADR002-TOL-208: la aprobacion es un acto del usuario.")
    return CODIGO_OK


def construir_parser() -> argparse.ArgumentParser:
    """Parser sin efectos secundarios y SIN puerta alguna a otra corrida."""
    parser = argparse.ArgumentParser(
        prog="execute_repetition",
        description=(
            "Ejecuta la repeticion unica controlada del §6.8 para ADR002-TOL-208. "
            "Exactamente una corrida; se bloquea sin su acta de autorizacion."
        ),
    )
    parser.add_argument("--execute", action="store_true", help="ejecuta la corrida unica")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada. Sin ``--execute`` no mide ni escribe nada."""
    args = construir_parser().parse_args(argv)
    if not args.execute:
        print("execute_repetition no ejecuta nada sin --execute.")
        return CODIGO_SIN_EXECUTE
    return ejecutar(RAIZ_REPOSITORIO / SALIDA_V02, RAIZ_REPOSITORIO / SALIDA_MUESTRAS_V02)


if __name__ == "__main__":
    raise SystemExit(main())
