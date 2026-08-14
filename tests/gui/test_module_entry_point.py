"""``python -m sirius`` tiene que abrir Sirius, sin atajo instalado.

No es comodidad. En la máquina real, una reinstalación que falló a mitad dejó
el atajo ``sirius`` sin existir, y con él desapareció la única manera de abrir
la aplicación: el código estaba descargado, completo y probado, y aun así era
inalcanzable. Esta prueba impide que esa puerta se vuelva a cerrar.
"""

from __future__ import annotations

import runpy

import pytest

import sirius.main

pytestmark = pytest.mark.gui


def test_running_the_package_starts_the_application(monkeypatch: pytest.MonkeyPatch) -> None:
    arranques: list[None] = []

    def _fake_main() -> int:
        arranques.append(None)
        return 0

    monkeypatch.setattr(sirius.main, "main", _fake_main)

    with pytest.raises(SystemExit) as salida:
        runpy.run_module("sirius", run_name="__main__")

    assert arranques == [None], "no se llamó al punto de entrada de siempre"
    assert salida.value.code == 0


def test_the_exit_code_of_the_application_is_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si la aplicación termina con error, el comando también.

    Un ``python -m sirius`` que siempre devuelve éxito engaña a cualquier cosa
    que lo llame desde un guion.
    """
    monkeypatch.setattr(sirius.main, "main", lambda: 3)

    with pytest.raises(SystemExit) as salida:
        runpy.run_module("sirius", run_name="__main__")

    assert salida.value.code == 3
