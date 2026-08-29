# Plan de Pruebas de Aceptación — Sirius 0.2 «Memoria útil»

**Identificador:** `SIRIUS-PRUEBAS-0.2-MEMORIA-UTIL`
**Versión:** v0.1
**Estado:** PROPUESTO
**Fecha:** 29 de agosto de 2026
**Autoridad final:** usuario propietario del Proyecto Sirius

> La aprobación de este documento es la fusión de la Pull Request que lo introduce, por
> el propietario. Este documento **no autoriza implementación**: opera exactamente igual
> que la cabecera de `docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:9-12`.

## 0. Origen y alcance

`docs/evolution/RECTOR.md` §17 («Regla de activación», líneas 282-290) exige, antes de que
una etapa posterior a Sirius 0.1 pueda empezar, entre otras condiciones: «existe una
Definición de Producto aprobada» y «existen pruebas de aceptación reproducibles»
(`docs/evolution/RECTOR.md:287-288`). La Definición de Producto de Sirius 0.2 ya existe,
en estado PROPUESTO, en
`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md`. Este documento cubre
la segunda condición: operacionaliza como pruebas de aceptación reproducibles los
criterios de comprobación que esa Definición ya fija en sus secciones §2.4, §3.4, §4.4,
§5.4, §6.4 y en la puerta integral §7.1.

La tercera condición de la regla de activación —«se aprueba la arquitectura técnica
correspondiente»— se desarrolla en paralelo en la PR #418, todavía en elaboración. Este
plan **no depende de esa Arquitectura ni la cita como aprobada**: donde una prueba
necesita un dato que solo la Arquitectura puede fijar (el disparador de la sugerencia de
guardado tras una conversación, §4 más abajo), este plan lo señala como pendiente y
define la prueba de forma que valga para cualquier mecanismo que la Arquitectura acabe
eligiendo, en vez de darlo por decidido.

Ninguna cifra ni umbral de este documento es inventado: todos proceden literalmente de
`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md`, con cita de línea en cada uso. Este
plan no modifica ningún otro fichero del repositorio.

## 1. El plan de pruebas de 0.1, usado solo como referencia de estilo

Existe en `main` un plan de pruebas de Sirius 0.1:
`docs/canonical/SIRIUS_PLAN_PRUEBAS_TRAZABILIDAD_0.1_v1.0_PROPUESTO.docx`. Es un documento
canónico de otra versión, con su propio ciclo de aprobación ya cerrado; este plan **no
reutiliza ni su contenido ni sus cifras**, solo su forma: identificador de prueba,
precondiciones/preparación, pasos, resultado esperado verificable, y la regla de
aceptación que ese documento fija — «una prueba pasa solo cuando existe evidencia
observable […] no sustituyen un resultado, una captura, un log de prueba o una evaluación
registrada» (extracto literal de su sección 1, «Estrategia»). Esa misma regla rige aquí:
ninguna PA de este plan se da por superada por inspección o por parecer razonable.

A diferencia del plan de 0.1, este documento no repite secciones que la incidencia que lo
origina no pidió (entorno de referencia, niveles de severidad, suite de personalidad
completa): su contenido se limita a lo que el objetivo de la incidencia autoriza —
operacionalizar §2.4, §3.4, §4.4, §5.4, §6.4 y §7.1 de la Definición de Producto de 0.2.

## 2. Metodología común: el banco de casos versionado

