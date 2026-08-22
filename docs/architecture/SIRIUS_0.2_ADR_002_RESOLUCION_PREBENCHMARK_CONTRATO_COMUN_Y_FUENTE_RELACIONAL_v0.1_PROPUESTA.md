# SIRIUS 0.2 · ADR-002 · Resolución pre-benchmark

## Contrato común experimental y fuente relacional admisible de ADR002-C

**Estado:** **PROPUESTA · PENDIENTE DE APROBACIÓN EXPLÍCITA DEL USUARIO**
**Versión:** v0.1 · **Rama:** `evidence/adr001-spikes` · **HEAD de partida:** `a074eb5effda760833fe7de1bd6e1b16984c982c`
**Preinscrita por:** `SIRIUS_0.2_ADR_002_PAQUETE_RESOLUCION_05_CONTRATO_COMUN_Y_FUENTE_RELACIONAL_v0.1.md`

> **Esta resolución no está aprobada.** Nada de lo que propone puede implementarse hasta que el usuario la apruebe de forma explícita. **El benchmark sigue bloqueado** por el hallazgo pre-benchmark, y esta resolución no lo desbloquea.

---

## 1. Qué resuelve y qué no

**Resuelve, para aprobación:** el contrato común experimental completo; la regla de agrupación y la estructura de salida de grupos; el reparto de `G5`/`G6`/`G7`; la proyección experimental del corpus; la frontera entre entrada y oráculo; el censo relacional; la adjudicación de suficiencia de `ADR002-C`; el tratamiento de `EJE-2`; y el plan de una sola ola de corrección.

**No resuelve, y lo declara abierto:** el eje `propiedad` de `B04-Q13` (§12.1) y la atribución de proyecto a los mensajes (§12.2). Ambos requieren decisión del usuario y **no se propone implementación para ellos**.

**No autoriza:** ejecutar candidatos, medir, reducir la ronda, tocar Sirius 0.1, modificar el corpus v0.4, ni modificar fichas o actas.

---

## 2. Diagnóstico consolidado

Los hechos siguientes se verificaron sobre el árbol de `a074eb5` y son la base de todo lo demás.

| # | Hecho | Anclaje |
|---|---|---|
| D1 | `Peticion.admite_no_vigentes` no produce ningún efecto: `G6` lo honra y `G7` vuelve a rechazar en M1 todo no vigente sin consultarlo. Tabla de verdad exhaustiva de 20 filas: **0 de 10** combinaciones (modo × vigencia) cambian de resultado. El campo se lee en un solo sitio y nunca se pone a `True`. | `contracts.py:162`, `gates.py:116,121-124` |
| D2 | `_agrupar` usa solo `subject_key`, `project_id` y polaridad: **3 de los 7 ejes** que `B04-Q13` exige. | `engine.py:88-92` |
| D3 | `lectura.condicion` y `lectura.tiempo` **existen y no se usan**. | `contracts.py:206-211` |
| D4 | `propiedad` no está modelada en ninguna parte, ni en el canon ni en el corpus. | §12.1 |
| D5 | `postura` no está modelada como campo; su única instanciación son los tipos de relación `APOYA`/`REFUTA`. | corpus `relaciones[].tipo` |
| D6 | No hay confirmación ni autoridad en `ItemCanonico`, luego no se puede elegir representante como `B04` manda. | `contracts.py:173-193` |
| D7 | `Resultado` no puede conservar el grupo, sus procedencias ni sus diferencias; la traza solo guarda pares de identificadores. | `contracts.py:246-253`, `trace.py:64-65` |
| D8 | `subject_key` NULL se convierte en cadena vacía, y los elementos sin asunto se agrupan entre sí. | `models.py:232` (nullable), `port.py:193` |
| D9 | `decisions.supersedes_decision_id` existe en Sirius 0.1 y es una clave externa físicamente forzada, pero el puerto no la selecciona. | `models.py:311`, `port.py:50-55` |

**Todos verificados de nuevo para esta resolución.** Ninguna otra afirmación de informes previos se da por válida sin comprobación; las que no resistieron están corregidas en §14.4.

---

## 3. Contrato común experimental completo

### 3.1 Criterio de plano

`DC` = dato canónico (lo que el sustrato entrega) · `LS` = lectura semántica (lo que el candidato deriva y declara) · `PT` = petición (lo que la operación fija).

### 3.2 Los veinte campos

