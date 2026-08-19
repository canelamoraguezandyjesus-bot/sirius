"""Validador de egress fail-closed (arquitectura §6.1 regla 4, incidencia #202: A4-P3)."""

from __future__ import annotations

import pytest

from sirius_engine.domain.context_fragment import Clasificacion, ContextFragment
from sirius_engine.domain.errors import EgressClassificationError
from sirius_engine.egress import validar_egress_fail_closed


def _fragmento(
    clasificacion: Clasificacion | None, procedencia: str = "incidencia:202"
) -> ContextFragment:
    return ContextFragment(contenido="texto", procedencia=procedencia, clasificacion=clasificacion)


def test_fragmento_sin_clasificar_impide_start_incluso_sin_red() -> None:
    """A4-P3: un fragmento sin clasificación exportable impide START."""
    with pytest.raises(EgressClassificationError):
        validar_egress_fail_closed(fragmentos=(_fragmento(None),), red=False)


def test_fragmento_sin_clasificar_impide_start_con_red() -> None:
    with pytest.raises(EgressClassificationError):
        validar_egress_fail_closed(fragmentos=(_fragmento(None),), red=True)


def test_fragmento_privado_con_red_concedida_impide_start() -> None:
    """§6.1 regla 2: todo contexto a un Worker con red externa pasa por ExportSafeBrief."""
    with pytest.raises(EgressClassificationError):
        validar_egress_fail_closed(fragmentos=(_fragmento("privado"),), red=True)


def test_fragmento_exportable_con_red_concedida_pasa() -> None:
    validar_egress_fail_closed(fragmentos=(_fragmento("exportable"),), red=True)


def test_fragmento_privado_sin_red_pasa() -> None:
    """Sin red concedida no hay exportación posible: lo privado no necesita ser exportable."""
    validar_egress_fail_closed(fragmentos=(_fragmento("privado"),), red=False)


def test_sin_fragmentos_no_hay_nada_que_bloquee() -> None:
    validar_egress_fail_closed(fragmentos=(), red=True)


def test_el_primer_fragmento_inseguro_de_varios_bloquea() -> None:
    fragmentos = (
        _fragmento("exportable", procedencia="a"),
        _fragmento("privado", procedencia="b"),
        _fragmento("exportable", procedencia="c"),
    )
    with pytest.raises(EgressClassificationError) as excinfo:
        validar_egress_fail_closed(fragmentos=fragmentos, red=True)
    assert excinfo.value.procedencia == "b"
