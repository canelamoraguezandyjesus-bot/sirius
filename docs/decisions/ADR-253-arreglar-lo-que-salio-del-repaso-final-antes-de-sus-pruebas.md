# ADR-253 — Arreglar lo que salió del repaso final antes de sus pruebas

- Estado: APROBADO
- Fecha: 2026-10-17
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Son defectos de ADR-244 a ADR-252, que
  salieron al recorrer, con la ventana de verdad en offscreen y `sirius-oye` con dobles,
  lo que el propietario hará en sus pruebas.

## Nota de arranque

Publicada antes del primer commit en la incidencia #696, con tres añadidos en sus
comentarios, cada uno escrito antes de su código. Aquí, resumida punto por punto; la
incidencia la tiene entera.

1. **Dónde vive cada fallo y dónde va el arreglo.**
   1. Las peticiones a Ollama iban a `localhost`. En Windows, `localhost` prueba primero
      `::1`, y Ollama escucha de serie solo en `127.0.0.1`. Desde ADR-252 cada petición
      de la charla abre su conexión, así que esa espera se pagaría en cada turno.
   2. La ventana principal no podía medir menos de 787 px de alto: la pestaña «Memoria y
      decisiones» iba sin barra. Al 150 % no cabe en la pantalla.
   3. La hoja se quedaba bajada al pasar de pregunta, en la prueba a ciegas y en las
      preguntas trampa.
   4. Un doble clic o un Intro en las preguntas trampa marcaba también la siguiente.
   5. Esc o la cruz cerraban una hoja sin preguntar.
   6. Si un modelo fallaba a mitad, la prueba a ciegas volvía a pedir las 60 respuestas,
      y las preguntas trampa, las 40.
   7. Cerrar Sirius con un trabajo en marcha pintaba «Signal source has been deleted» y
      esperaba a la petición.
   8. Tras elegir el modelo a ciegas, la ventana seguía diciendo que la charla iba fuera,
      y «Guardar configuración» la devolvía a OpenAI.
   9. El diario no decía qué modelo falló, y una respuesta no válida no dejaba rastro.
   10. Un juez que no contestaba contaba como uno que decía otra cosa.
   11. El resultado de las preguntas trampa no decía cuáles fallaron.
   12. Con la voz de personaje elegida, la ventana no salía hasta cargarla, sin decir nada.
   13. Sin un modelo de charla de este ordenador, `sirius-oye` escuchaba igual, y con el
       proveedor simulado daba un P95 falso.
   14. Con Ollama cerrado, `sirius-oye` decía «Revisa tu red».
   15. `sirius-oye` no calculaba las huellas pendientes ni cargaba el modelo de huellas.
   16. La línea del P95 salía después de cerrar el micro.
   17. Con la voz de personaje, cada frase pintaba su barra y dos avisos.
   18. Minimizar una hoja modal en Windows la deja como una barrita, con la ventana
       bloqueada.
   19. Las órdenes que Sirius enseña para pegar no llevaban `--link-mode=copy`.

   **¿Puede el sitio del arreglo observar el fallo?** Sí en casi todos: se reprodujeron con
   la ventana de verdad en offscreen o con `sirius-oye` de verdad, y se ven en su prueba.
   En 1 y 18, solo lo que se pide: la espera de `::1` y lo que hace Windows al minimizar
   no se pueden ver aquí.
2. **Qué NO garantiza.** Que la espera de `localhost` exista en su Windows; que las
   respuestas guardadas sobrevivan a cerrar Sirius; lo que hace Windows al minimizar; que
   la carga de la voz de personaje deje de ocupar el hilo de la ventana, porque solo se
   avisa.
3. **Criterio de parada.** Cada arreglo con una prueba vista fallar con el código de
   `c7c378f5` y su mutación, con caché de bytecode propia; la batería entera en verde;
   nada cambia lo que Sirius contesta, guarda o mide, solo cómo se ve, cómo se cierra, a
   qué dirección pide y qué apunta el diario; dos rondas de revisión con defectos de la
   misma familia, se para.
4. **Qué lo haría imposible en vez de improbable.** La espera de `::1`, imposible con
   `127.0.0.1`; perder una prueba por un Esc, imposible sin confirmar; dos marcas de un
   doble clic, imposible dentro del intervalo de doble clic; repetir las respuestas ya
   dadas, imposible mientras Sirius siga abierto.

## Contexto y problema

Tras fusionar la PR #692, dos revisores recorrieron todo lo que el propietario hará en su
ordenador. Uno lo hizo con la ventana de verdad en offscreen, con dobles de Ollama, del
oído y de las voces y la pantalla de un portátil al 150 %, 1280×672 lógicos: la prueba a
ciegas, las preguntas trampa, la prueba de voces y las 50 marcas. El otro recorrió con
`sirius-oye` de verdad y una base como la suya lo que hará en la consola. Las pruebas de
cada pieza pasaban; el recorrido entero, con su pantalla y su estado real, no.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Decisión

Un arreglo por punto, en los ficheros donde vive el fallo:

1. **`127.0.0.1`.** Los seis adaptadores de Ollama, la charla, las huellas y los cuatro
   clasificadores piden a `http://127.0.0.1:11434`, y las guardas de «solo va a este
   ordenador» piden ese host.
2. **La ventana cabe.** La pestaña «Memoria y decisiones» va en un `QScrollArea`, como
   Configuración. En 1280×672 a 1,5, el mínimo baja de 673×787 a 528×469, y la ventana abre
   a 900×620.
3. **Cada pregunta empieza arriba**, en la prueba a ciegas y en las preguntas trampa.
4. **Ni un doble clic ni un Intro marcan sin ver.** Tras cada marca, al llegar las
   respuestas y en «Cerrar», los botones esperan el intervalo de doble clic del sistema;
   Intro no los pulsa y un clic no les deja el foco.
5. **Esc o la cruz preguntan** en las tres hojas, si hay trabajo hecho o en marcha; «No»
   por defecto.
6. **Lo pagado no se tira.** Una respuesta que falla se pide otra vez, una sola. Las ya
   dadas se guardan mientras Sirius esté abierto: en la prueba a ciegas, por versión de la
   identidad, modelo y pregunta; en las preguntas trampa, por modelo y versión de la
   semilla. Volver a empezar pide solo las que faltan.
7. **Cerrar no pinta trazas ni espera.**
   - El aviso final de cada trabajador de la ventana, si la ventana ya no está, se pierde
     sin traza: el sueño, el juez, las huellas, Model Studio, las tres hojas, las copias,
     el envío, la clave, la criticidad y la exportación.
   - Cerrar una hoja corta las peticiones en curso de cada pasada, también si dos pasadas
     se solapan.
   - Cerrar Sirius corta el sueño, que deja ese día por soñar. Un turno no lo corta: si lo
     cortara, escribiendo a menudo un día no se soñaría nunca.
8. **Tras elegir a ciegas**, el selector del proveedor pasa a Ollama y el oído lo intenta
   como al abrirse; «Guardar configuración» ya no vuelve a OpenAI.
9. **El diario.** Cada error de la charla lleva la operación y el modelo; una respuesta no
   válida, su clase; una prueba a ciegas que falla, «falló en N de M, con el modelo X».
   Nunca texto de Ollama ni de la charla (ADR-248).
10. **El juez que calla** se cuenta aparte en las preguntas trampa.
11. **El resultado de las preguntas trampa** lista, por identificador e idea mala, las que
    le dieron la razón y las que el juez ve distinto; el diario lleva solo cifras e
    identificadores.
12. **La voz de personaje**: justo antes de cargarla, la consola dice que está cargando,
    que tarda, y que hasta entonces la ventana no sale o no responde.
13. **`sirius-oye` solo arranca con un modelo de Ollama.** Con uno de fuera dice
    CHAT_LEAVES; sin ninguno de este ordenador, que todavía no lo tiene y cómo elegirlo.
    Sale con 2 sin cargar nada, y nunca da un P95 sin un modelo detrás.
14. **Con Ollama cerrado**, `sirius-oye` dice «Ollama no contesta en este ordenador:
    ábrelo. No hace falta internet.».
15. **`sirius-oye` calcula las huellas pendientes** en un hilo de fondo al arrancar, o
    carga el modelo de huellas si no calculó ninguna. Al salir se le pide parar antes de
    cerrar la base, y parar no se apunta como fallo.
16. **La línea del P95 sale antes de cerrar el micro.**
17. **Chatterbox, callado al decir cada frase**: su barra «Sampling», el aviso de
    `sdp_kernel` y el de las generation flags, por su texto. Un cerrojo hace que nunca diga
    dos frases a la vez.
18. **Minimizar una hoja minimiza la ventana dueña**, que tiene botón en la barra de
    tareas.
19. **Las órdenes de `uv` que Sirius enseña** llevan `--link-mode=copy` justo detrás de
    `uv run`, y una guarda nueva lo exige en todo texto de `src/sirius` que no sea un
    docstring. Las dos órdenes de `PRUEBAS_0.2_DEL_ROBOT.md` y `PRUEBAS_0.3_DEL_ROBOT.md`
    también.

## Comprobación que la sostiene

Cada prueba nueva se vio fallar con el código de `c7c378f5`, o con el de la rama antes
del arreglo, y cada mutación corrió con su propia caché de bytecode vacía:
`PYTHONDONTWRITEBYTECODE=1` y un `PYTHONPYCACHEPREFIX` nuevo. Sin eso, una mutación podía
leer el bytecode de la anterior.

- **`127.0.0.1`**: con el código de antes fallaban 18 pruebas de los seis adaptadores y
  de las dos guardas.
- **La prueba a ciegas**: fallaban 8 del caso de uso y 10 de la hoja. El solape de dos
  pasadas se reprodujo: cerrar la segunda esperaba su respuesta entera; con el arreglo,
  la corta.
