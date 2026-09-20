# Las 35 sesiones de Claude Code en la nube, una a una (20-09-2026)

- Fecha: 2026-09-20
- Fuente: el listado de sesiones de la cuenta, leído desde esta sesión.
- Relacionado: `docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md`, paso 4.

## Por qué existe este documento

El paso 4 de la auditoría declaró como límite que **28 de las 34 sesiones de la
nube no se pudieron traer**. Las cuatro vías probadas para bajarlas están
medidas en la auditoría y ninguna funciona sin gastar un turno de modelo por
sesión.

Lo que sí se puede leer sin gastar nada es **la ficha de cada una**: cuándo
empezó y terminó, desde dónde se dirigió, con qué modelo, en qué rama dejó su
trabajo y cómo acabó. No es la conversación —eso sigue faltando— pero convierte
«28 sesiones desconocidas» en 35 sesiones con nombre, fecha y desenlace.

**Lo que este documento NO trae, a propósito:** el coste en dólares de cada
sesión, que la fuente sí da. El repositorio es público y eso es dinero del
propietario. Si él quiere la tabla con esa columna, se añade.

## Las cuatro preguntas que se quedaron sin contestar

El hallazgo que esta lectura destapa, y que no estaba en la auditoría. Cuatro
sesiones terminaron **esperando una respuesta suya que nunca llegó**, la más
vieja de hace dos meses. Dos siguen marcadas como bloqueadas hoy.

| Última actividad | Sesión | Estado | Qué pedía |
|---|---|---|---|
| 2026-07-18 | Validar suite Qt headless en Sirius | Archived | ¿Quieres que me suscriba a la actividad de la PR #33 para vigilar CI y comentarios de revisión, o la dejo así? |
| 2026-07-27 | Revisión forense ADR002-TOL-207 | Archived | approve classifications: ENVOLVENTE_REPRODUCIBLE, pico-inclusive semantics, 5.670-element corpus, memory values (1.6GB/8.5GB/30GB), package 04 executi |
| 2026-08-21 | Sirius learning vertical integration audit | Idle | decide: does GAP-1 (modelo by Run) attach to B1 or C2, or is it unowned? |
| 2026-08-24 | Sirius motor: PR y primer workflow | Idle | choose: (1) diary to own branch, (2) exempt automations from rule, or (3) diary as PR per turn |

Es exactamente la familia `pregunta-al-propietario-que-nadie-vuelve-a-poner-delante`,
con cuatro casos fechados. Ninguna de las cuatro llegó a una incidencia ni a un
ADR: se quedaron dentro de su sesión, donde solo se ven si alguien va a
buscarlas.

## Las 35, por orden de nacimiento

