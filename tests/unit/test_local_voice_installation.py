"""Qué necesita instalado la voz del robot, y la orden que lo instala (ADR-242).

Sirius mira que el modelo de oír esté entero antes de abrir el micro; si no, dice la
orden. La orden baja el modelo a una carpeta aparte y solo lo pone en su sitio cuando
está entero, así que una descarga cortada nunca parece un modelo instalado.
"""

from __future__ import annotations

import importlib.metadata
import re
import sys
import tomllib
import types
from pathlib import Path

import pytest

import sirius.install_local_voice as install_local_voice
from sirius.config.local_voice import LocalVoiceSettings
from sirius.infrastructure.local_voice_installation import (
    INSTALL_COMMAND,
    VOICE_DISTRIBUTIONS,
    LocalVoiceInstallation,
    listening_model_complete,
    voice_distributions_missing,
    voice_models_dir,
)
from sirius.infrastructure.paths import resolve_paths
from sirius.install_local_voice import download_listening_model
from sirius.ports.local_voice import VoiceUnavailable


@pytest.fixture
def bibliotecas_bien(monkeypatch: pytest.MonkeyPatch) -> None:
    """Las bibliotecas de la voz están y cargan, como tras `uv run --extra voz`."""
    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", lambda: ())
    monkeypatch.setattr(install_local_voice, "check_listening_libraries", lambda: None)


#: Lo que lee faster-whisper 1.2.1 de la carpeta de un modelo (``WhisperModel`` y
#: ``ctranslate2``), escrito aquí y no copiado de Sirius: si Sirius dejara de pedir uno,
#: estas pruebas lo verían. Sin ``tokenizer.json``, faster-whisper lo pide a internet.
#: Lo que la orden ya no dice al fallar: son remedios adivinados, y no sabe si sirven
#: (rondas 2, 4, 5, 8 y 9 de Codex sobre la PR #687).
_REMEDIOS_ADIVINADOS = ("repetirla", "ciérralo", "vuelve a ejecutar")


def _sin_remedios_adivinados(salida: str) -> None:
    assert not [r for r in _REMEDIOS_ADIVINADOS if r in salida], salida


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


@pytest.mark.usefixtures("bibliotecas_bien")
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


