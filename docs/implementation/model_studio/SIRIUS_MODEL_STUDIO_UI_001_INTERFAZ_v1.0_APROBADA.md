# SIRIUS · MODEL STUDIO

## INTERFAZ AUDIOVISUAL v1

**Documento:** SIRIUS-MODEL-STUDIO-UI-001  
**Versión:** 1.0  
**Estado:** APROBADO COMO DIRECCIÓN DE DISEÑO  
**Fecha:** 7 de agosto de 2026  
**Alcance:** Interfaz v1 de presencia, conversación, voz y control de captura  
**Relación:** Model Studio — Módulo Voz (#126) + Módulo Captura (#127)

## Objetivo

Definir una interfaz propia, reconocible y grabable para que Sirius pueda aparecer en pantalla sin mostrar la interfaz técnica actual. La solución se integra en la aplicación existente y preserva conversación, memoria, contexto y casos de uso.

> **Alcance de esta aprobación**  
> Este documento aprueba la dirección de diseño y los requisitos visibles de la interfaz. No declara que la interfaz, la animación, la voz, las cámaras o la grabación estén implementadas.

> ## Este documento está modificado en dos puntos. Léelos antes que nada.
>
> Se escribió el 7 de agosto de 2026 y su dirección de diseño sigue vigente entera. Dos cosas dejaron de ser ciertas ese mismo día y la siguiente semana, y quedan aquí dichas para que nadie lea como vigente lo que ya no lo es.
>
> **1. La presencia visual la redefinió el propio usuario.** La sección 3 describe «dos ojos y una boca sugeridos por agrupaciones de puntos más densas» y una «composición facial». Lo aprobado y construido es otra cosa: **una entidad digital abstracta y geométrica, no un rostro**. Ojos robóticos que parpadean y cambian de tamaño de forma sutil e irregular, boca de barras verticales tipo ecualizador, y cuatro marcas de esquina que la encuadran como interfaz. Sin sincronización labial y sin análisis de audio: la agitación nace de un pulso constante. Todo lo demás de la sección 3 —fondo negro, paleta azul, espacio negativo, prohibición de contorno de cabeza y de logotipo— se mantiene tal cual.
>
> **2. La ejecución no siguió el orden que este documento supone.** La sección de puesta en marcha describe una secuencia que se reordenó en tres etapas —E1 concha grabable, E2 voz, E3 captura— y todas están entregadas y verificadas contra OBS Studio 32.2.1 en Windows.
>
> **Dónde está lo vigente.** `docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_RECONCILIACION_v1.0_PROPUESTA.md` recoge las once decisiones que reconcilian este documento con #126 y #127, cuáles se implementaron y cuáles no. Ante cualquier contradicción entre aquel documento y este, **manda aquel**.
>
> Lo que este documento sigue gobernando sin cambios: la composición de la superficie, la conversación compartida con la interfaz técnica, la caja única de entrada, la barra de iconos, los estados separados de interacción y captura, la parada de emergencia siempre accesible, el aislamiento de fallos y los doce criterios de aceptación.

## 1. Referencia visual provisional

El mockup conversado fija la composición general. La presencia abstracta de puntos, la proporción de columnas y los elementos visuales se refinarán mediante prototipo, pero no deben sustituirse por una interfaz técnica genérica.

> **Corrección visual final incorporada**  
> La zona izquierda no mostrará la cabeza física de Sirius ni una silueta completa. Contendrá un campo de partículas azules, pequeño y minimalista, con solo dos ojos y una boca sugeridos por una mayor densidad de puntos.

El mockup es una referencia de composición, no una captura de implementación.

## 2. Propósito y estructura general

Model Studio será una superficie audiovisual integrada dentro de Sirius. Su finalidad inicial es permitir conversación, órdenes de voz, respuestas habladas y una presentación limpia para grabar el desarrollo de HEAD-R1.

- No será una segunda aplicación independiente.
- No sustituirá la interfaz técnica actual de memoria, decisiones, configuración y copias de seguridad.
- Tendrá un modo limpio para aparecer en vídeo y un modo de control para grabación, escenas y cámaras.
- La conversación, la voz y la interfaz utilizarán los mismos casos de uso y comandos internos.

### 2.1 Distribución principal

- Columna izquierda: aproximadamente 25–30 % del ancho útil.
- Zona derecha: aproximadamente 70–75 % del ancho útil.
- Barra superior: identidad, proyecto y estados.
- Zona inferior derecha: entrada expandible para texto y transcripción.
- Barra inferior: controles por iconos con nombre accesible y tooltip.
- Zona inferior izquierda: proyecto activo, contexto y notas rápidas.

> **Regla de estabilidad visual**  
> Durante la iteración no se cambiará toda la interfaz para corregir un único elemento. Las revisiones deben ser localizadas y conservar los componentes ya aprobados.

## 3. Presencia visual abstracta de partículas

**Decisión final:** la representación no intentará reproducir la cabeza física de Sirius. Será una presencia gráfica abstracta, ligera y animable.

### 3.1 Composición

- Fondo completamente negro o casi negro.
- Campo de muchos puntos distribuidos con baja densidad alrededor del centro.
- Paleta limitada a azules: azul oscuro, azul medio y azul claro.
- Sin contorno de cabeza, sin orejas, sin nariz, sin mandíbula, sin cuello y sin base.
- Solo dos ojos y una boca sugeridos por agrupaciones de puntos más densas.
- La composición facial será pequeña, centrada y con abundante espacio negativo.
- No se añadirá un símbolo, logotipo o estrella en la frente ni alrededor de la presencia.

### 3.2 Ojos

- Dos concentraciones circulares o elípticas de puntos.
- Más brillantes que el campo de fondo, pero sin convertirse en elementos sólidos.
- Pueden pulsar suavemente al escuchar, pensar o responder.
- No deben parecer ojos humanos realistas ni copiar literalmente la cámara física de HEAD-R1.

### 3.3 Boca

- Línea o pequeña curva de puntos bajo los ojos.
- Claramente visible, aunque más discreta que los ojos.
- Puede variar ligeramente de anchura, altura o densidad mientras Sirius habla.
- No requiere sincronización labial fonema por fonema.
- No mostrará dientes, labios humanos ni una mandíbula completa.

### 3.4 Movimiento

- **En reposo:** deriva lenta y casi imperceptible de partículas.
- **Escuchando:** leve concentración o pulsación alrededor de los ojos.
- **Pensando:** redistribución suave de puntos, sin formar una cabeza.
- **Hablando:** movimiento mínimo de la boca y respiración visual del conjunto.
- **Error:** reducción de estabilidad o brillo, sin destellos agresivos.

## 4. Zona de conversación

La zona derecha se comportará como un chat de escritorio moderno. Debe ser cómoda para trabajar y presentable al grabar pantalla.

- Mensajes con tipografía de tamaño normal para escritorio; se descartan textos gigantes.
- Solo aparecerán las etiquetas `TÚ` y `SIRIUS`.
- No habrá avatares, iconos de persona, estrellas ni símbolos decorativos junto a los mensajes.
- No habrá un panel separado llamado `Transcripción`.
- El historial tendrá desplazamiento vertical y conservará legibilidad en 1080p.
- La respuesta en streaming crecerá sin superponerse ni desplazar elementos esenciales.
- Errores, acciones y resultados aparecerán como texto claro, no como lenguaje técnico interno.

### 4.1 Comportamiento oral de las respuestas

- **Órdenes simples:** confirmación hablada corta y clara.
- **Preguntas conversacionales:** respuesta completa hablada cuando tenga una longitud razonable.
- **Explicaciones largas:** resumen oral útil, contenido completo en pantalla y opción `Leer todo`.
- **Acciones críticas o fallos:** información precisa, con humor reducido o desactivado.

> **Principio de personalidad**  
> Primero debe quedar claro qué ocurrió o cuál es la respuesta. Después puede aparecer humor seco, sarcasmo, provocación contextual o un insulto de confianza permitido.

## 5. Entrada escrita y transcripción

- Existirá una única caja inferior con el texto `Escribe o habla con Sirius…`.
- La misma caja recibirá texto escrito y la transcripción del audio.
- La caja crecerá automáticamente hasta una altura máxima razonable.
- Al alcanzar esa altura, tendrá desplazamiento interno sin invadir el historial.
- La transcripción será editable antes de enviarse.
- Cancelar una transcripción no creará un mensaje ni persistirá el contenido como enviado.
- El botón de micrófono permanecerá dentro o junto a la caja de entrada.
- El botón de enviar será visible, convencional y sin iconografía inventada.

### 5.1 Flujo de voz

1. El usuario inicia una captura visible mediante el control de micrófono.
2. Sirius muestra el estado `ESCUCHANDO`.
3. El audio se transcribe y el resultado aparece en la caja de entrada.
4. El usuario puede corregir, cancelar, volver a grabar o enviar.
5. Solo al enviar se incorpora el texto a la conversación y se ejecuta la solicitud.

## 6. Controles por iconos

Los controles principales no aparecerán como botones grandes llenos de texto. Se utilizarán iconos convencionales con tooltip, nombre accesible, estado visual y atajo cuando proceda.

- Micrófono / hablar.
- Enviar.
- Cancelar operación.
- Detener voz.
- Silenciar o reactivar salida hablada.
- Repetir última respuesta.
- Leer todo.
- Pantalla completa o modo limpio.
- Ajustes rápidos de Model Studio.
- Acceso a captura, grabación y cámaras.

### 6.1 Grabación, escenas y cámaras

- Forman parte de Model Studio, pero no saturarán la barra principal.
- El control principal de captura abrirá un panel compacto o desplegable.
- La interfaz reservará desde v1 espacio para iniciar, pausar, reanudar, detener y realizar una parada de emergencia.
- Permitirá consultar y cambiar escenas autorizadas.
- Mostrará la fuente o cámara activa, una fuente perdida y el estado incierto.
- No fijará visualmente un número máximo de cámaras.
- La tecnología concreta del backend de captura permanece pendiente de verificación técnica.

> **Autoridad del estado de grabación**  
> El indicador `GRABANDO` solo puede aparecer cuando el backend de captura confirme el estado real. El modelo no puede inventar ni asumir que una grabación ha comenzado o terminado.

## 7. Zona auxiliar izquierda

- Proyecto activo.
- Contexto activo de la sesión.
- Notas rápidas.
- Acceso posterior a escena, sesión o marcas de grabación cuando el módulo de captura se conecte.
- La zona podrá plegarse u ocultarse en modo grabación limpia.
- No mostrará toda la memoria, decisiones, presupuestos, copias de seguridad o configuración general.

## 8. Barra superior y estados

- Nombre `SIRIUS`.
- Proyecto activo, por ejemplo `HEAD-R1`.
- Estado de interacción.
- Estado separado de captura.
- Controles estándar de ventana.
- Sin símbolos decorativos ajenos a una función concreta.

| Ámbito | Estado | Comportamiento visual |
|---|---|---|
| Interacción | `PREPARADO` | Partículas en reposo y controles disponibles. |
| Interacción | `ESCUCHANDO` | Pulso suave en los ojos; captura visible. |
| Interacción | `TRANSCRIBIENDO` | Entrada bloqueada temporalmente y estado claro. |
| Interacción | `REVISANDO` | Transcripción editable antes del envío. |
| Interacción | `PENSANDO` | Movimiento suave del campo de puntos. |
| Interacción | `EJECUTANDO` | Estado de acción independiente de la generación textual. |
| Interacción | `HABLANDO` | Boca de puntos animada de forma mínima. |
| Interacción | `ERROR` | Mensaje claro y degradación visual no destructiva. |
| Captura | `GRABANDO` | Indicador rojo persistente, tiempo y escena si están disponibles. |
| Captura | `PAUSADO` | Estado diferenciado; no se confunde con detenido. |
| Captura | `ESTADO INCIERTO` | No se afirma éxito; se solicita reconciliación al backend. |

## 9. Modos de presentación

### 9.1 Modo grabación

- Presencia visual de puntos.
- Conversación y respuesta escrita.
- Caja de entrada.
- Estados esenciales.
- Controles mínimos y discretos.
- Indicador de grabación cuando corresponda.
- Sin paneles técnicos ni información administrativa.

### 9.2 Modo control

- Añade controles y estados de cámaras, escenas, grabación y marcas.
- Mantiene la conversación y la presencia visual.
- Utiliza los mismos comandos internos que la voz y los futuros botones físicos.

## 10. Requisitos no funcionales

- Diseño legible y equilibrado en captura 1920 × 1080.
- Animación ligera: no debe bloquear la interfaz ni degradar el chat.
- Escalado correcto al redimensionar la ventana.
- Accesibilidad: tooltips, nombres accesibles, foco visible y operación por teclado.
- Fallo aislado: un error de partículas, voz o captura no inutiliza el chat escrito.
- Sin grabación oculta ni activación automática al abrir Sirius.
- Sin audio completo, vídeo ni transcripciones completas en logs.
- Sin acceso directo de la interfaz al proveedor, secretos, base de datos o backend de captura.

## 11. Criterios de aceptación visual y funcional

1. La columna izquierda ocupa aproximadamente una cuarta parte de la ventana y no domina la composición.
2. La presencia muestra únicamente puntos, dos ojos y una boca: sin cabeza, orejas, cuello, base o dientes.
3. La paleta de la presencia usa solo azules sobre negro.
4. La boca es visible y admite una animación pequeña durante el habla.
5. Los mensajes solo identifican `TÚ` y `SIRIUS`, sin avatares.
6. El texto tiene escala de chat de escritorio y es legible en grabación.
7. No existe un panel separado de transcripción.
8. La caja de entrada recibe texto y voz, puede crecer y conserva controles accesibles.
9. Los iconos tienen función real, tooltip y estado visible; no se añaden símbolos decorativos.
10. El estado de interacción y el estado de grabación permanecen separados.
11. La parada de emergencia queda accesible durante una grabación.
12. Corregir un componente no rediseña ni sustituye el resto de la interfaz aprobada.

## 12. Fuera de alcance de la primera implementación

- Avatar 3D o rostro humano realista.
- Reproducción exacta de la cabeza física de Sirius mediante partículas.
- Sincronización labial avanzada.
- Visión artificial, reconocimiento de objetos o selección automática de planos.
- Edición, montaje, subtítulos, publicación o subida automática.
- Control general del ordenador o ejecución de comandos arbitrarios.
- Rediseño completo de la aplicación general de Sirius.

## 13. Orden recomendado de implementación

1. Construir la estructura estática de Model Studio dentro de la aplicación actual.
2. Validar proporciones y legibilidad mediante una grabación real de pantalla.
3. Implementar la presencia de partículas con estados simulados.
4. Conectar la conversación existente y el streaming de respuestas.
5. Conectar entrada escrita, captura de voz y revisión de transcripción.
6. Conectar síntesis, detener, repetir, silenciar y leer todo.
7. Integrar el módulo de captura una vez verificado el backend elegido.
8. Ejecutar pruebas de rendimiento, degradación segura y grabación real.

> **Condición de cierre del prototipo**  
> La interfaz se considerará lista para implementación funcional cuando el mockup pueda reproducirse como una pantalla estática, se vea correctamente en 1080p y el usuario confirme proporciones, tipografía, presencia visual y ubicación de controles.

## 14. Registro de decisiones consolidadas

| Decisión | Estado |
|---|---|
| La interfaz se integra en Sirius; no se crea otra aplicación. | **APROBADO** |
| La zona izquierda reduce su ancho a aproximadamente 25–30 %. | **APROBADO** |
| La presencia es abstracta: ojos y boca de puntos, sin cabeza. | **APROBADO** |
| Solo se usan tonos azules sobre negro en la presencia. | **APROBADO** |
| El chat usa escala de escritorio, sin avatares. | **APROBADO** |
| La entrada escrita y la transcripción comparten la misma caja. | **APROBADO** |
| No existe un panel separado de transcripción. | **APROBADO** |
| Los controles son iconos convencionales con tooltip. | **APROBADO** |
| Cámaras, escenas y grabación forman parte de Model Studio. | **APROBADO** |
| La tecnología concreta de captura aún requiere verificación. | **PENDIENTE TÉCNICO** |

---

Este documento registra una dirección aprobada. No autoriza por sí solo implementación, cambios canónicos fuera de Model Studio ni merge automático.
