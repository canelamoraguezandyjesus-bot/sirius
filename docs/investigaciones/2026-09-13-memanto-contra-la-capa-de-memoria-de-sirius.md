# Memanto contra la capa de memoria de Sirius: qué está cubierto, qué a medias y qué es nuevo

Fecha: 13-09-2026. Rama de auditoría. **Solo análisis**: ni código, ni ADR, ni
ampliación del permiso activo. Lo que salga de aquí es una mejora candidata que
el propietario decide.

## Por qué se hace

El propietario investigó Memanto (`moorcheh-ai/memanto`, MIT) y trajo cuatro
piezas candidatas (A–D) para «Memoria útil». Pide contrastarlas con lo que Sirius
ya tiene, decir cuál está cubierta, cuál a medias y cuál es nueva, y para las
nuevas el encaje mínimo: bloque documental, contrato y riesgo.

## Nota de arranque: qué se verificó y qué no

- **Memanto no se ha leído desde aquí.** Todo lo que se afirma de Memanto viene
  del propietario, que dice haberlo verificado leyendo el repositorio. Esta nota
  no lo re-verifica: no hay salida de red desde la sesión y no es el objeto.
- **Todo lo que se afirma de Sirius está leído del árbol de `main` en
  `7aae33c`**, con fichero y línea. Ninguna afirmación sobre Sirius sale de
  memoria ni de un documento: sale del código o de un documento citado.
- Criterio de «cubierta / a medias / nueva», fijado antes de mirar: **cubierta**
  si existe en el código de producción con prueba; **a medias** si existe la
  mitad de la función o existe solo en el banco/motor por etapas y no en el
  almacén real; **nueva** si no hay nada en el árbol ni en un encargo pendiente.

## Lo que Sirius tiene hoy, leído del árbol

| pieza de Sirius | dónde | qué hace |
|---|---|---|
| Estados de memoria `CURRENT / ARCHIVED / DELETED` | `src/sirius/domain/memory.py:12-19` | Ciclo de vida. Las revisiones son historia, no estado. |
| Estados de decisión `PROPOSED / APPROVED / SUPERSEDED / ARCHIVED` | `src/sirius/domain/decision.py` | Con enlace `supersedes_decision_id`. |
| Archivar, explícito, con evento de auditoría | `src/sirius/application/archive_memory.py:54` | Solo mueve `status`; **nada automático lo llama** (PA-015). |
| Eliminar: redacta el contenido de TODAS las revisiones, deja marcador | `src/sirius/application/delete_memory.py` | Irreversible por diseño (DR-012). |
| Evento de auditoría | `src/sirius/domain/event.py:38` | `event_type, actor, message_id, created_at, redacted_at`. **Sin campo de motivo.** |
| Tipos de evento | `src/sirius/domain/event.py:23-34` | `memory.archived`, `memory.deleted`, `decision.superseded`… **No hay `memory.unarchived`.** |
| Desarchivar | — | **No existe** ningún caso de uso que devuelva `ARCHIVED → CURRENT`. |
| Columnas persistidas de memoria | `src/sirius/adapters/persistence/models.py:208` | `status, subject_key, project_id, created_at, updated_at, category, category_locked, criticality`. **Sin `valid_from/valid_to`, sin `archived_at`, sin motivo.** |
| Precedencia y conflicto, deterministas, sin leer contenido | `src/sirius/domain/precedence.py:11` | `NO_CONFLICT / DECISION_PRECEDENCE / CONFLICT`, nombrando los ítems. «Never tries to decide whether two records are about the same thing from their text.» |
| Sustituir decisión | `src/sirius/application/supersede_decision.py` | Orden explícita, enlace persistente. |
| Sugerencia de memoria `PENDING / CONFIRMED / REJECTED` | `src/sirius/domain/memory_suggestion.py:19` | Nunca es memoria hasta confirmar. |
| Ventana temporal de la petición | `src/sirius/domain/staged_engine_contracts.py:157-197` | `tiempo_objetivo` (vigencia «a fecha de»), `tiempo_objetivo_desde` (intervalo, ADR-168), `corte_de_registro` («qué sabía yo el…»). |
| Esos tres campos en la intención de consulta | `src/sirius/domain/query_intent.py:38-45` | Se extraen de la pregunta. |
| Puerta `G8` | `src/sirius/domain/staged_engine_gates.py:233,240` | `created_at > corte` excluye; `valid_to <= objetivo` excluye salvo `admite_no_vigentes`. |
| Consulta por ventana de vigencia | `src/sirius/domain/staged_engine_contracts.py:541` | `por_ventana_de_vigencia(desde, hasta)`. |
| Ejes declarados (`valid_from`, `valid_to`, `polaridad`…) | `src/sirius/domain/staged_engine_contracts.py:245-277` | **`SIN_EJES` es «el valor que todo candidato real del producto recibe hoy»**: solo el banco los declara. |
| Estado publicado de lo no vigente | `src/sirius/domain/staged_engine_trace.py:86-113` | «no vigente: archivado / sustituido / finalizado» cuando el eje lo dice. |
| Polaridad, consumida de verdad | `src/sirius/domain/staged_engine_gates.py:310` | `conflictos_de_polaridad` por sujeto; lo llama `staged_engine.py:328`. |
| Declaración de ausencia sin filtrar existencia | `src/sirius/domain/staged_engine_contracts.py:467-479` | `Suficiencia` interna; estado externo único `SIN_RESULTADO_UTILIZABLE`. |
| Exportación abierta (S12.1, B9 completo) | `src/sirius/ports/export.py`; `adapters/export/filesystem_export_service.py:33-37` | `manifest.json, conversation.jsonl, project.json, memories.jsonl, decisions.jsonl, README.txt`. Solo lectura, atómica, sin secretos. |
| `MEMORIA.md` | `src/sirius_engine/memoria_cli.py` (ADR-171) | Vista Markdown **de las lecciones de los ADR**, generada y con guardián. No es la memoria del usuario. |
| Configuración declarativa | `src/sirius/config/settings.py:11-32` | `settings.json` (JSON, no YAML); ya se lee de ahí `category_matching_enabled`. |
| Permiso vigente | `docs/evolution/STATUS.md:14` y «No autorizado todavía» | 0.2 **limitada a sus cinco bloques**; el resto del roadmap NO está autorizado. |

