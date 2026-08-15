# Sirius Work Engine — Plan mínimo de implementación

- Estado: PROPUESTO. **Este plan no implementa nada**: ordena la implementación. Su
  aprobación es la fusión de la PR que lo introduce, por el propietario (ADR-020).
- Fecha: 2026-08-15
- Base: `main` = `54bb690` (PR #173 y #174 fusionadas). Diseño aprobado:
  `SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md`, `SIRIUS_WORK_ENGINE_INVENTARIO.md`,
  ADR-019. Encargo rector: incidencia #172.
- Nota de arranque de esta fase, publicada antes del primer commit:
  comentario en #172 (2026-08-15).

Reglas que este plan hereda y ningún bloque puede violar (arquitectura §2–§7):
motor determinista que posee el estado; Workers sustituibles tras
`START/STATUS/RESULT/CANCEL`; proyección determinista `WorkerRequest` con perfil
versionado; Capability Resolver con registro y **política global de egress** (red externa
+ contexto privado irrestricto: incompatibles, fail-closed); **cancelación en dos
tiempos**; **supervisor externo** al proceso supervisado; **persistencia detrás de
puerto**; reutilizar la automatización GitHub existente como primer Adapter, sin vías
paralelas; merge humano por `fusiona`; sin frameworks, proveedores ni base de datos
definitiva salvo dependencia demostrable.

---

## 1. La secuencia en una vista

Orden de dependencia real. Los spikes (S*) y la preparación de enmiendas pueden
solaparse con el bloque anterior cuando son independientes; lo que no se puede es
CONSUMIR su resultado antes de tenerlo.

```
E0  autorización de implementación + saneamiento documental (mini-PR, tipo #174) [DECISIÓN]
 └─ FASE A — núcleo, espejo e interacción (sin más decisiones; A1 puede empezar "mañana")
     A1 núcleo puro del motor (estados, transiciones, puerto, en-memoria)
     S1 spike I3: durabilidad (kill -9 → recuperación)                          [experiments/]
     A2 almacén durable de REFERENCIA según S1 + barrido de recuperación
     A3 espejo de solo lectura de la vía GitHub + contexto.recuperar v0
     A4 perfiles versionados + WorkerRequest + Resolver v0 + egress + PermissionEnvelope
     A5 interacción e intención v0 (compartida): conversación/consulta/exploración sin
        WorkItem, puerta determinista, creación/activación, presupuesto y corte,
        NEEDS_DECISION, escalado y notificación
        ── HITO M1: estado durable y consultable; se acabó la reconstrucción forense ──
 └─ E1a REGLA DE AUTORIDAD por clase (parte C5 del contrato v1.7)               [DECISIÓN]
 └─ FASE B — investigación (valor nuevo; NO depende de C1/C2)
     S2 spike I2: GPT Researcher aislado (sin repo)             [posible decisión de gasto]
     B1 adapter GPT Researcher + ExportSafeBrief + flujo investigación completo
        ── HITO M2: Sirius investiga de verdad desde una orden ──
 └─ FASE C — motor activo sobre la vía GitHub
     E1b enmienda del contrato v1.7: C1 (activación) + C2 (supervisión)         [DECISIÓN]
     S3 spike I1: bordes de STATUS de runs de Actions (solo lectura)
     C1 supervisión activa (LOST → reactivar / sustituir / escalar)
     C2 despacho end-to-end de programación (orden → ciclo completo → entrega)
     C3 documentación con Reviewer→Repair sobre el ciclo existente
     C4 Auditor como perfil del motor (superficie por etiqueta existente)
        ── HITO M3: vertical funcional completa de #172 §6 (incluye vía Codex ejecutada) ──
 └─ FASE D — canonicidad y servicio
     D1 conmutación de canonicidad de las clases con proyección GitHub (regla E1a)
     D2 servicio desatendido + representación física definitiva  [BLOQUEADO por I4]
     D3 (posterior, opcional) adapter Telegram                   [DECISIÓN nueva]
```

Qué demuestra cada eslabón y qué desbloquea:

- **A1–A3** demuestran lo que hoy no existe: estado del trabajo que sobrevive a procesos
  y sesiones, consultable («¿qué pasó con X?») sin leer GitHub a mano. Desbloquea todo lo
  demás: sin almacén ni espejo no hay supervisión ni despacho.
- **A4** demuestra que los perfiles gobiernan a los Workers sin acoplarse a runtimes
  (la proyección reproduce el prompt real del workflow implementador), y que el egress es
  imposible de saltar en vez de improbable. Desbloquea la Fase B (el investigador necesita
  perfil + egress) y la C (el despacho necesita WorkerRequest).
- **A5** demuestra la Capa 1 completa de #172 §6.1-6.4 (conversar, consultar el pasado,
  explorar y convertir una intención en trabajo) y aporta el gobierno que ningún Worker
  externo puede estrenarse sin él: presupuesto con corte determinista, `NEEDS_DECISION`,
  escalado y notificación. **B1 y C2 lo CONSUMEN; ninguno de los dos reimplementa la
  puerta de intención ni la interfaz.**
- **E1a** fija la regla de autoridad ANTES del primer trabajo nativo: ningún WorkItem
  nace sin autoridad definida (ver §4).
- **B1** demuestra la promesa diferencial de #172 §6: investigar desde una orden, con
  frontera mecánica. Se coloca ANTES que la Fase C a propósito: da valor nuevo sin
  depender de la activación ni de la supervisión de la vía GitHub.
- **C1–C2** demuestran el fin del propietario-mensajero en programación: nadie desatasca
  a mano, nadie transporta contexto ni activa etiquetas.
- **C3–C4** completan las clases de trabajo de la vertical (documentación, auditoría)
  REUTILIZANDO el ciclo y la superficie del Auditor existentes.
- **D1–D2** convierten el resultado en régimen: canonicidad conmutada sin doble autoridad,
  motor en servicio sin niñera y representación física definitiva ya decidida.

## 2. Bloques en detalle

