# ADR-256 — Cortar la respuesta cuando el modelo se inventa el turno del propietario

- Estado: APROBADO
- Fecha: 2026-10-18
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205).

## Nota de arranque

Publicada antes del primer commit en la incidencia #700. Aquí, resumida; la incidencia la
tiene entera.

1. **Dónde vive el fallo y dónde va el arreglo.** Las instrucciones de la charla, de la
   prueba a ciegas, de las preguntas trampa y de la voz de las órdenes de memoria llevan
   ejemplos escritos como diálogo, `Él: «…»` y `Sirius: «…»`, y la charla, además, los
   mensajes recientes como `[user] …` y `[sirius] …`. A Ollama no se le pedía ninguna
   parada: un modelo pequeño que siga el diálogo escribe el turno del propietario, se lo
   contesta y sigue, hasta el tope de 4.096 tokens. El arreglo va en la petición: lleva
   como paradas los comienzos de turno de sus instrucciones, y el adaptador de Ollama se
   las pasa en `options.stop`. **¿Puede el sitio del arreglo observar el fallo?** Sí: quien
   escribe las instrucciones sabe qué turnos hay en ellas, y Ollama corta en cuanto el
   modelo empieza uno.
2. **Qué NO garantiza.** Que deje de enrollarse por otro camino, que quite una etiqueta
   `Sirius:` al principio de la respuesta, ni que los modelos dejen de inventarse cosas.
   Con OpenAI no cambia nada. No se ha visto con un modelo de verdad.
3. **Criterio de parada.** Con el código de antes, la petición a Ollama no lleva paradas;
   con el arreglo, las cuatro peticiones llevan los comienzos de turno de sus
   instrucciones, visto fallar antes. Cada regla con su mutación y la batería entera en
   verde. Dos rondas de revisión con la misma familia: se para y se busca la raíz.
4. **Qué lo haría imposible en vez de improbable.** Quitar de las instrucciones el formato
   de diálogo. Es cambiar la semilla que escribió el propietario y cómo lee la charla el
   modelo, y eso no se hace sin él.

## Contexto y problema

El 18-10-2026, en la prueba a ciegas, el propietario eligió gemma3:4b en 16 de 20
preguntas, y de los tres modelos dijo que se inventan cosas, que «se quedan pillados
haciendo respuestas, respuestas, respuestas» y que dicen frases sin sentido.

Lo de inventarse cosas y las frases sin sentido es del tamaño del modelo, y eso no lo
arregla el código. Lo de quedarse escribiendo respuesta tras respuesta tiene una parte que
sí es nuestra. Así se escriben los ejemplos de la semilla desde ADR-240:

```
Así reaccionaste en algo parecido. Coge la actitud, no las palabras.

Él: «Buenos días, Sirius.»
Sirius: «Buenos días, jefe.»
```

Y la charla lleva los mensajes recientes así: `[user] …` y `[sirius] …`. Es un diálogo
escrito, y un modelo pequeño tiende a seguirlo: acaba su respuesta, escribe `Él: «…»` con
algo que el propietario no ha dicho, lo contesta, y vuelve a empezar. Nada lo paraba
antes del tope de salida, 4.096 tokens (ADR-248), que en su ordenador son minutos de
texto. En voz, Sirius leería en alto los turnos inventados.

En la nube no hay Ollama, así que no se ha podido ver con su modelo: es lo que el código
permite y lo que él describe. La confirmación es suya, en su ordenador.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

1. **A, paradas en la petición.** Cada petición lleva los comienzos de turno que hay en
   sus instrucciones, y Ollama deja de escribir en cuanto el modelo empieza uno. No toca
   nada de lo que el propietario escribió.
2. **B, escribir los ejemplos sin turnos.** Por ejemplo, «Si te dicen …, contestas algo
   como …». Quita la invitación de raíz, pero cambia la semilla, que es suya, y cómo la lee
   el modelo desde ADR-240.
3. **C, bajar el tope de salida para charlar.** Acorta el daño, pero el tope de 4.096 es el
   de la arquitectura de la 0.1 (S9), y una respuesta larga de verdad se quedaría a medias.

