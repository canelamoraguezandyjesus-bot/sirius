"""La orden que instala la voz del robot: ``uv run --extra voz sirius-instala-la-voz``.

ADR-242, ADR-243 y ADR-246. La ejecuta el propietario, una vez y con internet, en
PowerShell y dentro de la carpeta de Sirius. Cuando llega aquí, ``uv run --extra voz`` ya
ha instalado o puesto al día las bibliotecas; esto baja el modelo de oír y las cuatro
voces de Piper de la prueba a ciegas a sus carpetas si faltan, antes de mirar lo demás, y
comprueba que el oído y cada voz cargan. Con ``--extra personaje`` baja además la voz de
personaje, la de Chatterbox; sin él, dice cómo se pone. Lo que ya está no lo vuelve a
bajar, y lo que falla lo dice con su causa, sin adivinar remedios (rondas 5, 8 y 9 de
Codex sobre la PR #687).

Es lo único de Sirius que baja un modelo o una voz. Si a Sirius le falta, dice esta orden
y no baja nada (PA-R03-08); una prueba recorre ``src/`` para que siga siendo así.

Cada uno se baja a una carpeta aparte y solo se pone en su sitio cuando está entero: una
descarga cortada no deja un modelo ni una voz a medias que parezcan instalados.
"""

from __future__ import annotations

import re
import shutil
import urllib.request
from collections.abc import Callable
from pathlib import Path

from sirius.adapters.audio.local_listening import (
    check_listening_libraries,
    load_listening_engines,
)
from sirius.adapters.audio.local_speaking import (
    check_speaking_libraries,
    load_speaking_engines,
)
from sirius.config.local_voice import LocalVoiceSettings, SpeakingVoice
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
from sirius.ports.local_voice import VoiceUnavailable

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


def _fail(problem: str, error: VoiceUnavailable) -> int:
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
