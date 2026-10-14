"""Qué necesita instalado la voz del robot, y la orden que lo instala (ADR-242).

Sirius mira que el modelo de oír esté entero antes de abrir el micro; si no, dice la
orden. La orden baja el modelo a una carpeta aparte y solo lo pone en su sitio cuando
está entero, así que una descarga cortada nunca parece un modelo instalado.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import sirius.install_local_voice as install_local_voice
from sirius.config.local_voice import LocalVoiceSettings
from sirius.infrastructure.local_voice_installation import (
    INSTALL_COMMAND,
    LocalVoiceInstallation,
    listening_model_complete,
    voice_models_dir,
)
from sirius.infrastructure.paths import resolve_paths
from sirius.install_local_voice import download_listening_model
from sirius.ports.local_voice import VoiceUnavailable

#: Lo que lee faster-whisper 1.2.1 de la carpeta de un modelo (``WhisperModel`` y
#: ``ctranslate2``), escrito aquí y no copiado de Sirius: si Sirius dejara de pedir uno,
#: estas pruebas lo verían. Sin ``tokenizer.json``, faster-whisper lo pide a internet.
_MODELO_ENTERO = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")


def _pon_modelo(carpeta: Path, ficheros: tuple[str, ...] = _MODELO_ENTERO) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in ficheros:
        (carpeta / nombre).write_bytes(b"pesos")


def test_los_modelos_viven_en_la_carpeta_de_datos_de_siempre() -> None:
    assert voice_models_dir() == resolve_paths().data_dir / "modelos" / "voz"
    instalacion = LocalVoiceInstallation(LocalVoiceSettings())
    assert instalacion.listening_model_dir == voice_models_dir() / "faster-whisper-small"


def test_con_el_modelo_entero_no_falta_nada() -> None:
    instalacion = LocalVoiceInstallation(LocalVoiceSettings())
    _pon_modelo(instalacion.listening_model_dir)

    assert instalacion.missing() == ()
    assert instalacion.install_command == INSTALL_COMMAND


@pytest.mark.parametrize("quitado", _MODELO_ENTERO)
def test_falta_el_modelo_si_le_falta_cualquiera_de_sus_ficheros(
    tmp_path: Path, quitado: str
) -> None:
    instalacion = LocalVoiceInstallation(LocalVoiceSettings(), tmp_path)
    _pon_modelo(instalacion.listening_model_dir, tuple(n for n in _MODELO_ENTERO if n != quitado))

    assert instalacion.missing() == ("el modelo de oír (faster-whisper small)",)


def test_el_vocabulario_vale_en_texto_o_en_json(tmp_path: Path) -> None:
    _pon_modelo(tmp_path, ("model.bin", "config.json", "tokenizer.json", "vocabulary.json"))

    assert listening_model_complete(tmp_path)


def test_la_orden_se_pega_tal_cual_en_powershell() -> None:
    assert INSTALL_COMMAND == "uv run --extra voz sirius-instala-la-voz"


# --- La orden de instalar -----------------------------------------------------------


def test_baja_el_modelo_aparte_y_lo_pone_en_su_sitio_entero(tmp_path: Path) -> None:
    pedidos: list[tuple[str, str]] = []

    def baja(nombre: str, *, output_dir: str) -> str:
        pedidos.append((nombre, output_dir))
        _pon_modelo(Path(output_dir))
        return output_dir

    carpeta = tmp_path / "faster-whisper-small"
    download_listening_model(LocalVoiceSettings(), carpeta, baja)

    assert pedidos == [("small", str(tmp_path / "faster-whisper-small.a-medias"))]
    assert listening_model_complete(carpeta)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["faster-whisper-small"]


def test_una_descarga_a_medias_no_deja_nada_que_parezca_instalado(tmp_path: Path) -> None:
    carpeta = tmp_path / "faster-whisper-small"

    def baja_a_medias(nombre: str, *, output_dir: str) -> None:
        _pon_modelo(Path(output_dir), ("model.bin",))

    with pytest.raises(RuntimeError, match="no trajo todos los ficheros"):
        download_listening_model(LocalVoiceSettings(), carpeta, baja_a_medias)

    assert list(tmp_path.iterdir()) == []


def test_una_descarga_cortada_deja_el_modelo_que_ya_habia(tmp_path: Path) -> None:
    carpeta = tmp_path / "faster-whisper-small"
    _pon_modelo(carpeta)

    def se_corta(nombre: str, *, output_dir: str) -> None:
        Path(output_dir).mkdir(parents=True)
        raise ConnectionError("se fue internet")

    with pytest.raises(ConnectionError):
        download_listening_model(LocalVoiceSettings(), carpeta, se_corta)

    assert listening_model_complete(carpeta)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["faster-whisper-small"]


def test_con_el_modelo_ya_instalado_no_baja_nada_y_comprueba_que_carga(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pon_modelo(LocalVoiceInstallation(LocalVoiceSettings()).listening_model_dir)
    cargados: list[Path] = []

    def no_baja(*args: object) -> None:
        raise AssertionError("ha intentado bajar un modelo que ya estaba")

    monkeypatch.setattr(install_local_voice, "download_listening_model", no_baja)
    monkeypatch.setattr(install_local_voice, "load_listening_engines", cargados.append)

    assert install_local_voice.main() == 0

    assert cargados == [LocalVoiceInstallation(LocalVoiceSettings()).listening_model_dir]
    assert "sirius-oye" in capsys.readouterr().out


def test_si_el_oido_no_carga_la_orden_acaba_en_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pon_modelo(LocalVoiceInstallation(LocalVoiceSettings()).listening_model_dir)

    def no_carga(carpeta: Path) -> None:
        raise VoiceUnavailable("falta pipecat", fixed_by_install=True)

    monkeypatch.setattr(install_local_voice, "load_listening_engines", no_carga)

    assert install_local_voice.main() == 1
    assert "falta pipecat" in capsys.readouterr().out


def test_si_no_se_puede_bajar_la_orden_acaba_en_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def sin_internet(*args: object) -> None:
        raise ConnectionError("sin internet")

    monkeypatch.setattr(install_local_voice, "download_listening_model", sin_internet)

    assert install_local_voice.main() == 1
    assert "sin internet" in capsys.readouterr().out
