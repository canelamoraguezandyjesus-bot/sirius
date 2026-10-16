"""Pasa el banco de memoria por el camino real en este ordenador (E-R02-04, ADR-239).

POR QUÉ EXISTE
==============

El plan pide que el banco de 100 casos pase (§4, 0.2, «terminado cuando»), y
E-R02-04 lo mide en su ordenador con el modelo de huellas de verdad: 90 de 100,
con todos los de «olvida eso» y los de «quién dijo qué».

Cada caso es un Sirius nuevo, en una carpeta temporal que se borra al acabar:
nunca toca su ``sirius.db`` ni sus ajustes. Por el camino real:

1. Él dice cada cosa en la charla y la guarda con «Proponer guardar…», que él
   confirma. Lo que dijo Sirius («Sirius dijo que…») es una respuesta de Sirius,
   y guardarla así se rechaza: lo que dice Sirius nunca entra como suyo.
2. En «olvida eso», él dice «Olvida eso.» justo después de lo que hay que olvidar.
3. Él hace la pregunta, y se mira qué recuerdos llevó la petición al modelo.

El modelo de la charla no se usa: contesta un modelo de mentira, porque lo que se
mide es la memoria, no lo que contesta.

USO
===

    uv run python scripts/pasar_el_banco_de_memoria.py

Necesita Ollama abierto y el modelo de huellas instalado
(``ollama pull qwen3-embedding:0.6b``). Con ``--modelo NOMBRE`` lo pasa con otro
modelo de huellas de Ollama, sin tocar sus ajustes. Con ``--diagnostico`` escribe
además una línea por caso con lo que llegó al modelo, los puestos por palabras, los
parecidos de la pregunta y los recuerdos, como se piden hoy y con el formato que
recomienda el modelo, y el umbral en vigor (ADR-247): con ella se rehacen aquí
huellas con los mismos parecidos. Solo lleva el banco, que es inventado.
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import math
import shutil
import sqlite3
import sys
import tempfile
from collections.abc import Callable, Iterator, Sequence
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sirius.application.memory_search as memory_search
from sirius.adapters.llm.ollama_embeddings import OllamaEmbedder
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.sqlite_knowledge_search_repository import (
    build_sqlite_knowledge_search_repository,
)
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import (
    ConversationDependencies,
    build_conversation_dependencies,
    embedding_model,
)
from sirius.config.settings import load_settings
from sirius.domain.memory_bank import FAMILIES, MEMORY_BANK, NO_LO_SE, OLVIDA, QUIEN, MemoryCase
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.embeddings import EmbeddingError, TextEmbedder
from sirius.ports.llm import LLMCompleted, LLMRequest, LLMStreamEvent, LLMTextDelta

#: Lo que pide E-R02-04: 90 de 100, y todos los de estas dos familias.
APROBADO = 90
FAMILIAS_ENTERAS = (OLVIDA, QUIEN)

#: Así empieza lo que dijo Sirius en el banco.
_DIJO_SIRIUS = "Sirius dijo"

#: El formato que recomienda la ficha de cada modelo de huellas para buscar: cómo se pide
#: la pregunta y cómo los recuerdos. La búsqueda de hoy los pide tal cual.
FORMATOS: dict[str, tuple[str, str]] = {
    "qwen3-embedding": (
        "Instruct: Given a question, retrieve the memories that answer it\nQuery:{pregunta}",
        "{recuerdo}",
    ),
    "embeddinggemma": (
        "task: search result | query: {pregunta}",
        "title: none | text: {recuerdo}",
    ),
}

#: Lo que dice la primera línea de ``--diagnostico``: cómo se lee cada una de las demás.
CABECERA_DEL_DIAGNOSTICO = (
    "Diagnóstico: una línea por caso, en JSON. «traidos»: los recuerdos del caso que"
    " llegaron al modelo, en ese orden, por su número en el caso, desde 0. «esperado»: el"
    " que tenía que llegar el primero. «palabras»: el puesto de cada recuerdo en la búsqueda"
    " por palabras, 0 el mejor y null si no salió. «hoy»: el parecido de la pregunta con"
    " cada recuerdo, y el de cada par de recuerdos, pedidos como hoy. «formato»: lo mismo con"
    " el formato que recomienda el modelo, o null si no se conoce. «umbral»: el parecido"
    " mínimo en vigor."
)


@dataclass
class _ModeloDeMentira:
    """Hace de modelo de la charla: contesta lo que le toque, o «Vale.»."""

    model_name: str = "banco-de-memoria"
    siguientes: list[str] = field(default_factory=list)

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        del request
        texto = self.siguientes.pop(0) if self.siguientes else "Vale."
        yield LLMTextDelta(texto)
        yield LLMCompleted(text=texto, input_tokens=0, output_tokens=0)

    def cancel(self, operation_id: str) -> None:
        del operation_id


def es_de_sirius(recuerdo: str) -> bool:
    return recuerdo.startswith(_DIJO_SIRIUS)


def en_toda_la_base(base: Path, texto: str) -> list[str]:
    """Las columnas de TODA la base que contienen ``texto``, como la prueba de olvidar."""
    encontrados: list[str] = []
    with closing(sqlite3.connect(base)) as conexion:
        tablas = [
            fila[0]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        for tabla in tablas:
            columnas = [fila[1] for fila in conexion.execute(f'PRAGMA table_info("{tabla}")')]
            for columna in columnas:
                consulta = (
                    f'SELECT 1 FROM "{tabla}" WHERE CAST("{columna}" AS TEXT)'
                    " LIKE ? COLLATE NOCASE LIMIT 1"
                )
                if conexion.execute(consulta, (f"%{texto}%",)).fetchone():
                    encontrados.append(f"{tabla}.{columna}")
    return encontrados


class _Sirius:
    """Un Sirius de verdad en ``carpeta``, con el modelo de huellas dado."""

    def __init__(self, carpeta: Path, huellas: TextEmbedder) -> None:
        rutas = resolve_paths(carpeta)
        initialize_persistence(rutas)
        self.base = rutas.data_dir / "sirius.db"
        self.modelo = _ModeloDeMentira()
        self.deps: ConversationDependencies = build_conversation_dependencies(
            self.base,
            rutas.backups_dir,
            secret_store=FakeSecretStore(),
            text_embedder=huellas,
        )
        self.deps.send_message_use_case.set_llm_provider(self.modelo)
        proyecto = self.deps.initial_project_use_case
        if not proyecto.is_configured():
            proyecto.create_initial_project("Charla con Sirius", "Charlar con Sirius")

    def cierra(self) -> None:
        self.deps.close_database_connections()

    def dice_y_guarda(self, recuerdo: str) -> None:
        """Él lo dice y lo guarda con «Proponer guardar…», o Sirius lo dice."""
        if es_de_sirius(recuerdo):
            self.modelo.siguientes.append(recuerdo)
            respuesta = self.deps.send_message_use_case.send_message("¿Y tú qué dices?")
            mensaje = respuesta.sirius_message
        else:
            mensaje = self.deps.send_message_use_case.send_message(recuerdo).user_message
        sugerencia = self.deps.fact_proposals.propose_from_message(mensaje.id, recuerdo)
        if sugerencia is not None:
            self.deps.confirm_memory_suggestion_use_case.confirm(sugerencia.id)
        self.deps.memory_embedding_service.embed_pending()

    def pregunta(self, pregunta: str) -> list[str]:
        """Los recuerdos que llevó al modelo la petición de ``pregunta``, en su orden."""
        resultado = self.deps.send_message_use_case.send_message(pregunta)
        if resultado.context is None:
            return []
        return [memoria.current_revision.content or "" for memoria in resultado.context.memories]


def acierta(caso: MemoryCase, traidos: list[str], base: Path) -> bool:
    """Si lo que llevó la petición al modelo, ``traidos``, es lo que pide ``caso``."""
    if caso.family == OLVIDA:
        assert caso.forget is not None
        return caso.forget not in traidos and not en_toda_la_base(base, caso.forget)
    if caso.family == NO_LO_SE:
        return not set(traidos) & set(caso.memories)
    bien = traidos[:1] == [caso.expected]
    if caso.family == QUIEN:
        bien = bien and not any(es_de_sirius(traido) for traido in traidos)
    return bien


def formato_de(modelo: str) -> str | None:
    """Qué formato de ``FORMATOS`` recomienda ``modelo``, por su nombre en Ollama."""
    nombre = modelo.lower()
    return next((clave for clave in FORMATOS if clave in nombre), None)


def coseno(a: Sequence[float], b: Sequence[float]) -> float:
    """El parecido de dos huellas, el mismo que mide la búsqueda: su coseno."""
    normas = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / normas if normas else 0.0


def parecidos(huellas: TextEmbedder, pregunta: str, recuerdos: Sequence[str]) -> dict[str, Any]:
    """El parecido de ``pregunta`` con cada recuerdo, y el de cada par de recuerdos."""
    [suya, *de_ellos] = huellas.embed([pregunta, *recuerdos])
    return {
        "pregunta": [round(coseno(suya, huella), 4) for huella in de_ellos],
        "entre": {
            f"{i}{j}": round(coseno(de_ellos[i], de_ellos[j]), 4)
            for i, j in itertools.combinations(range(len(de_ellos)), 2)
        },
    }


def puestos_por_palabras(caso: MemoryCase, base: Path) -> list[int | None]:
    """El puesto de cada recuerdo del caso en la búsqueda por palabras del turno, o ``None``."""
    palabras = build_sqlite_knowledge_search_repository(base)
    try:
        encontrados = palabras.search_memory_ids(caso.question, memory_search.SEARCH_LIMIT)
    finally:
        palabras.close()
    with closing(sqlite3.connect(base)) as conexion:
        guardados: dict[str, int] = dict(
            conexion.execute(
                "SELECT r.content, m.id FROM memories AS m"
                " JOIN memory_revisions AS r ON r.memory_id = m.id AND r.is_current = 1"
                " WHERE m.status = 'current'"
            ).fetchall()
        )
    puestos = {memoria: puesto for puesto, memoria in enumerate(encontrados)}
    return [
        puestos.get(guardados[recuerdo]) if recuerdo in guardados else None
        for recuerdo in caso.memories
    ]


def diagnostico(
    caso: MemoryCase, traidos: list[str], base: Path, huellas: TextEmbedder, *, bien: bool
) -> dict[str, Any]:
    """Lo que pasó en ``caso`` por el camino real, para leerlo y reconstruirlo fuera."""
    formato: dict[str, Any] | None = None
    clave = formato_de(huellas.model_name)
    if clave is not None:
        molde_de_la_pregunta, molde_de_los_recuerdos = FORMATOS[clave]
        formato = {
            "nombre": clave,
            **parecidos(
                huellas,
                molde_de_la_pregunta.replace("{pregunta}", caso.question),
                [molde_de_los_recuerdos.replace("{recuerdo}", r) for r in caso.memories],
            ),
        }
    return {
        "id": caso.id,
        "familia": caso.family,
        "acierta": bien,
        "traidos": [caso.memories.index(t) if t in caso.memories else t for t in traidos],
        "esperado": caso.memories.index(caso.expected) if caso.expected is not None else None,
        "palabras": puestos_por_palabras(caso, base),
        "umbral": memory_search.MIN_SIMILARITY,
        "hoy": parecidos(huellas, caso.question, caso.memories),
        "formato": formato,
    }


def linea_del_diagnostico(caso: dict[str, Any]) -> str:
    return json.dumps(caso, ensure_ascii=False, separators=(",", ":"))


def pasa_un_caso(
    caso: MemoryCase,
    huellas: TextEmbedder,
    carpeta: Path,
    *,
    apunta: Callable[[dict[str, Any]], None] | None = None,
) -> bool:
    """Si Sirius acierta ``caso`` por el camino real; con ``apunta``, le da su diagnóstico."""
    sirius = _Sirius(carpeta, huellas)
    try:
        for recuerdo in caso.memories:
            sirius.dice_y_guarda(recuerdo)
        if caso.forget is not None:
            sirius.deps.send_message_use_case.send_message("Olvida eso.")
        traidos = sirius.pregunta(caso.question)
        bien = acierta(caso, traidos, sirius.base)
        if apunta is not None:
            apunta(diagnostico(caso, traidos, sirius.base, huellas, bien=bien))
        return bien
    finally:
        sirius.cierra()


def pasa_el_banco(
    huellas_de: Callable[[MemoryCase], TextEmbedder],
    carpeta: Path,
    *,
    casos: tuple[MemoryCase, ...] = MEMORY_BANK,
    apunta: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, tuple[int, int]]:
    """Aciertos y casos por familia, con un Sirius nuevo por caso.

    ``huellas_de`` da el modelo de huellas de cada caso: en su ordenador, el mismo
    para todos; en las pruebas, uno de mentira hecho para ese caso. ``apunta`` recibe
    el diagnóstico de cada caso, si se le da.
    """
    cuenta = {familia: [0, 0] for familia in FAMILIES}
    for numero, caso in zip(itertools.count(1), casos, strict=False):
        bien = pasa_un_caso(caso, huellas_de(caso), carpeta / f"{numero:03d}", apunta=apunta)
        cuenta[caso.family][0] += int(bien)
        cuenta[caso.family][1] += 1
    return {familia: (aciertos, total) for familia, (aciertos, total) in cuenta.items()}


def aprueba(resultado: dict[str, tuple[int, int]]) -> bool:
    aciertos = sum(acertados for acertados, _ in resultado.values())
    enteras = all(resultado[f][0] == resultado[f][1] for f in FAMILIAS_ENTERAS)
    return aciertos >= APROBADO and enteras


def opciones() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pasar_el_banco_de_memoria",
        description="Pasa el banco de memoria de E-R02-04 por el camino real.",
    )
    parser.add_argument(
        "--modelo", help="el modelo de huellas de Ollama; sin él, el de tus ajustes, que no cambian"
    )
    parser.add_argument(
        "--diagnostico",
        action="store_true",
        help="además, una línea por caso con lo que llegó al modelo y los parecidos",
    )
    return parser


def main(
    argv: Sequence[str] = (),
    huellas_de: Callable[[str], TextEmbedder] = OllamaEmbedder,
    escribe: Callable[[str], None] = print,
    *,
    casos: tuple[MemoryCase, ...] = MEMORY_BANK,
) -> int:
    """0 si pasa, 1 si no, 2 si falta el modelo de huellas."""
    elegidas = opciones().parse_args(list(argv))
    modelo = elegidas.modelo or embedding_model(load_settings())
    huellas = huellas_de(modelo)
    try:
        huellas.embed(["hola"])
    except EmbeddingError:
        escribe(f"No hay modelo de huellas. Abre Ollama y ejecuta: ollama pull {modelo}")
        return 2

    def apunta(caso: dict[str, Any]) -> None:
        escribe(linea_del_diagnostico(caso))

    if elegidas.diagnostico:
        escribe(CABECERA_DEL_DIAGNOSTICO)
    carpeta = Path(tempfile.mkdtemp(prefix="sirius-banco-"))
    try:
        resultado = pasa_el_banco(
            lambda _caso: huellas,
            carpeta,
            casos=casos,
            apunta=apunta if elegidas.diagnostico else None,
        )
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)
    for familia, (aciertos, total) in resultado.items():
        escribe(f"{familia}: {aciertos} de {total}")
    aciertos = sum(acertados for acertados, _ in resultado.values())
    escribe(f"En total: {aciertos} de {len(casos)}, con el modelo de huellas {modelo}.")
    if aprueba(resultado):
        escribe("Pasa.")
        return 0
    escribe("No pasa: hacen falta 90 de 100 y todos los de «olvida eso» y «quién dijo qué».")
    return 1


if __name__ == "__main__":
    logging.disable(logging.WARNING)
    sys.exit(main(sys.argv[1:]))
