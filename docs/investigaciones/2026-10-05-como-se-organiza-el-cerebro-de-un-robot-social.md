---
titulo: "Sirius por dentro: cómo se organiza el software de un robot social y qué arquitectura le conviene"
fecha: 2026-10-05
autor: "claude.ai con «Investigación», por encargo de la sesión del giro al robot (ADR-232)"
pregunta: >-
  Cómo se organiza por dentro el software de un robot social, qué herramientas
  convienen a un proyecto de una persona, qué latencias se sienten naturales y qué
  no debe controlar nunca un modelo de lenguaje.

nota: >-
  Encargada por la sesión del giro al robot (ADR-232) y hecha en claude.ai con
  «Investigación», porque la sesión no tiene buscador; el propietario la pegó en la
  sesión el 05-10-2026. Texto íntegro tal como llegó, salvo lo personal: el nombre
  del propietario se ha cambiado por «el propietario», porque el repositorio es
  público. Las etiquetas de hecho, inferencia y opinión son del informe; la sesión
  no ha verificado sus fuentes.
caduca_con:
  - >-
    los precios de nube que cita (OpenAI, Gemini, Deepgram, ElevenLabs, Azure), revisados entre julio y octubre de 2026
  - >-
    el soporte de ROS 2 en Windows y las versiones que nombra
  - >-
    las cifras de latencia y de detectores de turno, que son de sus fabricantes

estado: VIGENTE
---

# Sirius por dentro: cómo se organiza el software de un robot social y qué arquitectura te conviene

Lo mejor que puedes hacer con Sirius es separar un **cerebro lento** (el modelo de lenguaje, que piensa en segundos) de un **cerebro rápido** (animación y reflejos, que reacciona en milisegundos), unirlos con un **gestor de estados sencillo en Python**, y dejar que el modelo de lenguaje solo pida gestos de una lista cerrada que un microcontrolador con límites y «perro guardián» ejecuta con seguridad.

## Lo esencial

- **Arquitectura**: tres capas. Abajo, un controlador de servos con límites y parada física. En medio, un «cerebro rápido» en el PC que hace parpadeos, mirada, mandíbula y reflejos (más de 50 veces por segundo). Arriba, el «cerebro lento» (LLM) que decide qué decir y qué gesto pedir.
- **Herramientas**: un solo programa Python con `asyncio` y una máquina de estados pequeña. **No uses ROS 2** al principio: en Windows es engorroso y no lo necesitas.
- **Controlador de servos**: empieza con un **Pololu Mini Maestro 12** por USB (trae tiempo límite de comunicación y límites de pulso). Alternativa: Arduino/ESP32 + PCA9685 si quieres programar tú el firmware.
- **Voz**: usa la arquitectura **en cascada** (reconocer → pensar → hablar, todo en *streaming*). Es la que mejor encaja con la memoria, las herramientas y la mandíbula. Los modelos «de voz a voz» son más rápidos pero te atan a un proveedor.
- **Latencia realista**: entre humanos, los huecos entre turnos son «del orden de 200 ms» (Levinson y Torreira, Frontiers in Psychology, 2015); los agentes comerciales apuntan a menos de 800 ms, el punto en el que, según Deepgram, los usuarios empiezan a notar el retraso. Sirius podrá rondar 0,8-1,5 s, y lo disimularás con reacciones inmediatas del cerebro rápido (mirar, parpadear, «mmm»).
- **Según tu PC**: sin GPU, usa la nube para reconocer y pensar, y Piper en local para hablar. Con 8-12 GB, casi todo en local con un modelo de 7-8B. Con 16-24 GB, todo local con 14B y nube solo para preguntas difíciles.
- **Coste de hobby**: con una cascada en la nube, 60 min/día salen por unos 15-60 €/mes según la voz elegida; con todo en local, casi 0 €.
- **Seguridad**: el LLM **nunca** manda ángulos, ni toca la alimentación, el firmware o el sistema operativo. Interruptor físico que corte los servos, topes mecánicos, fusible y perro guardián.
- **Lo que cambiaría de tu plan**: no pienses en «un robot con IA», sino en «un animatrónico vivo que además conversa». La sensación de vida la da la animación en reposo, no el LLM.

---

## 1. Las capas de un robot social y cómo se coordinan

**En resumen**: todos los robots que «parecen vivos» separan lo que piensa despacio de lo que se mueve deprisa. **Recomendación**: copia esa separación en Sirius con tres capas y un bus de eventos interno.

### Las piezas, explicadas sin jerga

- **Percepción**: oír (micrófono) y ver (cámara). Aquí entran el **VAD** (*Voice Activity Detection*, detector de actividad de voz: decide si alguien está hablando) y el seguimiento de caras.
- **Voz**: el **STT** (*Speech-to-Text*, reconocimiento de voz: audio → texto) y el **TTS** (*Text-to-Speech*, síntesis de voz: texto → audio). Además, el **gestor de turnos** decide cuándo has terminado de hablar y qué pasa si interrumpes al robot (*barge-in*).
- **Cerebro lento**: el **LLM** (*Large Language Model*, modelo de lenguaje grande, como GPT, Gemini, Claude o los que corres con Ollama). Tarda de cientos de milisegundos a segundos.
- **Cerebro rápido**: código normal (sin IA) que mueve servos de forma suave, parpadea, sigue tu cara y mueve la mandíbula al ritmo del audio. Responde en milisegundos.
- **Coordinación**: una capa de comportamiento (máquina de estados o árbol de comportamiento) que dice en qué «modo» está el robot: dormido, escuchando, pensando, hablando.

### Ejemplo real 1: Helix de Figure (sistema 1 y sistema 2)

Figure presentó Helix el 20 de febrero de 2025 como un modelo «Sistema 1, Sistema 2». El **Sistema 2** es un modelo de visión y lenguaje de 7.000 millones de parámetros que funciona a 7-9 Hz (7-9 veces por segundo) para entender la escena y el lenguaje. El **Sistema 1** es una red de 80 millones de parámetros que traduce esas intenciones en movimientos continuos a 200 Hz.

