"""Probar el oído y la voz del robot en consola: ``uv run --extra voz sirius-oye``.

ADR-242 y ADR-243. Sirius le oye en local, le contesta hablando y escribe lo que oyó y lo
que contesta, en la misma charla de la ventana, hasta Ctrl+C; no abre la ventana (pieza
D). Si falta algo de la voz, dice qué orden lo instala y sale sin hacer nada más. Si deja
de oír mientras escucha, porque la charla se fue a un modelo de fuera o porque falló una
pieza del oído o de la voz, lo dice y sale; y si un envío se rompe, cuenta lo que quedó
guardado, como la ventana, y sale con error. Lo que oye y no era para él no lo enseña:
no es de la charla (ADR-244).

Al salir dice cuánto tardó en empezar a hablar: es la cifra de E-R03-02.

Solo arranca con la charla en un modelo de Ollama de este ordenador: con la simulada o sin
configurar, oiría y contestaría igual, y la cifra no sería la de ningún modelo (#696).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Sequence
from typing import Any

from sirius.adapters.audio.voice_libraries import hugging_face_offline
from sirius.adapters.llm.ollama_chat import OllamaChatProvider
from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.application.listening_loop import PAUSE_SECONDS
from sirius.application.local_listening import CHAT_LEAVES, HeardTurn, LocalListening
from sirius.application.memory_search import MemoryEmbeddingService
from sirius.composition_root import (
    DATA_PATHS_UNKNOWN,
    build_conversation_dependencies,
    known_data_paths,
)
from sirius.domain.conversation import Message, MessageRole, MessageStatus
from sirius.infrastructure.logging import configure_logging, get_logger
from sirius.ports.llm import LLMErrorKind, runs_on_this_computer
from sirius.presentation.error_messages import failed_send_message
from sirius.presentation.message_text import CANCELLED_SEND, HISTORY_NOT_LOADED, message_body

_logger = get_logger(__name__)

#: Lo que dice si la charla es de este ordenador pero no tiene un modelo de Ollama: está
#: sin configurar o es la simulada (#696). Acaba como CHAT_LEAVES, con cómo elegirlo.
NO_LOCAL_MODEL = (
    "No puedo oírte: la charla todavía no tiene un modelo de este ordenador. Elige uno en la "
    "ventana de Sirius: Configuración, «Elegir el modelo a ciegas…»."
)

#: Lo que dice si Ollama no contesta: la charla de esta orden solo va a Ollama, y aquí no
#: hace falta internet, también en la prueba que va sin wifi (#696).
OLLAMA_UNREACHABLE = "Ollama no contesta en este ordenador: ábrelo. No hace falta internet."


def listen(
    listening: LocalListening[Any],
    say: Callable[[str], None],
    *,
    keep_going: Callable[[], bool],
    pause: Callable[[], None],
    history: Callable[[], Sequence[Message]],
) -> int:
    """Escucha mientras ``keep_going`` lo diga y cuenta cada turno; al salir cierra el micro y
    suelta la voz, también si no llegó a escuchar (ADR-252).

    Cada turno lo cuenta como la ventana uno escrito, con lo guardado y no con lo oído
    (rondas 11 a 15 de Codex sobre la PR #687); ``history`` es la charla guardada, la que
    la ventana vuelve a leer tras un envío roto. Si un envío se rompe, cuenta los turnos
    que ya traía y sale con error; y si el oído deja de oír por su cuenta, dice su aviso y
    sale, en vez de seguir esperando a un micro cerrado.
    """
    delays: list[float] = []
    try:
        notice = listening.start()
        if notice:
            say(notice)
            return 1
        say("Te escucho. Habla cuando quieras; Ctrl+C para salir.")
        while keep_going():
            attended = listening.attend()
            broken = False
            for turn in attended.turns:
                if not turn.addressed:
                    # No fue a la charla: ni se enseña ni es un envío roto.
                    continue
                broken = _say_turn(turn, say, history) or broken
                if turn.first_sound_delay is not None:
                    delays.append(turn.first_sound_delay)
            if attended.notice:
                say(attended.notice)
                return 1
            if broken:
                return 1
            if not attended.turns:
                pause()
    finally:
        # La cifra, antes de cerrar: cerrar tarda, y un segundo Ctrl+C mientras se la
        # llevaría (#696).
        if delays:
            say(_delays_line(delays))
        listening.close()
    return 0


def _delays_line(delays: Sequence[float]) -> str:
    """Lo que tardó en empezar a hablar en los turnos de esta vez, con su P95 (E-R03-02).

    Por el rango más cercano, como PA-R03-09: con 20 turnos, el 19.º de menos a más.
    """
    ordered = sorted(delays)
    p95 = ordered[max(0, -(-95 * len(ordered) // 100) - 1)]
    turns = "1 turno" if len(ordered) == 1 else f"{len(ordered)} turnos"
    return (
        f"En {turns}, desde que dejé de oír tu voz hasta el primer sonido: P95 de "
        f"{f'{p95:.2f}'.replace('.', ',')} s."
    )


def _say_turn(
    turn: HeardTurn, say: Callable[[str], None], history: Callable[[], Sequence[Message]]
) -> bool:
    """El turno como lo enseña la ventana al acabar uno escrito (``_on_finished``), línea a
    línea y con lo guardado, nunca con lo oído; devuelve si el envío se rompió:

    - lo suyo, como quedó guardado (``_settle_user_item``): tras «olvida lo de…» ya no
      dice qué había que olvidar (ronda 14 de Codex sobre la PR #687);
    - la respuesta, con la marca de cómo acabó, también lo que llegó a escribir si falló;
    - si no acabó bien, el mismo aviso que ella;
    - y lo que el modelo propuso recordar, que ella deja en Memoria y decisiones.

    Si el envío se rompió con una excepción, como ella en ``_on_crashed``: lo que quedó
    guardado de esa operación y el aviso de siempre, con su referencia (ronda 15).
    """
    result = turn.result
    if result is None:
        _say_broken(turn.operation_id, say, history)
        return True
    say(_line("Tú", result.user_message))
    say(_line("Sirius", result.sirius_message))
    if result.outcome is MessageStatus.CANCELLED:
        say(CANCELLED_SEND)
    elif result.outcome is MessageStatus.FAILED and result.error_kind is LLMErrorKind.CONNECTION:
        # Aquí la charla solo va a Ollama: «revisa tu red» mandaría a encender el wifi.
        say(f"{OLLAMA_UNREACHABLE} (ref: {result.sirius_message.operation_id})")
    elif result.outcome is MessageStatus.FAILED:
        say(failed_send_message(result.error_kind, result.sirius_message.operation_id))
    if turn.proposed is not None:
        say(
            f"Sirius propone recordar «{turn.proposed}»: lo confirmas o lo rechazas en "
            "Memoria y decisiones, en la ventana."
        )
    return False


def _say_broken(
    operation_id: str, say: Callable[[str], None], history: Callable[[], Sequence[Message]]
) -> None:
    """Lo que quedó guardado de la operación rota, y el aviso que pone la ventana."""
    try:
        saved = [message for message in history() if message.operation_id == operation_id]
    except Exception as error:
        _logger.error("No se pudo leer lo guardado tras el envío roto (%s)", type(error).__name__)
        say(HISTORY_NOT_LOADED)
        saved = []
    for message in saved:
        say(_line("Tú" if message.role is MessageRole.USER else "Sirius", message))
    say(failed_send_message(None, operation_id))


def _line(who: str, message: Message) -> str:
    """Una línea de la charla con el texto que enseña la ventana de ese mensaje."""
    body = message_body(message.content, message.status).strip()
    return f"{who}: {body}" if body else f"{who}:"


def without_a_local_model(provider: object) -> str:
    """Por qué no puede oír con la charla en ``provider``; vacío si es un modelo de Ollama.

    Uno de fuera, lo de siempre (CHAT_LEAVES). Uno de este ordenador que no es de Ollama, la
    charla simulada o sin configurar, no es ningún modelo: contestaría o fallaría sin que
    nada lo pare, y la cifra de E-R03-02 no sería de nadie (#696).
    """
    if isinstance(provider, OllamaChatProvider):
        return ""
    return NO_LOCAL_MODEL if runs_on_this_computer(provider) else CHAT_LEAVES


def warm_up_embeddings_in_background(
    service: MemoryEmbeddingService, should_stop: Callable[[], bool]
) -> threading.Thread:
    """Como la ventana al abrirse: calcula las huellas que falten y, si no falta ninguna,
    carga el modelo de huellas, para que el primer turno no lo espere (#696).

    En un hilo demonio que nadie espera: escuchar no se retrasa por esto, y si falla, el
    diario se queda con el tipo de fallo y la búsqueda sigue como pueda.
    """

    def run() -> None:
        try:
            done = service.embed_pending(should_stop=should_stop)
            if done == 0 and not should_stop():
                service.warm_up()
        except Exception as error:  # las huellas nunca pueden romper la escucha
            _logger.error("Las huellas se interrumpieron (%s)", type(error).__name__)

    thread = threading.Thread(target=run, name="sirius-huellas", daemon=True)
    thread.start()
    return thread


def main() -> int:
    # Como la ventana: sin conexión a Hugging Face antes de cargar nada (ADR-246).
    hugging_face_offline()
    paths = known_data_paths()
    if paths is None:
        print(DATA_PATHS_UNKNOWN)
        return 2
    configure_logging(paths.logs_dir)
    initialize_persistence(paths)
    dependencies = build_conversation_dependencies(paths.data_dir / "sirius.db", paths.backups_dir)
    stop_embedding = threading.Event()
    try:
        if not dependencies.initial_project_use_case.is_configured():
            print("Abre Sirius una vez con su ventana antes de hablarle por aquí.")
            return 2
        notice = without_a_local_model(dependencies.send_message_use_case.llm_provider)
        if notice:
            print(notice)
            return 2
        # Que el modelo de la charla vaya cargando mientras carga la voz (ADR-252), y el de
        # huellas con las que falten, como la ventana al abrirse (#696).
        dependencies.send_message_use_case.warm_up_in_background()
        warm_up_embeddings_in_background(
            dependencies.memory_embedding_service, stop_embedding.is_set
        )
        return listen(
            dependencies.local_listening,
            print,
            keep_going=lambda: True,
            pause=lambda: time.sleep(PAUSE_SECONDS),
            history=dependencies.get_history_use_case.get_history,
        )
    except KeyboardInterrupt:
        print("Hasta luego.")
        return 0
    finally:
        # Las huellas paran antes del siguiente grupo: la base se cierra ahora.
        stop_embedding.set()
        dependencies.close_database_connections()


if __name__ == "__main__":
    raise SystemExit(main())
