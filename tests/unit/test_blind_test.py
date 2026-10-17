"""La prueba a ciegas: preguntas, barajado, recuento y caso de uso (pieza C de ADR-233)."""

from __future__ import annotations

import logging
import random
import threading
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from sirius.application.blind_test import BlindTestUseCase
from sirius.application.seed_examples import SeedExamplePicker
from sirius.domain.blind_test import (
    BLIND_TEST_QUESTIONS,
    BlindTestError,
    prepare_blind_test,
    tally,
)
from sirius.domain.identity import Identity, IdentityVersion, SeedExample
from sirius.domain.robot_seed import EXAMPLES_FRAME
from sirius.ports.llm import (
    LLMCancelled,
    LLMCompleted,
    LLMError,
    LLMErrorKind,
    LLMRequest,
    LLMStreamEvent,
)

_PREGUNTAS = ("¿Qué tal?", "Cuéntame un chiste.", "Ponte serio.")


def _respuestas(*modelos: str) -> dict[str, list[str]]:
    return {modelo: [f"{modelo} dice {n}" for n in range(len(_PREGUNTAS))] for modelo in modelos}


def test_son_20_preguntas_distintas() -> None:
    assert len(BLIND_TEST_QUESTIONS) == 20
    assert len(set(BLIND_TEST_QUESTIONS)) == 20


def test_la_hoja_lleva_todas_las_respuestas_y_la_clave_dice_de_quien_es_cada_una() -> None:
    hoja = prepare_blind_test(_PREGUNTAS, _respuestas("uno", "dos", "tres"), random.Random(7))

    assert hoja.models == ("uno", "dos", "tres")
    for indice, item in enumerate(hoja.items):
        assert item.question == _PREGUNTAS[indice]
        assert [letra for letra, _ in item.options] == ["A", "B", "C"]
        for (letra, texto), modelo in zip(item.options, hoja.key[indice], strict=True):
            assert texto == f"{modelo} dice {indice}", letra


def test_las_respuestas_no_llevan_el_nombre_del_modelo() -> None:
    respuestas = {"qwen-x": ["a", "b", "c"], "gemma-y": ["d", "e", "f"]}
    hoja = prepare_blind_test(_PREGUNTAS, respuestas, random.Random(1))

    for item in hoja.items:
        for _, texto in item.options:
            assert "qwen" not in texto and "gemma" not in texto


def test_con_la_misma_semilla_de_azar_sale_la_misma_hoja() -> None:
    una = prepare_blind_test(_PREGUNTAS, _respuestas("uno", "dos"), random.Random(3))
    otra = prepare_blind_test(_PREGUNTAS, _respuestas("uno", "dos"), random.Random(3))

    assert una == otra


@pytest.mark.parametrize("modelos", [("solo",), ("a", "b", "c", "d")])
def test_hacen_falta_entre_dos_y_tres_modelos(modelos: tuple[str, ...]) -> None:
    with pytest.raises(BlindTestError, match="entre 2 y 3"):
        prepare_blind_test(_PREGUNTAS, _respuestas(*modelos), random.Random(0))


def test_un_modelo_con_respuestas_de_menos_no_entra() -> None:
    respuestas = _respuestas("uno", "dos")
    respuestas["dos"] = respuestas["dos"][:2]

    with pytest.raises(BlindTestError, match="Faltan respuestas"):
        prepare_blind_test(_PREGUNTAS, respuestas, random.Random(0))


def _letra_de(hoja_key: tuple[str, ...], modelo: str) -> str:
    return "ABC"[hoja_key.index(modelo)]


def test_gana_el_modelo_que_mas_elige_el_propietario() -> None:
    hoja = prepare_blind_test(_PREGUNTAS, _respuestas("uno", "dos"), random.Random(5))
    elecciones = {
        0: _letra_de(hoja.key[0], "dos"),
        1: _letra_de(hoja.key[1], "dos"),
        2: _letra_de(hoja.key[2], "uno"),
    }

    resultado = tally(hoja, elecciones)

    assert resultado.votes == {"uno": 1, "dos": 2}
    assert resultado.winner == "dos"
    assert resultado.tied == ()


def test_con_empate_no_elige_por_el_propietario() -> None:
    hoja = prepare_blind_test(
        _PREGUNTAS[:2], {"uno": ["a", "b"], "dos": ["c", "d"]}, random.Random(2)
    )
    elecciones = {0: _letra_de(hoja.key[0], "uno"), 1: _letra_de(hoja.key[1], "dos")}

    resultado = tally(hoja, elecciones)

    assert resultado.winner is None
    assert set(resultado.tied) == {"uno", "dos"}


