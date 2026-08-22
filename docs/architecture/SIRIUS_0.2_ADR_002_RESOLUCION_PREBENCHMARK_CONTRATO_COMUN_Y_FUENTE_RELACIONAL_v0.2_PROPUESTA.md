# SIRIUS 0.2 · ADR-002 · Resolución pre-benchmark · v0.2

## Contrato común experimental y fuente relacional admisible de ADR002-C

**Estado:** **PROPUESTA · PENDIENTE DE APROBACIÓN EXPLÍCITA DEL USUARIO**
**Versión:** v0.2
**Sustituye documentalmente a:** `SIRIUS_0.2_ADR_002_RESOLUCION_PREBENCHMARK_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v0.1_PROPUESTA.md` (blob `727e02ed6b7f0e750d4877a8d10bd171afbf4d5a`), que **se conserva íntegro** y no se reescribe
**Preinscrita por:** `SIRIUS_0.2_ADR_002_PAQUETE_RESOLUCION_05_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v0.2.md`
**Rama de trabajo:** `claude/adr002-tol209-forensic-audit-i0ui8k` · **HEAD de partida:** `4a686c37dcf78c89bda3c08a4817737451248377`

> **No está aprobada.** Nada de lo que propone puede implementarse hasta aprobación explícita. **El benchmark sigue bloqueado.** Ninguna decisión aprobada anterior queda anulada: `ADR002-A v3` y `ADR002-B v5` continúan aprobadas e intactas.

---

## 1. Qué corrige esta versión

| # | Defecto material de la v0.1 | Corrección |
|---|---|---|
| **1** | Concluía que compartir tokens entre extremos demuestra que `A` alcanza ambos | **Retirado.** Ese razonamiento no es suficiente. La conclusión se rehace **por ejecución** (§8) |
| **2** | Confundía deduplicación con agrupación, y decía que «el mismo identificador es el único caso de agrupación» mientras permitía grupos de identidades distintas | **Dos mecanismos distintos**, definidos por separado, con sus efectos propios (§5) |
| **3** | Convertía la ausencia de sujeto en causa automática de descarte por `G5` | **Retirado.** `B04` no contiene esa obligación (§6) |
| **4** | Dejaba `propiedad` abierto sin propuesta | **Cerrado** como `property_key`, convención local P2 con controles estáticos (§7) |
| **5** | Autorizaba `criticidad` como objeto completo, y afirmaba que todos sus valores eran `null` | **Ambas cosas eran falsas.** Solo `criticidad.nivel` es entrada; **19 de 95** ítems la tienen no nula (§9) |
| **6** | Presentaba a `T0` como partícipe del motor, las etapas, las puertas y el puerto comunes | **Retirado y reescrito** contra la ficha vigente de `T0` (§10) |
| **7** | Dejaba abierta la atribución de proyecto a los mensajes | **Cerrado**: se transporta, declarado como atribución sintética del banco (§11) |
| **8** | Trataba los vocabularios como convención local sin cerrarla | **Cerrados** como convenciones locales del benchmark P2 (§12) |
| **9** | Proponía solo `conformance_corpus_v0_5.json` | **Familia sucesora completa** (§13) |
| **10** | Orden de la ola incompleto | **Once pasos**, con la familia de corpus antes de la proyección (§14) |

---

## 2. Diagnóstico consolidado

Los nueve hechos de la v0.1 se mantienen y se vuelven a verificar sobre el árbol. Se añaden dos:

| # | Hecho | Anclaje |
|---|---|---|
| D1 | `admite_no_vigentes` no produce efecto: **0 de 10** combinaciones cambian de resultado | `contracts.py:162`, `gates.py:116,121-124` |
| D2 | `_agrupar` usa 3 de los 7 ejes de `B04-Q13` | `engine.py:88-92` |
| D3 | `lectura.condicion` y `lectura.tiempo` existen y no se usan | `contracts.py:206-211` |
| D4 | `propiedad` no está modelada en ninguna parte | §7 |
| D5 | `postura` solo se instancia en `relaciones[].tipo ∈ {APOYA, REFUTA}` | corpus |
| D6 | Sin confirmación ni autoridad en `ItemCanonico` no se puede elegir representante como `B04` manda | `contracts.py:173-193` |
| D7 | `Resultado` no conserva grupo, procedencias ni diferencias | `contracts.py:246-253`, `trace.py:64-65` |
| D8 | `subject_key` NULL se convierte en cadena vacía | `models.py:232`, `port.py:193` |
| D9 | `decisions.supersedes_decision_id` existe y el puerto no lo selecciona | `models.py:311`, `port.py:50-55` |
| **D10** | **`criticidad` es un objeto `{nivel, razon, fuente, regla}` y `fuente` contiene identificadores de caso** («B04-CA-01», «B04-CA-45», «REGLA-CRIT-07»). **19 de 95 ítems la tienen no nula**: 17 `CRITICO`, 1 `IMPORTANTE`, 76 `null` | corpus v0.4 |
| **D11** | **La expansión `E3` de `ADR002-A` toma términos puente del texto de la propia semilla** y los busca en el índice léxico. Por eso alcanza ítems que la consulta no nombra | `adr002_a/candidate.py`, `_terminos_puente` |

