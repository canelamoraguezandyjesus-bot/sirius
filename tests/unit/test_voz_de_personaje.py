"""La voz de personaje, Chatterbox, cableada con módulos de mentira (pieza F, ADR-246).

Chatterbox es del extra ``personaje``, que Quality no instala: aquí se pone un módulo de
mentira en su sitio, y en el de torch, y se mira cómo los usa Sirius. Lo que se mira es lo
que cierra puertas: carga solo de su carpeta y sin conexión a Hugging Face, y nunca le da
un audio para imitar a nadie. Cómo suena lo dice él (E-R03-06).
"""

from __future__ import annotations

import ast
import importlib
import logging
import os
import sys
import threading
import types
import warnings
from array import array
from pathlib import Path
from typing import Any

import pytest

import sirius.adapters.audio.character_voice as character_voice_module
from sirius.adapters.audio.character_voice import LANGUAGE, CharacterSpeech, load_character_voice
from sirius.adapters.audio.voice_libraries import (
    CHARACTER_VOICE_LIBRARY,
    OFFLINE_VARIABLES,
    hugging_face_offline,
)
from sirius.ports.local_voice import VoiceUnavailable


class _Onda:
    """Lo que devuelve ``generate``: un tensor de (1, N) muestras entre -1 y 1."""

    def __init__(self, muestras: list[float]) -> None:
        self._muestras = muestras

    def squeeze(self, eje: int) -> _Onda:
        assert eje == 0
        return self

    def tolist(self) -> list[float]:
        return list(self._muestras)


class _Modelo:
    sr = 24_000

    def __init__(self) -> None:
        self.pedidos: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def generate(self, *args: Any, **kwargs: Any) -> _Onda:
        self.pedidos.append((args, kwargs))
        return _Onda([0.5, -2.0, 1.5, 0.0])


class _Chatterbox:
    cargas: list[tuple[Path, str]] = []  # noqa: RUF012
    falla: Exception | None = None

    @staticmethod
    def from_local(carpeta: Path, device: str) -> _Modelo:
        if _Chatterbox.falla is not None:
            raise _Chatterbox.falla
        _Chatterbox.cargas.append((carpeta, device))
        return _Modelo()


@pytest.fixture
def chatterbox(monkeypatch: pytest.MonkeyPatch) -> type[_Chatterbox]:
    """Un Chatterbox y un torch de mentira, sin gráfica, y Hugging Face sin importar."""
    monkeypatch.setattr(_Chatterbox, "cargas", [])
    monkeypatch.setattr(_Chatterbox, "falla", None)
    multilingue = types.ModuleType(CHARACTER_VOICE_LIBRARY)
    multilingue.ChatterboxMultilingualTTS = _Chatterbox  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, CHARACTER_VOICE_LIBRARY, multilingue)
    torch = types.ModuleType("torch")
    torch.cuda = types.SimpleNamespace(is_available=lambda: False)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.delitem(sys.modules, "huggingface_hub.constants", raising=False)
    for variable in OFFLINE_VARIABLES:
        monkeypatch.delenv(variable, raising=False)
    return _Chatterbox


def test_carga_solo_de_su_carpeta_sin_conexion_y_en_el_procesador_sin_grafica(
    chatterbox: type[_Chatterbox], tmp_path: Path
) -> None:
    voz = load_character_voice(tmp_path)

    assert chatterbox.cargas == [(tmp_path, "cpu")]
    assert all(os.environ[variable] == "1" for variable in OFFLINE_VARIABLES)
    assert voz.sample_rate == 24_000


