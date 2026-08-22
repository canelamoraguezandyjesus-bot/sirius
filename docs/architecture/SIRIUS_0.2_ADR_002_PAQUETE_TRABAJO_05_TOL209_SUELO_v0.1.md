# SIRIUS 0.2 — ADR-002 · Paquete de trabajo 05 · Preinscripción del suelo de medición

**Versión:** 0.1
**Estado:** **PROPUESTO · PREINSCRIPCIÓN** · no aprueba nada y no autoriza medir
**Fecha:** 29 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Exigido por:** `ADR002-TOL-209` del `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md`
**Protocolo que aplica:** `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md`, aprobado por `SIRIUS_0.2_ADR_002_REGISTRO_TOLERANCIAS_APROBACION_v1.0.md` §1 punto 2, blob `c298a6b804309a78062f79b6341adfea2374ce56`

**No autoriza:** ejecutar la medición · generar evidencia · producir el JSON de resultados · producir el informe de resultados · aprobar `ADR002-TOL-209` · crear acta · ejecutar T0 · implementar o ejecutar `ADR002-A/B/C/D` · iniciar el benchmark · fusionar el PR #117.

---

## 0. Objeto

Congelar, **antes de medir**, todo lo que decide el resultado: decisiones normativas, composición de sondas, fórmulas, controles ambientales, criterios de invalidez, esquema de evidencia, reglas de custodia, matriz bloqueante y pruebas negativas.

Este paquete **no contiene ninguna observación temporal real**. Ese es su propósito: que el commit que fija las reglas sea anterior y verificable frente al commit que aporta las cifras.

### 0.1 Por qué dos commits

El precedente del repositorio lo justifica sin necesidad de invocar ningún defecto. `ADR002-TOL-207` se materializó en `ea66cea` con **once ficheros en un solo commit** —código de sondas, esquema, validador, pruebas, paquete de trabajo, evidencia medida e informe—. Con esa forma, **ningún auditor puede distinguir qué código produjo qué cifra**: la ordenación temporal entre reglas y observaciones no queda registrada.

**Constancia expresa, para que no se propague una afirmación no demostrada:** el commit `dab27dd` (cierre del bloqueante B-1) modificó exclusivamente `experiments/adr002/storage/storage_accounting.py` y `experiments/adr002/storage/test_storage_gate.py`. El artefacto `artifacts/adr002_storage/entorno_lab_v0.1.json` lo genera `environment_capture.py::construir_documento()`, que **no fue tocado**, y ese JSON **no contiene ninguna salida de contabilidad de picos** —lo confirma el §4 corrección 4 del acta de TOL-207—. **Las cifras de TOL-207 no están contaminadas por B-1 y este paquete no reabre TOL-207.** La separación en dos commits es un endurecimiento estructural de trazabilidad, no la corrección de una infracción.

Ninguna regla aprobada exige dos commits: la regla dura 1 del §9 del Registro prohíbe fijar valores «después de observar el resultado **del candidato**», y la corrida de suelo no es un candidato. La separación se adopta porque es **el único mecanismo que hace auditable la afirmación**, y así se declara.

---

## 1. Decisiones normativas 1–8

### Decisión 1 · RED-032 y RED-033 quedan fuera

`RED-032` (tolerancias de texto, estado, conteo y tiempo de `RF-26`) y `RED-033` (clase de equivalencia de orden) **no pertenecen al cierre de TOL-209**.

- La `SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.3_PROPUESTO.md` §12.1 se los imputa, pero **no está aprobada**: no figura entre los cuatro artefactos del acta de aprobación v1.0 §1.
- La fila vinculante de TOL-209 (Registro v0.4 §7) **no los menciona** en su *Contenido mínimo*.
- El Registro imputa las tolerancias de `RF-26` a **`ADR002-TOL-201`** (línea 518, «Dependencia declarada (v0.4)»), y el hallazgo **m-03** las registra como dependencia de TOL-201.
- `TOL-201` es `REGLA_CONFIRMADA_VALOR_CANDIDATO`: **se congela con cada candidato**, en su ficha, antes de ejecutarlo.

**Dependencia registrada, con propietario explícito:** cerrar TOL-209 **no hace adjudicables por sí solo `CA-37`, `CA-39` ni `CA-48`**. Su desbloqueo pertenece al trabajo de `ADR002-TOL-201` y `ADR002-TOL-210`, sobre las fuentes canónicas ya materializadas por `SRC-ADR002-01`. **Este paquete no intenta resolverlo.**

### Decisión 2 · Sonda de reloj

- **100.000 lecturas consecutivas por proceso**, con **1.000 lecturas iniciales de warm-up descartadas**.
- Caracteriza **resolución efectiva y granularidad**. No se usa como presupuesto principal de ruido.
- **Se declara**: el bucle cerrado representa el **mejor caso** —caché caliente, sin expropiación— y por tanto **puede subestimar el coste real de leer el reloj**.
- Es una **desviación al alza declarada** respecto del mínimo de 100 repeticiones del §3.2 del protocolo, comunicada de antemano conforme al §7 punto 4.

### Decisión 3 · Margen

**`m = 1`.** No existe multiplicador adicional.

Es el **único** valor que conserva continuidad exacta entre regímenes en `M = U`: allí el permiso relativo vale `0,20 × 5B = B` y el absoluto vale `m × B`. Con `m ≠ 1` aparece un escalón en la frontera, y un escalón es un incentivo explotable.