## Las cinco garantías, del lado de Sirius

El propietario ya juzgó a Memanto. Del lado de Sirius, comprobado: aislamiento de
ámbito (`G4`, `Ambito`), polaridad (consumida, ver tabla), validez temporal
(`G8`), declaración de ausencia sin filtrar (`Suficiencia` → estado externo
único), y no pérdida silenciosa (estados, eventos, marcador de borrado, y la
traza publica «no vigente: por qué»). Las cinco están en el árbol. **Con una
condición que reaparece en todo lo de abajo**: los ejes temporales y de
polaridad los declara **el banco**, no el almacén real. En producción,
`SIN_EJES` y las puertas degradan al estado colapsado.

## Pieza por pieza

### A. Política de retención declarativa (tabla por tipo + reglas con nombre + ejecución en seco) — **NUEVA, y choca con un principio**

- En Sirius **no hay retención de ninguna clase**: ni tabla, ni reglas, ni tarea
  que expire. Barrido de `retenci|caducid|expir|ttl` en `src/sirius`: solo
  aciertos ajenos (captura, base de datos).
- Y no es un olvido: **nada automático toca una memoria**. `archive_memory.py`
  lo dice literal: «the absence of any automatic call site is what keeps a
  conversation from ever archiving a memory on its own» (PA-015; mismo patrón
  que PA-010/PA-011). Un proceso nocturno que expire por tabla **viola eso**.
- Lo que sí hay para apoyarla: `category` (vocabulario abierto, D7),
  `criticality` (`CRITICO / IMPORTANTE / None`), y `settings.json` como sitio
  declarativo. Lo que **no** hay: `valid_to` persistido en memorias reales, y
  los 13 tipos de Memanto no son el vocabulario de Sirius.
- **Consecuencia**: en Sirius, la «ejecución en seco» de Memanto no es la
  vista previa: **es la función entera**. Una política de retención solo cabe
  como *propuesta* —«estas 12 memorias de contexto llevan más de 7 días,
  ¿archivo?»— que el usuario confirma o rechaza. Eso tiene exactamente la forma
  de `MemorySuggestion` (`PENDING → CONFIRMED / REJECTED`), cuya construcción
  son los encargos M4–M6, **autorizados y pendientes**.

### B. Ciclo de vida activo/expirado con fecha, motivo, nombre de regla y restauración por elemento — **A MEDIAS, y en una parte MEJOR**

Lo que hay:
- Estados: sí, y más finos que activo/expirado (archivado, sustituido, finalizado,
  eliminado).
- Fecha: sí, por el evento `memory.archived` (`created_at`) y `updated_at`.
- Que lo no vigente **siga apareciendo, marcado con la causa**: sí, y mejor:
  `estado_publicado` escribe «no vigente: archivado / sustituido / finalizado», y
  los modos M3/M4/M5 lo ven mientras M1 no (`admite_no_vigentes`,
  `contracts.py:221`). Es la garantía 5, con control por modo.

Lo que falta:
- **Motivo**: el evento no tiene campo de texto. Se sabe *que* se archivó y *qué
  mensaje* lo ordenó; no *por qué*.
