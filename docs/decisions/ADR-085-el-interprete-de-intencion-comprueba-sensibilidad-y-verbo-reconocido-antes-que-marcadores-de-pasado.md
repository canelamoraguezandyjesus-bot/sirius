# ADR-085 — El intérprete de intención comprueba sensibilidad y verbo reconocido antes que marcadores de pasado

- Estado: PROPUESTO
- Fecha: 2026-08-25
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

## Contexto y problema

`docs/audits/evidencia-H-19.md` midió que `interpretar_intencion_v0`
(`src/sirius_engine/intent_interpreter.py`) comparaba sus marcadores léxicos
con el operador `in` sobre el texto normalizado, sin frontera de palabra, y
además comprobaba los marcadores de pasado **antes** que la sensibilidad. De
esa raíz salían tres fallos medidos:

- **(a)** Una orden destructiva o de gasto que contuviera por casualidad
  `estado de` (p. ej. `'borra el estado de la base de produccion'`) se
  despachaba como `consultar_pasado` y nunca llegaba al detector de
  sensibilidad: fail-open en una puerta que el propio comentario del módulo
  declara fail-closed («es preferible sobre-marcar como sensible que dejarlo
  pasar»). Esto toca el alcance del *fail-closed* de la puerta — criterio del
  propietario sobre su propia barrera, no del implementador.
- **(b)** `estado de` es subcadena de `estado del`, giro corriente en este
  repositorio (`'documenta el estado del motor'`, `'corrige el estado del
  despachador'`); y en un tercer caso el marcador aparece de verdad
  (`'audita el estado de las pruebas'`) pero la frase es una orden legítima
  sobre la situación actual de un módulo, no una consulta sobre el pasado.
- **(c)** `_primer_verbo` no quitaba la puntuación de borde, así que el
  formato que el propio `--help` propone como ejemplo (verbo entre comillas
  angulares) salía `ambigua` mientras el mismo texto sin comillas se
  despachaba bien.

La incidencia #325 (Work ID WI-20260825-115114) pedía corregir los tres en el
mismo cambio, condicionado a una única decisión del propietario: si la
sensibilidad debe comprobarse antes que los marcadores de pasado. Esa
pregunta se resolvió en #324.

## Criterio de parada (escrito ANTES de decidir)

Antes de tocar el código: las cuatro pruebas de `tests/engine/test_intent_interpreter.py`
que fijan (a), (b) y (c) —una por cada fallo medido, más una compuesta— deben
verse **FALLAR** con el intérprete sin modificar, reproduciendo la
clasificación equivocada exacta que registra `evidencia-H-19.md`. Si alguna
no falla como se predice, la raíz no está bien identificada y no se toca el
código hasta corregir la hipótesis. Tras el cambio, las mismas pruebas deben
pasar y ninguna prueba preexistente del módulo puede cambiar de resultado.

## Opciones consideradas

1. Parchear cada caso por separado (añadir excepciones a `_MARCADORES_PASADO`,
   o casos especiales en `_detectar_sensibilidad`). Descartado: es la
   "segunda ronda con defectos de la misma familia" que ADR-001 pide parar y
   resolver por la raíz, no seguir parcheando.
2. Corregir solo la comparación por subcadena (frontera de palabra) y el
   orden sensibilidad-antes-que-pasado, dejando intacto el orden entre
   "verbo reconocido" y "marcadores de pasado". Descartado: no cierra (b) en
   su tercer caso — `'audita el estado de las pruebas'` contiene el marcador
   `estado de` de verdad, no por colisión de subcadena, así que la frontera
   de palabra no lo resuelve.
3. **Elegida.** Reordenar las comprobaciones por la raíz que
   `evidencia-H-19.md` nombra explícitamente («comparación de marcadores por
   subcadena sin frontera, **más el orden de las comprobaciones**»):
   sensibilidad primero, después verbo reconocido, después
   pasado/exploración/pregunta; y hacer la comparación de marcadores con
   frontera de palabra en todas las listas que usan `in`.

## Decisión

`interpretar_intencion_v0` clasifica en este orden:

