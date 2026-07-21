# SIRIUS — Routines genéricas de automatización 0.1

**Versión:** 0.2  
**Fecha:** 20 de julio de 2026  
**Estado:** Operativa tras fusionar esta versión y configurar el secreto de autenticación de Claude Code descrito en §6.

Nota sobre el nombre: "Routine" aquí es solo la etiqueta que ya tenían estos
tres roles (implementadora, revisora, correctora) desde la versión 0.1 de
este documento. Deja de referirse a una interfaz externa de Claude
("Routines" como producto, no inspeccionable desde el repositorio): desde la
versión 0.2, los tres roles se ejecutan como Claude Code real, dentro de
GitHub Actions, con todo su mecanismo dentro de este repositorio.

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

### Puerta de activación en el repositorio

El workflow `.github/workflows/validate-sirius-activation.yml` valida cada
activación en cuanto se aplica `sirius:implement-requested` (incidencia #60):
incidencia abierta, `sirius:planned` presente, sin otros estados `sirius:`
activos o terminales, y cuerpo estructuralmente completo. Si la activación es
inválida, **rechaza temprano**: retira el evento, conserva el resto de
etiquetas y publica un comentario con el motivo exacto (marcador idempotente
por motivo) mencionando al propietario. Nunca añade `sirius:planned` (esa
etiqueta certifica una planificación aprobada — decisión humana), nunca aplica
`sirius:failed-safely` y nunca inicia trabajo. La puerta no garantiza ejecutarse
antes que la Routine: la Routine **conserva estas mismas comprobaciones** como
defensa en profundidad.

### Entrada válida

- incidencia abierta y conforme a la plantilla (todas las secciones
  obligatorias del contrato presentes; un cuerpo truncado no es válido);
- estado `sirius:planned` presente (la creación de la incidencia debe aplicarlo:
  la plantilla lo hace automáticamente; una creación por API debe incluirlo);
- sin otros estados `sirius:` activos o terminales (incluida
  `sirius:failed-safely`: reactivar exige retirar antes el diagnóstico de forma
  consciente);
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

## 6. Mecanismo real de ejecución

Los tres roles se ejecutan como tres workflows de GitHub Actions, cada uno
disparado por su etiqueta-evento, que invocan a `anthropics/claude-code-action`
para correr Claude Code de verdad dentro del propio runner:

- `.github/workflows/implement-sirius-work.yml` — `sirius:implement-requested`.
- `.github/workflows/review-sirius-work.yml` — `sirius:review-requested`.
- `.github/workflows/repair-sirius-work.yml` — `sirius:repair-requested`.

Todo el mecanismo vive en este repositorio y es inspeccionable: no hay
ninguna interfaz externa que registrar. La única acción pendiente fuera del
repositorio, y solo una vez, es añadir el secreto de autenticación de Claude
Code en la configuración del repositorio (Settings → Secrets and variables →
Actions):

- `CLAUDE_CODE_OAUTH_TOKEN`, si se autentica con un plan de suscripción de
  Claude (Pro/Max) — es el caso recomendado, ya que no genera facturación
  aparte; se genera con `claude setup-token` desde una sesión de Claude Code
  autenticada con esa cuenta.
- Alternativamente `ANTHROPIC_API_KEY`, si se prefiere facturación por uso de
  API; en ese caso hay que adaptar el nombre de la entrada en los tres
  workflows (`anthropic_api_key` en vez de `claude_code_oauth_token`).

`anthropics/claude-code-action` es un producto externo cuya interfaz exacta
(nombres de entradas, comportamiento de `allowed_tools`/`disallowed_tools`)
puede cambiar; verifica su README contra lo escrito en los tres workflows
antes de la primera ejecución real.

### Cómo se comunica Claude con el resto del sistema

Claude Code, dentro de cada workflow, nunca cambia etiquetas de la incidencia
ni la cierra por su cuenta: solo hace el trabajo (leer, implementar, revisar
o corregir según su rol; en implementador/corrector también comitea, hace
push y gestiona la PR) y termina escribiendo un único veredicto en un archivo
JSON, en la ruta fija que indica `SIRIUS_VERDICT_FILE` (ver
`scripts/automation/prompts/`). El script determinista
`scripts/automation/sirius_apply_verdict.sh` es quien aplica esa decisión:
reverifica por su cuenta todo lo que puede verificarse (existencia y estado
de la PR, head actual, consistencia con el head que superó Quality) en vez
de confiar en lo que el agente afirme. Un veredicto ausente, corrupto o fuera
del conjunto permitido para el rol se trata siempre como un fallo seguro.

### Permisos por rol (defensa en profundidad, no solo el prompt)

- Implementador y corrector: `contents: write`, necesitan comitear y hacer
  push.
- Revisor: `contents: read` — ni siquiera con acceso al token podría hacer
  push aunque lo intentara. La instrucción de "no modificar código en la
  primera pasada" no depende solo de que el modelo la respete.

### Single-flight y límite de reparación

Los tres workflows comparten el mismo grupo de concurrencia
(`sirius-work-<numero-de-incidencia>`), así que nunca hay dos ejecuciones
simultáneas sobre la misma incidencia — esto es lo que faltaba en el diseño
anterior y causó el incidente de PRs duplicadas (#52/#53). El corrector
cuenta los ciclos ya completados mediante los marcadores
`<!-- sirius-repair-cycle:N -->` que deja `sirius_apply_verdict.sh`; al llegar
al tercer intento se aplica `sirius:blocked-decision` sin siquiera invocar a
Claude.

Después de configurar el secreto, el usuario no copia prompts ni interactúa
con estas Routines directamente: crea la incidencia (a mano o pidiéndoselo a
Claude/ChatGPT) con `sirius:planned` y aplica `sirius:implement-requested`;
desde ahí todo avanza por eventos hasta `sirius:ready-for-merge`, donde solo
falta el comentario `fusiona` (ver `AUTOMATION_OPERATING_CONTRACT.md` §8).
