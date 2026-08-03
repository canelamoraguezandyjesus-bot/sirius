"""Pruebas funcionales de ``ADR002-B`` sobre fixtures propios.

**Solo despues de la ficha vigente.** El commit de entrada de
``ficha_ADR002-B_v1.json`` es ancestro estricto del commit que ejecuta estas
pruebas, y la primera de ellas lo comprueba contra el grafo de Git en vez de
declararlo.

Lo que se demuestra, por secciones y con instrumentacion:

- **Activacion tardia:** si ``E1`` o ``E2`` satisfacen, la ruta vectorial se
  invoca cero veces y el sidecar ni siquiera se abre — las pruebas usan un
  sidecar INEXISTENTE a proposito, que reventaria con error tipado si alguien
  lo tocara.
- **Ablacion:** un caso que ``ADR002-A`` no puede alcanzar por ningun medio
  lexico-estructurado y que ``ADR002-B`` recupera exclusivamente por
  similitud distribucional de segundo orden, con ``etapa_de_origen == E3``;
  desactivar la senal lo hace desaparecer y deja a B identico a A.
- **Puertas no compensables:** similitud maxima (coseno 1,0) no supera G4,
  ni vigencia, ni polaridad, ni corte temporal.
- **Ciclo del indice:** determinismo por volcado logico, borrado sin
  residuos, corrupcion y desfase con fallo cerrado, reconstruccion que
  restituye el mismo resultado funcional.
- **Traza y privacidad:** bandas en vez de puntuaciones, cero texto
  protegido, ausencia y no-reportable indistinguibles.
- **Limitacion S7:** registrada con honestidad, no fabricada.

Lo que estas pruebas **no** hacen: no miden rendimiento, no ejecutan casos
oficiales, no tocan el corpus congelado v0.4 y no producen ningun resultado
utilizable como benchmark.
"""

from __future__ import annotations

import inspect
import json
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.candidates import fixtures_b
from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.candidates.adr002_a.candidate import candidato as candidato_a
from experiments.adr002.candidates.adr002_b import vectores
from experiments.adr002.candidates.adr002_b.candidate import CandidatoB, candidato
from experiments.adr002.candidates.common import engine, stops, trace
from experiments.adr002.candidates.common.contracts import (
    ESTADO_EXTERNO_SIN_RESULTADO,
    Ambito,
    Cardinalidad,
    Clase,
    ClaseDeEvidencia,
    Etapa,
    ItemCanonico,
    Modo,
    Peticion,
    Polaridad,
    Suficiencia,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import PuertoSqlite

RAIZ = Path(__file__).resolve().parents[3]
FICHA: Final = "artifacts/adr002_cards/ficha_ADR002-B_v7.json"

#: Se fija al congelar la v4; si quedara desactualizada, la cita fallaria.
#: Mientras la suite este suspendida por la guarda de anterioridad, este
#: centinela no se compara con nada.
HUELLA_FICHA_B_V7: Final = "33a7617dc8713d7dc29fce1877b7c41d689f25d7"

CONSULTA: Final = "faro"
OBJETIVO: Final = fixtures_b.OBJETIVO_SOLO_B


# --------------------------------------------------------------------------
# A. Anterioridad y aislamiento
# --------------------------------------------------------------------------


def _git(*argumentos: str) -> str:
    return subprocess.run(
        ["git", *argumentos], cwd=str(RAIZ), capture_output=True, text=True, check=False
    ).stdout.strip()


def _la_ficha_vigente_es_ancestro_estricto() -> bool:
    """Suspension de TOL-210: la fe de erratas 04 acoto las cotas del lector
    de B contra los escapes sin tipar, y estas pruebas se repiten enteras bajo
    la v5 o no se ejecutan."""
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
        "la ficha ADR002-B v5 aun no es ancestro estricto: ejecutar ahora "
        "produciria evidencia no utilizable (TOL-210, regla 3)"
    ),
)


