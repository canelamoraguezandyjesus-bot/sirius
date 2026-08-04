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


def _script() -> str:
    chunks = [path.read_text(encoding="utf-8") for path in _VERIFY_PARTS]
    return "\n".join(chunks)


def test_the_canonical_wrapper_loads_every_phase_in_order() -> None:
    wrapper = _VERIFY_WRAPPER.read_text(encoding="utf-8")
    positions: list[int] = []

    assert _VERIFY_WRAPPER.is_file()
    for part in _VERIFY_PARTS:
        assert part.is_file()
        positions.append(wrapper.index(part.name))

    assert positions == sorted(positions)


def test_static_package_failures_abort_before_any_package_launch() -> None:
    script = _script()
    contamination = script.index("Sin bases de datos, registros, copias")
    static_gate = script.index("El paquete extraido no supera")
    first_launch = script.index("Invoke-SmokeLaunch -Label")

    assert contamination < static_gate < first_launch
    assert "if ($script:Failures.Count -gt 0)" in script[contamination:static_gate]
    assert "No se ejecutara Sirius.exe" in script[static_gate:first_launch]


def test_all_remaining_preconditions_abort_before_first_launch() -> None:
    script = _script()
    prelaunch_gate = script.index("Las precondiciones de ejecucion no se cumplen")
    first_launch = script.index("Invoke-SmokeLaunch -Label")

    assert prelaunch_gate < first_launch
    assert "if ($script:Failures.Count -gt 0)" in script[:prelaunch_gate]
    assert "No se ejecutara codigo del paquete" in script[prelaunch_gate:first_launch]


def test_window_observation_does_not_end_liveness_monitoring() -> None:
    script = _script()
    loop_start = script.index("while ((Get-Date) -lt $deadline)")
    loop_end = script.index("$stillAlive = -not $process.HasExited", loop_start)
    loop = script[loop_start:loop_end]

    assert "$sawWindow = $true" in loop
    assert "$titles = $visibleTitles" in loop
    break_lines = [line.strip() for line in loop.splitlines() if "break" in line]
    assert break_lines == ["if ($process.HasExited) { break }"]


def test_liveness_is_sampled_only_after_the_monitoring_deadline_loop() -> None:
    script = _script()
    loop_start = script.index("while ((Get-Date) -lt $deadline)")
    loop_end = script.index("$stillAlive = -not $process.HasExited", loop_start)
    liveness_check = script.index("el proceso sigue vivo tras", loop_end)

    assert "$StartupTimeoutSeconds s" in script[liveness_check : liveness_check + 200]
    assert loop_start < loop_end < liveness_check
