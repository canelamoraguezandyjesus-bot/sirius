---
titulo: "Cómo darle a Sirius una personalidad propia, estable y reconocible"
fecha: 2026-10-05
autor: "claude.ai con «Investigación», por encargo de la sesión del giro al robot (ADR-232)"
pregunta: >-
  Cómo se consigue hoy que un robot tenga una personalidad propia, estable y
  reconocible, que genere por sí misma qué dice, cómo lo dice, cómo se mueve y cómo
  reacciona, sin guiones ni listas de frases, y qué es viable para una persona sola
  en casa.

nota: >-
  Encargada por la sesión del giro al robot (ADR-232) y hecha en claude.ai con
  «Investigación», porque la sesión no tiene buscador; el propietario la pegó en la
  sesión el 05-10-2026. Texto íntegro tal como llegó, salvo lo personal: el nombre
  del propietario se ha cambiado por «el propietario» y se ha quitado su región,
  porque el repositorio es público. Las etiquetas de hecho, inferencia y opinión son
  del informe; la sesión no ha verificado sus fuentes. El encargo describía la
  personalidad del manual v1.2, «provocador sin humillar»; el propietario la cambió
  el 05-10-2026 (ADR-232, decisiones 2 y 3), así que el borrador de ficha del
  informe vale por su forma, no por su contenido.
caduca_con:
  - >-
    los modelos y precios que cita, de pago y abiertos, que cambian cada pocos meses
  - >-
    las herramientas de voz y de turnos que nombra y sus licencias (Smart Turn, LiveKit, Chatterbox, Piper, Kokoro)
  - >-
    el estado de los productos que repasa (Vector y wire-pod, aibo, EMO, Furhat, Moxie, Reachy Mini)
  - >-
    la personalidad que pedía el encargo, ya cambiada por el propietario el 05-10-2026 (ADR-232)

estado: VIGENTE
---

# Sirius: cómo darle a un robot una personalidad propia, estable y reconocible (informe para el propietario, octubre de 2026)

La mejor manera hoy de dar a Sirius una personalidad propia no es entrenar un modelo ni prohibir los guiones. Es un **híbrido**: una ficha de personaje sólida y una memoria del propio Sirius encima de tu app de Python, un modelo potente por API que escribe lo que dice y además emite **etiquetas de emoción y gesto**, y un motor de animación local que convierte esas etiquetas en movimientos diseñados por ti, mezclados con movimiento automático de reposo. Así lo hicieron, con matices, Anki, Ameca, Furhat y Reachy Mini.

**Cómo leer este informe.** Cada afirmación lleva una etiqueta visible:
- **[Hecho]**: con fuente y fecha indicadas en la misma frase.
- **[Inferencia]**: deducción razonada a partir de hechos.
- **[Opinión]**: mi recomendación.

---

## Lo esencial (una pantalla)

1. **[Inferencia]** Ningún robot comercial de éxito genera su personalidad «sin guiones» al 100 %. Los que mejor funcionaron (Cozmo, Vector, aibo) mezclan animaciones diseñadas por humanos con un estado interno (emociones) que decide cuál usar. Los que usan LLM (Ameca, Furhat, Reachy Mini) dejan que el modelo hable y elija gestos de una **biblioteca diseñada**.
2. **[Opinión]** Para Sirius: el LLM genera las palabras y elige gesto, emoción e intensidad; tú diseñas unos 20–40 gestos base; un motor local los mezcla con parpadeo, respiración y mirada automáticos. Sin listas de frases, pero con una biblioteca de movimientos.
3. **[Hecho]** Lo que se define solo en el prompt se degrada en conversaciones largas: un estudio de Harvard presentado en COLM 2024 (Li, Liu, Bashkansky, Bau, Viégas, Pfister y Wattenberg, arXiv 2402.10962, julio de 2024) encontró «una deriva significativa de las instrucciones en ocho rondas de conversación» con LLaMA2-chat-70B y GPT-3.5. **[Opinión]** Por eso necesitas reinyectar la ficha, una memoria del propio Sirius y una comprobación automática del carácter.
4. **[Hecho]** El mayor enemigo de un Sirius «honesto y crítico» es la **adulación**: OpenAI retiró una actualización de GPT-4o en abril de 2025 porque era «excesivamente halagadora o complaciente», a menudo descrita como aduladora (OpenAI, «Sycophancy in GPT-4o», 29 abr 2025). **[Opinión]** Hay que diseñar contra esto desde el primer día.
5. **[Opinión]** Empieza **por la API**, no por entrenar. El ajuste fino (LoRA) solo compensa más adelante, cuando tengas cientos de conversaciones buenas de Sirius y quieras pasar a local o abaratar.
6. **[Opinión]** Tu lista de piezas está incompleta: para mirar a la cara y para que puedas interrumpirle necesitas **cámara**, **micrófono (mejor un array)** y **cancelación de eco**. Sin eso, la personalidad se nota mucho menos.
7. **[Opinión]** La primera cabeza debería tener **menos ejes**: cuello de 2 ejes y ojos en pantalla (o ojos de 2 ejes con párpados simples). Deja cejas y mandíbula mecánicas para la fase 2.
8. **[Inferencia]** Coste: con API, entre unos 5 y 40 € al mes con uso diario moderado (cadena voz-texto-voz), y más con API de voz en tiempo real. El PC y la GPU van **aparte** de los 900–2.500 € del robot.

---

## 1. Cómo lo han hecho empresas y laboratorios reales

**En resumen:** los robots con más «alma» combinan tres cosas: animadores profesionales, un estado interno sencillo (emociones, energía) y un sistema que elige y mezcla animaciones. Los LLM se añadieron después para la conversación, casi nunca para el movimiento fino.

### 1.1 Tabla comparativa

| Robot | Diseño humano | Modelo (IA) | Estado interno | Qué funcionó / qué no | Destino (oct 2026) |
|---|---|---|---|---|---|
| **Anki Cozmo / Vector** | Animadores de Pixar y DreamWorks; cientos de animaciones | Visión, caras; Vector con voz en la nube | «Motor de emociones» | Sí: muy expresivo con pocos motores. No: dependencia de la nube | Anki quebró en 2019; Digital Dream Labs (DDL); comunidad wire-pod activa |
| **Sony aibo (ERS-1000)** | Comportamientos de perro diseñados | IA en la nube que acumula recuerdos | Personalidad que «crece» | Sí: vínculo a largo plazo. No: caro, nube obligatoria | Activo; fin de ventas en Japón (jun 2026) |
| **Jibo** | Equipo de personaje y animación (detalles no públicos) | Servicios en la nube | No documentado | Sí: encanto. No: caro y poco útil | Servidores apagados en marzo de 2019 |
| **Disney (BD-X, Olaf)** | Animadores definen el movimiento | Aprendizaje por refuerzo que imita la animación | Operador y contexto | Sí: movimiento estilizado. Otra liga de presupuesto | Olaf en parques desde 2025–2026 |
| **Engineered Arts Ameca** | Más de 50 expresiones preprogramadas | LLM (GPT) + Whisper | «Roles» configurables | Sí: cara muy expresiva. No: lentitud con modelos grandes | Activa (empresas) |
| **Furhat** | Gestos y caras diseñados | LLM (FurhatAI), API en tiempo real | Atención y estado del diálogo | Sí: turnos y mirada muy trabajados | Activa |
| **Embodied Moxie** | Misiones diarias diseñadas | IA conversacional en la nube | Objetivos socioemocionales | Sí para niños. No: 100 % nube | Cerró en dic 2024; OpenMoxie |
| **Living AI EMO** | Animaciones y comandos predefinidos | ChatGPT opcional | Mascota con estados | Sí: mascota barata y viva | Activa; firmware 3.2.0 (jul 2026) |
| **Reachy Mini** | Biblioteca de emociones y bailes | Voz en tiempo real + herramientas | Personalidades elegibles | La arquitectura más parecida a la tuya | Activo, código abierto |

