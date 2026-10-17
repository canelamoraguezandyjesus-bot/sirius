# ADR-248 — Poner tope a lo que escribe Ollama y apuntar sus errores

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

La opción 1: `num_predict` con el «Máximo de tokens de salida» de los ajustes.

El proveedor de Ollama lo pide en cada petición, 4 096 si los ajustes no dicen otro, como el
de OpenAI. Al escribir el código se decidió además:

- **Un solo sitio lee el tope**: `resolve_max_output_tokens`, en
  `src/sirius/config/llm_provider_settings.py`, con la misma clave y la misma validación
  que tenía OpenAI, que ahora también la usa. La clave conserva su nombre de la 0.1,
  `openai_max_output_tokens`, porque es la que guarda la pestaña Configuración.
- **Quién lo pasa**: la charla y el modelo de la charla que usan el juez y el sueño, con
  los ajustes de la charla; la prueba a ciegas, que pregunta a modelos aún sin elegir, lo
  lee de los ajustes al construir cada uno, y si están mal puestos usa el de serie: elegir
  modelo no se para por eso, y la charla ya dice qué está mal. Las preguntas trampa usan el
  de la charla.
- **El proveedor no se puede construir sin tope**: si nadie se lo da, lleva el de serie.
- **Una respuesta cortada por el tope** acaba como hoy cualquier otra: con lo escrito.
- **El diario** apunta, cuando Ollama contesta con un error, el código HTTP y su texto; con
  un error a mitad de respuesta, su texto; y con un fallo de red antes de contestar, cuál
  fue. El texto va en una línea, recortado a 300 caracteres, y lo que repita de lo que se
  le pidió al modelo, cada línea de 12 caracteres o más de las instrucciones y de lo que
  dijo él, se tacha antes de apuntarlo.

## Comprobación que la sostiene

- **El cuelgue, visto antes de arreglarlo**, con un Ollama de mentira que sin tope escribe
  50 000 trozos y con él para ahí, con `done_reason` «length»
  (`tests/integration/test_tope_de_salida_de_ollama.py`): con el código de `main`, la
  charla, las preguntas trampa con su juez y la prueba a ciegas pedían sin tope. Con el
  arreglo, las tres piden el de los ajustes, 5 en la prueba, y acaban en él.
- **El proveedor** (`tests/unit/test_ollama_chat_provider.py`): pide el tope que le dan y
  4 096 si no le dan ninguno; con el Ollama que no para, acaba en el tope; una respuesta
  cortada por él acaba con lo escrito; y el diario dice el código y el texto de Ollama, el
  error a mitad de respuesta, el fallo de red y cuál fue, tacha lo que repita de la charla
  y recorta lo largo.
- **Mutación**: 9, caen las 9: sin `num_predict` en la petición; la charla, el juez y la
  prueba a ciegas, cada uno sin el tope de sus ajustes; el diario sin tachar, sin recortar,
  y sin el texto en cada uno de sus tres casos.
- **Las pruebas que tocan Ollama, sus ajustes y quien los usa**, 40 ficheros: 1 057 en
  verde, 2 omitidas y 2 `xfail`.
- **ruff** limpio; **mypy** sin errores en 734 ficheros.
- **La batería entera**, sobre `401ea5a1`, el árbol final de la PR: 8 847 en verde,
  14 omitidas y 2 `xfail`, ningún fallo, en 23 min 41 s.

## Consecuencias

- **Ninguna respuesta de Ollama pasa del tope**: la prueba a ciegas, las preguntas trampa,
  el juez, el sueño, la charla y la voz acaban como mucho en él.
- **Con 4 096 tokens, una respuesta puede tardar minutos** con un modelo lento, pero acaba.
- **Si él baja el «Máximo de tokens de salida»**, también se cortan antes las respuestas de
  Ollama, como pasaba con OpenAI.
- **Su diario dirá por qué falla Ollama la próxima vez**, si el diario apunta: por eso va en
  la misma PR que ADR-249.
- **Lo que Ollama repita de la charla en un error se tacha** si es una línea de 12
  caracteres o más; una más corta podría llegar al diario.

## Alternativas descartadas y por qué

- **Un tope propio de Ollama** (opción 2): un ajuste nuevo es producto, y el que hay ya
  dice lo mismo.
- **Un tope de tiempo** (opción 3): cortaría también una respuesta buena de un modelo
  lento, y el texto sigue llegando, así que no hay silencio que medir.

## Revisión propia

Antes de empujar se releyó el diff entero contra el código y la nota. Encontró una cosa,
arreglada: las pruebas del diario leían el registro de la raíz, que no ve lo que apunta
`sirius` cuando ya se configuró su diario en el mismo proceso; leen el registrador del
conector.

## La lección

- familia: `pieza-correcta-a-la-que-no-llama-quien-la-necesita`
- sin esto se repetiría: un proveedor nuevo sin las salvaguardas del de antes. El tope de
  salida de OpenAI existía, y el de Ollama, escrito después, no lo leía: sin él, una
  respuesta podía no acabar nunca (H-248).
- lo hace cumplir: `tests/integration/test_tope_de_salida_de_ollama.py`

## Revisión externa

Va en la misma PR que ADR-247, y su alcance se suma al de allí: que toda petición a Ollama
lleve el tope de los ajustes, que una respuesta cortada por él acabe como hoy, y que el
diario diga lo que dijo Ollama sin nada de la charla.
