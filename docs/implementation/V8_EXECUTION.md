# V8 — Ejecución, puertas y evidencia

Este documento es el registro operativo único de V8. No sustituye el Producto, el Plan de Pruebas, la Arquitectura, las ATD ni `docs/implementation/PLAN.md`.

## Estado

- V8.1 — Corrección documental y automatizada: **ACTIVA**.
- V8.2 — Windows sin clave: **BLOQUEADA** hasta integración automática verde.
- V8.3 — Proveedor real: **BLOQUEADA**.
- V8.4 — PA-E2E-01 y cierre: **BLOQUEADA**.
- Sirius 0.1: **NO ACEPTADO** y **NO TERMINADO**.

No se crea una fase canónica adicional denominada `Preparación V8`.

## Fuentes normativas

- `docs/canonical/STATUS.md`
- Definición de Producto Sirius 0.1 aprobada
- Plan de Pruebas y Trazabilidad aprobado
- Arquitectura Técnica Sirius 0.1 aprobada
- ATD-001 a ATD-012
- `docs/implementation/PLAN.md`
- `AGENTS.md`

Los resúmenes de este documento no son normativos. Ante contradicción, prevalecen las fuentes aprobadas.

## Reglas de ejecución

- No ampliar el alcance de Sirius 0.1.
- No cambiar Producto, Arquitectura o ATD sin propuesta y aprobación explícita.
- No usar ni obtener una clave API real hasta abrir formalmente V8.3.
- No introducir voz, robótica, web, archivos externos, herramientas, automatización, RAG, multiagente ni programación supervisada.
- Cada corrección debe enlazar con un requisito aprobado y una prueba identificada.
- Trabajar en ramas breves, con cambios pequeños, reversibles y comprobaciones verdes.
- No confundir infraestructura implementada, comportamiento utilizable, prueba automática, prueba manual y aceptación formal.

## Puertas

### Puerta V8.2 — Windows sin clave

Debe cumplirse:

- integración automática verde sobre el estado exacto que se probará;
- defectos funcionales del bloque correspondiente corregidos;
- ejecutable reproducible disponible cuando la prueba lo requiera;
- guion manual con resultados esperados;
- entorno de datos desechable y copia externa preparada.

### Puerta V8.3 — Proveedor real

Debe cumplirse todo lo anterior y además:

- D-01, D-02, D-03, D-04, D-05, D-08, D-11 y A-01 cerrados;
- D-06, D-07, D-09 y D-10 corregidos o resueltos conforme al Plan de Pruebas;
- A-02 y A-03 verificados;
- suite automática PA/SP sin clave completamente verde;
- Credential Manager comprobado con un valor señuelo;
- copia y restauración comprobadas desde el ejecutable;
- cero defectos bloqueantes o altos conocidos;
- autorización explícita del usuario para obtener y usar una clave temporal.

### Puerta V8.4 — E2E y cierre

Debe cumplirse:

- ventana de proveedor real completada sin defectos bloqueantes;
- PA-001 a PA-025 ejecutables;
- PS-01 a PS-07 preparados para evaluación humana;
- SP-01 a SP-07 ejecutables;
- entorno, versión, commit y artefacto identificados;
- proyecto pequeño de aceptación definido y no canónico.

## Catálogo cerrado de trabajo

| ID | Resumen | Fuente principal | Bloquea proveedor real | Bloquea cierre | Estado | Bloque |
|---|---|---|---:|---:|---|---|
| D-01 | Onboarding y validación de credencial | RF-001/002; PA-001/002 | Sí | Sí | Abierto | B2 |
| D-02 | Proyecto operable | RF-014–018; PA-006–009 | Sí | Sí | Abierto | B3 |
| D-03 | Eventos, memoria y decisiones | RF-019–026; PA-010–016 | Sí | Sí | Abierto | B4 |
| D-04 | Panel de contexto | Producto §9.1 | Sí | Sí | Abierto | B5 |
| D-05 | Reintento sin reescribir | RF-007; PA-003/017 | Sí | Sí | Abierto | B7 |
| D-06 | Markdown seguro y código copiable | RF-008; SP-07 | No | Sí | Abierto | B8 |
| D-07 | Exportación estructurada | RF-031; PA-020; ATD-009 | No | Sí | Abierto | B9 |
| D-08 | Errores accionables | RF-028; RNF-018 | Sí | Sí | Abierto | B7 |
| D-09 | Aviso de presupuesto | RF-030; PA-018 | No | Sí | Abierto | B7 |
| D-10 | Ruta de datos y activación clara | Producto §5.1 | No | Sí | Abierto | B2 |
| D-11 | Contexto pertinente y limitado | RNF-008; SP-03; ATD-007 | Sí | Sí | Abierto | B6 |
| A-01 | Política de acciones fuera de alcance | RF-035; PA-024 | Sí | Sí | Abierto | B10 |
| A-02 | Recuperación tras cierre forzado | RNF-005/006; PA-019 | No | Sí | Abierto | B11 |
| A-03 | Empaquetado reproducible | ATD-011 | Sí, como puerta | Sí | Abierto | B13 |
| A-04 | Evidencia de aceptación trazada | Plan de Pruebas | No, por sí sola | Sí | Abierto | B12/B16 |

