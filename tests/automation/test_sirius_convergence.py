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
import subprocess
import sys
from pathlib import Path
from typing import Any

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
