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

**El filtro recibe un `cupo` y lo aplica sobre el veredicto del modelo, nunca
sobre una rendición suya.** Tres piezas, y ninguna más:

1. **`sirius.domain.relevance.cupo_del_filtro(peticion) -> int | None`**: la
   regla pura. `EXACTA` → `peticion.objetivos`; `ACOTADA` →
   `peticion.limite_objetivo`; `EXHAUSTIVA` → `None`. Es la MISMA
   correspondencia de campos que `_suficiente`
   (`src/sirius/domain/staged_engine.py`) ya usa entre etapas, para que el
   motor y el filtro no cuenten dos cosas distintas. Un cupo no positivo
   degrada a `None`: un cero no es una cuota, y obedecerlo vaciaría el
   resultado por un dato mal declarado.
2. **El contrato del puerto lo transporta**:
   `filter_candidates(query_text, candidates, *, cupo: int | None = None)`
   (`src/sirius/ports/relevance_filter.py`). Un solo dato ya derivado, no la
   `Peticion` entera: el adaptador de red no necesita saber de permiso,
   propósito ni ámbito. El valor por defecto `None` mantiene el
   comportamiento exacto de todo llamador anterior.
   `RankRelevantKnowledgeUseCase.rank_con_cupo` devuelve candidatas y cupo de
   una sola interrogación —`rank()` tiraba la petición con la que las había
   pedido—, y `ContextBuilder._apply_relevance_filter` lo entrega en sus dos
   llamadas al puerto.
3. **`recortar_al_cupo`, aplicado dentro del adaptador y solo en su camino de
   éxito** (`src/sirius/adapters/ollama_relevance_filter.py`). Es un
   **prefijo** del orden que §6.2 ya fijó, así que el filtro sigue sin
   reordenar. Y el `return candidates` del `except` —el mismo objeto que
   entró— no pasa por el recorte: **un fallo del modelo no puede acabar
   recortando por accidente**, que es la garantía que la incidencia pedía
   explicar. Esa identidad de objeto es además la señal por la que
   `scripts/medir_banco_con_ollama_real.py` cuenta rendiciones; si el recorte
   pasara por ahí, esa cuenta se volvería un cero falso.

El candado de puerta cerrada y el rescate RF-25/RF-26 no se tocan: siguen
decidiendo **después** del filtro, así que ninguna poda por cupo puede perder
una crítica.

Para poder medir el recorte sin Ollama, `scripts/diagnosticar_busqueda_del_banco.py`
gana la bandera **`--cupo`**, que aplica `recortar_al_cupo` sobre un doble que
no descarta nada. Su cifra es una **cota superior**, no un acierto: ver la
advertencia del guion y la sección siguiente.

## Comprobación que la sostiene

### El recuento del banco, antes y después

**Instrumento: `scripts/diagnosticar_busqueda_del_banco.py`. No se mezcla con
la vía completa**, que mide otra población (camino entero con modelo).

| Configuración | Exactas | De más | Hallados | Críticas perdidas |
|---|---|---|---|---|
| `--peticion` (antes = entrada de la palanca) | 17/47 | 162 | 78/81 | 0 |
| `--peticion` (después, sin `--cupo`) | 17/47 | 162 | 78/81 | 0 |
| `--peticion --cupo` (cota superior del recorte) | **18/47** | **125** | **75/81** | **0** |

La segunda fila es el candado: el cambio **no mueve la etapa de búsqueda**.
La tercera es lo que el recorte puede quitar por sí solo.

**La condición que viaja con la tercera fila, y sin la cual no se publica:**
la `n` de `EXACTA` que el banco pone en la petición es
`max(1, len(caso["resultado_esperado"]))`
(`tests/acceptance/staged_engine_case_translation.py`), o sea **adjudicación**
—el oráculo—. Producción no la tiene ni puede inventarla: ADR-164 la deja fija
en 1 y escribe por qué. Así que ese `125` **no es el acierto de la palanca**:
es cuánto quitaría el recorte si alguien acertara la `n`.

### Contra-medición que aísla el arnés

La pregunta que hay que poder responder es si el `−37` sale del recorte o del
andamiaje (la bandera, el doble, el guion de recuento). Se aísla midiendo
`--cupo` **sin** `--peticion`: entonces toda petición es la uniforme
(`EXHAUSTIVA`), el cupo es `None` en las 47 y el recorte no puede actuar.

