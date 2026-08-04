"""Regresiones estructurales de seguridad del verificador Windows de B13."""

from __future__ import annotations

from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
_VERIFY_WRAPPER = _SCRIPTS / "verify_windows_package.ps1"
_VERIFY_PARTS = (
    _SCRIPTS / "verify_windows_package_01_locate_extract.ps1",
    _SCRIPTS / "verify_windows_package_02_static_checks.ps1",
    _SCRIPTS / "verify_windows_package_03_preconditions.ps1",
    _SCRIPTS / "verify_windows_package_04_runtime.ps1",
    _SCRIPTS / "verify_windows_package_05_execute.ps1",
)
_FIRST_LAUNCH = '$DatabasePath = Invoke-SmokeLaunch -Label "1er arranque"'
_FAILURE_GATE = "if ($script:Failures.Count -gt 0)"
_STATIC_GATE = (
    'throw ("El paquete extraido no supera las comprobaciones estaticas de '
    'estructura, "'
)
_LOOP_START = "    while ((Get-Date) -lt $deadline) {"
_LOOP_END = "    $stillAlive = -not $process.HasExited"


def _script() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in _VERIFY_PARTS)


def test_the_canonical_wrapper_loads_every_phase_in_order() -> None:
    wrapper = _VERIFY_WRAPPER.read_text(encoding="utf-8")

    assert _VERIFY_WRAPPER.is_file()
    for part in _VERIFY_PARTS:
        assert part.is_file()

    positions = [wrapper.index(part.name) for part in _VERIFY_PARTS]
    assert positions == sorted(positions)


def test_static_package_failures_abort_before_any_package_launch() -> None:
    script = _script()

    contamination_check = script.index(
        'Test-Check "Sin bases de datos, registros, copias, exportaciones ni secretos"'
    )
    static_gate = script.index(_STATIC_GATE)
    first_launch = script.index(_FIRST_LAUNCH)

    assert contamination_check < static_gate < first_launch
    guarded_region = script[contamination_check:static_gate]
    assert _FAILURE_GATE in guarded_region
    assert "No se ejecutara Sirius.exe" in script[static_gate:first_launch]


def test_all_remaining_preconditions_abort_before_first_launch() -> None:
    script = _script()

    prelaunch_gate = script.index(
        'throw ("Las precondiciones de ejecucion no se cumplen. "'
    )
    first_launch = script.index(_FIRST_LAUNCH)

    assert prelaunch_gate < first_launch
    assert _FAILURE_GATE in script[:prelaunch_gate]
    assert "No se ejecutara codigo del paquete" in script[prelaunch_gate:first_launch]


def test_window_observation_does_not_end_liveness_monitoring() -> None:
    script = _script()
    loop_start = script.index(_LOOP_START)
    loop_end = script.index(_LOOP_END, loop_start)
    loop = script[loop_start:loop_end]

    assert "$sawWindow = $true" in loop
    assert "$titles = $visibleTitles" in loop
    break_lines = [line.strip() for line in loop.splitlines() if "break" in line]
    assert break_lines == ["if ($process.HasExited) { break }"]


def test_liveness_is_sampled_only_after_the_monitoring_deadline_loop() -> None:
    script = _script()
    loop_start = script.index(_LOOP_START)
    loop_end = script.index(_LOOP_END, loop_start)
    liveness_check = script.index(
        'Test-Check "$Label - el proceso sigue vivo tras $StartupTimeoutSeconds s"',
        loop_end,
    )

    assert loop_start < loop_end < liveness_check
