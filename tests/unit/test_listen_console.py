"""La orden ``sirius-oye``: escucha, cuenta cada turno y cierra el micro al salir (ADR-242),
y dice lo que tardó en empezar a hablar (ADR-243). Al salir suelta también la voz (ADR-252).

Solo arranca con la charla en un modelo de Ollama; si Ollama no contesta, dice que lo abra;
calienta las huellas en segundo plano; y la cifra sale antes de cerrar (#696).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import sirius.listen_console as consola
from sirius.adapters.llm.fake import FakeLLMProvider
from sirius.adapters.llm.ollama_chat import OllamaChatProvider
from sirius.adapters.llm.unconfigured import UnconfiguredLLMProvider
from sirius.application.local_listening import CHAT_LEAVES, Attended, HeardTurn
from sirius.application.send_message import SendMessageResult
from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.listen_console import listen
from sirius.ports.llm import LLMErrorKind
from sirius.presentation.error_messages import failed_send_message


def _turno(
    oido: str,
    contesta: str,
    desenlace: MessageStatus = MessageStatus.COMPLETED,
    *,
    por_que: LLMErrorKind | None = None,
    propuesto: str | None = None,
    guardado: str | None = None,
) -> HeardTurn:
    """Un turno con el resultado de la charla tal como lo devuelve ella: los dos mensajes
    guardados, el suyo como quedó (``guardado``, si no es lo oído) y el de Sirius con lo
    que escribió y cómo acabó, y su operación."""
    hoy = datetime(2026, 10, 15, tzinfo=UTC)
    tuyo = Message(1, 1, 1, MessageRole.USER, guardado or oido, hoy, operation_id="op-1")
    suyo = Message(2, 1, 2, MessageRole.SIRIUS, contesta, hoy, "op-1", 1, desenlace)
    resultado = SendMessageResult(desenlace, tuyo, suyo, None, error_kind=por_que)
    return HeardTurn(oido, True, resultado, "op-1", propuesto)


def _roto(oido: str) -> HeardTurn:
    """Un turno cuya charla lanzó una excepción: sin resultado, con su operación."""
    return HeardTurn(oido, True, None, "op-9")


class _Oido:
    def __init__(self, aviso: str = "", atenciones: list[Attended | BaseException] | None = None):
        self.aviso = aviso
        self.atenciones = list(atenciones or [])
        #: Si se cerró: el micro, y la voz con su cancelación de eco (ADR-252).
        self.cerrado = False

    def start(self) -> str:
        return self.aviso

    def attend(self) -> Attended:
        atencion = self.atenciones.pop(0)
        if isinstance(atencion, BaseException):
            raise atencion
        return atencion

    def close(self) -> None:
        self.cerrado = True


def _escucha(
    oido: _Oido, vueltas: int, historia: Callable[[], Sequence[Message]] = list
) -> tuple[int, list[str], int]:
    dicho: list[str] = []
    pausas = 0

    def pausa() -> None:
        nonlocal pausas
        pausas += 1

    quedan = iter([True] * vueltas + [False])
    codigo = listen(
        oido,  # type: ignore[arg-type]
        dicho.append,
        keep_going=lambda: next(quedan),
        pause=pausa,
        history=historia,
    )
    return codigo, dicho, pausas


def test_sin_el_oido_instalado_dice_el_aviso_y_sale_sin_escuchar() -> None:
    oido = _Oido(aviso="Para oírte me falta el modelo. Ejecuta: la orden")

    codigo, dicho, _ = _escucha(oido, 3)

    assert codigo == 1
    assert dicho == ["Para oírte me falta el modelo. Ejecuta: la orden"]
    assert oido.atenciones == []
    # Suelta lo que llegara a cargar: con la voz cargada, el micro pudo no abrirse.
    assert oido.cerrado


def test_cuenta_cada_turno_espera_cuando_no_llega_nada_y_cierra_al_salir() -> None:
    turno = _turno("Buenos días, Sirius.", "Buenos días.")
    oido = _Oido(atenciones=[Attended(), Attended(turns=(turno,))])

    codigo, dicho, pausas = _escucha(oido, 2)

    assert codigo == 0
    assert dicho[1:] == ["Tú: Buenos días, Sirius.", "Sirius: Buenos días."]
    assert pausas == 1
    assert oido.cerrado


def test_lo_que_no_era_para_el_no_se_ensena_ni_para_la_escucha() -> None:
    # ADR-244: no fue a la charla, así que no hay nada que contar, y no es un envío roto.
    tele = HeardTurn("Y mañana, cielos despejados.", False, None, "")
    turno = _turno("Sirius, ¿qué tal?", "Bien.")
    oido = _Oido(atenciones=[Attended(turns=(tele,)), Attended(turns=(turno,))])

    codigo, dicho, _ = _escucha(oido, 2)

    assert codigo == 0
    assert dicho[1:] == ["Tú: Sirius, ¿qué tal?", "Sirius: Bien."]
    assert not any("cielos" in linea for linea in dicho)


def test_si_la_charla_falla_a_medias_ensena_lo_escrito_y_el_aviso_como_la_ventana() -> None:
    # Rondas 12 y 13 de Codex sobre la PR #687: lo que llegó a escribir, con su marca, y el
    # mismo aviso que la ventana para ese fallo, con su referencia, sin adivinar el remedio.
    turno = _turno("Hola", "Ho", MessageStatus.FAILED, por_que=LLMErrorKind.TIMEOUT)
    oido = _Oido(atenciones=[Attended(turns=(turno,))])

    _, dicho, _ = _escucha(oido, 1)

    assert dicho[1:] == [
        "Tú: Hola",
        "Sirius: Ho (fallido)",
        failed_send_message(LLMErrorKind.TIMEOUT, "op-1"),
    ]


def test_si_la_charla_falla_sin_escribir_nada_lo_marca_igual() -> None:
    turno = _turno("Hola", "", MessageStatus.FAILED, por_que=LLMErrorKind.UNKNOWN)
    oido = _Oido(atenciones=[Attended(turns=(turno,))])

    _, dicho, _ = _escucha(oido, 1)

    assert dicho[1:] == [
        "Tú: Hola",
        "Sirius: (fallido)",
        failed_send_message(LLMErrorKind.UNKNOWN, "op-1"),
    ]


def test_si_ollama_no_contesta_dice_que_lo_abra_y_que_no_hace_falta_internet() -> None:
    # #696: con Ollama cerrado decía «Revisa tu red», también en la prueba sin wifi (E-R03-01).
    turno = _turno("Hola", "", MessageStatus.FAILED, por_que=LLMErrorKind.CONNECTION)
    oido = _Oido(atenciones=[Attended(turns=(turno,))])

    _, dicho, _ = _escucha(oido, 1)

    assert dicho[1:] == [
        "Tú: Hola",
        "Sirius: (fallido)",
        "Ollama no contesta en este ordenador: ábrelo. No hace falta internet. (ref: op-1)",
    ]


def test_un_turno_cancelado_se_ensena_como_en_la_ventana() -> None:
    turno = _turno("Hola", "Ho", MessageStatus.CANCELLED)
    oido = _Oido(atenciones=[Attended(turns=(turno,))])

    _, dicho, _ = _escucha(oido, 1)

    assert dicho[1:] == ["Tú: Hola", "Sirius: Ho (cancelado)", "Envío cancelado."]


def test_si_sirius_propone_recordar_algo_dice_donde_confirmarlo() -> None:
    turno = _turno("Me encanta el café", "¡Anotado!", propuesto="Le gusta el café")
    oido = _Oido(atenciones=[Attended(turns=(turno,))])

    _, dicho, _ = _escucha(oido, 1)

    assert dicho[1:] == [
        "Tú: Me encanta el café",
        "Sirius: ¡Anotado!",
        "Sirius propone recordar «Le gusta el café»: lo confirmas o lo rechazas en "
        "Memoria y decisiones, en la ventana.",
    ]


def test_si_deja_de_oir_mientras_escucha_lo_dice_y_sale() -> None:
    # Ronda 11 de Codex sobre la PR #687: la charla se fue a un modelo de fuera mientras
    # oía. El oído para y lo dice; la orden cuenta lo que ya oyó, dice el aviso y sale en
    # vez de esperar a un micro cerrado: otra vuelta pediría una atención que no hay.
    turno = _turno("Buenos días, Sirius.", "Buenos días.")
    oido = _Oido(atenciones=[Attended(turns=(turno,), notice=CHAT_LEAVES)])

    codigo, dicho, pausas = _escucha(oido, 5)

    assert codigo == 1
    assert dicho[1:] == ["Tú: Buenos días, Sirius.", "Sirius: Buenos días.", CHAT_LEAVES]
    assert pausas == 0
    assert oido.cerrado


def test_tras_una_orden_de_olvido_ensena_lo_guardado_y_no_lo_oido() -> None:
    # Ronda 14 de Codex sobre la PR #687: la ventana enseña lo guardado, que ya no dice
    # qué había que olvidar; lo oído sí lo dice, y no puede salir por la consola.
    turno = _turno("Olvida lo de mi vecino Ramiro.", "Hecho.", guardado="Olvida lo de…")
    oido = _Oido(atenciones=[Attended(turns=(turno,))])

    _, dicho, _ = _escucha(oido, 1)

    assert dicho[1:] == ["Tú: Olvida lo de…", "Sirius: Hecho."]
    assert not any("Ramiro" in linea for linea in dicho)


def test_si_la_charla_se_rompe_ensena_lo_guardado_y_el_aviso_como_la_ventana_y_sale() -> None:
    # Ronda 15 de Codex sobre la PR #687: lo que quedó guardado de esa operación, como la
    # ventana al releer la charla, y su aviso con la referencia; nunca lo oído.
    hoy = datetime(2026, 10, 15, tzinfo=UTC)
    otro = Message(1, 1, 1, MessageRole.USER, "Lo de antes", hoy, operation_id="op-0")
    guardado = Message(3, 1, 3, MessageRole.USER, "Olvida lo de…", hoy, operation_id="op-9")
    oido = _Oido(atenciones=[Attended(turns=(_roto("Olvida lo de mi vecino Ramiro."),))])

    codigo, dicho, _ = _escucha(oido, 5, historia=lambda: [otro, guardado])

    assert codigo == 1
    assert dicho[1:] == ["Tú: Olvida lo de…", failed_send_message(None, "op-9")]
    assert not any("Ramiro" in linea for linea in dicho)
    assert oido.cerrado


def test_si_no_quedo_nada_guardado_solo_dice_el_aviso() -> None:
    oido = _Oido(atenciones=[Attended(turns=(_roto("Hola"),))])

    codigo, dicho, _ = _escucha(oido, 5)

    assert codigo == 1
    assert dicho[1:] == [failed_send_message(None, "op-9")]


def test_si_no_se_puede_leer_lo_guardado_lo_dice_como_la_ventana() -> None:
    def rota() -> list[Message]:
        raise RuntimeError("la base no abre")

    oido = _Oido(atenciones=[Attended(turns=(_roto("Hola"),))])

    codigo, dicho, _ = _escucha(oido, 5, historia=rota)

    assert codigo == 1
    assert dicho[1:] == [
        "No se pudo cargar el historial de la conversación.",
        failed_send_message(None, "op-9"),
    ]


def test_un_envio_roto_no_calla_los_turnos_que_venian_con_el() -> None:
    bueno = _turno("Buenos días, Sirius.", "Buenos días.")
    oido = _Oido(atenciones=[Attended(turns=(_roto("Hola"), bueno))])

    codigo, dicho, _ = _escucha(oido, 5)

    assert codigo == 1
    assert dicho[1:] == [
        failed_send_message(None, "op-9"),
        "Tú: Buenos días, Sirius.",
        "Sirius: Buenos días.",
    ]


def test_con_ctrl_c_tambien_cierra_el_micro() -> None:
    oido = _Oido(atenciones=[KeyboardInterrupt()])

    with pytest.raises(KeyboardInterrupt):
        _escucha(oido, 5)

    assert oido.cerrado


# --- Lo que tardó en empezar a hablar (E-R03-02) -------------------------------------


def _hablado(segundos: float) -> HeardTurn:
    """Un turno contestado en voz alta, que empezó a sonar ``segundos`` después de su voz."""
    turno = _turno("Hola", "Hola.")
    return HeardTurn(
        turno.heard, True, turno.result, turno.operation_id, first_sound_delay=segundos
    )


def test_al_salir_dice_el_p95_de_lo_que_tardo_en_empezar_a_hablar() -> None:
    # Veinte turnos, de 0,1 s a 2,0 s: el P95 por el rango más cercano es el 19.º.
    turnos = [_hablado(n / 10) for n in range(20, 0, -1)]
    oido = _Oido(atenciones=[Attended(turns=(t,)) for t in turnos])

    codigo, dicho, _ = _escucha(oido, 20)

    assert codigo == 0
    assert dicho[-1] == (
        "En 20 turnos, desde que dejé de oír tu voz hasta el primer sonido: P95 de 1,90 s."
    )


def test_lo_dice_tambien_si_sale_con_ctrl_c() -> None:
    oido = _Oido(atenciones=[Attended(turns=(_hablado(1.234),)), KeyboardInterrupt()])
    dicho: list[str] = []

    with pytest.raises(KeyboardInterrupt):
        listen(
            oido,  # type: ignore[arg-type]
            dicho.append,
            keep_going=lambda: True,
            pause=lambda: None,
            history=list,
        )

    assert dicho[-1] == (
        "En 1 turno, desde que dejé de oír tu voz hasta el primer sonido: P95 de 1,23 s."
    )
    assert oido.cerrado


def test_sin_nada_dicho_no_dice_cuanto_tardo() -> None:
    oido = _Oido(atenciones=[Attended(turns=(_turno("Hola", "---"),))])

    _, dicho, _ = _escucha(oido, 1)

    assert not any("primer sonido" in linea for linea in dicho)


class _OidoQueTardaEnCerrar(_Oido):
    """Mientras cierra, le llega un segundo Ctrl+C: cerrar suelta la voz y tarda."""

    def __init__(self, atenciones: list[Attended | BaseException], dicho: list[str]) -> None:
        super().__init__(atenciones=atenciones)
        self._dicho = dicho
        self.dicho_al_cerrar: list[str] = []

    def close(self) -> None:
        self.dicho_al_cerrar = list(self._dicho)
        raise KeyboardInterrupt


def test_la_cifra_sale_antes_de_cerrar_y_un_segundo_ctrl_c_no_se_la_lleva() -> None:
    # #696: salía después de cerrar el micro y soltar la voz, y un segundo Ctrl+C mientras
    # cerraba se la llevaba.
    dicho: list[str] = []
    oido = _OidoQueTardaEnCerrar([Attended(turns=(_hablado(1.234),)), KeyboardInterrupt()], dicho)
    cifra = "En 1 turno, desde que dejé de oír tu voz hasta el primer sonido: P95 de 1,23 s."

    with pytest.raises(KeyboardInterrupt):
        listen(
            oido,  # type: ignore[arg-type]
            dicho.append,
            keep_going=lambda: True,
            pause=lambda: None,
            history=list,
        )

    assert dicho[-1] == cifra
    assert oido.dicho_al_cerrar[-1] == cifra


# --- Al arrancar (main) ----------------------------------------------------------------


class _Huellas:
    """El servicio de huellas: apunta lo que se le pide, desde qué hilo, y si tuvo que
    esperar a que se escuchara para seguir."""

    def __init__(self, pendientes: int = 0, falla: Exception | None = None) -> None:
        self.pendientes = pendientes
        self.falla = falla
        self.llamadas: list[str] = []
        self.hilos: list[threading.Thread] = []
        self.parar: Callable[[], bool] = lambda: False
        self.escuchando = threading.Event()
        #: Si al calcularlas ya se estaba escuchando: nadie esperó a las huellas.
        self.vio_escuchar = False
        self.acabadas = threading.Event()

    def embed_pending(self, should_stop: Callable[[], bool] = lambda: False) -> int:
        self.llamadas.append("calcula las que faltan")
        self.hilos.append(threading.current_thread())
        self.parar = should_stop
        try:
            self.vio_escuchar = self.escuchando.wait(timeout=5)
            if self.falla is not None:
                raise self.falla
            return self.pendientes
        finally:
            if self.falla is not None or self.pendientes:
                self.acabadas.set()

    def warm_up(self) -> None:
        self.llamadas.append("carga el modelo")
        self.acabadas.set()


@pytest.fixture
def arranque(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[Callable[..., SimpleNamespace]]:
    """``main`` con lo de fuera de mentira: devuelve con qué se arrancó y lo que pasó."""
    proveedores: list[OllamaChatProvider] = []

    def arranca(charla: object | None = None, huellas: _Huellas | None = None) -> SimpleNamespace:
        if charla is None:
            ollama = OllamaChatProvider("qwen3:4b-instruct")
            proveedores.append(ollama)
            charla = ollama
        huellas = huellas or _Huellas()
        visto = SimpleNamespace(orden=[], huellas=huellas, codigo=None)
        dependencias = SimpleNamespace(
            initial_project_use_case=SimpleNamespace(is_configured=lambda: True),
            send_message_use_case=SimpleNamespace(
                llm_provider=charla,
                warm_up_in_background=lambda: visto.orden.append("precarga"),
            ),
            memory_embedding_service=huellas,
            local_listening=object(),
            get_history_use_case=SimpleNamespace(get_history=list),
            close_database_connections=lambda: visto.orden.append("cierra la base"),
        )
        rutas = SimpleNamespace(logs_dir=tmp_path, data_dir=tmp_path, backups_dir=tmp_path)

        def escucha(*args: object, **kwargs: object) -> int:
            visto.orden.append("escucha")
            huellas.escuchando.set()
            return 0

        monkeypatch.setattr(consola, "hugging_face_offline", lambda: None)
        monkeypatch.setattr(consola, "known_data_paths", lambda: rutas)
        monkeypatch.setattr(consola, "configure_logging", lambda carpeta: None)
        monkeypatch.setattr(consola, "initialize_persistence", lambda rutas: None)
        monkeypatch.setattr(
            consola, "build_conversation_dependencies", lambda *a, **k: dependencias
        )
        monkeypatch.setattr(consola, "listen", escucha)
        visto.codigo = consola.main()
        return visto

    yield arranca
    for proveedor in proveedores:
        proveedor.close()


def test_al_arrancar_pide_que_el_modelo_de_la_charla_vaya_cargando(
    arranque: Callable[..., SimpleNamespace],
) -> None:
    visto = arranque()

    assert visto.codigo == 0
    # Antes de escuchar: va cargando mientras carga la voz.
    assert visto.orden == ["precarga", "escucha", "cierra la base"]


class _DeFuera:
    """Un modelo que no dice ser de este ordenador, como el de OpenAI."""


#: Lo que dice sin un modelo de este ordenador: lo lee él tal cual.
_SIN_MODELO = (
    "No puedo oírte: la charla todavía no tiene un modelo de este ordenador. Elige uno en la "
    "ventana de Sirius: Configuración, «Elegir el modelo a ciegas…»."
)


@pytest.mark.parametrize(
    ("charla", "aviso"),
    [
        (FakeLLMProvider(), _SIN_MODELO),
        (UnconfiguredLLMProvider("Haz la prueba a ciegas para elegirlo."), _SIN_MODELO),
        (_DeFuera(), CHAT_LEAVES),
    ],
    ids=["simulada", "sin configurar", "de fuera"],
)
def test_sin_un_modelo_de_ollama_no_arranca_y_dice_como_elegirlo(
    arranque: Callable[..., SimpleNamespace],
    capsys: pytest.CaptureFixture[str],
    charla: object,
    aviso: str,
) -> None:
    # #696: con la simulada contestaba «Respuesta simulada de Sirius.» y daba un P95 que no
    # era de ningún modelo; sin configurar, cada frase salía fallida.
    visto = arranque(charla)

    assert visto.codigo == 2
    assert capsys.readouterr().out == f"{aviso}\n"
    # Ni escucha ni carga nada: solo cierra la base.
    assert visto.orden == ["cierra la base"]
    assert visto.huellas.llamadas == []


def test_el_aviso_sin_modelo_lleva_a_elegirlo_como_el_de_un_modelo_de_fuera() -> None:
    # La pestaña y el botón de CHAT_LEAVES son los de verdad (ADR-252): este nombra los mismos.
    como_elegirlo = "Configuración, «Elegir el modelo a ciegas…»."

    assert CHAT_LEAVES.endswith(como_elegirlo)
    assert _SIN_MODELO.endswith(como_elegirlo)


def test_al_arrancar_calcula_las_huellas_que_faltan_sin_que_la_escucha_espere(
    arranque: Callable[..., SimpleNamespace],
) -> None:
    # #696: la ventana lo hace al abrirse; sirius-oye no, y el primer turno lo esperaba.
    huellas = _Huellas(pendientes=1)

    visto = arranque(huellas=huellas)

    assert huellas.acabadas.wait(timeout=5)
    assert visto.codigo == 0
    assert huellas.llamadas == ["calcula las que faltan"]
    assert huellas.vio_escuchar
    [hilo] = huellas.hilos
    assert hilo is not threading.main_thread()
    assert hilo.daemon
    # Al salir se le pide parar, antes de cerrar la base.
    assert huellas.parar()


def test_sin_huellas_que_calcular_carga_el_modelo_de_huellas() -> None:
    huellas = _Huellas(pendientes=0)
    huellas.escuchando.set()

    consola.warm_up_embeddings_in_background(huellas, lambda: False).join(timeout=5)  # type: ignore[arg-type]

    assert huellas.llamadas == ["calcula las que faltan", "carga el modelo"]


def test_si_ya_le_pidieron_parar_no_carga_el_modelo_de_huellas() -> None:
    huellas = _Huellas(pendientes=0)
    huellas.escuchando.set()

    consola.warm_up_embeddings_in_background(huellas, lambda: True).join(timeout=5)  # type: ignore[arg-type]

    assert huellas.llamadas == ["calcula las que faltan"]


class _Diario(logging.Handler):
    """Lo que apunta el registrador de la orden. Se lee de él, no de la raíz: con el diario
    de Sirius ya configurado en el mismo proceso, ``sirius`` no propaga (ADR-248)."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.lineas: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lineas.append(record.getMessage())


@pytest.fixture
def diario() -> Iterator[_Diario]:
    registrador = logging.getLogger(consola.__name__)
    nivel = registrador.level
    manejador = _Diario()
    registrador.addHandler(manejador)
    registrador.setLevel(logging.DEBUG)
    yield manejador
    registrador.removeHandler(manejador)
    registrador.setLevel(nivel)


def test_si_las_huellas_fallan_no_rompen_la_escucha_y_el_diario_solo_dice_el_tipo(
    arranque: Callable[..., SimpleNamespace], diario: _Diario
) -> None:
    huellas = _Huellas(falla=RuntimeError("Ollama dijo: Le pirra el cocido"))

    visto = arranque(huellas=huellas)
    assert huellas.acabadas.wait(timeout=5)
    huellas.hilos[0].join(timeout=5)

    assert visto.codigo == 0
    assert visto.orden == ["precarga", "escucha", "cierra la base"]
    assert diario.lineas == ["Las huellas se interrumpieron (RuntimeError)"]