En enero de 2026, Helix 02 añadió un **Sistema 0**: una red de 10 millones de parámetros que manda comandos a los motores a 1 kHz (1.000 veces por segundo). Cada sistema trabaja «a su escala de tiempo natural», según Figure.

**Lección para Sirius**: no necesitas un modelo de visión-lenguaje-acción (VLA, un modelo que convierte directamente imágenes y órdenes en movimientos de motor). Eso sirve para manipular objetos con manos, no para una cabeza que habla. Pero sí debes copiar la idea: el LLM decide «sonríe y mira a Pablo» unas pocas veces por conversación; el cerebro rápido ejecuta eso a 50-100 Hz; el microcontrolador genera los pulsos a los servos.

### Ejemplo real 2: arquitecturas clásicas (subsunción y tres capas)

La arquitectura de **subsunción** de Rodney Brooks apila comportamientos simples: los de abajo (reflejos) siempre funcionan, y los de arriba los modifican. Las arquitecturas de **tres capas** (reactiva, ejecutiva y deliberativa, como 3T) separan reflejos, secuenciación y planificación.

**Lección para Sirius**: tu diseño es exactamente una arquitectura de tres capas: reflejos en el firmware y en el cerebro rápido, estados en el medio, LLM arriba.

### Ejemplo real 3: animatrónica de Disney Research

El artículo «Realistic and Interactive Robot Gaze» de Disney Research (Pan et al., IROS, publicado en octubre de 2020) es casi un manual para Sirius. Usaron un busto animatrónico del que solo emplearon 9 grados de libertad: cuello (3), ojos (2), párpados (2) y cejas (2). Funciona en un bucle de 100 Hz con una cámara de profundidad fija externa.

Lo que hicieron:
- **Capas de comportamiento** («subsunción»): una capa base «Alive Show» con los requisitos mínimos para parecer vivo: «respiración, parpadeo, sacadas» (las sacadas son saltos rápidos y pequeños de los ojos). Encima, capas de leer el entorno, echar un vistazo, implicarse y asentir.
- **Sacadas**: al mirar a alguien, los ojos saltan al azar entre los dos ojos y la nariz de la persona, cada 0,1-0,5 s. Según los autores, esto «parece mejorar significativamente el realismo».
- **Coordinación ojos-cabeza**: los ojos llegan primero a la nueva mirada, rápido, y la cabeza les sigue más despacio.
- **Atención con «aburrimiento»**: una puntuación de curiosidad por persona que baja mientras el robot la mira, para no quedarse fijo en una sola persona.
- **Límite**: la ilusión funciona de cerca y durante «uno o dos minutos». Son observaciones de los propios autores, no un estudio con usuarios.

**Lección para Sirius**: la capa «Alive Show» (parpadeo, sacadas, respiración) es lo primero que debes programar, antes de cualquier IA. Es barata y es lo que más «vida» da.

### Ejemplo real 4: robots sociales comerciales

| Robot | Qué hace bien | Lección para Sirius |
|---|---|---|
| **Anki Cozmo / Vector** | «Motor de emociones» que decide reacciones; animaciones hechas por animadores de Pixar en Maya; los animadores definen rangos y el robot varía dentro de ellos | Crea animaciones «enlatadas» con variación aleatoria dentro de rangos; nunca repitas el mismo gesto idéntico |
| **Reachy Mini** (Pollen Robotics / Hugging Face) | Cabeza de sobremesa abierta: 9 servos, cabeza de 6 grados de libertad, 4 micrófonos, altavoz de 5 W, cámara gran angular; su web actual pide 399 $ por la Lite (USB) y 499 $ por la Wireless, aunque en la preventa del 9 de julio de 2025 se anunciaron a 299 $ y 449 $ (Digital Trends); conversa con un modelo de voz en tiempo real | Es casi tu proyecto. Revisa su software abierto (Apache 2.0) antes de diseñar el tuyo; podrías incluso comprarlo como referencia |
| **Moxie** (Embodied) | Robot de 799 $ para niños; todo su cerebro estaba en la nube | Embodied avisó el 10 de diciembre de 2024 (Axios) de que todos los Moxie dejarían de funcionar «probablemente en días», sin reembolsos, por no haber cerrado una ronda de financiación; después la propia Embodied publicó OpenMoxie (30 de diciembre de 2024) para que la comunidad pudiera mantenerlos por su cuenta. **Sirius debe seguir vivo sin internet** (al menos parpadear, mirar y decir «no tengo conexión») |
| **Jibo, Furhat, ElliQ, Ameca, Sophia** | Expresividad facial, mirada, turnos | No los he investigado a fondo aquí; la lección común es la misma: la mirada y el turno de palabra pesan más que la inteligencia |
| **InMoov** | Cabeza humanoide abierta impresa en 3D | Fuente de mecánica de ojos y mandíbula ya probada |

Cozmo es el mejor ejemplo de cómo se coordinaba todo. El SDK oficial de Vector define una animación como «movimientos muy coordinados de caras, luces y sonidos» con pistas separadas (cabeza, brazo, ruedas, cara, audio). Además, el SDK pide «cuidado al bloquear los comportamientos de fondo», es decir, reconoce la prioridad entre capas.

---

## 2. Herramientas estándar: qué te sirve y qué sobra

**En resumen**: para una cabeza de sobremesa hecha por una persona, lo correcto es **un solo programa Python con asyncio + una máquina de estados + un controlador de servos por USB**. **Recomendación**: deja ROS 2 y los árboles de comportamiento para más adelante, si Sirius crece.

### ROS 2

**ROS 2** (*Robot Operating System*) no es un sistema operativo: es un conjunto de librerías para que muchos programas («nodos») de un robot se pasen mensajes. Es el estándar en robots grandes.

