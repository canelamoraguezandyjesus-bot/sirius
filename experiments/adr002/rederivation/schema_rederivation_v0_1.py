"""Esquema del artefacto de rederivacion (ADR002-TOL-208, paquete 10).

Se congela ahora, **antes** de que exista la medicion, que es lo que impide
ajustarlo despues de ver los resultados. No mide, no lee ficheros y no ejecuta
nada al importarse.

Lo que exige del artefacto que la rederivacion producira:

- las **seis magnitudes** de la linea base, escenario por capa, sin faltar ni
  sobrar ninguna;
- **once** valores por percentil y magnitud, uno por sesion;
- que el veredicto de cada magnitud **recompute** con el perfil aprobado de
  TOL-209, en vez de aceptarse como viene;
- que la linea base historica se **cite** y no se sustituya;
- que ningun conjunto de campos quede abierto.

Falla cerrado y es **total por contrato**: nunca lanza.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final, TypeGuard

from experiments.adr002.rederivation import rederivation_protocol as rp
from experiments.adr002.tolerances import profile_protocol as pp

VERSION_ESQUEMA: Final = rp.VERSION_ESQUEMA

SECCIONES: Final[tuple[str, ...]] = (
    "documento",
    "version_esquema",
    "estado",
    "paquete",
    "protocolo",
    "registro",
    "candidato",
    "head_de_esquema",
    "corpus",
    "plan",
    "linea_base_historica",
    "magnitudes",
    "controles_internos",
    "no_autoriza",
)

CAMPOS_CORPUS: Final[tuple[str, ...]] = ("acta", "blobs")
CAMPOS_PLAN: Final[tuple[str, ...]] = ("sesiones", "repeticiones", "escenarios", "capas")
CAMPOS_LINEA_BASE: Final[tuple[str, ...]] = ("ruta", "blob", "sesiones", "nota", "sustituida")
CAMPOS_MAGNITUD: Final[tuple[str, ...]] = (
    "magnitud",
    "p50_por_sesion_ns",
    "p95_por_sesion_ns",
    "min_p50_ns",
    "max_p50_ns",
    "min_p95_ns",
    "max_p95_ns",
    "resultado",
    "motivo",
    "registro",
)

NEGACIONES: Final[tuple[str, ...]] = (
    "sustitucion_de_la_linea_base_historica",
    "candidatos",
    "benchmark",
    "merge_pr_117",
)


def _es_lista(valor: Any) -> TypeGuard[Sequence[Any]]:
    return isinstance(valor, Sequence) and not isinstance(valor, str | bytes)


def _entero(valor: Any) -> TypeGuard[int]:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _ajenos(objeto: Mapping[str, Any], admitidos: Sequence[str], etiqueta: str) -> list[str]:
    sobra = sorted(set(objeto) - set(admitidos))
    return [f"{etiqueta} declara campos ajenos al esquema: {sobra}"] if sobra else []


def fallos_rederivacion(doc: Mapping[str, Any], *, perfil: pp.Perfil | None = None) -> list[str]:
    """Valida el artefacto completo. **Total por contrato: nunca lanza.**"""
    try:
        return _fallos(doc, perfil)
    except Exception as exc:
        return [f"validacion abortada por artefacto malformado: {type(exc).__name__}: {exc}"]


def _fallos(doc: Mapping[str, Any], perfil: pp.Perfil | None) -> list[str]:
    if not isinstance(doc, Mapping):
        return ["el artefacto debe ser un objeto JSON"]

    fallos = [f"falta la seccion obligatoria: {s}" for s in SECCIONES if s not in doc]
    fallos.extend(_ajenos(doc, SECCIONES, "el artefacto"))
    if doc.get("version_esquema") != VERSION_ESQUEMA:
        fallos.append(f"version_esquema debe ser {VERSION_ESQUEMA}")
    if doc.get("protocolo") != rp.PROTOCOLO:
        fallos.append(f"el protocolo declarado debe ser el aprobado ({rp.PROTOCOLO})")
    if doc.get("candidato") != rp.CANDIDATO:
        fallos.append(f"candidato debe ser {rp.CANDIDATO}")
    if doc.get("head_de_esquema") != rp.HEAD_T0:
        fallos.append(f"head_de_esquema debe identificar a T0 ({rp.HEAD_T0})")

    fallos.extend(_fallos_corpus(doc))
    fallos.extend(_fallos_plan(doc))
    fallos.extend(_fallos_linea_base(doc))
    fallos.extend(_fallos_magnitudes(doc, perfil))
    fallos.extend(_fallos_controles(doc))
    fallos.extend(_fallos_negaciones(doc))
    return fallos


def _fallos_corpus(doc: Mapping[str, Any]) -> list[str]:
    corpus = doc.get("corpus")
    if not isinstance(corpus, Mapping):
        return ["corpus ausente o con forma invalida"]
    fallos = _ajenos(corpus, CAMPOS_CORPUS, "corpus")
    if corpus.get("acta") != rp.ACTA_CORPUS:
        fallos.append(f"corpus.acta debe ser {rp.ACTA_CORPUS}")
    # El corpus se cita por blob: rederivar sobre otro corpus no es rederivar.
    if corpus.get("blobs") != dict(rp.CORPUS_CONGELADO):
        fallos.append("corpus.blobs no cita los blobs congelados por el acta v0.4")
    return fallos


def _fallos_plan(doc: Mapping[str, Any]) -> list[str]:
    plan = doc.get("plan")
    if not isinstance(plan, Mapping):
        return ["plan ausente o con forma invalida"]
    fallos = _ajenos(plan, CAMPOS_PLAN, "plan")
    if plan.get("sesiones") != rp.SESIONES_EXIGIDAS:
        fallos.append(f"plan.sesiones debe ser exactamente {rp.SESIONES_EXIGIDAS}")
    repeticiones = plan.get("repeticiones")
    if not _entero(repeticiones) or repeticiones < rp.REPETICIONES_MINIMAS:
        fallos.append(f"plan.repeticiones debe ser al menos {rp.REPETICIONES_MINIMAS}")
    if list(plan.get("escenarios") or ()) != list(rp.ESCENARIOS):
        fallos.append("plan.escenarios debe ser identico al de la linea base historica")
    if list(plan.get("capas") or ()) != list(rp.CAPAS):
        fallos.append("plan.capas debe ser identico al de la linea base historica")
    return fallos


def _fallos_linea_base(doc: Mapping[str, Any]) -> list[str]:
    base = doc.get("linea_base_historica")
    if not isinstance(base, Mapping):
        return ["linea_base_historica ausente o con forma invalida"]
    fallos = _ajenos(base, CAMPOS_LINEA_BASE, "linea_base_historica")
    if base.get("ruta") != rp.LINEA_BASE_HISTORICA:
        fallos.append("linea_base_historica.ruta no es la evidencia congelada")
    if base.get("blob") != rp.BLOB_LINEA_BASE:
        fallos.append("linea_base_historica.blob no coincide con el congelado")
    if base.get("sesiones") != rp.SESIONES_LINEA_BASE_HISTORICA:
        fallos.append("linea_base_historica.sesiones debe declarar las cinco originales")
    # La historica se conserva. Rederivar no es remedirla ni retirarla.
    if base.get("sustituida") is not False:
        fallos.append(
            "linea_base_historica.sustituida debe ser False: la evidencia historica se "
            "conserva con su head y sus ficheros, y esta rederivacion no la sustituye"
        )
    if not isinstance(base.get("nota"), str) or not str(base.get("nota")).strip():
        fallos.append("linea_base_historica.nota debe explicar por que se rederiva")
    return fallos


def _fallos_magnitudes(doc: Mapping[str, Any], perfil: pp.Perfil | None) -> list[str]:
    magnitudes = doc.get("magnitudes")
    if not _es_lista(magnitudes):
        return ["magnitudes debe ser una lista"]
    esperadas = list(rp.magnitudes_previstas())
    nombres = [m.get("magnitud") if isinstance(m, Mapping) else None for m in magnitudes]
    if nombres != esperadas:
        return [f"magnitudes debe cubrir exactamente {esperadas}, en orden"]

    fallos: list[str] = []
    for indice, magnitud in enumerate(magnitudes):
        etiqueta = f"magnitudes[{indice}]"
        ausentes = [c for c in CAMPOS_MAGNITUD if c not in magnitud]
        if ausentes:
            fallos.append(f"{etiqueta} sin campos {ausentes}")
            continue
        fallos.extend(_ajenos(magnitud, CAMPOS_MAGNITUD, etiqueta))
        p50 = magnitud["p50_por_sesion_ns"]
        p95 = magnitud["p95_por_sesion_ns"]
        if not _es_lista(p50) or len(p50) != rp.SESIONES_EXIGIDAS:
            fallos.append(f"{etiqueta}: p50 debe traer {rp.SESIONES_EXIGIDAS} valores")
            continue
        if not _es_lista(p95) or len(p95) != rp.SESIONES_EXIGIDAS:
            fallos.append(f"{etiqueta}: p95 debe traer {rp.SESIONES_EXIGIDAS} valores")
            continue
        if not all(_entero(v) and v >= 0 for v in [*p50, *p95]):
            fallos.append(f"{etiqueta}: los percentiles deben ser enteros de nanosegundos")
            continue
        for campo, esperado in (
            ("min_p50_ns", min(p50)),
            ("max_p50_ns", max(p50)),
            ("min_p95_ns", min(p95)),
            ("max_p95_ns", max(p95)),
        ):
            if magnitud[campo] != esperado:
                fallos.append(f"{etiqueta}.{campo} no recomputa desde los valores por sesion")
        if perfil is not None:
            fallos.extend(_fallos_veredicto(magnitud, etiqueta, p50, p95, perfil))
    return fallos


def _fallos_veredicto(
    magnitud: Mapping[str, Any],
    etiqueta: str,
    p50: Sequence[int],
    p95: Sequence[int],
    perfil: pp.Perfil,
) -> list[str]:
    """El veredicto se recomputa con el perfil aprobado, no se acepta."""
    try:
        veredicto = rp.evaluar_magnitud_rederivada(list(p50), list(p95), perfil=perfil)
    except (ValueError, ArithmeticError) as exc:
        return [f"{etiqueta}: el veredicto no se pudo recomputar ({exc})"]
    fallos: list[str] = []
    if magnitud["resultado"] != veredicto.resultado:
        fallos.append(
            f"{etiqueta}: veredicto publicado {magnitud['resultado']!r} distinto del "
            f"recomputado {veredicto.resultado!r}"
        )
    if magnitud["motivo"] != veredicto.motivo:
        fallos.append(f"{etiqueta}: motivo publicado distinto del recomputado")
    if magnitud["registro"] != pp.registro_por_percentil(veredicto):
        fallos.append(f"{etiqueta}: el registro por percentil no recomputa")
    # Con once sesiones deja de ser NO_COMPARABLE: es lo que la rederivacion
    # existe para conseguir, y si siguiera siendolo no habria servido de nada.
    if veredicto.resultado == pp.NO_COMPARABLE:
        fallos.append(
            f"{etiqueta}: sigue siendo NO_COMPARABLE pese a las once sesiones; la "
            f"rederivacion no habria cumplido su proposito"
        )
    return fallos


def _fallos_controles(doc: Mapping[str, Any]) -> list[str]:
    controles = doc.get("controles_internos")
    if not isinstance(controles, Mapping):
        return ["controles_internos ausente o con forma invalida"]
    fallos = _ajenos(controles, rp.CONTROLES_BLOQUEANTES, "controles_internos")
    fallos.extend(
        f"control bloqueante ausente o fallido: {c}"
        for c in rp.CONTROLES_BLOQUEANTES
        if controles.get(c) is not True
    )
    return fallos


def _fallos_negaciones(doc: Mapping[str, Any]) -> list[str]:
    no_autoriza = doc.get("no_autoriza")
    if not isinstance(no_autoriza, Mapping):
        return ["no_autoriza ausente o con forma invalida"]
    fallos = _ajenos(no_autoriza, NEGACIONES, "no_autoriza")
    fallos.extend(
        f"no_autoriza.{clave} debe ser False"
        for clave in NEGACIONES
        if no_autoriza.get(clave) is not False
    )
    return fallos