### Decisión 4 · Sin regla antijuego nueva

**No se añade ninguna regla normativa nueva.** La dispersión absoluta se publica **siempre** como diagnóstico. Los límites propios de cada candidato pertenecen a `ADR002-TOL-102C`, `ADR002-TOL-202` y `ADR002-TOL-210`, que obligan a congelarlos en la ficha **antes** de la primera ejecución.

### Decisión 5 · Sesgo residual, registrado como limitación conocida

Por encima de `U`, un criterio relativo del 20 % resulta **mecánicamente más permisivo en términos absolutos para operaciones más lentas**: con el mismo jitter absoluto, un `mín` mayor produce un cociente menor.

Ese sesgo vive en el ≤20 % **ya congelado** por el Registro v0.4 (línea 476). **No se reabre.** Se declara.

### Decisión 6 · Lectura operativa de TOL-209

Se registra expresamente:

- el documento de protocolo v0.1 **ya está aprobado** (acta v1.0 §1 punto 2 y §2);
- **`ADR002-TOL-209` sigue NO SATISFECHA** mientras no existan `U` y `B` aplicables;
- **aprobación documental y aplicabilidad completa no son equivalentes**: el §6.4 del propio protocolo aprobado declara que no fija ese número;
- **esta interpretación deberá quedar explícita en el futuro acta**, no implícita, para que una auditoría posterior no pueda reabrirla alegando que la fila vinculante solo exige el documento.

### Decisión 7 · Sin techo histórico para `B`

- **No se usa `0,0661 ms` ni ninguna cifra histórica de FTS5 como límite.** Las cifras históricas son **contraste diagnóstico**.
- `B` se acepta o rechaza **exclusivamente mediante los controles internos preinscritos** del §6.
- Si `B` resulta alta con **todos** los controles válidos, **representa el suelo observado del entorno**.
- **Prohibido reducirla** para obtener una clasificación de régimen más conveniente.
- La posible **inercia solo puede verificarse durante la rederivación de T0** (`ADR002-TOL-208` paso 2), porque depende de las magnitudes que el benchmark vaya a comparar y esas no existen todavía.
- Si ninguna magnitud de T0 alcanza `U`, se permite **una única repetición controlada** (§6.5 del protocolo). Si vuelve a ocurrir, el entorno queda **`NO EVALUABLE`**; **nunca se rebaja `B`**.

Motivos por los que el techo histórico habría sido incorrecto: procede de sesiones **secuenciales intra-proceso**; **sin registro de carga ni throttling**; **sin muestras crudas**; con agregados **redondeados a cuatro decimales de milisegundo**; mide **una consulta FTS5 real**, no el instrumento; y la nueva corrida usa **procesos independientes** y registro en nanosegundos. Además, una corrida inter-proceso debe dispersar **más** que una intra-proceso, porque añade ruido de proceso: usar la cifra intra-proceso como techo **sesga sistemáticamente hacia el rechazo falso**. Por último, fundar la validez de la puerta en una cifra del sustrato léxico colisiona con la regla de neutralidad del §5.6 del Registro.

### Decisión 8 · Composición normativa de `F`

```
F = { D_vacia , SQLite_0_filas , SQLite_1_fila }
```

`F` **no puede contener**: FTS5 · `rank()` · busy-spin · lecturas consecutivas del reloj · sobrecoste del puerto · ninguna operación propia de `ADR002-A/B/C/D`.

**Solo `F` deriva `SM`, `B50`, `B95`, `B` y `U`.** Ningún diagnóstico los modifica.

---

## 2. Definición exacta de las sondas

### 2.1 Tabla canónica elegida

Tras inspeccionar el repositorio se elige **`memory_revisions`**, con clave primaria **`id`**.

Fundamento:

- es el **canon de ADR-001**: la reconstrucción obligatoria se hace *desde* esta tabla, y todo derivado es regenerable y no autoritativo;
- su clave primaria `id` la crea la cadena canónica de Alembic (`4022f15cc8df_create_memories_and_memory_revisions`) como `INTEGER` autoincremental: **el índice lo aporta SQLite**, no lo elige ninguna arquitectura candidata;
- **no es tabla FTS ni tabla sombra**;
- SQLite es el sustrato común ratificado por ADR-001 alternativa A, compartido por T0 y por los cuatro candidatos.

### 2.2 SQL de las sondas normativas

```sql
SELECT id FROM memory_revisions WHERE id = ?
```

- **`SQLite_0_filas`**: valor de clave que **no casa con ninguna fila** → resultado de cero filas.
- **`SQLite_1_fila`**: valor de clave que casa con **exactamente una fila** → resultado de una fila.

**Prohibido en ambas**, y comprobado por guarda ejecutable: `LIKE` · `MATCH` · tablas FTS · tablas sombra (`_content`, `_data`, `_idx`, `_docsize`, `_config`) · `JOIN` · `ORDER BY` · `GROUP BY` · agregaciones (`count`, `sum`, `avg`, `min`, `max`, `total`, `group_concat`) · funciones de ranking (`rank`, `bm25`) · cualquier estructura que dependa de un candidato.

**Fuera de la ventana cronometrada:** preparación del fixture, apertura de la conexión, DDL y selección de las claves (§2.2 del protocolo). El DDL procede de la cadena canónica de Alembic y nunca se escribe a mano (§2.5).

