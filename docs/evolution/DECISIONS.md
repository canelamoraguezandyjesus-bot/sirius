# Decisiones canónicas - Evolución post-0.1 de Sirius

**Estado:** APROBADO  
**Fecha de aprobación:** 22 de julio de 2026  
**Autoridad final:** usuario responsable del Proyecto Sirius

## EV-001 - Sirius es el sistema personal completo

> **PRECISADA por EV-015** (8 de septiembre de 2026, ADR-160): sigue vigente
> entera; EV-015 dice de qué es compañero, no cambia su fondo.

Sirius es la identidad y el sistema personal responsable ante el usuario. No es un modelo concreto, una secretaria pasiva, un lanzador de aplicaciones ni solo el subsistema de orquestación.

## EV-002 - Sirius es el interlocutor principal

> **SUSTITUIDA por EV-016** (8 de septiembre de 2026, ADR-160). El texto original
> se conserva íntegro porque un registro de decisiones no se reescribe: se
> continúa.

El usuario se relacionará principalmente con Sirius. Sirius conservará criterio, memoria, permisos, seguimiento y responsabilidad sobre el resultado aunque delegue trabajo especializado.

## EV-003 - Modelo de interacción híbrido

> **ACOTADA por EV-016 y EV-019** (8 de septiembre de 2026, ADR-160): la sesión
> especializada sigue siendo una capacidad de Sirius, pero deja de ser el camino
> por el que llega el trabajo del propietario.

Sirius podrá abrir sesiones especializadas visibles y acotadas en las que el usuario dialogue temporalmente con un especialista. Sirius preparará el contexto, conservará permisos y trazabilidad, y recuperará e integrará el resultado.

## EV-004 - Memoria canónica exclusiva de Sirius

> **VIGENTE, SIN ENMIENDA.** EV-018 (8 de septiembre de 2026, ADR-160) crea una
> categoría distinta —el conocimiento común del trabajo y los proyectos— que
> **no es** la memoria canónica de Sirius. Lo que esta decisión protege sigue
> protegido.

Los agentes y herramientas podrán producir resultados y candidatos a recuerdo o decisión, pero no poseerán ni modificarán directamente la memoria canónica. Todo cambio conservará origen y seguirá las reglas de confirmación, versionado y conflicto.

## EV-005 - Taxonomía obligatoria

Se distinguirán siempre estas categorías: Sirius, subsistemas internos, roles de agente, modelos/proveedores, herramientas, automatizaciones, protocolos de integración, controladores físicos y productos físicos.

## EV-006 - Delegación individual antes de multiagente

Antes de coordinar varios agentes, Sirius deberá demostrar que puede formular, limitar, supervisar y cerrar una tarea delegada a un solo especialista sin perder identidad, contexto, permisos ni trazabilidad.

## EV-007 - Multiagente condicionado a evidencia

El multiagente permanece pospuesto. Solo se activará cuando una tarea real demuestre necesidad de competencias separadas, revisión independiente, paralelismo útil o fallos recurrentes del especialista único.

## EV-008 - Roadmap post-0.1 sustituido

El roadmap orientativo aprobado queda:

1. Sirius 0.2 - Memoria útil.
2. Sirius 0.3 - Habilidades y permisos.
3. Sirius 0.4 - Delegación supervisada.
4. Sirius 0.5 - Voz.
5. Sirius 0.6 - Percepción y automatización digital.
6. Sirius 0.7 - Puente de laboratorio y dispositivos.
7. Sirius 1.0 - Compañero en la habitación.

Esta decisión sustituye la secuencia anterior que agrupaba voz en 0.4 y laboratorio completo en 0.5.

## EV-009 - Percepción explícita y temporal

La percepción visual o ambiental será bajo demanda, temporal, visible y cancelable. No habrá observación silenciosa ni grabación continua como comportamiento ordinario.

## EV-010 - Control visual del ordenador como último recurso

Sirius preferirá integraciones estructuradas y contratos de herramienta. El control visual de interfaces se utilizará únicamente cuando no exista una vía más segura y deberá operar con límites, confirmación y trazabilidad.

## EV-011 - Participación supervisada en su propio desarrollo

Sirius podrá preparar cambios, coordinar agentes de programación, ejecutar verificaciones autorizadas y colaborar con firmware o hardware. No podrá aprobar por sí mismo sus cambios ni concentrar simultáneamente autoría, revisión, aprobación y ejecución final.

## EV-012 - Prohibición de control físico directo por modelos

Ningún modelo conversacional enviará órdenes libres a actuadores o firmware activo. Todo control físico pasará por permisos, intenciones de alto nivel, controladores deterministas, límites, estado seguro y parada física.

## EV-013 - Referencias externas no son módulos

Aplicaciones y productos observados se conservarán como referencias de experiencia, proveedores, protocolos, motores o patrones. No se convertirán automáticamente en módulos o requisitos de Sirius.

## EV-014 - Reclasificación de la propuesta inicial

`PROPUESTA_ALCANCE_POST_0_1_v2.md` queda como referencia histórica de ideas y productos considerados. No posee autoridad normativa ni define el roadmap.

## Efecto de aprobación

Estas decisiones no amplían Sirius 0.1 ni autorizan implementación post-0.1. Su función es gobernar las futuras definiciones de producto.

