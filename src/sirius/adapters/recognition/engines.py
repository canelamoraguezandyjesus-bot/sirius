"""Reconocer de verdad, en este ordenador: InsightFace para las caras y ECAPA, de
SpeechBrain, para las voces (pieza E de la 0.4, ADR-263).

Las bibliotecas son del extra ``ojos`` y se importan al cargar, no al importar Sirius,
todas por ``import_sight_library``: sin el extra, o si una no carga, Sirius se abre igual y
cargar levanta ``RecognitionUnavailable`` diciendo qué falta. Los modelos los baja la orden
de instalar; aquí no se baja nada.

- **La cara**: el recorte que da la vista lleva la cara con margen y sus cinco puntos, los
  ojos, la nariz y las comisuras, sacados de los de MediaPipe. InsightFace la endereza con
  ellos y saca su huella con su modelo de reconocer, el ``w600k_r50`` de ``buffalo_l``:
  512 números.
- **La voz**: lo que sonó en el turno, muestras de 16 bits a 16 kHz. ECAPA saca su huella,
  192 números; con menos de ``SHORTEST_VOICE_SECONDS`` no hay huella. Se carga sin red y
  sin enlaces simbólicos, que en Windows piden permisos de administrador: lee los ficheros
  donde los dejó la orden de instalar y no escribe nada.
- ONNX Runtime, con el que va InsightFace, con su telemetría apagada antes de cargar.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sirius.adapters.audio.voice_libraries import onnx_runtime_quiet
from sirius.adapters.vision.local_sight import FaceCrop, import_sight_library
from sirius.infrastructure.local_sight_installation import (
    FACE_RECOGNITION_MODEL,
    face_recognition_model_complete,
    voice_recognition_complete,
)
from sirius.ports.local_sight import SightUnavailable
from sirius.ports.recognition import Print, RecognitionEngines, RecognitionUnavailable

#: Lo que tiene que durar lo que sonó para sacar la huella de una voz.
SHORTEST_VOICE_SECONDS = 0.5
#: A cuántas muestras por segundo llega lo que sonó.
SAMPLE_RATE = 16_000


def load_recognition_engines(
    face_models: Path, voice_model: Path
) -> RecognitionEngines[FaceCrop, bytes]:
    """InsightFace con el modelo de ``face_models`` y ECAPA con el de ``voice_model``;
    ``RecognitionUnavailable`` si falta un modelo o una biblioteca, o no carga."""
    if not face_recognition_model_complete(face_models):
        msg = "falta el modelo de reconocer caras"
        raise RecognitionUnavailable(msg)
    if not voice_recognition_complete(voice_model):
        msg = "falta el modelo de reconocer voces"
        raise RecognitionUnavailable(msg)
    try:
        return RecognitionEngines(InsightFacePrints(face_models), EcapaPrints(voice_model))
    except SightUnavailable as error:
        raise RecognitionUnavailable(error.reason) from error


class InsightFacePrints:
    """La huella de una cara, con el modelo de reconocer de InsightFace."""

    name = "insightface"

    def __init__(self, models: Path) -> None:
        onnx_runtime_quiet()
        self._numpy = import_sight_library("numpy")
        arcface = import_sight_library("insightface.model_zoo.arcface_onnx")
        self._face = import_sight_library("insightface.app.common").Face
        try:
            self._model = arcface.ArcFaceONNX(str(models / FACE_RECOGNITION_MODEL))
            self._model.prepare(-1)
        except Exception as error:
            msg = f"el modelo de reconocer caras no carga ({error})"
            raise RecognitionUnavailable(msg) from error

    def fingerprint(self, crop: FaceCrop) -> Print:
        numpy = self._numpy
        face = self._face(
            bbox=numpy.array(crop.box, dtype=numpy.float32),
            kps=numpy.array(crop.points, dtype=numpy.float32),
        )
        return _unit(self._model.get(crop.image, face).tolist())


class EcapaPrints:
    """La huella de una voz, con ECAPA de SpeechBrain."""

    name = "speechbrain-ecapa"

    def __init__(self, model: Path) -> None:
        self._torch = import_sight_library("torch")
        speaker = import_sight_library("speechbrain.inference.speaker")
        fetching = import_sight_library("speechbrain.utils.fetching")
        try:
            self._model = speaker.EncoderClassifier.from_hparams(
                source=str(model),
                savedir=str(model),
                run_opts={"device": "cpu"},
                overrides={"pretrained_path": str(model)},
                overrides_must_match=False,
                fetch_config=fetching.FetchConfig(allow_network=False),
                local_strategy=fetching.LocalStrategy.NO_LINK,
            )
        except Exception as error:
            msg = f"el modelo de reconocer voces no carga ({error})"
            raise RecognitionUnavailable(msg) from error

    def fingerprint(self, chunks: Sequence[bytes]) -> Print | None:
        samples = b"".join(chunks)
        if len(samples) // 2 < SHORTEST_VOICE_SECONDS * SAMPLE_RATE:
            return None
        torch: Any = self._torch
        wave = torch.frombuffer(bytearray(samples[: len(samples) // 2 * 2]), dtype=torch.int16)
        with torch.no_grad():
            embedding = self._model.encode_batch((wave.to(torch.float32) / 32768.0).unsqueeze(0))
        numbers = embedding.squeeze().tolist()
        return _unit(numbers) if any(numbers) else None


def _unit(numbers: Sequence[float]) -> Print:
    """``numbers`` con longitud uno."""
    length = math.sqrt(sum(number * number for number in numbers)) or 1.0
    return tuple(float(number) / length for number in numbers)
