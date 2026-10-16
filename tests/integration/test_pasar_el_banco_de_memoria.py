"""El diagnóstico del banco de memoria y el modelo elegido en las dos órdenes (ADR-247).

En su ordenador las ejecuta él, con su modelo de huellas de verdad, y la línea de cada
caso se lee aquí. Aquí se comprueba con huellas de mentira de parecidos sabidos que la
línea dice lo que pasó por el camino real y que se puede reconstruir.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

import medir_busqueda_de_memoria as busqueda
import pasar_el_banco_de_memoria as orden
import sirius.application.memory_search as memory_search
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.config.settings import load_settings, save_settings
from sirius.domain.memory_bank import MEMORY_BANK
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.embeddings import EmbeddingError

pytestmark = pytest.mark.integration

[_MB_001] = [caso for caso in MEMORY_BANK if caso.id == "MB-001"]
_HERMANA, _MOTO, _CAFE = _MB_001.memories
_PREGUNTA = _MB_001.question

#: Huellas de largos distintos, para que el producto no se confunda con el parecido.
#: Con ellas, hoy: la pregunta se parece 0,8 a la hermana, 0 a la moto y 0,6 al café; la
#: hermana y el café, 0,48. Con el formato de Qwen, la pregunta se parece 0,96, 0 y 0,36.
#: Con el de EmbeddingGemma, 1, 0 y 0,7071; la hermana y el café, 0,7071.
_HUELLAS: dict[str, list[float]] = {
    _PREGUNTA: [2.0, 0.0, 0.0, 0.0],
    _HERMANA: [1.6, 1.2, 0.0, 0.0],
    _MOTO: [0.0, 0.0, 3.0, 0.0],
    _CAFE: [0.3, 0.0, 0.0, 0.4],
    f"Instruct: Given a question, retrieve the memories that answer it\nQuery:{_PREGUNTA}": [
        1.8,
        2.4,
        0.0,
        0.0,
    ],
    f"task: search result | query: {_PREGUNTA}": [0.0, 0.0, 0.0, 1.0],
    f"title: none | text: {_HERMANA}": [0.0, 0.0, 0.0, 2.0],
    f"title: none | text: {_MOTO}": [0.0, 1.0, 0.0, 0.0],
    f"title: none | text: {_CAFE}": [0.0, 0.0, 1.0, 1.0],
}


class _Huellas:
    """Huellas de mentira: las sabidas de MB-001, y para lo demás, unas sacadas del texto."""

    def __init__(self, model: str, *, falla: bool = False) -> None:
        self.model_name = model
        self.falla = falla
        self.pedidas: list[str] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if self.falla:
            msg = "sin Ollama"
            raise EmbeddingError(msg)
        self.pedidas.extend(texts)
        return [
            _HUELLAS.get(t) or [b / 255 for b in hashlib.sha256(t.encode()).digest()[:4]]
            for t in texts
        ]


def _diagnostico_de_mb_001(tmp_path: Path, modelo: str) -> tuple[dict[str, Any], _Huellas]:
    huellas = _Huellas(modelo)
    lineas: list[dict[str, Any]] = []

    acierta = orden.pasa_un_caso(_MB_001, huellas, tmp_path / "caso", apunta=lineas.append)

    [linea] = lineas
    assert linea["acierta"] is acierta
    return linea, huellas


def test_la_linea_de_un_caso_conocido_dice_lo_que_paso_por_el_camino_real(
    tmp_path: Path,
) -> None:
    linea, _ = _diagnostico_de_mb_001(tmp_path, "qwen3-embedding:0.6b")

    assert linea == {
        "id": "MB-001",
        "familia": "personas",
        "acierta": True,
        "traidos": [0, 2],
        "esperado": 0,
        "palabras": [0, None, None],
        "umbral": 0.5,
        "hoy": {"pregunta": [0.8, 0.0, 0.6], "entre": {"01": 0.0, "02": 0.48, "12": 0.0}},
        "formato": {
            "nombre": "qwen3-embedding",
            "pregunta": [0.96, 0.0, 0.36],
            "entre": {"01": 0.0, "02": 0.48, "12": 0.0},
        },
    }
    # Escrita como sale, una línea que se lee de vuelta igual.
    texto = orden.linea_del_diagnostico(linea)
    assert "\n" not in texto
    assert json.loads(texto) == linea


def test_con_embeddinggemma_pide_la_pregunta_y_los_recuerdos_con_su_formato(
    tmp_path: Path,
) -> None:
    linea, huellas = _diagnostico_de_mb_001(tmp_path, "embeddinggemma:300m")

    assert linea["formato"] == {
        "nombre": "embeddinggemma",
        "pregunta": [1.0, 0.0, 0.7071],
        "entre": {"01": 0.0, "02": 0.7071, "12": 0.0},
    }
    assert f"task: search result | query: {_PREGUNTA}" in huellas.pedidas
    assert f"title: none | text: {_HERMANA}" in huellas.pedidas
    # Lo de hoy se sigue pidiendo tal cual: el formato es solo para medirlo.
    assert linea["hoy"]["pregunta"] == [0.8, 0.0, 0.6]


def test_con_un_modelo_sin_formato_conocido_no_se_lo_inventa(tmp_path: Path) -> None:
    linea, _ = _diagnostico_de_mb_001(tmp_path, "nomic-embed-text")

    assert linea["formato"] is None
    assert orden.formato_de("Qwen3-Embedding:4B") == "qwen3-embedding"


def test_la_linea_lleva_el_umbral_en_vigor_y_lo_que_trajo_con_el(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(memory_search, "MIN_SIMILARITY", 0.7)

    linea, _ = _diagnostico_de_mb_001(tmp_path, "qwen3-embedding:0.6b")

    assert linea["umbral"] == 0.7
    # El café se parece 0,6: con el umbral en 0,7 ya no llega por el significado.
    assert linea["traidos"] == [0]


def test_con_diagnostico_escribe_una_linea_por_caso_y_despues_lo_de_siempre() -> None:
    lineas: list[str] = []

    codigo = orden.main(
        ["--diagnostico"],
        huellas_de=_Huellas,
        escribe=lineas.append,
        casos=MEMORY_BANK[:2],
    )

    assert codigo == 1
    assert lineas[0] == orden.CABECERA_DEL_DIAGNOSTICO
    assert [json.loads(linea)["id"] for linea in lineas[1:3]] == ["MB-001", "MB-002"]
    assert lineas[-2].startswith("En total: ")
    assert lineas[-2].endswith(" de 2, con el modelo de huellas qwen3-embedding:0.6b.")


def test_sin_diagnostico_no_escribe_ninguna_linea_de_caso() -> None:
    lineas: list[str] = []

    orden.main(huellas_de=_Huellas, escribe=lineas.append, casos=MEMORY_BANK[:2])

    assert orden.CABECERA_DEL_DIAGNOSTICO not in lineas
    assert not [linea for linea in lineas if linea.startswith("{")]


def test_el_banco_se_pasa_con_el_modelo_elegido_sin_tocar_sus_ajustes() -> None:
    save_settings({"ollama_embedding_model": "qwen3-embedding:0.6b"})
    pedidos: list[str] = []

    def sin_ollama(modelo: str) -> _Huellas:
        pedidos.append(modelo)
        return _Huellas(modelo, falla=True)

    lineas: list[str] = []
    codigo = orden.main(
        ["--modelo", "embeddinggemma:300m"], huellas_de=sin_ollama, escribe=lineas.append
    )

    assert codigo == 2
    assert pedidos == ["embeddinggemma:300m"]
    assert lineas == [
        "No hay modelo de huellas. Abre Ollama y ejecuta: ollama pull embeddinggemma:300m"
    ]
    assert load_settings() == {"ollama_embedding_model": "qwen3-embedding:0.6b"}

    pedidos.clear()
    orden.main(huellas_de=sin_ollama, escribe=lineas.append)
    assert pedidos == ["qwen3-embedding:0.6b"]


def test_la_busqueda_se_mide_con_el_modelo_elegido_sin_tocar_sus_ajustes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save_settings({"ollama_embedding_model": "qwen3-embedding:0.6b"})
    initialize_persistence(resolve_paths())
    monkeypatch.setattr(busqueda, "RECUERDOS_DE_PRUEBA", 300)
    pedidos: list[str] = []

    def huellas_de(modelo: str) -> _Huellas:
        pedidos.append(modelo)
        return _Huellas(modelo)

    lineas: list[str] = []
    codigo = busqueda.main(
        ["--modelo", "embeddinggemma:300m"], huellas_de=huellas_de, escribe=lineas.append
    )

    assert codigo == 0
    assert pedidos == ["embeddinggemma:300m"]
    assert lineas[0] == "Modelo de huellas: embeddinggemma:300m (4 números por huella)."
    assert load_settings()["ollama_embedding_model"] == "qwen3-embedding:0.6b"
