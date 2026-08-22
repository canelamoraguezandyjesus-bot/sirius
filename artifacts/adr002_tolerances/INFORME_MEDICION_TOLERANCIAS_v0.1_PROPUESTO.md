# SIRIUS 0.2 — ADR-002 · Informe de medición de la línea base FTS5

**Versión:** 0.1
**Estado:** PROPUESTO · informe de medición, no aprueba ni decide nada
**Fecha:** 25 de julio de 2026
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02_TOLERANCIAS_Y_MEDICION_v0.1.md`
**Evidencia legible por máquina:** `artifacts/adr002_tolerances/mediciones_linea_base.json`
**Código de medición:** `experiments/adr002/tolerances/`
**No autoriza:** benchmark comparativo T1–T4, implementación, elección de alternativa ni merge.

---

## 1. Metodología y entorno

### 1.1 Entorno

| Elemento | Valor |
|---|---|
| Python | 3.14.6 |
| Biblioteca SQLite | 3.45.1 |
| SQLAlchemy | 2.0.51 |
| Alembic | 1.18.5 |
| Plataforma | linux · x86_64 |
| Head de Alembic | `61be4bb269bf` |
| Commit de partida | `e9b975c8762e762a28466cbdf255e6437e4fd7c1` |
| Red | **no utilizada** |
| Datos reales | **ninguno** — corpus sintético determinista |
| Embeddings o modelos externos | **ninguno** |

### 1.2 Metodología

| Aspecto | Decisión |
|---|---|
| Reloj | `time.perf_counter_ns` — monotónico, nunca reloj de pared |
| Warm-up | 5 pasadas por escenario, descartadas y declaradas |
| Repeticiones | 100 en escenarios baratos (índice), 30 en escenarios caros (`rank()`); mínimo exigido 30, comprobado en ejecución |
| Percentil | **rango más cercano (nearest-rank)**, nunca interpolado |
| Fixtures | corpus y repositorios construidos **antes** de cronometrar; su coste nunca entra en la latencia |
| Pareado | las ramas de TOL-002 se muestrean **intercaladas** (A,B,A,B…) para anular la deriva |
| Aleatoriedad | ninguna; corpus determinista, sin semillas |
| Aislamiento | una única máquina y un único proceso para todas las comparaciones |
| Código medido | código **real** de Sirius 0.1 **sin modificar** |

**Por qué nearest-rank y no interpolación.** Un P99 interpolado puede devolver un valor que nunca ocurrió. Este informe solo afirma valores realmente observados.

**Resolución del P99, declarada.** Con n=100, el P99 es la peor muestra observada. Con n=30, el P99 por rango más cercano **coincide con el máximo**: acota la cola, no la caracteriza. Ninguna conclusión de este informe descansa sobre un P99 de n=30.

### 1.3 Corpus de referencia

| Elemento | Valor |
|---|---|
| Mensajes | **5.000** |
| Recuerdos | **500** (499 vigentes, 1 archivado) |
| Decisiones aprobadas | 50 |
| Proyectos | 2 (uno activo, uno ajeno) |
| Revisiones por recuerdo | 2 (una vigente) |

Tokens de control, cada uno un único término tras la tokenización:

| Token | Papel | Aciertos en el índice |
|---|---|---|
| `zetaausentenoindexado` | ausencia real | **0** |
| `zetaunicovigente` | resultado único | **1** |
| `zetafrecuente` | alta frecuencia | **200** |
| `zetaocultoarchivado` | existe pero **no reportable** (archivado) | **1** |
| `zetaproyectoajeno` | proyecto no activo | 1 |

El comportamiento de los cinco tokens está verificado por pruebas propias: sin ese control, cada escenario podría estar midiendo otra cosa.

---

## 2. Resultados P50 / P95 / P99

Todas las cifras en milisegundos.

### 2.1 Sustrato léxico aislado (FTS5 puro)

| Escenario | n | P50 | P95 | P99 | mín | máx |
|---|---|---|---|---|---|---|
| 0 resultados | 100 | **0,188** | 0,259 | 0,324 | 0,138 | 0,581 |
| 1 resultado exacto | 100 | **0,172** | 0,261 | 0,288 | 0,139 | 0,311 |
| 200 candidatos | 100 | **0,576** | 0,730 | 1,415 | 0,538 | 1,530 |

### 2.2 Recuperación completa (`rank()`)

| Escenario | n | P50 | P95 | P99 | mín | máx |
|---|---|---|---|---|---|---|
| 0 resultados | 30 | **122,649** | 137,799 | 154,369 | 116,651 | 154,369 |
| 1 resultado exacto | 30 | **113,260** | 125,052 | 128,978 | 107,404 | 128,978 |
| 200 candidatos | 30 | **117,755** | 131,106 | 144,677 | 108,973 | 144,677 |

### 2.3 El hallazgo dominante: el barrido es el 99,85 % del coste

Con **cero** aciertos en el índice, `rank()` sigue tardando 122,6 ms:

| Componente | P50 (ms) | Fracción |
|---|---|---|
| Consulta al índice FTS5 | 0,188 | 0,15 % |
| **Barrido completo del conocimiento vigente** | **122,461** | **99,85 %** |

FTS5 no es el coste de la recuperación de Sirius 0.1: el coste es recorrer las 499 memorias vigentes y las 50 decisiones aprobadas **en cada consulta**, aciertos o no. La latencia es prácticamente **independiente de la consulta** —122,6 ms con cero resultados frente a 117,8 ms con doscientos— porque el trabajo dominante es constante.

**Traza normativa:** este barrido es exactamente el «salto a recuperación amplia» que **B04-RF-14** prohíbe. La medición cuantifica lo que el trabajo 01B clasificó como inseguro: no es una ineficiencia menor, es el 99,85 % del coste.

---

## 3. Estabilidad observada

30 repeticiones idénticas por escenario:

| Escenario | Resultados | Órdenes distintos | Conjuntos distintos | Orden idéntico | Conjunto idéntico |
|---|---|---|---|---|---|
| 200 candidatos | 200 | **1** | **1** | sí | sí |
| 1 resultado | 1 | **1** | **1** | sí | sí |
| 0 resultados | 0 | **1** | **1** | sí | sí |

**Estabilidad perfecta.** Ni una sola variación de orden ni de conjunto. Era esperable —la clave de orden termina en un id sintético que garantiza orden total— pero ahora está medido, no supuesto.

**Variación entre ejecuciones completas del runner.** Dos ejecuciones independientes en la misma máquina, escenario de 0 resultados:

| Ejecución | P50 | P95 |
|---|---|---|
| Primera | 114,800 | 125,871 |
| Segunda | 122,649 | 137,799 |
| **Variación** | **+6,8 %** | **+9,5 %** |

El orden no varió entre ejecuciones; la latencia sí. Es el dato que fundamenta la tolerancia de variación entre ejecuciones equivalentes.

---

## 4. Tamaño, construcción y reconstrucción del índice

### 4.1 Tamaño físico (medido con `dbstat`, bytes reales por objeto)

| Objeto | Bytes |
|---|---|
| `knowledge_fts_content` | 57.344 |
| `knowledge_fts_data` | 45.056 |
| `knowledge_fts_docsize` | 12.288 |
| `knowledge_fts_config` + `_idx` | 8.192 |
| **`knowledge_fts` total** | **122.880** |
| `message_fts_data` | 184.320 |
| `message_fts_docsize` | 49.152 |
| `message_fts_config` + `_idx` | 8.192 |
| **`message_fts` total** | **241.664** |
| **Derivados totales** | **364.544** |
| Fichero completo | 1.462.272 |

### 4.2 Ratio sobre el canon indexado

| Índice | Canon que cubre | Tamaño | **Ratio** |
|---|---|---|---|
| `knowledge_fts` (autocontenida) | 34.732 B | 122.880 B | **×3,54** |
| `message_fts` (external content) | 338.890 B | 241.664 B | **×0,71** |

**El contraste cuantifica el hallazgo cualitativo del trabajo 01.** `knowledge_fts` ocupa **tres veces y media** el contenido que indexa porque guarda una copia literal del texto (`knowledge_fts_content`, 57.344 B) además del índice. `message_fts` ocupa **menos** que su canon porque no guarda copia alguna: lee el texto vivo de `messages`.

La diferencia entre ×3,54 y ×0,71 es, exactamente, el precio de almacenar el contenido dentro del derivado. Los derivados suman el **24,9 %** del fichero.

### 4.3 Ciclo completo

| Operación | ms | Resultado |
|---|---|---|
| **Borrado** de los derivados y sus triggers | 48,8 | **desaparición completa: sí**; sin rastro de tablas sombra |
| **Construcción inicial desde el canon** | 55,8 | 550 filas en `knowledge_fts`, 5.000 en `message_fts` — **idénticas a las originales** |
| **`rebuild` interno** | 17,0 | filas idénticas |
| **Reconstrucción desde el canon** | 49,1 | filas idénticas |
| `integrity-check` | — | **OK** en ambas tablas |

El DDL de la reconstrucción **no se escribió a mano**: se recupera de `sqlite_master`, de modo que se reconstruye exactamente lo que creó la migración canónica.

**Matiz importante.** El `rebuild` interno es el más rápido (17,0 ms) porque `knowledge_fts` se reconstruye **desde su propia tabla de contenido**, no desde `memory_revisions`. La reconstrucción **desde el canon** —la que ADR-001 exige— cuesta 49,1 ms, casi el triple. Ambas rutas restituyen el índice de forma idéntica, pero solo la segunda satisface la obligación.

---

## 5. Resultado de indistinguibilidad (TOL-002)

### 5.1 Modelo de amenaza y sus límites

**Modelo:** observador externo que solo ve la salida de la recuperación y puede cronometrarla repetidamente en la misma máquina y proceso.

**Queda fuera:** atacante con acceso al fichero, a las trazas internas o al canal de otra operación concurrente.

**Límites de esta medición:** una sola máquina, un solo proceso, una sola configuración. **No es una garantía criptográfica** y no sustituye a un análisis de canal lateral: acota lo observable en este entorno, nada más. Una diferencia temporal repetible atribuible a la existencia protegida **falla** aunque ambas consultas sean rápidas; una diferencia no repetible **no prueba lo contrario**.

### 5.2 Las cuatro dimensiones, por separado

| Dimensión | Ausencia real | No reportable | ¿Equivalentes? |
|---|---|---|---|
| **Estado externo** | 0 resultados | 0 resultados | **sí** |
| **Texto externo** | `[]` | `[]` | **sí** |
| **Conteo externo** | 0 | 0 | **sí** |
| **Tiempo** | ver §5.3 | ver §5.3 | ver §5.3 |

**Control de validez:** el contenido protegido **sí existe** en el índice (1 acierto) mientras que la ausencia real no (0 aciertos). Sin este control, la comparación no probaría nada.

### 5.3 Tiempo — medición pareada intercalada

**Recuperación completa (`rank()`), n=30 por rama:**

| Estadístico | Ausencia real | No reportable | Δ |
|---|---|---|---|
| P50 | 119,763 | 120,100 | **+0,337 ms (+0,3 %)** |
| P95 | 157,827 | 173,196 | +15,369 ms |
| P99 | 160,330 | 181,817 | +21,487 ms |
| **Fracción de signo** | — | — | **0,533** (16 de 30) |
| Mediana de la diferencia pareada | — | — | +0,911 ms |

**Sustrato léxico aislado, n=100 por rama:**

| Estadístico | Ausencia real | No reportable | Δ |
|---|---|---|---|
| P50 | 0,1545 | 0,1584 | **+0,0039 ms (+2,5 %)** |
| P95 | 0,2419 | 0,2192 | **−0,0227 ms** |
| P99 | 0,3102 | 0,2512 | **−0,0590 ms** |
| **Fracción de signo** | — | — | **0,490** (49 de 100) |
| Mediana de la diferencia pareada | — | — | −0,000 ms |

### 5.4 Lectura honesta de estos números

**No se observa diferencia temporal repetible.** El estadístico robusto aquí es la **fracción de signo**: con ramas indistinguibles debería rondar 0,5, y vale **0,533** y **0,490**. En el sustrato léxico las diferencias cambian de signo según el percentil (+0,0039 en P50, −0,0227 en P95, −0,0590 en P99), lo que es ruido, no señal.

**Lo que estos números NO permiten afirmar.** Con n=30 por rama, el P95 y el P99 de `rank()` son la segunda peor y la peor muestra: los Δ de +15,4 ms y +21,5 ms **no son interpretables**. No sostienen una acusación de canal lateral, pero tampoco una absolución de la cola. Para caracterizar la cola haría falta n mucho mayor, y esta ronda no lo hizo.

**El hallazgo incómodo.** La indistinguibilidad observada en `rank()` es en buena medida **accidental, no de diseño**. El barrido completo cuesta 122,5 ms y es idéntico en ambas ramas; la única diferencia real de trabajo —la del índice— es de 0,004 ms, es decir, unas **31.000 veces menor**. El trabajo constante enmascara la diferencia.

La consecuencia es contraintuitiva y conviene registrarla: **si un candidato elimina el barrido, como B04-RF-14 exige, dejará de tener ese enmascaramiento**. La misma corrección que hace conforme la expansión escalonada puede destapar un canal temporal que hoy no se observa. TOL-002 debe reevaluarse **con cada candidato**, y su banda no puede heredarse de esta medición.

---

## 6. Control: la fuga de ámbito persiste al volumen de referencia

| Consulta | Resultados totales | De proyecto ajeno | ¿Hay fuga? |
|---|---|---|---|
| `zetaproyectoajeno` | 1 | **1** | **sí** |

Confirmado a escala lo ya medido en el trabajo 01: **B04-RF-06** y **B04-M06** (aislamiento de proyecto, 100 %) siguen incumplidos.

---

## 7. Lo que NO se ha medido, y por qué

| Elemento | Motivo |
|---|---|
| **Coste incremental por etapa E0–E5** | **No medible en la línea base.** Sirius 0.1 no tiene etapas: resuelve en una sola pasada más el barrido completo. Este valor solo puede medirse contra un candidato que implemente E0–E5 |
| Coste externo | Ninguno: no se usó red, API ni modelo externo |
| T1–T4 | No ejecutadas en esta ronda, conforme al §1 del paquete |
| Comportamiento en Windows | Pendiente desde ADR-001; el tokenizador y la purga pueden diferir |
| Escala superior a la de referencia | No explorada; el paquete la permite como observación, no como requisito |
| Caracterización de la cola de TOL-002 | n=30 por rama es insuficiente; ver §5.4 |

---

## 8. Reproducción

```
uv run pytest experiments/adr002 -q
uv run python -m experiments.adr002.tolerances.run_measurements
uv run ruff format --check experiments/adr002/tolerances
uv run ruff check experiments/adr002/tolerances
```

Las mediciones se escriben en `artifacts/adr002_tolerances/mediciones_linea_base.json`. Ningún fichero de `src/`, `tests/`, `migrations/` ni configuración productiva se modifica: el experimento solo **lee** el código real de Sirius 0.1 y crea bases SQLite en el directorio temporal del sistema.

---

**Siguiente movimiento único:** que el usuario revise este informe junto al `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.1_PROPUESTO.md` y decida si aprueba el Registro antes de construir corpus de benchmark o ejecutar cualquier candidato.
