"""Puertos de la vista del robot: la cámara y el detector de caras (pieza D de la 0.4,
ADR-262).

Sin tipos de ninguna biblioteca: los de verdad, OpenCV y MediaPipe, viven en
``sirius.adapters.vision`` y se cargan solo si están instalados, y las pruebas ponen dobles.
Lo que pasa de uno a otro es un fotograma que Sirius no abre: solo saben leerlo la cámara
que lo dio y el detector. De cada cara, Sirius sabe dónde está, si mueve la boca y si mira
a la cámara; su recorte lo lee solo quien reconoce caras, y no se guarda.

Dónde está una cara va con la izquierda y la derecha de lo que ve la cámara, tal como da
la imagen: de 0, su borde izquierdo, a 1, el derecho.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class SightUnavailable(RuntimeError):
    """La vista no puede arrancar en este ordenador: falta lo que instala la orden, o no
    carga. Dice por qué en ``reason``, para la ventana."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CameraUnavailable(RuntimeError):
    """No hay cámara, la tiene otro programa o ha dejado de dar imagen, como al
    desenchufarla. Dice por qué en ``reason``, para la ventana."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class SeenFace[Crop]:
    """Una cara en un fotograma.

    ``x`` es dónde está su centro, de 0 a 1 con la izquierda y la derecha de la cámara.
    ``talking`` dice si mueve la boca, y ``looking``, si mira a la cámara. ``crop`` es su
    recorte, que solo lee quien reconoce caras.
    """

    x: float
    talking: bool
    looking: bool
    crop: Crop


class Camera[Frame](Protocol):
    """La cámara del ordenador."""

    def open(self) -> None:
        """La abre; ``CameraUnavailable`` si no hay o la tiene otro programa."""
        ...

    def read(self) -> Frame | None:
        """El fotograma de ahora; ``None`` si está cerrada, y ``CameraUnavailable`` si ha
        dejado de dar imagen, como al desenchufarla."""
        ...

    def close(self) -> None:
        """La suelta. No falla."""
        ...


class FaceDetector[Frame, Crop](Protocol):
    """Quien busca las caras en un fotograma, en este ordenador."""

    #: Con qué las busca, para decirlo: «mediapipe».
    name: str

    def detect(self, frame: Frame) -> tuple[SeenFace[Crop], ...]:
        """Las caras de ``frame``. No guarda el fotograma ni nada de él."""
        ...


@dataclass(frozen=True, slots=True)
class SightEngines[Frame, Crop]:
    """La cámara y el detector, ya cargados."""

    camera: Camera[Frame]
    detector: FaceDetector[Frame, Crop]