def test_hay_que_contestar_todas_las_preguntas() -> None:
    hoja = prepare_blind_test(_PREGUNTAS, _respuestas("uno", "dos"), random.Random(0))

    with pytest.raises(BlindTestError, match="cada pregunta"):
        tally(hoja, {0: "A", 1: "B"})


def test_una_letra_que_no_existe_no_cuenta() -> None:
    hoja = prepare_blind_test(_PREGUNTAS, _respuestas("uno", "dos"), random.Random(0))

    with pytest.raises(BlindTestError, match="no tiene respuesta"):
        tally(hoja, {0: "A", 1: "B", 2: "C"})


# --- El caso de uso ----------------------------------------------------------


class _Identidades:
    def get_or_create_current_identity(self) -> Identity:
        version = IdentityVersion(
            id=1,
            identity_id=1,
            version=3,
            name="Sirius",
            description="El software del robot.",
            personality_instructions="Gracioso ante todo.",
            created_at=datetime(2026, 10, 7, tzinfo=UTC),
        )
        return Identity(id=1, current_version=version, created_at=version.created_at)


class _Modelo:
    def __init__(self, nombre: str, *, falla: bool = False) -> None:
        self.nombre = nombre
        self.falla = falla
        self.peticiones: list[LLMRequest] = []

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        self.peticiones.append(request)
        if self.falla:
            yield LLMError(kind=LLMErrorKind.CONNECTION, message="No se pudo contactar.")
            return
        yield LLMCompleted(
            text=f"  {self.nombre}: {request.input_text}  ", input_tokens=1, output_tokens=1
        )

    def cancel(self, operation_id: str) -> None:
        del operation_id


def _conversa(nombre: str) -> tuple[str, ...]:
    """Lo que dice ``/api/show`` de un modelo de charla."""
    del nombre
    return ("completion", "tools")


class _Callado(_Modelo):
    """Un modelo que acaba sin decir nada."""

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        self.peticiones.append(request)
        return iter(())


def _caso(modelos: dict[str, _Modelo], elegidos: list[str]) -> BlindTestUseCase:
    return BlindTestUseCase(
        identity_repository=_Identidades(),  # type: ignore[arg-type]
        provider_for=lambda nombre: modelos[nombre],
        list_models=lambda: tuple(sorted(modelos)),
        model_capabilities=_conversa,
        choose_model=elegidos.append,
        current_model=lambda: elegidos[-1] if elegidos else None,
        rng=random.Random(11),
    )


def test_pregunta_cada_pregunta_a_cada_modelo_con_la_identidad_vigente() -> None:
    modelos = {"uno": _Modelo("uno"), "dos": _Modelo("dos")}
    avance: list[tuple[int, int]] = []

    hoja = _caso(modelos, []).prepare(
        ["uno", "dos"], on_progress=lambda h, t: avance.append((h, t))
    )

    for modelo in modelos.values():
        assert [p.input_text for p in modelo.peticiones] == list(BLIND_TEST_QUESTIONS)
        for peticion in modelo.peticiones:
            assert peticion.instructions.startswith("# Identidad (v3): Sirius")
            assert "Gracioso ante todo." in peticion.instructions
    assert avance[-1] == (40, 40)
    assert len(avance) == 40
    assert hoja.items[0].question == BLIND_TEST_QUESTIONS[0]
    assert {texto for _, texto in hoja.items[0].options} == {
        f"uno: {BLIND_TEST_QUESTIONS[0]}",
        f"dos: {BLIND_TEST_QUESTIONS[0]}",
    }


def test_si_un_modelo_no_contesta_la_prueba_se_para_y_dice_cual() -> None:
    modelos = {"uno": _Modelo("uno"), "dos": _Modelo("dos", falla=True)}

    with pytest.raises(BlindTestError, match="El modelo dos no contestó"):
        _caso(modelos, []).prepare(["uno", "dos"])


@pytest.mark.parametrize("dos", [_Modelo("dos", falla=True), _Callado("dos")])
def test_si_un_modelo_no_contesta_el_aviso_dice_que_hacer(dos: _Modelo) -> None:
    # En su ordenador el aviso solo decía qué modelo no contestó (ADR-247).
    with pytest.raises(BlindTestError) as error:
        _caso({"uno": _Modelo("uno"), "dos": dos}, []).prepare(["uno", "dos"])

    assert "El modelo dos" in str(error.value)
    assert str(error.value).endswith("Vuelve a pulsar Empezar; si se repite, desmarca ese modelo.")


