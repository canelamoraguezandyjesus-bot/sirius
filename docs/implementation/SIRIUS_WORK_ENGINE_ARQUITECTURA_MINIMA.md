# Sirius Work Engine — Arquitectura mínima implementable

- Estado: DISEÑO / RECONCILIACIÓN. **No autoriza implementación, merge ni cambio canónico.**
- Encargo: incidencia #172 (SIRIUS-WORK-ENGINE-DESIGN-001), sección 9.
- Fecha: 2026-08-15
- Base: commit `e13a1e3`; inventario de piezas en
  `docs/implementation/SIRIUS_WORK_ENGINE_INVENTARIO.md`; decisión de diseño en
  `docs/decisions/ADR-019-el-motor-de-trabajo-posee-el-estado-y-los-workers-son-sustituibles.md`.
- Conserva sin rediseñar los Puntos 1–4 cerrados de #172 y el chasis de tres capas de su
  sección 5. Las contradicciones materiales encontradas NO se resuelven aquí: se presentan
  con evidencia en la sección 14 y esa rama del diseño queda detenida.

---

## 0. Qué es esto y qué no es

Esto es la arquitectura mínima del sistema de trabajo de Sirius: un **Motor de Trabajo**
determinista, propiedad de Sirius, que posee el estado y el ciclo de los trabajos, y
**Workers sustituibles** (Claude Code, Codex, GPT Researcher, programas deterministas…) que
ejecutan encargos temporales dentro de ese ciclo, detrás de Adapters finos.

No es: código productivo, una adopción de frameworks, un rediseño del chasis de #172, ni
una segunda vía paralela a la automatización existente. La automatización GitHub actual
**es** el primer Adapter de Worker del motor (sección 7.1), no algo a sustituir.

## 1. El chasis de tres capas, aterrizado sobre lo que existe

```
CAPA 1 — INTERACCIÓN
  usuario -> interfaz sustituible -> Sirius
  hoy: sesión de Claude Code / ChatGPT / web de GitHub (el propietario como transporte)
  primera prueba: Telegram como adaptador fino (7.4); mañana: UI propia, voz
        |
        v   (intención; conversación; consulta; orden de trabajo; decisión)
CAPA 2 — MOTOR DE TRABAJO (software determinista de Sirius; NO es un agente)
  interpretar intención (con ayuda de modelo, sin autoridad) -> WorkItem
  ciclo: PREPARAR -> EJECUTAR -> COMPROBAR -> REVISAR -> REPARAR* -> ENTREGAR
  máquina de estados durable + supervisor (deadlines, recuperación) + despachador
        |
        v   (WorkPackage)              ^ (WorkResult)
CAPA 3 — SERVICIOS COMUNES Y ADAPTERS
  almacén de estado | contexto.recuperar | permisos | presupuesto | evidencia | notificación
  Adapters de Worker: Claude Code (GitHub) | Codex (GitHub review) | GPT Researcher |
                      comprobador determinista local | (futuros)
  Adapters de interfaz: Telegram | CLI/sesión | (futuros)
```

Telegram, GitHub, Claude, Codex, GPT Researcher, Inspect, Hermes, MCP o una skill son
piezas sustituibles alrededor de este chasis; ninguna posee estado, ciclo ni permisos.

## 2. Componentes estrictamente necesarios (y ninguno más)

Cada componente lleva su naturaleza: **[D]** determinista, **[M]** necesita modelo,
**[D+M]** determinista con ayuda opcional de modelo.

