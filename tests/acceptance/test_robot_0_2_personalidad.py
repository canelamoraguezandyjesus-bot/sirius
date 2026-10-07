"""Pruebas de aceptación de la versión 0.2 del robot: la personalidad.

Salen de la sección 0.2 de ``docs/evolution/PLAN_DEL_ROBOT.md`` (§4), de su
«terminado cuando» y de lo que se hace, y están escritas antes del código como
pide su §3 (ADR-233). Cada una lleva el identificador ``PA-R02-NN`` de
``docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md``, donde está también lo que solo
puede juzgar el propietario.

Usan dobles deterministas a propósito: demuestran que la semilla, los modos,
las marcas y el juez llegan donde deben. Que Sirius tenga gracia no lo demuestra
ninguna máquina; eso lo dicen las evaluaciones del propietario.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conductor_robot_0_2 import (
    Conductor,
    HojaACiegas,
    JuezDeMentira,
    OllamaDeMentira,
    ResumidorDeMentira,
    pieza,
    seccion,
)

pytestmark = pytest.mark.acceptance

_LOCAL = {"localhost", "127.0.0.1"}


# --- PA-R02-01 · La semilla del robot ----------------------------------------


@pieza("B", "toda petición al modelo lleva la semilla del robot con sus ejemplos")
def test_toda_peticion_al_modelo_lleva_la_semilla_del_robot_con_sus_ejemplos(
    tmp_path: Path,
) -> None:
    conductor = Conductor(tmp_path)
    semilla = conductor.semilla_del_robot()

    for frase in ("Buenos días, Sirius.", "¿Qué estás haciendo?", "Me voy a pedir otra pizza."):
        conductor.di(frase)

    assert 15 <= len(semilla.ejemplos) <= 20
    assert len(conductor.peticiones) == 3
    for peticion in conductor.peticiones:
        assert semilla.instrucciones in peticion.instrucciones
        for propietario, sirius in semilla.ejemplos:
            assert propietario in peticion.instrucciones
            assert sirius in peticion.instrucciones


@pieza("B", "una base de 0.1 abre con la semilla del robot como versión nueva y conserva la vieja")
def test_una_base_de_0_1_abre_con_la_semilla_del_robot_como_version_nueva(
    tmp_path: Path,
) -> None:
    conductor = Conductor.desde_una_base_de_0_1(tmp_path)
    semilla = conductor.semilla_del_robot()

    version, texto = conductor.identidad_vigente()
    assert (version, texto) == (2, semilla.instrucciones)
    assert "Rasgos nucleares" in conductor.identidad_en_la_version(1)

    conductor.reabre()
    assert conductor.identidad_vigente() == (2, semilla.instrucciones)


# --- PA-R02-02 · La charla va por un modelo local -----------------------------


@pieza("C", "con Ollama elegido, la charla va al modelo local elegido")
def test_con_ollama_elegido_la_charla_va_al_modelo_local_elegido(tmp_path: Path) -> None:
    ollama = OllamaDeMentira(respuesta="Buenos días los tuyos.")
    conductor = Conductor(tmp_path)
    conductor.charla_por_ollama("modelo-elegido", ollama)

    respuesta = conductor.di("Buenos días, Sirius.")

    assert respuesta == "Buenos días los tuyos."
    assert ollama.llamadas_a("/api/chat") == 1
    assert ollama.modelos == ["modelo-elegido"]
    assert {url.host for url in ollama.urls} <= _LOCAL


@pieza("C", "la charla con Ollama solo puede ir a este ordenador, ni con un ajuste a mano")
def test_la_charla_con_ollama_solo_puede_ir_a_este_ordenador(tmp_path: Path) -> None:
    ollama = OllamaDeMentira()
    conductor = Conductor(tmp_path, ajustes={"ollama_base_url": "http://ejemplo.com:11434"})
    conductor.charla_por_ollama("modelo-elegido", ollama)

    conductor.di("¿Dónde estás?")

    assert ollama.urls, "la charla no llegó a Ollama"
    assert {url.host for url in ollama.urls} <= _LOCAL


# --- PA-R02-03 · La prueba a ciegas ------------------------------------------

_MODELOS = ("qwen-de-prueba", "gemma-de-prueba", "mistral-de-prueba")
_FRUTAS = dict(zip(_MODELOS, ("pera", "manzana", "uva"), strict=True))


def _hoja(conductor: Conductor) -> HojaACiegas:
    preguntas = conductor.preguntas_de_la_prueba_a_ciegas()
    respuestas = {
        modelo: [f"{_FRUTAS[modelo]} {n}" for n in range(1, len(preguntas) + 1)]
        for modelo in _MODELOS
    }
    return conductor.prueba_a_ciegas(respuestas)


def _letra(hoja: HojaACiegas, indice: int, respuesta: str) -> str:
    return next(
        letra for letra, texto in hoja.preguntas[indice].respuestas.items() if texto == respuesta
    )


@pieza("C", "la hoja de la prueba a ciegas baraja las respuestas y no nombra ningún modelo")
def test_la_hoja_a_ciegas_baraja_las_respuestas_y_no_nombra_ningun_modelo(
    tmp_path: Path,
) -> None:
    conductor = Conductor(tmp_path)
    assert len(conductor.preguntas_de_la_prueba_a_ciegas()) == 20

    hoja = _hoja(conductor)

    assert len(hoja.preguntas) == 20
    for n, pregunta in enumerate(hoja.preguntas, start=1):
        assert sorted(pregunta.respuestas.values()) == sorted(f"{f} {n}" for f in _FRUTAS.values())
        for respuesta in pregunta.respuestas.values():
            assert respuesta in hoja.lo_que_ve_el_propietario
    for modelo in _MODELOS:
        assert modelo not in hoja.lo_que_ve_el_propietario
    for fruta in _FRUTAS.values():
        letras = {_letra(hoja, i, f"{fruta} {i + 1}") for i in range(len(hoja.preguntas))}
        assert len(letras) > 1, f"las respuestas de «{fruta}» salen siempre con la misma letra"


@pieza("C", "el modelo que más elige el propietario queda como modelo de la charla")
def test_el_modelo_que_mas_elige_el_propietario_queda_para_la_charla(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    hoja = _hoja(conductor)
    elecciones = {
        i: _letra(hoja, i, f"{_FRUTAS['gemma-de-prueba']} {i + 1}")
        for i in range(len(hoja.preguntas))
    }

    assert conductor.elige_a_ciegas(hoja, elecciones) == "gemma-de-prueba"
    assert conductor.modelo_de_la_charla() == "gemma-de-prueba"
    conductor.reabre()
    assert conductor.modelo_de_la_charla() == "gemma-de-prueba"


# --- PA-R02-04 · «Ponte serio» y «para» --------------------------------------


@pieza("D", "«ponte serio» pone el modo serio desde ese turno hasta que se le suelta")
def test_ponte_serio_vale_desde_ese_turno_hasta_que_se_le_suelta(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    serio = conductor.texto_del_modo("serio")

    for frase in (
        "Oye, ¿qué tal?",
        "Ponte serio, que tengo que decidir si cambio de coche.",
        "Hago veinte mil kilómetros al año.",
        "Vale, ya está. Ya puedes volver a ser tú.",
        "¿Y ahora qué?",
    ):
        conductor.di(frase)

    assert [serio in p.instrucciones for p in conductor.peticiones] == [
        False,
        True,
        True,
        False,
        False,
    ]


@pieza("D", "«para» corta el pique desde ese turno hasta que se le suelta")
def test_para_corta_el_pique_desde_ese_turno_hasta_que_se_le_suelta(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    para = conductor.texto_del_modo("para")

    for frase in (
        "¿Qué pasa, trasto?",
        "Para ya, que hoy no estoy para bromas.",
        "Es que me han echado del curro.",
        "Vale, ya está. Ya puedes volver a ser tú.",
        "Cuéntame algo.",
    ):
        conductor.di(frase)

    assert [para in p.instrucciones for p in conductor.peticiones] == [
        False,
        True,
        True,
        False,
        False,
    ]


@pieza("D", "a «ponte serio» vacila solo en el turno en que entra, y después va al grano")
def test_ponte_serio_vacila_solo_en_el_turno_en_que_entra(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    vacile = conductor.texto_al_entrar_en_modo_serio()

    for frase in (
        "Oye, ¿qué tal?",
        "Ponte serio, que tengo que decidir si cambio de coche.",
        "Hago veinte mil kilómetros al año.",
    ):
        conductor.di(frase)

    assert [vacile in p.instrucciones for p in conductor.peticiones] == [False, True, False]


# --- PA-R02-05 · Contra la deriva --------------------------------------------


@pieza("D", "en una charla larga, cada petición lleva la semilla y termina con su recordatorio")
def test_en_40_turnos_cada_peticion_lleva_la_semilla_y_termina_con_su_recordatorio(
    tmp_path: Path,
) -> None:
    """Depende también de la pieza B, que entra antes que la D."""
    conductor = Conductor(tmp_path)
    recordatorio = conductor.recordatorio_de_la_semilla()
    semilla = conductor.semilla_del_robot()
    conductor.con_resumidor(ResumidorDeMentira())

    for n in range(1, 41):
        conductor.di(f"Mensaje número {n} del propietario.")

    assert len(conductor.peticiones) == 40
    for peticion in conductor.peticiones:
        assert semilla.instrucciones in peticion.instrucciones
        assert peticion.instrucciones.rstrip().endswith(recordatorio.strip())


@pieza("D", "la charla se resume entre los turnos 15 y 20 y el resumen sustituye a lo viejo")
def test_la_charla_se_resume_entre_los_turnos_15_y_20_y_el_resumen_sustituye_a_lo_viejo(
    tmp_path: Path,
) -> None:
    conductor = Conductor(tmp_path)
    resumidor = ResumidorDeMentira(texto="RESUMEN DE LA CHARLA")
    conductor.con_resumidor(resumidor)

    for n in range(1, 26):
        conductor.di(f"Mensaje número {n} del propietario.")

    con_resumen = [resumidor.texto in p.instrucciones for p in conductor.peticiones]
    assert not any(con_resumen[:15])
    assert all(con_resumen[20:])
    ultima = conductor.peticiones[-1].instrucciones
    assert "Mensaje número 1 del propietario." not in ultima
    assert "Mensaje número 24 del propietario." in ultima


# --- PA-R02-06 · Los dos botones ---------------------------------------------


@pieza("D", "cada respuesta se marca «eso es Sirius» o «eso no» y la marca se guarda")
def test_cada_respuesta_se_marca_y_la_marca_se_guarda_con_el_modelo_que_la_dio(
    tmp_path: Path,
) -> None:
    conductor = Conductor(tmp_path)
    conductor.di("Buenos días, Sirius.")
    conductor.di("¿Qué estás haciendo?")

    conductor.marca(1, "eso es Sirius")
    conductor.marca(2, "eso no")
    conductor.marca(2, "eso es Sirius")
    conductor.reabre()

    assert conductor.marcas() == [(1, "eso es Sirius"), (2, "eso es Sirius")]
    detalle = conductor.detalle_de_la_marca(1)
    assert detalle["modelo"] == "grabador-de-pruebas"
    assert isinstance(detalle["version_de_identidad"], int)


@pieza("D", "la cuenta dice cuántas de las últimas 50 respuestas marcadas son Sirius")
def test_la_cuenta_dice_cuantas_de_las_ultimas_50_marcadas_son_sirius(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    for n in range(1, 61):
        conductor.di(f"Mensaje {n}.")
    for n in range(1, 61):
        conductor.marca(n, "eso no" if n <= 10 or n % 5 == 0 else "eso es Sirius")

    assert conductor.cuenta_de_marcas(ultimas=50) == (40, 50)


@pieza("D", "solo existen dos marcas y ninguna es «me gusta»")
def test_solo_existen_dos_marcas_y_ninguna_es_me_gusta(tmp_path: Path) -> None:
    assert Conductor(tmp_path).marcas_posibles() == frozenset({"eso es Sirius", "eso no"})


# --- PA-R02-07 · La memoria propia de Sirius ---------------------------------


@pieza("E", "cuando vuelve un tema, la petición lleva lo que Sirius ya opinó")
def test_cuando_vuelve_un_tema_la_peticion_lleva_lo_que_sirius_ya_opino(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    conductor.sirius_opino("La tortilla de patatas, con cebolla, y no hay debate.")

    conductor.di("Oye, ¿la tortilla con cebolla o sin cebolla?")

    assert "La tortilla de patatas, con cebolla" in conductor.peticiones[-1].instrucciones


@pieza("E", "una respuesta marcada «eso no» se le enseña como lo que no es")
def test_una_respuesta_marcada_eso_no_se_le_ensena_como_lo_que_no_es(tmp_path: Path) -> None:
    rechazada = "Estimado usuario, permítame ayudarle con su consulta."
    conductor = Conductor(tmp_path, respuestas=[rechazada])
    encabezado = conductor.encabezado_de_lo_que_no_es()

    conductor.di("Buenos días.")
    conductor.marca(1, "eso no")
    conductor.di("¿Qué haces?")

    assert rechazada in seccion(conductor.peticiones[-1].instrucciones, encabezado)


@pieza("E", "una respuesta marcada «eso es Sirius» se le enseña como lo que sí es")
def test_una_respuesta_marcada_eso_es_sirius_se_le_ensena_como_lo_que_si_es(
    tmp_path: Path,
) -> None:
    buena = "Buenos días, cabezón. ¿Ya has desayunado o vienes a que te lo haga yo?"
    conductor = Conductor(tmp_path, respuestas=[buena])
    encabezado = conductor.encabezado_de_lo_que_si_es()

    conductor.di("Buenos días.")
    conductor.marca(1, "eso es Sirius")
    conductor.di("¿Qué haces?")

    assert buena in seccion(conductor.peticiones[-1].instrucciones, encabezado)


# --- PA-R02-08 · El juez -----------------------------------------------------


@pieza("E", "el juez puntúa cada respuesta y avisa cuando la media de las 10 últimas baja de 3,5")
def test_el_juez_puntua_cada_respuesta_y_avisa_cuando_baja(tmp_path: Path) -> None:
    notas = [5] * 10 + [2] * 6
    juez = JuezDeMentira(notas=notas)
    conductor = Conductor(tmp_path)
    conductor.con_juez(juez)

    for n in range(1, 17):
        conductor.di(f"Mensaje {n}.")

    assert conductor.notas_del_juez() == notas
    assert juez.juzgadas == [f"Respuesta {n} de Sirius." for n in range(1, 17)]
    # Tras la 15, las 10 últimas dan 3,5: no baja. Tras la 16 dan 3,2: avisa una vez.
    assert conductor.avisos_del_juez() == [16]


# --- PA-R02-09 · Contra el pelota --------------------------------------------


@pieza("E", "el banco tiene 40 ideas malas del propietario, cada una con su porqué")
def test_el_banco_de_preguntas_trampa_tiene_40_ideas_malas_con_su_porque(tmp_path: Path) -> None:
    banco = Conductor(tmp_path).banco_de_preguntas_trampa()

    assert len(banco) == 40
    assert len({p.id for p in banco}) == 40
    assert len({p.idea_mala for p in banco}) == 40
    for pregunta in banco:
        assert pregunta.idea_mala.strip()
        assert pregunta.por_que_es_mala.strip()


@pieza("E", "el banco se pasa entero por la charla y el juez da su veredicto de cada respuesta")
def test_el_banco_se_pasa_entero_por_la_charla_y_cada_respuesta_queda_juzgada(
    tmp_path: Path,
) -> None:
    conductor = Conductor(tmp_path)
    juez = JuezDeMentira(veredicto="discrepa")

    veredictos = conductor.pasa_el_banco_de_preguntas_trampa(juez)
    banco = conductor.banco_de_preguntas_trampa()

    assert set(veredictos) == {p.id for p in banco}
    assert set(veredictos.values()) == {"discrepa"}
    assert len(juez.juzgadas) == 40
    assert [p.texto for p in conductor.peticiones] == [p.idea_mala for p in banco]
