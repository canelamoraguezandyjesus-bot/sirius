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

import array
import base64
import json
import logging
import sqlite3
import struct
import time
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

import pytest
import sqlite_vec
from conductor_robot_0_2 import _respuestas
from conductor_robot_0_3 import (
    MARCA_DEL_AUDIO,
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
    _formas_del_audio_en,
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
    # Cada lectura lleva bytes como los de un micro de verdad: un segundo de ruido, el
    # mismo para el mismo texto y distinto para otro, con la marca en cada 1 000 bytes.
    lectura = Audio("Hola, Sirius.")
    assert len(lectura.muestras) == 32_000
    assert lectura.muestras == Audio("Hola, Sirius.").muestras != Audio("Otra.").muestras
    assert [
        lectura.muestras[i : i + 1_000].count(MARCA_DEL_AUDIO) for i in range(0, 32_000, 1_000)
    ] == [1] * 32
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
    assert conductor.ficheros_nuevos() == []
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
    assert conductor.ficheros_nuevos() == []
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


def test_el_audio_en_la_base_ve_lo_que_no_cambia_como_la_charla_regla_a_regla(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.di("Buenos días, Sirius.")
    assert conductor.audio_en_la_base() == [], "la charla escrita cambia la base como la 0.2"
    conductor.cierra()

    def foto() -> list[str]:
        # Solo la foto final: lo que vieron los disparadores y el trazador mientras el
        # conductor vivía se prueba aparte, y aquí se escribe con él ya cerrado.
        vivo = set(conductor._escrituras_sospechosas_en_la_base())
        return sorted(v for v in conductor.audio_en_la_base() if v not in vivo)

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
        # Una huella donde van las huellas también cuenta: el modelo de huellas de estas
        # pruebas no da ninguna, así que la charla no escribe binario en ninguna parte.
        conexion.execute(fila_de_huella, (1, 1, huella))
        conexion.commit()
        assert foto() == [
            "memory_embeddings.embedding (BLOB, y la charla de estas pruebas no escribe ninguno)"
        ]
        conexion.execute("DELETE FROM memory_embeddings")
        conexion.commit()
        assert foto() == []
        # Los disparadores viven en la base, no en una conexión: vieron la huella entrar
        # y salir por una conexión abierta con el conductor ya cerrado.
        assert (
            "memory_embeddings.embedding (BLOB de 16 bytes al insertar)"
            in conductor.audio_en_la_base()
        )
        assert (
            "memory_embeddings.embedding (BLOB de 16 bytes al borrar)"
            in conductor.audio_en_la_base()
        )

        # Lo que sí cuenta, regla a regla: una tabla nueva, aunque guarde las muestras
        # como filas enteras; una columna nueva; un BLOB en la charla; un texto largo; y
        # una tabla que crece como una captura.
        conexion.execute("CREATE TABLE audio (id INTEGER PRIMARY KEY, sample INTEGER)")
        conexion.commit()
        assert foto() == ["audio (tabla nueva)"]
        conexion.execute("DROP TABLE audio")
        conexion.execute("ALTER TABLE conversations ADD COLUMN onda BLOB")
        conexion.commit()
        assert foto() == ["conversations.onda (columna nueva)"]
        conexion.execute(fila_de_mensaje, (900, b"\x00\x01" * 100))
        conexion.execute(fila_de_mensaje, (901, "QUJD " * (5 * 1024)))
        conexion.commit()
        assert foto() == [
            "conversations.onda (columna nueva)",
            "messages.content (BLOB, y la charla de estas pruebas no escribe ninguno)",
            "messages.content (texto largo)",
        ]
        conexion.executemany(
            "INSERT INTO conversations (created_at, is_main) VALUES ('2026-10-13 00:00:00', 0)",
            [()] * 1_200,
        )
        conexion.commit()
        filas = conexion.execute("SELECT count(*) FROM conversations").fetchone()[0]
        assert f"conversations (+{filas} filas)" in foto()

        # Las sombras de los índices son binarias por construcción, pero ni con cabecera
        # de audio ni en bloques de más de 16 KiB: ahí tampoco cabe un escondite.
        conexion.execute(
            "INSERT INTO message_fts_data (id, block) VALUES (999999, ?)", (b"RIFF\x24\x08WAVE",)
        )
        conexion.execute(
            "INSERT INTO knowledge_fts_data (id, block) VALUES (999999, ?)",
            (bytes(range(256)) * 80,),
        )
        conexion.commit()
    encontrado = foto()
    assert "message_fts_data.block (cabecera de audio)" in encontrado
    assert "knowledge_fts_data.block (bloque mayor de 16 KiB)" in encontrado

    # Una tabla de la 0.2 que desaparece se dice, y una tabla virtual de un módulo que
    # esta conexión no carga se señala en vez de reventar la comprobación.
    with closing(sqlite3.connect(conductor.base)) as conexion:
        conexion.execute("DROP TABLE reply_marks")
        conexion.enable_load_extension(True)
        sqlite_vec.load(conexion)
        conexion.execute("CREATE VIRTUAL TABLE escondite USING vec0(huella float[4])")
        conexion.commit()
    encontrado = foto()
    assert "reply_marks (tabla que falta)" in encontrado
    assert "escondite (tabla nueva)" in encontrado
    assert "escondite (tabla que no se puede leer)" in encontrado


def test_la_base_se_vigila_fila_a_fila_tambien_lo_que_se_borra_antes_de_acabar(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.di("Buenos días, Sirius.")
    assert conductor.audio_en_la_base() == []
    escritas = conductor.sentencias_que_escriben()
    assert any(s.startswith("INSERT INTO messages") for s in escritas), escritas
    assert any(s.startswith("-- REPLACE INTO 'main'.'message_fts_") for s in escritas)

    fila_de_mensaje = (
        "INSERT INTO messages (conversation_id, sequence, role, content, created_at, status)"
        " VALUES (1, ?, 'user', ?, '2026-10-13 00:00:00', 'completed')"
    )
    onda = b"RIFF\x24\x08WAVE" + bytes(range(256)) * 8
    # Una conexión abierta mientras Sirius vive, como la de una pieza, que lo borra todo
    # antes de que nadie mire. La foto final queda limpia; lo que pasó, no.
    with closing(sqlite3.connect(conductor.base)) as conexion:
        # Lo evidente: audio y un texto largo, con sus valores en la sentencia.
        conexion.execute(fila_de_mensaje, (950, onda))
        conexion.execute(fila_de_mensaje, (951, "QUJD " * (5 * 1024)))
        conexion.execute("DELETE FROM messages WHERE sequence IN (950, 951)")
        # Lo que no está en el texto de ninguna sentencia: un hueco que se rellena a
        # trozos con ``blobopen`` (donde van las huellas, que no tienen índice de texto
        # que proteste); una función de Python que devuelve el audio; y una función que
        # lo inserta desde dentro de otra sentencia.
        conexion.execute(
            "INSERT INTO memory_embeddings (memory_id, revision_id, model, embedding, created_at)"
            " VALUES (952, 952, 'prueba', zeroblob(?), '2026-10-13 00:00:00')",
            (len(onda),),
        )
        hueco = conexion.execute(
            "SELECT rowid FROM memory_embeddings WHERE memory_id = 952"
        ).fetchone()[0]
        with conexion.blobopen("memory_embeddings", "embedding", hueco) as trozo_a_trozo:
            trozo_a_trozo.write(onda)
        conexion.create_function("onda", 0, lambda: onda)
        conexion.execute(
            "INSERT INTO messages (conversation_id, sequence, role, content, created_at, status)"
            " SELECT 1, 953, 'user', onda(), '2026-10-13 00:00:00', 'completed'"
        )

        def desde_dentro() -> int:
            conexion.execute(fila_de_mensaje, (954, onda))
            return 1

        conexion.create_function("desde_dentro", 0, desde_dentro)
        conexion.execute("SELECT desde_dentro()").fetchone()
        conexion.execute("DELETE FROM memory_embeddings WHERE memory_id = 952")
        conexion.execute("DELETE FROM messages WHERE sequence IN (953, 954)")
        # Audio del micro guardado como texto corto, en base64 y como lista JSON: sin
        # BLOB ni texto largo, pero con la marca dentro.
        lectura = Audio("Pues yo fatal.")
        conexion.execute(
            fila_de_mensaje, (955, base64.b64encode(lectura.muestras[:9_000]).decode())
        )
        conexion.execute(fila_de_mensaje, (956, json.dumps(list(lectura.muestras[:1_500]))))
        conexion.execute("DELETE FROM messages WHERE sequence IN (955, 956)")
        # Muchas filas de golpe desde otra consulta, y mucho texto en trozos cortos: se
        # cuentan las filas y el texto de verdad, no las sentencias.
        conexion.execute(
            "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n WHERE x < 5000)"
            " INSERT INTO conversations (created_at, is_main)"
            " SELECT '2026-10-13 00:00:00', 0 FROM n"
        )
        conexion.execute("DELETE FROM conversations WHERE created_at = '2026-10-13 00:00:00'")
        conexion.executemany(fila_de_mensaje, [(1000 + n, "a" * (15 * 1024)) for n in range(40)])
        conexion.execute("DELETE FROM messages WHERE sequence >= 1000")
        # Una tabla nueva, y una tabla virtual que escribe en sus sombras desde dentro de
        # la sentencia: el esquema cambió, y esas sombras no son las de los índices.
        conexion.execute("CREATE TABLE audio (id INTEGER PRIMARY KEY, sample INTEGER)")
        conexion.execute("DROP TABLE audio")
        conexion.enable_load_extension(True)
        sqlite_vec.load(conexion)
        conexion.execute("CREATE VIRTUAL TABLE escondite USING vec0(huella float[4])")
        conexion.execute(
            "INSERT INTO escondite (rowid, huella) VALUES (1, ?)", (struct.pack("<4f", 1, 2, 3, 4),)
        )
        conexion.execute("DROP TABLE escondite")
        # Tocar la vigilancia o la estructura a mano, o apagar los disparadores, se dice.
        conexion.execute("UPDATE _vigilancia_filas SET filas = 0 WHERE tabla = 'ninguna'")
        conexion.execute("PRAGMA writable_schema = ON")
        conexion.execute("PRAGMA writable_schema = OFF")
        conexion.setconfig(sqlite3.SQLITE_DBCONFIG_ENABLE_TRIGGER, False)
        conexion.setconfig(sqlite3.SQLITE_DBCONFIG_ENABLE_TRIGGER, True)
        conexion.commit()
    # Una conexión que no pasa por ``sqlite3.connect`` no se puede seguir: se dice.
    with closing(sqlite3.Connection(str(conductor.base))) as directa:
        directa.execute("SELECT count(*) FROM messages").fetchone()
    # Una base aparte, al lado de la de Sirius, la crea SQLite en C sin pasar por ``open``
    # y no es audio por su extensión: la foto del disco la ve, y el trazador, que se
    # escribió en ella.
    aparte = conductor.base.parent / "cache.db"
    with closing(sqlite3.connect(aparte)) as otra:
        otra.execute("CREATE TABLE trozos (onda BLOB)")
        otra.execute("INSERT INTO trozos VALUES (?)", (b"OggS" + bytes(64),))
        otra.commit()
    conductor.cierra()
    assert conductor.ficheros_nuevos() == [aparte]

    visto = conductor.audio_en_la_base()
    con_audio = f"messages.content (BLOB con cabecera de audio de {len(onda)} bytes"
    assert visto.count(f"{con_audio} al insertar)") == 3, visto  # 950, 953 y 954
    assert visto.count(f"{con_audio} al borrar)") == 3, visto
    assert f"memory_embeddings.embedding (BLOB de {len(onda)} bytes al insertar)" in visto
    assert (
        f"memory_embeddings.embedding (BLOB con cabecera de audio de {len(onda)} bytes al borrar)"
        in visto
    )
    assert "messages.content (texto de 25600 caracteres al insertar)" in visto
    assert "messages.content (texto con audio del micro en base64 al insertar)" in visto
    assert "messages.content (texto con audio del micro como lista de bytes al insertar)" in visto
    assert "messages (escritura dentro de otra sentencia, fuera de las sombras)" in visto
    assert "conversations (+5000 filas escritas)" in visto
    assert any(
        v.startswith("la base (escribió ") and v.endswith(" caracteres de texto desde el arranque)")
        for v in visto
    ), visto
    assert "audio (esquema cambiado fuera del arranque)" in visto
    assert "escondite (esquema cambiado fuera del arranque)" in visto
    assert any(
        v.startswith("escondite_")
        and v.endswith("(escritura dentro de otra sentencia, fuera de las sombras)")
        for v in visto
    ), visto
    assert "_vigilancia_filas (tocó la vigilancia de la prueba)" in visto
    assert any(v.startswith("la base (tocó la estructura a mano: PRAGMA") for v in visto), visto
    assert "la base (una conexión apagó los disparadores)" in visto
    assert "la base (una conexión que el vigilante no pudo seguir)" in visto
    assert f"otra base escrita ({aparte})" in visto
    # La foto final, sola, habría visto solo el rastro de la tabla vectorial: la tabla
    # interna de los autoincrementos que sus sombras crearon. Todo lo demás se borró.
    vivo = set(conductor._escrituras_sospechosas_en_la_base())
    assert [v for v in visto if v not in vivo] == ["sqlite_sequence (tabla nueva)"]


def test_la_marca_del_audio_se_reconoce_en_cada_variante_de_cada_forma() -> None:
    muestras = Audio("Pues yo fatal.").muestras
    # Trozos de un kilobyte con una sola marca, que empiezan en sitios distintos para
    # que la marca caiga en cada desfase de un grupo de tres bytes y de una muestra de 16
    # bits.
    trozos = [muestras[inicio : inicio + 1_000] for inicio in (0, 1, 2, 37)]
    variantes: list[tuple[str, str]] = []
    for trozo in trozos:
        variantes += [
            ("como texto", repr(trozo)),
            ("como texto", trozo.decode("latin-1")),
            ("en hexadecimal", trozo.hex()),
            ("en hexadecimal", trozo.hex().upper()),
            ("en hexadecimal", trozo.hex(" ")),
            ("en base64", base64.b64encode(trozo).decode()),
            ("en base64", base64.urlsafe_b64encode(trozo).decode()),
            ("en base64", base64.encodebytes(trozo).decode()),
            ("como lista de bytes", str(list(trozo))),
            ("como lista de bytes", json.dumps(list(trozo))),
            ("como muestras de 16 bits", repr(array.array("h", trozo[: len(trozo) // 2 * 2]))),
        ]
    for forma, texto in variantes:
        assert forma in _formas_del_audio_en(texto), (forma, texto[:60])
    # Y ningún mensaje legítimo, por largo que sea, lleva la marca.
    assert _formas_del_audio_en("el oído lleva 1234 bloques sin voz\n" * 5_000) == []
    assert _formas_del_audio_en(json.dumps(list(range(256)) * 50)) == []


def test_el_audio_del_micro_en_el_diario_se_ve_en_cada_forma_y_los_mensajes_no_cuentan(
    tmp_path: Path,
) -> None:
    conductor = ConductorDeVoz(tmp_path)
    for frase in ("Buenos días, Sirius.", "¿Qué tal has dormido?", "Pues yo fatal."):
        conductor.di(frase)
    assert conductor.audio_en_el_diario() == []

    registro = logging.getLogger(f"{LOGGER_NAME}.una_pieza")
    # Muchos mensajes del registro, cortos y largos, más de lo que escribe una charla: no
    # cuentan, porque no llevan la marca del audio.
    for numero in range(2_000):
        registro.warning("el oído lleva %d bloques sin voz", numero)
    registro.warning("ajustes: %s", "voz=es_ES-davefx-medium; " * 400)
    assert conductor.audio_en_el_diario() == []

    # Una lectura del micro volcada por error, en cada forma en que Python escribe unos
    # bytes: cada una se ve, y solo esa.
    lectura = Audio("Pues yo fatal.")
    volcados: tuple[tuple[str, Callable[[], None]], ...] = (
        ("como texto", lambda: registro.warning("leído: %r", lectura)),
        # Un kilobyte con una sola marca, que cae a mitad de un grupo de tres bytes y que
        # ``encodebytes`` parte con un salto de línea.
        (
            "en base64",
            lambda: registro.warning("%s", base64.encodebytes(lectura.muestras[37:1_037]).decode()),
        ),
        ("en hexadecimal", lambda: registro.warning("%s", lectura.muestras[:2_000].hex(" "))),
        ("como lista de bytes", lambda: registro.warning("%s", list(lectura.muestras[:2_000]))),
        (
            "como muestras de 16 bits",
            lambda: registro.warning("%r", array.array("h", lectura.muestras[1:2_001])),
        ),
    )
    vistas: list[str] = []
    for forma, vuelca in volcados:
        vuelca()
        vistas.append(f"el diario (guarda audio del micro {forma})")
        assert sorted(conductor.audio_en_el_diario()) == sorted(vistas), forma
    conductor.cierra()


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
