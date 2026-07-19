# SIRIUS - Contrato operativo de automatización con Claude Code

**Versión:** 1.0  
**Fecha:** 18 de julio de 2026  
**Estado:** VIGENTE - consolidación de decisiones ya tomadas  
**Autoridad:** Operativa para el flujo de desarrollo automatizado de Sirius 0.1  
**No modifica:** Producto, Arquitectura Técnica, ATD, requisitos ni alcance de Sirius 0.1

## 0. Propósito

Este documento consolida la conversación completa sobre la automatización del desarrollo de Sirius con Claude Code. Su finalidad es impedir desviaciones, improvisaciones y repeticiones de pasos ya realizados.

No crea una arquitectura multiagente, no añade servicios de pago y no autoriza nuevas funciones de Sirius. Solo fija el orden de trabajo, las puertas de avance y las prohibiciones vigentes.

Cuando una instrucción posterior contradiga este documento, el agente debe detenerse y pedir una decisión explícita al usuario. No debe reinterpretar, completar ni sustituir el plan por iniciativa propia.

## 1. Conclusión de la auditoría

La automatización buscada es viable, pero solo mediante una progresión controlada:

1. demostrar primero que una sesión cloud trabaja sin depender del ordenador del usuario ni solicitar aprobaciones rutinarias;
2. ejecutar después un subbloque pequeño de B4 en cloud;
3. revisar la PR de forma independiente y controlada;
4. repetir el método hasta acumular evidencia suficiente;
5. automatizar eventos de GitHub únicamente después de demostrar estabilidad y recibir aprobación expresa.

El objetivo no es una IA autónoma permanente. El objetivo es una fábrica de trabajo acotada que entregue uno de estos resultados:

- `READY_FOR_HUMAN_REVIEW`
- `BLOCKED_BY_DECISION`
- `FAILED_SAFELY`
- `USAGE_LIMIT_REACHED`

El merge siempre permanece bajo control humano.

## 2. Estado actual verificado

A fecha de este documento:

