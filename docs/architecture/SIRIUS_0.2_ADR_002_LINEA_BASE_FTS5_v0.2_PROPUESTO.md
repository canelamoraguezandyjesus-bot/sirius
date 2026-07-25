# SIRIUS 0.2 — ADR-002 · Línea base FTS5 de Sirius 0.1

**Versión:** 0.2
**Estado:** PROPUESTO · documento de análisis, no aprueba ni decide nada
**Fecha:** 25 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_LINEA_BASE_FTS5_v0.1_PROPUESTO.md`, que se conserva sin modificar
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_01B_CORRECCION_CANONICA_v0.1.md`
**No autoriza:** decisión de ADR-002, elección de alternativa técnica, implementación, cambios en Sirius 0.1 ni ejecución del benchmark.

---

## 0. Qué corrige esta versión

**[H] Ninguna medición se ha repetido y ninguna ha cambiado.** Todos los hechos técnicos de la v0.1 se conservan íntegros: el DDL, las tablas sombra, los ocho triggers, el comportamiento del saneado, el plegado de diacríticos, la ausencia de lematización, la disponibilidad no usada de `bm25`, la copia literal del contenido en `knowledge_fts`, la fuga entre proyectos y la invisibilidad de la negación.

Lo único que cambia es la **trazabilidad normativa**, ahora contra el texto canónico de B04:

| Hallazgo | Traza v0.1 (incorrecta) | Traza canónica v0.2 |
|---|---|---|
| Fuga de ámbito entre proyectos | RF-07 | **B04-RF-06** |
| Negación invisible | RF-19 | **B04-RF-19** (sin cambio) |
| Barrido completo sin etapas | «ausencia de expansión escalonada», RF-14 | **B04-RF-14**, reclasificado a **inseguro**: el texto canónico prohíbe expresamente el «salto a recuperación amplia» |

**[H]** El tercero es la única reclasificación de la línea base, y no procede de evidencia nueva sino del texto canónico: la v0.1 trabajaba con un resumen que decía «respetar E0–E5» y no permitía ver que el salto está explícitamente prohibido.

---

## 1. Objeto y método

Caracterizar **lo que la recuperación de Sirius 0.1 realmente hace**, medido y no presumido, como control comparativo congelado para ADR-002.

**[H]** Método de la v0.1, conservado: lectura del código y las migraciones reales, más medición directa contra una base creada con la cadena canónica de Alembic (`upgrade_to_head`). Ningún fichero de `src/`, `tests/`, `migrations/` ni configuración productiva fue modificado, ni entonces ni ahora. Las sondas se ejecutaron fuera del repositorio.

Marcas: **[H]** hecho verificado · **[N]** obligación normativa canónica · **[?]** hipótesis o incertidumbre.

**[N]** Clasificación del §8 del paquete 01: ① capacidad existente · ② capacidad parcial · ③ ausencia · ④ comportamiento inseguro para 0.2 · ⑤ decisión que pertenece a otro ADR.

---

## 2. Entorno de medición

**[H]**

| Elemento | Valor |
|---|---|
| Python | 3.14.6 |
| Biblioteca SQLite | 3.45.1 |
| SQLAlchemy | 2.0.51 |
| Alembic | 1.18.5 |
| Head de Alembic | `61be4bb269bf` |
| Plataforma | linux |

**[?]** El comportamiento del tokenizador y de la purga física debe reconfirmarse sobre el SQLite que embarque el ejecutable de Windows: ADR-001 dejó esa verificación explícitamente pendiente.

---

## 3. Superficie real de recuperación

**[H]** La recuperación completa de Sirius 0.1 son **560 líneas** en cinco ficheros, más el recorte aguas abajo:

| Fichero | Líneas | Papel |
|---|---|---|
| `migrations/versions/61be4bb269bf_create_fts5_search_indexes.py` | 196 | Sustrato: dos tablas FTS5 y ocho triggers |
| `src/sirius/ports/knowledge_search_repository.py` | 34 | Puerto (`Protocol`), sin dependencia de motor |
| `src/sirius/adapters/persistence/sqlite_knowledge_search_repository.py` | 93 | Adaptador FTS5 y saneado de consulta |
| `src/sirius/domain/relevance.py` | 152 | Orden puro, sin repositorio |
| `src/sirius/application/rank_relevant_knowledge.py` | 86 | Caso de uso: reúne candidatos y booleanos |
| `src/sirius/application/context_budget.py` | 195 | Recorte por presupuesto (B6c), aguas abajo |