Formato de cada bloque: objetivo / dependencia real / ficheros o componentes previsibles /
prueba de terminado / riesgo principal / qué puede hacerse automáticamente / decisión
humana material previa.

### E0 — Autorización de implementación + saneamiento documental

- **Objetivo**: dos cosas en la misma mini-PR acotada:
  1. **Autorizar**: extender la excepción registrada por la PR #174 en
     `docs/evolution/STATUS.md` de «solo la fase de diseño» a «implementación según el
     plan aprobado (ADR-020)», manteniendo el resto de prohibiciones
     (frameworks/proveedores no aprobados, multiagente abierto, permisos generales).
     Satisface también el criterio de parada de `AGENTS.md` («introducir otro proceso,
     servidor, agente o base de datos») mediante decisión explícita del propietario.
  2. **Sanear la condición documental**: ADR-019 sigue con `Estado: PROPUESTO` pese a que
     la fusión de la PR #173 por el propietario **es** su aprobación según su propia
     cabecera (verificado en `main` = `54bb690`), y la línea de la excepción en
     `docs/evolution/STATUS.md` lo cita como «(ADR-019, PROPUESTO)». E0 corrige ambos a
     APROBADO con la fecha de fusión. Es la familia de deriva que
     `WORK_PROCESS_AUDIT.md` ya registró (PROC-011: los siete primeros ADR siguieron
     «PROPUESTO» tras fusionarse). **Acotado a ADR-019 y a esa línea**: un barrido
     general sobre ADR-001..018 sería otra decisión, y se propone aparte si el
     propietario quiere.
- **Dependencia real**: la fusión de la PR de este plan (aprueba ADR-020 y la secuencia).
- **Ficheros**: `docs/evolution/STATUS.md` (una línea ampliada) y la cabecera de
  `docs/decisions/ADR-019-…md`. Mini-PR tipo #174.
- **Prueba de terminado**: la excepción menciona implementación + ADR-020; ADR-019 y la
  cita de STATUS dicen APROBADO con fecha; pruebas documentales en verde.
- **Riesgo principal**: redactar de más y autorizar de más; se mitiga copiando el patrón
  acotado de #174 y limitando el saneamiento a ADR-019.
- **Automatizable**: la redacción de la mini-PR sí; la fusión es del propietario.
- **Decisión humana previa**: SÍ — es en sí misma la decisión. Es la ÚNICA decisión
  material pendiente antes del primer bloque de código (junto con aprobar este plan).

### A1 — Núcleo puro del motor

- **Objetivo**: entidades `WorkItem` y `Run` con TODAS las transiciones del diseño
  (arquitectura §3): estados de WorkItem, `PREPARED→DISPATCHED→RUNNING→FINISHED` con
  desenlaces, cancelación en dos tiempos, `LOST` por cota, cambio de alcance versionado,
  reintento/sustitución como Runs nuevos; puerto de persistencia con implementación en
  memoria; diario de eventos append-only. Sin red, sin GitHub, sin hilos.
- **Dependencia real**: E0. Nada más: es el bloque que puede construirse mañana.
- **Ficheros**: paquete nuevo `src/sirius_engine/` (dominio + puertos + en-memoria),
  `tests/engine/`. Fuera de `src/sirius/` (frontera aprobada); al vivir bajo `src/`,
  `quality.yml` lo cubre TAL CUAL (`ruff`, `mypy src tests`, `pytest`) sin tocar ningún
  workflow. Alta del paquete en `pyproject.toml`. Prueba de frontera nueva: `sirius` y
  `sirius_engine` no se importan entre sí.
- **Prueba de terminado**: suite de propiedades en verde, con mutaciones vistas fallar:
  transición ilegal imposible; un Run cancelado sin terminal remoto NUNCA pasa a
  `CANCELLED`; ningún despacho sobre recurso con cancelación sin confirmar; el diario
  reconstruye cualquier secuencia.
- **Riesgo principal**: sobre-modelar. Mitigación: solo lo que la arquitectura §3 define;
  nada especulativo.
- **Automatizable**: sí — puede ejecutarse como Work Items del ciclo `sirius:*` actual
  (implementador/revisor/corrector de siempre; el runner no está sujeto a la allowlist de
  sesiones locales).
- **Decisión humana previa**: ninguna (E0 ya tomada).

### S1 — Spike I3: durabilidad del almacén (desechable)

- **Objetivo**: decidir la representación física y el patrón de escritura: proceso matado
  (`kill -9`) en CADA punto del ciclo de una transición → al rearrancar, ni pérdida ni
  duplicación.
- **Dependencia real**: A1 (usa su dominio y su puerto).
- **Ficheros**: `experiments/work_engine_spike_i3/` (desechable; SQLite u otro medio local
  VALE para el spike sin ser decisión de arquitectura).
- **Prueba de terminado**: matriz punto-de-muerte × resultado publicada en la incidencia
  del spike; decisión de representación registrada (una línea en el ADR de cierre de fase
  o en la incidencia).
- **Riesgo principal**: falso verde por matar «entre» transiciones y no «dentro»;
  mitigación: puntos de corte inyectados, no azar.
- **Automatizable**: sí, como Work Item; es código desechable con criterio observable.
- **Decisión humana previa**: ninguna.

### A2 — Almacén durable **de referencia** + barrido de recuperación

- **Objetivo**: una implementación durable del puerto —**de referencia, no definitiva**—
  con el patrón de escritura que S1 demostró seguro, más el barrido de arranque
  (arquitectura §3.5): reconciliar cada Run abierto contra el mundo y recalcular el
  siguiente paso.
- **Frontera explícita (ADR-019)**: la representación física **definitiva** depende de
  I3 **e I4** — el dónde corre el motor condiciona el medio (permisos de escritura,
  concurrencia, copias, disponibilidad). A2 no la fija: entrega un adaptador que cumple el
  puerto y unas pruebas de recuperación que cualquier sustituto deberá pasar. **La
  fijación definitiva ocurre en D2**, cuando I4 esté resuelta — **salvo que el propietario
  adelante I4**, en cuyo caso A2 puede fijar ya la representación y D2 se limita al
  servicio.
