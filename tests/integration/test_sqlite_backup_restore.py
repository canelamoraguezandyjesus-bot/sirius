"""Integration tests for restoring encrypted Sirius backup files.

SIRIUS-ARQ-0.1 S12.3: restoration must decrypt in a temporary location,
validate password/format/hashes/version/schema, check SQLite integrity,
create a validated safety copy of the current database, replace atomically
only after explicit confirmation, and automatically roll back to the safety
copy if the post-restore validation fails.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import sqlite3
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from sirius.adapters.backup.sqlite_backup_service import (
    _decrypt_envelope as decrypt_envelope,
)
from sirius.adapters.backup.sqlite_backup_service import _derive_key as derive_key
from sirius.adapters.backup.sqlite_backup_service import (
    _KdfParams,
    build_sqlite_backup_service,
)
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.ports.backup import (
    BackupConfirmationRequiredError,
    BackupManifest,
    BackupRestoreError,
    BackupTooLargeError,
    BackupValidationError,
)

_PASSWORD = "correct horse battery staple"


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "sirius.db"
    upgrade_to_head(path)
    return path


@pytest.fixture
def backups_dir(tmp_path: Path) -> Path:
    return tmp_path / "backups"


def _write_marker(database_path: Path, marker: int) -> None:
    """Stamp ``PRAGMA user_version`` so tests can tell data generations apart."""
    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute(f"PRAGMA user_version = {marker}")
        connection.commit()
    finally:
        connection.close()


def _read_marker(database_path: Path) -> int:
    connection = sqlite3.connect(str(database_path))
    try:
        row = connection.execute("PRAGMA user_version").fetchone()
        return int(row[0])
    finally:
        connection.close()


def _rewrite_manifest(backup_path: Path, password: str, schema_version: str | None = None) -> None:
    envelope = json.loads(backup_path.read_text(encoding="utf-8"))
    kdf = envelope["kdf"]
    params = _KdfParams(
        salt=base64.b64decode(kdf["salt"]),
        time_cost=kdf["time_cost"],
        memory_cost_kib=kdf["memory_cost_kib"],
        parallelism=kdf["parallelism"],
    )
    fernet = Fernet(derive_key(password, params))
    package = fernet.decrypt(envelope["ciphertext"].encode("ascii"))
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        db_bytes = archive.read("sirius.db")
    if schema_version is not None:
        manifest["schema_version"] = schema_version
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest).encode("utf-8"))
        archive.writestr("sirius.db", db_bytes)
    envelope["ciphertext"] = fernet.encrypt(buffer.getvalue()).decode("ascii")
    backup_path.write_text(json.dumps(envelope), encoding="utf-8")


def _rewrite_backup_package(
    backup_path: Path,
    password: str,
    transform: Callable[[dict[str, object], bytes], tuple[dict[str, object], bytes]],
) -> None:
    """Decrypt, apply ``transform`` to (manifest, db bytes), then re-encrypt."""
    envelope = json.loads(backup_path.read_text(encoding="utf-8"))
    kdf = envelope["kdf"]
    params = _KdfParams(
        salt=base64.b64decode(kdf["salt"]),
        time_cost=kdf["time_cost"],
        memory_cost_kib=kdf["memory_cost_kib"],
        parallelism=kdf["parallelism"],
    )
    fernet = Fernet(derive_key(password, params))
    package = fernet.decrypt(envelope["ciphertext"].encode("ascii"))
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        db_bytes = archive.read("sirius.db")
    new_manifest, new_db_bytes = transform(manifest, db_bytes)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(new_manifest).encode("utf-8"))
        archive.writestr("sirius.db", new_db_bytes)
    envelope["ciphertext"] = fernet.encrypt(buffer.getvalue()).decode("ascii")
    backup_path.write_text(json.dumps(envelope), encoding="utf-8")


@pytest.mark.integration
def test_restore_backup_requires_explicit_confirmation(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    database_before = database_path.read_bytes()

    with pytest.raises(BackupConfirmationRequiredError):
        service.restore_backup(created.path, _PASSWORD, confirmed=False)

    assert database_path.read_bytes() == database_before


@pytest.mark.integration
def test_restore_backup_does_not_touch_the_database_without_confirmation_even_if_invalid(
    database_path: Path, backups_dir: Path
) -> None:
    """Confirmation is checked before any decryption or validation happens."""
    service = build_sqlite_backup_service(database_path, backups_dir)
    database_before = database_path.read_bytes()
    nonexistent_backup = backups_dir / "does-not-exist.siriusbackup"

    with pytest.raises(BackupConfirmationRequiredError):
        service.restore_backup(nonexistent_backup, _PASSWORD, confirmed=False)

    assert database_path.read_bytes() == database_before


@pytest.mark.integration
def test_restore_backup_replaces_the_database_atomically(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    _write_marker(database_path, 111)
    created = service.create_backup(_PASSWORD)
    _write_marker(database_path, 222)

    result = service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert _read_marker(database_path) == 111
    assert result.manifest == created.manifest
    assert result.path == created.path


@pytest.mark.integration
def test_restore_backup_creates_a_validated_safety_copy_of_the_current_database(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    _write_marker(database_path, 111)
    created = service.create_backup(_PASSWORD)
    _write_marker(database_path, 222)

    result = service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert result.safety_backup_path is not None
    assert result.safety_backup_path.is_file()
    assert result.safety_backup_path != created.path

    safety_validation = service.validate_backup(result.safety_backup_path, _PASSWORD)
    assert safety_validation.path == result.safety_backup_path


@pytest.mark.integration
def test_restore_backup_leaves_the_safety_copy_as_the_only_extra_file(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)

    result = service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert result.safety_backup_path is not None
    assert set(backups_dir.iterdir()) == {created.path, result.safety_backup_path}
    assert all(not entry.name.endswith(".tmp") for entry in backups_dir.iterdir())


@pytest.mark.integration
def test_restore_backup_rejects_wrong_password_without_modifying_data(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    database_before = database_path.read_bytes()

    with pytest.raises(BackupValidationError, match="contraseña"):
        service.restore_backup(created.path, "wrong password", confirmed=True)

    assert database_path.read_bytes() == database_before
    assert list(backups_dir.iterdir()) == [created.path]


@pytest.mark.integration
def test_restore_backup_rejects_a_tampered_backup_without_modifying_data(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    database_before = database_path.read_bytes()
    envelope = json.loads(created.path.read_text(encoding="utf-8"))
    ciphertext = envelope["ciphertext"]
    envelope["ciphertext"] = f"{ciphertext[:-1]}A"
    created.path.write_text(json.dumps(envelope), encoding="utf-8")

    with pytest.raises(BackupValidationError):
        service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert database_path.read_bytes() == database_before
    assert list(backups_dir.iterdir()) == [created.path]


@pytest.mark.integration
def test_restore_backup_rejects_an_incompatible_schema_without_modifying_data(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    database_before = database_path.read_bytes()

    _rewrite_manifest(created.path, _PASSWORD, schema_version="future-schema")

    with pytest.raises(BackupValidationError, match="esquema incompatible"):
        service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert database_path.read_bytes() == database_before
    assert list(backups_dir.iterdir()) == [created.path]


@pytest.mark.integration
def test_restore_backup_rejects_a_valid_sqlite_database_missing_the_alembic_version_table(
    database_path: Path, backups_dir: Path, tmp_path: Path
) -> None:
    """A packaged database can be a perfectly valid SQLite file (passes
    ``integrity_check``) yet have no ``alembic_version`` table at all, e.g. a
    non-Sirius database. Reading its schema must fail safely with a
    ``BackupValidationError`` — never a raw ``sqlite3.OperationalError`` —
    and must never touch the current database.
    """
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    database_before = database_path.read_bytes()

    no_version_db_path = tmp_path / "no-alembic-version.db"
    connection = sqlite3.connect(str(no_version_db_path))
    try:
        connection.execute("CREATE TABLE dummy (id INTEGER PRIMARY KEY)")
        connection.commit()
    finally:
        connection.close()
    no_version_db_bytes = no_version_db_path.read_bytes()

    def replace_with_a_table_missing_alembic_version(
        manifest: dict[str, object], _db_bytes: bytes
    ) -> tuple[dict[str, object], bytes]:
        manifest["sha256"] = hashlib.sha256(no_version_db_bytes).hexdigest()
        return manifest, no_version_db_bytes

    _rewrite_backup_package(created.path, _PASSWORD, replace_with_a_table_missing_alembic_version)

    with pytest.raises(BackupValidationError, match="esquema"):
        service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert database_path.read_bytes() == database_before
    assert list(backups_dir.iterdir()) == [created.path]


@pytest.mark.integration
def test_restore_backup_rejects_oversized_files_without_reading_or_modifying_data(
    database_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    database_before = database_path.read_bytes()
    monkeypatch.setattr(backup_module, "_MAX_BACKUP_SIZE_BYTES", 10)

    with pytest.raises(BackupTooLargeError):
        service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert database_path.read_bytes() == database_before


@pytest.mark.integration
def test_restore_backup_rolls_back_automatically_when_post_restore_validation_fails(
    database_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-restore validation (in a temp file) must still pass; only the
    post-replace check on the live database path is forced to fail once, so
    the rollback's own post-check (a second, legitimate call) still succeeds.
    """
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    real_verify = backup_module._verify_database_matches_manifest
    calls = {"count": 0}

    def _fail_only_the_first_call(path: Path, manifest: BackupManifest) -> bool:
        calls["count"] += 1
        if calls["count"] == 1:
            return False
        return real_verify(path, manifest)

    service = build_sqlite_backup_service(database_path, backups_dir)
    _write_marker(database_path, 111)
    created = service.create_backup(_PASSWORD)
    _write_marker(database_path, 222)

    monkeypatch.setattr(
        backup_module, "_verify_database_matches_manifest", _fail_only_the_first_call
    )

    with pytest.raises(BackupRestoreError, match="validación posterior"):
        service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert _read_marker(database_path) == 222


