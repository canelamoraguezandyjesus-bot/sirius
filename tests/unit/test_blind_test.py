"""La prueba a ciegas: preguntas, barajado, recuento y caso de uso (pieza C de ADR-233)."""

from __future__ import annotations

import random
from collections.abc import Iterable
from datetime import UTC, datetime

import pytest

from sirius.application.blind_test import BlindTestUseCase
from sirius.domain.blind_test import (
    BLIND_TEST_QUESTIONS,
    BlindTestError,
    prepare_blind_test,
    tally,
)
from sirius.domain.identity import Identity, IdentityVersion
from sirius.ports.llm import LLMCompleted, LLMError, LLMErrorKind, LLMRequest, LLMStreamEvent

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


def _caso(modelos: dict[str, _Modelo], elegidos: list[str]) -> BlindTestUseCase:
    return BlindTestUseCase(
        identity_repository=_Identidades(),  # type: ignore[arg-type]
        provider_for=lambda nombre: modelos[nombre],
        list_models=lambda: tuple(sorted(modelos)),
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


def test_elegir_lo_deja_como_modelo_de_la_charla() -> None:
    elegidos: list[str] = []
    caso = _caso({"uno": _Modelo("uno"), "dos": _Modelo("dos")}, elegidos)

    assert caso.chat_model() is None
    caso.choose("dos")

    assert elegidos == ["dos"]
    assert caso.chat_model() == "dos"
    assert caso.installed_models() == ("dos", "uno")
