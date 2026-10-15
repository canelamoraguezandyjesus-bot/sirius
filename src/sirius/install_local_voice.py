"""La orden que instala la voz del robot: ``uv run --extra voz sirius-instala-la-voz``.

ADR-242 y ADR-243. La ejecuta el propietario, una vez y con internet, en PowerShell y
dentro de la carpeta de Sirius. Cuando llega aquí, ``uv run --extra voz`` ya ha instalado
o puesto al día las bibliotecas; esto baja el modelo de oír y la voz de Piper a sus
carpetas si faltan, antes de mirar lo demás, y comprueba que el oído y la voz cargan. Lo
que ya está no lo vuelve a bajar, y lo que falla lo dice con su causa, sin adivinar
remedios (rondas 5, 8 y 9 de Codex sobre la PR #687).

Es lo único de Sirius que baja un modelo o una voz. Si a Sirius le falta, dice esta orden
y no baja nada (PA-R03-08); una prueba recorre ``src/`` para que siga siendo así.

Cada uno se baja a una carpeta aparte y solo se pone en su sitio cuando está entero: una
descarga cortada no deja un modelo ni una voz a medias que parezcan instalados.
"""

from __future__ import annotations

import shutil
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
from sirius.config.local_voice import LocalVoiceSettings
from sirius.infrastructure.local_voice_installation import (
    INSTALL_COMMAND,
    listening_model_complete,
    listening_model_dir,
    speaking_voice_complete,
    speaking_voice_dir,
    speaking_voice_files,
    voice_distributions_missing,
)
from sirius.ports.local_voice import VoiceUnavailable

#: Cómo se baja un modelo de faster-whisper: ``download_model(nombre, output_dir=...)``.
Download = Callable[..., object]
#: Cómo se baja una voz de Piper: ``download_voice(nombre, carpeta)``.
DownloadVoice = Callable[[str, Path], object]


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
    voice_folder = speaking_voice_dir(settings)
    voice = settings.speaking_voice.value
    absent = voice_distributions_missing()
    if absent:
        # Solo pasa si se ejecutó sin el extra: así escrita, uv las instala antes.
        print(f"[FALLA] Faltan bibliotecas de la voz: {', '.join(absent)}")
        print(f"        Las instala esta orden escrita así: {INSTALL_COMMAND}")
        return 1
    # El modelo y la voz, antes que las demás bibliotecas: si faltan, se bajan aunque otra
    # esté rota, que lo que falta lo pone siempre (ronda 8 de Codex sobre la PR #687).
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
    if speaking_voice_complete(voice_folder, voice):
        print(f"[OK]    La voz (Piper {voice}) ya está en {voice_folder}")
    else:
        print(f"Bajando la voz (Piper {voice}, unos 60 MB). Solo esta vez.")
        try:
            download_speaking_voice(settings, voice_folder)
        except VoiceUnavailable as error:
            return _fail("No se puede bajar la voz", error)
        except Exception as error:
            print(f"[FALLA] No se pudo bajar la voz: {error}")
            return 1
        print(f"[OK]    Voz bajada a {voice_folder}")
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
    print("Comprobando que la voz carga y que el altavoz se abre...")
    voice_model, _config = speaking_voice_files(voice)
    try:
        load_speaking_engines(voice_folder / voice_model)
    except VoiceUnavailable as error:
        return _fail("La voz no carga", error)
    print("[OK]    Listo. Para probarlo: uv run --extra voz sirius-oye")
    return 0


def _fail(problem: str, error: VoiceUnavailable) -> int:
    """Dice qué falla, con su causa, y nada más: no adivina si repetirla lo arreglaría.

    Un fallo que vuelve (una DLL) y uno que no (sin memoria un momento) se ven igual desde
    aquí (ronda 9 de Codex sobre la PR #687).
    """
    print(f"[FALLA] {problem}: {error.reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
