"""Unit tests for ``sirius.adapters.persistence.staged_engine_port``
(issue #457/ADR-109/ADR-110): the ``PuertoDeRecuperacion`` adapter over the
real Sirius 0.1 schema. Uses a real, migrated SQLite database (like
``tests/integration/test_rank_relevant_knowledge.py``) because the queries
under test are SQL, not pure Python.

La última sección (incidencia #572/ADR-165, palanca 2 de ADR-148) fija los
ejes que el puerto DERIVA de las filas que ya lee, y —una por eje— fija
también que, faltando el dato del que sale, el eje queda sin derivar en vez
de recibir un valor inventado. Las fechas se fuerzan con ``UPDATE`` directos
sobre la base ya creada por los repositorios reales: sin eso, el instante
sería el del reloj de la máquina y la prueba mediría la máquina, no de qué
columna sale cada eje (SIRIUS-ARQ-0.1 S4).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from sirius.adapters.persistence.database import (
    build_engine,
    build_session_factory,
    session_scope,
)
from sirius.adapters.persistence.migrations import upgrade_to_head
from sirius.adapters.persistence.sqlite_decision_repository import (
    build_sqlite_decision_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_project_repository import build_sqlite_project_repository
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.adapters.persistence.staged_engine_port import (
    AUTORIDAD_POR_ORIGEN,
    IdentificadorInvalidoError,
    StagedEnginePort,
    build_staged_engine_port,
)
from sirius.application.confirm_memory_suggestion import CONFIRMED_MEMORY_SUGGESTION_ORIGIN
from sirius.application.correct_memory import MEMORY_CORRECTION_ORIGIN
from sirius.application.save_manual_memory import MANUAL_MEMORY_ORIGIN, SaveManualMemoryUseCase
from sirius.domain import staged_engine_gates as gates
from sirius.domain.staged_engine_contracts import (
    SIN_EJES,
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


def _bootstrap(database_path: Path) -> None:
    upgrade_to_head(database_path)
    build_sqlite_project_repository(database_path).ensure_bootstrap_project()


def test_por_termino_lexico_finds_a_saved_memory(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory = SaveManualMemoryUseCase(build_sqlite_unit_of_work(database_path)).save(
        "terminounicoparabuscar en la memoria"
    )

    puerto = build_staged_engine_port(database_path)
    try:
        encontrados = puerto.por_termino_lexico(["terminounicoparabuscar"])
    finally:
        puerto.close()

    assert [i.id for i in encontrados] == [f"{Clase.MEMORIA.value}:{memory.id}"]
    # ADR-165: un guardado manual llega con los dos ejes que sus filas SÍ
    # declaran. Antes de ADR-165 esta línea exigía `SIN_EJES`.
    assert encontrados[0].ejes.autoridad == "ACTO_EXPLICITO_USUARIO"
    assert encontrados[0].ejes.valid_from is not None


def test_por_termino_lexico_sin_terminos_utiles_no_ejecuta_consulta(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    puerto = build_staged_engine_port(database_path)
    try:
        assert puerto.por_termino_lexico(["", "  "]) == ()
    finally:
        puerto.close()


def test_por_clave_exacta_finds_by_subject_key(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project = build_sqlite_project_repository(database_path).create_project(
        "Proyecto de prueba", "objetivo", state_summary="", blockers=(), next_step=""
    )
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save(
        "texto cualquiera", subject_key="faro-costa-unico", project_id=project.id
    )

    puerto = build_staged_engine_port(database_path)
    try:
        encontrados = puerto.por_clave_exacta(["faro-costa-unico"])
    finally:
        puerto.close()

    assert [i.id for i in encontrados] == [f"{Clase.MEMORIA.value}:{memory.id}"]


def test_por_prefijo_de_sujeto_rejects_a_prefix_shorter_than_three_chars(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project = build_sqlite_project_repository(database_path).create_project(
        "Proyecto de prueba", "objetivo", state_summary="", blockers=(), next_step=""
    )
    unit_of_work = build_sqlite_unit_of_work(database_path)
    SaveManualMemoryUseCase(unit_of_work).save(
        "texto", subject_key="fa-algo-unico", project_id=project.id
    )

    puerto = build_staged_engine_port(database_path)
    try:
        # "fa" tiene menos de 3 caracteres: no es una relacion, es un barrido.
        assert puerto.por_prefijo_de_sujeto(["fa"]) == ()
    finally:
        puerto.close()


def test_por_identificadores_declares_absent_ids_without_raising(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    unit_of_work = build_sqlite_unit_of_work(database_path)
    memory = SaveManualMemoryUseCase(unit_of_work).save("texto cualquiera")

    puerto = build_staged_engine_port(database_path)
    try:
        materializacion = puerto.por_identificadores(
            [f"{Clase.MEMORIA.value}:{memory.id}", f"{Clase.MEMORIA.value}:999999"]
        )
    finally:
        puerto.close()

    assert [i.id for i in materializacion.items] == [f"{Clase.MEMORIA.value}:{memory.id}"]
    assert materializacion.ausentes == (f"{Clase.MEMORIA.value}:999999",)
    assert materializacion.completa is False


def test_por_identificadores_rejects_a_malformed_identifier(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    puerto = build_staged_engine_port(database_path)
    try:
        with pytest.raises(IdentificadorInvalidoError):
            puerto.por_identificadores(["no-es-un-identificador"])
    finally:
        puerto.close()


def test_historial_y_fuentes_always_empty(tmp_path: Path) -> None:
    """``E4`` no tiene objetivo real en Sirius 0.1: ``RankedKnowledge`` solo
    modela ``Memory``/``Decision`` (ver docstring del módulo bajo prueba)."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    puerto = build_staged_engine_port(database_path)
    try:
        assert puerto.historial_y_fuentes(["cualquiera"]) == ()
    finally:
        puerto.close()


