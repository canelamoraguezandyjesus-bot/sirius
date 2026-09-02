"""Mide, sobre el camino real, qué pasaría con cada forma de marcar lo crítico.

POR QUE EXISTE
==============

``scripts/medir_banco_con_ollama_real.py --diagnostico`` midió (02-09-2026, en
la máquina del propietario, 0 rendiciones) que producción pierde 10 críticas
del banco de 47 frente a las 4 del laboratorio con la misma receta, y localizó
la causa en una sola decisión de ADR-116: la categoría de producción es un
**tema** (``trabajo``, ``personal``, ``salud``…) mientras que la del
laboratorio se **deriva de la criticidad** (``restriccion`` para todo lo no
ordinario, ``None`` para lo ordinario). Con eso, (a) las consultas que piden
«restricciones» no activan el índice de categoría —9 pérdidas ``NO_ENTRO``— y
(b) la regla de rescate RF-25/RF-26, que protege ``"salud"``, no protege
ninguna crítica del banco —1 pérdida ``TIRADO_POR_EL_FILTRO``—.

Antes de que el propietario decida cómo marcar lo crítico en producción, este
guion mide **qué haría cada opción** sobre el arnés de producción real, sin
reimplementar nada: solo le inyecta al arnés otro vocabulario, otra asignación
de categoría y otra categoría de máxima criticidad (parámetros opcionales de
``_ejecutar_banco_paquete_completo`` que por defecto conservan el comportamiento
de hoy).

Corre **sin Ollama**: el filtro es el doble que nunca descarta. Por eso solo
puede ver la mitad de búsqueda (``NO_ENTRO``), que es la mitad grande (9 de 10),
y no puede ver la de rescate. Es deliberado: la búsqueda es determinista y se
puede medir en cualquier máquina; el filtro se mide aparte con Ollama.

LAS VARIANTES
=============

- ``hoy``: exactamente producción (etiquetas canónicas de tema, vocabulario de
  ADR-116, máxima criticidad ``salud``).
- ``A_porte_fiel``: la semántica del laboratorio, portada tal cual: categoría
  ``restriccion`` **solo** para los items con criticidad declarada (CRITICO o
  IMPORTANTE), ``None`` para el resto; vocabulario del laboratorio (las cinco
  palabras con las que alguien pide lo crítico); máxima criticidad
  ``restriccion``.
- ``B_arreglo_ingenuo``: lo que haría quien solo añadiera palabras: etiquetas
  de tema para todo (como hoy) + las cinco palabras del laboratorio sumadas al
  vocabulario. Máxima criticidad ``salud`` (como hoy).

PREDICCION, ESCRITA ANTES DE EJECUTAR (ADR-001)
===============================================

- ``hoy``: 9 críticas ``NO_ENTRO`` (lo ya medido; sirve de control).
- ``A_porte_fiel``: las críticas ``NO_ENTRO`` bajan a **4** —las mismas cuatro
  que pierde el laboratorio (B04-CA-33 DEC-003; B04-CA-34 DEC-003, MEM-014,
  MEM-016)— porque las cinco de B04-CA-31 y la de B04-CA-02 entran por el
  índice al activarse con «restricciones». Los elementos de más suben respecto
  a ``hoy`` (el índice ahora sí trae lo no ordinario del ámbito), pero no
  explotan: solo lo no ordinario lleva categoría.
- ``B_arreglo_ingenuo``: las ``NO_ENTRO`` también bajan (el índice se activa),
  pero los elementos de más **se disparan** muy por encima de ``A``: en
  producción **todo** item lleva etiqueta de tema, así que activar el índice
  trae todo lo del ámbito, ordinario incluido. Si esta predicción se cumple,
  «añadir palabras» queda descartado con datos.

Si ``A`` no baja a 4, la causa de las 9 no es (solo) el vocabulario y este
guion lo habrá dicho antes de que nadie construya nada.

USO
===

    uv run python scripts/medir_variantes_de_criticidad.py
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

from tests.acceptance.staged_engine_category_and_relevance import (  # noqa: E402
    CATEGORIA_DE_MAXIMA_CRITICIDAD,
    VOCABULARIO_DE_CATEGORIA,
    categoria_del_item,
)
from tests.acceptance.test_pa_0_2_rec_01_banco_evidencia import (  # noqa: E402
    _ejecutar_banco_paquete_completo,
)

from sirius.composition_root import (  # noqa: E402
    _CATEGORY_VOCABULARY,
    _MAX_CRITICALITY_CATEGORY,
)
from sirius.domain.relevance import RankedKnowledge  # noqa: E402

_BANCO = _RAIZ / "tests" / "acceptance" / "fixtures" / "evidence_bank_47_casos.json"
Clave = tuple[str, int]


class _FiltroQueNoDescartaYRecuerda:
    """El doble de producción (conserva todo) que además recuerda qué entró:
    con él, toda crítica perdida es ``NO_ENTRO`` por construcción, que es la
    única etapa que este guion mide."""

    def __init__(self) -> None:
        self.entradas: list[frozenset[Clave]] = []

    def filter_candidates(
        self, query_text: str, candidates: Sequence[RankedKnowledge]
    ) -> Sequence[RankedKnowledge]:
        self.entradas.append(frozenset((c.kind.value, c.item_id) for c in candidates))
        return candidates


def _medir(
    nombre: str,
    *,
    vocabulario: frozenset[str] | None,
    categoria_por_item: Any,
    maxima: str | None,
    banco: Mapping[str, Any],
    criticos: frozenset[str],
) -> tuple[str, Any, list[tuple[str, str]]]:
    filtro = _FiltroQueNoDescartaYRecuerda()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
        ejecucion = _ejecutar_banco_paquete_completo(
            Path(carpeta) / f"{nombre}.db",
            relevance_filter_port=filtro,
            category_vocabulary=vocabulario,
            categoria_por_item=categoria_por_item,
            max_criticality_category=maxima,
        )
    perdidas: list[tuple[str, str]] = []
    casos = banco["casos"]
    if len(filtro.entradas) == len(casos):
        for caso, entraron_raw in zip(casos, filtro.entradas, strict=True):
            entraron = {
                ejecucion.real_a_canonico[c] for c in entraron_raw if c in ejecucion.real_a_canonico
            }
            for identidad in caso["resultado_esperado"]:
                if identidad in criticos and identidad not in entraron:
                    perdidas.append((caso["id"], identidad))
    return nombre, ejecucion.metricas, perdidas


def main() -> int:
    banco = json.loads(_BANCO.read_text(encoding="utf-8"))
    criticos = frozenset(
        item["id"]
        for item in banco["items"]
        if (item.get("criticidad") or {}).get("nivel") == "CRITICO"
    )

    variantes = [
        _medir(
            "hoy",
            vocabulario=None,
            categoria_por_item=None,
            maxima=None,
            banco=banco,
            criticos=criticos,
        ),
        _medir(
            "A_porte_fiel",
            vocabulario=VOCABULARIO_DE_CATEGORIA,
            categoria_por_item=categoria_del_item,
            maxima=CATEGORIA_DE_MAXIMA_CRITICIDAD,
            banco=banco,
            criticos=criticos,
        ),
        _medir(
            "B_arreglo_ingenuo",
            vocabulario=_CATEGORY_VOCABULARY | VOCABULARIO_DE_CATEGORIA,
            categoria_por_item=None,
            maxima=_MAX_CRITICALITY_CATEGORY,
            banco=banco,
            criticos=criticos,
        ),
    ]

    print()
    print("=" * 74)
    print("QUE HARIA CADA FORMA DE MARCAR LO CRITICO (camino real, sin filtro)")
    print("=" * 74)
    print(f"  {'variante':18} {'exactos':>8} {'de mas':>7} {'crit perdidas':>14} {'cobertura':>10}")
    print(f"  {'-' * 18} {'-' * 8} {'-' * 7} {'-' * 14} {'-' * 10}")
    for nombre, m, perdidas in variantes:
        print(
            f"  {nombre:18} {m.aciertos_exactos:>5}/47 {m.elementos_de_mas:>7} "
            f"{len(perdidas):>14} {m.elementos_hallados:>7}/81"
        )
    print()
    for nombre, _m, perdidas in variantes:
        print(f"  {nombre}: criticas NO_ENTRO = {len(perdidas)}")
        for caso_id, identidad in perdidas:
            print(f"      {caso_id}  {identidad}")
    print()
    print("  Prediccion escrita antes de ejecutar: hoy=9, A=4, B baja pero dispara 'de mas'.")
    print("  Sin Ollama solo se ve la etapa de busqueda (NO_ENTRO): la de rescate se mide aparte.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
