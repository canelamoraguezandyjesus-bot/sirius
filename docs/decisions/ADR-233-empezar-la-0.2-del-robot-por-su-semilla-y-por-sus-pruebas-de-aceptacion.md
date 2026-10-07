# ADR-233 — Empezar la 0.2 del robot por su semilla y por sus pruebas de aceptación

- Estado: APROBADO
- Fecha: 2026-10-07
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre
  el head de contenido y Quality en verde (ADR-205). El plan que ejecuta lo aprobó el
  propietario el 06-10-2026 (ADR-232), y la orden de empezar la dio el 07-10-2026:
  «Pues venga, ponte a trabajar.»

Este ADR es además la **nota de arranque** de la rama
`claude/la-0-2-del-robot-empieza-por-su-semilla` y de la versión 0.2 de
`docs/evolution/PLAN_DEL_ROBOT.md` (skill `disciplina-evidencia`): las cuatro preguntas y
el criterio de parada están escritos antes del primer cambio de código, antes de
enseñarle al propietario ninguna respuesta candidata y antes de cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Hoy Sirius conversa con la semilla de
   0.1, que vive en el código (`src/sirius/domain/identity.py:56-90`). Dice que existe
   «para ayudar al usuario a pensar, debatir, recordar, organizar, decidir y construir»
   (línea 57), que el humor no se usa «para degradar, herir, imponerse» (línea 83) y que
   separa siempre hechos, inferencias y propuestas (línea 68). La enmienda del manual del
   06-10-2026 cambia las tres cosas. La charla va por OpenAI
   (`src/sirius/composition_root.py:294-348`) y no por un modelo local. El arreglo: la
   semilla nueva entra como versión nueva de la identidad, que ya se guarda por versiones
   (`src/sirius/adapters/persistence/sqlite_identity_repository.py:125`), y llega al modelo
   por `render_instructions` (`src/sirius/application/send_message.py:77-128`), que la pone
   en cada turno. **¿Puede el sitio del arreglo observar el fallo?** Una parte sí: que la
   semilla llegue entera a cada petición lo ve una prueba. La otra no: que suene a Sirius
   no lo ve ninguna máquina, lo ve el propietario. Por eso la semilla se hace con sus
   marcas y la versión acaba con su evaluación (§3 del plan).
2. **Qué NO garantiza.**
   - Las pruebas automáticas usan dobles deterministas. Demuestran que la semilla, los
     modos y las marcas llegan donde deben. No demuestran que Sirius tenga gracia.
   - En el contenedor de las sesiones no hay Ollama con modelos reales. La prueba a
     ciegas, el juez, las 40 preguntas trampa con respuestas reales, el banco de memoria
     con búsqueda por significado real y los 150 ms se miden en el ordenador del
     propietario. Cada prueba lo dice.
   - Las respuestas candidatas que se le enseñan las escribe una sesión. No son palabras
     del propietario: solo entran en la semilla las que él marque «eso es Sirius».
   - En 0.2 Sirius no ve quién tiene delante, porque la cámara llega en 0.4. El corte con
     críos y ancianos frágiles depende de que se lo digan.
   - No garantiza que un modelo pequeño tenga gracia en español. Es el primer riesgo del
     plan (§10), y lo decide la prueba a ciegas.
3. **Criterio de parada**, fijado antes de ver ninguna marca ni ninguna revisión:
   - **La semilla.** Se le enseñan 24 respuestas candidatas. Si marca 15 o más «eso es
     Sirius», la semilla lleva esas, hasta 20. Si marca menos de 15, se reescriben las
     rechazadas con sus comentarios y se le enseñan solo esas, una vez. Si después de esa
     segunda tanda no se llega a 15, se deja de escribir candidatas, porque el fallo es del
     enfoque: se le pide que diga él cómo lo diría Sirius en cinco de ellas.
   - Si rechaza el texto de valores, no se parchea frase a frase: se rehace desde la
     enmienda del manual.
   - **Las PR de la 0.2.** Cada una se fusiona con la cadena de comprobación verde, una
     ronda limpia de Codex sobre el head de contenido y Quality en verde (ADR-205). Como
     mucho tres rondas por PR, por la orden del propietario de no gastar en rondas («Nada
     de cinco rondas, nada de siete rondas»): lo cierto de la tercera se corrige en un
     solo commit, con su prueba vista fallar, y se fusiona sin cuarta.
   - Si dos rondas seguidas encuentran defectos de la misma familia, se deja de parchear y
     se busca la raíz.
   - Si una pieza pide dinero o cambia el producto, por ejemplo un modelo que no cabe en
     su gráfica o entrenar fuera de su ordenador, se para y se le pregunta.
4. **Qué lo haría imposible.**
   - **Que pierda la semilla en una charla larga.** `render_instructions` la pone en cada
     turno, y una prueba fija que toda petición al modelo la lleva, también cuando la
     charla ya está resumida. Eso lo hace imposible por construcción.
   - **Que se le entrene por «me gusta»**, que es lo que volvió pelota a ChatGPT en abril
     de 2025. Los botones solo recogen «eso es Sirius» o «eso no». La marca «me gusta» no
     existe, así que no hay con qué entrenarle mal.
   - **Que olvidar no borre.** La prueba busca el texto olvidado en todas las tablas de la
     base, resúmenes incluidos.
   - **Que lo que dice Sirius cuente como hecho del propietario.** Cada hecho lleva quién lo
     dijo, y un hecho sacado de un mensaje de Sirius se rechaza por su tipo.
   - **Lo que no se puede hacer imposible:** que un modelo no adule nunca y que tenga
     gracia. Se hace improbable con las 40 preguntas trampa, el juez y las marcas.

