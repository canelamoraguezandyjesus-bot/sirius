---
titulo: "Memoria para Sirius: cómo hacer que un robot compañero recuerde bien, rápido y durante años"
fecha: 2026-10-05
autor: "claude.ai con «Investigación», por encargo de la sesión del giro al robot (ADR-232)"
pregunta: >-
  Cómo diseñar la memoria de un robot compañero que recuerde bien y rápido durante
  años, y qué aprovechar y qué cambiar de la que ya tiene Sirius.

nota: >-
  Encargada por la sesión del giro al robot (ADR-232) y hecha en claude.ai con
  «Investigación», porque la sesión no tiene buscador; el propietario la pegó en la
  sesión el 05-10-2026. Texto íntegro tal como llegó, salvo lo personal: el nombre
  del propietario se ha cambiado por «el propietario», porque el repositorio es
  público. Las etiquetas de hecho, inferencia y opinión son del informe; la sesión
  no ha verificado sus fuentes.
caduca_con:
  - >-
    las cifras de bancos públicos y de vendedores que cita (LoCoMo, LongMemEval, HaluMem, Mem0, Zep, Letta)
  - >-
    los modelos de embeddings y sqlite-vec, y sus versiones
  - >-
    la capa de memoria de Sirius tal como estaba en main el 05-10-2026 (4ea76f35), que el informe no leyó: la describió el encargo

estado: VIGENTE
---

# Memoria para Sirius: cómo hacer que un robot compañero recuerde bien, rápido y durante años

La mejor manera de hacerlo es no cambiar de sistema. Amplía tu base de datos SQLite con cuatro cosas: un registro literal de todo lo que pasa, unas "fichas" de hechos con fecha de inicio y de fin, una búsqueda que mezcle significado, palabras y fecha, y una "limpieza nocturna" que resuma y revise. Adoptar Mem0, Letta o Graphiti tal cual no te conviene: las pruebas públicas no demuestran que sean claramente mejores que un buen sistema sencillo, y sus cifras las publican sobre todo los propios vendedores.

## TL;DR

- **Qué hacer:** conserva tu SQLite y conviértelo en la memoria de Sirius. Guarda siempre el texto original de cada conversación, que es la fuente de verdad. Encima, extrae hechos con fecha de validez ("vive en Madrid desde 2026, hasta ahora"). Busca por significado, por palabras y por fecha a la vez. Deja el resumen, la corrección de contradicciones y el olvido para un proceso nocturno, fuera de la conversación.
- **Por qué:** en las pruebas comparables, guardar el texto literal y recuperarlo bien rinde igual o mejor que extraer "recuerdos" con un modelo de lenguaje. Un estudio de Tao An (arXiv 2601.00821, v4 de julio de 2026) lo cifra en 67,4 % frente a 45,4 % en LongMemEval-S, y en 43,9 % frente a 28,0 % en LoCoMo. La extracción automática se equivoca a menudo: en HaluMem (arXiv 2511.03506), todos los sistemas salvo MemOS capturan menos del 60 % de los datos y todos aciertan menos del 62 %. Además, según la auditoría de Penfield Labs (2026), el principal banco de pruebas del sector, LoCoMo, tiene 99 de 1.540 respuestas "correctas" (6,4 %) que son erróneas.
- **Robot y PC:** Sirius no se mueve, así que no necesita mapas 3D ni SLAM. Le basta una "memoria de escena" desde un punto fijo (qué objeto vio, dónde y cuándo) y fichas de personas con huella de cara y de voz. Con cualquiera de los tres PC, la búsqueda local en memoria tarda milisegundos. Lo que cambia según la GPU es dónde se ejecuta el modelo que extrae y resume: en la nube si no hay GPU, y en local de noche con 8–12 GB o con 16–24 GB.

---

## Cómo leer este informe

- **[HECHO]**: algo que dice una fuente concreta, con su nombre y fecha.
- **[INFERENCIA]**: una deducción mía a partir de las fuentes.
- **[OPINIÓN]**: mi criterio como investigador. Puedes no estar de acuerdo.
- Las cifras de un vendedor sobre su propio producto se marcan como **(vendedor)**.
- Cada sección empieza con "En pocas palabras". La sección 7 (arquitectura recomendada) se entiende sola.

Primeros términos que conviene saber:
- **Modelo de lenguaje (LLM):** el programa que "habla", por ejemplo GPT, Claude o un modelo de Ollama.
- **Token:** un trozo de palabra. Unas 100 palabras en español son aproximadamente 130–150 tokens.
- **Contexto:** todo el texto que el LLM lee en cada turno. Tiene un tamaño máximo.
- **Latencia:** el tiempo de espera hasta que llega la respuesta.

---

## 1. Arquitecturas de memoria (2023–2026): qué existe y qué funciona

**En pocas palabras:** casi todos los sistemas combinan las mismas piezas. Hay un "bloc de notas" siempre visible, un diario de lo ocurrido, unas fichas de hechos y, a veces, un grafo. Lo que de verdad funciona es más sencillo de lo que sugiere el marketing. Las comparaciones públicas entre Mem0, Zep y Letta acabaron en polémica porque cada uno se medía a su manera.

### 1.1 Los cuatro tipos de memoria

- [HECHO] El marco CoALA (Sumers y otros, arXiv 2309.02427, septiembre de 2023) divide la memoria de un agente en cuatro tipos:
  - **De trabajo:** lo que está en el contexto ahora mismo.
  - **Episódica:** lo que pasó, como un diario.
  - **Semántica:** hechos y conocimiento ("a Pablo le gusta el café sin azúcar").
  - **Procedimental:** cómo se hacen las cosas, es decir, habilidades y reglas.
- [HECHO] El survey "Memory in the Age of AI Agents" (arXiv 2512.13564, diciembre de 2025) reúne el campo hasta finales de 2025. Lo citan muchos trabajos de 2026.
- [INFERENCIA] Para Sirius, los cuatro tipos se corresponden con cosas concretas:
  - De trabajo: el turno actual y el perfil fijo.
  - Episódica: conversaciones y eventos vistos u oídos.
  - Semántica: las fichas de personas, gustos, lugares y objetos.
  - Procedimental: rutinas y "lo que ha aprendido a hacer", por ejemplo "a Pablo se le saluda en voz baja por la mañana".

### 1.2 Generative Agents (Park y otros, 2023)

- [HECHO] El artículo es "Generative Agents" (arXiv 2304.03442, v2 del 6 de agosto de 2023; UIST 2023). Cada observación se guarda en un "flujo de memoria". Para recuperar recuerdos se suman tres puntuaciones normalizadas entre 0 y 1, con el mismo peso (α = 1):
  - **Recencia:** decae de forma exponencial con un factor 0,995 por cada hora de juego desde la última vez que se recuperó el recuerdo.
  - **Importancia:** un LLM la puntúa del 1 al 10 al crear el recuerdo. Por ejemplo, "limpiar la habitación" = 2 y "pedir una cita a quien te gusta" = 8.
  - **Relevancia:** la similitud coseno entre el recuerdo y la consulta.
- [HECHO] La **reflexión** se dispara cuando la suma de importancias de los eventos recientes supera 150. En la práctica ocurría "dos o tres veces al día". El agente lee los 100 registros más recientes, se hace 3 preguntas y saca 5 conclusiones de alto nivel.
- [HECHO] Las ablaciones (quitar piezas para ver cuánto aportan) las puntuaron 100 evaluadores con TrueSkill:

