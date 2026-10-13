"""Los dobles del conductor de la 0.3 hacen lo que dicen, y sus registros los escriben ellos.

Las 27 pruebas de la 0.3 miran lo que apuntan el micro, el oído, el transcriptor,
la voz, el altavoz y el modelo de mentira. Si esos registros los rellenara el
conductor, que escribe quien implementa cada pieza, no probarían nada; y una
prueba en ``xfail`` estricto no ejecuta ni una línea del conductor, así que lo
que el conductor ya hace necesita una prueba que corra hoy (revisión propia de
la PR #686). Aquí se comprueba que cada doble apunta en el acto de leer,
escuchar, transcribir, decir, sonar y contestar; que lo que la tubería recibe
del micro no dice quién habló; y que el conductor se construye, lee la charla y
el audio de la base de verdad y la charla de la ventana de verdad.
"""

from __future__ import annotations

import logging
import sqlite3
import struct
import time
from contextlib import closing
from pathlib import Path

import pytest
import sqlite_vec
from conductor_robot_0_2 import _respuestas
from conductor_robot_0_3 import (
    AltavozDeMentira,
    Audio,
    ConductorDeVoz,
    MicroCerrado,
    MicroDeMentira,
    ModeloDeMentira,
    OidoDeMentira,
    Sonido,
    TranscriptorDeMentira,
    VentanaDeVoz,
    VozDeMentira,
)
from piezas_del_robot import PiezaPendiente
from pytestqt.qtbot import QtBot

from sirius.infrastructure.logging import LOGGER_NAME
from sirius.ports.llm import LLMCompleted, LLMRequest, LLMTextDelta

pytestmark = pytest.mark.acceptance


def test_el_micro_solo_lee_abierto_y_apunta_cada_lectura_con_su_momento() -> None:
    micro = MicroDeMentira()
    micro.suena(Sonido("Se pierde: el micro está cerrado."))
    with pytest.raises(MicroCerrado):
        micro.lee()

    micro.abre()
    micro.suena(Sonido("Hola, Sirius."))
    micro.suena(Sonido(""))
    antes = time.perf_counter()

    # La tubería recibe el audio sin quién lo dijo; la prueba ve el sonido entero.
    assert micro.lee() == Audio("Hola, Sirius.")
    assert micro.lee() == Audio("")
    assert micro.lee() is None
    assert micro.perdidos == (Sonido("Se pierde: el micro está cerrado."),)
    assert micro.leidos == (Sonido("Hola, Sirius."), Sonido(""))
    assert micro.pendientes == ()
    assert len(micro.leido_en) == 2
    assert antes <= micro.leido_en[0] <= micro.leido_en[1] <= time.perf_counter()
    micro.cierra()
    assert not micro.abierto
    # Los registros solo se leen.
    with pytest.raises(AttributeError):
        micro.leidos = ()  # type: ignore[misc]


def test_el_oido_dice_fin_solo_tras_los_silencios_que_pide_y_despues_de_voz() -> None:
    oido = OidoDeMentira()
    oido.pide_silencios(3)

    assert not oido.escucha(Audio("")), "un silencio antes de la voz no acaba nada"
    assert not oido.escucha(Audio("Sirius, estaba pensando que"))
    assert not oido.escucha(Audio(""))
    assert not oido.escucha(Audio(""))
    assert oido.escucha(Audio(""))
    assert list(oido.fines) == [4]
    assert OidoDeMentira.hay_voz(Audio("algo"))
    assert not OidoDeMentira.hay_voz(Audio(""))

    # El impaciente, en el turno siguiente.
    oido.pide_silencios(1)
    assert not oido.escucha(Audio("Otra cosa."))
    assert oido.escucha(Audio(""))
    assert list(oido.fines) == [4, 6]
    assert len(oido.vistos) == 7


def test_el_transcriptor_devuelve_lo_escrito_en_la_voz_y_lo_apunta() -> None:
    transcriptor = TranscriptorDeMentira()

    texto = transcriptor.transcribe([Audio("Buenos días,"), Audio(""), Audio("Sirius.")])

    assert texto == "Buenos días, Sirius."
    assert transcriptor.transcritos == ("Buenos días, Sirius.",)