| Fechas | Título | Origen | Modelo | Rama de salida | Estado |
|---|---|---|---|---|---|
| 2026-07-18 → 2026-07-18 | Cloud push smoke test | ios | sonnet-5 | `claude/cloud-push-smoke-test-akcqiv` | Archived |
| 2026-07-18 → 2026-07-18 | Verificación de script de configuración | web_claude_ai | sonnet-5 | `claude/config-script-verification-fkugd1` | Archived |
| 2026-07-18 → 2026-07-18 | Verificar script de configuración | web_claude_ai | sonnet-5 | `claude/verify-config-script-2g9xls` | Archived |
| 2026-07-18 → 2026-07-23 | Verificar versiones y estado | web_claude_ai | sonnet-5 | `claude/check-versions-status-iejdep` | Archived |
| 2026-07-18 → 2026-07-18 | Sesión iniciada | web_claude_ai | sonnet-5 | `claude/sesion-iniciada-m39i87` | Archived |
| 2026-07-18 → 2026-07-18 | Validación del repositorio Sirius | web_claude_ai | sonnet-5 | `claude/sirius-repo-validation-mhcyft` | Archived |
| 2026-07-18 → 2026-07-18 | Python 3.14 compatibility validation | web_claude_ai | opus-4-8 | `claude/python-3-14-validation-luszd9` | Archived |
| 2026-07-18 → 2026-07-18 | Python 3.14 instalación | web_claude_ai | opus-4-8 | `claude/python-3-14-install-check-8pygia` | Archived |
| 2026-07-18 → 2026-07-18 | Validar entorno remoto Sirius Python 3.14 | web_claude_ai | opus-4-8 | `claude/validate-sirius-python-3.14-dtm5i0` | Archived |
| 2026-07-18 → 2026-07-18 | Validar suite Qt headless en Sirius | web_claude_ai | opus-4-8 | `claude/validate-sirius-qt-headless-zez2kf` | Archived |
| 2026-07-18 → 2026-07-18 | Validación final Sirius remoto | web_claude_ai | opus-4-8 | `claude/sirius-remote-validation-f0hiwe` | Archived |
| 2026-07-19 → 2026-08-17 | Sirius workflow transitions repair | ios | opus-4-8 | `feat/b13-reproducible-windows-package` | Idle |
| 2026-07-25 → 2026-07-26 | ADR-001 spike 7 y revisión de cierre | ios | opus-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-26 → 2026-07-26 | Auditoría Registro de Tolerancias v0.3 | ios | opus-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-26 → 2026-07-26 | Auditoría adversarial benchmark ADR-001 | ios | opus-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-26 → 2026-07-26 | Auditoría adversarial corpus v0.2 | ios | opus-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-26 → 2026-07-27 | ADR002 benchmark corpus hardening | ios | opus-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-27 → 2026-07-27 | ADR002 v0.4 auditoría adversarial final | ios | fable-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-27 → 2026-07-27 | Revisión forense ADR002-TOL-207 | ios | fable-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-27 → 2026-07-27 | Auditoría adversarial TOL-207 | ios | fable-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-27 → 2026-07-27 | TOL-207 caracterización almacenamiento v0.2 | ios | fable-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-28 → 2026-07-28 | ADR002-TOL-207 auditoría adversarial final | ios | fable-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-28 → 2026-07-28 | Auditoría final B-1 ADR-002 | ios | fable-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-28 → 2026-07-28 | Auditoría final B-1 ADR-002 | ios | opus-5 | `evidence/adr001-spikes` | Archived |
| 2026-07-29 → 2026-09-20 | Auditoría forense ADR002-TOL-209 | ios | opus-5 | `claude/adr002-tol209-forensic-audit-i0ui8k` | Running |
| 2026-08-02 → 2026-08-11 | Revisión dual Claude + Codex en Sirius | ios | fable-5 | `claude/sirius-dual-review-codex-m6vkcm-reactiv` | Idle |
| 2026-08-07 → 2026-08-14 | Model estudio review y auditoría | ios | opus-5 | `claude/model-estudio-review-qpbknq` | Idle |
| 2026-08-10 → 2026-08-11 | Pendientes del ciclo: PRs, issues y automatizaciones | ios | opus-5 | `claude/ciclo-pendientes-prs-issues-qm4t8x` | Idle |
| 2026-08-11 → 2026-08-15 | Auditoría de procesos de trabajo Sirius | ios | fable-5 | `feat/investigador-por-etiqueta` | Idle |
| 2026-08-15 → 2026-09-14 | Flujo de trabajo definitivo de Sirius | ios | fable-5 | `claude/sirius-workflow-definitivo-e91vn2` | Idle |
| 2026-08-18 → 2026-08-18 | No hagas nada | ios | opus-5 | `herramienta/skill-adr` | Idle |
| 2026-08-19 → 2026-08-21 | Sirius learning vertical integration audit | ios | opus-5 | `claude/sirius-learning-audit-ixtr0g` | Idle |
| 2026-08-24 → 2026-08-24 | Sirius motor: PR y primer workflow | ios | opus-5 | `devolver-el-permiso` | Idle |
| 2026-09-08 → 2026-09-14 | Propuesta separación Sirius y motor | ios | opus-5 | `cierre/lo-que-queda-y-por-que` | Idle |
| 2026-09-15 → 2026-09-20 | Colaboración en Sirius | ios | opus-5 | `claude/sirius-collaboration-rir6r6` | Running |

## Lo que esta tabla sí permite decir

- **Dónde vive el trabajo.** Cada sesión declara la rama en la que dejó lo suyo.
  Ese es el mapa que faltaba para saber qué ramas del repositorio son trabajo de
  sesión y cuáles no.
- **Desde dónde dirige.** La columna «origen» separa el móvil del ordenador, y
  confirma con datos el hallazgo E-01 de la auditoría.
- **Qué quedó a medias.** Los estados y las cuatro preguntas de arriba.

## Lo que NO permite decir

- **Qué se dijo dentro.** No es la transcripción. Las hipótesis de la auditoría
  sobre cómo conversa el propietario no se pueden contrastar con esto.
- **Cuánto tiempo pasó él en cada una.** Las fechas son de la sesión, no suyas.
- **Si el desenlace declarado es cierto.** El resumen lo escribió la propia
  sesión al terminar su turno; no está contrastado contra el árbol.
