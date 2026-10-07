# ADR-237 — Dar a Sirius memoria propia, un juez y las 40 preguntas trampa

- Estado: APROBADO
- Fecha: 2026-10-07
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza E de ADR-233; lo que hace
  sale de los pasos 3, 5, 7 y 8 de la personalidad en la 0.2 del plan del robot, aprobado
  por el propietario el 06-10-2026.

## Nota de arranque

Escrita antes del primer commit de la pieza E. El criterio de parada de las rondas es el
de ADR-233.

1. **Dónde vive el fallo y dónde va el arreglo.** Sirius no recuerda lo que ya opinó, así
   que puede contradecirse sin motivo o repetir el chiste. Nadie mide si deja de sonar a
   Sirius. Y nada comprueba que no le dé la razón en todo. Los arreglos van donde se
   observan:
   - La memoria propia va en el contexto de cada petición, `ContextBuilder`. PA-R02-07 mira
     lo que recibe el modelo.
   - El juez puntúa cada respuesta completa al acabar el turno, en
     `SendMessageUseCase.send_message`, y guarda la nota. PA-R02-08 mira las notas y los
     avisos guardados.
   - Las 40 ideas malas pasan por el modelo de la charla con la semilla y el recordatorio
     de un turno de verdad. PA-R02-09 mira lo que recibe el modelo y lo que dice el juez.

   **¿Puede el sitio del arreglo observar el fallo?** La memoria propia, sí: la prueba ve
   la petición. El juez es un modelo juzgando a otro y puede equivocarse. Por eso
   E-R02-03 lo compara con el propietario: si discrepa de él en más de 4 de las 40, todavía
   no vale para avisar. Que Sirius discuta de verdad las ideas malas no lo ve ninguna
   máquina: lo juzga el propietario en E-R02-03.
2. **Qué NO garantiza.**
   - La memoria propia busca por palabras. Una opinión dicha con otras palabras no vuelve.
     La búsqueda por significado es de la pieza F.
   - Que el modelo respete lo que ya dijo. Se le enseña; no se le obliga.
   - Que el juez acierte con un modelo pequeño. Es un aviso, no una puerta: no bloquea ni
     cambia ninguna respuesta.
   - El juez no puntúa si la charla va por OpenAI o si no hay modelo local elegido, porque
     cada nota sería una petición más que cuesta dinero.
   - Las preguntas trampa se contestan como el primer turno de una charla nueva, sin sus
     recuerdos ni su historia. No miden cómo influyen sus recuerdos.
3. **Criterio de parada.** El de ADR-233. Si E-R02-03 no pasa, lo que hace está escrito en
   `docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md`: se ajusta la semilla como mucho dos veces y,
   si sigue fallando, se le pregunta.
4. **Qué lo haría imposible.**
   - **Que el juez cueste dinero.** Solo puede construir un proveedor de Ollama local; no
     hay ningún camino suyo hacia OpenAI.
   - **Que una respuesta marcada «eso no» se le enseñe como opinión que mantener.** Lo que
     ya dijo excluye por construcción las respuestas marcadas «eso no»; esas van a «lo que
     no eres».
   - **Que las preguntas trampa ensucien su charla.** No pasan por la persistencia de
     `send_message`: no quedan en la conversación, ni en los resúmenes, ni en las marcas,
     ni en el juez de cada turno.
   - Lo que no se puede hacer imposible: que un modelo no se contradiga nunca ni dé la razón
     nunca. Se hace improbable con su memoria, el juez y las marcas.

## Lo que cambió respecto a la nota

La nota ponía el juez al acabar el turno, dentro de `SendMessageUseCase.send_message`. Así
cada mensaje pedía dos veces al modelo local, y PA-R02-02, que cuenta una sola petición a
Ollama por turno, falló con razón. La inf. 3 dice además que el modelo no debe meterse en
el turno. El juez pasó a segundo plano: la ventana lo lanza al abrirse y al acabar cada
turno, con la respuesta ya en pantalla, y le pide que pare cuando el propietario escribe.
El resto de la nota sigue igual.

## Contexto y problema

El paso 3 pide su propia memoria: «quién es, qué opiniones ha dado y qué bromas funcionaron
y cuáles no. Así no se contradice sin motivo ni repite chistes». El paso 5 dice que las dos
marcas «sirven ya como ejemplos». El paso 7, «un juez: el modelo puntúa cada respuesta en
"suena a Sirius" y avisa si baja». El paso 8, «40 preguntas trampa, con ideas malas del
propietario en las que Sirius tiene que discutirle». Y el plan acaba la versión cuando «le
lleva la contraria en las ideas malas del banco».

## Opciones consideradas

1. **Una tabla de opiniones que el modelo rellena** sacándolas de cada respuesta. Sería
   una petición más al modelo en cada turno para guardar lo que ya está guardado.
2. **Sus propias respuestas como memoria**: las que ya están en la conversación, buscadas
   por el tema del mensaje, con lo que dicen sus marcas.
3. **Pasar las preguntas trampa por la charla de siempre**, como 40 mensajes suyos.
   Quedarían en su conversación y en los resúmenes, y cada respuesta influiría en la
   siguiente.

## Decisión

Se adopta la opción 2 para la memoria propia, y las preguntas trampa se contestan aparte,
como el primer turno de una charla nueva.

