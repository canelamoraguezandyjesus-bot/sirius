from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from package_snapshot import SnapshotError, capture_source, verify_snapshot


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "live checkout"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "source.txt").write_text("acreditado\n", encoding="utf-8")
    _git(repo, "add", "source.txt")
    _git(repo, "commit", "-m", "source")
    head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/main", head)
    return repo


def test_snapshot_is_distinct_and_pinned_to_captured_commit(repository: Path) -> None:
    metadata = capture_source(repository)
    snapshot = repository.parent / "private snapshot"
    _git(repository, "worktree", "add", "--detach", str(snapshot), metadata.commit)
    try:
        result = verify_snapshot(snapshot, metadata.commit)
        assert Path(result.snapshot_root) != repository.resolve()
        assert result.commit == metadata.commit
        assert _git(snapshot, "rev-parse", "HEAD") == metadata.commit
    finally:
        _git(repository, "worktree", "remove", "--force", str(snapshot))


def test_live_checkout_mutation_cannot_change_snapshot_source(repository: Path) -> None:
    metadata = capture_source(repository)
    snapshot = repository.parent / "private snapshot"
    _git(repository, "worktree", "add", "--detach", str(snapshot), metadata.commit)
    try:
        (repository / "source.txt").write_text("checkout alterado\n", encoding="utf-8")
        assert (snapshot / "source.txt").read_text(encoding="utf-8") == "acreditado\n"
        assert verify_snapshot(snapshot, metadata.commit).clean
    finally:
        _git(repository, "worktree", "remove", "--force", str(snapshot))


@pytest.mark.parametrize("untracked", [False, True])
def test_snapshot_mutation_aborts_provenance(repository: Path, untracked: bool) -> None:
    metadata = capture_source(repository)
    snapshot = repository.parent / "private snapshot"
    _git(repository, "worktree", "add", "--detach", str(snapshot), metadata.commit)
    try:
        target = snapshot / ("unexpected.txt" if untracked else "source.txt")
        target.write_text("alterado\n", encoding="utf-8")
        with pytest.raises(SnapshotError, match="snapshot"):
            verify_snapshot(snapshot, metadata.commit)
    finally:
        _git(repository, "worktree", "remove", "--force", str(snapshot))


def test_snapshot_index_discrepancy_aborts_even_when_worktree_bit_hides_it(
    repository: Path,
) -> None:
    metadata = capture_source(repository)
    snapshot = repository.parent / "private snapshot"
    _git(repository, "worktree", "add", "--detach", str(snapshot), metadata.commit)
    try:
        _git(snapshot, "update-index", "--skip-worktree", "source.txt")
        (snapshot / "source.txt").unlink()
        # Git status deliberately trusts skip-worktree and reports no difference.
        assert _git(snapshot, "status", "--porcelain") == ""
        with pytest.raises(SnapshotError, match="snapshot"):
            verify_snapshot(snapshot, metadata.commit)
    finally:
        _git(repository, "worktree", "remove", "--force", str(snapshot))


def test_worktree_removal_clears_directory_and_registration(repository: Path) -> None:
    metadata = capture_source(repository)
    snapshot = repository.parent / "private snapshot"
    _git(repository, "worktree", "add", "--detach", str(snapshot), metadata.commit)
    _git(repository, "worktree", "remove", "--force", str(snapshot))
    assert not snapshot.exists()
    assert str(snapshot) not in _git(repository, "worktree", "list", "--porcelain")
