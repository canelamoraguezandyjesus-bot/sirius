# Instrucciones para agentes de programación

Este repositorio implementa Sirius 0.1. El producto y la arquitectura están aprobados.

## Antes de RESPONDER

Esta sección existe porque la de abajo empieza por «antes de modificar código», y
contestar una pregunta no es modificar código: ninguna de sus reglas se
disparaba. El 25-08-2026 el propietario tuvo que decir tres veces en una sesión
«búscalo, no me lo digas de memoria», y tenía razón las tres.

**Toda afirmación sobre qué está planeado, decidido, medido o pendiente sale de
leer este repositorio —empezando por `MEMORIA.md`, en la raíz, entera— y se
dice DÓNDE se leyó.** Nunca de memoria ni de lo que parezca razonable. Si no se
encontró, se dice «no lo he encontrado», que es legítimo; inventarlo no lo es.

Antes de proponer construir algo, **busca si ya existe**. En este repositorio ha
aparecido **ocho veces** una pieza correcta a la que no llamaba nadie -la octava,
el 12-09-2026: el campo `cerrada` del espejo, que se calculaba en cada pasada y
no leía nadie (ADR-173)-, y una novena casi se construye por duplicado el 25-08
-un «investigador del repositorio» que ya existía con otro nombre: el auditor-.

Este párrafo llevaba diciendo «seis veces» desde agosto porque el número lo
lleva una persona a mano. Desde ADR-174 la cuenta de cuántas veces ha mordido
cada familia la lleva la máquina: **«Las lecciones, por familia» en
`MEMORIA.md`**, generada de los propios ADR.

### Dónde mirar, para que buscar sea barato

| Qué buscas | Dónde está |
|---|---|
| Por dónde empezar, siempre; qué se decidió y por qué | `MEMORIA.md` (raíz), generada: cada ADR con su resumen, los registros con estado y los documentos con su fecha; los desenlaces del motor, en `estado-del-motor:DESENLACES.md` (ADR-171) |
| Qué quedó pendiente y el contexto de sesiones anteriores | la memoria de sesión, si tu entorno trae su herramienta (ADR-172) |
| Qué error se repetiría si no se supiera, y cuántas veces ha mordido ya | «Las lecciones, por familia», en `MEMORIA.md` (ADR-174) |
| Qué bloques del MOTOR hay y cómo van | `docs/implementation/bloques_del_motor.yml` |
| Qué defectos hay abiertos | `docs/audits/registro_defectos.yml` |
| El plan del motor, bloque a bloque | `docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md` |
| Qué reglas gobiernan la automatización | `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` |
| Qué hace cada agente | `scripts/automation/prompts/` |
| Cómo se usa el motor | `docs/operations/MOTOR_DE_SIRIUS.md` |
| Proveedores de IA, coste y local vs nube | `docs/implementation/AGENT_OPPORTUNITY_MATRIX.md` §6 y `BLOQUE_B_SUSCRIPCIONES_O_CLAVES.md` |
| La memoria del motor: diario, despachos y racha | la rama **`estado-del-motor`**, nunca `main` (ADR-083, ADR-093) |
| Las investigaciones que informaron una decisión | `docs/investigaciones/` — **con su fecha y de qué dependen para caducar** |
| Qué modelo de IA funciona HOY | `scripts/investigacion/modelos_atestiguados.yml`, que escribe una máquina tras llamar (ADR-095) |

Cuatro avisos que ya han costado tiempo:

- **«Los bloques» es ambiguo.** Hay dos listas: los 16 del PRODUCTO (cerrados el
  10-08-2026) y los del MOTOR. Comparten hasta un identificador: `B1` es uno de
  cada. Di siempre de cuál hablas.
- **Un documento de estado puede estar caducado.** `STATUS.md` estuvo quince
  días diciendo que Sirius 0.1 no estaba aceptado cuando ya lo estaba. Si una
  afirmación importa, contrástala con el registro o con el historial.
- **Una investigación NO es una fuente sobre algo vivo.** Es una foto con fecha.
  La del 27-08-2026 caducó **en veinticuatro horas**: tres de los modelos que
  recomendaba no existían ya. Sirve para decidir qué preguntar, nunca para
  responder — lo que responde es el servidor (ADR-095).
- **El fichero `docs/operations/racha_siete_dias.jsonl` de `main` está vacío
  a propósito y siempre lo estará.** El registro de verdad de la racha vive en
  la rama `estado-del-motor` (ADR-093). Mirar el de `main` y concluir «el
  contador no ha corrido nunca» sería exactamente el error del aviso anterior.

## Antes de modificar código

1. Lee `MEMORIA.md` entera; después `docs/canonical/STATUS.md`.
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
- **Todo ADR desde el 174 declara su lección** en un bloque `## La lección`: la
  familia del fallo, qué se repetiría sin él y qué prueba lo hace cumplir -o
  `ninguna: <razón>` si no dejó ninguna, que también es una respuesta. Lo
  comprueba `tests/automation/test_mina_de_lecciones.py`, y de ahí sale la
  cuenta por familia de `MEMORIA.md` (ADR-174). El criterio es el de Compound
  Engineering: se escribe una lección **solo si sin ella alguien repetiría el
  error**.