def test_ejes_por_identidad_overrides_sin_ejes_for_a_declared_item(tmp_path: Path) -> None:
    """Lo DECLARADO manda sobre lo derivado (ADR-165).

    El item de esta prueba tiene ejes derivables —es un guardado manual con
    su revisión—, y aun así sale con los declarados y solo con ellos.
    """
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    memory = SaveManualMemoryUseCase(build_sqlite_unit_of_work(database_path)).save(
        "terminounicoconejes en la memoria"
    )
    identidad = f"{Clase.MEMORIA.value}:{memory.id}"
    ejes_declarados = EjesDeclarados(ambito="GLOBAL")

    engine = build_engine(database_path)
    session_factory = build_session_factory(engine)
    puerto = StagedEnginePort(
        session_factory, engine, ejes_por_identidad={identidad: ejes_declarados}
    )
    try:
        (encontrado,) = puerto.por_termino_lexico(["terminounicoconejes"])
    finally:
        puerto.close()

    assert encontrado.ejes == ejes_declarados


# -- ADR-165: los ejes que el puerto deriva de lo que el esquema ya guarda ----

#: Instantes fijos, escritos en la forma en que SQLite guarda un `DateTime`
#: de SQLAlchemy (`AAAA-MM-DD hh:mm:ss.ffffff`). Se fuerzan con `UPDATE` para
#: que cada prueba diga de qué COLUMNA sale el eje, no qué hora era.
_REGISTRO_ANTIGUO = "2020-01-01 00:00:00.000000"
_REVISION_VIGENTE = "2026-03-05 07:08:09.123456"
_APROBACION = "2026-04-02 05:06:07.891011"
_SUSTITUCION = "2026-05-06 07:08:09.246810"


def _ejecutar(database_path: Path, sql: str, **parametros: object) -> None:
    engine = build_engine(database_path)
    try:
        with session_scope(build_session_factory(engine)) as session:
            session.execute(text(sql), parametros)
    finally:
        engine.dispose()


def _entregado(database_path: Path, identidad: str) -> ItemCanonico:
    """El item tal como el camino REAL del producto lo entrega."""
    puerto = build_staged_engine_port(database_path)
    try:
        materializacion = puerto.por_identificadores([identidad])
    finally:
        puerto.close()
    (item,) = materializacion.items
    return item


