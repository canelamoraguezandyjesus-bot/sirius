# SIRIUS - Contrato operativo de automatización

**Versión:** 1.1  
**Fecha:** 19 de julio de 2026  
**Estado:** VIGENTE  
**Autoridad:** Operativa para el desarrollo automatizado de Sirius 0.1  
**Sustituye:** versión 1.0 del 18 de julio de 2026  
**No modifica:** Producto, Arquitectura Técnica, ATD, requisitos ni alcance de Sirius 0.1

## 0. Propósito

Este contrato autoriza y regula un flujo permanente de automatización para Sirius 0.1 mediante Claude Code, Routines, GitHub, ChatGPT con conectores, tareas programadas y futuras aplicaciones de control. Su finalidad es que el usuario pueda iniciar trabajo mediante una instrucción breve y recibir una PR trazable, validada y revisada sin repetir autorizaciones administrativas por cada subbloque.

La automatización no convierte a los agentes en autoridad de producto ni permite cambios fuera del alcance aprobado.

## 1. Decisión operativa vigente

Desde el 19 de julio de 2026 queda autorizada de forma general, para todo Sirius 0.1, la automatización secuencial de implementación y revisión de PR.

Esta autorización cubre B4d, B4e, B4f y las verticales posteriores de Sirius 0.1, siempre que cada tarea:

- pertenezca al alcance ya aprobado;
- tenga objetivo y límites verificables;
- trabaje en una rama propia;
- prepare una PR propia;
- mantenga la suite completa en verde;
- no modifique documentos canónicos, Producto, Arquitectura Técnica o ATD salvo instrucción explícita;
- no haga merge automáticamente.

No se requiere una nueva modificación de este contrato ni una nueva autorización administrativa para activar la revisión de cada PR.

## 2. Flujo permanente autorizado

### 2.1 Inicio

El trabajo puede iniciarse mediante cualquiera de estos mecanismos:

- una instrucción directa del usuario en ChatGPT;
- una Routine de Claude Code;
- una tarea programada de ChatGPT;
- una incidencia o etiqueta de GitHub;
- una aplicación o interfaz futura conectada a GitHub o ChatGPT.

El mecanismo de entrada debe identificar la tarea o permitir resolverla inequívocamente desde el estado vigente del repositorio.

### 2.2 Implementación

El agente implementador puede:

- crear o utilizar una rama de trabajo;
- modificar código, pruebas y documentación de implementación dentro del alcance autorizado;
- ejecutar Ruff, mypy, pytest, comprobaciones de migraciones y otras validaciones ya existentes;
- realizar commits y push en la rama de trabajo;
- crear o actualizar una PR;
- marcarla lista para revisión cuando el trabajo esté terminado y CI esté en verde.

Debe detenerse con uno de estos estados:

- `READY_FOR_REVIEW`
- `BLOCKED_BY_DECISION`
- `FAILED_SAFELY`
- `USAGE_LIMIT_REACHED`

### 2.3 Revisión automática

Cuando una PR esté lista y su CI obligatorio esté en verde, queda autorizado activar automáticamente la Routine revisora mediante una incidencia etiquetada `agent-review-requested` o mediante otro disparador equivalente aprobado técnicamente.

La autorización es permanente para Sirius 0.1 y no depende del nombre del subbloque ni exige una entrada adicional en este contrato.

La revisión debe ser independiente de la implementación y puede:

- inspeccionar diff, código, pruebas, migraciones y documentación operativa;
- comprobar el alcance contra las fuentes aprobadas;
- publicar observaciones o un veredicto;
- devolver `REVIEW_APPROVED`, `CHANGES_REQUESTED`, `BLOCKED_BY_DECISION` o `FAILED_SAFELY`.

La Routine revisora no debe bloquearse por ausencia de una autorización específica por PR, porque esta sección constituye la autorización general vigente.

### 2.4 Corrección tras revisión

Cuando el revisor solicite cambios técnicos concretos, queda autorizado un ciclo automático de corrección limitado a la misma rama y PR.

Puede corregir:

- defectos de implementación;
- pruebas insuficientes;
- lint, formato, tipos e imports;
- errores deterministas de CI;
- migraciones aditivas o reversibles dentro del diseño aprobado;
- incumplimientos claros de requisitos ya aprobados.

Debe detenerse y pedir decisión cuando el cambio afecte a:

