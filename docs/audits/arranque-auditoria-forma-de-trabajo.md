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