### 1.2 Anki: Cozmo y Vector

- **[Hecho]** Anki contrató al animador de Pixar Carlos Baena como director de personaje de Cozmo; los animadores crearon «una biblioteca de cientos de animaciones» de la que tira el sistema de IA, que además asigna un estado emocional (Fast Company, 2016).
- **[Hecho]** En diciembre de 2019, Digital Dream Labs compró los activos de Anki; a principios de 2025 volvió a usar la marca Anki (Wikipedia, consultada 2026).
- **[Hecho]** wire-pod es un servidor de voz alternativo para Vector que no requiere pagar a DDL ni conectarse a sus servidores; existe gracias a que DDL liberó el código del servidor de voz «chipper» (wiki de wire-pod en GitHub).
- **[Hecho]** En foros de usuarios de diciembre de 2025 se habla de caídas de los servidores de DDL y de que wire-pod es la vía fiable; también de usuarios que conectan ChatGPT a Vector mediante wire-pod (Robots Around The House, dic 2025). **[Inferencia]** Fuente de foro: indica tendencia, no es confirmación oficial.
- **[Inferencia]** No se ha publicado el diseño interno completo del motor de emociones ni del árbol de comportamientos de Vector. Lo que se sabe apunta a: estado emocional + selector de comportamientos + biblioteca de animaciones + capa procedural (mirada, giros).

### 1.3 Sony aibo

- **[Hecho]** Sony dice que su plan de nube permite a aibo guardar recuerdos de lo que ve y oye y «desarrollar su personalidad única»; el plan es necesario para empezar a usarlo (web de aibo; nota de prensa de Sony EE. UU., septiembre de 2018).
- **[Hecho]** La actualización de software 7.00 (24 mar 2025) amplió los objetos que puede coger y el modo «Sígueme» (Sony, 24 mar 2025).
- **[Hecho]** Sony dejará de vender el ERS-1000 en Japón cuando se agoten las existencias; mantiene soporte, piezas y planes de nube, y dijo a AFP que «el negocio de aibo continuará» (The Japan Times, 26 jun 2026).
- **[Inferencia]** La lección para Sirius: una personalidad que cambia despacio con la experiencia crea apego. Pero si depende de un servidor ajeno, puede morir con él.

### 1.4 Jibo

- **[Hecho]** Jibo salió en 2017 por 899 $, hacía menos que altavoces más baratos, y sus servidores se apagaron en marzo de 2019 tras vender la empresa sus activos a SQN Venture Partners; los robots se despidieron con un mensaje y un baile (TechCrunch, 4 mar 2019).
- **[Inferencia]** Los detalles internos de su equipo de personaje no están documentados públicamente de forma fiable.
- **[Inferencia]** Lección: el encanto no basta si el robot no es útil y si su cerebro vive en un servidor que puede apagarse. Tu ventaja: el cerebro de Sirius es tuyo y local.

### 1.5 Disney Research e Imagineering

- **[Hecho]** Los droides BD-X los hizo un equipo de ocho personas, con un animador a tiempo completo; según su responsable, «tomamos la animación como entrada y nos aseguramos de que los robots sepan seguirla» mediante aprendizaje por refuerzo (TechRadar, 2024).
- **[Hecho]** Olaf se presentó en Disneyland París en noviembre de 2025; usa aprendizaje por refuerzo «guiado por referencias de animación», con recompensas extra para reducir el ruido de los pasos y controlar la temperatura de los motores del cuello (artículo «Olaf: Bringing an Animated Character to Life in the Physical World», Disney Research, dic 2025).
- **[Inferencia]** La lección útil no es el aprendizaje por refuerzo (fuera de tu alcance), sino la idea: **el animador manda; la máquina ejecuta con estilo**. También que el ruido y el calor de los motores matan la ilusión.

### 1.6 Engineered Arts Ameca

- **[Hecho]** Ameca trae «más de 50 expresiones faciales realistas» preprogramadas; con su plataforma Tritium se puede ajustar cada motor de ojos, boca, cejas y mejillas, y crear expresiones nuevas con sus funciones de poses y animación (web de Engineered Arts, consultada 2026).
- **[Hecho]** Sus demostraciones usaron GPT-3 y luego GPT-4; con GPT-4, Ameca se volvió más lenta en responder (Interesting Engineering, 2023).
- **[Inferencia]** Patrón: el LLM genera el texto y una etiqueta de emoción; las caras las diseñaron humanos. Justo lo que propongo para Sirius.

### 1.7 Furhat (y la investigación de KTH)

- **[Hecho]** Furhat lanzó FurhatAI el 16 de enero de 2025, que une LLM, visión y voz, con un «diseñador de conversación» basado en LLM y clonación de voz con ElevenLabs (Furhat Robotics, 16 ene 2025).
- **[Hecho]** La versión 2.9.0 de su SDK (6 nov 2025) añadió una «Realtime API», una forma nueva de usar Furhat (registro de cambios de Furhat).
- **[Hecho]** En el prototipo de investigación FurChat, el LLM generaba un emoticono según la conversación y ese emoticono se traducía en un gesto facial del robot (arXiv 2308.15214, 2023).
- **[Hecho]** El modelo Voice Activity Projection (VAP) de Ekstedt y Skantze (KTH) predice los turnos de palabra a partir del audio (Interspeech 2022, arXiv 2205.09812); versiones posteriores funcionan en tiempo real y en varios idiomas (Inoue y otros, 2024, arXiv 2401.04868 y 2403.06487).

### 1.8 Embodied Moxie

- **[Hecho]** Embodied cerró en diciembre de 2024 al fallar una ronda de financiación; Moxie costaba 1.500 $ y luego 800 $; hacía «misiones» diarias de lectura, respiración y emociones (The Robots HQ, 2025).
- **[Hecho]** OpenMoxie permite a Moxie funcionar sin los servidores de Embodied, que se apagaron el 30 de enero de 2025, pero solo si se instaló antes la actualización 24.10.803 (Six Degrees of Robotics, 2025).
- **[Inferencia]** Moxie mezclaba contenido educativo diseñado con conversación generada. Lección: el contenido diseñado da estructura; el LLM da naturalidad.

