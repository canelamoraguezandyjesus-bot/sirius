# ADR-246 — Elegir su voz a ciegas: la pieza F de la voz

- Estado: APROBADO
- Fecha: 2026-10-16
- Aprobación: la fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el
  head de contenido y Quality en verde (ADR-205). La pieza y su orden los aprobó el
  propietario con el plan (ADR-232) y con la tabla de piezas de ADR-241, que es la última
  de la 0.3.

Este ADR es además la **nota de arranque** de la rama de la pieza F (skill
`disciplina-evidencia`): las cuatro preguntas, el criterio de parada y el alcance de la
revisión están escritos antes del primer cambio de código de la pieza y antes de
cualquier revisión.

## Nota de arranque

1. **Dónde vive el fallo y dónde va el arreglo.** Hoy Sirius habla con una sola voz,
   `es_ES-davefx-medium`, la que puso la pieza C (`SpeakingVoice` en
   `src/sirius/config/local_voice.py`), y no hay forma de elegir otra. Las tres pruebas de
   la pieza F esperan en `xfail` estricto (PA-R03-10): la hoja de voces, la voz elegida
   que queda para hablar y que no haya forma de clonar una voz. El arreglo va en cinco
   sitios:
   - **El catálogo de voces**, cerrado como todos los ajustes de la voz: las cuatro
     masculinas de Piper en español de España que nombra ADR-241 (`davefx`, `sharvard`,
     `carlfm` y una de `mls`) y la de personaje con Chatterbox, que es su voz de serie, sin
     audio de nadie. Cinco candidatas.
   - **La prueba de voces**, un caso de uso: cinco frases fijas, típicas suyas (cuatro
     respuestas de la semilla que escribió él, un saludo, una broma, una pregunta y una
     frase larga, y otra con un número y una fecha); cada candidata dice las cinco con su
     voz al abrir la hoja, y las muestras viven en memoria (PA-R03-05). Las candidatas van
     barajadas y con etiquetas sin nombre; escuchar una muestra la pone por el altavoz;
     elegir guarda la voz.
   - **La voz elegida**, en los ajustes, como un valor del catálogo: con ella se carga la
     voz al abrir Sirius, y desde el turno siguiente sin volver a abrirlo: el oído cierra el
     altavoz de la voz de antes y carga la nueva.
   - **La voz de personaje**: un adaptador de Chatterbox que carga su modelo de la carpeta
     de modelos de Sirius, habla en español y nunca recibe audio de referencia. Va en un
     extra aparte, `personaje`, y la orden de instalar baja sus pesos; Sirius no baja nada
     en marcha (PA-R03-08).
   - **La ventana**: un botón que abre la hoja, con un botón por muestra y otro para
     elegir cada voz. La juzga E-R03-06.

   **¿Puede el sitio del arreglo observar el fallo?** Que la hoja dé lo que piden las
   pruebas, sí: el caso de uso sabe qué voz hay tras cada etiqueta y qué muestra salió de
   cada una. Que una voz le suene masculina, de España y a Sirius, no: eso lo dice él, por
   su altavoz (E-R03-06).
2. **Qué NO garantiza.**
   - Cómo suena la voz de serie de Chatterbox. Desde el contenedor no se llega a Hugging
     Face (el proxy responde 403), así que no se ha bajado ni oído. Si no le suena a Sirius
     no la elegirá; una voz de personaje distinta sería producto, y se le preguntaría.
   - Que Chatterbox hable en vivo a tiempo. Con el torch de PyPI para Windows va por el
     procesador: las muestras de la hoja salen, despacio. Si la elige y no puede hablar en
     vivo con la charla cargada, se le dice con la cifra y se le pregunta (E-R03-06).
   - Que se instale en su Windows. Solo se ha resuelto: con el extra `voz` y Python 3.14,
     se resuelve; `spacy-pkuseg`, que solo sirve para el chino y Chatterbox importa dentro
     de un `try`, no tiene rueda para Windows con 3.14 y se deja fuera, con `gradio`, que
     es de sus demos.
   - Que las cuatro de Piper sean masculinas: lo dice ADR-241, y lo oye él.
   - Que la biblioteca no sepa clonar: sí sabe (`audio_prompt_path`). Lo que se garantiza
     es que ningún camino de Sirius se lo pide.
