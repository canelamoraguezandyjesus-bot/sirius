"""Encrypted single-file backup adapter (SIRIUS-ARQ-0.1 S12.2).

Snapshots the SQLite database with ``VACUUM INTO``, packages it with a
``manifest.json`` (format, app version, schema version, timestamp, hash),
encrypts the package with a password-derived Argon2id key using Fernet, and
self-validates (decrypt, manifest, hash, SQLite integrity check) before ever
writing the final ``.siriusbackup`` file. Never touches ``SecretStore``: the
OpenAI API key is never part of the SQLite database, so it cannot leak into
the package.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import json
import os
import secrets
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from argon2.low_level import Type, hash_secret_raw
from cryptography.fernet import Fernet, InvalidToken

from sirius import __version__ as _APP_VERSION
from sirius.ports.backup import BackupError, BackupManifest, BackupResult, BackupTooLargeError

_BACKUP_FORMAT = "siriusbackup"
_ENVELOPE_VERSION = 1
_MANIFEST_ENTRY = "manifest.json"
_DATABASE_ENTRY = "sirius.db"

# OWASP-recommended Argon2id minimum profile: fast enough for an interactive
# manual backup, strong enough for a password-derived encryption key.
_ARGON2_TIME_COST = 2
_ARGON2_MEMORY_COST_KIB = 19_456
_ARGON2_PARALLELISM = 1
_ARGON2_SALT_BYTES = 16
_ARGON2_KEY_BYTES = 32

_MAX_BACKUP_SIZE_BYTES = 100 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class _KdfParams:
    salt: bytes
    time_cost: int
    memory_cost_kib: int
    parallelism: int


def _derive_key(password: str, params: _KdfParams) -> bytes:
    raw_key = hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=params.salt,
        time_cost=params.time_cost,
        memory_cost=params.memory_cost_kib,
        parallelism=params.parallelism,
        hash_len=_ARGON2_KEY_BYTES,
        type=Type.ID,
    )
    return base64.urlsafe_b64encode(raw_key)


def _snapshot_database(database_path: Path, destination: Path) -> None:
    connection = sqlite3.connect(str(database_path))
    try:
        connection.execute("VACUUM INTO ?", (str(destination),))
    finally:
        connection.close()


def _read_schema_version(snapshot_path: Path) -> str:
    connection = sqlite3.connect(str(snapshot_path))
    try:
        row = connection.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
        return str(row[0]) if row is not None else "unknown"
    finally:
        connection.close()


def _quick_check(snapshot_path: Path) -> bool:
    connection = sqlite3.connect(str(snapshot_path))
    try:
        row = connection.execute("PRAGMA quick_check").fetchone()
        return row is not None and str(row[0]) == "ok"
    finally:
        connection.close()


def _build_package(db_bytes: bytes, manifest_bytes: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(_MANIFEST_ENTRY, manifest_bytes)
        archive.writestr(_DATABASE_ENTRY, db_bytes)
    return buffer.getvalue()


def _read_package(package_bytes: bytes) -> tuple[dict[str, object], bytes]:
    with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
        manifest = json.loads(archive.read(_MANIFEST_ENTRY).decode("utf-8"))
        db_bytes = archive.read(_DATABASE_ENTRY)
    return manifest, db_bytes


def _build_envelope(ciphertext: bytes, params: _KdfParams) -> bytes:
    envelope = {
        "sirius_backup_format": _ENVELOPE_VERSION,
        "kdf": {
            "name": "argon2id",
            "salt": base64.b64encode(params.salt).decode("ascii"),
            "time_cost": params.time_cost,
            "memory_cost_kib": params.memory_cost_kib,
            "parallelism": params.parallelism,
        },
        "ciphertext": ciphertext.decode("ascii"),
    }
    return json.dumps(envelope, ensure_ascii=False).encode("utf-8")


def _write_atomically(destination: Path, data: bytes) -> None:
    """Write ``data`` to ``destination`` without ever exposing a partial file.

    Writes to a temporary file in the same directory (so the later rename is
    on the same filesystem and therefore atomic on both POSIX and Windows),
    fsyncs it, then swaps it into place with ``os.replace``. Any failure
    before the swap removes the temporary file instead of leaving it behind.
    """
    directory = destination.parent
    fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=".sirius-backup-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            tmp_file.write(data)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_name, destination)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_name)
        raise


def _decrypt_envelope(envelope_bytes: bytes, password: str) -> bytes:
    envelope = json.loads(envelope_bytes.decode("utf-8"))
    kdf = envelope["kdf"]
    params = _KdfParams(
        salt=base64.b64decode(kdf["salt"]),
        time_cost=kdf["time_cost"],
        memory_cost_kib=kdf["memory_cost_kib"],
        parallelism=kdf["parallelism"],
    )
    key = _derive_key(password, params)
    ciphertext = envelope["ciphertext"].encode("ascii")
    try:
        return Fernet(key).decrypt(ciphertext)
    except InvalidToken as exc:
        msg = "No se pudo descifrar la copia recién creada; contraseña o clave inválida."
        raise BackupError(msg) from exc


class SQLiteBackupService:
    """Creates a validated, encrypted single-file backup of the local database."""

    def __init__(self, database_path: Path, backups_dir: Path) -> None:
        self._database_path = database_path
        self._backups_dir = backups_dir

    def create_backup(self, password: str) -> BackupResult:
        if not password:
            msg = "La contraseña de la copia no puede estar vacía."
            raise BackupError(msg)

        created_at = datetime.now(UTC)
        self._backups_dir.mkdir(parents=True, exist_ok=True)
        unique_suffix = secrets.token_hex(4)
        destination = self._backups_dir / (
            f"sirius-backup-{created_at.strftime('%Y%m%d-%H%M%S')}-{unique_suffix}.{_BACKUP_FORMAT}"
        )

        db_bytes, schema_version = self._snapshot()
        db_sha256 = hashlib.sha256(db_bytes).hexdigest()
        manifest = BackupManifest(
            format=_BACKUP_FORMAT,
            app_version=_APP_VERSION,
            schema_version=schema_version,
            created_at=created_at,
            sha256=db_sha256,
        )
        manifest_bytes = json.dumps(
            {
                "format": manifest.format,
                "app_version": manifest.app_version,
                "schema_version": manifest.schema_version,
                "created_at": manifest.created_at.isoformat(),
                "sha256": manifest.sha256,
            },
            ensure_ascii=False,
        ).encode("utf-8")

        package_bytes = _build_package(db_bytes, manifest_bytes)
        params = _KdfParams(
            salt=os.urandom(_ARGON2_SALT_BYTES),
            time_cost=_ARGON2_TIME_COST,
            memory_cost_kib=_ARGON2_MEMORY_COST_KIB,
            parallelism=_ARGON2_PARALLELISM,
        )
        ciphertext = Fernet(_derive_key(password, params)).encrypt(package_bytes)
        envelope_bytes = _build_envelope(ciphertext, params)

        if len(envelope_bytes) > _MAX_BACKUP_SIZE_BYTES:
            msg = (
                "La copia supera el límite de 100 MB soportado en Sirius 0.1; "
                "no se ha creado ningún archivo."
            )
            raise BackupTooLargeError(msg)

        self._validate(envelope_bytes, password, expected_sha256=db_sha256)

        _write_atomically(destination, envelope_bytes)
        return BackupResult(
            path=destination,
            manifest=manifest,
            size_bytes=len(envelope_bytes),
        )

    def _snapshot(self) -> tuple[bytes, str]:
        with tempfile.TemporaryDirectory() as scratch_dir:
            snapshot_path = Path(scratch_dir) / "sirius.db"
            _snapshot_database(self._database_path, snapshot_path)
            schema_version = _read_schema_version(snapshot_path)
            return snapshot_path.read_bytes(), schema_version

    def _validate(self, envelope_bytes: bytes, password: str, *, expected_sha256: str) -> None:
        package_bytes = _decrypt_envelope(envelope_bytes, password)
        manifest, db_bytes = _read_package(package_bytes)

        if manifest.get("sha256") != expected_sha256:
            msg = "La copia generada no superó la validación de integridad del manifiesto."
            raise BackupError(msg)
        if hashlib.sha256(db_bytes).hexdigest() != expected_sha256:
            msg = "La copia generada no superó la validación de integridad de la base."
            raise BackupError(msg)

        with tempfile.TemporaryDirectory() as scratch_dir:
            snapshot_path = Path(scratch_dir) / "sirius.db"
            snapshot_path.write_bytes(db_bytes)
            if not _quick_check(snapshot_path):
                msg = "La copia generada no superó la comprobación de integridad de SQLite."
                raise BackupError(msg)


def build_sqlite_backup_service(database_path: Path, backups_dir: Path) -> SQLiteBackupService:
    """Build a backup service bound to the given database file and backups directory."""
    return SQLiteBackupService(database_path, backups_dir)
