"""El guardián del suelo de prueba muerto (G2, ADR-134, incidencia #526).

«Prueba que no puede fallar» es la familia de defecto más extendida de la ola
de criticidad medida por la mina de aprendizaje operativo de 2026-09 (7
hallazgos en 4 de 8 encargos,
``docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09.md`` sección 4, rama
``claude/adr002-tol209-forensic-audit-i0ui8k``). Su caso más simple y
mecánicamente detectable es el suelo muerto: una constante o una aserción
escritas como si fueran una cota, pero cuyo valor hace que la comparación sea
cierta para cualquier entrada posible.

Este guardián recorre ``tests/acceptance/*.py`` (nunca ``src/``: un suelo
muerto es un defecto de la prueba, no del código que prueba) y falla por cada
una de estas dos formas, y solo estas dos — la regla estrecha que la
incidencia #526 midió con cero falsos positivos sobre el corpus real de hoy:

1. una constante ``_MINIMO_*`` anotada ``Final[int]`` con valor ``0``: pone
   suelo a una métrica que nunca puede ser negativa (recuentos, aciertos,
   cobertura), así que la cota nunca puede fallar.
2. una línea ``assert <expresión> >= 0`` completa: la misma tautología
   escrita a mano en vez de en una constante nombrada.

Deliberadamente NO se señala una comparación encadenada como
``assert 0 <= x <= y``: ahí la mitad izquierda (``0 <= x``) es la misma
tautología, pero la mitad derecha (``x <= y``) sí puede fallar, así que la
aserción entera sigue siendo una prueba viva — retirar la mitad muerta de una
cadena así exige juicio sobre cuál mitad importa, y ese juicio es del
propietario, no de este guardián (ver ADR-134, nota de arranque, pregunta 2).

Es determinista: lee ficheros de texto y busca patrones por línea. No razona,
no ejecuta ninguna prueba, no sale a la red y cuesta milisegundos — mismo
estilo que ``tests/automation/test_contrato_http_de_ollama.py`` (G1,
ADR-132), del que copia la forma: glob + parametrize + funciones puras de
comprobación, verificadas también con texto sintético para que un patrón roto
no pase en verde sin mirar nada.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
DIRECTORIO_DE_ACEPTACION = RAIZ / "tests" / "acceptance"


def _ficheros_de_aceptacion() -> list[Path]:
    return sorted(DIRECTORIO_DE_ACEPTACION.glob("*.py"))


# --- Las dos formas de suelo muerto (incidencia #526), como funciones puras --
#
# Puras y sobre texto para poder verificarlas con texto sintético además de
# con los ficheros reales (ver la sección "Anti-vacua" más abajo). Cada
# función mira UNA línea ya recortada de espacios (`str.strip()`), nunca el
# fichero entero: las dos formas descritas por el encargo son, las dos, de
# una sola línea.

_CONSTANTE_MINIMO_CERO = re.compile(r"^_MINIMO_\w*\s*:\s*Final\[int\]\s*=\s*0\s*$")

#: `$` al final es lo que excluye una comparación encadenada
#: (`assert 0 <= x <= y`): esa línea termina en `<= y`, no en `>= 0`, así que
#: nunca casa con este patrón — sin lógica adicional para distinguir los dos
#: casos, la propia forma de la línea basta. `\s*0\s*$` (en vez de sólo `0$`)
#: es lo que evita marcar `assert x >= 0.0`: entre `>=` y el final de línea
#: solo puede haber espacios, y en `0.0` hay un `.` de por medio.
_ASSERT_MAYOR_O_IGUAL_A_CERO = re.compile(r"^assert\s+\S.*>=\s*0\s*$")


def es_constante_minimo_cero(linea: str) -> bool:
    """Regla 1: ``_MINIMO_*: Final[int] = 0``."""
    return _CONSTANTE_MINIMO_CERO.match(linea.strip()) is not None


def es_assert_mayor_o_igual_a_cero(linea: str) -> bool:
    """Regla 2: ``assert <expresión> >= 0`` como línea completa."""
    return _ASSERT_MAYOR_O_IGUAL_A_CERO.match(linea.strip()) is not None


def suelos_muertos(texto: str) -> list[tuple[int, str]]:
    """``(numero_de_linea, regla)`` por cada suelo muerto de ``texto``."""
    hallazgos: list[tuple[int, str]] = []
    for numero, linea in enumerate(texto.splitlines(), start=1):
        if es_constante_minimo_cero(linea):
            hallazgos.append((numero, "constante _MINIMO_*: Final[int] = 0"))
        elif es_assert_mayor_o_igual_a_cero(linea):
            hallazgos.append((numero, "assert <expresión> >= 0"))
    return hallazgos


# --- La guarda ------------------------------------------------------------


@pytest.mark.parametrize("fichero", _ficheros_de_aceptacion(), ids=lambda p: p.name)
def test_no_hay_suelo_muerto(fichero: Path) -> None:
    texto = fichero.read_text(encoding="utf-8")
    hallazgos = suelos_muertos(texto)
    mensaje = "; ".join(f"{fichero.name}:{numero} ({regla})" for numero, regla in hallazgos)
    assert hallazgos == [], (
        f"{mensaje} -- una cota que nunca puede fallar no es una prueba, es prosa con "
        "forma de aserción (mina 2026-09 §4/§6). Sube la constante por encima de 0, "
        "quita la aserción tautológica, o si de verdad hace falta una cota que toque 0, "
        "escríbela como comparación encadenada (`assert 0 <= x <= y`) que este guardián "
        "no señala porque su mitad derecha sí puede fallar."
    )


# --- Anti-vacua -------------------------------------------------------------
#
# El corpus real está limpio hoy (tras la retirada de esta misma incidencia),
# así que la prueba de arriba pasaría igual con las funciones de comprobación
# rotas. Estas fijan el comportamiento con texto sintético, que no depende de
# cómo esté el repositorio hoy -- mismo patrón que test_citas_de_los_adr.py y
# test_contrato_http_de_ollama.py.


def test_una_constante_minimo_en_cero_se_detecta() -> None:
    assert es_constante_minimo_cero("_MINIMO_ALGO: Final[int] = 0")


def test_una_constante_minimo_en_cero_indentada_se_detecta() -> None:
    assert es_constante_minimo_cero("    _MINIMO_ALGO: Final[int] = 0")


def test_una_constante_minimo_con_valor_positivo_no_se_detecta() -> None:
    """El suelo que sí puede fallar: M20 lo dejó al lado del muerto (ADR-134)."""
    assert not es_constante_minimo_cero(
        "_MINIMO_ELEMENTOS_HALLADOS_PAQUETE_COMPLETO: Final[int] = 72"
    )


def test_una_constante_maximo_en_cero_no_se_detecta() -> None:
    """Un techo en 0 SÍ puede fallar (cualquier valor positivo lo rompe): no es un
    suelo. Solo `_MINIMO_*` se señala, nunca `_MAXIMO_*`."""
    assert not es_constante_minimo_cero(
        "_MAXIMO_OMISIONES_CRITICAS_PAQUETE_COMPLETO: Final[int] = 0"
    )


def test_una_constante_minimo_sin_anotacion_final_int_no_se_detecta() -> None:
    """Sin `Final[int]` no es la forma exacta que el encargo describe."""
    assert not es_constante_minimo_cero("_MINIMO_ALGO = 0")


def test_un_assert_mayor_o_igual_a_cero_suelto_se_detecta() -> None:
    assert es_assert_mayor_o_igual_a_cero("assert paquete.elementos_de_mas >= 0")


def test_un_assert_mayor_o_igual_a_cero_indentado_se_detecta() -> None:
    assert es_assert_mayor_o_igual_a_cero("    assert paquete.elementos_de_mas >= 0")


def test_un_assert_mayor_o_igual_a_un_valor_positivo_no_se_detecta() -> None:
    assert not es_assert_mayor_o_igual_a_cero("assert metricas.aciertos_exactos >= 29")


def test_un_assert_mayor_o_igual_a_cero_punto_cero_no_se_detecta() -> None:
    """`>= 0.0` no es la forma entera `>= 0` -- ver el comentario del regex."""
    assert not es_assert_mayor_o_igual_a_cero("assert medida >= 0.0")


def test_una_comparacion_encadenada_con_cero_a_la_izquierda_no_se_detecta() -> None:
    """El caso adversario del encargo: `assert 0 <= x <= y` tiene su mitad
    izquierda muerta pero la derecha sí puede fallar -- retirarla es un juicio
    del propietario, no de este guardián (ver el docstring del módulo)."""
    assert not es_assert_mayor_o_igual_a_cero("assert 0 <= x <= y")


def test_una_comparacion_encadenada_real_del_banco_no_se_detecta() -> None:
    """La misma forma que usa de verdad `test_pa_0_2_rec_01_banco_evidencia.py`."""
    assert not es_assert_mayor_o_igual_a_cero(
        "assert 0 <= paquete_completo.omisiones_criticas <= limite_superior"
    )


def test_un_assert_de_igualdad_no_se_confunde_con_mayor_o_igual() -> None:
    assert not es_assert_mayor_o_igual_a_cero("assert total == 0")


def test_suelos_muertos_reporta_linea_y_regla_de_cada_hallazgo() -> None:
    texto = "x = 1\n_MINIMO_ALGO: Final[int] = 0\ny = 2\nassert y >= 0\nassert 0 <= y <= 10\n"
    assert suelos_muertos(texto) == [
        (2, "constante _MINIMO_*: Final[int] = 0"),
        (4, "assert <expresión> >= 0"),
    ]


def test_texto_conforme_no_reporta_nada() -> None:
    texto = (
        "_MINIMO_ELEMENTOS_HALLADOS: Final[int] = 72\n"
        "_MAXIMO_OMISIONES_CRITICAS: Final[int] = 0\n"
        "assert hallados >= _MINIMO_ELEMENTOS_HALLADOS\n"
        "assert omisiones <= _MAXIMO_OMISIONES_CRITICAS\n"
        "assert 0 <= omisiones <= total\n"
    )
    assert suelos_muertos(texto) == []


def test_el_barrido_encuentra_los_ficheros_de_prueba_de_aceptacion() -> None:
    """Si el glob se rompe, la guarda pasaría en verde sin mirar nada."""
    ficheros = _ficheros_de_aceptacion()
    nombres = {fichero.name for fichero in ficheros}
    assert "test_pa_0_2_rec_01_banco_evidencia.py" in nombres, (
        f"el barrido no encontró el banco de evidencia conocido: {nombres}"
    )
