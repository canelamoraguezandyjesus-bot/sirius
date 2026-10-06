---
titulo: "Cómo aprenden hoy los robots y qué camino realista tiene Sirius"
fecha: 2026-10-05
autor: "claude.ai con «Investigación», por encargo de la sesión del giro al robot (ADR-232)"
pregunta: >-
  Cómo aprenden hoy los robots y qué camino realista tiene Sirius para aprender poco
  a poco de su entorno, del propietario, de sí mismo y de su cuerpo.

nota: >-
  Encargada por la sesión del giro al robot (ADR-232) y hecha en claude.ai con
  «Investigación», porque la sesión no tiene buscador; el propietario la pegó en la
  sesión el 05-10-2026. Texto íntegro tal como llegó, salvo lo personal: el nombre
  del propietario se ha cambiado por «el propietario» y se ha generalizado un
  ejemplo que daba su horario de trabajo, porque el repositorio es público. Las
  etiquetas de hecho, inferencia y opinión son del informe; la sesión no ha
  verificado sus fuentes. Su plan por etapas empieza por el cuerpo; el propietario
  decidió empezar por el cerebro (ADR-232, decisión 1).
caduca_con:
  - >-
    los precios de hardware y de GPU que cita (servos, micrófonos, brazos SO-101, alquiler en la nube)
  - >-
    las versiones de LeRobot, de los modelos de visión, lenguaje y acción, y su soporte en Windows
  - >-
    la lectura de la ley de protección de datos que hace, si cambia su interpretación

estado: VIGENTE
---

# Cómo aprenden hoy los robots y qué camino realista tiene Sirius (informe para el propietario, octubre de 2026)

La mejor manera de que Sirius aprenda es empezar por lo que tu PC ya puede hacer, en este orden: recordar (memoria y preferencias en tu app de Python), atender (mirar a quien habla y reconocer caras con permiso) y conocer su propio cuerpo (autocalibrar la mirada con la cámara). Los "robots que aprenden a cocinar viendo vídeos" siguen necesitando datos grabados con el propio robot, y casi todo ese trabajo es para brazos con manos, no para cabezas.

## TL;DR

- **Lo que más rinde para Sirius no es un VLA ni el refuerzo en simulación:** es memoria con tu aprobación, un sistema de atención (voz + caras) y el autoaprendizaje de su cuerpo. Todo funciona en Windows 11 y sin GPU potente.
- **La seguridad va primero y no depende de la IA:** servos inteligentes con límites, un ESP32 que recorta órdenes y vigila un "latido" del PC, y una seta que corta la corriente de los motores. La IA solo elige habilidades de una lista.
- **Para aprender imitación "de verdad", lo práctico es un brazo SO-101 aparte** (unos 300–400 € imprimiendo tú las piezas [Inferencia]), con LeRobot, unas 50 demostraciones por tarea y GPU alquilada. Una GPU de 16 GB está muy cara en España en 2026 (RTX 5060 Ti 16 GB: 800–980 € entre agosto y octubre).

## Resumen en 1 minuto

- **[Hecho]** Hoy los robots aprenden de cinco formas: recordando, imitando demostraciones, con modelos de visión-lenguaje-acción (VLA), con vídeos de personas y con refuerzo en simulación.
- **[Inferencia]** Para una cabeza sin manos, "aprender una tarea" equivale a aprender a mirar, atender, gesticular, mover la boca al hablar, calibrarse, reconocer personas y aprender tus rutinas.
- **[Hecho]** Lo más parecido a Sirius es de Columbia (*Science Robotics*, enero de 2026): una cara robótica aprendió a mover los labios mirándose en un espejo y luego viendo vídeos de YouTube.
- **[Opinión]** Empieza por seguridad y memoria; sigue con sentidos y atención; deja el SO-101 y las piernas para después.
- **[Opinión]** Usa servos de bus serie con realimentación (Feetech STS/SCS), no PWM: sin realimentación Sirius no puede "sentir" su cuerpo.
- **[Opinión]** Cámara fija gran angular en la frente para aprender y grabar; las cámaras en los ojos son más bonitas pero mucho más difíciles.
- **[Opinión]** Nube para lo pesado (modelos grandes, entrenar de vez en cuando); local para lo privado (vídeo y audio de casa).
- **[Inferencia]** A 5–8 h/semana, calcula 12–18 meses para una cabeza segura que atiende, recuerda, se calibra y aprende tus rutinas.

**Suposición de tiempo [Opinión]:** 5–8 horas por semana, contando semanas perdidas por turnos.

**Etiquetas:** [Hecho] = con fuente y fecha. [Inferencia] = deducido o estimado por mí. [Opinión] = mi recomendación. ⚡ = cambia rápido; compruébalo antes de comprar.

---

## 1. Los tipos de aprendizaje, en sencillo

**En pocas palabras:** Hay dos familias. Aprender "con la cabeza" (recordar, razonar, preguntar) usa modelos de lenguaje y bases de datos y da resultados en semanas. Aprender "con el cuerpo" (imitar, practicar) usa redes entrenadas con datos del robot y tarda meses.

### 1a. Aprender recordando

**Qué es.** El robot guarda lo que pasa (memoria episódica, como un diario) y lo que sabe en general (memoria semántica: "al propietario le gusta el café sin azúcar"). Antes de responder busca lo relevante y se lo pasa al modelo de lenguaje; eso se llama RAG (recuperación aumentada).

**Ejemplos.** [Hecho] *Generative Agents* (Stanford, 2023) usó un flujo de memoria con reflexiones periódicas y recuperación por relevancia, actualidad e importancia. MemGPT (2023, hoy Letta) separa un contexto corto y un archivo largo que el modelo consulta. Mem0 (2024–2025) extrae hechos de las conversaciones y los guarda como memorias actualizables.

**Datos y hardware.** [Inferencia] No hay que entrenar nada. Funciona sin GPU: SQLite, un índice de vectores (ChromaDB o LanceDB) y un modelo de embeddings pequeño en CPU. Un embedding es un resumen numérico de un texto para buscar por significado.

**¿Aplica a una cabeza?** [Opinión] Totalmente; es lo más útil para Sirius. Separa en tu app tres memorias: diario de eventos; hechos y preferencias con fecha, fuente y confianza; y reglas de comportamiento aprobadas por ti.

### 1b. Imitación con demostraciones teleoperadas

**Qué es.** Tú mueves el robot (teleoperación, por ejemplo con un brazo "líder" que el robot copia) mientras se graban cámara y motores. Una red aprende a copiar: ve la imagen y produce el siguiente movimiento. Esa red es la "política"; cada grabación completa de una tarea es un "episodio".

**Ejemplos.**
- [Hecho] ACT y ALOHA (Stanford, RSS 2023, arXiv 2304.13705): dos brazos de menos de 20.000 $ y una red que predice "trozos" de movimiento; abrió un vasito de salsa translúcido y encajó piezas con un 80–90 % de éxito con solo 10 minutos de demostraciones (unas 50).
- [Hecho] Mobile ALOHA (enero de 2024, Fu, Zhao y Finn, arXiv 2401.02117): tareas de cocina con 50 demostraciones por tarea; entrenar a la vez con datos de otras tareas subió el éxito hasta 90 puntos, por encima del 80 % (34 puntos de mejora media).
- [Hecho] Diffusion Policy (2023): genera movimientos "limpiando ruido" paso a paso, como los generadores de imágenes.
- [Hecho] UMI (2024) recoge demostraciones sin robot, con una pinza de mano con GoPro; el guante de Sunday Robotics (2025) sigue la misma idea.

