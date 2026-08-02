# SIRIUS - Contrato operativo de automatización

**Versión:** 1.4  
**Fecha:** 3 de agosto de 2026  
**Estado:** VIGENTE (§4 actualizada; ver §10.3)  
**Autoridad:** Operativa para el desarrollo automatizado de Sirius 0.1  
**Sustituye:** versión 1.3 del 20 de julio de 2026  
**No modifica:** Producto, Arquitectura Técnica, ATD, requisitos ni alcance de Sirius 0.1

## 0. Propósito

Este contrato autoriza y regula un flujo permanente, secuencial y dirigido por eventos para Sirius 0.1. Su motor son tres workflows de GitHub Actions que ejecutan Claude Code real (implementador, revisor, corrector) — ver el mecanismo concreto en `SIRIUS_GENERIC_ROUTINES_0.1.md` §6 — y GitHub como canal operativo único. Cuando la revisión dual está activada (§4.1), Codex participa además como segundo revisor independiente de solo lectura, mediante su integración nativa con GitHub incluida en ChatGPT Business (sin API de OpenAI). ChatGPT, si el usuario lo usa, queda limitado a crear la incidencia inicial y aplicar la etiqueta de arranque; no ejecuta ninguno de los tres roles ni el merge (§8).

Su finalidad es que el usuario pueda escribir una orden breve, por ejemplo `Implementa B4e`, y que el sistema prepare la tarea, implemente, valide, revise, corrija de forma limitada y notifique el resultado sin copiar ni pegar prompts manualmente.

La automatización no convierte a ningún agente en autoridad de producto o arquitectura y no autoriza merge automático.

## 1. Decisión operativa

Tras el merge humano de la PR #44 queda autorizada, para todo Sirius 0.1, la automatización secuencial de:

1. creación de una incidencia de trabajo estructurada;
2. implementación en rama propia;
3. ejecución de pruebas y CI;
4. revisión independiente;
5. corrección automática limitada;
6. repetición de CI y revisión;
7. notificación del resultado al usuario;
8. cierre posterior al merge humano.

No será necesaria una autorización administrativa distinta para cada subbloque. Cada tarea deberá permanecer dentro del alcance ya aprobado.

## 2. Fuente de verdad y disparadores

La incidencia de trabajo es la fuente de verdad de cada bloque. Debe contener como mínimo:

- identificador y bloque;
- objetivo;
- alcance permitido y fuera de alcance;
- requisitos y pruebas vinculadas;
- comandos de validación;
- rama y PR asociadas;
- head SHA vigente;
- contador de correcciones;
- resultado actual;
- decisiones pendientes;
- prohibición de merge automático.

Las etiquetas representan estados o transiciones; no contienen el prompt completo.

Eventos consumibles:

- `sirius:implement-requested`
- `sirius:review-requested`
- `sirius:repair-requested`

Estados persistentes:

- `sirius:planned`
- `sirius:implementing`
- `sirius:ci-pending`
- `sirius:reviewing`
- `sirius:repairing`
- `sirius:ready-for-merge`
- `sirius:blocked-decision`
- `sirius:failed-safely`
- `sirius:completed`

## 3. Implementación

La Routine implementadora genérica puede:

- crear una rama desde la base registrada;
- modificar código, pruebas y documentación de implementación dentro del alcance;
- ejecutar Ruff, mypy, pytest y validaciones existentes;
- realizar commits y push en la rama de trabajo;
- abrir o actualizar una PR;
- registrar rama, PR y head SHA en la incidencia.

Debe detenerse sin merge y dejar el trabajo en `sirius:ci-pending`, `sirius:blocked-decision` o `sirius:failed-safely`.

## 4. CI y revisión

Cuando `Quality` termine sobre el head registrado:

- si pasa, se solicita automáticamente revisión independiente;
- si falla por una causa técnica concreta y segura, se solicita corrección;
- si no es seguro corregir automáticamente, se detiene en `sirius:failed-safely`.

La Routine revisora debe ser independiente de la implementación y revisar el head exacto aprobado por CI.

Resultados permitidos:

- `REVIEW_APPROVED` -> `sirius:ready-for-merge`
- `CHANGES_REQUESTED` -> `sirius:repair-requested`
- `BLOCKED_BY_DECISION` -> `sirius:blocked-decision`
- `FAILED_SAFELY` -> `sirius:failed-safely`

### 4.1 Revisión dual Claude + Codex (bandera de repositorio)

La variable de repositorio `SIRIUS_CODEX_REVIEW_ENABLED` gobierna el modo de
revisión dentro de `review-sirius-work.yml`:

- **ausente o distinta de `true`:** revisión solo con Claude, el comportamiento
  vigente antes de esta versión;
- **`true`:** revisión dual obligatoria. Tras Quality en verde sobre el head
  registrado, esa misma versión es revisada por dos revisores independientes:
  el revisor Claude actual y Codex mediante su integración nativa con GitHub
  (incluida en ChatGPT Business; sin API de OpenAI, sin claves nuevas y sin
  costes nuevos).

Reglas del modo dual:

- El workflow publica de forma idempotente un único comentario disparador
  `@codex review` por PR y head, con un marcador oculto estable
  (`<!-- sirius-codex-review:<head> -->`), mediante el paso determinista
  (`scripts/automation/sirius_codex_review.py`). La revisión automática del
  panel de Codex permanece apagada: el disparo ocurre solo después de Quality.
- Codex actúa únicamente como segundo revisor de solo lectura: la
  automatización nunca le pide corregir, comitear, hacer push ni fusionar.
- Ambos revisores deben revisar exactamente el mismo SHA que superó Quality.
  El recolector solo acepta resultados del conector oficial de Codex
  (allowlist), posteriores al disparador y demostrablemente referidos a ese
  SHA (`commit_id` de la revisión o el marcador `Reviewed commit:`). La
  ausencia de comentarios no es aprobación: la aprobación exige una revisión
  formal `APPROVED` o una reacción `+1` del conector sobre el disparador.
- Un agregador determinista (`scripts/automation/sirius_aggregate_reviews.py`)
  combina ambos resultados sin votos ni arbitraje de otro modelo, con esta
  precedencia: JSON inválido de un revisor obligatorio → `FAILED_SAFELY`; SHA
  distinto o no demostrable → `FAILED_SAFELY`; `FAILED_SAFELY` de cualquiera →
  `FAILED_SAFELY`; `BLOCKED_BY_DECISION` de Claude → `BLOCKED_BY_DECISION`;
  `CHANGES_REQUESTED` de cualquiera → `CHANGES_REQUESTED`; solo si ambos
  aprueban el mismo SHA → `REVIEW_APPROVED`.
- Con la revisión dual activada Codex es obligatorio: timeout
  (`SIRIUS_CODEX_REVIEW_TIMEOUT_SECONDS`, 1200 s por defecto), respuesta sobre
  otro SHA, autor no autorizado o resultado ambiguo terminan la ronda en
  `FAILED_SAFELY`, nunca en aprobación silenciosa ni en degradación automática
  a revisión solo Claude.
- Las observaciones combinadas conservan su procedencia (prefijos `CLAUDE-` y
  `CODEX-`), se deduplican solo cuando son duplicados exactos y llegan al
  corrector en la misma lista estructurada única (`OBSERVACIONES_ESTRUCTURADAS`)
  de una sola ronda. Claude sigue siendo el único corrector y se conserva el
  máximo de dos ciclos (§5).
- El veredicto de revisión (de Claude o agregado) debe declarar
  `reviewed_head_sha`; `sirius_apply_verdict.sh` exige para `REVIEW_APPROVED`
  y `CHANGES_REQUESTED` una PR única, abierta y no borrador, y la coincidencia
  exacta entre el head actual de la PR, el último head que superó Quality y el
  `reviewed_head_sha` declarado. Cualquier divergencia detiene la incidencia
  de forma segura.
- Desactivar la bandera devuelve inmediatamente el flujo a revisión solo
  Claude sin revertir commits. La activación estable solo se decidirá tras un
  piloto controlado posterior al merge de esta implementación.

## 5. Corrección automática limitada

La Routine correctora solo puede resolver observaciones técnicas concretas y estructuradas en la misma rama y PR.

Puede corregir defectos de implementación, pruebas insuficientes, lint, tipos, imports, errores deterministas de CI y migraciones aditivas o reversibles dentro del diseño aprobado.

