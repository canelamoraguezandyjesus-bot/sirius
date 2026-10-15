"""Lo que la voz del robot necesita instalado en este ordenador, y la orden que lo instala.

ADR-242. Las bibliotecas van en el extra ``voz`` de ``pyproject.toml``, y el modelo de
faster-whisper en ``modelos/voz`` de la carpeta de datos de siempre (en Windows,
``%LOCALAPPDATA%\\sirius``), fija como la de los ajustes aunque el propietario haya movido
sus datos: la orden de instalar y Sirius la encuentran sin mirar nada más. Silero y Smart
Turn vienen dentro de Pipecat, con la biblioteca.

Aquí no se baja nada: solo se mira qué hay. Lo único que baja modelos es la orden de
instalar, ``sirius.install_local_voice``, que ejecuta el propietario.

La orden de instalar mira si faltan las distribuciones del extra, por su nombre, por su
carpeta de metadatos, como las lista uv: si faltan es que no se ejecutó como se escribe.
Sirius no lo mira antes de cargar: si algo no carga, aconseja la orden igual, que pone al
día lo que haga falta y dice qué es si es otra cosa (ronda 8 de Codex sobre la PR #687).
"""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

from sirius.config.local_voice import LocalVoiceSettings
from sirius.infrastructure.paths import resolve_paths

#: La orden que instala la voz, tal como se pega en PowerShell en la carpeta de Sirius.
#: Instala el extra ``voz`` y baja el modelo; ``uv run`` no quita después lo instalado.
INSTALL_COMMAND = "uv run --extra voz sirius-instala-la-voz"

#: Lo que faster-whisper lee de la carpeta de un modelo. Sin ``tokenizer.json`` no falla:
#: lo pide a internet desde Rust (``tokenizers.Tokenizer.from_pretrained``), donde no lo
#: ve nadie, así que sin él el oído no arranca.
LISTENING_MODEL_FILES = ("model.bin", "config.json", "tokenizer.json")
#: Y su vocabulario, que según el modelo es ``vocabulary.txt`` o ``vocabulary.json``.
LISTENING_MODEL_VOCABULARY = "vocabulary.*"
#: Las distribuciones que pide el extra ``voz`` de ``pyproject.toml``; una prueba mira que
#: sean esas.
VOICE_DISTRIBUTIONS = ("pipecat-ai", "faster-whisper", "sounddevice", "numpy")


def voice_distributions_missing(names: tuple[str, ...] = VOICE_DISTRIBUTIONS) -> tuple[str, ...]:
    """Las de ``names`` que no están instaladas: sin carpeta de metadatos con su nombre.

    Es lo que mira uv para saber si una distribución está. Una que está, aunque esté
    dañada, cuenta como instalada: ``uv run --extra voz`` no la reinstala, así que no se
    promete; si sus metadatos no se pueden leer, tampoco.
    """
    return tuple(name for name in names if _absent(name))


def _absent(name: str) -> bool:
    """Si no hay carpeta de metadatos con ese nombre. Ilegible no es «no está»."""
    try:
        importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return True
    except Exception:
        return False
    return False


def voice_models_dir() -> Path:
    """La carpeta de los modelos de la voz, en la carpeta de datos por defecto."""
    return resolve_paths().data_dir / "modelos" / "voz"


def listening_model_dir(settings: LocalVoiceSettings, models_dir: Path | None = None) -> Path:
    """La carpeta del modelo de faster-whisper que eligen los ajustes."""
    base = models_dir if models_dir is not None else voice_models_dir()
    return base / f"faster-whisper-{settings.listening_model.value}"


def listening_model_complete(folder: Path) -> bool:
    """Si ``folder`` tiene todo lo que faster-whisper lee de un modelo."""
    return all((folder / name).is_file() for name in LISTENING_MODEL_FILES) and any(
        path.is_file() for path in folder.glob(LISTENING_MODEL_VOCABULARY)
    )


class LocalVoiceInstallation:
    """Mira en este ordenador si está el modelo de oír de los ajustes."""

    def __init__(self, settings: LocalVoiceSettings, models_dir: Path | None = None) -> None:
        self._settings = settings
        self._models_dir = models_dir

    @property
    def install_command(self) -> str:
        return INSTALL_COMMAND

    @property
    def listening_model_dir(self) -> Path:
        return listening_model_dir(self._settings, self._models_dir)

    def missing(self) -> tuple[str, ...]:
        if listening_model_complete(self.listening_model_dir):
            return ()
        model = self._settings.listening_model.value
        return (f"el modelo de oír (faster-whisper {model})",)