**Datos.** [Hecho] La guía oficial de LeRobot (2026) recomienda empezar con 50 episodios y subir a 100–300; con 50 episodios limpios, ACT debería superar el 70 % de éxito en la configuración grabada. [Inferencia] Entrenar ACT cabe en una GPU de 8–12 GB.

**¿Aplica a una cabeza?** [Inferencia] Sí, de otra forma: podrías teleoperar la cara (con un mando o tu propia cara vista por la cámara) y grabar cómo reaccionar. Vale menos que en un brazo, porque la cabeza no toca objetos.

### 1c. Modelos de visión-lenguaje-acción (VLA)

**Qué es.** Un modelo grande que recibe imágenes y una orden ("coge la taza") y devuelve movimientos. Se entrena con muchos robots y luego se ajusta al tuyo con pocas demostraciones (fine-tuning). LoRA es un ajuste barato que solo entrena pequeños "parches".

| Modelo (fecha) | ¿Pesos abiertos? | Tamaño | VRAM ejecutar / ajustar | ¿Windows? | ¿LeRobot? |
|---|---|---|---|---|---|
| RT-1 (2022), RT-2 (jul 2023), Google | No | RT-2: hasta 55.000 M | — | — | No |
| Open X-Embodiment (oct 2023) | Datos abiertos | >1 millón de episodios, 22 robots | — | — | Convertible |
| Octo (2024) | Sí, MIT | 27–93 M | [Inferencia] GPU pequeña | [Inferencia] Linux | No |
| OpenVLA (jun 2024) / OFT (feb 2025) | Sí, MIT | 7.000 M | [Inferencia] ~16 GB ejecutar; LoRA >24 GB | [Inferencia] Linux | No |
| π0 (oct 2024), π0-FAST (ene 2025), π0.5 (abr 2025) | Sí, openpi (Apache 2.0) | ~3.000 M | [Hecho] openpi: >8 GB ejecutar, >22,5 GB LoRA, >70 GB completo | [Hecho] Probado en Ubuntu | Sí |
| π*0.6 Recap (17 nov 2025), π0.7 (16 abr 2026) | No ⚡ | No publicado | [Hecho] π0.6: 63 ms por bloque en una H100 | — | No |
| SmolVLA (3 jun 2025) | Sí, Apache 2.0 | 450 M | [Hecho] GPU de consumo o CPU; [Inferencia] ajuste con 12–16 GB | Sí | Sí |
| GR00T N1 (mar 2025) → N1.7 (abr 2026), NVIDIA | Sí, licencia NVIDIA ⚡ | N1: ~2.000 M; N1.6: 3.000 M | [Inferencia] ajuste con ≥24 GB | [Inferencia] Linux | Sí |
| Gemini Robotics, On-Device (jun 2025), 1.5 (sep 2025), 2 (jul 2026) | No | — | Solo socios | — | No |
| Gemini Robotics-ER 1.5 (sep 2025), ER 2 (30 jul 2026) | No, **pero por API** | — | Nube | Sí, API | No |

**Notas.**
- [Hecho] Licencia de GR00T N1.6: unas guías dicen "One-Way Noncommercial" y otras "Open Model License". Mira la ficha en Hugging Face. N1.7 (17 abr 2026) se describe como comercial y preentrenado con 20.854 h de vídeo humano en primera persona (MarkTechPost, abril de 2026, fuente secundaria).
- [Hecho] SmolVLA se preentrenó con menos de 30.000 episodios de 481–487 datasets de la comunidad (~10 millones de fotogramas). En el SO-100 pasó del 51,7 % de éxito sin ese preentrenamiento al 78,3 % con él (Hugging Face, junio de 2025).
- [Hecho] ER 1.5 (`gemini-robotics-er-1.5-preview`) está marcado "para retirada pronto". ER 2 está en vista previa pública en la Gemini API y AI Studio (`gemini-robotics-er-2-preview` y `-streaming-preview`) ⚡.

**¿Aplica a una cabeza?** [Opinión] Un VLA de movimientos no, porque no hay datos de cabezas. Sí sirve **Gemini Robotics-ER por API como "ojos que razonan"**: le mandas una foto y te dice dónde están los objetos, qué ha cambiado o cuánto progreso lleva una tarea. Encaja con tu app.

### 1d. Aprender de vídeos de personas

**Qué funciona de verdad (2024–2026).**
- [Hecho] R3M y VIP (2022) aprendieron "cómo mirar" con vídeo humano (Ego4D); ayudan, pero el robot sigue necesitando sus propias demostraciones.
- [Hecho] LAPA (2024) deduce "acciones latentes" de vídeos sin etiquetas y las traduce al robot con pocos datos reales.
- [Hecho] EgoMimic (2024) mezcla vídeo humano en primera persona con datos del robot; RHyME (Cornell, 2025) aprende aunque los movimientos humanos y del robot no coincidan.
- [Hecho] DreamGen / GR00T-Dreams (NVIDIA, 2025) genera vídeo sintético de robots. V-JEPA 2 (Meta, junio de 2025) aprende un "modelo del mundo" con más de un millón de horas de vídeo y planifica con pocos datos de robot.
- [Hecho] Figure, Project Go-Big (18 sep 2025): con un 100 % de vídeo humano grabado en casas de Brookfield, su robot aprendió a **navegar** ("ve a la nevera"). Es navegación, no manipulación fina.
- [Hecho, fuente débil] Blogs de aficionados (optimusk.blog, 2026) dicen que Tesla pasó a mediados de 2025 de trajes de captura a grabar personas con casco y mochila de cámaras. No es oficial.

**La verdad sobre "cocinar viendo vídeos".** [Inferencia] Ningún sistema publicado hasta octubre de 2026 aprende a manipular comida *solo* con vídeos. Siempre hay datos del robot (teleoperación, correcciones o práctica), porque el vídeo no muestra fuerzas ni contacto.

**¿Aplica a una cabeza?** [Hecho] Sí, y aquí funciona: el robot de Columbia sincronizó labios viendo vídeos de personas hablando y cantando, **después** de aprender su propia cara frente a un espejo (14 de enero de 2026). Para una cara, el vídeo humano es justo el dato correcto.

### 1e. Refuerzo en simulación y paso al robot real (sim2real)

**Qué es.** El robot practica millones de veces en un mundo virtual y recibe premios cuando acierta (aprendizaje por refuerzo, RL). Luego se pasa al robot real (sim2real). Dos trucos: **aleatorización de dominio** (variar pesos, fricción y luces) e **identificación del sistema** (medir el robot real para que la simulación se le parezca).

**Herramientas.**
- [Hecho] Isaac Lab (NVIDIA): Ubuntu 22.04 o Windows 11, 32 GB de RAM y 16 GB de VRAM o más (documentación, 2026). Un aficionado entrenó con una RTX 4060 de 8 GB, con limitaciones.
- [Hecho] MuJoCo (DeepMind): gratis, ligero, funciona en Windows; MJX acelera en GPU. MuJoCo Playground (2025) trae robots con patas y manos listos.
- [Hecho] Genesis (2024–2025) y Newton (NVIDIA, Disney y DeepMind, 2025) son más nuevos ⚡. Disney entrenó así la forma de andar de sus droides BDX; los robots con patas aprenden a caminar así.

