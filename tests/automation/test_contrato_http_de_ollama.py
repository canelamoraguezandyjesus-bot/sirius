"""El guardián del contrato HTTP local de Ollama (G1, ADR-132, incidencia #522).

El repositorio tiene tres adaptadores locales de Ollama y un contrato HTTP ya
validado contra el modelo real (ADR-125,
``src/sirius/adapters/ollama_relevance_filter.py:112-132``): ``/api/chat`` (no
``/api/generate``), razonamiento apagado explícitamente (``think``), una URL
absoluta a ``_OLLAMA_LOCAL_BASE_URL`` (nunca relativa a la ``base_url`` de un
cliente inyectado) y ``follow_redirects=False``. Hasta ahora ese contrato solo
vivía por copia entre ficheros: nada impedía que un adaptador nuevo lo
incumpliera. Así incumplía ``ollama_category_classifier.py`` (deuda registrada
en ADR-130, confirmada por la mina de aprendizaje operativo de 2026-09 y causa
de los dos P1 de la incidencia #518) hasta que ADR-132 lo corrigió.

Este guardián descubre TODOS los adaptadores por *glob*
(``src/sirius/adapters/ollama_*.py``), nunca por una lista mantenida a mano:
un cuarto adaptador que aparezca mañana queda cubierto sin tocar esta prueba.
Las cuatro propiedades se comprueban sobre el TEXTO ENTERO de cada fichero, no
sobre la línea del ``.post(``: el propietario midió
(``docs/audits/mina-2026-09-medicion-de-guardianes.md``) que la llamada real
está partida en varias líneas, así que una comprobación por línea la dejaría
pasar por accidente de formato.

Es determinista: lee ficheros de texto y busca subcadenas. No razona, no
invoca ningún modelo, no sale a la red y cuesta milisegundos — igual que
``tests/automation/test_citas_de_los_adr.py``, del que copia el estilo (glob +
parametrize + funciones puras de comprobación, verificadas también con texto
sintético para que un extractor roto no pase en verde sin mirar nada).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
DIRECTORIO_DE_ADAPTADORES = RAIZ / "src" / "sirius" / "adapters"


def _adaptadores_de_ollama() -> list[Path]:
    return sorted(DIRECTORIO_DE_ADAPTADORES.glob("ollama_*.py"))


# --- Las cuatro propiedades del contrato (ADR-125), como funciones puras ------
#
# Puras y sobre texto para poder verificarlas con texto sintético además de
# con los ficheros reales (ver la sección "Anti-vacua" más abajo).


#: Todo lo envuelto en dobles comillas invertidas (`` ``así`` ``, el estilo RST
#: que este repositorio usa en docstrings y comentarios para mencionar código
#: SIN ejecutarlo — por ejemplo, ``ollama_criticality_classifier.py`` explica
#: por contraste por qué NO usa ``/api/generate``, y los tres adaptadores
#: explican en un comentario qué hace ``follow_redirects=False`` antes de la
#: línea que de verdad lo fija). Las cuatro propiedades comprueban sobre el
#: texto SIN esas menciones: si no lo hicieran, una propiedad de presencia
#: (2, 3, 4) podría dar un falso verde cuando el código real se rompe pero el
#: comentario que lo describe sigue ahí, y una propiedad de ausencia (1)
#: podría dar un falso rojo por una mención que no es una petición real.
#: Medido con mutación: quitar el ``follow_redirects=False`` real de
#: ``ollama_category_classifier.py`` dejando su comentario intacto pasaba en
#: verde sin este filtro.
_PROSA_ENTRE_COMILLAS_INVERTIDAS = re.compile(r"``[^`]*``")


def _sin_prosa(texto: str) -> str:
    return _PROSA_ENTRE_COMILLAS_INVERTIDAS.sub("", texto)


def pide_api_chat_no_api_generate(texto: str) -> bool:
    """Propiedad 1: ``/api/chat``, nunca ``/api/generate``."""
    sin_prosa = _sin_prosa(texto)
    return "/api/chat" in sin_prosa and "/api/generate" not in sin_prosa


def apaga_el_pensamiento_explicitamente(texto: str) -> bool:
    """Propiedad 2: el cuerpo de la petición lleva la clave ``"think"``."""
    return '"think"' in _sin_prosa(texto)


def la_url_del_post_es_absoluta(texto: str) -> bool:
    """Propiedad 3: ``_OLLAMA_LOCAL_BASE_URL}/api`` aparece en el fichero.

    Nunca una ruta relativa (``"/api/chat"`` a secas) que dependería de la
    ``base_url`` del cliente inyectado — el mismo cliente que un test seam o
    una configuración remota podría apuntar fuera de ``localhost``.
    """
    return "_OLLAMA_LOCAL_BASE_URL}/api" in _sin_prosa(texto)


def no_sigue_redirecciones(texto: str) -> bool:
    """Propiedad 4: ``follow_redirects=False`` en la llamada."""
    return "follow_redirects=False" in _sin_prosa(texto)


# --- La guarda ------------------------------------------------------------


@pytest.mark.parametrize("adaptador", _adaptadores_de_ollama(), ids=lambda p: p.name)
def test_pide_api_chat_y_no_api_generate(adaptador: Path) -> None:
    texto = adaptador.read_text(encoding="utf-8")
    assert pide_api_chat_no_api_generate(texto), (
        f"{adaptador.name} incumple el contrato validado (ADR-125): debe pedir "
        "'/api/chat' y no debe pedir '/api/generate' — un prompt libre a "
        "'/api/generate' es la causa medida de los P1 de la incidencia #518."
    )


@pytest.mark.parametrize("adaptador", _adaptadores_de_ollama(), ids=lambda p: p.name)
def test_apaga_el_pensamiento_explicitamente(adaptador: Path) -> None:
    texto = adaptador.read_text(encoding="utf-8")
    assert apaga_el_pensamiento_explicitamente(texto), (
        f"{adaptador.name} incumple el contrato validado (ADR-125): el cuerpo de "
        'la petición debe llevar la clave "think" (el apagado explícito del '
        "razonamiento) — sin ella, el modelo Qwen3 por defecto razona durante "
        "minutos antes de contestar."
    )


@pytest.mark.parametrize("adaptador", _adaptadores_de_ollama(), ids=lambda p: p.name)
def test_la_url_del_post_es_absoluta(adaptador: Path) -> None:
    texto = adaptador.read_text(encoding="utf-8")
    assert la_url_del_post_es_absoluta(texto), (
        f"{adaptador.name} incumple el contrato validado (ADR-125): la URL del "
        "POST debe ser absoluta ('_OLLAMA_LOCAL_BASE_URL}/api'), nunca una ruta "
        "relativa a la base_url de un cliente inyectado — de lo contrario un "
        "cliente de prueba o de configuración con base_url remota redirige la "
        "petición fuera de localhost."
    )


@pytest.mark.parametrize("adaptador", _adaptadores_de_ollama(), ids=lambda p: p.name)
def test_no_sigue_redirecciones(adaptador: Path) -> None:
    texto = adaptador.read_text(encoding="utf-8")
    assert no_sigue_redirecciones(texto), (
        f"{adaptador.name} incumple el contrato validado (ADR-125): la llamada "
        "debe fijar follow_redirects=False — sin esto, un 307/308 servido desde "
        "localhost puede reenviar la petición (y el contenido) a un host remoto."
    )


# --- Anti-vacua -------------------------------------------------------------
#
# El corpus real cumple hoy (tras ADR-132), así que las pruebas de arriba
# pasarían igual con las funciones de comprobación rotas. Estas fijan el
# comportamiento con texto sintético, que no depende de cómo esté el
# repositorio hoy — mismo patrón que test_citas_de_los_adr.py.

_TEXTO_CONFORME = (
    "response = client.post(\n"
    '    f"{_OLLAMA_LOCAL_BASE_URL}/api/chat",\n'
    '    json={"think": False},\n'
    "    follow_redirects=False,\n"
    ")\n"
)


def test_el_texto_conforme_pasa_las_cuatro_propiedades() -> None:
    assert pide_api_chat_no_api_generate(_TEXTO_CONFORME)
    assert apaga_el_pensamiento_explicitamente(_TEXTO_CONFORME)
    assert la_url_del_post_es_absoluta(_TEXTO_CONFORME)
    assert no_sigue_redirecciones(_TEXTO_CONFORME)


def test_pedir_api_generate_se_detecta() -> None:
    roto = _TEXTO_CONFORME.replace("/api/chat", "/api/generate")
    assert not pide_api_chat_no_api_generate(roto)


def test_pedir_api_generate_dentro_de_una_f_string_absoluta_tambien_se_detecta() -> None:
    """No solo la ruta relativa entre comillas: también la variante absoluta
    con `_OLLAMA_LOCAL_BASE_URL}/api/generate` en una f-string."""
    roto = 'client.post(f"{_OLLAMA_LOCAL_BASE_URL}/api/generate", follow_redirects=False)'
    assert not pide_api_chat_no_api_generate(roto)


def test_una_mencion_en_prosa_de_api_generate_no_se_confunde_con_una_peticion_real() -> None:
    """El defecto que este guardián casi comete: `ollama_criticality_classifier.py`
    menciona `/api/generate` en su docstring, envuelto en dobles comillas
    invertidas, para explicar por qué NO lo usa (ADR-125). Esa mención no es
    una petición real y no debe hacer fallar la propiedad."""
    prosa = (
        "response = self._client.post(\n"
        '    f"{_OLLAMA_LOCAL_BASE_URL}/api/chat",\n'
        "    follow_redirects=False,\n"
        ")\n"
        "\n"
        '"""not ``/api/generate`` with a free-text prompt, which reasons for minutes."""\n'
    )
    assert pide_api_chat_no_api_generate(prosa)


def test_una_llamada_partida_en_varias_lineas_se_lee_igual() -> None:
    """El defecto medido (mina-2026-09): la llamada real está partida en varias
    líneas, así que la comprobación tiene que ser sobre el fichero entero, no
    sobre la línea del ``.post(``."""
    partido = (
        "response = self._client.post(\n"
        '    f"{_OLLAMA_LOCAL_BASE_URL}"\n'
        '    "/api/chat",\n'
        "    json={\n"
        '        "think": False,\n'
        "    },\n"
        "    follow_redirects=False,\n"
        ")\n"
    )
    assert apaga_el_pensamiento_explicitamente(partido)
    assert no_sigue_redirecciones(partido)


def test_faltar_el_apagado_del_pensamiento_se_detecta() -> None:
    roto = _TEXTO_CONFORME.replace('"think": False', '"stream": False')
    assert not apaga_el_pensamiento_explicitamente(roto)


def test_una_url_relativa_se_detecta() -> None:
    roto = _TEXTO_CONFORME.replace('f"{_OLLAMA_LOCAL_BASE_URL}/api/chat"', '"/api/chat"')
    assert not la_url_del_post_es_absoluta(roto)


def test_faltar_follow_redirects_false_se_detecta() -> None:
    roto = _TEXTO_CONFORME.replace("    follow_redirects=False,\n", "")
    assert not no_sigue_redirecciones(roto)


def test_faltar_follow_redirects_false_se_detecta_aunque_un_comentario_lo_mencione() -> None:
    """El defecto que esta guarda casi comete, cazado por mutación: los tres
    adaptadores traen un comentario que EXPLICA ``follow_redirects=False``
    justo antes de la línea que de verdad lo fija. Quitar solo esa línea
    (mutación real sobre ollama_category_classifier.py) dejaba el comentario
    intacto, y una comprobación que no ignorara la prosa entre comillas
    invertidas habría pasado en verde con el código roto."""
    roto = (
        "response = self._client.post(\n"
        '    f"{_OLLAMA_LOCAL_BASE_URL}/api/chat",\n'
        "    # ``follow_redirects=False`` overrides any injected client that\n"
        "    # sets follow_redirects=True.\n"
        "    json={},\n"
        ")\n"
    )
    assert not no_sigue_redirecciones(roto)


def test_el_barrido_encuentra_los_adaptadores_de_ollama() -> None:
    """Si el glob se rompe, la guarda pasaría en verde sin mirar nada."""
    adaptadores = _adaptadores_de_ollama()
    nombres = {adaptador.name for adaptador in adaptadores}
    assert {
        "ollama_relevance_filter.py",
        "ollama_criticality_classifier.py",
        "ollama_category_classifier.py",
    } <= nombres, f"el barrido no encontró los tres adaptadores conocidos: {nombres}"
