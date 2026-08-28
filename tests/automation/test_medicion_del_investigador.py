"""Guardianes de la medición del investigador (S2), todos DETERMINISTAS.

Aquí no se mide a ningún investigador: no hay red, no hay claves y no se llama a
ningún modelo. Se fija por escrito lo que la medición **no puede dejar de
cumplir**, porque las seis propiedades de abajo comparten una familia de defecto:
ninguna falla a gritos. Todas fallan **en verde**, produciendo un número creíble
y equivocado, que es peor que una excepción.

Lo que se fija, y qué defecto silencioso impide cada una:

1. **La versión de la herramienta está fijada a 0.15.1 en los dos sitios.**
   Medido el 26-08-2026: `gpt-researcher` 0.16.0 **no llega ni a importarse**
   -usa `Any` sin importarlo en `actions/query_processing.py`-. Si el workflow y
   el medidor discreparan, se instalaría una versión y se exigiría otra: el
   trabajo moriría después de instalar, o peor, mediría sobre algo que nadie ha
   comprobado que funcione.
2. **Un error en una pregunta NUNCA cuenta como acierto.** Es el criterio de
   parada (c) de la nota de arranque hecho prueba: «si el arnés no distingue
   *respondió mal* de *no llegó a intentarlo*, se para». La trampa es concreta y
   está medida más abajo: `_corrige("", [])` devuelve **True**.
3. **El entorno de cada subproceso se construye desde cero.** Ésta es LA
   propiedad del trabajo entero. Medido sobre 0.15.1: tanto el proveedor de
   modelo (`llm_provider/generic/base.py`) como el de vectorización
   (`memory/embeddings.py`) leen `OPENAI_BASE_URL` cuando el proveedor es
   `openai`. Dos configuraciones en un mismo proceso se pisan esa variable:
   NVIDIA la secuestra y la rama de Google acabaría hablando con el servidor de
   NVIDIA, devolviendo un informe **perfecto y falso**.
4. **Medir UNA sola configuración sale marcado NO CONCLUYENTE.** Criterio de
   parada (b). Un 0 ahí significaría «la comparación existe», y no existiría.
5. **El `timeout-minutes` del workflow nuevo no ensancha la ventana de D1.** La
   tolerancia se DERIVA del mayor tope de trabajo del repositorio por dos, y el
   margen del contador de los siete días es de **dos minutos**. Subir este tope
   no rompe nada ruidosamente: deja la racha sin avanzar NUNCA, en verde.
6. **Ninguna clave viaja interpolada dentro de un `run:`.** Un
   `${{ secrets.X }}` dentro del guion lo sustituye GitHub antes de que bash lea
   nada, y acabaría en el registro a la primera traza.

**Lo que esta batería NO garantiza, dicho aquí para que no se le suponga:**

- No comprueba que la medición funcione. Eso solo se puede ver en Actions: la
  red de las máquinas donde se escribió está cerrada (medido: `curl` a
  duckduckgo, groq y nvidia devuelve 000). Verde aquí significa «el arnés no
  miente», no «el investigador acierta».
- No valida los nombres de modelo contra ningún catálogo real.
- En la propiedad 2 se fija la CONJUNCIÓN, no cada mitad por separado: como
  `asyncio.run` deja el informe vacío cuando revienta, no existe ningún caso en
  el que `error is not None` y el informe tenga texto, así que quitar solo una
  de las dos condiciones no se puede ver caer desde fuera. La guarda es
  redundante a propósito y se prueba entera.
- La propiedad 6 mira SOLO el workflow de la medición, no los demás: los otros
  workflows son de otras verticales y ensancharlos aquí sería rediseñar por
  iniciativa propia.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from sirius_engine.projection_verifier import ventana_tolerancia_etiqueta_maquina

RAIZ = Path(__file__).resolve().parents[2]
WORKFLOWS = RAIZ / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "medir-investigador.yml"
INVESTIGACION = RAIZ / "scripts" / "investigacion"
MEDIDOR = INVESTIGACION / "medir_investigador.py"
COMPARADOR = INVESTIGACION / "comparar_investigadores.py"

#: La versión medida como buena, escrita aquí a mano A PROPÓSITO. Es el tercer
#: sitio, y por eso vale: si las pruebas leyeran el número del mismo fichero que
#: vigilan, cambiarlo en los dos sitios a la vez pasaría en verde y la 0.16.0
#: -que ni importa- entraría sin que nada lo dijera.
VERSION_MEDIDA_COMO_BUENA = "0.15.1"

#: Un valor imposible de confundir con nada legítimo. Si aparece dentro de un
#: subproceso, es que alguien heredó el entorno de quien llama.
CENTINELA = "https://centinela.invalido/ESTO-NO-DEBE-LLEGAR/v1"

#: Medidor falso: no mide, RETRATA el entorno que de verdad recibió. Se ejecuta
#: de verdad, como proceso hijo, porque leer el código del comparador y concluir
#: que no contamina es exactamente la clase de afirmación sin comprobación que
#: `AGENTS.md` prohíbe. Solo usa la biblioteca estándar: el entorno que le llega
#: no tiene `PYTHONPATH` ni nada instalado por el proyecto.
GUION_FALSO = """
# Medidor falso para las pruebas: escribe el entorno que recibió y sale.
import json
import os
import sys

salida = sys.argv[sys.argv.index("--salida") + 1]
retrato = {
    "configuracion": sys.argv[1],
    "servidor": os.environ.get("OPENAI_BASE_URL", "(por defecto del proveedor)"),
    "version_herramienta": "0.15.1",
    "aciertos": 0,
    "total": 0,
    "porcentaje": 0.0,
    "segundos_totales": 0.0,
    "preguntas": [],
    "entorno_recibido": dict(os.environ),
}
texto = json.dumps(retrato, ensure_ascii=False)
with open(salida, "w", encoding="utf-8") as fichero:
    fichero.write(texto)
sys.stdout.write(texto + "\\n")
"""


def _modulo(ruta: Path, nombre: str) -> Any:
    """Carga un guion suelto como módulo. Mismo idioma que sus hermanas."""
    cacheado = sys.modules.get(nombre)
    if cacheado is not None:
        return cacheado
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _medidor() -> Any:
    return _modulo(MEDIDOR, "medir_investigador_bajo_prueba")


def _comparador() -> Any:
    return _modulo(COMPARADOR, "comparar_investigadores_bajo_prueba")


def _doc(ruta: Path) -> dict[str, Any]:
    return dict(yaml.safe_load(ruta.read_text(encoding="utf-8")))


def _trabajos(ruta: Path) -> dict[str, Any]:
    trabajos = _doc(ruta).get("jobs") or {}
    assert isinstance(trabajos, dict) and trabajos, f"{ruta.name} no declara trabajos"
    return dict(trabajos)


def _pasos(ruta: Path) -> list[dict[str, Any]]:
    """Todos los pasos de todos los trabajos, ya interpretados como YAML.

    Se leen del documento PARSEADO y no del texto crudo a propósito: los
    comentarios del fichero hablan de `${{ secrets.X }}` para explicar por qué no
    se hace, y un `grep` los confundiría con el defecto que describen. GitHub
    tampoco los ve: el analizador de YAML los tira antes.
    """
    pasos: list[dict[str, Any]] = []
    for trabajo in _trabajos(ruta).values():
        if not isinstance(trabajo, dict):
            continue
        for paso in trabajo.get("steps") or []:
            if isinstance(paso, dict):
                pasos.append(dict(paso))
    return pasos


def _guiones(ruta: Path) -> list[tuple[str, str]]:
    """(nombre del paso, texto de su `run:`) por cada paso que ejecuta algo."""
    return [
        (str(p.get("name", "(sin nombre)")), str(p["run"])) for p in _pasos(ruta) if p.get("run")
    ]


def _lineas_que_bash_ejecuta(guion: str) -> list[str]:
    """Las líneas de un `run:` quitando los comentarios de shell.

    Hace falta, y se descubrió midiendo: la primera versión de la prueba de la
    versión se puso roja por una línea `# ... gpt-researcher==0.15.1 ...` que
    explica una medición y no instala nada. Un guardián que confunda la
    documentación con el defecto que describe se acaba desactivando, y ese es un
    coste peor que el defecto.

    **Esto NO vale para los secretos, y por eso solo se usa aquí.** Un
    `${{ secrets.X }}` dentro de un comentario de shell SÍ lo sustituye GitHub:
    la expresión se resuelve al componer el texto del paso, mucho antes de que
    bash decida qué es un comentario. Ahí el `#` no protege nada.
    """
    return [linea for linea in guion.splitlines() if not linea.strip().startswith("#")]


# --- 0. Anti-vacuas: sin esto, todo lo de abajo pasaría en el vacío ---------


def test_las_piezas_que_se_vigilan_existen() -> None:
    """Si una ruta cambia de sitio, esta batería tiene que ponerse roja, no muda."""
    for pieza in (WORKFLOW, MEDIDOR, COMPARADOR, INVESTIGACION / "configuraciones.yml"):
        assert pieza.is_file(), (
            f"falta {pieza}: las pruebas de este fichero quedarían vigilando el aire, "
            "que es la forma más barata de tener una batería verde que no mide nada"
        )


# --- 1. La versión está fijada, y en los dos sitios dice lo mismo ----------


def test_la_version_exigida_esta_fijada_y_coincide_en_los_dos_sitios() -> None:
    """0.16.0 ni se importa: si los dos sitios discrepan, se mide sobre lo que sea.

    El medidor exige una versión y el workflow instala otra. Si no coinciden, el
    trabajo gasta doce minutos instalando para morir en la comprobación
    siguiente; y si alguien «arregla» eso relajando el medidor, se mediría sobre
    una versión que nadie ha comprobado que arranque.
    """
    exigida_por_el_medidor = str(_medidor().VERSION_EXIGIDA)
    entorno = _trabajos(WORKFLOW)["medir"].get("env") or {}
    exigida_por_el_workflow = str(entorno.get("VERSION_EXIGIDA", ""))

    assert exigida_por_el_medidor == VERSION_MEDIDA_COMO_BUENA, (
        f"medir_investigador.VERSION_EXIGIDA vale {exigida_por_el_medidor!r} y la única "
        f"versión medida como buena es {VERSION_MEDIDA_COMO_BUENA!r}. La 0.16.0 usa `Any` "
        "sin importarlo en `actions/query_processing.py` y ni llega a importarse (medido "
        "el 26-08-2026). Subirla no es cambiar un número: hay que volver a medir."
    )
    assert exigida_por_el_workflow == exigida_por_el_medidor, (
        f"el workflow instala gpt-researcher {exigida_por_el_workflow!r} y el medidor exige "
        f"{exigida_por_el_medidor!r}. Dos verdades sobre la misma versión: una acabará "
        "mintiendo. El número tiene que estar en los dos sitios y ser el mismo."
    )


def test_la_instalacion_no_escribe_la_version_a_mano() -> None:
    """El `env:` no puede ser decorativo: la instalación tiene que usarlo.

    Sin esta prueba, la de arriba pasaría en verde con un
    `gpt-researcher==0.16.0` escrito directamente en el `run:` y la variable
    `VERSION_EXIGIDA` mirando a otro lado.
    """
    versiones: list[str] = []
    for _, guion in _guiones(WORKFLOW):
        for linea in _lineas_que_bash_ejecuta(guion):
            versiones.extend(re.findall(r"gpt-researcher==(\S+)", linea))
    assert versiones, (
        "ningún `run:` del workflow instala `gpt-researcher==...`. O se dejó de instalar "
        "la herramienta, o se instala sin fijar versión: las dos cosas hacen que la "
        "medición sea sobre lo que hubiera ese día en PyPI"
    )
    for version in versiones:
        assert version.strip("\"'") == "$VERSION_EXIGIDA", (
            f"el workflow instala `gpt-researcher=={version}` escrito a mano en el `run:`, "
            "en vez de leer `$VERSION_EXIGIDA`. Ese es el segundo sitio donde vive el "
            "número, y el día que alguien cambie uno solo nadie se enterará."
        )


def test_el_medidor_se_para_ante_una_version_que_no_es_la_medida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anti-vacua de la constante: que el número exista no significa que se mire.

    Sin esto, `VERSION_EXIGIDA` podría ser un comentario con formato de código y
    las dos pruebas de arriba seguirían verdes mientras la medición corre sobre
    cualquier versión que hubiera instalada.
    """
    m = _medidor()
    monkeypatch.setattr(m, "_version_instalada", lambda: "0.16.0")
    with pytest.raises(SystemExit) as parada:
        m.medir("configuración-de-prueba")

    mensaje = str(parada.value)
    assert "0.16.0" in mensaje and VERSION_MEDIDA_COMO_BUENA in mensaje, (
        f"el medidor tiene que parar diciendo QUÉ versión encontró y cuál exigía; dijo: {mensaje!r}"
    )