---

## 3. Contrato común experimental completo

Se conserva la tabla de veinte campos de la v0.1 con dos cambios:

- el campo **`propiedad`** deja de estar abierto y pasa a `property_key` (§7);
- el campo **`criticidad`** se descompone: solo `nivel` es entrada de la capa común (§9).

**Dato que resume la brecha:** once de los veinte campos no tienen fuente en Sirius 0.1 y sí la tienen en el corpus congelado — tiempo válido, tiempo de registro, confirmación, validez, disponibilidad, sensibilidad, autoridad, procedencias, relaciones explícitas, marcas de no uso y estado histórico.

Nada de esta tabla es DDL productivo: vive en el plano de arquitectura experimental (P2), que `ADR-001` consecuencia 10 declaró no convertible automáticamente en diseño.

---

## 4. La norma de agrupación, literal

> **`B04-Q13`:** «Se agrupan equivalentes solo si **sujeto, propiedad, polaridad, condición, tiempo, ámbito y postura** coinciden; apoyo y refutación explícitos nunca se colapsan. **El representante prioriza confirmación/autoridad y conserva procedencias y diferencias.**»
>
> **`B04-RF-20`:** «Agrupar duplicados solo cuando también coincidan ámbito y postura; conservar procedencias y separar apoyo/refutación **o cualquier diferencia material**.»
>
> **`B04-D09` (APROBADA):** «La deduplicación conserva procedencias, polaridad, condición, tiempo, ámbito y postura; apoyo y refutación no se fusionan.»
>
> **`B04` línea 233 (contrato de salida):** «Grupos de duplicados | Representante justificado, procedencias adicionales y diferencias preservadas.»
>
> **`B04` línea 196 (glosario):** «Representante de grupo | Elemento confirmado, aplicable y de mayor autoridad/procedencia; **no se elige si hay diferencias materiales**.»

---

## 5. Dos mecanismos distintos: deduplicación y agrupación

La v0.1 los confundía. Son mecanismos **diferentes**, con disparador, efecto y salida propios.

### 5.A · Deduplicación exacta por identidad

| | |
|---|---|
| **Disparador** | **El mismo identificador canónico** aportado por varias etapas o con varias procedencias |
| **Efecto** | Una **sola entrada lógica** para esa identidad |
| **Fusiona** | Señales y procedencias de todas sus apariciones |
| **Conserva** | **Todas** las explicaciones: ninguna se pierde. La etapa de origen que se registra es la de **máxima autoridad** (`E1` antes que `E4`), y las demás quedan como procedencia adicional |
| **No hace** | **No selecciona representante entre identidades diferentes.** Aquí no hay identidades diferentes: hay una sola |
| **Anclaje** | `CA-19` («un grupo, representante justificado y tres procedencias»), `B02-RF-11`, línea 233 |

### 5.B · Agrupación de equivalentes

| | |
|---|---|
| **Disparador** | **Identificadores canónicos distintos** |
| **Condición** | Solo cuando los **siete ejes están determinados y coinciden**. Si cualquiera está indeterminado, **no se agrupa** |
| **Conserva** | **Todos los miembros**, sus relaciones, sus procedencias y sus diferencias |
| **Representante** | **Justificado**, por la regla de §5.D |
| **No hace** | **No elimina las identidades de la salida.** Los miembros siguen siendo identidades citables del resultado |
| **Anclaje** | `Q13`, `RF-20`, `D09`, línea 233 |

**Queda expresamente eliminada** toda frase que diga que el mismo identificador es el único caso de agrupación: es el único caso de **deduplicación**, que es otra cosa.

### 5.C · Qué diferencias impiden agrupar

