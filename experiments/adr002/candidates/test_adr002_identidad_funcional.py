"""Pruebas funcionales de la materializacion por identidad canonica exacta.

**Solo despues de las fichas sucesoras.** El paquete de correccion 02 cambio
fuentes de las huellas de `ADR002-A` y `ADR002-B`, y los paquetes 03 y 04
volvieron a cambiar las de B; estas pruebas exigen que los commits de entrada
de `ficha_ADR002-A_v3.json` y `ficha_ADR002-B_v5.json` sean ancestros
estrictos, y quedan suspendidas mientras no lo sean.

Lo que se demuestra, seccion a seccion:

- **El puerto por identificadores**, con elementos reales: memoria y decision
  exactas, mezcla de clases con orden canonico, duplicados de entrada,
  ausentes declarados, registro de consultas dirigidas y ausencia de barrido
  y de filtrado por proyecto o clave.
- **Clave de sujeto vacia**: el sidecar identifica el elemento, el puerto lo
  materializa por id y `ADR002-B` ya no lo pierde.
- **Claves duplicadas**: solo la identidad solicitada se materializa; nada
  entra por compartir clave.
- **Mas de 512 elementos con la misma clave**: el objetivo situado despues de
  las primeras 512 filas se recupera por id; la antigua cota por clave deja
  de ser relevante y el trabajo depende del top-K, no del numero de filas que
  comparten la clave.
- **Identidad inconsistente**: un id sintacticamente valido que el canon no
  contiene produce `IndiceInconsistenteError`, cerrado y tipado, sin
  `Recuperacion` parcial y sin contenido protegido en el mensaje.

Lo que estas pruebas **no** hacen: no miden rendimiento, no usan el corpus
oficial ni casos oficiales, y no producen ningun artefacto de benchmark.
"""

from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.candidates import fixtures_b
from experiments.adr002.candidates.adr002_b import vectores
from experiments.adr002.candidates.adr002_b.candidate import candidato
from experiments.adr002.candidates.common import engine
from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Cardinalidad,
    Etapa,
    Modo,
    Peticion,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import PuertoSqlite, fallos_de_barrido

RAIZ = Path(__file__).resolve().parents[3]
FICHAS_SUCESORAS: Final = (
    "artifacts/adr002_cards/ficha_ADR002-A_v3.json",
    "artifacts/adr002_cards/ficha_ADR002-B_v5.json",
)

CONSULTA: Final = "faro"


def _git(*argumentos: str) -> str:
    return subprocess.run(
        ["git", *argumentos], cwd=str(RAIZ), capture_output=True, text=True, check=False
    ).stdout.strip()


def _es_ancestro_estricto(ruta: str) -> bool:
    entrada = _git("log", "--format=%H", "--diff-filter=A", "--", ruta)
    if not entrada:
        return False
    commit_de_entrada = entrada.splitlines()[-1]
    if commit_de_entrada == _git("rev-parse", "HEAD"):
        return False
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit_de_entrada, "HEAD"],
            cwd=str(RAIZ),
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


pytestmark = pytest.mark.skipif(
    not all(_es_ancestro_estricto(ficha) for ficha in FICHAS_SUCESORAS),
    reason=(
        "las fichas ADR002-A v3 y ADR002-B v5 aun no son ancestros estrictos: "
        "ejecutar ahora produciria evidencia no utilizable (TOL-210, regla 3)"
    ),
)


@pytest.fixture
def base(tmp_path: Path) -> fixtures_b.FixtureB:
    return fixtures_b.construir_base(tmp_path / "identidad.db")


def _peticion(consulta: str) -> Peticion:
    return Peticion(
        operation_id="op-identidad",
        consulta=consulta,
        proposito="comprobacion tecnica de reglas, sin medicion",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=False, proyectos=(fixtures_b.PROYECTO_ACTIVO,)),
        ventana=VentanaTemporal(tiempo_objetivo="2026-07-01T00:00:00"),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=5,
        limite_duro=50,
        objetivos=1,
    )


# --------------------------------------------------------------------------
# A. El puerto por identificadores, con elementos reales
# --------------------------------------------------------------------------


