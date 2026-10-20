"""La edad de verdad, en este ordenador: el modelo de la edad de InsightFace (pieza F de la
0.4, ADR-264).

La biblioteca es del extra ``ojos`` y se importa al cargar, no al importar Sirius, por
``import_sight_library``: sin el extra, o si no carga, Sirius se abre igual y cargar
levanta ``AgeUnavailable`` diciendo qué falta. El modelo, el ``genderage`` de
``buffalo_l``, lo deja la orden de instalar junto al de reconocer caras (ADR-263); aquí no
se baja nada.

- **La edad**: el recorte que da la vista lleva la cara con margen y su caja. InsightFace
  la escala a su medida y da la edad que aparenta, en años. Da también si parece hombre o
  mujer, y eso se tira sin mirarlo.
- **Si se lee segura**: no, si la cara es pequeña, porque está lejos: el modelo mira cada
  cara a ``SMALLEST_SURE_FACE`` píxeles, y una más pequeña la tiene que agrandar; ni si no
  está de frente: la nariz se aparta del medio de los ojos más de ``MOST_TURNED`` de lo que
  hay de un ojo a otro, unos 27 grados de giro.
"""

from __future__ import annotations

from pathlib import Path

from sirius.adapters.audio.voice_libraries import onnx_runtime_quiet
from sirius.adapters.vision.local_sight import FaceCrop, import_sight_library
from sirius.infrastructure.local_sight_installation import AGE_MODEL, age_model_complete
from sirius.ports.age import AgeReading, AgeUnavailable
from sirius.ports.local_sight import SightUnavailable

#: El lado mayor de una cara, en píxeles, desde el que su edad se lee segura: el modelo de
#: la edad mira cada cara a 64 píxeles, los 96 de su entrada con margen, y una más pequeña
#: la agranda.
SMALLEST_SURE_FACE = 64.0
#: Lo más que puede apartarse la nariz del medio de los ojos, por lo que hay de un ojo a
#: otro, con la cara de frente: unos 27 grados de giro.
MOST_TURNED = 0.25


def load_age_estimator(face_models: Path) -> InsightFaceAges:
    """El modelo de la edad de InsightFace, de ``face_models``; ``AgeUnavailable`` si falta
    el modelo o la biblioteca, o no carga."""
    if not age_model_complete(face_models):
        msg = "falta el modelo de la edad"
        raise AgeUnavailable(msg)
    try:
        return InsightFaceAges(face_models)
    except SightUnavailable as error:
        raise AgeUnavailable(error.reason) from error


class InsightFaceAges:
    """La edad que aparenta una cara, con el modelo de la edad de InsightFace."""

    name = "insightface"

    def __init__(self, models: Path) -> None:
        onnx_runtime_quiet()
        self._numpy = import_sight_library("numpy")
        attribute = import_sight_library("insightface.model_zoo.attribute")
        self._face = import_sight_library("insightface.app.common").Face
        try:
            self._model = attribute.Attribute(model_file=str(models / AGE_MODEL))
            self._model.prepare(-1)
        except Exception as error:
            msg = f"el modelo de la edad no carga ({error})"
            raise AgeUnavailable(msg) from error

    def estimate(self, crop: FaceCrop) -> AgeReading:
        numpy = self._numpy
        face = self._face(bbox=numpy.array(crop.box, dtype=numpy.float32))
        _, years = self._model.get(crop.image, face)
        return AgeReading(years=int(years), sure=reads_sure(crop))


def reads_sure(crop: FaceCrop) -> bool:
    """Si la edad de la cara de ``crop`` se lee segura: grande y de frente."""
    left, top, right, bottom = crop.box
    if max(right - left, bottom - top) < SMALLEST_SURE_FACE:
        return False
    (one_eye_x, _), (other_eye_x, _), (nose_x, _) = crop.points[:3]
    between = other_eye_x - one_eye_x
    if between <= 0:
        return False
    return abs(nose_x - (one_eye_x + other_eye_x) / 2) / between <= MOST_TURNED
