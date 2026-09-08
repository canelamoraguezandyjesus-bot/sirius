# ADR-162 — La altura de una fila del chat se mide sobre un layout asentado, no en cuanto aparece el texto

- Estado: PROPUESTO
- Fecha: 2026-09-08
- Aprobación: la fusión de la PR por el propietario
- Incidencia: #566 (WI-20260908-0130), deuda 7 de la bitácora del ciclo

Este ADR es además la **nota de arranque** de la rama
`fix/wi-20260908-0130-altura-intermedia-layout-asentado` (ADR-001, skill
`disciplina-evidencia`): las cuatro preguntas y el criterio de parada están
abajo y se publicaron en el primer commit de la rama, antes de tocar ninguna
prueba.

## Nota de arranque (cuatro preguntas)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en la
   *medición* que hace `tests/gui/test_conversation_ui.py::
   test_streaming_message_grows_without_overlapping_neighbours`, no en la GUI:
   lee el alto de una fila en un instante en el que Qt todavía no ha colocado
   el contenido nuevo. El arreglo va en el mismo sitio que la medición —el
   fichero de pruebas—, y puede funcionar porque el sitio del arreglo sí puede
   observar el fallo: el alto prematuro y el asentado son dos valores
   distintos, legibles ambos desde la prueba (24 px vs 54 px; 32 px vs 62 px).
2. **¿Qué NO garantiza esto?** No garantiza que la GUI nunca enseñe una fila
   con el alto prematuro: esa ventana de un turno del bucle de eventos sigue
   existiendo en producción y este cambio no la cierra. Quien ya la estrecha
   es `MessageItemWidget._sync_size_when_laid_out`, en
   `src/sirius/presentation/message_view.py`, y ese código sigue igual; ningún
   ADR del registro razona esa cadena, así que el sitio donde se lee es el
   propio fichero. ADR-153 no pinta nada aquí: fue solo la rama sobre la que
   se observó la caída del 06-09, y no toca ni la GUI ni Python. No
   garantiza tampoco que ninguna otra prueba de la suite mida en la misma
   ventana: solo se corrige la que falla. Y no convierte el test en
   determinista frente a cualquier retraso de Qt: elimina la ventana conocida,
   no todas las imaginables.
3. **Criterio de parada** (escrito antes de ver el resultado del arreglo):
   ver más abajo, sección propia.
4. **¿Qué haría el fallo imposible en vez de improbable?** Imposible sería que
   la prueba no leyera geometría de la vista en absoluto y comparase solo lo
   que el widget pide (`sizeHint`), que es síncrono. No se hace porque la
   propiedad que esta prueba protege es precisamente que la **fila** no invade
   a sus vecinas: sustituir la geometría real por el `sizeHint` cambiaría lo
   que afirma y dejaría de cubrir el defecto original (mensajes solapados).
   Esa comparación directa ya existe además en
   `test_finished_message_row_is_as_tall_as_its_widget_asks`. Lo que sí se
   hace es quitar de la comparación el único valor que se sabe transitorio.

## Criterio de parada (escrito ANTES de decidir)

