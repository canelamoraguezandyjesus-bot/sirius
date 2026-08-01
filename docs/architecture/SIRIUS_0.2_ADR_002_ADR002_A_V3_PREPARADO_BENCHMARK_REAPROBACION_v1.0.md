# SIRIUS 0.2 — ADR-002 · Reaprobación de `ADR002-A` v3 como PREPARADO PARA BENCHMARK

**Versión:** 1.0
**Estado:** **APROBADO · `ADR002-A` v3 PREPARADO PARA BENCHMARK**
**Fecha:** 1 de agosto de 2026
**Rama:** `evidence/adr001-spikes`
**Autoridad:** Usuario / Proyecto Sirius
**Commit auditado:** `f45595337e455232a17878afe516d1eb9d78dd2b`
**Autorización explícita del usuario:** «Aprobar»

## 0. Objeto y alcance

Esta acta materializa la decisión explícita del usuario, expresada
literalmente como **«Aprobar»** ante la recomendación explícita de
reaprobación de `ADR002-A` v3, y registra el estado:

> **`ADR002-A` v3: PREPARADO PARA BENCHMARK**

La autorización se refiere **únicamente a `ADR002-A` v3**. **No aprueba
`ADR002-B` v2**, que permanece **PENDIENTE DE APROBACIÓN** (§5).

La reaprobación acepta, según el alcance declarado:

1. la extensión neutral del puerto común mediante la operación
   `por_identificadores`;
2. la ficha vigente `ADR002-A` v3;
3. que el código propio de `ADR002-A` permanece **idéntico byte a byte** al
   cubierto por la versión anteriormente aprobada;
4. que `ADR002-A` **no utiliza** la nueva operación por identidad;
5. que sus límites permanecen **válidos tras revisión**;
6. que **todas sus pruebas funcionales fueron repetidas** después de congelar
   la ficha v3;
7. que la aprobación histórica de `ADR002-A` v2 permanece como historial, y
   que **la presente decisión es la que aplica a la versión vigente v3**.

**Esta reaprobación NO autoriza ejecutar el benchmark, usar el corpus
oficial ni medir el candidato.**

## 1. Qué significa exactamente PREPARADO PARA BENCHMARK

El borde del estado queda escrito aquí, igual que en el acta histórica, para
que nadie lo ensanche después.

### 1.1 Significa, y solo esto

| # | Significado |
|---|---|
| 1 | **Implementación vigente identificada**: `ADR002-A` existe como candidato ejecutable sobre la infraestructura común, con identidad fijada por SHA, blob y árbol (§2). |
| 2 | **Ficha v3 congelada**: `ficha_ADR002-A_v3.json`, en estado `CONGELADA`, con su huella recomputable y sin ningún resultado observado del candidato. |
| 3 | **Custodia válida**: anterioridad estricta de la ficha frente a las pruebas repetidas, unicidad de ficha `CONGELADA`, identidades que resuelven o constan inventariadas, evidencia previa no reescrita. |
| 4 | **Regresión funcional superada**: las suites funcionales completas de `ADR002-A` fueron repetidas bajo la ficha v3 y pasaron. |
| 5 | **Aptitud para recibir una futura autorización conjunta de ejecución**: el material de gobierno está completo para que esa autorización pueda decidirse. |

### 1.2 No significa, en ningún grado

| # | Lo que **no** se afirma |
|---|---|
| 1 | **Benchmark ejecutado.** No se ha ejecutado. |
| 2 | **Rendimiento validado.** No existe ni una sola cifra de rendimiento de `ADR002-A`. |
| 3 | **Candidato ganador.** No hay comparación alguna. |
| 4 | **Arquitectura final aprobada.** No lo es. |
| 5 | **Autorización productiva.** Ninguna. |
| 6 | **Autorización de ejecución aislada de `ADR002-A`.** La eventual autorización de ejecución sería un acto de gobierno futuro y conjunto, no una consecuencia de esta acta. |

**La ejecución sigue bloqueada.** Autorizar una ejecución sobre el corpus
oficial es un acto de gobierno distinto, posterior e independiente de esta
acta.

## 2. Identidad vinculante: SHA, blobs y árboles

La identidad se fija sobre el commit auditado
`f45595337e455232a17878afe516d1eb9d78dd2b`. La cadena de la corrección 02 es
**lineal** y cada commit citado es **ancestro estricto** del siguiente.

