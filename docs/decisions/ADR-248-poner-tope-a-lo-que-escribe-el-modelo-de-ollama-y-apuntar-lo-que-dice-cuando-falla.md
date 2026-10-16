# ADR-248 — Poner tope a lo que escribe el modelo de Ollama y apuntar lo que dice cuando falla

- Estado: APROBADO
- Fecha: 2026-10-16
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). El tope no es nuevo: es el «Máximo de
  tokens de salida» que el propietario ya tiene en sus ajustes.

Este ADR es además la **nota de arranque** de este arreglo, en la misma rama que ADR-247
(`claude/la-cuenta-de-las-50-marcas`): las cuatro preguntas y el criterio de parada están
escritos antes del primer cambio de código y antes de cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Son dos, y salieron el 16-10-2026 en su
   ordenador, en la prueba a ciegas de E-R02-01.
   - **La pregunta 46 de 60, la sexta de `qwen3:4b-instruct`, se quedó más de 10 minutos
     sin avanzar.** `OllamaChatProvider._body`, en `src/sirius/adapters/llm/ollama_chat.py`,
     pide a Ollama un contexto, `num_ctx`, y ningún tope de lo que escribe. Sin
     `num_predict`, Ollama puede escribir sin fin, desplazando el contexto, y como no deja
     de llegar texto, el tope de lectura de httpx, 180 s sin nada, no salta nunca. Cuelga
     todo lo que habla con Ollama: la prueba a ciegas, las preguntas trampa, el juez, el
     sueño, la charla y la voz. El arreglo va en el proveedor de Ollama: pide como
     `num_predict` el mismo «Máximo de tokens de salida» de los ajustes que ya usa el de
     OpenAI, 4 096 si no dicen otro, y cada sitio que lo construye se lo da: la charla, el
     modelo de la charla que usan el juez y el sueño, y la prueba a ciegas, que construye
     el suyo por cada modelo. Una respuesta cortada por el tope, la que Ollama acaba con
     `done_reason` «length», se da por acabada, como hoy cualquier otra.
   - **El primer intento se cortó con «No se pudo completar la petición a Ollama.»**
     mientras, según el diario de Ollama, `gemma3:4b` contestaba bien, y no se puede saber
     por qué: el diario de Sirius apunta el código HTTP y nada de lo que dijo Ollama. El
     arreglo es que apunte también el texto del error que manda Ollama, recortado y sin
     nada de la charla, y en un fallo de red antes de contestar, qué fallo fue.

   **¿Puede el sitio del arreglo observar el fallo?** El tope, sí: es el proveedor quien
   pide a Ollama, y una prueba con un Ollama de mentira que no para de escribir mira lo que
   pide y lo que pasa. El diario, sí: el proveedor es quien recibe el error. Por qué Ollama
   cortó aquella vez no lo observa nadie desde aquí; lo dirá el diario la próxima.
2. **Qué NO garantiza.**
   - Que ninguna respuesta tarde mucho: con el tope, una respuesta acaba como mucho en
     4 096 tokens, que con un modelo lento pueden ser minutos.
   - Que el tope sea el bueno para cada uso: es el de la charla para todo, como en OpenAI.
     Afinarlo es producto, y no se decide aquí.
   - Que se sepa ya por qué falló el primer intento: eso lo dirá su diario la próxima vez,
     y solo si el diario apunta, que hoy deja de hacerlo al migrar la base: eso va en otro
     ADR de esta misma PR.
3. **Criterio de parada**, fijado antes de escribir código:
   - **Terminado** cuando una prueba con un Ollama de mentira que no para de escribir se
     ha visto fallar con el código de hoy y pasa con el arreglo, por los cuatro sitios que
     construyen el proveedor; una respuesta con `done_reason` «length» acaba como hoy; el
     diario apunta el texto del error de Ollama y el código, sin lo que se le dijo al
     modelo, y otra prueba lo mira; caen las mutaciones del tope y del diario; la cadena
     entera está en verde; y la revisión propia no encuentra nada.
   - **Si el tope pidiera decidir otro número** o tratar distinto una respuesta cortada,
     se para y se le pregunta: es producto.
4. **Qué lo haría imposible.**
   - Que una petición a Ollama no lleve tope: el proveedor no se puede construir sin él,
     porque lo pide con su valor por defecto, y lo manda en cada petición. Un sitio que lo
     construya sin leer sus ajustes llevaría el de serie, 4 096, nunca ninguno.
   - Que el diario lleve la charla: el texto del error se recorta, y lo que repita de lo que
     se le pidió al modelo se tacha antes de apuntarlo.

## Contexto y problema

Desde la 0.2 la charla va al Ollama de su ordenador (ADR-234), y con ella la prueba a
ciegas, las preguntas trampa, el juez, el sueño y, desde la 0.3, la voz. El proveedor de
OpenAI siempre ha pedido un tope de salida, el «Máximo de tokens de salida» de la pestaña
Configuración; el de Ollama, ninguno. El 16-10-2026, en su primera prueba a ciegas de
verdad, una respuesta no acabó en más de 10 minutos.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

1. **El mismo «Máximo de tokens de salida» que usa OpenAI**, como `num_predict`.
2. **Un tope propio de Ollama**, con su ajuste aparte.
3. **Un tope de tiempo** en vez de un tope de tokens.

## Decisión

La opción 1. Lo que quede por decidir al escribir el código se anota aquí con su porqué.

## Comprobación que la sostiene

Se escribe al acabar.

## Consecuencias

Se escriben al acabar.

## Alternativas descartadas y por qué

- **Un tope propio de Ollama** (opción 2): un ajuste nuevo es producto, y el que hay ya
  dice lo mismo.
- **Un tope de tiempo** (opción 3): cortaría también una respuesta buena de un modelo
  lento, y el texto sigue llegando, así que no hay silencio que medir.

## La lección

- ninguna: esta es la nota de arranque; si deja una lección, se escribe al acabar.

## Revisión externa

Va en la misma PR que ADR-247, y su alcance se suma al de allí: que toda petición a Ollama
lleve el tope de los ajustes, que una respuesta cortada por él acabe como hoy, y que el
diario diga lo que dijo Ollama sin nada de la charla.