---

## Separación entre Sirius y su motor de trabajo — decisiones EV-015 a EV-019

**Estado:** decisiones canónicas de la serie EV
**Fecha:** 8 de septiembre de 2026
**Aprobación:** la fusión de la Pull Request que las introduce, por el
propietario — la misma regla que fijan la Definición de Producto 0.2, la
Arquitectura Técnica 0.2 y el Plan de Pruebas 0.2 en sus propias cabeceras.
**Relación con las decisiones anteriores:** **EV-015 precisa EV-001, EV-016 sustituye EV-002 y acota EV-003, y EV-004 se
mantiene vigente sin enmienda.**
**Entrada en vigor:** la fusión de la Pull Request que las introduce, por el
propietario, conforme al procedimiento establecido en este repositorio.
**Aprobación documental y retirada técnica son cosas distintas:** esa fusión
aprueba estas decisiones y **no** desactiva ningún carril; la retirada de los
de investigación y auditoría (ADR-161) es un acto posterior.
**Autoridad final:** usuario responsable del Proyecto Sirius
**Registro de la decisión:** `docs/decisions/ADR-160-formalizar-la-separacion-entre-sirius-y-su-motor-sirius-es-el-companero-el-motor-ejecuta-y-las-ias-externas-son-el-lugar-de-trabajo.md`
y `docs/decisions/ADR-161-retirar-los-carriles-dedicados-de-investigacion-y-auditoria-conservando-los-revisores-del-ciclo-decision-tomada-ejecucion-pendiente.md`

> Estas cinco decisiones se añaden **al final** y no se intercalan entre las
> anteriores. EV-001 a EV-014 conservan su numeración, su texto y su fecha; las
> que quedan sustituidas o acotadas lo llevan escrito en su propio apartado, con
> el número de la que las sustituye. Un registro de decisiones no se reescribe.

### EV-015 - Sirius es el compañero personal, de ingeniería y del robot

Sirius conserva identidad, memoria propia, conversación, voz, cámaras y
percepción, ayuda de ingeniería y electrónica, y manejo del ordenador y de los
dispositivos autorizados. Conserva también la ayuda directa de ingeniería con
herramientas propias, los avisos sobre el estado de los trabajos y la
posibilidad de consultar a un especialista.

Precisa el alcance de EV-001 sin cambiar su fondo: Sirius sigue siendo el
sistema personal responsable ante el usuario, y no es un modelo concreto, una
secretaria pasiva ni un lanzador de aplicaciones.

### EV-016 - El trabajo habitual se realiza directamente con las IAs externas

El propietario conversa, encarga y decide desde ChatGPT, Claude o Codex sin que
Sirius intermedie. Sirius deja de ser el interlocutor obligatorio y la síntesis
final deja de ser obligatoria; sigue siendo el compañero personal y de
ingeniería, y puede integrar o sintetizar cuando se le pide.

**Sustituye a EV-002** y **acota EV-003**.

### EV-017 - El motor de trabajo conserva su responsabilidad, y solo esa

El motor conserva ejecución de encargos, documentación, comprobaciones,
revisión, corrección, recuperación y diario operativo. No adquiere ninguna
responsabilidad nueva: no conversa, no posee la identidad de Sirius, no decide
producto ni arquitectura, y no fusiona.

### EV-018 - Tres memorias con dueño distinto, y la común no es la canónica

Se distinguen tres responsabilidades de memoria, que **no obligan a tres bases
de datos**:

1. **La memoria propia de Sirius**, del producto, en el equipo del propietario.
2. **El estado y el diario operativo del motor**, en su propia rama.
3. **El conocimiento común del trabajo y de los proyectos** — documentos,
   investigaciones, decisiones, aprendizajes y continuidad entre proyectos—,
   que las IAs mantienen y que debe estar disponible con el ordenador del
   propietario apagado.

Regla común: cada dato tiene un dueño, y quien no es dueño **cita en vez de
copiar**; una copia va marcada como espejo no autoritativo.

El conocimiento común **no es la memoria canónica de Sirius**, así que **EV-004
sigue vigente sin enmienda**: ningún agente posee ni escribe directamente la
memoria canónica.

Esta decisión **no elige herramienta, ubicación ni formato**, no asigna etapa del
roadmap y no fija ninguna relación con Sirius 0.2.

### EV-019 - Sirius conserva la delegación especializada de ingeniería

Sirius puede delegar en un especialista una **consulta de ingeniería del
propietario** y devolver el resultado a la conversación. Es distinto de un
encargo del motor en tres rasgos: nace de una conversación y no de un WorkItem,
no produce Pull Request ni pasa por el ciclo de revisión y corrección, y su
resultado vuelve a la conversación y no al diario operativo.

Se registra expresamente para que la redefinición de la etapa 0.4 no la borre
por omisión al constatar que la delegación de *encargos de trabajo* ya la hace
el motor.

### Efecto de aprobación de EV-015 a EV-019

No autorizan implementación de nada, no cambian prioridades, alcance ni
numeración de ninguna versión, y no relajan la regla de activación del Rector
(`docs/evolution/RECTOR.md` §17). Gobiernan las futuras definiciones de producto,
igual que EV-001 a EV-014.