### 2.1 Cadena de la corrección 02

| Commit | Contenido |
|---|---|
| `13ffae552b76089fee7119264a2502d166ef97dd` | paquete de corrección 02 · acta de preinscripción |
| `9ccec61f0f005987aabedfce265d7654ff1588dc` | extensión neutral del puerto común · operación `por_identificadores` · corrección estática de `ADR002-B` · preparación de las fichas sucesoras |
| `51804f0caac5b0fee83789f0d3eb49cca2a3fe7c` | entrada de las fichas `ADR002-A` v3 y `ADR002-B` v2 · `ADR002-A` v2 y `ADR002-B` v1 marcadas `SUSTITUIDA` |
| `f45595337e455232a17878afe516d1eb9d78dd2b` | pruebas posteriores a las fichas · regresión completa de `ADR002-A` · pruebas de materialización por identidad |

La cadena de preparación y corrección original de `ADR002-A` (v1 y v2) quedó
fijada en el acta histórica y no se repite aquí: esta acta la **referencia por
identidad** en §2.4.

### 2.2 Ficha vigente de `ADR002-A`

| Campo | Valor |
|---|---|
| Ruta | `artifacts/adr002_cards/ficha_ADR002-A_v3.json` |
| Blob | `b3ce920e6dc0ee62a0358f8bfb9762dcac0d64d7` |
| Huella canónica | `427905a06f6c12666a09c73b8720e229f17eeef3` |
| Versión | `3` |
| Estado | `CONGELADA` |
| Sustituye a | `2` |
| Commit de referencia declarado | `13ffae552b76089fee7119264a2502d166ef97dd` |
| Commit de entrada observado en Git | `51804f0caac5b0fee83789f0d3eb49cca2a3fe7c` |

### 2.3 Fichas históricas de `ADR002-A`

| Campo | v2 | v1 |
|---|---|---|
| Ruta | `artifacts/adr002_cards/ficha_ADR002-A_v2.json` | `artifacts/adr002_cards/ficha_ADR002-A_v1.json` |
| Estado actual | `SUSTITUIDA` | `SUSTITUIDA` |
| Blob actual | `d8cdd35784437da1860dc4130c7d605ade695ab6` | `4dcb53873de5ca58cf3e929e861511219430b6be` |
| Huella actual | `95be1370e8279eea76fd92ade2db0545e5a417dc` | `8d8c21b6afd1d32ee612dd14199ab9c5605bfb96` |
| Contenido mientras estuvo `CONGELADA` | blob `c0169c26ead4e9237d4e81e8f5e75b412f505296` · huella `4ed820fab545dd9154ce078349c214f870baecd1` | blob `1a96f535250bce643e8ccf2edb0362b3ec9320fe` · huella `00571890294bcd18748e2ee600eb43bad1b92f80` |

Ninguna de las dos se borra ni se reescribe: el diff de cada una respecto de
su contenido congelado son exactamente el campo `estado` y la huella que se
recomputa de él, porque el estado forma parte de la forma canónica. Sus
contenidos normativos íntegros permanecen en el historial de Git.

### 2.4 Acta histórica de preparación de la v2

| Campo | Valor |
|---|---|
| Ruta | `docs/architecture/SIRIUS_0.2_ADR_002_ADR002_A_PREPARADO_BENCHMARK_APROBACION_v1.0.md` |
| Blob en el commit auditado | `a12932774c2cd987148e8c57bb6370c04294bd0e` |
| Estado | **INTACTA** — ni una línea modificada por esta acta ni por la corrección 02 |

### 2.5 Código ejecutable cubierto por la ficha v3

| Subárbol | Hash | Nota |
|---|---|---|
| `experiments/adr002/candidates/common` | `a83539e3c8b5396371b355619a29478cad054834` | infraestructura común vigente, extendida **solo** por la corrección 02 |
| `experiments/adr002/candidates/adr002_a` | `2d90b551445db340458278a5accad55372995b76` | código propio de `ADR002-A`, **idéntico byte a byte** desde el prototipo corregido de la corrección 01 |

El árbol propio de `ADR002-A` es el mismo que cubría la versión anteriormente
aprobada: `2d90b551445db340458278a5accad55372995b76` tanto en el commit
auditado histórico `e40eff416d4a7965217580635980ac897716306d` como en el
vigente. El diff de la capa común entre ambos commits auditados afecta
exclusivamente a `contracts.py` y `port.py`, los dos ficheros de la extensión
neutral.