def test_la_ficha_b_es_anterior_estricta_a_esta_ejecucion() -> None:
    """``TOL-210``: sin ficha previa, la ejecucion no es utilizable."""
    entrada = _git("log", "--format=%H", "--diff-filter=A", "--", FICHA)
    assert entrada, "la ficha v7 de ADR002-B no esta confirmada en el repositorio"
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


def test_la_ejecucion_cita_la_version_y_la_huella_correctas() -> None:
    """Una sola ficha CONGELADA de B —la v6— y v1..v5 conservadas."""
    fichas_de_b = sorted((RAIZ / "artifacts/adr002_cards").glob("ficha_ADR002-B_*.json"))
    assert [ruta.name for ruta in fichas_de_b] == [
        "ficha_ADR002-B_v1.json",
        "ficha_ADR002-B_v2.json",
        "ficha_ADR002-B_v3.json",
        "ficha_ADR002-B_v4.json",
        "ficha_ADR002-B_v5.json",
        "ficha_ADR002-B_v6.json",
        "ficha_ADR002-B_v7.json",
    ]
    for anterior in ("v1", "v2", "v3", "v4", "v5", "v6"):
        conservada = json.loads(
            (RAIZ / f"artifacts/adr002_cards/ficha_ADR002-B_{anterior}.json").read_text(
                encoding="utf-8"
            )
        )
        assert conservada["estado"] == "SUSTITUIDA"
    ficha = json.loads((RAIZ / FICHA).read_text(encoding="utf-8"))
    assert ficha["identidad"]["candidato"] == "ADR002-B"
    assert ficha["identidad"]["version"] == 7
    assert ficha["identidad"]["sustituye_a"] == 6
    assert ficha["estado"] == "CONGELADA"
    assert ficha["congelacion"]["huella"] == HUELLA_FICHA_B_V7
    assert ficha["senal_tardia"]["habilitada"] == "semantica_vectorial"
    assert ficha["no_contiene_resultados"] is True


# --------------------------------------------------------------------------
# Fixture y peticiones
# --------------------------------------------------------------------------


@pytest.fixture
def base(tmp_path: Path) -> fixtures_b.FixtureB:
    return fixtures_b.construir_base(tmp_path / "candidato-b.db")


@pytest.fixture
def indexada(base: fixtures_b.FixtureB) -> fixtures_b.FixtureB:
    fixtures_b.construir_sidecar(base)
    return base


def _peticion(
    consulta: str,
    *,
    cardinalidad: Cardinalidad = Cardinalidad.EXHAUSTIVA,
    limite_objetivo: int = 5,
    espacios: frozenset[Etapa] | None = None,
    corte: str | None = None,
) -> Peticion:
    argumentos = {
        "operation_id": "op-b",
        "consulta": consulta,
        "proposito": "comprobacion tecnica de reglas, sin medicion",
        "modo": Modo.M1_ORDINARIO,
        "ambito": Ambito(global_=False, proyectos=(fixtures_b.PROYECTO_ACTIVO,)),
        "ventana": VentanaTemporal(tiempo_objetivo="2026-07-01T00:00:00", corte_de_registro=corte),
        "cardinalidad": cardinalidad,
        "limite_objetivo": limite_objetivo,
        "limite_duro": 50,
        "objetivos": 1,
    }
    if espacios is not None:
        argumentos["espacios_autorizados"] = espacios
    return Peticion(**argumentos)  # type: ignore[arg-type]


def _recuperar(
    fixture: fixtures_b.FixtureB, candidato_b: CandidatoB, peticion: Peticion
) -> engine.Recuperacion:
    with PuertoSqlite(fixture.ruta) as puerto:
        return engine.recuperar(peticion, puerto, candidato_b)


def _sidecar_inexistente(fixture: fixtures_b.FixtureB) -> Path:
    return Path(f"{fixture.sidecar}.no-existe")


# --------------------------------------------------------------------------
# B. Activacion tardia, demostrada con instrumentacion
# --------------------------------------------------------------------------