- **La prueba de voces**: fallaban 5, entre ellas los tres avisos finales sin proteger.
- **El diario de la charla**: fallaban 34 pruebas del proveedor.
- **Las preguntas trampa**: fallaban 18, cada una por su motivo. Por ejemplo: la barra
  en 117 y no en 0, «Idea mala 3 de 40» tras un doble clic, «Signal source has been
  deleted» y «en 3 de 40» contando al juez callado.
- **La ventana**: «787 <= 672» y los `done` sin poner. Ahora cabe en 672 − 40, porque la
  barra de título de Windows al 150 % mide unos 30 px.
- **Los otros siete trabajadores**: con su código de antes y sus señales borradas fallaban
  14 de 14, vaya bien o falle.
- **`sirius-oye`**: fallaban 15. Por ejemplo: salía con 0 en vez de 2, decía «Sin
  conexión con el proveedor…», perdía la cifra si se cortaba el cierre y pintaba el aviso
  de torch al decir la frase.
- **Las órdenes de `uv`**: fallaban la guarda y las dos pruebas que fijaban el texto.
- **Mutación**: 140, y caen las 140. 47 son de `127.0.0.1`, la prueba a ciegas, la de
  voces, el diario, minimizar y las órdenes; 30, de las preguntas trampa y el solape; 29,
  de la ventana y el sueño; 34, de `sirius-oye` y Chatterbox.
- **Chatterbox de verdad**, en un entorno aparte, sin red, con chatterbox-tts 0.1.7, torch
  2.14.1, transformers 5.2.0, tqdm 4.68.4 y pesos al azar con las formas de verdad. Con el
  código de antes, decir una frase pinta la barra y los dos avisos; con el arreglo, ninguno.
- **Revisión propia**: cada rama la revisó en adversario otra bifurcación antes de
  juntarla. Encontró un trabajador sin proteger, el solape de dos pasadas, dos frases a la
  vez, una prueba que no contaba el marco de la ventana, otra que no veía el orden al salir, un aviso falso del diario y dos textos que
  decían más que el código. Todo se arregló con su prueba vista fallar.
- **La batería entera**, sobre `47c174d3`, con los dos ADR y el arreglo de la revisión del
  corte: 9 102 pasan, 15 omitidas, 2 `xfail` y 1 falla, en 34 min 8 s con la máquina
  cargada. La que falla es la guarda del registro de defectos, que pedía la entrada de
  ADR-254: es H-254, que entra en el commit siguiente, y con ella `tests/automation` y
  `tests/engine` pasan enteras. Quality dio lo mismo sobre ese head, con 9 098 en verde. La
  del head final se anota con la ronda de Codex.
- **Quality paró dos heads por guardas de documentos** que no se habían pasado antes de
  empujar: `458eb044`, por la de lecciones, y `47c174d3`, por la del registro. Es la misma
  raíz, y desde ahí, antes de empujar documentos, se pasan enteras `tests/automation` y
  `tests/engine`.
- **ruff** limpio; **mypy** sin errores.

## Consecuencias

- Las respuestas guardadas de la prueba a ciegas y de las preguntas trampa viven mientras
  Sirius esté abierto. Repetir la prueba con la misma identidad y los mismos modelos da las
  mismas respuestas, barajadas otra vez.
- `sirius-oye` ya no escucha sin un modelo de Ollama elegido.
- Si alguien pusiera Ollama a escuchar solo en `::1`, Sirius no lo encontraría. Lo de serie
  es `127.0.0.1`.

**Qué NO garantiza, después del código:**
- Lo de Windows: la espera de `::1`, lo que hace al minimizar una hoja, su intervalo de
  doble clic y cómo salen los botones de confirmar.
- Que Ollama deje de trabajar al colgarle la conexión, y Chatterbox con sus pesos de
  verdad.
- La carga de la voz de personaje sigue en el hilo de la ventana: solo se avisa.
- Al cerrar justo después de abrir, se espera a que cargue el modelo de huellas, hasta
  60 s: su proveedor no tiene `cancel`.
- La hoja de voces no corta la frase ni la carga en marcha: la voz solo sabe decir una
  frase entera.
- Cargar la voz de personaje a la vez que dice una frase, en dos hilos, aún podría pisar
  los filtros de avisos. Solo puede pasar en la ventana.
- El tope de tokens no va en la clave de las respuestas guardadas: si se cambia con
  Sirius abierto, servirían respuestas del tope anterior.

## La lección

- familia: `parada-segura-que-tira-lo-ya-pagado`
- sin esto se repetiría: un fallo de un modelo en la respuesta 46 de 60, o un Esc sin
  querer, tiraba las respuestas ya generadas, de 30 a 40 minutos de su tarde, y había que
  pedirlas todas otra vez. Parar era seguro; tirar lo pagado, no. Lo mismo fijan, para
  las preguntas trampa y las dos hojas, `tests/unit/test_trick_questions.py`,
  `tests/gui/test_blind_test_dialog.py` y `tests/gui/test_trick_questions_dialog.py`.
- lo hace cumplir: `tests/unit/test_blind_test.py`

## Revisión externa

Alcance, escrito antes de la primera petición: los 19 puntos de la nota de arranque, que
esta PR arregla, sin nada más. Las rondas se anotan aquí.
