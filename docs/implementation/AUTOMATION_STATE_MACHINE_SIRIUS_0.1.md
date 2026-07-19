# SIRIUS - Máquina de estados del flujo automático

**Versión:** 0.1 propuesta  
**Fecha:** 19 de julio de 2026  
**Estado:** En definición  
**Alcance:** Orquestación automática por eventos para Sirius 0.1

## 1. Decisión de diseño

El usuario debe poder escribir únicamente una orden breve, por ejemplo:

> Implementa B4e.

ChatGPT transforma esa orden en una incidencia de trabajo estructurada en GitHub y aplica una etiqueta de activación. Desde ese momento, el flujo avanza por eventos de GitHub sin copiar ni pegar prompts manualmente.

Las etiquetas no contienen el trabajo. La incidencia contiene el contrato completo de ejecución. Las etiquetas solo representan estados o transiciones.

## 2. Componentes

### 2.1 ChatGPT como panel de mando

Responsabilidades:

- interpretar la orden breve del usuario;
- leer Producto, Arquitectura, ATD y estado vigente;
- crear la incidencia de trabajo con objetivo, alcance, prohibiciones, requisitos, pruebas y condición de parada;
- aplicar la etiqueta inicial;
- explicar bloqueos;
- registrar decisiones humanas;
- ejecutar el merge solo tras autorización explícita.

ChatGPT no vigila por horas ni gobierna el ciclo mediante tareas programadas.

### 2.2 Incidencia de trabajo como fuente de verdad

Cada bloque utiliza una única incidencia de control con:

- identificador del trabajo;
- bloque solicitado;
- objetivo;
- alcance permitido;
- fuera de alcance;
- requisitos y pruebas vinculadas;
- validaciones obligatorias;
- rama y PR asociadas;
- head SHA vigente;
- número de ciclo de corrección;
- resultado actual;
- decisiones pendientes;
- prohibición de merge automático.

### 2.3 Routine implementadora genérica

Una sola Routine implementadora sirve para cualquier bloque. No contiene instrucciones específicas de B4e, B4f u otra vertical. Lee la incidencia activadora y ejecuta únicamente el contrato allí definido.

### 2.4 Routine revisora genérica

Una sola Routine revisora audita cualquier PR vinculada a una incidencia válida. Revisa el head exacto, el alcance, las pruebas, la arquitectura y la seguridad. En la primera pasada no corrige código.

### 2.5 Routine correctora genérica

Una sola Routine correctora recibe observaciones estructuradas, corrige exclusivamente esas observaciones en la misma rama y PR, ejecuta validaciones y devuelve el trabajo al ciclo de CI y revisión.

### 2.6 GitHub Actions como orquestador determinista

GitHub Actions reacciona a eventos objetivos:

- etiqueta añadida;
- PR abierta o marcada como lista;
- CI completado;
- revisión publicada;
- merge realizado.

No toma decisiones de producto. Solo valida condiciones y mueve el trabajo al siguiente estado.

## 3. Etiquetas propuestas

### Estados estables

- `sirius:planned`
- `sirius:implementing`
- `sirius:ci-pending`
- `sirius:reviewing`
- `sirius:repairing`
- `sirius:ready-for-merge`
- `sirius:blocked-decision`
- `sirius:failed-safely`
- `sirius:completed`

### Eventos consumibles

- `sirius:implement-requested`
- `sirius:review-requested`
- `sirius:repair-requested`

Las etiquetas de evento se consumen al comenzar la Routine correspondiente. No deben permanecer como estado permanente.

## 4. Flujo completo

### 4.1 Inicio

1. El usuario escribe `Implementa <bloque>`.
2. ChatGPT crea la incidencia estructurada.
3. ChatGPT aplica `sirius:implement-requested`.
4. La Routine implementadora valida la incidencia, consume la etiqueta de evento y aplica `sirius:implementing`.

### 4.2 Implementación

La Routine implementadora:

- crea una rama propia desde la base registrada;
- implementa solo el alcance autorizado;
- añade o actualiza pruebas;
- ejecuta Ruff, mypy, pytest y validaciones adicionales;
- abre o actualiza una PR;
- registra PR, rama y head SHA en la incidencia;
- sustituye `sirius:implementing` por `sirius:ci-pending`;
- se detiene sin merge.

### 4.3 CI

Cuando `Quality` termina sobre el head registrado:

- si pasa, GitHub elimina `sirius:ci-pending` y añade `sirius:review-requested`;
- si falla y el fallo es técnicamente corregible, añade `sirius:repair-requested` con el diagnóstico estructurado;
- si el fallo no es seguro de corregir automáticamente, aplica `sirius:failed-safely`.

