"""Los tres defectos del paquete de correccion 01, comprobados de verdad.

Este modulo existe porque las pruebas anteriores **no demostraban** lo que
decian demostrar. Cada bloque de aqui ataca uno de los tres defectos, y todos
se ejecutan **despues** de congelar ``ficha_ADR002-A_v2.json``: su commit de
entrada es ancestro estricto del commit que ejecuta, y la primera prueba lo
comprueba contra el grafo de Git en vez de declararlo.

1. **``E3`` recupera de verdad.** Un caso que ``E1`` y ``E2`` **no pueden**
   alcanzar, con la etapa de origen exigida exactamente igual a ``E3``.
2. **``E3`` no es un barrido.** El puerto registra cada sentencia con su cota y
   sus filas, de modo que la ausencia de barrido se comprueba sobre lo
   **ejecutado**: cuantas sentencias, cuantas filas, y que ninguna crece
   cuando el proyecto crece.
3. **La regeneracion es completa.** Inventario antes, desaparicion objeto a
   objeto, inventario restaurado, contenido derivado igual, y —lo que el
   defecto 3 ocultaba— el canon vuelve a **sincronizarse** despues, porque los
   triggers estan de nuevo ahi.

Lo que este modulo **no** hace: no mide rendimiento, no usa el corpus
congelado v0.4, no ejecuta casos oficiales y no produce ninguna cifra
utilizable como evidencia de benchmark. Solo fixtures propios.
"""

from __future__ import annotations

import sqlite3
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.candidates import fixtures
from experiments.adr002.candidates.adr002_a.candidate import candidato
from experiments.adr002.candidates.common import derived, engine
from experiments.adr002.candidates.common.contracts import (
    Ambito,
    Cardinalidad,
    Etapa,
    Modo,
    Peticion,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import (
    LIMITE_POR_PREFIJO,
    ConsultaNoDirigidaError,
    ConsultaRegistrada,
    PuertoSqlite,
    fallos_de_barrido,
)

RAIZ = Path(__file__).resolve().parents[3]
FICHA_VIGENTE: Final = "artifacts/adr002_cards/ficha_ADR002-A_v3.json"

#: El item que **solo** ``E3`` puede alcanzar desde la consulta ``faro``: su
#: texto no contiene ``faro`` ni ninguna variante morfologica suya.
SOLO_E3: Final = "abrigo-costa"

#: Mismo proyecto que las semillas, sin relacion lexica ni estructural con
#: ellas. Si apareciera, ``E3`` estaria enumerando el proyecto.
CONTROL_NEGATIVO: Final = "inventario-almacen"

CONSULTA: Final = "faro"

E1_E2: Final = frozenset({Etapa.E1, Etapa.E2})
E1_E3: Final = frozenset({Etapa.E1, Etapa.E2, Etapa.E3})


# --------------------------------------------------------------------------
# Guarda de anterioridad: la ficha vigente es la v3, y es anterior
# --------------------------------------------------------------------------


def _git(*argumentos: str) -> str:
    return subprocess.run(
        ["git", *argumentos], cwd=str(RAIZ), capture_output=True, text=True, check=False
    ).stdout.strip()


def _la_ficha_vigente_es_ancestro_estricto() -> bool:
    """Suspension de TOL-210: el paquete 02 cambio la capa comun de la huella
    de A, y estas pruebas se repiten enteras bajo la v3 o no se ejecutan."""
    entrada = _git("log", "--format=%H", "--diff-filter=A", "--", FICHA_VIGENTE)
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


def test_la_ficha_v3_es_anterior_estricta_a_esta_ejecucion() -> None:
    """``TOL-210``: sin ficha previa, la ejecucion no es utilizable.

    Y tiene que ser la **v3**: el paquete de correccion 02 cambio la capa
    comun incluida en la huella, de modo que ejecutar bajo la v2 produciria
    evidencia que la propia regla de custodia invalida.
    """
    entrada = _git("log", "--format=%H", "--diff-filter=A", "--", FICHA_VIGENTE)
    assert entrada, "la ficha v3 de ADR002-A no esta confirmada en el repositorio"
    commit_de_entrada = entrada.splitlines()[-1]
    head = _git("rev-parse", "HEAD")
    assert commit_de_entrada != head, "la ficha debe entrar ANTES del commit que ejecuta"
    ancestro = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit_de_entrada, head],
        cwd=str(RAIZ),
        capture_output=True,
        check=False,
    )
    assert ancestro.returncode == 0, "el commit de entrada de la ficha v3 no es ancestro de HEAD"