- B3a, B3b y B3c están integrados.
- B4 está autorizado y dividido operativamente en B4a-B4f.
- La PR #30, `docs: define B4 staged execution and cloud smoke test`, fue fusionada.
- La PR #33, `test: isolate platform directories across OSes`, fue fusionada, corrigiendo el aislamiento multiplataforma de las pruebas.
- La rutina de prueba de humo cloud ya fue creada y lanzada por el usuario.
- La rutina utiliza un disparador de **una sola ejecución programada**.
- No utiliza disparador API.
- No utiliza evento de GitHub.
- La Routine utiliza el conector `Claude_Code_Remote`.
- La corrección automática de pull requests está desactivada.
- La notificación push está activada.
- **18 de julio de 2026:** el resultado de la prueba de humo cloud quedó en `CLOUD_SMOKE_PASSED`. La PR #34, `docs: record successful cloud smoke test`, fue fusionada en `main`; su evidencia está registrada en `docs/implementation/CLOUD_SMOKE_EVIDENCE_20260718.md`.
- **18 de julio de 2026:** B4a se implementó en cloud controlado siguiendo la Fase B (rama `claude/intelligent-bohr-1s38y6`): evento de origen persistente, enlace real recuerdo-evento-mensaje, guardado manual explícito (`SaveManualMemoryUseCase`) y consulta de origen (`GetMemoryOriginUseCase`), sin GUI ni cambios de alcance. Ruff, mypy y pytest en verde (595 pruebas). Una PR borrador quedó abierta hacia `main`, sin merge; pendiente de revisión independiente (Fase C) y autorización de merge del usuario.
- **18 de julio de 2026:** la revisión de Fase C sobre la PR #36 encontró un `BLOCKER` transaccional: `SaveManualMemoryUseCase` confirmaba el evento de origen y el recuerdo en dos sesiones/transacciones SQLite independientes, en contra de SIRIUS-ARQ-0.1 S4/S8.1 ("evento y cambio de memoria se guardan en la misma transacción" mediante una `UnitOfWork`). Se corrigió en la misma rama, sin nueva rama ni nueva PR: se añadió el puerto `UnitOfWork` (`src/sirius/ports/unit_of_work.py`) y su adaptador SQLite (`src/sirius/adapters/persistence/sqlite_unit_of_work.py`), y `SaveManualMemoryUseCase` ahora crea el evento, el recuerdo y su primera revisión dentro de una única transacción, con `commit()` solo si todo tuvo éxito y rollback completo ante cualquier excepción. `GetMemoryOriginUseCase` sigue usando repositorios independientes de solo lectura, sin transacción compartida. Ruff, mypy y pytest en verde (602 pruebas: 595 previas + 7 nuevas de atomicidad/rollback).
- **18 de julio de 2026:** la PR #36 (B4a) quedó **fusionada en `main`** (commit `c025683c960a19a1a9c1aa40fa861547026118cc`), con el workflow `Quality` en verde sobre ese commit. Verificado directamente sobre `origin/main` antes de iniciar B4b: `git log` confirma el commit de merge y el histórico del check run confirma `conclusion: success`.
- **18 de julio de 2026:** B4b — Decisiones y aprobación explícita — se implementó en cloud controlado, partiendo del `main` ya fusionado de B4a: entidad de decisión, migración Alembic no destructiva (`decisions`/`decision_revisions`), `DecisionRepository`/`SqliteDecisionRepository`, extensión mínima de `UnitOfWork` con `decision_repository`, `ProposeDecisionUseCase`, `ApproveDecisionUseCase` (confirmación explícita obligatoria) y `GetDecisionOriginUseCase`. Ruff, mypy y pytest en verde (669 pruebas). Una PR borrador quedó abierta hacia `main`, sin merge.
- **18 de julio de 2026 — decisión operativa expresa del usuario:** el usuario decidió sustituir, solo para esta transición concreta, la puerta de "tres PR consecutivas" de la §7 (Fase E) por una autorización directa y explícita: activar desde la PR de B4b la revisión automática solicitada mediante una incidencia GitHub etiquetada `agent-review-requested` en `canelamoraguezandyjesus-bot/sirius`, siempre que la PR de B4b quede lista y con CI (`Quality`) en verde. Ver §10 para el registro formal de este cambio y sus límites exactos.
- **18 de julio de 2026 — estado real verificado de B4b:** la PR #37, `feat: implement B4b explicit decisions`, quedó **fusionada en `main`** (commit de merge `d1bbb872751a96ca11ec38c20fd8b3fb5322651c`), con el workflow `Quality` en verde sobre ese commit (669 pruebas superadas). Verificado directamente sobre `origin/main` (no solo por este resumen) antes de iniciar B4c: `git log` confirma el commit de merge y `pull_request_read`/`get_check_runs` confirma `conclusion: success` sobre el commit `982d968b9d4da425af57a5d53bcd903ecda94b2b` de la PR.
- **18 de julio de 2026:** B4c — Corrección y sustitución — se implementó en cloud controlado, partiendo del `main` ya fusionado de B4b: `CorrectMemoryUseCase` (consolida `MemoryRepository.correct_memory`, ya existente desde V4, bajo el mismo contrato transaccional de B4a: evento + nueva revisión inmutable + movimiento del puntero `current_revision` en una sola `UnitOfWork`); estado `DecisionStatus.SUPERSEDED` y campo `Decision.supersedes_decision_id` (equivalente, a nivel de decisión, al `knowledge_revision.supersedes_revision_id` de la arquitectura aprobada); `SupersedeDecisionUseCase` (sustitución explícita con confirmación obligatoria, ya que aprueba la sustituta y marca la sustituida como `SUPERSEDED` en la misma transacción); `DecisionRepository.supersede_decision`/`list_current_decisions`/`get_superseding_decision`; migración Alembic aditiva `05559a954593` (`decisions.supersedes_decision_id`, columna nula, no destructiva). Ruff, mypy y pytest en verde (735 pruebas: 669 previas + 66 nuevas). Una PR borrador quedó abierta hacia `main`, sin merge.
- **18 de julio de 2026 — autorización operativa expresa del usuario para B4c:** igual que para B4b (ver la entrada anterior y el cambio registrado en §10), el usuario autoriza expresamente activar desde la PR de B4c la revisión automática ya configurada: crear una incidencia GitHub etiquetada `agent-review-requested` en `canelamoraguezandyjesus-bot/sirius` en cuanto la PR de B4c quede lista y con CI (`Quality`) en verde, manteniendo la revisión separada de la implementación. Esta autorización cubre únicamente la revisión automática de B4c; siguen prohibidos revisión en cada push, auto-fix, correcciones de la Routine revisora, merge automático, trabajo paralelo sobre otro subbloque, check-ins horarios y tareas en segundo plano tras terminar. Ver §10 para el registro formal.

