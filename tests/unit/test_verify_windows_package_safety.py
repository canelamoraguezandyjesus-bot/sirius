"""Regresiones estructurales de seguridad del verificador Windows de B13."""

from __future__ import annotations

from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
_VERIFY_WRAPPER = _SCRIPTS / "verify_windows_package.ps1"
_VERIFY_PARTS = (
    _SCRIPTS / "verify_windows_package_01_locate_extract.ps1",
    _SCRIPTS / "verify_windows_package_02_static_checks.ps1",
    _SCRIPTS / "verify_windows_package_03_preconditions.ps1",
    _SCRIPTS / "verify_windows_package_035_credential_gate.ps1",
    _SCRIPTS / "verify_windows_package_04_runtime.ps1",
    _SCRIPTS / "verify_windows_package_05_execute.ps1",
)


def _script() -> str:
    # Reproduce el mismo orden de fases que carga el wrapper canonico.
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


def test_verifier_bounds_and_freezes_zip_before_use() -> None:
    script = _script()
    freeze = script.index('$inspectorScript "freeze" $ZipPath $FrozenZipPath')
    frozen_hash = script.index("Get-FileHash -LiteralPath $FrozenZipPath")
    inspection = script.index("$inspectorScript $FrozenZipPath $ExtractRoot")
    extraction = script.index('$inspectorScript "extract" $FrozenZipPath $ExtractRoot')
    first_launch = script.index("Invoke-SmokeLaunch -Label")

    assert freeze < frozen_hash < inspection < extraction < first_launch
    assert "Copy-Item -LiteralPath $ZipPath -Destination $FrozenZipPath" not in script
    assert "$inspectorScript $ZipPath $ExtractRoot" not in script
    assert '$inspectorScript "extract" $ZipPath $ExtractRoot' not in script
    assert '[guid]::NewGuid().ToString("N")' in script
    assert "1 GiB" in script[:frozen_hash]


def test_build_manifest_is_size_capped_before_json_parsing() -> None:
    static = _VERIFY_PARTS[1].read_text(encoding="utf-8")
    limit = static.index("$MaxBuildManifestBytes = 1MB")
    size = static.index("Get-Item -LiteralPath $buildManifestPath", limit)
    gate = static.index("BUILD-MANIFEST.json supera el limite permitido", size)
    parse = static.index("$buildManifest = Get-Content -LiteralPath $buildManifestPath -Raw", gate)

    assert limit < size < gate < parse
    assert "if ($script:Failures.Count -gt 0)" in static[size:gate]
    assert "Verificacion detenida antes de leerlo" in static[size:parse]


def test_manifest_paths_are_validated_before_manifest_file_access() -> None:
    static = _VERIFY_PARTS[1].read_text(encoding="utf-8")
    helper = static.index('$manifestValidator = Join-Path $PSScriptRoot "file_manifest.py"')
    invoke = static.index("$VenvPython $manifestValidator $fileManifestPath $PackageRoot", helper)
    accepted = static.index("foreach ($validatedEntry in @($manifestValidation.entries))", invoke)
    manifest_join = static.index(
        '$target = Join-Path $PackageRoot ($entry.Key.Replace("/", "\\"))', accepted
    )
    manifest_hash = static.index("Get-FileHash -LiteralPath $target", manifest_join)

    assert (_SCRIPTS / "file_manifest.py").is_file()
    assert helper < invoke < accepted < manifest_join < manifest_hash
    assert "ruta o un hash no seguro" in static[invoke:accepted]
    assert "No se leera ningun destino declarado" in static[invoke:accepted]


def test_smoke_profile_home_variables_are_derived_from_isolated_home() -> None:
    preconditions = _VERIFY_PARTS[2].read_text(encoding="utf-8")
    derive_root = preconditions.index(
        "$IsolatedHomeRoot = [System.IO.Path]::GetPathRoot($IsolatedHome)"
    )
    derive_drive = preconditions.index(
        "$IsolatedHomeDrive = $IsolatedHomeRoot.TrimEnd", derive_root
    )
    derive_path = preconditions.index(
        "$IsolatedHomePath = $IsolatedHome.Substring($IsolatedHomeDrive.Length)",
        derive_drive,
    )
    coherence = preconditions.index(
        "HOMEDRIVE y HOMEPATH reconstruyen el USERPROFILE aislado", derive_path
    )
    environment = preconditions.index("$IsolatedEnv = @{", coherence)
    banned = preconditions.index("foreach ($banned", environment)
    isolated_region = preconditions[environment:banned]

    assert derive_root < derive_drive < derive_path < coherence < environment
    assert '"USERPROFILE"            = $IsolatedHome' in isolated_region
    assert '"HOMEDRIVE"              = $IsolatedHomeDrive' in isolated_region
    assert '"HOMEPATH"               = $IsolatedHomePath' in isolated_region
    assert "$env:HOMEDRIVE" not in isolated_region
    assert "$env:HOMEPATH" not in isolated_region


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


