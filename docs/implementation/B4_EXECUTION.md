# B4 — Plan de ejecución operativo

## Estado y autoridad

El usuario autorizó explícitamente el 18 de julio de 2026 dividir B4 para reducir riesgo, tamaño de diff y tiempo de revisión.

Esta división es exclusivamente operativa. No cambia la Definición de Producto, la Arquitectura Técnica, las ATD ni los requisitos aprobados. B4 continúa cerrando D-03 y cubriendo RF-019 a RF-026 y PA-010 a PA-016.

Estado inicial: **AUTORIZADO Y NO INICIADO**.

## Objetivo de B4

Completar la capacidad observable de eventos, recuerdos y decisiones para que Sirius pueda:

- guardar memoria solo por orden o confirmación explícita;
- conservar y abrir un origen consultable;
- distinguir exploración, propuesta y decisión aprobada;
- corregir y sustituir sin destruir el historial;
- archivar y eliminar según la política aprobada;
- detectar incompatibilidades y no resolverlas silenciosamente.

## Base ya implementada

B4 no parte de cero. V4 ya incluye:

- recuerdo genérico versionado;
- origen obligatorio como valor no vacío;
- corrección mediante revisión nueva;
- archivo;
- redacción del contenido estructurado al eliminar.

Los subbloques siguientes deben reutilizar y completar esa infraestructura. No deben crear un segundo sistema de memoria paralelo.

## Reglas comunes

- Una rama y una pull request por subbloque.
- Ejecución secuencial al principio; no trabajar dos subbloques de B4 en paralelo.
- Cada cambio debe enlazar requisitos, pruebas y archivos afectados.
- No ampliar el modelo conceptual aprobado: evento, mensaje, recuerdo, decisión y proyecto.
- No introducir guardado proactivo, embeddings, RAG, grafos ni multiagente.
- No modificar documentos canónicos.
- No declarar superadas pruebas manuales o con proveedor real.
- `scripts/check.ps1` y CI deben quedar verdes antes del merge.
- Máximo dos ciclos de revisión y corrección por PR. Si no converge, devolver `BLOCKED_BY_DECISION`.
- El usuario conserva la autorización de merge.

## B4a — Origen consultable y guardado manual

### Alcance

- Representación persistente del evento de origen aprobado por la arquitectura.
- Enlace real entre recuerdo y evento o mensaje de procedencia.
- Caso de uso explícito para guardar un recuerdo manual.
- Consulta del origen sin acceso directo de la interfaz a SQLite.
- Fecha, estado y versión observables.

### Trazabilidad

- RF-019 — Guardar recuerdo.
- RF-021 — Consultar origen.
- PA-010 — Guardar memoria manual.

### Resultado verificable

Al ordenar guardar una preferencia o un hecho, se crea un recuerdo con origen, fecha, estado y versión, y el origen puede consultarse posteriormente.

### Fuera de alcance

- decisiones;
- sustitución;
- conflictos;
- archivo o eliminación desde interfaz;
- búsqueda FTS5 general;
- panel de contexto completo de B5.

## B4b — Decisiones y aprobación explícita

### Alcance

- Tipo o entidad de decisión sobre la infraestructura de conocimiento existente.
- Asunto, proyecto, estado, versión, fecha y origen.
- Estados mínimos necesarios para propuesta y aprobación.
- Caso de uso que exige confirmación explícita para aprobar.
- Una exploración conversacional no crea una decisión aprobada.

### Trazabilidad

- RF-020 — Guardar decisión.
- PA-011 — No convertir exploración en decisión aprobada.

### Resultado verificable

Debatir alternativas no genera una decisión aprobada. Una aprobación explícita sí crea o activa la decisión correspondiente con su origen y versión.

### Fuera de alcance

- sustitución de otra decisión;
- precedencia frente a recuerdos;
- resolución de conflictos;
- panel de contexto de B5.

## B4c — Corrección y sustitución

### Alcance

- Consolidar la corrección existente bajo los contratos vigentes.
- Nueva revisión inmutable y puntero autoritativo a la vigente.
- Relación explícita de sustitución entre decisiones.
- Exclusión de revisiones sustituidas del contexto normal.
- Consulta histórica sin tratar versiones anteriores como vigentes.

### Trazabilidad

- RF-022 — Corregir.
- RF-023 — Sustituir.
- PA-012 — Corregir y versionar.
- PA-013 — Sustituir decisión.

### Resultado verificable

Una corrección mantiene la versión anterior como histórica y activa la nueva. Una decisión sustituta queda enlazada con la sustituida y solo la nueva entra en el contexto ordinario.

## B4d — Archivo, eliminación y redacción de origen

### Alcance

