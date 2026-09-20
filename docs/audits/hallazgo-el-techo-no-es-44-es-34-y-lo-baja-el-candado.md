# El techo no es 44/47: es 34/47, y quien lo baja es el candado — 20-09-2026

Responde a `arranque-el-hueco-que-queda-en-el-filtro.md`, escrita antes de
mirar. Determinista, sin Ollama, sobre `main` en `66f11424` y la grabación
congelada `tests/acceptance/fixtures/relevance_filter_frozen_run.json`.

## Primero: corrijo mi propio hallazgo del techo

`hallazgo-el-techo-esta-en-el-filtro-no-en-la-busqueda.md` publicó esta tabla:

| configuración | techo con filtro perfecto |
|---|---|
| petición declarada | **44/47** |
| la del laboratorio (grabación) | **42/47** |

y concluyó que el filtro tenía **quince casos** de recorrido sobre el suelo de
29/47. **Ese techo está mal calculado.** Lo calculé como «un caso es exacto si
y solo si la búsqueda le trae todo su `resultado_esperado`» — es decir,
suponiendo que un filtro perfecto **entrega exactamente lo que conserva**.

No lo entrega. Entre el veredicto del filtro y lo que sale hay **el rescate de
criticidad** (RF-25/RF-26, M15/M19b, ADR-128), y ese rescate **vuelve a meter
cosas que el filtro había tirado**.

## Lo que hace el rescate, literal

`src/sirius/domain/relevance.py:516-521`:

> **RF-25**: si `kept_by_filter` conservó al menos una de `candidates`, una
> candidata protegida que el filtro descartó **se rescata de vuelta**.
> **RF-26**: si el filtro no conservó ninguna, ese veredicto se respeta
> entero — no hay rescate, ni siquiera para una protegida.

«Protegida» es `criticality is not None` (`context._is_protected_by_criticality`),
o sea **CRÍTICO o IMPORTANTE**. En el arnés es la misma condición por otro
nombre: `categoria_del_item` devuelve `restriccion` **si y solo si**
`criticidad is not None` (`staged_engine_category_and_relevance.py:276`). Los
dos caminos protegen **las mismas 19 identidades de 97**.

La consecuencia, que no estaba escrita en ninguna parte:

> **Si un caso espera algo —veredicto no vacío— y entre sus candidatas hay una
> protegida que NO está en lo esperado, ese caso no puede ser exacto jamás**,
> por bueno que sea el filtro: el rescate la mete de vuelta.

## El techo, recalculado

Aplicando la fórmula **exacta** del arnés (`aplicar_regla_de_criticas_original`)
sobre la grabación, bajo el supuesto explícito `candidatas == entraron_al_filtro`
—lo único que la grabación deja ver, así que todo esto es una **cota superior**:
si hubiera candidatas que nunca entraron al filtro, pasan intactas y el número
sólo puede bajar—:

| | casos exactos |
|---|---|
| techo **ingenuo** (sin contar el candado) | 42/47 |
| **techo real** (con RF-25 puesto) | **34/47** |
| **alcanzado hoy por la grabación** | **29/47** |

**El 29/47 es exactamente el suelo D1.** Que la aritmética reproduzca el número
que el arnés mide de verdad es la comprobación de que el modelo es correcto: no
es una estimación, es la misma regla aplicada a los mismos datos.

> **Al filtro le quedan cinco casos, no quince.**

## Los trece que no puede alcanzar

| caso | por qué |
|---|---|
| `CA-02` ¿Qué restricciones de transporte tengo? | rescate fuerza `MEM-001` |
| `CA-26` Enumera las restricciones esenciales… | rescate fuerza `MEM-001` |
| `CA-31` Dame todas las restricciones esenciales… | rescate fuerza `MEM-001` |
| `CA-05` ¿Qué decisión de presupuesto usábamos antes? | rescate fuerza `DEC-003` |
| `CA-14` ¿De qué se ocupa Juan? | rescate fuerza `MEM-025` |
| `CA-20` ¿Puedo usar vuelos con escala? | rescate fuerza `DEC-010`, `MEM-016` |
| `CA-21` ¿Acepto escalas? | rescate fuerza `MEM-014` |
| `CA-25` Atlas | rescate fuerza `DEC-003`, `DEC-010` |
| `CA-22`, `CA-29`, `CA-30`, `CA-33`, `CA-34` | la búsqueda no trae lo esperado |

