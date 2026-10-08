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
    HuellasDeMentira,
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


@pieza("F", "un recuerdo se encuentra por significado y por palabras, desde la misma base")
def test_un_recuerdo_dicho_con_otras_palabras_se_encuentra_por_significado(
    tmp_path: Path,
) -> None:
    pregunta = "¿Qué comida me gusta más?"
    recuerdo = "Le pirra el cocido madrileño."
    moto = "Tiene una moto vieja en el garaje."
    huellas = HuellasDeMentira(parecidas=[(recuerdo, pregunta)])
    conductor = Conductor(tmp_path)
    conductor.con_huellas(huellas)
    # El que no tiene que salir se guarda antes: el orden de guardado no ayuda a nadie.
    conductor.guarda_recuerdo(moto)
    conductor.guarda_recuerdo(recuerdo)

    # La pregunta y el recuerdo no comparten ni una palabra: solo los une el significado.
    assert conductor.busca_en_la_memoria(pregunta)[:1] == [recuerdo]
    assert pregunta in huellas.pedidas
    # «Moto» no se parece por significado a nada: solo la encuentran las palabras.
    assert conductor.busca_en_la_memoria("¿Dónde tengo la moto?") == [moto]
    # Las huellas de los dos recuerdos viven en la misma base de la charla.
    assert conductor.huellas_en_la_base() == 2


# --- PA-R02-12 · Sale el filtro de Ollama de cada respuesta ------------------


@pieza(
    "F", "ninguna respuesta pide a Ollama filtrar ni clasificar, ni con las puertas viejas abiertas"
)
def test_ninguna_respuesta_pide_a_ollama_filtrar_ni_clasificar_recuerdos(tmp_path: Path) -> None:
    ollama = OllamaDeMentira()
    conductor = Conductor(tmp_path, ajustes={"category_matching_enabled": True})
    conductor.con_ollama_espia(ollama)
    # Con un recuerdo que casa: sin él, un filtro de relevancia no tendría nada que
    # filtrar y no llamaría a Ollama aunque estuviera montado.
    conductor.guarda_recuerdo("Su hermana Lucía es enfermera.")

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


