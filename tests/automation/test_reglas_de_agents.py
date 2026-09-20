"""Las reglas del propietario que viven en `AGENTS.md` siguen ahí (ADR-204).

POR QUÉ ESTA PRUEBA EXISTE. La regla que gobierna qué se le pregunta al
propietario y qué no la dio él en una conversación, y estuvo catorce meses sin
estar escrita en ninguna parte del repositorio: el paso 3 de la auditoría la
encontró dicha el 24-07-2026 y el paso 4 la vio aplicada el 10-08-2026, sin que
ningún fichero la recogiera. Es la familia
`regla-del-propietario-que-solo-vive-en-una-conversacion`, la misma que ADR-195
nombró.

QUÉ COMPRUEBA, Y NADA MÁS. Que `AGENTS.md` —el fichero que toda IA de este
repositorio lee antes de responder— sigue diciendo las tres cosas por las que
se le pregunta y sigue citando el ADR que lo decidió. No comprueba que nadie
pregunte de más: eso es texto libre y ninguna guarda puede leer su intención.
Lo que sí impide es que la regla desaparezca del sitio donde se lee.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS = REPO_ROOT / "AGENTS.md"

#: Las tres categorías por las que sí se pregunta, con las palabras del
#: propietario del 20-09-2026.
CATEGORIAS_PREGUNTABLES = ("Dinero", "Salud y seguridad", "Cambio de producto")


@pytest.fixture(scope="module")
def agents() -> str:
    return AGENTS.read_text(encoding="utf-8")


def test_agents_declara_que_se_le_pregunta_al_propietario(agents: str) -> None:
    """La sección existe y cita el ADR que la decidió."""
    assert "## Qué se le pregunta al propietario, y qué no (ADR-204)" in agents, (
        "AGENTS.md ha perdido la sección de ADR-204. Es el único sitio donde una "
        "IA de este repositorio lee qué puede preguntarle al propietario."
    )


@pytest.mark.parametrize("categoria", CATEGORIAS_PREGUNTABLES)
def test_las_tres_categorias_preguntables_siguen_nombradas(agents: str, categoria: str) -> None:
    """Quitar una de las tres cambiaría la regla sin que nadie lo notara."""
    assert categoria in agents, (
        f"AGENTS.md ya no nombra «{categoria}» entre lo que se le pregunta al "
        "propietario (ADR-204)."
    )


def test_agents_distingue_arreglar_de_cambiar(agents: str) -> None:
    """La distinción es del propietario y es la que decide casi todos los casos."""
    assert "Arreglar no es cambiar" in agents, (
        "AGENTS.md ha perdido la distinción entre arreglo y cambio de producto. "
        "Sin ella, cualquier corrección se puede leer como cambio de alcance y "
        "vuelve a pararse esperando una respuesta."
    )


def test_lo_irreversible_sigue_pidiendo_decision(agents: str) -> None:
    """ADR-204 amplía la autonomía; no la amplía hasta lo que no se puede deshacer."""
    criterio = agents.split("## Criterio de parada", 1)
    assert len(criterio) == 2, "AGENTS.md ha perdido el criterio de parada"
    assert "irreversible" in criterio[1], (
        "El criterio de parada ya no exige preguntar antes de algo irreversible. "
        "Es la salvaguarda de ADR-204: lo que no se puede archivar, se pregunta."
    )