### 4.4 Revisión

La Routine revisora:

- consume `sirius:review-requested`;
- aplica `sirius:reviewing`;
- verifica que el head SHA coincide con el CI aprobado;
- audita el diff completo, pruebas, alcance, persistencia, migraciones, seguridad y arquitectura;
- publica uno de los resultados permitidos.

Resultados:

- `REVIEW_APPROVED` -> `sirius:ready-for-merge`;
- `CHANGES_REQUESTED` -> `sirius:repair-requested`;
- `BLOCKED_BY_DECISION` -> `sirius:blocked-decision`;
- `FAILED_SAFELY` -> `sirius:failed-safely`.

### 4.5 Corrección

La Routine correctora:

- consume `sirius:repair-requested`;
- valida que existen observaciones concretas y un ciclo disponible;
- aplica `sirius:repairing`;
- corrige exclusivamente esas observaciones;
- no amplía alcance ni reescribe requisitos;
- incrementa el contador de ciclo;
- ejecuta validaciones;
- registra el nuevo head SHA;
- vuelve a `sirius:ci-pending`.

Tras CI verde, el flujo vuelve automáticamente a revisión.

### 4.6 Límite del ciclo

Se permiten como máximo dos ciclos de revisión-corrección.

Si el segundo ciclo no converge:

- se elimina cualquier evento de corrección pendiente;
- se aplica `sirius:blocked-decision`;
- se informa al usuario con el problema exacto;
- no se realizan más cambios automáticos.

### 4.7 Merge

Cuando la incidencia tenga `sirius:ready-for-merge`, ChatGPT informa al usuario.

El merge requiere una orden explícita como:

> Fusiona.

Antes de ejecutar el merge, ChatGPT verifica:

- PR abierta;
- CI verde sobre el head actual;
- `REVIEW_APPROVED` para ese mismo head;
- ausencia de bloqueos;
- ausencia de cambios posteriores a la aprobación.

Tras el merge:

- la incidencia pasa a `sirius:completed`;
- se registra el commit de merge;
- se cierra la incidencia;
- no se inicia el siguiente bloque salvo orden del usuario o cola aprobada.

## 5. Protección contra duplicados y bucles

Cada transición debe ser idempotente.

Antes de actuar, toda Routine comprueba:

- identificador único de trabajo;
- estado actual permitido;
- head SHA esperado;
- que no exista otra ejecución activa para el mismo trabajo y estado;
- que la etiqueta de evento no haya sido ya consumida;
- contador de ciclos.

Los eventos repetidos o webhooks reintentados no deben duplicar ramas, PR, revisiones ni correcciones.

## 6. Formato de observaciones corregibles

`CHANGES_REQUESTED` debe publicar observaciones estructuradas con:

- identificador;
- severidad;
- archivo o componente;
- problema observado;
- criterio esperado;
- prueba que demuestra el fallo;
- límites de la corrección.

La Routine correctora no acepta instrucciones vagas como `mejorar el código` o `revisar todo`.

## 7. Qué puede automatizarse

Puede automatizarse:

- creación de la incidencia desde una orden breve;
- activación del implementador;
- creación de rama y PR;
- CI;
- activación de revisión;
- revisión independiente;
- correcciones técnicas acotadas;
- repetición de CI y revisión;
- actualización de estados;
- aviso de listo para merge;
- cierre posterior al merge.

## 8. Qué permanece bajo control humano

Permanece bajo control humano:

- decisiones de producto o arquitectura;
- ampliaciones de alcance;
- excepciones de seguridad;
- resolución de contradicciones canónicas;
- autorización final de merge.

## 9. Qué no se utilizará como motor

No se utilizarán tareas horarias o vigilancia periódica como motor del flujo.

Las tareas programadas de ChatGPT podrán usarse únicamente para resúmenes o recordatorios opcionales. La ejecución técnica se activa mediante eventos de GitHub.

## 10. Orden de implementación

1. Crear las etiquetas y su semántica.
2. Definir la plantilla estructurada de incidencia de trabajo.
3. Generalizar la Routine implementadora.
4. Automatizar `CI verde -> review-requested`.
5. Generalizar la Routine revisora.
6. Crear la Routine correctora.
7. Implementar contador de ciclos e idempotencia.
8. Automatizar el cierre tras merge.
9. Probar el flujo completo con un bloque acotado antes de usarlo de forma general.
