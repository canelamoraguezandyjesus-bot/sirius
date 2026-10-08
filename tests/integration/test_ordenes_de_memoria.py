"""Las órdenes de memoria y los hechos en cada turno, con Sirius montado de verdad (ADR-239)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pytest

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.memory_commands import ASK_TO_CONFIRM, FORGET_ABOUT_STORED
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.domain.facts import Certainty, ProposedFact
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.embeddings import EmbeddingError
from sirius.ports.llm import LLMCompleted, LLMRequest, LLMStreamEvent, LLMTextDelta

pytestmark = pytest.mark.integration


@dataclass
class _Modelo:
    model_name: str = "grabador"
    peticiones: list[LLMRequest] = field(default_factory=list)

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        self.peticiones.append(request)
        yield LLMTextDelta("Vale.")
        yield LLMCompleted(text="Vale.", input_tokens=1, output_tokens=1)

    def cancel(self, operation_id: str) -> None:
        del operation_id


class _SinHuellas:
    """Sin modelo de huellas, pero apuntando cada frase que le piden."""

    model_name = "sin-huellas"

    def __init__(self) -> None:
        self.pedidas: list[str] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.pedidas.extend(texts)
        raise EmbeddingError("sin huellas")


@dataclass
class _Sirius:
    deps: ConversationDependencies
    modelo: _Modelo
    backups: Path
    huellas: _SinHuellas

    def di(self, texto: str) -> str:
        resultado = self.deps.send_message_use_case.send_message(texto)
        return resultado.sirius_message.content or ""

    def instrucciones(self) -> str:
        return self.modelo.peticiones[-1].instructions

    def anota(self, persona: str, tema: str | None, texto: str, **extra: object) -> None:
        sugerencia = self.deps.fact_proposals.propose(ProposedFact(persona, tema, texto, **extra))  # type: ignore[arg-type]
        self.deps.confirm_memory_suggestion_use_case.confirm(sugerencia.id)


@pytest.fixture
def sirius(tmp_path: Path) -> Iterator[_Sirius]:
    rutas = resolve_paths(tmp_path / "datos")
    initialize_persistence(rutas)
    huellas = _SinHuellas()
    deps = build_conversation_dependencies(
        rutas.data_dir / "sirius.db",
        rutas.backups_dir,
        secret_store=FakeSecretStore(),
        text_embedder=huellas,
    )
    modelo = _Modelo()
    deps.send_message_use_case.set_llm_provider(modelo)
    if not deps.initial_project_use_case.is_configured():
        deps.initial_project_use_case.create_initial_project("Charla", "Charlar")
    yield _Sirius(deps, modelo, rutas.backups_dir, huellas)
    deps.close_database_connections()


def test_la_charla_trae_lo_que_se_sabe_de_quien_nombra_aunque_no_diga_su_nombre(
    sirius: _Sirius,
) -> None:
    # «Es enfermera» no dice «Lucía»: solo lo trae la ficha de Lucía, no la búsqueda.
    sirius.anota("Lucía", "trabajo", "Es enfermera")
    sirius.anota("Marta", "trabajo", "Es abogada")

    sirius.di("¿Qué tal estará Lucía?")

    instrucciones = sirius.instrucciones()
    assert "# Lo que sabes de Lucía\n- Es enfermera" in instrucciones
    assert "Es abogada" not in instrucciones


def test_lo_suyo_va_siempre_con_su_fecha_y_quien_lo_dijo_y_una_sola_vez(sirius: _Sirius) -> None:
    sirius.anota(
        "propietario",
        "equipo",
        "Es del Atleti",
        said_by="Lucía",
        certainty=Certainty.DOUBTFUL,
        since=date(2026, 9, 1),
    )

    sirius.di("Atleti o no Atleti, esa es la cuestión")

    instrucciones = sirius.instrucciones()
    assert (
        "# Lo que sabes de tu dueño\n- Es del Atleti (desde el 01-09-2026) "
        "(lo dijo Lucía; no es seguro)"
    ) in instrucciones
    # La búsqueda por palabras también lo encuentra, pero no va dos veces.
    assert instrucciones.count("Es del Atleti") == 1


def test_que_sabes_de_alguien_con_ficha_contesta_sin_modelo_y_sin_ficha_va_a_la_charla(
    sirius: _Sirius,
) -> None:
    sirius.anota("Lucía", "trabajo", "Es enfermera")
    sirius.di("Ayer vi a Lucía en el mercado.")
    antes = len(sirius.modelo.peticiones)

    respuesta = sirius.di("¿Qué sabes de Lucía?")

    assert respuesta == (
        "Esto es lo que sé de Lucía:\n- Es enfermera\nMe has hablado de Lucía en 1 mensaje."
    )
    assert len(sirius.modelo.peticiones) == antes
    sirius.di("¿Qué sabes de física cuántica?")
    assert len(sirius.modelo.peticiones) == antes + 1


def test_eso_no_es_asi_pregunta_y_un_si_justo_despues_lo_cambia(sirius: _Sirius) -> None:
    sirius.anota("propietario", "equipo", "Es del Atleti", said_by="Lucía")
    sirius.di("¿De qué equipo soy?")
    antes = len(sirius.modelo.peticiones)

    pregunta = sirius.di("Eso no es así: soy del Betis.")
    assert pregunta.endswith(ASK_TO_CONFIRM)
    assert "«Es del Atleti» (lo dijo Lucía)" in pregunta
    assert sirius.di("Sí.") == "Hecho. Ahora tengo «Soy del Betis»."

    assert len(sirius.modelo.peticiones) == antes
    assert [m.current_revision.content for m in sirius.deps.facts_use_case.current()] == [
        "Soy del Betis"
    ]


def test_un_si_que_no_contesta_a_la_pregunta_es_charla(sirius: _Sirius) -> None:
    sirius.anota("propietario", "equipo", "Es del Atleti")
    sirius.di("¿De qué equipo soy?")
    sirius.di("Eso no es así: soy del Betis.")
    sirius.di("Por cierto, hoy llueve.")
    antes = len(sirius.modelo.peticiones)

    sirius.di("Sí.")

    assert len(sirius.modelo.peticiones) == antes + 1, "el sí ya no contestaba a la pregunta"
    assert [c.after for c in sirius.deps.facts_use_case.pending_corrections()] == ["Soy del Betis"]


def test_un_no_deja_el_hecho_como_estaba(sirius: _Sirius) -> None:
    sirius.anota("propietario", "equipo", "Es del Atleti")
    sirius.di("¿De qué equipo soy?")
    sirius.di("Eso no es así: soy del Betis.")

    assert sirius.di("No") == "Vale, lo dejo como estaba: «Es del Atleti»."
    assert sirius.deps.facts_use_case.pending_corrections() == []


def test_eso_no_es_asi_sin_hecho_que_case_va_a_la_charla(sirius: _Sirius) -> None:
    sirius.anota("propietario", "trabajo", "Trabaja de electricista")
    sirius.di("¿Qué tiempo hará mañana?")
    antes = len(sirius.modelo.peticiones)

    sirius.di("Eso no es así: va a llover.")

    assert len(sirius.modelo.peticiones) == antes + 1
    assert sirius.deps.facts_use_case.pending_corrections() == []


def test_olvida_lo_de_no_guarda_el_tema_ni_lo_repite_y_avisa_de_las_copias(
    sirius: _Sirius,
) -> None:
    sirius.di("Mi vecino Ramiro me tiene frito.")
    sirius.backups.mkdir(parents=True, exist_ok=True)
    (sirius.backups / "copia.sirius-backup").write_bytes(b"cifrada")

    respuesta = sirius.di("Olvida lo de mi vecino Ramiro.")

    assert "Ramiro" not in respuesta
    # Ni el modelo de huellas vio la orden: se atiende antes de buscar.
    assert not any("Olvida" in frase for frase in sirius.huellas.pedidas)
    assert "Mi vecino Ramiro me tiene frito." in sirius.huellas.pedidas
    assert respuesta.endswith("Las copias de seguridad que hiciste antes lo siguen guardando.")
    historia = sirius.deps.get_history_use_case.get_history()
    assert [m.content for m in historia][-2:] == [FORGET_ABOUT_STORED, respuesta]
    assert sirius.di("Olvida lo de la luna de Plutón") == (
        "No encuentro nada dicho con esas palabras. Prueba con las palabras exactas."
    )


def test_que_sabes_de_mi_sin_nada_apuntado_lo_dice(sirius: _Sirius) -> None:
    assert sirius.di("¿Qué sabes de mí?") == "Todavía no tengo ningún hecho de ti apuntado."
    assert sirius.modelo.peticiones == []


def test_cada_hilo_tiene_su_unidad_de_trabajo(sirius: _Sirius) -> None:
    """Una unidad de trabajo guarda su sesión mientras dura: compartirla entre el hilo
    del envío, el del sueño y la ventana mezclaría sus transacciones."""
    deps = sirius.deps
    de_la_ventana = deps.fact_proposals._unit_of_work
    del_sueno = deps.dream_service._proposals._unit_of_work
    ordenes = deps.send_message_use_case._memory_commands
    assert ordenes is not None
    del_envio = ordenes._proposals._unit_of_work
    assert len({id(de_la_ventana), id(del_sueno), id(del_envio)}) == 3
    assert ordenes._confirm._unit_of_work is del_envio
    assert deps.confirm_memory_suggestion_use_case._unit_of_work is de_la_ventana
