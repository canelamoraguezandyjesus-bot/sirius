# SIRIUS 0.2 — Registro de Tolerancias

**Versión:** 0.3
**Estado:** **PROPUESTO** · este Registro **no está aprobado** y no autoriza nada por sí mismo
**Fecha:** 25 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.2_PROPUESTO.md`, que se conserva sin modificar (igual que la v0.1)
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02C_NEUTRALIDAD_ALMACENAMIENTO_v0.1.md`
**Evidencia:** `artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json` · `INFORME_MEDICION_TOLERANCIAS_v0.2_PROPUESTO.md`
**Alcance de toda cifra medida:** **LAB-LINUX** · `ACEPTACIÓN-WINDOWS` **pendiente**
**No autoriza:** benchmark T1–T4, prototipos, remedición, implementación productiva, elección de alternativa ni merge.

---

## 0. Qué corrige esta versión

Corrección **exclusivamente documental**. **No se ha ejecutado ninguna medición nueva y ninguna cifra medida ha cambiado.** Solo se corrige la formulación de una tolerancia de almacenamiento que no era tecnológicamente neutral.

| Corrección | v0.2 | v0.3 |
|---|---|---|
| **TOL-104** | Una sola fila: ≤ ×4,0 objetivo y ≤ ×8,0 duro **para todo índice** | Se separa en **TOL-104L** (sustrato léxico, conserva ×4,0/×8,0) y **TOL-104A** (índices semánticos y relacionales, valor congelado por candidato) |
| **Límite agregado** | «derivados ≤ 50 % del fichero» como **límite duro común a T1–T4** | **Eliminado como límite universal.** Se conserva solo como dato comparativo, con su razón metodológica |
| **TOL-203** | «Todo índice adicional **hereda íntegras** las obligaciones de TOL-104, 105 y 106», incluido el ratio léxico | Hereda **las obligaciones de comportamiento**, no el ratio: declara su propio tamaño y su propio límite, congelados antes de ejecutar |

**Sin cambios:** TOL-001–006, B04-M01–M21, TOL-204, TOL-101, 102, 103, 105, 106, 107, 201, 202 y 205; todas las mediciones de las rondas 02 y 02B; y el alcance LAB-LINUX con aceptación Windows pendiente.

### 0.1 Por qué era un defecto de neutralidad

Las cifras ×4,0 y ×8,0 proceden **exclusivamente de dos índices léxicos de Sirius 0.1**: `knowledge_fts` (×3,54, autocontenida) y `message_fts` (×0,71, external content). Son buenas cifras para lo que miden, y siguen vigentes para lo que miden.

Pero **T1–T4 incorporan obligatoriamente señal semántica tardía** —lo exige B04-RF-17, no lo elige ADR-002— y **T2 y T4 pueden incorporar además un índice relacional derivado**. Un vector, incluso razonablemente compacto, puede ocupar más de ocho veces el texto corto que representa: no porque el diseño sea peor, sino porque un índice invertido de términos y una representación densa de significado tienen naturalezas físicas distintas.

Aplicar el mismo ratio a ambos **no es neutral**: **preselecciona dimensión, precisión, cuantización, extensión vectorial y representación relacional** antes de que ADR-002 las haya comparado. Un techo de ×8 sobre el canon descarta de antemano familias enteras de configuraciones legítimas, y lo hace por una cifra derivada de una tecnología distinta.

**La puerta 7 de ADR-002 exige coste compatible con las tolerancias, no que todos los índices guarden la misma relación física que FTS5.** Esta corrección devuelve la decisión a donde corresponde: cada candidato declara y congela su propio límite antes de ejecutarse, y responde de él.

---

## 1. Cómo leer este Registro

### 1.1 Estados

| Estado | Significado |
|---|---|
| `CANÓNICA` | Ya aprobada en B04/PDP. Se reproduce literalmente. **No se toca.** |
| `DERIVADA_CANÓNICA` | Su valor **se deduce sin margen** de una regla canónica. No es propuesta y no se negocia por candidato. |
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

Reproducidos literalmente. **Estado: `CANÓNICA` en las seis. Sin cambios respecto de la v0.2.**

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

