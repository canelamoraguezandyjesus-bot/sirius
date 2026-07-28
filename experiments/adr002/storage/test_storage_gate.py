"""Puerta de pruebas de ADR002-TOL-207 v0.2 — paquete de trabajo 04.

Recalcula la aritmética normativa desde las constantes, verifica los blobs
congelados, valida la evidencia versionada, ejercita las sondas reales y la
contabilidad de pico, y ejecuta las pruebas negativas obligatorias: cada
control crítico se demuestra rompiéndolo.

Regla de no mutación: ninguna prueba escribe fuera de ``tmp_path`` y la
validación del artefacto se comprueba byte a byte antes y después.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experiments.adr002.benchmark import schema_v0_4 as S4  # noqa: E402
from experiments.adr002.storage import environment_capture as EC  # noqa: E402
from experiments.adr002.storage import filesystem_probes as FP  # noqa: E402
from experiments.adr002.storage import schema_storage_v0_1 as SS  # noqa: E402
from experiments.adr002.storage import storage_accounting as SA  # noqa: E402

_MIB = 1_048_576
ARTEFACTO = _REPO_ROOT / "artifacts" / "adr002_storage" / "entorno_lab_v0.1.json"
BENCHMARK = _REPO_ROOT / "experiments" / "adr002" / "benchmark"


@pytest.fixture(scope="module")
def doc() -> dict[str, Any]:
    contenido: dict[str, Any] = json.loads(ARTEFACTO.read_text(encoding="utf-8"))
    return contenido


@pytest.fixture(scope="module")
def corpus() -> dict[str, Any]:
    ruta = BENCHMARK / "performance_corpus_v0_2.json"
    contenido: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return contenido


def blob_git(ruta: Path) -> str:
    datos = ruta.read_bytes()
    return hashlib.sha1(b"blob %d\x00" % len(datos) + datos).hexdigest()


_BORRAR = object()


def con_mutacion(base: dict[str, Any], claves: list[str | int], valor: Any) -> dict[str, Any]:
    """Copia profunda del documento con una única mutación anidada."""
    mutado = copy.deepcopy(base)
    nodo: Any = mutado
    for clave in claves[:-1]:
        nodo = nodo[clave]
    if valor is _BORRAR:
        del nodo[claves[-1]]
    else:
        nodo[claves[-1]] = valor
    return mutado


# ===========================================================================
# Aritmética normativa · recalculada, nunca duplicada a mano
# ===========================================================================


def test_reserva_seguridad_es_mitad_exacta() -> None:
    assert SS.E_MIN_HISTORICO % 2 == 0
    assert SS.RESERVA_SEGURIDAD == SS.E_MIN_HISTORICO // 2
    assert SS.RESERVA_SEGURIDAD == 15_652_161_536


def test_suelo_es_suma_exacta_de_partidas() -> None:
    suma = SS.RESERVA_SEGURIDAD + SS.RESERVA_OPERATIVA + SS.PRESUPUESTO_AGREGADO
    assert SS.SUELO_ADMISION == suma == 30_684_547_072


def test_holgura_agregado_exacta() -> None:
    holgura = SS.PRESUPUESTO_AGREGADO - SS.NUMERO_CANDIDATOS * SS.PRESUPUESTO_POR_CANDIDATO
    assert SS.HOLGURA_AGREGADO == holgura == 536_870_912


def test_margen_suelo_sobre_e_min_exacto() -> None:
    assert SS.MARGEN_SUELO_SOBRE_E_MIN == SS.E_MIN_HISTORICO - SS.SUELO_ADMISION == 619_776_000


def test_porcentajes_recalculados() -> None:
    assert SS.porcentaje_2dec(SS.PRESUPUESTO_AGREGADO, SS.E_MIN_HISTORICO) == "27,44"
    assert SS.porcentaje_2dec(SS.PRESUPUESTO_POR_CANDIDATO, SS.E_MIN_HISTORICO) == "5,15"
    assert SS.porcentaje_2dec(SS.RESERVA_SEGURIDAD, SS.E_MIN_HISTORICO) == "50,00"
    assert SS.porcentaje_2dec(SS.RESERVA_OPERATIVA, SS.E_MIN_HISTORICO) == "20,58"


def test_cifras_retiradas_son_errores_de_6144_bytes() -> None:
    assert SS.RETIRADA_RESERVA_SEGURIDAD_V0_1 - SS.RESERVA_SEGURIDAD == 6_144
    assert SS.RETIRADO_SUELO_V0_1 - SS.SUELO_ADMISION == 6_144
    aritmetica = SS.aritmetica_normativa()
    assert aritmetica["porcentajes_sobre_e_min_historico"]["agregado"] != "27,43"
    assert aritmetica["errores_historicos_v0_1"]["porcentaje_agregado"] == "27,43"
    assert aritmetica["errores_historicos_v0_1"]["porcentaje_agregado_correcto"] == "27,44"


def test_denominador_es_suma_exacta() -> None:
    assert sum(SS.DENOMINADOR_DESGLOSE.values()) == SS.UNIDADES_LOGICAS_PRIMARIAS == 5_670
    assert (
        sum(SS.DESGLOSE_ITEMS_POR_KIND.values()) == SS.DENOMINADOR_DESGLOSE["items_estructurados"]
    )
    assert set(SS.CARGAS_ESTRUCTURALES_NO_DENOMINADOR) == {"relaciones", "entidades"}


def test_aritmetica_del_documento_coincide(doc: dict[str, Any]) -> None:
    assert doc["aritmetica_recalculada"] == SS.aritmetica_normativa()


def test_suma_de_partidas_de_reserva_operativa(doc: dict[str, Any]) -> None:
    desglose = doc["reserva_operativa_desglose"]
    suma = sum(
        p["asignacion_maxima_bytes"]
        for p in desglose["partidas"]
        if p.get("suma_excluida") is not True
    )
    assert desglose["suma_asignaciones_maximas_bytes"] == suma
    assert suma <= SS.RESERVA_OPERATIVA
    assert desglose["margen_restante_bytes"] == SS.RESERVA_OPERATIVA - suma
    assert desglose["cabe_en_presupuesto"] is True
    for partida in desglose["partidas"]:
        assert partida["bytes_medidos_actualmente"] <= partida["asignacion_maxima_bytes"]


# ===========================================================================
# Denominador y escalas · contra el corpus congelado
# ===========================================================================


def test_denominador_verificado_contra_corpus(corpus: dict[str, Any]) -> None:
    assert len(corpus["items"]) == SS.DENOMINADOR_DESGLOSE["items_estructurados"]
    assert len(corpus["mensajes"]) == SS.DENOMINADOR_DESGLOSE["mensajes"]
    assert len(corpus["documentos"]) == SS.DENOMINADOR_DESGLOSE["documentos"]
    assert len(corpus["relaciones"]) == SS.CARGAS_ESTRUCTURALES_NO_DENOMINADOR["relaciones"]
    assert len(corpus["entidades"]) == SS.CARGAS_ESTRUCTURALES_NO_DENOMINADOR["entidades"]
    kinds = {"MEMORIA": 0, "DECISION": 0}
    for item in corpus["items"]:
        kinds[item["kind"]] += 1
    assert kinds == dict(SS.DESGLOSE_ITEMS_POR_KIND)


@pytest.mark.parametrize(
    ("unidades", "reparto", "items_kind"),
    [
        (
            500,
            {"items_estructurados": 48, "mensajes": 441, "documentos": 11},
            {"MEMORIA": 44, "DECISION": 4},
        ),
        (
            5_000,
            {"items_estructurados": 485, "mensajes": 4_409, "documentos": 106},
            {"MEMORIA": 441, "DECISION": 44},
        ),
        (
            5_670,
            {"items_estructurados": 550, "mensajes": 5_000, "documentos": 120},
            {"MEMORIA": 500, "DECISION": 50},
        ),
    ],
)
def test_reparto_determinista_por_resto_mayor(
    unidades: int, reparto: dict[str, int], items_kind: dict[str, int]
) -> None:
    escala = SS.derivar_escala(unidades)
    assert escala["reparto"] == reparto
    assert sum(escala["reparto"].values()) == unidades
    assert escala["reparto_items_por_kind"] == items_kind
    assert SS.derivar_escala(unidades) == escala  # determinista


def test_rangos_de_ids_existen_en_el_corpus(corpus: dict[str, Any]) -> None:
    ids_items = {i["id"] for i in corpus["items"]}
    ids_msg = {m["id"] for m in corpus["mensajes"]}
    ids_doc = {d["id"] for d in corpus["documentos"]}
    for unidades in SS.ESCALAS_MEDICION_DIRECTA:
        rangos = SS.derivar_escala(unidades)["rangos_ids"]
        for extremo in rangos["MEMORIA"] + rangos["DECISION"]:
            assert extremo in ids_items, extremo
        for extremo in rangos["mensajes"]:
            assert extremo in ids_msg, extremo
        for extremo in rangos["documentos"]:
            assert extremo in ids_doc, extremo


def test_escala_no_contemplada_falla() -> None:
    with pytest.raises(ValueError):
        SS.derivar_escala(50_000)


def test_modelo_de_crecimiento_lineal_valido() -> None:
    puntos = [(500, 1_000_000), (5_000, 10_000_000), (5_670, 11_340_000)]
    resultado = SS.evaluar_modelo_crecimiento(puntos, "lineal", 0.05)
    assert resultado["resultado"] == "AJUSTE_VALIDO"
    assert resultado["etiqueta_proyeccion"] == SS.ETIQUETA_PROYECTADO
    assert resultado["cota_superior_conservadora_bytes"] >= resultado["proyeccion_50000_bytes"]


def test_negativa_modelo_no_lineal_tratado_como_lineal() -> None:
    cuadratico = [(500, 500**2), (5_000, 5_000**2), (5_670, 5_670**2)]
    resultado = SS.evaluar_modelo_crecimiento(cuadratico, "lineal", 0.05)
    assert resultado["resultado"] == SS.NO_EVALUABLE
    assert "proyeccion_50000_bytes" not in resultado


# ===========================================================================
# Blobs congelados · identidad vinculante del acta v0.4
# ===========================================================================


def test_siete_blobs_congelados_intactos() -> None:
    for nombre, blob in SS.BLOBS_CONGELADOS_V0_4.items():
        assert blob_git(BENCHMARK / nombre) == blob, nombre


def test_sha256_del_corpus_de_rendimiento() -> None:
    datos = (BENCHMARK / "performance_corpus_v0_2.json").read_bytes()
    assert hashlib.sha256(datos).hexdigest() == SS.SHA256_PERFORMANCE_V0_2
    assert SS.SHA256_PERFORMANCE_V0_2 == S4.SHA256_PERFORMANCE_V0_2


def test_congelables_coinciden_con_el_esquema_v0_4() -> None:
    assert set(SS.BLOBS_CONGELADOS_V0_4) == set(S4.CONGELABLES_V0_4)
    assert tuple(S4.NO_CONGELABLES_V0_4) == ("t0_preexecution_projection_v0_2.json",)


def test_blob_de_la_proyeccion_t0_excluida() -> None:
    ruta = BENCHMARK / "t0_preexecution_projection_v0_2.json"
    assert blob_git(ruta) == SS.BLOB_PROYECCION_T0_EXCLUIDA


def test_blobs_del_documento_coinciden(doc: dict[str, Any]) -> None:
    for nombre, blob in SS.BLOBS_CONGELADOS_V0_4.items():
        entrada = doc["blobs_congelados"][nombre]
        assert entrada["blob_esperado"] == entrada["blob_observado"] == blob
        assert entrada["intacto"] is True
    assert doc["blob_proyeccion_t0_excluida"]["blob_observado"] == SS.BLOB_PROYECCION_T0_EXCLUIDA
    assert doc["blob_proyeccion_t0_excluida"]["estado"] == SS.ESTADO_PROYECCION_T0


# ===========================================================================
# Documento de evidencia · validación, no mutación y regeneración
# ===========================================================================


def test_documento_versionado_sin_fallos(doc: dict[str, Any]) -> None:
    assert SS.fallos_entorno_lab(doc) == []


def test_estado_documental_propuesto(doc: dict[str, Any]) -> None:
    assert doc["estado"] == "PROPUESTO"
    assert "PENDIENTE DE AUDITORIA" in doc["estado_detalle"]
    assert doc["clasificacion_entorno"] == "ENVOLVENTE_REPRODUCIBLE"
    assert "NO SATISFECHA" in doc["estado_puertas"]["ADR002-TOL-207"]


def test_validar_no_muta_el_artefacto(doc: dict[str, Any]) -> None:
    antes = hashlib.sha256(ARTEFACTO.read_bytes()).hexdigest()
    copia = copy.deepcopy(doc)
    SS.fallos_entorno_lab(doc)
    assert doc == copia
    despues = hashlib.sha256(ARTEFACTO.read_bytes()).hexdigest()
    assert antes == despues


def test_regeneracion_desde_captura_fija(doc: dict[str, Any]) -> None:
    partidas = {p["partida"]: p for p in doc["reserva_operativa_desglose"]["partidas"]}
    medidas = {
        "repositorio_sin_git_ni_venv_bytes": partidas["repositorio_sin_git_ni_venv"][
            "bytes_medidos_actualmente"
        ],
        "git_bytes": partidas["git"]["bytes_medidos_actualmente"],
        "venv_bytes": partidas["venv"]["bytes_medidos_actualmente"],
        "corpus_congelado_bytes": partidas["corpus_congelado"]["bytes_medidos_actualmente"],
        "artefactos_bytes": partidas["artefactos_informes_logs_resultados"][
            "bytes_medidos_actualmente"
        ],
    }
    regenerado = EC.construir_documento(doc["captura_cruda"], doc["sondas"], medidas)
    assert regenerado == doc


# ===========================================================================
# Captura del entorno · atomicidad por punto de montaje
# ===========================================================================


def test_captura_de_punto_de_montaje_coherente() -> None:
    montaje = EC.capturar_punto_de_montaje(_REPO_ROOT)
    assert montaje["observacion_unica"] is True
    assert montaje["monotonico_ns_antes"] <= montaje["monotonico_ns_despues"]
    vfs = montaje["statvfs"]
    derivados = montaje["derivados"]
    assert derivados["bytes_disponibles"] == vfs["f_bavail"] * vfs["f_frsize"]
    assert derivados["bytes_libres_brutos"] == vfs["f_bfree"] * vfs["f_frsize"]
    assert derivados["diferencia_f_bfree_f_bavail_bloques"] == vfs["f_bfree"] - vfs["f_bavail"]


def test_captura_del_entorno_completa(tmp_path: Path) -> None:
    captura = EC.capturar_entorno(_REPO_ROOT, tmp_path)
    for clave in (
        "utc",
        "timestamp_monotonico_ns",
        "uid_efectivo",
        "gid_efectivo",
        "hostname",
        "machine_id",
        "boot_id",
        "so",
        "kernel",
        "arquitectura",
        "cpu",
        "virtualizacion",
        "puntos_de_montaje",
        "cgroups",
        "ulimit_tamano_fichero",
        "superbloque_ext4",
        "herramientas",
    ):
        assert clave in captura, clave
    assert len(captura["puntos_de_montaje"]) == 2
    assert isinstance(captura["superbloque_ext4"].get("legible"), bool)


def test_negativa_captura_mezclando_dos_statvfs(doc: dict[str, Any]) -> None:
    vfs = doc["captura_cruda"]["puntos_de_montaje"][0]["statvfs"]
    mezclado = con_mutacion(
        doc,
        ["captura_cruda", "puntos_de_montaje", 0, "statvfs", "f_bavail"],
        vfs["f_bavail"] + 1,
    )
    fallos = SS.fallos_entorno_lab(mezclado)
    assert any("mezcla de observaciones" in fallo for fallo in fallos)


# ===========================================================================
# Admisión de la sesión · suelo y filesystem
# ===========================================================================


def test_admision_de_la_sesion_actual(doc: dict[str, Any]) -> None:
    admision = doc["admision_sesion"]
    assert admision["campo_utilizado"] == "f_bavail"
    assert admision["bytes_disponibles"] >= SS.SUELO_ADMISION
    assert admision["supera_suelo"] is True
    assert admision["resultado"] == "ADMITIDA"
    assert admision["mismo_filesystem_repo_temporales"] is True


def test_negativa_f_bavail_bajo_suelo_aceptado(doc: dict[str, Any]) -> None:
    bajo = con_mutacion(doc, ["admision_sesion", "bytes_disponibles"], SS.SUELO_ADMISION - 1)
    fallos = SS.fallos_entorno_lab(bajo)
    assert any("bajo suelo aceptado" in fallo for fallo in fallos)


def test_negativa_f_bfree_usado_como_disponibilidad(doc: dict[str, Any]) -> None:
    vfs = doc["captura_cruda"]["puntos_de_montaje"][0]["statvfs"]
    con_bfree = con_mutacion(
        doc,
        ["admision_sesion", "bytes_disponibles"],
        vfs["f_bfree"] * vfs["f_frsize"],
    )
    fallos = SS.fallos_entorno_lab(con_bfree)
    assert any("f_bfree usado como disponibilidad" in fallo for fallo in fallos)


def test_negativa_repositorio_y_temporales_en_filesystems_distintos(
    doc: dict[str, Any],
) -> None:
    distinto = con_mutacion(doc, ["admision_sesion", "mismo_filesystem_repo_temporales"], False)
    fallos = SS.fallos_entorno_lab(distinto)
    assert any("filesystems distintos" in fallo for fallo in fallos)
    otro_dev = con_mutacion(doc, ["admision_sesion", "st_dev_temporales"], 99_999)
    assert any("st_dev" in fallo for fallo in SS.fallos_entorno_lab(otro_dev))


def test_negativa_inodos_agotados_ignorados(doc: dict[str, Any]) -> None:
    agotado = con_mutacion(doc, ["admision_sesion", "inodos_suficientes"], False)
    fallos = SS.fallos_entorno_lab(agotado)
    assert any("inodos agotados" in fallo for fallo in fallos)


def test_negativa_filesystem_incompatible_aceptado(doc: dict[str, Any]) -> None:
    btrfs = con_mutacion(
        doc,
        ["captura_cruda", "puntos_de_montaje", 0, "filesystem"],
        "btrfs",
    )
    fallos = SS.fallos_entorno_lab(btrfs)
    assert any("no confirma el campo estable filesystem" in fallo for fallo in fallos)


# ===========================================================================
# Proveniencia y anomalía de reserva
# ===========================================================================


def test_proveniencia_de_tres_sesiones(doc: dict[str, Any]) -> None:
    proveniencia = doc["proveniencia"]
    historica = proveniencia["medicion_versionada_historica"]
    assert historica["f_bavail_bytes"] == SS.E_MIN_HISTORICO
    assert historica["evidencia_primaria"] is True
    forense = proveniencia["informe_forense_no_versionado"]
    assert forense["evidencia_primaria"] is False
    assert forense["captura_independiente_versionada"] is False
    assert proveniencia["medicion_paquete_04"]["evidencia_primaria"] is True


def test_anomalia_de_reserva_documentada(doc: dict[str, Any]) -> None:
    anomalia = doc["anomalia_reserva"]
    assert anomalia["diferencia_bytes"] == 861_171_712
    assert (
        anomalia["reserva_aparente_26jul_bytes"] - anomalia["reserva_aparente_forense_bytes"]
        == 861_171_712
    )
    assert anomalia["oculta"] is False
    assert anomalia["demostrable_retrospectivamente_26jul"] is False
    demostracion = anomalia["demostracion_sesion_actual"]
    assert demostracion["f_bfree_menos_f_bavail_bloques"] > 0


def test_negativa_sesion_no_versionada_como_evidencia_primaria(doc: dict[str, Any]) -> None:
    elevada = con_mutacion(
        doc, ["proveniencia", "informe_forense_no_versionado", "evidencia_primaria"], True
    )
    fallos = SS.fallos_entorno_lab(elevada)
    assert any("evidencia primaria" in fallo for fallo in fallos)


def test_negativa_anomalia_de_reserva_ocultada(doc: dict[str, Any]) -> None:
    sin_anomalia = con_mutacion(doc, ["anomalia_reserva"], _BORRAR)
    fallos = SS.fallos_entorno_lab(sin_anomalia)
    assert any("anomalía de reserva ocultada" in fallo for fallo in fallos)
    tapada = con_mutacion(doc, ["anomalia_reserva", "oculta"], True)
    assert any("oculta" in fallo for fallo in SS.fallos_entorno_lab(tapada))


# ===========================================================================
# Constantes y presupuestos · pruebas negativas de identidad en bytes
# ===========================================================================


def test_negativa_presupuesto_solo_en_gib(doc: dict[str, Any]) -> None:
    en_gib = con_mutacion(doc, ["constantes", "presupuesto_por_candidato_bytes"], "1,5 GiB")
    fallos = SS.fallos_entorno_lab(en_gib)
    assert any("entero en bytes" in fallo for fallo in fallos)


def test_negativa_reserva_historica_erronea_aceptada(doc: dict[str, Any]) -> None:
    erronea = con_mutacion(
        doc, ["constantes", "reserva_seguridad_bytes"], SS.RETIRADA_RESERVA_SEGURIDAD_V0_1
    )
    fallos = SS.fallos_entorno_lab(erronea)
    assert any("retirada de la v0.1 presentada como vigente" in fallo for fallo in fallos)


def test_negativa_suelo_historico_erroneo_aceptado(doc: dict[str, Any]) -> None:
    erroneo = con_mutacion(doc, ["constantes", "suelo_admision_bytes"], SS.RETIRADO_SUELO_V0_1)
    fallos = SS.fallos_entorno_lab(erroneo)
    assert any("retirado de la v0.1 presentado como vigente" in fallo for fallo in fallos)


def test_negativa_suelo_distinto_de_la_suma(doc: dict[str, Any]) -> None:
    distinto = con_mutacion(doc, ["constantes", "suelo_admision_bytes"], SS.SUELO_ADMISION + 4_096)
    fallos = SS.fallos_entorno_lab(distinto)
    assert any("suelo_admision_bytes" in fallo for fallo in fallos)


def test_negativa_porcentaje_retirado_como_vigente(doc: dict[str, Any]) -> None:
    retirado = con_mutacion(
        doc,
        ["aritmetica_recalculada", "porcentajes_sobre_e_min_historico", "agregado"],
        "27,43",
    )
    fallos = SS.fallos_entorno_lab(retirado)
    assert any("no coincide con la recalculada exacta" in fallo for fallo in fallos)


def test_negativa_valor_ajustado_tras_observar_candidatos(doc: dict[str, Any]) -> None:
    ajustado = con_mutacion(doc, ["constantes", "presupuesto_por_candidato_bytes"], 2_147_483_648)
    fallos = SS.fallos_entorno_lab(ajustado)
    assert any("presupuesto_por_candidato_bytes" in fallo for fallo in fallos)


# ===========================================================================
# Sondas del filesystem · ejecución real y negativas
# ===========================================================================


@pytest.fixture(scope="module")
def sondas_reales(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    base = tmp_path_factory.mktemp("sondas")
    return FP.ejecutar_sondas(base, _REPO_ROOT)


def test_sondas_reales_validas(sondas_reales: dict[str, Any]) -> None:
    assert sondas_reales["resultado"] == "VALIDA"
    assert sondas_reales["mismo_filesystem_que_repositorio"] is True
    assert sondas_reales["limpieza"]["residuo_bytes"] <= SS.RESIDUO_MAXIMO_BYTES
    assert sondas_reales["limpieza"]["valida"] is True


def test_sonda_escritura_densa(sondas_reales: dict[str, Any]) -> None:
    densa = sondas_reales["escritura_densa"]
    assert densa["asignacion_completa"] is True
    assert densa["bloques_asignados_bytes"] >= densa["tamano_escrito_bytes"]
    assert densa["contabilizacion"] == "st_blocks*512"


def test_sonda_sparse_distingue_aparente_de_asignado(sondas_reales: dict[str, Any]) -> None:
    sparse = sondas_reales["fichero_sparse"]
    assert sparse["sparse_soportado"] is True
    assert sparse["bloques_asignados_bytes"] < sparse["tamano_aparente_bytes"]
    assert sparse["tamano_aparente_bytes"] == 64 * _MIB


def test_sonda_reflink_y_cow_del_envolvente(sondas_reales: dict[str, Any]) -> None:
    assert sondas_reales["reflink_ficlone"]["soportado"] is False
    assert sondas_reales["cow"]["observado"] is False
    assert sondas_reales["cow"]["sobrescritura_en_sitio"] is True


def test_sonda_compresion_no_aparente(sondas_reales: dict[str, Any]) -> None:
    compresion = sondas_reales["compresion_o_dedup_aparente"]
    assert compresion["compresion_aparente"] is False
    assert compresion["deduplicacion_aparente"] is False
    assert compresion["observada"] is False


def test_sonda_inodos_y_liberacion(sondas_reales: dict[str, Any]) -> None:
    assert sondas_reales["inodos"]["creacion_observable"] is True
    assert sondas_reales["inodos"]["liberacion_observada"] is True
    liberacion = sondas_reales["liberacion_bloques_tras_borrado"]
    assert liberacion["liberacion_observada"] is True


def test_sonda_ruta_de_error_limpia(sondas_reales: dict[str, Any]) -> None:
    assert sondas_reales["ruta_error"]["limpieza_tras_excepcion"] is True
    assert sondas_reales["ruta_error"]["fichero_residual"] is False


def test_negativa_sondas_dentro_del_repositorio() -> None:
    with pytest.raises(RuntimeError, match="fuera del repositorio"):
        FP._una_pasada(_REPO_ROOT / "artifacts", _REPO_ROOT)


def test_negativa_sondas_en_filesystem_distinto() -> None:
    otro = Path("/dev/shm")
    if not otro.exists() or otro.stat().st_dev == _REPO_ROOT.stat().st_dev:
        pytest.skip("no hay filesystem distinto disponible para la negativa")
    with pytest.raises(RuntimeError, match="filesystems distintos"):
        FP._una_pasada(otro, _REPO_ROOT)


def test_negativa_residuo_superior_al_admisible(tmp_path: Path) -> None:
    disponible, inodos, _ = FP._statvfs_bytes(tmp_path)
    resultado = FP._medir_residuo(tmp_path, disponible + 10 * _MIB, inodos)
    assert resultado["valida"] is False
    assert resultado["residuo_bytes"] > SS.RESIDUO_MAXIMO_BYTES


def test_negativa_sparse_contado_por_st_size(doc: dict[str, Any]) -> None:
    por_tamano = con_mutacion(doc, ["sondas", "fichero_sparse", "contabilizacion"], "st_size")
    fallos = SS.fallos_entorno_lab(por_tamano)
    assert any("sparse contado por st_size" in fallo for fallo in fallos)


@pytest.mark.parametrize("sonda", ["cow", "compresion_o_dedup_aparente"])
def test_negativa_cow_o_compresion_asumidos_sin_sonda(doc: dict[str, Any], sonda: str) -> None:
    sin_sonda = con_mutacion(doc, ["sondas", sonda], _BORRAR)
    fallos = SS.fallos_entorno_lab(sin_sonda)
    assert any(f"sonda obligatoria ausente: {sonda}" in fallo for fallo in fallos)


def test_negativa_limpieza_con_residuo_aceptada(doc: dict[str, Any]) -> None:
    exceso = con_mutacion(doc, ["sondas", "limpieza", "residuo_bytes"], SS.RESIDUO_MAXIMO_BYTES + 1)
    fallos = SS.fallos_entorno_lab(exceso)
    assert any("residuo superior a 65.536 B aceptada" in fallo for fallo in fallos)


def test_negativa_sonda_residual_tras_excepcion(doc: dict[str, Any]) -> None:
    residual = con_mutacion(doc, ["sondas", "ruta_error", "limpieza_tras_excepcion"], False)
    fallos = SS.fallos_entorno_lab(residual)
    assert any("sonda residual tras una excepción" in fallo for fallo in fallos)


# ===========================================================================
# Contabilidad · inventario por inode
# ===========================================================================


def test_inventario_hard_link_contado_una_vez(tmp_path: Path) -> None:
    original = tmp_path / "hl_a.bin"
    original.write_bytes(b"H" * _MIB)
    enlace = tmp_path / "hl_b.bin"
    enlace.hardlink_to(original)
    inventario = SA.inventario_por_inode([original, enlace])
    assert inventario["inodos"] == 1
    assert inventario["bytes_asignados"] < 2 * _MIB
    assert inventario["bytes_asignados"] >= _MIB
    assert inventario["inventario_completo"] is True
    assert inventario["numero_errores"] == 0
    assert inventario["errores_inventario"] == []
    assert inventario["rutas_no_contabilizadas"] == []


def test_inventario_copias_fisicas_contadas_cada_una(tmp_path: Path) -> None:
    a = tmp_path / "copia_a.bin"
    b = tmp_path / "copia_b.bin"
    a.write_bytes(b"C" * _MIB)
    b.write_bytes(b"C" * _MIB)
    inventario = SA.inventario_por_inode([a, b])
    assert inventario["inodos"] == 2
    assert inventario["bytes_asignados"] >= 2 * _MIB


def test_inventario_sparse_por_bloques_no_por_st_size(tmp_path: Path) -> None:
    sparse = tmp_path / "sparse.bin"
    with open(sparse, "wb") as fh:
        fh.truncate(8 * _MIB)
    inventario = SA.inventario_por_inode([sparse])
    assert inventario["bytes_aparentes"] == 8 * _MIB
    assert inventario["bytes_asignados"] < _MIB
    assert inventario["unidad"] == "st_blocks*512"


# ===========================================================================
# Contabilidad · muestreador, doble contabilidad y pico
# ===========================================================================


def test_muestreador_registra_intervalos_reales(tmp_path: Path) -> None:
    muestreador = SA.MuestreadorAlmacenamiento(tmp_path, [tmp_path])
    muestreador.iniciar()
    (tmp_path / "obra.bin").write_bytes(b"O" * (4 * _MIB))
    time.sleep(0.1)
    resumen = muestreador.detener()
    assert resumen["n_muestras"] >= SS.MINIMO_INTERVALOS_OPERACION + 1
    assert resumen["periodo_solicitado_ns"] == SS.PERIODO_MUESTREO_NS
    assert resumen["intervalo_maximo_ns"] >= resumen["intervalo_medio_ns"]
    assert resumen["hilo_finalizado"] is True
    assert resumen["hilo_vivo_tras_timeout"] is False
    assert resumen["error_hilo"] is None
    assert resumen["muestras_con_inventario_incompleto"] == 0
    assert resumen["muestreador_valido"] is True
    tiempos = [m["t_monotonico_ns"] for m in muestreador.muestras]
    assert tiempos == sorted(tiempos)
    pico = max(m["inventario_bytes_asignados"] for m in muestreador.muestras)
    assert pico >= 4 * _MIB


def test_contabilidad_de_operacion_con_checkpoints(tmp_path: Path) -> None:
    """Reconstrucción válida: checkpoints materiales completos y ordenados."""
    atribuible = tmp_path / "candidato"
    atribuible.mkdir()
    contabilidad = SA.ContabilidadOperacion(
        tmp_path, [atribuible], "reconstruccion", duracion_ventana_inactiva_ns=50_000_000
    )
    contabilidad.iniciar()
    viejo = atribuible / "indice_viejo.bin"
    viejo.write_bytes(b"V" * (4 * _MIB))
    contabilidad.checkpoint("despues_de_crear_temporales")
    time.sleep(0.05)
    nuevo = atribuible / "indice_nuevo.bin"
    nuevo.write_bytes(b"N" * (4 * _MIB))
    contabilidad.checkpoint("antes_de_intercambiar_viejo_nuevo")
    time.sleep(0.05)
    cota = SA.cota_determinista_reconstruccion(
        SA.inventario_por_inode([viejo])["bytes_asignados"],
        SA.inventario_por_inode([nuevo])["bytes_asignados"],
    )
    viejo.unlink()
    contabilidad.checkpoint("antes_de_borrar_temporales")
    resultado = contabilidad.cerrar(cotas_deterministas_bytes=[cota])
    assert resultado["tipo_operacion"] == "reconstruccion"
    assert resultado["validez"]["resultado"] == "VALIDO"
    assert resultado["pico"]["resultado"] == "VALIDO"
    assert resultado["pico"]["pico_publicado_bytes"] >= cota
    assert resultado["checkpoints"] == [
        "antes_de_la_operacion",
        "despues_de_crear_temporales",
        "antes_de_intercambiar_viejo_nuevo",
        "antes_de_borrar_temporales",
        "final",
    ]
    assert resultado["doble_contabilidad"]["banda_ruido"]["n_observaciones"] > 0
    assert resultado["doble_contabilidad"]["medida_valida"] is True
    assert resultado["atribuibilidad"]["rutas_atribuibles"] is True
    assert resultado["atribuibilidad"]["inventarios_completos"] is True
    assert resultado["muestreo"]["hilo_finalizado"] is True
    assert resultado["muestreo"]["error_hilo"] is None
    assert resultado["muestreo"]["muestras_con_inventario_incompleto"] == 0


def test_doble_contabilidad_registra_escritura_externa() -> None:
    banda = {"rango_bytes": 4_096, "granularidad_bytes": 4_096}
    dentro = SA.doble_contabilidad(10 * _MIB, 10 * _MIB - 4_096, banda)
    assert dentro["medida_valida"] is True
    fuera = SA.doble_contabilidad(10 * _MIB, 0, banda)
    assert fuera["medida_valida"] is False
    assert fuera["escritura_externa_bytes"] == 10 * _MIB
    assert fuera["diferencia_no_explicada_bytes"] == 10 * _MIB


def test_negativa_operacion_mas_rapida_que_la_observacion() -> None:
    resumen = {
        "intervalos_reales_ns": [5_000_000],
        "intervalo_medio_ns": 5_000_000,
        "intervalo_maximo_ns": 5_000_000,
    }
    validez = SA.evaluar_validez_pico(
        resumen,
        8_000_000,
        ["antes_de_la_operacion", "final"],
        True,
        True,
        tipo_operacion="borrado",
        doble_contabilidad_valida=True,
        inventarios_completos=True,
    )
    assert validez["resultado"] == SS.NO_EVALUABLE
    assert any("tres intervalos reales" in motivo for motivo in validez["motivos"])
    publicado = SA.publicar_pico(12 * _MIB, [], validez)
    assert publicado["resultado"] == SS.NO_EVALUABLE
    assert publicado["pico_publicado_bytes"] is None


def test_negativa_muestreo_solicitado_5ms_intervalos_largos() -> None:
    resumen = {
        "intervalos_reales_ns": [500_000_000] * 4,
        "intervalo_medio_ns": 500_000_000,
        "intervalo_maximo_ns": 500_000_000,
    }
    validez = SA.evaluar_validez_pico(
        resumen,
        100_000_000,
        ["antes_de_la_operacion", "final"],
        True,
        True,
        tipo_operacion="borrado",
        doble_contabilidad_valida=True,
        inventarios_completos=True,
    )
    assert validez["resultado"] == SS.NO_EVALUABLE
    assert any("pausa maxima" in motivo for motivo in validez["motivos"])


def test_negativa_operacion_sin_checkpoints_ni_observacion() -> None:
    resumen = {
        "intervalos_reales_ns": [5_000_000] * 100,
        "intervalo_medio_ns": 5_000_000,
        "intervalo_maximo_ns": 6_000_000,
    }
    validez = SA.evaluar_validez_pico(
        resumen,
        500_000_000,
        [],
        True,
        True,
        tipo_operacion="borrado",
        doble_contabilidad_valida=True,
        inventarios_completos=True,
    )
    assert validez["resultado"] == SS.NO_EVALUABLE
    assert any("sin observacion ni checkpoint" in motivo for motivo in validez["motivos"])
    assert any("checkpoints materiales ausentes" in motivo for motivo in validez["motivos"])


def test_negativa_rutas_no_atribuibles_o_sin_cota() -> None:
    resumen = {
        "intervalos_reales_ns": [5_000_000] * 100,
        "intervalo_medio_ns": 5_000_000,
        "intervalo_maximo_ns": 6_000_000,
    }
    completos = ["antes_de_la_operacion", "final"]
    sin_rutas = SA.evaluar_validez_pico(
        resumen,
        500_000_000,
        completos,
        False,
        True,
        tipo_operacion="borrado",
        doble_contabilidad_valida=True,
        inventarios_completos=True,
    )
    assert sin_rutas["resultado"] == SS.NO_EVALUABLE
    assert any("rutas no atribuibles" in motivo for motivo in sin_rutas["motivos"])
    sin_cota = SA.evaluar_validez_pico(
        resumen,
        500_000_000,
        completos,
        True,
        False,
        tipo_operacion="borrado",
        doble_contabilidad_valida=True,
        inventarios_completos=True,
    )
    assert sin_cota["resultado"] == SS.NO_EVALUABLE
    assert any("cota determinista" in motivo for motivo in sin_cota["motivos"])


def test_negativa_viejo_mas_nuevo_no_sumados() -> None:
    validez = {"resultado": "VALIDO", "motivos": []}
    cota = SA.cota_determinista_reconstruccion(6 * _MIB, 6 * _MIB)
    assert cota == 12 * _MIB
    publicado = SA.publicar_pico(7 * _MIB, [cota], validez)
    assert publicado["pico_publicado_bytes"] == 12 * _MIB
    assert publicado["fuente"] == "cota_determinista"


def test_pico_nunca_sustituye_un_maximo_por_una_muestra_inferior() -> None:
    validez = {"resultado": "VALIDO", "motivos": []}
    publicado = SA.publicar_pico(20 * _MIB, [12 * _MIB], validez)
    assert publicado["pico_publicado_bytes"] == 20 * _MIB
    assert publicado["fuente"] == "muestreo"


# ===========================================================================
# Checkpoints materiales por tipo de operación · anexo §3
# ===========================================================================


def test_checkpoints_materiales_derivados_del_anexo() -> None:
    assert set(SA.CHECKPOINTS_MATERIALES_POR_TIPO) == set(SA.TIPOS_OPERACION)
    for tipo, requeridos in SA.CHECKPOINTS_MATERIALES_POR_TIPO.items():
        assert requeridos[0] == "antes_de_la_operacion"
        assert requeridos[-1] == "final"
        assert all(c in SA.CHECKPOINTS_CANONICOS for c in requeridos)
        assert SA.fallos_checkpoints_materiales(tipo, list(requeridos)) == []


def test_negativa_lista_no_vacia_no_basta_como_checkpoints() -> None:
    fallos = SA.fallos_checkpoints_materiales("reconstruccion", ["antes_de_la_operacion", "final"])
    assert any("checkpoints materiales ausentes" in fallo for fallo in fallos)


def test_negativa_checkpoints_en_orden_incompatible() -> None:
    fallos = SA.fallos_checkpoints_materiales(
        "reconstruccion",
        [
            "antes_de_la_operacion",
            "antes_de_intercambiar_viejo_nuevo",
            "despues_de_crear_temporales",
            "antes_de_borrar_temporales",
            "final",
        ],
    )
    assert any("orden incompatible" in fallo for fallo in fallos)


def test_negativa_tipo_de_operacion_no_contemplado() -> None:
    fallos = SA.fallos_checkpoints_materiales("compactacion", ["antes_de_la_operacion", "final"])
    assert fallos == ["tipo de operacion no contemplado: 'compactacion'"]


def test_negativa_cero_intervalos_observados_es_no_evaluable() -> None:
    """Regresión: cero intervalos reales nunca es resolución válida (§5.1)."""
    resumen = {
        "n_muestras": 1,
        "intervalos_reales_ns": [],
        "intervalo_medio_ns": 0,
        "intervalo_maximo_ns": 0,
        "hilo_finalizado": True,
        "hilo_vivo_tras_timeout": False,
        "error_hilo": None,
        "muestras_con_inventario_incompleto": 0,
    }
    validez = SA.evaluar_validez_pico(
        resumen,
        2_000_000,
        ["antes_de_la_operacion", "final"],
        True,
        True,
        tipo_operacion="borrado",
        doble_contabilidad_valida=True,
        inventarios_completos=True,
    )
    assert validez["resultado"] == SS.NO_EVALUABLE
    assert any("tres intervalos reales" in motivo for motivo in validez["motivos"])
    publicado = SA.publicar_pico(4096, [8192], validez)
    assert publicado["resultado"] == SS.NO_EVALUABLE
    assert publicado["pico_publicado_bytes"] is None
    assert publicado["cota_determinista_bytes"] == 8192  # único dato utilizable


def test_inventario_decide_el_descenso_con_el_lstat_ya_obtenido(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regresión: sin segunda stat (is_dir/is_symlink) que trague OSError."""
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "oculto.bin").write_bytes(b"O" * _MIB)

    def segunda_stat_prohibida(self: Path) -> bool:
        raise AssertionError("is_dir/is_symlink no deben consultarse: segunda stat")

    monkeypatch.setattr(Path, "is_dir", segunda_stat_prohibida)
    monkeypatch.setattr(Path, "is_symlink", segunda_stat_prohibida)
    inventario = SA.inventario_por_inode([tmp_path])
    assert inventario["inventario_completo"] is True
    assert inventario["numero_errores"] == 0
    assert inventario["inodos"] == 3
    assert inventario["bytes_asignados"] >= _MIB