def test_si_e1_satisface_la_ruta_vectorial_se_invoca_cero_veces(
    base: fixtures_b.FixtureB,
) -> None:
    """El sidecar es INEXISTENTE a proposito: tocarlo reventaria la prueba."""
    b = candidato(base.ruta, _sidecar_inexistente(base))
    recuperacion = _recuperar(
        base, b, _peticion(CONSULTA, cardinalidad=Cardinalidad.ACOTADA, limite_objetivo=1)
    )
    assert recuperacion.parada.identificador == "S1"
    assert recuperacion.resultados
    assert b.invocaciones_vectoriales == 0
    assert b.indice_abierto is False
    assert b.registro_vectorial is None


def test_si_e2_satisface_la_ruta_vectorial_se_invoca_cero_veces(
    base: fixtures_b.FixtureB,
) -> None:
    """``iluminacion`` solo se alcanza por variante en E2; alli se para."""
    b = candidato(base.ruta, _sidecar_inexistente(base))
    recuperacion = _recuperar(
        base, b, _peticion("iluminacion", cardinalidad=Cardinalidad.ACOTADA, limite_objetivo=1)
    )
    assert recuperacion.parada.identificador == "S1"
    claves = {r.item.subject_key for r in recuperacion.resultados}
    assert "faro-costa" in claves
    assert b.invocaciones_vectoriales == 0
    assert b.indice_abierto is False


def test_sin_autorizacion_de_e3_no_hay_senal_vectorial(base: fixtures_b.FixtureB) -> None:
    """El candidato no puede adelantar la senal ni cuando E1/E2 no bastan."""
    b = candidato(base.ruta, _sidecar_inexistente(base))
    recuperacion = _recuperar(
        base, b, _peticion(CONSULTA, espacios=frozenset({Etapa.E1, Etapa.E2}))
    )
    assert recuperacion.parada.identificador == "S2"
    assert b.invocaciones_vectoriales == 0
    assert b.indice_abierto is False


def test_solo_tras_la_insuficiencia_de_e1_y_e2_se_consulta_el_indice(
    indexada: fixtures_b.FixtureB,
) -> None:
    """Una unica invocacion, dentro de E3, con sus conteos registrados."""
    b = candidato(indexada.ruta, indexada.sidecar)
    recuperacion = _recuperar(indexada, b, _peticion(CONSULTA))
    assert b.invocaciones_vectoriales == 1
    assert b.indice_abierto is True
    registro = b.registro_vectorial
    assert registro is not None and len(registro.consultas) == 1
    consulta = registro.consultas[0]
    assert consulta.elementos_examinados <= vectores.ELEMENTOS_EXAMINADOS_MAXIMOS
    assert consulta.devueltos <= vectores.TOP_K
    etapas = [p.etapa for p in recuperacion.traza.pasos]
    assert Etapa.E3 in etapas


# --------------------------------------------------------------------------
# C. Ablacion: el caso exclusivo de B
# --------------------------------------------------------------------------


def test_el_objetivo_es_inalcanzable_para_adr002_a(indexada: fixtures_b.FixtureB) -> None:
    """Primero la premisa: A completo (E0-E5) no lo alcanza."""
    with PuertoSqlite(indexada.ruta) as puerto:
        recuperacion = engine.recuperar(_peticion(CONSULTA), puerto, candidato_a())
    claves = {r.item.subject_key for r in recuperacion.resultados}
    assert OBJETIVO not in claves
    assert recuperacion.resultados, "sin resultados de A no habria comparacion honesta"


def test_el_objetivo_no_comparte_forma_alguna_con_la_consulta(
    base: fixtures_b.FixtureB,
) -> None:
    """Ni token, ni variante morfologica, ni termino puente, ni familia.

    Es la premisa que hace demostrativa la ablacion: si compartiera forma,
    la base lexico-estructurada podria alcanzarlo y la prueba no probaria
    nada sobre la senal vectorial.
    """
    texto_objetivo = next(t for t in base.textos if "espigon" in t)
    tokens_objetivo = set(lexical.terminos_significativos(texto_objetivo))
    for variante in lexical.variantes(CONSULTA):
        assert variante not in tokens_objetivo
    semillas = [t for t in base.textos if CONSULTA in lexical.terminos_significativos(t)]
    assert semillas, "las semillas de la consulta deben existir"
    puentes = {token for texto in semillas for token in lexical.terminos_significativos(texto)}
    assert not (puentes & tokens_objetivo)
    assert not OBJETIVO.startswith(f"{CONSULTA}-")


