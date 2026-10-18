"""Lo que la voz del robot necesita instalado en este ordenador, y la orden que lo instala.

ADR-242, ADR-243 y ADR-246. Las bibliotecas van en el extra ``voz`` de ``pyproject.toml``,
y las de la voz de personaje, Chatterbox, en el extra ``personaje``. El modelo de
faster-whisper, las voces de Piper y la de Chatterbox van en ``modelos/voz`` de la carpeta
de datos de siempre (en Windows, ``%LOCALAPPDATA%\\sirius``), fija como la de los ajustes
aunque el propietario haya movido sus datos: la orden de instalar y Sirius la encuentran
sin mirar nada más. Silero y Smart Turn vienen dentro de Pipecat, con la biblioteca.

Aquí no se baja nada: solo se mira qué hay. Lo único que baja modelos es la orden de
instalar, ``sirius.install_local_voice``, que ejecuta el propietario.

La orden de instalar mira si faltan las distribuciones del extra, por su nombre, por su
carpeta de metadatos, como las lista uv: si faltan es que no se ejecutó como se escribe.
Sirius no lo mira antes de cargar: si algo no carga, aconseja la orden igual, que pone al
día lo que haga falta y dice qué es si es otra cosa (ronda 8 de Codex sobre la PR #687).
"""

from __future__ import annotations

import importlib.metadata
from collections.abc import Callable
from pathlib import Path

from sirius.config.local_voice import LocalVoiceSettings, SpeakingVoice
from sirius.infrastructure.paths import resolve_paths

#: La orden que instala la voz, tal como se pega en PowerShell en la carpeta de Sirius.
#: Instala el extra ``voz`` y baja el modelo; ``uv run`` no quita después lo instalado.
#: Con ``--link-mode=copy``, como toda orden de uv que se le enseña: su carpeta de Sirius
#: está en OneDrive, y así uv copia lo que instala en vez de enlazarlo a su caché
#: (punto 19 de la incidencia #696).
INSTALL_COMMAND = "uv run --link-mode=copy --extra voz sirius-instala-la-voz"
#: La misma orden con la voz de personaje: instala además el extra ``personaje`` y baja la
#: voz de Chatterbox. Pesa mucho más, y sin ella Sirius oye y habla igual (ADR-246).
CHARACTER_INSTALL_COMMAND = (
    "uv run --link-mode=copy --extra voz --extra personaje sirius-instala-la-voz"
)

#: Lo que faster-whisper lee de la carpeta de un modelo. Sin ``tokenizer.json`` no falla:
#: lo pide a internet desde Rust (``tokenizers.Tokenizer.from_pretrained``), donde no lo
#: ve nadie, así que sin él el oído no arranca.
LISTENING_MODEL_FILES = ("model.bin", "config.json", "tokenizer.json")
#: Y su vocabulario, que según el modelo es ``vocabulary.txt`` o ``vocabulary.json``.
LISTENING_MODEL_VOCABULARY = "vocabulary.*"
#: Las distribuciones que pide el extra ``voz`` de ``pyproject.toml``; una prueba mira que
#: sean esas. ``livekit`` trae la cancelación de eco (ADR-245): sin ella oye y habla igual,
#: pero la orden de instalar la pone con lo demás.
VOICE_DISTRIBUTIONS = (
    "pipecat-ai",
    "faster-whisper",
    "sounddevice",
    "numpy",
    "piper-tts",
    "livekit",
)
#: Las que pide el extra ``personaje``: Chatterbox, con torch detrás (ADR-246).
CHARACTER_DISTRIBUTIONS = ("chatterbox-tts",)
#: Lo que Chatterbox multilingüe lee de su carpeta (``ChatterboxMultilingualTTS.from_local``):
#: sus pesos, su tokenizador y ``conds.pt``, su voz de serie, que es la de personaje.
CHARACTER_VOICE_FILES = (
    "ve.pt",
    "t3_mtl23ls_v2.safetensors",
    "s3gen.pt",
    "grapheme_mtl_merged_expanded_v1.json",
    "conds.pt",
)


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


def speaking_voice_dir(settings: LocalVoiceSettings, models_dir: Path | None = None) -> Path:
    """La carpeta de la voz que eligen los ajustes, una por voz: las de Piper bajo ``piper``
    y la de personaje bajo ``chatterbox``."""
    return voice_dir(settings.speaking_voice, models_dir)


def voice_dir(voice: SpeakingVoice, models_dir: Path | None = None) -> Path:
    """La carpeta de ``voice``."""
    base = models_dir if models_dir is not None else voice_models_dir()
    return base / ("chatterbox" if voice.is_character else "piper") / voice.value


def voice_model(voice: SpeakingVoice, models_dir: Path | None = None) -> Path:
    """Lo que se le da a cargar a la voz: el ``.onnx`` de Piper, o la carpeta de Chatterbox.

    Su nombre, sin ``.onnx``, es el de la voz.
    """
    folder = voice_dir(voice, models_dir)
    return folder if voice.is_character else folder / f"{voice.value}.onnx"


