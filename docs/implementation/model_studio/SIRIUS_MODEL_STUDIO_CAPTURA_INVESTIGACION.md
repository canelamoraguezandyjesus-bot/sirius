# SIRIUS · MODEL STUDIO · MÓDULO CAPTURA

## INVESTIGACIÓN TÉCNICA PREVIA

**Documento:** SIRIUS-MODEL-STUDIO-CAP-INV-001
**Versión:** 1.0
**Estado:** **INVESTIGACIÓN DOCUMENTAL — VERIFICADA EN LA PRÁCTICA EL 9-08-2026**
**Fecha:** 7 de agosto de 2026
**Responde a:** #127 (`SIRIUS-MODEL-STUDIO-003`), que exige *"investigación técnica breve antes de activar implementación"*

> ## Verificación realizada el 9 de agosto de 2026
>
> Este documento se escribió sin haber probado nada, y su advertencia original se conserva más abajo porque explica cómo se tomaron las decisiones. **Lo que ya no es cierto es que no haya evidencia.**
>
> Contra **OBS Studio 32.2.1 en Windows 11**, con dos escenas reales —captura de pantalla y webcam USB—, se ha comprobado: conexión y autenticación por el servidor WebSocket local en el puerto 4455, lectura de la lista de escenas, cambio de plano y vuelta al anterior, y una grabación real de tres segundos con el archivo resultante en disco. Después, las mismas órdenes desde Model Studio: `graba`, `cambia a cara` y `para`, con confirmación hablada.
>
> **Lo que la verificación corrigió:** OBS responde «recibido» y ejecuta después. Preguntar el estado en la línea siguiente devolvía el anterior, y con eso Sirius daba por fallida una grabación que sí estaba en marcha. Las órdenes que cambian el estado esperan ahora a que OBS lo confirme.
>
> **Lo que sigue sin verificarse:** varias cámaras simultáneas, el móvil como segunda cámara, sesiones largas, y la reconexión tras cerrar OBS a mitad de una grabación.
>
> ---
>
> ## Advertencia original, de cuando se redactó
>
> **No se ha probado nada.** El entorno donde se ha redactado no tiene acceso a internet ni a Windows, así que no se ha instalado ningún programa, no se ha abierto ningún puerto, no se ha conectado ninguna cámara y no se ha ejecutado ninguna llamada.
>
> Lo que sigue es conocimiento previo ordenado y una comparación razonada, **no evidencia**. #127 lo prohíbe expresamente: *"No afirmar que OBS, una API, una cámara o un protocolo funcionan sin prueba real."* Este documento respeta esa regla y por eso termina en un plan de verificación en vez de en una decisión.
>
> Cualquier cifra de este documento —versiones, puertos, precios, latencias— debe comprobarse antes de usarse. Están para orientar la búsqueda, no para citarlas como hechos.

## 1. Qué hay que resolver

#127 pide que Sirius pueda, por voz o por interfaz: consultar el estado real de la captura, iniciar, pausar, reanudar y detener una grabación, cambiar entre escenas autorizadas, marcar momentos y mostrar de forma inequívoca cuándo se está grabando.

Hay un requisito que manda sobre los demás y que descarta soluciones enteras: **el sistema de captura es la autoridad sobre `GRABANDO`/`DETENIDO`, y el modelo no puede inventar el estado.** Eso obliga a que el backend elegido sepa responder «¿estás grabando ahora mismo?» de forma fiable. No basta con poder mandarle órdenes.

## 2. Opciones consideradas

### 2.1 OBS Studio con su servidor WebSocket integrado

Es la hipótesis que #127 ya nombra. OBS es gratuito, es lo que usa de forma habitual quien graba pantalla y cámaras, e incorpora desde hace varias versiones un servidor WebSocket local que permite gobernarlo desde fuera.

**A favor**

- Cubre el contrato de comandos de #127 casi punto por punto: iniciar, parar, pausar, reanudar, cambiar de escena y **consultar el estado**, que es el requisito duro.
- Resuelve solo el problema de mezclar varias cámaras y la pantalla en una única salida grabada, que es la primera modalidad que #127 pide.
- Es local: no hace falta abrir nada a internet.
- Tiene autenticación por contraseña, así que el puerto local no queda abierto a cualquier proceso.
- Sustituirlo después no obliga a rehacer Sirius: viviría detrás del puerto de captura, igual que OpenAI vive detrás del puerto de texto.

**En contra y a verificar**

- Es **un segundo programa** que tiene que estar abierto. Si está cerrado, Model Studio debe degradar con elegancia y decirlo, nunca fingir.
- Hablar WebSocket desde Python casi con seguridad exige **una dependencia nueva**, y #126/#127 prohíben añadir dependencias sin decisión explícita. Habría que decidirlo antes, no descubrirlo a mitad.
- La API cambió de forma importante entre versiones mayores del complemento; hay que fijar versión mínima y comprobarla al conectar, no suponerla.
- Que exista un comando de pausa no garantiza que el formato de grabación elegido lo admita. #127 ya lo previó: la prueba MS-007 acepta *"o declara explícitamente que el backend no lo soporta"*.

### 2.2 Grabar desde el propio Sirius con Qt

Sirius ya usa PySide6, que trae piezas para capturar cámara y grabar.