Debe detenerse ante cambios de producto, arquitectura, ATD, seguridad no definida, migraciones destructivas, pérdida de datos, nuevos costes, credenciales reales o datos personales.

Se permiten como máximo dos ciclos de revisión-corrección. Si no converge, el estado final es `sirius:blocked-decision`.

## 6. Idempotencia y protección contra bucles

Cada transición debe comprobar:

- identificador único de trabajo;
- estado actual permitido;
- head SHA esperado;
- ausencia de otra ejecución activa para el mismo trabajo y estado;
- que la etiqueta de evento no haya sido consumida;
- contador de ciclos.

Los webhooks repetidos no deben duplicar ramas, PR, revisiones, correcciones ni notificaciones.

Además, toda lectura o escritura del cuerpo de una incidencia debe ser robusta
(ver `SIRIUS_GENERIC_ROUTINES_0.1.md` §0 y `scripts/automation/sirius_issue.sh`):

- ninguna automatización depende de una sola vía de lectura: REST (`gh api`) con
  reintentos y respaldo GraphQL;
- una respuesta truncada nunca se acepta como cuerpo completo; se valida que
  contenga todas las secciones obligatorias del contrato;
- una escritura del cuerpo se construye en un archivo, se respalda el cuerpo
  anterior, se escribe de una sola vez y se vuelve a leer para comparar longitud
  y hash; si no coincide, la escritura se considera fallida;
- nunca se sobrescribe una incidencia usando como fuente un cuerpo ya truncado;
- `sirius:failed-safely` solo se aplica cuando han fallado todas las vías
  permitidas, no hay una fuente local aprobada suficiente y continuar podría
  producir un cambio incorrecto; un error temporal de una sola API no fuerza por
  sí mismo una parada segura;
- los workflows de transición y notificación toleran fallos secundarios: un error
  transitorio de una API no debe volver roja la canalización ni dejar una
  transición a medias (la etiqueta se aplica antes que el comentario con marcador
  de idempotencia).

## 7. Notificaciones

ChatGPT no puede iniciar una conversación ni avisar por sí solo cuando termina una ejecución.

El canal operativo será GitHub. Al alcanzar cualquiera de estos estados, una automatización deberá mencionar **una sola vez** al usuario en la incidencia (sin autoasignación) y generar una notificación en español compatible con GitHub Mobile:

- `sirius:implementing`
- `sirius:repair-requested`
- `sirius:ready-for-merge`
- `sirius:blocked-decision`
- `sirius:failed-safely`
- `sirius:completed`

Los estados internos (`sirius:planned`, `sirius:ci-pending`, `sirius:review-requested`, `sirius:reviewing`, `sirius:repairing`) no generan notificación.

La notificación es secundaria y nunca debe romper el flujo principal: ante un fallo de lectura o publicación deja un aviso en los logs y termina con éxito. Debe emitirse una sola vez por combinación incidencia-estado-head (se usa `no-head` como identificador estable cuando aún no hay head registrado).

## 8. Merge

El merge permanece bajo control humano. Lo que cambia en esta versión es
únicamente el canal de autorización y quién ejecuta el comando técnico; la
decisión de fusionar sigue siendo exclusivamente del usuario para cada PR
concreta.

Ningún agente, Routine, workflow o aplicación puede fusionar una PR sin una
autorización explícita del usuario para ese merge. Esa autorización se
expresa mediante un comentario del propietario del repositorio, con la
palabra exacta `fusiona`, escrito directamente sobre la incidencia que está en
`sirius:ready-for-merge`. Ninguna otra persona, bot o cuenta puede
autorizarlo: el workflow verifica `author_association == OWNER` antes de
actuar.

La ejecución técnica del merge la realiza `.github/workflows/merge-sirius-work.yml`
(vía `scripts/automation/sirius_merge_on_command.sh`), disparado únicamente por
ese comentario. Antes de fusionar se verificará por REST, en el momento del
comentario (no solo cuando se alcanzó `ready-for-merge`):

- que la incidencia sigue en `sirius:ready-for-merge`;
- que existe una única PR asociada, abierta y fusionable (no borrador, no
  fusionada ya, sin conflictos con la rama base);
