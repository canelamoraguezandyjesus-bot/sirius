"""La memoria común se genera y nunca se cura (ADR-171).

Tres cosas se fijan aquí, y las tres son el mismo criterio de parada de la nota
de arranque de ADR-171:

- **(a)** el generador solo depende del árbol: ni reloj, ni red, ni git. Se
  comprueba sobre el código fuente del módulo y sobre dos generaciones seguidas;
- **(b)** la guardia falla contra una mutación —un ADR que cambia sin regenerar,
  una edición a mano— y el `MEMORIA.md` confirmado en este árbol está al día;
- **(c)** la vista cabe en una sola lectura (120 KB).

Y el cableado: el comando existe en `[project.scripts]`, `reflejar-desenlace.yml`
lo invoca de verdad y `AGENTS.md` ordena leer la vista. En este repositorio han
aparecido seis piezas correctas a las que no llamaba nadie; esta no será la
séptima.
"""

from __future__ import annotations

import importlib
import inspect
import json
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from sirius_engine import memoria
from sirius_engine.memoria import (
    COMANDO,
    FICHERO_DESENLACES,
    FICHERO_MEMORIA,
    SIN_FECHA,
    comprobar_memoria,
    escribir_memoria,
    generar_desenlaces,
    generar_memoria,
    leer_decisiones,
    leer_encargos,
)
from sirius_engine.memoria_cli import main

RAIZ_REPO = Path(__file__).resolve().parents[2]
LIMITE_DE_LECTURA = 120_000


# --- Un árbol mínimo ----------------------------------------------------------


