"""Pruebas del calculador de número de ADR (ADR-032).

Cada prueba fija una PROPIEDAD, no una grafía concreta: «el número propuesto es
mayor que todos los existentes», no «el número es 28». Enumerar valores es la
primera forma de prueba vacua del catálogo de patrones, y aquí se nota en
seguida: el registro real crece, y una prueba que espere «28» miente al mes
siguiente.

Los laboratorios traen su propia plantilla mínima en vez de la real, para que
un cambio de redacción en `PLANTILLA.md` no tumbe pruebas que no hablan de
ella. Lo que sí se comprueba contra el archivo real es que siga teniendo los
dos marcadores que el guion necesita: si se pierden, el guion se niega a
escribir, y esa prueba avisa antes de que ocurra.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

import siguiente_adr
from siguiente_adr import (
    crear_adr,
    duplicados,
    nombre_de_archivo,
    normalizar_titulo,
    numeros_por_archivo,
    rellenar_plantilla,
    siguiente_numero,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GUION = REPO_ROOT / "scripts" / "siguiente_adr.py"
PLANTILLA_REAL = REPO_ROOT / "docs" / "decisions" / "PLANTILLA.md"

PLANTILLA_LAB = (
    "# ADR-NNN — [Título en imperativo]\n"
    "\n"
    "- Estado: PROPUESTO\n"
    "- Fecha: AAAA-MM-DD\n"
    "\n"
    "## Contexto y problema\n"
)

FECHA = date(2026, 8, 17)


def _registro(tmp_path: Path, *nombres: str, plantilla: str = PLANTILLA_LAB) -> Path:
    """Registro de laboratorio con los ADR indicados y una plantilla propia."""
    directorio = tmp_path / "decisions"
    directorio.mkdir()
    (directorio / "PLANTILLA.md").write_text(plantilla, encoding="utf-8")
    (directorio / "README.md").write_text("registro\n", encoding="utf-8")
    for nombre in nombres:
        (directorio / nombre).write_text("# adr\n", encoding="utf-8")
    return directorio


# --------------------------------------------------------------------------- #
# El número: máximo + 1, y los huecos no vuelven
# --------------------------------------------------------------------------- #


def test_the_next_number_beats_every_existing_one(tmp_path: Path) -> None:
    directorio = _registro(tmp_path, "ADR-001-a.md", "ADR-016-b.md", "ADR-027-c.md")
    propuesto = siguiente_numero(directorio)
    assert propuesto > max(numeros_por_archivo(directorio).values())


def test_historical_gaps_are_never_reused(tmp_path: Path) -> None:
    """La razón de ser del guion: 017 y 018 están libres y no vuelven jamás.

    Reutilizarlos haría que un mismo número apuntara a decisiones distintas
    según la fecha del clon.
    """
    directorio = _registro(tmp_path, "ADR-001-a.md", "ADR-002-b.md", "ADR-005-c.md")
    propuesto = siguiente_numero(directorio)
    assert propuesto == 6
    assert propuesto not in {3, 4}


def test_the_last_file_counts_as_much_as_the_first(tmp_path: Path) -> None:
    """El máximo se busca en todo el directorio, no en el primer archivo.

    El orden alfabético pone ADR-001 primero; quedarse ahí propondría 002 y
    machacaría un ADR existente.
    """
    directorio = _registro(tmp_path, "ADR-001-a.md", "ADR-002-b.md", "ADR-030-z.md")
    assert siguiente_numero(directorio) == 31


def test_an_empty_registry_starts_at_one(tmp_path: Path) -> None:
    assert siguiente_numero(_registro(tmp_path)) == 1


def test_a_duplicated_number_does_not_shift_the_next_one(tmp_path: Path) -> None:
    """El registro real tiene dos ADR-016; eso no altera el cálculo."""
    directorio = _registro(tmp_path, "ADR-016-uno.md", "ADR-016-dos.md", "ADR-020-x.md")
    assert siguiente_numero(directorio) == 21


def test_a_number_without_title_still_occupies_it(tmp_path: Path) -> None:
    directorio = _registro(tmp_path, "ADR-030.md")
    assert siguiente_numero(directorio) == 31


def test_lowercase_spelling_does_not_hide_a_taken_number(tmp_path: Path) -> None:
    """En Windows `adr-030-x.md` y `ADR-030-x.md` son el mismo archivo."""
    directorio = _registro(tmp_path, "adr-030-x.md")
    assert siguiente_numero(directorio) == 31


def test_files_that_are_not_adrs_are_ignored(tmp_path: Path) -> None:
    directorio = _registro(tmp_path, "ADR-004-a.md", "NOTAS-999-b.md", "ADR-borrador.md")
    assert siguiente_numero(directorio) == 5


def test_a_missing_registry_is_an_error_not_a_one(tmp_path: Path) -> None:
    """Sin directorio, devolver 1 crearía un ADR-001 encima de un registro real
    mal enrutado. Mejor fallar."""
    with pytest.raises(NotADirectoryError):
        siguiente_numero(tmp_path / "no-existe")


def test_duplicates_are_reported_with_their_files(tmp_path: Path) -> None:
    directorio = _registro(tmp_path, "ADR-016-uno.md", "ADR-016-dos.md", "ADR-017-x.md")
    assert duplicados(directorio) == {16: ["ADR-016-dos.md", "ADR-016-uno.md"]}


# --------------------------------------------------------------------------- #
# El nombre: el convenio que ya siguen los ADR del registro
# --------------------------------------------------------------------------- #


def test_diacritics_are_stripped_as_the_registry_does() -> None:
    """ADR-002 «automatizacion», ADR-004 «periodica», ADR-007 «limite»."""
    assert normalizar_titulo("Automatización periódica del límite") == (
        "automatizacion-periodica-del-limite"
    )


def test_enye_becomes_n() -> None:
    assert normalizar_titulo("El año del diseño") == "el-ano-del-diseno"


def test_version_dots_survive() -> None:
    """ADR-012 termina en `sirius-0.1`: los puntos son parte del convenio."""
    assert normalizar_titulo("Frontera de confianza de Sirius 0.1") == (
        "frontera-de-confianza-de-sirius-0.1"
    )


def test_punctuation_never_leaves_double_or_edge_separators() -> None:
    generado = normalizar_titulo("  ¿Qué hacer?, ¡«esto» sí!  ")
    assert "--" not in generado
    assert not generado.startswith("-")
    assert not generado.endswith("-")
    assert generado == "que-hacer-esto-si"


def test_a_title_without_usable_characters_is_refused() -> None:
    with pytest.raises(ValueError):
        normalizar_titulo("¿¡«»!?")


def test_the_number_is_padded_to_three_digits() -> None:
    assert nombre_de_archivo(1, "Probar algo").startswith("ADR-001-")
    assert nombre_de_archivo(29, "Probar algo").startswith("ADR-029-")


def test_a_number_beyond_three_digits_is_not_truncated() -> None:
    assert nombre_de_archivo(1000, "Probar algo").startswith("ADR-1000-")


# --------------------------------------------------------------------------- #
# La creación: rellenar sin adivinar, y no destruir nunca
# --------------------------------------------------------------------------- #


def test_creating_an_adr_fills_number_title_and_date(tmp_path: Path) -> None:
    directorio = _registro(tmp_path, "ADR-028-previo.md")
    destino = crear_adr(directorio, "Contar los ADR bien", FECHA)
    assert destino.name == "ADR-029-contar-los-adr-bien.md"
    contenido = destino.read_text(encoding="utf-8")
    assert contenido.startswith("# ADR-029 — Contar los ADR bien\n")
    assert "- Fecha: 2026-08-17" in contenido
    assert "AAAA-MM-DD" not in contenido
    assert "## Contexto y problema" in contenido, "el resto de la plantilla se conserva"


def test_a_wrong_number_never_destroys_an_existing_adr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Segunda línea de defensa: si el cálculo del número se estropeara, el
    guion no puede llevarse por delante un ADR ya escrito.

    El fallo se fuerza a propósito porque por el camino normal la guarda es
    INALCANZABLE —máximo+1 nunca choca con nada—, y una prueba que no puede
    fallar no fija ninguna propiedad. Se escribió primero como
    «crear dos veces y esperar el choque», pasó en vacío, y se rehízo.
    """
    directorio = _registro(tmp_path, "ADR-028-previo.md")
    victima = directorio / "ADR-028-previo.md"
    # El doble acepta `reservados` porque la firma real lo lleva desde ADR-044;
    # lo que la prueba fija no es la firma, es que un numero equivocado no
    # se lleve por delante un ADR ya escrito.
    monkeypatch.setattr(siguiente_adr, "siguiente_numero", lambda _directorio, _reservados=(): 28)
    with pytest.raises(FileExistsError):
        crear_adr(directorio, "Previo", FECHA)
    assert victima.read_text(encoding="utf-8") == "# adr\n", "el ADR existente sigue intacto"


