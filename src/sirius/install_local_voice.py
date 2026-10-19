"""La orden que instala la voz del robot: ``uv run --extra voz sirius-instala-la-voz``.

ADR-242, ADR-243 y ADR-246. La ejecuta el propietario, una vez y con internet, en
PowerShell y dentro de la carpeta de Sirius. Cuando llega aquí, ``uv run --extra voz`` ya
ha instalado o puesto al día las bibliotecas; esto baja el modelo de oír y las cuatro
voces de Piper de la prueba a ciegas a sus carpetas si faltan, antes de mirar lo demás, y
comprueba que el oído y cada voz cargan. Con ``--extra personaje`` baja además la voz de
personaje, la de Chatterbox; sin él, dice cómo se pone. Con ``--extra ojos`` baja además
el modelo de las caras, comprueba que la vista carga y mira si la cámara se abre (pieza D
de la 0.4, ADR-262), y baja los modelos de reconocer caras y voces y comprueba que cargan
(pieza E, ADR-263); sin él, dice cómo se pone. Lo que ya está no lo vuelve a bajar, y lo
que falla lo dice con su causa, sin adivinar remedios (rondas 5, 8 y 9 de Codex sobre la
PR #687).

Es lo único de Sirius que baja un modelo o una voz. Si a Sirius le falta, dice esta orden
y no baja nada (PA-R03-08); una prueba recorre ``src/`` para que siga siendo así.

Cada uno se baja a una carpeta aparte y solo se pone en su sitio cuando está entero: una
descarga cortada no deja un modelo ni una voz a medias que parezcan instalados.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from sirius.adapters.audio.local_listening import (
    check_listening_libraries,
    load_listening_engines,
)
from sirius.adapters.audio.local_speaking import (
    check_speaking_libraries,
    load_speaking_engines,
)
from sirius.adapters.recognition.engines import load_recognition_engines
from sirius.adapters.vision.local_sight import load_sight_engines
from sirius.config.local_voice import LocalVoiceSettings, SpeakingVoice
from sirius.infrastructure.local_sight_installation import (
    FACE_MODEL_SHA256,
    FACE_MODEL_URL,
    FACE_RECOGNITION_FILES,
    FACE_RECOGNITION_PACK_SHA256,
    FACE_RECOGNITION_PACK_URL,
    SIGHT_DISTRIBUTIONS,
    SIGHT_INSTALL_COMMAND,
    VOICE_RECOGNITION_FILES,
    VOICE_RECOGNITION_URL,
    face_model_complete,
    face_model_path,
    face_recognition_complete,
    face_recognition_dir,
    voice_recognition_complete,
    voice_recognition_dir,
)
from sirius.infrastructure.local_voice_installation import (
    CHARACTER_DISTRIBUTIONS,
    CHARACTER_INSTALL_COMMAND,
    CHARACTER_VOICE_FILES,
    INSTALL_COMMAND,
    listening_model_complete,
    listening_model_dir,
    speaking_voice_complete,
    speaking_voice_dir,
    voice_dir,
    voice_distributions_missing,
    voice_model,
)
from sirius.ports.local_sight import CameraUnavailable, SightUnavailable
from sirius.ports.local_voice import VoiceUnavailable
from sirius.ports.recognition import RecognitionUnavailable

#: Cómo se baja un modelo de faster-whisper: ``download_model(nombre, output_dir=...)``.
Download = Callable[..., object]
#: Cómo se baja una voz de Piper: ``download_voice(nombre, carpeta)``.
DownloadVoice = Callable[[str, Path], object]
#: Cómo se baja un fichero de la voz de personaje: ``download_file(dirección, destino)``.
DownloadFile = Callable[[str, Path], object]
#: De dónde se baja cada fichero de la voz de personaje: el repositorio de Chatterbox en
#: Hugging Face, el mismo del que la baja Chatterbox, fichero a fichero.
CHARACTER_VOICE_URL = (
    "https://huggingface.co/ResembleAI/chatterbox/resolve/main/{name}?download=true"
)


def download_listening_model(
    settings: LocalVoiceSettings, folder: Path, download: Download | None = None
) -> None:
    """Baja el modelo de oír de los ajustes a ``folder``, y solo lo deja ahí si está entero."""
    fetch = download if download is not None else _faster_whisper_download()
    partial = folder.with_name(f"{folder.name}.a-medias")
    shutil.rmtree(partial, ignore_errors=True)
    partial.parent.mkdir(parents=True, exist_ok=True)
    try:
        fetch(settings.listening_model.value, output_dir=str(partial))
    except BaseException:
        # Una descarga cortada no deja cientos de megas a medias en su disco.
        shutil.rmtree(partial, ignore_errors=True)
        raise
    if not listening_model_complete(partial):
        shutil.rmtree(partial, ignore_errors=True)
        msg = "la descarga no trajo todos los ficheros del modelo"
        raise RuntimeError(msg)
    if folder.exists():
        shutil.rmtree(folder)
    partial.rename(folder)


def download_speaking_voice(
    settings: LocalVoiceSettings, folder: Path, download: DownloadVoice | None = None
) -> None:
    """Baja la voz de los ajustes a ``folder``, y solo la deja ahí si está entera."""
    fetch = download if download is not None else _piper_download()
    voice = settings.speaking_voice.value
    partial = folder.with_name(f"{folder.name}.a-medias")
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    try:
        fetch(voice, partial)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    if not speaking_voice_complete(partial, voice):
        shutil.rmtree(partial, ignore_errors=True)
        msg = "la descarga no trajo los dos ficheros de la voz"
        raise RuntimeError(msg)
    if folder.exists():
        shutil.rmtree(folder)
    partial.rename(folder)


def download_character_voice(folder: Path, download: DownloadFile | None = None) -> None:
    """Baja la voz de personaje a ``folder``, y solo la deja ahí si está entera."""
    fetch = download if download is not None else _download_file
    partial = folder.with_name(f"{folder.name}.a-medias")
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    try:
        for name in CHARACTER_VOICE_FILES:
            fetch(CHARACTER_VOICE_URL.format(name=name), partial / name)
    except BaseException:
        # Unos gigas a medias no se quedan en su disco.
        shutil.rmtree(partial, ignore_errors=True)
        raise
    if not speaking_voice_complete(partial, SpeakingVoice.CHARACTER.value):
        shutil.rmtree(partial, ignore_errors=True)
        msg = "la descarga no trajo todos los ficheros de la voz de personaje"
        raise RuntimeError(msg)
    if folder.exists():
        shutil.rmtree(folder)
    partial.rename(folder)


def download_face_model(target: Path, download: DownloadFile | None = None) -> None:
    """Baja el modelo de las caras a ``target``, y solo lo deja ahí si está entero y es el
    de su huella: uno a medias, o uno cambiado en el servidor, no se pone."""
    fetch = download if download is not None else _download_file
    partial = target.with_name(f"{target.name}.a-medias")
    partial.unlink(missing_ok=True)
    partial.parent.mkdir(parents=True, exist_ok=True)
    try:
        fetch(FACE_MODEL_URL, partial)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    if _sha256(partial) != FACE_MODEL_SHA256 or not face_model_complete(partial):
        partial.unlink(missing_ok=True)
        msg = "lo bajado no es el modelo de las caras que se espera, o no llegó entero"
        raise RuntimeError(msg)
    partial.replace(target)


def download_face_recognition(folder: Path, download: DownloadFile | None = None) -> None:
    """Baja el paquete de modelos de InsightFace, mira que es el de su huella, saca de él el
    de reconocer caras y el de la edad a ``folder`` y lo borra. Solo deja la carpeta si está
    entera: un paquete a medias, cambiado en el servidor o sin uno de los dos, no se pone.
    De cada fichero del paquete se mira solo su nombre, no su ruta: nada se escribe fuera
    de la carpeta."""
    fetch = download if download is not None else _download_file
    partial = folder.with_name(f"{folder.name}.a-medias")
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    pack = partial / "paquete.zip"
    try:
        fetch(FACE_RECOGNITION_PACK_URL, pack)
        if _sha256(pack) != FACE_RECOGNITION_PACK_SHA256:
            msg = "lo bajado no es el paquete de reconocer caras que se espera, o no llegó entero"
            raise RuntimeError(msg)
        with zipfile.ZipFile(pack) as bundle:
            for name in FACE_RECOGNITION_FILES:
                with (
                    bundle.open(_member(bundle, name)) as source,
                    (partial / name).open("wb") as sink,
                ):
                    shutil.copyfileobj(source, sink, length=1 << 20)
        pack.unlink()
    except BaseException:
        # Cientos de megas a medias no se quedan en su disco.
        shutil.rmtree(partial, ignore_errors=True)
        raise
    if not face_recognition_complete(partial):
        shutil.rmtree(partial, ignore_errors=True)
        msg = "el paquete no trae enteros los modelos de reconocer caras"
        raise RuntimeError(msg)
    if folder.exists():
        shutil.rmtree(folder)
    partial.rename(folder)


def _member(bundle: zipfile.ZipFile, name: str) -> zipfile.ZipInfo:
    """El único fichero de ``bundle`` que se llama ``name``, esté en la carpeta que esté."""
    found = [
        info
        for info in bundle.infolist()
        if not info.is_dir() and PurePosixPath(info.filename.replace("\\", "/")).name == name
    ]
    if len(found) != 1:
        msg = f"el paquete de reconocer caras no trae un {name}, o trae más de uno"
        raise RuntimeError(msg)
    return found[0]


def download_voice_recognition(folder: Path, download: DownloadFile | None = None) -> None:
    """Baja ECAPA a ``folder``, fichero a fichero, y solo lo deja ahí si está entero."""
    fetch = download if download is not None else _download_file
    partial = folder.with_name(f"{folder.name}.a-medias")
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    try:
        for name in VOICE_RECOGNITION_FILES:
            fetch(VOICE_RECOGNITION_URL.format(name=name), partial / name)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    if not voice_recognition_complete(partial):
        shutil.rmtree(partial, ignore_errors=True)
        msg = "la descarga no trajo todos los ficheros de reconocer voces"
        raise RuntimeError(msg)
    if folder.exists():
        shutil.rmtree(folder)
    partial.rename(folder)


def _sha256(path: Path) -> str:
    """La huella de ``path``, leída a trozos de un mega."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _download_file(url: str, target: Path) -> None:
    """Baja ``url`` a ``target`` a trozos de un mega, sin tenerlo entero en memoria."""
    with urllib.request.urlopen(url) as source, target.open("wb") as sink:
        shutil.copyfileobj(source, sink, length=1 << 20)


