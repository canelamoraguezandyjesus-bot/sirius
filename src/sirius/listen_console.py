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
from sirius.composition_root import build_conversation_dependencies
from sirius.infrastructure.bootstrap_location_store import build_bootstrap_location_store
from sirius.infrastructure.data_path_validator import build_data_path_validator
from sirius.infrastructure.logging import configure_logging
from sirius.infrastructure.paths import SiriusPaths, resolve_paths
from sirius.ports.data_location import DataLocationError

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

    Si el oído deja de oír por su cuenta, dice su aviso y sale, en vez de seguir esperando
    a un micro cerrado (ronda 11 de Codex sobre la PR #687).
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
                if turn.answered:
                    say(f"Sirius: {turn.reply}")
                else:
                    say("Sirius no ha podido contestar: mira que su modelo esté abierto.")
            if attended.notice:
                say(attended.notice)
                return 1
            if not attended.turns:
                pause()
    finally:
        listening.stop()
    return 0


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
