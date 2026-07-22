# Documento Rector — Cabeza Robótica Sirius HEAD-R1

**Identificador:** `SIRIUS-HEAD-RECTOR-R1`  
**Versión:** 1.1  
**Estado:** APROBADO  
**Fecha:** 22 de julio de 2026  
**Sustituye a:** Documento Rector v1.0 y propuesta v0.2  
**Autoridad final:** usuario responsable del Proyecto Sirius

> Representación GitHub-native, **fiel y completa**, del documento aprobado
> `artifacts/SIRIUS_DOCUMENTO_RECTOR_HEAD-R1_v1.1_APROBADO.docx` (huellas de
> integridad en `ARTIFACTS.md`). v1.1 añade la sección 7.5 (grabación de vídeo
> dirigida por Claude en cada sesión) y sustituye a v1.0 y v0.2. Este documento
> **no amplía Sirius 0.1**: HEAD-R1 es una línea de producto físico separada.

> ESTADO: Este documento es la base activa del proyecto. Define qué se construye y cómo. Cada fase se activa cuando el usuario da el visto bueno, con su lista de compras y su prueba para pasar. La autoridad final es siempre del usuario.

---

## 1. Qué es HEAD-R1 (en una página)

HEAD-R1 es la primera cabeza robótica de Sirius. Un objeto de sobremesa de unos 35 cm de alto con pedestal (base de apoyo), de estética claramente robótica: superficies negras y color gunmetal (gris metálico oscuro), ojos azules iluminados y mandíbula articulada.

La cabeza se mueve, mira, parpadea, mueve las cejas, abre la boca y habla con voz que sale de ella misma. No pretende parecer humana: es un robot con carácter y expresividad, siguiendo la imagen de referencia del proyecto.

El proyecto lo hace UNA sola persona, sin experiencia previa, guiada paso a paso por una IA (Claude). El objetivo no es solo la cabeza terminada: es aprender por el camino mecánica, electrónica, diseño 3D y fabricación, con un método seguro y ordenado.

Datos clave:

Presupuesto total orientativo: entre 900 y 2.500 €, repartido por fases (no se gasta todo de golpe).

Plazo realista: entre 12 y 30 meses trabajando a tiempo parcial. Es normal que sea largo.

Regla de oro: un solo frente de trabajo físico a la vez. No se abren dos montajes en paralelo.

La cabeza funciona conectada por cable al ordenador y a la corriente. Sin baterías. Siempre con alguien delante.

## 2. Qué lleva y qué no (alcance)

### 2.1 Lo que SÍ lleva HEAD-R1

| Función | Qué significa |
| --- | --- |
| Cuello: girar | La cabeza gira a izquierda y derecha (como decir "no"). |
| Cuello: inclinar | La cabeza mira arriba y abajo (como decir "sí"). |
| Ojos: horizontal | Los dos ojos miran juntos a izquierda y derecha. |
| Ojos: vertical | Los dos ojos miran juntos arriba y abajo. |
| Párpados | Se abren, se cierran y parpadean, los dos a la vez. |
| Cejas | Dos piezas visibles que suben y bajan juntas para dar expresión. |
| Mandíbula | La pieza de la boca se abre y se cierra. |
| Voz | El sonido sale de un altavoz dentro de la propia cabeza. |
| Boca al hablar | La mandíbula se mueve de forma creíble mientras habla (sin sincronizar letra a letra). |
| Ojos iluminados | Luz azul uniforme y suave en ambos ojos, sin puntos de luz molestos. |

### 2.2 Lo que NO lleva (queda para más adelante)

Sonrisa mecánica: se pospone a la versión R2. Es de lo más difícil de la animatrónica y no compensa en la primera versión.

Cámaras, visión ni reconocimiento de nada.

Micrófonos ni escucha.

Ojos, párpados o cejas moviéndose por separado (nada de guiños).

Inclinar la cabeza de lado (gesto de perrito curioso).

Baterías, funcionamiento sin cables o sin supervisión.

Cuerpo, torso, brazos o base con ruedas.

### 2.3 Decisión sobre los ojos

