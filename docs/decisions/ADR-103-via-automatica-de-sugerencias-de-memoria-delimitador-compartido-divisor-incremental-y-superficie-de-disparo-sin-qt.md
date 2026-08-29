# ADR-103 — Vía automática de sugerencias de memoria: delimitador compartido, divisor incremental y superficie de disparo sin Qt

- Estado: PROPUESTO
- Fecha: 2026-08-29
- Aprobación: pendiente (fusión de la PR de la incidencia #437 por el propietario)

## Contexto y problema

La incidencia #437 (Work ID WI-20260829-141434) pide construir M6 —«Sugerencias
confirmadas: interfaz y vía automática»— sobre `docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md`
§3.2, §3.6 y §8-M6, con M4 y M5 ya fusionados en `main`. El objetivo fija el
contrato en prosa (un delimitador acordado, un campo `memory_suggestion`
separado antes de que exista un solo evento del puerto, una superficie de
interfaz —nunca `SendMessageUseCase`— que decide llamar a
`ProposeMemorySuguestionUseCase.propose(...)`) pero dentro de ese contrato
quedan grados de libertad de implementación que el documento no cierra:

1. Qué token literal usar como delimitador, y en qué capa vive esa constante
   para que tanto `render_instructions()` (aplicación) como el adaptador
   concreto de `LLMProvider` (adaptadores) la compartan sin que ninguno
   importe de la otra capa indebidamente.
2. Cómo separar el delimitador de la salida cruda cuando puede llegar partido
   entre fragmentos de streaming, sin retrasar la mayoría del texto visible.
3. En qué módulo vive la superficie de interfaz que decide llamar a
   `ProposeMemorySuggestionUseCase.propose(...)` en la vía automática, dado
   que el objetivo prohíbe que sea `SendMessageUseCase` pero no obliga a que
   sea literalmente `MainWindow`.

## Criterio de parada (escrito ANTES de decidir)

Antes de escribir código: si separar el delimitador del adaptador exigiera una
segunda llamada al proveedor por conversación, o si alguna de las tres
condiciones del propietario (nunca autoguardar, ningún proveedor/tercero
nuevo, sin llamada adicional y sin que la propuesta cruce como texto
visible/persistido) resultara imposible de sostener con las pruebas
prescritas en §8-M6, el trabajo se detiene en `BLOCKED_BY_DECISION` en vez de
relajar cualquiera de las tres. Las cinco pruebas de la vía automática y la
prueba del adaptador sobre un delimitador partido entre fragmentos, tal como
las describe §8-M6, son el criterio de aceptación: si dos rondas de escribir
la lógica de separación producen el mismo defecto —el delimitador o la
propuesta cruda llegando a `on_delta`, `LLMCompleted.text`,
`LLMCancelled.partial_text` o `LLMError.partial_text`—, se para a buscar la
causa raíz del diseño de streaming, no a parchear el síntoma.

## Opciones consideradas

**Para el delimitador (punto 1):** (a) definirlo en `sirius.domain.event`
junto a los tipos de evento de M5; (b) definirlo en `sirius.ports.llm`, junto
a `LLMCompleted`; (c) definirlo por separado en cada capa que lo necesita.

**Para la separación streaming-safe (punto 2):** (a) acumular todo el texto
crudo y no emitir ningún `LLMTextDelta` hasta el evento terminal; (b) retener
siempre los últimos `len(delimitador)-1` caracteres como colchón fijo antes de
emitir cualquier delta; (c) retener solo el solapamiento real entre el final
de lo ya recibido y un prefijo del delimitador (0 caracteres la mayor parte
del tiempo), calculado en cada fragmento.

**Para la superficie de disparo (punto 3):** (a) escribir la lógica
directamente dentro de `MainWindow._on_finished`; (b) extraerla a una función
pura, sin Qt, que `MainWindow._on_finished` invoca.

## Decisión

1. El delimitador es el token literal `"<<<SIRIUS_MEMORY_SUGGESTION>>>"`
   (`MEMORY_SUGGESTION_DELIMITER`), definido en `sirius.ports.llm` junto a
   `LLMCompleted` (opción b). Los puertos ya son el punto de encuentro entre
   aplicación y adaptadores en este código base —`LLMProvider` vive ahí
   precisamente para eso—, así que `render_instructions()`
   (`sirius/application/send_message.py`) y `OpenAIResponsesProvider`
   (`sirius/adapters/llm/openai_responses.py`) importan la misma constante sin
   que ninguno de los dos dependa de la capa de dominio para algo que no es un
   concepto de dominio, ni la duplican con el riesgo de que diverjan.

2. `OpenAIResponsesProvider` separa el delimitador con un divisor incremental,
   `_MemorySuggestionSplitter` (opción c del punto 2): por cada fragmento
   crudo, calcula el solapamiento más largo entre el final de lo ya recibido y
   un prefijo del delimitador (`_longest_delimiter_prefix_as_suffix`) y solo
   retiene esos caracteres — nunca un colchón fijo de `len(delimitador)-1`
   para todo el streaming, que habría convertido cada fragmento corto en un
   candidato a retención y roto la cadencia de streaming en tiempo real que
   las pruebas ya existentes (`test_deltas_are_yielded_in_order_before_completion`)
   fijan. Con esto, el texto ordinario fluye exactamente igual que antes de
   M6, y solo se retiene algo cuando de verdad podría ser el principio del
   delimitador. Una vez encontrado el delimitador completo, todo lo posterior
   se acumula aparte como propuesta cruda y nunca vuelve a emitirse como
   delta. En cancelación, fallo, o fin de stream sin evento terminal,
   `finish()` se llama exactamente una vez para volcar cualquier resto seguro
   pendiente (nunca el delimitador ni la propuesta) antes de construir el
   evento terminal.

3. La superficie que decide llamar a
   `ProposeMemorySuggestionUseCase.propose(...)` en la vía automática es
   `sirius.presentation.memory_suggestion_trigger.propose_suggestion_if_completed_with_one(result, propose_memory_suggestion_use_case)`
   (opción b del punto 3): una función pura, sin ningún import de Qt, que
   `MainWindow._on_finished` invoca inmediatamente después de que el turno
   termine. `MainWindow` sigue siendo, en producción, quien de verdad orquesta
   el envío y quien de verdad llama a esta función — la extracción no traslada
   la decisión a otra capa (`SendMessageUseCase` nunca la importa ni la
   llama), solo la hace directamente comprobable sin construir un
   `QApplication` ni ningún widget.

## Comprobación que la sostiene

- `uv run ruff format --check .` → `540 files already formatted`.
- `uv run ruff check .` → `All checks passed!`.
- `uv run mypy src tests` → `Success: no issues found in 511 source files`.
- `uv run pytest -q` → `4083 passed, 9 skipped`.
- `git diff --check` → sin salida (sin marcas de conflicto ni espacios en
  blanco al final de línea).
- Prueba explícita del punto 2 (delimitador partido entre dos fragmentos
  consecutivos, sin llegar nunca a `LLMTextDelta` ni a `LLMCompleted.text`):
  `tests/unit/test_openai_responses_provider.py::test_memory_suggestion_delimiter_split_across_two_deltas_never_leaks`.
- Pruebas de que una cancelación o un fallo justo después de que el
  delimitador ya se emitiera entero no dejan rastro en `partial_text`:
  `test_cancelled_after_the_full_delimiter_already_streamed_has_no_delimiter_in_partial_text`,
  `test_response_failed_after_the_full_delimiter_already_streamed_has_no_delimiter`.
- Las cinco pruebas de la vía automática sin interfaz, ejercitando
  `propose_suggestion_if_completed_with_one` con `SendMessageUseCase` real:
  `tests/integration/test_memory_suggestion_automatic_trigger.py`.
- Prueba de que ninguna de las tres retenciones del divisor incremental
  frena el streaming de texto ordinario: la suite completa de
  `tests/unit/test_openai_responses_provider.py` (incluida
  `test_deltas_are_yielded_in_order_before_completion`, ya existente, sigue
  en verde sin modificarla) sigue pasando sin cambios en su aserción.
- Confirmado además que las pruebas nuevas fallan sin el cambio: con los
  ficheros de `src/` y `tests/` modificados devueltos a `main` (`git stash`) y
  los tres ficheros de prueba nuevos conservados, `pytest` no logra ni
  recolectar `tests/integration/test_memory_suggestion_automatic_trigger.py`
  (`ImportError: cannot import name 'MEMORY_SUGGESTION_DELIMITER' from
  'sirius.ports.llm'`), confirmando que ejercitan comportamiento nuevo y no
  algo que ya pasara antes de M6.

## Consecuencias

- `LLMCompleted` gana un cuarto campo, `memory_suggestion: str | None = None`,
  con valor por omisión: todo doble de prueba existente que construye
  `LLMCompleted(text=..., input_tokens=..., output_tokens=...)` sin ese
  argumento sigue compilando y comportándose igual (`memory_suggestion` queda
  `None`), sin tocar ningún doble existente.
- `SendMessageResult` gana el campo espejo `memory_suggestion`, copiado solo
  cuando `outcome` es `COMPLETED`; ningún llamador existente de
  `SendMessageUseCase.send_message()` necesita cambiar.
- `GetKnowledgeOverviewUseCase` gana una tercera dependencia obligatoria
  (`memory_suggestion_repository`) y `KnowledgeOverview` un campo nuevo
  (`pending_suggestions`): los tres call sites de producción/prueba que
  construían `GetKnowledgeOverviewUseCase` con dos argumentos posicionales se
  actualizaron a tres en el mismo cambio (`src/sirius/composition_root.py`,
  `tests/integration/test_local_performance.py`,
  `tests/integration/test_decision_supersession_explicit.py`).
- `MainWindow.__init__` y `KnowledgeWidget.__init__` ganan parámetros nuevos
  (los tres casos de uso de M5 y, en `MainWindow`, el seam
  `prompt_multiline_with_default`); todo constructor de prueba y de
  `src/sirius/main.py`/`src/sirius/presentation/validated_main_window.py` que
  los invocaba se actualizó en el mismo cambio.
- Un futuro bloque que quiera reutilizar «un delimitador acordado que el
  proveedor debe usar dentro de la misma respuesta» tiene ya, en
  `sirius.ports.llm`, tanto el patrón (constante de puerto compartida entre
  aplicación y adaptador) como el divisor incremental streaming-safe
  (`_MemorySuggestionSplitter`) como referencia, sin tener que redescubrir por
  qué un colchón fijo de retención rompería el streaming en tiempo real.

## Alternativas descartadas y por qué

- **Delimitador definido en `sirius.domain.event`:** descartado porque no es
  un tipo de evento de dominio ni el dominio necesita conocerlo; hacerlo así
  habría obligado a los adaptadores de LLM a importar de dominio para un
  detalle que es, literalmente, un protocolo de puerto entre la aplicación y
  el adaptador concreto.
- **Colchón fijo de `len(delimitador)-1` caracteres retenidos todo el rato:**
  descartado porque retrasaría la primera aparición de cada fragmento corto
  de streaming indiscriminadamente, incluso cuando no hay ninguna
  ambigüedad real con el delimitador, degradando la sensación de streaming en
  tiempo real que S9/B8a ya fijan para 0.1 sin necesidad.
- **Acumular todo el texto crudo y no emitir ningún delta hasta el evento
  terminal:** descartado por la misma razón, agravada: elimina el streaming
  por completo, no solo lo retrasa.
- **Lógica de disparo automático escrita directamente dentro de
  `MainWindow._on_finished`:** descartado porque las pruebas de la vía
  automática exigidas por §8-M6 son "sin interfaz"; dejar la decisión
  enterrada en un método de `QMainWindow` habría obligado a construir un
  `QApplication` y una `MainWindow` completa solo para probar una regla de
  negocio de cuatro líneas (`outcome is COMPLETED and memory_suggestion is not
  None`), y a mezclar esa prueba con las de infraestructura Qt en vez de con
  las de `SendMessageUseCase`.