| Variante | Credibilidad (μ) |
|---|---|
| Arquitectura completa | 29,89 |
| Sin reflexión | 26,88 |
| Sin reflexión ni planificación | 25,64 |
| Humanos que interpretaban a los agentes | 22,95 |
| Sin memoria, reflexión ni planificación | 21,21 |

- [HECHO] La diferencia entre la versión completa y la que no tenía memoria fue de d = 8,16 desviaciones típicas. El experimento, con 25 agentes durante 2 días de juego, costó "miles de dólares" en tokens.
- [INFERENCIA] La fórmula recencia + importancia + relevancia sigue siendo una buena base. Ojo: se midió la "credibilidad" del comportamiento, no si el agente acertaba datos concretos. Y la reflexión a cada rato sale cara. En Sirius conviene hacerla de noche.

### 1.3 MemGPT / Letta

- [HECHO] MemGPT (Packer y otros, arXiv 2310.08560, octubre de 2023) trata el contexto como la memoria RAM de un ordenador y el almacenamiento externo como el disco. Tiene tres partes:
  - **Memoria núcleo:** bloques siempre visibles, como un perfil del usuario y la personalidad del agente.
  - **Memoria de recuerdo:** el historial de la conversación, que se puede buscar.
  - **Memoria de archivo:** un almacén largo que también se puede buscar.
  El propio modelo "pagina", es decir, decide qué sube al contexto y qué baja, llamando a herramientas.
- [HECHO] **Sleep-time compute**, de Letta (blog y arXiv 2504.13171, abril de 2025), separa el trabajo en dos agentes. Uno conversa. El otro, el "agente de sueño", reorganiza la memoria en segundo plano. Letta lo incluyó en su versión 0.7.0 y dice que así mejoran la latencia y la calidad de la memoria **(vendedor)**. El propio artículo advierte que el cálculo previo ayuda más cuando las preguntas futuras se pueden prever a partir del contexto existente.
- [HECHO] En agosto de 2025, Letta publicó "Benchmarking AI Agent Memory: Is a Filesystem All You Need?". Su agente obtuvo un 74,0 % en LoCoMo con solo guardar el historial en un archivo, por encima de librerías de memoria especializadas **(vendedor)**.
- [HECHO] Sus últimas publicaciones van en la misma línea. En febrero de 2026 presentó "Context Repositories", memoria versionada con git para agentes de programación. En junio de 2026 publicó "Memory Models", modelos entrenados para crear recuerdos durante el "sueño". En julio de 2026, "Evaluating Memory in Production Agents".

### 1.4 Mem0 y Mem0g

- [HECHO] Mem0 (Chhikara y otros, arXiv 2504.19413, abril de 2025; ECAI 2025) **(vendedor)** funciona así. Tras cada intercambio, un LLM extrae hechos candidatos. Luego los compara con los recuerdos parecidos y elige una operación: **ADD** (añadir), **UPDATE** (actualizar), **DELETE** (borrar) o **NOOP** (no hacer nada). Mem0g añade además un grafo de entidades y relaciones.
- [HECHO] Sus resultados en LoCoMo, medidos por ellos, comparando la puntuación J (un LLM hace de juez) y la latencia:

| Método | J | Búsqueda p50 / p95 | Total p50 / p95 | Tokens por conversación |
|---|---|---|---|---|
| Mem0 | 66,88 % | 0,148 s / 0,200 s | 0,708 s / 1,440 s | ~1,7 mil |
| Mem0g | 68,44 % | 0,476 s (p50) | 1,091 s / 2,590 s | ~3,6 mil |
| Contexto completo | 72,9 % | — | 9,87 s / 17,12 s | ~26 mil |
| LangMem | — | 17,99 s / 59,82 s | — | — |

- [INFERENCIA] Fíjate: en la tabla del propio Mem0, **pasar toda la conversación al modelo acierta más** (72,9 %) que Mem0. Lo que gana Mem0 es velocidad y coste, no exactitud.
- [HECHO] Las latencias cambian mucho según quién mida. En MemOS (arXiv 2507.03724, julio de 2025), un competidor, la búsqueda de Mem0 dio 1.297 ms de p50. En "User as Code" (arXiv 2606.16707, 2026), la respuesta con contexto completo tardó 1,78 s de mediana y la de Mem0, 2,19 s.

### 1.5 Zep / Graphiti (grafo temporal)

- [HECHO] Zep (Rasmussen y otros, arXiv 2501.13956, enero de 2025) **(vendedor)** se basa en Graphiti, un **grafo de conocimiento** (personas, cosas y conceptos unidos por relaciones) que es **bitemporal**. Cada hecho guarda dos tiempos:
  - Cuándo fue verdad en el mundo: `valid_at` y `invalid_at`.
  - Cuándo lo supo el sistema: `created_at` y `expired_at`.
  Si llega un hecho que contradice a otro, el antiguo no se borra: se marca como inválido desde esa fecha. Zep obtuvo un 94,8 % en DMR, frente al 93,4 % de MemGPT. En LongMemEval declaró mejoras de exactitud de hasta el 18,5 % y un 90 % menos de latencia.
- [HECHO] Los repositorios oficiales de Graphiti en GitHub documentan problemas reales:
  - La incidencia #1728 dice que la invalidación busca en todo el grafo, de modo que hechos sin relación se "jubilan" entre sí. En un grafo de producción, 1.616 de unos 3.950 hechos (41 %) estaban invalidados.
  - La incidencia #1666 mide que, con un modelo pequeño sin razonamiento, la detección de contradicciones acertó 1 de 9 veces.
- [INFERENCIA] La idea bitemporal es excelente y barata de copiar en SQLite. Delegar en un LLM la decisión de qué hecho anula a otro es frágil, sobre todo con modelos locales pequeños.

### 1.6 La polémica Mem0–Zep–Letta sobre LoCoMo

- [HECHO] Mem0 publicó que Zep sacaba un 65,99 % en LoCoMo. El 6 de mayo de 2025, Zep respondió en su blog con "Lies, Damn Lies, & Statistics: Is Mem0 Really SOTA in Agent Memory?", donde decía que bien configurado obtenía un 84 %. Después lo corrigió al 75,14 % ± 0,17, porque había contado mal una categoría de preguntas. Según el ensayo "The Benchmark Theatre" de Dell Zhang (20 de mayo de 2026), el CTO de Mem0, Deshraj Yadav, lo recalculó en una incidencia de GitHub en el 58,44 % ± 0,20 (10 semillas) con la propia configuración de Zep; el ensayo explica que Zep había incluido la categoría 5 en el numerador pero no en el denominador, lo que inflaba la cifra unos 25 puntos. Letta, por su parte, sacó el 74,0 % con un simple archivo.
- [INFERENCIA] La misma herramienta tiene cuatro cifras distintas según quién la mida. Las comparaciones entre vendedores en LoCoMo **no sirven para decidir**.

### 1.7 Otros sistemas (2023–2026)

