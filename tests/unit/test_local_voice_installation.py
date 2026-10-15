"""Qué necesita instalado la voz del robot, y la orden que lo instala (ADR-242, ADR-243).

Sirius mira que el modelo de oír y la voz de hablar estén enteros antes de abrir el micro;
si no, dice la orden. La orden baja cada uno a una carpeta aparte y solo lo pone en su
sitio cuando está entero, así que una descarga cortada nunca parece instalada.
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
    speaking_voice_complete,
    voice_distributions_missing,
    voice_models_dir,
)
from sirius.infrastructure.paths import resolve_paths
from sirius.install_local_voice import download_listening_model, download_speaking_voice
from sirius.ports.local_voice import VoiceUnavailable

#: La voz de los ajustes, como la nombra Piper.
_VOZ = "es_ES-davefx-medium"
_VOZ_ENTERA = (f"{_VOZ}.onnx", f"{_VOZ}.onnx.json")


def _pon_voz(carpeta: Path, ficheros: tuple[str, ...] = _VOZ_ENTERA) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in ficheros:
        (carpeta / nombre).write_bytes(b"voz")


@pytest.fixture(autouse=True)
def la_voz_esta(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Un ordenador con la voz de hablar puesta y que carga. Las pruebas del modelo de oír
    no la miran; las de la voz la quitan o la rompen. Devuelve lo que se cargó."""
    _pon_voz(LocalVoiceInstallation(LocalVoiceSettings()).speaking_voice_dir)
    cargadas: list[Path] = []
    monkeypatch.setattr(install_local_voice, "load_speaking_engines", cargadas.append)
    return cargadas


@pytest.fixture
def aparte(tmp_path: Path) -> Path:
    """Una carpeta vacía, fuera de la de datos, donde la voz ya puesta no se ve."""
    carpeta = tmp_path / "aparte"
    carpeta.mkdir()
    return carpeta


@pytest.fixture
def bibliotecas_bien(monkeypatch: pytest.MonkeyPatch) -> None:
    """Las bibliotecas de la voz están y cargan, como tras `uv run --extra voz`."""
    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", lambda: ())
    monkeypatch.setattr(install_local_voice, "check_listening_libraries", lambda: None)
    monkeypatch.setattr(install_local_voice, "check_speaking_libraries", lambda: None)


#: Lo que lee faster-whisper 1.2.1 de la carpeta de un modelo (``WhisperModel`` y
#: ``ctranslate2``), escrito aquí y no copiado de Sirius: si Sirius dejara de pedir uno,
#: estas pruebas lo verían. Sin ``tokenizer.json``, faster-whisper lo pide a internet.
#: Lo que la orden ya no dice al fallar: son remedios adivinados, y no sabe si sirven
#: (rondas 2, 4, 5, 8 y 9 de Codex sobre la PR #687).
_REMEDIOS_ADIVINADOS = ("repetirla", "ciérralo", "vuelve a ejecutar")


def _sin_remedios_adivinados(salida: str) -> None:
    assert not [r for r in _REMEDIOS_ADIVINADOS if r in salida.casefold()], salida


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
    _pon_voz(instalacion.speaking_voice_dir)

    assert instalacion.missing() == ("el modelo de oír (faster-whisper small)",)


def test_la_voz_vive_en_su_carpeta_dentro_de_los_modelos() -> None:
    instalacion = LocalVoiceInstallation(LocalVoiceSettings())

    assert instalacion.speaking_voice_dir == voice_models_dir() / "piper" / _VOZ
    assert instalacion.speaking_voice_model == instalacion.speaking_voice_dir / f"{_VOZ}.onnx"


@pytest.mark.parametrize("quitado", _VOZ_ENTERA)
def test_falta_la_voz_si_le_falta_cualquiera_de_sus_dos_ficheros(
    tmp_path: Path, quitado: str
) -> None:
    instalacion = LocalVoiceInstallation(LocalVoiceSettings(), tmp_path)
    _pon_modelo(instalacion.listening_model_dir)
    _pon_voz(instalacion.speaking_voice_dir, tuple(n for n in _VOZ_ENTERA if n != quitado))

    assert instalacion.missing() == (f"la voz (Piper {_VOZ})",)


def test_sin_nada_instalado_faltan_el_modelo_de_oir_y_la_voz(tmp_path: Path) -> None:
    instalacion = LocalVoiceInstallation(LocalVoiceSettings(), tmp_path)

    assert instalacion.missing() == (
        "el modelo de oír (faster-whisper small)",
        f"la voz (Piper {_VOZ})",
    )


