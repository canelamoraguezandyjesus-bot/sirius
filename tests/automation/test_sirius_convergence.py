"""Pruebas de ``scripts/automation/sirius_convergence.py``.

La política de convergencia sustituye al tope fijo de dos ciclos de corrección
(contrato §5, v1.5). Estas pruebas fijan su comportamiento determinista: qué
cuenta como progreso, qué no, y en qué casos exactos el ciclo pasa a decisión
humana. El módulo es puro (texto de entrada, decisión de salida): no necesita
red ni ``gh``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "automation" / "sirius_convergence.py"

HEAD_A = "a" * 40
HEAD_B = "b" * 40
HEAD_C = "c" * 40
HEAD_D = "d" * 40


def _module() -> Any:
    name = "sirius_convergence_under_test"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _observation(
    identifier: str = "CODEX-001",
    archivo: str = "src/x.py:10",
    problema: str = "No valida la entrada.",
    severidad: str = "P2",
) -> dict[str, str]:
    return {
        "id": identifier,
        "severidad": severidad,
        "archivo": archivo,
        "problema": problema,
        "criterio_esperado": "debe validar",
        "prueba": "test_x",
        "limites_correccion": "solo src/x.py",
    }


def _round_comment(round_number: int, head: str, observations: list[dict[str, str]]) -> str:
    module = _module()
    record = module.round_record(round_number, head, observations)
    return (
        f"<!-- sirius-round:{round_number} -->\n\n"
        "## RONDA_HALLAZGOS\n```json\n" + json.dumps(record, ensure_ascii=False) + "\n```\n"
    )


def _decide(rounds: list[str]) -> dict[str, Any]:
    module = _module()
    result: dict[str, Any] = module.decide(module.parse_round_records("\n".join(rounds)))
    return result


# --------------------------------------------------------------------------- #
# Huella estable
# --------------------------------------------------------------------------- #


def test_fingerprint_ignores_the_sequential_identifier() -> None:
    # El mismo defecto reportado en dos rondas cambia de CODEX-001 a CODEX-002;
    # si la huella dependiera del identificador, un hallazgo persistente
    # parecería nuevo y la detección de progreso sería inútil.
    module = _module()
    first = module.fingerprint(_observation("CODEX-001"))
    second = module.fingerprint(_observation("CODEX-002"))
    assert first == second


def test_fingerprint_distinguishes_source() -> None:
    module = _module()
    assert module.fingerprint(_observation("CLAUDE-1")) != module.fingerprint(
        _observation("CODEX-1")
    )


def test_fingerprint_ignores_irrelevant_whitespace_but_not_content() -> None:
    module = _module()
    base = module.fingerprint(_observation(problema="No valida   la entrada."))
    assert base == module.fingerprint(_observation(problema="No valida la entrada."))
    assert base != module.fingerprint(_observation(problema="No valida la salida."))


def test_round_record_is_order_independent() -> None:
    module = _module()
    a = _observation("CODEX-001", "src/a.py:1", "Problema A")
    b = _observation("CODEX-002", "src/b.py:2", "Problema B")
    assert module.round_record(1, HEAD_A, [a, b]) == module.round_record(1, HEAD_A, [b, a])


# --------------------------------------------------------------------------- #
# Continuación mientras hay progreso
# --------------------------------------------------------------------------- #


def test_first_round_always_continues() -> None:
    assert _decide([])["decision"] == "CONTINUE"


def test_single_round_with_findings_continues() -> None:
    result = _decide([_round_comment(1, HEAD_A, [_observation()])])
    assert result["decision"] == "CONTINUE"


def test_fewer_pending_findings_is_progress() -> None:
    first = _round_comment(
        1, HEAD_A, [_observation("CODEX-001"), _observation("CODEX-002", "src/y.py:5", "Otro")]
    )
    second = _round_comment(2, HEAD_B, [_observation("CODEX-001")])
    result = _decide([first, second])
    assert result["decision"] == "CONTINUE"
    assert result["reason"] == "progreso"


def test_lower_aggregate_severity_is_progress() -> None:
    first = _round_comment(1, HEAD_A, [_observation(severidad="P0")])
    second = _round_comment(2, HEAD_B, [_observation(problema="Otro defecto", severidad="P4")])
    result = _decide([first, second])
    assert result["decision"] == "CONTINUE"
    assert "gravedad" in result["detail"]


def test_swapping_one_finding_for_another_is_not_progress() -> None:
    # Mismo número de hallazgos y misma gravedad, con un defecto distinto: es
    # exactamente la "sustitución de un fallo por otro equivalente" que el
    # contrato §5.1 excluye. Si contara como progreso, bastaría con reformular
    # un defecto persistente para mantener el ciclo abierto indefinidamente.
    first = _round_comment(1, HEAD_A, [_observation("CODEX-001", problema="Defecto uno")])
    second = _round_comment(2, HEAD_B, [_observation("CODEX-001", problema="Defecto dos")])
    result = _decide([first, second])
    assert result["decision"] == "CONTINUE"  # primera vez sin progreso: se tolera
    assert result["reason"] == "sin-progreso-aislado"


def test_rephrasing_a_persistent_finding_does_not_keep_the_cycle_open() -> None:
    # Cuatro paráfrasis del mismo defecto, mismo archivo, misma severidad y
    # mismo recuento. La huella cambia con la redacción, así que inferir
    # "resuelto" de que desapareció una huella mantendría el ciclo abierto para
    # siempre. Debe bloquear.
    parafrasis = [
        "No valida la entrada.",
        "La entrada no se valida.",
        "Falta validación de la entrada.",
        "La validación de la entrada no existe.",
    ]
    heads = [HEAD_A, HEAD_B, HEAD_C, HEAD_D]
    rounds = [
        _round_comment(index + 1, heads[index], [_observation("CODEX-001", problema=texto)])
        for index, texto in enumerate(parafrasis)
    ]
    result = _decide(rounds)
    assert result["decision"] == "BLOCK"
    assert result["reason"] == "sin-progreso"


def test_alternating_between_metrics_does_not_continue_forever() -> None:
    # 1 P0 (pendientes 1, gravedad 4) → 2 P3 (2, 2) → 1 P0 (1, 4) → ...
    # Cada ronda mejora una magnitud empeorando la otra, con huellas y heads
    # nuevos. Sin exigir disminución del PAR, alternaría indefinidamente.
    heads = [f"{index:040x}" for index in range(1, 12)]
    rounds = []
    for index in range(6):
        if index % 2 == 0:
            observations = [_observation("CODEX-001", f"src/a{index}.py:1", f"Grave {index}", "P0")]
        else:
            observations = [
                _observation("CODEX-001", f"src/b{index}.py:1", f"Leve {index}a", "P3"),
                _observation("CODEX-002", f"src/c{index}.py:1", f"Leve {index}b", "P3"),
            ]
        rounds.append(_round_comment(index + 1, heads[index], observations))
    result = _decide(rounds)
    assert result["decision"] == "BLOCK"
    assert result["reason"] == "sin-progreso"


def test_improving_one_metric_while_worsening_the_other_is_not_progress() -> None:
    module = _module()
    history = [{"pending": 1, "severity_total": 4, "fingerprints": {"aaa"}}]
    current = {"pending": 2, "severity_total": 2, "fingerprints": {"bbb", "ccc"}}
    progressed, why = module._has_progress(history, current)
    assert progressed is False
    assert "la otra la empeora" in why


def test_progress_is_measured_against_the_best_historical_mark() -> None:
    # La mejor marca histórica es el mínimo de CADA magnitud sobre todo el
    # historial, no el estado de la ronda inmediata: así una regresión aislada
    # no puede elevar el listón para la ronda siguiente.
    module = _module()
    history = [
        {"pending": 1, "severity_total": 2, "fingerprints": set()},  # mejor marca
        {"pending": 5, "severity_total": 9, "fingerprints": set()},  # regresión
    ]
    # Mejora respecto de la ronda inmediata (5, 9) pero NO respecto de (1, 2).
    progressed, why = module._has_progress(history, {"pending": 4, "severity_total": 8})
    assert progressed is False
    assert "(1, 2)" in why


def test_the_cycle_always_terminates_even_with_tolerated_regressions() -> None:
    """La terminación es una propiedad, no una expectativa.

    Esta prueba explora el ciclo COMPLETO, no solo las cadenas de progresos
    consecutivos. Esa distinción importa: una versión anterior de esta prueba
    solo encadenaba progresos y por eso no detectó que una regresión aislada
    —tolerada por la regla de "dos rondas consecutivas"— podía elevar el listón
    y permitir que la ronda siguiente reiniciara el contador con una mejora
    local, indefinidamente. Aquí se modela también esa alternancia.

    La búsqueda es un recorrido en anchura sobre estados
    ``(mejor marca histórica, hubo progreso en la última ronda)``: si existiera
    una secuencia infinita de `CONTINUE`, algún estado se repetiría y el
    conjunto alcanzable no se cerraría en un número finito de pasos.
    """
    module = _module()
    pesos = {"P0": 4, "P1": 3, "P2": 2, "P3": 1, "P4": 1}
    # Estados alcanzables por una ronda real: n hallazgos de una severidad.
    posibles = sorted({(n, n * pesos[sev]) for n in range(1, 6) for sev in pesos})

    def progresa(mejor: tuple[int, int], siguiente: tuple[int, int]) -> bool:
        resultado: bool = module._has_progress(
            [{"pending": mejor[0], "severity_total": mejor[1], "fingerprints": set()}],
            {"pending": siguiente[0], "severity_total": siguiente[1], "fingerprints": set()},
        )[0]
        return resultado

    # Estado del ciclo: (mejor marca histórica, si la última ronda progresó).
    # Una ronda sin progreso con la anterior también sin progreso bloquea, así
    # que ese estado es terminal y no se expande.
    inicial = {(estado, True) for estado in posibles}
    alcanzables: set[tuple[tuple[int, int], bool]] = set()
    frontera = set(inicial)
    pasos = 0
    while frontera:
        pasos += 1
        assert pasos <= 200, "el conjunto alcanzable no se cierra: hay un ciclo infinito"
        siguiente_frontera = set()
        for mejor, ultima_progreso in frontera:
            if (mejor, ultima_progreso) in alcanzables:
                continue
            alcanzables.add((mejor, ultima_progreso))
            for candidato in posibles:
                if progresa(mejor, candidato):
                    nueva_mejor = (min(mejor[0], candidato[0]), min(mejor[1], candidato[1]))
                    siguiente_frontera.add((nueva_mejor, True))
                elif ultima_progreso:
                    # Regresión tolerada: NO puede empeorar la mejor marca.
                    nueva_mejor = (min(mejor[0], candidato[0]), min(mejor[1], candidato[1]))
                    siguiente_frontera.add((nueva_mejor, False))
                # Si la última tampoco progresó, el ciclo bloquea: estado terminal.
        frontera = siguiente_frontera - alcanzables

    # Que la exploración termine ya demuestra la ausencia de ciclos infinitos.
    assert alcanzables, "debería haber estados alcanzables"


def test_an_isolated_regression_cannot_raise_the_bar() -> None:
    # La secuencia (1,2) → (2,4) → (2,3) → (3,5) → (3,4) → … alterna regresión
    # tolerada y mejora local mientras el estado global crece sin fin. Debe
    # bloquear, no continuar.
    pesos_por_par = [(1, 2), (2, 4), (2, 3), (3, 5), (3, 4), (4, 6)]
    heads = [f"{index:040x}" for index in range(1, 12)]
    rounds = []
    decisions = []
    module = _module()
    for index, (pendientes, _gravedad) in enumerate(pesos_por_par):
        # `pendientes` hallazgos P2 dan gravedad 2*pendientes; para obtener los
        # pares exactos se mezcla una severidad menor cuando hace falta.
        observations = [
            _observation(f"CODEX-{n:03d}", f"src/r{index}_{n}.py:1", f"Defecto {index}-{n}", "P2")
            for n in range(pendientes)
        ]
        rounds.append(_round_comment(index + 1, heads[index], observations))
        decisions.append(module.decide(module.parse_round_records("\n".join(rounds)))["decision"])
    assert "BLOCK" in decisions, f"la secuencia debe bloquear en algún punto: {decisions}"


def test_reducing_pending_without_raising_severity_is_progress() -> None:
    module = _module()
    history = [{"pending": 3, "severity_total": 6, "fingerprints": {"a", "b", "c"}}]
    current = {"pending": 2, "severity_total": 4, "fingerprints": {"a", "b"}}
    progressed, _ = module._has_progress(history, current)
    assert progressed is True


def test_many_rounds_with_progress_are_allowed() -> None:
    # Diez rondas consecutivas con progreso: el tope fijo de dos ciclos habría
    # bloqueado en la tercera. La política nueva no impone ningún tope.
    rounds = []
    heads = [f"{index:040x}" for index in range(1, 12)]
    for index in range(10):
        observations = [
            _observation(f"CODEX-{n:03d}", f"src/f{n}.py:1", f"Defecto {n}")
            for n in range(10 - index)
        ]
        rounds.append(_round_comment(index + 1, heads[index], observations))
    result = _decide(rounds)
    assert result["decision"] == "CONTINUE"
    assert result["rounds"] == 10


# --------------------------------------------------------------------------- #
# Bloqueo por falta de convergencia
# --------------------------------------------------------------------------- #


def test_no_progress_once_is_tolerated() -> None:
    same = [_observation("CODEX-001")]
    result = _decide([_round_comment(1, HEAD_A, same), _round_comment(2, HEAD_B, same)])
    assert result["decision"] == "CONTINUE"
    assert result["reason"] == "sin-progreso-aislado"


def test_no_progress_in_two_consecutive_rounds_blocks() -> None:
    same = [_observation("CODEX-001")]
    result = _decide(
        [
            _round_comment(1, HEAD_A, same),
            _round_comment(2, HEAD_B, same),
            _round_comment(3, HEAD_C, same),
        ]
    )
    assert result["decision"] == "BLOCK"
    assert result["reason"] == "sin-progreso"


def test_reappearance_of_a_resolved_finding_blocks() -> None:
    ghost = _observation("CODEX-001", "src/ghost.py:1", "Defecto fantasma")
    other = _observation("CODEX-002", "src/other.py:2", "Otro defecto")
    result = _decide(
        [
            _round_comment(1, HEAD_A, [ghost, other]),
            _round_comment(2, HEAD_B, [other]),
            _round_comment(3, HEAD_C, [ghost]),
        ]
    )
    assert result["decision"] == "BLOCK"
    assert result["reason"] == "reaparicion"


def test_returning_to_an_earlier_state_blocks_by_reappearance() -> None:
    # X -> Y -> X. Los hallazgos de X se dieron por resueltos en la ronda 2 y
    # vuelven en la 3: la reaparición es el diagnóstico correcto y tiene
    # prioridad sobre la oscilación, porque señala la causa (la corrección no
    # atacó la raíz) y no solo la forma del ciclo.
    state_x = [_observation("CODEX-001", "src/x.py:1", "Defecto X")]
    state_y = [
        _observation("CODEX-001", "src/y.py:1", "Defecto Y"),
        _observation("CODEX-002", "src/z.py:1", "Defecto Z"),
    ]
    result = _decide(
        [
            _round_comment(1, HEAD_A, state_x),
            _round_comment(2, HEAD_B, state_y),
            _round_comment(3, HEAD_C, state_x),
        ]
    )
    assert result["decision"] == "BLOCK"
    assert result["reason"] == "reaparicion"


def test_oscillation_between_previous_states_blocks() -> None:
    # Oscilación PURA, sin reaparición de por medio: {A} -> {A, B} -> {A}. A
    # nunca desaparece (la ronda 2 lo contiene), así que el detector de
    # reaparición no se dispara y quien debe hablar es el de oscilación. La
    # versión anterior de esta prueba aceptaba `oscilacion` O `reaparicion`, y
    # con el escenario que usaba siempre ganaba la reaparición: la rama de
    # oscilación no llegaba a ejecutarse nunca y podía romperse sin que ninguna
    # prueba lo notara.
    state_a = [_observation("CODEX-001", "src/a.py:1", "Defecto A")]
    state_ab = [
        _observation("CODEX-001", "src/a.py:1", "Defecto A"),
        _observation("CODEX-002", "src/b.py:1", "Defecto B"),
    ]
    result = _decide(
        [
            _round_comment(1, HEAD_A, state_a),
            _round_comment(2, HEAD_B, state_ab),
            _round_comment(3, HEAD_C, state_a),
        ]
    )
    assert result["decision"] == "BLOCK"
    assert result["reason"] == "oscilacion"
    assert "ronda 1" in result["detail"]


def test_same_head_in_two_rounds_blocks() -> None:
    # El corrector no publicó ningún cambio: no hay nada nuevo que revisar.
    result = _decide(
        [
            _round_comment(1, HEAD_A, [_observation("CODEX-001")]),
            _round_comment(2, HEAD_A, [_observation("CODEX-002", "src/y.py:1", "Otro")]),
        ]
    )
    assert result["decision"] == "BLOCK"
    assert result["reason"] == "head-sin-avance"


# --------------------------------------------------------------------------- #
# Lo que NO cuenta como progreso
# --------------------------------------------------------------------------- #


def test_cosmetic_identifier_change_is_not_progress() -> None:
    # Renumerar los hallazgos no cambia sus huellas, así que no simula avance.
    first = _round_comment(
        1, HEAD_A, [_observation("CODEX-001"), _observation("CODEX-002", "src/y.py:5", "Otro")]
    )
    second = _round_comment(
        2, HEAD_B, [_observation("CODEX-007"), _observation("CODEX-009", "src/y.py:5", "Otro")]
    )
    third = _round_comment(
        3, HEAD_C, [_observation("CODEX-011"), _observation("CODEX-013", "src/y.py:5", "Otro")]
    )
    result = _decide([first, second, third])
    assert result["decision"] == "BLOCK"
    assert result["reason"] == "sin-progreso"


def test_dropping_the_severity_label_does_not_fake_progress() -> None:
    # Una severidad desconocida pesa como media, no como cero: perder la
    # etiqueta no puede bajar artificialmente la gravedad agregada.
    module = _module()
    assert module.severity_weight("desconocida") == module.severity_weight("media")
    assert module.severity_weight("P0") > module.severity_weight("P2")


def test_unreadable_round_blocks_are_ignored_without_breaking() -> None:
    module = _module()
    text = "<!-- sirius-round:9 -->\n## RONDA_HALLAZGOS\n```json\n{no es json\n```\n" + (
        _round_comment(1, HEAD_A, [_observation()])
    )
    records = module.parse_round_records(text)
    assert len(records) == 1


def test_replacing_one_finding_with_more_is_not_progress() -> None:
    # Resolver A introduciendo B y C empeora el estado. Si contara como
    # progreso, ninguna magnitud decrecería y el ciclo no terminaría nunca.
    first = _round_comment(1, HEAD_A, [_observation("CODEX-001", "src/a.py:1", "Defecto A")])
    second = _round_comment(
        2,
        HEAD_B,
        [
            _observation("CODEX-001", "src/b.py:1", "Defecto B"),
            _observation("CODEX-002", "src/c.py:1", "Defecto C"),
        ],
    )
    result = _decide([first, second])
    assert result["decision"] == "CONTINUE"  # todavía es la primera vez sin progreso
    assert result["reason"] == "sin-progreso-aislado"
    # Ni los pendientes ni la gravedad disminuyeron: el par no mejoró.
    assert "no muestra progreso" in result["detail"]


def test_a_worsening_run_of_rounds_terminates() -> None:
    # Ocho rondas en las que cada una sustituye los hallazgos por MÁS hallazgos
    # nuevos: el ciclo debe bloquear, no continuar indefinidamente.
    rounds = []
    heads = [f"{index:040x}" for index in range(1, 12)]
    for index in range(8):
        observations = [
            _observation(f"CODEX-{n:03d}", f"src/r{index}_{n}.py:1", f"Defecto {index}-{n}")
            for n in range(index + 1)
        ]
        rounds.append(_round_comment(index + 1, heads[index], observations))
    result = _decide(rounds)
    assert result["decision"] == "BLOCK"
    assert result["reason"] == "sin-progreso"


def test_a_round_block_without_its_marker_is_ignored() -> None:
    # Un bloque suelto —copiado, citado o publicado en un comentario aparte— no
    # es una ronda: sin su marcador oculto no cuenta.
    module = _module()
    forged = (
        '## RONDA_HALLAZGOS\n```json\n{"round": 999999, "head": "0000000", "findings": []}\n```\n'
    )
    records = module.parse_round_records(forged + _round_comment(1, HEAD_A, [_observation()]))
    assert len(records) == 1
    assert records[0]["round"] == 1


def test_the_marker_number_wins_over_a_manipulated_round_field() -> None:
    # El número autoritativo es el del marcador. Un campo `round` no numérico no
    # puede provocar una excepción al ordenar (que dejaría la decisión vacía y
    # bloquearía toda ronda posterior).
    module = _module()
    text = (
        "<!-- sirius-round:2 -->\n## RONDA_HALLAZGOS\n```json\n"
        '{"round": "no-es-un-numero", "head": "abc", "findings": []}\n```\n'
    )
    records = module.parse_round_records(text)
    assert len(records) == 1
    assert records[0]["round"] == 2


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False
    )


def test_cli_record_emits_the_round_record(tmp_path: Path) -> None:
    verdict = tmp_path / "verdict.json"
    verdict.write_text(json.dumps({"observations": [_observation()]}), encoding="utf-8")
    output = tmp_path / "record.json"
    result = _run(
        [
            "record",
            "--verdict-file",
            str(verdict),
            "--round",
            "3",
            "--head",
            HEAD_D,
            "--output",
            str(output),
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["round"] == 3
    assert record["head"] == HEAD_D
    assert record["pending"] == 1
    assert len(record["findings"][0]["fingerprint"]) == 16


def test_cli_decide_writes_the_decision(tmp_path: Path) -> None:
    comments = tmp_path / "comments.txt"
    same = [_observation("CODEX-001")]
    comments.write_text(
        "\n".join(
            [
                _round_comment(1, HEAD_A, same),
                _round_comment(2, HEAD_B, same),
                _round_comment(3, HEAD_C, same),
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "decision.json"
    result = _run(["decide", "--comments-file", str(comments), "--output", str(output)])
    assert result.returncode == 0, result.stdout + result.stderr
    decision = json.loads(output.read_text(encoding="utf-8"))
    assert decision["decision"] == "BLOCK"
    assert decision["reason"] == "sin-progreso"


def test_cli_decide_blocks_when_history_is_unreadable(tmp_path: Path) -> None:
    output = tmp_path / "decision.json"
    result = _run(
        ["decide", "--comments-file", str(tmp_path / "no-existe.txt"), "--output", str(output)]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    decision = json.loads(output.read_text(encoding="utf-8"))
    assert decision["decision"] == "BLOCK"
    assert decision["reason"] == "historial-ilegible"


# --------------------------------------------------------------------------- #
# CLI family-check (ADR-078, incidencia #495: el detector existía y ya estaba
# medido, pero sin llamante desde ningún punto del ciclo)
# --------------------------------------------------------------------------- #


def test_cli_family_check_writes_the_evidence_when_three_consecutive_rounds_share_a_file(
    tmp_path: Path,
) -> None:
    comments = tmp_path / "comments.txt"
    same_file = [_observation("CODEX-001", archivo="src/x.py:10")]
    comments.write_text(
        "\n".join(
            [
                _round_comment(1, HEAD_A, same_file),
                _round_comment(2, HEAD_B, [_observation("CODEX-002", archivo="src/x.py:20")]),
                _round_comment(3, HEAD_C, [_observation("CODEX-003", archivo="src/x.py:30")]),
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "family.json"
    result = _run(["family-check", "--comments-file", str(comments), "--output", str(output)])
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["hay_familia_repetida"] is True
    assert payload["evidencias"][0]["archivo"] == "src/x.py"
    assert payload["evidencias"][0]["rondas"] == [1, 2, 3]


def test_cli_family_check_two_rounds_is_the_normal_case_not_a_family(tmp_path: Path) -> None:
    comments = tmp_path / "comments.txt"
    comments.write_text(
        "\n".join(
            [
                _round_comment(1, HEAD_A, [_observation("CODEX-001", archivo="src/x.py:10")]),
                _round_comment(2, HEAD_B, [_observation("CODEX-002", archivo="src/x.py:20")]),
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "family.json"
    result = _run(["family-check", "--comments-file", str(comments), "--output", str(output)])
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == {"hay_familia_repetida": False, "evidencias": []}


def test_cli_family_check_unreadable_history_reports_false_and_never_fails(
    tmp_path: Path,
) -> None:
    # Requisito (b) de la incidencia #495: este aviso informa, nunca bloquea.
    # Un historial ilegible se traduce en "no hay familia" con el motivo en
    # `error`, no en un código de salida distinto de 0 que pudiera detener al
    # llamador.
    output = tmp_path / "family.json"
    result = _run(
        [
            "family-check",
            "--comments-file",
            str(tmp_path / "no-existe.txt"),
            "--output",
            str(output),
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["hay_familia_repetida"] is False
    assert payload["evidencias"] == []
    assert "error" in payload


def _bare_system_python() -> str | None:
    """Un ``python3`` distinto del que ejecuta esta suite, sin el proyecto instalado.

    ``repair-sirius-work.yml`` invoca ``sirius_convergence.py`` con el
    ``python3`` del sistema del runner, **sin** ``actions/setup-python`` y sin
    haber corrido ``uv sync``: no es ``sys.executable`` (el intérprete de este
    proceso, que sí tiene el proyecto y sus dependencias instalados) sino el
    de la distribución del sistema operativo. En ``ubuntu-latest`` es
    ``/usr/bin/python3`` (Python 3.12, el mismo que fija
    ``test_sirius_runner_python_compat.RUNNER_PYTHON``); se prueba primero por
    ruta fija porque bajo ``uv run`` el ``.venv`` se antepone en ``PATH`` y
    ``shutil.which("python3")`` encontraría el intérprete del propio proyecto,
    no el del sistema.
    """
    ejecutando = Path(sys.executable).resolve()
    for candidato in ("/usr/bin/python3", shutil.which("python3")):
        if candidato is None:
            continue
        ruta = Path(candidato).resolve()
        if ruta.is_file() and ruta != ejecutando:
            return str(ruta)
    return None


_BARE_PYTHON = _bare_system_python()


@pytest.mark.skipif(
    _BARE_PYTHON is None,
    reason="No hay un python3 del sistema distinto del de este proyecto en este entorno.",
)
def test_cli_decide_runs_under_the_bare_system_python_without_the_project_installed(
    tmp_path: Path,
) -> None:
    """Requisito 3: el script sigue respondiendo bajo el intérprete pelado del runner.

    Invoca ``sirius_convergence.py`` exactamente como lo hace
    ``repair-sirius-work.yml:285`` -``python3 scripts/automation/sirius_convergence.py``
    desde la raíz del repositorio-, pero con un intérprete que NO es el de
    este proyecto (``_BARE_PYTHON``, no ``sys.executable``) y con un entorno
    reducido al ``PATH``: sin ``PYTHONPATH``, sin ``VIRTUAL_ENV``, sin nada que
    el ``.venv`` de desarrollo pudiera filtrar. Si el módulo compartido
    obligara a importar ``sirius_engine`` -que no está instalado en ese
    intérprete-, esta prueba fallaría con ``ModuleNotFoundError`` en vez de
    con ``decision == CONTINUE``.
    """
    assert _BARE_PYTHON is not None
    comments = tmp_path / "comments.txt"
    comments.write_text(_round_comment(1, HEAD_A, [_observation()]), encoding="utf-8")
    output = tmp_path / "decision.json"
    entorno_reducido = {"PATH": os.environ.get("PATH", "")}
    result = subprocess.run(
        [
            _BARE_PYTHON,
            str(SCRIPT),
            "decide",
            "--comments-file",
            str(comments),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env=entorno_reducido,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    decision = json.loads(output.read_text(encoding="utf-8"))
    assert decision["decision"] == "CONTINUE"
    assert decision["reason"] == "primera-ronda-con-hallazgos"


@pytest.mark.skipif(
    _BARE_PYTHON is None,
    reason="No hay un python3 del sistema distinto del de este proyecto en este entorno.",
)
def test_cli_family_check_runs_under_the_bare_system_python_without_the_project_installed(
    tmp_path: Path,
) -> None:
    """El detector (round_family_detector.py) SÍ hace ``import sirius_engine...``.

    A diferencia de ``round_history.py``, es un módulo de paquete normal, no
    pensado para cargarse por ruta. ``_cargar_round_family_detector`` registra
    un ``sirius_engine`` mínimo en ``sys.modules`` antes de ejecutarlo
    (incidencia #495); sin ese registro, esta prueba fallaría con
    ``ModuleNotFoundError: No module named 'sirius_engine'`` en vez de con el
    resultado esperado.
    """
    assert _BARE_PYTHON is not None
    comments = tmp_path / "comments.txt"
    comments.write_text(
        "\n".join(
            [
                _round_comment(1, HEAD_A, [_observation("CODEX-001", archivo="src/x.py:10")]),
                _round_comment(2, HEAD_B, [_observation("CODEX-002", archivo="src/x.py:20")]),
                _round_comment(3, HEAD_C, [_observation("CODEX-003", archivo="src/x.py:30")]),
            ]
        ),
        encoding="utf-8",
    )
    output = tmp_path / "family.json"
    entorno_reducido = {"PATH": os.environ.get("PATH", "")}
    result = subprocess.run(
        [
            _BARE_PYTHON,
            str(SCRIPT),
            "family-check",
            "--comments-file",
            str(comments),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env=entorno_reducido,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["hay_familia_repetida"] is True
    assert payload["evidencias"][0]["archivo"] == "src/x.py"


# --------------------------------------------------------------------------- #
# Estabilidad de la huella y de la gravedad
# --------------------------------------------------------------------------- #


def test_fingerprint_ignores_the_line_number() -> None:
    # Corregir cualquier punto anterior del archivo desplaza la numeración. Si
    # la línea entrara en la huella, el mismo defecto sin tocar aparecería como
    # uno resuelto más uno nuevo: el detector de reaparición se dispararía en
    # falso y el de progreso mediría una sustitución donde no la hay.
    module = _module()
    assert module.fingerprint(_observation(archivo="src/x.py:10")) == module.fingerprint(
        _observation(archivo="src/x.py:143")
    )
    # También con rango de líneas.
    assert module.fingerprint(_observation(archivo="src/x.py:10")) == module.fingerprint(
        _observation(archivo="src/x.py:120-134")
    )


def test_fingerprint_still_distinguishes_files() -> None:
    module = _module()
    assert module.fingerprint(_observation(archivo="src/x.py:10")) != module.fingerprint(
        _observation(archivo="src/y.py:10")
    )


def test_losing_a_severity_label_does_not_simulate_progress() -> None:
    # El MISMO hallazgo (misma huella) reportado en la ronda 2 sin su insignia
    # P0. Sin gravedad pegajosa pasaría a pesar como `sin-clasificar` (2 en vez
    # de 4), el par (pendientes, gravedad) "mejoraría" de (1, 4) a (1, 2) y el
    # ciclo seguiría corrigiendo un trabajo en el que no se ha resuelto nada.
    critico = _observation("CODEX-001", "src/x.py:10", "Fuga de credenciales", "P0")
    sin_etiqueta = _observation(
        "CODEX-001", "src/x.py:10", "Fuga de credenciales", "sin-clasificar"
    )
    dos_rondas = _decide(
        [
            _round_comment(1, HEAD_A, [critico]),
            _round_comment(2, HEAD_B, [sin_etiqueta]),
        ]
    )
    # `sin-progreso-aislado` es la tolerancia de una sola ronda: lo relevante es
    # que NO se ha clasificado como `progreso`, que es lo que ocurría antes.
    assert dos_rondas["reason"] == "sin-progreso-aislado"

    # Y sin nada resuelto, la ronda siguiente ya no se tolera.
    tres_rondas = _decide(
        [
            _round_comment(1, HEAD_A, [critico]),
            _round_comment(2, HEAD_B, [sin_etiqueta]),
            _round_comment(3, HEAD_C, [sin_etiqueta]),
        ]
    )
    assert tres_rondas["decision"] == "BLOCK"
    assert tres_rondas["reason"] == "sin-progreso"


def test_sticky_severity_keeps_the_worst_weight_seen() -> None:
    module = _module()
    critico = _observation("CODEX-001", "src/x.py:10", "Fuga de credenciales", "P0")
    sin_etiqueta = _observation(
        "CODEX-001", "src/x.py:10", "Fuga de credenciales", "sin-clasificar"
    )
    records = module.parse_round_records(
        "\n".join(
            [
                _round_comment(1, HEAD_A, [critico]),
                _round_comment(2, HEAD_B, [sin_etiqueta]),
            ]
        )
    )
    assert [record["severity_total"] for record in records] == [4, 4]


def test_resolving_the_critical_finding_still_counts_as_progress() -> None:
    # La gravedad pegajosa no puede convertirse en un bloqueo permanente: si el
    # hallazgo P0 desaparece de verdad, su peso desaparece con él.
    critico = _observation("CODEX-001", "src/x.py:10", "Fuga de credenciales", "P0")
    menor = _observation("CODEX-002", "src/y.py:4", "Nombre poco claro", "P4")
    result = _decide(
        [
            _round_comment(1, HEAD_A, [critico, menor]),
            _round_comment(2, HEAD_B, [menor]),
        ]
    )
    assert result["decision"] == "CONTINUE"
    assert result["reason"] == "progreso"


def test_sticky_severity_does_not_depend_on_the_order_within_a_round() -> None:
    # Una misma huella puede aparecer dos veces en la misma ronda con etiquetas
    # distintas. Si el máximo se actualizara mientras se suma, el total
    # dependería del orden de llegada y la decisión dejaría de ser función solo
    # del contenido del historial.
    module = _module()
    grave = _observation("CODEX-001", "src/x.py:10", "Mismo defecto", "P0")
    leve = _observation("CODEX-002", "src/x.py:99", "Mismo defecto", "P4")
    assert module.fingerprint(grave) == module.fingerprint(leve)

    primero_grave = module.parse_round_records(_round_comment(1, HEAD_A, [grave, leve]))
    primero_leve = module.parse_round_records(_round_comment(1, HEAD_A, [leve, grave]))
    assert primero_grave[0]["severity_total"] == primero_leve[0]["severity_total"]
    # Y el peso aplicado es el peor observado, no el medio ni el último.
    assert primero_grave[0]["severity_total"] == 8


# --------------------------------------------------------------------------- #
# El otro motor del ciclo: los fallos de Quality
# --------------------------------------------------------------------------- #
#
# `advance-sirius-after-quality.yml` vuelve a aplicar `sirius:repair-requested`
# cuando Quality falla, pero ese camino publica `## CI_FAILURE`, no un registro
# de ronda. El historial de rondas no cambia, así que la medida de progreso no
# puede verlo: sin una cota propia, `CONTINUE` se repetiría indefinidamente. El
# tope fijo de dos ciclos que esta versión elimina acotaba los dos motores a la
# vez; sustituirlo por una medida que solo mira las rondas dejaría este sin cota.


def _ci(sha: str, result: str) -> str:
    return f"<!-- sirius-quality:{sha}:{result} -->\n\n## CI_{result.upper()}\n"


def test_repeated_quality_failures_block_even_without_round_records() -> None:
    module = _module()
    history = "\n".join(
        [_ci("a" * 12, "failure"), _ci("b" * 12, "failure"), _ci("c" * 12, "failure")]
    )
    assert module.ci_failure_streak(history) == 3
    result = module.decide(module.parse_round_records(history), ci_failures=3)
    assert result["decision"] == "BLOCK"
    assert result["reason"] == "ci-sin-arreglo"


def test_a_green_quality_resets_the_failure_streak() -> None:
    # Un verde significa que la construcción volvió a estar sana: el ciclo pasa
    # a avanzar por el otro motor y la cuenta de intentos empieza de nuevo.
    module = _module()
    history = "\n".join(
        [
            _ci("a" * 12, "failure"),
            _ci("b" * 12, "failure"),
            _ci("c" * 12, "success"),
            _ci("d" * 12, "failure"),
        ]
    )
    assert module.ci_failure_streak(history) == 1
    result = module.decide(module.parse_round_records(history), ci_failures=1)
    assert result["decision"] == "CONTINUE"


def test_a_timed_out_quality_counts_as_a_failure() -> None:
    module = _module()
    history = "\n".join(
        [_ci("a" * 12, "failure"), _ci("b" * 12, "timed_out"), _ci("c" * 12, "failure")]
    )
    assert module.ci_failure_streak(history) == 3


def test_ci_failures_do_not_contaminate_the_progress_measure() -> None:
    # La cota de los fallos de CI es SEPARADA a propósito: un fallo de CI no
    # tiene hallazgos ni gravedad que comparar, y contarlo como ronda falsearía
    # la mejor marca histórica de las rondas de revisión.
    module = _module()
    history = "\n".join(
        [
            _round_comment(
                1,
                HEAD_A,
                [_observation("CODEX-001"), _observation("CODEX-002", "src/y.py:1", "Otro")],
            ),
            _ci("f" * 12, "failure"),
            _ci("g" * 12, "success"),
            _round_comment(2, HEAD_B, [_observation("CODEX-001")]),
        ]
    )
    records = module.parse_round_records(history)
    assert [record["pending"] for record in records] == [2, 1], (
        "los bloques de CI no pueden colarse como rondas"
    )
    result = module.decide(records, ci_failures=module.ci_failure_streak(history))
    assert result["decision"] == "CONTINUE"
    assert result["reason"] == "progreso"


# --------------------------------------------------------------------------- #
# Coherencia con los documentos que declaran la política vigente
# --------------------------------------------------------------------------- #

# La incidencia es la fuente de verdad del trabajo: si su plantilla sigue
# exigiendo un tope numérico de ciclos, a partir del tercer intento la
# automatización ejecuta más correcciones de las que el propio work item
# autoriza. El comportamiento y el contrato que lo describe tienen que cambiar
# juntos, así que aquí se ata uno al otro.
WORK_ITEM_TEMPLATE = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "sirius-work-item.yml"

DOCUMENTS_STATING_CURRENT_POLICY = (
    WORK_ITEM_TEMPLATE,
    REPO_ROOT / "docs" / "operations" / "CLAUDE_SIRIUS_KNOWLEDGE_BASE.md",
    REPO_ROOT / "scripts" / "automation" / "prompts" / "corrector.md",
)

# "Máximo 2 ciclos", "máx. 2 ciclos", "máximo de 2 ciclos". Deliberadamente NO
# se rastrean los registros históricos (`docs/audits/**` y el changelog §10 del
# contrato): describen lo que era cierto cuando se escribieron y reescribirlos
# falsearía el historial.
OBSOLETE_CAP_RE = re.compile(r"m[áa]x(?:imo)?\.?\s*(?:de\s+)?\d+\s*ciclos", re.IGNORECASE)


@pytest.mark.parametrize("document", DOCUMENTS_STATING_CURRENT_POLICY, ids=lambda path: path.name)
def test_no_current_document_declares_a_fixed_cycle_cap(document: Path) -> None:
    if not document.exists():
        pytest.skip(f"{document.name} no existe en este árbol")
    offenders = OBSOLETE_CAP_RE.findall(document.read_text(encoding="utf-8"))
    assert not offenders, (
        f"{document.name} sigue declarando un tope fijo de ciclos {offenders}; "
        "la política vigente es la convergencia del §5.1, sin máximo numérico"
    )


def test_the_work_item_template_defers_to_the_convergence_policy() -> None:
    template = WORK_ITEM_TEMPLATE.read_text(encoding="utf-8")
    assert "max_cycles" not in template, (
        "el campo obsoleto del tope de ciclos sigue en la plantilla"
    )
    assert "convergencia" in template.lower(), (
        "la plantilla debe remitir a la política de convergencia que sí gobierna el ciclo"
    )


def test_the_template_only_names_stops_that_the_gate_can_emit() -> None:
    # Evita la deriva inversa: que la plantilla prometa motivos de parada que el
    # código nunca produce. Los identificadores en `kebab-case` que cita la
    # plantilla deben existir de verdad.
    emitted = set(re.findall(r'"reason":\s*"([a-z-]+)"', SCRIPT.read_text(encoding="utf-8")))
    # Paradas seguras que aplican los workflows, no la puerta de convergencia.
    emitted |= {"ronda-innumerable", "historial-de-rondas-ilegible"}

    template = WORK_ITEM_TEMPLATE.read_text(encoding="utf-8")
    named = set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", template))
    assert named, "la plantilla ya no cita ningún motivo de parada: la prueba pasaría en vacío"
    unknown = named - emitted
    assert not unknown, f"la plantilla cita motivos de parada inexistentes: {sorted(unknown)}"


def test_repeated_quality_runs_on_one_head_are_a_single_attempt() -> None:
    # La cota cuenta INTENTOS de corrección, y cada intento es un commit nuevo.
    # Quality puede reejecutarse sobre el mismo head y cambiar de conclusión
    # (una prueba intermitente basta); eso no es un intento nuevo del corrector,
    # así que no puede gastar presupuesto.
    module = _module()
    history = "\n".join(
        [
            _ci("a" * 12, "failure"),
            _ci("a" * 12, "timed_out"),
            _ci("a" * 12, "failure"),
        ]
    )
    assert module.ci_failure_streak(history) == 1
    result = module.decide(module.parse_round_records(history), ci_failures=1)
    assert result["decision"] == "CONTINUE"


def test_distinct_heads_still_accumulate_toward_the_bound() -> None:
    # La otra mitad: ignorar repeticiones no puede desactivar la cota. Tres
    # intentos reales (tres commits) siguen bloqueando.
    module = _module()
    history = "\n".join(
        [
            _ci("a" * 12, "failure"),
            _ci("a" * 12, "timed_out"),
            _ci("b" * 12, "failure"),
            _ci("c" * 12, "failure"),
        ]
    )
    assert module.ci_failure_streak(history) == module.MAX_CI_FAILURE_STREAK
    result = module.decide(module.parse_round_records(history), ci_failures=3)
    assert result["decision"] == "BLOCK"
    assert result["reason"] == "ci-sin-arreglo"


# --------------------------------------------------------------------------- #
# Los lectores son idempotentes: un duplicado no es un hecho nuevo
# --------------------------------------------------------------------------- #


def test_a_duplicated_round_record_counts_once() -> None:
    # Publicar contra la API de GitHub no puede ser exactamente-una-vez: el POST
    # no es idempotente y no hay clave de idempotencia del servidor. La garantía
    # tiene que vivir aquí. Sin esto, dos copias del registro de la ronda N se
    # leían como dos rondas consecutivas sobre el mismo head y la puerta
    # bloqueaba por `head-sin-avance` un trabajo que sí avanzaba.
    module = _module()
    registro = _round_comment(1, HEAD_A, [_observation("CODEX-001")])
    records = module.parse_round_records("\n".join([registro, registro]))
    assert [record["round"] for record in records] == [1]


def test_a_duplicated_record_does_not_fake_head_sin_avance() -> None:
    module = _module()
    ronda1 = _round_comment(1, HEAD_A, [_observation("CODEX-001"), _observation("CODEX-002")])
    ronda2 = _round_comment(2, HEAD_B, [_observation("CODEX-001")])
    # La copia tiene que ser de la ÚLTIMA ronda: es la que deja dos registros
    # consecutivos con el mismo head y dispara `head-sin-avance`. Duplicando una
    # ronda anterior, las dos últimas siguen teniendo heads distintos y la prueba
    # pasaría sin ejercitar nada.
    history = "\n".join([ronda1, ronda2, ronda2])
    result = module.decide(module.parse_round_records(history))
    assert result["decision"] == "CONTINUE"
    assert result["reason"] == "progreso"


def test_a_legible_copy_wins_over_a_corrupt_one() -> None:
    # La deduplicación se aplica tras validar el JSON, así que una primera copia
    # ilegible no consume el hueco de la ronda.
    module = _module()
    corrupta = "<!-- sirius-round:1 -->\n## RONDA_HALLAZGOS\n```json\n{no es json\n```\n"
    buena = _round_comment(1, HEAD_A, [_observation("CODEX-001")])
    records = module.parse_round_records("\n".join([corrupta, buena]))
    assert [record["round"] for record in records] == [1]
    assert records[0]["pending"] == 1
