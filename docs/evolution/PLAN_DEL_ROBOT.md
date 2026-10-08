# Plan de Sirius, el robot

- Fecha: 2026-10-06
- Aprobado por el propietario el 06-10-2026, después de leerlo entero: «Me parece
  totalmente razonable». Lo registra ADR-232 y lo hace vigente la §20 del Rector de
  evolución.
- Quién lo lee: la sesión que vaya a empezar o a continuar una versión del robot. Llega
  aquí desde la tercera línea de `AGENTS.md` y de `README.md`, desde ADR-232 en
  `MEMORIA.md`, desde la §20 de `docs/evolution/RECTOR.md` y desde `docs/evolution/STATUS.md`.
- Caduca con: las decisiones del propietario y lo que mida cada versión al terminar. Las
  herramientas que nombra son las que recomendaron las investigaciones del 05-10-2026:
  antes de instalar una, se comprueba que sigue existiendo y cuál es su licencia.

Las seis decisiones del propietario del 05-10-2026 están en ADR-232. Al final de cada
versión pone de qué investigación sale cada cosa:

| Abreviatura | Investigación |
|---|---|
| inf. 1 | `docs/investigaciones/2026-10-05-personalidad-propia-estable-y-reconocible-para-sirius.md` |
| inf. 2 | `docs/investigaciones/2026-10-05-como-aprenden-los-robots-y-que-camino-tiene-sirius.md` |
| inf. 3 | `docs/investigaciones/2026-10-05-memoria-de-un-robot-companero-que-recuerde-bien-y-rapido.md` |
| inf. 4 | `docs/investigaciones/2026-10-05-como-se-organiza-el-cerebro-de-un-robot-social.md` |

## 1. El roadmap aprobado el 22-07-2026, revisado

| Versión aprobada | Qué pasa | Por qué |
|---|---|---|
| 0.2 Memoria útil | Se queda, y la personalidad entra delante | La personalidad es lo principal. La memoria está a medias y se aprovecha |
| 0.3 Habilidades y permisos | Fuera, aparcada | Era para que Sirius manejara el PC del propietario |
| 0.4 Delegación supervisada | Fuera, aparcada | Era para repartir trabajo entre agentes |
| 0.5 Voz | Se queda. Ahora escucha siempre y todo en local | Decisiones 4 y 6 |
| 0.6 Percepción y automatización digital | Se queda la cámara. Fuera la automatización | Lo digital era para el PC del propietario |
| 0.7 Puente de laboratorio y dispositivos | Se queda el puente con la cabeza. Fuera el laboratorio | Ese puente seguro es justo lo que necesita la cabeza |
| 1.0 Compañero en la habitación | Se queda | Sin el «proyecto real de ingeniería» |
| Nueva: Entrenarle | Entra | Aprender del propietario es el segundo pilar |

Lo que sale queda aparcado con su disparador en `docs/ideas/registro_de_ideas.yml`,
de I-010 a I-017. No se borra nada.

Orden nuevo:

1. 0.2 Sirius en texto: personalidad y memoria.
2. 0.3 Voz.
3. 0.4 Ojos.
4. 0.5 Entrenarle.
5. 0.6 Puente con la cabeza.
6. 1.0 Compañero en la habitación.

## 2. Dónde, quién y cuándo

- **Dónde.** Todo corre en el ordenador del propietario, con Windows. Nada sale a
  internet salvo búsquedas sueltas. El audio y el vídeo no salen nunca.
- **Sobre qué.** La app de Sirius que ya existe. No se empieza de cero.
- **Modelos.** En Ollama, que Sirius ya usa para clasificar recuerdos.
- **Quién.** Las sesiones programan en el repositorio y el propietario prueba en su
  ordenador. Cada versión acaba con una prueba suya, y sin ella no se pasa a la siguiente.
- **Cuándo.** Sumando lo que estiman las investigaciones, el cerebro entero son unos tres
  a cinco meses para una persona sola. Programando las sesiones, el ritmo lo marcan las
  pruebas del propietario. La cabeza va después.

## 3. Cómo empieza cada versión

La §17 del Rector pide, antes de empezar una versión, una definición de producto, unas
pruebas de aceptación reproducibles y una arquitectura aprobadas. Para las versiones del
robot, la §20 lo cumple así:

- **La definición y la arquitectura** son la sección de la versión en este plan, aprobada
  por el propietario el 06-10-2026.
- **Las pruebas de aceptación** se escriben antes de la primera línea de código de la
  versión, a partir de su «terminado cuando»: con pytest lo que una máquina puede
  comprobar, y paso a paso, como evaluación humana, lo que solo puede juzgar el
  propietario.
