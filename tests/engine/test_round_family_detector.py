"""Detector de familia repetida entre rondas (M1, incidencia #277, ADR-078).

Estas pruebas fijan el criterio medido en el módulo bajo prueba: 3+ rondas
consecutivas sobre el mismo archivo. Dos de ellas replican incidencias reales
de este repositorio -#246 y #211-, comprobadas a mano leyendo el texto de la
revisión (requisito 2); otra replica #268 sin cortar, tal cual ocurrió, para
demostrar que NO se señala (requisito 3: el falso positivo más probable es
justo el que #268 hubiera producido con un umbral de 2).
"""

from __future__ import annotations

from sirius_engine.round_family_detector import (
    RONDAS_CONSECUTIVAS_MINIMAS,
    detectar_familia_repetida,
)


def _hallazgo(
    archivo: str, fingerprint: str, severidad: str = "P2", fuente: str = "CODEX"
) -> dict[str, str]:
    return {"fingerprint": fingerprint, "severity": severidad, "source": fuente, "file": archivo}


def _registro(numero: int, hallazgos: list[dict[str, str]]) -> dict[str, object]:
    return {"round": numero, "head": f"head-{numero}", "findings": hallazgos}


# --------------------------------------------------------------------------- #
# Requisito 2: acierta sobre un caso real conocido
# --------------------------------------------------------------------------- #


def test_detecta_la_incidencia_246_seis_rondas_sobre_el_mismo_archivo() -> None:
    """#246 (C3a): seis rondas, todas sobre ``sirius_check_docs.py``, sin resolver.

    Datos reales, leídos de la incidencia (`gh issue view 246 --comments`):
    seis registros ``RONDA_HALLAZGOS`` publicados, todos con al menos un
    hallazgo en ``scripts/automation/sirius_check_docs.py``. Es el caso que
    la propia incidencia #277 cita como conocido y que el requisito 2 exige
    reconocer.
    """
    archivo = "scripts/automation/sirius_check_docs.py"
    registros = [
        _registro(
            1, [_hallazgo(archivo, "63feda7dda92e8b1"), _hallazgo(archivo, "77f49c240bfa164f")]
        ),
        _registro(
            2, [_hallazgo(archivo, "46b23caa5d8a46f0"), _hallazgo(archivo, "6afca84917de05a4")]
        ),
        _registro(3, [_hallazgo(archivo, "15918b53fe5eea29", fuente="CLAUDE")]),
        _registro(
            4,
            [
                _hallazgo(
                    f"{archivo} (ruta_citada líneas 132-146)", "0be31eaf8eab9ff3", fuente="CLAUDE"
                )
            ],
        ),
        _registro(5, [_hallazgo(archivo, "c8f64fc87094054d")]),
        _registro(6, [_hallazgo(archivo, "d2cca483e8f5864c")]),
    ]

    resultado = detectar_familia_repetida(registros)

    assert resultado.hay_familia_repetida
    # La ronda 4 no cuenta para este archivo: su hallazgo lleva la anotación
    # de la revisora pegada al nombre ("... (ruta_citada líneas 132-146)"),
    # así que normaliza a una ubicación distinta -limitación conocida y
    # aceptada, documentada en el módulo-. El tramo 5-6 que queda tras el
    # corte no llega al umbral (longitud 2), así que el único tramo
    # detectado es 1-3.
    assert len(resultado.evidencias) == 1
    evidencia = resultado.evidencias[0]
    assert evidencia.archivo == archivo
    assert evidencia.rondas == (1, 2, 3)


def test_detecta_la_incidencia_211_la_propia_revision_confirma_la_familia() -> None:
    """#211: la revisora dice, en la ronda 3, que es la misma familia que las rondas 1 y 2.

    Cita literal del comentario real (CLAUDE-REVISOR-001, ronda 3): «Es la
    misma familia de defecto que CODEX-001 (rondas 1 y 2 de esta misma PR):
    parseo heurístico y parcial de la gramática de banderas de `gh`». Es la
    confirmación más directa posible de que el criterio mide lo que dice
    medir, no una coincidencia de archivo sin relación real.
    """
    archivo = "experiments/work_engine_spike_i1/probe.py"
    registros = [
        _registro(1, [_hallazgo(archivo, "aaaa000000000001")]),
        _registro(2, [_hallazgo(archivo, "aaaa000000000002")]),
        _registro(3, [_hallazgo(archivo, "dd220acd066eb4ed", fuente="CLAUDE")]),
    ]

    resultado = detectar_familia_repetida(registros)

    assert resultado.hay_familia_repetida
    assert len(resultado.evidencias) == 1
    evidencia = resultado.evidencias[0]
    assert evidencia.archivo == archivo
    assert evidencia.rondas == (1, 2, 3)
    assert "3 rondas consecutivas" in evidencia.detalle


# --------------------------------------------------------------------------- #
# Requisito 3: NO salta sobre el caso normal
# --------------------------------------------------------------------------- #


