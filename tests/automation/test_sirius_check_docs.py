"""Pruebas de ``scripts/automation/sirius_check_docs.py`` (bloque C3a, incidencia #246).

Solo las cuatro comprobaciones medidas entran (ver el docstring del script y
el comentario de medición de la incidencia): referencias a fichero rotas
(con sus dos filtros y su clasificación por rama), un solo `h1`, sin saltos
de nivel de encabezado, y enlaces vacíos. Cada comprobación se ve
fallar con un defecto sembrado (ADR-001, prueba por mutación), incluido el
control negativo de que una ruta inventada dentro de un bloque de código no
avisa.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "automation" / "sirius_check_docs.py"


def _module() -> Any:
    name = "sirius_check_docs_under_test"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sin_ramas(_ruta: str) -> list[str]:
    """Doble determinista: ninguna rama conoce el fichero citado."""
    return []


def _escribir(tmp_path: Path, texto: str, nombre: str = "doc.md") -> Path:
    ruta = tmp_path / nombre
    ruta.write_text(texto, encoding="utf-8")
    return ruta


# --- 1. Toda referencia a fichero resuelve ------------------------------------


def test_una_cita_rota_fuera_de_bloque_se_detecta_si_vive_en_una_rama(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m = _module()
    monkeypatch.setattr(m, "_ramas_con_ruta", lambda ruta: ["origin/rama-de-prueba"])
    doc = _escribir(tmp_path, "# Título\n\nCita rota: `docs/esto_no_existe_de_verdad.md`.\n")
    hallazgos = m.comprobar_documento(doc)
    assert any("docs/esto_no_existe_de_verdad.md" in h.mensaje for h in hallazgos)
    assert any("origin/rama-de-prueba" in h.mensaje for h in hallazgos)


def test_una_cita_rota_dentro_de_un_bloque_de_codigo_no_se_avisa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Control negativo: sin él, la prueba de arriba pasaría con el extractor roto."""
    m = _module()
    monkeypatch.setattr(m, "_ramas_con_ruta", lambda ruta: ["origin/rama-de-prueba"])
    doc = _escribir(
        tmp_path,
        "# Título\n\n```\n`docs/esto_no_existe_de_verdad.md`\n```\n",
    )
    hallazgos = m.comprobar_documento(doc)
    assert hallazgos == []


def test_una_cita_rota_que_no_vive_en_ninguna_rama_conocida_no_se_avisa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Medido: 4 de 7 avisos sin este filtro eran ficheros que no existen en ningún sitio."""
    m = _module()
    monkeypatch.setattr(m, "_ramas_con_ruta", _sin_ramas)
    doc = _escribir(tmp_path, "# Título\n\nCita rota: `docs/esto_no_existe_en_ningun_sitio.md`.\n")
    assert m.comprobar_documento(doc) == []


def test_una_ruta_con_puntos_suspensivos_no_se_avisa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Filtro medido: -2 falsos positivos sobre este árbol."""
    m = _module()
    monkeypatch.setattr(m, "_ramas_con_ruta", lambda ruta: ["origin/rama-de-prueba"])
    for placeholder in ("docs/.../algo.py", "docs/…/algo.py"):
        doc = _escribir(tmp_path, f"# Título\n\nCita: `{placeholder}`.\n")
        assert m.comprobar_documento(doc) == [], placeholder