**¿Aplica a una cabeza?** [Opinión] Casi no: cuello y ojos se controlan bien sin RL. Para la cabeza, la simulación sirve para **probar tu código** en un modelo virtual (MuJoCo o visor URDF) antes de mover servos. El RL tiene sentido si algún día hay piernas.

### 1f. Aprender de forma continua sin olvidar

**Olvido catastrófico:** al entrenar una red con algo nuevo puede "pisar" lo anterior, como si al aprender una canción olvidaras las demás.

**Remedios.** Replay (mezclar datos viejos con los nuevos), EWC (proteger conexiones importantes), adaptadores LoRA por habilidad, y memoria externa o bibliotecas de habilidades (guardar el conocimiento fuera de la red).

**Estado del arte.** [Hecho] LIBERO (2023) es el banco de pruebas estándar; hoy se usa sobre todo para comparar VLAs. [Inferencia] El aprendizaje continuo dentro de redes sigue siendo investigación en 2026.

**Lo práctico.** [Opinión] No reentrenes nunca encima del modelo viejo. Memoria y preferencias en una base de datos; habilidades como funciones o políticas separadas con versión; si una sale mal, vuelves a la anterior.

### 1g. Cabezas y caras robóticas que aprenden

**Creative Machines Lab, Columbia (Hod Lipson).**
- [Hecho] **Eva (2021)** aprendió a imitar expresiones observándose a sí misma.
- [Hecho] **Emo (*Science Robotics* 9(88), eadi4724, marzo de 2024)** predice una sonrisa unos 839 ms antes de que la persona sonría y la imita a la vez; tiene 26 grados de libertad (23 motores faciales y 3 de cuello).
- [Hecho] **Modelo de sí mismo (2025, *Nature Machine Intelligence*):** robots que aprenden un modelo de su cuerpo viéndose en vídeo con una sola cámara.
- [Hecho] **Labios (*Science Robotics* 11(110), eadx3017, 14 de enero de 2026):** 26 motores faciales y labios de silicona con 10 grados de libertad. Hizo miles de expresiones al azar ante un espejo, luego vio horas de YouTube; usa un autoencoder variacional más un "transformer de acciones faciales". Lo evaluaron 1.300 voluntarios; según Hod Lipson (Live Science, 27 ene 2026), le costaron especialmente los sonidos duros como la "B" y los que fruncen los labios, como la "W" (primer autor: Yuhang Hu).

**Otras referencias.** [Hecho] iCub (IIT): cámaras en los ojos y control de mirada con estabilización. Disney Research: animatrónicos expresivos y RL que combina estilo de animación con física. Ameca: cara de gama alta con cámaras en los ojos. Furhat: cara proyectada sobre una máscara, con cámara y micrófonos.

**Reachy Mini (Pollen + Hugging Face, julio de 2025).**
- [Hecho] 28 cm, 1,5 kg; cabeza de 6 grados de libertad, giro de cuerpo, dos antenas, cámara gran angular, altavoz de 5 W, SDK en Python.
- [Hecho] Salió a 299 $ (Lite) y 449 $ (Wireless); la página de Hugging Face muestra hoy 399 $ y 499 $ más impuestos y envío ⚡. La Wireless lleva Raspberry Pi 5, batería y acelerómetro.
- [Hecho] Algunas fichas de 2025 daban 2 micrófonos a la Lite; la página actual indica 4 en ambas. En 2025, la Lite funcionaba con Mac y Linux y Windows estaba "pronto" ⚡.

[Opinión] Reachy Mini **no aprende sola**: ejecuta "apps" (seguir caras, conversar, bailar). Sirve como **referencia** de cámara, micrófonos y SDK, y como **banco de pruebas** de tu software. No sustituye a Sirius: no tiene ojos móviles, párpados, cejas ni mandíbula.

**Técnicas concretas para Sirius [Inferencia en datos].**

| Técnica | Qué hace | Dificultad | Datos |
|---|---|---|---|
| Autocalibración de la mirada | Mueve cuello y ojos, mira cómo se desplaza un punto en la imagen y ajusta | Baja-media | Minutos de movimientos automáticos |
| Modelo directo aprendido | "Si muevo el servo X tantos grados, la imagen cambia así" | Media | Cientos o miles de pares grabados solos |
| Sincronización labial (visemas) | Del audio a formas de boca (visema = forma de la boca para un sonido) | Baja con reglas; alta aprendida | Reglas: ninguno; aprendida: horas de vídeo |
| Aprender expresiones | Asocia cejas, párpados y boca con emociones | Media | Tus valoraciones "bien/mal" |
| Sistema de atención | A quién mirar según voz, caras y movimiento | Baja-media | Ninguno al principio; luego correcciones |

---

## 2. Cómo lo hacen las empresas (2024–2026)

**En pocas palabras:** Aprenden con miles de horas de teleoperación, vídeo humano y simulación, en miles de GPU. Su escala no se copia, pero sus ideas sí: separar "cerebro que razona" y "cerebro que mueve", aprender de correcciones y medirlo todo.

| Empresa | Modelos / productos | Datos | Hardware / a bordo | Novedades 2026 |
|---|---|---|---|---|
| **Tesla Optimus** | Gen 2/2.5; V3 anunciado | [Hecho, fuente débil] Antes trajes y realidad virtual; desde mediados de 2025, vídeo humano con casco y mochila | [Hecho, fuente débil] Clúster Cortex con decenas de miles de H100; chip AI5 | [Hecho] 28 ene 2026: Musk dijo que sigue "very much in the R&D phase". [Hecho, fuente débil] En septiembre la presentación completa de V3 seguía pendiente ⚡ |
| **Figure** | Helix (feb 2025), Helix 02 (ene 2026), Figure 03 (oct 2025) | [Hecho] Helix: ~500 h de teleoperación multi-robot y multi-operador, menos del 5 % del tamaño de los datasets VLA anteriores (Figure); Go-Big: vídeo humano en casas | [Hecho] Hasta dos GPU NVIDIA a bordo | [Hecho] Más de 350 Figure 03 entregados hasta abril; directo de paquetes en mayo |
| **1X** | NEO (reservas desde 28 oct 2025; 20.000 $ o 499 $/mes); Redwood; World Model | [Hecho] Teleoperación "Expert Mode" en casas de clientes, que alimenta el entrenamiento | No detallado | [Hecho] Fábrica en Hayward (abril); a mediados de agosto no había entregas verificadas ⚡ |
| **Physical Intelligence** | π0, π0-FAST, π0.5, π*0.6, π0.7 | [Hecho] π0: ~10.000 h en varios robots; π0.5: datos heterogéneos; Recap: demostraciones + correcciones + práctica | [Hecho] π0.6: 63 ms en una H100 | [Hecho] π0.7 (16 abr); socios Weave y Ultra (feb) |
| **Google DeepMind** | RT-2, ALOHA 2, Gemini Robotics 1.5/2, ER 1.5/1.6/2 | ALOHA y varios robots | Nube de Google | [Hecho] ER 2 por API (30 jul); Apptronik (Apollo 2), Boston Dynamics (Spot) |
| **NVIDIA** | GR00T N1–N1.7, N2 anunciado; Cosmos; Isaac Lab; Jetson Thor/T4000 | [Hecho] "Pirámide": pocos datos reales arriba, sintéticos y simulación en medio, mucho vídeo humano abajo | [Hecho] Jetson T4000 (CES, 5 ene 2026) | [Hecho, secundaria] N1.7 (abril); N2 para finales de 2026 ⚡ |
| **Hugging Face LeRobot** | LeRobot 0.6.1 (3 ago 2026), SmolVLA, SO-101, LeKiwi, HopeJR, Reachy Mini | [Hecho] Datasets de la comunidad en el Hub | [Hecho] SmolVLA: ~30.000 h de GPU en total | [Hecho] Compró Pollen (abril 2025); hackatones |

