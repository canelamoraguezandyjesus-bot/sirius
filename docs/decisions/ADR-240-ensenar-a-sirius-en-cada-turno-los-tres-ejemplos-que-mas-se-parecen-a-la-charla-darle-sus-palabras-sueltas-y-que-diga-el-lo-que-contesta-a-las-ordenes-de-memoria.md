# ADR-240 — Enseñar a Sirius en cada turno los tres ejemplos que más se parecen a la charla, darle sus palabras sueltas y que diga él lo que contesta a las órdenes de memoria

- Estado: APROBADO
- Fecha: 2026-10-08
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Lo que cambia es del propietario: la
  sesión lo propuso el 07-10-2026 y él contestó el 08-10-2026 «Procedemos como dices».
  Ese mismo día marcó el texto de la semilla: «me vale».

## Nota de arranque

Escrita antes del primer commit de código. El criterio de parada de las rondas es el de
ADR-233: como mucho tres por PR, y dos seguidas con hallazgos de la misma familia paran.

1. **Dónde vive el fallo y dónde va el arreglo.**
   - Cada petición de la charla lleva los 20 ejemplos de la semilla uno detrás de otro
     (`render_robot_seed` en `src/sirius/domain/robot_seed.py`), y un modelo tiende a
     copiar lo que ve. Él lo dijo el 07-10-2026: que no los lea «de una manera lineal»,
     pero que no se borren, porque definen bien a Sirius y «serviría para entrenar».
   - La semilla dice «No tienes muletillas fijas», y él quiere lo contrario: palabras
     suyas sueltas, como «listo».
   - Las órdenes de memoria contestan con frases fijas que escribió la sesión
     (`src/sirius/application/memory_commands.py`). Suenan a máquina, no a Sirius.
   - **El arreglo**:
     - Los 20 ejemplos pasan a ser datos de cada versión de la identidad, en su propia
       columna, y siguen guardados en todas. El texto de la semilla se queda con los
       valores.
     - Cada petición de la charla lleva los 3 ejemplos que más se parecen al mensaje,
       barajados, y delante «Así reaccionaste en algo parecido. Coge la actitud, no las
       palabras.». El parecido lo mide el modelo de huellas que ya busca los recuerdos;
       sin él, las palabras en común, y si no hay ninguna, el azar.
     - La misma regla vale en la prueba a ciegas, pregunta a pregunta, y en las 40
       preguntas trampa, que pasan por la charla. El juez no conversa: ve los 20, porque
       juzga cómo suena Sirius.
     - «No tienes muletillas fijas» se cambia por sus palabras: listo, jefe, tío, macho,
       joder, soquete, energúmeno y cabezón. Las suelta cuando le salen, nunca como
       fórmula.
     - Las órdenes de memoria se cumplen como hoy, sin el modelo. Después, el modelo de la
       charla dice con la voz de Sirius lo que pasó, a partir de una frase fija que no
       lleva nada de la base ni del mensaje de la orden. Lo que tiene que ir exacto va
       detrás, tal cual, sin pasar por el modelo: la lista de hechos, la corrección con su
       «Dime «sí» y lo cambio.» y el aviso de las copias. Si el modelo falla o se cancela,
       va la frase fija de hoy.
   - **¿Puede el sitio del arreglo observar el fallo?** Sí. El grabador de las pruebas de
     aceptación ve cada petición: cuenta que lleve 3 ejemplos de los 20, que sean los más
     parecidos y que cambien de orden, y busca lo olvidado en la petición de la voz.
2. **Qué NO garantiza.**
   - Que el modelo coja la actitud y no las palabras. Lo dicen sus marcas (E-R02-02).
   - Que lo que el modelo de huellas llama parecido sea lo que él llamaría parecido.
   - Sin el modelo de huellas, el parecido es por palabras en común, y sin ninguna, al
     azar.
   - Que la voz cuente bien lo que pasó: la pone el modelo. Lo exacto va aparte, tal cual.
   - Lo que tarda una orden de memoria: ahora espera una frase del modelo. Con el modelo
     cargado, segundos.
   - Con la charla en OpenAI, la frase fija de la orden va a OpenAI. Esa frase no lleva
     nada suyo.
3. **Criterio de parada.** El de ADR-233. Además:
   - si la voz de las órdenes necesita mandar al modelo algo que salga de la base o del
     mensaje de una orden de olvidar, esa parte no se hace y las órdenes siguen con la
     frase fija;
   - si guardar los ejemplos como datos obliga a tocar las copias de seguridad o la
     restauración más allá de la columna nueva, se para y se vuelve a pensar.