def test_la_palabra_rama_en_el_contexto_previo_descarta_la_cita(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Filtro medido: -3 falsos positivos. Es la forma en que el defecto real
    número 2 de la incidencia #246 se repara: nombrando la rama en la frase."""
    m = _module()
    monkeypatch.setattr(m, "_ramas_con_ruta", lambda ruta: ["origin/rama-de-prueba"])
    doc = _escribir(
        tmp_path,
        "# Título\n\nVive en la rama `docs/esto_no_existe_de_verdad.md` sin fusionar.\n",
    )
    assert m.comprobar_documento(doc) == []


def test_un_enlace_relativo_roto_se_detecta_igual_que_una_cita_en_linea(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Las dos sintaxis son una sola comprobación."""
    m = _module()
    monkeypatch.setattr(m, "_ramas_con_ruta", lambda ruta: ["origin/rama-de-prueba"])
    doc = _escribir(tmp_path, "# Título\n\n[ver](docs/esto_no_existe_de_verdad.md)\n")
    hallazgos = m.comprobar_documento(doc)
    assert any("docs/esto_no_existe_de_verdad.md" in h.mensaje for h in hallazgos)


def test_un_enlace_relativo_al_directorio_del_documento_resuelve(tmp_path: Path) -> None:
    """La otra convención de Markdown: relativa al propio fichero, no a la raíz."""
    m = _module()
    (tmp_path / "hermano.md").write_text("# Hermano\n", encoding="utf-8")
    doc = _escribir(tmp_path, "# Título\n\n[ver](./hermano.md)\n")
    assert m.comprobar_documento(doc) == []


@pytest.mark.parametrize(
    "span",
    [
        "origin/main",
        "feat/investigador-por-etiqueta",
        "https://github.com/x/y/pull/189",
        "domain/work_item.py",
    ],
)
def test_lo_que_no_es_una_ruta_de_este_repositorio_se_ignora(span: str) -> None:
    m = _module()
    assert m.ruta_citada(span) is None


def test_los_sufijos_de_cita_se_recortan() -> None:
    m = _module()
    assert (
        m.ruta_citada("docs/decisions/ADR-001-el-metodo-de-evidencia.md:95")
        == "docs/decisions/ADR-001-el-metodo-de-evidencia.md"
    )


def test_un_enlace_vacio_se_detecta_de_verdad(tmp_path: Path) -> None:
    doc = _escribir(tmp_path, "# Título\n\nFalta el destino: [aqui]().\n")
    hallazgos = _module().comprobar_documento(doc)
    assert any("vacío" in h.mensaje for h in hallazgos)


# --- 2. Un solo h1 por documento -----------------------------------------------


def test_mas_de_un_h1_se_detecta(tmp_path: Path) -> None:
    doc = _escribir(tmp_path, "# Uno\n\nTexto.\n\n# Dos\n\nMás texto.\n")
    hallazgos = _module().comprobar_documento(doc)
    assert any("nivel 1" in h.mensaje for h in hallazgos)


def test_exactamente_un_h1_no_se_avisa(tmp_path: Path) -> None:
    doc = _escribir(tmp_path, "# Uno\n\n## Sub\n\nTexto.\n")
    assert _module().comprobar_documento(doc) == []


def test_ningun_h1_se_detecta(tmp_path: Path) -> None:
    doc = _escribir(tmp_path, "## Solo un h2\n\nTexto.\n")
    hallazgos = _module().comprobar_documento(doc)
    assert any("nivel 1" in h.mensaje for h in hallazgos)


# --- 3. Sin saltos de nivel de encabezado --------------------------------------


def test_un_salto_de_h2_a_h4_se_detecta(tmp_path: Path) -> None:
    doc = _escribir(tmp_path, "# Título\n\n## Dos\n\n#### Cuatro\n\nTexto.\n")
    hallazgos = _module().comprobar_documento(doc)
    assert any("salto de nivel" in h.mensaje for h in hallazgos)


def test_encabezados_consecutivos_no_se_avisan(tmp_path: Path) -> None:
    doc = _escribir(tmp_path, "# Título\n\n## Dos\n\n### Tres\n\nTexto.\n")
    assert _module().comprobar_documento(doc) == []


# --- Ruta dentro de un bloque de código: control negativo transversal --------


def test_encabezados_dentro_de_un_bloque_de_codigo_no_cuentan(tmp_path: Path) -> None:
    doc = _escribir(
        tmp_path,
        "# Título\n\n```\n# esto no es un h1 de verdad\n```\n",
    )
    assert _module().comprobar_documento(doc) == []


# --- Las excepciones declaradas siguen haciendo falta -------------------------


def test_las_excepciones_declaradas_siguen_haciendo_falta() -> None:
    """Si la cita ya no aparece o ya resuelve, la excepción sobra (mismo patrón
    que ``test_lo_fijado_como_borrado_lo_cita_de_verdad_quien_dice_citarlo`` en
    ``tests/automation/test_citas_de_los_adr.py``)."""
    m = _module()
    for (doc_relativo, ruta), _motivo in m.CITAS_EXCEPCIONADAS.items():
        documento = REPO_ROOT / doc_relativo
        assert documento.is_file(), f"{doc_relativo} ya no existe: quita su excepción"
        assert not (REPO_ROOT / ruta).exists(), f"{ruta} ya existe: la excepción sobra"


def test_una_cita_exceptuada_no_se_avisa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    m = _module()
    monkeypatch.setattr(m, "_ramas_con_ruta", lambda ruta: ["origin/rama-de-prueba"])
    doc = _escribir(tmp_path, "# Título\n\nCita: `docs/esto_no_existe_de_verdad.md`.\n")
    monkeypatch.setattr(
        m,
        "CITAS_EXCEPCIONADAS",
        {(str(doc), "docs/esto_no_existe_de_verdad.md"): "excepción de prueba"},
    )
    assert m.comprobar_documento(doc) == []


# --- CLI: los tres defectos reales quedan arreglados ---------------------------


_DOCUMENTOS_DEL_DEFECTO = (
    "docs/evolution/SIRIUS_AI_CORE_AND_MODEL_STRATEGY.md",
    "docs/audits/DEFECTOS_ENCONTRADOS_2026-08-20.md",
    "docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md",
    "docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md",
)


def test_los_documentos_del_defecto_pasan_en_verde() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *_DOCUMENTOS_DEL_DEFECTO],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cli_reporta_fichero_linea_y_expectativa_en_un_defecto_sembrado(
    tmp_path: Path,
) -> None:
    doc = _escribir(tmp_path, "# Uno\n\nTexto.\n\n# Dos\n\nMás texto.\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(doc)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert f"{doc.name}:5" in result.stdout
    assert "se esperaba exactamente uno" in result.stdout


def test_cli_sin_defectos_sale_con_cero(tmp_path: Path) -> None:
    doc = _escribir(tmp_path, "# Uno\n\nTexto.\n")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(doc)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_cli_exige_al_menos_un_documento() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0


# --- El script tiene que arrancar donde de verdad se ejecuta -------------------


def test_el_comprobador_arranca_con_el_python_del_runner() -> None:
    """El Work Item lo invoca en el runner, con `python3` a secas, no con `uv`.

    `except A, B:` sin paréntesis es PEP 758, solo desde 3.14. El proyecto se
    valida con 3.14 y Quality lo aprueba; el runner de `ubuntu-latest` usa 3.12
    y el script moriría al arrancar. Es la segunda vez que esta sintaxis se
    cuela: la primera fue en `sirius_convergence.py`, y de ahí salió
    `test_sirius_runner_python_compat.py`.
    """
    import ast

    fuente = SCRIPT.read_text(encoding="utf-8")
    try:
        ast.parse(fuente, filename=str(SCRIPT), feature_version=(3, 12))
    except SyntaxError as exc:
        pytest.fail(
            f"sirius_check_docs.py no compila con Python 3.12 (línea {exc.lineno}): "
            f"{exc.msg}. Los Work Item documentales lo invocan con el `python3` del "
            "runner, no con el intérprete del proyecto."
        )