**[H]** La dirección de dependencias se respeta: el dominio no conoce SQLite y el puerto no importa SQLAlchemy. Es lo que sostiene la clasificación ① de **B04-RF-31**, neutralidad tecnológica.

---

## 4. El sustrato: dos tablas FTS5 y ocho triggers

### 4.1 DDL real, verificado

**[H]**

```sql
CREATE VIRTUAL TABLE message_fts USING fts5(
    content, content='messages', content_rowid='id');

CREATE VIRTUAL TABLE knowledge_fts USING fts5(
    kind UNINDEXED, item_id UNINDEXED, content);
```

**[H]** Ocho triggers presentes en head: `messages_fts_ai/ad/au`, `memory_revisions_fts_ai/au/ad`, `decision_revisions_fts_ai/ad`.

**[H]** `knowledge_fts` usa un espacio de rowid sintético: `memory_id * 2` (par) y `decision_id * 2 + 1` (impar). El mismo espacio se reutiliza como desempate final del orden, de modo que una memoria y una decisión del mismo id nunca empatan.

### 4.2 Diferencia material entre las dos tablas

**[H]** Medido enumerando las tablas sombra reales:

| Tabla | Modo | Tablas sombra | ¿Guarda copia del texto? |
|---|---|---|---|
| `message_fts` | **external content** sobre `messages` | `_config`, `_data`, `_docsize`, `_idx` | **No.** No existe `message_fts_content`; lee el texto vivo de `messages` en cada consulta |
| `knowledge_fts` | **autocontenida** | `_config`, `_content`, `_data`, `_docsize`, `_idx` | **Sí.** `SELECT content FROM knowledge_fts` devuelve el texto literal del recuerdo |

**[H]** Comprobación directa: `knowledge_fts` devolvió `"El cliente prefiere café con leche por la mañana"`, es decir, el contenido canónico íntegro almacenado dentro del derivado.

**[?]** No es un defecto de 0.1 —la migración documenta y justifica la decisión: el texto vigente de un recuerdo vive repartido en varias revisiones, así que no hay una fila fuente única a la que FTS5 pudiera apuntar—, pero **es un hecho con consecuencias para 0.2**: existe una segunda copia física del contenido canónico dentro de un derivado. Si 0.2 exige que ningún derivado retenga contenido en claro, condiciona el diseño de **todos** los índices de T1–T4.

**Clasificación: ⑤** — la política de contenido en derivados interactúa con ADR-001 (consecuencias 2 y 3) y con la arquitectura consolidada; ADR-002 no la decide en solitario.

### 4.3 Sincronización y regeneración

**[H]** Verificado por lectura y por las pruebas existentes:

- La actualización del índice ocurre **dentro de la misma transacción** que la escritura de datos, por trigger: un rollback de los datos revierte también el índice. Probado en `test_a_failed_commit_leaves_neither_the_data_nor_the_index_changed`.
- La migración hace **backfill** de ambas tablas: actualizar una base existente no pierde cobertura.
- El `downgrade` elimina **solo** las tablas FTS5 y sus triggers; ninguna tabla base ni sus datos se tocan. Probado.
- `INSERT INTO knowledge_fts(knowledge_fts) VALUES('integrity-check')` → **OK**.
- `rebuild` funciona en ambas tablas.

**Clasificación: ①.** Es el activo más sólido de la línea base. Satisface el invariante I-01 y anticipa la **puerta 5 de ADR-002** —borrado y reconstrucción completos de índices y derivados—, que convierte esta capacidad en requisito de toda realización técnica, no en ventaja diferencial.

**[?]** Matiz sobre `knowledge_fts`: al ser autocontenida, su `rebuild` se reconstruye desde `knowledge_fts_content`, es decir, **desde sí misma**, no desde `memory_revisions`. La regeneración desde el canon existe de hecho —las sentencias de backfill de la migración lo hacen— pero no está expuesta como operación invocable ni probada como tal. **[N]** ADR-001 exige que todo derivado sea reconstruible **desde la fuente canónica**.

---

## 5. El camino de consulta

### 5.1 Saneado: qué llega realmente a FTS5

**[H]** `sanitize_fts5_query` extrae cada token `\w+`, lo entrecomilla individualmente y los une con `OR`:

```
"café con leche"  ->  "café" OR "con" OR "leche"
```

**[H]** Consecuencias medidas, todas reproducibles:

| Entrada del usuario | Lo que llega a FTS5 | Resultado |
|---|---|---|
| `café` | `"café"` | acierta |
| `cafe` (sin tilde) | `"cafe"` | **acierta** sobre «café» |
| `CAFÉ` | `"CAFÉ"` | **acierta** |
| `reunion` | `"reunion"` | **acierta** sobre «reunión» |
| `"café con leche"` (frase) | `"café" OR "con" OR "leche"` | **la frase se pierde** |
| `caf*` (prefijo) | `"caf"` | **0 resultados** |
| `café NOT leche` | `"café" OR "NOT" OR "leche"` | `NOT` pasa a ser un término literal |
| `presupuesto AND anual` | `"presupuesto" OR "AND" OR "anual"` | `AND` pasa a ser un término literal |
| `!!!` o vacío | `""` | vacío, sin error |

**[H]** El plegado de mayúsculas y de diacríticos **funciona** (tokenizador `unicode61` por defecto). No es hipótesis: `cafe` recupera «café» y `reunion` recupera «reunión».

**[H]** No hay lematización ni derivación: `traslado` **no** recupera «trasladada»; `llueve` y `llovía` son términos disjuntos.

**Clasificación y traza canónica:**

| Aspecto | Clase | RF canónico |
|---|---|---|
| Robustez sintáctica ante entrada arbitraria | ① | contribuye a RF-32 |
| Normalización de caso y diacríticos | ① | contribuye a RF-16 |
| Frase, prefijo, proximidad y operadores | ③ | RF-16 |
| Variantes morfológicas y alias confirmados | ③ | **RF-16**, y RF-05 en su parte de alias |

**[?]** La unión por `OR` maximiza el recall a costa de la precisión: en la medición, `reunión jueves` devolvió tres documentos, uno por compartir solo la palabra «reunión». Cualquier comparación contra la línea base debe tener presente que **la línea base ya es deliberadamente permisiva**: su problema no es falta de recall léxico, sino ausencia de precisión y de puertas.

### 5.2 Lo que devuelve el adaptador

**[H]**

```python
def search_knowledge(self, query_text: str) -> frozenset[tuple[KnowledgeKind, int]]
```

Un **conjunto sin orden y sin puntuación**. FTS5 se usa como predicado booleano por candidato, no como motor de relevancia.

**[H]** `bm25()` **está disponible y funciona** sobre `knowledge_fts` —medido: `-0.340` y `-0.305` para dos documentos— pero **ninguna línea de la aplicación lo invoca**. La capacidad de ranking del propio FTS5 está sin explotar.

**Clasificación: ②** — capacidad existente en el motor, ausente en el producto.

**[N]** Que `bm25` esté disponible no lo convierte en la elección correcta: **RF-22 exige emitir razones mínimas por resultado** y **RF-28 exige explicar coincidencia, ámbito, tiempo, estado, procedencia, criticidad y razón de orden**. Cualquier incorporación de `bm25` debe demostrar cómo se mantiene esa explicabilidad.

### 5.3 Forma real de la recuperación

**[H]** `RankRelevantKnowledgeUseCase.rank(query_text)`:

1. Lee el proyecto activo.
2. Lanza **una** consulta FTS5 y obtiene el conjunto de aciertos.
3. Trae **todas** las memorias vigentes y **todas** las decisiones aprobadas, sin filtro de proyecto, sin límite y sin paginación.
4. Construye un candidato por cada una, con tres booleanos: asunto coincidente, pertenencia al proyecto activo y acierto FTS5.
5. Delega filtrado y orden en la función pura `rank_relevant_knowledge`.

**[H]** El filtro previo al orden descarta lo no vigente y lo no relacionado, y el dominio **reverifica** ambos por su cuenta en vez de fiarse del llamador.

**[H]** El orden es una tupla explícita, nunca una puntuación numérica:

```
(asunto coincidente, proyecto activo, acierto FTS5, recencia, id sintético)
```

**Clasificación: ①** para determinismo, estabilidad y explicabilidad del criterio; el desempate final garantiza orden total y reproducible. Es lo que sostiene la parte cumplida de RF-22 y RF-28.