```
$ uv run python scripts/diagnosticar_busqueda_del_banco.py
[ejes=no peticion=fija] SIN FILTRO: 0/47 exactos; 487 de mas; 72/81 hallados; omisiones criticas=0
$ uv run python scripts/diagnosticar_busqueda_del_banco.py --cupo
[ejes=no peticion=fija cupo=si] SOLO EL RECORTE POR CUPO (modelo que no descarta): 0/47 exactos; 487 de mas; 72/81 hallados; omisiones criticas=0
```

**Idénticas.** El andamiaje por sí solo no mueve una sola cifra: la diferencia
entera viene de las cardinalidades que la petición de cada caso declara.

Sobre la regla de la deuda 21 —«si la contra-medición sustituye un dato del
arnés, lo sustituye por ítem y no por una constante»—: aquí el dato sustituido
es **el modelo**, y se sustituye por la constante «no descarta nada». Se
declara por qué basta: la constante es justamente lo que aísla el recorte del
juicio del modelo. Un doble que descartara por ítem estaría midiendo un modelo
inventado, y el número resultante no sería ni cota ni medida de nada.

### La predicción falló, y así queda registrada

La nota de arranque predijo «las de más bajan de 162 a **menos de 60**». Salió
**125**. La predicción **no se ajusta después de verla**; se registra el fallo
y su causa, que la propia medición muestra:

- **El ruido gordo está donde el cupo es `None` por diseño.** Repartiendo las
  «de más» por cardinalidad, antes y después:

  | Cardinalidad | Casos | De más antes | De más después |
  |---|---|---|---|
  | `EXACTA` | 29 | 48 | **18** |
  | `ACOTADA` | 5 | 29 | **22** |
  | `EXHAUSTIVA` | 13 | 85 | **85** |
  | total | 47 | 162 | **125** |

  Las 85 de `EXHAUSTIVA` no se mueven **ni una**, que es exactamente lo que el
  diseño dice que tiene que pasar —ahí el cupo es `None`— y de paso una
  comprobación de consistencia interna del cambio. Yo predije sobre el total
  sin descontarlas.
- **Los diez casos `EXACTA` que no esperan nada siguen entregando uno.**
  `objetivos = max(1, …)` nunca es cero, así que ahí el recorte deja 1 de más
  en vez de 0. `B04-CA-35` es el caso extremo y la mayor ganancia suelta: de
  **16 de más a 1**.

Las otras tres predicciones se cumplieron: hallados `75/81` (predije no bajar
de 74), críticas perdidas `0`, y las exactas **suben** de 17 a 18.

### Las tres ocurrencias que el recorte pierde, una a una

`78/81 → 75/81`. No se resumen: la tercera es la lectura importante de toda
esta ficha. Entre paréntesis, el conjunto final antes → después, con sus «de
más»:

- **`B04-CA-43`** (`EXACTA`, `n=2`, espera `MEM-023` y `MEM-024`): 3 (1 de
  más) → 2 (1 de más). Conserva las dos que el cupo permite, pero una de las
  dos no es la esperada: pierde `MEM-024`.
- **`B04-CA-34`** (`ACOTADA n=10`, espera 10): 23 (13 de más) → 16 (7 de
  más). Pierde `MEM-914`. **Y el resultado final tiene 16, no 10**: el cupo
  acota el veredicto del filtro, y el candado/rescate posterior devuelve
  candidatos protegidos por encima de él. No es un fallo del recorte, es la
  garantía que lo envuelve — la misma por la que no puede perder una crítica.
- **`B04-CA-05`** (`EXACTA`, `n=1`, espera `DEC-002`): 2 (1 de más) → 1 (1 de
  más). Conserva **una que no es la esperada**. Ésta es la lectura que hay que
  llevarse: **un cupo sobre un modelo que no descarta es ciego** —conserva la
  primera del orden, acierte o no—. El cupo es un TOPE sobre el juicio del
  modelo, nunca un sustituto suyo; con un modelo que sí discrimina, las
  supervivientes son sus elegidas y no las primeras por recencia. Que la cota
  superior pierda tres es, por eso, una cota de la ceguera del doble tanto
  como del recorte.

