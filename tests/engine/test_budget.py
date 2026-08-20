"""Budget: presupuesto explícito, corte determinista al agotarse (ADR-043)."""

from __future__ import annotations

import pytest

from sirius_engine.domain.budget import Budget, leer_limite_declarado


def test_presupuesto_nuevo_no_esta_agotado() -> None:
    presupuesto = Budget(limite=10.0)
    assert presupuesto.consumido == 0.0
    assert presupuesto.restante == 10.0
    assert presupuesto.agotado is False


def test_consumir_no_muta_el_original() -> None:
    original = Budget(limite=10.0)
    nuevo = original.consumir(3.0)
    assert original.consumido == 0.0
    assert nuevo.consumido == 3.0
    assert nuevo is not original


def test_agotado_exactamente_al_igualar_el_limite() -> None:
    presupuesto = Budget(limite=5.0).consumir(5.0)
    assert presupuesto.agotado is True
    assert presupuesto.restante == 0.0


def test_agotado_al_superar_el_limite() -> None:
    presupuesto = Budget(limite=5.0).consumir(7.0)
    assert presupuesto.agotado is True
    assert presupuesto.restante == -2.0


def test_no_esta_agotado_justo_antes_del_limite() -> None:
    presupuesto = Budget(limite=5.0).consumir(4.99)
    assert presupuesto.agotado is False


@pytest.mark.parametrize("limite", (-1.0, -0.01))
def test_limite_negativo_es_invalido(limite: float) -> None:
    with pytest.raises(ValueError, match="límite"):
        Budget(limite=limite)


def test_coste_negativo_es_invalido() -> None:
    with pytest.raises(ValueError, match="coste"):
        Budget(limite=10.0).consumir(-1.0)


def test_leer_limite_declarado_lee_la_forma_esperada() -> None:
    assert leer_limite_declarado({"presupuesto": {"limite": 12.5}}) == 12.5


@pytest.mark.parametrize(
    "limites",
    (
        {},
        {"presupuesto": {}},
        {"presupuesto": "no es un mapa"},
        {"presupuesto": {"limite": "no es numero"}},
        {"presupuesto": {"limite": True}},
    ),
)
def test_leer_limite_declarado_falla_explicito_si_falta_o_es_invalido(
    limites: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        leer_limite_declarado(limites)
