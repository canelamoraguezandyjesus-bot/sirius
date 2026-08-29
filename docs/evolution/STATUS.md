# Estado - Evolución post-0.1 de Sirius

**Estado documental:** APROBADO  
**Documento rector vigente:** v1.0  
**Fecha de aprobación:** 22 de julio de 2026  
**Estado de ejecución:** INACTIVO / NO AUTORIZADO, con dos excepciones vigentes. La
primera, registrada el 15 de agosto de 2026 y ampliada el 23 de agosto de 2026: la
implementación del Sirius Work Engine, estrictamente según ADR-019, ADR-020 y su plan
aprobado, con las enmiendas que ADR-082 introduce sobre el despliegue del motor y la
ubicación de su diario (decisión I4 del propietario en la incidencia #270). La segunda,
registrada el 28 de agosto de 2026: la implementación de **Sirius 0.2 — Memoria útil**,
estrictamente según la Definición de Producto
`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` v0.1 (aprobada por la
fusión de la PR #410 por el propietario el 28-08-2026) y limitada a sus cinco bloques —
búsqueda mejorada, mejor recuperación, sugerencias confirmadas, conflictos asistidos y
proyectos históricos consultables
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:52-249`) —, por orden
del propietario en la incidencia #412. El resto del roadmap post-0.1 sigue sin autorizar.

## Vigente

- Sirius es el sistema personal completo responsable ante el usuario; no es un modelo concreto ni un simple router.
- Sirius conserva identidad, memoria canónica, contexto, permisos, trazabilidad y síntesis final.
- El modelo de interacción principal es híbrido: Sirius es el interlocutor principal y puede abrir sesiones especializadas acotadas.
- Los agentes no poseen ni escriben directamente en la memoria canónica.
- Debe validarse primero la delegación a un especialista antes de activar multiagente.
- El roadmap aprobado pasa por memoria útil, habilidades y permisos, delegación supervisada, voz, percepción/automatización digital, puente de laboratorio y Sirius 1.0.
- El multiagente permanece condicionado a evidencia posterior y no es requisito obligatorio de Sirius 1.0.
- Ningún modelo puede controlar directamente actuadores, firmware activo o acciones físicas sensibles.

## No autorizado todavía

- ampliar Sirius 0.1;
- implementar el roadmap post-0.1, salvo lo que amparan expresamente las excepciones del
  Sirius Work Engine y de Sirius 0.2 — Memoria útil descritas más abajo;
- seleccionar proveedores o frameworks para agentes;
- diseñar una arquitectura técnica multiagente — con una única excepción registrada el
  15 de agosto de 2026, ampliada ese mismo día y enmendada el 23 de agosto de 2026: el
  **diseño y la implementación** del Sirius Work Engine quedan autorizados por la orden
  explícita y posterior del propietario en la incidencia #172
  (SIRIUS-WORK-ENGINE-DESIGN-001), materializada en la PR #173 (ADR-019, APROBADO) y en la
  PR #175 (ADR-020, APROBADO, con su plan de implementación), y por su decisión I4 en la
  incidencia #270 (opción A), materializada en ADR-082. La implementación queda autorizada
  **estrictamente según ADR-020 y su plan aprobado, con las enmiendas que ADR-082 introduce
  sobre el despliegue del motor y la ubicación de su diario**; fuera de ese alcance siguen
  NO autorizados: adoptar frameworks o proveedores no aprobados, cualquier multiagente
  abierto más allá de la delegación supervisada descrita en ese diseño, y el resto del
  roadmap post-0.1;
- implementar el resto del roadmap post-0.1 más allá de Sirius 0.2 — con una segunda
  excepción registrada el 28 de agosto de 2026: la **implementación** de Sirius 0.2 —
  Memoria útil queda autorizada por la orden explícita del propietario en la incidencia
  #412, estrictamente según la Definición de Producto
  `docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md` v0.1 (aprobada por
  la fusión de la PR #410 por el propietario el 28-08-2026) y **limitada a sus cinco
  bloques**: búsqueda mejorada, mejor recuperación, sugerencias confirmadas, conflictos
  asistidos y proyectos históricos consultables
  (`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:52-249`), que esa
  misma Definición declara indivisibles: los cinco, sin excepción, deben estar
  incorporados y comprobados en `main` antes de evaluar la puerta de salida del Rector
  (`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:267-275`); fuera de
  ese alcance siguen NO autorizados: incorporar a `main` la evidencia experimental de la
  PR #117, decidir sobre la dependencia de Ollama del filtro de relevancia de búsqueda
  mejorada, y el resto del roadmap post-0.1
  (`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:297-310`);
- dar permisos generales sobre el ordenador;
- activar percepción continua;
- integrar Sirius con HEAD-R1;
- permitir control directo de hardware por un modelo.

## Prioridad actual

**Sirius 0.1 está ACEPTADO y TERMINADO** por declaración del propietario del **10 de agosto de 2026**, con sus pruebas de aceptación ejecutadas sobre el paquete `Sirius-0.1.0.dev0-3432253-windows-x64` con clave y proveedor reales. La declaración, las pruebas superadas una por una y las salvedades declaradas están en `docs/implementation/V8_EXECUTION.md`.

La **definición de producto Sirius 0.2 — Memoria útil**, que era lo único que esa aceptación condicionaba, ya no está abierta: existe y está aprobada desde la fusión de la PR #410 por el propietario el 28-08-2026 (ver «Próximo paso» más abajo).

> Esta línea dijo «pendiente de aceptación formal» desde el 22 de julio hasta el
> 25 de agosto: **quince días después de que el propietario cerrara 0.1**. Se deja
> dicho porque el coste no fue documental — se planificó sobre un estado falso, y
> el propietario tuvo que corregirlo él. Un documento de estado que no se actualiza
> cuando el estado cambia es peor que no tenerlo, porque se le cree.

## Próximo paso

La **Definición de Producto Sirius 0.2 — Memoria útil** que este apartado pedía crear ya
existe y está aprobada: `docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md`
v0.1, fusionada en la PR #410 por el propietario el 28-08-2026. La regla de activación
vigente (`docs/evolution/RECTOR.md:282-290`) exige, antes de implementar por encargos
cualquiera de sus cinco bloques
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:52-249`), que **existan**
pruebas de aceptación reproducibles y que se apruebe la arquitectura técnica
correspondiente (`docs/evolution/RECTOR.md:288`) — que existan, no que se hayan ejecutado
antes de implementar. Ambas puertas ya están cumplidas. La **Arquitectura Técnica 0.2**
(`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md`) fija en su propia
cabecera que su aprobación es la fusión de la PR que la introduce
(`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:9-15`), y esa fusión ya
ocurrió: PR #418, por el propietario, el 29-08-2026 (`80611d5`). El **Plan de Pruebas de
Aceptación 0.2** (`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md`), que
operacionaliza esas pruebas de aceptación reproducibles, fija la misma regla de aprobación
(`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:9-11`) y también ya se fusionó:
PR #420, por el propietario, ese mismo día (`c2a44f8`). Ambos documentos conservan
literalmente la cabecera «Estado: PROPUESTO» — no se reescribe tras la fusión, igual que
ADR-082 (`docs/decisions/ADR-082-el-motor-corre-dentro-de-github-actions-y-su-memoria-vive-en-el-repositorio.md:3`) —,
pero la condición de aprobación que cada uno fija en su propio encabezado es la fusión ya
ocurrida, no la palabra de la cabecera. El paquete de spikes
`docs/implementation/SIRIUS_0.2_ADR001_PAQUETE_OPERATIVO_SPIKES_v1.0.md`, que solo autoriza
experimentación aislada
(`docs/implementation/SIRIUS_0.2_ADR001_PAQUETE_OPERATIVO_SPIKES_v1.0.md:4-6`), queda así
superado por estas dos aprobaciones a efectos de la regla de activación. El próximo paso es,
por tanto, ordenar al Work Engine la implementación de los cinco bloques ya autorizada por
el propietario en la incidencia #412 (ver «No autorizado todavía» arriba), aplicando las
cuatro decisiones abiertas del propietario que quedaban pendientes: fusionar o no la
evidencia experimental de la PR #117, la dependencia de Ollama del filtro de relevancia de
búsqueda mejorada, el cierre de la última omisión crítica de recuperación
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:303-305`) y el origen de
los estados `CANDIDATA`/`RECHAZADA` de sugerencias confirmadas
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:306-310`), todas
enumeradas en
`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:297-310`. Las cuatro
quedaron **resueltas por el propietario el 29 de agosto de 2026** en su sesión interactiva
— ver «Decisiones del propietario registradas el 29 de agosto de 2026» más abajo —; esa
resolución fija el contenido de cada decisión y, junto con la aprobación ya cumplida de las
dos puertas de activación citadas en este mismo párrafo, deja sin premisas pendientes el
comienzo de la implementación de los cinco bloques.

