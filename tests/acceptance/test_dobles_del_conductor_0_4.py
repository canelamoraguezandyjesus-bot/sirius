"""Los dobles del conductor de la 0.4 hacen lo que dicen, y sus registros los escriben ellos.

Las pruebas de la 0.4 miran lo que apuntan la cámara, el detector de caras, los
reconocedores de cara y de voz y el estimador de edad, y buscan imágenes y huellas donde
no deben estar. Una prueba en ``xfail`` estricto no ejecuta ni una línea del conductor,
así que lo que el conductor ya hace necesita una prueba que corra hoy (lección de
ADR-241): que cada doble lee lo que hay delante de los bytes que le llegan y lo apunta en
el acto, que una huella de mentira se comporta como una de verdad, y que una imagen o una
huella guardadas por error se ven donde se buscan.
"""

from __future__ import annotations

import base64
import json
import logging
import math
import random
import sqlite3
import struct
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from conductor_robot_0_3 import Audio, Sonido
from conductor_robot_0_4 import (
    ALTO_DE_LA_CARA,
    MARCA_DE_LA_IMAGEN,
    NUMEROS_DE_LA_HUELLA_DE_CARA,
    NUMEROS_DE_LA_HUELLA_DE_VOZ,
    PIEZAS,
    PIEZAS_ENTREGADAS,
    AudioConVoz,
    CamaraDeMentira,
    CamaraNoEncontrada,
    ConductorDeOjos,
    DetectorDeMentira,
    Dibujo,
    EstimadorDeEdadDeMentira,
    Persona,
    ReconocedorDeCarasDeMentira,
    ReconocedorDeVocesDeMentira,
    SonidoDe,
    formas_de_la_huella,
    formas_en,
    huella_de_cara,
    huella_de_voz,
    parecido,
)
from lector_de_la_cara import lee
from pytestqt.qtbot import QtBot

from sirius.domain.gestures import GESTURES
from sirius.infrastructure.logging import LOGGER_NAME

pytestmark = pytest.mark.acceptance


class _Reloj:
    def __init__(self) -> None:
        self.ahora = 100.0


def test_la_camara_da_lo_que_hay_delante_y_apunta_cada_fotograma_con_su_momento() -> None:
    reloj = _Reloj()
    camara = CamaraDeMentira(lambda: reloj.ahora)
    marta = Persona("Marta", x=0.7, habla=True)
    camara.pon_delante([marta])

    assert camara.lee() is None, "cerrada no da nada"
    camara.abre()
    primero = camara.lee()
    reloj.ahora = 101.5
    camara.pon_delante([])
    segundo = camara.lee()

    assert primero is not None and segundo is not None
    assert (primero.numero, primero.momento) == (1, 100.0)
    assert (segundo.numero, segundo.momento) == (2, 101.5)
    assert marta.recorte() in primero.pixeles
    assert MARCA_DE_LA_IMAGEN in segundo.pixeles, "sin nadie delante también es una imagen"
    assert marta.recorte() not in segundo.pixeles
    assert camara.dados == (primero, segundo)

    camara.desconecta()
    assert not camara.abierta
    with pytest.raises(CamaraNoEncontrada):
        camara.abre()
    with pytest.raises(CamaraNoEncontrada):
        camara.lee()
    assert len(camara.dados) == 2
    with pytest.raises(AttributeError):
        camara.dados = ()  # type: ignore[misc]


def test_el_detector_encuentra_cada_cara_en_los_bytes_y_apunta_cuantas_vio() -> None:
    camara = CamaraDeMentira(lambda: 0.0)
    detector = DetectorDeMentira()
    camara.abre()
    camara.pon_delante(
        [
            Persona("propietario", x=0.25, habla=True, mira_a_sirius=False),
            Persona("Marta", x=0.75, habla=False, mira_a_sirius=True),
        ]
    )
    con_dos = camara.lee()
    camara.pon_delante([])
    vacio = camara.lee()
    assert con_dos is not None and vacio is not None

    caras = detector.detecta(con_dos)

    assert [(cara.x, cara.habla, cara.mira) for cara in caras] == [
        (0.25, True, False),
        (0.75, False, True),
    ]
    assert all(cara.recorte.startswith(MARCA_DE_LA_IMAGEN) for cara in caras)
    assert detector.detecta(vacio) == ()
    assert detector.detecciones == ((1, 2), (2, 0))
    # Cada recorte es la cara de una sola persona: el reconocedor la saca de ahí.
    reconocedor = ReconocedorDeCarasDeMentira()
    assert [reconocedor.huella(cara.recorte) for cara in caras] == [
        huella_de_cara("propietario"),
        huella_de_cara("Marta"),
    ]


