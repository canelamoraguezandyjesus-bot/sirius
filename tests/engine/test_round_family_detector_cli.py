"""``sirius-familia-repetida``: línea de órdenes del detector de M1 (incidencia #277).

Fija la costura del comando -lee un archivo ya existente, publica JSON-, no
el criterio en sí, que ya tiene su propia suite en
``test_round_family_detector.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sirius_engine import round_family_detector_cli as cli

_RONDA_1 = (
    "<!-- sirius-round:1 -->\n\n## RONDA_HALLAZGOS\n```json\n"
    '{"round": 1, "head": "a", "findings": '
    '[{"fingerprint": "f1", "severity": "P2", "source": "CODEX", "file": "src/x.py"}]}\n'
    "```\n"
)
_RONDA_2 = (
    "<!-- sirius-round:2 -->\n\n## RONDA_HALLAZGOS\n```json\n"
    '{"round": 2, "head": "b", "findings": '
    '[{"fingerprint": "f2", "severity": "P2", "source": "CODEX", "file": "src/x.py"}]}\n'
    "```\n"
)
_RONDA_3 = (
    "<!-- sirius-round:3 -->\n\n## RONDA_HALLAZGOS\n```json\n"
    '{"round": 3, "head": "c", "findings": '
    '[{"fingerprint": "f3", "severity": "P2", "source": "CODEX", "file": "src/x.py"}]}\n'
    "```\n"
)


def test_senala_familia_repetida_y_la_publica_en_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    historial = tmp_path / "historial.txt"
    historial.write_text(_RONDA_1 + _RONDA_2 + _RONDA_3, encoding="utf-8")

    codigo = cli.main(["--historial", str(historial)])

    assert codigo == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hay_familia_repetida"] is True
    assert payload["evidencias"][0]["archivo"] == "src/x.py"
    assert payload["evidencias"][0]["rondas"] == [1, 2, 3]


def test_sin_familia_repetida_publica_evidencias_vacias(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    historial = tmp_path / "historial.txt"
    historial.write_text(_RONDA_1 + _RONDA_2, encoding="utf-8")

    codigo = cli.main(["--historial", str(historial)])

    assert codigo == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"hay_familia_repetida": False, "evidencias": []}


def test_escribe_en_el_archivo_de_salida_si_se_pide(tmp_path: Path) -> None:
    historial = tmp_path / "historial.txt"
    historial.write_text(_RONDA_1 + _RONDA_2 + _RONDA_3, encoding="utf-8")
    salida = tmp_path / "resultado.json"

    codigo = cli.main(["--historial", str(historial), "--salida", str(salida)])

    assert codigo == 0
    payload = json.loads(salida.read_text(encoding="utf-8"))
    assert payload["hay_familia_repetida"] is True


def test_historial_inexistente_falla_con_diagnostico(tmp_path: Path) -> None:
    codigo = cli.main(["--historial", str(tmp_path / "no-existe.txt")])

    assert codigo == 1


def test_salida_en_directorio_inexistente_falla_con_diagnostico(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    historial = tmp_path / "historial.txt"
    historial.write_text(_RONDA_1 + _RONDA_2 + _RONDA_3, encoding="utf-8")
    salida = tmp_path / "directorio-inexistente" / "out.json"

    codigo = cli.main(["--historial", str(historial), "--salida", str(salida)])

    assert codigo == 1
    assert not salida.exists()
    assert cli.COMANDO in capsys.readouterr().err