1. Saludo / mensaje vacío → `conversar`.
2. **Sensibilidad** (`_detectar_sensibilidad`, con frontera de palabra) →
   `sensible_o_material`, **siempre**, aunque el mensaje contenga además un
   marcador de pasado o de exploración. Decisión del propietario en #324:
   *"Sí, que avise siempre, aunque a veces avise de más"* — fail-closed
   explícito: prioriza no dejar pasar una orden sensible por otra rama,
   incluso a costa de escalar de más.
3. **Verbo reconocido** (clase por `_VERBO_A_CLASE` o en
   `_VERBOS_IMPERATIVOS_SIN_CLASE`) → `orden_inequivoca` directamente, sin
   pasar por los marcadores de pasado/exploración/pregunta. Un primer verbo
   imperativo reconocido hace inequívoca la orden por sí solo; dejar que un
   marcador de pasado en el resto de la frase la reclasifique es el mismo
   error de raíz que (a) pero sin implicación de seguridad — es mecánico, no
   necesita decisión del propietario.
4. Marcadores de pasado, exploración y pregunta final (con frontera de
   palabra) → `consultar_pasado` / `explorar`, solo si (2) y (3) no
   aplicaron.
5. Si nada de lo anterior aplica → `ambigua`.

Los marcadores de todas las listas (`_MARCADORES_PASADO`,
`_MARCADORES_EXPLORACION`, `_MARCADORES_DESTRUCTIVO`, `_MARCADORES_GASTO`,
`_MARCADORES_CREDENCIALES`, `_MARCADORES_PRIVACIDAD`) se comparan con
`_marcador_presente`, que exige frontera de palabra (`\b...\b`) en vez de
subcadena libre.

`_primer_verbo` quita la puntuación de borde (`_PUNTUACION_DE_BORDE`) del
primer token antes de buscarlo en `_VERBO_A_CLASE`.

## Comprobación que la sostiene

Antes del cambio, con el intérprete sin modificar:

```
$ uv run pytest tests/engine/test_intent_interpreter.py -k "sensibilidad_se_comprueba or frontera_de_palabra or ignora_puntuacion"
...
9 failed, 32 deselected
```

Las 9 fallaban exactamente como predice `evidencia-H-19.md`: los tres casos
de (a) con `AssertionError: assert <CONSULTAR_PASADO> is <SENSIBLE_O_MATERIAL>`,
los tres de (b) con `assert <CONSULTAR_PASADO> is <ORDEN_INEQUIVOCA>`, los
tres de (c) con `assert <AMBIGUA> is <ORDEN_INEQUIVOCA>`.

Después del cambio:

```
$ uv run pytest tests/engine/test_intent_interpreter.py
41 passed
$ uv run ruff format --check .
499 files already formatted
$ uv run ruff check .
All checks passed!
$ uv run mypy src tests
Success: no issues found in 476 source files
$ uv run pytest
3569 passed, 9 skipped in 294.97s
```

Ninguna prueba preexistente del módulo cambió de resultado: las 32 pruebas
que ya pasaban antes del cambio (saludos, preguntas del pasado con marcador
genuino y sin verbo reconocido, exploración, órdenes sensibles ya
correctamente detectadas, clases por verbo, alcance/criterio por clase)
siguen pasando con la misma clasificación.

## Consecuencias

- Una orden con un marcador de sensibilidad siempre escala o pide
  confirmación, sin importar qué más contenga la frase — puede sobre-marcar
  como sensible texto que no lo era, que es el trade-off que el propietario
  aceptó explícitamente en #324.
- Un mensaje que empiece con un verbo imperativo reconocido nunca se
  clasifica como `consultar_pasado` o `explorar`, aunque el resto de la
  frase contenga esos marcadores — el primer verbo decide.
- La frontera de palabra es ahora la regla general de comparación de
  marcadores en todo el módulo, no solo para los de pasado.

## Alternativas descartadas y por qué

Ver "Opciones consideradas". La opción 1 (parches puntuales) queda descartada
por ADR-001: dos rondas de la misma familia de defecto piden buscar la raíz.
La opción 2 (frontera de palabra + orden sensibilidad/pasado, sin tocar el
orden verbo/pasado) queda descartada porque no cierra el tercer caso de (b),
medido y exigido por `evidencia-H-19.md`.
