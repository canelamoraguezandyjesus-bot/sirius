"""Que ningun critico **recuperado** desaparezca sin declararse, y la cota real.

Dos cosas distintas, las dos aprendidas midiendo:

1. ``RF-24`` prohibe la omision callada de un critico. ``G12`` ya declaraba el
   desbordamiento, pero nadie comprobaba la igualdad: si el orden por criticidad
   se rompiera, un critico caeria por el limite **sin** aparecer en
   ``criticos_omitidos`` y la salida seria plausible. La prueba negativa de aqui
   rompe ``G12`` a proposito y exige que el motor se niegue a entregar.

2. ``IDENTIDADES_POR_LLAMADA`` declara en el **contrato** cuantas identidades
   admite ``por_identificadores``, porque quien pide mas tiene que lotear y para
   lotear necesita saber por cuanto. La cota **rechaza, no trunca**: un lote de
   mas no devuelve menos elementos en silencio, falla. Eso es lo que hizo visible
   que el control de criticos pedia dieciocho identidades de golpe, y por eso la
   constante se fija con una prueba sobre el puerto real en vez de con un numero
   repetido en dos modulos.

Aqui **no se mide nada**: no hay cronometros, ni corpus del banco, ni casos.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from experiments.adr002.candidates import fixtures
from experiments.adr002.candidates.adr002_a import candidate as ca
from experiments.adr002.candidates.common import engine, gates, port
from experiments.adr002.candidates.common.contracts import (
    IDENTIDADES_POR_LLAMADA,
    Ambito,
    Cardinalidad,
    Criticidad,
    CriticidadAplicada,
    Modo,
    Peticion,
    VentanaTemporal,
)

_TIEMPO = "2025-01-15T12:00:00Z"


class _PlanoConUnCritico:
    """Plano comun minimo: una sola identidad critica, el resto ordinario."""

    def __init__(self, critica: str) -> None:
        self._critica = critica

    def property_key(self, identidad: str) -> str | None:
        return None

    def criticidad_aplicada(self, identidad: str) -> CriticidadAplicada | None:
        if identidad != self._critica:
            return None
        return CriticidadAplicada(
            nivel=Criticidad.CRITICA,
            razon_segura="critico para la prueba del invariante",
            fuente_de_politica="prueba",
            regla_de_politica="RF-24",
        )


def _peticion(*, limite_duro: int = 32) -> Peticion:
    return Peticion(
        operation_id="op-rf24",
        consulta="faro",
        proposito="responder_al_usuario",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=True, proyectos=()),
        ventana=VentanaTemporal(tiempo_objetivo=_TIEMPO),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=8,
        limite_duro=limite_duro,
    )


@pytest.fixture
def base(tmp_path: Path) -> Path:
    return fixtures.construir(tmp_path / "canon.sqlite3").ruta


def test_la_cota_del_puerto_es_la_del_contrato_y_rechaza_una_mas(base: Path) -> None:
    """Exactamente ``IDENTIDADES_POR_LLAMADA`` entran; una mas **falla**.

    No se comprueba que las dos constantes sean iguales —eso solo diria que
    alguien copio un numero—: se comprueba el **comportamiento** del puerto
    contra la cota que el contrato publica.
    """
    with port.PuertoSqlite(base) as puerto:
        justos = [f"MEMORIA:{n}" for n in range(1, IDENTIDADES_POR_LLAMADA + 1)]
        assert puerto.por_identificadores(justos).pedidos == IDENTIDADES_POR_LLAMADA

        una_mas = [*justos, f"MEMORIA:{IDENTIDADES_POR_LLAMADA + 1}"]
        with pytest.raises(port.IdentificadorInvalidoError) as fallo:
            puerto.por_identificadores(una_mas)
        assert "rechaza, no trunca" in str(fallo.value)


def test_marcar_critico_lo_saca_de_lo_que_el_limite_recortaba(base: Path) -> None:
    """Camino real: el limite recorta por abajo y lo critico sube.

    Control positivo del invariante, y **sin identidades a mano**: se recupera
    una vez sin canal lateral, se toma un elemento que el limite dejo fuera, se
    lo marca critico y se vuelve a recuperar. Fijar la identidad en el codigo
    ataria la prueba al orden de insercion del fixture y no a la regla.
    """
    peticion = _peticion(limite_duro=1)
    with port.PuertoSqlite(base) as puerto:
        sin_canal = engine.recuperar(peticion, puerto, ca.candidato())
        assert sin_canal.omitidos_por_limite, "el fixture debe desbordar para que esto mida algo"
        recortado = sin_canal.omitidos_por_limite[-1]
        assert recortado not in sin_canal.ids

        con_canal = engine.recuperar(
            peticion, puerto, ca.candidato(), _PlanoConUnCritico(recortado)
        )

    assert con_canal.traza.desbordamiento is True, "recortar y no decirlo es RF-24"
    assert con_canal.traza.criticos_omitidos == (), "no cabia solo lo ordinario, no lo critico"
    assert recortado in con_canal.ids, "el critico se preserva antes que lo ordinario"


def test_el_motor_se_niega_a_entregar_si_g12_pierde_un_critico(
    base: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prueba **negativa**: si ``G12`` se rompe, el motor no entrega.

    Se sustituye ``G12`` por una version que tira el critico **sin** declararlo,
    que es exactamente la forma que tendria el defecto si el orden por criticidad
    dejara de funcionar. Sin el invariante esto devolvia una respuesta
    perfectamente plausible a la que le faltaba lo importante.
    """
    with port.PuertoSqlite(base) as puerto:
        # El critico se elige entre lo que el motor SI recupera: romper G12 sobre
        # algo que nunca llega no probaria nada.
        critica = engine.recuperar(_peticion(), puerto, ca.candidato()).ids[0]
    original = gates.aplicar_g12

    def _g12_que_pierde(candidatas, peticion, criticidad_de=None, pertenece_a_grupo=None):  # type: ignore[no-untyped-def]
        veredicto = original(candidatas, peticion, criticidad_de, pertenece_a_grupo)
        return gates.ResultadoG12(
            dentro_del_limite=tuple(c for c in veredicto.dentro_del_limite if c.item.id != critica),
            desbordamiento_declarado=veredicto.desbordamiento_declarado,
            desbordamiento_critico=veredicto.desbordamiento_critico,
            # El defecto es justamente este: se pierde y no se dice.
            criticos_omitidos=(),
            miembros_omitidos=veredicto.miembros_omitidos,
        )

    monkeypatch.setattr(gates, "aplicar_g12", _g12_que_pierde)
    with (
        port.PuertoSqlite(base) as puerto,
        pytest.raises(engine.RecuperacionInvalidaError) as fallo,
    ):
        engine.recuperar(_peticion(), puerto, ca.candidato(), _PlanoConUnCritico(critica))
    assert critica in str(fallo.value)
    assert "sin declarar desbordamiento" in str(fallo.value)


def test_estas_pruebas_no_miden_nada() -> None:
    """Control de la particion: aqui no hay cronometro ni corpus del banco."""
    codigo = Path(__file__).read_text(encoding="utf-8")
    cuerpo = codigo.split("def test_estas_pruebas_no_miden_nada")[0]
    for prohibido in ("perf_counter", "timeit", "time.time", "p95", "percentil", "latencia"):
        assert prohibido not in cuerpo, prohibido
    assert "conformance_corpus" not in cuerpo
    assert "performance_corpus" not in cuerpo
