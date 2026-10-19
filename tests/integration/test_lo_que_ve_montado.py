"""Lo que recuerda haber visto, montado como en producción (pieza G de la 0.4, ADR-265): con
una cámara, un detector y unos reconocedores de mentira, quitar el permiso quita su nombre
de lo apuntado en la base en el acto, antes de que nadie lo lea."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.recognition import FACE_SAMPLES, EnrollmentStep
from sirius.composition_root import build_conversation_dependencies
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.embeddings import EmbeddingError
from sirius.ports.local_sight import SeenFace, SightEngines
from sirius.ports.recognition import Print, RecognitionEngines

pytestmark = pytest.mark.integration

_HUELLAS: dict[str, Print] = {"marta": (1.0, 0.0, 0.0), "pepe": (0.0, 1.0, 0.0)}
_SEIS = datetime(2026, 10, 19, 18, 0, tzinfo=UTC)


class _SinHuellas:
    model_name = "sin-huellas"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        del texts
        raise EmbeddingError("sin huellas")


class _Camara:
    def open(self) -> None:
        return None

    def read(self) -> str:
        return "fotograma"

    def close(self) -> None:
        return None


@dataclass
class _Detector:
    name: str = "mediapipe"
    caras: list[tuple[SeenFace[str], ...]] = field(default_factory=list)

    def detect(self, frame: str) -> tuple[SeenFace[str], ...]:
        del frame
        return self.caras.pop(0) if self.caras else ()


class _Caras:
    name = "insightface"

    def fingerprint(self, crop: str) -> Print:
        return _HUELLAS[crop]


class _Voces:
    name = "speechbrain-ecapa"

    def fingerprint(self, chunks: Sequence[str]) -> Print | None:
        return _HUELLAS["".join(chunks)]


class _Reloj:
    def __init__(self) -> None:
        self.ahora = 100.0

    def __call__(self) -> float:
        return self.ahora


def _apuntado(base: Path) -> list[tuple[str, str | None]]:
    with closing(sqlite3.connect(base)) as conexion:
        filas = conexion.execute("SELECT change, person FROM sight_log ORDER BY id").fetchall()
    return [(str(cambio), persona) for cambio, persona in filas]


def test_quitar_el_permiso_quita_su_nombre_de_lo_apuntado_en_el_acto(tmp_path: Path) -> None:
    rutas = resolve_paths()
    initialize_persistence(rutas)
    base = rutas.data_dir / "sirius.db"
    reloj, detector = _Reloj(), _Detector()
    deps = build_conversation_dependencies(
        base,
        tmp_path / "copias",
        secret_store=FakeSecretStore(),
        text_embedder=_SinHuellas(),
        sight_engines=lambda: SightEngines(_Camara(), detector),
        recognition_engines=lambda: RecognitionEngines(_Caras(), _Voces()),
        listening_clock=reloj,
        wall_clock=lambda: _SEIS + timedelta(seconds=reloj.ahora),
    )
    deps.recognition.begin("Marta")
    for _ in range(FACE_SAMPLES):
        deps.recognition.take_face("marta")
    deps.recognition.take_voice(["marta"])
    assert deps.recognition.enrollment.step is EnrollmentStep.DONE
    assert deps.local_sight.start() == ""
    for _ in range(40):
        detector.caras.append((SeenFace(0.5, False, False, "marta"),))
        deps.local_sight.look()
        reloj.ahora += 0.1
    assert _apuntado(base) == [("there", "Marta")]

    assert deps.recognition.forget("Marta")

    assert _apuntado(base) == [("there", None)]
    deps.close_database_connections()