def test_la_relacion_emerge_de_contextos_de_coocurrencia(
    indexada: fixtures_b.FixtureB,
) -> None:
    """Segundo orden de verdad: ``faro`` y ``baliza`` jamas coocurren.

    Ningun elemento del fixture contiene ambos terminos; la similitud nace de
    que comparten contextos (``senala``, ``oscuridad``) en elementos
    distintos. Eso es semantica distribucional, no una tabla de sinonimos.
    """
    for texto in indexada.textos:
        tokens = set(lexical.terminos_significativos(texto))
        assert not ({"faro", "baliza"} <= tokens), texto
    lector = vectores.LectorVectorial(indexada.ruta, indexada.sidecar)
    try:
        coincidencias = {c.clave_de_sujeto: c for c in lector.consultar((CONSULTA,))}
    finally:
        lector.close()
    assert OBJETIVO in coincidencias
    assert coincidencias[OBJETIVO].banda == "alta"
    assert coincidencias[OBJETIVO].solapamiento >= vectores.SOLAPAMIENTO_MINIMO


def test_b_recupera_el_objetivo_y_su_etapa_de_origen_es_exactamente_e3(
    indexada: fixtures_b.FixtureB,
) -> None:
    """``etapa_de_origen == E3`` y la explicacion nombra la senal vectorial."""
    b = candidato(indexada.ruta, indexada.sidecar)
    recuperacion = _recuperar(indexada, b, _peticion(CONSULTA))
    origen = {r.item.subject_key: r for r in recuperacion.resultados}
    assert OBJETIVO in origen, "B no recupero el caso que solo su senal puede alcanzar"
    resultado = origen[OBJETIVO]
    prohibidas: set[Etapa] = {Etapa.E1, Etapa.E2}
    assert resultado.etapa_de_origen not in prohibidas
    assert resultado.etapa_de_origen is Etapa.E3
    assert "semantica_vectorial" in resultado.explicacion.coincidencia
    assert "similitud distribucional" in resultado.explicacion.razon_de_orden


def test_desactivar_la_senal_vectorial_hace_desaparecer_el_objetivo(
    indexada: fixtures_b.FixtureB,
) -> None:
    """Control negativo de la ablacion, sobre el interruptor declarado."""
    apagado = candidato(indexada.ruta, indexada.sidecar, con_senal_vectorial=False)
    recuperacion = _recuperar(indexada, apagado, _peticion(CONSULTA))
    assert OBJETIVO not in {r.item.subject_key for r in recuperacion.resultados}
    assert apagado.invocaciones_vectoriales == 0


def test_b_sin_senal_vectorial_es_exactamente_a(indexada: fixtures_b.FixtureB) -> None:
    """La composicion, demostrada funcionalmente: B - senal == A, id a id."""
    peticion = _peticion(CONSULTA)
    apagado = candidato(indexada.ruta, indexada.sidecar, con_senal_vectorial=False)
    con_b = _recuperar(indexada, apagado, peticion)
    with PuertoSqlite(indexada.ruta) as puerto:
        con_a = engine.recuperar(peticion, puerto, candidato_a())
    assert con_b.ids == con_a.ids
    assert con_b.parada.identificador == con_a.parada.identificador


def test_la_lectura_semantica_de_b_es_la_de_a() -> None:
    """La validacion de lo vectorial no es distinta ni mas laxa (RF-17)."""
    item = ItemCanonico(
        id="MEMORIA:0",
        clase=Clase.MEMORIA,
        project_id="1",
        texto="la baliza no destella jamas en el dique",
        subject_key="baliza-averiada",
        vigente=True,
        disponible=True,
        created_at="2026-06-01T00:00:00",
        clase_de_evidencia=ClaseDeEvidencia.CANONICA,
    )
    b = candidato(Path("no-importa.db"), Path("no-importa.vectores.db"))
    assert b.leer(item, CONSULTA) == candidato_a().leer(item, CONSULTA)