def test_las_fichas_anteriores_siguen_presentes_y_marcadas() -> None:
    """Ni la v1 ni la v2 se borran: se marcan. Ocultarlas escondería historia."""
    import json

    v1 = json.loads(
        (RAIZ / "artifacts/adr002_cards/ficha_ADR002-A_v1.json").read_text(encoding="utf-8")
    )
    v2 = json.loads(
        (RAIZ / "artifacts/adr002_cards/ficha_ADR002-A_v2.json").read_text(encoding="utf-8")
    )
    v3 = json.loads((RAIZ / FICHA_VIGENTE).read_text(encoding="utf-8"))
    assert v1["estado"] == "SUSTITUIDA"
    assert v2["estado"] == "SUSTITUIDA"
    assert v3["estado"] == "CONGELADA"
    assert v3["identidad"]["sustituye_a"] == 2
    assert v3["no_contiene_resultados"] is True


# --------------------------------------------------------------------------
# Fixture y peticiones
# --------------------------------------------------------------------------


@pytest.fixture
def base(tmp_path: Path) -> fixtures.Fixture:
    return fixtures.construir(tmp_path / "candidatos.db")


def _peticion(consulta: str, *, espacios: frozenset[Etapa] | None = None) -> Peticion:
    """Peticion exhaustiva y de ambito cerrado al proyecto activo.

    Exhaustiva porque ``S1`` queda deshabilitada y el motor recorre las etapas
    autorizadas: es la unica forma de observar ``E3`` sin que una parada por
    cuota la impida. El ambito se cierra para que su papel de **filtro** sea
    comprobable.
    """
    argumentos = {
        "operation_id": "op-correccion-01",
        "consulta": consulta,
        "proposito": "comprobacion tecnica de reglas, sin medicion",
        "modo": Modo.M1_ORDINARIO,
        "ambito": Ambito(global_=False, proyectos=(fixtures.PROYECTO_ACTIVO,)),
        "ventana": VentanaTemporal(tiempo_objetivo="2026-07-01T00:00:00"),
        "cardinalidad": Cardinalidad.EXHAUSTIVA,
        "limite_objetivo": 5,
        "limite_duro": 50,
        "objetivos": 1,
    }
    if espacios is not None:
        argumentos["espacios_autorizados"] = espacios
    return Peticion(**argumentos)  # type: ignore[arg-type]


def _correr(
    ruta: Path, espacios: frozenset[Etapa] | None = None
) -> tuple[engine.Recuperacion, list[ConsultaRegistrada]]:
    """Ejecuta y devuelve **lo recuperado y lo consultado**, en ese orden."""
    with PuertoSqlite(ruta) as puerto:
        recuperacion = engine.recuperar(_peticion(CONSULTA, espacios=espacios), puerto, candidato())
        return recuperacion, list(puerto.registro.consultas)


def _sentencias_de_e3(ruta: Path) -> list[ConsultaRegistrada]:
    """Las sentencias que ``E3`` anade, aisladas por diferencia.

    Autorizar hasta ``E2`` y autorizar hasta ``E3`` recorre exactamente el
    mismo camino salvo por ``E3``: la diferencia entre ambos registros **es**
    el trabajo de esa etapa, observado y no deducido.
    """
    _r12, hasta_e2 = _correr(ruta, E1_E2)
    _r13, hasta_e3 = _correr(ruta, E1_E3)
    assert hasta_e3[: len(hasta_e2)] == hasta_e2, "el camino previo a E3 no es el mismo"
    return hasta_e3[len(hasta_e2) :]


