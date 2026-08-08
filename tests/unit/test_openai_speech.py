"""El WAV que llega del proveedor tiene que poder reproducirse entero.

La síntesis se genera mientras se envía, así que el encabezado se escribe antes
de saber cuánto dura y llega con tamaños de relleno. En la primera prueba real
en Windows eso salió por consola como *«Ignoring maximum wav data size, file may
be invalid»* y *«Packet corrupt»*, con la duración estimada por el bitrate en
lugar de leída del archivo.

Estas pruebas fijan las dos mitades del acuerdo: se corrige lo que es
imposible, y no se toca nada más. Lo segundo importa tanto como lo primero,
porque «arreglar» un WAV correcto es estropearlo.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import openai

from sirius.adapters.audio.openai_speech import OpenAISpeech, repair_wav_sizes
from sirius.ports.text_to_speech import SpeechError, SpeechRequest, SynthesizedSpeech

_PLACEHOLDER = 0xFFFFFFFF
_AUDIO = b"\x01\x02" * 64


def _fmt_chunk() -> bytes:
    body = (
        b"\x01\x00"  # PCM
        b"\x01\x00"  # un canal
        + (24_000).to_bytes(4, "little")
        + (48_000).to_bytes(4, "little")
        + b"\x02\x00"
        + b"\x10\x00"
    )
    return b"fmt " + len(body).to_bytes(4, "little") + body


def _wav(
    audio: bytes = _AUDIO,
    *,
    declared_data_size: int | None = None,
    declared_riff_size: int | None = None,
    before_data: bytes = b"",
    after_data: bytes = b"",
) -> bytes:
    data_size = len(audio) if declared_data_size is None else declared_data_size
    body = (
        b"WAVE"
        + _fmt_chunk()
        + before_data
        + b"data"
        + data_size.to_bytes(4, "little")
        + audio
        + after_data
    )
    riff_size = len(body) if declared_riff_size is None else declared_riff_size
    return b"RIFF" + riff_size.to_bytes(4, "little") + body


def _declared_sizes(payload: bytes) -> tuple[int, int]:
    riff = int.from_bytes(payload[4:8], "little")
    index = payload.index(b"data")
    return riff, int.from_bytes(payload[index + 4 : index + 8], "little")


def test_a_placeholder_size_is_replaced_by_the_bytes_that_really_arrived() -> None:
    repaired = repair_wav_sizes(
        _wav(declared_data_size=_PLACEHOLDER, declared_riff_size=_PLACEHOLDER)
    )

    riff_size, data_size = _declared_sizes(repaired)
    assert data_size == len(_AUDIO)
    assert riff_size == len(repaired) - 8
    # El audio no se toca: solo se reescriben los cuatro bytes del tamaño.
    assert repaired[-len(_AUDIO) :] == _AUDIO


def test_a_zero_size_also_counts_as_placeholder() -> None:
    """Cero es la otra forma de decir «todavía no sé cuánto»."""
    repaired = repair_wav_sizes(_wav(declared_data_size=0))

    _, data_size = _declared_sizes(repaired)
    assert data_size == len(_AUDIO)


def test_a_coherent_file_comes_back_untouched() -> None:
    original = _wav()

    assert repair_wav_sizes(original) == original


def test_audio_followed_by_another_chunk_is_never_stretched() -> None:
    """Un tamaño menor que lo disponible es legítimo, no un marcador.

    Después de ``data`` puede venir otro trozo. Estirar el audio hasta el final
    del archivo se tragaría ese trozo como si fuera sonido.
    """
    original = _wav(after_data=b"LIST" + (4).to_bytes(4, "little") + b"INFO")

    assert repair_wav_sizes(original) == original


def test_the_audio_is_found_behind_another_chunk() -> None:
    extra = b"LIST" + (4).to_bytes(4, "little") + b"INFO"
    repaired = repair_wav_sizes(_wav(declared_data_size=_PLACEHOLDER, before_data=extra))

    _, data_size = _declared_sizes(repaired)
    assert data_size == len(_AUDIO)


def test_an_odd_chunk_is_walked_with_its_padding_byte() -> None:
    """Los trozos ocupan un número par de bytes: uno impar lleva relleno.

    Sin contar ese byte, el recorrido se desalinea y ``data`` no se encuentra.
    """
    odd = b"LIST" + (5).to_bytes(4, "little") + b"INFOx" + b"\x00"
    repaired = repair_wav_sizes(_wav(declared_data_size=_PLACEHOLDER, before_data=odd))

    _, data_size = _declared_sizes(repaired)
    assert data_size == len(_AUDIO)


def test_something_that_is_not_a_wav_comes_back_as_it_arrived() -> None:
    for payload in (b"", b"RIFF", b"no soy un wav", b"RIFF\x00\x00\x00\x00OGGS"):
        assert repair_wav_sizes(payload) == payload


def test_a_header_that_cannot_be_walked_is_left_alone() -> None:
    """Ante un encabezado ilegible se prefiere no tocar a adivinar."""
    broken = (
        b"RIFF"
        + (99).to_bytes(4, "little")
        + b"WAVE"
        + b"fmt "
        + _PLACEHOLDER.to_bytes(4, "little")
    )

    assert repair_wav_sizes(broken) == broken


def test_a_wav_without_audio_chunk_is_left_alone() -> None:
    header_only = b"RIFF" + (12).to_bytes(4, "little") + b"WAVE" + _fmt_chunk()

    assert repair_wav_sizes(header_only) == header_only


# --- Que la corrección esté escrita no basta: tiene que aplicarse ---------


class _StubResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class _StubSpeech:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _StubResponse:
        self.calls.append(kwargs)
        return _StubResponse(self._payload)


class _StubClient:
    """Lo mínimo del cliente de OpenAI que este adaptador usa. Sin red."""

    def __init__(self, payload: bytes) -> None:
        self.audio = SimpleNamespace(speech=_StubSpeech(payload))


def _synthesize(payload: bytes, directory: Path) -> SynthesizedSpeech | SpeechError:
    adapter = OpenAISpeech(cast(openai.OpenAI, _StubClient(payload)), directory)
    return adapter.synthesize(
        SpeechRequest(text="Hola.", voice="onyx", instructions="tono de prueba")
    )


def test_the_file_written_to_disk_already_has_the_sizes_fixed(tmp_path: Path) -> None:
    """El fallo que ya me comí una vez: código correcto que nadie llama."""
    result = _synthesize(_wav(declared_data_size=_PLACEHOLDER), tmp_path)

    assert isinstance(result, SynthesizedSpeech)
    _, data_size = _declared_sizes(result.audio_path.read_bytes())
    assert data_size == len(_AUDIO)


def test_the_temporary_is_named_so_the_startup_sweep_finds_it(tmp_path: Path) -> None:
    """La limpieza de arranque barre un patrón común, y la voz tiene que caer ahí.

    Si el reproductor tenía el archivo abierto al intentar borrarlo —cosa que
    en Windows pasa—, el temporal sobrevive a la sesión. Lo recoge el siguiente
    arranque, pero solo si el nombre encaja con lo que se barre.
    """
    from sirius.adapters.audio.qt_capture import ORPHAN_PATTERN

    result = _synthesize(_wav(), tmp_path)

    assert isinstance(result, SynthesizedSpeech)
    assert result.audio_path in set(tmp_path.glob(ORPHAN_PATTERN))