def test_negativa_tipo_de_operacion_no_declarado() -> None:
    resumen = {
        "intervalos_reales_ns": [5_000_000] * 100,
        "intervalo_medio_ns": 5_000_000,
        "intervalo_maximo_ns": 6_000_000,
    }
    validez = SA.evaluar_validez_pico(
        resumen,
        500_000_000,
        ["antes_de_la_operacion", "final"],
        True,
        True,
        doble_contabilidad_valida=True,
        inventarios_completos=True,
    )
    assert validez["resultado"] == SS.NO_EVALUABLE
    assert any("tipo de operacion no declarado" in motivo for motivo in validez["motivos"])


# ===========================================================================
# Orquestador · pruebas adversariales de B-1 (fail-closed extremo a extremo)
# ===========================================================================


def _operacion_en(
    tmp_path: Path, tipo_operacion: str, **kwargs: Any
) -> tuple[SA.ContabilidadOperacion, Path]:
    atribuible = tmp_path / "candidato"
    atribuible.mkdir()
    contabilidad = SA.ContabilidadOperacion(
        tmp_path,
        [atribuible],
        tipo_operacion,
        duracion_ventana_inactiva_ns=50_000_000,
        **kwargs,
    )
    return contabilidad, atribuible


def _sin_pico_valido(resultado: dict[str, Any]) -> None:
    assert resultado["validez"]["resultado"] == SS.NO_EVALUABLE
    assert resultado["pico"]["resultado"] == SS.NO_EVALUABLE
    assert resultado["pico"]["pico_publicado_bytes"] is None