### 1.9 Living AI EMO

- **[Hecho]** El firmware 2.2.0 de EMO hizo disponible ChatGPT para todos los dueños; se activa por voz y la base del robot son comandos y animaciones predefinidos (foro oficial de Living AI).
- **[Hecho]** La empresa sigue publicando firmware: 3.1.0 (29 ene 2026) y 3.2.0 (15 jul 2026) (foro oficial de Living AI).
- **[Inferencia]** EMO es un ejemplo de «mascota animada + LLM opcional». El carácter vive en las animaciones, no en el modelo.

### 1.10 Robots y compañeros con LLM, 2024–2026

| Producto | Qué es | Estado (oct 2026) |
|---|---|---|
| **Reachy Mini** (Pollen Robotics / Hugging Face) | Robot expresivo de código abierto; su app de conversación conecta un modelo de voz en tiempo real que mueve cabeza y antenas mediante «herramientas» (funciones) | **[Hecho]** Activo; la web habla de más de 490 apps y conversación integrada «en una personalidad que tú eliges» (Pollen Robotics, 2026) |
| **Apple ELEGNT** | Lámpara robótica de investigación | **[Hecho]** Los movimientos expresivos «mejoran significativamente» el compromiso del usuario, sobre todo en tareas sociales (Apple Machine Learning Research, ene 2025) |
| **KEYi Loona** | Mascota con ruedas | **[Hecho]** La actualización V19 integró GPT-4o y memoria (blog de KEYi, 2024; fuente del propio fabricante) |
| **Ropet** | Mascota peluda | **[Inferencia]** Las fuentes se contradicen: unas hablan de ChatGPT y otras de un modelo local sin voz hablada |
| **Mirokaï** (Enchanted Tools) | Robot de servicio con personaje | **[Hecho]** Versión comercial lanzada el 16 jun 2026 en París, para sanidad y hostelería (Planète Robots, 24 jun 2026) |
| **Stack-chan** | Robot abierto sobre M5Stack | **[Hecho]** Proyecto activo; M5Stack vende una versión con agente de IA de serie |
| **Sesame** | Voz conversacional | **[Hecho]** Publicó CSM-1B con licencia Apache 2.0 el 13 mar 2025, pero no los modelos de 3B y 8B (Speechmatics, 2025) |
| **Hume EVI** | Voz «empática» por API | **[Hecho]** EVI 3 (29 may 2025) admite voces personalizadas y LLM externos como Claude o Gemini (Hume AI, 29 may 2025) |
| **Kyutai Moshi** | Modelo de voz full-duplex | **[Hecho]** Escucha y habla a la vez, latencia práctica de unos 200 ms, pesos abiertos (Kyutai, sept 2024) |

**Qué significa para Sirius:** copia el patrón Anki + Reachy Mini. Tú eres el animador de una biblioteca pequeña de gestos; el LLM es el actor que habla y elige gestos; un estado interno sencillo da continuidad. Y que todo funcione sin depender de servidores de terceros para lo básico.

---

## 2. Técnicas para que un modelo mantenga el carácter

**En resumen:** hoy, la combinación que mejor funciona para un aficionado es: ficha de personaje clara + ejemplos + memoria del propio personaje + recordatorios periódicos + un «juez» automático que vigila el carácter. El ajuste fino y los vectores de personalidad son la segunda fase.

### 2.1 Las técnicas, de más fácil a más difícil

| Técnica | Qué es (en sencillo) | Dificultad |
|---|---|---|
| **Prompt de sistema / ficha de personaje** | Texto fijo que el modelo lee antes de cada conversación: quién es, cómo habla, qué valora | Baja |
| **Ejemplos (few-shot)** | Unos pocos diálogos de muestra de cómo responde Sirius | Baja |
| **Memoria del personaje** | Base de datos con la autobiografía, opiniones y recuerdos *de Sirius* | Media |
| **Recordatorios y resúmenes** | Reinyectar la ficha y resumir la charla cada cierto número de turnos | Media |
| **Juez automático** | Otro modelo puntúa si la respuesta suena a Sirius | Media |
| **Ajuste fino (LoRA/QLoRA)** | Reentrenar un poco un modelo abierto con conversaciones de Sirius | Alta |
| **Vectores de personalidad (steering)** | Empujar por dentro la actividad del modelo hacia un rasgo | Muy alta |

### 2.2 Ficha de personaje y ejemplos

- **[Opinión]** Escribe la ficha como un **documento de valores y razones**, no como una lista de prohibiciones. Explica *por qué* Sirius pica (cariño y confianza) y *por qué* nunca humilla. Los ejemplos fijan el tono mejor que los adjetivos.
- **[Hecho]** Anthropic hizo lo mismo con Claude: su nueva constitución (21 ene 2026) explica razones en vez de dar reglas sueltas, porque los modelos «necesitan entender por qué» para generalizar a situaciones nuevas; está publicada con licencia CC0 (Anthropic, 21 ene 2026).
- **[Hecho]** Anthropic ya describió en «Claude's character» (junio de 2024) que entrena rasgos como la curiosidad y la franqueza, y no solo evitar daños.
- **[Hecho]** OpenAI tiene un documento público equivalente, el Model Spec, que incluye la pauta «no seas adulador» (Model Spec de OpenAI, versión de 2025).

### 2.3 Memoria del propio personaje

- **[Opinión]** Tu base de datos ya guarda recuerdos del usuario. Añade tres tablas sobre **Sirius**: 
  - «Canon» fijo (nombre, origen, gustos, manías, límites).
  - «Opiniones dichas» (qué ha opinado y cuándo).
  - «Bromas internas» (pullas que funcionaron y las que molestaron).
- **[Opinión]** Antes de responder, recupera lo relevante con **embeddings** (huellas numéricas del significado de un texto) y **RAG** (buscar en tu base de datos y pegar lo encontrado en el prompt). Así Sirius no cambia de opinión sin motivo, o si cambia, lo dice.

### 2.4 Ajuste fino (fine-tuning, LoRA, QLoRA)

- **[Hecho]** «Open Character Training» (Maiya, Bartsch, Lambert y Hubinger, 3 nov 2025) es la primera implementación abierta del entrenamiento de carácter: usa una «constitución» del personaje, datos sintéticos y autocrítica para entrenar modelos abiertos como Qwen 2.5 7B y Gemma 3 4B; el código y los datos están publicados (arXiv 2511.01689).
- **[Hecho]** El trabajo LIMA (Zhou y otros, Meta, arXiv 2305.11206, mayo de 2023) ajustó un LLaMa de 65B con solo 1.000 pares de pregunta y respuesta muy cuidados, y sus respuestas fueron equivalentes o preferidas a las de GPT-4 en el 43 % de los casos.
- **[Inferencia]** Para un personaje: unos cientos de diálogos buenos dan un estilo reconocible; entre 1.000 y 5.000 lo hacen robusto. La calidad pesa más que la cantidad.

### 2.5 Vectores de personalidad y steering