**Ocho de trece los bloquea el rescate**, no el filtro ni la búsqueda.

### Y esto mata una palanca que yo iba a proponer

`CA-20` «¿Puedo usar vuelos con escala?» espera `MEM-014` y el filtro conserva
además `MEM-016`. `CA-21` «¿Acepto escalas?» espera `MEM-016` y conserva además
`MEM-014`. Son **espejo**, y la instrucción del filtro **ordena exactamente eso**:

> «- Si hay dos frases opuestas sobre lo mismo, devuelve LAS DOS: quien
> pregunta tiene que ver que hay un permiso y una prohibicion.»

Es el mismo defecto que ADR-212 acaba de arreglar en el intérprete —
`criterio-que-se-pide-distinto-del-que-se-puntúa`— y llegué a redactarlo como
tercer encargo. **No sirve de nada**: `MEM-014` y `MEM-016` son las dos
CRÍTICAS, así que el rescate mete la otra de vuelta **diga lo que diga el
filtro**. Arreglar esa regla no gana `CA-20` ni `CA-21`.

Es el segundo «no se puede» que esta noche se decide **después** de mirar el
mecanismo entero y no antes. La diferencia es que esta vez miré antes de
proponerlo.

## La palanca que sí aparece, y que no es mía

De las 19 protegidas, **18 son CRÍTICO y una es IMPORTANTE**: `MEM-001`, «El
usuario prefiere que redactes en tono directo y sin adornos» — una preferencia
de estilo, tratada como restricción protegida, que se cuela en las tres
preguntas por «restricciones esenciales».

Cambiando **qué cuenta como protegida**, con la misma grabación y el mismo
filtro:

| definición de protegida | exactos hoy | techo | casos que bloquea |
|---|---|---|---|
| **CRÍTICO + IMPORTANTE** (hoy, ADR-128/M19b) | **29/47** | 34/47 | 8 |
| **solo CRÍTICO** | **31/47** | **37/47** | 5 |
| ninguna (sin rescate) | 32/47 | 42/47 | 0 |

**Dos casos medidos, hoy, sin modelo: `CA-02`, `CA-26` y `CA-31` dejan de estar
bloqueados y dos de ellos pasan a exactos.** Una condición, en una línea.

### Lo que cuesta, y por qué la decisión no es mía

La regla dura de la nota de arranque: *no se propone nada que aumente la
agresividad del filtro sin contar qué se lleva por delante.* Contado:

- `MEM-001` se espera en **2** casos (`CA-01`, `CA-30`).
- Entra al filtro en **4**.
- Donde se espera **y** entra, el filtro **la conserva igualmente**.
- **Coste medido de sacarla del rescate: cero.** No se pierde nada en el banco.

**Y ese cero no dice lo que parece.** El banco tiene **exactamente una**
identidad IMPORTANTE. Un banco con un solo ejemplar de una clase **no puede
medir** una regla sobre esa clase: el coste cero no es prueba de que el cambio
sea seguro, es prueba de que **este instrumento no sabe responder**. Fuera del
banco, IMPORTANTE puede ser mucha gente.

Además ADR-128 eligió `criticality is not None` **a propósito**, replicando lo
que la etiqueta `restriccion` del laboratorio protegía —«every non-ordinary
identity alike, never just one level»—. Aflojar el candado es **deshacer una
decisión registrada del propietario sobre seguridad de la memoria**, con dos
casos de banco a favor y ningún instrumento que mida el riesgo.

**Se deja escrito y se para aquí.** Es decisión suya, y necesita antes un banco
que tenga más de una IMPORTANTE.

## Contraste con las predicciones

| predicción (escrita antes de mirar) | resultado |
|---|---|
| >= 70% de los casos que fallan lo hacen **solo por exceso** | **FALLADA** — 6 de 15 (40%); 6 de 11 contando solo donde el filtro pinta algo |
| el exceso está **repartido** (10 casos o más) | **FALLADA** — 9 casos, y **27 de los 35** elementos en solo dos |
| la propiedad del ruido conservado es «mismo tema, no responde», que la **regla 7 ya prohíbe** | **ACERTADA** — 29 de los 35 elementos de exceso caen en casos que no esperan nada, y son distractores del mismo tema |

