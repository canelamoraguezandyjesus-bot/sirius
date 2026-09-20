# ADR-212 — La cardinalidad se instruye con el criterio del canon: determinacion contra extension, no la forma de la pregunta

- Estado: PROPUESTO
- Fecha: 2026-09-20
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

## Nota de arranque (escrita ANTES del primer commit de código)

Las cuatro preguntas de ADR-001, respondidas antes de tocar nada.

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en **lo que
   se le pide al modelo**, no en lo que el modelo contesta: la constante
   `_INSTRUCCION` de `src/sirius/adapters/ollama_query_intent_classifier.py`
   define la cardinalidad por la forma gramatical de la pregunta, y el banco
   de 47 casos la puntúa con el criterio de B04 §15.2 —determinación contra
   extensión—. El arreglo va exactamente ahí: el bloque `cardinalidad` de esa
   constante, y nada más. ¿Puede el sitio del arreglo **observar** el fallo
   que arregla? Sí, y de dos maneras distintas: la instrucción es literalmente
   el texto que viaja en el mensaje `system` de cada consulta —una prueba lo
   lee del cuerpo de la petición—, y la medición del banco compara campo a
   campo contra el criterio del canon. Lo que el arreglo **no** puede observar
   desde este runner es su propio efecto: eso exige Ollama, y aquí no lo hay
   (ver la pregunta 2 y «Condiciones de parada» de la incidencia #653).
2. **¿Qué NO garantiza esto?** (a) **No trae ninguna cifra nueva.** Este
   encargo no mide su efecto: CI no tiene Ollama, y una cifra sacada del doble
   determinista sería peor que ninguna (ADR-117). Se entrega con la medición
   pendiente, como ADR-164 previó. (b) **No toca la línea `limite`**: los
   `limite.n` de los tres casos `OBJETIVO` (`CA-26`, `CA-30`, `CA-34`) son
   cuota que el caso asigna, no algo inferible de la pregunta, y ninguna
   instrucción puede arreglarlos. (c) **No mete casos del banco en la
   instrucción.** El par `CA-08`/`CA-50` explica el criterio en este ADR y en
   los comentarios del código, y **no** viaja al modelo: escribir las
   preguntas del banco en el prompt convertiría la medición en una
   comprobación de memoria y dejaría la predicción sin valor. (d) No abre
   ningún interruptor: las cuatro claves de `memory_gates.py` siguen apagadas.
   (e) No cambia el esquema de respuesta, ni el modelo, ni el timeout, ni los
   parámetros de la llamada.
3. **Criterio de parada (decidido ANTES de ver ningún resultado).** Paro y no
   sigo empujando si ocurre cualquiera de estas: (i) cumplir el objetivo exige
   tocar algo de «Fuera de alcance» de la incidencia —la línea `limite`, el
   esquema, `src/sirius/application/**`, el corpus— → `BLOCKED_BY_DECISION`;
   (ii) el texto literal de §15.2 no se puede leer desde la rama de trabajo
   → parar y decirlo, en vez de reconstruirlo de memoria; (iii) alguna prueba
   determinista existente del adaptador o del intérprete cambia de intención
   para ponerse verde; (iv) dos rondas de revisión con defectos de la misma
   familia (ADR-001 §2, regla de #581) → buscar la raíz, no encadenar una
   tercera. Y el criterio de la propia medición, que decide el propietario:
   **por debajo de `30/47` en cardinalidad es una regresión y el cambio se
   revierte.**
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** El fallo temido es
   que la instrucción vuelva a derivar, en silencio, a un criterio gramatical
   —que es como llegó hasta aquí: nadie la escribió contra el canon, se
   escribió a ojo—. Lo que lo hace imposible no es el comentario que cita la
   sección: es la prueba de `tests/unit/test_ollama_query_intent_classifier.py`
   que lee la instrucción **tal como viaja al modelo**, exige los seis trozos
   literales de §15.2 en la línea de su cardinalidad y **prohíbe** las tres
   frases de la redacción retirada. Con solo la primera mitad, añadir el canon
   y dejar lo viejo al lado pasaría; con las dos, no. Lo que queda solo
   improbable, y se dice: que el criterio del canon cambie en una revisión de
   B04 y nadie vuelva aquí. Contra eso no hay guarda, porque el documento vive
   fuera de este árbol.

### Predicción, publicada ANTES de medir (la de la incidencia #653, tal cual)

> Con la instrucción alineada, `cardinalidad` pasa de `30/47` a **`>= 38/47`**,
> y la coincidencia campo a campo de `24/47` a **`>= 30/47`**. Si sale **por
> debajo de 30/47** en cardinalidad, es una regresión y el cambio se revierte.

No se ajusta después de verla. La medición la hace el propietario en su
máquina, con Ollama real, y se registra tal cual salga.

## Contexto y problema

La palanca 1 de ADR-148 —el intérprete de peticiones de ADR-164— le pide a un
modelo local cinco campos, y uno de ellos es la **cardinalidad**. Medida con
Ollama real en la máquina del propietario el 20-09-2026, en dos corridas
independientes, dio **`cardinalidad 30/47` en las dos**: 17 fallos, más de la
mitad de todo el error de la palanca, con los demás campos entre 41 y 43 de 47.

La causa no es que el modelo falle. Es que **se le pide un criterio y se le
puntúa con otro**:

- La instrucción decía «EXACTA: la pregunta busca **un dato concreto**»,
  «ACOTADA: la pregunta pide **una cantidad concreta**», «EXHAUSTIVA: la
  pregunta pide **todo lo que haya de un tema**». Las tres frases hablan de la
  **pregunta**: cuántas cosas nombra, si trae un número, de qué tema va.
- El banco puntúa con **B04 §15.2**, que habla del **conjunto de respuesta**.

El par que lo demuestra, y que cualquier redacción nueva tiene que explicar:

| caso | consulta | canon | lo que da la redacción vieja |
|---|---|---|---|
| `B04-CA-08` | «¿Cuál es **el** presupuesto de Beta?» | `EXHAUSTIVA` | `EXACTA` —«un dato concreto»— |
| `B04-CA-50` | «¿Qué **condiciones** de acceso al almacén hay?» | `EXACTA` | `EXHAUSTIVA` —suena a «todo lo que haya»— |

Falla en los **dos** sentidos, que es la firma de un criterio distinto y no de
un criterio mal aplicado: «presupuesto de Beta» es una **condición** cuya
extensión completa se pide (son dos elementos, y se esperan los dos), y «qué
condiciones de acceso hay» es una **respuesta cerrada**. El criterio no es
singular contra plural: es **determinación contra extensión**.

### El criterio, literal, con su cita

De la tabla «Cardinalidad · Definición · Regla de parada» de §15.2
(«Cardinalidad y suficiencia») del Bloque 04 de Búsqueda y Recuperación, v1.0
APROBADO, leído del propio documento en este runner (ver «Comprobación»):

```
EXACTA       Busca uno o varios objetivos identificados o una respuesta cerrada.
ACOTADA      Busca N resultados, una lista definida o exploración con límite/criterio explícito.
EXHAUSTIVA   Busca todos los elementos que cumplen una condición.
```

Y §15.3 lo confirma desde el otro lado: «S1 · Suficiencia por cardinalidad.
Solo para EXACTA o ACOTADA… **Nunca se aplica a EXHAUSTIVA**».

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3, publicado antes de tocar nada: alcance
ajeno → `BLOCKED_BY_DECISION`; §15.2 ilegible desde la rama → parar y decirlo;
una prueba existente que cambie de intención → parar; dos rondas de la misma
familia → buscar la raíz. Y, del lado de la medición que hará el propietario,
`cardinalidad` por debajo de `30/47` es regresión y se revierte.

## Opciones consideradas

1. **Reescribir el bloque `cardinalidad` con las definiciones literales de
   §15.2.** Toca un solo sitio, no cambia el esquema ni el vocabulario cerrado
   —`EXACTA`/`ACOTADA`/`EXHAUSTIVA` siguen siendo los tres valores— y alinea
   lo que se pide con lo que se puntúa.
2. **Dar al modelo ejemplos del banco** («¿cuál es el presupuesto de Beta?» →
   `EXHAUSTIVA`). Subiría la cifra y no demostraría nada: mediría memoria del
   corpus, no interpretación, y dejaría la predicción sin valor.
3. **Cambiar el corpus o `resultado_esperado`** para que encajen con la
   instrucción de hoy. Es mover el patrón de medida para que el instrumento
   acierte; además está expresamente fuera de alcance.
4. **No tocar nada y declarar el techo.** Deja `30/47` sin explicación y hace
   ilegible cualquier medición posterior de la palanca 1.

## Decisión

**Se toma la opción 1.** El bloque `cardinalidad` de `_INSTRUCCION`
(`src/sirius/adapters/ollama_query_intent_classifier.py`) enuncia las tres
definiciones de §15.2 casi palabra por palabra, sin reducirlas —`EXACTA`
conserva «uno o varios objetivos identificados» **y** «o una respuesta
cerrada»; `ACOTADA` conserva «N resultados», «una lista definida» **y**
«límite/criterio explícito»; `EXHAUSTIVA` dice «todos los elementos que
cumplen una condición», no «todo lo que haya de un tema»— y cierra con una
frase que nombra la confusión que se retira: lo que decide no es cómo suena la
pregunta, sino la forma del conjunto de respuesta.

Un comentario junto a la constante cita el documento, la sección y la tabla de
donde sale cada definición, y deja escrito el defecto medido para que el
siguiente que pase sepa por qué la redacción es esa.

**No se toca nada más**: ni la línea `limite`, ni los bloques `modo`,
`tiempo_objetivo` y `corte_de_registro`, ni `_ESQUEMA_RESPUESTA`, ni el
corpus, ni ningún interruptor.

## Comprobación que la sostiene

**El texto de §15.2 se leyó, no se reconstruyó de memoria.** El documento está
en la rama de evidencia (`evidence/adr001-spikes`), bajo la carpeta de fuentes canónicas de arquitectura, con nombre
`SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO.docx`; se trajo con
`git fetch --depth=1 origin evidence/adr001-spikes` y se extrajo el XML del
`.docx` con la biblioteca estándar. La tabla citada arriba es esa salida.

**La prueba, vista fallar ANTES del cambio** (ADR-001 §3). Con la instrucción
vieja en el árbol, `uv run pytest tests/unit/test_ollama_query_intent_classifier.py -k "criterios_del_canon or forma_de_la_pregunta"`
dio `6 failed, 39 deselected`. Primera línea del fallo:

```
E  AssertionError: la definición de «ACOTADA» pierde «N resultados» de B04 §15.2: - ACOTADA: la pregunta pide una cantidad concreta («dame las tres…»).
```

**La mutación, vista fallar** (ADR-001 §3, en las dos direcciones). Con la
redacción nueva puesta, devolver el bloque `cardinalidad` a su redacción de
hoy y correr el fichero entero da `6 failed, 39 passed`; restaurarlo devuelve
`45 passed`. Primera línea del fallo de la mutación:

```
E  AssertionError: la definición de «ACOTADA» pierde «N resultados» de B04 §15.2: - ACOTADA: la pregunta pide una cantidad concreta («dame las tres…»).
```

La prueba afirma sobre la instrucción **tal como viaja al modelo** —la lee del
cuerpo de la petición HTTP que el adaptador envía, no de la constante
privada—, y sobre el **bloque** de cardinalidad, no sobre la instrucción
entera: una frase del canon escrita en cualquier otro campo no enseña nada
sobre la cardinalidad.

**Ninguna prueba existente cambió de intención.** El fichero del adaptador
pasa de 39 a 45 pruebas; las 39 anteriores están intactas.

**Validación obligatoria: una sola invocación** de `pwsh -File scripts/check.ps1`
sobre el árbol de `d9768650`, que es el que trae el cambio entero —código,
pruebas, ADR, registro de defectos y la vista regenerada—. Código de salida
**0**, con los cuatro pasos en verde: `ruff format --check` («637 files already
formatted»), `ruff check` («All checks passed!»), `mypy src tests` («Success: no
issues found in 600 source files») y `pytest`:

```
=========== 6726 passed, 17 skipped, 2 xfailed in 1283.68s (0:21:23) ===========
```

Una sola invocación y sin partir `pytest` en tandas (ADR-145). El head final de
la rama añade a `d9768650` solo este párrafo del ADR: la terna es la de su
árbol y así se lee (ADR-154).

**Lo que esta comprobación NO dice:** nada sobre el efecto en la cifra del
banco. Aquí no hay Ollama, y no se ha simulado ninguna medición.

## Consecuencias

- La palanca 1 pide ahora el mismo criterio con el que se la puntúa. Si la
  predicción se cumple, `cardinalidad` deja de ser la mitad del error de la
  palanca; si no se cumple, la causa está en otro sitio y esa información
  también vale.
- **Queda pendiente la medición del propietario**, con Ollama real, en su
  máquina. Este ADR se entrega con ese hueco abierto a propósito, y la
  predicción ya publicada delante para que no se pueda ajustar después.
- El `limite.n` de los tres casos `OBJETIVO` sigue sin ser inferible de la
  pregunta, y sigue siendo decisión de producto del propietario. Este cambio
  no lo toca ni lo pretende.
- Queda en pie la deuda documental que la auditoría del 20-09-2026 señaló: B04
  v1.0 APROBADO define criterios de aceptación vivos y vive en una rama de
  evidencia, no en `main`. Decidir si se porta no es de este encargo.

## Alternativas descartadas y por qué

- **Ejemplos del banco dentro del prompt** (opción 2): contamina el
  instrumento. Se descarta aunque subiera la cifra —precisamente porque
  subiría la cifra sin que nadie pudiera saber por qué—.
- **Ajustar el corpus al criterio de la instrucción** (opción 3): mover el
  patrón de medida. Además, expresamente fuera de alcance.
- **Tocar también la línea `limite`** para intentar los tres `OBJETIVO`:
  imposible por construcción (el 10 de «prepara el contexto de planificación
  de Alfa» no está en la frase) y arriesga el `42/47` que ese campo ya
  consigue.
- **Esperar a portar B04 a `main` antes de alinear la instrucción**: el
  criterio ya es legible y citable hoy con fichero, rama y sección; esperar
  solo conserva un defecto medido.

## La lección

- familia: `criterio-que-se-pide-distinto-del-que-se-puntua`
- sin esto se repetiría: escribir a ojo la instrucción que se le da a un
  modelo y medirla después contra una regla del canon que nadie puso delante,
  de modo que el error medido se atribuye al modelo en vez de al enunciado.
- lo hace cumplir: `tests/unit/test_ollama_query_intent_classifier.py`
