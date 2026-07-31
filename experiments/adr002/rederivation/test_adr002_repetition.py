"""Pruebas de la repeticion unica controlada del §6.8 (evidencia v0.2).

Ninguna prueba cronometra operaciones de T0. Comprueban las reglas del
arnes de repeticion: una sola corrida sin puerta de reintento, condiciones
controladas congeladas, evidencia v0.1 intangible, estado final del §6.9
fijado antes de medir, y operacion medida identica a la de la v0.1.
"""

from __future__ import annotations

import json
from pathlib import Path

from experiments.adr002.rederivation import controlled_conditions as cc
from experiments.adr002.rederivation import execute_rederivation as arnes
from experiments.adr002.rederivation import execute_repetition as repeticion
from experiments.adr002.rederivation import rederivation_protocol as rp
from experiments.adr002.rederivation import schema_rederivation_v0_1 as esquema
from experiments.adr002.rederivation import test_adr002_execute_rederivation as base

RAIZ = Path(__file__).resolve().parents[3]


# --------------------------------------------------------------------------
# El estado final del §6.9, congelado antes de observar nada
# --------------------------------------------------------------------------


def test_una_magnitud_que_pasa_es_valida() -> None:
    assert cc.estado_final_6_9("VALIDA") == cc.ESTADO_FINAL_VALIDA


def test_una_magnitud_que_no_pasa_queda_no_evaluable() -> None:
    """INVALIDA no es publicable como estado definitivo tras consumir §6.8."""
    assert cc.estado_final_6_9("INVALIDA") == cc.ESTADO_FINAL_NO_EVALUABLE
    assert cc.estado_final_6_9("NO_EVALUABLE") == cc.ESTADO_FINAL_NO_EVALUABLE
    assert cc.estado_final_6_9("NO_COMPARABLE") == cc.ESTADO_FINAL_NO_EVALUABLE
    assert cc.estado_final_6_9("cualquier otra cosa") == cc.ESTADO_FINAL_NO_EVALUABLE


# --------------------------------------------------------------------------
# Condiciones controladas congeladas
# --------------------------------------------------------------------------


def test_las_condiciones_estan_congeladas() -> None:
    assert cc.UMBRAL_CARGA_1M == 0.35
    assert cc.PLAZO_ASENTAMIENTO_PREVIO_S == 600
    assert cc.PLAZO_ASENTAMIENTO_ENTRE_SESIONES_S == 120
    assert cc.BOOT_ID_V01 == "fd0d2268-0abc-4037-8b2a-c0a91dade2ef"


def test_el_asentamiento_termina_al_caer_la_carga() -> None:
    cargas = iter([0.9, 0.6, 0.2])
    dormidas: list[float] = []
    espera = cc.esperar_asentamiento(
        "prueba",
        plazo_s=600,
        leer_carga=lambda: next(cargas),
        dormir=dormidas.append,
        reloj=iter(range(0, 1000, 5)).__next__,
    )
    assert espera.alcanzado
    assert espera.serie == (0.9, 0.6, 0.2)
    assert dormidas == [cc.MUESTREO_S, cc.MUESTREO_S]


def test_el_asentamiento_vence_por_plazo_sin_bucle_infinito() -> None:
    espera = cc.esperar_asentamiento(
        "prueba",
        plazo_s=10,
        leer_carga=lambda: 9.9,
        dormir=lambda _s: None,
        reloj=iter(range(0, 1000, 6)).__next__,
    )
    assert not espera.alcanzado
    assert espera.serie[-1] == 9.9


def test_una_espera_no_alcanzada_entre_sesiones_no_aborta() -> None:
    """La regla esta en el ejecutor: incidencia registrada, corrida sigue."""
    fuente = (RAIZ / "experiments/adr002/rederivation/execute_repetition.py").read_text("utf-8")
    assert "la corrida continua y la incidencia queda registrada" in fuente