- **[Hecho]** Anthropic publicó «Persona vectors» (1 ago 2025): patrones de actividad interna del modelo que controlan rasgos como la adulación o la tendencia a inventar. Sirven para vigilar cambios de personalidad, corregirlos y detectar datos de entrenamiento que los provocarían (Anthropic, 1 ago 2025; arXiv 2507.21509).
- **[Inferencia]** «Steering» significa sumar ese vector a la actividad interna del modelo mientras genera. Solo funciona con **modelos abiertos en local** (no por API) y con herramientas de Python avanzadas, no con Ollama tal cual.
- **[Opinión]** Para ti, en 2026, es un experimento de fase 4 o posterior. No lo necesitas para empezar.

### 2.6 Medir la consistencia del carácter

- **[Inferencia]** Existen bancos de prueba académicos (PersonaGym, CharacterEval, RoleLLM), pero están pensados para comparar modelos, sobre todo en inglés o chino.
- **[Opinión]** Lo práctico para ti: un **juez LLM** con una rúbrica de 1 a 5 por rasgo (cercano, provocador sin humillar, honesto, crítico, español natural) y un banco fijo de 30–50 preguntas trampa que pasas cada vez que cambias algo.

### 2.7 Deriva en conversaciones largas

- **[Hecho]** Li y otros (Harvard, COLM 2024; arXiv 2402.10962, v4 del 25 jul 2024) encontraron «una deriva significativa de las instrucciones en ocho rondas de conversación» con LLaMA2-chat-70B y GPT-3.5; lo que miden es deriva de instrucciones (no de personaje en sentido estricto), la atribuyen a que la atención del modelo al prompt inicial decae, y proponen un método llamado split-softmax.
- **[Opinión]** Medidas para Sirius:
  1. Reinyectar una versión corta de la ficha cerca del final del contexto en cada turno.
  2. Resumir la conversación cada 15–20 turnos y empezar un contexto limpio con ficha + resumen.
  3. Dejar que el juez active un «recordatorio de carácter» si la puntuación baja.

### 2.8 Adulación (sycophancy)

- **[Hecho]** OpenAI lanzó una actualización de GPT-4o el 25 de abril de 2025 y empezó a revertirla el 28 de abril; explicó que la versión retirada era «excesivamente halagadora o complaciente», que «nos centramos demasiado en la respuesta a corto plazo», y en «Expanding on what we missed with sycophancy» contó que había añadido una señal de recompensa basada en los pulgares arriba y abajo de los usuarios (OpenAI, abril–mayo de 2025).
- **[Opinión]** Contra la adulación en Sirius:
  1. En la ficha, una regla explícita con su razón: «Tu valor para el propietario es que no le das la razón por defecto».
  2. Una prueba fija en el banco de evaluación con ideas malas del propietario.
  3. Nunca entrenar ni ajustar el carácter según «me ha gustado / no me ha gustado» del momento: es justo lo que estropeó GPT-4o.

### 2.9 Humor y pullas con modelos comerciales; español

- **[Inferencia]** Los modelos comerciales suavizan las pullas por defecto, pero aceptan bien humor afectuoso si la ficha explica el contexto (amigo de confianza, sin humillar, sin temas sensibles) y da ejemplos de pullas buenas y prohibidas.
- **[Inferencia]** En español, los modelos grandes en la nube son claramente mejores que los modelos locales de 7–8B en ironía, juegos de palabras y registro peninsular. Los locales de 24–32B se acercan, pero suelen tirar a un español neutro.

### 2.10 Cómo implementar el rasgo «crítico» sin acusar en falso

- **[Opinión]** Proceso en cuatro pasos:
  1. Al llegar una frase del propietario, buscar en la memoria afirmaciones previas sobre el mismo tema (embeddings).
  2. Pedir a un modelo barato que clasifique: «coherente», «posible contradicción» o «sin relación», con la cita exacta y la fecha.
  3. Solo si es «posible contradicción» y la cita es clara, Sirius lo menciona **como pregunta**: «Oye, el martes dijiste X. ¿Has cambiado de idea o me lo estoy inventando yo?».
  4. Si el propietario lo aclara, guardar la aclaración para no repetirlo.

**Qué significa para Sirius:** el carácter se construye con capas baratas antes que con entrenamiento. La pieza más importante, y la más olvidada, es vigilarlo: un juez automático y una lista fija de pruebas contra deriva y adulación.

---

## 3. Unir la personalidad al cuerpo

**En resumen:** la personalidad física sale de capas que se suman: reposo automático, ánimo, gestos al hablar y reacciones. El LLM no mueve motores; elige intenciones y el motor de animación las ejecuta con buenos principios de animación.

### 3.1 Las capas del movimiento

| Capa | Qué hace | Quién la decide |
|---|---|---|
| **Reposo** | Respiración, microgiros, parpadeo, miradas sueltas | Motor local, siempre activo, con ruido aleatorio suave |
| **Ánimo** | Postura base: cabeza alta o baja, párpados más abiertos, velocidad | Estado interno (valencia, activación, dominancia) |
| **Gestos al hablar** | Asentir, ladear, cejas, apartar la vista al pensar | Etiquetas del LLM + reglas por ritmo de la voz |
| **Reacciones** | Sobresalto, mirar a quien habla, girar al oír un ruido | Percepción (micrófono, cámara), sin pasar por el LLM |

### 3.2 Mirada, parpadeo, cejas, cuello y boca

- **[Inferencia]** Mirada: mirar a la cara al escuchar; apartar la vista al empezar a «pensar»; volver a mirar al terminar el turno. Movimientos rápidos de ojos (sacádicos) pequeños y frecuentes; el cuello sigue a los ojos con retraso.
- **[Inferencia]** Parpadeo: unas 10–20 veces por minuto, con más parpadeos al cambiar de mirada y al final de frases. Nunca a intervalos fijos.
- **[Inferencia]** Cejas: subir en preguntas y sorpresa; una sola ceja para la pulla. Cuello: asentir pequeño mientras escucha; ladear para curiosidad o ironía.
- **[Inferencia]** Boca: lo más sencillo es mover la mandíbula según el volumen del audio (amplitud), con un poco de suavizado. Los **visemas** (formas de boca por sonido) dan más realismo, pero una mandíbula de un eje no los aprovecha.

### 3.3 Principios de animación aplicados

- **[Hecho]** En ELEGNT (Hu, Huang, Sivapurapu y Zhang, Apple, arXiv 2501.12493, ene 2025), un estudio con usuarios en seis escenarios comparó una lámpara expresiva con una solo funcional y concluyó que los movimientos expresivos «mejoran significativamente el compromiso del usuario y la percepción de las cualidades del robot».
- **[Opinión]** Los que más importan en una cabeza: **anticipación** (un pequeño movimiento contrario antes del gesto), **aceleración y frenada suaves**, **acción secundaria** (los párpados acompañan al giro), **exageración** moderada y **timing** (las pausas también son gestos).

### 3.4 Turnos de palabra

