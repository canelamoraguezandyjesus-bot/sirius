# Prompt de investigación · memoria de asistente personal

> **RETIRADO.** Se retiro sin usarse. La via que proponia investigar quedo resuelta en local con un modelo propio, de modo que la investigacion dejo de hacer falta. Se conserva por trazabilidad.


**Cómo usarlo:** pégalo entero en una herramienta de investigación profunda (Deep Research de
ChatGPT o de Gemini, o Claude con búsqueda web). Está escrito para que devuelva una **decisión con
fuentes**, no un resumen bonito.

**Qué NO pide:** no pide que nos digan cómo construir una memoria. Pide que nos digan **qué ya
está construido y probado**, con números, y qué habría que hacer nosotros.

---

```
Necesito una investigación técnica para decidir la arquitectura de recuperación de la memoria
de un asistente personal. NO quiero un tutorial ni una explicación de qué es RAG. Quiero saber
QUÉ EXISTE YA, QUÉ RESULTADOS PUBLICADOS TIENE, y QUÉ DEBERÍAMOS ADOPTAR EN VEZ DE CONSTRUIR.

## El sistema

Asistente personal de escritorio, un solo usuario, en español. Guarda dos clases de cosas:
"memorias" (hechos y preferencias del usuario) y "decisiones" (acuerdos que pueden derogarse y
sustituirse). Cuando el usuario pregunta algo, el sistema tiene que recuperar exactamente los
elementos pertinentes de su propia memoria.

## Restricciones duras, y no son negociables

1. LOCAL. Aplicación de escritorio Windows sobre SQLite. Debe funcionar SIN CONEXIÓN. Puede
   llamar a un modelo remoto de forma opcional, pero no puede depender de ello para responder.
2. CORPUS PEQUEÑO. Cientos a decenas de miles de elementos, no millones. Cada elemento es una
   o dos frases, no documentos largos.
3. ESPAÑOL.
4. TODO DERIVADO DEBE PODER BORRARSE Y REGENERARSE. Si el usuario borra un dato, no puede
   quedar rastro en ningún índice, resumen, grafo ni vector. Y el derivado debe reconstruirse
   entero desde la fuente canónica.
5. COSTE DE INGESTA ACOTADO. Guardar una memoria no puede costar una llamada a un modelo de
   pago por elemento.

## Lo que el sistema debe garantizar, y que creo que ningún producto de memoria hace

- AISLAMIENTO POR ÁMBITO: lo de otro proyecto no puede aparecer nunca, ni siquiera para ser
  descartado.
- POLARIDAD PRESERVADA: "en este viaje se alquila coche" y "en este viaje NO se alquila coche"
  no pueden fundirse ni confundirse.
- VIGENCIA Y TIEMPO: lo derogado no vale; lo aplicable depende del instante por el que se
  pregunta; una decisión puede sustituir a otra.
- DECLARAR AUSENCIA SIN FILTRAR: poder decir "no tengo eso" sin revelar si existe algo que el
  usuario no puede ver.
- NUNCA PERDER UN ELEMENTO CRÍTICO EN SILENCIO: si algo marcado como crítico no se entrega, hay
  que declararlo explícitamente.
- EXPLICACIÓN POR RESULTADO: por qué salió cada elemento.
- NADA DE BARRIDOS: no recorrer la memoria entera para responder.

## Lo que ya hemos medido nosotros (banco propio de 47 casos, resultados reales)

- Búsqueda léxica sola (BM25 sobre SQLite FTS5): 24/47 respuestas exactas, 11 omisiones críticas.
- + embeddings densos (OpenAI text-embedding-3-small, 512 dims, umbral barrido de 0,25 a 0,65,
  fusión RRF): NUNCA supera la línea base. Recupera 1 omisión de 11 y pierde entre 3 y 5
  aciertos exactos. Por encima de coseno 0,55 es inerte.
- + ampliación de consulta con sinónimos escritos a mano: 26/47 y 7 omisiones. Es lo único que
  ha mejorado algo.
- Encima de la ampliación, los embeddings no aportan NADA: las omisiones se quedan en 7 en todos
  los umbrales y solo se pierden aciertos.

## La causa raíz que hemos identificado

Para los casos que fallan, la pregunta y el dato guardado NO COMPARTEN NI UNA PALABRA. Ejemplo
real: la pregunta es "¿hay evidencia de límite de gasto?" y el dato guardado es "El presupuesto
máximo del proyecto es 1.500 €". Cero solapamiento léxico. Además la pregunta es una PREGUNTA y
el dato es una AFIRMACIÓN: son géneros de texto distintos.

## Lo que quiero que investigues

### A. Técnicas para asimetría pregunta-documento

Para cada una: qué resultados publicados tiene, sobre qué datos, y si funciona con corpus
pequeños y en español.

1. HyDE (Hypothetical Document Embeddings): ¿cuánto mejora realmente? ¿En qué casos falla?
   ¿Hay evaluaciones independientes o solo el paper original?
2. doc2query / Doc-T5-Query (generar en la ingesta las preguntas que un documento responde):
   ¿números? ¿Coste? ¿Existe algo que no requiera un modelo entrenado en inglés?
3. Reranking con cross-encoder: ¿cuánto aporta sobre un híbrido léxico+vectorial? ¿Hay modelos
   multilingües pequeños que corran en CPU en un portátil?
4. ¿Alguna otra técnica ESTABLECIDA que ataque específicamente el solapamiento léxico cero?

Y una pregunta central: ¿hay evidencia publicada de que los embeddings densos rinden MAL en
corpus pequeños de frases cortas? Nuestro resultado apunta a eso y quiero saber si es conocido.

### B. Productos de memoria para agentes: cuál sobrevive a nuestras restricciones

Evalúa al menos: Mem0, Zep/Graphiti, Letta (MemGPT), Cognee, MemMachine, EverOS, Memori, memvid.

Para cada uno, responde exactamente esto:
- ¿Funciona sin conexión, de principio a fin?
- ¿Cuánto cuesta guardar un elemento? ¿Llama a un modelo por elemento?
- ¿Se puede borrar un dato y que no quede rastro en ningún derivado? ¿Está documentado?
- ¿Se puede regenerar el derivado entero desde la fuente?
- ¿Soporta validez temporal y sustitución de un dato por otro?
- ¿Distingue afirmación de negación?
- ¿Aísla por proyecto o espacio de forma dura?
- ¿Qué números publica en LoCoMo, LongMemEval o HaluMem, y quién los midió: ellos o un tercero?
- Licencia.

Descarta explícitamente los que no pasen las restricciones, y di por cuál.

### C. La parte que nadie resuelve

Confirma o desmiente esto: ¿existe algún sistema de memoria, abierto o comercial, que garantice
aislamiento por ámbito, polaridad preservada, vigencia temporal, declaración de ausencia sin
filtrado y ninguna pérdida silenciosa de elementos críticos? Si existe alguno, nómbralo. Si no
existe ninguno, dilo claramente: significa que esa capa la tenemos que construir nosotros sí o
sí, y quiero saberlo con certeza.

### D. Evaluación

- ¿Cómo se evalúa bien un sistema de memoria personal? ¿Qué bancos hay además de LoCoMo,
  LongMemEval y HaluMem?
- ¿Hay críticas publicadas a esos bancos? ¿Miden lo que dicen medir?
- ¿Alguno puntúa RECUPERACIÓN EXACTA de un conjunto, en vez de si la respuesta final del modelo
  era correcta?

## Cómo quiero la respuesta

1. UNA RECOMENDACIÓN AL PRINCIPIO, en cinco líneas: qué adoptar, qué implementar, qué ignorar.
2. Una tabla de los productos con las restricciones como columnas y un sí/no/desconocido en
   cada celda.
3. Una tabla de las técnicas con la mejora publicada y sobre qué datos se midió.
4. Distingue SIEMPRE lo que tiene evidencia publicada de lo que es material de marketing del
   propio proyecto. Si un número lo publica quien vende el producto, dilo.
5. Enlaces a las fuentes. Prefiero papers y repositorios a artículos de blog.
6. Si algo no lo encuentras, escribe "no encontrado". No rellenes huecos con plausibilidad.
7. Si crees que nuestro planteamiento está equivocado de raíz, dilo antes que nada.
```

---

## Qué haré yo con lo que traigas

- Si dice que HyDE o el reranking están probados, **los implemento y los mido en el banco** —los
  puertos ya están hechos, es enchufar—.
- Si aparece un producto que pasa los tres filtros —sin red, sin coste por elemento, derivados
  borrables y regenerables—, **paro y proponemos adoptarlo** en vez de seguir.
- Si confirma que nadie hace las puertas, deja de ser una sospecha y pasa a ser un hecho citado,
  y entonces las puertas son nuestras con razón escrita.
