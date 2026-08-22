"""Derivacion del perfil de tolerancias P50/P95 (ADR002-TOL-209, paquete 08).

**No mide nada.** La fuente es el artefacto congelado
``artifacts/adr002_tolerances/suelo_medicion_v0.3.json``, cuyo blob se fija
por constante, y todo el perfil se deriva de sus vectores crudos.

    uv run python -m experiments.adr002.tolerances.derive_profile \\
        --execute \\
        --preinscription-commit <SHA> \\
        --output artifacts/adr002_tolerances/perfil_tolerancias_v0.1.json

Garantias:

- **determinista**: misma fuente, mismo artefacto byte a byte. No hay reloj,
  ni PID, ni carga, ni nada dependiente del momento de ejecucion. La propia
  corrida lo comprueba derivando dos veces y comparando los bytes;
- **no mide**: no abre cronometro, no lanza procesos, no toca SQLite;
- antes de escribir comprueba, fallando cerrado: arbol limpio, ``HEAD`` igual
  al commit de preinscripcion, los ocho blobs preinscritos contra el arbol y
  contra el commit, el modulo heredado, **el protocolo y el Registro
  anteriores intactos**, **las seis evidencias anteriores intactas** y la
  ruta de salida inexistente;
- los percentiles se **recomputan** desde ``muestras_ns``: no se acepta
  ninguno de los publicados en la fuente.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from experiments.adr002.tolerances import envelope_protocol as ep
from experiments.adr002.tolerances import profile_protocol as pp
from experiments.adr002.tolerances import schema_profile_v0_1 as esquema

RAIZ_REPOSITORIO: Final = Path(__file__).resolve().parents[3]

CODIGO_OK: Final = 0
CODIGO_BLOQUEADO: Final = 2
CODIGO_SIN_EXECUTE: Final = 3

#: Linea base historica. Se cita como CONTRASTE, nunca como veredicto: fue
#: medida con cinco sesiones y la regla 5 prohibe comparar rangos obtenidos
#: con numeros distintos de sesiones.
RUTA_LINEA_BASE: Final = "artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json"
BLOB_LINEA_BASE: Final = "f9f051332d9833fb7e10b27f4820849f00b6fe6c"
SESIONES_LINEA_BASE: Final = 5


class DerivacionBloqueadaError(RuntimeError):
    """Una precondicion de custodia o de fuente no se cumple."""


# --------------------------------------------------------------------------
# Acceso a Git, aislado para poder inyectarlo en las pruebas
# --------------------------------------------------------------------------


def _git(*argumentos: str, raiz: Path | None = None) -> str:
    destino = RAIZ_REPOSITORIO if raiz is None else raiz
    completado = subprocess.run(
        ["git", *argumentos], cwd=str(destino), capture_output=True, text=True, check=False
    )
    if completado.returncode != 0:
        msg = f"git {' '.join(argumentos)} fallo: {completado.stderr.strip()}"
        raise DerivacionBloqueadaError(msg)
    return completado.stdout.strip()


def entorno_custodia_real(raiz: Path | None = None) -> ep.EntornoCustodia:
    """Construye el entorno de custodia sobre el repositorio real."""
    destino = RAIZ_REPOSITORIO if raiz is None else raiz

    def leer_bytes(ruta: str) -> bytes:
        return (destino / ruta).read_bytes()

    def _rc(*orden: str) -> bool:
        return (
            subprocess.run(
                list(orden), cwd=str(destino), capture_output=True, text=True, check=False
            ).returncode
            == 0
        )

    def blob_en_commit(sha: str, ruta: str) -> str | None:
        completado = subprocess.run(
            ["git", "rev-parse", f"{sha}:{ruta}"],
            cwd=str(destino),
            capture_output=True,
            text=True,
            check=False,
        )
        if completado.returncode != 0:
            return None
        return completado.stdout.strip() or None

    return ep.EntornoCustodia(
        leer_bytes=leer_bytes,
        es_ancestro=lambda a, b: _rc("git", "merge-base", "--is-ancestor", a, b),
        existe_commit=lambda sha: _rc("git", "cat-file", "-e", f"{sha}^{{commit}}"),
        head=lambda: _git("rev-parse", "HEAD", raiz=destino),
        arbol_limpio=lambda: _git("status", "--porcelain", raiz=destino) == "",
        diff_vacio=lambda desde, hasta, rutas: _rc(
            "git", "diff", "--quiet", f"{desde}..{hasta}", "--", *rutas
        ),
        blob_en_commit=blob_en_commit,
    )


# --------------------------------------------------------------------------
# Precondiciones
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Precondiciones:
    """Resultado de todas las comprobaciones previas a derivar."""

    fallos: tuple[str, ...]
    blobs_preinscritos: Mapping[str, str]
    blobs_heredados: Mapping[str, str]
    evidencias_intactas: bool
    gobierno_intacto: bool

    @property
    def permite_derivar(self) -> bool:
        return not self.fallos


def comprobar_precondiciones(
    entorno: ep.EntornoCustodia,
    *,
    sha_a: str,
    salida: Path,
    salida_existe: bool | None = None,
) -> Precondiciones:
    """Comprueba custodia y fuente. Falla cerrado y no deriva nada."""
    existe = salida.exists() if salida_existe is None else salida_existe
    fallos = list(pp.verificar_precondiciones(entorno, sha_a=sha_a, salida_existe=existe))

    blobs_preinscritos: dict[str, str] = {}
    for ruta in pp.ARCHIVOS_PREINSCRITOS:
        try:
            blobs_preinscritos[ruta] = pp.blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"fichero preinscrito ilegible: {ruta}")

    blobs_heredados: dict[str, str] = {}
    for ruta in pp.ARCHIVOS_HEREDADOS:
        try:
            blobs_heredados[ruta] = pp.blob_git(entorno.leer_bytes(ruta))
        except OSError:
            fallos.append(f"modulo heredado ilegible: {ruta}")

    fallos_gobierno = pp.fallos_documentos_de_gobierno(entorno)
    fallos.extend(fallos_gobierno)
    fallos_evidencias = pp.fallos_evidencias_anteriores(entorno)
    fallos.extend(fallos_evidencias)

    try:
        if pp.blob_git(entorno.leer_bytes(RUTA_LINEA_BASE)) != BLOB_LINEA_BASE:
            fallos.append("la linea base historica fue alterada")
    except OSError:
        fallos.append("linea base historica ilegible")

    if blobs_preinscritos and blobs_heredados:
        fallos.extend(
            pp.verificar_custodia(
                entorno,
                sha_a=sha_a,
                blobs_preinscritos=blobs_preinscritos,
                blobs_heredados=blobs_heredados,
            )
        )

    return Precondiciones(
        fallos=tuple(dict.fromkeys(fallos)),
        blobs_preinscritos=blobs_preinscritos,
        blobs_heredados=blobs_heredados,
        evidencias_intactas=not fallos_evidencias,
        gobierno_intacto=not fallos_gobierno,
    )


# --------------------------------------------------------------------------
# Lectura de la fuente congelada
# --------------------------------------------------------------------------


def leer_fuente_real() -> bytes:
    """Lee los BYTES del artefacto v0.3. La unica lectura vinculante.

    Devuelve bytes, no un objeto ya interpretado, para que el blob que se
    verifica y los datos que se derivan salgan de **la misma lectura**. Con
    dos lecturas independientes, el blob publicado acreditaria un contenido
    distinto del que produjo las cifras.
    """
    return (RAIZ_REPOSITORIO / pp.FUENTE).read_bytes()


def objeto_json(crudo: bytes, ruta: str) -> Mapping[str, Any]:
    """Interpreta unos bytes ya verificados como objeto JSON."""
    datos = json.loads(crudo.decode("utf-8"))
    if not isinstance(datos, dict):
        msg = f"{ruta} no contiene un objeto JSON"
        raise DerivacionBloqueadaError(msg)
    return datos


def cargar_linea_base_real() -> Mapping[str, Any]:
    """Lee la linea base historica. Solo para el contraste no comparable."""
    datos = json.loads((RAIZ_REPOSITORIO / RUTA_LINEA_BASE).read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        msg = f"{RUTA_LINEA_BASE} no contiene un objeto JSON"
        raise DerivacionBloqueadaError(msg)
    return datos


def _vector_entero(valores: Any) -> list[int]:
    if not isinstance(valores, Sequence) or isinstance(valores, str | bytes):
        msg = "muestras_ns debe ser una secuencia de enteros"
        raise DerivacionBloqueadaError(msg)
    salida: list[int] = []
    for v in valores:
        if not isinstance(v, int) or isinstance(v, bool):
            msg = "muestras_ns debe contener solo enteros"
            raise DerivacionBloqueadaError(msg)
        if v < 0:
            msg = "muestras_ns contiene una duracion negativa"
            raise DerivacionBloqueadaError(msg)
        salida.append(v)
    if not salida:
        msg = "vector de muestras vacio"
        raise DerivacionBloqueadaError(msg)
    return salida


def observaciones_desde_fuente(
    fuente: Mapping[str, Any],
) -> tuple[list[pp.ObservacionEscala], list[pp.ObservacionUnitaria]]:
    """Recompute los percentiles desde ``muestras_ns``. No acepta los publicados.

    Es el punto en el que la derivacion se hace independiente de la fuente:
    si el artefacto v0.3 publicase un percentil incoherente con su propio
    vector, el perfil se construiria con el vector, no con la cifra.
    """
    escalas = fuente.get("escalas")
    unitarias = fuente.get("sondas_unitarias")
    if not isinstance(escalas, Sequence) or isinstance(escalas, str | bytes):
        msg = "la fuente no publica la seccion escalas"
        raise DerivacionBloqueadaError(msg)
    if not isinstance(unitarias, Sequence) or isinstance(unitarias, str | bytes):
        msg = "la fuente no publica la seccion sondas_unitarias"
        raise DerivacionBloqueadaError(msg)

    observaciones: list[pp.ObservacionEscala] = []
    for entrada in escalas:
        if not isinstance(entrada, Mapping):
            msg = "cada entrada de escalas debe ser un objeto"
            raise DerivacionBloqueadaError(msg)
        vector = _vector_entero(entrada.get("muestras_ns"))
        familia, escala, pid = entrada.get("familia"), entrada.get("escala_ns"), entrada.get("pid")
        if not isinstance(familia, str):
            msg = "familia invalida en la fuente"
            raise DerivacionBloqueadaError(msg)
        if not isinstance(escala, int) or isinstance(escala, bool):
            msg = "escala_ns invalida en la fuente"
            raise DerivacionBloqueadaError(msg)
        if not isinstance(pid, int) or isinstance(pid, bool):
            msg = "pid invalido en la fuente"
            raise DerivacionBloqueadaError(msg)
        observaciones.append(
            pp.ObservacionEscala(
                familia=familia,
                escala_ns=escala,
                pid=pid,
                p50=pp.p50_ns(vector),
                p95=pp.p95_ns(vector),
            )
        )

    unidades: list[pp.ObservacionUnitaria] = []
    for entrada in unitarias:
        if not isinstance(entrada, Mapping):
            msg = "cada entrada de sondas_unitarias debe ser un objeto"
            raise DerivacionBloqueadaError(msg)
        vector = _vector_entero(entrada.get("muestras_ns"))
        sonda, pid = entrada.get("sonda"), entrada.get("pid")
        if not isinstance(sonda, str):
            msg = "sonda invalida en la fuente"
            raise DerivacionBloqueadaError(msg)
        if not isinstance(pid, int) or isinstance(pid, bool):
            msg = "pid invalido en la fuente"
            raise DerivacionBloqueadaError(msg)
        unidades.append(pp.ObservacionUnitaria(sonda=sonda, pid=pid, p95=pp.p95_ns(vector)))

    return observaciones, unidades


def _ms_a_ns(valor: Any) -> int:
    return round(float(valor) * 1_000_000)


def contraste_linea_base(linea_base: Mapping[str, Any], perfil: pp.Perfil) -> list[dict[str, Any]]:
    """Contraste con la linea base historica. **Nunca un veredicto.**

    La linea base se midio con cinco sesiones. La regla 5 prohibe comparar
    rangos obtenidos con numeros distintos de sesiones, de modo que cada
    magnitud sale ``NO_COMPARABLE`` con su motivo. Se publican sus cifras
    para que la asimetria entre P50 y P95 sea auditable, no para juzgarla.
    """
    escenarios = linea_base["escenarios_remedidos"]["E-SESIONES-5_variacion_entre_ejecuciones"][
        "variacion_entre_sesiones"
    ]
    entradas: list[dict[str, Any]] = []
    for escenario, magnitudes in escenarios.items():
        if not isinstance(magnitudes, Mapping):
            continue
        capas = sorted({clave.rsplit("__", 1)[0] for clave in magnitudes if clave.endswith("_ms")})
        for capa in capas:
            p50s = [_ms_a_ns(v) for v in magnitudes[f"{capa}__p50_ms"]["valores_por_sesion"]]
            p95s = [_ms_a_ns(v) for v in magnitudes[f"{capa}__p95_ms"]["valores_por_sesion"]]
            veredicto = pp.evaluar_magnitud(p50s, p95s, perfil=perfil)
            entradas.append(
                {
                    "magnitud": f"{escenario}.{capa}",
                    "fuente": RUTA_LINEA_BASE,
                    "sesiones": veredicto.sesiones,
                    "sesiones_exigidas": pp.SESIONES_EXIGIDAS,
                    "min_p50_ns": veredicto.p50.minimo,
                    "max_p50_ns": veredicto.p50.maximo,
                    "dispersion_p50_ns": veredicto.p50.dispersion,
                    "min_p95_ns": veredicto.p95.minimo,
                    "max_p95_ns": veredicto.p95.maximo,
                    "dispersion_p95_ns": veredicto.p95.dispersion,
                    "resultado": veredicto.resultado,
                    "motivo": veredicto.motivo,
                    "registro": pp.registro_por_percentil(veredicto),
                    "banda_p50_que_le_corresponderia_ns": None,
                    "banda_p95_que_le_corresponderia_ns": None,
                }
            )
    return entradas


# --------------------------------------------------------------------------
# Controles
# --------------------------------------------------------------------------


def evaluar_controles(
    *,
    fuente: Mapping[str, Any],
    observaciones: Sequence[pp.ObservacionEscala],
    unitarias: Sequence[pp.ObservacionUnitaria],
    perfil: pp.Perfil,
    fuente_intacta: bool,
    evidencias_intactas: bool,
    gobierno_intacto: bool,
    custodia_ok: bool,
    determinista: bool,
    percentiles_coinciden: bool,
) -> dict[str, bool]:
    """Deriva el estado de los controles bloqueantes desde los datos."""
    filas_por_par = {
        (familia, escala): [
            o for o in observaciones if o.familia == familia and o.escala_ns == escala
        ]
        for familia in pp.FAMILIAS
        for escala in pp.ESCALERA_NS
    }
    completa = len(filas_por_par) == len(pp.FAMILIAS) * len(pp.ESCALERA_NS)
    # Once identificadores, once filas —una por sesion— y las MISMAS once en
    # toda la fuente: sin las tres cosas, "once sesiones completas" no queda
    # comprobado en ningun punto.
    once = all(
        len({o.pid for o in filas}) == pp.SESIONES_EXIGIDAS == len(filas)
        for filas in filas_por_par.values()
    )
    mismas = len(pp.sesiones_de_la_fuente(observaciones, unitarias)) == pp.SESIONES_EXIGIDAS

    declaradas = fuente.get("plan", {})
    procesos_fuente = declaradas.get("procesos") if isinstance(declaradas, Mapping) else None

    return {
        "fuente_intacta": fuente_intacta,
        "fuente_con_once_sesiones": (once and mismas and procesos_fuente == pp.SESIONES_EXIGIDAS),
        "escalera_completa": completa and pp.escalera_estrictamente_creciente(),
        "percentiles_recomputados": percentiles_coinciden,
        "envolventes_monotonas": pp.envolventes_monotonas(perfil),
        "envolventes_cubren_el_suelo": pp.envolventes_cubren_el_suelo(perfil),
        "bandas_no_decrecientes": pp.bandas_no_decrecientes(perfil),
        "continuidad_p50_exacta": pp.continuidad_p50_exacta(perfil),
        "p95_no_mas_estable_que_p50": pp.p95_domina_a_p50(perfil),
        "sin_umbral_relativo_para_p95": pp.p95_sin_umbral_relativo(perfil),
        "guarda_de_sesiones_activa": _guarda_de_sesiones_activa(perfil),
        "evidencias_anteriores_intactas": evidencias_intactas,
        "documentos_de_gobierno_intactos": gobierno_intacto,
        "derivacion_determinista": determinista,
        "custodia_verificada": custodia_ok,
    }


def _guarda_de_sesiones_activa(perfil: pp.Perfil) -> bool:
    """Comprueba que una magnitud con otro numero de sesiones no recibe veredicto."""
    sondeo = pp.evaluar_magnitud([100_000] * 5, [200_000] * 5, perfil=perfil)
    correcta = pp.evaluar_magnitud(
        [100_000] * pp.SESIONES_EXIGIDAS, [200_000] * pp.SESIONES_EXIGIDAS, perfil=perfil
    )
    return (
        sondeo.resultado == pp.NO_COMPARABLE
        and sondeo.motivo == pp.MOTIVO_SESIONES
        and correcta.resultado != pp.NO_COMPARABLE
    )


def percentiles_de_la_fuente_coinciden(
    fuente: Mapping[str, Any], observaciones: Sequence[pp.ObservacionEscala]
) -> bool:
    """Los percentiles recomputados coinciden con los que la fuente publica.

    No es un requisito para derivar —el perfil usa los recomputados— pero su
    coincidencia acredita que la fuente era coherente consigo misma.
    """
    escalas = fuente.get("escalas")
    if not isinstance(escalas, Sequence) or isinstance(escalas, str | bytes):
        return False
    indice = {(o.familia, o.escala_ns, o.pid): o for o in observaciones}
    for entrada in escalas:
        if not isinstance(entrada, Mapping):
            return False
        clave = (entrada.get("familia"), entrada.get("escala_ns"), entrada.get("pid"))
        observacion = indice.get(clave)  # type: ignore[arg-type]
        if observacion is None:
            return False
        if entrada.get("p50_ns") != observacion.p50 or entrada.get("p95_ns") != observacion.p95:
            return False
    return True


# --------------------------------------------------------------------------
# Construccion del perfil publicable
# --------------------------------------------------------------------------


def curva_publicable(
    envolvente: ep.Envolvente, *, con_sostenibilidad: bool
) -> list[dict[str, Any]]:
    """Curva de un percentil: ``D``, ``E``, razones y —solo P50— sostenibilidad."""
    filas: list[dict[str, Any]] = []
    for indice, escala in enumerate(pp.ESCALERA_NS):
        dispersion = envolvente.dispersiones[indice]
        envuelta = envolvente.envolvente[indice]
        fila: dict[str, Any] = {
            "escala_ns": escala,
            "dispersion_ns": dispersion,
            "envolvente_ns": envuelta,
            "banda_ns": envuelta,
            "razon_dispersion_por_mil": pp.razon_por_mil(dispersion, escala),
            "razon_envolvente_por_mil": pp.razon_por_mil(envuelta, escala),
        }
        if con_sostenibilidad:
            fila["sostenible"] = ep.sostenible_en_escalon(envuelta, escala)
        filas.append(fila)
    return filas


def construir_documento(
    *,
    sha_a: str,
    head: str,
    perfil: pp.Perfil,
    fuente: Mapping[str, Any],
    blobs_preinscritos: Mapping[str, str],
    blobs_heredados: Mapping[str, str],
    controles: Mapping[str, bool],
    contraste: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Construye el perfil completo. Determinista: sin reloj, PID ni entorno."""
    cruce = perfil.cruce_p50
    escalon = cruce.indice_escalon
    return {
        "documento": "Perfil de tolerancias P50/P95 LAB-LINUX para ADR002-TOL-107",
        "version_esquema": pp.VERSION_ESQUEMA,
        "estado": pp.ESTADO,
        "acta": pp.ACTA,
        "protocolo": pp.PROTOCOLO,
        "registro": pp.REGISTRO,
        "paquete": pp.PAQUETE,
        "derivado_no_medido": True,
        "fuente": {
            "ruta": pp.FUENTE,
            "blob": pp.BLOB_FUENTE,
            "commit": pp.COMMIT_FUENTE,
            "sesiones": pp.SESIONES_EXIGIDAS,
            "escalera_ns": list(pp.ESCALERA_NS),
            "familias": list(pp.FAMILIAS),
            "nota": (
                "no se ha realizado ninguna medicion nueva: el perfil se deriva de los "
                "vectores crudos de esta evidencia, con los percentiles recomputados"
            ),
        },
        "metodo": {
            "nombre": "perfil de tolerancias con P50 y P95 separados",
            "p50": (
                "objetivo relativo <= 20 % por encima de U50; banda B50(M) = E50(escalon "
                "superior) por debajo; sin afirmacion de latencia por debajo de SM"
            ),
            "p95": (
                "sin objetivo relativo; banda B95(M) = E95(escalon superior) en todo el rango "
                "cubierto; NO_EVALUABLE por debajo de SM o por encima de la mayor escala medida"
            ),
            "envolvente": "E_p(s_i) = max(D_p(s_1), ..., D_p(s_i)), monotona no decreciente",
            "consulta_de_banda": (
                "M es el minimo entre sesiones del MISMO percentil que se evalua: B50 en "
                "min_s P50 y B95 en min_s P95"
            ),
            "sesiones": (
                f"exactamente {pp.SESIONES_EXIGIDAS} sesiones para construir las bandas y para "
                f"evaluar candidatos; no se comparan rangos de tamanos de muestra distintos"
            ),
            "continuidad": "m * B50(U50) = U50 / 5 = 0,20 U50, exacta y derivada",
            "agregacion": (
                "basta que uno de los dos percentiles falle para que la magnitud falle; para "
                "que sea VALIDA hacen falta los dos evaluables y validos. Un percentil "
                "NO_EVALUABLE deja la magnitud NO_EVALUABLE: no se emite afirmacion positiva "
                "sobre una magnitud cuya cola no se evaluo"
            ),
            "hereda_de": list(pp.ARCHIVOS_HEREDADOS),
            "no_sustituye_evidencia": True,
        },
        "sesiones_exigidas": pp.SESIONES_EXIGIDAS,
        "sm_ns": perfil.sm_ns,
        "p50": {
            "objetivo_relativo": f"{pp.OBJETIVO_RELATIVO_NUM}/{pp.OBJETIVO_RELATIVO_DEN}",
            "factor_u": pp.FACTOR_U,
            "m": pp.MARGEN_M,
            "u50_ns": perfil.u50_ns,
            "b50_en_u50_ns": perfil.b50_en_u50_ns,
            "indice_escalon_del_cruce": escalon,
            "escalon_del_cruce_ns": None if escalon is None else pp.ESCALERA_NS[escalon],
            "intervalo_del_cruce_ns": (
                None
                if escalon is None
                else [0 if escalon == 0 else pp.ESCALERA_NS[escalon - 1], pp.ESCALERA_NS[escalon]]
            ),
            "motivo_no_evaluable": cruce.motivo_no_evaluable,
            "curva": curva_publicable(cruce.envolvente, con_sostenibilidad=True),
        },
        "p95": {
            "sin_umbral_relativo": True,
            "objetivo_relativo_aplicable": False,
            "rango_cubierto_ns": [perfil.sm_ns, perfil.cubierto_hasta_ns],
            "curva": curva_publicable(perfil.envolvente_p95, con_sostenibilidad=False),
        },
        "preinscripcion": {
            "commit_a": sha_a,
            "head_en_derivacion": head,
            "blobs_preinscritos": dict(blobs_preinscritos),
            "blobs_heredados": dict(blobs_heredados),
            "blob_fuente": pp.BLOB_FUENTE,
            "blob_linea_base": BLOB_LINEA_BASE,
            "blobs_evidencias_anteriores": dict(pp.EVIDENCIAS_ANTERIORES),
            "blob_protocolo_anterior": ep.BLOB_PROTOCOLO_APROBADO,
            "blob_registro_anterior": ep.BLOB_REGISTRO_ACTUALIZADO,
        },
        "controles_internos": dict(controles),
        "contraste_no_comparable": {
            "fuente": RUTA_LINEA_BASE,
            "sesiones": SESIONES_LINEA_BASE,
            "sesiones_exigidas": pp.SESIONES_EXIGIDAS,
            "nota": (
                "la linea base se midio con cinco sesiones; la regla 5 de TOL-107 prohibe "
                "comparar rangos obtenidos con numeros distintos de sesiones. Sus cifras se "
                "publican para que la asimetria entre P50 y P95 sea auditable, y NUNCA como "
                "veredicto"
            ),
            "magnitudes": [dict(m) for m in contraste],
        },
        "custodia": {
            "sha_a_es_ancestro": True,
            "diff_preinscritos_vacio": True,
            "evidencias_anteriores_intactas": True,
            "documentos_de_gobierno_intactos": True,
            "head": head,
        },
        "no_autoriza": {
            "aprobacion_tol_209": False,
            "limite_duro_tol_107": False,
            "sustitucion_evidencias_anteriores": False,
            "medicion_nueva": False,
            "t0": False,
            "candidatos": False,
            "benchmark": False,
            "merge_pr_117": False,
        },
    }


