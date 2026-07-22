"""Unit tests for the packaged/development resource resolver.

SIRIUS-PKG-PREP-001 (A-03/ATD-011 groundwork): a packaged executable (Nuitka
or PyInstaller) has no repository root to resolve ``alembic.ini`` and
``migrations/`` against, so ``upgrade_to_head`` and
``get_supported_schema_version`` must locate those resources next to the
executable instead. These tests simulate that frozen mode without a real
build.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from sirius.adapters.persistence.migrations import _REPO_ROOT, _resource_root


def test_resource_root_is_the_repository_root_in_development() -> None:
    assert _resource_root() == _REPO_ROOT
    assert (_REPO_ROOT / "alembic.ini").is_file()
    assert (_REPO_ROOT / "migrations").is_dir()


def test_resource_root_is_next_to_the_executable_when_pyinstaller_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    (tmp_path / "migrations").mkdir()
    fake_executable = tmp_path / "sirius.exe"

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_executable))

    resolved = _resource_root()

    assert resolved == tmp_path
    assert resolved != _REPO_ROOT
    assert (resolved / "alembic.ini").is_file()
    assert (resolved / "migrations").is_dir()


def test_resource_root_is_next_to_the_executable_when_nuitka_compiled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    (tmp_path / "migrations").mkdir()
    fake_executable = tmp_path / "sirius"

    # Nuitka does not set ``sys.__compiled__``; it injects ``__compiled__`` as
    # a global of the compiled ``__main__`` module, so the fake must live
    # there (see nuitka/PythonVersions.py's ``isRunningInInterpreter``).
    main_module = sys.modules["__main__"]
    monkeypatch.setattr(main_module, "__compiled__", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_executable))

    resolved = _resource_root()

    assert resolved == tmp_path
    assert resolved != _REPO_ROOT
