"""``ADR002-D``: que sus dos senales tardias esten **separadas**, y sean falsables.

No comprueban que `D` recupere mejor: comprueban que cumple las **tres
restricciones acumulativas** que la Resolucion de la particion §7 le impone, y
que cada una de sus dos senales se puede falsar por separado.

El doble discriminante es la prueba central. Sobre el mismo fixture y la misma
peticion:

===========  ==========================  ==========================
candidato    objetivo solo relacional    objetivo solo vectorial
===========  ==========================  ==========================
`ADR002-A`   no                          no
`ADR002-B`   no                          si, en ``E3``
`ADR002-C`   si, en ``E3``               no
`ADR002-D`   si, en ``E3``               si, en **``E4``**
===========  ==========================  ==========================

Esa ultima fila es `ADR002-D` y ninguna otra cosa: **las dos senales, en
etapas distintas, en el orden congelado**. Y las tres ablaciones lo cierran
por el otro lado — apagando una senal, `D` colapsa exactamente en su vecino.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.candidates import fixtures_d
from experiments.adr002.candidates.adr002_a.candidate import candidato as candidato_a
from experiments.adr002.candidates.adr002_b import vectores
from experiments.adr002.candidates.adr002_b.candidate import candidato as candidato_b
from experiments.adr002.candidates.adr002_c import relaciones
from experiments.adr002.candidates.adr002_c.candidate import candidato as candidato_c
from experiments.adr002.candidates.adr002_d.candidate import (
    ACTA_DEL_ORDEN,
    DEFINICION_CANONICA,
    IDENTIFICADOR,
    ORDEN_CONGELADO,
    SENAL_DE_LA_ETAPA,
    SENAL_RELACIONAL,
    SENAL_TARDIA,
    SENAL_VECTORIAL,
    CandidatoD,
    OrdenDeSenalesVioladoError,
    candidato,
)
from experiments.adr002.candidates.common import engine, neutrality
from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Cardinalidad,
    Etapa,
    Modo,
    Peticion,
    SenalesDeCandidato,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import PuertoSqlite

RAIZ = Path(__file__).resolve().parents[3]

CONSULTA: Final = "faro"
#: Ruta que no existe a proposito: si alguien abriese el plano o el sidecar
#: fuera de su etapa, reventaria con error tipado en vez de pasar inadvertido.
INEXISTENTE: Final = Path("/no/existe/ninguna/ruta/de/adr002-d.db")


# --------------------------------------------------------------------------
# Fixture y peticiones
# --------------------------------------------------------------------------


@pytest.fixture
def base(tmp_path: Path) -> fixtures_d.FixtureD:
    return fixtures_d.construir_base(tmp_path / "candidato-d.db")


@pytest.fixture
def completa(base: fixtures_d.FixtureD) -> fixtures_d.FixtureD:
    """Base, sidecar vectorial y plano relacional: las dos senales disponibles."""
    fixtures_d.construir_sidecar(base)
    fixtures_d.construir_plano(base)
    return base


def _peticion(
    consulta: str = CONSULTA,
    *,
    cardinalidad: Cardinalidad = Cardinalidad.EXHAUSTIVA,
    limite_objetivo: int = 5,
    limite_duro: int = 50,
    espacios: frozenset[Etapa] | None = None,
    corte: str | None = None,
    global_: bool = False,
) -> Peticion:
    argumentos = {
        "operation_id": "op-d",
        "consulta": consulta,
        "proposito": "comprobacion tecnica de reglas, sin medicion",
        "modo": Modo.M1_ORDINARIO,
        "ambito": Ambito(global_=global_, proyectos=(fixtures_d.PROYECTO_ACTIVO,)),
        "ventana": VentanaTemporal(tiempo_objetivo="2026-07-01T00:00:00", corte_de_registro=corte),
        "cardinalidad": cardinalidad,
        "limite_objetivo": limite_objetivo,
        "limite_duro": limite_duro,
        "objetivos": 1,
    }
    if espacios is not None:
        argumentos["espacios_autorizados"] = espacios
    return Peticion(**argumentos)  # type: ignore[arg-type]


def _recuperar(
    fixture: fixtures_d.FixtureD, cand: object, peticion: Peticion | None = None
) -> engine.Recuperacion:
    with PuertoSqlite(fixture.ruta) as puerto:
        return engine.recuperar(peticion or _peticion(), puerto, cand)  # type: ignore[arg-type]


def _d(fixture: fixtures_d.FixtureD, **ablacion: bool) -> CandidatoD:
    return candidato(fixture.ruta, fixture.sidecar, fixture.plano, **ablacion)


def _claves(fixture: fixtures_d.FixtureD, recuperacion: engine.Recuperacion) -> set[str]:
    conexion = sqlite3.connect(str(fixture.ruta))
    try:
        por_id = {
            f"MEMORIA:{fila[0]}": str(fila[1])
            for fila in conexion.execute("SELECT id, subject_key FROM memories")
        }
    finally:
        conexion.close()
    return {por_id.get(identidad, identidad) for identidad in recuperacion.ids}


def _etapa_de(recuperacion: engine.Recuperacion, identidad: str) -> str | None:
    for resultado in recuperacion.resultados:
        if resultado.item.id == identidad:
            return resultado.etapa_de_origen.value
    return None


# --------------------------------------------------------------------------
# A. Identidad, definicion canonica y aislamiento
# --------------------------------------------------------------------------


def test_d_declara_su_definicion_canonica() -> None:
    assert IDENTIFICADOR == "ADR002-D"
    assert SENAL_TARDIA == "ambas_en_etapas_distintas"
    assert "etapas tardias distintas" in DEFINICION_CANONICA
    assert "orden predefinido" in DEFINICION_CANONICA
    assert "sin coordinacion simultanea" in DEFINICION_CANONICA


def test_d_implementa_el_contrato_de_candidato(completa: fixtures_d.FixtureD) -> None:
    assert isinstance(_d(completa), SenalesDeCandidato)
    assert _d(completa).senal_tardia_habilitada == SENAL_TARDIA


def test_d_no_reimplementa_el_motor_ni_las_puertas() -> None:
    assert neutrality.fallos_de_aislamiento_del_candidato(RAIZ, "adr002_d") == []


def test_la_capa_comun_sigue_sin_nombrar_a_ningun_candidato() -> None:
    assert neutrality.fallos_de_neutralidad(RAIZ) == []


# --------------------------------------------------------------------------
# B. Restriccion 2: el orden esta congelado ANTES, y en un acta anterior
# --------------------------------------------------------------------------


def test_el_orden_congelado_es_el_del_acta() -> None:
    """Dos senales, dos etapas, en el orden que el acta fijo: ``E3`` y ``E4``."""
    assert ORDEN_CONGELADO == (
        (Etapa.E3, SENAL_RELACIONAL),
        (Etapa.E4, SENAL_VECTORIAL),
    )
    assert isinstance(ORDEN_CONGELADO, tuple)
    assert all(isinstance(paso, tuple) for paso in ORDEN_CONGELADO)


def test_el_acta_que_congelo_el_orden_existe_en_el_repositorio() -> None:
    """El orden no lo declara el codigo: lo declara un acta, y el codigo la cita."""
    acta = RAIZ / "docs/architecture" / ACTA_DEL_ORDEN
    assert acta.exists(), f"el acta del orden no esta en el repositorio: {ACTA_DEL_ORDEN}"
    texto = acta.read_text(encoding="utf-8")
    assert "E3" in texto and "E4" in texto
    assert "relacional" in texto and "vectorial" in texto


def test_una_etapa_no_puede_alojar_dos_senales_tardias() -> None:
    """La restriccion 3 es estructural: la tabla se deriva del orden congelado."""
    assert dict(ORDEN_CONGELADO) == SENAL_DE_LA_ETAPA
    assert len(SENAL_DE_LA_ETAPA) == len(ORDEN_CONGELADO)
    etapas = [etapa for etapa, _senal in ORDEN_CONGELADO]
    assert len(etapas) == len(set(etapas))
    senales = [senal for _etapa, senal in ORDEN_CONGELADO]
    assert len(senales) == len(set(senales))


def test_ninguna_senal_tardia_vive_en_una_etapa_temprana() -> None:
    assert Etapa.E0 not in SENAL_DE_LA_ETAPA
    assert Etapa.E1 not in SENAL_DE_LA_ETAPA
    assert Etapa.E2 not in SENAL_DE_LA_ETAPA
    assert Etapa.E5 not in SENAL_DE_LA_ETAPA


# --------------------------------------------------------------------------
# C. El doble discriminante: la razon de ser de D
# --------------------------------------------------------------------------


def test_a_no_alcanza_ninguno_de_los_dos_objetivos(completa: fixtures_d.FixtureD) -> None:
    """Si A llegase a alguno, ese objetivo no discriminaria nada."""
    claves = _claves(completa, _recuperar(completa, candidato_a()))
    assert fixtures_d.OBJETIVO_SOLO_RELACIONAL not in claves
    assert fixtures_d.OBJETIVO_SOLO_VECTORIAL not in claves
    assert fixtures_d.SEMILLA in claves


def test_b_alcanza_solo_el_objetivo_vectorial(completa: fixtures_d.FixtureD) -> None:
    claves = _claves(completa, _recuperar(completa, candidato_b(completa.ruta, completa.sidecar)))
    assert fixtures_d.OBJETIVO_SOLO_VECTORIAL in claves
    assert fixtures_d.OBJETIVO_SOLO_RELACIONAL not in claves


def test_c_alcanza_solo_el_objetivo_relacional(completa: fixtures_d.FixtureD) -> None:
    claves = _claves(completa, _recuperar(completa, candidato_c(completa.plano)))
    assert fixtures_d.OBJETIVO_SOLO_RELACIONAL in claves
    assert fixtures_d.OBJETIVO_SOLO_VECTORIAL not in claves


def test_d_alcanza_los_dos_objetivos_cada_uno_en_su_etapa(
    completa: fixtures_d.FixtureD,
) -> None:
    """La fila que solo `ADR002-D` produce: los dos, y en etapas **distintas**."""
    recuperacion = _recuperar(completa, _d(completa))
    claves = _claves(completa, recuperacion)
    assert fixtures_d.OBJETIVO_SOLO_RELACIONAL in claves
    assert fixtures_d.OBJETIVO_SOLO_VECTORIAL in claves
    assert _etapa_de(recuperacion, completa.identidad(fixtures_d.OBJETIVO_SOLO_RELACIONAL)) == "E3"
    assert _etapa_de(recuperacion, completa.identidad(fixtures_d.OBJETIVO_SOLO_VECTORIAL)) == "E4"


def test_el_orden_observado_es_exactamente_el_congelado(completa: fixtures_d.FixtureD) -> None:
    d = _d(completa)
    _recuperar(completa, d)
    assert d.orden_observado == ORDEN_CONGELADO
    assert d.orden_respetado is True


def test_borrar_la_arista_elimina_el_alcance_relacional(
    completa: fixtures_d.FixtureD, tmp_path: Path
) -> None:
    """Falsacion de la senal relacional: sin la arista, ese alcance desaparece."""
    mutilado = tmp_path / "sin-arista.db"
    shutil.copy(completa.plano, mutilado)
    conexion = sqlite3.connect(str(mutilado))
    try:
        conexion.execute("DELETE FROM relaciones WHERE id = 'REL-D01'")
        conexion.commit()
    finally:
        conexion.close()
    d = candidato(completa.ruta, completa.sidecar, mutilado)
    claves = _claves(completa, _recuperar(completa, d))
    assert fixtures_d.OBJETIVO_SOLO_RELACIONAL not in claves
    # El vectorial sigue: las dos senales son independientes de verdad.
    assert fixtures_d.OBJETIVO_SOLO_VECTORIAL in claves


def test_el_destino_relacional_es_recuperable_por_su_propia_consulta(
    completa: fixtures_d.FixtureD,
) -> None:
    """Control positivo: el objetivo existe y es alcanzable, no es un inalcanzable."""
    claves = _claves(completa, _recuperar(completa, candidato_a(), _peticion("almacen repuestos")))
    assert fixtures_d.OBJETIVO_SOLO_RELACIONAL in claves


# --------------------------------------------------------------------------
# D. Activacion tardia: ninguna senal se adelanta, ninguna se abre de mas
# --------------------------------------------------------------------------


def test_si_e1_satisface_no_se_abre_ninguna_senal_tardia(base: fixtures_d.FixtureD) -> None:
    """Con rutas INEXISTENTES: si alguien las tocara, reventaria con error tipado."""
    d = candidato(base.ruta, INEXISTENTE, INEXISTENTE)
    recuperacion = _recuperar(
        base, d, _peticion(cardinalidad=Cardinalidad.ACOTADA, limite_objetivo=1)
    )
    assert recuperacion.parada.identificador == "S1"
    assert d.invocaciones_relacionales == 0
    assert d.invocaciones_vectoriales == 0
    assert d.plano_abierto is False
    assert d.indice_abierto is False
    assert d.orden_observado == ()


def test_si_e3_satisface_la_senal_vectorial_no_se_abre(completa: fixtures_d.FixtureD) -> None:
    """La restriccion clave del orden: una senal posterior **no se adelanta**.

    El sidecar se pasa INEXISTENTE a proposito: si `E4` llegase a pedirse, la
    apertura fallaria con ``IndiceInexistenteError`` en vez de pasar callada.
    """
    d = candidato(completa.ruta, INEXISTENTE, completa.plano)
    recuperacion = _recuperar(
        completa, d, _peticion(cardinalidad=Cardinalidad.ACOTADA, limite_objetivo=4)
    )
    assert recuperacion.parada.identificador == "S1"
    assert d.invocaciones_relacionales == 1
    assert d.invocaciones_vectoriales == 0
    assert d.plano_abierto is True
    assert d.indice_abierto is False
    assert d.orden_observado == ((Etapa.E3, SENAL_RELACIONAL),)
    assert d.orden_respetado is True
    d.cerrar()


def test_si_persiste_la_insuficiencia_la_segunda_senal_actua_en_su_etapa(
    completa: fixtures_d.FixtureD,
) -> None:
    d = _d(completa)
    recuperacion = _recuperar(completa, d)
    assert d.invocaciones_relacionales == 1
    assert d.invocaciones_vectoriales == 1
    assert recuperacion.traza.pasos[-1].etapa is Etapa.E5
    etapas_ejecutadas = [paso.etapa for paso in recuperacion.traza.pasos]
    assert etapas_ejecutadas.index(Etapa.E3) < etapas_ejecutadas.index(Etapa.E4)
    d.cerrar()


def test_un_modo_que_no_autoriza_e4_deja_la_senal_vectorial_sin_ejecutar(
    completa: fixtures_d.FixtureD,
) -> None:
    """El motor posee el bucle: si `E4` no esta autorizada, `D` no la fuerza."""
    d = candidato(completa.ruta, INEXISTENTE, completa.plano)
    recuperacion = _recuperar(
        completa,
        d,
        _peticion(espacios=frozenset({Etapa.E1, Etapa.E2, Etapa.E3})),
    )
    assert recuperacion.parada.identificador == "S2"
    assert d.invocaciones_vectoriales == 0
    assert d.indice_abierto is False
    d.cerrar()


def test_el_plano_se_abre_una_sola_vez_y_consulta_dirigido(
    completa: fixtures_d.FixtureD,
) -> None:
    d = _d(completa)
    _recuperar(completa, d)
    registro = d.registro_relacional
    assert registro is not None
    assert [operacion for operacion, _p, _f in registro.consultas] == ["salientes"]
    _identificador, parametros, _filas = registro.consultas[0]
    assert parametros, "la consulta relacional debe ir acotada por semillas concretas"
    assert len(parametros) <= relaciones.SEMILLAS_MAXIMAS
    d.cerrar()


def test_el_indice_vectorial_se_abre_una_sola_vez_y_solo_en_e4(
    completa: fixtures_d.FixtureD,
) -> None:
    d = _d(completa)
    _recuperar(completa, d)
    registro = d.registro_vectorial
    assert registro is not None
    assert len(registro.consultas) == 1
    assert d.orden_observado[-1] == (Etapa.E4, SENAL_VECTORIAL)
    d.cerrar()


# --------------------------------------------------------------------------
# E. Restriccion 3: nunca coordinacion simultanea
# --------------------------------------------------------------------------


def test_las_dos_senales_nunca_aportan_en_la_misma_etapa(
    completa: fixtures_d.FixtureD,
) -> None:
    """Sobre la explicacion, que es la evidencia publicable de que senal aporto."""
    recuperacion = _recuperar(completa, _d(completa))
    senal_por_etapa: dict[str, set[str]] = {}
    for resultado in recuperacion.resultados:
        coincidencia = resultado.explicacion.coincidencia
        for senal in (SENAL_RELACIONAL, SENAL_VECTORIAL):
            if senal in coincidencia:
                senal_por_etapa.setdefault(resultado.etapa_de_origen.value, set()).add(senal)
    assert senal_por_etapa == {"E3": {SENAL_RELACIONAL}, "E4": {SENAL_VECTORIAL}}


def test_pedir_una_senal_fuera_de_su_etapa_falla_cerrado(
    completa: fixtures_d.FixtureD,
) -> None:
    d = _d(completa)
    with PuertoSqlite(completa.ruta) as puerto:
        contexto = _contexto(puerto, Etapa.E3)
        with pytest.raises(OrdenDeSenalesVioladoError, match="fuera de su etapa congelada"):
            d._tardias(SENAL_VECTORIAL, contexto, frozenset())


def test_dos_senales_activas_a_la_vez_fallan_cerrado(completa: fixtures_d.FixtureD) -> None:
    """El guardia de reentrada: si una senal corriese dentro de otra, aborta."""
    d = _d(completa)
    d._senal_en_curso = SENAL_RELACIONAL
    with PuertoSqlite(completa.ruta) as puerto:
        contexto = _contexto(puerto, Etapa.E4)
        with pytest.raises(OrdenDeSenalesVioladoError, match="coordinacion simultanea"):
            d._tardias(SENAL_VECTORIAL, contexto, frozenset())


def test_invertir_el_orden_en_ejecucion_falla_cerrado(completa: fixtures_d.FixtureD) -> None:
    """Si `E4` se hubiese ejecutado antes que `E3`, el invariante lo detecta."""
    d = _d(completa)
    d._orden_observado = [(Etapa.E4, SENAL_VECTORIAL)]
    assert d.orden_respetado is True  # una sola senal sigue siendo subsecuencia
    d._orden_observado = [(Etapa.E4, SENAL_VECTORIAL), (Etapa.E3, SENAL_RELACIONAL)]
    assert d.orden_respetado is False


def test_una_senal_repetida_en_la_misma_ejecucion_rompe_el_invariante(
    completa: fixtures_d.FixtureD,
) -> None:
    d = _d(completa)
    d._orden_observado = [(Etapa.E3, SENAL_RELACIONAL), (Etapa.E3, SENAL_RELACIONAL)]
    assert d.orden_respetado is False


def test_lo_aportado_por_las_dos_senales_no_se_duplica(completa: fixtures_d.FixtureD) -> None:
    recuperacion = _recuperar(completa, _d(completa))
    assert len(recuperacion.ids) == len(set(recuperacion.ids))


# --------------------------------------------------------------------------
# F. Las dos senales pasan por las MISMAS puertas comunes
# --------------------------------------------------------------------------


def test_el_ambito_corta_lo_alcanzado_por_arista(completa: fixtures_d.FixtureD) -> None:
    """``archivo-forastero`` es destino de una arista y esta fuera de ambito."""
    claves = _claves(completa, _recuperar(completa, _d(completa)))
    assert "archivo-forastero" not in claves


def test_el_ambito_corta_lo_alcanzado_por_similitud(completa: fixtures_d.FixtureD) -> None:
    claves = _claves(completa, _recuperar(completa, _d(completa)))
    assert "baliza-forastera" not in claves


def test_la_polaridad_se_conserva_en_los_dos_canales(completa: fixtures_d.FixtureD) -> None:
    """Ni la arista ni la similitud voltean una negacion (``B04-RF-19``)."""
    recuperacion = _recuperar(completa, _d(completa))
    negativos = {
        completa.identidad("taller-clausurado"): "E3",
        completa.identidad("baliza-averiada"): "E4",
    }
    for identidad, etapa in negativos.items():
        assert _etapa_de(recuperacion, identidad) == etapa
    for resultado in recuperacion.resultados:
        if resultado.item.id in negativos:
            assert resultado.lectura.polaridad.value == "NEGATIVA"


def test_lo_no_vigente_no_entra_por_ninguno_de_los_dos_canales(
    completa: fixtures_d.FixtureD,
) -> None:
    claves = _claves(completa, _recuperar(completa, _d(completa)))
    assert "bodega-retirada" not in claves
    assert "baliza-retirada" not in claves


def test_el_corte_temporal_corta_lo_alcanzado_por_arista(
    completa: fixtures_d.FixtureD,
) -> None:
    sin_corte = _claves(completa, _recuperar(completa, _d(completa)))
    assert "cantera-posterior" in sin_corte
    con_corte = _claves(
        completa, _recuperar(completa, _d(completa), _peticion(corte="2026-07-01T00:00:00"))
    )
    assert "cantera-posterior" not in con_corte


def test_el_corte_temporal_corta_lo_alcanzado_por_similitud(
    completa: fixtures_d.FixtureD,
) -> None:
    con_corte = _claves(
        completa, _recuperar(completa, _d(completa), _peticion(corte="2026-07-01T00:00:00"))
    )
    assert "baliza-futura" not in con_corte


def test_los_dos_tipos_que_otra_regla_adjudica_no_expanden(
    completa: fixtures_d.FixtureD,
) -> None:
    """``SUSTITUYE_A`` la adjudica ``G7`` y ``CONFLICTO_CON`` la parada ``S6``."""
    d = _d(completa)
    claves = _claves(completa, _recuperar(completa, d))
    assert "sala-sustituida" not in claves
    assert "sala-conflictiva" not in claves
    registro = d.registro_relacional
    assert registro is not None
    assert {tipo for _id, tipo, _motivo in registro.descartadas_por_tipo} == set(
        relaciones.TIPOS_NO_EXPANDEN
    )
    d.cerrar()


def test_la_direccion_de_la_arista_se_respeta(completa: fixtures_d.FixtureD) -> None:
    """``patio-remoto`` apunta A la semilla; seguir salientes no lo alcanza."""
    claves = _claves(completa, _recuperar(completa, _d(completa)))
    assert "patio-remoto" not in claves


def test_un_extremo_sin_identidad_canonica_se_declara_en_vez_de_romper(
    completa: fixtures_d.FixtureD,
) -> None:
    """Un documento es extremo legitimo de una relacion y no un elemento del canon."""
    d = _d(completa)
    _recuperar(completa, d)
    registro = d.registro_relacional
    assert registro is not None
    assert [identificador for identificador, _destino in registro.no_materializables] == ["REL-D09"]
    d.cerrar()


def test_un_solo_salto(completa: fixtures_d.FixtureD, tmp_path: Path) -> None:
    """Encadenar una segunda arista desde el destino no alcanza al nieto."""
    assert relaciones.SALTOS == 1
    encadenado = tmp_path / "dos-saltos.db"
    fixtures_d.construir_plano(completa, destino=encadenado)
    conexion = sqlite3.connect(str(encadenado))
    try:
        conexion.execute(
            "INSERT INTO relaciones (id, tipo, origen, destino, origen_canonico, "
            "destino_canonico) VALUES ('REL-D10', 'APOYA', ?, ?, ?, ?)",
            (
                fixtures_d.OBJETIVO_SOLO_RELACIONAL,
                "patio-remoto",
                completa.identidad(fixtures_d.OBJETIVO_SOLO_RELACIONAL),
                completa.identidad("patio-remoto"),
            ),
        )
        conexion.commit()
    finally:
        conexion.close()
    claves = _claves(
        completa, _recuperar(completa, candidato(completa.ruta, completa.sidecar, encadenado))
    )
    assert fixtures_d.OBJETIVO_SOLO_RELACIONAL in claves
    assert "patio-remoto" not in claves


# --------------------------------------------------------------------------
# G. Ablaciones: cada senal contribuye, y se puede apagar sin mover nada
# --------------------------------------------------------------------------


def test_sin_la_senal_relacional_d_entrega_lo_mismo_que_b(
    completa: fixtures_d.FixtureD,
) -> None:
    d = _d(completa, con_senal_relacional=False)
    de_d = set(_recuperar(completa, d).ids)
    de_b = set(_recuperar(completa, candidato_b(completa.ruta, completa.sidecar)).ids)
    assert de_d == de_b
    assert d.plano_abierto is False
    assert d.orden_observado == ((Etapa.E4, SENAL_VECTORIAL),)
    assert d.orden_respetado is True, "apagar una senal no reordena las demas"
    d.cerrar()


def test_sin_la_senal_vectorial_d_entrega_lo_mismo_que_c(
    completa: fixtures_d.FixtureD,
) -> None:
    d = _d(completa, con_senal_vectorial=False)
    de_d = set(_recuperar(completa, d).ids)
    de_c = set(_recuperar(completa, candidato_c(completa.plano)).ids)
    assert de_d == de_c
    assert d.indice_abierto is False
    assert d.orden_observado == ((Etapa.E3, SENAL_RELACIONAL),)
    d.cerrar()


def test_sin_ninguna_senal_tardia_d_entrega_lo_mismo_que_a(
    completa: fixtures_d.FixtureD,
) -> None:
    d = _d(completa, con_senal_relacional=False, con_senal_vectorial=False)
    de_d = set(_recuperar(completa, d).ids)
    de_a = set(_recuperar(completa, candidato_a()).ids)
    assert de_d == de_a
    assert d.orden_observado == ()
    assert d.plano_abierto is False
    assert d.indice_abierto is False


def test_la_ablacion_no_cambia_la_etapa_de_la_senal_que_queda(
    completa: fixtures_d.FixtureD,
) -> None:
    """Apagar una senal **no mueve** la otra: el orden no es configurable."""
    d = _d(completa, con_senal_relacional=False)
    recuperacion = _recuperar(completa, d)
    identidad = completa.identidad(fixtures_d.OBJETIVO_SOLO_VECTORIAL)
    assert _etapa_de(recuperacion, identidad) == "E4"
    d.cerrar()


def test_la_misma_senal_vectorial_rankea_despues_en_d_que_en_b(
    completa: fixtures_d.FixtureD,
) -> None:
    """Consecuencia declarada del orden congelado, comprobada y no escondida."""
    identidad = completa.identidad(fixtures_d.OBJETIVO_SOLO_VECTORIAL)
    en_b = _recuperar(completa, candidato_b(completa.ruta, completa.sidecar))
    en_d = _recuperar(completa, _d(completa))
    assert _etapa_de(en_b, identidad) == "E3"
    assert _etapa_de(en_d, identidad) == "E4"
    assert en_b.ids.index(identidad) < en_d.ids.index(identidad)


# --------------------------------------------------------------------------
# H. Corrupcion y fallo seguro, en los dos canales
# --------------------------------------------------------------------------


def test_un_plano_relacional_ausente_falla_cerrado(base: fixtures_d.FixtureD) -> None:
    """Sin relaciones, esta mitad de `D` no existe: no se degrada en silencio."""
    fixtures_d.construir_sidecar(base)
    d = candidato(base.ruta, base.sidecar, INEXISTENTE)
    with pytest.raises(relaciones.PlanoRelacionalAusenteError):
        _recuperar(base, d)


def test_un_sidecar_vectorial_ausente_falla_cerrado(completa: fixtures_d.FixtureD) -> None:
    d = candidato(completa.ruta, INEXISTENTE, completa.plano)
    with pytest.raises(vectores.IndiceInexistenteError):
        _recuperar(completa, d)
    d.cerrar()


@pytest.mark.parametrize(
    ("sentencia", "parametros"),
    [
        ("UPDATE relaciones SET tipo = 'INVENTADO' WHERE id = 'REL-D01'", ()),
        ("UPDATE relaciones SET destino = '' WHERE id = 'REL-D01'", ()),
        ("UPDATE relaciones SET origen = destino WHERE id = 'REL-D01'", ()),
    ],
)
def test_un_grafo_invalido_invalida_la_fuente(
    completa: fixtures_d.FixtureD, tmp_path: Path, sentencia: str, parametros: tuple[str, ...]
) -> None:
    corrupto = tmp_path / "grafo-invalido.db"
    shutil.copy(completa.plano, corrupto)
    conexion = sqlite3.connect(str(corrupto))
    try:
        conexion.execute(sentencia, parametros)
        conexion.commit()
    finally:
        conexion.close()
    d = candidato(completa.ruta, completa.sidecar, corrupto)
    with pytest.raises(relaciones.RelacionInvalidaError):
        _recuperar(completa, d)


def test_una_arista_hacia_un_elemento_inexistente_falla_cerrado(
    completa: fixtures_d.FixtureD, tmp_path: Path
) -> None:
    corrupto = tmp_path / "destino-fantasma.db"
    shutil.copy(completa.plano, corrupto)
    conexion = sqlite3.connect(str(corrupto))
    try:
        conexion.execute(
            "UPDATE relaciones SET destino_canonico = 'MEMORIA:99999' WHERE id = 'REL-D01'"
        )
        conexion.commit()
    finally:
        conexion.close()
    d = candidato(completa.ruta, completa.sidecar, corrupto)
    with pytest.raises(relaciones.RelacionInconsistenteError):
        _recuperar(completa, d)


def test_una_identidad_no_canonica_en_el_grafo_falla_cerrado(
    completa: fixtures_d.FixtureD, tmp_path: Path
) -> None:
    corrupto = tmp_path / "identidad-invalida.db"
    shutil.copy(completa.plano, corrupto)
    conexion = sqlite3.connect(str(corrupto))
    try:
        conexion.execute(
            "UPDATE relaciones SET destino_canonico = 'MEMORIA:no-es-un-numero' "
            "WHERE id = 'REL-D01'"
        )
        conexion.commit()
    finally:
        conexion.close()
    d = candidato(completa.ruta, completa.sidecar, corrupto)
    with pytest.raises(relaciones.RelacionInconsistenteError):
        _recuperar(completa, d)


def test_un_sidecar_corrupto_falla_cerrado(completa: fixtures_d.FixtureD) -> None:
    completa.sidecar.write_bytes(b"esto no es una base de datos")
    d = candidato(completa.ruta, completa.sidecar, completa.plano)
    with pytest.raises(vectores.IndiceNoUtilizableError):
        _recuperar(completa, d)


def test_un_canon_cambiado_desfasa_el_sidecar_y_falla_cerrado(
    completa: fixtures_d.FixtureD,
) -> None:
    conexion = sqlite3.connect(str(completa.ruta))
    try:
        conexion.execute(
            "UPDATE memory_revisions SET content = content || ' anexo' WHERE memory_id = 1"
        )
        conexion.commit()
    finally:
        conexion.close()
    d = candidato(completa.ruta, completa.sidecar, completa.plano)
    with pytest.raises(vectores.IndiceDesfasadoError):
        _recuperar(completa, d)


def test_un_fallo_de_una_senal_no_produce_recuperacion_parcial(
    completa: fixtures_d.FixtureD, tmp_path: Path
) -> None:
    """Lo que importa: el fallo **no** se presenta como ausencia de conocimiento.

    Un `D` cuya senal vectorial esta rota no entrega los resultados de `E3` y
    calla: aborta. Devolver una salida creible con una senal muerta seria
    exactamente el escenario que ``B04-RF-26`` persigue.
    """
    roto = tmp_path / "sidecar-roto.db"
    roto.write_bytes(b"\x00" * 512)
    d = candidato(completa.ruta, roto, completa.plano)
    with pytest.raises(vectores.IndiceNoUtilizableError):
        _recuperar(completa, d)


# --------------------------------------------------------------------------
# I. Oraculo, traza y privacidad
# --------------------------------------------------------------------------


_PROHIBIDO_DEL_ORACULO: Final[tuple[str, ...]] = (
    "esperado",
    "esperados",
    "oraculo",
    "ground_truth",
    "etiqueta",
    "relevantes",
    "nota",
)


@pytest.mark.parametrize("prohibido", _PROHIBIDO_DEL_ORACULO)
def test_d_no_nombra_nada_del_oraculo(prohibido: str) -> None:
    """Sobre el CODIGO, no sobre la prosa: la explicacion honesta no es delito."""
    import re

    for ruta in sorted((RAIZ / "experiments/adr002/candidates/adr002_d").glob("*.py")):
        codigo = neutrality._sin_comentarios(ruta.read_text(encoding="utf-8"))
        assert not re.search(rf"\b{re.escape(prohibido)}\b", codigo), f"{ruta.name}: {prohibido}"


def test_la_traza_no_filtra_el_texto_de_ningun_item(completa: fixtures_d.FixtureD) -> None:
    recuperacion = _recuperar(completa, _d(completa))
    volcado = json.dumps(
        {
            "pasos": [(p.etapa.value, p.causa_de_entrada) for p in recuperacion.traza.pasos],
            "puertas": recuperacion.traza.puertas,
            "explicaciones": [
                (r.explicacion.coincidencia, r.explicacion.procedencias)
                for r in recuperacion.resultados
            ],
        },
        ensure_ascii=False,
    )
    for texto in completa.textos:
        assert texto not in volcado


def test_la_explicacion_identifica_que_senal_aporto_cada_elemento(
    completa: fixtures_d.FixtureD,
) -> None:
    recuperacion = _recuperar(completa, _d(completa))
    por_id = {r.item.id: r.explicacion.coincidencia for r in recuperacion.resultados}
    relacional = por_id[completa.identidad(fixtures_d.OBJETIVO_SOLO_RELACIONAL)]
    vectorial = por_id[completa.identidad(fixtures_d.OBJETIVO_SOLO_VECTORIAL)]
    assert relacional.startswith("E3 por ")
    assert SENAL_RELACIONAL in relacional and "REL-D01" in relacional
    assert vectorial.startswith("E4 por ")
    assert SENAL_VECTORIAL in vectorial


def test_la_traza_permite_reconstruir_la_etapa_real_de_incorporacion(
    completa: fixtures_d.FixtureD,
) -> None:
    recuperacion = _recuperar(completa, _d(completa))
    aportadas_por_etapa = {p.etapa: p.aportadas for p in recuperacion.traza.pasos}
    assert aportadas_por_etapa[Etapa.E3] > 0
    assert aportadas_por_etapa[Etapa.E4] > 0
    for resultado in recuperacion.resultados:
        assert resultado.explicacion.coincidencia.startswith(
            f"{resultado.etapa_de_origen.value} por "
        )


def test_d_es_determinista(completa: fixtures_d.FixtureD) -> None:
    primera = _recuperar(completa, _d(completa))
    segunda = _recuperar(completa, _d(completa))
    assert primera.ids == segunda.ids
    assert [r.posicion for r in primera.resultados] == [r.posicion for r in segunda.resultados]


def test_la_criticidad_no_genera_candidatas(completa: fixtures_d.FixtureD) -> None:
    """El plano comun no llega al candidato: sin canal lateral, nada es critico."""
    recuperacion = _recuperar(completa, _d(completa))
    assert all(resultado.criticidad is None for resultado in recuperacion.resultados)
    assert recuperacion.handoff_a_b05 == {}


def test_el_paquete_de_d_no_abre_red_ni_usa_proveedor() -> None:
    """Sobre el fuente crudo: ninguna de las dos senales sale de la maquina."""
    prohibidos = (
        *neutrality.EFECTOS_PROHIBIDOS,
        *neutrality.IMPORTS_PROHIBIDOS,
        "openai",
        "http",
    )
    for ruta in sorted((RAIZ / "experiments/adr002/candidates/adr002_d").glob("*.py")):
        codigo = ruta.read_text(encoding="utf-8")
        for prohibido in prohibidos:
            assert prohibido not in codigo, f"{ruta.name}: {prohibido}"


_MARCADOR_DEL_CONTROL = "def test_estas_pruebas_no_miden_rendimiento"


def test_estas_pruebas_no_miden_rendimiento() -> None:
    """Medir `ADR002-D` exige una autorizacion de benchmark que no existe."""
    codigo = Path(__file__).read_text(encoding="utf-8")
    cuerpo = codigo.split(_MARCADOR_DEL_CONTROL)[0]
    for prohibido in ("perf_counter", "timeit", "time.time", "p95", "percentil", "latencia"):
        assert prohibido not in cuerpo, prohibido
    assert "performance_corpus" not in cuerpo
    assert "conformance_corpus" not in cuerpo


# --------------------------------------------------------------------------
# Utilidad: construir un contexto de etapa para las pruebas de coordinacion
# --------------------------------------------------------------------------


def _contexto(puerto: PuertoSqlite, etapa: Etapa):
    from experiments.adr002.candidates.common.contracts import ContextoDeEtapa

    return ContextoDeEtapa(_peticion(), puerto, etapa, frozenset(), ())