| Caso | Regla |
|---|---|
| Sujeto ausente o indeterminado | **No se agrupa** (pero el elemento **sigue siendo elegible**, §6) |
| Sustituida y sucesora | **Nunca**: difieren en validez y en tiempo |
| Apoyo y refutación | **Nunca**, explícitamente |
| Condiciones, tiempos, ámbitos o posturas distintas | **Nunca** |
| Vigencia o disponibilidad distintas | **Nunca**: «cualquier diferencia material» |
| `property_key` distinta, `null` o desconocida | **Nunca** |
| Cualquier eje indeterminado | **Nunca.** Fallo cerrado: la duda no fusiona |

### 5.D · Regla de representante (solo para 5.B)

Cascada registrada: **confirmación → autoridad → vigencia → procedencia → identidad estable**. **«Primero en llegar» queda prohibido.** Y como `B04:196` prohíbe elegir representante cuando hay diferencias materiales, la regla solo se aplica a grupos que ya pasaron §5.C.

### 5.E · Estructura de salida

Agregado `GrupoDeEquivalentes`, campo propio del contrato de salida y **distinto de la traza**: `representante`, `miembros` (todas las identidades, incluida la del representante), `procedencias_adicionales`, `diferencias_materiales` (vacío por construcción), `relaciones_entre_miembros`, `razon_del_representante`, `estado_historico_por_miembro`.

**Invariante comprobable mecánicamente:** elegibles antes de agrupar = unión de los `miembros` de todos los grupos + los no agrupados. Ninguna agrupación puede eliminar información necesaria para responder o explicar.

### 5.F · Efectos, por mecanismo y por separado

| Aspecto | **Deduplicación exacta (5.A)** | **Agrupación de equivalentes (5.B)** |
|---|---|---|
| **Cardinalidad** | Una identidad repetida cuenta **una vez**. Se evalúa después de deduplicar | Un grupo cuenta **por sus miembros**, no por su representante: agrupar no reduce el recuento de elegibles |
| **Suficiencia** | Se adjudica sobre lo deduplicado | Se adjudica **después** de agrupar, sobre lo que se va a devolver. Nunca puede declararse `COMPLETA` con menos resultados que objetivos |
| **Orden** | La identidad ocupa **una** posición, la de su etapa de máxima autoridad | Se ordena por representante; los miembros conservan su orden interno estable |
| **`G12`** | Se aplica **después**: la deduplicación no puede ocultar un crítico | Se aplica **después** y ve **todos los miembros**, no solo representantes. Un crítico agrupado sigue siendo crítico para el límite |
| **Explicaciones** | Se conservan **todas**; las adicionales pasan a procedencia | Cada miembro conserva la suya; el grupo añade `razon_del_representante` |
| **Traza** | Registra las apariciones fusionadas y su etapa | Registra el grupo, sus miembros y el criterio de representante. **La traza no sustituye al campo de salida**: son requisitos distintos (`RF-29` frente a línea 233) |
| **Criticidad** | Se conserva; la identidad no cambia de nivel por aparecer varias veces | **No es eje de agrupación ni criterio de representante.** Un miembro crítico permanece como miembro y su nivel se conserva en el grupo |

---

## 6. `G5` y el sujeto ausente

**Se retira** la regla de la v0.1 que hacía de la ausencia de sujeto una causa de descarte. `B04` no contiene esa obligación, y `G5` no debe inventarla.

Regla propuesta:

| Situación | Efecto |
|---|---|
| **Identidad inválida o ambigua** | `G5` **rechaza** |
| **Entidad solicitada ambigua o no resuelta** | `G5` **rechaza o exige aclaración**, conforme a `B04` línea 299 («ID resuelto **o ambigüedad aclarada**») y `RF-05` línea 423 («no fusionar homónimos o alias ambiguos») |
| **Sujeto ausente** | El elemento **sigue siendo elegible**. No se descarta |
| **Sujeto ausente** | Queda **prohibida su agrupación por equivalencia** (§5.C) |
| **`NULL`** | Se **conserva como ausencia**. **Nunca** se convierte en `""` |

Así, el defecto D8 se corrige donde corresponde —en la proyección de sujeto y en la condición de agrupación— y no convirtiendo `G5` en un filtro que `B04` no pide.

---

## 7. El eje `propiedad`: `property_key`

**Decisión experimental propuesta y cerrada.**

