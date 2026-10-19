"""La telemetría de ONNX Runtime se apaga antes de cargar ningún modelo (ADR-259, ADR-262).

ONNX Runtime la trae encendida, y en Windows la manda al sistema. Silero, Smart Turn y
Piper cargan con él: el oído y la voz llaman a ``onnx_runtime_quiet`` antes de importar
nada (lo miran sus pruebas, en ``test_local_listening_adapters.py`` y
``test_local_speaking_adapters.py``). Aquí, lo que hace: la variable que lee al arrancar,
antes de importarlo, y la llamada que la apaga aunque ya estuviera importado. ONNX Runtime
no está en Quality: se pone uno de mentira.
"""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import os
import sys
import types
from collections.abc import Sequence

import pytest

from sirius.adapters.audio.voice_libraries import (
    ONNX_RUNTIME,
    ONNX_RUNTIME_TELEMETRY,
    onnx_runtime_quiet,
)


class _OnnxRuntimeDeMentira(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Hace de ``onnxruntime`` al importarlo: apunta cómo estaba la variable en ese momento
    y cuántas veces se le apaga la telemetría. Con ``falla``, no carga, como una DLL rota."""

    def __init__(self, falla: Exception | None = None) -> None:
        self.falla = falla
        self.variable_al_importar: list[str | None] = []
        self.apagada = 0

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: types.ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        del path, target
        if fullname != ONNX_RUNTIME:
            return None
        return importlib.machinery.ModuleSpec(fullname, self)

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> types.ModuleType | None:
        del spec
        return None

    def exec_module(self, module: types.ModuleType) -> None:
        self.variable_al_importar.append(os.environ.get(ONNX_RUNTIME_TELEMETRY))
        if self.falla is not None:
            raise self.falla

        def apaga() -> None:
            self.apagada += 1

        module.disable_telemetry_events = apaga  # type: ignore[attr-defined]


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Sin ``onnxruntime`` importado ni la variable puesta, y todo como estaba al acabar."""
    monkeypatch.delitem(sys.modules, ONNX_RUNTIME, raising=False)
    monkeypatch.setenv(ONNX_RUNTIME_TELEMETRY, "x")
    monkeypatch.delenv(ONNX_RUNTIME_TELEMETRY)
    return monkeypatch


def _instala(monkeypatch: pytest.MonkeyPatch, falso: _OnnxRuntimeDeMentira) -> None:
    monkeypatch.setattr(sys, "meta_path", [falso, *sys.meta_path])


def test_pone_la_variable_antes_de_importarlo_y_apaga_la_telemetria(
    entorno: pytest.MonkeyPatch,
) -> None:
    falso = _OnnxRuntimeDeMentira()
    _instala(entorno, falso)

    onnx_runtime_quiet()

    assert falso.variable_al_importar == ["1"]
    assert falso.apagada == 1
    assert os.environ[ONNX_RUNTIME_TELEMETRY] == "1"


def test_si_ya_estaba_importado_la_apaga_igual(entorno: pytest.MonkeyPatch) -> None:
    falso = _OnnxRuntimeDeMentira()
    _instala(entorno, falso)
    onnx_runtime_quiet()

    onnx_runtime_quiet()

    assert falso.variable_al_importar == ["1"], "no se vuelve a importar"
    assert falso.apagada == 2


@pytest.mark.parametrize(
    "falla",
    [ImportError("No module named 'onnxruntime'"), OSError("DLL load failed")],
)
def test_si_onnx_runtime_no_carga_no_hay_nada_que_apagar_y_no_falla(
    entorno: pytest.MonkeyPatch, falla: Exception
) -> None:
    # Lo que lo necesita falla después, al cargar, con su causa.
    falso = _OnnxRuntimeDeMentira(falla)
    _instala(entorno, falso)

    onnx_runtime_quiet()

    assert falso.variable_al_importar == ["1"]
    assert os.environ[ONNX_RUNTIME_TELEMETRY] == "1"
