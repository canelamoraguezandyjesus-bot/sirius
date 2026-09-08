"""Techo de la ETAPA DE BÚSQUEDA del banco de 47 casos, caso por caso y sin Ollama.

POR QUE EXISTE
==============

``scripts/medir_variantes_de_criticidad.py`` imprime totales de la etapa de
búsqueda (sin filtro: el doble nunca descarta) y solo localiza las críticas
perdidas. Este guion baja al caso: qué esperaba cada consulta, qué no entró
(id, tipo, nivel, validez, confirmación, autoridad) y cuánto sobró. Y mide el
techo de dos palancas que producción no tiene y el laboratorio sí (ADR-148):

- ``--ejes``: los ejes declarados de cada ítem del corpus (vigencia,
  autoridad, sensibilidad...) entran en el puerto del motor por
  ``ejes_por_identidad``; producción entrega todo ítem con ``SIN_EJES``
  (``src/sirius/adapters/persistence/staged_engine_port.py``).
- ``--peticion``: la petición real de cada caso (``peticion_p2``: modo,
  permiso, cardinalidad, tiempo objetivo, corte de registro) sustituye a la
  política uniforme de ``_peticion_ordinaria``
  (``src/sirius/application/rank_relevant_knowledge.py``), conservando el
  ámbito que producción deriva del proyecto activo.

Reutiliza ``_ejecutar_banco_paquete_completo`` sin reimplementarlo — la única
forma de no medir otra cosa por accidente — e inyecta las dos palancas por
parches sobre nombres de módulo, restaurados al salir. Corre sin Ollama: solo
ve la etapa de búsqueda. Nunca lee ``criticidad.razon_segura``.

USO
===

    uv run python scripts/diagnosticar_busqueda_del_banco.py [--ejes] [--peticion]

Medido el 05-09-2026 sobre ``a07c5d5`` (ADR-148): sin banderas 0/47 exactos,
487 de más, 72/81; ``--ejes`` 0/47, 421, 71/81; ``--peticion`` 16/47, 162,
73/81; ``--ejes --peticion`` 20/47, 144, 73/81; críticas perdidas 0 en las
cuatro configuraciones.
"""

from __future__ import annotations

import json
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ))
sys.path.insert(0, str(_RAIZ / "src"))
sys.path.insert(0, str(_RAIZ / "tests" / "acceptance"))

import tests.acceptance.test_pa_0_2_rec_01_banco_evidencia as arnes  # noqa: E402
from tests.acceptance.staged_engine_case_translation import peticion_desde_caso  # noqa: E402

import sirius.application.rank_relevant_knowledge as recuperacion  # noqa: E402
from sirius.domain.relevance import RankedKnowledge  # noqa: E402
from sirius.domain.staged_engine_contracts import Ambito, Peticion  # noqa: E402

_BANCO = _RAIZ / "tests" / "acceptance" / "fixtures" / "evidence_bank_47_casos.json"
Clave = tuple[str, int]


class _FiltroQueNoDescartaYRecuerda:
    """El doble de producción (conserva todo) que además recuerda qué entró."""

    def __init__(self) -> None:
        self.entradas: list[list[Clave]] = []

    def filter_candidates(
        self, query_text: str, candidates: Sequence[RankedKnowledge]
    ) -> Sequence[RankedKnowledge]:
        self.entradas.append([(c.kind.value, c.item_id) for c in candidates])
        return candidates


def _ambito_de_produccion(active_project_id: int | None) -> Ambito:
    """La misma regla que ``_peticion_ordinaria`` (M16): el ámbito real."""
    if active_project_id is None:
        return Ambito(global_=True, proyectos=())
    return Ambito(global_=False, proyectos=(str(active_project_id),))


def _medir(
    banco: Mapping[str, Any], *, con_ejes: bool, con_peticion: bool
) -> tuple[Any, list[list[Clave]], dict[str, int]]:
    casos = banco["casos"]
    consultas = [caso["consulta"] for caso in casos]
    if len(set(consultas)) != len(consultas):
        msg = "el banco tiene consultas repetidas; la petición por caso sería ambigua"
        raise RuntimeError(msg)
    casos_por_consulta = {caso["consulta"]: caso for caso in casos}
    limite_sin_atar = int(banco["conteos"]["items_del_canon"])

    registro: dict[Clave, Mapping[str, Any]] = {}
    cargador_original = arnes._load_canon_item
    puerto_original = arnes.build_staged_engine_port
    peticion_original = recuperacion._peticion_ordinaria
    llamadas = {"peticiones": 0, "sin_caso": 0}

    def cargar_y_registrar(item: Mapping[str, Any], **kw: Any) -> Clave | None:
        real = cargador_original(item, **kw)
        if real is not None:
            registro[real] = item
        return real

    def puerto_con_ejes(database_path: Path, **kw: Any) -> Any:
        ejes = {
            arnes._identidad_del_motor(kind, real_id): arnes._ejes_declarados(item)
            for (kind, real_id), item in registro.items()
        }
        return puerto_original(database_path, ejes_por_identidad=ejes)

    def peticion_del_caso(
        query_text: str, operation_id: str, *, active_project_id: int | None
    ) -> Peticion:
        llamadas["peticiones"] += 1
        caso = casos_por_consulta.get(query_text)
        if caso is None:
            llamadas["sin_caso"] += 1
            return peticion_original(query_text, operation_id, active_project_id=active_project_id)
        return peticion_desde_caso(
            caso,
            operation_id=operation_id,
            ambito=_ambito_de_produccion(active_project_id),
            limite_sin_atar=limite_sin_atar,
        )

    filtro = _FiltroQueNoDescartaYRecuerda()
    arnes._load_canon_item = cargar_y_registrar
    if con_ejes:
        arnes.build_staged_engine_port = puerto_con_ejes
    if con_peticion:
        recuperacion._peticion_ordinaria = peticion_del_caso
    try:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
            ejecucion = arnes._ejecutar_banco_paquete_completo(
                Path(carpeta) / "diagnostico.db", relevance_filter_port=filtro
            )
    finally:
        arnes._load_canon_item = cargador_original
        arnes.build_staged_engine_port = puerto_original
        recuperacion._peticion_ordinaria = peticion_original
    return ejecucion, filtro.entradas, llamadas