def _piper_download() -> DownloadVoice:
    """La función de Piper que baja una voz; si no carga, ``VoiceUnavailable``."""
    try:
        from piper.download_voices import download_voice
    except Exception as error:
        raise VoiceUnavailable(f"piper no carga ({error})") from error
    fetch: DownloadVoice = download_voice
    return fetch


def _faster_whisper_download() -> Download:
    """La función de faster-whisper que baja un modelo; si no carga, ``VoiceUnavailable``."""
    try:
        from faster_whisper import download_model
    except Exception as error:
        raise VoiceUnavailable(f"faster_whisper no carga ({error})") from error
    fetch: Download = download_model
    return fetch


def main() -> int:
    settings = LocalVoiceSettings()
    folder = listening_model_dir(settings)
    model = settings.listening_model.value
    absent = voice_distributions_missing()
    if absent:
        # Solo pasa si se ejecutó sin el extra: así escrita, uv las instala antes.
        print(f"[FALLA] Faltan bibliotecas de la voz: {', '.join(absent)}")
        print(f"        Las instala esta orden escrita así: {INSTALL_COMMAND}")
        return 1
    # El modelo y las voces, antes que las demás bibliotecas: si faltan, se bajan aunque
    # otra esté rota, que lo que falta lo pone siempre (ronda 8 de Codex sobre la PR #687).
    if listening_model_complete(folder):
        print(f"[OK]    El modelo de oír (faster-whisper {model}) ya está en {folder}")
    else:
        print(f"Bajando el modelo de oír (faster-whisper {model}, unos 500 MB). Solo esta vez.")
        try:
            download_listening_model(settings, folder)
        except VoiceUnavailable as error:
            return _fail("No se puede bajar el modelo", error)
        except Exception as error:
            # La causa, y nada más: sin internet, un 403, sin espacio o un fichero en uso
            # tienen remedios distintos, y la orden no sabe cuál es (ronda 9 de Codex).
            print(f"[FALLA] No se pudo bajar el modelo: {error}")
            return 1
        print(f"[OK]    Modelo bajado a {folder}")
    # Las cuatro voces de Piper de la prueba a ciegas, la de los ajustes y las demás
    # (pieza F, ADR-246).
    piper = tuple(voice for voice in SpeakingVoice if not voice.is_character)
    for voice in piper:
        failed = _install_piper_voice(voice)
        if failed is not None:
            return failed
    character = not voice_distributions_missing(CHARACTER_DISTRIBUTIONS)
    if not character:
        print(
            "[--]    La voz de personaje (Chatterbox), para la prueba de voces, no está: la "
            f"instala {CHARACTER_INSTALL_COMMAND}"
        )
    else:
        failed = _install_character_voice()
        if failed is not None:
            return failed
    # La vista, con el modelo de las caras (pieza D de la 0.4, ADR-262).
    sight = not voice_distributions_missing(SIGHT_DISTRIBUTIONS)
    if not sight:
        print(
            f"[--]    La vista (la cámara y las caras) no está: la instala {SIGHT_INSTALL_COMMAND}"
        )
    else:
        failed = _install_face_model() or _install_recognition_models()
        if failed is not None:
            return failed
    try:
        check_listening_libraries()
        check_speaking_libraries()
    except VoiceUnavailable as error:
        return _fail("Una biblioteca de la voz no está bien", error)
    print("Comprobando que el oído carga...")
    try:
        load_listening_engines(folder)
    except VoiceUnavailable as error:
        return _fail("El oído no carga", error)
    voices = piper + ((SpeakingVoice.CHARACTER,) if character else ())
    for voice in voices:
        print(f"Comprobando que {_name(voice)} carga y que el altavoz se abre...")
        try:
            engines = load_speaking_engines(voice_model(voice))
        except VoiceUnavailable as error:
            name = _name(voice)
            return _fail(f"{name[0].upper()}{name[1:]} no carga", error)
        engines.speaker.close()
    if sight:
        failed = _check_sight() or _check_recognition()
        if failed is not None:
            return failed
    print("[OK]    Listo. Para probarlo: uv run --link-mode=copy --extra voz sirius-oye")
    return 0


