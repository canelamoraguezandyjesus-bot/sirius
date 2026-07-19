# SIRIUS - Plan del flujo general de automatización

**Versión:** 0.1 propuesta
**Fecha:** 19 de julio de 2026
**Estado:** En definición
**Alcance:** Automatización general del desarrollo de Sirius 0.1

## 1. Objetivo

Permitir que el usuario inicie un bloque de trabajo con una instrucción breve y que el sistema avance de forma trazable hasta dejar una PR validada y revisada, reservando para el usuario únicamente las decisiones reales y la autorización final de merge.

Ejemplo de orden inicial:

> Empieza B4e.

## 2. Principio de diseño

El motor principal será GitHub por eventos. Las tareas programadas de ChatGPT no gobernarán el desarrollo ni comprobarán PR de forma horaria.

ChatGPT actuará como panel de mando para:

- iniciar trabajo;
- consultar estado;
- explicar bloqueos;
- registrar decisiones del usuario;
- autorizar el merge cuando corresponda.

Claude Code o la Routine implementadora ejecutará el trabajo técnico. Una Routine revisora independiente auditará la PR.

## 3. Flujo objetivo

### Paso 1 - Orden del usuario

El usuario da una instrucción breve para iniciar un bloque aprobado.

### Paso 2 - Preparación de la tarea

ChatGPT crea o completa una incidencia de trabajo con:

- objetivo;
- alcance permitido;
- fuera de alcance;
- requisitos y pruebas vinculadas;
- comandos de validación;
- condición de parada;
- estados finales permitidos;
- prohibición de merge automático.

La incidencia recibe una etiqueta de activación para el implementador.

### Paso 3 - Implementación

La Routine implementadora:

- crea una rama propia;
- implementa únicamente el bloque solicitado;
- añade o actualiza pruebas;
- ejecuta Ruff, mypy, pytest y las validaciones definidas;
- abre o actualiza una PR propia;
- se detiene sin hacer merge.

### Paso 4 - CI

GitHub Actions valida el head exacto de la PR.

- Si CI falla, se activa una corrección técnica acotada o se informa del fallo.
- Si CI queda verde y la PR está lista, se genera automáticamente la solicitud de revisión independiente.

### Paso 5 - Revisión independiente

La Routine revisora comprueba:

- cumplimiento del alcance;
- código y pruebas;
- compatibilidad con Producto y Arquitectura aprobados;
- migraciones y persistencia;
- seguridad y ausencia de ampliaciones no autorizadas.

En la primera pasada no modifica código.

### Paso 6 - Resultado de revisión

Resultados permitidos:

- `REVIEW_APPROVED`: PR técnicamente aprobada y lista para decisión humana de merge.
- `CHANGES_REQUESTED`: observaciones técnicas corregibles y estructuradas.
- `BLOCKED_BY_DECISION`: falta una decisión real de producto, arquitectura, seguridad o alcance.
- `FAILED_SAFELY`: fallo operativo no resoluble de forma segura.

### Paso 7 - Corrección automática limitada

Cuando el resultado sea `CHANGES_REQUESTED`, la Routine implementadora puede corregir únicamente las observaciones registradas en la misma rama y PR.

Después:

- CI vuelve a ejecutarse;
- la revisión vuelve a activarse al quedar verde;
- se permiten como máximo dos ciclos de revisión-corrección.

Si no converge en dos ciclos, el estado pasa a `BLOCKED_BY_DECISION`.

### Paso 8 - Merge humano

Cuando exista `REVIEW_APPROVED`, ChatGPT informa al usuario.

El merge solo se realiza tras una orden explícita, por ejemplo:

> Fusiona.

Antes del merge se verifica:

- PR abierta;
- CI verde;
- revisión aprobada;
- head sin cambios desde la aprobación;
- ausencia de bloqueos pendientes.

### Paso 9 - Cierre

Tras el merge:

- se actualiza el estado operativo;
- se cierra la incidencia del bloque;
- se registra la evidencia relevante;
- no se inicia el siguiente bloque salvo orden del usuario o cola previamente aprobada.

## 4. Qué queda automatizado

- creación y preparación de la tarea;
- rama y PR;
- implementación;
- pruebas y CI;
- solicitud de revisión;
- revisión independiente;
- correcciones técnicas acotadas;
- revalidación y segunda revisión;
- actualización de estado y notificación.

## 5. Intervención reservada al usuario

- decisiones reales de producto o arquitectura;
- ampliaciones de alcance;
- excepciones de seguridad;
- resolución de bloqueos no técnicos;
- autorización final de merge.

## 6. Prohibiciones vigentes

- merge automático;
- cambios directos en `main`;
- decisiones silenciosas de producto o arquitectura;
- bucles ilimitados de corrección;
- revisión automática en cada push sin condición;
- vigilancia horaria como motor del flujo;
- inicio indefinido de bloques sucesivos sin autorización.

## 7. Papel de las tareas programadas de ChatGPT

Solo se usarán como soporte opcional:

- resumen diario de trabajo activo;
- aviso de bloqueos prolongados;
- informe semanal;
- recordatorio de decisiones pendientes.

No sustituirán los eventos de GitHub ni gobernarán el ciclo técnico.

## 8. Implementación prevista por fases

### Fase 1 - Activación general de revisión

Automatizar el evento:

PR lista + CI verde -> solicitud de revisión independiente.

### Fase 2 - Corrección acotada

Automatizar:

`CHANGES_REQUESTED` -> corrección en la misma PR -> CI -> nueva revisión.

Límite: dos ciclos.

### Fase 3 - Panel de mando en ChatGPT

Permitir órdenes breves:

- `Empieza <bloque>`;
- `¿Qué está bloqueado?`;
- `Explícame la revisión`;
- `Acepto esta decisión`;
- `Fusiona`;
- `Siguiente`.

### Fase 4 - Aplicaciones de control

Evaluar una interfaz o aplicación desde la que una instrucción del usuario cree una tarea trazable en GitHub y active el mismo flujo, sin duplicar la lógica de automatización.

## 9. Primera acción de implementación

Definir y crear el disparador general que, para cualquier PR de Sirius 0.1, active la revisión cuando se cumplan simultáneamente estas condiciones:

1. PR abierta y no borrador;
2. CI `Quality` completado con éxito sobre el head actual;
3. etiqueta o estado que confirme que la implementación ha terminado;
4. no existe ya una revisión activa para ese mismo head;
5. el bloque pertenece al alcance aprobado;
6. el merge permanece desactivado.