- CI (`Quality`) verde sobre el head actual de esa PR;
- que ese head coincide con el último Head/Merge SHA aprobado registrado en la
  incidencia (ausencia de cambios posteriores a la aprobación sin revisar);
- ausencia de otros bloqueos detectados.

Si cualquier condición falla, el workflow no fusiona: publica en la incidencia
una explicación concreta del motivo y se detiene. No reintenta por su cuenta;
una nueva autorización requiere que el usuario vuelva a escribir `fusiona`
después de resolver lo señalado.

Tras un merge exitoso, `complete-sirius-after-merge.yml` sigue siendo quien
transiciona la incidencia a `sirius:completed` y la cierra, exactamente como
antes de este cambio.

## 9. Prohibiciones

Está prohibido:

- push directo a `main`;
- fusionar una PR sin el comentario explícito de autorización descrito en §8
  (ese comentario, no la mera llegada a `sirius:ready-for-merge`, es la
  autorización);
- reducir o falsear pruebas para conseguir verde;
- ocultar fallos;
- introducir servicios de pago, APIs, claves o suscripciones no aprobadas;
- usar secretos reales o datos personales en pruebas automáticas;
- cambiar Producto, Arquitectura Técnica, ATD o documentos canónicos sin decisión explícita;
- convertir una idea exploratoria en una decisión aprobada;
- usar vigilancia horaria como motor del flujo;
- iniciar bloques sucesivos sin orden del usuario o cola expresamente aprobada.

## 10. Entrada en vigor y cambio registrado

- **Decisión:** sustituir autorizaciones puntuales por subbloque por una autorización general de implementación, revisión y corrección automática limitada para Sirius 0.1.
- **Motivo:** eliminar trabajo manual repetitivo y permitir que el usuario solo intervenga ante decisiones reales y merge.
- **Alcance:** B4d, B4e, B4f y verticales posteriores de Sirius 0.1 dentro del alcance aprobado.
- **Mantiene:** revisión independiente, máximo de dos ciclos, trazabilidad, seguridad y merge humano.
- **Entrada en vigor:** únicamente cuando la PR #44 sea revisada, tenga CI verde y sea fusionada por autorización explícita del usuario.

### 10.1 Versión 1.2 — merge nativo de GitHub por comentario

- **Decisión:** sustituir el flujo de autorización de merge basado en pedirle a ChatGPT que ejecutara `Fusiona` por un mecanismo nativo de GitHub: el propietario escribe el comentario exacto `fusiona` sobre la incidencia en `sirius:ready-for-merge`, y `.github/workflows/merge-sirius-work.yml` ejecuta el merge tras reverificar por REST todas las condiciones del §8.
- **Motivo:** permitir que el usuario autorice el único paso que le queda (el merge) sin depender de abrir una conversación con ChatGPT; reduce a un solo canal (GitHub) el lugar donde ocurre todo el ciclo de un bloque.
- **Alcance:** exclusivamente la ejecución técnica del merge y la redacción de §8/§9 de este contrato, `AUTOMATION_STATE_MACHINE_SIRIUS_0.1.md` §2.1/§4.6/§4.7/§8 y el texto de `notify-sirius-state.yml`. No cambia la implementación, revisión ni corrección automática, que siguen siendo responsabilidad exclusiva de Claude Code/Routines.
- **Mantiene:** el merge permanece bajo control humano y bajo autorización explícita del usuario para cada PR; solo cambia el canal de esa autorización y quién teclea el comando técnico.
- **Entrada en vigor:** cuando la PR que introduce `merge-sirius-work.yml` y `sirius_merge_on_command.sh` sea revisada, tenga CI verde y sea fusionada por autorización explícita del usuario (con el mecanismo anterior, ya que este todavía no existe).

### 10.2 Versión 1.3 — ejecución real de las tres Routines dentro del repositorio

