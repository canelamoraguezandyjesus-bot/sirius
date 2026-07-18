# SIRIUS - Contrato operativo de automatización con Claude Code

**Versión:** 1.1
**Fecha:** 18 de julio de 2026  
**Última actualización:** 18 de julio de 2026 - cierre de la Fase A cloud y apertura del piloto local (ver Sección 13)
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

> **Nota (ver Sección 13):** los pasos 1 y 2 anteriores describen el plan cloud original y se conservan como registro histórico. Ambos quedaron sustituidos por la decisión registrada en la Sección 13: la vía vigente es el piloto local protegido definido en `docs/implementation/LOCAL_AUTOMATION_PILOT.md`, y B4a ya no depende de ninguna ejecución cloud.

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
- La PR #30, `docs: define B4 staged execution and cloud smoke test`, está abierta, es fusionable y su CI `Quality` terminó correctamente.
- La rutina de prueba de humo cloud fue creada y lanzada por el usuario.
- La rutina utilizó un disparador de **una sola ejecución programada**.
- No utilizó disparador API.
- No utilizó evento de GitHub.
- Los conectores estaban vacíos.
- La corrección automática de pull requests estaba desactivada.
- La notificación push estaba activada.
- **La prueba de humo cloud quedó cerrada en `BLOCKED_BY_ENVIRONMENT`** (decisión registrada el 18 de julio de 2026; detalle en `docs/implementation/CLOUD_SMOKE_TEST.md`). Este cierre no equivale a `CLOUD_SMOKE_PASSED`.
- No se realizarán más intentos cloud por ahora.
- La vía operativa activa es el piloto local semiautomático definido en `docs/implementation/LOCAL_AUTOMATION_PILOT.md`.
- B4a no ha comenzado y **no queda autorizado por este cambio de vía**.

### Próxima acción exacta

Ejecutar y evaluar el piloto local semiautomático conforme a `docs/implementation/LOCAL_AUTOMATION_PILOT.md`. No reabrir la vía cloud sin una nueva decisión explícita del usuario, no ampliar permisos y no comenzar B4a antes de cumplir la puerta explícita descrita en ese documento.

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

### Fase A - Prueba de humo cloud (CERRADA - `BLOCKED_BY_ENVIRONMENT`)

Objetivo: demostrar que Claude puede trabajar desde un clon limpio, instalar dependencias, ejecutar toda la validación, crear evidencia y preparar una PR sin depender del ordenador del usuario ni solicitar aprobaciones rutinarias.

Configuración aprobada:

- disparador: una sola vez;
- API: no;
- evento de GitHub: no;
- conectores: ninguno;
- auto-fix: desactivado;
- notificación push: activada;
- merge: prohibido.

Resultados posibles y acción prevista en su momento:

| Resultado | Acción |
|---|---|
| `CLOUD_SMOKE_PASSED` | Verificar evidencia y PR. Después se puede fusionar la PR #30 y preparar B4a. |
| `BLOCKED_BY_PERMISSION` | Corregir únicamente el permiso exacto que bloqueó la ejecución. No ampliar permisos de forma general. Repetir la prueba completa. |
| `BLOCKED_BY_ENVIRONMENT` | Corregir de forma reproducible el entorno cloud. Repetir la prueba completa. |
| `FAILED_SAFELY` | Diagnosticar la causa. No comenzar B4a. |
| `USAGE_LIMIT_REACHED` | Esperar la renovación de cuota. No rediseñar el flujo. |

**Cierre registrado (18 de julio de 2026):** el resultado real fue `BLOCKED_BY_ENVIRONMENT`. Por decisión del usuario, no se aplica la acción de "repetir la prueba completa": no se realizarán más intentos cloud por ahora. Esta fase queda cerrada como registro histórico; no se reabre sin una nueva decisión explícita del usuario. Ver `docs/implementation/CLOUD_SMOKE_TEST.md` para el detalle conservado.

### Fase A-bis - Piloto local semiautomático (fase actual)

Objetivo: mientras la vía cloud permanece cerrada, acumular evidencia auditable de que una sesión local, protegida por los permisos ya vigentes en `.claude/settings.json`, puede leer las fuentes obligatorias, ejecutar `scripts/check.ps1` y detenerse de forma segura, sin commit, push, PR, `gh` ni permisos nuevos.

