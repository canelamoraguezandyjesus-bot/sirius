# SIRIUS 0.2 — ADR-002 · Informe de medición de la línea base FTS5

**Versión:** 0.2
**Estado:** PROPUESTO · informe de medición, no aprueba ni decide nada
**Fecha:** 25 de julio de 2026
**Sustituye a:** `INFORME_MEDICION_TOLERANCIAS_v0.1_PROPUESTO.md`, que se conserva sin modificar
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02B_CORRECCION_TOLERANCIAS_v0.1.md`
**Evidencia legible por máquina:** `artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json`
**Código:** `experiments/adr002/tolerances/`
**Alcance:** **LAB-LINUX** — ver §1.3
**No autoriza:** benchmark T1–T4, implementación, aprobación del Registro ni merge.

---

## 0. Qué corrige esta versión

El paquete 02 produjo evidencia válida con **dos defectos de método** y **una contradicción normativa**. Esta versión los corrige y **conserva intacto todo lo demás**.

| Defecto | v0.1 | v0.2 |
|---|---|---|
| Ciclo del índice | Una sola pasada, justificada como «irrepetible por naturaleza» — **afirmación falsa** | **30 repeticiones** sobre copias limpias independientes, con distribución completa y tasa de éxito |
| Variación entre ejecuciones | Estimada con **2** ejecuciones (9,5 %) | **5 sesiones independientes**; la variación real llega al **36,4 %** |
| TOL-204 críticos pendientes | `REGLA_CONFIRMADA_VALOR_CANDIDATO` — **contradecía B04** | **Umbral canónico: 0 críticos elegibles pendientes.** No depende del candidato |
| Alcance de las cifras | No declarado | **LAB-LINUX**; `ACEPTACIÓN-WINDOWS` pendiente |

**Evidencia arrastrada literalmente del paquete 02, no reejecutada:** latencias por escenario, coste del barrido, TOL-002, tamaño físico, estabilidad intra-sesión y control de fuga de ámbito. La igualdad literal entre ambos artefactos la verifica una prueba automática.

### 0.1 Las dos estimaciones del v0.1 que la evidencia nueva refuta

Conviene decirlo sin rodeos, porque afecta a dos tolerancias que ya se habían propuesto:

1. **La reconstrucción desde el canon del v0.1 (49,1 ms) estaba por encima del máximo de las 30 repeticiones (44,5 ms).** Una sola pasada no era representativa: sobreestimaba la mediana real (29,3 ms) en un 68 %.
2. **La variación entre ejecuciones del v0.1 (9,5 %) subestimaba la real.** Con cinco sesiones, el peor valor observado es **36,4 %**, casi cuatro veces mayor. El objetivo del 25 % que proponía ADR002-TOL-107 v0.1 **queda refutado por la evidencia** y se corrige en §6, sin rebajarlo para que encaje.

---

## 1. Metodología, entorno y alcance

### 1.1 Entorno

| Elemento | Valor |
|---|---|
| Python | 3.14.6 |
| Biblioteca SQLite | 3.45.1 |
| SQLAlchemy | 2.0.51 |
| Alembic | 1.18.5 |
| Plataforma | linux · x86_64 |
| Head de Alembic | `61be4bb269bf` |
| Commit de partida | `610d10c5410438ad6251ebf0f813832539a6daef` |
| Red | **no utilizada** |
| Datos reales | **ninguno** — corpus sintético determinista |
| Embeddings o modelos externos | **ninguno** |
| T1–T4 | **no ejecutadas** |

### 1.2 Metodología

Se conserva la del paquete 02 —reloj monotónico, warm-up declarado y descartado, percentiles por rango más cercano nunca interpolados, fixtures fuera del cronómetro— y se añade:

| Aspecto | Decisión |
|---|---|
| Ciclo del índice | **30 repeticiones** + 2 de warm-up descartadas. Cada una sobre una **copia limpia e independiente**. La copia, la conexión, la lectura del DDL y **todas** las verificaciones quedan fuera del cronómetro |
| DDL de reconstrucción | Recuperado de `sqlite_master`, **nunca escrito a mano** |
| Sesiones | **5 sesiones independientes**, cada una con fichero, motor SQLAlchemy, caché y warm-up propios |
| Fórmula de variación | `(máx − mín) / mín` sobre el mismo percentil en todas las sesiones — el peor par posible, independiente del orden |

**Límite declarado de las sesiones.** Son independientes **dentro del mismo proceso**: comparten intérprete y máquina. **No** son procesos separados ni máquinas distintas. Acotan la variación intra-proceso, no la variación entre entornos. Esto importa para §6.

### 1.3 Alcance: LAB-LINUX, no aceptación Windows

**Todas las cifras de esta ronda son umbrales del laboratorio comparativo Linux.** Sirven para comparar T1–T4 entre sí en el mismo entorno, y solo para eso.

**`ACEPTACIÓN-WINDOWS` queda PENDIENTE.** Ninguna cifra absoluta de latencia, tamaño o ciclo se traslada automáticamente a Windows. La aceptación del producto exige confirmar el comportamiento sobre el ejecutable o el entorno de referencia Windows, incluidos el tokenizador, `secure_delete` y la secuencia de purga que ADR-001 dejó pendientes.

**Lo que sí es trasladable** son las comprobaciones booleanas: restitución idéntica, `integrity-check`, desaparición completa del derivado y estabilidad de orden y conjunto. Son propiedades de comportamiento, no cifras de rendimiento.

---

## 2. Corrección de TOL-204: cero críticos elegibles pendientes

El paquete 02 clasificó ADR002-TOL-204 como `REGLA_CONFIRMADA_VALOR_CANDIDATO`, dejando el umbral de cobertura de críticos «pendiente de congelar con cada candidato». **Eso contradecía B04 v1.0**, que ya lo fija.

B04 establece:

- la expansión continúa cuando falta suficiencia **o queda un crítico elegible pendiente**;
- S1 solo puede operar en cardinalidad `EXACTA` o `ACOTADA` **tras comprobar que no queda ningún crítico elegible pendiente** en espacios autorizados;
- una consulta `EXHAUSTIVA` **nunca** termina por S1;
- **B04-M01** exige 100 % de críticos recuperados por caso; bajo límite duro, todo crítico omitido debe contabilizarse y el desbordamiento debe ser **visible**.

Por tanto, en el Registro v0.2:

- **el umbral operativo es `0` críticos elegibles pendientes**;
- **no se congela por candidato**: el candidato solo decide **cómo** implementa y demuestra la comprobación, nunca el umbral;
- si el límite duro impide incluirlos, los críticos omitidos **se contabilizan** y la salida es **`PARCIAL` visible**, nunca suficiencia completa.

La fila pasa de `REGLA_CONFIRMADA_VALOR_CANDIDATO` a **`DERIVADA_CANÓNICA`**, y su valor no admite margen.

---

## 3. Ciclo del índice — 30 repeticiones

Cada repetición sobre una copia limpia e independiente. Todas las cifras en ms.

| Operación | n | P50 | P95 | P99 | mín | máx | media |
|---|---|---|---|---|---|---|---|
| **Borrado completo del derivado** | 30 | **43,564** | 84,303 | 122,865 | 33,861 | 122,865 | 48,356 |
| **Construcción inicial desde el canon** | 30 | **51,859** | 96,645 | 102,571 | 40,361 | 102,571 | 57,895 |
| **Reconstrucción desde el canon** | 30 | **29,294** | 41,745 | 44,512 | 26,232 | 44,512 | 31,491 |
| *(observación)* `rebuild` interno | 30 | *18,715* | *32,951* | *269,912* | *16,271* | *269,912* | *29,100* |

**Resolución declarada:** con n=30, el P99 por rango más cercano **coincide con el máximo observado**. Acota la cola; no la caracteriza.

### 3.1 Tasas de éxito — las cinco al 100 %

| Comprobación | Éxitos | Tasa |
|---|---|---|
| Borrado completo del derivado | 30/30 | **100 %** |
| Sin rastro de tablas sombra | 30/30 | **100 %** |
| Construcción: filas idénticas a las originales | 30/30 | **100 %** |
| Reconstrucción: filas idénticas a las originales | 30/30 | **100 %** |
| `integrity-check` correcto | 30/30 | **100 %** |

**Ninguna repetición con fallo.** Estas cinco comprobaciones no admiten margen: son la puerta 5 de ADR-002 y las consecuencias 2 y 3 de ADR-001.

### 3.2 El `rebuild` interno sigue siendo solo una observación

Es la operación más rápida en mediana (18,7 ms) pero reconstruye `knowledge_fts` **desde su propia tabla de contenido**, no desde `memory_revisions`. **No satisface la obligación de ADR-001** y no puede presentarse como evidencia de reconstrucción desde el canon.

La medición repetida añade una razón más para desconfiar de él: su **P99 es de 269,9 ms**, seis veces su P95 (33,0 ms). Un único valor atípico de esa magnitud no aparecía en la pasada única del v0.1.

### 3.3 Qué cambia respecto de la pasada única del v0.1

| Operación | v0.1 (1 pasada) | v0.2 P50 | v0.2 P99 | Lectura |
|---|---|---|---|---|
| Borrado | 48,8 | 43,6 | 122,9 | La pasada única quedaba entre P50 y P95; la cola real es 2,5× peor |
| Construcción | 55,8 | 51,9 | 102,6 | Similar |
| **Reconstrucción** | **49,1** | **29,3** | **44,5** | **La pasada única estaba por encima del máximo de 30 repeticiones** |

La tercera fila es la más elocuente: el valor con el que se propuso ADR002-TOL-105 v0.1 no era representativo de nada. La distribución real es más rápida en mediana y tiene una cola acotada por debajo de aquel único valor.

---

## 4. Sesiones independientes — 5 sesiones

P50 por sesión, en ms.

| Escenario | Capa | S1 | S2 | S3 | S4 | S5 | Var. máx |
|---|---|---|---|---|---|---|---|
| 0 resultados | FTS5 | 0,182 | 0,141 | 0,144 | 0,150 | 0,161 | **29,3 %** |
| 0 resultados | `rank()` | 128,586 | 121,251 | 125,646 | 120,853 | 116,286 | **10,6 %** |
| 1 resultado | FTS5 | 0,190 | 0,172 | 0,167 | 0,156 | 0,156 | **22,0 %** |
| 1 resultado | `rank()` | 115,519 | 119,409 | 127,763 | 117,469 | 120,983 | **10,6 %** |
| 200 candidatos | FTS5 | 0,601 | 0,631 | 0,614 | 0,676 | 0,596 | **13,4 %** |
| 200 candidatos | `rank()` | 118,208 | 121,151 | 120,920 | 120,588 | 117,817 | **2,8 %** |

Variación en P95:

| Escenario | Capa | mín | máx | Var. máx |
|---|---|---|---|---|
| 0 resultados | FTS5 | 0,188 | 0,255 | **35,1 %** |
| 0 resultados | `rank()` | 125,809 | 145,663 | **15,8 %** |
| 1 resultado | FTS5 | 0,217 | 0,288 | **32,9 %** |
| 1 resultado | `rank()` | 127,777 | 143,538 | **12,3 %** |
| 200 candidatos | FTS5 | 0,736 | 1,004 | **36,4 %** |
| 200 candidatos | `rank()` | 127,500 | 147,176 | **15,4 %** |

**Peor variación relativa observada: 36,4 %.**

### 4.1 Estabilidad entre sesiones: perfecta

| Comprobación | Resultado |
|---|---|
| Orden idéntico entre las 5 sesiones | **sí**, en los tres escenarios |
| Conjunto idéntico entre las 5 sesiones | **sí**, en los tres escenarios |

El orden y el conjunto **no varían** entre sesiones independientes. Solo varía el tiempo.

### 4.2 Lectura honesta de la variación

**Las dos capas se comportan de forma distinta y no deben mezclarse.**

- **`rank()`**, con magnitudes de ~120 ms: variación de **2,8 % a 15,8 %**. Es una señal interpretable.
- **FTS5**, con magnitudes de 0,14 a 1,0 ms: variación de **13,4 % a 36,4 %**. A escala de décimas de milisegundo, la resolución del reloj y el ruido del planificador **dominan** el resultado. Una variación relativa del 36 % sobre 0,74 ms son 0,27 ms de diferencia absoluta: no es inestabilidad del sistema, es el suelo de medición.

Por eso el Registro v0.2 propone objetivo **solo para `rank()`** y trata la capa de sub-milisegundo en términos absolutos, no relativos.

**Y por eso no se fija un límite duro.** Cinco sesiones **dentro del mismo proceso** y en una máquina cuya carga no controlamos no bastan para fijar un techo defendible que deba cumplirse en otro entorno. El paquete 02B autoriza expresamente esta salida: el objetivo queda `PROPUESTA` y el límite duro se clasifica como **`REGLA_CONFIRMADA_VALOR_ENTORNO`**, no se inventa.

---

## 5. Evidencia arrastrada del paquete 02, sin reejecutar

Copiada literalmente y verificada por prueba automática. Se resume aquí para lectura; el detalle está en el JSON.

| Elemento | Resultado |
|---|---|
| Latencia FTS5 | P50 0,172–0,576 ms · P95 0,209–0,730 ms |
| Latencia `rank()` | P50 113,3–122,6 ms · P95 125,1–137,8 ms |
| **Coste del barrido** | **99,85 % del total** — 122,461 ms de 122,649 ms con cero aciertos |
| Tamaño `knowledge_fts` | 122.880 B · **×3,54** sobre el canon que indexa |
| Tamaño `message_fts` | 241.664 B · **×0,71** sobre el canon que indexa |
| TOL-002 estado/texto/conteo | **equivalentes** |
| TOL-002 tiempo | sin diferencia repetible; fracción de signo 0,533 y 0,490 |
| Estabilidad intra-sesión | 1 orden y 1 conjunto en 30 repeticiones |
| Fuga de ámbito | **persiste** — incumple RF-06 y M06 |

**TOL-002 conserva su conclusión y sus límites**, incluida la advertencia central: la indistinguibilidad observada es **en buena medida accidental**, porque el barrido constante enmascara una diferencia de trabajo unas 31.000 veces menor. Un candidato que elimine el barrido perderá ese enmascaramiento. **El resultado no se hereda a los candidatos.**

Conforme al §6 del paquete 02B, la fracción de signo se conserva como **una** condición de la banda, **nunca como única protección**: el candidato deberá demostrar además ausencia de separación material en distribución y repetir la medición en sesión independiente.

---

## 6. Consecuencias para las tolerancias propuestas

| Fila | v0.1 | v0.2 | Motivo |
|---|---|---|---|
| **TOL-105** reconstrucción | objetivo ≤ 100 ms (×2 sobre una pasada de 49,1 ms) | objetivo por operación sobre **P95 real**; límite duro sobre la cola observada | La pasada única no era representativa |
| **TOL-107** variación | objetivo ≤ 25 %, límite duro ≤ 50 % (sobre 2 ejecuciones) | objetivo **solo para `rank()`**; límite duro → `REGLA_CONFIRMADA_VALOR_ENTORNO` | El peor valor real es 36,4 %, y 5 sesiones intra-proceso no fundan un techo |
| **TOL-204** críticos | `REGLA_CONFIRMADA_VALOR_CANDIDATO` | **`DERIVADA_CANÓNICA`: 0 críticos elegibles pendientes** | Contradecía B04 |
| **TOL-106** borrado | booleano, sin distribución | booleano **+ distribución de 30 repeticiones** y tasa 100 % | Ahora hay evidencia repetida |

Las demás filas propuestas en el paquete 02 se conservan, con su alcance marcado como **LAB-LINUX**.

---

## 7. Lo que sigue sin medirse

| Elemento | Motivo |
|---|---|
| **Coste incremental por etapa E0–E5** | No medible en la línea base: Sirius 0.1 no tiene etapas |
| **Aceptación Windows** | Pendiente; ninguna cifra Linux se traslada automáticamente |
| **Variación entre procesos o máquinas** | Las sesiones son intra-proceso; la variación entre entornos **no** se ha medido |
| **Caracterización de la cola** | Con n=30, el P99 es el máximo observado |
| **T1–T4** | No ejecutadas |

---

## 8. Reproducción

```
uv run pytest experiments/adr002 -q
uv run python -m experiments.adr002.tolerances.run_remeasurement
uv run ruff format --check experiments/adr002/tolerances
uv run ruff check experiments/adr002/tolerances
```

`measurements.py` **no se ha modificado**: la evidencia del paquete 02 sigue siendo reproducible tal cual, y la remedición vive en `remeasurement.py` y `run_remeasurement.py`. Ningún fichero de `src/`, `tests/`, `migrations/` ni configuración productiva se modifica. Los artefactos v0.1 se conservan intactos.

---

**Siguiente movimiento único:** que el usuario revise este informe junto al `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.2_PROPUESTO.md` y decida si aprueba el Registro antes de construir corpus de benchmark o ejecutar cualquier candidato.
