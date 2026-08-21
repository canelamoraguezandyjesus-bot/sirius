"""El comando de consola del motor: el agujero que dejó M1 (ADR-055).

M1 prometía que el propietario pudiera hablar con el motor. `SesionCLI`
existía y sus pruebas pasaban, pero **no había ningún comando que teclear**:
`[project.scripts]` no declaraba ninguna entrada del motor y nadie fuera de
`tests/` construía nunca una `SesionCLI`.

Estas pruebas parten de donde parte el propietario -la entrada declarada en
`pyproject.toml`-, no de un `import` conveniente: si mañana alguien borra la
entrada, renombra el módulo o cambia el nombre de la función, esto cae. Una
prueba que solo importara `sirius_engine.cli` no observaría el fallo que
arregla, porque el fallo era «no hay comando», no «no hay código».

Y fijan la propiedad que el comando no puede perder: **conversar y consultar
no crean trabajo** (A5-P1). El comando declina las órdenes en vez de
ejecutarlas, así que en v0 ninguna entrada puede escribir en el diario.
"""

from __future__ import annotations

import importlib
import io
import subprocess
import sys
import tomllib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sirius_engine import cli
from sirius_engine.adapters.durable.store import DurableWorkEngineStore
from sirius_engine.domain.work_item import WorkItemClass

RAIZ_REPO = Path(__file__).resolve().parents[2]
NOMBRE_COMANDO = "sirius-motor"

MainDeclarada = Callable[..., int]


