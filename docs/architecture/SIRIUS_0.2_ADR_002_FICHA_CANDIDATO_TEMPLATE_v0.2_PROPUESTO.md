# SIRIUS 0.2 — ADR-002 · Ficha de candidato · plantilla

**Versión:** 0.2
**Estado:** **PROPUESTO** · plantilla, **no está aprobada** y no autoriza nada por sí misma
**Fecha:** 26 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.1_PROPUESTO.md`, que **se conserva sin modificar** y cuya aprobación del 26 de julio de 2026 se respeta como historial
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_03A_RESOLUCION_PARTICION_CANDIDATOS_v0.1.md` §4.3
**Autoridad de la corrección:** `SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md` y `SIRIUS_0.2_ADR_002_NOTA_SUPERACION_02_PARTICION_CANDIDATOS_v1.0_APROBADA.md`
**Exigida por:** `ADR002-TOL-210` del `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md`, leído conforme a la nota de superación 02 §2.1
**No autoriza:** ejecutar el benchmark, ejecutar T0, implementar prototipos, elegir alternativa ni merge.

---

## 0. Por qué existe este artefacto

La regla de congelación es el mecanismo antitrampa de todo el Registro de Tolerancias: **ningún valor puede fijarse después de observar el resultado del candidato**. Hasta la v0.3 del Registro, esa regla decía que los valores congelados por candidato «se registran en la ficha del caso antes de la primera ejecución».

**La ficha del caso no podía alojarlos.** Es el artefacto de la Especificación de benchmark §5: trece campos que describen un **caso de prueba** —entrada, modo, ámbito, tiempo, candidatos elegibles y prohibidos, orden esperado, razón, métrica, evidencia, cardinalidad, etapa y parada—. Ninguno describe al **candidato**. La regla apuntaba a un contenedor equivocado, y su cumplimiento no era auditable.

Esta ficha es ese contenedor. Es un artefacto **propio del candidato**, no del caso: se escribe una vez por candidato, se confirma en el repositorio **antes de su primera ejecución**, y **cada ejecución la referencia** por ID, versión y huella.

### 0.1 Qué corrige la v0.2

**Solo la identificación del candidato y las declaraciones que dependen de ella.** Todas las reglas de congelación, límites, magnitudes, escalas comunes, advertencias y verificaciones de la v0.1 se conservan íntegras.

| Punto | v0.1 | **v0.2** |
|---|---|---|
| Universo de fichas | `T1`, `T2`, `T3`, `T4` + `T0-control` | **`ADR002-A`, `ADR002-B`, `ADR002-C`, `ADR002-D`** + `T0-control` |
| Realización técnica | `‹T1 · T2 · T3 · T4›` según ADR-002 §3 | **Alternativa mínima** de ARQ-00 §23, según la Resolución v1.0 |
| Señal semántica tardía | «es obligatoria por B04-RF-17, **no es una elección**» | **Obligatoria es la etapa `E3`. La señal tardía habilitada es lo que distingue a cada alternativa** |
| Orden de etapas tardías | No se declaraba | **Campo obligatorio nuevo** (§2.2 bis) |
| Restricción de `ADR002-D` | No existía | **Bloque obligatorio nuevo** (§2.2 ter) |
| §2.6 sustrato alternativo | «solo si … (T3, T4)» | «solo si el sustrato léxico **no es el FTS5 medido**» — condición, no etiqueta |

---

## 1. Reglas de uso

1. **Una ficha por candidato.** `ADR002-A`, `ADR002-B`, `ADR002-C` y `ADR002-D` tienen fichas distintas. **`T0` tiene la suya, marcada como control de falsación**, y no es candidato.
2. **Confirmada antes de la primera ejecución.** Una ficha creada o modificada después de observar cualquier resultado del candidato **no es una ficha**: es justificación a posteriori, y el Registro v0.4 §9 regla 1 la prohíbe.
3. **Completa o inexistente.** Un campo vacío o «pendiente» invalida la ficha. Si un valor no puede declararse, se declara **por qué** y esa imposibilidad se congela igual.
4. **Versionada.** Cualquier modificación posterior obliga a **nueva versión** de ficha y a **repetir** las ejecuciones ya realizadas bajo la anterior (Registro v0.4 §9 reglas 2 y 10).
5. **Referenciada desde cada ejecución.** El registro de evidencia de cada ejecución cita `id · versión · huella`. Una ejecución que no referencie una ficha previa **no es utilizable como evidencia**.
6. **No sustituye a la ficha del caso.** Ambas coexisten: la del caso describe qué se prueba, esta describe contra qué límites se juzga al candidato.
7. **No contiene resultados.** Esta ficha contiene **límites y declaraciones**, nunca mediciones del propio candidato. Los resultados viven en el registro de ejecución.
8. **Ninguna alternativa mínima puede fichar como control.** `ADR002-A`, `ADR002-B`, `ADR002-C` y `ADR002-D` son candidatos completos: la ficha de cada una se rellena con el mismo rigor y se juzga con las mismas puertas. **Marcar `ADR002-A` o `ADR002-C` como control invalida la ficha** (Resolución v1.0 §2.1 y §2.2).

