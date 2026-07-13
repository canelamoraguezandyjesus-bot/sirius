"""Integration tests for the encrypted single-file backup adapter.

SIRIUS-ARQ-0.1 S12.2: backup creation must produce one ``.siriusbackup``
file with a manifest (format, app version, schema, date, hash), stay under
the 100 MB Fernet limit, and self-validate before ever announcing success.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

import pytest

from sirius import __version__ as APP_VERSION
from sirius.adapters.backup.sqlite_backup_service import _decrypt_envelope as decrypt_envelope
from sirius.adapters.backup.sqlite_backup_service import build_sqlite_backup_service
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.ports.backup import BackupError, BackupTooLargeError

_PASSWORD = "correct horse battery staple"


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "sirius.db"
    upgrade_to_head(path)
    return path


@pytest.fixture
def backups_dir(tmp_path: Path) -> Path:
    return tmp_path / "backups"


def _decrypted_package(backup_path: Path, password: str) -> bytes:
    return decrypt_envelope(backup_path.read_bytes(), password)


@pytest.mark.integration
def test_create_backup_writes_a_single_file_with_the_sirius_extension(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)

    result = service.create_backup(_PASSWORD)

    assert result.path.is_file()
    assert result.path.parent == backups_dir
    assert result.path.suffix == ".siriusbackup"
    assert list(backups_dir.iterdir()) == [result.path]


@pytest.mark.integration
def test_create_backup_stays_within_the_100mb_limit(database_path: Path, backups_dir: Path) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)

    result = service.create_backup(_PASSWORD)

    assert result.size_bytes == result.path.stat().st_size
    assert result.size_bytes <= 100 * 1024 * 1024


@pytest.mark.integration
def test_create_backup_manifest_has_format_version_schema_and_hash(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)

    result = service.create_backup(_PASSWORD)

    assert result.manifest.format == "siriusbackup"
    assert result.manifest.app_version == APP_VERSION
    assert result.manifest.schema_version  # non-empty alembic head revision
    assert len(result.manifest.sha256) == 64


@pytest.mark.integration
def test_create_backup_rejects_an_empty_password_and_writes_nothing(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)

    with pytest.raises(BackupError):
        service.create_backup("")

    assert not backups_dir.exists() or list(backups_dir.iterdir()) == []


@pytest.mark.integration
def test_create_backup_package_contains_only_manifest_and_database(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)

    result = service.create_backup(_PASSWORD)

    package_bytes = _decrypted_package(result.path, _PASSWORD)
    with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
        assert set(archive.namelist()) == {"manifest.json", "sirius.db"}
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        db_bytes = archive.read("sirius.db")

    assert manifest["sha256"] == result.manifest.sha256
    assert manifest["schema_version"] == result.manifest.schema_version
    assert hashlib.sha256(db_bytes).hexdigest() == result.manifest.sha256


@pytest.mark.integration
def test_create_backup_never_leaks_data_outside_the_database_file(
    database_path: Path, backups_dir: Path, tmp_path: Path
) -> None:
    """Sibling files (like logs, which may contain an API key reference) must
    never end up inside the backup: only the database snapshot is packaged.
    """
    secret_marker = "sk-should-never-leak-into-a-backup"
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "application.log").write_text(f"api key used: {secret_marker}", encoding="utf-8")

    service = build_sqlite_backup_service(database_path, backups_dir)
    result = service.create_backup(_PASSWORD)

    package_bytes = _decrypted_package(result.path, _PASSWORD)
    assert secret_marker.encode("utf-8") not in package_bytes
    assert secret_marker.encode("utf-8") not in result.path.read_bytes()


@pytest.mark.integration
def test_create_backup_can_be_decrypted_only_with_the_correct_password(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)
    result = service.create_backup(_PASSWORD)

    _decrypted_package(result.path, _PASSWORD)  # does not raise

    with pytest.raises(BackupError):
        _decrypted_package(result.path, "wrong password")


@pytest.mark.integration
def test_create_backup_refuses_to_exceed_the_100mb_limit(
    database_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    monkeypatch.setattr(backup_module, "_MAX_BACKUP_SIZE_BYTES", 10)
    service = build_sqlite_backup_service(database_path, backups_dir)

    with pytest.raises(BackupTooLargeError):
        service.create_backup(_PASSWORD)

    assert not backups_dir.exists() or list(backups_dir.iterdir()) == []


@pytest.mark.integration
def test_create_backup_creates_the_backups_directory_if_missing(
    database_path: Path, backups_dir: Path
) -> None:
    assert not backups_dir.exists()
    service = build_sqlite_backup_service(database_path, backups_dir)

    service.create_backup(_PASSWORD)

    assert backups_dir.is_dir()


@pytest.mark.integration
def test_create_backup_leaves_no_partial_file_if_the_temporary_write_fails(
    database_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _broken_fsync(_fd: int) -> None:
        raise OSError("simulated crash mid-write")

    monkeypatch.setattr(os, "fsync", _broken_fsync)
    service = build_sqlite_backup_service(database_path, backups_dir)

    with pytest.raises(OSError, match="simulated crash mid-write"):
        service.create_backup(_PASSWORD)

    assert list(backups_dir.iterdir()) == []


@pytest.mark.integration
def test_create_backup_leaves_no_partial_file_if_the_atomic_replace_fails(
    database_path: Path, backups_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _broken_replace(_src: str, _dst: str) -> None:
        raise OSError("simulated failure during the atomic rename")

    monkeypatch.setattr(os, "replace", _broken_replace)
    service = build_sqlite_backup_service(database_path, backups_dir)

    with pytest.raises(OSError, match="simulated failure during the atomic rename"):
        service.create_backup(_PASSWORD)

    assert list(backups_dir.iterdir()) == []


@pytest.mark.integration
def test_create_backup_generates_distinct_files_for_immediate_successive_backups(
    database_path: Path, backups_dir: Path
) -> None:
    service = build_sqlite_backup_service(database_path, backups_dir)

    first = service.create_backup(_PASSWORD)
    second = service.create_backup(_PASSWORD)

    assert first.path != second.path
    assert first.path.is_file()
    assert second.path.is_file()
    assert sorted(backups_dir.iterdir()) == sorted([first.path, second.path])


def test_argon2_kdf_parameters_match_the_approved_owasp_profile() -> None:
    """SIRIUS-ARQ-0.1 S12.2 approved the OWASP-recommended Argon2id minimum
    profile; this pins those constants so a change would fail loudly here
    rather than silently weaken every future backup.
    """
    import sirius.adapters.backup.sqlite_backup_service as backup_module

    assert backup_module._ARGON2_TIME_COST == 2
    assert backup_module._ARGON2_MEMORY_COST_KIB == 19_456
    assert backup_module._ARGON2_PARALLELISM == 1
    assert backup_module._ARGON2_SALT_BYTES == 16
    assert backup_module._ARGON2_KEY_BYTES == 32