Las secciones 2 y 3 de la Definición de Producto miden un banco congelado de 47 casos
sobre la rama `evidence/adr001-spikes` (PR #117), **abierta y sin fusionar en `main`**
(`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:41`). Esas cifras son, por
declaración explícita de la propia Definición, «evidencia reportada, no verificada por
este documento contra su fuente» (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:46`).
Este plan de pruebas hereda esa misma cautela y no las trata como hechos de `main`.

Las pruebas PA-0.2-BUS-01, PA-0.2-REC-01 y PA-0.2-PUERTA-01 (más abajo) dependen de ese
banco. Se ejecutan **cuando** el paquete correspondiente se incorpore a `main` — no antes
— contra «el mismo banco de 47 casos (o su sucesor versionado)»
(`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:87-88`). PA-0.2-PUERTA-01 usa como
piso de no-regresión «la última cifra incorporada a `main`», tal como la propia Definición
lo fija en la puerta integral
(`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:279-280,282`); esa regla solo tiene
sentido ahí porque, para cuando PUERTA-01 se ejecuta, las seis PA anteriores ya la
superaron en `main` con una cifra propia que sirve de referencia.
PA-0.2-REC-01 (§3.4) no puede aplicar la misma regla: es la primera prueba en establecer
esa cifra en `main`, así que «la última cifra incorporada a `main`» no existiría todavía y
el criterio quedaría vacío, dejando pasar cualquier regresión frente a lo que demostró la
PR #117. §3.4 fija en su lugar el piso literal de la propia PR #117. De esas cifras
(aciertos exactos 24/47→29/47, elementos de más 29→21, omisiones críticas 11→1, cobertura
63/81 frente a 64/81, `SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:73-75`), solo la
de cobertura es ambigua: la propia Definición no distingue con certeza cuál de las dos
cifras —63/81 o 64/81— es la alcanzada bajo el paquete activo. Por eso PA-0.2-REC-01 (§4)
exige el resto de cifras exactas y deja bloqueado únicamente el componente de cobertura
hasta que el propietario registre en el repositorio cuál de las dos es la correcta
(decisión pendiente 6 de la sección 10); ni esta sección ni PA-0.2-REC-01 fijan una de las
dos a ciegas ni delegan la elección a quien ejecute la prueba.

## 3. PA-0.2-BUS — Búsqueda mejorada

Desarrolla el criterio de comprobación de
`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §2.4 (líneas 84-90).

### PA-0.2-BUS-01 · Paquete de categoría/filtro incorporado y dentro de presupuesto

- **Precondiciones:**
  1. El propietario ha decidido qué parte del paquete adopta — el índice de categoría
     determinista, el filtro de relevancia con Ollama, o ambos — resolviendo la decisión
     abierta sobre la dependencia de Ollama
     (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:301-302`). Esta prueba no
     resuelve esa decisión ni presupone cuál de las dos opciones se elige: se ejecuta
     igual sobre lo que el propietario haya decidido incorporar.
  2. La parte decidida está fusionada en `main`, cableada en `ContextBuilder`.
  3. El banco de 47 casos, o su sucesor versionado con el cambio declarado, existe
     versionado en el repositorio.
- **Pasos:**
  1. Ejecutar contra `main` la prueba automática equivalente a la que produjo las cifras
     de la PR #117, sobre el banco versionado.
  2. Medir aciertos exactos, elementos de más, omisiones críticas y cobertura.
  3. Medir la latencia P95 de construir el contexto con el paquete activo.
- **Resultado esperado verificable:** la parte del paquete que el propietario decidió
  adoptar está fusionada y cubierta por la prueba automática del paso 1 (existe, se
  ejecuta, no está marcada `skip`); la latencia P95 medida en el paso 3 cumple el
  presupuesto de `ContextBuilder` fijado por RNF-003 — 300 ms P95
  (`docs/implementation/V8_EXECUTION.md:47`), citado como criterio explícito de §2.4
  (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:89-90`).
- **Automatizable:** sí, en cuanto el paquete esté fusionado — es una prueba de
  integración con el banco versionado como dato de entrada y una medición de latencia,
  sin dependencia de proveedor real ni de interfaz gráfica.
- **Depende de:** la decisión pendiente del propietario sobre Ollama (§7 de este plan).

## 4. PA-0.2-REC — Mejor recuperación

Desarrolla `SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §3.4 (líneas 120-125).

### PA-0.2-REC-01 · Banco versionado sin omisiones críticas conocidas

- **Precondiciones:**
  1. El paquete de mejor recuperación (el mismo B6 de §3.1,
     `SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:96-98`) está fusionado en `main`.
  2. La salvedad (a) de §3.2 está resuelta explícitamente — el banco se amplió con casos
     que ejerciten la «siembra al ensamblar contexto», o esa siembra se retiró del código
     (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:105-106,124-125`). Sin esta
     precondición cumplida, esta PA no puede declararse superada — la propia Definición lo
     exige como condición previa, no solo deseable.
  3. El propietario ha registrado en el repositorio cuál de las dos cifras de cobertura
     que cita la Definición para el paquete completo —63/81 o 64/81
     (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:74`)— es la alcanzada bajo el
     paquete activo. §1 de esa Definición declara esas cifras como evidencia reportada, no
     verificada, que no se completa con ninguna cifra adicional
     (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:46`), así que ni este plan ni
     quien ejecute la prueba pueden fijar una de las dos a ciegas: sin esta precondición,
     el componente de cobertura de esta PA no tiene un piso reproducible y no puede
     evaluarse (decisión pendiente 6 de la sección 10).
- **Pasos:**
  1. Ejecutar el banco de 47 casos, o su sucesor versionado, contra el pipeline de
     recuperación de `main`.
  2. Medir omisiones críticas conocidas, aciertos exactos y cobertura.
- **Resultado esperado verificable:** 0 omisiones críticas conocidas; aciertos exactos no
  por debajo de 29/47 — cifra literal medida en la PR #117 para el paquete completo
  (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:73`), que no está afectada por la
  ambigüedad de cobertura y por eso sí es exigible tal cual; cobertura no por debajo de la
  cifra que el propietario registre al resolver la precondición 3 — cita literal del
  criterio de §3.4 (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:123-124`), que fija
  ese piso de forma distinta a como lo hace la puerta integral §7.1
  (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:279-282`): esta PA no usa «la última
  cifra incorporada a `main`» como piso, porque es la primera en establecer esa cifra en
  `main` y la regla de PUERTA-01 dejaría el criterio vacío (ver §2 de este plan). La
  omisión crítica por derivación léxica que §3.2 documenta como conocida
  (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:107-108`) debe quedar cerrada, no
  solo caracterizada.
- **Automatizable:** sí — misma forma que PA-0.2-BUS-01, sin proveedor real, una vez
  resuelta la precondición 3.
- **Depende de:** la resolución de las dos puertas que ADR-002 (de la rama de evidencia,
  no `docs/decisions/ADR-002`) dejó NO CONFORME, de la decisión del propietario sobre la
  última omisión crítica (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:303-305`) y
  del registro de la cifra exacta de cobertura de la precondición 3. Esta PA no resuelve
  ninguna de esas decisiones: se limita a medir si, una vez tomadas e implementadas, el
  banco pasa con 0 omisiones críticas y sin degradar los pisos que quedan fijados.

## 5. PA-0.2-SUG — Sugerencias confirmadas

Desarrolla `SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §4.4 (líneas 167-172).
Sirius 0.1 no tiene hoy ningún flujo de este tipo (§4.1,
`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:131-132`), así que ambas PA de este
bloque describen cómo se verificará cuando el flujo exista, no un comportamiento actual.

Este bloque depende de dos decisiones que ni la Definición de Producto ni esta incidencia
resuelven, y que este plan **no resuelve por su cuenta**:

- el origen de los estados que sostienen «propuesta pendiente de confirmar» — no
  localizados en `main` (§4.1, líneas 147-153; PENDIENTE DE DECISIÓN, §7.3, líneas
  306-310);
- el disparador de la sugerencia tras una conversación — la Arquitectura Técnica en curso
  (PR #418, no aprobada, no citada aquí como fuente) lo deja como decisión pendiente.

Ambas PA se definen para valer con cualquier salida de esas dos decisiones: no asumen un
mecanismo de disparo concreto (automático tras cada conversación, por heurística, o a
petición explícita del usuario) ni una forma concreta de estado «pendiente de confirmar».

### PA-0.2-SUG-01 · Confirmar una propuesta de guardado

- **Precondiciones:**
  1. El flujo de propuesta de guardado existe en `main` (fuera del alcance de esta
     incidencia: no existe hoy).
  2. El estado «propuesta pendiente de confirmar» — cualquiera que sea su origen final,
     ver arriba — está implementado para memoria y para decisión.
- **Pasos:**
  1. Mantener una conversación real con Sirius hasta que, por el mecanismo que la
     Arquitectura Técnica defina, aparezca al menos una propuesta de guardado visible en
     la interfaz.
  2. Confirmar la propuesta desde la interfaz.
- **Resultado esperado verificable:** la propuesta confirmada queda como memoria o
  decisión vigente, con origen trazable por el mismo mecanismo que ya usan
  `SaveManualMemoryUseCase` (`src/sirius/application/save_manual_memory.py:48`) o
  `ProposeDecisionUseCase` (`src/sirius/application/propose_decision.py:1-10`) — cita
  literal del criterio de comprobación
  (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:170-171`).
- **Automatizable:** sí, en cuanto el flujo exista — prueba de integración con doble
  determinista del proveedor, en la misma forma que
  `tests/integration/test_manual_memory_origin.py::test_explicit_save_creates_a_traceable_memory_and_its_origin_can_be_opened`
  y `tests/integration/test_decision_lifecycle.py`, ambas ya existentes en `main` para el
  guardado manual explícito.
- **Depende de:** las dos decisiones pendientes señaladas arriba.

### PA-0.2-SUG-02 · Rechazar una propuesta de guardado no deja rastro

- **Precondiciones:** las mismas que PA-0.2-SUG-01.
- **Pasos:**
  1. Repetir el paso 1 de PA-0.2-SUG-01 hasta obtener una propuesta visible.
  2. Rechazar la propuesta desde la interfaz.
  3. Consultar el contexto ordinario que `ContextBuilder` ensambla para la conversación
     siguiente.
- **Resultado esperado verificable:** no se crea ninguna memoria ni decisión nueva; el
  contexto ordinario consultado en el paso 3 no contiene ningún rastro de la propuesta
  rechazada — cita literal del criterio
  (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:171-172`).
- **Automatizable:** sí, en cuanto el flujo exista — misma forma que
  `tests/integration/test_decision_lifecycle.py::test_debating_alternatives_never_creates_a_decision`,
  que ya prueba una propiedad equivalente («debatir sin aprobar no crea una decisión») para
  el flujo manual existente.
- **Depende de:** las dos decisiones pendientes señaladas arriba.

## 6. PA-0.2-CONF — Conflictos asistidos

Desarrolla `SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §5.4 (líneas 216-220). A
diferencia de los bloques anteriores, la detección y su listado ya existen y están
probados en `main` (§5.1,
`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:176-200`); verificado directamente:
`find_subject_conflicts` filtra a solo `CONFLICT` (`src/sirius/domain/precedence.py:166-192`),
`DetectPrecedenceConflictsUseCase.detect()` expone esa consulta de solo lectura
(`src/sirius/application/detect_precedence_conflicts.py:28-46`), y `KnowledgeWidget` la
cablea a un botón que solo lista, sin ninguna acción de resolución todavía conectada
(`src/sirius/presentation/knowledge_widget.py:627-669`). Lo único que falta, y lo único que
esta PA nueva cubre, es la acción de resolución sobre ese listado (§5.3,
`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:209-214`).

### PA-0.2-CONF-01 · Resolver un conflicto listado lo retira de la siguiente detección

- **Precondiciones:**
  1. Dos memorias vigentes del mismo `subject_key`/`project_id`, sin ninguna decisión
     aprobada para ese mismo asunto — o, alternativamente, exactamente dos decisiones
     aprobadas para el mismo asunto —, de forma que `evaluate_subject_precedence` devuelva
     `CONFLICT` (`src/sirius/domain/precedence.py:150-157`) y no `DECISION_PRECEDENCE`.
     Exactamente una decisión aprobada produce siempre `DECISION_PRECEDENCE`, con
     independencia de cuántas memorias haya
     (`src/sirius/domain/precedence.py:142-148`), así que «una memoria y una decisión
     aprobada» nunca es una configuración de conflicto y no vale como precondición. Más de
     dos decisiones aprobadas tampoco vale: el paso 3 ejecuta una sola acción de
     resolución, y sustituir solo una de tres deja las otras dos aprobadas
     (`src/sirius/application/supersede_decision.py:118-121`), con lo que
     `evaluate_subject_precedence` seguiría devolviendo `CONFLICT`
     (`src/sirius/domain/precedence.py:150-157`); exactamente dos es el único número para
     el que una sola sustitución basta.
  2. Las acciones de resolución (corregir, archivar, aprobar/sustituir una decisión) están
     cableadas desde el listado de `KnowledgeWidget` a los casos de uso ya existentes de
     corrección, archivado o aprobación — pendiente de construir (§5.3).
- **Pasos:**
  1. Provocar el conflicto descrito en la precondición 1.
  2. Pulsar «Detectar conflictos de precedencia» y confirmar que el conflicto aparece
     listado (comportamiento ya cubierto hoy por
     `tests/gui/test_knowledge_widget.py:517-535`).
  3. Elegir, sobre el conflicto listado, una acción de resolución que elimine la
     ambigüedad estructural que causa el conflicto — archivar una de las dos memorias en
     conflicto, o sustituir una de las dos decisiones aprobadas por la otra
     (`SupersedeDecisionUseCase.supersede`,
     `src/sirius/application/supersede_decision.py:70-77`) cuando el conflicto es entre
     decisiones aprobadas, dejando una sola `APPROVED` para el asunto. Corregir el
     contenido de una memoria no sirve para este paso: la corrección crea una nueva
     revisión vigente sin cambiar su `subject_key` (`src/sirius/domain/memory.py:49-59`)
     ni reducir el número de memorias vigentes del mismo asunto, así que la segunda
     detección seguiría reportando el conflicto. Aprobar una decisión adicional tampoco
     sirve: aumenta, no reduce, el número de decisiones aprobadas para el asunto.
  4. Repetir la detección del paso 2.
- **Resultado esperado verificable:** tras el paso 3, la detección del paso 4 ya no
  reporta ese conflicto; en ningún paso se elige un ganador automáticamente — cita literal
  del criterio (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:218-220`).
- **Automatizable:** sí, sin condiciones pendientes — extiende directamente
  `tests/gui/test_knowledge_widget.py:517-535` con la acción de resolución y una segunda
  detección; no depende de proveedor real, de Ollama ni del banco versionado.

## 7. PA-0.2-HIST — Proyectos históricos consultables

Desarrolla `SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §6.4 (líneas 245-249).
Verificado directamente: `ProjectRepository` hoy solo expone `get_project(project_id)`,
que devuelve un proyecto por id conocido y nunca sirve para descubrirlos
(`src/sirius/ports/project_repository.py:29-36`); no existe ningún método de listado de
proyectos `COMPLETED`.

### PA-0.2-HIST-01 · Listar proyectos completados sin mezclarlos con el activo

- **Precondiciones:**
  1. Existe un proyecto `ACTIVE` y al menos dos proyectos `COMPLETED` en la base local.
  2. La operación de listado de proyectos completados (pendiente de construir, §6.3) está
     fusionada en `main`.
- **Pasos:**
  1. Leer el estado y el contexto del proyecto activo antes de cualquier consulta al
     histórico.
  2. Invocar la operación de listado de proyectos `COMPLETED`.
  3. Abrir la vista de proyectos históricos en la interfaz.
  4. Releer el estado y el contexto del proyecto activo tras los pasos 2 y 3.
- **Resultado esperado verificable:** el listado del paso 2 devuelve exactamente los
  proyectos `COMPLETED` existentes y ningún `ACTIVE`; la vista del paso 3 es distinta de
  la vista del proyecto activo; el estado y el contexto leídos en el paso 4 son idénticos
  a los leídos en el paso 1 — cita literal del criterio
  (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:247-249`).
- **Automatizable:** sí, sin condiciones pendientes — prueba de integración con
  repositorio real (misma forma que
  `tests/integration/test_initial_project_persistence.py`, que ya ejercita persistencia y
  recuperación de proyecto) más una prueba de interfaz para la vista separada.

## 8. PA-0.2-PUERTA — Puerta de salida integral

Desarrolla `SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §7.1 (líneas 253-290), que
cita a su vez la puerta de `RECTOR.md` §9.1 («puede construir un paquete de contexto
fiable y trazable para una tarea externa», `docs/evolution/RECTOR.md:146`) y su evidencia
exigida («recupera información correcta a través de varias sesiones sin aumentar ruido»,
`docs/evolution/RECTOR.md:145`).

### PA-0.2-PUERTA-01 · Paquete de contexto fiable para una tarea externa real

- **Precondiciones:**
  1. Las seis PA de este plan que cubren las secciones 2 a 6 de la Definición —
     PA-0.2-BUS-01, PA-0.2-REC-01, PA-0.2-SUG-01, PA-0.2-SUG-02, PA-0.2-CONF-01 y
     PA-0.2-HIST-01 — están superadas en `main`, sin excepción. Un subconjunto no basta:
     «el alcance de Sirius 0.2 es indivisible»
     (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:270-271`, que cita
     `RECTOR.md:143`).
  2. Existe una tarea externa real, no sintética, identificada, que requiera contexto de
     más de una sesión de conversación.