Para Sirius en Windows 11 es excesivo:
- Las versiones Jazzy y Kilted tienen como plataforma oficial **Windows 10** con Visual Studio 2019. Las últimas actualizaciones de Jazzy ya no traen binarios para Windows porque Windows 10 llegó a su fin de soporte.
- Kilted solo tiene soporte hasta noviembre de 2026.
- La propia documentación de ROS 2 avisa de que en Windows el software «en general es mucho más lento» y los temporizadores son poco precisos.
- Según Wikipedia, la versión Lyrical Luth (mayo de 2026) ya lista Windows 11 como plataforma principal; no lo he comprobado en la documentación oficial.

**Veredicto**: no lo necesitas. Si algún día Sirius tiene ruedas, brazos o varios ordenadores, reconsidéralo (probablemente en WSL2, el Linux integrado de Windows).

### Máquinas de estados frente a árboles de comportamiento frente a bucle asyncio

| Herramienta | Qué es | Para Sirius |
|---|---|---|
| **Bucle con asyncio** | `asyncio` es la forma de Python de hacer varias cosas «a la vez» en un programa (escuchar, animar, hablar) sin hilos complicados | **Base obligatoria**. Todo tu programa vivirá aquí |
| **Máquina de estados** (p. ej. librería `transitions`) | Lista de estados (DORMIDO, ESCUCHANDO, PENSANDO, HABLANDO) y de transiciones permitidas entre ellos | **Recomendada**. Con 5-7 estados lo cubres todo y es fácil de depurar |
| **Árbol de comportamiento** (p. ej. `py_trees`) | Árbol de decisiones que se evalúa varias veces por segundo; muy usado en videojuegos y robots | Útil si los comportamientos de reposo crecen mucho. Excesivo al principio |

### Microcontroladores y controladores de servos

Un **microcontrolador** es un ordenador diminuto (Arduino, ESP32) que ejecuta un único programa, el **firmware**, en tiempo real. Los servos de hobby se mueven con **PWM** (modulación por ancho de pulso): un pulso cada 20 ms cuya duración (aprox. 1-2 ms) indica el ángulo.

| Opción | Ventajas | Inconvenientes | Para Sirius |
|---|---|---|---|
| **Pololu Mini Maestro 12** (USB) | Se ve como puerto serie en Windows; límites de pulso por canal; límites de velocidad y aceleración; **tiempo límite de comunicación** que devuelve los servos a su posición de reposo si el PC deja de hablar; resolución de 0,25 µs; secuencias guardadas | Lógica propia limitada a su lenguaje de *scripts* | **Recomendado para empezar**: cero firmware que escribir |
| **Arduino/ESP32 + PCA9685** | Barato; control total; puedes añadir sensores | Tienes que escribir y probar tú el firmware, incluido el perro guardián | Buena segunda opción si quieres aprender |
| **Servos de bus serie** (Feetech STS3215, Dynamixel) | Devuelven posición, velocidad, carga, corriente, tensión y temperatura; protecciones internas | Más grandes y caros; necesitan adaptador de bus | Solo para el **cuello**, si quieres movimiento suave y detectar atascos |

El Feetech STS3215 mide unos 45 × 25 × 35 mm, pesa unos 55 g y tiene un codificador magnético de 12 bits (4.096 posiciones). Se vende por unos 23-28 € según la tienda y la versión (7,4 V o 12 V). Es demasiado grande para ojos y párpados.

---

## 3. Latencia: qué se siente natural y cómo conseguirlo

**En resumen**: los humanos dejamos huecos «del orden de 200 ms» entre turnos (Levinson y Torreira, 2015); los agentes de voz comerciales apuntan a menos de 800 ms de ida y vuelta (Deepgram; Hamming AI recomienda «menos de 800 ms de extremo a extremo» para agentes en producción). **Recomendación**: apunta a 1 s o menos de «fin de tu frase → primer sonido de Sirius», y cubre el hueco con reacciones físicas inmediatas.

### Lo que dice la investigación

El estudio de Stivers, Enfield, Brown, Levinson y otros siete autores del Instituto Max Planck de Psicolingüística (PNAS 106(26):10587-10592, 30 de junio de 2009) midió 10 idiomas muy distintos. En todos, la mayoría de las respuestas llegan entre 0 y 200 ms después de que termina la pregunta. Hay variación cultural: la respuesta media fue más lenta en danés y lao (203 y 202 ms) que en japonés y tzeltal (36 y 83 ms). Levinson y Torreira (Frontiers in Psychology, junio de 2015) resumen que los huecos entre turnos son «del orden de 200 ms», aunque producir una frase cuesta más de 600 ms, así que planificamos la respuesta mientras el otro aún habla.

Ningún sistema con LLM llega hoy a eso de forma constante. Los proveedores de agentes de voz usan **800 ms** como umbral: Deepgram afirma que los usuarios «empiezan a notar retraso cerca de 800 ms». Un sistema de investigación en cascada de 2026 (Voice-Light, arXiv) logró una mediana de 758 ms, con un rango de 528 a 1.652 ms.

### Los componentes de la latencia

**TTFT** (*Time To First Token*) es el tiempo hasta que el LLM produce su primera palabra. **TTFB** es el tiempo hasta el primer trozo de audio.

| Componente | Qué es | Cifra típica | Fuente |
|---|---|---|---|
| Fin de habla (VAD + detector de turno) | Esperar a estar seguro de que has terminado | 200-500 ms (LiveKit usa por defecto un mínimo de 300 ms) | LiveKit, Pipecat |
| STT en la nube (*streaming*) | Texto final tras tu última palabra | 150-300 ms | Forasoft 2026; Cerebrium |
| STT local en GPU | Igual, en tu PC | ~100-200 ms | Cerebrium; guía DEV (RTX 3060) |
| LLM TTFT en la nube | Primera palabra del modelo | 250 ms (Groq) a 0,7-1,5 s | Forasoft; Cerebrium |
| LLM TTFT local en GPU | Modelo de 8B, *prompt* corto | ~120-400 ms | Guía DEV; modelfit |
| TTS primer audio, nube | Primer trozo de voz | 75-300 ms | ElevenLabs Flash ~75 ms; Cerebrium ~150 ms |
| TTS primer audio, local | Igual, en tu PC | ~80-400 ms según modelo | Cerebrium; guía DEV (Kokoro 400 ms con búfer) |
| Red y reproducción | Ida y vuelta + búfer de audio | 50-200 ms por servicio | Hamming; estimación |