# --- 2. Un error jamás cuenta como acierto (criterio de parada (c)) --------


def test_el_corrector_da_por_bueno_un_informe_vacio_sin_obligatorias() -> None:
    """La trampa, medida y escrita: `_corrige("", [])` devuelve **True**.

    No es un defecto de `_corrige` -sin cadenas que buscar, ninguna falta-, pero
    sí es la razón por la que `medir` no puede fiarse solo de él. Esta prueba
    existe para que la de abajo no parezca paranoia: si alguien quitara la guarda
    creyendo que sobra, aquí se lee por qué no sobra.
    """
    m = _medidor()
    assert m._corrige("", []) == (True, [], []), (
        "si esto cambia, la guarda de `medir` puede sobrar o puede faltar: en "
        "cualquier caso, hay que volver a decidirlo mirando este número"
    )
    # Y sabe decir que no, que es la otra mitad del mismo control.
    acierta, encontradas, ausentes = m._corrige("El informe no dice el dato", ["Canberra"])
    assert (acierta, encontradas, ausentes) == (False, [], ["Canberra"])
    # Y no distingue mayúsculas, que es lo que promete su docstring.
    assert m._corrige("la capital es canberra", ["Canberra"])[0] is True


def _medir_con(
    monkeypatch: pytest.MonkeyPatch,
    preguntas: list[dict[str, Any]],
    respuesta: Any,
    presupuesto: int = 1800,
) -> Any:
    """Corre `medir()` de verdad, sin red y sin claves.

    Se sustituyen las tres puertas al mundo -la versión instalada, el banco de
    preguntas y la llamada al investigador- y NO la lógica que se está midiendo:
    el recuento y la construcción del `ResultadoPregunta` son los del fichero.

    La versión que se declara instalada se lee de `VERSION_EXIGIDA`, no de la
    copia de este fichero, A PROPÓSITO: quien vigila ese número es la propiedad
    1, y si aquí se escribiera a mano, cambiarlo pondría rojas también estas tres
    pruebas. Se midió: con la copia local, una sola mutación de versión sacaba
    cinco fallos, y cuatro no tenían nada que ver con lo que dicen medir.
    """
    m = _medidor()
    monkeypatch.setattr(m, "_version_instalada", lambda: m.VERSION_EXIGIDA)
    monkeypatch.setattr(m, "_cargar_preguntas", lambda: preguntas)
    monkeypatch.setattr(m, "_investigar", respuesta)
    return m.medir("configuración-de-prueba", presupuesto=presupuesto)


#: Una pregunta SIN cadenas obligatorias. Es el peor caso a propósito: es el
#: único en el que el corrector, por sí solo, diría que sí a un informe vacío.
PREGUNTA_SIN_OBLIGATORIAS: list[dict[str, Any]] = [
    {"id": "PX", "tipo": "prueba", "texto": "¿?", "obligatorias": []}
]


def test_un_error_no_cuenta_como_acierto(monkeypatch: pytest.MonkeyPatch) -> None:
    """Criterio de parada (c), hecho prueba: no llegar a intentarlo no es acertar.

    Se elige el caso más hostil que existe: la pregunta no tiene cadenas
    obligatorias -así que `_corrige` dice que sí- y la investigación revienta.
    Sin la guarda, esto sería un 100 % con la red caída.
    """

    async def revienta(_pregunta: str) -> tuple[str, int]:
        raise RuntimeError("la red está cerrada")

    resultado = _medir_con(monkeypatch, PREGUNTA_SIN_OBLIGATORIAS, revienta)

    assert resultado.aciertos == 0, (
        f"con la investigación reventada salieron {resultado.aciertos} aciertos de "
        f"{resultado.total}. Un error NUNCA puede contar como acierto: sin informe no hay "
        "nada que corregir, y confundir «respondió mal» con «no llegó a intentarlo» es "
        "exactamente lo que prohíbe el criterio de parada (c) de la nota de arranque."
    )
    assert resultado.porcentaje == 0.0
    (unica,) = resultado.preguntas
    assert unica["acierta"] is False
    assert unica["error"] is not None and "RuntimeError" in unica["error"], (
        "el fallo tiene que quedar ESCRITO en el resultado con su tipo. Un `acierta: false` "
        "sin error diría que respondió mal, que es otra cosa y se lee distinto"
    )


def test_un_informe_vacio_no_cuenta_como_acierto(monkeypatch: pytest.MonkeyPatch) -> None:
    """Y sin excepción tampoco: un informe vacío no es un acierto, es nada.

    La herramienta puede devolver cadena vacía sin reventar -un modelo que
    responde vacío, un informe que no se llegó a escribir-. Ahí no hay error que
    enseñar y el corrector diría que sí; el recuento tiene que decir que no.
    """

    async def vacio(_pregunta: str) -> tuple[str, int]:
        return "", 0

    resultado = _medir_con(monkeypatch, PREGUNTA_SIN_OBLIGATORIAS, vacio)

    assert resultado.aciertos == 0, (
        "un informe vacío se contó como acierto. `_corrige('', [])` devuelve True, así que "
        "esto es un 100 % construido sobre cero texto: el verde que no falla, miente."
    )
    (unica,) = resultado.preguntas
    assert unica["acierta"] is False
    assert unica["error"] is None, (
        "no hubo excepción, así que no puede inventarse un error: «no acertó» y «falló» "
        "son estados distintos y el informe los presenta distinto"
    )


def test_un_informe_bueno_si_cuenta_como_acierto(monkeypatch: pytest.MonkeyPatch) -> None:
    """Anti-vacua: un recuento que siempre diga cero también pasaría las dos de arriba."""

    async def responde(_pregunta: str) -> tuple[str, int]:
        return "La capital de Australia es Canberra.", 3

    preguntas = [{"id": "P1", "tipo": "memoria", "texto": "¿?", "obligatorias": ["Canberra"]}]
    resultado = _medir_con(monkeypatch, preguntas, responde)

    assert resultado.aciertos == 1 and resultado.porcentaje == 100.0, (
        "un informe que contiene el dato TIENE que contar. Si no, el arnés suspende "
        "siempre y su número no distingue una configuración de otra"
    )
    (unica,) = resultado.preguntas
    assert unica["acierta"] is True and unica["fuentes"] == 3


# --- 3. El entorno del subproceso se construye desde cero -----------------