def test_memoria_y_decision_exactas(base: fixtures_b.FixtureB) -> None:
    with PuertoSqlite(base.ruta) as puerto:
        memoria = puerto.por_identificadores(("MEMORIA:1",))
        decision = puerto.por_identificadores(("DECISION:1",))
    assert [item.id for item in memoria.items] == ["MEMORIA:1"]
    assert memoria.items[0].subject_key == "faro-costa"
    assert memoria.ausentes == () and memoria.completa
    assert [item.id for item in decision.items] == ["DECISION:1"]
    assert decision.items[0].subject_key == "luces-mantenimiento"


def test_mezcla_de_clases_con_orden_canonico(base: fixtures_b.FixtureB) -> None:
    """Orden por (clase, numero), NUMERICO: 2 antes que 10, DECISION antes."""
    with PuertoSqlite(base.ruta) as puerto:
        resultado = puerto.por_identificadores(
            ("MEMORIA:10", "MEMORIA:2", "DECISION:1", "MEMORIA:1")
        )
    assert resultado.solicitados == ("DECISION:1", "MEMORIA:1", "MEMORIA:2", "MEMORIA:10")
    assert [item.id for item in resultado.items] == list(resultado.solicitados)
    assert resultado.pedidos == 4 and resultado.ausentes == ()


def test_los_duplicados_de_entrada_se_deduplican(base: fixtures_b.FixtureB) -> None:
    with PuertoSqlite(base.ruta) as puerto:
        resultado = puerto.por_identificadores(("MEMORIA:1", "MEMORIA:1", "MEMORIA:1"))
    assert resultado.pedidos == 3
    assert resultado.solicitados == ("MEMORIA:1",)
    assert [item.id for item in resultado.items] == ["MEMORIA:1"]


def test_lo_ausente_se_declara_sin_confundirse_con_lo_invalido(
    base: fixtures_b.FixtureB,
) -> None:
    with PuertoSqlite(base.ruta) as puerto:
        resultado = puerto.por_identificadores(("MEMORIA:1", "MEMORIA:9999", "DECISION:77"))
    assert [item.id for item in resultado.items] == ["MEMORIA:1"]
    assert resultado.ausentes == ("DECISION:77", "MEMORIA:9999")
    assert resultado.completa is False


def test_la_cota_exacta_de_dieciseis_unicos_se_admite(base: fixtures_b.FixtureB) -> None:
    identificadores = tuple(f"MEMORIA:{n}" for n in range(1, 17))
    with PuertoSqlite(base.ruta) as puerto:
        resultado = puerto.por_identificadores(identificadores)
    assert len(resultado.solicitados) == 16
    assert set(resultado.ausentes) | {i.id for i in resultado.items} == set(identificadores)


def test_el_registro_anota_consultas_dirigidas_sin_barrido(
    base: fixtures_b.FixtureB,
) -> None:
    with PuertoSqlite(base.ruta) as puerto:
        puerto.por_identificadores(("MEMORIA:1", "DECISION:1", "MEMORIA:9999"))
        operaciones = [consulta.operacion for consulta in puerto.registro.consultas]
        assert operaciones == ["por_identidad:MEMORIA", "por_identidad:DECISION"]
        for consulta in puerto.registro.consultas:
            assert consulta.dirigida
            assert consulta.filas <= consulta.cota
            assert " ID IN " in f" {consulta.sql.upper()} ".replace("M.ID", "ID").replace(
                "D.ID", "ID"
            )
        assert fallos_de_barrido(puerto.registro, universo=12) == []


