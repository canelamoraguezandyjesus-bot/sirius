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

M19a (ADR-127, incidencia #512) cerró la causa (a): ``RankRelevantKnowledgeUseCase``
gana un segundo bloque de ampliación, ``solo_por_criticidad``, sobre
``Memory.criticality``/``Decision.criticality`` (M18b, ADR-126) y su propio
vocabulario (``composition_root._CRITICALITY_VOCABULARY``, portado literal del
laboratorio) — la variante ``hoy`` de este guion pasa a ejercitarlo por
defecto (`_ejecutar_banco_paquete_completo`` ya construye
``RankRelevantKnowledgeUseCase`` con ``criticality_vocabulary=
_CRITICALITY_VOCABULARY``). M19b (ADR-128, incidencia #514) cerró la causa
(b): la regla de rescate RF-25/RF-26 y la prioridad de G12 pasaron a mirar,
con la puerta abierta, ``criticality is not None`` en vez del tema — la
categoría de máxima criticidad (``_MAX_CRITICALITY_CATEGORY``) ya solo
gobierna el candado del camino cerrado.

M20 (ADR-129, incidencia #516, Decisión 2 del propietario del 02-09-2026)
porta la siembra en contexto (``RankRelevantKnowledgeUseCase.
_rank_via_staged_engine``'s tercer bloque, ``siembra``): activada por el
PROPÓSITO de la petición (``pide_contexto``), no por vocabulario, y
``_peticion_ordinaria`` declara el mismo propósito fijo para las 47
consultas del banco — así que, desde este encargo, la variante ``hoy`` (y
también ``A_porte_fiel``/``B_arreglo_ingenuo``, que comparten el mismo
``criticality`` real por item) siembra en cada una de las 47 consultas, no
solo en las dos que el arnés de examen declara con propósito de contexto.
Las tres ``NO_ENTRO`` bajan a **0** (las tres pérdidas de B04-CA-34 que
M19a/M19b dejaban sin cerrar) y ``elementos_de_mas`` sube sin cota, tal como
predecía la incidencia #516: la siembra mete en cada consulta todo lo no
ordinario del ámbito, y este guion mide sin filtro (el doble nunca poda).

Este guion mide **qué haría cada forma de marcar lo crítico** sobre el arnés
de producción real, sin reimplementar nada: solo le inyecta al arnés otro
vocabulario, otra asignación de categoría y otra categoría de máxima
criticidad (parámetros opcionales de ``_ejecutar_banco_paquete_completo`` que
por defecto conservan el comportamiento — desde M19a, ``hoy`` incluido).

Corre **sin Ollama**: el filtro es el doble que nunca descarta. Por eso solo
puede ver la mitad de búsqueda (``NO_ENTRO``); no puede ver la de rescate
(RF-25/RF-26). Es deliberado: la búsqueda es determinista y se puede
medir en cualquier máquina; el filtro se mide aparte con Ollama.

LAS VARIANTES
=============

- ``hoy``: producción real, desde M19a — etiquetas canónicas de tema
  (ADR-116) **más** el índice de criticidad (M19a) sobre
  ``criticidad.nivel`` del canon; máxima criticidad ``salud`` para el
  candado del camino cerrado (M19b no toca ese candado; con la puerta
  abierta, que este guion no ejercita, el rescate ya mira criticidad).
- ``A_porte_fiel``: la semántica del laboratorio, portada tal cual: categoría
  ``restriccion`` **solo** para los items con criticidad declarada (CRITICO o
  IMPORTANTE), ``None`` para el resto; vocabulario del laboratorio (las cinco
  palabras con las que alguien pide lo crítico); máxima criticidad
  ``restriccion``. Desde M19a ya no aporta nada distinto de ``hoy`` en
  búsqueda (las cuatro métricas de ``NO_ENTRO``/cobertura/exactos coinciden):
  la única diferencia que le queda es la categoría derivada de criticidad,
  que ``hoy`` no tiene — y por eso ``elementos_de_mas`` difiere entre las dos
  (``hoy`` sigue trayendo también lo hallado por el índice de categoría
  temático, que ``A_porte_fiel`` sustituye en vez de sumar).
- ``B_arreglo_ingenuo``: lo que haría quien solo añadiera palabras al índice
  de categoría existente en vez de crear uno propio de criticidad: etiquetas
  de tema para todo (como hoy) + las cinco palabras del laboratorio sumadas
  al vocabulario de categoría. Máxima criticidad ``salud`` (como hoy). Sigue
  sirviendo de control negativo: confirma con datos por qué M19a no fusionó
  los dos vocabularios en un único índice.

PREDICCION HISTORICA, ESCRITA ANTES DE EJECUTAR M19a (ADR-127, ADR-001)
========================================================================

- ``hoy``: las críticas ``NO_ENTRO`` bajan de 9 a **3** (quedan solo las tres
  de B04-CA-34: DEC-003, MEM-014, MEM-016 — la siembra, M20, no el índice),
  cobertura 62 → **68/81**, elementos de más ≤ 300.
- ``A_porte_fiel``: sin cambio respecto a la medición de M18b (260 elementos
  de más, 3 ``NO_ENTRO``, 68/81) — este encargo no toca esa variante.
- ``B_arreglo_ingenuo``: sus ``NO_ENTRO`` también bajan a 3 (mismo vocabulario
  de criticidad que activa el índice de categoría existente), pero sus
  elementos de más siguen muy por encima de ``hoy``/``A``: fusionar
  vocabularios en el índice de categoría trae todo el ámbito, ordinario
  incluido, en vez de solo lo no ordinario.

Esa predicción se cumplió sin ajustar el vocabulario (ver ADR-127/ADR-128).

VERDAD NUEVA TRAS M20 (ADR-129, incidencia #516)
=================================================

Con la siembra en contexto portada y activa en las 47 consultas (ver arriba,
"M20" en el docstring del módulo), las tres variantes miden ``hoy`` = **0**
``NO_ENTRO`` (las tres pérdidas de B04-CA-34 ya se siembran), cobertura
**72/81**, y ``elementos_de_mas`` sube sin cota respecto a la medición de
M19a/M19b — predicho por la incidencia #516 y no motivo de parada: la
siembra mete en cada consulta todo lo no ordinario del ámbito, y este guion
mide sin filtro (el doble nunca poda ese ruido).

Si ``hoy`` no baja a 0 ``NO_ENTRO``, o si algún caso PIERDE una crítica que
antes tenía, se para y se busca la raíz (regla de las dos rondas, ADR-001).

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
    print(
        "  Verdad nueva tras M20 (ADR-129, incidencia #516): hoy=0 NO_ENTRO "
        "(72/81), A=0, B=0 (sin cambio entre variantes: la siembra siembra "
        "igual en las tres) -- 'de mas' sube sin cota, previsto y no motivo "
        "de parada."
    )
    print("  Sin Ollama solo se ve la etapa de busqueda (NO_ENTRO): la de rescate se mide aparte.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