def test_las_huellas_son_como_las_de_verdad_y_normalizarlas_no_las_cambia() -> None:
    for huella, numeros in (
        (huella_de_cara("Marta"), NUMEROS_DE_LA_HUELLA_DE_CARA),
        (huella_de_voz("Marta"), NUMEROS_DE_LA_HUELLA_DE_VOZ),
    ):
        assert len(huella) == numeros
        assert sum(numero * numero for numero in huella) == 1.0
        longitud = math.sqrt(sum(numero * numero for numero in huella))
        assert tuple(numero / longitud for numero in huella) == huella
        en_float32 = struct.unpack(f"<{numeros}f", struct.pack(f"<{numeros}f", *huella))
        assert en_float32 == huella
    assert huella_de_cara("Marta") == huella_de_cara("Marta")
    assert parecido(huella_de_cara("Marta"), huella_de_cara("Marta")) == 1.0
    for otro in ("Pepe", "propietario", "Marta García"):
        assert abs(parecido(huella_de_cara("Marta"), huella_de_cara(otro))) < 0.3
        assert abs(parecido(huella_de_voz("Marta"), huella_de_voz(otro))) < 0.3


def test_los_reconocedores_de_caras_y_de_edad_leen_el_recorte_y_lo_apuntan() -> None:
    caras = ReconocedorDeCarasDeMentira()
    edades = EstimadorDeEdadDeMentira()
    lucas = Persona("Lucas", edad=8, edad_segura=False).recorte()

    assert caras.huella(lucas) == huella_de_cara("Lucas")
    assert edades.estima(lucas) == (8, False)
    with pytest.raises(ValueError, match="no es una cara"):
        caras.huella(random.Random(1).randbytes(500))
    with pytest.raises(ValueError, match="no es una cara"):
        edades.estima(b"")
    assert caras.dadas == (huella_de_cara("Lucas"),)
    assert edades.estimadas == ((8, False),)


def test_la_voz_lleva_su_timbre_en_las_muestras_y_solo_el_reconocedor_lo_lee() -> None:
    voces = ReconocedorDeVocesDeMentira()
    de_marta = SonidoDe("Sirius, ¿me conoces?", de_quien="Marta").audio
    sin_voz = Audio("Sirius, ¿me conoces?")

    # Lo mismo que un audio de la 0.3, con el timbre dentro de las mismas muestras.
    assert isinstance(de_marta, AudioConVoz)
    assert de_marta.texto == sin_voz.texto
    assert len(de_marta.muestras) == len(sin_voz.muestras)
    assert de_marta.muestras != sin_voz.muestras
    assert SonidoDe("Hola.").audio == AudioConVoz("Hola.", timbre="propietario")
    assert SonidoDe("Hola.").de("propietario"), "sin decir de quién, es del propietario"

    assert voces.huella(sin_voz.muestras) is None
    # Con silencio delante, como llega un turno con lo que había antes de que hablara.
    assert voces.huella(Audio("").muestras + de_marta.muestras) == huella_de_voz("Marta")
    mezcla = voces.huella(de_marta.muestras + SonidoDe("Y yo.", de_quien="Pepe").audio.muestras)
    assert mezcla is not None
    assert abs(parecido(mezcla, huella_de_voz("Marta"))) < 0.3
    assert abs(parecido(mezcla, huella_de_voz("Pepe"))) < 0.3
    assert voces.dadas == (huella_de_voz("Marta"), mezcla)


