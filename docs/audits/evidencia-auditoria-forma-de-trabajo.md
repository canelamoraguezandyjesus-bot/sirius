# Evidencia — la auditoría de la forma de trabajar, segunda edición

- Fecha: 2026-09-20
- Nota de arranque: `docs/audits/arranque-auditoria-forma-de-trabajo.md`
  (19-09-2026, con la adenda 1 del 19-09 a las 23:55 UTC, la adenda 2 del
  20-09 a las 00:52 UTC, y las adendas 4 y 5 del 20-09 a las 23:05 y las 23:27
  UTC).
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

**Afirmación 9.** Las fichas C-01…C-03 y N-03 y los hallazgos E-01…E-06
quedan revisados con 28 transcripciones más de la nube (paso 5), y los ocho
hallazgos T-01…T-08 tienen fecha y hora.
*Comprobación:* lectura, en el orden de las adendas 4 y 5 (escritas antes de
abrir ningún fichero), de 28 transcripciones traídas de las ramas
`transcripciones/<id>` que cada sesión empujó el 20-09 entre las 18:15 y las
23:18 UTC (`git for-each-ref refs/remotes/origin/transcripciones/`: 30 ramas;
tres sesiones más no la empujaron). Extractos por el mismo guion del paso 4;
cifras de la clasificación previa a la lectura: 32 769 registros, 7 532
entradas con rol de usuario, 12 273 del asistente, 107 MB. La separación
«entradas de usuario / texto suyo» la hizo un segundo guion, por heurística
(notificaciones, stop-hook, expansiones de skills, resúmenes de compactación,
comandos locales, interrupciones, pegados de terminal), y es aproximada: 873
entradas con texto, 358 suyas o pegadas por él. Cada cita del paso 5 lleva fecha
y hora y se localiza en el `.jsonl` de la sesión nombrada. Límite: las citas
tomadas de resúmenes de compactación (14-08; 13-09) se marcan «según el
resumen» y no sostienen nada por sí solas.

**Afirmación 10.** La cuarta pregunta colgada (27-07) sí se contestó.
*Comprobación:* la transcripción de «Auditoría Registro de Tolerancias v0.3»
termina con la respuesta del asistente a las 17:29 UTC del 27-07; la de
«ADR-001 spike 7 y revisión de cierre» empieza a las 17:41 con 488 líneas
pegadas por el propietario; la de «TOL-207 caracterización almacenamiento v0.2»
abre a las 18:01 con el paquete 04, que dice materializar «dos revisiones
forenses y una auditoría adversarial». `git grep` de las tres categorías sobre
el árbol rastreado de `main`: cero resultados fuera de
`docs/audits/las-sesiones-de-la-nube-2026-09.md`.

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
- Paso 5: 30 ramas `transcripciones/*` (18:15–23:18 UTC del 20-09); 28
  leídas; 32 769 registros; 7 532 entradas de usuario, 873 con texto, 358
  suyas; sesión del 08-09: 131 notificaciones de GitHub, 95 despertares, 142
  entradas con texto suyo, 7 días; PR #576: 4 rondas externas el 08-09 (14:05,
  15:51, 19:31, 21:38); vuelta del correo: 2 minutos (19-08, 00:03 → 00:05);
  regla dicha → regla escrita: 41 días (ADR-204), 8 (ADR-205), 0 (ADR-191), 6
  (ADR-206).

## Lo que este trabajo no garantiza

Lo que la nota de arranque dijo que no garantizaría, y se cumplió: no es
exhaustivo (falta ChatGPT; faltan 3 de las 33 sesiones de la nube con historia
—dos del 18-07 que empujaron tarde y se borraron sin leer, y «No hagas nada»—;
y todo lo local anterior al 16-08), no mide tiempo, no elige skills, no audita la cabeza
robótica, no repara nada. Las conversaciones crudas, las transcripciones
convertidas a texto y los índices viven en el espacio temporal de la sesión y
mueren con ella; las fuentes reproducibles son la exportación de Anthropic y
los dos zips de sesiones, que conserva el propietario.

## Decisiones

Las diez que se le pusieron delante las decidió él el 20-09 (ADR-204 a 211).
El paso 5 toma una, técnica, y la deja en ADR-213: tres reglas de conversación
más en `AGENTS.md`, con guarda, y la proporción de la cadena de comprobación.
