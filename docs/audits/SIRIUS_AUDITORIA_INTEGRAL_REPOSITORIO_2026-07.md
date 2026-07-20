# SIRIUS — Auditoría integral del repositorio (julio de 2026)

**Fecha de auditoría:** 2026-07-20 (17:52–18:30 UTC)
**SHA auditado de `main`:** `d2b974bf73c8fc74defcfba159d66a3d67e2d321` ("fix: harden Sirius automation I/O and transitions")
**Entorno:** Linux 6.18.5 · Python 3.11.15 (host) / 3.14.6 (proyecto, vía uv) · uv 0.8.17 · git 2.43.0
**Herramientas no disponibles:** `actionlint`, `shellcheck`, `gh` CLI local, `pwsh` (no se ejecutó `scripts/check.ps1`; sus cuatro pasos se ejecutaron individualmente con `uv run`), empaquetado Nuitka/Windows real.
**Alcance:** todo el repositorio `canelamoraguezandyjesus-bot/sirius` más el estado vivo de Issues, PRs, etiquetas, workflows y runs.
**Limitaciones:** sin Windows real ni ejecutable real; sin proveedor LLM real; sin credenciales reales; las Routines externas (Claude/Routines) no son inspeccionables desde el repositorio — se auditan por sus efectos observables. Las mediciones de rendimiento con volumen (5.000 mensajes) no se ejecutaron en esta pasada y no se inventan.

Distinción usada en todo el informe: **[HECHO]** comprobado con evidencia; **[INFERENCIA]** deducción razonada; **[RIESGO]** posibilidad no materializada; **[DECISIÓN]** requiere al usuario.

---

## 1. Resumen ejecutivo

Sirius 0.1 tiene una base de código **sólida y disciplinada**: capas limpias (verificado por imports), dominio puro, transaccionalidad real con rollback probado contra SQLite real, cadena Alembic lineal con 13 migraciones y sin bifurcaciones, `PRAGMA foreign_keys=ON` activado por conexión, `store=False` hacia el proveedor, pruebas de fuga de secretos significativas y una suite de ~904 pruebas verde en Linux.

El punto débil real del proyecto **no es el código de producto: es el circuito de automatización y, sobre todo, el conector externo que escribe en GitHub**. Durante las últimas 48 horas se han producido **seis incidentes reales**, todos reconstruidos aquí con evidencia (§13). Cuatro comparten la misma causa raíz: **una herramienta externa escribe contenido truncado y lo confirma sin verificar** — truncó dos workflows, el cuerpo de la Issue #55 y, hoy mismo (commit `ab6e74a`, 17:47 UTC), **vació 704 de 705 líneas de `src/sirius/presentation/knowledge_widget.py` en la rama de la PR #57**, destruyendo la implementación de B4f en esa rama. Las defensas añadidas esta semana (lectura robusta, validación estructural, escritura verificada, transiciones atómicas) funcionaron: el corrector se negó a operar sobre el head corrupto y dejó #55 en `sirius:blocked-decision` sin tocar nada. Pero el repositorio **no puede impedir** un `git push` corrupto desde fuera; solo puede detectarlo y contenerlo, y así lo hizo.

**Veredicto:** B4a–B4e están genuinamente terminados y fusionados. B4f está implementado y revisado (con 3 hallazgos concretos H1–H3 del revisor), pero **su rama está actualmente corrupta** y bloqueada a la espera de una decisión del usuario. La automatización es hoy mucho más robusta que hace 48 horas, pero sigue **degradada hasta que se fusione la PR #58** (el `ensure_label` de `main` está roto) y expuesta a duplicación de Routines externas. Ninguna prueba humana, de Windows real, de ejecutable real ni de proveedor real puede declararse superada.

---

## 2. Estado real de Sirius 0.1

