# ADR-131 — M21b: la interfaz de la criticidad, Sirius propone y el usuario confirma o rechaza

- Estado: PROPUESTO
- Fecha: 2026-09-03
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

Esta es también la nota de arranque de la rama `feature/m21b-criticality-ui`
(incidencia #520, Work ID WI-20260903-144522), publicada antes del primer
cambio de código, con las cuatro preguntas de la disciplina de evidencia
(ADR-001).

## Contexto y problema

El plan del propietario del 02-09-2026
(`docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md`, sección
«Decisión del propietario y plan»; ADR-126) termina en M21: «Sirius propone
la criticidad, el usuario confirma». M18b (ADR-126) introdujo la señal
`criticality` sin cablearla; M19a/M19b (ADR-127/ADR-128) la cablearon al
índice y al rescate RF-25/RF-26; M20 (ADR-129) la cableó a la siembra en
contexto; M21a (ADR-130) construyó el mecanismo de propuesta —
`CriticalityClassifierPort`, `OllamaCriticalityClassifierAdapter`,
`ProposeCriticalityUseCase` — sin interfaz ni escritura. Falta la última
pieza, y con ella se cierra M21: que el propietario *vea* la propuesta y
decida, en vez de que Sirius decida por él.

La regla que manda, literal de la incidencia (idéntica a la de M21a): **Sirius
propone, el usuario decide.** La única escritura de `criticality` sigue
siendo `SetCriticalityUseCase.set()` (M18b), siempre manual e incondicional,
disparada exclusivamente por una acción explícita del usuario — confirmar la
propuesta o editar a mano. Ningún camino de este encargo escribe por sí solo,
ni introduce `criticality_locked`, columnas o persistencia nueva.

El molde es `KnowledgeWidget`/`CategoryTaggingWorker`, ya usado para
`category` (D7): edición manual con `_prompt_line` contra un vocabulario
cerrado, trabajo fuera del hilo de la GUI con un `QRunnable` sobre
`self._thread_pool`, referencia fuerte al worker mientras vive (CODEX-001),
cableado a través de `main.py` → `ValidatedMainWindow` → `MainWindow` →
`KnowledgeWidget`. La pieza nueva, sin precedente en `category`, es la
propuesta no bloqueante con Confirmar/Rechazar y su descarte si la selección
cambió antes de que la propuesta llegara.

## Nota de arranque (cuatro preguntas, ADR-001)

**1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
observar el fallo que arregla?**

No hay un fallo que reproducir: es una carencia de interfaz — el mecanismo de
M21a existe (`ProposeCriticalityUseCase`, `SetCriticalityUseCase`) y está
cableado en `ConversationDependencies`, pero ningún widget lo invoca todavía
(`grep -rn "criticality" src/sirius/presentation` no encuentra nada antes de
este encargo). El arreglo vive exactamente donde vive la carencia:
`KnowledgeWidget` gana la edición manual y el flujo de propuesta, y un
`CriticalityProposalWorker` nuevo (calcado de `CategoryTaggingWorker`) saca
`ProposeCriticalityUseCase.propose()` del hilo de la GUI. Sí puede
observarse: cada pieza tiene su propia prueba en `tests/gui`, con dobles de
`ProposeCriticalityUseCase`/`SetCriticalityUseCase` que registran llamadas —
la prueba ve exactamente qué se escribió y cuándo, sin depender de Ollama ni
de ningún otro camino aguas abajo.

**2. ¿Qué NO va a garantizar esto?**

- No va a cambiar ninguna métrica del banco de 47 casos ni la salida de
  `scripts/medir_variantes_de_criticidad.py`: la interfaz no toca la
  recuperación (índice, rescate, G12, siembra, filtro) — solo lee y, ante una
  acción explícita, escribe a través del mismo `SetCriticalityUseCase` que ya
  existía desde M18b.
- No garantiza que la propuesta del modelo sea correcta en ningún sentido
  semántico — eso ya lo documentó ADR-130; aquí solo se decide si el
  propietario la ve y qué hace con ella.
- No persiste el rechazo de una propuesta más allá de la sesión: es una
  limitación conocida y deliberada (ver «Decisión» y «Consecuencias»), no un
  descuido.
- No introduce `criticality_locked`, columnas, migraciones ni ninguna otra
  forma de persistencia nueva. No toca `category`, `TagCategoryUseCase`,
  `_edit_category`, `_enqueue_untagged`, los vocabularios de D7 ni la
  recuperación.
- No barre todos los elementos pidiendo propuestas: como mucho, una llamada
  al modelo por selección del usuario.
- No verifica la aceptación real del propietario en su máquina, con sus
  recuerdos reales y Ollama corriendo — eso solo puede comprobarlo él mismo
  (ver «Comprobación que la sostiene» y «Consecuencias»).

**3. Criterio de parada (decidido antes de ver ningún resultado)**

Predicción escrita antes de construir: **ninguna** métrica del banco de 47
casos cambia (0 omisiones críticas, 72/81 cobertura, 0/47 exactos, elementos
de más igual que hoy en `main`), porque la interfaz no toca la recuperación;
`scripts/medir_variantes_de_criticidad.py` da exactamente lo mismo que hoy.
Si cualquiera de esas medidas cambia, o si aparece cualquier camino por el
que una propuesta se escriba sin acción explícita del usuario, este encargo
se para y se busca la causa en vez de seguir. Dos rondas de revisión seguidas
con defectos de la misma familia → parar y buscar la raíz, no seguir
parcheando (regla de las dos rondas, ADR-001).

**4. ¿Qué hace esto imposible, en vez de improbable?**

Que una propuesta se confunda con una decisión del usuario: `refresh()`
oculta cualquier propuesta mostrada porque repoblar las listas ya pierde la
selección (`QListWidget.clear()` deja `currentItem()` en `None`), y
`_handle_criticality_proposal_finished` compara `kind`/`id` con la selección
vigente antes de mostrar nada — una propuesta que llega tarde, para una
selección que ya cambió, se cachea (para no volver a pedirla) pero nunca se
muestra ni se escribe. `Confirmar` es el único botón que llama a
`SetCriticalityUseCase.set()` con la propuesta exacta; `Rechazar` nunca llama
a ese método, solo registra el rechazo en un conjunto en memoria. No hay
ningún temporizador, cierre de sesión ni evento del sistema que escriba
`criticality` por su cuenta.

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque, arriba. Ese resultado, medido después del
cambio, se registra en «Comprobación que la sostiene».

## Opciones consideradas

1. **Mostrar la propuesta directamente en el texto de la lista, con las
   acciones como parte del propio `QListWidgetItem`.** Descartada: Qt no
   ofrece botones dentro de un `QListWidgetItem` sin un delegado a medida
   (`QStyledItemDelegate` + widgets incrustados), una pieza de complejidad
   que ninguna otra parte de `KnowledgeWidget` usa y que el molde de
   categoría no necesitó porque nunca muestra una propuesta, solo el valor
   ya fijado.
2. **Un panel de propuesta por fila seleccionable dentro de cada lista**
   (etiqueta + Confirmar + Rechazar bajo los botones de cada sección,
   elegida): coherente con el resto de `KnowledgeWidget` (una fila de
   botones por sección), sin delegados nuevos, y suficiente porque la
   propuesta solo puede referirse a la selección vigente — nunca hay más de
   una propuesta visible por sección a la vez.
3. **Consultar la propuesta para todos los elementos sin criticidad al
   arrancar, como hace `_enqueue_retroactive_category_tagging` para
   categoría.** Descartada explícitamente por la incidencia: «no barrer
   todos los elementos pidiendo propuestas»; a diferencia de `category`
   (donde la clasificación automática escribe sola y sin coste visible para
   el usuario), cada propuesta de criticidad es una llamada de red a Ollama
   que solo tiene sentido pagar cuando el propietario está mirando ese
   elemento.
4. **Persistir el rechazo de una propuesta** (por ejemplo, en una tabla o
   columna nueva). Descartada de forma explícita por la incidencia: «no
   introduzcas... ninguna persistencia nueva de ningún tipo»; el rechazo
   vive solo en un `set` en memoria de la sesión, y esa limitación queda
   registrada aquí como decisión pendiente del propietario.

## Decisión

`KnowledgeWidget` gana dos kwargs opcionales nuevos —
`propose_criticality_use_case` y `set_criticality_use_case` — cableados desde
`main.py` → `ValidatedMainWindow` → `MainWindow` → `KnowledgeWidget`, igual
que los de categoría. Sin ellos, nada de esto existe (ni edición manual ni
propuesta), igual que sin `tag_category_use_case`/`set_category_use_case` no
existe el etiquetado automático.

- **Edición manual** (`_edit_criticality`, calcada de `_edit_category`): pide
  un valor con `_prompt_line` contra el vocabulario cerrado
  `{CRITICO, IMPORTANTE, ORDINARIO}`; `ORDINARIO` se traduce a `None`
  (ordinario es la ausencia de marca, M18b, nunca un tercer nivel del enum
  `Criticality`); cualquier otro valor se rechaza con una advertencia antes
  de llegar a `SetCriticalityUseCase.set()`.
- **Propuesta** (`CriticalityProposalWorker`, calcado de
  `CategoryTaggingWorker`): al seleccionar un recuerdo o decisión sin
  criticidad marcada, se arranca como mucho un worker para ese elemento —
  nunca un barrido. El worker ejecuta `ProposeCriticalityUseCase.propose()`
  fuera del hilo de la GUI y emite `finished(kind, item_id, propuesta)`;
  nunca escribe, y cualquier excepción se captura en la frontera del worker y
  se reporta como `None`, igual que `CategoryTaggingWorker`.
- **Caché en memoria** por `(kind, id)`, incluido el valor `None`: un
  elemento consultado una vez no se vuelve a consultar en la misma sesión.
  Una clave con un worker en vuelo no arranca un segundo worker si el
  usuario reselecciona el elemento antes de que el primero termine.
- **Selección vigente**: si cambió antes de que la propuesta llegara (`kind`/
  `id` ya no coinciden con lo seleccionado), la propuesta se cachea pero no
  se muestra ni se escribe. `refresh()` también oculta cualquier propuesta
  mostrada, porque repoblar las listas ya deja `currentItem()` en `None`.
- **Confirmar/Rechazar**: Confirmar llama a `SetCriticalityUseCase.set()` con
  la propuesta exacta y refresca; Rechazar no llama a `set()` — solo añade
  `(kind, id)` a un conjunto en memoria (`_rejected_criticality_proposals`)
  que evita volver a mostrar esa misma propuesta en lo que dure la sesión.
  Una edición manual posterior sobre el mismo elemento olvida tanto el
  rechazo como la caché, para que una propuesta pueda volver a pedirse si el
  propietario lo deja otra vez sin marcar (`ORDINARIO`).
- **Presentación**: `_criticality_suffix`, calcada de `_category_suffix`,
  añade `[CRITICO]`/`[IMPORTANTE]` al texto de la lista cuando el elemento
  tiene criticidad marcada — nada más cambia en la lista.

**Limitación conocida, decisión pendiente del propietario:** el rechazo de
una propuesta solo se recuerda durante la sesión (`set` en memoria, nunca
persistido). Si el propietario cierra y reabre Sirius, una propuesta ya
rechazada puede volver a pedirse y mostrarse. La incidencia prohíbe
explícitamente introducir persistencia nueva para resolverlo aquí; si el
propietario decide que el rechazo debe sobrevivir a la sesión, es una
decisión de producto para una incidencia futura, no algo que este encargo
pueda decidir por su cuenta.

## Comprobación que la sostiene

Comandos ejecutados tras completar la implementación (worker, kwargs
nuevos en `KnowledgeWidget`, cableado en `main.py`/`ValidatedMainWindow`/
`MainWindow`, edición manual, propuesta con caché/rechazo/descarte por
selección, sufijo de presentación), en este orden:

1. `uv run pytest tests/gui/test_criticality_proposal_worker.py
   tests/gui/test_knowledge_widget.py -q` → `80 passed` (5 del worker nuevo,
   16 nuevas de criticidad en `KnowledgeWidget`, 59 ya existentes sin
   regresión).
2. `uv run pytest tests/gui -q` → `467 passed, 2 skipped` (los dos
   `skipped` son preexistentes, por falta de `QtMultimedia` en esta
   máquina, MS-A02) — ninguna regresión en el resto de la interfaz.
3. `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q`
   → `28 passed, 1 skipped, 1 xfailed` — exactamente igual que antes del
   cambio (medido en `main` antes de tocar nada, y también lo que registró
   ADR-130 para M21a).
4. `uv run python scripts/medir_variantes_de_criticidad.py` →
   `hoy=0/47,487,0,72/81` / `A_porte_fiel=0/47,461,0,72/81` /
   `B_arreglo_ingenuo=0/47,551,0,72/81` — 0 omisiones críticas y 72/81 de
   cobertura en las tres variantes, exactamente la predicción de la nota de
   arranque. Sin cambio respecto a antes de este encargo (mismas cifras que
   ADR-130 registró para M21a).
5. `uv run ruff format --check .` → `594 files already formatted` (tras
   `uv run ruff format .`, que reformateó `knowledge_widget.py`: solo
   envoltura de línea); `uv run ruff check .` → `All checks passed!`;
   `uv run mypy src tests` → `Success: no issues found in 562 source
   files`; `uv run pytest -q` (suite completa) → `4637 passed, 15 skipped,
   2 xfailed` en 470 s, ningún fallo, ninguna prueba debilitada u omitida;
   `git diff --check` → limpio (sin salida, código de salida 0).
6. Dos mutaciones (ADR-001), cada una vista fallar y restaurada:
   - En `_handle_reject_criticality_clicked`, se añadió una llamada a
     `self._set_criticality_use_case.set(kind, item_id, _criticality)`
     antes de registrar el rechazo. `test_reject_criticality_proposal_does_not_write`
     **falla**: `assert [(<CriticalityTargetKind.MEMORY: 'memory'>, 1,
     <Criticality.CRITICO: 'CRITICO'>)] == []` — el doble sí registró una
     escritura que «Rechazar» nunca debe hacer. Restaurado; la prueba
     vuelve a pasar.
   - En `_handle_criticality_proposal_finished`, se sustituyó
     `if current is None or current.id != item_id:` por `if False:`.
     `test_late_criticality_proposal_after_selection_changed_is_not_shown`
     **falla**: `assert 'Sirius propone: CRITICO' == ''` — una propuesta
     llegada después de que la selección cambiara se mostró de todos
     modos. Restaurado; la prueba vuelve a pasar junto con el resto del
     archivo.
   - Verificación adicional de la caché (no exigida por el criterio de
     aceptación, pero necesaria para confiar en `test_reselecting_a_queried_memory_does_not_start_a_second_worker`):
     se sustituyó `if key in self._criticality_proposal_cache:` por
     `if False and key in self._criticality_proposal_cache:` en
     `_update_criticality_proposal_for_selection`. La prueba **falla**:
     `assert 2 == 1` — sin la caché, reseleccionar un elemento ya
     consultado vuelve a arrancar un worker. Restaurado.

## Rondas de revisión (03-09-2026)

### Ronda 1 → corrección `66a4197` (corrector del motor)

Seis hallazgos, todos atendidos con prueba: CLAUDE-REV-001/CODEX-001
(alta/P1: un `CriticalityProposalWorker` en vuelo podía reabrir `sirius.db`
mientras una restauración de copia lo sustituía — ahora `KnowledgeWidget`
expone `has_pending_criticality_proposal` y `criticality_proposal_idle`, y
`_handle_restore_backup_clicked` espera a categoría y criticidad; además no
se arranca ningún worker con el panel ocupado), CODEX-002 (P1: corregir un
recuerdo dejaba vigente la propuesta calculada sobre el contenido anterior —
contador de época por `(kind, id)` que invalida caché, rechazo y resultado en
vuelo), CLAUDE-REV-002/CODEX-003 (los cuatro botones de confirmar/rechazar
bajo `_set_controls_enabled`, restaurados solo si la propuesta sigue
visible) y CLAUDE-REV-003 (desglose de pruebas: 16 nuevas y 59
preexistentes). Ocho pruebas nuevas
(`tests/gui/test_knowledge_widget.py`, `tests/gui/test_backup_recovery_ui.py`).
Suite completa tras esta ronda: `4645 passed, 15 skipped, 2 xfailed`
(el punto 5 de arriba registra la cifra de la ronda 1, `4637`).

### Ronda 2 → corrección `(ver head de la PR #521)` (propietario)

Cuatro hallazgos más, **de la misma familia** que la ronda 1 — el estado de
la propuesta frente a transiciones —: CLAUDE-REV-R2-001 (alta: editar la
criticidad a mano mientras el worker estaba en vuelo y reseleccionar el
elemento mostraba una propuesta fantasma que «Confirmar» habría escrito
sobre el valor manual), CODEX-001 (P2: una selección hecha con el panel
ocupado se quedaba sin propuesta al liberarse), CODEX-002 (P2: corregir con
el worker en vuelo y reseleccionar dejaba la revisión nueva sin consulta,
porque «en vuelo» bloqueaba por `(kind, id)` sin época) y CLAUDE-REV-R2-002
(este ADR no registraba la ronda 1). El corrector del motor agotó su
ejecución sin subir nada (`failed-safely`, 16:04 → 16:35 UTC), igual que en
M21a; la corrección la hizo el propietario en la rama.

Dos rondas con la misma familia es el criterio de parada de ADR-001, así que
la corrección no añade otra guarda: **quita la necesidad de enumerarlas**.
`_update_criticality_proposal_for_selection` pasa a llamarse
`_reconcile_criticality_proposal` y es la única derivación de la propuesta
desde el estado — selección vigente, su `criticality`, caché, rechazos,
época, «en vuelo» y estado ocupado —, llamada en todas las transiciones:
cambio de selección (como antes), fin de un worker
(`_handle_criticality_proposal_finished` ahora solo actualiza el estado y
llama a la derivación, que comprueba entre otras cosas que el elemento siga
sin marca: cierra CLAUDE-REV-R2-001) y salida del estado ocupado
(`set_external_busy(False)`: cierra CODEX-001). «En vuelo» se indexa por
`(kind, id, época)`, de modo que el worker de la revisión anterior no
bloquea el de la nueva (cierra CODEX-002). Las mutaciones del punto 6 de
arriba que nombran `_update_criticality_proposal_for_selection` se refieren
a esa función con su nombre antiguo; siguen valiendo.

Comprobación (runner del propietario): `ruff check` → `All checks passed!`;
`mypy src tests` → `Success: no issues found in 562 source files`; las tres
pruebas nuevas, vistas fallar contra `66a4197` antes del cambio
(`assert 'Sirius propone: CRITICO' == ''` la de la propuesta fantasma; dos
`waitUntil timed out` las de reanudación y revisión nueva) y en verde
después; `tests/gui/test_knowledge_widget.py` +
`test_backup_recovery_ui.py` + `test_criticality_proposal_worker.py` →
`123 passed`; `tests/gui` completo → `477 passed, 2 skipped, 1 failed`,
donde el fallo es
`test_conversation_ui.py::test_streaming_message_grows_without_overlapping_neighbours`
(interfaz de conversación, sin relación con este cambio): pasa aislado en
este mismo árbol, en `66a4197` limpio y en `main` `1b96508`, y Quality ya
lo ejecutó en verde dentro de la suite completa sobre `66a4197` — depende
del orden/estado de Qt en el runner del propietario, no del código.
Queda anotado en la bitácora de fallos del ciclo. Tres mutaciones, cada
una vista fallar y restaurada por copia:

1. Quitar `item.criticality is not None` de la derivación →
   `test_manual_edit_before_the_worker_answers_never_resurrects_a_proposal`
   **falla** (la propuesta fantasma vuelve a mostrarse).
2. No reconciliar al salir del estado ocupado →
   `test_leaving_the_externally_busy_state_resumes_the_proposal_for_the_selection`
   **falla** (`waitUntil timed out`: nadie arranca el worker).
3. «En vuelo» sin época (bloquear por `(kind, id)`) →
   `test_correcting_a_memory_while_its_worker_is_in_flight_requests_the_new_revision`
   **falla** (la segunda consulta nunca llega).

### Ronda 3 → corrección (propietario)

Dos hallazgos, severidad total 3 (13 → 8 → 3: la consolidación cerró la
familia; lo que queda es acotado):

- **CLAUDE-REV-R3-001 (baja, solo pruebas).** La prueba de la revisión
  nueva usaba un doble con un único resultado y un único cerrojo, así que
  no distinguía si lo mostrado venía de v1 (obsoleto) o de v2. Nuevo doble
  `_SequencedBlockingProposeCriticalityUseCase` (un resultado y un cerrojo
  por llamada); la prueba libera primero v2 (IMPORTANTE), comprueba que se
  muestra, libera después v1 (CRITICO) y afirma que lo mostrado sigue
  siendo IMPORTANTE y que reseleccionar no vuelve a consultar: el descarte
  por época queda demostrado en el orden que importa.
- **CODEX-001 (P2).** La reanudación al salir del estado ocupado arrancaba
  un worker también en los flujos terminales de `MainWindow` — un envío que
  termina con el cierre ya solicitado (`_finish_sending`) y una
  restauración satisfactoria que cierra la ventana
  (`_on_restore_backup_succeeded`) —: una llamada a Ollama de hasta 30 s
  sobre una ventana que se cierra o una base recién restaurada.
  `KnowledgeWidget.set_external_busy` gana `resume_proposals: bool = True`;
  esos dos flujos pasan `False` (el primero, `not self._close_requested`),
  y el resto de liberaciones conserva la reanudación. Prueba nueva:
  `test_releasing_the_busy_state_without_resume_starts_no_proposal_worker`.

Comprobación: `ruff check` limpio, `mypy` sin incidencias (562 archivos);
`tests/gui/test_knowledge_widget.py` + `test_backup_recovery_ui.py` +
`test_criticality_proposal_worker.py` → `124 passed`;
`tests/gui/test_main_window.py` + `test_validated_main_window.py` →
`18 passed`. Dos mutaciones, vistas fallar y restauradas por copia:
suprimir el descarte por época (`if False:`) →
`test_correcting_a_memory_while_its_worker_is_in_flight_requests_the_new_revision`
**falla** (se muestra el CRITICO obsoleto); ignorar `resume_proposals` →
`test_releasing_the_busy_state_without_resume_starts_no_proposal_worker`
**falla** (arranca el worker).

## Consecuencias

- Se cierra M21 (M21a + M21b): Sirius puede sugerir criticidad y el
  propietario puede confirmarla, rechazarla o fijarla a mano, cumpliendo la
  regla «Sirius propone, el usuario decide» también en la interfaz.
- El rechazo de una propuesta no sobrevive a la sesión — limitación conocida,
  registrada arriba, pendiente de una decisión del propietario.
- La aceptación real de este encargo —que funcione con los recuerdos reales
  del propietario, no solo con dobles de prueba— es su prueba en su máquina,
  con Ollama corriendo; no se inventa ni se simula aquí.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba.