def _ids_materializados(sentencias: Sequence[ConsultaRegistrada]) -> set[str]:
    """Elementos canonicos distintos que las sentencias pidieron al canon."""
    return {
        f"{c.operacion}:{p}"
        for c in sentencias
        if c.operacion.startswith("materializar")
        for p in c.parametros
    }


# --------------------------------------------------------------------------
# Defecto 1: E3 recupera, y se exige que sea E3
# --------------------------------------------------------------------------


def test_el_caso_elegido_es_inalcanzable_para_e1_y_para_e2(base: fixtures.Fixture) -> None:
    """Primero la premisa: si ``E1`` o ``E2`` lo alcanzasen, no probaria nada.

    Esta es la prueba que faltaba. La anterior admitia que el resultado
    procediera de ``E1``, ``E2`` o ``E3`` sobre un caso que ``E2`` ya
    alcanzaba: no demostraba que ``E3`` recuperase nada.
    """
    recuperacion, _consultas = _correr(base.ruta, E1_E2)
    claves = {r.item.subject_key for r in recuperacion.resultados}
    assert SOLO_E3 not in claves
    assert recuperacion.resultados, "sin resultados previos no habria semillas para E3"


def test_e3_alcanza_el_caso_y_su_etapa_de_origen_es_exactamente_e3(
    base: fixtures.Fixture,
) -> None:
    """``etapa_de_origen == E3``. Ni ``E1``, ni ``E2``, ni «alguna de las tres»."""
    recuperacion, _consultas = _correr(base.ruta)
    origen = {r.item.subject_key: r.etapa_de_origen for r in recuperacion.resultados}
    assert SOLO_E3 in origen, "E3 no recupero el caso que solo ella puede alcanzar"
    # El orden importa: primero se rechazan las etapas que la prueba anterior
    # admitia, y solo despues se exige la igualdad estricta.
    prohibidas: set[Etapa] = {Etapa.E1, Etapa.E2}
    assert origen[SOLO_E3] not in prohibidas, "el origen no puede ser E1 ni E2"
    assert origen[SOLO_E3] is Etapa.E3


def test_e3_expande_desde_lo_recuperado_y_no_desde_la_consulta(
    base: fixtures.Fixture,
) -> None:
    """La razon por la que ``E3`` es una etapa y no un segundo intento de ``E2``.

    El texto del caso no contiene la consulta ni ninguna variante suya: lo que
    lo conecta es un termino puente presente en una **semilla**.
    """
    recuperacion, _consultas = _correr(base.ruta)
    alcanzado = next(r for r in recuperacion.resultados if r.item.subject_key == SOLO_E3)
    assert CONSULTA not in alcanzado.item.texto.lower()
    assert "puente" in alcanzado.explicacion.coincidencia or "puente" in str(
        alcanzado.lectura.medio + alcanzado.explicacion.coincidencia
    )


def test_desactivar_e3_hace_desaparecer_ese_resultado(base: fixtures.Fixture) -> None:
    """Control negativo del defecto 1: sin ``E3``, el caso no esta.

    Si siguiera apareciendo, lo estaria trayendo otra etapa y la prueba de
    ``E3`` seria de nuevo una prueba de nada.
    """
    con_e3, _c1 = _correr(base.ruta, E1_E3)
    sin_e3, _c2 = _correr(base.ruta, E1_E2)
    assert SOLO_E3 in {r.item.subject_key for r in con_e3.resultados}
    assert SOLO_E3 not in {r.item.subject_key for r in sin_e3.resultados}


# --------------------------------------------------------------------------
# Defecto 2: E3 no barre el proyecto, y se comprueba sobre lo ejecutado
# --------------------------------------------------------------------------


