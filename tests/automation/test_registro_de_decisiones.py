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

import pytest

from siguiente_adr import (
    REFSPEC_DE_LAS_CABEZAS,
    _como_se_consulto,
    _correr_git,
    duplicados,
    main,
    numeros_en_ramas,
    numeros_por_archivo,
    siguiente_numero,
    traer_las_cabezas,
)

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


# --- ADR-180: el número se calcula contra las ramas del REMOTO ---------------
#
# ADR-044 hizo que el guion mirara las ramas del clon y dejó su límite escrito:
# «solo ve las ramas TRAÍDAS». El 12-09-2026 ese límite se cobró tres ADR-177 a
# la vez -PR #590, #591 y #593-, dos de ellos renumerados a mano. Medido ese
# día: el clon tenía 14 refs remotas de las 409 del remoto, el 3,4 %, y traerlas
# todas costaba 4 segundos.


def _git_que_trae(
    exito: bool, registro: list[list[str]]
) -> Callable[[list[str], Path], tuple[bool, str]]:
    """Sustituto de git que apunta lo que se le pide y contesta lo que se le diga."""

    def correr(argumentos: list[str], _raiz: Path) -> tuple[bool, str]:
        registro.append(argumentos)
        return exito, ""

    return correr


def test_traer_las_cabezas_pide_todas_y_no_solo_las_que_el_clon_tenga(tmp_path: Path) -> None:
    """El refspec explícito es el cambio: sin él, un clon estrecho se queda como nació.

    Una sesión remota clona una sola rama, y `git fetch origin` a secas respeta
    ese refspec estrecho: seguiría viendo 14 de 409.
    """
    pedido: list[list[str]] = []
    assert traer_las_cabezas(_registro(tmp_path, []), _git_que_trae(True, pedido))
    assert pedido == [["fetch", "--quiet", "origin", REFSPEC_DE_LAS_CABEZAS]]
    assert REFSPEC_DE_LAS_CABEZAS == "+refs/heads/*:refs/remotes/origin/*"


def test_si_no_se_pueden_traer_las_cabezas_el_guion_no_aborta(tmp_path: Path) -> None:
    """Sin red, sin git o fuera de un repositorio: se degrada, nunca se aborta.

    Quedarse sin crear el ADR es peor que crearlo con la cobertura de ayer.
    """
    registro = _registro(tmp_path, ["ADR-041-x.md"])
    assert traer_las_cabezas(registro, _git_que_trae(False, [])) is False
    # Y el número se sigue calculando, con lo que hubiera.
    assert siguiente_numero(registro) == 42


def test_el_aviso_distingue_haber_traido_de_no_haber_podido() -> None:
    """Las dos situaciones piden cosas distintas de quien lee, y antes se decían igual.

    `git fetch --quiet` no imprime nada cuando va bien, así que con la forma
    anterior -solo la salida- «trajo» y «no pudo» eran la misma cadena vacía.
    """
    trajo = _como_se_consulto(409, trajo=True)
    no_pudo = _como_se_consulto(14, trajo=False)

    assert "409" in trajo
    assert "NO" not in trajo
    assert "14" in no_pudo
    assert "NO se pudieron traer" in no_pudo
    assert "git fetch" in no_pudo, "quien lee tiene que saber qué hacer al respecto"
    assert trajo != no_pudo


def test_el_guion_trae_antes_de_calcular_y_sin_traer_lo_impide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """La mitad que importa: que traer ocurra ANTES de calcular, en la pasada real.

    Se comprueba sobre `main`, no sobre la función suelta, porque el defecto de
    ADR-180 no era que `traer_las_cabezas` no existiera: era que nadie la
    llamaba antes de decidir el número.
    """
    import siguiente_adr

    registro = _registro(tmp_path, ["ADR-041-x.md"])
    llamadas: list[str] = []

    def traer_falso(_directorio: Path, _correr: object = None) -> bool:
        llamadas.append("traer")
        return True

    def numeros_falsos(_directorio: Path, _ejecutar: object = None) -> dict[int, list[str]]:
        llamadas.append("calcular")
        return {}

    monkeypatch.setattr(siguiente_adr, "traer_las_cabezas", traer_falso)
    monkeypatch.setattr(siguiente_adr, "numeros_en_ramas", numeros_falsos)

    assert main(["--solo-numero", "--directorio", str(registro)]) == 0
    assert llamadas == ["traer", "calcular"], "traer tiene que ocurrir antes de calcular"
    assert capsys.readouterr().out.strip() == "42"

    llamadas.clear()
    assert main(["--solo-numero", "--sin-traer", "--directorio", str(registro)]) == 0
    assert llamadas == ["calcular"], "--sin-traer no debe traer nada"


def test_correr_git_distingue_de_verdad_un_fallo_de_una_salida_vacia(tmp_path: Path) -> None:
    """La única prueba que ejercita git DE VERDAD, y la que faltaba.

    Lo encontró una mutación: devolviendo siempre `True` en `_correr_git`, las
    once pruebas seguían en verde, porque todas las demás inyectan un git de
    mentira. Y sobre ese booleano descansa todo lo que ADR-180 dice en voz
    alta: si «no pude traer» se cuela como «traje», el guion afirmaría una
    cobertura que no tiene, que es peor que la cobertura parcial de ayer.

    Los dos casos con git real: uno que funciona y no imprime casi nada, y uno
    que falla. Si git no estuviera instalado, el primero también daría `False`
    y la prueba lo dice en vez de pasar en vacío.
    """
    funciono, salida = _correr_git(["--version"], tmp_path)
    assert funciono, "sin git instalado esta prueba no puede medir nada"
    assert "git" in salida.lower()

    fallo, vacia = _correr_git(["rev-parse", "--esta-opcion-no-existe"], tmp_path)
    assert fallo is False
    assert vacia == ""