| # | Componente | Responsabilidad | Naturaleza |
|---|---|---|---|
| 1 | **Almacén de estado** | Persistir WorkItems, Runs y el diario de eventos del motor. SQLite propio del motor (fichero separado; nunca la base del producto 0.1) | [D] |
| 2 | **Máquina de estados** | Transiciones válidas de WorkItem y Run (sección 3); toda mutación pasa por aquí y queda en el diario | [D] |
| 3 | **Supervisor** | Deadlines por Run, sondeo de `STATUS` vía Adapters, detección de Runs perdidos, barrido de recuperación al arrancar | [D] |
| 4 | **Despachador** | Elegir Worker para un paso (perfil requerido + capacidades + permisos + presupuesto), construir el WorkPackage, invocar `START`. Despacha pasos en paralelo SOLO si no dependen entre sí (independencia real, #172 §2.6); en la duda, en serie | [D] |
| 5 | **Capability Resolver** | Traducir capacidades abstractas de un perfil a proveedores concretos (skill/MCP/API/CLI/función local/Worker externo) según registro versionado | [D] |
| 6 | **Perfiles de agente** | Documentos versionados: misión, procedimiento, capacidades requeridas, permisos, contrato E/S, criterios de éxito y parada. Sin modelo, runtime, credenciales ni estado | [dato, no código] |
| 7 | **Intérprete de intención** | Distinguir conversar/consultar/explorar/decidir/ordenar; estructurar un borrador de WorkItem desde lenguaje natural. Nunca crea trabajo por sí mismo: la creación exige confirmación (sección 8.5) | [M] con puerta [D] |
| 8 | **Contexto** (`contexto.recuperar`) | Capacidad común de recuperación (sección 9); compone proveedores; filtra por contexto autorizado | [D] (proveedores; el resumen final puede ser [M]) |
| 9 | **Permisos y presupuesto** | Perfil de permisos por WorkItem/Run (deny-by-default); límites de gasto/turnos/tiempo; corte y escalado al agotar | [D] |
| 10 | **Escalado y notificación** | Detectar condiciones de `NEEDS_DECISION` (sección 10); notificar por la interfaz activa; registrar la decisión del propietario como entrada | [D] |
| 11 | **Evidencia** | Diario append-only del motor + artefactos visibles en GitHub (bus provisional); todo lo necesario para reconstruir qué ocurrió (sección 12) | [D] |
| 12 | **Adapters** | Traducción fina Sirius↔Worker y Sirius↔interfaz (secciones 7 y 8) | [D] |

Lo que #172 §2.8 prohíbe y este diseño respeta: no hay Planner Agent ni Coordinator Agent.
La planificación compleja puede pedirse a un modelo **como un paso más** (un Run cuyo
resultado es un plan que el motor almacena), pero la persistencia, las dependencias, los
reintentos, la espera y la transición de estados son software determinista.

## 3. Modelo de estado

### 3.1 WorkItem

Registro durable, propiedad del motor. Campos mínimos (#172 §1.2):

```
work_id            identificador estable (p. ej. WI-2026-0001)
peticion_original  texto literal + referencia al origen (conversación, incidencia, orden)
objetivo           normalizado por el intérprete de intención, confirmado
contexto_origen    referencias autorizadas (proyecto, incidencias, documentos, decisiones)
entregable         qué debe existir al terminar
criterio_terminado qué comprobación lo declara terminado
limites            perfil de permisos + presupuesto (gasto, turnos, tiempo) + fuera de alcance
prioridad          repriorizable en caliente; no es un estado
clase              conversacion-no-aplica | investigacion | documentacion | programacion |
                   auditoria | consulta-larga | mixta
estado             (3.2)
fase               PREPARAR | EJECUTAR | COMPROBAR | REVISAR | REPARAR | ENTREGAR
plan               lista mínima de pasos (puede ser un solo paso); cada paso: perfil
                   requerido, capacidades, dependencias
evidencia          referencias al diario y a artefactos (PRs, informes, fuentes)
resultado          síntesis final + artefactos entregados
```

### 3.2 Estados del WorkItem y transiciones

```
                 crear (confirmado)
                        |
                        v
   +----------------- PLANNED ------------------ cancelar --------------+
   |                    | activar (orden del propietario o cola aprobada)|
   |                    v                                                v
   |   +------------- ACTIVE <--------------------+                 CANCELLED
   |   |                |  \                      | reanudar            ^
   |   |     despacho   |   \ escalar             |                     |
   |   |     asincrono  |    v                    |                     |
   |   |                |   NEEDS_DECISION -- decisión registrada       |
   |   |                v        |                                      |
   |   |             WAITING     +---- cancelar por decisión -----------+
   |   |                |  ^
   |   |  hecho externo |  | despacho asíncrono
   |   |                v  |
   |   |              ACTIVE
   |   |                |
   |   |    sin progreso posible, con diagnóstico
   |   |                v
   |   |          FAILED_SAFELY -- reactivación consciente --> ACTIVE
   |   |                |
   |   |                +------------------- cancelar ------------------+
   |   |  fase ENTREGAR completada
   |   |                v
   |   +----------> DELIVERED   (terminal)
   |
   +--- pausar (desde PLANNED/ACTIVE/WAITING) --> PAUSED -- reanudar --> estado previo
```

| Estado | Significado | Quién lo saca |
|---|---|---|
| `PLANNED` | Definido y confirmado; sin ejecutar | Activación (orden o cola aprobada) |
| `ACTIVE` | El motor está procesando una fase (hay un Run vivo o un paso listo) | El propio motor |
| `WAITING` | Sin Run que atender de inmediato: espera un hecho externo (CI, Worker asíncrono, temporizador) | El supervisor, al observar el hecho |
| `NEEDS_DECISION` | Escalado al propietario (sección 10) | Solo la decisión registrada del propietario |
| `PAUSED` | Pausado por orden | Orden de reanudar |
| `FAILED_SAFELY` | Parada segura con diagnóstico legible; nada se pierde | Reactivación consciente (como hoy exige retirar la etiqueta a sabiendas) |
| `CANCELLED` | Terminal; el motor cancela los Runs vivos vía `CANCEL` y lo deja escrito | — |
| `DELIVERED` | Terminal; entregable producido, criterio de terminado satisfecho, resultado entregado por la interfaz | — |

Operaciones que NO son estados:

- **Reintento**: crea un Run nuevo sobre el mismo paso (política por perfil: n.º máx. de
  intentos, espera). El WorkItem no cambia de estado por reintentar.
- **Sustitución de Worker**: reintento con otro Worker que satisfaga el mismo perfil.
  Registrada en el diario como sustitución, con motivo.
- **Cambio de alcance**: edición versionada del WorkItem (objetivo/entregable/límites) desde
  cualquier estado no terminal; obliga a rehacer PREPARAR; queda el antes y el después en el
  diario. Si el cambio invalida Runs vivos, el motor los cancela primero.
- **Repriorización**: cambio del campo `prioridad`; afecta al orden de despacho, no al estado.
- **Reinicio del proceso de Sirius**: no es una transición; ver 3.5.

### 3.3 Run

Un Run es **un intento de ejecución de un paso por un Worker**. Es la unidad que puede
morir sin avisar; por eso su ciclo está diseñado alrededor de esa muerte.

```
run_id           identificador
work_id / paso   a qué WorkItem y paso pertenece
worker           adapter + perfil + (si aplica) modelo/runtime concretos usados
work_package     instantánea exacta de lo enviado (4.1)
intento          n.º de intento sobre ese paso
estado           PREPARED -> DISPATCHED -> RUNNING -> FINISHED(desenlace)
desenlace        SUCCEEDED | FAILED | CANCELLED | LOST
deadline         cota absoluta (ADR-003: mínimo contra cota, nunca ventana propia)
observaciones    último STATUS conocido + instante
resultado        WorkResult (4.2), si lo hubo
```

Reglas:

- `DISPATCHED` → `RUNNING` cuando `STATUS` confirma que el Worker aceptó el encargo.
- Un Run **nunca resucita**: reintentar es crear otro Run.
- **`LOST`**: el supervisor no obtiene un `STATUS` concluyente y la cota absoluta vence.
  El Run se cierra como perdido, con el último dato observado, y la política del paso decide:
  reintentar, sustituir Worker o escalar. Esta es la respuesta estructural a «un proceso que
  muere no puede informar de su propia muerte»: quien lo declara muerto es un observador
  externo con estado propio, no el proceso.
- `CANCELLED`: el motor invocó `CANCEL`; si el Adapter no puede garantizar la cancelación
  remota, lo dice, y el Run queda cancelado para el motor con nota de «cancelación remota no
  confirmada» (el supervisor deja de atenderlo salvo para registrar efectos tardíos).

### 3.4 Las fases y el ciclo revisar-reparar

`PREPARAR → EJECUTAR → COMPROBAR → REVISAR → (REPARAR → COMPROBAR → REVISAR)* → ENTREGAR`

- **PREPARAR** [D+M]: reconstruir qué se pidió, contexto autorizado
  (`contexto.recuperar`), decisiones y restricciones aplicables, entregable, comprobaciones
  deterministas disponibles, perfil y Worker candidatos, permisos y presupuesto.
- **EJECUTAR** [M o D]: Run del Worker principal del paso.
- **COMPROBAR** [D]: SIEMPRE antes de pedir juicio a otro modelo, todas las validaciones
  objetivas disponibles: código → tests/lint/tipos/diff/estado de PR; documentación →
  rutas, referencias, existencia de artefactos, formato; investigación → presencia de
  fuentes y URLs, trazabilidad mínima; trabajo externo → estado real del servicio. «El
  Worker dice que terminó» no es evidencia.
- **REVISAR** [M]: otro Worker con perfil de revisión independiente. Salida cerrada:
  `APPROVED` | `CHANGES_REQUIRED` (defecto, evidencia, gravedad, corrección esperada — el
  contrato de observación ya existente) | `DECISION_REQUIRED`. El revisor no arregla lo que
  revisa.
- **REPARAR** [M]: las observaciones vuelven **al Worker**, no al propietario. El bucle
  continúa bajo la política de convergencia heredada (par pendientes/gravedad estrictamente
  descendente contra la mejor marca; reaparición u oscilación → `NEEDS_DECISION`).
- **ENTREGAR** [D+M]: síntesis final + artefactos + evidencia por la interfaz activa;
  `criterio_terminado` comprobado de forma determinista donde sea posible.

### 3.5 Durabilidad y reinicio

- Toda transición se escribe en el almacén **antes** de producir efectos externos
  observables, y los efectos externos son idempotentes o reanudables (el patrón ya probado
  de `sirius_transition`: marcador primero comprobado, mutación después, comentario al final).
- Al arrancar, el motor ejecuta un **barrido de recuperación**: para cada Run no terminado
  consulta `STATUS` contra el mundo real (la API de GitHub, el estado del proceso local…)
  y reconcilia; para cada WorkItem en `ACTIVE`/`WAITING` recalcula el siguiente paso. Un
  reinicio de Sirius no pierde ni duplica trabajo: como mucho repite una consulta.
- Si el propio motor está caído, no hay supervisión: esa ventana se cubre con (a) el
  reconciliador GitHub existente como respaldo de la vía GitHub, y (b) la notificación de
  arranque/parada del motor en el diario. La cota de esta garantía queda escrita: **el motor
  no se supervisa a sí mismo**; su caída la nota el propietario (o un vigilante externo
  futuro, fuera de este mínimo).

## 4. WorkPackage y WorkResult

### 4.1 WorkPackage (lo que recibe todo Worker, sea cual sea)

```yaml
work_id:        WI-…            # y run_id del intento
objetivo:       …               # qué debe lograr ESTE paso, no el WorkItem entero
contexto:                       # SOLO contexto autorizado por el perfil de permisos
  - {tipo: documento|decision|extracto|enlace, ref: …, contenido?: …}
entregable:     …               # forma exacta del resultado esperado
restricciones:  [fuera de alcance, invariantes, salvaguardas]
capacidades:    [contexto.recuperar, repo.leer, web.buscar, …]   # abstractas
permisos:       perfil aplicado (deny-by-default; escritura solo si el perfil la da)
criterios_aceptacion: [comprobables; alimentan COMPROBAR y REVISAR]
limites:        {presupuesto, tiempo_max, turnos_max, reintentos}
```

La plantilla actual del Work Item de GitHub (12 secciones) es la **proyección textual** de
este paquete para la vía GitHub; `validate_issue_body.py` ya valida esa proyección.

### 4.2 WorkResult (lo que devuelve todo Worker)

```yaml
estado:            SUCCEEDED | FAILED | BLOCKED_BY_DECISION | USAGE_LIMIT_REACHED
resultado:         resumen de lo hecho (texto corto, saneable)
artefactos:        [{tipo: pr|fichero|informe|dato, ref: …, sha?: …}]
evidencia:         [qué lo demuestra: runs, salidas de comandos, fuentes con URL]
comprobaciones:    [qué validaciones ejecutó o presenció el Worker, con desenlace]
problemas:         [contratiempos, decisiones que necesitó y no tenía]
no_comprobado:     [lo que queda sin verificar — obligatorio, puede ser vacío explícito]
metricas:          {tiempo?, coste?, turnos?, tool_calls?}   # unknown si no observable
```

El veredicto JSON actual (`{"verdict","summary","reviewed_head_sha","observations"}`) es un
`WorkResult` reducido; el Adapter lo eleva a esta forma. La regla vigente se conserva: el
Worker **informa**, el motor **aplica**. Un WorkResult ausente, ilegible o fuera de contrato
nunca se interpreta como éxito: cierra el Run como `FAILED` con diagnóstico (el patrón de
`sirius_apply_verdict.sh` hoy).

## 5. Contrato de Worker: START / STATUS / RESULT / CANCEL

Interfaz conceptual, sin HTTP, MCP, A2A, CLI ni proveedor presupuestos. La implementa cada
Adapter; el motor solo conoce esto:

| Operación | Semántica | Reglas |
|---|---|---|
| `START(work_package) -> run_ref` | Encargar el trabajo. | Idempotente por `run_id` (re-invocar con el mismo id no duplica el encargo, o el Adapter lo detecta y devuelve la ref existente). |
| `STATUS(run_ref) -> {ACCEPTED\|RUNNING\|FINISHED\|UNKNOWN}` | Observación barata y frecuente. | Nunca bloquea; `UNKNOWN` es respuesta legítima (y la que activa la cuenta atrás hacia `LOST`). Puede llevar señal de progreso opcional. |
| `RESULT(run_ref) -> work_result` | Recoger el resultado tras `FINISHED`. | Releíble (idempotente). Resultado ilegible = `FAILED`, nunca éxito. |
| `CANCEL(run_ref)` | Pedir la cancelación. | Mejor esfuerzo declarado: el Adapter responde `confirmada` o `no confirmada`, y el motor registra cuál fue. |

Notas de diseño:

- El sondeo de `STATUS` lo hace el **supervisor del motor** con cadencia por Adapter (un
  Run de Actions se consulta distinto que un proceso local). Un modelo nunca se queda
  «pensando si ya terminó otro agente» (#172 §2.8).
- Push además de pull: un Adapter puede empujar eventos (webhook, callback) como
  aceleración; el pull es la garantía, el push es la mejora.
- Si un Worker externo habla un estándar útil, su Adapter lo aprovecha por dentro; el
  contrato de Sirius no cambia (#172 §4.5).

## 6. Capability Resolver

Los perfiles piden capacidades abstractas; el Resolver las satisface con el proveedor
concreto disponible en el runtime del Worker elegido, según un **registro versionado** en el
repositorio (dato, no código; heredero directo del `registro_de_acciones.yml` de la PR #171
y de la superficie §2b del Auditor).

```
AgentProfile ──capacidades──> Resolver ──registro──> proveedor concreto
   web.buscar                              ├─ herramienta nativa del runtime (p. ej. la
   repo.leer                               │  búsqueda web del runtime del Worker)
   contexto.recuperar                      ├─ skill (paquete de procedimiento reutilizable)
   validacion.ejecutar                     ├─ servidor MCP
   documento.crear                         ├─ API / CLI
   …                                       ├─ función local determinista
                                           └─ delegación a otro Worker (p. ej. investigar)
```

Reglas:

1. **Orden de resolución = reutilizar antes de crear** (#172 §4.1): agente existente →
   skill → MCP/API/CLI → librería/programa local → pieza propia mínima, y solo con motivo.
2. **Deny-by-default**: solo se resuelven las capacidades que el perfil declara Y el perfil
   de permisos del WorkItem autoriza. Una capacidad con escritura o con red se resuelve solo
   si ambos lo permiten.
3. **La resolución queda en la evidencia** del Run: qué capacidad se pidió y con qué
   proveedor se satisfizo (dos runs solo son comparables si su resolución coincide — regla
   heredada del Auditor §2b).
4. **Entrega parcial declarada**: si un runtime no puede dar una capacidad completa (el
   precedente real: `leer_github` parcial en la superficie por etiqueta), el registro lo
   dice y el WorkResult debe declararlo en `no_comprobado`. Un informe que calla un recorte
   de superficie es un run fallido (regla heredada de la PR #171).
5. MCP es **un** transporte posible, nunca la arquitectura (#172 §4.4); si una función
   local o una CLI es más simple, gana.
6. Una **skill** es un paquete de capacidad/procedimiento reutilizable (instrucciones,
   scripts, plantillas, referencias) — nunca autoridad ni memoria — y puede ser propia o
   externa si es portable y auditable. Su formato NO determina el motor: el Resolver la
   trata como un proveedor más (#172 §4.3).

## 7. Adapters de Worker

### 7.1 Claude Code por GitHub (Worker principal inicial; reutiliza TODO lo existente)

La automatización actual se convierte en el Adapter, sin segunda vía paralela:

| Contrato | Implementación con lo que ya existe |
|---|---|
| `START` | Crear/actualizar la incidencia Work Item (proyección del WorkPackage por la plantilla actual) y aplicar la etiqueta de arranque del rol (`sirius:implement-requested` / `review-requested` / `repair-requested`). ⚠️ La aplicación de `implement-requested` por una máquina está hoy PROHIBIDA por el contrato §9.1 límite 1 — contradicción C1, sección 14; esta rama queda detenida hasta decisión del propietario. |
| `STATUS` | Lectura de etiquetas + marcadores de la incidencia (`sirius_issue.sh` ya implementa la lectura robusta y el filtro de confianza) + estado del run de Actions por API. Etiqueta `*-ing` con run muerto y cota vencida → `UNKNOWN` → `LOST`. |
| `RESULT` | Los marcadores y bloques estructurados existentes SON el formato de retorno: `## IMPLEMENTACION_LISTA` + `Head SHA`, veredictos `<!-- sirius-verdict:… -->`, `## OBSERVACIONES_ESTRUCTURADAS`, `## RONDA_HALLAZGOS`, `PR abierta: <URL>`. El Adapter los eleva a WorkResult. |
| `CANCEL` | Cancelar el run de Actions por API + retirar la etiqueta de evento/estado con la identidad correcta (regla ADR-014/015) + nota en la incidencia. |

Mapa de estados (vía GitHub → motor): `planned` ↔ `PLANNED`; `implementing`/`ci-pending`/
`reviewing`/`repairing` ↔ Run vivo del paso correspondiente (`ACTIVE`/`WAITING`);
`blocked-decision` ↔ `NEEDS_DECISION`; `failed-safely` ↔ `FAILED_SAFELY`;
`ready-for-merge` ↔ `WAITING` (espera la orden humana `fusiona`); `completed` ↔ fase
ENTREGAR del WorkItem (que puede abarcar más que la PR). Las etiquetas siguen siendo
protocolo de la vía, no el estado canónico (ver C5, sección 14).

Consecuencias:

- El motor pasa a ser el **observador externo** que el descargo de
  `repair-sirius-work.yml:67-81` declara imposible desde dentro: detecta el Run perdido en
  minutos (cota del Run), no en ≥180 min + 6 h. El reconciliador actual queda como respaldo
  de la vía GitHub, no como única vigilancia (ver C2, sección 14: la vigilancia del motor
  requiere decisión del propietario porque el contrato hoy la prohíbe como «motor»).
- Los tres prompts de rol se versionan como Agent Profiles neutrales (lo que ya son casi);
  el modo de ejecución actual (`--dangerously-skip-permissions`, PAT en el runner) conserva
  la clasificación de **prototipo declarado** que fijó la PR #171.
- Claude Code sigue siendo Worker: no coordina, no posee estado, no fusiona. El merge sigue
  siendo humano por `fusiona` (contrato §8), y eso no cambia en este diseño.

### 7.2 Codex por GitHub (Worker-revisor; sin duplicar la vía)

Codex participa exactamente por donde ya participa: la revisión dual de
`review-sirius-work.yml`. En términos del motor:

- Codex es un **Worker de perfil revisor** cuyo único canal es la PR de GitHub. Su Adapter
  ya existe: `sirius_codex_review.py` (`trigger` = START, sondeo interno = STATUS, JSON
  normalizado = RESULT; CANCEL no existe y el Adapter lo declara: `no confirmada`).
- La agregación determinista de dos revisores (`sirius_aggregate_reviews.py`) es un paso
  [D] del motor en la fase REVISAR: sin votos, con la precedencia ya probada, y sin
  degradación silenciosa a un solo revisor.
- El motor no asume que el modo dual esté activo: `SIRIUS_CODEX_REVIEW_ENABLED` sigue **NO
  VERIFICADO** desde el árbol; leerla es un dato que el propietario puede dar en un minuto
  (sección 15, incógnita I5).

### 7.3 GPT Researcher (Worker de investigación, OBLIGATORIO en el MVP) y `ExportSafeBrief`

Agente externo tras Adapter (#172 tipo B). No se instala en esta fase; su Adapter se diseña:

- `START`: el motor construye un **`ExportSafeBrief`** y lanza el proceso de GPT Researcher
  con ese único insumo. `STATUS`: estado del proceso/job local. `RESULT`: informe + fuentes
  + incertidumbres, normalizados a WorkResult. `CANCEL`: terminar el proceso.
- **Frontera de confidencialidad mecánica, no de prompt**: el Worker con Internet corre
  **sin credenciales del repositorio ni acceso al árbol privado**. La protección es
  estructural: no puede filtrar lo que no recibió. Esto es deliberadamente MÁS fuerte que
  la frontera contrato+registro del Investigador de la PR #171 (detección posterior al
  hecho), tal como exige #172 §4.7: «La protección no puede depender únicamente de decirle
  al modelo "no filtres datos"».
- **`ExportSafeBrief`** (construcción [D], redacción asistida [M], dentro de Sirius):
  pregunta de investigación + contexto mínimo imprescindible reescrito para exportación +
  restricciones de ámbito + formato esperado. Regla dura: al brief solo entra material
  marcado exportable; nombres, rutas, código y datos del repo privado NO entran salvo
  decisión explícita registrada. El brief completo queda en la evidencia del Run.
- **Reconciliación al volver**: el resultado externo se une al contexto privado DENTRO de
  Sirius (fase COMPROBAR: fuentes presentes y accesibles, trazabilidad mínima; fase REVISAR
  si el trabajo lo pide). El investigador externo nunca escribe en el repo ni en la memoria.
- Convivencia de perfiles: «investigación externa» (GPT Researcher, sin repo, con web) e
  «investigación interna» (el Investigador de #171: con repo, con web, riesgo residual
  declarado) son perfiles distintos con fronteras distintas; el motor elige por la
  sensibilidad del contexto que el trabajo necesita.

### 7.4 Telegram (Adapter de interacción, sin lógica de motor)

- Traduce mensajes/voz/archivos ↔ operaciones de la Capa 1: conversar, consultar estado,
  crear trabajo (con confirmación), pausar, reanudar, cancelar, decidir una escalada.
- **Cero estado propio**: si Telegram desaparece, no se pierde nada; otra interfaz (CLI,
  sesión, UI futura) ofrece las mismas operaciones contra el mismo motor.
- Seguridad mínima de diseño: solo el propietario autenticado; toda orden sensible se
  confirma; los textos del canal son entrada no confiable para el intérprete de intención,
  jamás órdenes directas a Workers.
- No se instala en esta fase (#172 §8).

### 7.5 Comprobador determinista (Worker local [D])

Las validaciones objetivas de COMPROBAR se ejecutan como Runs de un Worker determinista
local (o del runner de la vía GitHub, como hoy hace Quality): tests, lint, tipos,
existencia de rutas y artefactos, enlaces, formato. Ya existe en dos formas: `quality.yml`
y los pasos de arnés que la PR #171 añade al Auditor («el arnés ejecuta y el modelo
interpreta»). El motor generaliza ese patrón: comprobar nunca es opinión de modelo.

## 8. Flujos de extremo a extremo

### 8.1 Documentación + Reviewer + Repair (la clase nueva más inmediata)

1. PREPARAR: contexto del proyecto (`contexto.recuperar`), decisiones aplicables,
   entregable (documento X con criterios Y), perfil «documentalista».
2. EJECUTAR: Worker (p. ej. Claude Code por GitHub, en rama, o un Worker de documento
   local) produce/edita el artefacto.
3. COMPROBAR [D]: rutas citadas existen, referencias internas resuelven, formato válido,
   artefactos declarados presentes.
4. REVISAR: Worker con perfil «revisor documental» independiente → `APPROVED` /
   `CHANGES_REQUIRED` con el contrato de observación existente.
5. REPARAR: las observaciones vuelven al Worker ejecutor; convergencia heredada; el
   propietario no transporta nada.
6. ENTREGAR: síntesis + enlace al artefacto; si el artefacto vive en el repo, la fusión
   sigue siendo humana (`fusiona`).

### 8.2 Programación (la vía existente, dentro del motor)

El ciclo actual completo (implementar → Quality → revisión dual → reparar → merge humano →
cierre) se conserva como está; el motor añade por fuera: estado durable del WorkItem,
supervisión con cota corta, reintento/sustitución tras `LOST`, y entrega final por la
interfaz. Nada de la cadena determinista se duplica.

### 8.3 Investigación (GPT Researcher)

1. PREPARAR: pregunta normalizada; construcción del `ExportSafeBrief`.
2. EJECUTAR: Run del Adapter de GPT Researcher (7.3), estado `WAITING` mientras corre.
3. COMPROBAR [D]: fuentes presentes, URLs accesibles, estructura del informe.
4. REVISAR (si el trabajo lo pide): perfil revisor sobre el informe.
5. ENTREGAR: síntesis reconciliada con el contexto privado + fuentes; opcionalmente el
   resultado alimenta un WorkItem de documentación (8.1).

### 8.4 Auditoría (perfil portable en el mismo motor)

El Auditor es un Agent Profile más (el runbook existente), con perfil de permisos de solo
lectura resuelto por el Resolver. Ejecuta por la superficie disponible (sesión o etiqueta
`auditoria:solicitada`, que su Adapter conoce); la propiedad de ADR-016 se conserva: ningún
Run con modelo y permisos de escritura. Sus hallazgos NO se convierten en trabajo
automáticamente (ADR-010): la síntesis se entrega al propietario, que decide.

### 8.5 Conversación → trabajo (la puerta que evita formularios y falsos WorkItems)

- Conversar, consultar el pasado, explorar y debatir NO crean WorkItem. La conversación es
  entrada; su continuidad la da la Capa 1 + `contexto.recuperar`.
- El intérprete de intención [M] detecta una posible orden de trabajo y estructura un
  borrador de WorkItem (objetivo, entregable, límites) a partir del lenguaje natural.
- **Puerta determinista**: el WorkItem solo nace cuando el propietario confirma el borrador
  con un acto explícito (un «sí, hazlo» sobre el resumen propuesto). Sin confirmación, no
  hay trabajo. La activación (`PLANNED → ACTIVE`) es la orden del propietario, o una cola
  expresamente aprobada (la única figura que el contrato ya contempla, §9 in fine).

## 9. Contexto sin «Agente de memoria»

`contexto.recuperar(consulta, ámbito autorizado)` es una **capacidad común** [D]:

- Hoy compone proveedores deterministas: búsqueda en el árbol del repo (ficheros, ADRs,
  docs), búsqueda en GitHub (incidencias, PRs, marcadores del ciclo — la E/S robusta ya
  existe), y git (historial).
- Mañana añade la memoria propia de Sirius: el sustrato ya existe en el producto
  (`knowledge_fts` + ranking determinista + presupuesto de contexto en
  `src/sirius/application/`), pero hoy solo sirve al turno conversacional y no está
  expuesto como capacidad; exponerlo es trabajo futuro sobre código existente, sin cambiar
  los perfiles que lo consumen.
- Los resultados entran al WorkPackage como `contexto` **filtrado por el perfil de
  permisos** (un Worker con web no recibe contexto privado: 7.3).
- No hay «Agente de memoria»: ningún empleado con estado propio; una función que consulta
  fuentes y devuelve extractos con referencia.

## 10. Escalado al propietario (y solo esto escala)

`NEEDS_DECISION` se dispara únicamente por (#172 §2.7):

1. decisión de producto o arquitectura no resuelta (incluye `DECISION_REQUIRED` del revisor
   y `BLOCKED_BY_DECISION` del Worker);
2. gasto nuevo o cambio de presupuesto (incluye agotar el presupuesto del WorkItem);
3. permisos o credenciales sensibles;
4. operación destructiva o difícilmente reversible;
5. privacidad o salida de información sensible (incluye cualquier excepción al
   `ExportSafeBrief`);
6. alternativas razonables con consecuencias materialmente distintas;
7. ausencia real de convergencia tras intentos razonables (la política de convergencia lo
   detecta sola).

Los fallos técnicos corregibles NO escalan: reintento, sustitución de Worker o
`FAILED_SAFELY` con diagnóstico, en ese orden de preferencia. Cada escalada llega por la
interfaz activa con el contexto suficiente para decidir sin reconstruir nada, y la decisión
queda registrada en el diario y, si procede, como ADR.

## 11. Qué es determinista y qué necesita modelo

| Determinista (software de Sirius) | Necesita modelo (Workers) |
|---|---|
| Almacén, máquina de estados, transiciones | Interpretar intención y estructurar borradores |
| Supervisión, deadlines, `LOST`, recuperación | Implementar, corregir, redactar |
| Despacho, construcción del WorkPackage | Revisar con juicio (perfil independiente) |
| COMPROBAR (validaciones objetivas) | Investigar y sintetizar |
| Agregación de revisiones, convergencia | Auditar (con arnés determinista alrededor) |
| Resolver capacidades, permisos, presupuesto | Planificar un trabajo complejo (como paso, sin poseer el ciclo) |
| Escalado, notificación, evidencia, entrega mecánica | Síntesis final legible |

## 12. Evidencia: reconstruir qué ocurrió

- **Diario del motor** (append-only, en su almacén): toda transición de WorkItem y Run,
  todo WorkPackage/WorkResult (o su ausencia), toda resolución de capacidades, toda
  escalada y decisión, toda sustitución de Worker con motivo. Suficiente para responder
  «¿qué pasó con este trabajo?» sin leer GitHub.
- **GitHub como evidencia visible** (bus provisional, #172 §1.3): PRs, incidencias,
  marcadores y comentarios siguen siendo el registro público entre herramientas; el motor
  no lo convierte en vertedero de conversaciones.
- Reglas heredadas que se conservan: ninguna lectura fallida entra en una afirmación; los
  duplicados posibles se neutralizan en los lectores; todo texto de modelo se sanea antes
  de publicarse dentro del filtro de confianza.

## 13. Respuestas a los criterios de aceptación de #172 §11

(Respuestas según este diseño; donde una respuesta depende de una contradicción detenida en
la sección 14, se marca.)

- **¿Dónde vive el estado si Telegram desaparece?** En el almacén del motor [canónico
  condicionado a C5]. Telegram es un adaptador sin estado (7.4).
- **¿Si Claude Code muere?** El WorkItem y el Run viven en el motor; el Run muerto termina
  en `LOST` por cota y se reintenta/sustituye/escala (3.3). En la vía GitHub, además, la
  incidencia conserva su proyección.
- **¿Si GPT Researcher falla?** Igual: Run `FAILED`/`LOST`; el WorkItem no se pierde; el
  brief queda en la evidencia para reintentar (7.3).
- **¿Cómo se reanuda un trabajo tras reinicio?** Barrido de recuperación: `STATUS` de cada
  Run abierto contra el mundo real + recálculo del siguiente paso (3.5).
- **¿Cómo se cancela?** Orden por la interfaz → `CANCELLED`; el motor invoca `CANCEL` en
  los Runs vivos y registra si la cancelación remota quedó confirmada (3.2, 5).
- **¿Cómo se cambia el alcance?** Edición versionada del WorkItem + rehacer PREPARAR +
  cancelación previa de Runs invalidados (3.2).
- **¿Cómo se diferencia conversar de crear trabajo?** Puerta determinista de confirmación
  sobre un borrador estructurado por el intérprete (8.5).
- **¿Cómo se recupera contexto?** Capacidad común `contexto.recuperar` que compone
  proveedores deterministas; sin agente de memoria (9).
- **¿Cómo se satisfacen capacidades sin acoplar perfiles?** Registro versionado + Resolver
  deny-by-default; los perfiles nunca nombran herramientas (6).
- **¿Cómo se reutiliza Claude Code por GitHub?** La automatización existente ES el Adapter;
  mapa completo en 7.1.
- **¿Cómo se reutiliza Codex por GitHub?** Worker-revisor por la vía dual existente;
  `sirius_codex_review.py` ya es su Adapter (7.2).
- **¿Cómo investiga GPT Researcher sin el repo privado?** Frontera mecánica: proceso sin
  credenciales ni árbol; solo recibe el `ExportSafeBrief` (7.3).
- **¿Cómo se crea y revisa documentación?** Flujo 8.1 con el contrato de observación y la
  convergencia existentes.
- **¿Cómo se ejecuta el Auditor?** Perfil portable con permisos de solo lectura, por la
  superficie disponible; propiedad ADR-016 intacta (8.4).
- **¿Cómo vuelven los defectos al Worker automáticamente?** `CHANGES_REQUIRED` →
  observaciones estructuradas → Run de reparación del Worker ejecutor; convergencia
  gobierna el bucle (3.4, 8.1).
- **¿Cómo se evita que el propietario sea mensajero?** El motor transporta: contexto (9),
  resultados (RESULT), defectos (REPARAR), avisos (10). El propietario solo decide lo de
  la lista cerrada de 10 y da la orden de fusión.
- **¿Cómo se sustituye un Worker sin cambiar el motor?** Otro Adapter que cumpla
  START/STATUS/RESULT/CANCEL para el mismo perfil; la sustitución es un Run nuevo (3.3, 5).
- **¿Qué parte es determinista y cuál de modelo?** Tabla de 11.
- **¿Qué permisos/gastos obligan a escalar?** Lista cerrada de 10.
- **¿Qué evidencia permite reconstruir?** Diario del motor + GitHub visible (12).
- **¿Qué sucede si una GitHub Action muere sin registrar su muerte?** El supervisor externo
  la declara `LOST` al vencer la cota del Run y actúa; deja de depender de que el proceso
  moribundo avise (3.3, 7.1). [Sujeto a C2, sección 14.]

## 14. Contradicciones materiales — presentadas y detenidas, no resueltas

Regla de #172 §12 aplicada: decisión exacta + evidencia + consecuencia + recomendación +
rama detenida. **Ninguna se resuelve en este documento.**

### C1 — El motor no puede aplicar `sirius:implement-requested` (contrato §9.1, límite 1)

- **Decisión vigente**: `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` §9.1 límite
  1: «No inicia trabajo. No aplica **nunca** `sirius:implement-requested`»; y §9: «iniciar
  bloques sucesivos sin orden del usuario o cola expresamente aprobada» está prohibido.
  Vigilado por RECON-STUCK-007/013.
- **Conflicto**: el `START` del Adapter de Claude Code (7.1) necesita aplicar esa etiqueta
  para despachar trabajo por la vía existente.
- **Consecuencia**: sin resolverlo, el motor puede preparar el WorkItem y su proyección
  GitHub, pero la activación seguiría siendo un clic humano — se conserva el cuello de
  botella exacto que #172 quiere eliminar.
- **Recomendación**: cuando el propietario autorice la implementación, enmendar el contrato
  para distinguir **iniciativa** (prohibida: la máquina no decide qué trabajo existe) de
  **transporte de una orden ya dada** (el motor aplica la etiqueta únicamente para
  WorkItems confirmados explícitamente por el propietario, 8.5, dejando la orden enlazada
  en la evidencia). El espíritu del límite — que nada arranque solo — se conserva.
- **Rama detenida**: el diseño del `START` de 7.1 queda condicionado a esta decisión.

### C2 — La supervisión del motor es «vigilancia periódica como motor» (contrato §9 + §9.1)

- **Decisión vigente**: contrato §9: prohibido «usar vigilancia periódica como **motor**
  del flujo»; §9.1 la excepciona solo para el reconciliador con cinco límites («no inicia
  trabajo», «no avanza un ciclo sano», «ante la duda, informa y no toca»). ADR-004 fija la
  misma frontera.
- **Conflicto**: el supervisor (componente 3) sondea `STATUS` y **actúa** (reintenta,
  sustituye, escala): es exactamente vigilancia periódica como motor. A la vez, la propia
  automatización dejó escrito que el atasco «solo lo cierra un observador EXTERNO, y el
  contrato operativo prohíbe hoy programarlo. Queda registrado como decisión pendiente»
  (`repair-sirius-work.yml:67-81`); la incidencia #138 formuló el principio («un proceso
  que muere no puede informar de su propia muerte»).
- **Consecuencia**: sin decisión, el Motor de Trabajo no puede existir como tal: se
  reduciría a otra colección de reacciones a eventos, con la misma clase de atascos.
- **Recomendación**: la prohibición se escribió para la automatización GitHub, donde el
  observador vivía dentro de lo observado y cada sondeo costaba minutos de Actions. El
  motor es la «decisión pendiente» que esos textos anuncian. Al autorizar la
  implementación, sustituir la prohibición general por sus límites reales: el motor
  supervisa y repara SUS Runs; sigue sin inventar trabajo (C1), sin fusionar y sin tocar
  ciclos que no gobierna; el reconciliador de Actions queda como respaldo de la vía GitHub.
- **Rama detenida**: las políticas concretas de reintento/sustitución tras `LOST` (3.3)
  quedan en propuesta, no en norma, hasta esa decisión.

### C3 — «Diseñar una arquitectura técnica multiagente» consta como no autorizado

- **Decisión vigente**: `docs/evolution/STATUS.md`, «No autorizado todavía»: «seleccionar
  proveedores o frameworks para agentes; **diseñar una arquitectura técnica multiagente**».
  En la misma línea: EV-006/EV-007 (delegación individual antes que multiagente;
  multiagente pospuesto), RECTOR §15 («introduce arquitectura multiagente sin evidencia» es
  señal de parada), `AGENTS.md:26` (no introducir coordinación de agentes antes de la
  puerta del contrato) y `AGENTS.md:36` (criterio de parada ante «introducir otro proceso,
  servidor, agente o base de datos» — el motor sería otro proceso con otro almacén).
- **Conflicto**: la incidencia #172, escrita por el propietario DESPUÉS de esos textos,
  ordena producir exactamente este diseño. Este documento existe por esa orden.
- **Consecuencia**: dos instrucciones del propietario apuntan en direcciones opuestas según
  la letra. Nota de alcance: este diseño se mantiene dentro de EV-006 en lo ejecutable —
  delegación supervisada a UN especialista por paso, sin equipos permanentes ni
  conversaciones abiertas entre agentes (RECTOR §9, 0.4) — pero el chasis descrito es, en
  la letra de evolución/STATUS, «arquitectura técnica» para agentes.
- **Recomendación**: tratar #172 como la autorización expresa y posterior para la FASE DE
  DISEÑO (la propia issue se declara «DISEÑO / RECONCILIACIÓN. NO AUTORIZA IMPLEMENTACIÓN»),
  y al aprobar este diseño, actualizar `docs/evolution/STATUS.md` para registrar la
  excepción con nombre (el Work Engine) en vez de dejar que la contradicción viva callada.
- **Rama detenida**: nada de este documento se presenta como cambio canónico; queda en
  PROPUESTO hasta esa reconciliación.

### C4 — (Heredada, no nueva) Workers que escriben vs. la propiedad de ADR-016

- **Decisión vigente**: ADR-016: «ningún trabajo que ejecute un modelo declara permisos de
  escritura» — propiedad probada por `tests/automation/test_auditor_workflow.py`.
- **Estado**: los tres roles del ciclo la incumplen desde siempre (implementador y
  corrector escriben; reciben el PAT), y la PR #171 ya los clasifica «prototipo declarado»
  y exentos por nombre en su registro. Este diseño hereda esa clasificación sin ampliarla:
  los Workers con escritura siguen siendo la excepción declarada, y el objetivo de largo
  plazo (escritura solo mediante PR revisable, nunca directa; credencial mínima por perfil)
  queda anotado como dirección, no como norma nueva.
- **No detiene ninguna rama**: se lista para que nadie la descubra después como sorpresa.

### C5 — «La incidencia es la fuente de verdad del trabajo» (contrato §2) frente al almacén del motor

- **Decisión vigente**: `AUTOMATION_OPERATING_CONTRACT.md` §2 y la propia plantilla
  (`.github/ISSUE_TEMPLATE/sirius-work-item.yml:10`): «Esta incidencia es la fuente de
  verdad del trabajo. Las etiquetas solo representan estados o eventos».
- **Conflicto**: este diseño traslada el estado canónico al almacén del motor (#172 §1.3
  lo pide: GitHub es «bus operativo provisional», «no la memoria definitiva de Sirius»); la
  incidencia pasaría a ser la **proyección** del WorkItem para la vía GitHub. Mientras
  ambos existan, alguien tiene que ser canónico: dos fuentes de verdad es exactamente la
  clase de duplicación que ADR-005 eliminó para V8.
- **Consecuencia**: sin decisión explícita, la migración de esa propiedad ocurriría de
  facto y en silencio al implementar el motor.
- **Recomendación**: decidirlo junto con C1/C2 en la misma enmienda del contrato: la
  fuente de verdad se traspasa al motor POR CLASE DE TRABAJO a medida que cada vía migra,
  con la incidencia como proyección obligatoria (y verificable) mientras la vía GitHub
  siga operativa. Hasta esa enmienda, la incidencia sigue siendo la fuente de verdad.
- **Rama detenida**: el diseño no declara canónico al almacén del motor; lo declara
  candidato, condicionado a esta decisión.

## 15. Incógnitas que requieren spike empírico (aisladas; no se resuelven por intuición)

| # | Incógnita | Por qué bloquea | Spike mínimo y desechable |
|---|---|---|---|
| I1 | ¿`STATUS` fiable sobre runs de Actions? (latencia, rate limits, estados intermedios, runs cancelados/expirados) | Calibra las cotas de `LOST` en la vía GitHub (7.1) | Sonda de solo lectura contra runs reales del repo: consultar N runs vivos/muertos y medir qué se observa y cuándo |
| I2 | Contrato real de GPT Researcher (entrada/salida, coste, clave LLM necesaria, calidad con brief mínimo) | Sin esto el Adapter 7.3 es papel; además exige decisión de gasto (clave API) | Ejecución aislada, sin repo, con un `ExportSafeBrief` de prueba sobre una pregunta con respuesta conocida; medir formato, fuentes y coste |
| I3 | Durabilidad del almacén del motor (proceso muere en mitad de una transición → ¿recupera sin perder ni duplicar?) | Es LA garantía del motor (3.5) | Esqueleto desechable: WorkItem + Run en SQLite, matar el proceso en cada punto del ciclo, verificar el barrido de recuperación |
| I4 | ¿Dónde corre el motor? (máquina del propietario Windows vs. siempre-encendido; disponibilidad real) | Decide la latencia de supervisión y el respaldo necesario | No es spike de código: dato + decisión del propietario; si hay dudas de viabilidad en Windows, prueba de 5 min del esqueleto de I3 |
| I5 | Valor real de `SIRIUS_CODEX_REVIEW_ENABLED` | Decide si la fase REVISAR de la vía GitHub es dual o simple hoy | Dato del propietario (leer la variable en Settings); no requiere spike |
| I6 | ¿La etiqueta aplicada por la identidad del motor despierta los workflows? | Condición técnica de C1 (además de la contractual) | Ya casi verificado por ADR-014/015 (el PAT dispara `issues: labeled`); prueba de un clic sobre una incidencia de humo si se quiere evidencia directa |

Regla: cada spike es desechable, aislado (sin tocar 0.1 ni canónicos) y responde UNA
pregunta que cambia una decisión. Ninguno se ejecuta en esta fase sin orden.

## 16. La primera vertical funcional (mapa, no plan)

Los 16 puntos de #172 §6 quedan cubiertos por: conversación y contexto sin WorkItem (8.5 y
9: puntos 1–3), creación confirmada (8.5: punto 4), investigación GPT Researcher (7.3, 8.3:
puntos 5–6), documento + revisión + reparación (8.1: puntos 7–9), tarea de repo por Claude
Code (7.1, 8.2: punto 10), Codex donde corresponda (7.2: punto 11), Auditor (8.4: punto
12), estado/espera/supervivencia/cancelación (3: puntos 13–15), y entrega sin propietario-
mensajero (3.4 ENTREGAR, 10: punto 16). Las clases mínimas de trabajo de #172 §6 caben en
CUATRO perfiles (ejecutor de repo, revisor, investigador, auditor) más los pasos
deterministas; no se crea un agente por punto.

El plan de implementación NO se escribe aquí: es la fase posterior a la aprobación
(método de #172 §10, paso 8).

## 17. Lo que este diseño NO garantiza

- No garantiza que el modo dual de Codex esté activo (I5), ni la viabilidad empírica de
  GPT Researcher (I2), ni el comportamiento de `claude-code-action` como producto externo.
- No garantiza la supervivencia a la caída del propio motor mientras está caído: esa
  ventana queda cubierta solo por el respaldo GitHub y por el propietario (3.5).
- No resuelve C1–C3: sin esas decisiones del propietario, la parte de despacho automático
  y supervisión activa queda en propuesta.
- No autoriza nada: implementación, spikes, instalaciones y enmiendas de contrato son
  decisiones posteriores, del propietario, con este documento como material.
