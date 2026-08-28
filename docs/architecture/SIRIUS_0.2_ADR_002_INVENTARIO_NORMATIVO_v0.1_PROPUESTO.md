# SIRIUS 0.2 — ADR-002 · Inventario normativo de recuperación, ranking e índices

**Versión:** 0.1
**Estado:** PROPUESTO · documento de análisis, no aprueba ni decide nada
**Fecha:** 25 de julio de 2026
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_01_INVENTARIO_Y_BASELINE_v0.1.md`
**Dependencia satisfecha:** ADR-001 v1.1 APROBADO
**No autoriza:** decisión de ADR-002, elección de alternativa A/B/C/D, implementación productiva, cambios en Sirius 0.1 ni merge.

---

## 1. Objeto

Inventariar, sin elegir todavía ninguna arquitectura, **qué está obligada a cumplir** la recuperación de Sirius 0.2: obligaciones B04-RF-01 a RF-32, delegaciones RED-027 a RED-034 y la parte aplicable de RED-040, familias PDP mínimas e invariantes del paquete.

Este documento no compara alternativas, no propone técnicas y no fija cifras.

---

## 2. Cómo leer este documento

Todo enunciado está marcado con una de estas tres etiquetas, sin excepción:

| Marca | Significado |
|---|---|
| **[H]** | **Hecho verificado.** Comprobado en el repositorio real en esta ronda: código, migraciones, pruebas o medición directa. Reproducible. |
| **[N]** | **Obligación normativa.** Procede de un documento de autoridad (ADR-001 aprobado, ADR-002 abierto, paquete de trabajo 01). No es negociable por el código de 0.1. |
| **[?]** | **Hipótesis o incertidumbre.** Interpretación propia, laguna documental o cuestión que requiere experimento o decisión posterior. **No** es base suficiente para decidir. |

Cuando un enunciado mezcla capas, se separa en varios.

---

## 3. Fuentes y su disponibilidad real

**[H]** Estado de las fuentes de autoridad **dentro del repositorio**, comprobado por búsqueda exhaustiva:

| Fuente | ¿Está en el repositorio? |
|---|---|
| `SIRIUS_0.2_ADR_001_MODELO_FISICO_v1.1_APROBADO.md` | **Sí** |
| `SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.1_ABIERTO.md` | **Sí** |
| `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_01_...v0.1.md` | **Sí** |
| Código y pruebas de Sirius 0.1 | **Sí** |
| Texto atómico de B04-RF-01 a RF-32 | **No** |
| Texto atómico de RED-027 a RED-034 y RED-040 | **No** |
| Definición atómica de las familias PDP | **No** |
| ARQ-00 v1.0 | **No** (solo citado) |
| Registro de Tolerancias | **No** (solo citado) |

**[H]** Lo único disponible en el repositorio sobre B04, RED y PDP son los resúmenes por grupo de las §4, §5 y §6 del paquete de trabajo 01. El propio paquete declara en su §2 que «materializa para el repositorio los contratos aprobados de B04, RED/PDP y ARQ-00 necesarios para el trabajo 01», así que se toma como la reformulación autorizada en repositorio.

**[?] Consecuencia metodológica, importante.** El paquete agrupa los RF en bloques (RF-01–04, RF-05–08, …) pero no enumera cada RF por separado. La asignación de una obligación concreta a un número de RF concreto que aparece en la §5 de este documento es **descomposición propia**, derivada literalmente del texto del grupo. Donde el grupo contiene exactamente tantas cláusulas como números de RF, la correspondencia es directa y se marca así; donde no, el reparto es interpretativo y se marca también. **Antes de cerrar ADR-002 hay que cotejar esta tabla contra el texto atómico de B04.** Ninguna obligación del paquete se ha perdido en el reparto: lo que puede estar mal es el número asignado, no la existencia de la obligación.

**[N]** Si el código de 0.1 contradice una obligación aprobada de 0.2, prevalece la obligación de 0.2. El código de 0.1 es línea base técnica, nunca rebaja del producto.

---

## 4. Invariantes obligatorios y su consecuencia para la recuperación

Los once invariantes de la §3 del paquete, con lo que cada uno exige específicamente de la recuperación.

| # | Invariante **[N]** | Consecuencia para la recuperación **[N]** | Estado observado en 0.1 **[H]** |
|---|---|---|---|
| I-01 | Fuente canónica única; FTS, índices, caches y resúmenes son derivados regenerables | Ningún índice puede ser consultado como autoridad; todo derivado debe poder destruirse y regenerarse desde el canon | Cumplido en forma: `knowledge_fts` y `message_fts` se pueblan por trigger y admiten `rebuild`; ningún caso de uso los lee como fuente de contenido |
| I-02 | Privacidad, permiso, existencia, ámbito, tiempo, confirmación, disponibilidad, sensibilidad y marcas de no uso se resuelven **antes** de ranking | Las puertas son previas al orden, no un filtro posterior ni un desempate | **Parcial**: existencia/disponibilidad se filtran antes; ámbito **no** se filtra, se usa como señal de orden; el resto de dimensiones no existen |
| I-03 | Contenido eliminado, purgado, no guardado, restringido no autorizado o fuera de ámbito **nunca** es candidato | Exclusión dura, no penalización | **Parcial**: eliminado sí queda excluido; «fuera de ámbito» **no** |
| I-04 | Multi-proyecto cerrado: no existe ampliación silenciosa de ámbito | Un proyecto no ve el contenido de otro bajo ninguna consulta | **Incumplido en 0.1** (medido, §6 de la línea base) |
| I-05 | Tiempo válido y corte de registro son independientes | Dos ejes temporales separados en la consulta y en el filtro | **Ausente**: 0.1 no tiene ningún eje de tiempo válido |
| I-06 | Homónimos no se fusionan; alias ambiguos no expanden sin resolución | Resolución de entidad por ID estable antes de expandir | **Ausente** |
| I-07 | Negación, condición, postura, apoyo/refutación y conflicto no se pierden | La recuperación conserva la polaridad y la condición del enunciado | **Ausente** (medido: la negación es invisible para el índice) |
| I-08 | Los críticos elegibles dominan el presupuesto; el límite duro produce estado parcial **visible** | Criticidad propagada y parcialidad señalizada, no silenciosa | **Ausente**: el recorte por presupuesto existe pero no marca parcialidad ni conoce criticidad |
| I-09 | Cada resultado debe ser explicable: coincidencia, ámbito, tiempo, estado, procedencia, criticidad y razón de orden | La salida transporta su propia justificación | **Parcial**: se exponen tres booleanos y la recencia; faltan tiempo, procedencia, criticidad y razón explícita de orden |
| I-10 | Ninguna tecnología concreta es obligatoria por producto | Neutralidad observable; la continuidad con FTS5 es valor, no excepción | Cumplido en forma: el puerto `KnowledgeSearchRepository` es un `Protocol` sin SQLAlchemy |
| I-11 | Solo una operación activa y autorizada puede iniciar una búsqueda interna | La recuperación exige contexto de operación | **Ausente**: `rank(query_text)` no recibe `operation_id`, modo, propósito ni permiso |

**[N]** La salida de ADR-002 es arquitectura de recuperación. No emite el paquete final de contexto, que pertenece a ADR-003B.

---

## 5. Inventario B04-RF-01 a RF-32

Las columnas «obligación» son **[N]**; las columnas «estado observado» son **[H]**; los comentarios entre corchetes marcados **[?]** son interpretación propia.

Clasificación del estado, según el §8 del paquete: `EXISTENTE` · `PARCIAL` · `AUSENTE` · `INSEGURO` (comportamiento existente pero no admisible para 0.2) · `OTRO-ADR`.

### 5.1 Petición, modo y aclaración — RF-01 a RF-04

**[?]** Reparto interpretativo: el grupo tiene dos frases y cuatro números.

| RF | Obligación **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-01 | La petición transporta consulta, `operation_id`, propósito y traza | AUSENTE | `RankRelevantKnowledgeUseCase.rank(query_text: str)` recibe únicamente texto |
| RF-02 | Modo M1–M5 explícito y permiso asociado | AUSENTE | No existe noción de modo en `src/` |
| RF-03 | Ámbito, tiempo, estados, criticidad, espacios, cardinalidad y límites declarados en la petición | AUSENTE en la petición; PARCIAL aguas abajo | Los límites existen, pero como constantes de ensamblado de contexto, no como parámetros de la petición |
| RF-04 | Toda ambigüedad material o falta de permiso bloquea o aclara **antes** de generar candidatos | AUSENTE | No hay puerta de aclaración; una consulta ambigua produce candidatos directamente |

### 5.2 Identidad, ámbito y tiempo — RF-05 a RF-08

**[H]** Correspondencia directa: el grupo tiene cuatro cláusulas y cuatro números.

| RF | Obligación **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-05 | Resolver entidades por ID estable | PARCIAL | Existen ids estables de memoria/decisión, pero no hay resolución de entidad: la consulta es texto libre contra el índice |
| RF-06 | Impedir la fusión de homónimos | AUSENTE | No hay noción de entidad ni de alias |
| RF-07 | Aplicar ámbitos global / proyecto / multi-proyecto cerrado | **INSEGURO** | El ámbito es señal de orden, no puerta: contenido de otro proyecto se devuelve (medido) |
| RF-08 | Soportar tiempo objetivo, tiempo válido, evento e historial con corte de registro | AUSENTE | 0.1 solo tiene `created_at`/`updated_at`, que son tiempo de registro |

### 5.3 Puertas y exclusiones — RF-09 a RF-13

**[?]** Reparto interpretativo: el grupo tiene cuatro frases y cinco números.

| RF | Obligación **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-09 | Las puertas se aplican antes de exposición **y** antes de ranking | PARCIAL | `rank_relevant_knowledge` filtra antes de ordenar, pero solo por vigencia y relación; el ámbito queda fuera de la puerta |
| RF-10 | Excluir eliminado y purgado | EXISTENTE | `delete_memory` anula `content` en todas las revisiones y el trigger retira la fila del índice; probado |
| RF-11 | Excluir no guardado y «no usar como memoria» | AUSENTE | No existe marca de no uso en el modelo de 0.1 |
| RF-12 | Estados especiales solo elegibles en modos autorizados | AUSENTE | No hay modos; el archivado se excluye siempre, sin excepción autorizable |
| RF-13 | La evidencia externa permanece atribuida y no canónica | OTRO-ADR / AUSENTE | 0.1 no incorpora evidencia externa a la recuperación |

### 5.4 Expansión escalonada E0–E5 — RF-14 a RF-18

**[N]** La política E0–E5 y sus puertas G1–G12 proceden de B04 y **no** son objeto de decisión en ADR-002.

**[?]** Reparto interpretativo por cláusulas del grupo.

| RF | Obligación **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-14 | Respetar E0–E5 y su orden | AUSENTE | No hay etapas: una sola pasada de índice más un barrido completo de candidatos |
| RF-15 | Empezar por exacto y estructurado | PARCIAL | Existe coincidencia estructurada (asunto de decisión, proyecto activo) pero no está escalonada respecto del léxico: ambas señales se calculan siempre |
| RF-16 | Después, variantes léxicas y alias confirmados | AUSENTE | Sin lematización, sin alias, sin prefijo (medido) |
| RF-17 | Solo después, significado o relaciones | N/A en 0.1 | No hay señal semántica ni relacional; su incorporación es justamente lo que ADR-002 decidirá |
| RF-18 | Fuentes e historial solo en etapa autorizada y cotejados con el estado vigente | PARCIAL | El historial existe (`get_history`) y el mensaje fuente se resuelve, pero no como etapa autorizada de expansión |

### 5.5 Fidelidad semántica — RF-19 a RF-21

**[H]** Correspondencia directa: tres frases, tres números.

| RF | Obligación **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-19 | Preservar negación, condición, refutación y postura | **INSEGURO** | Medido: la consulta «café» devuelve por igual «prefiere café» y «NO prefiere café» |
| RF-20 | Deduplicar solo con equivalencia material, incluidas coincidencia de ámbito y postura | AUSENTE | No hay deduplicación en la recuperación |
| RF-21 | Recuperar todos los lados elegibles de un conflicto sin resolverlo silenciosamente | PARCIAL / OTRO-ADR | `find_prevailing_decision` (B4e) resuelve precedencia y **suprime** el lado no prevaleciente en el ensamblado de contexto |

### 5.6 Ranking, criticidad, límites y ausencia — RF-22 a RF-26

**[H]** Correspondencia directa: cinco cláusulas, cinco números.

| RF | Obligación **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-22 | Ordenar solo elegibles | PARCIAL | Se ordenan solo vigentes y relacionados, pero «elegible» de 0.2 incluye ámbito, tiempo y sensibilidad, que no se comprueban |
| RF-23 | Propagar criticidad con regla y fuente | AUSENTE | No existe criticidad en el modelo ni en el orden |
| RF-24 | Respetar límite objetivo y límite duro | PARCIAL | Existen límites (tope de elementos y presupuesto de tokens) pero como una sola capa de recorte, sin distinción objetivo/duro |
| RF-25 | Adjudicar suficiencia y taxonomía de ausencia | AUSENTE | No hay puerta de suficiencia ni tipos de ausencia; un resultado vacío es indistinguible de una consulta no ejecutable |
| RF-26 | Mantener ausencia y no-reportable indistinguibles externamente cuando revelar la diferencia filtre existencia | AUSENTE | Al no existir la distinción, tampoco existe la protección |

### 5.7 Contrato, explicación y trazabilidad — RF-27 a RF-32

**[H]** Correspondencia directa: seis frases, seis números.

| RF | Obligación **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-27 | Entregar resultados, estados, evidencia, criticidad, orden inicial, límites y suficiencia | PARCIAL | Se entrega una tupla ordenada con tres booleanos por elemento; faltan evidencia, criticidad, límites aplicados y suficiencia |
| RF-28 | Explicar cada resultado | PARCIAL | Los tres booleanos y la recencia son inspeccionables, pero no se emite la razón de orden ni la de exclusión |
| RF-29 | Registrar un plan reproducible | AUSENTE | No se registra plan alguno |
| RF-30 | Permitir búsqueda interna solo desde operación activa | AUSENTE | Ver RF-01 |
| RF-31 | Mantener neutralidad tecnológica | EXISTENTE | El puerto es un `Protocol` sin dependencia de motor; el dominio no conoce SQLite |
| RF-32 | Degradar de forma segura y reproducible | PARCIAL | Consulta vacía o solo puntuación devuelve vacío sin error; no hay degradación ante fuente inaccesible |

### 5.8 Comprobación de cobertura

**[H]** Los 32 números RF-01…RF-32 aparecen exactamente una vez en las tablas 5.1–5.7. Sin huecos, sin duplicados.

Resumen del estado observado:

| Clasificación | RF |
|---|---|
| `EXISTENTE` (3) | RF-10, RF-31, y RF-05 solo en su parte de identificadores |
| `PARCIAL` (11) | RF-03, RF-05, RF-09, RF-15, RF-18, RF-21, RF-22, RF-24, RF-27, RF-28, RF-32 |
| `AUSENTE` (15) | RF-01, RF-02, RF-04, RF-06, RF-08, RF-11, RF-12, RF-14, RF-16, RF-20, RF-23, RF-25, RF-26, RF-29, RF-30 |
| `INSEGURO` para 0.2 (2) | **RF-07** (ámbito), **RF-19** (negación) |
| `OTRO-ADR` o no aplicable a 0.1 (2) | RF-13, RF-17 |

**[?]** Un elemento puede figurar en dos filas cuando su obligación se cumple en un aspecto y no en otro (RF-05, RF-13, RF-21). Las cifras entre paréntesis cuentan la clasificación principal.

**[N]** Los dos `INSEGURO` son los hallazgos que condicionan cualquier alternativa: **ninguna** de A, B, C o D es admisible si hereda el tratamiento actual del ámbito o de la negación. No son defectos de Sirius 0.1 —cumplen su propio contrato S7.5— sino comportamientos que 0.2 no puede conservar.

---

## 6. Delegaciones RED que deben quedar trazadas

**[N]** Cada delegación exige una traza explícita en la arquitectura resultante. **[H]** El estado es lo observado en 0.1.

| RED | Delegación **[N]** | Estado **[H]** | Nota |
|---|---|---|---|
| RED-027 | Modo M1–M5, propósito, permisos y aclaración antes de buscar | AUSENTE | Ver RF-01, RF-02, RF-04 |
| RED-028 | Tiempo objetivo y corte de registro fijados antes de recuperar | AUSENTE | 0.1 no tiene los ejes; ADR-001 los declara obligatorios y ortogonales para 0.2 |
| RED-029 | Plan reproducible con espacios, puertas, etapas, parada y limitaciones | AUSENTE | Ver RF-29 |
| RED-030 | Cardinalidad, deduplicación prudente y evidencia plural | AUSENTE | Ver RF-20; la evidencia plural depende de la procedencia múltiple que ADR-001 validó como añadible |
| RED-031 | Taxonomía de ausencia sin falsos «no existe» | AUSENTE | Ver RF-25, RF-26 |
| RED-032 | Tolerancias diferenciales de texto, estado, conteo y tiempo | **BLOQUEADO** | **[H]** El Registro de Tolerancias no está en el repositorio. No se inventa ninguna cifra |
| RED-033 | Equivalencia semántica observable sin imponer técnica | AUSENTE | Es la incertidumbre central que ADR-002 debe falsar |
| RED-034 | Salida parcial reproducible y fuente necesaria inaccesible | AUSENTE | Ver RF-32; el recorte actual es silencioso |
| RED-040 (parte aplicable) | Un único reintento acotado entre recuperación y contexto, sin bucle | AUSENTE | **[N]** En este trabajo **solo se registra la interfaz**; ADR-003B no se decide aquí |

---

## 7. Familias PDP mínimas

**[N]** El benchmark debe cubrir como mínimo estas familias. **[H]** La columna de cobertura actual refleja lo que las pruebas de 0.1 ya ejercitan.

| Familia | Contenido **[N]** | ¿Cubierta hoy por pruebas de 0.1? **[H]** |
|---|---|---|
| F01 | Consulta ordinaria actual | **Sí, parcialmente**: `test_rank_relevant_knowledge.py` cubre orden, desempate y coincidencia real de índice |
| F02 | Tiempo válido | **No**: el eje no existe en 0.1 |
| F03 | Corte de conocimiento | **No**: el eje no existe en 0.1 |
| F10 | Diferencias materiales, derivados y equivalencias | **No** para diferencias y equivalencias; **sí** para derivados: `test_search_index_sync.py` prueba la sincronización transaccional del índice |
| F15 | Condición, negación, relaciones y composición | **No**, en ninguna de las cuatro |
| F22 | Neutralidad y portabilidad observable | **Parcialmente**: existe el puerto y un doble simulado, pero no una prueba de portabilidad |
| F23 | Ausencia, parcialidad, fuente inaccesible y degradación segura | **Parcialmente**: solo consulta vacía y caracteres especiales |
| F24 | Trazabilidad del plan, cuando aplique | **No** |

**[H]** Pruebas existentes con relación directa a recuperación, verificadas por lectura: `tests/integration/test_search_index_sync.py` (9 pruebas), `tests/integration/test_rank_relevant_knowledge.py` (8), `tests/unit/test_relevance_domain.py` (15), `tests/integration/test_fts5_availability.py` (2) y la parte FTS5 de `tests/integration/test_migrations.py`.

---

## 8. Herencia obligatoria de ADR-001

**[N]** Consecuencias de ADR-001 v1.1 APROBADO que atan a ADR-002 sin necesidad de nueva discusión:

1. Índices, FTS, caches, resúmenes, vistas y paquetes de contexto son **derivados regenerables**; ninguno puede consultarse como autoridad ni sobrevivir semánticamente a la eliminación de su fuente (consecuencias 1 y 2).
2. El borrado debe destruir explícitamente contenido, procedencia recuperable y **todos** los derivados afectados (consecuencia 3). **[N]** Toda alternativa de ADR-002 que introduzca un índice nuevo hereda esta obligación y la puerta 5 de ADR-002 la exige de forma explícita.
3. Tiempo válido y tiempo de registro permanecen separados (consecuencia 6).
4. Confirmación, validez, disponibilidad, sensibilidad, temporalidad, ámbito y autoridad permanecen **ortogonales** (consecuencia 7). **[N]** La recuperación debe poder filtrar por cada una por separado; ninguna puede condensarse en un estado único.
5. El ámbito multi-proyecto es **cerrado y se filtra antes de recuperación y ranking** (consecuencia 8). **[H]** Esta es exactamente la obligación que 0.1 no cumple.

---

## 9. Incertidumbres pendientes

Todas **[?]**. Ninguna se resuelve en este documento.

1. **Texto atómico de B04-RF-01–32, RED-027–034 y las familias PDP.** No está en el repositorio. El reparto por número de la §5 debe cotejarse antes de cerrar ADR-002.
2. **Registro de Tolerancias.** No está en el repositorio. Sin él no puede fijarse ninguna puerta cuantitativa: ni recall crítico, ni latencia, ni tamaño, ni coste. **No se ha inventado ninguna cifra en este documento ni en la especificación de benchmark.**
3. **Definición operativa de «recall crítico».** La puerta 1 de ADR-002 lo exige, pero «crítico» depende de la criticidad de RF-23, que no existe todavía en ningún modelo.
4. **Umbral de suficiencia.** Las alternativas B, C y D se definen por incorporar señal adicional «solo después de fallar la puerta de suficiencia». Sin definir esa puerta, B, C y D no son distinguibles de A en un benchmark.
5. **Frontera exacta con ADR-003B.** RF-27 exige entregar suficiencia y límites; el paquete de contexto es de ADR-003B. Hay que fijar dónde termina el contrato de recuperación.
6. **Frontera con ADR-003A y ADR-003C.** No inventariadas aquí porque el paquete no las incluye en el trabajo 01.
7. **Alcance de la resolución de entidad.** RF-05 y RF-06 exigen ID estable y no fusión de homónimos. Si eso obliga a un registro de entidades y alias, es diseño de modelo, no de recuperación: podría pertenecer a la arquitectura consolidada y no a ADR-002.
8. **Tratamiento del conflicto frente a la precedencia ya aprobada en 0.1.** RF-21 exige recuperar todos los lados elegibles; `find_prevailing_decision` hoy suprime el no prevaleciente. Hay que decidir si la precedencia se aplica en recuperación, en contexto o solo en presentación.
9. **Copia física del contenido en el índice derivado.** **[H]** `knowledge_fts` almacena una copia literal del texto (§4 de la línea base). **[?]** Si 0.2 exige que ningún derivado retenga contenido canónico en claro, esto condiciona el diseño de todos los índices, incluidos los de las alternativas B, C y D.
10. **Coste de la verificación en Windows.** ADR-001 dejó pendiente confirmar `secure_delete` y la purga sobre el ejecutable real. Todo índice nuevo que ADR-002 introduzca hereda esa verificación pendiente.

---

## 10. Lo que este documento no decide

**[N]** No elige entre A, B, C y D. No propone embeddings, vectores, grafos, extensiones ni fórmulas de fusión. No fija cifras de latencia, coste o tamaño. No modifica `src/`, `tests/`, `migrations/` ni configuración productiva. No abre ni cierra ningún otro ADR.

---

**Siguiente movimiento único:** revisar este inventario junto con la línea base FTS5 y la especificación de benchmark, y decidir si el trabajo 01 se da por cerrado antes de ejecutar la línea base.
