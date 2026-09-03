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
