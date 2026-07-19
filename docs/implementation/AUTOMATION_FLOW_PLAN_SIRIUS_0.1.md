# SIRIUS - Plan del flujo general de automatización

**Versión:** 0.2 propuesta  
**Fecha:** 19 de julio de 2026  
**Estado:** En definición  
**Alcance:** Automatización general del desarrollo de Sirius 0.1

## 1. Objetivo

Permitir que el usuario inicie un bloque con una orden breve, por ejemplo `Implementa B4e`, y que el sistema avance por eventos de GitHub hasta dejar una PR validada, revisada y preparada para merge.

El usuario solo interviene para:

- decisiones reales de producto, arquitectura o seguridad;
- ampliaciones de alcance;
- autorización final de merge.

## 2. Principio de diseño

GitHub y las Routines gobiernan el ciclo mediante eventos. No se utilizarán comprobaciones horarias ni tareas programadas de ChatGPT como motor técnico.

ChatGPT actúa como panel de mando cuando el usuario abre el chat:

- interpreta órdenes breves;
- crea la incidencia de trabajo;
- consulta y explica el estado;
- registra decisiones;
- ejecuta el merge tras autorización explícita.

ChatGPT no puede iniciar una conversación ni avisar por sí solo cuando el usuario no está presente. Las notificaciones de estados terminales o bloqueos deben generarse mediante GitHub, la Routine o un canal de notificación configurado expresamente.

## 3. Fuente de verdad

Cada bloque tendrá una incidencia de control que contendrá:

- identificador y bloque;
- objetivo;
- alcance permitido y fuera de alcance;
- requisitos y pruebas;
- validaciones obligatorias;
- rama, PR y head SHA;
- contador de correcciones;
- resultado vigente;
- decisiones pendientes;
- prohibición de merge automático.

Las etiquetas solo representan estados o eventos. No contienen el prompt ni el contrato de trabajo.

## 4. Flujo objetivo

### 4.1 Inicio

1. El usuario escribe `Implementa <bloque>`.
2. ChatGPT crea la incidencia estructurada.
3. ChatGPT aplica `sirius:implement-requested`.
4. La Routine implementadora consume el evento y aplica `sirius:implementing`.

### 4.2 Implementación

La Routine implementadora genérica:

- crea una rama propia;
- implementa solo el alcance autorizado;
- añade o actualiza pruebas;
- ejecuta Ruff, mypy, pytest y validaciones adicionales;
- abre o actualiza la PR;
- registra rama, PR y head SHA;
- pasa a `sirius:ci-pending`;
- se detiene sin merge.

### 4.3 CI

GitHub Actions valida el head exacto.

- CI verde: genera `sirius:review-requested`.
- Fallo técnicamente corregible: genera `sirius:repair-requested` con diagnóstico estructurado.
- Fallo no corregible de forma segura: aplica `sirius:failed-safely`.

### 4.4 Revisión

La Routine revisora independiente:

- consume `sirius:review-requested`;
- aplica `sirius:reviewing`;
- verifica el head SHA;
- revisa alcance, código, pruebas, arquitectura, persistencia y seguridad;
- publica uno de estos resultados:
  - `REVIEW_APPROVED`;
  - `CHANGES_REQUESTED`;
  - `BLOCKED_BY_DECISION`;
  - `FAILED_SAFELY`.

### 4.5 Corrección automática limitada

Cuando exista `CHANGES_REQUESTED`, la Routine correctora:

- consume `sirius:repair-requested`;
- corrige únicamente observaciones concretas;
- trabaja en la misma rama y PR;
- incrementa el contador;
- ejecuta validaciones;
- registra el nuevo head;
- vuelve a `sirius:ci-pending`.

Se permiten como máximo dos ciclos. Si no converge, pasa a `sirius:blocked-decision`.

### 4.6 Aprobación y notificación

Cuando la revisión aprueba el head exacto:

- se aplica `sirius:ready-for-merge`;
- GitHub, la Routine o el canal configurado emite la notificación;
- el sistema queda detenido sin fusionar.

ChatGPT no promete iniciar el aviso. Cuando el usuario vuelva al chat o responda a la notificación, puede consultar el estado y ordenar `Fusiona`.

### 4.7 Merge humano

Antes del merge se verifica:

- PR abierta;
- CI verde sobre el head actual;
- `REVIEW_APPROVED` para el mismo head;
- ausencia de bloqueos;
- ausencia de cambios posteriores a la aprobación.

El merge solo se ejecuta tras orden explícita del usuario.

### 4.8 Cierre

Tras el merge:

- se aplica `sirius:completed`;
- se registra el commit de merge;
- se cierra la incidencia;
- no se inicia otro bloque sin orden o cola aprobada.

## 5. Protección contra duplicados

Todas las transiciones serán idempotentes. Antes de actuar se comprobará:

- identificador único;
- estado permitido;
- head esperado;
- ausencia de ejecución activa equivalente;
- evento no consumido;
- contador de ciclos.

Los reintentos de webhooks no deben duplicar ramas, PR, revisiones ni correcciones.

## 6. Prohibiciones

- merge automático;
- cambios directos en `main`;
- decisiones silenciosas de producto o arquitectura;
- correcciones ilimitadas;
- revisión en cada push sin condiciones;
- vigilancia horaria como motor;
- inicio indefinido de bloques sin autorización.

## 7. Tareas programadas de ChatGPT

Solo podrán utilizarse como soporte opcional para resúmenes o recordatorios. No sustituyen los eventos de GitHub y no se usarán para vigilar PR periódicamente.

## 8. Orden de implementación

1. Crear etiquetas y semántica.
2. Definir plantilla universal de incidencia.
3. Generalizar Routine implementadora.
4. Automatizar `CI verde -> review-requested`.
5. Generalizar Routine revisora.
6. Crear Routine correctora.
7. Implementar contador e idempotencia.
8. Configurar notificación por evento.
9. Automatizar cierre tras merge.
10. Probar el flujo completo con un bloque acotado.
