# ADR-130 — M21a: Sirius propone la criticidad sin escribirla

- Estado: PROPUESTO
- Fecha: 2026-09-03
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

Esta es también la nota de arranque de la rama `feature/m21a-propose-criticality`
(incidencia #518, Work ID WI-20260903-124304), publicada antes del primer
cambio de código, con las cuatro preguntas de la disciplina de evidencia
(ADR-001).

## Contexto y problema

El plan del propietario del 02-09-2026
(`docs/audits/evidencia-experimento-filtro-fiel-al-laboratorio.md`, sección
«Decisión del propietario y plan»; ADR-126) termina en M21: «Sirius propone la
criticidad, el usuario confirma». M18b (ADR-126) introdujo la señal
`criticality` sin cablearla; M19a/M19b (ADR-127/ADR-128) la cablearon al
índice y al rescate RF-25/RF-26; M20 (ADR-129) la cableó a la siembra en
contexto. Falta la última pieza: que Sirius *sugiera* un nivel en vez de que
el usuario tenga que marcarlo siempre a mano.

M21 se parte en dos encargos en serie para que cada uno quepa en una
ejecución: **M21a** (este encargo) es el mecanismo de propuesta — puerto,
adaptador Ollama, caso de uso que lee y devuelve, sin interfaz ni escritura.
**M21b** (siguiente encargo) es la interfaz que muestra la propuesta y deja
que el usuario la confirme o la corrija.

La regla que manda, literal de la incidencia: **Sirius propone, el usuario
decide.** A diferencia de `category` (`TagCategoryUseCase` SÍ escribe sola,
protegida por `category_locked`, D7 punto 2), `criticality` no tiene candado
precisamente porque nadie automático la escribe — la única escritura sigue
siendo `SetCriticalityUseCase` (M18b), siempre manual e incondicional. Este
encargo no introduce `criticality_locked` ni escritura condicional alguna.

## Nota de arranque (cuatro preguntas, ADR-001)

**1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
observar el fallo que arregla?**

No hay un fallo que reproducir: es una carencia de mecanismo (no existe
ninguna forma de que Sirius sugiera una criticidad; solo el usuario puede
fijarla). El arreglo vive exactamente donde vive la carencia — un puerto
nuevo (`CriticalityClassifierPort`), un adaptador nuevo
(`OllamaCriticalityClassifierAdapter`) y un caso de uso nuevo
(`ProposeCriticalityUseCase`) — el mismo patrón, capa por capa, que
`CategoryClassifierPort`/`OllamaCategoryClassifierAdapter`/
`TagCategoryUseCase` ya establecieron para `category` (D7, SIRIUS-ARQ-0.2
§6.1). Sí puede observarse: cada capa tiene su propia prueba unitaria que la
ejercita directamente (el adaptador con `httpx.MockTransport`, el caso de uso
con dobles de repositorio que registran llamadas), sin depender de que algo
aguas abajo lo consuma — porque, deliberadamente, nada aguas abajo lo llama
todavía (eso es M21b).

**2. ¿Qué NO va a garantizar esto?**

- No va a cambiar ninguna métrica del banco de 47 casos ni la salida de
  `scripts/medir_variantes_de_criticidad.py`: nadie llama todavía a
  `ProposeCriticalityUseCase` (ni la interfaz, ni ningún worker) — eso es
  M21b.
- No garantiza que la propuesta del modelo sea correcta en ningún sentido
  semántico: es una sugerencia de un modelo local que puede fallar,
  equivocarse o no responder — de ahí que el puerto falle siempre abierto a
  `None` y que la decisión final sea siempre del usuario.
- No escribe `criticality` en ningún sitio, ni introduce
  `criticality_locked` ni ninguna forma de escritura condicional: la regla
  «propone, no escribe» es absoluta en este encargo.
- No toca `category`, `TagCategoryUseCase`, los vocabularios de D7, el
  índice de criticidad, el rescate RF-25/RF-26, G12 ni la siembra
  (M19a/M19b/M20): todos siguen leyendo exactamente lo que el usuario (o el
  cargador del banco) ya haya fijado con `SetCriticalityUseCase`.
- No añade interfaz: eso es M21b.

**3. Criterio de parada (decidido antes de ver ningún resultado)**

Predicción escrita antes de construir: **ninguna** métrica del banco de 47
casos cambia (0 omisiones críticas, 72/81 cobertura, 0/47 exactos, elementos
de más igual que hoy en `main`), porque nadie llama todavía al caso de uso
nuevo; `scripts/medir_variantes_de_criticidad.py` da exactamente lo mismo que
hoy. Si cualquiera de esas medidas cambia, este encargo ha cableado algo que
no debía, y se para a buscar la causa en vez de seguir. Dos rondas de
revisión seguidas con defectos de la misma familia → parar y buscar la raíz,
no seguir parcheando (regla de las dos rondas, ADR-001).

**4. ¿Qué hace esto imposible, en vez de improbable?**

Que una propuesta automática se confunda con una decisión del usuario: el
puerto documenta explícitamente que `None` significa "no hay propuesta", no
"ordinario", y el caso de uso nunca abre `UnitOfWork` ni llama a ningún
método de escritura del repositorio — no hay ningún camino de código, en
este encargo, por el que una propuesta pueda llegar a persistirse. Tampoco
hace posible que se vuelva a proponer sobre algo que el usuario ya marcó: si
el elemento ya tiene `criticality` fijada, el caso de uso devuelve `None`
*sin* invocar al clasificador — comprobado con un doble que registra
llamadas y falla si se invoca.

## Criterio de parada (escrito ANTES de decidir)

Ver punto 3 de la nota de arranque, arriba. Ese resultado, medido después del
cambio, se registra en «Comprobación que la sostiene».

## Opciones consideradas

1. **Extender `TagCategoryUseCase`/`CategoryClassifierPort` para que también
   manejen criticidad.** Descartada: mezclaría dos señales con contratos de
   escritura opuestos (categoría escribe sola y con candado; criticidad no
   escribe nunca) en el mismo puerto/caso de uso, y la incidencia prohíbe
   explícitamente introducir cualquier forma de candado o escritura
   condicional para criticidad.
2. **Un caso de uso que proponga y también escriba, con un candado nuevo
   `criticality_locked` calcado de `category_locked`.** Descartada de forma
   explícita por la incidencia: la ausencia de candado en `criticality` es
   deliberada («nadie automático la escribe»); introducirlo aquí sería
   decidir por cuenta propia una pieza de M21b (o más allá) que no está en
   este alcance — la orden pide `BLOCKED_BY_DECISION` si pareciera necesario,
   y no lo es: proponer sin escribir no lo necesita.
3. **Puerto/adaptador/caso de uso nuevos, calcados de los de categoría, que
   solo leen y devuelven** (elegida): mismo patrón de tres capas que ya
   demostró funcionar (D7, M8), con la única diferencia deliberada de que el
   caso de uso no abre ningún camino de escritura — ni condicional ni
   incondicional.

## Decisión

Se implementa el mecanismo de propuesta como tres piezas nuevas, sin ninguna
escritura:

- `CriticalityClassifierPort` (`src/sirius/ports/criticality_classifier.py`):
  `Protocol` de un solo método, `propose(content: str) -> Criticality | None`,
  que nunca propaga una excepción — cualquier fallo se reporta como `None`,
  que documenta explícitamente que significa "no hay propuesta", nunca
  "ordinario".
- `OllamaCriticalityClassifierAdapter`
  (`src/sirius/adapters/ollama_criticality_classifier.py`): calcado de
  `OllamaCategoryClassifierAdapter` — solo `localhost`, sin parámetro que
  permita apuntar a otro host, `client` solo como costura de prueba, falla
  abierto a `None`. Pide al modelo exactamente uno de tres resultados
  (CRITICO, IMPORTANTE, ORDINARIO) y traduce ORDINARIO y cualquier otra cosa
  a `None`.
- `ProposeCriticalityUseCase`
  (`src/sirius/application/propose_criticality.py`): dado un `kind` y un
  `item_id`, lee el elemento; si ya tiene `criticality` marcada, devuelve
  `None` sin llamar al clasificador; si no, llama al clasificador con el
  contenido vigente y devuelve lo que responda, sin tocar la base de datos.
  No abre `UnitOfWork` (no hay escritura que emparejar con un evento).

Cableado en `composition_root.py`: se construye el adaptador con
`ollama_model` (mismo modelo que categoría y filtro de relevancia) y se
expone `propose_criticality_use_case` en `ConversationDependencies`, junto a
`set_criticality_use_case` (M18b, que hasta ahora no estaba expuesto —
la incidencia pide exponerlo si no lo estaba). Que exista y esté cableado no
cambia ningún comportamiento: nadie lo llama todavía (M21b).

## Comprobación que la sostiene

Comandos ejecutados tras completar la implementación (puerto, adaptador
Ollama, caso de uso, cableado en `composition_root.py`), en este orden:

1. `uv run pytest tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py -q`
   → `28 passed, 1 skipped, 1 xfailed` — exactamente igual que antes del
   cambio (medido en `main` antes de tocar nada): mismas 28 pruebas en
   verde, mismo `xfail` de M11. Ninguna de las cuatro métricas del banco
   cambió porque nada llama todavía a `ProposeCriticalityUseCase`.
2. `uv run python scripts/medir_variantes_de_criticidad.py` →
   `hoy=0/47,487,0,72/81` / `A_porte_fiel=0/47,461,0,72/81` /
   `B_arreglo_ingenuo=0/47,551,0,72/81` — 0 omisiones críticas y 72/81 de
   cobertura en las tres variantes, exactamente la predicción de la nota de
   arranque (0 críticas perdidas, 72/81, 0/47 exactos, elementos de más
   igual). Sin cambio respecto a antes de este encargo.
3. `uv run ruff format .` → 2 archivos de prueba reformateados (solo
   envoltura de línea); `uv run ruff check .` → `All checks passed!`;
   `uv run mypy src tests` → `Success: no issues found in 560 source files`;
   `uv run pytest -q` (suite completa) → `4612 passed, 15 skipped, 2 xfailed`
   en 461 s, ningún fallo, ninguna prueba debilitada u omitida;
   `git diff --check` → limpio (sin salida, código de salida 0).
4. Prueba por mutación (ADR-001): en
   `ProposeCriticalityUseCase.propose`, se sustituyó temporalmente
   `if memory.criticality is not None:` por `if False:` (rama `MEMORY`), se
   confirmó que `test_propose_skips_the_classifier_for_an_already_marked_memory`
   **falla** (`AssertionError: assert <Criticality.CRITICO: 'CRITICO'> is
   None` — el doble sí registró una llamada al clasificador), y se restauró
   el código real; la prueba vuelve a pasar junto con el resto del archivo
   (8 pruebas).

## Consecuencias

- Sirius gana un mecanismo capaz de sugerir criticidad, pero **ningún**
  camino de código lo invoca todavía ni escribe con él: la interfaz de M21b
  es quien decidirá cuándo y cómo mostrar la propuesta al usuario.
- El patrón de tres capas de `category` (puerto/adaptador/caso de uso) queda
  replicado para `criticality`, con la asimetría deliberada de que este caso
  de uso nunca escribe.

## Alternativas descartadas y por qué

Ver «Opciones consideradas» arriba.