### 2.6 Blobs de los artefactos vinculados

**Documentación de gobierno de la corrección 02**

| Artefacto | Blob Git |
|---|---|
| `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_CORRECCION_02_MATERIALIZACION_POR_IDENTIDAD_v0.1.md` | `d0c5eb4bf4ee753e40da13962a817eaa967dff65` |

**Extensión neutral de la infraestructura común**

| Artefacto | Blob Git |
|---|---|
| `experiments/adr002/candidates/common/contracts.py` | `a13946b923b1ee6adf77ab46ed2fda4fb89ef64f` |
| `experiments/adr002/candidates/common/port.py` | `72041ab76d28de53d161e98172ea20c0ef1a0e2a` |

**Código propio de `ADR002-A` (sin cambios)**

| Artefacto | Blob Git |
|---|---|
| `experiments/adr002/candidates/adr002_a/candidate.py` | `9e8205b817ef23a03338e295d2f4b71fe4a307d4` |
| `experiments/adr002/candidates/adr002_a/lexical.py` | `549922cb61c4c8c9a067ca6bae2b6f485c107eb3` |

Los dos blobs del código propio son **los mismos** que registró el acta
histórica de la v2: la identidad del código de `ADR002-A` no ha cambiado.

**Prueba que observa la no-invocación de la operación nueva**

| Artefacto | Blob Git |
|---|---|
| `experiments/adr002/candidates/test_adr002_identidad_funcional.py` | `d1ac9cf319c447fc72b81190f1fcfd7168699088` |

Cualquier modificación posterior de los contenidos de esta §2 requiere
revisión explícita y un **acto sucesor**.

## 3. Criterios de reaprobación declarados demostrados

Los dieciséis criterios quedan declarados **demostrados** en el commit
auditado. Cada uno indica dónde se comprueba.

| # | Criterio | Demostración |
|---|---|---|
| 1 | `ADR002-A` sigue siendo un **candidato completo** y no un control | ficha v3 con `papel: CANDIDATO`, validada por la rama de candidato de `schema_card_v0_2`; el papel `CONTROL` sigue reservado a `T0-control` |
| 2 | Su **código propio no cambió** respecto de la versión anteriormente aprobada | árbol `adr002_a` `2d90b551…` idéntico entre `e40eff4` y `f455953`; blobs de `candidate.py` y `lexical.py` idénticos a los del acta histórica (§2.6) |
| 3 | La **infraestructura común cambió únicamente** para añadir una operación neutral | diff de `common` entre commits auditados: solo `contracts.py` y `port.py`; los métodos preexistentes del puerto conservan comportamiento y firma (aserción explícita en las suites estáticas) |
| 4 | `por_identificadores` está **disponible para todos los candidatos** y no favorece a `A` | vive en el puerto común, forma parte del protocolo público, no nombra candidato alguno; controles de neutralidad de la capa común: `[]` |
| 5 | `ADR002-A` **no llama** a `por_identificadores` | `test_a_no_invoca_la_materializacion_por_identidad`: ejecución completa real de `A` cuyo registro de consultas no contiene ninguna operación `por_identidad:*` |
| 6 | **`E0`–`E5`, `G1`–`G12` y las paradas realmente alcanzables** conservan su comportamiento | las dos suites funcionales de `A` repetidas enteras bajo la v3, con las mismas expectativas funcionales que validaron a la implementación cubierta por la v2 |
| 7 | `E3` **léxico-estructurada permanece dirigida y sin barrido** | pruebas repetidas de expansión desde semillas, prefijos concretos derivados, y no-conversión en barrido al ampliar el proyecto (mismas sentencias y filas observadas) |
| 8 | La **regeneración completa del derivado** permanece válida | pruebas repetidas de borrado objeto a objeto, reconstrucción de tablas, sombras y triggers, y resincronización FTS5 posterior |
| 9 | **Sujeto, ámbito, polaridad, condición y tiempo** siguen siendo validados | suite funcional de `A` repetida: puertas con caso discriminante, ámbito como filtro `G4`, polaridad conservada, condición y corte temporal |
| 10 | **Trazas, explicaciones, privacidad e indistinguibilidad** siguen comprobadas | suite funcional de `A` repetida: explicación por resultado, traza sin contenido protegido, bandas de privacidad, indistinguibilidad de ausencias |
| 11 | Los **resultados funcionales de `A` fueron repetidos bajo la ficha v3** | las suites quedaron suspendidas de forma declarada desde el commit `9ccec61f…` y se reactivaron al existir la v3; ninguna ejecución previa se reutilizó |
| 12 | La **ficha v3 es ancestro estricto de las pruebas** | entrada observada en `51804f0c…`, ancestro estricto de `f4559533…`; comprobado contra el grafo de Git por la guarda de cada suite |
| 13 | El **código propio de `A` cubierto por la ficha permanece estable** | árbol `2d90b551…` sin cambios después de congelar la v3 (y desde la corrección 01) |
| 14 | **No se usó el corpus oficial** | fixtures técnicos propios; control de fuente que prohíbe `performance_corpus_v0_2` y `conformance_corpus_v0_4` en los módulos auditables |
| 15 | **No se midió rendimiento** | controles de fuente que prohíben `perf_counter` y `time.time`; autocomprobación final de cada suite; ficha v3 con `no_contiene_resultados: true` |
| 16 | **No existen resultados de benchmark** | ningún artefacto de resultados existe en el repositorio; el verificador de fichas lo exige y pasa |

