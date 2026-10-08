"""El sueño: resume el día y propone hechos, sin leer a Sirius (pieza G de ADR-233, ADR-239)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import update

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.persistence.database import build_engine
from sirius.adapters.persistence.models import MessageModel
from sirius.adapters.persistence.sqlite_conversation_repository import (
    build_sqlite_conversation_repository,
)
from sirius.adapters.persistence.sqlite_memory_repository import build_sqlite_memory_repository
from sirius.adapters.persistence.sqlite_memory_suggestion_repository import (
    build_sqlite_memory_suggestion_repository,
)
from sirius.adapters.persistence.sqlite_robot_conversation import (
    build_sqlite_robot_conversation_repository,
)
from sirius.adapters.persistence.sqlite_unit_of_work import build_sqlite_unit_of_work
from sirius.application.dream import DreamService, parse_facts
from sirius.application.facts import FactProposals
from sirius.domain.conversation import MessageRole
from sirius.domain.facts import Certainty, ProposedFact
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.llm import LLMProvider

pytestmark = pytest.mark.integration

DE_SIRIUS = "SECRETO-DE-SIRIUS"


@dataclass
class _Resumidor:
    pedidos: list[str] = field(default_factory=list)
    falla: bool = False

    def summarize(self, text: str, provider: LLMProvider) -> str:
        del provider
        self.pedidos.append(text)
        if self.falla:
            raise RuntimeError("sin modelo")
        return "Cableó un edificio."


@dataclass
class _Extractor:
    propone: Sequence[ProposedFact] = ()
    leido: list[str] = field(default_factory=list)
    falla: bool = False

    def extract(self, text: str, provider: LLMProvider) -> Sequence[ProposedFact]:
        del provider
        self.leido.append(text)
        if self.falla:
            raise RuntimeError("el modelo se cortó")
        return self.propone


class _Modelo:
    model_name = "local"


@dataclass
class _Mundo:
    base: Path
    sueno: DreamService
    resumidor: _Resumidor
    extractor: _Extractor

    def di(self, texto: str, *, el: bool = True, hace_dias: int = 0) -> None:
        conversacion = build_sqlite_conversation_repository(self.base)
        try:
            principal = conversacion.get_or_create_main_conversation()
            rol = MessageRole.USER if el else MessageRole.SIRIUS
            mensaje = conversacion.append_message(principal.id, rol, texto)
        finally:
            conversacion.close()
        if hace_dias:
            motor = build_engine(self.base)
            with motor.begin() as conexion:
                conexion.execute(
                    update(MessageModel)
                    .where(MessageModel.id == mensaje.id)
                    .values(
                        created_at=(mensaje.created_at - timedelta(days=hace_dias)).replace(
                            tzinfo=None
                        )
                    )
                )
            motor.dispose()


def _mundo(
    tmp_path: Path, *, propone: Sequence[ProposedFact] = (), con_modelo: bool = True
) -> _Mundo:
    rutas = resolve_paths(tmp_path / "datos")
    initialize_persistence(rutas)
    base = rutas.data_dir / "sirius.db"
    resumidor, extractor = _Resumidor(), _Extractor(propone)
    sueno = DreamService(
        build_sqlite_conversation_repository(base),
        build_sqlite_robot_conversation_repository(base),
        resumidor,
        extractor,
        FactProposals(build_sqlite_unit_of_work(base)),
        build_sqlite_memory_repository(base),
        build_sqlite_memory_suggestion_repository(base),
        (lambda: _Modelo()) if con_modelo else (lambda: None),  # type: ignore[arg-type,return-value]
    )
    return _Mundo(base, sueno, resumidor, extractor)


def test_el_sueno_solo_lee_lo_que_dijo_el(tmp_path: Path) -> None:
    mundo = _mundo(tmp_path)
    mundo.di("Vengo reventado de la obra.")
    mundo.di(f"Pues yo he pensado en {DE_SIRIUS}.", el=False)

    mundo.sueno.dream(date.today())

    assert mundo.resumidor.pedidos == ["Él: Vengo reventado de la obra."]
    assert mundo.extractor.leido == ["Él: Vengo reventado de la obra."]
    assert mundo.sueno.latest_summary() == "Cableó un edificio."


def test_sin_modelo_de_este_ordenador_no_suena(tmp_path: Path) -> None:
    mundo = _mundo(tmp_path, con_modelo=False)
    mundo.di("Vengo reventado de la obra.")

    assert mundo.sueno.dream(date.today()) == []
    assert mundo.resumidor.pedidos == []
    assert mundo.sueno.latest_summary() is None


def test_lo_que_propone_queda_pendiente_y_no_se_propone_dos_veces(tmp_path: Path) -> None:
    hecho = ProposedFact("propietario", "trabajo", "Trabaja de electricista")
    mundo = _mundo(tmp_path, propone=[hecho, ProposedFact("propietario", None, "  ")])
    mundo.di("Hoy tocaba cablear un edificio entero.")

    assert mundo.sueno.dream(date.today()) == [hecho]
    assert mundo.sueno.dream(date.today()) == []


def test_si_no_puede_resumir_propone_igual_y_el_dia_queda_por_sonar(tmp_path: Path) -> None:
    hecho = ProposedFact("propietario", "trabajo", "Trabaja de electricista")
    mundo = _mundo(tmp_path, propone=[hecho])
    mundo.resumidor.falla = True
    mundo.di("Hoy tocaba cablear un edificio entero.", hace_dias=1)

    assert mundo.sueno.dream(date.today() - timedelta(days=1)) == [hecho]
    assert mundo.sueno.dream_pending(date.today()) == 1, "sin resumen, ese día sigue sin soñar"


def test_si_no_puede_proponer_el_dia_queda_por_sonar_aunque_ya_lo_resumiera(
    tmp_path: Path,
) -> None:
    """Ronda 1 de Codex: el resumen marcaba el día como soñado antes de proponer, y si
    proponer fallaba, sus hechos no se volvían a intentar nunca."""
    hecho = ProposedFact("propietario", "trabajo", "Trabaja de electricista")
    mundo = _mundo(tmp_path, propone=[hecho])
    mundo.extractor.falla = True
    mundo.di("Hoy tocaba cablear un edificio entero.", hace_dias=1)

    assert mundo.sueno.dream_pending(date.today()) == 1
    assert mundo.sueno.latest_summary() is None, "el día no puede quedar como soñado"

    mundo.extractor.falla = False
    assert mundo.sueno.dream_pending(date.today()) == 1
    assert mundo.sueno.latest_summary() == "Cableó un edificio."
    assert mundo.sueno.dream_pending(date.today()) == 0


def test_un_hecho_repetido_en_la_misma_respuesta_se_propone_una_vez(tmp_path: Path) -> None:
    """Ronda 2 de Codex: si el modelo repetía un hecho, salían dos sugerencias iguales."""
    hecho = ProposedFact("propietario", "trabajo", "Trabaja de electricista")
    otra_vez = ProposedFact("Propietario", "trabajo", "trabaja de ELECTRICISTA")
    mundo = _mundo(tmp_path, propone=[hecho, otra_vez])
    mundo.di("Hoy tocaba cablear un edificio entero.")

    assert mundo.sueno.dream(date.today()) == [hecho]
    sugerencias = build_sqlite_memory_suggestion_repository(mundo.base)
    try:
        assert len(sugerencias.list_pending_suggestions()) == 1
    finally:
        sugerencias.close()


def test_lo_que_el_rechazo_no_se_vuelve_a_proponer_al_volver_a_sonar_el_dia(
    tmp_path: Path,
) -> None:
    """Ronda 2 de Codex: un día que quedó a medias se vuelve a soñar, y no puede
    proponerle otra vez lo que ya contestó que no."""
    from sirius.application.reject_memory_suggestion import RejectMemorySuggestionUseCase

    hecho = ProposedFact("propietario", "trabajo", "Trabaja de electricista")
    mundo = _mundo(tmp_path, propone=[hecho])
    mundo.resumidor.falla = True
    mundo.di("Hoy tocaba cablear un edificio entero.", hace_dias=1)
    assert mundo.sueno.dream_pending(date.today()) == 1
    sugerencias = build_sqlite_memory_suggestion_repository(mundo.base)
    try:
        [propuesta] = sugerencias.list_pending_suggestions()
        assert propuesta.dreamed_day == date.today() - timedelta(days=1)
        RejectMemorySuggestionUseCase(build_sqlite_unit_of_work(mundo.base)).reject(propuesta.id)

        mundo.resumidor.falla = False
        assert mundo.sueno.dream(date.today() - timedelta(days=1)) == []
        assert sugerencias.list_pending_suggestions() == []
    finally:
        sugerencias.close()


def test_lo_que_el_ya_confirmo_no_vuelve_aunque_luego_cambiara(tmp_path: Path) -> None:
    """Ronda 3 de Codex: lo confirmado que después cambió ya no era un hecho vigente,
    y volver a soñar el día lo proponía otra vez."""
    from sirius.application.facts import ConfirmFactSuggestionUseCase

    hecho = ProposedFact("propietario", "dónde vive", "Vive en la sierra")
    mundo = _mundo(tmp_path, propone=[hecho])
    mundo.resumidor.falla = True
    mundo.di("Me mudé a la sierra.", hace_dias=1)
    assert mundo.sueno.dream_pending(date.today()) == 1
    sugerencias = build_sqlite_memory_suggestion_repository(mundo.base)
    memoria = build_sqlite_memory_repository(mundo.base)
    try:
        [propuesta] = sugerencias.list_pending_suggestions()
        ConfirmFactSuggestionUseCase(build_sqlite_unit_of_work(mundo.base)).confirm(propuesta.id)
        memoria.record_fact(
            "propietario", "dónde vive", "Vive en la costa", "prueba", since=date.today()
        )

        mundo.resumidor.falla = False
        assert mundo.sueno.dream(date.today() - timedelta(days=1)) == []
        assert sugerencias.list_pending_suggestions() == []
    finally:
        sugerencias.close()
        memoria.close()


def test_al_abrirse_suena_los_dias_de_antes_que_faltan_y_no_el_de_hoy(tmp_path: Path) -> None:
    mundo = _mundo(tmp_path)
    mundo.di("Hace un mes.", hace_dias=30)
    mundo.di("Anteayer.", hace_dias=2)
    mundo.di("Ayer.", hace_dias=1)
    mundo.di("Hoy.")

    assert mundo.sueno.dream_pending(date.today()) == 2
    assert mundo.resumidor.pedidos == ["Él: Anteayer.", "Él: Ayer."]
    assert mundo.sueno.dream_pending(date.today()) == 0


def test_parar_el_sueno_deja_los_dias_que_faltan_para_otra_vez(tmp_path: Path) -> None:
    mundo = _mundo(tmp_path)
    mundo.di("Anteayer.", hace_dias=2)
    mundo.di("Ayer.", hace_dias=1)

    assert mundo.sueno.dream_pending(date.today(), should_stop=lambda: True) == 0
    assert mundo.resumidor.pedidos == []


def test_lo_que_responde_el_modelo_se_lee_con_cuidado() -> None:
    respuesta = "\n".join(
        [
            '{"persona": "propietario", "tema": "trabajo", "texto": "Trabaja de electricista"}',
            "esto no es json",
            '{"persona": "Lucía", "texto": "Se va a una farmacia", "dicho_por": "Lucía",'
            ' "seguridad": "dudosa", "desde": "2026-09-01"},',
            '{"persona": "propietario", "texto": "Vive en Cuenca", "dicho_por": "Sirius"}',
            '{"persona": "", "texto": "Sin persona"}',
            '{"persona": "propietario", "texto": "Fecha rara", "desde": "ayer"}',
        ]
    )
    assert parse_facts(respuesta) == [
        ProposedFact("propietario", "trabajo", "Trabaja de electricista"),
        ProposedFact(
            "Lucía", None, "Se va a una farmacia", date(2026, 9, 1), "Lucía", Certainty.DOUBTFUL
        ),
        ProposedFact("propietario", None, "Fecha rara"),
    ]
    assert parse_facts('[{"persona": "propietario", "texto": "Es del Betis"}]') == [
        ProposedFact("propietario", None, "Es del Betis")
    ]
    assert parse_facts("") == []