def main() -> int:
    con_ejes = "--ejes" in sys.argv[1:]
    con_peticion = "--peticion" in sys.argv[1:]
    banco = json.loads(_BANCO.read_text(encoding="utf-8"))
    items = {item["id"]: item for item in banco["items"]}
    casos = banco["casos"]
    criticos = frozenset(
        item["id"]
        for item in banco["items"]
        if (item.get("criticidad") or {}).get("nivel") == "CRITICO"
    )

    ejecucion, entradas, llamadas = _medir(banco, con_ejes=con_ejes, con_peticion=con_peticion)
    if len(entradas) != len(casos):
        msg = f"el filtro vio {len(entradas)} consultas y el banco tiene {len(casos)}"
        raise RuntimeError(msg)

    m = ejecucion.metricas
    etiqueta = f"ejes={'si' if con_ejes else 'no'} peticion={'real' if con_peticion else 'fija'}"
    print("=" * 74)
    print(
        f"[{etiqueta}] SIN FILTRO: {m.aciertos_exactos}/47 exactos; "
        f"{m.elementos_de_mas} de mas; {m.elementos_hallados}/81 hallados; "
        f"omisiones criticas={m.omisiones_criticas}"
    )
    if con_peticion:
        print(f"   peticiones del caso: {llamadas['peticiones']}; sin caso: {llamadas['sin_caso']}")
    print("=" * 74)

    faltan_total: dict[str, list[str]] = {}
    criticas_perdidas: list[tuple[str, str]] = []
    extras_por_caso: list[tuple[str, int, int]] = []
    for caso, entraron_raw in zip(casos, entradas, strict=True):
        entraron = {
            ejecucion.real_a_canonico[c] for c in entraron_raw if c in ejecucion.real_a_canonico
        }
        esperados = list(caso["resultado_esperado"])
        faltan = [e for e in esperados if e not in entraron]
        extras = sorted(entraron - set(esperados))
        extras_por_caso.append((caso["id"], len(extras), len(esperados)))
        for identidad in faltan:
            faltan_total.setdefault(identidad, []).append(caso["id"])
            if identidad in criticos:
                criticas_perdidas.append((caso["id"], identidad))
        if not faltan:
            continue
        p2 = caso["peticion_p2"]
        print(
            f"[{caso['id']}] {p2['modo']} {p2['proposito']} permiso={p2['permiso']} "
            f"cardinalidad={p2['cardinalidad']} corte={p2['corte_registro']}"
        )
        print(f"   consulta = {caso['consulta']!r}")
        print(
            f"   faltan={faltan} entraron={[e for e in esperados if e in entraron]} "
            f"extras={len(extras)}"
        )
        for identidad in faltan:
            item = items.get(identidad, {})
            ejes = item.get("ejes_p2") or {}
            print(
                f"   FALTA {identidad} [{item.get('kind')}, "
                f"nivel={(item.get('criticidad') or {}).get('nivel')}, "
                f"validez={item.get('validez')}, confirmacion={item.get('confirmacion')}, "
                f"autoridad={ejes.get('autoridad')}]"
            )

    print("-" * 74)
    ocurrencias = sum(len(v) for v in faltan_total.values())
    print(
        f"RESUMEN [{etiqueta}]: distintos no encontrados={len(faltan_total)}; "
        f"ocurrencias={ocurrencias}; criticas perdidas={len(criticas_perdidas)} "
        f"{criticas_perdidas}"
    )
    extras_por_caso.sort(key=lambda t: -t[1])
    total_extras = sum(n for _, n, _ in extras_por_caso)
    sin_extras = sum(1 for _, n, _ in extras_por_caso if n == 0)
    print(
        f"extras: total={total_extras}; media={total_extras / len(extras_por_caso):.1f}; "
        f"casos con 0 extras={sin_extras}; peores={extras_por_caso[:6]}"
    )
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