Los ojos se diseñan A MEDIDA, desde cero, para conseguir la expresividad de la imagen de referencia de Sirius. No se usan mecanismos de terceros ya publicados. Es el reto técnico más grande de R1 y llevará varias versiones de prueba: se asume y se acepta.

### 2.4 Reservas para el futuro

Sin instalar nada ahora, el diseño dejará hueco y paso de cables para: una futura cámara en un ojo, futuros micrófonos (separados del altavoz) y la futura sonrisa de R2. Reservar hueco no obliga a instalarlo.

## 3. Estética y medidas

### 3.1 Identidad visual

Apariencia robótica, no humana realista.

Colores: negro y gunmetal, con toques metálicos limitados.

Tornillos, placas y mecanismos a la vista cuando den carácter y faciliten el acceso.

Ojos azules como sello de identidad. Mandíbula con dientes estéticos.

La imagen de referencia marca la dirección, no las medidas exactas de fabricación.

### 3.2 Medidas

| Medida | Valor |
| --- | --- |
| Altura total objetivo | 35 cm (cabeza + cuello + pedestal) |
| Altura total máxima | 39 cm. Límite absoluto, no se pasa. |
| Cabeza (orientativo) | 19-20 cm alto · 16-17 cm ancho · 17-19 cm fondo |
| Peso de la parte que se mueve | Objetivo 1,3-1,8 kg (máximo 2,2 kg) |
| Peso total con pedestal | 3,5-5 kg (el pedestal pesa a propósito, para que no vuelque) |

Las medidas orientativas se confirman con la maqueta y con las piezas reales en la mano. Regla práctica: cuanto menos pese lo que se mueve, más fácil, barato y seguro es todo.

### 3.3 Prioridades cuando dos cosas choquen

Si hay que elegir, este es el orden. Lo de arriba gana siempre a lo de abajo:

| Orden | Prioridad |
| --- | --- |
| 1 | Seguridad (de la persona y del aparato) |
| 2 | Que funcione bien |
| 3 | Que se pueda mantener y reparar sin romper nada |
| 4 | Tamaño y estabilidad (que no pase de 39 cm ni vuelque) |
| 5 | Robustez y duración |
| 6 | Parecido con la imagen de referencia |
| 7 | Coste |
| 8 | Refinamiento estético final |

## 4. Las fases, una a una

El proyecto avanza por fases. Cada fase tiene un objetivo y una "prueba para pasar": hasta que la prueba no sale bien, no se pasa a la siguiente. Volver atrás no es fracasar; es lo normal cuando una prueba enseña algo nuevo.

> REGLA: cada fase se activa con el visto bueno del usuario, y solo entonces se compran sus materiales. Un solo frente físico abierto a la vez.

### F0 · Preparación (1-3 semanas, en paralelo con F1)

Objetivo: dejar todo listo para empezar. Subir este documento al Proyecto de Claude, crear cuenta en Tinkercad (programa de diseño 3D para principiantes, gratis y en español) y practicar 2-3 semanas modelando piezas sencillas. Después, pasar a Onshape (diseño 3D más serio, gratis, por navegador y en español).

Prueba para pasar: haber modelado en Tinkercad una pieza simple inventada (una caja con agujeros, un soporte) y saber exportarla.

### F1 · Primer servo que se mueve (semanas 1-2)

Objetivo: ver movimiento cuanto antes para coger moral. Con un kit pequeño y barato, conectar un micro-servo (motor pequeño que se mueve al ángulo que le pidas) a una placa y moverlo desde el ordenador. Montar ya, desde el primer día, un interruptor de corte físico (botón que quita la corriente a los motores pase lo que pase).

Prueba para pasar: mover el servo a 3 posiciones distintas a voluntad, y pararlo en seco con el interruptor de corte mientras se mueve.

### F2 · Maqueta de escala (2-4 semanas)

Objetivo: hacer una maqueta de cartón o espuma con las medidas reales (35 cm) para ver el tamaño de verdad encima de la mesa, decidir proporciones y comprobar que no molesta ni vuelca. No es glamurosa, pero evita imprimir piezas equivocadas durante meses. Se hace y punto.