## Decisiones del propietario registradas el 29 de agosto de 2026

Fuente autorizada: sesión interactiva (`sesion-cli`), Work ID `WI-20260829-123248`. Las
seis decisiones que siguen son hechos declarados por el propietario, no autorizaciones de
implementación nuevas: ninguna de las seis abre por sí sola la puerta de activación del
Rector, que exige arquitectura técnica aprobada y pruebas de aceptación reproducibles y que
ya está cumplida, pero por la fusión de las PR #418 y #420, no por estas seis decisiones
(ver «Próximo paso» arriba). Cuando esta sección cita una cifra o un estado como evidencia de la
PR #117, se cita tal como la registra la Definición de Producto — «evidencia reportada, no
verificada» contra la rama `evidence/adr001-spikes`, que este documento tampoco lee
directamente (`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:41-47`).

**D1 — Incorporación completa de la evidencia de búsqueda mejorada y mejor recuperación.**
La evidencia de la rama `evidence/adr001-spikes` (PR #117, que permanece abierta y sin
fusionar como archivo de evidencia) se incorpora a `main` **completa** — el índice de
categoría determinista **y** el filtro de relevancia con modelo local vía Ollama —, no
mediante la fusión directa de esa PR sino mediante órdenes nuevas al Work Engine que porten
ese trabajo como código de producto con sus pruebas. Esas órdenes futuras deben respetar
los puntos de integración que la Arquitectura Técnica 0.2 §6 deja señalados sin decidir
— el índice de categoría como cuarta señal de `RankedKnowledge`
(`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:614-626`) y el filtro de
relevancia como segundo filtro en `ContextBuilder._rank_related_knowledge`, después de la
exclusión por precedencia
(`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:628-641`) — y el
presupuesto de latencia RNF-003, 300 ms P95
(`docs/decisions/ADR-008-cargar-en-lote-las-revisiones-vigentes-al-listar.md:111-117`,
`docs/implementation/V8_EXECUTION.md:44-48`), restricción que la propia Arquitectura fija
para ambos puntos
(`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:643-648`). El corpus del
banco congelado de 47 casos y sus resultados esperados
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:63-75`) se porta sin
modificarse. Esta decisión resuelve, con esta respuesta, las dos primeras de las cuatro
decisiones abiertas del propietario listadas en «Próximo paso» arriba y en
`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:299-302`: fusionar o no
la evidencia de la PR #117 (respuesta: incorporarla completa, por órdenes nuevas, no por
fusión directa) y la dependencia de Ollama del filtro de relevancia (respuesta: se adopta).

**D2 — Suelo de cobertura de PA-0.2-REC-01.** La Definición de Producto cita dos cifras de
cobertura para el paquete completo de recuperación, 63/81 y 64/81
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:74`), sin resolver cuál
corresponde al paquete activo — la precondición 3 de PA-0.2-REC-01
(`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:132-140`) y la decisión pendiente
6 de la sección 10 de ese mismo plan
(`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:405-411`) dejaban ese suelo sin
piso reproducible. El propietario registra ahora **63/81** — la menor de las dos cifras —
como suelo provisional, **hasta que la primera medición real de PA-0.2-REC-01 sobre `main`
registre la cifra medida**, momento en el que esa cifra medida sustituye a este provisional
sin necesidad de una nueva decisión del propietario.