| # | Campo | Semántica exacta | Vocabulario / fuente normativa | Plano | ¿En Sirius 0.1? | ¿En corpus v0.4? | Transporte propuesto | ¿Pendiente para producción? |
|---|---|---|---|---|---|---|---|---|
| 1 | **identidad** | Identificador estable del elemento, único y citable | `clase:entero` (convención vigente del puerto) | DC | **sí** (`memories.id`, `decisions.id`) | sí (`items[].id`) | ya viaja | no |
| 2 | **clase** | MEMORIA o DECISIÓN; distingue objetos que no son fusionables entre sí | Cerrado por el canon | DC | **sí** (tabla de origen) | sí (`kind`) | ya viaja | no |
| 3 | **sujeto** | Clave de asunto sobre la que versa el elemento | Abierto; texto | DC | **sí** (`memories.subject_key` *nullable*, `decisions.subject`) | **no explícito** — el corpus no declara `subject_key` | proyección: derivar del corpus con regla preinscrita y **conservar NULL como ausencia**, nunca como cadena vacía | no |
| 4 | **propiedad** | *Nombrada por `B04-Q13` y `M-03`; **no definida en ninguna fuente aprobada*** | **NINGUNO** | — | no | no | **§12.1 · decisión abierta** | **sí** |
| 5 | **polaridad** | Afirmación frente a negación de la lectura | `AFIRMATIVA` / `NEGATIVA` (`RF-19`) | LS | no (se deriva del texto) | sí (`polaridad`) | ya viaja | no |
| 6 | **condición** | Condicionante material de la afirmación («si abaratan el trayecto») | Abierto; texto o ausencia | LS | no | sí (`condicion`) | **existe en `LecturaSemantica` y hoy no se usa**; basta usarlo | no |
| 7 | **tiempo válido** | Intervalo en que la afirmación es aplicable | `valid_from` / `valid_to` (`ADR-001` consecuencia 6) | DC | **no** | sí (`temporalidad.valid_from/valid_to`) | proyección experimental | **sí** — `ADR-001` §6 |
| 8 | **tiempo de registro** | Cuándo Sirius pudo saberlo | `recorded_at` / `occurred_at` (`ADR-001` consecuencia 6) | DC | **parcial** (`created_at`) | sí (`temporalidad.recorded_at/occurred_at`) | proyección experimental | **sí** |
| 9 | **ámbito** | Global, proyecto o lista cerrada | `GLOBAL` / `PROYECTO` / `MULTI_PROYECTO_CERRADO` (`G4`) | DC + PT | **sí** para memorias y decisiones; **no** para mensajes | sí (`ambito`, `project_id`) | ya viaja para ítems; **§12.2** para mensajes | no |
| 10 | **postura** | Postura de la fuente respecto de la afirmación: apoyo frente a refutación | Determinada por `B04` líneas 105, 318, 437, 539: «apoyo y refutación **no se fusionan**». Sin enumeración cerrada, pero con semántica fijada | LS + DC | no | **sí, indirectamente**: `relaciones[].tipo ∈ {APOYA, REFUTA}` | proyección: transportar las aristas tipadas | parcial |
| 11 | **confirmación** | Grado de confirmación del elemento | `CONFIRMADA` / `CANDIDATA` / `RECHAZADA` / `SUPRIMIDA` (`benchmark/schema.py:31`; **convención local**, ver §12.3) | DC | **parcial**: `DecisionStatus.PROPOSED` ≈ candidata; las memorias no tienen estado propuesto | sí (`confirmacion`) | proyección experimental | **sí** |
| 12 | **validez** | Vigencia epistémica | `VIGENTE` / `SUSTITUIDA` / `INVALIDADA` / `SIN_SOPORTE` (**convención local**, ver §12.3) | DC | **parcial**: `DecisionStatus.SUPERSEDED` = sustituida; `INVALIDADA` y `SIN_SOPORTE` **sin fuente** | sí (`validez`) | proyección experimental | **sí** |
| 13 | **disponibilidad** | Existencia y accesibilidad del elemento | `DISPONIBLE` / `ARCHIVADA` / `ELIMINADA` / `PURGADA` / `NO_GUARDADA` (**convención local**) | DC | **parcial**: `ARCHIVED`, `DELETED`; no hay `PURGADA` ni `NO_GUARDADA` | sí (`disponibilidad`) | proyección experimental | **sí** |
| 14 | **sensibilidad** | Protección aplicable (`G9`) | `ORDINARIA` / `RESTRINGIDA` (**convención local**) | DC | **no** | sí (`sensibilidad`) | proyección experimental | **sí** |
| 15 | **autoridad** | Peso de la fuente, para elegir representante | `DOCUMENTO_CANONICO` / `ACTO_EXPLICITO_USUARIO` / `INFORMAL` / `FUENTE_EXTERNA` (**convención local**) | DC | **no** | sí (`autoridad`) | proyección experimental | **sí** |
| 16 | **criticidad** | Marca de producto revisable, previa al límite (`B04` §6) | `ORDINARIA` / `CRITICA`, con origen declarado | PT (marca de producto), no del canon | **no** | sí (`criticidad`, hoy `null` en todos) | de la petición y del corpus; hoy el puerto la fija a `ORDINARIA` en sus dos constructores | no |
| 17 | **procedencias** | Fuentes de las que procede el elemento; plural y conservable | Lista de identificadores | DC | **parcial**: `memory_revisions.origin`, `source_event_id` | sí (`procedencia`) | proyección experimental | parcial |
| 18 | **relaciones explícitas** | Aristas tipadas entre elementos identificados | `SUSTITUYE_A`, `CONFLICTO_CON`, `APOYA`, `REFUTA`, `ALIAS_DE`, `DERIVA_DE`, `ORIGINA_CANDIDATA`, `CORRIGE` (instanciación del corpus) | DC | **solo una**: `decisions.supersedes_decision_id` | sí (`relaciones[]`, 9 aristas) | proyección experimental; §7 y §8 | **sí** |
| 19 | **marcas de no uso** | «No usar como memoria» / «no consolidable» (`G3`) | Booleanos | DC | **no** | sí (`no_usar_como_memoria`, `no_consolidable`) | proyección experimental | **sí** |
| 20 | **estado histórico** | Si el elemento es la versión vigente o una anterior marcada | Derivado de validez + relación de sustitución | DC | **parcial** (`SUPERSEDED` + FK) | sí | proyección experimental | parcial |

### 3.3 Lo que esta tabla demuestra

De veinte campos, **once no tienen fuente en Sirius 0.1 y sí la tienen en el corpus congelado**. Esa es exactamente la brecha que impide medir hoy, y es la que la proyección experimental (§6) cierra sin tocar Sirius 0.1.

**Nada de esta tabla es DDL productivo.** Vive en el plano P2 del paquete: arquitectura experimental descartable.

---

## 4. Agrupación y estructura de salida

### 4.1 Cuándo son equivalentes dos elementos — literal de B04

> **`B04-Q13`:** «Se agrupan equivalentes solo si **sujeto, propiedad, polaridad, condición, tiempo, ámbito y postura** coinciden; apoyo y refutación explícitos nunca se colapsan. **El representante prioriza confirmación/autoridad y conserva procedencias y diferencias.**»
>
> **`B04-RF-20`:** «Agrupar duplicados solo cuando también coincidan ámbito y postura; conservar procedencias y separar apoyo/refutación **o cualquier diferencia material**.»
>
> **`B04-D09` (APROBADA):** «La deduplicación conserva procedencias, polaridad, condición, tiempo, ámbito y postura; apoyo y refutación no se fusionan.»
>
> **`B04` §12 paso 11:** «Agrupar duplicados prudentes | Conservar procedencias y separar diferencias materiales.»