@pytest.mark.integration
def test_restore_backup_rolls_back_if_sidecar_removal_fails_once_after_replacing(
    database_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``PermissionError`` while deleting a stale sidecar right after the
    replace must not leave the new, unverified database installed: it must
    trigger the same automatic rollback as a failed post-restore validation.
    """
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    real_remove = backup_module._remove_sqlite_sidecars
    calls = {"count": 0}

    def _fail_only_the_first_call(path: Path) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise PermissionError("simulated failure removing a stale sidecar")
        real_remove(path)

    service = build_sqlite_backup_service(database_path, backups_dir)
    _write_marker(database_path, 111)
    created = service.create_backup(_PASSWORD)
    _write_marker(database_path, 222)

    monkeypatch.setattr(backup_module, "_remove_sqlite_sidecars", _fail_only_the_first_call)

    with pytest.raises(BackupRestoreError, match="validación posterior"):
        service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert _read_marker(database_path) == 222


@pytest.mark.integration
def test_restore_backup_rolls_back_if_verification_raises_once_after_replacing(
    database_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even though ``_verify_database_matches_manifest`` is meant to be total,
    restore_backup must not trust that blindly: if it somehow raises anyway,
    the outcome must still be an automatic rollback, not a leaked exception
    with the new, unverified database left installed.
    """
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    real_verify = backup_module._verify_database_matches_manifest
    calls = {"count": 0}

    def _raise_only_the_first_call(path: Path, manifest: BackupManifest) -> bool:
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("simulated I/O failure while verifying the restored database")
        return real_verify(path, manifest)

    service = build_sqlite_backup_service(database_path, backups_dir)
    _write_marker(database_path, 111)
    created = service.create_backup(_PASSWORD)
    _write_marker(database_path, 222)

    monkeypatch.setattr(
        backup_module, "_verify_database_matches_manifest", _raise_only_the_first_call
    )

    with pytest.raises(BackupRestoreError, match="validación posterior"):
        service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert _read_marker(database_path) == 222


@pytest.mark.integration
def test_restore_backup_reports_explicit_failure_when_the_rollback_itself_is_not_verified(
    database_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If even the post-rollback verification cannot confirm the previous
    state was restored intact, Sirius must say so explicitly rather than
    silently reporting the generic "restored, then rolled back" outcome.
    """
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    service = build_sqlite_backup_service(database_path, backups_dir)
    _write_marker(database_path, 111)
    created = service.create_backup(_PASSWORD)
    _write_marker(database_path, 222)

    monkeypatch.setattr(
        backup_module, "_verify_database_matches_manifest", lambda _path, _manifest: False
    )

    with pytest.raises(BackupRestoreError, match="no dejó los datos anteriores íntegros"):
        service.restore_backup(created.path, _PASSWORD, confirmed=True)


@pytest.mark.integration
def test_restore_backup_leaves_no_partial_file_if_the_atomic_replace_fails(
    database_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The safety copy (a different path) must still be written; only the
    replace of the live database path is forced to fail.
    """
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    database_before = database_path.read_bytes()
    real_replace = os.replace

    def _fail_only_for_live_database(src: str, dst: str) -> None:
        if Path(dst) == database_path:
            raise OSError("simulated failure during the atomic rename")
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", _fail_only_for_live_database)

    with pytest.raises(BackupRestoreError, match="reemplazar"):
        service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert database_path.read_bytes() == database_before
    remaining_tmp_files = [p for p in database_path.parent.iterdir() if p.suffix == ".tmp"]
    assert remaining_tmp_files == []


@pytest.mark.integration
def test_restore_backup_over_a_missing_database_removes_it_on_failed_rollback_target(
    tmp_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    source_db = tmp_path / "source.db"
    upgrade_to_head(source_db)
    source_service = build_sqlite_backup_service(source_db, backups_dir)
    created = source_service.create_backup(_PASSWORD)

    missing_db = tmp_path / "missing.db"
    service = build_sqlite_backup_service(missing_db, backups_dir)
    monkeypatch.setattr(
        backup_module, "_verify_database_matches_manifest", lambda _path, _manifest: False
    )

    with pytest.raises(BackupRestoreError, match="validación posterior"):
        service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert not missing_db.exists()


@pytest.mark.integration
def test_verify_database_matches_manifest_is_true_for_a_faithful_restore(
    database_path: Path, backups_dir: Path
) -> None:
    """Manifest hashes are computed over the packaged (``VACUUM INTO``) bytes,
    not the live file's raw bytes, so this writes what a real restore would
    write before asserting the verification helper accepts it.
    """
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)

    package_bytes = decrypt_envelope(created.path.read_bytes(), _PASSWORD)
    with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
        db_bytes = archive.read("sirius.db")
    database_path.write_bytes(db_bytes)

    assert backup_module._verify_database_matches_manifest(database_path, created.manifest)


@pytest.mark.integration
def test_verify_database_matches_manifest_is_false_for_a_missing_database(
    database_path: Path, backups_dir: Path, tmp_path: Path
) -> None:
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)

    assert not backup_module._verify_database_matches_manifest(
        tmp_path / "missing.db", created.manifest
    )


@pytest.mark.integration
def test_verify_database_matches_manifest_opens_read_only_and_never_creates_a_missing_database(
    database_path: Path, backups_dir: Path, tmp_path: Path
) -> None:
    """Opening ``mode=ro`` must fail (safely, returning ``False``) instead of
    ever creating the file, unlike a normal ``sqlite3.connect``.
    """
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    missing_path = tmp_path / "never-created.db"

    result = backup_module._verify_database_matches_manifest(missing_path, created.manifest)

    assert result is False
    assert not missing_path.exists()


def _write_restored_bytes(database_path: Path, backup_path: Path, password: str) -> None:
    """Write the exact bytes a real restore would write, so a test can then
    tamper with only the manifest (isolating one failure mode at a time).
    """
    package_bytes = decrypt_envelope(backup_path.read_bytes(), password)
    with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
        db_bytes = archive.read("sirius.db")
    database_path.write_bytes(db_bytes)


@pytest.mark.integration
def test_verify_database_matches_manifest_is_false_for_a_sha256_mismatch(
    database_path: Path, backups_dir: Path
) -> None:
    import dataclasses

    import sirius.adapters.backup.sqlite_backup_service as backup_module

    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    _write_restored_bytes(database_path, created.path, _PASSWORD)
    tampered_manifest = dataclasses.replace(created.manifest, sha256="0" * 64)

    assert not backup_module._verify_database_matches_manifest(database_path, tampered_manifest)


@pytest.mark.integration
def test_verify_database_matches_manifest_is_false_for_a_schema_mismatch(
    database_path: Path, backups_dir: Path
) -> None:
    import dataclasses

    import sirius.adapters.backup.sqlite_backup_service as backup_module

    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    _write_restored_bytes(database_path, created.path, _PASSWORD)
    tampered_manifest = dataclasses.replace(created.manifest, schema_version="future-schema")

    assert not backup_module._verify_database_matches_manifest(database_path, tampered_manifest)


@pytest.mark.integration
def test_verify_database_matches_manifest_is_false_for_a_corrupted_database(
    database_path: Path, backups_dir: Path
) -> None:
    import dataclasses

    import sirius.adapters.backup.sqlite_backup_service as backup_module

    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    corrupted_bytes = b"this is not a valid sqlite database"
    database_path.write_bytes(corrupted_bytes)
    matching_manifest = dataclasses.replace(
        created.manifest, sha256=hashlib.sha256(corrupted_bytes).hexdigest()
    )

    assert not backup_module._verify_database_matches_manifest(database_path, matching_manifest)


@pytest.mark.integration
def test_restore_backup_removes_stale_sqlite_sidecars_after_replacing_the_database(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    _write_marker(database_path, 111)
    created = service.create_backup(_PASSWORD)
    _write_marker(database_path, 222)
    sidecars = [Path(f"{database_path}{suffix}") for suffix in ("-wal", "-shm", "-journal")]
    for sidecar in sidecars:
        sidecar.write_bytes(b"stale sidecar left behind by a previous crash")

    service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert _read_marker(database_path) == 111
    assert all(not sidecar.exists() for sidecar in sidecars)


@pytest.mark.integration
def test_restore_backup_removes_stale_sqlite_sidecars_after_rolling_back(
    database_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    real_verify = backup_module._verify_database_matches_manifest
    calls = {"count": 0}

    def _fail_only_the_first_call(path: Path, manifest: BackupManifest) -> bool:
        calls["count"] += 1
        if calls["count"] == 1:
            return False
        return real_verify(path, manifest)

    service = build_sqlite_backup_service(database_path, backups_dir)
    _write_marker(database_path, 111)
    created = service.create_backup(_PASSWORD)
    _write_marker(database_path, 222)
    sidecars = [Path(f"{database_path}{suffix}") for suffix in ("-wal", "-shm", "-journal")]
    for sidecar in sidecars:
        sidecar.write_bytes(b"stale sidecar left behind by a previous crash")

    monkeypatch.setattr(
        backup_module, "_verify_database_matches_manifest", _fail_only_the_first_call
    )

    with pytest.raises(BackupRestoreError, match="validación posterior"):
        service.restore_backup(created.path, _PASSWORD, confirmed=True)

    assert _read_marker(database_path) == 222
    assert all(not sidecar.exists() for sidecar in sidecars)


@pytest.mark.integration
def test_restore_backup_result_manifest_hash_matches_the_restored_database(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)

    result = service.restore_backup(created.path, _PASSWORD, confirmed=True)

    package_bytes = decrypt_envelope(created.path.read_bytes(), _PASSWORD)
    with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
        db_bytes = archive.read("sirius.db")

    assert result.manifest.sha256 == hashlib.sha256(database_path.read_bytes()).hexdigest()
    assert result.manifest.sha256 == hashlib.sha256(db_bytes).hexdigest()