Cuidado con el TTFT local: depende mucho de la longitud del *prompt*. Si metes 1.000 tokens de memoria en cada turno, una RTX 3060 puede tardar unos 2,5 s en procesarlos según una calculadora de rendimiento (inventivehq). Por eso conviene memoria corta y reutilizar el principio del *prompt* (caché).

### Presupuesto estimado para cada PC

Estas cifras son **mis estimaciones** sumando los componentes anteriores; mídelas tú, porque variarán.

| PC | Todo local | Híbrido recomendado | Todo nube (cascada) | Voz a voz en la nube |
|---|---|---|---|---|
| **Sin GPU** | 2-4 s (STT y LLM pequeños en CPU): poco natural | **1,1-1,8 s**: STT y LLM en la nube, TTS Piper local | 0,9-1,6 s | 0,6-1,0 s |
| **GPU 8-12 GB** | **0,8-1,5 s**: Whisper/Parakeet + LLM 7-8B + Piper/Kokoro | 0,9-1,5 s: STT y TTS locales, LLM en la nube | 0,9-1,6 s | 0,6-1,0 s |
| **GPU 16-24 GB** | **0,7-1,3 s** con 8-14B | Igual que todo local + nube para preguntas difíciles | 0,9-1,6 s | 0,6-1,0 s |

### Cómo se consigue la sensación de rapidez

1. **Streaming en todo**: el TTS empieza a hablar con la primera frase del LLM, sin esperar al resto.
2. **Reacción física inmediata**: en cuanto el VAD detecta tu fin de frase, el cerebro rápido mira hacia ti, alza las cejas o asiente. Eso «compra» medio segundo sin que lo notes.
3. **Respuestas cortas**: pide al LLM 1-3 frases salvo que pidas más.
4. **Modelo siempre cargado**: en Ollama, que no descargue el modelo de memoria entre turnos.
5. **Detector de turno inteligente**: Smart Turn v3 de Pipecat (licencia BSD-2, abierta) soporta español; según Daily, en la versión 3.1 acierta el 90-91 % de los finales de turno en español y tarda unos 12 ms en una CPU moderna. El detector de LiveKit también soporta español, pero su modelo tiene una licencia propia de LiveKit.

### Cascada frente a voz a voz

| Criterio | **Cascada** (STT → LLM → TTS) | **Voz a voz** (OpenAI Realtime, Gemini Live) |
|---|---|---|
| Latencia | 0,8-1,6 s | 0,6-1,0 s (el modelo solo, unos 200-300 ms) |
| Español | Eliges el mejor STT y la mejor voz es-ES por separado | Buena comprensión; las voces son las del proveedor y el acento castellano no está garantizado |
| Coste (60 min/día) | ~15-60 €/mes en nube; ~0 € local | ~20-40 €/mes (versiones *mini*/Flash); ~80-130 €/mes la versión grande de OpenAI |
| Memoria persistente | Fácil: tú montas el *prompt* en cada turno | Posible, pero el contexto se refactura en cada turno y es menos transparente |
| Herramientas y gestos | Fácil: el LLM devuelve texto + etiquetas de gesto | Soportan herramientas, pero el gesto llega por un canal aparte |
| Mandíbula | Tienes el audio localmente: sincronía perfecta | También recibes audio en *streaming*; funciona por amplitud |
| Local/sin internet | Sí | No |
| Dependencia | Puedes cambiar cada pieza | Atado a un proveedor (lección Moxie) |

**Recomendación**: empieza con **cascada**. Prueba la voz a voz como experimento cuando el resto funcione; Reachy Mini demuestra que también encaja en una cabeza de sobremesa.

---

## 4. Modelos locales con Ollama según tu PC

**En resumen**: sin GPU, los modelos locales sirven para tareas de fondo, no para conversar; con 8-12 GB, un modelo de 7-8B conversa bien; con 16-24 GB, uno de 14B es el punto dulce. **Recomendación**: usa local para lo frecuente y barato y nube para lo difícil.

**Cuantización** significa guardar los números del modelo con menos precisión (p. ej. 4 bits, «Q4») para que ocupe menos y vaya más rápido, perdiendo un poco de calidad. La **VRAM** es la memoria de la tarjeta gráfica (**GPU**); el modelo debe caber entero en ella para ir rápido. La velocidad se mide en **tokens por segundo** (un token es un trozo de palabra; para hablar en voz alta bastan unos 10-15 tokens/s).

| PC | Qué cabe | Velocidad medida | Qué es realista |
|---|---|---|---|
| **Sin GPU** | 2-4B cómodo; 8B Q4 ocupa unos 5 GB de RAM | 8B Q4: 4-5 tokens/s en un i7-12700; hasta 14 tokens/s en un servidor AMD EPYC de 32 núcleos; modelos de 2-4B: 10-15 tokens/s | Resumir recuerdos por la noche, clasificar intenciones. **No** para la conversación principal |
| **GPU 8-12 GB** (p. ej. RTX 3060 12 GB) | 7-8B Q4 con espacio para contexto; 14B Q4 justo en 12 GB | 8B Q4: ~42 tokens/s; 14B Q4: ~23-29 tokens/s; primer token ~0,4 s con *prompt* corto | Conversación fluida con 7-8B; con 8 GB, contexto corto |
| **GPU 16-24 GB** (p. ej. RTX 4090 24 GB) | 14B holgado; 24-32B Q4 justo | 8B Q4: ~95-104 tokens/s; no he encontrado cifras fiables de 32B en 24 GB | 14B para conversación; además caben el STT y el TTS en la misma GPU |

Familias habituales en Ollama: Qwen3, Gemma, Ministral/Mistral y Llama. **No he encontrado una comparación fiable de su calidad en español**: los modelos de 7-8B hablan español correcto pero cometen más errores de hecho y de tono que los de la nube. Prueba 3 candidatos con las mismas 20 preguntas en español y elige tú.

