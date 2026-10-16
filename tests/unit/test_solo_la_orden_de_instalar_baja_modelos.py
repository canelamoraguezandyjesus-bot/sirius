"""Sirius no baja un modelo ni una voz por su cuenta: solo lo hace la orden de instalar.

ADR-242 y ADR-243. Si al oído le falta su modelo, o a la voz la suya, dice qué orden
ejecutar y no baja nada (PA-R03-08). El vigilante de las pruebas de aceptación ve la red
de Python, pero faster-whisper pide el ``tokenizer.json`` que le falte desde Rust, donde no
llega nadie. Así que la puerta se cierra por construcción: ningún módulo de ``src/``, salvo
la orden de instalar, nombra una función que baje modelos o voces.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
_LA_ORDEN_DE_INSTALAR = _SRC / "sirius" / "install_local_voice.py"

#: Las funciones con que faster-whisper, huggingface_hub y tokenizers bajan un modelo, con
#: la que Piper baja una voz, y con la que la orden baja la voz de personaje (ADR-246).
QUE_BAJAN = frozenset(
    {
        "download_model",
        "snapshot_download",
        "hf_hub_download",
        "from_pretrained",
        "download_voice",
        "urlopen",
    }
)


def nombres(fuente: str) -> set[str]:
    """Cada nombre que usa un módulo: variables, atributos e importaciones, con su alias."""
    vistos: set[str] = set()
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.Name):
            vistos.add(nodo.id)
        elif isinstance(nodo, ast.Attribute):
            vistos.add(nodo.attr)
        elif isinstance(nodo, ast.alias):
            vistos.add(nodo.name.rsplit(".", 1)[-1])
            if nodo.asname:
                vistos.add(nodo.asname)
    return vistos


def test_solo_la_orden_de_instalar_nombra_lo_que_baja_modelos() -> None:
    culpables = {
        str(ruta.relative_to(_SRC)): sorted(nombres(ruta.read_text(encoding="utf-8")) & QUE_BAJAN)
        for ruta in sorted(_SRC.rglob("*.py"))
        if ruta != _LA_ORDEN_DE_INSTALAR
    }

    assert {ruta: n for ruta, n in culpables.items() if n} == {}


def test_la_orden_de_instalar_si_baja_el_modelo_y_la_voz() -> None:
    nombrados = nombres(_LA_ORDEN_DE_INSTALAR.read_text(encoding="utf-8"))

    assert {"download_model", "download_voice", "urlopen"} <= nombrados


def test_ve_lo_que_baja_se_llame_como_se_llame() -> None:
    fuente = (
        "import huggingface_hub\n"
        "from faster_whisper import download_model as d\n"
        "from faster_whisper.utils import download_model\n"
        "huggingface_hub.snapshot_download('x')\n"
        "Tokenizer.from_pretrained('openai/whisper-tiny')\n"
        "hf_hub_download('x', 'y')\n"
        "from piper.download_voices import download_voice as baja\n"
        "urllib.request.urlopen('https://huggingface.co/x')\n"
    )

    assert nombres(fuente) & QUE_BAJAN == QUE_BAJAN
