"""La orden de E-R02-05 funciona de punta a punta, con un modelo de huellas de mentira.

En su ordenador la ejecuta él con el de verdad. Aquí se comprueba que no se ha
roto y que nunca toca su ``sirius.db``.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Sequence
from pathlib import Path

import pytest

import medir_busqueda_de_memoria as orden
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.embeddings import EmbeddingError

pytestmark = pytest.mark.integration


class _Huellas:
    def __init__(self, model: str, *, falla: bool = False) -> None:
        self.model_name = model
        self.falla = falla

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if self.falla:
            msg = "sin Ollama"
            raise EmbeddingError(msg)
        return [[b / 255 for b in hashlib.sha256(t.encode()).digest()[:8]] for t in texts]


def test_mide_su_memoria_y_la_de_prueba_y_dice_si_pasa(monkeypatch: pytest.MonkeyPatch) -> None:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    suya = rutas.data_dir / "sirius.db"
    recuerdos = build_sqlite_memory_repository(suya)
    recuerdos.create_memory("Le pirra el cocido.", "manual")
    recuerdos.close()
    antes = suya.read_bytes()
    monkeypatch.setattr(orden, "RECUERDOS_DE_PRUEBA", 300)
    lineas: list[str] = []

    codigo = orden.main(huellas_de=_Huellas, escribe=lineas.append)

    assert codigo == 0
    assert lineas[0] == "Modelo de huellas: qwen3-embedding:0.6b (8 números por huella)."
    assert lineas[1].startswith("Tu memoria, 1 recuerdos: P50 ")
    assert lineas[2].startswith("300 recuerdos de prueba: P50 ")
    assert lineas[3] == "Pasa: sí."
    # Su base no se toca: ni una huella, ni un byte.
    assert suya.read_bytes() == antes
    with sqlite3.connect(suya) as conexion:
        assert conexion.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone() == (0,)


def test_sin_el_modelo_de_huellas_dice_que_hay_que_instalarlo() -> None:
    lineas: list[str] = []

    codigo = orden.main(
        huellas_de=lambda modelo: _Huellas(modelo, falla=True), escribe=lineas.append
    )

    assert codigo == 2
    assert lineas == [
        "El modelo de huellas qwen3-embedding:0.6b no contesta.",
        "Abre Ollama y ejecuta: ollama pull qwen3-embedding:0.6b",
    ]


def test_el_percentil_es_el_del_rango_mas_cercano() -> None:
    tiempos = [float(n) for n in range(1, 101)]

    assert orden.percentil(tiempos, 95) == 95.0
    assert orden.percentil(tiempos, 50) == 50.0
    assert orden.percentil([7.0], 95) == 7.0


def test_la_copia_de_una_base_que_no_existe_es_una_memoria_vacia(tmp_path: Path) -> None:
    assert orden.copia_su_memoria(tmp_path / "no-existe.db", tmp_path / "copia.db") == 0


def test_si_sqlite_vec_no_carga_lo_dice_en_vez_de_medir_solo_palabras(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sirius.adapters.persistence import sqlite_memory_embeddings

    def no_carga(conexion: object, registro: object) -> None:
        raise sqlite3.OperationalError("no se pudo cargar la extensión")

    monkeypatch.setattr(sqlite_memory_embeddings, "_load_sqlite_vec", no_carga)
    lineas: list[str] = []

    codigo = orden.main(huellas_de=_Huellas, escribe=lineas.append)

    assert codigo == 3
    assert lineas[-1] == "sqlite-vec no carga en este Python: Sirius buscaría solo por palabras."