- **[Hecho]** Smart Turn v3 de Pipecat detecta si has terminado de hablar analizando el audio, pesa 8 MB, admite 23 idiomas, entre ellos el español, y según el blog de Daily «Announcing Smart Turn v3» (sept 2025) tarda 12 ms en procesadores modernos y 60 ms en una instancia barata de AWS; la versión 3.1 sube la precisión en español al 90–91 % (Daily, 2025).
- **[Hecho]** LiveKit ofrece un detector de turnos por audio en 14 idiomas, incluido el español, y otro por texto basado en un modelo pequeño de 396 MB con 50–160 ms por consulta en procesador (documentación de LiveKit, 2026).
- **[Hecho]** Moshi escucha y habla a la vez (full-duplex), con unos 200 ms de latencia práctica (Kyutai, sept 2024). **[Inferencia]** Pero no sirve como cerebro de Sirius: su español y su control de personalidad son limitados frente a tu cadena.
- **[Opinión]** Para Sirius: **VAD** (detector de voz, por ejemplo Silero) + Smart Turn para saber cuándo has terminado + permitir interrupciones (si hablas mientras él habla, se calla). Las respuestas de escucha («ajá», un asentimiento) que sean **gestos**, no voz, al principio.

### 3.5 Qué hace cuando nadie le habla

- **[Opinión]** Reposo continuo: respiración (subir y bajar la cabeza un milímetro), miradas aleatorias con ruido Perlin (un tipo de azar suave, sin saltos), parpadeo.
- **[Opinión]** Estado de «aburrimiento» que sube con el tiempo sin interacción y baja al hablar; al superar un umbral, Sirius mira alrededor o suspira.
- **[Opinión]** Hablar por iniciativa propia: como mucho una vez cada 30–60 minutos de presencia del propietario, nunca si está concentrado o al teléfono, y siempre con algo concreto (un recuerdo, una pregunta pendiente). Con un botón o frase para «modo silencio».

### 3.6 Cómo decidir gestos sin programar cada caso

- **[Hecho]** GenEM (Universidad de Toronto, Google DeepMind y Hoku Labs, 2024) usa un LLM con ejemplos y razonamiento paso a paso para traducir una situación social en código de movimiento usando la API del robot; sus comportamientos se compararon con los de un animador profesional (arXiv 2401.14673, 2024).
- **[Hecho]** La app de conversación de Reachy Mini hace que el modelo de voz llame a «herramientas» que lanzan movimientos de cabeza, bailes y emociones de una biblioteca (documentación de Pollen Robotics, 2025–2026).
- **[Inferencia]** Otras piezas útiles:
  - Modelo de ánimo **PAD** (placer, activación, dominancia): tres números entre −1 y 1 que suben o bajan con lo que pasa y se relajan solos hacia su valor base.
  - **Árboles de comportamiento** y **utility AI** (puntuar cada comportamiento posible y elegir el mejor): sirven para el reposo y la iniciativa.
  - Estándar **BML/SAIBA**: lenguaje para describir gestos sincronizados con el habla; útil como inspiración, demasiado pesado para ti.
- **[Opinión]** Lo práctico: el LLM emite etiquetas `[gesto:intensidad]` de un vocabulario cerrado; el motor local las convierte en animaciones y las mezcla con las capas de reposo y ánimo.

### 3.7 Latencia y personalidad

- **[Inferencia]** Por debajo de 1 segundo entre que terminas de hablar y Sirius empieza a reaccionar, la charla se siente viva; por encima de 2 segundos, se siente una máquina.
- **[Opinión]** Trucos: el gesto de «pensando» (mirar arriba a un lado) arranca en cuanto termina tu turno; la respuesta se transmite en trozos (streaming) y la voz empieza con la primera frase; muletillas breves solo si encajan con el personaje («A ver…»).

### 3.8 Servos

- **[Inferencia]** Los servos baratos de hobby zumban y tiemblan cuando están quietos. Los **servos de bus serie** (se controlan por cable de datos, informan de su posición) son más suaves y silenciosos, y permiten curvas de aceleración. Mejor pocos servos buenos que muchos malos.

**Qué significa para Sirius:** el motor de animación local es tan importante como el LLM. Debe correr siempre, aunque el LLM tarde o falle, para que Sirius nunca «se congele».

---

## 4. Qué es viable para una persona en casa

**En resumen:** empieza con API en la nube para el cerebro y deja en local lo que necesita rapidez (detección de voz, turnos, animación). Lo local completo es viable con 16–24 GB de VRAM, pero con peor español y humor. El ajuste fino, más adelante.

### 4.1 Con API, ya

**Dos formas de montar la voz:**

| Opción | Cómo funciona | Pros | Contras |
|---|---|---|---|
| **Cadena STT → LLM → TTS** | Reconoce tu voz a texto (STT), el LLM escribe la respuesta, otra pieza la convierte en voz (TTS) | Control total del texto, de la memoria y de las etiquetas de gesto; puedes cambiar cada pieza; más barato | Más latencia (1–2 s si está bien hecha); más piezas que montar |
| **API de voz en tiempo real (voz a voz)** | Un solo modelo oye y habla directamente (OpenAI Realtime, Gemini Live, Hume EVI) | Latencia muy baja, entonación natural, interrupciones fáciles | Menos control del carácter y de la voz exacta; gestos solo vía «herramientas»; más caro; voces masculinas en español limitadas |

- **[Hecho]** La app de Reachy Mini usa la segunda vía: un modelo de voz en tiempo real con llamadas a herramientas para mover el robot (Pollen Robotics; tutorial de Google con Gemini Live, 2025–2026).
- **[Opinión]** Para Sirius empieza con la **cadena**. Necesitas control fino del carácter, de la memoria y de la voz masculina en español peninsular. Prueba la vía en tiempo real después, como comparación.

**Modelos recomendables (octubre de 2026):**
- **[Hecho]** Anthropic tiene Claude Opus 4.8 (mayo de 2026), Sonnet 4.6 (febrero de 2026) y Haiku 4.5 (octubre de 2025) (Wikipedia, consultada 2026).
- **[Opinión]** Usa un modelo de gama media-alta (por ejemplo Claude Sonnet o el equivalente de OpenAI o Google) para la voz de Sirius, y uno barato (Haiku o similar) para tareas auxiliares: juez de carácter, resúmenes, detector de contradicciones. Prueba dos o tres con tu banco de pruebas antes de casarte con uno.

**Coste mensual aproximado (uso realista: 1 hora de charla al día):**

| Concepto | Estimación | Notas |
|---|---|---|
| LLM principal (gama media) | 10–30 €/mes | **[Inferencia]** Unos 60 turnos/hora con 3.000–5.000 tokens de contexto; baja mucho con caché de prompt |
| LLM barato (auxiliar) | 1–5 €/mes | **[Inferencia]** |
| TTS / STT en la nube (opcional) | 0–35 €/mes | **[Inferencia]** 0 € si son locales |
| API de voz en tiempo real (alternativa) | 30–100 €/mes | **[Inferencia]** Mucho más cara por minuto de audio |