**Se agrupan solo si coinciden los siete ejes. Cualquier otra cosa es una diferencia material que impide agrupar.**

### 4.2 Regla propuesta, caso por caso

| Caso | Regla propuesta | Anclaje |
|---|---|---|
| **Asunto desconocido** | **No se agrupa nunca.** Sujeto ausente ≠ sujeto coincidente. Se conserva la ausencia como ausencia, no como cadena vacía | `Q13` («sujeto … coinciden»), `G5`, `RF-05` |
| **Identidades distintas** | Se agrupan solo si coinciden los siete ejes; el no-representante **permanece en la salida como miembro del grupo** | `Q13`, línea 233 |
| **Sustituida y sucesora** | **Nunca se agrupan.** Difieren en validez y en tiempo: diferencia material | `RF-20`, `CA-23` |
| **Apoyo y refutación** | **Nunca se colapsan**, explícitamente | `Q13`, `D09`, `RF-21` |
| **Condiciones distintas** | No se agrupan | `Q13`, `D09` |
| **Tiempos distintos** | No se agrupan | `Q13`, `D09` |
| **Ámbitos distintos** | No se agrupan | `Q13`, `RF-20`, `G4` |
| **Posturas distintas** | No se agrupan | `Q13`, `RF-20`, `D09` |
| **Vigencia o disponibilidad distintas** | No se agrupan: «cualquier diferencia material» | `RF-20` |
| **Duplicado real de una misma identidad** | Es el **único** caso de agrupación plena: una identidad aportada por varias etapas o varias procedencias produce **un grupo con todas sus procedencias**, no varias entradas ni una entrada con una sola procedencia | `CA-19`, `B02-RF-11`, línea 233 |
| **Cualquier eje desconocido** | **No se agrupa.** Fallo cerrado: la duda no fusiona | `RF-21`, `B04` §12 paso 11 («prudentes») |

### 4.3 Estructura de salida propuesta

`B04` línea 233 declara los grupos **campo propio del contrato de salida**, distinto de la traza: «Grupos de duplicados | Representante justificado, procedencias adicionales y diferencias preservadas».

Se propone un agregado `GrupoDeEquivalentes` que acompaña al resultado, con:

| Campo | Contenido | Exigido por |
|---|---|---|
| `representante` | Identidad del elemento que representa al grupo | línea 233 |
| `miembros` | **Todas** las identidades del grupo, incluida la del representante | línea 233, `CA-19` |
| `procedencias_adicionales` | Procedencias de los miembros no representantes, sin pérdida | línea 233, `B02-RF-11`, `M07` |
| `diferencias_materiales` | Ejes en que los miembros difieren, si el grupo se formó pese a ello (debe quedar **vacío** por construcción) | `RF-20`, `B04:196` |
| `relaciones_entre_miembros` | Aristas explícitas que vinculan miembros del grupo | `G11`, `RF-18` |
| `razon_del_representante` | Qué criterio lo eligió, en texto mínimo | `B04:196` («representante **justificado**») |
| `estado_historico_por_miembro` | Vigente o versión anterior marcada, por miembro | `CA-05`, `B01-RF-03` |

**Invariante que la estructura debe garantizar:** una agrupación **nunca** elimina información necesaria para responder o explicar. Formalmente: el conjunto de identidades elegibles antes de agrupar es igual a la unión de los `miembros` de todos los grupos más los no agrupados. Es comprobable mecánicamente y debe ser una prueba de la ola.

### 4.4 Regla de representante

`B04:196`: «Elemento **confirmado, aplicable y de mayor autoridad/procedencia**; **no se elige si hay diferencias materiales**.»
`B04-Q13`: «El representante prioriza **confirmación/autoridad**.»

Orden propuesto, aplicado en cascada y **registrado**:

1. **confirmación** — confirmado antes que candidato;
2. **autoridad** — documento canónico > acto explícito del usuario > informal > fuente externa;
3. **vigencia** — vigente antes que histórico;
4. **procedencia** — mayor número de procedencias distintas conservadas;
5. **identidad estable** — último desempate, determinista.

**Queda expresamente prohibido «primero en llegar».** Y como `B04:196` prohíbe elegir representante cuando hay diferencias materiales, la regla solo se aplica a grupos que ya pasaron §4.2.

### 4.5 Efectos que la resolución fija

| Aspecto | Regla propuesta | Anclaje |
|---|---|---|
| **Cardinalidad y suficiencia** | Se evalúan **después** de agrupar, sobre lo que realmente se va a devolver. Hoy se evalúan antes y pueden declarar `COMPLETA` con menos resultados que objetivos | `RF-25` |
| **`G12`** | Se aplica **después** de agrupar, para que nada desaparezca sin que `G12` lo vea | `B04` §11 (orden normativo) |
| **Criticidad** | No es eje de agrupación ni criterio de representante. Un miembro crítico **permanece como miembro** y su criticidad se conserva en el grupo | `Q13`, `B04` §6 |
| **Orden** | El desempate sigue siendo el estable y registrado ya vigente; se aplica sobre representantes | `M-05` (línea 46), `RF-22` |
| **Explicaciones** | Cada resultado conserva su explicación; el grupo añade la justificación del representante. No se pierde ninguna procedencia | `Q14`, `G10` |
| **Privacidad** | El grupo **no** revela contenido ni categoría restringida; solo identidades, ejes y procedencias ya autorizadas | `Q14`, `RF-28` |
| **Traza** | Sigue registrando la agrupación, y ahora también el criterio de representante. La traza **no sustituye** al campo de salida: son requisitos distintos | `RF-29`, línea 233 |
| **Indistinguibilidad externa** | Sin cambios: ausencia y no reportable siguen compartiendo `SIN_RESULTADO_UTILIZABLE` | `Q15`, `RF-26` |

---

