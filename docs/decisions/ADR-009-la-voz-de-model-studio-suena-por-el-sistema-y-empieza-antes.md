# ADR-009 — Sacar la voz de Model Studio por el reproductor del sistema y empezar a hablar antes de terminar

- Estado: PROPUESTO
- Fecha: 2026-08-12
- Aprobación: la fusión de la PR por el propietario

## Contexto y problema

La rama `claude/model-estudio-review-qpbknq` empezó como revisión de #126, #127
y #128 y terminó implementando Model Studio entero. Las decisiones de **alcance**
—las once R-01 a R-11— viven en
`docs/implementation/model_studio/SIRIUS_MODEL_STUDIO_RECONCILIACION_v1.0_PROPUESTA.md`,
se publicaron antes de implementar y están aprobadas por el propietario.

Este ADR registra las dos decisiones de **ejecución** que aparecieron al probar
en la máquina real, tienen consecuencias duraderas y no estaban en ninguna de
las tres piezas originales. Y recoge la evidencia de la rama, que ADR-001 exige.

> ## Incumplimiento de ADR-001, dicho antes que nada
>
> ADR-001 pide la nota de arranque **antes del primer commit**. Esta llega
> después de 28 y no se maquilla como si se hubiera escrito antes: parte de lo
> que sigue está reconstruido, y el criterio de parada de la implementación no
> ató nada, porque no estaba publicado cuando había que pararse.
>
> Lo que sí quedó publicado a tiempo y sí ató fue el criterio de la
> reconciliación: las once decisiones se propusieron por escrito y se esperó
> aprobación antes de tocar código. Cubrió el alcance; no cubrió la ejecución.
>
> La nota de rama no se pudo escribir en `.claude/evidencia/` —el entorno de
> esta sesión no da permiso de escritura ahí—, así que la evidencia vive aquí.

## Criterio de parada

Reconstruido, marcado como tal:

1. **Se para y se escala** si algo exige afirmar el estado de grabación sin que
   el sistema de captura lo confirme. *No ocurrió: el estado sale siempre de
   `get_status`, y existe `INCIERTO` para cuando no se sabe.*
2. **Se para y se replantea** si dos rondas seguidas dan defectos de la misma
   familia. *Rozó. Los tres fallos reales son la misma familia —«el sitio que
   debía comprobarlo no podía verlo»—, pero aparecieron en superficies
   distintas y separados por días. Se registró el patrón en vez de seguir
   parcheando: de ahí salen los dos comandos de diagnóstico.*
3. **Se para** si la implementación obliga a tocar un documento canónico. *No
   ocurrió: DR-018 se mantiene intacto (R-11).*

## La pregunta de ADR-001, aplicada

*¿Puede el sitio del arreglo observar el fallo que arregla?* Mordió tres veces,
y las tres la respuesta de partida era **no**:

| Fallo | Por qué el sitio no podía observarlo | Dónde se movió la observación |
|---|---|---|
| La voz no llegaba a la aplicación real | Las pruebas montaban la ventana a mano pasándole las verticales; así construida **no puede** detectar que la aplicación no las pasa | Pruebas que entran por `_build_main_window` |
| El audio se descartaba en Windows | El reproductor de Qt tiraba los paquetes y **no informaba de nada** | Un camino de reproducción sin ese descodificador |
| Las marcas se perdían | El caso de uso llamaba a un diario que la raíz de composición no conectaba; el `None` era legal | Prueba que recorre encender, grabar, marcar y parar, y **abre el archivo** |

## Decisión 1 · En Windows, la voz sale por el reproductor del sistema

`winsound`, de la biblioteca estándar, en lugar de QtMultimedia.

**No es una preferencia.** Contra la máquina real, el motor multimedia de Qt en
Windows descodifica con FFmpeg y, ante el WAV del proveedor de voz, respondía
`Ignoring maximum wav data size` y `Packet corrupt`: descartaba los paquetes y
no sacaba sonido, **sin error de ninguna clase**. Sin sonido y sin señal es la
peor combinación posible, porque desde fuera se ve como «no funciona» y no hay
nada que mirar.

Fuera de Windows sigue mandando Qt. Los dos cumplen el mismo puerto, así que
elegir uno u otro es una línea de la raíz de composición.

Lo que ese camino **no** da, dicho aquí y no descubierto luego: no controla el
volumen del sistema —silenciar es no reproducir— y no avisa por sí solo de
cuándo termina, así que el final se calcula leyendo la duración real del
archivo, cruzando el encabezado con el tamaño en disco y quedándose con el
menor, porque el encabezado del proveedor mentía.

## Decisión 2 · Sirius empieza a hablar antes de terminar de escribir

La primera frase se sintetiza mientras el resto se sigue escribiendo. Se corta
en final de frase y **una sola vez** por respuesta: dos peticiones y no diez,
así que el coste total no cambia.

