"""Open, human-readable structured export contract (SIRIUS-ARQ-0.1 S12.1).

Distinct from ``BackupService`` (S12.2-S12.3): the export is never encrypted,
never password-protected, and is meant to be read directly (a text editor,
``jq``, a spreadsheet) without Sirius. RNF-013 applies here too — an export
must never contain the API key or any other secret.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from sirius.domain.conversation import Message
from sirius.domain.decision import Decision
from sirius.domain.memory import Memory
from sirius.domain.project import Project


class ExportError(RuntimeError):
    """Raised when a structured export cannot be written safely."""


class ExportService(Protocol):
    """Contract implemented by the filesystem structured-export adapter."""

    def export_structured(
        self,
        destination_dir: Path,
        *,
        messages: Sequence[Message],
        project: Project | None,
        memories: Sequence[Memory],
        decisions: Sequence[Decision],
    ) -> Path:
        """Write the six-item S12.1 export under a new, timestamped directory.

        Creates ``destination_dir / "sirius-export-YYYYMMDD-HHMM"`` (the
        timestamp comes from the adapter's injected ``Clock``, never from
        ``datetime.now()`` directly) and writes ``manifest.json``,
        ``conversation.jsonl``, ``project.json``, ``memories.jsonl``,
        ``decisions.jsonl`` and ``README.txt`` inside it. Returns the created
        directory's path. Never includes the API key or any other secret.
        """
        ...
