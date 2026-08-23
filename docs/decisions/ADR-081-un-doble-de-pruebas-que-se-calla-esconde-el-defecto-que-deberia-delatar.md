# ADR-081 — Un doble de pruebas que se calla esconde el defecto que debería delatar

- Estado: APROBADO
- Fecha: 2026-08-23
- Aprobación: fusión de la PR por el propietario
- Contexto: incidencia #290, aparecida al fusionar #289
- Relacionadas: ADR-001 (disciplina de evidencia: medir antes de fijar el
  criterio, y ver fallar), ADR-047 (un defecto encontrado se registra y no se
  borra), ADR-080 (el precedente inmediato: elegir midiendo y escribir el
  precio), incidencia #290 (el defecto H-15)

## Contexto y problema

El 23-08-2026 la PR #289 lanzó **dos ejecuciones de Quality sobre el mismo
commit** (`4a75ec7`) por un cerrar-y-reabrir. Dieron resultados distintos:

| ejecución | duración | resultado |
|---|---|---|
| 32634952899 | 290 s | **3502 passed** |
| 32634959500 | 316 s | **1 failed** |

El fallo:

```
FAILED tests/gui/test_model_studio_integration.py::test_nothing_is_said_twice
       pytestqt.exceptions.TimeoutError: waitUntil timed out in 5000 milliseconds
tests/gui/test_model_studio_integration.py:760
```

Misma entrada, resultado distinto. Una prueba así **para el ciclo al azar**, y
cada parada cuesta una vuelta y la atención del propietario — que es el coste
que este proyecto existe para quitar.

## La primera explicación era cómoda, y era falsa

La explicación inmediata fue que las dos ejecuciones competían por el runner y
que a la lenta se le agotó el plazo. Medido antes de darla por buena:

```
0.52s call  tests/gui/test_model_studio_integration.py::test_nothing_is_said_twice
```

**0,52 s contra un plazo de 5 s: diez veces de margen.** Un 9 % de lentitud no
revienta eso. La explicación por lentitud no se sostenía, y darla por buena
habría llevado al arreglo equivocado —subir el plazo— dejando el defecto dentro.

Queda escrito porque es el mismo error de método que ya costó dos avisos falsos
de atasco esta semana: **explicar una observación temporal sin medir**.

## La causa real

`FakeAudioPlayback.finish()` no hacía nada, en silencio, si `play()` todavía no
se había llamado:

```python
callback, self._on_finished = self._on_finished, None
if callback is not None:      # si aún no hay nadie, el aviso se pierde
    callback()
```

Y la prueba esperaba el evento equivocado: la **síntesis** (`text_to_speech.requests`)
en vez de la **reproducción** (`playback.played`). Entre las dos hay una ventana
que la carga de la máquina ensancha. Un `finish()` caído dentro de esa ventana se
perdía, el segundo trozo no se sintetizaba nunca, y la espera moría a los 5 s sin
decir por qué.

No es lentitud: es una ventana. Por eso falla la ejecución cargada y pasa la que
va sola, aun con diez veces de margen.

**Dónde está la ventana, exactamente.** `SpeakWorker` es un `QRunnable` y corre
`StudioVoiceUseCase.speak()` en un `QThreadPool`, **nunca en el hilo de la
interfaz** (`src/sirius/presentation/studio_workers.py`). Dentro de `speak()`:

```python
synthesized = self._text_to_speech.synthesize(...)   # aquí crece `requests`
...
self._record_speech(synthesized)                     # <- la ventana vive aquí
return self._play(synthesized)                       # aquí se llama a play()
```

El hilo de la interfaz ve crecer `requests` y `waitUntil` vuelve **de inmediato**,
mientras el trabajador todavía está entre las dos líneas. Sin esa frontera de
hilos la ventana no existiría —`speak()` es síncrono—, y por eso nombrarla
importa: es lo que convierte un orden aparentemente garantizado en una carrera.

## Un resultado negativo que no se calla

