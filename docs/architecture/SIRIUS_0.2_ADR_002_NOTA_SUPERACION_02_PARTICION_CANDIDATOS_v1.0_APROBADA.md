# SIRIUS 0.2 — ADR-002 · Nota de superación 02

## Qué queda superado por la Resolución de la partición de candidatos v1.0

**Versión:** 1.0
**Estado:** **APROBADA · CANÓNICA PARA ADR-002** · nota de coherencia documental
**Fecha:** 26 de julio de 2026
**Rama:** `evidence/adr001-spikes`
**Autoridad:** aprobación explícita del usuario en el Proyecto Sirius
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_03A_RESOLUCION_PARTICION_CANDIDATOS_v0.1.md` §4
**Fuente que aplica:** `SIRIUS_0.2_ADR_002_RESOLUCION_PARTICION_CANDIDATOS_v1.0_APROBADA.md`
**No autoriza:** corregir o congelar el corpus, aprobar `ADR002-TOL-207`, ejecutar T0, implementar o ejecutar candidatos, satisfacer `ADR002-TOL-208`, `ADR002-TOL-209` o `ADR002-TOL-210`, ni merge.

---

## 0. Objeto y método

La Resolución v1.0 restituye `ADR002-A/B/C/D` como universo oficial de candidatos y supera `T1–T4` como universo principal. Varios documentos anteriores —dos de ellos **aprobados**— contienen la partición superada.

**Método aplicado: superación por nota, nunca reescritura silenciosa.**

1. **Ningún fichero anterior se modifica ni se borra.** `ADR-002 v0.2 ABIERTO`, el `Registro de Tolerancias v0.4`, su acta de aprobación, la `Ficha de candidato v0.1`, la `Especificación de benchmark v0.2`, la `Matriz canónica v0.1` y el `Informe de preparación del corpus v0.1` se conservan íntegros.
2. **Regla de lectura:** ante discrepancia entre un documento anterior y la Resolución v1.0 **en cualquiera de los puntos listados en esta nota**, prevalece la Resolución v1.0. En todo lo demás, los documentos anteriores siguen íntegros y vigentes.
3. **Alcance estricto.** Esta nota supera **la identificación y el universo de candidatos**, y nada más. No altera el contenido material de ninguna tolerancia, ningún umbral, ninguna medición ni ninguna regla de congelación.

---

## 1. `SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.2_ABIERTO.md` — **SUPERADO en su §0 y §3**

**Sustituido por:** `SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.3_ABIERTO.md`, emitido en esta misma ronda. La v0.2 **se conserva sin modificar**.

| Punto de la v0.2 | Estado | Qué prevalece |
|---|---|---|
| §0 · «sus alternativas A, B, C y D … **se retiran** y se sustituyen por realizaciones técnicas, §3» | **SUPERADO** | Las cuatro alternativas mínimas de ARQ-00 §23 **no fueron retiradas válidamente**. Se restituyen como `ADR002-A/B/C/D` |
| §0 · «**la variante solo léxica deja de ser candidata**. Se conserva como control y como hipótesis de falsación, nunca como producto alternativo equivalente, porque incumple la expansión aprobada» | **SUPERADO** | `ADR002-A` es **candidato completo y puede ser recomendado**. Lo que incumple la expansión aprobada es `T0` —la línea base de 0.1—, no una realización correcta de `E0–E5` con señales léxicas y estructuradas |
| §3 · tabla `T1–T4` como «alternativas técnicas excluyentes» | **SUPERADO como universo principal** | El universo principal es `ADR002-A/B/C/D`. Los dos ejes de `T1–T4` se conservan como **ejes contingentes** `EJE-1` (sustrato léxico) y `EJE-2` (materialización de relaciones) |
| §3 · «La señal semántica tardía es común a las cuatro porque **B04-RF-17 la impone**, no porque se elija» | **SUPERADO** | `RF-17` impone la **etapa `E3`** con validación de sujeto, polaridad, condición y tiempo. **No impone una señal vectorial.** `B04-RF-31` y B04 §8 lo prohíben expresamente |

**Lo que de la v0.2 NO queda superado y sigue íntegramente vigente:** §1 pregunta material, §2 entradas obligatorias y el tratamiento de `RED-040`, §3.1 el papel de `T0` como control de falsación, §3.2 las seis puertas previas comunes, §4 las nueve puertas de decisión —incluida la puerta 9, salto a recuperación amplia—, §5 evidencia requerida, §6 línea base heredada y su congelación, §7 método de cierre y el carácter bloqueante de su paso 3, y §8 la lista de decisiones no tomadas.

---

## 2. `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md` — **SUPERADO únicamente en la etiqueta de arquitectura de `TOL-210`**

**El Registro v0.4 no se reescribe.** Fue aprobado el 26 de julio de 2026 con blob verificado `263b1689c8e2ac1988d779826eb75cb5d63618a1`, y ese contenido exacto sigue siendo el aprobado. Esta nota **no toca el fichero**.

### 2.1 `ADR002-TOL-210` · fila «Contenido mínimo»

**Texto aprobado, conservado:**

> | **Contenido mínimo** | ID y versión · **arquitectura T1–T4** · componentes y versiones · corpus y commit (TOL-208) · **TOL-101A, TOL-102C, TOL-104A, TOL-201, TOL-202, TOL-203** · límite absoluto de almacenamiento del entorno (TOL-207) · límites de tiempo de construcción, reconstrucción y borrado · protocolo de medición (TOL-209) · modelo de amenaza de TOL-002 · secuencia de purga de TOL-206 · **huella del candidato** |

**Superación, y solo esta:**

> Donde `TOL-210` exige **«arquitectura T1–T4»**, debe leerse **«arquitectura `ADR002-A` · `ADR002-B` · `ADR002-C` · `ADR002-D` · `T0-control`»**, conforme a la Resolución v1.0 §2 y §3.

**Todo lo demás de `TOL-210` permanece intacto**: la regla de ficha propia, versionada y comprometida antes de la primera ejecución; el resto del contenido mínimo, campo por campo; el punto de congelación; el estado `PUERTA_DE_ARRANQUE`; la consecuencia de incumplimiento; y la advertencia de que la ficha de candidato no vive dentro de la ficha del caso.

**`ADR002-TOL-210` sigue `NO SATISFECHA`.** Esta nota corrige la etiqueta del candidato; no emite ninguna ficha.

### 2.2 Regla de lectura para las demás filas que citan `T1–T4`

El Registro v0.4 usa etiquetas `T1/T2` y `T3/T4` en otros seis lugares. **Ninguno cambia de contenido material.** En todos ellos las etiquetas designan una **condición técnica**, no una identidad de candidato, y así deben leerse:

| Lugar del Registro v0.4 | Texto que cita `T` | **Regla de lectura** |
|---|---|---|
| §0.2, `TOL-101A` | «Sustrato léxico alternativo de **T3/T4**» | «Sustrato léxico alternativo: **todo candidato cuyo sustrato léxico no sea el FTS5 medido**» |
| §1.3 | «Sirve para comparar **T1–T4** entre sí en el mismo entorno» | «Sirve para comparar **los candidatos de ADR-002** entre sí en el mismo entorno» |
| `TOL-101L`, ámbito y punto de congelación | «Un sustrato léxico alternativo de **T3/T4**…»; «Común únicamente a los candidatos cuyo sustrato léxico sea el FTS5 medido (**T1 y T2**)» | **Ya está expresado por condición**: rige para **todo candidato cuyo sustrato léxico sea el FTS5 medido**, sea `ADR002-A`, `B`, `C` o `D` |
| `TOL-101L`, regla de neutralidad | «Un candidato de **T3/T4** que quede por encima…» | «Un candidato **con sustrato léxico alternativo** que quede por encima…» |
| `TOL-104A`, ámbito | «representaciones semánticas de **T1–T4** y el índice relacional derivado de **T2/T4**» | «**toda representación semántica y todo índice relacional derivado**, de cualquier candidato que los declare» |
| §5.4 | «límite duro común a **T1–T4**» (retirado en la v0.2) | Referencia histórica a una regla ya retirada; **sin efecto** |
| §7, `TOL-208` y `TOL-209`; §9 | «antes de ejecutar **T1–T4**»; «ningún texto lo imponía a **T1–T4**»; «solo para los candidatos cuyo sustrato léxico sea el FTS5 medido (**T1 y T2**)» | «antes de ejecutar **los candidatos**»; «a **los candidatos**»; y la tercera **ya está expresada por condición** |
| §10.1 | «TOL-101L y TOL-104L dejan de ser el patrón obligatorio de **T3/T4**» | «…patrón obligatorio de **todo sustrato léxico alternativo**» |

**Esta regla de lectura no altera ningún umbral, ningún valor, ningún punto de congelación ni ningún estado.** El Registro v0.4 ya había desplazado estas filas del eje «candidato» al eje «condición técnica» en su propia §10.1; esta nota se limita a hacerlo explícito ahora que las etiquetas `T` dejan de nombrar candidatos.

### 2.3 Acta de aprobación del Registro

`SIRIUS_0.2_ADR_002_REGISTRO_TOLERANCIAS_APROBACION_v1.0.md` **se conserva sin modificar**. Su aprobación del 26 de julio de 2026 sigue vigente sobre los cuatro artefactos y sus blobs verificados. Lo que esta nota superpone es la lectura de la etiqueta de arquitectura de `TOL-210` y la de la plantilla de ficha, **sin invalidar el acta**: los contenidos aprobados siguen siendo los aprobados, con la corrección declarada aquí.

---

## 3. `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.1_PROPUESTO.md` — **SUPERADA en §1 regla 1 y §2.2**

**Sustituida por:** `SIRIUS_0.2_ADR_002_FICHA_CANDIDATO_TEMPLATE_v0.2_PROPUESTO.md`, emitida en esta misma ronda. La v0.1 **se conserva sin modificar** y su aprobación del 26 de julio de 2026 (blob `4e9fa861ed6ab22a6b19729ed44066c8d93d863e`) se respeta como historial.

| Punto de la v0.1 | Estado | Qué prevalece en la v0.2 |
|---|---|---|
| §1 regla 1 · «**T1, T2, T3 y T4** tienen fichas distintas. T0 tiene la suya, marcada como control de falsación» | **SUPERADO** | «`ADR002-A`, `ADR002-B`, `ADR002-C` y `ADR002-D` tienen fichas distintas. `T0` tiene la suya, marcada como control de falsación» |
| §2.1 · **ID de candidato** `‹T1 · T2 · T3 · T4 · T0-control›` | **SUPERADO** | `‹ADR002-A · ADR002-B · ADR002-C · ADR002-D · T0-control›` |
| §2.2 · **Realización técnica** `‹T1 · T2 · T3 · T4›` según ADR-002 §3 | **SUPERADO** | **Alternativa mínima** `‹ADR002-A · ADR002-B · ADR002-C · ADR002-D›` según ARQ-00 §23 y la Resolución v1.0 §2 |
| §2.2 · **Señal semántica tardía** `‹descripción; **es obligatoria por B04-RF-17, no es una elección**›` | **SUPERADO** | La señal tardía habilitada es **lo que distingue a cada alternativa**. Obligatoria es la **etapa `E3`**, no una señal vectorial |
| §2.6 · «Rellenar solo si el sustrato léxico no es el FTS5 medido (**T3, T4**)» | **SUPERADO en su etiqueta** | «Rellenar solo si el sustrato léxico **no es el FTS5 medido**» — condición, no etiqueta. La regla material es idéntica |
| §8 encabezado · «No autoriza: benchmark **T1–T4**…» | **SUPERADO en su etiqueta** | «No autoriza: benchmark de candidatos…» |

**Campos añadidos en la v0.2**, exigidos por el paquete 03A §4.3 y por la Resolución v1.0 §7: **señal tardía habilitada**, **orden de las etapas tardías** y **restricciones propias de `ADR002-D`**.

**Lo que de la v0.1 NO queda superado y se conserva íntegro en la v0.2:** las siete reglas de uso restantes, la estructura completa §2.1–§2.16, todas las reglas de congelación, todos los límites por magnitud, la escala común obligatoria, las advertencias de neutralidad y de indistinguibilidad accidental, la declaración final de congelación y la lista de verificación previa a ejecutar.

---

## 4. `SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.2_PROPUESTO.md` — **SUPERADA en §1 y §11**

**Sustituida por:** `SIRIUS_0.2_ADR_002_ESPECIFICACION_BENCHMARK_v0.3_PROPUESTO.md`, emitida en esta misma ronda. La v0.2 **se conserva sin modificar**.

| Punto de la v0.2 | Estado | Qué prevalece |
|---|---|---|
| §1 · «con los que ADR-002 comparará después las realizaciones técnicas **T1–T4**» | **SUPERADO** | «…comparará después los candidatos **`ADR002-A/B/C/D`**, con `T0` como control» |
| §11 · «No elige entre **T1, T2, T3 y T4**» | **SUPERADO** | «No elige entre `ADR002-A`, `ADR002-B`, `ADR002-C` y `ADR002-D`» |

**Lo que de la v0.2 NO queda superado:** los tres niveles de caso, los siete principios de construcción, la estructura del corpus, la ficha obligatoria del caso y sus trece campos, la agrupación `C-01`–`C-20`, las cinco clases de fallo duro, el tratamiento de suficiencia y criticidad, las siete ablaciones, la forma de las métricas y las cinco puertas booleanas, la evidencia mínima por ejecución y las nueve incertidumbres restantes.

---

## 5. `SIRIUS_0.2_ADR_002_MATRIZ_CANONICA_BENCHMARK_v0.1_PROPUESTO.md` §6 e `INFORME_PREPARACION_CORPUS_v0.1_PROPUESTO.md` §7 — **cuestión abierta CERRADA; cita literal corregida**

Ambos documentos **se conservan sin modificar**. Registraron correctamente el conflicto y se abstuvieron de resolverlo. Lo que esta nota hace es cerrar la cuestión que dejaron abierta y corregir una cita.

| Punto | Estado | Qué prevalece |
|---|---|---|
| Matriz §6 · «Se registra como **cuestión abierta** para el usuario. **No se resuelve aquí**» | **CERRADA** | Resuelta por la Resolución v1.0. Deja de ser cuestión abierta y deja de bloquear aguas arriba de `TOL-210` |
| Informe §7 · «**No se resuelve aquí.** Se registra para el usuario» | **CERRADA** | Ídem |
| Matriz §6 · «**B**: léxica/estructurada con **señal semántica vectorial** en etapas tardías» | **Correcta** | Conserva «vectorial». Se confirma como cita fiel |
| Informe §7 · «**B** con señal **semántica** tardía» | **CORREGIDO** | La cita omite la palabra **vectorial**, que sí está en ARQ-00 §23. La cita fiel es: «**B**: expansión escalonada léxica/estructurada con señal semántica **vectorial** únicamente en etapas tardías tras fallar la puerta de suficiencia» |
| Matriz §6 e Informe §7 · «la segunda es coherente con RF-17, que impone la señal tardía» | **SUPERADO** | `RF-17` impone la **etapa `E3`**, no una señal vectorial. Ver Resolución v1.0 §4 |
| Matriz §5 y §2, Informe §4 · «El corpus es **neutral** respecto de ambas particiones —traza a RF, CA, M y RED, nunca a T1–T4 ni a A–D—» | **Vigente y confirmado** | La neutralidad del corpus es real y sigue siendo correcta. **Esta resolución no obliga a tocar el corpus por motivo de partición** |

**Ningún otro defecto del corpus se corrige aquí.** Los hallazgos de la auditoría adversarial independiente sobre traza `RED↔CA↔M`, alcance de `congelada_por`, ausencia del modo `M4`, casos multirrama aplanados, ficha de caso frente al PDP §7, denominador de familias PDP y clasificación frente a `T0` **permanecen abiertos y sin corregir**, conforme al paquete 03A §4.5.

---

## 6. Lo que esta nota **NO** supera

Se enumera de forma expresa para que no pueda leerse de más:

1. **No supera ninguna tolerancia ni ningún umbral** del Registro v0.4 fuera de la etiqueta de arquitectura de `TOL-210`.
2. **No aprueba `ADR002-TOL-207`** ni valida ninguna de sus cifras.
3. **No declara satisfechas `ADR002-TOL-208`, `ADR002-TOL-209` ni `ADR002-TOL-210`.**
4. **No corrige el corpus**, ni sus casos, ni sus referencias, ni sus validadores.
5. **No modifica** `experiments/`, `artifacts/`, `docs/architecture/canonical_sources/`, `src/`, `tests/`, `migrations/` ni configuración productiva.
6. **No supera `SRC-ADR002-01`**, que sigue satisfecha por sí misma.
7. **No autoriza** ejecutar `T0`, implementar prototipos, emitir fichas de candidato, elegir realización técnica ni fusionar el PR #117.
8. **No invalida** el acta de aprobación del Registro de Tolerancias ni la de la plantilla de ficha.

---

## 7. Índice de superación — resumen

| Documento | Alcance de la superación | Sustituido por |
|---|---|---|
| `ADR-002 v0.2 ABIERTO` | §0 y §3: universo de candidatos e interpretación de `RF-17` | `ADR-002 v0.3 ABIERTO` |
| `Registro de Tolerancias v0.4` | **Solo** la etiqueta «arquitectura T1–T4» de `TOL-210`, más regla de lectura por condición en seis lugares | **Nada. No se reescribe** |
| Acta de aprobación del Registro v1.0 | Nada. Se respeta íntegra | — |
| `Ficha de candidato v0.1` | §1 regla 1, §2.1, §2.2, §2.6 y encabezado: identificación del candidato | `Ficha de candidato v0.2` |
| `Especificación de benchmark v0.2` | §1 y §11: universo de candidatos | `Especificación de benchmark v0.3` |
| `Matriz canónica v0.1` §6 | Cuestión abierta cerrada; lectura de `RF-17` | **Nada. No se reescribe** |
| `Informe de preparación del corpus v0.1` §7 | Cuestión abierta cerrada; cita literal de `B` corregida; lectura de `RF-17` | **Nada. No se reescribe** |

---

**Siguiente movimiento único:** con la partición resuelta y la coherencia documental restituida, el trabajo autorizado es **corregir los defectos del corpus que la auditoría dejó abiertos**, antes de que `ADR002-TOL-208` pueda plantearse. No se emite ninguna ficha, no se ejecuta `T0` y no se aprueba `TOL-207`.
