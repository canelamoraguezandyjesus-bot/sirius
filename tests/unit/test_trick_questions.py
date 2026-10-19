"""El banco de las 40 preguntas trampa (pieza E de ADR-233, PA-R02-09)."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import pytest

from sirius.application.age import care_block
from sirius.application.trick_questions import TrickQuestionsError, TrickQuestionsUseCase
from sirius.domain.identity import Identity, IdentityVersion
from sirius.domain.reply_judge import TrickVerdict
from sirius.domain.trick_questions import TRICK_QUESTIONS
from sirius.ports.llm import LLMCompleted, LLMError, LLMErrorKind, LLMRequest, LLMStreamEvent


def test_son_40_numeradas_seguidas_y_ninguna_repetida() -> None:
    assert [question.id for question in TRICK_QUESTIONS] == [f"T{n:02d}" for n in range(1, 41)]
    assert len({question.bad_idea for question in TRICK_QUESTIONS}) == 40


def test_cada_idea_mala_va_con_su_porque_y_en_boca_del_propietario() -> None:
    for question in TRICK_QUESTIONS:
        assert question.bad_idea.strip().endswith(".")
        assert question.why_bad.strip()
        assert question.why_bad != question.bad_idea


# --- ADR-253: el reintento, lo ya contestado, cortar al cerrar y lo que cuenta el juez ---


class _Identidades:
    def __init__(self) -> None:
        self.version = 2

    def get_current_identity(self) -> Identity:
        version = IdentityVersion(
            id=self.version,
            identity_id=1,
            version=self.version,
            name="Sirius",
            description="El software del robot.",
            personality_instructions="Gracioso ante todo.",
            created_at=datetime(2026, 10, 7, tzinfo=UTC),
        )
        return Identity(id=1, current_version=version, created_at=version.created_at)


class _Modelo:
    """Contesta a cada idea mala; las de ``falla`` fallan esas veces antes de contestar."""

    def __init__(self, falla: dict[str, int] | None = None) -> None:
        self.falla = dict(falla or {})
        self.pedidas: list[str] = []
        self.instrucciones: list[str] = []
        self.cortadas: list[str] = []

    def health_check(self) -> bool:
        return True

    def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        self.pedidas.append(request.input_text)
        self.instrucciones.append(request.instructions)
        if self.falla.get(request.input_text, 0) > 0:
            self.falla[request.input_text] -= 1
            yield LLMError(kind=LLMErrorKind.CONNECTION, message="Ollama se cayó.")
            return
        yield LLMCompleted(
            text=f"Ni de broma: {request.input_text}", input_tokens=1, output_tokens=1
        )

    def cancel(self, operation_id: str) -> None:
        self.cortadas.append(operation_id)


class _Juez:
    def __init__(self, calla_en: frozenset[str] = frozenset()) -> None:
        self.calla_en = calla_en

    def score(self, reply: str, *, should_stop: Callable[[], bool] | None = None) -> int:
        del reply, should_stop
        return 5

    def verdict(
        self, bad_idea: str, reply: str, *, should_stop: Callable[[], bool] | None = None
    ) -> TrickVerdict:
        del reply, should_stop
        if bad_idea in self.calla_en:
            msg = "el juez no contesta"
            raise RuntimeError(msg)
        return TrickVerdict.DISCREPA

    def cancel(self) -> None:
        pass

    def cancel_verdicts(self) -> None:
        pass


def _caso(
    modelo: _Modelo, identidades: _Identidades | None = None, juez: _Juez | None = None
) -> TrickQuestionsUseCase:
    return TrickQuestionsUseCase(
        identidades or _Identidades(),  # type: ignore[arg-type]
        local_chat_provider=lambda: modelo,
        judge=juez or _Juez(),
    )


_T05 = TRICK_QUESTIONS[4].bad_idea


def test_una_respuesta_que_falla_se_pide_otra_vez_y_no_se_para() -> None:
    modelo = _Modelo(falla={_T05: 1})

    respuestas = _caso(modelo).run()

    assert len(respuestas) == 40
    assert len(modelo.pedidas) == 41
    assert modelo.pedidas.count(_T05) == 2


def test_si_falla_otra_vez_para_y_volver_a_empezar_pide_solo_las_que_faltan() -> None:
    modelo = _Modelo(falla={_T05: 2})
    caso = _caso(modelo)

    with pytest.raises(TrickQuestionsError, match="Ollama se cayó"):
        caso.run()
    assert len(modelo.pedidas) == 6  # T01 a T04, y T05 dos veces
    modelo.pedidas.clear()

    respuestas = caso.run()

    assert [r.question.id for r in respuestas] == [q.id for q in TRICK_QUESTIONS]
    assert modelo.pedidas == [q.bad_idea for q in TRICK_QUESTIONS[4:]]


def test_con_otro_modelo_o_con_otra_semilla_se_vuelven_a_pedir_todas() -> None:
    identidades = _Identidades()
    modelo = _Modelo()
    caso = _caso(modelo, identidades)
    caso.run()
    assert len(modelo.pedidas) == 40
    caso.run()
    assert len(modelo.pedidas) == 40

    identidades.version = 3
    caso.run()
    assert len(modelo.pedidas) == 80

    otro = _Modelo()
    caso._local_chat_provider = lambda: otro
    caso.run()
    assert len(otro.pedidas) == 40


def test_cortar_al_cerrar_corta_la_que_esta_en_marcha_y_no_la_vuelve_a_pedir() -> None:
    pedida = threading.Event()
    cortada = threading.Event()
    parar = threading.Event()

    class _Lento(_Modelo):
        def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
            self.pedidas.append(request.operation_id)
            pedida.set()
            cortada.wait(5)
            yield LLMError(kind=LLMErrorKind.UNKNOWN, message="cortada")

        def cancel(self, operation_id: str) -> None:
            super().cancel(operation_id)
            cortada.set()

    modelo = _Lento()
    caso = _caso(modelo)
    respuestas: list[object] = []
    hilo = threading.Thread(target=lambda: respuestas.extend(caso.run(should_stop=parar.is_set)))
    hilo.start()
    assert pedida.wait(5)

    parar.set()
    caso.cancel_requests()
    hilo.join(5)

    assert not hilo.is_alive()
    assert modelo.cortadas == modelo.pedidas  # la que estaba en marcha, y no se pidió otra
    assert respuestas == []


def test_un_corte_entre_mirar_y_pedir_no_deja_salir_la_peticion() -> None:
    # Se cierra la hoja justo después de mirar si había que parar y antes de pedir: la
    # petición se apunta antes de volver a mirar, así que, o se corta, o no sale.
    modelo = _Modelo()
    miradas = iter([False])

    respuestas = _caso(modelo).run(should_stop=lambda: next(miradas, True))

    assert respuestas == ()
    assert modelo.pedidas == []


class _JuezQueCuenta(_Juez):
    def __init__(self) -> None:
        super().__init__()
        self.juzgadas: list[str] = []

    def verdict(
        self, bad_idea: str, reply: str, *, should_stop: Callable[[], bool] | None = None
    ) -> TrickVerdict:
        self.juzgadas.append(bad_idea)
        return super().verdict(bad_idea, reply, should_stop=should_stop)


def test_si_cierran_mientras_contesta_no_se_pide_el_veredicto_y_la_respuesta_se_queda() -> None:
    # Ronda 1 de Codex sobre la #698: la respuesta ya pagada no se tira al cerrar la hoja
    # (ADR-253); volver a empezar solo le pide el veredicto.
    modelo = _Modelo()
    juez = _JuezQueCuenta()
    caso = _caso(modelo, juez=juez)
    miradas = iter([False, False])  # antes de la pregunta y antes de pedirla

    assert caso.run(should_stop=lambda: next(miradas, True)) == ()
    assert modelo.pedidas == [TRICK_QUESTIONS[0].bad_idea]
    assert juez.juzgadas == []

    respuestas = caso.run()

    assert modelo.pedidas.count(TRICK_QUESTIONS[0].bad_idea) == 1
    assert len(modelo.pedidas) == 40
    assert juez.juzgadas == [q.bad_idea for q in TRICK_QUESTIONS]
    assert [r.judge_verdict for r in respuestas] == [TrickVerdict.DISCREPA] * 40


def test_cerrar_con_el_veredicto_en_marcha_lo_corta_y_la_respuesta_se_queda(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Ronda 1 de Codex sobre la #698: cerrar la hoja con el juez dando su veredicto lo
    # corta, como a las respuestas. No es que el juez calle, y la respuesta pagada se queda.
    pedido = threading.Event()
    cortado = threading.Event()
    parar = threading.Event()

    class _JuezLento(_JuezQueCuenta):
        def __init__(self) -> None:
            super().__init__()
            self.cortes = 0
            self.lento = True

        def verdict(
            self, bad_idea: str, reply: str, *, should_stop: Callable[[], bool] | None = None
        ) -> TrickVerdict:
            if self.lento:
                self.juzgadas.append(bad_idea)
                pedido.set()
                if cortado.wait(5):
                    msg = "El juez no terminó."
                    raise RuntimeError(msg)
                return TrickVerdict.DISCREPA
            return super().verdict(bad_idea, reply, should_stop=should_stop)

        def cancel_verdicts(self) -> None:
            self.cortes += 1
            cortado.set()

    modelo = _Modelo()
    juez = _JuezLento()
    caso = _caso(modelo, juez=juez)
    respuestas: list[object] = []
    hilo = threading.Thread(target=lambda: respuestas.extend(caso.run(should_stop=parar.is_set)))
    with caplog.at_level(logging.WARNING):
        hilo.start()
        assert pedido.wait(5)
        parar.set()
        caso.cancel_requests()
        hilo.join(3)

        assert not hilo.is_alive()
        assert juez.cortes == 1
        assert respuestas == []
        assert "veredicto" not in caplog.text

    juez.lento = False
    otra_vez = caso.run()

    t01 = TRICK_QUESTIONS[0].bad_idea
    assert modelo.pedidas.count(t01) == 1
    assert juez.juzgadas.count(t01) == 2
    assert otra_vez[0].judge_verdict is TrickVerdict.DISCREPA


def test_la_respuesta_sin_veredicto_no_vale_con_otra_semilla() -> None:
    identidades = _Identidades()
    modelo = _Modelo()
    caso = _caso(modelo, identidades)
    miradas = iter([False, False])
    caso.run(should_stop=lambda: next(miradas, True))
    assert len(modelo.pedidas) == 1

    identidades.version = 3
    caso.run()

    assert modelo.pedidas.count(TRICK_QUESTIONS[0].bad_idea) == 2


def test_el_juez_que_no_contesta_se_cuenta_aparte_y_el_diario_lleva_solo_identificadores(
    caplog: pytest.LogCaptureFixture,
) -> None:
    calla = frozenset(q.bad_idea for q in TRICK_QUESTIONS[9::10])  # T10, T20, T30 y T40
    caso = _caso(_Modelo(), juez=_Juez(calla_en=calla))
    respuestas = caso.run()
    marcas = {q.id: q.id not in {"T01", "T02"} for q in TRICK_QUESTIONS}

    with caplog.at_level(logging.INFO):
        resultado = caso.result(respuestas, marcas)

    assert (resultado.contrary, resultado.total) == (38, 40)
    # Discrepa de él en T01 y T02; en T10, T20, T30 y T40 no contestó, que es otra cosa.
    assert [q.id for q in resultado.judge_differs] == ["T01", "T02"]
    assert resultado.judge_disagreements == 2
    assert [q.id for q in resultado.judge_silent] == ["T10", "T20", "T30", "T40"]
    assert [q.id for q in resultado.agreed] == ["T01", "T02"]
    assert not resultado.judge_is_reliable  # un juez que no contesta tampoco vale para avisar
    [linea] = [r.getMessage() for r in caplog.records if "Preguntas trampa" in r.getMessage()]
    assert "38 de 40" in linea
    assert "T01, T02 (2)" in linea
    assert "T10, T20, T30, T40 (4)" in linea
    assert not any(q.bad_idea in linea for q in TRICK_QUESTIONS)
    assert "Ni de broma" not in linea


# --- La regla de no insultar (ronda 2 de Codex sobre la PR #703) ----------------------


def _caso_con_regla(modelo: _Modelo, regla: Callable[[], str]) -> TrickQuestionsUseCase:
    return TrickQuestionsUseCase(
        _Identidades(),  # type: ignore[arg-type]
        local_chat_provider=lambda: modelo,
        judge=_Juez(),
        reminder="El recordatorio de la semilla.",
        care=regla,
    )


def test_con_alguien_delante_que_la_pide_lleva_la_regla_antes_del_recordatorio() -> None:
    # Las respuestas se enseñan como de Sirius: con un crío delante, también se corta.
    modelo = _Modelo()

    _caso_con_regla(modelo, care_block).run()

    assert len(modelo.instrucciones) == 40
    for instrucciones in modelo.instrucciones:
        assert instrucciones.endswith(f"{care_block()}\n\nEl recordatorio de la semilla.")


def test_la_regla_se_mira_en_cada_pregunta() -> None:
    modelo = _Modelo()
    miradas: list[int] = []

    def regla() -> str:
        miradas.append(len(miradas))
        return care_block() if len(miradas) % 2 else ""

    _caso_con_regla(modelo, regla).run()

    assert len(miradas) == 40
    assert [care_block() in i for i in modelo.instrucciones] == [n % 2 == 0 for n in range(40)]


def test_al_volver_a_pedir_una_respuesta_que_fallo_la_regla_se_mira_otra_vez() -> None:
    """Ronda 3 de Codex sobre la PR #703: lo que tarda en fallar una petición es tiempo para
    que llegue alguien; la que se vuelve a pedir lleva la regla de ese momento. Y la
    respuesta se guarda con la regla con que se pidió."""
    regla = [""]

    class _FallaYLlegaUnCrio(_Modelo):
        def stream_response(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
            if self.falla.get(request.input_text, 0) > 0:
                regla[0] = care_block()
            return super().stream_response(request)

    modelo = _FallaYLlegaUnCrio(falla={_T05: 1})
    caso = _caso_con_regla(modelo, lambda: regla[0])

    caso.run()

    pares = zip(modelo.pedidas, modelo.instrucciones, strict=True)
    fallida, repetida = [i for p, i in pares if p == _T05]
    assert care_block() not in fallida
    assert care_block() in repetida
    antes = len(modelo.pedidas)
    caso.run()
    assert modelo.pedidas[antes:] == [q.bad_idea for q in TRICK_QUESTIONS[:4]], (
        "con la regla, solo las cuatro que se pidieron sin ella"
    )


def test_una_respuesta_pedida_sin_la_regla_no_vale_cuando_hace_falta() -> None:
    modelo = _Modelo()
    regla = [""]
    caso = _caso_con_regla(modelo, lambda: regla[0])
    caso.run()
    regla[0] = care_block()

    caso.run()

    assert len(modelo.pedidas) == 80, "se vuelven a pedir todas"
    assert all(care_block() in i for i in modelo.instrucciones[40:])
