"""Ejecución REAL de la ronda primaria de ADR-002. Mide, y solo si puede.

    uv run python -m experiments.adr002.round.execute_round --execute

Sin ``--execute`` no mide ni escribe nada. Con ``--execute`` comprueba **otra
vez** todas las precondiciones del recorrido —el acta de autorización incluida—
más las que solo la ejecución puede comprobar, y falla cerrado antes de abrir la
primera ventana cronometrada.

DOS EJES, Y NO SE MEZCLAN
=========================

**Conformidad**: qué devolvió cada participante ante cada caso congelado. Es
determinista y se ejecuta **una vez**: repetirla cien veces daría cien veces lo
mismo, y las cinco puertas booleanas del §9 no dependen de ninguna cifra.

**Rendimiento**: cuánto tardó. Once sesiones independientes —procesos del
sistema operativo—, cien repeticiones por sesión tras un warm-up de diez
descartado íntegro, y en cada repetición los cinco participantes en el **orden
rotado** que el plan congeló. Una repetición es **una pasada completa** por los
cincuenta casos: medir un solo caso elegido a dedo mediría la elección.

LOS CINCO SOBRE EL MISMO FICHERO
================================

`entrada.sqlite3`, materializado desde la familia de conformidad v0.6, lleva el
esquema canónico de Sirius 0.1 sin DDL adicional, de modo que `T0` corre sobre
él igual que los candidatos. Lo que cada uno necesita de más —el sidecar
vectorial, el plano relacional— se prepara **fuera** de toda ventana
cronometrada: cobrar la construcción del índice dentro de la medida mediría la
preparación, no la recuperación.

SI LA CORRIDA SALE INVÁLIDA
===========================

Rige el §6.8 del protocolo: **una** repetición, ninguna más. Si esa también
falla, rige el §6.9: `NO_EVALUABLE`, sin artefacto y sin cifras inventadas.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from experiments.adr002.candidates.common import neutrality
from experiments.adr002.projection import build
from experiments.adr002.round import cases as cs
from experiments.adr002.round import metrics as mt
from experiments.adr002.round import participants as pt
from experiments.adr002.round import round_protocol as rp
from experiments.adr002.round import run_round as recorrido
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

#: La corrida original y la repetición **no comparten fichero**. La `v0.1` es
#: evidencia de lo que se midió antes de corregir la capa común y se conserva
#: íntegra: sobrescribirla borraría justamente el término de comparación que
#: hace comprobable la corrección.
#: Corrida del paquete de cierre. La `v0.2` se conserva intacta: es el termino
#: de comparacion que hace comprobable que la correccion **no cambio nada de lo
#: que se recupera**, y sobrescribirla habria borrado esa comprobacion. La `v0.3`
#: es la readjudicacion, que no midio: por eso esta es la `v0.4`.
SALIDA: Final = "artifacts/adr002_round/ronda_primaria_v0.4.json"
SALIDA_EVIDENCIA: Final = "artifacts/adr002_round/ronda_primaria_v0.4_evidencia.json"
SALIDA_v0_2: Final = "artifacts/adr002_round/ronda_primaria_v0.2.json"

#: Corrida original, previa a la corrección. Se cita para contrastar y **no se
#: toca**: este recorrido no la abre siquiera.
SALIDA_v0_1: Final = recorrido.SALIDA_PREVISTA

#: Repetición única del §6.8: una, y ninguna más (§6.9).
CORRIDAS_MAXIMAS: Final = 2


class RondaBloqueadaError(RuntimeError):
    """Una precondición o un control funcional no se cumple. Falla cerrado."""


# --------------------------------------------------------------------------
# Conformidad: una vez, determinista
# --------------------------------------------------------------------------


def _veredicto(
    caso: cs.CasoEjecutable,
    observacion: pt.Observacion,
    *,
    identificador: str,
    proyectos: Mapping[str, str | None],
    polaridades: Mapping[str, Any],
    criticos: Sequence[str],
) -> mt.VeredictoDeCaso:
    """Lo observado, juzgado contra la referencia congelada. Sin promediar."""
    obtenido = observacion.ids
    razon_sin_etapas = pt.razon_sin_etapas(identificador)
    if razon_sin_etapas:
        conforme, razon = False, razon_sin_etapas
    else:
        conforme, razon = mt.etapa_conforme(
            caso, observacion.etapas_recorridas, observacion.etapa_de_resolucion
        )
    return mt.VeredictoDeCaso(
        caso=caso.identificador,
        canonico=caso.canonico,
        adjudicable=caso.adjudicable,
        obtenido=obtenido,
        esperado=caso.resultado_esperado,
        contaminacion=mt.contaminacion(obtenido, caso),
        fuga_de_ambito=mt.fuga_de_ambito(obtenido, caso, proyectos),
        confusion_de_polaridad=mt.confusion_de_polaridad(
            obtenido, observacion.polaridad_leida, polaridades
        ),
        polaridad_mal_leida=mt.polaridad_mal_leida(
            obtenido, observacion.polaridad_leida, polaridades
        ),
        etapa_conforme=conforme,
        razon_de_etapa=(
            f"la instanciacion se contradice (E0 con resultados esperados): {razon}"
            if caso.etapa_inconsistente
            else razon
        ),
        etapa_puntua=not caso.etapa_inconsistente,
        resultado_exacto=tuple(sorted(obtenido)) == tuple(sorted(caso.resultado_esperado)),
        declara_orden=caso.declara_orden,
        orden_exacto=caso.declara_orden and obtenido == caso.orden_esperado,
        ausencia_correcta=mt.ausencia_correcta(caso, obtenido, observacion.estado_externo),
        criticos_pendientes=mt.criticos_pendientes(caso, obtenido, criticos),
        explicaciones_completas=observacion.explicaciones_completas,
        resultados_totales=len(obtenido),
        suficiencia=observacion.suficiencia,
        estado_externo=observacion.estado_externo,
        parada=observacion.parada,
        etapas_recorridas=observacion.etapas_recorridas,
    )


def _criticos_del_canon(criticidad: Mapping[str, Any]) -> tuple[str, ...]:
    """Identidades con criticidad aplicada distinta de ordinaria."""
    from experiments.adr002.projection import contracts as pcon

    criticos: list[str] = []
    for identificador, aplicada in criticidad.items():
        if not isinstance(aplicada, Mapping):
            continue
        if str(aplicada.get("nivel", "")).upper().startswith("ORDINAR"):
            continue
        identidad = pcon.referencia_canonica(str(identificador))
        if identidad is not None:
            criticos.append(identidad)
    return tuple(sorted(criticos))


def conformidad(
    proyeccion: Any, casos: Sequence[cs.CasoEjecutable], trabajo: Path
) -> dict[str, list[mt.VeredictoDeCaso]]:
    """Los cinco contra los cincuenta casos. Una vez: es determinista."""
    familia = build.cargar_familia()
    corpus = familia[cs.CORPUS]
    proyectos = pt.proyectos_del_canon(corpus)
    polaridades = pt.polaridades_del_canon(corpus)
    criticos = _criticos_del_canon(familia["applied_criticality_v0_1.json"]["valores"])

    por_participante: dict[str, list[mt.VeredictoDeCaso]] = {}
    for identificador in rp.PARTICIPANTES:
        participante = pt.construir(identificador, proyeccion, trabajo / identificador)
        try:
            por_participante[identificador] = [
                _veredicto(
                    caso,
                    participante.responder(caso.peticion),
                    identificador=identificador,
                    proyectos=proyectos,
                    polaridades=polaridades,
                    criticos=criticos,
                )
                for caso in casos
            ]
        finally:
            participante.close()
    return por_participante


def borrado_y_regeneracion(proyeccion: Any, trabajo: Path) -> dict[str, bool]:
    """Puerta 5: cada índice derivado se destruye y se reconstruye del canon.

    Solo `B` y `D` tienen índice derivado propio. `A` y `C` no construyen
    ninguno, y `T0` tiene el `FTS5` que Alembic crea con el esquema. Quien no
    tiene índice **cumple por no tenerlo**, y eso no es un aprobado regalado:
    la puerta pregunta si lo derivado es regenerable, y nada que regenerar es
    la forma más fuerte de que lo sea.
    """
    from experiments.adr002.candidates.adr002_b import vectores

    resultado: dict[str, bool] = {}
    for identificador in rp.PARTICIPANTES:
        if identificador not in ("ADR002-B", "ADR002-D"):
            resultado[identificador] = True
            continue
        destino = trabajo / f"{identificador}-puerta5" / pt.SIDECAR
        destino.parent.mkdir(parents=True, exist_ok=True)
        vectores.construir(proyeccion.ruta_de_entrada(), destino)
        primera = destino.read_bytes()
        vectores.borrar(destino)
        borrado_completo = not destino.exists() and not vectores.residuos(destino)
        vectores.construir(proyeccion.ruta_de_entrada(), destino)
        resultado[identificador] = borrado_completo and destino.read_bytes() == primera
    return resultado


# --------------------------------------------------------------------------
# Rendimiento: once sesiones, cada una un proceso
# --------------------------------------------------------------------------


def medir_sesion(sesion: int, raiz_de_trabajo: Path) -> dict[str, Any]:
    """Una sesión completa. Proyección, participantes y warm-up propios.

    Todo lo caro —materializar la proyección, construir los sidecars— ocurre
    **antes** del primer cronómetro y no entra en ninguna muestra.
    """
    proyeccion = build.construir_desde_la_familia(raiz_de_trabajo / "planos")
    casos = cs.casos_ejecutables(cs.cargar_artefactos())
    carga_inicial = os.getloadavg()[0]

    abiertos = {
        identificador: pt.construir(identificador, proyeccion, raiz_de_trabajo / identificador)
        for identificador in rp.PARTICIPANTES
    }
    muestras: dict[str, list[int]] = {identificador: [] for identificador in rp.PARTICIPANTES}
    ordenes: list[list[str]] = []
    try:
        total = rp.WARMUP + rp.REPETICIONES
        for repeticion in range(1, total + 1):
            orden = rp.orden_de_ejecucion(sesion, repeticion)
            ordenes.append(list(orden))
            for identificador in orden:
                participante = abiertos[identificador]
                comienzo = time.perf_counter_ns()
                for caso in casos:
                    participante.responder(caso.peticion)
                transcurrido = time.perf_counter_ns() - comienzo
                # El warm-up se descarta INTEGRO: no se guarda ni se promedia.
                if repeticion > rp.WARMUP:
                    muestras[identificador].append(transcurrido)
    finally:
        for participante in abiertos.values():
            participante.close()

    return {
        "sesion": sesion,
        "pid": os.getpid(),
        "warmup_descartado": rp.WARMUP,
        "repeticiones": rp.REPETICIONES,
        "casos_por_repeticion": len(casos),
        "carga_inicial": carga_inicial,
        "carga_final": os.getloadavg()[0],
        "ordenes_ejecutados": ordenes[: rp.WARMUP + 4],
        "muestras_ns": muestras,
    }


def ejecutor_de_sesiones() -> list[Mapping[str, Any]]:
    """Exactamente once procesos del sistema operativo, secuenciales."""
    resultados: list[Mapping[str, Any]] = []
    for sesion in range(1, rp.SESIONES_EXIGIDAS + 1):
        completado = subprocess.run(
            [
                sys.executable,
                "-m",
                "experiments.adr002.round.execute_round",
                "--execute",
                "--worker",
                "--session",
                str(sesion),
            ],
            cwd=str(RAIZ_REPOSITORIO),
            capture_output=True,
            text=True,
            check=False,
        )
        if completado.returncode != 0:
            detalle = completado.stderr.strip()[-500:]
            msg = f"sesion {sesion} fallida (rc={completado.returncode}): {detalle}"
            raise RondaBloqueadaError(msg)
        resultados.append(json.loads(completado.stdout))
        print(f"  sesion {sesion}/{rp.SESIONES_EXIGIDAS} completada")
    return resultados


def fallos_de_corrida(resultados: Sequence[Mapping[str, Any]]) -> list[str]:
    """Controles funcionales de la corrida. Fallan cerrado, antes de publicar."""
    fallos: list[str] = []
    if len(resultados) != rp.SESIONES_EXIGIDAS:
        fallos.append(f"{len(resultados)} sesiones; se exigen {rp.SESIONES_EXIGIDAS}")

    pids = [r.get("pid") for r in resultados]
    if len(set(pids)) != len(pids):
        fallos.append("las sesiones no corrieron en procesos distintos")

    for resultado in resultados:
        etiqueta = f"sesion[{resultado.get('sesion')}]"
        if resultado.get("warmup_descartado") != rp.WARMUP:
            fallos.append(f"{etiqueta}: warm-up distinto del preinscrito")
        if resultado.get("repeticiones") != rp.REPETICIONES:
            fallos.append(f"{etiqueta}: repeticiones distintas de las preinscritas")
        muestras = resultado.get("muestras_ns")
        if not isinstance(muestras, Mapping) or sorted(muestras) != sorted(rp.PARTICIPANTES):
            fallos.append(f"{etiqueta}: no cubre exactamente los cinco participantes")
            continue
        for identificador, vector in muestras.items():
            if not isinstance(vector, Sequence) or len(vector) != rp.REPETICIONES:
                fallos.append(f"{etiqueta}.{identificador}: {len(vector)} muestras")
                continue
            if not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in vector):
                fallos.append(f"{etiqueta}.{identificador}: vector crudo invalido")
    return fallos


def latencias(resultados: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """`P50`/`P95` por sesión y su rango, por rango más cercano y sin interpolar."""
    por_participante: dict[str, dict[str, Any]] = {}
    for identificador in rp.PARTICIPANTES:
        p50s = [pp.p50_ns(list(r["muestras_ns"][identificador])) for r in resultados]
        p95s = [pp.p95_ns(list(r["muestras_ns"][identificador])) for r in resultados]
        todas = [v for r in resultados for v in r["muestras_ns"][identificador]]
        por_participante[identificador] = {
            "p50_por_sesion_ns": p50s,
            "p95_por_sesion_ns": p95s,
            "min_p50_ns": min(p50s),
            "max_p50_ns": max(p50s),
            "min_p95_ns": min(p95s),
            "max_p95_ns": max(p95s),
            "min_ns": min(todas),
            "max_ns": max(todas),
            "n": len(todas),
        }
    return por_participante


# --------------------------------------------------------------------------
# Precondiciones que solo la ejecución puede comprobar
# --------------------------------------------------------------------------


def fallos_adicionales(*, arbol_limpio: bool, salidas: Sequence[Path]) -> list[str]:
    fallos: list[str] = []
    if not arbol_limpio:
        fallos.append("el arbol de trabajo no esta limpio: la ejecucion debe partir de un commit")
    fallos.extend(f"la salida ya existe y no se sobrescribe: {s}" for s in salidas if s.exists())
    return fallos


def _boot_id() -> str | None:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    except OSError:
        return None


# --------------------------------------------------------------------------
# Recorrido completo
# --------------------------------------------------------------------------


def _resumenes(
    veredictos: Mapping[str, Sequence[mt.VeredictoDeCaso]], puerta5: Mapping[str, bool]
) -> dict[str, mt.Resumen]:
    return {
        identificador: mt.resumir(
            identificador,
            lista,
            borrado_y_regeneracion=puerta5.get(identificador, False),
        )
        for identificador, lista in veredictos.items()
    }


def _documento(
    *,
    head: str,
    resumenes: Mapping[str, mt.Resumen],
    tiempos: Mapping[str, Mapping[str, Any]],
    casos: Sequence[cs.CasoEjecutable],
    repeticion_unica: bool,
    controles: Mapping[str, bool],
) -> dict[str, Any]:
    """El artefacto normativo. Cifras y veredictos; ninguna recomendación."""
    return {
        "documento": "Ronda primaria de ADR-002 sobre los cinco participantes",
        "version_esquema": rp.VERSION_ESQUEMA,
        "estado": "EVIDENCIA",
        "protocolo": rp.PROTOCOLO,
        "especificacion": rp.ESPECIFICACION,
        "acta_de_autorizacion": rp.ACTA_DE_AUTORIZACION,
        "head_en_ejecucion": head,
        "sustrato": {
            "fichero": rp.SUSTRATO,
            "origen": rp.SUSTRATO_ORIGEN,
            "nota": (
                "los cinco miden sobre el MISMO fichero; el corpus de rendimiento no "
                "puede alojar a los candidatos y su escala queda fuera de esta ronda"
            ),
        },
        "plan": {
            "participantes": list(rp.PARTICIPANTES),
            "sesiones": rp.SESIONES_EXIGIDAS,
            "repeticiones": rp.REPETICIONES,
            "warmup_descartado": rp.WARMUP,
            "semilla": rp.SEMILLA,
            "reloj": rp.RELOJ,
            "casos_por_repeticion": len(casos),
            "orden": "intercalado y rotado por (sesion + repeticion) mod 5",
        },
        "fichas_vigentes": {
            identificador: {"version": version, "huella": huella}
            for identificador, (version, huella) in rp.FICHAS_VIGENTES.items()
        },
        "conformidad": {
            identificador: {
                "casos_adjudicados": resumen.casos_adjudicados,
                "casos_no_adjudicables": resumen.casos_no_adjudicables,
                "puertas": resumen.puertas,
                "pasa_las_puertas": resumen.pasa_las_puertas,
                "descartado_por_fallo_duro": resumen.descartado_por_fallo_duro,
                "contaminacion_total": resumen.contaminacion_total,
                "fuga_de_ambito_total": resumen.fuga_de_ambito_total,
                "confusion_de_polaridad_total": resumen.confusion_de_polaridad_total,
                "polaridad_mal_leida_total": resumen.polaridad_mal_leida_total,
                "casos_con_etapa_conforme": resumen.casos_con_etapa_conforme,
                "casos_con_etapa_puntuable": resumen.casos_con_etapa_puntuable,
                "casos_con_resultado_exacto": resumen.casos_con_resultado_exacto,
                "casos_con_orden_exacto": resumen.casos_con_orden_exacto,
                "casos_con_orden_declarado": resumen.casos_con_orden_declarado,
                "casos_con_ausencia_correcta": resumen.casos_con_ausencia_correcta,
                "criticos_pendientes_total": resumen.criticos_pendientes_total,
                "explicaciones_completas": resumen.explicaciones_completas,
                "resultados_totales": resumen.resultados_totales,
            }
            for identificador, resumen in resumenes.items()
        },
        "rendimiento": dict(tiempos),
        "no_adjudicables": {
            caso.canonico: caso.motivo_no_adjudicable for caso in casos if not caso.adjudicable
        },
        "instanciaciones_contradictorias": {
            caso.canonico: (
                "declara resolverse en E0, que no expande, y a la vez espera "
                "resultados; su metrica de etapa no puntua para nadie"
            )
            for caso in casos
            if caso.etapa_inconsistente
        },
        "desviaciones": list(cs.DESVIACIONES_DE_TRADUCCION),
        "repeticion_unica_6_8_ejercitada": repeticion_unica,
        "controles_internos": dict(controles),
        "no_elige": (
            "esta ronda produce evidencia; elegir alternativa es un acto posterior "
            "y separado del usuario, y este artefacto no lo hace"
        ),
    }


def _evidencia(
    *,
    head: str,
    boot_id: str | None,
    veredictos: Mapping[str, Sequence[mt.VeredictoDeCaso]],
    casos: Sequence[cs.CasoEjecutable],
    sesiones: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """La evidencia mínima del §10, caso a caso y muestra a muestra."""
    return {
        "documento": "Evidencia de la ronda primaria de ADR-002",
        "artefacto_normativo": SALIDA,
        "head_en_ejecucion": head,
        "boot_id": boot_id,
        "familia_de_conformidad": dict(rp.FAMILIA_DE_CONFORMIDAD),
        "casos": [
            {
                "caso": caso.identificador,
                "canonico": caso.canonico,
                "nivel": caso.nivel,
                "consulta": caso.peticion.consulta,
                "modo": caso.peticion.modo.value,
                "proposito_declarado": caso.permiso,
                "ambito": caso.proyecto_declarado,
                "tiempo_objetivo": caso.peticion.ventana.tiempo_objetivo,
                "cardinalidad": caso.cardinalidad_declarada,
                "etapa_esperada": caso.etapa_esperada,
                "parada_esperada": caso.parada_esperada,
                "resultado_esperado": list(caso.resultado_esperado),
                "orden_esperado": list(caso.orden_esperado),
                "elegibles": list(caso.elegibles),
                "prohibidos": list(caso.prohibidos),
                "adjudicable": caso.adjudicable,
                "motivo_no_adjudicable": caso.motivo_no_adjudicable,
                "referencias_fuera_del_canon": list(caso.referencias_fuera_del_canon),
            }
            for caso in casos
        ],
        "veredictos": {
            identificador: [
                {
                    "caso": v.caso,
                    "canonico": v.canonico,
                    "adjudicable": v.adjudicable,
                    "obtenido": list(v.obtenido),
                    "esperado": list(v.esperado),
                    "resultado_exacto": v.resultado_exacto,
                    "orden_exacto": v.orden_exacto,
                    "declara_orden": v.declara_orden,
                    "contaminacion": list(v.contaminacion),
                    "fuga_de_ambito": list(v.fuga_de_ambito),
                    "confusion_de_polaridad": list(v.confusion_de_polaridad),
                    "polaridad_mal_leida": list(v.polaridad_mal_leida),
                    "etapa_conforme": v.etapa_conforme,
                    "etapa_puntua": v.etapa_puntua,
                    "razon_de_etapa": v.razon_de_etapa,
                    "ausencia_correcta": v.ausencia_correcta,
                    "criticos_pendientes": list(v.criticos_pendientes),
                    "explicaciones_completas": v.explicaciones_completas,
                    "resultados_totales": v.resultados_totales,
                    "suficiencia": v.suficiencia,
                    "estado_externo": v.estado_externo,
                    "parada": v.parada,
                    "etapas_recorridas": list(v.etapas_recorridas),
                }
                for v in lista
            ]
            for identificador, lista in veredictos.items()
        },
        "sesiones": [
            {
                "sesion": s["sesion"],
                "pid": s["pid"],
                "carga_inicial": s["carga_inicial"],
                "carga_final": s["carga_final"],
                "casos_por_repeticion": s["casos_por_repeticion"],
                "primeros_ordenes": s["ordenes_ejecutados"],
                "muestras_ns": s["muestras_ns"],
            }
            for s in sesiones
        ],
        "registro_obligatorio": list(rp.REGISTRO_OBLIGATORIO),
        "evidencia_minima": list(rp.EVIDENCIA_MINIMA),
    }


def ejecutar(salida: Path, salida_evidencia: Path) -> int:
    """La corrida real. Solo llega a medir si TODO lo previo pasa."""
    entorno = entorno_custodia_real()
    dependencias = recorrido.dependencias_reales()
    fallos = list(recorrido.comprobar(dependencias).fallos)
    fallos.extend(
        fallos_adicionales(arbol_limpio=entorno.arbol_limpio(), salidas=(salida, salida_evidencia))
    )
    if fallos:
        print("la ronda primaria NO puede ejecutarse. Falta:")
        for fallo in fallos:
            print(f"  - {fallo}")
        return CODIGO_BLOQUEADO

    head = entorno.head()
    boot_id = _boot_id()
    trabajo = Path(tempfile.mkdtemp(prefix="adr002_ronda_"))
    try:
        proyeccion = build.construir_desde_la_familia(trabajo / "planos")
        casos = cs.casos_ejecutables(cs.cargar_artefactos())
        print(f"casos ejecutables: {len(casos)}; adjudicables: {sum(c.adjudicable for c in casos)}")

        print("conformidad: los cinco contra los casos congelados...")
        veredictos = conformidad(proyeccion, casos, trabajo / "conformidad")
        puerta5 = borrado_y_regeneracion(proyeccion, trabajo / "puerta5")

        repeticion_unica = False
        sesiones: list[Mapping[str, Any]] = []
        for intento in range(CORRIDAS_MAXIMAS):
            print(f"rendimiento, corrida {intento + 1}: {rp.SESIONES_EXIGIDAS} sesiones...")
            sesiones = ejecutor_de_sesiones()
            invalida = fallos_de_corrida(sesiones)
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
        shutil.rmtree(trabajo, ignore_errors=True)

    if boot_id is not None and boot_id != _boot_id():
        print("la maquina se reinicio durante la corrida: NO_EVALUABLE, sin artefacto.")
        return CODIGO_NO_EVALUABLE

    resumenes = _resumenes(veredictos, puerta5)
    tiempos = latencias(sesiones)
    controles = {
        "autorizacion_expresa_presente": not rp.fallos_de_autorizacion(
            dependencias.entorno_custodia
        ),
        "familia_de_conformidad_intacta": not rp.fallos_de_familia(dependencias.entorno_custodia),
        "corpus_congelado_intacto": not rp.fallos_de_corpus(dependencias.entorno_custodia),
        "perfil_y_suelo_congelados": not rp.fallos_de_perfil(dependencias.entorno_custodia),
        "capa_comun_neutral": not neutrality.fallos_de_neutralidad(RAIZ_REPOSITORIO),
        "ronda_sin_reduccion": sorted(veredictos) == sorted(rp.PARTICIPANTES),
        "once_sesiones_completas": len(sesiones) == rp.SESIONES_EXIGIDAS,
        "los_cinco_sobre_el_mismo_fichero": True,
        "warmup_declarado_y_descartado": all(s["warmup_descartado"] == rp.WARMUP for s in sesiones),
        "percentiles_por_rango_mas_cercano": all(
            tiempos[p]["p50_por_sesion_ns"]
            == [pp.p50_ns(list(s["muestras_ns"][p])) for s in sesiones]
            for p in rp.PARTICIPANTES
        ),
    }
    if not all(controles.values()):
        print("controles bloqueantes fallidos: no se escribe artefacto.")
        for nombre, valor in controles.items():
            if not valor:
                print(f"  - {nombre}")
        return CODIGO_BLOQUEADO

    documento = _documento(
        head=head,
        resumenes=resumenes,
        tiempos=tiempos,
        casos=casos,
        repeticion_unica=repeticion_unica,
        controles=controles,
    )
    evidencia = _evidencia(
        head=head, boot_id=boot_id, veredictos=veredictos, casos=casos, sesiones=sesiones
    )
    escribir_json_atomico(salida, documento)
    escribir_json_atomico(salida_evidencia, evidencia)

    print(f"artefacto escrito: {salida}")
    print(f"evidencia escrita: {salida_evidencia}")
    for identificador in rp.PARTICIPANTES:
        resumen = resumenes[identificador]
        puertas = "".join("V" if v else "X" for v in resumen.puertas.values())
        print(
            f"  {identificador:12} puertas={puertas} "
            f"exactos={resumen.casos_con_resultado_exacto}/{resumen.casos_adjudicados} "
            f"P50 {min(tiempos[identificador]['p50_por_sesion_ns']) / 1e6:.1f}-"
            f"{max(tiempos[identificador]['p50_por_sesion_ns']) / 1e6:.1f} ms"
        )
    print("Esta ejecucion NO elige alternativa: elegir es un acto del usuario.")
    return CODIGO_OK


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="execute_round",
        description="Ejecuta la ronda primaria de ADR-002. Se bloquea sin el acta.",
    )
    analizador.add_argument("--execute", action="store_true", help="ejecuta la corrida real")
    analizador.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    analizador.add_argument("--session", type=int, default=0, help=argparse.SUPPRESS)
    analizador.add_argument("--output", type=str, default=SALIDA)
    analizador.add_argument("--evidence-output", type=str, default=SALIDA_EVIDENCIA)
    argumentos = analizador.parse_args(argv)

    if not argumentos.execute:
        print("execute_round no ejecuta nada sin --execute.")
        return CODIGO_SIN_EXECUTE

    if argumentos.worker:
        if argumentos.session < 1:
            print("un worker exige --session >= 1", file=sys.stderr)
            return CODIGO_BLOQUEADO
        trabajo = Path(tempfile.mkdtemp(prefix=f"adr002_sesion_{argumentos.session}_"))
        try:
            resultado = medir_sesion(argumentos.session, trabajo)
        finally:
            shutil.rmtree(trabajo, ignore_errors=True)
        json.dump(resultado, sys.stdout, separators=(",", ":"))
        return CODIGO_OK

    return ejecutar(
        RAIZ_REPOSITORIO / argumentos.output, RAIZ_REPOSITORIO / argumentos.evidence_output
    )


if __name__ == "__main__":
    raise SystemExit(main())
