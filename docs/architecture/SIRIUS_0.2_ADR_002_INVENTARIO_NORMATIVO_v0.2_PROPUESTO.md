# SIRIUS 0.2 — ADR-002 · Inventario normativo de recuperación, ranking e índices

**Versión:** 0.2
**Estado:** PROPUESTO · documento de análisis, no aprueba ni decide nada
**Fecha:** 25 de julio de 2026
**Sustituye a:** `SIRIUS_0.2_ADR_002_INVENTARIO_NORMATIVO_v0.1_PROPUESTO.md`, que se conserva sin modificar
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_01B_CORRECCION_CANONICA_v0.1.md`
**Dependencias satisfechas:** ADR-001 v1.1 APROBADO · B04 v1.0 APROBADO (23 de julio de 2026)
**No autoriza:** decisión de ADR-002, elección de alternativa técnica, implementación productiva, cambios en Sirius 0.1 ni merge.

---

## 0. Qué corrige esta versión

La v0.1 reconstruyó el reparto de obligaciones a números de RF **desde resúmenes por grupo**, porque el texto atómico de B04 no estaba en el repositorio. La fuente canónica ya está verificada y el paquete 01B la incorpora.

**Esta versión sustituye la reconstrucción por la correspondencia exacta.** Toda la evidencia técnica medida contra Sirius 0.1 se conserva sin cambios: lo que se corrige es la numeración normativa, las clasificaciones que dependían de ella y dos incertidumbres que resultaron no serlo.

Resumen de la corrección en §1. Nada de lo medido en la v0.1 se ha vuelto a medir, y nada medido ha cambiado.

---

## 1. Correcciones respecto de la v0.1

### 1.1 Hecho canónico que lo cambia todo

**[N]** `SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO` es canónico desde el 23 de julio de 2026. Quedaron aprobados la **alternativa B de B04**, B04-D01–D16, B04-RF-01–32, B04-CA-01–50, B04-M01–21, la política E0–E5, las puertas G1–G12 y las paradas S1–S7.

**[N]** ADR-002 **no puede reabrir esa decisión de producto**. Su objeto es la arquitectura técnica que materializa el comportamiento ya aprobado. La v0.1 no lo decía porque no lo sabía; la reformulación de la pregunta material está en `SIRIUS_0.2_ADR_002_RECUPERACION_RANKING_INDICES_v0.2_ABIERTO.md`.

### 1.2 Errores de numeración corregidos

**[H]** Ocho RF estaban mal asignados. Comparación literal entre lo que la v0.1 escribió y el texto canónico:

| RF | Reconstrucción v0.1 (incorrecta) | Texto canónico | Naturaleza del error |
|---|---|---|---|
| RF-01 | Consulta, `operation_id`, propósito y traza | Petición con consulta, `operation_id`, propósito, **modo, ámbito, tiempo, estados, criticidad, espacios, cardinalidad, límites** y traza | **Incompleto**: la v0.1 repartió en RF-03 lo que RF-01 ya contiene |
| RF-02 | Modo M1–M5 explícito y permiso asociado | **Bloquear o aclarar propósito/permiso no autorizado** | **Contenido equivocado** |
| RF-03 | Ámbito, tiempo, estados… declarados en la petición | **Adjudicar M1–M5 antes de recuperar y conservarlo en traza** | **Contenido equivocado** |
| RF-05 | Resolver entidades por ID estable | Resolver entidades por ID estable **y no fusionar homónimos o alias ambiguos** | **Incompleto**: los homónimos son de RF-05, no de RF-06 |
| RF-06 | Impedir la fusión de homónimos | **Aislamiento global, proyecto y multi-proyecto cerrado sin ampliación silenciosa** | **Contenido equivocado.** El ámbito es RF-06 |
| RF-07 | Aplicar ámbitos global/proyecto/multi-proyecto cerrado | **Aplicabilidad respecto del tiempo objetivo; «ahora» solo como valor predeterminado** | **Contenido equivocado.** El tiempo objetivo es RF-07 |
| RF-10 | Excluir eliminado y purgado | Excluir eliminado, **no guardado** o purgado | **Incompleto** |
| RF-11 | Excluir no guardado y «no usar como memoria» | Excluir **de M1 y fallback** lo marcado «no usar como memoria/no consolidable» | **Impreciso**: la exclusión es por modo, no universal |

**[H]** Consecuencia práctica para el hallazgo principal: **la fuga de ámbito medida incumple B04-RF-06**, no RF-07 como decía la v0.1. La medición no cambia; su trazabilidad normativa sí.

**[H]** Los veinticuatro RF restantes coincidían en sustancia con el texto canónico. Diecisiete ganan precisiones materiales que la v0.2 incorpora, señaladas en la §4.

### 1.3 Dos incertidumbres que no lo eran

**[H]** La v0.1 declaró como incertidumbres bloqueantes «la puerta de suficiencia no está definida» y «"crítico" no está definido». **Ambas eran falsas**: B04 las tiene definidas y el paquete 01B las transcribe. Se retiran de la lista de incertidumbres y pasan a §5 y §6 como contrato vinculante.

**[H]** Corrección asociada, importante: la v0.1 conjeturó que la negación «no la resuelve ninguna alternativa por sí sola». B04 ya lo resolvió normativamente — **RF-17 exige que la etapa de significado y relaciones valide sujeto, polaridad, condición y tiempo**. Deja de ser una conjetura arquitectónica y pasa a ser una obligación de cualquier realización técnica.

### 1.4 Lo que no cambia

**[H]** Ninguna medición se ha repetido y ninguna ha cambiado. Los dos hallazgos inseguros siguen siendo los mismos, con la misma evidencia, y solo se retrazan a su RF correcto. La caracterización de FTS5 permanece íntegra en `SIRIUS_0.2_ADR_002_LINEA_BASE_FTS5_v0.2_PROPUESTO.md`.

---

## 2. Cómo leer este documento

| Marca | Significado |
|---|---|
| **[H]** | **Hecho verificado.** Comprobado en el repositorio real: código, migraciones, pruebas o medición directa. Reproducible. |
| **[N]** | **Obligación normativa canónica.** Procede de B04 v1.0 APROBADO, ADR-001 v1.1 APROBADO o los paquetes de trabajo 01 y 01B. No es negociable por el código de 0.1. |
| **[?]** | **Hipótesis o incertidumbre real.** Requiere decisión o experimento posterior. No es base suficiente para decidir. |

**[N]** Si el código de 0.1 contradice una obligación aprobada de 0.2, prevalece la obligación de 0.2.

---

## 3. Estado de las fuentes

**[H]** Tras la incorporación de la fuente canónica:

| Fuente | ¿Disponible para este trabajo? |
|---|---|
| Texto exacto de B04-RF-01 a RF-32 | **Sí** — §2.2 del paquete 01B |
| Mapeo canónico RED-027 a RED-034 | **Sí** — §2.5 del paquete 01B |
| Contrato de suficiencia | **Sí** — §2.3 |
| Contrato de criticidad | **Sí** — §2.4 |
| Decisión de producto B04 (alternativa B) | **Sí** — §2.1 |
| ADR-001 v1.1, ADR-002 abierto, paquetes 01 y 01B | **Sí** — en el repositorio |
| Código y pruebas de Sirius 0.1 | **Sí** — en el repositorio |
| Texto de B04-CA-01–50 | **No** — solo se conocen los CA citados en el mapeo RED |
| Texto de B04-M01–21 | **No** — solo los M citados en el mapeo RED |
| Texto de B04-D01–D16 | **No** |
| Texto de G1–G12, S1–S7 y detalle de E0–E5 | **No** — se conoce su existencia y su papel, no su enunciado |
| Definición de las familias PDP | **No** — se conocen sus identificadores |
| ARQ-00 v1.0 | **No** |
| Registro de Tolerancias | **No** |

**[?]** Lo que sigue sin estar disponible ya no afecta a la numeración de los RF, que es exacta, pero sí limita la trazabilidad del benchmark a casos CA concretos. Se trata explícitamente en la especificación de benchmark v0.2 y en §8.

---

## 4. Inventario B04-RF-01 a RF-32

**[N]** La columna «obligación canónica» reproduce el texto de la §2.2 del paquete 01B. **[H]** La columna «estado» es la clasificación del §8 del paquete 01, recalculada sobre la numeración correcta con la evidencia ya medida.

Clases: `EXISTENTE` · `PARCIAL` · `AUSENTE` · `INSEGURO` (existe pero no es admisible para 0.2) · `OTRO-ADR`.

### 4.1 Petición, permiso, modo y aclaración — RF-01 a RF-04

| RF | Obligación canónica **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-01 | Petición con consulta, `operation_id`, propósito, modo, ámbito, tiempo, estados, criticidad, espacios, cardinalidad, límites y traza | **AUSENTE** | `RankRelevantKnowledgeUseCase.rank(query_text: str)` recibe únicamente texto. Ninguno de los doce elementos viaja en la petición |
| RF-02 | Bloquear o aclarar propósito/permiso no autorizado | **AUSENTE** | No existe noción de permiso ni de propósito en la recuperación |
| RF-03 | Adjudicar M1–M5 antes de recuperar y conservarlo en traza | **AUSENTE** | No existe noción de modo en `src/` |
| RF-04 | Aclaración mínima ante ambigüedad material antes de generar candidatos | **AUSENTE** | No hay puerta de aclaración: una consulta ambigua produce candidatos directamente |

### 4.2 Identidad, ámbito y tiempo — RF-05 a RF-08

| RF | Obligación canónica **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-05 | Resolver entidades por ID estable y **no fusionar homónimos o alias ambiguos** | **PARCIAL** | Los ids de memoria y decisión son estables y se usan como espacio sintético en el índice y en el desempate. No hay resolución de entidad, ni alias, ni protección de homónimos: la consulta es texto libre contra el índice |
| RF-06 | **Aislamiento global, proyecto y multi-proyecto cerrado sin ampliación silenciosa** | **INSEGURO** | **Medido**: con dos proyectos, la consulta `presupuesto` devuelve también el contenido del proyecto ajeno. `list_current_memories()` no filtra por proyecto y `project_matches_active` es el segundo elemento de la clave de orden, no una puerta |
| RF-07 | Aplicabilidad respecto del **tiempo objetivo**; «ahora» solo como valor predeterminado | **AUSENTE** | 0.1 opera siempre en un «ahora» implícito. No se declara como valor predeterminado ni admite otro tiempo objetivo |
| RF-08 | Consultas por tiempo válido, evento e historial con **corte de registro** | **AUSENTE** | 0.1 solo tiene `created_at`/`updated_at`, que son tiempo de registro. Existe `get_history`, pero sin corte de registro ni eje de validez |

### 4.3 Puertas y exclusiones — RF-09 a RF-13

| RF | Obligación canónica **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-09 | **G1–G10 antes de candidatos; G11 antes de agrupar/ordenar; G12 antes de límite/handoff** | **PARCIAL** | La forma existe —`rank_relevant_knowledge` filtra antes de ordenar y el dominio reverifica por su cuenta— pero no la estructura: no hay puertas identificadas ni las tres fases de aplicación |
| RF-10 | Excluir eliminado, **no guardado** o purgado | **PARCIAL** | Eliminado: cumplido y probado — `delete_memory` anula `content` en todas las revisiones y el trigger retira la fila del índice en la misma transacción. «No guardado» y purgado no existen como marcas en 0.1 |
| RF-11 | Excluir **de M1 y fallback** lo marcado «no usar como memoria/no consolidable» | **AUSENTE** | No existe la marca ni el modo que condiciona la exclusión |
| RF-12 | Estados especiales solo elegibles en modos autorizados | **AUSENTE** | No hay modos. El archivado se excluye siempre, sin excepción autorizable |
| RF-13 | Evidencia externa atribuida y no canónica | **AUSENTE** | 0.1 no incorpora evidencia externa a la recuperación |

### 4.4 Expansión escalonada E0–E5 — RF-14 a RF-18

**[N]** E0–E5, G1–G12 y S1–S7 proceden de B04 y **no son objeto de decisión en ADR-002**.

| RF | Obligación canónica **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-14 | Ejecutar E0–E5 **sin salto a recuperación amplia** | **INSEGURO** | 0.1 hace exactamente el salto que la obligación prohíbe: una sola pasada de índice más un barrido completo de todo el conocimiento vigente, sin etapas |
| RF-15 | Comenzar por recuperación estructurada y exacta | **PARCIAL** | Existe señal estructurada —asunto de decisión, pertenencia a proyecto— pero no está escalonada respecto de la léxica: ambas se calculan siempre y a la vez |
| RF-16 | Variantes léxicas y alias confirmados **solo tras insuficiencia anterior** | **AUSENTE** | Sin lematización, sin alias, sin prefijo (medido). Y sin noción de insuficiencia que pudiera disparar la etapa |
| RF-17 | Significado y relaciones **con validación de sujeto, polaridad, condición y tiempo** | **AUSENTE** | No hay señal semántica ni relacional. La obligación de validar polaridad es la respuesta canónica al hallazgo de negación |
| RF-18 | Fuentes e historial solo como etapa autorizada, con **clase de evidencia** y cotejo con estado vigente/sustituido/contradictorio/candidata | **PARCIAL** | El historial existe y el mensaje fuente se resuelve, pero no como etapa autorizada, sin clase de evidencia y sin las cuatro categorías de cotejo |

### 4.5 Fidelidad semántica — RF-19 a RF-21

| RF | Obligación canónica **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-19 | Preservar negación, condición, refutación y postura | **INSEGURO** | **Medido**: la consulta `café` devuelve por igual «prefiere café» y «NO prefiere café»; la consulta `prefiere` también devuelve ambas. Nada en el camino representa la polaridad |
| RF-20 | Deduplicar solo con equivalencia material, incluido ámbito y postura; **conservar procedencias y diferencias** | **AUSENTE** | No hay deduplicación en la recuperación, ni procedencia múltiple en el modelo de 0.1 |
| RF-21 | **Recuperar y marcar** todos los lados elegibles de un conflicto sin resolverlo silenciosamente | **PARCIAL** | `find_prevailing_decision` (B4e) resuelve la precedencia y suprime el lado no prevaleciente durante el ensamblado de contexto. No hay marcado de lados |

### 4.6 Ranking, criticidad, límites y ausencia — RF-22 a RF-26

| RF | Obligación canónica **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-22 | Ordenar solo elegibles **y emitir razones mínimas por resultado** | **PARCIAL** | Se ordenan solo vigentes y relacionados, y el criterio es inspeccionable; pero «elegible» en 0.2 incluye ámbito, tiempo y sensibilidad, que no se comprueban, y no se emite una razón por resultado |
| RF-23 | Propagar **nivel, razón, fuente y regla aprobada** de criticidad; prohibido el auto-marcado libre | **AUSENTE** | No existe criticidad en el modelo ni en el orden |
| RF-24 | Respetar límite objetivo y duro; **no ocultar desbordamiento crítico** | **PARCIAL** | Hay un único recorte aguas abajo, en el ensamblado de contexto, sin distinción objetivo/duro y sin señalizar desbordamiento |
| RF-25 | Adjudicar **suficiencia interna por cardinalidad** y taxonomía completa; salida externa segura cuando ausencia y no-reportable no puedan distinguirse | **AUSENTE** | No hay cardinalidad declarada, ni suficiencia, ni taxonomía |
| RF-26 | Mantener ausencia y no-reportable indistinguibles externamente **dentro de tolerancias de texto, estado, conteo y tiempo** | **AUSENTE** | Al no existir la distinción interna, tampoco existe la protección externa |

### 4.7 Contrato, explicación y trazabilidad — RF-27 a RF-32

| RF | Obligación canónica **[N]** | Estado **[H]** | Evidencia |
|---|---|---|---|
| RF-27 | Entregar **a B05** resultados, estados, evidencia, criticidad, orden inicial, límites y suficiencia | **PARCIAL** | Se entrega una tupla ordenada con tres booleanos por elemento. Faltan evidencia, criticidad, límites aplicados y suficiencia |
| RF-28 | Explicar **coincidencia, ámbito, tiempo, estado, procedencia, criticidad y razón de orden** | **PARCIAL** | Coincidencia y estado son inspeccionables; ámbito lo es como booleano de orden, no como puerta. Faltan tiempo, procedencia, criticidad y razón explícita de orden |
| RF-29 | Registrar plan reproducible con puertas, etapas, expansiones, agrupaciones y parada | **AUSENTE** | No se registra plan alguno |
| RF-30 | Consultas internas solo desde operación activa que **herede propósito, permiso, ámbito, tiempo y límites** | **AUSENTE** | Ver RF-01 |
| RF-31 | Neutralidad tecnológica | **EXISTENTE** | `KnowledgeSearchRepository` es un `Protocol` sin dependencia de motor; el dominio no conoce SQLite |
| RF-32 | Degradación segura por **S3/S4/S7** o evidencia insuficiente, con salida parcial reproducible | **PARCIAL** | Consulta vacía o solo puntuación devuelve vacío sin error. No hay degradación ante fuente inaccesible ni salida parcial señalizada |

### 4.8 Comprobación de cobertura

**[H]** Los treinta y dos números RF-01…RF-32 aparecen **exactamente una vez** en las tablas 4.1–4.7. Sin huecos, sin duplicados, sin reconstrucción propia.

| Clase | Nº | RF |
|---|---|---|
| `EXISTENTE` | 1 | RF-31 |
| `PARCIAL` | 11 | RF-05, RF-09, RF-10, RF-15, RF-18, RF-21, RF-22, RF-24, RF-27, RF-28, RF-32 |
| `AUSENTE` | 17 | RF-01, RF-02, RF-03, RF-04, RF-07, RF-08, RF-11, RF-12, RF-13, RF-16, RF-17, RF-20, RF-23, RF-25, RF-26, RF-29, RF-30 |
| `INSEGURO` | 3 | **RF-06** (ámbito), **RF-14** (salto a recuperación amplia), **RF-19** (negación) |

**[H]** 1 + 11 + 17 + 3 = **32**. Cada RF aparece en exactamente una clase. La clase `OTRO-ADR`, que la v0.1 usaba para RF-13 y RF-17, queda vacía: con el texto canónico, ambos son obligaciones de B04 sobre la recuperación y están ausentes en 0.1.

**[H]** Diferencias de clasificación respecto de la v0.1, todas por corrección de numeración o de exigencia canónica, **ninguna por evidencia nueva**:

- **RF-06** pasa a `INSEGURO` (era la casilla del ámbito, mal numerada como RF-07 en la v0.1).
- **RF-07** pasa a `AUSENTE` (tiempo objetivo, que la v0.1 no inventarió como tal).
- **RF-14** pasa de `AUSENTE` a `INSEGURO`: el texto canónico prohíbe expresamente el «salto a recuperación amplia», y eso es exactamente lo que hace el barrido completo de candidatos de 0.1. La v0.1, con el texto resumido, no podía verlo.
- **RF-13** y **RF-17** dejan de estar en `OTRO-ADR`: son obligaciones de B04 sobre la recuperación, ausentes en 0.1.

**[N]** Los tres `INSEGURO` son las puertas previas comunes: **ninguna** realización técnica puede heredar el tratamiento actual del ámbito, del salto de expansión ni de la negación.

---

## 5. Contrato de suficiencia

**[N]** Transcrito de la §2.3 del paquete 01B. **No es una laguna: es contrato aprobado.**

La suficiencia depende de:

1. cardinalidad `EXACTA`, `ACOTADA` o `EXHAUSTIVA`;
2. cobertura de críticos elegibles pendientes;
3. etapas autorizadas ya ejecutadas;
4. taxonomía interna de resultado/ausencia;
5. paradas S1–S7.

**[N]** Reglas duras que se derivan:

- Solo se expande cuando **falta suficiencia** o **quedan críticos** y el siguiente espacio está autorizado.
- Una consulta **exhaustiva no puede detenerse por S1**.
- La ausencia interna solo se adjudica **tras agotar las etapas autorizadas pertinentes** y registrar espacios, puertas, parada y limitaciones.

**[N]** La tarea de ADR-002 **no es inventar el concepto**, sino convertir este contrato en política técnica verificable y fijar las tolerancias que B04/PDP delegaron.

**[H]** Estado en 0.1: `AUSENTE` por completo. No hay cardinalidad declarada, ni etapas, ni taxonomía, ni paradas.

---

## 6. Contrato de criticidad

**[N]** Transcrito de la §2.4 del paquete 01B. **Tampoco es una laguna.**

La criticidad procede de uno de estos orígenes trazables:

- requisito o decisión aprobada;
- acto explícito;
- etiqueta de escenario;
- regla operativa aprobada con ID y evidencia.

**[N]** No puede autoasignarse por intuición libre. Debe transportar **nivel, razón, fuente y regla** hasta B05. Es **corregible**, y no constituye una nueva verdad canónica.

**[H]** Estado en 0.1: `AUSENTE`. No existe criticidad en ninguna capa.

**[?]** Lo que sigue abierto no es la definición sino su **umbral operativo**: qué fracción de críticos elegibles debe cubrirse para adjudicar suficiencia. Eso es una tolerancia delegada, no una definición faltante.

---

## 7. Delegaciones RED con su mapeo canónico

**[N]** Mapeo exacto de la §2.5 del paquete 01B. **No se reconstruye por resumen.**

| RED | Mapeo canónico | Estado en 0.1 **[H]** |
|---|---|---|
| RED-027 | RF-01–04 → F01–F06 → B04-CA-01/05/08/15 → B04-M13/M15 | AUSENTE en los cuatro RF |
| RED-028 | RF-07–08 → F02/F03 → B04-CA-06/07/32/47 → B04-M11 | AUSENTE: ningún eje temporal existe |
| RED-029 | RF-18/RF-29 → F24 → B04-CA-40/44 → B04-M15 | RF-18 PARCIAL, RF-29 AUSENTE |
| RED-030 | RF-20–24 → F10/F14 → B04-CA-19/31/38 → B04-M10 | RF-20 y RF-23 AUSENTE; RF-21, RF-22 y RF-24 PARCIAL |
| RED-031 | RF-25/M09 → F23 → B04-CA-17/36 → B04-M09 | AUSENTE |
| RED-032 | RF-26/M20 → F11/F23 → **usar el mapeo exacto del Plan canónico** | AUSENTE. **[H]** Los CA concretos no figuran en el paquete 01B: la traza queda pendiente contra el Plan de Pruebas, y **no se inventa** |
| RED-033 | M16/CA-39 → F22 → tolerancia de orden y equivalencia observable | PARCIAL: existe el puerto y un doble simulado; no hay prueba de portabilidad |
| RED-034 | RF-31–32 → F10/F23 → fuente inaccesible y degradación parcial reproducible | RF-31 EXISTENTE, RF-32 PARCIAL |

**[N]** **RED-040 pertenece a B05/ADR-003B.** ADR-002 solo **registra la interfaz** de reintento acotado: no la diseña y no la usa como requisito propio de selección técnica. La v0.1 ya lo trataba así; se confirma.

**[H]** Familias PDP referenciadas por las fuentes canónicas, unión del paquete 01 (§6) y del mapeo RED: **F01, F02, F03, F04, F05, F06, F10, F11, F14, F15, F22, F23, F24**. La v0.1 solo conocía ocho de las trece.

**[H]** Métricas B04 citadas por el mapeo: **M09, M10, M11, M13, M15, M16, M20**. Las catorce restantes de M01–M21 no figuran en el paquete 01B.

---

## 8. Invariantes y su consecuencia para la recuperación

**[N]** Los once invariantes del §3 del paquete 01, retrazados a la numeración canónica. La evidencia es la misma que la v0.1.

| # | Invariante **[N]** | RF canónico | Estado **[H]** |
|---|---|---|---|
| I-01 | Fuente canónica única; los derivados son regenerables | — (ADR-001 c.1) | Cumplido en forma |
| I-02 | Privacidad, permiso, existencia, ámbito, tiempo, confirmación, disponibilidad, sensibilidad y no uso se resuelven antes de ranking | RF-09 | Parcial |
| I-03 | Eliminado, purgado, no guardado, restringido no autorizado o fuera de ámbito nunca es candidato | RF-10, RF-11 | Parcial |
| I-04 | Multi-proyecto cerrado sin ampliación silenciosa | **RF-06** | **Incumplido (medido)** |
| I-05 | Tiempo válido y corte de registro independientes | RF-07, RF-08 | Ausente |
| I-06 | Homónimos no se fusionan; alias ambiguos no expanden sin resolución | **RF-05**, RF-16 | Ausente |
| I-07 | Negación, condición, postura, apoyo/refutación y conflicto no se pierden | RF-19, RF-17, RF-21 | **Incumplido (medido)** |
| I-08 | Los críticos dominan el presupuesto; el límite duro produce estado parcial visible | RF-23, RF-24 | Ausente |
| I-09 | Cada resultado debe ser explicable | RF-22, RF-28 | Parcial |
| I-10 | Ninguna tecnología concreta es obligatoria por producto | RF-31 | Cumplido |
| I-11 | Solo una operación activa y autorizada puede iniciar una búsqueda interna | RF-30 | Ausente |

---

## 9. Herencia obligatoria de ADR-001

**[N]** Sin cambios respecto de la v0.1:

1. Índices, FTS, caches, resúmenes, vistas y paquetes de contexto son **derivados regenerables**; ninguno puede consultarse como autoridad ni sobrevivir semánticamente a la eliminación de su fuente.
2. El borrado debe destruir explícitamente contenido, procedencia recuperable y **todos** los derivados afectados. Toda realización técnica que introduzca un índice nuevo hereda esta obligación.
3. Tiempo válido y tiempo de registro permanecen separados — coincide con RF-07 y RF-08.
4. Las siete dimensiones canónicas permanecen **ortogonales**: confirmación, validez, disponibilidad, sensibilidad, temporalidad, ámbito y autoridad. La recuperación debe poder filtrar por cada una por separado.
5. El ámbito multi-proyecto es **cerrado y se filtra antes de recuperación y ranking** — coincide con RF-06, que es exactamente lo que 0.1 incumple.

**[N]** `secure_delete` y la secuencia de purga siguen pendientes de verificación sobre el ejecutable real de Windows. Todo índice nuevo hereda esa verificación.

---

## 10. Incertidumbres reales restantes

Todas **[?]**. Se han retirado las dos falsas de la v0.1.

1. **Registro de Tolerancias.** No existe todavía. Sin él no puede fijarse ninguna cifra de recall, latencia, coste, tamaño ni estabilidad. **[N]** El paquete 01B lo asigna expresamente al paquete siguiente y **prohíbe crearlo dentro de esta corrección**.
2. **Tolerancias ya congeladas frente a delegadas.** Parte de las cifras puede estar ya fijada en B04/PDP —RF-26 habla de «tolerancias de texto, estado, conteo y tiempo» y RED-032/RED-033 las presuponen— y otra parte estar delegada a Arquitectura. Separarlas es tarea del paquete siguiente.
3. **Trazabilidad a casos CA concretos.** Solo se conocen los CA citados en el mapeo RED (CA-01, 05, 06, 07, 08, 15, 17, 19, 31, 32, 36, 38, 39, 40, 44, 47). Los restantes de CA-01–50 no están disponibles, y los de RED-032 se difieren expresamente al Plan canónico.
4. **Umbral operativo de cobertura de críticos.** La criticidad está definida; el porcentaje que satisface la suficiencia, no. Es tolerancia, no definición.
5. **Elección técnica entre T1, T2, T3 y T4.** Es el objeto de ADR-002 y sigue enteramente abierta.
6. **Dónde actúa la precedencia.** RF-21 obliga a recuperar **y marcar** todos los lados elegibles sin resolver. `find_prevailing_decision` hoy suprime el no prevaleciente en el ensamblado de contexto. La obligación sobre la capa de recuperación es ahora inequívoca; lo que queda abierto es si la precedencia se aplica en contexto (ADR-003B) o solo en presentación.
7. **Copia física del contenido en el índice derivado.** **[H]** `knowledge_fts` almacena una copia literal del texto canónico. **[?]** Si 0.2 exige que ningún derivado retenga contenido en claro, condiciona el diseño de todos los índices de T1–T4.
8. **Frontera exacta con ADR-003B.** RF-27 fija el destinatario —B05— y el contenido de la entrega. Lo que queda por delimitar es dónde termina la responsabilidad de recuperación y empieza el ensamblado del paquete de contexto.
9. **Alcance del registro de entidades y alias.** RF-05 exige ID estable y no fusión de homónimos. Si eso obliga a un registro de entidades, puede ser diseño de modelo y no de recuperación.
10. **Coste de la verificación en Windows.** Heredado de ADR-001 y aplicable a todo índice nuevo.

---

## 11. Lo que este documento no decide

**[N]** No reabre B04 ni su alternativa B. No reabre E0–E5, G1–G12 ni S1–S7. No elige entre T1, T2, T3 y T4. No propone modelos de embedding, extensiones ni fórmulas de fusión. No fija cifras. No crea el Registro de Tolerancias. No modifica `src/`, `tests/`, `migrations/` ni configuración productiva. No sustituye B04-CA-01–50 ni el PDP.

---

**Siguiente movimiento único:** revisar los cuatro documentos de la corrección 01B y decidir si se abre el paquete específico del Registro de Tolerancias.
