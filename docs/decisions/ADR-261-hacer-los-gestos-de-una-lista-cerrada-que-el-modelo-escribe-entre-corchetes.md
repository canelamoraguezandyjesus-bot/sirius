# ADR-261 — Hacer los gestos de una lista cerrada que el modelo escribe entre corchetes

- Estado: APROBADO
- Fecha: 2026-10-19
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). Es la pieza C de la 0.4, en el orden
  de ADR-259.

Este ADR es además la **nota de arranque** de la pieza C. Se escribe antes de probar
nada: solo había un primer borrador del filtro, sin ejecutar. Los umbrales de la pieza los
fijó ADR-259 en
`docs/evolution/PRUEBAS_0.4_DEL_ROBOT.md`, PA-R04-05, antes de que la pieza existiera, y
aquí no se añade ni se afloja ninguno.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** El modelo no sabe que tiene cara, y si
   escribiera un gesto entre corchetes, la etiqueta saldría en la ventana, la diría la
   voz y quedaría guardada en la charla. El plan pide gestos de una lista cerrada, que el
   modelo escribe como `[ceja_arriba]` y la cara hace, y que lo que no está en la lista
   se ignore (§6, «Lo que se hace», 7). El arreglo va en cinco sitios:
   - **La lista y qué es una etiqueta**, en el dominio, sin Qt:
     `src/sirius/domain/gestures.py`, con el filtro que las quita del texto mientras
     llega a trozos.
   - **La charla**: `SendMessageService` pasa lo que escribe el modelo por el filtro
     antes de enseñarlo, decirlo o guardarlo, y da cada gesto de la lista, en su sitio
     entre los trozos, a quien lo pida (`on_gesture`). Las instrucciones llevan la lista.
   - **La voz**: cada gesto va con la frase en que se escribió, y la cara lo hace cuando
     esa frase empieza a sonar. El oído se lo da a la cara sin coger su cerrojo, como el
     volumen.
   - **Lo escrito en la ventana**, sin voz: la cara lo hace cuando llega el texto.
   - **La cara**: `FaceLife` hace los gestos, uno detrás de otro, y `FaceWidget` los
     dibuja.

   **¿Puede el sitio del arreglo observar el fallo?** Sí: todo lo que escribe el modelo
   de la charla pasa por `SendMessageService` antes de llegar a la ventana, a la voz o a
   la base, y ahí está el filtro.
2. **Qué NO garantiza.**
   - Que el modelo use bien los gestos, ni que los use: un modelo pequeño puede no
     escribir ninguno o escribirlos de más. Si la cara le gusta lo dice E-R04-05.
   - Que el gesto caiga en la palabra exacta: va con la frase, cuando empieza a sonar.
   - Que la cabeza los haga: es la 0.6, con la misma lista.
   - Que lo que escribe entre corchetes y no es una etiqueta desaparezca: un enlace, una
     cifra entre corchetes o lo que va dentro de un código se quedan como están, a
     propósito.
3. **Criterio de parada**, decidido antes de escribir el código:
   - Las cuatro pruebas de PA-R04-05 en verde, y la batería entera.
   - Una respuesta sin etiquetas no cambia ni un byte, y una respuesta a trozos da lo
     mismo que entera, se corte por donde se corte: si no se puede tener las dos cosas,
     se para y se dice.
   - Dos rondas seguidas de Codex con la misma familia: se deja de parchear y se busca la
     raíz.
4. **Qué lo haría imposible.** Que una etiqueta llegue a la ventana, a la voz o a la base
   desde la charla: el filtro está en el único sitio por el que pasa lo que escribe el
   modelo de la charla, antes de todo lo demás. Lo que no se hace imposible es que el
   modelo escriba entre corchetes algo que no es una etiqueta: eso se ve, como cualquier
   texto.

## Contexto y problema

La pieza B le dio a Sirius su cara (ADR-260). La C le da los gestos, de una lista cerrada
que es la misma que usará la cabeza en la 0.6: el modelo nunca manda ángulos, pide gestos
(§8 del plan). El plan no dice qué gestos son; los decide esta pieza.

