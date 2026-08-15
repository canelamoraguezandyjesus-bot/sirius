"""La categoria del canon, hecha buscable.

Corren en cualquier maquina y **sin modelo**: esta pieza es determinista y no
habla con nadie. Esa es justo la propiedad que hay que proteger, porque es lo
que la separa de la ampliacion escrita por un modelo, que se midio dos veces y
no aporto nada.

Lo que estas pruebas vigilan:

* que `razon_segura` no se lea nunca, ni acabe indexada;
* que lo ordinario no reciba categoria;
* que el plural de la pregunta encuentre el singular del indice, que es donde
  se rompia sin variantes;
* que el indice se regenere igual dos veces, que es lo que `TOL-207` pide.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from experiments.adr002.candidates.adr002_a import lexical
from experiments.adr002.lateral import categoria as cat

CRITICIDAD: dict[str, Any] = {
    "DEC-003": {
        "nivel": "CRITICO",
        "razon_segura": "Limite de gasto vigente; su omision causa decision erronea.",
    },
    "MEM-014": {"nivel": "CRITICO", "razon_segura": "No debe perderse."},
    "MEM-900": {"nivel": "ORDINARIO", "razon_segura": "Nota sin valor critico."},
    "DEC-001": None,
    "MEM-016": {"nivel": "IMPORTANTE"},
}


def test_solo_entran_los_que_el_canon_no_declara_ordinarios() -> None:
    assert cat.identidades_con_categoria(CRITICIDAD) == (
        "DECISION:3",
        "MEMORIA:14",
        "MEMORIA:16",
    )


def test_la_razon_segura_no_se_lee_ni_se_indexa(tmp_path: Path) -> None:
    """Prohibido por el encargo, y ademas equivale al oraculo.

    `razon_segura` dice **por que** un elemento importa —«su omision causa
    decision erronea»—, que es informacion sobre la respuesta correcta. Lo unico
    que entra aqui es que el elemento *pertenece* a una categoria.
    """
    ruta = tmp_path / "c.sqlite3"
    registro = cat.construir(ruta, CRITICIDAD)

    conexion = sqlite3.connect(str(ruta))
    guardado = " ".join(str(f[0]) for f in conexion.execute(f"SELECT contenido FROM {cat.TABLA}"))
    conexion.close()

    for prohibida in ("omision", "erronea", "gasto", "vigente", "perderse"):
        assert prohibida not in guardado.lower(), f"«{prohibida}» viene de razon_segura"
    assert registro["razon_segura_leida"] is False
    assert "razon" not in json.dumps(registro, ensure_ascii=False).lower().replace(
        "razon_segura_leida", ""
    )


def test_el_plural_de_la_pregunta_encuentra_el_singular_del_indice() -> None:
    """Donde se rompia sin variantes. `FTS5` casa tokens, no lematiza.

    El banco pregunta «Dame todas las **restricciones** esenciales», y el
    vocabulario congelado dice «restriccion». Sin expandir, no se tocan.
    """
    palabras = cat.palabras_de_categoria()
    consulta = lexical.terminos_significativos("Dame todas las restricciones esenciales.")

    assert "restricciones" in consulta
    assert "restricciones" in palabras, "el plural que usa la pregunta tiene que estar indexado"
    assert "restriccion" in palabras


def test_el_indice_se_regenera_identico(tmp_path: Path) -> None:
    """`TOL-207`: un derivado tiene que poder borrarse y rehacerse igual."""
    primero = cat.construir(tmp_path / "a.sqlite3", CRITICIDAD)
    segundo = cat.construir(tmp_path / "b.sqlite3", CRITICIDAD)
    assert primero == segundo
    assert (tmp_path / "a.sqlite3").read_bytes() == (tmp_path / "b.sqlite3").read_bytes()


def test_el_vocabulario_es_el_que_se_congelo_antes_de_medir() -> None:
    """`§8.1`: elegir las palabras ahora, sabiendo que casos fallan, seria
    fijar la medida sobre el resultado."""
    from experiments.adr002.modelo_local.medir import VOCABULARIO_DE_CATEGORIA

    assert cat.VOCABULARIO == VOCABULARIO_DE_CATEGORIA


def test_un_canon_sin_criticos_deja_el_indice_vacio_y_no_revienta(tmp_path: Path) -> None:
    ruta = tmp_path / "vacio.sqlite3"
    registro = cat.construir(ruta, {"DEC-001": None, "MEM-900": {"nivel": "ORDINARIO"}})
    assert registro["identidades"] == []
    conexion = sqlite3.connect(str(ruta))
    assert conexion.execute(f"SELECT count(*) FROM {cat.TABLA}").fetchone()[0] == 0
    conexion.close()
