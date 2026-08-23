"""Un doble de pruebas que se calla es peor que no tenerlo.

El 23-08-2026 la PR #289 tuvo dos ejecuciones de Quality sobre el MISMO commit
con resultados distintos: una verde en 290 s, otra roja en 316 s con un plazo
agotado de cinco segundos y ninguna explicación.

La causa no era lentitud —la prueba tarda 0,52 s contra un plazo de 5 s, diez
veces de margen— sino que `FakeAudioPlayback.finish()` **se tragaba en silencio**
el aviso de final cuando `play()` todavía no se había llamado. El trozo de audio
siguiente no se sintetizaba nunca y la espera moría sin decir por qué.

Estas pruebas fijan que el doble grite. No hacen improbable el error: lo hacen
imposible de pasar por alto. ADR-081, incidencia #290.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sirius.adapters.audio.fake import FakeAudioPlayback


def test_terminar_sin_nada_sonando_grita_en_vez_de_callarse() -> None:
    """El caso exacto que costó una vuelta del ciclo: `finish()` antes de `play()`."""
    playback = FakeAudioPlayback()

    with pytest.raises(AssertionError, match="finish\\(\\) sin nada sonando"):
        playback.finish()


def test_terminar_despues_de_parar_a_proposito_tambien_grita() -> None:
    """Tras un `stop()` no queda a quién avisar, y callarlo escondería lo mismo."""
    playback = FakeAudioPlayback()
    playback.play(Path("voz-1.wav"), lambda: None)
    playback.stop()

    with pytest.raises(AssertionError, match="finish\\(\\) sin nada sonando"):
        playback.finish()


def test_con_reproduccion_en_marcha_el_aviso_llega() -> None:
    """Anti-vacua: si la guarda gritara siempre, las dos de arriba pasarían solas."""
    playback = FakeAudioPlayback()
    finales: list[None] = []
    playback.play(Path("voz-1.wav"), lambda: finales.append(None))

    playback.finish()

    assert finales == [None], "el final tiene que llegar cuando sí hay algo sonando"
    assert not playback.is_playing()


def test_el_aviso_no_llega_dos_veces_por_el_mismo_audio() -> None:
    """Un solo audio, un solo final: el segundo `finish()` ya no tiene destinatario."""
    playback = FakeAudioPlayback()
    finales: list[None] = []
    playback.play(Path("voz-1.wav"), lambda: finales.append(None))
    playback.finish()

    with pytest.raises(AssertionError, match="finish\\(\\) sin nada sonando"):
        playback.finish()

    assert finales == [None]


def test_el_aviso_queda_instalado_antes_de_que_played_crezca() -> None:
    """`played` es la señal de «ya suena»: quien la ve tiene que poder terminar.

    Es la ventana que quedaba tras arreglar #290, dos líneas más abajo y de la
    misma familia: si `played` creciera antes de instalar el aviso, otro hilo
    podría verla y llamar a `finish()` sin que hubiera destinatario. Instalar
    primero convierte «`played` no vacío» en «aviso puesto», que es lo que las
    pruebas dan por hecho.
    """
    playback = FakeAudioPlayback()
    aviso_puesto_al_crecer: list[bool] = []

    class _ListaQueMira(list[Path]):
        def append(self, item: Path) -> None:
            aviso_puesto_al_crecer.append(playback._on_finished is not None)
            super().append(item)

    playback.played = _ListaQueMira()

    playback.play(Path("voz-1.wav"), lambda: None)

    assert aviso_puesto_al_crecer == [True], (
        "`played` creció antes de instalar el aviso de final: quien vea esa "
        "señal desde otro hilo puede llamar a `finish()` y no encontrar a nadie"
    )