## 5. Decisión sobre `G5`, `G6` y `G7`

### 5.1 `admite_no_vigentes`

**Propuesta: eliminarlo.**

`B04` línea 212 fija que «**cambiar de modo** amplía o restringe qué puede verse», y la fila de M1 (línea 207) no ofrece ninguna excepción por petición. El instrumento canónico para ver no vigentes es **usar M2, M3 o M4**, no marcar una bandera en M1. El campo, además, está provadamente inerte (D1).

### 5.2 ¿Necesita otro modo un campo equivalente?

**Propuesta: no.** M2 «permite archivado, sustituido y finalizado»; M3 permite historial y documentos autorizados; M4 permite inspeccionar candidatas, rechazadas, suprimidas, restringidas y sin soporte. Los tres lo hacen **por definición de modo**, no por bandera. Lo que sí exige `B04` línea 210 es que M4 opere «solo por petición o vista autorizada» — eso ya lo cubre `G1` (propósito y permiso).

### 5.3 Distinción en la traza de los ocho estados

Hoy los ocho caen con el mismo motivo. `B02-RF-15` (línea 109) exige que «archivo, restricción, invalidación y borrado» sean **distintos**. Propuesta:

| Estado | Puerta que lo descarta | Motivo propuesto en traza |
|---|---|---|
| propuesta (candidata) | `G6` | `confirmacion CANDIDATA: el modo M1 no la admite` |
| rechazada | `G6` | `confirmacion RECHAZADA: el modo M1 no la admite` |
| archivada | `G6` | `disponibilidad ARCHIVADA: el modo M1 no la admite` |
| sustituida | `G7` | `validez SUSTITUIDA: M1 exige estado valido` |
| invalidada | `G7` | `validez INVALIDADA: no entra en M1` |
| sin soporte | `G7` | `validez SIN_SOPORTE: no entra en M1` |
| eliminada | `G2` | `disponibilidad ELIMINADA: no recuperable ni reconstruible` |
| purgada | `G2` | `disponibilidad PURGADA: no recuperable ni reconstruible` |

Los motivos nombran **el estado real**, no una categoría prestada. Requiere que el contrato lleve las dimensiones (§3).

### 5.4 Qué debe comprobar `G5`

Hoy `G5` solo comprueba que la identidad no esté vacía, y el puerto siempre la construye no vacía: **`G5` no puede fallar jamás sobre un ítem real.**

`B04` línea 299 le exige «ID resuelto o ambigüedad aclarada; alias no fusionan homónimos». Propuesta: `G5` comprueba que
1. la identidad esté resuelta **y**
2. el **sujeto** esté resuelto —presente y no ambiguo—, porque es el sujeto, no la identidad, lo que la agrupación usa después.

**Cómo se impide agrupar elementos sin sujeto resuelto:** por dos vías independientes y redundantes a propósito — `G5` los descarta antes de agrupar, y la regla de §4.2 prohíbe agrupar con eje desconocido aunque llegaran. Fallo cerrado por partida doble.

### 5.5 Reparto de dimensiones entre `G6` y `G7`

| Puerta | Dimensiones | Literal |
|---|---|---|
| **`G6` · Modo y confirmación** | **confirmación** (confirmada/candidata/rechazada/suprimida) y **disponibilidad en su vertiente de visibilidad** (archivada), con el **modo como decisor** | «El modo decide si candidata, rechazada, archivada o conflicto son visibles» |
| **`G7` · Validez y soporte** | **validez** completa (vigente/sustituida/invalidada/sin soporte) | «Invalidado o sin soporte no entra en M1» + la exigencia positiva de M1 de ser «**válido**» (línea 207) |

**Aclaración deliberada:** la fila de `G7` nombra dos valores, pero la elegibilidad de M1 se fija en positivo en la línea 207 («Confirmado, **válido**, disponible…»), y el canon del propio repositorio lo confirma: `src/sirius/domain/decision.py:22-23` declara que «a still-PROPOSED decision was never part of ordinary context to begin with, **and a SUPERSEDED one is already excluded from it**». Por tanto **una decisión sustituida queda fuera de M1**, y quien la excluye es `G7`. Esto **no es una decisión nueva**: es lectura literal.

**`G6` no filtra por conflicto.** La línea 207 exige lo contrario: «Conflictos se recuperan **marcados**». El conflicto se denuncia, no se excluye.

---

## 6. Proyección experimental del corpus

### 6.1 Decisión propuesta

**Sí: el benchmark debe usar una proyección experimental separada del esquema productivo.**

Sin ella, once de los veinte campos del §3 no llegan al motor, y los casos que `B04` mide sobre estados no son medibles. Con ella, los cuatro candidatos y el control reciben **exactamente el mismo sustrato**, que es la condición de comparabilidad.

### 6.2 Propiedades obligatorias de la proyección

| Propiedad | Exigencia |
|---|---|
| **Ubicación** | Exclusivamente bajo `experiments/adr002/`. **Cero cambios** en `src/`, `migrations/` y `tests/` productivos |
| **Forma** | Base SQLite experimental propia, construida desde los blobs congelados |
| **Identificadores** | **Los mismos identificadores canónicos** del corpus, para que la evidencia sea citable y contrastable |
| **Índice léxico** | **El mismo FTS5** y la misma configuración que la línea base medida: el sustrato léxico no varía entre candidatos |
| **Motor, puertas y puerto lógico** | **Los mismos**. La proyección cambia lo que el puerto *puede leer*, no quién decide |
| **Transporte** | Sin pérdida de las dimensiones que el corpus declara |
| **Naturaleza** | **Derivado descartable y reconstruible** desde los blobs congelados. No es autoridad, no sobrevive a su fuente, no se exporta |
| **Custodia** | Construcción verificada contra los blobs congelados; una discrepancia de un byte aborta |
| **Plano** | **P2 · arquitectura experimental.** No es DDL productivo ni insumo de ADR-004 |

### 6.3 Por qué esto no es una modificación encubierta de Sirius 0.1