Reproducidos literalmente. **Estado: `CANÓNICA` en las veintiuna. Sin cambios respecto de la v0.2. Estas cifras no se rebajan por resultados de la línea base.**

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

**Sin cambios respecto de la v0.2.**

| Campo | Contenido |
|---|---|
| **Ámbito / responsable** | ADR-002, derivada del contrato canónico de suficiencia y de **B04-M01** |
| **Regla canónica de la que deriva** | La expansión continúa cuando falta suficiencia **o queda un crítico elegible pendiente**. S1 solo opera en cardinalidad `EXACTA` o `ACOTADA` **tras comprobar que no queda ningún crítico elegible pendiente** en espacios autorizados. Una consulta `EXHAUSTIVA` **nunca** termina por S1. M01 exige 100 % de críticos recuperados por caso |
| **Métrica y fórmula** | `críticos elegibles pendientes en espacios autorizados` al adjudicar suficiencia |
| **Objetivo** | **0** |
| **Límite duro** | **0. Sin margen.** |
| **Fundamento** | No es propuesta: se deduce sin margen del contrato canónico |
| **Qué decide el candidato** | Únicamente **cómo** implementa y demuestra la comprobación. **Nunca el umbral** |
| **Comportamiento bajo límite duro** | Si el límite duro impide incluir críticos elegibles, estos **se contabilizan** y la salida es **`PARCIAL` visible**. Nunca se adjudica suficiencia completa, y el desbordamiento **no puede ocultarse** (RF-24) |
| **Punto de congelación** | Ya congelada. No se renegocia |
| **Estado** | **`DERIVADA_CANÓNICA`** |
| **Consecuencia de fallo** | Adjudicar suficiencia con un crítico elegible pendiente incumple M01 y el contrato de suficiencia: **descarta**. Omitir críticos sin contabilizarlos ni marcar `PARCIAL` incumple además M21 |
| **Estado en la línea base** | `AUSENTE`: Sirius 0.1 no tiene criticidad, ni suficiencia, ni salida parcial visible |

---

## 5. Valores propuestos — alcance LAB-LINUX

### ADR002-TOL-101 · Latencia del sustrato léxico · `LAB-LINUX`

**Sin cambios respecto de la v0.2.**

| Campo | Contenido |
|---|---|
| **Métrica** | Latencia de una consulta al índice léxico, ms, percentiles nearest-rank |
| **Escenario** | Corpus de referencia (5.000 mensajes, 500 recuerdos); linux x86_64; head `61be4bb269bf` |
| **Repeticiones** | n=100 por escenario, warm-up 5 |
| **Dato observado** | P50 0,172–0,576 ms · P95 0,209–0,730 ms · P99 0,251–1,415 ms |
| **Objetivo** | **P95 ≤ 1,5 ms** |
| **Límite duro** | **P99 ≤ 5 ms** |
| **Margen** | ×2,05 sobre el peor P95; ×3,5 sobre el peor P99 |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos |
| **Estado** | `PROPUESTA` · `LAB-LINUX` |
| **Consecuencia de fallo** | No descarta por sí sola; combinada con TOL-102, descarta |

### ADR002-TOL-102 · Latencia de la recuperación completa · `LAB-LINUX`

**Sin cambios respecto de la v0.2.**

| Campo | Contenido |
|---|---|
| **Métrica** | Latencia extremo a extremo, ms, sin incluir construcción de fixtures |
| **Repeticiones** | n=30 por escenario × 5 sesiones independientes |
| **Dato observado** | P50 113,3–128,6 ms · P95 125,1–147,2 ms · P99 129,0–154,4 ms |
| **Objetivo** | **P95 ≤ 150 ms** |
| **Límite duro** | **P99 ≤ 250 ms** |
| **Margen** | Objetivo +1,9 % sobre el peor P95 observado: **techo de no regresión**. Límite duro ×1,6 sobre el peor P99 |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos |
| **Estado** | `PROPUESTA` · `LAB-LINUX` |
| **Consecuencia de fallo** | Superar el límite duro descarta por la puerta 7 |
| **Advertencia** | El **99,85 %** de esta latencia es el barrido que **B04-RF-14 prohíbe**. Un candidato conforme debería estar holgadamente por debajo |

