"""Sonda de escala real de Qt, ejecutada SIEMPRE como subproceso.

``QT_SCALE_FACTOR`` se lee una sola vez, al crear ``QApplication``. pytest-qt
comparte una única aplicación para toda la sesión de pruebas, así que cambiar
la variable dentro de una prueba no cambia nada: la única manera honesta de
probar 1.0 / 1.25 / 1.5 es un proceso nuevo por factor, con la variable puesta
antes de crear la aplicación. Este módulo es ese proceso hijo.

Protocolo: el padre fija ``QT_SCALE_FACTOR`` y ``QT_QPA_PLATFORM`` en el
entorno y ejecuta ``python _scale_probe.py <factor-esperado>``. La sonda
verifica que el proceso corre DE VERDAD a ese factor (``devicePixelRatio``),
construye la ventana real de Sirius con un mensaje largo, la estrecha y la
ensancha, y comprueba que el cuerpo sigue el ancho de la columna y que el
alto sube al estrechar y baja al ensanchar. Sale con código 0 y una línea
``OK ...`` solo si todo se cumple; cualquier fallo sale con código distinto
de 0 y el motivo por stdout.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def main() -> int:
    expected_scale = float(sys.argv[1])

    isolated = Path(tempfile.mkdtemp(prefix="sirius_scale_probe_"))
    for variable in ("WIN_PD_OVERRIDE_LOCAL_APPDATA", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
        os.environ[variable] = str(isolated)

    from PySide6.QtWidgets import QApplication

    app = QApplication([])

    screen = app.primaryScreen()
    if screen is None:
        print("FALLO: sin pantalla")
        return 2
    ratio = screen.devicePixelRatio()
    if abs(ratio - expected_scale) > 0.01:
        print(f"FALLO: devicePixelRatio={ratio}, esperado {expected_scale}")
        return 3

    # Los ayudantes reales de las pruebas GUI: misma ventana, mismo arranque.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    # Import dinámico deliberado: este módulo corre como script suelto, fuera
    # del paquete de pruebas, y mypy no puede resolver esa ruta en estático.
    from test_conversation_ui import (  # type: ignore[import-not-found]
        _bootstrapped_database,
        _build_window,
    )

    from sirius.adapters.persistence.sqlite_conversation_repository import (
        build_sqlite_conversation_repository,
    )
    from sirius.domain.conversation import MessageRole

    database_path = _bootstrapped_database(isolated / "sirius.db")
    repository = build_sqlite_conversation_repository(database_path)
    conversation = repository.get_or_create_main_conversation()
    repository.append_message(conversation.id, MessageRole.SIRIUS, "palabra " * 300)

    window = _build_window(database_path)
    window.resize(1200, 700)
    window.show()
    app.processEvents()

    def body_and_row() -> tuple[int, int, int]:
        widget = window.message_list.itemWidget(window.message_list.item(0))
        body = widget._segment_bodies[0]
        viewport_width = window.message_list.viewport().width()
        return body.width(), viewport_width, window.message_list.item(0).sizeHint().height()

    body_wide, viewport_wide, height_wide = body_and_row()
    if body_wide <= viewport_wide - 60:
        print(f"FALLO: ancho del cuerpo {body_wide} no sigue al viewport {viewport_wide} (ancho)")
        return 4

    window.resize(700, 700)
    app.processEvents()
    body_narrow, viewport_narrow, height_narrow = body_and_row()
    if viewport_narrow >= viewport_wide:
        print("FALLO: el viewport no se estrechó")
        return 5
    if body_narrow <= viewport_narrow - 60:
        print(
            f"FALLO: ancho del cuerpo {body_narrow} no sigue al viewport "
            f"{viewport_narrow} (estrecho)"
        )
        return 6
    if height_narrow <= height_wide:
        print(f"FALLO: al estrechar el alto no subió ({height_wide} -> {height_narrow})")
        return 7

    window.resize(1200, 700)
    app.processEvents()
    _body, _viewport, height_wide_again = body_and_row()
    if height_wide_again >= height_narrow:
        print(f"FALLO: al ensanchar el alto no bajó ({height_narrow} -> {height_wide_again})")
        return 8

    window.close()
    app.processEvents()
    print(
        f"OK escala={ratio} ancho:{height_wide} estrecho:{height_narrow} "
        f"ancho-otra-vez:{height_wide_again}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
