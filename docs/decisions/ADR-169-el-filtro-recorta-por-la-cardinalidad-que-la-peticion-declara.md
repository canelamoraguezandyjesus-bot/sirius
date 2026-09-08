# ADR-169 — El filtro recorta por la cardinalidad que la peticion declara

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de esta PR por el propietario.
- Esta ficha es además la **nota de arranque** de la rama (ADR-001, skill
  `disciplina-evidencia`): las cuatro preguntas, la línea base y el criterio
  de parada de abajo se escribieron y se publicaron **antes del primer commit
  de código** (commit de esta ficha sola, anterior a cualquier cambio en
  `src/`).

## Contexto y problema

**Palanca 3 de ADR-148**, incidencia #579 (`WI-20260908-P3`), la última de
las tres. Va detrás de P1 (ADR-164), H2 (ADR-166) y H1 (ADR-168), las tres
ya en `main` (`ce94bdf`). **No depende de la palanca 2**, cerrada el 08-09
con resultado medido y negativo.

El objetivo declarado: que el filtro de relevancia use la cardinalidad que la
petición ya trae — con `EXACTA n` recorta a `n`, con `EXHAUSTIVA` poda por
relevancia sin número fijo, con `ACOTADA` respeta el límite declarado.

### Lo que el árbol dice, comprobado línea a línea

1. **El filtro no recibe la petición.** El contrato del puerto es
   `filter_candidates(self, query_text, candidates)`
   (`src/sirius/ports/relevance_filter.py:33-35`): ni cardinalidad, ni
   límite, ni objetivos. Así que esto **no** es «que use un dato que ya
   tiene»: hay que hacérselo llegar, y eso toca el puerto y sus dos llamadas
   (`src/sirius/application/context.py:372` y `:399`).
2. **El motor sí honra la cardinalidad, pero por otra puerta.**
   `_suficiente` (`src/sirius/domain/staged_engine.py:240-250`) usa
   `peticion.objetivos` para `EXACTA` y `peticion.limite_objetivo` para
   `ACOTADA`, pero **solo como condición de insuficiencia entre etapas**:
   decide si hace falta seguir expandiendo, nunca recorta lo que una etapa ya
   aportó. El único recorte del motor es `G12`
   (`src/sirius/domain/staged_engine_gates.py:336-341`), y corta por
   `peticion.limite_duro`, no por `objetivos`.
3. **Por eso `B04-CA-35` es `EXACTA` y sale con 16 de más.** Su
   `peticion_p2.limite` es `null`, así que `limite_duro` degrada al «límite
   que no ata» (97, el tamaño del canon:
   `tests/acceptance/staged_engine_case_translation.py:129-137`) y `G12` no
   quita nada — `omitidos_por_limite` queda vacío. No es que un recorte
   existente no se aplique: es que **no existe ningún recorte por
   `objetivos`** en ninguna etapa. Ésa es la respuesta a la pregunta que la
   incidencia dejaba abierta.

### La línea base, medida al empezar y no heredada

**Entrada de la palanca** — `main` = `ce94bdf`, hoy 08-09-2026:

```
$ uv run python scripts/diagnosticar_busqueda_del_banco.py --peticion
[ejes=no peticion=real] SIN FILTRO: 17/47 exactos; 162 de mas; 78/81 hallados; omisiones criticas=0
extras: total=162; media=3.4; casos con 0 extras=19;
peores=[('B04-CA-17', 34, 0), ('B04-CA-28', 20, 0), ('B04-CA-35', 16, 0),
        ('B04-CA-34', 13, 10), ('B04-CA-03', 12, 0), ('B04-CA-44', 8, 5)]
```

Coincide con lo que la incidencia declaraba como referencia. **Es la entrada,
no el resultado**: ese guion corre SIN filtro, y esta palanca ES el filtro.

**Vía completa** (con Ollama real, `scripts/medir_banco_con_ollama_real.py`),
la cifra publicada que la incidencia cita: `29/47; 50; 0; 63/81`. No se
vuelve a medir aquí porque **no hay Ollama en CI**: la cierra el propietario
en su máquina, con el comando y la predicción de más abajo.

Las dos mediciones **no se mezclan**: poblaciones distintas (una es la etapa
de búsqueda sin filtro, la otra el camino entero con modelo). Cada cifra de
esta ficha lleva al lado de qué medición sale.

### El dato que el árbol desmiente, y que cambia el alcance de lo medible

La incidencia habla de «`EXACTA n`» como si la petición trajera `n`. **En
producción no lo trae, y el propio árbol lo declara**: ADR-164 fija
`objetivos = 1` para toda petición interpretada, y escribe por qué
(`src/sirius/application/interpret_query_request.py:182-189`):

> `objetivos` se queda en 1 porque la cuota de `EXACTA` que el banco usa
> (`max(1, len(caso["resultado_esperado"]))`) es **adjudicación** —el número
> de elementos que alguien ya decidió que el caso espera—, y producción no la
> tiene ni puede inventarla.

`scripts/medir_interprete_de_peticion.py:48-50` lo repite: `objetivos` no se
compara campo a campo «que en el banco es adjudicación». Y el corpus lo
confirma: las 29 `peticion_p2` con `cardinalidad: EXACTA` traen
`limite: null` y ningún número propio.

De ahí salen dos consecuencias que gobiernan toda la evidencia de esta ficha:

- **La `n` de `EXACTA` en producción es 1.** El recorte es «conserva la más
  relevante», que es exactamente lo que `_suficiente` ya considera
  suficiente. No es una `n` inventada aquí: es la única que la petición trae.