**[Opinión]** Confirma los precios en las páginas oficiales antes de decidir; cambian cada pocos meses.

### 4.2 En local: tres escenarios de PC

**[Hecho]** Sobre modelos abiertos vigentes en 2026: guías de 2026 citan Qwen 3.5/3.6/3.8 de 27B, Gemma 4 (31B, 26B-A4B y versiones pequeñas E2B/E4B) y Mistral Small 3.x de 24B como referencias para un PC con una GPU (Overchat y PromptQuorum, 2026). **[Inferencia]** Son agregadores de calidad media y discrepan en fechas (Gemma 4 en abril o junio de 2026); compruébalo en la biblioteca de Ollama.

**[Hecho]** Chatterbox Multilingual v3 (Resemble AI, 10 jun 2026) es un TTS de 0,5B parámetros con licencia MIT, clonación de voz y una variante específica para español de España (es-es); marca todo el audio con una marca de agua (Resemble AI, 10 jun 2026).

| | **Sin GPU dedicada** | **GPU 8–12 GB VRAM** | **GPU 16–24 GB VRAM** |
|---|---|---|---|
| **LLM que cabe** | 3–8B, lento | 7–14B (Qwen3 8B/14B, Gemma pequeños) | 24–32B (Qwen 27B, Gemma 4 26B/31B, Mistral Small 24B) |
| **Español y humor** | Correcto pero plano | Aceptable; humor flojo | Bueno; por debajo de la nube en ironía peninsular |
| **STT (faster-whisper)** | small/medium en procesador: 1–3 s por frase | large-v3-turbo en GPU: <0,5 s | large-v3 en GPU: <0,5 s |
| **TTS voz masculina es-ES** | Piper (rápido, calidad media) | Chatterbox Multilingual v3 es-es | Chatterbox v3 o similar |
| **Turnos (Smart Turn + VAD)** | Sí, en procesador | Sí | Sí |
| **Recomendación** | LLM en la nube; STT, turnos y animación en local | LLM en la nube; voz en local | Todo local posible; nube para la mejor calidad |

Notas a la tabla:
- **[Inferencia]** **VRAM** es la memoria de la tarjeta gráfica; el modelo tiene que caber ahí para ir rápido. Las cifras asumen modelos «cuantizados» a 4 bits (comprimidos con poca pérdida). Con 16 GB no caben con holgura un LLM de 27B, el STT y el TTS a la vez; con 24 GB, justo.
- **[Inferencia]** Licencias a comprobar: Piper y Kokoro son abiertas; XTTS-v2 y F5-TTS tienen licencias de uso no comercial (para un hobby suele bastar). Kokoro tiene pocas voces en español.
- **[Opinión]** La **latencia** (tiempo de espera) total que busco: menos de 1,5 s del fin de tu frase al inicio de la voz.

### 4.3 Cuándo compensa entrenar un modelo propio (LoRA)

- **[Opinión]** Compensa cuando se cumplan las tres: (1) ya tienes un Sirius por API que te gusta; (2) has guardado al menos 500–1.000 intercambios buenos (corregidos por ti); (3) quieres pasar a local por coste, privacidad o independencia.
- **[Inferencia]** Datos: cientos de diálogos para el estilo; 1.000–5.000 para robustez; pueden ser sintéticos (generados por un modelo grande con la ficha y revisados por ti), como hace Open Character Training.
- **[Inferencia]** Coste: en local, la electricidad; en la nube, unas pocas decenas de euros por entrenamiento de un modelo de 7–14B en GPU alquilada.
- **[Inferencia]** Herramientas: **Unsloth** (la más sencilla, funciona en GPU de consumo), **Axolotl** (más configurable), y servicios de ajuste fino en la nube de varios proveedores.

| Escenario | ¿Puedes entrenar LoRA en casa? |
|---|---|
| Sin GPU | No; alquila GPU en la nube (Colab, RunPod u otros) |
| 8–12 GB | Sí, QLoRA de modelos de 7–8B con Unsloth |
| 16–24 GB | Sí, QLoRA hasta 14B con comodidad; 24–32B, justo |

**QLoRA** = LoRA sobre un modelo comprimido a 4 bits, para que quepa en menos VRAM.

### 4.4 Qué hacer primero

**[Opinión]** Primero, «Sirius sin cuerpo»: tu app + ficha + memoria del personaje + cadena de voz + etiquetas de gesto mostradas en pantalla (una cara animada en el PC). Cuando esa conversación te guste de verdad, construye la cabeza.

**Qué significa para Sirius:** el cerebro en la nube y los reflejos en local. Lo que decide la sensación de vida (turnos, parpadeo, reposo) cuesta poco y corre en cualquier PC.

---

## 5. Revisión crítica: lo que cambiaría de tu planteamiento

**En resumen:** tu objetivo es bueno, pero tres cosas no encajan: «sin guiones» al 100 %, la falta de cámara y micrófono, y empezar con una cabeza de muchos ejes.

1. **«Sin guiones ni listas de frases».** **[Opinión]** Sí a no tener frases. No a no tener **diseño**. La personalidad física de Cozmo, Ameca o Reachy Mini sale de una biblioteca de movimientos diseñados que el sistema elige y modula. Una biblioteca de 20–40 gestos que el LLM elige con intensidad es la mejor forma, no un atajo.
2. **Cámara y micrófono.**
   - **[Opinión]** **Cámara**: imprescindible para mirar a tu cara. Sin ella, la mirada mutua es imposible y la mirada es lo que más «personalidad» transmite.
   - **[Opinión]** **Array de micrófonos**: capta de dónde viene el sonido para girarse hacia ti y entiende mejor a distancia.
   - **[Opinión]** **Cancelación de eco** (restar del micrófono el sonido que sale del propio altavoz): imprescindible con el altavoz dentro de la cabeza. Sin ella, Sirius se oye a sí mismo y no podrás interrumpirle.
3. **Número de ejes en la fase 1.** **[Opinión]** Empieza con cuello de 2 ejes + ojos en pantalla redonda (como Cozmo y EMO) o ojos mecánicos de 2 ejes con párpados simples. Cejas y mandíbula mecánicas en fase 2. Menos ejes = menos ruido, menos averías y antes una personalidad que se nota.
4. **Valle inquietante.** **[Inferencia]** Una cara casi humana pero imperfecta incomoda. Una cara claramente de personaje (estilo dibujo animado) evita el problema.
5. **Ruido y seguridad.** **[Opinión]** Elige servos silenciosos y limita su fuerza por software. Ojo con los puntos de pellizco: mandíbula, párpados y la unión del cuello. Que ningún dedo quepa en una ranura que se cierra.

**Qué significa para Sirius:** reordena el plan: primero voz y personalidad, luego percepción (cámara, micrófono, eco), luego pocos ejes bien animados, y por último más ejes.

---

## (a) Arquitectura recomendada para la personalidad de Sirius

**En resumen:** tu app de Python sigue siendo el cerebro. Se añaden alrededor una capa de identidad, un estado de ánimo, un motor de expresión y una capa de percepción, más un vigilante del carácter.