def test_el_puerto_no_ofrece_ninguna_ruta_de_barrido(base: fixtures.Fixture) -> None:
    """Ningun metodo del puerto equivale al barrido de ``T0``.

    No basta con no usarlo: una consulta sin predicado se **rechaza en
    ejecucion**, de modo que ninguna ruta futura pueda reintroducirlo en
    silencio.
    """
    with PuertoSqlite(base.ruta) as puerto:
        with pytest.raises(ConsultaNoDirigidaError):
            puerto._ejecutar("prueba", "SELECT id FROM memories", (), cota=1)
        assert puerto.por_termino_lexico([]) == ()
        assert puerto.por_clave_exacta([]) == ()
        assert puerto.por_prefijo_de_sujeto([]) == ()
        assert puerto.registro.consultas == []


def test_toda_sentencia_ejecutada_es_dirigida_y_respeta_su_cota(
    base: fixtures.Fixture,
) -> None:
    """La ausencia de barrido, comprobada sobre el registro de la ejecucion."""
    _recuperacion, consultas = _correr(base.ruta)
    assert consultas
    universo = fixtures.contenido_del_proyecto(base.ruta, fixtures.PROYECTO_ACTIVO)
    with PuertoSqlite(base.ruta) as puerto:
        puerto.registro.consultas.extend(consultas)
        assert fallos_de_barrido(puerto.registro, universo=universo) == []
    for consulta in consultas:
        assert consulta.dirigida, consulta.operacion
        assert consulta.filas <= consulta.cota, consulta.operacion


def test_e3_ejecuta_un_numero_acotado_de_sentencias_dirigidas(
    base: fixtures.Fixture,
) -> None:
    """Cuantas sentencias ejecuta ``E3``, y de que clase. Observado."""
    sentencias = _sentencias_de_e3(base.ruta)
    assert sentencias, "E3 no ejecuto ninguna consulta"
    assert len(sentencias) <= 13, [c.operacion for c in sentencias]
    operaciones = {c.operacion for c in sentencias}
    assert operaciones <= {
        "termino_lexico",
        "prefijo_de_sujeto:memoria",
        "prefijo_de_sujeto:decision",
        "materializar:MEMORIA",
        "materializar:DECISION",
    }
    for consulta in sentencias:
        if consulta.operacion.startswith("prefijo_de_sujeto"):
            assert consulta.cota == LIMITE_POR_PREFIJO
            assert not consulta.parametros[0].startswith("%")


def test_e3_no_pide_el_contenido_completo_del_proyecto(base: fixtures.Fixture) -> None:
    """Las filas candidatas de ``E3`` no son el proyecto entero.

    El defecto 2 hacia justo eso: pedia por ``project_id`` y materializaba
    hasta 512 memorias y 512 decisiones antes de filtrar.
    """
    for indice in range(30):
        fixtures.anadir_memoria(
            base.ruta,
            f"auxiliar-{indice:02d}",
            f"registro auxiliar numero {indice} de material inerte",
        )
    universo = fixtures.contenido_del_proyecto(base.ruta, fixtures.PROYECTO_ACTIVO)
    sentencias = _sentencias_de_e3(base.ruta)
    assert len(_ids_materializados(sentencias)) < universo
    assert sum(c.filas for c in sentencias) < universo


def test_ampliar_el_proyecto_no_convierte_e3_en_un_barrido(base: fixtures.Fixture) -> None:
    """La prueba decisiva: el trabajo de ``E3`` **no crece** con el proyecto.

    Si dependiese del tamano del proyecto en vez de lo recuperado, seria una
    enumeracion con otro nombre.
    """
    antes = _sentencias_de_e3(base.ruta)
    universo_antes = fixtures.contenido_del_proyecto(base.ruta, fixtures.PROYECTO_ACTIVO)
    resultado_antes, _c = _correr(base.ruta)

    for indice in range(30):
        fixtures.anadir_memoria(
            base.ruta,
            f"auxiliar-{indice:02d}",
            f"registro auxiliar numero {indice} de material inerte",
        )

    universo_despues = fixtures.contenido_del_proyecto(base.ruta, fixtures.PROYECTO_ACTIVO)
    assert universo_despues > universo_antes
    despues = _sentencias_de_e3(base.ruta)
    resultado_despues, _d = _correr(base.ruta)

    assert len(despues) == len(antes)
    assert sum(c.filas for c in despues) == sum(c.filas for c in antes)
    assert resultado_despues.ids == resultado_antes.ids