def test_el_vocabulario_vale_en_texto_o_en_json(tmp_path: Path) -> None:
    _pon_modelo(tmp_path, ("model.bin", "config.json", "tokenizer.json", "vocabulary.json"))

    assert listening_model_complete(tmp_path)


def test_la_orden_se_pega_tal_cual_en_powershell() -> None:
    assert INSTALL_COMMAND == "uv run --extra voz sirius-instala-la-voz"


# --- La orden de instalar -----------------------------------------------------------


def test_baja_el_modelo_aparte_y_lo_pone_en_su_sitio_entero(aparte: Path) -> None:
    pedidos: list[tuple[str, str]] = []

    def baja(nombre: str, *, output_dir: str) -> str:
        pedidos.append((nombre, output_dir))
        _pon_modelo(Path(output_dir))
        return output_dir

    carpeta = aparte / "faster-whisper-small"
    download_listening_model(LocalVoiceSettings(), carpeta, baja)

    assert pedidos == [("small", str(aparte / "faster-whisper-small.a-medias"))]
    assert listening_model_complete(carpeta)
    assert sorted(p.name for p in aparte.iterdir()) == ["faster-whisper-small"]


def test_una_descarga_a_medias_no_deja_nada_que_parezca_instalado(aparte: Path) -> None:
    carpeta = aparte / "faster-whisper-small"

    def baja_a_medias(nombre: str, *, output_dir: str) -> None:
        _pon_modelo(Path(output_dir), ("model.bin",))

    with pytest.raises(RuntimeError, match="no trajo todos los ficheros"):
        download_listening_model(LocalVoiceSettings(), carpeta, baja_a_medias)

    assert list(aparte.iterdir()) == []


def test_una_descarga_cortada_deja_el_modelo_que_ya_habia(aparte: Path) -> None:
    carpeta = aparte / "faster-whisper-small"
    _pon_modelo(carpeta)

    def se_corta(nombre: str, *, output_dir: str) -> None:
        Path(output_dir).mkdir(parents=True)
        raise ConnectionError("se fue internet")

    with pytest.raises(ConnectionError):
        download_listening_model(LocalVoiceSettings(), carpeta, se_corta)

    assert listening_model_complete(carpeta)
    assert sorted(p.name for p in aparte.iterdir()) == ["faster-whisper-small"]


@pytest.mark.usefixtures("bibliotecas_bien")
def test_con_el_modelo_ya_instalado_no_baja_nada_y_comprueba_que_carga(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], la_voz_esta: list[Path]
) -> None:
    instalacion = LocalVoiceInstallation(LocalVoiceSettings())
    _pon_modelo(instalacion.listening_model_dir)
    cargados: list[Path] = []

    def no_baja(*args: object) -> None:
        raise AssertionError("ha intentado bajar un modelo que ya estaba")

    monkeypatch.setattr(install_local_voice, "download_listening_model", no_baja)
    monkeypatch.setattr(install_local_voice, "download_speaking_voice", no_baja)
    monkeypatch.setattr(install_local_voice, "load_listening_engines", cargados.append)

    assert install_local_voice.main() == 0

    assert cargados == [instalacion.listening_model_dir]
    assert la_voz_esta == [instalacion.speaking_voice_model]
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


# --- La voz de hablar (pieza C, ADR-243) ----------------------------------------------


def test_baja_la_voz_aparte_y_la_pone_en_su_sitio_entera(aparte: Path) -> None:
    pedidos: list[tuple[str, Path]] = []

    def baja(voz: str, carpeta: Path) -> None:
        pedidos.append((voz, carpeta))
        _pon_voz(carpeta)

    carpeta = aparte / _VOZ
    download_speaking_voice(LocalVoiceSettings(), carpeta, baja)

    assert pedidos == [(_VOZ, aparte / f"{_VOZ}.a-medias")]
    assert speaking_voice_complete(carpeta, _VOZ)
    assert sorted(p.name for p in aparte.iterdir()) == [_VOZ]


def test_una_voz_a_medias_no_deja_nada_que_parezca_instalado(aparte: Path) -> None:
    def baja_a_medias(voz: str, carpeta: Path) -> None:
        _pon_voz(carpeta, (f"{voz}.onnx",))

    with pytest.raises(RuntimeError, match="no trajo los dos ficheros"):
        download_speaking_voice(LocalVoiceSettings(), aparte / _VOZ, baja_a_medias)

    assert list(aparte.iterdir()) == []


