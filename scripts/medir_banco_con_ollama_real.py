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

    uv run python scripts/medir_banco_con_ollama_real.py --modelo llama3.2 --espera 60

QUE MIRAR
=========

La cifra que manda es **omisiones críticas**: es lo que el propietario declaró
intolerable. ``elementos_de_mas`` es ruido tolerable. Y si el contador de
«rendiciones» no es cero, la medición está contaminada: parte de las consultas
no pasaron por el modelo y el número no vale.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from collections.abc import Sequence
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


class _FiltroQueSeDejaContar:
    """Envuelve el adaptador real y cuenta llamadas y rendiciones.

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

    def filter_candidates(
        self, query_text: str, candidates: Sequence[RankedKnowledge]
    ) -> Sequence[RankedKnowledge]:
        self.llamadas += 1
        resultado = self._real.filter_candidates(query_text, candidates)
        if candidates and resultado is candidates:
            self.rendiciones += 1
        return resultado


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
    args = parser.parse_args()

    contador = _FiltroQueSeDejaContar(
        OllamaRelevanceFilterAdapter(args.modelo, timeout_seconds=args.espera)
    )

    print(f"Modelo: {args.modelo}   Espera por consulta: {args.espera:g} s")
    print("Ejecutando los 47 casos contra el camino real. Esto tarda varios minutos.\n")

    comienzo = time.monotonic()
    with tempfile.TemporaryDirectory() as carpeta:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