Lo difícil no es la cara, es el texto. El modelo escribe a trozos, como Ollama, y una
etiqueta como `[ceja_arriba]` llega partida en cinco o seis. La ventana enseña cada trozo
según llega, la voz empieza a decir la primera frase antes de que el modelo acabe
(PA-R03-02), y lo que se guarda es lo que leen después la charla, el resumen, el sueño y
el juez. Si el filtro dejara pasar media etiqueta, se vería, se diría o se guardaría.

## Opciones consideradas

1. **Quitar las etiquetas al final**, de la respuesta entera. La ventana y la voz van
   antes: se verían y se dirían mientras llegan.
2. **Que la ventana, la voz y la base quiten cada una las suyas.** Tres reglas que tienen
   que decir lo mismo, y lo que lea la charla después sería de la que guarde.
3. **Un filtro en la charla, a trozos**, delante de todo lo demás, que da lo mismo que con
   la respuesta entera y los gestos en su sitio. **Esta.**

## Decisión

Se adopta la opción 3.

- **La lista**, ocho gestos de cara y de cabeza que van con su carácter:
  `ceja_arriba`, el del plan; `cejas_arriba`, `cejas_fruncidas`, `sonrisa`, `guino`,
  `ojos_en_blanco`, `asiente` y `niega`. Los decidió la sesión (ADR-204): elegir los
  gestos de la lista no cambia el producto que pide el plan.
- **Qué es una etiqueta**, en `src/sirius/domain/gestures.py`: un corchete, de una a tres
  palabras de letras unidas por guiones bajos, guiones o un blanco, y otro corchete.
  `[Guiño]` y `[ceja arriba]` son de la lista. Una de fuera de la lista es etiqueta si va
  de una pieza y no pegada a una palabra: `[bailar]` se quita, y `datos[clave]` y
  `[nota del autor]` se quedan. Nunca lo es delante de un paréntesis, que es un enlace,
  ni dentro de un código entre comillas invertidas, ni con cifras: `lista[0]` y `[1]`
  se quedan.
- **El blanco**: con la etiqueta se va uno, el de detrás, o el de delante si detrás viene
  una puntuación de cierre o nada, y de dos se queda el que lleva más saltos de línea.
  «Eso es mentira [ceja_arriba].» queda «Eso es mentira.».
- **El filtro**, `GestureFilter`, lee lo que llega y da lo que ya no puede cambiar; lo
  que aún puede, como un corchete abierto, unos blancos o unas comillas invertidas al
  final, espera al trozo siguiente. Así, a trozos da lo mismo que entero. Lo que no lleva
  corchetes no cambia ni un byte, pero los trozos que da no son los del modelo: un blanco
  del final va al principio del trozo siguiente. Si la respuesta se corta o falla, lo
  guardado es lo escrito, sin el corchete del final que aún podía ser una etiqueta.
- **La charla**, `SendMessageService`, pasa por el filtro lo que escribe el modelo, lo
  guarda sin etiquetas, y da cada gesto con `on_gesture` en su sitio: después del texto
  de delante y antes del de detrás. Sus instrucciones llevan la lista, en «# Tus gestos»,
  delante de la sugerencia de recuerdo. Las preguntas trampa usan las mismas
  instrucciones, y su respuesta se ve sin etiquetas.
- **La voz**: cada gesto se marca, entre lo que se corta en frases, con un carácter de
  uso privado de Unicode, y va con la frase que sale con la marca; si esa frase se queda
  sin nada que decir, con la de antes. La cara lo hace cuando esa frase empieza a sonar,
  y lo que no llega a sonar, por un corte, no lo hace. El oído se lo da a la cara sin su
  cerrojo (`LocalListening.speaking_gestures`).
- **Lo escrito en la ventana**, que no suena: la cara hace el gesto en cuanto llega.
- **La cara**: `FaceLife` hace los gestos uno detrás de otro, con tres como mucho
  esperando; cada uno se hace en 0,15 s, se sostiene y se deshace en 0,3, y dura de
  0,6 s el guiño a 1,6 la sonrisa. `FaceWidget` los dibuja: una ceja o las dos, el ceño,
  la sonrisa, el guiño, los ojos en blanco y la cabeza que asiente o niega.

## Comprobación que la sostiene

- Las cuatro pruebas de aceptación de la pieza C, PA-R04-05, en verde; las de la pieza B
  siguen en verde, y las demás de la 0.4, en `xfail` estricto con su pieza.
