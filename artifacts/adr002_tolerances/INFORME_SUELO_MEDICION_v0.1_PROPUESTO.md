# SIRIUS 0.2 — ADR-002 · Informe del suelo de medición LAB-LINUX

**Versión:** 0.1
**Estado:** **PROPUESTO** · informe de medición · **no aprueba `ADR002-TOL-209`**
**Fecha:** 30 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Fase:** D — ejecución de la preinscripción
**Commit A de preinscripción:** `442877c0c679f15ebc6d316b833ffa877ff96ecb`
**Paquete:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_05_TOL209_SUELO_v0.1.md`
**Protocolo aplicado:** `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md` (aprobado, blob `c298a6b804309a78062f79b6341adfea2374ce56`)
**Evidencia legible por máquina:** `artifacts/adr002_tolerances/suelo_medicion_v0.1.json`

**No autoriza:** aprobar `ADR002-TOL-209` · crear acta · fijar el límite duro de `TOL-107` · ejecutar T0 · implementar o ejecutar `ADR002-A/B/C/D` · iniciar el benchmark · fusionar el PR #117.

---

## 0. Qué se ejecutó

El recorrido preinscrito en el commit A, **sin modificar una sola línea de código**:

```
uv run python -m experiments.adr002.tolerances.run_floor \
  --execute \
  --preinscription-commit 442877c0c679f15ebc6d316b833ffa877ff96ecb \
  --output artifacts/adr002_tolerances/suelo_medicion_v0.1.json