def test_negativa_orquestador_escritura_externa_invalida_el_pico(tmp_path: Path) -> None:
    """B-1: la invalidez de la doble contabilidad invalida el veredicto y el pico."""
    contabilidad, _atribuible = _operacion_en(tmp_path, "borrado")
    externo = tmp_path / "externo"
    externo.mkdir()
    contabilidad.iniciar()
    with open(externo / "externo.bin", "wb") as fh:
        fh.write(b"X" * (64 * _MIB))
        fh.flush()
        os.fsync(fh.fileno())
    time.sleep(0.05)
    resultado = contabilidad.cerrar(cotas_deterministas_bytes=[_MIB])
    assert resultado["doble_contabilidad"]["medida_valida"] is False
    assert resultado["doble_contabilidad"]["escritura_externa_bytes"] >= 60 * _MIB
    _sin_pico_valido(resultado)
    assert any("doble contabilidad invalida" in m for m in resultado["validez"]["motivos"])
    assert resultado["pico"]["cota_determinista_bytes"] == _MIB  # solo diagnóstico
    assert resultado["atribuibilidad"]["rutas_atribuibles"] is False


def test_negativa_orquestador_checkpoints_insuficientes(tmp_path: Path) -> None:
    """Reconstrucción con temporal efímero y solo inicio/final: NO_EVALUABLE."""
    contabilidad, atribuible = _operacion_en(tmp_path, "reconstruccion")
    contabilidad.iniciar()
    temporal = atribuible / "temporal.bin"
    with open(temporal, "wb") as fh:
        fh.write(b"T" * (8 * _MIB))
        fh.flush()
        os.fsync(fh.fileno())
    temporal.unlink()
    time.sleep(0.05)
    resultado = contabilidad.cerrar(cotas_deterministas_bytes=[1024])
    assert resultado["checkpoints"] == ["antes_de_la_operacion", "final"]
    _sin_pico_valido(resultado)
    assert any("checkpoints materiales ausentes" in m for m in resultado["validez"]["motivos"])


