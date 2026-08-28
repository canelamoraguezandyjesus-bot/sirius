# Definición de Producto — Sirius 0.2 «Memoria útil»

**Identificador:** `SIRIUS-PRODUCTO-0.2-MEMORIA-UTIL`
**Versión:** v0.1
**Estado:** PROPUESTO
**Fecha:** 28 de agosto de 2026
**Autoridad final:** usuario propietario del Proyecto Sirius

> La aprobación de este documento es la fusión de la Pull Request que lo introduce, por
> el propietario. Este documento **no autoriza implementación**: el roadmap posterior a
> Sirius 0.1 sigue sin autorizar, con la única excepción vigente del Sirius Work Engine,
> descrita en `docs/evolution/STATUS.md`.

## 0. Origen y jerarquía

Este documento desarrolla `docs/evolution/RECTOR.md` §9.1 («Sirius 0.2 — Memoria útil»),
bajo la jerarquía documental de `RECTOR.md` §16: el Documento Rector fija dirección y
puertas; esta Definición de Producto desarrolla el problema, el alcance y la evidencia de
la versión, pero no sustituye al Rector ni se activa por sí sola (`RECTOR.md` §17,
«Regla de activación»).

Texto íntegro de `RECTOR.md` §9.1 (`docs/evolution/RECTOR.md:140-146`):

> **Problema:** 0.1 demuestra persistencia, pero no todavía selección y recuperación de
> alta calidad.
> **Incluye:** búsqueda mejorada, sugerencias confirmadas, conflictos asistidos, mejor
> recuperación y proyectos históricos consultables.
> **Excluye:** agentes, herramientas externas, voz y automatización.
> **Evidencia:** recupera información correcta a través de varias sesiones sin aumentar
> ruido.
> **Puerta:** puede construir un paquete de contexto fiable y trazable para una tarea
> externa.

Sirius 0.1 fue aceptado y cerrado por el propietario el 10 de agosto de 2026
(`docs/implementation/V8_EXECUTION.md:17-18`; declaración completa en
`docs/implementation/V8_EXECUTION.md:20-41`), lo que abre formalmente la definición de
esta versión (`docs/evolution/STATUS.md:48-60`).

## 1. Sobre la evidencia citada de la PR #117