### ADR002-TOL-103 · Estabilidad ante entradas idénticas · trasladable

**Sin cambios respecto de la v0.2.**

| Campo | Contenido |
|---|---|
| **Métrica** | Órdenes y conjuntos distintos al repetir la **misma** consulta |
| **Repeticiones** | n=30 intra-sesión × 3 escenarios, y **5 sesiones independientes** |
| **Dato observado** | **1 orden y 1 conjunto** en todos los casos, intra-sesión **y entre sesiones** |
| **Objetivo** | **100 % orden idéntico y conjunto idéntico** |
| **Límite duro** | **Idéntico. Cualquier variación es fallo** |
| **Margen** | **Ninguno.** No rebaja TOL-001, que gobierna entradas *equivalentes*: esta fila gobierna entradas *idénticas* |
| **Estado** | `PROPUESTA` · **propiedad de comportamiento, trasladable a Windows** |
| **Consecuencia de fallo** | Descarta por la puerta 4 |

### ADR002-TOL-104L · Tamaño del **sustrato léxico** · `LAB-LINUX`

**Corregida en la v0.3: era ADR002-TOL-104, aplicable a todo índice. Ahora aplica solo al sustrato léxico.**

| Campo | Contenido |
|---|---|
| **Ámbito de aplicación** | **Exclusivamente** el índice léxico: FTS5 o el índice léxico alternativo comparable de T3/T4. **No aplica a embeddings, vectores ni índices relacionales** |
| **Métrica** | `bytes del índice y sus sombras ÷ bytes del canon léxico que indexa`, vía `dbstat` |
| **Dato observado** | `knowledge_fts` **×3,54** (autocontenida) · `message_fts` **×0,71** (external content) |
| **Objetivo** | **≤ ×4,0** sobre el canon léxico que cubre |
| **Límite duro** | **≤ ×8,0** |
| **Margen** | +13 % sobre el peor caso léxico observado (×3,54); ×2 para el límite duro |
| **Punto de congelación** | Antes del benchmark, común a todos los candidatos **en su sustrato léxico** |
| **Estado** | `PROPUESTA` · `LAB-LINUX` |
| **Consecuencia de fallo** | No descarta por sí sola; combinada con la puerta 5, descarta |
| **Nota** | El contraste ×3,54 frente a ×0,71 es el precio de guardar contenido canónico dentro del derivado. Si 0.2 prohíbe retener contenido en claro, deja de ser tolerancia de tamaño y pasa a restricción de diseño |
| **Advertencia de alcance** | Estas cifras **no se extrapolan** a ningún otro tipo de índice. Extrapolarlas equivaldría a preseleccionar técnicas que ADR-002 aún no ha comparado |

### ADR002-TOL-104A · Tamaño de **índices semánticos y relacionales** · por candidato

**Nueva en la v0.3.** Sustituye la aplicación indebida del ratio léxico a índices de otra naturaleza.

| Campo | Contenido |
|---|---|
| **Ámbito de aplicación** | Todo índice **no léxico**: representaciones semánticas de T1–T4 y el índice relacional derivado de T2/T4 |
| **Regla** | **No existe un ratio universal derivado de la línea base léxica.** Cada candidato **declara y congela su propio límite de almacenamiento antes de ejecutarse**, y responde de él |
| **Ficha obligatoria, congelada antes de la primera ejecución** | 1. tipo de índice · 2. datos canónicos que cubre · 3. número de elementos · 4. dimensiones o estructura equivalente · 5. precisión o representación · 6. bytes totales · 7. bytes por elemento · 8. ratio respecto del canon que cubre · 9. porcentaje del fichero total · 10. crecimiento observado o esperado a **500, 5.000 y 50.000** unidades cuando aplique · 11. tiempo y espacio de construcción y reconstrucción · 12. **límite duro del candidato y su fundamento** · 13. comportamiento de borrado |
| **Dato observado** | **Ninguno.** No se ha medido ningún índice semántico ni relacional en ninguna ronda |
| **Punto de congelación** | **Con cada candidato, antes de la primera ejecución.** La ficha y su límite **no pueden ajustarse después de observar resultados** |
| **Estado** | **`REGLA_CONFIRMADA_VALOR_CANDIDATO`** |
| **Por qué no se fija un valor aquí** | Un vector, incluso compacto, puede ocupar más de ocho veces el texto corto que representa. Fijar un ratio desde FTS5 **preseleccionaría dimensión, precisión, cuantización, extensión vectorial y representación relacional** antes de compararlas. La puerta 7 exige coste compatible, no paridad física con FTS5 |

