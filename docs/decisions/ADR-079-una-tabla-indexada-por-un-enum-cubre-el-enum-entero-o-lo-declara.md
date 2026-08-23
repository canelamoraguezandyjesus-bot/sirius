# ADR-079 — Una tabla indexada por un enum cubre el enum entero, o lo declara

- Estado: APROBADO
- Fecha: 2026-08-23
- Aprobación: fusión de la PR por el propietario
- Contexto: bloque M2 del plan del Work Engine, incidencia #287
- Relacionadas: ADR-001 (disciplina de evidencia: medir antes de fijar el
  criterio), ADR-033 (una regla que enumera vehículos siempre tiene un hueco
  más — la misma lógica aplica aquí a las *formas* de tabla que el criterio
  reconoce), ADR-078 (el precedente directo de este bloque: medir contra
  datos reales del repositorio antes de decidir el umbral, y escribir en
  "Consecuencias" lo que el detector no atrapa), incidencia #278 (el defecto
  real que motiva este bloque: `LLMErrorKind.CONFIGURATION` faltaba en
  `sirius.adapters.llm.openai_responses._SAFE_MESSAGES`), incidencia #267
  (mecanizar el método)

## Contexto y problema

Una tabla indexada por un enum (`dict[MiEnum, X]`) es una promesa de
totalidad que nadie firma. Cuando el enum crece y la tabla no, el resultado
no es un error de compilación: es un `KeyError` en tiempo de ejecución, o
peor, un valor por defecto que devuelve algo plausible sin que nadie lo pida.
Ya ocurrió: `LLMErrorKind.CONFIGURATION` se añadió al enum, la tabla de
presentación (`sirius.presentation.error_messages._MESSAGES_BY_KIND`) lo
recogió porque tenía guarda
(`tests/unit/test_error_messages.py::test_all_error_kinds_are_covered_exhaustively`),
y la del adaptador (`sirius.adapters.llm.openai_responses._SAFE_MESSAGES`) no
porque no la tenía (PR #278).

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque de la incidencia #287, antes de medir nada:

- (a) Se recorren TODAS las tablas indexadas por enum de `src/`, se cuenta
  cuántas están completas, cuántas no, y de las incompletas cuántas son
  defectos reales y cuántas son parcialidad legítima. Si la parcialidad
  legítima es la norma y no la excepción, la guarda **no entra**: sería una
  alarma que hay que silenciar en la mayoría de los casos.
- (b) Si para reconocer las tablas hace falta ejecutar módulos que no se
  pueden importar sin pantalla, red o dispositivos, se para: el análisis
  tiene que funcionar sobre el árbol, no sobre un entorno.
- (c) Si hace falta cambiar alguna tabla existente para que la guarda pase
  —más allá de completar una que de verdad esté incompleta—, se para.

Ninguno de los tres se disparó: la parcialidad legítima resultó ser la
excepción, el análisis es puramente estático (`ast`, sin importar nada de
`src/`), y ninguna tabla existente cambió de comportamiento.

## Opciones consideradas

1. **Recorrido estático con `ast` sobre `src/`, reconociendo `dict[Enum, X]`
   por su anotación.** La opción elegida; ver medición abajo.
2. **Importar los módulos de `src/` y usar `typing.get_type_hints` /
   introspección en tiempo de ejecución para encontrar las tablas.** Choca
   directamente con el criterio de parada (b): varios módulos de
   `src/sirius/presentation/` (`_SPEAKER_LABELS`, `_LOOKS`) importan Qt y no
   se pueden cargar sin pantalla en este entorno de guardas. Descartada sin
   medir más, por el propio criterio de parada.
3. **Añadir una guarda de exhaustividad a mano, tabla por tabla, como ya
   hacían `tests/unit/test_error_messages.py` y
   `tests/unit/test_openai_responses_provider.py`.** Es exactamente el
   patrón que falló en la PR #278: depende de que cada autor de una tabla
   nueva recuerde añadir su propia prueba. La guarda de este bloque cubre
   las tablas ya existentes automáticamente y no necesita que nadie la
   recuerde para una tabla nueva, salvo para declarar la excepción si hace
   falta.

## Decisión

Se implementa `tests/automation/test_tablas_indexadas_por_enum.py`: una
guarda que recorre `src/` con `ast` (sin importar ningún módulo), reconoce
toda constante de módulo anotada `dict[MiEnum, X]` cuyo valor es un `dict`
literal, y exige que sus claves cubran el enum entero. Una tabla incompleta
sin declarar rompe la prueba nombrando el fichero, la tabla y las variantes
que faltan.

La parcialidad legítima se declara en `PARCIALIDAD_DECLARADA` (diccionario
`(archivo, nombre) -> ParcialidadDeclarada(motivo, ausentes)` dentro del
propio test): la lista cerrada de las 4 tablas que la medición confirmó
incompletas a propósito. `ausentes` fija el conjunto exacto de miembros cuya
falta autoriza el motivo -no la tabla entera-, así que si aparece una
ausencia nueva que ese conjunto no cubre la guarda la sigue señalando aunque
la tabla ya esté en la lista (#288). Tres pruebas complementarias evitan que
esa lista se pudra: una falla si el conjunto de ausentes ya no coincide con
el declarado, otra si una entrada declarada ya está completa (la excepción
sobra), otra si la tabla que declaraba ya no existe con ese nombre (la
excepción queda huérfana).

### Qué reconoce el criterio, y qué no (requisito 6 de la incidencia #287)

Reconoce: una asignación anotada `nombre: dict[MiEnum, X] = {...}` en el
nivel superior de un fichero de `src/`, con un `dict` literal por valor y
claves de la forma `MiEnum.MIEMBRO`.

No reconoce, y queda escrito aquí en vez de presentarse como cobertura
completa (mismo criterio que ADR-078 aplicó a lo que su detector no
atrapaba):

- Tablas que no viven como constante de módulo: una tabla local a una
  función o anidada en una clase no se ve.
- Tablas sin la anotación explícita `dict[UnEnum, X]`: un `dict()` llamado,
  una comprensión, una tabla `Dict[...]` de `typing` en vez de `dict[...]`,
  o una fusionada con `{**a, **b}`.
- Tablas cuya clave es un tipo compuesto que incluye un enum sin ser
  únicamente el enum: `dict[tuple[CaptureCommand, StudioCaptureState], X]`
  (`sirius.application.capture_replies._PHRASES`) no se mira, porque la
  clave es una tupla, no el enum.
- Enums definidos con la API funcional (`Color = Enum("Color", [...])`) en
  vez de `class Color(Enum):`. No hay ninguno en `src/` hoy.
- Dos enums con el mismo nombre en módulos distintos: la guarda lleva un
  registro global por nombre. No ocurre hoy (37 clases de enum, cero
  colisiones), y si ocurriera la propia prueba lo señala con una aserción
  explícita en vez de mezclar miembros en silencio.

## Comprobación que la sostiene

**Medición (requisito 1): todas las tablas `dict[Enum, X]` de `src/`.**
Con el script de análisis que luego se convirtió en el cuerpo de la guarda
(`ast`, sin importar nada), sobre el árbol de `main` en `e607c6e`:

37 clases de enum definidas en `src/`, cero nombres duplicados. 15 tablas
`dict[Enum, X]` reconocidas:

```
src/sirius_engine/intent_interpreter.py:_ALCANCE_POR_CLASE   (WorkItemClass)         5/7  incompleta
src/sirius_engine/intent_interpreter.py:_CRITERIO_POR_CLASE  (WorkItemClass)         5/7  incompleta
src/sirius_engine/dispatch_cli.py:TABLA_PERFILES             (WorkItemClass)         2/7  incompleta
src/sirius_engine/dispatcher.py:TABLA_ACTIVACION             (WorkItemClass)         2/7  incompleta
src/sirius/domain/model_studio.py:_INTERACTION_LABELS        (StudioInteractionState) 10/10 completa
src/sirius/domain/model_studio.py:_CAPTURE_LABELS            (StudioCaptureState)     9/9  completa
src/sirius/application/studio_voice.py:_CAPTURE_MESSAGES     (AudioCaptureErrorKind)  6/6  completa
src/sirius/application/studio_voice.py:_TRANSCRIPTION_MESSAGES (TranscriptionErrorKind) 9/9 completa
src/sirius/application/studio_voice.py:_SPEECH_MESSAGES      (SpeechErrorKind)        9/9  completa
src/sirius/application/studio_capture.py:_ERROR_MESSAGES     (CaptureErrorKind)       7/7  completa
src/sirius/presentation/error_messages.py:_MESSAGES_BY_KIND  (LLMErrorKind)           9/9  completa
src/sirius/ports/credential_validation.py:_SAFE_MESSAGES     (CredentialValidationKind) 7/7 completa
src/sirius/adapters/llm/openai_responses.py:_SAFE_MESSAGES   (LLMErrorKind)           9/9  completa
src/sirius/presentation/model_studio/studio_page.py:_SPEAKER_LABELS (MessageRole)     2/2  completa
src/sirius/presentation/model_studio/presence_widget.py:_LOOKS (StudioInteractionState) 10/10 completa
```

**11 completas, 4 incompletas.** Esto amplía la muestra parcial de la nota de
arranque (8 tablas, sobre las importables sin pantalla) a las 15 que existen
de verdad en `src/`, incluyendo las de `sirius.presentation` que la nota ya
avisaba que faltaban.

**Verificación a mano de las 4 incompletas — ¿defecto real o parcialidad
legítima?**

- `TABLA_PERFILES` (`src/sirius_engine/dispatch_cli.py:65`): el comentario
  junto a la tabla dice «Solo cubre las dos clases despachables
  -`programacion` y `auditoria`-: para cualquier otra, `dispatch_work_item`
  rechaza el despacho antes de que el perfil llegue a proyectarse». Leído
  `dispatcher.py` (guarda 2 de `dispatch_work_item`, líneas 24-28): en efecto
  levanta `ClaseNoDespachableError` para cualquier clase fuera de
  `TABLA_ACTIVACION` antes de leer ningún perfil. **Parcialidad legítima.**
- `TABLA_ACTIVACION` (`src/sirius_engine/dispatcher.py:103`): el comentario
  la llama «Tabla cerrada de clase -> etiquetas (contrato §12.4, ADR-068)
  (...) Añadir una fila es una enmienda del contrato, no una decisión de
  implementación». **Parcialidad legítima**, y explícitamente fuera del
  alcance de este bloque tocarla (cualquier cambio de contrato es una
  decisión aparte).
- `_ALCANCE_POR_CLASE` y `_CRITERIO_POR_CLASE`
  (`src/sirius_engine/intent_interpreter.py:74,105`): leído
  `interpretar_intencion_v0` (líneas 189-213), la única clave con la que se
  indexan ambas tablas es `clase_efectiva`, que vale `clase` (el resultado de
  `_VERBO_A_CLASE.get(verbo)`, cuyo rango es
  `{PROGRAMACION, INVESTIGACION, DOCUMENTACION, AUDITORIA}`) o, si `clase` es
  `None`, el valor fijo `WorkItemClass.CONSULTA_LARGA`. `CONVERSACION_NO_APLICA`
  y `MIXTA` no pueden llegar nunca a esa indexación por construcción del
  código, no por casualidad. **Parcialidad legítima.**

**Cero defectos reales encontrados** en esta medición: el único defecto real
conocido de esta familia (`_SAFE_MESSAGES` sin `CONFIGURATION`, PR #278) ya
está corregido en `main`.

**La parcialidad legítima es la excepción (4 de 15), no la norma**: el
criterio de parada (a) no se disparó. La guarda entra.

**Requisito 2 — se ha visto fallar.** Se retiró temporalmente la entrada
`LLMErrorKind.CONFIGURATION` de la tabla `_SAFE_MESSAGES`, real y completa,
en `src/sirius/adapters/llm/openai_responses.py`, y se ejecutó:

```
$ uv run pytest tests/automation/test_tablas_indexadas_por_enum.py::test_las_tablas_indexadas_por_enum_cubren_el_enum_o_estan_declaradas -v
...
FAILED ...: AssertionError: src/sirius/adapters/llm/openai_responses.py:_SAFE_MESSAGES (dict[LLMErrorKind, ...]) no cubre: ['CONFIGURATION']. Complétala, o declárala en PARCIALIDAD_DECLARADA con el motivo.
```

Se restauró el fichero (`git diff` vacío tras restaurar) y se volvió a
ejecutar la suite completa del módulo, en verde. La guarda nombra exactamente
la tabla y la variante que falta, como exige el requisito.

**Requisito 5 — la guarda encuentra el defecto histórico de la PR #278.**
Como el árbol anterior a la PR #278 no está disponible como rama de este
repositorio (main ya lo tiene fusionado), se usa la reconstrucción
equivalente que el propio requisito permite: un fichero fuente sintético con
la definición real de `LLMErrorKind` y la tabla `_SAFE_MESSAGES` exactamente
como estaba antes de la PR #278 (las mismas 8 claves, sin `CONFIGURATION`).
Test permanente:
`tests/automation/test_tablas_indexadas_por_enum.py::test_la_guarda_encuentra_el_defecto_historico_de_la_pr_278`,
más su gemelo
`test_la_guarda_no_senala_la_misma_tabla_ya_completa` que fija que añadir la
clave que faltaba hace desaparecer el hallazgo.

**Requisito 3 — no depende de importar módulos de interfaz.** La guarda usa
únicamente `ast.parse` sobre el texto de cada fichero; no hay ninguna
sentencia `import` de un módulo de `src/` en todo el fichero de la prueba.
Se comprobó ejecutando la suite dentro de este mismo entorno (el que ya
corre en modo *offscreen* para Qt), donde módulos como
`sirius.presentation.model_studio.presence_widget` sí necesitan Qt para
importarse pero sus tablas (`_LOOKS`) se reconocen igualmente porque nunca se
importa el módulo.

**Requisito 7 — determinista y sin red.** Sin novedad: `ast.parse` sobre
ficheros locales, sin reloj ni aleatoriedad ni E/S de red.

Suite completa del bloque:

```
$ uv run pytest tests/automation/test_tablas_indexadas_por_enum.py -v
7 passed
```

## Consecuencias

- Una tabla nueva `dict[Enum, X]` que llegue incompleta rompe esta guarda
  hasta que se complete o se declare en `PARCIALIDAD_DECLARADA` con su
  motivo: el fallo silencioso de la PR #278 no puede repetirse para ninguna
  tabla que el criterio reconozca.
- Las formas de tabla listadas en "Qué reconoce el criterio, y qué no" siguen
  sin cobertura. En particular, `_PHRASES`
  (`src/sirius/application/capture_replies.py`) usa una clave compuesta
  (`tuple[CaptureCommand, StudioCaptureState]`) y esta guarda no la mira; si
  se quisiera cubrir haría falta una decisión aparte sobre qué significa
  "cobertura total" para una clave compuesta (¿el producto cartesiano
  completo?, ¿solo las combinaciones alcanzables?), que #287 no pide resolver.
- `PARCIALIDAD_DECLARADA` es una lista que puede crecer. Las dos pruebas que
  la acompañan (`test_la_parcialidad_declarada_sigue_siendo_incompleta`,
  `test_la_parcialidad_declarada_sigue_existiendo_como_tabla`) evitan que
  crezca con excepciones que ya no hacen falta, pero no evitan que alguien
  declare una excepción para un defecto real en vez de arreglarlo: esa
  decisión la sigue tomando quien revisa la PR que la añade, igual que con
  cualquier otra excepción declarada del repositorio (`DUPLICADO_HISTORICO`,
  `BORRADOS_A_PROPOSITO`).

## Alternativas descartadas y por qué

- **Guarda de exhaustividad manual por tabla** (opción 3 arriba): descartada
  porque es el patrón que ya falló en la PR #278 — depende de que cada tabla
  nueva traiga su propia prueba, y ninguna la obliga a existir.
- **Introspección en tiempo de ejecución** (opción 2 arriba): descartada por
  el criterio de parada (b) sin necesidad de medir más: varios módulos con
  tablas relevantes (`sirius.presentation.model_studio.*`) requieren Qt para
  importarse.
- **Extender la cobertura a claves compuestas o a tablas construidas
  dinámicamente**: no lo pide la incidencia #287 (fuera de alcance,
  explícito) y habría exigido definir qué es "cobertura total" para esos
  casos sin datos que lo sostengan — la misma familia de riesgo que ADR-078
  evitó no endurecer su criterio sin medir contra casos reales.