La rama `evidence/adr001-spikes` (PR #117) está **abierta y sin fusionar: no está en
`main`**. Por instrucción explícita de la incidencia que origina este documento, este
documentalista no ha leído esa rama; las cifras de las secciones 2 y 3 provienen
literalmente de la orden de trabajo (Work ID `WI-20260828-205339`), no de una lectura
directa del experimento. Se citan como tales — evidencia reportada, no verificada por
este documento contra su fuente — y no se alteran ni se completan con ninguna cifra
adicional.

Todo lo demás que este documento afirma sobre el estado de Sirius 0.1 sí se ha verificado
directamente contra `main` en esta misma revisión, con cita de archivo y línea.

## 2. Búsqueda mejorada

### 2.1 Qué cubre ya Sirius 0.1

El bloque B6 («Selección y presupuesto de contexto») está completo: índices FTS5, su
sincronización transaccional, recuperación y ordenación de relevancia comprobable,
presupuesto y recorte determinista con un estimador local de tokens, y su cableado
dentro de `ContextBuilder` con la sección de decisiones vigentes relacionadas; cierra
D-11 (`docs/implementation/V8_EXECUTION.md:160`). Esto es búsqueda FTS5 con relevancia y
presupuesto de contexto.

### 2.2 Qué existe ya construido y medido como evidencia (PR #117, sin fusionar)

Medido sobre un banco congelado de 47 casos:

- un índice de categoría derivado de la criticidad del canon (determinista, sin modelo),
  que por sí solo baja las omisiones críticas de 11 a 5;
- un filtro de relevancia con modelo local vía Ollama que falla abierto;
- una regla en código que impide al filtro descartar un elemento crítico que la búsqueda
  trajo.

Resultado conjunto: aciertos exactos de 24/47 a 29/47, elementos de más de 29 a 21,
omisiones críticas de 11 a 1, cobertura 63/81 frente a 64/81, latencia dentro del
presupuesto de 5 s.

### 2.3 Qué falta por construir

Incorporarlo al producto: hoy es experimento en una rama sin fusionar, no comportamiento
de Sirius. Queda pendiente una decisión del propietario sobre la dependencia de Ollama —
la mitad del paquete (el índice de categoría determinista) funciona sin modelo; la otra
mitad (el filtro de relevancia) no.

### 2.4 Criterio de comprobación

El paquete de categoría y filtro, o la parte de él que el propietario decida adoptar,
queda fusionado en `main`, cubierto por prueba automática equivalente a la que produjo
estas cifras sobre el mismo banco de 47 casos (o su sucesor versionado), y ejecuta dentro
del presupuesto de latencia de `ContextBuilder` (RNF-003, ver
`docs/implementation/V8_EXECUTION.md:47`).

## 3. Mejor recuperación

### 3.1 Qué cubre ya Sirius 0.1

El mismo B6 de la sección 2.1: recuperación y ordenación de relevancia, con presupuesto y
recorte deterministas, cableados en `ContextBuilder`
(`docs/implementation/V8_EXECUTION.md:160`).

### 3.2 Qué existe ya construido y medido como evidencia (PR #117, sin fusionar)

El mismo paquete de evidencia de la sección 2.2, con tres salvedades que este documento
conserva sin suavizar:

- **(a)** la «siembra al ensamblar contexto» **no es validable** con ese banco: se
  escribió tras ver los fallos, y solo dos casos del banco activan ese propósito.
- **(b)** queda **1 omisión crítica conocida**, por derivación léxica («preferencia de
  redacción» frente a «prefiere que redactes»), con todas las vías medidas y descartadas.
- **(c)** ADR-002 (de esa rama de evidencia, no el `docs/decisions/ADR-002` de `main`)
  quedó cerrado **NO CONFORME**, con dos puertas nombradas: recall crítico a un caso del
  100 %, y conformidad de etapa con 14/46 sin resolver.

### 3.3 Qué falta por construir

Cerrar la última omisión crítica exigiría un diccionario a medida o rompería el
presupuesto de latencia; queda caracterizada, no resuelta (ver §7, decisión abierta).
Resolver las dos puertas que dejaron ADR-002 NO CONFORME. Decidir si la «siembra al
ensamblar contexto» se conserva sin banco que la valide o se retira.

### 3.4 Criterio de comprobación

El banco de 47 casos (o su sucesor versionado, con el cambio declarado) pasa con 0
omisiones críticas conocidas y sin degradar aciertos exactos ni cobertura por debajo de
lo medido en la PR #117; la salvedad (a) queda resuelta explícitamente — banco ampliado
que la ejercite, o retirada de la siembra — antes de declarar el criterio cumplido.

## 4. Sugerencias confirmadas

### 4.1 Qué cubre ya Sirius 0.1

Nada: no existe en Sirius 0.1 ningún flujo que proponga guardar una memoria o decisión y
pida confirmación o rechazo explícito del usuario.

Verificación directa contra `main`: los estados de una decisión son exactamente
`PROPOSED`, `APPROVED`, `SUPERSEDED` y `ARCHIVED` (`src/sirius/domain/decision.py:45-48`);
los de una memoria son exactamente `CURRENT`, `ARCHIVED` y `DELETED`
(`src/sirius/domain/memory.py:15-17`). Ninguno de los dos enumerados contiene un estado
«candidata» ni «rechazada» — ni con ese nombre ni con un equivalente en inglés —, y una
búsqueda exacta de `CANDIDATA`/`RECHAZADA` en todo el árbol de `main` no encuentra
ninguna coincidencia. El estado `PROPOSED` de una decisión es la propuesta explícita del
usuario a través de `ProposeDecisionUseCase`
(`src/sirius/application/propose_decision.py:1-10`), cuyo docstring afirma en inglés que
nada en la conversación ordinaria (`SendMessageUseCase`) invoca este caso de uso — es
decir, no es una sugerencia iniciada por Sirius, sino un guardado manual que el usuario ya
decidió hacer.

**Este documento no reproduce la frase de la orden de origen que da por existentes los
estados `CANDIDATA` y `RECHAZADA` «en el modelo de datos»**: no se ha encontrado esa
afirmación demostrada contra `main`, y el mandato de esta incidencia («lo que no quede
demostrado se dice aparte») exige señalarlo en vez de repetirlo como hecho. Es posible que
esos estados existan en la rama `evidence/adr001-spikes` (PR #117) —no leída, ver §1— o
que la orden se refiera a un estado conceptual del Producto 0.1 aún no localizado; ninguna
de las dos hipótesis se ha podido verificar en esta revisión.

### 4.2 Qué existe ya construido y medido como evidencia (PR #117, sin fusionar)

El objetivo de esta incidencia no incluye instrucciones específicas de la PR #117 para
este bloque más allá de lo ya cubierto en las secciones 2 y 3: la orden de origen no
aporta cifras propias de «sugerencias confirmadas», y este documento no inventa ninguna.

### 4.3 Qué falta por construir

El flujo entero: proponer «¿guardo esto?» tras una conversación, y que el usuario confirme
o rechace explícitamente. Si los estados que lo sostienen no existen todavía en el modelo
de datos de `main` (§4.1), construirlos forma parte de lo que falta, no un paso ya dado.

### 4.4 Criterio de comprobación

Una conversación real genera al menos una propuesta de guardado visible en la interfaz;
confirmarla la deja como memoria o decisión vigente con origen trazable (mismo patrón que
`SaveManualMemoryUseCase`/`ProposeDecisionUseCase`); rechazarla no deja ningún rastro en
el contexto ordinario; ambas rutas quedan cubiertas por prueba automática.

## 5. Conflictos asistidos

### 5.1 Qué cubre ya Sirius 0.1

El bloque B4 detecta conflictos deterministas y sustituciones
(`docs/implementation/V8_EXECUTION.md:158`). Concretamente,
`sirius.domain.precedence.evaluate_subject_precedence` compara, por asunto y proyecto
explícitos, memorias vigentes y decisiones aprobadas, y decide entre `NO_CONFLICT`,
`DECISION_PRECEDENCE` o `CONFLICT` sin elegir nunca un ganador
(`src/sirius/domain/precedence.py:123-163`). `find_subject_conflicts` evalúa con esa misma
regla todos los asuntos vigentes, pero filtra el resultado a una consulta exclusiva de los
que quedan en `CONFLICT`: descarta expresamente `NO_CONFLICT` y `DECISION_PRECEDENCE`
(`src/sirius/domain/precedence.py:166-192`). `DetectPrecedenceConflictsUseCase` expone esa
consulta de solo lectura de conflictos pendientes
(`src/sirius/application/detect_precedence_conflicts.py:28-46`), y su docstring en inglés
afirma que nunca elige un ganador, que resolver un conflicto reportado siempre pasa por los
casos de uso ya existentes que ya exigen una orden o confirmación explícita, y que nada en
`SendMessageUseCase` invoca este caso de uso tampoco, así que una conversación ordinaria
nunca lo dispara, lo resuelve ni queda bloqueada por él
(`src/sirius/application/detect_precedence_conflicts.py:10-16`).

`KnowledgeWidget` ya cablea esa consulta a una superficie de interfaz: el botón «Detectar
conflictos de precedencia» invoca `DetectPrecedenceConflictsUseCase.detect()` y presenta
cada conflicto pendiente en una lista, sin elegir nunca un ganador
(`src/sirius/presentation/knowledge_widget.py:627-669`), comportamiento cubierto por
`tests/gui/test_knowledge_widget.py:517-535` con dos memorias del mismo asunto en
conflicto.

### 5.2 Qué existe ya construido y medido como evidencia (PR #117, sin fusionar)

La orden de origen no aporta cifras propias de la PR #117 para este bloque; no se
inventa ninguna.

### 5.3 Qué falta por construir

La detección y su visualización ya existen (§5.1): `KnowledgeWidget` ya lista cada
conflicto pendiente ante el usuario. Falta ofrecer, desde ese mismo punto de la interfaz,
las acciones de resolución (corregir, archivar, aprobar/sustituir una decisión) sobre cada
conflicto listado — hoy la lista es de solo lectura y no está conectada a los casos de uso
de corrección, archivado o aprobación ya existentes; tampoco a `SendMessageUseCase`, que
sigue sin disparar ni resolver conflictos por sí solo.

### 5.4 Criterio de comprobación

Un conflicto real de asunto/proyecto detectado por `find_subject_conflicts` aparece
visible en la interfaz con las opciones de resolución existentes (corregir, archivar,
aprobar/sustituir), y resolverlo hace que una detección posterior deje de reportarlo.

## 6. Proyectos históricos consultables

### 6.1 Qué cubre ya Sirius 0.1

Sirius 0.1 mantiene un único proyecto activo con ciclo de vida versionado — activo o
completado (B3, `docs/implementation/V8_EXECUTION.md:157`;
`src/sirius/domain/project.py:10-22`). `ProjectRepository.get_project(project_id)` puede
devolver un proyecto completado por id, para «inspeccionar el historial conservado de un
proyecto cerrado» (`src/sirius/ports/project_repository.py:32-36`), pero el contrato no
declara ningún método para **listar** proyectos completados ni para consultarlos sin
conocer de antemano su id — no hay una vía para descubrirlos.

### 6.2 Qué existe ya construido y medido como evidencia (PR #117, sin fusionar)

La orden de origen no aporta cifras propias de la PR #117 para este bloque; no se
inventa ninguna.

### 6.3 Qué falta por construir

Consultar proyectos cerrados sin mezclarlos con el proyecto activo: una vía para
descubrirlos (listarlos), no solo para leer uno ya conocido, y su presentación en la
interfaz separada del proyecto vivo.

### 6.4 Criterio de comprobación

Existe una operación que devuelve todos los proyectos `COMPLETED` sin incluir el
`ACTIVE`, la interfaz los presenta en una vista distinta de la del proyecto activo, y
consultarlos nunca modifica ni contamina el estado o el contexto del proyecto vivo.

## 7. Cierre

### 7.1 Puerta de salida del Rector

`RECTOR.md` §9.1: «puede construir un paquete de contexto fiable y trazable para una
tarea externa» (`docs/evolution/RECTOR.md:146`), sostenida por la evidencia exigida en la
misma sección: «recupera información correcta a través de varias sesiones sin aumentar
ruido» (`docs/evolution/RECTOR.md:145`).

**Criterio de comprobación de la puerta** (define solo qué prueba o medida la acredita
cuando llegue el momento de construirla; no autoriza implementación — ver cabecera del
documento).

Sobre una tarea externa real, no sintética, que requiera contexto de más de una sesión de
conversación:

- Sirius ensambla un paquete de contexto para esa tarea combinando los resultados de las
  secciones 2 a 6 (búsqueda mejorada, mejor recuperación, sugerencias confirmadas,
  conflictos asistidos, proyectos históricos) que ya estén incorporados a `main`.
- El paquete recupera la información correcta guardada en sesiones anteriores a la
  actual, verificado sobre un banco de casos versionado (mismo patrón que el banco de 47
  casos de las secciones 2 y 3), sin regresión de aciertos exactos, cobertura ni omisiones
  críticas frente a la última cifra incorporada a `main` en esas secciones.
- El paquete no aumenta el ruido: los «elementos de más» (terminología de §2.2) medidos
  sobre ese mismo banco no empeoran respecto a la última cifra incorporada a `main`.
- Cada elemento del paquete es trazable a su origen —memoria, decisión o evento— por el
  mismo mecanismo que ya usan `GetMemoryOriginUseCase`/`GetDecisionOriginUseCase`
  (`src/sirius/application/memory_origin.py`, `src/sirius/application/decision_origin.py`),
  sin ningún elemento sin origen localizable.

La puerta se declara cumplida solo cuando las cuatro condiciones anteriores están
cubiertas por prueba automática o medida reproducible sobre el banco versionado, no por
inspección manual.

### 7.2 Exclusiones del Rector

`RECTOR.md` §9.1: «agentes, herramientas externas, voz y automatización»
(`docs/evolution/RECTOR.md:144`).

### 7.3 Decisiones abiertas del propietario

- **Fusionar o no la PR #117** como vía de entrada de su evidencia hacia el producto —
  hoy esa evidencia vive fuera de `main` y este documento no la da por incorporada.
- **La dependencia de Ollama** en el filtro de relevancia de búsqueda mejorada (§2.3):
  la mitad del paquete de categoría funciona sin modelo local; la otra mitad no.
- **La última omisión crítica de recuperación** (§3.3): cerrarla exigiría o un
  diccionario a medida o romper el presupuesto de latencia; queda caracterizada, no
  resuelta.
- **El origen de los estados `CANDIDATA`/`RECHAZADA`** que la orden de esta incidencia da
  por existentes en el modelo de datos (§4.1): no se han localizado en `main`; el
  propietario debe aclarar si viven en la rama de evidencia sin fusionar, si se refieren a
  un documento no localizado, o si «sugerencias confirmadas» parte de cero también en ese
  punto.