def _memoria(database_path: Path, contenido: str, origen: str = MANUAL_MEMORY_ORIGIN) -> str:
    memoria = build_sqlite_memory_repository(database_path).create_memory(contenido, origen)
    return f"{Clase.MEMORIA.value}:{memoria.id}"


def _proyecto(database_path: Path) -> int:
    proyecto = build_sqlite_project_repository(database_path).create_project(
        "proyecto de prueba", "objetivo", state_summary="", blockers=(), next_step=""
    )
    return proyecto.id


def _candidata(item: ItemCanonico) -> Candidata:
    return Candidata(
        item=item,
        etapa=Etapa.E1,
        lectura=LecturaSemantica(
            sujeto=item.subject_key or "asunto",
            polaridad=Polaridad.AFIRMATIVA,
            condicion=None,
            tiempo=item.created_at,
            medio="prueba",
        ),
        razon="coincidencia de prueba",
        senal="prueba",
    )


def _peticion(tiempo_objetivo: str) -> Peticion:
    return Peticion(
        operation_id="adr165",
        consulta="lo que sea",
        proposito="prueba",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=True, proyectos=()),
        ventana=VentanaTemporal(tiempo_objetivo=tiempo_objetivo),
        cardinalidad=Cardinalidad.EXHAUSTIVA,
        limite_objetivo=100,
        limite_duro=100,
    )


def test_un_item_real_del_camino_de_produccion_llega_con_sus_ejes_derivados(
    tmp_path: Path,
) -> None:
    """El caso de aceptación de la incidencia #572.

    Visto FALLAR contra el árbol anterior a ADR-165, donde
    `build_staged_engine_port` no poblaba `ejes_por_identidad` y todo item
    real llegaba con `SIN_EJES`.
    """
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    identidad = _memoria(database_path, "el faro abre a las nueve")

    item = _entregado(database_path, identidad)

    assert item.ejes != SIN_EJES
    assert item.ejes.valid_from is not None
    assert item.ejes.autoridad == "ACTO_EXPLICITO_USUARIO"


def test_el_valid_from_de_un_recuerdo_sale_de_su_revision_vigente(tmp_path: Path) -> None:
    """De la REVISIÓN, no de la fila del recuerdo: es el instante en que
    entró en vigor el contenido que el puerto entrega."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    identidad = _memoria(database_path, "el faro abre a las nueve")
    _ejecutar(database_path, "UPDATE memories SET created_at = :t", t=_REGISTRO_ANTIGUO)
    _ejecutar(database_path, "UPDATE memory_revisions SET created_at = :t", t=_REVISION_VIGENTE)

    item = _entregado(database_path, identidad)

    assert item.ejes.valid_from == "2026-03-05T07:08:09.123456Z"
    assert item.created_at == _REGISTRO_ANTIGUO


def test_un_recuerdo_sin_instante_legible_en_su_revision_no_recibe_valid_from(
    tmp_path: Path,
) -> None:
    """Falta el dato del que sale el eje: el eje queda SIN DERIVAR."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    identidad = _memoria(database_path, "el faro abre a las nueve")
    _ejecutar(database_path, "UPDATE memory_revisions SET created_at = ''")

    item = _entregado(database_path, identidad)

    assert item.ejes.valid_from is None
    # Y no se arrastra al resto: la autoridad, cuyo dato sí está, se deriva.
    assert item.ejes.autoridad == "ACTO_EXPLICITO_USUARIO"


