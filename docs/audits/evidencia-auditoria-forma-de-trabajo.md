# Evidencia — la auditoría de la forma de trabajar, segunda edición

- Fecha: 2026-09-20
- Nota de arranque: `docs/audits/arranque-auditoria-forma-de-trabajo.md`
  (19-09-2026, con la adenda 1 del 19-09 a las 23:55 UTC y la adenda 2 del
  20-09 a las 00:52 UTC).
- Documento: `docs/audits/AUDITORIA_FORMA_DE_TRABAJO_2026-09.md`.
- Rama: `claude/sirius-collaboration-rir6r6`.

## Lo que se afirma, y cómo se comprobó

**Afirmación 1.** Las 21 fichas de agosto tienen veredicto fechado
(2 caducadas, 11 transformadas, 8 vigentes).
*Comprobación:* para cada ficha, una lectura del árbol de `main` en `3062a31`
y de las fuentes que la tabla del documento cita: ADR y sus fechas
(`docs/decisions/`), el contrato v1.10, `docs/operations/MOTOR_DE_SIRIUS.md`,
los 24 workflows, `DESENLACES.md` de la rama `estado-del-motor` (91 encargos),
y la API de GitHub el 19-09 para las incidencias abiertas, la PR #122, la
incidencia #137 y las ejecuciones de `merge-sirius-work.yml`,
`quality-windows.yml` y `materialize-approved-docx.yml`. Regla aplicada:
«vigente» solo con ocurrencia fechada después del 11-08; «caducada» solo con lo
que la mató; «transformada» con las dos cosas. Límite: el clon de la sesión
era superficial (50 commits), así que ningún recuento salió de `git log`.

**Afirmación 2.** Conversación, ideas y debate tienen ficha (C-01, C-02,
C-03) y la revisión externa a mano (N-03) es real y tiene dos formas.
*Comprobación:* lectura entera, en orden, de las 12 conversaciones de
claude.ai de la muestra fijada en la adenda **antes** de abrirlas (237
mensajes; los del asistente hasta 2 500 caracteres), con el protocolo de cinco
campos escrito de antemano; después, contraste con la memoria de claude.ai
(nueve ficheros dentro del alcance) y las dos reflexiones mensuales. Las
frases del propietario que el documento cita están en las conversaciones
04 (24-07), 02 (25-07), 05 (10-08), 10 (04-09) y 11 (15-09); las de la
memoria de claude.ai, en `ways-of-working.md` y `preferences.md` del proyecto
«Sirius 0.2» y de la cuenta.

**Afirmación 3.** Las cinco hipótesis de la nota se confirman.
*Comprobación:* cada una tiene en el documento la conversación y la fecha que
la sostiene. Se intentó refutarlas: H2 podía ser un artefacto del motor (los
ADR llegan en lote porque el ciclo los fusiona en lote) y no del propietario;
la conversación 04 la afirma con sus palabras el 24-07, antes de que el motor
existiera, y la memoria de sesión del 14-09 la repite. H1 podía ser solo de
julio; la memoria de sesión del 12-09 muestra la segunda forma en septiembre.

**Afirmación 4.** La regla de las dos rondas se dispara y la taxonomía gana la
letra G.
*Comprobación:* la familia omitida que el paso 2 declaró (documento, «Regla de
las dos rondas, aplicada») y la que el paso 3 encuentra son la misma; el
criterio de la nota de arranque dice qué hacer entonces, y se hizo.

**Afirmación 5.** Ningún ADR cita la conversación de la que nace su decisión.
*Comprobación:* se buscaron en `docs/decisions/` los ADR que el documento
empareja con conversaciones (001, 002, 104–132, 161, 163) y ninguno menciona
claude.ai ni una conversación como origen. Es una afirmación sobre esos ADR,
no sobre los 196.