### 2.3 `D_vacía`

Corchete completo del arnés sobre un invocable vacío: llamada Python, dos lecturas de reloj y registro. Es la **distribución** del instrumento, no un escalar.

### 2.4 Sondas diagnósticas, fuera de `F`

| Diagnóstico | Para qué sirve |
|---|---|
| Lecturas consecutivas del reloj | Resolución efectiva y granularidad (decisión 2) |
| Busy-spin calibrado | Throttling y deriva; se reejecuta al inicio, mitad y final de cada proceso |
| Comprobación 1×/2× | **Valida el instrumento**; no define el cambio de régimen |
| Sobrecoste del puerto común | Coste del puerto equivalente a `KnowledgeSearchRepository`. Queda fuera de `F` porque incorporarlo elevaría `B` y `U` —empujando más magnitudes al régimen absoluto— y porque el puerto actual resuelve sobre FTS5 |

Las magnitudes históricas de FTS5 y `rank()` **se clasifican después como diagnóstico** usando su evidencia versionada (`mediciones_linea_base_v0.2.json`). **No se vuelven a medir en esta fase.** **Ningún diagnóstico puede modificar `B` ni `U`.**

---

## 3. Fórmulas vinculantes

Todo en **nanosegundos**. Percentiles **nearest-rank**, nunca interpolados. `S` = conjunto de procesos independientes, `|S| ≥ 5`. `F` = las tres sondas normativas.

```
SM  = máximo, sobre X en F y s en S, de P95(X, s)

B50 = máximo, sobre X en F y pares s,s' en S, de |P50(X,s) − P50(X,s')|

B95 = máximo, sobre X en F y pares s,s' en S, de |P95(X,s) − P95(X,s')|

B   = max(B50, B95)

U   = B / 0,20 = 5 × B

m   = 1
```

**`SM`** es el nivel máximo del instrumento y sirve **únicamente** como guarda de dominancia. **No define `U`.**

**No se permite**: redondeo previo · conversión temprana a milisegundos · interpolación · ajuste de `B` · multiplicador configurable · búsqueda de un `k_U` · uso de FTS5 para derivar `B` o `U`.

El criterio relativo se evalúa en **aritmética entera exacta** —`5 × (máx − mín) ≤ mín`— para que ningún resultado dependa de la representación binaria de un `float`.

### 3.1 Constantes operativas preinscritas

Fijadas en `floor_protocol.py` antes de medir; cambiarlas obliga a nueva versión del paquete y a repetir lo ejecutado bajo la anterior:

| Constante | Valor | Para qué |
|---|---|---|
| `RONDAS_ROUND_ROBIN` | `10` | Cada proceso reparte las `n = 100` repeticiones de cada sonda de `F` en 10 rondas intercaladas (tramos de 10), nunca en bloque |
| `VUELTAS_BUSY_SPIN` | `10.000` | Trabajo fijo y declarado del busy-spin de diagnóstico |
| `TOLERANCIA_DUPLICACION` | `3/10` | Comprobación 1×/2×: `|p50_2x − 2·p50_1x| × 10 ≤ 2·p50_1x × 3` |
| `TOLERANCIA_DERIVA` | `3/10` | Deriva del busy-spin: inestable si el P50 crece de forma **estrictamente monótona** entre inicio, mitad y final **y** `(final − inicio) × 10 > inicio × 3` |

La **media** exigida por el §7 punto 6 del protocolo se publica como `media_truncada_ns`: suma entera dividida (división entera) entre `n`. Truncada y declarada así para no introducir coma flotante en la cadena normativa.

---

## 4. Orden de evaluación y régimen por percentil

La guarda `SM` **se evalúa antes** de seleccionar régimen. Si se evaluase después, una magnitud dominada por el instrumento podría clasificarse y publicarse como latencia antes de que la guarda actuase.

```
Para una magnitud con sesiones S:

  PASO 1 · guarda de dominancia
     si min_s P95(s) < SM:
        no produce afirmación de latencia
        resultado NO_EVALUABLE para esa magnitud
        no se selecciona régimen

  PASO 2 · régimen por percentil, para cada p en {P50, P95}
     si min_s p(s) >= U  →  RELATIVO
     si min_s p(s) <  U  →  ABSOLUTO

  PASO 3 · criterios
     RELATIVO pasa si  (max_s p − min_s p) / min_s p <= 0,20
     ABSOLUTO pasa si  (max_s p − min_s p) <= B

  PASO 4 · veredicto
     válida únicamente si P50 y P95 pasan, cada uno en su régimen
```

### 4.1 Invariante

Debe verificarse siempre:

```
min_s P95 >= min_s P50
```

Demostración: para toda sesión `s`, `P95(s) ≥ P50(s)`; sea `s₁ = argmín P95`; entonces `min_s P95 = P95(s₁) ≥ P50(s₁) ≥ min_s P50`.

Combinaciones válidas, y solo estas tres:

- P50 absoluto / P95 absoluto;
- P50 absoluto / P95 relativo;
- P50 relativo / P95 relativo.

**P50 relativo / P95 absoluto es imposible y debe invalidar el artefacto.**

### 4.2 Registro por percentil

El resultado se registra en el campo único **`Régimen aplicable`** de la ficha de candidato aprobada como:

```
P50: absoluto · P95: relativo
```

La plantilla **no se modifica** y su blob (`4e9fa861ed6ab22a6b19729ed44066c8d93d863e`) **no cambia**: cada candidato crea su ficha *a partir de* la plantilla, y el `·` del marcador es separador de enumeración, no un valor.

Esto **refina el formato singular del §7 punto 9 del protocolo** («Régimen aplicado: relativo o absoluto») y constituye una **desviación previamente declarada** conforme al §7 punto 4, **no una modificación normativa**.

---

## 5. Desviaciones declaradas de antemano

Conforme al §7 punto 4 del protocolo, que obliga a declarar «toda desviación, declarada de antemano»:

| # | Desviación | Sentido |
|---|---|---|
| D-1 | `n = 100.000` en la sonda de reloj, frente al mínimo de 100 del §3.2 | Al alza. 100 muestras no caracterizan un tick |
| D-2 | Registro de **dos** regímenes, uno por percentil, frente al singular del §7 punto 9 | Estrictamente más informativo; coherente con el §6.1, que opera «sobre el mismo percentil» |
| D-3 | Sesiones materializadas como **procesos del sistema operativo distintos**, no como sesiones intra-proceso | Al alza. Cierra la laguna declarada por el Registro línea 486 |
| D-4 | Vectores crudos persistidos **en nanosegundos sin redondear** | Al alza. El redondeo a cuatro decimales de milisegundo es un cuantizador de 100 ns que destruiría la señal buscada |

---

## 6. Controles internos preinscritos

Todos **bloqueantes**. Falla cerrado: un control ausente cuenta como fallido.

| Control | Qué exige |
|---|---|
| `procesos_independientes` | Al menos cinco procesos del sistema operativo |
| `pids_distintos` | PIDs verificados y distintos entre sí |
| `carga_registrada` | Carga y procesos concurrentes registrados antes, durante y después |
| `boot_id_estable` | `boot_id` idéntico entre captura inicial y final |
| `busy_spin_estable` | Sin aumento monótono del P50 entre inicio, mitad y final |
| `duplicacion_1x_2x` | El tiempo medido escala con el trabajo dentro de la tolerancia preinscrita |
| `vectores_crudos_completos` | Vector íntegro por sonda y proceso, con `n` coherente |
| `sin_filtrado` | Ningún outlier eliminado, recortado ni winsorizado |
| `warmup_separado` | Warm-up ejecutado y descartado íntegro. **Se recomputa** contra el valor preinscrito: un proceso que declare otro número no supera el control, aunque su propio flag afirme lo contrario |
| `sin_redondeo_previo` | Nanosegundos sin redondear |
| `captura_ambiental_presente` | Entorno capturado y adjunto |
| `custodia_verificada` | Cadena A→D del §9 satisfecha |

Si **cualquiera** falla, la corrida **no publica `SM`, `B50`, `B95`, `B` ni `U`**.

### 6.1 Tratamiento de outliers

Nada se recorta, winsoriza ni filtra. Se publica la distribución completa, el vector íntegro y una **lista declarada de excursiones** con su índice, para que un pico de expropiación quede visible y atribuible en lugar de suavizado en silencio.

---

## 7. Criterio de reproducibilidad

**No se usa la etiqueta `ENVOLVENTE_REPRODUCIBLE`.** Es específica de `ADR002-TOL-207` y del almacenamiento: su acta §1.1 la define en términos de huella del entorno, **semántica de asignación del filesystem** y **suelo de admisión**, y `schema_storage_v0_1.py` la fija como constante de ese esquema. No existe autoridad normativa que la generalice a otras puertas.

Se declara, en términos propios:

- los **tiempos no son reproducibles bit a bit**;
- **sí son reproducibles** el procedimiento, las fórmulas, los blobs y los criterios;
- una repetición produce **una observación nueva del mismo entorno**;
- **conformidad no significa repetir cifras idénticas**;
- una reejecución debe **superar los controles internos** y ser **interpretada contra la banda publicada**.

---

## 8. Limitaciones conocidas

