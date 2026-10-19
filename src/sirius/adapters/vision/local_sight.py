"""La vista de verdad: la cámara con OpenCV y las caras con MediaPipe, en este ordenador
(pieza D de la 0.4, ADR-262).

Las bibliotecas son del extra ``ojos`` y se importan al cargar la vista, no al importar
Sirius, y todas por ``import_sight_library``: sin el extra, o si una no carga, Sirius se
importa igual y cargar la vista levanta ``SightUnavailable`` diciendo qué falta. El modelo
de las caras, el ``face_landmarker.task`` de MediaPipe, lo baja la orden de instalar a la
carpeta de los modelos; aquí no se baja nada.

- **La cámara** es la primera del ordenador, con DirectShow en Windows, que abre la
  cámara del portátil sin esperar. Si no hay, o la tiene otro programa, no se abre; si
  deja de dar imagen diez veces seguidas, como al desenchufarla, lo dice.
- **Las caras**: MediaPipe da de cada una sus puntos, cómo tiene la boca y los ojos, y
  dónde está la cabeza y hacia dónde apunta. Dónde está es el centro de sus puntos, con la
  izquierda y la derecha de la imagen. Mueve la boca si lo abierta que la tiene ha cambiado
  más de ``TALKING_SPREAD`` en el último segundo, siguiendo cada cara por dónde está.
- **Si le mira**: adonde mira es adonde apunta la cabeza más lo que se le van los ojos, y
  se compara con la dirección de esa cara a la cámara, no con el frente: quien está a un
  lado le mira girando la cabeza, y quien gira la cabeza puede mirarle con los ojos. Le
  mira si eso no se aparta más de ``LOOKING_ASIDE_DEGREES`` a un lado ni más de
  ``LOOKING_UP_DEGREES`` hacia arriba, y hacia abajo hasta ``LOOKING_DOWN_DEGREES``,
  porque Sirius está en la pantalla, debajo de la cámara.
- **El recorte** de cada cara es una copia de su trozo del fotograma, para quien reconoce
  caras; el fotograma no se queda en ningún sitio.
"""

from __future__ import annotations

import importlib
import math
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sirius.infrastructure.local_sight_installation import face_model_complete
from sirius.ports.local_sight import CameraUnavailable, SeenFace, SightEngines, SightUnavailable

#: Con qué ve: el detector de caras y lo que lee la cámara.
TOOLS = ("mediapipe", "opencv")
#: Cuántas lecturas seguidas sin imagen dan la cámara por perdida.
FAILURES_TO_GIVE_UP = 10
#: Cuántas caras busca a la vez.
MOST_FACES = 4
#: Lo que tiene que variar la boca en el último segundo para que hable, de 0 a 1.
TALKING_SPREAD = 0.08
#: Cuánto recuerda de cada boca, en segundos.
MOUTH_MEMORY_SECONDS = 1.0
#: Lo que se van los ojos, en grados, cuando MediaPipe dice que miran del todo a un lado,
#: arriba o abajo: así cuadra con una cara que mira a la cámara con la cabeza girada.
EYE_DEGREES = 30.0
#: Lo que puede apartarse a un lado lo que mira, en grados, mirando todavía a Sirius.
LOOKING_ASIDE_DEGREES = 20.0
#: Y hacia arriba de la cámara.
LOOKING_UP_DEGREES = 15.0
#: Y hacia abajo: Sirius está en la pantalla, por debajo de la cámara.
LOOKING_DOWN_DEGREES = 35.0
#: Lo lejos que puede estar una cara de la del fotograma anterior para ser la misma.
SAME_FACE_DISTANCE = 0.15

#: Lo que dice MediaPipe de los ojos que los lleva hacia la derecha de la imagen, y lo que
#: los lleva hacia la izquierda: a un lado de la cara es ``Out`` y hacia la nariz, ``In``.
_EYES_TO_IMAGE_RIGHT = ("eyeLookOutLeft", "eyeLookInRight")
_EYES_TO_IMAGE_LEFT = ("eyeLookInLeft", "eyeLookOutRight")
#: Y lo que los lleva arriba y abajo.
_EYES_UP = ("eyeLookUpLeft", "eyeLookUpRight")
_EYES_DOWN = ("eyeLookDownLeft", "eyeLookDownRight")