- alcance de producto;
- arquitectura aprobada;
- ATD o contratos públicos no previstos;
- seguridad con consecuencias no definidas;
- migraciones destructivas o pérdida de datos;
- costes o servicios externos nuevos;
- credenciales reales o datos personales.

Se permiten como máximo dos ciclos automáticos de revisión-corrección. Si no converge, el resultado será `BLOCKED_BY_DECISION`.

### 2.5 Merge

El merge permanece bajo control humano.

Ningún agente, Routine, tarea programada o aplicación puede fusionar una PR sin una autorización explícita del usuario para ese merge, salvo que el usuario apruebe posteriormente una política distinta mediante una nueva decisión registrada.

## 3. Reglas permanentes de seguridad

Está prohibido:

- hacer push directo a `main`;
- reducir, eliminar o falsear pruebas para conseguir verde;
- ocultar fallos o afirmar que una validación pasó sin evidencia;
- introducir servicios de pago, APIs, claves o suscripciones no aprobadas;
- usar secretos reales o datos personales en pruebas automáticas;
- cambiar Producto, Arquitectura Técnica, ATD o documentos canónicos sin decisión explícita;
- iniciar trabajo paralelo sobre componentes que compartan migraciones o contratos cuando exista riesgo de conflicto;
- ejecutar merge automático;
- interpretar una idea exploratoria como decisión aprobada.

## 4. Automatizaciones futuras autorizadas como línea de trabajo

Queda autorizada la exploración, diseño y puesta en marcha gradual de nuevas automatizaciones para reducir intervención manual, incluyendo:

- tareas programadas de ChatGPT para comprobaciones, resúmenes y avisos;
- Routines de Claude Code para implementación, revisión y corrección;
- disparadores mediante incidencias, etiquetas, comentarios o estados de GitHub;
- aplicaciones ligeras desde las que el usuario pueda enviar una instrucción y crear automáticamente una tarea, incidencia, rama o PR;
- flujos que conviertan un mensaje del usuario en una solicitud trazable dentro del repositorio;
- paneles de estado y notificaciones.

Cada nueva automatización puede desarrollarse sin reautorizar su mera investigación o prototipo. Antes de otorgarle permisos destructivos, acceso a secretos, gasto externo, merge o cambios canónicos, deberá existir una decisión explícita separada.

## 5. Criterios para activar nuevas automatizaciones

Una automatización nueva puede pasar de experimento a uso operativo cuando:

1. su objetivo y permisos están delimitados;
2. puede fallar de forma segura;
3. deja trazabilidad suficiente;
4. no cambia alcance de producto;
5. no introduce gasto o servicios no aprobados;
6. conserva el merge bajo control humano;
7. ha sido probada al menos una vez en un caso acotado.

No es necesario modificar este contrato para cada nueva Routine, tarea programada o interfaz que cumpla estas condiciones.

## 6. Estado operativo actual

- B4a, B4b y B4c están fusionados en `main`.
- B4d está implementado en la PR #41, con CI verde y 830 pruebas.
- La revisión automática de B4d queda autorizada por este contrato v1.1.
- La incidencia #43 puede reutilizarse para reactivar la revisión después de que esta versión esté presente en la rama de la PR.
- B4e y B4f no deben comenzar hasta cerrar B4d mediante revisión aprobada y merge autorizado por el usuario.

## 7. Gestión de cambios

Este contrato solo cambia mediante una decisión explícita del usuario. Las modificaciones futuras deben indicar fecha, decisión, motivo y alcance.

El historial anterior permanece disponible en Git y no se reescribe retrospectivamente.

## 8. Cambio registrado el 19 de julio de 2026

- **Decisión:** sustituir las autorizaciones puntuales por subbloque por una autorización general de implementación y revisión automática para todo Sirius 0.1.
- **Motivo:** evitar bloqueos administrativos repetidos y permitir un flujo realmente automatizado.
- **Sustituye:** las restricciones de la versión 1.0 que exigían una excepción específica para B4b, B4c y cada PR posterior.
- **Mantiene:** alcance aprobado, revisión independiente, máximo de dos ciclos, prohibición de push a `main`, prohibición de cambios canónicos no autorizados y merge bajo control humano.
- **Autoriza además:** explorar y construir nuevas automatizaciones con Routines, tareas programadas de ChatGPT, eventos de GitHub y aplicaciones de control, dentro de los límites de este contrato.
