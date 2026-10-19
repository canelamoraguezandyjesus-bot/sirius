"""Lo que la vista del robot necesita instalado en este ordenador (pieza D de la 0.4,
ADR-262).

Las bibliotecas van en el extra ``ojos`` de ``pyproject.toml``: MediaPipe, que trae su
OpenCV. El modelo de las caras, el ``face_landmarker.task`` de MediaPipe, va en
``modelos/ojos`` de la carpeta de datos de siempre, como los de la voz, y lo baja la misma
orden que instala la voz, con el extra ``ojos``. Sin él, Sirius no abre la cámara: dice que
no puede ver, con la orden, y sigue oyendo y hablando.

Aquí no se baja nada: solo se mira qué hay. Lo único que baja el modelo es la orden de
instalar, ``sirius.install_local_voice``.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from sirius.infrastructure.paths import resolve_paths

#: La orden que instala la voz y la vista, tal como se pega en PowerShell en la carpeta de
#: Sirius, con ``--link-mode=copy`` como toda orden de uv que se le enseña (incidencia #696).
SIGHT_INSTALL_COMMAND = "uv run --link-mode=copy --extra voz --extra ojos sirius-instala-la-voz"
#: Las distribuciones que pide el extra ``ojos``; una prueba mira que sean esas.
SIGHT_DISTRIBUTIONS = ("mediapipe",)
#: El modelo de las caras de MediaPipe: detecta las caras, da sus puntos y cómo tienen la
#: boca y los ojos.
FACE_MODEL_FILE = "face_landmarker.task"
#: De dónde se baja: la versión 1, fija, de los modelos de MediaPipe.
FACE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/"
    "float16/1/face_landmarker.task"
)
#: Su huella, para saber que se ha bajado entero y es ese.
FACE_MODEL_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
#: Lo que lleva dentro, que es un zip: el detector, los puntos, la boca y los ojos, y con
#: qué se sabe hacia dónde gira la cabeza.
FACE_MODEL_MEMBERS = (
    "face_detector.tflite",
    "face_landmarks_detector.tflite",
    "face_blendshapes.tflite",
    "geometry_pipeline_metadata_landmarks.binarypb",
)


def sight_models_dir() -> Path:
    """La carpeta de los modelos de la vista, en la carpeta de datos por defecto."""
    return resolve_paths().data_dir / "modelos" / "ojos"


def face_model_path(models_dir: Path | None = None) -> Path:
    """Dónde va el modelo de las caras."""
    base = models_dir if models_dir is not None else sight_models_dir()
    return base / FACE_MODEL_FILE


def face_model_complete(path: Path) -> bool:
    """Si ``path`` es el modelo de las caras entero: un zip con lo que lleva dentro."""
    if not path.is_file() or not zipfile.is_zipfile(path):
        return False
    with zipfile.ZipFile(path) as bundle:
        names = set(bundle.namelist())
    return all(member in names for member in FACE_MODEL_MEMBERS)