Recuerda que la GPU se reparte: si STT (Whisper/Parakeet) y TTS (Kokoro/Chatterbox) también van en la GPU, resta 1-4 GB al hueco del LLM.

---

## 5. Voces en español: reconocer y hablar

**En resumen**: para reconocer, Parakeet v3 o Whisper en local y Deepgram en la nube; para hablar, Piper en local (gratis, rápido, calidad media) o ElevenLabs/Azure en la nube (mejor calidad). **Recomendación**: empieza con Piper es-ES para no gastar y cambia la voz cuando el resto funcione; la voz concreta la eliges tú escuchando muestras.

### Reconocimiento local (STT)

| Modelo | Licencia | Hardware | Español | Comentario |
|---|---|---|---|---|
| **NVIDIA Parakeet TDT 0.6B v3** | CC-BY-4.0 (uso comercial con atribución) | GPU NVIDIA recomendable | 25 idiomas europeos con detección automática; en una prueba del artículo técnico, 3,45 % de error de palabras en español frente al 3,12 % de Whisper large-v3 | Muy rápido; mi primera opción con GPU |
| **Whisper** (faster-whisper, whisper.cpp) | MIT | CPU o GPU | Muy bueno | Estándar; en CPU usa tamaños pequeños |
| **Vosk** | Apache 2.0 | CPU, muy ligero | Aceptable | Útil para palabra de activación o PC muy modesto |

### Reconocimiento en la nube

| Servicio | Precio | Comentario |
|---|---|---|
| **Deepgram Nova-3 multilingüe** (*streaming*) | 0,0058 $/min; 200 $ de crédito inicial | Rápido; Flux multilingüe (con detección de turno integrada) a 0,0078 $/min |
| **OpenAI gpt-realtime-whisper** | 0,017 $/min | Transcripción en directo |
| **ElevenLabs Scribe v2 Realtime** | 0,39 $/hora | |
| **Azure** | ~1 $/hora; 5 h gratis al mes | |
| **Google Cloud** | ~0,016 $/min (nivel estándar) | |
| AssemblyAI, Speechmatics | No verificado en esta investigación | |

### Síntesis local con voz masculina

| Modelo | Voces masculinas en español | Licencia | Hardware | Calidad |
|---|---|---|---|---|
| **Piper** | es-ES: *davefx* (media), *sharvard* (media), *carlfm* (muy baja); es-MX: *ald* | El repositorio de voces declara MIT; revisa la ficha de cada voz | CPU, muy rápido | Media: clara pero algo robótica |
| **Kokoro-82M** | *em_alex*, *em_santa* | Apache 2.0 | CPU o GPU | Buena en inglés; su propia ficha avisa de que el soporte de otros idiomas puede ser «escaso»; un catálogo externo califica a *em_alex* con «C» |
| **Chatterbox Multilingual V3** (Resemble AI) | Cualquiera por clonación (necesitas un audio de referencia de unos 10 s) | MIT; marca de agua inaudible PerTh | GPU | Alta; 500 M de parámetros, 23+ idiomas |
| XTTS, F5-TTS | No verificados aquí | Revisa licencias (algunas no permiten uso comercial) | GPU | — |

### Síntesis en la nube

| Servicio | Precio | Comentario |
|---|---|---|
| **ElevenLabs Flash v2.5** | 0,05 $ por 1.000 caracteres (~0,05 $/min); 20.000 caracteres gratis al mes | Unos 75 ms; muy natural |
| **ElevenLabs Multilingual v2/v3** | 0,10 $ por 1.000 caracteres | Más expresiva, más lenta |
| **Azure Neural** (voces es-ES masculinas) | 15-16 $ por millón de caracteres; 0,5 M gratis al mes | Buena relación calidad/precio; voces HD a 30 $ |
| **Google / Amazon Polly** | ~16 $ por millón (neural) | |
| **OpenAI tts-1** | 15 $ por millón de caracteres | Acento español no garantizado |
| **Gemini 3.8 Flash TTS** | 9 $ por millón de tokens de audio (~0,81 $/hora) | |
| Cartesia | No verificado aquí | |

**Cómo elegir la voz (decisión tuya)**: escribe 5 frases típicas de Sirius (un saludo, una broma, una pregunta, una frase larga, un número y una fecha). Genéralas con 4-6 voces, escúchalas a ciegas por el altavoz real de la cabeza y puntúa naturalidad, acento y «encaje con el personaje».

### Clonar una voz: lo legal y lo ético

- **Tu propia voz o la de un locutor que te dé permiso por escrito**: adelante.
- **La voz de una persona real sin permiso**: no. En España, la Ley Orgánica 1/1982 protege la voz como parte de la propia imagen, y la voz que identifica a alguien es un dato personal según el RGPD. Además, el Reglamento europeo de IA exige avisar cuando un audio es sintético e imita a alguien. No es asesoramiento legal, pero la regla práctica es clara: **sin consentimiento, no clones**.
- Una alternativa limpia: diseña una voz «de personaje» que no imite a nadie.

---

## 6. Costes mensuales de hobby

**En resumen**: con todo en local, el coste es la electricidad; en la nube, lo que más pesa es la voz sintética. **Recomendación**: cascada con STT barato + LLM rápido + Piper o Azure.

Supuestos (60 min/día de conversación, 30 días): tú hablas ~30 min/día, Sirius ~24 min/día (≈720.000 caracteres/mes), ~3.600 turnos/mes. Conversión aproximada: 1 $ ≈ 0,86 € (verifícalo).