1. **Indulgencia compuesta sobre P50.** Como `B95 ≥ B50` casi siempre, en la práctica `B = B95`. P50 recibe entonces una banda más ancha que su propia `B50` **y** un `U` más alto que el derivado de su propia dispersión. Es el coste aceptado de mantener **una única banda compatible con la ficha aprobada**. `B50` se publica para que la magnitud de esa indulgencia sea auditable.
2. **`B` incorpora el comportamiento de caché de páginas y B-tree de SQLite.** Es correcto —es el suelo que todo candidato paga— pero si un candidato futuro usara un almacén distinto, `B` llevaría dentro un sustrato ajeno. ADR-001 lo impide en este benchmark.
3. **`B` hace doble función**: define `U` y es el criterio del régimen absoluto. No es circular, pero una corrida contaminada aflojaría en ambas direcciones a la vez. Por eso los controles internos son bloqueantes y `B` se publica descompuesta por sonda y percentil.
4. **La inercia no es verificable en esta puerta** (decisión 7). La puerta puede cerrarse con una banda que más tarde resulte inerte; el tratamiento es repetición única y `NO EVALUABLE`, **nunca rebajar `B`**.
5. **La composición de `F` determina la clasificación resultante.** Si `F` es mucho más barata y estable que una consulta FTS5 real, `B` saldrá pequeño, `U` saldrá pequeño y parte de la capa FTS5 podría caer en régimen relativo, donde el Registro dice que no debe caer. **Ese riesgo queda aceptado y divulgado, no eliminado**: que no se reproduzca la clasificación histórica **debe explicarse, no corregirse a posteriori**.
6. **Sigue siendo una sola máquina y un solo sistema operativo.** La corrida medirá por primera vez el ruido entre procesos, lo que **reduce pero no elimina** la laguna que motiva no fijar el límite duro de TOL-107.
7. **El sesgo residual del ≤20 % por encima de `U`** permanece (decisión 5).
8. **El filtrado silencioso de un proceso no es detectable con certeza.** Un worker que recortara la cola y repadease el vector produciría muestras indistinguibles de un suelo cuantizado por la resolución del reloj: un vector es un vector. Se recomputa todo lo que **sí** es comprobable —longitud, tipos, signo, warm-up contra el preinscrito, percentiles nearest-rank, derivación completa— y se **publica la forma del vector** (`valores_distintos`, `repeticion_maxima`) por sonda y proceso, para que un auditor lo evalúe. **Deliberadamente no se convierte en umbral automático**: cualquier corte elegido daría falsos positivos sobre un suelo legítimamente cuantizado, y el §6.4 del protocolo prohíbe inventar cifras. La garantía real de que el worker es el preinscrito la aporta la custodia por blobs del §9.3, no una heurística sobre las muestras.

---

## 9. Custodia A → D

El artefacto de la fase D debe registrar el SHA del commit A, el blob de cada uno de los seis ficheros preinscritos, el blob de `harness.py`, el blob del protocolo aprobado y los siete blobs del corpus congelado.

La comprobación ejecutable, reutilizable y probada ya en esta fase con dobles controlados, verifica en este orden:

1. lee `SHA_A` desde el JSON;
2. verifica que `SHA_A` **es ancestro de HEAD**;
3. recalcula los blobs de los **seis ficheros preinscritos**;
4. los compara con los blobs registrados;
5. verifica el blob de **`harness.py`**;
6. verifica los **siete blobs congelados**;
7. ejecuta el equivalente a `git diff --exit-code SHA_A..HEAD -- <seis ficheros preinscritos>`;
8. **falla si existe cualquier modificación**.

Sin los pasos 3 a 8, los dos commits darían ordenación temporal pero **no integridad**.

### 9.1 Precondiciones de la ejecución futura

`run_floor.py` **no ejecuta nada al importarse** y **no mide sin `--execute`** — la guarda cubre también al worker interno. La medición exige además `--preinscription-commit <SHA_A>` y `--output <ruta>`, y antes de abrir cualquier ventana comprueba: árbol de trabajo limpio · `HEAD` exactamente igual a `SHA_A` · `SHA_A` existente · los seis blobs coincidentes con el árbol · protocolo aprobado intacto · blobs congelados intactos · ruta de salida inexistente.

La ejecución rechaza además, fallando cerrado y sin publicar valor alguno: menos de cinco PIDs distintos · árbol sucio · HEAD distinto · cambio de código preinscrito · salida existente · warm-up mezclado · vectores incompletos · redondeo previo · ausencia de captura ambiental.

### 9.2 Recorrido implementado de la fase D

El recorrido completo queda **implementado y congelado en esta preinscripción**, de modo que la fase D pueda producir el JSON válido **sin volver a modificar el código**:

```
precondiciones (custodia y entorno)
→ captura ambiental inicial
→ lanzamiento de ≥5 procesos independientes del sistema operativo
   (cada uno: base propia construida con la cadena canónica de Alembic,
    corpus propio, warm-up propio, sondas de F en round-robin por rondas,
    reloj, busy-spin inicio/mitad/final, comprobación 1×/2×, puerto)
→ captura ambiental final
→ verificación de forma de cada resultado
→ evaluación de los doce controles bloqueantes DESDE los datos crudos
   (los flags que declara cada proceso se cruzan, nunca se aceptan solos)
→ derivación: SM, B50, B95, B = max(B50,B95), U = 5×B, m = 1
→ clasificación diagnóstica de la línea base versionada
→ construcción del documento completo
→ validación con schema_floor_v0_1
→ escritura ATÓMICA (fichero temporal en el mismo directorio + fsync + rename)
→ relectura del JSON escrito y REVALIDACIÓN con el mismo esquema
```

Si cualquier paso falla, **no queda ningún artefacto**: la validación previa impide escribir, y una revalidación fallida elimina el fichero. La escritura atómica garantiza que nunca exista un JSON parcial.

Las dependencias externas —custodia Git, ejecutor de procesos, captura de entorno, carga de la línea base— son **inyectables** (`DependenciasCorrida`): la prueba extremo a extremo de `test_adr002_floor.py` recorre este mismo camino de producción con dobles controlados, sin ejecutar la medición real. El ejecutor real lanza cada proceso hijo con `--execute --worker`; el worker mide y devuelve su resultado por stdout, **no escribe ningún artefacto**.

**Decisión técnica declarada:** todo el recorrido vive en `run_floor.py` para no ampliar el conjunto de seis ficheros preinscritos ni la custodia que los protege.

### 9.3 Custodia reverificada tras medir

