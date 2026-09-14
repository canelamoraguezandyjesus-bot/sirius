"""La cola: una rama entra a revisión solo si `main` ya está dentro de ella.

Lo que estas pruebas fijan no es «el módulo devuelve lo que devuelve», sino la
propiedad que costó una noche en rojo: si la punta de `main` no está en la rama,
la combinación que aterrizaría no la ha probado nadie, y la rama espera.

Cada aserción de abajo se ha visto FALLAR contra una versión rota a propósito;
las mutaciones están en el ADR. Una guarda que nunca se vio caer no prueba nada
(ADR-172).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MODULO = RAIZ / "scripts" / "automation" / "sirius_cola.py"


def _cargar() -> ModuleType:
    """Se carga por ruta, como lo hará el runner: sin instalar nada."""
    spec = importlib.util.spec_from_file_location("sirius_cola", MODULO)
    assert spec is not None and spec.loader is not None, f"no se pudo cargar {MODULO}"
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


cola = _cargar()


def _comparacion(tmp_path: Path, cuerpo: object) -> Path:
    """Cada comparación en su propio fichero.

    La primera versión de este ayudante escribía siempre en `compare.json`, así
    que dos comparaciones dentro de la misma prueba se pisaban y la segunda
    decidía por las dos. Lo cazó `test_el_codigo_de_salida_distingue_pasar_de_esperar`,
    que es la única que usa dos a la vez.
    """
    ruta = tmp_path / f"compare-{abs(hash(json.dumps(cuerpo, sort_keys=True)))}.json"
    ruta.write_text(json.dumps(cuerpo), encoding="utf-8")
    return ruta


# --- Lo que deja pasar -------------------------------------------------------


@pytest.mark.parametrize("estado", ["identical", "ahead"])
def test_con_la_punta_de_main_dentro_la_rama_entra(tmp_path: Path, estado: str) -> None:
    """Los dos únicos estados que significan «main ya está aquí».

    `identical` es la rama que no ha divergido; `ahead`, la que tiene trabajo
    propio encima de esa punta. En los dos casos lo que se revise es lo que
    aterrizará.
    """
    veredicto = cola.puede_entrar_a_revision(_comparacion(tmp_path, {"status": estado}))
    assert veredicto.al_dia, f"con status {estado!r} la rama tiene la punta de main"


# --- Lo que hace esperar -----------------------------------------------------


@pytest.mark.parametrize("estado", ["behind", "diverged"])
def test_sin_la_punta_de_main_la_rama_espera(tmp_path: Path, estado: str) -> None:
    """El caso que dejó `main` en rojo: #611 entró sin tener #602."""
    ruta = _comparacion(tmp_path, {"status": estado, "behind_by": 1})
    assert not cola.puede_entrar_a_revision(ruta).al_dia, (
        f"con status {estado!r} hay commits en main que la rama no tiene: "
        "revisar aquí aprobaría una combinación que nadie ha probado"
    )


def test_la_espera_dice_cuanto_le_falta(tmp_path: Path) -> None:
    """Una espera que no se cuenta no se distingue de un atasco (ADR-183)."""
    ruta = _comparacion(tmp_path, {"status": "behind", "behind_by": 3})
    motivo = cola.puede_entrar_a_revision(ruta).motivo
    assert "3" in motivo and "detrás" in motivo, (
        f"el motivo tiene que decir cuánto le falta; salió {motivo!r}"
    )


def test_un_solo_commit_por_detras_se_dice_en_singular(tmp_path: Path) -> None:
    """Un mensaje que dice «1 commits» delata que nadie lo leyó nunca."""
    ruta = _comparacion(tmp_path, {"status": "behind", "behind_by": 1})
    motivo = cola.puede_entrar_a_revision(ruta).motivo
    assert "1 commit " in motivo and "commits" not in motivo, (
        f"con uno solo va en singular; salió {motivo!r}"
    )


# --- Fail-closed: todo lo que impida AFIRMAR que está al día ------------------


def test_sin_fichero_la_rama_espera(tmp_path: Path) -> None:
    assert not cola.puede_entrar_a_revision(tmp_path / "no-existe.json").al_dia


