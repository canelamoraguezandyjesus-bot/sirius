# ADR-177 — La contradicción de etiquetas se decide por lo que proyectan, no por cuántas son

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: la fusión de la PR por el propietario

Este ADR es además la **nota de arranque** de la rama
`fix/contradiccion-de-etiquetas-por-lo-que-proyectan` (incidencia #594,
WI-20260912-223921): las cuatro preguntas y el criterio de parada se
escribieron ANTES de tocar una línea de `mirror_projection.py`.

## Contexto y problema

`mirror_projection._estado_y_fase` decidía que unas etiquetas se contradicen
**contándolas**:

```python
if len(presentes) > 1 and presentes != _PAR_DE_ACTIVACION_VALIDO:
    return None, None, True
```

Es decir: más de una etiqueta `sirius:*` reconocida es contradicción, salvo la
única pareja que alguien se acordó de escribir a mano
(`sirius:planned` + `sirius:implement-requested`, exenta desde la auditoría de
la PR #146).

**Reproducido el 12-09-2026 sobre la incidencia real #592.** Lleva
`sirius:repair-requested` y `sirius:repairing` a la vez, que es lo normal
mientras el corrector trabaja: la primera es el encargo y la segunda el acuse.
Las dos son `(ACTIVE, REPARAR)` en `_LABEL_STATE`. La proyección devolvía
`(None, None, True)` y, aguas abajo, el tablero de ADR-175
(`tablero.py:255-257`) le decía al propietario:

> ⚠️ **sus etiquetas de estado se contradicen** — míralo: el motor no puede
> decidir qué estado tiene

en una incidencia que iba perfectamente. Y no se queda en el tablero:
`projection_verifier._ventana_contradiccion` retira del registro la comparación
entera de esa incidencia (`NO_COMPARABLE`), así que el día no puede salir verde
por una avería que no existe.

El defecto no es la pareja que falta en la lista: es que el criterio mira la
**cardinalidad** cuando lo que decide una contradicción es el **destino**. Dos
etiquetas que dicen lo mismo no son un desacuerdo; son el mismo hecho dicho dos
veces.

## Nota de arranque (cuatro preguntas, ADR-001)

### 1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo OBSERVAR el fallo?

El fallo vive en `_estado_y_fase` (`src/sirius_engine/mirror_projection.py`),
la única función del módulo que decide qué significa un conjunto de etiquetas.
El arreglo va ahí mismo, y **sí puede observar el fallo**: la tabla que define
a dónde apunta cada etiqueta —`_LABEL_STATE`— está tres líneas más arriba, en
el mismo módulo, y es exactamente el dato que el criterio necesitaba y no
miraba. No hace falta ir a buscar nada fuera; hacía falta leer lo que ya estaba
al lado.

El tablero y el verificador **no** se tocan: los dos hacen lo correcto con lo
que reciben. Arreglar el mensaje del tablero habría sido tapar el dato malo en
el sitio donde se enseña, no donde se produce.

### 2. ¿Qué NO va a garantizar esto?

- **No garantiza que las etiquetas de GitHub sean coherentes.** Sigue siendo
  posible pegar a mano `sirius:completed` y `sirius:failed-safely`; lo que se
  promete es que eso se siga llamando contradicción, no que no ocurra.
- **No garantiza que la tabla `_LABEL_STATE` sea correcta.** Si mañana alguien
  le da a `sirius:reviewing` una fase equivocada, el criterio derivado heredará
  ese error sin ruido. La tabla sigue siendo la interpretación única del
  vocabulario y sigue sin más garantía que las pruebas que ya la atan a los
  workflows (`test_el_vocabulario_interpretado_es_el_que_de_verdad_se_crea`).
- **No arregla ninguna incidencia ya reflejada.** El registro del verificador no
  se reescribe hacia atrás; las pasadas futuras sobre #592 dejan de acusarla,
  las líneas ya escritas se quedan como están.
- **No toca el desempate `_LABEL_PRIORITY`.** Sigue existiendo y sigue atado por
  su prueba, aunque con este criterio todas las etiquetas que llegan a él
  proyecten ya lo mismo.

### 3. Criterio de parada (escrito ANTES de ver ningún resultado)

- **Paro y escalo si** al medir resulta que alguna pareja que hoy da
  contradicción **legítima** apunta al mismo `(estado, fase)`. Eso significaría
  que la tabla no basta para decidir y que hace falta una decisión de producto
  sobre el vocabulario, no un cambio de criterio.
- **Paro y escalo si** el criterio derivado dejara de marcar contradicción en
  `sirius:completed` + `sirius:failed-safely`. Es lo que la puerta protege y
  debilitarlo está fuera de lo que esta incidencia autoriza.
- **Retiro `_PAR_DE_ACTIVACION_VALIDO`** si y solo si la medición muestra que la
  pareja que exime queda eximida sola por el criterio derivado. Si quedara
  fuera, el criterio está mal y se para.
- **Dos rondas con defectos de la misma familia → parar y buscar la raíz**, no
  seguir añadiendo parejas.

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

Que la exención **no se pueda escribir**. Mientras el criterio sea una lista de
parejas, el fallo solo es improbable: depende de que alguien recuerde ampliarla
cada vez que el vocabulario crezca. Derivarlo de `_LABEL_STATE` lo hace
imposible por construcción —una fila nueva en la tabla entra sola— y
`test_la_exencion_se_deriva_de_la_tabla_y_no_de_una_lista_a_mano` recorre las
78 parejas del vocabulario comprobando el reparto contra la tabla, sin
escribirlo, así que cualquier vuelta a una lista a mano sale en rojo.

## La medición (hecha ANTES de decidir)

`uv run python` sobre `_LABEL_STATE`, las 13 etiquetas del vocabulario y sus
78 parejas:

| Destino `(estado, fase)` | Etiquetas que apuntan ahí |
|---|---|
| `(PLANNED, PREPARAR)` | `sirius:planned`, `sirius:implement-requested` |
| `(ACTIVE, EJECUTAR)` | `sirius:implementing`, `sirius:audit-requested` |
| `(ACTIVE, COMPROBAR)` | `sirius:ci-pending` |
| `(ACTIVE, REVISAR)` | `sirius:review-requested`, `sirius:reviewing` |
| `(ACTIVE, REPARAR)` | `sirius:repair-requested`, `sirius:repairing` |
| `(ACTIVE, ENTREGAR)` | `sirius:ready-for-merge` |
| `(NEEDS_DECISION, None)` | `sirius:blocked-decision` |
| `(FAILED_SAFELY, None)` | `sirius:failed-safely` |
| `(DELIVERED, ENTREGAR)` | `sirius:completed` |

- **4 parejas de 78 apuntan al mismo `(estado, fase)`**: activación
  (`planned` + `implement-requested`), ejecución (`implementing` +
  `audit-requested`), revisión (`review-requested` + `reviewing`) y reparación
  (`repair-requested` + `repairing`).
- **74 apuntan a estado o fase distintos**, y siguen siendo contradicción. Entre
  ellas las dos que la puerta protege: `completed` + `failed-safely` (estados
  distintos) y `completed` + `ready-for-merge` (misma fase `ENTREGAR`, estados
  `DELIVERED` y `ACTIVE`).
- **25 parejas comparten estado pero no fase** —todas las combinaciones de
  `ACTIVE` entre fases distintas—. Son el motivo por el que el criterio compara
  el par completo y no solo el estado: eximirlas convertiría un
  `implementing` + `ready-for-merge` en una entrega silenciosa.
- La única pareja que `_PAR_DE_ACTIVACION_VALIDO` eximía a mano es exactamente
  una de las cuatro que el criterio derivado exime solo. **Queda innecesaria**,
  y el criterio de parada decía que en ese caso se retira: se retira.

Ninguna pareja que hoy dé contradicción legítima apunta al mismo destino, así
que no se activó la condición de escalar.

## Opciones consideradas

1. **Añadir las tres parejas que faltan a `_PAR_DE_ACTIVACION_VALIDO`** (o
   convertirlo en un conjunto de parejas). Es la reparación mínima y la que el
   código invitaba a hacer.
2. **Derivar el criterio de `_LABEL_STATE`**: hay contradicción si y solo si las
   etiquetas presentes proyectan más de un `(estado, fase)` distinto.
3. **Agrupar las etiquetas por «etapa» en una tabla nueva** y comparar etapas.

## Decisión

**Opción 2.** `_estado_y_fase` calcula el conjunto de destinos de las etiquetas
presentes y marca contradicción si y solo si hay más de uno:

```python
if len({_LABEL_STATE[etiqueta] for etiqueta in presentes}) > 1:
    return None, None, True
```

Si todas apuntan al mismo sitio, la proyección devuelve ese estado y esa fase
con `etiquetas_contradictorias=False`. `_PAR_DE_ACTIVACION_VALIDO` se **retira**:
la medición muestra que su única pareja queda eximida sola, y mantener una lista
a mano al lado de un criterio derivado es garantizar que las dos se separen.

La opción 1 se descarta porque repara el síntoma con el mismo mecanismo que lo
produjo: la próxima etiqueta del vocabulario volvería a llegar sin su pareja. La
opción 3 se descarta porque inventa una segunda tabla que puede divergir de
`_LABEL_STATE`, que es justo lo que el módulo declara no querer («ningún otro
sitio de este módulo vuelve a decidir qué etiqueta significa qué estado»).

## Comprobación que la sostiene

- **La prueba del defecto, vista FALLAR antes del cambio** (ADR-001):
  `uv run pytest tests/engine/test_mirror_projection.py -k "repair_requested_y_repairing or exencion_se_deriva"`
  → `2 failed` con `etiquetas_contradictorias` en `True` para #592. Tras el
  cambio, `62 passed` en ese fichero.
- **Tres mutaciones sembradas y vistas caer**, cada una con la suite
  `tests/engine/` completa:

  | Mutación | Resultado |
  |---|---|
  | quitar la comprobación de contradicción (dos etiquetas de estados distintos dejan de darla) | `3 failed` — `test_etiquetas_de_estado_contradictorias_no_eligen_una_ganadora`, `test_completed_y_failed_safely_siguen_siendo_contradiccion`, `test_la_exencion_se_deriva_de_la_tabla_y_no_de_una_lista_a_mano` |
  | volver a `len(presentes) > 1 and presentes != _PAR` (la pareja exenta escrita a mano, sin derivar) | `2 failed` — la reproducción de #592 y la prueba exhaustiva |
  | eximir por mismo ESTADO sin mirar la fase | `1 failed` — la prueba exhaustiva, sobre `implementing` + `ci-pending` |

- **La puerta no se debilita**:
  `test_completed_y_failed_safely_siguen_siendo_contradiccion` fija el caso
  MEDIDO EN PRODUCCIÓN que cita `_ventana_contradiccion` (incidencia #353), y
  pasa igual antes y después del cambio.
- **Validaciones obligatorias** en verde: `uv run ruff format --check .`,
  `uv run ruff check .`, `uv run mypy src tests`, `uv run pytest`,
  `git diff --check`.

## Consecuencias

- Una incidencia con `sirius:repair-requested` + `sirius:repairing` —o con las
  parejas equivalentes de activación, ejecución y revisión— proyecta su estado y
  su fase de verdad. El tablero de ADR-175 deja de acusarla y el verificador
  vuelve a compararla en vez de marcarla `NO_COMPARABLE`.
- Ampliar el vocabulario ya no obliga a tocar ninguna lista de exenciones: basta
  con dar a la etiqueta nueva su fila en `_LABEL_STATE` (y en `_LABEL_PRIORITY`,
  que su propia prueba sigue exigiendo).
- La contradicción queda más estrecha a propósito: 74 de 78 parejas, en vez de
  77. Las 3 que dejan de serlo son las que decían lo mismo dos veces.
- Los comentarios que citaban `_PAR_DE_ACTIVACION_VALIDO` —`reflect.py` y el
  docstring de `MirroredWorkItem`— se actualizan para no dejar una referencia
  colgada a una constante que ya no existe. ADR-136, que también la cita, no se
  toca: es registro histórico.

## Alternativas descartadas y por qué

- **Arreglar el mensaje del tablero** para que no acuse cuando las etiquetas son
  compatibles: tapa el dato malo donde se enseña, y dejaría al verificador y a
  `authority_reversion` leyendo el mismo `(None, None, True)` de siempre.
- **Exigir que los workflows retiren `sirius:repair-requested` al aplicar
  `sirius:repairing`**: cambia el contrato de la automatización para acomodar un
  defecto de lectura, y está fuera del alcance de esta incidencia.
- **Marcar contradicción solo cuando los ESTADOS difieran**, ignorando la fase:
  la medición dice que eximiría 25 parejas más, entre ellas
  `implementing` + `ready-for-merge`. La mutación 3 lo comprueba en rojo.

## La lección

- familia: `lista-a-mano`
- sin esto se repetiría: escribir como lista de excepciones un criterio que el
  dato de al lado ya define —aquí, «qué etiquetas pueden convivir», enumerado a
  mano habiendo una tabla que dice a dónde apunta cada una—, de modo que la
  lista solo contiene lo que alguien recordó el día que la escribió y acusa de
  avería a todo lo demás.
- lo hace cumplir: `tests/engine/test_mirror_projection.py`
