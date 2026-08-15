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
E0  autorización de implementación (mini-PR a evolution/STATUS.md, tipo #174)   [DECISIÓN]
 └─ FASE A — núcleo y espejo (sin más decisiones; A1 puede empezar "mañana")
     A1 núcleo puro del motor (estados, transiciones, puerto, en-memoria)
     S1 spike I3: durabilidad (kill -9 → recuperación)                          [experiments/]
     A2 almacén durable según S1 + barrido de recuperación
     A3 espejo de solo lectura de la vía GitHub + contexto.recuperar v0
     A4 perfiles versionados + WorkerRequest + Resolver v0 + egress
        ── HITO M1: estado durable y consultable; se acabó la reconstrucción forense ──
 └─ FASE B — investigación (valor nuevo; NO depende de C1/C2/C5)
     S2 spike I2: GPT Researcher aislado (sin repo)             [posible decisión de gasto]
     B1 adapter GPT Researcher + ExportSafeBrief + flujo investigación completo
        ── HITO M2: Sirius investiga de verdad desde una orden ──
 └─ FASE C — motor activo sobre la vía GitHub
     E1 enmienda del contrato operativo v1.7: C1 + C2 + C5                      [DECISIÓN]
     S3 spike I1: bordes de STATUS de runs de Actions (solo lectura)
     C1 supervisión activa (LOST → reactivar / sustituir / escalar)
     C2 despacho end-to-end de programación (orden → ciclo completo → entrega)
     C3 documentación con Reviewer→Repair sobre el ciclo existente
     C4 Auditor como perfil del motor (superficie por etiqueta existente)
        ── HITO M3: vertical funcional completa de #172 §6 ──
 └─ FASE D — canonicidad y servicio
     D1 migración de canonicidad por clase (regla C5 de v1.7)
     D2 servicio desatendido                                     [BLOQUEADO por I4]
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
- **B1** demuestra la promesa diferencial de #172 §6: investigar desde una orden, con
  frontera mecánica. Se coloca ANTES que la Fase C a propósito: da valor nuevo sin tocar
  el contrato operativo.
- **C1–C2** demuestran el fin del propietario-mensajero en programación: nadie desatasca
  a mano, nadie transporta contexto ni activa etiquetas.
- **C3–C4** completan las clases de trabajo de la vertical (documentación, auditoría)
  REUTILIZANDO el ciclo y la superficie del Auditor existentes.
- **D1–D2** convierten el resultado en régimen: canonicidad sin doble autoridad y motor
  en servicio sin niñera.

## 2. Bloques en detalle

Formato de cada bloque: objetivo / dependencia real / ficheros o componentes previsibles /
prueba de terminado / riesgo principal / qué puede hacerse automáticamente / decisión
humana material previa.

### E0 — Autorización de implementación

- **Objetivo**: extender la excepción registrada por la PR #174 en
  `docs/evolution/STATUS.md`: de «solo la fase de diseño» a «implementación según el plan
  aprobado (ADR-020)», manteniendo el resto de prohibiciones (frameworks/proveedores no
  aprobados, multiagente abierto, permisos generales). Satisface también el criterio de
  parada de `AGENTS.md` («introducir otro proceso, servidor, agente o base de datos»)
  mediante decisión explícita del propietario.
- **Dependencia real**: la fusión de la PR de este plan (aprueba ADR-020 y la secuencia).
- **Ficheros**: `docs/evolution/STATUS.md` (una línea ampliada, mini-PR tipo #174).
- **Prueba de terminado**: la excepción menciona implementación + ADR-020; pruebas
  documentales en verde.
- **Riesgo principal**: redactar de más y autorizar de más; se mitiga copiando el patrón
  acotado de #174.
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

### A2 — Almacén durable + barrido de recuperación

- **Objetivo**: implementación durable del puerto según lo decidido en S1; barrido de
  arranque (arquitectura §3.5): reconciliar cada Run abierto contra el mundo y recalcular
  el siguiente paso.
- **Dependencia real**: A1 + resultado de S1.
- **Ficheros**: `src/sirius_engine/` (adaptador de persistencia), `tests/engine/`
  (la prueba del spike, convertida en prueba estable del repositorio).
- **Prueba de terminado**: la prueba de recuperación integrada en la suite y vista fallar
  con la durabilidad rota (mutación).
- **Riesgo principal**: heredar del spike un patrón que funcionó por accidente;
  mitigación: la prueba estable reproduce la matriz completa, no un caso.
- **Automatizable**: sí (Work Items del ciclo).
- **Decisión humana previa**: ninguna.

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

### A4 — Perfiles versionados + WorkerRequest + Resolver v0 + política de egress

- **Objetivo**: los tres prompts de rol + el runbook del Auditor convertidos en Agent
  Profiles versionados (misión/procedimiento/capacidades/permisos/contrato E-S, sin
  nombres de herramienta); proyección determinista `WorkerRequest` (arquitectura §5.1);
  Capability Resolver v0 con registro versionado (heredero del patrón
  `registro_de_acciones.yml` de la PR #171); validador de egress fail-closed (§6.1) con
  clasificación por fragmento.
- **Dependencia real**: A1 (tipos). Independiente de A3; puede solaparse.
- **Ficheros**: `src/sirius_engine/` (proyección, resolver, egress),
  `docs/implementation/work_engine/perfiles/` o equivalente (perfiles como datos
  versionados), `tests/engine/`.
- **Prueba de terminado**: (1) propiedad misma-entrada → misma-petición; (2) la
  proyección del perfil implementador reproduce el prompt que hoy monta
  `implement-sirius-work.yml` para una incidencia fixture — prueba de no-divergencia con
  la vía existente; (3) egress: un fragmento sin clasificación exportable IMPIDE `START`
  (mutación vista fallar); (4) capacidad no registrada → no resuelta.
- **Riesgo principal**: perfiles que digan más que los prompts reales (deriva); la prueba
  (2) lo hace estructural, no vigilado.
- **Automatizable**: sí (Work Items del ciclo).
- **Decisión humana previa**: ninguna.

**HITO M1** (fin de Fase A): el propietario puede preguntar por cualquier trabajo pasado
o vivo y obtener estado con evidencia, de un almacén que sobrevive a reinicios. Nada
escribe aún en GitHub.

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
- **Dependencia real**: A2 + A4 + S2. **No depende de C1/C2/C5**: no toca etiquetas
  `sirius:*` ni ciclos de la vía GitHub.
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

**HITO M2**: Sirius investiga de verdad — #172 §6.5-6.6 cumplidos — sin haber tocado el
contrato operativo.

### E1 — Enmienda del contrato operativo v1.7 (C1 + C2 + C5)

- **Objetivo**: una única revisión del contrato, documental, que resuelva las tres
  contradicciones detenidas ANTES de que la Fase C dependa de ellas (arquitectura §14):
  - **C1**: distinguir iniciativa (prohibida) de transporte de una orden ya dada: el
    motor puede aplicar `sirius:implement-requested` SOLO para WorkItems con orden
    explícita del propietario registrada y enlazada en la evidencia.
  - **C2**: el supervisor del motor queda autorizado con límites: supervisa y repara SUS
    Runs; no inventa trabajo; no fusiona; no toca ciclos que no gobierna; el
    reconciliador de Actions queda como respaldo de la vía GitHub.
  - **C5**: regla de migración de canonicidad POR CLASE de trabajo con proyección
    obligatoria y verificable en la incidencia mientras la vía GitHub siga operativa
    (mecánica en §4 de este plan).
- **Dependencia real**: fusión de este plan; conviene tras M1/M2 (evidencia de que el
  motor existe y aporta), pero puede prepararse en paralelo a la Fase B.
- **Ficheros**: `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` (v1.6 → v1.7, con
  su registro §10). PR documental propia, revisada y fusionada por el propietario.
- **Prueba de terminado**: contrato v1.7 fusionado; las pruebas estructurales que citan
  §9.1 (RECON-STUCK-007/013) siguen en verde o actualizadas en la misma PR con
  justificación.
- **Riesgo principal**: enmendar de más; mitigación: solo los tres puntos, con el texto
  propuesto derivado literalmente de §14 de la arquitectura.
- **Automatizable**: la redacción sí; la decisión es del propietario.
- **Decisión humana previa**: SÍ — es en sí misma la decisión (segunda y última decisión
  material del plan, junto con E0, hasta D2).

### S3 — Spike I1: bordes de `STATUS` sobre runs de Actions (desechable, solo lectura)

- **Objetivo**: medir lo que decide las cotas de `LOST`: latencia real de estados,
  comportamiento de runs cancelados/expirados, rate limits, y con ello cadencia de sondeo
  y cotas por etiqueta de estado.
- **Dependencia real**: A3 (espejo que consultar). Independiente de E1; puede solaparse.
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
- **Dependencia real**: A3 + S3 + **E1 (C2)**. Sin v1.7 este bloque NO empieza.
- **Ficheros**: `src/sirius_engine/` (supervisor + políticas), `tests/engine/`.
- **Prueba de terminado**: en una incidencia de humo, un run matado a mitad queda
  reactivado o escalado por el motor sin intervención humana, con el episodio completo en
  el diario; prueba de no-carrera con el reconciliador (los dos observando el mismo
  atasco → una sola acción).
- **Riesgo principal**: carreras con la automatización existente; mitigación: la misma
  disciplina de marcadores e idempotencia que ya usa `sirius_reconcile.sh`, mas la regla
  de recurso mutable de la cancelación en dos tiempos.
- **Automatizable**: el código sí; la prueba de humo, supervisada.
- **Decisión humana previa**: E1 fusionada (ya contada ahí).

### C2 — Despacho end-to-end de programación

- **Objetivo**: cerrar el círculo del propietario-no-mensajero en la clase programación:
  puerta de intención (orden inequívoca crea y activa, 8.5) → incidencia generada desde
  la plantilla (proyección del WorkPackage) → etiqueta de activación aplicada por la
  identidad del motor (**smoke test I6** como primer paso del bloque) → ciclo completo
  existente (implementar → Quality → revisión → reparar) seguido por el espejo y el
  supervisor → entrega del resultado con evidencia. El merge sigue siendo humano
  (`fusiona`), sin cambios.
- **Dependencia real**: C1 + **E1 (C1 contractual)** + A4.
- **Ficheros**: `src/sirius_engine/` (despachador + puerta de intención + adapter de
  escritura mínima: crear incidencia, aplicar etiqueta de activación), interfaz v0
  (CLI/sesión) para dar la orden.
- **Prueba de terminado**: un encargo pequeño real recorre TODO el ciclo desde una única
  orden del propietario, que no toca GitHub hasta el `fusiona`; el diario permite
  reconstruir el episodio completo. **I5** (valor de `SIRIUS_CODEX_REVIEW_ENABLED`) se
  conoce a más tardar aquí — es un dato para saber qué modo de revisión esperar, no un
  bloqueo: la agregación existente cubre ambos modos.
- **Riesgo principal**: el arranque doble (puerta de validación + implementador ya se
  revalidan solos) interactuando con un tercer actor; mitigación: el motor usa
  exactamente la vía del propietario (misma etiqueta, misma plantilla), sin atajos.
- **Automatizable**: el código sí; el encargo de demostración, real.
- **Decisión humana previa**: ninguna nueva (E0+E1 ya tomadas).

### C3 — Documentación + Reviewer→Repair

- **Objetivo**: la clase documental completa REUTILIZANDO el ciclo `sirius:*`: Work Item
  documental con validaciones deterministas de documento (rutas citadas existen,
  referencias resuelven, formato) como comandos de su campo «Validaciones»; revisor
  independiente con el contrato de observación existente; reparación automática;
  entrega.
- **Dependencia real**: C2 (despacho) — el ciclo, el revisor y el corrector ya existen.
- **Ficheros**: perfil documentalista + revisor documental; un comprobador de documentos
  como script determinista NUEVO (no toca workflows; se invoca desde las validaciones del
  Work Item); `tests/` del comprobador.
- **Prueba de terminado**: un documento real creado, revisado con `CHANGES_REQUIRED` y
  observaciones estructuradas, reparado sin intervención y entregado; las validaciones
  documentales vistas fallar con un defecto sembrado (mutación).
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
interfaz v0 es CLI/sesión; Telegram queda como D3).

### D1 — Migración de canonicidad por clase (mecánica en §4)

- **Objetivo**: ejecutar la regla C5 de v1.7: conmutación fechada por clase de trabajo,
  con verificador de proyección motor↔incidencia.
- **Dependencia real**: E1 (regla) + clase estable: investigación/documental tras M2/C3;
  programación tras varias semanas de C1+C2 sin intervención manual (umbral concreto en
  §4).
- **Ficheros**: `src/sirius_engine/` (verificador de proyección), registro de conmutación
  (dato versionado).
- **Prueba de terminado**: verificador en verde N días por clase (N en §4) + conmutación
  registrada; el episodio de divergencia sembrado dispara alarma (mutación).
- **Riesgo principal**: doble autoridad ambigua; mitigación: la regla de §4 hace la
  autoridad una función total (clase → autoridad) sin estados intermedios.
- **Automatizable**: el verificador sí; cada conmutación la registra el propietario.
- **Decisión humana previa**: la conmutación de cada clase (acto simple, previsto en E1).

### D2 — Servicio desatendido — BLOQUEADO por I4

- **Objetivo**: el motor en régimen: proceso bajo supervisión externa con reinicio
  automático (requisito de despliegue de la arquitectura §3.5), arrancando el barrido de
  recuperación en cada arranque.
- **Dependencia real**: **I4** (dónde corre el motor). Este es el punto EXACTO donde I4
  bloquea; hasta aquí, el motor corre atendido en sesiones y nada anterior se detiene por
  ello.
- **Ficheros**: unidad de servicio/process manager según I4; guía de operación.
- **Prueba de terminado**: matar el proceso en horario desatendido → reinicio automático
  + recuperación sin pérdida, verificado dos veces.
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

- **Cuándo**: una única enmienda (E1, contrato v1.6 → v1.7), posicionada después de M2 y
  antes de cualquier bloque de la Fase C. Ningún bloque anterior las necesita: la Fase A
  no escribe en GitHub; la Fase B no toca la vía `sirius:*`.
- **Cómo**: el texto operativo sale de la arquitectura §14 (recomendaciones de C1, C2 y
  C5, ya auditadas dos veces): C1 = transporte de orden registrada, nunca iniciativa;
  C2 = supervisor autorizado con límites nombrados y reconciliador como respaldo;
  C5 = regla de migración por clase (§4). La enmienda es UNA PR documental del
  propietario; las pruebas estructurales que fijan §9.1 se actualizan en esa misma PR si
  el texto nuevo las mueve.
- **Guardia del plan**: C1 y C2 de la Fase C declaran E1 como dependencia dura; el bloque
  no arranca sin v1.7 fusionada. C5 solo se CONSUME en D1.

## 4. Migración de canonicidad sin doble autoridad (diseño)

Regla única: **la autoridad es una función total por clase de trabajo, con un solo
conmutador fechado por clase**; no existe estado intermedio.

1. **Antes de la conmutación de una clase**: la incidencia de GitHub es la fuente de
   verdad (contrato §2 intacto); el motor mantiene un ESPEJO explícitamente
   no-autoritativo (así etiquetado en toda salida del motor desde A3).
2. **Condición de conmutación por clase**: el verificador de proyección (motor ↔
   incidencia) en verde de forma continua durante **14 días** para esa clase Y cero
   intervenciones manuales de desatasco en ese periodo. (El umbral es propuesta de este
   plan; E1 puede ajustarlo — es el único parámetro abierto.)
3. **El acto de conmutación**: registro fechado (dato versionado en el repo) + anuncio en
   la incidencia patrón de la clase. Desde ese instante, para esa clase: el almacén del
   motor es canónico y la incidencia pasa a PROYECCIÓN OBLIGATORIA — el motor la mantiene
   y el verificador la vigila; una divergencia es un defecto del motor, no una duda de
   autoridad.
4. **Orden de conmutación**: investigación → documental → programación → auditoría
   (las clases nativas del motor primero; programación solo tras el periodo de C1+C2).
5. **Vuelta atrás**: el conmutador es reversible por clase con el mismo acto fechado;
   revertir re-declara la incidencia como fuente de verdad y el motor vuelve a espejo.
   Nada que borrar: ambos lados conservan su historial completo.

## 5. Spikes e incógnitas: inserción exacta

| Incógnita | Se resuelve en | Bloquea exactamente | Antes de eso |
|---|---|---|---|
| I3 durabilidad | S1 (tras A1) | A2 | A1 avanza sin ella |
| I2 GPT Researcher | S2 (tras A4) | B1; y decisión de gasto SOLO si el spike la demuestra | Fases A completas sin ella |
| I1 bordes STATUS | S3 (tras A3, solapable con B) | C1 (cotas de LOST) | espejo pasivo A3 no la necesita |
| I4 dónde corre el motor | dato + decisión del propietario | **D2** (servicio desatendido) únicamente | A–C corren atendidos en sesión |
| I5 bandera Codex | dato del propietario (leer variable) | nada — se conoce a más tardar en C2 para interpretar la demo | ningún bloque se detiene |

Ningún spike se ejecuta por este plan: cada uno arranca como Work Item propio cuando su
bloque anterior termina.

## 6. Disposición recomendada para la PR #171: EXTRAER PIEZAS Y CERRAR SIN FUSIONAR

Estado verificado (2026-08-15): abierta, sin reviews ni comentarios, `quality` verde,
`mergeable_state: clean`; prohibición de fusión del propietario vigente. Contiene dos
familias de material con destinos opuestos:

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
   con reglas de coordinación (C1), luego despacho (C2) — y con E1 fijando los límites
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
- No autoriza nada por sí mismo: E0 y E1 son las puertas, y son del propietario.
