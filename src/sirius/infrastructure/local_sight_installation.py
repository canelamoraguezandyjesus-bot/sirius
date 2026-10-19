"""Lo que la vista del robot necesita instalado en este ordenador (piezas D y E de la 0.4,
ADR-262 y ADR-263).

Las bibliotecas van en el extra ``ojos`` de ``pyproject.toml``: MediaPipe, que trae su
OpenCV; InsightFace, para reconocer caras; y SpeechBrain, para reconocer voces con ECAPA.
Los modelos van en ``modelos/ojos`` de la carpeta de datos de siempre, como los de la voz,
y los baja la misma orden que instala la voz, con el extra ``ojos``: el de las caras de
MediaPipe, el de reconocer caras de InsightFace y ECAPA. Sin el de las caras, Sirius no
abre la cámara: dice que no puede ver, con la orden, y sigue oyendo y hablando. Sin los de
reconocer, ve y no reconoce a nadie: todos son «sin identificar».

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
SIGHT_DISTRIBUTIONS = ("mediapipe", "insightface", "speechbrain")
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


# --- Reconocer a quien dé permiso (pieza E de la 0.4, ADR-263) ---------------------------

#: El paquete de modelos de InsightFace de donde sale el de reconocer caras: ``buffalo_l``,
#: de la versión 0.7 de sus modelos, fija. Trae más de lo que se usa; de él se sacan solo
#: el de reconocer caras y el de la edad, y el paquete se borra.
FACE_RECOGNITION_PACK_URL = (
    "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
)
#: Su huella, para saber que se ha bajado entero y es ese.
FACE_RECOGNITION_PACK_SHA256 = "80ffe37d8a5940d59a7384c201a2a38d4741f2f3c51eef46ebb28218a7b0ca2f"
#: El modelo de reconocer caras de InsightFace: de una cara enderezada, su huella.
FACE_RECOGNITION_MODEL = "w600k_r50.onnx"
#: El de la edad, para la pieza F.
AGE_MODEL = "genderage.onnx"
#: Lo que se saca del paquete.
FACE_RECOGNITION_FILES = (FACE_RECOGNITION_MODEL, AGE_MODEL)
#: De dónde se baja cada fichero de ECAPA: el modelo de SpeechBrain entrenado con
#: VoxCeleb, en Hugging Face, fichero a fichero, como la voz de personaje.
VOICE_RECOGNITION_URL = (
    "https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb/resolve/main/{name}?download=true"
)
#: Lo que ECAPA lee de su carpeta.
VOICE_RECOGNITION_FILES = (
    "hyperparams.yaml",
    "embedding_model.ckpt",
    "mean_var_norm_emb.ckpt",
    "classifier.ckpt",
    "label_encoder.txt",
)


def face_recognition_dir(models_dir: Path | None = None) -> Path:
    """Dónde van los modelos de InsightFace."""
    base = models_dir if models_dir is not None else sight_models_dir()
    return base / "insightface"


def voice_recognition_dir(models_dir: Path | None = None) -> Path:
    """Dónde va ECAPA."""
    base = models_dir if models_dir is not None else sight_models_dir()
    return base / "ecapa"


def face_recognition_complete(folder: Path) -> bool:
    """Si ``folder`` tiene los modelos de InsightFace, sin ninguno vacío."""
    return _all_there(folder, FACE_RECOGNITION_FILES)


def voice_recognition_complete(folder: Path) -> bool:
    """Si ``folder`` tiene todo lo de ECAPA, sin ningún fichero vacío."""
    return _all_there(folder, VOICE_RECOGNITION_FILES)


def _all_there(folder: Path, names: tuple[str, ...]) -> bool:
    return all((folder / name).is_file() and (folder / name).stat().st_size > 0 for name in names)
