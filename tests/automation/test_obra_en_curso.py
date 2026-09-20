"""Pruebas de `scripts/automation/sirius_obra_en_curso.py` (ADR-206).

La guarda que impide que dos sesiones se pisen solo vale si **no dice que no
hay solape cuando no puede saberlo**. La mitad de estas pruebas comprueba
exactamente eso: cada forma de no poder afirmarlo sale como «no lo sé», nunca
como «adelante».
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "automation" / "sirius_obra_en_curso.py"


def _cargar() -> ModuleType:
    """Carga el guion por ruta, como hace `test_misma_obra.py`.

    Se registra en `sys.modules` ANTES de ejecutarlo porque el módulo declara
    `dataclass`es: con `from __future__ import annotations`, `dataclasses`
    resuelve las anotaciones buscando el módulo por su nombre, y si no está
    registrado falla al importar.
    """
    spec = importlib.util.spec_from_file_location("sirius_obra_en_curso", SCRIPT)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


_MODULO = _cargar()

LIBRE: int = _MODULO.LIBRE
NO_SE_SABE: int = _MODULO.NO_SE_SABE
SOLAPE: int = _MODULO.SOLAPE
Obra = _MODULO.Obra
leer_obras = _MODULO.leer_obras
main = _MODULO.main
solapes = _MODULO.solapes


def _obras_json(*entradas: dict[str, object]) -> str:
    return json.dumps(list(entradas))


# --------------------------------------------------------------------------- #
# La comparación
# --------------------------------------------------------------------------- #


def test_sin_obras_vivas_no_hay_solape() -> None:
    assert solapes(["docs/a.md"], []) == []


def test_una_obra_que_toca_otro_fichero_no_solapa() -> None:
    otra = Obra("#10", "otra cosa", frozenset({"src/b.py"}))
    assert solapes(["docs/a.md"], [otra]) == []


def test_el_solape_nombra_la_obra_y_los_ficheros_comunes() -> None:
    otra = Obra("#10", "el registro", frozenset({"docs/a.md", "src/b.py"}))
    encontrados = solapes(["docs/a.md", "docs/c.md"], [otra])
    assert len(encontrados) == 1
    assert encontrados[0].obra.pull_request == "#10"
    assert encontrados[0].ficheros == ("docs/a.md",)


def test_la_misma_ruta_con_barras_de_windows_es_la_misma_ruta() -> None:
    """Media casa corre en Windows: sin esto la guarda no vería el solape."""
    otra = Obra("#10", "", frozenset({"docs/a.md"}))
    assert solapes([r"docs\a.md"], [otra])


def test_una_sesion_no_se_detecta_a_si_misma() -> None:
    """Quien ya abrió su pull request declaró su obra; verla es lo esperado."""
    propia = Obra("#652", "lo mío", frozenset({"docs/a.md"}))
    assert solapes(["docs/a.md"], [propia], excluir="#652") == []
    assert solapes(["docs/a.md"], [propia], excluir="#99")


# --------------------------------------------------------------------------- #
# Fail-closed: cada forma de no poder afirmarlo
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "texto",
    [
        pytest.param("{", id="json-roto"),
        pytest.param('{"pull_request": "#1"}', id="no-es-una-lista"),
        pytest.param("[3]", id="entrada-que-no-es-objeto"),
        pytest.param('[{"ficheros": ["a.md"]}]', id="sin-pull_request"),
        pytest.param('[{"pull_request": "#1"}]', id="sin-ficheros"),
        pytest.param('[{"pull_request": "#1", "ficheros": "a.md"}]', id="ficheros-no-es-lista"),
    ],
)
def test_un_listado_que_no_se_entiende_no_es_un_listado_vacio(texto: str) -> None:
    with pytest.raises(ValueError):
        leer_obras(texto)


def test_la_cli_con_un_listado_ilegible_dice_que_no_sabe(tmp_path: Path) -> None:
    fichero = tmp_path / "obras.json"
    fichero.write_text("{", encoding="utf-8")
    assert main(["--obras", str(fichero), "--fichero", "docs/a.md"]) == NO_SE_SABE


def test_la_cli_sin_el_fichero_de_obras_dice_que_no_sabe(tmp_path: Path) -> None:
    assert (
        main(["--obras", str(tmp_path / "no-existe.json"), "--fichero", "docs/a.md"]) == NO_SE_SABE
    )


def test_la_cli_sin_ficheros_declarados_dice_que_no_sabe(tmp_path: Path) -> None:
    fichero = tmp_path / "obras.json"
    fichero.write_text("[]", encoding="utf-8")
    assert main(["--obras", str(fichero)]) == NO_SE_SABE


# --------------------------------------------------------------------------- #
# La CLI en los dos desenlaces buenos
# --------------------------------------------------------------------------- #


def test_la_cli_devuelve_libre_cuando_no_hay_solape(tmp_path: Path) -> None:
    fichero = tmp_path / "obras.json"
    fichero.write_text(
        _obras_json({"pull_request": "#10", "titulo": "otra", "ficheros": ["src/b.py"]}),
        encoding="utf-8",
    )
    assert main(["--obras", str(fichero), "--fichero", "docs/a.md"]) == LIBRE


def test_la_cli_devuelve_solape_y_lo_explica(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fichero = tmp_path / "obras.json"
    fichero.write_text(
        _obras_json({"pull_request": "#10", "titulo": "el registro", "ficheros": ["docs/a.md"]}),
        encoding="utf-8",
    )
    assert main(["--obras", str(fichero), "--fichero", "docs/a.md"]) == SOLAPE
    salida = capsys.readouterr().out
    assert "#10" in salida
    assert "el registro" in salida
    assert "docs/a.md" in salida
