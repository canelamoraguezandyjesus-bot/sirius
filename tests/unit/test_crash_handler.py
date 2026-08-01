"""El manejador global no puede fallar mientras informa de otro fallo.

Cubre las tres cosas que producían ``Error in sys.excepthook`` seguido de
``lost sys.stderr`` cuando Sirius se cerraba al acoplar la ventana: formatear
un ``RecursionError`` sin volver a agotar la pila, no reentrar si algo falla
durante el informe, y no depender de que ``sys.stderr`` exista.
"""

from __future__ import annotations

import logging
import sys
import threading

import pytest

from sirius.infrastructure import crash_handler
from sirius.infrastructure.crash_handler import format_crash, install_crash_handler


def _recursion_error() -> RecursionError:
    """Un RecursionError real, con una pila profunda de verdad."""

    def descend(depth: int) -> int:
        return descend(depth + 1)

    try:
        descend(0)
    except RecursionError as exc:
        return exc
    raise AssertionError("no se produjo el RecursionError esperado")


def test_format_crash_survives_a_real_recursion_error() -> None:
    """Este es el caso exacto que hacía fallar al manejador por omisión."""
    error = _recursion_error()

    text = format_crash(type(error), error, error.__traceback__)

    assert "RecursionError" in text
    assert text.strip() != ""


def test_format_crash_restores_the_recursion_limit() -> None:
    before = sys.getrecursionlimit()
    error = _recursion_error()

    format_crash(type(error), error, error.__traceback__)

    assert sys.getrecursionlimit() == before


def test_format_crash_truncates_a_runaway_traceback() -> None:
    """Cientos de marcos idénticos no aportan nada y cuestan pila."""
    error = _recursion_error()

    text = format_crash(type(error), error, error.__traceback__)

    assert len(text.splitlines()) < 200


def test_format_crash_never_raises_even_if_formatting_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _explode(*args: object, **kwargs: object) -> list[str]:
        raise ValueError("formateo roto")

    monkeypatch.setattr("sirius.infrastructure.crash_handler.traceback.format_exception", _explode)

    text = format_crash(ValueError, ValueError("algo"), None)

    assert "ValueError" in text


def test_the_hook_logs_the_crash(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    install_crash_handler()
    error = ValueError("fallo de prueba")

    with caplog.at_level(logging.CRITICAL, logger="sirius.infrastructure.crash_handler"):
        sys.excepthook(type(error), error, error.__traceback__)

    assert any("fallo de prueba" in record.getMessage() for record in caplog.records)


def test_the_hook_does_not_need_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    """En el ejecutable de Windows sin consola ``sys.stderr`` vale ``None``.

    Escribir a ciegas ahí es lo que acababa en ``lost sys.stderr``.
    """
    install_crash_handler()
    monkeypatch.setattr(sys, "stderr", None)
    error = ValueError("sin stderr")

    sys.excepthook(type(error), error, error.__traceback__)  # no debe lanzar


def test_the_hook_tolerates_a_broken_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BrokenStream:
        def write(self, text: str) -> int:
            raise OSError("stderr roto")

        def flush(self) -> None:
            raise OSError("stderr roto")

    install_crash_handler()
    monkeypatch.setattr(sys, "stderr", _BrokenStream())
    error = ValueError("stderr roto")

    sys.excepthook(type(error), error, error.__traceback__)  # no debe lanzar


def test_the_hook_never_reenters_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si informar falla, el manejador se retira en vez de recursar."""
    install_crash_handler()
    hook = sys.excepthook
    entries: list[int] = []

    real_format = crash_handler.format_crash

    def _reentrant_format(
        exc_type: type[BaseException], exc_value: BaseException, exc_traceback: object
    ) -> str:
        entries.append(1)
        if len(entries) < 5:
            # Un fallo mientras se informa: vuelve a entrar en el manejador.
            hook(ValueError, ValueError("fallo durante el informe"), None)
        return real_format(exc_type, exc_value, exc_traceback)  # type: ignore[arg-type]

    monkeypatch.setattr(crash_handler, "format_crash", _reentrant_format)

    hook(ValueError, ValueError("primero"), None)

    # La reentrada quedó cortada: solo se formateó el fallo original.
    assert len(entries) == 1


def test_the_thread_hook_reports_without_raising(caplog: pytest.LogCaptureFixture) -> None:
    install_crash_handler()
    failures: list[BaseException] = []

    def _boom() -> None:
        raise ValueError("fallo en hilo secundario")

    with caplog.at_level(logging.CRITICAL, logger="sirius.infrastructure.crash_handler"):
        thread = threading.Thread(target=_boom, name="hilo-de-prueba")
        thread.start()
        thread.join()

    assert failures == []
    assert any("fallo en hilo secundario" in record.getMessage() for record in caplog.records)


def test_the_thread_hook_ignores_system_exit() -> None:
    install_crash_handler()

    def _quit() -> None:
        raise SystemExit(0)

    thread = threading.Thread(target=_quit, name="hilo-que-sale")
    thread.start()
    thread.join()  # no debe registrar nada ni lanzar
