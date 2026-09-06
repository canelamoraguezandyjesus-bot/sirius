# ADR-151 — La pasada del contador mide y declara su entrega: retraso e higiene de su ventana previa

- Estado: PROPUESTO
- Fecha: 2026-09-06
- Aprobación: el propietario, al fusionar la PR de la incidencia #550 (WI-20260906-023326)

## Contexto y problema

ADR-144 cerró la mitad derivadora del problema: la hora de la pasada del
contador (`24 3 * * *`, 03:24 UTC) **se deriva** del mayor hueco libre de
disparos periódicos y se valida contra la ventana de tolerancia de etiqueta de
máquina (170 min hoy). La premisa de esa derivación es que **nada mueve
etiquetas durante la ventana previa a la pasada**. Sus «Consecuencias» dejaron
explícita la mitad que faltaba —«derivador ya; ventana después»—: nadie
comprueba esa premisa cuando la pasada llega de verdad.

Y no llega a su hora. Las ocho últimas pasadas programadas de
`contador-siete-dias.yml` (`event: schedule`, runs 4 a 11) arrancaron a las
10:13, 09:20, 09:54, 08:45, 07:59, 08:09, 08:04 y 07:44 UTC: **entre 4 h 20 min
y 6 h 50 min después de las 03:24 programadas, ninguna a su hora**. GitHub
entrega el cron con retraso, y ese retraso mueve la pasada a una franja del día
donde el repositorio SÍ tiene actividad.

El coste no es un verde falso: la ventana 4 del verificador
(`_ventana_residencia_o_fusion`) ya declara `NO_COMPARABLE` una etiqueta más
fresca que la tolerancia, y un `NO_COMPARABLE` no es verde. El coste es **un día
perdido en silencio**: nada dice que se perdió por haber llegado tarde a una
ventana sucia, así que el dato con el que decidir qué hacer con la entrega
tardía no existe.

## Nota de arranque (escrita ANTES de tocar el código)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo —«la pasada no sabe
   cuándo llegó ni con qué se cruzó»— vive en la propia pasada: `sirius-racha`
   toma `ahora = datetime.now(UTC)` y no lo compara con nada. El arreglo vive
   ahí mismo, y **sí puede observar lo que arregla**: la hora programada es
   derivable en el mismo proceso (`hora_recomendada_pasada`, que el guardián de
   ADR-144 mantiene igual al cron cableado) y la actividad de la ventana es
   legible por la misma vía `gh` que la pasada ya usa. No hace falta que un
   proceso informe de su propia muerte: informa de su propio nacimiento, que sí
   presencia.
2. **¿Qué NO va a garantizar esto?** No cambia ningún veredicto de ningún eje:
   la ventana 4 sigue decidiendo por edad de etiqueta, y una pasada tarde con la
   ventana sucia sigue dando exactamente el mismo resultado que daba. No mueve
   el cron, ni la tolerancia, ni ninguna ventana. No hace verde ningún día que
   hoy no lo sea, ni rojo ninguno que lo sea. No cubre los runs que **cruzan**
   la ventana sin empezar ni terminar dentro (un job que arrancó antes y sigue
   vivo): el criterio es «empezó o terminó dentro», y se declara así. Y no
   arregla el retraso de GitHub —no está en nuestra mano—: solo lo mide.
3. **Criterio de parada.** (a) Si medir la entrega obligara a cambiar el
   resultado de cualquier eje, o a tocar `.github/**`, el derivador, la
   tolerancia o cualquier ventana del verificador, se para y se escala: el
   encargo es medir, no decidir. (b) Si el campo nuevo del registro rompiera la
   lectura de las líneas antiguas —las que no lo llevan—, se para: el registro
   solo crece y su historia no se reescribe. (c) Si una lectura caída de los
   runs pudiera confundirse con «ventana tranquila» en algún camino del código,
   se para: ese es el defecto que este cambio existe para no cometer.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Imposible sería que
   la ausencia de medida no se pudiera representar: que toda línea llevara su
   `entrega`. No se hace, y por qué: el registro es versionado y solo crece, y
   ya tiene líneas escritas sin ese campo. Obligar el campo dejaría ilegible la
   historia (criterio de parada (b)). Lo que sí se hace imposible es la
   confusión que importa: `lectura_de_runs` es un valor propio
   (`LecturaEstado`), no la lista vacía, así que «no pude leer» y «leí y no
   había nada» son **dos valores distintos** y no un mismo cero con dos
   significados —el defecto que `sirius_engine.ports.github_mirror` documenta
   haberse cometido cinco veces.

