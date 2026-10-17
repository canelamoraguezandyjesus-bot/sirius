"""Lo de segundo plano avisa al acabar también a nivel de hilo (ADR-244).

Un turno de voz espera, desde el hilo del oído, a que el juez, las huellas o el sueño
acaben lo que tienen entre manos: no recibe las señales de la ventana, así que cada
trabajo pone ``done`` al acabar, vaya bien o falle.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import shiboken6
from PySide6.QtCore import QRunnable

from sirius.application.set_criticality import CriticalityTargetKind
from sirius.domain.conversation import MessageStatus
from sirius.presentation.backup_worker import (
    CreateBackupWorker,
    RestoreBackupWorker,
    ValidateBackupWorker,
)
from sirius.presentation.conversation_worker import SendMessageWorker
from sirius.presentation.credential_validation_worker import CredentialValidationWorker
from sirius.presentation.criticality_proposal_worker import CriticalityProposalWorker
from sirius.presentation.dream_worker import DreamWorker
from sirius.presentation.export_worker import ExportWorker
from sirius.presentation.memory_embedding_worker import MemoryEmbeddingWorker
from sirius.presentation.reply_judge_worker import ReplyJudgeWorker
from sirius.presentation.studio_workers import CaptureWorker, SpeakWorker, TranscribeWorker

pytestmark = pytest.mark.gui


def _falla(*args: Any, **kwargs: Any) -> Any:
    del args, kwargs
    msg = "roto"
    raise RuntimeError(msg)


@pytest.mark.parametrize("falla", [False, True])
def test_el_juez_avisa_al_acabar(falla: bool) -> None:
    servicio = SimpleNamespace(judge_pending=_falla if falla else lambda should_stop: 0)
    trabajo = ReplyJudgeWorker(servicio)  # type: ignore[arg-type]
    assert not trabajo.done.is_set()

    trabajo.run()

    assert trabajo.done.is_set()


@pytest.mark.parametrize("falla", [False, True])
def test_las_huellas_avisan_al_acabar(falla: bool) -> None:
    servicio = SimpleNamespace(
        embed_pending=_falla if falla else lambda should_stop: 1, warm_up=lambda: None
    )
    trabajo = MemoryEmbeddingWorker(servicio)  # type: ignore[arg-type]
    assert not trabajo.done.is_set()

    trabajo.run()

    assert trabajo.done.is_set()


@pytest.mark.parametrize("falla", [False, True])
def test_el_sueno_avisa_al_acabar(falla: bool) -> None:
    servicio = SimpleNamespace(dream_pending=_falla if falla else lambda today, should_stop: 0)
    trabajo = DreamWorker(servicio, today=date(2026, 10, 15))  # type: ignore[arg-type]
    assert not trabajo.done.is_set()

    trabajo.run()

    assert trabajo.done.is_set()


@pytest.mark.parametrize("trabajo", ["juez", "sueño", "huellas"])
def test_acaban_sin_traza_aunque_ya_no_haya_ventana(trabajo: str) -> None:
    """Al cerrar Sirius con ellos en marcha, sus señales desaparecen antes de que acaben: el
    aviso final no puede pintar «Signal source has been deleted» en la consola, ni dejar
    ``done`` sin poner (ADR-253)."""
    corre: ReplyJudgeWorker | DreamWorker | MemoryEmbeddingWorker
    if trabajo == "juez":
        juez = SimpleNamespace(judge_pending=lambda should_stop: 0)
        corre = ReplyJudgeWorker(juez)  # type: ignore[arg-type]
    elif trabajo == "sueño":
        sueno = SimpleNamespace(dream_pending=lambda today, should_stop: 0)
        corre = DreamWorker(sueno, today=date(2026, 10, 17))  # type: ignore[arg-type]
    else:
        huellas = SimpleNamespace(embed_pending=lambda should_stop: 1, warm_up=lambda: None)
        corre = MemoryEmbeddingWorker(huellas)  # type: ignore[arg-type]
    shiboken6.delete(corre.signals)

    corre.run()

    assert corre.done.is_set()


def _transcribe(falla: bool) -> TranscribeWorker:
    voz = SimpleNamespace(stop_and_transcribe=_falla if falla else lambda: None)
    return TranscribeWorker(voz)  # type: ignore[arg-type]


def _di(falla: bool) -> SpeakWorker:
    voz = SimpleNamespace(speak=_falla if falla else lambda text, status, read_code: None)
    return SpeakWorker(voz, "Hola.", MessageStatus.COMPLETED)  # type: ignore[arg-type]


def _captura(falla: bool) -> CaptureWorker:
    orden: Callable[[], Any] = _falla if falla else lambda: None
    return CaptureWorker(orden)


@pytest.mark.parametrize("falla", [False, True])
@pytest.mark.parametrize("trabajador", [_transcribe, _di, _captura])
def test_los_de_model_studio_acaban_sin_traza_aunque_ya_no_haya_ventana(
    trabajador: Callable[[bool], QRunnable], falla: bool
) -> None:
    """Los de Model Studio, igual: vaya bien o falle, si la ventana ya no está, su aviso se
    pierde sin pintar una traza (ADR-253)."""
    corre = trabajador(falla)
    shiboken6.delete(corre.signals)  # type: ignore[attr-defined]

    corre.run()


def _crea_copia(falla: bool) -> QRunnable:
    copia = SimpleNamespace(create_backup=_falla if falla else lambda password: "hecha")
    return CreateBackupWorker(copia, "clave")  # type: ignore[arg-type]


def _valida_copia(falla: bool) -> QRunnable:
    copia = SimpleNamespace(validate_backup=_falla if falla else lambda path, password: "válida")
    return ValidateBackupWorker(copia, Path("copia.zip"), "clave")  # type: ignore[arg-type]


def _restaura_copia(falla: bool) -> QRunnable:
    copia = SimpleNamespace(
        restore_backup=_falla if falla else lambda path, password, confirmed: "restaurada"
    )
    return RestoreBackupWorker(copia, Path("copia.zip"), "clave")  # type: ignore[arg-type]


def _envia(falla: bool) -> QRunnable:
    hecho = SimpleNamespace(outcome=SimpleNamespace(value="completed"))
    charla = SimpleNamespace(
        send_message=_falla
        if falla
        else lambda text, operation_id, on_delta, extra_instructions: hecho
    )
    return SendMessageWorker(charla, "Hola.", "op-1")  # type: ignore[arg-type]


def _valida_clave(falla: bool) -> QRunnable:
    clave = SimpleNamespace(validate_and_save=_falla if falla else lambda credential, model: None)
    return CredentialValidationWorker(clave, "sk-prueba", "modelo")  # type: ignore[arg-type]


def _propone_criticidad(falla: bool) -> QRunnable:
    propuesta = SimpleNamespace(propose=_falla if falla else lambda kind, item_id: None)
    return CriticalityProposalWorker(
        propuesta,  # type: ignore[arg-type]
        next(iter(CriticalityTargetKind)),
        1,
    )


def _exporta(falla: bool) -> QRunnable:
    exportacion = SimpleNamespace(
        export_structured=_falla if falla else lambda destination: Path("export")
    )
    return ExportWorker(exportacion, Path("destino"))  # type: ignore[arg-type]


@pytest.mark.parametrize("falla", [False, True])
@pytest.mark.parametrize(
    "trabajador",
    [
        _crea_copia,
        _valida_copia,
        _restaura_copia,
        _envia,
        _valida_clave,
        _propone_criticidad,
        _exporta,
    ],
)
def test_los_demas_trabajadores_acaban_sin_traza_aunque_ya_no_haya_ventana(
    trabajador: Callable[[bool], QRunnable], falla: bool
) -> None:
    """Los demás trabajadores de la ventana, igual: vaya bien o falle, si la ventana ya no
    está, su aviso se pierde sin pintar una traza (ADR-253)."""
    corre = trabajador(falla)
    shiboken6.delete(corre.signals)  # type: ignore[attr-defined]

    corre.run()