- **Dependencia real**: A1 + resultado de S1.
- **Ficheros**: `src/sirius_engine/` (adaptador de persistencia de referencia),
  `tests/engine/` (la prueba del spike, convertida en prueba estable del repositorio).
- **Prueba de terminado**: la prueba de recuperación integrada en la suite y vista fallar
  con la durabilidad rota (mutación); la suite se escribe **contra el puerto**, no contra
  el adaptador, para que valga tal cual con otra representación.
- **Riesgo principal**: que «de referencia» se convierta en definitivo por inercia;
  mitigación: la prueba contra el puerto y la revisión explícita de la representación en
  D2 (o al adelantarse I4).
- **Automatizable**: sí (Work Items del ciclo).
- **Decisión humana previa**: ninguna. (I4 no bloquea aquí; bloquea la fijación en D2.)

### A3 — Espejo de solo lectura de la vía GitHub + `contexto.recuperar` v0

- **Objetivo**: proyectar el estado real de la vía GitHub dentro del motor SIN escribir
  nada: incidencia + etiquetas + marcadores (`sirius-verdict`, `sirius-quality`,
  `sirius-round`, `Head SHA`, `PR abierta:`) + estado del run de Actions → WorkItem/Run
  espejo, marcado NO-autoritativo. Capacidad `contexto.recuperar` v0 con tres proveedores
  deterministas: árbol del repo (ficheros/ADRs/docs), incidencias/PRs (lectura robusta con
  el filtro de autores de confianza ya existente), historial git.
- **Dependencia real**: A2. (El espejo pasivo no necesita S3/I1: sin cotas de acción no
  hay `LOST` que declarar; observa y registra.)
- **Ficheros**: `src/sirius_engine/` (adapter GitHub de lectura; reutiliza los contratos
  de `scripts/automation/sirius_issue.sh` — como referencia de semántica o invocándolo,
  lo que menos duplique), `tests/engine/` con fixtures de hilos reales.
- **Prueba de terminado**: el espejo reconstruye fielmente el ciclo COMPLETO de la
  incidencia histórica #148 (implementación → Quality → dual → rondas → fusión manual →
  completado) desde fixtures, y una lectura viva de una incidencia actual coincide con
  GitHub; «¿qué pasó con B12e?» se responde desde el motor con referencias.
- **Riesgo principal**: divergencia silenciosa espejo↔GitHub; mitigación: el espejo
  siempre lleva instante-de-lectura y origen, y NUNCA se presenta como autoridad (la
  autoridad sigue siendo la incidencia hasta D1 — regla C5).
- **Automatizable**: sí (Work Items del ciclo).
- **Decisión humana previa**: ninguna.

### A4 — Perfiles versionados + WorkerRequest + Resolver v0 + egress + PermissionEnvelope

