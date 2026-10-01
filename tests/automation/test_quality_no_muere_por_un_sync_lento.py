"""Quality no muere cancelado por un `uv sync` sin caché (ADR-224).

El 01-10 tres ejecuciones se cancelaron a los 20 minutos del job con el paso
«Sync environment» entre 11 y 16,5 min (sin caché, PyPI servía 243 MiB de
PySide6 a menos de 1 MB/s). Un job cancelado no guarda la caché de `setup-uv`,
así que la rama volvía a fallarla y a cancelarse. Estas pruebas leen el YAML
REAL: los dos pasos largos llevan plazo propio (fallan ruidosamente, como el
paso de apt desde #202/#206) y el tope del job los cubre a los dos con holgura.
"""

from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
QUALITY = RAIZ / ".github" / "workflows" / "quality.yml"

#: Lo medido el 01-10 sin caché: 8 m 0 s, 11 m 47 s, 15 m 46 s y 16 m 30 s.
PEOR_SYNC_MEDIDO_MIN = 17
#: Lo medido en Pytest los días malos (08-09, 20-09, 21-09): 19 m 20 s a 19 m 37 s.
PEOR_PYTEST_MEDIDO_MIN = 20
#: Checkout, Qt, uv, ruff y mypy, juntos, hoy: menos de 3 min.
RESTO_DEL_JOB_MIN = 5


def _pasos() -> tuple[int, dict[str, dict[str, object]]]:
    flujo = yaml.safe_load(QUALITY.read_text(encoding="utf-8"))
    trabajo = flujo["jobs"]["quality"]
    pasos = {str(paso.get("name")): paso for paso in trabajo["steps"]}
    return int(trabajo["timeout-minutes"]), pasos


def test_los_dos_pasos_largos_de_quality_tienen_plazo_propio_por_encima_de_lo_medido() -> None:
    _, pasos = _pasos()
    sync = pasos["Sync environment"].get("timeout-minutes")
    pytest_ = pasos["Pytest"].get("timeout-minutes")
    assert isinstance(sync, int) and sync >= PEOR_SYNC_MEDIDO_MIN, (
        f"«Sync environment» necesita un plazo propio por encima de los {PEOR_SYNC_MEDIDO_MIN} "
        f"min medidos sin caché el 01-10; tiene {sync!r}: sin él, un PyPI lento se lleva el "
        "job entero a `cancelled`, que no guarda la caché y vuelve a pasar"
    )
    assert isinstance(pytest_, int) and pytest_ >= PEOR_PYTEST_MEDIDO_MIN, (
        f"«Pytest» necesita un plazo propio por encima de los {PEOR_PYTEST_MEDIDO_MIN} min "
        f"que rozó el 08-09, el 20-09 y el 21-09; tiene {pytest_!r}"
    )


def test_el_tope_del_job_de_quality_cubre_los_dos_pasos_largos_y_el_resto() -> None:
    """Si el tope del job fuera menor que la suma, los plazos de los pasos serían
    decorativos: el job moriría cancelado antes de que ninguno fallara solo."""
    tope, pasos = _pasos()
    sync = pasos["Sync environment"]["timeout-minutes"]
    pytest_ = pasos["Pytest"]["timeout-minutes"]
    assert isinstance(sync, int) and isinstance(pytest_, int)
    assert tope >= sync + pytest_ + RESTO_DEL_JOB_MIN, (
        f"el job de Quality tiene {tope} min y sus pasos largos suman {sync} + {pytest_} "
        f"(más {RESTO_DEL_JOB_MIN} del resto): con menos, el tope del job corta antes que "
        "los plazos propios y la ejecución vuelve a ser `cancelled`"
    )
