"""Pruebas del arnes real de la rederivacion (acta de autorizacion de T0).

Ninguna prueba cronometra nada: comprueban las reglas del arnes —derivacion
cerrada de consultas, carga fiel del corpus congelado, controles de corrida
fail-closed, agregacion y validacion contra el esquema congelado— con datos
sinteticos o con artefactos ya congelados del repositorio.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.rederivation import execute_rederivation as ejecutor
from experiments.adr002.rederivation import frozen_corpus as fc
from experiments.adr002.rederivation import rederivation_protocol as rp
from experiments.adr002.rederivation import schema_rederivation_v0_1 as esquema
from experiments.adr002.tolerances import profile_protocol as pp

RAIZ = Path(__file__).resolve().parents[3]


# --------------------------------------------------------------------------
# La regla de tokens, cerrada
# --------------------------------------------------------------------------


def test_los_tokens_pliegan_diacriticos_como_el_indice() -> None:
    assert fc.tokens_ascii("Aunque el glaciar está aquí") == [
        "aunque",
        "el",
        "glaciar",
        "esta",
        "aqui",
    ]


def test_una_corrida_con_digitos_se_descarta_entera() -> None:
    """Nunca se toma un fragmento de un token del indice."""
    assert fc.tokens_ascii("mar123 mar") == ["mar"]


def test_el_conteo_es_presencia_por_item_no_frecuencia() -> None:
    items = [{"text": "faro faro faro"}, {"text": "faro y vela"}]
    conteo = fc.conteo_por_item(items)
    assert conteo["faro"] == 2
    assert conteo["vela"] == 1


def _corpus_sintetico() -> dict[str, Any]:
    return {
        "conteos": {"mensajes": 3, "recuerdos": 2, "decisiones": 1, "proyectos": 2},
        "proyectos": [
            {"id": "PRJ-UNO", "nombre": "Uno"},
            {"id": "PRJ-DOS", "nombre": "Dos"},
        ],
        "mensajes": [
            {"id": "MSG-1", "texto": "primer mensaje del corpus"},
            {"id": "MSG-2", "texto": "segundo mensaje del corpus"},
            {"id": "MSG-3", "texto": "tercer mensaje del corpus"},
        ],
        "items": [
            {
                "id": "MEM-1",
                "kind": "MEMORIA",
                "project_id": "PRJ-UNO",
                "text": "faro brilla unico",
                "validez": "VIGENTE",
                "disponibilidad": "DISPONIBLE",
            },
            {
                "id": "MEM-2",
                "kind": "MEMORIA",
                "project_id": "PRJ-DOS",
                "text": "faro brilla",
                "validez": "SUSTITUIDA",
                "disponibilidad": "DISPONIBLE",
            },
            {
                "id": "DEC-1",
                "kind": "DECISION",
                "project_id": "PRJ-UNO",
                "text": "faro brilla siempre",
                "confirmacion": "CONFIRMADA",
            },
        ],
    }


def test_derivar_consultas_es_determinista_y_cerrada() -> None:
    corpus = _corpus_sintetico()
    primera = fc.derivar_consultas(corpus)
    segunda = fc.derivar_consultas(corpus)
    assert primera == segunda
    assert primera.cero_resultados == fc.TOKEN_CERO
    # 'siempre' y 'unico' aparecen una vez; gana el primero alfabetico.
    assert primera.un_resultado_exacto == "siempre"
    # 'brilla' y 'faro' empatan a tres; gana el primero alfabetico.
    assert primera.muchos_candidatos == "brilla"
    assert primera.esperados == {
        "cero_resultados": 0,
        "un_resultado_exacto": 1,
        "muchos_candidatos": 3,
    }


def test_derivar_consultas_bloquea_si_el_token_cero_aparece() -> None:
    corpus = _corpus_sintetico()
    corpus["items"][0]["text"] = f"texto con {fc.TOKEN_CERO}"
    with pytest.raises(fc.CorpusInvalidoError):
        fc.derivar_consultas(corpus)


def test_derivar_consultas_exige_items() -> None:
    with pytest.raises(fc.CorpusInvalidoError):
        fc.derivar_consultas({"items": []})


# --------------------------------------------------------------------------
# El corpus congelado, por blob
# --------------------------------------------------------------------------


def test_cargar_corpus_congelado_verifica_el_blob(tmp_path: Path) -> None:
    destino = tmp_path / fc.RUTA_CORPUS
    destino.parent.mkdir(parents=True)
    destino.write_text('{"alterado": true}', encoding="utf-8")
    with pytest.raises(fc.CorpusInvalidoError):
        fc.cargar_corpus_congelado(tmp_path)


def test_las_consultas_reales_derivan_del_corpus_congelado() -> None:
    """Sobre el corpus real: cero ausente, uno exacto, muchos de verdad."""
    corpus = fc.cargar_corpus_congelado(RAIZ)
    consultas = fc.derivar_consultas(corpus)
    assert consultas.esperados["cero_resultados"] == 0
    assert consultas.esperados["un_resultado_exacto"] == 1
    assert consultas.esperados["muchos_candidatos"] >= 2
    assert fc.derivar_consultas(corpus) == consultas


# --------------------------------------------------------------------------
# La carga fiel al corpus, verificada funcionalmente
# --------------------------------------------------------------------------


def test_construir_base_de_referencia_materializa_fielmente(tmp_path: Path) -> None:
    corpus = _corpus_sintetico()
    base = tmp_path / "referencia.db"
    conteos = fc.construir_base_de_referencia(corpus, base)
    assert conteos.proyectos == 2
    assert conteos.mensajes == 3
    assert conteos.memorias == 2
    assert conteos.memorias_vigentes == 1
    assert conteos.decisiones == 1
    assert conteos.filas_fts == 3
    assert fc.fallos_de_conteos(corpus, conteos) == []
    assert fc.fallos_de_consultas(base, fc.derivar_consultas(corpus)) == []


def test_un_kind_desconocido_bloquea_la_carga(tmp_path: Path) -> None:
    corpus = _corpus_sintetico()
    corpus["items"][0]["kind"] = "OTRO"
    with pytest.raises(fc.CorpusInvalidoError):
        fc.construir_base_de_referencia(corpus, tmp_path / "otra.db")


def test_una_carga_infiel_se_denuncia(tmp_path: Path) -> None:
    corpus = _corpus_sintetico()
    base = tmp_path / "referencia.db"
    conteos = fc.construir_base_de_referencia(corpus, base)
    corpus["conteos"]["mensajes"] = 4
    assert fc.fallos_de_conteos(corpus, conteos) != []


def test_una_consulta_que_no_cuenta_lo_esperado_se_denuncia(tmp_path: Path) -> None:
    corpus = _corpus_sintetico()
    base = tmp_path / "referencia.db"
    fc.construir_base_de_referencia(corpus, base)
    consultas = fc.ConsultasDeControl(
        cero_resultados=fc.TOKEN_CERO,
        un_resultado_exacto="siempre",
        muchos_candidatos="brilla",
        esperados={"cero_resultados": 0, "un_resultado_exacto": 2, "muchos_candidatos": 3},
    )
    fallos = fc.fallos_de_consultas(base, consultas)
    assert len(fallos) == 1
    assert "un_resultado_exacto" in fallos[0]


# --------------------------------------------------------------------------
# Controles de corrida, fail-closed
# --------------------------------------------------------------------------

_ESPERADOS = {"cero_resultados": 0, "un_resultado_exacto": 1, "muchos_candidatos": 3}


def _sesion_sintetica(pid: int, *, base_ns: int = 100_000) -> dict[str, Any]:
    magnitudes = {}
    for indice, nombre in enumerate(rp.magnitudes_previstas()):
        muestras = [base_ns + indice * 1_000 + (j % 7) for j in range(rp.REPETICIONES)]
        magnitudes[nombre] = {
            "muestras_ns": muestras,
            "p50_ns": pp.p50_ns(muestras),
            "p95_ns": pp.p95_ns(muestras),
        }
    return {
        "pid": pid,
        "warmup_descartado": ejecutor.WARMUP,
        "repeticiones": rp.REPETICIONES,
        "conteos": dict(_ESPERADOS),
        "magnitudes": magnitudes,
        "carga_inicial": 0.5,
        "carga_final": 0.5,
    }


def _corrida_sintetica() -> list[dict[str, Any]]:
    return [_sesion_sintetica(1000 + i) for i in range(rp.SESIONES_EXIGIDAS)]


def test_una_corrida_conforme_no_tiene_fallos() -> None:
    assert ejecutor.fallos_de_corrida(_corrida_sintetica(), esperados=_ESPERADOS) == []


def test_menos_de_once_sesiones_es_invalido() -> None:
    fallos = ejecutor.fallos_de_corrida(_corrida_sintetica()[:-1], esperados=_ESPERADOS)
    assert any("11" in f for f in fallos)


def test_pids_repetidos_son_invalidos() -> None:
    corrida = _corrida_sintetica()
    corrida[1]["pid"] = corrida[0]["pid"]
    fallos = ejecutor.fallos_de_corrida(corrida, esperados=_ESPERADOS)
    assert any("procesos distintos" in f for f in fallos)


def test_un_conteo_funcional_distinto_es_invalido() -> None:
    corrida = _corrida_sintetica()
    corrida[3]["conteos"] = {**_ESPERADOS, "muchos_candidatos": 2}
    fallos = ejecutor.fallos_de_corrida(corrida, esperados=_ESPERADOS)
    assert any("conteos funcionales" in f for f in fallos)


def test_un_vector_corto_es_invalido() -> None:
    corrida = _corrida_sintetica()
    nombre = next(iter(rp.magnitudes_previstas()))
    corrida[0]["magnitudes"][nombre]["muestras_ns"] = [1] * (rp.REPETICIONES - 1)
    fallos = ejecutor.fallos_de_corrida(corrida, esperados=_ESPERADOS)
    assert any("vector crudo invalido" in f for f in fallos)


def test_un_percentil_publicado_que_no_recomputa_es_invalido() -> None:
    corrida = _corrida_sintetica()
    nombre = next(iter(rp.magnitudes_previstas()))
    corrida[0]["magnitudes"][nombre]["p50_ns"] += 1
    fallos = ejecutor.fallos_de_corrida(corrida, esperados=_ESPERADOS)
    assert any("P50 publicado no recomputa" in f for f in fallos)


def test_una_magnitud_ausente_es_invalida() -> None:
    corrida = _corrida_sintetica()
    nombre = next(iter(rp.magnitudes_previstas()))
    del corrida[0]["magnitudes"][nombre]
    fallos = ejecutor.fallos_de_corrida(corrida, esperados=_ESPERADOS)
    assert any("seis magnitudes" in f for f in fallos)


# --------------------------------------------------------------------------
# El perfil aprobado se reconstruye, no se acepta
# --------------------------------------------------------------------------


def test_el_perfil_reconstruido_coincide_con_el_acta_de_tol_209() -> None:
    perfil = ejecutor.perfil_aprobado(RAIZ)
    assert perfil.sm_ns == 17405
    assert perfil.u50_ns == 2685
    assert perfil.b50_en_u50_ns == 537
    assert perfil.sesiones == rp.SESIONES_EXIGIDAS


# --------------------------------------------------------------------------
# Agregacion, veredictos delegados y esquema congelado
# --------------------------------------------------------------------------


def test_las_magnitudes_rederivadas_recomputan_y_delegan() -> None:
    perfil = ejecutor.perfil_aprobado(RAIZ)
    corrida = _corrida_sintetica()
    magnitudes = ejecutor.magnitudes_rederivadas(corrida, perfil=perfil)
    assert [m["magnitud"] for m in magnitudes] == list(rp.magnitudes_previstas())
    for magnitud in magnitudes:
        p50s, p95s = magnitud["p50_por_sesion_ns"], magnitud["p95_por_sesion_ns"]
        assert len(p50s) == len(p95s) == rp.SESIONES_EXIGIDAS
        assert magnitud["min_p50_ns"] == min(p50s)
        assert magnitud["max_p95_ns"] == max(p95s)
        veredicto = rp.evaluar_magnitud_rederivada(p50s, p95s, perfil=perfil)
        assert magnitud["resultado"] == veredicto.resultado
        assert magnitud["motivo"] == veredicto.motivo
        assert magnitud["registro"] == pp.registro_por_percentil(veredicto)
        assert veredicto.resultado != pp.NO_COMPARABLE


def test_el_documento_construido_valida_contra_el_esquema_congelado() -> None:
    perfil = ejecutor.perfil_aprobado(RAIZ)
    magnitudes = ejecutor.magnitudes_rederivadas(_corrida_sintetica(), perfil=perfil)
    controles = dict.fromkeys(rp.CONTROLES_BLOQUEANTES, True)
    documento = ejecutor.construir_documento(magnitudes=magnitudes, controles=controles)
    assert esquema.fallos_rederivacion(documento, perfil=perfil) == []


def test_un_veredicto_manipulado_no_valida() -> None:
    perfil = ejecutor.perfil_aprobado(RAIZ)
    magnitudes = ejecutor.magnitudes_rederivadas(_corrida_sintetica(), perfil=perfil)
    magnitudes[0]["resultado"] = "VALIDA" if magnitudes[0]["resultado"] != "VALIDA" else "INVALIDA"
    controles = dict.fromkeys(rp.CONTROLES_BLOQUEANTES, True)
    documento = ejecutor.construir_documento(magnitudes=magnitudes, controles=controles)
    assert esquema.fallos_rederivacion(documento, perfil=perfil) != []


def test_el_documento_de_muestras_conserva_los_vectores_crudos() -> None:
    corpus = _corpus_sintetico()
    consultas = fc.derivar_consultas(corpus)
    conteos = fc.ConteosCargados(
        proyectos=2,
        mensajes=3,
        memorias=2,
        memorias_vigentes=1,
        decisiones=1,
        filas_fts=3,
        no_cargados={"entidades": 0, "documentos": 0, "relaciones": 0},
    )
    corrida = _corrida_sintetica()
    documento = ejecutor.documento_de_muestras(
        head="f" * 40,
        consultas=consultas,
        conteos=conteos,
        resultados=corrida,
        repeticion_unica_ejercitada=False,
        boot_id="boot",
    )
    assert len(documento["sesiones"]) == rp.SESIONES_EXIGIDAS
    primera = documento["sesiones"][0]["magnitudes"]
    nombre = next(iter(rp.magnitudes_previstas()))
    assert primera[nombre]["muestras_ns"] == corrida[0]["magnitudes"][nombre]["muestras_ns"]
    assert documento["repeticion_unica_6_8_ejercitada"] is False
    assert json.dumps(documento)  # serializable tal cual


# --------------------------------------------------------------------------
# La CLI no mide sin --execute y el worker exige sus datos
# --------------------------------------------------------------------------


def test_sin_execute_no_hace_nada() -> None:
    assert ejecutor.main([]) == ejecutor.CODIGO_SIN_EXECUTE


def test_un_worker_sin_db_ni_consultas_se_bloquea() -> None:
    assert ejecutor.main(["--execute", "--worker"]) == ejecutor.CODIGO_BLOQUEADO


def test_un_worker_con_escenarios_incompletos_se_bloquea() -> None:
    assert (
        ejecutor.main(["--execute", "--worker", "--db", "x.db", "--queries", '{"a": "b"}'])
        == ejecutor.CODIGO_BLOQUEADO
    )


def test_las_salidas_existentes_bloquean(tmp_path: Path) -> None:
    """No se sobrescribe evidencia: una salida presente es un fallo."""
    ocupada = tmp_path / "ocupada.json"
    ocupada.write_text("{}", encoding="utf-8")
    fallos = ejecutor.fallos_adicionales(
        _entorno_nulo(),
        fichas=[],
        head="a" * 40,
        arbol_limpio=True,
        salida_existe=True,
        muestras_existen=True,
        es_ancestro=lambda *_: True,
    )
    assert any(ejecutor.SALIDA in f for f in fallos)
    assert any(ejecutor.SALIDA_MUESTRAS in f for f in fallos)


def _entorno_nulo() -> Any:
    class _Entorno:
        @staticmethod
        def leer_bytes(ruta: str) -> bytes:
            raise OSError(ruta)

    return _Entorno()


def test_un_arbol_sucio_bloquea() -> None:
    fallos = ejecutor.fallos_adicionales(
        _entorno_nulo(),
        fichas=[],
        head="a" * 40,
        arbol_limpio=False,
        salida_existe=False,
        muestras_existen=False,
        es_ancestro=lambda *_: True,
    )
    assert any("arbol" in f for f in fallos)


def test_una_ficha_en_el_mismo_commit_no_es_anterior() -> None:
    from experiments.adr002.cards import card_protocol as cp

    head = "a" * 40
    ficha = cp.FichaConfirmada(
        candidato=rp.CANDIDATO,
        version=1,
        huella="b" * 40,
        commit_de_entrada=head,
        estado=cp.ESTADO_CONGELADA,
    )
    fallos = ejecutor.fallos_adicionales(
        _entorno_nulo(),
        fichas=[ficha],
        head=head,
        arbol_limpio=True,
        salida_existe=False,
        muestras_existen=False,
        es_ancestro=lambda *_: True,
    )
    assert any("ESTRICTO" in f for f in fallos)


def test_el_perfil_y_su_fuente_se_exigen_intactos_por_blob() -> None:
    fallos = ejecutor.fallos_adicionales(
        _entorno_nulo(),
        fichas=[],
        head="a" * 40,
        arbol_limpio=True,
        salida_existe=False,
        muestras_existen=False,
        es_ancestro=lambda *_: True,
    )
    assert any(ejecutor.RUTA_PERFIL in f for f in fallos)
    assert any(ejecutor.RUTA_SUELO in f for f in fallos)


def test_el_cronometro_es_el_congelado_de_los_paquetes_06_y_07() -> None:
    """El arnes no trae cronometro propio: importa ``medir_ns`` congelado."""
    fuente = (RAIZ / "experiments/adr002/rederivation/execute_rederivation.py").read_text("utf-8")
    assert "sondas.medir_ns(" in fuente
    assert "perf_counter" not in fuente
