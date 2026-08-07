"""Los niveles 2 y 3: que midan lo que dicen y declaren lo que no pueden medir.

Estas pruebas vigilan tres cosas distintas:

1. que los casos arquitectónicos **fallen cerrado** —una ficha incompleta no
   pasa por descuido, y una exención no se convierte en aprobado—;
2. que las dos ablaciones declaradas **no ejecutables** lo sigan siendo por la
   razón escrita, de modo que si alguien añadiese el interruptor que falta la
   prueba lo diga en vez de dejar la declaración envejecer en un comentario;
3. que el suelo de `AB-6` sea un suelo, y no el oráculo prestado al azar.

La tercera está escrita como el defecto que fue: la primera versión sorteaba
entre los **elegibles** del caso, y como el banco define
``resultado_esperado == elegibles_semanticos`` para `EXHAUSTIVA`, el azar
acertaba 47 de 47. Un suelo del 100 % no es un suelo, y la prueba lo fija.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, Final

from experiments.adr002.candidates.common import gates
from experiments.adr002.round import execute_levels as el
from experiments.adr002.round import levels as lv
from experiments.adr002.round import participants as pt

RAIZ: Final = Path(__file__).resolve().parents[3]


def _ficha(nombre: str, version: int) -> dict[str, Any]:
    ruta = RAIZ / f"artifacts/adr002_cards/ficha_{nombre}_v{version}.json"
    datos: dict[str, Any] = json.loads(ruta.read_text(encoding="utf-8"))
    return datos


# ---------------------------------------------------------------------------
# A. No mide tiempo, y se puede comprobar
# ---------------------------------------------------------------------------


def test_los_niveles_2_y_3_no_cronometran_nada() -> None:
    """Ni un reloj: las latencias publicadas son las de `v0.1` y `v0.2`."""
    import re

    for modulo in ("levels.py", "execute_levels.py"):
        fuente = (RAIZ / f"experiments/adr002/round/{modulo}").read_text(encoding="utf-8")
        sin_docstrings = re.sub(r'"""(?:.|\n)*?"""', "", fuente)
        for prohibido in ("perf_counter", "monotonic(", "timeit", "process_time"):
            assert prohibido not in sin_docstrings, f"{modulo}: {prohibido}"


# ---------------------------------------------------------------------------
# B. Las dos ablaciones no ejecutables lo son **por el código**, no por decreto
# ---------------------------------------------------------------------------


def test_ab_5_sigue_sin_ser_ejecutable_porque_no_hay_mascara_de_puertas() -> None:
    """Si alguien añadiese la máscara, esta prueba lo diría.

    La declaración de `AB-5` dice que ``aplicar_previas``, ``aplicar_g11`` y
    ``aplicar_g12`` no aceptan selección de puertas. Comprobarlo contra las
    firmas convierte una afirmación en algo refutable.
    """
    esperadas = {
        gates.aplicar_previas: {"candidatas", "peticion"},
        gates.aplicar_g11: {"candidatas", "peticion"},
    }
    for funcion, parametros in esperadas.items():
        firma = set(inspect.signature(funcion).parameters)
        assert firma == parametros, (
            f"{funcion.__name__} cambio de firma: si ahora acepta una mascara de "
            f"puertas, AB-5 ha pasado a ser ejecutable y su declaracion miente"
        )
    assert "AB-5" in lv.ABLACIONES_NO_EJECUTABLES


def test_ab_4_sigue_sin_ser_ejecutable_porque_los_interruptores_apagan_la_senal() -> None:
    """`AB-4` necesita señal encendida y validación apagada. No existe tal cosa.

    Los únicos dos interruptores que los candidatos exponen apagan la señal
    **entera**, que es justo lo contrario de lo que `AB-4` pide.
    """
    firma = inspect.signature(pt.construir).parameters
    interruptores = {n for n in firma if n.startswith("con_")}
    assert interruptores == {"con_senal_relacional", "con_senal_vectorial"}, (
        "aparecio un interruptor nuevo: si separa la senal de su validacion, AB-4 "
        "ha pasado a ser ejecutable y su declaracion miente"
    )
    assert "AB-4" in lv.ABLACIONES_NO_EJECUTABLES


def test_la_declaracion_de_no_ejecutables_dice_por_que_y_no_solo_que() -> None:
    """Una carencia sin motivo es una excusa; con motivo es un dato."""
    for ablacion, motivo in lv.ABLACIONES_NO_EJECUTABLES.items():
        assert len(motivo) > 120, ablacion
        assert "gobierno" in motivo or "capa comun" in motivo, ablacion


# ---------------------------------------------------------------------------
# C. El suelo de AB-6 es un suelo (el defecto, escrito como prueba)
# ---------------------------------------------------------------------------


def test_sortear_entre_los_elegibles_devolveria_siempre_la_respuesta() -> None:
    """El defecto que tuvo la primera versión, fijado para que no vuelva.

    En `EXHAUSTIVA` el banco define ``resultado_esperado == elegibles``. Sacar
    `n` de `n` devuelve el conjunto entero **siempre**, con cualquier semilla:
    el «azar» acertaría el 100 % y el suelo no mediría nada.
    """
    esperado = ("MEMORIA:1", "MEMORIA:2", "DECISION:3")
    for semilla in range(5):
        muestra = lv.suelo_aleatorio(sorted(esperado), len(esperado), semilla)
        assert tuple(sorted(muestra)) == tuple(sorted(esperado))


def test_el_suelo_real_sortea_sobre_el_canon_entero_y_no_acierta_siempre() -> None:
    """Con el universo correcto el suelo deja de ser el oráculo."""
    universo = el.universo_canonico()
    assert len(universo) > 40, "el universo del suelo no puede ser el conjunto del caso"
    esperado = universo[:3]
    fallos = sum(
        tuple(sorted(lv.suelo_aleatorio(universo, 3, s))) != tuple(sorted(esperado))
        for s in range(20)
    )
    assert fallos >= 18, "un suelo que acierta casi siempre no es un suelo"


def test_el_suelo_publicado_no_supera_a_los_candidatos_en_casos_con_contenido() -> None:
    """La comparación informativa: contenido, no ausencia."""
    documento = json.loads((RAIZ / lv.SALIDA).read_text(encoding="utf-8"))
    suelos = [a for a in documento["ablaciones"] if a["ablacion"] == "AB-6"]
    assert len(suelos) == 2, "AB-6 se publica en sus dos lecturas"
    for suelo in suelos:
        assert suelo["lectura"], "cada lectura de AB-6 dice cual es"


# ---------------------------------------------------------------------------
# D. ARQ-CA-03: la guarda de las repeticiones y la de las sesiones
# ---------------------------------------------------------------------------


def test_la_estabilidad_exige_las_sesiones_y_las_repeticiones_que_pide_el_caso() -> None:
    """Un solo orden observado **una** vez no es estabilidad."""
    un_vector: list[list[list[str]]] = [[["MEMORIA:1"]]]
    veredicto, _ = lv.arq_ca_03([30, 30], un_vector)
    assert veredicto is lv.Veredicto.FALLA, "dos sesiones no son cinco"
    veredicto, _ = lv.arq_ca_03([30, 30, 30, 30, 1], un_vector)
    assert veredicto is lv.Veredicto.FALLA, "una sesion con una repeticion no puntua"
    veredicto, detalle = lv.arq_ca_03([30] * 5, un_vector)
    assert veredicto is lv.Veredicto.PASA, detalle


def test_el_mismo_conjunto_en_distinto_orden_no_es_estable() -> None:
    """`B04-RF-22` pide estabilidad de orden, no solo de contenido."""
    dos_ordenes = [[["MEMORIA:1", "MEMORIA:2"]], [["MEMORIA:2", "MEMORIA:1"]]]
    veredicto, detalle = lv.arq_ca_03([30] * 5, dos_ordenes)
    assert veredicto is lv.Veredicto.FALLA
    assert "orden" in detalle


# ---------------------------------------------------------------------------
# E. ARQ-CA-04 y ARQ-CA-05: fallan cerrado, y la exención no es un aprobado
# ---------------------------------------------------------------------------


def test_la_exencion_del_control_no_se_convierte_en_aprobado() -> None:
    """`NO_APLICABLE` es su propio valor. Colapsarlo regalaría una puerta."""
    control = _ficha("T0-control", 1)
    for caso, funcion in (("ARQ-CA-04", lv.arq_ca_04), ("ARQ-CA-05", lv.arq_ca_05)):
        veredicto, detalle = funcion(control)
        assert veredicto is lv.Veredicto.NO_APLICABLE, caso
        assert "exencion declarada" in detalle, caso
        assert veredicto is not lv.Veredicto.PASA


def test_una_ficha_de_candidato_completa_pasa_los_dos_casos_de_gobierno() -> None:
    for nombre, version in (("ADR002-A", 6), ("ADR002-B", 8), ("ADR002-C", 3), ("ADR002-D", 3)):
        ficha = _ficha(nombre, version)
        for caso, funcion in (("ARQ-CA-04", lv.arq_ca_04), ("ARQ-CA-05", lv.arq_ca_05)):
            veredicto, detalle = funcion(ficha)
            assert veredicto is lv.Veredicto.PASA, f"{nombre} {caso}: {detalle}"


def test_una_ficha_sin_congelar_no_pasa_arq_ca_04() -> None:
    ficha = dict(_ficha("ADR002-B", 8))
    ficha["estado"] = "PROPUESTA"
    veredicto, detalle = lv.arq_ca_04(ficha)
    assert veredicto is lv.Veredicto.FALLA
    assert "CONGELADA" in detalle


def test_un_indice_sin_limite_por_magnitud_no_pasa_arq_ca_04() -> None:
    """La puerta 7 pide el límite, no la mención del índice."""
    ficha = json.loads(json.dumps(_ficha("ADR002-B", 8)))
    del ficha["indices_no_lexicos"][0]["limites_por_magnitud"]
    veredicto, detalle = lv.arq_ca_04(ficha)
    assert veredicto is lv.Veredicto.FALLA
    assert "limite por magnitud" in detalle


def test_un_coste_por_etapa_que_no_suma_no_pasa_arq_ca_05() -> None:
    """Si la suma no explica el total, la declaración no dice nada."""
    ficha = json.loads(json.dumps(_ficha("ADR002-B", 8)))
    ficha["coste_por_etapa"]["etapas"][0]["coste_local_limite_ns"] += 1
    veredicto, detalle = lv.arq_ca_05(ficha)
    assert veredicto is lv.Veredicto.FALLA
    assert "no explica" in detalle


def test_una_etapa_sin_coste_externo_separado_no_pasa_arq_ca_05() -> None:
    """`TOL-202` prohíbe sumarlos: separarlos es la obligación."""
    ficha = json.loads(json.dumps(_ficha("ADR002-B", 8)))
    ficha["coste_por_etapa"]["etapas"][2]["coste_externo_declarado"] = ""
    veredicto, detalle = lv.arq_ca_05(ficha)
    assert veredicto is lv.Veredicto.FALLA
    assert "coste externo" in detalle


# ---------------------------------------------------------------------------
# F. ARQ-CA-02: la purga se comprueba en bytes crudos
# ---------------------------------------------------------------------------


def test_la_purga_se_busca_en_bytes_y_encuentra_lo_que_sigue_ahi(tmp_path: Path) -> None:
    """Una fila borrada con rastro en una página libre sigue siendo un fragmento."""
    fichero = tmp_path / "derivado.sqlite3"
    fichero.write_bytes(b"basura\x00texto canonico que sobrevive\x00mas basura")
    encontrados = lv.fragmentos_recuperables(fichero, ["texto canonico que sobrevive"])
    assert encontrados, "la busqueda en bytes no encontro lo que si esta"

    (tmp_path / "limpio.sqlite3").write_bytes(b"\x00" * 64)
    assert not lv.fragmentos_recuperables(tmp_path / "limpio.sqlite3", ["texto canonico"])


def test_quien_no_construye_indice_propio_no_aplica_a_la_purga(tmp_path: Path) -> None:
    """`A` y `C` no tienen derivado propio: el caso no les aplica, no lo aprueban."""
    veredicto, detalle = lv.arq_ca_02("ADR002-A", tmp_path, tmp_path / "canon.db", ["x"])
    assert veredicto is lv.Veredicto.NO_APLICABLE
    assert "no construye indice derivado propio" in detalle


# ---------------------------------------------------------------------------
# G. El artefacto publicado dice lo que se ejecutó y lo que no
# ---------------------------------------------------------------------------


def test_el_artefacto_publica_las_dos_ablaciones_que_no_se_ejecutaron() -> None:
    documento = json.loads((RAIZ / lv.SALIDA).read_text(encoding="utf-8"))
    assert set(documento["ablaciones_no_ejecutables"]) == {"AB-4", "AB-5"}
    no_ejecutadas = {a["ablacion"] for a in documento["ablaciones"] if not a["ejecutada"]}
    assert no_ejecutadas == {"AB-4", "AB-5"}
    for fila in documento["ablaciones"]:
        if not fila["ejecutada"]:
            assert fila["motivo_si_no_se_ejecuta"], fila["ablacion"]


def test_el_artefacto_no_adjudica_puertas_con_las_ablaciones() -> None:
    """El banco: «nunca producen veredicto de conformidad»."""
    documento = json.loads((RAIZ / lv.SALIDA).read_text(encoding="utf-8"))
    for fila in documento["ablaciones"]:
        assert "veredicto" not in fila, fila["ablacion"]
    assert "las_ablaciones_no_adjudican" in documento


def test_los_cinco_casos_arquitectonicos_cubren_a_los_cinco_participantes() -> None:
    documento = json.loads((RAIZ / lv.SALIDA).read_text(encoding="utf-8"))
    esperados = {f"ARQ-CA-0{n}" for n in range(1, 6)}
    por_participante: dict[str, set[str]] = {}
    for fila in documento["arquitectonicos"]:
        por_participante.setdefault(fila["participante"], set()).add(fila["caso"])
    assert len(por_participante) == 5
    for participante, casos in por_participante.items():
        assert casos == esperados, participante