Cualquier defecto nuevo debe vincularse a un requisito ya aprobado. Si no puede hacerse, debe detenerse el trabajo y solicitar decisión.

## Bloques operativos

| Bloque | Entrega | Estado |
|---|---|---|
| B1 | Reconciliación documental y trazabilidad | En curso |
| B2 | Onboarding, credencial, ruta y activación | Pendiente |
| B3 | Proyecto mínimo y ciclo de vida | Pendiente |
| B4 | Eventos, recuerdos, decisiones y conflictos | Pendiente |
| B5 | Panel de contexto | Pendiente |
| B6 | Selección y presupuesto de contexto | Pendiente |
| B7 | Reintento, errores y presupuesto | Pendiente |
| B8 | Markdown seguro y copia de código | Pendiente |
| B9 | Exportación estructurada | Pendiente |
| B10 | Política de acciones fuera de alcance | Pendiente |
| B11 | Recuperación tras cierre forzado | Pendiente |
| B12 | Suite PA/SP automática, rendimiento y evidencia | Pendiente |
| B13 | Empaquetado reproducible | Pendiente |
| B14 | Windows sin clave | Bloqueado |
| B15 | Ventana compacta con proveedor real | Bloqueado |
| B16 | PA-E2E-01, regresión y cierre | Bloqueado |

## Criterio de cierre de bloque

Un bloque solo puede marcarse terminado cuando:

- el alcance está trazado a requisitos aprobados;
- las pruebas previstas existen y pasan;
- `scripts/check.ps1` pasa cuando el bloque contiene código;
- CI está verde en la PR;
- no quedan comentarios de revisión sin resolver;
- la documentación operativa refleja el comportamiento real;
- el usuario autoriza el merge.

## Registro de evidencia

Añadir una fila por resultado verificable. No registrar secretos ni contenido sensible.

| Fecha | Bloque | Commit/artefacto | Tipo | Prueba | Resultado | Evidencia | Observaciones |
|---|---|---|---|---|---|---|---|
| 2026-07-15 | B1 | `a05af3c` | Documental | Reconciliación de estado y puertas | Superada | PR #17, CI Quality verde | Sin cambios funcionales |

Tipos permitidos: `automática`, `CI`, `manual-Windows`, `proveedor-real`, `evaluación-humana`, `documental`.

## Estado de pruebas de aceptación

Estados permitidos: `no preparada`, `preparada`, `automática superada`, `manual pendiente`, `superada`, `fallida`, `bloqueada`.

| Grupo | Estado | Dependencia principal |
|---|---|---|
| PA-001 a PA-025 | Bloqueada | D-01 a D-11 y A-01/A-02 según prueba |
| PS-01 a PS-07 | Bloqueada | Proveedor real y evaluación humana |
| SP-01 a SP-07 | Bloqueada parcialmente | D-03, D-06, D-11, Windows y proveedor real |
| PA-E2E-01 | Bloqueada | B2 a B15 |

## Próximo trabajo autorizado

Completar B1 mediante revisión e integración de este documento. Después, preparar B2 o el bloque que se autorice expresamente, sin iniciar todavía Windows real ni proveedor real.

## Cierre de V8

V8 solo puede cerrarse cuando:

- PA-001 a PA-025 estén superadas;
- PA-E2E-01 esté superada;
- PS-01 a PS-07 estén evaluadas y aprobadas;
- SP-01 a SP-07 estén superadas;
- no existan defectos bloqueantes o altos;
- los defectos medios estén corregidos o aceptados explícitamente conforme al Plan de Pruebas;
- documentación, código y evidencia coincidan;
- el usuario apruebe explícitamente Sirius 0.1.

Al cerrar Sirius 0.1, este documento se congela como evidencia histórica.