La custodia **no se comprueba solo antes de medir**. Entre la medición y la publicación se repite íntegra: árbol limpio, `HEAD` igual a `SHA_A`, blobs de los seis ficheros y del corpus congelado, protocolo intacto. Su resultado alimenta el control bloqueante `custodia_verificada`, de modo que un `HEAD` movido, un árbol ensuciado o un blob alterado **durante** la corrida impiden publicar.

El esquema lo hace cumplir de forma independiente: exige `custodia.reverificada_tras_medir` y compara `custodia.head` y `preinscripcion.head_en_ejecucion` contra `preinscripcion.commit_a`. Un artefacto cuyo `HEAD` de publicación no sea el commit de preinscripción es inválido, porque el código medido no sería el preinscrito.

**La comparación de blobs no es tautológica.** El árbol de trabajo se compara contra **lo que el commit `SHA_A` registra** para cada ruta (`git rev-parse <SHA_A>:<ruta>`), no contra un blob recalculado del mismo árbol. Sin esa fuente de verdad independiente, leer el árbol y compararlo consigo mismo coincidiría siempre y no detectaría ninguna alteración. Una ruta que el commit de preinscripción no registre también es fallo.

### 9.4 Publicación sin sobrescribir ni destruir

La escritura usa `os.link` en lugar de `os.replace`: si la ruta de salida apareciese entre la precondición «salida inexistente» y la publicación, `link` falla con `FileExistsError` en vez de destruir el fichero existente.

Y la limpieza **solo puede alcanzar un fichero que esta corrida haya creado**. Escritura y relectura están separadas: si `link` rehúsa, se bloquea **sin tocar nada**; el borrado de limpieza únicamente actúa tras un `link` exitoso, cuando la revalidación no respalda lo escrito. Cerrar la ventana TOCTOU no puede convertirse en «destruir en silencio» lo que se acababa de proteger. La serialización usa `allow_nan=False`: `NaN` e `Infinity` no son JSON estándar y no entran en evidencia normativa.

### 9.5 Recomputación obligatoria, tipos y validador total

El validador **recomputa** `SM`, `B50`, `B95`, `B`, `U` y la descomposición desde las propias sondas publicadas. Si las sondas no permiten recomputar —campo ausente o de tipo manipulado— eso **no es conformidad, es fallo**: el artefacto no puede publicar derivación. Los campos normativos (`pid`, `n`, warm-up, percentiles, mínimo, máximo, media truncada) se validan como enteros **antes** de usarlos, y todo control bloqueante debe ser exactamente `True`; un `0`, `None` o cadena vacía cuenta como fallido.

**`fallos_suelo_medicion` es total por contrato: nunca lanza.** Un validador que lanzase ante un valor JSON legal —`NaN`, cadena donde se espera entero, lista donde se espera objeto— dejaría de ser una guarda: quien lo invoca no obtendría veredicto y un artefacto manipulado podría quedar sin evaluar. Cualquier fallo interno inesperado se convierte en un fallo de validación explícito.

Toda dependencia externa del recorrido —custodia, captura de entorno, ejecutor, línea base, escritura, relectura— se invoca dentro de una guarda. Una excepción nunca escapa de `main` como traza: siempre se convierte en `CODIGO_BLOQUEADO` con su motivo.

### 9.6 El régimen publicado se recomputa; `NO_EVALUABLE` no es comodín

El régimen declarado para cada percentil **no se acepta**: se recomputa aplicando `U` a los mínimos publicados. Un régimen que no salga de esa regla invalida el artefacto — sin esta comprobación bastaba con declarar el régimen conveniente.

La **guarda `SM` se verifica también a nivel de artefacto**: una magnitud cuyo `mín P95` quede por debajo de `SM` está obligada a declararse `NO_EVALUABLE`, y una que se declare `NO_EVALUABLE` sin estar por debajo de `SM` es inválida. Y `NO_EVALUABLE` **no exime de nada**: el invariante `mín P95 ≥ mín P50` y la prohibición de publicar régimen se comprueban igualmente, porque el §4.1 es incondicional.

### 9.7 Otras guardas de fallo cerrado

| Guarda | Motivo |
|---|---|
| **Muestras no negativas** | Una duración medida con reloj monotónico no puede ser negativa: si lo es, el reloj retrocedió o el vector se manipuló |
| **Incidencias bloqueantes** | Una incidencia observada por la propia corrida —por ejemplo una sonda SQLite que no devolvió la forma declarada— **impide publicar `B` y `U`**. Registrarla como nota informativa sería fail-open contra el §2.2 y la condición 40 de la matriz |
| **`custodia.head` y `head_en_ejecucion` obligatorios** | Un valor ausente o nulo no puede ser más permisivo que un valor distinto: sin ellos el artefacto no queda ligado al commit preinscrito |
| **Identidad por igualdad estricta** | `version_esquema`, `protocolo` y `blob_protocolo` se comparan con igualdad, no con «ausente o igual». Publicar `null` no absuelve: la clave existe, así que la comprobación de secciones no la ve ausente |
| **Veredicto no vaciable** | `regimenes_por_percentil` debe tener al menos una entrada, y `clasificacion_diagnostica_linea_base.magnitudes` debe ser una lista no vacía. Vaciarlas borraría la divulgación que exige la condición 38 sin dejar rastro |
| **Warm-up coherente con el plan** | Una sonda de `F` debe declarar exactamente el warm-up preinscrito. Un artefacto que declare otro se contradice con su propio `plan` |
| **Residuos denunciados, nunca silenciados** | Todo borrado de limpieza —temporal de escritura, artefacto retirado por revalidación fallida— **verifica el estado del disco**. Si el fichero sobrevive, se informa explícitamente en lugar de seguir afirmando que no se publicó nada: un residuo con JSON válido y valores derivados sería evidencia publicada por una corrida que se declara bloqueada |