| Sistema | Idea principal | Comentario útil para Sirius |
|---|---|---|
| MemoryBank (arXiv 2305.10250, 2023) | Olvido según la curva de Ebbinghaus: los recuerdos se refuerzan al usarse | Buena idea para dar prioridad, mala para borrar de verdad |
| A-MEM (arXiv 2502.12110, 2025) | Notas enlazadas al estilo Zettelkasten que se reescriben solas | En la tabla de HaluMem, QA 43,02 % |
| LangMem (LangChain, 2025) | Memoria semántica, episódica y procedimental como herramientas | En la tabla de Mem0, búsqueda de 17,99 s de p50: demasiado lenta para la voz |
| HippoRAG 2 ("From RAG to memory", arXiv 2502.14802, 2025) | Grafo y PageRank, inspirado en el hipocampo | Útil para preguntas que encadenan varios datos |
| MemoryOS (arXiv 2506.06326, 2025) / MemOS (arXiv 2507.03724, 2025) | La memoria como un "sistema operativo" con niveles | MemOS: QA 67,23 % en HaluMem |
| MIRIX (arXiv 2507.07957, 2025) | Seis tipos de memoria y varios agentes | Complejo para una persona sola |
| Memory-R1 (arXiv 2508.19828, 2025) | Aprende por refuerzo qué operaciones ADD/UPDATE/DELETE hacer | Requiere entrenamiento |
| Nemori (arXiv 2508.03341, 2025) | Segmenta la conversación en episodios, como la mente humana | La segmentación en episodios encaja bien con un robot |
| LightMem (arXiv 2510.18866, 2025) | Memoria ligera con consolidación "en sueño" fuera de línea | En la línea de lo que recomiendo |
| TiMem (enero de 2026) | Árbol temporal de memorias | 76,88 % en LongMemEval-S con GPT-4o-mini, según su autor |
| Cognee, Memobase | Grafo y perfiles de usuario | Memobase: QA 35,33 % en HaluMem |

- [HECHO] Sobre la memoria de ChatGPT, Claude y Gemini, o de apps compañeras como Replika y Character.AI, no encontré documentación técnica fiable y verificable sobre su funcionamiento interno. El único dato medido que tengo es de LongMemEval (2024): la exactitud de ChatGPT bajó un 37 % y la de Coze un 64 % al pasar a sesiones largas reales.

### 1.8 ¿Lo sencillo rinde igual?

- [HECHO] "Fidelity Before Structure" (Tao An, arXiv 2601.00821, v4 de julio de 2026) comparó dos formas de guardar la información con el mismo buscador y el mismo modelo que responde. Guardar **trozos literales** de la conversación dio un 67,4 % en LongMemEval-S y un 43,9 % en LoCoMo. Guardar **artefactos extraídos** por un LLM dio un 45,4 % y un 28,0 %. Los trozos fueron por delante en las cinco categorías, aunque la diferencia solo fue significativa en tres: extracción (+34,0 puntos), varias sesiones (+28,1) y razonamiento temporal (+14,2). Añadir un reranker subió la exactitud solo 0,6 puntos en LongMemEval y 2,9 en LoCoMo.
- [HECHO] MemoryAgentBench (arXiv 2507.05257; ICLR 2026) encontró que la búsqueda (RAG) gana en recuperar datos exactos, pero pierde en resumir globalmente. Según sus autores (Hu, Wang y McAuley, v4 de junio de 2026), "los métodos actuales no llegan a dominar las cuatro competencias" que mide.
- [OPINIÓN] La conclusión práctica es esta: **guarda siempre el original y extrae fichas como un índice encima, nunca como sustituto.** Así, un error de extracción se puede corregir volviendo a la fuente.

---

## 2. Recuperación rápida

**En pocas palabras:** en cada turno, el modelo debe leer poco y bueno: un perfil fijo, un resumen reciente y 5–10 recuerdos elegidos. Llenar el contexto empeora las respuestas. Para elegir esos recuerdos, conviene combinar búsqueda por significado, por palabras y por fecha. En local, buscar entre cien mil recuerdos tarda milisegundos. Lo lento es el LLM.

### 2.1 Qué entra en el contexto

- [HECHO] "Lost in the middle" (Liu y otros, 2023; TACL 2024): los modelos aciertan más cuando el dato está al principio o al final del contexto, y pierden más de un 30 % cuando está en el medio.
- [HECHO] "Context Rot" (Chroma Research: Hong, Troynikov y Huber, julio de 2025) probó 18 modelos punteros, entre ellos GPT-4.1, Claude 4, Gemini 2.5 y Qwen3. **Todos empeoraron** al crecer la entrada, mucho antes de llenar su ventana. En su prueba con LongMemEval, todos fallaron más con entradas de unos 113.000 tokens que con la versión corta y relevante.
- [INFERENCIA] El presupuesto razonable por turno para Sirius, unos 2.000–4.000 tokens de memoria, sería este:
  1. Perfil fijo de la persona que habla y "quién soy yo, Sirius": unos 300–600 tokens.
  2. Resumen de hoy y de la última conversación: unos 300–500.
  3. Últimos 6–10 turnos literales.
  4. De 5 a 10 recuerdos recuperados, cada uno con fecha y origen.
  Pon lo más importante al principio o al final, no en medio.

### 2.2 Búsqueda híbrida

- **Embedding:** convierte un texto en una lista de números (un "vector") que representa su significado. Dos textos parecidos dan vectores cercanos.
- **BM25 / FTS5:** búsqueda clásica por palabras. SQLite la trae de serie con FTS5.
- **RRF (Reciprocal Rank Fusion):** mezcla varias listas de resultados según la posición que ocupa cada resultado en cada lista.
- **Reranker:** un modelo que relee los 20–50 candidatos y los reordena con más cuidado.
- [INFERENCIA] Flujo recomendado:
  1. Filtrar por persona y fecha si la pregunta lo pide ("el martes").
  2. Buscar los 30 más parecidos por embedding y los 30 mejores por FTS5.
  3. Fusionar con RRF.
  4. Sumar importancia y recencia, al estilo Park.
  5. Usar el reranker opcionalmente, porque su ganancia medida fue pequeña (+0,6 puntos en LongMemEval y +2,9 en LoCoMo en arXiv 2601.00821).
- [HECHO] En LongMemEval (arXiv 2410.10813; ICLR 2025), restringir la búsqueda por tiempo mejoró las preguntas temporales. Los diseños de memoria simples fallan en ese tipo de preguntas.

### 2.3 Modelos de embeddings y rerankers locales

| Modelo | Tamaño | Dimensiones | Datos clave (fuente y fecha) |
|---|---|---|---|
| EmbeddingGemma | 308M | 768 (recortable a 512/256/128) | Google, septiembre de 2025: el mejor modelo abierto multilingüe por debajo de 500M en MTEB; menos de 200 MB de RAM cuantizado; menos de 15 ms por texto de 256 tokens en EdgeTPU; está en Ollama; licencia Gemma (no Apache) |
| Qwen3-Embedding-0.6B | 0,6B | hasta 1024 | arXiv 2506.05176, junio de 2025: MMTEB 64,33; 32K de contexto; Apache 2.0 |
| Qwen3-Embedding-4B | 4B | hasta 2560 | MMTEB 69,45 |
| Qwen3-Embedding-8B | 8B | hasta 4096 | MMTEB 70,58, número 1 a 5 de junio de 2025 |
| bge-m3 | ~568M | 1024 | Muy usado en multilingüe; hace búsqueda densa y por palabras |
| multilingual-e5-small | ~21M (núcleo) | 384 | Antiguo pero rapidísimo en CPU |
| Qwen3-Reranker 0.6B / 4B / 8B | 0,6–8B | — | MMTEB-R del 4B: 72,74 |