## 4. Relación con la aprobación histórica de la v2

1. El acta histórica (`SIRIUS_0.2_ADR_002_ADR002_A_PREPARADO_BENCHMARK_APROBACION_v1.0.md`,
   blob `a12932774c2cd987148e8c57bb6370c04294bd0e`) **permanece intacta**.
2. Se conserva como **decisión histórica aplicable a la versión v2**, sobre la
   identidad exacta que esa acta fijó (ficha v2 congelada, blob
   `c0169c26…`, huella `4ed820fab5…`).
3. **La presente acta es la que reaprueba la versión vigente v3.** Desde este
   momento, el estado `PREPARADO PARA BENCHMARK` de `ADR002-A` se predica de
   la v3 por esta acta, no de la v2 por la histórica.
4. Esta decisión **no es una modificación retroactiva** de la anterior: no la
   corrige, no la sustituye en su ámbito histórico y no reescribe nada de lo
   que aquella declaró.
5. La ficha v3 **no se modifica**: la propia ficha ya declaraba que la
   aprobación histórica de la v2 no se trasladaba automáticamente, y esta
   acta es precisamente el acto de gobierno nuevo que esa declaración exigía.

## 5. Estado de `ADR002-B`

> **`ADR002-B` v2: PENDIENTE DE APROBACIÓN**

Esta decisión **no acepta ni rechaza** a `ADR002-B`. Su ficha v2 permanece
`CONGELADA` (huella `c98ef457273055f1362d2939d48bba096f62cdc2`), su código, sus
pruebas y su documentación quedan exactamente como estaban. La eventual
aprobación de `ADR002-B` v2 como PREPARADO PARA BENCHMARK es un acto de
gobierno futuro e independiente.

## 6. Evidencia de verificación en el commit auditado

| Comprobación | Resultado |
|---|---|
| Verificador de fichas (`verify_cards --check`) | `RC=0` · 6 fichas conformes · **una sola `CONGELADA` por candidato** · 14/14 controles bloqueantes · puertas de arranque pendientes: ninguna |
| Unicidad de ficha `CONGELADA` para `ADR002-A` | **una sola**: la v3; la v2 y la v1 constan `SUSTITUIDA` |
| Recomputación de las seis huellas | coinciden con las declaradas |
| Verificador de custodia (`fallos_de_identidad`) | `[]` · ninguna cita de identidad rota |
| Neutralidad de la capa común | `[]` |
| Aislamiento de `ADR002-A` | `[]` |
| Aislamiento de `ADR002-B` | `[]` |
| Ruff format | conforme |
| Ruff lint | conforme |
| mypy | sin errores |
| repositorio (`tests/`) | `1 195 passed` |
| `experiments/` | `1 358 passed` |
| Quality (GitHub Actions) sobre `f455953` | **success** |

## 7. Por qué esta acta no toca ningún verificador

