"""El vigilante del conductor de la 0.3 ve lo que dice ver, y solo mientras vigila.

Las pruebas de PA-R03-05 y PA-R03-08 exigen que mientras Sirius oye y habla nada
se abra para escribir, nada se conecte ni envíe a ningún sitio y nada lance un
proceso. Un vigilante que no viera nada las dejaría pasar en vacío; estas
pruebas lo alimentan con escrituras, conexiones, envíos y procesos de verdad
para que eso no pueda ocurrir (rondas 1 y 2 de Codex y revisión propia de la
PR #686).
"""

from __future__ import annotations

import contextlib
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import conductor_robot_0_3 as conductor
import pytest
from conductor_robot_0_3 import Permitidas, es_escritura_sospechosa


class _Testigo:
    """Hace de conductor vigilado: apunta lo que el vigilante le cuenta."""

    def __init__(self) -> None:
        self.escrituras: list[Path] = []
        self.conexiones: list[str] = []
        self.procesos: list[str] = []
        self.sentencias: list[str] = []
        self.bases: set[str] = set()

    def anota_escritura(self, ruta: Path) -> None:
        self.escrituras.append(ruta)

    def anota_conexion(self, direccion: str) -> None:
        self.conexiones.append(direccion)

    def anota_proceso(self, orden: str) -> None:
        self.procesos.append(orden)

    def anota_sentencia(self, sql: str, base: str = "") -> None:
        self.sentencias.append(sql)
        self.bases.add(base)


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


def test_ve_un_envio_sin_conexion_y_un_proceso_y_no_la_pareja_de_tomas_de_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conductor._vigilar()
    testigo = _Testigo()
    conductor._EN_UN_TURNO.add(testigo)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as toma:
            toma.sendto(b"x", ("127.0.0.1", 9))
        # Resolver un nombre ya sale del ordenador; una dirección numérica, no. La
        # resolución inversa y enlazar a un nombre, también.
        with contextlib.suppress(OSError):
            socket.getaddrinfo("localhost", 9)
        socket.getaddrinfo("127.0.0.1", 9)
        with contextlib.suppress(OSError):
            socket.gethostbyaddr("127.0.0.1")
        with socket.socket() as enlazada:
            enlazada.bind(("127.0.0.1", 0))
            with contextlib.suppress(OSError):
                enlazada.bind(("localhost", 0))
        # La pareja que Python se fabrica en Windows conectándose a sí mismo (y
        # que asyncio usa en cada bucle) no sale del ordenador: no cuenta.
        monkeypatch.setattr(socket, "socketpair", socket._fallback_socketpair)  # type: ignore[attr-defined]
        una, otra = socket.socketpair()
        una.close()
        otra.close()
        subprocess.run([sys.executable, "-c", "pass"], check=True)
        os.system("exit 0")
    finally:
        conductor._EN_UN_TURNO.discard(testigo)

    assert testigo.conexiones == [
        "('127.0.0.1', 9)",
        "resolver 'localhost'",
        "resolver '127.0.0.1'",
        "resolver 'localhost'",
    ]
    # Un mismo proceso puede llegar por dos eventos (`subprocess.Popen` y `os.posix_spawn`):
    # lo que importa es que ninguno de los dos se escapa.
    assert any(sys.executable in proceso for proceso in testigo.procesos)
    assert any("exit 0" in proceso for proceso in testigo.procesos)


class _SuConexion(sqlite3.Connection):
    """Una clase de conexión propia de una pieza."""


def test_ve_cada_sentencia_de_una_conexion_abierta_mientras_vigila_con_sus_valores(
    tmp_path: Path,
) -> None:
    conductor._vigilar()
    testigo = _Testigo()
    conductor._EN_UN_TURNO.add(testigo)
    try:
        with contextlib.closing(sqlite3.connect(tmp_path / "una.db")) as conexion:
            conexion.execute("CREATE TABLE t (b BLOB, s TEXT)")
            conexion.execute("INSERT INTO t VALUES (?, ?)", (b"RIFF\x00", "hola"))
            conexion.execute("DELETE FROM t")
            conexion.execute("SELECT count(*) FROM t").fetchone()
        # Una conexión que no pasa por ``sqlite3.connect`` no se puede trazar: se apunta.
        with contextlib.closing(sqlite3.Connection(str(tmp_path / "dos.db"))) as directa:
            directa.execute("CREATE TABLE u (b BLOB)")
        # La pieza puede poner su propio trazador, o quitarlo: el vigilante sigue viendo, y
        # el suyo recibe lo mismo. También con una clase de conexión suya.
        suyas: list[str] = []
        with contextlib.closing(sqlite3.connect(tmp_path / "cuatro.db", factory=_SuConexion)) as c:
            assert isinstance(c, _SuConexion)
            c.set_trace_callback(suyas.append)
            c.execute("CREATE TABLE w (b BLOB)")
            c.set_trace_callback(None)
            c.execute("INSERT INTO w VALUES (x'00')")
        # Y con la clase que ya sale vigilada como fábrica, no se envuelve dos veces.
        with contextlib.closing(sqlite3.connect(tmp_path / "cinco.db", factory=type(c))) as d:
            assert type(d) is type(c)
            d.execute("CREATE TABLE z (b BLOB)")
            # Apagar los disparadores de SQLite en una conexión vigilada queda apuntado.
            d.setconfig(sqlite3.SQLITE_DBCONFIG_ENABLE_TRIGGER, False)
        # Una fábrica que no es una clase de conexión no se puede envolver: se apunta.
        with contextlib.closing(
            sqlite3.connect(  # type: ignore[call-overload]
                tmp_path / "seis.db", factory=lambda *a, **k: sqlite3.Connection(*a, **k)
            )
        ) as suelta:
            suelta.execute("CREATE TABLE y (b BLOB)")
    finally:
        conductor._EN_UN_TURNO.discard(testigo)
    # Y sin nadie vigilando, una conexión nueva no apunta nada.
    with contextlib.closing(sqlite3.connect(tmp_path / "tres.db")) as conexion:
        conexion.execute("CREATE TABLE v (b BLOB)")

    # Los valores van puestos: el BLOB se ve en hexadecimal, y el texto, entero.
    assert "INSERT INTO t VALUES (x'5249464600', 'hola')" in testigo.sentencias
    assert "DELETE FROM t" in testigo.sentencias
    assert "SELECT count(*) FROM t" in testigo.sentencias
    assert testigo.sentencias.count(conductor._CONEXION_SIN_VIGILAR) == 2
    assert testigo.sentencias.count(conductor._APAGO_LOS_DISPARADORES) == 1
    assert not any("TABLE u" in s or "TABLE v" in s for s in testigo.sentencias)
    assert "CREATE TABLE y (b BLOB)" in testigo.sentencias, "se traza aunque no se envuelva"
    assert {b.rsplit("/", 1)[-1] for b in testigo.bases if b} == {
        "una.db",
        "cuatro.db",
        "cinco.db",
        "seis.db",
    }
    assert suyas == ["CREATE TABLE w (b BLOB)"]
    assert "CREATE TABLE w (b BLOB)" in testigo.sentencias
    assert "INSERT INTO w VALUES (x'00')" in testigo.sentencias
    assert testigo.sentencias.count("CREATE TABLE z (b BLOB)") == 1


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
