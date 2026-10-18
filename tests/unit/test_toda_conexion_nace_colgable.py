"""La guarda de ADR-255: ningún cliente de red de Sirius se construye fuera de la fábrica.

Así toda petición nueva nace colgable, y cerrar Sirius la corta sea del trabajo que sea:
eso es imposible, no improbable. Sin esta guarda, cada ronda de Codex encontraba otro
trabajador que el cierre no cortaba (familia ``cierre-que-no-corta-todo-lo-que-pide``:
dos en la ronda 1 sobre la #698 y cuatro en la ronda 2).
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SRC = RAIZ / "src"
FABRICA = "sirius/infrastructure/network.py"

#: Lo que abre una conexión por su cuenta: un cliente, una petición suelta o un socket.
CONSTRUCCIONES = frozenset(
    {
        "httpx.Client",
        "httpx.AsyncClient",
        "httpx.get",
        "httpx.post",
        "httpx.put",
        "httpx.patch",
        "httpx.delete",
        "httpx.head",
        "httpx.options",
        "httpx.request",
        "httpx.stream",
        "openai.OpenAI",
        "openai.AsyncOpenAI",
        "OpenAI",
        "AsyncOpenAI",
        "socket.create_connection",
        "create_connection",
        "urllib.request.urlopen",
        "urlopen",
    }
)

#: Las que se quedan fuera de la fábrica a propósito, cada una con su porqué.
EXCEPCIONES = {
    (
        "sirius/adapters/capture/websocket_client.py",
        "socket.create_connection",
    ): "la orden de captura no se cuelga: el cierre la espera, como a la copia, para saber "
    "cómo quedó la grabación (ADR-255)",
    (
        "sirius/install_local_voice.py",
        "urllib.request.urlopen",
    ): "la descarga de las voces es una orden de consola en primer plano, sin ventana que "
    "cerrar: la corta Ctrl+C",
}


def _nombre(nodo: ast.expr) -> str | None:
    """``httpx.Client`` de ``httpx.Client(...)``; ``None`` si no es un nombre con puntos."""
    if isinstance(nodo, ast.Name):
        return nodo.id
    if isinstance(nodo, ast.Attribute):
        base = _nombre(nodo.value)
        return f"{base}.{nodo.attr}" if base else None
    return None


def construcciones(fuente: str) -> list[str]:
    """Lo que ``fuente`` construye de ``CONSTRUCCIONES``, en orden."""
    return [
        nombre
        for nodo in ast.walk(ast.parse(fuente))
        if isinstance(nodo, ast.Call)
        and (nombre := _nombre(nodo.func)) is not None
        and nombre in CONSTRUCCIONES
    ]


def _encontradas() -> set[tuple[str, str]]:
    return {
        (ruta.relative_to(SRC).as_posix(), nombre)
        for ruta in SRC.rglob("*.py")
        if ruta.relative_to(SRC).as_posix() != FABRICA
        for nombre in construcciones(ruta.read_text(encoding="utf-8"))
    }


def test_ningun_cliente_de_red_se_construye_fuera_de_la_fabrica() -> None:
    fuera = _encontradas() - EXCEPCIONES.keys()
    assert not fuera, (
        f"Se construye un cliente de red fuera de `{FABRICA}`: {sorted(fuera)}. Usa "
        "`http_client` u `openai_client`, para que cerrar Sirius lo pueda colgar (ADR-255)."
    )


def test_cada_excepcion_sigue_haciendo_falta() -> None:
    sobran = EXCEPCIONES.keys() - _encontradas()
    assert not sobran, f"Estas excepciones ya no se usan: quítalas. {sorted(sobran)}"


def test_la_guarda_ve_un_cliente_puesto_a_mano() -> None:
    fuente = (
        "import httpx\n"
        "import openai\n"
        "from openai import OpenAI\n"
        "def f():\n"
        "    httpx.Client(timeout=5)\n"
        "    openai.OpenAI(api_key='x')\n"
        "    OpenAI()\n"
        "    httpx.post('http://127.0.0.1')\n"
    )

    assert construcciones(fuente) == ["httpx.Client", "openai.OpenAI", "OpenAI", "httpx.post"]


def test_la_guarda_no_confunde_un_tipo_con_una_construccion() -> None:
    fuente = "import httpx\ndef f(client: httpx.Client | None = None) -> httpx.Client: ...\n"

    assert construcciones(fuente) == []
