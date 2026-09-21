# Nota de arranque — la auditoría de la forma de trabajar, segunda edición: lo que la primera no podía ver

- Fecha: 2026-09-19
- Rama: `claude/sirius-collaboration-rir6r6`
- ADR previsto: ninguno todavía. Una auditoría produce un mapa y
  recomendaciones; si de ella sale una decisión, esa decisión dejará su propio
  ADR (mismo criterio que `docs/implementation/WORK_PROCESS_AUDIT.md`,
  «Declaración de alcance de decisión»).
- Incidencia: ninguna.
- Decisión que la autoriza: el propietario, el 15-09-2026 («vamos por la
  auditoría de mi forma de trabajar») y el 19-09-2026 («arranca con la nota»).
  Se escribe aquí para que el encargo no viva solo en una conversación
  (familia `decision-que-solo-vive-en-una-conversacion`, ADR-202).

Publicada ANTES de abrir ninguna conversación exportada, según ADR-001.

## El encargo, con las palabras del propietario

15-09-2026: auditar su forma completa de trabajar en Sirius —**conversación,
ideas, debate, investigación, decisiones, documentación, ejecución y
cierre**—. La recogida la lleva la IA; el propietario no lee ni clasifica su
historial. Las skills quedan aparcadas hasta que la auditoría diga qué merece
mecanizarse, si es que algo lo merece.

## Alcance

**Dentro:** Sirius aplicación (`src/sirius/`) y Sirius motor
(`src/sirius_engine/`, `scripts/automation/`, `.github/workflows/`), y la forma
de trabajar del propietario alrededor de los dos.

**Fuera, por decisión del propietario del 19-09-2026:** la cabeza robótica
HEAD-R1 y el laboratorio físico. Sus palabras, ese día: ese trabajo es suyo;
ahí la IA solo le da información y él va haciendo las cosas; «no hay que
revisar nada». Consta que hay avances —un primer prototipo de ojos, según él—
y `docs/robotics/head/STATUS.md` sigue diciendo «INACTIVO / NO AUTORIZADO»
desde el 22-07-2026. La discrepancia se anota y **no se corrige aquí**: no es la
vertical de esta auditoría.

## Lo que ya existe, y por qué esta es una segunda edición

`docs/implementation/WORK_PROCESS_AUDIT.md` (11–12 de agosto de 2026,
COMPLETADA) inventarió **21 procesos** (PROC-001…021), una taxonomía A–F, diez
puntos de pegamento (G1–G10) y un ranking de dónde se va el tiempo humano. No se
rehace: se **revalida** y se **extiende**.

Las ocho categorías del propietario, sobre las fichas de agosto:

| Categoría del propietario | Ficha de agosto | Estado |
|---|---|---|
| investigación | PROC-014 | tiene ficha |
| decisiones | PROC-011 | tiene ficha |
| documentación | PROC-009, 010, 012, 013 | tiene ficha |
| ejecución (y su administración) | PROC-002…007, 020, 021 | tiene ficha |
| cierre | PROC-004, PROC-009 | tiene ficha |
| **conversación** | — | **sin ficha** |
| **ideas** | — | **sin ficha** |
| **debate** | — | **sin ficha** |

PROC-001 (redactar el work item) y PROC-019 (transporte de contexto entre
herramientas) tocan la conversación por sus bordes —lo que entra a GitHub y lo
que se lleva de una herramienta a otra—, pero ninguna ficha describe cómo una
idea se debate hasta convertirse en una decisión. Y no es un olvido: la
auditoría de agosto lo declaró fuera de su vista en sus «Límites de
observabilidad» 1 y 2 —de ChatGPT, «cero trazas directas»; de las sesiones
interactivas, «solo se ven sus efectos», y la dirección verbal del propietario
«es no observable»—. Lo que el propietario más quiere ver es exactamente lo que
aquella auditoría no podía ver.

Y está fechada: inspeccionó `docs/decisions/` con siete ADR; hoy va por el
ADR-202. Sus cinco eras terminan el 11-08 y el motor entero (bloques E0…D2 de
`docs/implementation/bloques_del_motor.yml`) nació después.

## Fuentes

**En mano a 19-09-2026:**

- El árbol de `main` en `3062a31`: ADR-008…202 —que narran decisiones y, a
  menudo, el debate que las precedió— y `MEMORIA.md`.
- La memoria de sesión (ADR-172), espacio `repo_sirius__e87a5bbe75fe00b6`: 170
  recuerdos y 31 documentos a 15-09. Existe desde el 11-09; de antes no hay
  nada ahí.
- El listado de sesiones de Claude Code de la cuenta: 42, agregados más abajo.
  Solo metadatos; la herramienta no devuelve mensajes.
- La exportación de datos de Anthropic (conversaciones de claude.ai), obtenida
  por el propietario entre el 15 y el 19-09. **No se ha abierto.**

**Pendientes:**