def test_no_filtra_por_proyecto_ni_por_clave(base: fixtures_b.FixtureB) -> None:
    """La identidad materializa; el ambito filtra DESPUES, en G4.

    ``MEMORIA:7`` es del proyecto ajeno y ``MEMORIA:8`` esta archivada: ambas
    existen, ambas vuelven por id, y decidir su admisibilidad es trabajo de
    las puertas del motor, no del puerto.
    """
    with PuertoSqlite(base.ruta) as puerto:
        resultado = puerto.por_identificadores(("MEMORIA:7", "MEMORIA:8"))
        assert [item.id for item in resultado.items] == ["MEMORIA:7", "MEMORIA:8"]
        assert resultado.items[0].project_id != fixtures_b.PROYECTO_ACTIVO
        assert resultado.items[1].vigente is False
        for consulta in puerto.registro.consultas:
            assert "project_id = ?" not in consulta.sql
            assert "subject_key = ?" not in consulta.sql


# --------------------------------------------------------------------------
# B. Clave de sujeto vacia: la coincidencia ya no se pierde
# --------------------------------------------------------------------------


def test_una_clave_vacia_no_pierde_la_coincidencia(base: fixtures_b.FixtureB) -> None:
    memoria_sin_clave = fixtures_b.anadir_memoria(
        base.ruta, None, "la baliza anonima descansa junto al varadero"
    )
    identidad = f"MEMORIA:{memoria_sin_clave}"
    fixtures_b.construir_sidecar(base)

    b = candidato(base.ruta, base.sidecar)
    with PuertoSqlite(base.ruta) as puerto:
        recuperacion = engine.recuperar(_peticion(CONSULTA), puerto, b)
        materializaciones = [
            consulta
            for consulta in puerto.registro.consultas
            if consulta.operacion.startswith("por_identidad")
        ]
    por_id = {r.item.id: r for r in recuperacion.resultados}
    assert identidad in por_id, "la clave vacia volvio a perder la coincidencia"
    resultado = por_id[identidad]
    assert resultado.item.subject_key == ""
    assert resultado.etapa_de_origen is Etapa.E3
    assert "semantica_vectorial" in resultado.explicacion.coincidencia
    assert resultado.lectura.sujeto == "baliza"
    assert materializaciones, "la materializacion vectorial debe pasar por identidad"
    assert any(str(memoria_sin_clave) in consulta.parametros for consulta in materializaciones)
    from experiments.adr002.candidates.common import trace

    assert trace.fallos_de_minimizacion(recuperacion.traza.como_dict(), base.textos) == []


# --------------------------------------------------------------------------
# C. Claves duplicadas: la identidad no se sustituye
# --------------------------------------------------------------------------


def test_una_clave_duplicada_no_cambia_la_identidad(base: fixtures_b.FixtureB) -> None:
    objetivo = fixtures_b.anadir_memoria(
        base.ruta, "puesto-gemelo", "la baliza gemela flota junto al panton"
    )
    gemela = fixtures_b.anadir_memoria(
        base.ruta, "puesto-gemelo", "la torre gemela guarda el astillero viejo"
    )
    fixtures_b.construir_sidecar(base)

    b = candidato(base.ruta, base.sidecar)
    with PuertoSqlite(base.ruta) as puerto:
        recuperacion = engine.recuperar(_peticion(CONSULTA), puerto, b)
        pedidos_por_identidad = {
            parametro
            for consulta in puerto.registro.consultas
            if consulta.operacion.startswith("por_identidad")
            for parametro in consulta.parametros
        }
    ids = {r.item.id for r in recuperacion.resultados}
    assert f"MEMORIA:{objetivo}" in ids, "el sidecar identifico este elemento concreto"
    assert f"MEMORIA:{gemela}" not in ids, "compartir clave no puede colar a la gemela"
    assert str(objetivo) in pedidos_por_identidad
    assert str(gemela) not in pedidos_por_identidad
    resultado = next(r for r in recuperacion.resultados if r.item.id == f"MEMORIA:{objetivo}")
    assert resultado.item.subject_key == "puesto-gemelo"
    assert "MEMORIA del canon" in resultado.explicacion.procedencia


# --------------------------------------------------------------------------
# D. Mas de 512 elementos con la misma clave: la cota por clave es irrelevante
# --------------------------------------------------------------------------


