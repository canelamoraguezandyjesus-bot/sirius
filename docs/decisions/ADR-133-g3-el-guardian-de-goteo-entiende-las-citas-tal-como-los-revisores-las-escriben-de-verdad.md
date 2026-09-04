# ADR-133 — G3: el guardian de goteo entiende las citas tal como los revisores las escriben de verdad

- Estado: PROPUESTO
- Fecha: 2026-09-04
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

## Contexto y problema

El guardián de goteo en vivo (incidencia #496, ADR-123) está bien cableado
(`scripts/automation/sirius_apply_verdict.sh:481-495` invoca
`scripts/automation/sirius_drip_guard_cli.py`), pero en toda la ola de
criticidad reciente no marcó ni un solo hallazgo, pese a que la mina confirmó
5 goteos reales en esa ola.

Medición previa al cambio, ejecutando `parse_archivo_location`
(`src/sirius_engine/drip_guard.py:105`, regex `_LOCATION_LINE_RE`
`^(.*?):(\d+)(?:-\d+)?$`) sobre los seis campos `archivo` reales de la ola:

| # | Campo real | Antes | Debería dar |
|---|---|---|---|
| 1 | `src/sirius/presentation/knowledge_widget.py (_handle_criticality_proposal_finished, ~líneas 766-805)` (CLAUDE-REV-R2-001 de #520) | (texto entero, `None`) | (`.../knowledge_widget.py`, 766) |
| 2 | `src/sirius/presentation/knowledge_widget.py:1436-1449 (_set_controls_enabled)` | (texto entero, `None`) | (ruta, 1436) |
| 3 | `tests/unit/test_ollama_relevance_filter.py` | (ruta, `None`) | igual |
| 4 | `docs/decisions/ADR-128-m19b-el-rescate-rf-25-rf-26-y-la-prioridad-de-g12-por-criticidad.md` | (ruta, `None`) | igual |
| 5 | `src/sirius/domain/relevance.py:363` | (ruta, 363) | igual |
| 6 | `src/sirius/presentation/knowledge_widget.py:1490 en 6899ecf` | (texto entero, `None`) | (ruta, 1490) |

Solo 1 de 6 campos reales (el 5) se entendía. La regex original solo acepta
`ruta:número` limpio al final del texto; los revisores adornan el campo
`archivo` con el nombre de la función entre paréntesis, rangos con texto
detrás, el sha del commit, o la línea citada en prosa dentro del paréntesis.

## Criterio de parada (escrito ANTES de decidir)

Si para entender un caso hiciera falta cambiar el formato que escribe el
revisor (`scripts/automation` o `.github/**`), parar con
`BLOCKED_BY_DECISION`: el guardián se adapta al revisor, no al revés, y ese
cambio sería del propietario. **No se disparó**: los seis casos se resuelven
enteramente dentro de `parse_archivo_location`, sin tocar ningún formato de
salida de la revisión.

Predicción registrada antes de escribir el código:

- Los seis casos reales pasarán tras el cambio.
- La suite de `drip_guard` y las de extremo a extremo del cableado de
  ADR-123 seguirán en verde sin tocarlas.
- Ninguna métrica del banco de memoria cambia: este encargo no toca
  `src/sirius/`.
- Los dos falsos positivos conocidos de ADR-123 (línea de contexto dentro de
  un hunk modificado con una línea hermana modificada) siguen existiendo:
  este encargo arregla la lectura del campo `archivo`, no la semántica del
  guardián.

## Opciones consideradas

1. **Endurecer `parse_archivo_location` con una regla conservadora en tres
   pasos** (elegida): reconocer el prefijo de ruta real por su alfabeto de
   caracteres, aceptar `:NNN` pegado a esa ruta con cualquier texto detrás, y
   si no hay eso, buscar `línea(s) ~?NNN` en prosa en el resto del texto.
2. Pedir al propietario que cambie el formato que emite el revisor para que
   siempre sea `ruta:línea` limpio. Descartada: es exactamente la decisión
   fuera de alcance que el criterio de parada de este encargo prohíbe tomar
   por cuenta propia, y perdería información legible para humanos (el
   nombre de función, el sha) que hoy es útil en la revisión.
3. Usar una lista de rutas reales del repositorio para "adivinar" dónde
   termina la ruta contra el disco. Descartada explícitamente por el
   objetivo de la incidencia: la función es pura y no debe validar contra el
   disco; ese trabajo ya lo hace el `fetch` inyectado, que falla a
   `SIN_INFORMACION` si la ruta no existe en la comparación.

## Decisión

Se sustituye la regex única `_LOCATION_LINE_RE` por tres piezas y una regla
de precedencia fija en `parse_archivo_location`
(`src/sirius_engine/drip_guard.py`):

1. `_RUTA_PREFIX_RE` (`^[A-Za-z0-9/._-]+`) captura el prefijo de caracteres
   de ruta. Se acepta como "ruta reconocible" si ese prefijo contiene `/` o
   `.`, o -sin contener ninguno de los dos- si le sigue pegado `:NNN`
   (`_LOCATION_SUFFIX_RE`): el formato `ruta:línea` es en sí mismo la señal
   para ficheros raíz sin extensión (`LICENSE:5`), no solo el separador de
   directorio o la extensión (CLAUDE-R2-001, CODEX-002, ronda 2). Evita que
   una palabra suelta sin ninguna pinta de ruta (`"el"` de `"el cuerpo de la
   PR"`) se cuele como ruta.
2. Regla (1): si justo después de la ruta reconocible hay `_LOCATION_SUFFIX_RE`
   (`^:(\d+)(?:-\d+)?`), la línea es el primer número, sin importar qué
   texto venga después (paréntesis con función, `en <sha>`).
3. Regla (2): si la regla (1) no encontró nada **y ya hay una ruta
   reconocible**, se busca `_LOCATION_PROSE_RE` (`l[ií]neas?\s*~?\s*(\d+)`,
   sin distinguir mayúsculas) en el resto del texto. Sin una ruta reconocible
   previa, no se busca en prosa: una mención de "línea NNN" suelta en un
   texto que no identifica ningún fichero del repositorio no ancla ninguna
   comparación mecánica (CODEX-001, ronda 2). El `~` es tolerado antes del
   número; como la búsqueda no ancla el inicio, un `~` delante de la propia
   palabra "líneas" (como en "~líneas 766-805") no rompe la coincidencia.
4. Regla (3): sin número por ninguna de las dos reglas, la línea es `None` y
   la ruta es la ruta reconocible si la hubo, o el texto completo si no la
   hubo -igual que el comportamiento original para ese caso.

La función sigue siendo pura: no toca el disco, no importa nada nuevo, y el
resto del módulo (`evaluate_finding`, `annotate_observations*`,
`gh_compare_file`, `_line_kind_in_patch`) no cambia.

## Comprobación que la sostiene

1. Ocho pruebas nuevas en `tests/engine/test_drip_guard.py`, literales sobre
   los seis casos reales más dos adversarios, vistas FALLAR contra el
   parser viejo antes del cambio:

   ```
   $ git stash push -- src/sirius_engine/drip_guard.py
   $ uv run pytest tests/engine/test_drip_guard.py -k "caso_1 or caso_2 or caso_6 or adversario" -q
   4 failed, 1 passed, 26 deselected
   ```

   Fallaron exactamente los casos 1, 2, 6 y el segundo adversario (el
   primero); pasaron los casos 3, 4, 5 (comportamiento previo intacto) y el
   primer adversario -tal como predijo la incidencia.

2. Una prueba de extremo a extremo nueva en
   `tests/automation/test_sirius_drip_guard_cli.py`
   (`test_marca_una_observacion_real_de_la_ola_con_archivo_adornado`), con el
   mismo arnés que ya usan las pruebas del cableado de ADR-123: historial
   sintético de ronda 1 (`head1` = `"1"*40`) distinto del head actual
   (`head2` = `"2"*40`), la observación real CLAUDE-REV-R2-001 de #520
   (campo `archivo` = caso 1) y un `gh` simulado que devuelve `{"files":
   []}` ("el fichero no cambió"). Vista fallar contra el parser viejo:

   ```
   $ uv run pytest tests/automation/test_sirius_drip_guard_cli.py::test_marca_una_observacion_real_de_la_ola_con_archivo_adornado -q
   KeyError: 'posible_goteo'
   1 failed
   ```

   Y en verde tras el cambio.

3. Tras el cambio, las 8 pruebas nuevas de `parse_archivo_location`
   (6 casos reales + 2 adversarios), las pruebas existentes de
   `parse_archivo_location` (4), los 5 escenarios de `evaluate_finding` de
   la incidencia #496, y las pruebas de extremo a extremo del cableado de
   ADR-123 (incluida la nueva) pasan sin excepción:

   ```
   $ uv run pytest tests/engine/test_drip_guard.py tests/automation/test_sirius_drip_guard_cli.py -q
   39 passed in 0.10s
   ```

4. Corrección de ronda 2 (CLAUDE-R2-001, CODEX-001, CODEX-002): tres pruebas
   nuevas en `tests/engine/test_drip_guard.py` fijan el comportamiento
   descrito arriba en la regla (1) y la regla (2), vistas FALLAR contra el
   parser de la ronda 1 antes de esa corrección:

   - `test_ronda2_fichero_raiz_sin_extension_con_linea_pegada`:
     `parse_archivo_location("LICENSE:5") == ("LICENSE", 5)` -un fichero
     raíz sin `/` ni `.` sí cuenta como ruta reconocible cuando le sigue
     `:NNN` pegado.
   - `test_ronda2_fichero_raiz_sin_extension_con_rango_y_texto_detras`:
     mismo caso con rango y texto arbitrario detrás del número
     (`"LICENSE:5-10 en abc1234"` → `("LICENSE", 5)`).
   - `test_ronda2_prosa_sin_ninguna_ruta_reconocible_no_marca_linea`:
     `parse_archivo_location("el cuerpo de la PR (línea 10)")` devuelve la
     línea `None` -sin una ruta reconocible previa, la búsqueda en prosa de
     la regla (2) no se aplica sobre el texto completo.

   ```
   $ uv run pytest tests/engine/test_drip_guard.py tests/automation/test_sirius_drip_guard_cli.py -q
   42 passed in 0.15s
   ```

5. Mutaciones (ADR-001), ambas aplicadas y revertidas sobre el código ya
   corregido:

   - **Mutación 1** (revertir la regla (1) a la regex vieja, sobre el texto
     completo en vez de la ruta reconocible, sin regla (2)): reproduce el
     comportamiento anterior íntegro. Falla exactamente donde predice el
     objetivo -casos 1, 2, 6 y el segundo adversario- y pasa el resto
     (comprobado en el paso 1 de esta sección, que es la misma condición).

   - **Mutación 2** (la regla (2), la búsqueda en prosa, se comprueba ANTES
     que la regla (1)):

     ```
     $ uv run pytest tests/engine/test_drip_guard.py -q
     FAILED test_adversario_dos_numero_pegado_a_la_ruta_gana_al_parentesis
       assert ('src/x.py', 80) == ('src/x.py', 50)
     1 failed, 30 passed
     ```

     Falla únicamente el caso diseñado para demostrar la precedencia
     (`"src/x.py:50 (líneas 80)"` debe dar 50, no 80); el resto de la suite
     sigue en verde, así que la mutación no se camufla dentro de un fallo
     más amplio.

6. Validaciones obligatorias completas sobre el árbol final:

   ```
   $ uv run ruff format --check .   → 594 files already formatted
   $ uv run ruff check .            → All checks passed!
   $ uv run mypy src tests          → Success: no issues found in 562 source files
   $ uv run pytest -q               → 4691 passed, 15 skipped, 2 xfailed in 452.14s
   $ git diff --check               → limpio
   ```

   Cifra re-ejecutada sobre el árbol final, después de la corrección de
   ronda 2 (paso 4). Comparada contra `main` (9fd2666, 4695 pruebas
   recolectadas antes de esta rama) mediante `pytest --collect-only`, esta
   rama recolecta 4708, +13 en total: `tests/engine/test_drip_guard.py` pasa
   de 8 a 11 pruebas nuevas sobre el archivo original (6 casos reales + 2
   adversarios + 3 de ronda 2), `tests/automation/test_sirius_drip_guard_cli.py`
   añade 1, y `tests/automation/test_citas_de_los_adr.py::test_toda_ruta_citada_por_un_adr_existe`
   -parametrizada sobre cada archivo de `docs/decisions/`- gana 1 caso más
   porque este propio ADR-133 es un archivo nuevo en ese directorio.

## Consecuencias

- El guardián ahora entiende 6 de 6 campos `archivo` reales de la ola
  auditada, en vez de 1 de 6, sin cambiar su naturaleza estrictamente
  informativa: sigue sin bloquear rondas, sin alterar `fingerprint` ni
  severidad, sin tocar `round_family_detector` ni la política de
  convergencia.
- Sigue existiendo la limitación conocida y ya declarada en ADR-123: una
  línea de contexto sin tocar dentro de un hunk modificado con una línea
  hermana que sí cambió se marca igual que una línea completamente fuera de
  hunk. Este encargo no la toca -arregla la lectura del campo `archivo`, no
  la semántica de la comparación de líneas.
- La tasa real de marcado en producción, antes casi nula por esta causa
  raíz, debería subir a partir de la próxima ola con hallazgos de ronda >1
  que citen fichero y línea con estos adornos. Sigue siendo una medición a
  observar (criterio de la incidencia #267) antes de dar cualquier
  autoridad a la marca.

## Alternativas descartadas y por qué

Ver "Opciones consideradas": pedir al propietario un formato de salida más
estricto y validar contra el disco dentro de la función pura se descartaron
por estar fuera del alcance permitido de esta incidencia (la primera exige
una decisión de `.github/**`/`scripts/automation` que no es de este
encargo; la segunda contradice el requisito explícito de que la función siga
siendo pura).