**D3 — Última omisión crítica de recuperación (derivación léxica).** La Definición de
Producto §3.2(b) caracteriza una omisión crítica conocida por derivación léxica
(«preferencia de redacción» frente a «prefiere que redactes»), con todas las vías medidas y
descartadas hasta la fecha de ese documento
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:107-108`), y su cierre
queda listado como parte de lo que falta por construir
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:113-118`) y como
decisión abierta en §7.3
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:303-305`). El
propietario decide: se **intentará cerrar** dentro del mismo paquete de incorporación de D1.
Si no se consigue dentro de los límites de ese paquete, queda **documentada como abierta y
aplazada por decisión del propietario** — no como defecto sin diagnosticar —, y
**PA-0.2-REC-01 no se declara superada** mientras esa omisión siga abierta: el resultado
esperado de esa prueba exige explícitamente 0 omisiones críticas conocidas
(`docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md:145-157`).

**D4 — Origen de los estados `CANDIDATA`/`RECHAZADA`.** Verificado contra `main`:
`DecisionStatus` tiene exactamente `PROPOSED`, `APPROVED`, `SUPERSEDED`, `ARCHIVED`
(`src/sirius/domain/decision.py:45-48`) y `MemoryStatus` tiene exactamente `CURRENT`,
`ARCHIVED`, `DELETED` (`src/sirius/domain/memory.py:15-17`); ninguno de los dos modela
`CANDIDATA` ni `RECHAZADA`. La Definición de Producto §4.1 ya señalaba no haber localizado
esos estados en `main`
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:134-153`), y la
Arquitectura Técnica 0.2 §3.1 ya apunta en esa misma dirección, con una redacción que este
registro cita tal cual sin corregirla: «el origen de Sirius Work Engine (equipo de la sesión
del propietario) es la rama de evidencia sin fusionar, no el producto»
(`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:116-119`). El propietario
cierra ahora esa decisión abierta
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:306-310`;
`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:814-819`): esos estados
provienen del corpus del banco de la rama de evidencia, no del producto — «sugerencias
confirmadas» sigue partiendo de cero en `main` en este punto, tal como ya registraba §4.1.

**Nota — el disparador de sugerencias no se re-registra aquí.** La incidencia de origen de
esta sesión señala explícitamente que esa decisión no se repite en este registro porque ya
consta en la Arquitectura Técnica 0.2 §3.2: el propietario la resolvió en un comentario
anterior, 2026-08-29T02:24:52Z, con dos vías (disparador automático tras la conversación y
botón manual) que convergen en el mismo estado `PENDING`
(`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:132-137`), y la propia
Arquitectura la marca como «ya resuelta, no pendiente»
(`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:821-827`).

**D5 — Orden de la pieza (C) del contador de racha (ADR-101).** ADR-101, APROBADO el
28-08-2026 (`docs/decisions/ADR-101-declarar-la-precondicion-del-contador-de-siete-dias-en-vez-de-inferirla-por-caso.md:1-7`),
deja la pieza (C) —cablear el retorno del desenlace de GitHub al almacén del motor y
declarar la clase correspondiente— como «bloque propio, a la orden del propietario»
(`docs/decisions/ADR-101-declarar-la-precondicion-del-contador-de-siete-dias-en-vez-de-inferirla-por-caso.md:83-85`).
El propietario decide ahora el orden: la pieza (C) **se ordenará después de las oleadas de
construcción de Sirius 0.2** descritas en la Arquitectura Técnica 0.2 §8
(`docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md:692-696`), no antes ni en
paralelo con ellas.

**D6 — Separación de la memoria del producto y la memoria del motor.** Resuelve la
DECISIÓN 3 de `docs/implementation/DONDE_ESTAMOS_2026-08-21.md:704-707` («¿la memoria del
producto sirve también al motor, o el motor tiene la suya?»), planteada sobre la
constatación de que hoy conviven varios sitios que guardan estado, entre ellos el cuaderno
del motor y «la memoria del producto Sirius (una base de datos con 12 tablas, esa sí viva)»
(`docs/implementation/DONDE_ESTAMOS_2026-08-21.md:512-516`). El propietario decide: **la
memoria del producto y la memoria del motor permanecen separadas** — la del producto vive
en el equipo del propietario, la del motor en su diario del repositorio, cuya ubicación
técnica (rama propia, no `main`) describe ADR-083 — aprobada por la fusión de su PR #301 por
el propietario el 24-08-2026 (`bb851b8`) y cerrada por ejecución ese mismo día en la PR #304
(`a6f8e49`), que prueba por ejecución el camino de escritura a esa rama
(`docs/decisions/ADR-083-la-memoria-del-motor-vive-en-su-propia-rama-no-en-main.md:97-134`).
ADR-083 conserva literalmente la cabecera «Estado: PROPUESTO»
(`docs/decisions/ADR-083-la-memoria-del-motor-vive-en-su-propia-rama-no-en-main.md:1-9`), pero
`docs/operations/MOTOR_DE_SIRIUS.md:80-91` ya documenta esa rama como operación vigente. Se
replanteará **solo si algún día se unifican motor y producto**; hasta entonces, la objeción
que la auditoría de `DONDE_ESTAMOS_2026-08-21.md` dejó sin cerrar
(`docs/implementation/DONDE_ESTAMOS_2026-08-21.md:524-527`) queda resuelta por esta decisión
del propietario, no por evidencia de código nueva.
