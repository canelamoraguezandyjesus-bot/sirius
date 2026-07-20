# SIRIUS - Máquina de estados del flujo automático

**Versión:** 0.2 propuesta  
**Fecha:** 19 de julio de 2026  
**Estado:** En definición  
**Alcance:** Orquestación automática por eventos para Sirius 0.1

## 1. Decisión de diseño

El usuario debe poder escribir una orden breve, por ejemplo:

> Implementa B4e.

ChatGPT convierte esa orden en una incidencia estructurada y aplica el evento inicial. Desde ese momento, GitHub Actions y las Routines hacen avanzar el trabajo por eventos.

La incidencia contiene el contrato completo. Las etiquetas representan estados o transiciones.

## 2. Componentes

### 2.1 ChatGPT como panel de mando

Responsabilidades:

- interpretar la orden breve;
- leer las fuentes aprobadas;
- crear la incidencia de trabajo;
- aplicar el evento inicial;
- consultar y explicar estados;
- registrar decisiones humanas.

Limitación operativa: ChatGPT no puede iniciar una conversación ni contactar al usuario por sí solo cuando el chat está inactivo.

El merge ya no lo ejecuta ChatGPT: lo ejecuta de forma nativa
`.github/workflows/merge-sirius-work.yml` en cuanto detecta el comentario
exacto del propietario en GitHub (véase §4.7). Esto evita depender de que el
usuario tenga abierto un chat para autorizar un merge ya decidido.

### 2.2 Incidencia de control

Cada bloque mantiene una única incidencia con:

- identificador y bloque;
- objetivo y alcance;
- fuera de alcance;
- requisitos y pruebas;
- rama, PR y head SHA;
- contador de correcciones;
- resultado actual;
- decisiones pendientes;
- merge automático desactivado.

### 2.3 Routines genéricas

- **Implementadora:** ejecuta cualquier incidencia válida.
- **Revisora:** audita cualquier PR vinculada sin modificar código en la primera pasada.
- **Correctora:** corrige exclusivamente observaciones estructuradas en la misma rama y PR.

### 2.4 GitHub Actions

Reacciona a:

- etiquetas añadidas;
- PR abierta o lista;
- CI completado;
- revisión publicada;
- merge realizado.

Solo valida condiciones y mueve estados. No decide producto ni arquitectura.

## 3. Etiquetas

### Estados persistentes

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

Los eventos se consumen al comenzar la Routine correspondiente.

## 4. Transiciones

### 4.1 Inicio

`planned -> implement-requested -> implementing`

La implementadora valida la incidencia y consume el evento antes de actuar.

### 4.2 Implementación terminada

`implementing -> ci-pending`

Debe registrar rama, PR y head SHA y detenerse sin merge.

### 4.3 Resultado de CI

Con el head registrado:

- éxito: `ci-pending -> review-requested`;
- fallo corregible: `ci-pending -> repair-requested`;
- fallo inseguro o no clasificable: `ci-pending -> failed-safely`.

### 4.4 Revisión

`review-requested -> reviewing`

La revisora publica uno de estos resultados:

- `REVIEW_APPROVED -> ready-for-merge`;
- `CHANGES_REQUESTED -> repair-requested`;
- `BLOCKED_BY_DECISION -> blocked-decision`;
- `FAILED_SAFELY -> failed-safely`.

### 4.5 Corrección

`repair-requested -> repairing -> ci-pending`

La correctora:

- exige observaciones concretas;
- corrige solo esas observaciones;
- no amplía alcance;
- incrementa el contador;
- registra el nuevo head;
- vuelve a CI.

Máximo dos ciclos. Si no converge:

`repairing -> blocked-decision`

### 4.6 Listo para merge

Cuando se alcanza `ready-for-merge`:

- la PR permanece abierta y sin fusionar;
- GitHub, la Routine o un canal expresamente configurado emite una notificación por evento;
- el sistema se detiene.

La notificación llega por GitHub (incidencia). El usuario no necesita abrir
ningún chat: puede autorizar el merge escribiendo el comentario exacto
`fusiona` directamente en la incidencia.

### 4.7 Merge y cierre

El merge se ejecuta mediante `.github/workflows/merge-sirius-work.yml`,
disparado por un comentario del propietario del repositorio (verificado por
`author_association == OWNER`) que contenga exactamente la palabra `fusiona`
sobre una incidencia en `sirius:ready-for-merge`. Antes de fusionar, el
workflow verifica por REST:

- que el comentario proviene del propietario y la incidencia sigue en
  `sirius:ready-for-merge`;
- que existe una única PR asociada;
- que esa PR está abierta, no es borrador, no está ya fusionada y no tiene
  conflictos con la rama base;
- que su head actual coincide con el último Head/Merge SHA aprobado
  registrado en la incidencia (ningún cambio posterior sin revisar);
- que `Quality` está en verde sobre ese head exacto.

Si cualquier condición falla, publica una explicación concreta en la
incidencia y no fusiona. La autorización para ese merge concreto sigue siendo
del usuario; el workflow solo ejecuta un merge ya autorizado.

Tras el merge:

`ready-for-merge -> completed`

Lo aplica `complete-sirius-after-merge.yml` al recibir el evento de PR
fusionada; registra el commit y cierra la incidencia.

## 5. Idempotencia y bloqueo de duplicados

Toda transición comprueba:

- identificador único;
- estado de origen permitido;
- head SHA esperado;
- ausencia de ejecución activa equivalente;
- evento no consumido;
- contador de ciclos.

Los webhooks repetidos no pueden crear duplicados de ramas, PR, revisiones o correcciones.

## 6. Formato de cambios solicitados

Cada observación corregible incluirá:

- identificador;
- severidad;
- archivo o componente;
- problema;
- criterio esperado;
- prueba que demuestra el fallo;
- límites de la corrección.

La correctora rechazará instrucciones vagas como `mejorar el código`.

## 7. Control humano

Permanecen bajo control humano:

- producto y arquitectura;
- ampliaciones de alcance;
- excepciones de seguridad;
- contradicciones canónicas;
- autorización final de merge.

## 8. Prohibiciones

- tareas horarias como motor;
- vigilancia periódica de PR;
- fusionar sin el comentario explícito de autorización del propietario descrito en §4.7;
- cambios directos en `main`;
- bucles ilimitados;
- inicio automático indefinido de bloques.

## 9. Orden de construcción

1. Etiquetas.
2. Plantilla universal de incidencia.
3. Routine implementadora.
4. Evento `CI verde -> review-requested`.
5. Routine revisora.
6. Routine correctora.
7. Contador e idempotencia.
8. Notificación por evento.
9. Cierre tras merge.
10. Prueba integral con un bloque acotado.
