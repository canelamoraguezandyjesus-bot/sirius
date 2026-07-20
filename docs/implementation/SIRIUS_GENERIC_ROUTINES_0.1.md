# SIRIUS — Routines genéricas de automatización 0.1

**Versión:** 0.1 propuesta  
**Fecha:** 19 de julio de 2026  
**Estado:** Operativa tras merge de la PR de automatización y registro único de las Routines

## 0. E/S robusta de incidencias (obligatoria)

La incidencia #55 demostró que depender de una sola vía de lectura (GraphQL/MCP)
es frágil: un 502/503 o un cuerpo truncado pueden abortar una Routine o, peor,
provocar una escritura parcial que corrompa el cuerpo. Para evitarlo existe la
biblioteca **`scripts/automation/sirius_issue.sh`** y el validador
**`scripts/automation/validate_issue_body.py`**. Ninguna Routine ni workflow debe
leer o escribir incidencias por una sola vía sin las siguientes garantías:

- **Lectura:** vía principal GitHub REST (`gh api`) con reintentos limitados y
  espera creciente; ante fallo, respaldo independiente por GraphQL
  (`gh issue view`). Funciones: `sirius_read_issue_body`,
  `sirius_read_issue_comments`.
- **Validación estructural:** un contrato de trabajo solo se acepta si contiene
  todas las secciones obligatorias (Work ID, Bloque, Objetivo, Base y
  dependencias, Alcance permitido, Fuera de alcance, Requisitos y pruebas,
  Validaciones, Rama base, Condiciones de parada, Salvaguardas). Una respuesta
  truncada nunca se acepta como cuerpo completo. Función:
  `sirius_read_workitem_body` (lee de forma robusta y valida antes de devolver).
- **Escritura verificada:** el cuerpo se construye primero en un archivo, se
  guarda una copia recuperable del cuerpo anterior, se escribe de una sola vez
  por REST y se vuelve a leer; si la longitud y el hash del contenido almacenado
  no coinciden con lo preparado, la escritura se considera fallida. Nunca se
  sobrescribe una incidencia usando como fuente un cuerpo truncado. Función:
  `sirius_write_issue_body`.
- **Parada segura:** `FAILED_SAFELY` solo se aplica cuando han fallado todas las
  vías permitidas, no existe una fuente local aprobada suficiente y continuar
  podría producir un cambio incorrecto. Un error temporal de una sola API no
  provoca `FAILED_SAFELY` de inmediato si otra vía autoritativa puede completar
  la lectura.

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

El workflow `.github/workflows/notify-sirius-state.yml` publica una notificación
de GitHub, en español y comprensible, mencionando **una sola vez** al propietario
(sin autoasignación) cuando aparece cualquiera de estos estados:

- `sirius:implementing` — 🟦 inicio del trabajo;
- `sirius:repair-requested` — 🟠 problema corregible, reparación automática;
- `sirius:ready-for-merge` — 🟢 listo, requiere autorización de merge;
- `sirius:blocked-decision` — 🟡 requiere una decisión humana;
- `sirius:failed-safely` — 🔴 parada segura, requiere revisión;
- `sirius:completed` — ✅ bloque integrado.

Los estados internos (`sirius:planned`, `sirius:ci-pending`,
`sirius:review-requested`, `sirius:reviewing`, `sirius:repairing`) no notifican.

La notificación es secundaria y nunca rompe el flujo principal: ante un fallo de
lectura o publicación deja un aviso en los logs y termina con éxito. Es
idempotente por incidencia, estado y head SHA (usa `no-head` como identificador
estable cuando todavía no hay SHA registrado).

## 6. Registro único pendiente fuera del repositorio

GitHub contiene el contrato, estados y disparadores. Para ejecutar Claude Code en respuesta a las tres etiquetas es necesario registrar una sola vez estas tres Routines en la interfaz de Claude/Routines y asociar cada una a su etiqueta correspondiente.

Después de ese registro no se crean Routines por bloque y el usuario no copia prompts: ChatGPT crea la incidencia y aplica `sirius:implement-requested`.