- **La versión termina** cuando pasan las dos.
- **0.6 y 1.0 solo tienen un esbozo.** Antes de activarlas hay que completar su sección
  como las demás, con qué se hace, con qué, qué no se usa y cuándo termina, y que el
  propietario la apruebe.

## 4. Versión 0.2 · Sirius en texto: personalidad y memoria

**Ya está hecho en Sirius y se reutiliza**

- La app de escritorio con conversación, historial y memoria en SQLite.
- La identidad guardada por versiones (`src/sirius/domain/identity.py`). Ahí va su
  semilla nueva.
- Recuerdos con su origen, sugerencias que el propietario confirma o rechaza, corregir,
  borrar y archivar.
- Avisos de contradicción entre recuerdos, y decisiones con versiones. Es el «eso no es
  así» que piden las investigaciones 2 y 3.
- Búsqueda por palabras y un presupuesto de lo que entra en cada respuesta.
- Ollama conectado.

**Personalidad: lo que se hace**

1. Semilla nueva con las palabras del propietario, las de la enmienda del manual
   (`docs/evolution/ENMIENDA_MANUAL_IDENTIDAD_2026-10.md`). Se escribe como valores y
   razones, no como prohibiciones. Lleva de 15 a 20 ejemplos de charla. Los ejemplos no
   son frases que repita: le enseñan el tono.
   En cada turno ve los 3 que más se parecen a la charla, cada vez en distinto orden, y
   todos quedan guardados para entrenarle (ADR-240).
2. La charla pasa a un modelo local. Hoy va por OpenAI. Se añade el conector de Ollama
   para conversar, sobre la pieza que ya existe para cambiar de modelo.
3. Su propia memoria: quién es, qué opiniones ha dado y qué bromas funcionaron y cuáles
   no. Así no se contradice sin motivo ni repite chistes.
4. «Ponte serio» le cambia de modo. Vacila al entrar y luego va al grano. «Para» corta el
   pique.
5. Dos botones en cada respuesta: «eso es Sirius» y «eso no». Sirven ya como ejemplos y
   después para entrenarle.
6. Contra la deriva: la semilla se le recuerda en cada turno y la charla larga se resume
   cada 15 a 20 turnos. En las pruebas que cita inf. 1, sin esto se desdibuja a las ocho
   rondas.
7. Un juez: el modelo puntúa cada respuesta en «suena a Sirius» y avisa si baja.
8. Contra el pelota: 40 preguntas trampa, con ideas malas del propietario en las que
   Sirius tiene que discutirle.
9. Prueba a ciegas: 20 preguntas a 2 o 3 modelos locales que quepan en el ordenador, de
   las familias Qwen, Gemma y Mistral. El propietario ve las respuestas barajadas y sin
   nombre, y elige.

**Memoria: lo que se hace**

1. Banco propio de 100 casos en español: personas, gustos, cosas que cambian, fechas,
   decir «no lo sé», quién dijo qué y «olvida eso». Sustituye al banco de 47 casos, que
   medía memoria de ingeniería.
2. Búsqueda por significado, además de por palabras. Va dentro de la misma base de datos
   y tarda milisegundos.
3. Hechos con fecha de inicio y de fin, quién lo dijo y con qué seguridad. Lo que dice
   Sirius nunca cuenta como hecho del propietario.
4. «Sueño» nocturno: con el ordenador libre, el modelo resume el día y propone hechos
   nuevos. Quedan pendientes del sí del propietario.
5. Una ficha por persona. Ahí se juntan las charlas y, desde 0.4, su cara y su voz.
6. Por voz o por texto: «eso no es así», «olvida eso» y «¿qué sabes de mí?». Olvidar
   borra de verdad, también de los resúmenes.

**Se deja de hacer**

- El filtro con Ollama dentro de cada respuesta y el etiquetado por categorías. Es lo que
  falla hoy: en el banco de 47 casos el camino real acierta entre 4 y 7, y tarda hasta
  780 ms (`docs/evolution/STATUS.md:306-307`). El propietario dijo que ni 29 le valía.
  Inf. 3 dice que el modelo no debe meterse en el turno. La búsqueda por significado lo
  sustituye.

**Con qué**

| Pieza | Para qué |
|---|---|
| Ollama | Correr los modelos en el ordenador del propietario |
| sqlite-vec | Búsqueda por significado dentro de SQLite |
| Qwen3-Embedding 0.6B o EmbeddingGemma | Convertir frases en números para buscar por significado |
| FTS5 | Búsqueda por palabras. Ya está |

**No se usa:** Mem0, Letta, Graphiti ni LangMem. Sus cifras las publica quien los vende y
no ganan a un buen sistema sencillo. Se copian sus ideas.

**Terminado cuando**