---

## 2. Plantilla

> Copiar íntegra. Sustituir cada `‹…›`. No borrar ningún encabezado: un apartado vacío debe decir expresamente por qué lo está.

---

### 2.1 Identidad

| Campo | Valor |
|---|---|
| **ID de candidato** | `‹ADR002-A · ADR002-B · ADR002-C · ADR002-D · T0-control›` |
| **Versión de ficha** | `‹v0.1›` |
| **Fecha de congelación** | `‹AAAA-MM-DD›` |
| **Commit de confirmación** | `‹sha›` |
| **Huella de la ficha** | `‹hash del fichero en el momento de congelar›` |
| **Estado** | `CONGELADA` / `SUSTITUIDA POR ‹versión›` |
| **Sustituye a** | `‹versión anterior o "ninguna"›` · motivo: `‹…›` |
| **Papel** | `‹CANDIDATO · CONTROL DE FALSACIÓN›` — solo `T0` puede declararse control |

### 2.2 Arquitectura declarada

| Campo | Valor |
|---|---|
| **Alternativa mínima** | `‹ADR002-A · ADR002-B · ADR002-C · ADR002-D›` según **ARQ-00 §23** y la Resolución de la partición de candidatos v1.0 §2 |
| **Definición canónica que asume** | `‹transcribir literalmente la fila correspondiente de ARQ-00 §23›` |
| **Sustrato léxico** | `‹FTS5 medido · alternativo: nombre y versión›` |
| **Materialización de relaciones** | `‹desde el canon · índice relacional derivado›` |
| **Puerto de acceso** | `‹equivalente a KnowledgeSearchRepository; obligatorio por RF-31 y la puerta 6›` |
| **Etapas E0–E5 implementadas** | `‹mapa de qué ocurre en cada etapa y qué condición de insuficiencia autoriza la transición›` |

#### 2.2 bis · Señal tardía habilitada y orden de etapas — **obligatorio**

**Es lo que distingue a cada alternativa mínima.** La **etapa `E3`** es obligatoria para todos los candidatos, con validación explícita de sujeto, polaridad, condición y tiempo (`B04-RF-17`). **Una señal semántica vectorial NO es obligatoria**: `B04-RF-31` y B04 §8 prohíben convertir una obligación de comportamiento en una realización predeterminada.

| Campo | Valor |
|---|---|
| **Señal tardía habilitada** | `‹ninguna adicional (A) · semántica vectorial (B) · relacional explícita (C) · ambas en etapas distintas (D)›` |
| **Coherencia con la alternativa declarada** | `‹debe coincidir exactamente con §2.2; una discrepancia invalida la ficha›` |
| **Cómo satisface E3 este candidato** | `‹obligatorio también para ADR002-A: por qué medios léxico-estructurados se buscan paráfrasis, dependencias, apoyo/refutación y relaciones›` |
| **Validación de sujeto, polaridad, condición y tiempo en E3** | `‹mecanismo concreto; no se hereda de la señal›` |
| **Orden declarado de las etapas tardías** | `‹secuencia exacta y congelada; para A escribir "no aplica: sin señal tardía adicional"›` |
| **Condición de insuficiencia que autoriza cada transición tardía** | `‹una por transición›` |

#### 2.2 ter · Restricción propia de `ADR002-D` — **obligatorio para D**

> Rellenar **solo** si la alternativa declarada es `ADR002-D`. En cualquier otro caso escribir «No aplica: la alternativa declarada no habilita dos señales tardías».

`ADR002-D` **no es `B` más `C`**. Sus tres restricciones son acumulativas y su anclaje es `B04-D15`, que prohíbe adelantar espacios posteriores y sustituir la política escalonada.

