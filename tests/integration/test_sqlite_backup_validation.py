"""Integration tests for validating encrypted Sirius backup files."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
from cryptography.fernet import Fernet

from sirius.adapters.backup.sqlite_backup_service import _KdfParams
from sirius.adapters.backup.sqlite_backup_service import _derive_key as derive_key
from sirius.adapters.backup.sqlite_backup_service import build_sqlite_backup_service
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.ports.backup import BackupTooLargeError, BackupValidationError

_PASSWORD = "correct horse battery staple"


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "sirius.db"
    upgrade_to_head(path)
    return path


@pytest.fixture
def backups_dir(tmp_path: Path) -> Path:
    return tmp_path / "backups"


def _rewrite_encrypted_package(
    backup_path: Path,
    password: str,
    transform: Callable[[dict[str, object], bytes], tuple[dict[str, object], bytes]],
) -> None:
    envelope_value = json.loads(backup_path.read_text(encoding="utf-8"))
    assert isinstance(envelope_value, dict)
    envelope = cast(dict[str, object], envelope_value)
    kdf_value = envelope["kdf"]
    assert isinstance(kdf_value, dict)
    kdf = cast(dict[str, object], kdf_value)
    params = _KdfParams(
        salt=base64.b64decode(cast(str, kdf["salt"])),
        time_cost=cast(int, kdf["time_cost"]),
        memory_cost_kib=cast(int, kdf["memory_cost_kib"]),
        parallelism=cast(int, kdf["parallelism"]),
    )
    fernet = Fernet(derive_key(password, params))
    package = fernet.decrypt(cast(str, envelope["ciphertext"]).encode("ascii"))

    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        manifest_value = json.loads(archive.read("manifest.json").decode("utf-8"))
        assert isinstance(manifest_value, dict)
        manifest = cast(dict[str, object], manifest_value)
        db_bytes = archive.read("sirius.db")

    new_manifest, new_db_bytes = transform(manifest, db_bytes)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(new_manifest).encode("utf-8"))
        archive.writestr("sirius.db", new_db_bytes)
    envelope["ciphertext"] = fernet.encrypt(buffer.getvalue()).decode("ascii")
    backup_path.write_text(json.dumps(envelope), encoding="utf-8")


@pytest.mark.integration
def test_validate_backup_returns_verified_metadata_without_changing_current_data(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    database_before = database_path.read_bytes()

    validated = service.validate_backup(created.path, _PASSWORD)

    assert validated.path == created.path
    assert validated.manifest == created.manifest
    assert validated.size_bytes == created.path.stat().st_size
    assert database_path.read_bytes() == database_before


@pytest.mark.integration
def test_validate_backup_rejects_wrong_password(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)

    with pytest.raises(BackupValidationError, match="contraseña"):
        service.validate_backup(created.path, "wrong password")


@pytest.mark.integration
def test_validate_backup_rejects_a_tampered_ciphertext(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    envelope = json.loads(created.path.read_text(encoding="utf-8"))
    ciphertext = envelope["ciphertext"]
    envelope["ciphertext"] = f"{ciphertext[:-1]}A"
    created.path.write_text(json.dumps(envelope), encoding="utf-8")

    with pytest.raises(BackupValidationError):
        service.validate_backup(created.path, _PASSWORD)


@pytest.mark.integration
def test_validate_backup_rejects_an_incompatible_envelope_version(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    envelope = json.loads(created.path.read_text(encoding="utf-8"))
    envelope["sirius_backup_format"] = 999
    created.path.write_text(json.dumps(envelope), encoding="utf-8")

    with pytest.raises(BackupValidationError, match="versión del formato"):
        service.validate_backup(created.path, _PASSWORD)


@pytest.mark.integration
def test_validate_backup_rejects_unapproved_argon2_parameters_before_deriving_a_key(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    envelope = json.loads(created.path.read_text(encoding="utf-8"))
    envelope["kdf"]["memory_cost_kib"] = 2_000_000
    created.path.write_text(json.dumps(envelope), encoding="utf-8")

    with pytest.raises(BackupValidationError, match="Argon2id"):
        service.validate_backup(created.path, _PASSWORD)


@pytest.mark.integration
def test_validate_backup_rejects_a_manifest_hash_mismatch(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)

    def alter_database(
        manifest: dict[str, object], db_bytes: bytes
    ) -> tuple[dict[str, object], bytes]:
        return manifest, db_bytes + b"tampered"

    _rewrite_encrypted_package(created.path, _PASSWORD, alter_database)

    with pytest.raises(BackupValidationError, match="integridad"):
        service.validate_backup(created.path, _PASSWORD)


@pytest.mark.integration
def test_validate_backup_rejects_an_incompatible_schema(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)

    def alter_schema(
        manifest: dict[str, object], db_bytes: bytes
    ) -> tuple[dict[str, object], bytes]:
        manifest["schema_version"] = "future-schema"
        return manifest, db_bytes

    _rewrite_encrypted_package(created.path, _PASSWORD, alter_schema)

    with pytest.raises(BackupValidationError, match="esquema incompatible"):
        service.validate_backup(created.path, _PASSWORD)


@pytest.mark.integration
def test_validate_backup_rejects_invalid_sqlite_even_when_the_hash_matches(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)

    def replace_database(
        manifest: dict[str, object], _db_bytes: bytes
    ) -> tuple[dict[str, object], bytes]:
        invalid_db = b"this is not sqlite"
        manifest["sha256"] = hashlib.sha256(invalid_db).hexdigest()
        return manifest, invalid_db

    _rewrite_encrypted_package(created.path, _PASSWORD, replace_database)

    with pytest.raises(BackupValidationError, match="SQLite"):
        service.validate_backup(created.path, _PASSWORD)


@pytest.mark.integration
def test_validate_backup_rejects_oversized_files_without_reading_them(
    database_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)
    monkeypatch.setattr(backup_module, "_MAX_BACKUP_SIZE_BYTES", 10)

    with pytest.raises(BackupTooLargeError):
        service.validate_backup(created.path, _PASSWORD)
