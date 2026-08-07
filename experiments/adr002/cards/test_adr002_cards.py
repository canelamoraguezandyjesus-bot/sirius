"""Pruebas de la ficha de candidato (ADR002-TOL-210, paquete 09).

No miden, no ejecutan candidatos y no tocan el repositorio. Construyen fichas
sinteticas y comprueban que el contrato hace cumplir lo que TOL-210 exige.

La ficha de referencia de estas pruebas **no es la ficha de ningun candidato
real**: no hay candidato autorizado que fichar, y este paquete no lo autoriza.
Es un fixture, y su unico proposito es que las mutaciones que se le aplican
tengan un punto de partida conforme.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.cards import card_protocol as cp
from experiments.adr002.cards import schema_card_v0_1 as esquema
from experiments.adr002.cards import verify_cards as verificacion
from experiments.adr002.tolerances import profile_protocol as pp

RAIZ = Path(__file__).resolve().parents[3]

SHA_FICHA = "a" * 40
SHA_EJECUCION = "b" * 40
SHA_PROTOTIPO = "c" * 40
SHA_CORPUS = "d" * 40


def _etapas() -> list[dict[str, Any]]:
    return [
        {
            "etapa": etapa,
            "coste_local_objetivo_ns": 1_000_000,
            "coste_local_limite_ns": 2_000_000,
            "operaciones_locales": f"operaciones declaradas de {etapa}",
            "coste_externo_declarado": "ninguno: sin red ni modelo externo",
        }
        for etapa in cp.ETAPAS
    ]


def ficha_conforme() -> dict[str, Any]:
    """Fixture: una ficha que cumple el contenido minimo de TOL-210."""
    etapas = _etapas()
    total_local = sum(e["coste_local_limite_ns"] for e in etapas)
    return {
        "documento": "Ficha de candidato ADR002-B para ADR-002",
        "version_esquema": cp.VERSION_ESQUEMA,
        "estado": cp.ESTADO_CONGELADA,
        "plantilla": cp.PLANTILLA,
        "registro": cp.REGISTRO,
        "protocolo": cp.PROTOCOLO,
        "actas_de_puerta": [cp.ACTA_TOL_207, cp.ACTA_TOL_209],
        "identidad": {
            "candidato": "ADR002-B",
            "papel": cp.PAPEL_CANDIDATO,
            "version": 1,
            "sustituye_a": None,
            "motivo_de_sustitucion": None,
        },
        "congelacion": {
            "commit_de_referencia": SHA_FICHA,
            "huella": "0" * 40,
            "ruta": "artifacts/adr002_cards/ficha_ADR002-B_v1.json",
        },
        "arquitectura": {
            "alternativa_minima": "ADR002-B",
            "definicion_canonica_que_asume": "fila de ARQ-00 §23 transcrita literalmente",
            "sustrato_lexico": "FTS5 medido",
            "materializacion_de_relaciones": "desde el canon, regenerables",
            "puerto_de_acceso": "equivalente a KnowledgeSearchRepository (RF-31)",
            "etapas_implementadas": {
                e: f"que ocurre en {e} y que la transiciona" for e in cp.ETAPAS
            },
            "puertas_previas_comunes": {
                p: f"como este candidato satisface {p}" for p in cp.PUERTAS_PREVIAS_COMUNES
            },
        },
        "senal_tardia": {
            "habilitada": "semantica_vectorial",
            "coherente_con_la_alternativa": True,
            "como_satisface_e3": "validacion explicita en E3, no heredada de la senal",
            "validacion_en_e3": "sujeto, polaridad, condicion y tiempo, mecanismo concreto",
            "orden_de_las_etapas_tardias": "E3 antes que E4; congelado",
            "condicion_de_insuficiencia_por_transicion": "una condicion por transicion",
        },
        "restriccion_d": {
            "aplica": False,
            "motivo_de_no_aplicacion": ("la alternativa declarada no habilita dos senales tardias"),
            "senales_en_etapas_distintas": None,
            "orden_predefinido": None,
            "sin_coordinacion_simultanea": None,
            "como_se_demuestra_en_cada_ejecucion": None,
            "traza_a_b04_d15": None,
        },
        "componentes": [
            {
                "papel": "motor de base",
                "nombre": "SQLite",
                "version": "3.45",
                "origen": "biblioteca estandar",
                "acopla_a_proveedor": False,
                "ruta_de_sustitucion": None,
            }
        ],
        "corpus": {
            "version": "v0.4 congelado",
            "mensajes": 5000,
            "recuerdos": 500,
            "decisiones": 50,
            "proyectos": 2,
            "longitud_media_y_distribucion": "media y distribucion declaradas del corpus v0.4",
            "commit": SHA_CORPUS,
            "head_de_esquema": "61be4bb269bf",
            "t0_rederivada_sobre_este_corpus": False,
            "referencia_de_la_rederivacion": (
                "todavia no existe: los pasos 2 y 3 de TOL-208 no estan ejecutados"
            ),
        },
        "protocolo_aplicado": {
            "protocolo": cp.PROTOCOLO,
            "desviaciones": "ninguna",
            "entorno": "LAB-LINUX, carga no controlada y declarada",
            "semilla": "20260731",
            "repeticiones_por_magnitud": 100,
        },
        "sustrato_lexico": {
            "es_el_fts5_medido": True,
            "motivo": "sustrato lexico = FTS5 medido; rigen TOL-101L, TOL-104L y TOL-105",
            "magnitudes": [],
        },
        "indices_no_lexicos": [
            {
                "nombre": "semantico",
                "tipo": "vectorial denso",
                "datos_canonicos_que_cubre": "memorias vigentes",
                "numero_de_elementos": 499,
                "estructura": "384 dimensiones",
                "precision": "float32",
                "bytes_totales": 766_464,
                "bytes_por_elemento": 1536,
                "ratio_sobre_el_canon": 120,
                "porcentaje_del_fichero": 40,
                "crecimiento_por_escala": {"500": 766_464, "5000": 7_680_000, "50000": 76_800_000},
                "construccion_y_reconstruccion": "tiempo y espacio declarados",
                "limites_por_magnitud": {
                    "tamano": 1_000_000,
                    "construccion": 60_000_000_000,
                    "reconstruccion": 60_000_000_000,
                    "borrado": 1_000_000_000,
                },
                "comportamiento_de_borrado": "desaparece con el canon, sin residuo",
                "escala_comun": {"500": 766_464, "5000": 7_680_000, "50000": 76_800_000},
            }
        ],
        "ciclo_de_indice": {
            "operaciones": {
                nombre: {
                    "limite": 1_000_000_000,
                    "fundamento": f"fundamento del limite de {nombre}",
                    "ejecutable_treinta_veces": True,
                    "motivo_de_no_ejecutabilidad": None,
                    "evidencia_alternativa": None,
                }
                for nombre in cp.OPERACIONES_CICLO
            },
            "reconstruccion_desde_el_canon": "se reconstruye del canon, nunca del derivado",
            "desaparicion_completa": "incluye tablas sombra y estructuras auxiliares",
            "tasa_de_exito_del_cien_por_cien": "100 % sobre 30 repeticiones",
            "purga_fisica_sin_fragmento": "conforme a la secuencia de TOL-206",
        },
        "coste_por_etapa": {
            "etapas": etapas,
            "coste_de_la_senal_de_consulta": "local, sin inferencia externa",
            "coste_local_total_ns": total_local,
            "coste_externo_total": "ninguno; nunca se suma al local",
            "coste_extremo_a_extremo_ns": 20_000_000,
        },
        "extremo_a_extremo": {
            "objetivo_p95_ns": 15_000_000,
            "limite_duro_p99_ns": 20_000_000,
            "percentil_y_n": "nearest-rank; n=100",
            "fundamento": "fundamento propio, no derivado de T0",
            "no_deriva_de_tol_102b": True,
            "no_invoca_el_barrido_de_t0": True,
        },
        "almacenamiento": {
            "presupuesto_absoluto_b": cp.PRESUPUESTO_TOL207_B,
            "consumo_declarado_b": 161_061_273,
            "porcentaje_por_mil": cp.por_mil(161_061_273, cp.PRESUPUESTO_TOL207_B),
            "proyeccion_50000_b": 1_610_612_730,
            "cabe": True,
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
        "banda_temporal": {
            "equivalencia_externa": "estado, texto y conteo externos equivalentes",
            "fraccion_de_signo_pareada": "dentro de [0,40 · 0,60] con n>=30 por rama",
            "ausencia_de_separacion_material": "prueba concreta declarada",
            "repeticion_en_sesion_independiente": "mismo veredicto en sesion independiente",
            "modelo_de_amenaza": "observador local con reloj; no se modela el canal externo",
            "no_hereda_la_indistinguibilidad_de_la_linea_base": True,
        },
        "purga": {
            "secuencia": "checkpoint · truncado del journal · VACUUM",
            "ficheros_cubiertos": list(cp.FICHEROS_DE_PURGA),
            "payload_reversible_en_el_derivado": "ninguno literal; representacion no invertible",
            "modelo_de_amenaza": "no mas debil que el de ADR-001",
            "comprobacion_propuesta": "barrido de fragmentos sobre el fichero purgado",
        },
        "huella_candidato": {
            "commit_del_prototipo": SHA_PROTOTIPO,
            "hash_del_arbol_de_fuentes": "sha256 del arbol del candidato",
            "migraciones_o_ddl": "ninguna migracion canonica modificada",
            "artefactos_y_su_hash": "artefactos generados y su hash",
            "reproduccion": "comandos exactos de reproduccion",
        },
        "declaracion_de_congelacion": {
            "texto": (
                "los valores de esta ficha se fijaron antes de la primera ejecucion de este "
                "candidato y no proceden de ningun resultado observado"
            ),
            "responsable": "Proyecto Sirius",
            "fecha": "2026-07-31",
            "valores_anteriores_a_la_primera_ejecucion": True,
        },
        "no_contiene_resultados": True,
    }


def _mutada(**cambios: Any) -> dict[str, Any]:
    ficha = ficha_conforme()
    for ruta, valor in cambios.items():
        partes = ruta.split("__")
        destino: Any = ficha
        for parte in partes[:-1]:
            destino = destino[parte]
        destino[partes[-1]] = valor
    return ficha


# --------------------------------------------------------------------------
# Identidad y constantes
# --------------------------------------------------------------------------


def test_la_ficha_cita_las_puertas_ya_satisfechas_y_no_las_reproclama() -> None:
    """El presupuesto y el perfil los fijaron sus actas: la ficha los cita."""
    assert cp.PRESUPUESTO_TOL207_B == 1_610_612_736
    assert cp.SM_NS == 17_405
    assert cp.U50_NS == 2_685
    assert cp.SESIONES_EXIGIDAS == pp.SESIONES_EXIGIDAS == 11
    assert cp.PROTOCOLO == pp.PROTOCOLO
    assert cp.REGISTRO == pp.REGISTRO


def test_las_plantillas_se_versionan_en_vez_de_editarse() -> None:
    """La v0.1 y la v0.2 se conservan: sus blobs los citan otros documentos."""
    assert cp.PLANTILLA.endswith("v0.3_PROPUESTO.md")
    assert cp.PLANTILLA not in cp.PLANTILLAS_ANTERIORES
    for nombre, esperado in cp.PLANTILLAS_ANTERIORES.items():
        anterior = RAIZ / "docs/architecture" / nombre
        assert anterior.is_file(), nombre
        assert cp.blob_git(anterior.read_bytes()) == esperado, nombre


def test_los_documentos_de_la_plantilla_vigente_existen() -> None:
    for nombre in (cp.PLANTILLA, cp.REGISTRO, cp.PROTOCOLO, cp.ACTA_TOL_207, cp.ACTA_TOL_209):
        assert (RAIZ / "docs/architecture" / nombre).is_file(), nombre


# --------------------------------------------------------------------------
# Contenido minimo
# --------------------------------------------------------------------------


def test_la_ficha_de_referencia_es_conforme() -> None:
    assert esquema.fallos_ficha(ficha_conforme()) == []


def test_una_ficha_vacia_no_pasa_y_el_validador_no_lanza() -> None:
    assert esquema.fallos_ficha({})
    assert esquema.fallos_ficha([])  # type: ignore[arg-type]
    assert esquema.fallos_ficha({"identidad": 7})


@pytest.mark.parametrize("seccion", cp.SECCIONES)
def test_falta_cualquier_seccion_y_la_ficha_cae(seccion: str) -> None:
    ficha = ficha_conforme()
    del ficha[seccion]
    assert any(seccion in f for f in esquema.fallos_ficha(ficha))


@pytest.mark.parametrize("marcador", cp.MARCADORES_VACIOS)
def test_un_campo_pendiente_invalida_la_ficha(marcador: str) -> None:
    """«Pendiente» no es una declaracion: es la ausencia de una."""
    ficha = _mutada(arquitectura__definicion_canonica_que_asume=marcador)
    assert any("debe declararse" in f for f in esquema.fallos_ficha(ficha))
    assert not cp.es_declaracion(marcador)
    assert not cp.es_declaracion(f"  {marcador.upper()}  ")


def test_los_conjuntos_de_campos_estan_cerrados() -> None:
    """Una ficha declara limites; cerrar el conjunto impide colar una medida."""
    for seccion in (
        "identidad",
        "congelacion",
        "arquitectura",
        "corpus",
        "protocolo_aplicado",
        "estabilidad",
        "almacenamiento",
        "extremo_a_extremo",
        "purga",
        "huella_candidato",
        "declaracion_de_congelacion",
    ):
        ficha = ficha_conforme()
        ficha[seccion]["p95_observado_ns"] = 1
        assert any("ajenos al esquema" in f for f in esquema.fallos_ficha(ficha)), seccion

    ficha = ficha_conforme()
    ficha["resultado_de_la_ejecucion"] = {"p95_ns": 1}
    assert any("ajenos al esquema" in f for f in esquema.fallos_ficha(ficha))


# --------------------------------------------------------------------------
# Coherencia con las puertas ya satisfechas
# --------------------------------------------------------------------------


def test_la_ficha_no_puede_proponer_su_propio_perfil_de_estabilidad() -> None:
    for campo, valor in (("sesiones_previstas", 5), ("sm_ns", 1), ("u50_ns", 1)):
        ficha = ficha_conforme()
        ficha["estabilidad"][campo] = valor
        assert esquema.fallos_ficha(ficha), campo

    ficha = _mutada(estabilidad__sin_umbral_relativo_para_p95=False)
    assert any("no crea umbral relativo para P95" in f for f in esquema.fallos_ficha(ficha))


def test_cinco_sesiones_es_exactamente_lo_que_la_regla_prohibe() -> None:
    fallos = cp.estabilidad_conforme_al_perfil(
        {
            "sesiones_previstas": 5,
            "sm_ns": cp.SM_NS,
            "u50_ns": cp.U50_NS,
            "sin_umbral_relativo_para_p95": True,
        }
    )
    assert any("exactamente 11" in f for f in fallos)


def test_la_ficha_no_puede_reescribir_el_presupuesto_de_tol207() -> None:
    ficha = _mutada(almacenamiento__presupuesto_absoluto_b=cp.PRESUPUESTO_TOL207_B * 2)
    assert any("debe citar el aprobado por TOL-207" in f for f in esquema.fallos_ficha(ficha))


def test_el_porcentaje_y_el_cabe_se_recomputan() -> None:
    ficha = _mutada(almacenamiento__porcentaje_por_mil=1)
    assert any("porcentaje_por_mil no recomputa" in f for f in esquema.fallos_ficha(ficha))

    ficha = ficha_conforme()
    ficha["almacenamiento"]["consumo_declarado_b"] = cp.PRESUPUESTO_TOL207_B + 1
    assert any("cabe no recomputa" in f for f in esquema.fallos_ficha(ficha))
    assert not cp.cabe_en_el_presupuesto(cp.PRESUPUESTO_TOL207_B + 1, cp.PRESUPUESTO_TOL207_B)


def test_el_protocolo_declarado_debe_ser_el_aprobado() -> None:
    ficha = _mutada(
        protocolo_aplicado__protocolo="SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md"
    )
    assert any("debe ser el aprobado" in f for f in esquema.fallos_ficha(ficha))


def test_menos_de_treinta_repeticiones_no_pasa() -> None:
    ficha = _mutada(protocolo_aplicado__repeticiones_por_magnitud=29)
    assert any("al menos 30" in f for f in esquema.fallos_ficha(ficha))


# --------------------------------------------------------------------------
# Coste, coherencia y prohibiciones expresas
# --------------------------------------------------------------------------


def test_la_suma_por_etapas_debe_explicar_el_total() -> None:
    ficha = _mutada(coste_por_etapa__coste_local_total_ns=1)
    assert any("no explica el total declarado" in f for f in esquema.fallos_ficha(ficha))
    assert not cp.coste_local_coherente(_etapas(), 1)
    assert cp.coste_local_coherente(_etapas(), 6 * 2_000_000)


def test_el_coste_externo_no_entra_en_la_aritmetica_local() -> None:
    """TOL-202 prohibe sumarlo: por eso se declara en texto, no en enteros."""
    ficha = ficha_conforme()
    total = ficha["coste_por_etapa"]["coste_local_total_ns"]
    ficha["coste_por_etapa"]["coste_externo_total"] = 999
    assert any("prohibe sumarlo al coste local" in f for f in esquema.fallos_ficha(ficha))
    # Y el total sigue siendo el de las etapas locales: nada externo lo movio.
    assert total == sum(e["coste_local_limite_ns"] for e in _etapas())


def test_un_objetivo_por_encima_de_su_limite_no_es_un_objetivo() -> None:
    ficha = _mutada(extremo_a_extremo__objetivo_p95_ns=30_000_000)
    assert any("supera al limite duro" in f for f in esquema.fallos_ficha(ficha))
    assert not cp.objetivo_no_supera_al_limite(2, 1)
    assert cp.objetivo_no_supera_al_limite(1, 1)


def test_el_extremo_a_extremo_debe_cuadrar_con_el_coste_por_etapa() -> None:
    ficha = _mutada(coste_por_etapa__coste_extremo_a_extremo_ns=99)
    assert any("no coincide con el limite duro" in f for f in esquema.fallos_ficha(ficha))


def test_las_dos_prohibiciones_expresas_del_extremo_a_extremo() -> None:
    for campo in ("no_deriva_de_tol_102b", "no_invoca_el_barrido_de_t0"):
        ficha = ficha_conforme()
        ficha["extremo_a_extremo"][campo] = False
        assert any(campo in f for f in esquema.fallos_ficha(ficha)), campo


def test_la_indistinguibilidad_de_la_linea_base_no_se_hereda() -> None:
    ficha = _mutada(banda_temporal__no_hereda_la_indistinguibilidad_de_la_linea_base=False)
    assert any("no se hereda" in f for f in esquema.fallos_ficha(ficha))


# --------------------------------------------------------------------------
# No ejecutabilidad y puertas previas
# --------------------------------------------------------------------------


def test_la_no_ejecutabilidad_se_declara_antes_y_con_fundamento() -> None:
    ficha = ficha_conforme()
    ficha["ciclo_de_indice"]["operaciones"]["borrado"]["ejecutable_treinta_veces"] = False
    fallos = esquema.fallos_ficha(ficha)
    assert any("fundamento tecnico" in f for f in fallos)
    assert any("evidencia alternativa" in f for f in fallos)

    ficha["ciclo_de_indice"]["operaciones"]["borrado"]["motivo_de_no_ejecutabilidad"] = (
        "el borrado completo destruye el fixture y no puede repetirse sin recrearlo"
    )
    ficha["ciclo_de_indice"]["operaciones"]["borrado"]["evidencia_alternativa"] = (
        "diez repeticiones sobre copias limpias independientes"
    )
    assert esquema.fallos_ficha(ficha) == []


def test_una_operacion_ejecutable_no_declara_exencion() -> None:
    ficha = ficha_conforme()
    ficha["ciclo_de_indice"]["operaciones"]["tamano"]["motivo_de_no_ejecutabilidad"] = "x"
    assert any("no declara motivo de exencion" in f for f in esquema.fallos_ficha(ficha))


def test_las_seis_puertas_previas_comunes_son_obligatorias() -> None:
    """No son ventaja de ningun candidato y ninguno puede omitirlas."""
    for puerta in cp.PUERTAS_PREVIAS_COMUNES:
        ficha = ficha_conforme()
        del ficha["arquitectura"]["puertas_previas_comunes"][puerta]
        assert esquema.fallos_ficha(ficha), puerta


def test_el_acoplamiento_a_proveedor_exige_ruta_de_sustitucion() -> None:
    """Puerta 6 de ADR-002 (RF-31)."""
    ficha = ficha_conforme()
    ficha["componentes"][0]["acopla_a_proveedor"] = True
    assert any("puerta 6" in f for f in esquema.fallos_ficha(ficha))
    ficha["componentes"][0]["ruta_de_sustitucion"] = "sustituible por X sin cambiar el puerto"
    assert esquema.fallos_ficha(ficha) == []


def test_el_fts5_medido_no_congela_magnitudes_propias() -> None:
    ficha = ficha_conforme()
    ficha["sustrato_lexico"]["magnitudes"] = [
        {"magnitud": "latencia", "objetivo": 1, "limite_duro": 2, "fundamento": "x"}
    ]
    assert any("debe estar vacia" in f for f in esquema.fallos_ficha(ficha))


def test_un_sustrato_alternativo_debe_congelar_las_suyas() -> None:
    ficha = ficha_conforme()
    ficha["sustrato_lexico"]["es_el_fts5_medido"] = False
    ficha["sustrato_lexico"]["motivo"] = "sustrato alternativo: Tantivy 0.22"
    assert any("debe congelar sus propias magnitudes" in f for f in esquema.fallos_ficha(ficha))


# --------------------------------------------------------------------------
# Versionado
# --------------------------------------------------------------------------


def test_la_primera_version_no_sustituye_a_ninguna() -> None:
    ficha = _mutada(identidad__sustituye_a=0)
    assert any("no sustituye a ninguna" in f for f in esquema.fallos_ficha(ficha))


def test_una_version_sucesora_declara_a_quien_sustituye_y_por_que() -> None:
    ficha = ficha_conforme()
    ficha["identidad"]["version"] = 2
    fallos = esquema.fallos_ficha(ficha)
    assert any("sustituye_a debe ser 1" in f for f in fallos)
    assert any("por que sustituye" in f for f in fallos)

    ficha["identidad"]["sustituye_a"] = 1
    ficha["identidad"]["motivo_de_sustitucion"] = "cambio del limite de reconstruccion"
    assert esquema.fallos_ficha(ficha) == []


def test_las_versiones_crecen_de_una_en_una() -> None:
    assert cp.version_sucesora_valida(1, 2)
    assert not cp.version_sucesora_valida(1, 3)
    assert not cp.version_sucesora_valida(2, 1)


# --------------------------------------------------------------------------
# Anterioridad: la regla que convierte «congelada antes» en comprobable
# --------------------------------------------------------------------------


def _referencia(**cambios: Any) -> cp.ReferenciaEjecucion:
    base = {
        "candidato": "ADR002-B",
        "version": 1,
        "huella": "0" * 40,
        "commit_de_ejecucion": SHA_EJECUCION,
    }
    base.update(cambios)
    return cp.ReferenciaEjecucion(**base)  # type: ignore[arg-type]


def _confirmada(**cambios: Any) -> cp.FichaConfirmada:
    base = {
        "candidato": "ADR002-B",
        "version": 1,
        "huella": "0" * 40,
        "commit_de_entrada": SHA_FICHA,
        "estado": cp.ESTADO_CONGELADA,
    }
    base.update(cambios)
    return cp.FichaConfirmada(**base)  # type: ignore[arg-type]


def test_una_ejecucion_con_ficha_anterior_es_utilizable() -> None:
    veredicto = cp.admisibilidad(_referencia(), [_confirmada()], es_ancestro=lambda a, b: True)
    assert veredicto.resultado == cp.ADMISIBLE
    assert veredicto.utilizable


def test_una_ejecucion_sin_ficha_no_es_utilizable_como_evidencia() -> None:
    veredicto = cp.admisibilidad(_referencia(), [], es_ancestro=lambda a, b: True)
    assert veredicto.resultado == cp.NO_UTILIZABLE
    assert veredicto.motivo == cp.MOTIVO_SIN_FICHA
    assert not veredicto.utilizable


def test_una_ficha_posterior_a_la_ejecucion_no_vale() -> None:
    """La anterioridad es una relacion de ancestro, no una fecha escrita."""
    veredicto = cp.admisibilidad(_referencia(), [_confirmada()], es_ancestro=lambda a, b: False)
    assert veredicto.motivo == cp.MOTIVO_FICHA_POSTERIOR


def test_la_ficha_en_el_mismo_commit_que_la_ejecucion_no_es_anterior() -> None:
    """Aparecer en el mismo acto no es haber congelado antes."""
    veredicto = cp.admisibilidad(
        _referencia(commit_de_ejecucion=SHA_FICHA),
        [_confirmada()],
        es_ancestro=lambda a, b: True,
    )
    assert veredicto.motivo == cp.MOTIVO_FICHA_POSTERIOR


def test_una_huella_distinta_apunta_a_otro_contenido() -> None:
    veredicto = cp.admisibilidad(
        _referencia(huella="1" * 40), [_confirmada()], es_ancestro=lambda a, b: True
    )
    assert veredicto.motivo == cp.MOTIVO_HUELLA_DISTINTA


def test_una_ficha_sustituida_no_ampara_ejecuciones() -> None:
    veredicto = cp.admisibilidad(
        _referencia(),
        [_confirmada(estado=cp.ESTADO_SUSTITUIDA)],
        es_ancestro=lambda a, b: True,
    )
    assert veredicto.motivo == cp.MOTIVO_SIN_FICHA


def test_admisibilidad_exige_un_comprobador_de_ancestro() -> None:
    with pytest.raises(TypeError):
        cp.admisibilidad(_referencia(), [_confirmada()], es_ancestro="no invocable")


# --------------------------------------------------------------------------
# Ejecutabilidad del candidato
# --------------------------------------------------------------------------


def _puertas(**cambios: Any) -> dict[str, bool]:
    puertas = dict.fromkeys(cp.PUERTAS_DE_ARRANQUE, True)
    puertas.update(cambios)
    return puertas


def test_un_candidato_con_ficha_y_puertas_satisfechas_es_ejecutable() -> None:
    veredicto = cp.ejecutabilidad("ADR002-B", [_confirmada()], puertas=_puertas())
    assert veredicto.resultado == cp.ADMISIBLE


def test_un_candidato_sin_ficha_no_es_ejecutable() -> None:
    veredicto = cp.ejecutabilidad("ADR002-B", [], puertas=_puertas())
    assert veredicto.resultado == cp.NO_EJECUTABLE
    assert veredicto.motivo == cp.MOTIVO_SIN_FICHA


@pytest.mark.parametrize("puerta", cp.PUERTAS_DE_ARRANQUE)
def test_una_puerta_de_arranque_pendiente_impide_ejecutar(puerta: str) -> None:
    veredicto = cp.ejecutabilidad("ADR002-B", [_confirmada()], puertas=_puertas(**{puerta: False}))
    assert veredicto.motivo == cp.MOTIVO_PUERTA_PENDIENTE


def test_la_particion_t1_t4_ya_no_es_el_universo_de_fichas() -> None:
    """La Resolucion v1.0 la sustituyo por las alternativas minimas."""
    assert "T1" not in cp.CANDIDATOS
    with pytest.raises(cp.FichaInvalidaError):
        cp.ejecutabilidad("T1", [], puertas=_puertas())


def test_las_puertas_de_arranque_son_las_cinco_del_registro() -> None:
    assert cp.PUERTAS_DE_ARRANQUE == (
        "SRC-ADR002-01",
        "ADR002-TOL-207",
        "ADR002-TOL-208",
        "ADR002-TOL-209",
        "ADR002-TOL-210",
    )
    assert not cp.puertas_de_arranque_satisfechas({})


# --------------------------------------------------------------------------
# Controles y recorrido completo
# --------------------------------------------------------------------------


def test_los_controles_fallan_cerrado() -> None:
    assert cp.evaluar_controles(dict.fromkeys(cp.CONTROLES_BLOQUEANTES, True)).valido
    incompleto = dict.fromkeys(cp.CONTROLES_BLOQUEANTES, True)
    del incompleto["anterioridad_comprobada_contra_git"]
    assert not cp.evaluar_controles(incompleto).valido
    assert not cp.evaluar_controles({c: 1 for c in cp.CONTROLES_BLOQUEANTES}).valido  # type: ignore[misc]


def _dependencias(
    fichas: Mapping[str, bytes],
    *,
    registrado: Mapping[str, str] | None = None,
    ancestro: bool = True,
    confirmadas_en_git: bool = True,
    commit_existe: bool = True,
) -> verificacion.DependenciasVerificacion:
    def leer_bytes(ruta: str) -> bytes:
        if ruta in fichas:
            return fichas[ruta]
        return (RAIZ / ruta).read_bytes()

    def blob_en_commit(sha: str, ruta: str) -> str | None:
        if registrado is not None:
            return registrado.get(ruta)
        return cp.blob_git(fichas[ruta]) if ruta in fichas else None

    entorno = cp.EntornoCustodia(
        leer_bytes=leer_bytes,
        es_ancestro=lambda a, b: ancestro,
        existe_commit=lambda sha: commit_existe,
        head=lambda: SHA_EJECUCION,
        arbol_limpio=lambda: True,
        diff_vacio=lambda desde, hasta, rutas: True,
        blob_en_commit=blob_en_commit,
    )

    def primer_commit_con_blob(ruta: str, blob: str) -> str | None:
        if not confirmadas_en_git:
            return None
        return SHA_FICHA if ruta in fichas and cp.blob_git(fichas[ruta]) == blob else None

    return verificacion.DependenciasVerificacion(
        entorno_custodia=entorno,
        listar_fichas=lambda: tuple(fichas),
        leer_ficha=leer_bytes,
        blob_en_commit=blob_en_commit,
        primer_commit_con_blob=primer_commit_con_blob,
    )


def _serializada(ficha: Mapping[str, Any]) -> bytes:
    return (json.dumps(ficha, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def _con_huella_real(ficha: dict[str, Any], ruta: str) -> bytes:
    """Sella la ficha con su huella canonica y la serializa.

    La huella se calcula sobre el contenido normativo EXCLUIDA ella misma, de
    modo que escribirla no altera lo que se hasheo. Una huella que se
    incluyese a si misma no tendria punto fijo.
    """
    ficha["congelacion"]["ruta"] = ruta
    ficha["congelacion"]["huella"] = cp.huella_canonica(ficha)
    return _serializada(ficha)


def test_el_recorrido_completo_acepta_una_ficha_bien_congelada() -> None:
    ruta = "artifacts/adr002_cards/ficha_ADR002-B_v1.json"
    crudo = _con_huella_real(ficha_conforme(), ruta)
    resultado = verificacion.verificar(_dependencias({ruta: crudo}))
    assert resultado.conforme, resultado.fallos
    assert len(resultado.confirmadas) == 1
    assert resultado.confirmadas[0].candidato == "ADR002-B"


def test_una_huella_que_no_recomputa_bloquea() -> None:
    ruta = "artifacts/adr002_cards/ficha_ADR002-B_v1.json"
    ficha = ficha_conforme()
    ficha["congelacion"]["ruta"] = ruta
    ficha["congelacion"]["huella"] = "f" * 40
    resultado = verificacion.verificar(_dependencias({ruta: _serializada(ficha)}))
    assert any("no recomputa sobre el contenido normativo" in f for f in resultado.fallos)


def test_una_ficha_sin_confirmar_en_el_repositorio_bloquea() -> None:
    """Una ficha que solo existe en el arbol de trabajo no congela nada."""
    ruta = "artifacts/adr002_cards/ficha_ADR002-B_v1.json"
    crudo = _con_huella_real(ficha_conforme(), ruta)
    resultado = verificacion.verificar(_dependencias({ruta: crudo}, confirmadas_en_git=False))
    assert any("no esta confirmada en el repositorio" in f for f in resultado.fallos)
    assert resultado.confirmadas == ()


def test_un_commit_de_referencia_inexistente_bloquea() -> None:
    ruta = "artifacts/adr002_cards/ficha_ADR002-B_v1.json"
    crudo = _con_huella_real(ficha_conforme(), ruta)
    resultado = verificacion.verificar(_dependencias({ruta: crudo}, commit_existe=False))
    assert any("commit de referencia declarado no existe" in f for f in resultado.fallos)


def test_la_ficha_no_declara_el_commit_que_la_contiene() -> None:
    """Seria autorreferencial: el SHA depende del contenido que lo incluye.

    La ficha declara su **commit de referencia** —el del acto de gobierno bajo
    el que se congela, que ya existe cuando se escribe— y el commit en que
    entro de verdad lo **observa** el verificador en el historial.
    """
    assert "commit" not in cp.CAMPOS_CONGELACION
    assert "commit_de_referencia" in cp.CAMPOS_CONGELACION
    ruta = "artifacts/adr002_cards/ficha_ADR002-B_v1.json"
    crudo = _con_huella_real(ficha_conforme(), ruta)
    resultado = verificacion.verificar(_dependencias({ruta: crudo}))
    assert resultado.confirmadas[0].commit_de_entrada == SHA_FICHA


def test_dos_fichas_congeladas_del_mismo_candidato_bloquean() -> None:
    primera = "artifacts/adr002_cards/ficha_ADR002-B_v1.json"
    segunda = "artifacts/adr002_cards/ficha_ADR002-B_v2.json"
    uno = _con_huella_real(ficha_conforme(), primera)
    otra = ficha_conforme()
    otra["identidad"]["version"] = 2
    otra["identidad"]["sustituye_a"] = 1
    otra["identidad"]["motivo_de_sustitucion"] = "endurecimiento del limite de borrado"
    dos = _con_huella_real(otra, segunda)
    resultado = verificacion.verificar(_dependencias({primera: uno, segunda: dos}))
    assert any("CONGELADA a la vez" in f for f in resultado.fallos)


def test_un_json_ilegible_no_revienta_el_recorrido() -> None:
    ruta = "artifacts/adr002_cards/roto.json"
    resultado = verificacion.verificar(_dependencias({ruta: b"{no es json"}))
    assert any("no es JSON valido" in f for f in resultado.fallos)


def test_el_recorrido_denuncia_una_ejecucion_sin_ficha() -> None:
    resultado = verificacion.verificar(_dependencias({}), referencia=_referencia())
    assert resultado.veredicto is not None
    assert resultado.veredicto.motivo == cp.MOTIVO_SIN_FICHA
    assert any("no es utilizable como evidencia" in f for f in resultado.fallos)
    assert any("no es ejecutable" in f for f in resultado.fallos)


def test_el_recorrido_denuncia_una_ficha_no_anterior() -> None:
    ruta = "artifacts/adr002_cards/ficha_ADR002-B_v1.json"
    ficha = ficha_conforme()
    ficha["congelacion"]["ruta"] = ruta
    crudo = _con_huella_real(ficha, ruta)
    huella = json.loads(crudo)["congelacion"]["huella"]
    resultado = verificacion.verificar(
        _dependencias({ruta: crudo}, ancestro=False),
        referencia=_referencia(huella=huella, version=1),
    )
    assert resultado.veredicto is not None
    assert resultado.veredicto.motivo == cp.MOTIVO_FICHA_POSTERIOR


def test_la_plantilla_anterior_alterada_bloquea_el_recorrido() -> None:
    ruta = f"docs/architecture/{next(iter(cp.PLANTILLAS_ANTERIORES))}"
    resultado = verificacion.verificar(_dependencias({ruta: b"alterada"}))
    assert any("plantilla anterior alterada" in f for f in resultado.fallos)


# --------------------------------------------------------------------------
# Interfaz de linea de ordenes
# --------------------------------------------------------------------------


def test_sin_check_no_verifica_nada() -> None:
    assert verificacion.main([]) == verificacion.CODIGO_SIN_CHECK


def test_el_plan_no_verifica_y_no_escribe() -> None:
    assert verificacion.main(["--plan"]) == verificacion.CODIGO_OK


def test_execution_exige_los_tres_datos_de_la_referencia() -> None:
    assert (
        verificacion.main(["--check", "--execution", SHA_EJECUCION])
        == verificacion.CODIGO_BLOQUEADO
    )


def test_las_fichas_congeladas_son_las_esperadas() -> None:
    """El estado sigue al repositorio, y cada ficha nueva se declara aqui.

    Afirmo «cero fichas» hasta `95d00a1`, que congelo la del control; despues
    solo la del control, hasta que el paquete 11 congelo la de `ADR002-A`. El
    paquete de correccion 01 emite la v2 de `ADR002-A` y **sustituye** la v1,
    que sigue presente: una ficha sustituida no se borra, se marca. El paquete
    12 congela la v1 de `ADR002-B`. El criterio no cambia —toda ficha presente
    debe ser conforme y estar declarada—: cambia la lista, y una ficha
    inesperada sigue fallando.
    """
    resultado = verificacion.verificar(verificacion.dependencias_reales(RAIZ))
    assert resultado.conforme, resultado.fallos
    assert [(f.candidato, f.version, f.estado) for f in resultado.confirmadas] == [
        ("ADR002-A", 1, cp.ESTADO_SUSTITUIDA),
        ("ADR002-A", 2, cp.ESTADO_SUSTITUIDA),
        ("ADR002-A", 3, cp.ESTADO_SUSTITUIDA),
        ("ADR002-A", 4, cp.ESTADO_SUSTITUIDA),
        ("ADR002-A", 5, cp.ESTADO_CONGELADA),
        ("ADR002-B", 1, cp.ESTADO_SUSTITUIDA),
        ("ADR002-B", 2, cp.ESTADO_SUSTITUIDA),
        ("ADR002-B", 3, cp.ESTADO_SUSTITUIDA),
        ("ADR002-B", 4, cp.ESTADO_SUSTITUIDA),
        ("ADR002-B", 5, cp.ESTADO_SUSTITUIDA),
        ("ADR002-B", 6, cp.ESTADO_SUSTITUIDA),
        ("ADR002-B", 7, cp.ESTADO_CONGELADA),
        ("ADR002-C", 1, cp.ESTADO_SUSTITUIDA),
        ("ADR002-C", 2, cp.ESTADO_CONGELADA),
        ("ADR002-D", 1, cp.ESTADO_SUSTITUIDA),
        ("ADR002-D", 2, cp.ESTADO_CONGELADA),
        (cp.CONTROL, 1, cp.ESTADO_CONGELADA),
    ]


def test_una_sola_ficha_congelada_por_candidato() -> None:
    """Regla 5 de TOL-210: publicar una sucesora obliga a sustituir la anterior."""
    resultado = verificacion.verificar(verificacion.dependencias_reales(RAIZ))
    congeladas = [f.candidato for f in resultado.confirmadas if f.estado == cp.ESTADO_CONGELADA]
    assert len(congeladas) == len(set(congeladas))


def test_el_recorrido_real_sobre_el_repositorio_no_escribe(tmp_path: Path) -> None:
    antes = sorted(p.name for p in (RAIZ / "artifacts").iterdir())
    verificacion.main(["--check"], dependencias=verificacion.dependencias_reales(RAIZ))
    assert sorted(p.name for p in (RAIZ / "artifacts").iterdir()) == antes
    assert list(tmp_path.iterdir()) == []


def test_el_fixture_no_es_la_ficha_de_ningun_candidato_real() -> None:
    """Ninguna ficha sintetica de estas pruebas vive en el repositorio.

    Con fichas reales presentes, la garantia se comprueba ficha a ficha: el
    commit de referencia sintetico no aparece en ninguna real.
    """
    sintetica = deepcopy(ficha_conforme())
    assert sintetica["congelacion"]["commit_de_referencia"] == SHA_FICHA
    carpeta = RAIZ / verificacion.DIRECTORIO_FICHAS
    for ruta in sorted(carpeta.glob("*.json")) if carpeta.exists() else []:
        real = json.loads(ruta.read_text(encoding="utf-8"))
        assert real != sintetica
        assert real["congelacion"]["commit_de_referencia"] != SHA_FICHA


def test_el_estado_de_las_puertas_se_deriva_de_las_actas_que_existen() -> None:
    """El estado sigue al repositorio: una puerta vale lo que su acta.

    Esta prueba afirmaba `ADR002-TOL-208` en `False` hasta que su acta de
    aprobacion existio; su §5 registra la evolucion. El criterio no cambia
    —una puerta sin acta no esta satisfecha—, y la direccion bloqueante se
    conserva comprobada abajo con un entorno sin ninguna acta.
    """
    deps = verificacion.dependencias_reales(RAIZ)
    puertas = cp.estado_de_las_puertas(deps.entorno_custodia)
    for puerta in cp.PUERTAS_DE_ARRANQUE:
        assert puertas[puerta] is True, puerta
    assert cp.puertas_de_arranque_satisfechas(puertas)


def test_una_puerta_sin_su_acta_no_esta_satisfecha() -> None:
    """La direccion bloqueante no depende del estado del repositorio."""

    def sin_actas(_ruta: str) -> bytes:
        raise OSError(_ruta)

    entorno = cp.EntornoCustodia(
        leer_bytes=sin_actas,
        es_ancestro=lambda a, b: True,
        existe_commit=lambda sha: True,
        head=lambda: "0" * 40,
        arbol_limpio=lambda: True,
        diff_vacio=lambda desde, hasta, rutas: True,
        blob_en_commit=lambda sha, ruta: None,
    )
    puertas = cp.estado_de_las_puertas(entorno)
    assert all(estado is False for estado in puertas.values())
    assert not cp.puertas_de_arranque_satisfechas(puertas)


def test_sin_fichas_no_se_publican_catorce_controles_en_verde() -> None:
    """Publicarlos sin haber mirado ninguna ficha seria el defecto a corregir."""
    resultado = verificacion.verificar(_dependencias({}))
    assert resultado.controles is None
    assert resultado.conforme


def test_con_una_ficha_conforme_los_catorce_controles_se_computan() -> None:
    ruta = "artifacts/adr002_cards/ficha_ADR002-B_v1.json"
    crudo = _con_huella_real(ficha_conforme(), ruta)
    resultado = verificacion.verificar(_dependencias({ruta: crudo}))
    assert resultado.controles is not None
    assert set(resultado.controles) == set(cp.CONTROLES_BLOQUEANTES)
    assert all(resultado.controles.values()), resultado.controles
    assert resultado.conforme


def test_una_ficha_invalida_tumba_los_controles_de_contenido() -> None:
    ruta = "artifacts/adr002_cards/ficha_ADR002-B_v1.json"
    ficha = ficha_conforme()
    ficha["estabilidad"]["sesiones_previstas"] = 5
    crudo = _con_huella_real(ficha, ruta)
    resultado = verificacion.verificar(_dependencias({ruta: crudo}))
    assert resultado.controles is not None
    assert resultado.controles["once_sesiones_exigidas"] is False
    assert any("controles bloqueantes fallidos" in f for f in resultado.fallos)


def test_un_documento_de_particion_ausente_bloquea() -> None:
    """Sin la Resolucion, el universo de fichas no seria acreditable."""
    entorno_roto = _dependencias({})
    faltante = f"docs/architecture/{cp.DOCUMENTOS_DE_PARTICION[0]}"

    def _leer(ruta: str) -> bytes:
        if ruta == faltante:
            raise OSError(ruta)
        return (RAIZ / ruta).read_bytes()

    deps = verificacion.DependenciasVerificacion(
        entorno_custodia=cp.EntornoCustodia(
            leer_bytes=_leer,
            es_ancestro=entorno_roto.entorno_custodia.es_ancestro,
            existe_commit=entorno_roto.entorno_custodia.existe_commit,
            head=entorno_roto.entorno_custodia.head,
            arbol_limpio=entorno_roto.entorno_custodia.arbol_limpio,
            diff_vacio=entorno_roto.entorno_custodia.diff_vacio,
            blob_en_commit=entorno_roto.entorno_custodia.blob_en_commit,
        ),
        listar_fichas=lambda: (),
        leer_ficha=_leer,
        blob_en_commit=entorno_roto.blob_en_commit,
        primer_commit_con_blob=entorno_roto.primer_commit_con_blob,
    )
    resultado = verificacion.verificar(deps)
    assert any("documento de particion ausente" in f for f in resultado.fallos)
