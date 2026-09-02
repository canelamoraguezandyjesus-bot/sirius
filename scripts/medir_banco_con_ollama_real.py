"""Mide el banco de 47 casos contra el camino real de producción, con Ollama de verdad.

POR QUE EXISTE
==============

Hay tres arneses en el repositorio y **ninguno llama a Ollama**:

- el arnés de examen usa ``filtro_congelado_conserva``, una grabación de una
  corrida real;
- ``_ejecutar_banco_paquete_completo`` usa ``_FiltroDeRelevanciaQueNuncaDescarta``,
  un doble que conserva todo;
- el banco de latencia mide tiempos, no aciertos.

Así que la pregunta «¿cuánto acierta Sirius de verdad, con el modelo puesto?»
nunca se ha respondido. Este guion la responde: reutiliza el MISMO arnés de
producción —no reimplementa nada— y solo le cambia el filtro por el adaptador
real.

No es una prueba de ``pytest`` a propósito: necesita Ollama arrancado y tarda
minutos, así que se ejecuta a mano cuando se quiere medir.

USO
===

    uv run python scripts/medir_banco_con_ollama_real.py
    uv run python scripts/medir_banco_con_ollama_real.py --diagnostico
    uv run python scripts/medir_banco_con_ollama_real.py --modelo llama3.2 --espera 60

QUE MIRAR
=========

La cifra que manda es **omisiones críticas**: es lo que el propietario declaró
intolerable. ``elementos_de_mas`` es ruido tolerable. Y si el contador de
«rendiciones» no es cero, la medición está contaminada: parte de las consultas
no pasaron por el modelo y el número no vale.

``--diagnostico`` responde a la pregunta siguiente: de cada crítica perdida,
**en qué etapa se perdió** — nunca llegó al filtro (búsqueda), el filtro la tiró
y nadie la rescató, o sobrevivió al filtro y se perdió después. Y lo compara con
lo que el laboratorio perdió en su fila equivalente.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_RAIZ))
sys.path.insert(0, str(_RAIZ / "src"))
# El módulo del banco importa sus vecinos por nombre suelto
# (``staged_engine_case_translation``), como hace ``pytest`` con el directorio
# de la prueba en la ruta. Fuera de ``pytest`` hay que ponerlo a mano.
sys.path.insert(0, str(_RAIZ / "tests" / "acceptance"))

from tests.acceptance.test_pa_0_2_rec_01_banco_evidencia import (  # noqa: E402
    _ejecutar_banco_paquete_completo,
)

from sirius.adapters.ollama_relevance_filter import (  # noqa: E402
    OllamaRelevanceFilterAdapter,
)
from sirius.domain.relevance import RankedKnowledge  # noqa: E402
from sirius.ports.relevance_filter import RelevanceFilterPort  # noqa: E402

#: Suelo D1 publicado, para poder comparar de un vistazo. No se afirma aquí:
#: este guion mide y publica, no aprueba ni suspende (ADR-001).
_SUELO_ACIERTOS = 29
_SUELO_CRITICAS = 1
_SUELO_COBERTURA = 63

_BANCO = _RAIZ / "tests" / "acceptance" / "fixtures" / "evidence_bank_47_casos.json"

#: Lo que el laboratorio perdió en su fila equivalente a producción —«4. filtro
#: con regla, con categoría», SIN siembra— leído de
#: ``resultado_modelo_local_v0.7.json`` (rama ``evidence/adr001-spikes``,
#: ``detalle_por_caso``), traducido con la correspondencia que declara
#: ``tests/acceptance/fixtures/relevance_filter_frozen_run.json``
#: (``N1-NN -> B04-CA-NN``, ``MEMORIA:n -> MEM-nnn``, ``DECISION:n -> DEC-nnn``)
#: y contando como crítico lo mismo que el arnés (``criticidad.nivel == CRITICO``).
#: Las cuatro son ``NO_ENTRO``: nunca llegaron al filtro. El laboratorio publica
#: 5 con su propia lista de críticos; con la del banco son estas 4.
_LABORATORIO_FILA_4: Mapping[str, Mapping[str, str]] = {
    "B04-CA-33": {"DEC-003": "NO_ENTRO"},
    "B04-CA-34": {"DEC-003": "NO_ENTRO", "MEM-014": "NO_ENTRO", "MEM-016": "NO_ENTRO"},
}

Clave = tuple[str, int]


class _FiltroQueSeDejaContar:
    """Envuelve el adaptador real; cuenta llamadas y rendiciones y recuerda
    qué entró y qué salió en cada llamada.

    NO se cuenta leyendo el registro: ``alembic`` reconfigura ``logging`` al
    aplicar las migraciones y desactiva los ``logger`` ya existentes, así que
    un contador enganchado ahí devolvía cero aunque el filtro se estuviera
    rindiendo en todas las consultas. Un cero falso en esta cifra es peor que
    no tenerla: haría pasar por buena una medición inválida.

    La distinción se hace por identidad del objeto, que es exacta: el
    adaptador devuelve **la misma tupla** que recibió cuando falla abierto
    (``except Exception: return candidates``) y construye una **tupla nueva**
    cuando el modelo contestó, aunque conserve todos los candidatos.
    """

    def __init__(self, real: RelevanceFilterPort) -> None:
        self._real = real
        self.llamadas = 0
        self.rendiciones = 0
        #: Por llamada, en orden: (entraron, salieron) como claves (kind, id).
        self.trazas: list[tuple[frozenset[Clave], frozenset[Clave]]] = []

    def filter_candidates(
        self, query_text: str, candidates: Sequence[RankedKnowledge]
    ) -> Sequence[RankedKnowledge]:
        self.llamadas += 1
        resultado = self._real.filter_candidates(query_text, candidates)
        if candidates and resultado is candidates:
            self.rendiciones += 1
        self.trazas.append((_claves(candidates), _claves(resultado)))
        return resultado


def _claves(candidatos: Sequence[RankedKnowledge]) -> frozenset[Clave]:
    return frozenset((c.kind.value, c.item_id) for c in candidatos)


def _etapa(identidad: str, entraron: frozenset[str], salieron: frozenset[str]) -> str:
    if identidad not in entraron:
        return "NO_ENTRO"
    if identidad not in salieron:
        return "TIRADO_POR_EL_FILTRO"
    return "PERDIDO_TRAS_FILTRO"


def _diagnostico(
    contador: _FiltroQueSeDejaContar,
    obtenido_por_caso: Mapping[str, frozenset[str]],
    real_a_canonico: Mapping[Clave, str],
) -> None:
    banco = json.loads(_BANCO.read_text(encoding="utf-8"))
    criticos = {
        item["id"]
        for item in banco["items"]
        if (item.get("criticidad") or {}).get("nivel") == "CRITICO"
    }
    casos = banco["casos"]
    if len(contador.trazas) != len(casos):
        print()
        print(
            f"  DIAGNOSTICO NO POSIBLE: {len(contador.trazas)} llamadas al filtro para "
            f"{len(casos)} casos. La correlacion llamada<->caso exige exactamente una "
            "llamada por caso (contrato de _apply_relevance_filter)."
        )
        return

    def traducir(claves: frozenset[Clave]) -> frozenset[str]:
        return frozenset(real_a_canonico[c] for c in claves if c in real_a_canonico)

    filas: list[tuple[str, str, str, str]] = []
    resumen_prod: dict[str, int] = {}
    resumen_lab: dict[str, int] = {}
    for caso, (entraron_raw, salieron_raw) in zip(casos, contador.trazas, strict=True):
        caso_id = caso["id"]
        esperadas = [x for x in caso["resultado_esperado"] if x in criticos]
        if not esperadas:
            continue
        entraron = traducir(entraron_raw)
        salieron = traducir(salieron_raw)
        obtenido = obtenido_por_caso.get(caso_id, frozenset())
        lab = _LABORATORIO_FILA_4.get(caso_id, {})
        for identidad in esperadas:
            en_prod = "OK" if identidad in obtenido else _etapa(identidad, entraron, salieron)
            en_lab = lab.get(identidad, "OK")
            if en_prod != "OK" or en_lab != "OK":
                filas.append((caso_id, identidad, en_lab, en_prod))
            if en_prod != "OK":
                resumen_prod[en_prod] = resumen_prod.get(en_prod, 0) + 1
            if en_lab != "OK":
                resumen_lab[en_lab] = resumen_lab.get(en_lab, 0) + 1

    print()
    print("=" * 62)
    print("DIAGNOSTICO: DONDE SE PIERDE CADA CRITICA")
    print("=" * 62)
    print(f"  {'caso':10} {'critica':9} {'laboratorio (fila 4)':22} produccion (hoy)")
    print(f"  {'-' * 10} {'-' * 9} {'-' * 22} {'-' * 22}")
    for caso_id, identidad, en_lab, en_prod in filas:
        print(f"  {caso_id:10} {identidad:9} {en_lab:22} {en_prod}")
    print()
    print("  NO_ENTRO ............. la busqueda nunca la puso delante del filtro")
    print("  TIRADO_POR_EL_FILTRO . el modelo la descarto y ninguna regla la rescato")
    print("  PERDIDO_TRAS_FILTRO .. sobrevivio al filtro y se perdio despues")
    print()
    n_lab = sum(resumen_lab.values())
    n_prod = sum(resumen_prod.values())
    print(f"  Laboratorio, fila 4:  {n_lab} criticas perdidas  {dict(resumen_lab)}")
    print(f"  Produccion, hoy:      {n_prod} criticas perdidas  {dict(resumen_prod)}")
    tiradas = resumen_prod.get("TIRADO_POR_EL_FILTRO", 0)
    if tiradas:
        print()
        print(f"  {tiradas} criticas las TIRO EL FILTRO y la regla de las criticas no las rescato.")
        print("  Motivo comprobado en el codigo: la regla protege la categoria")
        print("  'salud' (composition_root._MAX_CRITICALITY_CATEGORY) y ninguna critica")
        print("  del banco esta etiquetada 'salud' (personal/finanzas/proyecto/trabajo).")
        print("  En el laboratorio la categoria se DERIVA de la criticidad, asi que la")
        print("  misma regla protegia todo lo no ordinario. En produccion no protege nada.")
    print("=" * 62)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--modelo",
        default="qwen3:4b-instruct",
        help="Modelo de Ollama. Por defecto el que midió el laboratorio.",
    )
    parser.add_argument(
        "--espera",
        type=float,
        default=30.0,
        help="Segundos de espera por consulta antes de rendirse.",
    )
    parser.add_argument(
        "--diagnostico",
        action="store_true",
        help="Ademas de las metricas, decir en que etapa se perdio cada critica.",
    )
    args = parser.parse_args()

    contador = _FiltroQueSeDejaContar(
        OllamaRelevanceFilterAdapter(args.modelo, timeout_seconds=args.espera)
    )

    print(f"Modelo: {args.modelo}   Espera por consulta: {args.espera:g} s")
    print("Ejecutando los 47 casos contra el camino real. Esto tarda varios minutos.\n")

    comienzo = time.monotonic()
    # ``ignore_cleanup_errors``: en Windows no se puede borrar un fichero que
    # sigue abierto, y las conexiones de SQLite del arnés aún lo están al
    # salir del bloque. Sin esto, la limpieza revienta DESPUÉS de haber
    # medido y antes de imprimir nada: se pierde una medición de minutos por
    # un fichero temporal que da igual.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as carpeta:
        ejecucion = _ejecutar_banco_paquete_completo(
            Path(carpeta) / "banco.db",
            relevance_filter_port=contador,
        )
    duracion = time.monotonic() - comienzo
    m = ejecucion.metricas

    def veredicto(valor: int, suelo: int, *, menor_es_mejor: bool = False) -> str:
        alcanza = valor <= suelo if menor_es_mejor else valor >= suelo
        return "ALCANZA" if alcanza else "por debajo"

    print("=" * 62)
    print("RESULTADO SOBRE EL BANCO DE 47 CASOS, CON OLLAMA REAL")
    print("=" * 62)
    print(f"  Aciertos exactos ...... {m.aciertos_exactos}/47")
    print(
        f"      suelo D1: {_SUELO_ACIERTOS}/47 -> {veredicto(m.aciertos_exactos, _SUELO_ACIERTOS)}"
    )
    print(f"  Omisiones criticas .... {m.omisiones_criticas}   <- LA QUE IMPORTA")
    print(
        f"      suelo D1: {_SUELO_CRITICAS} o menos -> "
        f"{veredicto(m.omisiones_criticas, _SUELO_CRITICAS, menor_es_mejor=True)}"
    )
    print(f"  Cobertura ............. {m.elementos_hallados}/{m.elementos_esperados_total}")
    print(
        f"      suelo D1: {_SUELO_COBERTURA} -> {veredicto(m.elementos_hallados, _SUELO_COBERTURA)}"
    )
    print(f"  Elementos de mas ...... {m.elementos_de_mas}   (ruido tolerable)")
    print()
    print(f"  Tiempo total .......... {duracion / 60:.1f} min")
    print(f"  Llamadas al filtro .... {contador.llamadas}")
    print(f"  Rendiciones del filtro. {contador.rendiciones}")
    if contador.llamadas == 0:
        print()
        print("  AVISO: el filtro no se llamo ni una vez. Esta medicion NO prueba nada")
        print("  sobre el filtro; mide el mismo camino que sin el.")
    elif contador.rendiciones:
        print()
        print("  AVISO: el filtro se rindio en algunas consultas, asi que estas cifras")
        print("  mezclan consultas filtradas con consultas sin filtrar. NO son validas.")
        print("  Sube --espera y vuelve a medir.")
    print("=" * 62)

    if args.diagnostico:
        _diagnostico(contador, ejecucion.obtenido_por_caso, ejecucion.real_a_canonico)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