- **Nombre de regla**: no hay reglas (ver A), así que no aplica hoy.
- **Restauración por elemento**: **no existe** `desarchivar`. Hoy una memoria
  archivada no vuelve; se re-guarda como otra. Eliminar es irreversible a
  propósito (DR-012), y eso no hay que tocarlo.
- Y la condición de siempre: en memorias reales `SIN_EJES` → la marca degrada a
  «no vigente» a secas; la causa solo se ve en el banco.

### C. Consultas bi-temporales como dos parámetros («a fecha de», «cambiado desde») — **CUBIERTA en la mitad que importa; a medias en el almacén**

- **«A fecha de»: cubierta, y con los dos ejes bi-temporales**, no uno.
  `VentanaTemporal` lleva `tiempo_objetivo` (vigencia) y `corte_de_registro`
  (registro: «qué sabía yo el…»), más `tiempo_objetivo_desde` para intervalos
  (ADR-168). Los tres salen de la pregunta (`query_intent.py:38-45`) y `G8` los
  aplica. Es justo lo que Memanto hace «en lugar de exigir un grafo bi-temporal
  completo»: Sirius ya lo hizo así.
- **«Cambiado desde»: no es parámetro.** Pero el dato existe: cada
  `MemoryRevision` tiene `created_at` y cada memoria `updated_at`. Es un listado
  («qué cambió desde el lunes»), no un eje de ranking.
- **La mitad a medias es el almacén**: las memorias reales no persisten
  `valid_from/valid_to` (columnas comprobadas). Con `SIN_EJES`, `G8` degrada al
  corte de registro. Así que **la consulta es bi-temporal y el almacén es
  mono-temporal**. La deuda 27 de la bitácora es la cara espejo del mismo hecho
  en el banco (`created_at == valid_from` ítem a ítem). Es una decisión del
  propietario, no un hueco de código.

### D. Exportación Markdown legible, diffable, versionable, como formato de trabajo — **A MEDIAS: existe abierta, pero en JSON**

- La exportación abierta S12.1 está completa (B9a/B9b, `V8_EXECUTION.md:163`):
  seis ficheros JSON/JSONL, solo lectura, atómica, nunca sobrescribe, sin
  secretos (probado). JSONL **ya es** diffable línea a línea y versionable; lo
  que no es, es legible como notas.
- El patrón «Markdown generado del árbol y con guardián que falla si está
  desactualizado» **ya existe y funciona**: `MEMORIA.md` (ADR-171). Pero es la
  vista de las lecciones de los ADR, no de la memoria del usuario.
- **Lo nuevo es solo el render**: una salida Markdown de `memories.jsonl` y
  `decisions.jsonl`. **Lo peligroso es la vuelta**: «formato de trabajo» en
  Memanto sugiere editar el Markdown y reimportar. Eso es un camino de escritura
  que salta los casos de uso explícitos (origen obligatorio, evento, precedencia:
  PA-010). No se copia.
- La investigación del 11-09 recomendó Basic Memory Cloud como opción Markdown,
  pero para **memoria compartida entre IAs**, no para el almacén de Sirius:
  función distinta, no sustituye a esto.

## El veredicto de conflicto: la forma sin el método

Sirius ya tiene una forma de veredicto, determinista y con los ítems nombrados:
`SubjectPrecedenceResult(outcome, prevailing_decision, conflicting_memories,
conflicting_decisions)`. Las acciones de resolución son **M3, autorizado y
pendiente** (`ARQUITECTURA_0.2:1195`): «sustituir» ya existe
(`SupersedeDecisionUseCase`), «mantener» es archivar la otra o no hacer nada, y
«anotar» no existe (lo más cercano: corregir con origen, o una sugerencia).

Lo que Memanto añade y Sirius **no tiene ni quiere**: el **tipo** de conflicto
(contradicción / refinamiento / duplicado). Eso exige leer contenido, y
`precedence.py:11` se niega a propósito: es exactamente el juicio por LLM que el
propietario descarta. **Veredicto: no copiar; M3 ya cubre lo compatible.**

## ¿Hay algo pendiente que cumpla la misma función y sea mejor?

| pieza | pendiente que la cubre | veredicto |
|---|---|---|
| A retención | **M4–M6 (sugerencias confirmadas)**: la única forma legal de A en Sirius es una sugerencia | **Esperar a M4–M6 y montar A encima**, no antes ni aparte |
| B motivo + desarchivar | Nada. M3 son acciones de resolución, no restauración | Pieza propia, pequeña |
| C «cambiado desde» | Nada | Pieza propia, trivial |
| C fechas de vigencia en el almacén | **Deuda 27** (misma pregunta, lado banco) | Decisión del propietario, no encargo |
| D Markdown de solo lectura | Nada (MEMORIA.md es otro sujeto) | Pieza propia, trivial |
| tipo de conflicto | M3 cubre la forma; el tipo no se quiere | No |