- [INFERENCIA] Elige **un solo** modelo de embeddings y no lo cambies a la ligera: si lo cambias, tendrás que recalcular todos los vectores. Guarda en la base de datos qué modelo y qué versión generó cada vector. Para español, Qwen3-Embedding-0.6B o EmbeddingGemma son las opciones equilibradas. Comprueba en tu propio banco de pruebas (sección 5) cuál acierta más con tus frases.

### 2.4 Bases de datos vectoriales en Windows con Python

- [HECHO] sqlite-vec (Alex García, versión v0.1.0, agosto de 2024) es una extensión de SQLite que funciona en Windows y hace búsqueda exacta por fuerza bruta. Con 100.000 vectores es usable. Con **1 millón**, ningún vector de tipo float bajó de 100 ms: los de 3.072 dimensiones tardaron 8,52 s y los de 192 dimensiones, 192 ms.
- [HECHO] Una comparativa de un tercero (Kanopy Labs, sin fecha clara, no verificada) da unos 5 ms con 100.000 vectores en sqlite-vec y unos 45 ms con 1 millón. Según la misma fuente, LanceDB y Chroma son más rápidos a gran escala.
- [HECHO] SuperLocalMemory (arXiv 2603.02240, 2026) mide unos 1,4 KB por recuerdo en SQLite: 13,6 MB para 10.000 recuerdos, sin contar los vectores.
- [INFERENCIA] Una persona habla con Sirius quizá 50–200 frases al día. En 5 años serían unos 100.000–350.000 fragmentos. **sqlite-vec basta**, y además vive en tu misma base de datos, con transacciones y JOIN con tus tablas. Si algún día pasas del millón de vectores, LanceDB es el salto natural. Qdrant local, FAISS, Chroma y DuckDB son alternativas válidas, pero añaden una segunda base de datos que sincronizar.
- [INFERENCIA] Tamaño en disco a 5 años: unos 300.000 recuerdos × (1,4 KB de texto + 4 KB de vector float32 de 1024 dimensiones) ≈ 1,6 GB. Con vectores de 768 dimensiones en int8 bajaría a unos 0,7 GB. Las fotos y el audio, si los guardas, ocuparían mucho más que todo eso.

### 2.5 Presupuesto de latencia para la voz

- [HECHO] En la conversación humana, el hueco medio entre turnos ronda los 200 ms en 10 idiomas (Stivers y otros, PNAS, 2009). Un trabajo de 2026 (HEART, arXiv 2601.19922) fija como objetivo práctico que el modelo empiece a responder en unos 500 ms. Detectar que la persona terminó de hablar y transcribirlo cuesta 150–300 ms, y la voz sintética, otros 100–200 ms.
- [HECHO] En un conjunto de datos de 2026 con agentes comerciales de vídeo y voz (DeepSpeak-Agentic, arXiv 2606.03686), la latencia media fue de 3,79 s, muy por encima de lo natural.
- [INFERENCIA] La memoria debería costar **menos de 100–150 ms por turno**, y es factible:
  - Calcular el embedding de la pregunta: decenas de ms en GPU y del orden de 50–150 ms en CPU con un modelo pequeño. Mídelo en tu PC.
  - sqlite-vec con 100.000 vectores: milisegundos.
  - FTS5: milisegundos.
  Lo que **no** cabe en el turno es extraer recuerdos con un LLM, que tarda segundos. Eso se hace después de responder o de noche. Un truco útil: mientras la persona aún habla, lanza ya la búsqueda con la transcripción parcial.

### 2.6 Qué cabe en local según el PC

**VRAM** es la memoria propia de la tarjeta gráfica. **Cuantizar** es comprimir el modelo (por ejemplo, Q4 usa unos 4 bits por parámetro) para que ocupe menos a cambio de perder un poco de calidad.

| Pieza | Sin GPU dedicada | GPU 8–12 GB | GPU 16–24 GB |
|---|---|---|---|
| Embeddings | EmbeddingGemma o Qwen3-Emb-0.6B en CPU | Qwen3-Emb-0.6B en GPU | Qwen3-Emb-0.6B o 4B en GPU |
| Reranker | Ninguno, o uno 0.6B solo de noche | Qwen3-Reranker-0.6B | Qwen3-Reranker-0.6B o 4B |
| LLM de conversación | Nube | Nube, o local de 7–8B en Q4 (unos 5 GB) | Nube, o local de 14B en Q4 / 24–32B en Q4 justo |
| Extracción y consolidación nocturna | Nube (barato con un modelo pequeño de API) | Local de 7–8B en Q4, de noche | Local de 14–32B en Q4, de noche |
| Visión: caras y objetos | CPU: pocas imágenes por segundo | GPU: tiempo real | GPU: tiempo real y un modelo de visión-lenguaje local |

- [INFERENCIA] Las cifras de VRAM son estimaciones (aproximadamente 0,6 GB por cada mil millones de parámetros en Q4, más el contexto). Compruébalas con Ollama en tu máquina. Ten en cuenta que, de noche, el LLM local no compite con la conversación, así que puede ser más grande y más lento.

---

## 3. Consolidar, evitar recuerdos falsos y corregir

**En pocas palabras:** resumir y "dormir" ayuda. El gran peligro es que el LLM invente o malinterprete al extraer recuerdos, y eso pasa a menudo. La defensa es guardar el original, anotar quién dijo cada cosa y con qué seguridad, no borrar sino marcar como "ya no válido", y dejar que tú corrijas por voz.

### 3.1 Resumir, jerarquías y "dormir"

- [HECHO] Letta (sleep-time compute, abril de 2025) y LightMem (arXiv 2510.18866, octubre de 2025) sacan la consolidación del camino crítico de la conversación y la pasan a un proceso fuera de línea.
- [INFERENCIA] Para Sirius, una jerarquía sencilla:
  - Turnos literales.
  - Episodio: una conversación o una "escena", con su resumen.
  - Resumen del día.
  - Resumen de la semana o el mes.
  - Fichas de hechos (semántica) y rutinas (procedimental).
  Cada nivel enlaza con los de abajo, de modo que siempre se puede volver al original.

### 3.2 Olvidar

- [HECHO] MemoryBank (2023) aplica la curva de Ebbinghaus: un recuerdo pierde fuerza con el tiempo y se refuerza cada vez que se usa.
- [OPINIÓN] Distingue entre **bajar de prioridad**, que se puede hacer automáticamente, y **borrar**, que debe ser una decisión tuya (ver la sección 8). Con 1–2 GB a 5 años, el espacio no obliga a borrar nada.

### 3.3 Recuerdos falsos: el problema principal

