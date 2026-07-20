# SIRIUS — Auditoría de la cadena de activación y estados (20-jul-2026, 2ª pasada)

**SHA auditado de `main`:** `07ac239a69a4fb6e860c38c9e5eae1e694250137` (B4f fusionado)
**Complementa a:** `SIRIUS_AUDITORIA_INTEGRAL_REPOSITORIO_2026-07.md` (misma fecha, pasada íntegra). Esta pasada se centra en la cadena creación → activación → implementación y en los estados atascados observados tras el merge de B4f.

## 1. Flujo real reconstruido (productor → consumidor → precondiciones)

| Estado/evento | Lo crea | Lo consume | Precondiciones que exige el consumidor | ¿Garantizadas por el paso anterior? |
|---|---|---|---|---|
| creación de incidencia | ChatGPT (API) o plantilla | — | cuerpo completo + `sirius:planned` | **NO** (hallazgo A1/A2) |
| `sirius:planned` | plantilla (auto) o humano | puerta + implementadora | alcance realmente aprobado | Solo si nace de la plantilla; por API depende del creador |
| `sirius:implement-requested` | ChatGPT/humano | puerta de activación (nueva) + Routine implementadora | abierta, `planned`, cuerpo completo, sin estados activos, sin PR previa | **NO antes de esta PR** — la puerta lo valida ahora en el repo |
| `sirius:implementing` | implementadora | — (estado) | — | sí |
| `sirius:ci-pending` | implementadora | workflow `advance` | PR abierta no draft, head == head del run Quality | sí (verificado en `advance`) |
| `sirius:review-requested` | `advance` | Routine revisora | Quality verde para head exacto | sí |
| `sirius:reviewing` → veredicto | revisora | `notify` / correctora | head == registrado | sí |
| `sirius:repair-requested` | `advance` (CI rojo) o revisora | correctora | hallazgos concretos + head == registrado | sí (hoy se negó correctamente ante head distinto) |
| `sirius:ready-for-merge` | revisora | humano (merge) | CI verde + revisión del head actual | sí |
| merge → `sirius:completed`+cierre | workflow `complete` | — | única incidencia que referencia la PR | **Degradado**: `ensure_label` roto en `main` hasta fusionar PR #58 (falló otra vez hoy con #55) |
| `sirius:blocked-decision`/`failed-safely` | Routines/workflows | humano | — | sí; recuperación: retirar la etiqueta conscientemente y reactivar |
| reconciliación | workflow manual (PR #59, pendiente) | — | casos inequívocos | pendiente de merge |

**Transición imposible detectada:** ninguna incidencia creada por API nace con las precondiciones que la activación exige (A1); la "transición" creación→activación dependía de dos acciones manuales no documentadas (aplicar `planned` y verificar el cuerpo). Ahora está documentada y validada por la puerta.

## 2. Incidente #60 reconstruido (evidencia)

1. **19:16Z** — #60 creada por API: **sin `sirius:planned`** y con el **cuerpo ya truncado** a mitad de frase ("…no crear repositorios, modelos de") — quinta ocurrencia del patrón de escritura truncada del conector (véase HAL-001 del informe integral).
2. **19:21Z** — Routine implementadora: FAILED_SAFELY (falta `planned`); retiró el evento y aplicó `failed-safely`. Notificación 🔴 emitida.
3. Reactivación manual (usuario añade `planned` + re-aplica el evento) **sin retirar `failed-safely` y sin reparar el cuerpo**.
4. **19:30Z** — segunda FAILED_SAFELY (cuerpo truncado, verificado por 3 vías). **Sin notificación**: el marcador `sirius-notification:sirius:failed-safely:no-head` ya existía (hallazgo A4).
5. Estado al auditar: `failed-safely` + `planned`, cuerpo aún truncado.

## 3. Hallazgos de esta pasada

- **A1 · P1 · Las incidencias nuevas no nacen con las precondiciones de activación.** La plantilla aplica `planned`, pero la creación por API (la vía real de ChatGPT) no lo garantiza, y nada validaba el cuerpo al activar. Causa raíz del incidente #60 (ambas paradas). **Corregido**: puerta de activación en el repositorio (rechazo temprano, diagnóstico exacto, sin auto-`planned`, sin `failed-safely`).
- **A2 · P2 · Plantilla desalineada con el validador.** `sirius-work-item.yml` no generaba la sección `Base y dependencias` que `validate_issue_body.py` exige (HAL-016 del informe integral): una incidencia nacida de la plantilla habría sido rechazada por la puerta. **Corregido**: campo obligatorio añadido a la plantilla.
- **A3 · P1 · #55 atascada en `ready-for-merge` con su PR ya fusionada.** El cierre post-merge de B4f volvió a fallar en `sirius_ensure_label` (defecto de `main`, corrección en PR #58 pendiente de merge). **Reconciliada en vivo** en esta pasada: `sirius:completed`, cerrada como completada y marcador `sirius-completed:07ac239…` registrado (ningún reintento duplicará el cierre). Verificado por relectura.
- **A4 · P2 · Deduplicación de notificaciones demasiado agresiva para fallos sin head.** Dos `failed-safely` distintos con `no-head` en la misma incidencia = una sola notificación: la segunda parada de #60 fue silenciosa; el usuario pudo creer que su corrección había funcionado. Mitigación de esta PR: la puerta rechaza cada motivo con su propio marcador y mención (cada causa distinta notifica). Riesgo residual: dos `failed-safely` de la *Routine* con `no-head` siguen deduplicándose; discriminarlos exigiría un identificador estable por causa — anotado como decisión de diseño futura, no se complica `notify` ahora.
- **A5 · P3 · Respuesta a la pregunta 15 (corregir / rechazar / detener).** La opción más segura es **rechazar antes**: corregir automáticamente (añadir `planned`) equivaldría a que una automatización apruebe planificación (prohibido por contrato); detener en la Routine cuesta una ejecución externa y deja `failed-safely` (dos veces en #60). El rechazo temprano deja el estado limpio, reintentable y explicado. La Routine conserva sus comprobaciones (la puerta no puede garantizar orden de ejecución frente al disparo simultáneo del mismo evento — carrera documentada, defensa en profundidad).
- **A6 · P3 · Cuerpo de #60 sigue truncado.** Repararlo exige contenido de planificación de B5 (alcance, requisitos, salvaguardas) que **no puede inventar una automatización**: queda como acción del gestor del backlog (el propio diagnóstico de la Routine lo detalla). No se toca en esta PR (regla: no convertir ideas no aprobadas en trabajo planificado).

Cobertura del resto de la lista de regresión pedida: etiquetas inexistentes, fallo parcial, marcador con transición incompleta, evento no repetible, estado contradictorio, Quality stale, reparación y reintento, y cierre idempotente ya tienen pruebas en `tests/automation/` (`test_sirius_issue.py`, 32; `test_sirius_reconcile.py`, 10 — PR #59) y en las simulaciones documentadas en las PRs #56/#58/#59. Esta PR añade las 10 de activación.

## 4. Correcciones aplicadas en esta PR

1. `scripts/automation/sirius_validate_activation.sh` + `.github/workflows/validate-sirius-activation.yml` — puerta de activación (rechazo temprano; nunca auto-`planned`; nunca `failed-safely`; marcador idempotente por motivo; retirada del evento verificada; fallo de retirada → run rojo reintentable).
2. `.github/ISSUE_TEMPLATE/sirius-work-item.yml` — sección obligatoria `Base y dependencias` (alineación plantilla↔validador).
3. `docs/implementation/SIRIUS_GENERIC_ROUTINES_0.1.md` — contrato de activación documentado (incluida la carrera puerta/Routine y la exigencia de retirar `failed-safely` conscientemente antes de reactivar).
4. `tests/automation/test_sirius_activation.py` — 10 pruebas: activación válida **sin caer en FAILED_SAFELY** y sin tocar nada; sin `planned` (no se añade `planned`, no se aplica `failed-safely`); cuerpo truncado real de #60; reactivación con `failed-safely` presente; activación duplicada con `implementing`; incidencia cerrada; rechazo repetido sin comentario duplicado; motivo distinto → comentario propio; fallo de retirada → reintentable; PR ignorada.
5. **Acción en vivo:** #55 reconciliada (A3).

## 5. Qué NO se cambió y por qué

- El cuerpo truncado de #60 (contenido de planificación = decisión humana, A6).
- `notify-sirius-state.yml` (la dedup `no-head` queda anotada como riesgo aceptado, A4).
- Los estados actuales de #60 (`failed-safely`+`planned` reflejan fielmente la realidad: el contrato está incompleto; retirar `failed-safely` sin reparar el cuerpo sería falsear el estado).
- Nada de producto, canónicos, B5/B6, ni las PRs #58/#59 (siguen pendientes de merge y esta PR no las solapa: archivos disjuntos).

## 6. Riesgos restantes

- Hasta fusionar **PR #58**, `advance`/`complete` siguen degradados (todas las transiciones que garanticen etiquetas fallarán de forma atómica y reintentable).
- Hasta fusionar **PR #59**, no hay reconciliador para futuros atascos.
- La puerta corre en paralelo con la Routine (mismo evento): una activación inválida aún puede costar una ejecución de Routine si esta gana la carrera; el estado final queda limpio en ambos órdenes.
- El conector externo sigue pudiendo escribir truncado (D-7 del informe integral): la puerta lo detecta en cuerpos de activación, no puede impedirlo.
