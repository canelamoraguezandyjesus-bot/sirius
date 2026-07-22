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
from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet

from sirius.adapters.backup.sqlite_backup_service import _derive_key as derive_key
from sirius.adapters.backup.sqlite_backup_service import _KdfParams, build_sqlite_backup_service
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.ports.backup import BackupTooLargeError, BackupValidationError

_PASSWORD = "correct horse battery staple"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_OLDER_SCHEMA_REVISION = "c4d8fc9d6f51"


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
def test_validate_backup_rejects_wrong_password(database_path: Path, backups_dir: Path) -> None:
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
    # Cambia el último carácter por otro DISTINTO garantizado: reemplazarlo
    # siempre por "A" no corrompía nada cuando el texto cifrado ya terminaba
    # en "A" (el cifrado es no determinista, así que ocurría de forma
    # intermitente ~1 de cada 60 ejecuciones y la validación no rechazaba nada).
    tampered_last = "B" if ciphertext[-1] == "A" else "A"
    envelope["ciphertext"] = f"{ciphertext[:-1]}{tampered_last}"
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
def test_validate_backup_rejects_a_coherent_but_unsupported_internal_schema(
    database_path: Path, backups_dir: Path, tmp_path: Path
) -> None:
    """A manifest can lie about ``schema_version`` and still be internally
    coherent (its ``sha256`` genuinely matches the packaged database) if the
    packaged database itself was downgraded to an older, still-valid schema.
    Validation must catch this by reading the database's own real schema
    marker, not just trusting whatever the manifest declares.
    """
    service = build_sqlite_backup_service(database_path, backups_dir)
    created = service.create_backup(_PASSWORD)

    def downgrade_to_an_older_but_internally_consistent_schema(
        _manifest: dict[str, object], db_bytes: bytes
    ) -> tuple[dict[str, object], bytes]:
        older_db_path = tmp_path / "older-schema.db"
        older_db_path.write_bytes(db_bytes)
        config = Config(str(_REPO_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(_REPO_ROOT / "migrations"))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{older_db_path}")
        command.downgrade(config, _OLDER_SCHEMA_REVISION)
        older_db_bytes = older_db_path.read_bytes()
        coherent_manifest: dict[str, object] = {
            "format": "siriusbackup",
            "app_version": created.manifest.app_version,
            "schema_version": _OLDER_SCHEMA_REVISION,
            "created_at": created.manifest.created_at.isoformat(),
            "sha256": hashlib.sha256(older_db_bytes).hexdigest(),
        }
        return coherent_manifest, older_db_bytes

    _rewrite_encrypted_package(
        created.path, _PASSWORD, downgrade_to_an_older_but_internally_consistent_schema
    )

    with pytest.raises(BackupValidationError, match="no soportada"):
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
