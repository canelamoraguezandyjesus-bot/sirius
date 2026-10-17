"""La orden de E-R02-05 funciona de punta a punta, con un modelo de huellas de mentira.

En su ordenador la ejecuta él con el de verdad. Aquí se comprueba que no se ha
roto y que nunca toca su ``sirius.db``.
"""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from _bases_abiertas import PUEDE_MIRAR, sin_recolector, vigila_lo_que_se_borra

import medir_busqueda_de_memoria as orden
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.composition_root import DATA_PATHS_UNKNOWN
from sirius.infrastructure.bootstrap_location_store import build_bootstrap_location_store
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.embeddings import EmbeddingError

pytestmark = pytest.mark.integration


class _Huellas:
    def __init__(self, model: str, *, falla: bool = False) -> None:
        self.model_name = model
        self.falla = falla
        self.pedidas: list[str] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.pedidas.extend(texts)
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
    assert lineas[0] == "Modelo de huellas: embeddinggemma (8 números por huella)."
    assert lineas[1].startswith("Tu memoria, 1 recuerdos: P50 ")
    assert lineas[2].startswith("300 recuerdos de prueba: P50 ")
    assert lineas[3] == "Pasa: sí."
    # Su base no se toca: ni una huella, ni un byte.
    assert suya.read_bytes() == antes
    with sqlite3.connect(suya) as conexion:
        assert conexion.execute("SELECT COUNT(*) FROM memory_embeddings").fetchone() == (0,)


def test_mide_la_memoria_de_la_carpeta_que_eligio_y_no_la_de_serie(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Al preparar sus evaluaciones (ADR-247): la orden buscaba su base en la carpeta de
    # serie, y con la que él eligiera al configurar Sirius medía una memoria vacía.
    elegida = resolve_paths(tmp_path / "datos-elegidos")
    initialize_persistence(elegida)
    build_bootstrap_location_store().save(elegida.data_dir)
    recuerdos = build_sqlite_memory_repository(elegida.data_dir / "sirius.db")
    recuerdos.create_memory("Le pirra el cocido.", "manual")
    recuerdos.close()
    monkeypatch.setattr(orden, "RECUERDOS_DE_PRUEBA", 300)
    lineas: list[str] = []

    codigo = orden.main(huellas_de=_Huellas, escribe=lineas.append)

    assert codigo == 0
    assert lineas[1].startswith("Tu memoria, 1 recuerdos: P50 ")
    assert not (resolve_paths().data_dir / "sirius.db").exists()


def test_si_sirius_no_sabe_donde_estan_sus_datos_dice_que_lo_abra() -> None:
    lineas: list[str] = []

    codigo = orden.main(huellas_de=_Huellas, escribe=lineas.append)

    assert codigo == 4
    assert lineas == [DATA_PATHS_UNKNOWN]


@pytest.mark.skipif(not PUEDE_MIRAR, reason="sin /proc no se ve qué ficheros tiene abiertos")
def test_al_borrar_su_carpeta_temporal_ninguna_base_sigue_abierta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # En su Windows, el 16-10-2026: la orden midió y se rompió al borrar la carpeta temporal,
    # «está siendo utilizado por otro proceso», sin decir si pasaba (ADR-247).
    initialize_persistence(resolve_paths())
    monkeypatch.setattr(orden, "RECUERDOS_DE_PRUEBA", 300)
    borrados = vigila_lo_que_se_borra(monkeypatch)
    lineas: list[str] = []

    with sin_recolector():
        codigo = orden.main(huellas_de=_Huellas, escribe=lineas.append)

    assert codigo == 0
    assert lineas[-1] == "Pasa: sí."
    assert borrados
    assert [abiertos for _, abiertos in borrados] == [[] for _ in borrados]


def test_si_no_puede_borrar_su_carpeta_temporal_lo_avisa_y_el_veredicto_queda(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initialize_persistence(resolve_paths())
    monkeypatch.setattr(orden, "RECUERDOS_DE_PRUEBA", 300)
    verdadero = shutil.rmtree
    sin_borrar: list[Path] = []

    def como_en_windows(ruta: Any, *args: Any, **kwargs: Any) -> None:
        sin_borrar.append(Path(ruta))
        raise PermissionError(13, "está siendo utilizado por otro proceso", str(ruta))

    monkeypatch.setattr(shutil, "rmtree", como_en_windows)
    lineas: list[str] = []

    try:
        codigo = orden.main(huellas_de=_Huellas, escribe=lineas.append)
    finally:
        for carpeta in sin_borrar:
            verdadero(carpeta, ignore_errors=True)

    assert codigo == 0
    assert lineas[-2] == "Pasa: sí."
    assert lineas[-1].startswith(f"Aviso: no se pudo borrar la carpeta temporal {sin_borrar[0]}.")


def test_sin_el_modelo_de_huellas_dice_que_hay_que_instalarlo() -> None:
    lineas: list[str] = []

    codigo = orden.main(
        huellas_de=lambda modelo: _Huellas(modelo, falla=True), escribe=lineas.append
    )

    assert codigo == 2
    assert lineas == [
        "El modelo de huellas embeddinggemma no contesta.",
        "Abre Ollama y ejecuta: ollama pull embeddinggemma",
    ]


def test_las_huellas_de_prueba_van_con_su_clave_y_sus_bits_y_no_se_recalculan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ADR-251: con el formato en la clave, unas huellas de prueba guardadas con el nombre
    # del modelo a secas serían de otra clave, y medir pediría 10.000 huellas a Ollama.
    rutas = resolve_paths()
    initialize_persistence(rutas)
    monkeypatch.setattr(orden, "RECUERDOS_DE_PRUEBA", 300)
    huellas: list[_Huellas] = []

    def huellas_de(modelo: str) -> _Huellas:
        huellas.append(_Huellas(modelo))
        return huellas[-1]

    assert orden.main(huellas_de=huellas_de, escribe=lambda _linea: None) == 0

    [suyas] = huellas
    assert not [texto for texto in suyas.pedidas if "Recuerdo de prueba" in texto]
    assert all(texto.startswith("task: search result | query: ") for texto in suyas.pedidas[1:])


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
    initialize_persistence(resolve_paths())
    lineas: list[str] = []

    codigo = orden.main(huellas_de=_Huellas, escribe=lineas.append)

    assert codigo == 3
    assert lineas[-1] == "sqlite-vec no carga en este Python: Sirius buscaría solo por palabras."
