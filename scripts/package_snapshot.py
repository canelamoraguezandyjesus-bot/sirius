"""Procedencia comprobable del snapshot usado para construir B13.

PowerShell conserva la orquestacion del ``git worktree`` y de su limpieza. Este
modulo concentra las comprobaciones de Git para que el controlador y las pruebas
ejecuten exactamente la misma logica.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


class SnapshotError(ValueError):
    """No puede demostrarse la procedencia limpia del checkout o snapshot."""


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    commit: str
    commit_short: str
    branch: str
    origin_main: str
    descends_from_origin_main: bool


@dataclass(frozen=True, slots=True)
class SnapshotVerification:
    snapshot_root: str
    commit: str
    clean: bool = True


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "sin detalle"
        raise SnapshotError(f"git {' '.join(args)} fallo: {detail}")
    return result


def capture_source(repo: Path) -> SourceMetadata:
    """Captura un commit acreditable solo desde un checkout completamente limpio."""

    root = repo.resolve()
    status = _git(root, "status", "--porcelain", "--untracked-files=all").stdout.strip()
    if status:
        raise SnapshotError(f"el checkout original no esta limpio:\n{status}")

    commit = _git(root, "rev-parse", "HEAD").stdout.strip()
    commit_short = _git(root, "rev-parse", "--short", commit).stdout.strip()
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    origin = _git(root, "rev-parse", "--verify", "refs/remotes/origin/main", check=False)
    if origin.returncode != 0:
        raise SnapshotError("no existe refs/remotes/origin/main; ejecuta git fetch origin")
    origin_main = origin.stdout.strip()
    ancestor = _git(root, "merge-base", "--is-ancestor", origin_main, commit, check=False)
    if ancestor.returncode not in (0, 1):
        raise SnapshotError("no se pudo comparar el commit con origin/main")
    return SourceMetadata(commit, commit_short, branch, origin_main, ancestor.returncode == 0)


def _tree_entries(repo: Path, commit: str) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for line in _git(repo, "ls-tree", "-r", "--full-tree", commit).stdout.splitlines():
        metadata, path = line.split("\t", 1)
        mode, _kind, object_id = metadata.split(" ", 2)
        entries.append((mode, object_id, path))
    return entries


def _index_entries(repo: Path) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    for line in _git(repo, "ls-files", "--stage").stdout.splitlines():
        metadata, path = line.split("\t", 1)
        mode, object_id, stage = metadata.split(" ", 2)
        if stage != "0":
            raise SnapshotError(f"el indice del snapshot contiene una etapa no resuelta: {path}")
        entries.append((mode, object_id, path))
    return entries


def _verify_worktree_blobs(repo: Path, entries: list[tuple[str, str, str]]) -> None:
    for mode, expected_object, relative in entries:
        if mode == "160000":
            raise SnapshotError(f"no se admite un submodulo en el snapshot: {relative}")
        candidate = repo / relative
        if not candidate.exists():
            raise SnapshotError(f"falta un archivo rastreado en el snapshot: {relative}")
        actual = _git(repo, "hash-object", f"--path={relative}", "--", relative).stdout.strip()
        if actual != expected_object:
            raise SnapshotError(f"cambio un archivo rastreado en el snapshot: {relative}")


def verify_snapshot(snapshot: Path, expected_commit: str) -> SnapshotVerification:
    """Exige HEAD exacto y ningún cambio rastreado o no rastreado en el snapshot."""

    root = snapshot.resolve()
    actual = _git(root, "rev-parse", "HEAD").stdout.strip()
    expected = _git(root, "rev-parse", expected_commit).stdout.strip()
    if actual != expected:
        raise SnapshotError(f"el snapshot apunta a {actual}, no al commit capturado {expected}")

    index_entries = _index_entries(root)
    if index_entries != _tree_entries(root, expected):
        raise SnapshotError("el indice del snapshot no contiene exactamente el arbol del commit")
    _verify_worktree_blobs(root, index_entries)

    status = _git(root, "status", "--porcelain", "--untracked-files=all").stdout.strip()
    if status:
        raise SnapshotError(f"el snapshot cambio durante la construccion:\n{status}")
    return SnapshotVerification(str(root), expected)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    result: SourceMetadata | SnapshotVerification
    try:
        if len(args) == 2 and args[0] == "capture":
            result = capture_source(Path(args[1]))
        elif len(args) == 3 and args[0] == "verify":
            result = verify_snapshot(Path(args[1]), args[2])
        else:
            raise SnapshotError("uso: capture <checkout> | verify <snapshot> <commit>")
    except SnapshotError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    payload = {"ok": True, **asdict(result)}
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
