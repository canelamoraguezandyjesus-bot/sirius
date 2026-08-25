# Instrucciones para agentes de programación

Este repositorio implementa Sirius 0.1. El producto y la arquitectura están aprobados.

## Antes de RESPONDER

Esta sección existe porque la de abajo empieza por «antes de modificar código», y
contestar una pregunta no es modificar código: ninguna de sus reglas se
disparaba. El 25-08-2026 el propietario tuvo que decir tres veces en una sesión
«búscalo, no me lo digas de memoria», y tenía razón las tres.

**Toda afirmación sobre qué está planeado, decidido, medido o pendiente sale de
leer este repositorio, y se dice DÓNDE se leyó.** Nunca de memoria, nunca de lo
que parezca razonable. Si no se encontró, se dice «no lo he encontrado», que es
una respuesta legítima; inventarlo no lo es.

Antes de proponer construir algo, **busca si ya existe**. En este repositorio ha
aparecido seis veces una pieza correcta a la que no llamaba nadie, y una séptima
casi se construye por duplicado el 25-08 -un «investigador del repositorio» que
ya existía con otro nombre: el auditor-.

### Dónde mirar, para que buscar sea barato

| Qué buscas | Dónde está |
|---|---|
| Qué se decidió y por qué | `docs/decisions/ADR-*.md` |
| Qué bloques del MOTOR hay y cómo van | `docs/implementation/bloques_del_motor.yml` |
| Qué defectos hay abiertos | `docs/audits/registro_defectos.yml` |
| El plan del motor, bloque a bloque | `docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md` |
| Qué reglas gobiernan la automatización | `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` |
| Qué hace cada agente | `scripts/automation/prompts/` |
| Cómo se usa el motor | `docs/operations/MOTOR_DE_SIRIUS.md` |
| Proveedores de IA, coste y local vs nube | `docs/implementation/AGENT_OPPORTUNITY_MATRIX.md` §6 y `BLOQUE_B_SUSCRIPCIONES_O_CLAVES.md` |

Dos avisos que ya han costado tiempo:

- **«Los bloques» es ambiguo.** Hay dos listas: los 16 del PRODUCTO (cerrados el
  10-08-2026) y los del MOTOR. Comparten hasta un identificador: `B1` es uno de
  cada. Di siempre de cuál hablas.
- **Un documento de estado puede estar caducado.** `STATUS.md` estuvo quince
  días diciendo que Sirius 0.1 no estaba aceptado cuando ya lo estaba. Si una
  afirmación importa, contrástala con el registro o con el historial.

## Antes de modificar código

1. Lee `docs/canonical/STATUS.md`.
2. Lee `docs/implementation/PLAN.md`.
3. Identifica la vertical activa.
4. No añadas funciones fuera de alcance.
5. Si la tarea afecta Claude Code, Routines, cloud, permisos, revisión automática, PR automáticas o cualquier flujo de agentes, lee obligatoriamente `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` y ejecuta únicamente la fase vigente descrita allí.
6. Si la tarea afecta hardware local de IA, DGX Spark o equivalente, Sirius Core, modelos open-weight, proveedores de IA, model routing, benchmarks de modelos, costes de inferencia o políticas local/nube, lee obligatoriamente `docs/evolution/SIRIUS_AI_CORE_AND_MODEL_STRATEGY.md`. Ese documento es una recolección informativa de ideas futuras: no constituye aprobación para implementarlas.

## Reglas obligatorias

- No inventes requisitos ni decisiones.
- No cambies arquitectura, modelo de datos, privacidad, costes o alcance sin registrar una propuesta y obtener aprobación.
- Mantén las dependencias hacia dentro: presentación -> aplicación -> dominio; los adaptadores implementan puertos del dominio/aplicación.
- No accedas a SQLite, OpenAI o secretos desde la interfaz.
- No guardes claves en código, SQLite, logs o archivos de texto.
- No uses el proveedor externo en pruebas normales; usa adaptadores simulados.
- Añade o actualiza pruebas con cada cambio.
- Ejecuta `scripts/check.ps1` antes de entregar.
- Haz cambios pequeños, trazables y reversibles.
- Actualiza la documentación cuando cambie el comportamiento aprobado.
- No introduzcas disparador API, eventos de GitHub, auto-fix, merge automático, coordinación de agentes ni otro nivel de automatización antes de la puerta y aprobación expresa definidas en `AUTOMATION_OPERATING_CONTRACT.md`.
- No pidas repetir una acción ya realizada. Antes de indicar el siguiente paso, verifica el estado real y la fase vigente.

## Criterio de parada

Detente y pide decisión cuando una tarea implique:

- ampliar Sirius 0.1;
- cambiar una decisión aprobada;
- enviar más datos a terceros;
- introducir otro proceso, servidor, agente o base de datos;
- ejecutar acciones externas autónomas;
- aumentar el presupuesto o reducir controles de seguridad;
- contradecir, saltar o reinterpretar el contrato operativo de automatización.