- [HECHO] HaluMem (Chen y otros, arXiv 2511.03506, v3 del 5 de enero de 2026) mide las alucinaciones en cada fase: extraer, actualizar y responder. En extracción, todos los sistemas probados salvo MemOS (74,07 %) tienen una cobertura de datos inferior al 60 %, y todos tienen una exactitud inferior al 62 % (Mem0: 42,91 % de cobertura y 60,86 % de exactitud, según su tabla 3). Los errores nacen al extraer y actualizar, y se propagan a las respuestas. Todos empeoran con historiales largos.
- [HECHO] En la tabla de HaluMem recogida por arXiv 2601.04463 (enero de 2026), la exactitud de las respuestas fue: Mem0 53,02 %, MemOS 67,23 %, Supermemory 54,07 %, A-Mem 43,02 %, MemoryOS 39,24 % y Memobase 35,33 %.
- [INFERENCIA] Las causas típicas en un robot son:
  - Atribuir a la persona algo que dijo el propio Sirius.
  - Tomar una broma o una hipótesis ("imagínate que me mudo") como un hecho.
  - Confundir lo que dijo una visita con lo que dijiste tú.
  - Guardar algo que se leyó en internet como si fuera un dato personal.
  - Que el reconocimiento de voz transcriba mal.
- [OPINIÓN] Reglas para evitarlo:
  1. Cada recuerdo guarda su **procedencia**: quién lo dijo, en qué turno, por qué canal (voz, cámara o web) y con qué confianza de reconocimiento de hablante.
  2. Solo se convierten en "hecho" las afirmaciones de la persona sobre sí misma o confirmadas. Lo que dice Sirius nunca es fuente de hechos sobre el usuario.
  3. Si la confianza es baja, se guarda como "posible" y se confirma con naturalidad: "¿Al final te mudaste?".
  4. La extracción usa un modelo bueno, de noche, con el texto original delante.

### 3.4 Contradicciones y hechos que cambian

- [HECHO] Zep/Graphiti (enero de 2025) usa el modelo bitemporal: el hecho viejo se cierra con fecha de fin en lugar de borrarse. Así se puede responder tanto "¿dónde vive ahora?" como "¿dónde vivía en 2025?".
- [HECHO] MemoryAgentBench (ICLR 2026): en resolución de conflictos de un solo paso, los agentes con GPT-4o aciertan alrededor del 60 %.
- [HECHO] Las incidencias #1728 y #1666 de Graphiti muestran invalidaciones erróneas masivas cuando un LLM pequeño decide qué contradice a qué.
- [OPINIÓN] Que el LLM **proponga** la contradicción, pero que la regla para aplicarla sea fija y limitada: solo entre hechos de la misma persona y el mismo atributo (por ejemplo, persona = Pablo, atributo = ciudad). Si la confianza es baja, se pregunta en vez de aplicar el cambio.

### 3.5 Corregir y borrar por voz

- [OPINIÓN] Tres órdenes con efectos distintos:
  - **"Eso no es así"**: cierra el hecho (`invalid_at = ahora`), crea el hecho correcto y anota "corregido por el usuario", que es la máxima confianza.
  - **"Olvida eso"**: borrado real del hecho, de sus vectores, de los resúmenes que lo contengan y de las copias de seguridad en su próxima rotación. Deja solo una línea de registro sin contenido.
  - **"¿Qué sabes de mí?"**: lee las fichas y permite revisarlas.
- [INFERENCIA] Tu versionado de decisiones actual vale para la parte de "eso no es así". El "olvida eso" exige además poder buscar y regenerar los resúmenes derivados. Por eso cada resumen debe enlazar con sus fuentes.

### 3.6 Seguridad: envenenamiento de la memoria

- [HECHO] MINJA (arXiv 2503.03704, 2025) consiguió introducir registros maliciosos en la memoria de agentes solo con preguntas normales: un 98,2 % de inyecciones con éxito y un 76,8 % de ataques con éxito. Un estudio posterior (arXiv 2601.05504, enero de 2026), en condiciones más realistas, bajó el éxito del ataque al 38 % con GPT-4o-mini y al 28 % con Llama en el mejor caso para el atacante.
- [HECHO] AgentPoison (2024) envenena bases de conocimiento. El blog de Mem0 **(vendedor)** le atribuye más del 80 % de éxito.
- [INFERENCIA] En casa, el riesgo real son visitas, niños, la televisión o la radio y páginas web que Sirius lea. Medidas:
  - Las instrucciones ("a partir de ahora haz X") solo se guardan si las da una persona reconocida con permiso.
  - El texto que venga de la web o de la televisión nunca se convierte en hecho ni en regla.
  - La memoria procedimental se revisa a mano.

---

## 4. Memoria propia de un robot de sobremesa

**En pocas palabras:** como Sirius no se mueve, los mapas 3D y el SLAM no tienen sentido hoy. Basta con una memoria de "escena fija": qué vi, en qué dirección del cuello y cuándo. Las personas se reconocen por su huella de cara y de voz, enlazada a su ficha. Todo comparte el mismo esquema de entidades que la conversación.

### 4.1 ¿Mapas, SLAM, grafos de escena 3D?

- [HECHO] ReMEmbR (NVIDIA, arXiv 2409.13682, septiembre de 2024; ICRA 2025) guarda descripciones de vídeo cada pocos segundos, junto con la posición y la hora, en una base vectorial. Responde preguntas como "¿dónde viste mi móvil?", y se probó con vídeos de hasta 20 minutos. STaR (arXiv 2602.09255, 2026) critica que esas descripciones se vuelven redundantes cuando el robot vuelve a ver lo mismo.
- [HECHO] Los grafos de escena 3D (ConceptGraphs, HOV-SG, Hydra) están pensados para robots que recorren espacios. Según STaR, siguen siendo sobre todo estáticos y centrados en objetos.
- [OPINIÓN] Para Sirius, lo adecuado es:
  - **Memoria de escena desde un punto fijo:** para cada observación guarda la dirección del cuello (pan y tilt), los objetos detectados, una descripción breve y la hora.
  - **Tabla de "último avistamiento":** objeto → dónde (dirección y zona: "la mesa de la izquierda") → cuándo → con qué confianza.
  - **Los lugares son conceptos de la conversación** ("la casa de mi madre", "la oficina"), no mapas.
  - Para evitar la redundancia de ReMEmbR, guarda solo los **cambios** ("apareció una taza", "se fue Pablo"), no cada fotograma.
  - **Camino de mejora:** si algún día se mueve, añade un campo `pose` (posición y orientación) y una tabla de "zonas". Un grafo de escena se puede montar encima de esas mismas entidades.

### 4.2 Reconocer personas

