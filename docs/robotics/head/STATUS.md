# Estado - Sirius HEAD-R1

**Estado documental:** APROBADO  
**Documento rector vigente:** v1.1  
**Fecha:** 22 de julio de 2026  
**Estado de ejecución:** INACTIVO / NO AUTORIZADO

## Vigente

- HEAD-R1 es una cabeza robótica de sobremesa de aproximadamente 35 cm con pedestal.
- Alcance funcional, estética, medidas, fases F0-F11 y presupuesto orientativo cerrados.
- Sonrisa mecánica pospuesta a R2.
- Ojos diseñados a medida desde cero.
- Presupuesto orientativo total: 900-2.500 EUR, comprado por fases.
- Plazo realista: 12-30 meses a tiempo parcial.
- Un solo frente físico principal activo a la vez.
- Interruptor de corte físico obligatorio desde F1.
- Grabación dirigida de cada sesión incorporada al método.
- Separación respecto de Sirius 0.1 y prohibición de control directo por modelos.

## No autorizado

- activar F0, F1 o cualquier otra fase;
- compras;
- fabricación o maqueta;
- montaje eléctrico;
- firmware o aplicación de control;
- repositorio independiente de la cabeza;
- integración conversacional con Sirius.

## Prioridad actual

Cerrar Sirius 0.1 sin ampliar su alcance: implementación terminada; pendiente empaquetado, pruebas manuales en Windows 11, configuración de clave real, prueba con proveedor real, recopilación de evidencias y aceptación formal.

## Próximo paso cuando se reactive

1. Autorizar expresamente una fase concreta.
2. Crear `HEAD_STATUS.md`.
3. Fijar presupuesto máximo y compras permitidas de esa fase.
4. Preparar sesión, seguridad, captura audiovisual y prueba de salida.
5. No abrir un segundo frente físico hasta cerrar o pausar formalmente el primero.

La primera fase de aprendizaje y preparación prevista es F0; F1 puede solaparse únicamente en la forma limitada descrita en el documento rector.

## HEAD-R1 es el cuerpo de Sirius — 6 de octubre de 2026

Añadido al final, sin tocar lo anterior, que es la foto aprobada del 22 de julio.

- **Qué cambia.** HEAD-R1 deja de ser un producto hermano y pasa a ser el cuerpo de Sirius
  (EV-020, §20 del Rector de evolución, ADR-232). Este documento y su Rector siguen
  mandando en mecánica, electrónica, firmware, calibración, límites y seguridad física.
- **Qué no cambia.** Sigue inactiva: ninguna fase, ninguna compra y ninguna fabricación
  autorizadas. Ningún modelo envía ángulos, pulsos ni secuencias libres a los actuadores.
- **Cuándo se reactiva.** Cuando termine la versión 0.5 del plan del robot
  (`docs/evolution/PLAN_DEL_ROBOT.md`): primero el cerebro, en el ordenador, y después la
  cabeza. Es la decisión 1 del propietario del 05-10-2026.
- **Qué se revisa al reactivarla.** R1 no llevaba cámara ni micrófonos: solo dejaba hueco
  para una cámara en un ojo y para micrófonos separados del altavoz. Con la decisión del
  propietario de que Sirius escuche y mire siempre (EV-022), las investigaciones del
  05-10 proponen una cámara gran angular fija en la frente, más fácil de procesar, y un
  array de micrófonos con cancelación de eco. Se decide con la fase que lo toque, no
  ahora.
- **La prioridad de arriba ya no vale.** Sirius 0.1 se aceptó el 10-08-2026; la prioridad
  vigente está en `docs/evolution/STATUS.md`.
