"""Guardián de goteo en vivo (incidencia #496, ADR-123).

Fija los cinco escenarios exigidos por la incidencia: fichero sin cambios
entre ronda 1 y N (marca), línea fuera de todo hunk (marca), línea dentro de
un hunk añadido (no marca), lectura de la API caída (no marca y lo declara
con un valor distinto de "sin cambios"), y ronda 1 (nunca marca). El módulo
es puro: el `fetch` de comparación se inyecta, sin red ni `gh`.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from sirius_engine.drip_guard import (
    MENSAJE_POSIBLE_GOTEO,
    CompareFetcher,
    DripVerdict,
    FileCompareResult,
    annotate_observations,
    annotate_observations_with_verdicts,
    evaluate_finding,
    gh_compare_file,
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
# Los seis campos reales de la ola de criticidad (incidencia #523, G3): la
# mina midió que solo el caso 5 se entendía con el parser viejo. Cada uno de
# estos casos se vio FALLAR contra `_LOCATION_LINE_RE` antes del cambio
# (ADR-001); los comentarios documentan qué devolvía entonces.
# --------------------------------------------------------------------------- #


def test_caso_1_sufijo_entre_parentesis_con_funcion_y_lineas_con_virgulilla() -> None:
    # Antes: (texto completo, None). CLAUDE-REV-R2-001 de #520.
    archivo = (
        "src/sirius/presentation/knowledge_widget.py "
        "(_handle_criticality_proposal_finished, ~líneas 766-805)"
    )
    assert parse_archivo_location(archivo) == (
        "src/sirius/presentation/knowledge_widget.py",
        766,
    )


def test_caso_2_rango_pegado_a_la_ruta_seguido_de_parentesis_con_funcion() -> None:
    # Antes: (texto completo, None).
    archivo = "src/sirius/presentation/knowledge_widget.py:1436-1449 (_set_controls_enabled)"
    assert parse_archivo_location(archivo) == (
        "src/sirius/presentation/knowledge_widget.py",
        1436,
    )


def test_caso_3_ruta_sin_linea_sigue_sin_evaluarse() -> None:
    # Ya funcionaba, y debe seguir igual: sin línea no hay evaluación mecánica.
    archivo = "tests/unit/test_ollama_relevance_filter.py"
    assert parse_archivo_location(archivo) == (archivo, None)


def test_caso_4_ruta_de_un_adr_sin_linea_sigue_sin_evaluarse() -> None:
    # Ya funcionaba, y debe seguir igual.
    archivo = (
        "docs/decisions/ADR-128-m19b-el-rescate-rf-25-rf-26-y-la-prioridad-de-g12-por-criticidad.md"
    )
    assert parse_archivo_location(archivo) == (archivo, None)


def test_caso_5_ruta_limpia_con_linea_ya_funcionaba_y_no_cambia() -> None:
    assert parse_archivo_location("src/sirius/domain/relevance.py:363") == (
        "src/sirius/domain/relevance.py",
        363,
    )


def test_caso_6_numero_pegado_a_la_ruta_seguido_de_en_sha() -> None:
    # Antes: (texto completo, None).
    archivo = "src/sirius/presentation/knowledge_widget.py:1490 en 6899ecf"
    assert parse_archivo_location(archivo) == (
        "src/sirius/presentation/knowledge_widget.py",
        1490,
    )


def test_adversario_texto_sin_ninguna_ruta_reconocible() -> None:
    # Sin ningún carácter de ruta reconocible (ni "/" ni "."): el texto
    # completo es la única ruta razonable, igual que hoy sin sufijo de línea.
    archivo = "el cuerpo de la PR"
    assert parse_archivo_location(archivo) == (archivo, None)


def test_adversario_dos_numero_pegado_a_la_ruta_gana_al_parentesis() -> None:
    # Cuando la ruta lleva ":NNN" Y además el paréntesis dice "líneas MMM",
    # gana el ":NNN" pegado a la ruta (regla (1) antes que la (2)).
    archivo = "src/x.py:50 (líneas 80)"
    assert parse_archivo_location(archivo) == ("src/x.py", 50)


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
    # Limitación conocida y declarada (ADR-123, docstring del módulo): no
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


def test_annotate_observations_descarta_una_marca_ajena_ya_presente() -> None:
    # Modo solo-Claude (incidencia #501, hallazgo Codex): la observación de
    # entrada puede traer ya una clave `posible_goteo` inventada por el
    # revisor, no por este guardián. Aquí ni siquiera hay ronda 1 con la que
    # comparar (round_number=1, regla (e) de la incidencia #496), así que
    # `fetch` no se llama y la única fuente posible de la clave es la propia
    # entrada: debe descartarse, no publicarse como si el guardián la
    # hubiera puesto.
    def _fetch_no_deberia_llamarse(repo: str, h1: str, h2: str, ruta: str) -> FileCompareResult:
        raise AssertionError("ronda 1 nunca compara")

    observations = [{"archivo": "src/x.py:10", "posible_goteo": "inventado"}]
    anotadas = annotate_observations(
        observations,
        round_number=1,
        round_records=[],
        current_head=HEAD1,
        repo=REPO,
        fetch=_fetch_no_deberia_llamarse,
    )
    assert "posible_goteo" not in anotadas[0]


# --------------------------------------------------------------------------- #
# annotate_observations_with_verdicts
# --------------------------------------------------------------------------- #


def test_annotate_observations_with_verdicts_expone_sin_informacion() -> None:
    fetch = _fetch_devolviendo(None)
    observations = [{"id": "R1", "archivo": "src/x.py:10", "problema": "..."}]
    anotadas, veredictos = annotate_observations_with_verdicts(
        observations,
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        fetch=fetch,
    )
    assert "posible_goteo" not in anotadas[0]
    assert veredictos == [DripVerdict.SIN_INFORMACION]


def test_annotate_observations_with_verdicts_coincide_con_annotate_observations() -> None:
    fetch = _fetch_devolviendo(FileCompareResult(changed=False, patch=None))
    observations = [{"id": "R1", "archivo": "src/x.py:10", "problema": "..."}]
    anotadas_simple = annotate_observations(
        observations,
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        fetch=fetch,
    )
    anotadas_detallada, veredictos = annotate_observations_with_verdicts(
        observations,
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        fetch=fetch,
    )
    assert anotadas_simple == anotadas_detallada
    assert veredictos == [DripVerdict.POSIBLE_GOTEO]


# --------------------------------------------------------------------------- #
# Presupuesto y deduplicación por fichero (incidencia #501, CLAUDE-REVISOR-001)
# --------------------------------------------------------------------------- #


def test_dos_observaciones_del_mismo_fichero_reutilizan_una_unica_comparacion() -> None:
    llamadas: list[str] = []

    def fetch(repo: str, head1: str, head2: str, ruta: str) -> FileCompareResult:
        llamadas.append(ruta)
        return FileCompareResult(changed=False, patch=None)

    observations = [
        {"id": "R1", "archivo": "src/x.py:10", "problema": "..."},
        {"id": "R2", "archivo": "src/x.py:20", "problema": "..."},
    ]
    anotadas, veredictos = annotate_observations_with_verdicts(
        observations,
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        fetch=fetch,
    )
    assert llamadas == ["src/x.py"]
    assert veredictos == [DripVerdict.POSIBLE_GOTEO, DripVerdict.POSIBLE_GOTEO]
    assert anotadas[0]["posible_goteo"] == MENSAJE_POSIBLE_GOTEO
    assert anotadas[1]["posible_goteo"] == MENSAJE_POSIBLE_GOTEO


def test_presupuesto_de_tiempo_agotado_no_intenta_mas_comparaciones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llamadas: list[str] = []

    def fetch(repo: str, head1: str, head2: str, ruta: str) -> FileCompareResult:
        llamadas.append(ruta)
        return FileCompareResult(changed=False, patch=None)

    # Tres lecturas del reloj: (1) al fijar el plazo, (2) antes de la primera
    # comparación -todavía dentro del presupuesto-, (3) antes de la segunda
    # -ya fuera-. Un reloj falso hace la prueba determinista, sin depender de
    # un `sleep` real ni de un `fetch` que tarde de verdad.
    tiempos = iter([0.0, 0.0, 100.0])
    monkeypatch.setattr("sirius_engine.drip_guard.time.monotonic", lambda: next(tiempos))

    observations = [
        {"id": "R1", "archivo": "src/a.py:1", "problema": "..."},
        {"id": "R2", "archivo": "src/b.py:1", "problema": "..."},
    ]
    anotadas, veredictos = annotate_observations_with_verdicts(
        observations,
        round_number=2,
        round_records=[_registro_ronda_1()],
        current_head=HEAD2,
        repo=REPO,
        fetch=fetch,
        time_budget_seconds=10.0,
    )
    # Solo la primera comparación llegó a llamar a `fetch`: la segunda vio el
    # presupuesto agotado y se resolvió sin ninguna llamada real.
    assert llamadas == ["src/a.py"]
    assert veredictos == [DripVerdict.POSIBLE_GOTEO, DripVerdict.SIN_INFORMACION]
    assert "posible_goteo" not in anotadas[1]


# --------------------------------------------------------------------------- #
# Lista de ficheros posiblemente truncada (incidencia #501, CLAUDE-REVISOR-002)
# --------------------------------------------------------------------------- #


def _instalar_gh_falso(monkeypatch: pytest.MonkeyPatch, stdout: str, returncode: int = 0) -> None:
    def _run_falso(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="")

    monkeypatch.setattr("sirius_engine.drip_guard.subprocess.run", _run_falso)


def test_lista_de_ficheros_en_el_limite_documentado_es_lectura_fallida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 300 es el límite documentado de la API de comparación de GitHub: si la
    # lista alcanza justo ese tamaño y el fichero citado no aparece en ella,
    # puede estar truncada -no es evidencia de que no cambiara.
    ficheros = [{"filename": f"src/f{i}.py", "status": "modified"} for i in range(300)]
    _instalar_gh_falso(monkeypatch, json.dumps({"files": ficheros}))

    resultado = gh_compare_file(REPO, HEAD1, HEAD2, "src/ausente.py")

    assert resultado is None


def test_lista_de_ficheros_corta_sin_el_fichero_citado_es_sin_cambios(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ficheros = [{"filename": "src/otro.py", "status": "modified"}]
    _instalar_gh_falso(monkeypatch, json.dumps({"files": ficheros}))

    resultado = gh_compare_file(REPO, HEAD1, HEAD2, "src/ausente.py")

    assert resultado == FileCompareResult(changed=False, patch=None)
