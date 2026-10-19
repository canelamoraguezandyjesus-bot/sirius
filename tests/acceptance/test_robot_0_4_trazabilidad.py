"""La tabla de ``docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md`` dice la verdad (ADR-259).

La comprobación es la de ``trazabilidad_del_robot``, la misma que vigila las tablas de la
0.2 y la 0.3 y a la que ``test_robot_0_2_trazabilidad.py`` da tablas rotas a propósito.
Aquí está lo que es de la 0.4: su ``Version`` y su inventario aprobado.
"""

from __future__ import annotations

from pathlib import Path

from conductor_robot_0_4 import PIEZAS, PIEZAS_ENTREGADAS
from trazabilidad_del_robot import Inventario, Version, defectos_de

_RAIZ = Path(__file__).resolve().parents[2]
_CARPETA = _RAIZ / "tests" / "acceptance"
_VERSION = Version(
    documento=_RAIZ / "docs" / "evolution" / "PRUEBAS_0.4_DEL_ROBOT.md",
    prefijo_pa="PA-R04-",
    prefijo_e="E-R04-",
    patron="test_robot_0_4_*.py",
    piezas=PIEZAS,
    adr="ADR-259",
)

#: El inventario aprobado en ADR-259: 14 PA, 28 pruebas de máquina y cinco evaluaciones
#: del propietario. Una prueba se puede renombrar o mejorar, pero quitar una PA, una
#: prueba o una evaluación es retirar una prueba, y eso no lo hace una sesión sola
#: (AGENTS.md): se cambia aquí, a la vista de la revisión.
INVENTARIO_APROBADO = Inventario(
    pruebas_por_pa={
        "PA-R04-01": 1,
        "PA-R04-02": 2,
        "PA-R04-03": 1,
        "PA-R04-04": 1,
        "PA-R04-05": 4,
        "PA-R04-06": 3,
        "PA-R04-07": 2,
        "PA-R04-08": 2,
        "PA-R04-09": 1,
        "PA-R04-10": 2,
        "PA-R04-11": 1,
        "PA-R04-12": 2,
        "PA-R04-13": 4,
        "PA-R04-14": 2,
    },
    evaluaciones=frozenset(f"E-R04-{n:02d}" for n in range(1, 6)),
)


def test_la_tabla_de_las_pruebas_de_la_0_4_dice_la_verdad() -> None:
    assert (
        defectos_de(_VERSION, _CARPETA, Path(__file__).name, PIEZAS_ENTREGADAS, INVENTARIO_APROBADO)
        == []
    )


def test_el_inventario_aprobado_suma_las_28_pruebas_y_las_cinco_evaluaciones() -> None:
    assert len(INVENTARIO_APROBADO.pruebas_por_pa) == 14
    assert sum(INVENTARIO_APROBADO.pruebas_por_pa.values()) == 28
    assert len(INVENTARIO_APROBADO.evaluaciones) == 5
