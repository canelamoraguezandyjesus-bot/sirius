"""Las órdenes de memoria y los hechos en cada turno, con Sirius montado de verdad (ADR-239)."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator, Sequence
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from sirius.adapters.persistence.bootstrap import initialize_persistence
from sirius.adapters.secrets.fake import FakeSecretStore
from sirius.application.memory_commands import ASK_TO_CONFIRM, FORGET_ABOUT_STORED
from sirius.application.send_message import COMMAND_VOICE_TASK, CommandVoice
from sirius.composition_root import ConversationDependencies, build_conversation_dependencies
from sirius.domain.conversation import MessageRole
from sirius.domain.conversation_mode import MODE_INSTRUCTIONS, ConversationMode
from sirius.domain.facts import Certainty, ProposedFact
from sirius.infrastructure.paths import resolve_paths
from sirius.ports.embeddings import EmbeddingError
from sirius.ports.llm import (
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMRequest,
    LLMStreamEvent,
    LLMTextDelta,
)

pytestmark = pytest.mark.integration


@dataclass
class _Modelo:
    """El modelo de la charla. Lo que se le pide para la voz de una orden (ADR-240) lo
    apunta aparte, en ``voces``: ``peticiones`` son solo las de la charla.

    Sin ``voz``, no se la pone, como un modelo que no contesta: así estas pruebas miran
    lo que hace cada orden con la frase de siempre, y la voz la miran las suyas.
    """

    model_name: str = "grabador"
    peticiones: list[LLMRequest] = field(default_factory=list)
    voces: list[LLMRequest] = field(default_factory=list)
    voz: str | None = None
    cancela_la_voz: bool = False
    #: Se llama al pedir la voz, antes de contestar: para mirar la base en ese momento.
    al_pedir_la_voz: Callable[[], None] | None = None

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        if COMMAND_VOICE_TASK in request.instructions:
            self.voces.append(request)
            if self.al_pedir_la_voz is not None:
                self.al_pedir_la_voz()
            if self.cancela_la_voz:
                yield LLMCancelled(partial_text="Bor")
            elif self.voz is None:
                yield LLMError(kind=LLMErrorKind.CONNECTION, message="sin voz en esta prueba")
            else:
                yield LLMTextDelta(self.voz)
                yield LLMCompleted(text=self.voz, input_tokens=1, output_tokens=1)
            return
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
    base: Path

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
    yield _Sirius(deps, modelo, rutas.backups_dir, huellas, rutas.data_dir / "sirius.db")
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


def test_olvida_eso_tras_eso_no_es_asi_se_lleva_la_correccion(sirius: _Sirius) -> None:
    """Ronda 2 de Codex: la corrección se proponía antes de guardar su mensaje y no
    quedaba ligada a él; olvidarlo la dejaba esperando su sí."""
    sirius.anota("propietario", "equipo", "Es del Atleti")
    sirius.di("¿De qué equipo soy?")
    sirius.di("Eso no es así: soy del Betis.")

    sirius.di("Olvida eso.")

    assert sirius.deps.facts_use_case.pending_corrections() == []
    with closing(sqlite3.connect(sirius.base)) as conexion:
        quedan = conexion.execute(
            "SELECT COUNT(*) FROM memory_suggestions WHERE content LIKE '%Betis%'"
        ).fetchone()
    assert quedan == (0,)


def _falla_una_vez(monkeypatch: pytest.MonkeyPatch, objeto: object, metodo: str) -> None:
    """La primera llamada a ``objeto.metodo`` falla, como un fallo pasajero de la base."""
    original = getattr(objeto, metodo)
    veces = [0]

    def falla_la_primera(*args: object, **kwargs: object) -> object:
        veces[0] += 1
        if veces[0] == 1:
            raise sqlite3.OperationalError("database is locked")
        return original(*args, **kwargs)

    monkeypatch.setattr(objeto, metodo, falla_la_primera)


def _falla_la_respuesta_una_vez(monkeypatch: pytest.MonkeyPatch, sirius: _Sirius) -> None:
    """Guardar la próxima respuesta de Sirius falla una vez; lo demás se guarda."""
    conversaciones = sirius.deps.send_message_use_case._conversation_repository
    original = conversaciones.append_message
    veces = [0]

    def falla_la_respuesta(conversation_id: int, role: MessageRole, *args: Any, **kw: Any) -> Any:
        if role is MessageRole.SIRIUS:
            veces[0] += 1
            if veces[0] == 1:
                raise sqlite3.OperationalError("database is locked")
        return original(conversation_id, role, *args, **kw)

    monkeypatch.setattr(conversaciones, "append_message", falla_la_respuesta)


def test_si_guardar_la_respuesta_falla_repetir_olvida_eso_no_se_lleva_otra_cosa(
    sirius: _Sirius, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ronda 3 de Codex: olvidar se guardaba antes que la orden. Si guardar la
    respuesta fallaba, repetir «olvida eso» ya no veía lo olvidado y se llevaba lo
    anterior, que no tenía nada que ver."""
    sirius.di("Mañana voy al dentista.")
    sirius.di("La clave es Zarzamora.")
    _falla_la_respuesta_una_vez(monkeypatch, sirius)
    with pytest.raises(sqlite3.OperationalError):
        sirius.di("Olvida eso.")

    assert sirius.di("Olvida eso.") == "Eso ya lo había olvidado."

    textos = [m.content for m in sirius.deps.get_history_use_case.get_history()]
    assert "Mañana voy al dentista." in textos
    assert not any("Zarzamora" in (texto or "") for texto in textos)