- **Quién es**: la semilla, que ya va en cada petición (pieza B).
- **Lo que ya ha dicho de esto**: hasta tres respuestas suyas que comparten palabras con el
  mensaje, que no están ya entre los mensajes recientes y que no están marcadas «eso no».
  Van en la sección «# Lo que ya has dicho de esto», con la indicación de no contradecirse
  sin motivo y no repetir el chiste.
- **Qué bromas funcionaron y cuáles no**: las tres últimas respuestas marcadas «eso es
  Sirius» van en «# Lo que sí eres», como tono y no como frases que repetir. Las tres
  últimas marcadas «eso no» van en «# Lo que no eres».
- **El juez**, en `src/sirius/domain/reply_judge.py` y `ReplyJudgeService`:
  - Puntúa del 1 al 5 si cada respuesta completa suena a Sirius, con el modelo local
    elegido. Sus instrucciones empiezan por la identidad, para que sepa quién es Sirius.
  - Va en segundo plano, no en el turno. Puntúa en orden las respuestas sin nota y para
    cuando el propietario escribe.
  - Solo puntúa las respuestas de la 0.2: las que tienen apuntado con qué modelo se dieron
    (pieza D). Las de antes se dieron con otra semilla.
  - La nota se guarda en la tabla nueva `judge_scores`, con su migración `5ae46b266506`.
  - Avisa cuando la media de las 10 últimas notas baja de 3,5, una vez por bajada. La
    ventana lo enseña mientras la media siga por debajo.
  - Si no hay modelo local o el juez falla, esa respuesta se queda sin nota hasta la vez
    siguiente y la charla sigue.
- **Las 40 preguntas trampa**, en `src/sirius/domain/trick_questions.py`, cada una con su
  porqué:
  - Se contestan con el modelo de la charla y las instrucciones del primer turno de una
    charla nueva, con la semilla y el recordatorio, sin guardar nada.
  - El juez da su veredicto de cada respuesta.
  - Una ventana, «Preguntas trampa…», deja al propietario leerlas y marcar si le lleva la
    contraria. Le dice cuántas, si pasa y en cuántas el juez dice otra cosa: es E-R02-03.
  - La ventana solo se abre con la charla en un modelo de este ordenador, para que las 40
    peticiones no cuesten dinero.

## Comprobación que la sostiene

- PA-R02-07, PA-R02-08 y PA-R02-09 en verde: sus siete pruebas de aceptación, una de
  ellas sobre la ventana de verdad. Con la pieza E entregada, las de la 0.2 dan 35
  pasadas y 16 `xfail` de las piezas F y G.
- PA-R02-02 sigue viendo una sola petición a Ollama por turno con el juez montado.
- Vistas fallar con el código estropeado a propósito, cada una en su prueba:
  - sin «lo que ya has dicho de esto», sin «lo que no eres» o sin «lo que sí eres»;
  - con el juez guardando la nota sin el aviso;
  - con la ventana que no enseña el aviso;
  - con las preguntas trampa sin veredicto del juez;
  - con el aviso del juez en cada nota baja y no una vez por bajada;
  - con la memoria propia repitiendo lo que ya va en la petición;
  - con el juez puntuando también las respuestas de la 0.1;
  - con las preguntas trampa sin el recordatorio.
- Que el juez no cueste dinero: con la charla puesta en OpenAI y un modelo local
  elegido, su única petición va a `localhost`, a `/api/chat` y con ese modelo. Sin modelo
  local elegido no pregunta a nadie.
- Que las preguntas trampa no ensucien su charla: después de las 40, las tablas
  `messages`, `reply_marks`, `judge_scores` y `conversation_summaries` siguen vacías.
- Unitarias: 10 de la memoria propia, 18 del juez y 2 del banco. 11 de integración sobre
  SQLite y 4 de la ventana de las preguntas trampa.
- Revisión propia antes de la primera ronda externa: restaurar una copia con el juez
  puntuando cerraba las conexiones con el juez aún por escribir su nota en `sirius.db`.
  Ahora la restauración le pide parar, espera a que acabe y mientras tanto no vuelve a
  empezar (`tests/gui/test_backup_recovery_ui.py`). La prueba falla sin la espera y
  también si solo falta la petición de parar.

## Consecuencias

- Cada petición puede llevar hasta nueve respuestas suyas, recortadas a 300 caracteres. Se
  cuentan dentro del presupuesto de lo que entra en la petición, como el resumen.
- Con un modelo local elegido, el modelo trabaja un poco al acabar cada turno para
  puntuar. Si el propietario escribe, el juez para y sigue después.
- El propietario tiene ya con qué hacer E-R02-03.

## Alternativas descartadas y por qué

- **El juez con el modelo de la charla, sea cual sea.** Con OpenAI duplicaría las
  peticiones de cada turno, y el dinero de la 0.2 es 0 €.
- **El juez dentro del turno.** Era lo de la nota. Duplicaba las peticiones de cada
  mensaje y rompía PA-R02-02.
- **Puntuar toda la historia al estrenar el juez.** Las respuestas de la 0.1 se dieron con
  otra semilla: puntuarlas con la nueva no dice nada y ocuparía el modelo un buen rato.

## La lección

- familia: `modelo-dentro-del-turno`
- sin esto se repetiría: poner otra petición al modelo de la charla dentro de cada turno,
  como el juez de la nota de arranque, que duplicaba las peticiones de cada mensaje. Lo
  cazó una prueba de otra pieza, no una de las suyas, y el sueño o los hechos de la pieza
  G podrían volver a hacerlo
- lo hace cumplir: tests/acceptance/test_robot_0_2_personalidad.py
