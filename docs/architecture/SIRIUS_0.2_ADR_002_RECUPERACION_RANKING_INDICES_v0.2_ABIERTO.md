# SIRIUS 0.2 — ADR-002

## Recuperación, ranking e índices

**Versión:** 0.2
**Estado:** ABIERTO · PROPUESTO PARA INVESTIGACIÓN Y DECISIÓN
**Fecha de reformulación:** 25 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.1_ABIERTO.md`, que se conserva sin modificar
**Autoridad de apertura:** Usuario / Proyecto Sirius
**Dependencias satisfechas:** ADR-001 v1.1 APROBADO · **B04 v1.0 APROBADO (23 de julio de 2026)**
**No autoriza:** implementación, cambios en Sirius 0.1, selección anticipada de tecnología semántica ni merge.

---

## 0. Por qué se reformula

**[N]** La v0.1 se abrió antes de que la fuente canónica de B04 estuviera verificada, y planteaba como alternativas de ADR-002 lo que en realidad ya era **decisión de producto cerrada**.

`SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO` es canónico desde el 23 de julio de 2026. Quedaron aprobados:

- la **alternativa B de B04**;
- B04-D01–D16, B04-RF-01–32, B04-CA-01–50, B04-M01–21;
- la política **E0–E5**;
- las puertas **G1–G12**;
- las paradas **S1–S7**.

**[N]** ADR-002 **no puede reabrir nada de eso**. Su objeto es la **arquitectura técnica** que materializa el comportamiento aprobado.

Consecuencia directa sobre la v0.1: sus alternativas A, B, C y D estaban formuladas como opciones de comportamiento —«solo léxica», «semántica tardía», «relacional tardía»— cuando la incorporación tardía de significado y relaciones **ya está aprobada** por B04-RF-17. Esas alternativas se retiran y se sustituyen por realizaciones técnicas, §3.

**[N]** En particular, **la variante solo léxica deja de ser candidata**. Se conserva como **control y como hipótesis de falsación**, nunca como producto alternativo equivalente, porque incumple la expansión aprobada.

---

## 1. Pregunta material

> **¿Qué arquitectura técnica de índices, señales y ranking implementa de forma mínima, explicable, borrable, portable y medible la alternativa B y el contrato B04 ya aprobados, preservando FTS5 cuando aporte valor sin convertirlo en excepción?**

**[N]** Los cinco adjetivos no son retórica: cada uno corresponde a una puerta de la §4 y a obligaciones concretas de B04 —mínima (RF-14), explicable (RF-22, RF-28, RF-29), borrable (ADR-001 c.2 y c.3), portable (RF-31) y medible (RF-25, RF-26 y el Registro de Tolerancias pendiente).

---

## 2. Entradas obligatorias

**[N]**

- B04 v1.0 APROBADO: D01–D16, RF-01–32, CA-01–50, M01–21, E0–E5, G1–G12, S1–S7.
- Contrato de suficiencia y contrato de criticidad (§2.3 y §2.4 del paquete 01B).
- Modelo aprobado por ADR-001 v1.1 y sus siete dimensiones ortogonales.
- Mapeo canónico RED-027–034.
- Familias PDP: F01–F06, F10, F11, F14, F15, F22, F23, F24.
- Línea base FTS5 de Sirius 0.1, medida y congelada.
- B01 y CT-02.
- Registro de Tolerancias **cuando exista**.

**[N]** **RED-040 pertenece a B05/ADR-003B.** ADR-002 solo **registra la interfaz** de reintento acotado: no la diseña y **no la usa como requisito propio de selección técnica**.

---

## 3. Alternativas técnicas excluyentes

**[N]** Todas son realizaciones **compatibles con B04-B**. Ninguna puede reabrir E0–E5, G1–G12, S1–S7 ni la incorporación tardía aprobada de significado y relaciones.

| Id | Sustrato léxico | Señal semántica | Relaciones |
|---|---|---|---|
| **T1** | FTS5 como base | Tardía | Resueltas **desde el canon**, sin índice relacional dedicado |
| **T2** | FTS5 como base | Tardía | **Índice relacional derivado tardío** |
| **T3** | Índice léxico **alternativo** | Tardía | Resueltas desde el canon |
| **T4** | Índice léxico **alternativo** | Tardía | **Índice relacional derivado** |

**[N]** La partición es ortogonal en dos ejes: *sustrato léxico* (conservar FTS5 o sustituirlo) × *relaciones* (desde el canon o mediante índice derivado). La señal semántica tardía es común a las cuatro porque **B04-RF-17 la impone**, no porque se elija.

**[N]** El paquete 01B admite ajustar la formulación si el análisis demuestra una partición más limpia, siempre que no reabra lo aprobado.

### 3.1 Control de falsación

**[N]** **T0 — solo léxica y estructurada**, es decir, la línea base de Sirius 0.1 congelada.

No es candidata. Se ejecuta para dos cosas: dar suelo de comparación y **falsar** la hipótesis de que la señal tardía es necesaria. **[H]** Su comportamiento ya está medido y contradice B04 en tres puntos —RF-06, RF-14 y RF-19—, así que su papel es exclusivamente instrumental.

### 3.2 Lo que las cuatro comparten y no diferencia a ninguna

**[N]** Estas obligaciones son **puertas previas comunes**. Ninguna realización técnica puede presentarlas como ventaja, y ninguna puede omitirlas:

1. **Aislamiento de ámbito** aplicado como puerta antes de candidatos — RF-06, RF-09.
2. **Expansión escalonada sin salto a recuperación amplia** — RF-14, RF-15, RF-16.
3. **Validación de sujeto, polaridad, condición y tiempo** en la etapa de significado y relaciones — RF-17, RF-19.
4. **Borrado y regeneración completos** de todo índice derivado, desde el canon — ADR-001 c.2 y c.3.
5. **Petición completa y operación activa** — RF-01, RF-30.
6. **Plan reproducible y explicación por resultado** — RF-22, RF-28, RF-29.

**[H]** Las tres primeras son exactamente los tres hallazgos clasificados como inseguros en la línea base. La elección técnica **no las resuelve**: las presupone.

---

## 4. Puertas de decisión

**[N]** Una realización queda descartada si incumple cualquiera de estas puertas. Se conservan las ocho de la v0.1 y se trazan al RF canónico.

| # | Puerta | Traza canónica |
|---|---|---|
| 1 | Recall crítico insuficiente | RF-23, RF-25 |
| 2 | Contaminación por contenido no pertinente, prohibido, eliminado, restringido o fuera de ámbito | RF-10, RF-11, RF-12, RF-06 |
| 3 | Ausencia de explicación reproducible del resultado | RF-22, RF-28, RF-29 |
| 4 | Inestabilidad material de orden o selección bajo entradas equivalentes | RF-22, RED-033 |
| 5 | Imposibilidad de borrar o reconstruir completamente sus índices y derivados | ADR-001 c.2, c.3 |
| 6 | Acoplamiento a un proveedor concreto | RF-31 |
| 7 | Coste, latencia o complejidad incompatibles con el Registro de Tolerancias | pendiente del Registro |
| 8 | Incumplimiento de aislamiento multi-proyecto, tiempo válido, corte de conocimiento, negación o conflicto | RF-06, RF-07, RF-08, RF-19, RF-21 |
| **9** | **Salto a recuperación amplia**: resolver en una etapa lo que exige escalonamiento, aunque el resultado final sea correcto | **RF-14** |

**[N]** La puerta 9 es nueva en la v0.2 y es la única que puede descartar una realización **con resultados perfectos**. Procede directamente del texto canónico de RF-14.

**[N]** La continuidad con FTS5 es un **valor favorable, nunca una excepción a las puertas**. Se conserva literalmente de la v0.1.

**[?]** Solo la puerta 7 depende del Registro de Tolerancias. Las puertas 2, 5, 6, 8 y 9 son evaluables ya en forma booleana; las puertas 1, 3 y 4 lo son parcialmente. Es decir: **ADR-002 puede descartar realizaciones antes de que exista el Registro, pero no puede elegir una.**

---

## 5. Evidencia requerida

**[N]** Se conserva la de la v0.1, corregida:

- Benchmark versionado por familias y casos, **respetando B04-CA-01–50 y el PDP como canónicos** y distinguiendo los tres niveles de caso.
- Línea base FTS5 reproducible y congelada — **[H]** ya medida y documentada.
- Ablaciones por señal y por etapa, incluida la que aísla la **validación de polaridad** frente a la señal cruda.
- Pruebas positivas, negativas y adversariales de negación, tiempo válido, corte de registro, ámbito, soporte plural, conflicto y ausencia.
- Pruebas de deduplicación prudente con equivalencia material, y de cardinalidad declarada.
- Pruebas de fuente inaccesible y degradación parcial reproducible.
- **Conformidad de etapa**: que cada resolución ocurra en la etapa esperada y que la transición obedezca a insuficiencia contrastada.
- Borrado transaccional y regeneración **desde el canon** de cada índice o derivado.
- Medición de latencia, coste, tamaño y estabilidad conforme al Registro de Tolerancias, **cuando exista**.
- Trazas minimizadas que permitan explicar por qué entró, salió u ocupó una posición cada resultado.

---

## 6. Línea base heredada

**[N]** Sirius 0.1 aporta una base real que **debe medirse, no presumirse**: FTS5, `KnowledgeSearchRepository`, `RankRelevantKnowledgeUseCase`, ranking de dominio puro, filtros y búsquedas locales existentes.

**[H]** Ya está medida. Aporta siete capacidades que conviene preservar —sincronización transaccional, regenerabilidad, saneado robusto, normalización de diacríticos, orden determinista y explicable, neutralidad tecnológica real y exclusión efectiva de lo eliminado— y contradice B04 en tres puntos: RF-06, RF-14 y RF-19.

**[N]** La línea base se conserva **congelada** como control comparativo, identificada por el head de Alembic `61be4bb269bf`. **No se modifica para favorecer a ninguna realización técnica.**

---

## 7. Método de cierre

**[N]**

1. ~~Reconstruir el contrato exacto de B04, RED y PDP aplicable.~~ **Hecho**: inventario normativo v0.2, 32/32 RF exactos y mapeo RED canónico.
2. ~~Ejecutar la línea base FTS5.~~ **Hecho en su parte de caracterización**; queda pendiente ejecutarla contra los casos canónicos cuando el nivel 1 pueda instanciarse.
3. **Fijar el Registro de Tolerancias**, separando lo ya congelado en B04/PDP de lo realmente delegado a Arquitectura, y obtener aprobación explícita. **[N]** Paquete siguiente.
4. Materializar corpus, referencias y métricas **antes** de observar resultados.
5. Implementar solo los prototipos mínimos necesarios para falsar T1, T2, T3 y T4.
6. Ejecutar benchmark y ablaciones.
7. Realizar una auditoría adversarial completa.
8. Corregir únicamente hallazgos demostrables.
9. Emitir ADR-002 final con una recomendación principal y sus consecuencias.
10. Obtener aprobación explícita del usuario.

**[N]** El paso 3 es nuevo y es **bloqueante** para los pasos 6 en adelante: sin tolerancias, el benchmark descarta pero no elige.

---

## 8. Decisiones que este documento no toma

**[N]** No decide todavía:

- embeddings definitivos ni modelo de embedding;
- `sqlite-vec` u otra extensión;
- RRF u otra fórmula de fusión;
- grafo, RDF o motor relacional especializado;
- si el sustrato léxico sigue siendo FTS5 o se sustituye;
- si las relaciones se resuelven desde el canon o mediante índice derivado;
- cifras de latencia, coste, tamaño o estabilidad;
- estructura final de tablas, carpetas o módulos;
- implementación productiva.

**[N]** Y **no reabre**: la alternativa B de B04, D01–D16, RF-01–32, CA-01–50, M01–21, E0–E5, G1–G12 ni S1–S7.

---

## 9. Siguiente movimiento único

**Abrir el paquete específico del Registro de Tolerancias**: recuperar las tolerancias ya congeladas en B04/PDP, identificar solo las cifras realmente delegadas a Arquitectura, proponer el Registro v0.1 y obtener aprobación explícita antes de ejecutar cualquier decisión dependiente de latencia, coste, tamaño o estabilidad.

No se construye corpus, no se implementa prototipo y no se ejecuta benchmark hasta entonces.