| # | Restricción canónica (ARQ-00 §23) | Declaración |
|---|---|---|
| 1 | Señales semántica y relacional en **etapas tardías distintas** | `‹qué señal en qué etapa›` |
| 2 | **Orden predefinido**, congelado antes de ejecutar | `‹orden exacto y su fundamento›` |
| 3 | **Nunca coordinación simultánea fuera de la etapa autorizada** | `‹cómo se impide técnicamente, no solo por convención›` |

| Campo | Valor |
|---|---|
| **Cómo se demuestra el cumplimiento en cada ejecución** | `‹traza que evidencia la etapa de cada señal y la ausencia de coordinación simultánea›` |
| **Traza a `B04-D15`** | `‹cómo se garantiza que la coordinación solo combina señales del mismo espacio y familia de la etapa activa›` |

**Consecuencia:** un `ADR002-D` que coordine ambas señales simultáneamente, o que no respete el orden aquí congelado, **incumple `B04-D15` y la puerta 9** aunque sus resultados sean perfectos.

#### 2.2 quater · Declaración obligatoria de puertas previas comunes

No son ventaja de ningún candidato y ninguno puede omitirlas (ADR-002 v0.3 §3.5):

| Puerta previa | Cómo la satisface este candidato |
|---|---|
| Aislamiento de ámbito antes de candidatos (RF-06, RF-09) | `‹…›` |
| Expansión escalonada sin salto (RF-14, RF-15, RF-16) | `‹…›` |
| Validación de sujeto, polaridad, condición y tiempo (RF-17, RF-19) | `‹…›` |
| Borrado y regeneración completos desde el canon (ADR-001 c.2, c.3) | `‹…›` |
| Petición completa y operación activa (RF-01, RF-30) | `‹…›` |
| Plan reproducible y explicación por resultado (RF-22, RF-28, RF-29) | `‹…›` |

### 2.3 Componentes y versiones

| Componente | Nombre | Versión | Origen | ¿Acopla a proveedor? |
|---|---|---|---|---|
| Motor de base | `‹›` | `‹›` | `‹›` | `‹sí/no + fundamento›` |
| Índice léxico | `‹›` | `‹›` | `‹›` | `‹›` |
| Representación semántica | `‹›` | `‹›` | `‹›` | `‹›` |
| Índice relacional | `‹›` | `‹›` | `‹›` | `‹›` |
| Otros | `‹›` | `‹›` | `‹›` | `‹›` |

> Un candidato que no declara una representación semántica o un índice relacional escribe «No aplica: la alternativa declarada no lo habilita». **No declararlo no es un déficit**: es la alternativa que se está poniendo a prueba.

**Puerta 6 de ADR-002 (RF-31):** el acoplamiento a un proveedor o formato no portable descarta. Declarar aquí cualquier dependencia y su ruta de sustitución.

### 2.4 Corpus y entorno — `ADR002-TOL-208`

| Campo | Valor |
|---|---|
| **Versión de corpus** | `‹›` |
| **Mensajes / recuerdos / decisiones / proyectos** | `‹› / ‹› / ‹› / ‹›` |
| **Longitud media y distribución del texto** | `‹›` |
| **Commit del corpus y de la configuración** | `‹›` |
| **Head de Alembic o equivalente** | `‹›` |
| **T0 rederivada sobre este mismo corpus** | `‹sí — referencia de la ejecución›` |

**Prohibido** reutilizar cifras del corpus 5.000/500 de la remedición 02B sobre otro volumen sin rederivar.

### 2.5 Protocolo de medición — `ADR002-TOL-209`

| Campo | Valor |
|---|---|
| **Protocolo aplicado** | `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v‹›` |
| **Desviaciones respecto del protocolo** | `‹ninguna · lista con fundamento›` |
| **Entorno de laboratorio** | `‹máquina, SO, carga controlada o no›` |
| **Semilla fija** | `‹›` |
| **Posición en el orden intercalado** | `‹el protocolo §5.2 exige intercalar candidatos; declarar la secuencia acordada›` |

Toda desviación no declarada **antes** de ejecutar invalida las cifras del candidato.

### 2.6 Sustrato léxico alternativo — `ADR002-TOL-101A`