Cinco razones acumulativas, todas verificables mecánicamente:

1. No toca `src/`, `migrations/` ni `tests/`; una prueba de la ola puede comprobarlo por diff.
2. No añade ni altera ninguna migración de Alembic; la cadena productiva sigue terminando donde termina hoy.
3. La base experimental se construye y se destruye en la propia ejecución; no persiste como autoridad.
4. `ADR-001` consecuencia 10 ya fijó que el código experimental no se convierte automáticamente en diseño ni en DDL. Esta resolución lo repite y lo hace condición de aprobación.
5. La proyección **no inventa datos**: transporta lo que el corpus congelado ya declara.

### 6.4 Lista blanca — lo que un candidato PUEDE consumir

**De `items[]`:** `id`, `kind`, `project_id`, `entity_ids`, `text`, `polaridad`, `condicion`, `confirmacion`, `validez`, `disponibilidad`, `sensibilidad`, `temporalidad.*`, `ambito`, `autoridad`, `no_usar_como_memoria`, `no_consolidable`, `criticidad`, `procedencia`.

**De `relaciones[]`:** `tipo`, `origen`, `destino`.

**De `entidades[]`:** `id`, `nombre_canonico`, `alias`.

**De `proyectos[]`:** `id`, `nombre`, `tipo`, `alias`, `miembros_lista_cerrada`.

**De `documentos[]`:** `id`, `titulo`, `texto`, `accesible`, `afirmacion_atribuida`.

**De `mensajes[]`:** `id`, `texto`, `recorded_at`, `no_guardar`, `redactado`. *(Sobre `project_id`, ver §12.2.)*

### 6.5 Lista negra — lo que queda EXPRESAMENTE PROHIBIDO consumir

- `items[].traza`
- `relaciones[].nota`
- `entidades[].nota`, `entidades[].grupo_homonimo`, `documentos[].traza`, `mensajes[].traza` y **cualquier nota que nombre un caso**
- `cases_v0_4.json` **completo**
- `references_v0_4.json` **completo**
- adjudicaciones, resultados esperados, elegibles, prohibidos, etapas esperadas, paradas esperadas
- etiquetas `A`/`B`/`C`/`D` de candidato
- **cualquier proyección de T0**

**Criterio único que separa las dos listas:** un campo es entrada si describe **qué es** el elemento; es oráculo si describe **qué debe hacer el sistema con él**. `traza` y `nota` nombran el caso que el elemento instancia, y `grupo_homonimo` declara qué no debe fusionarse: los tres dicen la respuesta.

**Mecanismo de control propuesto:** la lista blanca se materializa como constante única y la construcción de la proyección **falla cerrada** ante cualquier campo no listado, en vez de ignorarlo en silencio. Es la misma disciplina que ya usa la auditoría de interpolaciones de `ADR002-B`.

---

## 7. Censo relacional corregido

Auditoría directa de `conformance_corpus_v0_4.json` (blob `c21b702c…`).

**Total: 9 relaciones. Ítem↔ítem: 5 — `REL-001`, `REL-002`, `REL-004`, `REL-008`, `REL-009`.**

*(Corrige un censo previo erróneo que contaba ocho: las cuatro restantes tienen al menos un extremo que no es ítem recuperable.)*

| ID | Tipo | Origen (clase) | Destino (clase) | Dirección | ¿Ambos extremos recuperables? | ¿`tipo/origen/destino` es entrada? | ¿Usable en E3? | ¿A alcanza ambos sin recorrerla? |
|---|---|---|---|---|---|---|---|---|
| **REL-001** | `SUSTITUYE_A` | DEC-003 (DECISIÓN) | DEC-002 (DECISIÓN) | dirigida | **sí** | **sí** | **sí** | **sí** — 6 tokens comunes y misma familia de sujeto por regla canónica |
| **REL-002** | `CONFLICTO_CON` | MEM-006 (MEMORIA) | DEC-005 (DECISIÓN) | simétrica de hecho | **sí** | **sí** | **sí** | **sí** — 5 tokens comunes (`presupuesto`, `beta`), mismo proyecto |
| **REL-004** | `REFUTA` | MEM-015 (MEMORIA) | MEM-014 (MEMORIA) | dirigida | **sí** | **sí** | **sí** | **sí** — 5 tokens comunes (`escala`, `opciones`, `vuelo`) |
| **REL-008** | `SUSTITUYE_A` | DEC-013 (DECISIÓN) | DEC-012 (DECISIÓN) | dirigida | **sí** | **sí** | **sí** | **sí** — 8 tokens comunes y misma familia de sujeto |
| **REL-009** | `CORRIGE` | DEC-013 (DECISIÓN) | DEC-012 (DECISIÓN) | dirigida | **sí** | **sí** | **sí** | **sí** — mismo par que REL-008 |
| REL-003 | `APOYA` | DOC-001 (**documento**) | DEC-006 (DECISIÓN) | dirigida | destino sí; origen es evidencia atribuida de E4 | sí | solo E4 | n/a |
| REL-005 | `ALIAS_DE` | ENT-PROY-ALFA (**entidad**) | PRJ-ALFA (**proyecto**) | dirigida | ninguno es ítem | sí | E2 (alias) | n/a |
| REL-006 | `DERIVA_DE` | MEM-017 (MEMORIA) | DOC-004 (**documento**) | dirigida | origen sí; destino es documento | sí | solo E4 | n/a |
| REL-007 | `ORIGINA_CANDIDATA` | MSG-020 (**mensaje**) | MEM-007 (MEMORIA) | dirigida | destino sí; origen es historial de E4 | sí | solo E4 | n/a |

### 7.1 Por qué `nota` es oráculo y no puede exponerse

Cada `nota` cita el caso que la arista instancia — por ejemplo, «B04-CA-05 / CA-23: relación de sustitución explícita». Un candidato que la leyera sabría **qué se espera de él** en ese caso concreto: no es una descripción de la arista, es la respuesta. Se prohíbe en §6.5.

