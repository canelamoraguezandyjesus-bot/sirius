# ADR-076 — El motor deja de necesitar el árbol de código para ejecutar la proyección

- Estado: PROPUESTO
- Fecha: 2026-08-23
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

## Contexto y problema

`sirius_engine.mirror_projection` (A3, incidencia #193) interpreta el
historial de una incidencia reutilizando tres funciones puras de
`scripts/automation/sirius_convergence.py` -`parse_round_records`,
`history_after_last_resume`, `ci_failure_streak`- en vez de duplicarlas.
Hasta este bloque lo hacía insertando `scripts/` en `sys.path` e importando
el script de automatización directamente. Eso funciona en un checkout de
desarrollo, pero `pyproject.toml` solo empaqueta `sirius`/`sirius_engine`
(`scripts/` es automatización del repo, no parte del wheel): cualquier
llamador fuera del checkout -incluida una instalación real del paquete-
revienta con `ModuleNotFoundError` en cuanto se **llama** a la proyección
(incidencia #272).

Un intento previo de arreglarlo dentro de D1b (incidencia #269, commit
`1e8a52f`, "ronda 3") difirió el import a una función interna, y dos pruebas
nuevas fijaron ese comportamiento. Pero seguía fallando en una instalación
real desde wheel -difirió CUÁNDO se importa, no CÓMO se resuelve-, y el
propio D1b lo revirtió en su "ronda 4" (commit `c14ab7d`) por estar fuera de
su alcance declarado, dejando el defecto explícitamente para esta incidencia
(#275, H-13). **La nota de arranque de #275 asumía que esa ronda 3 seguía en
`main`** ("importar el módulo fuera del checkout ya funciona"); no es así:
el `main` sobre el que arranca este bloque tiene el import eager de siempre,
igual que `sirius-despachar`. Se documenta aquí porque cambia el punto de
partida técnico (hay que retirar un `sys.path`+import a nivel de módulo, no
una función `_sirius_convergence()` que no existe en `main`), pero no cambia
el objetivo del bloque ni activa ningún criterio de parada: sigue siendo
exactamente el defecto que #275 pide arreglar, solo que sin arreglar a medias
todavía.

La restricción dura, medida en la propia incidencia: `sirius_convergence.py`
lo ejecuta `repair-sirius-work.yml:285` con el `python3` **del sistema**, sin
`uv sync`, sin el paquete instalado. Si el arreglo hiciera que ese script
importara `sirius_engine`, el workflow de reparación dejaría de arrancar.

## Criterio de parada (escrito ANTES de decidir)

Copiado literal de la nota de arranque de la incidencia #275, más la quinta
condición ya verificada como no aplicable antes de tocar código:

(a) Si el arreglo obliga a `sirius_convergence.py` a importar `sirius_engine`
    -incluso indirectamente-, se para.
(b) Si hace falta duplicar `parse_round_records`/`history_after_last_resume`/
    `ci_failure_streak` en dos ficheros con contenido independiente, se para.
(c) Si el módulo compartido necesita sintaxis que el `python3` 3.12 del
    runner no entienda, se para.
(d) Cualquier edición de `.github/**` es criterio de parada.
(e) Si medir demuestra que llamar a la proyección ya no inyecta nada -porque
    otro cambio se adelantó-, se para: comprobado ANTES de decidir (ver
    Contexto) que no es el caso; `main` sigue teniendo el import eager.

## Opciones consideradas

1. **Enlace simbólico**: el contenido vive una sola vez en
   `src/sirius_engine/round_history.py` (para que el paquete lo importe sin
   ningún truco: `from sirius_engine.round_history import ...`), y
   `scripts/automation/round_history.py` es un enlace simbólico a ese mismo
   fichero. `sirius_convergence.py` carga su hermano por ruta de fichero
   (`importlib.util.spec_from_file_location`, el mismo patrón que ya usa
   `tests/automation/test_sirius_convergence.py` para cargar el propio
   script), sin pasar por `import sirius_engine...` en ningún punto.
2. **Tercer módulo empaquetado de forma independiente** (`round_history` como
   distribución propia junto a `sirius`/`sirius_engine`): descartada por el
   backend de construcción (ver más abajo, `uv_build` exige que cada entrada
   de `module-name` sea un paquete real bajo `src/`, no un módulo suelto).
3. **Cargar `src/sirius_engine/round_history.py` desde el script insertando
   `src/` en `sys.path` e importando `sirius_engine.round_history`**:
   descartada porque ejecutar ese `import` construye `sirius_engine` como
   paquete en `sys.modules` -aunque su `__init__.py` esté vacío hoy-, que es
   precisamente lo que el criterio de parada (a) prohíbe por nombre.

## Decisión

Opción 1. `src/sirius_engine/round_history.py` es la única definición real
de las tres funciones (con las expresiones regulares y funciones auxiliares
que necesitan: `ROUND_RECORD_RE`, `RESUME_MARKER_RE`,
`CI_FAILURE_MARKER_RE`/`CI_SUCCESS_MARKER_RE`, `SEVERITY_WEIGHTS`,
`severity_weight`, `_normalize_text`, `_normalize_location`). Movidas tal
cual, sin reescribir su lógica.

`scripts/automation/round_history.py` es un enlace simbólico relativo
(`../../src/sirius_engine/round_history.py`) al mismo fichero -comprobado
que `uv build --wheel` resuelve el enlace y empaqueta el contenido real, no
un enlace roto-.

`mirror_projection.py` importa el módulo compartido de forma normal:
`from sirius_engine.round_history import (ci_failure_streak,
history_after_last_resume, parse_round_records)`. Sin `sys.path`, sin
`scripts/` en ninguna parte.

`sirius_convergence.py` deja de definir esas funciones y carga su hermano
`round_history.py` por ruta de fichero
(`importlib.util.spec_from_file_location`, resuelta desde `Path(__file__)`),
exactamente el mismo patrón que la suite de pruebas ya usaba para cargar el
propio script. No hace `import sirius_engine` ni `import round_history` a
secas -este último habría exigido meter `scripts/automation` en `sys.path`,
que además de ser el mismo tipo de truco que se retira, se rompería en
cuanto el script se cargara por ruta (como ya hace la suite) en vez de
ejecutarse como `__main__`-.

`pyproject.toml` no cambia: `round_history.py` vive dentro de
`src/sirius_engine/`, un directorio que el backend de construcción ya
empaqueta.

## Comprobación que la sostiene

- `uv build --wheel -o /tmp/…` con un fichero de sonda enlazado
  simbólicamente desde `src/sirius_engine/` a `scripts/automation/`:
  el wheel resultante contiene el fichero real (no un enlace), confirmado
  extrayéndolo y leyendo su contenido.
- Antes del arreglo: construir el wheel real, instalarlo con
  `uv pip install --no-deps` en un venv limpio y ejecutar
  `sirius-despachar --help` reproduce
  `ModuleNotFoundError: No module named 'automation'` exactamente en
  `mirror_projection.py:52`. Después del arreglo, la misma secuencia
  responde `0` y sin ese error -automatizado en
  `tests/automation/test_installed_entry_points.py`, que construye e instala
  el wheel real en cada ejecución de la suite-.
- `tests/engine/test_mirror_projection.py::test_proyectar_funciona_sin_scripts_en_sys_path_ni_automation_importable`:
  quita `scripts/` de `sys.path`, confirma que `automation` deja de ser
  importable, y LLAMA a `proyectar_work_item` sobre el ciclo completo de la
  fixture #186 (requisito de aceptación 1).
- `tests/automation/test_sirius_convergence.py::test_cli_decide_runs_under_the_bare_system_python_without_the_project_installed`:
  ejecuta `sirius_convergence.py` con `/usr/bin/python3` (Python 3.12, el
  mismo que `RUNNER_PYTHON` en `test_sirius_runner_python_compat.py`), con
  `PATH` como único entorno -sin `PYTHONPATH`, sin `VIRTUAL_ENV`- y `cwd` en
  la raíz del repositorio, igual que `repair-sirius-work.yml:285`. Responde
  `CONTINUE`/`primera-ronda-con-hallazgos` (requisito 3).
- `tests/automation/test_sirius_runner_python_compat.py` amplía su lista con
  `round_history.py`: `ast.parse(..., feature_version=(3, 12))` sobre el
  módulo compartido (requisito 2).
- `tests/automation/test_round_history.py`: `Path.samefile()` entre las dos
  rutas prueba que son el mismo fichero, no una copia; y una comprobación
  estructural (`def <nombre>(` cuenta exactamente una vez en el canónico,
  cero en cualquier otro `.py` de `src/`/`scripts/automation/`) cierra el
  requisito 4.
- `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src
  tests` y `uv run pytest` (incluida la suite completa, GUI en modo
  offscreen) en verde. `tests/automation/test_sirius_convergence.py` no
  tocó ninguna de sus pruebas previas (requisito 5): solo se le añadió la
  prueba del intérprete pelado.

## Consecuencias

- `sirius_engine.round_history` pasa a ser parte pública del paquete (no
  privada de `mirror_projection`): cualquier otro módulo del motor puede
  reutilizar estos analizadores sin volver a inventar el truco de `sys.path`.
- El enlace simbólico es una dependencia estructural nueva: si algún día se
  reorganiza `scripts/automation/` o `src/sirius_engine/`, hay que mover el
  enlace con el fichero real, no solo el fichero. `test_round_history.py`
  falla de inmediato si el enlace se rompe o dos copias divergen.
- `sirius_convergence.py` gana una función `_cargar_round_history()` de
  cuatro líneas en vez de un `import` directo; es el precio de que ese
  script siga arrancando bajo un `python3` que no tiene el paquete instalado.
- `tests/automation/test_installed_entry_points.py` añade a la suite un
  `uv build`/`uv venv`/`uv pip install` real en cada ejecución (offline,
  usando la caché de `uv`; ~0.5 s en este entorno). Es una prueba de
  integración deliberadamente pesada porque el requisito 6 pide exactamente
  eso: que los puntos de entrada arranquen desde una instalación, no que se
  importen sin fallar.

## Alternativas descartadas y por qué

- **Symlink en dirección inversa** (fichero real en
  `scripts/automation/round_history.py`, enlace en `src/sirius_engine/`):
  funcionalmente equivalente -mismo inodo, cualquier lado resuelve al
  mismo contenido-, pero se prefirió el fichero real dentro del paquete
  porque son analizadores de dominio (interpretar el historial de una
  incidencia) que el motor debería poder reutilizar sin que su origen
  "real" viva en la carpeta de automatización del repositorio.
- **Insertar `scripts/automation` en `sys.path` desde dentro de
  `sirius_convergence.py`** para poder hacer `import round_history` a
  secas: descartada por ser el mismo tipo de mutación global de `sys.path`
  que este bloque existe para retirar del lado del paquete, aunque aquí
  fuera autorreferencial. `importlib.util.spec_from_file_location` logra lo
  mismo sin tocar `sys.path` en absoluto y reutiliza un patrón que la propia
  suite de pruebas del repositorio ya validaba.
- **Declarar el requisito 6 como no comprobable y limitarse a documentarlo**:
  la incidencia lo permite explícitamente ("declarando el límite si lo
  hay"), pero antes de recurrir a esa salida se comprobó que `uv build` +
  `uv venv` + `uv pip install --offline` funcionan sin red en este entorno
  (evidencia arriba), así que se prefirió la prueba automática real.
