# Estado - Evolución post-0.1 de Sirius

**Estado documental:** APROBADO  
**Documento rector vigente:** v1.0  
**Fecha de aprobación:** 22 de julio de 2026  
**Estado de ejecución:** INACTIVO / NO AUTORIZADO, con una única excepción registrada el
15 de agosto de 2026 y ampliada el 23 de agosto de 2026: la implementación del Sirius Work
Engine, estrictamente según ADR-019, ADR-020 y su plan aprobado, con las enmiendas que
ADR-082 introduce sobre el despliegue del motor y la ubicación de su diario (decisión I4
del propietario en la incidencia #270). El resto del roadmap post-0.1 sigue sin autorizar.

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
- implementar el roadmap post-0.1, salvo lo que ampara expresamente la excepción del
  Sirius Work Engine descrita más abajo;
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
- dar permisos generales sobre el ordenador;
- activar percepción continua;
- integrar Sirius con HEAD-R1;
- permitir control directo de hardware por un modelo.

## Prioridad actual

Implementación de Sirius 0.1 terminada. Pendiente: empaquetado, pruebas manuales en Windows 11, configuración de clave real, prueba con proveedor real, recopilación de evidencias y aceptación formal. La siguiente definición de producto se abrirá únicamente cuando 0.1 produzca la evidencia aprobada y quede aceptada.

## Próximo paso futuro

Tras la aceptación de Sirius 0.1, crear la Definición de Producto Sirius 0.2 - Memoria útil, con requisitos y pruebas propios.