- **Huella (embedding biométrico):** un vector que resume una cara o una voz. Dos huellas de la misma persona quedan cerca.
- [HECHO] Cara: ArcFace (Deng y otros, arXiv 1801.07698; versión TPAMI de 2021) produce huellas de 512 dimensiones. Tarda 8,9 ms por cara con ResNet50, en un hardware que el artículo no especifica y que probablemente es una GPU. El paquete `buffalo_l` de InsightFace ocupa 326 MB. Sus modelos son "solo para investigación no comercial". Un uso de hobby encaja, pero confírmalo. Hay paquetes pequeños: `buffalo_s`, de 159 MB, y `buffalo_sc`, de 16 MB. Funciona en CPU con onnxruntime.
- [HECHO] Voz: el modelo ECAPA-TDNN de SpeechBrain (`spkrec-ecapa-voxceleb`, Apache 2.0) produce huellas de 192 dimensiones, con un 0,80 % de tasa de error igual en VoxCeleb1. En CPU, con un solo hilo, un ECAPA de tamaño similar tiene un factor de tiempo real de 0,033 (CAM++, arXiv 2303.00332, 2023). Es decir, unos 33 ms por cada segundo de audio, según mi cálculo.
- [INFERENCIA] Las dos cosas caben en un PC sin GPU si analizas la cara solo cuando cambia la escena y la voz solo al final de cada frase. Guarda **varias huellas por persona** (con gafas, sin gafas, voz ronca...), y fija dos umbrales: "seguro" y "dudoso → preguntar".
- [INFERENCIA] Objetos: un detector de tipo YOLO funciona en CPU a pocas imágenes por segundo y en GPU en tiempo real. Un detector de vocabulario abierto, o un modelo local de visión-lenguaje (que describe imágenes con texto), es mejor para "cosas raras", pero pesa más. Conviene usarlo a demanda o en GPU de 16–24 GB.

### 4.3 Unirlo todo: un esquema común

- [OPINIÓN] Usa una sola tabla de **entidades** con un identificador único y estos tipos: persona, lugar, objeto, evento, Sirius.
  - La conversación ("Pablo dejó las llaves en la entrada") y la cámara (llaves vistas a las 18:02 en la dirección 30°) apuntan a las **mismas** entidades.
  - Un **episodio multimodal** guarda qué oyó (la transcripción y el hablante), qué vio (objetos y caras), qué dijo y qué hizo Sirius. Todo con sus horas e identificadores.

### 4.4 Lo que dicen los estudios de interacción humano-robot (HRI)

- [HECHO] "Not Forgotten" (arXiv 2607.24190, julio de 2026) estudió la cabeza robótica Kim, con memoria episódica sobre un LLM. Fue un estudio intra-sujetos con 43 personas. La memoria aumentó la sociabilidad percibida (d = 0,60) sin aumentar la incomodidad (d = 0,00). Los propios autores piden estudios largos, porque el efecto novedad limita los resultados.
- [HECHO] En un experimento de 2023 (Int. J. of Social Robotics, Springer), los participantes hablaron 10 veces con Pepper durante 5 semanas, y la duración de lo que contaban de sí mismos fue creciendo con las sesiones. Un estudio de 2025 sobre el robot MOCCA (Applied Sciences) halló que el riesgo de privacidad percibido reduce la confianza.
- [HECHO] Una revisión de 2026 ("Responsible Personalisation", arXiv 2607.06344) advierte de la "paradoja privacidad–personalización". Avisa también de que el robot puede revelar datos a terceros solo por cómo se comporta o por lo que dice en voz alta delante de otros.
- [OPINIÓN] Buenas prácticas para Sirius:
  - Que no suelte datos privados delante de visitas.
  - Que diga de dónde sabe algo ("me lo contaste el martes").
  - Que tenga un modo "no recordar".
  - Que muestre algo visible, como un LED, cuando graba o reconoce.

### 4.5 Privacidad y ley (España/UE)

- [HECHO] El RGPD excluye las actividades "exclusivamente personales o domésticas" (art. 2.2.c). El Tribunal de Justicia la interpreta de forma estricta (sentencia Ryneš, C-212/13, 11 de diciembre de 2014). Las Directrices 3/2019 del CEPD sobre vídeo (adoptadas el 10 de julio de 2019) recogen esa lectura estrecha.
- [HECHO] Según esas directrices, el vídeo solo es dato biométrico (categoría especial, art. 9) cuando se procesa técnicamente para identificar a una persona, que es exactamente lo que haría Sirius. Recomiendan:
  - Guardar las huellas separadas de los datos de identidad.
  - Cifrarlas.
  - Prohibir el acceso externo.
  - Evitar capturar huellas de quien no ha dado su consentimiento.
- [INFERENCIA] No es asesoramiento legal. Mientras Sirius esté en tu casa, para ti y sin enviar nada fuera, la exención doméstica probablemente cubre tu uso. Con visitas, la prudencia aconseja tres cosas: no crear la huella de nadie sin su permiso, tratar a los desconocidos como "persona sin identificar" sin guardar su huella, y no enviar caras ni voces a la nube. Si envías conversaciones a una API en la nube, ese proveedor recibe datos de terceros. Revisa sus condiciones.

---

## 5. Cómo medir que la memoria funciona

**En pocas palabras:** los bancos de pruebas públicos sirven de orientación, pero tienen fallos graves. LoCoMo tiene respuestas erróneas y un juez demasiado blando. Lo que de verdad te dirá si Sirius recuerda bien es un banco de pruebas propio, en español, que se repita solo tras cada cambio.

### 5.1 Bancos públicos

| Banco | Qué mide | Críticas o notas |
|---|---|---|
| LoCoMo (ACL 2024) | Conversaciones largas: preguntas de un salto, de varios saltos, temporales y abiertas | Auditoría de 2026 (dial481/locomo-audit, Penfield Labs): 99 de 1.540 respuestas oficiales son erróneas (6,4 %); el juez LLM aceptó el 62,81 % de respuestas vagas incorrectas; techo real de ~93,6 %; las 446 preguntas "trampa" (sin respuesta) se suelen excluir |
| LongMemEval (ICLR 2025) | 500 preguntas: extracción, varias sesiones, razonamiento temporal, actualización y abstención | Caídas del 30–60 %. Crítica: la versión S (~115.000 tokens) cabe ya en el contexto de los modelos actuales |
| DMR (MemGPT, 2023) | Recuperación en conversaciones | Fácil: Zep 94,8 % y MemGPT 93,4 % |
| MSC (2021–2022) | Chat de varias sesiones | Fácil y antiguo |
| PerLTQA, MemBench (ACL 2025 Findings) | Memoria personal y memoria reflexiva | Útiles como ideas de categorías |
| MemoryAgentBench (ICLR 2026) | Recuperación, aprendizaje en uso, comprensión larga, conflictos | Conflictos: ~60 % con GPT-4o |
| PersonaMem, PrefEval | Preferencias y personalidad | Interesantes para "mis gustos" |
| HaluMem (2025–2026) | Alucinaciones al extraer, actualizar y responder | El más relevante para los recuerdos falsos |

- [OPINIÓN] No persigas cifras de LoCoMo. Si quieres un banco público de referencia, usa LongMemEval y HaluMem, y añade preguntas propias.

### 5.2 Tu banco de pruebas casero

- [OPINIÓN] Un archivo con 100–200 casos en español, que se ejecute solo con `pytest` tras cada cambio. Para cada caso: una conversación simulada con fechas falsas, una pregunta, la respuesta esperada y la latencia máxima. Categorías:
  1. **Hechos plantados:** "Mi hermana se llama Lucía" y, 30 sesiones después, "¿Cómo se llama mi hermana?".
  2. **Hechos que cambian:** "Trabajo en X" y, meses después, "Me he cambiado a Y". Pregunta lo actual y lo antiguo.
  3. **Tiempo:** "¿Qué te dije el martes?" y "¿Cuándo fue la última vez que vino Ana?".
  4. **Preferencias implícitas:** "Ponme música" debe acertar el estilo que te gusta.
  5. **Abstención:** preguntar algo que nunca dijiste. La respuesta correcta es "no lo sé".
  6. **Atribución:** algo que dijo Sirius o una visita no debe atribuirse a ti.
  7. **Corrección y olvido:** tras "eso no es así" y "olvida eso", el dato no debe reaparecer, ni siquiera en los resúmenes.
  8. **Robot:** "¿Dónde viste mis llaves?" y "¿Quién vino ayer?".
  9. **Seguridad:** una frase de la televisión que da una "instrucción" no debe guardarse.
