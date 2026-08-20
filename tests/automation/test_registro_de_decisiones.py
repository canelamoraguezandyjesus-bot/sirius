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
from collections.abc import Callable
from pathlib import Path

from siguiente_adr import duplicados, numeros_en_ramas, numeros_por_archivo, siguiente_numero

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


# --- El número no se elige solo con lo que hay en este árbol (ADR-044) ---------
#
# Estas pruebas existen por un fallo real: el 20-08-2026 el arreglo de Qt y el
# bloque A5 crearon a la vez un `ADR-042` cada uno en ramas distintas. Ninguno de
# los dos árboles veía al otro, el guion propuso 42 a los dos, y la colisión solo
# apareció al fusionar: Quality en rojo y la incidencia #206 atascada. El mismo
# día estuvo a punto de repetirse con el 043.


def _git_de_mentira(ramas: dict[str, list[str]]) -> Callable[[list[str], Path], str]:
    """Sustituto de git que responde lo que le digamos, no lo que haya en el clon.

    Se inyecta para que la prueba sea función de sus argumentos: si leyera las
    ramas de verdad mediría el estado del clon en que corre, no el código.
    """

    def ejecutar(argumentos: list[str], _raiz: Path) -> str:
        if argumentos[0] == "for-each-ref":
            return "\n".join(ramas) + "\n"
        if argumentos[0] == "ls-tree":
            return "\n".join(ramas.get(argumentos[2], [])) + "\n"
        return ""

    return ejecutar


def _registro(tmp_path: Path, nombres: list[str]) -> Path:
    registro = tmp_path / "decisions"
    registro.mkdir()
    for nombre in nombres:
        (registro / nombre).write_text("# adr\n", encoding="utf-8")
    return registro


def test_a_number_taken_by_an_unmerged_branch_is_not_offered_again(tmp_path: Path) -> None:
    """El caso exacto que rompió main: dos ramas vivas sobre el mismo registro."""
    registro = _registro(tmp_path, ["ADR-041-uno.md", "ADR-042-dos.md"])
    ramas = {"refs/remotes/origin/feature/a5": ["decisions/ADR-043-de-otra-rama.md"]}

    reservados = numeros_en_ramas(registro, _git_de_mentira(ramas))

    assert 43 in reservados, "no vio el ADR que ya existe en otra rama"
    assert siguiente_numero(registro, reservados) == 44
    # Y la mitad que hace la prueba no vacua: sin mirar las ramas, colisiona.
    assert siguiente_numero(registro) == 43


def test_reading_the_branches_never_breaks_the_script(tmp_path: Path) -> None:
    """Sin git, fuera de un repositorio o con el clon a medias: degrada, no aborta."""
    registro = _registro(tmp_path, ["ADR-041-uno.md"])

    def git_mudo(_argumentos: list[str], _raiz: Path) -> str:
        return ""

    assert numeros_en_ramas(registro, git_mudo) == {}
    assert siguiente_numero(registro, {}) == 42


def test_a_branch_that_only_has_older_adrs_does_not_move_the_number(tmp_path: Path) -> None:
    """Una rama vieja no empuja el número hacia arriba: solo cuenta el máximo."""
    registro = _registro(tmp_path, ["ADR-041-uno.md", "ADR-042-dos.md"])
    ramas = {"refs/remotes/origin/vieja": ["decisions/ADR-030-antigua.md"]}

    reservados = numeros_en_ramas(registro, _git_de_mentira(ramas))

    assert reservados == {30: ["refs/remotes/origin/vieja"]}
    assert siguiente_numero(registro, reservados) == 43
