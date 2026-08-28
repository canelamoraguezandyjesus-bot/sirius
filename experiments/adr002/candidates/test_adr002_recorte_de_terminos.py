"""El recorte que tiraba palabras de la consulta, escrito como prueba.

`E2` es la etapa de variantes morfologicas: busca «restriccion» cuando el
usuario escribio «restricciones». Para eso genera variantes de cada termino y
se las pide al puerto.

El puerto acota los argumentos, y **acotaba ordenando alfabeticamente**. Con la
consulta «Restricciones esenciales, maximo duro 5» salian 25 variantes, la cota
era 16, y las 16 primeras del alfabeto eran todas de «duro», «esencial» y
«maximo». **Todas las de «restriccion» se caian**, porque la erre va detras.

Lo que llegaba al indice eran solo formas inventadas por el generador —duroa,
duroas, esenci, maxima— que no existen en ningun texto. La etapa devolvia cero.
Sin error, sin aviso y sin que ninguna prueba lo viese: el resultado era
plausible, simplemente mas pobre.

Estas pruebas fijan las dos mitades del arreglo: que el puerto no elija por
alfabeto, y que `E2` reparta las variantes entre los terminos para que la cota
no se agote con el primero.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from experiments.adr002.candidates.adr002_a import candidate as ca
from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.candidates.common import port

RAIZ: Final = Path(__file__).resolve().parents[3]

#: La consulta que lo destapo, literal del banco (`B04-CA-44`).
CONSULTA: Final = "Restricciones esenciales, máximo duro 5."


def _variantes_que_pediria_e2(consulta: str) -> list[str]:
    """Lo que `E2` entrega al puerto, con el reparto por rondas."""
    terminos = lexical.terminos_significativos(consulta)
    por_termino = [
        [v for v in lexical.ordenar_estable(lexical.variantes(t)) if v not in terminos]
        for t in terminos
    ]
    return [
        variantes[ronda]
        for ronda in range(max((len(v) for v in por_termino), default=0))
        for variantes in por_termino
        if ronda < len(variantes)
    ]


# ---------------------------------------------------------------------------
# A. El puerto ya no elige por alfabeto
# ---------------------------------------------------------------------------


def test_acotar_conserva_el_orden_de_llegada_y_no_el_alfabetico() -> None:
    """Quien llama decide la prioridad; el puerto la respeta."""
    pedidos = ["zeta", "alfa", "malva"]
    assert port.PuertoSqlite._acotar(pedidos, limite=2) == ["zeta", "alfa"]


def test_acotar_sigue_deduplicando() -> None:
    """Pedir dos veces lo mismo no es pedir mas: eso si era correcto."""
    assert port.PuertoSqlite._acotar(["a", "b", "a", "", "b"]) == ["a", "b"]


def test_el_termino_util_ya_no_se_cae_por_empezar_por_erre() -> None:
    """El defecto exacto: «restriccion» sobrevivia o no segun el alfabeto.

    Antes del arreglo esta comprobacion fallaba: ninguna variante de
    «restriccion» entraba en las 16 que el puerto conservaba.
    """
    pedidas = _variantes_que_pediria_e2(CONSULTA)
    conservadas = port.PuertoSqlite._acotar(pedidas)
    assert any(v.startswith("restriccion") for v in conservadas), (
        f"la cota vuelve a tirar el termino util: {conservadas}"
    )


# ---------------------------------------------------------------------------
# B. Ningun termino del usuario puede quedarse sin ninguna variante
# ---------------------------------------------------------------------------


def test_ningun_termino_de_la_consulta_pierde_todas_sus_variantes() -> None:
    """La garantia que hace util el reparto por rondas.

    No basta con «no ordenar por alfabeto»: si `E2` entregase todas las
    variantes de la primera palabra antes que ninguna de la segunda, la cota se
    agotaria con la primera y las demas desapareceria igual. El reparto por
    rondas es lo que lo impide, y esto lo comprueba sobre consultas reales del
    banco.
    """
    consultas = (
        CONSULTA,
        "¿Qué restricciones de transporte tengo?",
        "Dame todas las restricciones esenciales que debo respetar.",
        "Resume mi preferencia de redacción, el presupuesto vigente y la condición de ahorro.",
    )
    for consulta in consultas:
        terminos = lexical.terminos_significativos(consulta)
        conservadas = set(port.PuertoSqlite._acotar(_variantes_que_pediria_e2(consulta)))
        for termino in terminos:
            propias = {v for v in lexical.variantes(termino) if v not in terminos}
            if not propias:
                continue
            assert propias & conservadas, (
                f"«{termino}» de «{consulta}» se queda sin ninguna variante: "
                f"desaparece de la busqueda"
            )


def test_e2_reparte_por_rondas_y_no_amontona_por_el_primer_termino() -> None:
    """El primer bloque entregado toca **una** variante de cada termino."""
    terminos = lexical.terminos_significativos(CONSULTA)
    pedidas = _variantes_que_pediria_e2(CONSULTA)
    cabeza = pedidas[: len(terminos)]
    #: Cada elemento de la cabeza pertenece a un termino distinto.
    de_quien = [next(t for t in terminos if v in lexical.variantes(t)) for v in cabeza if v]
    assert len(set(de_quien)) == len(de_quien), f"la cabeza repite termino: {cabeza}"


def test_el_codigo_de_e2_reparte_y_no_ordena_el_conjunto_entero() -> None:
    """Que el reparto siga estando, y no vuelva a aplanarse en un `sorted`."""
    fuente = (RAIZ / "experiments/adr002/candidates/adr002_a/candidate.py").read_text(
        encoding="utf-8"
    )
    bloque = fuente.split("def _e2")[1].split("def _e3")[0]
    assert "por_termino" in bloque, "E2 dejo de repartir las variantes entre los terminos"
    assert "for ronda in range" in bloque


# ---------------------------------------------------------------------------
# C. El candidato sigue siendo el mismo por lo demas
# ---------------------------------------------------------------------------


def test_e2_sigue_sin_inventar_sinonimos() -> None:
    """El arreglo amplia el reparto, no el criterio.

    Una variante es la misma palabra flexionada. Si el arreglo hubiera colado
    sinonimos, `E2` habria dejado de ser `E2`.
    """
    for termino in ("restricciones", "presupuesto"):
        for variante in lexical.variantes(termino):
            assert lexical.raiz(variante) == lexical.raiz(termino), (variante, termino)


def test_el_candidato_a_se_construye_igual_que_siempre() -> None:
    instancia = ca.candidato()
    assert instancia.identificador == "ADR002-A"
    assert instancia.con_validacion_semantica is True