**Afirmación 6.** Las fichas C-01, C-02, C-03 y N-03 quedan revisadas con el
lado de la ejecución, y los seis hallazgos E-01…E-06 tienen fuente.
*Comprobación:* lectura, en el orden de la adenda 2, de las 13 transcripciones
de Claude Code (8 locales más `history.jsonl`, y 5 de la nube), convertidas
del `.jsonl` a texto por un guion de la sesión que conserva hora, autor,
nombre de herramienta y primera línea de su entrada; 237 mensajes del
propietario íntegros, 1 928 del asistente hasta 2 500 caracteres, 31
denegaciones o rechazos y 7 interrupciones contados por el mismo guion. Cada
frase citada tiene fecha y hora en el documento y se localiza en el fichero
de esa sesión. Los cruces con el árbol: ADR-005, 006 y 007 fechados el
10-08-2026 en `docs/decisions/`, frente a la incidencia #165 creada el 14-08 a
las 15:28 según la transcripción; los dos ADR-016, ambos fechados el
14-08-2026; ADR-032 fechado el 17-08-2026, con `scripts/siguiente_adr.py` y
`.claude/skills/adr/SKILL.md` presentes; y el caso de la «ronda interrumpida»
del 11-08, ya recogido en `docs/implementation/WORK_PROCESS_AUDIT.md`
(ficha PROC-005). Límite: 3 de las 5 transcripciones de la nube empiezan por
un resumen de compactación escrito por el modelo; lo que solo consta ahí se
cita como «según el resumen» y no sostiene ninguna afirmación por sí solo.

**Afirmación 7.** La bitácora de la auditoría forense no tiene PR.
*Comprobación:* la API de GitHub el 20-09 devuelve una sola PR abierta, la
#117; la rama de la auditoría forense existe en el remoto (`git ls-remote`).
Sus 114 entradas, sus 32 deudas y los 340 commits de retraso son cifras de la
propia sesión del 19 y 20-09, no verificadas desde este clon superficial.

**Afirmación 8.** Cada sesión local carga a la vez claude-mem y Supermemory.
*Comprobación:* solo por la transcripción: el informe de contexto que las dos
sesiones teletransportadas pegaron el 20-09 lista los dos plugins, 21 skills y
14 herramientas MCP de claude-mem. No es verificable desde aquí; el
repositorio no menciona claude-mem.

## Cifras, ancladas

- Árbol de `main`: `3062a31`. Diario del motor: 667 sucesos, último el 14-09
  09:24 UTC. Sesiones de Claude Code de la cuenta: 42 (15-09 y 19-09).
- Exportación de Anthropic: 38 conversaciones (12-06 a 19-09), 1 234
  mensajes, 1 482 k caracteres, 334 adjuntos; 12 dentro del alcance, 237
  mensajes, ~472 k caracteres; 5 vacías.
- Fricción medida en la 02: un fichero ausente seis rondas seguidas (23-07
  03:34 a 24-07 20:53); tres pegados vacíos seguidos (25-07 14:03–14:17).
- Transcripciones de Claude Code: 13 leídas (8 locales del 16-08 al 11-09 más
  `history.jsonl`; 5 de la nube: 18-07, 23-07, 10/11-08, 08–17-08, 19/20-09);
  237 mensajes del propietario, 1 928 del asistente, 31 denegaciones o
  rechazos, 7 interrupciones. En `history.jsonl`, 38 de 72 órdenes pegadas.
- Fricción medida en la ejecución: el selector de opciones rechazado 7 veces
  (5 el 10-08 entre las 20:52 y las 22:17); el mismo mapa reescrito 4 veces en
  18 minutos (10-08, 20:46–21:04); 4 promesas de «te aviso» en una sesión que
  no puede hablar entre turnos; 8 despertares horarios «sin cambios» (19-09,
  16:24–23:23).
- Sesiones paralelas: la incidencia #165 (14-08 15:28) encargó B12, cerrado
  por otra sesión el 10-08 (ADR-006, 007); dos ADR-016 fechados el 14-08.

## Lo que este trabajo no garantiza

Lo que la nota de arranque dijo que no garantizaría, y se cumplió: no es
exhaustivo (falta ChatGPT, faltan 28 de las 34 sesiones de la nube y todo lo
local anterior al 16-08), no mide tiempo, no elige skills, no audita la cabeza
robótica, no repara nada. Las conversaciones crudas, las transcripciones
convertidas a texto y los índices viven en el espacio temporal de la sesión y
mueren con ella; las fuentes reproducibles son la exportación de Anthropic y
los dos zips de sesiones, que conserva el propietario.

## Decisiones

Ninguna tomada. Diez puestas delante del propietario, en el documento, y tres
acciones para la pila del ordenador.
