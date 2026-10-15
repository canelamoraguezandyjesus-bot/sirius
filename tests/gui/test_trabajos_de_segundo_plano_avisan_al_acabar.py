"""Lo de segundo plano avisa al acabar también a nivel de hilo (ADR-244).

Un turno de voz espera, desde el hilo del oído, a que el juez, las huellas o el sueño
acaben lo que tienen entre manos: no recibe las señales de la ventana, así que cada
trabajo pone ``done`` al acabar, vaya bien o falle.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from sirius.presentation.dream_worker import DreamWorker
from sirius.presentation.memory_embedding_worker import MemoryEmbeddingWorker
from sirius.presentation.reply_judge_worker import ReplyJudgeWorker

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