def test_el_registro_documenta_el_arranque_sin_fingir_continuidad() -> None:
    registro = cc.RegistroCondiciones()
    registro.boot_id_inicio = "otro-arranque"
    registro.boot_id_final = "otro-arranque"
    datos = registro.como_dict()
    assert datos["boot_id_v01"] == cc.BOOT_ID_V01
    assert datos["arranque_estable_durante_la_corrida"] is True
    assert datos["mismo_arranque_que_v01"] is False


def test_un_cambio_de_arranque_a_mitad_no_es_estable() -> None:
    registro = cc.RegistroCondiciones()
    registro.boot_id_inicio = "a"
    registro.boot_id_final = "b"
    assert not registro.arranque_estable


# --------------------------------------------------------------------------
# La evidencia v0.1, intangible
# --------------------------------------------------------------------------


def _entorno(*, alterados: tuple[str, ...] = ()) -> rp.EntornoCustodia:
    def leer(ruta: str) -> bytes:
        if ruta in alterados:
            return b"alterado"
        return (RAIZ / ruta).read_bytes()

    from experiments.adr002.cards import card_protocol as cp

    return cp.EntornoCustodia(
        leer_bytes=leer,
        es_ancestro=lambda a, b: True,
        existe_commit=lambda sha: True,
        head=lambda: "a" * 40,
        arbol_limpio=lambda: True,
        diff_vacio=lambda desde, hasta, rutas: True,
        blob_en_commit=lambda sha, ruta: None,
    )


def test_la_evidencia_v01_intacta_no_falla() -> None:
    assert cc.fallos_de_evidencia_v01(_entorno()) == ()


def test_la_evidencia_v01_alterada_bloquea() -> None:
    ruta = next(iter(cc.EVIDENCIA_V01))
    fallos = cc.fallos_de_evidencia_v01(_entorno(alterados=(ruta,)))
    assert fallos
    assert "alterada" in fallos[0]


def test_sin_acta_de_repeticion_se_bloquea() -> None:
    def leer(ruta: str) -> bytes:
        if ruta.endswith(cc.ACTA_REPETICION):
            raise OSError(ruta)
        return (RAIZ / ruta).read_bytes()

    from experiments.adr002.cards import card_protocol as cp

    entorno = cp.EntornoCustodia(
        leer_bytes=leer,
        es_ancestro=lambda a, b: True,
        existe_commit=lambda sha: True,
        head=lambda: "a" * 40,
        arbol_limpio=lambda: True,
        diff_vacio=lambda desde, hasta, rutas: True,
        blob_en_commit=lambda sha, ruta: None,
    )
    fallos = cc.fallos_de_acta_de_repeticion(entorno)
    assert fallos
    assert cc.ACTA_REPETICION in fallos[0]
    assert cc.fallos_de_acta_de_repeticion(_entorno()) == ()


def test_el_acta_de_repeticion_existe_en_el_repositorio() -> None:
    assert (RAIZ / "docs/architecture" / cc.ACTA_REPETICION).is_file()


# --------------------------------------------------------------------------
# Una corrida y ninguna mas; la operacion medida no cambia
# --------------------------------------------------------------------------


def test_no_existe_bucle_de_reintento() -> None:
    """El arnes v0.1 tenia la repeticion interna del §6.8; este NO."""
    fuente = (RAIZ / "experiments/adr002/rederivation/execute_repetition.py").read_text("utf-8")
    assert "REPETICIONES_DE_CORRIDA_MAXIMAS" not in fuente
    assert "for intento" not in fuente


def test_el_worker_es_el_congelado_de_la_v01() -> None:
    """La orden del hijo invoca el modulo congelado: mismo trabajo medido."""
    fuente = (RAIZ / "experiments/adr002/rederivation/execute_repetition.py").read_text("utf-8")
    assert '"experiments.adr002.rederivation.execute_rederivation"' in fuente
    assert '"--worker"' in fuente
    assert "def medir_sesion" not in fuente  # no redefine la operacion medida
    assert "perf_counter" not in fuente
    assert "medir_ns" not in fuente  # no cronometra nada por si mismo