def test_a_template_without_the_header_marker_is_refused(tmp_path: Path) -> None:
    """Rellenar a ciegas dejaría un ADR con «ADR-NNN» en la cabecera."""
    directorio = _registro(tmp_path, plantilla="- Fecha: AAAA-MM-DD\n")
    with pytest.raises(ValueError):
        crear_adr(directorio, "Sin cabecera", FECHA)
    assert list(directorio.glob("ADR-*.md")) == [], "no se escribe nada si no se puede rellenar"


def test_a_template_without_the_date_marker_is_refused(tmp_path: Path) -> None:
    directorio = _registro(tmp_path, plantilla="# ADR-NNN — [Titulo]\n")
    with pytest.raises(ValueError):
        crear_adr(directorio, "Sin fecha", FECHA)


def test_a_missing_template_is_refused(tmp_path: Path) -> None:
    directorio = _registro(tmp_path)
    (directorio / "PLANTILLA.md").unlink()
    with pytest.raises(FileNotFoundError):
        crear_adr(directorio, "Sin plantilla", FECHA)


def test_the_same_arguments_always_give_the_same_file(tmp_path: Path) -> None:
    """Determinismo: el reloj no entra en el resultado, la fecha se inyecta."""
    uno = rellenar_plantilla(PLANTILLA_LAB, 29, "Contar los ADR bien", FECHA)
    otro = rellenar_plantilla(PLANTILLA_LAB, 29, "Contar los ADR bien", FECHA)
    assert uno == otro