Críticas perdidas: **0** en las cuatro configuraciones, y fijadas con prueba
(`test_el_recorte_por_cupo_nunca_pierde_una_critica`), no solo medidas.

### La medición con Ollama real: comando y predicción, escrita ANTES

No hay Ollama en CI. **La cierra el propietario**, en su máquina:

```
uv run python scripts/medir_banco_con_ollama_real.py
```

**Predicción, escrita antes de ejecutarla** (y antes de medir nada del
cambio, en la nota de arranque de arriba): **las cuatro cifras no se mueven —
`29/47; 50; 0; 63/81`**. No es una excusa, es la consecuencia comprobable del
árbol: en esa vía el intérprete se construye sin clasificador y toda petición
sale `EXHAUSTIVA` (`INTENCION_ORDINARIA`), así que el cupo es `None` en las 47
y el recorte no puede dispararse. Está fijado además por prueba determinista
(`test_rank_con_cupo_no_declara_cupo_con_la_peticion_uniforme`). **Si alguna
de las cuatro columnas cambia, esta palanca no es la causa y hay que explicar
caso a caso qué lo fue.**

Y por tanto, **la tercera condición de aceptación de la incidencia se activa
por construcción**: `50 > 20` de más. Se registra la cifra y **se para para
decisión del propietario** sobre qué modelo se adopta —el coste de un modelo
mayor es suyo—, con `--modelo` del mismo guion:

```
uv run python scripts/medir_banco_con_ollama_real.py --modelo <modelo mayor>
```

Esta palanca **no cierra el ruido de producción hoy**, y no podía: con la
puerta `category_matching_enabled` cerrada no hay filtro, y abierta toda
petición es `EXHAUSTIVA`. Lo que deja hecho es el mecanismo, medido y acotado,
para el día en que la petición traiga una cardinalidad de verdad.

### Pruebas vistas fallar (mutación transcrita)

Ocho mutaciones, cada una revertida después. Ninguna prueba nueva pasa con el
código de antes:

| Mutación | Qué se rompe | Rojo |
|---|---|---|
| M1 `recortar_al_cupo` devuelve `tuple(kept)` sin cortar | el recorte entero | 4 pruebas |
| M2 `cupo_del_filtro` deja caer la rama `EXHAUSTIVA` | «sin número fijo» | 3 |
| M3 `ACOTADA` usa `objetivos` en vez de `limite_objetivo` | el límite declarado | 3 |
| M4 sin la guarda del cupo no positivo (`return cupo`) | el cero que vaciaría | 1 (`test_cupo_del_filtro_no_devuelve_un_cupo_no_positivo`) |
| M5 `recortar_al_cupo` toma el sufijo (`[-cupo:]`) | el orden de §6.2 | 3 |
| M6 el adaptador recorta también la rendición del `except` | el fallo abierto | 1 (`test_el_cupo_no_recorta_cuando_el_modelo_falla_y_el_filtro_se_rinde`) |
| M7 el adaptador ignora el cupo (contrato anterior) | el cableado del puerto | 2 |
| M8 `ContextBuilder` no entrega el cupo al puerto | el cableado del llamador | 2 |

### La cota que se mueve, y en qué dirección

**Ninguna.** Ni una cota del banco cambia, porque ninguna cifra del banco
cambia: la vía completa y el arnés del motor portado siguen midiendo lo mismo
(el cupo es `None` en las 47 por la política uniforme). **Ninguna prueba se ha
relajado, saltado ni reescrito para conseguir verde.**

### Validación obligatoria

**Cadena completa como UNA SOLA invocación** (ADR-145, ADR-153), con
`pwsh -File scripts/check.ps1` y su código de salida capturado (ADR-154),
anclada al árbol de **`da6fea3`**:

```
5251 passed, 17 skipped, 2 xfailed in 523.33s (0:08:43)
EXIT_CODE_CHECK=0
```

De esa invocación se transcribe la cola capturada —la terna de `pytest` y el
código de salida—; el código `0` solo sale si `ruff format --check`, `ruff
check` y `mypy src tests` pasaron antes, porque el guion corta en el primero
que falle (ADR-153). Sube de `5232` a `5251` pruebas: las **diecinueve** que
esta ficha añade. Ninguna cota se ha movido y ninguna prueba se ha relajado.