def test_un_recuerdo_nunca_recibe_valid_to(tmp_path: Path) -> None:
    """Sirius 0.1 no sustituye recuerdos: una corrección crea una revisión
    nueva y el puerto entrega la vigente, que no tiene fin."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    identidad = _memoria(database_path, "el faro abre a las nueve")
    repositorio = build_sqlite_memory_repository(database_path)
    repositorio.correct_memory(
        int(identidad.split(":")[1]), "el faro abre a las diez", MEMORY_CORRECTION_ORIGIN
    )

    item = _entregado(database_path, identidad)

    assert item.ejes.valid_to is None
    assert item.ejes.autoridad == "ACTO_EXPLICITO_USUARIO"


@pytest.mark.parametrize(
    ("origen", "autoridad"),
    [
        (MANUAL_MEMORY_ORIGIN, "ACTO_EXPLICITO_USUARIO"),
        (MEMORY_CORRECTION_ORIGIN, "ACTO_EXPLICITO_USUARIO"),
        (CONFIRMED_MEMORY_SUGGESTION_ORIGIN, "INFORMAL"),
    ],
)
def test_la_autoridad_de_un_recuerdo_sale_del_origen_de_su_revision(
    tmp_path: Path, origen: str, autoridad: str
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    identidad = _memoria(database_path, "el faro abre a las nueve", origen)

    assert _entregado(database_path, identidad).ejes.autoridad == autoridad


def test_un_origen_que_el_producto_no_escribe_no_recibe_autoridad(tmp_path: Path) -> None:
    """Falta el dato del que sale el eje —el origen no está en la tabla
    cerrada—: sin derivar, no un valor por defecto."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    identidad = _memoria(database_path, "el faro abre a las nueve", "importado de otra parte")

    item = _entregado(database_path, identidad)

    assert item.ejes.autoridad is None
    assert item.ejes.valid_from is not None


def test_la_tabla_de_autoridad_cubre_los_tres_origenes_del_producto() -> None:
    """El guardián que hace IMPOSIBLE que renombrar un origen deje la tabla
    muda sin que nadie se entere: el adaptador no importa la capa de
    aplicación, así que sin esta prueba la coincidencia sería casualidad."""
    assert set(AUTORIDAD_POR_ORIGEN) == {
        MANUAL_MEMORY_ORIGIN,
        MEMORY_CORRECTION_ORIGIN,
        CONFIRMED_MEMORY_SUGGESTION_ORIGIN,
    }


def test_el_valid_from_de_una_decision_aprobada_es_el_instante_de_la_aprobacion(
    tmp_path: Path,
) -> None:
    """De `updated_at` (la transición a APPROVED), no de `created_at`:
    proponer no es aprobar."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repositorio = build_sqlite_decision_repository(database_path)
    decision = repositorio.create_proposal("aforo", _proyecto(database_path), "el aforo es 40")
    repositorio.approve_decision(decision.id)
    _ejecutar(
        database_path,
        "UPDATE decisions SET created_at = :c, updated_at = :u",
        c=_REGISTRO_ANTIGUO,
        u=_APROBACION,
    )

    item = _entregado(database_path, f"{Clase.DECISION.value}:{decision.id}")

    assert item.ejes.valid_from == "2026-04-02T05:06:07.891011Z"
    assert item.created_at == _REGISTRO_ANTIGUO


def test_una_decision_aprobada_sin_sustitucion_no_recibe_valid_to(tmp_path: Path) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repositorio = build_sqlite_decision_repository(database_path)
    decision = repositorio.create_proposal("aforo", _proyecto(database_path), "el aforo es 40")
    repositorio.approve_decision(decision.id)

    item = _entregado(database_path, f"{Clase.DECISION.value}:{decision.id}")

    assert item.ejes.valid_to is None


def test_una_decision_propuesta_no_recibe_ventana_de_vigencia(tmp_path: Path) -> None:
    """Nunca se aprobó: `updated_at` es el sello de la propuesta y no dice
    desde cuándo aplica, así que la ventana entera queda sin derivar."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    decision = build_sqlite_decision_repository(database_path).create_proposal(
        "aforo", _proyecto(database_path), "el aforo es 40"
    )

    item = _entregado(database_path, f"{Clase.DECISION.value}:{decision.id}")

    assert item.ejes == SIN_EJES


