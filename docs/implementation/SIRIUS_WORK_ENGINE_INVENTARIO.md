# Sirius Work Engine — Inventario y reconciliación del estado real

- Estado: DISEÑO / RECONCILIACIÓN. No autoriza implementación, merge ni cambio canónico.
- Encargo: incidencia #172 (SIRIUS-WORK-ENGINE-DESIGN-001), sección 9, puntos 2, 3, 19 y 21.
- Fecha: 2026-08-15
- Base inspeccionada: commit `e13a1e3` («Bloque B: ¿sirven las suscripciones…? (#170)»), igual a `main`.
- Nota de arranque publicada antes del primer commit: comentario en #172 (2026-08-15).

Convención de evidencia de este documento y de la arquitectura que lo acompaña:

- **Verificado**: leído en el árbol de este commit, con ruta (y líneas cuando importa).
- **Estado operativo declarado**: un documento o incidencia del repositorio afirma que algo
  ocurrió; no reverificado contra runs reales desde esta sesión.
- **NO VERIFICADO**: no comprobable desde el árbol ni desde la API disponible
  (secretos, variables de repositorio, comportamiento de productos externos).

---

## 1. Lo que ya existe

### 1.1 Una máquina de estados de trabajo completa, por etiquetas, sobre GitHub

Verificado en `.github/workflows/` (14 workflows) y `scripts/automation/` (9 scripts + 3 prompts).

Ciclo de un Work Item (etiquetas `sirius:*`, bootstrap en
`.github/workflows/bootstrap-sirius-automation-labels.yml:42-53`):

```
planned -> implement-requested -> implementing -> ci-pending
        -> review-requested -> reviewing -> (repair-requested -> repairing -> ci-pending)*
        -> ready-for-merge -> [fusiona, humano] -> completed
salidas laterales: blocked-decision, failed-safely
```

| Pieza | Fichero | Papel |
|---|---|---|
| Puerta de activación | `validate-sirius-activation.yml` + `sirius_validate_activation.sh` | Rechaza activaciones inválidas retirando solo el evento |
| Implementador | `implement-sirius-work.yml` | Claude Code implementa, abre PR, veredicto JSON |
| CI | `quality.yml` (ancla `quality`) | ruff format, ruff check, mypy, pytest |
| Avance tras CI | `advance-sirius-after-quality.yml` | `workflow_run` de Quality → review/repair/failed-safely |
| Revisor (dual opcional) | `review-sirius-work.yml` + `sirius_codex_review.py` + `sirius_aggregate_reviews.py` | Claude revisa en solo lectura; en modo dual, `@codex review` + agregación determinista |
| Corrector | `repair-sirius-work.yml` + `sirius_convergence.py` | Puerta de convergencia + corrección acotada a observaciones |
| Merge humano | `merge-sirius-work.yml` + `sirius_merge_on_command.sh` | Solo el comentario exacto `fusiona` del OWNER |
| Cierre | `complete-sirius-after-merge.yml` | PR fusionada → `completed` + cierre |
| Notificador | `notify-sirius-state.yml` | 6 estados notificables, idempotente |
| Red de seguridad | `reconcile-sirius-states.yml` + `sirius_reconcile.sh` | Cada 6 h; repara SOLO dos casos inequívocos; el resto informa |
| Auditor (fuera del ciclo) | `audit-sirius-repository.yml` | Etiqueta `auditoria:solicitada`; dos jobs partidos por ADR-016 |
| E/S robusta | `sirius_issue.sh` (790 líneas) | Lectura REST+GraphQL, filtro de autores de confianza, transición atómica, comentario idempotente, saneado |
| Aplicador de veredictos | `sirius_apply_verdict.sh` | El modelo nunca muta estado; este script reverifica y aplica |

Rasgos que un diseño nuevo debe conocer porque están pagados con defectos reales:

- **La incidencia es la fuente de verdad; las etiquetas solo estados/eventos**
  (`.github/ISSUE_TEMPLATE/sirius-work-item.yml:10`; contrato §2).
- **El modelo nunca muta etiquetas ni cierra**: escribe `{"verdict","summary",…}` en
  `SIRIUS_VERDICT_FILE`; lo aplica un script determinista que reverifica PR, head y Quality
  por su cuenta (`sirius_apply_verdict.sh`).
- **Head SHA de punta a punta**: revisión y merge exigen la coincidencia de tres SHA
  (declarado por el revisor, head real de la PR, último head con Quality verde).
- **Frontera de confianza en las lecturas**: todo comentario releído se filtra por
  `author_association == OWNER` o `github-actions[bot]` (`sirius_issue.sh:66-109`), y todo
  texto de modelo se sanea antes de publicarse dentro de ese filtro (`sanitize_untrusted_text`).
- **Dos identidades**: lecturas con `GITHUB_TOKEN`; toda escritura de etiqueta con el PAT,
  porque GitHub suprime los eventos del token efímero (ADR-014/ADR-015).
- **Convergencia en vez de tope de rondas**: el par (hallazgos pendientes, gravedad) debe
  descender estrictamente contra la mejor marca histórica; reaparición, oscilación o dos
  rondas sin progreso → `blocked-decision` (`sirius_convergence.py`; contrato §5.1).

### 1.2 Claude Code como Worker real, ya en producción

Verificado: los tres roles (implementador, revisor, corrector) ejecutan
`anthropics/claude-code-action@v1` dentro de GitHub Actions, con prompts de rol en
`scripts/automation/prompts/{implementer,reviewer,corrector}.md`. Esos prompts son
proto-perfiles: misión + límites + contrato de salida, sin nombre de modelo dentro del texto
del rol. Estado operativo declarado: ciclos completos reales (p. ej. incidencia #148 con
revisión dual, tres rondas y cierre; #133; #165).

### 1.3 Codex como segundo revisor, por GitHub, sin API de OpenAI

Verificado como soporte: `review-sirius-work.yml` en modo dual publica `@codex review`
determinista, recoge la respuesta del conector oficial (allowlist de autores), exige SHA
demostrado, y un agregador sin votos combina ambos veredictos; Codex mudo o ambiguo →
`FAILED_SAFELY`, nunca aprobación por silencio. **NO VERIFICADO**: el valor actual de
`SIRIUS_CODEX_REVIEW_ENABLED` (la sesión no puede leer variables de repositorio); por tanto
el soporte está presente, pero no se afirma que el modo dual esté activo.

### 1.4 El Auditor v0 como primer perfil portable

Verificado: `docs/implementation/AUDITOR_AGENT_V0.md` («este documento **es** el agente. El
modelo que lo ejecuta es una pieza intercambiable»), con superficie de herramientas
declarada por capacidades (§2b) y dos superficies de invocación (sesión; etiqueta por
ADR-016 con la propiedad «ningún trabajo que ejecute un modelo declara permisos de
escritura»). Estado operativo declarado: RUN-001 (#154, en sesión) y RUN-002 (#167, por
etiqueta, con dos hallazgos reales y correcciones fusionadas #168/#169).

### 1.5 La PR #171: la línea de agentes reconciliada, sin fusionar

Verificado por API (2026-08-15): abierta, `mergeable_state: clean`, `quality` en verde sobre
`52e0f55`, cero reviews y cero comentarios. Contiene: ADR-017 (Investigador, segundo agente
con web), ADR-018 (el arnés ejecuta y el modelo interpreta; runbooks neutrales al motor;
registro cerrado de acciones `tests/automation/registro_de_acciones.yml`), el workflow
`investigate-sirius-question.yml`, y `RECONCILIACION_LINEA_DE_AGENTES.md` que degrada los
tres roles del ciclo a «prototipo declarado». La prohibición de fusionarla dictada el 15-08
sigue vigente y la reitera #172 §7-§8. **Consecuencia para este diseño**: los números
ADR-017 y ADR-018 están tomados por esa rama; el primer libre es **ADR-019**.

### 1.6 El producto Sirius 0.1 (piezas conceptualmente reutilizables)

Verificado en `src/sirius/` (hexagonal vigilada por tests de frontera):

- **Recuperación de contexto**: FTS5 (`knowledge_fts`, `message_fts`) + ranking determinista
  + presupuesto de contexto (`application/context.py`, `context_budget.py`,
  `rank_relevant_knowledge.py`). Sirve solo al turno conversacional; no está expuesta como
  capacidad independiente, y `message_fts` no tiene hoy ningún consumidor.
- **Presupuesto LLM**: `adapters/llm/budget.py` + tabla `llm_usage` (límite mensual, aviso,
  comprobación antes de enviar).
- **Registro de eventos**: append-only, ligado a la transacción, pero limitado a memoria y
  decisión, sin listado ni payload (`ports/event_repository.py`).
- **Patrón puertos/adaptadores con dobles simulados** en cada capacidad externa.

### 1.7 Lo que NO existe (comprobado, no supuesto)

- **Ningún modelo persistido de trabajo**: ni tabla ni entidad de Work Item, run, cola o
  ejecución en `src/sirius/adapters/persistence/models.py` (12 modelos) ni en las 14
  migraciones. El único estado de trabajo del sistema son las etiquetas y comentarios de
  GitHub.
- **Ningún observador externo del ciclo**: la única vigilancia permitida es el
  reconciliador cada 6 h, que por contrato «no es motor» y para los estados de máquina
  atascados **solo avisa** («El reconciliador no ha reparado nada», `sirius_reconcile.sh:518`).
- **Ningún contrato de Worker ni adapter**: los tres roles están cableados a
  `claude-code-action` dentro de cada YAML; sustituir el motor exige editar workflows.
- **Ninguna capacidad de investigación**: GPT Researcher no está en el repositorio; el
  Investigador de la PR #171 es Claude-con-web sobre el propio repo, un perfil de confianza
  distinto del que #172 exige para investigación externa (`ExportSafeBrief`).
- **Ninguna interfaz sustituible**: hoy la interacción es la sesión de Claude Code, la web
  de GitHub y ChatGPT, con el propietario transportando contexto entre ellas
  (`WORK_PROCESS_AUDIT.md`: ≥15-20 desatascos manuales en 3,5 semanas; latencias de rescate
  de hasta 14 h 50 min y >6 días).
- **Ninguna clase de trabajo fuera de programación**: el ciclo `sirius:*` espera una PR con
  código; la auditoría vive fuera por diseño (ADR-016); documentación, investigación,
  conversación y consulta no tienen carril.

### 1.8 El defecto estructural de durabilidad, reconocido por escrito

Verificado, literal, en `repair-sirius-work.yml:67-81`:

> Todas las defensas de este workflow […] viven DENTRO del run. Un proceso que muere no
> puede informar de su propia muerte: […] la incidencia queda ATASCADA hasta que una
> persona la quita y la vuelve a poner […]. Eso no se arregla desde aquí: solo lo cierra un
> observador EXTERNO, y el contrato operativo prohíbe hoy programarlo […]. Queda registrado
> como decisión pendiente, no como defecto olvidado.

Alcance real: afecta a los tres consumidores de eventos por etiqueta (implementar, revisar,
reparar), al avance tras Quality (`workflow_run` es de un solo uso) y a la puerta de
activación (rechazo consumado sin diagnóstico publicable). La mitigación existente detecta
(≥180 min + cadencia 6 h) pero tiene prohibido reparar. Este es exactamente el hueco que el
Motor de Trabajo de #172 debe cerrar, y la propia automatización lo dejó anotado como
«decisión pendiente».

---

## 2. Qué se conserva, qué se adapta, qué se degrada a prototipo, qué se descarta

(Encargo #172 §9.21. «Conservar» = entra en el diseño tal cual; «adaptar» = entra con
cambios de forma, no de fondo; «prototipo declarado» = sigue funcionando pero no es la
referencia del diseño nuevo; «descartar» = no entra.)

| Pieza | Veredicto | Motivo |
|---|---|---|
| Ciclo por etiquetas + workflows + scripts deterministas | **Conservar** (como protocolo del Adapter de Claude Code por GitHub) | Es la vía Worker más probada del repositorio; #172 §4.7 prohíbe construir una segunda vía paralela |
| `sirius_issue.sh` (E/S robusta, confianza, saneado, transición atómica) | **Conservar** | Contratos pagados con defectos reales (#50, #55, #66, #136…) |
| Veredicto JSON + `sirius_apply_verdict.sh` | **Conservar** | Es ya la mitad del contrato `WorkResult`: el modelo informa, lo determinista aplica |
| Contrato de observación (id, severidad, archivo, problema, criterio_esperado, prueba, limites_correccion) | **Conservar** | Formato probado del retorno de defectos al Worker; lo consumen agregador y corrector |
| Política de convergencia (`sirius_convergence.py`) | **Conservar** | Terminación demostrable del bucle revisar-reparar; el motor la hereda como política del ciclo |
| Revisión dual con Codex por GitHub | **Conservar** | #172 §4.7: reutilizar esta vía en vez de diseñar Codex como si no existiera |
| Merge humano por `fusiona` | **Conservar** | Contrato §8; el motor no fusiona |
| Auditor v0 (runbook = perfil; ADR-016) | **Conservar** | Primer Agent Profile real del repositorio; molde del resto |
| Prompts `implementer/reviewer/corrector.md` | **Adaptar** → Agent Profiles versionados y neutrales al motor | Ya casi lo son; les falta separar capacidades requeridas de herramientas concretas (precedente: ADR-018 en PR #171) |
| Plantilla del Work Item (`sirius-work-item.yml`) + `validate_issue_body.py` | **Adaptar** → proyección GitHub del `WorkPackage` | Los 12 campos actuales son un subconjunto del WorkPackage de #172 §3.3 |
| Reconciliador (`sirius_reconcile.sh`) | **Adaptar** → respaldo transitorio de la supervisión del motor | Cuando el motor sea el observador externo, el reconciliador queda como red de seguridad de la vía GitHub, no como única vigilancia |
| ContextBuilder + FTS5 + presupuesto de contexto | **Adaptar** → proveedor futuro de `contexto.recuperar` | Hoy solo sirve al turno conversacional; exponerlo como capacidad es trabajo futuro sobre código existente |
| Registro de acciones + runbooks neutrales (PR #171) | **Adaptar** (conceptos; independiente de que #171 se fusione) | Precedentes directos del formato de perfil y del registro de qué ejecuta modelo |
| Los tres workflows de rol como «modo de ejecución» | **Prototipo declarado** | Clasificación ya hecha por la PR #171 (`registro_de_acciones.yml`: exentos del ciclo por `--dangerously-skip-permissions` y PAT al modelo); el motor debe poder sustituir ese modo sin cambiar el chasis |
| GitHub como bus operativo | **Prototipo declarado** (provisional por #172 §1.3) | Punto común verificable entre herramientas, no la memoria definitiva de Sirius |
| Frontera contrato+registro del Investigador (#171) como protección de confidencialidad | **Prototipo declarado** | #172 §4.7 exige que la protección no dependa de decirle al modelo «no filtres»; la frontera mecánica es `ExportSafeBrief` |
| Hermes, LangGraph, AutoGen, smolagents, A2A | **Descartar** (no entran en esta fase) | #172 §4.5, §4.7 y §8; ninguna incógnita actual los necesita |
| Inspect AI como dueño del ciclo | **Descartar** (queda como evaluador futuro, fuera del motor) | #172 §4.7; el diseño del banco de evaluación de la PR #171 ya apunta a un repo hermano |
| «Lectura estática» como modo del Auditor | **Descartado ya** por la PR #171 (pendiente de esa fusión) | RUN-002 demostró que degradaba el perfil; no se reintroduce |

---

## 3. Lista consolidada de NO VERIFICADO

1. Valores de secretos y variables de GitHub: `SIRIUS_BOT_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`,
   `SIRIUS_TRIGGER_TOKEN`, `SIRIUS_CODEX_REVIEW_ENABLED`, `SIRIUS_CODEX_*_SECONDS`,
   `SIRIUS_STUCK_MINUTES`.
2. Ejecución real del cron del reconciliador y de cualquier run de Actions citado.
3. Comportamiento de productos externos: `anthropics/claude-code-action@v1`, GitHub App de
   Codex, GPT Researcher (ni instalado), Telegram (ni instalado).
4. Protecciones de rama de `main` (el «no push directo» consta como salvaguarda y prompt,
   no como mecanismo verificado).
5. Estado vivo de issues/PRs no releídas en esta sesión más allá de lo citado.

Estos huecos no bloquean el diseño; los que bloquean una decisión están aislados como
spikes en la arquitectura (`SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md`, sección 15).