@pytest.fixture
def medidor_falso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Sustituye el medidor real por uno que retrata su entorno y sale."""
    guion = tmp_path / "medidor_falso.py"
    guion.write_text(GUION_FALSO, encoding="utf-8")
    monkeypatch.setattr(_comparador(), "MEDIDOR", guion)
    return guion


def _entorno_del_hijo(
    nombre: str,
    carpeta: Path,
) -> dict[str, str]:
    """Mide UNA configuración real con el medidor falso y devuelve su entorno."""
    c = _comparador()
    configuraciones = c.cargar_configuraciones(INVESTIGACION / "configuraciones.yml")
    (configuracion,) = [x for x in configuraciones if x.nombre == nombre]
    medicion = c.medir_configuracion(configuracion, carpeta, 60)
    assert medicion.estado == c.ESTADO_MEDIDA, (
        f"el subproceso de «{nombre}» no llegó a medir: {medicion.estado} — {medicion.detalle}"
    )
    assert medicion.resultado is not None
    return dict(medicion.resultado["entorno_recibido"])


def test_una_variable_contaminante_no_llega_al_subproceso_que_no_la_declara(
    medidor_falso: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LA propiedad del trabajo, comprobada EJECUTANDO, no leyendo el código.

    Se ensucia `os.environ` con una `OPENAI_BASE_URL` centinela -exactamente lo
    que pasaría si el propietario tuviera una exportada en su máquina, o si un
    paso anterior del workflow la pusiera- y se comprueba que el subproceso de
    Google, que NO la declara, no la ve.

    Que el guion parta de `{}` se lee en tres líneas; que el subproceso REAL no
    la reciba solo se sabe mirando el proceso hijo. Esa diferencia es el sentido
    entero de esta prueba: el día que alguien meta un `dict(os.environ)` para
    «arreglar» un fallo de entorno, la rama de Google hablaría con el servidor de
    NVIDIA y el informe saldría perfecto.
    """
    monkeypatch.setenv("OPENAI_BASE_URL", CENTINELA)
    monkeypatch.setenv("CLAVE_LIMPIA", "clave-falsa-de-prueba-limpia")
    monkeypatch.setenv("NVIDIA_API_KEY", "clave-falsa-de-prueba-nvidia")

    # Configuración DE LABORATORIO que no declara OPENAI_BASE_URL, como hacía la
    # de Google hasta que ADR-098 la retiró del fichero real: la propiedad que
    # se prueba es del arnés, no de un proveedor, y quitar a Google del banco no
    # podía llevarse la prueba (criterio de parada (b) de la nota de arranque
    # del descarte).
    c = _comparador()
    limpia = c.Configuracion(
        nombre="limpia",
        proveedor="laboratorio",
        modelo="m",
        variable_de_clave="CLAVE_LIMPIA",
        clave_destino="CLAVE_LIMPIA",
        entorno={"FAST_LLM": "lab:m", "SMART_LLM": "lab:m"},
    )
    medicion = c.medir_configuracion(limpia, tmp_path, 60)
    assert medicion.estado == c.ESTADO_MEDIDA, medicion.detalle
    assert medicion.resultado is not None
    entorno = dict(medicion.resultado["entorno_recibido"])

    assert "PATH" in entorno, (
        "el subproceso no recibió ni PATH: un entorno vacío pasaría el resto de esta "
        "prueba sin demostrar nada, y además dejaría al intérprete sin poder arrancar"
    )
    assert "OPENAI_BASE_URL" not in entorno, (
        f"la configuración limpia recibió OPENAI_BASE_URL={entorno.get('OPENAI_BASE_URL')!r} "
        "sin declararla: está viendo la variable de quien lanzó el proceso. "
        "`gpt-researcher` 0.15.1 la lee para el modelo (`llm_provider/generic/base.py`) y "
        "para vectorizar (`memory/embeddings.py`), así que una configuración de vía nativa "
        "mediría contra el servidor de otra y devolvería un informe impecable y FALSO."
    )
    coladas = sorted(v for v, valor in entorno.items() if CENTINELA in valor)
    assert coladas == [], (
        f"el valor centinela llegó al subproceso en {coladas}: alguien está heredando el "
        "entorno de quien llama en vez de construirlo desde cero"
    )
    assert "NVIDIA_API_KEY" not in entorno, (
        "la clave de NVIDIA no pinta nada en el subproceso de otra configuración: cada una "
        "recibe la suya, con el nombre que espera la herramienta, y ninguna más"
    )