`ADR002-A` **no es una puerta**, y el repositorio no tiene —ni esta acta
inventa— un registro legible por máquina de preparación por candidato, ni un
registro nuevo, ni una puerta nueva, ni un campo nuevo en las fichas, ni una
autorización de ejecución. El mecanismo existente
`card_protocol.estado_de_las_puertas` deriva el estado de las **puertas de
arranque**, que esta acta no crea ni satisface; y
`card_protocol.ejecutabilidad` —que exige puertas satisfechas y ficha
`CONGELADA`— ya se cumplía para `ADR002-A` antes de esta acta. Igual que en la
aprobación histórica, el acta documental **es** el registro del estado
`PREPARADO PARA BENCHMARK`: registra el juicio de gobierno sobre un material
que la máquina ya validaba, sin cambiar lo que la máquina comprueba.

Se recuerda expresamente: `ejecutabilidad` significa «tiene ficha vigente y
las puertas están satisfechas», **no** «está autorizado a ejecutarse». La
autorización de ejecución es un acto de gobierno y hoy no existe.

## 8. Limitaciones conocidas que siguen vigentes

Las limitaciones registradas en el acta histórica de la v2 siguen vigentes
bajo la v3, porque la corrección 02 no las tocó y el código propio de `A` no
cambió: los límites de la ficha proceden de análisis estático y ninguna
medición los respalda; `S7` sigue sin camino de adjudicación en el motor
común; `G2`, `G3`, `G5`, `G9` y `G10` siguen sin caso discriminante en el
fixture; las pruebas usan fixtures propios y no dicen nada sobre
comportamiento a escala; el `LIKE 'prefijo%'` de `E3` no está indexado por la
cadena canónica; todo es un solo entorno (`LAB-LINUX`); y la anterioridad se
apoya en el grafo de Git. Ninguna se presenta como corregida. Una ficha no
acredita un candidato: si `ADR002-A` cumple sus límites es cosa del
benchmark, que no está autorizado.

## 9. Lo que esta acta no autoriza

- **No autoriza ejecutar el benchmark.**
- **No autoriza usar el corpus oficial.**
- **No autoriza medir rendimiento** de ningún candidato.
- No aprueba `ADR002-B` v2 ni corrige su sidecar.
- No modificar las fichas (ni la v3 ni ninguna otra) ni ningún límite
  congelado.
- No cambiar código de `ADR002-A` ni de `ADR002-B`.
- No implementar `ADR002-C` ni `ADR002-D`.
- No abrir `EJE-1` ni `EJE-2`.
- No elegir ganador ni declarar arquitectura final.
- No autorizar uso productivo ni modificar Sirius 0.1 (`src/`, `tests/`,
  `migrations/` ni configuración productiva).
- **No fusionar el PR #117.**

## 10. Reglas de custodia que siguen vigentes

1. Toda ficha se congela **antes** de la primera ejecución de su candidato, y
   la anterioridad se comprueba contra el grafo de Git, no contra una fecha.
2. Una ejecución que no referencie una ficha previa por `candidato · versión ·
   huella` **no es utilizable como evidencia**.
3. **Una sola ficha `CONGELADA` por candidato.** Publicar una sucesora obliga
   a marcar `SUSTITUIDA` la anterior y a **repetir** las ejecuciones hechas
   bajo ella — regla ya cumplida por la corrección 02 para esta v3.
4. Las versiones de ficha crecen de una en una y nunca retroceden.
5. Una ficha sustituida **se marca, no se borra ni se reescribe**: se conserva
   su contenido normativo y su blob original en el historial.
6. Cualquier cambio de los contenidos vinculados en §2 exige revisión y un
   **acto sucesor**.
7. La evidencia publicada no se reescribe: los errores se declaran mediante fe
   de erratas y documento sucesor.
8. Las etiquetas internas históricas permanecen como historia auditada y no
   disminuyen la autoridad de esta acta.

---

**Decisión final:** `ADR002-A` v3 queda **REAPROBADO como PREPARADO PARA
BENCHMARK**, con el alcance exacto del §1 y ni un milímetro más. `ADR002-B`
v2 permanece **PENDIENTE DE APROBACIÓN**. La ejecución del benchmark, el uso
del corpus oficial, la medición de rendimiento, la implementación de
`ADR002-C/D`, la apertura de `EJE-1` y `EJE-2`, la elección de ganador, la
modificación de Sirius 0.1 y la fusión del PR #117 **continúan no
autorizadas**.
