# Nota de arranque — el detector de familia agrupa por la ruta, no por el recorte final

Rama `fix/el-detector-de-familia-agrupa-por-la-ruta`, 14-09-2026. Publicada
**antes del primer commit de arreglo**, como exige ADR-001.

## De dónde sale, y qué está ya medido

El propietario decidió, en la madrugada del 14-09: *«detector de familia
repetida: SÍ a darle autoridad para parar el ciclo, PERO con la medida de
septiembre delante; si la tasa aguanta, dársela»*. La mina de septiembre
—`docs/audits/SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09-14.md`, §4— ya trajo esa
medida, y trajo además un hallazgo que no se buscaba:

| | |
|---|---|
| Avisos emitidos en septiembre | 8 casos distintos |
| Acertados / falsos | **8 / 0** (12 / 0 sumando ADR-078) |
| **Familias reales que NO vio** | **6**, en 5 incidencias |
| Causa de las seis | **una línea** |

La línea es `LOCATION_LINE_RE = re.compile(r":\d+(?:-\d+)?$")`
(`src/sirius_engine/round_history.py:79`), anclada al final: solo recorta el
sufijo de línea cuando la cadena **termina** en él. Los revisores escriben
`fichero.py:185-205 y :230`, así que la misma ruta cuenta como otro fichero y el
tramo se rompe.

Y la pieza que lo resuelve **ya existe en este árbol**: `parse_archivo_location`
(`src/sirius_engine/drip_guard.py`), construida para la incidencia #523/G3
precisamente porque el guardián de goteo se topó con el mismo problema. El
detector no la llama.

La mina midió el cambio **antes de proponerlo**: la variante laxa caza **+6
familias reales y 2 falsos positivos**, neto **+4** por el criterio de entrada de
la incidencia #267.

## 1. ¿Dónde vive el fallo y dónde va el arreglo?

El fallo vive en **cómo agrupa el detector**, no en el umbral de 3 rondas, que
ADR-078 midió y que este trabajo no toca.

Y hay un sitio donde el arreglo **no** puede ir: `_normalize_location`.
`scripts/automation/sirius_convergence.py` la comparte con
`fingerprint`, que es el mecanismo de *sin-progreso*, otro distinto. Cambiarla
cambiaría la huella de convergencia sin haberla medido, que sería arreglar una
cosa rompiendo otra a ciegas.

Así que el arreglo va en `round_family_detector.py`, que pasa a derivar la ruta
con `parse_archivo_location` para agrupar, y `_normalize_location` se queda como
está.

*¿Puede el sitio del arreglo observar el fallo que arregla?* Sí: el detector
tiene delante el campo `archivo` tal como el revisor lo escribió.

## 2. Lo que hay que resolver para que esto funcione DE VERDAD

`sirius_convergence.py` corre con el **`python3` desnudo del runner, sin el
proyecto instalado**, y carga `round_family_detector.py` por ruta registrando a
mano en `sys.modules` un paquete `sirius_engine` simulado que **solo** contiene
`round_history`. Un `from sirius_engine.drip_guard import …` nuevo **rompería
eso** con `ModuleNotFoundError` en producción, y las pruebas que corren con el
proyecto instalado no lo notarían.

Ya existe una prueba que lo vigila —
`test_cli_family_check_runs_under_the_bare_system_python_without_the_project_installed`—
y es la que manda aquí. El simulacro tiene que registrar también
`sirius_engine.drip_guard`, cargado por ruta como los otros dos, y deshacerlo al
terminar igual que hace hoy.

## 3. ¿Qué NO va a garantizar esto?

- **No da autoridad al detector.** Esa es la otra mitad de la decisión del
  propietario y va aparte, por una razón que este trabajo descubre y que hay que
  decirle: el «8 de 8, cero falsos» está medido **con el agrupamiento viejo**.
  Las seis detecciones que este cambio añade traen 2 falsos positivos, así que la
  tasa combinada pasa a ser **14 aciertos y 2 falsos sobre 16**. Su condición era
  «si la tasa aguanta»; la tasa cambia con este arreglo, y quien decide sobre la
  nueva es él, con el número delante.
- **No toca el umbral de 3 rondas consecutivas** (ADR-078).
- **No caza las familias que se mueven de fichero entre rondas.** La #545 tiene
  una, entre `mirror_projection.py` y `reflect.py`, y este método no la ve. El 6
  es un suelo, como declara la propia mina.
- **No toca `.github/**`.**

## 4. Criterio de parada, decidido ANTES de tocar nada

- **`_normalize_location` no se cambia.** Si el arreglo obliga a cambiarla, se
  para: la huella de convergencia es otro mecanismo y no está medido aquí.
- **No se duplica el parser.** Si la única forma de usarlo fuera copiarlo, se
  para: una pieza copiada es la familia que este repositorio lleva cerrando.
- **La prueba del `python3` desnudo tiene que seguir pasando**, y sin retocarla
  para que quepa el cambio.
- **Los seis casos que la mina nombra tienen que pasar a detectarse**, y los dos
  que declaró falsos positivos tienen que seguir saliendo: si el arreglo caza
  más de lo que la mina midió, es que hace otra cosa distinta de la medida.
- **Cada regla nueva, una mutación sembrada y vista caer.**

## 5. ¿Qué haría el fallo imposible en vez de improbable?

**Que no haya dos formas de leer una cita de fichero en este repositorio.** Hoy
hay dos: el recorte anclado de `round_history` y el parser tolerante de
`drip_guard`, y el defecto es exactamente que una pieza usó la que no era. Con
este cambio quedan las dos, pero cada una con su dueño declarado: la huella de
convergencia usa la suya y todo lo que lea una cita como los revisores la
escriben usa la otra.

Lo que lo cerraría del todo sería **una sola función** y que la huella de
convergencia se midiera con ella. Eso exige medir de nuevo el `sin-progreso`
completo, es una decisión aparte, y **no se hace aquí**: queda declarado.