Prueba para pasar: maqueta terminada sobre la mesa, foto con regla al lado, y proporciones aprobadas por el usuario comparando con la imagen de referencia.

### F3 · Banco eléctrico seguro (4-8 semanas)

Objetivo: montar el "banco de pruebas": fuente de alimentación (aparato que convierte el enchufe en corriente segura de baja tensión), fusible (pieza que se funde y corta la corriente si algo falla), interruptor de corte, y un servo inteligente Feetech STS3215 (motor con sensores que informa de su posición, esfuerzo y temperatura) controlado desde el ordenador, con límites de movimiento puestos por software.

Prueba para pasar: mover el STS3215 con límites que no se puedan saltar, leer en pantalla su posición y temperatura, y provocar una parada segura (quitar la comunicación y comprobar que el motor no se queda empujando).

### F4 · Ojos a medida (3-6 meses, la fase más dura)

Objetivo: diseñar e imprimir en 3D el mecanismo propio de ojos: dos ojos que miran juntos en horizontal y vertical, suaves y sin rozar. Aquí llega la impresora 3D. Habrá varias versiones fallidas: forma parte del plan.

Prueba para pasar: ojos moviéndose en las dos direcciones con suavidad, sin rozar ni vibrar, funcionando 15 minutos seguidos sin que ningún servo se caliente en exceso.

### F5 · Párpados y cejas (1-3 meses)

Objetivo: añadir al módulo de ojos los párpados (abrir, cerrar, parpadear) y las dos cejas con movimiento conjunto, sin chocar con los ojos.

Prueba para pasar: parpadeo natural con los ojos en cualquier posición, cejas arriba/abajo, y todo junto sin rozamientos, 15 minutos seguidos.

### F6 · Mandíbula (1-2 meses)

Objetivo: mandíbula articulada sobre dos pivotes laterales (puntos de giro), movida por un servo inteligente, desmontable sin tocar los ojos.

Prueba para pasar: abrir y cerrar con suavidad 200 ciclos seguidos, sin holguras raras ni ruidos que vayan a más.

### F7 · Cuello y pedestal (2-3 meses)

Objetivo: construir el cuello (girar + inclinar) con servos inteligentes y el pedestal con su peso de lastre. Se prueba primero con una "masa falsa": un peso equivalente al de la cabeza (unos 2 kg), nunca con la cabeza buena. Los cables pasan por dentro con holgura y protección.

Prueba para pasar: mover la masa falsa por todo el recorrido sin que el conjunto vuelque, sin que los cables se pellizquen y sin que los servos se calienten en exceso.

### F8 · Integración: cabeza abierta (2-3 meses)

Objetivo: juntar todos los módulos sobre el esqueleto interno, sin carcasa, y hacer que convivan: ojos + párpados + cejas + mandíbula + cuello a la vez.

Prueba para pasar: una secuencia combinada (mirar, parpadear, mover cejas, abrir boca, girar cabeza) repetida 10 veces sin fallos ni choques.

### F9 · Audio e iluminación (1-2 meses)

Objetivo: altavoz fijado al esqueleto (nunca a la mandíbula), voz clara a distancia normal de uso, mandíbula moviéndose de forma creíble al hablar, y luz azul uniforme en los ojos con difusor (pieza que reparte la luz para que no se vean puntos).

Prueba para pasar: la cabeza habla y se le entiende a 2 metros, la boca acompaña de forma creíble, la luz azul es uniforme, y nada vibra de forma molesta.

### F10 · Carcasa y acabado (2-4 meses)

Objetivo: diseñar e imprimir la carcasa definitiva con la estética Sirius (negro/gunmetal), desmontable con tornillos, sin perder acceso para reparar ni empeorar la temperatura.

Prueba para pasar: con la carcasa puesta, todo sigue funcionando igual de bien, se puede quitar la cara frontal con herramientas normales, y el conjunto pasa la comparación visual con la imagen de referencia (con las diferencias aceptadas apuntadas).

### F11 · Validación final y cierre de R1 (1 mes)

Objetivo: campaña final de pruebas: encendidos repetidos desde cero, todos los movimientos al límite, sesión larga de uso, corte físico en marcha, quitar y volver a poner un módulo, y guardar una copia de seguridad completa de programas y configuraciones que se sepa que funciona.

