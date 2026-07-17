"""GUI tests for the B2b pre-bootstrap data-location screen (D-10).

No test ever touches a real folder-picker dialog or a real message box:
``choose_folder``/``confirm_onedrive``/``show_warning`` are always test
doubles, exactly like every other presentation GUI test in this repo. The
real ``WindowsDataPathValidator`` runs against ``tmp_path``, so validation
behavior stays honest without touching the real filesystem outside pytest's
sandbox.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from sirius.application.data_location import DataLocationUseCase
from sirius.infrastructure.data_path_validator import WindowsDataPathValidator
from sirius.presentation.data_location_window import (
    ACCESS_ERROR_TITLE,
    EXISTING_DATA_TITLE,
    ONEDRIVE_WARNING_TITLE,
    RECOVERY_INTRO_TEXT,
    DataLocationWindow,
)


class _FakeLocationStore:
    def __init__(self) -> None:
        self.saved: Path | None = None

    def load(self) -> Path | None:
        return self.saved

    def save(self, data_dir: Path) -> None:
        self.saved = data_dir


def _build_window(
    tmp_path: Path,
    *,
    recovery: bool = False,
    show_warning: Callable[[str, str], None] | None = None,
    confirm_onedrive: Callable[[str, str], bool] | None = None,
    choose_folder: Callable[[], str] | None = None,
) -> tuple[DataLocationWindow, DataLocationUseCase, _FakeLocationStore]:
    location_store = _FakeLocationStore()
    use_case = DataLocationUseCase(
        location_store,
        WindowsDataPathValidator(),
        default_data_dir=tmp_path / "default-data",
    )
    window = DataLocationWindow(
        use_case,
        recovery=recovery,
        show_warning=show_warning,
        confirm_onedrive=confirm_onedrive,
        choose_folder=choose_folder,
    )
    return window, use_case, location_store


@pytest.mark.gui
def test_default_path_is_shown_and_preselected(qtbot: QtBot, tmp_path: Path) -> None:
    window, use_case, _ = _build_window(tmp_path)
    qtbot.addWidget(window)

    assert window.default_path_label.text() == str(use_case.default_path)
    assert window.accept_default_button.isDefault() is True


@pytest.mark.gui
def test_accepting_the_default_path_creates_it_and_emits_resolved(
    qtbot: QtBot, tmp_path: Path
) -> None:
    window, use_case, location_store = _build_window(tmp_path)
    qtbot.addWidget(window)
    resolved_paths: list[str] = []
    window.resolved.connect(resolved_paths.append)

    window.accept_default_button.click()

    assert resolved_paths == [str(use_case.default_path)]
    assert use_case.default_path.is_dir()
    assert location_store.saved == use_case.default_path


@pytest.mark.gui
def test_choosing_a_valid_custom_folder_validates_and_resolves(
    qtbot: QtBot, tmp_path: Path
) -> None:
    custom = tmp_path / "Carpeta Personalizada"
    window, _use_case, location_store = _build_window(tmp_path, choose_folder=lambda: str(custom))
    qtbot.addWidget(window)
    resolved_paths: list[str] = []
    window.resolved.connect(resolved_paths.append)

    window.advanced_button.click()

    assert resolved_paths == [str(custom)]
    assert location_store.saved == custom


@pytest.mark.gui
def test_cancelling_the_folder_picker_does_nothing(qtbot: QtBot, tmp_path: Path) -> None:
    window, _use_case, location_store = _build_window(tmp_path, choose_folder=lambda: "")
    qtbot.addWidget(window)
    resolved_paths: list[str] = []
    window.resolved.connect(resolved_paths.append)

    window.advanced_button.click()

    assert resolved_paths == []
    assert location_store.saved is None


@pytest.mark.gui
def test_custom_folder_with_existing_sirius_data_is_blocked(qtbot: QtBot, tmp_path: Path) -> None:
    custom = tmp_path / "con-datos"
    custom.mkdir()
    (custom / "sirius.db").write_bytes(b"")
    warnings: list[tuple[str, str]] = []
    window, _use_case, location_store = _build_window(
        tmp_path,
        choose_folder=lambda: str(custom),
        show_warning=lambda title, text: warnings.append((title, text)),
    )
    qtbot.addWidget(window)
    resolved_paths: list[str] = []
    window.resolved.connect(resolved_paths.append)

    window.advanced_button.click()

    assert resolved_paths == []
    assert location_store.saved is None
    assert len(warnings) == 1
    assert warnings[0][0] == EXISTING_DATA_TITLE


@pytest.mark.gui
def test_inaccessible_custom_folder_shows_an_error_and_can_be_retried(
    qtbot: QtBot, tmp_path: Path
) -> None:
    blocked = tmp_path / "bloqueada"
    blocked.write_text("soy un archivo, no una carpeta", encoding="utf-8")
    warnings: list[tuple[str, str]] = []
    chosen = [str(blocked)]
    window, _use_case, location_store = _build_window(
        tmp_path,
        choose_folder=lambda: chosen[0],
        show_warning=lambda title, text: warnings.append((title, text)),
    )
    qtbot.addWidget(window)
    resolved_paths: list[str] = []
    window.resolved.connect(resolved_paths.append)

    window.advanced_button.click()
    assert len(warnings) == 1
    assert warnings[0][0] == ACCESS_ERROR_TITLE
    assert resolved_paths == []

    # Flow state is preserved: correcting the choice and retrying still works.
    corrected = tmp_path / "corregida"
    chosen[0] = str(corrected)
    window.advanced_button.click()

    assert resolved_paths == [str(corrected)]
    assert location_store.saved == corrected


@pytest.mark.gui
def test_onedrive_folder_warns_but_does_not_block_after_confirmation(
    qtbot: QtBot, tmp_path: Path
) -> None:
    onedrive_folder = tmp_path / "OneDrive" / "Sirius"
    onedrive_confirmations: list[tuple[str, str]] = []

    def _confirm_onedrive(title: str, text: str) -> bool:
        onedrive_confirmations.append((title, text))
        return True

    window, _use_case, location_store = _build_window(
        tmp_path, choose_folder=lambda: str(onedrive_folder), confirm_onedrive=_confirm_onedrive
    )
    qtbot.addWidget(window)
    resolved_paths: list[str] = []
    window.resolved.connect(resolved_paths.append)

    window.advanced_button.click()

    assert len(onedrive_confirmations) == 1
    assert onedrive_confirmations[0][0] == ONEDRIVE_WARNING_TITLE
    assert resolved_paths == [str(onedrive_folder)]
    assert location_store.saved == onedrive_folder


@pytest.mark.gui
def test_declining_the_onedrive_warning_does_not_resolve(qtbot: QtBot, tmp_path: Path) -> None:
    onedrive_folder = tmp_path / "OneDrive" / "Sirius"
    window, _use_case, location_store = _build_window(
        tmp_path,
        choose_folder=lambda: str(onedrive_folder),
        confirm_onedrive=lambda title, text: False,
    )
    qtbot.addWidget(window)
    resolved_paths: list[str] = []
    window.resolved.connect(resolved_paths.append)

    window.advanced_button.click()

    assert resolved_paths == []
    assert location_store.saved is None


@pytest.mark.gui
def test_recovery_mode_shows_recovery_text_and_still_resolves_the_default(
    qtbot: QtBot, tmp_path: Path
) -> None:
    window, use_case, location_store = _build_window(tmp_path, recovery=True)
    qtbot.addWidget(window)
    resolved_paths: list[str] = []
    window.resolved.connect(resolved_paths.append)

    assert window.intro_label.text() == RECOVERY_INTRO_TEXT

    window.accept_default_button.click()

    assert resolved_paths == [str(use_case.default_path)]
    assert location_store.saved == use_case.default_path