@pytest.mark.usefixtures("bibliotecas_bien")
def test_sin_modelo_lo_baja_y_comprueba_que_carga(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    carpeta = LocalVoiceInstallation(LocalVoiceSettings()).listening_model_dir
    bajados: list[Path] = []
    cargados: list[Path] = []

    def baja(ajustes: LocalVoiceSettings, carpeta: Path) -> None:
        bajados.append(carpeta)

    monkeypatch.setattr(install_local_voice, "download_listening_model", baja)
    monkeypatch.setattr(install_local_voice, "load_listening_engines", cargados.append)

    assert install_local_voice.main() == 0

    assert bajados == [carpeta]
    assert cargados == [carpeta]
    assert "sirius-oye" in capsys.readouterr().out


@pytest.mark.usefixtures("bibliotecas_bien")
def test_un_modelo_que_esta_no_se_vuelve_a_bajar_aunque_no_cargue(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Ronda 5 de Codex sobre la PR #687: si no carga porque el ordenador no puede (sin
    # memoria, un motor que no admite), bajarlo otra vez gasta 500 MB y vuelve a fallar.
    # La orden no puede distinguirlo de un fichero roto, así que no lo baja otra vez y
    # dice la causa.
    _pon_modelo(LocalVoiceInstallation(LocalVoiceSettings()).listening_model_dir)

    def no_baja(*args: object) -> None:
        raise AssertionError("ha vuelto a bajar un modelo que ya estaba")

    def no_carga(carpeta: Path) -> None:
        raise VoiceUnavailable("el modelo de oír no carga (Unable to allocate memory)")

    monkeypatch.setattr(install_local_voice, "download_listening_model", no_baja)
    monkeypatch.setattr(install_local_voice, "load_listening_engines", no_carga)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "Unable to allocate memory" in salida
    _sin_remedios_adivinados(salida)


@pytest.mark.usefixtures("bibliotecas_bien")
def test_si_el_oido_no_carga_la_orden_acaba_en_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pon_modelo(LocalVoiceInstallation(LocalVoiceSettings()).listening_model_dir)

    def no_carga(carpeta: Path) -> None:
        raise VoiceUnavailable("INVALID_PROTOBUF")

    monkeypatch.setattr(install_local_voice, "load_listening_engines", no_carga)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "INVALID_PROTOBUF" in salida
    _sin_remedios_adivinados(salida)


@pytest.mark.usefixtures("bibliotecas_bien")
def test_si_no_se_puede_bajar_la_orden_acaba_en_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def sin_internet(*args: object) -> None:
        raise ConnectionError("sin internet")

    monkeypatch.setattr(install_local_voice, "download_listening_model", sin_internet)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    # Ronda 9 de Codex sobre la PR #687: cerrar Sirius no arregla quedarse sin internet,
    # un 403 ni el disco lleno. Se dice la causa, sin adivinar el remedio.
    assert "sin internet" in salida
    _sin_remedios_adivinados(salida)


def _biblioteca_rota(monkeypatch: pytest.MonkeyPatch) -> None:
    def rota() -> None:
        raise VoiceUnavailable("sounddevice no carga (PortAudio library not found)")

    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", lambda: ())
    monkeypatch.setattr(install_local_voice, "check_listening_libraries", rota)


def test_con_una_biblioteca_rota_baja_igual_el_modelo_que_falta_y_lo_dice(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Ronda 8 de Codex sobre la PR #687: Sirius aconseja la orden porque falta el modelo,
    # y la orden se paraba en la biblioteca rota sin bajarlo. Lo que falta lo pone siempre.
    _biblioteca_rota(monkeypatch)
    bajados: list[Path] = []

    def baja(ajustes: LocalVoiceSettings, carpeta: Path) -> None:
        bajados.append(carpeta)

    monkeypatch.setattr(install_local_voice, "download_listening_model", baja)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert bajados == [LocalVoiceInstallation(LocalVoiceSettings()).listening_model_dir]
    assert "PortAudio" in salida
    _sin_remedios_adivinados(salida)


def test_con_el_modelo_puesto_y_una_biblioteca_rota_no_baja_nada_y_lo_dice(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _biblioteca_rota(monkeypatch)
    _pon_modelo(LocalVoiceInstallation(LocalVoiceSettings()).listening_model_dir)

    def no_baja(*args: object) -> None:
        raise AssertionError("ha vuelto a bajar un modelo que ya estaba")

    monkeypatch.setattr(install_local_voice, "download_listening_model", no_baja)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "PortAudio" in salida
    _sin_remedios_adivinados(salida)


def test_si_faster_whisper_no_carga_al_ir_a_bajar_falla_como_la_voz_y_no_tumba_la_orden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Falle como falle: en Windows, una DLL de CTranslate2 puede fallar con algo que no es
    # ImportError.
    roto = types.ModuleType("faster_whisper")

    def __getattr__(nombre: str) -> object:
        raise RuntimeError("DLL load failed while importing _ext")

    roto.__getattr__ = __getattr__  # type: ignore[method-assign]
    monkeypatch.setitem(sys.modules, "faster_whisper", roto)

    with pytest.raises(VoiceUnavailable) as fallo:
        install_local_voice._faster_whisper_download()

    assert "DLL load failed" in fallo.value.reason


@pytest.mark.usefixtures("bibliotecas_bien")
def test_si_faster_whisper_no_carga_dice_que_no_puede_bajar_el_modelo_y_por_que(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_carga() -> object:
        raise VoiceUnavailable("faster_whisper no carga ([WinError 126])")

    monkeypatch.setattr(install_local_voice, "_faster_whisper_download", no_carga)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "No se puede bajar el modelo: faster_whisper no carga ([WinError 126])" in salida
    _sin_remedios_adivinados(salida)


# --- Las bibliotecas del extra: la orden mira si están como lo mira uv ---------------
#
# Si faltan, es que la orden no se ejecutó como se escribe: lo dice, con cómo escribirla.
# Una distribución está si tiene su carpeta de metadatos, aunque esté dañada (ronda 7 de
# Codex sobre la PR #687).


def test_las_distribuciones_que_se_miran_son_las_del_extra_voz() -> None:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    extra = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"][
        "optional-dependencies"
    ]["voz"]
    nombres = {re.split(r"[^A-Za-z0-9._-]", requisito, maxsplit=1)[0] for requisito in extra}

    assert {n.lower().replace("_", "-") for n in nombres} == set(VOICE_DISTRIBUTIONS)


def test_una_distribucion_falta_solo_si_no_tiene_carpeta_de_metadatos(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Como la del hallazgo: con METADATA pero sin RECORD ni top_level.txt. uv la ve
    # instalada y no la reinstala, así que no falta.
    danada = tmp_path / "demo_pkg-1.0.dist-info"
    danada.mkdir()
    (danada / "METADATA").write_text("Metadata-Version: 2.1\nName: demo-pkg\nVersion: 1.0\n")
    (tmp_path / "sin_metadata-2.0.dist-info").mkdir()
    monkeypatch.syspath_prepend(str(tmp_path))

    nombres = ("demo-pkg", "sin-metadata", "no-esta-en-este-ordenador")

    assert voice_distributions_missing(nombres) == ("no-esta-en-este-ordenador",)


def test_unos_metadatos_que_no_se_pueden_leer_no_cuentan_como_que_falta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def ilegibles(nombre: str) -> importlib.metadata.Distribution:
        raise OSError("METADATA ilegible")

    monkeypatch.setattr(importlib.metadata, "distribution", ilegibles)

    assert voice_distributions_missing(("numpy",)) == ()


@pytest.mark.usefixtures("bibliotecas_bien")
def test_sin_las_bibliotecas_del_extra_la_orden_dice_como_escribirla_y_no_baja_nada(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def no_baja(*args: object) -> None:
        raise AssertionError("ha bajado el modelo sin las bibliotecas")

    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", lambda: ("numpy",))
    monkeypatch.setattr(install_local_voice, "download_listening_model", no_baja)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "numpy" in salida
    assert INSTALL_COMMAND in salida