## Opciones consideradas

1. **Que la pasada mida y declare su entrega, sin cambiar ningún veredicto.**
   El retraso, derivado de la hora programada que ya se deriva; la higiene de la
   ventana, leída de los runs reales por un método nuevo del puerto de solo
   lectura. Las dos medidas al `motivo` de la evaluación y a un campo opcional
   `entrega` de cada línea nueva.
2. **Que la ventana sucia rompa el día o lo marque `NO_COMPARABLE` por sí
   misma.** Descartada: cambia veredictos, y hacerlo antes de tener un solo día
   de datos sobre cuánta actividad hay de verdad en la ventana sería decidir a
   ciegas justo lo que estos datos servirán para decidir.
3. **Mover el cron o pedir a GitHub que entregue a su hora.** Fuera de alcance
   (`.github/**` no se toca en esta incidencia) y, la segunda, fuera de nuestra
   mano.
4. **Deducir la actividad de la ventana del propio registro o del diario del
   motor.** Descartada: ninguno de los dos ve los runs de Actions, que son
   justamente lo que mueve las etiquetas.

## Decisión

Se toma la opción 1.

- El puerto `GitHubMirrorPort` gana `listar_runs_en_ventana(repo, desde, hasta)`
  → `LecturaRunsEnVentana`, con su `LecturaEstado` propio como todas las demás
  lecturas. `GitHubCliMirrorReader` lo implementa sobre
  `gh api repos/{repo}/actions/runs` con el filtro `created` de la API.
- `sirius_engine.seven_day_streak` gana `medir_entrega_de_la_pasada` (la medida)
  y `declarar_entrega_de_la_pasada` (el texto), y `evaluar_racha` acepta
  `entrega_hoy` con el mismo molde que `lecturas_caidas_hoy` (ADR-084): una
  declaración no bloqueante que se anexa al `motivo` y no toca el conteo.
- `LineaRegistro` gana el campo **opcional** `entrega`
  (`retraso_min`, `runs_en_ventana`, `lectura_de_runs`). Ausente = «no medido»:
  las líneas antiguas se siguen leyendo y evaluando igual.
- Los runs del propio contador no cuentan como actividad, por el **mismo
  criterio nombrado** que ADR-144: `NOMBRE_DEL_WORKFLOW_DEL_CONTADOR`. Una
  pasada no se estorba a sí misma, y contarla daría siempre «ventana sucia».

## Comprobación que la sostiene

- Los ocho retrasos citados salen de los runs reales de
  `contador-siete-dias.yml` (`event: schedule`, runs 4 a 11), tal y como los
  recoge el cuerpo de la incidencia #550.
- Cada prueba nueva se vio FALLAR antes del cambio (ADR-001, §3 de la skill
  `disciplina-evidencia`); el detalle de la comprobación va en la descripción de
  la PR.
- Las cuatro validaciones obligatorias, en verde, con una sola invocación del
  script de comprobación (ADR-145).

## Consecuencias

- A partir de la primera pasada con este cambio, el registro guarda con qué
  retraso llegó y con qué se cruzó. En unos días habrá datos reales para decidir
  —eso sí, en otra incidencia— qué hacer con la entrega tardía: mover la hora,
  ensanchar la ventana, o aceptar el coste.
- El `motivo` de cada clase crece con una frase más. Es deliberado: un `CUMPLE`
  que calle que la pasada llegó cinco horas tarde a una ventana sucia afirma
  más de lo que el dato sostiene.
- La pasada hace **una llamada más** a `gh` por ejecución. Si esa llamada cae,
  se declara y la pasada sigue: una lectura caída no rompe la racha (ADR-084).
- Si `hora_recomendada_pasada` no pudiera derivar la hora —el escenario que el
  guardián de ADR-144 vigila: alguien sube un `timeout-minutes` y ninguna hora
  del día sirve—, la pasada **no revienta**: lo declara en el `motivo` y escribe
  la línea sin `entrega`. Un guardián en rojo es mejor aviso que una pasada
  diaria muerta.

## Alternativas descartadas y por qué

Las opciones 2, 3 y 4 de arriba. La 2 es la tentadora y la que este ADR aparta a
propósito: convertir la medida en veredicto sin haber medido nada todavía sería
exactamente «afirmar más de lo que el dato sostiene», la primera de las dos
familias de defectos que dieron origen a la disciplina de evidencia.