Prueba para pasar: todo lo anterior superado y documentado. Se congela la versión: HEAD-R1 terminada. Las mejoras nuevas (sonrisa incluida) van a la lista de R2.

## 5. Lista de compras por fase (precios orientativos)

Regla de compras: solo se compra lo que hace falta para la fase activa, con el visto bueno del usuario. Los precios son orientativos (España/Europa, 2026) y se verifican justo antes de comprar. Cada compra se apunta en el registro de compras.

| Fase | Qué comprar | Precio aprox. | Acumulado |
| --- | --- | --- | --- |
| F1 | Kit de inicio: 1-2 micro-servos, placa controladora (ESP32 o similar), protoboard (placa de pruebas sin soldar), cables, interruptor de corte, alimentación pequeña | 40-70 € | ~70 € |
| F2 | Cartón pluma, cúter, regla metálica, pegamento, cinta | 15-25 € | ~95 € |
| F3 | Fuente de alimentación 12 V (5-10 A), 2× servo Feetech STS3215, adaptador de bus (conecta los servos al ordenador), fusibles y portafusibles, multímetro (aparato para medir corriente y voltaje), calibre digital (para medir piezas con precisión), cables y conectores | 180-250 € | ~350 € |
| F4 | Impresora 3D (herramienta permanente; gama Bambu Lab A1/P1S o similar), filamento PLA y PETG (los plásticos de impresión), 4-6 micro-servos para ojos, tornillería fina, varillas y rodamientos pequeños | 400-800 € | ~1.150 € |
| F5 | 2-3 micro-servos más, filamento, tornillería | 30-60 € | ~1.200 € |
| F6 | 1× STS3215 (si no está ya), pivotes, casquillos, muelles suaves | 40-70 € | ~1.270 € |
| F7 | 2× STS3215 (versión 12 V con más fuerza), rodamientos, material del pedestal, lastre (peso), pasacables | 90-150 € | ~1.420 € |
| F8 | Cableado fino, fundas, bridas, conectores etiquetables | 20-40 € | ~1.460 € |
| F9 | Altavoz pequeño + amplificador, tira LED azul + difusores | 35-65 € | ~1.520 € |
| F10 | Filamento de carcasa, lijas, imprimación y pintura gunmetal | 50-100 € | ~1.620 € |
| Extra | Reserva para errores, repeticiones e imprevistos (30-50%) | 300-900 € | 900-2.500 € |

Notas:

El total queda dentro del rango aprobado de 900-2.500 €. El extremo bajo supone impresora económica y pocas repeticiones; el alto, impresora mejor y más iteraciones.

La impresora 3D es herramienta permanente: se amortiza porque este proyecto necesita imprimir y corregir piezas constantemente.

No se compra soldador hasta que la protoboard y los conectores se queden cortos. No se compran servos en cantidad hasta validar los primeros.

## 6. Seguridad práctica

Todo el montaje funciona a baja tensión (12 V como máximo): la corriente del enchufe (230 V) nunca entra en el robot, solo llega a la fuente de alimentación, que es un aparato cerrado y comercial. Aun así, hay reglas de oro:

El interruptor de corte físico siempre montado, probado y al alcance de la mano. Es sagrado: existe desde la fase F1 hasta el final.

Si un mecanismo no se mueve suave con la mano, no se le pone motor para forzarlo. Primero se arregla el roce.

Al encender: primero el ordenador y la lógica con los motores cortados; solo se da corriente a los motores cuando todo está comprobado. Al apagar: posición segura y luego cortar.

Manos fuera de la zona de movimiento cuando los motores tienen corriente.

Si algo huele raro, quema al tocarlo, echa humo o hace un zumbido nuevo: cortar corriente y parar. Se investiga con calma, sin corriente.

Comprobar la polaridad (el + y el −) antes de conectar cualquier cosa. Un cable al revés puede quemar una placa.

Herramientas: pieza bien sujeta, gafas al cortar o lijar, ventilar al pintar.

