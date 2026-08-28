"""Ejecucion REAL de T0 y rederivacion de la linea base (TOL-208, pasos 2 y 3).

Este modulo es el arnes de medicion que el paquete 10 dejo preinscrito y que
el acta ``SIRIUS_0.2_ADR_002_TOL_208_AUTORIZACION_T0_v1.0.md`` autoriza a
ejecutar. **Sin esa acta en el repositorio, este recorrido se bloquea igual
que el de ``run_rederivation``**: la guarda es la misma, comprobada contra el
repositorio, y ninguna bandera la salta.

    uv run python -m experiments.adr002.rederivation.execute_rederivation --execute

Garantias:

- **No mide nada al importarse** y no mide nada sin ``--execute``.
- Antes de abrir una sola ventana cronometrada comprueba, fallando cerrado:
  las cinco precondiciones del paquete 10 —autorizacion, actas de puerta,
  corpus congelado por blob, linea base historica intacta, ficha de T0
  congelada—, y ademas: arbol limpio, ficha de T0 con commit de entrada
  **ancestro estricto** de ``HEAD``, perfil aprobado y su fuente intactos por
  blob, y salidas inexistentes.
- El plan es EXACTAMENTE el preinscrito: tres escenarios por dos capas, seis
  magnitudes, **once** sesiones independientes (procesos del sistema
  operativo), **cien** repeticiones por magnitud, percentiles por rango mas
  cercano, veredictos delegados en el perfil aprobado de TOL-209.
- El instrumento es el congelado: ``floor_scale_probes.medir_ns``, el mismo
  cronometro de los paquetes 06 y 07, sin tocar.
- Si la corrida resulta invalida por sus controles funcionales, se aplica la
  **repeticion unica** del §6.8 del protocolo; si vuelve a fallar, rige el
  §6.9: **NO_EVALUABLE**, sin artefacto y sin cifras inventadas.
- El artefacto se valida con el esquema congelado ANTES de escribirse, se
  escribe de forma atomica sin sobrescribir nada, y se relee y revalida.
- La linea base historica no se toca. Este recorrido no la abre siquiera.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from experiments.adr002.cards import card_protocol as cp
from experiments.adr002.rederivation import frozen_corpus as fc
from experiments.adr002.rederivation import rederivation_protocol as rp
from experiments.adr002.rederivation import run_rederivation as recorrido
from experiments.adr002.rederivation import schema_rederivation_v0_1 as esquema
from experiments.adr002.tolerances import derive_profile as dp
from experiments.adr002.tolerances import floor_scale_probes as sondas
from experiments.adr002.tolerances import profile_protocol as pp
from experiments.adr002.tolerances.run_envelope import (
    entorno_custodia_real,
    escribir_json_atomico,
)

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

CODIGO_OK: Final = 0
CODIGO_BLOQUEADO: Final = 2
CODIGO_SIN_EXECUTE: Final = 3
CODIGO_NO_EVALUABLE: Final = 4

SALIDA: Final = recorrido.SALIDA_PREVISTA
SALIDA_MUESTRAS: Final = "artifacts/adr002_tolerances/rederivacion_t0_v0.1_muestras.json"

#: Perfil aprobado por el acta de TOL-209 y su fuente, citados POR BLOB.
RUTA_PERFIL: Final = "artifacts/adr002_tolerances/perfil_tolerancias_v0.1.json"
BLOB_PERFIL: Final = "41003495620aaf9cd37404b45bf359410c4e7504"
RUTA_SUELO: Final = "artifacts/adr002_tolerances/suelo_medicion_v0.3.json"
BLOB_SUELO: Final = "7273264879ec0d45861160066555c1f08b5882bc"

#: Warm-up por magnitud y sesion, descartado integro. El mismo de la linea
#: base historica (``measurements.WARMUP``), citado literal para no importar
#: un modulo que abre cronometros al cargarse.
WARMUP: Final = 5

#: Repeticion unica del §6.8 del protocolo: una, y ninguna mas (§6.9, §8.8).
REPETICIONES_DE_CORRIDA_MAXIMAS: Final = 2


class EjecucionBloqueadaError(RuntimeError):
    """Una precondicion de custodia o un control funcional no se cumple."""


# --------------------------------------------------------------------------
# Precondiciones adicionales a las del paquete 10
# --------------------------------------------------------------------------


def _cargar_json(raiz: Path, ruta: str) -> Mapping[str, Any]:
    datos = json.loads((raiz / ruta).read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        msg = f"{ruta} no contiene un objeto JSON"
        raise EjecucionBloqueadaError(msg)
    return datos


def ficha_de_t0(fichas: Sequence[cp.FichaConfirmada]) -> cp.FichaConfirmada | None:
    """La unica ficha CONGELADA de T0-control, si existe."""
    vigentes = [
        f for f in fichas if f.candidato == rp.CANDIDATO and f.estado == cp.ESTADO_CONGELADA
    ]
    return vigentes[0] if len(vigentes) == 1 else None


def fallos_adicionales(
    entorno: pp.EntornoCustodia,
    *,
    fichas: Sequence[cp.FichaConfirmada],
    head: str,
    arbol_limpio: bool,
    salida_existe: bool,
    muestras_existen: bool,
    es_ancestro: Any,
) -> list[str]:
    """Lo que el paquete 10 no podia comprobar aun: la ejecucion concreta."""
    fallos: list[str] = []
    if not arbol_limpio:
        fallos.append("el arbol de trabajo no esta limpio: la ejecucion debe partir de un commit")
    if salida_existe:
        fallos.append(f"la salida ya existe y no se sobrescribe: {SALIDA}")
    if muestras_existen:
        fallos.append(f"la salida de muestras ya existe y no se sobrescribe: {SALIDA_MUESTRAS}")

    for ruta, esperado in ((RUTA_PERFIL, BLOB_PERFIL), (RUTA_SUELO, BLOB_SUELO)):
        try:
            observado = rp.blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"artefacto aprobado ilegible: {ruta}")
            continue
        if observado != esperado:
            fallos.append(f"artefacto aprobado alterado: {ruta} ({observado} != {esperado})")

    ficha = ficha_de_t0(fichas)
    if ficha is None:
        fallos.append(f"{rp.CANDIDATO} no tiene exactamente una ficha CONGELADA")
    else:
        if not es_ancestro(ficha.commit_de_entrada, head):
            fallos.append(
                f"el commit de entrada de la ficha ({ficha.commit_de_entrada}) no es "
                f"ancestro de HEAD ({head})"
            )
        if ficha.commit_de_entrada == head:
            fallos.append(
                "la ficha entra en el MISMO commit que ejecuta: la anterioridad exige "
                "ancestro ESTRICTO (TOL-210 §1.3)"
            )
    return fallos


def perfil_aprobado(raiz: Path) -> pp.Perfil:
    """Reconstruye el perfil desde los vectores crudos de la fuente aprobada.

    No acepta los percentiles publicados: recomputa, igual que hizo la
    derivacion del paquete 08. Despues contrasta ``SM``, ``U50`` y
    ``B50(U50)`` contra el artefacto aprobado por el acta de TOL-209; una
    discrepancia bloquea, porque significaria que el perfil aprobado no es
    derivable de su propia fuente.
    """
    fuente = _cargar_json(raiz, RUTA_SUELO)
    observaciones, unitarias = dp.observaciones_desde_fuente(fuente)
    perfil = pp.derivar_perfil(observaciones, unitarias)

    aprobado = _cargar_json(raiz, RUTA_PERFIL)
    p50 = aprobado.get("p50")
    esperados = {
        "sm_ns": aprobado.get("sm_ns"),
        "u50_ns": p50.get("u50_ns") if isinstance(p50, Mapping) else None,
        "b50_en_u50_ns": p50.get("b50_en_u50_ns") if isinstance(p50, Mapping) else None,
    }
    derivados = {
        "sm_ns": perfil.sm_ns,
        "u50_ns": perfil.u50_ns,
        "b50_en_u50_ns": perfil.b50_en_u50_ns,
    }
    if esperados != derivados:
        msg = f"el perfil derivado {derivados} no coincide con el aprobado {esperados}"
        raise EjecucionBloqueadaError(msg)
    return perfil


# --------------------------------------------------------------------------
# Worker: UNA sesion independiente en su propio proceso
# --------------------------------------------------------------------------


def _carga_actual() -> float:
    return os.getloadavg()[0]


def medir_sesion(base_referencia: Path, consultas: Mapping[str, str]) -> dict[str, Any]:
    """Una sesion completa: fichero, motor, cache y warm-up propios.

    Mide las seis magnitudes en el orden preinscrito —escenario por capa—,
    con ``REPETICIONES`` repeticiones cronometradas por magnitud tras un
    warm-up descartado integro. Los conteos funcionales de cada escenario se
    observan FUERA del cronometro y viajan con la sesion para el control.
    """
    from sirius.adapters.persistence.sqlite_decision_repository import (
        build_sqlite_decision_repository,
    )
    from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
        build_sqlite_knowledge_search_repository,
    )
    from sirius.adapters.persistence.sqlite_memory_repository import (
        build_sqlite_memory_repository,
    )
    from sirius.adapters.persistence.sqlite_project_repository import (
        build_sqlite_project_repository,
    )
    from sirius.application.rank_relevant_knowledge import RankRelevantKnowledgeUseCase

    carga_inicial = _carga_actual()
    directorio = Path(tempfile.mkdtemp(prefix="adr002_rederivacion_"))
    copia = directorio / "sesion.db"
    shutil.copy2(base_referencia, copia)

    busqueda = build_sqlite_knowledge_search_repository(copia)
    caso_de_uso = RankRelevantKnowledgeUseCase(
        memory_repository=build_sqlite_memory_repository(copia),
        decision_repository=build_sqlite_decision_repository(copia),
        project_repository=build_sqlite_project_repository(copia),
        knowledge_search_repository=busqueda,
    )
    try:
        conteos = {
            escenario: len(busqueda.search_knowledge(consulta))
            for escenario, consulta in consultas.items()
        }
        magnitudes: dict[str, dict[str, Any]] = {}
        for escenario in rp.ESCENARIOS:
            consulta = consultas[escenario]
            operaciones = {
                "solo_indice_fts5": lambda c=consulta: busqueda.search_knowledge(c),
                "recuperacion_completa_rank": lambda c=consulta: caso_de_uso.rank(c),
            }
            for capa in rp.CAPAS:
                muestras = sondas.medir_ns(operaciones[capa], n=rp.REPETICIONES, warmup=WARMUP)
                magnitudes[f"{escenario}.{capa}"] = {
                    "muestras_ns": muestras,
                    "p50_ns": pp.p50_ns(muestras),
                    "p95_ns": pp.p95_ns(muestras),
                }
    finally:
        busqueda.close()
        shutil.rmtree(directorio, ignore_errors=True)

    return {
        "pid": sondas.pid_actual(),
        "warmup_descartado": WARMUP,
        "repeticiones": rp.REPETICIONES,
        "conteos": conteos,
        "magnitudes": magnitudes,
        "carga_inicial": carga_inicial,
        "carga_final": _carga_actual(),
    }


def ejecutor_sesiones_reales(
    base_referencia: Path, consultas: Mapping[str, str]
) -> list[Mapping[str, Any]]:
    """Exactamente once procesos del sistema operativo, secuenciales."""
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
    for _ in range(rp.SESIONES_EXIGIDAS):
        completado = subprocess.run(
            orden,
            cwd=str(RAIZ_REPOSITORIO),
            capture_output=True,
            text=True,
            check=False,
        )
        if completado.returncode != 0:
            msg = f"sesion fallida (rc={completado.returncode}): {completado.stderr.strip()[:500]}"
            raise EjecucionBloqueadaError(msg)
        resultados.append(json.loads(completado.stdout))
    return resultados


# --------------------------------------------------------------------------
# Validez de la corrida: controles funcionales, ANTES de publicar nada
# --------------------------------------------------------------------------


def fallos_de_corrida(
    resultados: Sequence[Mapping[str, Any]],
    *,
    esperados: Mapping[str, int],
) -> list[str]:
    """Controles funcionales de la corrida completa. Fallan cerrado."""
    fallos: list[str] = []
    if len(resultados) != rp.SESIONES_EXIGIDAS:
        fallos.append(f"{len(resultados)} sesiones; se exigen {rp.SESIONES_EXIGIDAS}")

    pids = [r.get("pid") for r in resultados]
    if len(set(pids)) != len(pids) or not all(
        isinstance(p, int) and not isinstance(p, bool) and p > 0 for p in pids
    ):
        fallos.append("las sesiones no corrieron en procesos distintos")

    nombres = list(rp.magnitudes_previstas())
    for indice, resultado in enumerate(resultados):
        etiqueta = f"sesion[{indice}]"
        if resultado.get("warmup_descartado") != WARMUP:
            fallos.append(f"{etiqueta}: warm-up distinto del preinscrito")
        if resultado.get("repeticiones") != rp.REPETICIONES:
            fallos.append(f"{etiqueta}: repeticiones distintas de las preinscritas")
        if resultado.get("conteos") != dict(esperados):
            fallos.append(
                f"{etiqueta}: conteos funcionales {resultado.get('conteos')} distintos de "
                f"los del corpus congelado {dict(esperados)}"
            )
        magnitudes = resultado.get("magnitudes")
        if not isinstance(magnitudes, Mapping) or sorted(magnitudes) != sorted(nombres):
            fallos.append(f"{etiqueta}: no cubre exactamente las seis magnitudes")
            continue
        for nombre in nombres:
            entrada = magnitudes[nombre]
            muestras = entrada.get("muestras_ns")
            if (
                not isinstance(muestras, Sequence)
                or len(muestras) != rp.REPETICIONES
                or not all(
                    isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in muestras
                )
            ):
                fallos.append(f"{etiqueta}.{nombre}: vector crudo invalido")
                continue
            if entrada.get("p50_ns") != pp.p50_ns(muestras):
                fallos.append(f"{etiqueta}.{nombre}: P50 publicado no recomputa")
            if entrada.get("p95_ns") != pp.p95_ns(muestras):
                fallos.append(f"{etiqueta}.{nombre}: P95 publicado no recomputa")
    return fallos


# --------------------------------------------------------------------------
# Agregacion y documento
# --------------------------------------------------------------------------


def magnitudes_rederivadas(
    resultados: Sequence[Mapping[str, Any]], *, perfil: pp.Perfil
) -> list[dict[str, Any]]:
    """Las seis magnitudes del esquema, con el veredicto delegado al perfil."""
    salida: list[dict[str, Any]] = []
    for nombre in rp.magnitudes_previstas():
        p50s = [pp.p50_ns(r["magnitudes"][nombre]["muestras_ns"]) for r in resultados]
        p95s = [pp.p95_ns(r["magnitudes"][nombre]["muestras_ns"]) for r in resultados]
        veredicto = rp.evaluar_magnitud_rederivada(p50s, p95s, perfil=perfil)
        salida.append(
            {
                "magnitud": nombre,
                "p50_por_sesion_ns": p50s,
                "p95_por_sesion_ns": p95s,
                "min_p50_ns": min(p50s),
                "max_p50_ns": max(p50s),
                "min_p95_ns": min(p95s),
                "max_p95_ns": max(p95s),
                "resultado": veredicto.resultado,
                "motivo": veredicto.motivo,
                "registro": pp.registro_por_percentil(veredicto),
            }
        )
    return salida


def construir_documento(
    *,
    magnitudes: Sequence[Mapping[str, Any]],
    controles: Mapping[str, bool],
) -> dict[str, Any]:
    """El artefacto EXACTO que el esquema congelado exige. Nada mas."""
    return {
        "documento": (
            "Rederivacion de la linea base sobre el corpus congelado v0.4 "
            "(ADR002-TOL-208, pasos 2 y 3)"
        ),
        "version_esquema": rp.VERSION_ESQUEMA,
        "estado": "EVIDENCIA",
        "paquete": rp.PAQUETE,
        "protocolo": rp.PROTOCOLO,
        "registro": rp.REGISTRO,
        "candidato": rp.CANDIDATO,
        "head_de_esquema": rp.HEAD_T0,
        "corpus": {"acta": rp.ACTA_CORPUS, "blobs": dict(rp.CORPUS_CONGELADO)},
        "plan": {
            "sesiones": rp.SESIONES_EXIGIDAS,
            "repeticiones": rp.REPETICIONES,
            "escenarios": list(rp.ESCENARIOS),
            "capas": list(rp.CAPAS),
        },
        "linea_base_historica": {
            "ruta": rp.LINEA_BASE_HISTORICA,
            "blob": rp.BLOB_LINEA_BASE,
            "sesiones": rp.SESIONES_LINEA_BASE_HISTORICA,
            "nota": (
                "medida con cinco sesiones sobre el corpus 5000/500; la regla 3.3.b del "
                "protocolo la declara NO_COMPARABLE frente a las bandas de once sesiones, "
                "y por eso el paso 3 ordena rederivar sobre el corpus definitivo. Se "
                "conserva congelada con su head y sus ficheros"
            ),
            "sustituida": False,
        },
        "magnitudes": [dict(m) for m in magnitudes],
        "controles_internos": dict(controles),
        "no_autoriza": dict.fromkeys(esquema.NEGACIONES, False),
    }


def documento_de_muestras(
    *,
    head: str,
    consultas: fc.ConsultasDeControl,
    conteos: fc.ConteosCargados,
    resultados: Sequence[Mapping[str, Any]],
    repeticion_unica_ejercitada: bool,
    boot_id: str | None,
) -> dict[str, Any]:
    """Evidencia cruda acompanante: todo lo necesario para recomputar.

    El artefacto normativo tiene sus conjuntos de campos cerrados por el
    esquema congelado y no puede alojar los vectores crudos; este documento
    los publica aparte, con la sesion, el pid y la carga de cada uno, para
    que P50 y P95 por sesion sean recomputables desde las cien repeticiones.
    """
    return {
        "documento": "Muestras crudas de la rederivacion de T0 (ADR002-TOL-208, paso 2)",
        "artefacto_normativo": SALIDA,
        "head_en_ejecucion": head,
        "boot_id": boot_id,
        "consultas_derivadas": {
            "regla": (
                "derivadas del corpus congelado por frozen_corpus.derivar_consultas: "
                "tokens ASCII por presencia por item; unico = primer token alfabetico "
                "con presencia 1; frecuente = mayor presencia con desempate alfabetico; "
                "cero = token de la linea base verificado ausente"
            ),
            "por_escenario": consultas.por_escenario(),
            "conteos_esperados": dict(consultas.esperados),
        },
        "carga_del_corpus": {
            "proyectos": conteos.proyectos,
            "mensajes": conteos.mensajes,
            "memorias": conteos.memorias,
            "memorias_vigentes": conteos.memorias_vigentes,
            "decisiones": conteos.decisiones,
            "filas_knowledge_fts": conteos.filas_fts,
            "no_cargados_por_esquema_de_t0": dict(conteos.no_cargados),
            "nota": (
                "entidades, documentos y relaciones del corpus no tienen tabla en el "
                "esquema de T0 (head 61be4bb269bf): T0 no materializa relaciones, y esa "
                "carencia es parte de lo que el control es"
            ),
        },
        "repeticion_unica_6_8_ejercitada": repeticion_unica_ejercitada,
        "warmup_descartado": WARMUP,
        "repeticiones": rp.REPETICIONES,
        "sesiones": [
            {
                "sesion": indice + 1,
                "pid": resultado["pid"],
                "carga_inicial": resultado["carga_inicial"],
                "carga_final": resultado["carga_final"],
                "conteos_observados": dict(resultado["conteos"]),
                "magnitudes": {
                    nombre: {
                        "muestras_ns": list(entrada["muestras_ns"]),
                        "p50_ns": entrada["p50_ns"],
                        "p95_ns": entrada["p95_ns"],
                    }
                    for nombre, entrada in resultado["magnitudes"].items()
                },
            }
            for indice, resultado in enumerate(resultados)
        ],
    }


def _boot_id() -> str | None:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return None


# --------------------------------------------------------------------------
# Recorrido completo
# --------------------------------------------------------------------------


def ejecutar(salida: Path, salida_muestras: Path) -> int:
    """La corrida real completa. Solo llega a medir si TODO lo previo pasa."""
    entorno = entorno_custodia_real()
    deps = recorrido.dependencias_reales()

    precondiciones = rp.comprobar_precondiciones(
        deps.entorno_custodia, fichas_congeladas=deps.fichas_congeladas
    )
    head = entorno.head()
    fallos = list(precondiciones.fallos)
    fallos.extend(
        fallos_adicionales(
            deps.entorno_custodia,
            fichas=deps.fichas_congeladas,
            head=head,
            arbol_limpio=entorno.arbol_limpio(),
            salida_existe=salida.exists(),
            muestras_existen=salida_muestras.exists(),
            es_ancestro=entorno.es_ancestro,
        )
    )
    if fallos:
        print("la rederivacion de T0 NO puede ejecutarse. Falta:")
        for fallo in fallos:
            print(f"  - {fallo}")
        return CODIGO_BLOQUEADO

    perfil = perfil_aprobado(RAIZ_REPOSITORIO)
    boot_id = _boot_id()

    corpus = fc.cargar_corpus_congelado(RAIZ_REPOSITORIO)
    consultas = fc.derivar_consultas(corpus)

    directorio = Path(tempfile.mkdtemp(prefix="adr002_t0_referencia_"))
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

        repeticion_unica = False
        resultados: list[Mapping[str, Any]] = []
        for intento in range(REPETICIONES_DE_CORRIDA_MAXIMAS):
            print(f"corrida {intento + 1}: once sesiones independientes...")
            resultados = ejecutor_sesiones_reales(base_referencia, consultas.por_escenario())
            invalida = fallos_de_corrida(resultados, esperados=consultas.esperados)
            if not invalida:
                break
            for fallo in invalida:
                print(f"  - {fallo}")
            if intento == 0:
                repeticion_unica = True
                print("corrida invalida: se ejercita la repeticion unica del §6.8.")
            else:
                print("la repeticion unica tambien es invalida: rige el §6.9.")
                print("resultado: NO_EVALUABLE. No se escribe artefacto ni cifra alguna.")
                return CODIGO_NO_EVALUABLE
    finally:
        shutil.rmtree(directorio, ignore_errors=True)

    if boot_id is not None and boot_id != _boot_id():
        print("la maquina se reinicio durante la corrida: NO_EVALUABLE, sin artefacto.")
        return CODIGO_NO_EVALUABLE

    magnitudes = magnitudes_rederivadas(resultados, perfil=perfil)

    # Los once controles preinscritos, derivados del estado observado.
    fallos_base = rp.fallos_de_linea_base(deps.entorno_custodia)
    controles = {
        "autorizacion_expresa_presente": not rp.fallos_de_autorizacion(deps.entorno_custodia),
        "actas_de_puerta_presentes": not rp.fallos_de_puertas(deps.entorno_custodia),
        "corpus_congelado_intacto": not rp.fallos_de_corpus(deps.entorno_custodia),
        "linea_base_historica_intacta": not fallos_base,
        "ficha_de_t0_congelada_y_anterior": ficha_de_t0(deps.fichas_congeladas) is not None
        and not fallos_adicionales(
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
            r["magnitudes"][m]["p50_ns"] == pp.p50_ns(r["magnitudes"][m]["muestras_ns"])
            and r["magnitudes"][m]["p95_ns"] == pp.p95_ns(r["magnitudes"][m]["muestras_ns"])
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
        "sin_sustituir_la_linea_base_historica": not fallos_base,
    }
    evaluacion = rp.evaluar_controles(controles)
    if not evaluacion.valido:
        print("controles bloqueantes fallidos: no se escribe artefacto.")
        for fallo in evaluacion.fallos:
            print(f"  - {fallo}")
        return CODIGO_BLOQUEADO

    documento = construir_documento(magnitudes=magnitudes, controles=controles)
    invalido = esquema.fallos_rederivacion(documento, perfil=perfil)
    if invalido:
        print("el documento NO valida contra el esquema congelado: no se escribe.")
        for fallo in invalido:
            print(f"  - {fallo}")
        return CODIGO_BLOQUEADO

    muestras = documento_de_muestras(
        head=head,
        consultas=consultas,
        conteos=conteos,
        resultados=resultados,
        repeticion_unica_ejercitada=repeticion_unica,
        boot_id=boot_id,
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

    print(f"artefacto escrito y revalidado: {salida}")
    print(f"muestras crudas escritas: {salida_muestras}")
    for magnitud in magnitudes:
        print(
            f"  {magnitud['magnitud']}: {magnitud['resultado']} "
            f"(P50 {magnitud['min_p50_ns']}-{magnitud['max_p50_ns']} ns, "
            f"P95 {magnitud['min_p95_ns']}-{magnitud['max_p95_ns']} ns)"
        )
    print("Esta ejecucion NO aprueba ADR002-TOL-208: la aprobacion es un acto del usuario.")
    return CODIGO_OK


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def construir_parser() -> argparse.ArgumentParser:
    """Parser sin efectos secundarios. La guarda sigue siendo el acta."""
    parser = argparse.ArgumentParser(
        prog="execute_rederivation",
        description=(
            "Ejecuta T0 sobre el corpus congelado v0.4 y rederiva la linea base "
            "(pasos 2 y 3 de ADR002-TOL-208). Se bloquea sin el acta de autorizacion."
        ),
    )
    parser.add_argument("--execute", action="store_true", help="ejecuta la corrida real")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--db", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--queries", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--output", type=str, default=SALIDA, help="ruta del artefacto")
    parser.add_argument(
        "--samples-output", type=str, default=SALIDA_MUESTRAS, help="ruta de las muestras crudas"
    )
    return parser


@dataclass(frozen=True, slots=True)
class Argumentos:
    """Argumentos ya validados del punto de entrada."""

    execute: bool
    worker: bool
    db: str | None
    queries: str | None
    output: str
    samples_output: str


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada. Sin ``--execute`` no mide ni escribe nada."""
    espacio = construir_parser().parse_args(argv)
    args = Argumentos(
        execute=bool(espacio.execute),
        worker=bool(espacio.worker),
        db=espacio.db,
        queries=espacio.queries,
        output=str(espacio.output),
        samples_output=str(espacio.samples_output),
    )

    if not args.execute:
        print("execute_rederivation no ejecuta nada sin --execute.")
        return CODIGO_SIN_EXECUTE

    if args.worker:
        if not args.db or not args.queries:
            print("un worker exige --db y --queries", file=sys.stderr)
            return CODIGO_BLOQUEADO
        consultas = json.loads(args.queries)
        if not isinstance(consultas, dict) or sorted(consultas) != sorted(rp.ESCENARIOS):
            print("las consultas del worker no cubren los escenarios", file=sys.stderr)
            return CODIGO_BLOQUEADO
        resultado = medir_sesion(Path(args.db), consultas)
        json.dump(resultado, sys.stdout, separators=(",", ":"))
        return CODIGO_OK

    return ejecutar(RAIZ_REPOSITORIO / args.output, RAIZ_REPOSITORIO / args.samples_output)


if __name__ == "__main__":
    raise SystemExit(main())
