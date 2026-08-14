# Base de conocimiento de Claude sobre el Proyecto Sirius

**Naturaleza:** mapa operativo derivado, para sesiones futuras de Claude. **No es una fuente canónica** y nunca prevalece sobre `docs/canonical/`, `docs/canonical/STATUS.md`, `docs/implementation/PLAN.md`, `REPOSITORY_STATUS.md` ni `AGENTS.md`. Ante cualquier duda o contradicción, releer las fuentes y corregir este documento.

**Fecha de auditoría:** 20 de julio de 2026.
**Commit de `main` auditado:** `07ac239a69a4fb6e860c38c9e5eae1e694250137` (B4f fusionado).
**Auditoría asociada:** `docs/audits/AUDITORIA_INTEGRAL_INCORPORACION_CLAUDE_2026-07.md`.

## 1. Identidad y propósito de Sirius

Sirius es un **compañero personal de creación e ingeniería**: una segunda mente con identidad estable, memoria propia y portable, criterio, continuidad y autoridad final del usuario. Existe para ayudar a pensar, debatir, recordar, organizar, decidir y construir con continuidad — no para responder preguntas sueltas. No es un chatbot genérico, ni una AGI, ni un gestor de proyectos, ni un sistema autónomo con derecho a actuar sin permiso. *(Fuente: Manual de Visión e Identidad v1.2, `docs/canonical/SIRIUS_MANUAL_VISION_IDENTIDAD_v1.2_PROPUESTO.docx`, §2–3 — aprobado según `docs/canonical/STATUS.md`.)*

## 2. Visión a largo plazo

Ecosistema personal de creación que une conversación, memoria, proyectos, herramientas, laboratorio físico y contenido creativo, con Sirius como presencia que lo conecta. Roadmap orientativo: 0.1 corazón persistente → 0.2 memoria útil → 0.3 primeras habilidades → 0.4 voz → 0.5 laboratorio → 1.0 "compañero en la habitación". El roadmap expresa aprendizaje esperado, no fechas. *(Manual §8, §14.)* La línea física **HEAD-R1** (cabeza robótica) tiene Documento Rector v1.0 aprobado pero está **físicamente inactiva y sin compras autorizadas**; es una línea separada que NO forma parte de Sirius 0.1 (`docs/robotics/head/README.md`, `STATUS.md`).

## 3. Alcance exacto de Sirius 0.1

Aplicación de escritorio **Windows 11, local, monousuario, en español, centrada en texto**: una conversación principal persistente; identidad reconocible y versionada; un único proyecto activo mínimo; memoria manual trazable y decisiones versionadas; proveedor real detrás de contrato sustituible (simulado en pruebas); persistencia local; exportación estructurada; copia cifrada y restauración; presupuesto; errores comprensibles; sin acciones externas. Requisitos: RF-001–RF-035 y RNF-001–RNF-024. *(Definición de Producto 0.1 v0.2, §3, §10–11 — aprobada.)*

## 4. Fuera de alcance de 0.1 (no introducir sin decisión registrada)

Voz/cámara/sensores/robótica; web e investigación autónoma; ejecución de código/comandos/automatizaciones externas; adjuntos y acceso general a archivos; múltiples conversaciones o proyectos activos; selector de proveedores; guardado proactivo/extracción automática de recuerdos; RAG/embeddings/vectorial/grafos/multiagente; nube/cuentas/móvil; interfaz galáctica avanzada/avatar/presencia física. *(Producto §4.)*

## 5. Principios de producto

Validar primero la experiencia de compañero persistente; una función entra si resuelve un problema observado o una condición de confianza; memoria/personalidad/continuidad priman sobre cantidad de funciones; privacidad, reversibilidad y trazabilidad son parte del producto; no colar capacidades futuras como "preparación". *(Manual §10.)*

## 6. Identidad y personalidad

Cercano, espontáneo, extrovertido, provocador, ingenioso, resolutivo, honesto, crítico, adaptable, coherente entre proveedores. Recomendación principal por defecto; derecho a discrepar con argumentos; humor contextual nunca obligatorio ni en situaciones serias; separar hechos/inferencias/propuestas; reconocer incertidumbre; español natural y directo. La identidad se carga desde un **perfil versionado** (`sirius.domain.identity`), y cada cambio de proveedor/modelo/perfil exige la suite de escenarios. PS-01–PS-07 requieren evaluación humana: **no declarar la personalidad aprobada sin el usuario**. *(Manual §5–6; Producto §8.)*

## 7. Autoridad y rol del usuario

El usuario conserva la autoridad sobre objetivos, decisiones importantes, acciones sensibles y **todo merge**. Sirius (y los agentes del proyecto) analizan, filtran y recomiendan; pueden discrepar; respetan la decisión final; no convierten exploración en decisión aprobada; no reabren decisiones aprobadas sin contradicción, evidencia nueva o riesgo concreto. *(Manual §4, §13.)*

