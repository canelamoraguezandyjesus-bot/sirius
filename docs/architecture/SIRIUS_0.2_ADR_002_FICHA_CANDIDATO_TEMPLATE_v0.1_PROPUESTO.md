# SIRIUS 0.2 — ADR-002 · Ficha de candidato · plantilla

**Versión:** 0.1
**Estado:** **PROPUESTO** · plantilla, **no está aprobada** y no autoriza nada por sí misma
**Fecha:** 26 de julio de 2026
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02D_CORRECCION_AUDITORIA_v0.1.md` §5.3
**Exigida por:** `ADR002-TOL-210` del `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md`
**No autoriza:** benchmark T1–T4, ejecución de T0, implementación de prototipos, elección de alternativa ni merge.

---

## 0. Por qué existe este artefacto

La regla de congelación es el mecanismo antitrampa de todo el Registro de Tolerancias: **ningún valor puede fijarse después de observar el resultado del candidato**. Hasta la v0.3, esa regla decía que los valores congelados por candidato «se registran en la ficha del caso antes de la primera ejecución».

**La ficha del caso no podía alojarlos.** Es el artefacto de la Especificación de benchmark §5: trece campos que describen un **caso de prueba** —entrada, modo, ámbito, tiempo, candidatos elegibles y prohibidos, orden esperado, razón, métrica, evidencia, cardinalidad, etapa y parada—. Ninguno describe al **candidato**. La regla apuntaba a un contenedor equivocado, y su cumplimiento no era auditable.

Esta ficha es ese contenedor. Es un artefacto **propio del candidato**, no del caso: se escribe una vez por candidato, se confirma en el repositorio **antes de su primera ejecución**, y **cada ejecución la referencia** por ID, versión y huella.

---

## 1. Reglas de uso

1. **Una ficha por candidato.** T1, T2, T3 y T4 tienen fichas distintas. T0 tiene la suya, marcada como control de falsación.
2. **Confirmada antes de la primera ejecución.** Una ficha creada o modificada después de observar cualquier resultado del candidato **no es una ficha**: es justificación a posteriori, y el Registro v0.4 §9 regla 1 la prohíbe.
3. **Completa o inexistente.** Un campo vacío o «pendiente» invalida la ficha. Si un valor no puede declararse, se declara **por qué** y esa imposibilidad se congela igual.
4. **Versionada.** Cualquier modificación posterior obliga a **nueva versión** de ficha y a **repetir** las ejecuciones ya realizadas bajo la anterior (Registro v0.4 §9 reglas 2 y 10).
5. **Referenciada desde cada ejecución.** El registro de evidencia de cada ejecución cita `id · versión · huella`. Una ejecución que no referencie una ficha previa **no es utilizable como evidencia**.
6. **No sustituye a la ficha del caso.** Ambas coexisten: la del caso describe qué se prueba, esta describe contra qué límites se juzga al candidato.
7. **No contiene resultados.** Esta ficha contiene **límites y declaraciones**, nunca mediciones del propio candidato. Los resultados viven en el registro de ejecución.

---

## 2. Plantilla

> Copiar íntegra. Sustituir cada `‹…›`. No borrar ningún encabezado: un apartado vacío debe decir expresamente por qué lo está.

---

### 2.1 Identidad

| Campo | Valor |
|---|---|
| **ID de candidato** | `‹T1 · T2 · T3 · T4 · T0-control›` |
| **Versión de ficha** | `‹v0.1›` |
| **Fecha de congelación** | `‹AAAA-MM-DD›` |
| **Commit de confirmación** | `‹sha›` |
| **Huella de la ficha** | `‹hash del fichero en el momento de congelar›` |
| **Estado** | `CONGELADA` / `SUSTITUIDA POR ‹versión›` |
| **Sustituye a** | `‹versión anterior o "ninguna"›` · motivo: `‹…›` |

### 2.2 Arquitectura declarada

| Campo | Valor |
|---|---|
| **Realización técnica** | `‹T1 · T2 · T3 · T4›` según ADR-002 §3 |
| **Sustrato léxico** | `‹FTS5 medido · alternativo: nombre y versión›` |
| **Señal semántica tardía** | `‹descripción; es obligatoria por B04-RF-17, no es una elección›` |
| **Relaciones** | `‹desde el canon · índice relacional derivado›` |
| **Puerto de acceso** | `‹equivalente a KnowledgeSearchRepository; obligatorio por RF-31 y la puerta 6›` |
| **Etapas E0–E5 implementadas** | `‹mapa de qué ocurre en cada etapa y qué condición de insuficiencia autoriza la transición›` |

**Declaración obligatoria de puertas previas comunes.** No son ventaja de ningún candidato y ninguno puede omitirlas (ADR-002 §3.2):

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

Toda desviación no declarada **antes** de ejecutar invalida las cifras del candidato.

### 2.6 Sustrato léxico alternativo — `ADR002-TOL-101A`

> Rellenar **solo** si el sustrato léxico **no** es el FTS5 medido (T3, T4). Si es el FTS5 medido, escribir «No aplica: sustrato léxico = FTS5 medido; rigen TOL-101L, TOL-104L y los tiempos de TOL-105».

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

> Una tabla por índice no léxico. Los trece campos son obligatorios.

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
| **Coste de inferencia o generación de la señal de consulta** | `‹objetivo / límite duro / dónde se ejecuta›` |
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
- [ ] Ficha completa: ningún campo vacío ni «pendiente» sin fundamento.
- [ ] Ficha confirmada en el repositorio, con commit y huella.
- [ ] Corpus congelado y **T0 rederivada sobre ese mismo corpus**.
- [ ] Protocolo de medición aplicado, con desviaciones declaradas de antemano.
- [ ] Todos los límites por magnitud congelados, con fundamento.
- [ ] Coherencia verificada entre §2.9 y §2.10.
- [ ] Puertas previas comunes declaradas en §2.2.
- [ ] Modelos de amenaza de TOL-002 y TOL-206 declarados.
- [ ] Ningún valor de esta ficha procede de un resultado observado del candidato.

---

## 4. Lo que esta plantilla no hace

- No aprueba ningún candidato ni autoriza ejecutarlo.
- No fija ningún valor: los valores los declara y congela cada candidato.
- No sustituye a la ficha del caso de la Especificación de benchmark §5.
- No sustituye al Registro de Tolerancias: lo instrumenta.
- No modifica `src/`, `tests/`, `migrations/`, `experiments/`, `artifacts/` ni configuración productiva.

---

**Siguiente movimiento único:** que el usuario apruebe o corrija esta plantilla junto al Registro v0.4. Hasta entonces no se instancia ninguna ficha, porque no hay candidato autorizado que fichar.