def _name(voice: SpeakingVoice) -> str:
    return "la voz de personaje (Chatterbox)" if voice.is_character else f"la voz (Piper {voice})"


def _install_piper_voice(voice: SpeakingVoice) -> int | None:
    """Baja la voz de Piper ``voice`` si falta; el código con que acaba la orden si falla."""
    voice_settings = LocalVoiceSettings(speaking_voice=voice)
    voice_folder = speaking_voice_dir(voice_settings)
    if speaking_voice_complete(voice_folder, voice.value):
        print(f"[OK]    La voz (Piper {voice}) ya está en {voice_folder}")
        return None
    print(f"Bajando la voz (Piper {voice}, unos 60 MB). Solo esta vez.")
    try:
        download_speaking_voice(voice_settings, voice_folder)
    except VoiceUnavailable as error:
        return _fail("No se puede bajar la voz", error)
    except Exception as error:
        print(f"[FALLA] No se pudo bajar la voz: {error}")
        return 1
    print(f"[OK]    Voz bajada a {voice_folder}")
    return None


def _install_character_voice() -> int | None:
    """Baja la voz de personaje si falta; el código con que acaba la orden si falla."""
    character_folder = voice_dir(SpeakingVoice.CHARACTER)
    if speaking_voice_complete(character_folder, SpeakingVoice.CHARACTER.value):
        print(f"[OK]    La voz de personaje (Chatterbox) ya está en {character_folder}")
        return None
    print("Bajando la voz de personaje (Chatterbox, varios GB). Solo esta vez.")
    try:
        download_character_voice(character_folder)
    except Exception as error:
        print(f"[FALLA] No se pudo bajar la voz de personaje: {error}")
        return 1
    print(f"[OK]    Voz de personaje bajada a {character_folder}")
    return None


