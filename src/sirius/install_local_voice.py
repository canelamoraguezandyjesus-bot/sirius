"""La orden que instala la voz del robot: ``uv run --extra voz sirius-instala-la-voz``.

ADR-242. La ejecuta el propietario, una vez y con internet, en PowerShell y dentro de la
carpeta de Sirius. Cuando llega aquí, ``uv run --extra voz`` ya ha instalado las
bibliotecas; esto baja el modelo de oír a su carpeta y comprueba que el oído carga.

Es lo único de Sirius que baja un modelo. Si a Sirius le falta, dice esta orden y no
baja nada (PA-R03-08); una prueba recorre ``src/`` para que siga siendo así.

El modelo se baja a una carpeta aparte y solo se pone en su sitio cuando está entero:
una descarga cortada no deja un modelo a medias que parezca instalado.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from sirius.adapters.audio.local_listening import load_listening_engines
from sirius.config.local_voice import LocalVoiceSettings
from sirius.infrastructure.local_voice_installation import (
    listening_model_complete,
    listening_model_dir,
)
from sirius.ports.local_voice import VoiceUnavailable

#: Cómo se baja un modelo de faster-whisper: ``download_model(nombre, output_dir=...)``.
Download = Callable[..., object]


def download_listening_model(
    settings: LocalVoiceSettings, folder: Path, download: Download | None = None
) -> None:
    """Baja el modelo de oír de los ajustes a ``folder``, y solo lo deja ahí si está entero."""
    fetch = download
    if fetch is None:
        from faster_whisper import download_model

        fetch = download_model
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


def main() -> int:
    settings = LocalVoiceSettings()
    folder = listening_model_dir(settings)
    model = settings.listening_model.value
    if listening_model_complete(folder):
        print(f"[OK]    El modelo de oír (faster-whisper {model}) ya está en {folder}")
    else:
        print(f"Bajando el modelo de oír (faster-whisper {model}, unos 500 MB). Solo esta vez.")
        try:
            download_listening_model(settings, folder)
        except Exception as error:
            print(f"[FALLA] No se pudo bajar el modelo: {error}")
            return 1
        print(f"[OK]    Modelo bajado a {folder}")
    print("Comprobando que el oído carga...")
    try:
        load_listening_engines(folder)
    except VoiceUnavailable as error:
        print(f"[FALLA] El oído no carga: {error.reason}")
        return 1
    print("[OK]    Listo. Para probarlo: uv run --extra voz sirius-oye")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
