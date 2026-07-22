"""Open, human-readable structured export adapter (SIRIUS-ARQ-0.1 S12.1).

Writes the six-item ``sirius-export-YYYYMMDD-HHMM/`` directory the
architecture defines: ``manifest.json``, ``conversation.jsonl``,
``project.json``, ``memories.jsonl``, ``decisions.jsonl`` and ``README.txt``,
all UTF-8 and readable without Sirius. Every value written here comes from
the domain entities the use case already read from the existing repositories
(read-only) — this adapter never opens SQLite, and never has access to the
API key or any other secret, so it structurally cannot leak one.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from sirius import __version__ as _APP_VERSION
from sirius.adapters.persistence.migrations import get_supported_schema_version
from sirius.domain.conversation import Message
from sirius.domain.decision import Decision
from sirius.domain.memory import Memory
from sirius.domain.project import Project, is_configured
from sirius.ports.clock import Clock
from sirius.ports.export import ExportError

_EXPORT_FORMAT = "sirius-export"
_MANIFEST_FILE = "manifest.json"
_CONVERSATION_FILE = "conversation.jsonl"
_PROJECT_FILE = "project.json"
_MEMORIES_FILE = "memories.jsonl"
_DECISIONS_FILE = "decisions.jsonl"
_README_FILE = "README.txt"
_EXPORT_FILES = (
    _MANIFEST_FILE,
    _CONVERSATION_FILE,
    _PROJECT_FILE,
    _MEMORIES_FILE,
    _DECISIONS_FILE,
    _README_FILE,
)

_README_TEXT = """Exportación estructurada de Sirius
===================================

Este directorio contiene una copia legible y abierta de tus datos en Sirius,
en el formato aprobado (SIRIUS-ARQ-0.1 S12.1). Cada archivo puede abrirse con
un editor de texto o cualquier herramienta que entienda JSON/JSONL, sin
necesidad de la aplicación Sirius.

Contenido:

- manifest.json: formato, versión de la aplicación, versión del esquema,
  fecha de la exportación y lista de los archivos incluidos.
- conversation.jsonl: la conversación completa, un mensaje por línea, en
  orden, con su rol, contenido, estado y fecha.
- project.json: el proyecto activo y su revisión vigente, o un valor vacío si
  todavía no hay ningún proyecto configurado.
- memories.jsonl: los recuerdos vigentes, uno por línea.
- decisions.jsonl: las decisiones vigentes, una por línea.

Advertencias importantes:

- Esta exportación puede contener información personal, porque refleja el
  contenido real de tu conversación, tu proyecto, tus recuerdos y tus
  decisiones. Trátala con el mismo cuidado que le darías a esos datos.
- Esta exportación NO contiene tu clave de API ni ningún otro secreto.
"""


def _json_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _json_line(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False)


def _serialize_message(message: Message) -> dict[str, Any]:
    return {
        "role": message.role.value,
        "content": message.content,
        "status": message.status.value,
        "created_at": message.created_at.isoformat(),
        "operation_id": message.operation_id,
        "identity_version": message.identity_version,
    }


def _serialize_project(project: Project | None) -> dict[str, Any] | None:
    if project is None or not is_configured(project):
        return None
    revision = project.current_revision
    assert revision is not None  # is_configured() guarantees this.
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status.value,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "completed_at": (project.completed_at.isoformat() if project.completed_at else None),
        "current_revision": {
            "version": revision.version,
            "objective": revision.objective,
            "state_summary": revision.state_summary,
            "blockers": list(revision.blockers),
            "next_step": revision.next_step,
            "created_at": revision.created_at.isoformat(),
        },
    }


def _serialize_memory(memory: Memory) -> dict[str, Any]:
    revision = memory.current_revision
    return {
        "id": memory.id,
        "status": memory.status.value,
        "subject_key": memory.subject_key,
        "project_id": memory.project_id,
        "created_at": memory.created_at.isoformat(),
        "updated_at": memory.updated_at.isoformat(),
        "current_revision": {
            "version": revision.version,
            "content": revision.content,
            "origin": revision.origin,
            "created_at": revision.created_at.isoformat(),
        },
    }


def _serialize_decision(decision: Decision) -> dict[str, Any]:
    revision = decision.current_revision
    return {
        "id": decision.id,
        "subject": decision.subject,
        "project_id": decision.project_id,
        "status": decision.status.value,
        "supersedes_decision_id": decision.supersedes_decision_id,
        "created_at": decision.created_at.isoformat(),
        "updated_at": decision.updated_at.isoformat(),
        "current_revision": {
            "version": revision.version,
            "content": revision.content,
            "created_at": revision.created_at.isoformat(),
        },
    }


def _build_manifest(created_at: datetime) -> dict[str, Any]:
    return {
        "format": _EXPORT_FORMAT,
        "app_version": _APP_VERSION,
        "schema_version": get_supported_schema_version(),
        "created_at": created_at.isoformat(),
        "files": list(_EXPORT_FILES),
    }


class FilesystemExportService:
    """Writes the S12.1 open, human-readable export to the local filesystem."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def export_structured(
        self,
        destination_dir: Path,
        *,
        messages: Sequence[Message],
        project: Project | None,
        memories: Sequence[Memory],
        decisions: Sequence[Decision],
    ) -> Path:
        created_at = self._clock.utc_now()
        export_name = f"sirius-export-{created_at.strftime('%Y%m%d-%H%M')}"
        final_dir = destination_dir / export_name
        if final_dir.exists():
            msg = f"Ya existe una exportación en '{final_dir}'; no se sobrescribe."
            raise ExportError(msg)

        destination_dir.mkdir(parents=True, exist_ok=True)
        staging_dir = Path(tempfile.mkdtemp(dir=destination_dir, prefix=".sirius-export-"))
        try:
            (staging_dir / _MANIFEST_FILE).write_text(
                _json_dumps(_build_manifest(created_at)), encoding="utf-8"
            )
            (staging_dir / _CONVERSATION_FILE).write_text(
                "".join(f"{_json_line(_serialize_message(m))}\n" for m in messages),
                encoding="utf-8",
            )
            (staging_dir / _PROJECT_FILE).write_text(
                json.dumps(_serialize_project(project), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (staging_dir / _MEMORIES_FILE).write_text(
                "".join(f"{_json_line(_serialize_memory(m))}\n" for m in memories),
                encoding="utf-8",
            )
            (staging_dir / _DECISIONS_FILE).write_text(
                "".join(f"{_json_line(_serialize_decision(d))}\n" for d in decisions),
                encoding="utf-8",
            )
            (staging_dir / _README_FILE).write_text(_README_TEXT, encoding="utf-8")
            os.replace(staging_dir, final_dir)
        except BaseException:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise
        return final_dir


def build_filesystem_export_service(clock: Clock) -> FilesystemExportService:
    """Build the production ``ExportService`` implementation."""
    return FilesystemExportService(clock)