4. **Qué lo haría imposible.**
   - **Que vuelvan los 20 en fila a la charla.** La charla los toma de un selector que
     devuelve como mucho 3, y la prueba los cuenta en cada petición.
   - **Que el modelo vea lo olvidado.** La petición de la voz se monta solo con la
     identidad, el modo y una frase de una lista cerrada, con números y, en «¿qué sabes
     de…?», el nombre de la persona. Ningún texto de la orden de olvidar ni de lo que
     borra entra en ella. La prueba busca la palabra olvidada en todas las peticiones.

## Contexto y problema

La propuesta del 07-10-2026, tal como se le dio:

> No se borra nada. Los 20 ejemplos se quedan enteros. Siguen en su identidad, que
> guarda cada versión, y servirán en la 0.5 para entrenarle. Sin leerlos en fila cada
> vez: al principio de cada respuesta le llegan los 3 que más se parecen a lo que estáis
> hablando, cada vez en distinto orden, con esta idea: «así reaccionaste en algo
> parecido; coge la actitud, no las palabras». Quito «no tienes muletillas fijas» y le
> pongo palabras suyas, para soltarlas cuando le salgan, nunca como fórmula: listo, jefe,
> tío, macho, joder, soquete, energúmeno, cabezón. «Olvida eso» y las demás las dirá él a
> su manera, sin ver lo que olvida.

El 08-10-2026 volvió a pegar sus 24 marcas del 07-10, iguales, y cambió la última línea:
de «Texto de la semilla: sin marcar» a «Texto de la semilla: me vale».

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

1. **Los ejemplos dentro del texto de la identidad, y separarlos al montar la
   petición.** No cambia la base, pero el montaje tendría que adivinar dónde empieza
   cada ejemplo dentro de un texto libre.
2. **Los ejemplos como datos de cada versión de la identidad, en su propia columna.**
   Una migración pequeña; la identidad sigue viviendo en datos, como pide la decisión 5
   del giro al robot.
3. **Los ejemplos solo en el código.** La base dejaría de guardar con qué ejemplos
   habló cada versión, y eso es lo que servirá para entrenarle.

## Decisión

La opción 2, con lo que describe la nota de arranque. En concreto:

- **Los ejemplos, como datos.** `identity_versions.examples` guarda, en JSON, quién habla,
  qué dice y qué contesta Sirius en cada ejemplo (migración `96dcb8c3d40e`). Las versiones
  de antes quedan con `[]`; las de la semilla del robot de ayer los llevan dentro del
  texto. `adopt_robot_seed` compara texto y ejemplos: una base con la semilla de ayer
  recibe esta como versión nueva, y la de ayer se queda en la historia.
- **Los tres de cada petición.** `SeedExamplePicker`
  (`src/sirius/application/seed_examples.py`) da los 3 de más parecido entre la huella
  del mensaje y la de lo que se le dice a Sirius en cada ejemplo, con el modelo de huellas
  de la búsqueda de recuerdos. Las de los ejemplos se piden de cuatro en cuatro, con la
  misma paciencia que la del mensaje, y se guardan mientras Sirius está abierto. Sin
  huellas, cuentan las palabras de cuatro letras o más en común, y los empates los decide
  el azar. Los tres van siempre barajados.
- **Una huella por turno.** La del mensaje la piden la búsqueda y los ejemplos;
  `MemoryEmbeddingService` recuerda la última y Ollama la calcula una vez.
- **Quién ve cuántos.** La charla, las 40 preguntas trampa y la prueba a ciegas, 3. En
  la prueba a ciegas se eligen una vez por pregunta y valen para todos los modelos. El
  juez ve los 20, con el aviso de antes, «Así suenas. No son frases para repetir: te
  enseñan el tono.»: juzga cómo suena Sirius y no conversa.
- **La voz de las órdenes.** `CommandReply` separa lo que Sirius puede decir con su voz
  (`said`), lo exacto (`exact`) y la frase de siempre (`fixed`). `CommandVoice` monta la
  petición con la identidad y 3 ejemplos elegidos por la frase, el modo de la charla, la
  tarea y el recordatorio. Lo que contesta es su voz y, en la línea siguiente, lo exacto.
  Si el modelo falla, se cancela, no dice nada o la petición no se puede preparar, va la
  frase de siempre. La respuesta se guarda con la frase de siempre en cuanto la orden se
  cumple, y la voz la cambia después (ronda 1 de Codex). La voz no se apunta con su modelo
  y el juez no la puntúa: lleva datos tal cual, como la lista de hechos, que no son charla.

## Comprobación que la sostiene

- **Pruebas de aceptación de la 0.2**: las 9 de la pieza H, escritas antes del código
  (`da77f87b`) y en `xfail` estricto hasta él, pasan. Las de la pieza G que pedían que no
  hubiera petición ahora piden que lo olvidado y los hechos no lleguen al modelo, y pasan
  antes y después del código.