**A favor:** sin programas de por medio, sin dependencias nuevas y con el estado de grabación conocido de primera mano, que es justo el requisito duro.

**En contra:** habría que construir desde cero la mezcla de varias fuentes, las escenas y la composición de pantalla más cámaras. Eso es rehacer un programa de estudio completo, muy por encima de lo que #127 llama una vertical acotada. Y grabar la pantalla no es su terreno.

**Lectura:** razonable si el objetivo se redujera a una sola cámara sin escenas. Para lo que pide #127, no.

### 2.3 FFmpeg como proceso lanzado por Sirius

**A favor:** enorme control sobre el archivo resultante y ninguna interfaz de por medio.

**En contra:** el cambio de escena en caliente y la mezcla de fuentes son trabajo manual y frágil. Y sobre todo, **saber si está grabando** pasa a depender de vigilar un proceso, que es exactamente la clase de estado poco fiable que #127 quiere evitar. Además, componer las órdenes desde texto abre la puerta a ejecución arbitraria, prohibida en el alcance.

### 2.4 Programas de estudio de pago

No se consideran en esta pasada. Introducen coste recurrente y dependencia comercial para un objetivo que dos opciones gratuitas parecen cubrir. Reabrir solo si las dos fallan la verificación.

## 3. Recomendación

**Verificar OBS primero**, con Qt como plan B reducido si OBS no supera las pruebas.

El motivo no es que OBS sea popular: es que es la única de las cuatro que responde de forma nativa a «¿estás grabando?», y ese es el requisito del que dependen la mitad de las pruebas MS de #127. Las demás obligarían a deducir el estado, y un estado deducido es justo lo que #127 prohíbe.

**Esta recomendación no autoriza a escribir código.** Autoriza a hacer la comprobación de la sección siguiente.

## 4. Plan de verificación

Antes de escribir una sola línea del Módulo Captura, en la máquina real del usuario. Cada punto se responde con una captura de pantalla o un archivo, no con una impresión.

| # | Qué se comprueba | Se supera si |
|---|---|---|
| V-01 | OBS instalado, con su servidor local activado y contraseña puesta | La ventana de ajustes muestra el servidor activo y el puerto |
| V-02 | Algo externo consigue conectarse y autenticarse | Una herramienta de prueba se conecta y lista las escenas |
| V-03 | Preguntar el estado devuelve la verdad | Con OBS parado dice parado; grabando, dice grabando |
| V-04 | Iniciar y detener por orden externa | Aparece un archivo y se puede reproducir |
| V-05 | Pausa y reanudación | Funciona, **o** se documenta que el formato no lo admite |
| V-06 | Cambio de escena por orden externa | La escena cambia y el archivo sigue siendo uno solo |
| V-07 | Dos ángulos físicos más la pantalla | Las tres fuentes se ven y se puede alternar entre ellas |
| V-08 | Qué hace falta en Python para hablar con OBS | Nombre y versión exactos de la dependencia, para decidirla |
| V-09 | OBS cerrado a mitad | Se detecta la caída sin afirmar éxito ni bloquear el chat |
| V-10 | Rendimiento con Sirius abierto a la vez | La conversación no se atasca mientras se graba |
| V-11 | Privacidad | Nada escucha fuera de la máquina; ningún registro guarda vídeo ni audio |
| V-12 | Empaquetado | Se decide qué pasa si el usuario no tiene OBS instalado |

**Si V-03 falla, OBS queda descartado**, por popular que sea: sin estado real no se puede cumplir #127.

## 5. Lo que el usuario tendría que tener

Sin decidir nada de esto todavía, y sin recomendar ninguna compra:

- **OBS instalado.** Gratuito.
- **Al menos dos fuentes de imagen** para la aceptación mínima de #127. Una webcam corriente y el móvil como segunda cámara suelen bastar para empezar; la captura de pantalla la da el propio programa.
- Nada más, de momento. **Ninguna compra está justificada hasta superar V-01 a V-07**, y esas se pueden hacer con lo que ya se tenga en casa.

## 6. Riesgos que conviene tener presentes

- **Un segundo programa que hay que abrir.** Si se olvida, Model Studio tiene que decirlo con claridad. Ese camino hay que construirlo desde el principio, no dejarlo para el final.
- **Dependencia nueva.** No se puede añadir sin decisión explícita del usuario. Decidirlo tras V-08.
- **Coste de contexto.** Grabar la pantalla mientras Sirius está abierto consume máquina. V-10 existe por eso.
- **Tentación de fingir.** La forma fácil de que «funcione» es que el modelo diga *«ya estoy grabando»* sin comprobarlo. Está prohibido y es la razón de que existan los estados `INICIANDO` y `DETENIENDO` en la máquina de estados unificada: cubren el momento en que la orden salió pero el backend aún no ha confirmado.

## 7. Qué no cubre este documento

- Cualquier afirmación sobre versiones, puertos, nombres de comandos o dependencias concretas: no se han comprobado.
- La elección de cámaras, protocolos de transporte o hardware.
- El diseño del `SceneRegistry` y del contrato de comandos, que ya están definidos en #127 y no se tocan aquí.
- Edición, montaje, subtítulos o publicación, fuera de alcance por decisión propia de #127.