def test_no_senala_dos_rondas_consecutivas_sobre_el_mismo_archivo() -> None:
    """El falso positivo más probable: corregir un fichero y que se revise otra vez.

    Es el patrón real y sin bucle de la incidencia #268 (rondas 1 y 2, antes
    de que la ronda 3 pasara a un archivo distinto): dos rondas seguidas
    tocan ``seven_day_streak_cli.py`` y la incidencia progresó con
    normalidad. Con el umbral en 3 esto no se señala.
    """
    cli = "src/sirius_engine/seven_day_streak_cli.py"
    otro = "src/sirius_engine/seven_day_streak.py"
    registros = [
        _registro(
            1,
            [
                _hallazgo(cli, "2e8f2ffc95cfa4f5"),
                _hallazgo(otro, "7f2709c588f648f9", severidad="P1"),
            ],
        ),
        _registro(2, [_hallazgo(cli, "40998e101d7ff87d", severidad="P1")]),
    ]

    resultado = detectar_familia_repetida(registros)

    assert not resultado.hay_familia_repetida
    assert resultado.evidencias == ()


def test_no_senala_la_incidencia_268_completa_tal_cual_ocurrio() -> None:
    """#268 real, sin cortar: 3 rondas, pero el archivo repetido nunca llega a 3 seguidas.

    Ronda 1: dos archivos. Ronda 2: uno de esos dos (2 consecutivas). Ronda
    3: un archivo distinto. El requisito 2 solo exige acertar en #268 O
    #246; este detector no señala #268 -documentado como limitación
    aceptada en el módulo-, y esta prueba fija que ese "no señala" es
    intencional y no un olvido: si alguna vez el detector empezara a
    señalar #268, esta prueba lo diría antes de que llegara a producción.
    """
    cli = "src/sirius_engine/seven_day_streak_cli.py"
    streak = "src/sirius_engine/seven_day_streak.py"
    mirror = "src/sirius_engine/mirror_projection.py"
    registros = [
        _registro(
            1,
            [
                _hallazgo(cli, "2e8f2ffc95cfa4f5"),
                _hallazgo(streak, "7f2709c588f648f9", severidad="P1"),
                _hallazgo(cli, "e2e477765f88da86", severidad="P1"),
            ],
        ),
        _registro(2, [_hallazgo(cli, "40998e101d7ff87d", severidad="P1")]),
        _registro(
            3,
            [
                _hallazgo(mirror, "69dfd1dcfcc018c9", severidad="P1"),
                _hallazgo(mirror, "dff5f225d8a10d3d", severidad="P1", fuente="CLAUDE"),
            ],
        ),
    ]

    resultado = detectar_familia_repetida(registros)

    assert not resultado.hay_familia_repetida


def test_no_senala_el_mismo_archivo_con_un_hueco_entre_apariciones() -> None:
    """Tres apariciones del mismo archivo, pero no seguidas: no es el mismo tramo.

    Replica el patrón real de la incidencia #177 (rondas 1, 2 y 5 sobre
    ``adapters/memory_store.py``, con progreso real -y una decisión humana
    de por medio- entre la 2 y la 5): tres apariciones NO consecutivas no
    son evidencia de bucle, y contarlas como si lo fueran habría sido
    exactamente el "detectar de más" que la nota de arranque de la
    incidencia #277 identifica como el riesgo real de este bloque.
    """
    archivo = "src/sirius_engine/adapters/memory_store.py"
    registros = [
        _registro(1, [_hallazgo(archivo, "a1")]),
        _registro(2, [_hallazgo(archivo, "a2")]),
        _registro(3, [_hallazgo("src/sirius_engine/domain/run.py", "a3")]),
        _registro(4, [_hallazgo("src/sirius_engine/domain/run.py", "a4")]),
        _registro(5, [_hallazgo(archivo, "a5")]),
    ]

    resultado = detectar_familia_repetida(registros)

    assert not resultado.hay_familia_repetida


# --------------------------------------------------------------------------- #
# Requisitos 4 y 5: determinista, sin red, y con evidencia
# --------------------------------------------------------------------------- #


def test_es_determinista() -> None:
    archivo = "src/x.py"
    registros = [_registro(n, [_hallazgo(archivo, f"fp{n}")]) for n in (1, 2, 3)]

    primero = detectar_familia_repetida(registros)
    segundo = detectar_familia_repetida(list(reversed(registros)))

    assert primero == segundo


def test_la_evidencia_dice_que_archivo_y_que_rondas() -> None:
    archivo = "src/x.py"
    registros = [_registro(n, [_hallazgo(archivo, f"fp{n}")]) for n in (1, 2, 3, 4)]

    resultado = detectar_familia_repetida(registros)

    assert len(resultado.evidencias) == 1
    evidencia = resultado.evidencias[0]
    assert evidencia.archivo == archivo
    assert evidencia.rondas == (1, 2, 3, 4)
    assert archivo in evidencia.detalle
    assert "1-4" in evidencia.detalle


def test_sin_registros_no_hay_familia_repetida() -> None:
    resultado = detectar_familia_repetida([])

    assert not resultado.hay_familia_repetida
    assert resultado.evidencias == ()


def test_el_umbral_exige_al_menos_tres() -> None:
    assert RONDAS_CONSECUTIVAS_MINIMAS == 3