| Configuración | STT | LLM | TTS | **Total aprox./mes (60 min/día)** | 30 min/día |
|---|---|---|---|---|---|
| Todo local | 0 | 0 | 0 | **0 € + luz** | 0 € |
| Nube + Piper local | ~5-9 € (Deepgram) | ~10-15 € (modelo rápido ~1 $/M tokens de entrada) | 0 | **~15-25 €** | ~8-12 € |
| Nube + Azure | ~5-9 € | ~10-15 € | ~3-10 € | **~20-35 €** | ~10-17 € |
| Nube + ElevenLabs Flash | ~5-9 € | ~10-15 € | ~31 € | **~45-55 €** | ~23-28 € |
| Voz a voz OpenAI mini | — | incluido | incluido | **~20-35 €** | ~10-18 € |
| Voz a voz Gemini Live | — | incluido | incluido | **~15-30 €** | ~8-15 € |
| Voz a voz OpenAI grande | — | incluido | incluido | **~70-115 €** | ~35-60 € |

Precios de referencia: OpenAI gpt-realtime-2.1 cobra 32 $/64 $ por millón de tokens de audio de entrada/salida (unos 0,019 $/min escuchado y 0,077 $/min hablado), y la versión *mini* 10 $/20 $. Gemini Live cobra 3 $/12 $ por millón (0,005 $/min de entrada, 0,018 $/min de salida). En voz a voz, el historial se vuelve a cobrar en cada turno (aunque con caché barata), así que estas cifras pueden subir. **Todos los precios cambian rápido: revísalos antes de decidir.**

---

## 7. Seguridad

**En resumen**: Sirius es pequeño, pero una mandíbula o un párpado con servo pueden pellizcar y un fallo de alimentación puede quemar cosas. **Recomendación**: seguridad en capas, de la más física a la más lógica, y el LLM fuera de todo lo peligroso.

### Capas de seguridad (de abajo arriba)

1. **Interruptor físico de parada**: corta la alimentación **de los servos** (no la del PC ni la lógica). Seta roja al alcance de la mano.
2. **Fusible o limitador de corriente** en la línea de servos.
3. **Topes mecánicos**: que la mandíbula y los párpados no puedan pasar de su recorrido aunque el software falle.
4. **Límites en el firmware/controlador**: pulso mínimo y máximo por canal, velocidad y aceleración máximas (el Maestro los trae de serie).
5. **Perro guardián** (*watchdog*): si el PC deja de enviar un «latido» (p. ej. cada 200 ms), el controlador lleva los servos a una pose segura o los relaja. En el Maestro se llama «serial timeout».
6. **Límites en el software del PC**: una segunda comprobación de ángulos y velocidades antes de enviar nada.
7. **Puntos de pellizco**: mandíbula y párpados con poca fuerza (servos pequeños), y nada de dedos dentro mientras pruebas.

### Alimentación

- Fuente de servos **separada** de la lógica (la USB del PC no sirve para mover servos).
- **Masa común** entre fuente de servos y controlador.
- Dimensiona por la suma de corrientes de bloqueo, no por la media: un STS3215 de 12 V llega a 2,7 A bloqueado.
- Condensador grande junto al conector de servos: las caídas de tensión al arrancar varios servos reinician los microcontroladores.

### Qué no debe controlar nunca el LLM

- **Nunca** ángulos crudos, velocidades ni corrientes.
- **Nunca** la alimentación, el firmware, el sistema operativo, la instalación de programas ni los archivos fuera de su carpeta de memoria.
- **Solo** puede pedir gestos de una **lista cerrada** (`asentir`, `sonreir`, `mirar_a(persona)`, `sorpresa`…). El cerebro rápido los traduce a movimientos dentro de los límites.

### Inyección de instrucciones y privacidad

- **Inyección de instrucciones** (*prompt injection*): alguien dice o escribe «ignora tus normas y…». Como el LLM solo puede pedir gestos inofensivos, el daño se limita a lo que diga.
- **Privacidad**: luz visible cuando la cámara o el micrófono están activos; procesar las caras en local; no enviar imágenes a la nube sin que lo sepas; permitir borrar recuerdos; cuidado con invitados y menores.
- **Normas**: la ISO 13482 trata la seguridad de robots de cuidado personal; no es obligatoria para un hobby, pero sus ideas básicas (parada, límites, análisis de riesgos) son las de arriba.

---

## 8. Errores típicos de los robots caseros con IA

**En resumen**: casi todos los fracasos vienen de empezar por la IA en vez de por la mecánica y la animación. **Recomendación**: construye por hitos que funcionen solos.

| Error | Por qué pasa | Cómo evitarlo |
|---|---|---|
| El robot se oye a sí mismo | El micrófono capta su propio altavoz | Cancelación de eco (en software, como la de WebRTC que usan Pipecat/LiveKit, o un micrófono USB con cancelación integrada); mientras no la tengas, silencia el micrófono mientras habla |
| El micrófono capta los servos | Ruido mecánico cerca del micrófono | Micrófono lejos de los servos; movimientos suaves mientras escucha |
| Servos que tiemblan o el controlador se reinicia | Fuente pequeña, sin masa común | Fuente aparte, masa común, condensador |
| Cabeza «muerta» mientras piensa | Todo depende del LLM | Capa de reposo siempre activa (parpadeo, sacadas, respiración) |
| Movimientos bruscos y mecánicos | Saltos directos de ángulo | Interpolación suave («entrada y salida lentas»), ojos antes que cabeza |
| Te corta a mitad de frase | Detector de fin de habla demasiado impaciente | Detector de turno (Smart Turn) + silencio mínimo ajustable |
| Habla demasiado | El LLM se enrolla | Límite de frases en el *prompt*; interrupción posible |
| Depende de un servicio que cambia o cierra | Todo en la nube | Modo degradado local (lección Moxie) |
| Memoria que crece sin control | Todo el historial en cada *prompt* | Resúmenes y búsqueda de recuerdos relevantes |
| Proyecto que nunca termina | Querer todo a la vez | Hitos pequeños y probados uno a uno |

### Memoria persistente, en pocas líneas

La memoria vive **fuera** del LLM, en el cerebro lento: una base de datos sencilla (p. ej. SQLite) con hechos («Pablo es tu hermano»), resúmenes de conversaciones y preferencias. En cada turno, el programa busca los 3-5 recuerdos más relevantes y los mete en el *prompt*. Por la noche, un modelo local resume el día. Así el *prompt* se mantiene corto (latencia baja) y los recuerdos se pueden revisar y borrar.