## 8. Arquitectura aprobada

Monolito modular local de un solo proceso: **presentación (PySide6) → aplicación (casos de uso/puertos) → dominio (puro) → infraestructura/adaptadores** (SQLite+SQLAlchemy+Alembic, OpenAI Responses, keyring, backups, logs), con dependencias hacia dentro y `composition_root` como único ensamblador. La UI no toca SQLite/OpenAI/secretos; el dominio no importa PySide6/SQLAlchemy/OpenAI. SQLite es la fuente canónica local; `PRAGMA foreign_keys=ON` por conexión (`src/sirius/adapters/persistence/database.py`); operaciones lentas en `QThreadPool`; pruebas normales con proveedor simulado y sin red. ATD-001–ATD-012 aprobadas. Verificado por imports en la auditoría integral: sin violaciones de capas. *(Arquitectura Técnica 0.1 v1.0 aprobada; verificación: auditoría 2026-07.)*

## 9. Estado real de implementación (a 2026-07-20, commit auditado)

- **V0–V6B**: infraestructura implementada. V6 (OpenAI real): implementación y pruebas simuladas completas; **pendiente prueba manual real** con clave.
- **V7A/V7**: seguridad, copia cifrada (Argon2id+Fernet, `VACUUM INTO`, manifiesto, límite 100 MB), validación y **restauración con rollback verificada**, integradas en la interfaz. Pendiente solo la validación manual de Windows Credential Manager con valor señuelo.
- **V8.1 (ACTIVA)**: fusionados B2a/B2b (onboarding de clave con política de datos; ruta de datos con `BootstrapLocationStore`), B3a/B3b/B3c (proyecto: creación, continuidad estado/bloqueos/siguiente paso, ciclo de vida con `project_revisions`), **B4a–B4f completos** (eventos de origen, decisiones con aprobación explícita, corrección/sustitución, archivo/eliminación con `SourceMessageChoice` y advertencia de copias antiguas, precedencia/conflictos `sirius.domain.precedence`, y `KnowledgeWidget` — pestaña "Memoria y decisiones").
- **V8.2/V8.3/V8.4: BLOQUEADAS** por puertas explícitas (`docs/implementation/PLAN.md`, `V8_EXECUTION.md`).
- **Pendiente dentro de V8**: exportación (RF-031), B5 (panel de contexto completo), B6 (indexación/búsqueda, D-11), defectos D-01–D-11/A-01–A-04 restantes, empaquetado Nuitka, y todas las validaciones manuales/reales.
- **Suite** en el commit auditado: ~930–940 pruebas verdes en Linux (el número exacto varía por PRs de automatización pendientes); Quality corre en `windows-latest`.

## 10. Verticales completadas, parciales y pendientes

Completadas (implementación): V0, V1, V2, V5. Implementadas con validación real pendiente: V6, V7A, V7. Parciales: V3 (proyecto: B3 cerrado; PA-008/PA-009 pendientes), V4 (memoria: B4 cerrado; B6 pendiente). Activa: **V8.1**. No iniciadas: B5, B6, V8.2–V8.4. Sirius 0.1: **NO ACEPTADO y NO TERMINADO**.

## 11. Requisitos y pruebas clave

RF-001–RF-035 (Producto §10). Cobertura automática demostrada para RF-001–RF-026 (proveedor simulado); RF-031 (exportación) **sin implementar**; RF-027–RF-030/RF-032–RF-035 implementados con pruebas. PA-001–PA-016: parte automatizable cubierta; PA-001/PA-002 (credencial real), PA-008 parcial, PA-009, PA-E2E-01 y PS-01–PS-07 **pendientes de proveedor real/Windows real/evaluación humana**. La matriz de evidencia vive en `docs/implementation/V8_EXECUTION.md` y `B4_EXECUTION.md`.

## 12. Decisiones técnicas principales

ATD-001–ATD-012 (aprobadas; canónico). Operativas relevantes: `store=False` hacia OpenAI (`adapters/llm/openai_responses.py:132`); presupuesto como decorador del proveedor (`adapters/llm/budget.py`) con uso persistido (`llm_usage`); revisiones inmutables con puntero autoritativo (memoria, decisiones, proyecto); cadena Alembic lineal (13 migraciones, head `94418c79da9d`); eliminación de decisiones deliberadamente fuera de 0.1 (documentado en `sirius.domain.decision`). Los ADR nuevos van en `docs/decisions/` (`ADR-NNN-*`), aún vacío.

## 13. Reglas sobre recuerdos y decisiones (invariantes)

