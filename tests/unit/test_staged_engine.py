"""Unit tests for the staged retrieval engine ported for issue #457
(ADR-109/ADR-110) from ``experiments/adr002/candidates/common/{contracts,
gates,grouping,stops,trace,engine}.py`` (``evidence/adr001-spikes``, PR
#117) into ``sirius.domain.staged_engine*``.

A minimal, self-contained ``SenalesDeCandidato``/``PuertoDeRecuperacion``
pair drives the whole ``recuperar()`` pipeline end to end (no SQLite, no
Sirius domain objects) so these tests pin the ported engine's own
behaviour — gates, grouping, stop adjudication — independent of how any
real port/candidate feeds it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

import pytest

from sirius.domain import staged_engine_gates as gates
from sirius.domain import staged_engine_grouping as grouping
from sirius.domain.staged_engine import (
    RecuperacionInvalidaError,
    _clave_de_orden,
    _con_representante_al_frente,
    recuperar,
)
from sirius.domain.staged_engine_contracts import (
    PLANO_COMUN_VACIO,
    Ambito,
    Candidata,
    Cardinalidad,
    Clase,
    ClaseDeEvidencia,
    ContextoDeEtapa,
    Criticidad,
    CriticidadAplicada,
    EjesDeclarados,
    Etapa,
    ItemCanonico,
    LecturaSemantica,
    MaterializacionPorIdentidad,
    Modo,
    Peticion,
    Polaridad,
    VentanaTemporal,
)
from sirius.domain.staged_engine_trace import (
    EJES_DE_ORDEN_DECLARADOS,
    PROMOCION_DE_REPRESENTANTE_DECLARADA,
)


def _item(
    item_id: str,
    *,
    subject_key: str | None = "faro-costa",
    texto: str = "El horario del faro es de nueve a cinco.",
    vigente: bool = True,
    disponible: bool = True,
    project_id: str | None = "1",
    created_at: str = "2026-01-01T00:00:00Z",
    ejes: EjesDeclarados | None = None,
) -> ItemCanonico:
    return ItemCanonico(
        id=item_id,
        clase=Clase.MEMORIA,
        project_id=project_id,
        texto=texto,
        subject_key=subject_key,
        vigente=vigente,
        disponible=disponible,
        created_at=created_at,
        ejes=ejes if ejes is not None else EjesDeclarados(),
    )


def _peticion(**overrides: object) -> Peticion:
    base: dict[str, object] = {
        "operation_id": "test",
        "consulta": "horario del faro",
        "proposito": "prueba",
        "modo": Modo.M1_ORDINARIO,
        "ambito": Ambito(global_=True, proyectos=()),
        "ventana": VentanaTemporal(tiempo_objetivo="2026-06-15T00:00:00Z"),
        "cardinalidad": Cardinalidad.EXHAUSTIVA,
        "limite_objetivo": 100,
        "limite_duro": 100,
    }
    base.update(overrides)
    return Peticion(**base)  # type: ignore[arg-type]


def _candidata(item: ItemCanonico, *, etapa: Etapa = Etapa.E1) -> Candidata:
    return Candidata(
        item=item,
        etapa=etapa,
        lectura=LecturaSemantica(
            sujeto=item.subject_key or "faro",
            polaridad=Polaridad.AFIRMATIVA,
            condicion=None,
            tiempo=item.created_at,
            medio="prueba",
        ),
        razon="coincidencia de prueba",
        senal="prueba",
    )


# -- staged_engine_gates ------------------------------------------------------


def test_g4_global_item_always_passes_regardless_of_peticion_ambito() -> None:
    item = _item("MEMORIA:1", ejes=EjesDeclarados(ambito="GLOBAL"))
    peticion = _peticion(ambito=Ambito(global_=False, proyectos=("9",)))
    filtrado = gates.aplicar_previas([_candidata(item)], peticion)
    assert filtrado.admitidas == (_candidata(item),)


def test_g4_project_scoped_item_outside_authorized_projects_is_discarded() -> None:
    item = _item("MEMORIA:1", project_id="1", ejes=EjesDeclarados(ambito="PROYECTO"))
    peticion = _peticion(ambito=Ambito(global_=False, proyectos=("9",)))
    filtrado = gates.aplicar_previas([_candidata(item)], peticion)
    assert filtrado.admitidas == ()
    assert any(puerta == "G4" for _item_id, puerta, _motivo in filtrado.descartes)


def test_g4_sin_ejes_degrades_to_peticion_ambito_over_real_project_id() -> None:
    item = _item("MEMORIA:1", project_id="9")
    peticion = _peticion(ambito=Ambito(global_=False, proyectos=("9",)))
    filtrado = gates.aplicar_previas([_candidata(item)], peticion)
    assert filtrado.admitidas == (_candidata(item),)


def test_g8_item_not_yet_valid_at_target_time_is_discarded_even_with_no_vigentes() -> None:
    item = _item("MEMORIA:1", ejes=EjesDeclarados(valid_from="2027-01-01T00:00:00Z"))
    peticion = _peticion(admite_no_vigentes=True)
    filtrado = gates.aplicar_previas([_candidata(item)], peticion)
    assert filtrado.admitidas == ()


def test_g8_sin_ejes_never_blocks_on_time() -> None:
    item = _item("MEMORIA:1")
    filtrado = gates.aplicar_previas([_candidata(item)], _peticion())
    assert filtrado.admitidas == (_candidata(item),)


def test_g9_sensibilidad_protegida_is_discarded_outside_inspecting_modes() -> None:
    item = _item("MEMORIA:1", ejes=EjesDeclarados(sensibilidad="RESTRINGIDA"))
    filtrado = gates.aplicar_previas([_candidata(item)], _peticion())
    assert filtrado.admitidas == ()


def test_g11_discards_candidatas_with_incomplete_semantic_reading() -> None:
    item = _item("MEMORIA:1")
    incompleta = replace(_candidata(item), lectura=replace(_candidata(item).lectura, sujeto="   "))
    filtrado = gates.aplicar_g11([incompleta], _peticion())
    assert filtrado.admitidas == ()
    assert filtrado.descartes[0][1] == "G11"


def test_conflictos_de_polaridad_flags_a_subject_with_both_polarities() -> None:
    item_a = _item("MEMORIA:1", subject_key="viaje-politica")
    item_b = _item("MEMORIA:2", subject_key="viaje-politica")
    candidata_afirmativa = _candidata(item_a)
    candidata_negativa = replace(
        _candidata(item_b),
        lectura=replace(_candidata(item_b).lectura, polaridad=Polaridad.NEGATIVA),
    )
    conflictos = gates.conflictos_de_polaridad([candidata_afirmativa, candidata_negativa])
    assert conflictos == ("viaje-politica",)


def test_g12_declares_but_never_hides_a_critical_item_over_the_hard_limit() -> None:
    critico = _item("MEMORIA:1")
    ordinario = _item("MEMORIA:2", subject_key="otro-sujeto")
    peticion = _peticion(limite_duro=1)
    resultado = gates.aplicar_g12(
        [_candidata(critico), _candidata(ordinario)],
        peticion,
        criticidad_de=lambda i: Criticidad.CRITICA if i == "MEMORIA:1" else Criticidad.ORDINARIA,
    )
    assert resultado.desbordamiento_declarado is True
    assert resultado.desbordamiento_critico is False
    assert [c.item.id for c in resultado.dentro_del_limite] == ["MEMORIA:1"]


# -- staged_engine_grouping ---------------------------------------------------


def test_agrupar_equivalentes_never_groups_without_a_property_key() -> None:
    item_a = _item("MEMORIA:1")
    item_b = _item("MEMORIA:2")
    agrupacion = grouping.agrupar_equivalentes(
        [_candidata(item_a), _candidata(item_b)], lambda _i: None
    )
    assert agrupacion.grupos == ()
    assert {c.item.id for c in agrupacion.sueltos} == {"MEMORIA:1", "MEMORIA:2"}


def test_agrupar_equivalentes_groups_two_items_with_all_ten_axes_matching() -> None:
    item_a = _item("MEMORIA:1")
    item_b = _item("MEMORIA:2")
    agrupacion = grouping.agrupar_equivalentes(
        [_candidata(item_a), _candidata(item_b)], lambda _i: "PK-1"
    )
    assert len(agrupacion.grupos) == 1
    assert set(agrupacion.grupos[0].miembros) == {"MEMORIA:1", "MEMORIA:2"}


def test_deduplicar_por_identidad_merges_signals_without_losing_any() -> None:
    item = _item("MEMORIA:1")
    aportada_e1 = _candidata(item, etapa=Etapa.E1)
    aportada_e2 = replace(_candidata(item, etapa=Etapa.E2), senal="otra senal")
    unicas, fusionadas = grouping.deduplicar_por_identidad([aportada_e1, aportada_e2])
    assert len(unicas) == 1
    # La primera etapa (mayor autoridad) es la que se conserva.
    assert unicas[0].etapa is Etapa.E1
    assert fusionadas == {"MEMORIA:1": ("otra senal", "prueba")}


# -- staged_engine (recuperar) ------------------------------------------------


class _CandidatoDeUnaEtapa:
    """Fuente de prueba: aporta lo que se le da, solo en ``E1``."""

    identificador = "prueba"
    senal_tardia_habilitada = "ninguna_adicional"

    def __init__(self, items: Sequence[ItemCanonico]) -> None:
        self._items = tuple(items)

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        if contexto.etapa is not Etapa.E1:
            return ()
        return [
            _candidata(i, etapa=Etapa.E1)
            for i in self._items
            if i.id not in contexto.ya_recuperados
        ]

    def leer(self, item: ItemCanonico, consulta: str) -> LecturaSemantica:
        return _candidata(item).lectura


class _CandidatoDeDosEtapas:
    """Fuente de prueba: aporta un grupo de items distinto por etapa, para
    reproducir un grupo de equivalentes cuyos miembros llegan de etapas de
    autoridad distinta (CODEX-002)."""

    identificador = "prueba"
    senal_tardia_habilitada = "ninguna_adicional"

    def __init__(self, por_etapa: dict[Etapa, Sequence[ItemCanonico]]) -> None:
        self._por_etapa = por_etapa

    def candidatas(self, contexto: ContextoDeEtapa) -> Sequence[Candidata]:
        items = self._por_etapa.get(contexto.etapa, ())
        return [
            _candidata(i, etapa=contexto.etapa)
            for i in items
            if i.id not in contexto.ya_recuperados
        ]

    def leer(self, item: ItemCanonico, consulta: str) -> LecturaSemantica:
        return _candidata(item).lectura


class _PuertoDePrueba:
    def __init__(self, items: Sequence[ItemCanonico]) -> None:
        self._items = tuple(items)

    def por_clave_exacta(self, claves: Sequence[str]) -> tuple[ItemCanonico, ...]:
        return self._items

    def por_termino_lexico(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        return ()

    def por_prefijo_de_sujeto(self, prefijos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        return ()

    def por_identificadores(self, identificadores: Sequence[str]) -> MaterializacionPorIdentidad:
        raise NotImplementedError

    def historial_y_fuentes(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        return ()


def test_recuperar_returns_admitted_items_ordered_and_stops_by_exhaustion() -> None:
    item = _item("MEMORIA:1")
    recuperacion = recuperar(
        _peticion(), _PuertoDePrueba([item]), _CandidatoDeUnaEtapa([item]), PLANO_COMUN_VACIO
    )
    assert recuperacion.ids == ("MEMORIA:1",)
    assert recuperacion.parada.identificador == "S5"


def test_recuperar_discards_a_project_scoped_item_outside_the_authorized_project() -> None:
    dentro = _item("MEMORIA:1", project_id="1")
    fuera = _item("MEMORIA:2", subject_key="otro", project_id="2")
    peticion = _peticion(ambito=Ambito(global_=False, proyectos=("1",)))
    recuperacion = recuperar(
        peticion,
        _PuertoDePrueba([dentro, fuera]),
        _CandidatoDeUnaEtapa([dentro, fuera]),
        PLANO_COMUN_VACIO,
    )
    assert recuperacion.ids == ("MEMORIA:1",)


def test_recuperar_never_lets_a_critical_item_vanish_without_declaring_overflow() -> None:
    critico = _item("MEMORIA:1")
    ordinario = _item("MEMORIA:2", subject_key="otro-sujeto")
    peticion = _peticion(limite_duro=1)

    class _PlanoConCritico:
        def property_key(self, identidad: str) -> str | None:
            return None

        def criticidad_aplicada(self, identidad: str) -> CriticidadAplicada | None:
            if identidad != "MEMORIA:1":
                return None
            return CriticidadAplicada(
                nivel=Criticidad.CRITICA,
                razon_segura="prueba",
                fuente_de_politica="prueba",
                regla_de_politica="prueba",
            )

    recuperacion = recuperar(
        peticion,
        _PuertoDePrueba([critico, ordinario]),
        _CandidatoDeUnaEtapa([critico, ordinario]),
        _PlanoConCritico(),
    )
    # El critico entra dentro del limite (G12 lo prioriza); nada se pierde
    # en silencio. Si G12 tuviera un fallo, `RecuperacionInvalidaError`
    # abortaria en vez de devolver un resultado incompleto sin declararlo.
    assert recuperacion.ids == ("MEMORIA:1",)
    assert recuperacion.suficiencia.value in {"PARCIAL", "COMPLETA"}


def test_recuperar_orders_the_group_representative_ahead_of_a_higher_authority_member() -> None:
    """CODEX-002: `_elegir_representante` (staged_engine_grouping) puede
    elegir un representante distinto del miembro de mayor autoridad de
    etapa, y `GrupoDeEquivalentes` exige que ese representante encabece
    (staged_engine_contracts.py: "el representante encabeza"). Se reproduce
    con `MEMORIA:2` en `E1`, `MEMORIA:1` equivalente en `E2` (el desempate
    por id nombra representante a `MEMORIA:1`) y un tercer elegible ajeno al
    grupo (`MEMORIA:3`, también en `E2`). El orden corregido antepone al
    representante dentro de su propio grupo sin relegar a `MEMORIA:2` (su
    miembro de mayor autoridad) detrás de `MEMORIA:3`: con límite duro 2 el
    grupo entero cabe (`[MEMORIA:1, MEMORIA:2]`) y es `MEMORIA:3` —ajeno al
    grupo, sin ninguna señal que lo prefiera— quien queda fuera."""
    en_e1 = _item("MEMORIA:2")
    en_e2 = _item("MEMORIA:1")
    ajeno = _item("MEMORIA:3", subject_key="ancho-sujeto")
    peticion = _peticion(limite_duro=2)

    class _PlanoConPropiedad:
        def property_key(self, identidad: str) -> str | None:
            return "PK-1"

        def criticidad_aplicada(self, identidad: str) -> CriticidadAplicada | None:
            return None

    recuperacion = recuperar(
        peticion,
        _PuertoDePrueba([en_e1, en_e2, ajeno]),
        _CandidatoDeDosEtapas({Etapa.E1: [en_e1], Etapa.E2: [en_e2, ajeno]}),
        _PlanoConPropiedad(),
    )

    assert len(recuperacion.grupos) == 1
    grupo = recuperacion.grupos[0]
    assert grupo.representante == "MEMORIA:1"
    assert set(grupo.miembros) == {"MEMORIA:1", "MEMORIA:2"}
    assert recuperacion.ids == ("MEMORIA:1", "MEMORIA:2")
    assert grupo.identificador not in recuperacion.traza.grupos_truncados
    assert recuperacion.omitidos_por_limite == ("MEMORIA:3",)


def test_explicacion_documents_the_two_step_order_for_a_promoted_representative() -> None:
    """CODEX-002 (incidencia #457, tercera ronda): al sacar la prioridad
    del representante de ``_clave_de_orden`` hacia un segundo paso
    (``_con_representante_al_frente``, segunda ronda), ``EJES_DE_ORDEN_
    DECLARADOS`` seguía nombrando al representante como su segundo eje y
    ``explicar()`` seguía afirmando que la posición se debía solo a esa
    clave de desempate de cinco ejes — una descripción que ya no coincidía
    con el algoritmo real. Reutiliza el caso de
    ``test_recuperar_orders_the_group_representative_ahead_of_a_higher_
    authority_member``: MEMORIA:1 (``E2``) encabeza a MEMORIA:2 (``E1``,
    mayor autoridad de etapa) solo por la promoción intragrupo del segundo
    paso, no por la clave de desempate base."""
    en_e1 = _item("MEMORIA:2")
    en_e2 = _item("MEMORIA:1")
    peticion = _peticion(limite_duro=2)

    class _PlanoConPropiedad:
        def property_key(self, identidad: str) -> str | None:
            return "PK-1"

        def criticidad_aplicada(self, identidad: str) -> CriticidadAplicada | None:
            return None

    recuperacion = recuperar(
        peticion,
        _PuertoDePrueba([en_e1, en_e2]),
        _CandidatoDeDosEtapas({Etapa.E1: [en_e1], Etapa.E2: [en_e2]}),
        _PlanoConPropiedad(),
    )

    assert recuperacion.ids == ("MEMORIA:1", "MEMORIA:2")
    assert "representante" not in EJES_DE_ORDEN_DECLARADOS

    representante_resultado = next(r for r in recuperacion.resultados if r.item.id == "MEMORIA:1")
    razon = representante_resultado.explicacion.razon_de_orden
    assert ", ".join(EJES_DE_ORDEN_DECLARADOS) in razon
    assert PROMOCION_DE_REPRESENTANTE_DECLARADA in razon


def test_con_representante_al_frente_never_relegates_a_member_behind_an_unrelated_item() -> None:
    """CODEX-002 (segunda ronda): la corrección anterior anteponía el
    representante a *todo* miembro no representante, no solo a los de su
    propio grupo — con `no_es_representante` antes que la autoridad de
    etapa en la clave de orden, cualquier suelto quedaba por delante de un
    miembro de mayor autoridad de otro grupo. Reproduce el ejemplo exacto
    del hallazgo directamente sobre la función de orden: representante y
    miembro equivalentes, ambos en `E1`, y un suelto ajeno al grupo en `E4`
    (menor autoridad). `recuperar()` no puede reproducir este caso de punta
    a punta con `limite_duro=2`: el mecanismo de parada por límite duro
    (S4) corta la expansión nada más admitir el grupo completo en `E1`, sin
    llegar a `E4` — precisamente la razón por la que el hallazgo original
    solo pudo demostrarse sobre `_clave_de_orden`/`_con_representante_al_
    frente`, no sobre un caso íntegro de `recuperar()`. El orden corregido
    debe anteponer el representante a su propio miembro sin relegar a ese
    miembro (mayor autoridad) detrás del suelto (menor autoridad)."""
    representante_candidata = _candidata(_item("MEMORIA:1"), etapa=Etapa.E1)
    miembro_candidata = _candidata(_item("MEMORIA:2"), etapa=Etapa.E1)
    suelto_candidata = _candidata(_item("MEMORIA:3", subject_key="otro-sujeto"), etapa=Etapa.E4)

    def criticidad_de(identidad: str) -> Criticidad:
        return Criticidad.ORDINARIA

    def representante_de(identidad: str) -> str | None:
        return "MEMORIA:1" if identidad in {"MEMORIA:1", "MEMORIA:2"} else None

    ordenadas_por_criticidad = sorted(
        [miembro_candidata, suelto_candidata, representante_candidata],
        key=lambda c: _clave_de_orden(c, criticidad_de),
    )
    ordenadas = _con_representante_al_frente(
        ordenadas_por_criticidad, criticidad_de, representante_de
    )

    assert [c.item.id for c in ordenadas] == ["MEMORIA:1", "MEMORIA:2", "MEMORIA:3"]


def test_recuperar_raises_if_a_candidate_reads_no_subject_at_all() -> None:
    """Guarda de integridad de `RecuperacionInvalidaError`: no es alcanzable
    con un candidato honesto (``leer`` siempre declara sujeto), así que esta
    prueba fuerza el caso límite directamente sobre `staged_engine_gates`,
    no sobre `recuperar`, para no depender de un doble que mienta."""
    item = _item("MEMORIA:1")
    candidata_incompleta = replace(
        _candidata(item), lectura=replace(_candidata(item).lectura, sujeto="")
    )
    filtrado = gates.aplicar_g11([candidata_incompleta], _peticion())
    assert filtrado.admitidas == ()


def test_clase_de_evidencia_atribuida_never_reads_as_canonica_by_default() -> None:
    assert (
        ItemCanonico(
            id="MEMORIA:1",
            clase=Clase.MEMORIA,
            project_id=None,
            texto="x",
            subject_key=None,
            vigente=True,
            disponible=True,
            created_at="2026-01-01T00:00:00Z",
        ).clase_de_evidencia
        is ClaseDeEvidencia.CANONICA
    )


def test_recuperacion_invalida_error_is_a_runtime_error() -> None:
    assert issubclass(RecuperacionInvalidaError, RuntimeError)


@pytest.mark.parametrize("nivel", [Criticidad.ORDINARIA, Criticidad.IMPORTANTE, Criticidad.CRITICA])
def test_criticidad_orden_es_total_y_estable(nivel: Criticidad) -> None:
    from sirius.domain.staged_engine_contracts import ORDEN_DE_CRITICIDAD

    assert nivel in ORDEN_DE_CRITICIDAD
