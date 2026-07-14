"""Encrypted single-file backup adapter (SIRIUS-ARQ-0.1 S12.2-S12.3).

Creates encrypted SQLite backups and validates existing backup files before
any restore operation can use them. Validation treats backup files as untrusted
input: it checks the envelope and KDF profile before deriving a key, limits
uncompressed payload size, verifies manifest compatibility and hashes, and runs
SQLite ``integrity_check`` in a temporary directory.
"""

from __future__ import annotations

import base64
import binascii
import contextlib
import hashlib
import io
import json
import os
import re
import secrets
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from argon2.low_level import Type, hash_secret_raw
from cryptography.fernet import Fernet, InvalidToken

from sirius import __version__ as _APP_VERSION
from sirius.adapters.persistence.migrations import get_supported_schema_version
from sirius.ports.backup import (
    BackupConfirmationRequiredError,
    BackupError,
    BackupManifest,
    BackupRestoreError,
    BackupRestoreResult,
    BackupResult,
    BackupTooLargeError,
    BackupValidationError,
    BackupValidationResult,
)

_BACKUP_FORMAT = "siriusbackup"
_ENVELOPE_VERSION = 1
_MANIFEST_ENTRY = "manifest.json"
_DATABASE_ENTRY = "sirius.db"
_PACKAGE_ENTRIES = {_MANIFEST_ENTRY, _DATABASE_ENTRY}

# OWASP-recommended Argon2id minimum profile approved for Sirius 0.1.
_ARGON2_TIME_COST = 2
_ARGON2_MEMORY_COST_KIB = 19_456
_ARGON2_PARALLELISM = 1
_ARGON2_SALT_BYTES = 16
_ARGON2_KEY_BYTES = 32

_MAX_BACKUP_SIZE_BYTES = 100 * 1024 * 1024
_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)(?:\.|$)")


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


def _integrity_check(snapshot_path: Path) -> bool:
    connection = sqlite3.connect(str(snapshot_path))
    try:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
        return len(rows) == 1 and str(rows[0][0]) == "ok"
    except sqlite3.DatabaseError:
        return False
    finally:
        connection.close()


