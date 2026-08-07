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
from pathlib import Path

import pytest

from sirius.infrastructure import crash_handler
from sirius.infrastructure.crash_handler import format_crash, install_crash_handler
from sirius.infrastructure.logging import configure_logging


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


def _distinguishable_deep_error() -> ValueError:
    """Una cadena de llamadas con extremos reconocibles: los marcos antiguos
    y el marco final tienen nombres únicos, con 80 niveles anónimos en medio,
    para poder afirmar QUÉ extremo de la traza sobrevive al recorte."""

    def marco_antiguo_origen() -> None:
        marco_antiguo_segundo()

    def marco_antiguo_segundo() -> None:
        descender(0)

    def descender(depth: int) -> None:
        if depth < 80:
            descender(depth + 1)
            return
        marco_reciente_del_fallo()

    def marco_reciente_del_fallo() -> None:
        raise ValueError("fallo al fondo de la cadena")

    try:
        marco_antiguo_origen()
    except ValueError as exc:
        return exc
    raise AssertionError("no se produjo el ValueError esperado")


def test_format_crash_keeps_the_most_recent_frames_and_drops_the_oldest() -> None:
    """El contrato dice «los últimos 40 marcos», y tiene que ser verdad.

    Con límite positivo, ``traceback.format_exception`` conserva los marcos
    MÁS ANTIGUOS: esta prueba fallaría, porque el marco del fallo desaparece
    y el arranque de la cadena sobrevive. El límite debe ir en negativo.
    """
    error = _distinguishable_deep_error()
    limit_before = sys.getrecursionlimit()

    text = format_crash(type(error), error, error.__traceback__)

    # Los marcos más recientes permanecen: el del fallo y el propio mensaje.
    assert "marco_reciente_del_fallo" in text
    assert "fallo al fondo de la cadena" in text
    # Los más antiguos se truncan: la cadena tiene ~84 marcos y se conservan 40.
    assert "marco_antiguo_origen" not in text
    assert "marco_antiguo_segundo" not in text
    # La traza sigue limitada.
    assert len(text.splitlines()) < 200
    # Y el límite de recursión queda restaurado.
    assert sys.getrecursionlimit() == limit_before


def test_reporting_a_distinguishable_crash_never_propagates(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Informar nunca lanza, y lo registrado enseña el extremo útil."""
    install_crash_handler()
    error = _distinguishable_deep_error()

    with caplog.at_level(logging.CRITICAL, logger="sirius.infrastructure.crash_handler"):
        sys.excepthook(type(error), error, error.__traceback__)  # no debe lanzar

    logged = " ".join(record.getMessage() for record in caplog.records)
    assert "marco_reciente_del_fallo" in logged
    assert "marco_antiguo_origen" not in logged


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


def test_after_configure_logging_a_crash_persists_to_the_rotating_file_without_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El contrato principal, de punta a punta y sin dobles.

    Después de ``configure_logging`` (es decir, una vez resuelto el directorio
    de datos), una excepción no capturada tiene que quedar en el fichero
    rotatorio real ``application.log`` aunque ``sys.stderr`` sea ``None``,
    como en el ejecutable de Windows sin consola. Antes de ese punto la
    persistencia NO está garantizada: esa ventana es mejor esfuerzo.
    """
    logs_dir = tmp_path / "logs"
    configure_logging(logs_dir)
    install_crash_handler()
    monkeypatch.setattr(sys, "stderr", None)
    error = _distinguishable_deep_error()

    sys.excepthook(type(error), error, error.__traceback__)  # no debe lanzar

    written = (logs_dir / "application.log").read_text(encoding="utf-8")
    assert "Excepción no capturada" in written
    assert "marco_reciente_del_fallo" in written
    assert "fallo al fondo de la cadena" in written
