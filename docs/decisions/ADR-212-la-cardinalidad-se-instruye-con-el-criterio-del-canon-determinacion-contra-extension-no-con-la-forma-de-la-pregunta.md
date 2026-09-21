# ADR-212 — La cardinalidad se instruye con el criterio del canon: determinacion contra extension, no la forma de la pregunta

- Estado: APROBADO
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

**Validación obligatoria, redactada para no caducar.** Las cuatro
comprobaciones de `scripts/check.ps1` —`ruff format --check`, `ruff check`,
`mypy src tests` y `pytest`, en una sola invocación y sin partir `pytest` en
tandas (ADR-145)— las corre **Quality sobre el head que esta PR entrega**, y
las vuelve a correr **en cada empuje**. El veredicto vigente es el de la
ejecución de Quality que la incidencia #653 publica para el head actual.

**Por qué está escrito así, y no anclado a un SHA.** Las rondas 2, 3 y 4
escribieron este párrafo clavando un árbol concreto y enumerando a mano qué
quedaba fuera de él. Las tres veces la enumeración quedó incompleta, y la
tercera de una forma que no dependía de nadie: **`main` se movió por debajo**.
La PR #652 se fusionó en `main` el 20-09, esta rama tuvo que traerla, y con
eso un párrafo que decía «`git diff --stat 5d79fe6..HEAD` es una sola línea»
pasó a describir **196 ficheros y 5810 inserciones**, incluidos `MEMORIA.md` y
`docs/audits/registro_defectos.yml`, que el propio párrafo declaraba «dentro
del árbol validado».

La raíz no era una enumeración mal hecha tres veces: **una prosa que congela
un SHA describe un árbol que deja de existir en cuanto la rama se mueve**, y
una rama se mueve cada vez que su base avanza, lo cual no lo controla quien
escribe el ADR. Por eso este párrafo ya no nombra ningún árbol: nombra **el
head vigente**, que es una referencia que se actualiza sola. La siguiente
fusión de `main` no puede volver a falsearlo, porque no hay ninguna afirmación
que dependa de que el árbol se quede quieto.

**Corridas locales de la rama, como historia y sólo como historia.** Ninguna
describe el head que se entrega; se conservan porque enseñan que el cambio
estuvo en verde en cada paso, no para sostener el head actual:

| árbol | qué traía | terna | duración |
| --- | --- | --- | --- |
| `d9768650` | el cambio con el número 204 | `6726 passed, 17 skipped, 2 xfailed` | 1283.68 s |
| `d8cf2756` | el mismo cambio renumerado a 212 | `6726 passed, 17 skipped, 2 xfailed` | 758.73 s |
| `c866d763` | el mismo cambio con las correcciones documentales de la ronda 3 | `6726 passed, 17 skipped, 2 xfailed` | 635.71 s |
| `5d79fe64` | el mismo cambio con la enumeración de la ronda 4 | `6726 passed, 17 skipped, 2 xfailed` | 640.73 s |
| `ca847501` | el head aprobado en la ronda 5, antes de traer `main` | `6726 passed, 17 skipped, 2 xfailed` | 616.43 s |
| `178b1bee` | **con `main` (#652) dentro y `Estado: APROBADO`** | `7311 passed, 16 skipped, 2 xfailed` | 687.37 s |

Esa última corrida de la tabla se hizo con los cuatro pasos por separado y no
con `check.ps1` —`ruff format --check` («644 files already formatted»), `ruff
check` («All checks passed!»), `mypy src tests` («Success: no issues found in
606 source files») y el `pytest` de la fila, con código de salida 0—. Cuatro
pasos separados **no sustituyen** a la invocación única (ADR-145), y la razón
que se dio para partirlos —que el runner no tenía `pwsh`— era falsa:
`/usr/bin/pwsh` está instalado (PowerShell 7.6.5). Desde la ronda siguiente la
cadena se corre como manda el guion, **una sola invocación de `pwsh -File
scripts/check.ps1`**, y su terna y su código de salida viven donde no caducan:
en el veredicto de la ronda que la corrió y en la ejecución de Quality del head
vigente. No se clavan aquí, porque una cifra clavada en este párrafo vuelve a
describir un árbol que la próxima fusión de `main` mueve, que es el defecto que
esta sección acaba de dejar de cometer.

**Lo que esta comprobación NO dice:** nada sobre el efecto en la cifra del
banco. Aquí no hay Ollama, y no se ha simulado ninguna medición.

## El número de este ADR

Este ADR nació como `ADR-204` y se renumeró a **212** antes de fusionar. La
ronda 2 atribuyó la colisión a que la otra rama «empujó `ADR-204` … `ADR-211` a
las 13:32Z, una hora antes de que esta rama creara su 204». **Esa cronología es
falsa**, y además se contradecía a sí misma: ADR-180 §2 dice expresamente que
las ramas abiertas desde horas antes sí quedan cubiertas por el fetch, así que
un 204 empujado a las 13:32Z no habría llegado a colisionar. La cronología real,
reconstruida con los tiempos de empuje —no con los de commit, que es donde se
torció la explicación anterior—:

- **13:32:55Z.** `claude/sirius-collaboration-rir6r6` (PR #652) empuja
  `0b15d1c`. Ese árbol llega hasta `ADR-202`:
  `git ls-tree -r --name-only 0b15d1c docs/decisions/` no contiene ningún 204.
  Lo que se empujó a las 13:32Z no era el 204.
- **14:12:59Z – 15:27:00Z.** Esa rama **crea** `ADR-204` … `ADR-211` en commits
  locales (`e5e5c54` el 204), pero no los empuja: sus ejecuciones de Quality
  saltan de `0b15d1c` (13:32:55Z) directamente a `3de6e77` (15:29:28Z), sin
  ninguna en medio
  (`gh api "…/actions/runs?branch=claude/sirius-collaboration-rir6r6"`).
- **14:40:31Z.** Esta rama pide su número y crea el ADR (`3c50d7d`). En ese
  momento el remoto **no tenía** ningún 204 que traer.
- **15:22:53Z.** Esta rama empuja su 204 (Quality de `b67f389`). La otra lo
  empuja unos cinco minutos después, con `3de6e77`.

Es decir: el caso no es el que el fetch de ADR-180 cubre, sino **exactamente la
ventana de carrera que ADR-180 §2 declara abierta** —dos sesiones que piden
número antes de que ninguna haya empujado, «el remoto no puede decir lo que aún
no le han contado»—. El fetch no falló ni se saltó: en el instante de pedir el
número, 204 era el número correcto, y no hace falta invocar creación manual,
`--sin-traer` ni un fetch roto para explicar la colisión. La colisión solo
aparece al fusionar, y la caza
`tests/automation/test_registro_de_decisiones.py::test_no_new_number_is_ever_reused`. El número nuevo es el que devuelve `uv run python scripts/siguiente_adr.py
--solo-numero` con el fetch de ADR-180 («traidas las cabezas del remoto;
consultadas 343 ramas con ADR» → `212`), no uno elegido a mano. Se renumeró el
fichero, su encabezado, `H-212`/`adr: 212` en el registro de defectos con la
ruta y el comentario que los precede, la cita del comentario de
`ollama_query_intent_classifier.py` y `MEMORIA.md` regenerada con
`uv run sirius-memoria conocimiento`. Ni una línea de contenido técnico cambió.

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