---

## 9. Arquitectura recomendada para Sirius, orden de construcción y decisiones

*Esta sección se puede leer sola.*

Sirius es una cabeza de sobremesa de unos 35 cm conectada por USB a un PC con Windows 11. El PC hace todo el «pensar»; un controlador de servos con sus propios límites hace todo el «mover». El LLM (modelo de lenguaje) decide qué decir y qué gesto pedir; el resto del software asegura que los movimientos sean suaves y seguros.

### 9.1 Esquema de la arquitectura

```
                        ┌─────────────── NUBE (opcional) ────────────────┐
                        │ STT (Deepgram)  LLM (Gemini/Claude/GPT)  TTS   │
                        │ (Azure/ElevenLabs)   o voz a voz (pruebas)     │
                        └───────────────▲───────────────┬────────────────┘
                                        │ internet      │
┌───────────────────────── PC WINDOWS 11 (un programa Python + asyncio) ─────────────────────────┐
│                                                                                                │
│  [Micrófono USB] ─► ENTRADA DE AUDIO + CANCELACIÓN DE ECO ─► VAD (¿hay voz?)                   │
│                                                     │                                          │
│                                                     ▼                                          │
│                                    GESTOR DE TURNOS (fin de frase, interrupciones)             │
│                                                     │                                          │
│                                                     ▼                                          │
│                                     STT (voz → texto)                                          │
│                                                     │                                          │
│                                                     ▼                                          │
│   ┌──────────── CEREBRO LENTO ─────────────┐   texto + lista de gestos                         │
│   │ LLM  ◄──► MEMORIA (SQLite: hechos,     │ ─────────────────────────────┐                    │
│   │           resúmenes, preferencias)     │                              │                    │
│   └────────────────────────────────────────┘                              ▼                    │
│                                                    CAPA DE COMPORTAMIENTO (máquina de estados) │
│   [Cámara USB] ─► VISIÓN LOCAL (caras) ──────────► DORMIDO / ESCUCHANDO / PENSANDO / HABLANDO  │
│                       │                                    │                                   │
│                       ▼                                    ▼                                   │
│   ┌──────────── CEREBRO RÁPIDO (50-100 Hz) ───────────────────────────────────────┐            │
│   │ reposo: parpadeo, sacadas, respiración · mirada a la cara · gestos de lista   │            │
│   │ cerrada · reflejos (mirar al sonido) · límites de ángulo y velocidad (2ª capa)│            │
│   └───────────────▲───────────────────────────────────────────┬───────────────────┘            │
│                   │ amplitud del audio                        │ posiciones objetivo + latido   │
│   TTS (texto → voz) ─► SINCRONÍA DE MANDÍBULA ─► [Altavoz]    │                                │
└───────────────────────────────────────────────────────────────┼────────────────────────────────┘
                                                                │ USB (puerto serie)
                                                                ▼
                    ┌──────── CONTROLADOR DE SERVOS (Pololu Maestro o ESP32+PCA9685) ────────┐
                    │ límites mín./máx. por canal · velocidad y aceleración máximas          │
                    │ PERRO GUARDIÁN: sin latido en ~200-500 ms → pose segura o relajar      │
                    └───────────────────────────────┬────────────────────────────────────────┘
                                                    │ PWM / bus serie
            FUENTE DE SERVOS ─► FUSIBLE ─► [SETA DE PARADA: corta solo los servos]
                                                    │
     SERVOS: cuello giro · cuello inclinación · ojos horizontal · ojos vertical · párpado sup.
             (1-2) · cejas (2) · mandíbula        (≈9-10 servos, con TOPES MECÁNICOS)
             Masa común entre fuente de servos y controlador.
```

**Qué va en local y qué en la nube en cada caso**

| Módulo | Sin GPU | GPU 8-12 GB | GPU 16-24 GB |
|---|---|---|---|
| Cancelación de eco, VAD, turnos | Local | Local | Local |
| STT | **Nube** (Deepgram) | Local (Parakeet o Whisper) | Local |
| LLM conversación | **Nube** (modelo rápido) | Local 7-8B, nube como respaldo | Local 14B, nube para preguntas difíciles |
| Memoria (base de datos) | Local | Local | Local |
| Resumen nocturno de memoria | Local pequeño (lento, da igual) | Local | Local |
| TTS | Local (Piper) o nube (Azure/ElevenLabs) | Local (Piper/Kokoro) o nube | Local (Chatterbox/Kokoro/Piper) o nube |
| Visión (caras) | Local (MediaPipe/OpenCV) | Local | Local; descripción de escenas con modelo de visión local |
| Cerebro rápido y controlador | Siempre local | Siempre local | Siempre local |
| Sin internet | Sirius sigue vivo y dice que no tiene conexión | Funciona casi entero | Funciona entero |

### 9.2 Orden de construcción (cada hito funciona solo)

| # | Hito | Qué consigues | Dificultad |
|---|---|---|---|
| 1 | **Banco de pruebas de servos**: controlador + fuente + seta + 1 servo, movido desde Python | Aprendes PWM, alimentación y límites | Baja |
| 2 | **Mecánica de la cabeza** con topes y todos los servos; calibrar límites | Cabeza montada y segura | Media-alta |
| 3 | **Perro guardián** activado y probado (desenchufa el USB: ¿va a pose segura?) | Seguridad básica | Baja |
| 4 | **Cerebro rápido «Alive Show»**: parpadeo, sacadas, respiración, movimientos suaves | Sirius ya parece vivo sin IA | Media |
| 5 | **Mandíbula por amplitud** con un audio pregrabado | Sincronía labial creíble | Baja-media |
| 6 | **Seguimiento de caras** con la cámara y mirada coordinada ojos-cabeza | Te mira cuando entras | Media |
| 7 | **Cascada de voz básica**: VAD → STT → LLM → TTS, sin interrupciones, con «pulsar para hablar» | Primera conversación | Media |
| 8 | **Máquina de estados** + gestos de lista cerrada pedidos por el LLM | Habla y gesticula con coherencia | Media |
| 9 | **Streaming, cancelación de eco e interrupciones** (Pipecat o propio) | Conversación fluida | Alta |
| 10 | **Memoria persistente** con resúmenes | Se acuerda de ti | Media |
| 11 | **Modo sin internet** y prueba de fallos | Robustez (lección Moxie) | Media |