**Otros.** [Hecho] TRI y Boston Dynamics mostraron en agosto de 2025 "Large Behavior Models" en Atlas. Generalist AI anunció GEN-0 (noviembre de 2025) entrenado con más de 270.000 h de manipulación. Sunday Robotics (noviembre de 2025) recoge datos con un guante en vez de teleoperar.

**Lección de privacidad de 1X.** [Hecho] En Expert Mode un operador remoto ve tu casa por las cámaras; 1X promete aprobación, zonas prohibidas y difuminado, sin auditoría independiente. [Opinión] Para Sirius: nada de vídeo de casa sale del PC sin que tú lo apruebes.

| Puedes copiar | No puedes copiar |
|---|---|
| Separar razonador (modelo de lenguaje o Gemini-ER) y ejecutor (habilidades locales) | Miles de horas de teleoperación |
| Aprender de correcciones (idea de Recap, DAgger) | Clústeres de miles de GPU |
| Registrar todo con fecha y revisarlo | Modelos cerrados (π0.7, Gemini Robotics 2) |
| Ajustar modelos abiertos (SmolVLA, π0, GR00T) | Humanoides y sus datos |
| Vídeo humano para la cara (como Columbia) | Vídeo a escala de internet para manipular |

---

## 3. Qué puede hacer un aficionado

**En pocas palabras:** Con LeRobot, un SO-101 y unas 50 demostraciones, un principiante enseña "coge el cubo y déjalo en el cuenco" en unas semanas. ACT cabe en una GPU modesta; SmolVLA va mejor con 12–16 GB o alquilando GPU.

### 3a. LeRobot y Windows 11

- [Hecho] LeRobot es la librería abierta de Hugging Face para grabar datos, entrenar políticas y ejecutarlas. La versión 0.6.1 es del 3 de agosto de 2026 ⚡; pide Python 3.12+ y PyTorch 2.10+, y se instala con `pip install 'lerobot[core_scripts,training]'`. En Windows usa el PyTorch con CUDA para Windows (CUDA es la tecnología de NVIDIA para cálculos en GPU).
- [Hecho] Un laboratorio de la Universidad de Estrasburgo no logró que WSL2 (Linux dentro de Windows) manejara bien los puertos serie y las cámaras; el contenedor se colgaba.

[Opinión] **La mejor manera:** LeRobot **nativo en Windows 11** para grabar y controlar (USB directo); entrena en la nube o en WSL2 con datos ya grabados. Arranque dual con Ubuntu solo si te atascas o para openpi y GR00T, que piden Linux.

### 3b. SO-100 frente a SO-101

- [Hecho] Ambos son brazos abiertos de 6 articulaciones con servos Feetech STS3215 (TheRobotStudio + Hugging Face). El SO-101 (2025) tiene cableado y montaje más sencillos y servos con otras relaciones de engranaje en el brazo líder, para que se mueva suave con la mano. El seguidor usa STS3215 de 12 V y 30 kg·cm.

**Materiales y precios ⚡** (consultados en octubre de 2026; casi todos en dólares, no encontré kit completo con precio en tiendas UE):

| Pieza | Precio | Tienda |
|---|---|---|
| Servo STS3215 C018 (12 V, 30 kg·cm) | 15,99 $ (13,99 $ en lotes de 10) | WowRobo |
| Servo STS3215 C018 | 31,71 $ | RobotShop |
| Kit de motores SO-ARM101 Pro (sin piezas impresas) | 277,99 $ | Seeed Studio |
| Electrónica del seguidor (6 servos, fuente 12 V 5 A, placa USB-C, cables) | 166,49 $ | Amazon (ForgeMotion Labs) |
| Piezas impresas del seguidor | 31,49 $ | Amazon (ForgeMotion Labs) |
| 2 cámaras USB | [Inferencia] 20–50 € cada una | Cualquier tienda UE |

[Inferencia] Imprimiendo tú (0,5–1 kg de PLA o PETG), líder + seguidor sale por unos 300–400 € con envío e IVA; montado, 500 € o más. Para la UE mira el almacén europeo de Seeed, Kiwi Electronics (Países Bajos) u OpenELAB (Alemania).

### 3c. Demostraciones, éxito y errores típicos

- [Hecho] **ACT:** 50 episodios para empezar; más del 70 % de éxito en la configuración grabada (guía de LeRobot, 2026).
- [Hecho] **SmolVLA:** la documentación recomienda unos 50 episodios; su ejemplo usó 50 en 5 posiciones del cubo (10 por posición) y con 25 el resultado fue malo.
- [Inferencia] **Diffusion Policy:** 50–200 episodios y más pasos de entrenamiento que ACT.
- [Hecho, secundaria] En el SO-100 real del artículo de SmolVLA: ACT 48,3 %, π0 61,7 %, SmolVLA 78,3 %.

**Errores de principiante** (blog de una aficionada en Hugging Face y guía de LeRobot): la cámara se movió un poco entre grabar y probar; la luz cambió del día a la noche (fija exposición y balance de blancos); mala calibración; demostraciones dudosas. [Hecho] La guía resume: "la iluminación importa más que la resolución", y si tú no puedes hacer la tarea mirando solo la cámara, está mal puesta.

### 3d. GPU para entrenar y ejecutar

| GPU | ACT (50 episodios) | SmolVLA ajuste | π0 / GR00T |
|---|---|---|---|
| Solo CPU | [Inferencia] Entrenar inviable; ejecutar lento | Ejecutar lento; entrenar en nube | Nube |
| RTX 3060 12 GB | [Hecho, secundaria] ~30 min por 100 épocas | [Inferencia] Posible, varias horas | Ejecutar π0 justo; ajustar en nube |
| 4060 Ti/5060 Ti 16 GB, 4070/5070 12 GB | [Inferencia] 20–40 min | [Inferencia] 4–8 h | Ejecutar π0 sí; LoRA no (>22,5 GB) |
| 3090/4090 24 GB | [Hecho, secundaria] ~10 min en 4090 | [Inferencia] 2–4 h | π0 LoRA justo; GR00T posible |
| 5090 32 GB | [Inferencia] Muy rápido | [Inferencia] ~2 h | π0 LoRA cómodo |

[Hecho] Referencia oficial: 20.000 pasos de SmolVLA tardan unas 4 horas en una A100.

### 3e. Alquiler de GPU en la nube ⚡

| Servicio | Precio (2026) | Entrenamiento típico [Inferencia] |
|---|---|---|
| RunPod Community | RTX 4090 0,34 $/h; A100 desde 1,19 $/h | ACT <1 €; SmolVLA en A100 (~4 h) 5–7 € |
| RunPod Secure | RTX 4090 0,69–0,74 $/h; A100 80 GB 1,59 $/h; H100 2,89–3,49 $/h (revisado 1 oct 2026) | SmolVLA 6–8 € |
| Vast.ai | Mercado variable; RTX 4090 0,34–0,50 $/h | Parecido o menos |
| Lambda | A100 40 GB 1,99 $/h | SmolVLA ~8 € |
| Google Colab / Hugging Face | Colab gratis con T4 (limitado); HF por horas | SmolVLA en T4: lento |

