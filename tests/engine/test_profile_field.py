"""Campo declarativo ``Perfil: <ref>@<version>`` (arquitectura §5.1, incidencia #202)."""

from __future__ import annotations

from sirius_engine.profile_field import ProfileRef, parse_perfil_field, project_perfil_field


def test_ausente_devuelve_none_retrocompatible() -> None:
    cuerpo = "## Work ID\n\nSIRIUS-WORK-ENGINE-A2-001\n\n## Rama base\n\nmain\n"
    assert parse_perfil_field(cuerpo) is None


def test_lee_el_campo_dentro_de_un_cuerpo_realista() -> None:
    cuerpo = (
        "## Work ID\n\nSIRIUS-WORK-ENGINE-A4-001\n\nPerfil: implementer@1\n\n## Rama base\n\nmain\n"
    )
    assert parse_perfil_field(cuerpo) == ProfileRef(ref="implementer", version=1)


def test_ignora_lineas_parecidas_pero_mal_formadas() -> None:
    cuerpo = "Perfil: sin-version\nPerfil implementer@1 (sin dos puntos)\n"
    assert parse_perfil_field(cuerpo) is None


def test_se_queda_con_la_primera_ocurrencia() -> None:
    cuerpo = "Perfil: implementer@1\n...\nPerfil: corrector@2\n"
    assert parse_perfil_field(cuerpo) == ProfileRef(ref="implementer", version=1)


def test_proyeccion_y_lectura_son_inversas() -> None:
    referencia = ProfileRef(ref="revisor-documental", version=3)
    linea = project_perfil_field(referencia)
    assert linea == "Perfil: revisor-documental@3"
    cuerpo = f"## Bloque\n\nDocumentación\n\n{linea}\n\n## Rama base\n\nmain\n"
    assert parse_perfil_field(cuerpo) == referencia