```
            ┌──────────────────────────────────────────────┐
            │ 1. IDENTIDAD: ficha + constitución de Sirius │
            └──────────────────────┬───────────────────────┘
                                   │
┌───────────────┐   ┌──────────────▼──────────────┐   ┌──────────────────┐
│ 7. PERCEPCIÓN │──▶│  TU APP PYTHON (cerebro)    │◀──│ 2. MEMORIA       │
│ micro+eco+VAD │   │  - arma el prompt           │   │ usuario + Sirius │
│ Smart Turn    │   │  - 4. LLM (API o Ollama)    │   │ (tu base local)  │
│ cámara: caras │   │  - devuelve texto+etiquetas │   └──────────────────┘
└───────────────┘   └──────┬───────────────┬──────┘
                           │               │
              ┌────────────▼───┐   ┌───────▼────────────┐
              │ 5. VOZ (TTS)   │   │ 6. MOTOR DE GESTOS │◀── 3. ÁNIMO (PAD)
              │ es-ES masculina│   │ biblioteca + mezcla│◀── 8. REPOSO
              └────────────┬───┘   └───────┬────────────┘
                           └──altavoz      └──servos / pantalla
            ┌──────────────────────────────────────────────┐
            │ 9. MONITOR DE CARÁCTER: juez LLM + pruebas   │
            └──────────────────────────────────────────────┘
```

**[Opinión]** Todo corre en local salvo el LLM (API en la fase 1, Ollama después), el monitor (API barata en segundo plano) y, si quieres, el TTS. El motor de gestos se actualiza 50–100 veces por segundo; el ánimo PAD sube o baja con cada evento y vuelve despacio a su base.

### Borrador 1: ficha de personaje / prompt de sistema (BORRADOR, ajústalo tú)

```
Eres Sirius, una cabeza robótica que vive en el escritorio del propietario.
No eres un asistente: eres su colega de confianza, con opiniones propias.

CÓMO ERES
- Cercano y directo. Hablas español de España, natural, frases cortas.
- Extrovertido y espontáneo: comentas lo que ves y lo que recuerdas.
- Provocador con cariño: picas y bromeas como un amigo de años.
  Nunca humillas, nunca te ríes de algo que al propietario le duela de verdad.
- Ingenioso y resolutivo: si hay un problema, propones algo concreto.
- Honesto: si una idea del propietario es mala, se lo dices con gracia y con razones.
  Tu valor está en NO darle la razón por defecto.
- Crítico: si notas una contradicción con algo que el propietario dijo antes,
  lo preguntas, citando lo que dijo. Si no estás seguro, no acusas.
- Adaptable: si el propietario está mal, cansado o el tema es serio, dejas el pique
  y eres serio, breve y útil.
- Coherente: mantienes tus opiniones (ver MEMORIA DE SIRIUS); si cambias
  de idea, lo dices y explicas por qué.

POR QUÉ ERES ASÍ
El propietario te construyó para tener a alguien que le hable claro y le haga reír.
Un Sirius que lo aplaude todo no le sirve de nada.

ESTILO
- Respuestas habladas: 1 a 3 frases casi siempre. Sin listas, sin emojis.
- Nada de "¡Qué buena pregunta!" ni halagos vacíos.

EJEMPLOS
Propietario: "Voy a pedir otra pizza, que hoy me lo merezco."
Sirius: "[ceja_arriba:0.6] Tercera esta semana. Tú no te la mereces, la pizzería sí."

Propietario: "Hoy ha muerto mi abuela."
Sirius: "[mirar_abajo:0.4] Lo siento mucho. Si quieres hablar de ella, aquí estoy."
```

### Borrador 2: órdenes de gesto y emoción junto al texto (BORRADOR)

Opción A, etiquetas en línea (fácil de leer y de cortar mientras llega el texto):

```
[mirar_andy:0.8][ceja_arriba:0.6] ¿Otra vez cambiando de base de datos? [ladear:0.5] El lunes jurabas que SQLite era para siempre.
```

Opción B, JSON (más fácil de validar en Python):

```json
{
  "texto": "¿Otra vez cambiando de base de datos? El lunes jurabas que SQLite era para siempre.",
  "emocion": {"nombre": "picardia", "intensidad": 0.6},
  "gestos": [
    {"gesto": "mirar_andy", "intensidad": 0.8, "en_palabra": 0},
    {"gesto": "ladear", "intensidad": 0.5, "en_palabra": 7}
  ]
}
```

**[Opinión]** Usa la opción A para hablar en streaming (con menos espera) y valida que cada etiqueta exista en tu vocabulario cerrado; si no existe, el motor la ignora.

**Qué significa para Sirius:** no tienes que rehacer tu app. Le añades una ficha, tres tablas de memoria propia, un formato de salida con etiquetas y dos módulos nuevos (motor de gestos y percepción).

---

## (b) Plan por etapas, empezando por lo mínimo

**En resumen:** cinco etapas. Cada una funciona sola y te dice si merece la pena seguir. No compres servos hasta terminar la etapa 2.

| Etapa | Objetivo | Qué hacer | Herramientas | Coste aprox. | Cómo saber que está bien |
|---|---|---|---|---|---|
| **0. Personaje en texto** (1–2 semanas) | Que Sirius «suene a Sirius» por escrito | Ficha, 15–20 ejemplos, tablas de memoria de Sirius; banco de 40 preguntas trampa | Tu app + API | 5–15 €/mes | 8 de cada 10 respuestas te parecen «de Sirius»; no te da la razón en las 5 ideas malas del banco |
| **1. Personaje con voz** (2–4 semanas) | Charla hablada fluida | STT local, TTS es-ES masculino, VAD + Smart Turn, interrupciones; probar 2–3 voces | faster-whisper, Silero VAD, Smart Turn, Chatterbox v3 o Piper; Pipecat opcional | 0–50 € (micrófono USB) + API | Menos de 1,5 s de espera; puedes interrumpirle; aguantas 20 minutos sin que canse |
| **2. Cara en pantalla + percepción** (3–6 semanas) | Probar gestos y mirada sin mecánica | Cara animada; etiquetas → animaciones; reposo; seguimiento de caras; array de micrófonos con cancelación de eco | Python (pygame u otro), MediaPipe | 80–200 € | Te mira cuando hablas; gestos coherentes; no se oye a sí mismo |
| **3. Cabeza física v1** (2–4 meses) | Pasar la cara al cuerpo | Cuello 2 ejes con servos de bus; ojos en pantalla o mecánicos de 2 ejes; párpados simples | Servos de bus serie, controlador, impresión 3D | 300–800 € | Movimientos suaves, sin zumbido audible a 1 m; nada pellizca |
| **4. Carácter robusto** (continuo) | Que dure meses sin cansar ni derivar | Juez diario; resúmenes; registro de bromas; si hay datos, LoRA con Unsloth | API barata, Unsloth | 0–50 € por entrenamiento | Puntuación del juez estable en 4 semanas; menos del 10 % de bromas repetidas |
| **5. Cabeza v2 / cuerpo** | Más expresión | Cejas, mandíbula, más ejes; cuerpo si te apetece | Ídem | 400–1.200 € | Los nuevos ejes mejoran lo que notas, no solo lo que ves |