[Opinión] Sin GPU o con 8 GB, 5–15 € al mes de nube sale mucho más barato que comprar una GPU de 16 GB.

### 3f. Requisitos para ejecutar cada política

| Política | Ejecutar en local | Comentario |
|---|---|---|
| ACT | [Inferencia] GPU de 4 GB o más; CPU lento | La mejor para empezar |
| Diffusion Policy | [Inferencia] GPU de 6–8 GB | Más lenta al ejecutar |
| SmolVLA | [Hecho] GPU de consumo o CPU | Ejecución asíncrona: 30 % más rápida |
| π0 / π0.5 | [Hecho] >8 GB (openpi) | Linux |
| GR00T N1.6 | [Inferencia] ≥16 GB | Linux; licencia NVIDIA |
| OpenVLA 7B | [Inferencia] ~16 GB; menos si se cuantiza | Linux |

### 3g. HIL-SERL, comunidad y precios de GPU en España

- [Hecho] **HIL-SERL** (2024) está en LeRobot: el robot practica en el mundo real con un detector de éxito y tú lo corriges con un mando. Es la versión aficionada de la idea de Recap.
- [Hecho] **Comunidad:** Discord de LeRobot y Reachy Mini, datasets con la etiqueta "lerobot" en el Hub, hackatones de Hugging Face.
- [Hecho] **GPU en España ⚡:** la RTX 5060 Ti 16 GB salió el 16 de abril de 2025 a 459,90 €. En agosto de 2026 su precio mediano era de 856 € en PcComponentes y Coolmod y de 801,95 € en Amazon España (El Chapuzas Informático); en octubre, PcComponentes listaba una Zotac a 984 €. La RTX 5070 de 12 GB estaba desde unos 759 €. La causa es la subida de la memoria DRAM en 2025–2026.
- [Opinión] No compres una GPU nueva de 16 GB solo para Sirius. Si necesitas GPU local, una RTX 3060 12 GB usada es "suficiente" (precio de segunda mano no verificado).

---

## 4. Aprender de una persona sin programar, y aprender de sí mismo

**En pocas palabras:** De ti, Sirius aprende con el ciclo observar → proponer → preguntar → tú confirmas → guardar. De sí mismo: registrar → revisar cada día → proponer mejoras → tú apruebas. **Nada cambia su comportamiento sin tu "sí".**

### 4a. Aprender de ti

**Observar (con permiso).** [Inferencia] Registrar qué app usas, a qué hora empiezas y paras y cuándo estás en el escritorio (cámara o sensor de presencia), para deducir rutinas: "los martes llegas a las 15:30 y abres primero el correo". [Opinión] Solo resúmenes (app y tiempo), nunca capturas de pantalla.

**Preguntar.** [Hecho] El aprendizaje activo pregunta solo cuando hay duda. *KnowNo / Robots that Ask for Help* (Princeton y Google, 2023) usó "predicción conforme", una forma matemática de medir la duda, para pedir ayuda solo cuando no estaba seguro. [Opinión] Para Sirius: por debajo de un umbral de confianza, pregunta; por encima, propone para confirmar.

**Confirmar y corregir.** [Hecho] TAMER (2009): el humano da "bien/mal". DAgger (2011) y HG-DAgger (2019): el humano corrige en el momento del error y se añade a los datos. Yell At Your Robot (2024) y RT-H (2024): correcciones habladas ("más a la izquierda"). π*0.6 con Recap (2025): demostraciones + correcciones + práctica propia.

**Preferencias con pocos ejemplos.** [Hecho] TidyBot (2023) usó un modelo de lenguaje para generalizar desde unos pocos ejemplos de dónde guardas las cosas. [Inferencia] Tu app puede hacer lo mismo con preferencias, sin entrenar nada.

### 4b. Aprender de sí mismo

- [Hecho] **Registro:** qué hizo, cuándo, con qué resultado y qué leían sus servos (posición, carga, temperatura).
- [Hecho] **Reflexión:** en *Reflexion* (2023) un agente escribe qué salió mal y lo usa después; en *REFLECT* (2023) un modelo de lenguaje resume los sensores de un robot para explicar fallos.
- [Hecho] **Autoevaluación:** detectores de éxito y modelos de visión-lenguaje como "jueces". Según Google (julio de 2026), Gemini Robotics-ER 2 acierta un 57,4 % clasificando el progreso de tareas y un 91,3 % encontrando el momento exacto de un evento.
- [Hecho] **Habilidades:** *Voyager* (2023) guardaba cada habilidad que funcionaba como código reutilizable. *AutoRT* (Google, 2024) proponía tareas a una flota de robots con reglas de seguridad tipo "constitución".

### 4c. Riesgos

[Inferencia] Deducir una "costumbre" de un día raro; reconocer peor a ciertas personas o con ciertas luces; guardar datos de visitas sin permiso; pequeños cambios aprobados que suman un comportamiento no deseado. [Opinión] Solución: cada recuerdo y regla con fecha, fuente y botón de "olvidar", y una revisión mensual.

### 4d. Cómo aplicarlo a tu app de Python [Opinión]

1. **Qué guardar (SQLite):** eventos (hora, tipo, quién, resumen); hechos y preferencias (texto, confianza, fuente, fecha, estado: propuesto, aprobado o rechazado); telemetría de servos cada segundo; fallos con su contexto.
2. **Reflexión diaria (por ejemplo, a las 23:00):** un modelo de lenguaje lee el día y escribe un resumen con 0–5 propuestas ("parece que los martes trabajas hasta tarde") y una "lección" por cada fallo.
3. **Aprobación humana:** las propuestas van a una bandeja y solo se activan si pulsas "Aprobar". Guarda versiones para deshacer.
4. **Señal "bien/mal":** dos táctiles capacitivos (coronilla "bien", nuca "mal") o un gesto de pulgar ante la cámara, ligados a lo último que hizo Sirius, al estilo TAMER.

---

## 5. Seguridad: arquitectura por capas

**En pocas palabras:** La seguridad es una cebolla: cada capa para los errores de la anterior y **ninguna depende de que la IA se porte bien**. La última es física: un botón que corta la corriente de los motores.

| Capa | Qué hace | Ejemplo para Sirius |
|---|---|---|
| 1. Mecánica | Topes físicos, servos de bajo par en párpados y mandíbula | Topes impresos en el cuello |
| 2. Firmware del servo | Límites de ángulo, par, temperatura, sobrecarga | Registros del STS3215 |
| 3. Microcontrolador | Recorta posición, velocidad y aceleración; vigila el latido | ESP32 entre el PC y el bus |
| 4. Software del PC | Lista blanca de habilidades con parámetros recortados | `mirar_a(x, y)` con rango limitado |
| 5. IA | Solo elige habilidades, nunca ángulos | El modelo llama a funciones |
| 6. Parada física | Seta que corta la alimentación de los motores | Seta + relé en la línea de servos |