def test_solo_ofrece_los_modelos_que_conversan_y_dice_por_que_deja_fuera_los_demas() -> None:
    # En su ordenador ofrecía también los de huellas (ADR-247).
    modelos = {nombre: _Modelo(nombre) for nombre in ("uno", "dos", "huellas", "raro")}

    def sabe(nombre: str) -> tuple[str, ...]:
        if nombre == "raro":
            msg = "Ollama no dijo qué sabe hacer"
            raise BlindTestError(msg)
        return ("embedding",) if nombre == "huellas" else ("completion", "tools")

    caso = BlindTestUseCase(
        identity_repository=_Identidades(),  # type: ignore[arg-type]
        provider_for=lambda nombre: modelos[nombre],
        list_models=lambda: tuple(sorted(modelos)),
        model_capabilities=sabe,
        choose_model=lambda _nombre: None,
        current_model=lambda: None,
    )

    ofrecidos = caso.installed_models()

    assert ofrecidos.chat == ("dos", "uno")
    assert ofrecidos.left_out == (
        ("huellas", "no conversa"),
        ("raro", "Ollama no dijo qué sabe hacer"),
    )


def test_elegir_lo_deja_como_modelo_de_la_charla() -> None:
    elegidos: list[str] = []
    caso = _caso({"uno": _Modelo("uno"), "dos": _Modelo("dos")}, elegidos)

    assert caso.chat_model() is None
    caso.choose("dos")

    assert elegidos == ["dos"]
    assert caso.chat_model() == "dos"
    assert caso.installed_models().chat == ("dos", "uno")


# --- ADR-240: los ejemplos de la semilla, pregunta a pregunta ---------------------------


class _IdentidadesConEjemplos(_Identidades):
    def get_or_create_current_identity(self) -> Identity:
        version = replace(
            super().get_or_create_current_identity().current_version,
            examples=tuple(
                SeedExample("Él", f"Frase número {n}.", f"Respuesta número {n}.")
                for n in range(1, 8)
            ),
        )
        return Identity(id=1, current_version=version, created_at=version.created_at)


def test_cada_pregunta_lleva_tres_ejemplos_y_todos_los_modelos_las_mismas_instrucciones() -> None:
    modelos = {"uno": _Modelo("uno"), "dos": _Modelo("dos")}
    caso = BlindTestUseCase(
        identity_repository=_IdentidadesConEjemplos(),  # type: ignore[arg-type]
        provider_for=lambda nombre: modelos[nombre],
        list_models=lambda: tuple(sorted(modelos)),
        model_capabilities=_conversa,
        choose_model=lambda _nombre: None,
        current_model=lambda: None,
        rng=random.Random(11),
        seed_examples=SeedExamplePicker(rng=random.Random(5)),
    )

    caso.prepare(["uno", "dos"])

    for de_uno, de_dos in zip(modelos["uno"].peticiones, modelos["dos"].peticiones, strict=True):
        assert de_uno.input_text == de_dos.input_text
        assert de_uno.instructions == de_dos.instructions
        assert EXAMPLES_FRAME in de_uno.instructions
        assert de_uno.instructions.count("\nSirius: «Respuesta número") == 3


class _SelectorQueApunta(SeedExamplePicker):
    """Elige como el de verdad y apunta para qué texto se le pide."""

    def __init__(self) -> None:
        super().__init__(rng=random.Random(5))
        self.textos: list[str] = []

    def pick(self, examples: Sequence[SeedExample], text: str) -> tuple[SeedExample, ...]:
        self.textos.append(text)
        return super().pick(examples, text)


def _caso_con(modelos: dict[str, _Modelo], selector: SeedExamplePicker) -> BlindTestUseCase:
    return BlindTestUseCase(
        identity_repository=_IdentidadesConEjemplos(),  # type: ignore[arg-type]
        provider_for=lambda nombre: modelos[nombre],
        list_models=lambda: tuple(sorted(modelos)),
        model_capabilities=_conversa,
        choose_model=lambda _nombre: None,
        current_model=lambda: None,
        rng=random.Random(11),
        seed_examples=selector,
    )


