"""El arnés de ejecución: que traduzca fiel y que juzgue lo que dice juzgar.

Estas pruebas **no miden tiempo** y no ejecutan la ronda. Comprueban las dos
cosas que, si se rompieran, harían inservible cualquier cifra posterior: que los
casos congelados se conviertan en peticiones sin perder ni inventar nada, y que
cada métrica cuente **lo que su norma nombra** y no otra cosa parecida.

Cuatro de los controles de aquí nacieron de defectos que la verificación previa
a la corrida encontró en este mismo arnés, y por eso están escritos como el
defecto: `E0 -> E1 -> E5` no es un salto, `E0` y `E5` no originan resultados,
leer una polaridad al revés no es fundirla, y una instanciación que se
contradice no puntúa contra quien la ejecuta.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.candidates.common.contracts import Cardinalidad, Modo, Polaridad
from experiments.adr002.round import cases as cs
from experiments.adr002.round import execute_round as ex
from experiments.adr002.round import metrics as mt
from experiments.adr002.round import round_protocol as rp

RAIZ: Final = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def casos() -> tuple[cs.CasoEjecutable, ...]:
    return cs.casos_ejecutables(cs.cargar_artefactos())


def _caso(**cambios: object) -> cs.CasoEjecutable:
    """Un caso mínimo para probar una métrica sin arrastrar la familia entera."""
    from experiments.adr002.candidates.common.contracts import (
        Ambito,
        Peticion,
        VentanaTemporal,
    )

    base: dict[str, object] = {
        "identificador": "N-TEST",
        "canonico": "B04-CA-TEST",
        "nivel": 1,
        "peticion": Peticion(
            operation_id="prueba",
            consulta="consulta",
            proposito="responder_al_usuario",
            modo=Modo.M1_ORDINARIO,
            ambito=Ambito(global_=False, proyectos=("1",)),
            ventana=VentanaTemporal(tiempo_objetivo="2026-06-15T00:00:00Z"),
            cardinalidad=Cardinalidad.EXHAUSTIVA,
            limite_objetivo=10,
            limite_duro=10,
        ),
        "cardinalidad_declarada": "EXHAUSTIVA",
        "etapa_esperada": "E1",
        "parada_esperada": "S1",
        "resultado_esperado": (),
        "orden_esperado": (),
        "tipo_de_orden": "CONJUNTO",
        "elegibles": (),
        "prohibidos": (),
        "pendientes_por_limite": (),
        "decoys_fuera_de_ambito": (),
        "permiso": "AUTORIZADO",
        "proyecto_declarado": "PRJ-ALFA",
    }
    base.update(cambios)
    return cs.CasoEjecutable(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# A. La traducción: ni pierde ni inventa
# ---------------------------------------------------------------------------


def test_se_traducen_los_cincuenta_casos_de_recuperacion(
    casos: tuple[cs.CasoEjecutable, ...],
) -> None:
    assert len(casos) == 50
    assert len({c.identificador for c in casos}) == 50


def test_los_no_adjudicables_son_los_que_el_canon_declara(
    casos: tuple[cs.CasoEjecutable, ...],
) -> None:
    """Ni uno más ni uno menos: excluir por gusto sería elegir el resultado."""
    observados = {c.canonico for c in casos if not c.adjudicable}
    assert observados == set(cs.NO_ADJUDICABLES)
    for caso in casos:
        assert bool(caso.motivo_no_adjudicable) is (not caso.adjudicable)


def test_el_permiso_no_autorizado_se_traduce_como_proposito_vacio(
    casos: tuple[cs.CasoEjecutable, ...],
) -> None:
    """`RF-02`: sin autorización no se recupera, y `E0` es donde eso ocurre."""
    sin_permiso = [c for c in casos if c.sin_autorizacion]
    assert sin_permiso
    for caso in sin_permiso:
        assert caso.peticion.proposito == ""
    for caso in casos:
        if not caso.sin_autorizacion:
            assert caso.peticion.proposito


def test_un_caso_sin_limite_declarado_recibe_uno_que_no_ata(
    casos: tuple[cs.CasoEjecutable, ...],
) -> None:
    """Un límite que nunca corta es la traducción fiel de «sin límite»."""
    corpus = cs.cargar_artefactos()[cs.CORPUS]
    canon = len(corpus["items"])
    atados = [c for c in casos if c.peticion.limite_duro != canon]
    assert len(atados) == 2
    for caso in casos:
        assert caso.peticion.limite_duro >= caso.peticion.limite_objetivo


def test_los_prohibidos_suman_las_dos_fuentes(casos: tuple[cs.CasoEjecutable, ...]) -> None:
    """La lista instanciada y la calculada por la adjudicación, las dos."""
    con_prohibidos = [c for c in casos if c.prohibidos]
    assert len(con_prohibidos) >= 30
    for caso in con_prohibidos:
        assert not set(caso.prohibidos) & set(caso.resultado_esperado)


def test_los_senuelos_fuera_de_ambito_no_se_pierden(
    casos: tuple[cs.CasoEjecutable, ...],
) -> None:
    """Llegan como pares `{id, razon}`; leer solo la forma desnuda los perdía."""
    con_senuelos = [c for c in casos if c.decoys_fuera_de_ambito]
    assert len(con_senuelos) == 6


def test_las_desviaciones_de_traduccion_se_declaran() -> None:
    """El §10.11 exige declarar toda desviación. Callarla es la desviación."""
    assert len(cs.DESVIACIONES_DE_TRADUCCION) >= 4
    assert any("proposito vacio" in d for d in cs.DESVIACIONES_DE_TRADUCCION)


# ---------------------------------------------------------------------------
# B. Conformidad de etapa: los tres defectos que la verificación encontró
# ---------------------------------------------------------------------------


def test_parar_pronto_no_es_saltar() -> None:
    """`E0 -> E1 -> E5` es el caso perfecto, no una infracción.

    La política escalonada manda expandir **solo por insuficiencia**: si `E1`
    basta, no abrir `E2` es obedecerla. Leer `E5` como discontinuidad hacía que
    veintisiete casos correctos se contaran como saltos.
    """
    conforme, razon = mt.etapa_conforme(_caso(etapa_esperada="E1"), ("E0", "E1", "E5"), "E1")
    assert conforme, razon


def test_saltarse_una_etapa_de_expansion_si_es_saltar() -> None:
    conforme, razon = mt.etapa_conforme(_caso(etapa_esperada="E3"), ("E0", "E1", "E3", "E5"), "E3")
    assert not conforme
    assert "salto" in razon


def test_e5_no_origina_y_por_eso_no_se_le_exige_origen() -> None:
    """Ningún resultado nace en `E5`: adjudica. Exigirlo era exigir lo imposible."""
    caso = _caso(etapa_esperada="E5")
    conforme, razon = mt.etapa_conforme(caso, ("E0", "E1", "E5"), "E1")
    assert conforme
    assert "E5 no origina" in razon


def test_e0_exige_que_la_expansion_no_aporte() -> None:
    """Zanjarse en `E0` es zanjarse **antes** de expandir, y eso sí es comprobable."""
    caso = _caso(etapa_esperada="E0")
    assert mt.etapa_conforme(caso, ("E0",), None)[0]
    assert not mt.etapa_conforme(caso, ("E0", "E1", "E5"), "E1")[0]


def test_una_instanciacion_que_se_contradice_no_puntua(
    casos: tuple[cs.CasoEjecutable, ...],
) -> None:
    """`E0` con resultados esperados pide dos cosas incompatibles.

    El conflicto es de la familia, no del participante, y por eso su métrica de
    etapa no cuenta para nadie —ni a favor ni en contra—.
    """
    contradictorios = [c for c in casos if c.etapa_inconsistente]
    assert len(contradictorios) == 1
    assert contradictorios[0].canonico == "B04-CA-14"
    assert not _caso(etapa_esperada="E1").etapa_inconsistente


# ---------------------------------------------------------------------------
# C. Polaridad: fundir y malinterpretar son cosas distintas
# ---------------------------------------------------------------------------


def test_leer_una_polaridad_al_reves_no_es_fundirla() -> None:
    """El §6.1 define fundir; leer mal es otro defecto y va a otra columna."""
    canon = {"MEMORIA:1": Polaridad.AFIRMATIVA}
    leida = {"MEMORIA:1": Polaridad.NEGATIVA}
    assert mt.confusion_de_polaridad(("MEMORIA:1",), leida, canon) == ()
    assert mt.polaridad_mal_leida(("MEMORIA:1",), leida, canon) == ("MEMORIA:1",)


def test_entregar_opuestas_con_la_misma_marca_es_fundirlas() -> None:
    canon = {"MEMORIA:1": Polaridad.AFIRMATIVA, "MEMORIA:2": Polaridad.NEGATIVA}
    leida = {"MEMORIA:1": Polaridad.AFIRMATIVA, "MEMORIA:2": Polaridad.AFIRMATIVA}
    assert len(mt.confusion_de_polaridad(("MEMORIA:1", "MEMORIA:2"), leida, canon)) == 1


def test_entregarlas_marcadas_y_distinguidas_es_correcto() -> None:
    canon = {"MEMORIA:1": Polaridad.AFIRMATIVA, "MEMORIA:2": Polaridad.NEGATIVA}
    leida = {"MEMORIA:1": Polaridad.AFIRMATIVA, "MEMORIA:2": Polaridad.NEGATIVA}
    assert mt.confusion_de_polaridad(("MEMORIA:1", "MEMORIA:2"), leida, canon) == ()


def test_quien_no_marca_polaridad_no_distingue_nada() -> None:
    """No marcar no es aprobar: es la fusión más completa que hay."""
    canon = {"MEMORIA:1": Polaridad.AFIRMATIVA, "MEMORIA:2": Polaridad.NEGATIVA}
    assert len(mt.confusion_de_polaridad(("MEMORIA:1", "MEMORIA:2"), {}, canon)) == 1


# ---------------------------------------------------------------------------
# D. Las demás métricas cuentan lo que su norma nombra
# ---------------------------------------------------------------------------


def test_la_contaminacion_es_un_recuento_absoluto() -> None:
    caso = _caso(prohibidos=("MEMORIA:9",))
    assert mt.contaminacion(("MEMORIA:1", "MEMORIA:9"), caso) == ("MEMORIA:9",)
    assert mt.contaminacion(("MEMORIA:1",), caso) == ()


def test_la_fuga_se_mide_contra_el_proyecto_real_no_contra_los_senuelos() -> None:
    """Una fuga que nadie previó sigue siendo una fuga."""
    caso = _caso(decoys_fuera_de_ambito=())
    proyectos = {"MEMORIA:1": "1", "MEMORIA:2": "7"}
    assert mt.fuga_de_ambito(("MEMORIA:1", "MEMORIA:2"), caso, proyectos) == ("MEMORIA:2",)


def test_un_critico_que_el_limite_dejo_pendiente_no_cuenta_como_fallo() -> None:
    caso = _caso(resultado_esperado=("MEMORIA:5",), pendientes_por_limite=("MEMORIA:5",))
    assert mt.criticos_pendientes(caso, (), ("MEMORIA:5",)) == ()


def test_declarar_ausencia_cuando_no_la_hay_es_incorrecto() -> None:
    caso = _caso(resultado_esperado=("MEMORIA:5",))
    assert not mt.ausencia_correcta(caso, (), "SIN_RESULTADO_UTILIZABLE")
    assert mt.ausencia_correcta(caso, ("MEMORIA:5",), "COMPLETA")


def test_las_cinco_puertas_son_cinco_y_tres_son_de_fallo_duro() -> None:
    assert len(mt.PUERTAS_BOOLEANAS) == 5
    assert set(mt.PUERTAS_DE_FALLO_DURO) < set(mt.PUERTAS_BOOLEANAS)
    assert len(mt.PUERTAS_DE_FALLO_DURO) == 3


def test_una_sola_ocurrencia_descarta() -> None:
    """§6.1: no se promedia. Un prohibido basta, por perfecto que sea el resto."""
    veredicto = mt.VeredictoDeCaso(
        caso="N-TEST",
        canonico="B04-CA-TEST",
        adjudicable=True,
        obtenido=("MEMORIA:9",),
        esperado=(),
        contaminacion=("MEMORIA:9",),
        fuga_de_ambito=(),
        confusion_de_polaridad=(),
        polaridad_mal_leida=(),
        etapa_conforme=True,
        razon_de_etapa="",
        etapa_puntua=True,
        resultado_exacto=False,
        declara_orden=False,
        orden_exacto=False,
        ausencia_correcta=False,
        criticos_pendientes=(),
        explicaciones_completas=0,
        resultados_totales=1,
        suficiencia="COMPLETA",
        estado_externo="",
        parada="S1",
        etapas_recorridas=("E0", "E1", "E5"),
    )
    resumen = mt.resumir("X", [veredicto], borrado_y_regeneracion=True)
    assert resumen.descartado_por_fallo_duro
    assert not resumen.pasa_las_puertas


# ---------------------------------------------------------------------------
# E. El ejecutor no mide sin permiso y no escribe sin orden
# ---------------------------------------------------------------------------


def test_sin_execute_no_hace_nada() -> None:
    assert ex.main([]) == ex.CODIGO_SIN_EXECUTE


def test_un_worker_exige_su_numero_de_sesion() -> None:
    assert ex.main(["--execute", "--worker", "--session", "0"]) == ex.CODIGO_BLOQUEADO


def test_no_hay_bandera_que_salte_la_guarda() -> None:
    """La autorización es un documento; ninguna bandera la sustituye."""
    fuente = (RAIZ / "experiments/adr002/round/execute_round.py").read_text(encoding="utf-8")
    for prohibida in ("--force", "--yes", "--skip-checks", "--sin-guarda", "--no-check"):
        assert prohibida not in fuente, prohibida


def test_la_repeticion_unica_del_6_8_es_una_y_solo_una() -> None:
    assert ex.CORRIDAS_MAXIMAS == 2


def test_una_corrida_con_menos_sesiones_es_invalida() -> None:
    fallos = ex.fallos_de_corrida([])
    assert any("sesiones" in f for f in fallos)


def test_una_corrida_con_muestras_de_menos_es_invalida() -> None:
    sesion = {
        "sesion": 1,
        "pid": 1,
        "warmup_descartado": rp.WARMUP,
        "repeticiones": rp.REPETICIONES,
        "muestras_ns": {p: [1] for p in rp.PARTICIPANTES},
    }
    fallos = ex.fallos_de_corrida([sesion] * rp.SESIONES_EXIGIDAS)
    assert any("muestras" in f for f in fallos)


def test_las_salidas_no_se_sobrescriben(tmp_path: Path) -> None:
    existente = tmp_path / "ya_esta.json"
    existente.write_text("{}", encoding="utf-8")
    fallos = ex.fallos_adicionales(arbol_limpio=True, salidas=(existente,))
    assert any("no se sobrescribe" in f for f in fallos)


def test_un_arbol_sucio_bloquea() -> None:
    fallos = ex.fallos_adicionales(arbol_limpio=False, salidas=())
    assert any("no esta limpio" in f for f in fallos)


def test_lo_que_no_es_del_canon_se_aparta_y_se_declara(
    casos: tuple[cs.CasoEjecutable, ...],
) -> None:
    """Un documento prohibido no puede aparecer, y callarlo era peor que apartarlo.

    ``referencia_canonica`` acepta ``MSG`` y ``DOC`` y devuelve `MENSAJE:n` y
    `DOCUMENTO:n`, que **no son clases del canon** y por tanto no pueden ser
    resultados. Antes entraban en la lista de prohibidos, donde no podían
    detectarse jamás: la puerta parecía vigilarlos y no vigilaba nada. Ahora se
    apartan del recuento y viajan declarados con el caso.
    """
    apartadas = {i for c in casos for i in c.referencias_fuera_del_canon}
    assert apartadas
    assert all(i.split(":")[0] in ("MENSAJE", "DOCUMENTO") for i in apartadas)
    for caso in casos:
        for identidad in (*caso.resultado_esperado, *caso.prohibidos, *caso.elegibles):
            assert identidad.split(":")[0] in ("MEMORIA", "DECISION"), identidad
