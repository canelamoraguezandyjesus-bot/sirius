"""Punto de entrada del subproceso de kill-injection contra el diario de producción (A2, #186).

Réplica de ``experiments/work_engine_spike_i3/writer_process.py`` (S1,
incidencia #182), apuntada al camino de producción
(:mod:`sirius_engine.adapters.durable.journal`) en vez de al spike. Vive en
``tests/engine/`` -no en ``src/``- porque es arnés de pruebas, no código de
producción: la única razón de que exista un módulo de sistema operativo
aparte es que "matar el proceso" sea literal (``subprocess.run`` real, no un
hilo ni una simulación dentro del intérprete que hace la comprobación).

Se invoca como::

    python -m tests.engine._durable_writer_process <diario> <registro.json> <kill_at|->
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sirius_engine.adapters.durable.journal import KillPoint, append_durably


def main(argv: list[str]) -> int:
    journal_path = Path(argv[1])
    record_path = Path(argv[2])
    kill_at_name = argv[3]
    kill_at = None if kill_at_name == "-" else KillPoint(kill_at_name)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    append_durably(journal_path, record, kill_at=kill_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