def _install_face_model() -> int | None:
    """Baja el modelo de las caras si falta; el código con que acaba la orden si falla."""
    model = face_model_path()
    if face_model_complete(model):
        print(f"[OK]    El modelo de las caras (MediaPipe) ya está en {model}")
        return None
    print("Bajando el modelo de las caras (MediaPipe, unos 4 MB). Solo esta vez.")
    try:
        download_face_model(model)
    except Exception as error:
        print(f"[FALLA] No se pudo bajar el modelo de las caras: {error}")
        return 1
    print(f"[OK]    Modelo de las caras bajado a {model}")
    return None


def _install_recognition_models() -> int | None:
    """Baja los modelos de reconocer caras y voces si faltan; el código con que acaba la
    orden si falla uno."""
    faces = face_recognition_dir()
    if face_recognition_complete(faces):
        print(f"[OK]    El modelo de reconocer caras (InsightFace) ya está en {faces}")
    else:
        print("Bajando el modelo de reconocer caras (InsightFace, unos 280 MB). Solo esta vez.")
        try:
            download_face_recognition(faces)
        except Exception as error:
            print(f"[FALLA] No se pudo bajar el modelo de reconocer caras: {error}")
            return 1
        print(f"[OK]    Modelo de reconocer caras bajado a {faces}")
    voices = voice_recognition_dir()
    if voice_recognition_complete(voices):
        print(f"[OK]    El modelo de reconocer voces (ECAPA) ya está en {voices}")
        return None
    print("Bajando el modelo de reconocer voces (ECAPA, unos 90 MB). Solo esta vez.")
    try:
        download_voice_recognition(voices)
    except Exception as error:
        print(f"[FALLA] No se pudo bajar el modelo de reconocer voces: {error}")
        return 1
    print(f"[OK]    Modelo de reconocer voces bajado a {voices}")
    return None


