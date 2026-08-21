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
    LecturaHistorialGit,
    Referencia,
    buscar_en_arbol_repo,
    buscar_en_historial_git,
    buscar_en_incidencias,
    leer_historial_git,
    leer_historial_git_como_lectura,
    recuperar_contexto,
)
from sirius_engine.domain.mirror import EspejoIlegibleError
from sirius_engine.ports.github_mirror import (
    Comentario,
    CuerpoIncidencia,
    LecturaComentarios,
    LecturaCuerpo,
    LecturaEstado,
)

_REPO = "canelamoraguezandyjesus-bot/sirius"
_AHORA = datetime(2026, 8, 18, 15, 0, tzinfo=UTC)


def _git_leido(*entradas: EntradaGitLog) -> LecturaHistorialGit:
    """Historial leído sin problemas. ``()`` es "leí y no había", no "no pude leer"."""
    return LecturaHistorialGit(estado=LecturaEstado.OK, entradas=entradas)


def _git_ilegible() -> LecturaHistorialGit:
    return LecturaHistorialGit(estado=LecturaEstado.NO_DISPONIBLE, error="git no disponible")


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

    referencias, fallidas = buscar_en_arbol_repo(tmp_path, "B12e")

    assert referencias == (
        Referencia(tipo="fichero", identificador="docs/b12e.md:1", fragmento="# B12e"),
        Referencia(
            tipo="fichero",
            identificador="docs/b12e.md:3",
            fragmento="B12e quedó bloqueado por decisión.",
        ),
    )
    assert fallidas == ()


def test_buscar_en_arbol_repo_ignora_directorios_excluidos(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "ficticio.md").write_text("B12e\n", encoding="utf-8")
    referencias, fallidas = buscar_en_arbol_repo(tmp_path, "B12e")
    assert referencias == ()
    assert fallidas == ()


