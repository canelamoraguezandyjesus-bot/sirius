# ADR-181 — La contradicción de etiquetas se decide por lo que proyectan, no por cuántas son

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: la fusión de la PR por el propietario

> **Nació como ADR-177 y se renumeró a 181.** El 12-09-2026 hubo **cuatro**
> ADR-177 distintos, cada uno en su rama abierta y ninguno en `main`: la
> ampliación por categoría (PR #590, la más antigua, conserva el 177), la
> autoridad por clase (PR #591, renumerada a 178), la guarda de piezas sin
> llamante (PR #593, renumerada a 179) y este, nacido a las 22:54, después de
> que se escribieran los dos anteriores —por eso ADR-179 y ADR-180 dicen
> «tres» y no se corrigen: son evidencia fechada—.
> `scripts/siguiente_adr.py` consultaba las ramas **del clon**, así que una
> rama que no se ha traído no existía para él, y `test_registro_de_decisiones.py`
> mira el árbol local: las cuatro ramas pasaban por separado y el rojo habría
> aparecido en `main` al fusionar la segunda. Es el modo exacto en que nacieron
> los dos ADR-016 que ADR-032 conserva.
>
> **Esta es la última renumeración hecha bajo el régimen viejo.** ADR-180
> (PR #595, ya en `main`) hace que el guion traiga las cabezas del remoto antes
> de contar: corrido sobre este árbol consulta 309 ramas y devuelve 181, que es
> justo el número que esta rama toma. La familia que obligó a las tres
> renumeraciones del día la cierra ahora una comprobación, no la memoria de
> nadie.

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
`sirius:repair-requested` y `sirius:repairing` a la vez: la primera es el
encargo y la segunda el acuse. Las dos conviven durante la VENTANA que va desde
que se aplica la etiqueta de encargo hasta que el run que la consume la retira
-el paso «Consumir el evento y marcar en curso» de
`.github/workflows/repair-sirius-work.yml:597-617` añade `sirius:repairing` y
retira `sirius:repair-requested` ANTES de arrancar al corrector, y
`review-sirius-work.yml:229` e `implement-sirius-work.yml:267` hacen el mismo
relevo con sus parejas-. La ventana es corta cuando el relevo ocurre, y queda
abierta de forma indefinida si ese run muere antes de consumir el evento, que
es justamente el caso que la red de reconciliación existe para cubrir. Las dos
etiquetas son `(ACTIVE, REPARAR)` en `_LABEL_STATE`. La proyección devolvía
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
- **No alcanza a la red de reconciliación.** El criterio por cardinalidad con
  su exención escrita a mano sigue vivo e intacto en
  `scripts/automation/sirius_reconcile.sh:250-269`: cuenta TODAS las etiquetas
  `sirius:*` de la incidencia (línea 184) y solo exime literalmente
  `"sirius:implement-requested sirius:planned "`. Así que las tres parejas que
  este cambio exime en el espejo -activación, revisión y reparación- siguen
  produciendo ahí `report CONTRADICCION "#N: varias etiquetas sirius
  simultáneas (...)"`, y el `continue` de la línea 268 sigue saltándose el
  resto de comprobaciones de esa pasada para esa incidencia -incluido el Caso B
  de `ci-pending`-. Arreglarlo está **fuera del alcance de #594**, que autoriza
  el cambio en `src/sirius_engine/mirror_projection.py` y sus pruebas: queda
  registrado aquí como pendiente y necesita su propio encargo.
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
66 parejas del vocabulario comprobando el reparto contra la tabla, sin
escribirlo, así que cualquier vuelta a una lista a mano sale en rojo.

## La medición (hecha ANTES de decidir)

`uv run python` sobre `_LABEL_STATE`, las 12 etiquetas del vocabulario y sus
66 parejas (la medición inicial contaba 13 etiquetas y 78 parejas porque
`_LABEL_STATE` incluía `sirius:audit-requested`, una etiqueta que el bootstrap
NO crea; ver «La etiqueta retirada» más abajo):

| Destino `(estado, fase)` | Etiquetas que apuntan ahí |
|---|---|
| `(PLANNED, PREPARAR)` | `sirius:planned`, `sirius:implement-requested` |
| `(ACTIVE, EJECUTAR)` | `sirius:implementing` |
| `(ACTIVE, COMPROBAR)` | `sirius:ci-pending` |
| `(ACTIVE, REVISAR)` | `sirius:review-requested`, `sirius:reviewing` |
| `(ACTIVE, REPARAR)` | `sirius:repair-requested`, `sirius:repairing` |
| `(ACTIVE, ENTREGAR)` | `sirius:ready-for-merge` |
| `(NEEDS_DECISION, None)` | `sirius:blocked-decision` |
| `(FAILED_SAFELY, None)` | `sirius:failed-safely` |
| `(DELIVERED, ENTREGAR)` | `sirius:completed` |

- **3 parejas de 66 apuntan al mismo `(estado, fase)`**: activación
  (`planned` + `implement-requested`), revisión (`review-requested` +
  `reviewing`) y reparación (`repair-requested` + `repairing`).
- **63 apuntan a estado o fase distintos**, y siguen siendo contradicción. Entre
  ellas las dos que la puerta protege: `completed` + `failed-safely` (estados
  distintos) y `completed` + `ready-for-merge` (misma fase `ENTREGAR`, estados
  `DELIVERED` y `ACTIVE`).
- **19 parejas comparten estado pero no fase** —todas las combinaciones de
  `ACTIVE` entre fases distintas—. Son el motivo por el que el criterio compara
  el par completo y no solo el estado: eximirlas convertiría un
  `implementing` + `ready-for-merge` en una entrega silenciosa.
- La única pareja que `_PAR_DE_ACTIVACION_VALIDO` eximía a mano es exactamente
  una de las cuatro que el criterio derivado exime solo. **Queda innecesaria**,
  y el criterio de parada decía que en ese caso se retira: se retira.

Ninguna pareja que hoy dé contradicción legítima apunta al mismo destino, así
que no se activó la condición de escalar.

## La etiqueta retirada (`sirius:audit-requested`)

Al medir el vocabulario apareció una cuarta pareja compatible que **no existe**:
`sirius:implementing` + `sirius:audit-requested`. Esa segunda etiqueta está
retirada: `.github/workflows/bootstrap-sirius-automation-labels.yml:55-62` dice
expresamente que fue un error -el prefijo `sirius:` la metía en la máquina de
estados- y crea en su lugar `auditoria:solicitada`, FUERA del espacio
`sirius:*`, como fijan ADR-016 y
`docs/implementation/AUTOMATION_OPERATING_CONTRACT.md:784-796`. El bootstrap no
la crea; solo la NOMBRA en ese comentario.

La prueba que ata el vocabulario interpretado al que de verdad se crea no lo
detectaba porque leía el workflow con `re.findall(r"sirius:[a-z-]+", ...)` sobre
el fichero entero, y ese patrón recogía el nombre citado en el comentario. Con
esa lectura, una etiqueta que el workflow declara NO crear contaba como creada.

Se corrige donde nace: la lectura pasa a tomar solo los argumentos de
`ensure_label` -la única línea que crea una etiqueta- y `sirius:audit-requested`
sale de `_LABEL_STATE` y de `_LABEL_PRIORITY`. A partir de ahí es una etiqueta
no reconocida más, como cualquier `sirius:` que nadie haya definido, y el espejo
la ignora en vez de derivar de ella una compatibilidad: la ejecución deja de
tener pareja y el reparto queda en 3 exentas de 66. No se añade ninguna lista de
etiquetas retiradas —sería exactamente la `lista-a-mano` que este ADR retira—:
el vocabulario es el que el bootstrap crea, y la prueba lo comprueba leyéndolo.

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
- **Validaciones obligatorias**: una sola invocación de
  `pwsh -File scripts/check.ps1` sobre el árbol final de la rama; su terna de
  `pytest` y su código de salida quedan anclados al head en el cuerpo de la PR.

### Ronda 2 de corrección (la etiqueta retirada y la prosa)

- **La lectura del bootstrap, vista FALLAR con la mutación** que la devuelve a
  `re.findall(r"sirius:[a-z-]+", texto)` sobre el fichero entero:
  `test_el_vocabulario_interpretado_es_el_que_de_verdad_se_crea` cae con
  `AssertionError: solo se crean: ['sirius:audit-requested']; solo se
  interpretan: []`.
- **La salida de la etiqueta del vocabulario, vista FALLAR con la mutación**
  que devuelve `sirius:audit-requested` a `_LABEL_STATE` y `_LABEL_PRIORITY`:
  `test_la_exencion_se_deriva_de_la_tabla_y_no_de_una_lista_a_mano` cae con
  `AssertionError: el vocabulario cambió de tamaño: revisa la medición del ADR`
  (`assert 78 == 66`), y con ella
  `test_el_vocabulario_interpretado_es_el_que_de_verdad_se_crea` y
  `test_una_etiqueta_solo_citada_en_un_comentario_no_cuenta_como_creada`.
- Con las dos correcciones puestas, `uv run pytest
  tests/engine/test_mirror_projection.py` da `63 passed` (eran 62 antes de
  añadir la prueba de la etiqueta citada solo en un comentario).

## Consecuencias

- Una incidencia con `sirius:repair-requested` + `sirius:repairing` —o con las
  parejas equivalentes de activación, ejecución y revisión— proyecta su estado y
  su fase de verdad. El tablero de ADR-175 deja de acusarla y el verificador
  vuelve a compararla en vez de marcarla `NO_COMPARABLE`.
- Ampliar el vocabulario ya no obliga a tocar ninguna lista de exenciones: basta
  con dar a la etiqueta nueva su fila en `_LABEL_STATE` (y en `_LABEL_PRIORITY`,
  que su propia prueba sigue exigiendo).
- La contradicción queda más estrecha a propósito: 63 de 66 parejas, en vez de
  65. Las 2 que dejan de serlo -revisión y reparación- son las que decían lo
  mismo dos veces; la de activación ya estaba exenta a mano.
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
- sin esto se repetiría: escribir como lista de excepciones un criterio que el dato de al lado ya define —aquí «qué etiquetas pueden convivir», enumerado a mano habiendo una tabla que dice a dónde apunta cada una—, de modo que la lista solo contiene lo que alguien recordó el día que la escribió y acusa de avería a todo lo demás.
- lo hace cumplir: `tests/engine/test_mirror_projection.py`