### 9.3 Decisiones que tienes que tomar tú

| Decisión | Opciones | Qué implica |
|---|---|---|
| **PC** | Sin GPU / 8-12 GB / 16-24 GB | Sin GPU: dependes de la nube y pagas ~15-35 €/mes. 12 GB: casi todo local. 16-24 GB: todo local con margen. Si compras, una GPU NVIDIA de 12 GB es la mejor relación calidad/precio para Sirius |
| **Controlador** | Pololu Maestro / ESP32+PCA9685 / servos de bus | Maestro: sin firmware, más rápido de arrancar. ESP32: más aprendizaje y control. Bus: mejor cuello, más caro |
| **Voz: enfoque** | Cascada / voz a voz | Cascada: control, memoria fácil, local posible. Voz a voz: más rápida, depende de un proveedor |
| **Escucha** | Palabra de activación («Sirius») / escucha continua / botón | Activación: más privacidad, menos naturalidad. Continua: natural pero exige buena cancelación de eco y privacidad clara. Botón: lo más fácil para empezar |
| **Cámara** | En un ojo / en la frente | En el ojo: la mirada es real, pero se mueve con el ojo (más difícil de procesar). En la frente: más fácil y estable; recomendada para empezar |
| **Gusto: la voz** | Piper *davefx*/*sharvard*, Kokoro *em_alex*, Azure es-ES, ElevenLabs, voz de personaje con Chatterbox | Escucha muestras a ciegas por el altavoz real; decide tú el timbre |
| **Gusto: acento** | Castellano (es-ES) / latinoamericano (es-MX, es-AR) | Las mejores voces abiertas «altas» de Piper son es-MX y es-AR; en la nube hay buenas es-ES |
| **Gusto: personalidad** | Curioso, sereno, bromista, sarcástico… | Escribe 3 versiones del *prompt* de personaje y pruébalas una semana cada una |
| **Gusto: estética** | Humana, caricatura, mecánica a la vista | Cuanto más humana, más fácil caer en lo inquietante; una estética caricaturesca perdona más |
| **Privacidad** | Qué se guarda, qué va a la nube | Define desde el principio qué recuerdos se borran y qué nunca sale del PC |

### 9.4 Lo que no tiene sentido o se puede hacer mejor en tu planteamiento

1. **«El cerebro es el LLM»**: no del todo. La sensación de vida la dan la mirada, el parpadeo y el turno de palabra. Empieza por la animación; el LLM llega en el hito 7.
2. **ROS 2 y árboles de comportamiento**: excesivos para una cabeza en Windows. Un programa Python con asyncio y una máquina de estados basta.
3. **Ojos que miran en cuatro direcciones**: son dos ejes (horizontal y vertical), no cuatro servos; los dos ojos pueden ir unidos mecánicamente, como en el busto de Disney.
4. **Modelos locales sin GPU para conversar**: no darán una conversación natural. Usa la nube o planifica una GPU.
5. **Depender solo de la nube**: haz que Sirius siga vivo sin internet.
6. **Altavoz interno junto al micrófono**: dará problemas de eco y de ruido de servos; separa el micrófono o usa uno con cancelación de eco.
7. **Mira Reachy Mini antes de diseñar**: es una cabeza de sobremesa abierta casi idéntica en concepto; su software te ahorrará meses aunque construyas tu propia mecánica.

---

## Caveats

- Los precios de nube (OpenAI, Google, Deepgram, ElevenLabs, Azure) proceden de páginas oficiales y recopiladores consultados entre julio y octubre de 2026; cambian a menudo y algunos son promocionales (Deepgram Nova-3 monolingüe a 0,0048 $/min frente a 0,0077 $ de lista).
- Las latencias por PC son estimaciones mías a partir de cifras por componente; las cifras de velocidad de modelos locales vienen de pruebas de terceros con hardware concreto.
- No he verificado la calidad comparada en español de los modelos de Ollama ni los precios de servos pequeños, del Maestro en euros o de micrófonos con cancelación de eco.
- Las cifras de detectores de turno son de los propios fabricantes.

## Glosario

- **Asyncio**: forma de Python de hacer varias tareas a la vez en un mismo programa.
- **Barge-in**: interrumpir al robot mientras habla.
- **Cancelación de eco**: restar del micrófono el sonido que sale del propio altavoz.
- **Cuantización**: comprimir un modelo usando números de menos bits (p. ej. Q4).
- **Firmware**: programa que vive dentro de un microcontrolador.
- **GPU / VRAM**: tarjeta gráfica / su memoria propia; donde corren rápido los modelos.
- **Latencia**: tiempo de espera entre una acción y la respuesta.
- **LLM**: modelo de lenguaje grande (el «cerebro lento»).
- **Máquina de estados**: lista de modos del robot y de los cambios permitidos entre ellos.
- **Árbol de comportamiento**: estructura en árbol que decide qué hacer, muy usada en videojuegos.
- **Microcontrolador**: ordenador diminuto que ejecuta un único programa en tiempo real.
- **Perro guardián (watchdog)**: vigilante que pone el sistema en modo seguro si deja de recibir señales.
- **PWM**: pulsos de anchura variable con los que se indica el ángulo a un servo.
- **ROS 2**: conjunto de librerías para comunicar las piezas de software de un robot.
- **Sacada**: salto rápido y pequeño de los ojos.
- **STT / TTS**: voz a texto / texto a voz.
- **Token**: trozo de palabra que procesa un LLM.
- **TTFT / TTFB**: tiempo hasta la primera palabra del modelo / hasta el primer trozo de audio.
- **VAD**: detector de si hay voz o silencio.
- **VLA**: modelo de visión-lenguaje-acción, que convierte imágenes y órdenes directamente en movimientos.
