"""Regresiones estructurales de seguridad del verificador Windows de B13."""

from __future__ import annotations

from pathlib import Path

_VERIFY_SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "verify_windows_package.ps1"
)


def _script() -> str:
    return _VERIFY_SCRIPT.read_text(encoding="utf-8")


def test_static_package_failures_abort_before_any_package_launch() -> None:
    script = _script()

    contamination_check = script.index(
        'Test-Check "Sin bases de datos, registros, copias, exportaciones ni secretos"'
    )
    static_gate = script.index(
        'throw ("El paquete extraido no supera las comprobaciones estaticas de estructura, "'
    )
    first_launch = script.index('$DatabasePath = Invoke-SmokeLaunch -Label "1er arranque"')

    assert contamination_check < static_gate < first_launch
    assert 'if ($script:Failures.Count -gt 0)' in script[contamination_check:static_gate]
    assert "No se ejecutara Sirius.exe" in script[static_gate:first_launch]


def test_all_remaining_preconditions_abort_before_first_launch() -> None:
    script = _script()

    prelaunch_gate = script.index(
        'throw ("Las precondiciones de ejecucion no se cumplen. "'
    )
    first_launch = script.index('$DatabasePath = Invoke-SmokeLaunch -Label "1er arranque"')

    assert prelaunch_gate < first_launch
    assert 'if ($script:Failures.Count -gt 0)' in script[:prelaunch_gate]
    assert "No se ejecutara codigo del paquete" in script[prelaunch_gate:first_launch]


def test_window_observation_does_not_end_liveness_monitoring() -> None:
    script = _script()
    loop_start = script.index('    while ((Get-Date) -lt $deadline) {')
    loop_end = script.index('    $stillAlive = -not $process.HasExited', loop_start)
    loop = script[loop_start:loop_end]

    assert "$sawWindow = $true" in loop
    assert "$titles = $visibleTitles" in loop
    break_lines = [line.strip() for line in loop.splitlines() if "break" in line]
    assert break_lines == ['if ($process.HasExited) { break }']


def test_liveness_is_sampled_only_after_the_monitoring_deadline_loop() -> None:
    script = _script()
    loop_start = script.index('    while ((Get-Date) -lt $deadline) {')
    loop_end = script.index('    $stillAlive = -not $process.HasExited', loop_start)
    liveness_check = script.index(
        'Test-Check "$Label - el proceso sigue vivo tras $StartupTimeoutSeconds s"',
        loop_end,
    )

    assert loop_start < loop_end < liveness_check