def test_buscar_en_arbol_repo_es_determinista(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("consulta\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("consulta\n", encoding="utf-8")
    assert buscar_en_arbol_repo(tmp_path, "consulta") == buscar_en_arbol_repo(tmp_path, "consulta")


def test_buscar_en_arbol_repo_fallo_de_lectura_se_reporta_no_se_esconde(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Requisito 2 también en el proveedor de árbol: un fichero elegible que ya
    no se puede leer (borrado, sin permisos, cualquier ``OSError``) no debe
    desaparecer como si el árbol no tuviera nada que decir sobre él.
    """
    (tmp_path / "legible.md").write_text("B12e en el que sí se puede confiar\n", encoding="utf-8")
    (tmp_path / "ilegible.md").write_text("B12e pero no se podrá leer\n", encoding="utf-8")

    original_read_text = Path.read_text

    def read_text_que_falla_para_ilegible(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == "ilegible.md":
            raise OSError("permiso denegado")
        return original_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", read_text_que_falla_para_ilegible)

    referencias, fallidas = buscar_en_arbol_repo(tmp_path, "B12e")

    assert any(r.identificador.startswith("legible.md") for r in referencias)
    assert not any(r.identificador.startswith("ilegible.md") for r in referencias)
    assert fallidas == ("arbol:ilegible.md",)


# --- Proveedor 2: incidencias y PR ------------------------------------------


def test_buscar_en_incidencias_respeta_el_filtro_de_confianza() -> None:
    puerto = FixedGitHubMirrorReader(
        cuerpos_por_incidencia={
            (_REPO, 1): LecturaCuerpo(
                estado=LecturaEstado.OK,
                cuerpo=CuerpoIncidencia(
                    autor_login="canelamoraguezandyjesus-bot",
                    autor_asociacion="OWNER",
                    texto="",
                ),
            )
        },
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
        cuerpos_por_incidencia={
            (_REPO, 1): LecturaCuerpo(
                estado=LecturaEstado.OK,
                cuerpo=CuerpoIncidencia(
                    autor_login="canelamoraguezandyjesus-bot",
                    autor_asociacion="OWNER",
                    texto="B12e",
                ),
            )
        }
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
    lectura = _git_leido(
        EntradaGitLog(sha="a" * 40, asunto="Añade B12e", cuerpo=""),
        EntradaGitLog(sha="b" * 40, asunto="Sin relación", cuerpo="tampoco menciona nada"),
    )
    referencias, fallidas = buscar_en_historial_git(lectura, "B12e")
    assert referencias == (
        Referencia(tipo="commit", identificador="a" * 12, fragmento="Añade B12e"),
    )
    assert fallidas == ()


def test_buscar_en_historial_git_cita_el_cuerpo_cuando_la_coincidencia_esta_ahi() -> None:
    """La cita debe evidenciar dónde ocurrió la coincidencia: si el asunto no
    contiene la consulta, el fragmento debe venir del cuerpo, no del asunto.
    """
    lectura = _git_leido(
        EntradaGitLog(sha="a" * 40, asunto="Refactor", cuerpo="B12e quedó bloqueado")
    )
    referencias, fallidas = buscar_en_historial_git(lectura, "B12e")
    assert referencias == (
        Referencia(tipo="commit", identificador="a" * 12, fragmento="B12e quedó bloqueado"),
    )
    assert fallidas == ()


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


def test_buscar_en_historial_git_distingue_no_pude_leer_de_no_habia_nada() -> None:
    """H-5 (incidencia #216): el tercer proveedor tiene la misma firma que los
    otros dos, y las dos situaciones que producen cero referencias -no pude
    leer, leí y no había- no dan el mismo resultado.
    """
    sin_leer, fallidas_sin_leer = buscar_en_historial_git(_git_ilegible(), "B12e")
    leido_vacio, fallidas_leido_vacio = buscar_en_historial_git(_git_leido(), "B12e")

    assert sin_leer == leido_vacio == ()
    assert fallidas_sin_leer == ("historial_git",)
    assert fallidas_leido_vacio == ()


def test_leer_historial_git_como_lectura_convierte_el_fallo_en_no_disponible(
    tmp_path: Path,
) -> None:
    """El adapter es el único sitio donde ``EspejoIlegibleError`` deja de ser
    una excepción: tiene que convertirse en ``NO_DISPONIBLE``, nunca en un
    ``OK`` con cero entradas.
    """

    def ejecutar_fallido(argv: list[str], raiz: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv, returncode=1, stdout="", stderr="git no disponible"
        )

    lectura = leer_historial_git_como_lectura(tmp_path, ejecutar=ejecutar_fallido)

    assert lectura.estado is LecturaEstado.NO_DISPONIBLE
    assert lectura.entradas is None
    assert lectura.error == "git no disponible"


def test_leer_historial_git_como_lectura_marca_ok_un_historial_vacio(tmp_path: Path) -> None:
    """Anti-vacua del adapter: un historial que se leyó y estaba vacío es
    ``OK``, no ``NO_DISPONIBLE``. Sin esta prueba, un adapter que devolviera
    siempre ``NO_DISPONIBLE`` pasaría la de arriba.
    """

    def ejecutar_vacio(argv: list[str], raiz: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, returncode=0, stdout="", stderr="")

    lectura = leer_historial_git_como_lectura(tmp_path, ejecutar=ejecutar_vacio)

    assert lectura.estado is LecturaEstado.OK
    assert lectura.entradas == ()
    assert lectura.error is None


# --- Orquestación ------------------------------------------------------------


def test_recuperar_contexto_responde_con_referencias_no_con_afirmaciones(
    tmp_path: Path,
) -> None:
    (tmp_path / "PLAN.md").write_text("B12e: pendiente de decisión.\n", encoding="utf-8")
    puerto = FixedGitHubMirrorReader(
        cuerpos_por_incidencia={
            (_REPO, 1): LecturaCuerpo(
                estado=LecturaEstado.OK,
                cuerpo=CuerpoIncidencia(
                    autor_login="canelamoraguezandyjesus-bot",
                    autor_asociacion="OWNER",
                    texto="B12e se referencia aquí",
                ),
            )
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
        lectura_historial_git=_git_leido(*entradas_git),
        ahora=_AHORA,
    )

    tipos = {r.tipo for r in contexto.referencias}
    assert tipos == {"fichero", "incidencia", "commit"}
    assert contexto.proveedores_fallidos == ()
    assert contexto.origen.leido_en == _AHORA
    assert contexto.consulta == "B12e"


def test_recuperar_contexto_reporta_el_fallo_del_tercer_proveedor(tmp_path: Path) -> None:
    """H-5 (incidencia #216). Antes de ADR-050, ``proveedores_fallidos`` sumaba
    solo dos de los tres proveedores: un ``git log`` caído llegaba a quien
    recibía el ``ContextoRecuperado`` como "git no tenía nada".

    La prueba exige además que el fallo de un proveedor no se lleve por
    delante a los otros dos: la referencia del árbol tiene que seguir ahí.
    """
    (tmp_path / "PLAN.md").write_text("B12e: pendiente de decisión.\n", encoding="utf-8")

    contexto = recuperar_contexto(
        "B12e",
        raiz_repo=tmp_path,
        port=FixedGitHubMirrorReader(),
        repo=_REPO,
        numeros_incidencias=[],
        lectura_historial_git=_git_ilegible(),
        ahora=_AHORA,
    )

    assert "historial_git" in contexto.proveedores_fallidos
    assert any(r.tipo == "fichero" for r in contexto.referencias)


def test_recuperar_contexto_no_llama_fallo_a_un_historial_de_git_vacio(tmp_path: Path) -> None:
    """Anti-vacua de la de arriba: "git se leyó y no había coincidencias" NO
    puede aparecer en ``proveedores_fallidos``. Sin esta prueba, reportar
    siempre el tercer proveedor pasaría por arreglo.
    """
    (tmp_path / "PLAN.md").write_text("B12e: pendiente de decisión.\n", encoding="utf-8")

    contexto = recuperar_contexto(
        "B12e",
        raiz_repo=tmp_path,
        port=FixedGitHubMirrorReader(),
        repo=_REPO,
        numeros_incidencias=[],
        lectura_historial_git=_git_leido(),
        ahora=_AHORA,
    )

    assert contexto.proveedores_fallidos == ()
    assert any(r.tipo == "fichero" for r in contexto.referencias)


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
            lectura_historial_git=_git_leido(),
            ahora=_AHORA,
        )

    assert _recuperar() == _recuperar()