def test_coincidir_en_ambito_sin_relacion_no_basta_para_entrar(
    base: fixtures.Fixture,
) -> None:
    """El ambito **filtra**; no genera candidatos (``B04-RF-06``).

    ``inventario-almacen`` esta en el mismo proyecto que las semillas y no
    comparte con ellas ni termino ni familia de sujeto. Si entrase, el ambito
    estaria actuando de generador.
    """
    recuperacion, _consultas = _correr(base.ruta)
    claves = {r.item.subject_key for r in recuperacion.resultados}
    assert CONTROL_NEGATIVO not in claves
    assert SOLO_E3 in claves, "el control negativo solo vale si E3 si alcanza lo relacionado"


def test_los_prefijos_consultados_son_concretos_y_derivados_de_las_semillas(
    base: fixtures.Fixture,
) -> None:
    """Ningun prefijo comodin, y ninguno tan corto que seleccione media base."""
    sentencias = _sentencias_de_e3(base.ruta)
    prefijos = [c.parametros[0] for c in sentencias if c.operacion.startswith("prefijo_de_sujeto")]
    assert prefijos
    for patron in prefijos:
        assert patron.endswith("%")
        assert len(patron.rstrip("%")) >= 3
        assert "%" not in patron.rstrip("%")


# --------------------------------------------------------------------------
# Defecto 3: borrado y regeneracion COMPLETOS, con resincronizacion
# --------------------------------------------------------------------------


def test_el_inventario_derivado_incluye_tablas_sombras_y_triggers(
    base: fixtures.Fixture,
) -> None:
    """Lo que hay que destruir y restaurar, enumerado antes de tocar nada."""
    inventario = fixtures.objetos_derivados(base.ruta)
    assert inventario.completo
    assert set(inventario.tablas) == set(derived.TABLAS_FTS)
    assert inventario.sombras
    assert inventario.triggers, "sin triggers en el inventario no habria nada que restaurar"


def test_el_ddl_se_lee_del_canon_y_no_se_copia_a_mano(base: fixtures.Fixture) -> None:
    """La reconstruccion usa el DDL que creo la migracion canonica.

    Y si ese DDL llegara sin triggers, reconstruir se **rechaza**: seria una
    foto congelada, no una regeneracion.
    """
    ddl = fixtures.leer_ddl(base.ruta)
    assert ddl.completo
    assert len(ddl.tablas) == len(derived.TABLAS_FTS)
    conexion = sqlite3.connect(str(base.ruta))
    try:
        with pytest.raises(ValueError, match="triggers"):
            derived.reconstruir_derivado(conexion, derived.DdlCanonico(ddl.tablas, ()))
    finally:
        conexion.close()


def test_el_borrado_hace_desaparecer_el_derivado_objeto_a_objeto(
    base: fixtures.Fixture,
) -> None:
    """Desaparicion completa: tablas, sombras y triggers, comprobado uno a uno."""
    antes = fixtures.objetos_derivados(base.ruta)
    nombres = [*antes.tablas, *antes.sombras, *antes.triggers]
    fixtures.borrar_derivado(base.ruta)
    despues = fixtures.objetos_derivados(base.ruta)
    assert despues.vacio
    conexion = sqlite3.connect(str(base.ruta))
    try:
        assert derived.objetos_residuales(conexion, nombres) == ()
    finally:
        conexion.close()


