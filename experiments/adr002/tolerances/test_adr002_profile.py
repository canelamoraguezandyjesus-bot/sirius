"""Pruebas del perfil de tolerancias P50/P95 (TOL-209, paquete 08).

Cubren:

1. la separacion de percentiles y las propiedades demostrables del perfil;
2. **la guarda de sesiones**, que es la regla 5 hecha ejecutable;
3. el recorrido completo de la derivacion, incluido su **determinismo**;
4. el validador, contra un catalogo de mutaciones.

Ninguna prueba mide, y ninguna escribe en ``artifacts/``.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from collections.abc import Mapping
from copy import deepcopy
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from experiments.adr002.tolerances import derive_profile as derivacion
from experiments.adr002.tolerances import envelope_protocol as ep
from experiments.adr002.tolerances import profile_protocol as pp
from experiments.adr002.tolerances import schema_profile_v0_1 as esquema

RAIZ = Path(__file__).resolve().parents[3]
SHA_FICTICIO = "0" * 40
PIDS: tuple[int, ...] = tuple(9001 + i for i in range(pp.SESIONES_EXIGIDAS))


# --------------------------------------------------------------------------
# Utilidades sinteticas
# --------------------------------------------------------------------------


def observaciones_de_leyes(
    ley50: Any, ley95: Any, sesiones: int = pp.SESIONES_EXIGIDAS
) -> list[pp.ObservacionEscala]:
    """Observaciones con dispersion exacta ``ley(s)`` en cada percentil."""
    ultimo = max(1, sesiones - 1)
    salida: list[pp.ObservacionEscala] = []
    for escala in pp.ESCALERA_NS:
        for indice in range(sesiones):
            p50 = escala + ley50(escala) * indice // ultimo
            p95 = 2 * escala + ley95(escala) * indice // ultimo
            for familia in pp.FAMILIAS:
                salida.append(
                    pp.ObservacionEscala(
                        familia=familia,
                        escala_ns=escala,
                        pid=9001 + indice,
                        p50=p50 if familia == pp.FAMILIAS[1] else escala,
                        p95=p95 if familia == pp.FAMILIAS[1] else 2 * escala,
                    )
                )
    return salida


def unitarias_sinteticas(sesiones: int = pp.SESIONES_EXIGIDAS) -> list[pp.ObservacionUnitaria]:
    return [
        pp.ObservacionUnitaria(sonda=sonda, pid=9001 + i, p95=5_000 + 1_000 * i)
        for sonda in pp.SONDAS_UNITARIAS
        for i in range(sesiones)
    ]


def perfil_sintetico(ley50: Any = lambda s: s // 20, ley95: Any = lambda s: s // 2) -> pp.Perfil:
    """``D50 = s/20`` (5 %, sostenible en todo escalon) y ``D95 = s/2``."""
    return pp.derivar_perfil(observaciones_de_leyes(ley50, ley95), unitarias_sinteticas())


# --------------------------------------------------------------------------
# Identidad y constantes
# --------------------------------------------------------------------------


def test_el_paquete_exige_exactamente_once_sesiones() -> None:
    assert pp.SESIONES_EXIGIDAS == 11


def test_la_escalera_y_las_familias_se_heredan_del_paquete_07() -> None:
    assert pp.ESCALERA_NS is ep.ESCALERA_NS
    assert pp.FAMILIAS is ep.FAMILIAS
    assert len(pp.ESCALERA_NS) == 16
    assert pp.escalera_estrictamente_creciente()
    assert all(a < b for a, b in pairwise(pp.ESCALERA_NS))


def test_el_objetivo_relativo_y_el_margen_se_heredan_congelados() -> None:
    assert (pp.OBJETIVO_RELATIVO_NUM, pp.OBJETIVO_RELATIVO_DEN) == (1, 5)
    assert pp.MARGEN_M == 1
    assert pp.FACTOR_U == 5


def test_los_documentos_actualizados_son_versiones_nuevas() -> None:
    """No se editan el protocolo ni el Registro anteriores: se versionan.

    Sus blobs los citan las evidencias v0.1, v0.2 y v0.3 ya publicadas.
    """
    nuevos = {pp.PROTOCOLO, pp.REGISTRO}
    anteriores = {pp.PROTOCOLO_ANTERIOR, pp.REGISTRO_ANTERIOR}
    assert len(nuevos | anteriores) == 4, "los cuatro documentos son distintos"
    for nombre in nuevos | anteriores:
        assert (RAIZ / "docs/architecture" / nombre).is_file(), nombre
    # Los NUEVOS se preinscriben; los ANTERIORES no, porque no se tocan.
    for nombre in nuevos:
        assert f"docs/architecture/{nombre}" in pp.ARCHIVOS_PREINSCRITOS, nombre
    for nombre in anteriores:
        assert f"docs/architecture/{nombre}" not in pp.ARCHIVOS_PREINSCRITOS, nombre
    # Y su intangibilidad es un control, no una promesa.
    assert pp.fallos_documentos_de_gobierno(entorno_de_prueba()) == ()


# --------------------------------------------------------------------------
# Separacion de percentiles
# --------------------------------------------------------------------------


def test_cada_percentil_construye_su_propia_curva() -> None:
    """``D50`` no es el peor caso sobre percentiles: es solo P50."""
    observaciones = observaciones_de_leyes(lambda s: s // 20, lambda s: s // 2)
    for escala in pp.ESCALERA_NS:
        d50 = pp.dispersion_de_escala(observaciones, escala, pp.PERCENTIL_P50)
        d95 = pp.dispersion_de_escala(observaciones, escala, pp.PERCENTIL_P95)
        assert d50 == escala // 20
        assert d95 == escala // 2
        assert d50 < d95


def test_la_dispersion_rechaza_percentiles_no_normativos() -> None:
    observaciones = observaciones_de_leyes(lambda s: 1, lambda s: 2)
    with pytest.raises(ValueError, match="percentil no normativo"):
        pp.dispersion_de_familia(observaciones, pp.FAMILIAS[0], pp.ESCALERA_NS[0], "P99")


def test_las_dos_envolventes_son_monotonas_y_cubren_su_suelo() -> None:
    perfil = perfil_sintetico()
    assert pp.envolventes_monotonas(perfil)
    assert pp.envolventes_cubren_el_suelo(perfil)
    assert pp.bandas_no_decrecientes(perfil)


def test_la_envolvente_de_p95_domina_a_la_de_p50() -> None:
    perfil = perfil_sintetico()
    assert pp.p95_domina_a_p50(perfil)


def test_una_envolvente_de_p95_por_debajo_de_p50_se_denuncia() -> None:
    """Si la cola fuese mas estable que el centro, el perfil seria ilegible."""
    perfil = perfil_sintetico(ley50=lambda s: s // 2, ley95=lambda s: s // 20)
    assert not pp.p95_domina_a_p50(perfil)


# --------------------------------------------------------------------------
# El cruce de P50
# --------------------------------------------------------------------------


def test_el_cruce_de_p50_cae_dentro_de_su_intervalo_y_es_continuo() -> None:
    perfil = perfil_sintetico()
    cruce = perfil.cruce_p50
    assert cruce.evaluable
    indice = cruce.indice_escalon
    assert indice is not None
    inferior = 0 if indice == 0 else pp.ESCALERA_NS[indice - 1]
    assert perfil.u50_ns is not None
    assert inferior < perfil.u50_ns <= pp.ESCALERA_NS[indice]
    assert pp.continuidad_p50_exacta(perfil)
    assert pp.FACTOR_U * (perfil.b50_en_u50_ns or 0) == perfil.u50_ns


def test_con_p50_estable_el_cruce_cae_en_el_primer_escalon() -> None:
    """``D50 = 5 % de s`` cabe en el 20 % en todo escalon: el cruce baja del todo."""
    perfil = perfil_sintetico()
    assert perfil.cruce_p50.indice_escalon == 0
    assert perfil.u50_ns == 5 * (pp.ESCALERA_NS[0] // 20)


def test_sin_cruce_de_p50_el_perfil_no_publica_u50() -> None:
    perfil = perfil_sintetico(ley50=lambda s: s // 2)
    assert not perfil.cruce_p50.evaluable
    assert perfil.u50_ns is None
    assert perfil.b50_en_u50_ns is None
    assert not pp.continuidad_p50_exacta(perfil)


# --------------------------------------------------------------------------
# Las dos reglas
# --------------------------------------------------------------------------


def test_p50_relativo_por_encima_de_u50_y_banda_por_debajo() -> None:
    perfil = perfil_sintetico()
    u50 = perfil.u50_ns
    assert u50 is not None
    alto = max(u50, perfil.sm_ns) + 1_000_000
    relativo = pp.evaluar_p50(alto, alto + alto // 10, perfil)
    assert relativo.regimen == pp.REGIMEN_RELATIVO
    assert relativo.banda_ns is None
    assert relativo.resultado == pp.VALIDA
    excesivo = pp.evaluar_p50(alto, alto + alto // 3, perfil)
    assert excesivo.resultado == pp.INVALIDA


def test_p50_no_emite_afirmacion_por_debajo_de_sm() -> None:
    perfil = perfil_sintetico()
    veredicto = pp.evaluar_p50(perfil.sm_ns - 1, perfil.sm_ns, perfil)
    assert veredicto.resultado == pp.NO_EVALUABLE
    assert veredicto.motivo == pp.MOTIVO_BAJO_SM
    assert veredicto.regimen is None


def test_p95_se_evalua_siempre_contra_banda_y_nunca_en_relativo() -> None:
    perfil = perfil_sintetico()
    minimo = max(perfil.sm_ns, pp.ESCALERA_NS[3])
    veredicto = pp.evaluar_p95(minimo, minimo + 1, perfil)
    assert veredicto.regimen == pp.REGIMEN_ABSOLUTO
    assert veredicto.banda_ns == perfil.banda_p95(minimo)
    # Una variacion enorme en relativo pasa si cabe en la banda: P95 ya no
    # esta sujeto al 20 %.
    banda = perfil.banda_p95(minimo)
    assert pp.evaluar_p95(minimo, minimo + banda, perfil).resultado == pp.VALIDA
    assert pp.evaluar_p95(minimo, minimo + banda + 1, perfil).resultado == pp.INVALIDA


def test_p95_es_no_evaluable_bajo_sm_y_sobre_la_mayor_escala() -> None:
    perfil = perfil_sintetico()
    bajo = pp.evaluar_p95(perfil.sm_ns - 1, perfil.sm_ns, perfil)
    assert bajo.resultado == pp.NO_EVALUABLE
    assert bajo.motivo == pp.MOTIVO_BAJO_SM

    alto = pp.evaluar_p95(pp.ESCALERA_NS[-1] + 1, pp.ESCALERA_NS[-1] + 2, perfil)
    assert alto.resultado == pp.NO_EVALUABLE
    assert alto.motivo == pp.MOTIVO_SOBRE_ESCALERA

    justo = pp.evaluar_p95(pp.ESCALERA_NS[-1], pp.ESCALERA_NS[-1], perfil)
    assert justo.resultado != pp.NO_EVALUABLE, "la mayor escala SI esta cubierta"


def test_la_banda_se_consulta_en_el_minimo_del_mismo_percentil() -> None:
    """Regla 4: ``B50`` en ``min_s P50`` y ``B95`` en ``min_s P95``."""
    perfil = perfil_sintetico()
    # Se eligen dos magnitudes que caen en escalones distintos.
    min50 = pp.ESCALERA_NS[3]
    min95 = pp.ESCALERA_NS[8]
    v50 = pp.evaluar_p50(min50, min50, perfil)
    v95 = pp.evaluar_p95(min95, min95, perfil)
    assert v95.banda_ns == perfil.banda_p95(min95)
    assert v95.banda_ns != perfil.banda_p95(min50), "la banda depende del minimo de SU percentil"
    if v50.regimen == pp.REGIMEN_ABSOLUTO:
        assert v50.banda_ns == perfil.banda_p50(min50)


def test_la_banda_toma_el_escalon_superior() -> None:
    perfil = perfil_sintetico()
    for indice, escala in enumerate(pp.ESCALERA_NS):
        assert perfil.banda_p95(escala) == perfil.envolvente_p95.envolvente[indice]
    assert perfil.banda_p95(pp.ESCALERA_NS[0] + 1) == perfil.envolvente_p95.envolvente[1]
    assert perfil.banda_p95(1) == perfil.envolvente_p95.envolvente[0]


# --------------------------------------------------------------------------
# La guarda de sesiones: la regla 5
# --------------------------------------------------------------------------


def test_una_magnitud_con_otro_numero_de_sesiones_no_recibe_veredicto() -> None:
    perfil = perfil_sintetico()
    alto = max(perfil.sm_ns, pp.ESCALERA_NS[5])
    for sesiones in (2, 5, 10, 12, 30):
        veredicto = pp.evaluar_magnitud([alto] * sesiones, [alto] * sesiones, perfil=perfil)
        assert veredicto.resultado == pp.NO_COMPARABLE, sesiones
        assert veredicto.motivo == pp.MOTIVO_SESIONES
        assert veredicto.p50.resultado == pp.NO_EVALUABLE
        assert veredicto.p95.resultado == pp.NO_EVALUABLE
        assert veredicto.p50.banda_ns is None
        assert veredicto.p95.banda_ns is None
        assert pp.registro_por_percentil(veredicto) == pp.NO_COMPARABLE


def test_con_once_sesiones_si_hay_veredicto() -> None:
    perfil = perfil_sintetico()
    alto = max(perfil.sm_ns, pp.ESCALERA_NS[5])
    veredicto = pp.evaluar_magnitud(
        [alto] * pp.SESIONES_EXIGIDAS, [alto] * pp.SESIONES_EXIGIDAS, perfil=perfil
    )
    assert veredicto.resultado != pp.NO_COMPARABLE
    assert veredicto.sesiones == pp.SESIONES_EXIGIDAS


def test_un_perfil_no_puede_declarar_otro_numero_de_sesiones() -> None:
    """``sesiones`` no es un campo libre: la guarda no obedece al perfil.

    Si lo fuese, ``evaluar_magnitud`` exigiria «lo que diga el perfil» en vez
    de los once que exige la regla 5, y bastaria construir un perfil con otro
    numero para que una magnitud de cinco sesiones recibiese veredicto.
    """
    base = perfil_sintetico()
    for sesiones in (0, 5, 10, 12):
        with pytest.raises(pp.PerfilInvalidoError, match="exactamente"):
            pp.Perfil(
                sm_ns=base.sm_ns,
                cruce_p50=base.cruce_p50,
                envolvente_p95=base.envolvente_p95,
                sesiones=sesiones,
            )


def test_la_guarda_de_sesiones_no_depende_del_campo_del_perfil() -> None:
    perfil = perfil_sintetico()
    assert perfil.sesiones == pp.SESIONES_EXIGIDAS
    alto = max(perfil.sm_ns, pp.ESCALERA_NS[5])
    veredicto = pp.evaluar_magnitud([alto] * 5, [alto] * 5, perfil=perfil)
    assert veredicto.resultado == pp.NO_COMPARABLE


def test_una_dispersion_p50_nula_en_el_primer_escalon_se_denuncia() -> None:
    """Caso degenerado que la separacion por percentil hace alcanzable.

    Con ``D50(s_1) = 0`` el cruce se resolveria en ``U50 = 0``, que la
    maquinaria heredada —demostrada para ``E(s_k) > 0``— no admite. Se
    denuncia con un error propio en vez de propagar el invariante violado de
    un modulo congelado que este paquete no puede tocar.
    """
    observaciones = observaciones_de_leyes(lambda s: 0, lambda s: s // 2)
    with pytest.raises(pp.PerfilInvalidoError, match="dispersion P50 nula"):
        pp.derivar_perfil(observaciones, unitarias_sinteticas())


def test_p95_no_aplica_ningun_criterio_relativo_y_se_comprueba() -> None:
    """El control se interroga, no se declara.

    Con ``D95 = s/2`` la banda supera de largo el 20 %: una magnitud con esa
    dispersion exacta es VALIDA pese a variar un 50 %, y con un nanosegundo
    mas es INVALIDA. Eso acredita que lo que vincula es la banda.
    """
    perfil = perfil_sintetico()
    assert pp.p95_sin_umbral_relativo(perfil)
    minimo = pp.ESCALERA_NS[8]
    banda = perfil.banda_p95(minimo)
    dentro = pp.evaluar_p95(minimo, minimo + banda, perfil)
    assert dentro.resultado == pp.VALIDA
    assert dentro.regimen == pp.REGIMEN_ABSOLUTO
    assert not pp.pasa_relativo(minimo, minimo + banda)
    assert pp.evaluar_p95(minimo, minimo + banda + 1, perfil).resultado == pp.INVALIDA

    # Con una banda siempre mas estrecha que el 20 %, el sondeo no puede
    # distinguir un metodo del otro: el control falla cerrado en vez de dar
    # por buena una propiedad que no se ha podido demostrar.
    estrecho = pp.derivar_perfil(
        observaciones_de_leyes(lambda s: s // 20, lambda s: s // 20), unitarias_sinteticas()
    )
    assert not pp.p95_sin_umbral_relativo(estrecho)


def test_la_cobertura_exige_exactamente_once_sesiones_no_al_menos() -> None:
    """Diez fallan por pocas; doce fallan por muchas. Un rango no es comparable."""
    for sesiones in (10, 12):
        observaciones = observaciones_de_leyes(lambda s: s // 20, lambda s: s // 2, sesiones)
        with pytest.raises(pp.PerfilInvalidoError, match="se exigen exactamente"):
            pp.comprobar_cobertura(observaciones)


def test_sm_exige_exactamente_once_sesiones_y_las_tres_sondas() -> None:
    assert pp.calcular_sm(unitarias_sinteticas()) == max(o.p95 for o in unitarias_sinteticas())
    with pytest.raises(pp.PerfilInvalidoError, match="se exigen exactamente"):
        pp.calcular_sm(unitarias_sinteticas(5))
    sin_una = [o for o in unitarias_sinteticas() if o.sonda != pp.SONDAS_UNITARIAS[1]]
    with pytest.raises(pp.PerfilInvalidoError, match="faltan sondas unitarias"):
        pp.calcular_sm(sin_una)


def test_el_invariante_de_percentiles_se_hace_cumplir() -> None:
    perfil = perfil_sintetico()
    n = pp.SESIONES_EXIGIDAS
    with pytest.raises(pp.InvarianteVioladoError, match="invariante violado"):
        pp.evaluar_magnitud([500_000] * n, [400_000] * n, perfil=perfil)
    with pytest.raises(ValueError, match="incoherente"):
        pp.evaluar_magnitud([1] * n, [2] * (n - 1), perfil=perfil)
    with pytest.raises(ValueError, match="faltan percentiles"):
        pp.evaluar_magnitud([], [], perfil=perfil)


# --------------------------------------------------------------------------
# Agregacion
# --------------------------------------------------------------------------


def _vp(percentil: str, resultado: str) -> pp.VeredictoPercentil:
    return pp.VeredictoPercentil(
        percentil=percentil,
        minimo=1,
        maximo=1,
        dispersion=0,
        regimen=None,
        banda_ns=None,
        variacion_por_mil=None,
        resultado=resultado,
        motivo=None,
    )


def test_la_agregacion_reparte_la_exigencia_sin_relajarla() -> None:
    v = pp.VALIDA
    i = pp.INVALIDA
    n = pp.NO_EVALUABLE
    assert pp.agregar(_vp("P50", v), _vp("P95", v)) == v
    # Basta un fallo: una afirmacion NEGATIVA se sostiene con un percentil.
    assert pp.agregar(_vp("P50", i), _vp("P95", v)) == i
    assert pp.agregar(_vp("P50", v), _vp("P95", i)) == i
    assert pp.agregar(_vp("P50", i), _vp("P95", i)) == i
    assert pp.agregar(_vp("P50", n), _vp("P95", i)) == i
    assert pp.agregar(_vp("P50", i), _vp("P95", n)) == i
    # Una afirmacion POSITIVA exige los DOS percentiles: no se declara estable
    # una magnitud cuya cola quedo sin evaluar.
    assert pp.agregar(_vp("P50", n), _vp("P95", v)) == n
    assert pp.agregar(_vp("P50", v), _vp("P95", n)) == n
    assert pp.agregar(_vp("P50", n), _vp("P95", n)) == n


def test_una_magnitud_por_encima_de_la_escalera_no_se_declara_estable() -> None:
    """El caso que motivo endurecer la agregacion.

    Una magnitud mayor que la mayor escala medida deja a P95 ``NO_EVALUABLE``
    por decision de gobierno. Si la agregacion heredase el veredicto de P50,
    el perfil emitiria una afirmacion positiva de estabilidad sobre una
    magnitud cuya cola esta demostrablemente fuera del rango calibrado.
    """
    perfil = perfil_sintetico()
    fuera = pp.ESCALERA_NS[-1] + 1
    p50 = [fuera] * pp.SESIONES_EXIGIDAS
    p95 = [fuera * 2] * pp.SESIONES_EXIGIDAS
    veredicto = pp.evaluar_magnitud(p50, p95, perfil=perfil)
    assert veredicto.p50.resultado == pp.VALIDA
    assert veredicto.p95.resultado == pp.NO_EVALUABLE
    assert veredicto.p95.motivo == pp.MOTIVO_SOBRE_ESCALERA
    assert veredicto.resultado == pp.NO_EVALUABLE


# --------------------------------------------------------------------------
# Custodia
# --------------------------------------------------------------------------


def entorno_de_prueba(
    *,
    limpio: bool = True,
    ancestro: bool = True,
    diff_vacio: bool = True,
    head: str = SHA_FICTICIO,
    sobrescribir: Mapping[str, bytes] | None = None,
    blob_en_commit_divergente: bool = False,
) -> ep.EntornoCustodia:
    extra = dict(sobrescribir or {})

    def leer_bytes(ruta: str) -> bytes:
        if ruta in extra:
            return extra[ruta]
        return (RAIZ / ruta).read_bytes()

    def blob_en_commit(_sha: str, ruta: str) -> str | None:
        if blob_en_commit_divergente:
            return "f" * 40
        return pp.blob_git(leer_bytes(ruta))

    return ep.EntornoCustodia(
        leer_bytes=leer_bytes,
        es_ancestro=lambda _a, _b: ancestro,
        existe_commit=lambda _sha: True,
        head=lambda: head,
        arbol_limpio=lambda: limpio,
        diff_vacio=lambda _a, _b, _rutas: diff_vacio,
        blob_en_commit=blob_en_commit,
    )


def blobs_reales() -> dict[str, str]:
    return {ruta: pp.blob_git((RAIZ / ruta).read_bytes()) for ruta in pp.ARCHIVOS_PREINSCRITOS}


def heredados_reales() -> dict[str, str]:
    return {ruta: pp.blob_git((RAIZ / ruta).read_bytes()) for ruta in pp.ARCHIVOS_HEREDADOS}


def test_custodia_completa_no_encuentra_fallos() -> None:
    assert (
        pp.verificar_custodia(
            entorno_de_prueba(),
            sha_a=SHA_FICTICIO,
            blobs_preinscritos=blobs_reales(),
            blobs_heredados=heredados_reales(),
        )
        == ()
    )


def test_custodia_denuncia_evidencias_anteriores_alteradas() -> None:
    for ruta in pp.EVIDENCIAS_ANTERIORES:
        fallos = pp.fallos_evidencias_anteriores(entorno_de_prueba(sobrescribir={ruta: b"{}"}))
        assert any("alterada" in f and ruta in f for f in fallos), ruta


def test_custodia_denuncia_documentos_de_gobierno_anteriores_alterados() -> None:
    """El protocolo y el Registro ANTERIORES no se tocan: los cita la evidencia."""
    for nombre in (pp.PROTOCOLO_ANTERIOR, pp.REGISTRO_ANTERIOR):
        ruta = f"docs/architecture/{nombre}"
        fallos = pp.fallos_documentos_de_gobierno(
            entorno_de_prueba(sobrescribir={ruta: b"cambiado"})
        )
        assert any("alterado" in f and ruta in f for f in fallos), ruta
    assert pp.fallos_documentos_de_gobierno(entorno_de_prueba()) == ()


def test_custodia_usa_una_fuente_de_verdad_independiente_del_arbol() -> None:
    fallos = pp.verificar_custodia(
        entorno_de_prueba(blob_en_commit_divergente=True),
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=blobs_reales(),
        blobs_heredados=heredados_reales(),
    )
    assert any("difiere del commit de preinscripcion" in f for f in fallos)


def test_custodia_denuncia_no_ancestro_diff_y_heredado_alterado() -> None:
    fallos = pp.verificar_custodia(
        entorno_de_prueba(ancestro=False, diff_vacio=False),
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=blobs_reales(),
        blobs_heredados=heredados_reales(),
    )
    assert any("no es ancestro" in f for f in fallos)
    assert any("diff no vacio" in f for f in fallos)
    fallos = pp.verificar_custodia(
        entorno_de_prueba(),
        sha_a=SHA_FICTICIO,
        blobs_preinscritos=blobs_reales(),
        blobs_heredados={r: "0" * 40 for r in pp.ARCHIVOS_HEREDADOS},
    )
    assert any("blob heredado distinto del preinscrito" in f for f in fallos)


def test_precondiciones_fallan_cerrado() -> None:
    limpio = entorno_de_prueba()
    assert pp.verificar_precondiciones(limpio, sha_a=SHA_FICTICIO, salida_existe=False) == ()
    assert "arbol de trabajo sucio" in pp.verificar_precondiciones(
        entorno_de_prueba(limpio=False), sha_a=SHA_FICTICIO, salida_existe=False
    )
    assert "la ruta de salida ya existe" in pp.verificar_precondiciones(
        limpio, sha_a=SHA_FICTICIO, salida_existe=True
    )
    fallos = pp.verificar_precondiciones(
        entorno_de_prueba(head="a" * 40), sha_a=SHA_FICTICIO, salida_existe=False
    )
    assert any("distinto del commit de preinscripcion" in f for f in fallos)


# --------------------------------------------------------------------------
# Recorrido completo sobre la fuente real congelada
# --------------------------------------------------------------------------


def dependencias_de_prueba(
    *, entorno: ep.EntornoCustodia | None = None, fuente: Mapping[str, Any] | None = None
) -> derivacion.DependenciasDerivacion:
    def _fuente() -> bytes:
        if fuente is not None:
            # Se inyectan BYTES, no un objeto: es la misma lectura que la
            # derivacion hashea, que es justo lo que se quiere poder falsear
            # en las pruebas que comprueban que el blob bloquea.
            return json.dumps(fuente).encode("utf-8")
        return (RAIZ / pp.FUENTE).read_bytes()

    def _linea_base() -> Mapping[str, Any]:
        datos = json.loads((RAIZ / derivacion.RUTA_LINEA_BASE).read_text(encoding="utf-8"))
        assert isinstance(datos, dict)
        return datos

    return derivacion.DependenciasDerivacion(
        entorno_custodia=entorno_de_prueba() if entorno is None else entorno,
        leer_fuente_bytes=_fuente,
        cargar_linea_base=_linea_base,
    )


@pytest.fixture(scope="module")
def perfil_derivado(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    salida = tmp_path_factory.mktemp("perfil") / "perfil.json"
    codigo = derivacion.main(
        ["--execute", "--preinscription-commit", SHA_FICTICIO, "--output", str(salida)],
        dependencias=dependencias_de_prueba(),
    )
    assert codigo == derivacion.CODIGO_OK
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert isinstance(datos, dict)
    return datos


def test_el_perfil_derivado_es_valido(perfil_derivado: dict[str, Any]) -> None:
    assert esquema.fallos_perfil_tolerancias(perfil_derivado) == []
    assert perfil_derivado["derivado_no_medido"] is True
    assert perfil_derivado["sesiones_exigidas"] == 11
    assert perfil_derivado["fuente"]["blob"] == pp.BLOB_FUENTE


def test_la_derivacion_es_determinista(tmp_path: Path) -> None:
    """Misma fuente, mismos bytes. Es lo que una medicion no puede prometer."""
    bytes_por_pasada: list[str] = []
    for indice in range(2):
        salida = tmp_path / f"perfil_{indice}.json"
        assert (
            derivacion.main(
                ["--execute", "--preinscription-commit", SHA_FICTICIO, "--output", str(salida)],
                dependencias=dependencias_de_prueba(),
            )
            == derivacion.CODIGO_OK
        )
        bytes_por_pasada.append(salida.read_text(encoding="utf-8"))
    assert bytes_por_pasada[0] == bytes_por_pasada[1]


def test_el_artefacto_no_traduce_saltos_de_linea(tmp_path: Path) -> None:
    """La garantia declarada es de BYTES, no de texto equivalente.

    Sin ``newline="\\n"`` explicito, Python traduce cada salto a
    ``os.linesep`` y el mismo perfil saldria con CRLF en otra plataforma. Una
    derivacion pura es justo lo que invita a reproducirla en otra maquina.
    """
    salida = tmp_path / "perfil.json"
    assert (
        derivacion.main(
            ["--execute", "--preinscription-commit", SHA_FICTICIO, "--output", str(salida)],
            dependencias=dependencias_de_prueba(),
        )
        == derivacion.CODIGO_OK
    )
    crudo = salida.read_bytes()
    assert b"\r" not in crudo
    assert crudo.endswith(b"\n")


def test_el_control_de_determinismo_es_una_consecuencia_no_una_constante() -> None:
    """Si las dos pasadas difiriesen, el control saldria False y bloquearia."""
    fuente = _fuente_real_mutable()
    linea_base = json.loads((RAIZ / derivacion.RUTA_LINEA_BASE).read_text(encoding="utf-8"))
    argumentos: dict[str, Any] = {
        "sha_a": SHA_FICTICIO,
        "head": SHA_FICTICIO,
        "fuente": fuente,
        "linea_base": linea_base,
        "blobs_preinscritos": {r: "a" * 40 for r in pp.ARCHIVOS_PREINSCRITOS},
        "blobs_heredados": dict(pp.ARCHIVOS_HEREDADOS),
        "fuente_intacta": True,
        "evidencias_intactas": True,
        "gobierno_intacto": True,
        "custodia_ok": True,
    }
    assert (
        derivacion.derivar_documento(**argumentos, determinista=True)["controles_internos"][
            "derivacion_determinista"
        ]
        is True
    )
    fallido = derivacion.derivar_documento(**argumentos, determinista=False)
    assert fallido["controles_internos"]["derivacion_determinista"] is False
    # Y el esquema lo rechaza: el control no depende de que alguien lo mire.
    assert any(
        "controles bloqueantes fallidos" in f for f in esquema.fallos_perfil_tolerancias(fallido)
    )


def test_los_bytes_que_se_hashean_son_los_que_se_derivan(tmp_path: Path) -> None:
    """La fuente se lee UNA vez: el blob acredita los bytes que dan las cifras.

    Con dos lecturas independientes, ``fuente.blob`` afirmaria algo sobre un
    contenido distinto del que produjo D50, E50, D95, E95 y SM.
    """
    leidas: list[bytes] = []

    def _una_vez() -> bytes:
        crudo = (RAIZ / pp.FUENTE).read_bytes()
        leidas.append(crudo)
        return crudo

    base = dependencias_de_prueba()
    deps = derivacion.DependenciasDerivacion(
        entorno_custodia=base.entorno_custodia,
        leer_fuente_bytes=_una_vez,
        cargar_linea_base=base.cargar_linea_base,
    )
    codigo, _ = derivacion.ejecutar_derivacion(
        sha_a=SHA_FICTICIO, salida=tmp_path / "perfil.json", dependencias=deps
    )
    assert codigo == derivacion.CODIGO_OK
    assert len(leidas) == 1
    assert pp.blob_git(leidas[0]) == pp.BLOB_FUENTE


def test_el_perfil_no_republica_la_medicion(perfil_derivado: dict[str, Any]) -> None:
    """Duplicar la fuente permitiria que divergiesen."""
    for prohibido in ("escalas", "sondas_unitarias", "entorno", "procesos", "diagnosticos"):
        assert prohibido not in perfil_derivado


def test_los_percentiles_se_recomputan_desde_los_vectores() -> None:
    """El perfil usa los vectores, no las cifras que la fuente publica."""
    fuente = json.loads((RAIZ / pp.FUENTE).read_text(encoding="utf-8"))
    observaciones, _ = derivacion.observaciones_desde_fuente(fuente)
    assert derivacion.percentiles_de_la_fuente_coinciden(fuente, observaciones)

    manipulada = deepcopy(fuente)
    manipulada["escalas"][0]["p95_ns"] += 1
    observaciones2, _ = derivacion.observaciones_desde_fuente(manipulada)
    assert not derivacion.percentiles_de_la_fuente_coinciden(manipulada, observaciones2)
    # Y aun asi el percentil derivado sale del vector, no de la cifra alterada.
    assert observaciones2[0].p95 == observaciones[0].p95


def test_el_perfil_publica_las_dos_curvas_y_su_relacion(
    perfil_derivado: dict[str, Any],
) -> None:
    curva50 = perfil_derivado["p50"]["curva"]
    curva95 = perfil_derivado["p95"]["curva"]
    assert len(curva50) == len(curva95) == len(pp.ESCALERA_NS)
    e50 = [f["envolvente_ns"] for f in curva50]
    e95 = [f["envolvente_ns"] for f in curva95]
    assert e50 == sorted(e50)
    assert e95 == sorted(e95)
    assert all(a <= b for a, b in zip(e50, e95, strict=True))
    assert all(f["banda_ns"] == f["envolvente_ns"] for f in curva50 + curva95)


def test_p95_del_perfil_no_declara_umbral_relativo(perfil_derivado: dict[str, Any]) -> None:
    p95 = perfil_derivado["p95"]
    assert p95["sin_umbral_relativo"] is True
    assert p95["objetivo_relativo_aplicable"] is False
    for prohibido in ("u95_ns", "umbral_ns", "objetivo_relativo", "factor_u"):
        assert prohibido not in p95
    assert all("sostenible" not in f for f in p95["curva"])


def test_el_contraste_historico_no_emite_veredicto(perfil_derivado: dict[str, Any]) -> None:
    """La linea base tiene cinco sesiones: la regla 5 lo impide."""
    contraste = perfil_derivado["contraste_no_comparable"]
    assert contraste["sesiones"] == derivacion.SESIONES_LINEA_BASE == 5
    assert contraste["magnitudes"]
    for entrada in contraste["magnitudes"]:
        assert entrada["sesiones"] == 5
        assert entrada["resultado"] == pp.NO_COMPARABLE
        assert entrada["motivo"] == pp.MOTIVO_SESIONES
        assert entrada["banda_p50_que_le_corresponderia_ns"] is None
        assert entrada["banda_p95_que_le_corresponderia_ns"] is None


def test_todos_los_controles_bloqueantes_pasan(perfil_derivado: dict[str, Any]) -> None:
    controles = perfil_derivado["controles_internos"]
    assert set(controles) == set(pp.CONTROLES_BLOQUEANTES)
    assert all(controles[c] is True for c in pp.CONTROLES_BLOQUEANTES)


def test_no_se_deriva_con_el_arbol_sucio_o_la_salida_existente(tmp_path: Path) -> None:
    salida = tmp_path / "perfil.json"
    codigo, fallos = derivacion.ejecutar_derivacion(
        sha_a=SHA_FICTICIO,
        salida=salida,
        dependencias=dependencias_de_prueba(entorno=entorno_de_prueba(limpio=False)),
    )
    assert codigo == derivacion.CODIGO_BLOQUEADO
    assert any("sucio" in f for f in fallos)
    assert not salida.exists()

    salida.write_text("evidencia ajena", encoding="utf-8")
    codigo, fallos = derivacion.ejecutar_derivacion(
        sha_a=SHA_FICTICIO, salida=salida, dependencias=dependencias_de_prueba()
    )
    assert codigo == derivacion.CODIGO_BLOQUEADO
    assert any("ya existe" in f for f in fallos)
    assert salida.read_text(encoding="utf-8") == "evidencia ajena"


def test_una_evidencia_anterior_alterada_bloquea_la_derivacion(tmp_path: Path) -> None:
    entorno = entorno_de_prueba(
        sobrescribir={"artifacts/adr002_tolerances/suelo_medicion_v0.2.json": b"[]"}
    )
    codigo, fallos = derivacion.ejecutar_derivacion(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "perfil.json",
        dependencias=dependencias_de_prueba(entorno=entorno),
    )
    assert codigo == derivacion.CODIGO_BLOQUEADO
    assert any("evidencia anterior alterada" in f for f in fallos)


def test_una_fuente_con_otro_blob_bloquea_la_derivacion(tmp_path: Path) -> None:
    entorno = entorno_de_prueba(sobrescribir={pp.FUENTE: b'{"escalas": []}'})
    codigo, fallos = derivacion.ejecutar_derivacion(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "perfil.json",
        dependencias=dependencias_de_prueba(entorno=entorno),
    )
    assert codigo == derivacion.CODIGO_BLOQUEADO
    assert any("alterada" in f or "blob" in f for f in fallos)


def _fuente_real_mutable() -> dict[str, Any]:
    datos = json.loads((RAIZ / pp.FUENTE).read_text(encoding="utf-8"))
    assert isinstance(datos, dict)
    return datos


def test_una_fuente_con_menos_de_once_sesiones_bloquea() -> None:
    """La cobertura se comprueba sobre la fuente ya interpretada.

    No se ejercita por ``ejecutar_derivacion`` porque ahi bloquea antes, y con
    razon, la guarda de blob: cualquier fuente distinta de la congelada deja
    de ser la fuente. Lo que se comprueba aqui es la regla, no la custodia.
    """
    fuente = _fuente_real_mutable()
    victima = fuente["escalas"][0]
    fuente["escalas"] = [
        e
        for e in fuente["escalas"]
        if not (
            e["familia"] == victima["familia"]
            and e["escala_ns"] == victima["escala_ns"]
            and e["pid"] == victima["pid"]
        )
    ]
    observaciones, unitarias = derivacion.observaciones_desde_fuente(fuente)
    with pytest.raises(pp.PerfilInvalidoError, match="se exigen exactamente"):
        pp.derivar_perfil(observaciones, unitarias)


def test_una_fuente_con_una_sesion_duplicada_bloquea() -> None:
    """Once identificadores no bastan: hacen falta once OBSERVACIONES.

    Con un vector repetido el rango se tomaria sobre doce muestras aunque los
    identificadores siguiesen siendo once, y su esperanza ya no seria la de
    las bandas.
    """
    fuente = _fuente_real_mutable()
    fuente["escalas"] = [*fuente["escalas"], dict(fuente["escalas"][0])]
    observaciones, unitarias = derivacion.observaciones_desde_fuente(fuente)
    with pytest.raises(pp.PerfilInvalidoError, match="una por sesion"):
        pp.derivar_perfil(observaciones, unitarias)


def test_una_escalera_medida_por_sesiones_distintas_bloquea() -> None:
    """«Once sesiones completas» exige que sean LAS MISMAS en toda la escalera."""
    fuente = _fuente_real_mutable()
    ultima = pp.ESCALERA_NS[-1]
    for entrada in fuente["escalas"]:
        if entrada["escala_ns"] == ultima and entrada["familia"] == pp.FAMILIAS[0]:
            entrada["pid"] = entrada["pid"] + 100_000
    observaciones, unitarias = derivacion.observaciones_desde_fuente(fuente)
    with pytest.raises(pp.PerfilInvalidoError, match="las mismas sesiones"):
        pp.derivar_perfil(observaciones, unitarias)


def test_una_fuente_alterada_no_llega_siquiera_a_interpretarse(tmp_path: Path) -> None:
    """Una fuente distinta de la congelada bloquea por blob, antes de parsearse."""
    fuente = _fuente_real_mutable()
    fuente["escalas"] = fuente["escalas"][:-1]
    codigo, fallos = derivacion.ejecutar_derivacion(
        sha_a=SHA_FICTICIO,
        salida=tmp_path / "perfil.json",
        dependencias=dependencias_de_prueba(fuente=fuente),
    )
    assert codigo == derivacion.CODIGO_BLOQUEADO
    assert any("no coincide con su blob congelado" in f for f in fallos)


def test_la_escritura_no_destruye_un_fichero_ajeno(tmp_path: Path) -> None:
    salida = tmp_path / "perfil.json"
    salida.write_text("evidencia ajena", encoding="utf-8")
    with pytest.raises(FileExistsError):
        derivacion.escribir_json_atomico(salida, {"a": 1})
    assert salida.read_text(encoding="utf-8") == "evidencia ajena"
    assert list(tmp_path.iterdir()) == [salida]


def test_sin_execute_no_escribe_nada(capsys: pytest.CaptureFixture[str]) -> None:
    assert derivacion.main([]) == derivacion.CODIGO_SIN_EXECUTE
    assert "no escribe sin --execute" in capsys.readouterr().out
    assert derivacion.main(["--plan"]) == derivacion.CODIGO_OK
    salida = capsys.readouterr().out
    assert "11" in salida
    assert derivacion.main(["--execute"]) == derivacion.CODIGO_BLOQUEADO


# --------------------------------------------------------------------------
# Validador: mutaciones
# --------------------------------------------------------------------------


def _mutado(doc: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(doc))


def test_el_validador_es_total_y_nunca_lanza() -> None:
    basuras: tuple[Any, ...] = (None, [], "texto", 3, {"documento": object()})
    for basura in basuras:
        assert esquema.fallos_perfil_tolerancias(basura)


def test_el_validador_exige_todas_las_secciones(perfil_derivado: dict[str, Any]) -> None:
    for seccion in esquema.SECCIONES_OBLIGATORIAS:
        doc = _mutado(perfil_derivado)
        del doc[seccion]
        assert any(seccion in f for f in esquema.fallos_perfil_tolerancias(doc)), seccion


def test_el_validador_rechaza_identidad_alterada(perfil_derivado: dict[str, Any]) -> None:
    for campo, valor in (
        ("version_esquema", "otra"),
        ("estado", "APROBADO"),
        ("acta", "otra.md"),
        ("protocolo", pp.PROTOCOLO_ANTERIOR),
        ("registro", pp.REGISTRO_ANTERIOR),
        ("paquete", "otro"),
        ("derivado_no_medido", False),
        ("sesiones_exigidas", 5),
    ):
        doc = _mutado(perfil_derivado)
        doc[campo] = valor
        assert esquema.fallos_perfil_tolerancias(doc), campo


def test_el_validador_rechaza_un_u50_inventado(perfil_derivado: dict[str, Any]) -> None:
    doc = _mutado(perfil_derivado)
    doc["p50"]["u50_ns"] = (doc["p50"]["u50_ns"] or 0) + 5
    assert any(
        "no coincide con el cruce recomputado" in f for f in esquema.fallos_perfil_tolerancias(doc)
    )


def test_el_validador_rechaza_una_envolvente_maquillada(
    perfil_derivado: dict[str, Any],
) -> None:
    for percentil in ("p50", "p95"):
        doc = _mutado(perfil_derivado)
        doc[percentil]["curva"][5]["envolvente_ns"] += 1
        fallos = esquema.fallos_perfil_tolerancias(doc)
        assert any("maximo acumulado" in f or "banda debe ser la envolvente" in f for f in fallos)


def test_el_validador_rechaza_una_envolvente_no_monotona(
    perfil_derivado: dict[str, Any],
) -> None:
    doc = _mutado(perfil_derivado)
    curva = doc["p95"]["curva"]
    curva[-1]["envolvente_ns"] = 1
    curva[-1]["banda_ns"] = 1
    curva[-1]["razon_envolvente_por_mil"] = pp.razon_por_mil(1, curva[-1]["escala_ns"])
    fallos = esquema.fallos_perfil_tolerancias(doc)
    assert any("monotona" in f or "maximo acumulado" in f for f in fallos)


def test_el_validador_rechaza_una_banda_distinta_de_la_envolvente(
    perfil_derivado: dict[str, Any],
) -> None:
    doc = _mutado(perfil_derivado)
    doc["p95"]["curva"][2]["banda_ns"] += 1
    assert any(
        "la banda debe ser la envolvente" in f for f in esquema.fallos_perfil_tolerancias(doc)
    )


def test_el_validador_rechaza_un_umbral_relativo_para_p95(
    perfil_derivado: dict[str, Any],
) -> None:
    for campo, valor in (
        ("sin_umbral_relativo", False),
        ("objetivo_relativo_aplicable", True),
        ("u95_ns", 1_000),
        ("objetivo_relativo", "1/5"),
    ):
        doc = _mutado(perfil_derivado)
        doc["p95"][campo] = valor
        assert esquema.fallos_perfil_tolerancias(doc), campo


def test_el_validador_rechaza_p95_con_sostenibilidad(perfil_derivado: dict[str, Any]) -> None:
    doc = _mutado(perfil_derivado)
    doc["p95"]["curva"][0]["sostenible"] = True
    assert any("no tiene umbral relativo" in f for f in esquema.fallos_perfil_tolerancias(doc))


def test_el_validador_rechaza_e95_por_debajo_de_e50() -> None:
    """Si la cola fuese mas estable que el centro, el perfil seria ilegible."""
    e50 = ep.Envolvente(tuple([100] * 16), tuple([100] * 16))
    e95 = ep.Envolvente(tuple([10] * 16), tuple([10] * 16))
    perfil = pp.Perfil(
        sm_ns=1,
        cruce_p50=ep.resolver_cruce(e50),
        envolvente_p95=e95,
        sesiones=pp.SESIONES_EXIGIDAS,
    )
    assert not pp.p95_domina_a_p50(perfil)
    doc = {
        "p50": {
            "curva": [
                {"escala_ns": s, "dispersion_ns": 100, "envolvente_ns": 100} for s in pp.ESCALERA_NS
            ]
        },
        "p95": {
            "curva": [
                {"escala_ns": s, "dispersion_ns": 10, "envolvente_ns": 10} for s in pp.ESCALERA_NS
            ]
        },
    }
    fallos = esquema._fallos_relacion_entre_percentiles(doc)
    assert any("E95 queda por debajo de E50" in f for f in fallos)


def test_el_validador_hace_cumplir_la_regla_de_sesiones(
    perfil_derivado: dict[str, Any],
) -> None:
    """Emitir un veredicto con otro numero de sesiones es la mutacion critica."""
    doc = _mutado(perfil_derivado)
    doc["contraste_no_comparable"]["magnitudes"][0]["resultado"] = pp.VALIDA
    fallos = esquema.fallos_perfil_tolerancias(doc)
    assert any("y aun asi se emitio el veredicto" in f for f in fallos)

    doc = _mutado(perfil_derivado)
    doc["contraste_no_comparable"]["magnitudes"][0]["banda_p95_que_le_corresponderia_ns"] = 1
    assert any(
        "no se publica banda para una magnitud no comparable" in f
        for f in esquema.fallos_perfil_tolerancias(doc)
    )

    doc = _mutado(perfil_derivado)
    doc["contraste_no_comparable"]["sesiones_exigidas"] = 5
    assert esquema.fallos_perfil_tolerancias(doc)


def test_el_validador_cruza_las_dos_declaraciones_de_sesiones(
    perfil_derivado: dict[str, Any],
) -> None:
    """El documento declara el numero de sesiones dos veces: se contrastan.

    Sin cruzarlas, bastaria con que la entrada mintiese sobre su propio
    numero para que la regla 5 no se activase nunca.
    """
    doc = _mutado(perfil_derivado)
    doc["contraste_no_comparable"]["magnitudes"][0]["sesiones"] = pp.SESIONES_EXIGIDAS
    fallos = esquema.fallos_perfil_tolerancias(doc)
    assert any("la cabecera de su misma fuente declara" in f for f in fallos)

    doc = _mutado(perfil_derivado)
    doc["contraste_no_comparable"]["sesiones"] = "cinco"
    assert any(
        "contraste_no_comparable.sesiones debe ser un entero" in f
        for f in esquema.fallos_perfil_tolerancias(doc)
    )


def test_el_validador_recomputa_el_veredicto_de_una_magnitud_comparable(
    perfil_derivado: dict[str, Any],
) -> None:
    """Con once sesiones SI hay veredicto, y el validador lo recomputa.

    Antes, toda la comprobacion vivia dentro de la rama «n distinto de once»:
    una entrada que declarase once quedaba con su `resultado` sin auditar.
    """
    doc = _mutado(perfil_derivado)
    entrada = doc["contraste_no_comparable"]["magnitudes"][0]
    entrada["sesiones"] = pp.SESIONES_EXIGIDAS
    entrada["motivo"] = None
    doc["contraste_no_comparable"]["sesiones"] = pp.SESIONES_EXIGIDAS
    doc["contraste_no_comparable"]["fuente"] = "otra"

    # Con el veredicto que el propio perfil recomputa, la entrada es conforme;
    # el resto de entradas siguen siendo de cinco sesiones y no se tocan.
    perfil = esquema._perfil_desde_documento(doc)
    assert perfil is not None
    veredicto = pp.evaluar_magnitud(
        [entrada["min_p50_ns"], entrada["max_p50_ns"]] + [entrada["min_p50_ns"]] * 9,
        [entrada["min_p95_ns"], entrada["max_p95_ns"]] + [entrada["min_p95_ns"]] * 9,
        perfil=perfil,
    )
    entrada["resultado"] = veredicto.resultado
    entrada["registro"] = pp.registro_por_percentil(veredicto)
    assert esquema._fallos_contraste(doc) == []

    # Y cualquier otro veredicto es un fallo.
    entrada["resultado"] = pp.VALIDA if veredicto.resultado != pp.VALIDA else pp.INVALIDA
    assert any(
        "distinto del recomputado" in f or "registro por percentil no recomputa" in f
        for f in esquema._fallos_contraste(doc)
    )


def test_el_esquema_cierra_los_conjuntos_de_campos(perfil_derivado: dict[str, Any]) -> None:
    """Una lista negra se esquiva rebautizando; un conjunto cerrado, no."""
    for seccion in ("p50", "p95", "metodo", "preinscripcion", "custodia", "no_autoriza"):
        doc = _mutado(perfil_derivado)
        doc[seccion]["umbral_disfrazado"] = 1
        assert any(
            "ajenos al esquema" in f or "ajenas al esquema" in f
            for f in esquema.fallos_perfil_tolerancias(doc)
        ), seccion

    doc = _mutado(perfil_derivado)
    doc["controles_internos"]["control_inventado"] = True
    assert any("ajenos al esquema" in f for f in esquema.fallos_perfil_tolerancias(doc))

    doc = _mutado(perfil_derivado)
    doc["p95"]["curva"][0]["umbral_disfrazado"] = 1
    assert any("ajenos al esquema" in f for f in esquema.fallos_perfil_tolerancias(doc))

    doc = _mutado(perfil_derivado)
    doc["contraste_no_comparable"]["magnitudes"][0]["extra"] = 1
    assert any("ajenos al esquema" in f for f in esquema.fallos_perfil_tolerancias(doc))


def test_el_validador_rechaza_dispersiones_del_contraste_incoherentes(
    perfil_derivado: dict[str, Any],
) -> None:
    doc = _mutado(perfil_derivado)
    doc["contraste_no_comparable"]["magnitudes"][0]["dispersion_p95_ns"] += 1
    assert any("no recomputa" in f for f in esquema.fallos_perfil_tolerancias(doc))


def test_el_validador_rechaza_publicar_con_controles_fallidos(
    perfil_derivado: dict[str, Any],
) -> None:
    doc = _mutado(perfil_derivado)
    doc["controles_internos"]["custodia_verificada"] = False
    assert any(
        "controles bloqueantes fallidos" in f for f in esquema.fallos_perfil_tolerancias(doc)
    )
    doc = _mutado(perfil_derivado)
    del doc["controles_internos"]["derivacion_determinista"]
    assert any("control bloqueante ausente" in f for f in esquema.fallos_perfil_tolerancias(doc))


def test_el_validador_rechaza_negaciones_alteradas(perfil_derivado: dict[str, Any]) -> None:
    assert len(esquema.NEGACIONES_OBLIGATORIAS) == 8
    for clave in esquema.NEGACIONES_OBLIGATORIAS:
        doc = _mutado(perfil_derivado)
        doc["no_autoriza"][clave] = True
        assert any(clave in f for f in esquema.fallos_perfil_tolerancias(doc))
        doc = _mutado(perfil_derivado)
        del doc["no_autoriza"][clave]
        assert any(clave in f for f in esquema.fallos_perfil_tolerancias(doc))


def test_el_validador_rechaza_custodia_o_blobs_alterados(
    perfil_derivado: dict[str, Any],
) -> None:
    for clave in (
        "sha_a_es_ancestro",
        "diff_preinscritos_vacio",
        "evidencias_anteriores_intactas",
        "documentos_de_gobierno_intactos",
    ):
        doc = _mutado(perfil_derivado)
        doc["custodia"][clave] = False
        assert esquema.fallos_perfil_tolerancias(doc), clave
    for campo in (
        "blob_fuente",
        "blob_protocolo_anterior",
        "blob_registro_anterior",
    ):
        doc = _mutado(perfil_derivado)
        doc["preinscripcion"][campo] = "0" * 40
        assert esquema.fallos_perfil_tolerancias(doc), campo
    doc = _mutado(perfil_derivado)
    doc["preinscripcion"]["blobs_evidencias_anteriores"] = {}
    assert any("blobs_evidencias_anteriores" in f for f in esquema.fallos_perfil_tolerancias(doc))


def test_el_validador_exige_forma_de_sha(perfil_derivado: dict[str, Any]) -> None:
    for ruta, valor in (
        (("preinscripcion", "commit_a"), ""),
        (("preinscripcion", "head_en_derivacion"), "no-es-un-sha"),
        (("custodia", "head"), "0" * 39),
        (("fuente", "commit"), "corto"),
    ):
        doc = _mutado(perfil_derivado)
        doc[ruta[0]][ruta[1]] = valor
        assert any("SHA" in f for f in esquema.fallos_perfil_tolerancias(doc)), ruta


def test_el_validador_rechaza_republicar_la_medicion(
    perfil_derivado: dict[str, Any],
) -> None:
    # El conjunto de secciones esta CERRADO: no hay lista de nombres que
    # esquivar rebautizando la seccion.
    for prohibido in ("escalas", "sondas_unitarias", "entorno", "procesos", "diagnosticos", "x"):
        doc = _mutado(perfil_derivado)
        doc[prohibido] = []
        assert any(
            "secciones ajenas al esquema" in f for f in esquema.fallos_perfil_tolerancias(doc)
        ), prohibido


# --------------------------------------------------------------------------
# Integridad de la preinscripcion
# --------------------------------------------------------------------------


def test_los_ocho_ficheros_preinscritos_existen_y_parsean() -> None:
    assert len(pp.ARCHIVOS_PREINSCRITOS) == 8
    for ruta in pp.ARCHIVOS_PREINSCRITOS:
        completa = RAIZ / ruta
        assert completa.is_file(), ruta
        if completa.suffix == ".py":
            ast.parse(completa.read_text(encoding="utf-8"), filename=str(completa))


def test_este_fichero_esta_entre_los_preinscritos() -> None:
    relativa = Path(__file__).resolve().relative_to(RAIZ).as_posix()
    assert relativa in pp.ARCHIVOS_PREINSCRITOS


def test_las_seis_evidencias_anteriores_siguen_intactas() -> None:
    assert len(pp.EVIDENCIAS_ANTERIORES) == 6
    for ruta, blob in pp.EVIDENCIAS_ANTERIORES.items():
        completa = RAIZ / ruta
        assert completa.is_file(), ruta
        assert pp.blob_git(completa.read_bytes()) == blob, ruta


def test_la_maquinaria_heredada_esta_intacta() -> None:
    for ruta, blob in pp.ARCHIVOS_HEREDADOS.items():
        assert pp.blob_git((RAIZ / ruta).read_bytes()) == blob, ruta


def test_derivar_no_mide_nada() -> None:
    """Ni cronometro, ni procesos, ni SQLite en el camino de derivacion."""
    for nombre in ("profile_protocol.py", "derive_profile.py", "schema_profile_v0_1.py"):
        ruta = RAIZ / "experiments/adr002/tolerances" / nombre
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
        importados: set[str] = set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                importados.update(a.name.split(".")[0] for a in nodo.names)
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                importados.add(nodo.module.split(".")[0])
        assert "time" not in importados, nombre
        assert "sqlite3" not in importados, nombre
        assert "random" not in importados, nombre
        texto = ruta.read_text(encoding="utf-8")
        assert "perf_counter" not in texto, nombre


def test_importar_los_modulos_no_deriva_ni_escribe(tmp_path: Path) -> None:
    guion = (
        f"import sys; sys.path.insert(0, {str(RAIZ)!r});"
        "from experiments.adr002.tolerances import profile_protocol,"
        " derive_profile, schema_profile_v0_1;"
        "print('ok')"
    )
    completado = subprocess.run(
        [sys.executable, "-c", guion],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completado.returncode == 0, completado.stderr
    assert completado.stdout.strip() == "ok"
    assert list(tmp_path.iterdir()) == []


def test_ninguna_prueba_deja_residuos_en_artifacts() -> None:
    """El perfil real solo lo escribe el commit 2, no las pruebas."""
    presentes = {p.name for p in (RAIZ / "artifacts/adr002_tolerances").iterdir()}
    assert not any(n.endswith(".tmp") for n in presentes)