def test_con_grafica_carga_en_la_grafica(
    chatterbox: type[_Chatterbox], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    torch = sys.modules["torch"]
    monkeypatch.setattr(torch, "cuda", types.SimpleNamespace(is_available=lambda: True))

    load_character_voice(tmp_path)

    assert chatterbox.cargas == [(tmp_path, "cuda")]


def test_si_no_carga_avisa_y_no_tumba_a_sirius(
    chatterbox: type[_Chatterbox], tmp_path: Path
) -> None:
    chatterbox.falla = RuntimeError("CUDA out of memory")

    with pytest.raises(
        VoiceUnavailable, match="la voz de personaje no carga \\(CUDA out of memory\\)"
    ):
        load_character_voice(tmp_path)


def test_sin_el_extra_personaje_avisa_y_no_tumba_a_sirius(
    chatterbox: type[_Chatterbox], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(sys.modules, CHARACTER_VOICE_LIBRARY, None)

    with pytest.raises(VoiceUnavailable, match="chatterbox"):
        load_character_voice(tmp_path)


#: Un Chatterbox de mentira que avisa como el de verdad al cargar: al importarse, la marca
#: de agua de Perth importa ``pkg_resources``; al construirse, diffusers y el tokenizador.
_CHATTERBOX_QUE_AVISA = """
import logging
import warnings

warnings.warn(
    "pkg_resources is deprecated as an API. See https://setuptools.pypa.io/.", UserWarning
)


class ChatterboxMultilingualTTS:
    sr = 24_000

    @staticmethod
    def from_local(carpeta, device):
        warnings.warn(
            "`LoRACompatibleLinear` is deprecated and will be removed in version 1.0.0.",
            FutureWarning,
        )
        tokenizador = logging.getLogger("chatterbox.models.tokenizers.tokenizer")
        tokenizador.warning("Could not load Cangjie mapping: sin conexión")
        tokenizador.warning("pkuseg not available - Chinese segmentation will be skipped")
        warnings.warn("Este aviso sí cuenta algo.", UserWarning)
        return ChatterboxMultilingualTTS()
"""


def test_al_cargar_calla_los_tres_avisos_que_no_dicen_nada_y_solo_esos(
    chatterbox: type[_Chatterbox],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    del chatterbox  # solo por su torch de mentira y Hugging Face sin importar
    paquete = tmp_path / "chatterbox"
    paquete.mkdir()
    (paquete / "__init__.py").write_text("", encoding="utf-8")
    (paquete / "mtl_tts.py").write_text(_CHATTERBOX_QUE_AVISA, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, CHARACTER_VOICE_LIBRARY)
    tokenizador = logging.getLogger("chatterbox.models.tokenizers.tokenizer")
    try:
        with warnings.catch_warnings(record=True) as avisos, caplog.at_level(logging.WARNING):
            warnings.simplefilter("always")
            load_character_voice(tmp_path)
            # Después de cargar, avisan como siempre.
            warnings.warn("`LoRACompatibleLinear` is deprecated.", FutureWarning, stacklevel=1)
            tokenizador.warning("pkuseg not available")
    finally:
        sys.modules.pop(CHARACTER_VOICE_LIBRARY, None)
        sys.modules.pop("chatterbox", None)

    assert [str(aviso.message) for aviso in avisos] == [
        "Este aviso sí cuenta algo.",
        "`LoRACompatibleLinear` is deprecated.",
    ]
    assert [registro.getMessage() for registro in caplog.records] == ["pkuseg not available"]
    assert tokenizador.level == logging.NOTSET


#: Dónde avisa transformers 5.2.0 de que ``output_attentions`` no vale para generar.
_GENERACION = "transformers.generation.configuration_utils"
_AVISO_DE_TORCH = (
    "`torch.backends.cuda.sdp_kernel()` is deprecated. In the future, this context manager "
    "will be removed. Please see `torch.nn.attention.sdpa_kernel()` for the new context "
    "manager, with updated signature."
)
_AVISO_DE_TRANSFORMERS = (
    "The following generation flags are not valid and may be ignored: ['output_attentions']. "
    "Set `TRANSFORMERS_VERBOSITY=info` for more details."
)


def _pinta_como_chatterbox_al_decir() -> None:
    """Lo que pinta Chatterbox 0.1.7 al decir una frase: la barra de tqdm de verdad, el aviso
    de torch y el de transformers; y además otras cosas, que tienen que salir."""
    tqdm = importlib.import_module("tqdm").tqdm
    for _ in tqdm(range(3), desc="Sampling", dynamic_ncols=True):
        pass
    warnings.warn(_AVISO_DE_TORCH, FutureWarning, stacklevel=1)
    logging.getLogger(_GENERACION).warning(_AVISO_DE_TRANSFORMERS)
    print("otra cosa por la consola", file=sys.stderr)
    warnings.warn("Este aviso sí cuenta algo.", UserWarning, stacklevel=1)
    warnings.warn("Y este del futuro, también.", FutureWarning, stacklevel=1)
    logging.getLogger(_GENERACION).warning("Otro aviso de transformers")


class _ModeloQuePinta(_Modelo):
    def generate(self, *args: Any, **kwargs: Any) -> _Onda:
        _pinta_como_chatterbox_al_decir()
        return super().generate(*args, **kwargs)


class _Registro(logging.Handler):
    """Lo que llega a un registrador, leído de él y no de la raíz."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.lineas: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lineas.append(record.getMessage())


def test_al_decir_cada_frase_calla_la_barra_y_los_dos_avisos_y_solo_esos(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # #696: con la voz de personaje, cada frase pintaba su barra «Sampling», el aviso de
    # torch por ``sdp_kernel`` y el de transformers por ``output_attentions``.
    generacion = logging.getLogger(_GENERACION)
    registro = _Registro()
    generacion.addHandler(registro)
    consola = sys.stderr
    try:
        with warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter("always")
            CharacterSpeech(_ModeloQuePinta()).say("Buenos días, jefe.")
            dentro = [str(aviso.message) for aviso in avisos]
            del avisos[:]
            # Después de decirla, todo sale como siempre.
            _pinta_como_chatterbox_al_decir()
            fuera = [str(aviso.message) for aviso in avisos]
    finally:
        generacion.removeHandler(registro)

    pintado = capsys.readouterr().err
    assert sys.stderr is consola
    assert dentro == ["Este aviso sí cuenta algo.", "Y este del futuro, también."]
    assert fuera == [_AVISO_DE_TORCH, "Este aviso sí cuenta algo.", "Y este del futuro, también."]
    assert registro.lineas == [
        "Otro aviso de transformers",
        _AVISO_DE_TRANSFORMERS,
        "Otro aviso de transformers",
    ]
    dicho_al_decir, _, dicho_despues = pintado.partition("otra cosa por la consola\n")
    # Al decirla, ni la barra ni el salto de línea con que la cierra tqdm.
    assert dicho_al_decir == ""
    assert "Sampling:" in dicho_despues
    assert dicho_despues.endswith("otra cosa por la consola\n")


class _ModeloQueEspera(_Modelo):
    """Avisa con ``dentro`` al empezar su frase, espera a ``seguir`` como mucho ``espera``
    segundos, y la dice pintando como Chatterbox. Cuenta cuántas frases se dicen a la vez."""

    a_la_vez = 0
    mas_a_la_vez = 0
    _cuenta = threading.Lock()

    def __init__(self, dentro: threading.Event, seguir: threading.Event, espera: float) -> None:
        super().__init__()
        self._dentro = dentro
        self._seguir = seguir
        self._espera = espera

    def generate(self, *args: Any, **kwargs: Any) -> _Onda:
        with _ModeloQueEspera._cuenta:
            _ModeloQueEspera.a_la_vez += 1
            _ModeloQueEspera.mas_a_la_vez = max(
                _ModeloQueEspera.mas_a_la_vez, _ModeloQueEspera.a_la_vez
            )
        try:
            self._dentro.set()
            self._seguir.wait(timeout=self._espera)
            tqdm = importlib.import_module("tqdm").tqdm
            for _ in tqdm(range(3), desc="Sampling", dynamic_ncols=True):
                pass
            warnings.warn(_AVISO_DE_TORCH, FutureWarning, stacklevel=1)
            return super().generate(*args, **kwargs)
        finally:
            with _ModeloQueEspera._cuenta:
                _ModeloQueEspera.a_la_vez -= 1


def test_dos_frases_a_la_vez_en_dos_hilos_van_una_detras_de_otra_y_lo_dejan_todo_como_estaba(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # #696, revisión de 0d74123c: con dos frases entrelazadas, la segunda pintaba su barra y
    # el filtro de ``sdp_kernel`` se quedaba para siempre en ``warnings.filters``. Si pueden,
    # la primera empieza, la segunda empieza, la primera acaba y después la segunda.
    monkeypatch.setattr(_ModeloQueEspera, "a_la_vez", 0)
    monkeypatch.setattr(_ModeloQueEspera, "mas_a_la_vez", 0)
    consola = sys.stderr
    a_dentro, b_dentro, a_fuera = threading.Event(), threading.Event(), threading.Event()
    primera = _ModeloQueEspera(a_dentro, b_dentro, espera=1.0)
    segunda = _ModeloQueEspera(b_dentro, a_fuera, espera=5.0)

    def dice_la_primera() -> None:
        CharacterSpeech(primera).say("Una.")
        a_fuera.set()

    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        filtros = list(warnings.filters)
        hilo_a = threading.Thread(target=dice_la_primera)
        hilo_a.start()
        assert a_dentro.wait(timeout=5)
        hilo_b = threading.Thread(target=CharacterSpeech(segunda).say, args=("Y otra.",))
        hilo_b.start()
        hilo_a.join(timeout=10)
        hilo_b.join(timeout=10)
        filtros_despues = list(warnings.filters)

    assert primera.pedidos
    assert segunda.pedidos
    assert filtros_despues == filtros
    assert "Sampling" not in capsys.readouterr().err
    assert not [aviso for aviso in avisos if "sdp_kernel" in str(aviso.message)]
    assert sys.stderr is consola
    assert _ModeloQueEspera.mas_a_la_vez == 1


def test_solo_le_da_el_texto_y_el_idioma_y_ningun_audio() -> None:
    modelo = _Modelo()

    sonido = CharacterSpeech(modelo).say("Buenos días, jefe.")

    assert modelo.pedidos == [(("Buenos días, jefe.",), {"language_id": LANGUAGE})]
    # En 16 bits como Piper, con lo que se pasa de -1 a 1 recortado.
    assert sonido == array("h", [16384, -32767, 32767, 0]).tobytes()


def test_ninguna_funcion_de_la_voz_de_personaje_importa_por_su_cuenta() -> None:
    fuente = Path(character_voice_module.__file__).read_text(encoding="utf-8")
    sueltos = [
        f"{funcion.name}:{nodo.lineno}"
        for funcion in ast.walk(ast.parse(fuente))
        if isinstance(funcion, ast.FunctionDef | ast.AsyncFunctionDef)
        for nodo in ast.walk(funcion)
        if isinstance(nodo, ast.Import | ast.ImportFrom)
    ]

    assert sueltos == []


# --- Hugging Face sin conexión -------------------------------------------------------


def _hub(monkeypatch: pytest.MonkeyPatch, *, mira: bool = True) -> types.ModuleType:
    """Un ``huggingface_hub.constants`` ya importado con conexión, que en cada petición mira
    su constante, como el de la versión 1.33."""
    constantes = types.ModuleType("huggingface_hub.constants")
    constantes.HF_HUB_OFFLINE = False  # type: ignore[attr-defined]
    if mira:
        constantes.is_offline_mode = lambda: constantes.HF_HUB_OFFLINE  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "huggingface_hub.constants", constantes)
    return constantes


def test_sin_conexion_pone_las_variables_que_lee_hugging_face(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "huggingface_hub.constants", raising=False)
    for variable in OFFLINE_VARIABLES:
        monkeypatch.delenv(variable, raising=False)

    hugging_face_offline()

    assert {variable: os.environ[variable] for variable in OFFLINE_VARIABLES} == {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
    }


def test_si_ya_estaba_importado_con_conexion_lo_apaga(monkeypatch: pytest.MonkeyPatch) -> None:
    constantes = _hub(monkeypatch)

    hugging_face_offline()

    assert constantes.is_offline_mode() is True


def test_si_no_se_puede_saber_que_esta_sin_conexion_no_carga(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _hub(monkeypatch, mira=False)

    with pytest.raises(VoiceUnavailable, match="sin conexión"):
        hugging_face_offline()


def test_si_sigue_con_conexion_despues_de_apagarlo_no_carga(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constantes = _hub(monkeypatch)
    constantes.is_offline_mode = lambda: False  # type: ignore[attr-defined]

    with pytest.raises(VoiceUnavailable, match="sin conexión"):
        hugging_face_offline()


def test_la_ventana_y_la_consola_se_ponen_sin_conexion_antes_de_nada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sirius.listen_console as consola
    import sirius.main as ventana

    class Primero(Exception):
        pass

    def apunta() -> None:
        raise Primero

    class _QtTodaviaNo:
        @staticmethod
        def instance() -> None:
            pytest.fail("abrió Qt antes de ponerse sin conexión")

    monkeypatch.setattr(ventana, "install_crash_handler", lambda: None)
    monkeypatch.setattr(ventana, "QApplication", _QtTodaviaNo)
    monkeypatch.setattr(ventana, "hugging_face_offline", apunta)
    monkeypatch.setattr(consola, "hugging_face_offline", apunta)
    monkeypatch.setattr(consola, "known_data_paths", lambda: pytest.fail("leyó antes los datos"))

    with pytest.raises(Primero):
        ventana.main()
    with pytest.raises(Primero):
        consola.main()