def test_una_descarga_cortada_deja_la_voz_que_ya_habia(aparte: Path) -> None:
    carpeta = aparte / _VOZ
    _pon_voz(carpeta)

    def se_corta(voz: str, carpeta: Path) -> None:
        raise ConnectionError("se fue internet")

    with pytest.raises(ConnectionError):
        download_speaking_voice(LocalVoiceSettings(), carpeta, se_corta)

    assert speaking_voice_complete(carpeta, _VOZ)
    assert sorted(p.name for p in aparte.iterdir()) == [_VOZ]


@pytest.mark.usefixtures("bibliotecas_bien")
def test_sin_la_voz_la_baja_y_comprueba_que_carga_y_que_el_altavoz_se_abre(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], la_voz_esta: list[Path]
) -> None:
    instalacion = LocalVoiceInstallation(LocalVoiceSettings())
    _pon_modelo(instalacion.listening_model_dir)
    for nombre in _VOZ_ENTERA:
        (instalacion.speaking_voice_dir / nombre).unlink()
    bajadas: list[Path] = []

    def baja(ajustes: LocalVoiceSettings, carpeta: Path) -> None:
        bajadas.append(carpeta)

    monkeypatch.setattr(install_local_voice, "download_speaking_voice", baja)
    monkeypatch.setattr(install_local_voice, "load_listening_engines", lambda carpeta: None)

    assert install_local_voice.main() == 0

    assert bajadas == [instalacion.speaking_voice_dir]
    assert la_voz_esta == [instalacion.speaking_voice_model]
    salida = capsys.readouterr().out
    assert f"Bajando la voz (Piper {_VOZ}" in salida
    assert "sirius-oye" in salida


@pytest.mark.usefixtures("bibliotecas_bien")
def test_si_no_se_puede_bajar_la_voz_lo_dice_con_su_causa(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    instalacion = LocalVoiceInstallation(LocalVoiceSettings())
    _pon_modelo(instalacion.listening_model_dir)
    (instalacion.speaking_voice_dir / f"{_VOZ}.onnx").unlink()

    def sin_internet(*args: object) -> None:
        raise ConnectionError("HTTP Error 403: Forbidden")

    monkeypatch.setattr(install_local_voice, "download_speaking_voice", sin_internet)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "[FALLA] No se pudo bajar la voz: HTTP Error 403: Forbidden" in salida
    _sin_remedios_adivinados(salida)


@pytest.mark.usefixtures("bibliotecas_bien")
def test_si_piper_no_carga_dice_que_no_puede_bajar_la_voz_y_por_que(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    instalacion = LocalVoiceInstallation(LocalVoiceSettings())
    _pon_modelo(instalacion.listening_model_dir)
    (instalacion.speaking_voice_dir / f"{_VOZ}.onnx.json").unlink()
    roto = types.ModuleType("piper.download_voices")

    def __getattr__(nombre: str) -> object:
        raise OSError("DLL load failed while importing espeakbridge")

    roto.__getattr__ = __getattr__  # type: ignore[method-assign]
    monkeypatch.setitem(sys.modules, "piper.download_voices", roto)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "No se puede bajar la voz: piper no carga (DLL load failed" in salida
    _sin_remedios_adivinados(salida)


@pytest.mark.usefixtures("bibliotecas_bien")
def test_si_la_voz_no_carga_o_el_altavoz_no_se_abre_la_orden_lo_dice(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pon_modelo(LocalVoiceInstallation(LocalVoiceSettings()).listening_model_dir)

    def sin_altavoz(modelo: Path) -> None:
        raise VoiceUnavailable("no puedo abrir el altavoz (Error querying device -1)")

    monkeypatch.setattr(install_local_voice, "load_listening_engines", lambda carpeta: None)
    monkeypatch.setattr(install_local_voice, "load_speaking_engines", sin_altavoz)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "[FALLA] La voz no carga: no puedo abrir el altavoz (Error querying device -1)" in (
        salida
    )
    _sin_remedios_adivinados(salida)


def test_si_una_biblioteca_de_hablar_esta_rota_la_orden_lo_dice(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pon_modelo(LocalVoiceInstallation(LocalVoiceSettings()).listening_model_dir)

    def rota() -> None:
        raise VoiceUnavailable("piper no carga (No module named 'onnxruntime')")

    monkeypatch.setattr(install_local_voice, "voice_distributions_missing", lambda: ())
    monkeypatch.setattr(install_local_voice, "check_listening_libraries", lambda: None)
    monkeypatch.setattr(install_local_voice, "check_speaking_libraries", rota)

    assert install_local_voice.main() == 1
    salida = capsys.readouterr().out
    assert "Una biblioteca de la voz no está bien: piper no carga" in salida
