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
- B4a no ha comenzado.

### Próxima acción exacta

La Fase A quedó superada con `CLOUD_SMOKE_PASSED`. La Fase B queda preparada para iniciar B4a mediante una Routine cloud controlada, con disparador de una sola vez, sin API ni evento de GitHub. B4a todavía no ha comenzado; no se inicia automáticamente por este documento.

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

Al retomar este trabajo, la primera pregunta operativa no es "¿qué automatizamos ahora?". Es:

**¿B4a ya se inició en cloud controlado, o sigue preparado y pendiente de arranque?**

Mientras B4a no haya comenzado, la única acción válida es prepararlo conforme a la Fase B, sin adelantar API, eventos de GitHub, auto-fix ni merge automático.