def test_una_decision_sustituida_recibe_valid_to_de_la_sustitucion_y_no_valid_from(
    tmp_path: Path,
) -> None:
    """El sello de la decisión SUSTITUIDA es el de la sustitución. El de su
    aprobación ya no se persiste, y `created_at` no lo sustituye."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project_id = _proyecto(database_path)
    repositorio = build_sqlite_decision_repository(database_path)
    vieja = repositorio.create_proposal("aforo", project_id, "el aforo es 40")
    repositorio.approve_decision(vieja.id)
    nueva = repositorio.create_proposal("aforo", project_id, "el aforo es 25")
    repositorio.supersede_decision(vieja.id, nueva.id)
    _ejecutar(
        database_path,
        "UPDATE decisions SET created_at = :c, updated_at = :u WHERE id = :i",
        c=_REGISTRO_ANTIGUO,
        u=_SUSTITUCION,
        i=vieja.id,
    )

    item = _entregado(database_path, f"{Clase.DECISION.value}:{vieja.id}")

    assert item.ejes.valid_to == "2026-05-06T07:08:09.246810Z"
    assert item.ejes.valid_from is None


def test_una_decision_archivada_deja_la_ventana_sin_derivar(tmp_path: Path) -> None:
    """`updated_at` pasa a ser el sello del ARCHIVADO, que no es ni la
    aprobación ni una sustitución."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repositorio = build_sqlite_decision_repository(database_path)
    decision = repositorio.create_proposal("aforo", _proyecto(database_path), "el aforo es 40")
    repositorio.approve_decision(decision.id)
    repositorio.archive_decision(decision.id)

    item = _entregado(database_path, f"{Clase.DECISION.value}:{decision.id}")

    assert item.ejes == SIN_EJES


def test_una_decision_nunca_recibe_autoridad(tmp_path: Path) -> None:
    """`decision_revisions` no guarda `origin`: la autoridad no se deduce de
    la clase, que sería deducirla de otra cosa que del origen."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repositorio = build_sqlite_decision_repository(database_path)
    decision = repositorio.create_proposal("aforo", _proyecto(database_path), "el aforo es 40")
    repositorio.approve_decision(decision.id)

    assert _entregado(database_path, f"{Clase.DECISION.value}:{decision.id}").ejes.autoridad is None


def test_los_ejes_que_el_esquema_no_guarda_siguen_sin_declararse(tmp_path: Path) -> None:
    """ADR-165 deriva tres ejes y ni uno más: lo que el esquema no sabe se
    queda en `None`, y `declarados` sigue siendo `False` porque mira
    `confirmacion`/`validez`, que nadie declara en el camino real."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    identidad = _memoria(database_path, "el faro abre a las nueve")

    ejes = _entregado(database_path, identidad).ejes

    assert ejes.confirmacion is None
    assert ejes.validez is None
    assert ejes.disponibilidad is None
    assert ejes.sensibilidad is None
    assert ejes.ambito is None
    assert ejes.no_usar_como_memoria is None
    assert ejes.no_consolidable is None
    assert ejes.procedencia == ()
    assert ejes.miembros_de_ambito == ()
    assert ejes.declarados is False


def test_el_registro_se_canoniza_a_la_forma_con_la_que_g8_lo_compara(tmp_path: Path) -> None:
    """`G8` compara el corte de registro con `created_at` como CADENAS, y
    ADR-164 emite el corte como `AAAA-MM-DD 23:59:59.999999`. Una fila sin
    microsegundos sale canonizada a esa forma; escrita con `T` y `Z` —la
    forma que este puerto NO emite para el registro— la comparación se
    invertiría."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    identidad = _memoria(database_path, "el faro abre a las nueve")
    _ejecutar(database_path, "UPDATE memories SET created_at = '2026-03-01 00:00:00'")
    corte_de_ADR_164 = "2026-03-01 23:59:59.999999"

    item = _entregado(database_path, identidad)

    assert item.created_at == "2026-03-01 00:00:00.000000"
    assert item.created_at <= corte_de_ADR_164
    sin_canonizar = "2026-03-01T00:00:00Z"
    assert sin_canonizar > corte_de_ADR_164


def test_un_registro_ilegible_pasa_verbatim_y_no_se_inventa(tmp_path: Path) -> None:
    """Degradar a lo que el puerto entregaba antes de ADR-165 es honesto;
    escribir un instante que la fila no dice, no."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    identidad = _memoria(database_path, "el faro abre a las nueve")
    _ejecutar(database_path, "UPDATE memories SET created_at = 'no es una fecha'")

    assert _entregado(database_path, identidad).created_at == "no es una fecha"