- **Pasos:**
  1. Ejecutar la tarea externa real a través de varias sesiones.
  2. Dejar que Sirius ensamble el paquete de contexto para esa tarea combinando los cinco
     resultados de las secciones 2 a 6.
  3. Medir, sobre el banco de casos versionado (metodología de la sección 2 de este
     plan), aciertos exactos, cobertura, omisiones críticas y elementos de más.
  4. Verificar el origen de cada elemento del paquete con
     `GetMemoryOriginUseCase` (`src/sirius/application/memory_origin.py:52`) o
     `GetDecisionOriginUseCase` (`src/sirius/application/decision_origin.py:63`).
- **Resultado esperado verificable**, las cuatro condiciones que fija §7.1
  (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:267-286`), sin ninguna cifra
  inventada por este plan:
  1. los cinco bloques incorporados y comprobados en `main`, sin excepción;
  2. 0 omisiones críticas conocidas sobre el banco versionado, sin degradar aciertos
     exactos ni cobertura por debajo de la última cifra incorporada a `main`;
  3. los elementos de más no empeoran respecto a la última cifra incorporada a `main`;
  4. cada elemento del paquete tiene origen localizable, ninguno sin origen.
- **Automatizable:** parcial. Las condiciones 2 a 4 son automatizables contra el banco
  versionado y el mecanismo de origen ya existente. La condición 1 es una comprobación de
  estado del repositorio (las seis PA anteriores superadas), no una prueba en sí. Elegir
  y ejecutar «una tarea externa real» (paso 1) es evaluación humana por definición — mismo
  motivo que PA-E2E-01 del plan de 0.1 (sección 7 de
  `docs/canonical/SIRIUS_PLAN_PRUEBAS_TRAZABILIDAD_0.1_v1.0_PROPUESTO.docx`): una tarea
  real con valor genuino para el usuario no se sintetiza ni se sustituye por un banco de
  casos.
- **Depende de:** la superación de las seis PA anteriores y, por tanto, de todas las
  decisiones pendientes de las que ellas dependen.

## 9. Trazabilidad de este plan con la Definición de Producto

| Bloque de la Definición | Sección | Líneas | PA de este plan |
|---|---|---|---|
| Búsqueda mejorada | §2.4 | 84-90 | PA-0.2-BUS-01 |
| Mejor recuperación | §3.4 | 120-125 | PA-0.2-REC-01 |
| Sugerencias confirmadas | §4.4 | 167-172 | PA-0.2-SUG-01, PA-0.2-SUG-02 |
| Conflictos asistidos | §5.4 | 216-220 | PA-0.2-CONF-01 |
| Proyectos históricos consultables | §6.4 | 245-249 | PA-0.2-HIST-01 |
| Puerta de salida integral | §7.1 | 253-290 | PA-0.2-PUERTA-01 |

Esta tabla es la trazabilidad propia de este plan, no una extensión de
`docs/implementation/TRAZABILIDAD_PA_SP.md`: esa matriz pertenece a Sirius 0.1 y a su
propio proceso comprobado por `tests/unit/test_pa_sp_traceability.py`
(`docs/implementation/TRAZABILIDAD_PA_SP.md:7-11`); ampliarla con los identificadores
`PA-0.2-*` queda fuera del alcance de esta incidencia y es trabajo de implementación
posterior, no de este documento.

## 10. Decisiones pendientes del propietario que condicionan estas pruebas

Esta lista reproduce, sin resolverlas, las decisiones que
`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` §7.3 (líneas 297-310) deja abiertas, y
añade una quinta que no vive en esa sección sino en la Arquitectura Técnica en curso.
Ninguna PA de este plan da una de estas decisiones por tomada:

1. **Fusionar o no la PR #117** como vía de entrada de su evidencia — afecta a si el banco
   de 47 casos llega a `main` en algún momento, precondición de PA-0.2-BUS-01,
   PA-0.2-REC-01 y PA-0.2-PUERTA-01.
2. **La dependencia de Ollama** en el filtro de relevancia — afecta a qué parte del
   paquete adopta PA-0.2-BUS-01; la prueba se definió para valer con cualquiera de las dos
   partes.
3. **La última omisión crítica de recuperación** — afecta al umbral de cierre de
   PA-0.2-REC-01.
4. **El origen de los estados `CANDIDATA`/`RECHAZADA`** — afecta a la forma concreta del
   estado «propuesta pendiente de confirmar» en PA-0.2-SUG-01 y PA-0.2-SUG-02; ambas
   pruebas se definieron sin asumir una forma concreta.
5. **El disparador de la sugerencia tras una conversación**, que la Arquitectura Técnica
   en curso (PR #418, no aprobada) deja como decisión pendiente — afecta al paso 1 de
   PA-0.2-SUG-01 y PA-0.2-SUG-02; ambas pruebas se definieron para valer con cualquier
   mecanismo de disparo.
6. **Cuál de las dos cifras de cobertura que cita la Definición para el paquete
   completo** —63/81 o 64/81 (`SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:74`)— es
   la alcanzada bajo el paquete activo. No proviene de §7.3 ni de la Arquitectura: es una
   ambigüedad de la propia evidencia de la PR #117 (§1 de esa Definición,
   `SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:46`), que este plan no resuelve
   inventando una de las dos. Afecta al componente de cobertura del piso de no-regresión
   de PA-0.2-REC-01 (precondición 3).

## 11. Criterios de salida de este plan

- Las seis PA de bloque de este documento — PA-0.2-BUS-01, PA-0.2-REC-01,
  PA-0.2-SUG-01, PA-0.2-SUG-02, PA-0.2-CONF-01 y PA-0.2-HIST-01 — superadas con evidencia
  observable — resultado, captura, log de prueba o evaluación registrada — no por
  inspección, y solo después PA-0.2-PUERTA-01 superada en las mismas condiciones: son
  siete PA en total, y la puerta integral no sustituye a ninguna de las seis anteriores
  ni puede darse por superada sin ellas (precondición 1 de PA-0.2-PUERTA-01, líneas
  306-311 de este mismo documento).
- Ninguna PA se declara superada mientras su precondición dependiente de una decisión
  pendiente (sección 10) siga sin resolver.
- La trazabilidad de la sección 9 no contiene ningún criterio de comprobación de la
  Definición de Producto sin una PA que lo cubra.