- Ejecuta `scripts/check.ps1` antes de entregar.
- Haz cambios pequeños, trazables y reversibles.
- Actualiza la documentación cuando cambie el comportamiento aprobado.
- No introduzcas disparador API, eventos de GitHub, auto-fix, merge automático, coordinación de agentes ni otro nivel de automatización antes de la puerta y aprobación expresa definidas en `AUTOMATION_OPERATING_CONTRACT.md`.
- No pidas repetir una acción ya realizada. Antes de indicar el siguiente paso, verifica el estado real y la fase vigente.

## Política de revisión (revisores automáticos)

- Una revisión es una pasada EXHAUSTIVA: reporta en esta ronda TODOS los
  hallazgos que el diff contiene; no guardes ninguno para una ronda futura.
- En rondas posteriores a la primera, cada hallazgo nuevo debe nacer del
  código introducido por la corrección anterior o ser una regresión suya; un
  hallazgo sobre líneas ya idénticas en la ronda previa se reporta igualmente,
  declarando que llega tarde por goteo del revisor.

## La memoria común: `MEMORIA.md` (ADR-171)

`MEMORIA.md`, en la raíz, es la memoria común del trabajo, **generada** a partir
del árbol: qué se decidió (cada ADR con su resumen), qué registros hay y en qué
estado, qué documentos existen y de cuándo, y dónde están los desenlaces del
motor. Es lo primero que se lee, antes de responder y antes de modificar; desde
ahí, solo lo que la tarea necesite.

- **No se edita a mano.** Se regenera con `uv run sirius-memoria conocimiento`,
  y `tests/engine/test_memoria.py` (en Quality) falla si el fichero confirmado no
  coincide con lo generado.
- **Si cambias un ADR, un documento de `docs/` o un registro YAML, regenérala y
  confírmala en la misma PR.**
- **Quality comprueba el commit de fusión con `main`.** Si `main` ganó un ADR o un
  documento después de abrir tu rama, tu PR sale en rojo aunque tu rama esté al
  día: trae `main`, regenera, confirma. Un conflicto en `MEMORIA.md` se resuelve
  siempre regenerando, nunca a mano.

## La memoria de sesión, si tienes su herramienta (ADR-172)

Hay un segundo sitio, y **solo existe si tu entorno trae la herramienta de
Supermemory**. Si no la tienes —es el caso de los agentes del ciclo, en GitHub
Actions—, esta sección no te aplica: sigue como siempre.

Guarda lo que el repositorio no guarda: **lo pendiente, el contexto de una
sesión, las preferencias de trabajo del propietario y lo que se intentó y no
salió.** Dos momentos:

- **Al empezar** algo que pueda tener antecedentes, búscalo ahí antes de
  preguntarle al propietario lo que ya te dijo una vez.
- **Al terminar**, guarda lo que quede pendiente y lo aprendido que no vaya a un
  fichero. Concreto y con fecha; una memoria vaga no le sirve a nadie.

### El espacio canónico, que hay que nombrar SIEMPRE

El espacio de este proyecto es **`repo_sirius__e87a5bbe75fe00b6`**. Pásalo como
`containerTag` en **cada** búsqueda y en **cada** guardado, sin excepción.

No basta con buscar y guardar: si no nombras el espacio, cada herramienta usa el
suyo por omisión y acabáis escribiendo en sitios distintos. El 11-09-2026 pasó
exactamente eso, medido: la captura automática del complemento local fue al
espacio del repositorio y todo lo escrito por MCP —desde la nube, desde
ChatGPT— al espacio por defecto de la cuenta. Dos memorias paralelas que no se
veían la una a la otra.

Si ese espacio no aparece al listar los espacios disponibles, no inventes otro
ni escribas en el que salga: **dilo y para**. El nombre lo deriva el complemento
del remoto de git, así que cambia si el repositorio se renombra, y entonces esta
línea hay que corregirla aquí.

Y el reparto, que es la regla entera:

| Qué | Dónde |
|---|---|
| Lo decidido, investigado, medido o acordado | **El repositorio**, con su PR, su ADR y su prueba |
| Lo pendiente, el contexto de sesión, las preferencias | **La memoria de sesión** |
| El estado de un trabajo del motor | **Su diario**, que manda sobre las dos |

**Una decisión que solo está en la memoria de sesión no está tomada.** Si no
llegó a una PR fusionada, no existe.

**Lo que se guarda ahí sale a un servicio de terceros**, y una sesión contiene
más que este repositorio público. El propietario lo sabe y lo acepta; aun así,
ahí no van claves ni secretos, nunca.

## Criterio de parada

Detente y pide decisión cuando una tarea implique:

- ampliar Sirius 0.1;
- cambiar una decisión aprobada;
- enviar más datos a terceros;
- introducir otro proceso, servidor, agente o base de datos;
- ejecutar acciones externas autónomas;
- aumentar el presupuesto o reducir controles de seguridad;
- contradecir, saltar o reinterpretar el contrato operativo de automatización.