> Rellenar **solo** si el sustrato léxico **no es el FTS5 medido**. Si es el FTS5 medido, escribir «No aplica: sustrato léxico = FTS5 medido; rigen TOL-101L, TOL-104L y los tiempos de TOL-105».
>
> La condición es el **sustrato**, no la alternativa: cualquiera de `ADR002-A/B/C/D` puede declarar un sustrato alternativo, y en la primera ronda ninguna lo hace (Resolución v1.0 §6.1).

| # | Magnitud | Objetivo congelado | Límite duro congelado | Fundamento |
|---|---|---|---|---|
| 1 | Latencia de consulta (percentil y n) | `‹›` | `‹›` | `‹›` |
| 2 | Tamaño del índice y estructuras auxiliares | `‹›` | `‹›` | `‹›` |
| 3 | Tiempo de construcción desde el canon | `‹›` | `‹›` | `‹›` |
| 4 | Tiempo de reconstrucción desde el canon | `‹›` | `‹›` | `‹›` |
| 5 | Tiempo de borrado completo | `‹›` | `‹›` | `‹›` |
| 6 | Crecimiento a 500 / 5.000 / 50.000 unidades | `‹›` | `‹›` | `‹›` |

**Recordatorio de neutralidad (Registro v0.4 §5.6):** la desviación respecto de FTS5 se informa como **comparación**, no como déficit automático. Superar TOL-101L, TOL-104L o los tiempos de TOL-105 **no descarta** a este candidato. Lo que descarta es incumplir el límite que **él mismo** congeló aquí.

### 2.7 Índices semánticos y relacionales — `ADR002-TOL-104A`

> Una tabla por índice no léxico. Los trece campos son obligatorios. Si el candidato no declara ninguno, escribir «No aplica: la alternativa declarada no habilita índices no léxicos», y esa declaración se congela igual.

**Índice `‹nombre›`**

| # | Campo | Valor |
|---|---|---|
| 1 | Tipo de índice | `‹›` |
| 2 | Datos canónicos que cubre | `‹›` |
| 3 | Número de elementos | `‹›` |
| 4 | Dimensiones o estructura equivalente | `‹›` |
| 5 | Precisión o representación | `‹›` |
| 6 | Bytes totales | `‹›` |
| 7 | Bytes por elemento | `‹›` |
| 8 | Ratio respecto del canon que cubre | `‹›` |
| 9 | Porcentaje del fichero total | `‹›` |
| 10 | Crecimiento a 500 / 5.000 / 50.000 unidades | `‹›` |
| 11 | Tiempo y espacio de construcción y reconstrucción | `‹›` |
| 12 | **Límite duro por magnitud, con fundamento** | tamaño `‹›` · construcción `‹›` · reconstrucción `‹›` · borrado `‹›` |
| 13 | Comportamiento de borrado | `‹›` |

**Escala común obligatoria** — se reporta además de los límites propios, para que los candidatos sigan siendo comparables sin ratio compartido:

| Magnitud | 500 unidades | 5.000 unidades | 50.000 unidades |
|---|---|---|---|
| Bytes totales | `‹›` | `‹›` | `‹›` |
| Bytes por elemento | `‹›` | `‹›` | `‹›` |
| % del presupuesto absoluto (TOL-207) | `‹›` | `‹›` | `‹›` |

### 2.8 Ciclo de todo índice adicional — `ADR002-TOL-203`

| Magnitud | Límite congelado | Fundamento | ¿Ejecutable ≥30 veces? |
|---|---|---|---|
| Tamaño | `‹›` | `‹›` | — |
| Construcción desde el canon | `‹›` | `‹›` | `‹sí/no›` |
| Reconstrucción desde el canon | `‹›` | `‹›` | `‹sí/no›` |
| Borrado completo | `‹›` | `‹›` | `‹sí/no›` |

| Obligación de comportamiento | Declaración |
|---|---|
| Reconstrucción **desde el canon**, no desde el propio derivado | `‹›` |
| Desaparición completa, incluidas todas las estructuras auxiliares | `‹›` |
| Tasa de éxito del **100 %** en restitución, integridad y borrado, sobre **≥30 repeticiones** | `‹›` |
| Purga física sin fragmento recuperable (TOL-206) | `‹›` |

**No ejecutabilidad.** Si alguna operación no es ejecutable 30 veces, declararlo **aquí y ahora**, con fundamento. Invocarlo después de ejecutar equivale a no haber declarado el límite:

> `‹operación› no es ejecutable ≥30 veces porque ‹fundamento técnico›. Evidencia alternativa propuesta: ‹…›`