- Las transcripciones locales de Claude Code, en `%USERPROFILE%\.claude\projects\`
  del ordenador del propietario, cuando las comprima. Son la única fuente de
  las sesiones que corrieron en su máquina.
- La exportación de ChatGPT: pedida, «tardará días», no ha llegado. Es la
  fuente de la era en que ChatGPT era «el panel de mando» (agosto, línea
  temporal, era 1). Hasta que llegue, esa parte se ve solo por sus efectos.

**Dónde se trabajan:** las exportaciones crudas no entran en este repositorio,
que es público a propósito (ADR-171), ni en la memoria de sesión tal cual. Se
analizan en el espacio temporal de la sesión; al repositorio van conclusiones,
recuentos y citas cortas, nunca conversaciones enteras.

## 1. ¿Dónde vive el fallo y dónde va el arreglo?

El «fallo» que se estudia no es un defecto de código: es la parte de la forma
de trabajar que no deja traza estructurada y por eso se pudre sin que nadie lo
note. Tres ejemplos ya pagados, con su ADR: una decisión de no hacer M17 que no
constaba en ningún sitio y bloqueó trece días una incidencia (ADR-202); una
regla dada de viva voz —«no se borra nada»— que no estaba escrita (ADR-195);
una pregunta al propietario que nadie volvió a poner delante en veinte días
(ADR-198). Los tres nacen en la conversación y mueren en el hueco entre la
conversación y el repositorio.

El «arreglo» de esta fase es un mapa: qué procesos hay hoy, cuáles de los de
agosto siguen vivos, cuáles nacieron después, y por dónde se escapan las cosas.
Vive en `docs/audits/`.

**¿Puede el sitio del arreglo OBSERVAR el fallo?** En agosto, no: la
conversación era invisible desde el repositorio. Hoy, **a medias, y es la
primera vez**: la exportación de Anthropic y las transcripciones locales hacen
observable el lado Claude de la conversación; la memoria de sesión hace
observable el contexto desde el 11-09; ChatGPT sigue ciego hasta que llegue su
exportación; y la cabeza del propietario, su trabajo en Windows no confirmado y
su tiempo real siguen sin ser observables desde ningún sitio. Todo lo que caiga
ahí se marca como hipótesis o como límite, nunca como hecho. Es la misma regla
que en agosto, y sigue siendo la correcta.

## 2. ¿Qué NO va a garantizar esto?

- **No garantiza un inventario exhaustivo.** Sin ChatGPT, la era 1 (julio) y
  toda redacción de mandatos que ocurriera allí se ven por sus efectos. Se dirá
  dónde falta.
- **No mide tiempo humano.** Sigue sin haber registro de tiempo; toda duración
  es latencia de atención (cuándo respondió), no esfuerzo. Las cifras estimadas
  irán marcadas EST, como en agosto.
- **No lee todas las conversaciones.** Se lee una muestra, y la muestra se
  declara en la adenda de esta nota ANTES de abrir la primera (ver «La
  muestra»).
- **No elige skills.** Produce el mapa y, como mucho, candidatos; instalar o
  construir una skill es una decisión posterior del propietario, con su ADR.
- **No audita la cabeza robótica.** Fuera por decisión suya.
- **No repara nada.** Si aparece un defecto del motor o de la aplicación, se
  registra donde toca (`docs/audits/registro_defectos.yml`, ADR-182 y ADR-192)
  y no se arregla dentro de esta auditoría.
- **No garantiza que la taxonomía sea la buena.** Probarla es parte del
  trabajo: si dos rondas seguidas destapan la misma familia de proceso omitida,
  se para de añadir fichas y se revisa la taxonomía entera (regla de las dos
  rondas, ADR-001).

## 3. Criterio de parada — decidido ahora, antes de abrir ninguna conversación

Terminada cuando:

1. **Cada una de las 21 fichas de agosto tiene veredicto fechado**: `vigente`,
   `caducada` (con qué la mató: ADR, workflow o bloque) o `transformada` (en
   qué), con la evidencia citada. Ninguna se da por vigente por inercia.
2. **Las tres categorías sin ficha —conversación, ideas, debate— tienen al
   menos una ficha cada una**, construida con las fuentes nuevas, o llevan
   escrito «no observable ni con las fuentes nuevas» y por qué.
3. **Todo proceso repetido nacido después del 11-08** (dos o más ocurrencias
   observadas) tiene ficha, con el mismo formato que las de agosto.
4. **Las ocho categorías del propietario quedan mapeadas** sobre la taxonomía,
   y la taxonomía sale confirmada o revisada. La revisión la dispara la regla
   de las dos rondas, no el gusto.
5. **Cada afirmación cita su fuente** —fichero, ADR, sesión, recuerdo— o va
   marcada como EST o hipótesis. Las cifras van ancladas al árbol o a la fecha
   que las produjo (ADR-154).
6. **Hay un ranking de dónde se va la atención del propietario**, con el mismo
   límite declarado que en agosto.
7. **Se detiene sin elegir skills.** Ese es el siguiente paso, y es suyo.
8. **Se detiene también si la muestra declarada se agota** sin cumplir el
   punto 2: entonces la conclusión es «con estas fuentes no se ve», que es una
   respuesta, y se escribe.

## 4. ¿Qué haría el fallo imposible en vez de improbable?

Hay que separar dos fallos.

**El de la auditoría misma** —afirmar más de lo que el dato sostiene, la
familia de la PR #136—: lo hacen improbable, no imposible, cuatro cosas de esta
nota: la muestra declarada antes de leer, la cita obligatoria por afirmación,
la regla de las dos rondas y el criterio de parada publicado. No hay guardián
automático que vigile la prosa de `docs/` contra el árbol (ADR-177 lo deja
dicho), así que lo sostiene el método, no un mecanismo.

**El de fondo** —que lo que se decide o se acuerda en una conversación no
llegue a ningún sitio—: **esta auditoría no lo hace imposible; lo hace
visible.** Lo que lo haría imposible es una decisión posterior sobre dónde y
cuándo se escribe lo que se dice de viva voz, y esa decisión no se toma aquí.
Se dice ahora para no venderla después.

## La muestra (se rellena en adenda ANTES de leer)

La exportación de Anthropic no se ha abierto y su tamaño no se conoce. Antes
de leer la primera conversación se añadirá aquí una adenda con: el recuento
total y el rango de fechas de la exportación (primer barrido, solo metadatos),
el criterio de selección de la muestra —por fecha y por tema, fijado antes de
ver contenido— y el tamaño resultante. Lo mismo para las transcripciones
locales cuando lleguen.

## Primera evidencia: las 42 sesiones de Claude Code de la cuenta

Obtenida el 15-09-2026 y repetida el 19-09 desde esta sesión con
`list_sessions(mine=true)`. Solo metadatos: título, fechas, origen, entorno,
modelo, rama de salida y un resumen de cierre de una línea. Ningún mensaje. El
índice completo por sesión se entregó al propietario como fichero y no se
publica aquí; el coste por sesión existe como campo y se excluye de este
documento público a propósito.

| | |
|---|---|
| Sesiones | **42**, de 2026-07-14 a 2026-09-15 |
| Por mes | julio 27 · agosto 8 · septiembre 7 |
| Por origen | `ios` 25 · `web_claude_ai` 10 · `claude_code_cli` 5 · `claude_code_vscode` 1 · sin origen declarado 1 |
| Por entorno | nube 35 · puente con su ordenador 7 |
| Con rama de salida | 37 de 42 |
| Cierre declarado | `review_ready` 24 · `need_input` 6 · `completed` 4 · `failed` 2 · sin resumen 6 |

Dos lecturas que salen solas de la tabla, y que son **hipótesis a contrastar**,
no conclusiones:

- **La mayoría de las sesiones se abrieron desde el móvil** (25 de 42). Si el
  contenido lo confirma, la forma de trabajar dominante no es «en el ordenador
  con el código delante», y eso cambia qué procesos merecen mecanizarse.
- **Seis sesiones terminaron con la IA esperando una respuesta que no llegó**
  (`need_input`). Dos son del 11-09, abiertas desde el escritorio el día en que
  se instaló la memoria de sesión y sin tarea: probablemente pruebas de
  instalación. Las otras cuatro esperaban una decisión con nombre —cinco
  aprobaciones, una propiedad, una de tres opciones—. Es la forma de la familia
  `pregunta-al-propietario-que-nadie-vuelve-a-poner-delante` (ADR-198), vista
  ahora en las sesiones y no solo en las incidencias. Si el contenido lo
  confirma, es una ficha nueva.

Lo que la tabla NO dice: cuánto duró de verdad cada sesión, qué se decidió
dentro, ni cuántas conversaciones de ChatGPT hubo en paralelo.

## Hipótesis a contrastar (escritas antes de leer, para no descubrirlas después)

Formadas leyendo solo el árbol, `MEMORIA.md`, los agregados de arriba y la
memoria de sesión. Si el contenido las desmiente, se escribe que las desmintió.

- **H1 — la revisión externa traída a mano.** El propietario lleva hallazgos de
  ChatGPT o de Codex a la sesión de Claude, y de vuelta. Señal: la nota del
  12-09 en la memoria de sesión («cinco hallazgos, los cinco ciertos, cero
  falsos»). ADR-156 automatizó el tramo Codex → tubería; el tramo ChatGPT →
  sesión sigue siendo una persona pegando texto.
- **H2 — el lote de decisiones antes de dormir.** Varias decisiones tomadas de
  golpe en conversación para que el trabajo nocturno no se pare, convertidas a
  ADR después. Señal: la nota del 14-09 en la memoria de sesión, y **veinte
  ADR** fechados entre el 13 y el 14 de septiembre.
- **H3 — el propio ritual es un proceso con coste.** «Nota de arranque →
  evidencia → ADR» lo hace hoy el propietario o la sesión en su nombre: 27
  notas de arranque y 51 evidencias en `docs/audits/`, 196 ficheros de ADR en
  `docs/decisions/`. No estaba en las fichas de agosto porque nació con ADR-001
  tres días antes de que aquella auditoría empezara.
- **H4 — partir un objetivo grande es conversación.** Lo hace la sesión
  interactiva (ADR-089, ADR-198), luego es un proceso conversacional repetido y
  sin ficha.
- **H5 — reconstruir contexto ha cambiado de mecanismo.** PROC-013 sigue
  existiendo, pero `MEMORIA.md` y la memoria de sesión (ADR-171, ADR-172) han
  cambiado cómo se hace; la ficha de agosto está caducada en el mecanismo
  aunque no en la existencia del proceso.

## Declaración de alcance de decisión

Este trabajo produce un mapa y recomendaciones, no decisiones. No se registra
ADR al abrirlo. Si al cerrarlo el propietario decide algo —qué mecanizar, qué
no, dónde se escriben las decisiones de viva voz—, esa decisión dejará su ADR,
creado con la skill `adr`.

## Adenda — la muestra, fijada antes de leer (2026-09-19 23:55 UTC)

**Lo recibido el 19-09 y el 20-09**, todo fuera del repositorio, en el espacio
temporal de la sesión: el manifiesto de la exportación de Anthropic (seis
zips); `conversations.json` (38 conversaciones de claude.ai, del 12-06 al
19-09: junio 10, julio 13, agosto 7, septiembre 8; 1 234 mensajes, 618 del
propietario y 616 del asistente; 1 482 k caracteres de texto; 334 adjuntos);
los metadatos ligeros (cuenta y 17 inicios de sesión entre el 12-06 y el
15-09: 8 desde iPhone, 9 desde Windows —Edge 5, aplicación de escritorio 3,
Chrome 1—); los siete proyectos de claude.ai («Sirius 0.2», 14 documentos;
«Robótica Sirius», 5 documentos y una plantilla; los demás vacíos o ajenos);
la memoria de claude.ai (22 ficheros, tres memorias de proyecto y una de
conversaciones); las reflexiones mensuales generadas por claude.ai (junio y
julio; no hay de agosto ni de septiembre) y la lista de feedback, vacía. Los
artefactos («frames») no se han subido: no describen el proceso; se pedirán
si una conversación de la muestra los necesita.

**Lo visto antes de fijar la muestra, y nada más:** de cada conversación, el
título, las fechas, el número de mensajes, el tamaño y los primeros ~230
caracteres del `summary` que la exportación trae generado; las dos
reflexiones mensuales; la estructura de la memoria (rutas y tamaños, no
contenido); los nombres de los documentos de los proyectos. **Ningún
mensaje.** Se declara porque las reflexiones y los resúmenes son fuentes
secundarias, escritas por un modelo, y podrían orientar la lectura.

**Criterio.** Por tema, decidido sobre título y resumen; por fecha, todo el
rango. La muestra es la población dentro del alcance: no se muestrea dentro
de ella.

- **Dentro — 12 conversaciones, 237 mensajes, ~472 k caracteres:** Bloque 01
  de Sirius 0.2 (23-07 00:48); Auditoría exhaustiva de documento (23-07
  01:16; 101 mensajes, 278 k, 91 adjuntos); Límite de uso consumido (24-07
  00:10); Automatización con agentes y revisión por bloques (24-07 03:13);
  Investigación de capacidades de plataformas IA (24-07 05:17); MCP para
  Sirius (04-08); Evidence discipline architecture for Claude Code (07-08);
  Integrar skills de memoria en Sirius (16-08); Configurar Ultracode en
  sesiones de cloud (21-08); Repositorio Sirius en GitHub (04-09); Niveles
  ocultos del ingeniero de IA (11-09); N8N y Claude para agentes de Sirius
  (16-09).
- **Fuera — la cabeza robótica, 8:** Primera sesión del proyecto (22-07),
  Clarificación del orden de fases (22-07), Segunda sesión (24-08), Sesión
  tres (24-08), Diseño de cuello móvil (02-09), Documentales de robots y IA
  caseros (06-09), Sesión 4 (18-09), Diseño de mecanismo de ojos v0.2
  (19-09). Decisión del propietario del 19-09-2026.
- **Fuera — proyectos ajenos a Sirius, 13:** la barbería Zona Cero (6), el
  canal de YouTube y Mente Financiera (3), un sitio de ropa (1), una decisión
  personal (1), Warzone (1), un coche (1), el trabajo (1).
- **Sin texto en la exportación, 5:** del 18-07 al 22-07, sin título, sin
  resumen y sin bloques de contenido (2, 4, 8, 80 y 10 mensajes). No se
  pueden leer: quedan fuera **por imposibilidad, no por criterio**. Se anota
  que la de 80 mensajes (21-07 21:15) coincide con la noche en que nació el
  contrato de automatización, y que ese hueco existe.
- **Casos límite, decididos ahora:** «Niveles ocultos del ingeniero de IA»
  entra porque trata de cómo el propietario trabaja con IA aunque mezcle
  temas; «Documentales de robots» sale como robótica y contenido.

**Cómo se lee.** Las 12 enteras, en orden cronológico. Los mensajes del
propietario, íntegros; los del asistente, íntegros hasta 2 500 caracteres y
recortados después con la cuenta de lo omitido, porque lo que se audita es la
forma de trabajar del propietario y no la prosa del modelo; los adjuntos, por
nombre y tamaño, no por contenido. **Después** de las 12, y no antes, se leen
como fuentes secundarias la memoria de claude.ai y las reflexiones completas,
para contrastar sin anclar la lectura. De cada conversación se extrae lo
mismo: (1) cómo entra la idea —voz, captura, documento, pregunta—; (2) el
debate: correcciones, rechazos y decisiones tomadas dentro; (3) qué sale y
hacia dónde —repositorio, incidencia, ADR, otra herramienta, ningún sitio—;
(4) marcas de tiempo; (5) reglas de trabajo que el propietario enuncia. Toda
cita que llegue al repositorio será corta y sin datos personales.

**Parada de esta lectura:** cumplido el punto 2 del criterio de parada —las
tres fichas, o «no observable» escrito— o agotadas las 12.

**Lo que tendrá su propia adenda al llegar**, con el mismo criterio: las
transcripciones locales de Claude Code —entran solo las carpetas del
repositorio de Sirius— y la exportación de ChatGPT.

## Adenda 2 — la segunda muestra: las transcripciones de Claude Code (2026-09-20 00:52 UTC)

**Lo recibido el 20-09**, fuera del repositorio, en el espacio temporal de la
sesión: un zip **local** (0,7 MB) con 8 sesiones `.jsonl` de
`%USERPROFILE%\.claude\projects\` —todas de la carpeta del repositorio de
Sirius— y `history.jsonl`, las **72 órdenes tecleadas** por el propietario en
Claude Code local entre el 13-07 y el 11-09; y un zip de la **nube** (3,6 MB)
con **6 de las 34 sesiones** de la nube que se intentaron traer con
`claude --teleport` en un clon aparte. Por qué solo seis, no se sabe todavía:
queda como límite hasta que el propietario confirme si el bucle terminó o se
cortó. Antes de traerlas, el propietario subió la retención local a 3 650
días: hasta hoy, Claude Code borraba las sesiones locales a los 30, y por eso
las 8 locales que quedan son del 16-08 en adelante.

**Lo visto para clasificar, y nada más:** el nombre de la carpeta (que es el
repositorio), las fechas, el número de registros por tipo, el título generado
por la herramienta, la rama, la versión, los nombres de las herramientas
invocadas con su recuento, y el tamaño del texto del propietario y del
asistente. **Ningún mensaje.**

**Criterio.** Por carpeta: entra todo lo que esté en una carpeta del
repositorio de Sirius, que es todo lo recibido.

- **Dentro — locales (8 + history):** dos con sustancia, 17-08 (rama
  `evidence/adr001-spikes`, 1 h 30, 13 mensajes del propietario y 162 del
  asistente) y 18-08 (rama `herramienta/skill-adr`, 3 h 35, 21 y 183); seis
  pequeñas del 16-08 y del 11-09 (instalar la memoria entre sesiones, probar
  Supermemory); y `history.jsonl` entero.
- **Dentro — nube (5 de las 6):** dos pruebas de julio (18-07 y 23-07, las
  primeras sesiones de Claude Code en la nube; entran aunque sean cortas), y
  tres largas: rama `feat/b13-reproducible-windows-package` (del 08-08 en
  adelante; 100 mensajes del propietario, 685 del asistente; probablemente la
  sesión que cerró la PR #122), rama `claude/ciclo-pendientes-prs-issues`
  (del 10-08; 38 y 604; probablemente «Pendientes del ciclo») y rama
  `claude/adr002-tol209-forensic-audit` (registros desde el 19-09; 35 y 230;
  probablemente la cola de «Auditoría forense TOL-209», que figuraba en marcha
  desde julio). La correspondencia con los títulos del índice de sesiones es
  por rama y fecha, no por identificador: se marca como probable.
- **Fuera por descarte:** el fichero del 20-09 con tres mensajes, que es el
  propio teleport de prueba.
- **Fuera por imposibilidad:** las 28 sesiones de la nube que no bajaron, y
  todo lo local anterior al 16-08, borrado por la retención de 30 días.

**Cómo se lee**, adaptado a transcripciones de Claude Code, que son sobre todo
tráfico de herramientas: los mensajes del propietario, íntegros; el texto del
asistente hasta 2 500 caracteres; de cada llamada a herramienta, solo su
nombre y la primera línea de su entrada (el comando, la ruta); los resultados
de herramienta **no se leen** —son el repositorio y salidas de comandos—, con
dos excepciones: los que registran una denegación de permiso o un rechazo del
propietario, y las respuestas del propietario a una pregunta de la IA, que se
leen enteras porque son dirección suya. Los registros de sistema, adjuntos,
modo y coste se cuentan, no se leen.

**Qué se extrae:** los cinco campos de la adenda 1 y un sexto: (6) **cómo
dirige la sesión** —permisos concedidos y denegados, interrupciones,
respuestas a preguntas de la IA, órdenes de corrección—, que es exactamente el
límite 2 de la auditoría de agosto: «la dirección verbal del propietario
dentro de la sesión es no observable».

**Orden:** `history.jsonl` → las dos locales con sustancia → las pequeñas →
las tres largas de la nube, de menor a mayor → las dos de julio.

**Parada:** revisadas C-01, C-02, C-03 y N-03 con lo que estas fuentes añadan
o desmientan, y escrita la sección «el lado de la ejecución»; o agotadas las
fuentes.

## Adenda 3 — la tanda de skills: cuatro preguntas y criterio de parada, escritos antes de elegir ningún candidato (2026-09-20 15:09 UTC)

Esta adenda no amplía la muestra: abre un trabajo **derivado** de la auditoría.
El propietario lo pidió con estas palabras el 20-09: «tenemos si o sí q hacer q
se creen skills como en Hermes para no tener q buscar mil veces como hacer la
misma tarea o trabajo y poder aprender dia a dia de lo q hacemos y de cómo
trabajamos». Los candidatos salen de las fichas de esta auditoría, así que su
nota de arranque va aquí, y se escribe **antes** de mirar cuáles pasan el
filtro.

**Las tres condiciones que tiene que cumplir un candidato, a la vez** (fijadas
ahora, no después de ver la lista):

1. **Se repite**: al menos dos ocurrencias fechadas en la auditoría o en el
   árbol, no una impresión.
2. **Tiene fricción medida**: un número, una fecha o un defecto registrado que
   diga cuánto cuesta hacerlo mal o buscarlo otra vez.
3. **La decisión no es del propietario**: es técnica o de lógica, y por tanto
   entra en lo que ADR-204 dice que se resuelve sin preguntarle.

### 1. ¿Dónde vive el fallo y dónde va el arreglo?

El fallo tiene dos caras. La primera: lo que se repite se vuelve a averiguar
desde cero en cada sesión, porque el conocimiento está repartido entre
`AGENTS.md`, 210 ADR y las fichas de esta auditoría, y nadie carga 210 ADR. La
segunda, peor: **un documento que nadie mantiene se pudre en silencio**, y de
eso hay medida en este mismo repositorio —PROC-010, la base de conocimiento que
se quedó nueve versiones de contrato atrás sin que nadie lo notara, porque
nadie la hacía y nadie la leía.

El arreglo de la primera cara vive en el propio texto de las skills, dentro de
lo que falla; el de la segunda **no puede** vivir ahí: un documento no observa
su propia podredumbre. Por eso la guarda va en `tests/`, fuera del documento, y
corre en la batería de cada sesión. La pregunta que caza la raíz —¿puede el
sitio del arreglo OBSERVAR el fallo que arregla?— se responde sí solo para la
guarda: una prueba que abre cada ruta citada por una skill ve exactamente la
cita que dejó de resolver.

### 2. ¿Qué NO va a garantizar esto?

- **No garantiza que nadie las cargue.** Quien decide cargar una skill es el
  modelo, leyendo su descripción; no hay puerta que lo obligue, igual que no la
  hay para `AGENTS.md`.
- **No garantiza que el contenido sea correcto**, solo que lo que cita existe.
  Una skill puede tener todas sus rutas vivas y el texto obsoleto.
- **No mide si ahorran tiempo.** No hay instrumento para eso en este
  repositorio y no se va a inventar uno aquí.
- **No cubre la cabeza robótica ni el laboratorio físico**, fuera de alcance
  desde el 19-09 por decisión del propietario.
- **No convierte en skill lo que pasó una vez.** Un caso único se queda en su
  ADR.

### 3. Criterio de parada — decidido ahora, antes de escribir una sola línea

| # | Si ocurre esto | Entonces |
|---|---|---|
| 1 | Una skill no se puede escribir sin repetir palabra por palabra lo que ya dice `AGENTS.md` | no es una skill, es un puntero: se descarta |
| 2 | La guarda no falla al mutar cada una de sus reglas | la guarda es vacua: no entra |
| 3 | Pasan el filtro más de siete candidatos | entran los cinco de fricción mayor; el resto va a `docs/ideas/registro_de_ideas.yml` como aparcado |
| 4 | La batería completa no vuelve verde | no se empuja nada |
| 5 | La cadena de comprobación de esta misma sesión se alarga por culpa de esto | la skill de la cadena ha fracasado en su propósito y se revisa |

### 4. ¿Qué haría el fallo imposible en vez de improbable?

Imposible queda: que una skill cite una ruta que no existe, que le falte el
nombre o la descripción, que su nombre no coincida con su carpeta, o que cite
un ADR inexistente — todo eso tumba la batería. **Improbable, no imposible,
queda lo único que importa de verdad**: que la prosa esté caducada aunque cada
ruta resuelva. Contra eso no hay prueba posible, solo la revisión trimestral
que `patrones.md` ya declara; queda escrito aquí para que nadie confunda una
skill verde con una skill al día.

## Adenda 4 — la tercera muestra: 28 transcripciones que cada sesión de la nube subió por sí misma (2026-09-20 23:05 UTC)

**Cómo llegaron.** Ninguna de las cuatro vías del teleport trae la transcripción
sin gastar un turno (auditoría, sección «Las cuatro vías probadas»). La quinta
sí: la transcripción vive en el contenedor de cada sesión, y **cada sesión puede
copiarla al repositorio ella misma**. El propietario pegó en cada una de las 33
sesiones de la nube la misma orden —copia tus `.jsonl` a
`docs/audits/transcripciones/<id>/`, rama `transcripciones/<id>`, commit y
push— entre las 18:15 y las 22:30 UTC del 20-09. Dos cosas que pasaron por el
camino y quedan escritas: en algunas sesiones con Opus 5 la primera redacción de
la orden («copia tu transcripción») disparó un filtro de seguridad
(`reasoning_extraction`) y el turno cayó; una redacción sin esa palabra, o
cambiar el modelo de la sesión, lo resolvió. Y hacia las 22:30 el propietario
agotó su ventana de uso de cinco horas, que es cuando dejaron de llegar.

**Antes de eso, desde esta sesión**, se desarchivaron las 23 que estaban
archivadas (una archivada no se puede reanudar) y se comprobó que la mensajería
entre sesiones no alcanza a las de la nube: lo que se hizo lo hizo él, una a
una.

**Lo visto para clasificar, y nada más** —el mismo límite de la adenda 2—: el
nombre de la rama, las fechas del primer y último registro, el número de
registros por tipo, las ramas de git que el fichero declara, las herramientas
invocadas con su recuento y el tamaño del texto del propietario y del
asistente. **Ningún mensaje.** El casado sesión↔transcripción se hizo por la
rama de salida que la sesión declara en su ficha y que el fichero repite.

**Lo recibido: 28 transcripciones de 28 sesiones, más un fichero de subagente.**

| Sesión creada | Título | Registros de | Registros | KB |
|---|---|---|---|---|
| 2026-07-18 | Validación final Sirius remoto | 2026-07-18 → 2026-09-20 | 101 | 486 |
| 2026-07-18 | Validar suite Qt headless en Sirius | 2026-07-18 → 2026-09-20 | 272 | 895 |
| 2026-07-18 | Validar entorno remoto Sirius Python 3.14 | 2026-07-18 → 2026-09-20 | 175 | 631 |
| 2026-07-18 | Python 3.14 compatibility validation | 2026-07-18 → 2026-09-20 | 108 | 490 |
| 2026-07-18 | Validación del repositorio Sirius | 2026-07-18 → 2026-09-20 | 190 | 645 |
| 2026-07-18 | Sesión iniciada | 2026-07-18 → 2026-09-20 | 80 | 471 |
| 2026-07-18 | Verificar script de configuración | 2026-09-20 → 2026-09-20 | 118 | 496 |
| 2026-07-18 | Verificación de script de configuración | 2026-09-20 → 2026-09-20 | 91 | 442 |
| 2026-07-19 | Sirius workflow transitions repair | 2026-08-08 → 2026-09-20 | 1337 | 5848 |
| 2026-07-25 | ADR-001 spike 7 y revisión de cierre | 2026-07-27 → 2026-09-20 | 212 | 1181 |
| 2026-07-26 | ADR002 benchmark corpus hardening | 2026-07-28 → 2026-09-20 | 121 | 721 |
| 2026-07-26 | Auditoría adversarial corpus v0.2 | 2026-07-28 → 2026-09-20 | 206 | 1081 |
| 2026-07-26 | Auditoría adversarial benchmark ADR-001 | 2026-07-27 → 2026-09-20 | 180 | 942 |
| 2026-07-26 | Auditoría Registro de Tolerancias v0.3 | 2026-07-27 → 2026-09-20 | 155 | 1013 |
| 2026-07-27 | TOL-207 caracterización almacenamiento v0.2 | 2026-07-27 → 2026-09-20 | 477 | 2851 |
| 2026-07-27 | Auditoría adversarial TOL-207 | 2026-07-26 → 2026-09-20 | 417 | 1470 |
| 2026-07-27 | Revisión forense ADR002-TOL-207 | 2026-07-28 → 2026-09-20 | 550 | 3752 |
| 2026-07-27 | ADR002 v0.4 auditoría adversarial final | 2026-07-26 → 2026-09-20 | 440 | 3473 |
| 2026-07-28 | Auditoría final B-1 ADR-002 | 2026-07-26 → 2026-09-20 | 453 | 3209 |
| 2026-07-28 | Auditoría final B-1 ADR-002 | 2026-07-25 → 2026-09-20 | 638 | 3773 |
| 2026-07-28 | ADR002-TOL-207 auditoría adversarial final | 2026-07-27 → 2026-09-20 | 484 | 2438 |
| 2026-08-02 | Revisión dual Claude + Codex en Sirius | 2026-08-11 → 2026-09-20 | 328 | 1889 |
| 2026-08-07 | Model estudio review y auditoría | 2026-08-14 → 2026-09-20 | 163 | 891 |
| 2026-08-11 | Auditoría de procesos de trabajo Sirius | 2026-08-15 → 2026-09-20 | 605 | 3267 |
| 2026-08-15 | Flujo de trabajo definitivo de Sirius | 2026-09-13 → 2026-09-20 | 856 | 2693 |
| 2026-08-19 | Sirius learning vertical integration audit | 2026-08-19 → 2026-09-20 | 749 | 2641 |
| 2026-08-24 | Sirius motor: PR y primer workflow | 2026-08-24 → 2026-09-20 | 565 | 1389 |
| 2026-09-08 | Propuesta separación Sirius y motor | 2026-09-08 → 2026-09-20 | 21669 | 56910 |

El fichero `agent-a6add8…` (40 registros, 11-09) es un subagente de la sesión
del 08-09; el protocolo del paso 4 no leyó tráfico de subagentes y este tampoco.

**Las cinco que no llegaron**, con la rama que las identifica:

| Creada | Título | Rama de salida |
|---|---|---|
| 2026-08-18 | No hagas nada | `herramienta/skill-adr` |
| 2026-08-10 | Pendientes del ciclo: PRs, issues y automatiza | `claude/ciclo-pendientes-prs-issues-qm4t8x` |
| 2026-07-18 | Python 3.14 instalación | `claude/python-3-14-install-check-8pygia` |
| 2026-07-18 | Verificar versiones y estado | `claude/check-versions-status-iejdep` |
| 2026-07-18 | Cloud push smoke test | `claude/cloud-push-smoke-test-akcqiv` |

De estas, **«Pendientes del ciclo» ya está leída**: es la sesión de la nube que
el propietario trajo a mano el 20-09 a las 02:44 y que el paso 4 leyó entera. La
única pérdida con sustancia es **«No hagas nada» (18-08-2026)**. Las otras tres
son pruebas de siete minutos del 18-07. Y la sesión de la auditoría forense
sigue viva y trabajando; se excluyó a propósito, y de ella se leyó en el paso 4
la copia de las 02:45.

**Qué entra y qué no.** Entran las 26 con historia. Quedan fuera las dos de
`2026-09-20 → 2026-09-20` («Verificar script de configuración» y su gemela):
sus contenedores de julio no conservaban nada y el fichero solo contiene el turno
de hoy. Queda fuera el subagente.

**Orden**, del hueco más ciego al menos: primero **agosto**, que es lo que el
paso 4 no pudo ver —15-08 «Auditoría de procesos de trabajo» (la sesión donde
nació la primera edición de esta auditoría), 08-08 «workflow transitions
repair», 11-08 «revisión dual», 14-08 «Model estudio review», 19-08 «learning
audit», 24-08 «motor: PR y primer workflow»—; después **septiembre** —13-09
«flujo de trabajo definitivo» y, la última por tamaño, 08-09 «propuesta
separación Sirius y motor» (1 491 KB de extracto, 470 mensajes del
propietario)—; después el **bloque de julio de ADR-002** (25-07 → 28-07, doce
sesiones), de la más antigua a la más nueva; y al final las **seis pruebas del
18-07**.

**Cómo se lee:** el protocolo de la adenda 2, sin cambios. Los extractos se
generan por máquina a partir de los `.jsonl` (mensajes del propietario
íntegros; asistente hasta 2 500 caracteres; herramienta: nombre y primera
línea; resultados no leídos salvo denegaciones) y viven **solo en el espacio
temporal de esta sesión**, no en el repositorio. El filtro de denegaciones es
grueso a propósito —casa «permiso» y «rechaz» en cualquier contexto— y la
lectura separa denegación de mención.

**Qué se extrae:** los seis campos de la adenda 2.

**Hipótesis, escritas ahora, antes de abrir ningún extracto:**

- **H-A.** La sesión del 15-08 es donde se escribieron las 21 fichas PROC de
  agosto. Leerla dirá si esa primera edición se hizo leyendo fuentes o de
  memoria, que es la duda que el paso 2 dejó abierta.
- **H-B.** La sesión del 08-09 —doce días, 470 mensajes suyos— es donde más se
  ven E-04 y E-05: muchos mensajes cortos, esperas largas, cambios de modelo por
  consumo.
- **H-C.** El bloque de julio de ADR-002 enseña C-03 en ejecución: corrige con
  datos y rechaza menús, ya en julio y desde el móvil.
- **H-D.** La columna de «denegaciones» del extracto no correlaciona con las
  escaladas: la mayoría serán menciones, no denegaciones.
- **H-E.** Las seis del 18-07 no cambian ninguna ficha; solo confirman que el
  modo «pegado desde el ordenador» de E-01 empezó en la web.

**Parada:** revisadas C-01, C-02, C-03, N-03 y E-01 a E-06 con lo que estas
fuentes añadan o desmientan, y escrita la sección «paso 5»; o agotados los
extractos; o disparada la regla de las dos rondas por una familia nueva.

**Compromiso con el propietario, que aceptó la exposición «durante ese rato»:**
las ramas `transcripciones/*` se borran del remoto al cerrar el paso 5, y se
deja constancia de cuándo. Mientras tanto, nada de lo que contienen se cita
literalmente fuera de lo que la auditoría ya permitía: frases cortas sobre cómo
trabajar.

## Adenda 5 — las que llegaron después de fijar la muestra (2026-09-20 23:27 UTC)

La adenda 4 fijó 28 transcripciones antes de leerlas. Mientras se leían, el
propietario repitió la orden en las cinco sesiones que faltaban («ya están
todas», 23:20 UTC). Estado a la hora de escribir esto:

| Sesión | Creada | Estado |
|---|---|---|
| «Pendientes del ciclo: PRs, issues y automatizaciones» (`02df1df0`) | 10-08 | rama `transcripciones/02df1df0-…` en el remoto a las 23:18 UTC |
| «Python 3.14 instalación» (`923794ec`) | 18-07 | rama `transcripciones/923794ec-…` en el remoto a las 23:17 UTC |
| «No hagas nada» | 18-08 | parada: pide permiso para hacer push; espera su respuesta |
| «Verificar versiones y estado» | 18-07 | parada: pide que confirme la orden antes de subir la transcripción |
| «Cloud push smoke test» | 18-07 | parada: pregunta si quita el identificador del modelo antes de subir |

Las dos llegadas se clasifican aquí SIN leer ningún mensaje, como manda la
adenda 2 (`fichas_llegadas_tarde.json` en el cuaderno de la sesión):

| Fichero | Registros | Desde → hasta | Tamaño | Texto del propietario | Texto del asistente | Herramientas más usadas |
|---|---|---|---|---|---|---|
| `02df1df0…jsonl` | 1 057 (340 de usuario, 600 del asistente, 80 adjuntos) | 2026-08-10 20:42 → 2026-09-20 23:01 | 4 108 KB | 11 266 caracteres | 59 438 caracteres | Bash 174, lectura de PR 24, lectura de incidencias 24, Edit 20, AskUserQuestion 9 |
| `923794ec…jsonl` | 181 (44 de usuario, 59 del asistente, 41 adjuntos) | 2026-07-18 14:50 → 2026-09-20 18:31 | 720 KB | 13 321 caracteres | 5 943 caracteres | Bash 22, Grep 4, Skill 3 |

Dos observaciones que salen de la clasificación, no del contenido:

- Las dos sesiones empujaron más que la transcripción: `MEMORIA.md` y un
  `docs/audits/evidencia-transcripciones-<id>.md` (1 127 y 316 líneas de
  diferencia frente a `main`). La orden decía «no modifiques nada más»; el
  stop-hook y la skill de evidencia de esta casa pesaron más que la orden
  literal. Se lee solo el `.jsonl`; el resto no se fusiona ni se cita. Va al
  paso 5 como observación sobre cómo las reglas del repositorio se imponen
  incluso a una orden explícita del propietario, no como defecto.
- Con 11 266 caracteres del propietario repartidos en 340 entradas de usuario,
  la del 10-08 confirma antes de leerla lo que la del 08-09 enseñó: «entradas
  de usuario» no son palabras suyas; la mayoría son resultados de herramienta,
  notificaciones y expansiones automáticas. El paso 5 lo dice de todas las
  fichas.

**Hipótesis:** ninguna nueva. Se contrastan las mismas H-A…H-E; de la del 10-08
se espera, por título y fecha, que hable de H-D (los pendientes del ciclo en la
semana en que nacieron las ramas `wip/`) y de la aceptación de 0.1; de la del
18-07, solo el molde de los micro-encargos del primer día.

**Orden y protocolo:** primero la del 10-08, después la del 18-07, con el
protocolo de la adenda 2 sin cambios. Las tres paradas se leen si llegan antes
de escribir el paso 5; si no llegan, el paso 5 las nombra como no leídas, con
la razón (esperan una respuesta del propietario dentro de cada sesión), y no se
espera por ellas: la parada de la adenda 4 sigue mandando.

**Parada de esta adenda:** las dos leídas y anotadas; o disparada la regla de
las dos rondas por una familia nueva.

## Adenda 6 — tres skills de flujo de trabajo, con las condiciones escritas antes de elegirlas (2026-09-21 10:26 UTC)

El propietario, al ver el paso 5 fusionado, lo dijo sin rodeos: de las
transcripciones quedó un informe y tres reglas, no herramientas de flujo de
trabajo, y «pasado mañana te vas a olvidar». Tiene razón en el fondo: lo que
no está en el repositorio no sobrevive a la sesión. Las transcripciones ya no
existen (borradas a las 00:25 UTC a petición suya) y no deben volver; lo que
sigue sale de lo que esta sesión aún conserva de su lectura y de lo que el paso
5 dejó escrito con fecha y hora.

Las tres condiciones de ADR-211, por candidata, ANTES de escribir ninguna:

| Candidata | Se repite (ocurrencias fechadas) | Fricción medida | ¿Es decisión del propietario? |
|---|---|---|---|
| `modo-nocturno` | 08-08, 10-08, 15-08, 13-09, 14-09 | 3 h 18 min despierto por avisos de permiso (15-08, 01:09 → 04:27) y una herramienta rechazada que la sesión reintentó; diez esperas de fondo perdidas por reinicio del contenedor (09-09 03:01); «que me contestes primero» (14-09 11:04); el parte pedido tres veces (14-09 11:06, 20:53, 22:48); 95 despertares en siete días (08-09) | no: es cómo ejecuta la sesión lo que él ya delegó |
| `revision-externa` | PR #576 (08-09, cuatro rondas traídas por él); PR #658 (21-09, tres rondas sin él); el diseño de la revisión dual (11-08) | cuatro rondas en un día de la misma familia sin que nadie las contara; cuota de Codex agotada (12-09 16:41) | no: el mecanismo es el que ya aprobó (ADR-156, ADR-205); cambia quién lo pide |
| `coste-antes-de-tocar-una-fuente` | 28-07 (12 de 23 agentes muertos por límite de sesión); 11-08 (21 subagentes, «nada»); 19-08 (2,8 M tokens, «todavía no»); 20/21-09 (33 sesiones × un turno, un día y medio uso suyo) | las cuatro cifras de la izquierda | no: es la regla de dinero de ADR-204 aplicada antes de gastar, no una decisión de gasto |

Descartadas antes de escribir: «el parte de la mañana» como skill propia (cabe
en tres párrafos y ya está en `hablar-con-el-propietario` y en la regla 12 de
`AGENTS.md`); «auditar las transcripciones a fondo con más agentes» (no hay
transcripciones, y no debe volver a haberlas en el repositorio).

**Criterio de parada, escrito ahora:** las tres pasan la guarda de ADR-211
(`tests/automation/test_skills.py`) sin tocarla; cada una cita solo ficheros y
ADR que existen; ninguna repite `AGENTS.md` (remiten a sus reglas); la batería
entera vuelve verde salvo la roja por diseño del ADR sin su defecto (ADR-182),
que cierra el commit siguiente con H-214; y si al escribir una candidata no
llega a dos ocurrencias fechadas, se descarta.

**Qué NO garantiza:** que una sesión las cargue —la descripción es lo único que
decide eso (ADR-211)—, ni que el propietario deje de ser el correo entre IAs:
eso es la memoria común, no una skill.

**Adenda 6 bis (10:34 UTC).** El propietario, al ver las tres: «así pudimos haber
sacado por lo menos diez o veinte». Antes de escribir ninguna más, las
candidatas que aún salen de lo leído, con las mismas tres condiciones:

| Candidata | Se repite (ocurrencias fechadas) | Fricción medida | ¿Decisión del propietario? |
|---|---|---|---|
| `comandos-para-su-ordenador` | 08-08, 09-08, 14-08, 11-09, 20-09 | `.venv` «acceso denegado» y el error 396 de OneDrive (08/09-08); `Sirius.lnk` en un escritorio que no existe (14-08 15:18); «¿yo qué sé dónde está la carpeta?» (11-09 21:17); `npx.ps1` bloqueado por la política de ejecución y `winget` con error 1622 (11-09 21:51-21:54); dos comandos tumbados por `$HOME\Desktop` (20-09) | no |
| `paquete-de-trabajo-pegado` | las seis del 18-07; las doce del 25 al 28-07; 19-08; los diez encargos del 08-09 | ficheros pedidos que la sesión no puede ver (26-07 14:14 → 15:31); «dame todas las respuestas… como un solo documento» (26-07 20:20); el mismo paquete en dos sesiones (28-07 19:52); el paquete equivocado (13-09 06:23) | no: el paquete lo redacta quien él quiera; esto es cómo se ejecuta |
| `traspaso-a-otra-sesion` | 08-08 («genera un prompt… que me voy a dormir»), 19-08 00:03, 24-08 15:12 (traspaso pegado), 13-09 14:35 (lo de Hermes perdido), 14-09 21:24 (M17 sin razón recordada) | una tarde en balde por reconciliar desde una copia caducada (14-08, #165); «otra vez a investigar, otra vez a mirar, otra vez a hablar» (13-09) | no |
| `verificar-el-estado-real` | 10-08 22:08, 14-08 14:51, 14-08 15:28, 17-08 15:00-15:47, 19-08 00:44 | documentos que decían «terminada» lo que no lo estaba; seis correcciones suyas, seis acertadas (E-03); la afirmación falsa repetida siete veces en tres documentos (19-08) | no |

Descartadas por no llegar a dos ocurrencias fechadas o por caber en una regla
que ya existe: «presentar un plan sin códigos» (regla 10 y la skill de hablar),
«cuándo usar el motor en vez de la sesión» (una ocurrencia, 12-09 15:32),
«instalar herramientas en su ordenador» (cabe en la de comandos). El criterio
de parada de la adenda 6 no cambia; ADR-214 pasa a cubrir las siete.

## Adenda 7 — segunda tanda de skills, desde la auditoría y los ADR, con las condiciones escritas antes de elegirlas (2026-09-21 13:55 UTC)

La PR #659 dejó catorce skills en el repositorio. El propietario preguntó
(21-09) si sin las transcripciones «ya es imposible sacar buenas skills». No lo
es: las fuentes baratas que quedan son las fichas de esta auditoría (PROC, E, T),
los ADR con su lección, los guiones de `scripts/` y la historia de git; ninguna
cuesta nada y ninguna es una transcripción. **Línea de coste, antes de tocar
nada** (skill `coste-antes-de-tocar-una-fuente`): leer unas cuatrocientas
líneas de fichas, diez decisiones de ADR y seis cabeceras de guiones; ningún
agente; rendimiento esperado, entre cuatro y seis skills que pasen las tres
condiciones de ADR-211; parada, la de abajo.

Las cuatro preguntas de la disciplina, contestadas antes de escribir:

1. **Dónde vive el fallo y dónde va el arreglo.** El fallo vive en los
   procedimientos de sesión que la auditoría dio por vigentes y nadie convirtió
   en algo que una sesión cargue; el arreglo va a `.claude/skills/`, que es lo
   único que una sesión lee por su descripción (ADR-211).
2. **Qué NO garantiza.** Que una sesión cargue la skill cuando toca —la
   descripción es lo único que decide eso— ni que la prosa siga al día: la
   guarda solo vigila rutas, ADR, nombre, descripción y límites.
3. **Criterio de parada, decidido ahora:** el de la adenda 6 —la guarda de
   ADR-211 (`tests/automation/test_skills.py`) pasa sin tocarla; cada skill
   cita solo ficheros y ADR que existen; ninguna repite `AGENTS.md`; la batería
   entera vuelve verde salvo la roja por diseño del ADR sin su defecto (ADR-182),
   que cierra el commit siguiente con H-215; una candidata sin dos ocurrencias
   fechadas se descarta al escribirla— más una regla nueva, salida de las
   rondas 3, 4 y 5 de Codex sobre la PR #659: **lo que ya tiene una fuente
   canónica** (el contrato operativo, `docs/operations/MOTOR_DE_SIRIUS.md`,
   otra skill) **se remite, no se copia**; una copia parcial es un defecto
   antes de nacer.
4. **Qué haría el fallo imposible.** Para la podredumbre mecánica, la guarda;
   para la carga, nada: se dice.

Las tres condiciones, por candidata, ANTES de escribir ninguna:

| Candidata | Se repite (ocurrencias fechadas) | Fricción medida | ¿Decisión del propietario? |
|---|---|---|---|
| `validacion-manual-en-windows` | 10-08 14:49 («77 comprobaciones, 0 fallos, 3 omitidas», con lo no demostrado declarado); 17-08 (PR #122, B13 y B14 en Windows real y la aceptación de 0.1) | la PR #122 esperó más de nueve días una ejecución correcta; `.github/workflows/quality-windows.yml` tiene cero ejecuciones en toda su historia; #127 y #134 intactas desde agosto (PROC-008) | no: él ejecuta; la sesión prepara el comando, guía y registra |
| `medir-con-linea-base` | ADR-154 (cifras ancladas al árbol); ADR-202 (14-09: M17, 7/47 contra un suelo de 29/47, y la razón de no medir sin constar); ADR-203 (19-09: la línea base que faltaba; H-203 sigue abierto); 19-09 (una cifra sin su comparación leída como regresión, disparador 4 de E-04) | una medición que cerraba una ola no se hizo y nadie sabe por qué; el banco no sabía medir el camino de producción; una alarma por una línea base recién medida | no |
| `documento-con-lector` | PROC-010 (20-09: la base de conocimiento en v1.1 con el contrato en v1.10; el onboarding con «estado a 20 de julio»); ADR-207 (20-09: dos mapas de julio archivados); ADR-210 (20-09: incidencias que ya no describían nada); ADR-196 (la vista que copiaba el corpus del que huía) | nueve versiones de contrato de retraso; 97 de 150 documentos sin fecha declarada (`MEMORIA.md`); la familia `pieza-sin-lector` suma cinco ADR | no. (Esta fila decía al principio que qué documento concreto se archiva sí se le preguntaba; la ronda 1 de Codex de la PR #660 lo corrigió: archivar es reversible por construcción, ADR-195, y por eso lo decide la sesión, ADR-204. Queda dicho aquí para que nadie siga el criterio inicial.) |
| `rama-y-pr-de-sesion` | 20-09 (#658: rama reiniciada desde `main` porque la anterior tenía la historia de #652 ya fusionada); 21-09 (#659: empujón rechazado por la misma razón; forzar, borrar y `merge` denegados; una pregunta al propietario para abrir rama nueva) | una pregunta evitable y un empujón rechazado el 21-09; los dos ADR-016 nacidos en ramas distintas (ADR-180) | no |
| `paradas-del-motor-delante-del-propietario` | 03-09 → 13-09 (cuatro paradas en `NEEDS_DECISION`, la más antigua diez días, sin salida hasta ADR-189); ADR-198 (una pregunta veinte días sin que nadie la pusiera delante); 19-09 (las cuatro paradas del diario seguían sin salida, PROC-003) | diez y veinte días de espera; 20 de 91 encargos re-despachados, el 22 % (PROC-005) | no: decidir es suyo; ponérselo delante con la orden copiable es de la sesión |

Descartadas antes de escribir: `prueba-intermitente` (una sola ocurrencia,
#137, arreglada por ADR-162 y archivada por ADR-210); `investigacion-con-fecha`
(la regla ya está en la tabla de `AGENTS.md` y en `docs/investigaciones/`, y no
hay fricción medida); `operar-el-ciclo-entero` (su fuente es
`docs/operations/MOTOR_DE_SIRIUS.md` y el contrato operativo: una copia sería
`pieza-sin-lector` al mes); `exportacion-de-chatgpt` (una ocurrencia, 19-09).

**Parada de esta adenda:** las cinco escritas y en verde, o la candidata que al
escribirla no llegue a dos ocurrencias fechadas, descartada por escrito.
