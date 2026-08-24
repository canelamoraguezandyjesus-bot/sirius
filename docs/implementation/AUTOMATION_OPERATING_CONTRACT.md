# SIRIUS - Contrato operativo de automatización

- **Versión:** 1.9
- **Fecha:** 22 de agosto de 2026
- **Estado:** VIGENTE (§4, §5, §9, §11 y §12 actualizadas; ver §10.3 a §10.9)
- **Autoridad:** Operativa para el desarrollo automatizado de Sirius 0.1
- **Sustituye:** versión 1.8 del 21 de agosto de 2026
- **No modifica:** Producto, Arquitectura Técnica, ATD, requisitos ni alcance de Sirius 0.1

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

- **ausente o distinta de `true`:** revisión solo con Claude, como antes de
  esta versión. El endurecimiento común de la verificación de head — el gate
  del workflow que exige que el head actual coincida con el último que superó
  Quality, y el `reviewed_head_sha` obligatorio en el paso determinista —
  aplica en ambos modos: es parte de esta versión del contrato, no de la
  bandera. En cambio, la lectura del instante en que Quality terminó
  (`check-runs`), que solo consume el disparador de Codex, se exige únicamente
  en modo dual: exigirla con la bandera apagada dejaría que un 403 sobre ese
  endpoint matara una ronda solo-Claude y la bandera dejaría de ser reversible
  de verdad;
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
- Un disparador solo se reutiliza si lo emitió la propia automatización: se
  verifica que el autor del comentario es la identidad real del token y que su
  cuerpo coincide exactamente con la plantilla determinista. El marcador es
  predecible, así que un comentario ajeno que lo contuviera podría, si no, hacer
  que una revisión de Codex no solicitada por el workflow quedara «posterior al
  disparador» y satisficiera la ronda. Si no puede demostrarse la identidad, la
  ronda se detiene de forma segura.
- El presupuesto de tiempo es explícito: el revisor Claude y la recolección de
  Codex están acotados por paso, el job cubre la suma de ambos y la espera
  configurada se limita a `SIRIUS_CODEX_REVIEW_MAX_TIMEOUT_SECONDS` (1500 s por
  defecto), de modo que el recolector siempre llega a escribir su resultado
  estructurado antes de que el paso expire; un valor excesivo en la variable de
  repositorio no puede convertir el fallo seguro en una cancelación sin
  veredicto.
- Codex actúa únicamente como segundo revisor de solo lectura: la
  automatización nunca le pide corregir, comitear, hacer push ni fusionar.
- Ambos revisores deben revisar exactamente el mismo SHA que superó Quality.
  El recolector solo acepta resultados del conector oficial de Codex
  (allowlist), posteriores al disparador y demostrablemente referidos a ese
  SHA (`commit_id` de la revisión o el marcador `Reviewed commit:`). La
  ausencia de señales no es aprobación: aprobar exige una señal explícita del
  conector, y solo se admiten tres —una revisión formal `APPROVED`, una reacción
  `+1` sobre el disparador, o un comentario de la conversación que **declare
  ausencia de hallazgos en la fórmula conocida** del conector, con las mismas
  comprobaciones de autor, orden temporal y SHA que cualquier otra señal—.