def test_g8_admite_en_la_frontera_exacta_el_valid_from_que_este_puerto_emite(
    tmp_path: Path,
) -> None:
    """La razón por la que la vigencia sale con `Z` y grano de segundo: con
    fracción, `"…:00.000000Z"` ordena ANTES que `"…:00Z"` y el veredicto de
    la frontera se invierte."""
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    repositorio = build_sqlite_decision_repository(database_path)
    decision = repositorio.create_proposal("aforo", _proyecto(database_path), "el aforo es 40")
    repositorio.approve_decision(decision.id)
    _ejecutar(database_path, "UPDATE decisions SET updated_at = :u", u=_APROBACION)
    item = _entregado(database_path, f"{Clase.DECISION.value}:{decision.id}")
    frontera = item.ejes.valid_from
    assert frontera == "2026-04-02T05:06:07.891011Z"

    en_la_frontera = gates.aplicar_previas([_candidata(item)], _peticion(frontera))
    un_segundo_antes = gates.aplicar_previas(
        [_candidata(item)], _peticion("2026-04-02T05:06:06.000000Z")
    )

    assert en_la_frontera.admitidas == (_candidata(item),)
    assert (item.id, "G8", "aun no vigente en el tiempo objetivo") in un_segundo_antes.descartes
    # Y contra el otro ancho de tiempo objetivo que hoy existe —el respaldo
    # «ahora» de `InterpreteDePeticion`, que lleva fracción— el mismo item
    # sigue admitido; truncado al segundo saldría «aún no vigente», que es la
    # razón por la que este puerto emite los seis dígitos siempre.
    objetivo_con_fraccion = "2026-04-02T05:06:07.891012Z"
    truncado_al_segundo = "2026-04-02T05:06:07Z"
    assert frontera is not None
    assert frontera < objetivo_con_fraccion
    assert truncado_al_segundo > objetivo_con_fraccion


def test_g8_da_por_expirado_en_la_frontera_exacta_el_valid_to_que_este_puerto_emite(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "sirius.db"
    _bootstrap(database_path)
    project_id = _proyecto(database_path)
    repositorio = build_sqlite_decision_repository(database_path)
    vieja = repositorio.create_proposal("aforo", project_id, "el aforo es 40")
    repositorio.approve_decision(vieja.id)
    nueva = repositorio.create_proposal("aforo", project_id, "el aforo es 25")
    repositorio.supersede_decision(vieja.id, nueva.id)
    _ejecutar(
        database_path,
        "UPDATE decisions SET updated_at = :u WHERE id = :i",
        u=_SUSTITUCION,
        i=vieja.id,
    )
    item = _entregado(database_path, f"{Clase.DECISION.value}:{vieja.id}")
    frontera = item.ejes.valid_to
    assert frontera == "2026-05-06T07:08:09.246810Z"

    en_la_frontera = gates.aplicar_previas([_candidata(item)], _peticion(frontera))
    un_segundo_antes = gates.aplicar_previas(
        [_candidata(item)], _peticion("2026-05-06T07:08:08.000000Z")
    )

    assert (item.id, "G8", "vigencia expirada en el tiempo objetivo") in en_la_frontera.descartes
    assert not any(puerta == "G8" for _i, puerta, _m in un_segundo_antes.descartes)
    # Contra un tiempo objetivo SIN fracción del mismo segundo, la forma
    # emitida ordena inmediatamente antes —el `.` (0x2E) va antes que la `Z`
    # (0x5A)—, que en `valid_to` es dar por terminada la vigencia: el lado
    # seguro para una decisión ya sustituida.
    objetivo_sin_fraccion = "2026-05-06T07:08:09Z"
    assert frontera is not None
    assert frontera <= objetivo_sin_fraccion
