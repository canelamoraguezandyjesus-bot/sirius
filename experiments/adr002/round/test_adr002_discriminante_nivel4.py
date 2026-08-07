"""El caso discriminante de nivel 4, y el hueco del arnés que lo perdía.

La ronda ejecutaba `casos["nivel_1"]` y nada más, de modo que las dos corridas
publicadas midieron la aportación de la señal relacional sin ejecutar el único
caso construido para que esa señal importe. Estas pruebas fijan lo que ese caso
dice y, sobre todo, **que se ejecuta**.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from experiments.adr002.round import cases as cs
from experiments.adr002.round import discriminant as dc

RAIZ: Final = Path(__file__).resolve().parents[3]
CASOS: Final = RAIZ / "experiments/adr002/benchmark/cases_v0_5.json"


def _artefacto() -> dict[str, Any]:
    return json.loads((RAIZ / dc.SALIDA).read_text(encoding="utf-8"))


def test_el_banco_tiene_un_caso_discriminante_relacional() -> None:
    """No es una carencia del banco: el banco lo previó y el arnés lo perdía."""
    casos = json.loads(CASOS.read_text(encoding="utf-8"))
    nivel4 = casos["nivel_4"]
    assert len(nivel4) == 1
    assert nivel4[0]["id"] == dc.CASO
    assert nivel4[0]["clase"] == "CASO_DISCRIMINANTE_RELACIONAL"
    assert "falsar la suficiencia" in nivel4[0]["proposito"].lower()


def test_la_ronda_de_nivel_1_no_lo_incluye_y_por_eso_va_aparte() -> None:
    """El recorte que causó el defecto, hecho explícito en vez de implícito."""
    ejecutables = cs.casos_ejecutables(cs.cargar_artefactos())
    assert all(caso.nivel == 1 for caso in ejecutables)
    assert dc.CASO not in {caso.identificador for caso in ejecutables}


def test_solo_los_que_tienen_senal_relacional_alcanzan_el_destino() -> None:
    """La falsación, ejecutada: la expansión léxica sola **no basta**."""
    veredictos = {v["participante"]: v for v in _artefacto()["veredictos"]}
    for con_relacional in ("ADR002-C", "ADR002-D"):
        assert veredictos[con_relacional]["alcanza_por_arista"] is True, con_relacional
        assert veredictos[con_relacional]["etapa_de_aporte"] == "E3", con_relacional
    for sin_relacional in ("ADR002-A", "ADR002-B", "T0-control"):
        assert veredictos[sin_relacional]["alcanza_por_arista"] is False, sin_relacional


def test_la_senal_vectorial_no_suple_a_la_relacional() -> None:
    """Sin un token compartido, la similitud distribucional no llega."""
    veredictos = {v["participante"]: v for v in _artefacto()["veredictos"]}
    assert veredictos["ADR002-B"]["alcanza_el_lexico"] is True
    assert veredictos["ADR002-B"]["alcanza_por_arista"] is False


def test_todos_alcanzan_el_extremo_lexico() -> None:
    """Si alguno no lo alcanzara, el caso no estaría midiendo lo que dice."""
    for v in _artefacto()["veredictos"]:
        assert v["alcanza_el_lexico"] is True, v["participante"]


def test_el_artefacto_declara_el_hueco_que_lo_hizo_necesario() -> None:
    """Callar por qué se publica aparte convertiría el defecto en una nota al pie."""
    documento = _artefacto()
    assert "solo el nivel 1" in documento["por_que_se_publica_aparte"]
    assert "no elige alternativa" in documento["no_elige"]
    assert "calidad comparada entre candidatos" in documento["no_mide"]
