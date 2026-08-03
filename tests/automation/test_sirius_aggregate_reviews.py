"""Pruebas de ``scripts/automation/sirius_aggregate_reviews.py``.

El agregador es puro (lee dos archivos JSON, escribe uno): se ejercita como CLI
sin red ni ``gh``. Cubre las reglas de precedencia deterministas, la
verificación de SHA, la deduplicación exacta con procedencia y el modo ``solo``
que reproduce el flujo vigente sin Codex.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "automation" / "sirius_aggregate_reviews.py"

HEAD = "1234567890abcdef1234567890abcdef12345678"
OTHER_HEAD = "feedfacefeedfacefeedfacefeedfacefeedface"


def _claude_observation(**overrides: str) -> dict[str, str]:
    base = {
        "id": "R1",
        "severidad": "alta",
        "archivo": "src/x.py:10",
        "problema": "No valida la entrada.",
        "criterio_esperado": "Debe validar la entrada.",
        "prueba": "test_x_invalid",
        "limites_correccion": "solo src/x.py",
    }
    base.update(overrides)
    return base


def _codex_observation(**overrides: str) -> dict[str, str]:
    base = {
        "id": "CODEX-001",
        "severidad": "P2",
        "archivo": "src/y.py:20",
        "problema": "Comprueba mal el límite.",
        "criterio_esperado": "Resolver el defecto descrito.",
        "prueba": "https://github.com/o/r/pull/9#discussion_r1",
        "limites_correccion": "solo el componente señalado",
    }
    base.update(overrides)
    return base


def _claude(
    verdict: str = "REVIEW_APPROVED",
    *,
    sha: str | None = HEAD,
    observations: list[dict[str, str]] | None = None,
    summary: str = "resumen claude",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "verdict": verdict,
        "summary": summary,
        "observations": observations if observations is not None else [],
    }
    if sha is not None:
        payload["reviewed_head_sha"] = sha
    return payload


def _codex(
    status: str = "APPROVED",
    *,
    sha: str | None = HEAD,
    observations: list[dict[str, str]] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "source": "codex",
        "status": status,
        "reason": reason,
        "reviewed_head_sha": sha,
        "trigger_comment_id": 500,
        "review_id": 700,
        "summary": "resumen codex",
        "observations": observations if observations is not None else [],
    }


def _run(
    tmp_path: Path,
    claude: object,
    codex: object,
    *,
    mode: str = "dual",
    raw_claude: str | None = None,
    raw_codex: str | None = None,
    skip_claude_file: bool = False,
    skip_codex_file: bool = False,
) -> dict[str, Any]:
    claude_file = tmp_path / "claude.json"
    codex_file = tmp_path / "codex.json"
    output = tmp_path / "aggregated.json"
    if not skip_claude_file:
        claude_file.write_text(
            raw_claude if raw_claude is not None else json.dumps(claude), encoding="utf-8"
        )
    if not skip_codex_file:
        codex_file.write_text(
            raw_codex if raw_codex is not None else json.dumps(codex), encoding="utf-8"
        )
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--claude-file",
            str(claude_file),
            "--codex-file",
            str(codex_file),
            "--expected-head",
            HEAD,
            "--mode",
            mode,
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data: dict[str, Any] = json.loads(output.read_text(encoding="utf-8"))
    return data


# --------------------------------------------------------------------------- #
# Reglas de precedencia
# --------------------------------------------------------------------------- #


def test_both_approve_same_head(tmp_path: Path) -> None:
    result = _run(tmp_path, _claude(), _codex())
    assert result["verdict"] == "REVIEW_APPROVED"
    assert result["reviewed_head_sha"] == HEAD
    assert result["sources"] == {
        "claude": {"status": "REVIEW_APPROVED"},
        "codex": {"status": "APPROVED"},
    }
    assert result["observations"] == []


def test_claude_requests_changes(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _claude("CHANGES_REQUESTED", observations=[_claude_observation()]),
        _codex(),
    )
    assert result["verdict"] == "CHANGES_REQUESTED"
    assert [o["id"] for o in result["observations"]] == ["CLAUDE-R1"]


def test_codex_requests_changes(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _claude(),
        _codex("CHANGES_REQUESTED", observations=[_codex_observation()]),
    )
    assert result["verdict"] == "CHANGES_REQUESTED"
    assert [o["id"] for o in result["observations"]] == ["CODEX-001"]


def test_both_request_changes_merges_observations(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _claude("CHANGES_REQUESTED", observations=[_claude_observation()]),
        _codex("CHANGES_REQUESTED", observations=[_codex_observation()]),
    )
    assert result["verdict"] == "CHANGES_REQUESTED"
    ids = [o["id"] for o in result["observations"]]
    assert ids == ["CLAUDE-R1", "CODEX-001"]
    assert result["sources"]["claude"]["status"] == "CHANGES_REQUESTED"
    assert result["sources"]["codex"]["status"] == "CHANGES_REQUESTED"


def test_claude_blocked_by_decision_wins_over_codex_changes(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _claude("BLOCKED_BY_DECISION", sha=None, summary="decisión pendiente"),
        _codex("CHANGES_REQUESTED", observations=[_codex_observation()]),
    )
    assert result["verdict"] == "BLOCKED_BY_DECISION"
    assert "decisión pendiente" in result["summary"]


def test_claude_failed_safely(tmp_path: Path) -> None:
    result = _run(tmp_path, _claude("FAILED_SAFELY", sha=None), _codex())
    assert result["verdict"] == "FAILED_SAFELY"


def test_codex_failed_safely_never_degrades_to_claude_only(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _claude(),
        _codex("FAILED_SAFELY", sha=None, reason="timeout"),
    )
    assert result["verdict"] == "FAILED_SAFELY"
    assert "timeout" in result["summary"]


def test_claude_wrong_sha_fails_safely(tmp_path: Path) -> None:
    result = _run(tmp_path, _claude(sha=OTHER_HEAD), _codex())
    assert result["verdict"] == "FAILED_SAFELY"
    assert "Claude" in result["summary"]


def test_claude_missing_sha_fails_safely(tmp_path: Path) -> None:
    result = _run(tmp_path, _claude(sha=None), _codex())
    assert result["verdict"] == "FAILED_SAFELY"


def test_codex_wrong_sha_fails_safely(tmp_path: Path) -> None:
    result = _run(tmp_path, _claude(), _codex(sha=OTHER_HEAD))
    assert result["verdict"] == "FAILED_SAFELY"
    assert "Codex" in result["summary"]


def test_claude_abbreviated_sha_prefix_is_accepted(tmp_path: Path) -> None:
    result = _run(tmp_path, _claude(sha=HEAD[:12]), _codex())
    assert result["verdict"] == "REVIEW_APPROVED"


def test_missing_claude_file_fails_safely(tmp_path: Path) -> None:
    result = _run(tmp_path, None, _codex(), skip_claude_file=True)
    assert result["verdict"] == "FAILED_SAFELY"
    assert result["sources"]["claude"]["status"] == "INVALID"


def test_corrupt_codex_json_fails_safely(tmp_path: Path) -> None:
    result = _run(tmp_path, _claude(), None, raw_codex="{no es json")
    assert result["verdict"] == "FAILED_SAFELY"
    assert result["sources"]["codex"]["status"] == "INVALID"


def test_changes_requested_with_empty_observations_fails_safely(tmp_path: Path) -> None:
    result = _run(tmp_path, _claude("CHANGES_REQUESTED", observations=[]), _codex())
    assert result["verdict"] == "FAILED_SAFELY"


def test_codex_changes_with_empty_observations_fails_safely(tmp_path: Path) -> None:
    result = _run(tmp_path, _claude(), _codex("CHANGES_REQUESTED", observations=[]))
    assert result["verdict"] == "FAILED_SAFELY"


# --------------------------------------------------------------------------- #
# Deduplicación y procedencia
# --------------------------------------------------------------------------- #


def test_exact_duplicates_within_source_are_removed(tmp_path: Path) -> None:
    duplicated = [_claude_observation(id="R1"), _claude_observation(id="R2")]
    result = _run(
        tmp_path,
        _claude("CHANGES_REQUESTED", observations=duplicated),
        _codex(),
    )
    assert [o["id"] for o in result["observations"]] == ["CLAUDE-R1"]


def test_same_problem_with_different_criteria_is_not_deduplicated(tmp_path: Path) -> None:
    # Mismo archivo y mismo problema, pero criterio esperado distinto: NO son
    # duplicados exactos y deben conservarse ambos.
    observations = [
        _claude_observation(id="R1"),
        _claude_observation(id="R2", criterio_esperado="Un criterio distinto."),
    ]
    result = _run(
        tmp_path,
        _claude("CHANGES_REQUESTED", observations=observations),
        _codex(),
    )
    assert [o["id"] for o in result["observations"]] == ["CLAUDE-R1", "CLAUDE-R2"]


def test_similar_but_not_identical_observations_are_kept(tmp_path: Path) -> None:
    similar = [
        _claude_observation(id="R1", problema="No valida la entrada."),
        _claude_observation(id="R2", problema="No valida la entrada vacía."),
    ]
    result = _run(
        tmp_path,
        _claude("CHANGES_REQUESTED", observations=similar),
        _codex(),
    )
    assert [o["id"] for o in result["observations"]] == ["CLAUDE-R1", "CLAUDE-R2"]


def test_cross_source_same_finding_keeps_both_provenances(tmp_path: Path) -> None:
    # Mismo archivo y mismo cuerpo desde fuentes distintas: se conservan ambos
    # hallazgos con su procedencia (nunca deduplicación entre fuentes).
    shared = {"archivo": "src/x.py:10", "problema": "No valida la entrada."}
    result = _run(
        tmp_path,
        _claude("CHANGES_REQUESTED", observations=[_claude_observation(**shared)]),
        _codex("CHANGES_REQUESTED", observations=[_codex_observation(**shared)]),
    )
    ids = [o["id"] for o in result["observations"]]
    assert ids == ["CLAUDE-R1", "CODEX-001"]


def test_observations_carry_corrector_contract_keys(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _claude("CHANGES_REQUESTED", observations=[_claude_observation()]),
        _codex("CHANGES_REQUESTED", observations=[_codex_observation()]),
    )
    for observation in result["observations"]:
        assert set(observation) == {
            "id",
            "severidad",
            "archivo",
            "problema",
            "criterio_esperado",
            "prueba",
            "limites_correccion",
        }


# --------------------------------------------------------------------------- #
# Modo solo (bandera desactivada): flujo vigente sin Codex
# --------------------------------------------------------------------------- #


def test_solo_mode_ignores_codex_entirely(tmp_path: Path) -> None:
    result = _run(tmp_path, _claude(), None, mode="solo", skip_codex_file=True)
    assert result["verdict"] == "REVIEW_APPROVED"
    assert "codex" not in result["sources"]


def test_solo_mode_changes_requested_keeps_claude_observations(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _claude("CHANGES_REQUESTED", observations=[_claude_observation()]),
        None,
        mode="solo",
        skip_codex_file=True,
    )
    assert result["verdict"] == "CHANGES_REQUESTED"
    assert [o["id"] for o in result["observations"]] == ["CLAUDE-R1"]
