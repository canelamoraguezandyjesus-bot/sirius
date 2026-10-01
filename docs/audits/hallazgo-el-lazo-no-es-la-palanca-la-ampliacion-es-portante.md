# El lazo no es la palanca: la ampliación por criticidad es portante — 20-09-2026

Responde a `arranque-el-lazo-entre-la-ampliacion-y-el-rescate.md`, escrita antes
de medir. Determinista, sin Ollama. **Negativo medido.**

## La hipótesis

La entrada 134 concluyó que el techo lo fija el rescate RF-25 y que la única
salida es **proteger menos** (deuda 42). Leyendo el motor apareció un segundo
paso: cuando el texto de la consulta activa el vocabulario de criticidad,
`rank_relevant_knowledge.py:550-600` inyecta `solo_por_criticidad` —**todas** las
identidades no ordinarias del ámbito, marcadas `fts_match=False`,
`subject_matches_query=False`—, y después RF-25 las protege del filtro.

El lazo: **el motor inyecta → el filtro intenta tirar → el rescate devuelve**.
El filtro no puede deshacer el paso 1 por construcción.

La hipótesis era que el techo no lo fija *cuánto se protege* sino *qué se
inyecta*, y que apagar la inyección daría una salida **sin tocar la seguridad**.

## Lo medido

Apagando **solo** la llamada que usa el vocabulario de criticidad (por parche en
la medición, restaurado al salir; la ampliación por categoría se queda encendida):

| | `--peticion` ON | OFF | `--ejes --peticion` ON | OFF |
|---|---|---|---|---|
| exactos sin filtro | 17/47 | 19/47 | 22/47 | 25/47 |
| elementos de más | 162 | 148 | 146 | 131 |
| hallados /81 | 78 | **72** | 79 | **73** |
| **omisiones críticas** | **0** | **6** | **0** | **6** |
| la búsqueda trae todo lo esperado | 44/47 | 42/47 | 45/47 | 43/47 |
| **techo real (RF-25)** | 32/47 | **34/47** | 33/47 | **36/47** |
| bloqueados por el rescate | 12 | 8 | 12 | 7 |

**Sube el techo dos y tres casos. Y cuesta seis críticas.**

Los casos que de verdad se liberan son **`CA-38` y `CA-44`** (y `CA-26` con ejes):
los que recibían el bloque entero de golpe. `CA-02` y `CA-31` salen de la lista
de bloqueados **pero no se ganan**: pasan a perder lo esperado, porque la
ampliación era lo único que se lo traía —`CA-31` deja de recibir `DEC-003`,
`DEC-010`, `MEM-014`, `MEM-016` y `MEM-025`, que son **cinco de sus cinco**—.

## El veredicto

El criterio de parada, escrito antes: *si lo sube < 3 casos o pierde esperado en
>= 5, la ampliación es portante y la deuda 42 es la única salida*.

`--peticion` sube **2**. Y el número que la nota de arranque no supo anticipar es
el que decide: **las omisiones críticas pasan de 0 a 6**.

> **La ampliación por criticidad es exactamente lo que mantiene las omisiones
> críticas en cero.** Apagarla compra dos o tres casos exactos a cambio de perder
> seis críticas. Es un pésimo trato y no se propone.

**Negativo registrado. El lazo no es la palanca.** La deuda 42 se queda como
está, y es la única.

## Y esto no es un defecto: es el diseño funcionando

Vale la pena decirlo con todas las letras, porque las tres últimas entradas han
sido correcciones de cosas mías y ésta no lo es.

El motor inyecta toda no-ordinaria del ámbito **para que no se pierda ninguna**.
El rescate la protege del filtro **por lo mismo**. Las dos piezas juntas
consiguen su objetivo declarado: **cero omisiones críticas en las cuatro
configuraciones medidas**, desde el 05-09. El precio es el techo de ~34/47.

Eso no es un fallo que arreglar: es **una decisión de producto, tomada y
registrada** (ADR-128), pagando precisión por seguridad. Lo único que estaba mal
era que **nadie había puesto el precio por escrito**, y yo publiqué tres veces un
techo que lo ignoraba.

## Contraste con las predicciones

| predicción (escrita antes de medir) | resultado |
|---|---|
| apagarla sube el techo real a **>= 40/47** (70%) | **FALLADA** — 34/47 y 36/47 |
| pierde esperado en **<= 3** casos (55%) | **ACERTADA en la letra** — 2 casos; pero perdió **6 críticas**, que es lo que importaba y no estaba en la predicción |
| los bloqueados son los de «restricciones esenciales» (80%) | **ACERTADA a medias** — los 7 que nombré están entre los 12, y la ampliación explica 4 de ellos |

La segunda es la lección: **acerté el número que pregunté y me faltó preguntar el
que decidía**. La nota contaba casos con esperado perdido y no contaba críticas
perdidas, cuando «no perder una crítica» es la propiedad que todo este mecanismo
existe para sostener.

## Dónde queda el mapa

| línea | estado |
|---|---|
| filtro de relevancia | 5 casos de recorrido sobre la grabación; sigue siendo la mayor |
| intérprete (`modo` y `corte`) | encargo preparado; `CA-32` es uno de los cinco ganables |
| **ampliación por criticidad** | **cerrada — portante, negativo medido** |
| candado / nivel de protección | **decisión del propietario (deuda 42)**, y la única que mueve el techo |
| ranking del motor, siembra | cerradas |