def speaking_voice_files(voice: str) -> tuple[str, ...]:
    """Lo que lee una voz de su carpeta: de Piper, el modelo y, a su lado, su
    configuración; de Chatterbox, ``CHARACTER_VOICE_FILES``."""
    if voice == SpeakingVoice.CHARACTER.value:
        return CHARACTER_VOICE_FILES
    return (f"{voice}.onnx", f"{voice}.onnx.json")


def speaking_voice_complete(folder: Path, voice: str) -> bool:
    """Si ``folder`` tiene todos los ficheros de la voz ``voice``."""
    return all((folder / name).is_file() for name in speaking_voice_files(voice))


def voice_label(voice: SpeakingVoice) -> str:
    """Cómo se le dice al propietario qué voz falta: de Piper con su nombre, o la de
    personaje. Fuera de la prueba a ciegas, que no lleva nombres."""
    return "la voz de personaje (Chatterbox)" if voice.is_character else f"la voz (Piper {voice})"


def voices_missing(models_dir: Path | None = None) -> tuple[SpeakingVoice, ...]:
    """Las voces de la prueba a ciegas que no están enteras en este ordenador."""
    return tuple(
        voice
        for voice in SpeakingVoice
        if not speaking_voice_complete(voice_dir(voice, models_dir), voice.value)
    )


class LocalVoiceInstallation:
    """Mira en este ordenador si están el modelo de oír y la voz de los ajustes."""

    def __init__(self, settings: LocalVoiceSettings, models_dir: Path | None = None) -> None:
        self._settings = settings
        self._models_dir = models_dir

    @property
    def install_command(self) -> str:
        return (
            CHARACTER_INSTALL_COMMAND
            if self._settings.speaking_voice.is_character
            else (INSTALL_COMMAND)
        )

    @property
    def listening_model_dir(self) -> Path:
        return listening_model_dir(self._settings, self._models_dir)

    @property
    def speaking_voice_dir(self) -> Path:
        return speaking_voice_dir(self._settings, self._models_dir)

    @property
    def speaking_voice_model(self) -> Path:
        """Lo que se le da a cargar a la voz: el ``.onnx`` de Piper, o la carpeta de
        Chatterbox."""
        return voice_model(self._settings.speaking_voice, self._models_dir)

    def missing(self) -> tuple[str, ...]:
        missing: list[str] = []
        if not listening_model_complete(self.listening_model_dir):
            model = self._settings.listening_model.value
            missing.append(f"el modelo de oír (faster-whisper {model})")
        voice = self._settings.speaking_voice
        if not speaking_voice_complete(self.speaking_voice_dir, voice.value):
            missing.append(voice_label(voice))
        return tuple(missing)


def voice_test_missing(
    models_dir: Path | None = None, *, libraries: bool = True
) -> tuple[str, ...]:
    """Lo que falta para la prueba de voces, dicho para él con la orden que lo instala; vacío
    si están todas (pieza F, ADR-246). Sin una, la hoja no se abre a medias.

    Con ``libraries`` mira además la biblioteca de la voz de personaje, la del extra
    ``personaje``: sus ficheros pueden seguir aquí con el entorno rehecho sin ella (ronda 1
    de Codex sobre la PR #691). Que falte la instala la orden, así que no se adivina nada.
    Sin ``libraries`` no la mira, para quien carga las voces con otra cosa.
    """
    missing = [voice_label(voice) for voice in voices_missing(models_dir)]
    absent = voice_distributions_missing(CHARACTER_DISTRIBUTIONS) if libraries else ()
    if absent:
        missing.append(f"la biblioteca de la voz de personaje ({', '.join(absent)})")
    if not missing:
        return ()
    names = missing[0] if len(missing) == 1 else f"{', '.join(missing[:-1])} y {missing[-1]}"
    return (
        f"Para la prueba de voces me falta instalar {names} en este ordenador. Ejecuta en "
        f"PowerShell, dentro de la carpeta de Sirius: {CHARACTER_INSTALL_COMMAND} .",
    )


class ChosenVoiceInstallation:
    """Lo instalado para oír y hablar con la voz que digan los ajustes en cada momento: la
    que él elige vale desde que la elige, sin volver a abrir Sirius (pieza F, ADR-246)."""

    def __init__(
        self, settings: Callable[[], LocalVoiceSettings], models_dir: Path | None = None
    ) -> None:
        self._settings = settings
        self._models_dir = models_dir

    def now(self) -> LocalVoiceInstallation:
        """La instalación con los ajustes de ahora."""
        return LocalVoiceInstallation(self._settings(), self._models_dir)

    @property
    def install_command(self) -> str:
        return self.now().install_command

    @property
    def listening_model_dir(self) -> Path:
        return self.now().listening_model_dir

    @property
    def speaking_voice_model(self) -> Path:
        return self.now().speaking_voice_model

    def missing(self) -> tuple[str, ...]:
        return self.now().missing()