def test_negativa_orquestador_checkpoint_arbitrario(tmp_path: Path) -> None:
    contabilidad, _atribuible = _operacion_en(tmp_path, "borrado")
    contabilidad.iniciar()
    contabilidad.checkpoint("checkpoint_inventado")
    time.sleep(0.06)
    resultado = contabilidad.cerrar(cotas_deterministas_bytes=[4096])
    _sin_pico_valido(resultado)
    assert any("vocabulario canonico" in m for m in resultado["validez"]["motivos"])


def test_inventario_fail_closed_fichero_desaparecido(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "estable.bin").write_bytes(b"E" * _MIB)
    (tmp_path / "volatil.bin").write_bytes(b"V" * _MIB)
    lstat_original = Path.lstat

    def lstat_con_carrera(self: Path) -> os.stat_result:
        if self.name == "volatil.bin":
            raise FileNotFoundError(2, "desaparecido durante el recorrido", str(self))
        return lstat_original(self)

    monkeypatch.setattr(Path, "lstat", lstat_con_carrera)
    inventario = SA.inventario_por_inode([tmp_path])
    assert inventario["inventario_completo"] is False
    assert inventario["numero_errores"] == 1
    assert inventario["errores_inventario"][0]["tipo"] == "FileNotFoundError"
    assert any(r.endswith("volatil.bin") for r in inventario["rutas_no_contabilizadas"])
    assert inventario["bytes_asignados"] >= _MIB  # el parcial queda solo como diagnóstico