#### 5.1 Cuándo el almacenamiento sí descarta a un candidato

**El almacenamiento es métrica comparativa, no sesgo técnico.** Un candidato **no** se descarta únicamente por superar el ratio del índice léxico.

**Sí** se descarta cuando:

1. incumple el límite de almacenamiento que **él mismo declaró y congeló**;
2. su crecimiento **no es acotado** o **no es explicable**;
3. **no cabe** en el entorno local de referencia, cuando este quede fijado;
4. **no puede reconstruirse desde el canon**;
5. **no puede borrarse completamente**;
6. **acopla** el sistema a un proveedor o a un formato no portable;
7. el coste adicional **no produce mejora material** frente a alternativas más simples.

Los criterios 4, 5 y 6 son puertas ya existentes (5 y 6 de ADR-002); los criterios 1, 2, 3 y 7 son los que esta fila añade, y ninguno depende de una cifra heredada de otra tecnología.

#### 5.2 El límite agregado del 50 % deja de ser universal

La v0.2 fijaba «suma de derivados ≤ 50 % del fichero» como **límite duro común a T1–T4**. **Se elimina como límite universal.**

**Se conserva como dato comparativo:** en la línea base medida, los derivados suman el **24,9 %** del fichero.

**Razón metodológica:** el tamaño del fichero canónico depende del corpus y de la longitud media del texto, mientras que un índice vectorial depende principalmente del número de elementos, las dimensiones y la precisión. El porcentaje del fichero puede variar radicalmente **sin que la arquitectura sea peor**. Un límite expresado como fracción del canon penaliza corpus de textos cortos y premia corpus de textos largos, sin relación con la calidad del diseño.

**Dónde vive la restricción real:** la eventual restricción **absoluta** de almacenamiento local pertenece al **entorno de referencia**, y debe congelarse antes del benchmark o, para aceptación, sobre Windows. Ver ADR002-TOL-205.

### ADR002-TOL-105 · Ciclo del índice desde el canon · `LAB-LINUX` + trasladable

**Sin cambios respecto de la v0.2.**

| Campo | Contenido |
|---|---|
| **Métrica** | Tiempo de borrado, construcción y reconstrucción **desde el canon**, ms; y booleano de restitución idéntica |
| **Escenario** | **30 repeticiones**, cada una sobre copia limpia independiente preparada fuera del cronómetro; 2 de warm-up descartadas |
| **Dato observado** | Borrado P50 43,6 · P95 84,3 · P99 122,9 — Construcción P50 51,9 · P95 96,6 · P99 102,6 — **Reconstrucción P50 29,3 · P95 41,7 · P99 44,5** |
| **Objetivo** | Reconstrucción desde el canon **P95 ≤ 60 ms**; construcción **P95 ≤ 120 ms**; borrado **P95 ≤ 110 ms** |
| **Límite duro** | **P99 ≤ 150 ms** en cualquiera de las tres · **restitución idéntica: obligatoria, sin margen** |
| **Margen** | ×1,44 sobre el P95 de reconstrucción, ×1,24 sobre el de construcción, ×1,30 sobre el de borrado. Límite duro anclado a la peor cola observada (122,9 ms) + 22 % |
| **Estado** | `PROPUESTA` (tiempos, `LAB-LINUX`) · la **restitución idéntica** deriva de ADR-001 y es **trasladable** |
| **Consecuencia de fallo** | Fallo de restitución **descarta** por la puerta 5. Exceso de tiempo obliga a justificar |
| **Advertencia** | El `rebuild` interno (P50 18,7 ms) reconstruye `knowledge_fts` **desde sí misma**, no desde `memory_revisions`. **No satisface ADR-001**. Su **P99 es 269,9 ms**, seis veces su P95 |
| **Ámbito** | Estos tiempos son del **sustrato léxico**. Los de índices adicionales se congelan por candidato (TOL-203) |