Definición completa, alcance, prohibiciones, evidencia y estados finales: `docs/implementation/LOCAL_AUTOMATION_PILOT.md`.

Esta fase **no equivale** a la Fase B y no autoriza B4a por sí sola. La puerta explícita hacia B4a queda definida en `docs/implementation/LOCAL_AUTOMATION_PILOT.md`.

### Fase B - B4a mediante el flujo local protegido

Se abre únicamente cuando se cumpla la puerta explícita definida en `docs/implementation/LOCAL_AUTOMATION_PILOT.md`. No depende de una Routine ni de ninguna ejecución cloud: ninguna de las dos es obligatoria para abrir esta fase.

Cuando B4a quede autorizado, se ejecutará en local, con el ordenador del usuario encendido durante toda la ejecución, bajo un flujo protegido y auditable equivalente en disciplina al piloto descrito en `docs/implementation/LOCAL_AUTOMATION_PILOT.md` — sujeto a la definición de alcance y permisos específicos que exige la puerta de ese documento antes de tocar código de producto (el piloto de validación, por sí mismo, prohíbe modificar `src/`, `tests/` y `migrations/`, y B4a sí necesita hacerlo). No usará API ni evento de GitHub.

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

> **Nota (ver Sección 13):** la definición de "automatización real" fue ampliada por la decisión registrada en la Sección 13 para incluir también el flujo local protegido definido en `docs/implementation/LOCAL_AUTOMATION_PILOT.md`. La ejecución cloud descrita arriba ya no es un requisito vigente.

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

Al retomar este trabajo, la primera pregunta operativa no es "¿qué automatizamos ahora?". Es:

**¿Cuál es el estado real del piloto local semiautomático descrito en `docs/implementation/LOCAL_AUTOMATION_PILOT.md`, y se cumplió ya su puerta explícita antes de B4a?**

El resultado de la prueba de humo cloud ya se conoce (`BLOCKED_BY_ENVIRONMENT`, cerrada el 18 de julio de 2026) y no se reabre esa vía sin una nueva decisión explícita del usuario. Hasta conocer el estado del piloto local, la única acción válida es revisar su evidencia y su estado final declarado.

## 13. Registro de cambios del contrato

### Cambio 1 - 18 de julio de 2026

- **Decisión cambiada:** la Fase A (prueba de humo cloud) deja de ser la fase actual.
- **Motivo:** la prueba de humo cloud terminó en `BLOCKED_BY_ENVIRONMENT`; el usuario decidió no seguir intentando la vía cloud por ahora.
- **Sección que sustituye:** Sección 2 ("Estado actual verificado") y Sección 4 ("Fase A" y nueva "Fase A-bis").
- **Estado operativo actualizado:** la fase operativa actual pasa a ser el piloto local semiautomático, definido en `docs/implementation/LOCAL_AUTOMATION_PILOT.md`.
- **Aclaración expresa:** este cambio de vía no autoriza B4a. B4a sigue exigiendo la puerta explícita descrita en `docs/implementation/LOCAL_AUTOMATION_PILOT.md`.
- Este registro no reescribe lo ocurrido en la Fase A: su configuración, resultado y cierre se conservan tal como sucedieron en la Sección 4 y en `docs/implementation/CLOUD_SMOKE_TEST.md`.

### Cambio 2 - 18 de julio de 2026

- **Decisión cambiada:** la Fase B deja de depender de una Routine o de una ejecución cloud.
- **Nueva decisión vigente:** B4a, cuando quede autorizado, se ejecutará mediante el flujo local protegido.
- **Motivo:** instrucción explícita del usuario tras cerrar la vía cloud como `BLOCKED_BY_ENVIRONMENT`.
- **Secciones sustituidas o afectadas:** Fase B; Sección 9, "Error 1".
- **Aclaración:** B4a sigue sin iniciarse; este cambio no amplía permisos; la autorización de B4a sigue dependiendo de la puerta definida en `docs/implementation/LOCAL_AUTOMATION_PILOT.md`.
