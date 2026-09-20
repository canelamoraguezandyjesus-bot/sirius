# Evidencia — la auditoría de la forma de trabajar, segunda edición

- Fecha: 2026-09-20
- Nota de arranque: `docs/audits/arranque-auditoria-forma-de-trabajo.md`
  (19-09-2026, con su adenda de muestra del 19-09 a las 23:55 UTC).
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

## Cifras, ancladas

- Árbol de `main`: `3062a31`. Diario del motor: 667 sucesos, último el 14-09
  09:24 UTC. Sesiones de Claude Code de la cuenta: 42 (15-09 y 19-09).
- Exportación de Anthropic: 38 conversaciones (12-06 a 19-09), 1 234
  mensajes, 1 482 k caracteres, 334 adjuntos; 12 dentro del alcance, 237
  mensajes, ~472 k caracteres; 5 vacías.
- Fricción medida en la 02: un fichero ausente seis rondas seguidas (23-07
  03:34 a 24-07 20:53); tres pegados vacíos seguidos (25-07 14:03–14:17).

## Lo que este trabajo no garantiza

Lo que la nota de arranque dijo que no garantizaría, y se cumplió: no es
exhaustivo (falta ChatGPT y lo local), no mide tiempo, no elige skills, no
audita la cabeza robótica, no repara nada. Las conversaciones crudas y los
índices viven en el espacio temporal de la sesión y mueren con ella; la fuente
reproducible es la exportación, que conserva el propietario.

## Decisiones

Ninguna tomada. Ocho puestas delante del propietario, en el documento.