def test_la_configuracion_que_si_declara_la_variable_recibe_la_suya(
    medidor_falso: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anti-vacua de la anterior: borrarlo todo también dejaría el centinela fuera.

    Un `entorno = {}` que no añadiera nunca nada pasaría la prueba de arriba con
    sobresaliente y no mediría nada en absoluto. Aquí se exige lo contrario: que
    NVIDIA reciba **su** URL, la declarada en `configuraciones.yml`, y su clave
    con el nombre de destino -`OPENAI_API_KEY`, que es su vía compatible-.
    """
    monkeypatch.setenv("OPENAI_BASE_URL", CENTINELA)
    monkeypatch.setenv("GOOGLE_API_KEY", "clave-falsa-de-prueba-google")
    monkeypatch.setenv("NVIDIA_API_KEY", "clave-falsa-de-prueba-nvidia")

    entorno = _entorno_del_hijo("nvidia", tmp_path)

    assert entorno.get("OPENAI_BASE_URL") == "https://integrate.api.nvidia.com/v1", (
        f"NVIDIA recibió OPENAI_BASE_URL={entorno.get('OPENAI_BASE_URL')!r} en vez de la que "
        "declara `configuraciones.yml`. Si es el centinela, hereda del entorno de fuera; si "
        "no está, la configuración no llegó a aplicarse y la medición no es de NVIDIA."
    )
    # La clave llega TAPADA, y eso es la prueba de que llegó. El comparador pasa
    # el JSON del hijo por `sin_secretos` antes de tocarlo -porque ese JSON se
    # sube como artefacto-, así que el valor real nunca sale por aquí. El
    # marcador solo aparece donde estaba la clave exacta: verlo demuestra las dos
    # cosas a la vez, que llegó y que no se publica.
    valor = entorno.get("OPENAI_API_KEY")
    assert valor is not None, (
        "la clave tiene que llegar con su nombre de DESTINO: NVIDIA entra por la vía "
        "compatible con OpenAI y la herramienta la busca como OPENAI_API_KEY"
    )
    assert valor != "", "OPENAI_API_KEY llegó vacía: la configuración no se aplicó"
    assert "clave-falsa-de-prueba-nvidia" not in valor, (
        "la clave viajó SIN TAPAR en el JSON del hijo, que es lo que se sube como artefacto"
    )
    assert "GOOGLE_API_KEY" not in entorno, (
        "la clave de Google se coló en el subproceso de NVIDIA: ninguna configuración puede "
        "ver las credenciales de la otra"
    )


# --- 4. Con una sola configuración medida, NO CONCLUYENTE -----------------


def _configuraciones_de_prueba(ruta: Path, mismo_servidor: bool = False) -> Path:
    """Dos configuraciones inventadas, con la misma forma que las de verdad.

    No se tocan las reales: una prueba que dependa de que sigan siendo dos se
    pondría roja el día que se añada una tercera, y eso sería ruido, no defecto.
    """
    segundo_servidor = (
        "https://servidor-uno.invalido/v1" if mismo_servidor else "https://servidor-dos.invalido/v1"
    )
    ruta.write_text(
        "version: 1\n"
        "configuraciones:\n"
        "  - nombre: uno\n"
        "    proveedor: proveedor-falso-uno\n"
        "    modelo: modelo-falso-uno\n"
        "    variable_de_clave: CLAVE_FALSA_UNO\n"
        "    clave_destino: OPENAI_API_KEY\n"
        "    entorno:\n"
        '      FAST_LLM: "openai:modelo-falso-uno"\n'
        '      SMART_LLM: "openai:modelo-falso-uno"\n'
        '      OPENAI_BASE_URL: "https://servidor-uno.invalido/v1"\n'
        "  - nombre: dos\n"
        "    proveedor: proveedor-falso-dos\n"
        "    modelo: modelo-falso-dos\n"
        "    variable_de_clave: CLAVE_FALSA_DOS\n"
        "    clave_destino: OPENAI_API_KEY\n"
        "    entorno:\n"
        '      FAST_LLM: "openai:modelo-falso-dos"\n'
        '      SMART_LLM: "openai:modelo-falso-dos"\n'
        f'      OPENAI_BASE_URL: "{segundo_servidor}"\n',
        encoding="utf-8",
    )
    return ruta


def _atestado_de_prueba(configuraciones: Path) -> str:
    """Un atestado que declara usables los modelos falsos de esta batería.

    Se DERIVA del propio fichero de configuraciones en vez de escribirse a mano:
    si alguien cambia un modelo de prueba y el atestado se quedara atrás, estas
    pruebas empezarían a fallar por su montaje y no por el código, que es la forma
    más fácil de acabar relajando el guardián que vigilan.
    """
    from datetime import UTC, datetime

    texto = configuraciones.read_text(encoding="utf-8")
    nombres = sorted(
        set(
            re.findall(r'(?:FAST_LLM|SMART_LLM|STRATEGIC_LLM|EMBEDDING):\s*"[^:"]+:([^"]+)"', texto)
        )
    )
    ahora = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lineas = ["version: 1", "proveedores:", "  prueba:", "    modelos:"]
    for nombre in nombres:
        lineas += [
            f'      "{nombre}":',
            "        existe: true",
            "        usable: true",
            f"        fecha_utc: {ahora}",
        ]
    return "\n".join(lineas) + "\n"


def _comparar(
    tmp_path: Path,
    configuraciones: Path,
) -> tuple[int, dict[str, Any], str]:
    """Ejecuta el comparador entero y devuelve (código, JSON crudo, Markdown).

    ATESTADO PROPIO, y no es fontanería de prueba: desde ADR-095 el comparador se
    NIEGA a medir un modelo del que no conste que responde. Estas pruebas usan
    modelos de mentira, así que se les monta su atestado de mentira —lo mismo que
    el `gh` simulado de otras baterías—. La comprobación NO se puede saltar: si el
    fichero no existiera, todos los modelos contarían como sin atestiguar y el
    comparador saldría con código 5, que es justo lo que debe pasar.
    """
    md = tmp_path / "informe.md"
    crudo = tmp_path / "comparacion.json"
    atestado = tmp_path / "atestado.yml"
    if not atestado.exists():
        atestado.write_text(_atestado_de_prueba(configuraciones), encoding="utf-8")
    codigo = _comparador().main(
        [
            "--configuraciones",
            str(configuraciones),
            "--atestado",
            str(atestado),
            "--salida-md",
            str(md),
            "--salida-json",
            str(crudo),
            "--tiempo-maximo",
            "60",
            # Fecha fija: un informe que cambia solo porque ha pasado un día no
            # se puede comparar con el anterior.
            "--fecha",
            "2026-08-26",
        ]
    )
    return codigo, json.loads(crudo.read_text(encoding="utf-8")), md.read_text(encoding="utf-8")


def test_medir_una_sola_configuracion_sale_no_concluyente(
    medidor_falso: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Criterio de parada (b): «si acaba midiendo UNA sola configuración, no vale».

    Se le da la clave de una sola de las dos, que es el caso real: el propietario
    guarda un secreto y se le olvida el otro. La que hay se mide -eso está bien y
    vale como medida suelta-, pero el VEREDICTO no puede ser un cero: un cero
    significaría «la comparación existe», y no existe.
    """
    monkeypatch.delenv("CLAVE_FALSA_DOS", raising=False)
    monkeypatch.setenv("CLAVE_FALSA_UNO", "clave-falsa-de-prueba-uno")
    configuraciones = _configuraciones_de_prueba(tmp_path / "configuraciones.yml")

    codigo, crudo, informe = _comparar(tmp_path, configuraciones)
    c = _comparador()

    assert codigo == c.CODIGO_NO_CONCLUYENTE, (
        f"el comparador midió una sola configuración y salió con código {codigo}. Tiene que "
        f"salir con {c.CODIGO_NO_CONCLUYENTE}: en este repositorio las validaciones se leen "
        "por CÓDIGO DE SALIDA, así que un 0 aquí publicaría como comparación algo que no "
        "compara nada (criterio de parada (b))."
    )
    assert crudo["configuraciones_medidas"] == 1
    assert crudo["concluyente"] is False
    assert crudo["veredicto"] == "NO CONCLUYENTE"
    assert "NO CONCLUYENTE" in informe, (
        "el Markdown es lo que lee una persona: el veredicto tiene que estar escrito ahí "
        "arriba, no solo en el código de salida"
    )


def test_dos_configuraciones_medidas_contra_servidores_distintos_si_concluyen(
    medidor_falso: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Anti-vacua: un comparador que devolviera 2 siempre pasaría la prueba de arriba."""
    monkeypatch.setenv("CLAVE_FALSA_UNO", "clave-falsa-de-prueba-uno")
    monkeypatch.setenv("CLAVE_FALSA_DOS", "clave-falsa-de-prueba-dos")
    configuraciones = _configuraciones_de_prueba(tmp_path / "configuraciones.yml")

    codigo, crudo, informe = _comparar(tmp_path, configuraciones)

    assert codigo == _comparador().CODIGO_OK, (
        f"dos configuraciones medidas contra servidores distintos y el veredicto salió "
        f"{codigo}. Si esto no puede salir 0, el arnés suspende siempre y su código no "
        "distingue una comparación buena de una que no existe."
    )
    assert crudo["concluyente"] is True and crudo["veredicto"] == "CONCLUYENTE"
    assert crudo["configuraciones_medidas"] == 2
    assert "CONCLUYENTE" in informe


def test_dos_mediciones_del_mismo_servidor_no_son_una_comparacion(
    medidor_falso: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El tercer peldaño, que es el peligroso: dos números que PARECEN comparables.

    Quedarse corto de mediciones se nota. Que las dos hayan hablado con el mismo
    servidor no se nota en absoluto: salen dos porcentajes, uno por etiqueta, y
    son la misma medida contada dos veces.
    """
    monkeypatch.setenv("CLAVE_FALSA_UNO", "clave-falsa-de-prueba-uno")
    monkeypatch.setenv("CLAVE_FALSA_DOS", "clave-falsa-de-prueba-dos")
    configuraciones = _configuraciones_de_prueba(
        tmp_path / "configuraciones.yml", mismo_servidor=True
    )

    codigo, crudo, _informe = _comparar(tmp_path, configuraciones)

    assert codigo == _comparador().CODIGO_COMPARACION_FALSA, (
        f"las dos mediciones declararon el MISMO servidor y el veredicto salió {codigo}. "
        "Eso no es una comparación: es una medición con dos etiquetas, y publicarla como "
        "comparación es el verde que miente."
    )
    assert crudo["servidores_distintos"] is False
    assert crudo["veredicto"] == "COMPARACIÓN FALSA"


# --- 5. El tope de tiempo no ensancha la ventana de D1 --------------------


def _tolerancia_en_minutos(directorio: Path) -> int:
    return int(ventana_tolerancia_etiqueta_maquina(directorio).total_seconds() // 60)


def test_el_tope_del_workflow_no_supera_el_mayor_del_resto() -> None:
    """El margen del contador de los siete días es de DOS minutos. Literalmente dos.

    `ventana_tolerancia_etiqueta_maquina` deriva la tolerancia del MAYOR
    `timeout-minutes` de trabajo del repositorio, por dos: hoy 85 x 2 = 170. La
    tranquilidad previa a la pasada del contador son 172. Un workflow nuevo con
    un tope de 87 dejaría a D1 sin ninguna hora posible, y no lo diría ningún
    rojo: `sirius-racha` devuelve 0 tanto si CUMPLE como si no, así que la racha
    simplemente no avanzaría nunca.
    """
    del_workflow = [
        trabajo["timeout-minutes"]
        for trabajo in _trabajos(WORKFLOW).values()
        if isinstance(trabajo, dict) and isinstance(trabajo.get("timeout-minutes"), int)
    ]
    assert del_workflow, (
        "el trabajo de la medición no declara `timeout-minutes`. Sin tope, GitHub le da "
        "seis horas: una medición colgada gastaría la cuota de las dos APIs del propietario"
    )

    del_resto: list[int] = []
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        if wf == WORKFLOW:
            continue
        for trabajo in (_doc(wf).get("jobs") or {}).values():
            if isinstance(trabajo, dict) and isinstance(trabajo.get("timeout-minutes"), int):
                del_resto.append(int(trabajo["timeout-minutes"]))
    assert del_resto, "no se encontró ningún otro tope: la comparación no mediría nada"

    assert max(del_workflow) <= max(del_resto), (
        f"el workflow de la medición declara un tope de {max(del_workflow)} min, por encima "
        f"del mayor del resto del repositorio ({max(del_resto)} min). La tolerancia de D1 se "
        "deriva de ese máximo por dos, y el contador solo tiene 172 minutos tranquilos por "
        "delante: el margen es de DOS. Subirlo no rompe nada ruidosamente, deja la racha sin "
        "avanzar NUNCA y en verde. Baja el tope o parte el trabajo en dos."
    )


def test_este_workflow_no_mueve_la_ventana_que_juzga_al_contador(tmp_path: Path) -> None:
    """La misma propiedad, derivada con la función real en vez de con un `max` copiado.

    Comparar máximos a mano es reimplementar el criterio: si mañana la derivación
    cambia -por ejemplo, para mirar también los topes de paso-, la prueba de
    arriba seguiría verde midiendo otra cosa. Aquí se llama a la función que de
    verdad decide, con y sin este fichero, y se exige que dé lo mismo.
    """
    sin_este = tmp_path / "workflows"
    sin_este.mkdir()
    for wf in WORKFLOWS.glob("*.yml"):
        if wf != WORKFLOW:
            shutil.copy(wf, sin_este / wf.name)

    con, sin = _tolerancia_en_minutos(WORKFLOWS), _tolerancia_en_minutos(sin_este)
    assert con == sin, (
        f"con el workflow de la medición la tolerancia de D1 vale {con} min y sin él {sin}. "
        "Este fichero está ensanchando la ventana con la que se juzga la hora del contador "
        "de los siete días, y esa hora está calculada con dos minutos de margen."
    )


# --- 6. Las claves entran por `env:`, nunca interpoladas en un `run:` -----


_SECRETO_INTERPOLADO = re.compile(r"\$\{\{\s*secrets\.", re.IGNORECASE)


def test_ninguna_clave_viaja_interpolada_dentro_de_un_run() -> None:
    """Un `${{ secrets.X }}` dentro de un `run:` acaba en el registro, y punto.

    GitHub sustituye la expresión ANTES de que bash lea el guion: el valor queda
    incrustado en el texto del paso, y basta una traza, un `set -x` o un error de
    sintaxis para que salga impreso. El enmascarado de Actions ayuda, pero no es
    una garantía: no cubre transformaciones de la clave ni la salida de un
    subproceso que la reformatee.

    Por `env:` no pasa eso: la clave viaja como variable de entorno del paso y el
    texto del guion nunca la contiene.
    """
    culpables = [
        f"{nombre}: {linea.strip()}"
        for nombre, guion in _guiones(WORKFLOW)
        for linea in guion.splitlines()
        if _SECRETO_INTERPOLADO.search(linea)
    ]
    assert culpables == [], (
        "estos `run:` del workflow de la medición interpolan un secreto:\n  "
        + "\n  ".join(culpables)
        + "\n\nGitHub lo sustituye antes de que bash vea nada y el valor acaba dentro del "
        "texto del guion. Pásalo por el `env:` del paso y léelo como variable."
    )


def test_el_paso_que_compara_recibe_las_claves_declaradas() -> None:
    """Anti-vacua afinada, y la afinó una mutación que la versión anterior NO cazó.

    La primera redacción de esta guarda solo miraba si las claves aparecían
    en ALGÚN `env:` del fichero. Se probó a quitárselas al paso que ejecuta el
    comparador -dejándolas en el paso que solo comprueba que existen- y la
    batería siguió verde: el trabajo habría comprobado las claves, instalado la
    herramienta, y llegado a la comparación sin ninguna, para salir con todo
    marcado `sin_clave`.

    Por eso se exige sobre el paso concreto que las necesita, localizado por lo
    que ejecuta y no por su nombre. Y desde ADR-098 la lista de claves se DERIVA
    de `configuraciones.yml` -las principales; las opcionales tienen su propia
    guarda-, no se escribe aquí: era el número en dos sitios otra vez.
    """
    c = _comparador()
    configuraciones = c.cargar_configuraciones(INVESTIGACION / "configuraciones.yml")
    principales = sorted({conf.variable_de_clave for conf in configuraciones})
    assert principales, "sin claves declaradas esta prueba no mediría nada"

    pasos = [p for p in _pasos(WORKFLOW) if "comparar_investigadores.py" in str(p.get("run", ""))]
    assert len(pasos) == 1, (
        f"se esperaba exactamente un paso que ejecute el comparador, hay {len(pasos)}. "
        "Si se partió en dos, esta guarda ya no sabe cuál tiene que llevar las claves"
    )
    entorno = {str(k): str(v) for k, v in (pasos[0].get("env") or {}).items()}
    faltan = [
        variable
        for variable in principales
        if not _SECRETO_INTERPOLADO.search(entorno.get(variable, ""))
    ]
    assert faltan == [], (
        f"el paso que ejecuta el comparador no recibe {faltan} desde los secretos. Sin la "
        "clave, `medir_configuracion` marca esa configuración `sin_clave` y NO la mide: el "
        "trabajo gastaría la instalación entera para acabar en NO CONCLUYENTE. Y no sale "
        "rojo por sorpresa: sale rojo después de gastar los minutos."
    )


def test_las_claves_entran_por_env_y_solo_las_declaradas() -> None:
    """Anti-vacua: un workflow sin claves pasaría la prueba de arriba sin mérito.

    HASTA EL 27-08-2026 esta prueba fijaba a mano el par NVIDIA/GOOGLE, y añadir
    la clave opcional del buscador (ADR-098) la puso roja: el número estaba
    escrito en dos sitios y uno mentiría tarde o temprano. Ahora el conjunto
    esperado se DERIVA de `configuraciones.yml` -claves principales más
    opcionales-, que es la única fuente. La mitad que de verdad protege queda
    igual y explícita: el criterio de parada (a) -«si hiciera falta clave de
    OpenAI o Anthropic, se para»- se comprueba sobre el ORIGEN; que la de NVIDIA
    se llame `OPENAI_API_KEY` DENTRO del subproceso la hace el guion con
    `clave_destino` y está permitida.
    """
    c = _comparador()
    configuraciones = c.cargar_configuraciones(INVESTIGACION / "configuraciones.yml")
    esperadas = {conf.variable_de_clave for conf in configuraciones} | {
        origen for conf in configuraciones for origen, _destino in conf.claves_opcionales
    }
    assert esperadas, "sin claves declaradas esta prueba no mediría nada"

    entradas: dict[str, str] = {}
    for paso in _pasos(WORKFLOW):
        for variable, valor in (paso.get("env") or {}).items():
            if _SECRETO_INTERPOLADO.search(str(valor)):
                entradas[str(variable)] = str(valor)

    assert set(entradas) == esperadas, (
        f"el workflow declara estas claves por `env:`: {sorted(entradas)}, y "
        f"`configuraciones.yml` declara {sorted(esperadas)}. Los dos tienen que decir lo "
        "mismo: una clave en el workflow que ninguna configuración nombra no la usa nadie, "
        "y una nombrada que el workflow no pasa deja la pieza muerta."
    )
    prohibidas = sorted(set(entradas) & set(c.CLAVES_QUE_OBLIGAN_A_PARAR))
    assert prohibidas == [], (
        f"el workflow pide {prohibidas}: criterio de parada (a), se para y se sube al propietario."
    )


def test_el_env_del_trabajo_no_configura_al_investigador() -> None:
    """Lo que se declara arriba lo ven TODOS los pasos: ahí no cabe una configuración.

    Una `OPENAI_BASE_URL` en el `env:` del trabajo sería la contaminación de la
    propiedad 3, pero entrando por la puerta grande y sin que ningún subproceso
    pudiera evitarla: el guion construye su entorno desde cero, sí, pero la
    heredaría igual quien lanzara al guion.
    """
    c = _comparador()
    entorno = _trabajos(WORKFLOW)["medir"].get("env") or {}
    coladas = sorted(set(entorno) & set(c.VARIABLES_QUE_CONTAMINAN))
    assert coladas == [], (
        f"el `env:` del trabajo declara {coladas}, que configuran al investigador. Ese "
        "bloque lo ven todos los pasos: una sola de esas variables ahí y las dos "
        "configuraciones medirían contra el mismo sitio, con dos etiquetas distintas."
    )


# --------------------------------------------------------------------------- #
# La raíz que la refutación del 26-08-2026 destapó
# --------------------------------------------------------------------------- #
#
# 27 hallazgos, 8 graves, y SEIS DE LOS OCHO eran el mismo defecto: el arnés
# medía lo que se le PEDÍA y nunca lo que OCURRÍA. El caso que lo demuestra:
# `gpt-researcher` importa `ddgs` y declara `duckduckgo-search`. Sin el primero
# el buscador no arranca, el modelo escribe de memoria, y como las preguntas del
# banco se las sabe, el informe SALE PERFECTO con cero fuentes.
#
# Medido antes de corregir: 5/5, 100 %, código 0, «concluyente».
# Medido después:           0/5,   0 %, código 3, «no fiable».


def _medidor_con_doble(
    monkeypatch: pytest.MonkeyPatch, respuestas: dict[str, tuple[str, int]]
) -> Any:
    """El medidor REAL con la investigación sustituida por un doble.

    Se apoya en el cargador que ya tiene este fichero (`_medidor`), en vez de
    traerse otro: dos cargadores del mismo módulo son dos formas de que las
    pruebas midan cosas distintas sin que se note.
    """
    modulo = _medidor()

    async def _doble(pregunta: str) -> tuple[str, int]:
        for clave, valor in respuestas.items():
            if clave.lower() in pregunta.lower():
                return valor
        return ("", 0)

    monkeypatch.setattr(modulo, "_investigar", _doble)
    monkeypatch.setattr(modulo, "_version_instalada", lambda: modulo.VERSION_EXIGIDA)
    return modulo


def test_un_informe_correcto_SIN_FUENTES_no_es_un_acierto(monkeypatch: pytest.MonkeyPatch) -> None:
    """La propiedad que mata a toda la familia, y la que costó una refutación.

    El informe CONTIENE la respuesta correcta. Y no cuenta, porque nadie buscó:
    el modelo se la sabía. Sin esta regla, un buscador muerto daba 100 %.
    """
    modulo = _medidor_con_doble(monkeypatch, {"": ("La capital de Australia es Canberra.", 0)})
    resultado = modulo.medir("sin-fuentes")
    assert resultado.aciertos == 0, (
        f"un informe sin ni una fuente contó como acierto: {resultado.aciertos} de "
        f"{resultado.total}. Eso es el modelo recitando, no el investigador"
    )
    assert resultado.medicion_fiable is False
    assert "buscador no funciono" in (resultado.motivo_no_fiable or "")


def test_el_mismo_informe_CON_FUENTES_si_es_un_acierto(monkeypatch: pytest.MonkeyPatch) -> None:
    """Anti-vacua: sin esto, «acierta=False» siempre pasaría la prueba de arriba."""
    # UN TEXTO DERIVADO DEL BANCO, no escrito a mano.
    #
    # Esta prueba ya se rompió DOS veces por su propio montaje: la primera porque
    # el doble devolvía solo la respuesta de P1, y la segunda cuando el banco
    # creció de cinco preguntas a siete y el texto fijo se quedó atrás. Las dos
    # veces la culpa fue de la prueba, no del código.
    #
    # Una anti-vacua que falla por su montaje es la forma más fácil de acabar
    # relajando la regla que vigila, así que deja de haber texto que mantener: se
    # arma con todas las obligatorias del banco real.
    import yaml as _yaml

    banco = _yaml.safe_load(
        (RAIZ / "scripts" / "investigacion" / "preguntas.yml").read_text(encoding="utf-8")
    )
    completo = ", ".join(
        sorted({o for q in banco["preguntas"] for o in (q.get("obligatorias") or [])})
    )
    modulo = _medidor_con_doble(monkeypatch, {"": (completo, 4)})
    resultado = modulo.medir("con-fuentes")
    assert resultado.aciertos == resultado.total
    assert resultado.medicion_fiable is True
    assert resultado.motivo_no_fiable is None


def test_una_medicion_no_fiable_sale_con_codigo_3(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """El código de salida deja de mentir.

    Antes devolvía 0 pasara lo que pasara, y el comparador decidía «medida
    válida» solo con verlo: cinco preguntas reventadas y comparación concluyente.
    """
    modulo = _medidor_con_doble(monkeypatch, {"": ("Canberra, 1969, Apache, Rust, Pyre.", 0)})
    codigo = modulo.main(["x", "--salida", str(tmp_path / "r.json")])
    assert codigo == 3, f"una medición sin fuentes salió con código {codigo}"


def test_una_medicion_fiable_sale_con_codigo_0(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Anti-vacua del anterior: `return 3` a secas también lo pasaría."""
    modulo = _medidor_con_doble(monkeypatch, {"": ("Canberra 1969 Apache Rust Pyre", 7)})
    assert modulo.main(["x", "--salida", str(tmp_path / "r.json")]) == 0


def test_el_json_conserva_el_rastro_aunque_la_medicion_no_valga(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Un fallo que no deja rastro es peor que el fallo.

    El JSON tiene que salir igual, con el motivo y los informes dentro, para que
    quien lo lea después sepa QUÉ pasó y no solo que algo pasó.
    """
    salida = tmp_path / "r.json"
    modulo = _medidor_con_doble(monkeypatch, {"": ("La capital de Australia es Canberra.", 0)})
    modulo.main(["x", "--salida", str(salida)])
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert datos["medicion_fiable"] is False
    assert datos["fuentes_totales"] == 0
    assert "ddgs" in datos["motivo_no_fiable"], "el motivo tiene que nombrar la causa real"
    assert datos["preguntas"], "los informes se conservan para poder releerlos"


@pytest.mark.parametrize(
    ("texto", "obligatoria", "esperado"),
    [
        ("uv is a tool you can trust", "Rust", False),
        ("distrust and frustrating", "Rust", False),
        ("uv está escrito en Rust", "Rust", True),
        ("the Apache Foundation is unrelated", "Apache", True),
        ("Rust.", "Rust", True),
    ],
)
def test_la_correccion_exige_palabra_entera(texto: str, obligatoria: str, esperado: bool) -> None:
    """«trust» contenía «rust», y aprobaba la pregunta. Medido por el refutador."""
    acierta, _, _ = _medidor()._corrige(texto, [obligatoria])
    assert acierta is esperado, f"_corrige({texto!r}, [{obligatoria!r}]) dio {acierta}"


# --------------------------------------------------------------------------- #
# Los tres hallazgos de la refutación que NO eran de la familia de la raíz
# --------------------------------------------------------------------------- #


def test_el_workflow_instala_el_paquete_que_el_buscador_importa() -> None:
    """`ddgs`, la causa material del defecto.

    `gpt-researcher` 0.15.1 hace `check_pkg('ddgs')` y `from ddgs import DDGS`,
    pero declara `Requires-Dist: duckduckgo-search>=4.1.1`. Son paquetes
    distintos. Sin instalarlo a mano el buscador NO arranca, el modelo escribe de
    memoria y el informe sale perfecto con cero fuentes.
    """
    # SE MIRA LA ORDEN DE INSTALACION, NO EL FICHERO. La primera version de esta
    # prueba buscaba «ddgs» en todo el texto y la cabecera del propio workflow lo
    # nombra dos veces al explicar el defecto: quitarlo de la linea de instalacion
    # la dejaba en verde. Vacua, y por el mismo motivo que ya paso con H-14: un
    # guardian que se conforma con que algo este NOMBRADO no comprueba que este
    # HECHO.
    doc = _doc(WORKFLOW)
    instalaciones = [
        str(paso.get("run", ""))
        for job in (doc.get("jobs") or {}).values()
        for paso in (job.get("steps") or [])
        if "uv pip install" in str(paso.get("run", ""))
    ]
    assert instalaciones, "el workflow no instala nada: no hay orden que comprobar"
    sin_comentarios = "\n".join(
        linea
        for orden in instalaciones
        for linea in orden.splitlines()
        if not linea.lstrip().startswith("#")
    )
    assert re.search(r"(?<!\w)ddgs(?!\w)", sin_comentarios), (
        "ninguna orden `uv pip install` del workflow instala `ddgs`: el buscador "
        "no arrancaría y las dos configuraciones contestarían de memoria, con cero "
        "fuentes y un informe perfecto"
    )


def test_todos_los_pasos_declaran_su_shell() -> None:
    """El `-e` por defecto mata el paso antes de que se lea el código de salida.

    El shell por defecto de un `run:` en GitHub es `bash -e {0}`, y
    `set -uo pipefail` NO apaga errexit. Sin `shell:` explícito, cualquier
    veredicto distinto de 0 mataba el paso antes de `codigo=$?`, y el trabajo
    publicaba «probablemente agotó el tope» en vez del motivo real.
    """
    doc = _doc(WORKFLOW)
    sin_shell = [
        paso.get("name", "(sin nombre)")
        for job in (doc.get("jobs") or {}).values()
        for paso in (job.get("steps") or [])
        if "run" in paso and "shell" not in paso
    ]
    assert sin_shell == [], (
        f"pasos con `run:` y sin `shell:` explícito: {sin_shell}. Heredan `bash -e`, "
        "que los mata antes de leer el código de salida"
    )


def test_el_json_del_hijo_se_tapa_antes_de_publicarse() -> None:
    """La clave podía viajar intacta al artefacto.

    `medir_investigador.py` guarda el texto de la excepción en el JSON, y el de
    un cliente HTTP puede traer dentro la cabecera de autenticación. Ese JSON se
    sube como artefacto. Antes solo se tapaba la cola de un subproceso fallido:
    el único canal por el que una clave podía salir era el que no se tapaba.
    """
    modulo = _comparador()
    fuente = Path(modulo.__file__).read_text(encoding="utf-8")
    lectura = fuente.index("salida_json.read_text")
    ventana = fuente[max(0, lectura - 200) : lectura + 100]
    assert "sin_secretos" in ventana, (
        "el JSON del hijo se lee sin pasar por `sin_secretos`, y es lo que se sube como artefacto"
    )


# RETIRADO EL 27-08-2026: `test_una_medicion_que_el_hijo_declara_no_fiable_no_se_
# cuenta_como_medida`. Leía el TEXTO del comparador y comprobaba que
# `ESTADO_FALLO` apareciera dentro de los 400 caracteres siguientes a
# `medicion_fiable`.
#
# Estuvo en verde todo el tiempo que esa rama fue INALCANZABLE. No podía ser de
# otra manera: un guardián que lee el código fuente ve que la rama está escrita,
# nunca que se ejecute. Es la lección de la noche entera en una sola prueba.
#
# Lo que comprueba lo mismo ejecutándolo:
# `test_un_tres_no_se_convierte_en_una_medida`, que lanza un hijo de verdad —el
# que sale con 3 y escribe su JSON con `porcentaje: 100.0` dentro— y exige que
# quede en `fallo` y sin porcentaje copiado. Y se ve caer con la mutación.


# --------------------------------------------------------------------------- #
# El lazo entre atestiguar y medir
# --------------------------------------------------------------------------- #


def _sin_comentarios(guion: str) -> str:
    """El guion sin comentarios: un guardián que ve un nombre en un comentario
    no comprueba nada. Cuarto caso de la noche del 27-08 (ADR-095)."""
    return "\n".join(x for x in guion.splitlines() if not x.lstrip().startswith("#"))


def test_el_banco_atestigua_en_su_propia_pasada() -> None:
    """Sin esto, el guardián de ADR-095 existe y no sirve para nada.

    El atestado que el comparador exige lo escribía el preflight **en su propio
    runner**, y allí moría. El fichero versionado del repositorio se queda con lo
    que hubiera la última vez, o vacío: con eso el banco se negaría a medir
    siempre —correcto pero inútil— o, peor, mediría con un atestado viejo.

    Generarlo en la misma pasada es más fuerte que confirmarlo en el repositorio:
    no puede estar caducado ni pertenecer a otra cuenta. **Lo que se mide y lo que
    se atestigua son la misma corrida.**
    """
    doc = _doc(WORKFLOW)
    pasos = [paso for job in (doc.get("jobs") or {}).values() for paso in (job.get("steps") or [])]
    nombres = [str(p.get("name", "")) for p in pasos]
    guiones = [_sin_comentarios(str(p.get("run", ""))) for p in pasos]

    indice_atestado = next(
        (i for i, g in enumerate(guiones) if "--atestiguar" in g),
        None,
    )
    assert indice_atestado is not None, (
        "el banco no genera su propio atestado: el guardián de ADR-095 se negaría "
        f"a medir siempre, o mediría con uno viejo. Pasos: {nombres}"
    )

    indice_medicion = next(
        (i for i, g in enumerate(guiones) if "comparar_investigadores.py" in g),
        None,
    )
    assert indice_medicion is not None, "el banco no llama al comparador"
    assert indice_atestado < indice_medicion, (
        "se atestigua DESPUÉS de medir: para entonces la cuota ya está gastada"
    )


# --- Que el banco diga por qué no midió -------------------------------------
#
# La primera pasada real del banco (ejecución 33079519839, 27-08-2026) no midió
# ninguna de las dos configuraciones y NO PUDO DECIR POR QUÉ:
#
#   nvidia:  fallo — el subproceso terminó con código 3. Final de su salida:
#            «new images from 0 total images INFO: 🌐 Scraping complete…»
#   google:  agotado_el_tiempo — el subproceso pasó de 1500 s y se cortó.
#
# Dos defectos distintos, uno por línea.


GUION_QUE_SE_DECLARA_NO_FIABLE = """
# Hijo que mide, se da cuenta de que lo suyo no vale, ESCRIBE su JSON con el
# motivo dentro y sale con 3. Es el camino real de `medir_investigador.main`.
import json
import sys

salida = sys.argv[sys.argv.index("--salida") + 1]
retrato = {
    "configuracion": sys.argv[1],
    "servidor": "https://ejemplo.invalido/v1",
    "version_herramienta": "0.15.1",
    "aciertos": 5,
    "total": 5,
    "porcentaje": 100.0,
    "segundos_totales": 1.0,
    "medicion_fiable": False,
    "motivo_no_fiable": "ninguna pregunta trajo ni una sola fuente: el buscador no funciono",
    "preguntas": [],
}
with open(salida, "w", encoding="utf-8") as fichero:
    fichero.write(json.dumps(retrato, ensure_ascii=False))
sys.stderr.write("INFO: 🌐 Scraping complete\\n")
sys.stderr.write("INFO: 📚 Getting relevant content based on query\\n")
sys.exit(3)
"""

GUION_QUE_MUERE_SIN_JSON = """
import sys
sys.stderr.write("me mori antes de escribir nada\\n")
sys.exit(3)
"""

GUION_QUE_REVIENTA = """
import sys
sys.stderr.write("excepcion cualquiera\\n")
sys.exit(1)
"""


def _medicion_con_guion(guion_texto: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    c = _comparador()
    guion = tmp_path / "hijo.py"
    guion.write_text(guion_texto, encoding="utf-8")
    monkeypatch.setattr(c, "MEDIDOR", guion)
    monkeypatch.setenv("CLAVE_DE_PRUEBA", "no-es-una-clave")
    configuracion = c.Configuracion(
        nombre="prueba",
        proveedor="proveedor",
        modelo="modelo",
        variable_de_clave="CLAVE_DE_PRUEBA",
        clave_destino="CLAVE_DE_PRUEBA",
        entorno={},
    )
    return c.medir_configuracion(configuracion, tmp_path, 60)


def test_un_tres_con_json_publica_el_motivo_y_no_la_cola_del_buscador(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pregunta 1: el camino real, no una constante.

    `medir_investigador.main` devuelve 3 EXACTAMENTE cuando la medición no es
    fiable, y escribe su JSON antes. La guarda genérica del padre atrapaba ese 3
    y volvía, así que la rama que lee `motivo_no_fiable` —con su comentario
    diciendo «el hijo ya sabe que lo suyo no vale y lo dice»— era inalcanzable.
    """
    medicion = _medicion_con_guion(GUION_QUE_SE_DECLARA_NO_FIABLE, tmp_path, monkeypatch)
    assert "el buscador no funciono" in medicion.detalle, (
        f"el detalle no trae el motivo que el hijo escribió: {medicion.detalle!r}. "
        "Se está publicando otra cosa —la cola de la salida— y el motivo se tira."
    )
    assert "Scraping complete" not in medicion.detalle, (
        "el detalle sigue siendo la cola de los registros del buscador"
    )
    assert medicion.resultado is not None, "el JSON del hijo no llegó al informe"


def test_un_tres_no_se_convierte_en_una_medida(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Criterio de parada (a): distinguir el 3 no puede volverse creerse el 3.

    El JSON del hijo trae `porcentaje: 100.0`. Si esto pasara a `medida`, un
    100 % construido sobre cero fuentes acabaría publicado como resultado.
    """
    medicion = _medicion_con_guion(GUION_QUE_SE_DECLARA_NO_FIABLE, tmp_path, monkeypatch)
    c = _comparador()
    assert medicion.estado == c.ESTADO_FALLO, (
        f"una medición que el propio hijo declara no fiable quedó como {medicion.estado!r}"
    )
    assert medicion.porcentaje in (None, 0.0), (
        f"se copió el porcentaje de una medición no fiable: {medicion.porcentaje}"
    )


def test_un_tres_sin_json_sigue_siendo_fallo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pregunta 2, primera mitad: sin JSON no hay motivo que leer."""
    medicion = _medicion_con_guion(GUION_QUE_MUERE_SIN_JSON, tmp_path, monkeypatch)
    c = _comparador()
    assert medicion.estado == c.ESTADO_FALLO
    assert "me mori antes de escribir nada" in medicion.detalle, (
        f"un 3 sin JSON tiene que enseñar la cola de su salida: {medicion.detalle!r}"
    )


def test_otro_codigo_sigue_siendo_fallo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pregunta 2, segunda mitad: solo el 3 es un veredicto; el resto, averías."""
    medicion = _medicion_con_guion(GUION_QUE_REVIENTA, tmp_path, monkeypatch)
    c = _comparador()
    assert medicion.estado == c.ESTADO_FALLO
    assert "código 1" in medicion.detalle, medicion.detalle


# --- El plazo, por pregunta y no por configuración --------------------------


def test_el_plazo_por_pregunta_sale_del_presupuesto_y_cabe_dentro() -> None:
    """Pregunta 4: un plazo interior mayor que el exterior no protege nada."""
    m = _medidor()
    cuantas = len(m._cargar_preguntas())
    assert cuantas >= 7, f"el banco encogió a {cuantas}: esta prueba mide el reparto real"
    presupuesto = 1500
    plazo = m.segundos_por_pregunta(presupuesto, cuantas)
    assert plazo * cuantas <= presupuesto, (
        f"{cuantas} preguntas a {plazo} s son {plazo * cuantas} s, más que los "
        f"{presupuesto} s del presupuesto: lo cortaría el padre y no habría informe."
    )
    assert plazo >= m.SEGUNDOS_MINIMOS_POR_PREGUNTA, (
        "el reparto se saltó el suelo: con plazos de segundos se mide el reloj, no al investigador"
    )
    # Y el suelo manda cuando el presupuesto es ridículo.
    assert m.segundos_por_pregunta(1, cuantas) == m.SEGUNDOS_MINIMOS_POR_PREGUNTA


TRES_PREGUNTAS: list[dict[str, Any]] = [
    {"id": "P1", "tipo": "prueba", "texto": "rápida 1", "obligatorias": ["sí"]},
    {"id": "P2", "tipo": "prueba", "texto": "colgada", "obligatorias": ["sí"]},
    {"id": "P3", "tipo": "prueba", "texto": "rápida 2", "obligatorias": ["sí"]},
]


def _con_una_colgada(monkeypatch: pytest.MonkeyPatch, cuantas_cuelgan: int) -> Any:
    m = _medidor()
    monkeypatch.setattr(m, "segundos_por_pregunta", lambda *_a, **_k: 1)

    async def responde(pregunta: str) -> tuple[str, int]:
        if "colgada" in pregunta or cuantas_cuelgan == 3:
            await asyncio.sleep(3)
        return "sí, con fuentes", 4

    return _medir_con(monkeypatch, TRES_PREGUNTAS, responde)


def test_una_pregunta_colgada_no_se_lleva_por_delante_las_demas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pregunta 3: seis respuestas ya escritas no se tiran por una séptima colgada."""
    resultado = _con_una_colgada(monkeypatch, cuantas_cuelgan=1)
    assert resultado.aciertos == 2, (
        f"se perdieron respuestas buenas: {resultado.aciertos} aciertos de 3 preguntas "
        "con una sola colgada"
    )
    assert resultado.preguntas_cortadas_por_plazo == 1
    cortada = next(p for p in resultado.preguntas if p["cortada_por_plazo"])
    assert cortada["id"] == "P2"
    assert "no llegó a terminar" in (cortada["error"] or ""), cortada["error"]
    assert resultado.medicion_fiable, (
        f"una medición con 2 de 3 respondidas se declaró no fiable: {resultado.motivo_no_fiable}"
    )


def test_si_se_cortan_todas_la_medicion_no_es_fiable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Criterio de parada (b): medir el reloj no es medir al investigador."""
    resultado = _con_una_colgada(monkeypatch, cuantas_cuelgan=3)
    assert not resultado.medicion_fiable
    assert "se cortaron por plazo" in (resultado.motivo_no_fiable or ""), resultado.motivo_no_fiable


GUION_QUE_RETRATA_SUS_ARGUMENTOS = """
# Hijo que solo apunta con qué lo llamaron. Sirve para comprobar el CABLE, no la
# pieza: que el medidor sepa repartir un presupuesto no demuestra que el padre se
# lo dé, y sin esa mitad el hijo reparte un valor por defecto que no tiene nada
# que ver con el plazo real -y vuelve a morir con las respuestas dentro-.
import json
import sys

salida = sys.argv[sys.argv.index("--salida") + 1]
with open(salida, "w", encoding="utf-8") as fichero:
    fichero.write(json.dumps({"argv": sys.argv, "medicion_fiable": True, "preguntas": []}))
"""


def test_el_padre_le_dice_al_hijo_de_cuanto_tiempo_dispone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El cable, no la pieza. Sin esta prueba, quitar `--presupuesto` deja todo verde."""
    medicion = _medicion_con_guion(GUION_QUE_RETRATA_SUS_ARGUMENTOS, tmp_path, monkeypatch)
    assert medicion.resultado is not None, medicion.detalle
    argv = list(medicion.resultado["argv"])
    assert "--presupuesto" in argv, (
        f"el padre no le dice al hijo de cuánto dispone: {argv}. El hijo repartirá "
        "un valor por defecto ajeno al plazo real y morirá con las respuestas dentro."
    )
    # 60 es el `tiempo_maximo` con el que `_medicion_con_guion` llama al padre: se
    # comprueba que viaja EL MISMO número, no que exista la bandera.
    assert argv[argv.index("--presupuesto") + 1] == "60", (
        f"viaja un presupuesto que no es el plazo real del padre: {argv}"
    )


def test_el_desglose_por_pregunta_sale_por_el_registro_y_trae_el_error() -> None:
    """Lo que impidió no volver a adivinar: el artefacto no se puede leer.

    El JSON con el detalle de cada pregunta se sube como artefacto, y desde una
    sesión no se descarga. El 27-08-2026 eso costó una pasada de treinta minutos
    con las dos APIs gastadas: la única pista legible fue «el subproceso terminó
    con código 3».
    """
    c = _comparador()
    medicion = c.Medicion(
        nombre="prueba",
        proveedor="p",
        modelo="m",
        estado=c.ESTADO_FALLO,
        detalle="no fiable",
        variable_de_clave="X",
        variables_puestas=[],
    )
    medicion.resultado = {
        "preguntas": [
            {
                "id": "P1",
                "acierta": False,
                "fuentes": 0,
                "segundos": 3.2,
                "cortada_por_plazo": False,
                "error": "RuntimeError: el modelo devolvio 404 al escribir el informe",
            },
            {
                "id": "P2",
                "acierta": True,
                "fuentes": 4,
                "segundos": 41.0,
                "cortada_por_plazo": False,
                "error": None,
            },
        ]
    }
    lineas = c.desglose_por_pregunta(medicion)
    assert len(lineas) == 2, lineas
    assert "404 al escribir el informe" in lineas[0], (
        f"el error de la pregunta no llega al registro: {lineas[0]!r}. Sin eso, "
        "la única forma de saber qué pasó es descargar el artefacto a mano."
    )
    assert "fuentes=0" in lineas[0] and "fuentes=4" in lineas[1]
    assert "[NO]" in lineas[0] and "[ok]" in lineas[1]


def test_el_comparador_escribe_ese_desglose_de_verdad(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """El cable otra vez: que la función exista no la ejecuta nadie.

    Es la misma comprobación que faltó con `--presupuesto`, donde quitar el cable
    dejó las cuarenta pruebas en verde.
    """
    c = _comparador()
    guion = tmp_path / "hijo.py"
    guion.write_text(
        "\nimport json, sys\n"
        'salida = sys.argv[sys.argv.index("--salida") + 1]\n'
        'open(salida, "w", encoding="utf-8").write(json.dumps({\n'
        '  "medicion_fiable": False,\n'
        '  "motivo_no_fiable": "motivo de prueba",\n'
        '  "preguntas": [{"id": "PZ", "acierta": False, "fuentes": 0, "segundos": 1.0,\n'
        '                 "cortada_por_plazo": False, "error": "SEÑAL-QUE-SE-BUSCA"}]}))\n'
        "sys.exit(3)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(c, "MEDIDOR", guion)
    monkeypatch.setenv("CLAVE_DE_PRUEBA", "no-es-una-clave")
    monkeypatch.setattr(
        c,
        "cargar_configuraciones",
        lambda _ruta: [
            c.Configuracion(
                nombre="prueba",
                proveedor="p",
                modelo="m",
                variable_de_clave="CLAVE_DE_PRUEBA",
                clave_destino="CLAVE_DE_PRUEBA",
                entorno={},
            )
        ],
    )
    monkeypatch.setattr(c, "modelos_sin_atestado", lambda *_a, **_k: [])
    c.main(
        [
            "--salida-md",
            str(tmp_path / "i.md"),
            "--salida-json",
            str(tmp_path / "i.json"),
            "--tiempo-maximo",
            "60",
            "--fecha",
            "2026-08-27",
        ]
    )
    registro = capsys.readouterr().err
    assert "SEÑAL-QUE-SE-BUSCA" in registro, (
        "el desglose por pregunta no se escribió en el registro del trabajo; "
        f"lo que salió fue:\n{registro[-800:]}"
    )


# --- Claves opcionales: el buscador con clave, sin que su ausencia rompa nada ---
#
# ADR-098. DuckDuckGo desde los runners devolvió vacío en 5 de 7 búsquedas y el
# 80 % de S2 no se podía ni medir. Tavily aporta fuentes si su clave está; el
# esquema solo admitía UNA clave y el guardián anti-secretos rechaza -con razón-
# cualquier `*_API_KEY` escrito en `entorno`. De ahí `claves_opcionales`.


def _configuracion_con_opcional(c: Any) -> Any:
    return c.Configuracion(
        nombre="prueba",
        proveedor="p",
        modelo="m",
        variable_de_clave="CLAVE_DE_PRUEBA",
        clave_destino="CLAVE_DE_PRUEBA",
        entorno={},
        claves_opcionales=(("TAVILY_API_KEY", "TAVILY_API_KEY"),),
    )


def test_la_clave_opcional_presente_llega_al_hijo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pregunta 1, primera mitad: presente se entrega, con su nombre de destino."""
    c = _comparador()
    guion = tmp_path / "hijo.py"
    guion.write_text(GUION_FALSO, encoding="utf-8")
    monkeypatch.setattr(c, "MEDIDOR", guion)
    monkeypatch.setenv("CLAVE_DE_PRUEBA", "clave-principal")
    monkeypatch.setenv("TAVILY_API_KEY", "clave-del-buscador-de-prueba")
    medicion = c.medir_configuracion(_configuracion_con_opcional(c), tmp_path, 60)
    assert medicion.resultado is not None, medicion.detalle
    entorno = dict(medicion.resultado["entorno_recibido"])
    # El hijo la recibió (la variable existe en su retrato) y el retrato vuelve
    # TAPADO: `sin_secretos` sustituyó el valor antes de que tocara el disco.
    # Las dos cosas a la vez, con una sola llamada real.
    assert entorno.get("TAVILY_API_KEY") == c.OCULTO, (
        f"TAVILY_API_KEY en el retrato del hijo: {entorno.get('TAVILY_API_KEY')!r}. "
        "O no llegó al subproceso (Tavily quedaría inerte también con el secreto "
        "puesto), o llegó y NO se tapó (la clave saldría en el artefacto)."
    )


def test_la_clave_opcional_ausente_no_rompe_ni_avisa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pregunta 1, segunda mitad: opcional significa opcional."""
    c = _comparador()
    guion = tmp_path / "hijo.py"
    guion.write_text(GUION_FALSO, encoding="utf-8")
    monkeypatch.setattr(c, "MEDIDOR", guion)
    monkeypatch.setenv("CLAVE_DE_PRUEBA", "clave-principal")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    medicion = c.medir_configuracion(_configuracion_con_opcional(c), tmp_path, 60)
    assert medicion.estado == c.ESTADO_MEDIDA, (
        f"sin la clave opcional la medición no puede degradarse: {medicion.estado} — "
        f"{medicion.detalle}"
    )
    assert medicion.resultado is not None
    assert "TAVILY_API_KEY" not in dict(medicion.resultado["entorno_recibido"]), (
        "sin valor no se entrega la variable: una cadena vacía en el entorno del "
        "hijo no es lo mismo que su ausencia."
    )


def test_el_valor_de_la_clave_opcional_se_tapa_en_la_salida(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pregunta 3: que sea opcional no la hace publicable.

    El guion falso retrata el entorno entero en su JSON, que es exactamente el
    texto que acaba en el artefacto: si la clave opcional no se tapara, saldría
    versionada ahí.
    """
    c = _comparador()
    guion = tmp_path / "hijo.py"
    guion.write_text(GUION_FALSO, encoding="utf-8")
    monkeypatch.setattr(c, "MEDIDOR", guion)
    monkeypatch.setenv("CLAVE_DE_PRUEBA", "clave-principal-larga")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-secreto-que-no-puede-salir")
    medicion = c.medir_configuracion(_configuracion_con_opcional(c), tmp_path, 60)
    assert medicion.resultado is not None
    crudo = str(medicion.resultado)
    assert "tvly-secreto-que-no-puede-salir" not in crudo, (
        "el valor de la clave opcional aparece en el JSON que se sube como artefacto"
    )


def test_una_clave_opcional_de_openai_o_anthropic_para_el_guion(tmp_path: Path) -> None:
    """Criterio de parada (a), también para las opcionales: el origen manda."""
    c = _comparador()
    fichero = tmp_path / "configuraciones.yml"
    fichero.write_text(
        """
version: 1
configuraciones:
  - nombre: tramposa
    proveedor: p
    modelo: m
    variable_de_clave: CLAVE_X
    clave_destino: CLAVE_X
    entorno:
      FAST_LLM: "p:m"
      SMART_LLM: "p:m"
    claves_opcionales:
      - variable_de_clave: OPENAI_API_KEY
""",
        encoding="utf-8",
    )
    with pytest.raises(c.ConfiguracionInvalida):
        c.cargar_configuraciones(fichero)


def test_las_dos_configuraciones_declaran_el_mismo_buscador() -> None:
    """Pregunta 4: si difieren, la comparación tiene dos variables y no dice nada."""
    c = _comparador()
    configuraciones = c.cargar_configuraciones(INVESTIGACION / "configuraciones.yml")
    buscadores = {conf.entorno.get("RETRIEVER") for conf in configuraciones}
    assert len(buscadores) == 1, (
        f"las configuraciones declaran buscadores distintos: {buscadores}. La "
        "comparación presume de tener UNA variable -el modelo- y esto le mete otra."
    )
    (buscador,) = buscadores
    assert buscador == "tavily,duckduckgo", (
        f"el buscador declarado es {buscador!r}. Desde ADR-098 van los dos y en ese "
        "orden: Tavily aporta fuentes si su clave está, y sin clave queda inerte."
    )


# --- Contar las DOS fuentes: el registro que Tavily no alimenta ---------------
#
# La cadena entera (28-08-2026): la clave llegaba (pasada 4), Tavily contestaba
# USABLE con resultados (atestado), y `fuentes` seguia a cero. La 0.15.1 manda
# los resultados que ya traen contenido a `research_sources` y esos nunca pasan
# por `visited_urls`, que era lo unico que se contaba. Tercer rojo-que-miente de
# la misma familia: el instrumento lee el registro equivocado.


class _InvestigadorFingido:
    def __init__(self, visitadas: list[str], origenes: list[object]) -> None:
        self._visitadas = visitadas
        self._origenes = origenes

    def get_source_urls(self) -> list[str]:
        return list(self._visitadas)

    def get_research_sources(self) -> list[object]:
        return list(self._origenes)


def test_las_fuentes_pretraidas_cuentan_aunque_no_se_visitaran() -> None:
    """La prueba que la pasada 4 exigia: Tavily lleno, visited_urls vacio."""
    m = _medidor()
    fingido = _InvestigadorFingido(
        visitadas=[],
        origenes=[{"url": "https://a.example"}, {"url": "https://b.example"}],
    )
    assert m._contar_fuentes(fingido) == 2, (
        "las fuentes pre-traidas por el buscador no cuentan: con Tavily POR FIN "
        "funcionando, el medidor seguiria diciendo fuentes=0 y suspendiendo "
        "preguntas investigadas con fuentes reales."
    )


def test_una_url_en_los_dos_registros_cuenta_una_vez() -> None:
    """Inflar fuentes seria el verde que miente, peor que el rojo."""
    m = _medidor()
    fingido = _InvestigadorFingido(
        visitadas=["https://a.example"],
        origenes=[{"url": "https://a.example"}, {"url": "https://b.example"}],
    )
    assert m._contar_fuentes(fingido) == 2


def test_origenes_sin_url_no_cuentan_ni_revientan() -> None:
    m = _medidor()
    fingido = _InvestigadorFingido(
        visitadas=[],
        origenes=[{"title": "sin url"}, "no soy un dict", {"url": ""}, None],
    )
    assert m._contar_fuentes(fingido) == 0


def test_con_todo_vacio_sigue_siendo_cero_y_la_regla_intacta() -> None:
    """Criterio de parada (a): la correccion no puede desarmar `fuentes > 0`."""
    m = _medidor()
    assert m._contar_fuentes(_InvestigadorFingido([], [])) == 0


# --- El descarte de ADR-098, implementado y vigilado --------------------------


def test_el_atestado_cubre_a_los_proveedores_declarados() -> None:
    """El paso del atestado nombra a CADA proveedor de `configuraciones.yml`.

    El atestado dejó de correr «para todos» cuando ADR-098 retiró a Google:
    atestarlo sin su clave fallaría siempre, y con ella gastaría cuota de un
    proveedor descartado. El precio de nombrar al proveedor en el workflow es
    que el fichero de configuraciones y el workflow pueden divergir; esta prueba
    es ese precio pagado una vez.
    """
    c = _comparador()
    configuraciones = c.cargar_configuraciones(INVESTIGACION / "configuraciones.yml")
    declarados = sorted({conf.proveedor for conf in configuraciones})
    pasos = [p for p in _pasos(WORKFLOW) if "preflight.py" in str(p.get("run", ""))]
    assert len(pasos) == 1, "se esperaba exactamente un paso de atestado en el banco"
    orden = str(pasos[0]["run"])
    ausentes = [p for p in declarados if p not in orden]
    assert ausentes == [], (
        f"el paso del atestado no nombra a {ausentes}: sus modelos entrarían a la "
        "medición sin que nadie haya comprobado hoy que responden."
    )


def _main_con_configuraciones(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    nombres_y_codigos: list[tuple[str, int]],
) -> tuple[int, dict[str, Any]]:
    """Ejecuta `main` real con un hijo fingido por configuración declarada."""
    import json as _json

    c = _comparador()
    guion = tmp_path / "hijo.py"
    guion.write_text(
        "\nimport json, sys\n"
        'salida = sys.argv[sys.argv.index("--salida") + 1]\n'
        "codigo = int(sys.argv[1].rsplit('-', 1)[-1])\n"
        'open(salida, "w", encoding="utf-8").write(json.dumps({\n'
        '  "medicion_fiable": codigo == 0, "motivo_no_fiable": None if codigo == 0 else "x",\n'
        '  "servidor": "https://servidor-" + sys.argv[1], "aciertos": 5, "total": 7,\n'
        '  "porcentaje": 71.4, "segundos_totales": 10.0, "preguntas": []}))\n'
        "sys.exit(codigo)\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(c, "MEDIDOR", guion)
    monkeypatch.setenv("CLAVE_DE_PRUEBA", "no-es-una-clave")
    monkeypatch.setattr(
        c,
        "cargar_configuraciones",
        lambda _ruta: [
            c.Configuracion(
                nombre=f"{nombre}-{codigo}",
                proveedor="p",
                modelo="m",
                variable_de_clave="CLAVE_DE_PRUEBA",
                clave_destino="CLAVE_DE_PRUEBA",
                entorno={},
            )
            for nombre, codigo in nombres_y_codigos
        ],
    )
    monkeypatch.setattr(c, "modelos_sin_atestado", lambda *_a, **_k: [])
    salida_json = tmp_path / "i.json"
    codigo = c.main(
        [
            "--salida-md",
            str(tmp_path / "i.md"),
            "--salida-json",
            str(salida_json),
            "--tiempo-maximo",
            "60",
            "--fecha",
            "2026-08-28",
        ]
    )
    return codigo, dict(_json.loads(salida_json.read_text(encoding="utf-8")))


def test_una_sola_declarada_y_medida_es_medida_unica(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pregunta 1: desde ADR-098 la pasada es una medición, no una comparación."""
    codigo, crudo = _main_con_configuraciones(tmp_path, monkeypatch, [("unica", 0)])
    assert codigo == 0, (
        f"una única configuración declarada y MEDIDA salió con código {codigo}: el banco "
        "de la configuración elegida no podría dar nunca su número en verde."
    )
    assert crudo["veredicto"] == "MEDIDA ÚNICA", crudo["veredicto"]
    assert "NO compara" in str(crudo["motivo"]), (
        "el motivo no deja claro que esto no es una comparación: alguien leería el "
        "número como si hubiera ganado a otro."
    )


def test_una_sola_declarada_pero_no_medida_sigue_sin_valer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pregunta 2: una pasada vacía no sale verde por ser pequeña."""
    codigo, crudo = _main_con_configuraciones(tmp_path, monkeypatch, [("unica", 3)])
    assert codigo == c_codigo_no_concluyente(), f"código {codigo}, crudo: {crudo['veredicto']}"
    assert crudo["veredicto"] == "NO CONCLUYENTE"


def c_codigo_no_concluyente() -> int:
    return int(_comparador().CODIGO_NO_CONCLUYENTE)


def test_con_dos_declaradas_el_veredicto_viejo_queda_intacto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pregunta 3: medir una de dos sigue siendo NO CONCLUYENTE."""
    codigo, crudo = _main_con_configuraciones(tmp_path, monkeypatch, [("a", 0), ("b", 3)])
    assert codigo == c_codigo_no_concluyente()
    assert crudo["veredicto"] == "NO CONCLUYENTE"