def _check_recognition() -> int | None:
    """Que reconocer caras y voces carga; el código con que acaba la orden si no."""
    print("Comprobando que reconocer caras y voces carga...")
    try:
        load_recognition_engines(face_recognition_dir(), voice_recognition_dir())
    except RecognitionUnavailable as error:
        return _fail("Reconocer caras y voces no carga", error)
    return None


def _check_sight() -> int | None:
    """Que la vista carga y si la cámara se abre; el código con que acaba la orden si la
    vista no carga. Sin cámara no falla: Sirius oye y habla igual, y lo dice."""
    print("Comprobando que la vista carga y que la cámara se abre...")
    try:
        engines = load_sight_engines(face_model_path())
    except SightUnavailable as error:
        return _fail("La vista no carga", error)
    try:
        engines.camera.open()
    except CameraUnavailable as error:
        print(f"[--]    La cámara no se abre: {error.reason}. Sirius oye y habla igual sin ella.")
        return None
    engines.camera.close()
    return None


def _fail(problem: str, error: VoiceUnavailable | SightUnavailable | RecognitionUnavailable) -> int:
    """Dice qué falla, con su causa, y nada más: no adivina si repetirla lo arreglaría.

    Un fallo que vuelve (una DLL) y uno que no (sin memoria un momento) se ven igual desde
    aquí (ronda 9 de Codex sobre la PR #687).
    """
    print(f"[FALLA] {problem}: {_cause(error.reason)}")
    return 1


#: Un motivo que vuelve a decir que lo comprobado no carga: el de una voz o del modelo de
#: oír, «la voz de personaje no carga (causa)». El de una biblioteca empieza por su nombre,
#: «torch no carga (causa)», y se deja entero, que dice cuál.
_SAME_FAILURE = re.compile(r"(?:la|el) [^()]* no carga \((?P<cause>.*)\)", re.DOTALL)


def _cause(reason: str) -> str:
    """La causa de ``reason``, sin repetir que lo comprobado no carga (ADR-252)."""
    same = _SAME_FAILURE.fullmatch(reason)
    return same["cause"] if same else reason


if __name__ == "__main__":
    raise SystemExit(main())