- El propietario ha elegido modelo a ciegas.
- 8 de cada 10 respuestas le suenan a Sirius.
- Le lleva la contraria en las ideas malas del banco.
- El banco de memoria pasa.
- Buscar en la memoria tarda menos de 150 ms por respuesta.

**Parte del propietario:** hacer la semilla con la sesión, la prueba a ciegas y marcar
respuestas.
**Dinero:** 0 €.
**Sale de:** inf. 1 §2 y su etapa 0. Inf. 3 §1.8, §2, §3, §5 y §7.
**Pruebas de aceptación:** `docs/evolution/PRUEBAS_0.2_DEL_ROBOT.md`, escritas antes del
código (ADR-233).

## 5. Versión 0.3 · Voz

**Ya está hecho en Sirius**

- Oír por el micro, pasar a texto, hablar y reproducir en Windows. Lo hizo Model Studio
  (`src/sirius/application/studio_voice.py`).
- Preparar el texto para leerlo en voz alta.
- Hoy va con OpenAI y por turnos. Eso cambia.

**Lo que se hace**

1. Una tubería de voz en tiempo real con Pipecat. Ya resuelve escuchar, saber cuándo ha
   terminado de hablar el propietario, empezar a hablar mientras piensa y dejar que le
   corten. No se programa desde cero.
2. Oír en local: Silero detecta si hay voz, Smart Turn decide si ha terminado y
   faster-whisper lo pasa a texto.
3. Hablar en local con Piper en español de España, para tener voz desde el primer día.
4. Escucha siempre, con un indicador en pantalla y botón de silencio. No guarda audio.
5. Distingue cuándo le hablan a él: su nombre, el contexto y, desde 0.4, si le miran. La
   tele y el teléfono no son órdenes.
6. Al principio, mientras habla no escucha. Después, cancelación de eco por software para
   poder cortarle.
7. Elegir su voz: 5 frases típicas suyas con 4 a 6 voces, a ciegas, por el altavoz. Entre
   ellas Piper y una voz de personaje propia con Chatterbox. Clonar a alguien, solo con su
   permiso por escrito.

**Con qué**

| Pieza | Para qué |
|---|---|
| Pipecat | La tubería de voz entera |
| Silero VAD | Saber si alguien habla |
| Smart Turn v3 | Saber si ha terminado. Según quien lo hace, acierta un 90 % en español |
| faster-whisper | Voz a texto en local |
| Piper | Texto a voz en local, rápido |
| Chatterbox | Voz de personaje propia, según inf. 1 |

**No se usa:** voz a voz en la nube. Es más rápida, pero ata a un proveedor y no deja
meter su memoria ni sus gestos.

**Terminado cuando**

- Tarda menos de 1,5 s desde que el propietario acaba hasta que suena.
- Se le puede cortar.
- El propietario aguanta 20 minutos de charla sin que canse.
- No contesta a la tele.

**Dinero:** 0 €. Si la cancelación por software no basta, un micro con cancelación de eco
de unos 60 €, que se le pregunta al propietario cuando haga falta.
**Sale de:** inf. 4 §3, §5 y §8. Inf. 1 §3.4 y su etapa 1.

## 6. Versión 0.4 · Ojos

**Ya está hecho:** nada de cámara. La captura que existe es la de grabar vídeo con OBS de
Model Studio, que no sirve para esto.

**Lo que se hace**

1. Cámara del ordenador. Detecta caras con MediaPipe, en local.
2. Reconoce a quien dé permiso: su cara con InsightFace y su voz con ECAPA. Las huellas
   van cifradas y no salen del ordenador. A un desconocido lo trata como «sin
   identificar» y no guarda su huella.
3. La regla del propietario con críos y ancianos frágiles: estima la edad con la cámara.
   Ante la duda, no insulta.
4. Su cara, dentro de la app: ojos, párpados, cejas y boca dibujados.
5. Vida en reposo: parpadea sin ritmo fijo, mueve un poco los ojos y «respira». Es la
   capa base del busto de Disney y lo que más vida da.
6. Mira a quien habla y aparta la vista al pensar. La boca se mueve con el volumen de su
   voz.
7. Gestos de una lista cerrada. El modelo escribe la respuesta con etiquetas como
   [ceja_arriba]. La cara las hace y lo que no está en la lista se ignora. Es la misma
   lista que usará la cabeza.
8. Recuerda lo que ve como texto: quién vino, a qué hora y qué cambió. No guarda imágenes.

**Con qué**

| Pieza | Para qué |
|---|---|
| MediaPipe | Detectar caras |
| InsightFace | Reconocer caras y estimar la edad |
| SpeechBrain ECAPA | Reconocer voces |
| La app de Sirius | Dibujar su cara |