### ADR002-TOL-106 · Borrado y desaparición del derivado · trasladable

**Sin cambios respecto de la v0.2.**

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
| **Nota** | La purga **física** del fichero es un paso distinto y requiere `VACUUM` (spike 10 de ADR-001). Esta fila cubre la desaparición lógica del derivado |

### ADR002-TOL-107 · Variación entre ejecuciones equivalentes · `LAB-LINUX`

**Sin cambios respecto de la v0.2.**

| Campo | Contenido |
|---|---|
| **Métrica** | `(máx − mín) / mín` sobre el mismo percentil en todas las sesiones; y órdenes distintos entre sesiones |
| **Escenario** | **5 sesiones completas independientes**, cada una con fichero, motor, caché y warm-up propios |
| **Dato observado** | **Orden y conjunto: 0 variación**. Latencia `rank()`: **2,8–10,6 % en P50, 12,3–15,8 % en P95**. Latencia FTS5: **13,4–29,3 % en P50, 32,9–36,4 % en P95**. **Peor global: 36,4 %** |
| **Objetivo** | **Orden y conjunto: 0 variación** (sin margen) · **`rank()`: ≤ 20 % en P50 y P95** |
| **Límite duro** | **Orden: 0, sin margen.** **Latencia: `REGLA_CONFIRMADA_VALOR_ENTORNO` — no se fija** |
| **Margen** | ×1,9 sobre el peor P50 y ×1,27 sobre el peor P95 de `rank()`. **Para FTS5 no se propone objetivo relativo**: con magnitudes de 0,14–1,0 ms, un 36 % son 0,27 ms absolutos, es el suelo de medición |
| **Punto de congelación** | Objetivo, antes del benchmark. Límite duro, **con el entorno de ejecución** |
| **Estado** | `PROPUESTA` (objetivo, `LAB-LINUX`) · **`REGLA_CONFIRMADA_VALOR_ENTORNO`** (límite duro) |
| **Consecuencia de fallo** | Latencia: la comparación **no es válida** y debe repetirse; no descarta al candidato. Orden: descarta por la puerta 4 |
| **Por qué no se fija el límite duro** | Las cinco sesiones son independientes **dentro del mismo proceso**, en una máquina cuya carga no se controla. Fijar un techo defendible para otro entorno con esta evidencia sería inventarlo |

---

## 6. Reglas cuyo valor se congela con cada candidato

### ADR002-TOL-201 · Banda temporal de TOL-002

**Sin cambios respecto de la v0.2.**

| Campo | Contenido |
|---|---|
| **Regla canónica** | TOL-002: pares con igual configuración deben caer en la misma banda externa prefijada; cualquier diferencia repetible atribuible a existencia protegida falla. **La banda se congela con el candidato antes de ejecutar** |
| **Forma propuesta de la banda** | **Cuatro** condiciones simultáneas: (1) estado, texto y conteo externos **exactamente equivalentes**; (2) **fracción de signo pareada dentro de [0,40 · 0,60]** con n≥30 por rama; (3) **ausencia de separación material en distribución**, no solo en un estadístico puntual; (4) **repetición en sesión independiente** con el mismo veredicto |
| **Dato observado** | Fracción de signo **0,533** (`rank()`, n=30) y **0,490** (índice, n=100); estado, texto y conteo equivalentes |
| **Por qué no basta un Δ de percentil** | Con n=30 por rama, P95 y P99 son la segunda peor y la peor muestra: los Δ observados **no son interpretables** |
| **Punto de congelación** | **Con cada candidato, antes de ejecutarlo** |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Descarta por la puerta 8; incumple M20 |
| **Advertencia crítica** | La indistinguibilidad observada hoy es **en buena medida accidental**: el barrido constante de 122,5 ms enmascara una diferencia de trabajo ~31.000 veces menor. **Un candidato que elimine el barrido perderá ese enmascaramiento.** El resultado **no se hereda** |