def _build_package(db_bytes: bytes, manifest_bytes: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(_MANIFEST_ENTRY, manifest_bytes)
        archive.writestr(_DATABASE_ENTRY, db_bytes)
    return buffer.getvalue()


def _read_package(package_bytes: bytes) -> tuple[dict[str, object], bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(_PACKAGE_ENTRIES) or set(names) != _PACKAGE_ENTRIES:
                msg = "La copia no contiene exactamente el manifiesto y la base de datos esperados."
                raise BackupValidationError(msg)
            if sum(info.file_size for info in infos) > _MAX_BACKUP_SIZE_BYTES:
                msg = "El contenido descomprimido de la copia supera el límite seguro de 100 MB."
                raise BackupTooLargeError(msg)

            manifest_value = json.loads(archive.read(_MANIFEST_ENTRY).decode("utf-8"))
            if not isinstance(manifest_value, dict):
                msg = "El manifiesto de la copia no tiene una estructura válida."
                raise BackupValidationError(msg)
            manifest = cast(dict[str, object], manifest_value)
            db_bytes = archive.read(_DATABASE_ENTRY)
    except BackupError:
        raise
    except (
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
    ) as exc:
        msg = "El paquete interno de la copia está dañado o tiene un formato inválido."
        raise BackupValidationError(msg) from exc
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
    """Write ``data`` without ever exposing a partial destination file."""
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


def _sqlite_sidecar_paths(database_path: Path) -> tuple[Path, Path, Path]:
    base = str(database_path)
    return Path(f"{base}-wal"), Path(f"{base}-shm"), Path(f"{base}-journal")


def _remove_sqlite_sidecars(database_path: Path) -> None:
    """Remove stale ``-wal``/``-shm``/``-journal`` files next to ``database_path``.

    ``os.replace`` swaps only the main SQLite file. A sidecar left over from
    the previous generation of the file would no longer correspond to its
    content, and SQLite could mistake it for an unfinished transaction and
    "recover" the new file back into a stale, partial state.
    """
    for sidecar in _sqlite_sidecar_paths(database_path):
        with contextlib.suppress(FileNotFoundError):
            sidecar.unlink()


def _verify_database_matches_manifest(database_path: Path, manifest: BackupManifest) -> bool:
    """Re-open ``database_path`` read-only and confirm it matches ``manifest``.

    Runs after every atomic replace (forward restore and rollback) so a
    corrupted or unexpectedly different file is caught before Sirius trusts
    it, instead of assuming the write succeeded just because it did not raise.

    This function is total: it never raises. Opening fails safe (a missing
    file, a locked file, an unreadable schema, or any other I/O/SQLite/schema
    lookup error all resolve to ``False``) and it only ever reads, never
    writes or creates a file — the connection URI forces SQLite's own
    read-only mode rather than relying on ``PRAGMA query_only`` alone.
    """
    if not database_path.is_file():
        return False
    try:
        if hashlib.sha256(database_path.read_bytes()).hexdigest() != manifest.sha256:
            return False
        supported_schema_version = get_supported_schema_version()
        readonly_uri = f"{database_path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(readonly_uri, uri=True)
        try:
            connection.execute("PRAGMA query_only = ON")
            row = connection.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
            real_schema_version = str(row[0]) if row is not None else "unknown"
            if real_schema_version != manifest.schema_version:
                return False
            if real_schema_version != supported_schema_version:
                return False
            integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
            return len(integrity_rows) == 1 and str(integrity_rows[0][0]) == "ok"
        finally:
            connection.close()
    except OSError, sqlite3.Error, RuntimeError:
        return False


def _parse_kdf_params(kdf: object) -> _KdfParams:
    if not isinstance(kdf, dict):
        msg = "La copia no contiene parámetros de derivación de clave válidos."
        raise BackupValidationError(msg)

    if kdf.get("name") != "argon2id":
        msg = "La copia utiliza un método de derivación de clave incompatible."
        raise BackupValidationError(msg)

    time_cost = kdf.get("time_cost")
    memory_cost_kib = kdf.get("memory_cost_kib")
    parallelism = kdf.get("parallelism")
    if (
        not isinstance(time_cost, int)
        or isinstance(time_cost, bool)
        or not isinstance(memory_cost_kib, int)
        or isinstance(memory_cost_kib, bool)
        or not isinstance(parallelism, int)
        or isinstance(parallelism, bool)
    ):
        msg = "La copia contiene parámetros Argon2id inválidos."
        raise BackupValidationError(msg)
    if (
        time_cost != _ARGON2_TIME_COST
        or memory_cost_kib != _ARGON2_MEMORY_COST_KIB
        or parallelism != _ARGON2_PARALLELISM
    ):
        msg = "La copia utiliza parámetros Argon2id incompatibles o inseguros."
        raise BackupValidationError(msg)

    salt_value = kdf.get("salt")
    if not isinstance(salt_value, str):
        msg = "La copia contiene una sal Argon2id inválida."
        raise BackupValidationError(msg)
    try:
        salt = base64.b64decode(salt_value, validate=True)
    except (binascii.Error, ValueError) as exc:
        msg = "La copia contiene una sal Argon2id inválida."
        raise BackupValidationError(msg) from exc
    if len(salt) != _ARGON2_SALT_BYTES:
        msg = "La copia contiene una sal Argon2id con longitud incompatible."
        raise BackupValidationError(msg)

    return _KdfParams(
        salt=salt,
        time_cost=time_cost,
        memory_cost_kib=memory_cost_kib,
        parallelism=parallelism,
    )


def _decrypt_envelope(envelope_bytes: bytes, password: str) -> bytes:
    try:
        envelope_value = json.loads(envelope_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = "La copia no contiene un sobre cifrado válido."
        raise BackupValidationError(msg) from exc
    if not isinstance(envelope_value, dict):
        msg = "La copia no contiene un sobre cifrado válido."
        raise BackupValidationError(msg)
    envelope = cast(dict[str, object], envelope_value)

    if envelope.get("sirius_backup_format") != _ENVELOPE_VERSION:
        msg = "La versión del formato de copia no es compatible con Sirius 0.1."
        raise BackupValidationError(msg)

    params = _parse_kdf_params(envelope.get("kdf"))
    ciphertext_value = envelope.get("ciphertext")
    if not isinstance(ciphertext_value, str):
        msg = "La copia no contiene un bloque cifrado válido."
        raise BackupValidationError(msg)
    try:
        ciphertext = ciphertext_value.encode("ascii")
    except UnicodeEncodeError as exc:
        msg = "La copia no contiene un bloque cifrado válido."
        raise BackupValidationError(msg) from exc

    try:
        return Fernet(_derive_key(password, params)).decrypt(ciphertext)
    except (InvalidToken, ValueError) as exc:
        msg = "La contraseña es incorrecta o la copia está dañada."
        raise BackupValidationError(msg) from exc


def _version_family(version: str) -> tuple[int, int] | None:
    match = _VERSION_PATTERN.match(version)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _manifest_from_mapping(manifest: dict[str, object]) -> BackupManifest:
    backup_format = manifest.get("format")
    app_version = manifest.get("app_version")
    schema_version = manifest.get("schema_version")
    created_at_value = manifest.get("created_at")
    sha256 = manifest.get("sha256")

    if backup_format != _BACKUP_FORMAT:
        msg = "El manifiesto declara un formato de copia incompatible."
        raise BackupValidationError(msg)
    if not isinstance(app_version, str) or _version_family(app_version) is None:
        msg = "El manifiesto contiene una versión de aplicación inválida."
        raise BackupValidationError(msg)
    if not isinstance(schema_version, str) or not schema_version or schema_version == "unknown":
        msg = "El manifiesto no contiene una versión de esquema válida."
        raise BackupValidationError(msg)
    if not isinstance(created_at_value, str):
        msg = "El manifiesto no contiene una fecha válida."
        raise BackupValidationError(msg)
    try:
        created_at = datetime.fromisoformat(created_at_value)
    except ValueError as exc:
        msg = "El manifiesto no contiene una fecha válida."
        raise BackupValidationError(msg) from exc
    if created_at.tzinfo is None:
        msg = "El manifiesto no contiene una fecha con zona horaria."
        raise BackupValidationError(msg)
    if not isinstance(sha256, str) or len(sha256) != 64:
        msg = "El manifiesto no contiene un hash SHA-256 válido."
        raise BackupValidationError(msg)
    try:
        int(sha256, 16)
    except ValueError as exc:
        msg = "El manifiesto no contiene un hash SHA-256 válido."
        raise BackupValidationError(msg) from exc

    return BackupManifest(
        format=backup_format,
        app_version=app_version,
        schema_version=schema_version,
        created_at=created_at,
        sha256=sha256.lower(),
    )


class SQLiteBackupService:
    """Creates and validates encrypted single-file SQLite backups."""

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

        self._validate_and_extract(
            envelope_bytes,
            password,
            expected_sha256=db_sha256,
        )

        _write_atomically(destination, envelope_bytes)
        return BackupResult(path=destination, manifest=manifest, size_bytes=len(envelope_bytes))

    def validate_backup(self, backup_path: Path, password: str) -> BackupValidationResult:
        manifest, _db_bytes, size_bytes = self._read_and_validate(backup_path, password)
        return BackupValidationResult(
            path=backup_path,
            manifest=manifest,
            size_bytes=size_bytes,
        )

    def restore_backup(
        self,
        backup_path: Path,
        password: str,
        *,
        confirmed: bool,
    ) -> BackupRestoreResult:
        if not confirmed:
            msg = "La restauración requiere confirmación explícita antes de modificar los datos."
            raise BackupConfirmationRequiredError(msg)

        manifest, restored_db_bytes, size_bytes = self._read_and_validate(backup_path, password)

        database_existed = self._database_path.is_file()
        safety_backup_path = self.create_backup(password).path if database_existed else None

        try:
            _write_atomically(self._database_path, restored_db_bytes)
        except OSError as exc:
            msg = (
                "No se pudo reemplazar la base de datos de forma atómica; "
                "no se modificaron los datos actuales."
            )
            raise BackupRestoreError(msg) from exc

        try:
            _remove_sqlite_sidecars(self._database_path)
            restored_ok = _verify_database_matches_manifest(self._database_path, manifest)
        except Exception:
            # Anything going wrong after a successful replace (sidecar cleanup,
            # opening the file, hashing, schema lookup, integrity check) must
            # never leave the new, unverified database installed — treat it
            # exactly like a failed post-restore validation and roll back.
            restored_ok = False

        if restored_ok:
            return BackupRestoreResult(
                path=backup_path,
                manifest=manifest,
                size_bytes=size_bytes,
                safety_backup_path=safety_backup_path,
            )

        self._rollback_after_failed_restore(safety_backup_path, password, database_existed)
        msg = (
            "La base restaurada no superó la validación posterior; "
            "se revirtió automáticamente al estado anterior."
        )
        raise BackupRestoreError(msg)

    def _rollback_after_failed_restore(
        self,
        safety_backup_path: Path | None,
        password: str,
        database_existed: bool,
    ) -> None:
        rollback_ok = False
        try:
            if safety_backup_path is not None:
                envelope_bytes = safety_backup_path.read_bytes()
                safety_manifest, safety_db_bytes = self._validate_and_extract(
                    envelope_bytes, password
                )
                _write_atomically(self._database_path, safety_db_bytes)
                _remove_sqlite_sidecars(self._database_path)
                rollback_ok = _verify_database_matches_manifest(
                    self._database_path, safety_manifest
                )
            elif not database_existed:
                with contextlib.suppress(FileNotFoundError):
                    self._database_path.unlink()
                _remove_sqlite_sidecars(self._database_path)
                rollback_ok = not self._database_path.exists()
        except Exception as exc:
            msg = (
                "La restauración falló la validación posterior y el rollback automático "
                "también falló; los datos actuales podrían estar dañados. La copia de "
                f"seguridad previa sigue disponible en: {safety_backup_path}."
            )
            raise BackupRestoreError(msg) from exc

        if not rollback_ok:
            msg = (
                "La restauración falló la validación posterior; el rollback automático no "
                "dejó los datos anteriores íntegros y los datos actuales podrían estar "
                f"dañados. La copia de seguridad previa sigue disponible en: {safety_backup_path}."
            )
            raise BackupRestoreError(msg)

    def _snapshot(self) -> tuple[bytes, str]:
        with tempfile.TemporaryDirectory() as scratch_dir:
            snapshot_path = Path(scratch_dir) / "sirius.db"
            _snapshot_database(self._database_path, snapshot_path)
            schema_version = _read_schema_version(snapshot_path)
            return snapshot_path.read_bytes(), schema_version

    def _read_and_validate(
        self, backup_path: Path, password: str
    ) -> tuple[BackupManifest, bytes, int]:
        if not password:
            msg = "La contraseña de la copia no puede estar vacía."
            raise BackupValidationError(msg)
        if not backup_path.is_file():
            msg = "El archivo de copia no existe o no es un archivo válido."
            raise BackupValidationError(msg)

        try:
            size_bytes = backup_path.stat().st_size
        except OSError as exc:
            msg = "No se pudo leer la información del archivo de copia."
            raise BackupValidationError(msg) from exc
        if size_bytes > _MAX_BACKUP_SIZE_BYTES:
            msg = "La copia supera el límite seguro de 100 MB soportado en Sirius 0.1."
            raise BackupTooLargeError(msg)

        try:
            envelope_bytes = backup_path.read_bytes()
        except OSError as exc:
            msg = "No se pudo leer el archivo de copia."
            raise BackupValidationError(msg) from exc

        manifest, db_bytes = self._validate_and_extract(envelope_bytes, password)
        return manifest, db_bytes, size_bytes

    def _validate_and_extract(
        self,
        envelope_bytes: bytes,
        password: str,
        *,
        expected_sha256: str | None = None,
    ) -> tuple[BackupManifest, bytes]:
        package_bytes = _decrypt_envelope(envelope_bytes, password)
        manifest_mapping, db_bytes = _read_package(package_bytes)
        manifest = _manifest_from_mapping(manifest_mapping)

        if _version_family(manifest.app_version) != _version_family(_APP_VERSION):
            msg = "La copia pertenece a una versión de Sirius incompatible con esta aplicación."
            raise BackupValidationError(msg)
        if expected_sha256 is not None and manifest.sha256 != expected_sha256:
            msg = "La copia generada no superó la validación de integridad del manifiesto."
            raise BackupValidationError(msg)
        if hashlib.sha256(db_bytes).hexdigest() != manifest.sha256:
            msg = "La copia no superó la validación de integridad de la base de datos."
            raise BackupValidationError(msg)

        with tempfile.TemporaryDirectory() as scratch_dir:
            snapshot_path = Path(scratch_dir) / "sirius.db"
            snapshot_path.write_bytes(db_bytes)
            check = _quick_check if expected_sha256 is not None else _integrity_check
            if not check(snapshot_path):
                msg = "La copia no superó la comprobación de integridad de SQLite."
                raise BackupValidationError(msg)

            try:
                real_schema_version = _read_schema_version(snapshot_path)
            except sqlite3.Error as exc:
                msg = (
                    "No se pudo determinar el esquema de la base de datos empaquetada en la copia."
                )
                raise BackupValidationError(msg) from exc
            if real_schema_version != manifest.schema_version:
                msg = (
                    "La copia declara una versión de esquema incompatible con el "
                    "contenido real de la base de datos."
                )
                raise BackupValidationError(msg)
            if real_schema_version != get_supported_schema_version():
                msg = (
                    "La copia utiliza una versión de esquema no soportada por esta "
                    "versión de Sirius."
                )
                raise BackupValidationError(msg)
        return manifest, db_bytes


def build_sqlite_backup_service(database_path: Path, backups_dir: Path) -> SQLiteBackupService:
    """Build a backup service bound to the given database and backup directory."""
    return SQLiteBackupService(database_path, backups_dir)
