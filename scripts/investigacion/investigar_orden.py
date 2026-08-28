"""El hijo que investiga UNA pregunta de una orden. Corre en el entorno medido.

Es el hermano de ``medir_investigador.py`` para B1 (ADR-099): mismo entorno,
misma herramienta, mismo tipo de informe (``research_report``, el ÚNICO con
número: 7/7 en el banco, run 33141864710) y el mismo conteo de fuentes —la
unión deduplicada de los dos registros (PR #382)—. No mide contra un banco:
contesta la pregunta del ``## Objetivo`` de una incidencia y deja informe y
fuentes en un JSON para que el padre (``atender_orden.py``) componga el
documento.

Nunca imprime la clave. El plazo lo aplica dentro (``asyncio.wait_for``),
para morir escribiendo su JSON en vez de que lo mate el padre con todo dentro
—la lección de la pasada 3 del banco—.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from medir_investigador import VERSION_EXIGIDA, _urls_de_fuentes, _version_instalada


async def _investigar(pregunta: str) -> tuple[str, list[str]]:
    from gpt_researcher import GPTResearcher

    investigador = GPTResearcher(query=pregunta, report_type="research_report")
    await investigador.conduct_research()
    informe = await investigador.write_report()
    # La MISMA unión que decide `fuentes > 0` en el banco (PR #382): listar los
    # enlaces con otra lógica que la del conteo sería tener dos verdades.
    return str(informe), sorted(_urls_de_fuentes(investigador))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Investiga UNA pregunta y deja un JSON.")
    parser.add_argument("--pregunta", required=True)
    parser.add_argument("--salida", required=True)
    parser.add_argument("--plazo", type=int, default=1200, help="segundos como mucho")
    args = parser.parse_args(argv)

    version = _version_instalada()
    if version != VERSION_EXIGIDA:
        raise SystemExit(
            f"gpt-researcher instalado: {version}, exigido: {VERSION_EXIGIDA}. "
            "Se para en vez de investigar sobre una versión sin medir."
        )

    resultado: dict[str, Any] = {
        "pregunta": args.pregunta,
        "informe": "",
        "fuentes": [],
        "error": None,
        "cortada_por_plazo": False,
    }
    codigo = 0
    try:
        informe, fuentes = asyncio.run(
            asyncio.wait_for(_investigar(args.pregunta), timeout=args.plazo)
        )
        resultado["informe"] = informe
        resultado["fuentes"] = fuentes
        if not informe.strip():
            resultado["error"] = "la herramienta devolvió un informe vacío"
            codigo = 3
        elif not fuentes:
            # La regla de la casa, aplicada a las órdenes igual que al banco:
            # sin fuentes, el texto sale del modelo y NO es una investigación.
            resultado["error"] = (
                "cero fuentes: el texto saldría de la memoria del modelo, no de "
                "investigar. No se publica un informe recitado."
            )
            codigo = 3
    except TimeoutError:
        resultado["cortada_por_plazo"] = True
        resultado["error"] = (
            f"la investigación pasó de {args.plazo} s y se cortó. NO es una "
            "respuesta equivocada: es que no llegó a terminar."
        )
        codigo = 3
    except Exception as exc:
        resultado["error"] = f"{type(exc).__name__}: {exc}"
        codigo = 3

    Path(args.salida).write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if resultado["error"]:
        sys.stderr.write(str(resultado["error"]) + "\n")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