3. **Criterio de parada**, fijado antes de ver ninguna prueba ni ninguna revisión:
   - **La pieza está terminada** cuando sus tres pruebas corren y pasan con el conductor de
     verdad, sin `xfail`; la tabla de `PRUEBAS_0.3_DEL_ROBOT.md` lo dice de PA-R03-10; la
     batería entera y la cadena de comprobación están en verde; la revisión propia no
     encuentra nada; y hay una ronda limpia de Codex sobre el head de contenido con
     Quality en verde. Con ella acaba la 0.3 en máquina; quedan las evaluaciones del
     propietario.
   - **Revisión propia antes de pedir otra**, y dos rondas seguidas con hallazgos de la
     misma familia: se deja de parchear y se busca la raíz (ADR-001).
   - **Cada regla nueva, con una prueba que la tumbe** en mutación.
   - **Si la voz de personaje no se puede instalar o no habla en su ordenador**, se para y
     se le dice con la cifra: es producto.
   - Si algo pide dinero o cambia el producto, se para y se le pregunta.
4. **Qué lo haría imposible.**
   - Clonar: que ningún puerto ni adaptador tenga por dónde recibir un audio. La voz solo
     recibe texto, el adaptador de Chatterbox no expone el audio de referencia y los
     ajustes no tienen rutas; una prueba lo mira y una mutación que añada ese parámetro la
     tumba.
   - Que se guarde el audio de las muestras: viven en memoria, y el conductor mira el disco
     (PA-R03-05).

**Lo aprendido en las piezas B a E, aplicado desde el principio** (ADR-242 a ADR-245):

- Una garantía va en el único sitio por el que pasan todos los caminos.
- Lo que se decide de algo, con el estado de cuando pasó, no con el de cuando se atiende.
- Lo que se decide con las palabras no se apunta en el diario con ellas.
- Un dato nuevo va por todos los caminos que lo leen, no solo por el que se está mirando.

## Contexto y problema

ADR-241 dejó la 0.3 en seis piezas, con sus pruebas de aceptación escritas antes del
código; la B a la E ya han entrado. La pieza F es «Elegir su voz a ciegas, con las de Piper
y una de personaje con Chatterbox» (PLAN_DEL_ROBOT, «Lo que se hace», 7: «5 frases típicas
suyas con 4 a 6 voces, a ciegas, por el altavoz. Entre ellas Piper y una voz de personaje
propia con Chatterbox. Clonar a alguien, solo con su permiso por escrito»).

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, punto 3.

## Opciones consideradas

Para la voz de personaje:

1. **La voz de serie de Chatterbox**, sin audio de referencia: no imita a nadie conocido.
2. **Chatterbox con una de Piper de referencia**: imitaría al locutor de esa voz.
3. **Mezclar varias voces de referencia**: una voz nueva, pero hecha con las de otros.
4. **Grabar una voz propia**: es clonar a alguien, y el plan pide su permiso por escrito.

Para cuándo vale la voz elegida:

- **Desde el turno siguiente**, cerrando el altavoz de la de antes.
- **Al volver a abrir Sirius**: más simple, pero elegir no se notaría hasta reiniciar.

## Decisión

La opción 1, y la voz elegida vale desde el turno siguiente. Lo que quede por decidir al
escribir el código se anota aquí con su porqué.

## Comprobación que la sostiene

Se escribe al acabar.

## Consecuencias

Se escriben al acabar.

## Alternativas descartadas y por qué

- **Chatterbox con una voz de referencia** (opciones 2 y 3): imita, aunque sea a medias, a
  quien grabó esas voces.
- **Grabar una voz propia** (opción 4): es clonar, y necesita su permiso por escrito.

## La lección

- ninguna: esta es la nota de arranque; si la pieza deja una lección, se escribe al
  acabarla.

## Revisión externa

Alcance, escrito antes de la primera petición: esta PR trae la pieza F y nada más. Mira que
la hoja dé cinco frases con cinco voces barajadas y sin nombre, que cada muestra salga de
su voz y suene por el altavoz, que la elegida quede para hablar, también la de personaje,
y que ningún camino de Sirius acepte un audio para imitar una voz.
