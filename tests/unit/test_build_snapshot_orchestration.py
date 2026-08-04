from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_WRAPPER = _ROOT / "scripts" / "build_windows.ps1"
_IMPLEMENTATION = _ROOT / "scripts" / "build_windows_impl.ps1"


def test_canonical_command_builds_from_a_distinct_detached_worktree() -> None:
    script = _WRAPPER.read_text(encoding="utf-8")
    capture = script.index('@("capture", $ControllerRoot)')
    add = script.index("worktree add --detach $SnapshotRoot $SourceCommit")
    invoke = script.index("& $SnapshotImplementation")

    assert capture < add < invoke
    assert '$SnapshotRoot = Join-Path $SnapshotContainer "snapshot"' in script
    assert "$SnapshotRoot $SourceCommit" in script
    assert "-SnapshotRoot $SnapshotRoot" in script
    assert "-PublishRoot $ControllerRoot" in script


def test_sensitive_build_inputs_are_resolved_only_from_snapshot() -> None:
    script = _IMPLEMENTATION.read_text(encoding="utf-8")
    assert "$RepoRoot = (Resolve-Path -LiteralPath $SnapshotRoot).Path" in script
    assert "$ControllerRoot" not in script
    for sensitive in (
        "pyproject.toml",
        "uv.lock",
        "pysidedeploy.spec",
        "src\\sirius\\__main__.py",
        "alembic.ini",
        "git ls-files migrations",
    ):
        assert sensitive in script
    assert "Push-Location $RepoRoot" in script
    assert 'cd /d "$RepoRoot"' in script


def test_provenance_is_rechecked_before_any_publication() -> None:
    script = _IMPLEMENTATION.read_text(encoding="utf-8")
    verify = script.index('$SnapshotHelper "verify" $RepoRoot $SourceCommit')
    publish = script.index("Publish-ValidatedArtifact `", verify)

    assert verify < publish
    assert "Snapshot aun detached, limpio" in script[verify:publish]
    assert "Publish-ValidatedArtifact `" not in script[:verify]


def test_publication_tracks_backups_and_new_results_separately() -> None:
    script = _IMPLEMENTATION.read_text(encoding="utf-8")
    transaction = script[
        script.index("function Publish-ValidatedArtifact") : script.index(
            'Write-Step "1/13 Entorno del sistema"'
        )
    ]

    backup_move = transaction.index("$backedUp.Add($itemName)")
    publish_move = transaction.index("$published.Add($itemName)")
    rollback = transaction.index("catch {", publish_move)
    remove_new = transaction.index("foreach ($itemName in $published)", rollback)
    restore_old = transaction.index("foreach ($itemName in $backedUp)", remove_new)

    assert backup_move < publish_move < rollback < remove_new < restore_old
    assert "$rollbackFailures.Add" in transaction[rollback:]
    assert "-ErrorAction Stop" in transaction[:rollback]


def test_incomplete_publication_rollback_preserves_backups_and_reports_both_errors() -> None:
    script = _IMPLEMENTATION.read_text(encoding="utf-8")
    transaction = script[
        script.index("function Publish-ValidatedArtifact") : script.index(
            'Write-Step "1/13 Entorno del sistema"'
        )
    ]

    incomplete = transaction.index("if ($rollbackFailures.Count -gt 0)")
    preserve = transaction.index("$preserveTransaction = $true", incomplete)
    aggregate = transaction.index("Errores de rollback", preserve)
    finally_block = transaction.index("finally {", aggregate)
    guarded_cleanup = transaction.index(
        "if (-not $preserveTransaction -and (Test-Path -LiteralPath $transaction))",
        finally_block,
    )

    assert incomplete < preserve < aggregate < finally_block < guarded_cleanup
    assert "Error original: $originalDetail" in transaction[incomplete:finally_block]
    assert "B13 PUBLISH ROLLBACK ERROR" in transaction[incomplete:finally_block]
    assert "transaccion con los backups se conserva" in transaction[incomplete:finally_block]