def test_the_real_template_still_has_the_markers_the_script_needs() -> None:
    """Si alguien reescribe PLANTILLA.md y se lleva un marcador, el guion deja
    de escribir. Que se entere aquí y no al crear un ADR con prisa."""
    generado = rellenar_plantilla(
        PLANTILLA_REAL.read_text(encoding="utf-8"), 29, "Un titulo", FECHA
    )
    assert generado.startswith("# ADR-029 — Un titulo\n")
    assert "- Fecha: 2026-08-17" in generado


# --------------------------------------------------------------------------- #
# La interfaz de línea de órdenes, como la invoca la skill
# --------------------------------------------------------------------------- #


def _ejecutar(*argumentos: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GUION), *argumentos],
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
        timeout=60,
    )


def test_the_cli_reports_the_next_number_without_creating_anything(tmp_path: Path) -> None:
    directorio = _registro(tmp_path, "ADR-028-previo.md")
    resultado = _ejecutar("--directorio", str(directorio), "--solo-numero", cwd=tmp_path)
    assert resultado.returncode == 0
    assert resultado.stdout.strip() == "29"
    assert list(directorio.glob("ADR-029*.md")) == []


def test_the_cli_creates_the_adr_and_prints_its_path(tmp_path: Path) -> None:
    directorio = _registro(tmp_path, "ADR-028-previo.md")
    resultado = _ejecutar(
        "Contar los ADR bien",
        "--directorio",
        str(directorio),
        "--fecha",
        "2026-08-17",
        cwd=tmp_path,
    )
    assert resultado.returncode == 0
    creado = directorio / "ADR-029-contar-los-adr-bien.md"
    assert creado.is_file()
    assert resultado.stdout.strip().endswith("ADR-029-contar-los-adr-bien.md")


def test_the_cli_warns_about_existing_duplicates(tmp_path: Path) -> None:
    directorio = _registro(tmp_path, "ADR-016-uno.md", "ADR-016-dos.md")
    resultado = _ejecutar("--directorio", str(directorio), "--solo-numero", cwd=tmp_path)
    assert resultado.returncode == 0
    assert "ADR-016" in resultado.stderr


def test_the_cli_refuses_to_run_without_a_title(tmp_path: Path) -> None:
    directorio = _registro(tmp_path)
    resultado = _ejecutar("--directorio", str(directorio), cwd=tmp_path)
    assert resultado.returncode == 2
    assert list(directorio.glob("ADR-*.md")) == []