# --------------------------------------------------------------------------
# Escritura atomica
# --------------------------------------------------------------------------


def serializar(documento: Mapping[str, Any]) -> str:
    """Serializacion canonica. Misma entrada, mismos bytes."""
    return json.dumps(documento, ensure_ascii=False, indent=1, allow_nan=False) + "\n"


def escribir_json_atomico(ruta: Path, documento: Mapping[str, Any]) -> None:
    """Escribe el artefacto de forma atomica y SIN sobrescribir nunca."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    descriptor, nombre_temporal = tempfile.mkstemp(
        dir=str(ruta.parent), prefix=f"{ruta.name}.", suffix=".tmp"
    )
    try:
        # newline="\n" explicito: sin el, Python traduce cada salto a
        # os.linesep y el artefacto saldria con CRLF en Windows. Una
        # DERIVACION pura invita a reproducirla en otra plataforma, y la
        # garantia declarada es de bytes identicos, no de texto equivalente.
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as fichero:
            fichero.write(serializar(documento))
            fichero.flush()
            os.fsync(fichero.fileno())
        os.link(nombre_temporal, ruta)
    except BaseException:
        _eliminar_o_denunciar(Path(nombre_temporal), "temporal de escritura")
        raise
    else:
        _eliminar_o_denunciar(Path(nombre_temporal), "temporal de escritura")


class ResiduoNoEliminableError(RuntimeError):
    """Un fichero que debia desaparecer sigue en disco."""


def _eliminar_o_denunciar(ruta: Path, etiqueta: str) -> None:
    """Elimina ``ruta`` y verifica el estado del disco; nunca calla el fallo."""
    try:
        ruta.unlink()
    except FileNotFoundError:
        return
    except OSError as exc:
        msg = f"{etiqueta} no eliminable: {ruta} ({exc})"
        raise ResiduoNoEliminableError(msg) from exc
    if ruta.exists():
        msg = f"{etiqueta} sigue en disco tras eliminarlo: {ruta}"
        raise ResiduoNoEliminableError(msg)


# --------------------------------------------------------------------------
# Recorrido completo
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DependenciasDerivacion:
    """Dependencias externas del recorrido, inyectables en las pruebas."""

    entorno_custodia: ep.EntornoCustodia
    leer_fuente_bytes: Callable[[], bytes]
    cargar_linea_base: Callable[[], Mapping[str, Any]]


def dependencias_reales() -> DependenciasDerivacion:
    """Dependencias de la derivacion real sobre el repositorio."""
    return DependenciasDerivacion(
        entorno_custodia=entorno_custodia_real(),
        leer_fuente_bytes=leer_fuente_real,
        cargar_linea_base=cargar_linea_base_real,
    )


def derivar_documento(
    *,
    sha_a: str,
    head: str,
    fuente: Mapping[str, Any],
    linea_base: Mapping[str, Any],
    blobs_preinscritos: Mapping[str, str],
    blobs_heredados: Mapping[str, str],
    fuente_intacta: bool,
    evidencias_intactas: bool,
    gobierno_intacto: bool,
    custodia_ok: bool,
    determinista: bool,
) -> dict[str, Any]:
    """Deriva el documento completo. Funcion PURA de sus argumentos."""
    observaciones, unitarias = observaciones_desde_fuente(fuente)
    perfil = pp.derivar_perfil(observaciones, unitarias)
    contraste = contraste_linea_base(linea_base, perfil)
    controles = evaluar_controles(
        fuente=fuente,
        observaciones=observaciones,
        unitarias=unitarias,
        perfil=perfil,
        fuente_intacta=fuente_intacta,
        evidencias_intactas=evidencias_intactas,
        gobierno_intacto=gobierno_intacto,
        custodia_ok=custodia_ok,
        determinista=determinista,
        percentiles_coinciden=percentiles_de_la_fuente_coinciden(fuente, observaciones),
    )
    return construir_documento(
        sha_a=sha_a,
        head=head,
        perfil=perfil,
        fuente=fuente,
        blobs_preinscritos=blobs_preinscritos,
        blobs_heredados=blobs_heredados,
        controles=controles,
        contraste=contraste,
    )


def ejecutar_derivacion(
    *, sha_a: str, salida: Path, dependencias: DependenciasDerivacion
) -> tuple[int, tuple[str, ...]]:
    """Recorrido completo: precondiciones -> derivacion -> validacion -> JSON."""
    try:
        precondiciones = comprobar_precondiciones(
            dependencias.entorno_custodia, sha_a=sha_a, salida=salida
        )
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"comprobacion de precondiciones fallo: {exc}",)
    if not precondiciones.permite_derivar:
        return CODIGO_BLOQUEADO, precondiciones.fallos

    # UNA sola lectura de la fuente: los bytes que se hashean son exactamente
    # los que se interpretan y de los que salen D50, E50, D95, E95 y SM. Con
    # dos lecturas, el blob publicado acreditaria otra cosa que las cifras.
    try:
        crudo = dependencias.leer_fuente_bytes()
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"lectura de la fuente fallo: {exc}",)
    if pp.blob_git(crudo) != pp.BLOB_FUENTE:
        return CODIGO_BLOQUEADO, ("la fuente v0.3 no coincide con su blob congelado",)

    try:
        fuente = objeto_json(crudo, pp.FUENTE)
        linea_base = dependencias.cargar_linea_base()
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"lectura de la fuente fallo: {exc}",)

    argumentos: dict[str, Any] = {
        "sha_a": sha_a,
        "head": dependencias.entorno_custodia.head(),
        "fuente": fuente,
        "linea_base": linea_base,
        "blobs_preinscritos": precondiciones.blobs_preinscritos,
        "blobs_heredados": precondiciones.blobs_heredados,
        "fuente_intacta": True,
        "evidencias_intactas": precondiciones.evidencias_intactas,
        "gobierno_intacto": precondiciones.gobierno_intacto,
        "custodia_ok": precondiciones.permite_derivar,
    }
    try:
        # Determinismo comprobado, no prometido: se deriva dos veces desde la
        # misma fuente y se comparan los BYTES, no los objetos. El control
        # publicado es el RESULTADO de esa comparacion, no una constante.
        primera = derivar_documento(**argumentos, determinista=True)
        repeticion = derivar_documento(**argumentos, determinista=True)
        determinista = serializar(primera) == serializar(repeticion)
        # El documento que se publica se construye CON el resultado de la
        # comparacion. Si las dos pasadas difiriesen, el control saldria
        # False y el esquema rechazaria el artefacto aunque este retorno no
        # existiese: el control no es una promesa, es una consecuencia.
        documento = derivar_documento(**argumentos, determinista=determinista)
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"derivacion fallo: {exc}",)
    if not determinista:
        return CODIGO_BLOQUEADO, ("la derivacion no es determinista: dos pasadas difieren",)

    fallos_documento = esquema.fallos_perfil_tolerancias(documento)
    if fallos_documento:
        return CODIGO_BLOQUEADO, tuple(f"perfil invalido: {f}" for f in fallos_documento)

    try:
        escribir_json_atomico(salida, documento)
    except FileExistsError:
        return CODIGO_BLOQUEADO, (
            f"la ruta de salida aparecio durante la derivacion y no se sobrescribe: {salida}",
        )
    except Exception as exc:
        return CODIGO_BLOQUEADO, (f"escritura del artefacto fallo: {exc}",)

    def _retirar(motivos: tuple[str, ...]) -> tuple[int, tuple[str, ...]]:
        try:
            _eliminar_o_denunciar(salida, "artefacto invalido")
        except ResiduoNoEliminableError as exc:
            return CODIGO_BLOQUEADO, (*motivos, f"ATENCION: {exc}")
        return CODIGO_BLOQUEADO, motivos

    try:
        releido = json.loads(salida.read_text(encoding="utf-8"))
    except Exception as exc:
        return _retirar((f"relectura del artefacto fallo: {exc}",))

    fallos_relectura = esquema.fallos_perfil_tolerancias(releido)
    if fallos_relectura:
        return _retirar(tuple(f"revalidacion tras escritura fallo: {f}" for f in fallos_relectura))

    return CODIGO_OK, ()


# --------------------------------------------------------------------------
# Interfaz de linea de ordenes
# --------------------------------------------------------------------------


def construir_parser() -> argparse.ArgumentParser:
    """Parser sin efectos secundarios."""
    parser = argparse.ArgumentParser(
        prog="derive_profile",
        description=(
            "Deriva el perfil de tolerancias P50/P95 desde la evidencia congelada v0.3. "
            "No mide nada. Sin --execute no escribe nada."
        ),
    )
    parser.add_argument("--execute", action="store_true", help="autoriza escribir el perfil")
    parser.add_argument(
        "--preinscription-commit",
        dest="preinscription_commit",
        default=None,
        help="SHA del commit de preinscripcion del paquete 08",
    )
    parser.add_argument("--output", dest="output", default=None, help="ruta del perfil a producir")
    parser.add_argument("--plan", action="store_true", help="imprime las reglas sin derivar")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    dependencias: DependenciasDerivacion | None = None,
) -> int:
    """Punto de entrada. Sin ``--execute`` no escribe nada."""
    args = construir_parser().parse_args(argv)

    if args.plan and not args.execute:
        print(f"fuente congelada: {pp.FUENTE} ({pp.BLOB_FUENTE})")
        print(f"sesiones exigidas: {pp.SESIONES_EXIGIDAS} (exactamente)")
        print(f"escalera: {list(pp.ESCALERA_NS)}")
        print("P50: relativo <= 1/5 por encima de U50 · banda por debajo · nada bajo SM")
        print("P95: sin umbral relativo · banda en todo el rango cubierto")
        print("B(M) se consulta en el minimo entre sesiones del MISMO percentil")
        print(f"controles bloqueantes: {len(pp.CONTROLES_BLOQUEANTES)}")
        return CODIGO_OK

    if not args.execute:
        print("derive_profile no escribe sin --execute.")
        return CODIGO_SIN_EXECUTE

    if not args.preinscription_commit or not args.output:
        print("--execute exige ademas --preinscription-commit y --output")
        return CODIGO_BLOQUEADO

    deps = dependencias_reales() if dependencias is None else dependencias
    codigo, fallos = ejecutar_derivacion(
        sha_a=args.preinscription_commit, salida=Path(args.output), dependencias=deps
    )
    if codigo != CODIGO_OK:
        print("derivacion bloqueada; no se ha publicado ningun valor:")
        for fallo in fallos:
            print(f"  - {fallo}")
        return codigo

    print(f"perfil derivado y revalidado: {args.output}")
    print("ADR002-TOL-209 sigue NO SATISFECHA hasta el acta correspondiente.")
    return CODIGO_OK


if __name__ == "__main__":
    raise SystemExit(main())