**Ordinal del percentil sin coma flotante.** `resolucion_percentil` deriva el ordinal con la misma aritmética entera de techo que `percentil_ns`. Con `floor(0.99 × n)` había un off-by-one para todo `n` múltiplo de 100 —precisamente los tamaños preinscritos—, y el artefacto afirmaba que su P99 era el máximo observado cuando era la segunda peor muestra.

---

## 10. Alcance de los commits

### 10.1 Commit A — este paquete

| Ruta |
|---|
| `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_05_TOL209_SUELO_v0.1.md` |
| `experiments/adr002/tolerances/floor_probes.py` |
| `experiments/adr002/tolerances/floor_protocol.py` |
| `experiments/adr002/tolerances/run_floor.py` |
| `experiments/adr002/tolerances/schema_floor_v0_1.py` |
| `experiments/adr002/tolerances/test_adr002_floor.py` |

**Cero evidencia medida · cero informe de resultados · cero acta · cero modificaciones de ficheros existentes.**

### 10.2 Commit D — futuro, no autorizado por este paquete

| Ruta |
|---|
| `artifacts/adr002_tolerances/suelo_medicion_v0.1.json` |
| `artifacts/adr002_tolerances/INFORME_SUELO_MEDICION_v0.1_PROPUESTO.md` |

**Cero cambios en cualquier fichero del commit A.**

Entre A y D se interpone una **auditoría independiente del commit A**.

---

## 11. Matriz bloqueante

Transcrita íntegra desde la auditoría aprobada. Ninguna condición ha sido añadida, retirada ni reinterpretada.

> **Corrección de recuento, no de contenido.** La auditoría anterior etiquetó esta matriz como «42 condiciones». El recuento correcto es **44**: 24 de la primera ronda (con 18 y 21 sustituidas por 18′ y 21′), más 11 de la segunda (25–35), más 9 de la tercera (36–44), con 33 sustituida por 33′. El error era aritmético en la etiqueta del total; **el contenido de la matriz es exactamente el aprobado**.

| # | Condición bloqueante |
|---|---|
| 1 | Valores publicados sin evidencia versionada |
| 2 | Fórmula fijada, alterada o afinada después de medir |
| 3 | Menos de cinco sesiones |
| 4 | Percentil interpolado en cualquier cifra |
| 5 | Warm-up mezclado con las muestras |
| 6 | Fixtures dentro del cronómetro |
| 7 | Arnés dominante sin declarar |
| 8 | Carga o throttling no registrados |
| 9 | Comparación entre procesos o máquinas no declarada |
| 10 | Umbral que premie añadir latencia |
| 11 | Banda absoluta menor que el ruido demostrado |
| 12 | Banda tan amplia que vuelva inerte TOL-107 |
| 13 | Cifras no vinculadas a entorno, commit y protocolo |
| 14 | Valores modificados tras resultados de candidatos |
| 15 | Sesiones en un único proceso del sistema operativo |
| 16 | Muestras crudas ausentes, vacías o redondeadas antes de persistirse |
| 17 | Outlier eliminado, recortado o winsorizado |
| 18′ | Umbral fundado en algo distinto de `U = B / 0,20`, o `B` derivado de otra cosa que la dispersión absoluta entre sesiones de `F` |
| 19 | Banda derivada con la fórmula relativa en vez de la absoluta |
| 20 | Límite duro de TOL-107 fijado en este cierre, o `B` reutilizado como techo |
| 21′ | Comprobación de duplicación omitida, o corrida publicada pese a fallarla (validez del instrumento, no definición de régimen) |
| 22 | Magnitud con `P95 < SM` publicada como latencia en vez de dominada por el instrumento |
| 23 | Modificación de cualquier blob aprobado o congelado |
| 24 | Preinscripción posterior al commit de la corrida |
| 25 | Margen `m ≠ 1` sin demostrar continuidad en `M = U` |
| 26 | Régimen asignado a la magnitud en bloque en vez de por percentil |
| 27 | Régimen seleccionado con `máx`, media o mediana en lugar de `mín_s` |
| 28 | Artefacto que viole `mín_s P95 ≥ mín_s P50` |
| 29 | Dos bandas normativas separadas, o banda que no quepa en el campo único de la ficha aprobada |
| 30 | Commit de evidencia que modifique cualquier fichero preinscrito, o que no registre commit y blobs de preinscripción |
| 31 | Matriz bloqueante o constantes que aparezcan por primera vez en el commit de evidencia |
| 32 | Magnitud con `mín_s P95 < SM` evaluada en cualquier régimen en vez de declararse sin afirmación de latencia |
| 33′ | Corrida publicada con cualquier control interno preinscrito inválido — sesiones no independientes, carga o throttling sin registrar, busy-spin inestable, 1×/2× fallida, muestras crudas incompletas, filtrado presente, warm-up mezclado |
| 34 | Composición de `F` no declarada, o alterada entre preinscripción y ejecución |
| 35 | Régimen por percentil no registrado como desviación del §7 punto 9 |
| 36 | `B` reducido, recortado o ajustado por producir una clasificación de régimen inesperada |
| 37 | `B` publicado sin descomposición por sonda y por percentil |
| 38 | Clasificación de régimen diagnóstica de la línea base ausente del artefacto |
| 39 | Guarda `SM` evaluada después de la selección de régimen |
| 40 | Sonda SQLite que use `LIKE`, `MATCH`, tabla FTS o sombra, `JOIN`, `ORDER BY` o agregación, o que no consulte por clave primaria sobre tabla canónica |
| 41 | Sobrecoste del puerto incorporado a `F` en lugar de publicarse como diagnóstico |
| 42 | Uso de la etiqueta `ENVOLVENTE_REPRODUCIBLE` o de cualquier clasificación formal de TOL-207 sin autoridad que la generalice |
| 43 | Blobs del corpus congelado o de `harness.py` ausentes del JSON |
| 44 | Validación de custodia `git diff A..D` no ejecutable como prueba |

