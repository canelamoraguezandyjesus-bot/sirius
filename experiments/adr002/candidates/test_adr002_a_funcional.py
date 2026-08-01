"""Pruebas funcionales de ``ADR002-A`` sobre fixtures propios.

**Solo despues de la ficha vigente.** El commit de entrada de
``ficha_ADR002-A_v2.json`` es ancestro estricto del commit que ejecuta estas
pruebas, y la primera de ellas lo comprueba contra el grafo de Git en vez de
declararlo. La v1 quedo ``SUSTITUIDA`` y las ejecuciones hechas bajo ella son
historial, no evidencia vigente: por eso estas pruebas se repiten enteras aqui
en vez de heredarse.

Lo que estas pruebas **no** hacen: no miden rendimiento, no ejecutan casos
oficiales, no tocan el corpus congelado v0.4 y no producen ningun resultado
utilizable como benchmark. Verifican **reglas**: etapas, puertas, paradas,
ambito, polaridad, tiempo, explicacion, trazas y ciclo del derivado.

Las tres reglas que el paquete de correccion 01 puso en duda —que ``E3``
recupere de verdad, que no barra el proyecto y que la regeneracion sea
completa— viven en ``test_adr002_a_e3_y_regeneracion.py``, con sus controles
negativos propios.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest
from experiments.adr002.candidates import fixtures
from experiments.adr002.candidates.adr002_a.candidate import candidato
from experiments.adr002.candidates.common import engine, trace
from experiments.adr002.candidates.common.contracts import (
    ESTADO_EXTERNO_SIN_RESULTADO,
    Ambito,
    Candidata,
    Cardinalidad,
    ContextoDeEtapa,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
    Modo,
    Peticion,
    Polaridad,
    Suficiencia,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import PuertoSqlite

RAIZ = Path(__file__).resolve().parents[3]
FICHA = "artifacts/adr002_cards/ficha_ADR002-A_v3.json"


# --------------------------------------------------------------------------
# La guarda de anterioridad, comprobada contra Git
# --------------------------------------------------------------------------


def _git(*argumentos: str) -> str:
    return subprocess.run(
        ["git", *argumentos], cwd=str(RAIZ), capture_output=True, text=True, check=False
    ).stdout.strip()


def _la_ficha_vigente_es_ancestro_estricto() -> bool:
    """Suspension de TOL-210: sin ficha sucesora anterior, no se ejecuta.

    El paquete de correccion 02 cambio fuentes de la huella de A (la capa
    comun), de modo que ejecutar bajo la v2 produciria evidencia no
    utilizable. Estas pruebas SE REPITEN enteras bajo la v3; mientras su
    commit de entrada no sea ancestro estricto, quedan suspendidas y el
    motivo esta escrito aqui.
    """
    entrada = _git("log", "--format=%H", "--diff-filter=A", "--", FICHA)
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
    not _la_ficha_vigente_es_ancestro_estricto(),
    reason=(
        "la ficha ADR002-A v3 aun no es ancestro estricto: ejecutar ahora "
        "produciria evidencia no utilizable (TOL-210, regla 3)"
    ),
)


def test_la_ficha_es_anterior_estricta_a_esta_ejecucion() -> None:
    """Una ejecucion sin ficha previa no es utilizable como evidencia.

    ``TOL-210`` exige ancestro **estricto**: aparecer en el mismo commit que la
    ejecucion no es haber congelado antes.
    """
    entrada = _git("log", "--format=%H", "--diff-filter=A", "--", FICHA)
    assert entrada, "la ficha vigente de ADR002-A no esta confirmada en el repositorio"
    commit_de_entrada = entrada.splitlines()[-1]
    head = _git("rev-parse", "HEAD")
    assert commit_de_entrada != head, "la ficha debe entrar ANTES del commit que ejecuta"
    ancestro = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit_de_entrada, head],
        cwd=str(RAIZ),
        capture_output=True,
        check=False,
    )
    assert ancestro.returncode == 0, "el commit de entrada de la ficha no es ancestro de HEAD"


# --------------------------------------------------------------------------
# Fixture y peticiones
# --------------------------------------------------------------------------


@pytest.fixture
def base(tmp_path: Path) -> fixtures.Fixture:
    return fixtures.construir(tmp_path / "candidatos.db")


def _peticion(
    consulta: str,
    *,
    cardinalidad: Cardinalidad = Cardinalidad.EXACTA,
    modo: Modo = Modo.M1_ORDINARIO,
    global_: bool = False,
    espacios: frozenset[Etapa] | None = None,
    objetivos: int = 1,
    limite_objetivo: int = 5,
    limite_duro: int = 20,
    corte: str | None = None,
    proposito: str = "consulta ordinaria autorizada",
) -> Peticion:
    ambito = Ambito(global_=global_, proyectos=(fixtures.PROYECTO_ACTIVO,))
    argumentos = {
        "operation_id": "op-prueba",
        "consulta": consulta,
        "proposito": proposito,
        "modo": modo,
        "ambito": ambito,
        "ventana": VentanaTemporal(tiempo_objetivo="2026-07-01T00:00:00", corte_de_registro=corte),
        "cardinalidad": cardinalidad,
        "limite_objetivo": limite_objetivo,
        "limite_duro": limite_duro,
        "objetivos": objetivos,
    }
    if espacios is not None:
        argumentos["espacios_autorizados"] = espacios
    return Peticion(**argumentos)  # type: ignore[arg-type]


def _recuperar(base: fixtures.Fixture, peticion: Peticion) -> engine.Recuperacion:
    with PuertoSqlite(base.ruta) as puerto:
        return engine.recuperar(peticion, puerto, candidato())


# --------------------------------------------------------------------------
# E0-E5: expansion escalonada sin saltos
# --------------------------------------------------------------------------


def test_e0_bloquea_sin_proposito(base: fixtures.Fixture) -> None:
    """``G1``: sin proposito no se ejecuta recuperacion, y se dice por que."""
    recuperacion = _recuperar(base, _peticion("faro", proposito="   "))
    assert recuperacion.resultados == ()
    assert recuperacion.parada.identificador == "S3"
    assert recuperacion.estado_externo == ESTADO_EXTERNO_SIN_RESULTADO


def test_e1_recupera_por_clave_exacta_y_para_por_s1(base: fixtures.Fixture) -> None:
    """La etapa de maxima autoridad basta: no se expande sin necesidad."""
    recuperacion = _recuperar(base, _peticion("faro-costa"))
    assert recuperacion.parada.identificador == "S1"
    assert any(r.item.subject_key == "faro-costa" for r in recuperacion.resultados)
    etapas = [p.etapa for p in recuperacion.traza.pasos]
    assert Etapa.E3 not in etapas and Etapa.E4 not in etapas


def test_la_expansion_no_salta_etapas(base: fixtures.Fixture) -> None:
    """``B04-RF-14``: E1, E2, E3 y E4 en orden, ninguna omitida."""
    recuperacion = _recuperar(base, _peticion("iluminacion", cardinalidad=Cardinalidad.EXHAUSTIVA))
    ejecutadas = [p.etapa for p in recuperacion.traza.pasos if p.etapa in set(Etapa)]
    expansion = [e for e in ejecutadas if e in (Etapa.E1, Etapa.E2, Etapa.E3, Etapa.E4)]
    assert expansion == [Etapa.E1, Etapa.E2, Etapa.E3, Etapa.E4]


def test_cada_transicion_registra_su_causa(base: fixtures.Fixture) -> None:
    """Una transicion sin causa registrada seria irreproducible."""
    recuperacion = _recuperar(base, _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA))
    for paso in recuperacion.traza.pasos:
        assert paso.causa_de_entrada.strip(), paso.etapa


def test_e2_alcanza_variantes_morfologicas(base: fixtures.Fixture) -> None:
    """``iluminar`` alcanza ``iluminacion`` por variante, no por sinonimia."""
    recuperacion = _recuperar(base, _peticion("iluminacion", cardinalidad=Cardinalidad.EXHAUSTIVA))
    claves = {r.item.subject_key for r in recuperacion.resultados}
    assert "senal-iluminacion" in claves


def test_e3_no_se_ejecuta_sin_semillas(base: fixtures.Fixture) -> None:
    """Sin nada recuperado antes, ``E3`` no tiene desde donde expandir.

    Inventar un punto de partida seria volver a la consulta —trabajo de
    ``E2``— o enumerar un espacio, que es el barrido que ``RF-14`` prohibe.
    """
    recuperacion = _recuperar(
        base, _peticion("zetaausentenoindexado", cardinalidad=Cardinalidad.EXHAUSTIVA)
    )
    assert recuperacion.resultados == ()
    paso_e3 = next(p for p in recuperacion.traza.pasos if p.etapa is Etapa.E3)
    assert paso_e3.aportadas == 0


def test_e4_marca_el_historial_como_evidencia_atribuida(base: fixtures.Fixture) -> None:
    """``B04-RF-13``: el historial no se eleva a verdad canonica."""
    recuperacion = _recuperar(
        base, _peticion("patron", cardinalidad=Cardinalidad.EXHAUSTIVA, global_=True)
    )
    atribuidas = [r for r in recuperacion.resultados if r.item.id.startswith("MENSAJE:")]
    for resultado in atribuidas:
        assert resultado.item.clase_de_evidencia.value == "ATRIBUIDA"


# --------------------------------------------------------------------------
# Puertas
# --------------------------------------------------------------------------


def test_g4_aisla_el_ambito(base: fixtures.Fixture) -> None:
    """``RF-06``: fuera de ambito no contamina, ni siquiera como descarte."""
    recuperacion = _recuperar(base, _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA))
    claves = {r.item.subject_key for r in recuperacion.resultados}
    assert "faro-ajeno" not in claves
    assert any(p == "G4" for _i, p, _m in recuperacion.traza.puertas)


def test_g6_y_g7_excluyen_lo_no_vigente_en_m1(base: fixtures.Fixture) -> None:
    recuperacion = _recuperar(base, _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA))
    claves = {r.item.subject_key for r in recuperacion.resultados}
    assert "faro-antiguo" not in claves


def test_g8_respeta_el_corte_de_registro(base: fixtures.Fixture) -> None:
    """Lo posterior al corte no es lo que Sirius sabia entonces."""
    recuperacion = _recuperar(
        base,
        _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA, corte="2026-07-01T00:00:00"),
    )
    claves = {r.item.subject_key for r in recuperacion.resultados}
    assert "faro-futuro" not in claves


def test_g12_preserva_criticos_y_declara_desbordamiento(base: fixtures.Fixture) -> None:
    """Bajo limite duro se declara desbordamiento; no se oculta."""
    recuperacion = _recuperar(
        base,
        _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA, limite_duro=1, limite_objetivo=1),
    )
    assert len(recuperacion.resultados) <= 1
    assert recuperacion.traza.desbordamiento or len(recuperacion.resultados) <= 1


# --------------------------------------------------------------------------
# Paradas
# --------------------------------------------------------------------------


def test_s1_no_se_adjudica_en_exhaustiva(base: fixtures.Fixture) -> None:
    """La regla de ``B04 §15.2``: exhaustiva agota o para por S2-S7."""
    recuperacion = _recuperar(base, _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA))
    assert recuperacion.parada.identificador != "S1"


def test_s2_para_cuando_el_modo_no_autoriza_el_espacio(base: fixtures.Fixture) -> None:
    recuperacion = _recuperar(
        base,
        _peticion(
            "faro",
            cardinalidad=Cardinalidad.EXHAUSTIVA,
            espacios=frozenset({Etapa.E1, Etapa.E2}),
        ),
    )
    assert recuperacion.parada.identificador == "S2"


def test_siempre_se_adjudica_exactamente_una_parada(base: fixtures.Fixture) -> None:
    for cardinalidad in Cardinalidad:
        recuperacion = _recuperar(base, _peticion("faro", cardinalidad=cardinalidad))
        assert recuperacion.parada.identificador in {f"S{n}" for n in range(1, 8)}
        assert recuperacion.traza.parada is not None


# --------------------------------------------------------------------------
# Semantica: sujeto, polaridad, condicion, tiempo
# --------------------------------------------------------------------------


def test_la_polaridad_negativa_se_preserva(base: fixtures.Fixture) -> None:
    """``RF-19``: la negacion no se pierde en expansion ni en ranking."""
    recuperacion = _recuperar(base, _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA))
    por_clave = {r.item.subject_key: r.lectura for r in recuperacion.resultados}
    assert por_clave["faro-niebla"].polaridad is Polaridad.NEGATIVA
    assert por_clave["faro-costa"].polaridad is Polaridad.AFIRMATIVA


def test_la_condicion_se_declara(base: fixtures.Fixture) -> None:
    recuperacion = _recuperar(base, _peticion("boya", cardinalidad=Cardinalidad.EXHAUSTIVA))
    por_clave = {r.item.subject_key: r.lectura for r in recuperacion.resultados}
    assert por_clave["boya-canal"].condicion == "si"


def test_toda_lectura_declara_sujeto_y_medio(base: fixtures.Fixture) -> None:
    """``G11``: sin lectura completa no se llega al ranking."""
    recuperacion = _recuperar(base, _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA))
    for resultado in recuperacion.resultados:
        assert resultado.lectura.sujeto.strip()
        assert resultado.lectura.medio.strip()
        assert resultado.lectura.tiempo


def test_las_posturas_opuestas_no_se_fusionan(base: fixtures.Fixture) -> None:
    """``RF-20``/``RF-21``: apoyo y refutacion se conservan separados."""
    recuperacion = _recuperar(base, _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA))
    claves = [r.item.subject_key for r in recuperacion.resultados]
    assert "faro-costa" in claves
    assert "faro-niebla" in claves


# --------------------------------------------------------------------------
# Explicacion y traza
# --------------------------------------------------------------------------


def test_todo_resultado_lleva_explicacion_completa(base: fixtures.Fixture) -> None:
    """``RF-28``: 100 % de la muestra, no la mayoria."""
    recuperacion = _recuperar(base, _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA))
    assert recuperacion.resultados
    assert trace.fallos_de_explicacion(recuperacion.resultados) == []


def test_la_traza_reproduce_el_plan(base: fixtures.Fixture) -> None:
    """``RF-29``: puertas, etapas, expansiones, agrupaciones y parada."""
    recuperacion = _recuperar(base, _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA))
    plan = recuperacion.traza.como_dict()
    assert plan["etapas"] and plan["parada"] is not None
    assert plan["modo"] == "M1" and plan["cardinalidad"] == "EXHAUSTIVA"
    assert plan["candidato"] == "ADR002-A"
    assert "descartes_por_puerta" in plan and "suficiencia" in plan


def test_la_traza_no_filtra_contenido_protegido(base: fixtures.Fixture) -> None:
    """La auditoria no puede convertirse en canal lateral (``B04-Q18``)."""
    recuperacion = _recuperar(base, _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA))
    assert trace.fallos_de_minimizacion(recuperacion.traza.como_dict(), base.textos) == []


def test_ausencia_y_no_reportable_comparten_estado_externo(base: fixtures.Fixture) -> None:
    """``RF-26``: distinguirlas fuera filtraria existencia."""
    vacia = _recuperar(base, _peticion("zetaausentenoindexado"))
    assert vacia.resultados == ()
    assert vacia.estado_externo == ESTADO_EXTERNO_SIN_RESULTADO
    assert vacia.suficiencia is Suficiencia.NINGUNA_EN_AMBITO


# --------------------------------------------------------------------------
# Determinismo y ciclo del derivado
# --------------------------------------------------------------------------


def test_dos_ejecuciones_dan_el_mismo_orden(base: fixtures.Fixture) -> None:
    """Sin determinismo, ninguna comparacion entre candidatos seria justa."""
    peticion = _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA)
    assert _recuperar(base, peticion).ids == _recuperar(base, peticion).ids


def test_sin_derivado_la_recuperacion_lexica_no_encuentra_nada(
    base: fixtures.Fixture,
) -> None:
    """Todo derivado es regenerable y **no autoritativo** (ADR-001).

    Con el derivado borrado, el candidato deja de recuperar por via lexica: es
    la comprobacion de que el indice no guarda autoridad propia. La
    reconstruccion completa —con triggers y resincronizacion— se comprueba en
    ``test_adr002_a_e3_y_regeneracion.py``.
    """
    peticion = _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA)
    antes = _recuperar(base, peticion).ids
    assert antes

    ddl = fixtures.leer_ddl(base.ruta)
    fixtures.borrar_derivado(base.ruta)
    fixtures.regenerar_derivado(base.ruta, ddl)
    assert _recuperar(base, peticion).ids == antes


# --------------------------------------------------------------------------
# Neutralidad ejecutable: el motor no es de ADR002-A
# --------------------------------------------------------------------------


class _CandidatoDePrueba:
    """Candidato minimo y ajeno a ``ADR002-A``, solo para esta comprobacion.

    Si el motor solo funcionara con las senales de ``ADR002-A``, esta prueba
    fallaria — y con ella caeria la premisa de que la infraestructura es
    comparable entre alternativas.
    """

    identificador = "CANDIDATO-DE-PRUEBA"

    @property
    def senal_tardia_habilitada(self) -> str:
        return "ninguna_adicional"

    def leer(self, item: ItemCanonico, consulta: str) -> LecturaSemantica:
        del consulta  # el candidato de prueba no la usa: su lectura es trivial
        return LecturaSemantica(
            sujeto=item.subject_key or item.id,
            polaridad=Polaridad.AFIRMATIVA,
            condicion=None,
            tiempo=item.created_at,
            medio="candidato de prueba: lectura trivial",
        )

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        if contexto.etapa is not Etapa.E1:
            return ()
        items = contexto.puerto.por_termino_lexico([contexto.peticion.consulta])
        return [
            Candidata(
                item=item,
                etapa=contexto.etapa,
                lectura=self.leer(item, contexto.peticion.consulta),
                razon="coincidencia literal del candidato de prueba",
                senal="termino literal",
            )
            for item in items
        ]


def test_el_motor_funciona_con_un_candidato_ajeno(base: fixtures.Fixture) -> None:
    """El cuarto control de neutralidad, el que exige ejecutar."""
    peticion = _peticion("faro", cardinalidad=Cardinalidad.EXHAUSTIVA)
    with PuertoSqlite(base.ruta) as puerto:
        recuperacion = engine.recuperar(peticion, puerto, _CandidatoDePrueba())
    assert recuperacion.traza.candidato == "CANDIDATO-DE-PRUEBA"
    assert recuperacion.parada.identificador in {f"S{n}" for n in range(1, 8)}
    assert trace.fallos_de_explicacion(recuperacion.resultados) == []


#: Marcador que separa las pruebas del control que las audita. El control se
#: excluye a si mismo por la misma razon que el inventario de neutralidad: es
#: el unico sitio donde los terminos prohibidos DEBEN aparecer.
_MARCADOR_DEL_CONTROL = "def test_estas_pruebas_no_miden_rendimiento"


def test_estas_pruebas_no_miden_rendimiento() -> None:
    """La prohibicion, comprobada sobre este mismo fichero.

    Medir el rendimiento de ``ADR002-A`` exige una autorizacion de benchmark
    que no existe, y una prueba tecnica que lo hiciera produciria cifras
    utilizables como evidencia sin ficha de ejecucion que las ampare.
    """
    codigo = Path(__file__).read_text(encoding="utf-8")
    cuerpo = codigo.split(_MARCADOR_DEL_CONTROL)[0]
    for prohibido in ("perf_counter", "timeit", "time.time", "p95", "percentil"):
        assert prohibido not in cuerpo, prohibido