| | |
|---|---|
| **Nombre** | `property_key` |
| **Semántica** | Identificador **opaco y estable** del atributo o predicado del sujeto sobre el que versa la afirmación |
| **Ejemplos** | **Exclusivamente ilustrativos**: `presupuesto.maximo`, `aforo.maximo` |
| **Uso permitido** | La **igualdad** de `property_key` sirve **solo** para agrupación |
| **No es** | Texto libre |
| **No se deriva** | Durante la consulta |
| **No es** | Señal de recuperación, de ranking ni de expansión |
| **Quién puede consultarlo** | **Únicamente la capa común**, y solo para decidir equivalencia. **Ningún módulo específico de `A`/`B`/`C`/`D` puede consultarlo** |
| **`null` o desconocido** | **No se agrupa** |
| **Naturaleza** | **Convención local del benchmark P2.** No decide el vocabulario productivo de Sirius 0.2 |

**Control obligatorio de la futura implementación:** controles **estáticos** que prohíban el uso de `property_key` en los candidatos —del mismo tipo que la auditoría de interpolaciones ya vigente en `ADR002-B`—, de modo que un candidato que lo lea falle en pruebas y no en revisión.

---

## 8. Suficiencia funcional de ADR002-C — rehecha por ejecución

### 8.1 Se retira el razonamiento anterior

La v0.1 concluyó a partir del **solapamiento de tokens** entre extremos. **Ese razonamiento no es suficiente** y queda retirado: una consulta construida solo con términos propios del origen no alcanza el destino por léxico, así que el solapamiento entre los dos textos no prueba nada por sí solo.

### 8.2 Proyección de sujeto, fijada de antemano

**`P-SUJETO-01`: `subject_key := identificador del propio ítem`.**

Es la regla que aplica el único cargador congelado existente (`frozen_corpus.py`). Es también la **más conservadora**: no crea familias de sujeto artificiales, de modo que `A` opera solo con léxico y términos puente. Cualquier proyección más rica haría a `A` **más** fuerte, luego la conclusión es *a fortiori*.

Se declara **antes** de mostrar resultados, como exige el método.

### 8.3 Condiciones de la sonda

Sonda construida **fuera del repositorio**, sin benchmark oficial y sin medir rendimiento. Campos usados: de los ítems `id`, `kind`, `project_id`, `text`, `confirmacion`, `validez`, `disponibilidad`; de las relaciones `tipo`, `origen`, `destino`. **No** se leyeron `relaciones[].nota`, casos, referencias, resultados esperados, trazas ni adjudicaciones. Reglas de traducción idénticas a las preinscritas en `frozen_corpus.py`. Comportamiento real de `ADR002-A` completo `E0-E5` sobre el motor y las puertas comunes.

### 8.4 Resultados de ejecución

Consulta construida **exclusivamente con términos propios del origen ausentes del destino**:

| Arista | Ámbito | Consulta | 1) A alcanza semilla | 2) A **no** alcanza destino | Etapa | n |
|---|---|---|---|---|---|---|
| **REL-002** `CONFLICTO_CON` | GLOBAL | `comentario reunion` | **sí** | **NO — sí lo alcanza** | `E3` | 78 |
| **REL-002** | PRJ-BETA | `comentario reunion` | **sí** | **NO — sí lo alcanza** | `E3` | 20 |
| **REL-004** `REFUTA` | GLOBAL | `acepta abaratan trayecto` | **sí** | **NO — sí lo alcanza** | `E3` | 60 |
| **REL-004** | PRJ-BETA | `acepta abaratan trayecto` | **sí** | sí, no lo alcanza | — | 10 |
| REL-001 `SUSTITUYE_A` | GLOBAL / ALFA | `500` | sí | **NO — sí lo alcanza** | `E3` | 19 / 10 |
| REL-008 `SUSTITUYE_A` | GLOBAL / BETA | `25` | sí | **NO — sí lo alcanza** | `E3` | 91 / 7 |
| REL-009 `CORRIGE` | GLOBAL / BETA | `25` | sí | **NO — sí lo alcanza** | `E3` | 91 / 7 |

**Condición 4 —¿permiten las puertas el destino?—** comprobada con consulta directa al destino en el mismo ámbito:

- `REL-002`: **sí** en ambos ámbitos.
- `REL-004` en GLOBAL: **sí**. En **PRJ-BETA: NO** — el destino `MEM-014` es de `PRJ-ALFA` y `G4` lo excluye.

**Por qué `A` lo alcanza (causa, no coincidencia):** la etapa `E3` de `ADR002-A` toma **términos puente del texto de la propia semilla** y los busca en el índice léxico. Los extremos de las cinco aristas comparten vocabulario, así que el puente existe siempre. Trazas de etapa:

```
REL-002  E1: 1 aportada  E2: 9   E3: 72 aportadas / 68 nuevas   total 78
REL-004  E1: 2 aportadas E2: 0   E3: 62 aportadas / 58 nuevas   total 60
```

### 8.5 Observación de honestidad: alcance frente a orden

Bajo límite duro estrecho, `A` devuelve la semilla **pero no el destino**:

```
REL-002, consulta 'comentario reunion', ámbito global
  límite 1 → MEMORIA:6                    destino: no
  límite 2 → MEMORIA:6, DECISION:16       destino: no
  límite 5 → 5 resultados                 destino: no
  sin límite práctico → 78 resultados     destino: posición 15 de 78
REL-004, sin límite práctico → 60 resultados, destino en posición 14 de 60
```

Se registra sin adornos: **no hay discriminante de alcance, pero sí podría haberlo de orden.** Una arista relacional daría al destino una razón fuerte para subir. La condición que el método fija es la de **alcance** —«`A` no alcanza el destino»— y no se cumple en ninguna de las configuraciones donde las puertas permiten el destino. Un eventual discriminante de orden es otra cosa, exigiría métricas de ranking y **no está autorizado medirlas**.

### 8.6 Veredicto

# **B · ADMISIBLE PERO INSUFICIENTE**

Existe fuente relacional admisible, pero **ninguna arista congelada produce un caso discriminante honesto**, y esto se sostiene **en las ejecuciones**, no en el solapamiento textual:

- En las tres configuraciones donde las puertas permiten el destino y hay términos propios del origen, **`A` alcanza el destino en `E3`**.
- En la única configuración donde `A` **no** lo alcanza —`REL-004` en ámbito `PRJ-BETA`—, **las puertas tampoco lo permiten**: `G4` excluye `MEM-014`. `C` no puede relajar una puerta común, luego tampoco lo devolvería. No es discriminante: es exclusión de ámbito.
- Las tres aristas de supersesión y corrección (`REL-001`, `REL-008`, `REL-009`) **carecen prácticamente de vocabulario propio del origen**: sus consultas se reducen a `500` y `25`. Por construcción, una sustitución produce textos casi idénticos.

---

## 9. Criticidad y frontera de oráculo

### 9.1 Corrección de un error de la v0.1

La v0.1 afirmó que todos los valores de `criticidad` estaban en `null`. **Es falso.** Recuento directo sobre el blob congelado: **76 `null`, 17 `CRITICO`, 1 `IMPORTANTE`** — 19 de 95 ítems la tienen.

### 9.2 `criticidad` es un objeto, y solo un campo es entrada

Forma real: `{"nivel", "razon", "fuente", "regla"}`. Ejemplo literal: `{"nivel": "CRITICO", "razon": "Límite de gasto vigente; su omisión causa decisión errónea.", "fuente": "B04-CA-45", "regla": "CRIT-03"}`.

| Campo | Clasificación | Motivo |
|---|---|---|
| `criticidad.nivel` | **PERMITIDO a la capa común**, normalizado al vocabulario experimental | Es el dato que `B04` §6 exige que exista antes del límite |
| `criticidad.razon` | **PROHIBIDO** a candidatos y a la capa común de recuperación | Contiene fundamentos de adjudicación |
| `criticidad.fuente` | **PROHIBIDO** | Contiene **identificadores de caso**: `B04-CA-01`, `B04-CA-45`, `REGLA-CRIT-07` |
| `criticidad.regla` | **PROHIBIDO** | Identificador de regla de adjudicación |

Los tres prohibidos permanecen como **metadatos privados del arnés**.

### 9.3 Qué NO hace la criticidad

- **No genera candidatas.**
- **No aumenta similitud.**
- **No permite saltar etapas.**
- Solo afecta al **tratamiento común anterior al límite** cuando `B04` lo exige (`G12`, `RF-24`, `B04` §6).

### 9.4 Re-auditoría de todos los objetos anidados de la lista blanca

