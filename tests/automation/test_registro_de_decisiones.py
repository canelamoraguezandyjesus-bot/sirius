"""El registro de decisiones no admite dos ADR con el mismo número (ADR-032).

Esta es la pieza que hace el fallo **imposible** en `main`, no solo improbable:
`scripts/siguiente_adr.py` quita fricción, pero no impide crear un ADR a mano,
y solo ve el árbol local. Esta prueba, en cambio, corre en Quality sobre el
árbol fusionado, así que ningún número repetido llega a `main` en verde.

Hay una excepción, y está fijada nombre por nombre a propósito: el par
`ADR-016` que ya existía cuando se escribió esto. Corregirlo es una decisión
del propietario —hay una veintena de referencias a «ADR-016» en workflows,
pruebas y documentos, y ninguna dice cuál de los dos documentos cita—, y
ADR-032 declaró expresamente que no corrige el pasado. Fijar la excepción por
su nombre es lo que mantiene la prueba anti-vacua: cualquier duplicado nuevo
rompe la igualdad, y arreglar el viejo también, que es cuando toca venir aquí
y borrar la excepción.
"""

from __future__ import annotations

import re
from pathlib import Path

from siguiente_adr import duplicados, numeros_por_archivo, siguiente_numero

REGISTRO = Path(__file__).resolve().parents[2] / "docs" / "decisions"

# El único número repetido tolerado, con los dos archivos que lo usan.
DUPLICADO_HISTORICO = {
    16: [
        "ADR-016-el-auditor-se-lanza-por-etiqueta-y-no-escribe-nunca.md",
        "ADR-016-el-estado-se-lee-de-main-no-de-la-rama.md",
    ]
}

CONVENIO = re.compile(r"^ADR-\d{3,}-[a-z0-9.]+(?:-[a-z0-9.]+)*\.md$")


def test_no_new_number_is_ever_reused() -> None:
    encontrados = duplicados(REGISTRO)
    assert encontrados == DUPLICADO_HISTORICO, (
        "Un número de ADR repetido hace que dos decisiones distintas se citen igual. "
        "Si acabas de crear uno, usa `scripts/siguiente_adr.py`. Si has arreglado el par "
        "ADR-016 histórico, quita DUPLICADO_HISTORICO de esta prueba."
    )


def test_every_adr_follows_the_naming_convention() -> None:
    """Mayúsculas en «ADR», tres dígitos y el resto en minúsculas sin tildes."""
    incumplen = [nombre for nombre in numeros_por_archivo(REGISTRO) if not CONVENIO.match(nombre)]
    assert incumplen == [], f"nombres fuera del convenio de ADR-032: {incumplen}"


def test_the_registry_has_the_template_the_script_needs() -> None:
    assert (REGISTRO / "PLANTILLA.md").is_file()


def test_the_proposed_number_is_free_in_the_real_registry() -> None:
    """Sin fijar un valor: el registro crece y una prueba con «30» caduca al mes."""
    usados = set(numeros_por_archivo(REGISTRO).values())
    propuesto = siguiente_numero(REGISTRO)
    assert propuesto not in usados
    assert propuesto > max(usados)
