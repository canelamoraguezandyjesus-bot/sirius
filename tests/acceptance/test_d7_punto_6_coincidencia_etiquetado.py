"""D7 punto 6 (SIRIUS-ARQ-0.2 §6.1, §6.5, §8-M11): coincidencia del
etiquetado automático de Ollama contra las etiquetas canónicas del banco.

D7 punto 6 exige medir, antes de fiarse de `category` contra `Memory`/
`Decision` reales, cuánto coincide el etiquetado automático
(`CategoryClassifierPort`) con un canon conocido, publicando la cifra
(aciertos/N) sin fijar ningún umbral exigible — el propietario lo registra en
`docs/evolution/STATUS.md` (sección D7, incidencia #435), junto a D7, a la
vista de esa medición (§9, mismo patrón que D2 fija para el suelo de
cobertura).

Las etiquetas canónicas (`evidence_bank_47_casos_categorias_canonicas.json`)
las fija ADR-116: una regla mecánica, determinista y documentada sobre el
`text` de cada item del canon — nunca una decisión manual item por item — que
`test_las_etiquetas_canonicas_se_recalculan_byte_a_byte`, en
`test_pa_0_2_rec_01_banco_evidencia.py`, recalcula y compara byte a byte
contra este fixture, para que la tabla del ADR y el fichero nunca puedan
divergir en silencio.

Este módulo construye el arnés en dos mecanismos distintos, tal como pide el
objetivo de la incidencia #471:

1. `test_el_arnes_mide_la_coincidencia_de_un_clasificador_con_respuestas_deterministas`
   — corre siempre, en CI: un doble determinista de `CategoryClassifierPort`
   con "las respuestas que Ollama daría" fijadas de antemano (nunca Ollama
   real). Con las respuestas fijadas de antemano y el canon conocidos de
   antemano, la cifra de coincidencia es una constante conocida — esta prueba
   demuestra que el arnés cuenta aciertos y fallos correctamente, no mide
   nada sobre la fiabilidad real de Ollama (eso, ningún doble puede medirlo).
2. `test_medicion_real_de_coincidencia_contra_ollama_local` — el mecanismo
   ejecutable en máquina real, marcado con `requires_real_ollama` para correr
   solo cuando esta máquina expone un Ollama real en `localhost:11434`;
   `pytest.mark.skipif` lo salta automáticamente en cualquier otro sitio,
   incluido este runner de CI, sin necesitar ninguna variable de entorno ni
   paso manual adicional (mismo patrón que `requires_multimedia`,
   `tests/gui/test_qt_playback.py:31-33`). Ejecutarlo de verdad, en una
   máquina con Ollama instalado, es lo que produce la cifra real que M11
   publica en su PR/incidencia como evidencia del encargo — este entorno de
   ejecución no tiene Ollama y no está autorizado a instalarlo, así que esta
   prueba se salta aquí (ver el veredicto de la incidencia #471).

**Denominador: 97 items, no 47 casos.** §6.1/§6.5/§8-M11 escriben la cifra
como "(aciertos/47)", pero `category` es una propiedad de cada item del canon
(`Memory`/`Decision`), no de cada caso (consulta + resultado esperado) — un
caso no tiene contenido propio que clasificar. El banco tiene 97 items y 47
casos (`evidence_bank_47_casos.json`, `conteos`); este módulo mide sobre los
97 items, que es lo que `CategoryClassifierPort.classify` puede recibir, y
dos de ellos (`MEM-009`, `MEM-019`) traen texto vacío — nunca llegaron a
existir como contenido real (mismo criterio que `_load_canon_item` en
`test_pa_0_2_rec_01_banco_evidencia.py`) y se excluyen del denominador, igual
que un clasificador real no tendría nada que clasificar. Denominador real:
95.
"""

from __future__ import annotations

import json
import socket
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from sirius.adapters.ollama_category_classifier import OllamaCategoryClassifierAdapter
from sirius.composition_root import _CATEGORY_CLASSIFIER_MODEL, _CATEGORY_VOCABULARY

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "evidence_bank_47_casos.json"
CANON_CATEGORIES_PATH = (
    Path(__file__).parent / "fixtures" / "evidence_bank_47_casos_categorias_canonicas.json"
)

pytestmark = [pytest.mark.acceptance]


def _fixture() -> Mapping[str, Any]:
    banco: Mapping[str, Any] = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return banco


def _canon_categories() -> Mapping[str, str]:
    contenido: Mapping[str, Any] = json.loads(CANON_CATEGORIES_PATH.read_text(encoding="utf-8"))
    etiquetas: Mapping[str, str] = contenido["etiquetas"]
    return etiquetas