- Pruebas nuevas, 71: 34 del filtro (`tests/unit/test_gestos.py`), 12 de la vida de la
  cara, 11 del widget, 7 del oído, 4 de la charla montada de verdad
  (`tests/integration/test_gestos_en_la_charla.py`), 1 de las preguntas trampa, 1 de lo
  escrito en la ventana y 1 de que el conductor ve los gestos que hace la cara.
- El filtro, a trozos y entero: cada respuesta de un banco de 26, cortada por cada sitio
  posible en dos, en tres las de hasta 45 caracteres, y letra a letra, da lo mismo que
  entera; y 3 000 respuestas al azar, cortadas al azar, también, acabadas y cortadas
  antes de acabar. Ninguna deja un gesto de la lista a la vista, y 3 000 sin corchetes
  salen sin cambiar ni un byte.
- Mutación: 46, cada una con su caché de bytecode vacía y su fichero restaurado byte a
  byte. Caen 42 a la primera; vivían cuatro, y cada una pidió una prueba más fuerte: un
  gesto al final de la respuesta que no llegaba al acabar, el gesto de una frase que se
  queda sin nada que decir, un gesto nuevo que pisaba al que se hacía y una duración que
  no era la suya. Con ellas, caen las 46.
- La batería entera, sobre `f95c3073`: 9 323 en verde, 15 omitidas y 21 xfail, los 19
  de la 0.4 que esperan su pieza y 2 de antes, ninguna roja, en 24 min 32 s.
- Quality, sobre la #702, vio fallar una de las dos pruebas de la ventana de la lección;
  las dos, con lo que esperaban antes y una espera más corta que la del modelo de
  mentira, fallan siempre en local, y con lo que se ve mientras llega pasan: las 65 de
  `tests/gui/test_conversation_ui.py` en verde.

## Consecuencias

- La cara gesticula con lo que dice, cuando el modelo escribe gestos.
- `on_delta` ya no recibe los trozos del modelo, sino los del filtro: un blanco del final
  espera al trozo siguiente, por si va delante de una etiqueta. Juntos dicen lo mismo.
  Cinco pruebas de la charla miraban los trozos exactos y ahora miran estos, y dos de la
  ventana miran lo que se ve mientras llega.
- Una respuesta cortada o fallida se guarda sin el corchete del final que aún podía ser
  una etiqueta.
- Las instrucciones de la charla llevan unas sesenta palabras más.
- Lo guardado no lleva los gestos, así que las respuestas que marque para entrenarle en la
  0.5 tampoco: el modelo entrenado seguirá sabiendo qué gestos tiene por sus
  instrucciones. Si se quieren en lo que aprende, habrá que guardarlos aparte.

## Alternativas descartadas y por qué

- **Quitar las etiquetas al final**: se verían y se dirían mientras llegan.
- **Un filtro en la ventana, otro en la voz y otro al guardar**: tres reglas que tienen
  que coincidir, y lo que lee la charla después sería de una de ellas.
- **Marcar los gestos con su sitio en el texto en vez de con una marca entre lo que se
  corta en frases**: el corte en frases cambia el texto, quita el código y las marcas de
  formato, y saber qué sitio queda en qué frase sería otra cuenta, con sus fallos. La
  marca va dentro y sale con su frase.

## La lección

- familia: `prueba-que-no-puede-ver-lo-que-vigila`
- sin esto se repetiría: cambiar lo que llega a trozos y ajustar solo las pruebas que
  fallan. Dos de la ventana esperaban ver, mientras llega la respuesta, lo que el filtro
  guarda hasta el trozo siguiente: un blanco del final y unas comillas invertidas. Su
  modelo de mentira acaba solo a los 5 s, y lo que llegaba al acabar se veía un instante
  antes de redibujarse, así que pasaban por carrera: en local, siempre; en Quality, sobre
  la #702, una falló. Ahora esperan lo que se ve mientras llega, en menos tiempo del que
  tarda el modelo en acabar solo. Con lo que esperaban antes fallan siempre. Lo demás que
  salió al hacerla quedó arreglado antes de la revisión: los cinco trozos de la charla,
  una marca perdida dentro de un código y el ceño de la pieza B.
- lo hace cumplir: `tests/gui/test_conversation_ui.py`