Cansado o frustrado = parar. Parar es parte del método, no una derrota. Con sueño se cometen los errores caros.

Cualquier susto o casi-accidente se apunta en el registro de incidentes, aunque no haya pasado nada. Sirve para que no se repita.

## 7. Cómo trabajamos en cada sesión

### 7.1 Reparto de papeles

| Claude (la IA) | Usuario |
| --- | --- |
| Prepara el objetivo del día, los pasos y la seguridad | Ejecuta con las manos: monta, imprime, conecta |
| Explica cada cosa en sencillo y dice el porqué | Observa: roces, ruidos, calor, olores |
| Revisa fotos y capturas y diagnostica | Hace fotos y vídeos de lo importante |
| Guía dentro del CAD paso a paso (menú, botón, operación) | Mide con calibre y cuenta lo que ve, sin adornar |
| Al cierre, resume y deja apuntado el siguiente paso | Decide, aprueba compras y para si hay riesgo |

### 7.2 Inicio de sesión (se dicta por voz, 1 minuto)

"Claude, empezamos sesión. Lee el estado. Estoy en la fase [X]. Hoy quiero [objetivo]. Dime el plan en pasos, qué necesito tener a mano y qué NO hay que hacer hoy."

### 7.3 Cierre de sesión (1 minuto)

"Cerramos sesión. Resume qué hemos hecho, qué ha fallado, qué queda pendiente de verificar, y dame el texto para actualizar el estado y el siguiente paso exacto."

### 7.4 Costumbres que ahorran disgustos

Fotos: antes de tocar nada, cuando algo falla, y al terminar. Nombres cortos de archivo.

Una variable cada vez: si cambias dos cosas a la vez y mejora, no sabrás cuál fue.

Dimensiones, fuerzas y conexiones que diga la IA: se verifican siempre contra la hoja del fabricante o midiendo. La IA ayuda, pero no se le cree a ciegas en números críticos.

Al acabar, la mesa queda en "estado seguro": sin corriente, mecanismos relajados, piezas y tornillos guardados juntos y etiquetados.

### 7.5 Grabar vídeo de las sesiones (para futuros vídeos)

El usuario quiere documentar el proceso en vídeo para internet (canal de construcción, "build log"). No hay obligación de publicar nada: se graba primero y se decide después qué usar. Los fallos también se graban: suelen ser el contenido que más conecta.

Como el usuario no siempre sabrá identificar el momento importante, esta tarea la dirige Claude: al empezar cada sesión ("Claude, empezamos sesión"), además del plan del día, Claude añadirá una línea "Qué grabar hoy" con el plano y el momento exactos para la tarea de ese día (por ejemplo: "plano general al montar, primer plano al conectar el servo, vídeo del movimiento, y si algo falla, grábalo tal cual").

Momentos mínimos por sesión: apertura (plano general), justo antes de un cambio, el momento de la prueba, el fallo si lo hay, y el cierre.

Nombres de archivo cortos y simples: por ejemplo S014_servo-cuello.mp4. No hace falta ningún sistema de etiquetas complicado.

Antes de publicar cualquier cosa: revisar que no salgan credenciales, pantallas, documentos o datos privados de fondo.

## 8. Los 4 registros y las plantillas

Toda la burocracia del proyecto se reduce a 4 registros (4 archivos o 4 secciones de un mismo archivo) y una plantilla de sesión de una página. Nada más. Los códigos de identificación son solo 4:

| Código | Para qué |
| --- | --- |
| DEC-### | Decisiones importantes (qué se decidió, cuándo y por qué). Ej.: DEC-001. |
| COMP-### | Compras (qué, cuánto costó, para qué fase, resultado al probarlo). |
| TEST-### | Pruebas (qué se probó, cómo salió, con qué evidencia en foto/vídeo). |
| INC-### | Incidentes y sustos (qué pasó, causa probable, qué se cambia para que no se repita). |

Además existe un documento aparte, HEAD_STATUS, de UNA página, que dice en todo momento: fase activa, último avance, siguiente paso exacto, compras autorizadas y estado del montaje. Es lo primero que se lee en cada sesión.

### 8.1 Plantilla de sesión (una página)