def test_successful_rollback_rethrows_original_and_cleanup_cannot_mask_it() -> None:
    script = _IMPLEMENTATION.read_text(encoding="utf-8")
    transaction = script[
        script.index("function Publish-ValidatedArtifact") : script.index(
            'Write-Step "1/13 Entorno del sistema"'
        )
    ]

    incomplete = transaction.index("if ($rollbackFailures.Count -gt 0)")
    rethrow = transaction.index("throw\n    }", incomplete)
    finally_block = transaction.index("finally {", rethrow)
    cleanup_error = transaction.index("B13 PUBLISH CLEANUP ERROR", finally_block)

    assert incomplete < rethrow < finally_block < cleanup_error
    assert "if ($null -ne $operationFailure)" in transaction[finally_block:cleanup_error]
    assert "else {\n                    throw" in transaction[cleanup_error:]


def test_exclusive_publication_file_lock_covers_build_transaction_and_cleanup() -> None:
    wrapper = _WRAPPER.read_text(encoding="utf-8")
    destination = wrapper.index('$PublishDestinationRoot = Join-Path $ControllerRoot "dist\\windows"')
    lock_path = wrapper.index(
        '$PublicationLockPath = Join-Path $PublishDestinationRoot ".b13-publish.lock"',
        destination,
    )
    acquire = wrapper.index("$PublicationLockStream = [System.IO.File]::Open(", lock_path)
    no_share = wrapper.index("[System.IO.FileShare]::None", acquire)
    concurrent_rejection = wrapper.index("La publicacion concurrente se rechaza", no_share)
    add_worktree = wrapper.index("worktree add --detach $SnapshotRoot $SourceCommit", acquire)
    invoke = wrapper.index("& $SnapshotImplementation", add_worktree)
    orchestration_finally = wrapper.index("finally {", wrapper.index("$BuildFailure = $null"))
    remove_snapshot = wrapper.index("worktree remove --force $SnapshotRoot", orchestration_finally)
    dispose = wrapper.index("$PublicationLockStream.Dispose()", remove_snapshot)

    assert destination < lock_path < acquire < no_share < concurrent_rejection
    assert concurrent_rejection < add_worktree < invoke < orchestration_finally
    assert orchestration_finally < remove_snapshot < dispose
    assert "[System.IO.FileMode]::OpenOrCreate" in wrapper[acquire:no_share]
    assert "catch [System.IO.IOException]" in wrapper[acquire:add_worktree]


def test_wrapper_always_attempts_registry_physical_and_file_lock_cleanup() -> None:
    wrapper = _WRAPPER.read_text(encoding="utf-8")
    orchestration_start = wrapper.index("$BuildFailure = $null")
    finally_start = wrapper.index("finally {", orchestration_start)
    finally_block = wrapper[finally_start:]
    unregister = finally_block.index("worktree remove --force $SnapshotRoot")
    physical_remove = finally_block.index(
        "Remove-Item -LiteralPath $SnapshotContainer -Recurse -Force -ErrorAction Stop"
    )
    dispose = finally_block.index("$PublicationLockStream.Dispose()")

    assert unregister < physical_remove < dispose
    assert "catch {" in finally_block[unregister:physical_remove]
    assert "Write-Error" not in finally_block
    assert "$CleanupFailures.Add" in finally_block[unregister:physical_remove]
    assert "$CleanupFailures.Add" in finally_block[physical_remove:dispose]
    assert "No se pudo liberar el bloqueo exclusivo de publicacion" in finally_block[dispose:]


def test_cleanup_preserves_build_failure_and_fails_a_successful_build() -> None:
    wrapper = _WRAPPER.read_text(encoding="utf-8")
    orchestration = wrapper[wrapper.index("$BuildFailure = $null") :]

    assert "$BuildFailure = $_" in orchestration
    assert "catch {" in orchestration
    assert "throw\n}" in orchestration
    assert "if ($null -eq $BuildFailure)" in orchestration
    assert "B13 CLEANUP ERROR" in orchestration