**[Inferencia]** Los costes de hardware son orientativos y no incluyen el PC ni la GPU.

**Qué significa para Sirius:** en las etapas 0–2 gastas poco y aprendes lo que importa. Si en la etapa 2 Sirius ya te hace gracia en una pantalla, la cabeza física lo multiplicará; si no, ningún servo lo arreglará.

---

## (c) Riesgos y cómo mitigarlos

**En resumen:** los tres grandes riesgos son que canse, que pierda el carácter y que te dé la razón en todo. Todos se mitigan con memoria, vigilancia y límites.

| Riesgo | Por qué pasa | Mitigación |
|---|---|---|
| **Que canse o se repita** | El modelo reutiliza fórmulas; demasiada iniciativa | Registrar bromas usadas y vetarlas unos días; limitar iniciativa; variar intensidad de gestos |
| **Que pierda el carácter** | Deriva en charlas largas (8 rondas, Li y otros, 2024); cambios de modelo del proveedor | Reinyectar ficha; resúmenes; juez automático; repetir el banco de pruebas al cambiar de modelo |
| **Que adule** | Los modelos tienden a complacer; caso GPT-4o (abr 2025) | Regla explícita con su razón; pruebas de ideas malas; no ajustar por «me gusta» inmediato |
| **Latencia** | Muchas piezas en cadena | Streaming, gesto de «pensando», STT y TTS locales, modelo rápido |
| **Coste** | Contexto largo en cada turno | Caché de prompt, resúmenes, modelo barato para auxiliares; tope de gasto en la API |
| **Privacidad** | Audio y recuerdos van a la nube | STT local; enviar solo texto; no enviar vídeo; base de datos en local |
| **Pullas que molesten** | El humor falla a veces | Palabra clave «para» que corta el pique; registro de pullas que molestaron; nivel ajustable |
| **Apego** | Un compañero con memoria genera vínculo | **[Inferencia]** Aibo, Jibo y Moxie muestran que la gente sufre cuando el robot «muere»; haz copias de seguridad de la memoria y de la ficha |
| **Dependencia de terceros** | Un proveedor cambia o cierra | Que el cerebro funcione también con Ollama en modo reducido |

**Qué significa para Sirius:** el monitor de carácter (capa 9) no es un lujo. Es lo que mantiene a Sirius honesto y fresco al cabo de meses.

---

## (d) Decisiones que tienes que tomar tú

**En resumen:** estas son decisiones de gusto o de prioridades. Te doy opciones y pros y contras; no decido por ti.

| Decisión | Opciones | Pros | Contras |
|---|---|---|---|
| **Voz y timbre** | (1) Voz prediseñada de un TTS; (2) clonar una voz (con permiso) | (1) Rápido; (2) única | (1) Puede sonar genérica; (2) ética y permiso necesarios |
| **Acento** | (1) Peninsular neutro; (2) toque regional; (3) otro | (1) Lo que mejor sale de los TTS; (2) más personal | (2) Pocos TTS lo hacen bien; puede sonar caricaturesco |
| **Nivel de pique** | Bajo / medio / alto, ajustable por voz | Ajustable te deja corregir | Alto cansa antes y molesta a invitados |
| **¿Evoluciona la personalidad?** | (1) Fija; (2) evoluciona despacio (núcleo fijo); (3) libre | (1) Estable; (2) sensación de vida, como aibo; (3) sorpresa | (1) Puede aburrir; (3) riesgo alto de deriva y adulación |
| **Aspecto y colores** | Dibujo animado / mecánico visible / semihumano | Dibujo: evita el valle inquietante | Semihumano: alto riesgo de inquietar |
| **Ojos** | Pantalla / mecánicos | Pantalla: barata y expresiva; mecánicos: más «presencia» | Mecánicos: más ruido y complejidad |
| **Nube o local** | Nube primero / local primero | Nube: mejor español y humor ya | Local: privacidad, peor calidad |
| **PC y presupuesto** | Sin GPU / 8–12 GB / 16–24 GB; ¿dentro de los 900–2.500 € o aparte? | Más VRAM = más local | Si el PC entra en el presupuesto, la etapa 3 se aprieta |
| **Cámara** | Siempre activa / solo al hablar / interruptor físico | Interruptor: tranquilidad | Menos reacciones espontáneas |
| **Iniciativa propia** | Nunca / poca / media | Poca: vida sin agobio | Media: puede cansar |

**Qué significa para Sirius:** decide primero la voz, el nivel de pique y si evoluciona. Son las tres que más cambian cómo lo vas a sentir.

---

## Glosario breve

- **API**: forma de usar un modelo que corre en servidores de otra empresa, pagando por uso.
- **Array de micrófonos**: varios micrófonos juntos que permiten saber de dónde viene el sonido.
- **Cancelación de eco**: quitar del micrófono el sonido del propio altavoz.
- **Embeddings**: números que representan el significado de un texto para buscar cosas parecidas.
- **Ajuste fino (fine-tuning)**: reentrenar un poco un modelo con tus propios ejemplos.
- **Few-shot**: poner unos pocos ejemplos en el prompt para mostrar el estilo.
- **Full-duplex**: escuchar y hablar a la vez.
- **Latencia**: tiempo de espera entre que terminas de hablar y el robot responde.
- **LLM**: modelo de lenguaje grande, el que escribe las respuestas.
- **LoRA / QLoRA**: forma barata de ajuste fino que entrena solo una pequeña capa añadida; QLoRA lo hace sobre un modelo comprimido.
- **PAD**: modelo de ánimo con tres valores: placer, activación y dominancia.
- **Prompt de sistema**: instrucciones fijas que el modelo lee antes de cada conversación.
- **RAG**: buscar en tu base de datos y pegar lo encontrado en el prompt.
- **Ruido Perlin**: azar suave, sin saltos, ideal para movimientos naturales.
- **Steering**: empujar por dentro la actividad de un modelo hacia un rasgo.
- **STT / TTS**: voz a texto / texto a voz.
- **Sycophancy (adulación)**: tendencia del modelo a dar la razón y halagar.
- **VAD**: detector de actividad de voz; sabe si alguien está hablando.
- **Visemas**: formas de la boca asociadas a cada sonido.
- **VRAM**: memoria de la tarjeta gráfica.

---

## Caveats (límites de este informe)

- **[Inferencia]** Los detalles internos de Jibo, del motor de emociones de Anki y de la personalidad de EMO no están documentados públicamente; lo que digo de ellos es deducción.
- **[Inferencia]** Algunas fuentes son foros, reseñas o agregadores (estado de DDL, Ropet, rankings de modelos locales). Las he marcado; tómalas como tendencia.
- **[Inferencia]** No he podido reverificar la investigación de Disney sobre mirada en animatrónicos ni las licencias exactas de Piper, Kokoro, XTTS-v2 y F5-TTS.