**Firmware del STS3215.** [Hecho] La hoja de datos (STS3215-C001, junio de 2023) indica realimentación de carga, posición, velocidad, tensión, corriente y temperatura, y estas protecciones: sobrecarga (más del 80 % del par de bloqueo durante 2 s), sobrecorriente (más de 2 A durante 2 s apaga la salida), sobretensión y más de 70 °C corta el par. Dice "Limit Angle: No limit": el servo no tiene tope propio y los límites se programan en registros (ángulo mínimo y máximo, par máximo). Algunos vendedores y pruebas dan cifras distintas (25 ms en vez de 2 s; dudas sobre el corte térmico). [Opinión] No confíes solo en el servo. [Inferencia] Dynamixel ofrece protecciones parecidas, mejor documentadas y más caras.

**Microcontrolador local (ESP32, Arduino, STM32 o Teensy)** [Opinión]. El PC habla con el ESP32, no con los servos. El ESP32 impone: límites de cada articulación guardados en su memoria; velocidad y aceleración máximas con rampas suaves; y un **latido (watchdog)**: si en 200–500 ms no llega un mensaje válido del PC, Sirius va despacio a una postura segura (cabeza al centro, mandíbula cerrada) y luego quita el par. [Inferencia] Un ESP32 cuesta menos de 10 €.

**Parada física y electricidad.** [Hecho] ISO 13850 (parada de emergencia) e IEC 60204-1 (equipo eléctrico de máquinas) definen la **categoría 0** (cortar la energía de inmediato), la **1** (frenar controlado y luego cortar) y la **2** (frenar manteniendo la energía). [Opinión] Para Sirius basta la categoría 0: una seta enclavable que abre un relé en la alimentación de los servos, nunca solo un botón en software. Fuente de servos separada de la del PC y el ESP32, fusible en la línea de servos, masas comunes bien hechas y nada de 230 V dentro de la cabeza.

**La IA nunca envía ángulos crudos** [Opinión]: habilidades como `mirar_a(persona)`, `parpadear()`, `expresión("alegre", 0–1)` o `hablar(texto)`, con cada parámetro recortado antes de enviarlo.

**LeRobot.** [Hecho] `max_relative_target` limita cuánto se mueve cada motor en una orden respecto a su posición actual, "for safety purposes"; por defecto está desactivado (None). Un usuario explica que funciona como **limitador de velocidad**, no de rango, y una propuesta abierta en 2026 señala que el SO-100/101 aún no se detiene si un motor tira de corriente sin llegar a su destino. [Opinión] Actívalo siempre y añade límites de rango en el ESP32.

**Riesgos de los modelos de lenguaje.** [Hecho] RoboPAIR (Universidad de Pensilvania, 2024; Robey et al., arXiv 2410.13691) "liberó" robots controlados por modelos de lenguaje —el perro Unitree Go2, el vehículo Clearpath Jackal y NVIDIA Dolphins— para hacer acciones peligrosas, a menudo con un 100 % de éxito; en el Go2 pasó del 37 % del método anterior (PAIR) al 100 %. [Inferencia] También hay inyección de instrucciones (un texto en una web o correo que el modelo obedece) y comandos inventados. [Opinión] La lista blanca y los límites del ESP32 protegen aunque la IA "quiera" salirse.

**Pellizcos y normas.** [Opinión] Párpados y mandíbula pueden pillar dedos: micro servos de bus de bajo par (como el Feetech SCS0009), par limitado en registro y holguras de 8–10 mm. [Hecho] ISO 10218 (robots industriales, revisada en 2025) e ISO/TS 15066 (robots colaborativos, límites de fuerza sobre el cuerpo). [Opinión] Para ti, solo referencia conceptual. Prueba cada habilidad primero en un modelo virtual, luego con servos sin carga a velocidad baja y por último en la cabeza.

**Qué servos elegir.**

| Tipo | Realimentación | Para aprender | Precio [Inferencia] |
|---|---|---|---|
| PWM de hobby (SG90, MG996R) | Ninguna | No sabe dónde está ni si se atasca | 2–10 € |
| Bus serie Feetech STS/SCS | Posición, carga, temperatura, corriente | Aprende su cuerpo y detecta fallos | 10–30 € |
| Dynamixel (XL330, XL430) | Igual o mejor, muy documentado | Igual | 25–60 € |

[Opinión] **Feetech STS3215 para el cuello y micro servos de bus Feetech para ojos, párpados y cejas.** Sin realimentación no se puede medir qué hizo de verdad cada motor, y sin eso no hay "aprender de su cuerpo".

---

## 6. Sensores de la cabeza y dónde van

**En pocas palabras:** Imprescindible: una cámara gran angular fija y una matriz de 4 micrófonos con cancelación de eco. Lo demás (presencia, distancia, tacto, inclinación) es barato y ayuda a aprender rutinas y a recibir tu "bien/mal".

### 6a. Cámaras

- [Opinión] **Frente o puente de la nariz, fija y gran angular (recomendada):** la imagen solo se mueve con el cuello, que conoces por los servos, así que aprender y grabar es más fácil.
- [Hecho] **Dentro de los ojos (iCub, Ameca):** se mueve con la mirada y hay que compensarlo. [Opinión] Intermedio: fija en la frente y, más adelante, una pequeña en un ojo para autocalibrar la mirada.
- [Inferencia] **Mono USB** 1080p, 90–120° y 30 fps basta (20–60 €). **Estéreo o profundidad** (OAK-D Lite, Orbbec, RealSense) mide distancias; útil, no imprescindible.
- [Hecho] RealSense se separó de Intel en julio de 2025 con 50 millones de dólares de Intel Capital y MediaTek; fuentes secundarias apuntan a una adquisición en 2026 que no he verificado ⚡.
- [Inferencia] Una 1080p MJPEG a 30 fps cabe en USB 2.0; con dos cámaras y micrófono, mejor en controladores USB distintos.
- [Opinión] **Privacidad:** tapa deslizante impresa y un LED de "grabando" cableado al ESP32 para que el software no pueda apagarlo.

### 6b. Micrófonos

- [Hecho] **ReSpeaker XVF3800 (Seeed, 2025):** 4 micrófonos en círculo con cancelación de eco (AEC), control de ganancia, dirección de llegada (DoA), detección de voz (VAD), formación de haz y supresión de ruido, a hasta 5 m; USB sin controladores en Windows; 16 kHz máximo.
- [Hecho] **Precios ⚡:** 60,99 $ en Seeed; 58,30 € con IVA en Kiwi Electronics; 61,44 € en OpenELAB; 83,49 € en Antratek.
- [Opinión] **La AEC es imprescindible:** sin ella Sirius se oye por su altavoz y se "responde". Saca el audio del altavoz por la salida de 3,5 mm del ReSpeaker para que sepa qué suena.
- [Opinión] **Colocación:** la placa en la coronilla, micrófonos hacia arriba bajo una rejilla; el altavoz abajo (barbilla o cuello), lo más lejos posible; espuma o goma entre servos y placa.
- [Inferencia] Servos y ventiladores meten ruido: que Sirius no se mueva mientras escucha frases largas. Software: openWakeWord (palabra de activación), Silero VAD y huella de voz con SpeechBrain o pyannote, con consentimiento.

### 6c. Otros sensores [precios: Inferencia]