| Objeto | Campos | Veredicto |
|---|---|---|
| `items[].temporalidad` | `valid_from`, `valid_to`, `occurred_at`, `recorded_at` | **entrada completa**: los cuatro son datos temporales |
| `items[].criticidad` | `nivel` / `razon`, `fuente`, `regla` | **parcial**: solo `nivel` |
| `items[].procedencia` | lista de identificadores | **entrada completa** |
| `items[].entity_ids` | lista de identificadores | **entrada completa** |
| `items[].traza` | lista de identificadores de caso | **oráculo completo: prohibido** |
| `relaciones[]` | `tipo`, `origen`, `destino` / `nota` | **parcial**: `nota` prohibido |
| `entidades[]` | `id`, `nombre_canonico`, `alias` / `grupo_homonimo`, `nota` | **parcial**: los dos últimos prohibidos |
| `documentos[]` | `id`, `titulo`, `texto`, `accesible`, `afirmacion_atribuida` / `traza` | **parcial**: `traza` prohibido. `afirmacion_atribuida` es contenido real y es entrada |
| `mensajes[]` | `id`, `texto`, `recorded_at`, `no_guardar`, `redactado`, `project_id` / `traza` | **parcial**: `traza` prohibido; `project_id` según §11 |
| `proyectos[]` | `id`, `nombre`, `tipo`, `alias`, `miembros_lista_cerrada` | **entrada completa** |

**Regla general que se adopta:** no se autoriza un objeto completo cuando solo algunos de sus campos son entrada legítima. La lista blanca se materializa como constante única y **falla cerrada** ante cualquier campo no listado.

---

## 10. Arquitectura de T0 — corregida

**Se retira** toda afirmación de la v0.1 de que `T0` utiliza el motor común, las etapas `E0-E5`, las puertas comunes o el puerto lógico de `A/B/C/D`.

Redacción correcta, contrastada contra la ficha vigente `ficha_T0-control_v1.json` y contra `adr002_a/candidate.py`:

| Hecho | Anclaje literal |
|---|---|
| `T0` conserva el **`KnowledgeSearchRepository` real de Sirius 0.1** | Ficha, `arquitectura_de_control.puerto_de_acceso`: «`KnowledgeSearchRepository` de Sirius 0.1 vía `build_sqlite_knowledge_search_repository` y `RankRelevantKnowledgeUseCase`, **los originales medidos**» |
| Conserva sus **incumplimientos declarados** | Ficha, `incumplimientos_conocidos`: `RF-06` (no aísla ámbito), `RF-14` (barrido completo presente), `RF-19` |
| **No se convierte en candidato** | Ficha, `identidad.papel`: `CONTROL_DE_FALSACION`. Y `adr002_a/candidate.py`: «Este candidato **no es T0**. T0 es Sirius 0.1 tal cual: no implementa las etapas, no tiene puertas ni paradas» |
| `T0` **no tiene** motor común ni puertas | La ficha de `T0` no contiene las palabras «motor» ni «puertas»: **0 apariciones** |
| Lo que **sí** comparten `T0` y `A/B/C/D` | La **fuente congelada**, los **identificadores**, los **textos** y un **índice léxico FTS5 comparable**. Nada más |
| `A/B/C/D` usan el **contrato y motor experimental común** | `common/engine.py`, `common/gates.py`, `common/port.py` |
| Las dimensiones adicionales de la proyección | Permiten **adjudicar el comportamiento de los candidatos**. **No se presentan como capacidades de `T0`** |
| Cualquier adaptador de carga de `T0` | Debe **conservar exactamente su comportamiento medido**. Si lo alterase, dejaría de ser el control |

### 10.1 Discrepancia documental detectada, que NO se corrige aquí

La ficha de `T0` nombra la tabla léxica **`items_fts`**. La cadena de migraciones canónica crea **`knowledge_fts`** (`61be4bb269bf`), y `items_fts` **no aparece en ningún otro punto del repositorio**.

Se **registra y no se toca**: la ficha está congelada y aprobada, y esta resolución no modifica fichas. No afecta a la medición ya realizada —que corrió contra la base real—, pero es una discrepancia de custodia que merece una fe de erratas propia cuando se autorice. **Se deja constancia; no se disimula.**

---

## 11. Proyecto de los mensajes

**Decisión adoptada para P2:**

- **Se transporta `mensajes[].project_id`.**
- Se declara **atribución sintética del banco**, no dato del canon.
- **No se afirma que exista en el canon productivo.** `MessageModel` y `ConversationModel` no tienen esa columna y no hay camino transitivo.
- **Usos permitidos:** `G4`, trazas de ámbito y adjudicación de `E4`. Nada más.
- **Prohibido:** que genere candidatas o relaciones.
- **Aplicación idéntica** a todos los candidatos que utilizan `E4`.

**Esto no es una propuesta de cambio productivo.**

---

## 12. Vocabularios experimentales