## Decisión

La opción A: cada petición que lleva diálogo en sus instrucciones lleva sus comienzos de
turno como paradas, y Ollama deja de escribir en cuanto el modelo empieza uno.

- **Las paradas de los ejemplos**, `example_turns` en `src/sirius/domain/robot_seed.py`,
  junto a `render_examples`, que es quien los escribe: un salto de línea y quién habla,
  sin repetir, y `Sirius`. Sin ejemplos, ninguna.
- **Las de los mensajes recientes**, `RECENT_MESSAGE_TURNS` en
  `src/sirius/application/send_message.py`, junto a `render_recent_message`: `\n[user]` y
  `\n[sirius]`. `context_turns` junta las dos, y las de los mensajes solo si la petición
  los lleva.
- **El puerto**, `LLMRequest.stop`, vacío si no se dice otra cosa.
- **Las cuatro peticiones que llevan ejemplos**: la charla, con `context_turns`; la voz de
  las órdenes, la prueba a ciegas y las preguntas trampa, con los turnos de sus ejemplos.
  El juez, el sueño y el resumen no llevan diálogo que seguir y no cambian.
- **Ollama** las recibe en `options.stop`. OpenAI no: su API de respuestas no tiene
  paradas.

## Comprobación que la sostiene

- **Las pruebas nuevas**, 9: 7 en `tests/unit/test_paradas_de_turno.py` y 2 en
  `tests/integration/test_paradas_de_turno_en_la_charla.py`. Miran que cada parada es como
  empieza un turno en lo que lee el modelo, que Ollama las recibe, y que la charla, la voz
  de las órdenes, la prueba a ciegas y las preguntas trampa llevan exactamente los
  comienzos de turno de sus instrucciones; la charla, los de los mensajes recientes solo
  desde el segundo turno, que es cuando los lleva. Con el código de antes no pueden ni
  cargar: no existen ni las paradas ni quien las calcula.
- **Mutación**: 10, cada una con su caché de bytecode vacía, restaurada y con su hash
  comprobado, y caen las 10. Son que Ollama no las pase, que los ejemplos no den paradas o
  falte la de Sirius, que cada una de las cuatro peticiones vaya sin ellas, que falten las
  de los mensajes recientes, que se pongan aunque no haya mensajes, y que los mensajes no
  den ninguna.
- **ruff** limpio.

## Consecuencias

- Un modelo que siga el diálogo de sus instrucciones deja de escribir en cuanto empieza
  un turno. Lo escrito hasta ahí es su respuesta, como cualquier otra.
- Una petición nueva que lleve ejemplos o mensajes por turnos tiene que llevar sus
  paradas, o vuelve el fallo.

**Qué NO garantiza, después del código:**
- Que deje de enrollarse por otro camino: un monólogo largo que no abra turno sigue hasta
  el tope.
- Que quite una etiqueta `Sirius:` o `[sirius]` al principio de la respuesta, si el modelo
  la escribe.
- Que los modelos dejen de inventarse cosas o de decir frases sin sentido: eso es del
  modelo.
- Con OpenAI no cambia nada.
- Una respuesta que de verdad tenga una línea que empiece por `Él:` o `Sirius:` se corta
  ahí. En lo que contesta Sirius es raro, y se acepta.
- No se ha visto con un modelo de verdad: la confirmación es del propietario, en su
  ordenador.

## Alternativas descartadas y por qué

B y C, por lo dicho en las opciones. B queda como la salida de raíz si las paradas no
bastan, y se le preguntaría al propietario, porque cambia lo que él escribió.

## La lección

- familia: `turnos-en-las-instrucciones-sin-parada`
- sin esto se repetiría: un modelo pequeño seguiría el diálogo de sus instrucciones hasta su tope
- lo hace cumplir: `tests/unit/test_paradas_de_turno.py`

## Revisión externa

Va en su PR, con ADR-257. Su alcance: que cada petición con ejemplos o mensajes por turnos
lleve exactamente sus comienzos de turno como paradas, que Ollama las reciba, y que las
peticiones sin diálogo no cambien. Las rondas se anotan aquí.