Conversar nunca crea/aprueba/corrige/archiva/elimina memoria ni decisiones (`SendMessageUseCase` no llama a esos casos de uso — probado). Todo recuerdo/decisión tiene origen (evento). Corrección = revisión nueva + anterior histórica. Solo una decisión APPROVED vigente por asunto; prevalece sobre recuerdos incompatibles del mismo asunto/proyecto; sin precedencia inequívoca → conflicto explícito, nunca elección silenciosa. Archivados/sustituidos/eliminados fuera del contexto ordinario. Eliminar redacta contenido en toda la historia de revisiones y conserva marcador mínimo sin texto; el mensaje fuente solo se redacta por elección explícita tipada (`SourceMessageChoice`, sin valor por defecto); la interfaz advierte de que las copias antiguas pueden reintroducir datos. *(Producto §6–7; implementación B4a–B4f.)*

## 14. Seguridad, privacidad y secretos

Clave API solo en Windows Credential Manager vía `keyring` (`adapters/secrets/`); nunca en código, Git, logs, exportaciones ni copias (pruebas reales en `tests/integration/test_secret_leakage.py`). Sin telemetría. `store=false` y retención transparente (RNF-009/010). Modelo de amenazas: sesión de Windows confiable; malware/administrador fuera de alcance de 0.1. Nunca usar clave real en pruebas normales (prohibido hasta abrir V8.3 con autorización expresa).

## 15. Persistencia, copias y recuperación

SQLite + SQLAlchemy + Alembic; `session_scope` con rollback íntegro; FKs activadas; migraciones aditivas probadas con upgrade/downgrade reales. Copia: `.siriusbackup` cifrado y autovalidado; restauración: valida → copia de seguridad previa → reemplazo atómico → verificación posterior en solo lectura → rollback automático ante cualquier fallo; gestión de sidecars WAL/SHM; cierre de conexiones antes de restaurar (`close_database_connections()`); reinicio controlado tras restaurar. Sin WAL/busy_timeout configurados (mejora anotada).

## 16. Flujo de desarrollo

Ramas breves desde `main` actualizado → PR → Quality verde (Ruff format/lint, mypy estricto, pytest, en Windows) → **merge solo humano** (squash). Validación local: `scripts/check.ps1` (Windows) o los cuatro `uv run` equivalentes (otros entornos). `main` siempre integrable. No convertir exploración en requisitos. Detenerse ante decisiones de producto/arquitectura, contradicciones u operaciones peligrosas.

## 17. Contrato de automatización

`docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` v1.1 (vigente tras el merge de la PR #44, aunque su cabecera aún diga "PROPUESTO" — hallazgo documental abierto). Autoriza para todo Sirius 0.1: incidencia de trabajo estructurada como fuente de verdad → implementación en rama propia → CI → revisión independiente → máximo **2 ciclos** de corrección → notificación → cierre tras merge humano. Prohibidos: merge automático, push a `main`, falsear pruebas, vigilancia horaria como motor (con la excepción acotada del §9.1 v1.6: una red de seguridad periódica que no dirige el flujo), iniciar bloques sin orden. Estados: etiquetas `sirius:*` (planned, implement-requested, implementing, ci-pending, review-requested, reviewing, repair-requested, repairing, ready-for-merge, blocked-decision, failed-safely, completed). Piezas del repo: workflows `quality`, `advance-sirius-after-quality`, `complete-sirius-after-merge`, `notify-sirius-state`, `bootstrap-sirius-automation-labels`; biblioteca `scripts/automation/sirius_issue.sh` (lectura REST-first con reintentos, validación estructural de cuerpos, escritura verificada, transiciones atómicas con marcadores idempotentes) y `validate_issue_body.py`. Historial de incidentes y reparaciones: `docs/audits/`.

## 18. Claude Code, Claude Max, Cowork y Routines — sin mezclarlos

- **Claude Code**: el agente de ingeniería que trabaja dentro del repositorio (sesiones como esta): lee, implementa, prueba, hace commit/push en ramas y abre PRs. Sin merge.
- **Routines** (de Claude): ejecuciones externas registradas una sola vez que reaccionan a las etiquetas-evento (`implement-requested`/`review-requested`/`repair-requested`) según `docs/implementation/SIRIUS_GENERIC_ROUTINES_0.1.md`. No son inspeccionables desde el repo; se auditan por sus efectos. Riesgo conocido: ejecuciones duplicadas (sin single-flight garantizado).
- **Cowork**: superficie de escritorio de Claude para trabajo asistido; a efectos de este repo se rige por las mismas reglas de incorporación que Claude Code.
- **Claude Max**: plan de suscripción que da acceso/capacidad a lo anterior; **no es un componente técnico del sistema** — no atribuirle comportamientos propios.
- **ChatGPT**: panel de mando del usuario (crea incidencias, aplica etiquetas, ejecuta el merge autorizado). No es autoridad documental.

## 19. Límites de autonomía de Claude

Puede sin escalar: detalles ordinarios de implementación dentro del contrato de la tarea; correcciones documentales operativas; pruebas; ramas/commits/push/PR autorizados por la tarea. Debe **detenerse y pedir decisión**: ampliar 0.1; cambiar decisiones aprobadas/canónicos; alterar arquitectura, datos, privacidad, proveedor o presupuesto de forma material; nuevas dependencias estructurales; acciones externas autónomas; operaciones destructivas o irreversibles; merge; publicar; contradicciones irresolubles con la jerarquía documental. *(AGENTS.md; onboarding.)*

## 20. Criterios de parada

`READY_FOR_REVIEW`, `BLOCKED_BY_DECISION`, `FAILED_SAFELY`, `USAGE_LIMIT_REACHED`. Sin tope fijo de ciclos de corrección: rige la política de convergencia (`AUTOMATION_OPERATING_CONTRACT.md` §5.1). Se corrige mientras el par `(hallazgos pendientes, severidad agregada)` mejore estrictamente respecto al mejor resultado previo; en cuanto deja de mejorar —o Quality encadena fallos sin arreglo— se detiene con motivo exacto → `BLOCKED_BY_DECISION`. Nunca declarar terminado sin evidencia; nunca declarar superadas pruebas manuales/reales.

## 21. Riesgos abiertos (a fecha de auditoría)

1. **Conector externo de escritura que trunca contenidos largos y confirma sin verificar** — 5 incidentes reales (workflows, rama, cuerpos de issues #55/#60, código en PR #57). El repo detecta y contiene, no puede impedirlo. Decisión de política pendiente (D-7 de la auditoría integral).
2. Automatización degradada hasta fusionar las PRs de reparación pendientes (en la fecha auditada: #58 `ensure_label`, #59 reconciliador+transición auto-reparadora, #62 puerta de activación).
3. Routines externas duplicadas (sin single-flight).
4. Issue de B5 (#60) con cuerpo truncado: B5 no puede activarse hasta que el gestor del backlog complete su contrato.
5. Deduplicación de notificaciones `no-head` puede silenciar una segunda parada distinta en la misma incidencia.
6. Sin evidencia de Windows real, ejecutable real ni proveedor real.

## 22. Validaciones manuales pendientes

Credential Manager con valor señuelo; ejecutable Nuitka reproducible y su ejecución (escalado/teclado/foco/cierre forzado/restauración empaquetada); ventana con proveedor real (V8.3, tras sus puertas); PA-001/PA-002/PA-009; PA-E2E-01 (proyecto real multi-sesión); PS-01–PS-07 (personalidad, evaluación humana); pruebas manuales de seguridad/privacidad. *(`REPOSITORY_STATUS.md` §Pendiente de validación manual; PLAN V8.2–V8.4.)*

## 23. Siguiente trabajo correcto

En orden razonable (sin decidir por el usuario): (1) resolver las decisiones de automatización pendientes (merge de las PRs de reparación; política del conector); (2) completar el cuerpo de la incidencia de B5 y activarla por el flujo normal; (3) continuar V8.1: exportación (RF-031), B5, B6/D-11, defectos D-0x restantes; (4) preparar la puerta V8.2 (ejecutable + guiones manuales). Cualquier salto de puerta exige decisión expresa del usuario.

## 24. Jerarquía de fuentes (resumen operativo)

1. Instrucciones vigentes del proyecto (`AGENTS.md`, `CLAUDE.md`). 2. Manual de Visión e Identidad. 3. Definición de Producto 0.1. 4. Registro de Decisiones. 5. Plan de Pruebas y Trazabilidad. 6. Arquitectura Técnica + ATD. 7. `docs/canonical/STATUS.md` (estado de aprobación: los nombres con "PROPUESTO" son instantáneas históricas ya aprobadas). 8. `PLAN.md`, `REPOSITORY_STATUS.md`, Git y pruebas (estado material). 9. Auditorías y conversaciones (evidencia secundaria). Este documento está por debajo de todos ellos.

## 25. Mantenimiento de este documento

Actualizarlo al final de cualquier sesión que cambie: estado de verticales/bloques, automatización, riesgos abiertos o jerarquía documental. Procedimiento: (1) releer `docs/canonical/STATUS.md`, `PLAN.md`, `REPOSITORY_STATUS.md` y el estado vivo de PRs/Issues; (2) corregir las secciones afectadas; (3) actualizar fecha y commit auditado de la cabecera; (4) entregar el cambio por PR como documentación operativa. Si este documento contradice una fuente superior, la fuente superior prevalece y este archivo debe corregirse.
