"""La tabla de ``docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md`` dice la verdad (ADR-241).

La comprobación es la de ``trazabilidad_del_robot``, la misma que vigila la
tabla de la 0.2 y a la que ``test_robot_0_2_trazabilidad.py`` da tablas rotas a
propósito. Aquí está lo que es de la 0.3: su ``Version`` y su inventario
aprobado.
"""

from __future__ import annotations

from pathlib import Path

from conductor_robot_0_3 import PIEZAS, PIEZAS_ENTREGADAS
from trazabilidad_del_robot import Inventario, Version, defectos_de

_RAIZ = Path(__file__).resolve().parents[2]
_CARPETA = _RAIZ / "tests" / "acceptance"
_VERSION = Version(
    documento=_RAIZ / "docs" / "evolution" / "PRUEBAS_0.3_DEL_ROBOT.md",
    prefijo_pa="PA-R03-",
    prefijo_e="E-R03-",
    patron="test_robot_0_3_*.py",
    piezas=PIEZAS,
    adr="ADR-241",
)

#: El inventario aprobado en ADR-241: 10 PA, 27 pruebas de máquina y seis
#: evaluaciones del propietario; ADR-245 añade una prueba a PA-R03-07, hasta dónde oyó lo
#: que le cortaron, por decisión del propietario del 15-10-2026: 28. Una prueba se puede
#: renombrar o mejorar, pero quitar una PA, una prueba o una evaluación es retirar una
#: prueba, y eso no lo hace una sesión sola (AGENTS.md): se cambia aquí, a la vista de la
#: revisión.
INVENTARIO_APROBADO = Inventario(
    pruebas_por_pa={
        "PA-R03-01": 4,
        "PA-R03-02": 3,
        "PA-R03-03": 2,
        "PA-R03-04": 3,
        "PA-R03-05": 2,
        "PA-R03-06": 3,
        "PA-R03-07": 3,
        "PA-R03-08": 4,
        "PA-R03-09": 1,
        "PA-R03-10": 3,
    },
    evaluaciones=frozenset(f"E-R03-{n:02d}" for n in range(1, 7)),
)


def test_la_tabla_de_las_pruebas_de_la_0_3_dice_la_verdad() -> None:
    assert (
        defectos_de(_VERSION, _CARPETA, Path(__file__).name, PIEZAS_ENTREGADAS, INVENTARIO_APROBADO)
        == []
    )


def test_el_inventario_aprobado_suma_las_28_pruebas_y_las_seis_evaluaciones() -> None:
    assert len(INVENTARIO_APROBADO.pruebas_por_pa) == 10
    assert sum(INVENTARIO_APROBADO.pruebas_por_pa.values()) == 28
    assert len(INVENTARIO_APROBADO.evaluaciones) == 6
