# SIRIUS 0.2 — ADR-002

## Recuperación, ranking e índices

**Versión:** 0.3
**Estado:** ABIERTO · PROPUESTO PARA INVESTIGACIÓN Y DECISIÓN
**Fecha de reformulación:** 26 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.2_ABIERTO.md`, que **se conserva sin modificar**
**Autoridad de la corrección:** `SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md` y `SIRIUS_0.2_ADR_002_NOTA_SUPERACION_02_PARTICION_CANDIDATOS_v1.0_APROBADA.md`
**Dependencias satisfechas:** ADR-001 v1.1 APROBADO · **B04 v1.0 APROBADO (23 de julio de 2026)** · **ARQ-00 v1.0 APROBADO (25 de julio de 2026)** · `SRC-ADR002-01` satisfecha (26 de julio de 2026)
**No autoriza:** implementación, cambios en Sirius 0.1, ejecución de T0 o de candidatos, corrección o congelación del corpus, aprobación de `ADR002-TOL-207`, selección anticipada de tecnología semántica ni merge.

Marcas: **[H]** hecho verificado · **[N]** obligación normativa canónica · **[?]** hipótesis o incertidumbre.

---

## 0. Por qué se reformula

**[N]** La v0.2 corrigió con acierto una premisa de la v0.1 —B04 v1.0 es canónico y ADR-002 no puede reabrir la política de producto— pero **se excedió al aplicarla**: retiró las cuatro alternativas mínimas de `ARQ-00 v1.0 APROBADO` §23 y las sustituyó por una partición propia, `T1–T4`, apoyándose en una lectura de `B04-RF-17` que `B04-RF-31` contradice.

**[H]** La auditoría adversarial independiente lo demostró y el usuario resolvió la cuestión. La corrección se materializa en la **Resolución de la partición de candidatos v1.0 APROBADA**, que esta versión aplica.

**[N]** Qué cambia exactamente respecto de la v0.2:

| Punto | v0.2 | **v0.3** |
|---|---|---|
| Universo de candidatos | `T1–T4`, particionados por sustrato léxico × relaciones | **`ADR002-A/B/C/D`**, las alternativas mínimas de ARQ-00 §23 |
| Señal semántica vectorial | Común y obligatoria en las cuatro | **Eje de contraste**, no obligación |
| «Solo léxica» | «Deja de ser candidata» | **`ADR002-A` es candidato completo y puede ser recomendado** |
| «Solo relacional» | No existía como candidato | **`ADR002-C` es candidato completo y puede ser recomendado** |
| Orden de etapas tardías | No expresado | **Restricción explícita de `ADR002-D`** |
| Sustrato léxico y materialización relacional | Ejes principales | **Ejes contingentes**, abiertos solo por evidencia |
| `T0` | Control de falsación | **Sin cambios**: control de falsación, no candidato |

**[N]** Qué **no** cambia: las nueve puertas de decisión, la evidencia requerida, las seis puertas previas comunes, la línea base congelada, el método de cierre y la lista de decisiones no tomadas se conservan de la v0.2, con las etiquetas de candidato actualizadas.

**[N]** Esta versión **no reabre** nada de B04: la alternativa B, `B04-D01–D16`, `B04-RF-01–32`, `B04-CA-01–50`, `B04-M01–21`, la política `E0–E5`, las puertas `G1–G12` y las paradas `S1–S7` siguen intactas.

---

## 1. Pregunta material

> **¿Qué arquitectura técnica de índices, señales y ranking implementa de forma mínima, explicable, borrable, portable y medible la alternativa B y el contrato B04 ya aprobados, preservando FTS5 cuando aporte valor sin convertirlo en excepción?**

**[N]** Se conserva literalmente de la v0.2. Los cinco adjetivos corresponden a puertas de la §4 y a obligaciones concretas de B04 —mínima (RF-14), explicable (RF-22, RF-28, RF-29), borrable (ADR-001 c.2 y c.3), portable (RF-31) y medible (RF-25, RF-26 y el Registro de Tolerancias).

**[N]** Corolario que la v0.2 no extraía: si la pregunta es **qué** arquitectura técnica implementa el contrato, entonces **cuántas señales tardías hacen falta es parte de la pregunta, no de la respuesta**. Fijar la señal semántica como común a todos los candidatos respondía la pregunta antes de medir.

---

## 2. Entradas obligatorias

**[N]** Sin cambios respecto de la v0.2, más una:

- B04 v1.0 APROBADO: D01–D16, RF-01–32, CA-01–50, M01–21, E0–E5, G1–G12, S1–S7.
- **ARQ-00 v1.0 APROBADO §23: las cuatro alternativas mínimas.** *(entrada explicitada en la v0.3)*
- Contrato de suficiencia y contrato de criticidad (§2.3 y §2.4 del paquete 01B).
- Modelo aprobado por ADR-001 v1.1 y sus siete dimensiones ortogonales.
- Mapeo canónico RED-027–034 y el Anexo B del Plan de Pruebas.
- Familias PDP: F01–F06, F10, F11, F14, F15, F22, F23, F24.
- Línea base FTS5 de Sirius 0.1, medida y congelada.
- B01 y CT-02.
- Registro de Tolerancias v0.4, aprobado el 26 de julio de 2026, y su nota de superación 02.

**[N]** **RED-040 pertenece a B05/ADR-003B.** ADR-002 solo **registra la interfaz** de reintento acotado: no la diseña y **no la usa como requisito propio de selección técnica**. Sin cambios.

---

## 3. Candidatos — las cuatro alternativas mínimas de ARQ-00 §23

**[N]** Todas son realizaciones **compatibles con B04-B**. Ninguna puede reabrir `E0–E5`, `G1–G12`, `S1–S7` ni la política escalonada aprobada.

| Id | Nombre | Señal tardía habilitada | Definición canónica (ARQ-00 §23) |
|---|---|---|---|
| **`ADR002-A`** | Léxica/estructurada | **Ninguna adicional** | Expansión escalonada **solo léxica/estructurada en todas las etapas E0–E5** |
| **`ADR002-B`** | Semántica vectorial tardía | **Semántica vectorial** | Expansión escalonada léxica/estructurada con señal semántica **vectorial** únicamente en etapas tardías tras fallar la puerta de suficiencia |
| **`ADR002-C`** | Relacional explícita tardía | **Relacional explícita** | Expansión escalonada léxica/estructurada con señal relacional explícita únicamente en etapas tardías tras fallar la puerta de suficiencia |
| **`ADR002-D`** | Semántica y relacional separadas | **Ambas, en etapas distintas** | Expansión escalonada con señales semántica y relacional en etapas tardías distintas y orden predefinido; **nunca coordinación simultánea fuera de la etapa autorizada** |

**[N]** Las cuatro son **candidatos completos**. Ninguna es control, ninguna está degradada de antemano y **cualquiera de las cuatro puede ser la recomendación principal de ADR-002** si supera las puertas y aporta mejora material. En particular, `ADR002-A` y `ADR002-C` **no** son controles.

### 3.1 La etapa E3 es obligatoria; la señal vectorial no

**[N]** Texto canónico:

> **B04-RF-17** — Expandir a significado y relaciones con validación explícita de sujeto, polaridad, condición y tiempo.
>
> **B04-RF-31** — Mantener neutralidad tecnológica: ninguna obligación exige embeddings, RAG, FTS, vectores, grafos o un modelo concreto.
>
> **B04 §8** — [problema que el bloque debe impedir] Atar el contrato a embeddings, RAG, FTS, grafos, un modelo o una base concreta.

**[N]** Consecuencias, todas obligatorias:

1. **Todo candidato ejecuta `E3`** —significado y relaciones— con validación explícita de sujeto, polaridad, condición y tiempo. Ninguno puede omitirla.
2. `RF-17` obliga al **comportamiento** de `E3`, no a una realización concreta. `ADR002-A` debe satisfacer `E3` por medios léxico-estructurados y responderá por `B04-M02`, `B04-M17` y `B04-M18` como cualquier otro.
3. **Ningún candidato está obligado a incorporar una señal semántica vectorial.** Qué señal tardía aporta valor material es exactamente lo que el benchmark debe medir.
4. ARQ-00 §23 prohíbe decidir «embeddings definitivos, sqlite-vec, RRF, grafo/RDF y modelo de embedding **hasta que la evidencia los justifique**». Hacer obligatoria la señal vectorial en las cuatro realizaciones sería decidirlos por construcción.

### 3.2 Restricción propia de `ADR002-D`

**[N]** `ADR002-D` no es «`B` más `C`». Sus tres restricciones son acumulativas y obligatorias:

1. señales semántica y relacional en **etapas tardías distintas**;
2. con **orden predefinido**, declarado y congelado en la ficha **antes** de ejecutar;
3. **sin coordinación simultánea fuera de la etapa autorizada**.

**[N]** Anclaje canónico directo:

> **B04-D15** (APROBADA) — La coordinación solo combina señales del mismo espacio y familia de la etapa activa; **no adelanta espacios posteriores ni sustituye la política escalonada**.

**[N]** Un `ADR002-D` que coordine ambas señales simultáneamente, o que no declare su orden de etapas antes de ejecutar, incumple `B04-D15` y la **puerta 9**. La restricción es lo que impide que la política aprobada —alternativa B de B04— derive de hecho hacia la alternativa C de B04, que B04 §14.1 clasificó como «RESERVA TÉCNICA, NO POLÍTICA PRINCIPAL».

### 3.3 Control de falsación — `T0`

**[N]** **`T0` — línea base congelada de Sirius 0.1**, identificada por el head de Alembic `61be4bb269bf`.

**No es candidata.** Se ejecuta para dos cosas: dar suelo de comparación y **falsar** la hipótesis de que la señal tardía es necesaria. **[H]** Su comportamiento ya está medido y contradice B04 en tres puntos —RF-06, RF-14 y RF-19—, así que su papel es exclusivamente instrumental.

**[N]** **`T0` no es `ADR002-A`.** `T0` es Sirius 0.1 tal como está: sin `E0–E5`, sin `G1–G12` como puertas, sin `S1–S7`, y con tres incumplimientos medidos. `ADR002-A` es una realización **correcta** del contrato B04 cuyas señales son léxicas y estructuradas. Confundirlos convertiría una alternativa mínima en un control, que es precisamente lo que la Resolución v1.0 prohíbe.

### 3.4 Ejes contingentes — herencia de `T1–T4`

**[N]** La partición `T1–T4` de la v0.2 queda **superada como universo principal**. No se borra ni se reescribe: la v0.2 se conserva como historial. Lo que se conserva con valor prospectivo son sus dos ejes técnicos, reclasificados:

| Eje | Contraste | Origen en `T1–T4` |
|---|---|---|
| **`EJE-1` · Sustrato léxico** | FTS5 medido **frente a** sustrato léxico alternativo | `T1/T2` frente a `T3/T4` |
| **`EJE-2` · Materialización de relaciones** | Resueltas **desde el canon** frente a **índice relacional derivado** | `T1/T3` frente a `T2/T4` |

**[N]** **Regla de contención, obligatoria:**

1. **Primera ronda:** `T0` (control) + `ADR002-A`, `ADR002-B`, `ADR002-C`, `ADR002-D`, **todos sobre el mismo sustrato léxico FTS5 medido y la misma infraestructura común**. Cinco fichas.
2. `EJE-1` y `EJE-2` **solo se abren después** de la comparación primaria, y **solo cuando una puerta o un fallo sea atribuible a ese eje**.
3. **Máximo dos fichas adicionales** por apertura contingente, cada una con su justificación. **No se ejecuta el producto cartesiano** `A/B/C/D × sustratos × materialización relacional`.
4. Las **ablaciones de nivel 3** miden la aportación marginal sin multiplicar candidatos: `AB-3` aísla la señal tardía y `AB-4` separa la señal cruda de la validación de polaridad que `RF-17` exige.
5. Abrir un eje contingente **no retira** ninguna de las cuatro alternativas mínimas.

**[N]** `EJE-2` no debe confundirse con `ADR002-C`. `ADR002-C` decide **si existe** una señal relacional explícita tardía; `EJE-2` decide **cómo se materializa** —desde el canon o mediante índice derivado— para el candidato que la tenga. Son preguntas distintas y se responden en momentos distintos.

### 3.5 Lo que las cuatro comparten y no diferencia a ninguna

**[N]** Sin cambios respecto de la v0.2 §3.2. Son **puertas previas comunes**: ninguna realización puede presentarlas como ventaja y ninguna puede omitirlas.

1. **Aislamiento de ámbito** aplicado como puerta antes de candidatos — RF-06, RF-09.
2. **Expansión escalonada sin salto a recuperación amplia** — RF-14, RF-15, RF-16.
3. **Validación de sujeto, polaridad, condición y tiempo** en la etapa de significado y relaciones — RF-17, RF-19.
4. **Borrado y regeneración completos** de todo índice derivado, desde el canon — ADR-001 c.2 y c.3.
5. **Petición completa y operación activa** — RF-01, RF-30.
6. **Plan reproducible y explicación por resultado** — RF-22, RF-28, RF-29.

**[H]** Las tres primeras son exactamente los tres hallazgos clasificados como inseguros en la línea base. La elección técnica **no las resuelve**: las presupone.

**[N]** La obligación 3 se aplica a `ADR002-A` con el mismo rigor que a `ADR002-D`. Que sus señales sean léxicas y estructuradas no le exime de validar sujeto, polaridad, condición y tiempo.

---

## 4. Puertas de decisión

**[N]** **Sin cambios respecto de la v0.2.** Una realización queda descartada si incumple cualquiera de estas puertas.

| # | Puerta | Traza canónica |
|---|---|---|
| 1 | Recall crítico insuficiente | RF-23, RF-25 |
| 2 | Contaminación por contenido no pertinente, prohibido, eliminado, restringido o fuera de ámbito | RF-10, RF-11, RF-12, RF-06 |
| 3 | Ausencia de explicación reproducible del resultado | RF-22, RF-28, RF-29 |
| 4 | Inestabilidad material de orden o selección bajo entradas equivalentes | RF-22, RED-033 |
| 5 | Imposibilidad de borrar o reconstruir completamente sus índices y derivados | ADR-001 c.2, c.3 |
| 6 | Acoplamiento a un proveedor concreto | RF-31 |
| 7 | Coste, latencia o complejidad incompatibles con el Registro de Tolerancias | Registro v0.4, §5.1 |
| 8 | Incumplimiento de aislamiento multi-proyecto, tiempo válido, corte de conocimiento, negación o conflicto | RF-06, RF-07, RF-08, RF-19, RF-21 |
| **9** | **Salto a recuperación amplia**: resolver en una etapa lo que exige escalonamiento, aunque el resultado final sea correcto | **RF-14** |

**[N]** La puerta 9 es la única que puede descartar una realización **con resultados perfectos**. Procede directamente del texto canónico de RF-14.

**[N]** La puerta 9 se aplica también al **orden de etapas tardías de `ADR002-D`**: resolver en una sola etapa lo que la alternativa declaró como dos etapas distintas es salto, aunque el conjunto final sea correcto.

**[N]** La continuidad con FTS5 es un **valor favorable, nunca una excepción a las puertas**. Se conserva literalmente de la v0.1 y de la v0.2.

**[?]** Solo la puerta 7 depende de cifras del Registro de Tolerancias. Las puertas 2, 5, 6, 8 y 9 son evaluables ya en forma booleana; las puertas 1, 3 y 4 lo son parcialmente. Es decir: **ADR-002 puede descartar realizaciones antes de que las cifras estén congeladas, pero no puede elegir una.**

---

## 5. Evidencia requerida

**[N]** Sin cambios respecto de la v0.2, salvo la etiqueta de candidato:

- Benchmark versionado por familias y casos, **respetando B04-CA-01–50 y el PDP como canónicos** y distinguiendo los tres niveles de caso.
- Línea base FTS5 reproducible y congelada — **[H]** ya medida y documentada.
- Ablaciones por señal y por etapa, incluida la que aísla la **validación de polaridad** frente a la señal cruda.
- Pruebas positivas, negativas y adversariales de negación, tiempo válido, corte de registro, ámbito, soporte plural, conflicto y ausencia.
- Pruebas de deduplicación prudente con equivalencia material, y de cardinalidad declarada.
- Pruebas de fuente inaccesible y degradación parcial reproducible.
- **Conformidad de etapa**: que cada resolución ocurra en la etapa esperada y que la transición obedezca a insuficiencia contrastada.
- **[N]** Para `ADR002-D`, además: que el **orden declarado** de sus etapas tardías se respete en cada ejecución y que no exista coordinación simultánea fuera de la etapa autorizada.
- Borrado transaccional y regeneración **desde el canon** de cada índice o derivado.
- Medición de latencia, coste, tamaño y estabilidad conforme al Registro de Tolerancias y al protocolo común de `ADR002-TOL-209`.
- Trazas minimizadas que permitan explicar por qué entró, salió u ocupó una posición cada resultado.

**[?]** **[H]** El corpus ejecutable existe en estado `v0.1 PROPUESTO` y **no está congelado**. La auditoría adversarial independiente dejó abiertos varios defectos de fidelidad canónica que deben corregirse antes de que `ADR002-TOL-208` pueda plantearse. Este documento **no los corrige y no los da por resueltos**.

---

## 6. Línea base heredada

**[N]** Sin cambios respecto de la v0.2.

Sirius 0.1 aporta una base real que **debe medirse, no presumirse**: FTS5, `KnowledgeSearchRepository`, `RankRelevantKnowledgeUseCase`, ranking de dominio puro, filtros y búsquedas locales existentes.

**[H]** Ya está medida. Aporta siete capacidades que conviene preservar —sincronización transaccional, regenerabilidad, saneado robusto, normalización de diacríticos, orden determinista y explicable, neutralidad tecnológica real y exclusión efectiva de lo eliminado— y contradice B04 en tres puntos: RF-06, RF-14 y RF-19.

**[N]** La línea base se conserva **congelada** como control comparativo, identificada por el head de Alembic `61be4bb269bf`. **No se modifica para favorecer a ninguna realización técnica.**

**[N]** Que `ADR002-A` comparta con `T0` la ausencia de señal semántica vectorial **no le hereda ninguno de sus tres incumplimientos**, ni le permite invocar ninguna de sus cifras. Cada candidato responde de su propia ficha.

---

## 7. Método de cierre

**[N]**

1. ~~Reconstruir el contrato exacto de B04, RED y PDP aplicable.~~ **Hecho**: inventario normativo v0.2, 32/32 RF exactos y mapeo RED canónico; fuentes canónicas materializadas y verificadas (`SRC-ADR002-01`).
2. ~~Ejecutar la línea base FTS5.~~ **Hecho en su parte de caracterización**; pendiente ejecutarla contra los casos canónicos.
3. ~~Fijar el Registro de Tolerancias y obtener aprobación explícita.~~ **Hecho**: Registro v0.4 aprobado el 26 de julio de 2026, con protocolo de medición y plantilla de ficha.
4. ~~Resolver el universo oficial de candidatos.~~ **Hecho**: Resolución de la partición de candidatos v1.0 APROBADA. **[N]** Paso nuevo en la v0.3; era condición previa de `ADR002-TOL-210`.
5. **Corregir y congelar corpus, referencias y métricas antes de observar resultados**, y **rederivar `T0` sobre el corpus congelado** (`ADR002-TOL-208`). **[N]** Bloqueante y **no realizado**.
6. **Congelar los valores de entorno del protocolo común** (`ADR002-TOL-209`) y **aprobar el presupuesto absoluto de almacenamiento** (`ADR002-TOL-207`). **[N]** No realizado.
7. **Emitir la ficha congelada de cada candidato y del control** (`ADR002-TOL-210`), conforme a la plantilla v0.2. **[N]** No realizado.
8. Implementar solo los prototipos mínimos necesarios para falsar `ADR002-A`, `ADR002-B`, `ADR002-C` y `ADR002-D`.
9. Ejecutar benchmark y ablaciones.
10. Abrir `EJE-1` o `EJE-2` **solo si** la evidencia lo exige, con un máximo de dos fichas adicionales.
11. Realizar una auditoría adversarial completa.
12. Corregir únicamente hallazgos demostrables.
13. Emitir ADR-002 final con una recomendación principal y sus consecuencias.
14. Obtener aprobación explícita del usuario.

**[N]** Los pasos 5, 6 y 7 son **bloqueantes** para el 8 en adelante: las cinco puertas de arranque no admiten margen, excepción por candidato ni cumplimiento parcial.

---

## 8. Decisiones que este documento no toma

**[N]** No decide todavía:

- **cuál de las cuatro alternativas mínimas es la recomendable**;
- embeddings definitivos ni modelo de embedding;
- `sqlite-vec` u otra extensión;
- RRF u otra fórmula de fusión;
- grafo, RDF o motor relacional especializado;
- si el sustrato léxico sigue siendo FTS5 o se sustituye (`EJE-1`);
- si las relaciones se resuelven desde el canon o mediante índice derivado (`EJE-2`);
- cifras de latencia, coste, tamaño o estabilidad;
- estructura final de tablas, carpetas o módulos;
- implementación productiva.

**[N]** Y **no hace**:

- no reabre la alternativa B de B04, `D01–D16`, `RF-01–32`, `CA-01–50`, `M01–21`, `E0–E5`, `G1–G12` ni `S1–S7`;
- **no aprueba `ADR002-TOL-207`**;
- **no declara satisfechas `ADR002-TOL-208`, `ADR002-TOL-209` ni `ADR002-TOL-210`**;
- **no corrige el corpus** ni ninguno de los defectos que la auditoría dejó abiertos;
- **no ejecuta `T0`** ni ningún candidato;
- no modifica `experiments/`, `artifacts/`, `docs/architecture/canonical_sources/`, `src/`, `tests/`, `migrations/` ni configuración productiva.

---

## 9. Estado de las puertas de arranque

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` · fuentes canónicas completas | **SATISFECHA** |
| `ADR002-TOL-207` · presupuesto absoluto de almacenamiento | **NO SATISFECHA** |
| `ADR002-TOL-208` · corpus congelado y T0 rederivada | **NO SATISFECHA** |
| `ADR002-TOL-209` · protocolo común de medición | **NO SATISFECHA** |
| `ADR002-TOL-210` · ficha de candidato | **NO SATISFECHA** |

**El benchmark sigue bloqueado.** La Resolución v1.0 retira una condición previa a `TOL-210` —ya se sabe cuántos candidatos hay y cómo se identifican— pero **no satisface ninguna puerta**.

---

## 10. Siguiente movimiento único

**Corregir los defectos de fidelidad canónica del corpus que la auditoría adversarial independiente dejó abiertos**, antes de que `ADR002-TOL-208` pueda plantearse.

No se emite ninguna ficha de candidato, no se ejecuta `T0`, no se implementa ningún prototipo, no se aprueba `TOL-207` y no se abre ningún eje contingente.
