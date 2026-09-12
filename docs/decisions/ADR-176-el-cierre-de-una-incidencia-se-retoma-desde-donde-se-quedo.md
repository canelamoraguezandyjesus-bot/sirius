# ADR-176 — El cierre de una incidencia se retoma desde donde se quedó

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: la fusión de la PR por el propietario

## Nota de arranque (escrita ANTES de tocar una línea de código)

### El fallo, reproducido antes de escribir esta nota

ADR-173 (fusionado hoy, `6d91482`) cierra un encargo cuya incidencia está
cerrada. Desde `ACTIVE` no hay una arista directa a `CANCELLED` en el dominio,
así que el plan son **dos pasos**: `escalate` (a `NEEDS_DECISION`) y después
`resolve_decision(continuar=False)`.

**Si la pasada se corta entre los dos, el encargo no se recupera nunca.**
Reproducido sobre `main`, aplicando solo el primer paso del plan:

```
tras la interrupcion: needs_decision
pasos del reintento: [] | divergencia: True
```

La siguiente pasada ve el motor en `NEEDS_DECISION` y la incidencia
proyectando `ACTIVE` por una etiqueta congelada, declara «no hay camino hacia
delante» y no toca nada. Y la regla 7 de ADR-173 **no entra**, porque solo
actúa cuando el plan de las etiquetas no declaró divergencia. El encargo se
queda a medio cancelar para siempre: el mismo final que ADR-173 vino a
arreglar, por otra puerta.

Que `aplicar_pasos` se corte a la mitad no es hipotético: lo dice su propio
docstring —«si un paso fallara a mitad, los anteriores ya quedaron aplicados y
registrados en el diario»— y el trabajo corre en un runner que puede acabarse,
quedarse sin tiempo o perder la red entre dos llamadas al almacén.

### 1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo OBSERVAR el fallo?

El fallo vive en el ORDEN de las comprobaciones de `reflejar_desenlace`: el
cierre llega después del plan por etiquetas y hereda su divergencia. El arreglo
va justo delante: **antes de preguntarle nada a las etiquetas, si la incidencia
está cerrada y el motor ya está en un estado con salida directa a `CANCELLED`,
se termina**.

**Sí puede observar el fallo**: el estado a medio cancelar está en el propio
`WorkItem` que la función recibe, y `espejo.cerrada` ya viaja hasta ahí. No
hace falta ninguna lectura nueva, ni recordar nada de la pasada anterior — que
es justo lo que no se puede hacer entre dos invocaciones.

### 2. ¿Qué NO va a garantizar esto?

- **No hace atómicos los dos pasos.** Siguen siendo dos sucesos en el diario y
  la pasada se puede seguir cortando entre ellos. Lo que cambia es que la
  siguiente **retoma** en vez de atascarse.
- **No resucita nada.** Una parada cuya incidencia está cerrada se termina como
  `CANCELLED`; nunca vuelve a `ACTIVE`. La regla que CODEX-001 defendió en la
  PR #530 —sin permiso escrito del propietario no se reanuda— sigue intacta,
  porque **cancelar no es reanudar**.
- **No toca las etiquetas contradictorias.** Si el espejo las declara en
  conflicto, la regla 1 sigue ganando y no se toca nada.
- **No cambia nada si la incidencia está abierta.**
- **No arregla que el motor tenga que dar dos pasos** para algo que
  conceptualmente es uno. Añadir una arista `ACTIVE -> CANCELLED` al dominio
  sería otra decisión, más ancha, y no entra aquí.

### 3. Criterio de parada (decidido ANTES de ver ningún resultado)

- **(a)** Si retomar el cierre exigiera una transición que el dominio no
  admita, **se para**: es el mismo criterio (b) de ADR-173 y por la misma
  razón.
- **(b)** Si el arreglo pudiera convertir una parada en `ACTIVE` sin permiso
  escrito, **se para y se rediseña**: eso costó cuatro rondas en la PR #530 y
  no se reabre.
