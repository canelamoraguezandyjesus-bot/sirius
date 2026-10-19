"""Lo que necesita instalado la vista del robot, y cómo lo pone la orden de instalar (pieza
D de la 0.4, ADR-262).

Las bibliotecas van en el extra ``ojos``, y el modelo de las caras, el ``face_landmarker.task``
de MediaPipe, lo baja la orden de instalar la voz cuando se escribe con ese extra. Lo baja
aparte y solo lo pone en su sitio si es el de su huella y está entero: una descarga
cortada, o un fichero cambiado en el servidor, nunca parecen instalados. Después mira que
la vista carga y si la cámara se abre; sin cámara no falla, que Sirius oye y habla igual.
Aquí no se baja nada de verdad: la descarga es de mentira, como la vista.
"""

from __future__ import annotations

import hashlib
import io
import re
import tomllib
import types
import zipfile
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path

import pytest

import sirius.install_local_voice as install_local_voice
from sirius.config.local_voice import LocalVoiceSettings, SpeakingVoice
from sirius.infrastructure.local_sight_installation import (
    FACE_MODEL_MEMBERS,
    FACE_MODEL_URL,
    FACE_RECOGNITION_PACK_URL,
    SIGHT_DISTRIBUTIONS,
    SIGHT_INSTALL_COMMAND,
    VOICE_RECOGNITION_FILES,
    VOICE_RECOGNITION_URL,
    face_model_complete,
    face_model_path,
    face_recognition_complete,
    face_recognition_dir,
    sight_models_dir,
    voice_recognition_complete,
    voice_recognition_dir,
)
from sirius.infrastructure.local_voice_installation import (
    CHARACTER_DISTRIBUTIONS,
    LocalVoiceInstallation,
    speaking_voice_files,
    voice_dir,
)
from sirius.infrastructure.paths import resolve_paths
from sirius.install_local_voice import (
    download_face_model,
    download_face_recognition,
    download_voice_recognition,
)
from sirius.ports.local_sight import CameraUnavailable, SightUnavailable
from sirius.ports.recognition import RecognitionUnavailable

_RAIZ = Path(__file__).resolve().parents[2]
#: Lo que lleva dentro el modelo de las caras de verdad, escrito aquí y no copiado de
#: Sirius: si Sirius dejara de pedir uno, estas pruebas lo verían. El de la geometría es con
#: lo que MediaPipe sabe hacia dónde gira la cabeza.
_DENTRO = (
    "face_detector.tflite",
    "face_landmarks_detector.tflite",
    "face_blendshapes.tflite",
    "geometry_pipeline_metadata_landmarks.binarypb",
)


def _modelo(dentro: tuple[str, ...] = _DENTRO, relleno: bytes = b"pesos") -> bytes:
    """Un ``.task`` de mentira: un zip con ``dentro``."""
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zip_:
        for nombre in dentro:
            zip_.writestr(nombre, relleno)
    return salida.getvalue()