| Campo | Contenido |
| --- | --- |
| Sesión nº y fecha |  |
| Fase y objetivo de hoy |  |
| Qué NO tocar hoy |  |
| Seguridad / cuándo parar |  |
| Qué grabar hoy (lo indica Claude) |  |
| Qué ha pasado (resultado) |  |
| Fallos o sorpresas |  |
| Fotos/vídeos guardados |  |
| Estado seguro al terminar | Sí / No + nota |
| Siguiente paso exacto |  |

### 8.2 Plantilla de prueba (media página)

| Campo | Contenido |
| --- | --- |
| TEST-### y fecha |  |
| Qué se prueba y por qué |  |
| Cómo se prueba (pasos) |  |
| Resultado esperado |  |
| Resultado real y medidas |  |
| Evidencia (foto/vídeo) |  |
| Veredicto | Superada / repetir / rediseñar |

## Anexo · Vocabulario en cristiano

| Palabra | Qué significa |
| --- | --- |
| Servo | Motor pequeño que se mueve exactamente al ángulo que le pides y se queda ahí. Es el músculo del robot. |
| Servo inteligente | Servo con sensores que además te informa: en qué posición está, cuánto esfuerzo hace y qué temperatura tiene. Ej.: Feetech STS3215. |
| Torque (par) | La fuerza de giro de un motor. Se mide en kg·cm: cuántos kilos puede sostener a 1 cm del eje. Más torque = más fuerza (y más precio). |
| GDL (grados de libertad) | Cuántos movimientos independientes tiene algo. El cuello de HEAD-R1 tiene 2 GDL: girar e inclinar. |
| PWM | La "señal de radio" clásica con la que se manda a un servo normal a qué ángulo ir. Los servos inteligentes usan otra cosa mejor: el bus serie. |
| Bus serie | Un cable de datos compartido: varios servos inteligentes encadenados en el mismo cable, cada uno con su número, hablando con el ordenador. |
| Encoder | El sensor interno que sabe en qué posición exacta está el eje del servo. |
| Holgura (backlash) | El pequeño juego o baile que tiene un mecanismo antes de moverse de verdad. Poca holgura = movimiento fino y preciso. |
| Neutral | La posición de reposo o centro de un movimiento. Los servos se centran en su neutral antes de montarlos. |
| Calibrar | Ajustar y apuntar los valores reales de cada servo: su centro, sus límites y su sentido de giro. |
| Fuente de alimentación | Aparato que convierte los 230 V del enchufe en corriente segura de baja tensión (12 V) para el robot. |
| Fusible | Pieza barata que se sacrifica: si pasa demasiada corriente, se funde y corta el circuito antes de que se queme algo caro. |
| Protoboard | Placa de pruebas con agujeritos donde se pinchan cables y componentes sin soldar. Para experimentar y cambiar cosas fácil. |
| Corte físico | Interruptor real que quita la corriente a los motores pase lo que pase, aunque el software se vuelva loco. Siempre al alcance. |
| Masa falsa | Un peso equivalente al de la cabeza (unos 2 kg) que se usa para probar el cuello sin arriesgar la cabeza buena. |
| CAD | Programa de diseño 3D en el ordenador (Tinkercad para empezar, Onshape después). Ahí se dibujan las piezas antes de imprimirlas. |
| STL | El tipo de archivo que sale del CAD y entra en la impresora 3D. Es la pieza "lista para imprimir". |
| PLA / PETG | Los dos plásticos de impresión 3D del proyecto. PLA: fácil, para prototipos. PETG: más resistente, para piezas definitivas. |
| Filamento | El "hilo" de plástico en bobina que come la impresora 3D. |
| Lastre | Peso que se pone a propósito en el pedestal para que la cabeza no vuelque al moverse. |
| Pivote | Punto de giro de una pieza, como la bisagra de una puerta. La mandíbula gira sobre dos pivotes laterales. |
| Difusor | Pieza translúcida que reparte la luz de los LED para que el ojo se vea iluminado uniforme, sin puntitos. |

---

> FIN DEL DOCUMENTO · SIRIUS HEAD-R1 · Documento Rector v1.1 · APROBADO
