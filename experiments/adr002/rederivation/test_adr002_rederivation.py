"""Pruebas de la rederivacion de T0 (ADR002-TOL-208, paquete 10).

**No ejecutan T0 y no miden nada.** Comprueban que la guarda de autorizacion
bloquea, que las precondiciones fallan cerrado y que el esquema del artefacto
—congelado antes de que exista la medicion— hace cumplir lo preinscrito.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from experiments.adr002.cards import card_protocol as cp
from experiments.adr002.rederivation import rederivation_protocol as rp
from experiments.adr002.rederivation import run_rederivation as recorrido
from experiments.adr002.rederivation import schema_rederivation_v0_1 as esquema
from experiments.adr002.tolerances import envelope_protocol as ep
from experiments.adr002.tolerances import profile_protocol as pp

RAIZ = Path(__file__).resolve().parents[3]
SHA = "a" * 40


def _entorno(*, ausentes: Sequence[str] = (), alterados: Sequence[str] = ()) -> rp.EntornoCustodia:
    def leer(ruta: str) -> bytes:
        if ruta in ausentes:
            raise OSError(ruta)
        if ruta in alterados:
            return b"alterado"
        return (RAIZ / ruta).read_bytes()

    return cp.EntornoCustodia(
        leer_bytes=leer,
        es_ancestro=lambda a, b: True,
        existe_commit=lambda sha: True,
        head=lambda: SHA,
        arbol_limpio=lambda: True,
        diff_vacio=lambda desde, hasta, rutas: True,
        blob_en_commit=lambda sha, ruta: None,
    )


def _ficha_t0() -> cp.FichaConfirmada:
    return cp.FichaConfirmada(
        candidato=rp.CANDIDATO,
        version=1,
        huella="0" * 40,
        commit_de_entrada=SHA,
        estado=cp.ESTADO_CONGELADA,
    )


# --------------------------------------------------------------------------
# La guarda de autorizacion
# --------------------------------------------------------------------------


def test_hoy_la_rederivacion_esta_bloqueada_por_falta_de_autorizacion() -> None:
    """Ejecutar T0 exige un acta que no existe. La ausencia es la guarda."""
    assert not (RAIZ / "docs/architecture" / rp.ACTA_DE_AUTORIZACION).exists()
    fallos = rp.fallos_de_autorizacion(_entorno())
    assert fallos
    assert rp.MOTIVO_SIN_AUTORIZACION in fallos[0]


def test_la_autorizacion_no_es_una_bandera_de_linea_de_ordenes() -> None:
    """No existe argumento que salte la guarda: es un documento del repositorio."""
    acciones = {a.dest for a in recorrido.construir_parser()._actions}
    assert acciones == {"help", "check", "plan"}


def test_las_precondiciones_no_cortocircuitan() -> None:
    """Quien prepare la ejecucion debe ver TODO lo que le falta, de una vez."""
    precondiciones = rp.comprobar_precondiciones(_entorno(), fichas_congeladas=[])
    assert not precondiciones.permite_ejecutar
    assert any(rp.MOTIVO_SIN_AUTORIZACION in f for f in precondiciones.fallos)
    assert any(rp.MOTIVO_SIN_FICHA in f for f in precondiciones.fallos)


def test_t0_no_tiene_ficha_congelada_hoy() -> None:
    assert rp.fallos_de_ficha([])
    assert not rp.fallos_de_ficha([_ficha_t0()])


def test_una_ficha_sustituida_no_habilita_la_rederivacion() -> None:
    sustituida = cp.FichaConfirmada(
        candidato=rp.CANDIDATO,
        version=1,
        huella="0" * 40,
        commit_de_entrada=SHA,
        estado=cp.ESTADO_SUSTITUIDA,
    )
    assert rp.fallos_de_ficha([sustituida])


# --------------------------------------------------------------------------
# Custodia de lo que la rederivacion no puede tocar
# --------------------------------------------------------------------------


def test_el_corpus_congelado_esta_intacto_y_su_alteracion_bloquea() -> None:
    assert rp.fallos_de_corpus(_entorno()) == ()
    ruta = next(iter(rp.CORPUS_CONGELADO))
    fallos = rp.fallos_de_corpus(_entorno(alterados=[ruta]))
    assert any(rp.MOTIVO_CORPUS_ALTERADO in f for f in fallos)


def test_la_linea_base_historica_esta_intacta_y_su_alteracion_bloquea() -> None:
    assert rp.fallos_de_linea_base(_entorno()) == ()
    fallos = rp.fallos_de_linea_base(_entorno(alterados=[rp.LINEA_BASE_HISTORICA]))
    assert any(rp.MOTIVO_LINEA_BASE_ALTERADA in f for f in fallos)


def test_las_tres_actas_de_puerta_existen() -> None:
    assert rp.fallos_de_puertas(_entorno()) == ()
    ausente = f"docs/architecture/{cp.ACTA_TOL_210}"
    fallos = rp.fallos_de_puertas(_entorno(ausentes=[ausente]))
    assert any(rp.MOTIVO_PUERTA_PENDIENTE in f for f in fallos)


# --------------------------------------------------------------------------
# El plan preinscrito
# --------------------------------------------------------------------------


def test_el_plan_conserva_los_escenarios_de_la_linea_base() -> None:
    """Rederivar debe medir LO MISMO, o no seria comparable en funcion."""
    assert rp.ESCENARIOS == ("cero_resultados", "un_resultado_exacto", "muchos_candidatos")
    assert rp.CAPAS == ("solo_indice_fts5", "recuperacion_completa_rank")
    assert len(rp.magnitudes_previstas()) == 6
    assert "cero_resultados.solo_indice_fts5" in rp.magnitudes_previstas()


def test_once_sesiones_es_lo_que_cambia() -> None:
    """El criterio no cambia; el tamano de muestra si. Eso es la rederivacion."""
    assert rp.SESIONES_EXIGIDAS == pp.SESIONES_EXIGIDAS == 11
    assert rp.SESIONES_LINEA_BASE_HISTORICA == 5
    assert rp.deja_de_ser_no_comparable(11)
    assert not rp.deja_de_ser_no_comparable(5)


def test_los_veredictos_se_delegan_al_perfil_aprobado() -> None:
    """La rederivacion no inventa criterio: usa el de TOL-209."""
    perfil = _perfil_sintetico()
    alto = max(perfil.sm_ns, pp.ESCALERA_NS[5])
    propio = rp.evaluar_magnitud_rederivada([alto] * 11, [alto] * 11, perfil=perfil)
    delegado = pp.evaluar_magnitud([alto] * 11, [alto] * 11, perfil=perfil)
    assert propio == delegado
    assert propio.resultado != pp.NO_COMPARABLE


def _perfil_sintetico() -> pp.Perfil:
    e50 = ep.Envolvente(
        tuple(s // 20 for s in pp.ESCALERA_NS), tuple(s // 20 for s in pp.ESCALERA_NS)
    )
    e95 = ep.Envolvente(
        tuple(s // 2 for s in pp.ESCALERA_NS), tuple(s // 2 for s in pp.ESCALERA_NS)
    )
    return pp.Perfil(
        sm_ns=15_000,
        cruce_p50=ep.resolver_cruce(e50),
        envolvente_p95=e95,
        sesiones=pp.SESIONES_EXIGIDAS,
    )


# --------------------------------------------------------------------------
# El esquema del artefacto, congelado antes de que exista la medicion
# --------------------------------------------------------------------------


def _artefacto(perfil: pp.Perfil) -> dict[str, Any]:
    alto = max(perfil.sm_ns, pp.ESCALERA_NS[5])
    magnitudes = []
    for nombre in rp.magnitudes_previstas():
        p50 = [alto] * 11
        p95 = [alto * 2] * 11
        veredicto = rp.evaluar_magnitud_rederivada(p50, p95, perfil=perfil)
        magnitudes.append(
            {
                "magnitud": nombre,
                "p50_por_sesion_ns": p50,
                "p95_por_sesion_ns": p95,
                "min_p50_ns": min(p50),
                "max_p50_ns": max(p50),
                "min_p95_ns": min(p95),
                "max_p95_ns": max(p95),
                "resultado": veredicto.resultado,
                "motivo": veredicto.motivo,
                "registro": pp.registro_por_percentil(veredicto),
            }
        )
    return {
        "documento": "Rederivacion de la linea base de T0",
        "version_esquema": esquema.VERSION_ESQUEMA,
        "estado": "PROPUESTO",
        "paquete": rp.PAQUETE,
        "protocolo": rp.PROTOCOLO,
        "registro": rp.REGISTRO,
        "candidato": rp.CANDIDATO,
        "head_de_esquema": rp.HEAD_T0,
        "corpus": {"acta": rp.ACTA_CORPUS, "blobs": dict(rp.CORPUS_CONGELADO)},
        "plan": {
            "sesiones": 11,
            "repeticiones": rp.REPETICIONES,
            "escenarios": list(rp.ESCENARIOS),
            "capas": list(rp.CAPAS),
        },
        "linea_base_historica": {
            "ruta": rp.LINEA_BASE_HISTORICA,
            "blob": rp.BLOB_LINEA_BASE,
            "sesiones": 5,
            "nota": "se conserva intacta; se rederiva porque cinco sesiones no son comparables",
            "sustituida": False,
        },
        "magnitudes": magnitudes,
        "controles_internos": dict.fromkeys(rp.CONTROLES_BLOQUEANTES, True),
        "no_autoriza": dict.fromkeys(esquema.NEGACIONES, False),
    }


def test_el_artefacto_de_referencia_es_conforme() -> None:
    perfil = _perfil_sintetico()
    assert esquema.fallos_rederivacion(_artefacto(perfil), perfil=perfil) == []


def test_el_validador_es_total_y_nunca_lanza() -> None:
    assert esquema.fallos_rederivacion({})
    assert esquema.fallos_rederivacion([])  # type: ignore[arg-type]
    assert esquema.fallos_rederivacion({"magnitudes": 7})


def test_la_linea_base_historica_no_puede_declararse_sustituida() -> None:
    perfil = _perfil_sintetico()
    doc = _artefacto(perfil)
    doc["linea_base_historica"]["sustituida"] = True
    assert any("no la sustituye" in f for f in esquema.fallos_rederivacion(doc, perfil=perfil))


def test_menos_de_once_sesiones_no_pasa() -> None:
    perfil = _perfil_sintetico()
    doc = _artefacto(perfil)
    doc["plan"]["sesiones"] = 5
    assert any("exactamente 11" in f for f in esquema.fallos_rederivacion(doc, perfil=perfil))


def test_faltar_una_magnitud_no_pasa() -> None:
    perfil = _perfil_sintetico()
    doc = _artefacto(perfil)
    doc["magnitudes"] = doc["magnitudes"][:-1]
    assert any("exactamente" in f for f in esquema.fallos_rederivacion(doc, perfil=perfil))


def test_un_veredicto_inventado_no_pasa() -> None:
    perfil = _perfil_sintetico()
    doc = _artefacto(perfil)
    doc["magnitudes"][0]["resultado"] = (
        pp.VALIDA if doc["magnitudes"][0]["resultado"] != pp.VALIDA else pp.INVALIDA
    )
    fallos = esquema.fallos_rederivacion(doc, perfil=perfil)
    assert any("distinto del recomputado" in f or "no recomputa" in f for f in fallos)


def test_los_minimos_y_maximos_se_recomputan() -> None:
    perfil = _perfil_sintetico()
    doc = _artefacto(perfil)
    doc["magnitudes"][0]["min_p50_ns"] = 1
    assert any("no recomputa" in f for f in esquema.fallos_rederivacion(doc, perfil=perfil))


def test_el_corpus_debe_citarse_por_blob() -> None:
    perfil = _perfil_sintetico()
    doc = _artefacto(perfil)
    doc["corpus"]["blobs"] = {}
    assert any("blobs congelados" in f for f in esquema.fallos_rederivacion(doc, perfil=perfil))


def test_los_conjuntos_estan_cerrados() -> None:
    perfil = _perfil_sintetico()
    for seccion in ("corpus", "plan", "linea_base_historica", "controles_internos", "no_autoriza"):
        doc = _artefacto(perfil)
        doc[seccion]["colado"] = 1
        assert any(
            "ajenos al esquema" in f for f in esquema.fallos_rederivacion(doc, perfil=perfil)
        ), seccion
    doc = _artefacto(perfil)
    doc["seccion_inventada"] = 1
    assert any("ajenos al esquema" in f for f in esquema.fallos_rederivacion(doc, perfil=perfil))


def test_un_control_fallido_bloquea() -> None:
    perfil = _perfil_sintetico()
    doc = _artefacto(perfil)
    doc["controles_internos"]["autorizacion_expresa_presente"] = False
    assert any("control bloqueante" in f for f in esquema.fallos_rederivacion(doc, perfil=perfil))


# --------------------------------------------------------------------------
# El recorrido no mide
# --------------------------------------------------------------------------


def test_sin_check_no_comprueba_nada() -> None:
    assert recorrido.main([]) == recorrido.CODIGO_SIN_CHECK


def test_el_plan_no_ejecuta_nada() -> None:
    assert recorrido.main(["--plan"]) == recorrido.CODIGO_OK


def test_el_recorrido_real_bloquea_y_no_escribe(tmp_path: Path) -> None:
    antes = sorted(p.name for p in (RAIZ / "artifacts/adr002_tolerances").iterdir())
    assert recorrido.main(["--check"]) == recorrido.CODIGO_BLOQUEADO
    assert sorted(p.name for p in (RAIZ / "artifacts/adr002_tolerances").iterdir()) == antes
    assert not (RAIZ / recorrido.SALIDA_PREVISTA).exists()
    assert list(tmp_path.iterdir()) == []


def test_el_artefacto_previsto_no_existe_todavia() -> None:
    """Preparado no es ejecutado."""
    assert not (RAIZ / recorrido.SALIDA_PREVISTA).exists()


def test_ningun_modulo_del_paquete_mide() -> None:
    """Ni cronometro, ni SQLite, ni procesos: este paquete no mide."""
    for nombre in ("rederivation_protocol", "schema_rederivation_v0_1", "run_rederivation"):
        fuente = (RAIZ / "experiments/adr002/rederivation" / f"{nombre}.py").read_text("utf-8")
        for prohibido in ("perf_counter", "sqlite3", "time.time", "multiprocessing"):
            assert prohibido not in fuente, f"{nombre} usa {prohibido}"


def test_los_once_controles_fallan_cerrado() -> None:
    assert rp.evaluar_controles(dict.fromkeys(rp.CONTROLES_BLOQUEANTES, True)).valido
    assert not rp.evaluar_controles({}).valido
    incompleto = dict.fromkeys(rp.CONTROLES_BLOQUEANTES, True)
    del incompleto["autorizacion_expresa_presente"]
    assert not rp.evaluar_controles(incompleto).valido