def _items_con_contenido(banco: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [item for item in banco["items"] if item["text"].strip()]


class _ScriptedCategoryClassifier:
    """Doble determinista de `CategoryClassifierPort`: nunca llama a Ollama.
    Responde exactamente lo que este diccionario diga para cada contenido, o
    `None` si el contenido no está en el guion — el mismo contrato de "no sé
    decidir" que el puerto real documenta."""

    def __init__(self, respuestas: Mapping[str, str | None]) -> None:
        self._respuestas = respuestas

    def classify(self, content: str) -> str | None:
        return self._respuestas.get(content)


def _medir_coincidencia(
    items: list[dict[str, Any]], canon: Mapping[str, str], classifier: Any
) -> tuple[int, int]:
    """Ejecuta `classifier.classify` sobre el `text` de cada item y lo
    compara contra su categoría canónica. Devuelve `(aciertos, total)`."""
    aciertos = 0
    for item in items:
        obtenido = classifier.classify(item["text"])
        if obtenido == canon[item["id"]]:
            aciertos += 1
    return aciertos, len(items)


def test_el_arnes_mide_la_coincidencia_de_un_clasificador_con_respuestas_deterministas() -> None:
    """Mecanismo (1): siempre en CI, sin Ollama real. Un doble cuyas
    respuestas se fijan de antemano —el guion "las respuestas que Ollama
    daría" que pide el objetivo de la incidencia— demuestra que el arnés
    cuenta aciertos y fallos correctamente contra un resultado conocido de
    antemano, no una opinión real sobre estos 95 items."""
    banco = _fixture()
    canon = _canon_categories()
    items = _items_con_contenido(banco)
    assert len(items) == 95

    # Guion: acierta en todos salvo los tres primeros items por id, a los
    # que se les asigna deliberadamente una categoría del vocabulario
    # distinta de la canónica — para que el arnés tenga fallos reales que
    # contar, no solo aciertos.
    discrepancias = {item["id"] for item in sorted(items, key=lambda i: i["id"])[:3]}
    respuestas = {
        item["text"]: (
            next(c for c in sorted(_CATEGORY_VOCABULARY) if c != canon[item["id"]])
            if item["id"] in discrepancias
            else canon[item["id"]]
        )
        for item in items
    }
    classifier = _ScriptedCategoryClassifier(respuestas)

    aciertos, total = _medir_coincidencia(items, canon, classifier)

    print(
        f"\nD7 punto 6 (mecanismo de la suite, doble determinista): "
        f"coincidencia={aciertos}/{total} ({aciertos / total:.1%}) — mide el arnés, "
        "no la fiabilidad real de Ollama."
    )
    assert total == 95
    assert aciertos == 95 - len(discrepancias)


_OLLAMA_HOST = "localhost"
_OLLAMA_PORT = 11434


def _real_ollama_available() -> bool:
    try:
        with socket.create_connection((_OLLAMA_HOST, _OLLAMA_PORT), timeout=0.2):
            return True
    except OSError:
        return False


requires_real_ollama = pytest.mark.skipif(
    not _real_ollama_available(),
    reason=(
        "no hay un Ollama real escuchando en localhost:11434 en esta máquina "
        "(D7 punto 6): este mecanismo produce la cifra real de evidencia solo "
        "cuando se ejecuta a propósito en una máquina con Ollama instalado, "
        "nunca en CI"
    ),
)


@requires_real_ollama
def test_medicion_real_de_coincidencia_contra_ollama_local() -> None:
    """Mecanismo (2): la medición real que D7 punto 6 exige, contra el
    `OllamaCategoryClassifierAdapter` real y un Ollama de verdad — nunca se
    ejecuta en este runner de CI (ver `requires_real_ollama` arriba). Quien
    la ejecute a propósito, en una máquina con `ollama serve` corriendo y el
    modelo `_CATEGORY_CLASSIFIER_MODEL` ya descargado, obtiene la cifra real
    que se registra como evidencia del encargo y que el propietario usa para
    fijar el umbral exigible en `docs/evolution/STATUS.md` (§9, D7 punto 6).
    """
    banco = _fixture()
    canon = _canon_categories()
    items = _items_con_contenido(banco)

    classifier = OllamaCategoryClassifierAdapter(_CATEGORY_CLASSIFIER_MODEL, _CATEGORY_VOCABULARY)
    aciertos, total = _medir_coincidencia(items, canon, classifier)

    print(
        f"\nD7 punto 6 (medición real, Ollama local): "
        f"coincidencia={aciertos}/{total} ({aciertos / total:.1%}) — evidencia para "
        "el registro del umbral en docs/evolution/STATUS.md."
    )
    assert 0 <= aciertos <= total
