# SIRIUS 0.2 — ADR-002 · Resolución de la partición de candidatos

**Versión:** 1.0
**Estado:** **APROBADA · CANÓNICA PARA ADR-002**
**Fecha:** 26 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Autoridad:** aprobación explícita del usuario en el Proyecto Sirius
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_03A_RESOLUCION_PARTICION_CANDIDATOS_v0.1.md`
**Fuente canónica que restituye:** `SIRIUS_0.2_ARQ_00_MARCO_RECTOR_ARQUITECTURA_Y_MAPA_DECISIONES_v1.0_APROBADO.docx` §23
**No autoriza:** corregir o congelar el corpus, aprobar `ADR002-TOL-207`, ejecutar T0, implementar o ejecutar candidatos, satisfacer `ADR002-TOL-208`, `ADR002-TOL-209` o `ADR002-TOL-210`, ni merge.

---

## 0. Objeto

Resolver, con autoridad canónica, cuál es el **universo oficial de candidatos** del benchmark de ADR-002.

La cuestión quedó abierta cuando `ADR-002 v0.2 ABIERTO` §3 sustituyó las alternativas mínimas de `ARQ-00 v1.0 APROBADO` §23 por una partición propia, `T1–T4`. La matriz canónica §6 y el informe de preparación del corpus §7 la registraron como cuestión abierta y expresamente **no la resolvieron**. Esta resolución la cierra.

Esta resolución **no reabre** ninguna decisión de producto: la alternativa B de B04, `B04-D01–D16`, `B04-RF-01–32`, `B04-CA-01–50`, `B04-M01–21`, la política `E0–E5`, las puertas `G1–G12` y las paradas `S1–S7` permanecen intactas y vigentes.

---

## 1. Reproducción literal de ARQ-00 v1.0 APROBADO §23

Se transcribe **sin alterar una palabra**, incluida la palabra **vectorial** en la alternativa B, desde `docs/architecture/canonical_sources/SIRIUS_0.2_ARQ_00_MARCO_RECTOR_ARQUITECTURA_Y_MAPA_DECISIONES_v1.0_APROBADO.docx` (SHA-256 `730a5fd13dce18bfcdb8dd4afee23dfe22c067c7cb3b953a9bd115cf73224f49`, verificada contra el `MANIFEST.md`).

> **23. ADR-002 — Recuperación, ranking e índices**
>
> **PREGUNTA** ¿Qué arquitectura de recuperación supera B04/PDP con explicabilidad, privacidad, aislamiento y coste controlado sin acoplarse a un proveedor?
>
> **Alternativas mínimas**
>
> **A:** expansión escalonada solo léxica/estructurada en todas las etapas E0–E5.
> **B:** expansión escalonada léxica/estructurada con señal semántica **vectorial** únicamente en etapas tardías tras fallar la puerta de suficiencia.
> **C:** expansión escalonada léxica/estructurada con señal relacional explícita únicamente en etapas tardías tras fallar la puerta de suficiencia.
> **D:** expansión escalonada con señales semántica y relacional en etapas tardías distintas y orden predefinido; nunca coordinación simultánea fuera de la etapa autorizada.
>
> **Criterios y puertas**
> La política E0–E5, sus puertas G1–G12 y la expansión escalonada provienen de B04 y no son objeto del ADR.
> Recall crítico y contaminación como puertas.
> Explicabilidad y estabilidad.
> Coste, latencia y mantenibilidad.
> Portabilidad y borrado de índices.
>
> **Evidencia requerida**
> Benchmark por familias y casos.
> Ablaciones por señal.
> Pruebas de negación, tiempo, ámbito y conflicto.
> Borrado transaccional de cada índice.
>
> **Dependencias:** Contratos aprobados de ADR-001.
>
> **No puede decidir todavía:** La política escalonada aprobada, sus etapas o puertas; embeddings definitivos, sqlite-vec, RRF, grafo/RDF y modelo de embedding **hasta que la evidencia los justifique**.

Dos precisiones de lectura, ambas literales del propio ARQ-00:

- El encabezado es **«Alternativas mínimas»**: es el **conjunto mínimo de contraste** que ADR-002 debe falsar, no una lista de ejemplos ni un catálogo cerrado de productos. Reducirlo es rebajar el marco; ampliarlo con ejes adicionales es legítimo.
- ARQ-00 §1 sitúa dentro de su alcance los **«criterios para decidir y falsar alternativas»** y fuera de él el **«resultado de ADR-002 … y selección definitiva de tecnologías»**. Fijar el conjunto mínimo de contraste es competencia de ARQ-00; decidir cuál gana es competencia del benchmark.

---

## 2. Decisión aprobada

> ### La partición oficial y obligatoria del benchmark principal de ADR-002 es la de ARQ-00 §23, con identificadores propios de ADR-002.

| ID | Nombre | Definición operativa |
|---|---|---|
| **`ADR002-A`** | **Léxica/estructurada** | Expansión escalonada mediante señales **léxicas y estructuradas** en todas las etapas `E0–E5`. La etapa `E3` se ejecuta y se satisface por medios léxico-estructurados. |
| **`ADR002-B`** | **Semántica vectorial tardía** | Base léxica/estructurada y **señal semántica vectorial** únicamente en etapas tardías, tras fallar la puerta de suficiencia. |
| **`ADR002-C`** | **Relacional explícita tardía** | Base léxica/estructurada y **señal relacional explícita** únicamente en etapas tardías, tras fallar la puerta de suficiencia. |
| **`ADR002-D`** | **Semántica y relacional separadas** | Ambas señales en **etapas tardías distintas**, con **orden predefinido** y **sin coordinación simultánea fuera de la etapa autorizada**. |

### 2.1 Las cuatro son candidatos completos

**Ninguna de las cuatro queda degradada de antemano a control, ni excluida como recomendación posible, ni tratada como hipótesis ya falsada.**

En particular, y de forma expresa:

- **`ADR002-A` es un candidato completo y puede resultar recomendable.** No es un control. No es la línea base de Sirius 0.1. Si supera todas las puertas y aporta valor material, la recomendación principal de ADR-002 puede ser `ADR002-A`.
- **`ADR002-C` es un candidato completo y puede resultar recomendable.** No es un control ni una variante subordinada de `ADR002-D`.

Las cuatro entran en la comparación con el mismo estatuto, se juzgan con las mismas puertas y se miden con el mismo protocolo. **La evidencia decidirá cuál supera las puertas y cuál aporta mejora material**; ninguna decisión documental puede anticiparlo.

### 2.2 Regla de no degradación

Ningún documento posterior de ADR-002 puede:

1. retirar una de las cuatro alternativas mínimas del universo de candidatos;
2. reclasificarla como «control», «hipótesis de falsación» o «reserva técnica» sin una decisión canónica explícita del usuario;
3. declarar de antemano que no puede ser recomendada.

Retirar una alternativa mínima exige **corrección canónica de ARQ-00**, no una nota de un documento derivado.

---

## 3. T0 — línea base de Sirius 0.1, y nada más

**`T0` es únicamente la línea base congelada de Sirius 0.1**, identificada por el head de Alembic `61be4bb269bf`. Es **control de falsación**, no una quinta alternativa de arquitectura y **no candidata**.

`T0` **no es `ADR002-A`**, y confundirlos es un error material:

| | `T0` | `ADR002-A` |
|---|---|---|
| Qué es | Sirius 0.1 tal como está | Realización correcta del contrato B04 con señales léxicas y estructuradas |
| `E0–E5` | No las implementa | Las implementa íntegras |
| `G1–G12` | No las implementa como puertas | Las implementa como puertas no compensables |
| `S1–S7` | No existen | Existen y se adjudican |
| Estado frente a B04 | **Incumple RF-06, RF-14 y RF-19** (medido; los tres `INSEGURO` del inventario) | Debe cumplirlos como cualquier otro candidato |

La función de `T0` es doble y solo esa: dar **suelo de comparación** y **falsar** la hipótesis de que una señal tardía es necesaria. Su ficha existe marcada como control de falsación.

---

## 4. Interpretación correcta de B04-RF-17

Esta resolución corrige una lectura que sostuvo la sustitución de `T1–T4`. Se apoya en el texto literal de `B04 v1.0 APROBADO` (SHA-256 `b28a2cbed62b90f35e28db2412e46939b9bd2cdb8f145a5e9bbb2a8e7a5cbb45`).

**Texto canónico:**

> **B04-RF-17** — Expandir a significado y relaciones con validación explícita de sujeto, polaridad, condición y tiempo.
>
> **B04-RF-31** — Mantener neutralidad tecnológica: ninguna obligación exige embeddings, RAG, FTS, vectores, grafos o un modelo concreto.
>
> **B04 §15.1, etapa E3 · Semántica y relacional** — Buscar paráfrasis, dependencias, apoyo/refutación y relaciones; validar negación, condición, sujeto y tiempo. → Mejora recall sin convertir similitud en identidad.
>
> **B04 §8, problema que el bloque debe impedir** — Atar el contrato a embeddings, RAG, FTS, grafos, un modelo o una base concreta.

**Conclusión normativa:**

1. **La etapa `E3` es obligatoria** para todo candidato, con validación explícita de sujeto, polaridad, condición y tiempo. Esto no admite excepción.
2. **`RF-17` es una obligación de comportamiento, no de realización.** No exige embeddings, ni vectores, ni un índice semántico dedicado. `RF-31` y B04 §8 prohíben expresamente convertirla en tal.
3. Por tanto, **una señal semántica vectorial no es obligatoria para todos los candidatos**. Es el eje que `ARQ-00` §23 pone a prueba.
4. `ADR002-A` y `ADR002-C` siguen siendo **hipótesis legítimas** hasta que el benchmark las falsifique o las sostenga. Si fallan, fallarán por `B04-M02`, `B04-M17`, `B04-M18` o cualquier otra puerta **medida**, nunca por definición documental.
5. ARQ-00 v1.0 se aprobó el **25 de julio de 2026**, dos días **después** de B04 v1.0 (23 de julio de 2026), y enuncia `A` con `RF-17` ya canónico. No existe la incompatibilidad que se alegó: existe una hipótesis que se retiró sin autoridad.
6. El propio §23 prohíbe decidir «embeddings definitivos, sqlite-vec, RRF, grafo/RDF y modelo de embedding **hasta que la evidencia los justifique**». Hacer obligatoria la señal vectorial en las cuatro realizaciones **decide embeddings por construcción**, que es exactamente lo prohibido.

---

## 5. Por qué T1–T4 no era una refinación legítima

`ADR-002 v0.2 ABIERTO` §3 particiona por *sustrato léxico* (FTS5 o alternativo) × *relaciones* (desde el canon o índice derivado), con señal semántica tardía **común a las cuatro**, y su §0 declara que «la variante solo léxica **deja de ser candidata**».

La auditoría adversarial independiente demostró que esto es **sustitución parcial no autorizada**, no refinación del mismo eje:

| Eje | ARQ-00 §23 | ADR-002 v0.2 §3 | Efecto |
|---|---|---|---|
| **Señal tardía habilitada** (ninguna / semántica / relacional / ambas) | Variable a falsar; es el eje mínimo | **Fijada**: semántica común a las cuatro | **Sustitución.** Elimina `A` y `C` del universo |
| **Orden y separación de etapas tardías** | Restricción explícita de `D` | No expresada | **Pérdida.** Desaparece la salvaguarda de `B04-D15` |
| **Sustrato léxico** (FTS5 / alternativo) | No contemplado | Eje principal | **Adición legítima**, pero no puede ocupar el lugar del eje mínimo |
| **Materialización de relaciones** (canon / índice derivado) | No contemplado | Eje principal | **Adición legítima**, misma consideración |

`T1–T4` aporta valor real en dos ejes que ARQ-00 no cubría. Su defecto es haber **ocupado el lugar** del eje mínimo en vez de añadirse a él, y haber justificado esa ocupación en una lectura de `RF-17` que `RF-31` contradice.

**Se registra sin eufemismo: fue sustitución parcial no autorizada.** No se presenta como refinación legítima del mismo eje.

---

## 6. Tratamiento de T1–T4

`T1–T4` queda **SUPERADA como universo principal de candidatos**.

**No se borra, no se reescribe retrospectivamente y no se declara errónea en su totalidad.** `ADR-002 v0.2 ABIERTO` se conserva íntegro y sin modificar como historial. Lo que se conserva con valor prospectivo son sus **dos ejes técnicos**, reclasificados como **contingentes**:

| Eje contingente | Contenido | Origen |
|---|---|---|
| **EJE-1 · Sustrato léxico** | FTS5 medido **frente a** sustrato léxico alternativo | `T1/T2` frente a `T3/T4` |
| **EJE-2 · Materialización de relaciones** | Resueltas **desde el canon** frente a **índice relacional derivado** | `T1/T3` frente a `T2/T4` |

### 6.1 Regla de contención — obligatoria

Para impedir la explosión combinatoria `4 alternativas × 2 sustratos × 2 materializaciones = 16`:

1. **Primera ronda, y única autorizada a planificarse hoy:** `T0` (control) **+** `ADR002-A`, `ADR002-B`, `ADR002-C`, `ADR002-D`, **todos sobre el mismo sustrato léxico FTS5 medido y la misma infraestructura común**. Cinco fichas: cuatro candidatos y un control.
2. **`EJE-1` y `EJE-2` solo pueden abrirse después de la comparación primaria `A/B/C/D`**, y únicamente cuando la evidencia demuestre que **pueden cambiar materialmente la decisión** —es decir, cuando una puerta o un fallo sea atribuible a ese eje concreto.
3. **Máximo dos fichas adicionales** por apertura contingente, cada una con su justificación de puerta o fallo atribuido. No se ejecuta en ningún caso el producto cartesiano.
4. **Las ablaciones técnicas de nivel 3** miden la aportación marginal de cada señal y de cada etapa **sin multiplicar candidatos**. `AB-3` aísla la aportación de la señal tardía y `AB-4` separa la señal cruda de la validación de polaridad que `RF-17` exige: son el instrumento previsto para esa información marginal.
5. La apertura de un eje contingente **no reabre** esta resolución ni retira ninguna de las cuatro alternativas mínimas.

### 6.2 Efecto sobre el presupuesto

La primera ronda mantiene **cinco fichas** —las mismas cinco que la partición anterior planificaba (`T0` + cuatro realizaciones)—, de modo que **el reparto agregado de `ADR002-TOL-207` no se altera por esta resolución**. Esta resolución **no aprueba, no modifica y no valida** ninguna cifra de `TOL-207`.

---

## 7. La restricción de ADR002-D se preserva íntegra

`ADR002-D` no es «`B` más `C`». Su definición canónica lleva **tres restricciones acumulativas**, y las tres son obligatorias:

1. las señales semántica y relacional actúan en **etapas tardías distintas**;
2. con **orden predefinido**, declarado y congelado **antes** de ejecutar;
3. **nunca coordinación simultánea fuera de la etapa autorizada**.

Esta restricción no es decorativa. Es lo que impide que la política aprobada —alternativa B de B04, expansión escalonada— derive de hecho hacia la alternativa C de B04, «recuperación coordinada», que B04 §14.1 clasificó como **«RESERVA TÉCNICA, NO POLÍTICA PRINCIPAL»**. Su anclaje canónico es directo:

> **B04-D15** — La coordinación solo combina señales del mismo espacio y familia de la etapa activa; **no adelanta espacios posteriores ni sustituye la política escalonada**. (APROBADA)

Un candidato `ADR002-D` que coordine ambas señales simultáneamente, o que no declare el orden de sus etapas tardías antes de ejecutar, **no es `ADR002-D`**: incumple `B04-D15` y la puerta 9 de ADR-002. La ficha de candidato v0.2 recoge esta declaración como campo obligatorio.

---

## 8. Lo que esta resolución no hace

- **No ejecuta `T0`**, ni ningún candidato, ni ninguna medición.
- **No implementa** ningún prototipo.
- **No corrige el corpus.** Los defectos de fidelidad canónica detectados por la auditoría adversarial independiente —traza `RED↔CA↔M` frente al Anexo B del PDP, alcance de la etiqueta `congelada_por` de las referencias, ausencia del modo `M4`, casos multirrama aplanados, ficha de caso frente al PDP §7, y la clasificación frente a `T0`— **siguen abiertos y sin corregir**. Esta resolución no los toca y no los cierra.
- **No aprueba ni modifica `ADR002-TOL-207`.**
- **No declara satisfechas `ADR002-TOL-208`, `ADR002-TOL-209` ni `ADR002-TOL-210`.**
- **No altera el contenido material** de ninguna tolerancia aprobada. La única corrección sobre el Registro v0.4 es la **etiqueta de arquitectura** exigida por `TOL-210`, y se materializa mediante nota de superación, no reescribiendo el documento aprobado.
- **No emite ninguna ficha de candidato.** `ADR002-TOL-210` sigue **NO SATISFECHA**.
- **No reabre** la alternativa B de B04, `D01–D16`, `RF-01–32`, `CA-01–50`, `M01–21`, `E0–E5`, `G1–G12` ni `S1–S7`.
- **No modifica** `experiments/`, `artifacts/`, `docs/architecture/canonical_sources/`, `src/`, `tests/`, `migrations/` ni configuración productiva.
- **No abre otro PR ni fusiona el PR #117.**

---

## 9. Estado de las puertas de arranque tras esta resolución

Sin cambios, salvo la eliminación de un bloqueo aguas arriba de `TOL-210`.

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` · fuentes canónicas completas | **SATISFECHA** (26 de julio de 2026) |
| `ADR002-TOL-207` · presupuesto absoluto de almacenamiento | **NO SATISFECHA** — propuesta pendiente; esta resolución no la aprueba |
| `ADR002-TOL-208` · corpus congelado y T0 rederivada | **NO SATISFECHA** — el corpus es `v0.1 PROPUESTO`, no congelado; `T0` no se ha ejecutado; hay defectos de auditoría abiertos |
| `ADR002-TOL-209` · protocolo común de medición | **NO SATISFECHA** — faltan por congelar los valores del entorno |
| `ADR002-TOL-210` · ficha de candidato | **NO SATISFECHA** — la plantilla v0.2 existe y el universo de candidatos ya está resuelto, pero **no hay ninguna ficha emitida** |

