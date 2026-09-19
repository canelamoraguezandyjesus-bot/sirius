"""El rechazo de la combinación imposible en el diagnóstico del banco (ADR-203).

`scripts/diagnosticar_busqueda_del_banco.py --puerta-cerrada` mide el camino
que ejecuta hoy el Sirius del propietario: `rank_con_cupo` se va por
`_rank_via_current_pipeline(query_text)`, que **solo recibe el texto de la
consulta**. Allí no se construye ninguna `Peticion`, así que las tres palancas
de laboratorio —`--peticion`, `--ejes`, `--cupo`— no pueden influir en el
resultado. Una corrida `--puerta-cerrada --peticion` daría exactamente el
mismo número que `--puerta-cerrada` a secas, pero llevaría escrito al lado que
la petición estaba puesta, y quien la comparase con la cifra de puerta abierta
`--peticion` estaría comparando dos cosas que no comparten condiciones.

Por eso el guion no lo anota al pie: **rechaza y no mide**. Estas pruebas fijan
esa propiedad. La tabla se prueba sobre la función pura —es la que decide— y el
código de salida, sobre el guion de verdad, porque un rechazo que no se
tradujera en un código distinto de 0 no detendría a nadie.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

#: Importado por nombre, no con un `import` normal, y la razón es concreta: el
#: guion importa el arnés como `tests.acceptance.test_pa_0_2_rec_01_banco_
#: evidencia`, y `mypy src tests` ve ese mismo fichero como módulo de primer
#: nivel (`tests/` no es un paquete). Un `import` estático hace que mypy siga
#: la cadena y falle con «Source file found twice under different module
#: names», que no es un defecto de este cambio sino la forma del árbol.
_guion: Any = importlib.import_module("diagnosticar_busqueda_del_banco")
_rechazo_de_puerta_cerrada = _guion._rechazo_de_puerta_cerrada
_BANDERAS_INCOMPATIBLES_CON_PUERTA_CERRADA = _guion._BANDERAS_INCOMPATIBLES_CON_PUERTA_CERRADA

_GUION = Path(__file__).resolve().parents[2] / "scripts" / "diagnosticar_busqueda_del_banco.py"


def _ejecutar(*banderas: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_GUION), *banderas],
        capture_output=True,
        text=True,
        check=False,
        cwd=_GUION.parent.parent,
    )


@pytest.mark.parametrize("bandera", _BANDERAS_INCOMPATIBLES_CON_PUERTA_CERRADA)
def test_la_puerta_cerrada_rechaza_cada_palanca_de_laboratorio(bandera: str) -> None:
    rechazo = _rechazo_de_puerta_cerrada(["--puerta-cerrada", bandera])
    assert rechazo is not None
    assert bandera in rechazo


def test_la_puerta_cerrada_nombra_todas_las_palancas_que_le_pusieron() -> None:
    """El mensaje dice cuáles sobran, no «alguna sobra»: quien lo lee tiene
    que saber qué quitar sin volver a leer el guion."""
    rechazo = _rechazo_de_puerta_cerrada(["--puerta-cerrada", "--peticion", "--cupo"])
    assert rechazo is not None
    assert "--peticion" in rechazo
    assert "--cupo" in rechazo


@pytest.mark.parametrize(
    "argumentos",
    [
        [],
        ["--puerta-cerrada"],
        ["--peticion"],
        ["--ejes", "--peticion", "--cupo"],
    ],
)
def test_lo_que_si_es_medible_no_se_rechaza(argumentos: list[str]) -> None:
    """Las tres palancas juntas siguen siendo válidas SIN `--puerta-cerrada`:
    el rechazo es de la combinación, no de las banderas."""
    assert _rechazo_de_puerta_cerrada(argumentos) is None


def test_el_guion_sale_con_error_y_sin_medir_nada() -> None:
    """La propiedad que importa de verdad: no basta con avisar. Si el guion
    imprimiera el aviso y midiera igual, la cifra engañosa estaría publicada
    y el aviso sería una nota al pie — que es justo lo que ADR-203 no quiere.
    """
    resultado = _ejecutar("--puerta-cerrada", "--peticion")
    assert resultado.returncode != 0
    assert "--peticion" in resultado.stderr
    assert "_rank_via_current_pipeline" in resultado.stderr
    assert "SIN FILTRO" not in resultado.stdout


def test_el_guion_mide_la_puerta_cerrada_a_secas() -> None:
    """El modo nuevo existe y da un número: las cuatro cifras, etiquetadas
    como puerta cerrada para que nadie las confunda con las de la abierta.
    No se fija aquí el VALOR de las cifras —lo fija la medición del banco en
    `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`, donde vive el
    arnés—, solo que el modo corre entero y publica su etiqueta."""
    resultado = _ejecutar("--puerta-cerrada")
    assert resultado.returncode == 0, resultado.stderr
    assert "[puerta=cerrada] SIN FILTRO:" in resultado.stdout
    assert "/47 exactos" in resultado.stdout


#: Un banco de juguete: `_medir` solo lee las consultas (para detectar
#: repetidas y construir la tabla por consulta) y el límite sin atar. Todo lo
#: caro queda fuera porque el arnés se sustituye por un doble.
_BANCO_MINIMO = {"casos": [{"consulta": "una consulta"}], "conteos": {"items_del_canon": 3}}


@pytest.mark.parametrize(
    ("observados", "esperado_en_el_mensaje"),
    [
        ([], "ninguna construccion"),
        ([object()], "object"),
        ([None, object()], "object"),
    ],
)
def test_la_guarda_de_puerta_cerrada_se_queja_de_lo_que_debe(
    observados: list[Any], esperado_en_el_mensaje: str
) -> None:
    """La guarda mira lo que `ContextBuilder` recibió, y una lista vacía es
    tan sospechosa como un puerto presente: sin observación no hay guarda."""
    queja = _guion._incoherencia_del_puerto_de_relevancia(observados)
    assert queja is not None
    assert esperado_en_el_mensaje in queja


def test_la_guarda_de_puerta_cerrada_calla_ante_la_construccion_de_produccion() -> None:
    assert _guion._incoherencia_del_puerto_de_relevancia([None]) is None


@pytest.mark.parametrize("el_arnes_se_fabrica_su_filtro", [False, True])
def test_la_puerta_cerrada_vigila_el_argumento_real_de_context_builder(
    monkeypatch: pytest.MonkeyPatch, el_arnes_se_fabrica_su_filtro: bool
) -> None:
    """La propiedad que la guarda anterior no tenía (CODEX-001, segunda
    vuelta): si el arnés volviera a fabricarse su propio filtro de relevancia
    en modo cerrado, el guion tiene que verlo.

    El doble contador del guion ya no se instancia en modo cerrado, así que
    `entradas` sale vacío en los DOS escenarios —por eso mirarlo no
    distinguía nada—. Lo que sí los distingue es el `relevance_filter_port`
    que `ContextBuilder` recibió de verdad, que es lo que `_medir` captura.
    """
    arnes = _guion.arnes
    monkeypatch.setattr(arnes, "ContextBuilder", lambda **kw: object(), raising=True)

    def falso_ejecutar(_ruta: Any, **kw: Any) -> Any:
        propio = _guion._FiltroQueNoDescartaYRecuerda()
        arnes.ContextBuilder(
            relevance_filter_port=(
                propio if el_arnes_se_fabrica_su_filtro else kw.get("relevance_filter_port")
            )
        )
        return object()

    monkeypatch.setattr(arnes, "_ejecutar_banco_paquete_completo", falso_ejecutar, raising=True)

    _ejecucion, entradas, _llamadas, puertos = _guion._medir(
        _BANCO_MINIMO, con_ejes=False, con_peticion=False, motor_por_etapas=False
    )

    assert entradas == []
    queja = _guion._incoherencia_del_puerto_de_relevancia(puertos)
    if el_arnes_se_fabrica_su_filtro:
        assert queja is not None
        assert "_FiltroQueNoDescartaYRecuerda" in queja
    else:
        assert puertos == [None]
        assert queja is None
