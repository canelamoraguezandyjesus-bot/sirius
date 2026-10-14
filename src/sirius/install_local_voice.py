"""La orden que instala la voz del robot: ``uv run --extra voz sirius-instala-la-voz``.

ADR-242. La ejecuta el propietario, una vez y con internet, en PowerShell y dentro de la
carpeta de Sirius. Cuando llega aquí, ``uv run --extra voz`` ya ha instalado o puesto al
día las bibliotecas; esto baja el modelo de oír a su carpeta si falta, antes de mirar lo
demás, y comprueba que el oído carga. Lo que ya está no lo vuelve a bajar, y lo que no
puede arreglar lo dice (rondas 5 y 8 de Codex sobre la PR #687).

Es lo único de Sirius que baja un modelo. Si a Sirius le falta, dice esta orden y no
baja nada (PA-R03-08); una prueba recorre ``src/`` para que siga siendo así.

El modelo se baja a una carpeta aparte y solo se pone en su sitio cuando está entero:
una descarga cortada no deja un modelo a medias que parezca instalado.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from sirius.adapters.audio.local_listening import (
    check_listening_libraries,
    load_listening_engines,
)
from sirius.config.local_voice import LocalVoiceSettings
from sirius.infrastructure.local_voice_installation import (
    INSTALL_COMMAND,
    listening_model_complete,
    listening_model_dir,
    voice_distributions_missing,
)
from sirius.ports.local_voice import VoiceUnavailable

#: Cómo se baja un modelo de faster-whisper: ``download_model(nombre, output_dir=...)``.
Download = Callable[..., object]


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
    # El modelo, antes que las demás bibliotecas: si falta, se baja aunque otra esté rota,
    # que lo que falta lo pone siempre (ronda 8 de Codex sobre la PR #687).
    if listening_model_complete(folder):
        print(f"[OK]    El modelo de oír (faster-whisper {model}) ya está en {folder}")
    else:
        print(f"Bajando el modelo de oír (faster-whisper {model}, unos 500 MB). Solo esta vez.")
        try:
            download_listening_model(settings, folder)
        except VoiceUnavailable as error:
            return _fail("No se puede bajar el modelo", error)
        except Exception as error:
            print(f"[FALLA] No se pudo bajar el modelo: {error}")
            print("        Si Sirius está abierto, ciérralo y vuelve a ejecutar la orden.")
            return 1
        print(f"[OK]    Modelo bajado a {folder}")
    try:
        check_listening_libraries()
    except VoiceUnavailable as error:
        return _fail("Una biblioteca de la voz no está bien", error)
    print("Comprobando que el oído carga...")
    try:
        load_listening_engines(folder)
    except VoiceUnavailable as error:
        return _fail("El oído no carga", error)
    print("[OK]    Listo. Para probarlo: uv run --extra voz sirius-oye")
    return 0


def _fail(problem: str, error: VoiceUnavailable) -> int:
    """Dice qué falla y que repetir la orden no lo arreglará.

    Escrita como la dice Sirius, uv ya puso al día las bibliotecas antes de empezar y el
    modelo ya está: lo que quede no lo arregla repetirla.
    """
    print(f"[FALLA] {problem}: {error.reason}")
    print(f"        Si la ejecutaste así, {INSTALL_COMMAND} , repetirla no lo arreglará.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