### ADR002-TOL-202 · Coste incremental por etapa E0–E5

**Sin cambios respecto de la v0.2.**

| Campo | Contenido |
|---|---|
| **Regla** | Cada etapa declara su coste incremental en tiempo y operaciones locales; el coste externo se declara **aparte** y nunca se mezcla con el local |
| **Dato observado** | **Ninguno. No medible en la línea base:** Sirius 0.1 no tiene etapas |
| **Punto de congelación** | Con cada candidato que implemente E0–E5, antes de ejecutarlo |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Un candidato que no pueda declarar el coste por etapa no es evaluable contra RF-14 y no puede compararse |

### ADR002-TOL-203 · Obligaciones de todo índice adicional

**Corregida en la v0.3.** La v0.2 decía que todo índice adicional «hereda íntegras las obligaciones de TOL-104, 105 y 106», lo que arrastraba el ratio léxico ×4/×8 a índices de otra naturaleza.

| Campo | Contenido |
|---|---|
| **Qué hereda un índice adicional** | **Obligaciones de comportamiento, no el ratio léxico.** En concreto: 1. **declaración completa de tamaño** conforme a la ficha de TOL-104A · 2. **límite propio, declarado y congelado** por el candidato antes de ejecutarse · 3. **reconstrucción desde el canon** · 4. **desaparición completa**, incluidas todas sus estructuras auxiliares · 5. **al menos 30 repeticiones** para los tiempos de ciclo, cuando sean ejecutables · 6. **tasa de éxito del 100 %** en restitución, integridad y borrado |
| **Qué NO hereda** | **El ratio ×4,0 / ×8,0 de ADR002-TOL-104L.** Esas cifras son del sustrato léxico y no se extrapolan |
| **Dato observado** | Solo para los dos índices léxicos de la línea base; **ningún índice semántico ni relacional medido** |
| **Punto de congelación** | Con cada candidato, antes de ejecutarlo. El límite no puede ajustarse tras observar resultados |
| **Estado** | `REGLA_CONFIRMADA_VALOR_CANDIDATO` |
| **Consecuencia de fallo** | Incumplir 3, 4 o 6 **descarta** por la puerta 5. Incumplir 1 o 2 impide evaluar al candidato: sin declaración congelada no hay nada contra lo que medir. Incumplir 5 deja los tiempos sin evidencia utilizable |

### ADR002-TOL-205 · Aceptación sobre Windows

**Sin cambios respecto de la v0.2.**

| Campo | Contenido |
|---|---|
| **Regla** | Ninguna cifra `LAB-LINUX` de latencia, tamaño o ciclo se traslada automáticamente. Antes de aceptar la implementación hay que confirmar el comportamiento sobre el ejecutable o entorno de referencia Windows, incluidos tokenizador, `secure_delete` y secuencia de purga |
| **Dato observado** | **Ninguno.** No se ha medido en Windows en ninguna ronda |
| **Qué sí se traslada** | Las comprobaciones booleanas: restitución idéntica, `integrity-check`, desaparición completa del derivado, estabilidad de orden y conjunto |
| **Punto de congelación** | Antes de aceptar la implementación productiva |
| **Estado** | **`REGLA_CONFIRMADA_VALOR_ENTORNO`** |
| **Consecuencia de fallo** | Presentar cifras Linux como aceptación del producto Windows invalida la aceptación |
| **Nota añadida en la v0.3** | La **restricción absoluta de almacenamiento local** —cuánto puede ocupar el conjunto en el equipo del usuario— pertenece a esta fila y al entorno de referencia, **no** a un porcentaje del fichero canónico. Ver §5.2 |

---

## 7. Dependencias que no decide ADR-002

**Sin cambios respecto de la v0.2.**