def test_si_olvidar_falla_repetir_olvida_eso_lo_olvida(
    sirius: _Sirius, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La orden que se quedó sin respuesta no cuenta: repetirla olvida lo de antes."""
    sirius.di("La clave es Zarzamora.")
    ordenes = sirius.deps.send_message_use_case._memory_commands
    assert ordenes is not None
    _falla_una_vez(monkeypatch, ordenes._forgetter, "forget_message")
    with pytest.raises(sqlite3.OperationalError):
        sirius.di("Olvida eso.")

    assert sirius.di("Olvida eso.").startswith("Hecho: ya no lo recuerdo.")
    textos = [m.content for m in sirius.deps.get_history_use_case.get_history()]
    assert not any("Zarzamora" in (texto or "") for texto in textos)


def test_olvida_eso_tras_confirmar_una_correccion_se_lleva_lo_corregido(
    sirius: _Sirius,
) -> None:
    """Ronda 3 de Codex: el «sí» confirmaba la corrección sin ligarla a su mensaje, y
    «olvida eso» justo después no la encontraba."""
    sirius.anota("propietario", "equipo", "Es del Atleti")
    sirius.di("¿De qué equipo soy?")
    sirius.di("Eso no es así: soy del Betis.")
    sirius.di("Sí.")

    sirius.di("Olvida eso.")

    with closing(sqlite3.connect(sirius.base)) as conexion:
        quedan = conexion.execute(
            "SELECT COUNT(*) FROM memory_revisions WHERE content LIKE '%Betis%'"
        ).fetchone()
    assert quedan == (0,)


def test_repetir_eso_no_es_asi_tras_un_fallo_no_deja_dos_correcciones(
    sirius: _Sirius, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ronda 3 de Codex: si guardar la respuesta fallaba, repetir la orden dejaba dos
    correcciones iguales esperando su sí."""
    sirius.anota("propietario", "equipo", "Es del Atleti")
    sirius.di("¿De qué equipo soy?")
    _falla_la_respuesta_una_vez(monkeypatch, sirius)
    with pytest.raises(sqlite3.OperationalError):
        sirius.di("Eso no es así: soy del Betis.")

    # Repetida, sigue siendo la misma orden, y pregunta otra vez.
    assert sirius.di("Eso no es así: soy del Betis.").endswith(ASK_TO_CONFIRM)

    assert [c.after for c in sirius.deps.facts_use_case.pending_corrections()] == ["Soy del Betis"]


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


# --- La voz de Sirius en las órdenes (ADR-240) ---------------------------------


def _lo_ve_la_voz(sirius: _Sirius, texto: str) -> bool:
    """Si ``texto`` llegó al modelo en alguna petición de voz."""
    return any(
        texto.casefold() in f"{voz.instructions}\n{voz.input_text}".casefold()
        for voz in sirius.modelo.voces
    )


def test_con_voz_la_respuesta_es_la_voz_y_detras_lo_exacto_tal_cual(sirius: _Sirius) -> None:
    sirius.anota("Lucía", "trabajo", "Es enfermera")
    sirius.di("Ayer vi a Lucía en el mercado.")
    sirius.modelo.voz = "Pues de Lucía sé esto, jefe:"
    antes = len(sirius.modelo.peticiones)

    respuesta = sirius.di("¿Qué sabes de Lucía?")

    assert respuesta == (
        "Pues de Lucía sé esto, jefe:\n- Es enfermera\nMe has hablado de Lucía en 1 mensaje."
    )
    assert len(sirius.modelo.peticiones) == antes, "la orden no va a la charla"
    assert len(sirius.modelo.voces) == 1
    assert not _lo_ve_la_voz(sirius, "enfermera"), "lo exacto no pasa por el modelo"
    assert not _lo_ve_la_voz(sirius, "mercado"), "la voz no lleva la charla"


def test_la_voz_no_ve_lo_que_se_olvida_ni_la_orden(sirius: _Sirius) -> None:
    sirius.di("Mi vecino Ramiro me tiene frito con la obra.")
    sirius.modelo.voz = "Borrado, jefe."

    respuesta = sirius.di("Olvida lo de mi vecino Ramiro.")

    assert respuesta == "Borrado, jefe."
    assert len(sirius.modelo.voces) == 1
    for palabra in ("Ramiro", "vecino", "frito", "obra"):
        assert not _lo_ve_la_voz(sirius, palabra), palabra


def test_la_correccion_con_voz_sigue_acabando_en_la_pregunta_y_el_si_la_contesta(
    sirius: _Sirius,
) -> None:
    sirius.anota("propietario", "equipo", "Es del Atleti", said_by="Lucía")
    sirius.di("¿De qué equipo soy?")
    sirius.modelo.voz = "A ver, a ver."

    pregunta = sirius.di("Eso no es así: soy del Betis.")

    assert pregunta.startswith("A ver, a ver.\nAhora tengo «Es del Atleti»")
    assert pregunta.endswith(ASK_TO_CONFIRM)
    assert sirius.di("Sí.") == "A ver, a ver.\nAhora tengo «Soy del Betis»."
    assert not _lo_ve_la_voz(sirius, "Betis")
    assert not _lo_ve_la_voz(sirius, "Atleti")


def test_la_voz_habla_en_el_modo_de_la_charla(sirius: _Sirius) -> None:
    sirius.di("Ponte serio, que esto es importante.")
    sirius.di("La clave de la alarma es Zarzamora.")
    sirius.modelo.voz = "Hecho."

    sirius.di("Olvida eso.")

    [voz] = sirius.modelo.voces
    assert MODE_INSTRUCTIONS[ConversationMode.SERIO] in voz.instructions
    assert not _lo_ve_la_voz(sirius, "Zarzamora")


def test_si_la_voz_se_cancela_la_orden_queda_cumplida_con_la_frase_de_siempre(
    sirius: _Sirius,
) -> None:
    sirius.di("La clave de la alarma es Zarzamora.")
    sirius.modelo.cancela_la_voz = True

    respuesta = sirius.di("Olvida eso.")

    assert respuesta == "Hecho: ya no lo recuerdo."
    assert len(sirius.modelo.voces) == 1
    with closing(sqlite3.connect(sirius.base)) as conexion:
        contenidos = [fila[0] or "" for fila in conexion.execute("SELECT content FROM messages")]
    assert not any("Zarzamora" in contenido for contenido in contenidos)


def test_si_preparar_la_voz_falla_la_orden_contesta_con_la_frase_de_siempre(
    sirius: _Sirius, monkeypatch: pytest.MonkeyPatch
) -> None:
    sirius.di("La clave de la alarma es Zarzamora.")
    sirius.modelo.voz = "Borrado."

    def rompe(*args: object, **kwargs: object) -> None:
        msg = "la base no contesta"
        raise RuntimeError(msg)

    monkeypatch.setattr(CommandVoice, "request", rompe)

    assert sirius.di("Olvida eso.") == "Hecho: ya no lo recuerdo."
    assert sirius.modelo.voces == []


def _ultima_respuesta(sirius: _Sirius) -> tuple[str | None, str | None]:
    """El texto y la operación de la última respuesta de Sirius guardada en la base."""
    with closing(sqlite3.connect(sirius.base)) as conexion:
        fila = conexion.execute(
            "SELECT content, operation_id FROM messages WHERE role = 'sirius' ORDER BY id DESC"
        ).fetchone()
    return (fila[0], fila[1]) if fila else (None, None)


def test_la_respuesta_de_siempre_ya_esta_guardada_cuando_se_pide_la_voz(sirius: _Sirius) -> None:
    """Ronda 1 de Codex: la orden se cumple y su respuesta se guarda antes de esperar al
    modelo; la voz la cambia después."""
    sirius.di("La clave de la alarma es Zarzamora.")
    vistas: list[tuple[str | None, str | None]] = []
    sirius.modelo.voz = "Borrado, jefe."
    sirius.modelo.al_pedir_la_voz = lambda: vistas.append(_ultima_respuesta(sirius))

    resultado = sirius.deps.send_message_use_case.send_message("Olvida eso.")

    [(texto, operacion)] = vistas
    assert texto == "Hecho: ya no lo recuerdo."
    assert operacion == resultado.sirius_message.operation_id
    assert resultado.sirius_message.content == "Borrado, jefe."
    assert _ultima_respuesta(sirius) == ("Borrado, jefe.", operacion)


def test_si_sirius_se_cierra_mientras_pone_la_voz_la_orden_ya_tiene_su_respuesta(
    sirius: _Sirius,
) -> None:
    sirius.di("La clave de la alarma es Zarzamora.")

    def se_cierra() -> None:
        raise SystemExit

    sirius.modelo.voz = "Borrado, jefe."
    sirius.modelo.al_pedir_la_voz = se_cierra

    with pytest.raises(SystemExit):
        sirius.di("Olvida eso.")

    texto, operacion = _ultima_respuesta(sirius)
    assert texto == "Hecho: ya no lo recuerdo."
    # Es la respuesta de esa orden: no queda como una orden sin respuesta.
    with closing(sqlite3.connect(sirius.base)) as conexion:
        [orden] = conexion.execute(
            "SELECT operation_id FROM messages WHERE role = 'user' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert operacion == orden
