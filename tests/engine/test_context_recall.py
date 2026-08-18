"""``contexto.recuperar`` v0: tres proveedores deterministas (A3, incidencia #193).

Requisitos ejercitados: 2 (una lectura caída no es una ausencia, también
aquí), 4 (``contexto.recuperar`` responde con referencias, no con
afirmaciones), 5 (determinismo), 7 (ninguna prueba accede a la red: los dos
adapters -sistema de ficheros y ``git log``- se ejercitan sobre datos
controlados, y el de ``git`` con un ``ejecutar`` inyectado que nunca invoca
al binario real).
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sirius_engine.adapters.fixture_mirror import FixedGitHubMirrorReader
from sirius_engine.context_recall import (
    EntradaGitLog,
    Referencia,
    buscar_en_arbol_repo,
    buscar_en_historial_git,
    buscar_en_incidencias,
    leer_historial_git,
    recuperar_contexto,
)
from sirius_engine.domain.mirror import EspejoIlegibleError
from sirius_engine.ports.github_mirror import (
    Comentario,
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
)

_REPO = "canelamoraguezandyjesus-bot/sirius"
_AHORA = datetime(2026, 8, 18, 15, 0, tzinfo=UTC)


# --- Proveedor 1: árbol del repositorio -------------------------------------


def test_buscar_en_arbol_repo_encuentra_y_referencia_con_fichero_y_linea(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "b12e.md").write_text(
        "# B12e\n\nB12e quedó bloqueado por decisión.\n", encoding="utf-8"
    )
    (tmp_path / "otro.md").write_text("nada relevante aquí\n", encoding="utf-8")
    (tmp_path / "binario.png").write_bytes(b"\x89PNG\r\n")

    referencias = buscar_en_arbol_repo(tmp_path, "B12e")

    assert referencias == (
        Referencia(tipo="fichero", identificador="docs/b12e.md:1", fragmento="# B12e"),
        Referencia(
            tipo="fichero",
            identificador="docs/b12e.md:3",
            fragmento="B12e quedó bloqueado por decisión.",
        ),
    )


def test_buscar_en_arbol_repo_ignora_directorios_excluidos(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "ficticio.md").write_text("B12e\n", encoding="utf-8")
    referencias = buscar_en_arbol_repo(tmp_path, "B12e")
    assert referencias == ()


def test_buscar_en_arbol_repo_es_determinista(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("consulta\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("consulta\n", encoding="utf-8")
    assert buscar_en_arbol_repo(tmp_path, "consulta") == buscar_en_arbol_repo(tmp_path, "consulta")


# --- Proveedor 2: incidencias y PR ------------------------------------------


def test_buscar_en_incidencias_respeta_el_filtro_de_confianza() -> None:
    puerto = FixedGitHubMirrorReader(
        cuerpos_por_incidencia={(_REPO, 1): LecturaCuerpo(estado=LecturaEstado.OK, cuerpo="")},
        comentarios_por_incidencia={
            (_REPO, 1): LecturaComentarios(
                estado=LecturaEstado.OK,
                comentarios=(
                    Comentario(
                        autor_login="owner-de-verdad",
                        autor_asociacion="OWNER",
                        cuerpo="B12e avanzó en esta ronda.",
                        creado_en=_AHORA,
                    ),
                    Comentario(
                        autor_login="un-tercero",
                        autor_asociacion="NONE",
                        cuerpo="B12e según un tercero sin autoridad.",
                        creado_en=_AHORA,
                    ),
                ),
            )
        },
    )
    referencias, fallidas = buscar_en_incidencias(puerto, repo=_REPO, numeros=[1], consulta="B12e")
    assert fallidas == ()
    assert len(referencias) == 1
    assert referencias[0].identificador == f"{_REPO}#1:comentario:0"


def test_buscar_en_incidencias_fallo_de_lectura_se_reporta_no_se_esconde() -> None:
    """Requisito 2 también en ``contexto.recuperar``: un 503 en una incidencia
    no reduce el resultado a "no hay referencias ahí" sin dejar rastro.
    """
    puerto = FixedGitHubMirrorReader(
        cuerpos_por_incidencia={(_REPO, 1): LecturaCuerpo(estado=LecturaEstado.OK, cuerpo="B12e")}
        # incidencia 2: ni cuerpo ni comentarios configurados -> NO_DISPONIBLE
    )
    referencias, fallidas = buscar_en_incidencias(
        puerto, repo=_REPO, numeros=[1, 2], consulta="B12e"
    )
    assert any(r.identificador.startswith(f"{_REPO}#1") for r in referencias)
    assert "incidencia:2:cuerpo" in fallidas
    assert "incidencia:2:comentarios" in fallidas


# --- Proveedor 3: historial de git ------------------------------------------


def test_buscar_en_historial_git_referencia_por_sha_corto() -> None:
    entradas = (
        EntradaGitLog(sha="a" * 40, asunto="Añade B12e", cuerpo=""),
        EntradaGitLog(sha="b" * 40, asunto="Sin relación", cuerpo="tampoco menciona nada"),
    )
    referencias = buscar_en_historial_git(entradas, "B12e")
    assert referencias == (
        Referencia(tipo="commit", identificador="a" * 12, fragmento="Añade B12e"),
    )


def test_leer_historial_git_propaga_fallo_como_espejo_ilegible(tmp_path: Path) -> None:
    def ejecutar_fallido(argv: list[str], raiz: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv, returncode=1, stdout="", stderr="git no disponible"
        )

    with pytest.raises(EspejoIlegibleError):
        leer_historial_git(tmp_path, ejecutar=ejecutar_fallido)


def test_leer_historial_git_parsea_registros_delimitados(tmp_path: Path) -> None:
    salida = "sha1\x1fAsunto uno\x1fCuerpo uno\x1esha2\x1fAsunto dos\x1f\x1e"

    def ejecutar_falso(argv: list[str], raiz: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, returncode=0, stdout=salida, stderr="")

    entradas = leer_historial_git(tmp_path, ejecutar=ejecutar_falso)
    assert entradas == (
        EntradaGitLog(sha="sha1", asunto="Asunto uno", cuerpo="Cuerpo uno"),
        EntradaGitLog(sha="sha2", asunto="Asunto dos", cuerpo=""),
    )


# --- Orquestación ------------------------------------------------------------


def test_recuperar_contexto_responde_con_referencias_no_con_afirmaciones(
    tmp_path: Path,
) -> None:
    (tmp_path / "PLAN.md").write_text("B12e: pendiente de decisión.\n", encoding="utf-8")
    puerto = FixedGitHubMirrorReader(
        cuerpos_por_incidencia={
            (_REPO, 1): LecturaCuerpo(estado=LecturaEstado.OK, cuerpo="B12e se referencia aquí")
        },
        comentarios_por_incidencia={
            (_REPO, 1): LecturaComentarios(estado=LecturaEstado.OK, comentarios=())
        },
    )
    entradas_git = (EntradaGitLog(sha="c" * 40, asunto="B12e: primer commit", cuerpo=""),)

    contexto = recuperar_contexto(
        "B12e",
        raiz_repo=tmp_path,
        port=puerto,
        repo=_REPO,
        numeros_incidencias=[1],
        entradas_git_log=entradas_git,
        ahora=_AHORA,
    )

    tipos = {r.tipo for r in contexto.referencias}
    assert tipos == {"fichero", "incidencia", "commit"}
    assert contexto.proveedores_fallidos == ()
    assert contexto.origen.leido_en == _AHORA
    assert contexto.consulta == "B12e"


def test_recuperar_contexto_es_determinista(tmp_path: Path) -> None:
    (tmp_path / "PLAN.md").write_text("B12e\n", encoding="utf-8")
    puerto = FixedGitHubMirrorReader()

    def _recuperar() -> object:
        return recuperar_contexto(
            "B12e",
            raiz_repo=tmp_path,
            port=puerto,
            repo=_REPO,
            numeros_incidencias=[],
            entradas_git_log=(),
            ahora=_AHORA,
        )

    assert _recuperar() == _recuperar()