## Encaje mínimo de lo nuevo

Todo lo de abajo está **fuera de los cinco bloques autorizados** de 0.2
(`STATUS.md`, «No autorizado todavía»), salvo lo que se cuelgue de M3 o M4–M6.
Cualquiera de estas piezas necesita una decisión registrada del propietario
antes de un encargo: **esta nota no amplía el permiso.**

1. **B: motivo al archivar + desarchivar.**
   - *Bloque*: reglas de memoria (Producto 0.1 S7, RF-024); cabe como enmienda
     pequeña, no como bloque nuevo.
   - *Contrato*: `ArchiveMemoryUseCase.archive(..., motivo: str | None)` y el
     motivo persistido en el evento (columna nueva en `EventModel`, migración);
     `UnarchiveMemoryUseCase` espejo de archivar (`ARCHIVED → CURRENT`, evento
     `memory.unarchived`, orden explícita, sin tocar revisiones);
     `MemoryRepository.unarchive_memory`.
   - *Riesgo*: bajo. El único real: desarchivar una memoria cuyo asunto ya tiene
     decisión aprobada. La precedencia lo re-evalúa sola porque lee `status`;
     hay que probarlo, no diseñarlo.

2. **D: Markdown de solo lectura.**
   - *Bloque*: S12.1 exportación abierta (D-07, cerrado); extensión.
   - *Contrato*: segundo formato en `ExportService` (parámetro `formato` o
     método nuevo), mismo contenido que los seis ficheros, mismo directorio
     atómico. **Sin importación.**
   - *Riesgo*: bajo si es solo lectura; **RNF-013** (ningún secreto) aplica
     igual y se prueba igual que hoy. Alto si se hace bidireccional: no.

3. **C: `cambiado desde`.**
   - *Bloque*: proyectos históricos consultables (§6) es el que más se le
     parece; o consulta de solo lectura sin bloque.
   - *Contrato*: `MemoryRepository.list_changed_since(instante)` sobre
     `MemoryRevision.created_at`; caso de uso de solo lectura. **No** toca
     `Peticion` ni `G8`.
   - *Riesgo*: ninguno funcional. La deuda 20 (instantes como texto) avisa del
     formato: ISO-8601 estricto o nada.

4. **C: vigencia declarada en memorias reales** (`valid_from/valid_to`).
   - *Bloque*: mejor recuperación; es lo que convierte `G8` en útil fuera del
     banco.
   - *Contrato*: dos columnas en `MemoryModel`/`DecisionModel`, escritura
     manual como `criticality` (sin clasificador automático), y que el puerto
     real deje de entregar `SIN_EJES`.
   - *Riesgo*: **medio y real**: una `valid_to` pasada saca el ítem del
     contexto ordinario (`G8`, `gates.py:240`). Es la semántica buscada, pero
     una fecha mal puesta es pérdida silenciosa **salvo** que la traza lo
     publique —y lo publica («no vigente: finalizado»)—. Condición: decidir
     primero la deuda 27.

5. **A: retención como sugerencia**, después de M4–M6.
   - *Bloque*: sugerencias confirmadas (§4), como fuente nueva de sugerencias.
   - *Contrato*: función pura `evaluar_retencion(memorias, politica) →
     propuestas` (política en `settings.json`, JSON como todo lo demás, con
     nombre de regla), y cada propuesta entra por `ProposeMemorySuggestion`;
     confirmar = `ArchiveMemoryUseCase` con motivo = nombre de la regla. La
     «ejecución en seco» es la lista de propuestas.
   - *Riesgo*: **alto si se aplica sola** (rompe PA-015); **bajo si solo
     propone**. Y sin fechas de vigencia (punto 4) las reglas solo pueden ser
     por antigüedad de registro o por categoría, que es más tosco de lo que
     Memanto vende.

## Orden recomendado, por valor partido por riesgo

1. **B** (motivo + desarchivar): cierra un hueco real, pequeño, sin chocar con
   nada.
2. **D** (Markdown solo lectura): trivial, y el propietario lee Markdown.
3. **C** (`cambiado desde`): trivial.
4. **Decisión sobre vigencia en el almacén** (C-4 + deuda 27): antes de
   cualquier retención seria.
5. **A** solo cuando existan M4–M6 y la decisión 4.

## Lo que esta nota NO hace

No lee Memanto. No escribe código ni ADR. No cambia `STATUS.md` ni el permiso:
los cinco bloques de 0.2 siguen siendo los cinco. Y no da por hecho que las
piezas «triviales» lo sean hasta que un encargo las mida: «trivial» aquí
significa *pequeñas y sin decisión de diseño*, no *gratis*.