- **Objetivo**: los tres prompts de rol + el runbook del Auditor convertidos en Agent
  Profiles versionados (misión/procedimiento/capacidades/permisos/contrato E-S, sin
  nombres de herramienta); proyección determinista `WorkerRequest` (arquitectura §5.1),
  incluido el **`PermissionEnvelope`** (perfil de permisos efectivo del Run: qué
  capacidades, qué escritura, qué red — deny-by-default, calculado por el motor, nunca
  declarado por el Worker); Capability Resolver v0 con registro versionado (heredero del
  patrón `registro_de_acciones.yml` de la PR #171); validador de egress fail-closed
  (§6.1) con clasificación por fragmento.
- **Cómo llega un perfil a los workflows GitHub existentes** (sin vía paralela): los
  perfiles viven en el árbol como datos versionados; la proyección del Adapter escribe en
  la **incidencia** (que ya es el canal del que se alimentan los workflows) un campo
  declarativo `Perfil: <ref>@<version>` dentro del cuerpo del Work Item, junto al resto de
  secciones de la plantilla. El paso de construcción de prompt de cada workflow —que hoy
  concatena una ruta fija (`prompts/implementer.md`, `prompts/reviewer.md`,
  `prompts/corrector.md`)— pasa a resolver **esa** ruta desde el campo declarado, con la
  ruta actual como valor por defecto si el campo no está. Es una parametrización de un
  paso existente, no un carril nuevo; retrocompatible con toda incidencia que no declare
  perfil. **Ese cambio de workflow lo hace una sesión interactiva, nunca la automatización
  (ADR-002)**, y se ejecuta en el bloque que primero lo necesita (**C3**), no aquí: A4
  entrega la proyección, el campo y las pruebas.
- **Dependencia real**: A1 (tipos). Independiente de A3; puede solaparse.
- **Ficheros**: `src/sirius_engine/` (proyección, resolver, egress, PermissionEnvelope),
  `docs/implementation/work_engine/perfiles/` o equivalente (perfiles como datos
  versionados), `tests/engine/`.
- **Prueba de terminado**: (1) propiedad misma-entrada → misma-petición; (2) la
  proyección del perfil implementador reproduce el prompt que hoy monta
  `implement-sirius-work.yml` para una incidencia fixture — prueba de no-divergencia con
  la vía existente; (3) egress: un fragmento sin clasificación exportable IMPIDE `START`
  (mutación vista fallar); (4) capacidad no registrada → no resuelta; (5) un
  `PermissionEnvelope` sin la capacidad pedida impide la resolución (no la degrada).
- **Riesgo principal**: perfiles que digan más que los prompts reales (deriva); la prueba
  (2) lo hace estructural, no vigilado.
- **Automatizable**: sí (Work Items del ciclo).
- **Decisión humana previa**: ninguna.

### A5 — Interacción e intención v0 (bloque COMPARTIDO; lo consumen B1 y C2)

- **Objetivo**: la Capa 1 y el gobierno del trabajo, una sola vez y para todas las clases:
  1. **Conversar, consultar y explorar SIN crear WorkItem** (#172 §6.1-6.3), apoyado en
     `contexto.recuperar` de A3 para responder «¿qué pasó con X?».
  2. **Interpretación de intención** [M] + **puerta determinista** (arquitectura §8.5):
     orden inequívoca → crea **y activa**; ambigüedad → pregunta o no crea;
     sensible/material → confirma o escala.
  3. **Creación/activación del WorkItem** con su proyección según la clase.
  4. **Gobierno previo al primer Worker externo**: presupuesto por WorkItem/Run con
     **corte determinista** al agotarse, `NEEDS_DECISION` con la lista cerrada de causas
     (arquitectura §10), **escalado** al propietario y **notificación** por la interfaz
     activa; toda escalada llega con contexto suficiente para decidir sin reconstruir.
  5. **Interfaz v0**: sesión/CLI, sin estado propio (Telegram será otro adapter, D3).
- **Dependencia real**: A2 (estado durable) + A3 (contexto) + A4 (permisos/egress para
  poder calcular el sobre de permisos de un trabajo). **Ningún Worker externo se estrena
  antes de este bloque**: sin presupuesto, corte y escalado, un Worker externo puede
  gastar sin freno y fallar sin cauce.
- **Ficheros**: `src/sirius_engine/` (intención, puerta, presupuesto, escalado,
  notificación, interfaz v0), `tests/engine/`.
- **Prueba de terminado**: (1) una conversación de varios turnos con consultas al pasado
  NO crea ningún WorkItem; (2) una orden inequívoca crea y activa sin segunda
  confirmación; (3) una petición ambigua no crea trabajo; (4) agotar el presupuesto
  simulado corta el Run y produce `NEEDS_DECISION` con notificación —visto fallar con el
  corte desactivado (mutación)—; (5) una causa de la lista cerrada de §10 escala y ninguna
  otra lo hace.
- **Riesgo principal**: que la puerta se vuelva un interrogatorio (el defecto G1 ya
  corregido en el diseño); mitigación: las pruebas (2) y (3) fijan el comportamiento en
  ambas direcciones.
- **Automatizable**: sí (Work Items del ciclo).
- **Decisión humana previa**: ninguna.

**HITO M1** (fin de Fase A): el propietario **conversa con Sirius**, pregunta por
cualquier trabajo pasado o vivo y obtiene estado con evidencia de un almacén que
sobrevive a reinicios, y puede convertir una orden en WorkItem con presupuesto y cauce de
escalado. Nada escribe aún en GitHub y ningún Worker externo se ha estrenado.

### E1a — Regla de autoridad por clase (parte C5 del contrato v1.7)

- **Objetivo**: fijar, ANTES de que nazca el primer trabajo nativo del motor, quién es la
  autoridad de cada WorkItem, sin ningún estado ambiguo. Redacción operativa en §4. En una
  frase: **las clases con proyección en la vía GitHub (programación, auditoría) siguen
  teniendo la incidencia como fuente de verdad hasta su conmutación; las clases nativas
  del motor (conversación/exploración, investigación, documental no publicada) nacen
  canónicas en el almacén del motor**, y su reflejo en GitHub —si lo hay— es informativo y
  así se etiqueta.
- **Dependencia real**: fusión de este plan. Debe estar fusionada **antes de B1**, porque
  B1 crea el primer WorkItem que no existe en GitHub.
- **Ficheros**: `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` (apertura de la
  v1.7 con la regla de autoridad; C1 y C2 llegan después, en E1b, a la misma versión).
- **Prueba de terminado**: contrato con la regla; ninguna clase sin autoridad asignada
  (tabla completa en §4); pruebas documentales en verde.
- **Riesgo principal**: enmendar de más y colar aquí la activación o la supervisión;
  mitigación: E1a se limita a la autoridad — C1/C2 quedan explícitamente para E1b.
- **Automatizable**: la redacción sí; la decisión es del propietario.
- **Decisión humana previa**: SÍ (primera de las dos enmiendas).

### S2 — Spike I2: GPT Researcher aislado (desechable)

- **Objetivo**: medir el contrato real de GPT Researcher SIN repo: instalación en entorno
  aislado del spike, un `ExportSafeBrief` de prueba sobre pregunta con respuesta
  conocida; formato de salida, fuentes, calidad, y COSTE real (hoy NO VERIFICADO). Probar
  primero el camino sin gasto (modelo local vía Ollama, camino ya medido en
  `BLOQUE_B_SUSCRIPCIONES_O_CLAVES.md`); si solo funciona con clave de pago, eso es un
  dato que sube al propietario.
- **Dependencia real**: A4 (egress y forma del brief). Nada de la Fase C.
- **Ficheros**: `experiments/work_engine_spike_i2/` (desechable).
- **Prueba de terminado**: informe del spike en su incidencia: contrato de E/S observado,
  coste medido, decisión de adaptador viable/no viable.
- **Riesgo principal**: que el resultado dependa del modelo subyacente y no del
  adaptador; mitigación: probar ≥2 configuraciones si el coste lo permite.
- **Automatizable**: parcialmente; la instalación aislada puede exigir sesión.
- **Decisión humana previa**: SOLO SI el spike demuestra que exige gasto (clave LLM):
  escalado por presupuesto antes de continuar. Si el camino local basta: ninguna.

### B1 — Adapter GPT Researcher + flujo de investigación completo

- **Objetivo**: primer Worker externo real tras el contrato: `START` lanza el proceso
  aislado SIN credenciales ni árbol del repo, solo el brief validado; `STATUS` observa el
  proceso; `RESULT` normaliza informe+fuentes+incertidumbres a WorkResult; `CANCEL`
  termina el proceso (aislamiento demostrado → `CANCELLED` directo). Flujo entero:
  orden → puerta de intención → WorkItem clase investigación → brief (egress fail-closed)
  → Run → COMPROBAR (fuentes presentes/accesibles, trazabilidad) → entrega reconciliada
  con el contexto privado dentro de Sirius.
- **Consume A5, no lo reimplementa**: la orden, la puerta de intención, la creación del
  WorkItem, el presupuesto con corte, el escalado y la notificación son los de A5. B1
  aporta únicamente el Adapter, el brief y las comprobaciones propias de investigación.
- **Dependencia real**: A2 + A4 + **A5** + **E1a** (autoridad del WorkItem nativo) + S2.
  **No depende de C1/C2 (activación ni supervisión de la vía GitHub)**: no toca etiquetas
  `sirius:*` ni sus ciclos.
- **Ficheros**: `src/sirius_engine/` (adapter + flujo), perfil investigador-externo,
  `tests/engine/` (con doble simulado del proceso; el real solo en prueba manual
  documentada).
- **Prueba de terminado**: una pregunta real del propietario respondida de punta a punta
  desde una sola orden, con fuentes y con el brief y las consultas en la evidencia; la
  prueba de egress del flujo completo vista fallar con un brief envenenado (mutación).
- **Riesgo principal**: calidad de investigación decepcionante aunque el mecanismo
  funcione; mitigación: es un Worker sustituible — el flujo, el brief y la frontera valen
  para cualquier investigador que lo reemplace.
- **Automatizable**: el código sí (Work Items); la prueba real de punta a punta, con el
  propietario.
- **Decisión humana previa**: la de gasto si S2 la levantó; ninguna más.

**HITO M2**: Sirius investiga de verdad — #172 §6.5-6.6 cumplidos — sin haber tocado la
activación ni la supervisión de la vía GitHub.

### E1b — Enmienda del contrato operativo v1.7 (C1 + C2)

- **Objetivo**: cerrar la v1.7 abierta por E1a con las dos contradicciones que la Fase C
  consume (arquitectura §14):
  - **C1**: distinguir iniciativa (prohibida) de transporte de una orden ya dada: el
    motor puede aplicar `sirius:implement-requested` SOLO para WorkItems con orden
    explícita del propietario registrada y enlazada en la evidencia.
  - **C2**: el supervisor del motor queda autorizado con límites: supervisa y repara SUS
    Runs; no inventa trabajo; no fusiona; no toca ciclos que no gobierna; el
    reconciliador de Actions queda como respaldo de la vía GitHub.
  (La parte C5 —autoridad y su conmutación— ya está en la v1.7 desde E1a.)
- **Dependencia real**: E1a fusionada; conviene tras M2 (evidencia de que el motor existe
  y aporta), pero puede prepararse en paralelo a la Fase B.
- **Ficheros**: `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` (cierre de la
  v1.7, con su registro §10). PR documental propia, revisada y fusionada por el
  propietario.
- **Prueba de terminado**: contrato v1.7 completo y fusionado; las pruebas estructurales
  que citan §9.1 (RECON-STUCK-007/013) siguen en verde o actualizadas en la misma PR con
  justificación.
- **Riesgo principal**: enmendar de más; mitigación: solo esos dos puntos, con el texto
  propuesto derivado literalmente de §14 de la arquitectura.
- **Automatizable**: la redacción sí; la decisión es del propietario.
- **Decisión humana previa**: SÍ (segunda enmienda; con E0 y E1a completan las decisiones
  documentales del plan hasta D1/D2).

### S3 — Spike I1: bordes de `STATUS` sobre runs de Actions (desechable, solo lectura)

- **Objetivo**: medir lo que decide las cotas de `LOST`: latencia real de estados,
  comportamiento de runs cancelados/expirados, rate limits, y con ello cadencia de sondeo
  y cotas por etiqueta de estado.
- **Dependencia real**: A3 (espejo que consultar). Independiente de E1b; puede solaparse.
- **Ficheros**: `experiments/work_engine_spike_i1/` (sonda de solo lectura).
- **Prueba de terminado**: tabla medida borde × observación en su incidencia; cotas
  propuestas para C1.
- **Riesgo principal**: medir solo el camino feliz; mitigación: incluir a propósito runs
  cancelados y un run expirado histórico.
- **Automatizable**: sí.
- **Decisión humana previa**: ninguna.

### C1 — Supervisión activa de la vía GitHub

- **Objetivo**: el motor deja de solo mirar: cotas de S3 → Run `LOST` → acción según
  política del paso: reactivación (la receta exacta del reconciliador: reponer lo que el
  consumo retiró), sustitución o escalado; coordinación con el reconciliador (el motor
  respeta sus marcadores; el reconciliador queda de respaldo, sin cambiarlo).
- **Dependencia real**: A3 + S3 + **E1b (C2)**. Sin la v1.7 completa este bloque NO
  empieza.
- **Ficheros**: `src/sirius_engine/` (supervisor + políticas), `tests/engine/`.
- **Prueba de terminado**: en una incidencia de humo, un run matado a mitad queda
  reactivado o escalado por el motor sin intervención humana, con el episodio completo en
  el diario; prueba de no-carrera con el reconciliador (los dos observando el mismo
  atasco → una sola acción).
- **Riesgo principal**: carreras con la automatización existente; mitigación: la misma
  disciplina de marcadores e idempotencia que ya usa `sirius_reconcile.sh`, mas la regla
  de recurso mutable de la cancelación en dos tiempos.
- **Automatizable**: el código sí; la prueba de humo, supervisada.
- **Decisión humana previa**: E1b fusionada (ya contada ahí).

### C2 — Despacho end-to-end de programación

- **Objetivo**: cerrar el círculo del propietario-no-mensajero en la clase programación:
  puerta de intención **de A5** → incidencia generada desde la plantilla (proyección del
  WorkPackage, con el campo `Perfil:` de A4) → etiqueta de activación aplicada por la
  identidad del motor (**smoke test I6** como primer paso del bloque) → ciclo completo
  existente (implementar → Quality → revisión → reparar) seguido por el espejo y el
  supervisor → entrega del resultado con evidencia. El merge sigue siendo humano
  (`fusiona`), sin cambios.
- **Consume A5, no lo reimplementa**: interfaz, intención, puerta, presupuesto y escalado
  vienen de A5; C2 aporta el despachador y la escritura mínima en GitHub.
- **Dependencia real**: C1 + **E1b (C1 contractual)** + A4 + **A5**.
- **Ficheros**: `src/sirius_engine/` (despachador + adapter de escritura mínima: crear
  incidencia, aplicar etiqueta de activación).
- **Prueba de terminado**: un encargo pequeño real recorre TODO el ciclo desde una única
  orden del propietario, que no toca GitHub hasta el `fusiona`; el diario permite
  reconstruir el episodio completo. **La vía Codex debe haberse ejercitado de verdad**:
  al menos un ciclo despachado por el motor pasa por una revisión dual real (Claude +
  Codex, agregación determinista) con su resultado en la evidencia. **I5** (valor de
  `SIRIUS_CODEX_REVIEW_ENABLED`) no bloquea la construcción de ningún bloque, pero es
  aquí donde deja de ser un dato ignorable: si la bandera está apagada, se enciende para
  esa demostración —o se registra por escrito la decisión de no hacerlo, y entonces M3 se
  declara con esa carencia dicha, no en silencio.
- **Riesgo principal**: el arranque doble (puerta de validación + implementador ya se
  revalidan solos) interactuando con un tercer actor; mitigación: el motor usa
  exactamente la vía del propietario (misma etiqueta, misma plantilla), sin atajos.
- **Automatizable**: el código sí; el encargo de demostración, real.
- **Decisión humana previa**: ninguna nueva (E0, E1a y E1b ya tomadas). Encender la
  bandera de Codex para la demostración, si estuviera apagada, es un acto operativo del
  propietario, no una decisión de arquitectura.

### C3 — Documentación + Reviewer→Repair

- **Objetivo**: la clase documental completa REUTILIZANDO el ciclo `sirius:*`: Work Item
  documental con validaciones deterministas de documento (rutas citadas existen,
  referencias resuelven, formato) como comandos de su campo «Validaciones»; revisor
  independiente con el contrato de observación existente; reparación automática;
  entrega.
- **Selección de perfil por la vía existente** (el mecanismo de A4, aquí es donde se
  ejerce): el WorkItem documental declara `Perfil: revisor-documental@vN` en su cuerpo; el
  paso de construcción de prompt de `review-sirius-work.yml` resuelve la ruta del perfil
  desde ese campo en vez de la ruta fija `prompts/reviewer.md`, conservando esa ruta como
  valor por defecto. Cambio de una línea de resolución en un paso que ya existe —
  **hecho en sesión interactiva, nunca por la automatización (ADR-002)**, con su prueba
  estructural en `tests/automation/`. No se crea ningún workflow ni carril nuevo: el
  revisor documental es el mismo revisor con otro perfil.
- **Dependencia real**: C2 (despacho) + A4 (perfiles y campo declarativo) — el ciclo, el
  revisor y el corrector ya existen.
- **Ficheros**: perfil documentalista + perfil revisor documental; un comprobador de
  documentos como script determinista NUEVO (se invoca desde las validaciones del Work
  Item); una edición mínima del paso de prompt de `review-sirius-work.yml`; `tests/` del
  comprobador y prueba estructural del paso editado.
- **Prueba de terminado**: un documento real creado, revisado con `CHANGES_REQUIRED` y
  observaciones estructuradas por el **perfil revisor documental seleccionado desde la
  incidencia**, reparado sin intervención y entregado; las validaciones documentales
  vistas fallar con un defecto sembrado (mutación); una incidencia SIN campo `Perfil:`
  sigue usando el prompt de siempre (prueba de retrocompatibilidad).
- **Riesgo principal**: revisar documentos con criterios de código; mitigación: perfil
  revisor documental propio, no el de código.
- **Automatizable**: sí, íntegramente como Work Items.
- **Decisión humana previa**: ninguna.

### C4 — Auditor como perfil del motor

- **Objetivo**: la clase auditoría dentro del motor SIN duplicar la superficie: una orden
  crea el WorkItem de auditoría; el adapter aplica `auditoria:solicitada` (fuera de
  `sirius:*`, como manda ADR-016); el espejo recoge el informe publicado; la síntesis se
  entrega al propietario. Los hallazgos NO se convierten en trabajo automáticamente
  (ADR-010): cada uno puede originar una nueva orden del propietario.
- **Dependencia real**: C2 (despacho por etiqueta con identidad del motor). La superficie
  del Auditor NO se modifica.
- **Ficheros**: perfil auditor (referencia al runbook existente
  `AUDITOR_AGENT_V0.md`), adapter mínimo en `src/sirius_engine/`.
- **Prueba de terminado**: una auditoría lanzada desde una orden, informe entregado como
  síntesis en la interfaz, evidencia enlazada; cero escrituras nuevas en la superficie
  del Auditor.
- **Riesgo principal**: tocar el carril del Auditor «de paso»; mitigación: prohibido en
  el bloque; cualquier mejora del carril (p. ej. las de la PR #171) es una PR aparte.
- **Automatizable**: sí.
- **Decisión humana previa**: ninguna.

**HITO M3**: vertical funcional completa — los 16 puntos de #172 §6 cubiertos (la
interfaz v0 es CLI/sesión; Telegram queda como D3). **Criterio de cierre explícito**: M3
no se declara completo sin que la vía Codex se haya **ejecutado de verdad** al menos una
vez en un ciclo despachado por el motor (punto 11 de #172 §6), con su evidencia; si el
propietario decide no ejercitarla, esa carencia se escribe en el registro del hito.

### D1 — Conmutación de canonicidad de las clases con proyección GitHub

- **Objetivo**: ejecutar la parte de la regla de E1a que queda pendiente: conmutar
  programación, documental publicada y auditoría desde «incidencia canónica» a «motor
  canónico + proyección obligatoria», con verificador de proyección motor↔incidencia.
  (Las clases nativas del motor NO pasan por aquí: nacieron canónicas por E1a.)
- **Dependencia real**: E1a (regla) + clase estable: documental tras C3; programación
  tras el periodo de C1+C2 sin intervención manual (umbral en §4).
- **Ficheros**: `src/sirius_engine/` (verificador de proyección), registro de conmutación
  (dato versionado).
- **Prueba de terminado**: verificador en verde N días por clase (N en §4) + conmutación
  registrada; el episodio de divergencia sembrado dispara alarma (mutación).
- **Riesgo principal**: doble autoridad ambigua; mitigación: la regla de §4 hace la
  autoridad una función total (clase → autoridad) sin estados intermedios.
- **Automatizable**: el verificador sí; cada conmutación la registra el propietario.
- **Decisión humana previa**: la conmutación de cada clase (acto simple, previsto en E1a).

### D2 — Servicio desatendido + representación física definitiva — BLOQUEADO por I4

- **Objetivo**: dos cosas que I4 gobierna a la vez:
  1. el motor en régimen: proceso bajo supervisión externa con reinicio automático
     (requisito de despliegue de la arquitectura §3.5), arrancando el barrido de
     recuperación en cada arranque;
  2. **fijar la representación física definitiva del almacén** (ADR-019: depende de I3
     e I4), confirmando o sustituyendo el adaptador de referencia de A2 según lo que el
     entorno elegido permita. Si el propietario adelanta I4, esta parte se adelanta con
     ella y D2 se queda solo con el servicio.
- **Dependencia real**: **I4** (dónde corre el motor). Este es el punto EXACTO donde I4
  bloquea; hasta aquí, el motor corre atendido en sesiones sobre el adaptador de
  referencia y nada anterior se detiene por ello.
- **Ficheros**: unidad de servicio/process manager según I4; adaptador definitivo si
  sustituye al de referencia; guía de operación.
- **Prueba de terminado**: matar el proceso en horario desatendido → reinicio automático
  + recuperación sin pérdida, verificado dos veces; si cambia la representación, la suite
  de recuperación de A2 (escrita contra el puerto) pasa sin modificarse.
- **Riesgo principal**: entorno Windows real (la clase de hueco que ya bloqueó V8.2/V8.3);
  mitigación: prueba de 5 minutos del esqueleto bajo el supervisor elegido antes de dar
  I4 por resuelta.
- **Automatizable**: parcialmente; la instalación del servicio es de máquina real.
- **Decisión humana previa**: I4 (dato + decisión de despliegue).

### D3 — Adapter Telegram (posterior, opcional)

- **Objetivo**: primera interfaz sustituible no-CLI (texto/voz/archivos), sin estado, con
  las operaciones de la Capa 1.
- **Dependencia real**: M3 (que haya motor que exponer); decisión del propietario.
- **Decisión humana previa**: SÍ — superficie externa nueva + credencial de bot; queda
  explícitamente FUERA del alcance aprobado por este plan (se propondrá con su propia
  mini-decisión cuando llegue).

## 3. C1, C2, C5: cómo y cuándo se enmiendan

Una sola versión del contrato (v1.6 → **v1.7**), en **dos entregas** colocadas cada una
justo antes del primer bloque que la consume. La razón de partirla es exacta: **C5 se
consume mucho antes que C1 y C2**. El primer WorkItem nativo del motor nace en B1 (una
investigación no existe como incidencia del ciclo), y un WorkItem sin autoridad definida
es precisamente el estado ambiguo que la regla debe impedir.

- **E1a — regla de autoridad (C5), antes de B1.** Texto operativo en §4. No toca
  activación ni supervisión: la vía GitHub sigue funcionando exactamente igual.
- **E1b — activación y supervisión (C1 y C2), antes de la Fase C.** C1 = transporte de
  una orden registrada, nunca iniciativa; C2 = supervisor autorizado con límites
  nombrados y reconciliador como respaldo. Texto derivado de la arquitectura §14.
- **Cómo**: cada entrega es una PR documental del propietario sobre
  `AUTOMATION_OPERATING_CONTRACT.md`, registrada en su §10; las pruebas estructurales que
  fijan §9.1 (RECON-STUCK-007/013) se actualizan en la misma PR si el texto las mueve.
- **Guardia del plan**: B1 declara E1a como dependencia dura; C1 y C2 declaran E1b. La
  conmutación de las clases con proyección GitHub (D1) consume la parte de E1a que queda
  viva después de M3.

## 4. Migración de canonicidad sin doble autoridad (diseño)

Regla única: **la autoridad es una función total por clase de trabajo, con un solo
conmutador fechado por clase**; no existe estado intermedio y **ningún WorkItem puede
nacer sin autoridad asignada**. La regla entra en vigor en **E1a**, antes del primer
trabajo nativo del motor (B1).

**Tabla de autoridad al entrar en vigor E1a** (cubre TODAS las clases de #172 §6; sin
huecos):

| Clase de trabajo | ¿Existe en la vía GitHub? | Autoridad desde E1a | Conmuta en D1 |
|---|---|---|---|
| conversación / exploración / consulta | no (no crea WorkItem) | motor (o ningún WorkItem) | — |
| investigación | no | **motor, desde su nacimiento** | — |
| documental no publicada | no | **motor** | — |
| documental publicada (PR en el repo) | sí | incidencia | sí |
| programación | sí | incidencia | sí |
| auditoría | sí (etiqueta propia) | incidencia | sí |
| reparación / espera / cancelación | son fases o estados, no clases | la de su WorkItem | — |

1. **Antes de la conmutación de una clase con proyección GitHub**: la incidencia es la
   fuente de verdad (contrato §2 intacto); el motor mantiene un ESPEJO explícitamente
   no-autoritativo (así etiquetado en toda salida del motor desde A3).
   **Para las clases nativas no hay periodo previo**: nacen canónicas en el motor y, si
   se refleja algo en GitHub, ese reflejo es informativo y se etiqueta como tal.
2. **Condición de conmutación por clase** (solo para las clases con proyección GitHub):
   el verificador de proyección (motor ↔ incidencia) en verde de forma continua durante
   **14 días** para esa clase Y cero intervenciones manuales de desatasco en ese periodo.
   (El umbral es propuesta de este plan; E1a puede ajustarlo — es el único parámetro
   abierto.)
3. **El acto de conmutación**: registro fechado (dato versionado en el repo) + anuncio en
   la incidencia patrón de la clase. Desde ese instante, para esa clase: el almacén del
   motor es canónico y la incidencia pasa a PROYECCIÓN OBLIGATORIA — el motor la mantiene
   y el verificador la vigila; una divergencia es un defecto del motor, no una duda de
   autoridad.
4. **Orden de conmutación** (solo las clases con proyección): documental publicada →
   programación → auditoría (programación solo tras el periodo de C1+C2). Investigación y
   demás clases nativas no aparecen: no conmutan porque ya nacieron canónicas.
5. **Vuelta atrás**: el conmutador es reversible por clase con el mismo acto fechado;
   revertir re-declara la incidencia como fuente de verdad y el motor vuelve a espejo.
   Nada que borrar: ambos lados conservan su historial completo.

## 5. Spikes e incógnitas: inserción exacta

| Incógnita | Se resuelve en | Bloquea exactamente | Antes de eso |
|---|---|---|---|
| I3 durabilidad | S1 (tras A1) | A2 (patrón de escritura seguro) | A1 avanza sin ella |
| I2 GPT Researcher | S2 (tras A4/A5) | B1; y decisión de gasto SOLO si el spike la demuestra | Fase A completa sin ella |
| I1 bordes STATUS | S3 (tras A3, solapable con B) | C1 (cotas de LOST) | espejo pasivo A3 no la necesita |
| I4 dónde corre el motor | dato + decisión del propietario | **D2**: servicio desatendido **y fijación de la representación física definitiva** (ADR-019). Si el propietario la adelanta, A2 puede fijar ya la representación | A–C corren atendidos, sobre el adaptador **de referencia** de A2 |
| I5 bandera Codex | dato del propietario (leer/encender la variable) | **no bloquea la construcción de ningún bloque**, pero la vía Codex debe haberse EJECUTADO de verdad antes de declarar **M3** completo (o la carencia se escribe) | todos los bloques avanzan sin ella |

Ningún spike se ejecuta por este plan: cada uno arranca como Work Item propio cuando su
bloque anterior termina.

## 6. Disposición recomendada para la PR #171: EXTRAER PIEZAS Y CERRAR SIN FUSIONAR

**Estado factual reverificado por API el 2026-08-15, después de fusionarse #173 y #174**:
abierta, `merged: false`, head `52e0f55`, cero reviews y cero comentarios, `quality` verde
sobre su head, `mergeable_state: clean`; prohibición de fusión del propietario vigente,
declarada en su propio cuerpo. **Su base es `e13a1e3`**, es decir, quedó **dos commits por
detrás de `main` (`54bb690`)**: no contiene ADR-019, ni la arquitectura aprobada, ni la
excepción de `docs/evolution/STATUS.md`. Su rama `feat/investigador-por-etiqueta` sigue
existiendo, así que ADR-017 y ADR-018 continúan reservados por la convención de
numeración. Contiene dos familias de material con destinos opuestos:

- **Incompatible con el diseño aprobado**: el Investigador de ADR-017 es exactamente la
  combinación repo privado + web que la política global de egress (arquitectura §6.1,
  auditada como B1 y cerrada) declara estructuralmente incompatible dentro del motor.
  Fusionarlo crearía la segunda vía de investigación con la frontera débil
  (contrato+registro, detección posterior al hecho) mientras B1 construye la fuerte.
- **Compatible y valioso**: ADR-018 (el arnés ejecuta y el modelo interpreta; runbooks
  neutrales al motor), el registro cerrado de acciones, las mejoras del workflow del
  Auditor, el banco de evaluación y el endurecimiento de pruebas. Varias de estas ideas
  ya están absorbidas conceptualmente por ADR-019.

**Recomendación única**: no fusionar nunca #171 tal cual; extraer las piezas compatibles
en PRs pequeñas nuevas, cada una en el bloque donde encajan — el registro de acciones y
la neutralidad de runbooks alimentan **A4**; las mejoras del arnés del Auditor y sus
pruebas, una PR propia junto a **C4**; el banco de evaluación queda como material para la
fase de evaluación posterior —, y entonces **cerrar #171 sin fusionar**, dejando en la PR
el motivo escrito: su parte investigadora quedó superada por la frontera de egress del
diseño aprobado (la necesidad real la cubre B1) y su parte reutilizable vive en las PRs
extraídas (enlazadas). Los números ADR-017/018 siguen tomados mientras exista la rama
`feat/investigador-por-etiqueta` (la convención cuenta todas las ramas remotas); para no
resucitar ambigüedad, las PRs de extracción usarán numeración nueva en todo caso.

**Quién decide**: el cierre de #171 es un acto del propietario (la prohibición de fusión
es suya); este plan solo lo recomienda. No bloquea ningún bloque: A4 y C4 pueden extraer
las piezas con #171 aún abierta.

## 7. Riesgos globales del plan

1. **Interferencia motor↔automatización existente** (dos observadores, un estado): se
   controla entrando por fases — primero espejo (A3, cero escrituras), luego supervisión
   con reglas de coordinación (C1), luego despacho (C2) — y con E1b fijando los límites
   antes de la primera escritura.
2. **El entorno real de I4** (Windows, disponibilidad): aislado en D2; nada anterior
   depende de él.
3. **Coste de la vía GitHub** (minutos de Actions por ciclos de demostración): los
   bloques usan incidencias de humo pequeñas; el espejo y el supervisor leen con
   moderación (cadencias de S3).
4. **Deriva documental** (la familia PROC-010): cada bloque que cambie comportamiento
   actualiza su documento en la misma PR; el plan no crea documentos de estado nuevos
   (ADR-005).

## 8. Lo que este plan NO garantiza

- No garantiza esfuerzo ni fechas: ordena dependencias y valor, no calendario.
- No garantiza que GPT Researcher sea el investigador definitivo: garantiza que el flujo,
  el brief y la frontera sobreviven a su sustitución.
- No garantiza la calidad de los Workers: garantiza que sus defectos vuelven a ellos y
  que su muerte no pierde estado.
- No autoriza nada por sí mismo: E0, E1a y E1b son las puertas, y son del propietario.
