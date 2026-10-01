"""ADR-229 (deuda 20): los instantes de G8 se comparan en una sola forma.

El repositorio escribe los instantes de dos maneras —el ``str(datetime)`` de
SQLite y el ISO con ``T`` y ``Z`` del corpus— y G8 los comparaba como cadenas:
``"2026-03-20 09:00:00.000000" > "2026-03-20T00:00:00Z"`` es ``False`` porque
el espacio ordena antes que la ``T``, así que lo registrado a las nueve de la
mañana pasaba un corte de medianoche del mismo día. Tres apariciones de la
familia en septiembre (bitácora, entradas 52, 60 y 69). Estas pruebas fijan el
comparador y la frontera exacta con las formas mezcladas; las de G8 con una
sola forma siguen en ``test_staged_engine.py``.
"""

from __future__ import annotations

import pytest

from sirius.domain import staged_engine_gates as gates
from sirius.domain.instantes import FORMA_CANONICA, comparable, en_forma_canonica
from sirius.domain.staged_engine_contracts import (
    Ambito,
    Candidata,
    Cardinalidad,
    Clase,
    EjesDeclarados,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
    Modo,
    Peticion,
    Polaridad,
    VentanaTemporal,
)

LAS_NUEVE_EN_SQLITE = "2026-03-20 09:00:00.000000"
MEDIANOCHE_EN_EL_CORPUS = "2026-03-20T00:00:00Z"


# --- el comparador -------------------------------------------------------------


@pytest.mark.parametrize(
    "escritura",
    [
        "2026-03-20 09:00:00.000000",
        "2026-03-20 09:00:00",
        "2026-03-20T09:00:00Z",
        "2026-03-20T09:00:00+00:00",
        "2026-03-20T11:00:00+02:00",
        "2026-03-20T09:00:00.000000Z",
    ],
)
def test_seis_escrituras_del_mismo_instante_tienen_la_misma_forma_canonica(escritura: str) -> None:
    assert en_forma_canonica(escritura) == "2026-03-20T09:00:00.000000Z"


def test_la_forma_canonica_es_utc_de_ancho_fijo_y_ordena_como_el_reloj() -> None:
    """Ancho fijo: sin él, «09:00:00» y «09:00:00.000001» no ordenarían bien
    frente a otras escrituras. Es la mutación M2."""
    assert FORMA_CANONICA == "%Y-%m-%dT%H:%M:%S.%fZ"
    canonicas = [
        en_forma_canonica(e)
        for e in ("2026-03-20 09:00:00", "2026-03-20T09:00:00.000001Z", "2026-03-20T08:59:59+00:00")
    ]
    assert all(c is not None and len(c) == 27 for c in canonicas)
    assert sorted(canonicas) == [canonicas[2], canonicas[0], canonicas[1]]  # type: ignore[type-var]


def test_una_fecha_sola_es_su_medianoche_en_utc() -> None:
    assert en_forma_canonica("2026-03-20") == "2026-03-20T00:00:00.000000Z"


def test_un_desfase_se_convierte_a_utc_en_vez_de_ignorarse() -> None:
    """M3: ignorar el desfase haría que «las dos de la tarde en Madrid» y «las
    dos de la tarde en UTC» fueran el mismo instante."""
    assert en_forma_canonica("2026-03-20T14:00:00+02:00") == "2026-03-20T12:00:00.000000Z"
    assert en_forma_canonica("2026-03-20T14:00:00-03:00") == "2026-03-20T17:00:00.000000Z"


def test_lo_que_no_es_un_instante_se_compara_tal_cual() -> None:
    assert en_forma_canonica("ayer por la tarde") is None
    assert en_forma_canonica("") is None
    assert comparable("ayer por la tarde") == "ayer por la tarde"
    assert comparable(LAS_NUEVE_EN_SQLITE) == "2026-03-20T09:00:00.000000Z"


# --- G8 en la frontera, con las formas mezcladas ----------------------------------


def _item(
    item_id: str = "DECISION:1",
    *,
    created_at: str = "2026-01-01T00:00:00Z",
    ejes: EjesDeclarados | None = None,
) -> ItemCanonico:
    return ItemCanonico(
        id=item_id,
        clase=Clase.DECISION,
        project_id="1",
        texto="Se aprueba el cambio de proveedor.",
        subject_key="proveedor-embalaje",
        vigente=True,
        disponible=True,
        created_at=created_at,
        ejes=ejes if ejes is not None else EjesDeclarados(),
    )


