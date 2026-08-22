# SIRIUS 0.2 — Registro de Tolerancias

**Versión:** 0.1
**Estado:** **PROPUESTO** · este Registro **no está aprobado** y no autoriza nada por sí mismo
**Fecha:** 25 de julio de 2026
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02_TOLERANCIAS_Y_MEDICION_v0.1.md`
**Evidencia:** `artifacts/adr002_tolerances/mediciones_linea_base.json` · `artifacts/adr002_tolerances/INFORME_MEDICION_TOLERANCIAS_v0.1_PROPUESTO.md`
**No autoriza:** benchmark comparativo T1–T4, implementación productiva, elección de alternativa ni merge.

---

## 1. Qué es y qué no es este Registro

**Es** el lugar único donde viven las cifras que gobiernan las decisiones de ADR-002: las que ya son canónicas, las que esta ronda ha medido y propone, y las que por contrato solo pueden congelarse frente a un candidato concreto.

**No es** una reinterpretación de nada aprobado. Las reglas canónicas se reproducen **literalmente** y **ningún umbral se ha rebajado** a la vista de los resultados. Cuando la línea base incumple un umbral canónico, el que falla es la línea base, no el umbral.

### 1.1 Estados

| Estado | Significado |
|---|---|
| `CANÓNICA` | Ya aprobada en B04/PDP. Se reproduce literalmente. **No se toca.** |
| `PROPUESTA` | Cifra nueva que esta ronda propone con medición y margen declarados. Requiere aprobación explícita. |
| `REGLA_CONFIRMADA_VALOR_CANDIDATO` | La regla es firme; el **valor** solo puede fijarse frente a un candidato concreto y antes de ejecutarlo. |
| `NO_APLICA_ADR002` | Pertenece a otro ADR. Se registra la dependencia, no se decide aquí. |

### 1.2 Regla de propuesta

Toda fila `PROPUESTA` declara **dato observado**, **margen elegido** y **consecuencia de fallo**. Ninguna cifra de este Registro se ha inventado: o es canónica, o procede de una medición reproducible de esta ronda.

---

## 2. Valores ya canónicos — TOL-001 a TOL-006

Reproducidos literalmente del Plan de Pruebas canónico. **Estado: `CANÓNICA` en las seis.**

| ID | Regla | Umbral | Responsable |
|---|---|---|---|
| **TOL-001** | **Orden y equivalencia B04/B05.** Mismos críticos, estados, razones y dependencias. El orden no crítico solo puede variar dentro de una clase de equivalencia prefijada y sin alterar el resultado material | **100 % críticos; ≥95 % global** | ADR-002 |
| **TOL-002** | **Indistinguibilidad temporal.** Pares con igual configuración y entorno deben caer en la misma banda externa prefijada; cualquier diferencia repetible atribuible a existencia protegida falla. **La banda concreta se congela con el candidato antes de ejecutar** | banda prefijada por candidato | ADR-002 |
| **TOL-003** | **Carga e interrupciones.** Máximo una interrupción ordinaria no solicitada por unidad de trabajo; excepciones solo por privacidad o criticidad y registradas | máx. 1 por unidad de trabajo | Interacción — `NO_APLICA_ADR002` |
| **TOL-004** | **Coste contextual UCC.** Adaptador monotónico y estable; mismo adaptador para comparar. Presupuesto objetivo y duro se congelan con el candidato antes de ejecutar | por candidato | ADR-003B — ADR-002 solo registra la dependencia |
| **TOL-005** | **Portabilidad semántica.** Dos consumidores realmente independientes, incluidas negaciones, condiciones y permisos reportables | **100 % campos críticos; ≥99 % global** | ADR-002 (comparte con B05) |
| **TOL-006** | **Comprensión de operaciones** | **≥95 % no destructivas; 100 % destructivas** antes de confirmación final | Interacción — `NO_APLICA_ADR002` |

---

## 3. Valores ya canónicos — B04-M01 a M21

Reproducidos literalmente. **Estado: `CANÓNICA` en las veintiuna. Estas cifras no se rebajan por resultados de la línea base.**

| ID | Métrica | Umbral | Línea base 0.1 |
|---|---|---|---|
| M01 | Recall crítico | **100 % por caso** | no evaluable: no hay criticidad |
| M02 | Recall total | **≥90 % global; ≥85 % por familia** | no evaluado en esta ronda |
| M03 | Precisión útil | **≥80 % global; ningún caso <60 %** | no evaluado en esta ronda |
| M04 | Contaminación prohibida | **0 absoluto** | no evaluado en esta ronda |
| M05 | Obsoleto como vigente | **0 crítico; ≤1 % global** | no evaluado en esta ronda |
| **M06** | **Aislamiento de proyecto** | **100 %** | **INCUMPLIDO — fuga medida (§6 del informe)** |
| M07 | Procedencia recuperable | **100 %** | no existe procedencia múltiple en 0.1 |
| M08 | Visibilidad de conflicto | **100 % críticos; ≥95 % global** | no existe postura en 0.1 |
| M09 | Estado interno de ausencia | **100 % críticos; ≥95 % global; 0 falsos «no existe»** | no existe taxonomía de ausencia |
| M10 | Deduplicación | **0 fusiones materiales erróneas; ≥95 % agrupaciones correctas** | no hay deduplicación |
| M11 | Separación temporal | **100 % críticos; ≥95 % global** | no existen los ejes |
| M12 | Fallback | **0 violaciones de no uso; 100 % de fragmentos sustituidos/candidatos enlazados** | no existe la marca |
| M13 | Aclaración material | **100 %** | no existe |
| M14 | Explicación mínima completa | **100 % de muestra auditada** | parcial |
| M15 | Trazabilidad del plan | **100 %** | no se registra plan |
| M16 | Neutralidad | **100 % semántico; tolerancia de orden TOL-001** | puerto neutral: cumple en forma |
| M17 | Negación | **100 % críticos; ≥95 % global** | **INCUMPLIDO — medido en el trabajo 01** |
| M18 | Condición | **100 % críticos; ≥95 % global** | no representada |
| M19 | Criticidad | **100 %; 0 auto-marcados sin regla; 0 exclusiones por presupuesto ordinario** | no existe |
| M20 | Indistinguibilidad externa | **100 %; 0 canales laterales observables dentro de tolerancias prefijadas** | estado/texto/conteo equivalentes; tiempo sin diferencia repetible observada (§5 del informe) |
| M21 | Límites/parada/desempate | **100 %; 0 ampliaciones silenciosas; 0 variaciones no justificadas** | recorte silencioso, sin paradas |

**La columna «línea base» es informativa.** Registra dónde está hoy Sirius 0.1 frente al umbral canónico. **No modifica ningún umbral.**

---

## 4. Valores que esta ronda propone

Todas las filas siguientes son **`PROPUESTA`** salvo indicación expresa. Todas declaran dato observado, margen y consecuencia de fallo.

### ADR002-TOL-101 · Latencia del sustrato léxico

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002 |
| **Métrica y fórmula** | Latencia de una consulta al índice léxico, en ms. Percentiles por rango más cercano sobre las muestras de un escenario |
| **Escenario y entorno** | Corpus de referencia (5.000 mensajes, 500 recuerdos); linux x86_64; SQLite 3.45.1; head `61be4bb269bf` |
| **Repeticiones** | n=100 por escenario, warm-up 5 descartado |
| **Dato observado** | P50 0,172–0,576 ms · P95 0,209–0,730 ms · P99 0,251–1,415 ms |
| **Objetivo** | **P95 ≤ 1,5 ms** al volumen de referencia |
| **Límite duro** | **P99 ≤ 5 ms** |
| **Margen elegido** | Objetivo ×2,05 sobre el peor P95 observado (0,730 ms); límite duro ×3,5 sobre el peor P99 (1,415 ms). Margen amplio porque un candidato con vocabulario mayor o índice distinto puede ser legítimamente más lento sin dejar de ser aceptable |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos |
| **Estado** | `PROPUESTA` |
| **Consecuencia de fallo** | No descarta por sí sola: obliga a justificar el coste frente a la aportación medida de la señal. Si además incumple ADR002-TOL-102, descarta |

### ADR002-TOL-102 · Latencia de la recuperación completa

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002 |
| **Métrica y fórmula** | Latencia extremo a extremo de una consulta de recuperación, en ms, sin incluir construcción de fixtures |
| **Escenario y entorno** | Los tres escenarios de consulta sobre el corpus de referencia |
| **Repeticiones** | n=30 por escenario, warm-up 5 descartado |
| **Dato observado** | P50 113,3–122,6 ms · P95 125,1–137,8 ms · P99 129,0–154,4 ms |
| **Objetivo** | **P95 ≤ 140 ms** al volumen de referencia |
| **Límite duro** | **P99 ≤ 250 ms** |
| **Margen elegido** | Objetivo +1,6 % sobre el peor P95 observado (137,8 ms): es un **techo de no regresión** respecto de la línea base, no una meta de rendimiento. Límite duro ×1,6 sobre el peor P99 (154,4 ms), margen amplio porque con n=30 el P99 es el máximo observado y absorbe mal el ruido de máquina |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos |
| **Estado** | `PROPUESTA` |
| **Consecuencia de fallo** | Superar el límite duro descarta el candidato por la puerta 7 de ADR-002 |
| **Advertencia** | El **99,85 %** de la latencia de la línea base es el barrido que **B04-RF-14 prohíbe**. Un candidato conforme debería estar holgadamente por debajo de este techo. Un candidato que apenas lo alcance probablemente esté reproduciendo el mismo defecto |

### ADR002-TOL-103 · Estabilidad de conjunto y orden ante entradas idénticas

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002 |
| **Métrica y fórmula** | Número de órdenes distintos y de conjuntos distintos observados al repetir la **misma** consulta |
| **Escenario y entorno** | Tres escenarios (0, 1 y 200 resultados) sobre el corpus de referencia |
| **Repeticiones** | n=30 por escenario |
| **Dato observado** | **1 orden distinto y 1 conjunto distinto** en los tres escenarios: estabilidad perfecta |
| **Objetivo** | **100 % de repeticiones con orden idéntico y conjunto idéntico** |
| **Límite duro** | **Idéntico al objetivo: cualquier variación es fallo** |
| **Margen elegido** | **Ninguno, deliberadamente.** La línea base ya alcanza el 100 %; aceptar menos sería rebajar por conveniencia. No rebaja TOL-001, que gobierna entradas *equivalentes*: esta fila gobierna entradas *idénticas*, un caso estrictamente más exigente |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos |
| **Estado** | `PROPUESTA` |
| **Consecuencia de fallo** | Descarta por la puerta 4 de ADR-002 (inestabilidad material de orden o selección) |

### ADR002-TOL-104 · Tamaño del índice derivado

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002 |
| **Métrica y fórmula** | `bytes del índice y sus tablas sombra ÷ bytes del contenido canónico que indexa`, medido con `dbstat` |
| **Escenario y entorno** | Corpus de referencia; ambos índices por separado |
| **Repeticiones** | medición directa, no distribucional |
| **Dato observado** | `knowledge_fts` (autocontenida) **×3,54** · `message_fts` (external content) **×0,71** · derivados = 24,9 % del fichero |
| **Objetivo** | **≤ ×4,0** por índice sobre el canon que cubre |
| **Límite duro** | **≤ ×8,0** por índice; y **suma de todos los derivados ≤ 50 %** del fichero |
| **Margen elegido** | Objetivo +13 % sobre el peor caso observado (×3,54). Límite duro ×2 sobre el objetivo, porque un índice con señal semántica almacena vectores y es legítimamente mayor que uno léxico. El tope agregado del 50 % procede de duplicar el 24,9 % observado |
| **Punto de congelación** | Antes del benchmark para el sustrato léxico; el techo de índices adicionales se congela con cada candidato |
| **Estado** | `PROPUESTA` |
| **Consecuencia de fallo** | No descarta por sí sola: obliga a justificar el coste. Combinada con incumplimiento de la puerta 5, descarta |
| **Nota** | El contraste ×3,54 frente a ×0,71 es exactamente el precio de guardar el contenido canónico dentro del derivado. Si 0.2 exige que ningún derivado retenga contenido en claro, esta fila deja de ser una tolerancia de tamaño y pasa a ser una restricción de diseño |

### ADR002-TOL-105 · Construcción y reconstrucción desde el canon

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002, con obligación heredada de ADR-001 (consecuencias 2 y 3) |
| **Métrica y fórmula** | Tiempo en ms de destruir, construir y reconstruir el índice **desde la fuente canónica**; y booleano de restitución idéntica |
| **Escenario y entorno** | Corpus de referencia, sobre copia de la base |
| **Repeticiones** | una pasada cronometrada por operación (irrepetibles por naturaleza) |
| **Dato observado** | Borrado 48,8 ms · construcción desde canon 55,8 ms · `rebuild` interno 17,0 ms · **reconstrucción desde canon 49,1 ms** · filas restituidas idénticas · `integrity-check` OK |
| **Objetivo** | **Reconstrucción completa desde el canon ≤ 100 ms** al volumen de referencia, para el sustrato léxico |
| **Límite duro** | **Restitución idéntica: obligatoria, sin margen.** El índice reconstruido debe contener exactamente las mismas filas y pasar `integrity-check` |
| **Margen elegido** | ×2 sobre el dato observado (49,1 ms) para el tiempo. Para la restitución idéntica, **ninguno**: es la puerta 5 de ADR-002 y no admite grado |
| **Punto de congelación** | Antes del benchmark para el sustrato léxico; el tiempo de índices adicionales, con cada candidato |
| **Estado** | `PROPUESTA` (tiempo) · el requisito de restitución idéntica es consecuencia directa de ADR-001 |
| **Consecuencia de fallo** | Fallo de restitución **descarta** por la puerta 5. Exceso de tiempo obliga a justificar |
| **Advertencia** | El `rebuild` interno (17,0 ms) reconstruye `knowledge_fts` **desde sí misma**, no desde `memory_revisions`. **No satisface la obligación de ADR-001** y no puede usarse como evidencia de conformidad. La ruta válida es la de 49,1 ms |

### ADR002-TOL-106 · Borrado y desaparición del derivado

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002, obligación heredada de ADR-001 (consecuencia 3) |
| **Métrica y fórmula** | Booleano: ¿desaparecen el índice, sus triggers y **todas** sus tablas sombra? |
| **Escenario y entorno** | Corpus de referencia, sobre copia |
| **Repeticiones** | una pasada, verificada por consulta a `sqlite_master` |
| **Dato observado** | **Desaparición completa: sí. Sin rastro de tablas sombra: sí.** 48,8 ms |
| **Objetivo** | **100 %, sin residuo** |
| **Límite duro** | **Idéntico. Sin margen.** |
| **Margen elegido** | **Ninguno.** Es la puerta 5 de ADR-002 y la consecuencia 3 de ADR-001 |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos |
| **Estado** | `PROPUESTA` (la regla ya es obligación de ADR-001; aquí solo se le da forma medible) |
| **Consecuencia de fallo** | **Descarta** el candidato por la puerta 5 |
| **Nota** | La purga **física** del fichero es un paso distinto y requiere `VACUUM`, según demostró el spike 10 de ADR-001. Esta fila cubre la desaparición lógica del derivado, no la purga del medio |

### ADR002-TOL-107 · Variación entre ejecuciones equivalentes

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002 |
| **Métrica y fórmula** | `|P_x(ejecución B) − P_x(ejecución A)| ÷ P_x(ejecución A)` para el mismo escenario, y número de órdenes distintos entre ejecuciones |
| **Escenario y entorno** | Dos ejecuciones completas del runner en la misma máquina |
| **Repeticiones** | 2 ejecuciones × n por escenario |
| **Dato observado** | Latencia: **+6,8 % en P50, +9,5 % en P95**. Orden: **0 variación** |
| **Objetivo** | Latencia: **variación ≤ 25 % en P50 y P95**. Orden: **0 variación** |
| **Límite duro** | Latencia: **≤ 50 %**; superarlo invalida la comparación. Orden: **0**, sin margen |
| **Margen elegido** | ×2,6 sobre la variación observada (9,5 %) para absorber una máquina con carga distinta; ×5 como límite duro. Para el orden, **ninguno**: variar el orden entre ejecuciones con la misma entrada es un defecto, no ruido |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos |
| **Estado** | `PROPUESTA` |
| **Consecuencia de fallo** | Latencia: la comparación entre candidatos **no es válida** y debe repetirse en condiciones controladas; no descarta al candidato. Orden: descarta por la puerta 4 |

---

## 5. Reglas confirmadas cuyo valor se congela con cada candidato

Estas filas **no llevan cifra** y no puede dárseles una desde la línea base. La regla es firme; el valor se fija frente al candidato **antes** de ejecutarlo, y queda registrado en su propia ficha de benchmark.

### ADR002-TOL-201 · Banda temporal de TOL-002

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002 |
| **Regla canónica** | TOL-002: pares con igual configuración deben caer en la misma banda externa prefijada; cualquier diferencia repetible atribuible a existencia protegida falla. **La banda se congela con el candidato antes de ejecutar** |
| **Forma propuesta de la banda** | Tres condiciones simultáneas: (1) estado, texto y conteo externos **exactamente equivalentes**; (2) **fracción de signo pareada dentro de [0,40 · 0,60]** con n≥30 por rama; (3) sin diferencia de signo constante al repetir la medición en sesión independiente |
| **Dato observado** | Fracción de signo **0,533** (`rank()`, n=30) y **0,490** (índice, n=100). Δ P50 +0,337 ms y +0,0039 ms. Estado, texto y conteo equivalentes |
| **Por qué la fracción de signo y no el Δ de percentil** | Con n=30 por rama, P95 y P99 son la segunda peor y la peor muestra: los Δ observados de +15,4 ms y +21,5 ms **no son interpretables**. La fracción de signo es robusta con n moderado y detecta precisamente lo que TOL-002 prohíbe: una diferencia **repetible** |
| **Punto de congelación** | **Con cada candidato, antes de ejecutarlo** |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Descarta por la puerta 8 de ADR-002 e incumple M20 |
| **Advertencia crítica** | La indistinguibilidad observada hoy es **en buena medida accidental**: el barrido constante de 122,5 ms enmascara una diferencia de trabajo real ~31.000 veces menor. **Un candidato que elimine el barrido, como B04-RF-14 exige, perderá ese enmascaramiento.** TOL-002 debe reevaluarse con cada candidato y su resultado **no puede heredarse** de esta medición |

### ADR002-TOL-202 · Coste incremental por etapa E0–E5

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002 |
| **Regla** | Cada etapa declara su coste incremental en tiempo y operaciones locales; cualquier coste externo se declara **aparte** y nunca se mezcla con el local |
| **Dato observado** | **Ninguno. No medible en la línea base:** Sirius 0.1 no tiene etapas — resuelve en una sola pasada más el barrido completo, que es el salto que B04-RF-14 prohíbe |
| **Punto de congelación** | Con cada candidato que implemente E0–E5, antes de ejecutarlo |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Un candidato que no pueda declarar el coste por etapa no es evaluable contra RF-14 y no puede compararse |

### ADR002-TOL-203 · Tamaño y reconstrucción de índices adicionales

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002 |
| **Regla** | Todo índice adicional que un candidato introduzca hereda íntegras las obligaciones de ADR002-TOL-104, TOL-105 y TOL-106: ratio declarado, reconstrucción **desde el canon** y desaparición completa |
| **Dato observado** | Solo para los dos índices de la línea base; ningún candidato medido |
| **Punto de congelación** | Con cada candidato, antes de ejecutarlo |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Descarta por la puerta 5 |

### ADR002-TOL-204 · Umbral operativo de cobertura de críticos

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002, dependiente del contrato canónico de suficiencia |
| **Regla** | La suficiencia depende de cardinalidad (`EXACTA`/`ACOTADA`/`EXHAUSTIVA`), cobertura de críticos elegibles pendientes, etapas autorizadas ejecutadas, taxonomía interna y paradas S1–S7. **La definición no es una laguna: está aprobada** |
| **Qué falta** | El **umbral operativo** de cobertura que adjudica suficiencia. M01 ya fija recall crítico 100 % por caso; lo que no está fijado es la fracción de críticos *pendientes* que permite detener la expansión |
| **Dato observado** | Ninguno: la línea base no tiene criticidad ni suficiencia |
| **Punto de congelación** | Con cada candidato, antes de ejecutarlo, y sin poder rebajar M01 |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Sin este umbral, T1–T4 son indistinguibles entre sí: las tres realizaciones con señal tardía se definen por actuar «tras fallar la puerta de suficiencia» |

---

## 6. Dependencias que no decide ADR-002

| ID | Ámbito | Tratamiento |
|---|---|---|
| **TOL-003** | Carga e interrupciones | `NO_APLICA_ADR002`. Se registra la dependencia |
| **TOL-004** | Coste contextual UCC | `NO_APLICA_ADR002`. Pertenece a **ADR-003B**. ADR-002 solo registra que el presupuesto objetivo y duro se congelan con el candidato |
| **TOL-006** | Comprensión de operaciones | `NO_APLICA_ADR002` |
| **RED-040** | Reintento acotado entre recuperación y contexto | `NO_APLICA_ADR002`. Pertenece a **B05/ADR-003B**. ADR-002 solo **registra la interfaz**: no la diseña y **no la usa como requisito propio de selección técnica** |

---

## 7. Punto de congelación — regla de proceso

**Antes del benchmark**, y comunes a todos los candidatos, se congelan: ADR002-TOL-101, 102, 103, 104, 105, 106 y 107, más todas las filas `CANÓNICA` de las §2 y §3.

**Con cada candidato y antes de ejecutarlo**, se congelan: ADR002-TOL-201, 202, 203 y 204, más el techo de tamaño y tiempo de sus índices adicionales.

**Reglas duras del proceso:**

1. Ningún valor se fija **después** de observar el resultado del candidato. Un valor congelado tarde no es una tolerancia: es una justificación a posteriori.
2. Los valores congelados por candidato se registran en la ficha del caso, con su fundamento, **antes** de la primera ejecución.
3. Un umbral canónico **nunca** se rebaja. Si un candidato no lo alcanza, el que falla es el candidato.
4. Cambiar cualquier valor de este Registro obliga a **repetir** las comparaciones ya ejecutadas bajo el valor anterior.

---

## 8. Estado de aprobación

**Este Registro está `PROPUESTO` y no está aprobado.** Requiere decisión explícita del usuario antes de ejecutar cualquier decisión dependiente de latencia, coste, tamaño o estabilidad.

Resumen por estado:

| Estado | Filas |
|---|---|
| `CANÓNICA` | TOL-001, TOL-002, TOL-005 (más TOL-003, TOL-004 y TOL-006 como dependencia) y B04-M01–M21 |
| `PROPUESTA` | ADR002-TOL-101, 102, 103, 104, 105, 106, 107 |
| `REGLA_CONFIRMADA_VALOR_CANDIDATO` | ADR002-TOL-201, 202, 203, 204 |
| `NO_APLICA_ADR002` | TOL-003, TOL-004, TOL-006, RED-040 |

**Ningún umbral canónico ha sido modificado ni rebajado en este documento.**

---

**Siguiente movimiento único:** que el usuario apruebe, corrija o rechace las siete filas `PROPUESTA`. Hasta entonces no se construye corpus de benchmark, no se implementa ningún prototipo y no se ejecuta ningún candidato.