**Esta decisión relaja una regla escrita.** #126 dice *«solo se habla lo que
Sirius terminó de decir de verdad»*, y hablar antes significa que una respuesta
cancelada a mitad puede haber sonado en parte. Se acepta porque grabando eran
dos esperas seguidas mirando a la cámara, y se compensa del único modo honesto:
**al cancelar o fallar, la voz se calla en seco** y lo que quedaba no se lee.
Interrumpir a alguien es que deje de hablar, no que termine la frase.

Lo que se dice es literalmente lo que ya está en pantalla. Sin adelanto, sin
resumen y sin un segundo modelo por medio.

## Comprobación que las sostiene

**Contra hardware real**, OBS Studio 32.2.1 en Windows 11 con dos escenas
—captura de pantalla y webcam USB—: conexión y autenticación por el servidor
WebSocket local, lista de escenas, cambio de plano y vuelta, y grabación con el
archivo resultante en disco. Después, las mismas órdenes desde Model Studio con
confirmación hablada. La decisión 1 se tomó **después** de oír el silencio y
leer los avisos de FFmpeg en esa máquina, no antes.

**Prueba por mutación.** Cuatro propiedades se han visto fallar antes de darlas
por buenas, quitando a propósito el arreglo que fijan:

| Propiedad | Mutación aplicada | Resultado |
|---|---|---|
| La voz llega a la aplicación real | Borrar el paso de la vertical en `main.py` | 2 pruebas en rojo |
| El trabajo de Qt ocurre en el hilo dueño | Llamar directo en vez de por señal | 1 prueba en rojo, con mensaje legible |
| OBS confirma antes de darlo por bueno | Volver a la consulta inmediata | 1 prueba en rojo |
| Lo escrito en un botón funciona al escribirlo | Quitar «detener» de la lista | 1 prueba en rojo |

**Ciclo completo**, tras fusionar `main` (`d7cec31`) en la rama:
`ruff format` 0 · `ruff check` 0 · `mypy` 0 · **2087 pruebas** en verde, 2
saltadas por falta de QtMultimedia en el runner (MS-A02).

## Consecuencias

- El sonido de Model Studio en Windows deja de depender del descodificador que
  lo descartaba. A cambio, el volumen se controla desde Windows y no desde
  Sirius.
- Una respuesta cancelada puede haber sonado en parte. Es un cambio de
  comportamiento observable y está escrito para que no sorprenda.
- Los dos comandos de comprobación —`voice_doctor` y `capture_setup`— pasan a
  ser el camino normal de diagnóstico. Nacieron de que diagnosticar a distancia
  pidiendo líneas de consola costó cinco rondas y falló la mitad de las veces.

## Qué NO garantiza este trabajo

Escrito aquí para que no se lea como verificado: dos cámaras simultáneas, el
móvil como segunda cámara, sesiones largas —lo más largo grabado son tres
segundos—, la reconexión tras cerrar OBS a mitad de una toma —hay código y
pruebas con dobles, no se ha visto en real—, que `onyx` sea la mejor voz —ahora
se pueden comparar oyéndolas, nadie lo ha hecho— y el coste mensual real, que
es un cálculo sobre la política vigente y no una factura observada.

## Qué haría cada fallo imposible en vez de improbable

| Fallo | Qué se hizo | Imposible o improbable |
|---|---|---|
| Verticales sin conectar en la aplicación real | Pruebas por `_build_main_window` | **Improbable.** Cubre las de hoy; una nueva puede colarse. Imposible exigiría comprobar por construcción que todo lo que la raíz produce llega a la ventana; no se hizo porque cuesta más que el fallo |
| Palabra de un botón que el sistema no entiende | Prueba que lee el texto real de cada botón y exige que `interpret` lo reconozca | **Imposible** para los botones existentes |
| Frase enseñada al usuario que no funciona | Prueba que pasa cada frase mostrada por `interpret` | **Imposible** por lo mismo |
| Configuración generada que Sirius luego descarta | Se relee por el `build_scene_registry` del arranque y se compara la cuenta | **Imposible** de pasar inadvertido |
| Estado de grabación inventado | Sale siempre del backend; `INCIERTO` cuando no se sabe | **Imposible** por diseño del puerto |
| Ejecutar código antiguo creyéndolo nuevo | Primera comprobación de `voice_doctor`: mira el código cargado, no git | **Improbable.** Detecta los tres arreglos conocidos, no los futuros |

## Alternativas descartadas y por qué

- **Insistir con QtMultimedia en Windows.** Se reparó además el encabezado del
  WAV, que era una causa real; aun así, en la máquina del propietario el
  reproductor de Qt siguió sin sonar y el del sistema sonó a la primera. Un
  camino que falla en silencio no se arregla a base de suposiciones.
- **Añadir una biblioteca de audio de terceros.** `winsound` es de la
  biblioteca estándar: cero dependencias nuevas para el mismo resultado.
- **Trocear la respuesta en muchas frases.** Multiplicaba las peticiones y la
  latencia por llamada sin reducir el coste total. Se parte una vez.
- **Mantener la regla estricta de #126 y esperar a la respuesta entera.** Se
  descarta por lo que costaba grabando; queda registrada aquí para que revertir
  la decisión sea un cambio consciente y no un descubrimiento.