- **(c)** Si alguna prueba existente de `reflect` cambia de resultado, se mira
  una por una y se dice cuál y por qué, en vez de ajustarla para que pase.
- **(d)** Ninguna prueba nueva se da por buena sin haberla visto fallar contra
  una versión rota a propósito (ADR-001 §3).

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

Lo verdaderamente imposible sería que el cierre fuera **un solo suceso**, y eso
exige una arista nueva en el dominio: fuera de alcance, y dicho.

Lo que entra hace algo casi tan fuerte y más barato: **el cierre deja de
depender de haber llegado hasta el final en una sola pasada**. Se mira el
estado en el que el motor ESTÁ, no el que se esperaba que tuviera, así que
cualquier interrupción —en este punto o en otro— se retoma en la pasada
siguiente. Un plan que hay que completar de una sentada es frágil por
construcción; uno que se recalcula desde el estado real, no.

## Contexto y problema

ADR-173 midió 21 encargos varados y los desatascó. Esta es la grieta que dejó:
el desatasco en sí podía quedarse a medias. La encontró una revisión externa el
mismo día, antes de que ocurriera en producción.

## Decisión

**El cierre se comprueba ANTES que las etiquetas, y se retoma desde el estado
real.** Si la incidencia está cerrada, sus etiquetas no se contradicen, y el
`WorkItem` ya está en un estado con salida directa a `CANCELLED`
—`NEEDS_DECISION`, `FAILED_SAFELY` o `PLANNED`—, el plan es esa salida y nada
más. Solo si no se da ese caso se calcula el plan por etiquetas como siempre, y
se le añade el cierre al final como hizo ADR-173.

Ni un puerto nuevo ni una arista nueva: son las mismas transiciones que ADR-173
ya usaba, consultadas antes.

## Comprobación que la sostiene

Sobre el caso real reproducido arriba —el encargo a medio cancelar—, el
reintento pasa de `[]` con divergencia a `[work_item_decision_resolved]`, y el
encargo acaba en `cancelled`.

**Cuatro mutaciones sembradas y vistas caer**, y una prueba existente que
cambia de resultado a propósito, explicada abajo.

## Consecuencias

- Un encargo a medio cancelar se termina en la pasada siguiente, sin que el
  propietario tenga que dar ninguna orden.
- **Una prueba de ADR-173 cambia de resultado a propósito:**
  `test_el_cierre_no_pisa_una_divergencia_hacia_atras` fijaba que una parada
  cuya incidencia está cerrada se conservara cuando las etiquetas proyectan
  `ACTIVE` sin permiso. Esa regla es la que dejaba el cierre a medias
  atascado. Se reescribe para fijar la propiedad más afilada, que es la que de
  verdad importaba: **el cierre nunca reanuda una parada, pero sí puede
  terminarla.** La mitad que protegía —que un `WorkItem` parado no vuelva a
  `ACTIVE` sin permiso escrito— se conserva y se comprueba explícitamente.
- Una incidencia cerrada por error cancela su encargo. Ya era así desde
  ADR-173; el diario conserva todo y el encargo se puede volver a dar.

## Alternativas descartadas y por qué

1. **Hacer atómicos los dos pasos.** Exige una transición `ACTIVE -> CANCELLED`
   en el dominio, que es una decisión de modelo mucho más ancha que este
   defecto.
2. **Reintentar el plan entero dentro de la misma pasada.** No arregla nada: si
   la pasada muere, muere con su reintento.
3. **Dejarlo y confiar en que la ventana es estrecha.** Es exactamente el
   razonamiento que produjo los 21 encargos varados: una ventana estrecha
   recorrida cientos de veces se acaba atravesando.

## La lección

- familia: `plan-que-hay-que-terminar-de-una-sentada`
- sin esto se repetiría: escribir un plan de varios pasos contra un almacén que los aplica uno a uno, y comprobar la precondición del primero en vez del estado real en que el motor está, de modo que una interrupción a la mitad deja el trabajo atascado para siempre.
- lo hace cumplir: `tests/engine/test_reflect.py`