def test_cerrada_antes_de_empezar_no_elige_ejemplos_ni_pide_nada() -> None:
    """Ronda 2 de Codex: elegir los ejemplos pide huellas a Ollama; cerrar la ventana
    antes de empezar no puede dejar nada pidiéndose."""
    modelos = {"uno": _Modelo("uno")}
    selector = _SelectorQueApunta()

    with pytest.raises(BlindTestError, match="canceló"):
        _caso_con(modelos, selector).prepare(["uno"], should_stop=lambda: True)

    assert selector.textos == []
    assert modelos["uno"].peticiones == []


def test_cerrada_a_medias_solo_eligio_los_ejemplos_de_lo_preguntado_y_una_vez() -> None:
    modelos = {"uno": _Modelo("uno"), "dos": _Modelo("dos")}
    selector = _SelectorQueApunta()
    caso = _caso_con(modelos, selector)
    preguntas = caso.questions()
    hechas: list[int] = []

    def para_en_la_tercera_del_segundo() -> bool:
        hechas.append(1)
        return len(hechas) > len(preguntas) + 2

    with pytest.raises(BlindTestError, match="canceló"):
        caso.prepare(["uno", "dos"], should_stop=para_en_la_tercera_del_segundo)

    assert selector.textos == list(preguntas)
    assert len(modelos["dos"].peticiones) == 2


# --- Un fallo suelto, un «Empezar» después de un fallo y cerrar a mitad (incidencia #696) ---


class _FallaUnasVeces(_Modelo):
    """Falla las primeras ``veces`` que le preguntan ``pregunta``; después contesta."""

    def __init__(self, nombre: str, pregunta: str, veces: int) -> None:
        super().__init__(nombre)
        self.pregunta = pregunta
        self.quedan = veces

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        if request.input_text == self.pregunta and self.quedan > 0:
            self.quedan -= 1
            self.peticiones.append(request)
            return iter([LLMError(kind=LLMErrorKind.CONNECTION, message="No se pudo contactar.")])
        return super().stream_response(request)


