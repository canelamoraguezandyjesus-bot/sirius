# Sirius 0.2 · ADR-002 · Inventario de lo que ya existe

**Qué es esto:** un inventario de lo que otros ya han construido para «memoria de un asistente»,
para decidir **qué se adopta, qué idea se copia y qué se descarta**, en lugar de seguir midiendo
cosas que la industria ya midió.

**Por qué existe:** porque el motor híbrido que construí —`FTS5` + vectores + fusión `RRF`— es de
manual, y lo construí y lo medí en vez de adoptarlo. Lo mismo la ampliación de consulta, que es
recuperación de información de los años setenta. Eso fue un error de método, y este documento es
la corrección.

---

## Aviso sobre la calidad de esta evidencia

En esta sesión **no hay buscador web** y **solo se pueden leer ficheros del repositorio de
Sirius**. La búsqueda en GitHub sí funciona, pero devuelve metadatos —descripción, temas,
estrellas, fechas—, no código.

De modo que cada fila lleva su procedencia:

- **`[listado]`** — visto en los resultados de búsqueda de GitHub de hoy. Nombre, descripción,
  estrellas y fecha son datos, no recuerdos.
- **`[conocimiento]`** — de lo que yo sé, **sin verificar aquí**. Trátese como hipótesis a
  confirmar, no como hecho.

Nada de lo que sigue se ha ejecutado ni leído en su código fuente. Este documento **no mide**:
sirve para decidir qué merece la pena mirar de cerca.

---

## 1. Lo primero, porque cambia todo lo demás: dos problemas distintos

Hay un malentendido que conviene deshacer antes de comparar nada.

Los productos de memoria para agentes optimizan una cosa: **que el agente conteste bien**. Sus
bancos de pruebas —`LoCoMo`, `LongMemEval`, `HaluMem`— puntúan si la respuesta final del modelo
era correcta.

`B04` pide otra cosa. Pide un **conjunto exacto** de elementos, y además:

| exigencia de `B04` | qué significa |
|---|---|
| `G4` ámbito | lo de otro proyecto no puede aparecer, ni siquiera para descartarse |
| `RF-19` polaridad | «se alquila coche» y «no se alquila coche» no pueden fundirse |
| `G7`/`G8` vigencia y tiempo | lo derogado no vale; lo aplicable depende del instante |
| `RF-25`/`RF-26` ausencia | decir «no tengo eso» **sin filtrar** si existe |
| `RF-24` críticos | no perder un elemento crítico en silencio |
| `RF-28` explicación | por resultado, con siete elementos |
| `RF-14` anti-barrido | no recorrer el canon entero para responder |
| `TOL-207` derivados | todo derivado, borrable y regenerable |

**Ningún producto del inventario hace las puertas.** Eso no es un defecto suyo: es que resuelven
otro problema. Y no es un argumento para no adoptarlos —la mitad de recuperación sí es de
estantería—, es un aviso de **qué parte seguirá siendo nuestra pase lo que pase**.

---

## 2. Productos de memoria: se adoptan o se descartan enteros

| proyecto | estrellas | qué dice ser | procedencia |
|---|---|---|---|
| **mem0** (`mem0ai/mem0`) | 62.900 | «capa de memoria universal para agentes» | `[listado]` |
| **memvid** (`memvid/memvid`) | 16.200 | memoria en fichero único, sin tubería RAG, *offline-first* | `[listado]` |
| **Memori** (`MemoriLabs/Memori`) | 15.700 | memoria agnóstica del LLM, orientada a empresa y on-premises | `[listado]` |
| **EverOS** (`EverMind-AI/EverOS`) | 11.900 | memoria portátil **local-first**, en Markdown, propiedad del usuario | `[listado]` |
| **Letta** (`letta-ai/letta-code`) | 3.000 | agentes con estado, memoria e identidad (antes MemGPT) | `[listado]` |
| **MemMachine** | 3.400 | memoria universal con grafo de conocimiento | `[listado]` |
| **memory-os** | 1.300 | 7 capas, Qdrant, hechos estructurados, local, cualquier LLM | `[listado]` |
| **Zep / Graphiti** | — | grafo de conocimiento **temporal**, validez bi-temporal | `[conocimiento]` |

### Lectura honesta

**Lo que aportan y nosotros no tenemos:** extracción de memorias desde la conversación,
consolidación —fundir lo repetido, actualizar lo que cambió—, y en el caso de `Graphiti`, validez
bi-temporal, que es lo más cercano que existe a nuestras `G7`/`G8` y a la sucesión de decisiones.

**Lo que les falta para Sirius:** las puertas. Y tres cosas más que no son negociables aquí:

1. **La mayoría asume servicio y red.** Sirius es una aplicación de escritorio con `SQLite` que
   tiene que funcionar sin conexión. Los que declaran lo contrario —`EverOS`, `memvid`,
   `memory-os`— son los únicos que merecen una mirada seria por este eje.
2. **Casi todos cobran una llamada al modelo por elemento ingerido.** Eso convierte guardar una
   memoria en un gasto recurrente y en una dependencia de red al escribir, no solo al leer.
3. **Borrado y regeneración.** `TOL-207` exige que todo derivado se pueda destruir y reconstruir.
   Un grafo consolidado por un modelo no es trivialmente regenerable ni trivialmente borrable, y
   eso hay que comprobarlo antes de adoptar nada, no después.

### Un caso que merece nombrarse aparte

`NORTHTEKDevs/genome` `[listado]`, 2 estrellas, creado hace un mes. Dice: memoria auditable,
ingesta local **sin ninguna llamada al modelo** (~10 ms por mensaje, funciona aislada de la red),
precisión comparable a `mem0` con coste de ingesta mil veces menor, **estado de creencia
bi-temporal**, y benchmarks `LoCoMo`/`LongMemEval` publicados.