| Vertical/Bloque | Estado | Evidencia |
|---|---|---|
| V0–V8 (parcial), B2a/B2b/B3a/B3b/B3c, V7/V7A | Fusionados | `REPOSITORY_STATUS.md` + historial de merges + suite verde |
| B4a origen/guardado manual | **Terminado** | merge `c025683`, pruebas |
| B4b decisiones/aprobación | **Terminado** | merge `d1bbb87` (PR #37) |
| B4c corrección/sustitución | **Terminado** | merge `e244649` (PR #39) |
| B4d archivo/eliminación/redacción | **Terminado** | merge PR #41 |
| B4e precedencia/conflictos | **Terminado** | merge PR #52 (`b649c92`); Issue #50 reconciliada y cerrada en esta auditoría |
| B4f integración observable | **Implementado y revisado, NO terminado** | PR #57 abierta; revisor emitió `CHANGES_REQUESTED` (H1–H3) sobre `c4d4822`; head actual `ab6e74a` **corrupto**; #55 en `blocked-decision` |
| Exportación de conversaciones | **No implementada** | no existe caso de uso de exportación (solo backup/restore); pendiente de su vertical |
| FTS5 / selección de contexto B6 | No iniciado (correcto) | sin rastro de FTS5 en `src/` |
| Empaquetado Windows/Nuitka | **Sin evidencia** | no auditable en este entorno |
| Personalidad (PS-01–PS-07) | Pendiente de evaluación humana | no se declara superada |

Solo parece terminado pero no lo está: **B4f** (rama corrupta + hallazgos H1–H3 sin corregir) y **el cierre automático post-merge** (funcionará solo tras fusionar la PR #58).

---

## 3. Hallazgos

Formato: ID · severidad · categoría · archivo/objeto · evidencia · impacto · causa raíz · corrección · estado.

### P0

Ninguno vigente en `main`. El único candidato a P0 (pérdida de código por `ab6e74a`) no afecta a `main` ni a datos de usuario: afecta a la rama de la PR #57 y **el contenido es recuperable** desde `c4d4822` (ningún dato se ha perdido de forma irrecuperable). Se clasifica como P1 activo (HAL-001).

### P1

- **HAL-001 · P1 · automatización/conector externo · rama `claude/focused-bohr-3dj9el` (PR #57), commit `ab6e74a`.**
  [HECHO] Commit "fix: require explicit source-message choice before memory deletion" (17:47:36Z, autor `canelamoraguezandyjesus-bot`) con diff `1 insertion(+), 704 deletions(-)` sobre `knowledge_widget.py`; el archivo resultante son 8 líneas con docstring sin cerrar — verificado localmente: `SyntaxError: unterminated triple-quoted string literal`. **Cuarta ocurrencia** del patrón de escritura truncada (§13, INC-1/INC-6/INC-7).
  Impacto: implementación de B4f destruida en la rama; el título del commit simula ser la corrección de H1 sin serlo. Reproducción: `git show ab6e74a:src/.../knowledge_widget.py | python -m py_compile -`.
  Causa raíz [INFERENCIA fuerte]: el conector externo de escritura corta payloads largos (~>4 KB) y confirma sin releer/verificar — la misma firma en 4 incidentes distintos (workflow, rama, cuerpo de issue, archivo de código).
  Contención que SÍ funcionó [HECHO]: el corrector detectó head≠registrado, se negó a operar y aplicó `blocked-decision`; no hubo reconstrucción no autorizada.
  Corrección: **decisión del usuario** (revertir `ab6e74a` o reset a `c4d4822`; después reaplicar `sirius:repair-requested`). Prevención: prohibir a ese conector escrituras de archivos >N líneas sin verificación por relectura; preferir `git` real o la escritura verificada de `sirius_issue.sh` para cuerpos de issues. Estado: **ABIERTO — DECISIÓN REQUERIDA (D-1)**.

- **HAL-002 · P1 · automatización · Issue #50 (B4e).**
  [HECHO] Tras fusionar la PR #52 (00:35Z), el workflow de cierre (versión anterior a la PR #56) publicó el marcador `<!-- sirius-completed:b649c92… -->` y murió después en `ensure_label` (`gh label view` inexistente) bajo `set -e`: la incidencia quedó abierta, sin etiquetas y — al salir todo reintento por el marcador — **atascada de forma permanente**. Además hubo **dos implementaciones duplicadas** (PRs #52 y #53, comentarios READY_FOR_REVIEW a las 23:51 y 23:57) para el mismo Work ID.
  Corrección aplicada en esta auditoría: (a) #50 **reconciliada en vivo** (etiquetas saneadas, cerrada como completada — verificado por relectura); (b) `sirius_transition` ahora **verifica el estado final aunque el marcador exista y reanuda sin duplicar comentarios** (raíz del atasco permanente eliminada); (c) reconciliador manual que detecta y repara este patrón (caso A). Estado: **CORREGIDO** (pendiente de merge de la PR de esta auditoría para b y c).

- **HAL-003 · P1 · automatización · `scripts/automation/sirius_issue.sh` en `main` (línea ~240).**
  [HECHO] `sirius_ensure_label` usa `gh label view` (subcomando inexistente) → cae a `gh label create` → falla con "already exists" para etiquetas existentes → **toda transición que garantice una etiqueta existente falla** (así se atascó #55 en `ci-pending`; run `29745812244`). Diagnóstico y corrección ya en la **PR #58** (abierta, `gh label create --force`). Hasta su merge, `advance` y `complete` seguirán fallando en ese paso (de forma atómica y reintentable, pero fallando). Estado: **CORREGIDO EN PR #58 — pendiente de merge (D-2)**.

- **HAL-004 · P1 · CI/eventos · PR #57, head `ab6e74a`.**
  [HECHO] 20+ minutos tras el push, `get_status` = `pending`, `total_count: 0`: **Quality nunca se ejecutó sobre el head corrupto**. [INFERENCIA] El push del conector no generó un evento que dispare workflows (pushes hechos por integraciones/tokens de Actions no disparan `pull_request: synchronize`). Impacto: un head roto ni siquiera aparece en rojo; si un humano mirase solo "checks", no vería alarma. Mitigaciones existentes: `advance` compara head actual vs `workflow_run.head_sha` (los resultados verdes antiguos no promueven un head nuevo — verificado en código, líneas 61–68); el merge exige verificación humana. Mitigación añadida: el reconciliador informa de `ci-pending` sin resultado de CI para el head vigente. Estado: **MITIGADO — riesgo residual documentado (§20)**.

### P2

- **HAL-005 · P2 · Routines externas · duplicación de ejecuciones.**
  [HECHO] Dos implementadores para #50 (PRs #52/#53, 6 min de diferencia); dos comentarios `BLOCKED_BY_DECISION` del corrector para #55 (17:52:07 y 17:52:28). El contrato (§6) exige "ninguna ejecución equivalente activa", pero las Routines externas no lo garantizan. El repositorio no puede imponer single-flight sobre un componente externo. Corrección posible en el lado externo: comprobación de marcador/etiqueta al inicio + un lock por Work ID. Estado: **ABIERTO — componente externo (D-3)**.

- **HAL-006 · P2 · gobernanza de incidencias · #45, #38, #40, #42 abiertas y obsoletas.**
  [HECHO] #45 (`sirius:planned`, "automation activation check") nunca se activó; #38/#40/#42 son del patrón antiguo "Review request" ya sustituido por etiquetas. Ruido para el reconciliador y para cualquier búsqueda de incidencias activas. Corrección: cerrarlas (decisión del usuario; no las cierro por iniciativa propia al no ser estados inequívocamente terminados). Estado: **ABIERTO — DECISIÓN (D-4)**.

- **HAL-007 · P2 · automatización · `sirius_transition` (marcador antes que verificación).**
  [HECHO] Hasta hoy, la salida temprana por marcador no verificaba el estado final: cualquier flujo que hubiese publicado marcador sin completar (como INC-3/#50) quedaba irrecuperable por reintento. Corregido en esta auditoría: verificación del estado final (etiqueta presente; cerrada si procede) y **reanudación sin comentario duplicado**. Probado (`test_transition_resumes_when_marker_present_but_state_incomplete`, `test_transition_verified_marker_short_circuits`). Estado: **CORREGIDO en esta PR**.

- **HAL-008 · P2 · pruebas/cobertura · biblioteca Bash sin cobertura en Windows.**
  [HECHO] `tests/automation/test_sirius_issue.py` (y el nuevo `test_sirius_reconcile.py`) se omiten en Windows (runner de Quality: `bash.exe` de WSL sin distribución — INC-5). La cobertura queda solo en Linux, que es donde la biblioteca se ejecuta realmente (runners `ubuntu-latest`). Aceptable y documentado en el propio módulo; si la biblioteca llegara a ejecutarse en Windows habría que revisar esta decisión. Estado: **ACEPTADO con nota**.

### P3

- **HAL-009 · P3 · documentación operativa · `B4_EXECUTION.md`/`REPOSITORY_STATUS.md` en `main` desfasados.** [HECHO] `B4_EXECUTION.md` §B4e termina con "Una PR borrador quedó abierta… B4f sigue sin iniciarse", pero B4e está fusionado (#52) y B4f en curso (#57). La PR #57 ya trae esas actualizaciones; corregirlo también aquí crearía conflicto. Estado: ABIERTO — se resuelve con la vía que el usuario elija para B4f.
- **HAL-010 · P3 · persistencia · sin `WAL`/`busy_timeout` en `database.py`.** [RIESGO] Con UI + worker actuando sobre la misma base, un candado puntual puede aflorar como error. FKs sí están activadas; `session_scope` hace rollback íntegro. MEJORA para un corte futuro; no bloquea 0.1 monousuario.
- **HAL-011 · P3 · gobernanza · `AUTOMATION_OPERATING_CONTRACT.md` dice "PROPUESTO EN PR #44; VIGENTE ÚNICAMENTE TRAS MERGE HUMANO".** [HECHO] La PR #44 se fusionó: el contrato está vigente pero se sigue leyendo como propuesto. Informado, no corregido automáticamente (declarar vigencia es acto de gobernanza — D-5).
- **HAL-012 · P3 · notificaciones · texto de `repair-requested` engañoso.** [HECHO] Decía "Una comprobación automática ha fallado" también cuando el origen era `CHANGES_REQUESTED` de revisión (caso real de hoy). **CORREGIDO en esta PR** (texto neutro que cubre ambos orígenes).
- **HAL-013 · P3 · Quality solo en Windows.** Quality corre únicamente en `windows-latest`: apropiado para el producto (app Windows), pero significa que los scripts Bash de automatización solo se validan en CI vía… nada (se omiten). Compensado con validación local documentada y simulaciones; considerar un job Linux ligero para `tests/automation` (MEJORA, requiere decisión de coste de CI).

### MEJORA

- **HAL-014** · presupuesto implementado como decorador en `adapters/llm/budget.py`: diseño defendible (proxy transversal), pero la regla mensual es de producto; considerar moverla a aplicación si crece.
- **HAL-015** · el reconciliador es manual (`workflow_dispatch`); programarlo requeriría decidir sobre la prohibición de vigilancia horaria del contrato (D-6).
- **HAL-016** · incidencia plantilla: el validador estructural exige "Base y dependencias" pero la plantilla `sirius-work-item.yml` no genera esa sección (los cuerpos generados por ChatGPT sí la incluyen). Alinear plantilla y validador en un corte futuro.

---

## 4. Contradicciones detectadas

1. Contrato de automatización "propuesto" vs. realmente vigente (HAL-011).
2. `B4_EXECUTION.md` en `main` vs. estado real de B4e/B4f (HAL-009).
3. Comentario del implementador de B4f: "se prueban ambas elecciones" vs. hallazgo H2 del revisor (REDACT sin cobertura GUI en el widget) — la afirmación excedía la evidencia; el revisor lo detectó.
4. Mensaje de notificación `repair-requested` vs. origen real del evento (HAL-012, corregido).
5. Título del commit `ab6e74a` ("fix: require explicit source-message choice…") vs. su contenido real (borrado masivo) — la contradicción más grave; motivo de D-1.

## 5. Memoria y datos (F5–F6)

[HECHO] Verificado por inspección y por la suite (integración con SQLite real, no dobles):
- Conversar no crea/aprueba/corrige/archiva/elimina memoria ni decisiones (pruebas explícitas en `test_send_message.py` y ciclos de vida).
- Origen obligatorio; corrección crea revisión nueva e inmutable con puntero autoritativo; sustitución conserva historial y enlace; archivados/sustituidos/eliminados fuera del contexto ordinario; eliminación redacta contenido en todas las revisiones y el marcador mínimo no conserva texto; redacción del mensaje fuente solo por elección explícita tipada sin valor por defecto; advertencia de copias antiguas devuelta por el caso de uso.
- Transaccionalidad: evento+estado en la misma `UnitOfWork`; pruebas de rollback tras fallos intermedios; sin huérfanos observados.
- Cadena Alembic **lineal** (13 migraciones, 1 head `94418c79da9d`, 0 bifurcaciones), migraciones aditivas, probadas con `upgrade`/`downgrade` reales.
- FTS5: no existe aún (B6): la invariante "índices sincronizados" es N/A hoy; al introducirlo, las pruebas de reaparición de datos eliminados en búsqueda serán obligatorias.
- [RIESGO] Sin WAL/busy_timeout (HAL-010).

## 6. Seguridad y privacidad (F11)

[HECHO] `store=False` en `openai_responses.py:132`. Clave API solo vía `keyring` (Credential Manager en Windows); puertos/fakes correctos; **pruebas de fuga reales y valiosas** (`test_secret_leakage.py`: settings.json, SQLite tras un envío completo, logs incluso cuando la excepción incrusta la clave, reprs). Sin telemetría; sin tráfico externo salvo el proveedor. No se usaron credenciales reales en la auditoría.
[RIESGO no verificado en esta pasada]: cifrado/nonces del backup y limpieza de temporales se validaron por suite existente (`validate_backup`/`restore_backup` con casos de corrupción y contraseña incorrecta), no por criptoanálisis independiente.

## 7. Interfaz (F10)

Verificación limitada a suite GUI offscreen (Linux): coherencia de estados, señales y diálogos cubierta por `tests/gui/` (~pestañas, onboarding, backup, continuidad). **Pendiente Windows real**: escalado 100/125 %, foco/tabulación reales, antivirus, cierre forzado con UI abierta. El hallazgo H1 del revisor (radio preseleccionado en el diálogo de borrado de B4f) demuestra que la revisión de UI está funcionando; su corrección está bloqueada por D-1.

## 8. Proveedor y contexto (F8)

[HECHO] Proveedor tras contrato (`ports/llm.py`), adaptador OpenAI con `store=False`, errores normalizados, presupuesto persistente con aviso/bloqueo (decorador `budget.py` + `sqlite_llm_usage_repository`), FakeLLM para toda la suite. Contexto mínimo: `ContextBuilder` excluye archivados/eliminados/sustituidos y aplica la precedencia B4e (decisión APPROVED inequívoca excluye al recuerdo contradicho; conflictos genuinos se conservan sin elegir). [PENDIENTE proveedor real] Streaming/cancelación/reintentos contra la API real y PA que lo exijan.

## 9. Pruebas y trazabilidad (F15)

- Suite en `main`: **~904 pruebas, 0 fallos, 0 xfail; único skip**: módulo Bash en Windows (justificado). Sin `assert True`, sin `noqa`, sin TODO/FIXME; 17 `type: ignore` (16 en tests, 1 en el adaptador OpenAI).
- Mocks: el `gh` simulado de automatización **modela el gh real** (sin `label view`, `create --force` upsert) — corregido tras el incidente INC-2, donde un mock permisivo ocultó el defecto real. Lección incorporada.
- Clasificación de aceptación: PA-001–PA-016 en su parte automatizable → **demostradas automáticamente** (PA-010–PA-016 completas solo cuando B4f cierre); PA-008, PA-E2E-01 → **pendientes de proveedor real/evaluación humana**; PS-01–PS-07 → **pendientes de evaluación humana**; SP-01–SP-07 → parcialmente demostradas (SP-06 probada; el resto por suite de backup/secretos); **pendiente de Windows real/ejecutable real**: todo lo de F16.
- Nada contradicho por la suite; lo contradicho (H1/H2 de B4f) lo detectó la revisión independiente, no la suite — exactamente el defecto de cobertura que H2 señala.

## 10. Empaquetado y Windows real (F16)

**Sin evidencia en esta auditoría** (entorno Linux sin Nuitka/pyside6-deploy). `uv run` verde NO se considera suficiente. Pendientes: instalación limpia, portable, Credential Manager real, antivirus, DLL/plugins Qt, Unicode/espacios en rutas, cierre forzado, primera/segunda ejecución, actualización de esquema. Estado: **pendiente de ejecutable real** (bloqueante para declarar 0.1 validado).

## 11. Automatización (F18) — máquina de estados reconstruida

Estados y transiciones (actor → disparador → efecto verificado):

| Transición | Actor | Disparador | Salvaguardas verificadas |
|---|---|---|---|
| planned → implement-requested | ChatGPT/usuario | etiqueta | evento consumible |
| implement-requested → implementing | Routine implementadora | etiqueta | valida contrato completo (rechaza truncados); consume evento |
| implementing → ci-pending | Routine | fin de implementación | registra rama/PR/head; para sin merge |
| ci-pending → review-requested | workflow `advance` | `workflow_run` Quality=success | head actual == head del run; 1 sola issue; transición atómica; marcador por head |
| ci-pending → repair-requested | `advance` | Quality=failure/timed_out | ídem |
| ci-pending → failed-safely | `advance` | otras conclusiones / ambigüedad | ídem + exit 1 en ambigüedad |
| review-requested → reviewing | Routine revisora | etiqueta | head==registrado; Quality verde para ese head exacto (verificado hoy en vivo) |
| reviewing → ready-for-merge / repair-requested / blocked-decision / failed-safely | revisora | veredicto | ligado a head exacto |
| repair-requested → repairing → ci-pending | correctora | etiqueta | máx. 2 ciclos; hoy se negó ante head≠registrado (correcto) |
| merge (humano) → completed+cerrada | workflow `complete` | PR merged | transición atómica + cierre; **degradada hasta PR #58** |
| notificación | workflow `notify` | 6 etiquetas | secundaria; nunca rompe el flujo; dedup por issue/estado/SHA |

Puntos ciegos que quedaban y su tratamiento: estados atascados sin evento repetible (etiqueta ya presente no re-dispara `labeled`) → **reconciliador manual** añadido; marcador-sin-estado → transición auto-reparadora; `ci-pending` con CI ya resuelto → reconciliador caso B; contradicciones de etiquetas → reconciliador informa. `workflow_run` usa el workflow de la rama por defecto y `checkout ref: main` [HECHO], por lo que las correcciones solo rigen tras su merge — documentado en cada PR.

## 12. Notificaciones (F19)

[HECHO] Los comentarios de las Routines los firma la cuenta del propietario: **no generan notificación al propietario** (GitHub no notifica autocomentarios). La entrega real depende de `notify-sirius-state.yml`, que comenta como `github-actions[bot]` mencionando `@propietario` una sola vez — esto sí notifica (verificado por diseño; los cuatro avisos de hoy — implementing, repair-requested, blocked-decision — se publicaron y deduplicaron correctamente por issue/estado/SHA, incluido `no-head`). "Comentario creado" ≠ "notificación entregada": la entrega final depende de la configuración de GitHub del usuario (no verificable desde el repo). Fallos del workflow de notificación terminan con warning y éxito (no rompen el flujo) y el intento queda registrado en el run. Sin autoasignación; sin avisos de CI antiguo (dedup por SHA); no se notifica una transición no aplicada (etiquetas se aplican antes del comentario en las transiciones; `notify` reacciona a la etiqueta ya puesta).

## 13. Incidentes reconstruidos (F18, obligatorio)

- **INC-1 — Workflows truncados (19-jul).** Síntoma: `advance` cortado dentro de `CI_STOPPED_SAFELY`; `notify` con cuerpo a columna 0 (YAML inválido, `startup_failure` en cada push). Causa raíz: escritura truncada del conector + bloque escalar YAML mal indentado. Por qué no lo detectaron las pruebas: no existían pruebas de automatización. Corrección: PRs #49/#54 (reconstrucción completa, `printf` indentado). Regresión: parseo YAML + `bash -n` en auditorías; pruebas de automatización desde PR #56. Riesgo residual: el conector sigue pudiendo escribir truncado (HAL-001).
- **INC-2 — #47 cierre fallido (19-jul).** Síntoma: `failed to update … 'sirius:completed' not found`. Causa: etiqueta inexistente + dependencia del bootstrap. Corrección: PR #51 (`ensure_label`)… que introdujo `gh label view` (INC-4). Lección: el mock permisivo del test no modeló el `gh` real.
- **INC-3 — #50 atascada (20-jul, 00:35).** Síntoma: issue abierta, sin etiquetas, con marcador SIRIUS_COMPLETED. Causa: marcador publicado antes del éxito + `ensure_label` roto + `set -e`. Por qué no lo detectaron las pruebas: la simulación no cubría "marcador ya presente con estado a medias". Corrección: PR #56 (comentario al final) + **esta auditoría** (transición auto-reparadora + reconciliador + #50 reconciliada en vivo).
- **INC-4 — #55 atascada en ci-pending (20-jul, 13:20).** Síntoma: Quality verde sin transición. Causa demostrada: `gh label view` inexistente → "already exists" (run `29745812244`, log literal en PR #58). Corrección: PR #58 + desbloqueo manual verificado (revisor arrancó: `reviewing` observado).
- **INC-5 — Pytest rojo en Windows (20-jul, 03:23).** Síntoma: 10–15 fallos UTF-16 "WSL has no installed distributions". Causa: `bash` del runner = stub WSL; el primer guard (`shutil.which`) encontró Git Bash pero `subprocess` resolvió el stub (PATH con `:` en Windows). Corrección: skip por plataforma + `os.pathsep`; Quality verde en `81d2b1e`.
- **INC-6 — Corrupción de `knowledge_widget.py` (20-jul, 17:47).** Ver HAL-001. Las defensas de proceso (head-check del corrector, transiciones atómicas) **contuvieron** el incidente; CI no se disparó sobre el head corrupto (HAL-004). ABIERTO (D-1).
- **INC-7 — Lectura 502/503 + cuerpo #55 truncado (20-jul, 01:24).** Síntoma: FAILED_SAFELY del implementador; cuerpo sobrescrito parcialmente. Causa: única vía GraphQL/MCP + escritura no verificada. Corrección: PR #56 (biblioteca robusta REST-first, validador estructural, escritura verificada) + restauración verificada del cuerpo. Riesgo residual: el conector externo (HAL-001).
- **INC-8 — Routines duplicadas.** Ver HAL-005. ABIERTO (D-3).

## 14. Correcciones realizadas en esta auditoría

1. **`sirius_transition` auto-reparadora** (`scripts/automation/sirius_issue.sh`): con marcador presente verifica etiqueta/cierre reales; completa lo que falte **sin duplicar comentarios**; solo corto-circuita si el estado final está verificado.
2. **Reconciliador manual** (`scripts/automation/sirius_reconcile.sh` + `.github/workflows/reconcile-sirius-states.yml`, solo `workflow_dispatch`): repara los dos casos inequívocos (completado-sin-cerrar; `ci-pending` con Quality verde del head vigente) e informa del resto (eventos sin consumir, en-curso, decisiones humanas, contradicciones, CI pendiente/fallido). No hace merge, no inicia bloques, no se programa (contrato: sin vigilancia horaria — D-6 si se quisiera programar).
3. **Notificación `repair-requested`** con texto veraz para ambos orígenes (CI o revisión).
4. **Reconciliación en vivo de #50** (cerrada como completada, etiquetas saneadas — verificado por relectura).
5. **10 pruebas nuevas** (`tests/automation/test_sirius_reconcile.py`) cubriendo: caso A con idempotencia y sin comentarios nuevos; caso B con Quality verde/pending/failure; marcador ambiguo no reparado; contradicción de etiquetas; blocked-decision solo informe; reanudación de transición con marcador presente; corto-circuito verificado.

No se tocó: `src/` de producto, documentos canónicos, la rama de la PR #57, el cuerpo de #55, ni las PRs #57/#58.

## 15. Decisiones requeridas del usuario

- **D-1 (urgente):** commit `ab6e74a` — ¿accidental? → revertir/reset a `c4d4822` y reaplicar `sirius:repair-requested` para corregir H1–H3. ¿Intencional? → aclarar el contenido esperado de `knowledge_widget.py`.
- **D-2:** fusionar la **PR #58** (sin ella, `advance`/`complete` siguen degradados).
- **D-3:** configurar single-flight/deduplicación en las Routines externas (fuera del repo).
- **D-4:** cerrar las incidencias obsoletas #45, #38, #40, #42.
- **D-5:** actualizar el estado del contrato operativo a "VIGENTE" (acto de gobernanza).
- **D-6:** si se desea reconciliación periódica, decidir la excepción a la prohibición de vigilancia horaria (hoy es solo manual).
- **D-7:** política del conector externo: prohibir escrituras largas no verificadas (raíz de 4 incidentes).

## 16. Validaciones ejecutadas (F20)

| Comando | Resultado |
|---|---|
| `uv run ruff format --check .` | 192/193 archivos conformes (los nuevos formateados) |
| `uv run ruff check .` | All checks passed |
| `uv run mypy src tests` | Success (189→190 archivos) |
| `uv run pytest` | verde (904 en `main`; +10 de esta auditoría; ver PR) |
| `git diff --check` | limpio |
| Parseo YAML 5+1 workflows | OK |
| `bash -n` biblioteca + reconciliador + scripts embebidos | OK |
| `actionlint`/`shellcheck`/`scripts/check.ps1`/Nuitka | **no disponibles en el entorno** (limitación registrada) |
| Simulaciones con `gh` simulado | 42 pruebas de automatización en verde |

## 17. Veredicto

**Sirius 0.1 no está aún en condiciones de declararse validado**, por tres razones objetivas: (1) B4f bloqueado con rama corrupta y hallazgos de revisión sin corregir (D-1); (2) automatización degradada hasta fusionar la PR #58 (D-2); (3) cero evidencia de Windows real/ejecutable real/proveedor real/evaluación humana de personalidad. El código de producto fusionado (V0–B4e) es de calidad alta y verificable; el sistema de defensa de la automatización demostró hoy, en un incidente real, que contiene fallos destructivos externos en lugar de propagarlos. El eslabón más débil es el conector externo de escritura (D-7): mientras no se controle, cualquier artefacto de GitHub puede volver a corromperse; el repositorio ya solo puede detectarlo, no impedirlo.