**El benchmark sigue bloqueado.** Esta resolución retira **una condición previa** a `TOL-210` —no se sabía cuántos candidatos había ni cómo se identificaban—, y **no satisface la puerta**.

---

## 10. Validación de esta resolución

| Comprobación exigida por el paquete 03A §7 | Resultado |
|---|---|
| Coherente con ARQ-00 §23 | **Sí** — §1 lo reproduce literalmente desde el `.docx` canónico |
| Palabra **vectorial** presente en `ADR002-B` | **Sí** — §1 y §2 |
| Coherente con `B04-RF-17`, `B04-RF-31` y la neutralidad tecnológica | **Sí** — §4, con texto canónico citado |
| `A/B/C/D` presentes como **cuatro candidatos completos** | **Sí** — §2 y §2.1, con regla de no degradación en §2.2 |
| `T0` separado como control | **Sí** — §3, con tabla de diferencias frente a `ADR002-A` |
| `T1–T4` conservados **solo** como ejes contingentes | **Sí** — §6, con regla de contención en §6.1 |
| Restricción de `ADR002-D` preservada | **Sí** — §7, con las tres restricciones y su anclaje en `B04-D15` |
| No se declara obligatoria la señal vectorial para todos | **Sí** — §4 punto 3 |
| `A` y `C` no convertidas en controles | **Sí** — §2.1, expresamente |
| `T1–T4` no presentada como refinación legítima | **Sí** — §5, calificada como sustitución parcial no autorizada |
| No se resuelven ni se mencionan como aprobadas `TOL-207`, `TOL-208`, `TOL-209` | **Sí** — §8 y §9 |
| No se corrige silenciosamente ninguna versión anterior | **Sí** — la corrección va por nota de superación 02 |

---

**Siguiente movimiento único:** con el universo de candidatos resuelto, el trabajo autorizado es **corregir los defectos del corpus que la auditoría adversarial dejó abiertos** antes de poder congelarlo (`ADR002-TOL-208`). No se emite ninguna ficha de candidato, no se ejecuta `T0`, no se aprueba `TOL-207` y no se implementa ningún prototipo.