def _huella(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


# --- Dónde va y cuándo está entero ----------------------------------------------------


def test_el_modelo_de_las_caras_vive_en_la_carpeta_de_datos_de_siempre() -> None:
    carpeta = resolve_paths().data_dir / "modelos" / "ojos"

    assert sight_models_dir() == carpeta
    assert face_model_path() == carpeta / "face_landmarker.task"


def test_se_mira_que_lleve_dentro_lo_que_lleva_el_de_verdad() -> None:
    assert set(FACE_MODEL_MEMBERS) == set(_DENTRO)


def test_esta_entero_solo_si_es_un_zip_con_todo_lo_que_lleva_dentro(tmp_path: Path) -> None:
    modelo = tmp_path / "face_landmarker.task"
    assert not face_model_complete(modelo), "sin fichero"

    modelo.write_bytes(b"no es un zip")
    assert not face_model_complete(modelo)

    for falta in _DENTRO:
        modelo.write_bytes(_modelo(tuple(n for n in _DENTRO if n != falta)))
        assert not face_model_complete(modelo), falta

    modelo.write_bytes(_modelo())
    assert face_model_complete(modelo)


def test_baja_de_la_version_fija_de_los_modelos_de_mediapipe() -> None:
    assert FACE_MODEL_URL == (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/"
        "float16/1/face_landmarker.task"
    )


# --- Bajarlo --------------------------------------------------------------------------


def test_lo_baja_aparte_y_lo_pone_en_su_sitio_si_es_el_de_su_huella(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    datos = _modelo()
    monkeypatch.setattr(install_local_voice, "FACE_MODEL_SHA256", _huella(datos))
    destino = tmp_path / "ojos" / "face_landmarker.task"
    pedidos: list[tuple[str, Path]] = []

    def baja(url: str, aparte: Path) -> None:
        pedidos.append((url, aparte))
        assert not destino.exists(), "no se escribe en su sitio mientras baja"
        aparte.write_bytes(datos)

    download_face_model(destino, baja)

    assert pedidos == [(FACE_MODEL_URL, destino.with_name("face_landmarker.task.a-medias"))]
    assert destino.read_bytes() == datos
    assert list(destino.parent.iterdir()) == [destino]


@pytest.mark.parametrize(
    "bajado",
    [
        pytest.param(_modelo(relleno=b"otros pesos"), id="otro modelo entero"),
        pytest.param(_modelo()[:-40], id="cortado"),
        pytest.param(b"<html>404</html>", id="una pagina de error"),
    ],
)
def test_lo_que_no_es_el_de_su_huella_no_se_pone_y_deja_el_que_habia(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bajado: bytes
) -> None:
    monkeypatch.setattr(install_local_voice, "FACE_MODEL_SHA256", _huella(_modelo()))
    destino = tmp_path / "face_landmarker.task"
    destino.write_bytes(b"el que habia")

    with pytest.raises(RuntimeError, match="no es el modelo de las caras"):
        download_face_model(destino, lambda url, aparte: aparte.write_bytes(bajado))

    assert destino.read_bytes() == b"el que habia"
    assert list(tmp_path.iterdir()) == [destino], "no queda nada a medias"


def test_uno_con_su_huella_que_no_lleva_todo_dentro_tampoco_se_pone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # La huella es la garantía; lo de dentro, la segunda mirada, la misma que hace Sirius.
    incompleto = _modelo(_DENTRO[:2])
    monkeypatch.setattr(install_local_voice, "FACE_MODEL_SHA256", _huella(incompleto))
    destino = tmp_path / "face_landmarker.task"

    with pytest.raises(RuntimeError):
        download_face_model(destino, lambda url, aparte: aparte.write_bytes(incompleto))

    assert list(tmp_path.iterdir()) == []


def test_una_descarga_cortada_no_deja_nada_y_deja_el_que_habia(tmp_path: Path) -> None:
    destino = tmp_path / "face_landmarker.task"
    destino.write_bytes(b"el que habia")

    def se_corta(url: str, aparte: Path) -> None:
        aparte.write_bytes(b"medio")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        download_face_model(destino, se_corta)

    assert destino.read_bytes() == b"el que habia"
    assert list(tmp_path.iterdir()) == [destino]


def test_unos_restos_de_otra_vez_no_cuentan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    datos = _modelo()
    monkeypatch.setattr(install_local_voice, "FACE_MODEL_SHA256", _huella(datos))
    destino = tmp_path / "face_landmarker.task"
    aparte = destino.with_name("face_landmarker.task.a-medias")
    aparte.write_bytes(b"restos de una descarga cortada")
    vistos: list[bool] = []

    def baja(url: str, donde: Path) -> None:
        vistos.append(donde.exists())
        donde.write_bytes(datos)

    download_face_model(destino, baja)

    assert vistos == [False]
    assert destino.read_bytes() == datos


# --- La orden de instalar -------------------------------------------------------------


class _Camara:
    def __init__(self, apuntes: list[str], falla: CameraUnavailable | None = None) -> None:
        self._apuntes = apuntes
        self._falla = falla

    def open(self) -> None:
        self._apuntes.append("abre")
        if self._falla is not None:
            raise self._falla

    def close(self) -> None:
        self._apuntes.append("cierra")


@pytest.fixture
def la_voz_esta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Todo lo de la voz puesto y cargando, como tras `uv run --extra voz`; la vista, según
    la prueba. Y nada se baja de verdad."""
    ajustes = LocalVoiceSettings()
    carpeta = LocalVoiceInstallation(ajustes).listening_model_dir
    carpeta.mkdir(parents=True)
    for nombre in ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt"):
        (carpeta / nombre).write_bytes(b"pesos")
    for voz in SpeakingVoice:
        if not voz.is_character:
            voice_dir(voz).mkdir(parents=True)
            for nombre in speaking_voice_files(voz.value):
                (voice_dir(voz) / nombre).write_bytes(b"voz")
    monkeypatch.setattr(install_local_voice, "check_listening_libraries", lambda: None)
    monkeypatch.setattr(install_local_voice, "check_speaking_libraries", lambda: None)
    monkeypatch.setattr(install_local_voice, "load_listening_engines", lambda carpeta: None)
    monkeypatch.setattr(
        install_local_voice,
        "load_speaking_engines",
        lambda modelo: types.SimpleNamespace(speaker=types.SimpleNamespace(close=lambda: None)),
    )

    def no_baja(url: str, destino: Path) -> None:
        raise AssertionError(f"una prueba ha ido a bajar {url}")

    monkeypatch.setattr(install_local_voice, "_download_file", no_baja)
    # Lo de reconocer (pieza E, ADR-263), puesto y cargando, salvo que la prueba diga otra
    # cosa.
    monkeypatch.setattr(install_local_voice, "face_recognition_complete", lambda carpeta: True)
    monkeypatch.setattr(install_local_voice, "voice_recognition_complete", lambda carpeta: True)
    monkeypatch.setattr(install_local_voice, "load_recognition_engines", lambda caras, voces: None)


def _con_ojos(nombres: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Las bibliotecas de la voz y de los ojos están; las de ``personaje``, no."""
    return tuple(nombre for nombre in nombres if nombre in CHARACTER_DISTRIBUTIONS)


def _sin_ojos(nombres: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Las bibliotecas de la voz están; las de ``personaje`` y ``ojos``, no."""
    return tuple(
        nombre for nombre in nombres if nombre in (*CHARACTER_DISTRIBUTIONS, *SIGHT_DISTRIBUTIONS)
    )


def _vista(monkeypatch: pytest.MonkeyPatch, camara: _Camara) -> list[Path]:
    """La vista de mentira, que carga con la cámara ``camara``; devuelve con qué modelo."""
    cargadas: list[Path] = []

    def carga(modelo: Path) -> types.SimpleNamespace:
        cargadas.append(modelo)
        return types.SimpleNamespace(camera=camara, detector=object())

    monkeypatch.setattr(install_local_voice, "load_sight_engines", carga)
    return cargadas


@pytest.mark.usefixtures("la_voz_esta")
def test_sin_el_extra_ojos_dice_como_se_pone_y_no_baja_ni_carga_nada(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no(*args: object) -> None:
        raise AssertionError("sin el extra no se toca la vista")

    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", _sin_ojos)
    monkeypatch.setattr(install_local_voice, "download_face_model", no)
    monkeypatch.setattr(install_local_voice, "load_sight_engines", no)

    assert install_local_voice.main() == 0

    salida = capsys.readouterr().out
    assert f"La vista (la cámara y las caras) no está: la instala {SIGHT_INSTALL_COMMAND}" in salida


@pytest.mark.usefixtures("la_voz_esta")
def test_con_el_extra_ojos_baja_el_modelo_y_mira_que_la_vista_carga_y_la_camara_se_abre(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bajados: list[Path] = []

    def baja(destino: Path) -> None:
        bajados.append(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(_modelo())

    apuntes: list[str] = []
    cargadas = _vista(monkeypatch, _Camara(apuntes))
    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", _con_ojos)
    monkeypatch.setattr(install_local_voice, "download_face_model", baja)

    assert install_local_voice.main() == 0

    assert bajados == [face_model_path()]
    assert cargadas == [face_model_path()]
    assert apuntes == ["abre", "cierra"], "la abre para mirarla, y la suelta"
    salida = capsys.readouterr().out
    assert "Bajando el modelo de las caras (MediaPipe" in salida
    assert "Comprobando que la vista carga y que la cámara se abre" in salida
    assert SIGHT_INSTALL_COMMAND not in salida
    assert salida.rstrip().endswith("sirius-oye")


@pytest.mark.usefixtures("la_voz_esta")
def test_con_el_modelo_puesto_no_lo_vuelve_a_bajar(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    face_model_path().parent.mkdir(parents=True)
    face_model_path().write_bytes(_modelo())

    def no_baja(destino: Path) -> None:
        raise AssertionError("ha vuelto a bajar el modelo de las caras")

    _vista(monkeypatch, _Camara([]))
    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", _con_ojos)
    monkeypatch.setattr(install_local_voice, "download_face_model", no_baja)

    assert install_local_voice.main() == 0
    assert "El modelo de las caras (MediaPipe) ya está en" in capsys.readouterr().out


@pytest.mark.usefixtures("la_voz_esta")
def test_si_no_se_puede_bajar_el_modelo_lo_dice_con_su_causa_y_no_carga_la_vista(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def sin_internet(destino: Path) -> None:
        raise OSError("[Errno 11001] getaddrinfo failed")

    def no_carga(modelo: Path) -> None:
        raise AssertionError("sin modelo no se carga la vista")

    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", _con_ojos)
    monkeypatch.setattr(install_local_voice, "download_face_model", sin_internet)
    monkeypatch.setattr(install_local_voice, "load_sight_engines", no_carga)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "[FALLA] No se pudo bajar el modelo de las caras: [Errno 11001] getaddrinfo failed" in (
        salida
    )


@pytest.mark.usefixtures("la_voz_esta")
def test_si_la_vista_no_carga_lo_dice_una_vez_con_su_causa_y_acaba_en_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    face_model_path().parent.mkdir(parents=True)
    face_model_path().write_bytes(_modelo())

    def no_carga(modelo: Path) -> None:
        raise SightUnavailable("el modelo de las caras no carga (Unable to open zip archive)")

    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", _con_ojos)
    monkeypatch.setattr(install_local_voice, "load_sight_engines", no_carga)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "[FALLA] La vista no carga: Unable to open zip archive" in salida
    assert salida.count("no carga") == 1


@pytest.mark.usefixtures("la_voz_esta")
def test_sin_camara_lo_dice_y_acaba_bien_porque_oye_y_habla_igual(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    face_model_path().parent.mkdir(parents=True)
    face_model_path().write_bytes(_modelo())
    apuntes: list[str] = []
    _vista(
        monkeypatch, _Camara(apuntes, CameraUnavailable("no hay cámara, o la tiene otro programa"))
    )
    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", _con_ojos)

    assert install_local_voice.main() == 0

    assert apuntes == ["abre"]
    salida = capsys.readouterr().out
    assert "La cámara no se abre: no hay cámara, o la tiene otro programa." in salida
    assert "[FALLA]" not in salida


# --- Los modelos de reconocer (pieza E de la 0.4, ADR-263) -------------------------

#: Lo que trae el paquete ``buffalo_l`` de InsightFace, escrito aquí y no copiado de Sirius.
_PAQUETE = ("det_10g.onnx", "1k3d68.onnx", "2d106det.onnx", "genderage.onnx", "w600k_r50.onnx")


def _paquete(nombres: tuple[str, ...] = _PAQUETE, carpeta: str = "") -> bytes:
    """Un paquete de mentira: un zip con ``nombres`` dentro de ``carpeta``, y en cada uno,
    «pesos» y su nombre."""
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zip_:
        for nombre in nombres:
            zip_.writestr(f"{carpeta}{nombre}", b"pesos-" + nombre.encode())
    return salida.getvalue()


def _baja_esto(datos: bytes, pedidos: list[str] | None = None) -> Callable[[str, Path], None]:
    def baja(url: str, destino: Path) -> None:
        if pedidos is not None:
            pedidos.append(url)
        destino.write_bytes(datos)

    return baja


def test_los_modelos_de_reconocer_viven_en_la_carpeta_de_los_ojos() -> None:
    assert face_recognition_dir() == sight_models_dir() / "insightface"
    assert voice_recognition_dir() == sight_models_dir() / "ecapa"


def test_baja_el_paquete_de_la_version_fija_y_se_queda_solo_con_los_dos_modelos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    datos = _paquete()
    monkeypatch.setattr(install_local_voice, "FACE_RECOGNITION_PACK_SHA256", _huella(datos))
    pedidos: list[str] = []
    carpeta = tmp_path / "insightface"

    download_face_recognition(carpeta, _baja_esto(datos, pedidos))

    assert pedidos == [FACE_RECOGNITION_PACK_URL]
    assert "/releases/download/v0.7/buffalo_l.zip" in FACE_RECOGNITION_PACK_URL
    assert sorted(p.name for p in carpeta.iterdir()) == ["genderage.onnx", "w600k_r50.onnx"]
    assert (carpeta / "w600k_r50.onnx").read_bytes() == b"pesos-w600k_r50.onnx"
    assert face_recognition_complete(carpeta)
    assert list(tmp_path.iterdir()) == [carpeta], "ni el paquete ni la carpeta a medias"


def test_los_modelos_dentro_de_una_carpeta_del_paquete_tambien_valen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    datos = _paquete(carpeta="buffalo_l/")
    monkeypatch.setattr(install_local_voice, "FACE_RECOGNITION_PACK_SHA256", _huella(datos))
    carpeta = tmp_path / "insightface"

    download_face_recognition(carpeta, _baja_esto(datos))

    assert (carpeta / "genderage.onnx").read_bytes() == b"pesos-genderage.onnx"


def test_nada_del_paquete_se_escribe_fuera_de_su_carpeta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    datos = _paquete(("w600k_r50.onnx", "genderage.onnx"), carpeta="../../fuera/")
    monkeypatch.setattr(install_local_voice, "FACE_RECOGNITION_PACK_SHA256", _huella(datos))
    dentro = tmp_path / "a" / "b"
    dentro.mkdir(parents=True)
    carpeta = dentro / "insightface"

    download_face_recognition(carpeta, _baja_esto(datos))

    assert sorted(p.name for p in carpeta.iterdir()) == ["genderage.onnx", "w600k_r50.onnx"]
    assert not (tmp_path / "fuera").exists()


@pytest.mark.parametrize(
    "nombres",
    [
        ("det_10g.onnx", "w600k_r50.onnx"),
        ("genderage.onnx", "w600k_r50.onnx", "otra/w600k_r50.onnx"),
    ],
)
def test_un_paquete_sin_uno_de_los_dos_o_con_dos_iguales_no_se_pone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, nombres: tuple[str, ...]
) -> None:
    datos = _paquete(nombres)
    monkeypatch.setattr(install_local_voice, "FACE_RECOGNITION_PACK_SHA256", _huella(datos))
    carpeta = tmp_path / "insightface"

    with pytest.raises(RuntimeError, match="no trae"):
        download_face_recognition(carpeta, _baja_esto(datos))

    assert list(tmp_path.iterdir()) == []


def test_un_paquete_que_no_es_el_de_su_huella_no_se_pone_y_deja_lo_que_habia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(install_local_voice, "FACE_RECOGNITION_PACK_SHA256", _huella(_paquete()))
    carpeta = tmp_path / "insightface"
    carpeta.mkdir()
    (carpeta / "w600k_r50.onnx").write_bytes(b"el de antes")

    with pytest.raises(RuntimeError, match="no es el paquete de reconocer caras"):
        download_face_recognition(carpeta, _baja_esto(_paquete(carpeta="cambiado/")))

    assert (carpeta / "w600k_r50.onnx").read_bytes() == b"el de antes"
    assert list(tmp_path.iterdir()) == [carpeta]


def test_una_descarga_cortada_del_paquete_no_deja_nada(tmp_path: Path) -> None:
    def cortada(url: str, destino: Path) -> None:
        destino.write_bytes(b"a medias")
        raise OSError("se cortó")

    with pytest.raises(OSError, match="se cortó"):
        download_face_recognition(tmp_path / "insightface", cortada)

    assert list(tmp_path.iterdir()) == []


def test_baja_cada_fichero_de_ecapa_y_solo_lo_pone_si_esta_entero(tmp_path: Path) -> None:
    pedidos: list[str] = []
    carpeta = tmp_path / "ecapa"

    download_voice_recognition(carpeta, _baja_esto(b"pesos", pedidos))

    assert pedidos == [VOICE_RECOGNITION_URL.format(name=n) for n in VOICE_RECOGNITION_FILES]
    assert "huggingface.co/speechbrain/spkrec-ecapa-voxceleb/" in VOICE_RECOGNITION_URL
    assert sorted(p.name for p in carpeta.iterdir()) == sorted(VOICE_RECOGNITION_FILES)
    assert voice_recognition_complete(carpeta)
    assert list(tmp_path.iterdir()) == [carpeta]


def test_ecapa_a_medias_o_con_un_fichero_vacio_no_se_pone_y_deja_lo_que_habia(
    tmp_path: Path,
) -> None:
    carpeta = tmp_path / "ecapa"
    carpeta.mkdir()
    (carpeta / "hyperparams.yaml").write_bytes(b"el de antes")

    def cortada(url: str, destino: Path) -> None:
        if "classifier" in url:
            raise OSError("se cortó")
        destino.write_bytes(b"pesos")

    def vacio(url: str, destino: Path) -> None:
        destino.write_bytes(b"" if "label_encoder" in url else b"pesos")

    with pytest.raises(OSError, match="se cortó"):
        download_voice_recognition(carpeta, cortada)
    with pytest.raises(RuntimeError, match="no trajo todos los ficheros de reconocer voces"):
        download_voice_recognition(carpeta, vacio)

    assert (carpeta / "hyperparams.yaml").read_bytes() == b"el de antes"
    assert list(tmp_path.iterdir()) == [carpeta]


@pytest.mark.usefixtures("la_voz_esta")
def test_con_el_extra_ojos_baja_los_modelos_de_reconocer_y_mira_que_cargan(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    face_model_path().parent.mkdir(parents=True)
    face_model_path().write_bytes(_modelo())
    _vista(monkeypatch, _Camara([]))
    hecho: list[str] = []
    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", _con_ojos)
    monkeypatch.setattr(install_local_voice, "face_recognition_complete", lambda c: False)
    monkeypatch.setattr(install_local_voice, "voice_recognition_complete", lambda c: False)
    monkeypatch.setattr(
        install_local_voice, "download_face_recognition", lambda c: hecho.append(f"caras:{c}")
    )
    monkeypatch.setattr(
        install_local_voice, "download_voice_recognition", lambda c: hecho.append(f"voces:{c}")
    )
    monkeypatch.setattr(
        install_local_voice,
        "load_recognition_engines",
        lambda caras, voces: hecho.append(f"carga:{caras}:{voces}"),
    )

    assert install_local_voice.main() == 0

    assert hecho == [
        f"caras:{face_recognition_dir()}",
        f"voces:{voice_recognition_dir()}",
        f"carga:{face_recognition_dir()}:{voice_recognition_dir()}",
    ]
    salida = capsys.readouterr().out
    assert "Bajando el modelo de reconocer caras (InsightFace" in salida
    assert "Bajando el modelo de reconocer voces (ECAPA" in salida
    assert "Comprobando que reconocer caras y voces carga" in salida
    assert salida.rstrip().endswith("sirius-oye")


@pytest.mark.usefixtures("la_voz_esta")
def test_con_los_modelos_de_reconocer_puestos_no_los_vuelve_a_bajar(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    face_model_path().parent.mkdir(parents=True)
    face_model_path().write_bytes(_modelo())
    _vista(monkeypatch, _Camara([]))

    def no_baja(carpeta: Path) -> None:
        raise AssertionError("ha vuelto a bajar un modelo de reconocer")

    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", _con_ojos)
    monkeypatch.setattr(install_local_voice, "download_face_recognition", no_baja)
    monkeypatch.setattr(install_local_voice, "download_voice_recognition", no_baja)

    assert install_local_voice.main() == 0
    salida = capsys.readouterr().out
    assert "El modelo de reconocer caras (InsightFace) ya está en" in salida
    assert "El modelo de reconocer voces (ECAPA) ya está en" in salida


@pytest.mark.usefixtures("la_voz_esta")
@pytest.mark.parametrize("de_que", ["caras", "voces"])
def test_si_no_se_puede_bajar_un_modelo_de_reconocer_lo_dice_con_su_causa(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], de_que: str
) -> None:
    face_model_path().parent.mkdir(parents=True)
    face_model_path().write_bytes(_modelo())

    def sin_internet(carpeta: Path) -> None:
        raise OSError("[Errno 11001] getaddrinfo failed")

    def no_carga(*args: object) -> None:
        raise AssertionError("sin los modelos no se carga nada más")

    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", _con_ojos)
    monkeypatch.setattr(
        install_local_voice,
        f"{'face' if de_que == 'caras' else 'voice'}_recognition_complete",
        lambda c: False,
    )
    monkeypatch.setattr(install_local_voice, "download_face_recognition", sin_internet)
    monkeypatch.setattr(install_local_voice, "download_voice_recognition", sin_internet)
    monkeypatch.setattr(install_local_voice, "load_sight_engines", no_carga)
    monkeypatch.setattr(install_local_voice, "load_recognition_engines", no_carga)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert (
        f"[FALLA] No se pudo bajar el modelo de reconocer {de_que}: [Errno 11001] getaddrinfo "
        "failed"
    ) in salida


@pytest.mark.usefixtures("la_voz_esta")
def test_si_reconocer_no_carga_lo_dice_una_vez_con_su_causa_y_acaba_en_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    face_model_path().parent.mkdir(parents=True)
    face_model_path().write_bytes(_modelo())
    _vista(monkeypatch, _Camara([]))

    def no_carga(caras: Path, voces: Path) -> None:
        raise RecognitionUnavailable("el modelo de reconocer voces no carga (falta torch)")

    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", _con_ojos)
    monkeypatch.setattr(install_local_voice, "load_recognition_engines", no_carga)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "[FALLA] Reconocer caras y voces no carga: falta torch" in salida
    assert salida.count("no carga") == 1


@pytest.mark.usefixtures("la_voz_esta")
def test_sin_el_extra_ojos_no_baja_ni_carga_lo_de_reconocer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no(*args: object) -> None:
        raise AssertionError("sin el extra no se toca lo de reconocer")

    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", _sin_ojos)
    monkeypatch.setattr(install_local_voice, "download_face_recognition", no)
    monkeypatch.setattr(install_local_voice, "download_voice_recognition", no)
    monkeypatch.setattr(install_local_voice, "load_recognition_engines", no)

    assert install_local_voice.main() == 0


# --- El extra y la orden --------------------------------------------------------------


def _pyproject() -> dict[str, object]:
    return tomllib.loads((_RAIZ / "pyproject.toml").read_text(encoding="utf-8"))


def test_las_distribuciones_que_se_miran_son_las_del_extra_ojos() -> None:
    proyecto = _pyproject()["project"]
    assert isinstance(proyecto, dict)
    extra = proyecto["optional-dependencies"]["ojos"]
    nombres = {re.split(r"[^A-Za-z0-9._-]", requisito, maxsplit=1)[0] for requisito in extra}

    assert {n.lower().replace("_", "-") for n in nombres} == set(SIGHT_DISTRIBUTIONS)


def test_la_orden_se_pega_tal_cual_en_powershell_y_es_la_de_la_voz_con_los_ojos() -> None:
    proyecto = _pyproject()["project"]
    assert isinstance(proyecto, dict)
    orden = SIGHT_INSTALL_COMMAND.split()

    assert orden[:3] == ["uv", "run", "--link-mode=copy"]
    assert orden[-1] in proyecto["scripts"]
    assert proyecto["scripts"][orden[-1]] == "sirius.install_local_voice:main"
    assert {"--extra voz", "--extra ojos"} <= {" ".join(par) for par in pairwise(orden)}


def test_un_solo_opencv_el_de_mediapipe() -> None:
    # Todos ponen el mismo `cv2`, y el segundo pisaría al primero (ADR-259): los otros dos
    # quedan fuera con un marcador que nunca se cumple, para quien los pida. InsightFace pide
    # `opencv-python` (pieza E, ADR-263): el candado lo apunta, siempre con ese marcador, y
    # nunca se instala.
    herramienta = _pyproject()["tool"]
    assert isinstance(herramienta, dict)
    fuera = herramienta["uv"]["override-dependencies"]
    nunca = "sys_platform == 'never'"
    assert f"opencv-python; {nunca}" in fuera
    assert f"opencv-python-headless; {nunca}" in fuera

    candado = tomllib.loads((_RAIZ / "uv.lock").read_text(encoding="utf-8"))
    aristas: list[dict[str, str]] = []
    for paquete in candado["package"]:
        grupos = [
            paquete.get("dependencies", []),
            *paquete.get("optional-dependencies", {}).values(),
            *paquete.get("dev-dependencies", {}).values(),
        ]
        aristas.extend(dependencia for grupo in grupos for dependencia in grupo)
    opencv = {arista["name"] for arista in aristas if arista["name"].startswith("opencv")}
    assert opencv <= {"opencv-contrib-python", "opencv-python", "opencv-python-headless"}
    otros = [a for a in aristas if a["name"] in ("opencv-python", "opencv-python-headless")]
    assert all(arista.get("marker") == nunca for arista in otros), otros
    assert any(a["name"] == "opencv-contrib-python" and "marker" not in a for a in aristas)