### Próxima acción exacta

La Fase A quedó superada con `CLOUD_SMOKE_PASSED`. La Fase B se ejecutó tres veces: B4a (fusionado en `main`, PR #36), B4b (fusionado en `main`, PR #37) y B4c (PR borrador abierta, sin merge, implementada sobre el `main` con B4b ya fusionado). Por las decisiones operativas del 18 de julio de 2026 (§10), la PR de B4c activa también la revisión por evento de GitHub (incidencia `agent-review-requested`) en cuanto su CI quede en verde — sin esperar tres PR consecutivas adicionales, y sin ampliar ninguna otra prohibición vigente (sin revisión por push, sin auto-fix, sin merge automático). El usuario conserva la autorización de merge sobre B4c. B4d, B4e y B4f no han comenzado.

## 3. Decisiones operativas no negociables

### 3.1 Coste y servicios

- No se utilizará una clave API de Anthropic para este flujo.
- No se utilizará el disparador API de Routines.
- No se añadirán APIs, créditos automáticos, servicios de revisión ni suscripciones adicionales.
- Se utilizarán únicamente Claude Pro, Claude Code/Routines y GitHub dentro de las capacidades ya disponibles.

### 3.2 Control y seguridad

- Ningún agente hace merge.
- Ningún agente empuja directamente a `main`.
- Ningún agente cambia Producto, Arquitectura, ATD o documentos canónicos.
- Ningún agente rebaja, elimina o modifica pruebas para conseguir verde.
- Ningún agente usa claves reales, proveedor real, Credential Manager real ni datos personales durante las fases automáticas iniciales.
- Las pruebas manuales de Windows no se declaran superadas por una sesión cloud.

### 3.3 Agentes y coordinación

- No se construirá una plataforma multiagente.
- No se añadirán agentes de coordinación, gestores de agentes ni orquestación adicional sin decisión expresa del usuario.
- Una revisión independiente puede realizarse como una sesión separada y controlada, pero no se convierte en una arquitectura de agentes.
- El usuario decide si en el futuro se añade cualquier agente especializado.

### 3.4 Automatización progresiva

- Durante el piloto no se activa una Routine por cada push.
- Durante el piloto no se activa auto-fix general.
- Durante el piloto no se automatiza el merge.
- Un evento de GitHub no se introduce hasta cumplir la puerta definida en la sección 7.

## 4. Flujo aprobado, fase por fase

### Fase A - Prueba de humo cloud (SUPERADA — 18 de julio de 2026)

Objetivo: demostrar que Claude puede trabajar desde un clon limpio, instalar dependencias, ejecutar toda la validación, crear evidencia y preparar una PR sin depender del ordenador del usuario ni solicitar aprobaciones rutinarias.

Configuración aprobada:

- disparador: una sola vez;
- API: no;
- evento de GitHub: no;
- conector: `Claude_Code_Remote`;
- auto-fix: desactivado;
- notificación push: activada;
- merge: prohibido.

Resultados posibles y acción obligatoria:

| Resultado | Acción |
|---|---|
| `CLOUD_SMOKE_PASSED` | Cumplido. Evidencia verificada en `docs/implementation/CLOUD_SMOKE_EVIDENCE_20260718.md`; PR #34 fusionada. Preparar B4a en Fase B. |
| `BLOCKED_BY_PERMISSION` | Corregir únicamente el permiso exacto que bloqueó la ejecución. No ampliar permisos de forma general. Repetir la prueba completa. |
| `BLOCKED_BY_ENVIRONMENT` | Corregir de forma reproducible el entorno cloud. Repetir la prueba completa. |
| `FAILED_SAFELY` | Diagnosticar la causa. No comenzar B4a. |
| `USAGE_LIMIT_REACHED` | Esperar la renovación de cuota. No rediseñar el flujo. |

### Fase B - B4a en cloud controlado (preparada para iniciar, no iniciada)

La puerta de esta fase está satisfecha: la prueba de humo cloud terminó en `CLOUD_SMOKE_PASSED` (18 de julio de 2026). B4a queda preparado para ejecutarse en cloud controlado, pero todavía no ha comenzado.

La ejecución de B4a utilizará una nueva Routine o ejecución cloud controlada con disparador de una sola vez. No usará API ni evento de GitHub.

Debe:

1. leer las fuentes obligatorias;
2. inspeccionar la memoria V4 existente;
3. implementar únicamente B4a;
4. ejecutar Ruff, mypy, pytest y `git diff --check`;
5. preparar una PR;
6. detenerse sin merge.

### Fase C - Revisión independiente y controlada

La primera revisión no se activa automáticamente por GitHub.

- Se inicia de forma explícita después de que exista la PR.
- La revisión no modifica código en su primera pasada.
- Se permiten como máximo dos ciclos revisión-corrección.
- El comportamiento normal será una corrección y una segunda revisión.
- Si no converge, el estado final es `BLOCKED_BY_DECISION`.
- El usuario autoriza o rechaza el merge.

### Fase D - Repetición secuencial de B4

Los subbloques se ejecutan uno detrás de otro. No se trabaja en paralelo sobre memoria, migraciones o contratos compartidos.

Cada subbloque requiere:

- rama propia;
- PR propia;
- alcance trazado;
- pruebas nuevas o actualizadas;
- suite completa verde;
- revisión;
- autorización humana de merge.

### Fase E - Automatización por eventos de GitHub

No se abre hasta que existan **tres PR consecutivas satisfactorias** producidas por el flujo controlado y el usuario lo apruebe expresamente.

Si se aprueba, la primera automatización por evento será una auditoría solicitada explícitamente, preferentemente mediante una etiqueta como:

`agent-review-requested`

No se activará en cada push. No hará merge. No decidirá producto ni arquitectura.

### Fase F - Auto-fix limitado

Solo se estudiará después de demostrar que CI y revisión producen observaciones claras y repetibles.

Podrá limitarse a fallos inequívocos como lint, tipos, imports o pruebas deterministas. Nunca abarcará migraciones destructivas, seguridad, contratos públicos, memoria, documentos canónicos o decisiones de arquitectura sin aprobación expresa.

## 5. División canónica de B4

La división autorizada y vigente es:

### B4a - Origen consultable y guardado manual

- evento de origen persistente;
- enlace entre recuerdo y evento o mensaje;
- guardado manual explícito;
- consulta del origen;
- fecha, estado y versión observables;
- RF-019, RF-021 y PA-010.

### B4b - Decisiones y aprobación explícita

- decisión sobre la infraestructura de conocimiento existente;
- propuesta y aprobación;
- una exploración no se convierte en decisión aprobada;
- RF-020 y PA-011.

### B4c - Corrección y sustitución

- revisión inmutable;
- versión vigente autoritativa;
- relación de sustitución;
- exclusión del contexto ordinario de versiones sustituidas;
- RF-022, RF-023, PA-012 y PA-013.

### B4d - Archivo, eliminación y redacción de origen

- archivo consultable fuera del contexto normal;
- eliminación con confirmación;
- marcador mínimo sin contenido;
- opción explícita sobre el mensaje fuente;
- RF-024, RF-025, PA-015, PA-016 y SP-06.

### B4e - Precedencia y conflictos

- detección determinista de incompatibilidades;
- prioridad de decisión aprobada vigente cuando corresponda;
- aclaración cuando no exista precedencia;
- prohibición de elegir silenciosamente;
- RF-026, PA-014 y DR-011.

### B4f - Integración observable y cierre

- integración mínima en las superficies existentes;
- composición, interfaz y pruebas GUI necesarias;
- búsqueda local solo en la medida necesaria;
- cierre de PA-010 a PA-016 en su parte automatizable;
- actualización de evidencia operativa.

## 6. Contrato de cada ejecución funcional

Toda tarea automatizada debe contener explícitamente:

- objetivo;
- alcance permitido;
- fuera de alcance;
- requisitos y pruebas vinculadas;
- archivos o capas previsibles;
- comandos de validación;
- condición de parada;
- estados finales permitidos;
- prohibición de merge.

La ejecución debe trabajar hasta obtener un resultado verificable, pero no puede inventar una decisión para desbloquearse.

## 7. Puerta para automatizar más

La automatización puede avanzar de nivel únicamente si se cumplen todas estas condiciones:

1. tres PR consecutivas terminan sin ampliación de alcance;
2. la suite completa queda verde;
3. no se necesitan más de dos ciclos de revisión-corrección;
4. las PR son comprensibles y acotadas;
5. no se producen cambios peligrosos o no autorizados;
6. la intervención del usuario queda limitada a iniciar, resolver decisiones reales y autorizar merge;
7. el usuario aprueba expresamente el siguiente nivel.

Cumplir las métricas no autoriza automáticamente el cambio de nivel.

**Excepción registrada el 18 de julio de 2026** (ver §10): la condición 1 de esta puerta ("tres PR consecutivas terminan sin ampliación de alcance") queda sustituida, únicamente para la transición hacia la revisión automática por incidencia etiquetada `agent-review-requested`, por una autorización directa y explícita del usuario sobre la PR de B4b. Las condiciones 2 a 6 de esta puerta siguen exigiéndose tal cual sobre esa PR (suite completa verde, máximo dos ciclos de revisión-corrección, PR comprensible y acotada, sin cambios peligrosos, intervención del usuario limitada a iniciar/decidir/autorizar merge). Esta excepción no reduce ninguna otra restricción de la sección 3: sigue sin activarse revisión en cada push, auto-fix general ni merge automático.

## 8. Reglas antidesviación para ChatGPT y Claude

Antes de dar una instrucción sobre Routines, cloud, revisión, permisos o automatización, el agente debe:

1. leer este documento;
2. declarar internamente cuál es la fase actual;
3. proponer únicamente la siguiente acción de esa fase;
4. comprobar si el usuario ya realizó esa acción;
5. distinguir estado real, plan futuro y decisión pendiente.

Está prohibido:

- introducir API cuando no está aprobada;
- adelantar eventos de GitHub;
- adelantar auto-fix;
- convertir una posible capacidad futura en una instrucción actual;
- pedir al usuario repetir pasos ya realizados;
- ofrecer varias arquitecturas de agentes no solicitadas;
- afirmar que algo está automatizado cuando solo existe documentación;
- afirmar que una Routine terminó correctamente sin revisar su resultado y evidencia;
- inventar elementos de la interfaz; si la pantalla no coincide, se pide una captura y se avanza desde lo visible.

## 9. Auditoría de errores detectados en la conversación

### Error 1 - Confundir preparación con automatización

Se afirmó que el sistema estaba preparado cuando todavía solo existían documentos y comandos locales.

**Corrección:** la automatización real empieza cuando la Routine cloud completa una ejecución sin depender del ordenador del usuario.

### Error 2 - Introducir el disparador API

Se recomendó API pese a que el plan excluía APIs adicionales y el usuario no quería claves ni tokens.

**Corrección:** API queda expresamente fuera del piloto y del flujo vigente.

### Error 3 - Adelantar eventos de GitHub

Se propuso crear el auditor por evento antes de demostrar el flujo controlado.

**Corrección:** los eventos de GitHub se posponen hasta tres PR satisfactorias y nueva aprobación explícita.

### Error 4 - Adelantar auto-fix

Se describió un bucle automático de corrección antes de validar su estabilidad.

**Corrección:** auto-fix permanece desactivado y fuera de la fase actual.

### Error 5 - Cambiar el plan mientras se ejecutaba

Se dieron instrucciones distintas en mensajes consecutivos, aumentando carga mental y riesgo.

**Corrección:** este documento fija la secuencia y obliga a trabajar con una única siguiente acción.

### Error 6 - Añadir coordinación o agentes no solicitados

Se sugirieron agentes, coordinación y estructuras que el usuario había reservado para una decisión posterior.

**Corrección:** no se añade ninguna arquitectura de agentes. Una sesión revisora separada es una operación puntual, no una decisión de sistema.

## 10. Gestión de cambios

Este contrato solo puede cambiar por una decisión explícita del usuario.

Toda modificación debe:

- indicar fecha;
- identificar la decisión cambiada;
- explicar el motivo;
- señalar qué sección sustituye;
- actualizar el estado operativo correspondiente;
- evitar reescribir retrospectivamente lo ocurrido.

Las ideas exploratorias y las capacidades disponibles en una herramienta no modifican este contrato.

### Cambio registrado el 18 de julio de 2026

- **Fecha:** 18 de julio de 2026.
- **Decisión cambiada:** la condición 1 de la puerta de la sección 7 ("tres PR consecutivas terminan sin ampliación de alcance") y, en consecuencia, el disparador de entrada a la Fase E de la sección 4.
- **Motivo:** decisión operativa expresa del usuario: en vez de esperar tres PR consecutivas satisfactorias adicionales a B4a, autoriza activar ya, desde la PR de B4b, la primera revisión automática por evento de GitHub descrita en la Fase E — una auditoría solicitada explícitamente mediante una incidencia etiquetada `agent-review-requested`, exactamente como la Fase E ya preveía como primer paso de esa etapa.
- **Sección que sustituye:** sección 7, condición 1 (únicamente para esta transición); sección 4, Fase E (activación anticipada, con el mismo alcance ya descrito allí: ninguna otra ampliación).
- **Estado operativo actualizado:** ver la nueva entrada del 18 de julio de 2026 en la sección 2 y la "Próxima acción exacta" de esa misma sección.
- **Alcance exacto de lo autorizado — solo esto:**
  - crear, en una sola operación, una incidencia GitHub en `canelamoraguezandyjesus-bot/sirius` con la etiqueta `agent-review-requested` aplicada desde su creación, únicamente cuando la PR de B4b exista, esté lista y su CI (`Quality`) esté en verde;
  - esa incidencia existe solo para activar la Routine "Sirius PR Reviewer" ya configurada por el usuario para escuchar ese evento.
- **Sigue expresamente prohibido** (sin cambios respecto a la sección 3.4 y la Fase E/F):
  - revisión automática en cada push;
  - auto-fix general o automático de cualquier tipo;
  - merge automático;
  - cambios automáticos de producto o arquitectura;
  - trabajo paralelo sobre otros subbloques de B4;
  - cualquier otra ampliación de automatización no descrita aquí.
- Esta excepción es puntual, para la transición B4a→B4b descrita arriba; no reabre ni relaja de forma general la puerta de la sección 7 para transiciones futuras, que requerirán su propia decisión expresa o el cumplimiento ordinario de las condiciones ya definidas.

### Cambio registrado el 18 de julio de 2026 (B4b→B4c)

- **Fecha:** 18 de julio de 2026.
- **Decisión cambiada:** ninguna regla de la sección 7 ni de la Fase E se reinterpreta; este registro extiende, a la PR de B4c, la misma autorización puntual ya concedida a la PR de B4b (ver el cambio anterior), porque la PR de B4b se fusionó en el ínterin y B4c es ahora el subbloque en curso.
- **Motivo:** decisión operativa expresa del usuario: activar, desde la PR de B4c y bajo las mismas condiciones y límites ya fijados para B4b, la revisión automática por incidencia etiquetada `agent-review-requested`.
- **Sección que sustituye:** ninguna; es una aplicación puntual adicional del mismo mecanismo ya descrito en el cambio del 18 de julio de 2026 anterior y en la Fase E de la sección 4, no una modificación de sus términos.
- **Estado operativo actualizado:** ver la nueva entrada del 18 de julio de 2026 en la sección 2 ("autorización operativa expresa del usuario para B4c") y la "Próxima acción exacta" de esa misma sección.
- **Alcance exacto de lo autorizado — solo esto:**
  - crear, en una sola operación, una incidencia GitHub en `canelamoraguezandyjesus-bot/sirius` con la etiqueta `agent-review-requested` aplicada desde su creación, únicamente cuando la PR de B4c exista, esté lista y su CI (`Quality`) esté en verde;
  - esa incidencia existe solo para activar la Routine "Sirius PR Reviewer" ya configurada por el usuario para escuchar ese evento.
- **Sigue expresamente prohibido** (sin cambios respecto a la sección 3.4 y la Fase E/F, y respecto al cambio anterior):
  - revisión automática en cada push;
  - auto-fix general o automático de cualquier tipo;
  - correcciones realizadas por la Routine revisora;
  - merge automático;
  - cambios automáticos de producto o arquitectura;
  - trabajo paralelo sobre otros subbloques de B4 (B4d, B4e, B4f no comienzan);
  - check-ins horarios o suscripciones de vigilancia sobre esta PR;
  - tareas en segundo plano después de terminar;
  - cualquier otra ampliación de automatización no descrita aquí.
- Esta excepción es puntual, para la transición B4b→B4c descrita arriba; no reabre ni relaja de forma general la puerta de la sección 7 para transiciones futuras.

## 11. Definición de éxito del flujo

El flujo se considera útil cuando el usuario puede iniciar una tarea acotada y ausentarse, y después recibe:

- una PR trazable;
- pruebas ejecutadas;
- estado final claro;
- ausencia de prompts rutinarios de permiso;
- ausencia de cambios en `main`;
- ausencia de merge automático;
- bloqueo seguro cuando falta una decisión.

No se exige que toda tarea termine implementada. Se exige que termine correctamente o se bloquee de forma explícita y segura.

## 12. Estado que debe consultarse al reanudar

La Routine de prueba de humo ya lanzada terminó en `CLOUD_SMOKE_PASSED` (18 de julio de 2026; evidencia en `docs/implementation/CLOUD_SMOKE_EVIDENCE_20260718.md`, PR #34 fusionada).

B4a se implementó el 18 de julio de 2026 (rama `claude/intelligent-bohr-1s38y6`) conforme a la Fase B. La Fase C encontró un `BLOCKER` transaccional (evento y recuerdo no se guardaban en la misma transacción); se corrigió en la misma rama y PR mediante una `UnitOfWork`, con Ruff, mypy y pytest en verde (602 pruebas). **La PR #36 quedó fusionada en `main`** el 18 de julio de 2026 (commit `c025683c960a19a1a9c1aa40fa861547026118cc`, `Quality` en verde).

B4b se implementó el 18 de julio de 2026 sobre ese `main` ya fusionado, conforme a la Fase D (repetición secuencial de B4): rama propia, PR propia, Ruff/mypy/pytest en verde (669 pruebas). Por la decisión operativa registrada en la sección 10, esa PR activó además la primera revisión automática por evento de GitHub (incidencia `agent-review-requested`). **La PR #37 quedó fusionada en `main`** el 18 de julio de 2026 (commit de merge `d1bbb872751a96ca11ec38c20fd8b3fb5322651c`, `Quality` en verde) — verificado directamente sobre `origin/main` antes de iniciar B4c.

B4c — Corrección y sustitución — se implementó el 18 de julio de 2026 sobre ese `main` ya fusionado, conforme a la Fase D: rama propia (`feat/b4c-correction-supersession-20260719-01`), PR propia, Ruff/mypy/pytest en verde (735 pruebas: 669 previas + 66 nuevas). Por el cambio registrado en la sección 10 (B4b→B4c), esta PR activa también la revisión automática por incidencia `agent-review-requested` en cuanto su CI quede en verde — sin esperar tres PR consecutivas adicionales, y sin ampliar ninguna otra prohibición vigente (sin revisión por push, sin auto-fix, sin merge automático). No se ha hecho ningún merge de la PR de B4c.

Al retomar este trabajo, la primera pregunta operativa no es "¿qué automatizamos ahora?". Es:

**¿La PR de B4c ya fue revisada (por la Routine "Sirius PR Reviewer" disparada por la incidencia, o por una revisión adicional) y el usuario autorizó su merge, o sigue pendiente?**

Mientras esa PR no esté fusionada, la única acción válida es completar su revisión — nunca iniciar B4d, adelantar más automatización de la descrita en la sección 10, ni un merge automático.
