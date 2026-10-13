"""El vigilante del conductor de la 0.3 ve lo que dice ver, y solo dentro de un turno.

Las pruebas de PA-R03-05 y PA-R03-08 exigen que durante un turno de voz nada se
abra para escribir ni se conecte a ningún sitio. Un vigilante que no viera nada
las dejaría pasar en vacío; estas pruebas lo alimentan con escrituras y
conexiones de verdad para que eso no pueda ocurrir (rondas 1 y 2 de Codex sobre
la PR #686).
"""

from __future__ import annotations

import contextlib
import os
import socket
import tempfile
from pathlib import Path

import conductor_robot_0_3 as conductor
from conductor_robot_0_3 import Permitidas, es_escritura_sospechosa


class _Testigo:
    """Hace de conductor dentro de un turno: apunta lo que el vigilante le cuenta."""

    def __init__(self) -> None:
        self.escrituras: list[Path] = []
        self.conexiones: list[str] = []

    def anota_escritura(self, ruta: Path) -> None:
        self.escrituras.append(ruta)

    def anota_conexion(self, direccion: str) -> None:
        self.conexiones.append(direccion)


def test_ve_un_temporal_de_audio_borrado_antes_de_acabar_y_un_os_open(tmp_path: Path) -> None:
    conductor._vigilar()
    testigo = _Testigo()
    conductor._EN_UN_TURNO.add(testigo)
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", dir=tmp_path) as temporal:
            temporal.write(b"RIFF")
        descriptor = os.open(tmp_path / "captura.tmp", os.O_WRONLY | os.O_CREAT)
        os.close(descriptor)
        (tmp_path / "leido.txt").write_text("x", encoding="utf-8")
        with (tmp_path / "leido.txt").open(encoding="utf-8") as lectura:
            lectura.read()
    finally:
        conductor._EN_UN_TURNO.discard(testigo)

    nombres = [ruta.name for ruta in testigo.escrituras]
    assert any(nombre.endswith(".wav") for nombre in nombres)
    assert "captura.tmp" in nombres
    assert nombres.count("leido.txt") == 1, "la lectura no cuenta; la escritura sí"


def test_ve_una_conexion_y_nada_fuera_del_turno(tmp_path: Path) -> None:
    conductor._vigilar()
    testigo = _Testigo()
    conductor._EN_UN_TURNO.add(testigo)
    try:
        with socket.socket() as toma, contextlib.suppress(OSError):
            toma.settimeout(0.2)
            toma.connect(("127.0.0.1", 9))
    finally:
        conductor._EN_UN_TURNO.discard(testigo)
    (tmp_path / "fuera.wav").write_bytes(b"RIFF")

    assert testigo.conexiones == ["('127.0.0.1', 9)"]
    assert testigo.escrituras == []


def test_solo_la_base_los_ajustes_y_el_diario_de_verdad_se_pueden_escribir(tmp_path: Path) -> None:
    datos, ajustes, diario = tmp_path / "datos", tmp_path / "config", tmp_path / "datos" / "logs"
    permitidas = Permitidas(
        base=datos / "sirius.db",
        ajustes=ajustes / "settings.json",
        diario=diario / "application.log",
    )
    for permitido in (
        datos / "sirius.db",
        datos / "sirius.db-wal",
        datos / "sirius.db-shm",
        datos / "sirius.db-journal",
        ajustes / "settings.json",
        diario / "application.log",
        diario / "application.log.3",
    ):
        assert not es_escritura_sospechosa(permitido, permitidas), permitido
    # El mismo nombre en otra carpeta es una escritura como otra cualquiera.
    for sospechoso in (
        datos / "captura.tmp",
        datos / "sirius.db.wav",
        datos / "grabacion.ogg",
        tmp_path / "sirius.db",
        tmp_path / "settings.json",
        tmp_path / "application.log",
        diario / "sirius.db-wal",
        Path(tempfile.gettempdir()) / "sirius.db",
    ):
        assert es_escritura_sospechosa(sospechoso, permitidas), sospechoso
