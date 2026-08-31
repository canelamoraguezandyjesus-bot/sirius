"""Guardián de goteo en vivo (incidencia #496, ADR-121).

Fija los cinco escenarios exigidos por la incidencia: fichero sin cambios
entre ronda 1 y N (marca), línea fuera de todo hunk (marca), línea dentro de
un hunk añadido (no marca), lectura de la API caída (no marca y lo declara
con un valor distinto de "sin cambios"), y ronda 1 (nunca marca). El módulo
es puro: el `fetch` de comparación se inyecta, sin red ni `gh`.
"""

from __future__ import annotations

from sirius_engine.drip_guard import (
    MENSAJE_POSIBLE_GOTEO,
    CompareFetcher,
    DripVerdict,
    FileCompareResult,
    annotate_observations,
    evaluate_finding,
    parse_archivo_location,
)

HEAD1 = "1" * 40
HEAD2 = "2" * 40
REPO = "owner/repo"


def _fetch_devolviendo(resultado: FileCompareResult | None) -> CompareFetcher:
    def _fetch(repo: str, head1: str, head2: str, ruta: str) -> FileCompareResult | None:
        assert repo == REPO
        assert head1 == HEAD1
        assert head2 == HEAD2
        return resultado

    return _fetch


def _registro_ronda_1(head: str = HEAD1) -> dict[str, object]:
    return {"round": 1, "head": head, "findings": []}


# --------------------------------------------------------------------------- #
# parse_archivo_location
# --------------------------------------------------------------------------- #


def test_parse_archivo_location_separa_ruta_y_linea() -> None:
    assert parse_archivo_location("src/x.py:120") == ("src/x.py", 120)


def test_parse_archivo_location_acepta_un_rango_y_usa_el_primer_numero() -> None:
    assert parse_archivo_location("src/x.py:120-134") == ("src/x.py", 120)


def test_parse_archivo_location_sin_linea_devuelve_none() -> None:
    assert parse_archivo_location("src/x.py") == ("src/x.py", None)


def test_parse_archivo_location_con_valor_vacio() -> None:
    assert parse_archivo_location(None) == ("", None)


# --------------------------------------------------------------------------- #
# Los cinco escenarios exigidos por la incidencia #496
# --------------------------------------------------------------------------- #


def test_fichero_sin_cambios_entre_ronda_1_y_n_marca() -> None:
    fetch = _fetch_devolviendo(FileCompareResult(changed=False, patch=None))
    veredicto = evaluate_finding(
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        archivo="src/x.py:10",
        fetch=fetch,
    )
    assert veredicto is DripVerdict.POSIBLE_GOTEO


def test_linea_fuera_de_todo_hunk_marca() -> None:
    # El fichero cambió, pero en otro punto: la línea 10 citada no aparece en
    # ningún hunk (el `@@` de este patch cubre las líneas nuevas 40-42).
    patch = "@@ -38,2 +40,3 @@\n context\n+añadida\n context"
    fetch = _fetch_devolviendo(FileCompareResult(changed=True, patch=patch))
    veredicto = evaluate_finding(
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        archivo="src/x.py:10",
        fetch=fetch,
    )
    assert veredicto is DripVerdict.POSIBLE_GOTEO


def test_linea_de_contexto_sin_tocar_dentro_de_un_hunk_tambien_marca() -> None:
    # Limitación conocida y declarada (ADR-121, docstring del módulo): no
    # distingue el caso de #459 rondas 3-4, donde una línea hermana del mismo
    # hunk sí cambió. Esta prueba fija ese comportamiento tal cual es hoy.
    patch = "@@ -8,3 +8,3 @@\n context\n-vieja\n+nueva\n context sin tocar"
    fetch = _fetch_devolviendo(FileCompareResult(changed=True, patch=patch))
    veredicto = evaluate_finding(
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        archivo="src/x.py:10",
        fetch=fetch,
    )
    assert veredicto is DripVerdict.POSIBLE_GOTEO


def test_linea_dentro_de_un_hunk_anadido_no_marca() -> None:
    patch = "@@ -8,2 +8,4 @@\n context\n+añadida\n+línea 10 añadida\n context"
    fetch = _fetch_devolviendo(FileCompareResult(changed=True, patch=patch))
    veredicto = evaluate_finding(
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        archivo="src/x.py:10",
        fetch=fetch,
    )
    assert veredicto is DripVerdict.SIN_MARCA