**Categorías no bloqueantes** (se registran, no detienen): correcciones de redacción del informe; endurecimientos opcionales del validador; sondas adicionales que no alteren `F`.

---

## 12. Pruebas negativas

`experiments/adr002/tolerances/test_adr002_floor.py` cubre, con datos sintéticos y dobles controlados y **sin ejecutar la corrida real**:

nearest-rank sin interpolación · `SM`, `B50`, `B95`, `B` y `U` exactos · `m` fijo igual a 1 · continuidad en `U` · `F` con exactamente tres sondas · diagnósticos excluidos de `F` · SQL permitido por clave primaria · rechazo de `LIKE`, `MATCH`, FTS, sombras, `JOIN`, `ORDER BY` y agregación · menos de cinco procesos · PIDs repetidos · warm-up mezclado · muestras redondeadas · muestras filtradas o `n` incoherente · ausencia de carga o entorno · cambio de `boot_id` · control busy-spin fallido · comprobación 1×/2× fallida · guarda `SM` anterior al régimen · régimen separado para P50 y P95 · invariante `mín P95 ≥ mín P50` · combinación P50 relativo / P95 absoluto rechazada · `B` única con diagnóstico `B50`/`B95` · `U` distinta de `5B` rechazada · `B` ajustada por clasificación histórica rechazada · FTS5 nunca afecta `B` ni `U` · puerto fuera de `F` · excepción → `NO_EVALUABLE` · control bloqueante → ningún valor publicado · commit de preinscripción inexistente · `SHA_A` no ancestro · blob preinscrito alterado · `harness.py` alterado · blob congelado alterado · diff A..D no vacío · importación sin efectos secundarios · ejecución sin `--execute` rechazada · árbol sucio rechazado · salida existente rechazada.

Y además, la **prueba extremo a extremo sintética** del §9.2: `main() --execute` con dependencias inyectadas recorre el camino de producción completo —precondiciones, ejecutor, sondas, controles, derivación, documento, validación, escritura atómica, relectura y revalidación— y produce un JSON que el esquema valida sin fallos; sus variantes negativas comprueban que cuatro procesos, PIDs repetidos, duplicación fallida, deriva monótona del busy-spin, cambio de `boot_id`, vector redondeado, vector incompleto, resultado sin clave obligatoria, ejecutor que lanza o salida existente **bloquean sin escribir nada**, y que con árbol sucio **el ejecutor ni siquiera llega a invocarse**. La derivación publicada se recomputa además **desde las propias sondas publicadas** dentro del validador: una derivación incoherente con sus vectores invalida el artefacto.

**No se crean snapshots temporales dentro del repositorio.**

---

## 13. Qué desbloquea y qué no

**Desbloquea:** la posibilidad de someter el commit A a **auditoría independiente**, y —solo si esa auditoría lo autoriza expresamente— la ejecución de la fase D sobre este código exacto y sin modificarlo.

**No desbloquea:**

- `ADR002-TOL-209` sigue **NO SATISFECHA**: no existen `U` ni `B` observados;
- `ADR002-TOL-208` global sigue **NO SATISFECHA**;
- `ADR002-TOL-210` sigue **NO SATISFECHA**;
- `CA-37`, `CA-39` y `CA-48` **no** pasan a ser adjudicables (decisión 1);
- el **límite duro de TOL-107** sigue sin fijarse y **no se fija aquí**: su punto de congelación es «con el entorno de ejecución» (Registro §9), y `B` **no** puede reutilizarse como techo.

---

## 14. Prohibiciones

1. **No** ejecutar la medición ni generar evidencia.
2. **No** ejecutar T0.
3. **No** implementar ni ejecutar `ADR002-A/B/C/D`.
4. **No** iniciar el benchmark.
5. **No** aprobar `ADR002-TOL-209` ni crear acta.
6. **No** modificar Sirius 0.1 (`src/`, `tests/`, `migrations/`, configuración productiva).
7. **No** modificar ningún blob aprobado o congelado, ni el protocolo, ni la plantilla de ficha.
8. **No** abrir otro PR ni fusionar el PR #117.

---

**Siguiente movimiento único:** auditoría independiente de este commit A. Ninguna medición está autorizada hasta que esa auditoría se pronuncie y el usuario lo autorice expresamente.