**[N] Corrección de la v0.2 respecto de la v0.1:** el paso 3 —barrido completo de todo el conocimiento vigente en una sola pasada— es exactamente el **«salto a recuperación amplia» que B04-RF-14 prohíbe**. La v0.1 lo describió como ausencia de etapas; con el texto canónico es **④ comportamiento inseguro para 0.2**. Ver §8.

**[?]** El barrido es `O(n)` sobre todo el conocimiento vigente en cada consulta. Con los volúmenes de 0.1 no se ha observado problema, pero **no se ha medido** y no se fija aquí ningún umbral: eso pertenece al Registro de Tolerancias, que no existe todavía.

---

## 6. Primer hallazgo inseguro: el ámbito no es una puerta — B04-RF-06

**[H] Medido, no deducido.** Con dos proyectos —uno activo y otro ajeno— y una consulta ordinaria:

| Consulta | Resultado | `project_id` | ¿Proyecto activo? |
|---|---|---|---|
| `presupuesto` | «nota del proyecto activo sobre presupuesto» | 1 | sí |
| `presupuesto` | **«secreto del proyecto ajeno: presupuesto confidencial»** | 2 | **no** |

**[H]** El contenido del proyecto ajeno **se devuelve**. No se filtra: se ordena por debajo. Causa estructural, en dos sitios a la vez:

- `list_current_memories()` no tiene cláusula de proyecto: devuelve todas las memorias vigentes de la base.
- `project_matches_active` es el **segundo elemento de la clave de orden**, no una condición de exclusión.

**[H]** Sirius 0.1 cumple así su propio contrato: S7.5 enumera «proyecto activo» como criterio de **prioridad**, y B6b lo implementó exactamente como se le pidió. **No es un defecto de 0.1.**

**[N]** Para Sirius 0.2 es inadmisible. Traza canónica:

- **B04-RF-06**: «Aislamiento global, proyecto y multi-proyecto cerrado sin ampliación silenciosa».
- **B04-RF-09**: las puertas G1–G10 se aplican **antes de candidatos**, no después.
- Invariantes I-04 e I-03 del paquete 01.
- Consecuencia 8 de ADR-001: el ámbito se filtra **antes** de recuperación y ranking.
- Puerta 8 de ADR-002.

**Clasificación: ④.**

**[N]** Consecuencia para la comparación técnica: el aislamiento de ámbito es **puerta previa común** a T1, T2, T3 y T4, no rasgo diferenciador. El benchmark debe tratar toda fuga entre proyectos como **fallo duro**, no como pérdida de precisión.

---

## 7. Segundo hallazgo inseguro: la negación es invisible — B04-RF-19

**[H] Medido.** Dos recuerdos:

- «El cliente prefiere café con leche por la mañana»
- «El cliente **NO** prefiere café con leche»

La consulta `café` devuelve **los dos**, indistinguibles. La consulta `prefiere`, también.

**[H]** La causa es estructural, no del saneado: FTS5 indexa tokens, y «no» es un token más. Nada en el camino —índice, saneado u orden— representa la polaridad del enunciado.

**[N]** Traza canónica:

- **B04-RF-19**: preservar negación, condición, refutación y postura.
- **B04-RF-17**: la etapa de significado y relaciones debe incorporar **validación de sujeto, polaridad, condición y tiempo**.
- Invariante I-07.

**[N] Corrección respecto de la v0.1.** La v0.1 conjeturó que «ninguna de las cuatro alternativas resuelve la negación por sí sola, porque un modelo vectorial también sitúa "prefiere X" y "no prefiere X" a distancia mínima». La observación técnica sigue siendo cierta, pero la conclusión era incompleta: **B04 ya lo resolvió normativamente**. RF-17 no permite que la señal semántica actúe sin validación de polaridad. La validación de polaridad no es una opción de diseño que ADR-002 pueda descartar: es requisito de la etapa.

**Clasificación: ④.**

**[N]** Consecuencia para el benchmark: los casos de negación son **adversariales y de fallo duro**, y deben ejecutarse contra todas las realizaciones técnicas, precisamente para verificar que la validación exigida por RF-17 está presente y funciona.

---

## 8. Tercer hallazgo inseguro: el salto a recuperación amplia — B04-RF-14

**[H]** Hecho ya registrado en la v0.1, **reclasificado** aquí sin evidencia nueva.

`rank()` ejecuta una única pasada de índice y, en paralelo, un barrido completo de todo el conocimiento vigente. No hay etapas, no hay orden entre espacios de búsqueda, y no hay condición que gobierne el paso de uno a otro.

