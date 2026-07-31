"""Pruebas del esquema v0.2 de la ficha (acto sucesor 01 de TOL-210).

No miden, no ejecutan candidatos y no tocan el repositorio. Comprueban que la
exencion del control es exactamente lo aprobado: limitada a ``T0-control``,
con fundamento obligatorio por area, y sin relajar NADA para los candidatos.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.cards import card_protocol as cp
from experiments.adr002.cards import schema_card_v0_2 as esquema_v2
from experiments.adr002.cards import test_adr002_cards as base
from experiments.adr002.cards import verify_cards as verificacion

RAIZ = Path(__file__).resolve().parents[3]

SHA_REFERENCIA = "a" * 40
SHA_PROTOTIPO = "c" * 40


def ficha_control_conforme() -> dict[str, Any]:
    """Fixture: la ficha de T0-control conforme al esquema v0.2.

    No es la ficha real —esa se congela en su propio commit—: es el punto de
    partida conforme sobre el que las pruebas aplican mutaciones.
    """
    return {
        "documento": "Ficha de control de falsacion T0 para ADR-002",
        "version_esquema": esquema_v2.VERSION_ESQUEMA,
        "estado": cp.ESTADO_CONGELADA,
        "plantilla": esquema_v2.PLANTILLA,
        "registro": cp.REGISTRO,
        "protocolo": cp.PROTOCOLO,
        "actas_de_puerta": list(esquema_v2.ACTAS_DE_PUERTA),
        "identidad": {
            "candidato": cp.CONTROL,
            "papel": cp.PAPEL_CONTROL,
            "version": 1,
            "sustituye_a": None,
            "motivo_de_sustitucion": None,
        },
        "congelacion": {
            "commit_de_referencia": SHA_REFERENCIA,
            "huella": "0" * 40,
            "ruta": "artifacts/adr002_cards/ficha_T0-control_v1.json",
        },
        "arquitectura_de_control": {
            "sustrato_lexico": "FTS5 medido de Sirius 0.1, sin alternativa",
            "materializacion_de_relaciones": "las del canon de Sirius 0.1, tal como estan",
            "puerto_de_acceso": "KnowledgeSearchRepository de Sirius 0.1, el original",
            "incumplimientos_conocidos": {
                "RF-06": "aislamiento de ambito no implementado; medido e inventariado",
                "RF-14": "barrido completo prohibido presente; es la razon de ser del control",
                "RF-19": "validacion explicita no implementada; medido e inventariado",
            },
        },
        "corpus": {
            "version": "v0.4 congelada (performance_corpus_v0_2.json)",
            "mensajes": 5000,
            "recuerdos": 500,
            "decisiones": 50,
            "proyectos": 2,
            "longitud_media_y_distribucion": "las declaradas por el corpus congelado",
            "commit": esquema_v2.CORPUS_COMMIT_CONGELADO,
            "head_de_esquema": esquema_v2.HEAD_T0,
            "t0_rederivada_sobre_este_corpus": False,
            "referencia_de_la_rederivacion": (
                "no existe aun: esta ficha ampara precisamente esa rederivacion"
            ),
        },
        "protocolo_aplicado": {
            "protocolo": cp.PROTOCOLO,
            "desviaciones": "ninguna",
            "entorno": "LAB-LINUX, carga no controlada y declarada",
            "semilla": "20260731",
            "repeticiones_por_magnitud": 100,
        },
        "escenario_de_control": {
            "fuente_del_plan": esquema_v2.FUENTE_DEL_PLAN,
            "escenarios": list(esquema_v2.ESCENARIOS_PLAN),
            "capas": list(esquema_v2.CAPAS_PLAN),
            "magnitudes": 6,
        },
        "estabilidad": {
            "sesiones_previstas": cp.SESIONES_EXIGIDAS,
            "sm_ns": cp.SM_NS,
            "u50_ns": cp.U50_NS,
            "regimen_p50": "relativo <= 20 % por encima de U50; sin afirmacion bajo SM",
            "regimen_p95": "absoluto contra B95(M) en todo el rango cubierto",
            "sin_umbral_relativo_para_p95": True,
            "consulta_de_banda": "M es el minimo entre sesiones del mismo percentil",
            "repeticion_unica_y_no_evaluable": "una sola repeticion; despues NO EVALUABLE",
        },
        "presupuesto_aplicable": {
            "presupuesto_absoluto_b": cp.PRESUPUESTO_TOL207_B,
            "nota": "presupuesto del acta de TOL-207; el consumo se conocera al medir",
        },
        "exenciones_de_control": {
            "limitada_a": cp.CONTROL,
            "alternativa_minima_y_senal_tardia": (
                "T0 no representa ninguna alternativa de ARQ-00 §23 ni habilita senal tardia"
            ),
            "etapas_e0_e5": "T0 no implementa E0-E5 (Resolucion de la particion §3)",
            "limites_locales_por_etapa": "sin etapas no hay limites por etapa que congelar",
            "limites_extremo_a_extremo": (
                "T0 no es un presupuesto heredable y no se descarta por su tiempo"
            ),
            "consumo_de_almacenamiento_previo": (
                "declararlo antes de medir seria una medicion no autorizada o un invento"
            ),
            "limites_del_ciclo_de_indice": (
                "ninguna decision congela limites de ciclo para la linea base"
            ),
        },
        "huella_candidato": {
            "commit_del_prototipo": SHA_PROTOTIPO,
            "hash_del_arbol_de_fuentes": "arbol git de src/sirius en el commit del prototipo",
            "migraciones_o_ddl": "cadena canonica de Alembic hasta 61be4bb269bf, sin cambios",
            "artefactos_y_su_hash": "ninguno generado por adelantado",
            "reproduccion": "uv run python -m experiments.adr002.rederivation.run_rederivation",
        },
        "declaracion_de_congelacion": {
            "texto": "valores fijados antes de la primera ejecucion del control",
            "responsable": "Proyecto Sirius",
            "fecha": "2026-07-31",
            "valores_anteriores_a_la_primera_ejecucion": True,
        },
        "no_contiene_resultados": True,
    }


def _mutada(**cambios: Any) -> dict[str, Any]:
    ficha = ficha_control_conforme()
    for ruta, valor in cambios.items():
        partes = ruta.split("__")
        destino: Any = ficha
        for parte in partes[:-1]:
            destino = destino[parte]
        destino[partes[-1]] = valor
    return ficha


def ficha_candidato_v02() -> dict[str, Any]:
    """Una ficha v0.2 de candidato: la v0.1 con las citas actualizadas."""
    ficha = base.ficha_conforme()
    ficha["version_esquema"] = esquema_v2.VERSION_ESQUEMA
    ficha["plantilla"] = esquema_v2.PLANTILLA
    ficha["actas_de_puerta"] = list(esquema_v2.ACTAS_DE_PUERTA)
    return ficha


# --------------------------------------------------------------------------
# El control conforme, y el validador total
# --------------------------------------------------------------------------


def test_la_ficha_de_control_de_referencia_es_conforme() -> None:
    assert esquema_v2.fallos_ficha(ficha_control_conforme()) == []


def test_el_validador_es_total_y_nunca_lanza() -> None:
    assert esquema_v2.fallos_ficha({})
    assert esquema_v2.fallos_ficha([])  # type: ignore[arg-type]
    assert esquema_v2.fallos_ficha({"version_esquema": esquema_v2.VERSION_ESQUEMA, "identidad": 7})


def test_una_version_de_esquema_ajena_no_pasa() -> None:
    ficha = _mutada(version_esquema="ficha-candidato-0.9")
    assert esquema_v2.fallos_ficha(ficha) == ["version_esquema debe ser ficha-candidato-0.2"]


@pytest.mark.parametrize("seccion", esquema_v2.SECCIONES_CONTROL)
def test_falta_cualquier_seccion_del_control_y_la_ficha_cae(seccion: str) -> None:
    ficha = ficha_control_conforme()
    del ficha[seccion]
    assert esquema_v2.fallos_ficha(ficha), seccion


def test_los_conjuntos_del_control_estan_cerrados() -> None:
    for seccion in (
        "identidad",
        "congelacion",
        "arquitectura_de_control",
        "corpus",
        "protocolo_aplicado",
        "escenario_de_control",
        "estabilidad",
        "presupuesto_aplicable",
        "exenciones_de_control",
        "huella_candidato",
        "declaracion_de_congelacion",
    ):
        ficha = ficha_control_conforme()
        ficha[seccion]["p95_observado_ns"] = 1
        assert any("ajenos al esquema" in f for f in esquema_v2.fallos_ficha(ficha)), seccion
    ficha = ficha_control_conforme()
    ficha["resultado"] = {"p95_ns": 1}
    assert any("ajenos al esquema" in f for f in esquema_v2.fallos_ficha(ficha))


# --------------------------------------------------------------------------
# La exencion: limitada, fundamentada y cerrada
# --------------------------------------------------------------------------


def test_cada_exencion_exige_fundamento_no_vacio() -> None:
    for area in esquema_v2.EXENCIONES:
        ficha = ficha_control_conforme()
        ficha["exenciones_de_control"][area] = "  "
        assert any("debe declararse" in f for f in esquema_v2.fallos_ficha(ficha)), area
        ficha["exenciones_de_control"][area] = "pendiente"
        assert any("debe declararse" in f for f in esquema_v2.fallos_ficha(ficha)), area


def test_las_areas_eximibles_son_exactamente_seis() -> None:
    assert len(esquema_v2.EXENCIONES) == 6
    ficha = ficha_control_conforme()
    ficha["exenciones_de_control"]["banda_temporal"] = "area inventada"
    assert any("ajenos al esquema" in f for f in esquema_v2.fallos_ficha(ficha))


def test_la_exencion_se_declara_limitada_al_control() -> None:
    ficha = _mutada(exenciones_de_control__limitada_a="ADR002-A")
    assert any("no es transferible" in f for f in esquema_v2.fallos_ficha(ficha))


def test_ningun_candidato_puede_usar_la_exencion() -> None:
    """La regla central del acto sucesor: la exencion no alcanza a A/B/C/D."""
    ficha = ficha_candidato_v02()
    ficha["exenciones_de_control"] = ficha_control_conforme()["exenciones_de_control"]
    fallos = esquema_v2.fallos_ficha(ficha)
    assert any("exclusiva de T0-control" in f for f in fallos)


def test_un_candidato_v02_conforme_sigue_el_contenido_integro_de_la_v01() -> None:
    ficha = ficha_candidato_v02()
    assert esquema_v2.fallos_ficha(ficha) == []
    # Y cualquier mutacion que la v0.1 rechaza, la v0.2 tambien la rechaza.
    ficha["estabilidad"]["sesiones_previstas"] = 5
    assert esquema_v2.fallos_ficha(ficha)


def test_un_candidato_v02_no_puede_citar_la_plantilla_vieja() -> None:
    ficha = ficha_candidato_v02()
    ficha["plantilla"] = cp.PLANTILLA
    assert any("plantilla vigente" in f for f in esquema_v2.fallos_ficha(ficha))


def test_las_actas_citadas_incluyen_el_acto_sucesor() -> None:
    assert esquema_v2.ACTO_SUCESOR in esquema_v2.ACTAS_DE_PUERTA
    assert cp.ACTA_TOL_210 in esquema_v2.ACTAS_DE_PUERTA
    ficha = _mutada(actas_de_puerta=[cp.ACTA_TOL_207, cp.ACTA_TOL_209])
    assert any("actas_de_puerta" in f for f in esquema_v2.fallos_ficha(ficha))


# --------------------------------------------------------------------------
# Lo que sigue vinculando al control
# --------------------------------------------------------------------------


def test_el_control_no_puede_fichar_como_candidato() -> None:
    ficha = _mutada(identidad__papel=cp.PAPEL_CANDIDATO)
    assert any("papel" in f for f in esquema_v2.fallos_ficha(ficha))


def test_el_control_cita_el_corpus_congelado_y_no_otro() -> None:
    ficha = _mutada(corpus__commit="b" * 40)
    assert any("acta de congelacion v0.4" in f for f in esquema_v2.fallos_ficha(ficha))
    ficha = _mutada(corpus__head_de_esquema="deadbeef1234")
    assert any("identificar a T0" in f for f in esquema_v2.fallos_ficha(ficha))


def test_el_control_cita_el_perfil_aprobado_y_las_once_sesiones() -> None:
    for campo, valor in (("sesiones_previstas", 5), ("sm_ns", 1), ("u50_ns", 1)):
        ficha = ficha_control_conforme()
        ficha["estabilidad"][campo] = valor
        assert esquema_v2.fallos_ficha(ficha), campo


def test_el_control_cita_el_presupuesto_aprobado() -> None:
    ficha = _mutada(presupuesto_aplicable__presupuesto_absoluto_b=1)
    assert any("TOL-207" in f for f in esquema_v2.fallos_ficha(ficha))


def test_el_control_declara_sus_tres_incumplimientos_conocidos() -> None:
    assert esquema_v2.INCUMPLIMIENTOS_CONOCIDOS == ("RF-06", "RF-14", "RF-19")
    for rf in esquema_v2.INCUMPLIMIENTOS_CONOCIDOS:
        ficha = ficha_control_conforme()
        del ficha["arquitectura_de_control"]["incumplimientos_conocidos"][rf]
        assert esquema_v2.fallos_ficha(ficha), rf
    ficha = ficha_control_conforme()
    ficha["arquitectura_de_control"]["incumplimientos_conocidos"]["RF-99"] = "inventado"
    assert any("ajenos al esquema" in f for f in esquema_v2.fallos_ficha(ficha))


def test_el_escenario_del_control_es_el_plan_del_paquete_10() -> None:
    ficha = _mutada(escenario_de_control__magnitudes=5)
    assert any("magnitudes debe ser 6" in f for f in esquema_v2.fallos_ficha(ficha))
    ficha = ficha_control_conforme()
    ficha["escenario_de_control"]["escenarios"] = ["otro"]
    assert any("plan del paquete 10" in f for f in esquema_v2.fallos_ficha(ficha))


def test_el_protocolo_del_control_es_el_aprobado() -> None:
    ficha = _mutada(
        protocolo_aplicado__protocolo="SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md"
    )
    assert any("debe ser el aprobado" in f for f in esquema_v2.fallos_ficha(ficha))
    ficha = _mutada(protocolo_aplicado__repeticiones_por_magnitud=29)
    assert any("al menos 30" in f for f in esquema_v2.fallos_ficha(ficha))


def test_una_ficha_de_control_con_resultados_no_pasa() -> None:
    ficha = _mutada(no_contiene_resultados=False)
    assert any("no_contiene_resultados" in f for f in esquema_v2.fallos_ficha(ficha))


def test_los_escenarios_del_esquema_coinciden_con_el_paquete_10() -> None:
    """Los literales duplicados para evitar un ciclo de import se contrastan."""
    from experiments.adr002.rederivation import rederivation_protocol as rp

    assert esquema_v2.ESCENARIOS_PLAN == rp.ESCENARIOS
    assert esquema_v2.CAPAS_PLAN == rp.CAPAS
    assert esquema_v2.HEAD_T0 == rp.HEAD_T0


# --------------------------------------------------------------------------
# El verificador despacha por version
# --------------------------------------------------------------------------


def _con_huella_real(ficha: dict[str, Any], ruta: str) -> bytes:
    ficha["congelacion"]["ruta"] = ruta
    ficha["congelacion"]["huella"] = cp.huella_canonica(ficha)
    import json

    return (json.dumps(ficha, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def test_el_verificador_acepta_una_ficha_de_control_bien_congelada() -> None:
    ruta = "artifacts/adr002_cards/ficha_T0-control_v1.json"
    crudo = _con_huella_real(ficha_control_conforme(), ruta)
    resultado = verificacion.verificar(base._dependencias({ruta: crudo}))
    assert resultado.conforme, resultado.fallos
    assert len(resultado.confirmadas) == 1
    assert resultado.confirmadas[0].candidato == cp.CONTROL


def test_el_verificador_rechaza_una_version_de_esquema_desconocida() -> None:
    ruta = "artifacts/adr002_cards/ficha_T0-control_v1.json"
    ficha = ficha_control_conforme()
    ficha["version_esquema"] = "ficha-candidato-9.9"
    crudo = _con_huella_real(ficha, ruta)
    resultado = verificacion.verificar(base._dependencias({ruta: crudo}))
    assert any("version de esquema desconocida" in f for f in resultado.fallos)


def test_el_verificador_sigue_validando_fichas_v01() -> None:
    ruta = "artifacts/adr002_cards/ficha_ADR002-B_v1.json"
    crudo = base._con_huella_real(base.ficha_conforme(), ruta)
    resultado = verificacion.verificar(base._dependencias({ruta: crudo}))
    assert resultado.conforme, resultado.fallos


def test_la_plantilla_v03_es_ahora_intangible() -> None:
    nombre = next(iter(esquema_v2.PLANTILLAS_INTANGIBLES_ADICIONALES))
    esperado = esquema_v2.PLANTILLAS_INTANGIBLES_ADICIONALES[nombre]
    real = (RAIZ / "docs/architecture" / nombre).read_bytes()
    assert cp.blob_git(real) == esperado
    resultado = verificacion.verificar(
        base._dependencias({f"docs/architecture/{nombre}": b"alterada"})
    )
    assert any("plantilla anterior alterada" in f for f in resultado.fallos)


def test_la_plantilla_v04_existe_y_la_v03_no_se_toco() -> None:
    assert (RAIZ / "docs/architecture" / esquema_v2.PLANTILLA).is_file()
    assert (RAIZ / "docs/architecture" / esquema_v2.ACTO_SUCESOR).is_file()


def test_huella_canonica_del_control_excluye_su_propio_campo() -> None:
    ficha = ficha_control_conforme()
    huella_1 = cp.huella_canonica(ficha)
    ficha["congelacion"]["huella"] = huella_1
    assert cp.huella_canonica(ficha) == huella_1


def test_deepcopy_del_fixture_no_comparte_estado() -> None:
    a, b = ficha_control_conforme(), ficha_control_conforme()
    a["exenciones_de_control"]["etapas_e0_e5"] = "mutado"
    assert deepcopy(b)["exenciones_de_control"]["etapas_e0_e5"] != "mutado"
