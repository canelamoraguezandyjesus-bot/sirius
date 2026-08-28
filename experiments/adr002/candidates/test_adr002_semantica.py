"""El indice semantico: ciclo de vida, fallo cerrado y proveedor desacoplado.

Estas pruebas corren en **cualquier maquina** porque usan el codificador
determinista, que no depende de nada. Lo que comprueban no es la calidad
semantica —eso se mide con un modelo real y se publica aparte—, sino que el
derivado cumple lo que ``ADR-002`` exige de todo derivado: se construye entero
desde el canon, se borra sin residuos, se regenera identico y **falla cerrado**
cuando algo no cuadra.

La prueba que mas importa es la de sustitucion: el mismo indice consultado con
**otro** codificador no se lee. Comparar vectores de modelos distintos no
compara nada, y degradar en silencio ahi seria peor que no tener indice.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.candidates import fixtures
from experiments.adr002.candidates.adr002_a.candidate import CandidatoA
from experiments.adr002.candidates.adr002_b import semantica
from experiments.adr002.candidates.adr002_b.candidate_semantico import (
    IDENTIFICADOR,
    SENAL_TARDIA,
    CandidatoBSemantico,
)
from experiments.adr002.candidates.adr002_b.codificadores import CodificadorDeterminista
from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Cardinalidad,
    Etapa,
    Modo,
    Peticion,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import PuertoSqlite

_TIEMPO: Final = "2025-01-15T12:00:00Z"


class _OtroCodificador(CodificadorDeterminista):
    """Mismo formato, **otra** identidad. Sirve para probar la sustitucion."""

    identificador: Final = "otro-codificador-v1"


@pytest.fixture
def canon(tmp_path: Path) -> Path:
    return fixtures.construir(tmp_path / "canon.sqlite3").ruta


@pytest.fixture
def sidecar(tmp_path: Path) -> Path:
    return tmp_path / "semantica.sqlite3"


def _peticion(consulta: str = "faro", *, limite: int = 32) -> Peticion:
    return Peticion(
        operation_id="op-sem",
        consulta=consulta,
        proposito="responder_al_usuario",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=True, proyectos=()),
        ventana=VentanaTemporal(tiempo_objetivo=_TIEMPO),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=4,
        limite_duro=limite,
    )


# --------------------------------------------------------------------------
# Ciclo de vida del derivado
# --------------------------------------------------------------------------


def test_se_construye_se_borra_sin_residuos_y_se_regenera_identico(
    canon: Path, sidecar: Path
) -> None:
    """La puerta 5 de la ronda, sobre este indice: borrado y regeneracion."""
    codificador = CodificadorDeterminista()
    semantica.construir(canon, sidecar, codificador)
    primero = sidecar.read_bytes()
    assert primero, "el sidecar no puede quedar vacio"

    semantica.borrar(sidecar)
    assert not sidecar.exists()
    assert semantica.residuos(sidecar) == (), "borrar debe llevarse tambien -wal y -shm"

    semantica.construir(canon, sidecar, codificador)
    assert sidecar.read_bytes() == primero, "la regeneracion no es determinista"


def test_no_se_persiste_ni_un_flotante(canon: Path, sidecar: Path) -> None:
    """Determinismo por construccion: enteros en punto fijo, nada mas."""
    import sqlite3

    semantica.construir(canon, sidecar, CodificadorDeterminista())
    conexion = sqlite3.connect(str(sidecar))
    try:
        for vector, norma in conexion.execute(
            "SELECT vector, norma_cuadrada FROM vectores_de_elemento"
        ):
            assert isinstance(norma, int)
            assert "." not in str(vector), "un punto decimal significa flotante persistido"
    finally:
        conexion.close()


# --------------------------------------------------------------------------
# Fallo cerrado: las tres causas, tipadas
# --------------------------------------------------------------------------


def test_sin_indice_no_se_degrada_a_otra_senal(canon: Path, sidecar: Path) -> None:
    with pytest.raises(semantica.IndiceInexistenteError):
        semantica.LectorSemantico(sidecar, canon, CodificadorDeterminista())


def test_otro_codificador_no_puede_leer_el_indice(canon: Path, sidecar: Path) -> None:
    """**La prueba del desacoplamiento.** El modelo viaja en el sidecar.

    Si esta no fallara, un cambio de modelo pasaria inadvertido y las
    similitudes medidas compararian espacios distintos sin que nadie lo supiera.
    """
    semantica.construir(canon, sidecar, CodificadorDeterminista())
    with pytest.raises(semantica.IndiceCorruptoError) as fallo:
        semantica.LectorSemantico(sidecar, canon, _OtroCodificador())
    assert "otro codificador" in str(fallo.value)


def test_si_el_canon_cambia_el_indice_queda_desfasado(canon: Path, sidecar: Path) -> None:
    semantica.construir(canon, sidecar, CodificadorDeterminista())
    fixtures.anadir_memoria(canon, "faro-nuevo", "el faro nuevo se enciende al anochecer")
    with pytest.raises(semantica.IndiceDesfasadoError):
        semantica.LectorSemantico(sidecar, canon, CodificadorDeterminista())


def test_un_codificador_que_miente_en_sus_dimensiones_no_construye(
    canon: Path, sidecar: Path
) -> None:
    """Falla al construir, no al consultar: un indice torcido no llega a existir."""

    class _Mentiroso(CodificadorDeterminista):
        dimensiones: Final = 999

        def codificar(self, textos: Sequence[str]) -> tuple[tuple[int, ...], ...]:
            return tuple((1, 2, 3) for _ in textos)

    with pytest.raises(semantica.IndiceCorruptoError):
        semantica.construir(canon, sidecar, _Mentiroso())


# --------------------------------------------------------------------------
# El candidato: senal tardia de verdad, y nada mas que la senal
# --------------------------------------------------------------------------


def test_el_indice_no_se_abre_si_las_etapas_tempranas_bastan(canon: Path, sidecar: Path) -> None:
    """Activacion tardia **demostrada**, no prometida: sobre el contador.

    Ni siquiera hace falta que el sidecar exista: si ``E1``/``E2`` bastan, la
    ruta semantica no se toca, y por eso esta prueba no lo construye.
    """
    candidato = CandidatoBSemantico(canon, sidecar, CodificadorDeterminista())
    with PuertoSqlite(canon) as puerto:
        peticion = Peticion(
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
        )
        engine.recuperar(peticion, puerto, candidato)
    assert candidato.invocaciones_semanticas == 0
    assert candidato.indice_abierto is False


def test_con_la_senal_apagada_es_exactamente_la_base(canon: Path, sidecar: Path) -> None:
    """El control que hace atribuible cualquier diferencia a la senal.

    Sin el, una diferencia medida podria venir del arnes. Con el, si los
    resultados coinciden con los de ``ADR002-A``, lo unico que puede explicar
    una diferencia posterior es la senal semantica.
    """
    semantica.construir(canon, sidecar, CodificadorDeterminista())
    peticion = _peticion()
    with PuertoSqlite(canon) as puerto:
        base = engine.recuperar(peticion, puerto, CandidatoA()).ids
        apagada = engine.recuperar(
            peticion,
            puerto,
            CandidatoBSemantico(
                canon, sidecar, CodificadorDeterminista(), con_senal_semantica=False
            ),
        ).ids
    assert apagada == base


def test_lo_que_propone_la_senal_pasa_por_las_mismas_puertas(canon: Path, sidecar: Path) -> None:
    """La similitud no es identidad ni verdad: selecciona, no admite.

    Con umbral cero el codificador determinista propone cualquier cosa; nada de
    lo entregado puede saltarse ``G4``, de modo que un elemento fuera de ambito
    no aparece por mucho que la senal lo proponga.
    """
    semantica.construir(canon, sidecar, CodificadorDeterminista())
    candidato = CandidatoBSemantico(
        canon, sidecar, CodificadorDeterminista(), k=8, coseno_minimo=-1.0
    )
    peticion = Peticion(
        operation_id="op-ambito",
        consulta="faro",
        proposito="responder_al_usuario",
        modo=Modo.M1_ORDINARIO,
        # Ambito cerrado al proyecto activo: lo ajeno debe caer por G4.
        ambito=Ambito(global_=False, proyectos=("1",)),
        ventana=VentanaTemporal(tiempo_objetivo=_TIEMPO),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=4,
        limite_duro=32,
    )
    with PuertoSqlite(canon) as puerto:
        recuperacion = engine.recuperar(peticion, puerto, candidato)
    for resultado in recuperacion.resultados:
        assert resultado.item.project_id == "1", "la senal no rescata de G4"


def test_la_senal_solo_puede_aportar_en_e3(canon: Path, sidecar: Path) -> None:
    """``E3`` y solo ``E3``: lo tardio es tardio de verdad."""
    semantica.construir(canon, sidecar, CodificadorDeterminista())
    candidato = CandidatoBSemantico(
        canon, sidecar, CodificadorDeterminista(), k=8, coseno_minimo=-1.0
    )
    with PuertoSqlite(canon) as puerto:
        recuperacion = engine.recuperar(_peticion(), puerto, candidato)
    de_la_senal = [
        r for r in recuperacion.resultados if r.explicacion.coincidencia.startswith("E3")
    ]
    assert candidato.invocaciones_semanticas >= 1
    for resultado in de_la_senal:
        assert resultado.etapa_de_origen is Etapa.E3


def test_el_candidato_declara_lo_que_pone_a_prueba() -> None:
    assert IDENTIFICADOR == "ADR002-B-SEM"
    assert SENAL_TARDIA == "semantica_real_externa"


def test_estas_pruebas_no_miden_rendimiento() -> None:
    """Control de la particion: aqui no hay cronometro ni corpus del banco."""
    codigo = Path(__file__).read_text(encoding="utf-8")
    cuerpo = codigo.split("def test_estas_pruebas_no_miden_rendimiento")[0]
    for prohibido in ("perf_counter", "timeit", "p95", "percentil", "latencia"):
        assert prohibido not in cuerpo, prohibido
    assert "conformance_corpus" not in cuerpo
    assert "performance_corpus" not in cuerpo