**No se usa:** mapas del cuarto. Sirius no se mueve.

**Terminado cuando**

- Mira al propietario cuando habla.
- Reconoce a los que dieron permiso.
- No insulta a un crío en la prueba.
- Nunca se queda congelado, aunque el modelo tarde.

**Dinero:** 0 €.
**Sale de:** inf. 4 §1 y §9. Inf. 1 §3 y su etapa 2. Inf. 3 §4. Inf. 2 §1g y §6.

## 7. Versión 0.5 · Entrenarle

**Cuándo:** cuando haya unas 500 respuestas marcadas «eso es Sirius».

**Lo que se hace**

1. Se entrena el modelo elegido con las marcadas. Las «eso no» le enseñan lo que no es.
2. Se pasa a Ollama y se compara a ciegas con el Sirius de solo semilla.
3. Semilla, marcas, memoria y voz se guardan con copia. Si cambia el modelo, se reentrena
   con lo mismo.

**Con qué:** Unsloth, abierto, para entrenar en ordenadores normales.

**Ojo:** se marca si «es Sirius», no si gusta. Premiar lo que agrada volvió pelota a
ChatGPT en abril de 2025.

**Terminado cuando:** el entrenado gana a ciegas.
**Dinero:** 0 € si cabe en el ordenador. Si no cabe, la primera salida es un modelo más
pequeño en el mismo ordenador. Alquilar una GPU unas horas costaría decenas de euros y
sacaría del ordenador las respuestas marcadas, que son conversaciones del propietario: va
contra EV-023, así que solo con una decisión nueva suya sobre sus datos y su dinero.
**Sale de:** inf. 1 §2.4, §2.8 y §4.3.

## 8. Versión 0.6 · Puente con la cabeza, y la 1.0

Aparcadas hasta terminar 0.5. Esto es un esbozo, no su definición: antes de activarlas se
completa su sección como las demás y la aprueba el propietario. Ya se sabe cómo serán:

- Un controlador con límites y perro guardián: si el ordenador deja de hablarle, la
  cabeza va a una postura segura. Una seta corta los servos.
- Servos de bus en el cuello, que dicen dónde están y si se atascan.
- El modelo nunca manda ángulos. Pide gestos de la misma lista que la cara en pantalla.
- Labios: primero por reglas con Rhubarb, luego aprendidos mirándose y viendo vídeos,
  como la cara de Columbia.
- Calibra solo la mirada con su cámara.
- Antes de diseñar, se mira el software abierto de Reachy Mini.

La cabeza física es HEAD-R1 (`docs/robotics/head/`), con su propio Rector para la
mecánica, la electrónica y la seguridad. Sigue inactiva y sin compras.

**Sale de:** inf. 4 §7 y §9. Inf. 2 §1g, §5 y su plan. Rector de evolución §12.

## 9. Cómo aprende, y cuándo

| De qué | Cómo | Versión |
|---|---|---|
| Del propietario | Sus marcas, sus gustos y costumbres, y el «sueño» que propone y él aprueba | 0.2 |
| De sí mismo | Su memoria de opiniones y bromas, el juez y la revisión nocturna | 0.2 |
| Del entorno | Quién hay, a qué hora y qué cambia | 0.4 |
| Del propietario, a fondo | Se le entrena con lo marcado | 0.5 |
| De cómo se mueve | Calibra la mirada y aprende los labios | 0.6 |

Los robots que aprenden viendo vídeos son brazos con manos. En una cabeza, eso solo sirve
para los labios.

## 10. Riesgos, y qué se hace con ellos

- **La gracia de los modelos pequeños.** Inf. 1 e inf. 4 dicen que flojea en español. Por
  eso la prueba a ciegas va primero. Si ninguno pasa, se le entrena o se usa uno mayor.
- **El ordenador.** Con 6 GB en la gráfica, modelo, oído y voz a la vez van justos. Si no
  caben, el oído y la voz van al procesador. Se mide al empezar 0.3.
- **Python.** Sirius usa Python 3.14. Alguna pieza de voz o de visión quizá no esté aún
  para esa versión. Si pasa, va en un proceso aparte, sin que cambie nada para el
  propietario.
- **Pipecat en Windows.** Se comprueba el primer día de 0.3.

## 11. Lo que queda aparcado

- Las decisiones D-1 a D-5 de `docs/audits/decisiones-abiertas-del-propietario.md`, que
  eran del banco de 47 casos. La D-6 no es del banco y sigue abierta.
- La propuesta 8 de la mina de septiembre, la skill de encargos, que es del motor.
- Model Studio se queda como está. Su voz se aprovecha.
- La cabeza física HEAD-R1 sigue inactiva.
- El motor de trabajo no cambia: el propietario volverá sobre él.
