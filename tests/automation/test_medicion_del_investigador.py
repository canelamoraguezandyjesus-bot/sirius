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
    return m.medir("configuración-de-prueba")


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
    monkeypatch.setenv("GOOGLE_API_KEY", "clave-falsa-de-prueba-google")
    monkeypatch.setenv("NVIDIA_API_KEY", "clave-falsa-de-prueba-nvidia")

    entorno = _entorno_del_hijo("google", tmp_path)

    assert "PATH" in entorno, (
        "el subproceso no recibió ni PATH: un entorno vacío pasaría el resto de esta "
        "prueba sin demostrar nada, y además dejaría al intérprete sin poder arrancar"
    )
    assert "OPENAI_BASE_URL" not in entorno, (
        f"la configuración de Google recibió OPENAI_BASE_URL={entorno.get('OPENAI_BASE_URL')!r}. "
        "Google entra por su vía nativa y no declara esa variable: si la ve, está viendo la "
        "de otra configuración o la de quien lanzó el proceso. `gpt-researcher` 0.15.1 la lee "
        "para el modelo (`llm_provider/generic/base.py`) y para vectorizar "
        "(`memory/embeddings.py`), así que Google mediría contra el servidor de NVIDIA y "
        "devolvería un informe impecable y FALSO."
    )
    coladas = sorted(v for v, valor in entorno.items() if CENTINELA in valor)
    assert coladas == [], (
        f"el valor centinela llegó al subproceso en {coladas}: alguien está heredando el "
        "entorno de quien llama en vez de construirlo desde cero"
    )
    assert "NVIDIA_API_KEY" not in entorno, (
        "la clave de NVIDIA no pinta nada en el subproceso de Google: cada configuración "
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


def test_el_paso_que_compara_recibe_las_dos_claves() -> None:
    """Anti-vacua afinada, y la afinó una mutación que la versión anterior NO cazó.

    La primera redacción de esta guarda solo miraba si las dos claves aparecían
    en ALGÚN `env:` del fichero. Se probó a quitárselas al paso que ejecuta el
    comparador -dejándolas en el paso que solo comprueba que existen- y la
    batería siguió verde: el trabajo habría comprobado las claves, instalado la
    herramienta, y llegado a la comparación sin ninguna, para salir NO
    CONCLUYENTE con las dos configuraciones marcadas `sin_clave`.

    Por eso ahora se exige sobre el paso concreto que las necesita, que se
    localiza por lo que ejecuta y no por su nombre.
    """
    pasos = [p for p in _pasos(WORKFLOW) if "comparar_investigadores.py" in str(p.get("run", ""))]
    assert len(pasos) == 1, (
        f"se esperaba exactamente un paso que ejecute el comparador, hay {len(pasos)}. "
        "Si se partió en dos, esta guarda ya no sabe cuál tiene que llevar las claves"
    )
    entorno = {str(k): str(v) for k, v in (pasos[0].get("env") or {}).items()}
    faltan = [
        variable
        for variable in ("NVIDIA_API_KEY", "GOOGLE_API_KEY")
        if not _SECRETO_INTERPOLADO.search(entorno.get(variable, ""))
    ]
    assert faltan == [], (
        f"el paso que ejecuta el comparador no recibe {faltan} desde los secretos. Sin la "
        "clave, `medir_configuracion` marca esa configuración `sin_clave` y NO la mide: el "
        "trabajo gastaría la instalación entera para acabar en NO CONCLUYENTE. Y no sale "
        "rojo por sorpresa: sale rojo después de gastar los minutos."
    )


def test_las_claves_entran_por_env_y_solo_las_dos_previstas() -> None:
    """Anti-vacua: un workflow sin claves pasaría la prueba de arriba sin mérito.

    Se exige además que sean las dos de ORIGEN previstas. El criterio de parada
    (a) de la nota de arranque -«si hiciera falta clave de OpenAI o Anthropic, se
    para y se sube al propietario»- se comprueba sobre el origen: que la de
    NVIDIA se llame `OPENAI_API_KEY` DENTRO del subproceso es otra cosa, la hace
    el guion con `clave_destino`, y está permitida.
    """
    entradas: dict[str, str] = {}
    for paso in _pasos(WORKFLOW):
        for variable, valor in (paso.get("env") or {}).items():
            if _SECRETO_INTERPOLADO.search(str(valor)):
                entradas[str(variable)] = str(valor)

    assert set(entradas) == {"NVIDIA_API_KEY", "GOOGLE_API_KEY"}, (
        f"el workflow declara estas claves por `env:`: {sorted(entradas)}. Se esperaban "
        "exactamente NVIDIA_API_KEY y GOOGLE_API_KEY, los nombres de ORIGEN que declara "
        "`configuraciones.yml`. Si aparece una clave de OpenAI o de Anthropic, hay que "
        "parar y subírselo al propietario (criterio de parada (a))."
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


def test_una_medicion_que_el_hijo_declara_no_fiable_no_se_cuenta_como_medida(
    tmp_path: Path,
) -> None:
    """El hijo ya sabe que lo suyo no vale. El padre tiene que hacerle caso.

    Copiar su porcentaje como «medida completa» sería volver exactamente a la
    raíz que la refutación tumbó: un número publicado sobre una medición que su
    propio autor marcó como inservible.
    """
    modulo = _comparador()
    fuente = Path(modulo.__file__).read_text(encoding="utf-8")
    assert "medicion_fiable" in fuente, (
        "el comparador no mira `medicion_fiable`: publicaría como medida válida "
        "un resultado que el propio medidor marcó como no fiable"
    )
    marca = fuente.index("medicion_fiable")
    assert "ESTADO_FALLO" in fuente[marca : marca + 400], (
        "mira `medicion_fiable` pero no lo trata como fallo"
    )