Los vocabularios actuales del corpus se adoptan como **CONVENCIONES LOCALES CERRADAS DEL BENCHMARK P2**: `CONFIRMACION`, `VALIDEZ`, `DISPONIBILIDAD`, `SENSIBILIDAD`, `AUTORIDAD`, `AMBITO` y los niveles de criticidad.

Se declara expresamente:

1. **No son vocabularios productivos aprobados.**
2. **No se atribuyen a `ADR-001 v1.1`.** Ese documento nombra las siete dimensiones y ordena su ortogonalidad, pero **no enumera sus valores**, y su §6 remite «fijar vocabularios definitivos» a la arquitectura consolidada.
3. **Se congelan** para garantizar comparabilidad experimental entre los cuatro candidatos.
4. Una futura arquitectura productiva **puede sustituirlos**.
5. **El benchmark no decide esa sustitución.**

---

## 13. Familia de corpus sucesora

Procede, porque el veredicto de §8 es **B**. **La v0.4 permanece completamente intacta**; la familia sucesora se materializa **junto a** ella, conforme a la propia acta de congelación §111.

### 13.1 Artefactos de la familia

| # | Artefacto | Contenido |
|---|---|---|
| 1 | **Corpus de conformidad sucesor o delta formal** | Dos ítems sintéticos nuevos y **una** arista ítem↔ítem de tipo distinto de supersesión y conflicto |
| 2 | **Caso funcional discriminante** | Semilla alcanzable por `A`; destino **no** alcanzable por `A` completo `E0-E5` |
| 3 | **Referencia calculada independientemente** | Derivada **después** del corpus, por regla cerrada, con el orden auditable |
| 4 | **PDP o reglas que deban cambiar** | Identificadas explícitamente; si ninguna cambia, se declara |
| 5 | **Manifiesto sucesor** | Debe **cerrar de forma inequívoca la familia completa utilizada**, incluidos los artefactos que no cambian |
| 6 | **Validadores** | Sucesores de los de v0.4, con la comprobación nueva de §13.2 |
| 7 | **Auditoría independiente** | Con las mismas puertas que la v0.4 |
| 8 | **Acta de congelación propia** | Blobs nuevos; los siete de v0.4 **intactos** |

**Se versionan únicamente los artefactos afectados**, pero el manifiesto sucesor cierra la familia entera.

### 13.2 Condición de diseño que la ejecución impone

La sonda de §8 demuestra **por qué** el discriminante es difícil: `E3` de `A` expande con **términos puente del texto de la semilla**. Por tanto la condición no es «poco solapamiento», sino:

> **Cero** tokens de contenido compartidos entre el texto del origen y el del destino, bajo la **misma regla de tokenización del índice** (`unicode61` + plegado de diacríticos, tokens ASCII), **verificado mecánicamente por el validador**, no a ojo.

Y además: sujetos distintos bajo la proyección declarada; mismo proyecto en ambos extremos, para que el ámbito no sea la señal ni `G4` los separe; y generación del resultado esperado **posterior e independiente**.

### 13.3 Impacto exacto

| Elemento | Impacto |
|---|---|
| **Rendimiento y rederivación T0 de `TOL-208`** | **INTACTOS**, siempre que `performance_corpus_v0_2.json` no cambie. T0 se midió sobre ese artefacto (`frozen_corpus.py:51`), distinto del corpus de conformidad |
| **Participación de `T0`** | `T0` **deberá participar en el nuevo caso funcional** cuando el benchmark sea autorizado. El control se ejecuta sobre los mismos casos, con su arquitectura propia |
| **Fichas sucesoras de `A/B/C/D`** | **Deberán citar la familia realmente utilizada**, no la v0.4 genéricamente |
| **Acta de congelación v0.4** | **INTACTA** |

---

## 14. Plan de una sola ola

Se mantiene el principio de **una sola corrección de `common/`**, con el orden actualizado:

| Paso | Contenido |
|---|---|
| **1** | Aprobar la resolución documental corregida |
| **2** | Resolver, **solo si es necesario**, la familia de corpus sucesora y congelarla |
| **3** | Construir la proyección experimental |
| **4** | Corregir **íntegramente** `common/` |
| **5** | Emitir las fichas sucesoras de `A` y `B` |
| **6** | Repetir sus pruebas |
| **7** | **Reaprobación explícita** de `A` y `B` |
| **8** | Implementar `C` con la fuente relacional adjudicada |
| **9** | Congelar, probar y aprobar `C` |
| **10** | Implementar y aprobar `D` |
| **11** | Solicitar **aparte** la autorización de benchmark |