# --------------------------------------------------------------------------
# D. Puertas no compensables: la similitud no compra nada
# --------------------------------------------------------------------------


def test_una_similitud_maxima_no_supera_el_ambito_g4(indexada: fixtures_b.FixtureB) -> None:
    """``baliza-forastera`` (proyecto ajeno) puntua coseno maximo y NO entra.

    Solo la senal vectorial puede proponerla —no comparte forma con las
    semillas—, de modo que el descarte G4 observado en la traza es del canal
    vectorial, no de la base.
    """
    lector = vectores.LectorVectorial(indexada.ruta, indexada.sidecar)
    try:
        coincidencias = {c.clave_de_sujeto: c for c in lector.consultar((CONSULTA,))}
    finally:
        lector.close()
    assert coincidencias["baliza-forastera"].similitud_fija == vectores.ESCALA_FIJA
    assert coincidencias["baliza-forastera"].banda == "alta"

    b = candidato(indexada.ruta, indexada.sidecar)
    recuperacion = _recuperar(indexada, b, _peticion(CONSULTA))
    assert "baliza-forastera" not in {r.item.subject_key for r in recuperacion.resultados}
    forastera = fixtures_b.identificador_de(indexada.ruta, "baliza-forastera")
    assert any(
        item == forastera and puerta == "G4" for item, puerta, _m in recuperacion.traza.puertas
    ), "el descarte G4 del canal vectorial debe constar en la traza"


def test_lo_no_vigente_ni_siquiera_entra_en_el_indice(indexada: fixtures_b.FixtureB) -> None:
    """``baliza-retirada`` esta archivada: el indice la excluye por origen.

    Y aunque la base lexica la proponga via FTS, G6/G7 la descartan: por
    ninguno de los dos canales una similitud o coincidencia la resucita.
    """
    retirada = fixtures_b.identificador_de(indexada.ruta, "baliza-retirada")
    conexion = sqlite3.connect(str(indexada.sidecar))
    try:
        for tabla in ("vectores_de_elemento", "posting"):
            filas = conexion.execute(
                f"SELECT count(*) FROM {tabla} WHERE elemento = ?", (retirada,)
            ).fetchone()
            assert int(filas[0]) == 0, f"{tabla} contiene un elemento no vigente"
    finally:
        conexion.close()
    b = candidato(indexada.ruta, indexada.sidecar)
    recuperacion = _recuperar(indexada, b, _peticion(CONSULTA))
    assert "baliza-retirada" not in {r.item.subject_key for r in recuperacion.resultados}


def test_la_polaridad_opuesta_se_conserva_y_no_se_fusiona(
    indexada: fixtures_b.FixtureB,
) -> None:
    """``baliza-averiada`` llega SOLO por vector y llega NEGATIVA.

    La similitud selecciona la candidata; no le fabrica identidad, ni verdad,
    ni postura: la negacion se lee item a item y las posturas no se fusionan
    (RF-17, RF-19, RF-20).
    """
    b = candidato(indexada.ruta, indexada.sidecar)
    recuperacion = _recuperar(indexada, b, _peticion(CONSULTA))
    por_clave = {r.item.subject_key: r for r in recuperacion.resultados}
    assert "baliza-averiada" in por_clave
    averiada = por_clave["baliza-averiada"]
    assert "semantica_vectorial" in averiada.explicacion.coincidencia
    assert averiada.lectura.polaridad is Polaridad.NEGATIVA
    assert por_clave[OBJETIVO].lectura.polaridad is Polaridad.AFIRMATIVA
    assert averiada.item.id != por_clave[OBJETIVO].item.id


def test_el_corte_temporal_excluye_lo_posterior_tambien_para_lo_vectorial(
    indexada: fixtures_b.FixtureB,
) -> None:
    """G8 rige igual: lo posterior al corte no entra, gane lo que gane."""
    b = candidato(indexada.ruta, indexada.sidecar)
    con_corte = _recuperar(indexada, b, _peticion(CONSULTA, corte="2026-07-01T00:00:00"))
    claves = {r.item.subject_key for r in con_corte.resultados}
    assert "baliza-futura" not in claves
    assert OBJETIVO in claves, "el objetivo es anterior al corte y debe seguir"