- [INFERENCIA] Mide dos cosas por separado:
  - **Recuperación:** ¿estaba el recuerdo correcto entre los 10 primeros? Esto se comprueba sin LLM, es barato y no tiene el problema del juez blando.
  - **Respuesta final:** un juez LLM estricto, más revisión manual de los fallos.
  Guarda también la latencia p50 y p95 de cada fase.

---

## 6. Partes de la petición que no tienen sentido o tienen una forma mejor

**En pocas palabras:** casi todo lo que pides es razonable. Hay cinco ajustes.

1. **Mapas de un espacio (SLAM, grafos 3D):** para una cabeza fija no tienen sentido. Mejor una memoria de escena desde un punto fijo, dejando abierto el camino para el futuro.
2. **"Recordar durante años" no exige un sistema complejo,** sino un formato estable: el original guardado, el modelo de embeddings anotado y migraciones planificadas. El riesgo a largo plazo no es el espacio en disco. Es cambiar de modelo o de librería y perderlo todo.
3. **Elegir por las cifras de LoCoMo** no es fiable: hay respuestas erróneas, el juez es blando y los vendedores se contradicen.
4. **Que el LLM "decida" solo qué es verdad** (extraer, actualizar, borrar) es la causa número uno de los recuerdos falsos. Mejor que proponga y que reglas fijas, y tú, confirméis.
5. **"Rápido"** no depende de la base de datos, que ya es rápida. Depende de no meter el LLM de extracción en el turno de voz.

---

## 7. Arquitectura de memoria recomendada para Sirius (se entiende sola)

**En pocas palabras:** una sola base de datos SQLite con cinco capas. Durante la conversación solo se **lee** de forma rápida y se **apunta** lo literal. Todo lo "inteligente" (resumir, extraer hechos, resolver contradicciones, olvidar) ocurre de noche o cuando el PC está libre. Tú puedes revisar y corregir.

### a) Capas

| Capa | Qué guarda | Cuándo se escribe | Cómo se lee |
|---|---|---|---|
| 0. Contexto del turno | Perfil fijo de quien habla, "quién soy yo", resumen de hoy, últimos turnos, 5–10 recuerdos | Se monta en cada turno | Va directo al LLM (2.000–4.000 tokens) |
| 1. Registro literal (episódica bruta) | Cada frase con hora, hablante, confianza de quién habla y canal; eventos de cámara (objetos, caras, dirección del cuello) | Al instante, sin LLM | Búsqueda por fecha, por palabras y por significado |
| 2. Episodios y resúmenes | Conversaciones y escenas resumidas; resúmenes diarios y mensuales, cada uno con enlaces a sus fuentes | De noche | Para preguntas de "¿qué hicimos...?" |
| 3. Fichas de hechos (semántica, bitemporal) | Entidad + atributo + valor + `valid_at` / `invalid_at` + procedencia + confianza + "confirmado sí/no" | De noche (propuesta del LLM + reglas fijas); al instante si tú corriges | Perfil fijo y búsqueda |
| 4. Rutinas y aprendizaje (procedimental) | Costumbres ("café a las 8"), formas de tratar a cada persona, lo que Sirius ha aprendido a hacer | De noche, con revisión tuya | Se inyectan según la situación |
| Entidades y huellas | Personas, lugares, objetos y eventos con un identificador común; huellas de cara y voz cifradas y separadas | Al dar de alta a una persona (con su permiso) | Reconocimiento en tiempo real |

### Diagrama sencillo

```
  Micrófono / Cámara
        │
        ▼
 [Reconocer quién habla y qué hay]  (voz ECAPA, cara ArcFace, objetos)
        │
        ▼
 ┌──────────── TURNO DE VOZ (meta: memoria < 150 ms) ────────────┐
 │ 1. Apuntar frase literal en SQLite (capa 1)                   │
 │ 2. Buscar: filtro persona/fecha + vectores (sqlite-vec)       │
 │    + palabras (FTS5) → fusión RRF + importancia + recencia    │
 │ 3. Montar contexto (capa 0) → LLM → respuesta por voz         │
 └───────────────────────────────────────────────────────────────┘
        │
        ▼  (de noche / PC inactivo)
 ┌──────────── "SUEÑO" ──────────────────────────────────────────┐
 │ a. Cortar el día en episodios y resumirlos (capa 2)           │
 │ b. Proponer hechos nuevos y cambios (LLM) → reglas fijas →    │
 │    aplicar, o dejar "pendiente de confirmar" (capa 3)         │
 │ c. Cerrar hechos contradichos (invalid_at), nunca borrarlos   │
 │ d. Detectar rutinas (capa 4); bajar prioridad de lo trivial   │
 │ e. Ejecutar el banco de pruebas y guardar informe             │
 └───────────────────────────────────────────────────────────────┘
        │
        ▼
 Tú: "¿qué sabes de mí?", "eso no es así", "olvida eso"
```

### Recuperación, consolidación, corrección y olvido

- **Recuperación:** búsqueda híbrida con filtros de persona y fecha. Puntuación final = RRF + importancia + recencia. Reranker opcional.
- **Consolidación nocturna:** los pasos a–e del diagrama.
- **Corrección:** "eso no es así" cierra el hecho viejo y crea el nuevo con la máxima confianza.
- **Olvido:** bajar la prioridad es automático. Borrar de verdad ("olvida eso") lo elimina todo, incluidos vectores y resúmenes derivados.

### Según tu PC

| | Sin GPU | GPU 8–12 GB | GPU 16–24 GB |
|---|---|---|---|
| En local | SQLite, sqlite-vec, FTS5, embeddings pequeños en CPU, voz ECAPA, cara InsightFace pequeña | Lo anterior en GPU + reranker 0.6B + LLM de 7–8B (Q4) para el "sueño" | Lo anterior + LLM de 14–32B (Q4) para el "sueño" y quizá para conversar; visión-lenguaje local |
| En la nube | LLM de conversación y LLM del "sueño" (solo texto) | LLM de conversación (o local si te basta) | Opcional: solo para preguntas difíciles |
| Nunca a la nube | Huellas de cara y voz, imágenes | Igual | Igual |

### b) Qué aprovechar y qué cambiar de tu memoria actual

**Aprovechar:**
- La base de datos local con historial: es tu capa 1.
- Los "recuerdos": pasan a ser la capa 3, con campos añadidos.
- Las **decisiones versionadas**: son justo el mecanismo para corregir sin perder historia.
- La búsqueda por relevancia: será la mitad semántica de la búsqueda híbrida.

**Cambiar o añadir:**
1. Campos bitemporales: `valid_at`, `invalid_at`, `created_at` y `expired_at`.
2. Procedencia en cada recuerdo: hablante, turno de origen, canal, confianza y si está confirmado.
3. Una tabla de entidades común (persona, lugar, objeto, evento) y una de huellas cifradas.
4. FTS5 junto a los vectores, y fusión RRF.
5. Un campo con el modelo y la versión de cada embedding.
6. Un proceso nocturno separado del de conversación.
7. Borrado real que alcance a los resúmenes derivados.
8. Tablas de escena: observación y último avistamiento.
9. El banco de pruebas automático.