def test_una_huella_en_claro_se_reconoce_en_cada_forma_y_cifrada_no() -> None:
    huella = huella_de_cara("Marta")
    formas = formas_de_la_huella(huella)
    en_float32 = struct.pack(f"<{len(huella)}f", *huella)
    # Como la parte SQLite cuando no cabe en una página: trozos con cuatro bytes en medio.
    partida = b"".join(
        en_float32[inicio : inicio + 1_000] + b"\x00\x00\x00\x07"
        for inicio in range(0, len(en_float32), 1_000)
    )
    guardadas = {
        "float32": en_float32,
        "float32 partida": partida,
        "float64": struct.pack(f"<{len(huella)}d", *huella),
        "json": json.dumps(list(huella)).encode(),
        "json apretado": json.dumps(list(huella), separators=(",", ":")).encode(),
        "repr": repr(huella).encode(),
        "float32 en base64": base64.b64encode(en_float32),
        "float32 en base64 tras un byte": base64.b64encode(b"x" + en_float32),
        "float32 en base64 tras dos bytes": base64.b64encode(b"xy" + en_float32),
        "float64 en base64 de direcciones": base64.urlsafe_b64encode(
            struct.pack(f"<{len(huella)}d", *huella)
        ),
        "float32 en hexadecimal": en_float32.hex().encode(),
        "float64 en hexadecimal en mayúsculas": struct.pack(f"<{len(huella)}d", *huella)
        .hex()
        .upper()
        .encode(),
    }
    for nombre, guardada in guardadas.items():
        assert any(forma in guardada for forma in formas), nombre
    llave = random.Random(7).randbytes(len(en_float32))
    cifrada = bytes(a ^ b for a, b in zip(en_float32, llave, strict=True))
    assert not any(forma in cifrada for forma in formas)
    assert not any(forma in base64.b64encode(cifrada) for forma in formas)
    assert not any(forma in cifrada.hex().encode() for forma in formas)
    assert not any(forma in json.dumps(list(huella_de_cara("Pepe"))).encode() for forma in formas)


def test_la_marca_de_la_imagen_se_reconoce_en_cada_forma_en_que_python_escribe_bytes() -> None:
    recorte = Persona("Marta").recorte()
    for desfase in (0, 1, 2):
        trozo = b"x" * desfase + recorte
        assert "en base64" in formas_en(MARCA_DE_LA_IMAGEN, base64.b64encode(trozo).decode())
    assert "como texto" in formas_en(MARCA_DE_LA_IMAGEN, repr(recorte))
    assert "en hexadecimal" in formas_en(MARCA_DE_LA_IMAGEN, recorte.hex(" "))
    assert "como lista de bytes" in formas_en(MARCA_DE_LA_IMAGEN, str(list(recorte)))
    assert formas_en(MARCA_DE_LA_IMAGEN, "Marta ha venido a las 18:02.\n" * 1_000) == []