### 2.9 Coste por etapa — `ADR002-TOL-202`

| Etapa | Coste incremental local (objetivo / límite duro) | Operaciones locales | Coste externo, **declarado aparte** |
|---|---|---|---|
| E0 | `‹›` | `‹›` | `‹›` |
| E1 | `‹›` | `‹›` | `‹›` |
| E2 | `‹›` | `‹›` | `‹›` |
| E3 | `‹›` | `‹›` | `‹›` |
| E4 | `‹›` | `‹›` | `‹›` |
| E5 | `‹›` | `‹›` | `‹›` |

| Campo | Valor |
|---|---|
| **Coste de inferencia o generación de la señal de consulta** | `‹objetivo / límite duro / dónde se ejecuta; "no aplica" si el candidato no genera señal›` |
| **Coste local total** | `‹›` |
| **Coste externo total** | `‹›` — **nunca sumado al local** |
| **Coste extremo a extremo resultante** | `‹›` — debe coincidir con §2.10 |

**Regla de coherencia:** la suma de los costes por etapa debe explicar el coste extremo a extremo declarado. Una discrepancia no explicada **invalida ambas declaraciones**.

### 2.10 Límite extremo a extremo — `ADR002-TOL-102C`

| Campo | Valor |
|---|---|
| **Objetivo P95** | `‹›` |
| **Límite duro P99** | `‹›` |
| **Percentil y n** | `‹nearest-rank; n=›` |
| **Fundamento de ambos valores** | `‹›` |
| **Desglose por etapa que los sostiene** | referencia a §2.9 |

**Prohibiciones expresas:**

- **No** derivar estos valores de TOL-102B ni de ningún «techo razonable» inspirado en T0.
- **Ningún candidato puede invocar el barrido prohibido de T0 como justificación de un coste alto propio.** T0 incumple RF-14 y no es un presupuesto heredable.
- **Ningún candidato puede invocar cifras de otro candidato.** Que `ADR002-A` comparta con `T0` la ausencia de señal vectorial no le hereda ninguna de sus cifras ni ninguno de sus incumplimientos.
- Superar el tiempo de T0 **no descarta**. Incumplir el límite congelado aquí, o el del entorno, **sí**.

### 2.11 Almacenamiento absoluto del entorno — `ADR002-TOL-207`

| Campo | Valor |
|---|---|
| **Presupuesto absoluto congelado del laboratorio (bytes)** | `‹›` |
| **Consumo total declarado por este candidato (bytes)** | `‹›` |
| **Porcentaje del presupuesto** | `‹›` |
| **Proyección a 50.000 unidades** | `‹›` |
| **¿Cabe?** | `‹sí/no›` |

Si no cabe, el candidato queda descartado por §5.1 criterio 3 del Registro y la puerta 7.

> **Nota de estado:** `ADR002-TOL-207` **no está aprobada**. Esta plantilla no fija ninguna cifra y no la da por congelada.

### 2.12 Estabilidad — `ADR002-TOL-107`

| Campo | Valor |
|---|---|
| **Régimen aplicable** | `‹relativo · absoluto›` según el umbral de conmutación congelado |
| **Umbral de conmutación en vigor** | `‹›` |
| **Banda absoluta en vigor** | `‹›` |
| **Sesiones independientes previstas** | `‹≥5›` |

Si la comparación resulta inválida, **se repite una única vez** en condiciones controladas. Si vuelve a fallar, el candidato queda **`NO EVALUABLE` en rendimiento**, y así se registra.

### 2.13 Banda temporal e indistinguibilidad — `ADR002-TOL-201` y `TOL-002`

| Condición | Valor congelado |
|---|---|
| (1) Estado, texto y conteo externos exactamente equivalentes | `‹cómo se comprueba›` |
| (2) Fracción de signo pareada dentro de [0,40 · 0,60], n≥30 por rama | `‹›` |
| (3) Ausencia de separación material en distribución | `‹prueba concreta›` |
| (4) Repetición en sesión independiente con el mismo veredicto | `‹›` |

**Modelo de amenaza declarado:** `‹observador, capacidades, qué no se modela›`

**Advertencia obligatoria de lectura.** La indistinguibilidad observada en la línea base es **en buena medida accidental**: el barrido constante de 122,5 ms enmascara una diferencia de trabajo ~31.000 veces menor. **Un candidato que elimine el barrido, como RF-14 exige, perderá ese enmascaramiento. El resultado no se hereda.**

