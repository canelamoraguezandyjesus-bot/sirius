"""La vía de recuperación por vigencia del candidato léxico-estructurado
(ADR-168, hueco H1 de ADR-148, incidencia #577).

Un puerto espía y el candidato real: estas pruebas fijan **cuándo** se
pregunta por la ventana de vigencia y qué se hace con lo que devuelve, sin
SQLite y sin el banco de 47 casos. Lo que el banco mide está en
``tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py``; lo que el SQL
hace, en ``tests/unit/test_staged_engine_port.py``.
"""

from __future__ import annotations

from collections.abc import Sequence

from sirius.adapters.persistence import staged_engine_candidate
from sirius.adapters.persistence.staged_engine_candidate import MEDIO_POR_VIGENCIA
from sirius.domain.staged_engine import recuperar
from sirius.domain.staged_engine_contracts import (
    PLANO_COMUN_VACIO,
    Ambito,
    Cardinalidad,
    Clase,
    ContextoDeEtapa,
    Criticidad,
    CriticidadAplicada,
    Etapa,
    ItemCanonico,
    MaterializacionPorIdentidad,
    Modo,
    Peticion,
    VentanaTemporal,
)

#: La consulta del caso `B04-CA-22` no aporta ningún término que case con
#: nada del canon: su único criterio es el intervalo. Aquí se lleva al
#: extremo con una consulta cuyo tratamiento léxico deja CERO términos
#: significativos (`terminos_significativos` la vacía entera), que es
#: exactamente la entrada con la que `candidatas` salía antes por «no hay
#: términos» sin llegar a mirar la etapa.
CONSULTA_SIN_TEMA = "¿que hay entre uno y otro?"

#: Una consulta con tema: la que sí da de dónde partir.
CONSULTA_CON_TEMA = "horario del faro"

VENTANA = ("2026-01-10T00:00:00Z", "2026-03-20T00:00:00Z")


def _decision(item_id: str, *, texto: str = "Se aprueba el cambio de proveedor.") -> ItemCanonico:
    return ItemCanonico(
        id=item_id,
        clase=Clase.DECISION,
        project_id="1",
        texto=texto,
        subject_key="proveedor-embalaje",
        vigente=True,
        disponible=True,
        created_at="2026-02-01T00:00:00Z",
    )


