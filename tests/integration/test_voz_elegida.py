"""La voz que elige a ciegas habla desde el turno siguiente, sin volver a abrir Sirius
(pieza F, ADR-246).

PA-R03-10 mira que la elegida quede al volver a abrir Sirius; esta es la decisión de
ADR-246 de que valga ya en el turno siguiente. Con el conductor de la 0.3, que es Sirius
de verdad con los dobles del oído y la voz.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conductor_robot_0_3 import ConductorDeVoz

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.composition_root import build_conversation_dependencies
from sirius.config.local_voice import SpeakingVoice
from sirius.infrastructure.local_voice_installation import (
    CHARACTER_INSTALL_COMMAND,
    speaking_voice_files,
    voice_dir,
    voice_distributions_missing,
)
from sirius.infrastructure.paths import resolve_paths

pytestmark = pytest.mark.integration


def _elige(conductor: ConductorDeVoz, voz: SpeakingVoice) -> None:
    hoja = conductor.hoja_de_voces()
    etiqueta = next(c.etiqueta for c in hoja.candidatas if conductor.voz_tras(c.etiqueta) == voz)
    conductor.elige_voz(etiqueta)


@pytest.mark.parametrize("voz", [SpeakingVoice.SHARVARD, SpeakingVoice.CHARACTER])
def test_la_voz_elegida_habla_desde_el_turno_siguiente(tmp_path: Path, voz: SpeakingVoice) -> None:
    conductor = ConductorDeVoz(tmp_path)
    antes = conductor.oye("Buenos días, Sirius.")
    assert antes.contestado is not None
    assert conductor.voz.frases[-1].voz == SpeakingVoice.DAVEFX

    _elige(conductor, voz)
    turno = conductor.oye("Sirius, ¿me oyes ahora?")

    assert turno.contestado is not None
    assert conductor.voz.frases[-1].voz == voz
    assert conductor.altavoz.sonados[-1][0].voz == voz
    assert conductor.altavoz.sonados[-1][0].texto == turno.contestado


def test_mientras_suena_una_muestra_el_micro_esta_cerrado(tmp_path: Path) -> None:
    conductor = ConductorDeVoz(tmp_path)
    conductor.oye("Buenos días, Sirius.")
    oido = conductor._dependencias.local_listening
    assert oido.listening
    hoja = conductor.hoja_de_voces()

    conductor.escucha_en_la_hoja(hoja.candidatas[0].etiqueta, hoja.frases[0])

    # La muestra sonó con el micro ya cerrado: Sirius no la toma por algo que le dicen.
    assert not oido.listening
    assert not conductor.micro.abierto
    turno = conductor.oye("Sirius, ¿sigues ahí?")
    assert turno.oido == "Sirius, ¿sigues ahí?"


@pytest.mark.skipif(
    not voice_distributions_missing(("chatterbox-tts",)),
    reason="aquí está instalada la voz de personaje: no se puede ver que falte",
)
def test_con_la_voz_de_verdad_la_hoja_mira_que_este_la_biblioteca_de_personaje(
    tmp_path: Path,
) -> None:
    # Ronda 1 de Codex sobre la PR #691: con todos los ficheros puestos y sin el extra
    # `personaje`, como Quality, la hoja no se abre y dice la orden.
    rutas = resolve_paths()
    initialize_persistence(rutas)
    for voz in SpeakingVoice:
        carpeta = voice_dir(voz)
        carpeta.mkdir(parents=True, exist_ok=True)
        for nombre in speaking_voice_files(voz.value):
            (carpeta / nombre).write_bytes(b"de mentira")
    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db", tmp_path / "copias", secret_store=FakeSecretStore()
    )

    [aviso] = deps.voice_test_use_case.missing()

    assert "la biblioteca de la voz de personaje (chatterbox-tts)" in aviso
    assert CHARACTER_INSTALL_COMMAND in aviso