En cambio `tipo`, `origen` y `destino` describen **qué es** la arista, no qué debe hacerse con ella, y por eso son entrada.

### 7.2 Aclaración exigida

**Ninguna arista se clasifica como no utilizable por el mero hecho de que hoy falte un cargador.** La ausencia de cargador es una condición **transitoria y resoluble** de la proyección experimental (§6), no una propiedad de la arista. Las cinco aristas ítem↔ítem son **admisibles**; su problema es otro, y es el del §8.

---

## 8. Adjudicación de suficiencia funcional de ADR002-C

### 8.1 Veredicto

# **B · ADMISIBLE PERO INSUFICIENTE**

Existe fuente relacional admisible —`decisions.supersedes_decision_id` en el canon, y cinco aristas ítem↔ítem en el corpus congelado—, pero **ninguna permite un caso discriminante honesto**.

### 8.2 Demostración, arista por arista

El caso discriminante exige un destino que `A` completo (E0–E5) **no** alcance y que `C` alcance **solo** por la arista. Se comprobó, por análisis estático sobre el corpus como dato de entrada, con la misma regla de tokenización del índice FTS5 (`unicode61` + plegado de diacríticos, tokens ASCII):

| Arista | Tokens de contenido compartidos entre extremos | ¿A alcanza el destino? | Razón adicional |
|---|---|---|---|
| REL-001 | `presupuesto`, `maximo`, `proyecto` (6 en total) | **sí** | Además, la supersesión canónica **obliga** a mismo `subject` y `project_id`: A los alcanza por familia de sujeto |
| REL-002 | `presupuesto`, `beta` (5 en total) | **sí** | Mismo proyecto |
| REL-004 | `escala`, `opciones`, `vuelo` (5 en total) | **sí** | Los tres términos de contenido son compartidos |
| REL-008 | `aforo`, `maximo`, `sala`, `personas` (8 en total) | **sí** | Supersesión: misma familia de sujeto |
| REL-009 | idéntico a REL-008 | **sí** | Mismo par |

**En las cinco, una consulta que alcanza el origen alcanza también el destino por léxico.** No hay ni un solo destino que exija recorrer la arista.

Y una salvedad que cierra la única escapatoria aparente: `REL-004` cruza proyecto (PRJ-BETA → PRJ-ALFA), lo que podría parecer un discriminante en ámbito de proyecto. No lo es: **`G4` es común a todos los candidatos** y elimina el destino fuera de ámbito. `C` no puede relajar una puerta; si pudiera, la comparación mediría quién esquiva mejor el contrato.

### 8.3 Delta mínimo de un corpus sucesor

**No se modifica v0.4.** El acta de congelación §111 ya fija la convención: «Una versión posterior del corpus se materializa **junto a** la v0.4, con nueva acta y nuevos blobs; no se sobrescribe ningún congelado».

Delta mínimo propuesto para un `conformance_corpus_v0_5.json`:

| # | Requisito | Contenido |
|---|---|---|
| 1 | **Nueva versión** | `v0.5`, hereda de `v0.4`, materializada junto a ella |
| 2 | **Relación explícita neutral** | **Una** arista ítem↔ítem de un tipo que no sea supersesión ni conflicto —para no reutilizar señales que A ya cubre—, con dirección declarada |
| 3 | **Extremos sintéticos de entrada** | Dos ítems nuevos, con las siete dimensiones declaradas como cualquier otro |
| 4 | **Ausencia deliberada de solapamiento léxico** | **Cero** tokens de contenido compartidos entre los textos de origen y destino, verificado con la misma regla de tokenización del índice. Verificación mecánica, no a ojo |
| 5 | **Sin familia de sujeto compartida** | Sujetos distintos, de modo que la señal estructurada de A no los una |
| 6 | **Sin usar la pertenencia a proyecto como generador** | Ambos extremos en el mismo proyecto, para que el ámbito no sea la señal |
| 7 | **Generación independiente del resultado esperado** | El resultado esperado se deriva **después**, por regla cerrada, y nunca al revés. Debe poder auditarse el orden |
| 8 | **Nueva auditoría** | Auditoría independiente del delta, con las mismas puertas que la v0.4 |
| 9 | **Nueva congelación** | Acta propia con blobs propios; los siete blobs de v0.4 **permanecen intactos** |

### 8.4 Impacto exacto sobre TOL-208 y sobre las fichas

| Elemento | Impacto | Justificación verificada |
|---|---|---|
| **`ADR002-TOL-208`** | **NINGUNO** | T0 se midió sobre `performance_corpus_v0_2.json` (así lo fija `frozen_corpus.py`, `RUTA_CORPUS`), que es un artefacto **distinto** del corpus de conformidad. Un `conformance_corpus_v0_5.json` no toca ese blob |
| **Rederivación de T0** | **NO PROCEDE** | Solo procedería si el delta afectara al sustrato de T0, y no lo afecta |
| **Ficha `T0-control`** | **INTACTA** | No cambia su sustrato ni sus condiciones |
| **Fichas `A v3` y `B v5`** | **Intactas hasta la ola**; después, sucesoras por el cambio de contrato común, no por el corpus | El corpus sucesor por sí solo no altera el contrato |
| **Acta de congelación v0.4** | **INTACTA** | La v0.5 se materializa junto a ella, conforme a su §111 |

---

## 9. Tratamiento de `EJE-2`

Se registra expresamente, y es lectura literal de la resolución de partición aprobada (blob `269e960e…`):

1. **La ficha de candidato permite declarar la realización**: un candidato puede resolver las relaciones **desde el canon** o mediante un **índice relacional derivado**. Ambas son realizaciones admisibles de la misma alternativa mínima.
2. **Elegir una realización concreta para `C` no abre por sí mismo `EJE-2`.** `EJE-2` es un eje **contingente** definido como la *comparación* de las dos materializaciones: «Resueltas **desde el canon** frente a **índice relacional derivado**» (§6, línea 168).
3. **`EJE-2` solo se abre** si, **después** de la comparación primaria `A/B/C/D`, se decide comparar ambas materializaciones como **variantes adicionales**, y solo «cuando la evidencia demuestre que pueden cambiar materialmente la decisión» (§6.1 punto 2). Máximo dos fichas adicionales.
4. Por tanto, si `C` se implementa con índice derivado, **debe declararlo en su ficha** como realización, y esa declaración **no** constituye apertura de `EJE-2`.