def test_a_present_credential_does_not_abort_the_verification() -> None:
    """Tener la credencial guardada no puede impedir verificar B13.

    La puerta anterior abortaba si Credential Manager tenia la credencial de
    Sirius. Eso hacia imposible verificar el paquete en la unica maquina donde
    se construye -la del desarrollador, que usa Sirius y por tanto la tiene-, y
    ademas exigia el escenario que el propio B13 declara fuera de su alcance:
    "Windows sin clave" es B14. La verificacion moria despues de haber pasado ya
    la procedencia, el inventario y el aislamiento, sin nada malo en el paquete.
    """
    # Se mira la fase suelta, no la concatenacion: entre esta puerta y el primer
    # arranque esta 04_runtime, cuyos throw son del helper de lanzamiento y no
    # tienen nada que ver con la credencial.
    gate_script = _VERIFY_PARTS[3].read_text(encoding="utf-8")

    assert 'Write-Step "D. Cobertura del escenario sin clave"' in gate_script
    assert "throw" not in gate_script, "la credencial presente vuelve a abortar la verificacion"
    assert "Add-Skip" in gate_script, "la falta de cobertura tiene que quedar registrada"


def test_a_present_credential_is_reported_as_an_uncovered_scenario() -> None:
    """No cubrirlo es aceptable; ocultarlo no.

    El veredicto ya distingue SUPERADA de SUPERADA CON RESERVAS y enumera lo que
    no se ha demostrado. Registrar la omision es lo que impide que una
    verificacion con la credencial presente se lea como si hubiera probado el
    arranque sin clave.
    """
    gate_script = _VERIFY_PARTS[3].read_text(encoding="utf-8")

    assert 'Add-Skip "El arranque sin clave"' in gate_script
    assert "B14" in gate_script, "la omision no dice a que bloque pertenece el escenario"


def test_the_launches_must_not_change_the_credential_state() -> None:
    """Lo que hay que demostrar es que el paquete no altero la boveda.

    Exigir ABSENT despues de los arranques solo era correcto mientras una puerta
    anterior garantizase ABSENT antes. Sin esa puerta, exigirlo convertiria la
    credencial legitima del usuario en un fallo del paquete.
    """
    script = _script()
    postcheck = script.index("La credencial de Sirius no cambio de estado con los arranques")
    postcheck_region = script[postcheck : postcheck + 400]

    assert "$CredentialStateAfter -eq $CredentialState" in postcheck_region
    assert '$CredentialStateAfter -eq "ABSENT"' not in script


def test_window_observation_does_not_end_liveness_monitoring() -> None:
    script = _script()
    loop_start = script.index("while ((Get-Date) -lt $deadline)")
    loop_end = script.index("$stillAlive = -not $process.HasExited", loop_start)
    loop = script[loop_start:loop_end]

    assert "$sawWindow = $true" in loop
    assert "$titles = $visibleTitles" in loop
    break_lines = [line.strip() for line in loop.splitlines() if "break" in line]
    assert break_lines == ["if ($process.HasExited) { break }"]


def test_liveness_is_sampled_after_the_monitoring_deadline_loop() -> None:
    script = _script()
    loop_start = script.index("while ((Get-Date) -lt $deadline)")
    loop_end = script.index("$stillAlive = -not $process.HasExited", loop_start)
    liveness_check = script.index("el proceso sigue vivo tras", loop_end)

    assert "$StartupTimeoutSeconds s" in script[liveness_check : liveness_check + 200]
    assert loop_start < loop_end < liveness_check


def test_isolated_process_is_stopped_from_finally_on_every_path() -> None:
    runtime = _VERIFY_PARTS[-2].read_text(encoding="utf-8")
    function_start = runtime.index("function Invoke-SmokeLaunch")
    start = runtime.index("Start-IsolatedSirius `", function_start)
    finally_block = runtime.index("finally {", start)
    stop = runtime.index("Stop-IsolatedSirius -Process $process", finally_block)
    dispose = runtime.index("$process.Dispose()", stop)
    database_checks = runtime.index('Test-Check "$Label - se creo sirius.db"', dispose)

    assert function_start < start < finally_block < stop < dispose < database_checks
    assert "B13 PROCESS CLEANUP ERROR" in runtime[finally_block:database_checks]


def test_user_state_postconditions_run_after_launch_failures() -> None:
    execute = _VERIFY_PARTS[-1].read_text(encoding="utf-8")
    first_launch = execute.index('Invoke-SmokeLaunch -Label "1er arranque"')
    sqlite_check = execute.index("SELECT version_num FROM alembic_version", first_launch)
    catch = execute.index("catch {", sqlite_check)
    finally_block = execute.index("finally {", catch)
    pointer_check = execute.index(
        "La existencia del data_location.json real no cambio", finally_block
    )
    credential_check = execute.index(
        "La credencial de Sirius no cambio de estado con los arranques", finally_block
    )
    result = execute.index('Write-Step "Resultado"', credential_check)

    assert first_launch < sqlite_check < catch < finally_block
    assert finally_block < pointer_check < credential_check < result
    assert "$ExecutionFailure = $_" in execute[catch:finally_block]


def test_launch_exception_is_reported_after_user_state_checks() -> None:
    execute = _VERIFY_PARTS[-1].read_text(encoding="utf-8")
    finally_block = execute.index("finally {")
    finally_end = execute.index("if ($null -ne $ExecutionFailure)", finally_block)
    execution_failure = execute.index(
        "Los dos arranques y las validaciones SQLite terminaron sin excepciones",
        finally_end,
    )
    result = execute.index('Write-Step "Resultado"', execution_failure)

    assert "throw" not in execute[finally_block:finally_end]
    assert finally_block < finally_end < execution_failure < result
    assert 'Test-Check "Se pudo comprobar el data_location.json real' in execute
    assert 'Test-Check "Se pudo comprobar la credencial de Sirius' in execute
