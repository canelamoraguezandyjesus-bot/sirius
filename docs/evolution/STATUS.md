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

Queda por tanto **abierta la definición de producto Sirius 0.2 — Memoria útil**, que era lo único que esa aceptación condicionaba.

> Esta línea dijo «pendiente de aceptación formal» desde el 22 de julio hasta el
> 25 de agosto: **quince días después de que el propietario cerrara 0.1**. Se deja
> dicho porque el coste no fue documental — se planificó sobre un estado falso, y
> el propietario tuvo que corregirlo él. Un documento de estado que no se actualiza
> cuando el estado cambia es peor que no tenerlo, porque se le cree.

## Próximo paso

La **Definición de Producto Sirius 0.2 — Memoria útil** que este apartado pedía crear ya
existe y está aprobada: `docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md`
v0.1, fusionada en la PR #410 por el propietario el 28-08-2026. El próximo paso pasa a ser
**implementarla por encargos**, bloque a bloque según los cinco bloques de esa Definición
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:52-249`), dejando la
incorporación de la evidencia experimental de la PR #117 —y la decisión sobre la
dependencia de Ollama del filtro de relevancia— como una única decisión del propietario al
final, no repartida por partes
(`docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md:297-310`).
