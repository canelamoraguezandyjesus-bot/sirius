# SIRIUS - Contrato operativo de automatización

**Versión:** 1.1  
**Fecha:** 19 de julio de 2026  
**Estado:** PROPUESTO EN PR #44; VIGENTE ÚNICAMENTE TRAS MERGE HUMANO  
**Autoridad:** Operativa para el desarrollo automatizado de Sirius 0.1  
**Sustituye:** versión 1.0 del 18 de julio de 2026  
**No modifica:** Producto, Arquitectura Técnica, ATD, requisitos ni alcance de Sirius 0.1

## 0. Propósito

Este contrato autoriza y regula un flujo permanente, secuencial y dirigido por eventos para Sirius 0.1 mediante Claude Code/Routines, GitHub y ChatGPT con conectores.

Su finalidad es que el usuario pueda escribir una orden breve, por ejemplo `Implementa B4e`, y que el sistema prepare la tarea, implemente, valide, revise, corrija de forma limitada y notifique el resultado sin copiar ni pegar prompts manualmente.

La automatización no convierte a ningún agente en autoridad de producto o arquitectura y no autoriza merge automático.

## 1. Decisión operativa

Tras el merge humano de la PR #44 queda autorizada, para todo Sirius 0.1, la automatización secuencial de:

1. creación de una incidencia de trabajo estructurada;
2. implementación en rama propia;
3. ejecución de pruebas y CI;
4. revisión independiente;
5. corrección automática limitada;
6. repetición de CI y revisión;
7. notificación del resultado al usuario;
8. cierre posterior al merge humano.

No será necesaria una autorización administrativa distinta para cada subbloque. Cada tarea deberá permanecer dentro del alcance ya aprobado.

## 2. Fuente de verdad y disparadores

La incidencia de trabajo es la fuente de verdad de cada bloque. Debe contener como mínimo:

- identificador y bloque;
- objetivo;
- alcance permitido y fuera de alcance;
- requisitos y pruebas vinculadas;
- comandos de validación;
- rama y PR asociadas;
- head SHA vigente;
- contador de correcciones;
- resultado actual;
- decisiones pendientes;
- prohibición de merge automático.

Las etiquetas representan estados o transiciones; no contienen el prompt completo.

Eventos consumibles:

- `sirius:implement-requested`
- `sirius:review-requested`
- `sirius:repair-requested`

Estados persistentes:

- `sirius:planned`
- `sirius:implementing`
- `sirius:ci-pending`
- `sirius:reviewing`
- `sirius:repairing`
- `sirius:ready-for-merge`
- `sirius:blocked-decision`
- `sirius:failed-safely`
- `sirius:completed`

## 3. Implementación

La Routine implementadora genérica puede:

- crear una rama desde la base registrada;
- modificar código, pruebas y documentación de implementación dentro del alcance;
- ejecutar Ruff, mypy, pytest y validaciones existentes;
- realizar commits y push en la rama de trabajo;
- abrir o actualizar una PR;
- registrar rama, PR y head SHA en la incidencia.

Debe detenerse sin merge y dejar el trabajo en `sirius:ci-pending`, `sirius:blocked-decision` o `sirius:failed-safely`.

## 4. CI y revisión

Cuando `Quality` termine sobre el head registrado:

- si pasa, se solicita automáticamente revisión independiente;
- si falla por una causa técnica concreta y segura, se solicita corrección;
- si no es seguro corregir automáticamente, se detiene en `sirius:failed-safely`.

La Routine revisora debe ser independiente de la implementación y revisar el head exacto aprobado por CI.

Resultados permitidos:

- `REVIEW_APPROVED` -> `sirius:ready-for-merge`
- `CHANGES_REQUESTED` -> `sirius:repair-requested`
- `BLOCKED_BY_DECISION` -> `sirius:blocked-decision`
- `FAILED_SAFELY` -> `sirius:failed-safely`

## 5. Corrección automática limitada

La Routine correctora solo puede resolver observaciones técnicas concretas y estructuradas en la misma rama y PR.

Puede corregir defectos de implementación, pruebas insuficientes, lint, tipos, imports, errores deterministas de CI y migraciones aditivas o reversibles dentro del diseño aprobado.

Debe detenerse ante cambios de producto, arquitectura, ATD, seguridad no definida, migraciones destructivas, pérdida de datos, nuevos costes, credenciales reales o datos personales.

Se permiten como máximo dos ciclos de revisión-corrección. Si no converge, el estado final es `sirius:blocked-decision`.

## 6. Idempotencia y protección contra bucles

Cada transición debe comprobar:

- identificador único de trabajo;
- estado actual permitido;
- head SHA esperado;
- ausencia de otra ejecución activa para el mismo trabajo y estado;
- que la etiqueta de evento no haya sido consumida;
- contador de ciclos.

Los webhooks repetidos no deben duplicar ramas, PR, revisiones, correcciones ni notificaciones.

## 7. Notificaciones

ChatGPT no puede iniciar una conversación ni avisar por sí solo cuando termina una ejecución.

El canal operativo será GitHub. Al alcanzar cualquiera de estos estados, una automatización deberá asignar o mencionar al usuario en la incidencia y generar una notificación compatible con GitHub Mobile:

- `sirius:ready-for-merge`
- `sirius:blocked-decision`
- `sirius:failed-safely`
- `sirius:completed`

La notificación deberá incluir bloque, estado, PR, head SHA y siguiente acción humana. Debe emitirse una sola vez por combinación incidencia-estado-head.

## 8. Merge

El merge permanece bajo control humano.

Ningún agente, Routine, workflow o aplicación puede fusionar una PR sin una autorización explícita del usuario para ese merge.

Antes de fusionar se verificará:

- PR abierta y fusionable;
- CI verde sobre el head actual;
- revisión aprobada sobre ese mismo head;
- ausencia de bloqueos;
- ausencia de cambios posteriores a la aprobación.

## 9. Prohibiciones

Está prohibido:

- push directo a `main`;
- merge automático;
- reducir o falsear pruebas para conseguir verde;
- ocultar fallos;
- introducir servicios de pago, APIs, claves o suscripciones no aprobadas;
- usar secretos reales o datos personales en pruebas automáticas;
- cambiar Producto, Arquitectura Técnica, ATD o documentos canónicos sin decisión explícita;
- convertir una idea exploratoria en una decisión aprobada;
- usar vigilancia horaria como motor del flujo;
- iniciar bloques sucesivos sin orden del usuario o cola expresamente aprobada.

## 10. Entrada en vigor y cambio registrado

- **Decisión:** sustituir autorizaciones puntuales por subbloque por una autorización general de implementación, revisión y corrección automática limitada para Sirius 0.1.
- **Motivo:** eliminar trabajo manual repetitivo y permitir que el usuario solo intervenga ante decisiones reales y merge.
- **Alcance:** B4d, B4e, B4f y verticales posteriores de Sirius 0.1 dentro del alcance aprobado.
- **Mantiene:** revisión independiente, máximo de dos ciclos, trazabilidad, seguridad y merge humano.
- **Entrada en vigor:** únicamente cuando la PR #44 sea revisada, tenga CI verde y sea fusionada por autorización explícita del usuario.

El historial de la versión 1.0 permanece disponible en Git y no se reescribe retrospectivamente.