def _scripts_declarados() -> dict[str, str]:
    datos = tomllib.loads((RAIZ_REPO / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = datos["project"]["scripts"]
    assert isinstance(scripts, dict)
    return {str(clave): str(valor) for clave, valor in scripts.items()}


def _main_declarada() -> MainDeclarada:
    """Resolver la función que ejecuta el comando, tal y como lo hace el instalador."""
    scripts = _scripts_declarados()
    assert NOMBRE_COMANDO in scripts, (
        f"`[project.scripts]` no declara {NOMBRE_COMANDO!r}: sin esa entrada no existe "
        f"ningún comando del motor que el propietario pueda teclear. Declaradas: {sorted(scripts)}"
    )
    modulo, _, funcion = scripts[NOMBRE_COMANDO].partition(":")
    return cast(MainDeclarada, getattr(importlib.import_module(modulo), funcion))


def _ejecutar(
    *argumentos: str, entrada: str = "", entorno: dict[str, str] | None = None
) -> tuple[int, str]:
    """Invocar el comando declarado y devolver (código de salida, salida escrita)."""
    salida = io.StringIO()
    codigo = _main_declarada()(
        list(argumentos),
        entrada=io.StringIO(entrada),
        salida=salida,
        entorno={} if entorno is None else entorno,
    )
    return codigo, salida.getvalue()


# --- 1. Existe un comando, y es el que el instalador va a crear -----------------


def test_pyproject_declara_un_comando_del_motor_que_apunta_a_algo_invocable() -> None:
    """El fallo de M1, fijado: sin esta entrada no hay nada que teclear."""
    assert callable(_main_declarada())


def test_todo_comando_declarado_apunta_a_un_modulo_que_el_paquete_construido_contiene() -> None:
    """Un comando cuyo módulo no se empaqueta está muerto en cuanto alguien instala.

    No lo caza ninguna otra prueba: el desarrollo trabaja en editable, y el
    `.pth` de la instalación editable publica `src/` entero, así que
    `sirius_engine` se importa igual estando o no estando en el paquete. Se
    comprobó construyendo el wheel de verdad: con `module-name = "sirius"`
    traía 172 ficheros de `sirius/` y **0** de `sirius_engine/`.
    """
    datos = tomllib.loads((RAIZ_REPO / "pyproject.toml").read_text(encoding="utf-8"))
    empaquetados = datos["tool"]["uv"]["build-backend"]["module-name"]
    if isinstance(empaquetados, str):
        empaquetados = [empaquetados]

    for comando, destino in _scripts_declarados().items():
        raiz_modulo = destino.partition(":")[0].split(".")[0]
        assert raiz_modulo in empaquetados, (
            f"el comando {comando!r} apunta a {raiz_modulo!r}, que el backend de construcción "
            f"no empaqueta ({empaquetados}): funcionaría en editable y no una vez instalado"
        )


def test_el_comando_instalado_se_ejecuta_de_verdad(tmp_path: Path) -> None:
    """No un `import` desde la prueba: el ejecutable que `uv sync` deja en el entorno.

    Es la única forma de comprobar lo que el propietario hace de verdad
    (teclear el nombre). Si la entrada de `[project.scripts]` apuntara a un
    módulo que no se empaqueta, o a una función inexistente, el `import`
    de la prueba anterior pasaría igual y esto caería.
    """
    binarios = Path(sys.executable).parent
    ejecutable = binarios / NOMBRE_COMANDO
    if not ejecutable.exists():
        ejecutable = binarios / f"{NOMBRE_COMANDO}.exe"
    assert ejecutable.exists(), (
        f"el entorno no tiene el comando {NOMBRE_COMANDO!r} en {binarios}: "
        "`[project.scripts]` no lo declara, o el entorno está sin sincronizar"
    )

    diario = tmp_path / "diario.jsonl"
    proceso = subprocess.run(
        [str(ejecutable), "--diario", str(diario), "--raiz", str(tmp_path), "hola"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert proceso.returncode == 0, proceso.stderr
    assert proceso.stdout.strip() != ""
    assert not diario.exists(), "conversar no puede escribir en el diario"


# --- 2. Conversar y consultar no crean trabajo (A5-P1) --------------------------


def test_conversar_no_crea_trabajo_ni_toca_el_diario(tmp_path: Path) -> None:
    diario = tmp_path / "diario.jsonl"
    codigo, salida = _ejecutar("--diario", str(diario), "--raiz", str(tmp_path), "hola")

    assert codigo == 0
    assert salida.strip() != ""
    assert not diario.exists()


def test_una_orden_se_declina_y_no_crea_trabajo(tmp_path: Path) -> None:
    """La propiedad que el encargo pone por delante: este comando NO crea trabajo.

    «implementa el despachador de programación» es exactamente el mensaje que
    `tests/engine/test_session.py` usa para comprobar que `SesionCLI` crea Y
    activa un WorkItem. Aquí no puede: la cáscara consulta la MISMA puerta
    determinista antes de entregar el turno, y si la puerta no dice
    `NO_CREAR`, el turno no llega a la sesión.
    """
    diario = tmp_path / "diario.jsonl"
    codigo, salida = _ejecutar(
        "--diario",
        str(diario),
        "--raiz",
        str(tmp_path),
        "implementa el despachador de programación",
    )

    assert codigo == 0
    assert not diario.exists(), "una orden no puede crear trabajo desde este comando"
    assert "no crea trabajo" in salida.casefold()
    assert DurableWorkEngineStore(diario).list_events() == ()


def test_una_orden_sensible_tampoco_crea_trabajo(tmp_path: Path) -> None:
    """El otro desenlace que sí escribe: `CREAR_Y_ESCALAR` crea el WorkItem y lo escala."""
    diario = tmp_path / "diario.jsonl"
    codigo, _salida = _ejecutar(
        "--diario", str(diario), "--raiz", str(tmp_path), "borra la base de producción"
    )

    assert codigo == 0
    assert DurableWorkEngineStore(diario).list_events() == ()


def test_una_conversacion_entera_intercalada_con_ordenes_deja_el_diario_intacto(
    tmp_path: Path,
) -> None:
    diario = tmp_path / "diario.jsonl"
    guion = "\n".join(
        (
            "hola",
            "implementa el despachador de programación",
            "quizá convendría revisar el enfoque",
            "borra la base de producción",
            "gracias",
        )
    )
    codigo, salida = _ejecutar(
        "--diario", str(diario), "--raiz", str(tmp_path), entrada=f"{guion}\n"
    )

    assert codigo == 0
    # Las dos órdenes -la normal y la sensible- y solo ellas.
    assert salida.count("Esto es una orden") == 2
    assert not diario.exists()


# --- 3. El cableado de contexto.recuperar está vivo ------------------------------


def test_consultar_el_pasado_cita_el_arbol_del_repositorio(tmp_path: Path) -> None:
    """Si `contexto.recuperar` no estuviera cableado, la sesión respondería que no hay fuentes."""
    (tmp_path / "notas.md").write_text(
        "una linea cualquiera con estado de la nave dentro\n", encoding="utf-8"
    )
    diario = tmp_path / "diario.jsonl"

    codigo, salida = _ejecutar(
        "--diario", str(diario), "--raiz", str(tmp_path), "estado de la nave"
    )

    assert codigo == 0
    assert "notas.md" in salida
    assert "no hay fuentes" not in salida.casefold()


def test_un_historial_de_git_ilegible_se_dice_y_no_se_disfraza_de_no_hay(
    tmp_path: Path,
) -> None:
    """ADR-036: «no pude leerlo» nunca se convierte en «no hay nada»."""
    (tmp_path / "notas.md").write_text("estado de la nave\n", encoding="utf-8")
    codigo, salida = _ejecutar(
        "--diario",
        str(tmp_path / "diario.jsonl"),
        "--raiz",
        str(tmp_path),
        "estado de la nave",
    )

    assert codigo == 0
    assert "no pude leer" in salida.casefold()
    assert "historial" in salida.casefold()


# --- 4. Consultar el trabajo que ya hay, sin escribir en él ----------------------


def test_trabajos_lista_lo_que_el_diario_ya_contiene_sin_escribir_en_el(
    tmp_path: Path,
) -> None:
    diario = tmp_path / "diario.jsonl"
    DurableWorkEngineStore(diario).create_work_item(
        work_id="WI-YA-EXISTIA",
        peticion_original="algo que alguien encargó antes",
        objetivo="objetivo de prueba",
        contexto_origen=(),
        entregable="un entregable",
        criterio_terminado="existe",
        limites={},
        prioridad=3,
        clase=WorkItemClass.PROGRAMACION,
        now=datetime(2026, 8, 21, 3, 0, tzinfo=UTC),
    )
    antes = diario.read_bytes()

    codigo, salida = _ejecutar(
        "--diario", str(diario), "--raiz", str(tmp_path), entrada="/trabajos\n"
    )

    assert codigo == 0
    assert "WI-YA-EXISTIA" in salida
    assert "objetivo de prueba" in salida
    assert diario.read_bytes() == antes, "consultar no puede escribir en el diario"


def test_trabajos_sobre_un_diario_que_todavia_no_existe_no_lo_crea(tmp_path: Path) -> None:
    diario = tmp_path / "sin_estrenar.jsonl"
    codigo, salida = _ejecutar(
        "--diario", str(diario), "--raiz", str(tmp_path), entrada="/trabajos\n"
    )

    assert codigo == 0
    assert "ningún trabajo" in salida
    assert not diario.exists()


# --- 5. Dónde vive el almacén se cambia sin tocar código -------------------------


def test_el_diario_por_defecto_se_cambia_por_entorno_o_por_argumento(tmp_path: Path) -> None:
    por_defecto = cli.resolver_diario(argumento=None, entorno={})
    del_entorno = cli.resolver_diario(
        argumento=None, entorno={cli.VARIABLE_DIARIO: str(tmp_path / "delentorno.jsonl")}
    )
    manda_el_argumento = cli.resolver_diario(
        argumento=str(tmp_path / "delargumento.jsonl"),
        entorno={cli.VARIABLE_DIARIO: str(tmp_path / "delentorno.jsonl")},
    )

    assert por_defecto.name == "diario.jsonl"
    assert por_defecto != del_entorno
    assert del_entorno == tmp_path / "delentorno.jsonl"
    assert manda_el_argumento == tmp_path / "delargumento.jsonl"


def test_la_raiz_del_repositorio_se_cambia_por_entorno_o_por_argumento(tmp_path: Path) -> None:
    del_entorno = cli.resolver_raiz(argumento=None, entorno={cli.VARIABLE_RAIZ: str(tmp_path)})
    manda_el_argumento = cli.resolver_raiz(
        argumento=str(tmp_path / "otra"), entorno={cli.VARIABLE_RAIZ: str(tmp_path)}
    )

    assert cli.resolver_raiz(argumento=None, entorno={}) == Path.cwd()
    assert del_entorno == tmp_path
    assert manda_el_argumento == tmp_path / "otra"


def test_la_variable_de_entorno_gobierna_al_comando_entero(tmp_path: Path) -> None:
    """No basta con que el resolutor la lea: el comando tiene que usar lo que devuelve."""
    diario = tmp_path / "porentorno.jsonl"
    DurableWorkEngineStore(diario).create_work_item(
        work_id="WI-POR-ENTORNO",
        peticion_original="x",
        objetivo="objetivo llegado por la variable de entorno",
        contexto_origen=(),
        entregable="un entregable",
        criterio_terminado="existe",
        limites={},
        prioridad=3,
        clase=WorkItemClass.PROGRAMACION,
        now=datetime(2026, 8, 21, 3, 0, tzinfo=UTC),
    )

    codigo, salida = _ejecutar(
        "--raiz",
        str(tmp_path),
        entrada="/trabajos\n",
        entorno={cli.VARIABLE_DIARIO: str(diario), cli.VARIABLE_RAIZ: str(tmp_path)},
    )

    assert codigo == 0
    assert "WI-POR-ENTORNO" in salida


# --- 6. La sesión interactiva ----------------------------------------------------


def test_la_sesion_lee_varias_lineas_y_termina_en_el_fin_de_la_entrada(
    tmp_path: Path,
) -> None:
    codigo, salida = _ejecutar(
        "--diario",
        str(tmp_path / "diario.jsonl"),
        "--raiz",
        str(tmp_path),
        entrada="hola\ngracias\n",
    )

    assert codigo == 0
    assert salida.count(">") >= 2, "cada turno se escribe con su propio indicador"


def test_salir_termina_la_sesion_sin_leer_el_resto(tmp_path: Path) -> None:
    codigo, salida = _ejecutar(
        "--diario",
        str(tmp_path / "diario.jsonl"),
        "--raiz",
        str(tmp_path),
        entrada="/salir\nesto ya no se lee\n",
    )

    assert codigo == 0
    assert "esto ya no se lee" not in salida