**No se consiguió reproducir el fallo.** Con la espera vieja restaurada y la
guarda puesta: tres tandas de **dos suites de GUI concurrentes** —la condición
real de CI, dos ejecuciones a la vez— dieron `393 passed` las seis veces. Antes,
dos vueltas de la suite bajo carga de CPU en todos los núcleos menos uno: también
`393 passed`.

Eso **no desmiente el diagnóstico**: la ventana es demostrable leyendo el código,
y es estrecha —un registro de presupuesto entre dos líneas—, que es justamente por
qué el fallo es raro y no constante. Pero sí obliga a decir dos cosas:

1. La causa está **razonada sobre el código y sobre la frontera de hilos**, no
   reproducida a voluntad. Se dice así.
2. **Volver a lanzar la prueba no vale como comprobación de este arreglo.** Ocho
   ejecuciones en verde no distinguen «arreglado» de «hoy no tocó». Lo que sí
   comprueba es la guarda del doble, que sí se ve fallar a voluntad.

**La prueba de al lado ya tenía la cura.** `test_the_second_piece_waits_for_the_first_to_finish`,
cuarenta líneas más abajo, espera a que el sistema quede quieto antes de llamar a
`finish()`. El conocimiento existía en una prueba y no en su vecina, que es la
forma más común en que un repositorio olvida algo que ya sabía.

## Criterio de parada (escrito ANTES de decidir)

1. Si hacer que `finish()` grite rompe alguna prueba que hoy lo llame
   **legítimamente** sin nada sonando, se para: sería cambiar el comportamiento
   para que encaje con el instrumento.
2. Si el arreglo exige subir el plazo, se para. Subir un plazo **esconde** la
   ventana, no la cierra: la prueba volvería a fallar el día que la máquina vaya
   más cargada, y ya sin pista de por qué.
3. Si hace falta tocar el caso de uso de voz de producción, se para y se dice.

## Opciones consideradas

1. **Subir el plazo de 5 s a 15 s.** Descartada por el criterio 2. Es el arreglo
   que la explicación falsa habría sugerido, y no arregla nada.
2. **Arreglar solo la espera de esa prueba.** Correcta pero insuficiente: deja el
   doble callado, así que la próxima prueba que cometa lo mismo volverá a morir
   en un plazo agotado sin causa visible.
3. **Que el doble se niegue a tragarse el aviso, y arreglar la espera.** Elegida.

## Decisión

Opción 3, las dos mitades:

- `FakeAudioPlayback.finish()` **lanza** cuando no hay nada sonando, con un
  mensaje que nombra la causa y dice qué esperar en su lugar.
- `test_nothing_is_said_twice` espera a que crezca `played` —que la
  reproducción arrancó— en vez de a que se registre la síntesis.

La primera mitad es la que importa a futuro: convierte un misterio de cinco
segundos en un error inmediato con nombre, en esta prueba y en cualquiera que
cometa lo mismo después.

## Comprobación que la sostiene

**Alcance, medido antes de fijar el criterio.** De las **7** llamadas a
`playback.finish()` del árbol, **una sola** esperaba el evento equivocado: la que
falló. Las otras seis esperan algo que ya garantiza reproducción activa. No es
una familia extendida — es un sitio, y la raíz que lo hizo invisible toca a los
siete.

**Criterio de parada 1, comprobado y no disparado:** con la guarda puesta,
`tests/gui/test_model_studio_integration.py` y `tests/unit/test_studio_voice.py`
dan **69 passed**. Ninguna prueba llamaba a `finish()` legítimamente sin nada
sonando, así que la opción elegida no estaba cambiando lo medido para que
encajara.

**Vista fallar (ADR-001).** Reproduciendo la carrera —`finish()` justo tras el
clic, sin esperar a que suene— la guarda dispara con su nombre:

```
E  AssertionError: finish() sin nada sonando: play() todavía no se ha llamado
   (o ya hubo un stop()) ... Espera a que crezca `played` antes de dar el audio
   por terminado.
src/sirius/adapters/audio/fake.py:195
1 failed in 2.35s
```

**2,35 s con la causa escrita**, frente a **5 s de plazo agotado sin ninguna**.
Esa es toda la diferencia que busca este ADR.

