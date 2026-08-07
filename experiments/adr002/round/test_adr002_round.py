"""La ronda primaria, preinscrita: que esté completa y que **no se ejecute**.

Lo que estas pruebas vigilan no es una medición —no hay ninguna—, sino que el
plan esté congelado antes de medir y que la guarda de autorización sea real.

La comprobación central es de resta: sobre el repositorio real, la única
precondición sin satisfacer debe ser **la autorización**. Si alguna otra
fallara, la fase previa al benchmark no estaría cerrada; y si no fallara
ninguna, la guarda no estaría guardando nada.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Final

import pytest
from experiments.adr002.cards import card_protocol as cp
from experiments.adr002.round import round_protocol as rp
from experiments.adr002.round import run_round

RAIZ: Final = Path(__file__).resolve().parents[3]
SHA: Final = "a" * 40

ACTA_DE_AUTORIZACION: Final = f"docs/architecture/{rp.ACTA_DE_AUTORIZACION}"


def _entorno(
    *, ausentes: Sequence[str] = (), alterados: Sequence[str] = (), presentes: Sequence[str] = ()
) -> rp.EntornoCustodia:
    """Entorno sobre el repositorio real, con ausencias y alteraciones fingidas.

    ``presentes`` finge que existe algo que no existe: es como se comprueba que
    la guarda de autorización responde al acta y no a otra cosa.
    """

    def leer(ruta: str) -> bytes:
        if ruta in ausentes:
            raise OSError(ruta)
        if ruta in alterados:
            return b"alterado"
        if ruta in presentes:
            return b"presente"
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


def _fichas(**sustituciones: cp.FichaConfirmada) -> list[cp.FichaConfirmada]:
    """Las cinco fichas vigentes tal como la ronda las preinscribe."""
    confirmadas = []
    for participante in rp.PARTICIPANTES:
        if participante in sustituciones:
            confirmadas.append(sustituciones[participante])
            continue
        version, huella = rp.FICHAS_VIGENTES[participante]
        confirmadas.append(
            cp.FichaConfirmada(
                candidato=participante,
                version=version,
                huella=huella,
                commit_de_entrada=SHA,
                estado=cp.ESTADO_CONGELADA,
            )
        )
    return confirmadas


# --------------------------------------------------------------------------
# A. La guarda de autorización
# --------------------------------------------------------------------------


def test_la_unica_precondicion_pendiente_es_la_autorizacion() -> None:
    """La comprobación central de la fase previa al benchmark.

    Sobre el repositorio real: todo lo demás está en su sitio, y lo único que
    falta es el acto de gobierno. Si esta prueba empezara a listar más fallos,
    la fase no estaría cerrada.
    """
    resultado = run_round.comprobar(run_round.dependencias_reales(RAIZ))
    assert [f.split(":")[0] for f in resultado.fallos] == [rp.MOTIVO_SIN_AUTORIZACION]


def test_con_el_acta_presente_no_queda_ninguna_precondicion() -> None:
    """Fingir el acta desbloquea, y sólo eso: el documento **es** la guarda."""
    precondiciones = rp.comprobar_precondiciones(
        _entorno(presentes=[ACTA_DE_AUTORIZACION]),
        fichas_congeladas=_fichas(),
    )
    assert precondiciones.fallos == ()
    assert precondiciones.permite_ejecutar is True


def test_sin_el_acta_se_bloquea() -> None:
    precondiciones = rp.comprobar_precondiciones(
        _entorno(ausentes=[ACTA_DE_AUTORIZACION]), fichas_congeladas=_fichas()
    )
    assert any(rp.MOTIVO_SIN_AUTORIZACION in fallo for fallo in precondiciones.fallos)


def test_el_acta_de_autorizacion_no_existe_en_el_repositorio() -> None:
    """Si algún día existiera sin decisión del usuario, esto lo delata.

    Esta prueba y `test_la_unica_precondicion_pendiente_es_la_autorizacion`
    están escritas para **caducar**, y no en silencio: el día que llegue la
    autorización, ambas fallarán y habrá que reescribirlas en el mismo commit
    que materialice el acta. Eso es lo que se busca. Cambiarlas antes, o
    borrarlas, sería quitar el único control que hoy distingue «preparado» de
    «autorizado».
    """
    assert not (RAIZ / ACTA_DE_AUTORIZACION).exists()


def test_el_recorrido_devuelve_codigo_de_bloqueo() -> None:
    codigo = run_round.main(["--check"], dependencias=run_round.dependencias_reales(RAIZ))
    assert codigo == run_round.CODIGO_BLOQUEADO


def test_no_hay_bandera_que_salte_la_guarda() -> None:
    """La autorización es un documento, no un argumento de línea de órdenes."""
    codigo = run_round.main(["--plan"], dependencias=run_round.dependencias_reales(RAIZ))
    assert codigo == run_round.CODIGO_OK
    fuente = (RAIZ / "experiments/adr002/round/run_round.py").read_text(encoding="utf-8")
    for prohibida in ("--force", "--yes", "--run", "--execute", "--ejecutar", "--sin-guarda"):
        assert prohibida not in fuente, prohibida


# --------------------------------------------------------------------------
# B. Los cinco participantes, sin reducción
# --------------------------------------------------------------------------


def test_la_ronda_son_los_cinco_participantes() -> None:
    assert rp.PARTICIPANTES == ("T0-control", "ADR002-A", "ADR002-B", "ADR002-C", "ADR002-D")
    assert rp.PARTICIPANTES == cp.CANDIDATOS
    assert set(rp.FICHAS_VIGENTES) == set(rp.PARTICIPANTES)


@pytest.mark.parametrize("ausente", rp.PARTICIPANTES)
def test_retirar_un_participante_bloquea(ausente: str) -> None:
    """La Resolución de la partición §2.2 prohíbe reducir la ronda."""
    reducida = tuple(p for p in rp.PARTICIPANTES if p != ausente)
    fallos = rp.fallos_de_reduccion(reducida)
    assert any(ausente in fallo for fallo in fallos)


def test_anadir_un_participante_ajeno_bloquea() -> None:
    fallos = rp.fallos_de_reduccion((*rp.PARTICIPANTES, "ADR002-Z"))
    assert any("ADR002-Z" in fallo for fallo in fallos)


def test_cada_candidato_tiene_acta_de_preparacion_y_el_control_no() -> None:
    """Congelar es un acto técnico; preparar es un acto de gobierno."""
    assert set(rp.ACTAS_DE_PREPARACION) == set(cp.ALTERNATIVAS)
    assert cp.CONTROL not in rp.ACTAS_DE_PREPARACION
    for acta in set(rp.ACTAS_DE_PREPARACION.values()):
        assert (RAIZ / "docs/architecture" / acta).exists(), acta


def test_una_acta_de_preparacion_ausente_bloquea() -> None:
    acta = rp.ACTAS_DE_PREPARACION["ADR002-D"]
    fallos = rp.fallos_de_preparacion(_entorno(ausentes=[f"docs/architecture/{acta}"]))
    assert any("ADR002-D" in fallo for fallo in fallos)


# --------------------------------------------------------------------------
# C. Las fichas: una por participante, con la huella declarada
# --------------------------------------------------------------------------


@pytest.mark.parametrize("participante", rp.PARTICIPANTES)
def test_la_huella_preinscrita_es_la_del_repositorio(participante: str) -> None:
    """No basta con declarar una huella: tiene que ser la que la ficha tiene."""
    version, huella = rp.FICHAS_VIGENTES[participante]
    ruta = RAIZ / f"artifacts/adr002_cards/ficha_{participante}_v{version}.json"
    ficha = json.loads(ruta.read_text(encoding="utf-8"))
    assert ficha["estado"] == cp.ESTADO_CONGELADA
    assert ficha["congelacion"]["huella"] == huella
    assert cp.huella_canonica(ficha) == huella


def test_una_huella_distinta_de_la_preinscrita_bloquea() -> None:
    """Medir bajo una ficha que cambió tras declarar el plan no es utilizable."""
    impostora = cp.FichaConfirmada(
        candidato="ADR002-D",
        version=2,
        huella="f" * 40,
        commit_de_entrada=SHA,
        estado=cp.ESTADO_CONGELADA,
    )
    fallos = rp.fallos_de_fichas(_fichas(**{"ADR002-D": impostora}))
    assert any("ADR002-D" in fallo for fallo in fallos)


def test_un_participante_sin_ficha_congelada_bloquea() -> None:
    sin_c = [f for f in _fichas() if f.candidato != "ADR002-C"]
    fallos = rp.fallos_de_fichas(sin_c)
    assert any("ADR002-C" in fallo for fallo in fallos)


def test_dos_fichas_congeladas_del_mismo_participante_bloquean() -> None:
    duplicada = cp.FichaConfirmada(
        candidato="ADR002-A",
        version=4,
        huella="1" * 40,
        commit_de_entrada=SHA,
        estado=cp.ESTADO_CONGELADA,
    )
    fallos = rp.fallos_de_fichas([*_fichas(), duplicada])
    assert any("ADR002-A" in fallo and "2 fichas" in fallo for fallo in fallos)


# --------------------------------------------------------------------------
# D. La entrada congelada
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "artefactos",
    [rp.CORPUS_CONGELADO, rp.LINEA_BASE_REDERIVADA, rp.PERFIL_Y_SUELO],
    ids=["corpus", "linea_base", "perfil_y_suelo"],
)
def test_los_artefactos_congelados_estan_intactos(artefactos: dict[str, str]) -> None:
    entorno = _entorno()
    for ruta, esperado in artefactos.items():
        assert rp.blob_git(entorno.leer_bytes(ruta)) == esperado, ruta


@pytest.mark.parametrize(
    ("comprobacion", "artefactos"),
    [
        (rp.fallos_de_corpus, rp.CORPUS_CONGELADO),
        (rp.fallos_de_linea_base, rp.LINEA_BASE_REDERIVADA),
        (rp.fallos_de_perfil, rp.PERFIL_Y_SUELO),
    ],
    ids=["corpus", "linea_base", "perfil_y_suelo"],
)
def test_alterar_un_artefacto_congelado_bloquea(
    comprobacion: Callable[[rp.EntornoCustodia], tuple[str, ...]],
    artefactos: Mapping[str, str],
) -> None:
    ruta = next(iter(artefactos))
    assert comprobacion(_entorno(alterados=[ruta])) != ()


def test_las_cinco_puertas_de_arranque_estan_satisfechas() -> None:
    assert rp.fallos_de_puertas(_entorno()) == ()


# --------------------------------------------------------------------------
# E. El plan congelado antes de medir
# --------------------------------------------------------------------------


def test_el_plan_declara_lo_que_el_protocolo_exige() -> None:
    assert rp.SESIONES_EXIGIDAS == 11
    assert rp.REPETICIONES == 100
    assert rp.REPETICIONES >= rp.REPETICIONES_MINIMAS
    assert rp.WARMUP > 0
    assert rp.SEMILLA
    assert rp.RELOJ == "time.perf_counter_ns"


def test_el_orden_es_determinista() -> None:
    """§5.3: sin aleatoriedad no sembrada, sin dependencia de reloj."""
    assert rp.orden_de_ejecucion(3, 7) == rp.orden_de_ejecucion(3, 7)


def test_el_orden_es_intercalado_y_nunca_agrupa_por_candidato() -> None:
    """§5.2: prohibido todos los bloques de uno seguidos de los de otro."""
    for sesion in range(1, rp.SESIONES_EXIGIDAS + 1):
        for repeticion in range(1, 6):
            orden = rp.orden_de_ejecucion(sesion, repeticion)
            assert sorted(orden) == sorted(rp.PARTICIPANTES)
            assert len(set(orden)) == len(rp.PARTICIPANTES)


def test_ningun_participante_ocupa_siempre_la_primera_posicion() -> None:
    """Quien va primero paga la caché fría; fijar quién sería regalar ventaja."""
    for sesion in range(1, rp.SESIONES_EXIGIDAS + 1):
        primeros = [rp.orden_de_ejecucion(sesion, r)[0] for r in range(1, rp.REPETICIONES + 1)]
        reparto = {p: primeros.count(p) for p in rp.PARTICIPANTES}
        assert set(reparto) == set(rp.PARTICIPANTES)
        assert set(reparto.values()) == {rp.REPETICIONES // len(rp.PARTICIPANTES)}


def test_cada_participante_ocupa_cada_posicion_el_mismo_numero_de_veces() -> None:
    """No basta con repartir la primera posición: hay que repartirlas todas.

    La segunda posición mide detrás de un candidato concreto, y la última mide
    con el entorno más caliente. Si el reparto sólo equilibrase la cabeza, esas
    ventajas seguirían siendo de alguien fijo.
    """
    reparto_esperado = rp.REPETICIONES // len(rp.PARTICIPANTES)
    for sesion in range(1, rp.SESIONES_EXIGIDAS + 1):
        veces: dict[tuple[str, int], int] = {}
        for repeticion in range(1, rp.REPETICIONES + 1):
            for posicion, participante in enumerate(rp.orden_de_ejecucion(sesion, repeticion)):
                veces[participante, posicion] = veces.get((participante, posicion), 0) + 1
        assert len(veces) == len(rp.PARTICIPANTES) ** 2, sesion
        assert set(veces.values()) == {reparto_esperado}, sesion


def test_la_numeracion_empieza_en_uno() -> None:
    for sesion, repeticion in ((0, 1), (1, 0), (-1, 3)):
        with pytest.raises(ValueError, match="se numeran desde 1"):
            rp.orden_de_ejecucion(sesion, repeticion)


def test_el_registro_obligatorio_cubre_los_once_puntos_del_protocolo() -> None:
    assert len(rp.REGISTRO_OBLIGATORIO) == 11
    assert len(set(rp.REGISTRO_OBLIGATORIO)) == 11


def test_la_evidencia_minima_cubre_los_once_puntos_de_la_especificacion() -> None:
    assert len(rp.EVIDENCIA_MINIMA) == 11
    assert rp.EVIDENCIA_PROPIA_DE_D in rp.EVIDENCIA_MINIMA
    assert "adr002_d" in rp.EVIDENCIA_PROPIA_DE_D


# --------------------------------------------------------------------------
# F. Neutralidad y aislamiento
# --------------------------------------------------------------------------


def test_la_capa_comun_es_neutral_y_los_candidatos_estan_aislados() -> None:
    dependencias = run_round.dependencias_reales(RAIZ)
    assert list(dependencias.neutralidad) == []
    assert {p: list(h) for p, h in dependencias.aislamiento.items()} == {
        paquete: [] for paquete in run_round.PAQUETES_DE_CANDIDATO
    }


def test_un_fallo_de_neutralidad_bloquea() -> None:
    fallos = rp.fallos_de_neutralidad(["engine.py nombra a ADR002-A"], {})
    assert fallos and rp.MOTIVO_NEUTRALIDAD in fallos[0]


def test_un_fallo_de_aislamiento_bloquea() -> None:
    fallos = rp.fallos_de_neutralidad([], {"adr002_d": ["candidate.py implementa el motor"]})
    assert fallos and rp.MOTIVO_AISLAMIENTO in fallos[0]


# --------------------------------------------------------------------------
# G. Que este paquete no mida y no escriba
# --------------------------------------------------------------------------


def test_la_salida_prevista_no_existe_todavia() -> None:
    """Comprobar no produce artefacto: ejecutar es otro acto, y no ha ocurrido."""
    assert not (RAIZ / run_round.SALIDA_PREVISTA).exists()


def test_comprobar_no_crea_nada(tmp_path: Path) -> None:
    antes = sorted(p.name for p in (RAIZ / "artifacts").iterdir())
    run_round.comprobar(run_round.dependencias_reales(RAIZ))
    assert sorted(p.name for p in (RAIZ / "artifacts").iterdir()) == antes
    assert list(tmp_path.iterdir()) == []


#: A partir de este marcador viven los **inventarios de lo prohibido**, y por
#: eso el control de abajo no los mira. No es comodidad: un inventario contiene
#: por necesidad todos los términos que persigue, de modo que auditarlo sería
#: exigirle que no nombre aquello que existe para nombrar, y la única forma de
#: pasar sería vaciarlo. Es la misma exclusión, y por el mismo motivo, que
#: ``neutrality.py`` se aplica a sí mismo.
_MARCADOR_DE_LOS_INVENTARIOS: Final = "def test_estas_pruebas_no_miden_rendimiento"


def test_estas_pruebas_no_miden_rendimiento() -> None:
    """Medir exige la autorización que este mismo paquete declara ausente.

    El control persigue **llamadas**, no nombres: preinscribir el reloj es
    declarar cuál se usará, y esa declaración es justamente lo que el §8.1 del
    protocolo obliga a fijar antes de medir. Prohibir la palabra obligaría a
    borrar la declaración para pasar el control, que es lo contrario de lo que
    se quiere.
    """
    codigo = Path(__file__).read_text(encoding="utf-8")
    cuerpo = codigo.split(_MARCADOR_DE_LOS_INVENTARIOS)[0]
    for prohibido in ("perf_counter(", "monotonic(", "timeit", "time.time(", "latencia"):
        assert prohibido not in cuerpo, prohibido
    assert "performance_corpus" not in cuerpo
    assert "conformance_corpus" not in cuerpo


_MODULOS: Final[tuple[str, ...]] = ("round_protocol.py", "run_round.py")


@pytest.mark.parametrize("modulo", _MODULOS)
def test_el_paquete_no_cronometra(modulo: str) -> None:
    """Preinscribir no es medir: aquí no hay ni un reloj llamado."""
    codigo = (RAIZ / "experiments/adr002/round" / modulo).read_text(encoding="utf-8")
    sin_comentarios = re.sub(r'"""(?:.|\n)*?"""', "", codigo)
    for prohibido in ("perf_counter(", "monotonic(", "timeit", "time.time("):
        assert prohibido not in sin_comentarios, f"{modulo}: {prohibido}"


@pytest.mark.parametrize("modulo", _MODULOS)
def test_el_paquete_no_escribe(modulo: str) -> None:
    codigo = (RAIZ / "experiments/adr002/round" / modulo).read_text(encoding="utf-8")
    sin_comentarios = re.sub(r'"""(?:.|\n)*?"""', "", codigo)
    for prohibido in ("write_text", "write_bytes", "open(", "mkdir", "sqlite3"):
        assert prohibido not in sin_comentarios, f"{modulo}: {prohibido}"


def test_el_reloj_se_declara_pero_no_se_llama() -> None:
    """La otra mitad del control anterior, dicha en positivo."""
    for modulo in _MODULOS:
        codigo = (RAIZ / "experiments/adr002/round" / modulo).read_text(encoding="utf-8")
        assert f"{rp.RELOJ}(" not in codigo, modulo
    assert rp.RELOJ == "time.perf_counter_ns"
