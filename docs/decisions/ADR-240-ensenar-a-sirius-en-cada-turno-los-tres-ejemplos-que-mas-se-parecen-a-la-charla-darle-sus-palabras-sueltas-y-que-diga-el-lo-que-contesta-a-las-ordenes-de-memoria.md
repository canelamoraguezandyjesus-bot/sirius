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

La opción 2, con lo que describe la nota de arranque.

## Comprobación que la sostiene

Se completa al terminar, con las pruebas, la mutación y la batería.

## Consecuencias

Se completan al terminar.

## Alternativas descartadas y por qué

Las opciones 1 y 3, por lo que dice cada una.

## La lección

- ninguna: es un cambio de producto pedido por el propietario, no el arreglo de un
  defecto que alguien pudiera repetir.