def _escribir(ruta: Path, texto: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8", newline="\n")


def _adr(numero: str, titulo: str, decision: str, *, estado: str = "PROPUESTO") -> str:
    return (
        f"# ADR-{numero} — {titulo}\n\n- Estado: {estado}\n- Fecha: 2026-0{numero[-1]}-01\n"
        f"- Aprobación: la fusión\n\n## Contexto y problema\n\nAlgo.\n\n"
        f"## Decisión\n\n{decision}\n\n## Consecuencias\n\nOtras.\n"
    )


def _arbol_minimo(raiz: Path) -> Path:
    decisiones = raiz / "docs" / "decisions"
    _escribir(
        decisiones / "ADR-001-la-primera.md",
        _adr(
            "001",
            "La primera",
            "**Se decide A**, con  dos espacios.\n\nSegundo párrafo.",
            estado="APROBADO",
        ),
    )
    _escribir(
        decisiones / "ADR-002-la-segunda.md",
        _adr("002", "La segunda", "Tres piezas, y ninguna más:\n\n- uno\n- dos\n\nY luego prosa."),
    )
    _escribir(
        decisiones / "ADR-002-la-repetida.md",
        _adr("002", "La repetida", "x " * 300, estado="SUPERADO por ADR-003 (ver)"),
    )
    _escribir(
        decisiones / "ADR-003-sin-decision.md",
        "# ADR-003 — Sin decisión\n\n- Estado: RECHAZADO\n- Fecha: 2026-03-01\n\n"
        "## Contexto\n\nNada.\n",
    )
    _escribir(decisiones / "PLANTILLA.md", "# ADR-NNN — plantilla\n\n## Decisión\n\nNo cuenta.\n")
    _escribir(
        raiz / "docs" / "implementation" / "bloques_del_motor.yml",
        "bloques:\n  - id: A1\n    titulo: Uno\n    estado: cerrado\n"
        "  - id: A2\n    titulo: Dos | con barra\n    estado: pendiente\n",
    )
    _escribir(
        raiz / "docs" / "audits" / "registro_defectos.yml",
        "defectos:\n  - id: H-1\n    titulo: Cerrado\n    estado: cerrado\n"
        "  - id: H-2\n    titulo: Abierto\n    estado: abierto\n",
    )
    _escribir(
        raiz / "docs" / "investigaciones" / "2026-01-02-una-foto.md",
        "---\ntitulo: Una foto\nfecha: 2026-01-02\ncaduca_con:\n  - los precios\n  - los modelos\n"
        "  - los clientes MCP: cambian cada mes\n"
        "estado: VIGENTE\n---\n\n# Otro título\n",
    )
    _escribir(raiz / "docs" / "implementation" / "PLAN.md", "# El plan\n\nSin fecha.\n")
    _escribir(
        raiz / "docs" / "evolution" / "STATUS.md",
        "# Estado\n\nÚltima actualización: 03-01-2026.\n",
    )
    _escribir(raiz / "README.md", "# Léeme\n")
    _escribir(raiz / FICHERO_MEMORIA, "no cuenta como documento")
    return raiz


@pytest.fixture
def arbol(tmp_path: Path) -> Path:
    return _arbol_minimo(tmp_path)


# --- La tabla de decisiones ---------------------------------------------------


def test_las_decisiones_van_de_la_mas_reciente_a_la_mas_antigua_y_no_pierden_repetidas(
    arbol: Path,
) -> None:
    decisiones = leer_decisiones(arbol)
    assert [d.numero for d in decisiones] == [3, 2, 2, 1]
    assert [d.ruta for d in decisiones][1:3] == [
        "docs/decisions/ADR-002-la-repetida.md",
        "docs/decisions/ADR-002-la-segunda.md",
    ]


def test_el_resumen_es_el_primer_parrafo_de_la_decision_tal_cual(arbol: Path) -> None:
    por_ruta = {d.ruta.rsplit("/", 1)[1]: d for d in leer_decisiones(arbol)}
    primera = por_ruta["ADR-001-la-primera.md"]
    assert primera.resumen == "Se decide A, con dos espacios."
    assert primera.titulo == "La primera"
    assert (primera.fecha, primera.estado) == ("2026-01-01", "APROBADO")
    segunda = por_ruta["ADR-002-la-segunda.md"]
    assert segunda.resumen == "Tres piezas, y ninguna más: uno dos"
    repetida = por_ruta["ADR-002-la-repetida.md"]
    assert repetida.resumen.endswith("…") and len(repetida.resumen) <= memoria.LONGITUD_RESUMEN + 1
    assert repetida.estado == "SUPERADO por ADR-003"
    assert por_ruta["ADR-003-sin-decision.md"].resumen == "(sin sección Decisión)"


# --- Documentos, registros e investigaciones -----------------------------------


def test_la_fecha_es_la_declarada_y_la_vista_no_data_nada(arbol: Path) -> None:
    texto = generar_memoria(arbol)
    assert "| 2026-01-03 | [Estado](docs/evolution/STATUS.md) |" in texto
    assert f"| {SIN_FECHA} | [El plan](docs/implementation/PLAN.md) |" in texto
    assert f"| {SIN_FECHA} | [Léeme](README.md) |" in texto
    assert "no cuenta como documento" not in texto
    assert f"({FICHERO_MEMORIA})" not in texto


def test_los_registros_se_cuentan_y_solo_los_defectos_sin_cerrar_se_listan(arbol: Path) -> None:
    texto = generar_memoria(arbol)
    assert "- Bloques del motor: 1 cerrado, 1 pendiente." in texto
    assert "- Defectos registrados: 1 abierto, 1 cerrado." in texto
    assert "| A2 | pendiente | Dos \\| con barra |" in texto
    assert "| H-2 | abierto | Abierto |" in texto
    assert "| H-1 | cerrado |" not in texto


def test_una_investigacion_declara_fecha_estado_y_de_que_depende(arbol: Path) -> None:
    texto = generar_memoria(arbol)
    assert (
        "| 2026-01-02 | VIGENTE | [Una foto](docs/investigaciones/2026-01-02-una-foto.md) "
        "| los precios; los modelos; los clientes MCP: cambian cada mes |"
    ) in texto


# --- Criterio (a): solo el árbol ----------------------------------------------


def test_el_generador_no_mira_el_reloj_ni_la_red_ni_git() -> None:
    fuente = inspect.getsource(memoria)
    for prohibido in ("datetime", "subprocess", "urllib", "httpx", "time.time", "os.environ"):
        assert prohibido not in fuente, (
            f"memoria.py usa {prohibido!r}: una vista que cambia sin que cambie el árbol no "
            "se puede guardar con una prueba (ADR-171, criterio (a))"
        )


def test_dos_generaciones_del_mismo_arbol_son_identicas(arbol: Path) -> None:
    assert generar_memoria(arbol) == generar_memoria(arbol)


# --- Criterio (b): la guardia -------------------------------------------------


def test_la_guardia_calla_cuando_la_vista_esta_al_dia_y_habla_cuando_no(arbol: Path) -> None:
    (arbol / FICHERO_MEMORIA).unlink()
    assert comprobar_memoria(arbol) is not None
    escribir_memoria(arbol)
    assert comprobar_memoria(arbol) is None

    primera = arbol / "docs" / "decisions" / "ADR-001-la-primera.md"
    primera.write_text(primera.read_text(encoding="utf-8").replace("La primera", "Otra"), "utf-8")
    problema = comprobar_memoria(arbol)
    assert problema is not None and f"uv run {COMANDO} conocimiento" in problema

    escribir_memoria(arbol)
    assert comprobar_memoria(arbol) is None
    fichero = arbol / FICHERO_MEMORIA
    fichero.write_text(fichero.read_text(encoding="utf-8") + "\n- añadido a mano\n", "utf-8")
    assert comprobar_memoria(arbol) is not None


def test_la_memoria_confirmada_en_este_arbol_esta_al_dia() -> None:
    problema = comprobar_memoria(RAIZ_REPO)
    assert problema is None, problema


def test_la_memoria_cabe_en_una_sola_lectura() -> None:
    tamano = len((RAIZ_REPO / FICHERO_MEMORIA).read_bytes())
    assert tamano <= LIMITE_DE_LECTURA, (
        f"{FICHERO_MEMORIA} pesa {tamano} bytes: por encima de {LIMITE_DE_LECTURA} deja de "
        "leerse entera de una vez y vuelve a ser un corpus (ADR-171, criterio (c))"
    )


# --- La vista de desenlaces ---------------------------------------------------


def _suceso(work_id: str, kind: str, cuando: str, **entidad: Any) -> str:
    base: dict[str, Any] = {
        "clase": "programacion",
        "estado": "planned",
        "fase": "preparar",
        "created_at": "2026-09-01T10:00:00+00:00",
        "objetivo": f"Objetivo de {work_id}\n\n## Contexto\n\nMucho texto.",
        "resultado": None,
        "diagnostico": None,
    }
    base.update(entidad)
    return json.dumps(
        {
            "aggregate_id": work_id,
            "aggregate_type": "work_item",
            "kind": kind,
            "occurred_at": cuando,
            "entity": base,
        }
    )


@pytest.fixture
def diario(tmp_path: Path) -> Path:
    ruta = tmp_path / "diario.jsonl"
    lineas = [
        _suceso("WI-A", "work_item_created", "2026-09-01T10:00:00+00:00"),
        "",
        json.dumps(
            {
                "aggregate_id": "R-1",
                "aggregate_type": "run",
                "occurred_at": "2026-09-01T11:00:00+00:00",
            }
        ),
        _suceso(
            "WI-B",
            "work_item_created",
            "2026-09-02T10:00:00+00:00",
            created_at="2026-09-02T10:00:00+00:00",
        ),
        _suceso(
            "WI-A",
            "work_item_delivered",
            "2026-09-03T10:00:00+00:00",
            estado="delivered",
            fase="entregar",
            resultado={"numero_incidencia": 12, "merge_sha": "abcdef0123456789"},
        ),
        _suceso(
            "WI-B",
            "work_item_failed_safely",
            "2026-09-04T10:00:00+00:00",
            estado="failed_safely",
            fase="reparar",
            diagnostico="No hubo veredicto.\n\n- Registro: https://github.com/o/r/actions/runs/99/attempts/1",
        ),
    ]
    _escribir(ruta, "\n".join(lineas) + "\n")
    _escribir(
        tmp_path / "diario-despacho.jsonl",
        json.dumps(
            {"kind": "dispatch_episode_recorded", "work_id": "WI-B", "numero_incidencia": 13}
        )
        + "\n",
    )
    return ruta


def test_los_encargos_salen_del_ultimo_suceso_de_cada_uno_y_del_mas_reciente_al_mas_antiguo(
    diario: Path,
) -> None:
    encargos, total, ultimo = leer_encargos(diario, diario.with_name("diario-despacho.jsonl"))
    assert (total, ultimo) == (5, "2026-09-04T10:00:00+00:00")
    assert [e.work_id for e in encargos] == ["WI-B", "WI-A"]
    b, a = encargos
    assert (a.estado, a.fase, a.incidencia, a.merge_sha, a.run, a.sucesos) == (
        "delivered",
        "entregar",
        12,
        "abcdef0123456789",
        None,
        2,
    )
    assert (b.estado, b.incidencia, b.run) == (
        "failed_safely",
        13,
        "https://github.com/o/r/actions/runs/99/attempts/1",
    )
    assert a.objetivo == "Objetivo de WI-A"


def test_la_vista_de_desenlaces_enlaza_la_evidencia(diario: Path) -> None:
    texto = generar_desenlaces(diario, diario.with_name("diario-despacho.jsonl"))
    assert "5 sucesos, el último el 2026-09-04 10:00 UTC" in texto
    assert "| delivered | 1 |" in texto and "| failed_safely | 1 |" in texto
    assert (
        "[#12](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/12), fusión `abcdef0`"
        in texto
    )
    assert (
        "[#13](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/13), [run](https://github.com/o/r/actions/runs/99/attempts/1)"
        in texto
    )
    assert texto.index("| WI-B |") < texto.index("| WI-A |")


def test_un_diario_corrupto_se_declara_con_su_linea(tmp_path: Path) -> None:
    ruta = tmp_path / "diario.jsonl"
    _escribir(ruta, '{"aggregate_type": "work_item"}\nesto no es json\n')
    with pytest.raises(ValueError, match=r"diario\.jsonl:2"):
        leer_encargos(ruta)


# --- El comando ---------------------------------------------------------------


def _scripts_declarados() -> dict[str, str]:
    datos = tomllib.loads((RAIZ_REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in datos["project"]["scripts"].items()}


def test_el_comando_esta_declarado_y_resuelve() -> None:
    scripts = _scripts_declarados()
    assert COMANDO in scripts, f"`[project.scripts]` no declara {COMANDO!r}: {sorted(scripts)}"
    modulo, _, funcion = scripts[COMANDO].partition(":")
    resuelta = cast(Callable[..., int], getattr(importlib.import_module(modulo), funcion))
    assert resuelta is main


def test_conocimiento_escribe_y_comprobar_distingue(
    arbol: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (arbol / FICHERO_MEMORIA).unlink()
    assert main(["conocimiento", "--raiz", str(arbol), "--comprobar"]) == 1
    assert main(["conocimiento", "--raiz", str(arbol)]) == 0
    assert (arbol / FICHERO_MEMORIA).read_text(encoding="utf-8") == generar_memoria(arbol)
    assert main(["conocimiento", "--raiz", str(arbol), "--comprobar"]) == 0
    assert main(["conocimiento", "--raiz", str(arbol / "docs")]) == 2
    assert "no parece la raíz" in capsys.readouterr().err


def test_desenlaces_escribe_junto_al_diario_y_declara_el_que_falta(
    diario: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["desenlaces", "--diario", str(diario)]) == 0
    escrito = (diario.with_name(FICHERO_DESENLACES)).read_text(encoding="utf-8")
    assert escrito == generar_desenlaces(diario, diario.with_name("diario-despacho.jsonl"))
    assert main(["desenlaces", "--diario", str(tmp_path / "no.jsonl")]) == 2
    assert "no existe el diario" in capsys.readouterr().err


# --- El cableado --------------------------------------------------------------


def test_el_reflejo_publica_la_vista_de_desenlaces_aunque_el_reflejo_falle() -> None:
    workflow = yaml.safe_load(
        (RAIZ_REPO / ".github" / "workflows" / "reflejar-desenlace.yml").read_text(encoding="utf-8")
    )
    pasos = workflow["jobs"]["reflejo"]["steps"]
    publican = [p for p in pasos if f"{COMANDO} desenlaces" in str(p.get("run", ""))]
    assert len(publican) == 1, (
        f"reflejar-desenlace.yml no invoca `{COMANDO} desenlaces`: la vista existiría y "
        "nadie la escribiría (la séptima pieza sin llamante)"
    )
    assert str(publican[0].get("if", "")).strip() == "always()"
    nombres = [str(p.get("name", "")) for p in pasos]
    assert nombres.index(str(publican[0]["name"])) < nombres.index("Confirmar el diario")


def test_agents_ordena_leer_la_memoria_primero() -> None:
    texto = (RAIZ_REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert f"`{FICHERO_MEMORIA}`" in texto
    assert f"uv run {COMANDO} conocimiento" in texto


# --- La regla de la memoria de sesión (ADR-172) -------------------------------
#
# Una obligación por entrada, y cada una con el trozo de texto que la sostiene.
# La primera versión de esta prueba comprobaba cuatro expresiones sueltas sobre
# el fichero entero: se podían borrar las dos instrucciones y la tabla de reparto
# completa y seguía pasando (hallazgo de la revisión de la PR #585). Ahora cada
# obligación se comprueba por separado y **dentro de su sección**, y
# `test_cada_obligacion_del_reparto_es_imprescindible` demuestra, retirando cada
# una, que ninguna sobra.

TITULO_SECCION_SESION = "## La memoria de sesión, si tienes su herramienta (ADR-172)"

OBLIGACIONES_DEL_REPARTO: tuple[tuple[str, str], ...] = (
    ("solo aplica a quien tenga la herramienta", "solo existe si tu entorno trae la herramienta"),
    ("buscar al empezar", "**Al empezar**"),
    ("guardar al terminar", "**Al terminar**"),
    ("el espacio canónico, con su nombre", "`repo_sirius__e87a5bbe75fe00b6`"),
    ("pasar el espacio en cada llamada", "`containerTag` en **cada** búsqueda"),
    ("parar si el espacio no aparece", "**dilo y para**"),
    ("lo decidido va al repositorio", "**El repositorio**, con su PR, su ADR y su prueba"),
    ("lo pendiente va a la memoria de sesión", "**La memoria de sesión** |"),
    ("sobre el motor manda su diario", "**Su diario**, que manda sobre las dos"),
    ("lo que solo vive ahí no está decidido", "no está tomada"),
    ("sale a un tercero", "sale a un servicio de terceros"),
    ("ahí no van secretos", "no van claves ni secretos"),
)


def _seccion_de_la_memoria_de_sesion(texto: str) -> str:
    """El cuerpo de la sección de ADR-172, del título al siguiente `## `."""
    _, marca, resto = texto.partition(TITULO_SECCION_SESION)
    assert marca, (
        f"AGENTS.md ya no tiene la sección {TITULO_SECCION_SESION!r}: la regla de "
        "la memoria de sesión desapareció entera (ADR-172)"
    )
    cuerpo, _, _ = resto.partition("\n## ")
    return cuerpo


def test_agents_declara_el_reparto_entre_las_dos_memorias() -> None:
    """Las doce obligaciones de ADR-172, cada una dentro de su sección.

    No comprueba conducta -no se puede-: comprueba que la regla siga ESCRITA
    donde toda IA la lee, y completa. Se exige dentro de la sección a propósito:
    dejar la frase suelta en otra parte del fichero no vale.
    """
    seccion = _seccion_de_la_memoria_de_sesion((RAIZ_REPO / "AGENTS.md").read_text("utf-8"))
    perdidas = [nombre for nombre, marca in OBLIGACIONES_DEL_REPARTO if marca not in seccion]
    assert perdidas == [], (
        f"la sección de la memoria de sesión perdió estas obligaciones: {perdidas}. "
        "Una regla incompleta es peor que ninguna: dice qué hacer y calla lo que "
        "hace falta para hacerlo bien (ADR-172)"
    )


@pytest.mark.parametrize(("nombre", "marca"), OBLIGACIONES_DEL_REPARTO, ids=lambda v: v[:28])
def test_cada_obligacion_del_reparto_es_imprescindible(nombre: str, marca: str) -> None:
    """Retirar CUALQUIERA de las doce tiene que hacer fallar la prueba de arriba.

    Es la prueba por mutación de ADR-001, automatizada: sin esto, nada impide que
    la lista de obligaciones se quede corta otra vez y la comprobación siga en
    verde, que es justo el defecto que la revisión de la PR #585 encontró.
    """
    seccion = _seccion_de_la_memoria_de_sesion((RAIZ_REPO / "AGENTS.md").read_text("utf-8"))
    mutada = seccion.replace(marca, "")
    assert marca not in mutada
    supervivientes = [n for n, m in OBLIGACIONES_DEL_REPARTO if m in mutada]
    assert nombre not in supervivientes, (
        f"quitar «{nombre}» de la sección no lo hace detectable: la marca {marca!r} "
        "no distingue esa obligación de las demás"
    )