Si la descripción fuera cierta, describe casi exactamente lo que Sirius necesita. Con dos
estrellas y un mes de vida **no se adopta**: se lee, se comprueban sus números y, si aguantan, se
copia la idea. Es una pista, no una solución.

---

## 3. Técnicas de recuperación: no se adoptan, se implementan, y son pocas líneas

Esta es la parte donde el reproche está más justificado, porque aquí hay soluciones **publicadas y
con nombre** para el fallo exacto que medimos.

**Nuestro fallo medido:** la pregunta es una pregunta y lo guardado es una afirmación, y no
comparten ni una palabra. «¿Hay evidencia de límite de gasto?» contra «El presupuesto máximo del
proyecto es 1.500 €». En la literatura eso se llama *vocabulary mismatch* y asimetría
pregunta-documento `[conocimiento]`.

| técnica | qué hace | lo hemos hecho | procedencia |
|---|---|---|---|
| **HyDE** | pedir al modelo que **escriba una respuesta falsa** a la pregunta, y buscar con ese texto en vez de con la pregunta | **NO.** Hice una versión casera y más pobre: añadir sinónimos | `[conocimiento]` |
| **doc2query** | al **guardar**, generar las preguntas que ese dato responde e indexarlas **junto al texto** | **NO.** Probé «etiquetas» indexadas aparte y puntuadas con `bm25`, que es otra cosa, y la falsé | `[conocimiento]` |
| **Reranking con cross-encoder** | segunda pasada que lee pregunta y candidato **juntos** y los reordena | **NO. Nunca lo hemos tocado.** | `[listado]` |
| **Híbrido léxico + vectorial con `RRF`** | fusionar dos rankings por puesto | Sí, construido y medido. **Inerte en este banco** | medido aquí |
| **Ampliación de consulta** | añadir sinónimos antes de buscar | Sí. Es lo único que ha mejorado: 24→26 exactos, 11→7 omisiones | medido aquí |

**Librería concreta para el reranking:** `AnswerDotAI/rerankers` `[listado]`, 1.628 estrellas, «API
unificada y de pocas dependencias para todos los modelos comunes de reranking y cross-encoder».
Activa este mes.

### Por qué HyDE es la primera que hay que probar

Porque ataca nuestra causa raíz **de frente**, y las otras no:

- la ampliación de consulta añade sinónimos, y esperamos que uno acierte;
- HyDE convierte la pregunta en **un texto del mismo género que lo guardado** —una afirmación—
  antes de comparar. La asimetría desaparece en vez de puentearse.

Y es barato de probar: ya tenemos el puerto de la fuente y el guion de medición. Es cambiar qué
texto se genera.

---

## 4. Bancos de prueba que existen y no estamos usando

| banco | qué mide | procedencia |
|---|---|---|
| **LoCoMo** | memoria en conversaciones muy largas | `[listado]` |
| **LongMemEval** | memoria de larga duración, varias sesiones | `[listado]` |
| **HaluMem** | alucinación en sistemas de memoria | `[listado]` |

Y arneses ya escritos para correrlos contra varios sistemas: `rivercrab26/mem-bench` `[listado]`
—«marco estandarizado para probar Mem0, Graphiti, Letta contra LongMemEval, LoCoMo, HaluMem»—.

**Lectura:** no sustituyen a nuestro banco, porque no puntúan las puertas. Pero un sistema que
vaya a entrar en Sirius debería traer su número en uno de estos, y hoy no sabemos el de ninguno.

---

## 5. Material de estudio ya recopilado

`NirDiamant/Agent_Memory_Techniques` `[listado]`, 853 estrellas, creado hace tres meses:
**30 cuadernos ejecutables** sobre memoria de agentes —búferes de conversación, almacenes
vectoriales, grafos de conocimiento, memoria episódica y semántica, MemGPT, Mem0, Letta, Zep,
Graphiti, benchmarks LoCoMo y patrones de producción—.

Es exactamente el mapa del terreno que hacía falta antes de construir nada.

---

## 6. Qué se hace con todo esto

| decisión | qué |
|---|---|
| **Probar ya, es barato** | **HyDE**. Ataca la causa raíz de frente y reusa el puerto y el guion que ya existen |
| **Probar ya, es barato** | **Reranking** con `rerankers`. Segunda etapa estándar que nunca hemos tocado |
| **Reimplementar bien** | **doc2query** en su forma publicada: preguntas generadas **dentro del mismo índice**, no etiquetas aparte. Lo que falsé no fue esto |
| **Leer antes de decidir** | los 30 cuadernos, y los números de `genome` sobre ingesta sin modelo y validez bi-temporal |
| **Adoptar solo si pasa tres filtros** | funciona sin red · no cuesta una llamada al modelo por elemento guardado · sus derivados se borran y se regeneran |
| **Seguirá siendo nuestro** | las puertas `G1`–`G12`, las paradas, la declaración de ausencia y la explicación por resultado. Nadie las hace |

**Lo que no se hace:** otro experimento casero antes de haber leído lo anterior.

---

## 7. Lo que este documento no puede decir

- No he leído el código de ninguno de estos proyectos. No puedo confirmar que hagan lo que dicen.
- No he ejecutado ninguno.
- Las filas `[conocimiento]` pueden estar desactualizadas.
- No sé qué números sacan en `LoCoMo` o `LongMemEval`, ni si son comparables entre sí.

Todo eso es exactamente lo que la investigación en abierto tiene que traer, y por eso va con el
prompt que acompaña a este documento.