| Sensor | Precio | Qué aprende Sirius | Dónde | Conexión |
|---|---|---|---|---|
| IMU (MPU6050 / BNO085) | 5–25 € | Su inclinación; golpes | Cráneo, cerca del cuello | I2C al ESP32 |
| Distancia ToF (VL53L1X) | 10–15 € | A qué distancia estás | Frente | I2C al ESP32 |
| Radar mmWave (LD2410) | 5–10 € | Presencia aunque no te muevas: rutinas | Base o cuello | Serie al ESP32 |
| PIR | 2–5 € | Movimiento en la habitación | Base | Digital al ESP32 |
| Luz (BH1750) | 3–5 € | Día o noche; ajustar cámara | Coronilla | I2C |
| Temperatura/humedad (SHT31) | 5–10 € | Calor interno de servos y ambiente | Dentro y fuera | I2C |
| Táctiles (TTP223 / MPR121) | 1–10 € | Canal "bien/mal" | Coronilla y nuca | ESP32 |
| Propiocepción de servos | Incluida | Su cuerpo | — | Bus serie |
| Térmica (MLX90640), opcional | 50–80 € | Presencia por calor | Frente | I2C |

**Comparación.** [Hecho] Reachy Mini: cámara gran angular, 4 micrófonos, altavoz y acelerómetro (Wireless). iCub: cámaras en los ojos, micrófonos, inercia y piel táctil. Ameca: cámaras en los ojos y micrófonos. Furhat: cámara y micrófonos. [Inferencia] InMoov: webcams en los ojos. [Opinión] Con esta propuesta Sirius quedaría al nivel de Reachy Mini o algo por encima.

### 6d. Modelos locales de visión y voz por tipo de PC [Inferencia, ⚡]

| Tarea | A: sin GPU | B: 8–12 GB | C: 16–24 GB | Nube |
|---|---|---|---|---|
| Detección de caras (MediaPipe / YuNet) | Sí | Sí | Sí | No |
| Reconocimiento de caras (InsightFace), con consentimiento | Sí, lento | Sí | Sí | No (privacidad) |
| Voz a texto (faster-whisper) | "small"/"base" en CPU | large-v3-turbo | large-v3 | No |
| Visión-lenguaje (Ollama) | Moondream o Gemma 3 4B, lento | Qwen2.5-VL 7B o Gemma 3 12B cuantizados | Gemma 3 27B o Qwen-VL 32B cuantizados | Razonamiento espacial (Gemini-ER) |
| Conversación | API | 8.000 M local + API | 14.000–32.000 M local + API | Tareas complejas |

---

## Tabla de los tres casos de PC

**En pocas palabras:** Puedes empezar con cualquier PC; la GPU solo cambia cuánto haces en casa y cuánto alquilas.

| | A: sin GPU | B: 8–12 GB | C: 16–24 GB |
|---|---|---|---|
| Entrenar en local | Nada pesado | ACT, Diffusion pequeña, modelo directo de la cara | ACT, Diffusion, SmolVLA; π0 LoRA solo con 24 GB |
| Ejecutar en local | Caras, Whisper pequeño, memoria, control | + visión-lenguaje 7.000 M, Whisper turbo, ACT | + visión-lenguaje mayor, SmolVLA, π0 |
| En la nube | Modelo de lenguaje, visión-lenguaje, entrenamientos | Modelo grande, SmolVLA | Solo π0/GR00T completos y modelos punteros |
| Coste extra [Inferencia] | 10–25 €/mes | 5–15 €/mes | 0–10 €/mes |
| GPU en España ⚡ | 0 € | [Inferencia] 3060 12 GB usada 200–300 €; 5070 desde ~759 € | [Hecho] 5060 Ti 16 GB 800–980 €; [Inferencia] 4090/5090 >2.000 € |

**Si el PC entrara en el presupuesto** [Opinión]: una GPU de 16 GB se comería entre la mitad y casi todo el mínimo de 900 €. Elige B (o A + nube) y deja el dinero para servos, sensores y SO-101. Solo con 2.500 € tendría sentido un PC C, renunciando al brazo.

---

## Lo que conviene replantear

**En pocas palabras:** Tu plan es bueno; estas ocho cosas conviene ajustarlas.

1. **Imitación, VLA y "cocinar viendo vídeos" son para manos.** [Opinión] En una cabeza lo equivalente es mirar, atender, gesticular, sincronizar labios, autocalibrarse, reconocer y aprender rutinas. Persigue eso.
2. **¿Un SO-101 como laboratorio?** [Opinión] Sí, si quieres aprender imitación y VLA de verdad: es lo más barato y mejor documentado. Pero tras la cabeza básica (etapa 5).
3. **Windows o Linux.** [Opinión] Windows para controlar y grabar; nube o WSL2 para entrenar. Arranque dual solo para openpi o GR00T en local.
4. **Servos con realimentación.** [Opinión] Imprescindibles; los PWM cierran la puerta a "aprender de su cuerpo".
5. **Reachy Mini.** [Opinión] Úsala gratis como referencia (es abierta). Comprarla (~450–550 € con IVA y envío [Inferencia]) solo si quieres probar software mientras imprimes.
6. **Nube o local.** [Opinión] Local: vídeo y audio de casa, caras, memoria. Nube: razonamiento (modelo de lenguaje, Gemini-ER) con texto o fotos sueltas que permitas, y entrenamiento.
7. **RL en simulación.** [Opinión] No compensa para la cabeza; guárdalo para las piernas.
8. **Privacidad y ley (España/UE), lo esencial:**
   - [Hecho] El RGPD (art. 2.2.c) no se aplica al tratamiento "por una persona física en el ejercicio de actividades exclusivamente personales o domésticas".
   - [Hecho] El TJUE (caso Ryneš, C-212/13, 11 dic 2014) dijo que una cámara doméstica que graba aunque sea en parte la vía pública **pierde** esa exención.
   - [Hecho] El Reglamento de IA (2024/1689, art. 2.10) no se aplica a las obligaciones de personas físicas que usan IA "en el ejercicio de una actividad personal de carácter no profesional". Las prohibiciones del art. 5 rigen desde el 2 de febrero de 2025; el texto consolidado de julio de 2026 parece haber movido algunas fechas ⚡.
   - [Opinión] Que la cámara no apunte a ventana ni calle; avisa a las visitas y tapa la cámara si no quieren; no guardes caras ni voces de visitas sin permiso; cifra el disco; borra el vídeo crudo en 24–72 h; nunca subas vídeo de casa a datasets públicos.

---

## Plan por etapas para Sirius

**En pocas palabras:** Ocho etapas, de la más segura y barata a la más ambiciosa, a 5–8 h/semana [Opinión] y con el PC aparte. Horas y costes son estimaciones [Inferencia].

