"""``sirius_drip_guard_cli.py``: costura del guardián de goteo en vivo (incidencia #496, ADR-121).

Fija la costura del comando -carga los módulos compartidos por ruta de
fichero (igual que ``sirius_convergence.py``, porque se ejecuta con el
``python3`` del sistema sin el proyecto instalado), lee observaciones e
historial ya existentes, invoca ``gh api compare`` a través de un binario
``gh`` simulado en el PATH, y escribe el resultado anotado-. El criterio de
marcado en sí ya tiene su propia suite en ``tests/engine/test_drip_guard.py``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "automation" / "sirius_drip_guard_cli.py"

HEAD1 = "1" * 40
HEAD2 = "2" * 40


def _module() -> Any:
    name = "sirius_drip_guard_cli_under_test"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_GH_STUB = """#!/usr/bin/env bash
# Simula `gh api repos/.../compare/{h1}...{h2}`: devuelve el fichero que
# indique GH_STUB_RESPONSE (o "{\\"files\\": []}" si no está definida).
if [ -n "${GH_STUB_RESPONSE:-}" ]; then
  cat "$GH_STUB_RESPONSE"
else
  printf '{"files": []}'
fi
"""


def _instalar_gh_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, respuesta: str) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(_GH_STUB, encoding="utf-8")
    gh.chmod(0o755)
    respuesta_file = tmp_path / "gh_response.json"
    respuesta_file.write_text(respuesta, encoding="utf-8")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GH_STUB_RESPONSE", str(respuesta_file))


def _round1_history(head: str = HEAD1) -> str:
    record = json.dumps({"round": 1, "head": head, "findings": []})
    return f"<!-- sirius-round:1 -->\n\n## RONDA_HALLAZGOS\n```json\n{record}\n```\n"


def _observation(archivo: str = "src/x.py:10") -> dict[str, str]:
    return {"id": "R1", "severidad": "alta", "archivo": archivo, "problema": "..."}


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_marca_un_hallazgo_cuando_el_fichero_no_cambio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _instalar_gh_stub(tmp_path, monkeypatch, respuesta='{"files": []}')
    comments = tmp_path / "comments.txt"
    comments.write_text(_round1_history(), encoding="utf-8")
    observations = tmp_path / "observations.json"
    _write_json(observations, [_observation()])
    output = tmp_path / "output.json"

    codigo = _module().main(
        [
            "--repo",
            "owner/repo",
            "--comments-file",
            str(comments),
            "--round",
            "2",
            "--head",
            HEAD2,
            "--observations",
            str(observations),
            "--output",
            str(output),
        ]
    )

    assert codigo == 0
    anotadas = json.loads(output.read_text(encoding="utf-8"))
    assert "posible goteo" in anotadas[0]["posible_goteo"]


def test_no_marca_una_linea_dentro_de_un_hunk_anadido(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    patch = "@@ -8,2 +8,4 @@\n context\n+añadida\n+línea 10 añadida\n context"
    respuesta = json.dumps(
        {"files": [{"filename": "src/x.py", "status": "modified", "patch": patch}]}
    )
    _instalar_gh_stub(tmp_path, monkeypatch, respuesta=respuesta)
    comments = tmp_path / "comments.txt"
    comments.write_text(_round1_history(), encoding="utf-8")
    observations = tmp_path / "observations.json"
    _write_json(observations, [_observation()])
    output = tmp_path / "output.json"

    codigo = _module().main(
        [
            "--repo",
            "owner/repo",
            "--comments-file",
            str(comments),
            "--round",
            "2",
            "--head",
            HEAD2,
            "--observations",
            str(observations),
            "--output",
            str(output),
        ]
    )

    assert codigo == 0
    anotadas = json.loads(output.read_text(encoding="utf-8"))
    assert "posible_goteo" not in anotadas[0]


def test_ronda_1_nunca_marca(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _instalar_gh_stub(tmp_path, monkeypatch, respuesta='{"files": []}')
    comments = tmp_path / "comments.txt"
    comments.write_text("", encoding="utf-8")
    observations = tmp_path / "observations.json"
    _write_json(observations, [_observation()])
    output = tmp_path / "output.json"

    codigo = _module().main(
        [
            "--repo",
            "owner/repo",
            "--comments-file",
            str(comments),
            "--round",
            "1",
            "--head",
            HEAD1,
            "--observations",
            str(observations),
            "--output",
            str(output),
        ]
    )

    assert codigo == 0
    anotadas = json.loads(output.read_text(encoding="utf-8"))
    assert "posible_goteo" not in anotadas[0]


def test_gh_no_disponible_se_calla_y_no_bloquea(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # PATH sin `gh`: gh_compare_file recibe un fallo de proceso y devuelve
    # None (SIN_INFORMACION), nunca una marca. El proceso completo sigue en
    # verde: el guardián es estrictamente informativo (regla (a), incidencia #496).
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    (tmp_path / "empty-bin").mkdir()
    comments = tmp_path / "comments.txt"
    comments.write_text(_round1_history(), encoding="utf-8")
    observations = tmp_path / "observations.json"
    _write_json(observations, [_observation()])
    output = tmp_path / "output.json"

    codigo = _module().main(
        [
            "--repo",
            "owner/repo",
            "--comments-file",
            str(comments),
            "--round",
            "2",
            "--head",
            HEAD2,
            "--observations",
            str(observations),
            "--output",
            str(output),
        ]
    )

    assert codigo == 0
    anotadas = json.loads(output.read_text(encoding="utf-8"))
    assert "posible_goteo" not in anotadas[0]


def test_observaciones_ilegibles_publica_sin_anotar_y_no_falla(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _instalar_gh_stub(tmp_path, monkeypatch, respuesta='{"files": []}')
    comments = tmp_path / "comments.txt"
    comments.write_text(_round1_history(), encoding="utf-8")
    observations = tmp_path / "observations.json"
    observations.write_text("esto no es JSON", encoding="utf-8")
    output = tmp_path / "output.json"

    codigo = _module().main(
        [
            "--repo",
            "owner/repo",
            "--comments-file",
            str(comments),
            "--round",
            "2",
            "--head",
            HEAD2,
            "--observations",
            str(observations),
            "--output",
            str(output),
        ]
    )

    assert codigo == 0
    assert json.loads(output.read_text(encoding="utf-8")) == []


def test_historial_ilegible_publica_las_observaciones_sin_anotar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _instalar_gh_stub(tmp_path, monkeypatch, respuesta='{"files": []}')
    observations = tmp_path / "observations.json"
    _write_json(observations, [_observation()])
    output = tmp_path / "output.json"

    codigo = _module().main(
        [
            "--repo",
            "owner/repo",
            "--comments-file",
            str(tmp_path / "no-existe.txt"),
            "--round",
            "2",
            "--head",
            HEAD2,
            "--observations",
            str(observations),
            "--output",
            str(output),
        ]
    )

    assert codigo == 0
    anotadas = json.loads(output.read_text(encoding="utf-8"))
    assert anotadas == [_observation()]
