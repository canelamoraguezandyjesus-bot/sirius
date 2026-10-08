"""Shared test configuration."""

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_platform_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Aísla platformdirs en Windows y Linux: en Windows redirige mediante
    # WIN_PD_OVERRIDE_LOCAL_APPDATA y en Linux mediante XDG_CONFIG_HOME/
    # XDG_DATA_HOME, para que resolve_paths() apunte a tmp_path en cada prueba.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("WIN_PD_OVERRIDE_LOCAL_APPDATA", str(tmp_path))


# Variables que Actions exporta en el runner y que los scripts de automatización
# leen para construir los marcadores de sus comentarios (`SIRIUS_RUN_TAG` y
# `SIRIUS_ROUND_TAG` derivan de ellas). Las pruebas de `tests/automation`
# ejecutan esos scripts con un entorno construido a partir de `os.environ`, así
# que heredarlas hace que las aserciones sobre marcadores dependan de DÓNDE se
# ejecuten las pruebas, no de lo que hace el código.
#
# No es un riesgo teórico: al relanzar un job de Quality el runner exporta
# `GITHUB_RUN_ATTEMPT=2`, los marcadores pasan a terminar en `-2` y dos pruebas
# que esperaban `-1` fallaban. El MISMO commit daba verde en el primer intento y
# rojo en la reejecución, que es la peor forma de fallo posible: aparenta un
# cambio de código cuando lo único que cambió fue el entorno.
ACTIONS_VARIABLES_THAT_GOVERN_MARKERS = ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")


@pytest.fixture(autouse=True)
def _hermetic_actions_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entorno hermético respecto de Actions.

    Las pruebas que necesitan un run o un intento concretos los fijan de forma
    explícita; el resto ve el mismo entorno dentro y fuera de CI.
    """
    for name in ACTIONS_VARIABLES_THAT_GOVERN_MARKERS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _sin_espias_de_ollama_al_acabar() -> Iterator[None]:
    """El conductor de la 0.2 del robot puede espiar todo lo que va a Ollama
    (``con_ollama_espia``, ADR-238): al acabar cada prueba se quita, para que no
    llegue a la siguiente."""
    yield
    conductor = sys.modules.get("conductor_robot_0_2")
    if conductor is not None:
        conductor.deshaz_los_espias()