## Contexto y problema

El propietario aprobó el plan del robot el 06-10-2026 y el 07-10 dio la orden de empezar.
La versión 0.2 es «Sirius en texto: personalidad y memoria» (§4 del plan). Su primer paso
es la semilla nueva, «con las palabras del propietario», escrita «como valores y razones,
no como prohibiciones», con «de 15 a 20 ejemplos de charla». La parte del propietario es
«hacer la semilla con la sesión, la prueba a ciegas y marcar respuestas».

La §3 del plan pide que las pruebas de aceptación se escriban antes de la primera línea de
código de la versión: con pytest lo que una máquina puede comprobar y como evaluación
humana lo que solo puede juzgar el propietario.

Lo único de la 0.2 que espera al propietario es la semilla. Todo lo demás lo programan las
sesiones.

## Opciones consideradas

1. **Empezar por el código**, el conector de Ollama, y dejar la semilla para después. La
   §3 lo impide, porque las pruebas de aceptación van antes del código. Además dejaría al
   propietario esperando sin nada que hacer.
2. **Empezar por la semilla con sus marcas y, a la vez, por las pruebas de aceptación.** Él
   marca mientras la sesión escribe las pruebas.
3. **Que las respuestas candidatas las escriba un modelo local en el contenedor.** No hay
   Ollama con modelos reales aquí, y bajar varios gigas en cada sesión es gasto sin
   retorno. Los modelos se comparan en la prueba a ciegas, que es su sitio.

## Decisión

Se adopta la opción 2.

**Cómo se hace la semilla.** La sesión escribe el texto de valores con las palabras de la
enmienda y 24 respuestas candidatas que cubren las situaciones del plan: pique diario,
ideas malas del propietario, «ponte serio», «para», una mala noticia, desconocidos, un
crío delante, decir «no lo sé», sus opiniones y algo sin sentido. Se le enseñan en una
página privada con dos botones por respuesta, «eso es Sirius» y «eso no», y una casilla
opcional para decir cómo lo diría. Las candidatas son textos escritos por la sesión, no
conversaciones suyas. A la semilla solo entran las que él marque.

**El orden de la 0.2**, una PR por pieza, cada una con sus pruebas de aceptación pasando de
esperadas a verdes:

| Pieza | Qué trae |
|---|---|
| A | Esta nota y las pruebas de aceptación de toda la 0.2, antes del código |
| B | La semilla, cuando el propietario la marque |
| C | Ollama para la charla y la herramienta de la prueba a ciegas |
| D | «Ponte serio» y «para», lo de la deriva y los dos botones |
| E | La memoria propia de Sirius, el juez y las 40 preguntas trampa |
| F | El banco de memoria de 100 casos y la búsqueda por significado. Sale el filtro de Ollama de cada respuesta |
| G | Hechos con fecha y con quién lo dijo, la ficha por persona, «eso no es así», «olvida eso», «¿qué sabes de mí?» y el «sueño» |

**Las pruebas de aceptación** se llaman `PA-R02-NN`. Lo que comprueba una máquina va con
pytest en `tests/acceptance/`, marcado `xfail(strict=True)` mientras falte su pieza: el
día que la pieza entra, la prueba pasa, la marca estricta hace fallar la batería y obliga
a quitarla, así que ninguna marca se queda puesta de más. Lo que solo juzga el propietario
va como evaluación humana paso a paso. Una tabla de trazabilidad une cada `PA-R02-NN` con
sus pruebas y se comprueba por máquina, como la de ADR-006.

## Comprobación que la sostiene

- La semilla vigente es la de 0.1: `sed -n 56,90p src/sirius/domain/identity.py` enseña las
  tres frases citadas en la nota, en las líneas 57, 68 y 83.
- La charla no tiene camino local: `src/sirius/config/llm_provider_settings.py:28-32`
  define solo dos proveedores, `fake` y `openai`.
- Nadie más trabaja en estos ficheros: el 07-10-2026 la API de GitHub devolvió 0 PR
  abiertas, con respuesta 200, y `scripts/automation/sirius_obra_en_curso.py` respondió
  libre.

## Consecuencias

- El propietario recibe primero la semilla para marcar, y mientras marca la sesión escribe
  las pruebas de aceptación.
- La batería tendrá pruebas `xfail` estrictas de la 0.2 hasta que entre cada pieza. Se
  suman a las dos de M11, que siguen como estaban.

## Alternativas descartadas y por qué

- **Enseñarle las candidatas en una lista dentro del chat.** Son 24 respuestas: en el
  móvil, una lista así es larga de leer y de contestar. Los botones le quitan trabajo.
- **Escribir la semilla sin él.** El plan dice que la semilla se hace con él, y la §3 del
  manual enmendado dice que la identidad es lo que se le enseña.

## La lección

- ninguna: es el arranque de una versión con un método ya escrito. Si algo muerde al
  ejecutarla, se escribe aquí.