La quinta validación se ejecuta **sobre el rango de la rama y no sin
argumentos** (CODEX-001, señalado en la revisión de ADR-168): `git diff
--check` sin revisiones compara el árbol de trabajo con el índice y sale `0`
aunque el rango ya confirmado traiga errores de espacios, así que no
demostraría nada sobre este cambio.

```
$ git diff --check ce94bdf da6fea3
EXIT_DIFF_CHECK=0
$ git diff --check ce94bdf
EXIT_DIFF_CHECK_ARBOL=0
```

Sin salida y con código `0` las dos: el rango entero de la rama —desde su base
en `main` (`ce94bdf`) hasta el árbol que midió la cadena— está limpio, y el
árbol de trabajo que confirma esta sección también.

Lo único posterior a `da6fea3` es **esta sección de la ficha** y el cuerpo de
la PR: documentales, sin tocar código ni pruebas, y existen porque la sección
tiene que anclarse al árbol que la cadena midió. Si una corrección posterior
toca código o pruebas, la cadena se vuelve a ejecutar entera y esta sección se
re-ancla al árbol nuevo, sin conservar la terna del anterior (ADR-154).

## Consecuencias

- **El filtro puede usar la cardinalidad, y en producción hoy no la usa.** Con
  `category_matching_enabled` cerrada no hay filtro; abierta, toda petición es
  `EXHAUSTIVA` y el cupo es `None`. Ninguna cifra de la vía completa se mueve,
  y eso está predicho y fijado con prueba, no descubierto después.
- **La cota superior del recorte queda medida: `162 → 125` de más**, con
  `78/81 → 75/81` hallados y `0` críticas perdidas, y con la condición del
  oráculo escrita al lado. El objetivo del propietario sigue siendo `0` de
  más; esta palanca no lo alcanza y las tres palancas de ADR-148 quedan
  cerradas sin alcanzarlo.
- **Queda una decisión del propietario, y esta ficha no la toma**: `50 > 20`
  de más en la vía completa activa la tercera condición de aceptación de la
  incidencia #579 — medir un modelo mayor y decidir cuál se adopta. El coste
  es suyo.
- **Y queda una pregunta de esquema, también suya**: que la petición traiga
  una `n` de verdad para `EXACTA` en vez de la constante 1. Hoy la `n` del
  banco es adjudicación y ADR-164 decidió, con razón, no inventarla. Mientras
  siga siendo 1, `EXACTA` significa «conserva la más relevante», que es
  agresivo para una pregunta que espera dos.
- El contrato del puerto crece en un parámetro con valor por defecto, así que
  ninguna implementación ni ningún llamador anterior cambia de comportamiento.

## Alternativas descartadas y por qué

- **Recortar en `ContextBuilder`, después del filtro.** Es donde más a mano
  estaba el dato, y es justo donde no puede ir: allí no se distingue el
  veredicto del modelo de una rendición suya, así que recortaría también un
  fallo abierto; y actuaría **después** del rescate RF-25/RF-26, de modo que
  podría tirar la crítica que el rescate acababa de recuperar.
- **Pasar la `Peticion` entera al puerto.** El puerto es deliberadamente
  estrecho —un método, un `Protocol`—; darle permiso, propósito y ámbito a un
  adaptador de red es acceso que no necesita para decidir qué conservar.
- **Derivar el cupo de `limite_duro` en vez de `objetivos`/`limite_objetivo`.**
  `limite_duro` es lo que `G12` ya aplica en el motor: usarlo aquí sería
  aplicar dos veces la misma puerta y no la cardinalidad. Es además el campo
  que degrada al «límite que no ata» en los 47 casos, así que no recortaría
  nada.
- **Inventar una `n` para `EXACTA` a partir de la consulta** (contar los
  sustantivos, buscar «cuál» frente a «cuáles»…). Sería fabricar una
  adjudicación con una heurística que nadie ha medido, exactamente lo que
  ADR-164 se negó a hacer. Si esa `n` tiene que existir, la decide el
  propietario y la infiere el intérprete (palanca 1), no el filtro.