def test_la_voz_apunta_cada_frase_con_su_voz_y_la_devuelve_como_sonido_de_sirius() -> None:
    voz = VozDeMentira()

    sonido = voz.di("Hola, jefe.", "es_ES-davefx-medium")

    assert sonido == Sonido("Hola, jefe.", de_quien="sirius", voz="es_ES-davefx-medium")
    assert sonido.audio == Audio("Hola, jefe.")
    assert [(f.texto, f.voz) for f in voz.frases] == [("Hola, jefe.", "es_ES-davefx-medium")]
    assert voz.frases[0].momento <= time.perf_counter()


def test_el_micro_capta_el_eco_a_la_vez_que_la_voz_mientras_el_altavoz_sigue_sonando(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.altavoz.con_eco = True
    conductor.altavoz.sigue_sonando = True
    conductor.micro.abre()
    respuesta = conductor.voz.di("Una respuesta larga.", "es_ES-davefx-medium")

    conductor.altavoz.suena(respuesta)
    conductor.habla_encima("Espera, espera.")

    # El eco entra al sonar; después la voz del propietario llega mezclada con el eco
    # en un solo audio, y el silencio llega como eco solo: las dos señales van juntas.
    assert [(s.texto, s.de_quien) for s in conductor.micro.pendientes] == [
        ("Una respuesta larga.", "sirius"),
        ("Una respuesta larga. Espera, espera.", "propietario y sirius"),
        ("Una respuesta larga.", "sirius"),
    ]
    mezclado = conductor.micro.pendientes[1]
    assert mezclado.de("propietario") and mezclado.de("sirius")
    assert mezclado.audio == Audio("Una respuesta larga. Espera, espera.")
    conductor.altavoz.para()
    conductor.habla_encima("Ya has parado.")
    assert [s.texto for s in conductor.micro.pendientes][-2:] == ["Ya has parado.", ""]
    conductor.cierra()


def test_el_altavoz_apunta_lo_que_suena_devuelve_el_eco_y_sabe_cuando_le_paran() -> None:
    micro = MicroDeMentira()
    altavoz = AltavozDeMentira(micro)

    altavoz.suena(Sonido("Sin eco.", de_quien="sirius"))
    altavoz.para()

    assert list(micro.perdidos) == []
    assert list(micro.pendientes) == []
    assert altavoz.parado_en is None, "parar lo que no suena no es un corte"

    altavoz.con_eco = True
    altavoz.sigue_sonando = True
    eco = Sonido("Con eco, y sigue sonando.", de_quien="sirius", voz="es_ES-davefx-medium")
    altavoz.suena(eco)
    assert list(micro.perdidos) == [eco], "con el micro cerrado el eco se pierde"
    micro.abre()
    altavoz.suena(eco)
    assert list(micro.pendientes) == [eco], "con el micro abierto el eco entra"
    assert altavoz.sonando == eco

    altavoz.para()

    assert altavoz.sonando is None
    assert altavoz.parado_en is not None
    assert [s.texto for s, _ in altavoz.sonados] == ["Sin eco.", eco.texto, eco.texto]
    momentos = [momento for _, momento in altavoz.sonados]
    assert momentos == sorted(momentos)
    assert momentos[-1] <= altavoz.parado_en
    altavoz.suena(eco)
    altavoz.acaba()
    assert altavoz.sonando is None


def test_el_modelo_apunta_cuando_acabo_y_puede_contestar_a_trozos_con_pausa() -> None:
    modelo = ModeloDeMentira(_respuestas(()))
    peticion = LLMRequest(operation_id="op-1", instructions="x", input_text="hola")

    eventos = list(modelo.stream_response(peticion))

    assert [type(evento) for evento in eventos] == [LLMTextDelta, LLMCompleted]
    assert modelo.acabo_en is not None
    assert modelo.acabo_en <= time.perf_counter()

    entre_trozos: list[float | None] = []
    modelo.contesta_despacio(
        ["Primera.", " Segunda."],
        pausa=0.05,
        tras_el_primer_trozo=lambda: entre_trozos.append(modelo.acabo_en),
    )
    antes = time.perf_counter()
    flujo = iter(modelo.stream_response(peticion))

    assert next(flujo) == LLMTextDelta(text="Primera.")
    assert modelo.acabo_en < antes, "con el primer trozo el modelo aún no ha acabado"
    assert entre_trozos == [], "el gancho va con el segundo trozo, no con el primero"
    resto = list(flujo)
    assert resto == [
        LLMTextDelta(text=" Segunda."),
        LLMCompleted(text="Primera. Segunda.", input_tokens=1, output_tokens=17),
    ]
    # Dos pausas de 50 ms; el margen es por el temporizador de Windows.
    assert modelo.acabo_en >= antes + 0.09
    (visto_por_el_gancho,) = entre_trozos
    assert visto_por_el_gancho is None or visto_por_el_gancho < antes, (
        "el gancho vio al modelo escribiendo"
    )
    assert [p.texto for p in modelo.peticiones] == ["hola", "hola"]


def test_el_conductor_se_construye_lee_la_base_de_verdad_y_sus_piezas_pendientes_lo_dicen(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    assert not conductor.micro.abierto
    assert conductor.escrituras_en_disco() == []
    assert conductor.ficheros_de_audio_nuevos() == []
    assert conductor.conexiones_de_red() == []
    assert conductor.procesos_lanzados() == []

    conductor.di("Buenos días, Sirius.")

    assert conductor.charla_guardada()[-2:] == (
        ("propietario", "Buenos días, Sirius."),
        ("Sirius", "Respuesta 1 de Sirius."),
    )
    assert [p.texto for p in conductor.peticiones] == ["Buenos días, Sirius."]
    assert conductor.audio_en_la_base() == []
    conductor.reabre()
    with pytest.raises(PiezaPendiente) as pendiente:
        conductor.oye("Sirius, ¿me oyes?")
    assert pendiente.value.letra == "B"
    conductor.cierra()
    assert conductor.escrituras_en_disco() == []
    assert conductor.ficheros_de_audio_nuevos() == []
    assert conductor.conexiones_de_red() == []


def test_el_diario_es_el_de_produccion_y_se_lee_entero(tmp_path: Path) -> None:
    # Un registrador de módulo que ya existía antes de la migración, como los que
    # usa cada módulo de producción (`get_logger(__name__)`).
    hijo = logging.getLogger("sirius.application.send_message")
    conductor = ConductorDeVoz(tmp_path)

    logging.getLogger(LOGGER_NAME).info("El diario apunta esto: Zarzamora.")
    hijo.info("Y esto lo apunta un módulo: Membrillo.")

    assert conductor.el_diario_contiene("zarzamora")
    assert conductor.el_diario_contiene("membrillo"), "la migración apaga los hijos"
    assert not conductor.el_diario_contiene("cielos despejados")

    # Volver a arrancar vuelve a migrar: el diario tiene que seguir encendido.
    conductor.reabre()
    hijo.info("Y tras reabrir, otro módulo: Alcaparra.")

    assert conductor.el_diario_contiene("alcaparra"), "reabrir apaga los hijos otra vez"
    conductor.cierra()
    assert conductor.escrituras_en_disco() == [], "el diario es una ruta permitida"


def test_el_audio_en_la_base_ve_lo_que_no_cambia_como_la_charla_y_no_una_huella(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.di("Buenos días, Sirius.")
    assert conductor.audio_en_la_base() == [], "la charla escrita cambia la base como la 0.2"
    conductor.cierra()

    def sospechosas() -> list[str]:
        return sorted(conductor.audio_en_la_base())

    huella = struct.pack("<4f", 0.1, 0.2, 0.3, 0.4)
    fila_de_huella = (
        "INSERT INTO memory_embeddings (memory_id, revision_id, model, embedding, created_at)"
        " VALUES (?, ?, 'prueba', ?, '2026-10-13 00:00:00')"
    )
    fila_de_mensaje = (
        "INSERT INTO messages (conversation_id, sequence, role, content, created_at, status)"
        " VALUES (1, ?, 'user', ?, '2026-10-13 00:00:00', 'completed')"
    )
    with closing(sqlite3.connect(conductor.base)) as conexion:
        # Una huella donde van las huellas: la base cambia como cambia charlando.
        conexion.execute(fila_de_huella, (1, 1, huella))
        conexion.commit()
        assert sospechosas() == []

        # Lo que sí cuenta, regla a regla: una tabla nueva, aunque guarde las muestras
        # como filas enteras; una columna nueva; un BLOB fuera de las huellas; una
        # huella con cabecera de audio; un texto largo; y una tabla que crece como una
        # captura.
        conexion.execute("CREATE TABLE audio (id INTEGER PRIMARY KEY, sample INTEGER)")
        conexion.commit()
        assert sospechosas() == ["audio (tabla nueva)"]
        conexion.execute("DROP TABLE audio")
        conexion.execute("ALTER TABLE conversations ADD COLUMN onda BLOB")
        conexion.commit()
        assert sospechosas() == ["conversations.onda (columna nueva)"]
        conexion.execute(fila_de_mensaje, (900, b"\x00\x01" * 100))
        conexion.execute(fila_de_mensaje, (901, "QUJD " * (5 * 1024)))
        conexion.execute(fila_de_huella, (2, 2, b"RIFF\x24\x08\x00\x00WAVEfmt "))
        conexion.commit()
        assert sospechosas() == [
            "conversations.onda (columna nueva)",
            "memory_embeddings.embedding (cabecera de audio)",
            "messages.content (BLOB fuera de las huellas)",
            "messages.content (texto largo)",
        ]
        conexion.execute("DELETE FROM memory_embeddings WHERE memory_id = 2")
        conexion.execute(fila_de_huella, (3, 3, bytes(range(256)) * 80))
        conexion.commit()
        assert "memory_embeddings.embedding (BLOB mayor que una huella)" in sospechosas()
        conexion.executemany(
            "INSERT INTO conversations (created_at, is_main) VALUES ('2026-10-13 00:00:00', 0)",
            [()] * 1_200,
        )
        conexion.commit()
        filas = conexion.execute("SELECT count(*) FROM conversations").fetchone()[0]
        assert f"conversations (+{filas} filas)" in sospechosas()

        # Las sombras de los índices son binarias por construcción, pero ni con cabecera
        # de audio ni mayores que una huella: ahí tampoco cabe un escondite.
        conexion.execute(
            "INSERT INTO message_fts_data (id, block) VALUES (999999, ?)", (b"RIFF\x24\x08WAVE",)
        )
        conexion.execute(
            "INSERT INTO knowledge_fts_data (id, block) VALUES (999999, ?)",
            (bytes(range(256)) * 80,),
        )
        conexion.commit()
    encontrado = sospechosas()
    assert "message_fts_data.block (cabecera de audio)" in encontrado
    assert "knowledge_fts_data.block (BLOB mayor que una huella)" in encontrado

    # Una tabla de la 0.2 que desaparece se dice, y una tabla virtual de un módulo que
    # esta conexión no carga se señala en vez de reventar la comprobación.
    with closing(sqlite3.connect(conductor.base)) as conexion:
        conexion.execute("DROP TABLE reply_marks")
        conexion.enable_load_extension(True)
        sqlite_vec.load(conexion)
        conexion.execute("CREATE VIRTUAL TABLE escondite USING vec0(huella float[4])")
        conexion.commit()
    encontrado = sospechosas()
    assert "reply_marks (tabla que falta)" in encontrado
    assert "escondite (tabla nueva)" in encontrado
    assert "escondite (tabla que no se puede leer)" in encontrado


@pytest.mark.gui
def test_la_ventana_de_voz_lee_la_charla_de_la_ventana_de_verdad(
    qtbot: QtBot, tmp_path: Path
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    ventana = VentanaDeVoz(conductor.abre_la_ventana(qtbot), qtbot)

    ventana.escribe("Buenos días, Sirius.")

    assert ventana.mensajes()[-2:] == (
        ("propietario", "Buenos días, Sirius."),
        ("Sirius", "Respuesta 1 de Sirius."),
    )