def test_el_objetivo_tras_512_filas_de_la_misma_clave_se_recupera(
    base: fixtures_b.FixtureB,
) -> None:
    relleno = [f"material de reserva numero {n:03d}" for n in range(512)]
    fixtures_b.anadir_memorias_en_bloque(base.ruta, "lastre-comun", relleno)
    objetivo = fixtures_b.anadir_memoria(
        base.ruta, "lastre-comun", "el lastre mayor acompana la baliza del fondeadero"
    )
    identidad = f"MEMORIA:{objetivo}"
    fixtures_b.construir_sidecar(base)

    with PuertoSqlite(base.ruta) as puerto:
        por_clave = puerto.por_clave_exacta(("lastre-comun",))
    assert len(por_clave) == 512
    assert identidad not in {item.id for item in por_clave}, (
        "la premisa: la ruta por clave NO puede ver al objetivo"
    )

    b = candidato(base.ruta, base.sidecar)
    with PuertoSqlite(base.ruta) as puerto:
        recuperacion = engine.recuperar(_peticion(CONSULTA), puerto, b)
        materializaciones = [
            consulta
            for consulta in puerto.registro.consultas
            if consulta.operacion.startswith("por_identidad")
        ]
    por_id = {r.item.id: r for r in recuperacion.resultados}
    assert identidad in por_id, "el objetivo tras las 512 filas volvio a perderse"
    assert por_id[identidad].etapa_de_origen is Etapa.E3
    assert "semantica_vectorial" in por_id[identidad].explicacion.coincidencia

    registro_b = b.registro_vectorial
    assert registro_b is not None
    assert any(consulta.devueltos <= vectores.TOP_K for consulta in registro_b.consultas)
    identidades_pedidas = {
        parametro for consulta in materializaciones for parametro in consulta.parametros
    }
    assert str(objetivo) in identidades_pedidas
    assert len(identidades_pedidas) <= vectores.TOP_K, (
        "el trabajo depende del top-K solicitado, no de las filas que comparten clave"
    )
    for consulta in materializaciones:
        assert consulta.filas <= vectores.TOP_K


# --------------------------------------------------------------------------
# E. Identidad inconsistente: fallo cerrado y tipado
# --------------------------------------------------------------------------


def test_una_identidad_inexistente_en_el_canon_falla_cerrada(
    base: fixtures_b.FixtureB,
) -> None:
    fixtures_b.construir_sidecar(base)
    objetivo = fixtures_b.identificador_de(base.ruta, fixtures_b.OBJETIVO_SOLO_B)
    conexion = sqlite3.connect(str(base.sidecar))
    try:
        conexion.execute(
            "UPDATE vectores_de_elemento SET elemento = 'MEMORIA:9999' WHERE elemento = ?",
            (objetivo,),
        )
        conexion.execute(
            "UPDATE posting SET elemento = 'MEMORIA:9999' WHERE elemento = ?", (objetivo,)
        )
        conexion.commit()
    finally:
        conexion.close()

    b = candidato(base.ruta, base.sidecar)
    with PuertoSqlite(base.ruta) as puerto:  # noqa: SIM117
        with pytest.raises(vectores.IndiceInconsistenteError) as excepcion:
            engine.recuperar(_peticion(CONSULTA), puerto, b)
    mensaje = str(excepcion.value)
    assert "MEMORIA:9999" in mensaje
    for texto in base.textos:
        assert texto not in mensaje, "el mensaje no puede contener contenido protegido"
    assert isinstance(excepcion.value, vectores.IndiceNoUtilizableError)
    assert "S7" not in mensaje, "no se adjudica una parada que el motor no ofrece"


#: Marcador que separa las pruebas del control que las audita.
_MARCADOR_DEL_CONTROL = "def test_estas_pruebas_no_miden_rendimiento"


def test_estas_pruebas_no_miden_rendimiento() -> None:
    codigo = Path(__file__).read_text(encoding="utf-8")
    cuerpo = codigo.split(_MARCADOR_DEL_CONTROL)[0]
    for prohibido in ("perf_counter", "timeit", "time.time", "p95", "percentil", "latencia"):
        assert prohibido not in cuerpo, prohibido
    assert "performance_corpus" not in cuerpo
    assert "conformance_corpus" not in cuerpo