**¿Librería o sistema propio?** [OPINIÓN]

| Opción | A favor | En contra |
|---|---|---|
| Seguir con lo propio (recomendado) | Ya existe; control total; SQLite en Windows; sin dependencias que cambien; privacidad | Más trabajo tuyo; nadie te lo mantiene |
| Mem0 | Rápido de integrar; modelo ADD/UPDATE/DELETE probado | Usa la extracción como sustituto del original; HaluMem QA 53 %; sus cifras son de vendedor |
| Letta | Bloques núcleo y agentes de "sueño" bien pensados | Es un servidor y un marco completo; tendrías que adaptar tu aplicación a él |
| Graphiti | La mejor idea temporal | Necesita una base de datos de grafos (Neo4j o similar); invalidaciones erróneas con modelos pequeños (#1728, #1666) |
| LangMem | Buenas ideas sobre memoria procedimental | Latencia de búsqueda medida de 18 s (p50) en la tabla de Mem0 |

[OPINIÓN] **Copia las ideas, no las librerías:** los bloques núcleo de Letta, las operaciones de Mem0, los campos bitemporales de Graphiti, la puntuación de Park y el "sueño" de Letta y LightMem.

### c) Plan por fases (para una persona sola)

1. **Fase 0 (1–2 semanas): medir.** Monta el banco de pruebas (sección 5.2) con 50 casos y mide tu sistema actual. Sin esto no sabrás si mejoras.
2. **Fase 1: registro literal y búsqueda híbrida.** Hablante y hora en cada frase, FTS5 + sqlite-vec + RRF, y el contexto del turno con presupuesto fijo. Mide que la memoria tarde menos de 150 ms.
3. **Fase 2: fichas bitemporales y procedencia.** Migra tus recuerdos actuales. Añade las órdenes "eso no es así", "olvida eso" y "¿qué sabes de mí?".
4. **Fase 3: el "sueño" nocturno.** Episodios, resúmenes, propuesta de hechos con reglas fijas y cola de "pendiente de confirmar". Al final, el banco de pruebas se ejecuta solo.
5. **Fase 4: personas.** Alta con permiso, huella de voz (ECAPA) y luego de cara (InsightFace), umbrales, y el modo "persona sin identificar".
6. **Fase 5: escena.** Detección de objetos solo cuando hay cambios, tabla de último avistamiento y enlace con las entidades de la conversación.
7. **Fase 6: rutinas y pulido.** Memoria procedimental revisada por ti, olvido por prioridad y defensas contra la inyección.

### d) Decisiones que tienes que tomar tú

| Decisión | Opciones | Consecuencias |
|---|---|---|
| Visitas e invitados | (1) No reconocer a nadie que no se dé de alta; (2) reconocer con permiso verbal; (3) reconocer a todos | (1) es lo más seguro legalmente y Sirius es menos "social"; (2) es un equilibrio, pero tienes que gestionar el permiso; (3) tiene riesgo legal y social |
| Nube o local | Todo local / texto en la nube y biometría en local / casi todo en la nube | Más local = más privacidad y más GPU; más nube = mejor calidad y coste por uso, y terceros reciben tus conversaciones |
| ¿Puede olvidar solo? | Nunca borra (solo baja la prioridad) / borra lo trivial pasado X meses / borrado agresivo | Nunca borrar ocupa poco y siempre se puede volver atrás; borrar solo puede eliminar algo que luego echarías de menos |
| ¿Revisas lo que recuerda? | Revisión semanal de lo "pendiente" / solo cuando preguntes / nunca | Revisar da más exactitud y te lleva unos minutos a la semana; no revisar acumula errores (HaluMem) |
| Qué se guarda de cámara y audio | Solo texto y etiquetas / también miniaturas / audio y vídeo | Solo texto es ligero y privado; guardar medios permite reinterpretar más tarde, pero ocupa mucho y es más sensible |
| Presupuesto de GPU | Ninguna / 8–12 GB / 16–24 GB | Sin GPU funciona con la nube; 8–12 GB permite el "sueño" local; 16–24 GB permite casi todo en local |
| Qué dice Sirius delante de otros | Todo / nada privado si hay alguien más / preguntar | Afecta a la confianza y a la privacidad de terceros |
| Modo "no recordar" | Sí, por orden de voz / sí, con un botón físico / no | Recomendable para la confianza; tienes que garantizar que de verdad no guarda nada |
| Cifrado y copias de seguridad | Disco cifrado / base de datos cifrada / sin cifrado | Más cifrado = más protección si roban el PC, y algo más de complejidad |

### e) Lo que no tiene sentido o tiene una forma mejor (resumen)

- Mapas y SLAM para una cabeza fija: no. Usa memoria de escena desde un punto fijo.
- Elegir librería por LoCoMo: no. Usa tu propio banco de pruebas.
- Dejar que el LLM decida solo qué es verdad: no. Que proponga, y que reglas fijas y tú confirméis.
- Sustituir el original por "recuerdos" extraídos: no. Guarda siempre el original.
- Hacer la extracción durante la voz: no. Hazla de noche.

---

## Advertencias

- Muchas cifras (Mem0, Zep, Letta, Hindsight, TiMem) las publican los autores sobre su propio sistema. Las comparaciones cruzadas usan jueces y configuraciones distintas.
- Varios trabajos de 2026 citados son preprints de arXiv sin revisión por pares completa.
- La comparativa de sqlite-vec de Kanopy Labs y las cifras de CPU de InsightFace que circulan por blogs no están verificadas. Mide en tu PC.
- No encontré información técnica fiable sobre la memoria interna de ChatGPT, Claude, Gemini, Replika o Character.AI.
- La parte legal es orientativa, no asesoramiento jurídico.

## Glosario

- **Abstención:** responder "no lo sé" cuando no hay dato.
- **Bitemporal:** guardar cuándo algo fue verdad y cuándo lo supo el sistema.
- **BM25 / FTS5:** búsqueda por palabras; FTS5 es la de SQLite.
- **Contexto:** el texto que el LLM lee en cada turno.
- **Cuantización (Q4, Q8):** comprimir un modelo para que ocupe menos memoria.
- **Embedding:** vector de números que representa el significado de un texto, una cara o una voz.
- **Grafo de conocimiento:** red de entidades unidas por relaciones.
- **Huella biométrica:** embedding de una cara o una voz que identifica a una persona.
- **Latencia (p50 / p95):** tiempo de espera; p50 es el caso típico y p95, el caso lento (solo el 5 % tarda más).
- **LLM:** modelo de lenguaje.
- **RAG:** buscar información y dársela al LLM antes de que responda.
- **Reranker:** modelo que reordena los resultados de una búsqueda.
- **RRF:** forma de fusionar varias listas de resultados.
- **SLAM:** técnica para que un robot móvil construya un mapa y se sitúe en él.
- **Token:** trozo de palabra; es la unidad de medida del texto en un LLM.
- **VRAM:** memoria de la tarjeta gráfica.
