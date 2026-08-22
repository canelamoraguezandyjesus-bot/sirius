# SIRIUS 0.2 — Registro de Tolerancias

**Versión:** 0.2
**Estado:** **PROPUESTO** · este Registro **no está aprobado** y no autoriza nada por sí mismo
**Fecha:** 25 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.1_PROPUESTO.md`, que se conserva sin modificar
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02B_CORRECCION_TOLERANCIAS_v0.1.md`
**Evidencia:** `artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json` · `INFORME_MEDICION_TOLERANCIAS_v0.2_PROPUESTO.md`
**Alcance de toda cifra medida:** **LAB-LINUX** · `ACEPTACIÓN-WINDOWS` **pendiente**
**No autoriza:** benchmark T1–T4, implementación productiva, elección de alternativa ni merge.

---

## 0. Qué corrige esta versión

| Corrección | v0.1 | v0.2 |
|---|---|---|
| **TOL-204 críticos pendientes** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` — **contradecía B04** | **`DERIVADA_CANÓNICA`: 0 críticos elegibles pendientes.** No depende del candidato |
| **TOL-105 ciclo del índice** | Una sola pasada, «irrepetible por naturaleza» | **30 repeticiones** sobre copias limpias, con distribución y tasa de éxito |
| **TOL-106 borrado** | Booleano de una pasada | Booleano **+ distribución de 30 repeticiones**, tasa 100 % |
| **TOL-107 variación** | Objetivo 25 %, límite duro 50 %, sobre **2** ejecuciones | **5 sesiones**; peor valor real **36,4 %**; límite duro → `REGLA_CONFIRMADA_VALOR_ENTORNO` |
| **Alcance** | No declarado | **LAB-LINUX** en toda cifra; `ACEPTACIÓN-WINDOWS` pendiente |

**Ningún umbral canónico se ha tocado.** TOL-001–006 y B04-M01–M21 se reproducen literalmente, igual que en la v0.1.

---

## 1. Cómo leer este Registro

### 1.1 Estados

| Estado | Significado |
|---|---|
| `CANÓNICA` | Ya aprobada en B04/PDP. Se reproduce literalmente. **No se toca.** |
| `DERIVADA_CANÓNICA` | Su valor **se deduce sin margen** de una regla canónica. No es una propuesta y no admite negociación por candidato. |
| `PROPUESTA` | Cifra nueva con medición, margen y consecuencia declarados. Requiere aprobación explícita. |
| `REGLA_CONFIRMADA_VALOR_CANDIDATO` | La regla es firme; el valor solo puede fijarse frente a un candidato concreto, antes de ejecutarlo. |
| `REGLA_CONFIRMADA_VALOR_ENTORNO` | La regla es firme; el valor depende del entorno de ejecución y **la evidencia disponible no basta** para fijarlo. **No se inventa.** |
| `NO_APLICA_ADR002` | Pertenece a otro ADR. Se registra la dependencia. |

### 1.2 Alcance de toda cifra medida

**`LAB-LINUX`** — umbral del laboratorio comparativo Linux. Sirve para comparar T1–T4 entre sí en el mismo entorno, y solo para eso.

**`ACEPTACIÓN-WINDOWS`** — **PENDIENTE**. Ninguna cifra absoluta de latencia, tamaño o ciclo se traslada automáticamente a Windows. Aceptar la implementación exige confirmar el comportamiento sobre el ejecutable o entorno de referencia Windows, incluidos el tokenizador, `secure_delete` y la secuencia de purga que ADR-001 dejó pendientes.

**Sí es trasladable** lo booleano: restitución idéntica, `integrity-check`, desaparición completa del derivado y estabilidad de orden y conjunto. Son propiedades de comportamiento, no cifras de rendimiento.

### 1.3 Regla de propuesta

Toda fila `PROPUESTA` declara **dato observado**, **margen elegido** y **consecuencia de fallo**. Ninguna cifra se ha inventado: o es canónica, o procede de una medición reproducible.

---

## 2. Valores ya canónicos — TOL-001 a TOL-006

Reproducidos literalmente. **Estado: `CANÓNICA` en las seis.**

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
| **M01** | **Recall crítico** | **100 % por caso** | no evaluable: no hay criticidad |
| M02 | Recall total | **≥90 % global; ≥85 % por familia** | no evaluado |
| M03 | Precisión útil | **≥80 % global; ningún caso <60 %** | no evaluado |
| M04 | Contaminación prohibida | **0 absoluto** | no evaluado |
| M05 | Obsoleto como vigente | **0 crítico; ≤1 % global** | no evaluado |
| **M06** | **Aislamiento de proyecto** | **100 %** | **INCUMPLIDO — fuga medida** |
| M07 | Procedencia recuperable | **100 %** | no existe procedencia múltiple |
| M08 | Visibilidad de conflicto | **100 % críticos; ≥95 % global** | no existe postura |
| M09 | Estado interno de ausencia | **100 % críticos; ≥95 % global; 0 falsos «no existe»** | no existe taxonomía |
| M10 | Deduplicación | **0 fusiones materiales erróneas; ≥95 % agrupaciones correctas** | no hay deduplicación |
| M11 | Separación temporal | **100 % críticos; ≥95 % global** | no existen los ejes |
| M12 | Fallback | **0 violaciones de no uso; 100 % de fragmentos sustituidos/candidatos enlazados** | no existe la marca |
| M13 | Aclaración material | **100 %** | no existe |
| M14 | Explicación mínima completa | **100 % de muestra auditada** | parcial |
| M15 | Trazabilidad del plan | **100 %** | no se registra plan |
| M16 | Neutralidad | **100 % semántico; tolerancia de orden TOL-001** | puerto neutral: cumple en forma |
| **M17** | **Negación** | **100 % críticos; ≥95 % global** | **INCUMPLIDO — medido** |
| M18 | Condición | **100 % críticos; ≥95 % global** | no representada |
| M19 | Criticidad | **100 %; 0 auto-marcados sin regla; 0 exclusiones por presupuesto ordinario** | no existe |
| M20 | Indistinguibilidad externa | **100 %; 0 canales laterales observables dentro de tolerancias prefijadas** | estado/texto/conteo equivalentes; sin diferencia temporal repetible observada |
| M21 | Límites/parada/desempate | **100 %; 0 ampliaciones silenciosas; 0 variaciones no justificadas** | recorte silencioso, sin paradas |

---

## 4. Derivada canónica — cobertura de críticos

### ADR002-TOL-204 · Cero críticos elegibles pendientes

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002, derivada del contrato canónico de suficiencia y de **B04-M01** |
| **Regla canónica de la que deriva** | La expansión continúa cuando falta suficiencia **o queda un crítico elegible pendiente**. S1 solo opera en cardinalidad `EXACTA` o `ACOTADA` **tras comprobar que no queda ningún crítico elegible pendiente** en espacios autorizados. Una consulta `EXHAUSTIVA` **nunca** termina por S1. M01 exige 100 % de críticos recuperados por caso |
| **Métrica y fórmula** | `críticos elegibles pendientes en espacios autorizados` al adjudicar suficiencia |
| **Objetivo** | **0** |
| **Límite duro** | **0. Sin margen.** |
| **Fundamento** | No es una propuesta: se deduce sin margen del contrato canónico. La v0.1 la clasificó como pendiente de congelar por candidato, y **eso contradecía B04** |
| **Qué decide el candidato** | Únicamente **cómo** implementa y demuestra la comprobación. **Nunca el umbral** |
| **Comportamiento bajo límite duro** | Si el límite duro impide incluir críticos elegibles, estos **se contabilizan** y la salida es **`PARCIAL` visible**. Nunca se adjudica suficiencia completa, y el desbordamiento **no puede ocultarse** (RF-24) |
| **Punto de congelación** | Ya congelada. No se renegocia |
| **Estado** | **`DERIVADA_CANÓNICA`** |
| **Consecuencia de fallo** | Adjudicar suficiencia con un crítico elegible pendiente incumple M01 y el contrato de suficiencia: **descarta** el candidato. Omitir críticos sin contabilizarlos ni marcar `PARCIAL` incumple además M21 |
| **Estado en la línea base** | `AUSENTE`: Sirius 0.1 no tiene criticidad, ni suficiencia, ni salida parcial visible |

---

## 5. Valores propuestos — alcance LAB-LINUX

Todas `PROPUESTA` salvo indicación. Todas declaran dato observado, margen y consecuencia.

### ADR002-TOL-101 · Latencia del sustrato léxico · `LAB-LINUX`

| Campo | Contenido |
|---|---|
| **Métrica** | Latencia de una consulta al índice léxico, ms, percentiles nearest-rank |
| **Escenario** | Corpus de referencia (5.000 mensajes, 500 recuerdos); linux x86_64; head `61be4bb269bf` |
| **Repeticiones** | n=100 por escenario, warm-up 5 |
| **Dato observado** | P50 0,172–0,576 ms · P95 0,209–0,730 ms · P99 0,251–1,415 ms |
| **Objetivo** | **P95 ≤ 1,5 ms** |
| **Límite duro** | **P99 ≤ 5 ms** |
| **Margen** | ×2,05 sobre el peor P95; ×3,5 sobre el peor P99. Amplio porque un candidato con vocabulario o índice distinto puede ser legítimamente más lento |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos |
| **Estado** | `PROPUESTA` · `LAB-LINUX` |
| **Consecuencia de fallo** | No descarta por sí sola: obliga a justificar el coste frente a la aportación medida. Combinada con TOL-102, descarta |

### ADR002-TOL-102 · Latencia de la recuperación completa · `LAB-LINUX`

| Campo | Contenido |
|---|---|
| **Métrica** | Latencia extremo a extremo, ms, sin incluir construcción de fixtures |
| **Repeticiones** | n=30 por escenario × 5 sesiones independientes |
| **Dato observado** | P50 113,3–128,6 ms · P95 125,1–147,2 ms · P99 129,0–154,4 ms |
| **Objetivo** | **P95 ≤ 150 ms** |
| **Límite duro** | **P99 ≤ 250 ms** |
| **Margen** | Objetivo +1,9 % sobre el peor P95 observado en las cinco sesiones (147,2 ms): **techo de no regresión**, no meta de rendimiento. Límite duro ×1,6 sobre el peor P99 (154,4 ms), amplio porque con n=30 el P99 es el máximo y absorbe mal el ruido |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos |
| **Estado** | `PROPUESTA` · `LAB-LINUX` |
| **Consecuencia de fallo** | Superar el límite duro descarta por la puerta 7 |
| **Advertencia** | El **99,85 %** de esta latencia es el barrido que **B04-RF-14 prohíbe**. Un candidato conforme debería estar holgadamente por debajo. Uno que apenas alcance el techo probablemente reproduce el mismo defecto |

*Nota de corrección:* el objetivo sube de 140 ms (v0.1) a 150 ms **no por rebaja**, sino porque cinco sesiones observaron un P95 de 147,2 ms que dos ejecuciones no habían visto. La cifra sigue anclada al peor valor observado + margen mínimo.

### ADR002-TOL-103 · Estabilidad ante entradas idénticas · trasladable

| Campo | Contenido |
|---|---|
| **Métrica** | Órdenes y conjuntos distintos al repetir la **misma** consulta |
| **Repeticiones** | n=30 intra-sesión × 3 escenarios, y **5 sesiones independientes** |
| **Dato observado** | **1 orden y 1 conjunto** en todos los casos, intra-sesión **y entre sesiones** |
| **Objetivo** | **100 % orden idéntico y conjunto idéntico** |
| **Límite duro** | **Idéntico. Cualquier variación es fallo** |
| **Margen** | **Ninguno.** La línea base ya alcanza el 100 %. No rebaja TOL-001, que gobierna entradas *equivalentes*: esta fila gobierna entradas *idénticas*, caso estrictamente más exigente |
| **Estado** | `PROPUESTA` · **propiedad de comportamiento, trasladable a Windows** |
| **Consecuencia de fallo** | Descarta por la puerta 4 |

### ADR002-TOL-104 · Tamaño del índice derivado · `LAB-LINUX`

| Campo | Contenido |
|---|---|
| **Métrica** | `bytes del índice y sus sombras ÷ bytes del canon que indexa`, vía `dbstat` |
| **Dato observado** | `knowledge_fts` **×3,54** · `message_fts` **×0,71** · derivados = 24,9 % del fichero |
| **Objetivo** | **≤ ×4,0** por índice |
| **Límite duro** | **≤ ×8,0** por índice; **suma de derivados ≤ 50 %** del fichero |
| **Margen** | +13 % sobre el peor caso; ×2 para el límite duro, porque un índice con señal semántica almacena vectores y es legítimamente mayor. El tope agregado duplica el 24,9 % observado |
| **Estado** | `PROPUESTA` · `LAB-LINUX` |
| **Consecuencia de fallo** | No descarta por sí sola; combinada con la puerta 5, descarta |
| **Nota** | El contraste ×3,54 frente a ×0,71 es el precio de guardar contenido canónico dentro del derivado. Si 0.2 prohíbe retener contenido en claro, deja de ser tolerancia de tamaño y pasa a restricción de diseño |

### ADR002-TOL-105 · Ciclo del índice desde el canon · `LAB-LINUX` + trasladable

| Campo | Contenido |
|---|---|
| **Métrica** | Tiempo de borrado, construcción y reconstrucción **desde el canon**, ms; y booleano de restitución idéntica |
| **Escenario** | **30 repeticiones**, cada una sobre copia limpia independiente preparada fuera del cronómetro; 2 de warm-up descartadas |
| **Dato observado** | Borrado P50 43,6 · P95 84,3 · P99 122,9 — Construcción P50 51,9 · P95 96,6 · P99 102,6 — **Reconstrucción P50 29,3 · P95 41,7 · P99 44,5** |
| **Objetivo** | Reconstrucción desde el canon **P95 ≤ 60 ms**; construcción **P95 ≤ 120 ms**; borrado **P95 ≤ 110 ms** |
| **Límite duro** | **P99 ≤ 150 ms** en cualquiera de las tres operaciones · **restitución idéntica: obligatoria, sin margen** |
| **Margen** | ×1,44 sobre el P95 de reconstrucción, ×1,24 sobre el de construcción, ×1,30 sobre el de borrado. Límite duro anclado a la peor cola observada del ciclo (122,9 ms, borrado) + 22 % |
| **Estado** | `PROPUESTA` (tiempos, `LAB-LINUX`) · la **restitución idéntica** deriva de ADR-001 y es **trasladable** |
| **Consecuencia de fallo** | Fallo de restitución **descarta** por la puerta 5. Exceso de tiempo obliga a justificar |
| **Advertencia** | El `rebuild` interno (P50 18,7 ms) reconstruye `knowledge_fts` **desde sí misma**, no desde `memory_revisions`. **No satisface ADR-001** y no puede usarse como evidencia. Además su **P99 es 269,9 ms**, seis veces su P95 |

*Nota de corrección:* la v0.1 proponía ≤100 ms con margen ×2 sobre **una sola pasada de 49,1 ms**. Las 30 repeticiones muestran que aquel valor único estaba **por encima del máximo real** (44,5 ms). El objetivo se re-ancla a la distribución, no a un punto.

### ADR002-TOL-106 · Borrado y desaparición del derivado · trasladable

| Campo | Contenido |
|---|---|
| **Métrica** | Booleano: ¿desaparecen índice, triggers y **todas** las tablas sombra? Más distribución de tiempo |
| **Escenario** | **30 repeticiones** sobre copias limpias independientes |
| **Dato observado** | **30/30 = 100 %** desaparición completa · **30/30 = 100 %** sin rastro de sombras · tiempo P50 43,6 ms |
| **Objetivo** | **100 %, sin residuo** |
| **Límite duro** | **Idéntico. Sin margen** |
| **Margen** | **Ninguno.** Es la puerta 5 y la consecuencia 3 de ADR-001 |
| **Estado** | `PROPUESTA` (la regla ya es obligación de ADR-001) · **trasladable** |
| **Consecuencia de fallo** | **Descarta** por la puerta 5 |
| **Nota** | La purga **física** del fichero es un paso distinto y requiere `VACUUM` (spike 10 de ADR-001). Esta fila cubre la desaparición lógica del derivado, no la purga del medio |

### ADR002-TOL-107 · Variación entre ejecuciones equivalentes · `LAB-LINUX`

| Campo | Contenido |
|---|---|
| **Métrica** | `(máx − mín) / mín` sobre el mismo percentil en todas las sesiones; y órdenes distintos entre sesiones |
| **Escenario** | **5 sesiones completas independientes**, cada una con fichero, motor, caché y warm-up propios |
| **Dato observado** | **Orden y conjunto: 0 variación** en las cinco sesiones. Latencia `rank()`: **2,8–10,6 % en P50, 12,3–15,8 % en P95**. Latencia FTS5: **13,4–29,3 % en P50, 32,9–36,4 % en P95**. **Peor global: 36,4 %** |
| **Objetivo** | **Orden y conjunto: 0 variación** (sin margen) · **`rank()`: ≤ 20 % en P50 y P95** |
| **Límite duro** | **Orden: 0, sin margen.** **Latencia: `REGLA_CONFIRMADA_VALOR_ENTORNO` — no se fija** |
| **Margen** | ×1,9 sobre el peor P50 y ×1,27 sobre el peor P95 de `rank()`. **Para FTS5 no se propone objetivo relativo**: con magnitudes de 0,14–1,0 ms, un 36 % son 0,27 ms absolutos — es el suelo de medición, no inestabilidad del sistema. A esa escala la comparación debe hacerse en valor absoluto |
| **Punto de congelación** | Objetivo, antes del benchmark. Límite duro, **con el entorno de ejecución** |
| **Estado** | `PROPUESTA` (objetivo, `LAB-LINUX`) · **`REGLA_CONFIRMADA_VALOR_ENTORNO`** (límite duro) |
| **Consecuencia de fallo** | Latencia: la comparación entre candidatos **no es válida** y debe repetirse en condiciones controladas; no descarta al candidato. Orden: descarta por la puerta 4 |
| **Por qué no se fija el límite duro** | Las cinco sesiones son independientes **dentro del mismo proceso**, en una máquina cuya carga no se controla. Acotan la variación intra-proceso, no la variación entre procesos, entre máquinas ni entre sistemas operativos. Fijar un techo defendible para otro entorno con esta evidencia sería inventarlo, y el §4 del paquete 02B lo prohíbe expresamente |

*Nota de corrección:* la v0.1 proponía objetivo 25 % y límite duro 50 % **sobre dos ejecuciones que dieron 9,5 %**. El peor valor real es **36,4 %**. La cifra del v0.1 no se rebaja para que encaje: se sustituye por un objetivo acotado a `rank()` y un límite duro que se declara **no fijable** con la evidencia disponible.

---

## 6. Reglas cuyo valor se congela con cada candidato

### ADR002-TOL-201 · Banda temporal de TOL-002

| Campo | Contenido |
|---|---|
| **Regla canónica** | TOL-002: pares con igual configuración deben caer en la misma banda externa prefijada; cualquier diferencia repetible atribuible a existencia protegida falla. **La banda se congela con el candidato antes de ejecutar** |
| **Forma propuesta de la banda** | **Cuatro** condiciones simultáneas: (1) estado, texto y conteo externos **exactamente equivalentes**; (2) **fracción de signo pareada dentro de [0,40 · 0,60]** con n≥30 por rama; (3) **ausencia de separación material en distribución**, no solo en un estadístico puntual; (4) **repetición en sesión independiente** con el mismo veredicto |
| **Dato observado** | Fracción de signo **0,533** (`rank()`, n=30) y **0,490** (índice, n=100); estado, texto y conteo equivalentes |
| **Corrección del 02B** | La fracción de signo se conserva como **una** condición, **nunca como única protección**. Las condiciones (3) y (4) son nuevas y obligatorias |
| **Por qué no basta un Δ de percentil** | Con n=30 por rama, P95 y P99 son la segunda peor y la peor muestra: los Δ observados de +15,4 ms y +21,5 ms **no son interpretables** |
| **Punto de congelación** | **Con cada candidato, antes de ejecutarlo** |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Descarta por la puerta 8; incumple M20 |
| **Advertencia crítica** | La indistinguibilidad observada hoy es **en buena medida accidental**: el barrido constante de 122,5 ms enmascara una diferencia de trabajo ~31.000 veces menor. **Un candidato que elimine el barrido, como RF-14 exige, perderá ese enmascaramiento.** El resultado **no se hereda** |

### ADR002-TOL-202 · Coste incremental por etapa E0–E5

| Campo | Contenido |
|---|---|
| **Regla** | Cada etapa declara su coste incremental en tiempo y operaciones locales; el coste externo se declara **aparte** y nunca se mezcla con el local |
| **Dato observado** | **Ninguno. No medible en la línea base:** Sirius 0.1 no tiene etapas |
| **Punto de congelación** | Con cada candidato que implemente E0–E5, antes de ejecutarlo |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Un candidato que no pueda declarar el coste por etapa no es evaluable contra RF-14 y no puede compararse |

### ADR002-TOL-203 · Tamaño y ciclo de índices adicionales

| Campo | Contenido |
|---|---|
| **Regla** | Todo índice adicional hereda íntegras las obligaciones de TOL-104, TOL-105 y TOL-106: ratio declarado, reconstrucción **desde el canon** y desaparición completa, con **al menos 30 repeticiones** y tasa de éxito del 100 % |
| **Dato observado** | Solo para los dos índices de la línea base; ningún candidato medido |
| **Punto de congelación** | Con cada candidato, antes de ejecutarlo |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Descarta por la puerta 5 |

### ADR002-TOL-205 · Aceptación sobre Windows

| Campo | Contenido |
|---|---|
| **Regla** | Ninguna cifra `LAB-LINUX` de latencia, tamaño o ciclo se traslada automáticamente. Antes de aceptar la implementación hay que confirmar el comportamiento sobre el ejecutable o entorno de referencia Windows, incluidos tokenizador, `secure_delete` y secuencia de purga |
| **Dato observado** | **Ninguno.** No se ha medido en Windows en ninguna ronda |
| **Qué sí se traslada** | Las comprobaciones booleanas: restitución idéntica, `integrity-check`, desaparición completa del derivado, estabilidad de orden y conjunto |
| **Punto de congelación** | Antes de aceptar la implementación productiva |
| **Estado** | **`REGLA_CONFIRMADA_VALOR_ENTORNO`** |
| **Consecuencia de fallo** | Presentar cifras Linux como aceptación del producto Windows invalida la aceptación |

---

## 7. Dependencias que no decide ADR-002

| ID | Ámbito | Tratamiento |
|---|---|---|
| **TOL-003** | Carga e interrupciones | `NO_APLICA_ADR002` |
| **TOL-004** | Coste contextual UCC | `NO_APLICA_ADR002`. Pertenece a **ADR-003B** |
| **TOL-006** | Comprensión de operaciones | `NO_APLICA_ADR002` |
| **RED-040** | Reintento acotado entre recuperación y contexto | `NO_APLICA_ADR002`. Pertenece a **B05/ADR-003B**. ADR-002 solo **registra la interfaz** |

---

## 8. Punto de congelación — regla de proceso

**Antes del benchmark**, comunes a todos los candidatos: ADR002-TOL-101, 102, 103, 104, 105, 106 y el **objetivo** de 107, más todas las filas `CANÓNICA` y la `DERIVADA_CANÓNICA` TOL-204.

**Con cada candidato, antes de ejecutarlo**: ADR002-TOL-201, 202 y 203.

**Con el entorno de ejecución**: el **límite duro** de ADR002-TOL-107 y ADR002-TOL-205.

**Reglas duras:**

1. Ningún valor se fija **después** de observar el resultado del candidato. Un valor congelado tarde no es tolerancia: es justificación a posteriori.
2. Los valores congelados por candidato se registran en la ficha del caso **antes** de la primera ejecución.
3. Un umbral canónico **nunca** se rebaja. Si un candidato no lo alcanza, falla el candidato.
4. **TOL-204 no se renegocia**: cero críticos elegibles pendientes es derivación canónica, no propuesta.
5. Cambiar cualquier valor obliga a **repetir** las comparaciones ya ejecutadas bajo el valor anterior.

---

## 9. Estado de aprobación

**Este Registro está `PROPUESTO` y no está aprobado.** Requiere decisión explícita del usuario.

| Estado | Filas |
|---|---|
| `CANÓNICA` | TOL-001, TOL-002, TOL-005 (y TOL-003, TOL-004, TOL-006 como dependencia) · B04-M01–M21 |
| `DERIVADA_CANÓNICA` | **ADR002-TOL-204** |
| `PROPUESTA` | ADR002-TOL-101, 102, 103, 104, 105, 106 · objetivo de 107 |
| `REGLA_CONFIRMADA_VALOR_CANDIDATO` | ADR002-TOL-201, 202, 203 |
| `REGLA_CONFIRMADA_VALOR_ENTORNO` | Límite duro de ADR002-TOL-107 · ADR002-TOL-205 |
| `NO_APLICA_ADR002` | TOL-003, TOL-004, TOL-006, RED-040 |

**Ningún umbral canónico ha sido modificado ni rebajado.** Todas las cifras medidas son **`LAB-LINUX`**; la **`ACEPTACIÓN-WINDOWS` queda pendiente**.

---

**Siguiente movimiento único:** que el usuario apruebe, corrija o rechace las filas `PROPUESTA` y confirme la derivación canónica de TOL-204. Hasta entonces no se construye corpus de benchmark, no se implementa ningún prototipo y no se ejecuta ningún candidato.