- Archivo consultable fuera del contexto ordinario.
- Eliminación con confirmación explícita.
- Borrado del contenido estructurado y de sus índices.
- Conservación del marcador mínimo sin contenido.
- Elección explícita de redactar o conservar el mensaje fuente.
- Advertencia de que una copia antigua puede reintroducir datos eliminados.

### Trazabilidad

- RF-024 — Archivar.
- RF-025 — Eliminar.
- PA-015 — Archivar.
- PA-016 — Eliminar.
- SP-06 — Borrado y copia antigua.

### Resultado verificable

Un elemento archivado sigue siendo consultable y deja de usarse normalmente. Un elemento eliminado pierde su contenido conforme a la opción elegida y solo conserva el marcador mínimo autorizado.

## B4e — Precedencia y conflictos

### Alcance

- Detección determinista de recuerdos vigentes incompatibles del mismo asunto.
- Prioridad de una decisión aprobada vigente sobre recuerdos generales incompatibles del mismo asunto.
- Solicitud de aclaración cuando no exista precedencia inequívoca.
- Prohibición de elegir silenciosamente.
- Pruebas de dominio y aplicación independientes del proveedor real.

### Trazabilidad

- RF-026 — Detectar conflicto.
- PA-014 — Conflicto.
- DR-011 — Precedencia y conflictos de memoria.

### Resultado verificable

Ante dos recuerdos incompatibles sin precedencia, Sirius devuelve un conflicto explícito y solicita aclaración. Cuando existe una decisión aprobada vigente del mismo asunto, esa decisión prevalece de forma trazable.

## B4f — Integración observable y cierre de B4

### Alcance

- Integrar las operaciones aprobadas en las superficies existentes sin crear una aplicación de gestión independiente.
- Completar casos de uso, composición, interfaz mínima y pruebas GUI necesarias.
- Añadir indexación o búsqueda local únicamente en la medida necesaria para PA-010 a PA-016 y para el posterior B6.
- Actualizar la documentación operativa y la matriz de evidencia.

### Trazabilidad

- PA-010 a PA-016 completas.
- Parte correspondiente de PA-008 y PA-E2E-01 preparada, sin declararla formalmente superada mientras dependa de proveedor real o evaluación humana.

## Puerta de entrada de cada subbloque

Antes de comenzar:

1. El subbloque anterior está fusionado y CI está verde.
2. La tarea identifica requisitos y pruebas exactas.
3. Se ha inspeccionado el código existente para evitar duplicación.
4. El diff previsto está acotado y no requiere una decisión nueva.
5. La rama parte del `main` vigente.

## Criterio de cierre de cada subbloque

Un subbloque queda `READY_FOR_HUMAN_REVIEW` cuando:

- cumple exclusivamente su alcance;
- añade o actualiza las pruebas previstas;
- `scripts/check.ps1` pasa;
- CI está verde;
- no quedan hallazgos `BLOCKER` o `HIGH`;
- la documentación operativa coincide con el comportamiento;
- la PR explica límites y pendientes;
- no se han declarado superadas pruebas manuales no ejecutadas.

## Estados finales permitidos

- `READY_FOR_HUMAN_REVIEW`
- `BLOCKED_BY_DECISION`
- `FAILED_SAFELY`
- `USAGE_LIMIT_REACHED`

## Criterio de cierre de B4 completo

B4 solo podrá marcarse terminado cuando:

- B4a a B4f estén fusionados;
- RF-019 a RF-026 tengan trazabilidad verificable;
- PA-010 a PA-016 existan y pasen en la parte automatizable;
- no queden defectos bloqueantes o altos de D-03;
- las revisiones históricas, archivadas, sustituidas o eliminadas no entren indebidamente en el contexto vigente;
- la documentación operativa y el registro de evidencia estén actualizados;
- el usuario haya autorizado todos los merges.

## Primera tarea funcional

La primera tarea funcional de esta secuencia fue **B4a — origen consultable y guardado manual**.