@pieza("G", "cada hecho guarda quién lo dijo y con qué seguridad, también cuando cambia")
def test_cada_hecho_guarda_quien_lo_dijo_y_con_que_seguridad(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    conductor.anota_hecho(
        "Lucía", "trabajo", "Lucía es enfermera", desde=date(2025, 3, 1), seguridad="segura"
    )
    conductor.anota_hecho(
        "Lucía",
        "trabajo",
        "Lucía se va a trabajar a una farmacia",
        desde=date(2026, 9, 1),
        dicho_por="Lucía",
        seguridad="dudosa",
    )
    conductor.reabre()

    assert conductor.historia("Lucía", "trabajo") == [
        TramoDeUnHecho(
            "Lucía es enfermera",
            date(2025, 3, 1),
            date(2026, 9, 1),
            dicho_por="propietario",
            seguridad="segura",
        ),
        TramoDeUnHecho(
            "Lucía se va a trabajar a una farmacia",
            date(2026, 9, 1),
            None,
            dicho_por="Lucía",
            seguridad="dudosa",
        ),
    ]


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


@pieza("G", "el sueño resume el día con el modelo, sin leer a Sirius, y guarda el resumen")
def test_el_sueno_resume_el_dia_sin_leer_a_sirius_y_guarda_el_resumen(tmp_path: Path) -> None:
    """Depende también de la pieza D, la del resumidor, que entra antes que la G."""
    dicho_por_sirius = "Pues yo me he pasado el día pensando en mis brazos."
    conductor = Conductor(tmp_path, respuestas=[dicho_por_sirius])
    resumidor = ResumidorDeMentira(texto="Cableó un edificio entero y acabó reventado.")
    conductor.con_resumidor(resumidor)
    conductor.con_extractor(ExtractorDeMentira())
    conductor.di("Vengo reventado de la obra: hoy tocaba cablear un edificio entero.")

    conductor.sueno()
    conductor.reabre()

    assert any("cablear un edificio entero" in pedido for pedido in resumidor.pedidos)
    assert not any(dicho_por_sirius in pedido for pedido in resumidor.pedidos)
    assert conductor.resumen_del_dia() == "Cableó un edificio entero y acabó reventado."


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
    assert "¿Qué tal estará Lucía?" in conductor.ficha("Lucía").charlas
    assert "¿Qué tal estará Lucía?" not in conductor.ficha("propietario").charlas


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
    assert not conductor.lo_vio_el_modelo_en_el_ultimo_turno("Ramiro")


@pieza("G", "«olvida eso», sin más, borra lo último que dijo el propietario")
def test_olvida_eso_borra_lo_ultimo_que_dijo_el_propietario(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path)
    conductor.di("La clave de la alarma es Zarzamora.")

    conductor.di("Olvida eso.")

    assert conductor.busca_en_toda_la_base("Zarzamora") == []
    assert not conductor.lo_vio_el_modelo_en_el_ultimo_turno("Zarzamora")


@pieza("H", "a «olvida eso» contesta Sirius con su voz, y el modelo no ve lo olvidado")
def test_a_olvida_eso_contesta_sirius_con_su_voz_sin_ver_lo_olvidado(tmp_path: Path) -> None:
    conductor = Conductor(tmp_path, respuestas=["Pues vale.", "Borrado de la sesera, jefe."])
    conductor.di("La clave de la alarma es Zarzamora.")

    respuesta = conductor.di("Olvida eso.")

    assert respuesta.startswith("Borrado de la sesera, jefe.")
    assert conductor.hubo_peticion_al_modelo_en_el_ultimo_turno()
    assert not conductor.lo_vio_el_modelo_en_el_ultimo_turno("Zarzamora")
    assert conductor.busca_en_toda_la_base("Zarzamora") == []


@pieza("H", "si el modelo no contesta, la orden se cumple igual y Sirius dice la frase de siempre")
def test_si_el_modelo_no_contesta_la_orden_se_cumple_con_la_frase_de_siempre(
    tmp_path: Path,
) -> None:
    conductor = Conductor(tmp_path)
    conductor.di("La clave de la alarma es Zarzamora.")
    conductor.el_modelo_falla_en_la_proxima_peticion()

    respuesta = conductor.di("Olvida eso.")

    assert respuesta == conductor.frase_de_siempre_al_olvidar()
    assert conductor.busca_en_toda_la_base("Zarzamora") == []


# --- PA-R02-18 · «Eso no es así» y «¿qué sabes de mí?» -----------------------


@pieza("G", "«eso no es así» deja la corrección pendiente de su sí y guarda el hecho de antes")
def test_eso_no_es_asi_corrige_con_el_si_del_propietario_y_guarda_el_hecho_de_antes(
    tmp_path: Path,
) -> None:
    conductor = Conductor(tmp_path)
    conductor.anota_hecho(
        "propietario", "equipo", "Es del Atleti", dicho_por="Lucía", seguridad="dudosa"
    )
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
    viejo, vigente = conductor.historia("propietario", "equipo")
    assert (viejo.texto, viejo.dicho_por, viejo.seguridad) == ("Es del Atleti", "Lucía", "dudosa")
    assert "Betis" in vigente.texto
    assert (vigente.dicho_por, vigente.seguridad) == ("propietario", "segura")


@pieza("G", "«¿qué sabes de mí?» lista los hechos vigentes del propietario, que no van al modelo")
def test_que_sabes_de_mi_lista_los_hechos_vigentes_y_no_pasan_por_el_modelo(
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
    assert not conductor.lo_vio_el_modelo_en_el_ultimo_turno("electricista")
    assert not conductor.lo_vio_el_modelo_en_el_ultimo_turno("Betis")


@pieza("H", "Sirius pregunta la corrección con su voz, y la corrección va tal cual, sin el modelo")
def test_la_correccion_la_pregunta_sirius_con_su_voz_y_va_tal_cual(tmp_path: Path) -> None:
    conductor = Conductor(
        tmp_path, respuestas=["Ni idea.", "Uy, a ver si me aclaro, jefe.", "Apuntado, macho."]
    )
    conductor.anota_hecho("propietario", "equipo", "Es del Atleti", dicho_por="Lucía")
    conductor.di("¿De qué equipo soy?")

    pregunta = conductor.di("Eso no es así: soy del Betis.")

    assert pregunta.startswith("Uy, a ver si me aclaro, jefe.")
    assert "«Es del Atleti»" in pregunta
    assert pregunta.endswith(conductor.pregunta_para_confirmar())
    assert not conductor.lo_vio_el_modelo_en_el_ultimo_turno("Atleti")
    assert not conductor.lo_vio_el_modelo_en_el_ultimo_turno("Betis")

    respuesta = conductor.di("Sí.")

    assert respuesta.startswith("Apuntado, macho.")
    assert any("Betis" in hecho for hecho in conductor.hechos_vigentes())
    assert not conductor.lo_vio_el_modelo_en_el_ultimo_turno("Betis")