**Ninguno de estos pasos queda autorizado por esta resolución.**

---

## 15. Auditoría adversarial de esta versión

| # | Tesis atacada | Resultado |
|---|---|---|
| 1 | ¿Determina `B04` la agrupación? | **Sí** (`Q13`, `RF-20`, `D09`, `M-03`), salvo `propiedad`, ahora cerrada como convención local P2 con controles estáticos |
| 2 | ¿Es la proyección una modificación encubierta de 0.1? | **No**: vive en `experiments/`, no añade migraciones, es descartable y reconstruible, y `ADR-001` consecuencia 10 lo respalda |
| 3 | ¿Son entrada los campos permitidos? | **Re-auditados objeto por objeto** (§9.4). Se restringió `criticidad` a `nivel` y se confirmaron las exclusiones de `traza`, `nota` y `grupo_homonimo` |
| 4 | ¿Es correcto el censo? | **9 relaciones, 5 ítem↔ítem** (`REL-001`, `REL-002`, `REL-004`, `REL-008`, `REL-009`) |
| 5 | ¿Abre `EJE-2` un índice derivado? | **No**: `EJE-2` es la *comparación* de ambas materializaciones, posterior a la ronda primaria (partición §6, líneas 168 y 175) |
| 6 | ¿Bastan las relaciones para `C`? | **No**, y ahora **probado por ejecución** (§8), no por solapamiento textual |
| 7 | ¿Favorece a `A`, `B`, `C` o `D`? | **No.** Mismo contrato, mismo motor, mismas puertas y misma lista blanca para los cuatro. `property_key` queda **vedado a los candidatos**. La proyección **no** añade la señal que `C` necesitaría: por eso el veredicto sigue siendo **B** |
| 8 | ¿Dos generaciones de fichas? | **No**: la familia de corpus y la proyección preceden a la corrección de `common/`, que se hace una sola vez |
| 9 | ¿Se reescribe algún documento anterior? | **No.** Los v0.1 se conservan íntegros; el commit `4a686c3` no se reescribe |
| 10 | ¿Autoriza el plan el benchmark? | **No**: el paso 11 exige autorización explícita e independiente |
| 11 | ¿Se sostiene la conclusión sobre `C` por ejecución? | **Sí**: siete configuraciones ejecutadas sobre las cinco aristas, con proyección de sujeto declarada de antemano |
| 12 | ¿Es contrastable la redacción sobre `T0`? | **Sí**, contra su ficha vigente. Y se registra la discrepancia `items_fts` / `knowledge_fts` sin tocar la ficha (§10.1) |
| 13 | ¿Cuela algún anidado campos de oráculo? | **Se encontró uno y se corrigió**: `criticidad` completo, con `fuente` conteniendo identificadores de caso |
| 14 | ¿Quedan deduplicación y agrupación como mecanismos distintos? | **Sí** (§5), y se eliminó la frase contradictoria de la v0.1 |

---

## 16. Cuestiones que requieren aprobación explícita

1. Los dos mecanismos de §5 y la estructura de salida de §5.E.
2. La regla de representante de §5.D.
3. La regla de `G5` y sujeto ausente de §6.
4. `property_key` como convención local P2, con controles estáticos (§7).
5. El veredicto **B** de §8 y la familia de corpus sucesora de §13.
6. La frontera de criticidad de §9 y la lista blanca re-auditada.
7. La redacción corregida de `T0` de §10, y qué hacer con la discrepancia `items_fts` (§10.1).
8. El transporte de `mensajes[].project_id` de §11.
9. Los vocabularios cerrados de §12.
10. El plan de once pasos de §14.
11. La eliminación de `admite_no_vigentes` y el reparto `G6`/`G7`, que se conservan de la v0.1.

---

## 17. Estado

**PROPUESTA. NO APROBADA.**

- El contrato común **no se modifica**.
- Las fichas y actas vigentes permanecen **intactas y válidas**: `ADR002-A v3` y `ADR002-B v5` continúan aprobadas.
- **El benchmark permanece bloqueado.**
- La comparación primaria sigue siendo `T0 + A + B + C + D`, **sin reducción**.
- Los documentos **v0.1 se conservan**; esta versión los sustituye **documentalmente**, no los borra.
- `evidence/adr001-spikes` **no se ha movido**; PR #117 sigue abierto, sin fusionar y con cabeza en `a074eb5`.