- **La medición de banco con `--peticion` NO puede puntuar esta palanca.**
  Ahí `objetivos = max(1, len(resultado_esperado))`, o sea el oráculo: cortar
  por él sería decirle al filtro cuántos guardar y publicar el resultado como
  acierto. Cualquier cifra que salga de ese camino se publica **con esa
  condición al lado y como cota superior**, nunca como acierto.

## Criterio de parada (escrito ANTES de decidir y ANTES de medir nada del cambio)

- **La vía completa no se mueve: `29/47; 50; 0; 63/81` sigue igual.** Es una
  predicción, no una excusa: en esa vía el intérprete se construye sin
  clasificador y toda petición sale `EXHAUSTIVA`
  (`INTENCION_ORDINARIA`, `src/sirius/application/interpret_query_request.py:102-108`),
  así que el cupo es `None` en las 47 y el recorte no puede dispararse. **Si
  alguna de las cuatro columnas cambia, esta palanca no es la causa y hay que
  explicar caso a caso qué lo fue.**
- **Como `50 > 20`, la tercera condición de aceptación de la incidencia se
  activa por construcción**: se registra la cifra y **se para para decisión
  del propietario** sobre el modelo. Esta palanca no cierra el ruido de
  producción hoy, y decirlo antes de medir es parte del criterio.
- **La entrada tampoco se mueve**: `17/47; 162; 78/81; 0` con
  `--peticion`. Ese guion corre sin filtro; si cambia, el cambio se coló
  fuera del filtro y hay que explicarlo.
- **Cota superior del recorte, con su condición**: se mide `--peticion
  --cupo`, que aplica el recorte real sobre un modelo que no descarta nada.
  Predicción: **las «de más» bajan de 162 a menos de 60** y **los hallados no
  bajan de 74/81** (a lo sumo se pierden los 4 elementos de los tres casos
  `EXACTA` que esperan más de uno —`B04-CA-19` con 3, `B04-CA-23` y
  `B04-CA-43` con 2— y el undécimo de `B04-CA-26`, `ACOTADA n=10`).
  **Críticas perdidas: 0.** Si baja de 74/81 o aparece una crítica perdida,
  se para y se registra.
- **Ninguna prueba se relaja, se salta ni se reescribe para conseguir
  verde.** Si una cota del banco tuviera que bajar, se para.
- **Se para** si hace falta decidir algo de producto, esquema o corpus: en
  particular, **cambiar `objetivos` para que producción traiga una `n` de
  verdad es decisión del propietario y no se toma aquí**.

## Las cuatro preguntas de la nota de arranque

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en el
   **contrato del puerto**: el filtro no puede usar la cardinalidad porque
   nadie se la pasa, y ninguna etapa del motor recorta por `objetivos` (punto
   2 y 3 del contexto). El arreglo va en tres sitios y en ninguno más: la
   regla pura que traduce cardinalidad a cupo (`sirius.domain.relevance`), el
   contrato del puerto que transporta ese cupo, y el adaptador que lo aplica
   **solo cuando el modelo contestó**. No puede ir en `ContextBuilder`: allí
   no se distingue un veredicto del modelo de una rendición, y recortar una
   rendición sería recortar por accidente justo lo que la incidencia prohíbe.
2. **¿Qué NO garantiza?** No baja el ruido de producción hoy: con la puerta
   `category_matching_enabled` cerrada no hay filtro, y con ella abierta toda
   petición sale `EXHAUSTIVA`, así que el cupo es `None`. No abre la puerta.
   No inventa una `n` para `EXACTA` (producción trae 1, por ADR-164). No
   toca el corpus, ni `resultado_esperado`, ni ninguna adjudicación. No
   reordena nada: el orden sigue siendo de `sirius.domain.relevance`.
3. **Criterio de parada:** el de arriba, publicado antes de medir.
4. **¿Qué haría el fallo imposible en vez de improbable?** Que el recorte no
   pudiera aplicarse sobre una rendición del modelo. Se consigue por
   construcción: el `return candidates` del `except` del adaptador es el
   **mismo objeto** que entró y no pasa por el recorte, que vive solo en el
   camino de éxito; una prueba lo fija por identidad (`is candidates`), que
   es la misma señal por la que `medir_banco_con_ollama_real.py` cuenta
   rendiciones. Y que ninguna poda pierda una crítica: lo fijan el candado de
   puerta cerrada y RF-25/RF-26 con puerta abierta, con prueba propia.

## Opciones consideradas

1. **Recortar en `ContextBuilder`, después del filtro.** Descartada: no
   distingue veredicto de rendición (recortaría un fallo abierto) y actuaría
   después del rescate RF-25/RF-26, de modo que podría tirar una crítica que
   el rescate acababa de recuperar.
2. **Pasar la `Peticion` entera al puerto.** Descartada: el puerto es
   deliberadamente estrecho (un método, un `Protocol`) y arrastrar el
   vocabulario del motor por etapas hasta el adaptador de red le da acceso a
   permiso, propósito y ámbito que no necesita.
3. **Pasar un `cupo: int | None` ya derivado.** Elegida. Un solo dato, con un
   significado explícito —«cuántas conservar como mucho; `None` = sin número,
   poda por relevancia»— derivado por una función pura del dominio que sí
   conoce la cardinalidad.

## Decisión

*(se completa con la implementación)*

## Comprobación que la sostiene

*(se completa tras medir)*

## Consecuencias

*(se completa tras medir)*

## Alternativas descartadas y por qué

*(se completa con la implementación)*
