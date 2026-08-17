"""Punto de entrada del subproceso de kill-injection (ADR-026, incidencia #182).

Se invoca como::

    python -m experiments.work_engine_spike_i3.writer_process <diario> <registro.json> <kill_at|->

Llama a la MISMA función de escritura durable que usa el almacén en proceso
(:func:`experiments.work_engine_spike_i3.durable_journal.append_durably`) con
el punto de corte pedido. Vive en su propio módulo, invocado como proceso de
sistema operativo aparte (no un hilo ni una simulación dentro del mismo
intérprete que hace la comprobación), para que "matar el proceso" sea
literal: el proceso padre del test nunca corre el código que muere.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from experiments.work_engine_spike_i3.durable_journal import KillPoint, append_durably


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