def import_sight_library(module: str) -> Any:
    """Una biblioteca del extra ``ojos``; si no carga, falle como falle, ``SightUnavailable``."""
    try:
        return importlib.import_module(module)
    except Exception as error:
        raise SightUnavailable(f"{module} no carga ({error})") from error


def load_sight_engines(model: Path, *, camera_index: int = 0) -> SightEngines[Any, Any]:
    """La cámara y el detector de caras, con el modelo de ``model``; ``SightUnavailable``
    si falta el modelo o una biblioteca."""
    if not face_model_complete(model):
        msg = "falta el modelo de las caras"
        raise SightUnavailable(msg)
    return SightEngines(OpenCvCamera(camera_index), MediaPipeFaces(model))


class OpenCvCamera:
    """La cámara del ordenador, con OpenCV. Da cada fotograma como lo da OpenCV."""

    def __init__(self, index: int = 0) -> None:
        self._index = index
        self._capture: Any = None
        self._failures = 0

    def open(self) -> None:
        cv2 = import_sight_library("cv2")
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        capture = cv2.VideoCapture(self._index, backend)
        if not capture.isOpened():
            capture.release()
            msg = "no hay cámara, o la tiene otro programa"
            raise CameraUnavailable(msg)
        self._capture = capture
        self._failures = 0

    def read(self) -> Any:
        capture = self._capture
        if capture is None:
            return None
        ok, frame = capture.read()
        if not ok or frame is None:
            self._failures += 1
            if self._failures >= FAILURES_TO_GIVE_UP:
                msg = "la cámara ha dejado de dar imagen"
                raise CameraUnavailable(msg)
            return None
        self._failures = 0
        return frame

    def close(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            try:
                capture.release()
            except Exception:  # soltarla no falla: si ya no está, no hay nada que soltar
                return


@dataclass(slots=True)
class _Mouth:
    """Una cara seguida de fotograma en fotograma: dónde estaba y lo abierta que tenía la
    boca, con su momento, el último segundo."""

    x: float
    openings: deque[tuple[float, float]] = field(default_factory=deque)


class MediaPipeFaces:
    """El detector de caras, con el Face Landmarker de MediaPipe, en modo de vídeo."""

    name = "mediapipe"

    def __init__(self, model: Path, *, clock: Any = time.monotonic) -> None:
        self._clock = clock
        self._cv2 = import_sight_library("cv2")
        self._mediapipe = import_sight_library("mediapipe")
        tasks = import_sight_library("mediapipe.tasks.python")
        vision = import_sight_library("mediapipe.tasks.python.vision")
        options = vision.FaceLandmarkerOptions(
            base_options=tasks.BaseOptions(model_asset_path=str(model)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=MOST_FACES,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        try:
            self._landmarker = vision.FaceLandmarker.create_from_options(options)
        except Exception as error:
            raise SightUnavailable(f"el modelo de las caras no carga ({error})") from error
        self._last_ms = 0
        self._mouths: list[_Mouth] = []

    def detect(self, frame: Any) -> tuple[SeenFace[Any], ...]:
        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        image = self._mediapipe.Image(image_format=self._mediapipe.ImageFormat.SRGB, data=rgb)
        now = self._clock()
        # El modo de vídeo pide momentos que siempre crezcan, en milisegundos.
        moment = max(self._last_ms + 1, int(now * 1000))
        self._last_ms = moment
        result = self._landmarker.detect_for_video(image, moment)
        height, width = frame.shape[:2]
        mouths: list[_Mouth] = []
        faces: list[SeenFace[Any]] = []
        for index, points in enumerate(result.face_landmarks):
            xs = [point.x for point in points]
            ys = [point.y for point in points]
            x = sum(xs) / len(xs)
            shapes = _shapes(result.face_blendshapes, index)
            mouth = self._follow(x, mouths)
            mouth.openings.append((now, shapes.get("jawOpen", 0.0)))
            while mouth.openings and now - mouth.openings[0][0] > MOUTH_MEMORY_SECONDS:
                mouth.openings.popleft()
            opened = [opening for _, opening in mouth.openings]
            faces.append(
                SeenFace(
                    x=x,
                    talking=max(opened) - min(opened) > TALKING_SPREAD,
                    looking=_looking(result.facial_transformation_matrixes, index, shapes),
                    crop=_crop(frame, xs, ys, width, height),
                )
            )
        self._mouths = mouths
        return tuple(faces)

    def _follow(self, x: float, taken: list[_Mouth]) -> _Mouth:
        """La boca de la cara que estaba más cerca de ``x``, o una nueva."""
        near = [
            mouth
            for mouth in self._mouths
            if mouth not in taken and abs(mouth.x - x) <= SAME_FACE_DISTANCE
        ]
        mouth = min(near, key=lambda m: abs(m.x - x)) if near else _Mouth(x)
        mouth.x = x
        taken.append(mouth)
        return mouth


def _shapes(blendshapes: Any, index: int) -> dict[str, float]:
    """Lo que dice MediaPipe de la cara ``index``: cómo tiene la boca y los ojos, de 0 a 1."""
    if not blendshapes or index >= len(blendshapes):
        return {}
    return {shape.category_name: float(shape.score) for shape in blendshapes[index]}


def _looking(matrixes: Any, index: int, shapes: dict[str, float]) -> bool:
    """Si la cara ``index`` mira a Sirius: adonde apunta la cabeza, más lo que se le van los
    ojos, comparado con la dirección de esa cara a la cámara.

    La matriz de MediaPipe lleva la cabeza a la cámara: su tercera columna es hacia dónde
    apunta la cara, y la cuarta, dónde está, en centímetros, con la x a la derecha de la
    imagen, la y hacia arriba y la cámara mirando hacia -z.
    """
    if not matrixes or index >= len(matrixes):
        return False
    matrix = matrixes[index]
    ahead = [float(matrix[row][2]) for row in range(3)]
    where = [float(matrix[row][3]) for row in range(3)]
    distance = math.hypot(*where)
    if distance == 0:
        return False
    to_camera = [-value / distance for value in where]
    aside = (
        _side_degrees(ahead)
        - _side_degrees(to_camera)
        + EYE_DEGREES * _eyes(shapes, _EYES_TO_IMAGE_RIGHT, _EYES_TO_IMAGE_LEFT)
    )
    down = (
        _down_degrees(ahead)
        - _down_degrees(to_camera)
        - EYE_DEGREES * _eyes(shapes, _EYES_UP, _EYES_DOWN)
    )
    return (
        abs(aside) <= LOOKING_ASIDE_DEGREES and -LOOKING_UP_DEGREES <= down <= LOOKING_DOWN_DEGREES
    )


def _side_degrees(direction: list[float]) -> float:
    """Lo que ``direction`` se va a la derecha de la imagen, en grados."""
    return math.degrees(math.atan2(direction[0], direction[2]))


def _down_degrees(direction: list[float]) -> float:
    """Lo que ``direction`` va hacia abajo, en grados."""
    return math.degrees(math.asin(max(-1.0, min(1.0, -direction[1]))))


def _eyes(shapes: dict[str, float], toward: tuple[str, str], away: tuple[str, str]) -> float:
    """Lo que se van los dos ojos hacia ``toward`` y no hacia ``away``, de -1 a 1."""
    return (
        sum(shapes.get(name, 0.0) for name in toward) - sum(shapes.get(n, 0.0) for n in away)
    ) / 2


def _crop(frame: Any, xs: list[float], ys: list[float], width: int, height: int) -> Any:
    """Una copia del trozo del fotograma donde está la cara."""
    left = max(int(min(xs) * width), 0)
    right = min(int(max(xs) * width) + 1, width)
    top = max(int(min(ys) * height), 0)
    bottom = min(int(max(ys) * height) + 1, height)
    return frame[top:bottom, left:right].copy()