def test_failed_build_diagnostics_are_copied_before_snapshot_cleanup() -> None:
    wrapper = _WRAPPER.read_text(encoding="utf-8")
    invoke = wrapper.index("& $SnapshotImplementation")
    catch = wrapper.index("catch {", invoke)
    preserve = wrapper.index("Preserve-FailedBuildDiagnostics `", catch)
    rethrow = wrapper.index("throw\n}", preserve)
    finally_block = wrapper.index("finally {", rethrow)
    cleanup = wrapper.index("worktree remove --force $SnapshotRoot", finally_block)

    assert catch < preserve < rethrow < finally_block < cleanup
    assert "build\\packaging-diagnostics\\$CommitShort" in wrapper
    assert '$_.Name -like "build-*.log"' in wrapper
    assert '$_.Name -like "nuitka-crash-report-*.xml"' in wrapper
    assert '$_.Name -eq "pyside6-deploy-dry-run.txt"' in wrapper
    assert '$_.Name -eq "msvc-env.txt"' not in wrapper
    assert "B13 DIAGNOSTICS: conservados" in wrapper[catch:finally_block]


def test_controller_uses_uv_managed_python_without_a_global_interpreter() -> None:
    script = _WRAPPER.read_text(encoding="utf-8")
    uv_lookup = script.index("Get-Command uv.exe")
    controller = script.index("function Invoke-JsonController", uv_lookup)
    capture = script.index('@("capture", $ControllerRoot)', controller)
    add = script.index("worktree add --detach", capture)

    assert uv_lookup < controller < capture < add
    assert '"--no-project"' in script[uv_lookup:controller]
    assert '"--managed-python"' in script[uv_lookup:controller]
    assert '"--python", "3.14"' in script[uv_lookup:controller]
    assert "Get-Command python.exe" not in script
    assert "Get-Command py.exe" not in script
    assert "& $PythonCommand @PythonPrefix $Script @Arguments" in script


def test_complete_process_environment_is_restored_before_cleanup() -> None:
    script = _WRAPPER.read_text(encoding="utf-8")
    capture = script.index("$EnvironmentBeforeBuild = Get-ProcessEnvironmentSnapshot")
    invoke = script.index("& $SnapshotImplementation", capture)
    finally_block = script.index("finally {", invoke)
    restore = script.index("Restore-ProcessEnvironment `", finally_block)
    cleanup = script.index("worktree remove --force $SnapshotRoot", restore)

    assert capture < invoke < finally_block < restore < cleanup
    assert "foreach ($item in @(Get-ChildItem Env:))" in script
    assert "$Snapshot.ContainsKey($item.Name)" in script
    assert "$item.Name, $null" in script
    assert "foreach ($name in @($Snapshot.Keys))" in script
    assert "[string]$Snapshot[$name]" in script
    assert "-Failures $CleanupFailures" in script[restore:cleanup]
    assert "if ($null -eq $BuildFailure)" in script[finally_block:]


def test_localappdata_guard_still_precedes_file_lock_worktree_and_build() -> None:
    script = _WRAPPER.read_text(encoding="utf-8")
    guard = script.index("$packagingGuard = Invoke-JsonController $GuardScript")
    acquire = script.index("$PublicationLockStream = [System.IO.File]::Open(")
    add = script.index("worktree add --detach")
    invoke = script.index("& $SnapshotImplementation")

    assert guard < acquire < add < invoke
    assert 'Join-Path $env:LOCALAPPDATA "Sirius\\packaging-venv"' in script
    assert "packaging_path_guard.py" in script


def test_user_facing_build_command_remains_the_canonical_wrapper() -> None:
    implementation = _IMPLEMENTATION.read_text(encoding="utf-8")
    assert '$BuildCommand = ".\\scripts\\build_windows.ps1"' in implementation
