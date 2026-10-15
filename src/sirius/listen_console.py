"""Probar el oído del robot en consola: ``uv run --extra voz sirius-oye`` (ADR-242).

La parte de E-R03-01 que no depende de la pieza C: Sirius le oye en local y escribe lo
que oyó y lo que contesta, en la misma charla de la ventana, hasta Ctrl+C. No habla
(pieza C) ni abre la ventana (pieza D). Si falta algo del oído, dice qué orden lo
instala y sale sin hacer nada más. Si deja de oír mientras escucha, porque la charla se
fue a un modelo de fuera, lo dice y sale.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.application.data_location import DataLocationUseCase
from sirius.application.local_listening import LocalListening
from sirius.application.send_message import SendMessageResult
from sirius.composition_root import build_conversation_dependencies
from sirius.domain.conversation import MessageStatus
from sirius.infrastructure.bootstrap_location_store import build_bootstrap_location_store
from sirius.infrastructure.data_path_validator import build_data_path_validator
from sirius.infrastructure.logging import configure_logging
from sirius.infrastructure.paths import SiriusPaths, resolve_paths
from sirius.ports.data_location import DataLocationError
from sirius.presentation.error_messages import failed_send_message
from sirius.presentation.message_text import CANCELLED_SEND, message_body

#: Cuánto se espera antes de volver a mirar el micro cuando no ha llegado nada.
PAUSE_SECONDS = 0.03


def listen(
    listening: LocalListening[Any],
    say: Callable[[str], None],
    *,
    keep_going: Callable[[], bool],
    pause: Callable[[], None],
) -> int:
    """Escucha mientras ``keep_going`` lo diga y cuenta cada turno; cierra el micro al salir.

    Cuenta todo lo que devuelve el oído (rondas 11, 12 y 13 de Codex sobre la PR #687).
    Cada respuesta, como la ventana: lo que escribió con la marca de cómo acabó, también
    lo que llegó a escribir si falló, y después el mismo aviso que ella. Si el modelo
    propuso algo que recordar, dónde confirmarlo. Y si el oído deja de oír por su cuenta,
    dice su aviso y sale, en vez de seguir esperando a un micro cerrado.
    """
    notice = listening.start()
    if notice:
        say(notice)
        return 1
    say("Te escucho. Habla cuando quieras; Ctrl+C para salir.")
    try:
        while keep_going():
            attended = listening.attend()
            for turn in attended.turns:
                say(f"Tú: {turn.heard}")
                _say_reply(turn.result, say)
                if turn.proposed is not None:
                    say(
                        f"Sirius propone recordar «{turn.proposed}»: lo confirmas o lo "
                        "rechazas en Memoria y decisiones, en la ventana."
                    )
            if attended.notice:
                say(attended.notice)
                return 1
            if not attended.turns:
                pause()
    finally:
        listening.stop()
    return 0


def _say_reply(result: SendMessageResult, say: Callable[[str], None]) -> None:
    """La respuesta como la enseña la ventana al acabar un turno escrito (``_on_finished``):
    lo que escribió con la marca de cómo acabó y, si no acabó bien, el mismo aviso."""
    sirius = result.sirius_message
    body = message_body(sirius.content, sirius.status).strip()
    say(f"Sirius: {body}" if body else "Sirius:")
    if result.outcome is MessageStatus.CANCELLED:
        say(CANCELLED_SEND)
    elif result.outcome is MessageStatus.FAILED:
        say(failed_send_message(result.error_kind, sirius.operation_id))


def _data_paths() -> SiriusPaths | None:
    """Dónde guarda Sirius sus datos, como lo resuelve la ventana; ``None`` si aún no lo sabe."""
    default = resolve_paths()
    location = DataLocationUseCase(
        location_store=build_bootstrap_location_store(),
        validator=build_data_path_validator(),
        default_data_dir=default.data_dir,
    )
    try:
        resolution = location.resolve()
    except DataLocationError:
        return None
    if resolution.needs_selection:
        return None
    return resolve_paths(resolution.path)


def main() -> int:
    paths = _data_paths()
    if paths is None:
        print("Abre Sirius una vez con su ventana: todavía no sabe dónde guardar tus datos.")
        return 2
    configure_logging(paths.logs_dir)
    initialize_persistence(paths)
    dependencies = build_conversation_dependencies(paths.data_dir / "sirius.db", paths.backups_dir)
    try:
        if not dependencies.initial_project_use_case.is_configured():
            print("Abre Sirius una vez con su ventana antes de hablarle por aquí.")
            return 2
        return listen(
            dependencies.local_listening,
            print,
            keep_going=lambda: True,
            pause=lambda: time.sleep(PAUSE_SECONDS),
        )
    except KeyboardInterrupt:
        print("Hasta luego.")
        return 0
    finally:
        dependencies.close_database_connections()


if __name__ == "__main__":
    raise SystemExit(main())