class _PuertoEspia:
    """Puerto que anota qué rutas se le piden y con qué argumentos."""

    def __init__(
        self,
        *,
        por_ventana: Sequence[ItemCanonico] = (),
        por_clave: Sequence[ItemCanonico] = (),
    ) -> None:
        self._por_ventana = tuple(por_ventana)
        self._por_clave = tuple(por_clave)
        self.rutas: list[str] = []
        self.ventanas: list[tuple[str, str]] = []

    def por_clave_exacta(self, claves: Sequence[str]) -> tuple[ItemCanonico, ...]:
        self.rutas.append("por_clave_exacta")
        return self._por_clave

    def por_termino_lexico(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        self.rutas.append("por_termino_lexico")
        return ()

    def por_prefijo_de_sujeto(self, prefijos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        self.rutas.append("por_prefijo_de_sujeto")
        return ()

    def por_identificadores(self, identificadores: Sequence[str]) -> MaterializacionPorIdentidad:
        raise NotImplementedError

    def historial_y_fuentes(self, terminos: Sequence[str]) -> tuple[ItemCanonico, ...]:
        self.rutas.append("historial_y_fuentes")
        return ()

    def por_ventana_de_vigencia(self, desde: str, hasta: str) -> tuple[ItemCanonico, ...]:
        self.rutas.append("por_ventana_de_vigencia")
        self.ventanas.append((desde, hasta))
        return self._por_ventana


def _peticion(
    *,
    consulta: str,
    intervalo: tuple[str, str] | None,
    cardinalidad: Cardinalidad = Cardinalidad.EXHAUSTIVA,
    objetivos: int = 1,
    limite_duro: int = 100,
) -> Peticion:
    desde, hasta = (None, "2026-06-15T00:00:00Z") if intervalo is None else intervalo
    return Peticion(
        operation_id="test",
        consulta=consulta,
        proposito="prueba",
        modo=Modo.M2_HISTORICO,
        ambito=Ambito(global_=True, proyectos=()),
        ventana=VentanaTemporal(tiempo_objetivo=hasta, tiempo_objetivo_desde=desde),
        cardinalidad=cardinalidad,
        limite_objetivo=limite_duro,
        limite_duro=limite_duro,
        admite_no_vigentes=True,
        objetivos=objetivos,
    )


def _contexto(peticion: Peticion, puerto: _PuertoEspia, etapa: Etapa) -> ContextoDeEtapa:
    return ContextoDeEtapa(peticion, puerto, etapa, frozenset(), ())


# -- La vía nueva -------------------------------------------------------------


def test_e3_enumera_lo_vigente_en_la_ventana_cuando_la_consulta_no_da_palabras() -> None:
    """El caso que ADR-148 llama hueco H1, en pequeño: la petición declara un
    intervalo, la consulta no aporta un solo término significativo, y aun así
    ``E3`` propone lo que el sustrato afirma vigente en la ventana.

    Antes de ADR-168 esta prueba fallaba en la primera aserción: ``candidatas``
    salía por «no hay términos» antes de mirar la etapa, así que devolvía
    ``()`` para las cuatro etapas y la pregunta no tenía camino de entrada.
    """
    vigente = _decision("DECISION:9")
    puerto = _PuertoEspia(por_ventana=[vigente])
    peticion = _peticion(consulta=CONSULTA_SIN_TEMA, intervalo=VENTANA)
    candidato = staged_engine_candidate.candidato()

    aportadas = candidato.candidatas(_contexto(peticion, puerto, Etapa.E3))

    assert [c.item.id for c in aportadas] == ["DECISION:9"]
    assert aportadas[0].senal == MEDIO_POR_VIGENCIA
    assert puerto.ventanas == [VENTANA]
    # Y la ventana no se cuela en las otras tres etapas: la vía vive en E3.
    for etapa in (Etapa.E1, Etapa.E2, Etapa.E4):
        assert not candidato.candidatas(_contexto(peticion, puerto, etapa))
    assert puerto.ventanas == [VENTANA]


def test_sin_intervalo_declarado_e3_no_pregunta_por_la_ventana() -> None:
    """Una pregunta con tema —o cualquiera que declare un instante y no un
    intervalo— no activa la vía: el puerto no recibe la consulta por ventana
    y ``E3`` aporta exactamente lo que aportaba antes de ADR-168."""
    puerto = _PuertoEspia(por_ventana=[_decision("DECISION:9")])
    peticion = _peticion(consulta=CONSULTA_CON_TEMA, intervalo=None)
    candidato = staged_engine_candidate.candidato()

    aportadas = candidato.candidatas(_contexto(peticion, puerto, Etapa.E3))

    assert aportadas == []
    assert "por_ventana_de_vigencia" not in puerto.rutas


def test_un_intervalo_invertido_no_es_un_intervalo() -> None:
    """``desde`` posterior a ``hasta`` no enumera nada: se degrada al
    comportamiento anterior en vez de consultar una ventana imposible."""
    puerto = _PuertoEspia(por_ventana=[_decision("DECISION:9")])
    peticion = _peticion(
        consulta=CONSULTA_SIN_TEMA,
        intervalo=("2026-03-20T00:00:00Z", "2026-01-10T00:00:00Z"),
    )

    aportadas = staged_engine_candidate.candidato().candidatas(
        _contexto(peticion, puerto, Etapa.E3)
    )

    assert aportadas == []
    assert "por_ventana_de_vigencia" not in puerto.rutas


# -- Dónde vive la vía: E3, la etapa a la que solo se llega por insuficiencia --


def test_la_ventana_no_se_consulta_si_las_etapas_lexicas_ya_bastaron() -> None:
    """La razón de que la vía viva en ``E3`` y no en ``E1``.

    El motor solo avanza de etapa por insuficiencia. Con una cardinalidad
    ``EXACTA`` que ``E1`` ya satisface, la expansión se detiene antes de
    ``E3`` y la ventana no llega a consultarse: es la forma que el motor
    tiene de decir «esta pregunta sí tenía de dónde partir», sin necesidad de
    una lista de temas. En ``E1`` la enumeración se dispararía siempre, aun
    cuando la vía léxica ya hubiera resuelto la pregunta.
    """
    encontrada = _decision("DECISION:1", texto="El horario del faro es de nueve a cinco.")
    puerto = _PuertoEspia(por_ventana=[_decision("DECISION:9")], por_clave=[encontrada])
    peticion = _peticion(
        consulta=CONSULTA_CON_TEMA,
        intervalo=VENTANA,
        cardinalidad=Cardinalidad.EXACTA,
        objetivos=1,
    )

    recuperacion = recuperar(
        peticion, puerto, staged_engine_candidate.candidato(), PLANO_COMUN_VACIO
    )

    assert recuperacion.ids == ("DECISION:1",)
    assert recuperacion.parada.identificador == "S1"
    assert "por_ventana_de_vigencia" not in puerto.rutas


def test_lo_lexico_conserva_su_autoridad_sobre_lo_enumerado_por_ventana() -> None:
    """La vía añade, no sustituye ni desplaza: lo que ``E1`` encuentra por
    palabras encabeza igual, porque la autoridad de la etapa de origen manda
    en el orden y ``E3`` va por detrás de ``E1``."""
    lexica = _decision("DECISION:1", texto="El horario del faro es de nueve a cinco.")
    puerto = _PuertoEspia(por_ventana=[_decision("DECISION:9")], por_clave=[lexica])
    peticion = _peticion(consulta=CONSULTA_CON_TEMA, intervalo=VENTANA)

    recuperacion = recuperar(
        peticion, puerto, staged_engine_candidate.candidato(), PLANO_COMUN_VACIO
    )

    assert recuperacion.ids == ("DECISION:1", "DECISION:9")
    origen = {r.item.id: r.etapa_de_origen for r in recuperacion.resultados}
    assert origen == {"DECISION:1": Etapa.E1, "DECISION:9": Etapa.E3}


# -- Ninguna crítica se pierde por culpa de la vía ---------------------------


class _PlanoConCritico:
    def __init__(self, critico: str) -> None:
        self._critico = critico

    def property_key(self, identidad: str) -> str | None:
        return None

    def criticidad_aplicada(self, identidad: str) -> CriticidadAplicada | None:
        if identidad != self._critico:
            return None
        return CriticidadAplicada(
            nivel=Criticidad.CRITICA,
            razon_segura="no se lee en las pruebas",
            fuente_de_politica="prueba",
            regla_de_politica="prueba",
        )


def test_la_via_no_puede_desplazar_a_un_critico_fuera_del_limite() -> None:
    """La vía enumera, y enumerar puede traer muchos: lo que no puede es
    empujar a un crítico fuera del límite duro en silencio.

    ``G12`` ordena por criticidad antes de recortar y el motor levanta
    ``RecuperacionInvalidaError`` si un crítico elegible desaparece sin
    declararse. Con un límite duro de uno y tres candidatos de ventana, el
    crítico es el que se entrega.
    """
    critico = _decision("DECISION:7")
    puerto = _PuertoEspia(por_ventana=[_decision("DECISION:5"), critico, _decision("DECISION:6")])
    peticion = _peticion(consulta=CONSULTA_SIN_TEMA, intervalo=VENTANA, limite_duro=1)

    recuperacion = recuperar(
        peticion, puerto, staged_engine_candidate.candidato(), _PlanoConCritico("DECISION:7")
    )

    assert recuperacion.ids == ("DECISION:7",)
    assert recuperacion.traza.criticos_omitidos == ()