- **Decisión:** sustituir la referencia a una interfaz externa de Claude/Routines (no inspeccionable desde el repositorio, sin single-flight garantizado) por tres workflows de GitHub Actions (`implement-sirius-work.yml`, `review-sirius-work.yml`, `repair-sirius-work.yml`) que ejecutan Claude Code real mediante `anthropics/claude-code-action`, con un script determinista (`sirius_apply_verdict.sh`) que aplica el veredicto del agente reverificándolo por su cuenta.
- **Motivo:** el mecanismo anterior era un plan sin mecanismo de ejecución verificable desde el repositorio, y su ausencia de garantía de ejecución única fue la causa raíz del incidente de PRs duplicadas (#52/#53). El nuevo mecanismo es autocontenido, auditable en Git y usa `concurrency` de GitHub Actions para garantizar una sola ejecución activa por incidencia entre los tres roles.
- **Alcance:** exclusivamente el mecanismo de ejecución de implementación/revisión/corrección y la redacción de §0 de este contrato y de `SIRIUS_GENERIC_ROUTINES_0.1.md` §6. No cambia el contrato de estados, el límite de dos ciclos de corrección, ni el mecanismo de merge (§8, ya actualizado en la v1.2).
- **Mantiene:** ChatGPT sigue disponible como front-end conversacional para crear incidencias; deja de tener ningún rol de ejecución en el ciclo automático.
- **Pendiente de la primera ejecución real:** el secreto `CLAUDE_CODE_OAUTH_TOKEN` (o `ANTHROPIC_API_KEY`) debe añadirse a los secretos del repositorio antes de que estos workflows puedan completar su trabajo; sin él, la puerta de activación y las comprobaciones deterministas siguen funcionando, pero el paso de Claude Code fallará y la incidencia terminará en `sirius:failed-safely`.
- **Entrada en vigor:** cuando la PR que introduce estos tres workflows sea revisada, tenga CI verde y sea fusionada por autorización explícita del usuario.

### 10.3 Versión 1.4 — revisión dual Claude + Codex tras Quality

- **Decisión:** aprobada por el usuario el 3 de agosto de 2026. Después de que
  Quality termine en verde sobre un head concreto, esa misma versión es
  revisada por dos revisores independientes: Claude (el revisor actual) y
  Codex mediante su integración nativa con GitHub incluida en ChatGPT
  Business. Un agregador determinista combina ambos resultados en un único
  veredicto; Claude sigue siendo el implementador, uno de los dos revisores y
  el único corrector.
- **Motivo:** añadir una segunda revisión independiente real sin introducir la
  API de OpenAI, claves nuevas, servicios de pago ni un segundo flujo: la
  prueba manual en la PR #122 confirmó que el comentario `@codex review`
  activa una revisión formal, con comentarios por archivo y línea, sin
  modificar el código.
- **Alcance:** exclusivamente el mecanismo de revisión
  (`review-sirius-work.yml`, `sirius_codex_review.py`,
  `sirius_aggregate_reviews.py`, el endurecimiento de
  `sirius_apply_verdict.sh` y `prompts/reviewer.md`) y la redacción de §4 de
  este contrato. No cambia la implementación, la corrección (mismo corrector
  Claude, mismas `OBSERVACIONES_ESTRUCTURADAS`, máximo de dos ciclos), la
  máquina de estados ni el mecanismo de merge (§8): `fusiona` sigue siendo la
  única autorización humana de merge.
- **Mantiene:** mismo head exacto para CI, ambos revisores y el veredicto;
  fallo seguro obligatorio si Codex no responde, responde sobre otro SHA o su
  resultado no es identificable; Codex sin ningún permiso de escritura;
  reversibilidad total mediante `SIRIUS_CODEX_REVIEW_ENABLED` sin revertir
  commits.
- **Pendiente del piloto posterior al merge:** que un comentario publicado
  automáticamente con el token de los workflows active la integración de
  Codex es una dependencia externa aún no verificada. La bandera queda
  desactivada por defecto; tras el merge se realizará un piloto controlado
  (una PR pequeña, bandera activada, verificación de disparador único, SHA
  correcto, veredicto único y rollback) y solo entonces se decidirá su
  activación estable.
- **Entrada en vigor:** cuando la PR que introduce la revisión dual sea
  revisada, tenga CI verde y sea fusionada por autorización explícita del
  usuario. La activación de la bandera queda fuera de esa entrada en vigor y
  requiere el piloto.

El historial de las versiones 1.0, 1.1, 1.2 y 1.3 permanece disponible en Git y no se reescribe retrospectivamente.
