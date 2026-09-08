# ADR-165 — Derivar los ejes de cada ítem de lo que el esquema ya guarda, en vez de entregarlos sin ejes

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de esta PR por el propietario.

Esta es también la **nota de arranque** de la rama
`feature/ejes-derivados-en-el-puerto-real` (incidencia #572, WI-20260908-P2),
publicada antes del primer commit de código, con las cuatro preguntas de la
disciplina de evidencia (ADR-001).

## Contexto y problema

Es la **palanca 2 de ADR-148**, después de la palanca 1 (ADR-164, ya en
`main`).

`ejes_por_identidad` es el único canal por el que un ítem real puede llevar
ejes distintos de `SIN_EJES`, y `build_staged_engine_port` nunca lo puebla:
queda `{}` por defecto, así que todo ítem del camino de producción llega al
motor sin ejes y las puertas que los necesitan degradan
(`src/sirius/adapters/persistence/staged_engine_port.py`, docstring del módulo
y `StagedEnginePort.__init__`). El banco de 47 casos, en su arnés de examen,
instancia el puerto directamente con los ejes que el corpus congelado declara
(`tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py:777`), y por eso mide
un techo que producción no alcanza.

El techo está medido y repetido en ADR-148: con la petición real del caso
**y además** los ejes de los ítems, la búsqueda pasa de `16/47 exactas y 162
de más` a `20/47 y 144`, con 0 críticas perdidas y 73/81 hallados.

## Nota de arranque (cuatro preguntas, ADR-001)

1. **¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo
   OBSERVAR el fallo que arregla?** El fallo vive en
   `build_staged_engine_port`/`StagedEnginePort`: es el único sitio que lee
   las filas canónicas **y** construye el `ItemCanonico`, y hoy tira los datos
   temporales y de origen que ya trae en la mano. El arreglo va exactamente
   ahí. Sí puede observar el fallo: las puertas que degradan (`G6`, `G7`,
   `G8`) solo ven lo que el puerto les entrega, así que desde una puerta el
   dato ausente es indistinguible de un dato que no existe; desde el puerto,
   la fila está delante. Se observa con pruebas sobre una base migrada real
   (las consultas bajo prueba son SQL, no Python puro) y con el doble de la
   búsqueda del banco (`scripts/diagnosticar_busqueda_del_banco.py`).
2. **¿Qué NO va a garantizar esto?**
   - No persiste ningún eje nuevo: **sin migración**. Lo que el esquema no
     guarda sigue sin derivarse — `ambito`, `sensibilidad`, `confirmacion`,
     `validez`, `disponibilidad`, `no_usar_como_memoria`, `no_consolidable`,
     `procedencia`, `miembros_de_ambito` y `property_key` (que ni siquiera
     vive en `EjesDeclarados`, sino en `PlanoComun`).
   - No cambia `EjesDeclarados.declarados`, que por definición mira
     `confirmacion`/`validez`: seguirá siendo `False` para todo ítem real.
   - No abre `category_matching_enabled` ni toca el corpus, `resultado_esperado`
     ni ninguna adjudicación del banco.
   - **No alcanza el techo del banco.** El techo se midió inyectando los ejes
     del **corpus** (que declara `sensibilidad`, `ambito`, `confirmacion` y
     `validez`, ninguno derivable aquí). Lo que esta palanca deriva es un
     subconjunto, así que igualar `20/47` no está garantizado por
     construcción: es lo que hay que medir.
   - `autoridad` no cambia ninguna métrica: **ninguna puerta la lee**. Se
     deriva porque la incidencia la pide y porque es dato real, no porque
     mueva un número.
   - No arregla H2 (ADR-148): el cargador del banco sigue creando todos los
     ítems el día de la medición, y ahora esa fecha artificial también viaja
     en `valid_from`. Lo que eso implica se mide y se escribe abajo.
3. **Criterio de parada (decidido ANTES de ver ningún resultado).**
   - Al menos una prueba **vista fallar** contra el árbol anterior que fije
     que un ítem real entregado por `build_staged_engine_port` llega con sus
     ejes derivados y no con `SIN_EJES`.
   - Por cada eje derivado, una prueba que fije **de qué dato sale** y otra
     que fije que, **faltando ese dato**, el eje queda sin derivar (`None`) y
     no con un valor inventado.
   - `scripts/check.ps1` en una sola invocación, terminando en 0, con la terna
     de `pytest` anclada al árbol que la produjo (ADR-145, ADR-153, ADR-154).
   - **Predicción del banco, escrita antes de ejecutar nada** (la de la
     incidencia, que es la de ADR-148): con Ollama real en la máquina del
     propietario, **20/47 exactas, ≤144 de más, 0 críticas perdidas, ≥73/81
     hallados**. Esa medición la cierra el propietario; aquí se le entrega el
     comando exacto.
   - **Predicción del doble sin Ollama**, misma regla: con la petición del
     caso inyectada (`--peticion`), los ejes derivados deben dar **al menos
     lo mismo que hoy da `SIN_EJES` (16/47 exactas, ≤162 de más, 0 críticas
     perdidas, ≥73/81 hallados)** y acercarse a `20/47; 144`. Si sale por
     debajo del suelo de hoy, **se registra y se para**: no se ajusta la
     predicción después de ver el número.
   - Dos rondas seguidas con defectos de la misma familia → parar y buscar la
     raíz.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Que el esquema
   persistiera los ejes — es decir, una migración, que esta incidencia
   prohíbe expresamente. Dentro de lo permitido, lo que sí se hace imposible
   es lo que ya mordió antes: (a) que un cambio de los tres textos de origen
   de la capa de aplicación deje la tabla de autoridad muda sin que nadie se
   entere, con un guardián que compara la tabla del adaptador contra esas
   constantes; y (b) que un instante derivado salga en una forma que `G8` no
   pueda comparar, con pruebas de frontera exacta. Lo que **no** se hace
   imposible es que el esquema no sepa un eje: eso se declara, no se inventa.

## Criterio de parada (escrito ANTES de decidir)

Ver el punto 3 de la nota de arranque.

## Opciones consideradas

1. **Derivar en el puerto, desde las filas que ya se leen** (elegida). Sin
   migración, sin tabla nueva y sin tocar el motor ni las puertas.
2. **Derivar en el motor o en las puertas.** Descartada: la puerta no ve la
   fila, solo el `ItemCanonico` ya construido; para derivar tendría que
   volver a la base, que es justo lo que el puerto existe para hacer.
3. **Añadir una migración con los ejes.** Fuera de alcance por la incidencia,
   y además innecesaria para los tres ejes que sí salen de datos existentes.
4. **Rellenar con valores por defecto los ejes que el esquema no guarda.**
   Descartada por la incidencia y por ADR-001: un `CONFIRMADA` inventado es
   una afirmación sin dato que la sostenga, y las puertas la creerían.

## Decisión

`StagedEnginePort` deriva, de las filas que **ya** consulta, tres cosas, y
declara explícitamente todo lo demás como no derivado.

### Lo que se deriva, y de qué dato exacto

- **`valid_from` (desde cuándo aplica)**
  - `MEMORIA`: `memory_revisions.created_at` de la revisión vigente
    (`is_current = 1`) — el instante en que el contenido vigente entró en
    vigor. Es la revisión que el puerto ya une para leer `content`.
  - `DECISION` con `status = approved`: `decisions.updated_at` — el instante
    de la **aprobación**. `updated_at` de una decisión solo lo escriben las
    transiciones de estado (`create_proposal`, `approve_decision`,
    `supersede_decision`, `archive_decision`); `set_category`,
    `set_user_category` y `set_user_criticality` no lo tocan.
  - `DECISION` con `status = proposed`: nunca se aprobó → **sin derivar**.
  - `DECISION` con `status = superseded` o `archived`: `updated_at` ya
    registra la sustitución o el archivado, y el instante de la aprobación no
    se persiste en ninguna parte → **sin derivar**. No se sustituye por
    `created_at`: la propuesta no es la aprobación.
- **`valid_to` (hasta cuándo aplicó)**
  - `DECISION` con `status = superseded`: `decisions.updated_at` — el instante
    de la **sustitución**, que `supersede_decision` estampa en la misma
    transacción en las dos filas. Es un estado terminal (`ensure_can_archive`
    solo admite `APPROVED`, y `DecisionStatus` no tiene camino de vuelta), así
    que ese sello no vuelve a moverse.
  - Se lee del sello de la **propia** decición sustituida y no del de la que
    la sustituye, porque en una cadena `D1 → D2 → D3` el sello de `D2` ya se
    habría movido a la segunda sustitución y le atribuiría a `D1` una fecha
    de fin que no es la suya.
  - Cualquier otro caso —una decisión **sin sustitución**, y toda memoria—:
    **sin derivar**. Sirius 0.1 no sustituye memorias: una corrección crea una
    revisión nueva y el puerto entrega siempre la vigente.
- **`autoridad`**: de `memory_revisions.origin`, con la tabla cerrada de los
  tres orígenes que el producto escribe:
  - «Guardado manual del usuario» (`MANUAL_MEMORY_ORIGIN`) →
    `ACTO_EXPLICITO_USUARIO`.
  - «Corrección manual del usuario» (`MEMORY_CORRECTION_ORIGIN`) →
    `ACTO_EXPLICITO_USUARIO`: corregir es otro acto explícito del usuario
    sobre el mismo contenido.
  - «Sugerencia confirmada por el usuario»
    (`CONFIRMED_MEMORY_SUGGESTION_ORIGIN`) → `INFORMAL`. La autoridad es la
    del **origen del contenido**, y el de una sugerencia es lo que Sirius
    recogió de la conversación (SIRIUS-ARQ-0.2 §3.3), no una frase dictada por
    el usuario. Que el usuario la confirmara es el eje `confirmacion`, que es
    otro eje y aquí **no** se deriva. Es exactamente cómo el corpus adjudica
    `MEM-017` («Resumen: el equipo acordó…»): `CONFIRMADA` e `INFORMAL` a la
    vez.
  - Cualquier otro origen → **sin derivar**.
  - `FUENTE_EXTERNA` no lo produce ningún camino del producto hoy: no existe
    un origen de fuente externa que escribir. Es, precisamente, el hueco H3 de
    ADR-148, que espera una decisión de producto del propietario.
  - `DECISION`: `decision_revisions` no guarda `origin` → **sin derivar**.
    No se le pone `DOCUMENTO_CANONICO` por ser decisión: eso sería deducir el
    eje de la clase, no del origen, que es lo que la incidencia pide.
- **Registro**: `ItemCanonico.created_at`, de `memories.created_at` /
  `decisions.created_at` (que ya era su fuente), ahora **canonizado** a la
  forma `AAAA-MM-DD hh:mm:ss.ffffff`. `G8` compara el corte de registro con
  `created_at` como **cadenas**, y ADR-164 emite el corte exactamente en esa
  forma; canonizar aquí deja de depender de que la fila se escribiera con
  microsegundos. Un valor que no se pueda interpretar pasa **verbatim**: se
  degrada al comportamiento de hoy, nunca se inventa un instante.

### La forma en que se escriben los instantes derivados

`valid_from`/`valid_to` salen en **ISO-8601 UTC con sufijo `Z` y grano de
segundo** (`2026-09-08T11:48:10Z`), la misma forma con la que el corpus los
declara y con la que `InterpreteDePeticion` emite el tiempo objetivo
(ADR-164). No es cosmética: `G8` compara `valid_from > objetivo` y
`valid_to <= objetivo` **como cadenas**, y una fracción de segundo escrita
rompería la frontera exacta —`"…:00.000000Z"` ordena ANTES que `"…:00Z"`
porque el `.` (`0x2E`) va antes que la `Z` (`0x5A`)—, de modo que un
`valid_to` medio segundo POSTERIOR al tiempo objetivo se leería como
anterior y el ítem saldría expirado sin estarlo. Truncando al segundo, las
dos comparaciones son exactas en la frontera; y el truncado, cuando pierde
fracción, la pierde siempre hacia el mismo lado seguro: un `valid_from`
ligeramente anterior admite, y un `valid_to` ligeramente anterior da por
terminada antes una decisión ya sustituida.

### Precedencia

`ejes_por_identidad`, cuando trae una entrada para esa identidad, **manda**
sobre lo derivado. Es el canal con el que el arnés de examen del banco inyecta
los ejes del corpus congelado, y esta palanca no le cambia el significado: lo
derivado es el suelo del camino de producción, no un sustituto de lo declarado.

## Comprobación que la sostiene

PENDIENTE: se completa antes de abrir la PR.

## Consecuencias

PENDIENTE: se completa antes de abrir la PR.

## Alternativas descartadas y por qué

Ver «Opciones consideradas».
