# Memoria común del proyecto Sirius

> **Generado por `uv run sirius-memoria conocimiento` a partir del árbol del repositorio.**
> No se edita a mano: `tests/engine/test_memoria.py` falla si este fichero no
> coincide con lo que el generador produce. Si cambias un ADR, un documento de
> `docs/` o un registro, vuelve a ejecutar el comando y confirma el resultado en
> la misma PR (ADR-171).

## Cómo se usa

- **Léela entera antes de abrir nada más.** Es la memoria del trabajo: qué se
  decidió, qué registros hay y en qué estado, qué documentos existen y de
  cuándo. Desde aquí, abre solo lo que la tarea necesite.
- **Los desenlaces del motor** —qué se encargó, qué salió, dónde está la
  evidencia— están en la rama `estado-del-motor`, fichero `DESENLACES.md`
  (https://github.com/canelamoraguezandyjesus-bot/sirius/blob/estado-del-motor/DESENLACES.md), que el motor escribe solo tras cada reflejo. Se leen con
  `git fetch origin estado-del-motor && git show origin/estado-del-motor:DESENLACES.md`.
- **Regla de conflicto (ADR-171).** Si el diario del motor y un documento
  discrepan sobre un trabajo, manda el diario. Si dos documentos discrepan
  entre sí, manda el más reciente fusionado en `main`.
- **Qué no se puede hacer** está en `AGENTS.md` («Reglas obligatorias» y
  «Criterio de parada») y en el contrato operativo de automatización. Aquí no
  se copian: un dato, un dueño.
- **Todo lo que hay aquí es público**: el repositorio lo es a propósito
  (ADR-171). Quien escribe en él lo sabe.

## Qué hay, en números

- Decisiones (ADR): **255**.
- Bloques del motor: 17 cerrado, 3 fuera_de_alcance.
- Defectos registrados: 2 abierto, 103 cerrado.
- Ideas aparcadas o descartadas: 12 aparcada, 3 descartada, 2 promovida.
- Skills: **19**.
- Investigaciones: **14** (fotos con fecha; caducan).
- Documentos: **214**, de los que **136** no declaran fecha.

## Las skills: lo que ya costó averiguar dos veces (ADR-211)

Viven en `.claude/skills/`, una carpeta por skill, y guardan lo que
esta casa ya averiguó dos veces. No hay que leerlas todas: esta tabla dice
cuándo carga cada una, y se abre la que toque. Algo se convierte en skill
cuando se repite, cuesta medido y la decisión no es del propietario; cómo se
escribe una nueva lo dice `crear-una-skill`.

| Skill | Cuándo se carga |
|---|---|
| adr | Úsala SIEMPRE que vayas a registrar una decisión, en vez de elegir el número leyendo el listado: así nacieron los dos ADR-016 que hoy conviven en el registro. |
| cadena-de-comprobacion | Cárgala siempre que vayas a confirmar, a empujar, a decir que algo está verde, o cuando la batería o el comprobador te hayan rechazado algo y no sepas por qué. |
| comandos-para-su-ordenador | Cárgala antes de escribirle cualquier comando, ruta o instalación, y cuando un comando suyo haya fallado con «no se encuentra la ruta», «acceso denegado» o «la ejecución de scripts está deshabilitada». |
| coste-antes-de-tocar-una-fuente | Cárgala cuando vayas a lanzar más de tres agentes, a leer más de un megabyte, a gastar turnos de sesiones del propietario o cuota suya, o cuando un trabajo lleve más de una hora sin entregarle nada visible. |
| crear-una-skill | Cárgala al cerrar cualquier trabajo en el que hayas tenido que averiguar dos veces lo mismo, cuando una skill existente se te haya quedado corta, o cuando el propietario pida que aprendamos de cómo trabajamos. |
| disciplina-evidencia | Cárgala siempre que vayas a afirmar algo sobre el comportamiento del sistema, a arreglar un defecto o a producir un documento con conclusiones. |
| documento-con-lector | Cárgala antes de crear cualquier documento Markdown nuevo fuera de la carpeta de decisiones, cuando encuentres un documento que contradice el árbol, cuando la memoria común lo liste «sin fecha declarada», y al cerrar un trabajo que haya dejado documentos por el camino. |
| hablar-con-el-propietario | Cárgala antes de escribirle cualquier mensaje, antes de darle una cifra, antes de pedirle algo y antes de decidir si una pregunta merece molestarle. |
| medir-con-linea-base | Cárgala antes de lanzar cualquier medición del banco de 47 casos o de latencia, antes de escribir una cifra en un ADR o en un mensaje al propietario, y cuando alguien —él incluido— lea una cifra como regresión o como mejora. |
| modo-nocturno | Cárgala en cuanto diga «me voy a dormir», «modo nocturno», «trabaja toda la noche» o «déjalo listo para fusionar», y también si una sesión arranca de noche con una orden de esas. |
| obra-en-curso | Cárgala al empezar cualquier trabajo sobre este repositorio, antes del primer cambio, y también cuando te encuentres algo que no cuadra con lo que dice `main`: puede que lo esté haciendo otra sesión ahora mismo. |
| paquete-de-trabajo-pegado | Cárgala en cuanto un mensaje suyo tenga esa forma, y cuando después del encargo lleguen hallazgos numerados de una revisión externa. |
| paradas-del-motor-delante-del-propietario | Cárgala al abrir una sesión con mandos de GitHub, al escribir el parte de la mañana, y siempre que el diario o el tablero de una incidencia digan «esperando decisión» o `NEEDS_DECISION`. |
| rama-y-pr-de-sesion | Cárgala antes de crear una rama, cuando un `git push` te rechace por no ser avance directo, cuando vayas a abrir o a actualizar una PR, y al retomar una rama que ya tuvo una PR fusionada. |
| registro-de-defectos | Cárgala cuando encuentres un defecto, cuando arregles uno, y SIEMPRE que escribas un ADR con una `familia:` en su bloque `## La lección`: desde ADR-182 ese ADR no pasa la batería sin su entrada aquí. |
| revision-externa | Cárgala cuando una PR tuya tenga Quality en verde y toque pedir revisión, cuando llegue una revisión de Codex a una PR que llevas, y cuando el propietario diga «pásala por Codex» o «a ver qué opina». |
| traspaso-a-otra-sesion | Cárgala cuando él diga «dame un prompt para la otra sesión», «genera un informe para pasarlo» o «me voy a dormir, déjalo para la siguiente», cuando el contexto vaya a compactarse, y al abrir una sesión que empieza con un traspaso pegado. |
| validacion-manual-en-windows | Cárgala cuando un cambio toque la interfaz, el empaquetado, el arranque o las credenciales de Sirius, cuando una prueba de la trazabilidad tenga motivo «windows-real», y antes de declarar superada cualquier prueba que ninguna suite pueda dar. |
| verificar-el-estado-real | Cárgala antes de tocar un registro de estado o de decir «esto ya está», al abrir una sesión sobre una rama vieja, y siempre que él te corrija con «eso ya lo hicimos» o «¿tú sabes bien lo que se ha hecho?». |

## Qué se decidió: los ADR, del más reciente al más antiguo

**Están todos**: el índice completo -número, fecha, estado y título- se queda
entero aquí, porque saber QUÉ se decidió es la orientación que esta vista
existe para dar. Cada uno se abre por su número, en
`docs/decisions/ADR-NNN-*.md`: su ruta repetía el título y
pesaba la cuarta parte de la vista (ADR-258).

El resumen -el primer párrafo de la sección «Decisión»- solo lo llevan los ADR
desde el 174. De los anteriores está en el propio ADR,
sin copiarlo aquí. No es una poda: el texto no se ha ido a ninguna parte
-aquí no se borra nada-. Es que llevar el párrafo de las ciento y pico
decisiones viejas convertía esta vista en el corpus del que venía huyendo, y
la dejó a 630 bytes de no caber en una sola lectura (ADR-196).

| ADR | Fecha | Estado | Decisión | Resumen |
|---|---|---|---|---|
| 261 | 2026-10-19 | APROBADO | Hacer los gestos de una lista cerrada que el modelo escribe entre corchetes | Se adopta la opción 3. |
| 260 | 2026-10-18 | APROBADO | Darle a Sirius su cara en la ventana, dibujada, viva y sin congelarse | Se adopta la opción 3. |
| 259 | 2026-10-18 | APROBADO | Empezar la 0.4 del robot, los ojos, por sus pruebas de aceptación | Se adopta la opción 2. |
| 258 | 2026-10-18 | APROBADO | Hacer sitio en la memoria común nombrando cada ADR por su número, sin su ruta | La tabla de decisiones de `MEMORIA.md` nombra cada ADR por su número, con su fecha, su estado, su título y, desde el 174, su resumen, y ya no lleva la ruta de… |
| 257 | 2026-10-18 | APROBADO | Apuntar lo que midió y decidió el propietario la noche del 17 al 18-10 | Pasan E-R02-04 y E-R02-05, y E-R02-03 no pasa. La prueba sin internet no se hace, y la 0.4 empieza sin esperar a sus pruebas. |
| 256 | 2026-10-18 | APROBADO | Cortar la respuesta cuando el modelo se inventa el turno del propietario | La opción A: cada petición que lleva diálogo en sus instrucciones lleva sus comienzos de turno como paradas, y Ollama deja de escribir en cuanto el modelo… |
| 255 | 2026-10-17 | APROBADO | Cerrar Sirius cuelga todo lo que está en vuelo | La opción B, con la orden de captura esperada. C queda como segunda línea solo si, con B, la salida siguiera esperando por trabajo que no es red. |
| 254 | 2026-10-17 | APROBADO | Al cortarle, dejar de escribir la respuesta | La opción A. Cortarle por voz no es cancelar el envío: lo dicho queda dicho, ahora solo hasta donde llegó a escribir. Es el modelo de ADR-245 frente a la letra… |
| 253 | 2026-10-17 | APROBADO | Arreglar lo que salió del repaso final antes de sus pruebas | Un arreglo por punto, en los ficheros donde vive el fallo: `127.0.0.1`. Los seis adaptadores de Ollama, la charla, las huellas y los cuatro |
| 252 | 2026-10-17 | APROBADO | Dejar la voz y la ventana listas para sus pruebas de voz | Tope propio del juez, cortarle colgando su conexión, `think` apagado con reintento, la APM soltada al salir y migrar sin el registro de Alembic. Son 1(a)… |
| 251 | 2026-10-17 | APROBADO | Ajustar la memoria a lo que midió su ordenador: E-R02-04 y E-R02-05 | La opción 1. Las decisiones son técnicas y caben en lo que permite ADR-238, que dejó el umbral para que lo moviera lo que dijera E-R02-04; las toma la sesión… |
| 250 | 2026-10-17 | APROBADO | Que la voz de personaje cargue con su marca de agua | La opción 1: `setuptools<82` en el extra `personaje`. |
| 249 | 2026-10-16 | APROBADO | Que migrar la base no apague el diario de Sirius | La opción 1: `disable_existing_loggers=False` en el `fileConfig` de Alembic. |
| 248 | 2026-10-16 | APROBADO | Poner tope a lo que escribe Ollama y apuntar sus errores | La opción 1: `num_predict` con el «Máximo de tokens de salida» de los ajustes. |
| 247 | 2026-10-16 | APROBADO | Dar con una orden la cuenta de las 50 marcas de E-R02-02 | La opción 1: una orden da la cuenta de las marcas, y la de E-R02-05 mide su base y acaba. |
| 246 | 2026-10-16 | APROBADO | Elegir su voz a ciegas: la pieza F de la voz | La opción 1: la voz de personaje es la voz de serie de Chatterbox, sin audio de nadie; y la voz elegida vale desde el turno siguiente, sin volver a abrir… |
| 245 | 2026-10-15 | APROBADO | Cortarle: la pieza E de la voz | La opción 2; el micro leído todo el rato que la charla contesta, por un hilo aparte y antes de decir cada frase; y el corte apuntado en el mensaje de Sirius.… |
| 244 | 2026-10-15 | APROBADO | Escuchar siempre: la pieza D de la voz | Se adopta la opción 3, y la charla dura 10 s, desde que Sirius calla hasta que empieza a oírse la voz del turno siguiente. Los turnos de voz no despiertan al… |
| 243 | 2026-10-15 | APROBADO | Hablar en local: la pieza C de la voz | Se adopta la opción 2. |
| 242 | 2026-10-14 | APROBADO | Oír en local: la pieza B de la voz | Se adopta la opción 2. Lo decide la sesión (ADR-204: no es dinero, ni salud, ni cambia lo que el propietario ve u oye). |
| 241 | 2026-10-13 | APROBADO | Empezar la 0.3 del robot, la voz, por sus pruebas de aceptación | Se adopta la opción 2. |
| 240 | 2026-10-08 | APROBADO | Enseñar a Sirius en cada turno los tres ejemplos que más se parecen a la charla, darle sus palabras sueltas y que diga él lo que contesta a las órdenes de memoria | La opción 2, con lo que describe la nota de arranque. En concreto: Los ejemplos, como datos. `identity_versions.examples` guarda, en JSON, quién habla, |
| 239 | 2026-10-07 | APROBADO | Guardar los hechos con su fecha y quién lo dijo como recuerdos, soñar sin leer a Sirius y obedecer las órdenes de memoria sin pasar por el modelo | Se adopta la opción 2. |
| 238 | 2026-10-07 | APROBADO | Buscar los recuerdos por significado dentro de sirius.db y sacar a Ollama de cada respuesta | Se adopta la opción 2. |
| 237 | 2026-10-07 | APROBADO | Dar a Sirius memoria propia, un juez y las 40 preguntas trampa | Se adopta la opción 2 para la memoria propia, y las preguntas trampa se contestan aparte, como el primer turno de una charla nueva. |
| 236 | 2026-10-07 | APROBADO | Dar a la charla de Sirius sus modos, su recordatorio, su resumen y los dos botones | Se adopta la opción 2, y el resumen se hace al acabar el turno que lo dispara. |
| 235 | 2026-10-07 | APROBADO | Dar a Sirius la semilla del robot hecha con las marcas y las palabras del propietario | Se adopta la opción 2. |
| 234 | 2026-10-07 | APROBADO | Llevar la charla de Sirius al Ollama de este ordenador y elegir su modelo a ciegas | Se adoptan la opción 1 y, para la prueba, una ventana dentro de Sirius. |
| 233 | 2026-10-07 | APROBADO | Empezar la 0.2 del robot por su semilla y por sus pruebas de aceptación | Se adopta la opción 2. |
| 232 | 2026-10-06 | APROBADO | Hacer de Sirius solo el software del robot y revisar el roadmap: primero el cerebro, después la cabeza | La opción 3, en estos documentos: |
| 231 | 2026-10-02 | APROBADO | Un defecto se cierra desde la PR que mete en `main` el ADR que lo nombra, no solo desde la del ADR que lo declaró | Un defecto cerrado puede citar en `pr:` la PR que metió en `main` el ADR que lo declaró (ADR-222) o la que metió un ADR posterior que lo nombra por su id… |
| 230 | 2026-10-02 | APROBADO | Registrar qué revisores tuvo cada ronda y medir la convergencia y las familias solo entre rondas comparables | El veredicto agregado dice qué revisores tuvo la ronda. La regla 5 de `sirius_aggregate_reviews.py` añade `reviewers`: `["CLAUDE", "CODEX"]` en la revisión… |
| 229 | 2026-10-01 | APROBADO | Los instantes de G8 se comparan en una sola forma canónica, sean cuales sean sus escrituras | `src/sirius/domain/instantes.py` (nuevo): `FORMA_CANONICA` (`%Y-%m-%dT%H:%M:%S.%fZ`), `en_forma_canonica(texto) -> str \| None` (una fecha ISO con hora opcional… |
| 228 | 2026-10-01 | APROBADO | El implementador sabe qué hora es: su paso tiene plazo propio y el prompt lleva la hora a la que muere y la hora límite de la validación final | En `.github/workflows/implement-sirius-work.yml`: El primer paso del job, «Anotar el arranque del job», deja |
| 227 | 2026-10-01 | APROBADO | Las divergencias que el reflector aparta para una persona quedan escritas junto al diario y la vista de desenlaces las enseña con su edad | Módulo nuevo `src/sirius_engine/divergencias.py`: `DivergenciaVista` (lo que la pasada declara), `DivergenciaApartada` (lo que se conserva: encargo… |
| 226 | 2026-10-01 | APROBADO | Cuando Codex declara que no revisa y Claude pidió cambios, la ronda entrega los hallazgos de Claude en vez de tirarlos | En `scripts/automation/sirius_aggregate_reviews.py`: Las razones con las que el recolector dice que el conector declaró que |
| 225 | 2026-10-01 | APROBADO | La línea del contador de los siete días quedó cancelada por decisión del propietario el 13-09 y ADR-101 deja de tenerla como bloque pendiente | La pieza (C) de #376 queda cancelada por decisión del propietario del 13-09-2026 (#610). No se ordenará salvo decisión nueva suya; si algún día la quiere, la… |
| 224 | 2026-10-01 | APROBADO | Quality no muere por un `uv sync` sin caché: los dos pasos largos llevan plazo propio y el job sube de 20 a 60 minutos | En `.github/workflows/quality.yml`: el job pasa de `timeout-minutes: 20` a 60; «Sync environment» lleva `timeout-minutes: 20` (peor medido sin caché: |
| 223 | 2026-10-01 | APROBADO | `continua` sobre una parada anterior a la PR repone `sirius:planned` si consta que ya estuvo planificada, y si no consta lo dice sin pedir la orden otra vez | En el camino `sin_pr`, cuando la fase de destino es `sirius:implement-requested` y la incidencia no lleva `sirius:planned`, el guion: Lee la cronología de la… |
| 222 | 2026-10-01 | APROBADO | Un defecto cerrado lleva la PR que lo fusionó: la referencia que un clon de `main` puede seguir | Desde este ADR, un defecto `cerrado` lleva, además de `cerrado_por`, `pr: <número de la PR que lo fusiona>`; si lo cerró un encargo del motor, cuya PR la abre… |
| 221 | 2026-10-01 | APROBADO | La puerta de activación resuelve el `Perfil: rol@N` con el mismo resolutor que el implementador, y avisa si la versión no es la vigente | La puerta gana el paso 4: con el cuerpo ya leído, y solo para los roles del carril de ejecución del manifiesto (hoy `implementer` y `documentalista`, leídos… |
| 220 | 2026-10-01 | APROBADO | La cola regenera las vistas de la memoria al traer la base, y resuelve sola el conflicto que solo está en ellas | La puesta al día pasa a dos jobs nuevos, `regenerar` y `empujar`, que arrancan con las salidas del paso «Advance matching Sirius work item» (`ponerse_al_dia`… |
| 219 | 2026-10-01 | APROBADO | El motor dice lo que hace: el veredicto nombra su PR, el aviso de «listo» no pide una autorización que ya no necesita y una casi-orden recibe respuesta | `sirius_apply_verdict.sh` publica la línea con `printf '%s\n' "- PR: …"`: el texto va como argumento, nunca como formato. Vale para los dos caminos del… |
| 218 | 2026-10-01 | APROBADO | La vista de memoria deja fuera el índice de `docs/audits`, que pasa a una vista generada aparte, y no repite las rutas que ya enlaza | El índice de `docs/audits/` sale de `MEMORIA.md` y vive en `docs/audits/INDICE.md`, generado. Lo escribe el mismo comando (`uv run sirius-memoria conocimiento`… |
| 217 | 2026-10-01 | APROBADO | La bitácora del ciclo entra en `main` con su familia, y la evidencia de ADR-002 se queda en su rama | Entran en `main`, tal como estaban en `a044fb4a`, los 48 ficheros de `docs/audits/` que la rama añade y… |
| 216 | 2026-09-24 | APROBADO | Cerrar el ciclo: el motor se queda sin trabajo vivo, los horarios se apagan desde Actions y el estado real queda escrito | Las PR abiertas, cerradas. La #661 (cinco skills, ADR-215) fusionada aplastada en `6a58c75e`. La #117 —la rama de evidencia de julio, abierta desde el 25-07 y… |
| 215 | 2026-09-21 | APROBADO | Cinco skills más de flujo de trabajo, salidas de la auditoría y de los ADR: la validación manual en Windows, medir con línea base, el documento con lector, la rama y la PR de sesión y las paradas del motor delante del propietario | Cinco skills nuevas en `.claude/skills/`: |
| 214 | 2026-09-21 | APROBADO | Siete skills de flujo de trabajo salidas de las transcripciones: la noche delegada, la revisión externa, el coste antes de gastar, los comandos para su ordenador, el paquete pegado, el traspaso y el estado real | La tercera. Siete skills nuevas, en `.claude/skills/`: |
| 213 | 2026-09-20 | APROBADO | Escribir las tres reglas de septiembre del propietario, dar proporción a la cadena de comprobación y fechar en las transcripciones las reglas del 20-09 | `AGENTS.md`, sección «Cómo conversa el propietario, y qué espera (ADR-208)», gana las reglas 11, 12 y 13, con sus palabras y su fecha: *contesta primero… |
| 212 | 2026-09-20 | APROBADO | La cardinalidad se instruye con el criterio del canon: determinacion contra extension, no la forma de la pregunta | Se toma la opción 1. El bloque `cardinalidad` de `_INSTRUCCION` (`src/sirius/adapters/ollama_query_intent_classifier.py`) enuncia las tres definiciones de… |
| 211 | 2026-09-20 | APROBADO | Convertir en skills lo que ya costó averiguar dos veces, con una guarda que impida que se pudran | La tercera. Cinco skills nuevas, una guarda, y las dos puertas de entrada de una sesión enterándose de que existen. |
| 210 | 2026-09-20 | APROBADO | Archivar las incidencias que ya no describen nada, y decir dónde vive la bitácora del ciclo | De las nueve abiertas que la decisión 2 nombraba: |
| 209 | 2026-09-20 | APROBADO | Un ADR fusionado está aprobado, y PROPUESTO deja de existir como estado | Un ADR que está en el árbol está aprobado, porque lo que lo aprueba, según él mismo, es la fusión de su PR. `PROPUESTO` deja de existir como estado. |
| 208 | 2026-09-20 | APROBADO | Las ideas aparcadas tienen registro, y el método de conversación del propietario entra en AGENTS.md | `docs/ideas/registro_de_ideas.yml`, con tres estados y un campo que cada uno exige: |
| 207 | 2026-09-20 | APROBADO | Archivar los dos mapas caducados de julio, retirar el workflow de Word y poner en D4 el estado que ya tenía | `docs/operations/CLAUDE_SIRIUS_KNOWLEDGE_BASE.md` y `docs/operations/CLAUDE_PROJECT_ONBOARDING.md` son fotos del 20-07-2026. El primero dice que el contrato… |
| 206 | 2026-09-20 | APROBADO | Cada sesión declara su obra antes de empezar, y una guarda impide que dos se pisen | Una sesión declara su obra abriendo su pull request en cuanto tiene su primer commit, aunque sea borrador, y antes de empezar comprueba si otra obra viva toca… |
| 205 | 2026-09-20 | APROBADO | La fusión no espera al propietario cuando los dos revisores aprueban | La aprobación de los dos revisores es la autorización de merge. El comentario `fusiona` del propietario deja de ser necesario y se conserva como mando manual… |
| 204 | 2026-09-20 | APROBADO | El propietario decide producto, dinero y salud, y lo técnico lo resuelve la sesión | Se pregunta al propietario solo por tres cosas: |
| 203 | 2026-09-19 | APROBADO | El banco mide tambien el camino de puerta cerrada: la linea base que faltaba | El instrumento aprende el otro camino; el sistema medido no se toca. |
| 202 | 2026-09-14 | APROBADO | M17, la medición que cerraba la ola de paridad, no se hace; y la razón no consta | 1. M17 no se hace. Es una decisión del propietario, tomada antes de hoy. Si algún día se hace, es una decisión nueva: nada de lo escrito aquí la prepara. |
| 201 | 2026-09-14 | APROBADO | La mina de aprendizaje tiene reloj: el día 1 de cada mes se pide la edición del mes que se cierra | (sin sección Decisión) |
| 200 | 2026-09-14 | APROBADO | La cola deja de ser una condición y pasa a ser un mecanismo: el ciclo trae la base a la rama que espera | 1. La cola se consulta antes de reponer la revisión. En la rama `success)` de `.github/workflows/advance-sirius-after-quality.yml`, antes de aplicar… |
| 199 | 2026-09-14 | APROBADO | El detector de familia repetida detiene el ciclo, y esa parada vuelve al corrector, no al revisor que la emitió | 1. Con familia repetida detectada, la puerta del veredicto detiene el ciclo. En vez de `sirius:repair-requested`, publica `sirius:blocked-decision`. El… |
| 198 | 2026-09-14 | APROBADO | Partir un objetivo grande lo hace la sesión interactiva; el descomponedor automático queda descartado | (sin sección Decisión) |
| 197 | 2026-09-14 | APROBADO | El detector de familia repetida agrupa por la ruta que el revisor escribe, no por el recorte anclado | El detector agrupa por la ruta que encabeza la cita, extraída con `parse_archivo_location`, y normalizada con `_normalize_text` para que la comparación siga… |
| 196 | 2026-09-14 | APROBADO | La vista de memoria lleva el índice completo de decisiones, y el resumen solo de las que siguen vigentes como método | El índice se queda entero; la copia del resumen, no. |
| 195 | 2026-09-14 | APROBADO | «Podar» significa archivar: en este repositorio no se borra nada | (sin sección Decisión) |
| 194 | 2026-09-14 | APROBADO | `ci-pending` distingue «Quality todavía no ha contestado» de «Quality no va a contestar nunca» | El caso «sin resultado» se parte en dos, y solo lo parte un hecho explícito. |
| 193 | 2026-09-14 | APROBADO | El doble de `gh` rechaza lo que el `gh` real rechaza, y la red de seguridad vuelve a poder fechar | Dos mitades, y ninguna vale sola. |
| 192 | 2026-09-14 | APROBADO | El numero de un defecto es el numero de su ADR, no un contador aparte | Uno. El número de un defecto nuevo es el número de su ADR. `H-192` para el defecto que declara ADR-192. Nadie elige nada: se copia un dato que la entrada ya… |
| 191 | 2026-09-14 | APROBADO | La revision es una cola: una rama entra a revision solo si main ya esta dentro de ella | Uno. La condición es una sola pregunta: ¿es la punta de `main` ancestro del head de la rama? Si lo es, lo que se revise es lo que aterrizará. Si no, la… |
| 190 | 2026-09-14 | APROBADO | La guarda de citas no sale de docs/decisions/: medidas 590 citas y 23 rotas fuera del registro, cero son defectos de este árbol | La guarda de citas no sale de `docs/decisions/`. Con 0 defectos reales y 23 falsos positivos, el criterio de la incidencia #267 no se salva cambiándole la… |
| 189 | 2026-09-13 | APROBADO | La salida de una parada sin incidencia es una orden del propietario, y reanudar es despachar en el mismo gesto | Se elige la opción 1: un comando del propietario, `sirius-decidir`. Y la respuesta a «qué pasa al reanudar» es que reanudar es despachar en el mismo gesto: si… |
| 188 | 2026-09-13 | APROBADO | Parar antes de crear la incidencia cuando la orden pide tocar lo que el motor no puede escribir | Opción 1 (variante B), como QUINTA causa de sensibilidad del intérprete, con la causa `permisos_o_credenciales_sensibles`. |
| 187 | 2026-09-13 | APROBADO | Una revision sobrevive a ponerse al dia con main si el trabajo propio de la rama no cambia | La guarda de ADR-142 pasa de «mismo head» a «mismo trabajo»: la aprobación registrada sigue valiendo si el trabajo PROPIO de la rama es el mismo en el head… |
| 185 | 2026-09-13 | APROBADO | la puerta de la memoria se parte en tres interruptores antes de abrirla | Se añade `src/sirius/config/memory_gates.py` con una función pura, `puertas_de_memoria(settings) -> PuertasDeMemoria`, y un `dataclass(frozen=True)` de tres… |
| 184 | 2026-09-13 | APROBADO | La prohibicion no es una peticion: el detector de sensibilidad exige que el marcador no vaya negado | `_detectar_sensibilidad` deja de preguntar ¿aparece el marcador? y pregunta ¿la orden lo PIDE?. Una aparición cuenta solo si no va negada, y basta una… |
| 183 | 2026-09-13 | APROBADO | La ausencia de run de Quality para el head se encamina, no se espera en silencio | Opción 3. En `relanzar_quality_si_ya_termino`, la rama que hoy sale con `return 0` cuando no hay ningún run relanzable pasa a llamar a… |
| 182 | 2026-09-13 | APROBADO | La guarda del registro de defectos deriva de los ADR que declaran leccion | La guarda del registro de defectos gana una segunda mitad, y esa mitad deriva su inventario de `docs/decisions/`: un ADR que declara una lección con `familia:`… |
| 181 | 2026-09-12 | APROBADO | La contradicción de etiquetas se decide por lo que proyectan, no por cuántas son | Opción 2. `_estado_y_fase` calcula el conjunto de destinos de las etiquetas presentes y marca contradicción si y solo si hay más de uno: |
| 180 | 2026-09-12 | APROBADO | El numero del siguiente ADR se calcula contra las ramas del remoto, no contra las que el clon tenga traidas | `scripts/siguiente_adr.py` trae las cabezas del remoto antes de calcular el número, con el refspec explícito `+refs/heads/*:refs/remotes/origin/*` para que un… |
| 179 | 2026-09-12 | APROBADO | La guarda de piezas sin llamante deriva su inventario del codigo del motor | El inventario de `tests/automation/test_piezas_con_llamante.py` se deriva de `src/sirius_engine` con `ast`, en tres formas de pieza: `modulo:`, `definicion:` y… |
| 178 | 2026-09-12 | APROBADO | La autoridad por clase se deriva de la vía GitHub que el despachador declara, no de una segunda tabla a mano | La autoridad por clase se deriva de una sola definición en el dominio de qué clases existen en la vía GitHub (`CLASES_CON_VIA_GITHUB`, en… |
| 177 | 2026-09-12 | APROBADO | La ampliación por categoría entra por una señal explícita de la petición, no por la subcadena «contexto» | `Peticion` gana un campo booleano propio, `amplia_por_categoria`, apagado por defecto, y el consumidor lee ese campo y nada más. `pide_contexto` y… |
| 176 | 2026-09-12 | APROBADO | El cierre de una incidencia se retoma desde donde se quedó | El cierre de una parada sin salida se comprueba DESPUÉS de todo lo demás, y se retoma desde el estado en que el motor está. Primero se calcula el plan por… |
| 175 | 2026-09-12 | APROBADO | Un tablero por incidencia: un solo comentario que el motor mantiene al día | Uno. Un solo comentario por incidencia, reescrito en cada cambio de estado. Lleva: qué se pidió (del cuerpo declarado), por dónde va el ciclo, qué se ha… |
| 174 | 2026-09-12 | APROBADO | La mina en dos pasadas: la lección se declara en el ADR que la produce y las familias se cuentan solas | Uno. La lección se declara en el ADR que la produce, en un bloque `## La lección` con tres líneas —`familia`, `sin esto se repetiría`, `lo hace cumplir`— o con… |
| 173 | 2026-09-12 | APROBADO | El cierre de la incidencia es un desenlace, y el reflector mira todas las clases que el despachador despacha | — |
| 172 | 2026-09-12 | APROBADO | La memoria de sesión vive en Supermemory y el conocimiento en el repositorio, con una regla de reparto que toda IA lee | — |
| 171 | 2026-09-11 | APROBADO | La memoria común arranca sobre lo que ya existe: evaluación funcional de las tres piezas (T-5) y lo que el motor tiene que publicar | — |
| 170 | 2026-09-11 | APROBADO | DEC-001 entra por pertenencia a su lista cerrada: portar los miembros del origen y que G4 decida por pertenencia | — |
| 169 | 2026-09-08 | APROBADO | El filtro recorta por la cardinalidad que la peticion declara | — |
| 168 | 2026-09-08 | APROBADO | Listar por vigencia cuando la pregunta declara un intervalo y la busqueda lexica no tiene de donde partir | — |
| 167 | 2026-09-08 | APROBADO | Las dos puertas de carril retirado comprueban el estado real, no declaran éxito sin confirmarlo y se cierran ante cualquier fallo del lector | — |
| 166 | 2026-09-08 | APROBADO | El cargador del banco da a cada ítem la fecha de registro que el corpus declara | — |
| 164 | 2026-09-08 | APROBADO | La pregunta se convierte en una petición propia interpretada, no en la política uniforme de hoy | — |
| 163 | 2026-09-08 | APROBADO | Desactivar de forma reversible los carriles de investigación y auditoría: el registro de carriles retirados cierra sus entradas y explica en vez de esperar | — |
| 162 | 2026-09-08 | APROBADO | La altura de una fila del chat se mide sobre un layout asentado, no en cuanto aparece el texto | — |
| 161 | 2026-09-08 | APROBADO | Retirar los carriles dedicados de investigación y auditoría, conservando los revisores del ciclo: decisión tomada, ejecución pendiente | — |
| 160 | 2026-09-08 | APROBADO | Formalizar la separación entre Sirius y su motor: Sirius es el compañero, el motor ejecuta y las IAs externas son el lugar de trabajo | — |
| 159 | 2026-09-08 | APROBADO | El recibo de una reanudación distingue cada permiso escrito, no solo su head | — |
| 158 | 2026-09-07 | APROBADO | Cada evento de etiqueta tiene su propia ranura de notificación | — |
| 157 | 2026-09-07 | APROBADO | Cada parada deja su propio marcador de notificación | — |
| 156 | 2026-09-07 | APROBADO | El recolector lee los hallazgos que Codex publica en el cuerpo de la revisión | — |
| 155 | 2026-09-06 | APROBADO | El corrector entrega por hallazgo, con el plazo a la vista | — |
| 154 | 2026-09-06 | APROBADO | Las cifras de la validación se citan ancladas al árbol que las produjo | — |
| 153 | 2026-09-06 | APROBADO | check.ps1 se detiene en el primer paso rojo y propaga su código de salida | — |
| 152 | 2026-09-06 | APROBADO | Los pasos posteriores al agente ejecutan la automatización de `main`, no la del árbol que el agente dejó | — |
| 151 | 2026-09-06 | APROBADO | La pasada del contador mide y declara su entrega: retraso e higiene de su ventana previa | — |
| 150 | 2026-09-06 | APROBADO | Dar al corrector tiempo para corregir y validar con la cadena completa dentro de su paso | — |
| 149 | 2026-09-06 | APROBADO | Relanzar Quality al entrar en `ci-pending` cuando su cierre ya se consumió con la incidencia en otro estado | — |
| 148 | 2026-09-05 | APROBADO | Dar la memoria por bien hecha solo con todos los números del banco bien, y llegar por palancas medidas | — |
| 147 | 2026-09-05 | APROBADO | La salida de una parada la acredita el permiso escrito del propietario | — |
| 146 | 2026-09-05 | APROBADO | El fallo transitorio que Codex declara se reintenta con el candado existente | — |
| 145 | 2026-09-05 | APROBADO | La validación obligatoria es una sola invocación del script de comprobación | — |
| 144 | 2026-09-05 | APROBADO | El derivador de la hora del contador no se cuenta a sí mismo | — |
| 143 | 2026-09-05 | APROBADO | Los dos lectores de cron del repositorio hablan un único dialecto | — |
| 142 | 2026-09-05 | APROBADO | La ruta de avance repone la revisión cuando la aprobación caducó | — |
| 141 | 2026-09-05 | APROBADO | Una parada de infraestructura del revisor rearma una ronda, una sola vez | — |
| 140 | 2026-09-05 | APROBADO | El corrector firma su run y demuestra cada mutación | — |
| 139 | 2026-09-05 | RECHAZADO | La reconciliación pasa cada hora activa en vez de cada seis | — |
| 138 | 2026-09-04 | APROBADO | Los tres agentes del ciclo corren con el modelo opus | — |
| 137 | 2026-09-04 | APROBADO | El enganche de sirius-reflejar corre en un workflow propio tras cada cambio de etiqueta | — |
| 136 | 2026-09-04 | APROBADO | El reflejo del desenlace de GitHub vuelve al almacén del motor | — |
| 135 | 2026-09-04 | APROBADO | El corrector actualiza en el mismo commit el papel que depende de su corrección | — |
| 134 | 2026-09-04 | APROBADO | El guardián del suelo de prueba muerto retira las dos cotas tautológicas del banco de evidencia | — |
| 133 | 2026-09-04 | APROBADO | G3: el guardian de goteo entiende las citas tal como los revisores las escriben de verdad | — |
| 132 | 2026-09-04 | APROBADO | El guardián del contrato local de Ollama convierte ADR-125 en prueba y corrige ollama_category_classifier | — |
| 131 | 2026-09-03 | APROBADO | M21b: la interfaz de la criticidad, Sirius propone y el usuario confirma o rechaza | — |
| 130 | 2026-09-03 | APROBADO | M21a: Sirius propone la criticidad sin escribirla | — |
| 129 | 2026-09-03 | APROBADO | M20: la siembra en contexto por criticidad | — |
| 128 | 2026-09-03 | APROBADO | M19b: el rescate RF-25/RF-26 y la prioridad de G12 por criticidad | — |
| 127 | 2026-09-03 | APROBADO | M19a: el índice de criticidad en la búsqueda | — |
| 126 | 2026-09-02 | APROBADO | M18b: la señal de criticidad como dato propio de cada recuerdo y decisión | — |
| 125 | 2026-09-02 | APROBADO | Suspender el limite de 300 ms de RNF-003 en el camino del filtro de relevancia mientras se mide su coste real | — |
| 124 | 2026-09-01 | APROBADO | Cablear la petición de producción en RankRelevantKnowledgeUseCase con ámbito real derivado del proyecto activo y propósito honesto que activa pide_contexto (M16) | — |
| 123 | 2026-08-31 | APROBADO | Guardián de goteo en vivo, integrado con el aviso de familia repetida | — |
| 122 | 2026-08-31 | APROBADO | Consulta por lote en StagedEnginePort y ampliación por categoría filtrada en SQL (M13, incidencia #489, integrado sobre M14) | — |
| 121 | 2026-08-31 | APROBADO | Cablear el detector de familia repetida al ciclo real como aviso informativo | — |
| 120 | 2026-08-31 | APROBADO | M15: RF-25/RF-26 sustituye el candado de M10 y G8/G12 se aplican sobre el conjunto combinado, ambos tras la puerta | — |
| 119 | 2026-08-31 | APROBADO | Diseñar la ola de paridad en producción: portar la semántica del arnés tras la puerta category_matching_enabled, la petición de contexto real y el plan de optimización de RNF-003 (incidencia #478) | — |
| 118 | 2026-08-31 | APROBADO | Cuatro huecos operativos del motor: verdes sin registrar, reparaciones tras mover el head, bloqueos mal enrutados y decisiones invisibles al corrector (incidencias #435, #442, #453, #469, #471) | — |
| 117 | 2026-08-31 | APROBADO | M11 mide RNF-003 con el paquete completo activo y publica la coincidencia del etiquetado, sin abrir la puerta de D7 punto 6 | — |
| 116 | 2026-08-31 | APROBADO | Categoría de máxima criticidad y etiquetas canónicas provisionales del banco de 47 casos para M11 | — |
| 115 | 2026-08-31 | APROBADO | Las dos puertas que la ampliación del arnés no heredaba bajan los aciertos exactos a 29/47 y elementos de más alcanza D1 bajo la población del umbral publicado (incidencia #469) | — |
| 114 | 2026-08-30 | APROBADO | La restricción por ámbito del índice de categoría baja los elementos de más de 110 a 62 pero no alcanza D1 (incidencia #467) | — |
| 113 | 2026-08-30 | APROBADO | El índice de categoría buscable, la regla de las críticas original y la siembra en contexto cierran las dos causas de ADR-112 pero no alcanzan D1 (incidencia #465) | — |
| 112 | 2026-08-30 | APROBADO | El índice de categoría y el filtro de relevancia, conectados al arnés del banco (incidencia #463), mejoran cobertura y omisiones críticas pero empeoran los elementos de más y no alcanzan D1 | — |
| 111 | 2026-08-30 | APROBADO | La petición por caso portada mejora el banco a 23/47 pero D1 exige además el índice de categoría y el filtro de relevancia Ollama | — |
| 110 | 2026-08-30 | APROBADO | El motor por etapas portado mejora el banco a 11/47 pero no alcanza el suelo D1 porque la petición por caso del laboratorio no está autorizada a portarse | — |
| 109 | 2026-08-30 | APROBADO | El tratamiento léxico portado mejora el banco de 1/47 a 10/47, pero no alcanza el suelo D1 porque la precisión restante vive en las puertas del motor por etapas | — |
| 106 | 2026-08-29 | APROBADO | Vocabulario y modelo provisionales del clasificador de categoría en composition_root | — |
| 105 | 2026-08-29 | APROBADO | Añadir RAMA_DE_ORIGEN_NO_FUSIONADA al guardián de citas de los ADR | — |
| 104 | 2026-08-29 | APROBADO | Portar el banco de 47 casos de evidence/adr001-spikes al modelo real de Sirius | — |
| 103 | 2026-08-29 | APROBADO | Vía automática de sugerencias de memoria: delimitador compartido, divisor incremental y superficie de disparo sin Qt | — |
| 102 | 2026-08-29 | APROBADO | Las pruebas de aceptación de Sirius 0.2 no resuelven las decisiones que la Definición deja abiertas | — |
| 101 | 2026-08-28 | APROBADO | Declarar la precondicion del contador de siete dias en vez de inferirla por caso | — |
| 100 | 2026-08-28 | APROBADO | Fijar cada `rol@N` a un texto exacto con un manifiesto verificado por sha256 | — |
| 099 | 2026-08-28 | APROBADO | La clase investigacion entra en la tabla de activación, y su ejecutor es el investigador medido | — |
| 098 | 2026-08-27 | APROBADO | El investigador se queda con NVIDIA, porque fue el único que pudo correr la prueba | — |
| 097 | 2026-08-27 | APROBADO | Un tres no es un fallo sino un veredicto con motivo, y el plazo se reparte por pregunta | — |
| 096 | 2026-08-27 | APROBADO | Una contradicción de etiquetas no es una divergencia, y confundirlas gasta la salida de emergencia | — |
| 095 | 2026-08-27 | APROBADO | La escalera de cuatro preguntas, y el atestado que impide medir un modelo muerto | — |
| 094 | 2026-08-25 | APROBADO | Una parada anterior a la primera PR se reanuda repitiendo la fase, no continuando sobre un head | — |
| 093 | 2026-08-25 | APROBADO | El registro de la racha vive en la rama de memoria, no en `main` | — |
| 092 | 2026-08-25 | APROBADO | Cerrar el marcador de corte por presupuesto abandonándolo cuando el WorkItem sale de curso | — |
| 091 | 2026-08-25 | APROBADO | La disciplina de evidencia alcanza también a responder, no solo a modificar código | — |
| 090 | 2026-08-25 | APROBADO | Darle horario al motor, dentro de la ventana que dejan el reconciliador y el contador | — |
| 089 | 2026-08-25 | APROBADO | Partir un objetivo grande lo hace la sesión interactiva, y el descomponedor automático queda aplazado | — |
| 088 | 2026-08-25 | APROBADO | Elegir el prompt por el perfil del encargo, y morir en rojo si no se reconoce | — |
| 087 | 2026-08-25 | APROBADO | Dar nombre propio a los bloques del motor y exigir evidencia para cerrar uno | — |
| 086 | 2026-08-25 | APROBADO | Dar manos al despachador dentro de Actions, para que el encargo llegue al diario del motor | — |
| 085 | 2026-08-25 | APROBADO | El intérprete de intención comprueba sensibilidad y verbo reconocido antes que marcadores de pasado | — |
| 084 | 2026-08-25 | APROBADO | El aviso de lecturas caidas hoy no interrumpe el contador de la racha | — |
| 083 | 2026-08-24 | APROBADO | La memoria del motor vive en su propia rama, no en `main` | — |
| 082 | 2026-08-24 | APROBADO | El motor corre dentro de GitHub Actions y su memoria vive en el repositorio | — |
| 081 | 2026-08-23 | APROBADO | Un doble de pruebas que se calla esconde el defecto que debería delatar | — |
| 080 | 2026-08-23 | APROBADO | Un arreglo fusionado se reconoce por el asunto del commit, y por eso la guarda ve poco pero no se equivoca | — |
| 079 | 2026-08-23 | APROBADO | Una tabla indexada por un enum cubre el enum entero, o lo declara | — |
| 078 | 2026-08-23 | APROBADO | Tres rondas consecutivas sobre el mismo archivo son la familia repetida, medido antes de fijarlo | — |
| 077 | 2026-08-23 | APROBADO | La autoridad de una clase es la tabla estática más un registro fechado, y su reversión no espera a la segunda divergencia | — |
| 076 | 2026-08-23 | APROBADO | El motor deja de necesitar el árbol de código para ejecutar la proyección | — |
| 075 | 2026-08-22 | APROBADO | El estado de un defecto lo dice el registro versionado y la incidencia se cierra con el | — |
| 074 | 2026-08-22 | APROBADO | El contador de los siete días deriva la corrección manual del diario de eventos del motor | — |
| 073 | 2026-08-22 | APROBADO | El verificador de proyección se ve fallar antes de fiarse de que dé verde | — |
| 072 | 2026-08-22 | APROBADO | REPARAR tiene dos entradas, porque el ciclo real tiene dos | — |
| 071 | 2026-08-22 | APROBADO | La inversa de la proyección del cuerpo, para que haya algo que verificar | — |
| 070 | 2026-08-22 | APROBADO | Las defensas de workflow reconocen «acción clasificada», no un nombre | — |
| 069 | 2026-08-22 | APROBADO | Fusionar exige que la rama esté al día con su base | — |
| 068 | 2026-08-22 | APROBADO | La etiqueta que el motor aplica depende de la clase que despacha | — |
| 067 | 2026-08-22 | APROBADO | Las órdenes del propietario toleran la firma que añade la herramienta | — |
| 066 | 2026-08-22 | APROBADO | Perfiles documentales: documentalista y revisor documental, coherentes con la maquinaria existente | — |
| 065 | 2026-08-22 | APROBADO | El despachador usa el diario durable ahora y no en D2 | — |
| 064 | 2026-08-22 | APROBADO | Diario del despachador durable reutiliza ADR-061 | — |
| 063 | 2026-08-21 | APROBADO | `sirius-despachar`: la costura entre una orden y la vía GitHub, con ensayo por defecto | — |
| 062 | 2026-08-21 | APROBADO | C2 — despacho end-to-end de programación: escritura mínima enumerada y orden enlazada en la evidencia | — |
| 061 | 2026-08-21 | APROBADO | Diario del supervisor durable como outbox propio, no acoplado al almacen | — |
| 060 | 2026-08-21 | APROBADO | Un error del conector no es silencio, y no debe costar el plazo entero | — |
| 059 | 2026-08-21 | APROBADO | La sesión dice «no pude mirar» en vez de «no hay nada», y lo dice también cuando sí encontró algo | — |
| 058 | 2026-08-21 | APROBADO | La fase entra en la tabla de estados como coordenada dependiente, y el eje fase gana su propia guarda | — |
| 057 | 2026-08-21 | APROBADO | Supervisor de la vía GitHub: detectar Runs perdidos y actuar | — |
| 056 | 2026-08-21 | APROBADO | El motor puede transportar una orden ya dada y reparar sus propios Runs | — |
| 055 | 2026-08-21 | APROBADO | Dar al motor un comando de consola que conversa y consulta, y que no puede crear trabajo | — |
| 054 | 2026-08-21 | APROBADO | Un Run tiene que poder decir con qué modelo se ejecutó | — |
| 053 | 2026-08-21 | APROBADO | «No pude observar» es un valor del puerto, y el barrido no lo convierte en éxito | — |
| 052 | 2026-08-21 | APROBADO | Una ruta citada por un ADR existe, o está fijada como historia | — |
| 051 | 2026-08-21 | APROBADO | El cuerpo de una incidencia pasa por el mismo filtro de confianza que sus comentarios | — |
| 050 | 2026-08-21 | APROBADO | Los tres proveedores de `contexto.recuperar` tienen la misma firma y reportan su fallo | — |
| 048 | 2026-08-21 | APROBADO | La capa que llama a las reglas también necesita su tabla exhaustiva de estados | — |
| 047 | 2026-08-21 | APROBADO | Un defecto encontrado se registra con incidencia y no se borra nunca | — |
| 046 | 2026-08-21 | APROBADO | Spike I1: bordes de STATUS sobre runs de Actions | — |
| 045 | 2026-08-21 | APROBADO | El corte por presupuesto tiene que salir también de WAITING, que es donde se gasta el dinero | — |
| 044 | 2026-08-20 | APROBADO | Abrir el repositorio al público sin que el propio repositorio lo desmienta | — |
| 043 | 2026-08-19 | APROBADO | Gobierno previo al primer Worker externo: puerta determinista, presupuesto con corte y siete causas cerradas de escalado | — |
| 042 | 2026-08-19 | APROBADO | Un paso de preparación sin plazo propio puede costar el trabajo entero | — |
| 041 | 2026-08-19 | APROBADO | La autoridad de cada clase de trabajo se fija antes de que exista el primer WorkItem | — |
| 040 | 2026-08-19 | APROBADO | Convertir una intención en encargo preguntando una cosa cada vez | — |
| 039 | 2026-08-19 | APROBADO | Perfiles versionados gobiernan a los Workers sin acoplarse a runtimes, y el egress es imposible de saltar | — |
| 038 | 2026-08-19 | APROBADO | Una prueba que mutila datos debe alterar siempre lo que comprueba | — |
| 037 | 2026-08-18 | APROBADO | Reanudar y fusionar son gestos humanos, y la automatización no los rodea | — |
| 036 | 2026-08-18 | APROBADO | Una lectura caída no es una ausencia, y el llamador tiene que poder distinguirlas | — |
| 035 | 2026-08-18 | APROBADO | El revisor no juzga con el intérprete del runner, y toda parada tiene vuelta | — |
| 034 | 2026-08-18 | APROBADO | El espejo de solo lectura de la vía GitHub marca cada proyección como no autoritativa y nunca confunde un fallo de lectura con una ausencia | — |
| 033 | 2026-08-18 | APROBADO | Una regla que enumera vehículos siempre tiene un hueco más: enunciar la propiedad | — |
| 032 | 2026-08-17 | APROBADO | Calcular el número de un ADR como el máximo existente más uno | — |
| 031 | 2026-08-18 | APROBADO | Un rol necesita un veredicto para cada desenlace real, incluido «esto no lo he roto yo» | — |
| 030 | 2026-08-18 | APROBADO | Todo estado de parada declara la orden que lo levanta | — |
| 029 | 2026-08-18 | APROBADO | Promocionar el patrón de escritura de S1 a almacén de referencia del Work Engine, más el barrido de recuperación (A2) | — |
| 028 | 2026-08-17 | APROBADO | Una avería transitoria de un tercero no justifica una invariante permanente en la suite | — |
| 027 | 2026-08-17 | APROBADO | Las etiquetas se leen del objeto de la incidencia, nunca del endpoint `/issues/{n}/labels` | — |
| 026 | 2026-08-17 | APROBADO | Adoptar diario append-only con `fsync`, checksum por registro e idempotencia por clave como patrón de escritura seguro del spike I3 | — |
| 025 | 2026-08-17 | APROBADO | Ninguna afirmación de un prompt sobre su entorno vale sin una prueba que la ate al workflow que lo ejecuta | — |
| 024 | 2026-08-17 | APROBADO | Extender al implementador las tres reglas de rol y vigilarlas con una prueba que recorre el directorio de prompts | — |
| 023 | 2026-08-16 | APROBADO | Admitir como aprobación de Codex el comentario en el que declara no haber encontrado hallazgos | — |
| 022 | 2026-08-16 | APROBADO | Endurecer el prompt del revisor: veredicto provisional, prohibición de esperar nada (subagentes incluidos) y revisión con el entorno acotado que hay | — |
| 021 | 2026-08-16 | APROBADO | Prohibir en el prompt que el corrector cierre el turno esperando trabajo en segundo plano | — |
| 020 | 2026-08-15 | APROBADO | Construir el Work Engine por verticales delgadas, reutilizando la vía GitHub y aplazando cada decisión a su punto exacto de consumo | — |
| 019 | 2026-08-15 | APROBADO | Diseñar el Motor de Trabajo como software determinista que posee el estado, con Workers sustituibles detrás de Adapters | — |
| 016 | 2026-08-14 | APROBADO | El Auditor se lanza con una etiqueta, y el trabajo que puede escribir no ejecuta modelos | — |
| 016 | 2026-08-14 | APROBADO | El estado del proyecto se lee de `main`, nunca de la rama de trabajo | — |
| 015 | 2026-08-14 | APROBADO | Toda escritura de etiqueta pasa por una envoltura con el PAT, y la prueba busca lo malo en vez de lo bueno | — |
| 014 | 2026-08-14 | APROBADO | Quien escribe una etiqueta notificable usa la identidad real, y el recolector de Codex no aprueba por comentario | — |
| 013 | 2026-08-14 | APROBADO | La contraseña de OBS vive en el almacén del sistema, y sin él no se guarda | — |
| 012 | 2026-08-14 | APROBADO | Un proceso local que corre como el usuario está dentro de la frontera de confianza | — |
| 011 | 2026-08-14 | APROBADO | Correlacionar cada respuesta de OBS con su petición, en vez de desconectar ante un plazo agotado | — |
| 010 | 2026-08-12 | APROBADO | Adoptar Auditor Agent v0 (solo lectura) como primer piloto de agentes | — |
| 009 | 2026-08-12 | APROBADO | Sacar la voz de Model Studio por el reproductor del sistema y empezar a hablar antes de terminar | — |
| 008 | 2026-08-11 | APROBADO | Cargar en lote las revisiones vigentes al listar recuerdos y decisiones | — |
| 007 | 2026-08-10 | APROBADO | Afirmar el límite de rendimiento en CI solo si hay un orden de magnitud de holgura | — |
| 006 | 2026-08-10 | APROBADO | Declarar la trazabilidad PA/SP y comprobarla por máquina, en vez de derivarla por búsqueda | — |
| 005 | 2026-08-10 | APROBADO | Mantener el estado de V8 en un único registro que la automatización pueda escribir | — |
| 004 | 2026-08-10 | APROBADO | Una red de seguridad periódica, porque un run muerto no puede avisar | — |
| 003 | 2026-08-10 | APROBADO | Un plazo es un mínimo contra una cota absoluta, nunca una ventana propia | — |
| 002 | 2026-08-09 | APROBADO | No conceder a la automatización permiso sobre sus propios workflows | — |
| 001 | 2026-08-08 | APROBADO | Instrumentar la disciplina de evidencia con una skill y este registro | — |

## Las lecciones, por familia (ADR-174)

Lo que alguien repetiría sin cada ADR, agrupado por familia de fallo y
contado por la máquina. **La cuenta no la lleva nadie**: un número escrito a
mano caduca en silencio -`AGENTS.md` decía «seis veces» cuando ya iban ocho-.
Declararla es obligatorio desde ADR-174; los anteriores
quedan exentos, así que esta vista crece desde cero en vez de nacer rellenada
de memoria. Cada ADR va por su número, como en la tabla de arriba (ADR-218 y
ADR-258).

| Familia | Veces | Hay prueba que la haga cumplir | ADR |
|---|---|---|---|
| `regla-que-depende-de-que-alguien-se-acuerde` | 11 | no en todas | 227, 222, 220, 217, 216, 192, 191, 188, 182, 179, 174 |
| `prueba-que-no-puede-ver-lo-que-vigila` | 6 | no en todas | 261, 259, 249, 247, 241, 238 |
| `pieza-sin-lector` | 5 | no en todas | 210, 209, 207, 183, 175 |
| `doble-mas-permisivo-que-la-herramienta-que-dobla` | 4 | sí | 251, 250, 242, 193 |
| `prosa-que-el-cambio-deja-falsa` | 4 | no en todas | 223, 219, 211, 177 |
| `regla-del-propietario-que-solo-vive-en-una-conversacion` | 4 | sí | 213, 208, 204, 195 |
| `modelo-dentro-del-turno` | 3 | sí | 254, 243, 237 |
| `vista-que-copia-el-corpus-del-que-venia-huyendo` | 3 | sí | 258, 218, 196 |
| `decision-que-solo-vive-en-una-conversacion` | 2 | no en todas | 225, 202 |
| `guardian-que-mide-posicion-en-vez-de-estructura` | 2 | sí | 221, 187 |
| `leccion-que-se-queda-en-el-informe` | 2 | sí | 215, 214 |
| `lista-a-mano` | 2 | sí | 181, 178 |
| `medir-lo-que-se-tiene-en-vez-de-lo-que-hay` | 2 | sí | 184, 180 |
| `parada-segura-que-tira-lo-ya-pagado` | 2 | sí | 253, 226 |
| `paso-largo-sin-plazo-propio` | 2 | sí | 228, 224 |
| `pieza-correcta-a-la-que-no-llama-quien-la-necesita` | 2 | sí | 248, 197 |
| `cierre-que-no-corta-todo-lo-que-pide` | 1 | sí | 255 |
| `comparar-instantes-como-texto` | 1 | sí | 229 |
| `condicion-construida-sin-el-mecanismo-que-la-hace-cumplible` | 1 | sí | 200 |
| `cortar-solo-entre-trozos` | 1 | sí | 252 |
| `criterio-que-se-pide-distinto-del-que-se-puntua` | 1 | sí | 212 |
| `dos-sesiones-que-no-se-ven` | 1 | sí | 206 |
| `espera-sin-fin-por-un-suceso-que-nadie-va-a-emitir` | 1 | sí | 194 |
| `estado-compartido-entre-hilos` | 1 | sí | 239 |
| `estado-en-el-que-se-entra-y-del-que-no-se-sale` | 1 | sí | 189 |
| `guarda-ampliada-a-un-corpus-que-no-es-el-suyo` | 1 | sí | 190 |
| `guarda-medida-que-se-queda-sin-autoridad-porque-nadie-relee-la-medida` | 1 | sí | 199 |
| `instrumento-que-solo-mide-un-lado` | 1 | sí | 203 |
| `interruptor-que-enciende-mas-de-lo-que-se-puede-medir` | 1 | sí | 185 |
| `la-hora-de-quien-lee-y-no-de-quien-capta` | 1 | sí | 245 |
| `lo-que-un-hilo-carga-despues-de-cerrar` | 1 | sí | 246 |
| `plan-que-hay-que-terminar-de-una-sentada` | 1 | sí | 176 |
| `pregunta-al-propietario-que-nadie-vuelve-a-poner-delante` | 1 | no en todas | 198 |
| `registro-sin-decir-quien-lo-hizo` | 1 | sí | 230 |
| `regla-nueva-que-cambia-lo-que-otro-reconoce` | 1 | sí | 244 |
| `regla-nueva-sin-pasarla-por-los-casos-vivos` | 1 | sí | 231 |
| `tarea-periodica-sin-reloj` | 1 | no en todas | 201 |
| `tramite-que-solo-puede-hacer-una-persona-y-no-anade-comprobacion` | 1 | sí | 205 |
| `turnos-en-las-instrucciones-sin-parada` | 1 | sí | 256 |

### `regla-que-depende-de-que-alguien-se-acuerde`

- **ADR-227** — derivar una contradicción a «una persona» en el diseño y no dejar ningún sitio donde esa persona la encuentre: el motivo se imprimía en un log que nadie relee, y la memoria común la contaba como un encargo activo más. (lo hace cumplir `tests/engine/test_reflect_cli.py`).
- **ADR-222** — una convención de registro escrita para un modo de fusión (con commit de mezcla) que sobrevive al cambio de modo (aplastado) sin que nadie la relea, con la batería en verde y 29 referencias que no llevan a ninguna parte. (lo hace cumplir `tests/automation/test_registro_de_defectos.py`).
- **ADR-220** — automatizar la mitad de un gesto (traer la base) y dejar la otra mitad (regenerar lo generado) a que alguien se acuerde, con Quality como único aviso y 25 minutos después. (lo hace cumplir `tests/automation/test_cola.py`).
- **ADR-217** — dejar la entrada de un registro en `main` condicionada (sin prueba que lo haga cumplir: ninguna prueba: la condición vivía en prosa de un documento).
- **ADR-216** — escribir una salvaguarda en prosa y darla por puesta. (lo hace cumplir `tests/automation/test_cierre_del_ciclo_ps1_no_puede_hacer_dano.py`).
- **ADR-192** — elegir a mano un identificador leyendo el máximo del (lo hace cumplir `tests/automation/test_registro_de_defectos.py`).
- **ADR-191** — fusionar una rama cuya combinación con `main` no ha (lo hace cumplir `tests/automation/test_cola.py`).
- **ADR-188** — despachar al ciclo automático un encargo cuyo alcance cae donde la credencial del motor no llega, hacer el trabajo entero y perderlo en el push, porque la única regla que lo evitaba vivía en la cabeza de quien despacha. (lo hace cumplir `tests/engine/test_intent_interpreter.py`).
- **ADR-182** — poner a vigilar un registro con comprobaciones que solo miran la coherencia de lo ya escrito; el registro deja de recibir lo que pasa, ninguna de ellas puede notarlo y el verde lo confirma —aquí fueron doce días sin una sola entrada, con todos los ADR de ese intervalo entrando entretanto. (lo hace cumplir `tests/automation/test_registro_de_defectos.py`).
- **ADR-179** — escribir un guardián sobre una lista de inclusión (lo hace cumplir `tests/automation/test_piezas_con_llamante.py`).
- **ADR-174** — escribir la regla de captura en un catálogo y dar por hecho que alguien la aplicará; los dos sitios de lecciones de este repositorio llevaban 48 ADR sin una sola entrada, con sus reglas escritas dentro. (lo hace cumplir `tests/automation/test_mina_de_lecciones.py`).

### `prueba-que-no-puede-ver-lo-que-vigila`

- **ADR-261** — cambiar lo que llega a trozos y ajustar solo las pruebas que (lo hace cumplir `tests/gui/test_conversation_ui.py`).
- **ADR-259** — una huella de mentira con una marca en sus bytes la pierde en cuanto la pieza la pasa a números, y la prueba de «cifradas» pasaría con la huella guardada en claro (lo hace cumplir `tests/acceptance/test_dobles_del_conductor_0_4.py`).
- **ADR-249** — arreglar en la prueba lo que falla en el producto. El conductor de (lo hace cumplir `tests/gui/test_app_bootstrap.py`).
- **ADR-247** — probar una orden que él ejecuta en su ordenador solo como es la (lo hace cumplir `tests/integration/test_medir_busqueda_de_memoria.py`).
- **ADR-241** — escribir las pruebas de aceptación de una versión antes del (sin prueba que lo haga cumplir: ninguna prueba mide la fuerza de una prueba; lo que hay es).
- **ADR-238** — una prueba de «no se hace X» que pasa con X puesto, porque su (lo hace cumplir `tests/acceptance/test_robot_0_2_memoria.py`).

### `pieza-sin-lector`

- **ADR-210** — el tablero de incidencias seguiría llenándose de cosas (sin prueba que lo haga cumplir: ninguna prueba: cerrar una incidencia ocurre en GitHub, no).
- **ADR-209** — el campo de estado seguiría siendo ruido, y cada ADR (lo hace cumplir `tests/automation/test_estado_de_los_adr.py`).
- **ADR-207** — seguirían conviviendo documentos que nadie mantiene y (lo hace cumplir `tests/automation/test_registro_de_bloques.py`).
- **ADR-183** — escribir la rama «no hay nada que hacer» de un encaminador como un `return 0` con un `echo`, de modo que la única prueba de que el ciclo se ha parado viva en un log que nadie lee. (lo hace cumplir `tests/automation/test_sirius_apply_verdict.py`).
- **ADR-175** — proyectar en cada pasada el estado entero de una incidencia -fase, rondas, Quality, PR, diagnóstico- y no enseñárselo nunca a quien tiene que decidir; es la novena vez que un dato correcto de esta casa no tiene lector, tres días después de la octava. (lo hace cumplir `tests/engine/test_tablero.py`).

### `doble-mas-permisivo-que-la-herramienta-que-dobla`

- **ADR-251** — el banco de memoria pasaba en la nube con unas huellas de (lo hace cumplir `tests/integration/test_memoria_en_su_ordenador.py`).
- **ADR-250** — probar con dobles una biblioteca que nadie cargó. (lo hace cumplir `tests/automation/test_marca_de_agua.py`).
- **ADR-242** — un adaptador que carga una biblioteca con código nativo solo (lo hace cumplir `tests/unit/test_local_listening_adapters.py`).
- **ADR-193** — una prueba en verde sobre una invocación que la (lo hace cumplir `tests/automation/test_sirius_reconcile.py`).

### `prosa-que-el-cambio-deja-falsa`

- **ADR-223** — un camino de reinicio escrito cuando activar era una etiqueta, que anuncia «autorizado» sin releer la puerta que ahora exige dos; el aviso en verde era verdad el día que se escribió y dejó de serlo sin que nadie lo tocara. (lo hace cumplir `tests/automation/test_reanudar_ejecutando_el_guion.py`).
- **ADR-219** — cambiar la regla (ADR-205) y dejar el aviso que la contaba al propietario diciendo la regla vieja; y dar por publicada una línea de un comentario sin haber leído nunca un comentario publicado. (lo hace cumplir `tests/automation/test_sirius_notifications.py`).
- **ADR-211** — escribir un documento de método que nadie vuelve a (lo hace cumplir `tests/automation/test_skills.py`).
- **ADR-177** — retirar un símbolo de producción y dejar vivas las frases que lo daban por cierto; al quitar `pide_contexto` quedaron falsos los once pasajes de prosa que la sección 6 de esta ficha enumera, 22 referencias del literal en las pruebas más otros cuatro pasajes de pruebas que describían el mecanismo sin nombrarlo, y el criterio de aceptación de M16 de la Arquitectura Técnica; y el barrido que las buscó en `scripts/` y `tests/` no miró en `docs/evolution/` ni podía ver lo que no escribe el literal, así que una lista solo se declara completa sobre el alcance del barrido que la produjo y el resto se dice cubierto por lectura. (sin prueba que lo haga cumplir: ninguna prueba: nada en este repositorio vigila la coherencia de la prosa de `docs/` con el árbol, y la ocurrencia que queda viva está en la Arquitectura Técnica, que la salvaguarda de #581 prohíbe tocar sin decisión del propietario.).

### `regla-del-propietario-que-solo-vive-en-una-conversacion`

- **ADR-213** — que una regla que él dijo el 14-09 («que me contestes (lo hace cumplir `tests/automation/test_reglas_de_agents.py`).
- **ADR-208** — las ideas aparcadas volverían como nuevas y cada (lo hace cumplir `tests/automation/test_registro_de_ideas.py`).
- **ADR-204** — la sesión seguiría devolviéndole decisiones técnicas (lo hace cumplir `tests/automation/test_reglas_de_agents.py`).
- **ADR-195** — una regla dada de viva voz —«no se elimina nada»— que no (lo hace cumplir `tests/automation/test_registro_de_defectos.py`).

### `modelo-dentro-del-turno`

- **ADR-254** — al cortarle, dejar que siga dentro del turno una petición al modelo (lo hace cumplir `tests/acceptance/test_robot_0_3_voz.py`).
- **ADR-243** — esperar a que `send_message` vuelva para hacer lo que toca en (lo hace cumplir `tests/integration/test_send_message.py`).
- **ADR-237** — poner otra petición al modelo de la charla dentro de cada turno, (lo hace cumplir `tests/acceptance/test_robot_0_2_personalidad.py`).

### `vista-que-copia-el-corpus-del-que-venia-huyendo`

- **ADR-258** — la fila de cada ADR llevaba su título dos veces, una en su ruta, y la vista volvía a no caber con el ADR siguiente (lo hace cumplir `tests/engine/test_memoria.py`).
- **ADR-218** — dejar que la única lectura lleve dos veces la misma ruta y la fila de cada pieza de evidencia, y descubrirlo cuando la guardia bloquea una PR que no tiene la culpa; es la segunda vez que muerde esta familia en 17 días, y el suelo que no se puede cortar está declarado arriba con su cifra. (lo hace cumplir `tests/engine/test_memoria.py`).
- **ADR-196** — una vista que existe para caber en una sola lectura (lo hace cumplir `tests/engine/test_memoria.py`).

### `decision-que-solo-vive-en-una-conversacion`

- **ADR-225** — una orden del propietario que cancela una línea entera queda en el comentario de una incidencia cerrada, y dieciocho días después el ADR, el código y el estado del proyecto siguen diciendo que esa línea está pendiente y bloquea algo; la siguiente sesión la retomaría o la pondría delante de él otra vez. (sin prueba que lo haga cumplir: ninguna prueba: una decisión del propietario no tiene hoy una forma mecánica que una guarda pueda leer; la caza la mina mensual (deuda 13) y la hoja de decisiones abiertas, a posteriori).
- **ADR-202** — una decisión de NO hacer algo no deja rastro —no hay (sin prueba que lo haga cumplir: ninguna prueba: una decisión tomada de viva voz fuera del).

### `guardian-que-mide-posicion-en-vez-de-estructura`

- **ADR-221** — una puerta que comprueba la forma del cuerpo (las secciones) y no lo que el siguiente paso va a hacer con él (resolver el perfil), y da por válida una activación que muere a los seis segundos. (lo hace cumplir `tests/automation/test_sirius_activation.py`).
- **ADR-187** — escribir un guardián que comprueba que algo aparece (lo hace cumplir `tests/automation/test_misma_obra.py`).

### `leccion-que-se-queda-en-el-informe`

- **ADR-215** — creer que sin transcripciones no salen más skills (lo hace cumplir `tests/automation/test_skills.py`).
- **ADR-214** — leer caro y dejar lo aprendido solo en un informe (lo hace cumplir `tests/automation/test_skills.py`).

### `lista-a-mano`

- **ADR-181** — escribir como lista de excepciones un criterio que el dato de al lado ya define —aquí «qué etiquetas pueden convivir», enumerado a mano habiendo una tabla que dice a dónde apunta cada una—, de modo que la lista solo contiene lo que alguien recordó el día que la escribió y acusa de avería a todo lo demás. (lo hace cumplir `tests/engine/test_mirror_projection.py`).
- **ADR-178** — escribir dos veces «qué clases existen en la vía GitHub» -una tabla que decide y una copia que se queda vieja- y comprobar la copia en vez de la relación; es la familia que ADR-033 nombró, y aquí dejó quince encargos sin medir durante dos semanas. (lo hace cumplir `tests/engine/test_authority.py`).

### `medir-lo-que-se-tiene-en-vez-de-lo-que-hay`

- **ADR-184** — poner una guarda a responder la pregunta que sabe contestar barata —«¿aparece la palabra?»— en lugar de la que tiene que contestar —«¿la orden lo pide?»—, y no notarlo porque el sustituto acierta casi siempre: aquí acertó en 1 de 3 paradas reales y paró sobre las salvaguardas que prohibían justo la operación. (lo hace cumplir `tests/engine/test_intent_interpreter.py`).
- **ADR-180** — preguntarle a la copia local por un hecho que vive fuera -las ramas traídas en vez de las que existen- y creer que la respuesta cubre el caso; aquí el guion veía el 3,4% de las ramas y repartió el mismo número tres veces en un día. (lo hace cumplir `tests/automation/test_registro_de_decisiones.py`).

### `parada-segura-que-tira-lo-ya-pagado`

- **ADR-253** — un fallo de un modelo en la respuesta 46 de 60, o un Esc sin (lo hace cumplir `tests/unit/test_blind_test.py`).
- **ADR-226** — tratar toda parada de un revisor como pérdida del veredicto del otro, aunque el que para haya declarado que no va a revisar y el otro ya haya entregado hallazgos pagados; la asimetría que protege (no aprobar sin los dos) se conserva sin tirar el trabajo hecho. (lo hace cumplir `tests/automation/test_sirius_aggregate_reviews.py`).

### `paso-largo-sin-plazo-propio`

- **ADR-228** — dar a un agente una regla que depende de la hora («para si no cabe») sin darle la hora ni un plazo propio, y dejar que el tope del job lo mate sin diagnóstico; la misma lección que ADR-155 dejó para el corrector y ADR-224 para los pasos de Quality, aplicada al paso que quedaba. (lo hace cumplir `tests/automation/test_implementador_con_reloj.py`).
- **ADR-224** — dejar que el tope del job sea el único plazo de un paso que depende de la red, y descubrirlo en una cancelación muda que no guarda caché y se repite sola; es la misma lección que el paso de `apt` dejó escrita el 19-08, aplicada esta vez a los dos pasos que quedaban. (lo hace cumplir `tests/automation/test_quality_no_muere_por_un_sync_lento.py`).

### `pieza-correcta-a-la-que-no-llama-quien-la-necesita`

- **ADR-248** — un proveedor nuevo sin las salvaguardas del de antes. El tope de (lo hace cumplir `tests/integration/test_tope_de_salida_de_ollama.py`).
- **ADR-197** — dos piezas del mismo árbol leen la misma clase de dato (lo hace cumplir `tests/engine/test_round_family_detector.py`).

### `cierre-que-no-corta-todo-lo-que-pide`

- **ADR-255** — cada trabajo de fondo nuevo nacería sin saber cortarse al cerrar (lo hace cumplir `tests/unit/test_toda_conexion_nace_colgable.py`).

### `comparar-instantes-como-texto`

- **ADR-229** — comparar instantes por orden léxico de cadenas que distintos emisores escriben de distinta forma, y descubrirlo caso a caso en la frontera: tres veces en septiembre (entradas 52, 60 y 69), siempre parcheando al emisor porque el comparador estaba fuera del alcance. (lo hace cumplir `tests/unit/test_instantes_en_una_sola_forma.py`).

### `condicion-construida-sin-el-mecanismo-que-la-hace-cumplible`

- **ADR-200** — una guarda se construye entera y se deja sin llamante (lo hace cumplir `tests/automation/test_cola.py`).

### `cortar-solo-entre-trozos`

- **ADR-252** — un corte que se mira entre trozos no corta mientras el otro calla. (lo hace cumplir `tests/unit/test_el_juez_no_frena_la_voz.py`).

### `criterio-que-se-pide-distinto-del-que-se-puntua`

- **ADR-212** — escribir a ojo la instrucción que se le da a un (lo hace cumplir `tests/unit/test_ollama_query_intent_classifier.py`).

### `dos-sesiones-que-no-se-ven`

- **ADR-206** — dos sesiones volverían a construir lo mismo o a (lo hace cumplir `tests/automation/test_obra_en_curso.py`).

### `espera-sin-fin-por-un-suceso-que-nadie-va-a-emitir`

- **ADR-194** — una incidencia en un estado que solo mueve la máquina, (lo hace cumplir `tests/automation/test_sirius_reconcile.py`).

### `estado-compartido-entre-hilos`

- **ADR-239** — un caso de uso nuevo que corre en segundo plano reutiliza la (lo hace cumplir `tests/integration/test_ordenes_de_memoria.py`).

### `estado-en-el-que-se-entra-y-del-que-no-se-sale`

- **ADR-189** — dar por buena una arista del dominio que en producción no llama nadie, y dejar así un estado en el que el motor entra solo y del que solo puede salir un mecanismo que necesita un dato que ese estado, por definición, no tiene. (lo hace cumplir `tests/engine/test_decision_cli.py`).

### `guarda-ampliada-a-un-corpus-que-no-es-el-suyo`

- **ADR-190** — llevar una comprobación al sitio donde el hueco está declarado sin medir antes qué cosecharía allí, y pagar la ampliación con excepciones escritas a mano; aquí el criterio calibrado sobre `docs/decisions/` —un corpus homogéneo, donde un ADR cita este árbol— habría gritado 17 veces en falso y cazado cero defectos al salir a `docs/`, donde una investigación cita los árboles de otros repositorios. (lo hace cumplir `tests/automation/test_citas_de_los_adr.py`).

### `guarda-medida-que-se-queda-sin-autoridad-porque-nadie-relee-la-medida`

- **ADR-199** — una guarda se fusiona a propósito sin autoridad para (lo hace cumplir `tests/automation/test_reanudar_una_parada.py`).

### `instrumento-que-solo-mide-un-lado`

- **ADR-203** — publicar «la pieza X aporta tanto» citando solo la (lo hace cumplir `tests/acceptance/test_pa_0_2_rec_01_banco_evidencia.py`).

### `interruptor-que-enciende-mas-de-lo-que-se-puede-medir`

- **ADR-185** — poner una sola puerta delante de varias piezas (lo hace cumplir `tests/unit/test_composition_root_relevance_gate.py`).

### `la-hora-de-quien-lee-y-no-de-quien-capta`

- **ADR-245** — decidir algo de lo oído con el estado del momento en que se (lo hace cumplir `tests/unit/test_local_listening.py`).

### `lo-que-un-hilo-carga-despues-de-cerrar`

- **ADR-246** — que un trabajo en segundo plano siga cargando después de que (lo hace cumplir `tests/unit/test_voice_test.py`).

### `plan-que-hay-que-terminar-de-una-sentada`

- **ADR-176** — escribir un plan de varios pasos contra un almacén que los aplica uno a uno, y comprobar la precondición del primero en vez del estado real en que el motor está, de modo que una interrupción a la mitad deja el trabajo atascado para siempre. (lo hace cumplir `tests/engine/test_reflect.py`).

### `pregunta-al-propietario-que-nadie-vuelve-a-poner-delante`

- **ADR-198** — una incidencia formula una pregunta que solo el (sin prueba que lo haga cumplir: ninguna prueba: nada en este repositorio distingue una).

### `registro-sin-decir-quien-lo-hizo`

- **ADR-230** — comparar una ronda a la que le falta un revisor con rondas enteras y leer la ausencia de sus hallazgos como progreso, y su vuelta como reaparición (lo hace cumplir `tests/automation/test_sirius_convergence.py`).

### `regla-nueva-que-cambia-lo-que-otro-reconoce`

- **ADR-244** — pedirle al propietario algo nuevo, aquí llamar a Sirius por su (lo hace cumplir `tests/unit/test_memory_commands_domain.py`).

### `regla-nueva-sin-pasarla-por-los-casos-vivos`

- **ADR-231** — una guarda nueva que modela el camino común y prohíbe sin querer un caso legítimo que ya existía al escribirla (H-216 abierto con su arreglo en otra PR el mismo día que ADR-222), con la batería en verde y un defecto arreglado que el registro no puede cerrar. (lo hace cumplir `tests/automation/test_registro_de_defectos.py`).

### `tarea-periodica-sin-reloj`

- **ADR-201** — el único trabajo que mide los ciclos de este (sin prueba que lo haga cumplir: ninguna prueba: que el reloj dispare de verdad no lo puede).

### `tramite-que-solo-puede-hacer-una-persona-y-no-anade-comprobacion`

- **ADR-205** — el ciclo volvería a quedarse horas en verde esperando (lo hace cumplir `tests/automation/test_sirius_merge.py`).

### `turnos-en-las-instrucciones-sin-parada`

- **ADR-256** — un modelo pequeño seguiría el diálogo de sus instrucciones hasta su tope (lo hace cumplir `tests/unit/test_paradas_de_turno.py`).

Y **8** ADR declaran expresamente que no dejaron lección: 260, 257, 240, 236, 235, 234, 233, 232.

## Los bloques del motor

Registro: `docs/implementation/bloques_del_motor.yml`. No confundir con los 16 bloques del
producto Sirius 0.1, cerrados el 10-08-2026.

| Bloque | Estado | Título |
|---|---|---|
| E0 | cerrado | El permiso escrito para construir el motor |
| A1 | cerrado | Las reglas del juego, qué es un trabajo y qué saltos están prohibidos |
| S1 | cerrado | Experimento desechable, cómo guardar en disco sin perder ni duplicar |
| A2 | cerrado | El motor ya no olvida al reiniciarse |
| A3 | cerrado | El motor ya puede mirar GitHub, sin tocar nada |
| A4 | cerrado | Qué puede y qué no puede hacer cada rol, y la barrera de salida de datos |
| E1a | cerrado | Quién manda sobre cada tipo de trabajo, contrato v1.7 |
| A5 | cerrado | Distinguir charla de orden, presupuesto con corte, escalado al propietario |
| S2 | cerrado | Probar si el investigador externo funciona y qué cuesta |
| B1 | cerrado | Que Sirius investigue de verdad desde una orden |
| E1b | cerrado | Contrato v1.8, permitir al motor activar y vigilar |
| S3 | cerrado | Medir cuándo GitHub dice que algo terminó |
| C1 | cerrado | Que el motor desatasque solo lo que se cuelga |
| C2 | cerrado | Una orden tuya y no tocas GitHub hasta «fusiona» |
| C3 | cerrado | El mismo ciclo para documentos |
| C4 | cerrado | La auditoría dentro del motor |
| D1 | fuera_de_alcance | Pasar el mando de GitHub al motor, clase por clase |
| D2 | cerrado | Que el motor corra solo, siempre |
| D3 | fuera_de_alcance | Hablar con Sirius por Telegram |
| D4 | fuera_de_alcance | Partir un objetivo grande en bloques |

## Los defectos registrados

Registro: `docs/audits/registro_defectos.yml`. Solo se listan los que no están
cerrados; el recuento completo está arriba.

| Defecto | Estado | Título |
|---|---|---|
| H-202 | abierto | Una decision de no hacer algo no dejaba rastro, y una precondicion escrita antes que ella bloqueo trabajo real trece dias |
| H-203 | abierto | El banco solo sabia medir el camino con el motor encendido, asi que la linea base contra la que comparar no existia |

## Las ideas aparcadas y descartadas (ADR-208)

Registro: `docs/ideas/registro_de_ideas.yml`. Una idea que se pensó y no se hace
ahora vive aquí para que no vuelva como nueva: la aparcada declara qué tendría
que pasar para volver a mirarla, y la descartada, por qué no se hace.

| Idea | Estado | Título |
|---|---|---|
| I-001 | aparcada | Orquestacion grande y tuberias multiagente para construir Sirius |
| I-002 | descartada | n8n como orquestador de agentes para el motor |
| I-003 | descartada | Obsidian como capa de conocimiento de Sirius |
| I-004 | aparcada | Piezas de Memanto para la capa de memoria (motivo y desarchivar, exportacion Markdown, «cambiado desde», valid_from/valid_to persistidos, retencion como sugerencia) |
| I-005 | aparcada | Un agente que revise el repositorio por modulos, en rondas, cuando nadie esta delante |
| I-006 | promovida | Un cazador de contradicciones entre los documentos canonicos y el codigo |
| I-007 | promovida | Traer a local las 28 sesiones de Claude Code de la nube que le faltan a la auditoria |
| I-008 | aparcada | Un contador de rondas para la revision externa que el propietario trae a mano |
| I-009 | aparcada | Una via segura para que la decision del propietario llegue al diario de estado-del-motor |
| I-010 | aparcada | Habilidades y permisos sobre el ordenador del propietario (la antigua version 0.3, con el control visual del ordenador de EV-010) |
| I-011 | aparcada | Sirius como ayudante de ingenieria (delegacion supervisada, multiagente, consultas de ingenieria y participar en su propio desarrollo) |
| I-012 | aparcada | Automatizacion digital (captura de pantalla, flujos entre aplicaciones y control de programas; la mitad digital de la antigua 0.6) |
| I-013 | aparcada | Laboratorio (la mitad de laboratorio de la antigua 0.7) y un brazo SO-101 para aprender por imitacion |
| I-014 | aparcada | ROS 2 para organizar el software del robot |
| I-015 | aparcada | Voz a voz en la nube (un solo modelo que oye y habla, como OpenAI Realtime o Gemini Live) |
| I-016 | descartada | Librerias de memoria hechas (Mem0, Letta, Graphiti, LangMem) en vez de la memoria propia de Sirius |
| I-017 | aparcada | Mapas del espacio, SLAM y grafos de escena 3D |

## Las investigaciones: fotos con fecha, que caducan

Una investigación sirve para decidir qué preguntar, nunca para responder sobre
algo vivo (`AGENTS.md`). Cada una declara de qué depende para caducar.

| Fecha | Estado | Investigación | Caduca con |
|---|---|---|---|
| 2026-08-27 | PARCIALMENTE CADUCADA | [La medición real de NVIDIA contra Google, con las claves puestas](docs/investigaciones/2026-08-27-medicion-real-nvidia-contra-google.md) | las cuotas y límites de la capa gratuita de Google AI (si suben, Google merece la revancha; la condición está en el ADR-098); las cuotas de build.nvidia.com; el comportamiento de DuckDuckGo con las IP de los runners de GitHub; los nombres de modelo (gemini-3.5-flash, nemotron-3-nano-30b-a3b) |
| 2026-08-27 | PARCIALMENTE CADUCADA | [NVIDIA vs Google para el Investigador de Sirius](docs/investigaciones/2026-08-27-nvidia-vs-google-para-el-investigador.md) | nombres de modelo de cualquier proveedor; precios publicados; condiciones de uso de las capas gratuitas; qué modelos incluye la cuota de una cuenta concreta |
| 2026-08-28 | VIGENTE | [Examen lado a lado, Sirius contra la investigación profunda de ChatGPT](docs/investigaciones/2026-08-28-examen-lado-a-lado-sirius-contra-chatgpt.md) | la configuración del investigador (modelo, buscador, modo, idioma); la herramienta de investigación profunda de ChatGPT, que también cambia; los tres informes comparados, cada uno con su propia caducidad |
| 2026-08-28 | VIGENTE | [Investigación de la orden](docs/investigaciones/2026-08-28-orden-386-investiga-cuales-son-los-limites-actuales-de-la-capa-gratuit.md) | los datos y las fuentes que cita el informe; la fecha de esta ejecución: es UNA pasada del investigador, no un hecho estable |
| 2026-08-28 | VIGENTE | [Investigación de la orden](docs/investigaciones/2026-08-28-orden-392-investiga-y-compara-los-proveedores-de-api-de-modelos-nvidia.md) | los datos y las fuentes que cita el informe; la fecha de esta ejecución: es UNA pasada del investigador, no un hecho estable |
| 2026-08-31 | VIGENTE | [Investigación de la orden](docs/investigaciones/2026-08-31-orden-483-investiga-una-sola-pregunta-acotada-el-marco-de-agentes-herm.md) | los datos y las fuentes que cita el informe; la fecha de esta ejecución: es UNA pasada del investigador, no un hecho estable |
| 2026-09-11 | VIGENTE | [Flujos reales de agentes de código, comparados con el motor de Sirius](docs/investigaciones/2026-09-11-flujos-reales-de-agentes-comparados-con-el-motor.md) | el contenido de los trece repositorios citados, verificado el 11-09-2026 en su último commit; la documentación de Supermemory y Mem0 sobre Claude Code, Codex y ChatGPT, que cambia cada pocas semanas; los artículos, vídeos y fechas de publicación, que esta sesión no pudo abrir |
| 2026-09-11 | VIGENTE | [Qué memoria compartida para IAs existe ya hecha y probada, y si supera a la generada en el repositorio](docs/investigaciones/2026-09-11-que-memoria-compartida-para-ias-existe-ya-hecha-y-probada.md) | los precios y límites gratuitos de los servicios alojados (Mem0, Supermemory, Basic Memory Cloud, Letta Cloud, Zep); qué clientes admiten MCP y cómo (Claude Code, Codex, ChatGPT), que cambia cada pocos meses; las versiones y la actividad de cada proyecto, medidas el día de la clonación; la lista de herramientas que leen AGENTS.md |
| 2026-09-13 | PARCIALMENTE CADUCADA | [Memanto contra la capa de memoria de Sirius: qué está cubierto, qué a medias y qué es nuevo](docs/investigaciones/2026-09-13-memanto-contra-la-capa-de-memoria-de-sirius.md) | los ficheros de la capa de memoria que cita (src/sirius/domain/memory.py, decision.py, event.py, precedence.py, staged_engine_contracts.py, staged_engine_gates.py y src/sirius/adapters/persistence/models.py); si cambian, las líneas citadas dejan de valer; el estado de la línea de memoria (ADR-185 partió la puerta en tres interruptores el 13-09; las piezas A–D quedaron aparcadas con su momento de disparo, bitácora del ciclo, entrada 109); el propio repositorio moorcheh-ai/memanto, que no se leyó desde aquí |
| 2026-10-05 | VIGENTE | [Cómo aprenden hoy los robots y qué camino realista tiene Sirius](docs/investigaciones/2026-10-05-como-aprenden-los-robots-y-que-camino-tiene-sirius.md) | los precios de hardware y de GPU que cita (servos, micrófonos, brazos SO-101, alquiler en la nube); las versiones de LeRobot, de los modelos de visión, lenguaje y acción, y su soporte en Windows; la lectura de la ley de protección de datos que hace, si cambia su interpretación |
| 2026-10-05 | VIGENTE | [Sirius por dentro: cómo se organiza el software de un robot social y qué arquitectura le conviene](docs/investigaciones/2026-10-05-como-se-organiza-el-cerebro-de-un-robot-social.md) | los precios de nube que cita (OpenAI, Gemini, Deepgram, ElevenLabs, Azure), revisados entre julio y octubre de 2026; el soporte de ROS 2 en Windows y las versiones que nombra; las cifras de latencia y de detectores de turno, que son de sus fabricantes |
| 2026-10-05 | VIGENTE | [Memoria para Sirius: cómo hacer que un robot compañero recuerde bien, rápido y durante años](docs/investigaciones/2026-10-05-memoria-de-un-robot-companero-que-recuerde-bien-y-rapido.md) | las cifras de bancos públicos y de vendedores que cita (LoCoMo, LongMemEval, HaluMem, Mem0, Zep, Letta); los modelos de embeddings y sqlite-vec, y sus versiones; la capa de memoria de Sirius tal como estaba en main el 05-10-2026 (4ea76f35), que el informe no leyó: la describió el encargo |
| 2026-10-05 | VIGENTE | [Cómo darle a Sirius una personalidad propia, estable y reconocible](docs/investigaciones/2026-10-05-personalidad-propia-estable-y-reconocible-para-sirius.md) | los modelos y precios que cita, de pago y abiertos, que cambian cada pocos meses; las herramientas de voz y de turnos que nombra y sus licencias (Smart Turn, LiveKit, Chatterbox, Piper, Kokoro); el estado de los productos que repasa (Vector y wire-pod, aibo, EMO, Furhat, Moxie, Reachy Mini); la personalidad que pedía el encargo, ya cambiada por el propietario el 05-10-2026 (ADR-232) |
| sin fecha declarada | — | [Investigaciones](docs/investigaciones/README.md) | — |

## Los documentos, carpeta a carpeta

La fecha es la que cada documento **declara** en su cabecera; la vista no data
nada por su cuenta. «Sin fecha declarada» es un aviso, no un dato.

### `docs/audits`

**152 documentos**, 83 sin fecha declarada; el más reciente declara 2026-10-02.
Es la carpeta de la evidencia y crece a dos filas por ADR, así que la fila
de cada documento vive en un índice generado aparte,
[`docs/audits/INDICE.md`](docs/audits/INDICE.md), que escribe el
mismo comando y vigila la misma prueba que esta vista (ADR-218).

### `docs/canonical`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Estado canónico (desde el 06-10-2026 manda también la última sección: Sirius, el software del robot)](docs/canonical/STATUS.md) |

### `docs/evolution`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Artefactos aprobados - Evolución post-0.1 de Sirius (el DOCX es la foto del 22-07-2026; ver la nota al final)](docs/evolution/ARTIFACTS.md) |
| sin fecha declarada | [Auditoría cerrada - Plan de evolución de Sirius después de 0.1 (foto del 22-07-2026; ver la nota del 06-10-2026 al final)](docs/evolution/AUDIT.md) |
| sin fecha declarada | [Decisiones canónicas - Evolución post-0.1 de Sirius (desde el 06-10-2026 mandan EV-020 a EV-023, al final)](docs/evolution/DECISIONS.md) |
| 2026-10-06 | [Enmienda al Manual de Visión e Identidad v1.2: Sirius, el robot](docs/evolution/ENMIENDA_MANUAL_IDENTIDAD_2026-10.md) |
| 2026-10-06 | [Plan de Sirius, el robot](docs/evolution/PLAN_DEL_ROBOT.md) |
| sin fecha declarada | [Propuesta de separación entre Sirius y su motor de trabajo](docs/evolution/PROPUESTA_SEPARACION_SIRIUS_MOTOR.md) |
| 2026-10-08 | [Pruebas de aceptación de la 0.2 del robot](docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md) |
| 2026-10-13 | [Pruebas de aceptación de la 0.3 del robot](docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md) |
| 2026-10-18 | [Pruebas de aceptación de la 0.4 del robot](docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md) |
| sin fecha declarada | [Evolución de Sirius después de 0.1](docs/evolution/README.md) |
| sin fecha declarada | [Documento Rector - Evolución de Sirius después de 0.1 (enmendado por su §20 el 06-10-2026: Sirius es el software del robot)](docs/evolution/RECTOR.md) |
| sin fecha declarada | [Sirius AI Core y estrategia de modelos — recolección de ideas](docs/evolution/SIRIUS_AI_CORE_AND_MODEL_STRATEGY.md) |
| sin fecha declarada | [Arquitectura Técnica — Sirius 0.2 «Memoria útil» (sustituida el 06-10-2026 por la 0.2 del robot, ADR-232)](docs/evolution/SIRIUS_ARQUITECTURA_TECNICA_0.2_v0.1_PROPUESTO.md) |
| sin fecha declarada | [Plan de Pruebas de Aceptación — Sirius 0.2 «Memoria útil» (sustituido el 06-10-2026 por la 0.2 del robot, ADR-232)](docs/evolution/SIRIUS_PLAN_PRUEBAS_0.2_v0.1_PROPUESTO.md) |
| sin fecha declarada | [Definición de Producto — Sirius 0.2 «Memoria útil» (sustituida el 06-10-2026 por la 0.2 del robot, ADR-232)](docs/evolution/SIRIUS_PRODUCTO_0.2_MEMORIA_UTIL_v0.1_PROPUESTO.md) |
| sin fecha declarada | [Estado - Evolución post-0.1 de Sirius (desde el 06-10-2026 manda la última sección: Sirius, el software del robot)](docs/evolution/STATUS.md) |

### `docs/evolution/history`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Sirius — Tarjeta de referencia](docs/evolution/history/PROPUESTA_ALCANCE_POST_0_1_v2.md) |

### `docs/implementation`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Agentes de Sirius — desde dónde se invocan](docs/implementation/AGENTES_SUPERFICIE_DE_INVOCACION.md) |
| sin fecha declarada | [SIRIUS — Matriz de oportunidades de agentes (Fase 0)](docs/implementation/AGENT_OPPORTUNITY_MATRIX.md) |
| sin fecha declarada | [AUDITOR AGENT v0 — Especificación reproducible del agente](docs/implementation/AUDITOR_AGENT_V0.md) |
| sin fecha declarada | [SIRIUS - Plan del flujo general de automatización](docs/implementation/AUTOMATION_FLOW_PLAN_SIRIUS_0.1.md) |
| sin fecha declarada | [SIRIUS - Contrato operativo de automatización](docs/implementation/AUTOMATION_OPERATING_CONTRACT.md) |
| sin fecha declarada | [SIRIUS — Evidencia de prueba de humo de automatización](docs/implementation/AUTOMATION_SMOKE_EVIDENCE_20260719.md) |
| sin fecha declarada | [SIRIUS - Máquina de estados del flujo automático](docs/implementation/AUTOMATION_STATE_MACHINE_SIRIUS_0.1.md) |
| sin fecha declarada | [B13 — Empaquetado reproducible de Sirius 0.1 para Windows 11 x64](docs/implementation/B13_PACKAGING.md) |
| sin fecha declarada | [B14 — Windows sin clave](docs/implementation/B14_WINDOWS_SIN_CLAVE.md) |
| sin fecha declarada | [B4 — Plan de ejecución operativo](docs/implementation/B4_EXECUTION.md) |
| sin fecha declarada | [Banco de evaluación de agentes — diseño v0](docs/implementation/BANCO_DE_EVALUACION_DISENO.md) |
| sin fecha declarada | [Bloque B — ¿Sirven las suscripciones para un runner multimodelo, o hacen falta claves de API?](docs/implementation/BLOQUE_B_SUSCRIPCIONES_O_CLAVES.md) |
| sin fecha declarada | [Cloud Smoke Test Evidence — 2026-07-18](docs/implementation/CLOUD_SMOKE_EVIDENCE_20260718.md) |
| sin fecha declarada | [Prueba de humo de Claude Code cloud](docs/implementation/CLOUD_SMOKE_TEST.md) |
| sin fecha declarada | [Dónde estamos](docs/implementation/DONDE_ESTAMOS_2026-08-21.md) |
| sin fecha declarada | [Método de interrogatorio](docs/implementation/METODO_INTERROGATORIO.md) |
| sin fecha declarada | [Plan de implementación por verticales](docs/implementation/PLAN.md) |
| sin fecha declarada | [SIRIUS 0.2 — Paquete operativo de spikes de ADR-001](docs/implementation/SIRIUS_0.2_ADR001_PAQUETE_OPERATIVO_SPIKES_v1.0.md) |
| sin fecha declarada | [SIRIUS — Routines genéricas de automatización 0.1](docs/implementation/SIRIUS_GENERIC_ROUTINES_0.1.md) |
| 2026-08-15 | [Sirius Work Engine — Arquitectura mínima implementable](docs/implementation/SIRIUS_WORK_ENGINE_ARQUITECTURA_MINIMA.md) |
| 2026-08-15 | [Sirius Work Engine — Inventario y reconciliación del estado real](docs/implementation/SIRIUS_WORK_ENGINE_INVENTARIO.md) |
| 2026-08-15 | [Sirius Work Engine — Plan mínimo de implementación](docs/implementation/SIRIUS_WORK_ENGINE_PLAN_IMPLEMENTACION.md) |
| sin fecha declarada | [Trazabilidad de las pruebas de aceptación, personalidad y seguridad](docs/implementation/TRAZABILIDAD_PA_SP.md) |
| sin fecha declarada | [V8 — Ejecución, puertas y evidencia](docs/implementation/V8_EXECUTION.md) |
| sin fecha declarada | [SIRIUS — Auditoría de procesos de trabajo (Fase 0)](docs/implementation/WORK_PROCESS_AUDIT.md) |

### `docs/implementation/model_studio`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [SIRIUS · MODEL STUDIO · MÓDULO CAPTURA](docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_CAPTURA_INVESTIGACION.md) |
| sin fecha declarada | [SIRIUS · MODEL STUDIO · MÓDULO CAPTURA](docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_PRIMERA_PRUEBA_CAPTURA.md) |
| sin fecha declarada | [SIRIUS · MODEL STUDIO](docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_RECONCILIACION_v1.0_PROPUESTA.md) |
| sin fecha declarada | [SIRIUS · MODEL STUDIO](docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_UI_001_INTERFAZ_v1.0_APROBADA.md) |

### `docs/operations`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Incorporación de Claude al Proyecto Sirius](docs/operations/CLAUDE_PROJECT_ONBOARDING.md) |
| sin fecha declarada | [Base de conocimiento de Claude sobre el Proyecto Sirius](docs/operations/CLAUDE_SIRIUS_KNOWLEDGE_BASE.md) |
| sin fecha declarada | [Cómo se usa el motor de Sirius](docs/operations/MOTOR_DE_SIRIUS.md) |

### `docs/robotics/head`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Artefactos aprobados - Sirius HEAD-R1 (el DOCX es la foto del 22-07-2026; ver la nota al final)](docs/robotics/head/ARTIFACTS.md) |
| sin fecha declarada | [Auditoría y cierre documental - Sirius HEAD-R1 (foto del 22-07-2026; ver la nota del 06-10-2026 al final)](docs/robotics/head/AUDIT.md) |
| sin fecha declarada | [Decisiones canónicas - Sirius HEAD-R1 (desde el 06-10-2026 manda D-HEAD-14, al final)](docs/robotics/head/DECISIONS.md) |
| sin fecha declarada | [Sirius HEAD-R1](docs/robotics/head/README.md) |
| sin fecha declarada | [Documento Rector — Cabeza Robótica Sirius HEAD-R1 (enmendado al final el 06-10-2026: HEAD-R1 es el cuerpo de Sirius)](docs/robotics/head/RECTOR.md) |
| sin fecha declarada | [Estado - Sirius HEAD-R1 (desde el 06-10-2026 manda la última sección)](docs/robotics/head/STATUS.md) |

### `(raíz)`

| Fecha | Documento |
|---|---|
| sin fecha declarada | [Instrucciones para agentes de programación](AGENTS.md) |
| sin fecha declarada | [Registro de cambios](CHANGELOG.md) |
| sin fecha declarada | [Claude Code](CLAUDE.md) |
| sin fecha declarada | [Forma de trabajo](CONTRIBUTING.md) |
| 2026-08-10 | [Sirius 0.1](README.md) |
| sin fecha declarada | [Estado actual del repositorio](REPOSITORY_STATUS.md) |