- **Roturas a propósito**, sobre una copia aparte, cada una con las pruebas que la vigilan.
  Las 19 fallan como deben:
  1. llevar todos los ejemplos en vez de 3;
  2. no barajarlos;
  3. elegirlos sin mirar el parecido;
  4. romper el parecido por palabras;
  5. dar a la voz la frase de siempre entera, con lo exacto dentro;
  6. que un fallo del modelo no vuelva a la frase de siempre;
  7. quitar lo exacto de detrás de la voz;
  8. quitar el modo de la petición de la voz;
  9. adoptar la semilla sin sus ejemplos;
  10. no guardarlos en la base;
  11. no recordar la huella del mensaje;
  12. que el juez vea 3 en vez de 20;
  13. que la prueba a ciegas elija los ejemplos por modelo;
  14. dejar sin ejemplos las preguntas trampa;
  15. aceptar unos ejemplos dañados en la base;
  16. pedir las 20 huellas de una vez;
  17. no contar los ejemplos en el presupuesto de la petición;
  18. que un fallo al preparar la voz deje la orden sin respuesta;
  19. pedir la voz antes de guardar la respuesta, como antes de la ronda 1 de Codex.

  La 17 pasó con las pruebas que había. Se añadió la que la caza
  (`test_los_ejemplos_de_la_semilla_de_la_peticion_cuentan_en_el_presupuesto`).
- **La batería entera** sobre el código de la ronda 1: 8 179 pasan, 16 saltadas y los 2
  `xfail` que ya estaban, en 20 min 31 s. Sobre `a9207bbd` eran 8 176, y en `main`, antes
  del cambio, 8 126. La
  primera vuelta dio 8 174 bien y 1 mal: una prueba de la ventana contaba las huellas que
  se piden y no esperaba las de los ejemplos. Se ajustó, y ahora comprueba además que se
  piden dentro del turno, antes de que sigan las de los recuerdos.
- **ruff**, **mypy** sobre `src` y `tests` (682 ficheros) y el **comprobador de
  documentos**, limpios.

## Revisión externa

- **Ronda 1 de Codex**, sobre `a9207bbd`: un hallazgo, cierto, con sus dos pruebas vistas
  fallar sin el arreglo.
  - P1: la orden se cumplía y su respuesta no se guardaba hasta que el modelo acabara la
    voz. Si Sirius se cerraba o el modelo se quedaba colgado esos segundos, la orden
    quedaba cumplida y sin respuesta, y la frase de siempre no llegaba a guardarse. Ahora
    la respuesta se guarda con la frase de siempre en cuanto la orden se cumple, y la voz
    la cambia después, con un puerto aparte, `ReplyRewriter`, para no tocar los dobles del
    repositorio de la conversación.
  - Familia: una orden cumplida sin su respuesta guardada. Es lo que ADR-239 ya no
    garantizaba, y la voz lo había ensanchado de milésimas a segundos.

## Consecuencias

- Una orden de memoria tarda lo que tarde el modelo en decir una frase: con el modelo de
  su ordenador cargado, segundos. Con la charla en OpenAI, cada orden es una petición más,
  con la identidad y la frase fija.
- La respuesta de una orden se escribe dos veces: primero la frase de siempre y después la
  voz. Si Sirius se cierra entre medias, se queda la frase de siempre.
- El primer turno de cada vez que se abre Sirius pide también las huellas de los 20
  ejemplos, en 5 tandas de 4. Los siguientes, ninguna.
- Montar el contexto ya no da siempre lo mismo: cuáles de los ejemplos empatan y en qué
  orden van cambian a propósito.
- Dos búsquedas seguidas con la misma frase piden su huella una sola vez. La orden de
  E-R02-05 usa las 100 preguntas del banco, que son distintas: mide la huella de todas.
- Un `ContextBuilder`, una prueba a ciegas o unas preguntas trampa montados sin selector
  eligen los ejemplos por palabras.
- Como con cada migración, una copia de seguridad de antes de esta versión no se restaura
  con ella: la restauración solo acepta copias del esquema vigente.
- La orden de E-R02-04 pide en cada caso las huellas de los 20 ejemplos para su Sirius
  nuevo: el banco tarda algo más en su ordenador.

## Alternativas descartadas y por qué

- **Las opciones 1 y 3**, por lo que dice cada una.
- **Que la voz vea los hechos o la corrección.** Podría decirlos mal; lo exacto va tal
  cual, detrás.
- **Pedir las huellas de los ejemplos en segundo plano, al abrir.** Tocaría la
  coordinación de ADR-238 por un trabajo de décimas, y esa coordinación costó tres rondas.
- **Que el juez vea solo 3.** Juzgaría el tono con menos de lo que tiene.

## La lección

- ninguna: es un cambio de producto pedido por el propietario, no el arreglo de un
  defecto que alguien pudiera repetir.