- Si al medir el mecanismo resultara que el alto prematuro nace en el código de
  producción de la GUI (es decir, que la fila se queda corta de forma
  permanente y no durante un turno del bucle de eventos), **parar** y
  registrarlo: sería un defecto real de la aplicación y no una prueba
  inestable, y el alcance de la incidencia cambiaría (límite explícito de #566).
- Si el arreglo no se pudiera fijar con una prueba vista fallar antes del
  cambio, **no inventar** una prueba que pase por construcción: decirlo y
  proponer la alternativa.
- Si el arreglo exigiera `sleep` fijos, `xfail`, `skip` o reintentos, **parar**:
  eso esconde el dato.

## Contexto y problema

`test_streaming_message_grows_without_overlapping_neighbours` cae de forma
intermitente en la cadena completa (bitácora del ciclo, entradas 16 y 44; la
última el 06-09 a las 04:16 con `assert 32 >= 54` sobre una rama que no toca ni
la GUI ni Python). La entrada 47 de la bitácora dejó 47 ejecuciones en verde sin
reproducirlo: 25/25 en aislamiento, 10/10 de `tests/gui` y 12/12 de la cadena
completa.

La prueba mide así:

```python
qtbot.waitUntil(lambda: _widget_at(window, 1).rendered_plain_text() == "parcial", timeout=5000)
mid_stream_height = _row_rects(window)[1].height()
...
assert _row_rects(window)[1].height() >= mid_stream_height
```

`rendered_plain_text() == "parcial"` dice que el TEXTO está puesto. No dice que
la fila ya mida lo que ese texto necesita.

## Comprobación que la sostiene

### 1. El mecanismo, medido

Con una sonda temporal (un `QTimer` de intervalo 0 que muestrea la fila en cada
vuelta del bucle de eventos) sobre la prueba real, cada cambio de contenido de
la fila 1 produce **dos** alturas seguidas, no una:

```
sample (24, 24, 24, (640, 480, 22), 616, 'parcial')            <- prematura
sample (54, 54, 54, (600,  30, 22), 616, 'parcial')            <- asentada
sample (32, 32, 32, (640, 480, 22), 616, 'parcial completo')   <- prematura
sample (62, 62, 62, (600,  30, 22), 616, 'parcial completo')   <- asentada
```

(los campos son: alto del `visualItemRect`, `item.sizeHint()`,
`widget.sizeHint()`, `(ancho, alto, alto del documento)` del cuerpo, ancho del
viewport y texto).

Lo que separa a las dos lecturas es la cuarta columna: en la prematura el
cuerpo todavía tiene su geometría de construcción (640×480, la de un `QWidget`
recién creado que el layout aún no ha colocado); en la asentada ya tiene la que
le da el layout (600×30). Es exactamente la doble medida que documenta
`MessageItemWidget._sync_size_when_laid_out`: una síncrona al poblar el
contenido y otra en el turno siguiente del bucle de eventos, ya con el cuerpo
colocado. **El defecto no está en producción**: la fila queda con el alto
correcto: el valor corto vive un turno. Por eso el criterio de parada 1 no se
dispara.

### 2. El fallo, reproducido

La suposición de que el fallo era irreproducible se cayó al ocupar el bucle de
eventos. Con un `QTimer` de intervalo 0 corriendo durante la prueba —un
sustituto fiel de un runner cargado— y una copia literal del test actual:

```
RUN 16: mid=54 final=32   -> assert 32 >= 54   (el fallo del 06-09, idéntico)
```

Sobre 160 ejecuciones con esa sonda, la distribución de la prueba tal como está
hoy es:

| mid | final | veces |
|---|---|---|
| 24 (prematura) | 62 | 10 |
| 54 | 32 (prematura) | **1 — falla** |
| 54 | 62 | 149 |

### 3. La hipótesis de la incidencia estaba invertida, y eso cambia el arreglo

La incidencia ofrecía como pista, explícitamente no confirmada, que la lectura
**intermedia** capturaba un alto anterior al ajuste. Lo medido dice lo
contrario: en el caso que falla, la intermedia (54) es la asentada y la que
está prematura es la **final** (32). La aserción cae porque compara un final
transitorio contra un intermedio correcto.

Consecuencia directa: asentar solo la lectura intermedia **no elimina el modo
de fallo**. Hoy hace falta que coincidan «intermedia asentada» y «final
prematura»; asentando solo la intermedia bastaría con «final prematura», que es
un subconjunto mayor. Medido sobre 160 ejecuciones por variante:

| variante | fallos / 160 | lecturas prematuras observadas |
|---|---|---|
| como está hoy | 1 | 10 intermedias, 1 final |
| solo la intermedia asentada | 0 | 0 (el modo de fallo sigue abierto) |
| **ambas asentadas** | 0 | 0 |

Que «solo la intermedia» diera 0/160 no la salva: su modo de fallo es el mismo
que el actual menos la condición que hoy lo enmascara, así que su tasa es por
construcción mayor o igual; 160 ejecuciones no tienen resolución para
distinguir 1/160 de 1/1000.

Las 10 lecturas intermedias prematuras sí importan por otra razón: cuando la
intermedia sale 24, la aserción compara 62 contra 24 y pasa sin afirmar nada —
es la comparación vacua que ya documenta
`test_finished_message_row_is_as_tall_as_its_widget_asks` («ambas medidas
salían igual de obsoletas»).

### 4. La prueba nueva, vista fallar antes del cambio (mutación)

`test_row_height_read_as_soon_as_the_text_lands_is_not_the_settled_one` fija el
invariante de forma determinista: pone el texto desde el propio hilo de la
prueba —sin que pase un turno del bucle de eventos— y compara la lectura
inmediata con la asentada.

Mutación aplicada: sustituir el cuerpo de `_settled_row_height` por
`return _row_rects(window)[index].height()`, es decir, deshacer el cambio y
medir como se medía antes.

```
# con la mutación (medida de antes del cambio)
assert premature_height < settled_height
E       assert 24 < 24
1 failed

# sin la mutación
1 passed
```

Las dos direcciones, como exige ADR-001 §3.

### 5. Validaciones obligatorias

`uv run ruff format --check .` (607 ficheros), `uv run ruff check .`,
`uv run mypy src tests` (574 ficheros), `uv run pytest` y `git diff --check`,
todas en verde. `tests/gui` completa: 482 pasadas, 2 saltadas (QtMultimedia
ausente, MS-A02).

## Decisión

**Las dos alturas que compara la aserción se leen sobre una geometría
asentada**, con un ayudante nuevo en el fichero de pruebas,
`_settled_row_height`, en el mismo estilo de espera determinista que el resto
(`qtbot.waitUntil`, sin `sleep`):

- la **final**, porque es la lectura prematura que hace caer la prueba;
- la **intermedia**, porque es la que pide el objetivo de la incidencia y sin
  ella la comparación es vacua una de cada dieciséis veces.

El ayudante espera a que dos lecturas consecutivas del bucle de eventos
coincidan y a que el alto no quede por debajo del que pide el widget. Es
determinista sin `sleep`: el `QTimer.singleShot(0, ...)` que dispara la segunda
medida tiene prioridad sobre el temporizador de sondeo de `waitUntil`, así que
entre dos sondeos siempre ha corrido.

Ninguna aserción de la prueba se relaja ni se borra: sigue afirmando que la fila
en streaming no invade a sus vecinas ni antes ni después, y que no encoge
respecto a lo que llegó a ocupar. Lo único que cambia es *cuándo* se leen los
dos números que compara.

No se toca el código de producción de la GUI.

## Consecuencias

- La prueba deja de depender de en qué vuelta del bucle de eventos caiga el
  sondeo de `waitUntil`, y pasa a comparar 54 contra 62 siempre, en vez de
  62 contra 24 (vacua) o 32 contra 54 (falso fallo).
- Queda un ayudante reutilizable para cualquier medición futura de geometría de
  fila en este fichero.
- La ventana de un turno con el alto prematuro sigue existiendo en producción,
  a la vista y documentada, aquí y en `message_view.py`. Si alguna vez hay que
  cerrarla, este ADR es el sitio donde está medida.

## Alternativas descartadas y por qué

- **Asentar solo la lectura intermedia** (lo que pedía literalmente la
  incidencia): descartada por la sección 3 — no elimina el modo de fallo
  observado, solo le quita la condición que hoy lo enmascara.
- **Sondear con `qtbot.wait(50)` antes de medir**: es un `sleep` fijo
  disfrazado, prohibido por la incidencia y frágil ante una máquina más lenta.
- **`xfail`, `skip` o reintentos**: esconden el dato; prohibidos por la
  incidencia y por el criterio de parada.
- **Comparar solo `sizeHint` y no geometría real**: cambiaría lo que la prueba
  afirma y dejaría de cubrir el defecto de mensajes solapados (pregunta 4 de la
  nota de arranque).
- **Dejar la sonda del `QTimer` de intervalo 0 como prueba permanente**:
  descartada. Reproduce el fallo 1 de cada 160 veces, así que como guardia
  sería ella misma inestable. Su sitio es este ADR, como evidencia fechada.