La prueba de humo cloud definida en `docs/implementation/CLOUD_SMOKE_TEST.md` terminó en `CLOUD_SMOKE_PASSED` el 18 de julio de 2026 (evidencia en `docs/implementation/CLOUD_SMOKE_EVIDENCE_20260718.md`, PR #34 fusionada). La puerta de entrada de B4a quedó satisfecha y B4a se implementó el 18 de julio de 2026 (rama `claude/intelligent-bohr-1s38y6`, PR #36). La revisión de Fase C encontró un `BLOCKER` transaccional (evento y recuerdo en dos transacciones independientes), corregido en la misma rama y PR mediante `UnitOfWork` (ver `AUTOMATION_OPERATING_CONTRACT.md` §2). **B4a quedó fusionado en `main`** el 18 de julio de 2026 (commit `c025683c960a19a1a9c1aa40fa861547026118cc`), con el workflow `Quality` en verde sobre ese commit.

**B4b — decisiones y aprobación explícita** se implementó el 18 de julio de 2026 sobre el `main` ya fusionado de B4a, siguiendo el mismo patrón que B4a: entidad de decisión (`sirius.domain.decision`), tabla `decisions`/`decision_revisions` (migración Alembic no destructiva), `DecisionRepository`/`SqliteDecisionRepository`, extensión mínima de `UnitOfWork` con `decision_repository`, `ProposeDecisionUseCase` (propuesta) y `ApproveDecisionUseCase` (aprobación con confirmación explícita obligatoria), y `GetDecisionOriginUseCase` (consulta de asunto, proyecto, estado, versión, fecha y origen). Una PR borrador quedó abierta hacia `main`, pendiente de revisión y sin merge. El usuario decidió expresamente, el 18 de julio de 2026, activar desde esta PR la revisión automática solicitada mediante una incidencia GitHub etiquetada `agent-review-requested` — ver `AUTOMATION_OPERATING_CONTRACT.md` §2 y §10 para el registro completo de esa decisión y sus límites.

**Estado real verificado antes de iniciar B4c:** la PR #37 (B4b) quedó **fusionada en `main`** el 18 de julio de 2026 (commit de merge `d1bbb872751a96ca11ec38c20fd8b3fb5322651c`), con el workflow `Quality` en verde (669 pruebas). Verificado directamente sobre `origin/main` (no solo por resumen previo) antes de tocar código de B4c.

**B4c — Corrección y sustitución** se implementó el 18 de julio de 2026 sobre el `main` ya fusionado de B4b, reutilizando la infraestructura existente sin crear un segundo sistema de memoria, decisiones o eventos:

- *Corrección de recuerdos (RF-022, PA-012):* `CorrectMemoryUseCase` (`sirius.application.correct_memory`) consolida la corrección ya existente desde V4 (`MemoryRepository.correct_memory`, que ya creaba una revisión nueva inmutable, movía el puntero `current_revision` y conservaba la revisión anterior) bajo el mismo contrato transaccional que B4a estableció para la creación: valida contenido y estado corregible antes de escribir nada, crea un evento de origen (`memory.corrected`) y la nueva revisión dentro de la misma `UnitOfWork`, y solo confirma si ambos escriben con éxito. Un identificador inexistente o un estado no corregible (archivado/eliminado) falla de forma segura sin escribir nada; un fallo tras crear el evento revierte también el evento.
- *Sustitución de decisiones (RF-023, PA-013):* nuevo estado `DecisionStatus.SUPERSEDED` y campo `Decision.supersedes_decision_id` (el equivalente, a la granularidad de decisión que B4b ya eligió, del `knowledge_revision.supersedes_revision_id` de la Arquitectura Técnica aprobada S7.3 — B4b nunca da a una decisión más de una revisión, así que el enlace de sustitución vive entre dos decisiones, no entre dos revisiones). `SupersedeDecisionUseCase` (`sirius.application.supersede_decision`) exige confirmación explícita (aprueba la sustituta como parte de la misma operación), valida ambas decisiones existentes, que la sustituida esté APPROVED, que la sustituta esté PROPOSED, que no sea autosustitución y que compartan asunto y proyecto, y ejecuta evento + aprobación de la sustituta + estado histórico de la sustituida + enlace de sustitución en una sola `UnitOfWork`. `DecisionRepository.supersede_decision`/`list_current_decisions` (consulta ordinaria de decisiones vigentes, excluye propuestas y sustituidas)/`get_superseding_decision` (consulta inversa del enlace).
- *Persistencia:* migración Alembic aditiva y no destructiva `05559a954593` (`decisions.supersedes_decision_id`, columna nula con clave foránea autorreferencial); ningún dato existente se pierde ni se reescribe.
- *Pruebas:* Ruff, mypy y pytest en verde (735 pruebas: 669 previas + 66 nuevas), incluidas atomicidad/rollback de ambas operaciones, migración real (`upgrade`/`downgrade`), regresión de B4a/B4b, y la garantía de que una conversación ordinaria nunca corrige ni sustituye por sí sola.

Una PR borrador quedó abierta hacia `main`, pendiente de revisión y sin merge. El usuario autorizó expresamente, el 18 de julio de 2026, activar desde esta PR la misma revisión automática ya usada para B4b (incidencia GitHub etiquetada `agent-review-requested`) — ver `AUTOMATION_OPERATING_CONTRACT.md` §2 y §10 (cambio B4b→B4c) para el registro completo de esa decisión y sus límites. B4d, B4e y B4f siguen sin iniciarse.