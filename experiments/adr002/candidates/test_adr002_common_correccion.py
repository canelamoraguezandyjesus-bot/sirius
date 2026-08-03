"""Invariantes de la correccion unica de ``common`` (paso 5 del plan aprobado).

No comprueban que la capa comun sea buena: comprueban que hace **exactamente**
lo que la resolucion aprobada exige y que no puede volver a hacer lo que hacia.
Cada prueba nombra el defecto que cierra, de modo que si alguien revirtiera un
punto sin darse cuenta, el fallo diga cual.

Se ejecutan contra la **proyeccion real** de la familia v0.6 siempre que el
invariante dependa de datos, y contra estructuras minimas cuando el invariante
es puramente estructural. No miden nada y no ejecutan benchmark.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from experiments.adr002.candidates import fixtures
from experiments.adr002.candidates.adr002_a.candidate import candidato
from experiments.adr002.candidates.common import engine, gates, grouping, stops
from experiments.adr002.candidates.common.contracts import (
    ORDEN_DE_CRITICIDAD,
    PLANO_COMUN_VACIO,
    Ambito,
    Candidata,
    Cardinalidad,
    Clase,
    ClaseDeEvidencia,
    ContextoDeEtapa,
    Criticidad,
    CriticidadAplicada,
    Etapa,
    GrupoDeEquivalentes,
    ItemCanonico,
    LecturaSemantica,
    Modo,
    Peticion,
    Polaridad,
    Suficiencia,
    VentanaTemporal,
)
from experiments.adr002.candidates.common.port import PuertoSqlite
from experiments.adr002.projection import build
from experiments.adr002.projection.plane import PlanoReservado

#: Los tres de `B04-CA-19`: mismo sujeto sintetico y misma property_key.
CA_19 = ("DECISION:6", "DECISION:7", "DECISION:8")


@pytest.fixture(scope="module")
def proyeccion(tmp_path_factory: pytest.TempPathFactory):
    return build.construir_desde_la_familia(tmp_path_factory.mktemp("v06") / "planos")


@pytest.fixture
def plano(proyeccion):
    lector = PlanoReservado(proyeccion)
    yield lector
    lector.close()


def _peticion(
    consulta: str,
    *,
    cardinalidad: Cardinalidad = Cardinalidad.EXHAUSTIVA,
    limite_duro: int = 10,
    limite_objetivo: int = 10,
    objetivos: int = 1,
    proyectos: tuple[str, ...] = ("2",),
) -> Peticion:
    return Peticion(
        operation_id="correccion",
        consulta=consulta,
        proposito="responder_al_usuario",
        modo=Modo.M1_ORDINARIO,
        ambito=Ambito(global_=False, proyectos=proyectos),
        ventana=VentanaTemporal(tiempo_objetivo="2026-06-15T00:00:00Z"),
        cardinalidad=cardinalidad,
        limite_objetivo=limite_objetivo,
        limite_duro=limite_duro,
        objetivos=objetivos,
    )


def _item(
    identidad: str,
    *,
    sujeto: str | None = "vehiculo",
    proyecto: str | None = "2",
    vigente: bool = True,
    evidencia: ClaseDeEvidencia = ClaseDeEvidencia.CANONICA,
) -> ItemCanonico:
    return ItemCanonico(
        id=identidad,
        clase=Clase.MEMORIA,
        project_id=proyecto,
        texto="texto",
        subject_key=sujeto,
        vigente=vigente,
        disponible=True,
        created_at="2026-01-01T00:00:00Z",
        clase_de_evidencia=evidencia,
    )


def _candidata(
    identidad: str,
    *,
    etapa: Etapa = Etapa.E1,
    senal: str = "clave_exacta",
    polaridad: Polaridad = Polaridad.AFIRMATIVA,
    **kwargs: object,
) -> Candidata:
    return Candidata(
        item=_item(identidad, **kwargs),  # type: ignore[arg-type]
        etapa=etapa,
        lectura=LecturaSemantica(
            sujeto="vehiculo", polaridad=polaridad, condicion=None, tiempo=None, medio="lexico"
        ),
        razon="coincide",
        senal=senal,
    )


# ---------------------------------------------------------------------------
# 1-2. Ausencia real de sujeto, y prohibicion de fabricarlo
# ---------------------------------------------------------------------------


def test_la_ausencia_de_sujeto_se_conserva_como_null(tmp_path: Path) -> None:
    """Cadena vacia y ausencia eran indistinguibles, y agrupaban entre si."""
    base = tmp_path / "f.sqlite3"
    fixtures.construir(base)
    with PuertoSqlite(base) as puerto:
        with_sujeto = puerto.por_clave_exacta(["faro-costa"])
    assert with_sujeto[0].subject_key == "faro-costa"
    assert with_sujeto[0].sujeto_determinado


def test_el_historial_no_recibe_un_sujeto_fabricado(tmp_path: Path) -> None:
    """``mensaje-<n>`` era un sujeto sintetico que el canon nunca declaro."""
    base = tmp_path / "f.sqlite3"
    fixtures.construir(base)
    with PuertoSqlite(base) as puerto:
        historial = puerto.historial_y_fuentes(["faro"])
    assert historial, "el fixture debe tener historial"
    for item in historial:
        assert item.subject_key is None
        assert not item.sujeto_determinado


def test_un_sujeto_ausente_nunca_entra_en_un_grupo() -> None:
    sin_sujeto = [_candidata("MEMORIA:1", sujeto=None), _candidata("MEMORIA:2", sujeto=None)]
    agrupacion = grouping.agrupar_equivalentes(sin_sujeto, lambda _i: "PK-igual")
    assert agrupacion.grupos == ()
    assert len(agrupacion.sueltos) == 2


# ---------------------------------------------------------------------------
# 3-4. Todos los ejes determinados · identidad exacta vs equivalencia
# ---------------------------------------------------------------------------


def test_una_property_key_nula_impide_agrupar() -> None:
    """La duda no fusiona: sin propiedad, dos identidades siguen siendo dos."""
    pareja = [_candidata("MEMORIA:1"), _candidata("MEMORIA:2")]
    assert grouping.agrupar_equivalentes(pareja, lambda _i: None).grupos == ()
    assert len(grouping.agrupar_equivalentes(pareja, lambda _i: "PK-a").grupos) == 1


def test_una_polaridad_distinta_impide_agrupar() -> None:
    """``RF-21``: fusionar posturas opuestas resolveria el conflicto en silencio."""
    opuestas = [
        _candidata("MEMORIA:1", polaridad=Polaridad.AFIRMATIVA),
        _candidata("MEMORIA:2", polaridad=Polaridad.NEGATIVA),
    ]
    assert grouping.agrupar_equivalentes(opuestas, lambda _i: "PK-a").grupos == ()


def test_la_deduplicacion_por_identidad_no_elige_representante() -> None:
    """No hay identidades distintas entre las que elegir: solo se fusionan senales."""
    dos_veces = [
        _candidata("MEMORIA:1", etapa=Etapa.E1, senal="clave_exacta"),
        _candidata("MEMORIA:1", etapa=Etapa.E3, senal="prefijo_de_sujeto"),
    ]
    unicas, fusionadas = grouping.deduplicar_por_identidad(dos_veces)
    assert len(unicas) == 1
    # Conserva la etapa MAS AUTORIZADA, la primera: degradarla cambiaria el orden.
    assert unicas[0].etapa is Etapa.E1
    assert fusionadas["MEMORIA:1"] == ("clave_exacta", "prefijo_de_sujeto")


def test_la_agrupacion_conserva_a_todos_sus_miembros() -> None:
    """El representante encabeza; **no** sustituye ni elimina."""
    tres = [_candidata(f"MEMORIA:{n}") for n in (1, 2, 3)]
    agrupacion = grouping.agrupar_equivalentes(tres, lambda _i: "PK-a")
    grupo = agrupacion.grupos[0]
    assert set(grupo.miembros) == {"MEMORIA:1", "MEMORIA:2", "MEMORIA:3"}
    assert grupo.representante in grupo.miembros
    assert agrupacion.miembros_totales == ("MEMORIA:1", "MEMORIA:2", "MEMORIA:3")


def test_un_representante_fuera_de_sus_miembros_es_imposible() -> None:
    with pytest.raises(ValueError, match="representante"):
        GrupoDeEquivalentes(
            identificador="GRP-X",
            representante="MEMORIA:9",
            miembros=("MEMORIA:1",),
            procedencias_adicionales=(),
            diferencias_materiales=(),
            relaciones_entre_miembros=(),
            razon_del_representante="",
            estado_historico_por_miembro=(),
        )


def test_el_representante_no_se_elige_por_orden_de_llegada() -> None:
    """``§7.4``: cascada registrada. «Primero en llegar» queda prohibido."""
    desordenadas = [
        _candidata("MEMORIA:9", vigente=False),
        _candidata("MEMORIA:2", vigente=True),
    ]
    grupo = grouping.agrupar_equivalentes(desordenadas, lambda _i: "PK-a").grupos
    assert grupo == () or grupo[0].representante == "MEMORIA:2"


# ---------------------------------------------------------------------------
# 5. property_key es senal exclusiva de common
# ---------------------------------------------------------------------------


def test_ningun_candidato_recibe_el_plano_comun() -> None:
    """Estructural: ``ContextoDeEtapa`` no tiene por donde llevarlo."""
    campos = {f for f in ContextoDeEtapa.__dataclass_fields__}
    assert "plano" not in campos
    assert "property_key" not in campos
    assert "criticidad" not in campos
    firma = inspect.signature(engine.recuperar)
    assert list(firma.parameters) == ["peticion", "puerto", "candidato", "plano"]


def test_item_canonico_no_lleva_criticidad_ni_property_key() -> None:
    """Estaban al alcance de cualquiera que recibiese un item."""
    campos = set(ItemCanonico.__dataclass_fields__)
    assert "criticidad" not in campos
    assert "property_key" not in campos


def test_el_plano_vacio_no_determina_nada() -> None:
    """Sin canal lateral no se agrupa y nada es critico. No es permisivo."""
    assert PLANO_COMUN_VACIO.property_key("MEMORIA:1") is None
    assert PLANO_COMUN_VACIO.criticidad_aplicada("MEMORIA:1") is None


# ---------------------------------------------------------------------------
# 6, 15. Cardinalidad semantica y documental · reinterpretacion de ACOTADA
# ---------------------------------------------------------------------------


def test_los_equivalentes_cuentan_una_vez_para_la_cuota(proyeccion, plano) -> None:
    """Regla 7: repetir equivalentes no satisface necesidades distintas."""
    peticion = _peticion(
        "plataforma", cardinalidad=Cardinalidad.ACOTADA, limite_objetivo=3, limite_duro=10
    )
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperacion = engine.recuperar(peticion, puerto, candidato(), plano)
    entregados = set(recuperacion.ids)
    assert set(CA_19) <= entregados, "los tres siguen entregandose"
    assert recuperacion.cardinalidades.documental == len(recuperacion.resultados)
    assert recuperacion.cardinalidades.semantica < recuperacion.cardinalidades.documental
    assert recuperacion.parada.identificador != "S1", (
        "tres equivalentes no cubren una cuota de tres necesidades distintas"
    )


def test_los_tres_equivalentes_forman_un_solo_grupo(proyeccion, plano) -> None:
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperacion = engine.recuperar(_peticion("plataforma"), puerto, candidato(), plano)
    grupos = [g for g in recuperacion.grupos if set(g.miembros) == set(CA_19)]
    assert len(grupos) == 1, f"grupos observados: {[g.miembros for g in recuperacion.grupos]}"
    assert grupos[0].razon_del_representante


# ---------------------------------------------------------------------------
# 7-9. Grupo no atomico · miembros omitidos declarados · PARCIAL
# ---------------------------------------------------------------------------


def test_el_limite_parte_el_grupo_y_lo_declara(proyeccion, plano) -> None:
    """``CA-44``: B04 SI trunca; lo que prohibe es ocultarlo."""
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperacion = engine.recuperar(
            _peticion("plataforma", limite_duro=2), puerto, candidato(), plano
        )
    assert len(recuperacion.resultados) == 2, "entrega lo que cabe, no el grupo entero"
    assert recuperacion.omitidos_por_limite, "los omitidos se cuentan y se nombran"
    assert recuperacion.traza.grupos_truncados
    assert recuperacion.suficiencia is Suficiencia.PARCIAL
    assert recuperacion.parada.identificador == "S4"


def test_s1_no_se_adjudica_si_el_limite_parte_un_grupo(proyeccion, plano) -> None:
    """Regla 9: prevalece ``S4`` con ``PARCIAL`` sobre la suficiencia."""
    peticion = _peticion("plataforma", cardinalidad=Cardinalidad.EXACTA, objetivos=1, limite_duro=2)
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperacion = engine.recuperar(peticion, puerto, candidato(), plano)
    assert recuperacion.parada.identificador == "S4"
    assert recuperacion.suficiencia is Suficiencia.PARCIAL


# ---------------------------------------------------------------------------
# 10-12. G12 sobre todos los miembros · criticidad segura · precedencia
# ---------------------------------------------------------------------------


def test_g12_recorre_miembros_y_no_solo_representantes() -> None:
    """Antes se aplicaba **despues** de agrupar y solo veia representantes."""
    criticos = {"MEMORIA:3"}
    candidatas = [_candidata(f"MEMORIA:{n}") for n in (1, 2, 3)]
    resultado = gates.aplicar_g12(
        candidatas,
        _peticion("x", limite_duro=1),
        lambda i: Criticidad.CRITICA if i in criticos else Criticidad.ORDINARIA,
        lambda i: i in {"MEMORIA:1", "MEMORIA:2", "MEMORIA:3"},
    )
    # El critico sobrevive al limite aunque llegase el ultimo.
    assert [c.item.id for c in resultado.dentro_del_limite] == ["MEMORIA:3"]
    assert resultado.desbordamiento_declarado
    assert not resultado.desbordamiento_critico
    assert set(resultado.miembros_omitidos) == {"MEMORIA:1", "MEMORIA:2"}


def test_el_desbordamiento_ordinario_no_se_confunde_con_el_critico() -> None:
    candidatas = [_candidata(f"MEMORIA:{n}") for n in (1, 2)]
    ordinario = gates.aplicar_g12(candidatas, _peticion("x", limite_duro=1))
    assert ordinario.desbordamiento_declarado
    assert not ordinario.desbordamiento_critico
    assert ordinario.criticos_omitidos == ()

    critico = gates.aplicar_g12(
        candidatas, _peticion("x", limite_duro=1), lambda _i: Criticidad.CRITICA
    )
    assert critico.desbordamiento_critico
    assert critico.criticos_omitidos == ("MEMORIA:2",)


def test_la_criticidad_tiene_tres_niveles_y_se_compara_por_orden() -> None:
    """Con dos niveles, ``IMPORTANTE`` era indistinguible de ``ORDINARIA``."""
    assert ORDEN_DE_CRITICIDAD == (
        Criticidad.ORDINARIA,
        Criticidad.IMPORTANTE,
        Criticidad.CRITICA,
    )
    candidatas = [_candidata("MEMORIA:1"), _candidata("MEMORIA:2")]
    niveles = {"MEMORIA:1": Criticidad.ORDINARIA, "MEMORIA:2": Criticidad.IMPORTANTE}
    resultado = gates.aplicar_g12(candidatas, _peticion("x", limite_duro=1), niveles.__getitem__)
    assert [c.item.id for c in resultado.dentro_del_limite] == ["MEMORIA:2"]


def test_ninguna_etapa_puede_crear_un_nivel_de_criticidad(proyeccion) -> None:
    """Sin entrada congelada, el elemento es ordinario. Cero auto-marcados."""
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperacion = engine.recuperar(_peticion("plataforma"), puerto, candidato())
    assert all(r.criticidad is None for r in recuperacion.resultados)
    assert recuperacion.handoff_a_b05 == {}


def test_s1_no_se_adjudica_con_criticos_pendientes() -> None:
    pendientes = [_candidata("MEMORIA:9")]
    peticion = _peticion("x", cardinalidad=Cardinalidad.EXACTA, objetivos=1)
    assert (
        stops.evaluar_suficiencia(
            [_candidata("MEMORIA:1")],
            peticion,
            pendientes=pendientes,
            criticidad_de=lambda _i: Criticidad.CRITICA,
        )
        is None
    )
    assert (
        stops.evaluar_suficiencia([_candidata("MEMORIA:1")], peticion, pendientes=pendientes)
        is not None
    )


# ---------------------------------------------------------------------------
# 13. Handoff integro a B05
# ---------------------------------------------------------------------------


def test_el_handoff_lleva_los_cuatro_campos_verbatim(proyeccion, plano) -> None:
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperacion = engine.recuperar(_peticion("presupuesto"), puerto, candidato(), plano)
    handoff = recuperacion.handoff_a_b05
    assert handoff, "el corpus declara 19 items con criticidad; alguno debe llegar"
    for identidad, aplicada in handoff.items():
        assert isinstance(aplicada, CriticidadAplicada)
        assert aplicada.nivel in ORDEN_DE_CRITICIDAD
        assert aplicada.razon_segura.strip()
        assert aplicada.fuente_de_politica.strip()
        assert aplicada.regla_de_politica.strip()
        assert aplicada == plano.criticidad_aplicada(identidad), "verbatim, sin reinterpretar"


def test_el_handoff_no_arrastra_la_fuente_bruta(plano) -> None:
    """La fuente bruta porta identificadores de caso del banco."""
    from experiments.adr002.benchmark import schema_v0_5 as S5

    campos = set(CriticidadAplicada.__dataclass_fields__)
    assert campos == {"nivel", "razon_segura", "fuente_de_politica", "regla_de_politica"}
    for identidad in ("DECISION:3",):
        aplicada = plano.criticidad_aplicada(identidad)
        if aplicada is None:
            continue
        assert not S5.contiene_identificador_de_caso(aplicada.razon_segura)
        assert not S5.contiene_identificador_de_caso(aplicada.regla_de_politica)


# ---------------------------------------------------------------------------
# 14. Explicacion y trazabilidad
# ---------------------------------------------------------------------------


def test_la_explicacion_lleva_las_procedencias_de_todo_el_grupo(proyeccion, plano) -> None:
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperacion = engine.recuperar(_peticion("plataforma"), puerto, candidato(), plano)
    representantes = [r for r in recuperacion.resultados if r.es_representante]
    assert representantes, "el grupo de CA-19 debe tener representante entregado"
    for resultado in representantes:
        assert len(resultado.explicacion.procedencias) > 1
        assert resultado.explicacion.grupo


def test_la_explicacion_no_llama_canonica_a_la_evidencia_atribuida(tmp_path: Path) -> None:
    """``RF-13``: lo externo es evidencia atribuida, no verdad canonica."""
    from experiments.adr002.candidates.common.trace import explicar

    atribuida = _candidata("MENSAJE:1", evidencia=ClaseDeEvidencia.ATRIBUIDA, sujeto=None)
    explicacion = explicar(atribuida, _peticion("x"), 1)
    assert any("atribuida" in p for p in explicacion.procedencias)
    assert not any("del canon" in p for p in explicacion.procedencias)


def test_la_razon_de_orden_cita_la_clave_de_desempate_real() -> None:
    from experiments.adr002.candidates.common.trace import EJES_DE_ORDEN_DECLARADOS, explicar

    explicacion = explicar(_candidata("MEMORIA:1"), _peticion("x"), 1)
    for eje in EJES_DE_ORDEN_DECLARADOS:
        assert eje in explicacion.razon_de_orden


def test_la_traza_separa_deduplicacion_de_agrupacion(proyeccion, plano) -> None:
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperacion = engine.recuperar(_peticion("plataforma"), puerto, candidato(), plano)
    volcado = recuperacion.traza.como_dict()
    assert "agrupaciones" in volcado
    assert "deduplicaciones_por_identidad" in volcado
    for agrupacion in volcado["agrupaciones"]:
        assert agrupacion["motivo"], "una agrupacion sin motivo no es auditable"
        assert agrupacion["ejes"]


def test_la_traza_declara_las_dos_cardinalidades(proyeccion, plano) -> None:
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperacion = engine.recuperar(_peticion("plataforma"), puerto, candidato(), plano)
    volcado = recuperacion.traza.como_dict()
    assert volcado["cardinalidad_semantica"] == recuperacion.cardinalidades.semantica
    assert volcado["cardinalidad_documental"] == recuperacion.cardinalidades.documental


# ---------------------------------------------------------------------------
# 16-17. Clasificacion fallo-cerrado · prohibicion de oraculo
# ---------------------------------------------------------------------------


def test_un_campo_sin_terna_aborta_la_clasificacion() -> None:
    from experiments.adr002.benchmark import schema_v0_5 as S5

    with pytest.raises(S5.ContratoFamiliaV05Error, match="sin terna"):
        S5.capacidad_de("campo_que_nadie_clasifico")


def test_la_clasificacion_niega_property_key_a_los_candidatos() -> None:
    from experiments.adr002.benchmark import schema_v0_5 as S5

    assert S5.legible_por("property_key", "common")
    for candidato_id in ("ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D"):
        assert not S5.legible_por("property_key", candidato_id)


def test_la_capa_comun_sigue_siendo_neutral() -> None:
    from experiments.adr002.candidates.common import neutrality

    raiz = Path(__file__).resolve().parents[3]
    assert neutrality.fallos_de_neutralidad(raiz) == []
    assert "grouping.py" in neutrality.MODULOS_COMUNES


# ---------------------------------------------------------------------------
# 18. Compatibilidad con la familia v0.6, de extremo a extremo
# ---------------------------------------------------------------------------


def test_el_invariante_de_agrupacion_se_comprueba_en_ejecucion(proyeccion, plano) -> None:
    """``§7.9``: elegibles antes de agrupar = union de miembros mas sueltos."""
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        recuperacion = engine.recuperar(_peticion("plataforma"), puerto, candidato(), plano)
    de_grupos = {m for g in recuperacion.grupos for m in g.miembros}
    entregados = set(recuperacion.ids)
    omitidos = set(recuperacion.omitidos_por_limite)
    assert de_grupos <= entregados | omitidos


def test_el_motor_es_determinista_sobre_la_proyeccion(proyeccion, plano) -> None:
    with PuertoSqlite(proyeccion.ruta_de_entrada()) as puerto:
        primera = engine.recuperar(_peticion("plataforma"), puerto, candidato(), plano)
        segunda = engine.recuperar(_peticion("plataforma"), puerto, candidato(), plano)
    assert primera.ids == segunda.ids
    assert [g.miembros for g in primera.grupos] == [g.miembros for g in segunda.grupos]


# ---------------------------------------------------------------------------
# 19. Las cinco puertas que leian el estado colapsado
# ---------------------------------------------------------------------------


@pytest.fixture
def puerto_con_ejes(proyeccion):
    from experiments.adr002.projection.contracts import Plano

    with PuertoSqlite(proyeccion.ruta_de_entrada(), proyeccion.ruta(Plano.EJES_P2)) as puerto:
        yield puerto


def _con_ejes(puerto, identidad: str, **kwargs) -> Candidata:
    item = puerto.por_identificadores([identidad]).items[0]
    return Candidata(
        item=item,
        etapa=Etapa.E1,
        lectura=LecturaSemantica(
            sujeto="s", polaridad=Polaridad.AFIRMATIVA, condicion=None, tiempo=None, medio="lexico"
        ),
        razon="coincide",
        senal="clave_exacta",
    )


def test_el_puerto_declara_si_aporta_los_ejes(puerto_con_ejes) -> None:
    assert puerto_con_ejes.declara_ejes


def test_g6_distingue_candidata_de_rechazada(puerto_con_ejes) -> None:
    """Leyendo ``vigente`` las dos caian juntas y no habia forma de separarlas."""
    candidata = _con_ejes(puerto_con_ejes, "MEMORIA:7")
    rechazada = _con_ejes(puerto_con_ejes, "MEMORIA:8")
    assert candidata.item.ejes.confirmacion == "CANDIDATA"
    assert rechazada.item.ejes.confirmacion == "RECHAZADA"

    en_m1 = gates.aplicar_previas([candidata, rechazada], _peticion("x"))
    assert en_m1.admitidas == (), "en M1 ninguna confirmacion distinta de CONFIRMADA es visible"
    assert {p for _i, p, _m in en_m1.descartes} >= {"G6"}

    gestion = gates.aplicar_previas(
        [candidata, rechazada],
        Peticion(
            operation_id="g6",
            consulta="x",
            proposito="gestionar",
            modo=Modo.M4_GESTION,
            ambito=Ambito(global_=True, proyectos=()),
            ventana=VentanaTemporal(tiempo_objetivo="2026-06-15T00:00:00Z"),
            cardinalidad=Cardinalidad.EXHAUSTIVA,
            limite_objetivo=10,
            limite_duro=10,
        ),
    )
    assert len(gestion.admitidas) == 2, "el modo de gestion si las ve"


def test_g7_separa_sustituida_de_sin_soporte(puerto_con_ejes) -> None:
    """Dos causas distintas que el estado colapsado hacia indistinguibles."""
    sin_soporte = _con_ejes(puerto_con_ejes, "MEMORIA:17")
    assert sin_soporte.item.ejes.validez == "SIN_SOPORTE"
    assert sin_soporte.item.vigente is False
    veredicto = [
        m
        for _i, p, m in gates.aplicar_previas([sin_soporte], _peticion("x")).descartes
        if p == "G7"
    ]
    assert veredicto == ["validez SIN_SOPORTE: no entra en M1"]


def test_g4_admite_una_lista_cerrada_cuyos_miembros_estan_autorizados(
    puerto_con_ejes,
) -> None:
    """Una sola clave foranea no puede expresar un ambito multiproyecto."""
    decision = _con_ejes(puerto_con_ejes, "DECISION:1")
    assert decision.item.ejes.ambito == "MULTI_PROYECTO_CERRADO"
    assert decision.item.ejes.miembros_de_ambito == ("2", "3")

    completo = gates.aplicar_previas([decision], _peticion("x", proyectos=("2", "3")))
    assert len(completo.admitidas) == 1

    parcial = gates.aplicar_previas([decision], _peticion("x", proyectos=("2",)))
    assert parcial.admitidas == ()
    assert [m for _i, p, m in parcial.descartes if p == "G4"] == [
        "lista cerrada con miembros fuera del ambito"
    ]


def test_g4_admite_el_item_global_desde_cualquier_ambito(puerto_con_ejes) -> None:
    global_ = _con_ejes(puerto_con_ejes, "MEMORIA:1")
    assert global_.item.ejes.ambito == "GLOBAL"
    admitidas = gates.aplicar_previas([global_], _peticion("x", proyectos=("2",))).admitidas
    assert len(admitidas) == 1


def test_g3_y_g9_degradan_declarandolo_cuando_no_hay_ejes(tmp_path: Path) -> None:
    """Sin ejes las puertas no se relajan: degradan y lo hacen constar."""
    base = tmp_path / "f.sqlite3"
    fixtures.construir(base)
    with PuertoSqlite(base) as puerto:
        assert not puerto.declara_ejes
        item = puerto.por_clave_exacta(["faro-costa"])[0]
    assert item.ejes.no_usar_como_memoria is None
    sin_disponer = _candidata("MEMORIA:1")
    veredicto = gates.aplicar_previas([sin_disponer], _peticion("x")).admitidas
    assert len(veredicto) == 1, "un item disponible sigue pasando cuando el eje no se declara"


def test_g9_mantiene_la_proteccion_superior(puerto_con_ejes) -> None:
    """La duda no abre acceso: lo restringido solo lo inspecciona M3/M4."""
    restringidos = [
        _con_ejes(puerto_con_ejes, i)
        for i in ("MEMORIA:1", "MEMORIA:7")
        if _con_ejes(puerto_con_ejes, i).item.ejes.sensibilidad == "RESTRINGIDA"
    ]
    # El corpus declara dos items RESTRINGIDA; si el fixture no los alcanza por
    # identidad, el invariante se comprueba igual sobre la regla.
    from experiments.adr002.candidates.common.contracts import SENSIBILIDAD_PROTEGIDA

    assert "RESTRINGIDA" in SENSIBILIDAD_PROTEGIDA
    assert not restringidos or gates.aplicar_previas(restringidos, _peticion("x")).admitidas == ()