La tercera la acerté **y la conclusión que colgué de ella era falsa**. Escribí:
*«si acierto la tercera, el resultado es un cierre, no una palanca»*. Hay
palanca — pero no está en la prosa del filtro **ni en el filtro**: está en el
candado, un sitio donde la nota de arranque ni miró.

## Qué cambia esto en el plan

| línea | antes | ahora |
|---|---|---|
| **filtro de relevancia** | prioritaria, 15 casos de recorrido | **5 casos de recorrido**; sigue siendo la mayor, pero es un tercio de lo que dije |
| **candado de criticidad** | no estaba en el mapa | **bloquea 8 casos**; una línea daría +2 medidos y +3 de techo, y es **decisión del propietario** |
| intérprete / `modo` y `corte` | encargo preparado | sin cambios: `CA-32`, uno de los cinco ganables, es suyo |
| ranking del motor, siembra | cerradas | sin cambios |

## Addendum, misma noche: las otras dos configuraciones, medidas

El párrafo que cerraba este documento decía que el techo real de «petición
declarada» *«exige correr la búsqueda, no leer un fixture»*. Se corrió. Con
`_medir` del propio `scripts/diagnosticar_busqueda_del_banco.py` —importado tal
como el guion se importa a sí mismo, y con su propia aserción de que el filtro
ve las 47 consultas como guardián contra el fallo de identidad de módulo que ya
me costó una medición esta noche— y aplicando a sus conjuntos de candidatas la
fórmula de RF-25:

| configuración | exactos sin filtro | techo **ingenuo** (el que publiqué) | **techo real** | si protegiera solo CRÍTICO |
|---|---|---|---|---|
| grabación (laboratorio) | — | 42/47 | **34/47** | 37/47 |
| `--peticion` | 17/47 | **44/47** | **32/47** | 34/47 |
| `--ejes --peticion` | 22/47 | **45/47** | **33/47** | 35/47 |

El `44/47` que publiqué como techo de la mejor configuración **es 32/47**.

### Y hay algo peor que una corrección

Mírese la tabla en vertical. **La configuración que busca mejor tiene el techo
real MÁS BAJO.** `--peticion` recupera más de lo esperado que la grabación
—techo ingenuo 44 contra 42— y sin embargo su techo real es **32 contra 34**.

La razón es mecánica: buscar mejor trae **más** candidatas, y entre las
candidatas de más hay **más protegidas**, y el rescate las mete todas. En
`--peticion` el rescate bloquea **12 casos**, contra 8 en la grabación.

> **Con el candado tal como está, mejorar la búsqueda empeora el techo.**

`CA-44` lo enseña en un renglón: el rescate le fuerza ocho identidades
(`MEM-001`, `MEM-106`…`MEM-112`). Ninguna la eligió el filtro; todas entran
porque son protegidas y el filtro conservó algo.

### Lo que esto le hace al plan entero

El suelo D1 es **29/47**. Los techos reales de las tres configuraciones son
**32, 33 y 34**. Es decir:

> **A todo el sistema, tal como está arquitecturado, le quedan entre tres y
> cinco casos.** No quince. No los 45/47 que ADR-164 predijo.

Y eso no es un defecto del filtro, ni de la búsqueda, ni del intérprete: las
tres piezas juntas, perfectas, se quedan ahí. El límite lo pone **una decisión
de seguridad registrada** —ADR-128, no perder nunca una no-ordinaria— que hace
exactamente lo que se le pidió.

**No se toca nada.** Lo que cambia es lo que se le puede prometer a una
medición: ninguna palanca sobre filtro, búsqueda o intérprete puede pasar de
~34/47 mientras el candado proteja CRÍTICO **e** IMPORTANTE. Si el objetivo
está por encima, la conversación no es sobre prompts: es sobre el candado, y es
suya.

**Lo que este addendum NO dice.** No mide el camino de producción con la puerta
cerrada, que además del rescate lleva una cláusula incondicional —toda candidata
`category is None` pasa, diga lo que diga el filtro
(`ContextBuilder._apply_relevance_filter`)— que el arnés no replica. Ese techo
**solo puede ser más bajo**, nunca más alto.
