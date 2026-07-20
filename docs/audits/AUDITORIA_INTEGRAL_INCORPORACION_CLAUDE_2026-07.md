# Auditoría integral de incorporación de Claude — Proyecto Sirius (julio 2026)

**Fecha:** 20 de julio de 2026 · **Commit de `main` auditado:** `07ac239a69a4fb6e860c38c9e5eae1e694250137` (B4f fusionado) · **Rama de trabajo:** `docs/claude-project-onboarding-20260720` (PR #61, borrador).
**Entorno:** sesión Claude Code en Linux (sin Windows real, sin PowerShell, sin `actionlint`/`shellcheck`, sin clave API). Los `.docx` canónicos se leyeron mediante `scripts/read_docx.py`.
**Convención:** [HECHO] verificado con evidencia · [INFERENCIA] deducción · [RIESGO] posibilidad · [DECISIÓN] requiere al usuario.

## 1. Resumen ejecutivo

Sirius es un proyecto **inusualmente bien gobernado**: la cadena visión → producto → arquitectura → plan → ejecución → evidencia existe de verdad, es trazable y — con las excepciones listadas en §14 — es coherente entre documentos, código y pruebas. El estado real a día de hoy: **V0–V7 implementadas** (con validaciones manuales/reales pendientes), **V8.1 activa** con B2–B4 fusionados al completo (incluido B4f hoy), **B5/B6 y exportación pendientes**, **V8.2–V8.4 bloqueadas por puertas explícitas**, y **Sirius 0.1 NO aceptado ni terminado**. El riesgo dominante no está en el producto sino en el circuito de automatización de desarrollo: un conector externo de escritura ha truncado contenidos en 5 incidentes reales en 48 h, y tres PRs de reparación de automatización esperan merge. La guía de incorporación (PR #61) es fiable tras las correcciones aplicadas en esta auditoría.

## 2. Alcance auditado y nivel de cobertura

- **Leído íntegro** [HECHO]: `README.md`, `AGENTS.md`, `CLAUDE.md`, `docs/canonical/STATUS.md`, `REPOSITORY_STATUS.md`, `docs/implementation/PLAN.md`, `B4_EXECUTION.md`, `SIRIUS_GENERIC_ROUTINES_0.1.md`, `AUTOMATION_OPERATING_CONTRACT.md`, `AUTOMATION_STATE_MACHINE_SIRIUS_0.1.md`, `AUTOMATION_FLOW_PLAN_SIRIUS_0.1.md`, `docs/operations/CLAUDE_PROJECT_ONBOARDING.md`, `docs/robotics/head/README.md` + `STATUS.md`, `docs/decisions/README.md`, `PRIVATE_PROJECT.md`, Manual de Visión e Identidad v1.2 (extraído) y Definición de Producto 0.1 v0.2 (extraída, RF/RNF completos), los 5 workflows, la plantilla de incidencias, `scripts/automation/*` y la totalidad de `tests/automation/`.
- **Leído parcial** [HECHO]: `V8_EXECUTION.md` (estado, reglas y puertas; no las 657 líneas de evidencia por bloque), `CHANGELOG.md` (cabecera), `docs/robotics/head/RECTOR.md`/`DECISIONS.md`/`AUDIT.md`/`ARTIFACTS.md` (no leídos línea a línea; su estado queda fijado por README/STATUS de la cabeza).
- **Código y pruebas**: verificación estructural completa (imports por capas, cadena Alembic, engine SQLite, secretos, presupuesto, `store=False`) sobre 94 módulos `src` y 95 archivos de test; lectura selectiva de módulos clave; **no** se releyó línea a línea todo el código de producto en esta pasada — la suite (~940 verdes) y dos auditorías previas del mismo día (`docs/audits/` en PRs #59/#62) cubren esa profundidad.
- **Estado vivo**: Issues #45–#62 relevantes, PRs #44–#62 relevantes, runs recientes de Actions.
- **Canónicos `.docx` restantes** (Cierre Prearquitectura, Estado Canónico, Registro de Decisiones, Plan de Pruebas, Arquitectura Técnica, Auditoría prearquitectura): **no extraídos en esta pasada** (§19); su estado de aprobación consta en `docs/canonical/STATUS.md` y sus contenidos operativos están reflejados en PLAN/V8_EXECUTION.

Cobertura global estimada: **alta** para gobernanza, producto, estado y automatización; **media** para el detalle línea a línea del código de producto; **baja** para los cuatro docx canónicos no extraídos.

## 3. Inventario y jerarquía de fuentes (Fase 1)

| Clase | Fuentes | Autoridad |
|---|---|---|
| Canónicas (aprobadas 11-jul-2026 por `docs/canonical/STATUS.md`) | Manual Visión/Identidad v1.2 · Producto 0.1 v0.2 · Registro de Decisiones v1.0 · Plan de Pruebas v1.0 · Estado Canónico v2.0 · Arquitectura Técnica v1.0 + ATD-001–012 · Cierre Prearquitectura v1.0 | Máxima; los nombres conservan "PROPUESTO" como instantánea histórica |
| Estado de aprobación | `docs/canonical/STATUS.md` | Fija el estado APROBADO de lo anterior |
| Estado material | `REPOSITORY_STATUS.md`, `docs/implementation/PLAN.md`, Git, pruebas, CI | Estado real de implementación |
| Ejecución operativa | `V8_EXECUTION.md`, `B4_EXECUTION.md`, `AUTOMATION_*`, `SIRIUS_GENERIC_ROUTINES_0.1.md` | Registro operativo; no normativo ante contradicción |
| Operaciones/incorporación | `docs/operations/*` (PR #61) | Mapa derivado |
| Auditorías | `docs/audits/*` | Evidencia secundaria fechada |
| HEAD-R1 | `docs/robotics/head/*` | Línea separada; rector v1.0 aprobado; ejecución NO autorizada |
| Históricas/exploratorias | Issues #13/#14/#15/#25, CHANGELOG | Sin autoridad normativa |
| Futuras decisiones | `docs/decisions/` (ADR-NNN) | Vacío aún |

Contradicciones y riesgos de obsolescencia por fuente: §14.

## 4. Comprensión resultante de Sirius (Fase 2)

Registrada de forma permanente y referenciada en `docs/operations/CLAUDE_SIRIUS_KNOWLEDGE_BASE.md` (§§1–8): identidad, visión, relación con el usuario, personalidad (10 rasgos nucleares + reglas de humor/honestidad), memoria como fundamento de continuidad (8 principios permanentes), niveles de autonomía (consultar→proponer→preparar→ejecutar reversible→ejecutar sensible; 0.1 se queda en consultar/proponer/registrar autorizado), diferencia 0.1↔visión (roadmap 0.1→1.0) y 0.1↔HEAD-R1 (líneas separadas; HEAD-R1 inactiva). Ambigüedades detectadas que podrían desviar a un agente: ninguna material en los canónicos; las dos operativas (B5 sin sección de plan; contrato de automatización con cabecera "PROPUESTO") están en §14.

## 5. Estado real del producto e implementación (Fase 3)

Ver tabla completa en KB §9–§11. Síntesis verificada [HECHO]:
- Implementado y probado automáticamente (proveedor simulado): conversación persistente con streaming/cancelación/reintento; identidad versionada; proyecto único con continuidad y ciclo de vida; memoria completa B4 (origen, decisiones, corrección, sustitución, archivo, eliminación con redacción opcional del mensaje fuente, precedencia/conflictos, panel observable); presupuesto con aviso/bloqueo; copia/validación/restauración cifradas con rollback; onboarding de clave y ruta de datos.
- **Sin implementar**: exportación estructurada (RF-031 — no existe caso de uso; verificado por búsqueda en `src/sirius/application/`); B5 (panel de contexto completo — confirmado por `REPOSITORY_STATUS.md` §126-138); B6/D-11 (indexación/búsqueda; FTS5 no existe en `src/`).
- **Solo infraestructura / pendiente de aceptación**: V6 proveedor real (pendiente prueba manual con clave); PA-001/002/008-parcial/009, PA-E2E-01, PS-01–07 (proveedor real/Windows real/evaluación humana); empaquetado Nuitka (sin evidencia).
- Divergencias documentales README↔estado: corregidas en esta rama (§15).

## 6. Auditoría técnica (Fase 4)

Hallazgos estructurales [HECHO, verificados en esta sesión sobre el árbol actual]:
- Capas limpias: 0 imports prohibidos (dominio↛PySide6/SQLAlchemy/OpenAI; aplicación↛presentación/infraestructura; presentación↛sqlite/openai).
- Alembic: 13 migraciones, cadena lineal, 1 head, 0 bifurcaciones; migraciones aditivas con pruebas upgrade/downgrade reales.
- `PRAGMA foreign_keys=ON` por conexión; `session_scope` con rollback total; transaccionalidad evento+estado probada contra SQLite real.
- Secretos: puerto+keyring+fake; pruebas de fuga reales (settings/SQLite/logs/reprs). `store=False` verificado.
- Higiene: 0 TODO/FIXME/noqa; 17 `type: ignore` (16 en tests); 26 `except Exception` en src (patrón handler UI: tipadas + genérico con log y aviso — aceptable).
- Clasificación: **crítico: 0 · alto: 0** (en código de producto de `main`) · medio: sin WAL/`busy_timeout` (bloqueos potenciales UI/worker) · bajo: presupuesto como regla de producto viviendo en capa adaptador (defendible como proxy) · mejora futura: job de CI Linux para `tests/automation` (hoy solo se ejecutan localmente: Quality-Windows las omite de forma documentada).

## 7. Estado de pruebas y aceptación (Fase 3/6)

Suite ~940 verdes en Linux (varía con las PRs de automatización pendientes); sin xfail; 1 skip justificado y documentado (Bash en Windows). Sin `assert True` ni relajaciones. Mock de `gh` modela el CLI real (lección del incidente `gh label view`). Clasificación de aceptación completa en KB §11: nada declarado superado sin evidencia; PS/PA reales explícitamente pendientes.

## 8. Auditoría de documentación (Fase 6)

Fiable y actual: `PLAN.md`, `REPOSITORY_STATUS.md`, `B4_EXECUTION.md`, `V8_EXECUTION.md` (los tres primeros incluyen ya B4f). Corregido en esta rama: README (estado V8 sin B2–B4), guía de incorporación (lecturas de automatización, equivalente Linux de `check.ps1`, B5 sin plan propio, exportación pendiente, referencia a KB y audits). Hallazgos abiertos (no corregidos aquí por autoridad o alcance): §14.

## 9. Auditoría de automatización (Fase 5)

Reconstrucción completa de la máquina de estados, productores/consumidores/precondiciones e incidentes en `docs/audits/SIRIUS_AUDITORIA_ACTIVACION_2026-07.md` (PR #62) y en la auditoría integral del repositorio (PR #59); resumen operativo en KB §17. Qué existe y está **activo en `main`** [HECHO]: Quality (Windows), advance-after-Quality, complete-after-merge, notify (6 estados, dedup por issue/estado/SHA), bootstrap de etiquetas, biblioteca robusta de E/S. Qué está **documentado/reparado pero pendiente de merge** (a fecha de esta auditoría): corrección de `ensure_label` (PR #58 — hasta entonces `advance`/`complete` fallan de forma atómica y reintentable al garantizar etiquetas), reconciliador manual + transición auto-reparadora (PR #59), puerta de validación de activación + plantilla alineada (PR #62). Qué es **externo y no inspeccionable**: las tres Routines genéricas (implementadora/revisora/correctora) — se auditan por efectos; funcionan (B4f fue implementado, revisado con hallazgos, y el corrector se negó correctamente ante un head corrupto), con un defecto conocido: **ejecuciones duplicadas** (PRs #52/#53 para un mismo Work ID; doble comentario del corrector). Qué debe mejorar antes de aumentar autonomía: fusionar las tres PRs pendientes; política del conector de escritura (§14-C1); single-flight en Routines; decidir si el reconciliador puede programarse (hoy solo manual, conforme a la prohibición de vigilancia horaria).

## 10. Evaluación del uso de Claude Max (Fase 5)

[HECHO] En el repositorio no existe ninguna integración técnica denominada "Claude Max": lo que existe es Claude Code (sesiones de ingeniería), Routines externas y GitHub Actions. [INFERENCIA] "Claude Max" es el plan de suscripción que da capacidad/acceso a esas superficies; su valor real aquí es económico-operativo (límites de uso de las Routines y sesiones — el contrato ya contempla `USAGE_LIMIT_REACHED`). Recomendación: no atribuir a "Claude Max" comportamientos técnicos propios en ningún documento (KB §18 fija la separación Claude Code / Routines / Cowork / Claude Max); cualquier automatización nueva debe seguir describiéndose por su superficie real (workflow, Routine o sesión), no por el plan que la financia. Flujo recomendado a partir de ahora: el descrito en KB §16–§17 (incidencia-contrato → Routines → puertas → merge humano), sin aumentar autonomía hasta cerrar los pendientes de §9.

## 11–13. Contradicciones, información faltante y riesgos → §14, §19, §16

## 14. Contradicciones y hallazgos abiertos

- **C1 · ALTO · [DECISIÓN]** Conector externo de escritura trunca contenidos largos y confirma sin verificar — 5 incidentes reales (2 workflows; rama de PR #57 con `knowledge_widget.py` vaciado; cuerpos de #55 y #60). El repo solo detecta/contiene. Requiere política de uso del conector (verificación por relectura; preferir git real).
- **C2 · ALTO** Automatización degradada en `main` (`ensure_label` con `gh label view` inexistente) hasta fusionar PR #58; consecuencia observada: #50 y #55 hubo que reconciliarlas manualmente tras sus merges. [DECISIÓN: merge].
- **C3 · MEDIO** `AUTOMATION_OPERATING_CONTRACT.md` cabecera "PROPUESTO EN PR #44; VIGENTE ÚNICAMENTE TRAS MERGE HUMANO": la PR #44 está fusionada → el contrato rige pero se lee como propuesto. Actualizar su estado es acto de gobernanza [DECISIÓN]; no se toca aquí.
- **C4 · MEDIO** B5 sin sección propia en `PLAN.md`: su única definición es la Issue #60, hoy **truncada** → B5 no activable hasta completar su contrato [DECISIÓN de contenido: gestor del backlog].
- **C5 · MEDIO** Routines externas sin single-flight (duplicados observados) [DECISIÓN: configuración externa].
- **C6 · BAJO** Dedup de notificaciones `no-head` puede silenciar una segunda parada distinta (caso real #60); mitigado parcialmente por la puerta de activación (PR #62); discriminador por causa anotado como diseño futuro.
- **C7 · BAJO** Issues obsoletas abiertas (#45, #38, #40, #42) del patrón antiguo de revisión [DECISIÓN: cerrarlas].
- **C8 · BAJO** README desfasado respecto a B4 — **corregido en esta rama**.
- **C9 · BAJO** `docs/decisions/` define el formato ADR pero está vacío pese a decisiones operativas posteriores registradas solo en issues/PRs (p. ej. Issue #25, contrato v1.1). Mejora recomendable: consolidar como ADR las decisiones operativas mayores.

## 15. Correcciones aplicadas en esta rama (PR #61)

1. `docs/operations/CLAUDE_PROJECT_ONBOARDING.md`: lecturas 11–12 (KB + audits) y lectura obligatoria del código real de automatización; equivalente Linux de `check.ps1`; estado ejecutivo precisado (B5 sin plan propio; exportación RF-031 pendiente; dónde vive el estado vivo de la automatización).
2. `README.md`: estado de V8.1 completado con B2a/B2b, B3a–c y B4a–f (con proveedor simulado).
3. Nuevo `docs/operations/CLAUDE_SIRIUS_KNOWLEDGE_BASE.md` (mapa permanente, 25 secciones, con fecha/commit y procedimiento de mantenimiento).
4. Este informe.

No se tocó: código de producto, pruebas, migraciones, workflows, canónicos, HEAD-R1, ni ninguna otra rama o PR.

## 16. Riesgos clasificados

**Críticos:** ninguno nuevo en `main` (sin pérdida de datos de usuario; el único candidato — corrupción de rama por C1 — es recuperable y está contenido). **Altos:** C1, C2. **Medios:** C3–C5; ausencia de evidencia Windows real/ejecutable/proveedor real (bloquea aceptación, ya reflejado en puertas). **Bajos:** C6–C9; sin WAL/busy_timeout; cobertura Bash solo local/Linux.

## 17. Mejoras recomendadas (no son decisiones)

1. *Corrección necesaria:* fusionar PRs #58/#59/#62; completar contrato de B5; política del conector (C1). 2. *Recomendable dentro del alcance:* job Linux ligero de CI para `tests/automation`; WAL+busy_timeout; ADRs para decisiones operativas mayores (C9); discriminador de causa en notificaciones `no-head`. 3. *Ideas futuras (fuera de 0.1):* nada que deba adelantarse; las ideas exploratorias permanecen en la Issue #15. *(Referencia externa usada solo como método: prácticas comunes de SQLite en escritorio —WAL/busy_timeout— y de CI multiplataforma; nada de ello altera producto ni arquitectura aprobados.)*

## 18. Ideas futuras claramente separadas

Roadmap 0.2–1.0 (Manual §14), HEAD-R1 (inactiva), backlog exploratorio (Issue #15). Ninguna es tarea actual.

## 19. Archivos no revisados y suposiciones

- No extraídos en esta pasada: `SIRIUS_CIERRE_PREARQUITECTURA_v1.0`, `SIRIUS_ESTADO_CANONICO_v2.0`, `SIRIUS_REGISTRO_DECISIONES_v1.0`, `SIRIUS_PLAN_PRUEBAS_TRAZABILIDAD_0.1`, `SIRIUS_ARQUITECTURA_TECNICA_0.1`, `Auditoria_Integral_Prearquitectura` (.docx) y `docs/robotics/head/RECTOR.md`/`DECISIONS.md`/`AUDIT.md`/`ARTIFACTS.md` completos; `V8_EXECUTION.md` líneas 61–657; `CHANGELOG.md` completo; el código de producto no cubierto por las verificaciones estructurales.
- Suposiciones: (1) `docs/canonical/STATUS.md` es veraz sobre la aprobación del paquete; (2) los IDs D-01–D-11/A-01–A-04 y PA/PS/SP citados en PLAN/V8_EXECUTION corresponden fielmente al Plan de Pruebas canónico no extraído; (3) las Routines externas siguen el contrato documentado salvo los desvíos observados. Ninguna afirmación de este informe depende solo de una suposición sin señalarlo.

## 20. Nivel de confianza

**Alto** en: gobernanza, producto/identidad, estado de verticales, automatización, riesgos. **Medio** en: correspondencia exacta requisito↔prueba del Plan de Pruebas canónico (docx no extraído) y detalle línea a línea del código no muestreado. **Bajo** en: todo lo que exige Windows real/ejecutable/proveedor real (sin evidencia posible desde este entorno).

## 21. Recomendación principal

Estabilizar el circuito de automatización **antes** de activar B5: fusionar las tres PRs de reparación pendientes, fijar la política del conector de escritura (C1) y completar el contrato de la Issue de B5. Después, continuar V8.1 por el flujo normal.

## 22. Siguiente paso concreto

Decisión del usuario sobre el merge de las PRs #58, #59 y #62 (en ese orden lógico), y completar el cuerpo de la Issue #60 (B5) con el mismo nivel de detalle que la #55 antes de reactivar `sirius:implement-requested`.