def test_lectura_de_la_api_caida_no_marca_y_se_declara_distinta_de_sin_cambios() -> None:
    fetch = _fetch_devolviendo(None)
    veredicto = evaluate_finding(
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        archivo="src/x.py:10",
        fetch=fetch,
    )
    # Estructuralmente distinto de "el fichero no cambió" (POSIBLE_GOTEO):
    # ningún llamador puede confundir un fallo de lectura con evidencia real.
    assert veredicto is DripVerdict.SIN_INFORMACION


def test_ronda_1_nunca_marca_ni_siquiera_si_el_fetch_diria_que_si() -> None:
    def _fetch_que_marcaria(repo: str, h1: str, h2: str, ruta: str) -> FileCompareResult:
        return FileCompareResult(changed=False, patch=None)

    veredicto = evaluate_finding(
        round_number=1,
        round_records=[],
        current_head=HEAD1,
        repo=REPO,
        archivo="src/x.py:10",
        fetch=_fetch_que_marcaria,
    )
    assert veredicto is DripVerdict.SIN_MARCA


# --------------------------------------------------------------------------- #
# Casos adicionales: sin línea citada, sin registro de ronda 1, patch ausente
# --------------------------------------------------------------------------- #


def test_sin_linea_citada_el_nivel_mecanico_no_es_aplicable() -> None:
    def _fetch_no_deberia_llamarse(repo: str, h1: str, h2: str, ruta: str) -> FileCompareResult:
        raise AssertionError("no debe compararse sin una línea concreta")

    veredicto = evaluate_finding(
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        archivo="src/x.py",
        fetch=_fetch_no_deberia_llamarse,
    )
    assert veredicto is DripVerdict.SIN_MARCA


def test_sin_registro_de_ronda_1_se_calla() -> None:
    fetch = _fetch_devolviendo(FileCompareResult(changed=False, patch=None))
    veredicto = evaluate_finding(
        round_number=3,
        round_records=[{"round": 2, "head": HEAD2, "findings": []}],
        current_head=HEAD2,
        repo=REPO,
        archivo="src/x.py:10",
        fetch=fetch,
    )
    assert veredicto is DripVerdict.SIN_INFORMACION


def test_fichero_cambiado_sin_patch_textual_no_marca() -> None:
    # Renombrado o binario: cambió, pero no hay línea que examinar.
    fetch = _fetch_devolviendo(FileCompareResult(changed=True, patch=None))
    veredicto = evaluate_finding(
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        archivo="src/x.py:10",
        fetch=fetch,
    )
    assert veredicto is DripVerdict.SIN_MARCA


# --------------------------------------------------------------------------- #
# annotate_observations
# --------------------------------------------------------------------------- #


def test_annotate_observations_anade_el_mensaje_exacto_cuando_marca() -> None:
    fetch = _fetch_devolviendo(FileCompareResult(changed=False, patch=None))
    observations = [{"id": "R1", "archivo": "src/x.py:10", "problema": "..."}]
    anotadas = annotate_observations(
        observations,
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        fetch=fetch,
    )
    assert anotadas[0]["posible_goteo"] == MENSAJE_POSIBLE_GOTEO


def test_annotate_observations_no_anade_el_campo_cuando_no_marca() -> None:
    patch = "@@ -8,2 +8,4 @@\n context\n+añadida\n+línea 10 añadida\n context"
    fetch = _fetch_devolviendo(FileCompareResult(changed=True, patch=patch))
    observations = [{"id": "R1", "archivo": "src/x.py:10", "problema": "..."}]
    anotadas = annotate_observations(
        observations,
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        fetch=fetch,
    )
    assert "posible_goteo" not in anotadas[0]


def test_annotate_observations_no_muta_la_entrada() -> None:
    fetch = _fetch_devolviendo(FileCompareResult(changed=False, patch=None))
    original = {"id": "R1", "archivo": "src/x.py:10", "problema": "..."}
    observations = [original]
    annotate_observations(
        observations,
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        fetch=fetch,
    )
    assert "posible_goteo" not in original