- El tercer canal existe porque los otros dos no ocurren con este conector
  (v1.6.1). Observado en la PR #178: en seis rondas con hallazgos publicó
  revisiones formales, todas `COMMENTED` y ninguna `APPROVED`; en la ronda sin
  hallazgos publicó un comentario («Codex Review: Didn't find any major issues»)
  y **no** marcó 👍 el disparador, pese a que su propio texto lo promete. Con
  solo los dos canales anteriores, ninguna PR limpia podía alcanzar
  `sirius:ready-for-merge`: el modo dual quedaba estructuralmente bloqueado.
- El reconocimiento de esa fórmula es **deliberadamente estrecho** y falla
  cerrado: solo variantes de la afirmación observada («did(n't) find any
  [major] issues») aprueban, y un comentario que además traiga insignias de
  severidad no aprueba aunque la contenga. Cualquier otra redacción sigue siendo
  la parada segura `respuesta-por-comentario`. Si el conector cambia su texto, el
  coste es una ronda detenida que mira una persona, nunca una aprobación falsa.
  Esta señal aporta, además, solo la mitad del veredicto: la precedencia del
  agregador (más abajo en esta misma sección) exige que Claude apruebe también
  el mismo SHA para que la ronda termine en `REVIEW_APPROVED`.
- Se consideran **todos** los comentarios del conector referidos al head
  esperado, no solo uno, y basta uno que no declare ausencia de hallazgos para
  detener la ronda — el mismo principio que ya rige para las revisiones. Decidir
  con el primero dejaría que un comentario intermedio bloqueara una ronda
  limpia; decidir con el último dejaría que una declaración posterior enterrara
  un comentario anterior con hallazgos. Exigirlo de todos quita la dependencia
  del orden de llegada por los dos lados.
- Se consideran **todas** las revisiones del conector posteriores al
  disparador, no solo la última: sus hallazgos se unen y basta una que no
  demuestre el SHA esperado para detener la ronda. Quedarse con la última
  descartaría en silencio los hallazgos de las anteriores y, si la última fuera
  aprobatoria, la ronda aprobaría un head con defectos ya reportados.
- La unión solo se acepta cuando **cada** revisión formal no aprobatoria ha
  entregado algo. Basta una que no haya entregado ni cuerpo ni comentarios
  inline para que la ronda siga sin interpretar, aunque otras ya hayan aportado
  hallazgos: entregar la lista parcial dejaría que la ventana de estabilidad
  cerrara sobre ella —el mismo resultado se repite pasada tras pasada— y los
  hallazgos que faltan no llegarían nunca al corrector, con apariencia de lista
  completa. El discriminante es haber entregado algo, no tener comentarios
  inline: el conector publica también resúmenes cuyo contenido vive entero en el
  cuerpo, y esos están completos —su endpoint de comentarios queda vacío para
  siempre—, así que exigirles comentarios convertiría cada ronda legítima con
  resumen en un timeout. De los comentarios que lleguen tarde se encarga la
  ventana de estabilidad.
- Una revisión solo cuenta si es **estrictamente posterior** al disparador.
  `submitted_at` tiene resolución de segundo, así que un empate no demuestra el
  orden causal: aceptarlo dejaría que una revisión automática del panel, o una
  manual previa, satisficiera la ronda sin que Codex haya respondido al
  comentario posterior a Quality.
- La reacción `+1` solo decide cuando **no** hay ninguna revisión formal
  posterior al disparador. Con una revisión formal en curso pero todavía no
  interpretable, la reacción no la resuelve: se sigue esperando y, si no se
  aclara, la ronda termina en fallo seguro. Una reacción es una señal más débil
  que una revisión y no puede convertir una ambigüedad en aprobación.
- El resultado no se entrega en cuanto aparece: se exige observarlo **dos veces
  igual**, con una ventana de estabilidad de por medio
  (`SIRIUS_CODEX_SETTLE_SECONDS`, 60 s por defecto), y cualquier hallazgo nuevo
  reinicia esa ventana. Unir todas las revisiones de la ronda solo sirve si se
  han publicado ya: cerrar el sondeo en cuanto la primera revisión trae un
  comentario dejaría fuera las posteriores y el corrector recibiría una lista
  incompleta con apariencia de completa. La ventana está acotada por el plazo
  absoluto: al vencer este se entrega lo observado, nunca un timeout falso
  teniendo hallazgos a la vista. Una parada segura no espera. Si una pasada
  posterior deja de ser interpretable —típicamente porque apareció una revisión
  formal sin comentarios visibles—, el resultado que se estaba estabilizando se
  **descarta**: conservarlo permitiría aprobar el head pese a una revisión
  pendiente que el propio recolector declara ambigua. Un fallo de transporte no
  descarta nada: no es evidencia de ambigüedad, solo de que no se pudo mirar.
  Cada pausa de sondeo se acota al plazo absoluto (y al cierre de la ventana),
  para que el plazo prometido sea exacto y no aproximado.
- La deduplicación de observaciones neutraliza las URL de `prueba`, solo de ese
  campo y solo para la procedencia `CODEX`, al construir su clave. En los hallazgos de Codex `prueba` es el
  permalink del comentario que lo reportó, distinto para cada comentario aunque
  el defecto sea el mismo: con el enlace dentro de la clave, un hallazgo
  repetido en dos revisiones no se dedupararía nunca y `pending` y
  `severity_total` contarían comentarios en vez de defectos, falseando la medida
  de convergencia. La neutralización NO se extiende al resto de campos: dos
  hallazgos cuyo `problema` se distingue precisamente por una URL —dos
  advisories, dos endpoints— se fusionarían y uno se perdería, y borrar un
  hallazgo real es peor que conservar dos parecidos. Tampoco se extiende a la
  procedencia `CLAUDE`: dar por supuesto que su `prueba` nunca es un enlace
  sería una suposición sobre la salida de un modelo, no una garantía.
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
  de una sola ronda. Claude sigue siendo el único corrector, sujeto a la
  política de convergencia del §5.
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

### 5.1 Convergencia técnica en vez de un tope fijo de ciclos

No existe un límite total fijo de ciclos de revisión-corrección. El tope anterior de dos ciclos era arbitrario y detenía trabajos que seguían siendo puramente técnicos y que progresaban ronda a ronda.

La corrección automática continúa mientras se cumplan todas estas condiciones:

- los fallos siguen siendo técnicos;
- permanecen dentro del alcance aprobado;
- hay progreso comprobable;
- no aparece una decisión humana real;
- no hay oscilación ni repetición sin progreso.

Cada ronda de `CHANGES_REQUESTED` publica en la incidencia un registro estructurado (`<!-- sirius-round:N -->` con un bloque `## RONDA_HALLAZGOS`) que contiene, por hallazgo, una huella estable, su severidad y su procedencia, además del head de la ronda y los totales. La huella no depende ni del identificador correlativo (`CODEX-001`, que cambia entre rondas) ni del número de línea (que se desplaza en cuanto se edita cualquier punto anterior del archivo), de modo que un mismo defecto conserva su huella entre rondas.

La severidad de una huella es **pegajosa**: cuenta siempre la peor jamás observada para ella mientras siga pendiente. Sin esa regla, un revisor que omitiera la insignia de un hallazgo P0 que sigue ahí haría bajar la severidad agregada por sí sola, y esa mejora fantasma bastaría para superar la comprobación de progreso sin haber corregido nada.

El marcador del comentario que arrastra el registro depende del head y del **run** de Actions, no del intento: una reejecución del mismo run es idempotente —no duplica el registro— y una ronda nueva, que siempre es un run nuevo, siempre se registra.

La deduplicación por marcador solo reconoce marcadores de **autor de confianza** (propietario o `github-actions[bot]`), igual que el resto de lecturas de comentarios. Los marcadores son predecibles —`sirius-quality:<head>:failure` se deriva del SHA público de la PR—, así que una deduplicación ciega al autor sería un interruptor abierto: bastaba con publicar el marcador antes que el flujo para que la transición se diera por hecha y omitiera su propio comentario. La etiqueta se aplicaba, pero el registro oficial no llegaba a existir y, como las cuentas sí filtran por autor, ese fallo de Quality quedaba invisible para la racha del §5.1 y su cota podía eludirse indefinidamente. Con el filtro, un marcador ajeno sencillamente no existe para la automatización: el registro oficial se publica siempre y la deduplicación sigue operando entre comentarios propios, que es lo único que prueba que el paso ya se ejecutó.

`scripts/automation/sirius_convergence.py` decide de forma determinista a partir de ese historial. Hay **progreso** cuando el par `(hallazgos pendientes, severidad agregada)` **disminuye estrictamente en el orden producto**: al menos una de las dos magnitudes baja y ninguna sube. Nada más cuenta.

Esa definición es lo que convierte la terminación en una propiedad demostrable y no en una expectativa. Dos alternativas más laxas fallan:

- Mirar cada magnitud por separado permitiría alternar indefinidamente entre estados que mejoran una a costa de la otra (un hallazgo P0, luego dos P3, luego un P0 otra vez), sin activar nunca reaparición, oscilación ni dos rondas sin progreso.
- Inferir progreso de que "desapareció una huella" permitiría mantener el ciclo abierto para siempre reformulando el mismo defecto con otras palabras, porque la huella incluye el texto del problema.

Con el orden producto sobre ℕ² —bien fundado— cada ronda que continúa por progreso decrece estrictamente una cantidad que no puede decrecer sin fin, y las rondas sin progreso se agotan por la regla de dos consecutivas.

No cuentan como progreso los cambios cosméticos, los renombrados, los cambios de comentario, la renumeración de identificadores, la reformulación de un hallazgo persistente, la sustitución de un fallo por otro equivalente ni el silenciamiento de pruebas: ninguno hace disminuir el par.

Los registros de ronda son autoritativos solo si los publicó la propia automatización: la lectura acepta únicamente comentarios del propietario del repositorio —misma frontera de confianza que el `fusiona` del §8— o del bot de Actions, y exige el marcador `<!-- sirius-round:N -->` en el mismo comentario que el bloque. El número de ronda autoritativo es el del marcador, no un campo del JSON.

El ciclo pasa a `sirius:blocked-decision`, con el motivo exacto registrado, únicamente cuando:

- no hay progreso neto en dos rondas consecutivas;
- un hallazgo dado por resuelto reaparece en una ronda posterior;
- el conjunto de hallazgos oscila entre estados anteriores;
- el head no avanzó entre dos rondas (no hubo corrección efectiva que revisar);
- Quality tumba `MAX_CI_FAILURE_STREAK` intentos de corrección seguidos (3) sin un verde de por
  medio. La cuenta es de **heads distintos**, no de marcadores: cada intento del corrector es
  forzosamente un commit nuevo, así que dos resultados de Quality sobre el mismo head —una
  reejecución que pase de `failure` a `timed_out`, cosa que una prueba intermitente vuelve
  rutinaria— siguen siendo un solo intento y no pueden gastar el margen sin que el corrector
  haya vuelto a probar nada;
- el historial de rondas no se puede leer, o se puede leer pero la ronda no se puede numerar (numerar a ciegas repetiría un número ya usado, colaría la ronda nueva al principio del historial ordenado y falsearía la medida);
- o concurre cualquiera de las causas de parada del párrafo tercero de este apartado (producto, arquitectura, alcance, credenciales, permisos, costes, datos reales u operaciones irreversibles).

Un problema técnico corregible nunca se convierte automáticamente en una decisión humana.

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
- usar vigilancia periódica como **motor** del flujo (excepciones acotadas en §9.1 y
  §12.2; fuera de ellas sigue prohibida);
- iniciar bloques sucesivos sin orden del usuario o cola expresamente aprobada
  (§12.1 precisa qué cuenta como orden del usuario y quién puede transportarla).

### 9.1 Excepción: red de seguridad periódica que no es motor

La prohibición anterior existe para que el flujo lo dirijan los eventos y no una
tarea que sondea. Esa razón no alcanza a un caso: **un proceso que muere no
puede informar de su propia muerte**, y `issues: labeled` no vuelve a dispararse
con una etiqueta ya aplicada. Cuando una ejecución muere a mitad, la incidencia
queda en un estado que ningún evento futuro puede mover, y el flujo por eventos
—por construcción— no puede notarlo.

Queda permitida, por tanto, **una** ejecución periódica, sujeta a todo lo
siguiente. Si un cambio futuro rompe cualquiera de estos límites, deja de estar
amparado por esta excepción y necesita una decisión nueva:

1. **No inicia trabajo.** No aplica **nunca** `sirius:implement-requested`, que
   es la etiqueta que arranca un bloque nuevo. La redacción anterior decía «ni
   ninguna otra etiqueta que arranque un bloque», y **era falsa**: el caso B
   aplica `sirius:review-requested` para reparar una transición perdida. Eso no
   inicia un bloque —el bloque ya estaba en marcha— pero sí despierta al
   revisor, así que queda bajo el límite 2 y no bajo este. Es la única etiqueta
   disparadora que este workflow escribe, y solo desde `sirius:ci-pending`.
   Lo comprueban ejecutando dos pruebas, no una: RECON-STUCK-007 recorre todos
   los demás caminos y exige que no se escriba ninguna disparadora, y
   RECON-STUCK-013 exige que desde `ci-pending` con Quality verde se escriba
   `review-requested` y solo esa. Ambas miran CADA escritura de etiqueta, no el
   estado final: retirar y volver a poner deja el mismo estado y dispara un
   evento nuevo.
2. **No avanza un ciclo sano.** Solo repara estados inequívocos que ya estaban
   mal (los casos A y B de `scripts/automation/sirius_reconcile.sh`), y esos
   mismos casos son reparables hoy a mano sin esta excepción.
3. **No fusiona.** El merge sigue siendo humano y exige el comentario de §8.
4. **Ante la duda, informa y no toca.** Un estado que no puede fechar o cuya
   situación es ambigua produce un aviso, nunca una acción. «Duda» incluye **no
   haber podido leer**: si las etiquetas, los comentarios o el cuerpo de una
   incidencia fallan en todas sus vías, esa incidencia se omite entera en esa
   pasada —sin comprobarla y sin comentario— y consta en el resumen del job.
   Un fichero vacío por un 503 es byte a byte el de una incidencia sana, así que
   usarlo como dato era afirmar hechos que nadie había leído. Lo comprueban
   ejecutando RECON-AUD-011 a RECON-AUD-016, una por cada lectura y por cada
   afirmación que se derivaba de ella.
5. **No sustituye a ningún productor de eventos.** Si el flujo por eventos
   funciona, esta ejecución no hace nada.

Hoy la implementa `.github/workflows/reconcile-sirius-states.yml` con cadencia de
seis horas. La cadencia se eligió por coste —cada hora costaría ~720 minutos de
Actions al mes sobre los 2000 gratuitos de un repositorio privado, y seis horas
cuestan ~120—, y **ese argumento dejó de aplicar** cuando el repositorio pasó a
ser público (ADR-044): los runners estándar de Actions no consumen cuota en un
repositorio público. La cadencia se mantiene en seis horas por una razón
distinta, que sí sigue en pie: el reconciliador es una excepción a «los eventos
mandan», y una excepción que corre cada hora se parece demasiado a un motor.
Acortarla ya no es un cambio de coste; es un cambio de arquitectura y se decide
como tal.

Consecuencia que conviene decir en voz alta: el **caso B** del reconciliador
—`sirius:ci-pending` con Quality ya en verde— pasa a repararse **sin
supervisión**, y esa reparación despierta al revisor. No es trabajo nuevo: es
exactamente lo que `advance-sirius-after-quality.yml` habría hecho si el evento
no se hubiera perdido. Pero antes ocurría solo cuando una persona lo pedía, y
ahora puede ocurrir de madrugada.

Para que eso siga dentro de los límites 2 y 5 hace falta una condición que la
primera versión de esta excepción no tenía: el caso B **solo repara si el estado
`ci-pending` lleva puesto más de `STUCK_MINUTES`**. Sin ella, un cron que se
dispare justo después de que Quality se ponga verde —con
`advance-sirius-after-quality.yml` encolado o corriendo— transiciona antes que
él: eso no es reparar un estado roto, es **sustituir al productor del evento y
avanzar un ciclo sano**, exactamente lo que los límites 2 y 5 prohíben.

Desde fuera no hay forma de distinguir «la transición se perdió» de «la
transición está en vuelo» salvo por el tiempo transcurrido. La condición se
aplica también a las ejecuciones manuales: la distinción no depende de quién
dispare. Todo esto es reversible quitando el `schedule:`.

Lo que esta excepción **no** resuelve: no detecta que un run murió —eso solo lo
sabe el run—, sino que un estado dejó de avanzar, que es lo único observable
desde fuera. Y no repara ese estado: avisa a una persona. Ver ADR-004.

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

### 10.4 Versión 1.5 — convergencia técnica en lugar del tope de dos ciclos

- **Decisión:** aprobada por el usuario el 3 de agosto de 2026. Se elimina el límite absoluto de dos ciclos de revisión-corrección y se sustituye por la política de convergencia demostrable del §5.1: la automatización sigue corrigiendo mientras haya progreso comprobable y se detiene, con motivo exacto, en cuanto deja de haberlo.
- **Motivo:** el tope fijo era arbitrario. Bloqueaba trabajos que seguían siendo puramente técnicos, estaban dentro del alcance aprobado y avanzaban ronda a ronda, obligando a una intervención humana que no decidía nada: solo autorizaba a continuar.
- **Alcance:** exclusivamente el mecanismo de continuación del ciclo de corrección — `scripts/automation/sirius_convergence.py` (nuevo), el registro de ronda que publica `sirius_apply_verdict.sh`, la puerta de `repair-sirius-work.yml`, `prompts/corrector.md`, la plantilla de work item (`.github/ISSUE_TEMPLATE/sirius-work-item.yml`, que declaraba el tope como campo obligatorio y por tanto autorizaba menos ciclos de los que la política ejecuta) y la redacción de §5 de este contrato y de los documentos operativos que citaban el tope. No cambia el contrato de estados, la revisión dual (§4), la verificación de head ni el mecanismo de merge (§8).
- **Mantiene:** la incidencia como fuente de verdad; una sola máquina de estados; Claude como implementador y único corrector; Claude y Codex como revisores cuando la bandera está activa; fallo seguro; verificación del SHA; Quality antes de la revisión; merge exclusivamente humano mediante `fusiona`; y reversibilidad. La terminación del ciclo la garantizan las condiciones de bloqueo, no un contador.
- **Entrada en vigor:** cuando la PR que introduce la política de convergencia sea revisada, tenga CI verde y sea fusionada por autorización explícita del usuario.

### 10.5 Versión 1.6 — red de seguridad periódica que no es motor del flujo

- **Decisión:** acotar la prohibición de vigilancia periódica a lo que de verdad prohibía —usarla como motor— y permitir una sola ejecución programada como red de seguridad, con los cinco límites del §9.1. Incidencia #138.
- **Motivo:** la única pieza capaz de notar una incidencia atascada por un run muerto (`reconcile-sirius-states.yml`) solo arrancaba si una persona pulsaba un botón, es decir, dependía de que un humano notara primero justo aquello que la automatización debía notar por él. Siete correcciones consecutivas fallaron por vivir dentro del run que puede morir; la octava habría fallado igual.
- **Alcance:** `reconcile-sirius-states.yml` (añade `schedule:`), `scripts/automation/sirius_reconcile.sh` (avisa en la incidencia cuando un estado de máquina lleva más de `STUCK_MINUTES` sin avanzar) y la redacción de §9. No cambia estados, ni la revisión dual (§4), ni la convergencia (§5), ni el merge (§8).
- **Mantiene:** que ninguna automatización fusione, inicie bloques ni avance un ciclo sano por sondeo; que ante la duda se informe en vez de actuar; y la reversibilidad —quitar el `schedule:` devuelve el comportamiento anterior sin tocar nada más—.
- **Entrada en vigor:** cuando la PR que introduce el `schedule:` sea revisada, tenga CI verde y sea fusionada por autorización explícita del usuario.

### 10.6 Versión 1.6.1 — el canal por el que Codex dice de verdad que no encontró nada

- **Decisión:** admitir como tercera señal de aprobación de Codex un comentario de la conversación que declare ausencia de hallazgos en la fórmula conocida del conector, con las mismas comprobaciones de autor, orden temporal y SHA que las otras dos. Incidencia #177.
- **Motivo:** los dos canales que §4.1 admitía —revisión formal `APPROVED` y reacción `+1`— no ocurren nunca con este conector. Comprobado sobre las siete rondas de la PR #178: seis revisiones formales, todas `COMMENTED` y ninguna `APPROVED`, y en la única ronda sin hallazgos un comentario («Codex Review: Didn't find any major issues») con el disparador a cero reacciones. No era una intermitencia: con la regla anterior ninguna PR limpia podía alcanzar `sirius:ready-for-merge` en modo dual. La incidencia #148 ya había visto ese mismo comentario y se corrigió entonces solo la mentira del timeout; segunda vez que muerde la misma familia, así que se corrige la regla y no el síntoma.
- **Alcance:** el reconocimiento de la señal en `scripts/automation/sirius_codex_review.py` (`_declares_no_findings` y el desenlace de `_check_conversation_comments`), sus pruebas, y la redacción de §4.1 y de esta sección. No cambia el contrato de estados, la precedencia del agregador, la convergencia (§5), la verificación de head, los permisos, ni el mecanismo de merge (§8). Ningún workflow se toca.
- **Mantiene:** que la ausencia de señales no aprueba jamás; la allowlist de autores; la exigencia de que la señal sea estrictamente posterior al disparador y demostrablemente sobre el SHA esperado; la precedencia —una revisión formal manda sobre señales más débiles, y el comentario solo se consulta cuando no hay ninguna—; que Codex sigue siendo obligatorio en modo dual; y que Claude debe aprobar el mismo SHA para que la ronda apruebe. El reconocimiento falla cerrado: una redacción distinta, o un comentario con insignias de severidad, sigue terminando en `respuesta-por-comentario`.
- **Numeración:** se usa un tercer nivel (1.6.1) a propósito. El plan aprobado del Work Engine (ADR-020, decisión 5) reserva **v1.7 para E1a** y **v1.8 para E1b**; tomar la 1.7 aquí habría obligado a renumerar un plan ya aprobado por una razón puramente contable. Esta enmienda además no añade capacidad: corrige la descripción de un canal de la revisión dual que la v1.4 ya introdujo.
- **Entrada en vigor:** cuando la PR que introduce este canal sea revisada, tenga CI verde y sea fusionada por autorización explícita del usuario.

### 10.7 Versión 1.7 — regla de autoridad por clase de trabajo (E1a)

- **Decisión:** fijar, ANTES de que el motor cree su primer WorkItem, quién es la autoridad de cada clase de trabajo, sin ningún estado ambiguo. Se añade §11. Incidencia del bloque E1a del plan del Work Engine (ADR-020).
- **Motivo:** A5 es el bloque que crea y activa el primer WorkItem del motor. Un WorkItem que nazca sin autoridad definida es exactamente el estado ambiguo que esta regla existe para impedir, y una vez creado ya no se puede arreglar sin reescribir historia. La regla va delante de A5, no detrás.
- **Alcance:** solo la autoridad. **No toca la activación ni la supervisión**, que llegan en la v1.8 (E1b), ni el mecanismo de merge (§8), ni la convergencia (§5), ni las notificaciones (§7), ni ningún workflow.
- **Mantiene:** §2 intacta mientras una clase no haya conmutado — para las clases con proyección en la vía GitHub, la incidencia sigue siendo la fuente de verdad hasta el acto fechado de su conmutación.
- **Entrada en vigor:** cuando la PR que introduce esta sección sea revisada, tenga CI verde y sea fusionada por autorización explícita del usuario.

### 10.8 Versión 1.8 — activación y supervisión del motor (E1b)

- **Decisión:** autorizar al motor de trabajo dos cosas que el contrato le prohibía, con sus límites, en la nueva §12: **transportar una orden ya dada** (aplicar `sirius:implement-requested` solo para WorkItems con orden explícita del propietario registrada y enlazada) y **supervisar y reparar sus propios Runs**. Bloque E1b del plan del Work Engine (ADR-020); contradicciones C1 y C2 de la arquitectura §14, con el texto derivado de sus recomendaciones.
- **Motivo:** sin la primera, el motor puede preparar el trabajo pero la activación sigue siendo un clic humano, que es el cuello de botella exacto que el Work Engine viene a eliminar. Sin la segunda, el motor no existe como motor: se reduce a otra colección de reacciones a eventos, con la misma clase de atascos que ya hemos pagado.
- **Decidido por el propietario**, por interrogatorio, el 21 de agosto de 2026: a la pregunta de si el motor puede dar la salida a un trabajo ya pedido, «que la dé el motor»; a la de si puede levantar solo un trabajo caído, «que lo arregle solo». Y antes de ambas, al elegir qué construir primero, «desatascarse solo».
- **Alcance:** solo esos dos puntos. **No toca** §8 (el merge sigue siendo suyo), ni §9.1 (el vigilante periódico conserva sus cinco límites intactos, incluido el de no aplicar nunca `sirius:implement-requested`), ni §5, ni §11, ni ningún workflow.
- **Mantiene:** la prohibición de iniciativa —la máquina no decide qué trabajo existe— y la de vigilancia periódica como motor para todo lo que no sea el motor sobre sus propios Runs.
- **Entrada en vigor:** cuando la PR que introduce §12 sea revisada, tenga CI verde y sea fusionada por autorización explícita del usuario.

### 10.9 Versión 1.9 — la etiqueta de activación depende de la clase despachada

- **Decisión:** generalizar §12.1 mediante una nueva §12.4: el motor puede aplicar la etiqueta de activación **que corresponde a la clase del WorkItem que despacha**, tomada de una **tabla cerrada** de dos filas (`programacion` → `sirius:implement-requested`; `auditoria` → `auditoria:solicitada`). La condición de §12.1 —orden explícita del propietario, registrada y enlazada en la evidencia— **no se relaja ni se reescribe**.
- **Motivo:** §12.1 nombró una etiqueta concreta porque, cuando se escribió, `programacion` era la única clase despachable. Esa redacción bloquea el bloque C4 (Auditor como perfil del motor), cuyo carril usa `auditoria:solicitada` fuera del espacio `sirius:*` por decisión de ADR-016. Sin esta enmienda el motor puede preparar una auditoría entera y no darle la salida — el cuello de botella exacto que §12.1 eliminó para programación.
- **Por qué es una generalización y no una autorización nueva:** el argumento de §12.1 no dependía de la etiqueta, sino del gesto: «solo cambia quién teclea la etiqueta, no quién decide». Ese razonamiento es idéntico para una auditoría pedida por el propietario.
- **Defecto de planificación que la motiva:** el plan del Work Engine (ADR-020) anticipó **dos** enmiendas —v1.7 (E1a) y v1.8 (E1b)— y declara para C4 «Decisión humana previa: ninguna». Es inexacto: C4 no se puede implementar bajo la v1.8. El plan se corrige en la misma PR que esta enmienda.
- **Alcance:** solo §12. **No toca** §8 (el merge sigue siendo del propietario), ni §9.1 (el vigilante periódico sigue sin poder aplicar ninguna de las dos etiquetas), ni §5, ni §11, ni ningún workflow, ni la superficie del Auditor.
- **Mantiene:** la prohibición de iniciativa; la tabla cerrada (una clase que no esté en ella no se despacha); ADR-016 (el Auditor se lanza por etiqueta y no escribe nunca) y ADR-010 (los hallazgos no se convierten en trabajo por su cuenta).
- **Entrada en vigor:** cuando la PR que introduce §12.4 sea revisada, tenga CI verde y sea fusionada por autorización explícita del propietario.

El historial de las versiones 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7 y 1.8 permanece disponible en Git y no se reescribe retrospectivamente.


## 11. Autoridad por clase de trabajo

Regla única: **la autoridad es una función total por clase de trabajo, con un solo conmutador fechado por clase.** No existe estado intermedio, y **ningún WorkItem puede nacer sin autoridad asignada**.

### 11.1 Tabla de autoridad

Cubre todas las clases de trabajo, sin huecos. Una clase que no aparezca aquí no puede crear WorkItems hasta que se añada.

| Clase de trabajo | ¿Existe en la vía GitHub? | Autoridad desde la v1.7 | ¿Conmuta? |
|---|---|---|---|
| conversación / exploración / consulta | no (no crea WorkItem) | motor, o ningún WorkItem | — |
| investigación | no | **motor, desde su nacimiento** | — |
| documental no publicada | no | **motor** | — |
| documental publicada (PR en el repo) | sí | incidencia | sí |
| programación | sí | incidencia | sí |
| auditoría | sí (etiqueta propia) | incidencia | sí |
| reparación / espera / cancelación | son fases o estados, no clases | la de su WorkItem | — |

Para las clases nativas del motor **no hay periodo previo**: nacen canónicas en el almacén del motor. Si algo de ellas se refleja en GitHub, ese reflejo es informativo y se etiqueta como tal.

Para las clases con proyección en la vía GitHub, mientras no hayan conmutado, el motor mantiene un espejo **explícitamente no autoritativo**, así marcado en toda salida del motor.

### 11.2 Condición de conmutación

Una clase con proyección en la vía GitHub conmuta cuando se cumplen las dos, medidas sobre esa clase:

1. **Siete días naturales consecutivos** en que el verificador de proyección (motor ↔ incidencia) esté en verde de forma continua.
2. **Cero correcciones manuales del estado** en ese periodo: ninguna vez en que una persona o una sesión haya tenido que arreglar a mano el almacén del motor o las etiquetas de la incidencia **porque ambos dijeran cosas distintas**.

**Lo que NO interrumpe el contador**, y la distinción es deliberada: un fallo de un servicio externo, una ejecución de CI cancelada, una parada por convergencia, un timeout de un revisor o cualquier otra avería operativa. Ninguna de esas cosas hace que las dos representaciones discrepen, y **es la discrepancia lo único que esta condición mide**.

> Esa distinción es la corrección de fondo respecto a la propuesta del plan, que exigía catorce días sin ninguna intervención manual. Sobre el ritmo real del repositorio esa condición no es exigente: es inalcanzable, y una condición inalcanzable no protege — impide que la conmutación ocurra nunca. Se cambia el umbral a siete días y, sobre todo, se cambia **qué se cuenta**.

El contador no puede empezar antes de que el motor lleve el estado por sí mismo (bloques C1 y C2): que lo escriba en su diario y mantenga la incidencia como proyección de él. Lo que crea la proyección a verificar es que existan **dos** representaciones del mismo estado —el diario del motor y las etiquetas de la incidencia—; mientras el motor no tenga estado propio que comparar no hay nada que medir. Dónde se ejecute el motor no entra en esta condición: desde ADR-082 corre dentro de GitHub Actions, invocado por los workflows, y eso no le quita ni le da autoridad.

Precisión que ADR-082 obliga a añadir al punto 1: el motor ya no es un proceso que corra sin parar —nace y muere con cada invocación—, así que el verificador no observa de forma continua. «En verde de forma continua» se mide, por tanto, sobre las pasadas realmente ejecutadas, y medirlo así no lo relaja: **una sola pasada en rojo rompe el contador**, y un tramo sin ninguna pasada tampoco lo acredita, porque no hay nada medido que enseñar.

### 11.3 El acto de conmutación

**Es automático.** No requiere autorización explícita del usuario, a diferencia del merge (§8).

La razón es que la condición de §11.2 es **medible**: no hay juicio que emitir, solo una comprobación que se cumple o no. Pedir una firma sobre una medición no añade seguridad; añade una espera y traslada al usuario la responsabilidad de un criterio que no puede evaluar por su cuenta.

El acto consiste en: registro fechado como dato versionado en el repositorio, más anuncio por el canal de notificaciones ya existente (§7).

**Orden entre clases:** documental publicada → programación → auditoría. De menor a mayor consecuencia si algo sale mal.

### 11.4 Después de conmutar, y la vuelta atrás

Desde el instante de la conmutación, para esa clase: el almacén del motor es canónico, y la incidencia pasa a **proyección obligatoria** — el motor la mantiene al día y el verificador la vigila. Una divergencia deja de ser una duda de autoridad y pasa a ser **un defecto del motor**.

**A la primera divergencia detectada, la clase revierte automáticamente**: la incidencia vuelve a ser la fuente de verdad, el motor vuelve a ser espejo, y se notifica.

No se espera a un patrón ni a una segunda ocurrencia. Volver atrás no cuesta nada —ninguna de las dos representaciones se borra, ambas conservan su historial completo— y seguir siendo autoridad cuando ya se ha demostrado poco fiable sí cuesta.

Tras una reversión, la clase vuelve a empezar el contador de §11.2 desde cero.

### 11.5 Lo que esta sección NO cambia

- **Nada sobre dónde se ejecuta el trabajo.** Los workflows de GitHub Actions siguen siendo quienes ejecutan al implementador, al revisor y al corrector, y desde ADR-082 también al propio motor. La conmutación mueve la autoridad del estado, no la ejecución.
- **Nada de lo que el usuario ve.** Las incidencias, las etiquetas y las notificaciones siguen existiendo y actualizándose igual.
- **Nada del merge.** §8 sigue exigiendo la orden explícita del usuario, antes y después de conmutar.
- **Nada de la activación ni de la supervisión.** Llegan en la v1.8 (E1b), no aquí.


## 12. El motor de trabajo: qué puede hacer por su cuenta

Esta sección autoriza al **motor de trabajo** dos cosas que el contrato le
prohibía, y **solo esas dos**, con sus límites. Todo lo demás sigue igual.

El motor es un actor distinto del vigilante periódico de §9.1. Los límites de
aquella sección gobiernan al vigilante y **no se tocan aquí**: siguen valiendo
enteros para él. Confundirlos sería relajar dos cosas creyendo que se relaja
una.

### 12.1 Transportar una orden ya dada no es iniciativa

El motor **puede** aplicar `sirius:implement-requested` a un WorkItem, con una
condición que no admite excepción:

> Solo si existe una **orden explícita del propietario**, registrada y
> **enlazada en la evidencia** de ese WorkItem. Sin orden enlazada que señalar,
> el motor no arranca nada.

Lo que sigue prohibido, y es lo que el límite protegía: **la máquina no decide
qué trabajo existe**. No inventa bloques, no encadena el siguiente porque el
anterior terminó, no interpreta un silencio como permiso.

Por qué la distinción es real y no una excusa: el contrato exigía «orden del
usuario», y una orden explícita e inequívoca **ya es** esa orden. Pedirla dos
veces —una al encargar el trabajo y otra al pulsar la etiqueta— no añade
control, añade un intermediario. Y esta enmienda solo cambia **quién teclea la
etiqueta**, no **quién decide**.

Hay una razón práctica, además de la doctrinal: mientras el propietario delegó
ese gesto en la sesión interactiva, esa sesión lo puso mal **tres veces en una
noche** —una activación sin `sirius:planned`, una revisión antes de que
terminara Quality, y una tercera— y las tres detuvieron un bloque. La etiqueta
es una comprobación mecánica de precondiciones, y eso lo hace mejor una máquina
que una persona a las cuatro de la mañana.

### 12.2 Supervisar y reparar sus propios Runs

El motor **puede** sondear el estado de sus Runs y **actuar** sobre ellos:
reintentar, sustituir el Worker o escalar. Eso es vigilancia periódica que sí
dirige el flujo, y por eso hacía falta esta enmienda.

Con cuatro límites, y ninguno es decorativo:

1. **Solo SUS Runs.** Los que él despachó y gobierna. No toca ciclos ajenos ni
   trabajos que no nacieron de él.
2. **No inventa trabajo.** El límite de §12.1 vale igual aquí: reparar un Run no
   autoriza a crear otro WorkItem.
3. **No fusiona. Nunca.** §8 queda intacta: el merge sigue siendo un gesto
   explícito del propietario y no hay ninguna vía por la que el motor lo haga.
4. **El vigilante periódico de §9.1 se queda como respaldo** de la vía GitHub,
   con sus límites intactos. Si el motor se equivoca, o si su run no llega a
   terminar, esa red sigue debajo. Desde ADR-082 los modos de fallo que cubre
   son los de un job, no los de un proceso que se cuelga: el run que no se
   disparó, el que expiró por timeout, el que alguien canceló y el que terminó
   a medias sin dejar su diario confirmado. Y hay que decir en voz alta lo que
   este respaldo **ya no** da: motor y vigilante corren ambos en GitHub
   Actions, así que la red comparte sustrato con lo que respalda y una
   degradación de la plataforma se lleva a los dos. Esa dependencia común se
   acepta a sabiendas y no está mitigada.

Por qué la prohibición general deja de aplicarse aquí, y no es porque el motor
viva fuera de GitHub Actions: desde ADR-082 corre dentro, invocado por los
workflows. Las dos razones que sí siguen en pie son otras. **Primera:** el
defecto que §9.1 nombra es que un proceso no puede informar de su **propia**
muerte, no de la ajena, y ADR-057 demuestra que un run sí puede observar otro
run por la API. El motor es externo **al run que vigila** aunque comparta
sustrato con él, y eso es lo que esta autorización necesita. **Segunda:** el
argumento de coste dejó de aplicar cuando el repositorio pasó a ser público
(ADR-044), como ya recoge §9.1.

Lo que esto **no** resuelve, y se dice aquí en voz alta en vez de dejarlo
deducir: la muerte del run del propio motor sigue sin observador propio. Ahí el
motor hereda los tres modos de muerte que `repair-sirius-work.yml` describe
sobre sí mismo —el checkout que cae, el runner que desaparece, el job que
alguien cancela— y deja de ser el «observador externo» que aquel workflow y la
incidencia #138 dejaron anunciado como decisión pendiente. Esta sección
responde la mitad alcanzable de esa decisión —externo al run observado—, no la
otra. La única red que queda debajo es el vigilante periódico de §9.1, con los
límites que allí tiene. Es el precio de ADR-082 y no está mitigado.

### 12.3 Lo que esta sección NO cambia

Se dice explícitamente para que nadie lo deduzca al revés:

- **§8, el merge.** Sigue exigiendo el comentario explícito del propietario. Es
  el único gesto que el contrato le reserva y esta enmienda no lo toca.
- **§9.1, el vigilante periódico.** Sus cinco límites siguen enteros. En
  particular sigue sin poder aplicar `sirius:implement-requested`: la
  autorización de §12.1 es del motor, no suya.
- **§5, la convergencia.** Un ciclo que no progresa sigue parándose y pidiendo
  una decisión humana.
- **§11, la autoridad por clase.** Sin cambios.
- **La prohibición de vigilancia periódica como motor** sigue vigente para todo
  lo que no sea el motor supervisando sus propios Runs.

### 12.4 La etiqueta que el motor aplica depende de la clase que despacha

§12.1 autorizó al motor a aplicar `sirius:implement-requested`, y nombró esa
etiqueta y ninguna otra. Fue correcto: cuando se escribió, la única clase que el
motor sabía despachar era `programacion`.

Esa redacción **bloquea la clase auditoría**, cuyo carril usa una etiqueta
distinta a propósito —`auditoria:solicitada`, fuera del espacio `sirius:*`,
como fija ADR-016—. Sin esta enmienda, el motor podría preparar una auditoría
entera y no podría darle la salida, que es exactamente el cuello de botella que
§12.1 vino a eliminar para programación.

El motor **puede** aplicar la etiqueta de activación **que corresponde a la
clase del WorkItem que despacha**, tomada de esta tabla cerrada:

| Clase del WorkItem | Etiqueta de activación que el motor puede aplicar |
|---|---|
| `programacion` | `sirius:implement-requested` |
| `auditoria` | `auditoria:solicitada` |

Con la **misma condición sin excepción de §12.1**, que no se relaja ni se
reescribe: solo si existe una orden explícita del propietario, registrada y
enlazada en la evidencia de ese WorkItem.

**Por qué esto es una generalización y no una autorización nueva.** El argumento
de §12.1 no dependía de qué etiqueta era: *«esta enmienda solo cambia quién
teclea la etiqueta, no quién decide»*. Ese razonamiento es idéntico para una
auditoría pedida por el propietario. Lo que cambia es el carril, no la
naturaleza del gesto.

**Qué sigue prohibido, y es lo que la tabla protege:**

- **La tabla es cerrada.** Una clase que no esté en ella no se despacha: el
  motor se detiene con la clase no despachable, como hace hoy. Añadir una fila
  es una enmienda de este contrato, no una decisión de implementación.
- **El carril del Auditor no se toca.** El motor aplica la etiqueta y nada más.
  No modifica `audit-sirius-repository.yml`, no escribe en el informe, no altera
  la superficie que ADR-016 fijó. El Auditor sigue lanzándose por etiqueta y sin
  escribir nunca.
- **Los hallazgos no se convierten en trabajo.** ADR-010 sigue entero: cada
  hallazgo puede originar una orden **del propietario**, y el motor no la
  inventa. Despachar una auditoría no autoriza a despachar sus consecuencias.
- **§9.1 sigue sin poder aplicar ninguna de las dos.** La autorización es del
  motor, no del vigilante periódico, igual que en §12.1.
