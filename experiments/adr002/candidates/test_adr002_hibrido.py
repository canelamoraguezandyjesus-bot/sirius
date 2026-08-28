"""El motor hibrido: la fusion ordena por acuerdo y **no** inventa ni pierde.

Estas pruebas corren en cualquier maquina porque usan el codificador
determinista. Lo que comprueban no es la calidad semantica —eso se mide con un
modelo real y se publica aparte— sino el **mecanismo**: que fusionar por puesto
hace lo que dice, que el conjunto devuelto es exactamente la union de las dos
vias, y que un elemento en el que las dos coinciden sube por encima de uno que
solo una propone.

La prueba que mas importa es la del limite. Concatenar coloca la senal
semantica siempre al final; si la via lexica llena el cupo del contrato, lo que
la semantica proponga se recorta **antes** de que ninguna puerta lo mire. Ahi,
un acierto semantico y la ausencia total de senal semantica son observablemente
lo mismo. La fusion es lo unico que separa esos dos casos, y aqui se comprueba
sobre datos, no se promete en un docstring.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.candidates import fixtures
from experiments.adr002.candidates.adr002_b import semantica
from experiments.adr002.candidates.adr002_b.candidate_semantico import CandidatoBSemantico
from experiments.adr002.candidates.adr002_b.codificadores import CodificadorDeterminista
from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.contracts import (
    IDENTIDADES_POR_LLAMADA,
    Ambito,
    Candidata,
    Cardinalidad,
    Clase,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
    Modo,
    Peticion,
    Polaridad,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import PuertoSqlite
from experiments.adr002.hibrido import fusion
from experiments.adr002.hibrido.buscador import (
    IDENTIFICADOR,
    LISTA_LEXICA,
    LISTA_SEMANTICA,
    SENAL_TARDIA,
    CandidatoHibrido,
    fusionar,
)

_TIEMPO: Final = "2025-01-15T12:00:00Z"


@pytest.fixture
def canon(tmp_path: Path) -> Path:
    return fixtures.construir(tmp_path / "canon.sqlite3").ruta


@pytest.fixture
def sidecar(tmp_path: Path) -> Path:
    return tmp_path / "semantica.sqlite3"


def _peticion(
    consulta: str = "faro",
    *,
    cardinalidad: Cardinalidad = Cardinalidad.EXHAUSTIVA,
    limite: int = 32,
) -> Peticion:
    return Peticion(
        operation_id="op-hib",
        consulta=consulta,
        proposito="responder_al_usuario",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=True, proyectos=()),
        ventana=VentanaTemporal(tiempo_objetivo=_TIEMPO),
        cardinalidad=cardinalidad,
        limite_objetivo=4,
        limite_duro=limite,
    )


# -- La formula ------------------------------------------------------------


def test_el_acuerdo_gana_a_un_primer_puesto_solitario() -> None:
    """Segundo en las dos listas vence a primero en una y ausente en la otra.

    Es la propiedad por la que se elige ``RRF`` y no «coge la mejor de cada
    una»: dos vias independientes que coinciden son mas evidencia que una sola
    muy segura de si misma.
    """
    orden = fusion.fusionar({"a": ["solo", "acordado"], "b": ["otro", "acordado"]})
    assert next(f.identidad for f in orden) == "acordado"
    acordado = next(f for f in orden if f.identidad == "acordado")
    assert acordado.en_cuantas_listas == 2


def test_una_lista_no_vota_dos_veces_por_lo_mismo() -> None:
    """Un duplicado dentro de una lista aporta una vez, no dos."""
    con_duplicado = fusion.fusionar({"a": ["x", "x", "x"]})
    sin_duplicado = fusion.fusionar({"a": ["x"]})
    assert con_duplicado[0].puntuacion == sin_duplicado[0].puntuacion
    assert con_duplicado[0].en_cuantas_listas == 1


def test_el_orden_es_estable_ante_empate() -> None:
    """Dos elementos con la misma puntuacion salen siempre en el mismo orden."""
    primera = fusion.fusionar({"a": ["zeta"], "b": ["alfa"]})
    segunda = fusion.fusionar({"b": ["alfa"], "a": ["zeta"]})
    assert [f.identidad for f in primera] == [f.identidad for f in segunda] == ["alfa", "zeta"]


def test_k_cero_es_un_error_y_no_una_division_silenciosa() -> None:
    with pytest.raises(ValueError, match="k debe ser positivo"):
        fusion.fusionar({"a": ["x"]}, k=0)


def test_la_explicacion_nombra_puesto_y_via() -> None:
    """``RF-28`` exige explicacion por resultado; aqui es literal."""
    orden = fusion.fusionar({LISTA_LEXICA: ["b", "x"], LISTA_SEMANTICA: ["x"]})
    x = next(f for f in orden if f.identidad == "x")
    assert fusion.explicar(x) == f"2.º por {LISTA_LEXICA} y 1.º por {LISTA_SEMANTICA}"


# -- La fusion de candidatas -----------------------------------------------


def _candidata(item_id: str, texto: str, senal: str, razon: str) -> Candidata:
    item = ItemCanonico(
        id=item_id,
        clase=Clase.MEMORIA,
        project_id=None,
        texto=texto,
        subject_key="sujeto",
        vigente=True,
        disponible=True,
        created_at=_TIEMPO,
    )
    return Candidata(
        item=item,
        etapa=Etapa.E3,
        lectura=LecturaSemantica(
            sujeto="sujeto",
            polaridad=Polaridad.AFIRMATIVA,
            condicion=None,
            tiempo=_TIEMPO,
            medio="prueba",
        ),
        razon=razon,
        senal=senal,
    )


def _lexicas(*ids: str) -> list[Candidata]:
    return [_candidata(i, f"texto {i}", "lexica", "por palabra") for i in ids]


def _semanticas(*ids: str) -> list[Candidata]:
    return [_candidata(i, f"texto {i}", "semantica", "por sentido") for i in ids]


def test_la_fusion_no_inventa_ni_pierde_nada() -> None:
    """El conjunto devuelto es exactamente la union. Quien descarta son las puertas."""
    salida = fusionar(_lexicas("a", "b"), _semanticas("b", "c"))
    assert {c.item.id for c in salida} == {"a", "b", "c"}
    assert len(salida) == 3


def test_el_acuerdo_reescribe_la_razon_para_nombrar_las_dos_vias() -> None:
    salida = fusionar(_lexicas("solo_lexica", "acordada"), _semanticas("acordada"))
    por_id = {c.item.id: c for c in salida}
    assert "las dos vias" in por_id["acordada"].razon
    assert por_id["solo_lexica"].razon == "por palabra"
    assert f"por {LISTA_LEXICA}" in por_id["acordada"].senal
    assert f"por {LISTA_SEMANTICA}" in por_id["acordada"].senal


def test_lo_acordado_sube_por_encima_de_lo_que_solo_propone_una_via() -> None:
    """La reordenacion es el efecto entero de este candidato."""
    # Concatenado, «acordada» iria en tercer lugar: es la ultima lexica.
    lexicas = _lexicas("primera", "segunda", "acordada")
    salida = fusionar(lexicas, _semanticas("acordada"))
    assert next(c.item.id for c in salida) == "acordada"


def test_sin_semantica_la_fusion_conserva_el_orden_lexico() -> None:
    """Con una sola lista, ``RRF`` es la identidad. La fusion no perturba nada."""
    lexicas = _lexicas("a", "b", "c", "d")
    salida = fusionar(lexicas, [])
    assert [c.item.id for c in salida] == ["a", "b", "c", "d"]


def test_concatenar_pierde_la_senal_bajo_el_limite_y_fusionar_no() -> None:
    """La prueba que justifica el candidato entero.

    Con el cupo lleno de candidatas lexicas, la identidad que solo la via
    semantica encuentra queda **fuera** al concatenar y **dentro** al fusionar.
    Ese es exactamente el escenario en el que medir la senal semantica sin
    fusionarla no mide nada.
    """
    lexicas = _lexicas(*[f"lex{n:02d}" for n in range(IDENTIDADES_POR_LLAMADA)])
    solo_semantica = _semanticas("la_que_solo_ve_el_sentido")

    concatenado = [c.item.id for c in [*lexicas, *solo_semantica]][:IDENTIDADES_POR_LLAMADA]
    assert "la_que_solo_ve_el_sentido" not in concatenado

    fusionado = [c.item.id for c in fusionar(lexicas, solo_semantica)][:IDENTIDADES_POR_LLAMADA]
    assert "la_que_solo_ve_el_sentido" in fusionado


# -- El candidato dentro del motor ------------------------------------------


def test_el_candidato_recupera_y_declara_su_senal(canon: Path, sidecar: Path) -> None:
    """Extremo a extremo con el motor comun, sin ningun modelo instalado."""
    codificador = CodificadorDeterminista()
    semantica.construir(canon, sidecar, codificador)
    candidato = CandidatoHibrido(canon, sidecar, codificador)
    try:
        with PuertoSqlite(canon) as puerto:
            resultado = engine.recuperar(_peticion("faro"), puerto, candidato)
    finally:
        candidato.close()
    assert candidato.identificador == IDENTIFICADOR
    assert candidato.senal_tardia_habilitada == SENAL_TARDIA
    assert resultado.resultados


def test_el_indice_no_se_abre_si_no_se_llega_a_e3(canon: Path, sidecar: Path) -> None:
    """Activacion tardia demostrada sobre el contador, no prometida.

    Una consulta que ``E1`` resuelve entera con cardinalidad ``EXACTA`` para el
    motor **antes** de ``E3``: el sidecar no llega a abrirse, y por tanto la
    fusion no impone ningun coste a las consultas que no la necesitan.
    """
    codificador = CodificadorDeterminista()
    semantica.construir(canon, sidecar, codificador)
    candidato = CandidatoHibrido(canon, sidecar, codificador)
    try:
        with PuertoSqlite(canon) as puerto:
            engine.recuperar(
                Peticion(
                    operation_id="op-temprana",
                    consulta="faro-costa",
                    proposito="responder_al_usuario",
                    modo=Modo.M1_ORDINARIO,
                    ambito=Ambito(global_=True, proyectos=()),
                    ventana=VentanaTemporal(tiempo_objetivo=_TIEMPO),
                    cardinalidad=Cardinalidad.EXACTA,
                    limite_objetivo=1,
                    limite_duro=8,
                    objetivos=1,
                ),
                puerto,
                candidato,
            )
        assert candidato.invocaciones_semanticas == 0
        assert candidato.indice_abierto is False
    finally:
        candidato.close()


def test_apagar_la_fusion_devuelve_exactamente_el_comportamiento_anterior(
    canon: Path, sidecar: Path
) -> None:
    """El control: con ``con_fusion=False`` este candidato **es** el anterior.

    Que las dos ramas compartan todo lo demas es lo que permite atribuir
    cualquier diferencia medida a la fusion y no a otra cosa.
    """
    codificador = CodificadorDeterminista()
    semantica.construir(canon, sidecar, codificador)
    consulta = _peticion("faro costa niebla")

    def ids(candidato: CandidatoHibrido | CandidatoBSemantico) -> Sequence[str]:
        try:
            with PuertoSqlite(canon) as puerto:
                salida = engine.recuperar(consulta, puerto, candidato)
                return [r.item.id for r in salida.resultados]
        finally:
            candidato.close()

    sin_fusion = ids(CandidatoHibrido(canon, sidecar, codificador, con_fusion=False))
    anterior = ids(CandidatoBSemantico(canon, sidecar, codificador))
    assert list(sin_fusion) == list(anterior)