| Etapa | Objetivo / qué aprende | Datos | Hardware | Software | Horas / calendario | Coste | Terminada cuando… | Riesgos |
|---|---|---|---|---|---|---|---|---|
| **0. Base segura** | Mover cuello y una ceja con límites | Ninguno | ESP32, adaptador de bus Feetech, fuente 12 V, seta + relé, fusible, 2–3 STS3215 | Arduino IDE, script Python | 30–50 h / 6–8 sem | 120–200 € | Desenchufar el PC lleva a postura segura; la seta corta todo; ninguna orden supera límites | Cableado; falta de tiempo |
| **1. Memoria y preferencias** | Hechos, preferencias y diario con aprobación | Tus conversaciones | Nada nuevo | Tu app + SQLite + vectores + bandeja | 25–40 h / 4–6 sem (en paralelo a la 0) | 0–10 €/mes API | Recuerda 20 preferencias aprobadas y las olvida si se lo pides | Guardar basura |
| **2. Sentidos y atención** | Mirar a quien habla; reconocerte | Fotos tuyas con consentimiento | Cámara gran angular, ReSpeaker XVF3800, altavoz + amplificador, tapa y LED | MediaPipe, faster-whisper, Silero VAD, DoA | 40–60 h / 8–10 sem | 120–200 € | Gira hacia quien habla ≥80 % en 20 pruebas; no se oye a sí mismo | Eco, ruido, luz |
| **3. Cara completa** | Ojos, párpados, cejas, mandíbula en lista blanca | Ninguno | 6–9 micro servos de bus, piezas impresas | Habilidades con parámetros recortados | 60–100 h / 12–16 sem | 150–300 € | 10 expresiones y parpadeo sin pellizcos | Mecánica pequeña |
| **4. Aprende su cuerpo** | Autocalibrar mirada; modelo directo; detectar fallos | Miles de movimientos automáticos | Igual (opcional cámara en un ojo, 20–40 €) | OpenCV + regresión o red pequeña | 40–60 h / 8–10 sem | 0–40 € | Mira a un punto señalado con error pequeño tras calibrarse sola | Datos ruidosos |
| **5. Aprende de ti** | Rutinas, preguntas, "bien/mal", reflexión | Semanas de eventos y valoraciones | Táctiles, LD2410, luz, temperatura | Reflexión diaria, umbral, aprobación | 40–60 h / 8–12 sem | 20–40 € | ≥3 rutinas correctas aprobadas; aprende de 50 señales | Aprender cosas falsas |
| **6. Voz y labios** | Visemas desde el audio; luego aprendidos | Reglas; luego vídeo de su cara + audio | Espejo o su cámara | Rhubarb Lip Sync; luego modelo pequeño | 30–60 h / 6–12 sem | 0 € | La boca acompaña al habla sin retraso visible | Valle inquietante |
| **7. Laboratorio SO-101 (opcional)** | Imitación (ACT) y VLA (SmolVLA) | 50 episodios por tarea | SO-101 líder + seguidor, 2 cámaras | LeRobot en Windows; nube | 50–80 h / 10–14 sem | 300–400 € + 10–30 € nube | ACT ≥70 % en "cubo al cuenco" | Calibración, luz |
| **8. Cuerpo o piernas (futuro)** | Locomoción con RL y sim2real | Millones de pasos simulados | Servos grandes, IMU, batería; GPU 16 GB o nube | MuJoCo Playground o Isaac Lab | >200 h / >1 año | ≥800 € | Camina en simulación y da pasos reales con arnés | Caídas, coste |

**Total etapas 0–6** [Inferencia]: unos 410–790 € y 265–430 h (12–18 meses a 5–8 h/semana). Con la etapa 7: 750–1.250 €. Cabe en 900–2.500 € con margen para errores y reimpresiones.

---

## Decisiones que tienes que tomar tú

**En pocas palabras:** Son tuyas; aquí tienes opciones, pros y contras y cuándo decidir.

| Decisión | Opciones | Pros / contras | Qué necesitas saber | Cuándo |
|---|---|---|---|---|
| **PC o GPU** | A + nube; B (12 GB usada); C (16–24 GB) | A: barato, depende de internet. B: equilibrio. C: autonomía, ≥800 € ⚡ | Presupuesto real; otros usos del PC | Antes de la etapa 4 |
| **Nube o local** | Todo local; mixto; todo nube | Local: privado, más lento. Nube: potente, cuesta y saca datos | Qué datos aceptas que salgan | Etapa 1 |
| **Dónde va la cámara** | Frente fija; ojos; ambas | Frente: fácil. Ojos: mirada real, difícil | Tu diseño de la cara | Antes de diseñar el cráneo |
| **Tipo de servos** | Feetech STS/SCS; Dynamixel; PWM | Feetech: buena relación. Dynamixel: mejor y caro. PWM: no aprende | Presupuesto y tamaño | Etapa 0 |
| **Añadir SO-101** | Tras la etapa 5; ya; no | Imitación real / distracción | Si te interesa manipular | Al acabar la etapa 5 |
| **Qué recuerda y de quién** | Solo tú; familia con permiso; también visitas | Más memoria = más útil y más riesgo | Quién vive contigo y qué opina | Etapa 1 |
| **Horas por semana** | 3–5; 5–8; >8 | Más horas = antes, riesgo de quemarte | Tus turnos | Ya |
| **Estética de la cara** | Realista; dibujo animado; mecánica a la vista | Realista = valle inquietante; dibujo = más amable | Tu gusto | Antes de la etapa 3 |
| **Voz de Sirius** | Local (Piper); nube; clonada con permiso | Local: privada. Nube: más natural | Gusto y presupuesto | Etapa 2 |
| **Comprar Reachy Mini** | No (solo referencia); sí, la Lite | Probar ya / ~500 € | Si quieres resultados mientras imprimes | Etapas 0–2 |

---

## Recordatorio de lo más importante

1. **Seguridad primero:** servos con límites, ESP32 que recorta y vigila, y seta que corta la corriente. La IA solo elige habilidades.
2. **Lo que más rinde:** memoria con aprobación, atención (voz + caras) y autocalibración del cuerpo.
3. **"Aprender viendo vídeos" sí sirve para una cara** (Columbia, enero de 2026), pero primero el robot se mira a sí mismo.
4. **VLA e imitación son para brazos:** si te interesan, un SO-101 aparte.
5. **Cámara fija en la frente, ReSpeaker en la coronilla, altavoz abajo.**
6. **Windows para controlar, nube para entrenar.** No compres una GPU de 16 GB en 2026 solo por esto.
7. **Nada cambia sin tu "sí",** y todo se puede olvidar.
8. **Calendario realista:** 12–18 meses a 5–8 h/semana.

---

## Glosario sencillo

- **GPU:** tarjeta gráfica; acelera la IA haciendo muchos cálculos a la vez.
- **VRAM:** memoria de la GPU; limita el tamaño de modelo que cabe.
- **Política:** el "programa aprendido" que decide el siguiente movimiento.
- **Episodio:** una grabación completa de una tarea.
- **Teleoperación:** mover el robot a distancia para grabar demostraciones.
- **VLA:** modelo que ve, entiende órdenes y produce movimientos.
- **Fine-tuning:** reentrenar un poco un modelo ya entrenado con tus datos.
- **LoRA:** ajuste fino barato que solo entrena pequeños "parches".
- **RL:** aprender por prueba y error con premios.
- **Sim2real:** pasar lo aprendido en simulación al robot real.
- **Olvido catastrófico:** aprender algo nuevo borra lo anterior.
- **RAG:** buscar en la memoria antes de responder.
- **AEC:** cancelación de eco; quita del micrófono el sonido del propio altavoz.
- **DoA / VAD:** de dónde viene una voz / cuándo alguien habla.
- **IMU:** sensor de inclinación y movimiento. **ToF:** sensor de distancia por luz.
- **Propiocepción:** el robot "siente" posición, carga y temperatura de cada motor.
- **Watchdog o latido:** vigilante que actúa si el PC deja de dar señales.
- **Visema:** forma de la boca para un sonido.
- **WSL2:** Linux dentro de Windows. **Cuantizar:** comprimir un modelo con menos precisión.