### 2.14 Purga física — `ADR002-TOL-206`

| Campo | Valor |
|---|---|
| **Secuencia declarada de purga** | `‹checkpoint · journal · VACUUM · …›` |
| **Ficheros cubiertos** | `.db` · `-wal` · `-shm` · `-journal` |
| **Qué payload literal o representación reversible contiene el derivado** | `‹›` |
| **Modelo de amenaza** | `‹no puede ser más débil que el de ADR-001›` |
| **Comprobación propuesta** | `‹cómo se demuestra que no queda fragmento recuperable›` |

### 2.15 Huella del candidato

| Campo | Valor |
|---|---|
| **Commit del prototipo** | `‹›` |
| **Hash del árbol de fuentes del candidato** | `‹›` |
| **Migraciones o DDL aplicados** | `‹›` |
| **Artefactos generados y su hash** | `‹›` |
| **Reproducción** | `‹comandos exactos›` |

### 2.16 Declaración final de congelación

> Declaro que los valores de esta ficha se han fijado **antes** de la primera ejecución de este candidato, que no proceden de ningún resultado observado del propio candidato, y que cualquier modificación posterior obligará a nueva versión de ficha y a repetir las ejecuciones ya realizadas.

| Campo | Valor |
|---|---|
| **Responsable** | `‹›` |
| **Fecha** | `‹›` |
| **Commit** | `‹›` |

---

## 3. Verificación antes de ejecutar

Ninguna ejecución puede comenzar si alguna casilla queda sin marcar:

- [ ] Puertas de arranque satisfechas: `SRC-ADR002-01`, TOL-207, TOL-208, TOL-209, TOL-210.
- [ ] **ID de candidato dentro del universo oficial**: `ADR002-A`, `ADR002-B`, `ADR002-C`, `ADR002-D` o `T0-control`. Ningún otro identificador es admisible.
- [ ] **Alternativa mínima declarada y coherente** con la señal tardía habilitada de §2.2 bis.
- [ ] **Etapa `E3` declarada para todo candidato**, incluido `ADR002-A`, con su validación de sujeto, polaridad, condición y tiempo.
- [ ] **Si la alternativa es `ADR002-D`**: §2.2 ter completo, con orden de etapas congelado y mecanismo que impide la coordinación simultánea.
- [ ] Ficha completa: ningún campo vacío ni «pendiente» sin fundamento.
- [ ] Ficha confirmada en el repositorio, con commit y huella.
- [ ] Corpus congelado y **T0 rederivada sobre ese mismo corpus**.
- [ ] Protocolo de medición aplicado, con desviaciones declaradas de antemano.
- [ ] Todos los límites por magnitud congelados, con fundamento.
- [ ] Coherencia verificada entre §2.9 y §2.10.
- [ ] Puertas previas comunes declaradas en §2.2 quater.
- [ ] Modelos de amenaza de TOL-002 y TOL-206 declarados.
- [ ] Ningún valor de esta ficha procede de un resultado observado del candidato.

---

## 4. Lo que esta plantilla no hace

- No aprueba ningún candidato ni autoriza ejecutarlo.
- **No emite ninguna ficha.** `ADR002-TOL-210` sigue **NO SATISFECHA**.
- No fija ningún valor: los valores los declara y congela cada candidato.
- **No declara obligatoria ninguna señal tardía concreta.** Obligatoria es la etapa `E3`; qué señal la satisface es lo que el benchmark mide.
- **No convierte `ADR002-A` ni `ADR002-C` en controles.** Solo `T0` puede fichar como control de falsación.
- No sustituye a la ficha del caso de la Especificación de benchmark §5.
- No sustituye al Registro de Tolerancias: lo instrumenta. **No aprueba `TOL-207` ni declara satisfechas `TOL-208` o `TOL-209`.**
- No abre `EJE-1` ni `EJE-2`: en la primera ronda todos los candidatos comparten el sustrato léxico FTS5 medido.
- No modifica `src/`, `tests/`, `migrations/`, `experiments/`, `artifacts/` ni configuración productiva.

---

**Siguiente movimiento único:** que el usuario apruebe o corrija esta plantilla v0.2. Hasta entonces no se instancia ninguna ficha, y aunque se apruebe, no habrá ficha que emitir mientras el corpus no esté corregido y congelado (`ADR002-TOL-208`) y el entorno del protocolo no esté congelado (`ADR002-TOL-209`).
