"""Mide UNA configuración del investigador contra el banco de respuestas conocidas.

Cierra el número que S2 dejó sin medir. El spike I2 (#351) dejó escrito lo que le
faltaba, con estas palabras: *«ni una sola pregunta se ha respondido de verdad»*.
Esto responde preguntas de verdad y cuenta cuántas acierta.

**Corre UNA configuración y sale.** La comparación entre dos la hace
``comparar_investigadores.py``, y lo hace lanzando este guion **en procesos
separados**. No es una manía de diseño: es la única forma de que la comparación
no sea mentira. Medido hoy sobre `gpt-researcher` 0.15.1:

- El proveedor de modelo lee ``OPENAI_BASE_URL`` cuando el proveedor es
  ``openai`` (`llm_provider/generic/base.py`), y
- el de vectorización hace lo mismo (`memory/embeddings.py`).

Es decir: **las dos configuraciones se pisan las variables**. Una vía compatible
con OpenAI —NVIDIA, por ejemplo— secuestra ``OPENAI_BASE_URL`` para todo el
proceso, así que si dos configuraciones compartieran entorno, la segunda hablaría
con el servidor de la primera **y el informe saldría precioso**. Un verde que
mide dos veces lo mismo es exactamente la familia de defecto que este repositorio
persigue: no falla, miente.

Por eso este guion **construye su entorno desde cero** y declara en su salida
contra qué servidor habló, para que la comparación pueda demostrarlo en vez de
prometerlo.

Salida: un JSON por stdout. Nunca imprime la clave.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parents[2]
PREGUNTAS = Path(__file__).resolve().parent / "preguntas.yml"

#: La versión medida como buena. La 0.16.0 **no llega ni a importarse**: usa `Any`
#: sin importarlo en `actions/query_processing.py`. Medido el 26-08-2026, y por eso
#: aquí hay un número y no un rango.
VERSION_EXIGIDA = "0.15.1"


@dataclass
class ResultadoPregunta:
    id: str
    tipo: str
    texto: str
    acierta: bool
    obligatorias_encontradas: list[str]
    obligatorias_ausentes: list[str]
    fuentes: int
    segundos: float
    error: str | None
    informe: str


@dataclass
class ResultadoConfiguracion:
    configuracion: str
    proveedor_declarado: str
    servidor: str
    modelo_rapido: str
    modelo_listo: str
    vectorizacion: str
    buscador: str
    version_herramienta: str
    aciertos: int
    total: int
    porcentaje: float
    segundos_totales: float
    # LO QUE OCURRIO, no lo que se pidio. Estos cuatro campos son la correccion
    # de la raiz que la refutacion del 26-08-2026 destapo: sin ellos, el arnes
    # solo sabia repetir su propia configuracion.
    preguntas_con_error: int
    preguntas_sin_fuentes: int
    fuentes_totales: int
    medicion_fiable: bool
    motivo_no_fiable: str | None
    preguntas: list[dict[str, Any]]


def _cargar_preguntas() -> list[dict[str, Any]]:
    datos = yaml.safe_load(PREGUNTAS.read_text(encoding="utf-8"))
    return list(datos["preguntas"])


def _version_instalada() -> str:
    import importlib.metadata as metadata

    return metadata.version("gpt-researcher")


def _corrige(informe: str, obligatorias: list[str]) -> tuple[bool, list[str], list[str]]:
    """Corrección determinista, cruda y declarada como tal — pero por PALABRA.

    REFUTADO EL 26-08-2026 Y CORREGIDO. La primera versión buscaba subcadena:
    ``o.lower() in informe.lower()``. Medido por el refutador y comprobado a
    mano:

        _corrige("uv is a tool you can trust", ["Rust"])          -> True
        _corrige("the Apache Foundation is unrelated", ["Apache"]) -> True

    «trust» contiene «rust». Y como el texto corregido incluye las URLs de las
    fuentes, cualquier enlace a `apache.org` aprobaba la pregunta de la licencia
    sin que el informe dijera nada. Ahora se exige **límite de palabra**.

    Lo que sigue sin hacer, y se dice para que nadie lo lea de más: no juzga la
    calidad de la redacción ni si el dato está sostenido por las fuentes, solo
    si aparece como palabra. Un corrector fino exigiría otro modelo juzgando, y
    entonces mediríamos al juez. El informe entero se conserva para que quien
    dude lo lea.
    """
    encontradas: list[str] = []
    ausentes: list[str] = []
    for obligatoria in obligatorias:
        patron = re.compile(rf"(?<!\w){re.escape(obligatoria)}(?!\w)", re.IGNORECASE)
        (encontradas if patron.search(informe) else ausentes).append(obligatoria)
    return (not ausentes), encontradas, ausentes


async def _investigar(pregunta: str) -> tuple[str, int]:
    """Una pregunta, con la herramienta real. Devuelve informe y nº de fuentes."""
    from gpt_researcher import GPTResearcher

    investigador = GPTResearcher(query=pregunta, report_type="research_report")
    await investigador.conduct_research()
    informe = await investigador.write_report()
    try:
        fuentes = len(investigador.get_source_urls())
    except Exception:
        fuentes = 0
    return str(informe), fuentes


def medir(configuracion: str) -> ResultadoConfiguracion:
    version = _version_instalada()
    if version != VERSION_EXIGIDA:
        # Se para en vez de medir: la 0.16.0 ni importa, y una versión no medida
        # daría un número sobre algo que nadie ha comprobado que funcione.
        raise SystemExit(
            f"gpt-researcher instalado: {version}, exigido: {VERSION_EXIGIDA}. "
            "La 0.16.0 no llega ni a importarse (NameError: Any). Se para en vez "
            "de medir sobre una versión sin comprobar."
        )

    resultados: list[ResultadoPregunta] = []
    arranque = time.monotonic()
    for pregunta in _cargar_preguntas():
        inicio = time.monotonic()
        error: str | None = None
        informe, fuentes = "", 0
        try:
            informe, fuentes = asyncio.run(_investigar(str(pregunta["texto"])))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        acierta, encontradas, ausentes = _corrige(informe, list(pregunta["obligatorias"]))
        resultados.append(
            ResultadoPregunta(
                id=str(pregunta["id"]),
                tipo=str(pregunta["tipo"]),
                texto=str(pregunta["texto"]),
                # TRES condiciones, y la tercera es la que arregla la raiz.
                #
                # 1. Sin error: un error nunca es un acierto.
                # 2. Con informe: `_corrige("")` con obligatorias vacias devolveria
                #    True, o sea un 100 % construido sobre cero texto.
                # 3. CON FUENTES. Esta es la nueva, y es la que mata a toda la
                #    familia de defectos que la refutacion encontro. Sin `ddgs`
                #    instalado el buscador no arranca, el modelo escribe de
                #    memoria y el informe SALE PERFECTO: la respuesta esta ahi
                #    porque el modelo se la sabe, no porque se haya investigado.
                #    Exigir `fuentes > 0` es lo unico que distingue «investigo y
                #    acerto» de «se lo sabia». Sin esta linea, un buscador muerto
                #    daba 100 %.
                acierta=bool(acierta and error is None and informe.strip() and fuentes > 0),
                obligatorias_encontradas=encontradas,
                obligatorias_ausentes=ausentes,
                fuentes=fuentes,
                segundos=round(time.monotonic() - inicio, 1),
                error=error,
                informe=informe,
            )
        )

    aciertos = sum(1 for r in resultados if r.acierta)
    total = len(resultados)
    con_error = sum(1 for r in resultados if r.error is not None)
    sin_fuentes = sum(1 for r in resultados if r.fuentes == 0)
    fuentes_totales = sum(r.fuentes for r in resultados)

    # POR QUE UNA MEDICION PUEDE NO SER FIABLE, y por que hay que decirlo aparte
    # del porcentaje. Un 0 % puede significar dos cosas opuestas: «contesto mal»
    # o «no llego a intentarlo». Confundirlas es el criterio de parada (c) de la
    # nota de arranque, y era exactamente lo que este guion hacia antes.
    motivo: str | None = None
    if total == 0:
        motivo = "el banco de preguntas esta vacio: no se midio nada"
    elif fuentes_totales == 0:
        motivo = (
            "ninguna pregunta trajo ni una sola fuente: el buscador no funciono. "
            "Los informes salen del modelo, no de la investigacion, asi que el "
            "porcentaje no mide al investigador. Comprueba que `ddgs` este "
            "instalado: gpt-researcher lo importa pero declara `duckduckgo-search`."
        )
    elif con_error == total:
        motivo = "todas las preguntas fallaron: no hay nada medido"

    return ResultadoConfiguracion(
        configuracion=configuracion,
        proveedor_declarado=os.environ.get("SIRIUS_PROVEEDOR", "(sin declarar)"),
        # LO QUE DE VERDAD SE USÓ, no lo que se pidió: es lo único que demuestra
        # que dos configuraciones hablaron con servidores distintos.
        servidor=os.environ.get("OPENAI_BASE_URL", "(por defecto del proveedor)"),
        modelo_rapido=os.environ.get("FAST_LLM", "(por defecto)"),
        modelo_listo=os.environ.get("SMART_LLM", "(por defecto)"),
        vectorizacion=os.environ.get("EMBEDDING", "(por defecto)"),
        buscador=os.environ.get("RETRIEVER", "(por defecto)"),
        version_herramienta=version,
        aciertos=aciertos,
        total=total,
        porcentaje=round(100.0 * aciertos / total, 1) if total else 0.0,
        segundos_totales=round(time.monotonic() - arranque, 1),
        preguntas_con_error=con_error,
        preguntas_sin_fuentes=sin_fuentes,
        fuentes_totales=fuentes_totales,
        medicion_fiable=motivo is None,
        motivo_no_fiable=motivo,
        preguntas=[asdict(r) for r in resultados],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mide UNA configuración del investigador contra el banco de S2."
    )
    parser.add_argument("configuracion", help="nombre legible de esta configuración")
    parser.add_argument("--salida", default=None, help="fichero JSON donde escribir")
    args = parser.parse_args(argv)

    resultado = medir(args.configuracion)
    texto = json.dumps(asdict(resultado), ensure_ascii=False, indent=2)
    if args.salida:
        Path(args.salida).write_text(texto, encoding="utf-8")
    sys.stdout.write(texto + "\n")

    # EL CODIGO DE SALIDA DEJA DE MENTIR. Antes devolvia 0 pasara lo que pasara,
    # y el comparador decidia «medida valida» solo con verlo. Es decir: cinco
    # preguntas reventadas, cero fuentes, y una comparacion concluyente.
    #
    # Ahora 3 significa «no me creas»: se midio algo, pero no lo que se queria
    # medir. El JSON sale igual -contiene el motivo y los informes-, porque un
    # fallo que no deja rastro es peor que el fallo.
    if not resultado.medicion_fiable:
        sys.stderr.write(f"MEDICION NO FIABLE: {resultado.motivo_no_fiable}\n")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