def test_con_json_roto_la_rama_espera(tmp_path: Path) -> None:
    ruta = tmp_path / "compare.json"
    ruta.write_text("{ esto no es json", encoding="utf-8")
    assert not cola.puede_entrar_a_revision(ruta).al_dia


@pytest.mark.parametrize("cuerpo", [[], "ahead", 7, None])
def test_si_la_comparacion_no_es_un_objeto_la_rama_espera(tmp_path: Path, cuerpo: object) -> None:
    """Una lista o una cadena no traen `status`; afirmar desde ahí sería inventar."""
    assert not cola.puede_entrar_a_revision(_comparacion(tmp_path, cuerpo)).al_dia


def test_sin_status_la_rama_espera(tmp_path: Path) -> None:
    ruta = _comparacion(tmp_path, {"behind_by": 0, "ahead_by": 2})
    assert not cola.puede_entrar_a_revision(ruta).al_dia


def test_con_un_status_desconocido_la_rama_espera(tmp_path: Path) -> None:
    """Si GitHub añadiera un estado nuevo, esperar es el error barato.

    Esperar se recupera solo: la condición se vuelve a evaluar. Dejar pasar de
    más mete en `main` algo que nadie probó, y eso se paga en rojo.
    """
    ruta = _comparacion(tmp_path, {"status": "estado-que-hoy-no-existe"})
    assert not cola.puede_entrar_a_revision(ruta).al_dia


@pytest.mark.parametrize("valor", [None, "1", 1.5, True])
def test_un_status_que_no_es_texto_hace_esperar(tmp_path: Path, valor: object) -> None:
    """`True` entra a propósito: en Python es `int`, y un `in` descuidado lo colaría."""
    assert not cola.puede_entrar_a_revision(_comparacion(tmp_path, {"status": valor})).al_dia


def test_una_comparacion_rota_no_afirma_que_la_rama_va_por_detras(tmp_path: Path) -> None:
    """Esperar por lo que no se pudo leer NO es lo mismo que ir por detrás.

    Con `status` ilegible pero `behind_by` presente, decir «vas 2 commits por
    detrás» es afirmar algo que el dato no sostiene, y manda a quien lo lea a
    ponerse al día de algo que quizá ya tiene. El motivo tiene que decir que no
    se pudo leer.

    Esta prueba existe porque la mutación M3 -quitar la comprobación de que
    `status` es texto- sobrevivió a la primera pasada: la garantía estaba en la
    prosa del módulo y en ninguna aserción.
    """
    ruta = _comparacion(tmp_path, {"status": None, "behind_by": 2})
    veredicto = cola.puede_entrar_a_revision(ruta)
    assert not veredicto.al_dia
    assert "detrás" not in veredicto.motivo, (
        f"no se puede afirmar que va por detrás con `status` ilegible; salió {veredicto.motivo!r}"
    )
    assert "status" in veredicto.motivo


# --- El código de salida ES la respuesta -------------------------------------


def test_el_codigo_de_salida_distingue_pasar_de_esperar(tmp_path: Path) -> None:
    """El workflow se ramifica por el código, no por el texto.

    Si se ramificara por el mensaje, cambiarle una palabra convertiría un
    «espera» en un «pasa» sin que ninguna prueba se enterara.
    """
    al_dia = _comparacion(tmp_path, {"status": "ahead"})
    detras = _comparacion(tmp_path, {"status": "behind", "behind_by": 2})
    assert cola.main([str(al_dia)]) == 0
    assert cola.main([str(detras)]) != 0


