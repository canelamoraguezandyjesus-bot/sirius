"""Las voces con que puede hablar, dónde viven y cuál eligió (pieza F, ADR-246).

El catálogo es cerrado, como todos los ajustes de la voz: cuatro voces de Piper y la de
personaje. La que él elige se guarda en los ajustes por su nombre, y se lee cada vez que
hace falta, así que vale desde que la elige.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import sirius.infrastructure.local_voice_installation as instalacion_module
from sirius.config.local_voice import (
    SPEAKING_VOICE_SETTING,
    LocalVoiceSettings,
    SpeakingVoice,
    local_voice_settings,
)
from sirius.infrastructure.local_voice_installation import (
    CHARACTER_INSTALL_COMMAND,
    CHARACTER_VOICE_FILES,
    INSTALL_COMMAND,
    ChosenVoiceInstallation,
    LocalVoiceInstallation,
    speaking_voice_files,
    voice_dir,
    voice_model,
    voice_test_missing,
    voices_missing,
)


def _pon(voz: SpeakingVoice, base: Path) -> None:
    carpeta = voice_dir(voz, base)
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre in speaking_voice_files(voz.value):
        (carpeta / nombre).write_bytes(b"voz")


def test_la_voz_elegida_se_lee_de_los_ajustes_por_su_nombre() -> None:
    for voz in SpeakingVoice:
        assert local_voice_settings({SPEAKING_VOICE_SETTING: voz.value}).speaking_voice is voz


@pytest.mark.parametrize(
    "guardado", [{}, {SPEAKING_VOICE_SETTING: "es_MX-ald-medium"}, {SPEAKING_VOICE_SETTING: 3}]
)
def test_sin_elegir_o_con_algo_que_no_es_del_catalogo_habla_con_la_de_siempre(
    guardado: dict[str, object],
) -> None:
    assert local_voice_settings(guardado) == LocalVoiceSettings()
    assert LocalVoiceSettings().speaking_voice is SpeakingVoice.DAVEFX


def test_solo_la_de_personaje_es_de_chatterbox_y_solo_sharvard_pide_su_locutor() -> None:
    assert [voz for voz in SpeakingVoice if voz.is_character] == [SpeakingVoice.CHARACTER]
    assert {voz: voz.piper_speaker for voz in SpeakingVoice if voz.piper_speaker} == {
        SpeakingVoice.SHARVARD: "M"
    }


def test_cada_voz_vive_en_su_carpeta_y_se_carga_por_su_nombre(tmp_path: Path) -> None:
    for voz in SpeakingVoice:
        carpeta = voice_dir(voz, tmp_path)
        modelo = voice_model(voz, tmp_path)
        assert carpeta.parent == tmp_path / ("chatterbox" if voz.is_character else "piper")
        assert carpeta.name == voz.value
        # Quien carga la voz sabe cuál es por el nombre de lo que le dan (el conductor de
        # las pruebas también).
        assert modelo.name.removesuffix(".onnx") == voz.value
        assert modelo == (carpeta if voz.is_character else carpeta / f"{voz.value}.onnx")
    assert speaking_voice_files(SpeakingVoice.CHARACTER.value) == CHARACTER_VOICE_FILES


def test_la_prueba_de_voces_dice_que_voces_faltan_y_con_que_orden(tmp_path: Path) -> None:
    for voz in SpeakingVoice:
        _pon(voz, tmp_path)
    assert voices_missing(tmp_path) == ()
    assert voice_test_missing(tmp_path, libraries=False) == ()

    (voice_dir(SpeakingVoice.CARLFM, tmp_path) / f"{SpeakingVoice.CARLFM.value}.onnx").unlink()
    (voice_dir(SpeakingVoice.CHARACTER, tmp_path) / "conds.pt").unlink()

    assert voices_missing(tmp_path) == (SpeakingVoice.CARLFM, SpeakingVoice.CHARACTER)
    [aviso] = voice_test_missing(tmp_path, libraries=False)
    assert (
        f"la voz (Piper {SpeakingVoice.CARLFM.value}) y la voz de personaje (Chatterbox)" in aviso
    )
    assert CHARACTER_INSTALL_COMMAND in aviso


def test_con_la_de_personaje_elegida_falta_ella_y_su_orden_es_la_del_extra(tmp_path: Path) -> None:
    personaje = LocalVoiceInstallation(
        LocalVoiceSettings(speaking_voice=SpeakingVoice.CHARACTER), tmp_path
    )
    de_piper = LocalVoiceInstallation(LocalVoiceSettings(), tmp_path)

    assert "la voz de personaje (Chatterbox)" in personaje.missing()
    assert personaje.install_command == CHARACTER_INSTALL_COMMAND
    assert de_piper.install_command == INSTALL_COMMAND


def test_la_instalacion_elegida_sigue_a_los_ajustes_de_cada_momento(tmp_path: Path) -> None:
    ahora = [LocalVoiceSettings()]
    instalacion = ChosenVoiceInstallation(lambda: ahora[0], tmp_path)
    antes = instalacion.speaking_voice_model

    ahora[0] = LocalVoiceSettings(speaking_voice=SpeakingVoice.SHARVARD)

    assert antes == voice_model(SpeakingVoice.DAVEFX, tmp_path)
    assert instalacion.speaking_voice_model == voice_model(SpeakingVoice.SHARVARD, tmp_path)
    assert instalacion.missing() == LocalVoiceInstallation(ahora[0], tmp_path).missing()
    assert (
        instalacion.listening_model_dir
        == LocalVoiceInstallation(ahora[0], tmp_path).listening_model_dir
    )


def test_con_los_ficheros_y_sin_la_biblioteca_de_personaje_la_hoja_no_se_abre(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Ronda 1 de Codex sobre la PR #691: los ficheros de la voz de personaje siguen aquí con
    # el entorno rehecho sin el extra `personaje`.
    for voz in SpeakingVoice:
        _pon(voz, tmp_path)
    mirados: list[tuple[str, ...]] = []

    def sin_chatterbox(nombres: tuple[str, ...]) -> tuple[str, ...]:
        mirados.append(nombres)
        return ("chatterbox-tts",)

    monkeypatch.setattr(instalacion_module, "voice_distributions_missing", sin_chatterbox)

    [aviso] = voice_test_missing(tmp_path)

    assert mirados == [("chatterbox-tts",)]
    assert "la biblioteca de la voz de personaje (chatterbox-tts)" in aviso
    assert CHARACTER_INSTALL_COMMAND in aviso
    monkeypatch.setattr(instalacion_module, "voice_distributions_missing", lambda nombres: ())
    assert voice_test_missing(tmp_path) == ()