def _peticion(ventana: VentanaTemporal, *, admite_no_vigentes: bool = False) -> Peticion:
    return Peticion(
        operation_id="test",
        consulta="proveedor de embalaje",
        proposito="prueba",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=True, proyectos=()),
        ventana=ventana,
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=100,
        limite_duro=100,
        admite_no_vigentes=admite_no_vigentes,
    )


def _candidata(item: ItemCanonico) -> Candidata:
    return Candidata(
        item=item,
        etapa=Etapa.E1,
        lectura=LecturaSemantica(
            sujeto=item.subject_key or "proveedor",
            polaridad=Polaridad.AFIRMATIVA,
            condicion=None,
            tiempo=item.created_at,
            medio="prueba",
        ),
        razon="coincidencia de prueba",
        senal="prueba",
    )


def _veredicto_de_g8(item: ItemCanonico, peticion: Peticion) -> str | None:
    """``None`` si G8 admite; el motivo si descarta."""
    filtrado = gates.aplicar_previas([_candidata(item)], peticion)
    motivos = [motivo for _item_id, puerta, motivo in filtrado.descartes if puerta == "G8"]
    assert len(motivos) <= 1
    return motivos[0] if motivos else None


def test_lo_registrado_a_las_nueve_no_pasa_un_corte_de_medianoche_del_mismo_dia() -> None:
    """El caso de la deuda 20, visto fallar contra la G8 anterior: con el
    espacio delante de la `T`, la cadena de SQLite «era anterior» a la
    medianoche escrita por el corpus y el elemento entraba."""
    item = _item(created_at=LAS_NUEVE_EN_SQLITE)
    peticion = _peticion(
        VentanaTemporal(
            tiempo_objetivo="2026-06-15T00:00:00Z", corte_de_registro=MEDIANOCHE_EN_EL_CORPUS
        )
    )
    assert _veredicto_de_g8(item, peticion) == "posterior al corte de registro"


def test_el_corte_sigue_siendo_inclusivo_en_su_instante_exacto_sea_cual_sea_la_escritura() -> None:
    """`created_at > corte` no excluye el instante del corte: con las dos
    escrituras del mismo instante tampoco."""
    item = _item(created_at="2026-03-20 00:00:00")
    peticion = _peticion(
        VentanaTemporal(
            tiempo_objetivo="2026-06-15T00:00:00Z", corte_de_registro="2026-03-20T00:00:00+00:00"
        )
    )
    assert _veredicto_de_g8(item, peticion) is None


def test_un_valid_from_con_mas_cero_cero_y_un_objetivo_con_z_son_el_mismo_instante() -> None:
    """Con las cadenas crudas, `+` ordena antes que `Z` y el veredicto dependía
    de la escritura; en la frontera exacta el elemento está vigente."""
    item = _item(ejes=EjesDeclarados(valid_from="2026-06-15T00:00:00+00:00"))
    peticion = _peticion(VentanaTemporal(tiempo_objetivo="2026-06-15T00:00:00Z"))
    assert _veredicto_de_g8(item, peticion) is None
    todavia_no = _item(ejes=EjesDeclarados(valid_from="2026-06-15T00:00:01+00:00"))
    assert _veredicto_de_g8(todavia_no, peticion) == "aun no vigente en el tiempo objetivo"


def test_un_valid_to_escrito_con_desfase_expira_cuando_su_instante_en_utc_llega() -> None:
    """`2026-06-15T01:00:00+02:00` es la 23:00 UTC del día 14: para un objetivo
    de la medianoche del 15 ya ha expirado, diga lo que diga el orden léxico."""
    item = _item(ejes=EjesDeclarados(valid_to="2026-06-15T01:00:00+02:00"))
    peticion = _peticion(VentanaTemporal(tiempo_objetivo="2026-06-15T00:00:00Z"))
    assert _veredicto_de_g8(item, peticion) == "vigencia expirada en el tiempo objetivo"
    assert _veredicto_de_g8(item, _peticion(peticion.ventana, admite_no_vigentes=True)) is None


def test_con_una_sola_forma_el_veredicto_es_el_de_siempre() -> None:
    """No cambia nada para quien ya escribía las dos cadenas igual: es lo que
    hace que el banco de 47 casos no se mueva."""
    peticion = _peticion(
        VentanaTemporal(
            tiempo_objetivo="2026-06-15T00:00:00Z", corte_de_registro="2026-03-20T00:00:00Z"
        )
    )
    assert _veredicto_de_g8(_item(created_at="2026-03-19T23:59:59Z"), peticion) is None
    assert (
        _veredicto_de_g8(_item(created_at="2026-03-20T00:00:01Z"), peticion)
        == "posterior al corte de registro"
    )
