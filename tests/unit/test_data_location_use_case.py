"""Unit tests for DataLocationUseCase (B2b, D-10).

Uses in-memory fakes for both ports so behavior is verified independently of
the filesystem and of platformdirs (those get their own dedicated tests in
``test_bootstrap_location_store.py`` and ``test_data_path_validator.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.application.data_location import DataLocationUseCase
from sirius.ports.data_location import (
    DataPathCheck,
    DataPathHasExistingInstallationError,
    DataPathInvalidError,
    LocationFileCorruptedError,
)


class _FakeLocationStore:
    def __init__(self, saved: Path | None = None) -> None:
        self._saved = saved
        self.save_calls: list[Path] = []

    def load(self) -> Path | None:
        return self._saved

    def save(self, data_dir: Path) -> None:
        self.save_calls.append(data_dir)
        self._saved = data_dir


class _CorruptedLocationStore:
    def load(self) -> Path | None:
        raise LocationFileCorruptedError("dañado")

    def save(self, data_dir: Path) -> None:
        raise AssertionError("save() must not be called after a corrupted load()")


class _FakeValidator:
    def __init__(
        self,
        *,
        installations: set[Path] | None = None,
        onedrive: set[Path] | None = None,
        missing: set[Path] | None = None,
        inaccessible: set[Path] | None = None,
    ) -> None:
        self._installations = installations or set()
        self._onedrive = onedrive or set()
        self._missing = missing or set()
        self._inaccessible = inaccessible or set()
        self.validate_calls: list[tuple[Path, bool]] = []

    def peek(self, candidate: Path) -> DataPathCheck:
        return DataPathCheck(
            path=candidate,
            has_existing_installation=candidate in self._installations,
            is_onedrive=candidate in self._onedrive,
        )

    def validate(self, candidate: Path, *, allow_create: bool) -> DataPathCheck:
        self.validate_calls.append((candidate, allow_create))
        if candidate in self._inaccessible:
            raise DataPathInvalidError(f"'{candidate}' no es accesible.")
        if candidate in self._missing and not allow_create:
            raise DataPathInvalidError(f"'{candidate}' no existe.")
        return DataPathCheck(
            path=candidate,
            has_existing_installation=candidate in self._installations,
            is_onedrive=candidate in self._onedrive,
        )


def test_resolve_proposes_the_default_path_on_a_brand_new_install(tmp_path: Path) -> None:
    default_path = tmp_path / "default"
    use_case = DataLocationUseCase(
        _FakeLocationStore(saved=None),
        _FakeValidator(missing={default_path}),
        default_data_dir=default_path,
    )

    resolution = use_case.resolve()

    assert resolution.needs_selection is True
    assert resolution.path == default_path
    assert resolution.default_path == default_path


def test_resolve_keeps_and_persists_an_existing_default_installation_silently(
    tmp_path: Path,
) -> None:
    default_path = tmp_path / "default"
    location_store = _FakeLocationStore(saved=None)
    use_case = DataLocationUseCase(
        location_store,
        _FakeValidator(installations={default_path}),
        default_data_dir=default_path,
    )

    resolution = use_case.resolve()

    assert resolution.needs_selection is False
    assert resolution.path == default_path
    assert location_store.save_calls == [default_path]


def test_resolve_loads_and_validates_a_previously_saved_custom_path(tmp_path: Path) -> None:
    custom_path = tmp_path / "custom"
    use_case = DataLocationUseCase(
        _FakeLocationStore(saved=custom_path),
        _FakeValidator(),
        default_data_dir=tmp_path / "default",
    )

    resolution = use_case.resolve()

    assert resolution.needs_selection is False
    assert resolution.path == custom_path


def test_resolve_raises_when_the_saved_path_is_no_longer_accessible(tmp_path: Path) -> None:
    custom_path = tmp_path / "ya-no-accesible"
    use_case = DataLocationUseCase(
        _FakeLocationStore(saved=custom_path),
        _FakeValidator(inaccessible={custom_path}),
        default_data_dir=tmp_path / "default",
    )

    with pytest.raises(DataPathInvalidError):
        use_case.resolve()


def test_resolve_propagates_a_corrupted_location_file_without_any_fallback(tmp_path: Path) -> None:
    use_case = DataLocationUseCase(
        _CorruptedLocationStore(),
        _FakeValidator(),
        default_data_dir=tmp_path / "default",
    )

    with pytest.raises(LocationFileCorruptedError):
        use_case.resolve()


def test_validate_candidate_blocks_a_non_default_path_with_existing_data(tmp_path: Path) -> None:
    custom_path = tmp_path / "custom-con-datos"
    location_store = _FakeLocationStore(saved=None)
    use_case = DataLocationUseCase(
        location_store,
        _FakeValidator(installations={custom_path}),
        default_data_dir=tmp_path / "default",
    )

    with pytest.raises(DataPathHasExistingInstallationError):
        use_case.validate_candidate(custom_path, is_default=False)

    assert location_store.save_calls == []


def test_validate_candidate_allows_the_default_path_even_with_existing_data(
    tmp_path: Path,
) -> None:
    default_path = tmp_path / "default"
    use_case = DataLocationUseCase(
        _FakeLocationStore(saved=None),
        _FakeValidator(installations={default_path}),
        default_data_dir=default_path,
    )

    check = use_case.validate_candidate(default_path, is_default=True)

    assert check.path == default_path


def test_confirm_persists_the_validated_check(tmp_path: Path) -> None:
    location_store = _FakeLocationStore(saved=None)
    use_case = DataLocationUseCase(
        location_store, _FakeValidator(), default_data_dir=tmp_path / "default"
    )
    check = DataPathCheck(
        path=tmp_path / "elegida", has_existing_installation=False, is_onedrive=False
    )

    use_case.confirm(check)

    assert location_store.save_calls == [tmp_path / "elegida"]


def test_validate_candidate_does_not_persist_by_itself(tmp_path: Path) -> None:
    """The window must call confirm() separately (e.g. after an OneDrive
    acknowledgement) — validate_candidate() alone must never save."""
    location_store = _FakeLocationStore(saved=None)
    use_case = DataLocationUseCase(
        location_store, _FakeValidator(), default_data_dir=tmp_path / "default"
    )

    use_case.validate_candidate(tmp_path / "elegida", is_default=False)

    assert location_store.save_calls == []