def test_el_conductor_se_construye_con_sus_dobles_y_ve_huellas_en_claro(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    assert set(PIEZAS) == set("ABCDEFG")
    assert "A" in PIEZAS_ENTREGADAS
    assert conductor.camara.dados == ()
    assert conductor.huellas_en_claro() == []
    assert conductor.imagenes_guardadas() == []
    huella = conductor.caras.huella(Persona("Marta").recorte())
    assert conductor.huellas_en_claro() == [], "dada no es guardada"
    en_claro = struct.pack(f"<{len(huella)}f", *huella)

    # Lo escrito en modo WAL espera en «-wal» hasta volcarse a la base. Sirius usa el
    # diario de deshacer, que con la base en ese modo no mira el «-wal»; una pieza podría
    # cambiar el modo, y entonces la huella estaría ahí.
    wal = conductor.base.with_name(conductor.base.name + "-wal")
    wal.write_bytes(b"\x00" * 32 + en_claro)
    assert conductor.huellas_en_claro() == ["la base lleva una huella en claro"]
    wal.unlink()
    assert conductor.huellas_en_claro() == []

    # En base64, partida en líneas como la escribe ``encodebytes``: no está cifrada.
    with closing(sqlite3.connect(conductor.base)) as conexion:
        conexion.execute("CREATE TABLE huellas_en_texto (huella TEXT)")
        conexion.execute(
            "INSERT INTO huellas_en_texto VALUES (?)", (base64.encodebytes(en_claro).decode(),)
        )
        conexion.commit()
    assert conductor.huellas_en_claro() == ["la base lleva una huella en claro"]
    with closing(sqlite3.connect(conductor.base)) as conexion:
        conexion.execute("DROP TABLE huellas_en_texto")
        conexion.execute("VACUUM")
        conexion.commit()
    assert conductor.huellas_en_claro() == []

    with closing(sqlite3.connect(conductor.base)) as conexion:
        conexion.execute("CREATE TABLE huellas_de_prueba (huella BLOB)")
        conexion.execute("INSERT INTO huellas_de_prueba VALUES (?)", (en_claro,))
        conexion.commit()
    assert conductor.huellas_en_claro() == ["la base lleva una huella en claro"]

    de_pepe = conductor.voces.huella(SonidoDe("Hola.", de_quien="Pepe").audio.muestras)
    assert de_pepe is not None
    logging.getLogger(LOGGER_NAME).warning("huella: %s", list(de_pepe))
    assert conductor.huellas_en_claro() == [
        "la base lleva una huella en claro",
        "el diario lleva una huella en claro",
    ]
    conductor.cierra()


def test_el_conductor_ve_imagenes_en_el_disco_en_la_base_y_en_el_diario(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    datos = conductor.base.parent
    assert conductor.imagenes_guardadas() == []

    (datos / "cara").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    assert conductor.imagenes_guardadas() == [str(datos / "cara")]

    # Un fotograma en base64 en una columna de texto no lleva la marca tal cual.
    with closing(sqlite3.connect(conductor.base)) as conexion:
        conexion.execute("CREATE TABLE fotos_en_texto (foto TEXT)")
        conexion.execute(
            "INSERT INTO fotos_en_texto VALUES (?)",
            (base64.b64encode(b"z" + Persona("Pepe").recorte()).decode(),),
        )
        conexion.commit()
    assert conductor.imagenes_guardadas() == [
        str(datos / "cara"),
        "la base lleva la marca de los fotogramas en base64",
    ]

    with closing(sqlite3.connect(conductor.base)) as conexion:
        conexion.execute("CREATE TABLE fotos_de_prueba (foto BLOB, texto TEXT)")
        conexion.execute(
            "INSERT INTO fotos_de_prueba VALUES (?, ?)",
            (Persona("Marta").recorte(), "data:image/png;base64,iVBORw0KGgoAAAA"),
        )
        conexion.commit()
    vistas = conductor.imagenes_guardadas()
    assert "la base lleva la marca de los fotogramas como texto" in vistas
    assert "la base lleva una imagen: b'iVBORw0KGgo'" in vistas

    logging.getLogger(LOGGER_NAME).warning("fotograma: %s", Persona("Pepe").recorte().hex())
    assert "el diario lleva la marca de los fotogramas en hexadecimal" in (
        conductor.imagenes_guardadas()
    )
    conductor.cierra()


def test_oye_y_oye_a_suenan_con_su_voz_y_marcan_el_turno(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)

    primero = conductor.oye("Sirius, ¿qué tal?")
    segundo = conductor.oye_a("Marta", "Sirius, ¿y a mí me oyes?")

    assert (primero.oido, segundo.oido) == ("Sirius, ¿qué tal?", "Sirius, ¿y a mí me oyes?")
    con_voz = [sonido for sonido in conductor.micro.leidos if sonido.texto]
    assert [(sonido.texto, sonido.de_quien) for sonido in con_voz] == [
        ("Sirius, ¿qué tal?", "propietario"),
        ("Sirius, ¿y a mí me oyes?", "Marta"),
    ]
    assert all(isinstance(sonido, SonidoDe) for sonido in con_voz)
    assert conductor.voces.huella(con_voz[1].audio.muestras) == huella_de_voz("Marta")
    assert [p.texto for p in conductor.peticiones_del_ultimo_turno()] == [
        "Sirius, ¿y a mí me oyes?"
    ]
    assert not isinstance(Sonido("x").audio, AudioConVoz), "la 0.3 sigue como estaba"
    conductor.cierra()


def test_a_quien_mira_va_con_la_izquierda_y_la_derecha_de_la_camara(tmp_path: Path) -> None:
    conductor = ConductorDeOjos(tmp_path)
    conductor.delante(Persona("propietario", x=0.2), Persona("Marta", x=0.8))

    def mirando(x: float, y: float = 0.0) -> Dibujo:
        return Dibujo(0.0, 1.0, (x, y), 0.0, 0.0, 0.0)

    assert conductor.a_quien_mira(mirando(-0.6)) == "propietario"
    assert conductor.a_quien_mira(mirando(0.55)) == "Marta"
    assert conductor.a_quien_mira(mirando(0.0)) is None, "al frente, entre los dos"
    assert conductor.a_quien_mira(mirando(0.6, 0.8)) is None, "hacia arriba"
    conductor.delante()
    assert conductor.a_quien_mira(mirando(0.0)) is None, "sin nadie delante"
    conductor.cierra()


@pytest.mark.gui
def test_gestos_dibujados_ve_cada_gesto_que_hace_la_cara_y_ninguno_si_no_hace(
    qtbot: QtBot, tmp_path: Path
) -> None:
    """Lo que lee ``gestos_dibujados`` sale de la cara de la ventana de verdad: sin gestos
    no ve ninguno, y con dos ve los dos, en orden (pieza C)."""
    conductor = ConductorDeOjos(tmp_path)
    ventana = conductor.ventana(qtbot)

    assert conductor.gestos_dibujados(1.0) == ()
    ventana._cara().make("guino")
    ventana._cara().make("asiente")
    assert conductor.gestos_dibujados(3.0) == ("guino", "asiente")
    conductor.cierra()


# --- La cara, leída de los píxeles (ronda 1 de Codex sobre la PR #702) ----------------


def _cara_suelta(qtbot: QtBot, reloj: _Reloj, cara_de: type[Any] | None = None) -> Any:
    """La cara de verdad, sola y del alto con que se lee en las pruebas, con una vida de
    semilla fija."""
    from sirius.domain.face import FaceLife
    from sirius.presentation.face_widget import FaceWidget

    clase = cara_de or FaceWidget
    cara = clase(lambda: reloj.ahora, life=FaceLife(seed=5))
    cara.resize(1000, ALTO_DE_LA_CARA)
    qtbot.addWidget(cara)
    cara.show()
    return cara


@pytest.mark.gui
def test_el_lector_lee_de_los_pixeles_lo_que_pinta_la_cara(qtbot: QtBot) -> None:
    """Lo que lee el lector es lo que se ve: imagen a imagen, se parece a lo que la cara
    dice que pintó, que aquí solo sirve para comprobar al lector."""
    reloj = _Reloj()
    cara = _cara_suelta(qtbot, reloj)
    vistos: set[str] = set()
    for paso in range(1, 1501):
        reloj.ahora += 0.02
        if paso % 150 == 0:
            cara.make(GESTURES[(paso // 150 - 1) % len(GESTURES)])
        lectura = lee(cara.grab().toImage(), reloj.ahora)
        assert lectura is not None
        dibujo, (_, pose) = lectura.dibujo, cara.last_drawn
        izquierdo = min(max(pose.eyes, 0.0), 1.0)
        derecho = 1.0 - max(1.0 - izquierdo, min(max(pose.wink, 0.0), 1.0))
        assert abs(dibujo.ojos - (izquierdo + derecho) / 2) < 0.05
        if dibujo.mirada is not None and min(izquierdo, derecho) > 0.6:
            assert abs(dibujo.mirada[0] - pose.gaze[0]) < 0.06
            assert abs(dibujo.mirada[1] - pose.gaze[1]) < 0.06
        assert abs(dibujo.cejas - pose.brows) < 0.06
        if dibujo.gesto is not None:
            assert dibujo.gesto == pose.gesture, "lee un gesto que no hace"
            vistos.add(dibujo.gesto)
    assert vistos == set(GESTURES), "no ha visto todos los gestos"


@pytest.mark.gui
def test_una_cara_que_no_pinta_lo_que_dice_no_se_lee_como_si_lo_pintara(qtbot: QtBot) -> None:
    """Una cara que dice que parpadea y pinta siempre los ojos abiertos se lee con los ojos
    abiertos; y una que no pinta nada, sin cara."""
    from sirius.domain.face import FacePose
    from sirius.presentation.face_widget import FaceWidget

    class Quieta(FaceWidget):
        def _draw(self, painter: Any, pose: Any) -> None:
            del pose
            super()._draw(painter, FacePose(1.0, (0.0, 0.0), 0.0, 0.0, 0.0))

    class Vacia(FaceWidget):
        def _draw(self, painter: Any, pose: Any) -> None:
            del pose
            painter.fillRect(self.rect(), 0)

    reloj = _Reloj()
    quieta = _cara_suelta(qtbot, reloj, Quieta)
    dice, se_ve = set(), set()
    for _ in range(500):
        reloj.ahora += 0.02
        lectura = lee(quieta.grab().toImage(), reloj.ahora)
        assert lectura is not None
        dice.add(quieta.last_drawn[1].eyes <= 0.2)
        se_ve.add(lectura.dibujo.ojos <= 0.2)
    assert dice == {True, False}, "la cara de la prueba tenía que decir que parpadea"
    assert se_ve == {False}, "ha leído un parpadeo que no se pinta"
    vacia = _cara_suelta(qtbot, reloj, Vacia)
    assert lee(vacia.grab().toImage(), reloj.ahora) is None