**[N]** **B04-RF-14** exige «ejecutar E0–E5 **sin salto a recuperación amplia**». **B04-RF-15** exige comenzar por recuperación estructurada y exacta. **B04-RF-16** condiciona la etapa léxica a la **insuficiencia** de la anterior.

**[H]** Lo que 0.1 hace es literalmente el salto: recupera todo lo elegible de una vez y decide después. La v0.1 lo clasificó como ③ ausencia de expansión escalonada; el texto canónico lo convierte en **④**, porque no es que falte una capacidad, es que el comportamiento existente está expresamente prohibido.

**[N]** Consecuencia: la expansión escalonada es la **tercera puerta previa común** a T1–T4. Ninguna realización técnica puede heredar el barrido completo.

**[?]** Esto tiene una implicación práctica que conviene anticipar: la comparación entre realizaciones técnicas **no** puede hacerse midiendo «cuántos resultados correctos devuelve cada una sobre el corpus completo». Debe medirse por etapa, respetando el orden E0–E5 y la condición de insuficiencia. El diseño de ablaciones de la especificación de benchmark ya lo contempla.

---

## 9. Estados, borrado y redacción

**[H]** Lo verificado, sin cambios respecto de la v0.1, con traza canónica añadida:

| Situación | Comportamiento real | Clase | RF canónico |
|---|---|---|---|
| Memoria archivada | **Sigue indexada y encontrable**; se excluye después, en el filtro de vigencia | ② | RF-12 |
| Decisión archivada o sustituida | Igual | ② | RF-12 |
| Memoria eliminada | `delete_memory` anula `content` en **todas** las revisiones; el trigger retira la fila del índice en la misma transacción | ① | RF-10 |
| Mensaje redactado | `content` a `NULL` y estado `REDACTED`; el trigger retira su texto de `message_fts` | ① | RF-10 |
| «No guardado», purgado, «no usar como memoria» | **No existen** como marcas en 0.1 | ③ | RF-10, RF-11 |
| Purga física del fichero | **No la hace la aplicación**; requiere `VACUUM`, según demostró el spike 10 de ADR-001 | ⑤ | ADR-001 c.3 y c.4 |

**[N]** La decisión de indexar lo archivado y filtrarlo después está documentada en el puerto: «excluir lo no vigente es trabajo del dominio, no del repositorio». Es coherente en 0.1.

**[?]** Para 0.2 debe reexaminarse a la luz de **RF-09**, que exige aplicar G1–G10 **antes de candidatos**. Un índice que contiene contenido no elegible es seguro solo mientras **todos** sus consumidores apliquen la puerta correcta. Hoy hay un solo consumidor; con más señales y más etapas, esa garantía deja de ser estructural.

**[H]** De las siete dimensiones canónicas de ADR-001, **solo disponibilidad** participa hoy en la recuperación, y en su forma degradada de enum heredado. Confirmación, validez, sensibilidad, temporalidad, ámbito y autoridad no intervienen. **Clase ③.**

---

## 10. Explicación, límites y ausencia

**[H]** Con traza canónica:

| Obligación | Estado real | Clase | RF |
|---|---|---|---|
| Razones mínimas por resultado | Tres booleanos y la recencia; criterio de orden legible. No se emite razón por resultado | ② | RF-22 |
| Explicación completa | Faltan tiempo, procedencia, criticidad y razón explícita de orden; el ámbito aparece como señal de orden, no como puerta | ② | RF-28 |
| Plan reproducible | No se registra ninguno | ③ | RF-29 |
| Límite objetivo y duro | Un único recorte aguas abajo, con constantes por defecto en el código. Sin distinción objetivo/duro | ② | RF-24 |
| Desbordamiento crítico no oculto | El recorte es **silencioso** | ③ | RF-24 |
| Suficiencia por cardinalidad y taxonomía | No existe | ③ | RF-25 |
| Ausencia y no-reportable indistinguibles | No existe la distinción interna, luego tampoco la protección | ③ | RF-26 |
| Degradación por S3/S4/S7 con salida parcial | No contemplada | ③ | RF-32 |
| Operación activa que herede propósito, permiso, ámbito, tiempo y límites | `rank(query_text)` solo recibe texto | ③ | RF-30, RF-01 |
| Entrega a B05 | Tupla ordenada; faltan evidencia, criticidad, límites y suficiencia | ② | RF-27 |

