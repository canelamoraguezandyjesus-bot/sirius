# ADR-066 — Perfiles documentales: documentalista y revisor documental, coherentes con la maquinaria existente

- Estado: PROPUESTO
- Fecha: 2026-08-22
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario

## Contexto y problema

C3 (Capability Resolver, incidencia #202) dejó versionados los `AgentProfile`
de los tres roles del ciclo de programación —`implementer`, `reviewer`,
`corrector`— más el `auditor`. La incidencia #246 (C3a) midió y publicó lo
necesario para una clase nueva de perfil, el documental, pero no pudo
escribirlo entero: su puente hacia la incidencia real vive en
`.github/workflows/**`, y ADR-002 prohíbe a la automatización tocar sus
propios workflows. #246 dejó, en su lugar, la medición completa y este
bloque (C3b) la aplica: los dos ficheros `AgentProfile` de la clase
documental —`documentalista` y `revisor-documental`— más las tablas escritas
a mano que la propia medición encontró desincronizables.

Los dos perfiles son, deliberadamente, los mismos dos huecos que ya cubren
`implementer`/`reviewer` para el ciclo de código, pero para trabajo cuyo
contenido es documentación: `documentalista.yml` reutiliza exactamente la
forma de `implementer.yml` (capacidades de escritura sobre el repositorio,
`pr.crear`, `permisos.escritura: repo`), y `revisor-documental.yml`
reutiliza exactamente la forma de `reviewer.yml` (solo lectura del
repositorio, `permisos.escritura: veredicto` acotado al canal del veredicto
JSON). Ninguna capacidad nueva hace falta en `registro_capacidades.yml`: las
seis que ambos perfiles piden (`incidencia.leer`, `repo.leer`,
`repo.escribir`, `pr.crear`, `validaciones.ejecutar`, `veredicto.escribir`)
ya existen, porque el trabajo de fondo —leer una incidencia, escribir en el
árbol o solo leerlo, ejecutar validaciones, escribir un veredicto— es la
misma forma de trabajo que el ciclo de código, aplicada a otro tipo de
contenido.

## Criterio de parada (escrito ANTES de decidir)

Antes de tocar ningún fichero: si alguno de los dos perfiles necesitara una
capacidad que no existe todavía en `registro_capacidades.yml`, o si el
alcance permitido de la incidencia #247 no bastara para dejar el bloque
completo y coherente con `profile_registry.py` y las pruebas existentes, me
detengo con `BLOCKED_BY_DECISION` en vez de ampliar el registro o el alcance
por mi cuenta. Igualmente, si al añadir los dos `.md` nuevos a
`scripts/automation/prompts/` alguna prueba existente de la familia
`test_prompts_de_rol.py` o `test_veredictos_de_rol.py` exigiera una
propiedad que estos dos prompts no pudieran cumplir sin inventar contenido
no autorizado por la incidencia, eso también es parada, no una razón para
debilitar la prueba.

Verificado: las seis capacidades ya están en el registro (ninguna nueva), y
las cuatro pruebas de aceptación pasan sin `skip` con los dos prompts
presentes (ver «Comprobación que la sostiene»). No hubo que ampliar nada
fuera del alcance permitido.

## Opciones consideradas

1. **Reutilizar la forma de `implementer.yml`/`reviewer.yml` tal cual**,
   cambiando solo `ref`, `mision` y `procedimiento_ref`.
2. Diseñar una forma de perfil distinta para la clase documental (por
   ejemplo, con capacidades más finas: `documentacion.escribir` en vez de
   `repo.escribir`).
3. No versionar perfiles documentales todavía y esperar a que el puente en
   `.github/**` exista primero.

## Decisión

**Opción 1.** Los dos ficheros de perfil son estructuralmente los mismos
huecos que `implementer.yml`/`reviewer.yml`, con el contenido de `mision` y
`procedimiento_ref` ajustado al trabajo documental. La opción 2 se descarta
porque introduciría capacidades nuevas en `registro_capacidades.yml` sin que
la incidencia lo autorice (ver «Fuera de alcance» en #247) y sin que exista
todavía ningún caso real que distinga "escribir documentación" de "escribir
en el repositorio" a nivel de capacidad del Resolver: ambos perfiles escriben
archivos de texto versionados de la misma forma. La opción 3 se descarta
porque `profile_registry.py` y `AgentProfile` ya son la maquinaria genérica
que #202 dejó lista para cualquier perfil nuevo -esperar no reduce ningún
riesgo, solo pospone un trabajo ya medido y ya seguro.

### B2 · Con revisión dual, el perfil documental no decide nada

Ejecutado el agregador real (`scripts/automation/sirius_aggregate_reviews.py`):
si Claude documental aprueba y Codex responde con una observación de estilo
sobre un documento (por ejemplo, longitud de línea), `CHANGES_REQUESTED` de
cualquiera de los dos gana. El revisor de Codex
(`scripts/automation/sirius_codex_review.py`) es una constante del módulo,
no un perfil: pide severidad, archivo y línea, sin distinguir si el archivo
es documental o de código. Ningún `AgentProfile` lo alcanza, y eximirlo
rompería `test_codex_requests_changes` y
`test_codex_failed_safely_never_degrades_to_claude_only`, que son
invariantes de la revisión dual, no de este bloque.

**Límite declarado, no descubierto después:** la garantía de que "los
hallazgos que el revisor documental produce sobre un documento real son
documentales y no de código" solo vale cuando `SIRIUS_CODEX_REVIEW_ENABLED`
no está activo (revisión de un único perfil). Con revisión dual activada,
Codex puede seguir aportando observaciones de forma/estilo sobre el
documento que no son "de código" en el sentido que preocupa a la incidencia,
pero tampoco están gobernadas por `revisor-documental.yml`: las gobierna el
recolector de Codex, que es el mismo para cualquier PR. Ampliar o acotar ese
recolector por tipo de contenido es un cambio del agregador y del contrato de
observación, y está fuera de alcance de #247.

### B3 · El corrector no tiene autoridad documental

`scripts/automation/prompts/corrector.md` enumera lo corregible
-implementación, pruebas, lint, tipos, imports, CI, migraciones- y ninguna
categoría es documental; manda `BLOCKED_BY_DECISION` si la observación toca
arquitectura o ATD, que es donde viven los documentos que este bloque
gobierna. Es la misma familia de límite que ADR-033 diagnosticó para las
reglas anti-espera: una lista de lo corregible que no nombra "documentación"
no la cubre, y ampliar esa lista es una decisión sobre la autoridad del
corrector, no sobre los perfiles documentales.

**Consecuencia práctica:** un `CHANGES_REQUESTED` del `revisor-documental`
sobre una PR documental llega hoy al mismo corrector genérico, que puede
corregir defectos mecánicos (una comprobación de lint sobre el documento, un
enlace roto detectado por herramienta) pero se detendrá con
`BLOCKED_BY_DECISION` ante cualquier observación que requiera reescribir
contenido documental de fondo. Ampliar la autoridad del corrector para que
sepa corregir observaciones documentales es una decisión aparte, declarada
aquí como pendiente y explícitamente fuera de alcance de #247.

## Comprobación que la sostiene

- `registro_capacidades.yml` no se modificó: `git diff --stat` no lo lista
  entre los ficheros tocados por este bloque, y las seis capacidades que
  piden `documentalista.yml`/`revisor-documental.yml` (`incidencia.leer`,
  `repo.leer`, `repo.escribir`, `pr.crear`, `validaciones.ejecutar`,
  `veredicto.escribir`) ya estaban declaradas antes de este bloque.
- `uv run pytest tests/automation/test_prompts_de_rol.py
  tests/automation/test_veredictos_de_rol.py tests/engine/test_agent_profile.py -q`
  → 58 passed, 5 skipped (los mismos cinco `skip` estructurales que ya
  existían para `reviewer.md`, ahora también para `revisor-documental.md` y
  `documentalista.md`, ninguno por ausencia de los prompts nuevos).
- `test_lo_que_el_prompt_ofrece_es_exactamente_lo_que_el_guion_acepta[revisor-documental.md-reviewer]`
  pasa: las viñetas de veredicto de `revisor-documental.md` son exactamente
  `{REVIEW_APPROVED, CHANGES_REQUESTED, BLOCKED_BY_DECISION, FAILED_SAFELY}`,
  el mismo conjunto que `sirius_apply_verdict.sh` acepta para el rol
  `reviewer` (R10/R11: `ROLE` sigue siendo el literal `"reviewer"`; el
  perfil solo elige qué `.md` se inserta, cosa que decide el puente en
  `.github/**`, fuera de este bloque).
- `tests/engine/test_agent_profile.py` recorre ahora los perfiles por
  `glob` sobre `docs/implementation/work_engine/perfiles/*.yml` (excluido
  `registro_capacidades.yml`, que no es un `AgentProfile`), y
  `test_el_procedimiento_referenciado_existe_en_el_arbol` comprueba que el
  `procedimiento_ref` de los seis perfiles (`implementer`, `reviewer`,
  `corrector`, `auditor`, `documentalista`, `revisor-documental`) apunta a
  un fichero real del árbol.
- `load_agent_profile("documentalista")` y
  `load_agent_profile("revisor-documental")` cargan sin
  `UnknownAgentProfileError` (cubierto por
  `test_carga_todos_los_perfiles_reales`, parametrizado por el `glob`).

## Consecuencias

- Los dos ficheros de perfil documental existen, son válidos según
  `profile_registry.py`, y sus dos prompts cumplen los mismos invariantes
  anti-silencio (veredicto provisional, prohibición de esperar, entorno
  acotado) que los tres roles de código, verificados por la misma familia de
  pruebas -no por una copia nueva de las reglas.
- El puente que resuelve `Perfil: documentalista@1` /
  `Perfil: revisor-documental@1` desde el cuerpo de una incidencia hacia
  `.github/workflows/implement-sirius-work.yml` /
  `review-sirius-work.yml` **no existe todavía**: `profile_field.py` ya sabe
  leer y proyectar el campo, pero ningún workflow lo consulta. Sin ese
  puente, activar hoy una incidencia con `Perfil: documentalista@1` seguiría
  ejecutando el prompt de `implementer.md`, no el de `documentalista.md`.
  Escribir ese puente requiere sesión interactiva (ADR-002) y es la
  incidencia siguiente de esta serie, no este bloque.
- B2 y B3 quedan como límites conocidos y declarados, no como defectos
  ocultos: la revisión dual no distingue perfiles documentales de perfiles
  de código, y el corrector genérico no tiene autoridad sobre contenido
  documental de fondo. Ambos son decisiones de alcance para otra incidencia.

## Alternativas descartadas y por qué

- **Capacidades nuevas y más finas para la clase documental**: ningún caso
  real las necesita todavía, y añadirlas sin necesidad concreta contradice
  el criterio de `registro_capacidades.yml` ("añadir una capacidad nueva es
  una decisión visible en este fichero", no una anticipación).
- **Eximir al revisor documental de la revisión dual de Codex**: ya se
  intentó eximir una constante del agregador por otro motivo y rompió dos
  pruebas de invariante (`test_codex_requests_changes`,
  `test_codex_failed_safely_never_degrades_to_claude_only`); repetirlo aquí
  tendría el mismo defecto. Se declara el límite (B2) en vez de forzar una
  excepción no probada.
- **Ampliar `corrector.md` para que sepa corregir observaciones
  documentales**: es una decisión sobre la autoridad de un rol ya existente,
  fuera del alcance permitido de #247 (B3), no una consecuencia mecánica de
  añadir dos perfiles nuevos.