---

## 10. Plan de una sola ola de corrección

Ejecutable **solo tras aprobación explícita**, en este orden y sin fragmentar:

| Paso | Contenido | Condición de cierre |
|---|---|---|
| **1** | Implementar la proyección experimental (§6), con lista blanca fallo-cerrada | Construcción verificada contra blobs congelados |
| **2** | Corregir `common/` **por completo**: contrato (§3), agrupación y salida (§4), `G5`/`G6`/`G7` (§5), orden de suficiencia y `G12` (§4.5) | Ruff, mypy y suite verdes |
| **3** | Emitir ficha sucesora de `ADR002-A` | Congelada antes de ejecutar; predecesora marcada SUSTITUIDA |
| **4** | Emitir ficha sucesora de `ADR002-B` | Ídem |
| **5** | Repetir **íntegramente** las pruebas de A y de B bajo las fichas nuevas | Suite verde bajo anterioridad estricta |
| **6** | Reaprobar `A` y `B` | **Aprobación explícita del usuario**; no automática |
| **7** | Implementar `C` sobre la fuente relacional aprobada | Solo tras 6 |
| **8** | Congelar `C` y ejecutar sus pruebas posteriores a la ficha | Ficha antes de la primera ejecución |
| **9** | Aprobar `C` | **Aprobación explícita** |
| **10** | Implementar `D`, con sus tres restricciones acumulativas intactas | Orden de etapas tardías declarado y congelado antes de ejecutar |
| **11** | **Solo entonces** solicitar autorización de benchmark | Autorización explícita e independiente |

**Una sola ola, una sola generación de fichas por candidato.** El plan corrige `common/` **una vez**: por eso incluye desde el principio las piezas que dependen de la proyección, en lugar de un arreglo parcial que obligaría a una segunda corrección y a una segunda generación de fichas.

**El paso 11 no está autorizado por esta resolución** y requiere un acto separado.

---

## 11. Lo que esta resolución NO autoriza

- ❌ Ejecutar el benchmark o cualquier medición. **El benchmark sigue bloqueado.**
- ❌ Reducir la comparación primaria `T0 + A + B + C + D`.
- ❌ Modificar Sirius 0.1.
- ❌ Modificar el corpus v0.4 ni ninguno de sus siete blobs.
- ❌ Modificar fichas o actas vigentes de `T0-control`, `A` o `B`.
- ❌ Crear estados nuevos de ficha.
- ❌ Transferir o anular retroactivamente aprobaciones.
- ❌ Abrir `EJE-1` o `EJE-2`.
- ❌ Fusionar el PR #117.

---

## 12. Cuestiones que requieren aprobación explícita

### 12.1 El eje `propiedad` — **DECISIÓN ABIERTA, sin implementación propuesta**

`B04-Q13` (línea 406) y `M-03` (línea 44) nombran **`propiedad`** como uno de los siete ejes de equivalencia. **Ninguna fuente aprobada lo define.** No tiene vocabulario, no tiene campo en el corpus congelado y no tiene columna en Sirius 0.1. Las otras dos apariciones del término en `B04` (líneas 33 y 214) lo usan en sentido corriente, no como dimensión.

**Decisión exacta que corresponde al usuario:** qué es «propiedad» como eje de agrupación — el atributo del sujeto sobre el que versa la afirmación (por ejemplo, *presupuesto máximo* frente a *aforo máximo* del mismo proyecto), o algo distinto — y con qué vocabulario o regla de derivación.

**Regla de fallo cerrado mientras no se decida, para no bloquear el resto:** si el eje `propiedad` no está determinado para dos elementos, **no se agrupan**. Es estrictamente conservador —agrupar de menos nunca pierde información; agrupar de más sí—, no inventa la semántica y no anticipa la decisión.

### 12.2 Atribución de proyecto a los mensajes — **DECISIÓN ABIERTA**

El corpus declara `mensajes[].project_id`, pero **Sirius 0.1 no atribuye proyecto a un mensaje**: ni `MessageModel` ni `ConversationModel` tienen esa columna, y no existe camino transitivo. Hoy el puerto los construye con `project_id=None`, lo que es **fiel al canon** y hace que `G4` los elimine en toda petición con ámbito de proyecto.

**Decisión exacta:** ¿la proyección experimental transporta el proyecto de los mensajes?

- **Si sí:** `E4` puede contribuir en ámbito de proyecto y los casos que lo requieren son medibles. La proyección es entonces más rica que Sirius 0.1 — legítimo en el plano P2, e igual para los cinco competidores, pero debe declararse.
- **Si no:** la evidencia atribuida de `E4` queda estructuralmente fuera de toda petición con ámbito de proyecto, y hay que declararlo como limitación conocida del banco.

**No propongo implementación hasta que se decida.** Mi lectura, si sirve: transportarlo, porque el banco debe poder medir lo que `B04` exige y la proyección es P2, no P3. Pero es una decisión de alcance, no de código.

### 12.3 Vocabularios de las dimensiones — **CONFIRMACIÓN REQUERIDA**

`experiments/adr002/benchmark/schema.py:3` afirma que las siete dimensiones y sus valores son «las canónicas de **ADR-001 v1.1**». **Los valores de `VALIDEZ`, `CONFIRMACION`, `DISPONIBILIDAD`, `SENSIBILIDAD` y `AUTORIDAD` no aparecen en ADR-001 v1.1**: ese documento nombra las siete dimensiones y ordena su ortogonalidad, pero **no enumera sus valores**, y su §6 remite «fijar vocabularios definitivos» a la arquitectura consolidada.