**[N]** No se transcriben las cifras por defecto del recorte como si fueran tolerancias: son constantes de implementación de 0.1, no umbrales aprobados. El Registro de Tolerancias no existe todavía y **no se inventa ninguna cifra**.

---

## 11. Resumen de la línea base

**[H]** Lo que la línea base **sí** aporta y conviene conservar:

1. Sincronización índice/dato transaccional por trigger, con rollback conjunto probado.
2. Regenerabilidad del índice y `downgrade` limpio que no toca ninguna tabla base — anticipa la puerta 5.
3. Saneado de consulta a prueba de entrada arbitraria, sin posibilidad de inyección de operadores.
4. Normalización de caso y diacríticos.
5. Orden determinista, estable y explicable, sin puntuación opaca, con desempate total.
6. Neutralidad tecnológica real — **RF-31**, único `EXISTENTE` del inventario.
7. Exclusión efectiva del contenido eliminado, propagada al índice en la misma transacción.

**[H]** Lo que la línea base **no** aporta, con su RF canónico:

| Hueco | RF |
|---|---|
| Aislamiento de ámbito — **④** | RF-06 |
| Expansión escalonada sin salto — **④** | RF-14 |
| Preservación de negación, condición y postura — **④** | RF-19, RF-17 |
| Petición completa, permiso, modo y aclaración | RF-01 a RF-04 |
| Resolución de entidad, homónimos y alias | RF-05, RF-16 |
| Tiempo objetivo y corte de registro | RF-07, RF-08 |
| Puertas G1–G12 estructuradas | RF-09 |
| Marcas de no guardado, purgado y no consolidable | RF-10, RF-11, RF-12 |
| Evidencia externa atribuida | RF-13 |
| Frase, prefijo, proximidad y variantes morfológicas | RF-16 |
| Clase de evidencia y cotejo de estados en fuentes e historial | RF-18 |
| Deduplicación con equivalencia material y conservación de procedencias | RF-20 |
| Marcado de lados de un conflicto | RF-21 |
| Criticidad con nivel, razón, fuente y regla | RF-23 |
| Suficiencia, taxonomía de ausencia y parcialidad visible | RF-24, RF-25, RF-26 |
| Plan reproducible y contexto de operación | RF-29, RF-30 |

**[N]** Los tres **④** son puertas previas comunes a T1–T4. Los siete puntos del primer bloque son el activo que toda realización técnica debe preservar.

---

## 12. Condiciones de congelación

**[N]** ADR-002 exige que la línea base se conserve **congelada** como control comparativo y no se modifique para favorecer a ninguna realización técnica.

**[H]** En esta ronda no se ha modificado nada: ni `src/`, ni `tests/`, ni `migrations/`, ni configuración productiva. **No se ha repetido ninguna medición.**

**[N]** La línea base queda identificada por el head de Alembic `61be4bb269bf` y por los ficheros de la §3. Cualquier cambio en ellos invalida las comparaciones ya ejecutadas y obliga a repetir la medición.

---

## 13. Incertidumbres de esta línea base

Todas **[?]**. Sin cambios materiales respecto de la v0.1.

1. **No se ha medido rendimiento.** Ni latencia, ni tamaño de índice, ni escalado del barrido completo. Sin Registro de Tolerancias no habría con qué comparar.
2. **No se ha medido sobre Windows.** Tokenizador, `secure_delete` y purga pueden diferir en el SQLite empaquetado.
3. **No se ha medido con corpus realista.** Las sondas usaron unidades de documentos. El comportamiento del `OR` permisivo a escala es previsiblemente peor en precisión, pero no está medido.
4. **No se ha ejecutado el benchmark.** Este documento caracteriza; no puntúa.
5. **Regeneración desde el canon.** Implícita en las sentencias de backfill de la migración, pero sin operación invocable ni prueba que la ejerza.
6. **Interacción entre precedencia y conflicto.** RF-21 obliga a recuperar **y marcar** todos los lados elegibles; `find_prevailing_decision` suprime el no prevaleciente en el ensamblado de contexto. La obligación sobre la capa de recuperación es ahora inequívoca; en qué capa actúa la precedencia, no.

---

**Siguiente movimiento único:** revisar esta línea base junto al inventario v0.2, la especificación de benchmark v0.2 y la apertura de ADR-002 v0.2, antes de ejecutar medición alguna.