def test_las_condiciones_no_cronometran_operaciones_de_t0() -> None:
    fuente = (RAIZ / "experiments/adr002/rederivation/controlled_conditions.py").read_text("utf-8")
    for prohibido in ("perf_counter", "sqlite3", "medir_ns", "search_knowledge"):
        assert prohibido not in fuente


def test_sin_execute_no_hace_nada() -> None:
    assert repeticion.main([]) == repeticion.CODIGO_SIN_EXECUTE


def test_el_parser_no_ofrece_ninguna_otra_puerta() -> None:
    acciones = {a.dest for a in repeticion.construir_parser()._actions}
    assert acciones == {"help", "execute"}


# --------------------------------------------------------------------------
# El artefacto v0.2: mismo contrato congelado, estados del §6.9 aparte
# --------------------------------------------------------------------------


def test_el_documento_v02_valida_contra_el_esquema_congelado() -> None:
    perfil = arnes.perfil_aprobado(RAIZ)
    magnitudes = arnes.magnitudes_rederivadas(base._corrida_sintetica(), perfil=perfil)
    controles = dict.fromkeys(rp.CONTROLES_BLOQUEANTES, True)
    documento = repeticion.documento_v02(magnitudes, controles)
    assert documento["documento"] == repeticion.DOCUMENTO_V02
    assert esquema.fallos_rederivacion(documento, perfil=perfil) == []


def test_las_muestras_v02_llevan_condiciones_y_estado_final() -> None:
    perfil = arnes.perfil_aprobado(RAIZ)
    corrida = base._corrida_sintetica()
    magnitudes = arnes.magnitudes_rederivadas(corrida, perfil=perfil)
    consultas = repeticion.fc.derivar_consultas(base._corpus_sintetico())
    registro = cc.RegistroCondiciones()
    registro.boot_id_inicio = registro.boot_id_final = "boot-v02"
    conteos = repeticion.fc.ConteosCargados(
        proyectos=2,
        mensajes=3,
        memorias=2,
        memorias_vigentes=1,
        decisiones=1,
        filas_fts=3,
        no_cargados={"entidades": 0, "documentos": 0, "relaciones": 0},
    )
    documento = repeticion.muestras_v02(
        head="f" * 40,
        consultas=consultas,
        conteos=conteos,
        resultados=corrida,
        magnitudes=magnitudes,
        registro=registro,
    )
    assert documento["artefacto_normativo"] == repeticion.SALIDA_V02
    assert documento["acta_de_repeticion"] == cc.ACTA_REPETICION
    assert documento["repeticion_unica_6_8_ejercitada"] is True
    finales = documento["estado_final_6_9_por_magnitud"]
    assert sorted(finales) == sorted(rp.magnitudes_previstas())
    for magnitud in magnitudes:
        assert finales[magnitud["magnitud"]] == cc.estado_final_6_9(str(magnitud["resultado"]))
    condiciones = documento["condiciones_controladas"]
    assert condiciones["boot_id_v01"] == cc.BOOT_ID_V01
    assert condiciones["mismo_arranque_que_v01"] is False
    assert json.dumps(documento)


def test_las_salidas_v02_solo_existen_ejecutadas_y_validan() -> None:
    """Tres estados legales, fallando cerrado en cualquier otro."""
    artefacto = RAIZ / repeticion.SALIDA_V02
    muestras = RAIZ / repeticion.SALIDA_MUESTRAS_V02
    if not artefacto.exists():
        assert not muestras.exists(), "muestras v0.2 sin artefacto v0.2"
        return  # autorizada pero aun no ejecutada
    assert muestras.exists(), "artefacto v0.2 sin sus muestras"
    perfil = arnes.perfil_aprobado(RAIZ)
    documento = json.loads(artefacto.read_text(encoding="utf-8"))
    assert esquema.fallos_rederivacion(documento, perfil=perfil) == []
    # Y la evidencia v0.1 sigue intacta byte a byte.
    assert cc.fallos_de_evidencia_v01(_entorno()) == ()
