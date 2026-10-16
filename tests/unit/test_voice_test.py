"""La prueba de voces: su hoja y su caso de uso (pieza F de ADR-241, ADR-246; PA-R03-10).

Las voces son dobles que apuntan qué frase se les pide y la devuelven como su muestra; el
altavoz de cada una apunta lo que suena, lo que se calla y si se suelta.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from sirius.application.prepare_speech_text import prepare_speech_text
from sirius.application.voice_test import VOICE_TEST_INTRO, VoiceTestUseCase
from sirius.config.local_voice import SpeakingVoice
from sirius.domain.voice_test import (
    MAX_VOICES,
    MIN_VOICES,
    VOICE_TEST_LABELS,
    VOICE_TEST_PHRASES,
    VoiceTestError,
    prepare_voice_test,
)
from sirius.ports.local_voice import SpeakingEngines, VoiceUnavailable

# --- La hoja ---------------------------------------------------------------------------


def _muestras(voces: list[str], frases: tuple[str, ...]) -> dict[str, dict[str, str]]:
    return {voz: {frase: f"{voz}:{frase}" for frase in frases} for voz in voces}


def test_las_cinco_frases_son_distintas_y_se_dicen_tal_cual() -> None:
    assert len(VOICE_TEST_PHRASES) == 5
    assert len(set(VOICE_TEST_PHRASES)) == 5
    # Lo que dice la voz en la charla pasa por `prepare_speech_text`: las frases de la hoja
    # no cambian al pasar, así que suenan como sonarían hablando.
    assert all(prepare_speech_text(frase) == frase for frase in VOICE_TEST_PHRASES)
    assert any(caracter.isdigit() for caracter in VOICE_TEST_PHRASES[-1])


def test_la_hoja_baraja_las_voces_tras_etiquetas_sin_nombre() -> None:
    voces = ["a", "b", "c", "d", "e"]
    hoja = prepare_voice_test(
        VOICE_TEST_PHRASES, _muestras(voces, VOICE_TEST_PHRASES), random.Random(3)
    )

    assert [c.label for c in hoja.candidates] == list(VOICE_TEST_LABELS[:5])
    assert sorted(hoja.key.values()) == voces
    for candidata in hoja.candidates:
        voz = hoja.voice_behind(candidata.label)
        assert dict(candidata.samples) == {f: f"{voz}:{f}" for f in VOICE_TEST_PHRASES}
        assert (
            hoja.sample(candidata.label, VOICE_TEST_PHRASES[0]) == f"{voz}:{VOICE_TEST_PHRASES[0]}"
        )
    ordenes = {
        tuple(
            prepare_voice_test(
                VOICE_TEST_PHRASES, _muestras(voces, VOICE_TEST_PHRASES), random.Random(semilla)
            ).key.values()
        )
        for semilla in range(20)
    }
    assert len(ordenes) > 1


@pytest.mark.parametrize("cuantas", [MIN_VOICES - 1, MAX_VOICES + 1])
def test_la_hoja_es_de_cuatro_a_seis_voces(cuantas: int) -> None:
    voces = [f"v{n}" for n in range(cuantas)]
    with pytest.raises(VoiceTestError, match="entre 4 y 6"):
        prepare_voice_test(
            VOICE_TEST_PHRASES, _muestras(voces, VOICE_TEST_PHRASES), random.Random()
        )


def test_la_hoja_no_acepta_frases_repetidas_ni_vacias_ni_muestras_de_menos() -> None:
    voces = ["a", "b", "c", "d"]
    for frases in (("Hola.", "Hola."), ("Hola.", " ")):
        with pytest.raises(VoiceTestError, match="distintas y no vacías"):
            prepare_voice_test(frases, _muestras(voces, frases), random.Random())
    muestras = _muestras(voces, VOICE_TEST_PHRASES)
    del muestras["c"][VOICE_TEST_PHRASES[2]]
    with pytest.raises(VoiceTestError, match="Falta alguna muestra"):
        prepare_voice_test(VOICE_TEST_PHRASES, muestras, random.Random())


def test_la_hoja_dice_si_no_tiene_una_etiqueta_o_una_frase() -> None:
    voces = ["a", "b", "c", "d"]
    hoja = prepare_voice_test(
        VOICE_TEST_PHRASES, _muestras(voces, VOICE_TEST_PHRASES), random.Random()
    )

    with pytest.raises(VoiceTestError, match="etiqueta"):
        hoja.voice_behind("Voz Z")
    with pytest.raises(VoiceTestError, match="etiqueta"):
        hoja.sample("Voz Z", VOICE_TEST_PHRASES[0])
    with pytest.raises(VoiceTestError, match="frase"):
        hoja.sample("Voz A", "Otra cosa.")


# --- El caso de uso --------------------------------------------------------------------


@dataclass
class _Altavoz:
    sonados: list[str] = field(default_factory=list)
    callados: int = 0
    soltado: bool = False

    def play(self, sound: str) -> None:
        assert not self.soltado, "suena por un altavoz ya soltado"
        self.sonados.append(sound)

    @property
    def playing(self) -> bool:
        return False

    @property
    def latency(self) -> float:
        return 0.0

    def stop(self) -> None:
        self.callados += 1

    @property
    def started(self) -> int:
        return len(self.sonados)

    def close(self) -> None:
        self.soltado = True


@dataclass
class _Voz:
    nombre: str
    pedidas: list[str] = field(default_factory=list)

    def say(self, text: str) -> str:
        self.pedidas.append(text)
        return f"{self.nombre}:{text}"


class _Entorno:
    """Las voces, cargadas como las cargaría el oído, y lo que el caso de uso hace con fuera."""

    def __init__(
        self, *, falta: tuple[str, ...] = (), no_carga: SpeakingVoice | None = None
    ) -> None:
        self.cargadas: list[SpeakingVoice] = []
        self.altavoces: dict[SpeakingVoice, _Altavoz] = {}
        self.voces: dict[SpeakingVoice, _Voz] = {}
        self.elegidas: list[SpeakingVoice] = []
        self.pausas = 0
        self.falta = falta
        self.no_carga = no_carga
        self.al_cargar: Callable[[SpeakingVoice], None] | None = None

    def carga(self, voz: SpeakingVoice) -> SpeakingEngines[str]:
        if voz is self.no_carga:
            raise VoiceUnavailable("la voz de personaje no carga (sin memoria)")
        self.cargadas.append(voz)
        if self.al_cargar is not None:
            self.al_cargar(voz)
        self.voces[voz] = _Voz(voz.value)
        self.altavoces[voz] = _Altavoz()
        return SpeakingEngines(voice=self.voces[voz], speaker=self.altavoces[voz])

    def pausa(self) -> None:
        self.pausas += 1

    def caso(self) -> VoiceTestUseCase:
        return VoiceTestUseCase(
            load_voice=self.carga,
            choose_voice=self.elegidas.append,
            missing=lambda: self.falta,
            pause_listening=self.pausa,
            rng=random.Random(7),
        )


def test_las_candidatas_son_las_del_catalogo_con_piper_y_la_de_personaje() -> None:
    caso = _Entorno().caso()

    voces = caso.voices()
    assert MIN_VOICES <= len(voces) <= MAX_VOICES
    assert sum(voz.value.startswith("es_ES-") for voz in voces) >= 2
    assert [voz for voz in voces if voz.is_character] == [SpeakingVoice.CHARACTER]
    assert "chatterbox" in SpeakingVoice.CHARACTER.value


def test_preparar_pide_cada_frase_a_cada_voz_una_vez_y_cuenta_lo_hecho() -> None:
    entorno = _Entorno()
    caso = entorno.caso()
    progreso: list[tuple[int, int]] = []

    hoja = caso.prepare(on_progress=lambda hecho, total: progreso.append((hecho, total)))
    otra = caso.prepare()

    # Cada voz se carga una vez y queda cargada; las frases se piden en cada hoja.
    assert entorno.cargadas == list(SpeakingVoice)
    total = len(SpeakingVoice) * len(VOICE_TEST_PHRASES)
    assert progreso == [(n, total) for n in range(1, total + 1)]
    for voz in SpeakingVoice:
        assert entorno.voces[voz].pedidas == [*VOICE_TEST_PHRASES, *VOICE_TEST_PHRASES]
    for una in (hoja, otra):
        for candidata in una.candidates:
            voz = una.voice_behind(candidata.label)
            assert dict(candidata.samples) == {f: f"{voz.value}:{f}" for f in VOICE_TEST_PHRASES}


def test_sin_todas_las_voces_instaladas_no_prepara_nada_y_dice_que_falta() -> None:
    entorno = _Entorno(falta=("Para la prueba de voces me falta instalar la voz X.",))
    caso = entorno.caso()

    with pytest.raises(VoiceTestError, match="me falta instalar la voz X"):
        caso.prepare()
    assert entorno.cargadas == []


def test_si_una_voz_no_carga_lo_dice_con_su_causa() -> None:
    caso = _Entorno(no_carga=SpeakingVoice.CHARACTER).caso()

    with pytest.raises(VoiceTestError, match="la voz de personaje no carga \\(sin memoria\\)"):
        caso.prepare()


def test_si_se_cierra_mientras_prepara_no_pide_mas_frases() -> None:
    entorno = _Entorno()
    caso = entorno.caso()
    pedidas = 0

    def tras_tres() -> bool:
        nonlocal pedidas
        pedidas += 1
        return pedidas > 3

    with pytest.raises(VoiceTestError, match="se canceló"):
        caso.prepare(should_stop=tras_tres)
    assert sum(len(voz.pedidas) for voz in entorno.voces.values()) == 3


def test_lo_que_carga_una_hoja_cerrada_a_medias_se_suelta() -> None:
    entorno = _Entorno()
    caso = entorno.caso()

    def cierra_al_cargar_la_segunda(voz: SpeakingVoice) -> None:
        if voz is list(SpeakingVoice)[1]:
            caso.close()

    entorno.al_cargar = cierra_al_cargar_la_segunda
    with pytest.raises(VoiceTestError, match="se canceló"):
        caso.prepare()

    assert all(altavoz.soltado for altavoz in entorno.altavoces.values())


def test_escuchar_cierra_el_micro_calla_lo_que_sonaba_y_pone_esa_muestra() -> None:
    entorno = _Entorno()
    caso = entorno.caso()
    hoja = caso.prepare()
    candidata = hoja.candidates[2]
    voz = hoja.voice_behind(candidata.label)

    caso.listen(hoja, candidata.label, VOICE_TEST_PHRASES[1])

    assert entorno.pausas == 1
    assert all(altavoz.callados == 1 for altavoz in entorno.altavoces.values())
    assert entorno.altavoces[voz].sonados == [candidata.samples[VOICE_TEST_PHRASES[1]]]
    otras = [a for v, a in entorno.altavoces.items() if v is not voz]
    assert all(altavoz.sonados == [] for altavoz in otras)


def test_escuchar_con_la_hoja_cerrada_lo_dice() -> None:
    entorno = _Entorno()
    caso = entorno.caso()
    hoja = caso.prepare()
    caso.close()

    with pytest.raises(VoiceTestError, match="cerrada"):
        caso.listen(hoja, "Voz A", VOICE_TEST_PHRASES[0])
    assert all(altavoz.sonados == [] for altavoz in entorno.altavoces.values())


def test_elegir_deja_la_voz_que_hay_tras_la_etiqueta() -> None:
    entorno = _Entorno()
    caso = entorno.caso()
    hoja = caso.prepare()

    elegida = caso.choose(hoja, "Voz D")

    assert entorno.elegidas == [hoja.voice_behind("Voz D")] == [elegida]


def test_cerrar_suelta_las_voces_cargadas() -> None:
    entorno = _Entorno()
    caso = entorno.caso()
    caso.prepare()

    caso.close()
    caso.close()

    assert all(altavoz.soltado for altavoz in entorno.altavoces.values())


def test_lo_que_se_ve_son_etiquetas_y_frases_y_ningun_nombre_de_voz() -> None:
    caso = _Entorno().caso()
    hoja = caso.prepare()

    vista = caso.view(hoja)

    etiquetas = tuple(c.label for c in hoja.candidates)
    assert vista.intro == VOICE_TEST_INTRO
    assert vista.rows == tuple((frase, etiquetas) for frase in VOICE_TEST_PHRASES)
    assert [etiqueta for etiqueta, _texto in vista.choices] == list(etiquetas)
    lineas = vista.lines()
    assert lineas[0] == VOICE_TEST_INTRO
    visible = "\n".join(lineas).casefold()
    for escondido in (*(voz.value for voz in SpeakingVoice), "piper", "chatterbox", "es_es"):
        assert escondido.casefold() not in visible