Son, por tanto, **convención local del benchmark**, no vocabulario aprobado. Propuesta: **usarlos tal cual para el plano experimental P2, declarando expresamente que son convención local y que no prejuzgan el vocabulario productivo**. No los cambio y no invento otros.

### 12.4 Otras cuestiones que requieren tu aprobación

1. La proyección experimental (§6) y su lista blanca fallo-cerrada.
2. La regla de agrupación de §4.2 y la estructura de salida de §4.3.
3. La regla de representante de §4.4.
4. La eliminación de `admite_no_vigentes` (§5.1).
5. El reparto `G6`/`G7` de §5.5 y los motivos de traza de §5.3.
6. El veredicto **B** de §8 y, si lo aceptas, el delta mínimo del corpus sucesor de §8.3.
7. El plan de una sola ola de §10.

---

## 13. Auditoría adversarial de esta propuesta

Se intentó refutar cada punto exigido. Resultado y correcciones aplicadas **antes** de publicar:

| # | Tesis atacada | Resultado |
|---|---|---|
| 1 | **¿Determina `B04` realmente la agrupación?** | **Sí, y más de lo que un informe previo sostuvo.** `Q13` (406) enumera los siete ejes y fija el criterio de representante; `RF-20` (438), `D09` (539) y `M-03` (44) lo refuerzan. **Salvo `propiedad`**, que se nombra y no se define: por eso §12.1 lo deja abierto en vez de inventarlo |
| 2 | **¿Es la proyección una modificación encubierta de Sirius 0.1?** | **No**, por cinco razones mecánicamente verificables (§6.3). Se añadió como condición de aprobación una prueba que comprueba por diff que `src/`, `migrations/` y `tests/` no cambian |
| 3 | **¿Son los campos permitidos entrada y no oráculo?** | Se revisó campo a campo. **Se movieron a la lista negra** `entidades[].grupo_homonimo` —declara qué no debe fusionarse, que es la respuesta de CA-14— y todas las notas que nombran casos. `mensajes[].project_id` quedó fuera de la lista blanca a la espera de §12.2 |
| 4 | **¿Es correcto el censo relacional?** | **Corregido.** Un censo previo contaba ocho aristas ítem↔ítem; el recuento directo sobre el blob congelado da **cinco**. Las otras cuatro tienen un extremo documento, entidad, proyecto o mensaje |
| 5 | **¿Abre un índice derivado automáticamente `EJE-2`?** | **No.** `EJE-2` es la *comparación* de ambas materializaciones, posterior a la ronda primaria (§9). Elegir una realización es declararla, no abrir el eje |
| 6 | **¿Bastan las relaciones existentes para `C`?** | **No.** Se comprobó con la tokenización real del índice: las cinco aristas tienen tokens de contenido compartidos entre extremos. Se cerró además la escapatoria de `REL-004` (cruce de proyecto), porque `G4` es común |
| 7 | **¿Favorece la solución a `A`, `B`, `C` o `D`?** | **No.** Mismo sustrato, mismo FTS5, mismo motor, mismas puertas, mismo puerto lógico y misma lista blanca para los cinco. Las reglas de agrupación y representante se aplican en la capa común, que ningún candidato controla. La proyección **no** añade la señal relacional que `C` necesitaría: por eso el veredicto sigue siendo **B** y no se convierte en un regalo a `C` |
| 8 | **¿Se requieren dos generaciones innecesarias de fichas?** | **No, con este plan.** Fue precisamente el motivo de rechazar la corrección parcial: incluir la proyección en el paso 1 permite corregir `common/` una sola vez |
| 9 | **¿Queda algún documento anterior reescrito?** | **No.** Dos ficheros nuevos en rutas inexistentes. Ningún documento aprobado se modifica; las actas de A y B conservan su validez íntegra |
| 10 | **¿Autoriza el plan silenciosamente el benchmark?** | **No.** El paso 11 exige autorización explícita e independiente, y §11 lo repite como prohibición. El bloqueo pre-benchmark se mantiene |

### 13.1 Correcciones de informes previos incorporadas

Esta resolución **no hereda** las siguientes afirmaciones, que no resistieron verificación:

- Que la sustituida se devuelva «sin marca»: la explicación **sí** estampa `estado` (`trace.py:129`).
- Que la pérdida de un miembro sea «silenciosa»: la traza **sí** registra la agrupación por identidad.
- Que `desbordamiento` deba activarse al agrupar: es término atado al **límite duro**; activarlo sería una declaración falsa.
- Que `project_id=None` en mensajes sea un descarte del puerto: es **representación fiel** de un canon sin esa columna.
- Que el destino de una decisión sustituida en M1 fuera pregunta abierta: `B04:207` y `decision.py:22-23` lo resuelven.
- Que el colapso de dimensiones contradiga `ADR-001` consecuencia 7: esa consecuencia es un mandato para la arquitectura consolidada, y el colapso es una condición **ya declarada y aprobada** del sustrato heredado.

---

## 14. Validación

| Comprobación | Resultado |
|---|---|
| Blobs de todas las fuentes citadas | verificados sobre el árbol de `a074eb5` |
| Corpus congelado intacto | los cuatro blobs contrastados contra el acta: **coinciden** |
| Fichas y actas de A y B intactas | sin cambios |
| `src/`, `tests/`, `migrations/` | sin cambios |
| Ruff format, Ruff lint, mypy, suite completa | ver informe de entrega |
| PR #117 | abierto y sin fusionar |

---

## 15. Estado

**PROPUESTA. NO APROBADA.**

Esta resolución requiere **aprobación explícita del usuario** para cualquiera de sus decisiones. Hasta entonces:

- el contrato común no se modifica;
- las fichas y actas vigentes permanecen intactas y válidas;
- **el benchmark permanece bloqueado** por el hallazgo pre-benchmark;
- la comparación primaria sigue siendo `T0 + A + B + C + D`, sin reducción;
- las dos cuestiones de §12.1 y §12.2 permanecen **abiertas**, sin implementación propuesta.