def test_g12_y_el_limite_duro_rigen_tambien_para_lo_vectorial(
    indexada: fixtures_b.FixtureB,
) -> None:
    b = candidato(indexada.ruta, indexada.sidecar)
    recuperacion = _recuperar(
        indexada,
        b,
        Peticion(
            operation_id="op-b",
            consulta=CONSULTA,
            proposito="comprobacion tecnica de reglas, sin medicion",
            modo=Modo.M1_ORDINARIO,
            ambito=Ambito(global_=False, proyectos=(fixtures_b.PROYECTO_ACTIVO,)),
            ventana=VentanaTemporal(tiempo_objetivo="2026-07-01T00:00:00"),
            cardinalidad=Cardinalidad.EXHAUSTIVA,
            limite_objetivo=1,
            limite_duro=1,
            objetivos=1,
        ),
    )
    assert len(recuperacion.resultados) <= 1


# --------------------------------------------------------------------------
# E. El indice derivado: determinismo, borrado, corrupcion, desfase
# --------------------------------------------------------------------------


def test_la_construccion_es_determinista(base: fixtures_b.FixtureB, tmp_path: Path) -> None:
    """Dos construcciones sobre el mismo canon: el mismo volcado logico."""
    primero = tmp_path / "uno.vectores.db"
    segundo = tmp_path / "dos.vectores.db"
    vectores.construir(base.ruta, primero)
    vectores.construir(base.ruta, segundo)
    assert vectores.volcado_logico(primero) == vectores.volcado_logico(segundo)


def test_borrado_completo_y_reconstruccion_identica(indexada: fixtures_b.FixtureB) -> None:
    """El ciclo entero: volcado igual y mismo resultado funcional despues."""
    antes = vectores.volcado_logico(indexada.sidecar)
    b = candidato(indexada.ruta, indexada.sidecar)
    resultados_antes = _recuperar(indexada, b, _peticion(CONSULTA)).ids

    vectores.borrar(indexada.sidecar)
    assert vectores.residuos(indexada.sidecar) == ()
    for sufijo in vectores.SUFIJOS_DE_FICHERO:
        assert not Path(f"{indexada.sidecar}{sufijo}").exists()

    fixtures_b.construir_sidecar(indexada)
    assert vectores.volcado_logico(indexada.sidecar) == antes
    b2 = candidato(indexada.ruta, indexada.sidecar)
    assert _recuperar(indexada, b2, _peticion(CONSULTA)).ids == resultados_antes


def test_el_sidecar_cabe_en_su_techo_declarado(indexada: fixtures_b.FixtureB) -> None:
    """La cota estatica de la ficha no es decorativa: se comprueba en bytes."""
    assert indexada.sidecar.stat().st_size <= vectores.ALMACENAMIENTO_MAXIMO_SIDECAR_B


def test_un_indice_inexistente_falla_cerrado(base: fixtures_b.FixtureB) -> None:
    b = candidato(base.ruta, _sidecar_inexistente(base))
    with pytest.raises(vectores.IndiceInexistenteError):
        _recuperar(base, b, _peticion(CONSULTA))


def test_un_indice_corrupto_falla_cerrado(indexada: fixtures_b.FixtureB) -> None:
    indexada.sidecar.write_bytes(b"esto ya no es una base de datos")
    b = candidato(indexada.ruta, indexada.sidecar)
    with pytest.raises(vectores.IndiceCorruptoError):
        _recuperar(indexada, b, _peticion(CONSULTA))


def test_unas_versiones_incompatibles_fallan_cerrado(indexada: fixtures_b.FixtureB) -> None:
    conexion = sqlite3.connect(str(indexada.sidecar))
    try:
        conexion.execute(
            "UPDATE metadatos SET valor = 'otro-algoritmo' WHERE clave = 'version_del_algoritmo'"
        )
        conexion.commit()
    finally:
        conexion.close()
    b = candidato(indexada.ruta, indexada.sidecar)
    with pytest.raises(vectores.IndiceCorruptoError):
        _recuperar(indexada, b, _peticion(CONSULTA))