```

**Resultado: corrida válida al primer intento.** Código de salida 0. **No se ejerció la repetición controlada del §6.5** del protocolo, porque ningún control ambiental ni instrumental falló. Los doce controles bloqueantes salieron `True`.

Las precondiciones se verificaron antes de abrir la primera ventana cronometrada y **de nuevo después de medir, antes de publicar**: árbol de trabajo limpio, `HEAD` igual al commit A, los seis blobs preinscritos y el de `harness.py` coincidentes con lo que el commit A registra, protocolo aprobado intacto, los siete blobs del corpus congelado intactos, ruta de salida inexistente.

---

## 1. Valores observados

Todo en **nanosegundos enteros**, nearest-rank, sin interpolar y sin redondeo previo.

| Magnitud | Valor observado (ns) | Equivalente informativo |
|---|---:|---|
| **`SM`** — guarda de dominancia instrumental | **21.451** | 0,021451 ms |
| **`B50`** — peor dispersión de P50 entre procesos | **476** | 0,000476 ms |
| **`B95`** — peor dispersión de P95 entre procesos | **9.758** | 0,009758 ms |
| **`B` = max(B50, B95)** — banda absoluta | **9.758** | 0,009758 ms |
| **`U` = B / 0,20 = 5 × B** — umbral de conmutación | **48.790** | 0,048790 ms |
| **`m`** — margen | **1** | — |

Los valores en milisegundos son **únicamente informativos**. Los normativos son los enteros en nanosegundos.

### 1.1 Descomposición de `B` por sonda y percentil

| Sonda de `F` | `B50` (ns) | `B95` (ns) | Procesos |
|---|---:|---:|---:|
| `D_vacia` | 15 | 68 | 5 |
| `SQLite_0_filas` | 476 | 7.872 | 5 |
| `SQLite_1_fila` | 283 | **9.758** | 5 |

`B` la determina el **P95 de `SQLite_1_fila`**. `B95 ≥ B50` en las tres sondas, de modo que `B = B95`, tal como anticipa la limitación 1 del paquete: **P50 recibe una banda más ancha que su propia `B50` (9.758 frente a 476) y un `U` derivado de la dispersión de P95**. La indulgencia compuesta sobre P50 es, en esta corrida, de un factor ≈20.

### 1.2 Distribuciones por sonda y proceso

| Sonda | P50 por proceso (ns) | P95 por proceso (ns) |
|---|---|---|
| `D_vacia` | 133 · 138 · 147 · 132 · 144 | 304 · 310 · 250 · 242 · 243 |
| `SQLite_0_filas` | 7.052 · 6.929 · 7.292 · 6.816 · 7.137 | 13.997 · **21.451** · 18.603 · 13.579 · 13.696 |
| `SQLite_1_fila` | 7.493 · 7.521 · 7.533 · 7.263 · 7.546 | 16.963 · 17.973 · 15.644 · 8.215 · 14.175 |

`SM = 21.451` ns proviene del P95 de `SQLite_0_filas` en el segundo proceso: es el peor P95 observado sobre `F` y todos los procesos.

**Forma de los vectores** (diagnóstico, no umbral): valores distintos 35–58 en `D_vacia` y 90–99 en las sondas SQLite, con repetición máxima 2–14 sobre `n = 100`. Ningún vector muestra la firma de un repadeado tras recorte.

---

## 2. Controles internos

Los doce **bloqueantes**, todos satisfechos:

| Control | Resultado | Evidencia observada |
|---|---|---|
| `procesos_independientes` | ✅ | 5 procesos del sistema operativo |
| `pids_distintos` | ✅ | PIDs 3045 · 3046 · 3405 · 3406 · 3407 |
| `carga_registrada` | ✅ | 3 lecturas por proceso; carga 0,289 → 0,447 |
| `boot_id_estable` | ✅ | `6273aecb-02a7-4769-be84-ba331232c833`, idéntico inicio y fin |
| `busy_spin_estable` | ✅ | Sin crecimiento monótono (ver §3.2) |
| `duplicacion_1x_2x` | ✅ | Razones 1,912 – 2,032 (ver §3.3) |
| `vectores_crudos_completos` | ✅ | 15 vectores de `n = 100` enteros en ns |
| `sin_filtrado` | ✅ | Ningún outlier eliminado, recortado ni winsorizado |
| `warmup_separado` | ✅ | 5 descartadas por sonda, recomputado contra el preinscrito |
| `sin_redondeo_previo` | ✅ | Nanosegundos sin redondear |
| `captura_ambiental_presente` | ✅ | Capturas inicial y final adjuntas |
| `custodia_verificada` | ✅ | Reverificada tras medir, antes de publicar |

**Incidencias registradas: ninguna.** Las dos sondas SQLite devolvieron exactamente la forma declarada (cero filas y una fila respectivamente).

---

## 3. Diagnósticos, fuera de `F`

Ninguno modifica `B` ni `U`.

### 3.1 Resolución efectiva del reloj

`n = 100.000` lecturas consecutivas por proceso, 1.000 de warm-up descartadas.

| Proceso | Δ mínimo no nulo (ns) | P50 (ns) | Deltas distintos |
|---|---:|---:|---:|
| 1 | 115 | 124 | 761 |
| 2 | 113 | 125 | 761 |
| 3 | 112 | 124 | 591 |
| 4 | 111 | 124 | 600 |
| 5 | 113 | 124 | 574 |

**Lectura honesta:** **no se observó ningún delta nulo** en 500.000 lecturas. Eso significa que el *tick* del reloj es más fino que el coste de leerlo: la granularidad real del reloj **no es observable por este método**, y lo que estas cifras miden es el **coste de una lectura de `perf_counter_ns`, ≈124 ns**. Como el paquete declara (decisión 2), el bucle cerrado representa el **mejor caso** y **subestima** el coste real de leer el reloj bajo carga. Esta sonda no entra en el presupuesto de ruido.

### 3.2 Busy-spin calibrado (10.000 vueltas)

P50 en inicio / mitad / final de cada proceso, en ns:

| Proceso | Inicio | Mitad | Final |
|---|---:|---:|---:|
| 1 | 459.892 | 459.255 | 467.670 |
| 2 | 480.768 | 475.552 | 482.316 |
| 3 | 460.424 | 457.474 | 464.134 |
| 4 | 448.228 | 460.751 | 447.237 |
| 5 | 462.002 | 447.409 | 448.542 |

**Sin deriva ni throttling:** en ningún proceso el P50 crece de forma estrictamente monótona entre los tres puntos. Las excursiones son de ±2 % sobre un trabajo fijo.

### 3.3 Comprobación 1× / 2×

| Proceso | 1× (ns) | 2× (ns) | Razón |
|---|---:|---:|---:|
| 1 | 453.798 | 922.065 | 2,032 |
| 2 | 477.076 | 957.666 | 2,007 |
| 3 | 463.479 | 917.259 | 1,979 |
| 4 | 471.954 | 902.243 | 1,912 |
| 5 | 459.959 | 931.032 | 2,024 |

**El arnés no domina la medida** al nivel de trabajo probado: doblar el trabajo dobla el tiempo dentro de la tolerancia preinscrita de 3/10.

### 3.4 Sobrecoste del puerto común

P50 por proceso, del puerto equivalente a `KnowledgeSearchRepository` (resuelve sobre FTS5): **290.362 · 273.138 · 275.190 · 275.632 · 286.426 ns**.

El puerto cuesta **≈37 veces** lo que `SQLite_1_fila` (P50 ≈7.500 ns). Confirma con evidencia la decisión 8: incorporarlo a `F` habría elevado `B` y `U` de forma sustancial y empujado más magnitudes al régimen absoluto. Queda como diagnóstico.

---

## 4. Clasificación diagnóstica de la línea base

Aplicando `SM`, `B` y `U` observados a las magnitudes de `mediciones_linea_base_v0.2.json`. **Es divulgación diagnóstica: no modifica `B` ni `U`.**

| Magnitud | mín P50 (ns) | mín P95 (ns) | Régimen |
|---|---:|---:|---|
| `cero_resultados` · `rank()` | 116.286.300 | 125.809.200 | P50 relativo · P95 relativo |
| `cero_resultados` · FTS5 | 140.700 | 188.400 | P50 relativo · P95 relativo |
| `un_resultado_exacto` · `rank()` | 115.518.500 | 127.777.300 | P50 relativo · P95 relativo |
| `un_resultado_exacto` · FTS5 | 155.800 | 216.900 | P50 relativo · P95 relativo |
| `muchos_candidatos` · `rank()` | 117.817.400 | 127.499.800 | P50 relativo · P95 relativo |
| `muchos_candidatos` · FTS5 | 596.200 | 735.700 | P50 relativo · P95 relativo |

**Ninguna magnitud queda dominada por el instrumento:** el mín P95 más bajo (188.400 ns) supera `SM` (21.451 ns) por un factor 8,8. No hay ningún `NO_EVALUABLE` por guarda de dominancia.

---

## 5. Hallazgo material: el riesgo de la limitación 5 se ha materializado

**Debe explicarse, no corregirse.** Así lo fija la decisión 7 del paquete y la limitación 5 del §8.

`U = 48.790` ns queda **por debajo** del escenario FTS5 más rápido (mín P50 = 140.700 ns). En consecuencia **toda la capa FTS5 cae en régimen relativo**, cuando el Registro v0.4 declara para esa escala que «**a esa escala la comparación debe hacerse en valor absoluto**» y que el objetivo relativo es «**solo para `rank()`**» (línea 480).

Consecuencia calculada aplicando los criterios congelados —relativo `(máx−mín)/mín ≤ 0,20`, absoluto `máx−mín ≤ B`— a las variaciones históricas:

| Magnitud | Var. P50 | Var. P95 | Veredicto con `U` observado |
|---|---:|---:|---|
| `cero_resultados` · `rank()` | 10,6 % | 15,8 % | **VÁLIDA** |
| `un_resultado_exacto` · `rank()` | 10,6 % | 12,3 % | **VÁLIDA** |
| `muchos_candidatos` · `rank()` | 2,8 % | 15,4 % | **VÁLIDA** |
| `cero_resultados` · FTS5 | 29,3 % | 35,1 % | **INVÁLIDA** (P50 y P95 fallan) |
| `un_resultado_exacto` · FTS5 | 22,0 % | 32,9 % | **INVÁLIDA** (P50 y P95 fallan) |
| `muchos_candidatos` · FTS5 | 13,4 % | 36,4 % | **INVÁLIDA** (P95 falla) |

### 5.1 Causa técnica, demostrada con la propia evidencia

Las sondas de `F` son **más baratas y más estables** que cualquier consulta real:

- **Coste:** `D_vacia` P50 ≈133–147 ns; sondas SQLite P50 ≈6.800–7.550 ns; FTS5 más barato 140.700 ns (≈19× la sonda SQLite); puerto real ≈275.000 ns (≈37×).
- **Estabilidad:** `B95` medido = 9.758 ns, frente a dispersiones absolutas históricas del P95 de FTS5 entre sesiones de **66.100 · 71.300 · 268.100 ns** — entre 7 y 27 veces mayores.

`B` pequeño ⇒ `U` pequeño ⇒ magnitudes que el Registro situaba en régimen absoluto pasan al relativo. **Es exactamente el mecanismo que el paquete anticipó y aceptó divulgar.**

Nótese además que el «suelo de medición» que el propio Registro nombra —0,27 ms, es decir 270.000 ns— es **≈27 veces mayor que la `B` medida**. No hay contradicción: aquella cifra es la dispersión de una consulta **FTS5 completa**, que incluye el trabajo de FTS5; `B` mide la dispersión del **suelo puro**, sin ese trabajo.

### 5.2 Qué NO se ha hecho

- **No se ha rebajado `B`.** Reducirla haría alcanzable el régimen absoluto para FTS5 y sería fijar un valor tras observar su consecuencia — prohibido por la regla dura 1 del §9 del Registro y por la condición bloqueante 36.
- **No se ha ajustado `U`.** Su fórmula estaba preinscrita en el commit A: `U = B / 0,20`.
- **No se ha alterado la composición de `F`.** Añadir FTS5 elevaría `B` y produciría la clasificación «esperada», que es precisamente la manipulación que la decisión 8 prohíbe.
- **No se ha suavizado ningún control.**

### 5.3 Qué decisión abre

Esta clasificación **no invalida el suelo medido**: `SM`, `B50`, `B95`, `B` y `U` son observaciones legítimas de este entorno, obtenidas bajo el protocolo aprobado y con los doce controles en verde. Lo que abre es una **decisión normativa que no corresponde a esta fase**: si el régimen que resulta para la capa FTS5 es aceptable, o si el Registro requiere una revisión de la composición de `F` mediante acto sucesor. **Esta fase no la resuelve y no la prejuzga.**

---

## 6. Entorno

| Elemento | Valor |
|---|---|
| Plataforma | Linux · x86_64 · Ubuntu 24.04 |
| Contenedor | virtualizado (`systemd_detect_virt: docker`, flag de hipervisor presente) |
| CPU | Intel Xeon @ 2.10 GHz · 4 núcleos |
| `boot_id` | `6273aecb-02a7-4769-be84-ba331232c833`, estable inicio → fin |
| Carga observada | 0,289 al inicio → 0,447 al final; 3 lecturas por proceso |
| Corpus por proceso | Construido con la cadena canónica de Alembic y poblado por `corpus.poblar` |
| Tabla canónica de las sondas | `memory_revisions`, clave primaria `id` |
| Alcance | **LAB-LINUX**; `ACEPTACIÓN-WINDOWS` sigue pendiente |

---

## 7. Custodia verificada

| Elemento | Estado |
|---|---|
| `commit_a` publicado | `442877c0c679f15ebc6d316b833ffa877ff96ecb` |
| `head_en_ejecucion` | idéntico a `commit_a` |
| `custodia.head` al publicar | idéntico a `commit_a` |
| `sha_a_es_ancestro` | `true` |
| `diff_preinscritos_vacio` | `true` |
| `reverificada_tras_medir` | `true` |
| Blobs de los seis ficheros preinscritos | coinciden con lo que registra el commit A (`git rev-parse <A>:<ruta>`) |
| Blob de `harness.py` | `119c5e831b1a533825353d35f7e0326c509f2e68`, coincide |
| Blob del protocolo aprobado | `c298a6b804309a78062f79b6341adfea2374ce56`, intacto |
| Los siete blobs del corpus congelado | 7 de 7 intactos |

---

## 8. Verificación independiente de la evidencia

Además de la validación con el esquema congelado —`fallos_suelo_medicion` devolvió **cero fallos**—, se recompusieron `SM`, `B50`, `B95`, `B`, `U` y la descomposición **desde los vectores crudos con aritmética escrita de cero**, sin importar ningún módulo del paquete. Los cinco valores y las tres descomposiciones coinciden exactamente con lo publicado. Se comprobaron también, por separado: percentiles nearest-rank de las 15 entradas, coherencia de `n`, ausencia de muestras negativas, warm-up igual a 5 en todas las sondas de `F`, cinco PIDs distintos por sonda, y los blobs publicados contra `git`.

---

## 9. Limitaciones e incidencias

**Incidencias de la corrida: ninguna.** Ningún control falló, no se ejerció la repetición controlada.

Limitaciones, todas ya declaradas en el paquete y ahora con cifra observada:

1. **Indulgencia compuesta sobre P50** — factor ≈20 en esta corrida (`B` = 9.758 frente a `B50` = 476). Es el coste aceptado de una banda única compatible con la ficha aprobada.
2. **`B` incorpora el comportamiento de SQLite** (caché de páginas, B-tree). Correcto —es el suelo que todo candidato paga— y acotado por ADR-001, que fija SQLite como sustrato común.
3. **`B` hace doble función**: define `U` y es el criterio del régimen absoluto. No es circular, pero por eso los doce controles son bloqueantes y `B` se publica descompuesta.
4. **La inercia de `B` no se verifica en esta puerta.** Depende de las magnitudes que el benchmark compare, que salen de la rederivación de T0 (`ADR002-TOL-208` paso 2). Con los datos históricos disponibles el régimen relativo **sí** es alcanzable —los tres escenarios de `rank()` lo alcanzan y pasan—, luego `B` no es inerte en el sentido del §1.1 del paquete.
5. **La composición de `F` determinó la clasificación**, y el riesgo se materializó. Documentado íntegro en el §5.
6. **Una sola máquina y un solo sistema operativo.** Esta corrida mide por primera vez el ruido **entre procesos** —`N_proc` y `Δ_sesiones`—, lo que **reduce pero no elimina** la laguna que motiva no fijar el límite duro de `TOL-107`. **El límite duro sigue sin fijarse y este informe no lo fija.**
7. **El sesgo residual del ≤20 % por encima de `U`** permanece: con el mismo jitter absoluto, una operación más lenta obtiene un cociente menor.
8. **El filtrado silencioso de un proceso no es detectable con certeza.** Se publica la forma del vector (`valores_distintos`, `repeticion_maxima`) para el auditor; la garantía real la aporta la custodia por blobs, no una heurística sobre las muestras.
9. **La resolución del reloj no es observable** por la sonda usada: en 500.000 lecturas no apareció ningún delta nulo, luego el tick es más fino que el coste de lectura (≈124 ns). La sonda caracteriza el coste de leer, no la granularidad.
10. **La corrida no es reproducible bit a bit.** Lo son el procedimiento, las fórmulas, los blobs y los criterios. Una repetición produce **una observación nueva del mismo entorno**; conformidad no significa repetir cifras idénticas, sino superar los controles internos e interpretarse contra la banda publicada.
11. **El esquema congelado no puede validar por sí solo los blobs preinscritos publicados** — hallazgo de la auditoría adversarial de esta fase, verificado: alterar uno de los seis blobs en la sección `preinscripcion` de un artefacto **no** produce fallo en `fallos_suelo_medicion`. **La causa es autorreferencia y es inevitable:** `schema_floor_v0_1.py` es uno de los seis ficheros preinscritos, así que no puede contener el blob de sí mismo sin cambiar su propio blob. Por eso el esquema sí lleva constantes para el protocolo aprobado y para los siete blobs del corpus congelado —externos a él— pero solo rutas para los preinscritos.

    **La detección real existe, fuera del esquema, y se ha ejercitado:** `verificar_custodia` compara el árbol contra lo que registra el commit A vía `git rev-parse <A>:<ruta>`, y se comprobó que alterar `run_floor.py` produce el fallo «blob preinscrito difiere del commit de preinscripción». Además, la verificación independiente del §8 contrastó los **seis blobs publicados** directamente contra `git`: 6 de 6 coinciden. Un auditor de este artefacto debe repetir esa comparación contra `git`, porque **el esquema por sí solo no la cubre**.

---

## 10. Estado de `ADR002-TOL-209`

> ### **NO SATISFECHA**

Existen por primera vez `SM`, `B50`, `B95`, `B` y `U` **observados** bajo el protocolo aprobado, con custodia verificada y los doce controles en verde. **Eso no aprueba la puerta.**

Conforme a la decisión 6 del paquete, que debe quedar explícita: **aprobación documental y aplicabilidad completa no son equivalentes**, y **la satisfacción de `ADR002-TOL-209` requiere un acta de aprobación explícita del usuario que este informe no constituye ni sustituye**. Hasta esa acta:

- `ADR002-TOL-209` sigue **NO SATISFECHA**;
- `ADR002-TOL-208` global sigue **NO SATISFECHA**;
- `ADR002-TOL-210` sigue **NO SATISFECHA**;
- el **límite duro de `TOL-107`** sigue sin fijarse, y `B` **no** puede reutilizarse como techo;
- el benchmark continúa **bloqueado**;
- el PR #117 continúa **sin fusionar**.

---

**Siguiente movimiento único:** auditoría independiente de este commit de evidencia y decisión del usuario sobre el §5 —si el régimen resultante para la capa FTS5 es aceptable— antes de cualquier acta. Nada de eso queda autorizado por este informe.