def test_la_reconstruccion_restaura_el_inventario_y_el_contenido(
    base: fixtures.Fixture,
) -> None:
    """Mismo inventario y mismo contenido derivado, no una aproximacion."""
    inventario_antes = fixtures.objetos_derivados(base.ruta)
    filas_antes = fixtures.filas_indexadas(base.ruta)
    ddl = fixtures.leer_ddl(base.ruta)

    fixtures.borrar_derivado(base.ruta)
    fixtures.regenerar_derivado(base.ruta, ddl)

    inventario_despues = fixtures.objetos_derivados(base.ruta)
    assert derived.fallos_de_reconstruccion(inventario_antes, inventario_despues) == []
    assert inventario_despues.triggers == inventario_antes.triggers
    assert fixtures.filas_indexadas(base.ruta) == filas_antes


def test_tras_reconstruir_el_canon_vuelve_a_sincronizarse(base: fixtures.Fixture) -> None:
    """Lo que el defecto 3 ocultaba: que el indice **siga vivo** despues.

    Un alta y una modificacion del canon posteriores a la reconstruccion deben
    reflejarse en el indice sin tocarlo. Con los triggers perdidos —el estado
    que la prueba anterior no detectaba— ninguna de las dos ocurriria.
    """
    ddl = fixtures.leer_ddl(base.ruta)
    fixtures.borrar_derivado(base.ruta)
    fixtures.regenerar_derivado(base.ruta, ddl)

    memory_id = fixtures.anadir_memoria(
        base.ruta, "resincronizacion-alta", "el sincronizador zafiro quedo operativo"
    )
    conexion = sqlite3.connect(str(base.ruta))
    try:
        alta = conexion.execute(
            "SELECT item_id FROM knowledge_fts WHERE knowledge_fts MATCH 'zafiro'"
        ).fetchall()
        assert [int(f[0]) for f in alta] == [memory_id], "el trigger de alta no se reconstruyo"
    finally:
        conexion.close()

    fixtures.actualizar_memoria(base.ruta, memory_id, "el sincronizador topacio quedo operativo")
    conexion = sqlite3.connect(str(base.ruta))
    try:
        assert (
            conexion.execute(
                "SELECT count(*) FROM knowledge_fts WHERE knowledge_fts MATCH 'topacio'"
            ).fetchone()[0]
            == 1
        )
        assert (
            conexion.execute(
                "SELECT count(*) FROM knowledge_fts WHERE knowledge_fts MATCH 'zafiro'"
            ).fetchone()[0]
            == 0
        ), "el trigger de actualizacion no retiro el texto anterior"
    finally:
        conexion.close()


def test_la_recuperacion_sobrevive_al_ciclo_completo(base: fixtures.Fixture) -> None:
    """Y el candidato devuelve exactamente lo mismo despues del ciclo."""
    antes, _c = _correr(base.ruta)
    assert antes.ids
    ddl = fixtures.leer_ddl(base.ruta)
    fixtures.borrar_derivado(base.ruta)
    fixtures.regenerar_derivado(base.ruta, ddl)
    despues, _d = _correr(base.ruta)
    assert despues.ids == antes.ids


#: Marcador que separa las pruebas del control que las audita. El control se
#: excluye a si mismo por la misma razon que el inventario de neutralidad: es
#: el unico sitio donde los terminos prohibidos DEBEN aparecer.
_MARCADOR_DEL_CONTROL = "def test_este_modulo_no_mide_rendimiento"


def test_este_modulo_no_mide_rendimiento() -> None:
    """La prohibicion, comprobada sobre este mismo fichero."""
    codigo = Path(__file__).read_text(encoding="utf-8")
    cuerpo = codigo.split(_MARCADOR_DEL_CONTROL)[0]
    for prohibido in ("perf_counter", "timeit", "time.time", "p95", "percentil"):
        assert prohibido not in cuerpo, prohibido
    assert "performance_corpus" not in cuerpo