def test_un_indice_desfasado_falla_cerrado_y_reconstruir_lo_cura(
    indexada: fixtures_b.FixtureB,
) -> None:
    """El canon cambia -> fallo cerrado; se reconstruye -> mismo resultado.

    La memoria anadida es deliberadamente inerte (tokens df=1): no altera el
    vocabulario util, de modo que la igualdad funcional tras reconstruir es
    exigible y no una casualidad.
    """
    b = candidato(indexada.ruta, indexada.sidecar)
    resultados_antes = _recuperar(indexada, b, _peticion(CONSULTA)).ids

    fixtures_b.anadir_memoria_inerte(
        indexada.ruta, "generador-taller", "el generador auxiliar del taller quedo revisado"
    )
    b2 = candidato(indexada.ruta, indexada.sidecar)
    with pytest.raises(vectores.IndiceDesfasadoError):
        _recuperar(indexada, b2, _peticion(CONSULTA))

    fixtures_b.construir_sidecar(indexada)
    b3 = candidato(indexada.ruta, indexada.sidecar)
    assert _recuperar(indexada, b3, _peticion(CONSULTA)).ids == resultados_antes


def test_el_indice_solo_cubre_vigentes_y_aprobadas(indexada: fixtures_b.FixtureB) -> None:
    """Origen exclusivo declarado: ni archivadas, ni propuestas, ni mensajes."""
    conexion = sqlite3.connect(str(indexada.sidecar))
    try:
        elementos = {
            str(fila[0]) for fila in conexion.execute("SELECT elemento FROM vectores_de_elemento")
        }
    finally:
        conexion.close()
    retirada = fixtures_b.identificador_de(indexada.ruta, "baliza-retirada")
    assert retirada not in elementos
    assert not any(e.startswith("MENSAJE") for e in elementos)
    canon = sqlite3.connect(str(indexada.ruta))
    try:
        propuesta = canon.execute("SELECT id FROM decisions WHERE status = 'proposed'").fetchone()
    finally:
        canon.close()
    assert propuesta is not None
    assert f"DECISION:{int(propuesta[0])}" not in elementos


def test_dos_ejecuciones_de_b_dan_el_mismo_orden(indexada: fixtures_b.FixtureB) -> None:
    peticion = _peticion(CONSULTA)
    primero = _recuperar(indexada, candidato(indexada.ruta, indexada.sidecar), peticion)
    segundo = _recuperar(indexada, candidato(indexada.ruta, indexada.sidecar), peticion)
    assert primero.ids == segundo.ids


# --------------------------------------------------------------------------
# F. Traza y privacidad
# --------------------------------------------------------------------------


def test_la_traza_no_filtra_contenido_protegido(indexada: fixtures_b.FixtureB) -> None:
    b = candidato(indexada.ruta, indexada.sidecar)
    recuperacion = _recuperar(indexada, b, _peticion(CONSULTA))
    assert trace.fallos_de_minimizacion(recuperacion.traza.como_dict(), indexada.textos) == []


def test_la_similitud_se_publica_en_bandas_y_no_como_verdad(
    indexada: fixtures_b.FixtureB,
) -> None:
    """Bandas minimizadas; ni puntuaciones crudas ni afirmaciones de identidad."""
    b = candidato(indexada.ruta, indexada.sidecar)
    recuperacion = _recuperar(indexada, b, _peticion(CONSULTA))
    vectoriales = [
        r for r in recuperacion.resultados if "semantica_vectorial" in r.explicacion.coincidencia
    ]
    assert vectoriales, "sin resultados vectoriales no habria nada que minimizar"
    for resultado in vectoriales:
        assert "banda" in resultado.explicacion.coincidencia
        assert "similitud distribucional" in resultado.explicacion.razon_de_orden
        campos = [
            str(getattr(resultado.explicacion, campo))
            for campo in ("coincidencia", "razon_de_orden")
        ] + list(resultado.explicacion.procedencias)
        for texto in campos:
            assert re.search(r"0[.,]\d+", texto) is None, "puntuacion cruda en la explicacion"
        assert any("del canon" in p for p in resultado.explicacion.procedencias)
    serializada = repr(recuperacion.traza.como_dict())
    assert re.search(r"0[.,]\d{3,}", serializada) is None, "puntuacion cruda en la traza"