def test_el_motivo_sale_por_la_salida_estandar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Quien llama tiene que poder escribir la espera en la incidencia."""
    cola.main([str(_comparacion(tmp_path, {"status": "behind", "behind_by": 2}))])
    assert "detrás" in capsys.readouterr().out


def test_el_modulo_no_importa_nada_de_fuera_de_la_estandar() -> None:
    """Corre con el `python3` a secas del runner, sin `uv` ni dependencias."""
    fuente = MODULO.read_text(encoding="utf-8")
    importados = {
        linea.split()[1].split(".")[0]
        for linea in fuente.splitlines()
        if linea.startswith(("import ", "from ")) and "__future__" not in linea
    }
    assert importados <= set(sys.stdlib_module_names), (
        f"solo biblioteca estándar; sobran {importados - set(sys.stdlib_module_names)}"
    )


# --- La mitad que faltó las ocho veces: alguien que la llame -----------------

AVANCE = RAIZ / ".github" / "workflows" / "advance-sirius-after-quality.yml"


def _avance_sin_comentarios() -> str:
    """El workflow sin sus líneas de comentario.

    Buscar el nombre del módulo en el fichero entero no vale: la cabecera de
    este workflow y sus comentarios explican la historia, así que una mutación
    que quitara la llamada seguiría encontrando el nombre escrito. Es la misma
    lección que `_codigo_sin_comentarios` en test_reanudar_una_parada.py: una
    prueba que se conforma con que algo se MENCIONE certifica documentación.
    """
    return "\n".join(
        linea
        for linea in AVANCE.read_text(encoding="utf-8").splitlines()
        if not linea.lstrip().startswith("#")
    )


def test_el_avance_llama_a_la_cola() -> None:
    """ADR-191 construyó la condición y dejó escrito que NO la cableaba.

    Ocho veces ha pasado ya en esta casa que una pieza correcta se quedara sin
    llamante, con sus pruebas en verde vigilando código que no se ejecutaba.
    `tests/automation/test_piezas_con_llamante.py` cierra esa clase para los
    módulos de `src/sirius_engine`; `scripts/automation/` queda fuera de su
    inventario, y ahí es donde vive esta pieza. Así que aquí va su llamante.
    """
    assert "sirius_cola.py" in _avance_sin_comentarios(), (
        "`sirius_cola.py` decide si una rama puede entrar a revisión y el "
        "workflow que repone `sirius:review-requested` no lo llama: la "
        "condición existiría sin gobernar nada"
    )


def test_la_cola_se_consulta_antes_de_reponer_la_revision() -> None:
    """Preguntar después de haber repuesto la etiqueta no es preguntar.

    Sin esta, una mutación que dejara la llamada DESPUÉS de la transición
    pasaría la prueba de arriba en verde y la rama entraría a revisión igual.
    """
    texto = _avance_sin_comentarios()
    consulta = texto.find("sirius_cola.py")
    repone = texto.find('"sirius:review-requested"')
    assert consulta != -1, "no se encontró la llamada a la cola"
    assert repone != -1, "no se encontró la transición que repone la revisión"
    assert consulta < repone, (
        "la cola se consulta DESPUÉS de reponer `sirius:review-requested`: "
        "la rama ya habría entrado a revisión cuando se pregunta si podía"
    )


def test_la_puesta_al_dia_no_empuja_con_el_token_del_workflow() -> None:
    """Un push con `GITHUB_TOKEN` no dispara workflows (ADR-183).

    Si la rama se pusiera al día con él, Quality no volvería a correr y la rama
    quedaría esperando otra vez: el mismo atasco con otra cara. Por eso el
    checkout que hace la puesta al día lleva el PAT, igual que el del corrector.
    """
    import yaml

    flujo = yaml.safe_load(AVANCE.read_text(encoding="utf-8"))
    pasos = [
        paso
        for trabajo in flujo["jobs"].values()
        for paso in trabajo.get("steps", [])
        if str(paso.get("uses", "")).startswith("actions/checkout")
    ]
    con_pat = [
        paso for paso in pasos if "SIRIUS_BOT_TOKEN" in str(paso.get("with", {}).get("token", ""))
    ]
    assert con_pat, (
        "ningún checkout de este workflow lleva el PAT: un push hecho con "
        "`GITHUB_TOKEN` no dispara workflows, así que Quality no volvería a "
        "correr y la rama se quedaría esperando otra vez (ADR-183)"
    )
    for paso in con_pat:
        assert paso.get("with", {}).get("persist-credentials") is True, (
            "el checkout que trae el PAT tiene que persistir credenciales o el "
            "push no podrá autenticarse"
        )
    assert "--force" not in _avance_sin_comentarios(), (
        "la puesta al día nunca reescribe la historia de una rama que no es suya"
    )