def test_negativa_orquestador_inventario_fichero_desaparecido(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contabilidad, atribuible = _operacion_en(tmp_path, "borrado")
    (atribuible / "fantasma.bin").write_bytes(b"F" * _MIB)
    lstat_original = Path.lstat

    def lstat_con_carrera(self: Path) -> os.stat_result:
        if self.name == "fantasma.bin":
            raise FileNotFoundError(2, "desaparecido durante el recorrido", str(self))
        return lstat_original(self)

    monkeypatch.setattr(Path, "lstat", lstat_con_carrera)
    contabilidad.iniciar()
    time.sleep(0.06)
    resultado = contabilidad.cerrar(cotas_deterministas_bytes=[4096])
    _sin_pico_valido(resultado)
    assert resultado["atribuibilidad"]["inventarios_completos"] is False
    assert resultado["atribuibilidad"]["errores_inventario_checkpoints"] >= 2
    assert resultado["atribuibilidad"]["rutas_atribuibles"] is False
    assert any("inventario" in m for m in resultado["validez"]["motivos"])


def test_negativa_orquestador_directorio_inaccesible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OSError determinista vía monkeypatch: no depende de permisos Unix reales."""
    contabilidad, atribuible = _operacion_en(tmp_path, "borrado")
    opaco = atribuible / "opaco"
    opaco.mkdir()
    (opaco / "oculto.bin").write_bytes(b"O" * _MIB)
    iterdir_original = Path.iterdir

    def iterdir_denegado(self: Path) -> Any:
        if self.name == "opaco":
            raise PermissionError(13, "acceso denegado simulado", str(self))
        return iterdir_original(self)

    monkeypatch.setattr(Path, "iterdir", iterdir_denegado)
    contabilidad.iniciar()
    time.sleep(0.06)
    resultado = contabilidad.cerrar(cotas_deterministas_bytes=[4096])
    _sin_pico_valido(resultado)
    assert resultado["atribuibilidad"]["inventarios_completos"] is False
    assert any("inventario" in m for m in resultado["validez"]["motivos"])


def test_negativa_orquestador_excepcion_en_hilo_del_muestreador(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contabilidad, _atribuible = _operacion_en(tmp_path, "borrado")
    muestra_original = contabilidad._muestreador._muestra
    llamadas = {"n": 0}

    def muestra_explosiva() -> dict[str, Any]:
        llamadas["n"] += 1
        if llamadas["n"] >= 2:
            raise RuntimeError("fallo inyectado en el hilo del muestreador")
        return muestra_original()

    monkeypatch.setattr(contabilidad._muestreador, "_muestra", muestra_explosiva)
    contabilidad.iniciar()
    time.sleep(0.06)
    resultado = contabilidad.cerrar(cotas_deterministas_bytes=[4096])
    assert resultado["muestreo"]["error_hilo"] == {
        "tipo": "RuntimeError",
        "mensaje": "fallo inyectado en el hilo del muestreador",
        "origen": "hilo",
    }
    assert resultado["muestreo"]["hilo_finalizado"] is True
    assert resultado["muestreo"]["muestreador_valido"] is False
    _sin_pico_valido(resultado)
    assert any("excepcion en el hilo" in m for m in resultado["validez"]["motivos"])


def test_negativa_orquestador_hilo_vivo_tras_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contabilidad, _atribuible = _operacion_en(tmp_path, "borrado", timeout_join_s=0.2)
    bloqueo = threading.Event()
    muestra_original = contabilidad._muestreador._muestra

    def muestra_bloqueada() -> dict[str, Any]:
        if threading.current_thread().name == "muestreador-tol207" and not bloqueo.is_set():
            bloqueo.wait(5)  # bloqueo acotado: el hilo nunca queda residual
        return muestra_original()

    monkeypatch.setattr(contabilidad._muestreador, "_muestra", muestra_bloqueada)
    contabilidad.iniciar()
    time.sleep(0.05)
    resultado = contabilidad.cerrar(cotas_deterministas_bytes=[4096])
    assert resultado["muestreo"]["hilo_vivo_tras_timeout"] is True
    assert resultado["muestreo"]["hilo_finalizado"] is False
    _sin_pico_valido(resultado)
    assert any("vivo tras el timeout" in m for m in resultado["validez"]["motivos"])
    bloqueo.set()
    contabilidad._muestreador._hilo.join(timeout=5)
    assert contabilidad._muestreador._hilo.is_alive() is False


def test_negativa_orquestador_muestra_con_inventario_incompleto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contabilidad, _atribuible = _operacion_en(tmp_path, "borrado")
    muestra_original = contabilidad._muestreador._muestra

    def muestra_incompleta() -> dict[str, Any]:
        muestra = muestra_original()
        if threading.current_thread().name == "muestreador-tol207":
            muestra["inventario_completo"] = False
            muestra["inventario_numero_errores"] = 1
        return muestra

    monkeypatch.setattr(contabilidad._muestreador, "_muestra", muestra_incompleta)
    contabilidad.iniciar()
    time.sleep(0.06)
    resultado = contabilidad.cerrar(cotas_deterministas_bytes=[4096])
    assert resultado["muestreo"]["muestras_con_inventario_incompleto"] >= 1
    _sin_pico_valido(resultado)
    assert any("muestras del muestreador" in m for m in resultado["validez"]["motivos"])
    assert resultado["atribuibilidad"]["inventarios_completos"] is False


def test_negativa_orquestador_wal_abierto_y_desvinculado(tmp_path: Path) -> None:
    """El pathname desaparece pero los bloques siguen asignados: doble contabilidad."""
    contabilidad, atribuible = _operacion_en(tmp_path, "borrado")
    contabilidad.iniciar()
    wal = atribuible / "indice-wal"
    fd = os.open(wal, os.O_CREAT | os.O_WRONLY)
    try:
        os.write(fd, b"W" * (16 * _MIB))
        os.fsync(fd)
        time.sleep(0.05)
        wal.unlink()  # abierto y desvinculado: invisible para el inventario
        time.sleep(0.05)
        resultado = contabilidad.cerrar(cotas_deterministas_bytes=[1024])
    finally:
        os.close(fd)
    assert resultado["doble_contabilidad"]["medida_valida"] is False
    assert resultado["doble_contabilidad"]["escritura_externa_bytes"] >= 15 * _MIB
    _sin_pico_valido(resultado)
    assert any("doble contabilidad invalida" in m for m in resultado["validez"]["motivos"])


def test_orquestador_vacuum_valido_publica_el_mayor_valor(tmp_path: Path) -> None:
    atribuible = tmp_path / "candidato"
    atribuible.mkdir()
    original = atribuible / "base.db"
    original.write_bytes(b"B" * (4 * _MIB))
    contabilidad = SA.ContabilidadOperacion(
        tmp_path, [atribuible], "vacuum", duracion_ventana_inactiva_ns=50_000_000
    )
    contabilidad.iniciar()
    time.sleep(0.05)
    contabilidad.checkpoint("antes_de_vacuum")
    copia = atribuible / "base.db-vacuum"
    copia.write_bytes(b"C" * (4 * _MIB))
    time.sleep(0.05)
    cota = SA.cota_determinista_reconstruccion(
        SA.inventario_por_inode([original])["bytes_asignados"],
        SA.inventario_por_inode([copia])["bytes_asignados"],
    )
    resultado = contabilidad.cerrar(cotas_deterministas_bytes=[cota])
    assert resultado["checkpoints"] == ["antes_de_la_operacion", "antes_de_vacuum", "final"]
    assert resultado["validez"]["resultado"] == "VALIDO"
    assert resultado["pico"]["resultado"] == "VALIDO"
    pico_muestreado = resultado["pico"]["pico_muestreado_bytes"]
    assert resultado["pico"]["pico_publicado_bytes"] == max(cota, pico_muestreado)
    assert resultado["pico"]["pico_publicado_bytes"] >= cota
    assert resultado["doble_contabilidad"]["medida_valida"] is True


# ===========================================================================
# Declaración de candidato · partidas atribuibles
# ===========================================================================


def _declaracion_completa() -> dict[str, Any]:
    return {
        "unidad": "st_blocks*512",
        "hard_links_deduplicados": True,
        "fases_maximo_simultaneo": list(SS.FASES_MAXIMO_SIMULTANEO),
        "partidas": {p: 0 for p in SS.PARTIDAS_OBLIGATORIAS_CANDIDATO},
    }


def test_declaracion_de_candidato_completa_sin_fallos() -> None:
    assert SA.fallos_declaracion_candidato(_declaracion_completa()) == []


@pytest.mark.parametrize(
    "partida",
    [
        "wal",
        "shm",
        "journal",
        "temporales",
        "copia_vacuum",
        "indice_viejo_y_nuevo_coexistentes",
        "spills",
    ],
)
def test_negativa_partida_atribuible_omitida(partida: str) -> None:
    declaracion = _declaracion_completa()
    del declaracion["partidas"][partida]
    fallos = SA.fallos_declaracion_candidato(declaracion)
    assert any(f"partida atribuible omitida: {partida}" in fallo for fallo in fallos)


def test_negativa_modelo_compartido_cargado_a_un_candidato() -> None:
    declaracion = _declaracion_completa()
    declaracion["partidas"]["modelos_locales_compartidos"] = 700 * _MIB
    fallos = SA.fallos_declaracion_candidato(declaracion)
    assert any("reserva operativa" in fallo for fallo in fallos)


def test_negativa_hard_link_contado_dos_veces_en_declaracion() -> None:
    declaracion = _declaracion_completa()
    declaracion["hard_links_deduplicados"] = False
    fallos = SA.fallos_declaracion_candidato(declaracion)
    assert any("hard links" in fallo for fallo in fallos)


def test_negativa_declaracion_sin_st_blocks() -> None:
    declaracion = _declaracion_completa()
    declaracion["unidad"] = "st_size"
    fallos = SA.fallos_declaracion_candidato(declaracion)
    assert any("st_blocks*512" in fallo for fallo in fallos)


# ===========================================================================
# Reserva operativa · negativas de cobertura y presupuesto
# ===========================================================================


def _con_partida_ajustada(doc: dict[str, Any], nombre: str, **cambios: Any) -> dict[str, Any]:
    mutado = copy.deepcopy(doc)
    desglose = mutado["reserva_operativa_desglose"]
    for partida in desglose["partidas"]:
        if partida["partida"] == nombre:
            partida.update(cambios)
    suma = sum(
        p["asignacion_maxima_bytes"]
        for p in desglose["partidas"]
        if p.get("suma_excluida") is not True
    )
    desglose["suma_asignaciones_maximas_bytes"] = suma
    desglose["margen_restante_bytes"] = SS.RESERVA_OPERATIVA - suma
    desglose["cabe_en_presupuesto"] = suma <= SS.RESERVA_OPERATIVA
    return mutado


def test_negativa_reserva_operativa_superior_a_6_gib(doc: dict[str, Any]) -> None:
    inflado = _con_partida_ajustada(
        doc, "modelos_locales_compartidos", asignacion_maxima_bytes=2 * SS.PRESUPUESTO_AGREGADO
    )
    inflado["reserva_operativa_desglose"]["cabe_en_presupuesto"] = True
    fallos = SS.fallos_entorno_lab(inflado)
    assert any("superior a 6 GiB aceptada" in fallo for fallo in fallos)


def test_negativa_modelo_compartido_fuera_de_la_reserva_operativa(
    doc: dict[str, Any],
) -> None:
    mutado = copy.deepcopy(doc)
    desglose = mutado["reserva_operativa_desglose"]
    desglose["partidas"] = [
        p for p in desglose["partidas"] if p["partida"] != "modelos_locales_compartidos"
    ]
    suma = sum(
        p["asignacion_maxima_bytes"]
        for p in desglose["partidas"]
        if p.get("suma_excluida") is not True
    )
    desglose["suma_asignaciones_maximas_bytes"] = suma
    desglose["margen_restante_bytes"] = SS.RESERVA_OPERATIVA - suma
    fallos = SS.fallos_entorno_lab(mutado)
    assert any("modelos_locales_compartidos" in fallo for fallo in fallos)


def test_negativa_logs_fuera_de_toda_reserva(doc: dict[str, Any]) -> None:
    mutado = _con_partida_ajustada(
        doc,
        "artefactos_informes_logs_resultados",
        cubre=["artefactos", "informes", "resultados"],
    )
    fallos = SS.fallos_entorno_lab(mutado)
    assert any("logs" in fallo for fallo in fallos)


def test_negativa_asignacion_presentada_como_medida(doc: dict[str, Any]) -> None:
    mutado = _con_partida_ajustada(doc, "copias_limpias_ciclo", tipo=SS.ETIQUETA_MEDIDO)
    fallos = SS.fallos_entorno_lab(mutado)
    assert any("presentada como medida sin bytes medidos" in fallo for fallo in fallos)


# ===========================================================================
# Denominador y escalas · negativas
# ===========================================================================


def test_negativa_denominador_distinto_de_5670(doc: dict[str, Any]) -> None:
    distinto = con_mutacion(doc, ["denominador", "unidades_logicas_primarias"], 5_671)
    fallos = SS.fallos_entorno_lab(distinto)
    assert any("denominador distinto de 5.670" in fallo for fallo in fallos)


def test_negativa_relaciones_o_entidades_en_el_denominador(doc: dict[str, Any]) -> None:
    con_relaciones = copy.deepcopy(doc)
    con_relaciones["denominador"]["desglose"]["relaciones"] = 180
    fallos = SS.fallos_entorno_lab(con_relaciones)
    assert any("carga estructural incorporada al denominador" in fallo for fallo in fallos)


def test_negativa_extrapolacion_a_50000_presentada_como_medicion(
    doc: dict[str, Any],
) -> None:
    medida = con_mutacion(doc, ["escalas", "proyeccion", "etiqueta"], SS.ETIQUETA_MEDIDO)
    fallos = SS.fallos_entorno_lab(medida)
    assert any("presentada como medición" in fallo for fallo in fallos)


# ===========================================================================
# Estado de las puertas y cierre
# ===========================================================================


def test_matriz_de_aceptacion_fija_de_16(doc: dict[str, Any]) -> None:
    condiciones = doc["matriz_aceptacion"]["condiciones_bloqueantes"]
    assert [c["id"] for c in condiciones] == list(range(1, 17))
    assert condiciones == [dict(c) for c in SS.MATRIZ_ACEPTACION]


def test_negativa_tol207_declarada_satisfecha(doc: dict[str, Any]) -> None:
    satisfecha = con_mutacion(doc, ["estado_puertas", "ADR002-TOL-207"], "SATISFECHA")
    fallos = SS.fallos_entorno_lab(satisfecha)
    assert any("NO SATISFECHA" in fallo for fallo in fallos)
    aprobada = con_mutacion(doc, ["estado_puertas", "ADR002-TOL-207"], "NO SATISFECHA APROBADA")
    assert any("aprobada" in fallo for fallo in SS.fallos_entorno_lab(aprobada))


def test_documento_sin_claves_sensibles(doc: dict[str, Any]) -> None:
    fallos: list[str] = []
    SS._fallos_secretos(doc, fallos)
    assert fallos == []