| ID | Ámbito | Tratamiento |
|---|---|---|
| **TOL-003** | Carga e interrupciones | `NO_APLICA_ADR002` |
| **TOL-004** | Coste contextual UCC | `NO_APLICA_ADR002`. Pertenece a **ADR-003B** |
| **TOL-006** | Comprensión de operaciones | `NO_APLICA_ADR002` |
| **RED-040** | Reintento acotado entre recuperación y contexto | `NO_APLICA_ADR002`. Pertenece a **B05/ADR-003B**. ADR-002 solo **registra la interfaz** |

---

## 8. Punto de congelación — regla de proceso

**Antes del benchmark**, comunes a todos los candidatos: ADR002-TOL-101, 102, 103, **104L**, 105, 106 y el **objetivo** de 107, más todas las filas `CANÓNICA` y la `DERIVADA_CANÓNICA` TOL-204.

**Con cada candidato, antes de ejecutarlo**: ADR002-TOL-**104A**, 201, 202 y 203.

**Con el entorno de ejecución**: el **límite duro** de ADR002-TOL-107 y ADR002-TOL-205, incluida la restricción absoluta de almacenamiento local.

**Reglas duras:**

1. Ningún valor se fija **después** de observar el resultado del candidato. Un valor congelado tarde no es tolerancia: es justificación a posteriori.
2. Los valores congelados por candidato se registran en la ficha del caso **antes** de la primera ejecución.
3. Un umbral canónico **nunca** se rebaja. Si un candidato no lo alcanza, falla el candidato.
4. **TOL-204 no se renegocia**: cero críticos elegibles pendientes es derivación canónica.
5. **El ratio de TOL-104L no se extrapola** a índices no léxicos. Cada índice adicional responde de su propio límite declarado.
6. Cambiar cualquier valor obliga a **repetir** las comparaciones ya ejecutadas bajo el valor anterior.

---

## 9. Estado de aprobación

**Este Registro está `PROPUESTO` y no está aprobado.** Requiere decisión explícita del usuario.

| Estado | Filas |
|---|---|
| `CANÓNICA` | TOL-001, TOL-002, TOL-005 (y TOL-003, TOL-004, TOL-006 como dependencia) · B04-M01–M21 |
| `DERIVADA_CANÓNICA` | ADR002-TOL-204 |
| `PROPUESTA` | ADR002-TOL-101, 102, 103, **104L**, 105, 106 · objetivo de 107 |
| `REGLA_CONFIRMADA_VALOR_CANDIDATO` | ADR002-TOL-**104A**, 201, 202, 203 |
| `REGLA_CONFIRMADA_VALOR_ENTORNO` | Límite duro de ADR002-TOL-107 · ADR002-TOL-205 |
| `NO_APLICA_ADR002` | TOL-003, TOL-004, TOL-006, RED-040 |

**Ningún umbral canónico ha sido modificado ni rebajado.** **Ninguna medición ha cambiado ni se ha ejecutado ninguna nueva.** Todas las cifras medidas siguen siendo **`LAB-LINUX`**; la **`ACEPTACIÓN-WINDOWS` sigue pendiente**.

### 9.1 Neutralidad tecnológica de esta versión

La corrección de la v0.3 existe para que el Registro **no elija por adelantado**:

- ninguna **dimensión** de representación semántica;
- ninguna **precisión** ni **cuantización**;
- ninguna **extensión vectorial** concreta;
- ninguna **representación relacional** concreta;
- ningún **formato de índice** que no sea el léxico ya medido.

El almacenamiento pasa a ser lo que debe ser en ADR-002: **una métrica comparativa que cada candidato declara, congela y justifica**, sujeta a las puertas de reconstrucción, borrado y portabilidad que sí son comunes. Es exactamente lo que **B04-RF-31** y la **puerta 6** exigen, y lo que la formulación de la v0.2 comprometía sin querer.

---

**Siguiente movimiento único:** que el usuario apruebe, corrija o rechace las filas `PROPUESTA`, confirme la derivación canónica de TOL-204 y valide la separación entre TOL-104L y TOL-104A. Hasta entonces no se construye corpus de benchmark, no se implementa ningún prototipo y no se ejecuta ningún candidato.
