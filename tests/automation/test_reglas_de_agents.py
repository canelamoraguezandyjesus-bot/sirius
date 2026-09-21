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
se le pregunta y sigue citando el ADR que lo decidió; y, desde ADR-213, que
siguen las tres reglas de conversación que dijo en septiembre de 2026 y que se
violaron después de dichas porque no estaban escritas (contestar primero, el
parte de la mañana, lo del ordenador en lote). No comprueba que nadie pregunte
de más ni que nadie conteste tarde: eso es texto libre y ninguna guarda puede
leer su intención. Lo que sí impide es que la regla desaparezca del sitio
donde se lee.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS = REPO_ROOT / "AGENTS.md"

#: Las tres categorías por las que sí se pregunta, con las palabras del
#: propietario del 20-09-2026.
CATEGORIAS_PREGUNTABLES = ("Dinero", "Salud y seguridad", "Cambio de producto")

#: Las tres reglas de septiembre de 2026 (ADR-213), con las palabras con que
#: `AGENTS.md` las titula. Viven en la sección de ADR-208, detrás de las diez.
#: La regla 12 tiene tres partes y se vigilan por separado: quitar solo «y qué
#: le toca a él» dejaba la guarda en verde (revisión de Codex de la PR #658,
#: 21-09-2026).
REGLAS_DE_SEPTIEMBRE = (
    "Contesta primero, trabaja después",
    "qué hiciste, qué no y por qué",
    "y qué le toca a él",
    "Lo del ordenador, en lote",
)
SECCION_DE_CONVERSACION = "## Cómo conversa el propietario, y qué espera (ADR-208)"


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


def cuerpo_de_la_seccion_de_conversacion(agents: str) -> str:
    """El texto de la sección de ADR-208 y solo ese: desde su encabezado hasta el
    siguiente `## `. Sin el corte, una frase que se mudara a otra sección más
    abajo seguiría dando la guarda por buena (segunda pasada de Codex sobre la
    PR #658, 21-09-2026)."""
    partes = agents.split(SECCION_DE_CONVERSACION, 1)
    assert len(partes) == 2, (
        "AGENTS.md ha perdido la sección de cómo conversa el propietario (ADR-208)"
    )
    return partes[1].split("\n## ", 1)[0]


@pytest.mark.parametrize("regla", REGLAS_DE_SEPTIEMBRE)
def test_las_tres_reglas_de_septiembre_siguen_en_agents(agents: str, regla: str) -> None:
    """ADR-213: cada una se violó después de dicha porque no estaba donde la sesión lee."""
    assert regla in cuerpo_de_la_seccion_de_conversacion(agents), (
        f"AGENTS.md ya no dice «{regla}» en la sección de cómo conversa el "
        "propietario (ADR-213). La regla vuelve a vivir solo en una conversación."
    )
