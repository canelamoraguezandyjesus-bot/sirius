# SIRIUS — Routines genéricas de automatización 0.1

**Versión:** 0.1 propuesta  
**Fecha:** 19 de julio de 2026  
**Estado:** Operativa tras merge de la PR de automatización y registro único de las Routines

## 1. Regla común

Las tres Routines leen una incidencia creada con `.github/ISSUE_TEMPLATE/sirius-work-item.yml`. La incidencia es la fuente de verdad. Las etiquetas solo activan transiciones.

Comprobaciones obligatorias antes de actuar:

- `work_id` presente y único;
- estado de entrada permitido;
- rama base y alcance definidos;
- PR y head SHA coherentes cuando existan;
- ninguna ejecución equivalente activa;
- máximo de dos ciclos de corrección;
- merge automático prohibido.

Toda ejecución registra en la incidencia:

- Routine y ejecución;
- estado inicial;
- head inicial y final;
- comandos ejecutados;
- resultado terminal;
- diagnóstico o evidencia.

## 2. Routine implementadora genérica

**Nombre recomendado:** `Sirius Generic Implementer`  
**Disparador:** incidencia etiquetada `sirius:implement-requested`.

### Entrada válida

- incidencia abierta y conforme a la plantilla;
- estado `sirius:planned`;
- sin rama o PR activa para el mismo `work_id`;
- alcance previamente aprobado.

### Ejecución

1. Consume `sirius:implement-requested`.
2. Sustituye `sirius:planned` por `sirius:implementing`.
3. Crea una rama desde la base registrada.
4. Implementa únicamente el contrato de la incidencia.
5. Añade o actualiza pruebas.
6. Ejecuta todas las validaciones obligatorias.
7. Crea o actualiza una única PR.
8. Registra rama, PR y head SHA en la incidencia.
9. Aplica `sirius:ci-pending` y retira `sirius:implementing`.
10. Se detiene sin merge.

### Salidas permitidas

- `READY_FOR_REVIEW` → `sirius:ci-pending`;
- `BLOCKED_BY_DECISION` → `sirius:blocked-decision`;
- `FAILED_SAFELY` → `sirius:failed-safely`;
- `USAGE_LIMIT_REACHED` → `sirius:failed-safely` con diagnóstico específico.

## 3. Routine revisora genérica

**Nombre recomendado:** `Sirius Generic Reviewer`  
**Disparador:** incidencia etiquetada `sirius:review-requested`.

### Entrada válida

- incidencia y PR abiertas;
- PR no borrador;
- head SHA de la incidencia igual al head actual de la PR;
- `Quality` verde para ese head;
- sin revisión activa o completada para el mismo head.

### Ejecución

1. Consume `sirius:review-requested`.
2. Aplica `sirius:reviewing`.
3. Audita diff, código, pruebas, migraciones, persistencia, seguridad y alcance.
4. En la primera pasada no modifica código.
5. Publica un veredicto estructurado ligado al head exacto.

### Salidas permitidas

- `REVIEW_APPROVED` → retira `sirius:reviewing` y aplica `sirius:ready-for-merge`;
- `CHANGES_REQUESTED` → registra observaciones concretas, retira `sirius:reviewing` y aplica `sirius:repair-requested`;
- `BLOCKED_BY_DECISION` → `sirius:blocked-decision`;
- `FAILED_SAFELY` → `sirius:failed-safely`.

Cada observación corregible incluye identificador, severidad, archivo o componente, problema, criterio esperado, prueba y límites de corrección.

## 4. Routine correctora genérica

**Nombre recomendado:** `Sirius Generic Corrector`  
**Disparador:** incidencia etiquetada `sirius:repair-requested`.

### Entrada válida

- observaciones estructuradas existentes;
- rama y PR registradas y abiertas;
- head SHA vigente;
- contador de ciclos inferior a dos;
- ningún cambio de producto, arquitectura, seguridad no definida o alcance requerido.

### Ejecución

1. Consume `sirius:repair-requested`.
2. Aplica `sirius:repairing`.
3. Corrige exclusivamente las observaciones registradas.
4. Trabaja en la misma rama y PR.
5. Ejecuta todas las validaciones obligatorias.
6. Incrementa el contador de ciclo.
7. Registra el nuevo head SHA.
8. Retira `sirius:repairing` y aplica `sirius:ci-pending`.
9. Se detiene sin merge.

### Salidas permitidas

- corrección completada → `sirius:ci-pending`;
- decisión real necesaria → `sirius:blocked-decision`;
- fallo no corregible de forma segura → `sirius:failed-safely`.

Tras dos ciclos sin convergencia se elimina cualquier evento de reparación y se aplica `sirius:blocked-decision`.

## 5. Notificación al usuario

El workflow `.github/workflows/notify-sirius-state.yml` genera una notificación de GitHub al propietario cuando aparece cualquiera de estos estados:

- `sirius:ready-for-merge`;
- `sirius:blocked-decision`;
- `sirius:failed-safely`;
- `sirius:completed`.

La notificación es idempotente por incidencia, estado y head SHA.

## 6. Registro único pendiente fuera del repositorio

GitHub contiene el contrato, estados y disparadores. Para ejecutar Claude Code en respuesta a las tres etiquetas es necesario registrar una sola vez estas tres Routines en la interfaz de Claude/Routines y asociar cada una a su etiqueta correspondiente.

Después de ese registro no se crean Routines por bloque y el usuario no copia prompts: ChatGPT crea la incidencia y aplica `sirius:implement-requested`.
