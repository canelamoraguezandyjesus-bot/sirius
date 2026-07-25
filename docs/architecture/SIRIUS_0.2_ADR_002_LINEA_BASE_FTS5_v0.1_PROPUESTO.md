# SIRIUS 0.2 — ADR-002 · Línea base FTS5 de Sirius 0.1

**Versión:** 0.1
**Estado:** PROPUESTO · documento de análisis, no aprueba ni decide nada
**Fecha:** 25 de julio de 2026
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_01_INVENTARIO_Y_BASELINE_v0.1.md`
**Rama:** `evidence/adr001-spikes`
**No autoriza:** decisión de ADR-002, elección de alternativa, implementación, cambios en Sirius 0.1 ni ejecución del benchmark.

---

## 1. Objeto y método

Caracterizar **lo que la recuperación de Sirius 0.1 realmente hace**, medido y no presumido, como control comparativo congelado para ADR-002.

**[H]** Método: lectura del código y las migraciones reales, más medición directa contra una base creada con la cadena canónica de Alembic (`upgrade_to_head`). Ningún fichero de `src/`, `tests/`, `migrations/` ni configuración productiva fue modificado. Las sondas se ejecutaron fuera del repositorio.

Marcas: **[H]** hecho verificado · **[N]** obligación normativa · **[?]** hipótesis o incertidumbre.

**[N]** Clasificación exigida por el §8 del paquete, usada en todo el documento:

| Clase | Significado |
|---|---|
| ① | Capacidad existente |
| ② | Capacidad parcial |
| ③ | Ausencia |
| ④ | Comportamiento inseguro para 0.2 |
| ⑤ | Decisión que pertenece a otro ADR |

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

**[H]** La recuperación completa de Sirius 0.1 son **560 líneas** en cinco ficheros:

| Fichero | Líneas | Papel |
|---|---|---|
| `migrations/versions/61be4bb269bf_create_fts5_search_indexes.py` | 196 | Sustrato: dos tablas FTS5 y ocho triggers |
| `src/sirius/ports/knowledge_search_repository.py` | 34 | Puerto (`Protocol`), sin dependencia de motor |
| `src/sirius/adapters/persistence/sqlite_knowledge_search_repository.py` | 93 | Adaptador FTS5 y saneado de consulta |
| `src/sirius/domain/relevance.py` | 152 | Orden puro, sin repositorio |
| `src/sirius/application/rank_relevant_knowledge.py` | 86 | Caso de uso: reúne candidatos y booleanos |
| `src/sirius/application/context_budget.py` | 195 | Recorte por presupuesto (B6c), aguas abajo |

**[H]** La dirección de dependencias se respeta: el dominio no conoce SQLite y el puerto no importa SQLAlchemy.

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

**[H]** Ocho triggers, todos presentes en head: `messages_fts_ai/ad/au`, `memory_revisions_fts_ai/au/ad`, `decision_revisions_fts_ai/ad`.

**[H]** `knowledge_fts` usa un espacio de rowid sintético para no mezclar identificadores: `memory_id * 2` (par) y `decision_id * 2 + 1` (impar). El mismo espacio se reutiliza como desempate final del orden.

### 4.2 Diferencia material entre las dos tablas

**[H]** Medido enumerando las tablas sombra reales:

| Tabla | Modo | Tablas sombra | ¿Guarda copia del texto? |
|---|---|---|---|
| `message_fts` | **external content** sobre `messages` | `_config`, `_data`, `_docsize`, `_idx` | **No.** No existe `message_fts_content`; lee el texto vivo de `messages` en cada consulta |
| `knowledge_fts` | **autocontenida** | `_config`, `_content`, `_data`, `_docsize`, `_idx` | **Sí.** `SELECT content FROM knowledge_fts` devuelve el texto literal del recuerdo |

**[H]** Comprobación directa: `knowledge_fts` devolvió `"El cliente prefiere café con leche por la mañana"`, es decir, el contenido canónico íntegro almacenado en el derivado.

**[?]** Esto no es un defecto de 0.1 —la migración documenta y justifica la decisión: el texto vigente de un recuerdo vive repartido en varias revisiones, así que no hay una fila fuente única a la que FTS5 pudiera apuntar—, pero **es un hecho de privacidad con consecuencias para 0.2**: existe una segunda copia física del contenido canónico dentro de un derivado. Si 0.2 exige que ningún derivado retenga contenido en claro, esto condiciona el diseño de **todos** los índices, incluidos los que introduzcan las alternativas B, C y D.

**Clasificación: ⑤** — la política de contenido en derivados no la decide ADR-002 por sí sola; interactúa con ADR-001 (consecuencias 2 y 3) y con la arquitectura consolidada.

### 4.3 Sincronización y regeneración

**[H]** Verificado por lectura y por las pruebas existentes:

- La actualización del índice ocurre **dentro de la misma transacción** que la escritura de datos, por trigger: un rollback de los datos revierte también el índice. Probado en `test_a_failed_commit_leaves_neither_the_data_nor_the_index_changed`.
- La migración hace **backfill** de ambas tablas, así que actualizar una base existente no pierde cobertura.
- El `downgrade` elimina **solo** las tablas FTS5 y sus triggers; ninguna tabla base ni sus datos se tocan. Probado.
- `INSERT INTO knowledge_fts(knowledge_fts) VALUES('integrity-check')` → **OK**.
- `rebuild` funciona en ambas tablas. `message_fts` se regenera desde `messages`; `knowledge_fts`, desde su propia tabla de contenido.

**Clasificación: ①** para sincronización transaccional y regenerabilidad. Es el activo más sólido de la línea base y satisface el invariante I-01.

**[?]** Matiz sobre `knowledge_fts`: al ser autocontenida, su `rebuild` se reconstruye desde `knowledge_fts_content`, es decir, **desde sí misma**, no desde `memory_revisions`. La regeneración desde el canon existe de hecho (las sentencias de backfill de la migración lo hacen), pero no está expuesta como operación invocable. **[N]** ADR-001 exige que todo derivado sea reconstruible **desde la fuente canónica**; conviene comprobar que esa ruta queda disponible y probada, no solo implícita en una migración.

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

**[H]** El plegado de mayúsculas y de diacríticos **funciona** (tokenizador `unicode61` por defecto). No es una hipótesis: `cafe` recupera «café» y `reunion` recupera «reunión».

**[H]** No hay lematización ni derivación: `traslado` **no** recupera «trasladada»; `llueve` y `llovía` son términos disjuntos.

**Clasificación:**
- Robustez sintáctica frente a entrada arbitraria: **①**. Ningún carácter especial puede romper la consulta ni inyectar operadores. Probado.
- Normalización de caso y diacríticos: **①**.
- Frase, prefijo, proximidad y operadores booleanos: **③**. No están disponibles porque el saneado los neutraliza deliberadamente.
- Variantes morfológicas y alias: **③**. Es exactamente el hueco de B04-RF-16.

**[?]** La unión por `OR` maximiza el recall a costa de la precisión: en la medición, `reunión jueves` devolvió tres documentos, uno de ellos por compartir únicamente la palabra «reunión». Cualquier alternativa que compare recall contra la línea base debe tener en cuenta que **la línea base ya es deliberadamente permisiva**, y que su problema no es la falta de recall léxico sino la ausencia de precisión y de puertas.

### 5.2 Lo que devuelve el adaptador

**[H]**

```python
def search_knowledge(self, query_text: str) -> frozenset[tuple[KnowledgeKind, int]]
```

Un **conjunto sin orden y sin puntuación**. FTS5 se usa como predicado booleano por candidato, no como motor de relevancia.

**[H]** `bm25()` **está disponible y funciona** sobre `knowledge_fts` —medido: devolvió `-0.340` y `-0.305` para dos documentos— pero **ninguna línea de la aplicación lo invoca**. La capacidad de ranking del propio FTS5 está sin explotar.

**Clasificación: ②** — el sustrato ofrece ranking; la aplicación no lo consume. Es capacidad existente en el motor y ausente en el producto.

**[N]** Que `bm25` esté disponible no lo convierte en la elección correcta: la §5 de ADR-002 exige medir, y S7.5 de la arquitectura de 0.1 fijó explícitamente «ordenación simple y comprobable», no «fórmula opaca». **[?]** Si ADR-002 quisiera incorporar `bm25`, tendría que justificar cómo se mantiene la explicabilidad de RF-28.

### 5.3 Forma real de la recuperación

**[H]** `RankRelevantKnowledgeUseCase.rank(query_text)`:

1. Lee el proyecto activo.
2. Lanza **una** consulta FTS5 y obtiene el conjunto de aciertos.
3. Trae **todas** las memorias vigentes (`list_current_memories`) y **todas** las decisiones aprobadas (`list_current_decisions`), sin filtro de proyecto ni límite ni paginación.
4. Construye un candidato por cada una, con tres booleanos: asunto coincidente, pertenencia al proyecto activo y acierto FTS5.
5. Delega el filtrado y el orden en la función pura `rank_relevant_knowledge`.

**[H]** El filtro previo al orden descarta lo no vigente y lo no relacionado, y el dominio **reverifica** ambos por su cuenta en vez de fiarse del llamador.

**[H]** El orden es una tupla explícita, nunca una puntuación numérica:

```
(asunto coincidente, proyecto activo, acierto FTS5, recencia, id sintético)
```

**Clasificación: ①** para determinismo, estabilidad y explicabilidad del criterio. El desempate final por id sintético garantiza orden total y reproducible, y una memoria y una decisión del mismo id no pueden empatar nunca.

**[?]** El barrido completo de candidatos es `O(n)` sobre todo el conocimiento vigente en cada consulta. Con los volúmenes de 0.1 no es un problema observado, pero **no se ha medido** y no se fija aquí ningún umbral: eso pertenece al Registro de Tolerancias, que no está en el repositorio.

---

## 6. Hallazgo crítico: el ámbito no es una puerta

**[H] Medido, no deducido.** Con dos proyectos —uno activo y otro ajeno— y una consulta ordinaria:

| Consulta | Resultado | `project_id` | ¿Proyecto activo? |
|---|---|---|---|
| `presupuesto` | «nota del proyecto activo sobre presupuesto» | 1 | sí |
| `presupuesto` | **«secreto del proyecto ajeno: presupuesto confidencial»** | 2 | **no** |

**[H]** El contenido del proyecto ajeno **se devuelve**. No se filtra: se ordena por debajo. La causa es estructural y está en dos sitios a la vez:

- `list_current_memories()` no tiene cláusula de proyecto: devuelve todas las memorias vigentes de la base.
- `project_matches_active` es el **segundo elemento de la clave de orden**, no una condición de exclusión.

**[H]** Sirius 0.1 cumple así su propio contrato: S7.5 enumera «proyecto activo» como criterio de **prioridad**, y B6b lo implementó exactamente como se le pidió. Esto **no** es un defecto de 0.1.

**[N]** Para Sirius 0.2 es inadmisible. Choca frontalmente con:
- el invariante I-04 del paquete, «multi-proyecto cerrado: no existe ampliación silenciosa de ámbito»;
- el invariante I-03, «contenido fuera de ámbito nunca es candidato»;
- la consecuencia 8 de ADR-001, «el ámbito multi-proyecto será cerrado y filtrado antes de recuperación y ranking»;
- la puerta 8 de ADR-002, que descarta cualquier alternativa que incumpla el aislamiento multi-proyecto.

**Clasificación: ④ — comportamiento inseguro para 0.2.**

**[N]** Consecuencia para la comparación de alternativas: el aislamiento de ámbito es una **puerta previa común** a A, B, C y D, no un rasgo diferenciador. Ninguna alternativa puede heredarlo. El benchmark debe tratar toda fuga entre proyectos como fallo duro, no como pérdida de precisión.

---

## 7. Segundo hallazgo crítico: la negación es invisible

**[H] Medido.** Dos recuerdos:

- «El cliente prefiere café con leche por la mañana»
- «El cliente **NO** prefiere café con leche»

La consulta `café` devuelve **los dos**, indistinguibles. La consulta `prefiere` también devuelve los dos.

**[H]** La causa es estructural, no del saneado: FTS5 indexa tokens, y «no» es un token más. Nada en el camino —ni el índice, ni el saneado, ni el orden— representa la polaridad del enunciado.

**[N]** B04-RF-19 exige preservar negación, condición, refutación y postura. El invariante I-07 lo repite. **[?]** Y es un problema que **ninguna** de las cuatro alternativas resuelve por sí sola: un modelo vectorial también sitúa «prefiere X» y «no prefiere X» a distancia mínima. La negación no es un problema de recuperación sino de **representación**, y remite a las dimensiones ortogonales que ADR-001 aprobó —confirmación en particular— y a la relación de postura apoyo/refutación que el spike 2 demostró añadible.

**Clasificación: ④ — comportamiento inseguro para 0.2.**

**[N]** Consecuencia para el benchmark: los casos de negación deben ser **adversariales y de fallo duro**, y deben ejecutarse también contra las alternativas B, C y D para evitar la conclusión falsa de que la señal semántica los resuelve.

---

## 8. Estados, borrado y redacción

**[H]** Lo verificado:

| Situación | Comportamiento real | Clase |
|---|---|---|
| Memoria archivada | **Sigue indexada y encontrable** por FTS5; se excluye después, en el filtro de vigencia | ② |
| Decisión archivada o sustituida | Igual: sigue indexada, se excluye por estado | ② |
| Memoria eliminada | `delete_memory` anula `content` en **todas** las revisiones; el trigger `memory_revisions_fts_au` retira la fila del índice en la misma transacción | ① |
| Mensaje redactado | `content` a `NULL` y estado `REDACTED`; el trigger retira su texto de `message_fts` | ① |
| Purga física del fichero | **No la hace la aplicación.** Requiere `VACUUM`, según demostró el spike 10 de ADR-001 | ⑤ |

**[N]** La decisión deliberada de indexar lo archivado y filtrarlo después está documentada en el puerto: «excluir lo no vigente es trabajo del dominio, no del repositorio». Es coherente en 0.1.

**[?]** Para 0.2 esa decisión debe reexaminarse a la luz del invariante I-02, que exige resolver privacidad, sensibilidad y marcas de no uso **antes** de ranking. Un índice que contiene contenido no elegible es seguro solo mientras **todos** sus consumidores apliquen la puerta correcta. Hoy hay un solo consumidor; con más señales y más etapas, esa garantía deja de ser estructural. No se resuelve aquí.

**[H]** Lo que **no** existe: marca de «no usar como memoria», sensibilidad, restricción por permiso, autoridad, confirmación, tiempo válido y corte de registro. Ninguna de las siete dimensiones canónicas de ADR-001 —salvo disponibilidad, en su forma degradada de enum heredado— participa hoy en la recuperación. **Clase ③.**

---

## 9. Explicación, límites y ausencia

**[H]**

| Obligación | Estado real | Clase |
|---|---|---|
| Explicación por resultado | Se exponen tres booleanos y la recencia; el criterio de orden es legible. No se emite razón de orden, de exclusión, ni procedencia, tiempo o criticidad | ② |
| Plan reproducible | No se registra ninguno | ③ |
| Límite objetivo / límite duro | Existe un único recorte aguas abajo, en el ensamblado de contexto: tope de elementos de conocimiento y presupuesto de tokens, ambos constantes por defecto en el código. No hay distinción objetivo/duro | ② |
| Estado parcial visible | El recorte es **silencioso**: nada en la salida indica que se descartó algo | ③ |
| Taxonomía de ausencia | No existe. Un resultado vacío no distingue «no hay», «no es reportable» y «no se pudo consultar» | ③ |
| Degradación ante fuente inaccesible | No contemplada | ③ |
| Operación activa y autorizada | `rank(query_text)` no recibe `operation_id`, modo, propósito ni permiso | ③ |

**[N]** No se transcriben aquí las cifras por defecto del recorte como si fueran tolerancias: son constantes de implementación de 0.1, no umbrales aprobados. El Registro de Tolerancias no está en el repositorio y **no se inventa ninguna cifra**.

---

## 10. Resumen de la línea base

**[H]** Lo que la línea base **sí** aporta y conviene conservar:

1. Sincronización índice/dato transaccional por trigger, con rollback conjunto probado.
2. Regenerabilidad del índice y `downgrade` limpio que no toca ninguna tabla base.
3. Saneado de consulta a prueba de entrada arbitraria, sin posibilidad de inyección de operadores.
4. Normalización de caso y diacríticos.
5. Orden determinista, estable y explicable, sin puntuación opaca, con desempate total.
6. Neutralidad tecnológica real: puerto sin dependencia de motor, dominio sin SQLite.
7. Exclusión efectiva del contenido eliminado, propagada al índice en la misma transacción.

**[H]** Lo que la línea base **no** aporta:

8. Aislamiento de ámbito — **④ inseguro**.
9. Preservación de la negación y la postura — **④ inseguro**.
10. Frase, prefijo, proximidad, variantes morfológicas y alias — ③.
11. Los dos ejes temporales — ③.
12. Resolución de entidad y no fusión de homónimos — ③.
13. Criticidad, suficiencia, taxonomía de ausencia y parcialidad visible — ③.
14. Plan reproducible y contexto de operación — ③.
15. Deduplicación con equivalencia material — ③.
16. Expansión escalonada E0–E5 — ③.

**[N]** Los puntos 8 y 9 son puertas previas comunes a las cuatro alternativas. Los puntos 1–7 son el activo que cualquier alternativa debe preservar, y la puerta 5 de ADR-002 —borrado y reconstrucción completos de índices y derivados— convierte el punto 2 en requisito, no en ventaja.

---

## 11. Condiciones de congelación

**[N]** ADR-002 §6 exige que la línea base se conserve **congelada** como control comparativo y no se modifique para favorecer a ninguna alternativa.

**[H]** En esta ronda no se ha modificado nada: ni `src/`, ni `tests/`, ni `migrations/`, ni configuración productiva. Toda la medición se hizo contra bases temporales creadas por la cadena canónica de Alembic, fuera del repositorio.

**[N]** La línea base queda identificada por el head de Alembic `61be4bb269bf` y por los cinco ficheros de la §3. Cualquier cambio futuro en ellos invalida las comparaciones ya ejecutadas y obliga a repetir la medición.

---

## 12. Incertidumbres de esta línea base

Todas **[?]**.

1. **No se ha medido rendimiento.** Ni latencia, ni tamaño de índice, ni escalado del barrido completo de candidatos. Sin Registro de Tolerancias no habría con qué comparar.
2. **No se ha medido sobre Windows.** El tokenizador, `secure_delete` y la purga pueden diferir en el SQLite empaquetado.
3. **No se ha medido con corpus realista.** Las sondas usaron unidades de documentos. El comportamiento del `OR` permisivo con miles de documentos es previsiblemente peor en precisión, pero no está medido.
4. **No se ha ejecutado el benchmark.** Este documento caracteriza; no puntúa.
5. **Regeneración desde el canon.** Que `knowledge_fts` pueda reconstruirse desde `memory_revisions` y `decision_revisions` está implícito en las sentencias de backfill de la migración, pero no existe una operación invocable ni una prueba que lo ejerza como tal.
6. **Interacción entre precedencia y conflicto.** `find_prevailing_decision` suprime el lado no prevaleciente en el ensamblado de contexto. Si RF-21 obliga a recuperar todos los lados elegibles, hay que decidir en qué capa actúa la precedencia. No se resuelve aquí.

---

**Siguiente movimiento único:** revisar esta línea base junto al inventario normativo y la especificación de benchmark, antes de ejecutar medición alguna.
