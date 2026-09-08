"""Mide el intérprete de peticiones (ADR-164, palanca 1 de ADR-148) contra el
banco de 47 casos, con Ollama de verdad.

POR QUE EXISTE
==============

La prueba de aceptación de la palanca 1 son las 47 ``peticion_p2`` del banco
campo a campo, y la inferencia de modo, cardinalidad, límite y tiempo la hace
el modelo local, que **no está en CI**. ADR-148 ya preveía separar las dos
medidas, y ADR-164 lo cumple así:

- **en CI, determinista** (``tests/unit/test_interpret_query_request.py``,
  ``tests/unit/test_ollama_query_intent_classifier.py`` y las cinco pruebas
  de ADR-164 en ``tests/integration/test_rank_relevant_knowledge.py`` —las
  tres de la ronda 1, la de las tres escrituras del corte y la del corte con
  desfase negativo—): la parte por reglas —permiso y propósito—, la forma de
  la ``Peticion`` y el cableado, con un doble del modelo;
- **aquí, con Ollama real en la máquina del propietario**: la coincidencia
  campo a campo con las 47 y las cuatro cifras del banco.

Esta medición NO la cierra el ciclo: la ejecuta el propietario, y la palanca 1
no se da por cerrada hasta que él la corra.

USO
===

    uv run python scripts/medir_interprete_de_peticion.py
    uv run python scripts/medir_interprete_de_peticion.py --modelo llama3.2

PREDICCION, ESCRITA ANTES DE EJECUTARLA (ADR-164, nota de arranque)
===================================================================

    exactas >= 16/47; de mas <= 162; criticas perdidas = 0; hallados >= 73/81
    coincidencia campo a campo >= 45/47

Si sale por debajo, se registra el número tal cual y se para: no se ajusta la
predicción después de verla.

QUE COMPARA, Y QUE NO
=====================

Compara los cinco campos que el modelo infiere: modo (y su consecuencia
``admite_no_vigentes``), cardinalidad, límite, tiempo objetivo y corte de
registro. NO compara el propósito ni el ámbito: el propósito por caso del
banco (``planificar_viaje``, ``verificar_fuente``…) es una declaración del
caso, no algo derivable de la frase, y en producción lo fija la regla del
producto (ADR-164); el ámbito lo resuelve el llamador contra los proyectos
reales, igual en las dos peticiones. Tampoco ``objetivos``, que en el banco
es adjudicación (``max(1, len(resultado_esperado))``).

El límite se compara en su significado, no en su número: el banco usa el
tamaño del canon como "límite que no ata" y el intérprete usa su propia
constante, así que "no ata" se normaliza a ``None`` en los dos lados. El
tiempo se compara como instante, no como cadena: ``…Z``, ``…+00:00`` y una
forma sin zona (que se lee como UTC) son el mismo instante.

Cada caso se interroga UNA sola vez: la petición interpretada se reutiliza
para las dos medidas, así que el guion hace 47 llamadas a Ollama, no 94.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ))
sys.path.insert(0, str(_RAIZ / "src"))
sys.path.insert(0, str(_RAIZ / "tests" / "acceptance"))

from scripts.diagnosticar_busqueda_del_banco import _ambito_de_produccion, _medir  # noqa: E402
from tests.acceptance.staged_engine_case_translation import peticion_desde_caso  # noqa: E402

from sirius.adapters.ollama_query_intent_classifier import (  # noqa: E402
    OllamaQueryIntentClassifierAdapter,
    instante_utc,
)
from sirius.application.interpret_query_request import (  # noqa: E402
    LIMITE_SIN_ATAR,
    InterpreteDePeticion,
)
from sirius.domain.staged_engine_contracts import Peticion  # noqa: E402

_BANCO = _RAIZ / "tests" / "acceptance" / "fixtures" / "evidence_bank_47_casos.json"
_MODELO_POR_DEFECTO = "qwen3:4b-instruct"

#: Los campos que el modelo infiere y que, por tanto, esta medición compara.
_CAMPOS = ("modo", "admite_no_vigentes", "cardinalidad", "limite", "tiempo_objetivo", "corte")


class _RelojDelBanco:
    """El «ahora» declarado del fixture, no el de la máquina: el banco fija
    su propio presente y comparar contra el reloj real mediría el día en que
    se ejecuta la medición."""

    def __init__(self, ahora: str) -> None:
        momento = instante_utc(ahora)
        if momento is None:
            raise ValueError(f"«ahora» del banco no es un ISO-8601 reconocible: {ahora!r}")
        self._ahora = momento

    def utc_now(self) -> datetime:
        return self._ahora


def _instante(valor: str | None) -> datetime | None:
    """El instante que la cadena nombra, con UTC asumido si no declara zona.

    Es la misma normalización que el adaptador usa para emitirlos
    (``sirius.adapters.ollama_query_intent_classifier.instante_utc``), y se
    comparte a propósito: el lado del banco siempre trae ``Z`` y sale
    consciente, mientras que el intérprete puede emitir una forma sin zona.
    Comparar un ingenuo con un consciente por ``!=`` no lanza —da siempre
    «distintos»—, así que sin asumir la zona un instante semánticamente
    idéntico se puntuaría como fallo.
    """
    return instante_utc(valor)


def _limite_normalizado(peticion: Peticion, sin_atar: int) -> int | None:
    """El límite en su significado: ``None`` cuando no ata."""
    if peticion.limite_objetivo >= sin_atar:
        return None
    return peticion.limite_objetivo


def _campos(peticion: Peticion, *, sin_atar: int) -> dict[str, Any]:
    return {
        "modo": peticion.modo,
        "admite_no_vigentes": peticion.admite_no_vigentes,
        "cardinalidad": peticion.cardinalidad,
        "limite": _limite_normalizado(peticion, sin_atar),
        "tiempo_objetivo": _instante(peticion.ventana.tiempo_objetivo),
        "corte": _instante(peticion.ventana.corte_de_registro),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", default=_MODELO_POR_DEFECTO)
    argumentos = parser.parse_args()

    banco = json.loads(_BANCO.read_text(encoding="utf-8"))
    casos = banco["casos"]
    limite_sin_atar_del_banco = int(banco["conteos"]["items_del_canon"])
    ahora = str(banco["ahora_declarado"])

    interprete = InterpreteDePeticion(
        intent_classifier=OllamaQueryIntentClassifierAdapter(argumentos.modelo, ahora=ahora[:10]),
        clock=_RelojDelBanco(ahora),
    )

    print("=" * 74)
    print(f"[interprete={argumentos.modelo}] 47 consultas, una llamada por caso")
    print("=" * 74)

    interpretadas: dict[str, Peticion] = {}
    aciertos_por_campo = dict.fromkeys(_CAMPOS, 0)
    exactas = 0
    for caso in casos:
        consulta = str(caso["consulta"])
        interpretada = interprete.interpretar(
            consulta, f"rank:{consulta[:64]}", active_project_id=None
        )
        interpretadas[consulta] = interpretada
        declarada = peticion_desde_caso(
            caso,
            operation_id=f"rank:{consulta[:64]}",
            ambito=_ambito_de_produccion(None),
            limite_sin_atar=limite_sin_atar_del_banco,
        )
        obtenidos = _campos(interpretada, sin_atar=LIMITE_SIN_ATAR)
        esperados = _campos(declarada, sin_atar=limite_sin_atar_del_banco)
        distintos = [campo for campo in _CAMPOS if obtenidos[campo] != esperados[campo]]
        for campo in _CAMPOS:
            if campo not in distintos:
                aciertos_por_campo[campo] += 1
        if not distintos:
            exactas += 1
            continue
        print(f"[{caso['id']}] {consulta!r}")
        for campo in distintos:
            print(f"   {campo}: esperado={esperados[campo]!r} obtenido={obtenidos[campo]!r}")

    print("-" * 74)
    print(f"COINCIDENCIA CAMPO A CAMPO: {exactas}/{len(casos)} peticiones idénticas")
    for campo in _CAMPOS:
        print(f"   {campo}: {aciertos_por_campo[campo]}/{len(casos)}")
    print("=" * 74)

    def peticion_interpretada(
        query_text: str, operation_id: str, *, active_project_id: int | None
    ) -> Peticion:
        """La petición ya interpretada arriba, con el ámbito real que
        producción deriva del proyecto activo. Sin caso —no debería
        ocurrir—, se interroga al modelo otra vez."""
        cacheada = interpretadas.get(query_text)
        if cacheada is None:
            return interprete.interpretar(
                query_text, operation_id, active_project_id=active_project_id
            )
        return replace(
            cacheada,
            operation_id=operation_id,
            ambito=_ambito_de_produccion(active_project_id),
        )

    ejecucion, entradas, _ = _medir(
        banco, con_ejes=False, con_peticion=False, peticion_alternativa=peticion_interpretada
    )
    if len(entradas) != len(casos):
        msg = f"el filtro vio {len(entradas)} consultas y el banco tiene {len(casos)}"
        raise RuntimeError(msg)
    m = ejecucion.metricas
    print(
        f"[interprete] SIN FILTRO: {m.aciertos_exactos}/47 exactos; "
        f"{m.elementos_de_mas} de mas; {m.elementos_hallados}/81 hallados; "
        f"omisiones criticas={m.omisiones_criticas}"
    )
    print("PREDICCION (ADR-164): >=16/47; <=162 de mas; 0 criticas perdidas; >=73/81 hallados")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