@pytest.fixture
def diario() -> Iterator[list[str]]:
    """Lo que apunta en el diario el caso de uso, leído de su propio registrador."""
    registrador = logging.getLogger("sirius.application.blind_test")
    apuntado: list[str] = []

    class _Apunta(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            apuntado.append(record.getMessage())

    manejador = _Apunta()
    registrador.addHandler(manejador)
    try:
        yield apuntado
    finally:
        registrador.removeHandler(manejador)


def test_una_respuesta_que_falla_una_vez_se_vuelve_a_pedir_y_la_prueba_sigue() -> None:
    tercera = BLIND_TEST_QUESTIONS[2]
    dos = _FallaUnasVeces("dos", tercera, veces=1)

    hoja = _caso({"uno": _Modelo("uno"), "dos": dos}, []).prepare(["uno", "dos"])

    assert len(hoja.items) == 20
    assert [p.input_text for p in dos.peticiones].count(tercera) == 2


def test_si_vuelve_a_fallar_para_y_el_diario_dice_donde_y_con_que_modelo(
    diario: list[str],
) -> None:
    quinta = BLIND_TEST_QUESTIONS[4]
    dos = _FallaUnasVeces("dos", quinta, veces=2)

    with pytest.raises(BlindTestError, match="El modelo dos no contestó"):
        _caso({"uno": _Modelo("uno"), "dos": dos}, []).prepare(["uno", "dos"])

    # Las 20 de «uno», cuatro de «dos» y la quinta de «dos», que falla dos veces.
    assert diario == ["La prueba a ciegas falló en 25 de 40, con el modelo dos"]
    assert [p.input_text for p in dos.peticiones].count(quinta) == 2


def test_empezar_otra_vez_pide_solo_las_que_faltan() -> None:
    quinta = BLIND_TEST_QUESTIONS[4]
    uno, dos = _Modelo("uno"), _FallaUnasVeces("dos", quinta, veces=2)
    caso = _caso({"uno": uno, "dos": dos}, [])
    with pytest.raises(BlindTestError):
        caso.prepare(["uno", "dos"])
    antes_uno, antes_dos = len(uno.peticiones), len(dos.peticiones)

    hoja = caso.prepare(["uno", "dos"])

    assert len(hoja.items) == 20
    assert uno.peticiones[antes_uno:] == []
    assert [p.input_text for p in dos.peticiones[antes_dos:]] == list(BLIND_TEST_QUESTIONS[4:])


class _IdentidadesQueCambian(_Identidades):
    """La identidad vigente, con una versión que la prueba puede cambiar."""

    def __init__(self) -> None:
        self.version_id = 1

    def get_or_create_current_identity(self) -> Identity:
        version = replace(
            super().get_or_create_current_identity().current_version, id=self.version_id
        )
        return Identity(id=1, current_version=version, created_at=version.created_at)


def test_con_otra_version_de_la_identidad_se_vuelve_a_pedir_todo() -> None:
    uno, dos = _Modelo("uno"), _Modelo("dos")
    identidades = _IdentidadesQueCambian()
    caso = BlindTestUseCase(
        identity_repository=identidades,  # type: ignore[arg-type]
        provider_for=lambda nombre: {"uno": uno, "dos": dos}[nombre],
        list_models=lambda: ("dos", "uno"),
        model_capabilities=_conversa,
        choose_model=lambda _nombre: None,
        current_model=lambda: None,
    )
    caso.prepare(["uno", "dos"])
    caso.prepare(["uno", "dos"])
    assert len(uno.peticiones) == len(dos.peticiones) == 20

    identidades.version_id = 2
    caso.prepare(["uno", "dos"])

    assert len(uno.peticiones) == len(dos.peticiones) == 40


class _QueEspera(_Modelo):
    """Un modelo que no acaba de contestar hasta que se corta su petición."""

    def __init__(self, nombre: str) -> None:
        super().__init__(nombre)
        self.preguntando = threading.Event()
        self.cortadas: list[str] = []
        self._corte = threading.Event()

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        self.peticiones.append(request)
        self.preguntando.set()
        self._corte.wait(timeout=5)
        yield LLMCancelled(partial_text="")

    def cancel(self, operation_id: str) -> None:
        self.cortadas.append(operation_id)
        self._corte.set()


def test_cerrar_a_mitad_corta_la_respuesta_en_curso_y_no_la_vuelve_a_pedir(
    diario: list[str],
) -> None:
    lento = _QueEspera("uno")
    caso = _caso({"uno": lento, "dos": _Modelo("dos")}, [])
    errores: list[BaseException] = []

    def preparar() -> None:
        try:
            caso.prepare(["uno", "dos"])
        except BlindTestError as exc:
            errores.append(exc)

    hilo = threading.Thread(target=preparar)
    hilo.start()
    assert lento.preguntando.wait(timeout=5)

    caso.cancel()
    hilo.join(timeout=5)

    assert not hilo.is_alive()
    assert lento.cortadas == ["prueba-a-ciegas-1"]
    assert [str(e) for e in errores] == ["La prueba a ciegas se canceló."]
    assert len(lento.peticiones) == 1
    assert diario == []


class _QueRecuerdaElCorte(_Modelo):
    """Como el proveedor de verdad: un corte pedido antes de que empiece la respuesta se
    cumple en cuanto empieza, sin contestar."""

    def __init__(self, nombre: str) -> None:
        super().__init__(nombre)
        self.cortadas: list[str] = []
        self.contestadas: list[str] = []

    def stream_response(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        self.peticiones.append(request)
        if request.operation_id in self.cortadas:
            yield LLMCancelled(partial_text="")
            return
        self.contestadas.append(request.operation_id)
        yield LLMCompleted(
            text=f"{self.nombre}: {request.input_text}", input_tokens=1, output_tokens=1
        )

    def cancel(self, operation_id: str) -> None:
        self.cortadas.append(operation_id)


class _SelectorQueCierra(_SelectorQueApunta):
    """Elegir los ejemplos pide huellas a Ollama y tarda: mientras, se cierra la hoja."""

    def __init__(self, cierra: Callable[[], None]) -> None:
        super().__init__()
        self._cierra = cierra

    def pick(self, examples: Sequence[SeedExample], text: str) -> tuple[SeedExample, ...]:
        self._cierra()
        return super().pick(examples, text)


def test_cerrar_mientras_elige_los_ejemplos_corta_la_respuesta_que_viene_detras() -> None:
    """El cierre no se pierde entre mirar si se cerró y pedir la respuesta: si llega
    mientras se eligen los ejemplos, la respuesta que viene detrás se corta y no se espera
    entera."""
    modelo = _QueRecuerdaElCorte("uno")
    cerrada = threading.Event()

    def cierra() -> None:
        # Lo que hace la hoja al cerrarse (BlindTestWorker.stop): marca, y corta.
        cerrada.set()
        caso.cancel()

    caso = _caso_con({"uno": modelo}, _SelectorQueCierra(cierra))

    with pytest.raises(BlindTestError, match="canceló"):
        caso.prepare(["uno"], should_stop=cerrada.is_set)

    assert modelo.cortadas == ["prueba-a-ciegas-1"]
    assert modelo.contestadas == []


def test_un_cierre_justo_despues_de_mirar_si_se_cerro_tampoco_se_pierde() -> None:
    """La hoja marca que se cierra y después corta lo que se esté pidiendo; la prueba, al
    revés: apunta lo que va a pedir y después mira si se cerró. Así, aunque el cierre
    llegue justo después de mirar, el corte encuentra la respuesta apuntada."""
    modelo = _QueRecuerdaElCorte("uno")
    cerrada = threading.Event()

    def mira_y_justo_se_cierra() -> bool:
        visto = cerrada.is_set()
        if not visto:
            cerrada.set()
            caso.cancel()
        return visto

    caso = _caso_con({"uno": modelo}, _SelectorQueApunta())

    with pytest.raises(BlindTestError, match="canceló"):
        caso.prepare(["uno"], should_stop=mira_y_justo_se_cierra)

    assert modelo.cortadas == ["prueba-a-ciegas-1"]
    assert modelo.contestadas == []


def test_cortar_cuando_ya_acabo_no_deja_un_corte_apuntado() -> None:
    """``cancel()`` corta solo lo que se está pidiendo: con la prueba ya preparada no deja
    un corte que cayera sobre la próxima vez que se pidiera esa pregunta."""
    modelos = {"uno": _QueRecuerdaElCorte("uno"), "dos": _QueRecuerdaElCorte("dos")}
    caso = _caso_con(modelos, _SelectorQueApunta())  # type: ignore[arg-type]
    caso.prepare(["uno", "dos"])

    caso.cancel()

    assert [m.cortadas for m in modelos.values()] == [[], []]


class _SelectorQueTardaLaPrimeraVez(_SelectorQueApunta):
    """Elegir los ejemplos pide huellas a Ollama y puede tardar segundos: la primera vez, el
    de la primera pasada, tarda hasta que lo sueltan."""

    def __init__(self) -> None:
        super().__init__()
        self.eligiendo = threading.Event()
        self.suelta = threading.Event()

    def pick(self, examples: Sequence[SeedExample], text: str) -> tuple[SeedExample, ...]:
        if not self.eligiendo.is_set():
            self.eligiendo.set()
            self.suelta.wait(timeout=5)
        return super().pick(examples, text)


def test_con_dos_pasadas_solapadas_cerrar_la_segunda_corta_su_respuesta() -> None:
    """Se cierra la hoja mientras elige los ejemplos, y se vuelve a empezar antes de que esa
    pasada acabe. Al acabar, la primera no puede llevarse lo que está pidiendo la segunda:
    si no, cerrar la segunda ya no la cortaría y se esperaría su respuesta entera (#696)."""
    pedidos: list[_QueEspera] = []

    def nuevo(nombre: str) -> _QueEspera:
        # Como el de verdad: cada pasada, un proveedor nuevo para cada modelo.
        pedidos.append(_QueEspera(nombre))
        return pedidos[-1]

    selector = _SelectorQueTardaLaPrimeraVez()
    caso = BlindTestUseCase(
        identity_repository=_IdentidadesConEjemplos(),  # type: ignore[arg-type]
        provider_for=nuevo,
        list_models=lambda: ("uno",),
        model_capabilities=_conversa,
        choose_model=lambda _nombre: None,
        current_model=lambda: None,
        rng=random.Random(11),
        seed_examples=selector,
    )
    para_la_primera, para_la_segunda = threading.Event(), threading.Event()

    def pasada(parar: threading.Event) -> None:
        with pytest.raises(BlindTestError, match="canceló"):
            caso.prepare(["uno"], should_stop=parar.is_set)

    primera = threading.Thread(target=pasada, args=(para_la_primera,))
    primera.start()
    assert selector.eligiendo.wait(timeout=5)
    para_la_primera.set()  # se cierra la primera hoja
    caso.cancel()
    segunda = threading.Thread(target=pasada, args=(para_la_segunda,))
    segunda.start()
    assert len(pedidos) == 2
    assert pedidos[1].preguntando.wait(timeout=5)
    selector.suelta.set()  # la primera acaba de desenrollarse
    primera.join(timeout=5)
    assert not primera.is_alive()

    para_la_segunda.set()  # se cierra la segunda hoja
    caso.cancel()
    segunda.join(timeout=2)

    assert not segunda.is_alive(), "cerrar la segunda esperaría su respuesta entera"
    assert pedidos[1].cortadas == ["prueba-a-ciegas-1"]