La guarda va además con su anti-vacua: si gritara siempre, las pruebas que
esperan el grito pasarían solas, así que
`test_con_reproduccion_en_marcha_el_aviso_llega` fija que con reproducción
activa el aviso sí llega.

## La ventana que quedaba, y un aviso sobre el propio método

Revisando el arreglo se encontró que **no cerraba la ventana del todo**, dos
líneas más abajo y en la misma familia. `FakeAudioPlayback.play()` hacía crecer
`played` ANTES de instalar el aviso:

```python
self.played.append(audio_path)     # otro hilo ya puede ver «ya suena»
self._playing = True
self._on_finished = on_finished    # ...pero el aviso todavía no está puesto
```

`played` es precisamente la señal por la que la prueba arreglada sabe que puede
llamar a `finish()`. Con ese orden, el arreglo cambiaba una ventana ancha por una
estrecha en vez de cerrarla. Instalando el aviso primero, **`played` no vacío
implica aviso puesto**, y la invariante queda fijada por
`test_el_aviso_queda_instalado_antes_de_que_played_crezca`, que se ve fallar
devolviendo el orden anterior.

**Y un aviso que toca a la disciplina misma.** Al restaurar el fichero mutado con
`cp`, la siguiente ejecución siguió comportándose como el fichero MUTADO: el
fuente restaurado era correcto —`inspect.getsource` lo confirmaba— pero
`__pycache__` servía el bytecode viejo. Durante unos minutos eso se leyó como
«contaminación entre pruebas», que es un diagnóstico falso y caro.

Importa más allá de este bloque: **este repositorio comprueba sus guardas
sembrando mutaciones**, y una caché rancia puede hacer que una mutación parezca
no morder, o que un arreglo parezca no arreglar. La conclusión práctica es
sencilla y va escrita aquí para que no se vuelva a descubrir: **tras restaurar
un fichero mutado, borrar `__pycache__` antes de creerse la siguiente
ejecución.**

## Consecuencias

**Lo que esto NO arregla.** Hay **139 plazos de 5000 ms** en `tests/gui/`. Este
ADR cierra uno, con causa medida. No audita los otros, y decir lo contrario
sería vender más de lo que se compra. Lo que sí queda para todos ellos es la
lección: un plazo agotado en una prueba de GUI merece que se mida la duración
real antes de culpar a la máquina.

Lo poco que sí se midió sobre ellas: con la espera vieja restaurada, ocho
ejecuciones de la suite de GUI —seis de ellas concurrentes de dos en dos— no
sacaron ningún otro fallo. Es una señal débil a favor de que esto era un sitio y
no un sistema, y se presenta como lo que es: ausencia de evidencia, no evidencia
de ausencia.

**Un doble de pruebas es una pieza de vigilancia, no de comodidad.** Su trabajo
no es dejar pasar: es delatar. Cuando un doble tolera en silencio una secuencia
imposible, convierte el defecto de quien lo usa en un síntoma sin causa, y el
coste no lo paga quien escribió el doble sino quien tres semanas después mira un
plazo agotado a las tres de la mañana.

**Efecto lateral esperado:** cualquier prueba futura que llame a `finish()` sin
haber esperado a la reproducción falla al instante y con la causa dicha, en vez
de volverse inestable. Es la frontera mecánica en lugar de la confiada, aplicada
a un doble de pruebas.

## Alternativas descartadas y por qué

- **Subir el plazo**: criterio de parada 2. Esconde la ventana y la devuelve más
  tarde y sin pista.
- **Arreglar solo la espera**: deja la raíz dentro. El siguiente que la pise paga
  el mismo precio de diagnóstico que se ha pagado aquí.
- **Hacer que `finish()` encole el aviso para cuando `play()` llegue**: convertiría
  una secuencia imposible en una tolerada, y el doble dejaría de parecerse al
  adaptador real, que tampoco puede terminar lo que no ha empezado. Un doble que
  es más permisivo que la realidad deja pasar defectos que la realidad no.
