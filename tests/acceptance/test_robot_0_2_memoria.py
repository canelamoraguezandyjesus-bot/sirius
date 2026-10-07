"""Pruebas de aceptación de la versión 0.2 del robot: la memoria.

Salen de la sección 0.2 de ``docs/evolution/PLAN_DEL_ROBOT.md`` (§4), de su
«terminado cuando» y de lo que se hace, y están escritas antes del código como
pide su §3 (ADR-233). Cada una lleva el identificador ``PA-R02-NN`` de
``docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md``.

Olvidar se comprueba mirando la base ENTERA, tabla por tabla, también las de la
búsqueda por palabras y las de los resúmenes: así «olvida eso» no puede dejar el
dato en un sitio que nadie mira.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from conductor_robot_0_2 import (
    FAMILIAS_DEL_BANCO_DE_MEMORIA,
    Conductor,
    ExtractorDeMentira,
    HechoPropuesto,
    OllamaDeMentira,
    ResumidorDeMentira,
    TramoDeUnHecho,
    pieza,
)

pytestmark = pytest.mark.acceptance


# --- PA-R02-10 · El banco de memoria -----------------------------------------


@pieza("F", "el banco de memoria tiene 100 casos en español de las siete familias")
def test_el_banco_de_memoria_tiene_100_casos_de_las_siete_familias(tmp_path: Path) -> None:
    banco = Conductor(tmp_path).banco_de_memoria()

    assert len(banco) == 100
    assert len({caso.id for caso in banco}) == 100
    assert {caso.familia for caso in banco} == FAMILIAS_DEL_BANCO_DE_MEMORIA
    assert all(caso.pregunta.strip() for caso in banco)


@pieza("G", "por el camino real, «olvida eso» y «quién dijo qué» aciertan todos sus casos")
def test_el_banco_pasa_por_el_camino_real_y_olvidar_y_quien_lo_dijo_aciertan_todo(
    tmp_path: Path,
) -> None:
    resultado = Conductor(tmp_path).pasa_el_banco_de_memoria()

    assert set(resultado) == FAMILIAS_DEL_BANCO_DE_MEMORIA
    assert sum(casos for _, casos in resultado.values()) == 100
    for familia in ("olvida eso", "quién dijo qué"):
        aciertos, casos = resultado[familia]
        assert aciertos == casos, f"«{familia}»: {aciertos} de {casos}"


# --- PA-R02-11 · Buscar en menos de 150 ms -----------------------------------


@pieza("F", "buscar en 10.000 recuerdos tarda menos de 150 ms en el P95")
def test_buscar_en_10000_recuerdos_tarda_menos_de_150_ms_en_el_p95(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    conductor.llena_la_memoria(10_000)

    tiempos = sorted(conductor.mide_la_busqueda(consultas=100))

    assert len(tiempos) == 100
    assert tiempos[94] < 150, f"P95 de {tiempos[94]:.1f} ms"


# --- PA-R02-12 · Sale el filtro de Ollama de cada respuesta ------------------


@pieza(
    "F", "ninguna respuesta pide a Ollama filtrar ni clasificar, ni con las puertas viejas abiertas"
)
def test_ninguna_respuesta_pide_a_ollama_filtrar_ni_clasificar_recuerdos(tmp_path: Path) -> None:
    ollama = OllamaDeMentira()
    conductor = Conductor(tmp_path, ajustes={"category_matching_enabled": True})
    conductor.con_ollama_espia(ollama)

    conductor.di("¿Qué sabes de mi hermana?")

    assert ollama.llamadas_a("/api/chat") == 0
    assert ollama.llamadas_a("/api/generate") == 0


# --- PA-R02-13 · Hechos con fecha --------------------------------------------


@pieza("G", "un hecho que cambia cierra el anterior con su fecha y la charla trae el vigente")
def test_un_hecho_que_cambia_cierra_el_anterior_y_la_charla_trae_el_vigente(
    tmp_path: Path,
) -> None:
    conductor = Conductor(tmp_path)
    conductor.anota_hecho("propietario", "dónde vive", "Vive en Madrid", desde=date(2024, 1, 1))
    conductor.anota_hecho("propietario", "dónde vive", "Vive en Valencia", desde=date(2026, 9, 1))

    assert "Vive en Valencia" in conductor.hechos_vigentes()
    assert "Vive en Madrid" not in conductor.hechos_vigentes()
    assert conductor.historia("propietario", "dónde vive") == [
        TramoDeUnHecho("Vive en Madrid", date(2024, 1, 1), date(2026, 9, 1)),
        TramoDeUnHecho("Vive en Valencia", date(2026, 9, 1), None),
    ]

    conductor.di("¿Dónde vivo yo?")
    instrucciones = conductor.peticiones[-1].instrucciones
    assert "Vive en Valencia" in instrucciones
    assert "Vive en Madrid" not in instrucciones


# --- PA-R02-14 · Lo que dice Sirius no es un hecho del propietario -----------


@pieza("G", "lo que dice Sirius nunca entra como hecho del propietario")
def test_lo_que_dice_sirius_nunca_entra_como_hecho_del_propietario(tmp_path: Path) -> None:
    dicho_por_sirius = "Tú vives en Cuenca, que lo sé yo."
    conductor = Conductor(tmp_path, respuestas=[dicho_por_sirius])
    conductor.di("¿Dónde vivo?")

    assert conductor.anota_hecho_desde_la_respuesta(1) == "rechazado"

    extractor = ExtractorDeMentira()
    conductor.con_extractor(extractor)
    conductor.sueno()
    assert extractor.leido, "el sueño no leyó nada de la charla del día"
    assert any("¿Dónde vivo?" in leido for leido in extractor.leido)
    assert not any(dicho_por_sirius in leido for leido in extractor.leido)


# --- PA-R02-15 · El sueño propone, el propietario decide ---------------------


@pieza("G", "el sueño propone hechos y ninguno entra sin el sí del propietario")
def test_el_sueno_propone_y_ningun_hecho_entra_sin_el_si_del_propietario(tmp_path: Path) -> None:
    propuesta = HechoPropuesto("propietario", "trabajo", "Trabaja de electricista")
    conductor = Conductor(tmp_path)
    conductor.con_extractor(ExtractorDeMentira([propuesta]))
    conductor.di("Vengo reventado de la obra: hoy tocaba cablear un edificio entero.")

    assert conductor.sueno() == [propuesta]
    assert "Trabaja de electricista" not in conductor.hechos_vigentes()

    conductor.acepta(propuesta)
    assert "Trabaja de electricista" in conductor.hechos_vigentes()


# --- PA-R02-16 · Una ficha por persona ---------------------------------------


@pieza("G", "cada persona tiene su ficha y la charla trae lo que se sabe de ella")
def test_cada_persona_tiene_su_ficha_y_la_charla_trae_lo_que_se_sabe_de_ella(
    tmp_path: Path,
) -> None:
    conductor = Conductor(tmp_path)
    conductor.anota_hecho("Lucía", "trabajo", "Lucía es enfermera")
    conductor.anota_hecho("Lucía", "familia", "Lucía es su hermana")
    conductor.anota_hecho("propietario", "trabajo", "Trabaja de electricista")

    assert set(conductor.ficha("Lucía").hechos) == {"Lucía es enfermera", "Lucía es su hermana"}

    conductor.di("¿Qué tal estará Lucía?")
    assert "Lucía es enfermera" in conductor.peticiones[-1].instrucciones


# --- PA-R02-17 · «Olvida eso» borra de verdad --------------------------------


@pieza("G", "«olvida lo de...» lo borra de toda la base, también de los resúmenes")
def test_olvida_lo_de_algo_lo_borra_de_toda_la_base_tambien_de_los_resumenes(
    tmp_path: Path,
) -> None:
    """Depende también de la pieza D, la de los resúmenes, que entra antes que la G."""
    conductor = Conductor(tmp_path)
    conductor.con_resumidor(ResumidorDeMentira(copiar=True))
    conductor.di("Mi vecino Ramiro me tiene frito con la obra del tercero.")
    for n in range(1, 25):
        conductor.di(f"Mensaje número {n}.")
    assert conductor.busca_en_toda_la_base("Ramiro"), "el dato tenía que estar antes de olvidarlo"

    conductor.di("Olvida lo de mi vecino Ramiro.")

    assert conductor.busca_en_toda_la_base("Ramiro") == []
    assert not conductor.hubo_peticion_al_modelo_en_el_ultimo_turno()


@pieza("G", "«olvida eso», sin más, borra lo último que dijo el propietario")
def test_olvida_eso_borra_lo_ultimo_que_dijo_el_propietario(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    conductor.di("La clave de la alarma es Zarzamora.")

    conductor.di("Olvida eso.")

    assert conductor.busca_en_toda_la_base("Zarzamora") == []
    assert not conductor.hubo_peticion_al_modelo_en_el_ultimo_turno()


# --- PA-R02-18 · «Eso no es así» y «¿qué sabes de mí?» -----------------------


@pieza("G", "«eso no es así» deja la corrección pendiente de su sí y guarda el hecho de antes")
def test_eso_no_es_asi_corrige_con_el_si_del_propietario_y_guarda_el_hecho_de_antes(
    tmp_path: Path,
) -> None:
    conductor = Conductor(tmp_path)
    conductor.anota_hecho("propietario", "equipo", "Es del Atleti")
    conductor.di("¿De qué equipo soy?")

    conductor.di("Eso no es así: soy del Betis.")

    [(antes, nuevo)] = conductor.correcciones_pendientes()
    assert antes == "Es del Atleti"
    assert "Betis" in nuevo
    assert "Es del Atleti" in conductor.hechos_vigentes()

    conductor.confirma_las_correcciones()
    vigentes = conductor.hechos_vigentes()
    assert any("Betis" in hecho for hecho in vigentes)
    assert "Es del Atleti" not in vigentes
    assert conductor.historia("propietario", "equipo")[0].texto == "Es del Atleti"


@pieza("G", "«¿qué sabes de mí?» lista los hechos vigentes del propietario sin pasar por el modelo")
def test_que_sabes_de_mi_lista_los_hechos_vigentes_sin_pasar_por_el_modelo(
    tmp_path: Path,
) -> None:
    conductor = Conductor(tmp_path)
    conductor.anota_hecho("propietario", "trabajo", "Trabaja de electricista")
    conductor.anota_hecho("propietario", "equipo", "Es del Betis")
    conductor.anota_hecho("Lucía", "trabajo", "Lucía es enfermera")

    respuesta = conductor.di("¿Qué sabes de mí?")

    assert "Trabaja de electricista" in respuesta
    assert "Es del Betis" in respuesta
    assert "Lucía es enfermera" not in respuesta
    assert not conductor.hubo_peticion_al_modelo_en_el_ultimo_turno()
