"""El estado de un ADR no contradice su propia línea de aprobación (ADR-209).

EL DEFECTO QUE ESTO CIERRA. Todo ADR de este repositorio declara, dos líneas
más abajo del estado, qué lo aprueba: «la fusión de la PR por el propietario».
Y 150 de los primeros 203 decían a la vez `Estado: PROPUESTO` **estando
fusionados en `main`**: la fusión ya había ocurrido, así que la línea de estado
contradecía a la de aprobación. Un campo que dice lo mismo en el 74 % de los
casos y además es falso no informa de nada; el propietario lo dijo más corto:
«que ponga lo que es».

QUÉ COMPRUEBA. Que ningún ADR declara `PROPUESTO` y que el estado es uno de los
tres que quedan. Es determinista: lee ficheros y compara texto.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DECISIONES = REPO_ROOT / "docs" / "decisions"
PLANTILLA = DECISIONES / "PLANTILLA.md"

#: Los tres estados que quedan. `APROBADO` es el normal: lo que lo aprueba lo
#: dice la línea `Aprobación`, y en este repositorio es la fusión de la PR.
ESTADOS = ("APROBADO", "RECHAZADO", "SUPERADO por ADR-")

LINEA_ESTADO = re.compile(r"^- Estado:\s*(.+)$", re.MULTILINE)

ADR = sorted(DECISIONES.glob("ADR-*.md"))


def _estado(ruta: Path) -> str:
    encontrado = LINEA_ESTADO.search(ruta.read_text(encoding="utf-8"))
    assert encontrado, f"{ruta.name} no declara ninguna línea `- Estado:`"
    return encontrado.group(1).strip()


def test_hay_adr_que_comprobar() -> None:
    """Una prueba que no recorre nada pasa siempre y no fija nada."""
    assert len(ADR) > 100, f"solo {len(ADR)} ADR; el registro no puede haber encogido así"


@pytest.mark.parametrize("ruta", ADR, ids=lambda p: p.name[:11])
def test_ningun_adr_sigue_diciendo_propuesto(ruta: Path) -> None:
    estado = _estado(ruta)
    assert not estado.upper().startswith("PROPUESTO"), (
        f"{ruta.name} dice `{estado}` y su propia línea de aprobación dice que lo "
        "aprueba la fusión de su PR. Si está en el árbol, la fusión ocurrió "
        "(ADR-209)."
    )


@pytest.mark.parametrize("ruta", ADR, ids=lambda p: p.name[:11])
def test_el_estado_es_uno_de_los_tres(ruta: Path) -> None:
    estado = _estado(ruta)
    assert any(estado.startswith(e) for e in ESTADOS), (
        f"{ruta.name} declara el estado «{estado}», que no es ninguno de "
        f"{', '.join(ESTADOS)}. Un estado inventado no se puede contar."
    )


def test_la_plantilla_no_ofrece_propuesto() -> None:
    """Si la plantilla lo sigue ofreciendo, el defecto vuelve con el ADR siguiente."""
    texto = PLANTILLA.read_text(encoding="utf-8")
    linea = LINEA_ESTADO.search(texto)
    assert linea, "la plantilla no declara línea de estado"
    assert "PROPUESTO" not in linea.group(1), (
        "la plantilla sigue ofreciendo PROPUESTO como estado de un ADR nuevo, "
        "así que el próximo nacería contradiciendo su línea de aprobación."
    )