def test_todo_resultado_conserva_sujeto_polaridad_condicion_y_tiempo(
    indexada: fixtures_b.FixtureB,
) -> None:
    b = candidato(indexada.ruta, indexada.sidecar)
    recuperacion = _recuperar(indexada, b, _peticion(CONSULTA))
    assert recuperacion.resultados
    assert trace.fallos_de_explicacion(recuperacion.resultados) == []
    for resultado in recuperacion.resultados:
        assert resultado.lectura.sujeto.strip()
        assert resultado.lectura.medio.strip()
        assert resultado.lectura.tiempo


def test_ausencia_y_no_reportable_siguen_indistinguibles(
    indexada: fixtures_b.FixtureB,
) -> None:
    """La senal vectorial no anade ningun estado externo distinguible."""
    b = candidato(indexada.ruta, indexada.sidecar)
    vacia = _recuperar(indexada, b, _peticion("zetaausentenoindexado"))
    assert vacia.resultados == ()
    assert vacia.estado_externo == ESTADO_EXTERNO_SIN_RESULTADO
    assert vacia.suficiencia is Suficiencia.NINGUNA_EN_AMBITO
    registro = b.registro_vectorial
    assert registro is not None
    assert registro.consultas[0].devueltos == 0


# --------------------------------------------------------------------------
# G. La limitacion S7, registrada con honestidad
# --------------------------------------------------------------------------


def test_el_fallo_cerrado_del_indice_no_se_disfraza_de_s7(
    base: fixtures_b.FixtureB,
) -> None:
    """El motor comun actual NO adjudica S7 desde el fallo del indice.

    Lo que hay: la excepcion tipada se propaga y la ejecucion no produce
    ningun resultado utilizable —comportamiento cerrado correcto—. Lo que NO
    hay: una parada S7 adjudicada. El constructor de S7 existe en la capa
    comun, pero el motor no tiene camino que lo invoque, y esta prueba deja
    ambas cosas escritas en vez de fingir cobertura. No se modifica la
    infraestructura comun para fabricar esa ruta; el benchmark podra
    convertir esta limitacion en fallo observable del candidato.
    """
    assert stops.parada_por_fuente_inaccesible("indice").identificador == "S7"
    fuente_del_motor = inspect.getsource(engine)
    assert "parada_por_fuente_inaccesible" not in fuente_del_motor
    b = candidato(base.ruta, _sidecar_inexistente(base))
    with pytest.raises(vectores.IndiceNoUtilizableError):
        _recuperar(base, b, _peticion(CONSULTA))


#: Marcador que separa las pruebas del control que las audita. El control se
#: excluye a si mismo por la misma razon que el inventario de neutralidad: es
#: el unico sitio donde los terminos prohibidos DEBEN aparecer.
_MARCADOR_DEL_CONTROL = "def test_estas_pruebas_no_miden_rendimiento"


def test_estas_pruebas_no_miden_rendimiento() -> None:
    """La prohibicion, comprobada sobre este mismo fichero.

    Medir el rendimiento de ``ADR002-B`` exige una autorizacion de benchmark
    que no existe, y una prueba tecnica que lo hiciera produciria cifras
    utilizables como evidencia sin ficha de ejecucion que las ampare.
    """
    codigo = Path(__file__).read_text(encoding="utf-8")
    cuerpo = codigo.split(_MARCADOR_DEL_CONTROL)[0]
    for prohibido in ("perf_counter", "timeit", "time.time", "p95", "percentil", "latencia"):
        assert prohibido not in cuerpo, prohibido
    assert "performance_corpus" not in cuerpo
    assert "conformance_corpus" not in cuerpo
