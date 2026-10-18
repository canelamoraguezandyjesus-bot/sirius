# ADR-254 — Al cortarle, dejar de escribir la respuesta

- Estado: APROBADO
- Fecha: 2026-10-17
- Aprobación: la decisión es del propietario, del 17-10-2026; entra en `main` con la
  fusión de la PR que lo introduce, con una ronda limpia de Codex sobre el head de
  contenido y Quality en verde (ADR-205). Cambia su decisión del 15-10-2026 en PA-R03-07
  (ADR-245).

## Nota de arranque

Publicada antes del primer commit en la incidencia #697. Aquí, resumida; la incidencia la
tiene entera.

1. **Dónde vive el fallo y dónde va el arreglo.** Al cortarle, `_cut` de
   `application/local_listening.py` callaba la voz, pero la petición de la charla seguía
   hasta el final, y lo que se cerró mientras hablaba esperaba detrás. El arreglo: al
   cortarle, además de callar la voz, cortar la petición de la charla con el `cancel` que
   desde ADR-252 cuelga la conexión con Ollama. Lo que el modelo llegó a escribir queda en
   la charla con la nota de hasta dónde lo oyó, y es lo que lee después. PA-R03-07 y sus
   pruebas se ponen al día. **¿Puede el sitio del arreglo observar el fallo?** Sí: `_cut`
   sabe qué turno está contestando, y los dobles miden cuándo llega lo nuevo al modelo.
2. **Qué NO garantiza.** Que Ollama deje de escribir al momento en su Windows; lo que el
   modelo iba a decir después del corte, que se pierde, porque es lo que él eligió; que lo
   que quede a medias se entienda al releerlo.
3. **Criterio de parada.** Con los dobles, lo nuevo llega al modelo en menos de 1 s tras
   el corte, vista fallar con el código de antes; la charla guarda lo escrito hasta el
   corte y la nota de hasta dónde sonó; PA-R03-07 y su trazabilidad al día; cada regla
   nueva con su mutación; la batería entera en verde; dos rondas de revisión con la misma
   familia, se para.
4. **Qué lo haría imposible en vez de improbable.** Que lo nuevo espere a lo de antes:
   imposible mientras el corte cuelgue la petición y la cadena de turnos no espere a uno
   cortado.

## Contexto y problema

ADR-245, la pieza E de la 0.3, hizo que se le pudiera cortar: si el propietario habla
mientras Sirius habla, Sirius calla en menos de medio segundo. El 15-10-2026 el propietario
decidió que lo que iba a decir quedara escrito entero aunque le cortara con el modelo aún
escribiendo, y que la charla apuntara hasta dónde lo oyó (PA-R03-07). Para eso la petición
seguía hasta el final, y lo que se cerró mientras hablaba esperaba detrás.

El repaso de la consola de la #696 lo midió con un modelo de mentira que tarda 10 s en
escribir: calla a los 3,27 s, pero lo nuevo llega al modelo 10,4 s después de la primera
petición, y su primer sonido, 8 617 ms después de que él callara. Con una respuesta larga,
decenas de segundos sin contestarle a lo nuevo. En E-R03-03, que le corta diez veces,
parecería colgado.

## La decisión del propietario

Se le preguntó el 17-10-2026: «Cuando le cortas hablando, Sirius calla al momento, pero no
contesta a lo nuevo hasta que el modelo termina de escribir lo que iba a decir. Es porque el
15-10 decidiste que quedara escrito entero. Con una respuesta larga, puede tardar decenas
de segundos en contestarte. ¿Hago que deje de escribirla en cuanto le cortas, aunque quede
a medias en la charla? Te lo recomiendo.» Contestó: «Vale si has lo como dices».

## Opciones consideradas

Para lo que se guarda al cortar, una vez cortada la petición:

1. **A, la respuesta cortada queda COMPLETED**, con lo que llegó a escribir y la nota de
   hasta dónde sonó. Todo lo demás sigue como con ADR-245: el modelo la lee con su nota y
   se le atribuye su modelo.
2. **B, queda CANCELLED con la nota**, como si él hubiera pulsado «Cancelar». Entonces el
   modelo no la leería, porque el contexto deja fuera lo que no está COMPLETED
   (SIRIUS-ARQ-0.1 S5.2), no se apuntaría la nota, y la ventana y `sirius-oye` dirían
   «Envío cancelado.». Para arreglarlo habría que tocar el contexto, los textos y la consola.

## Decisión

La opción A. Cortarle por voz no es cancelar el envío: lo dicho queda dicho, ahora solo
hasta donde llegó a escribir. Es el modelo de ADR-245 frente a la letra de SIRIUS-ARQ-0.1
S5.1, que habla de la cancelación del envío y no se toca. Cambia lo que fijó ADR-245 para
PA-R03-07, que lo que iba a decir «queda escrito entero aunque le corte con el modelo aún
escribiendo».

- **`_cut`**, en el oído, además de callar la voz, pide a la charla que deje de escribir esa
  respuesta, con su operación, que viaja con lo que se está diciendo.
- **`SendMessageUseCase.cut(operation_id)`** corta como `cancel`, que cuelga la conexión con
  Ollama desde ADR-252. Lo que el modelo llevaba escrito queda como su respuesta,
  COMPLETED; se le atribuye su modelo, se apunta hasta dónde se oyó y el modelo lo lee
  después con esa nota.
- **Tras un turno cortado no se mira si toca resumir**, tampoco si le cortan con la
  respuesta ya escrita, mientras dice la última frase: sería otra petición al modelo, y lo
  nuevo esperaría detrás. Lo mira el turno siguiente.
- **Si le cortan mientras resume**, cosa que pasa cada 18 turnos, se corta también el
  resumen, que va con la operación del turno, `resumen-<operación>`. Un resumen cortado no
  guarda nada ni cuenta como fallo en el diario, y lo hace el turno siguiente.
- **Si le cortan antes de que escriba nada**, su respuesta queda acabada y vacía, con la
  nota de que no oyó nada. La ventana y `sirius-oye` enseñan «(le cortaste antes de que
  dijera nada)», no una línea vacía.
- **El juez no puntúa las respuestas cortadas**, porque quedan a medias: diez cortes de
  E-R03-03 le bajarían la media sin motivo.
- **Si cortar la charla falla**, la respuesta acaba entera, como antes, y el diario apunta
  solo el tipo de fallo.
- **PA-R03-07** en `docs/evolution/PRUEBAS_0.3_DEL_ROBOT.md`, con su nota de la decisión del
  17-10-2026, y su trazabilidad, al día. También los textos que citaban el de antes.

## Comprobación que la sostiene

- **La prueba clave**, la segunda de PA-R03-07: con el código de `c7c378f5`, lo nuevo llega
  al modelo 2,99 s después del corte; con el arreglo, en 0,039 a 0,041 s, en tres pasadas
  con los dobles.
- **Las demás pruebas nuevas** también caen con el código de antes: 3 del oído, 2 de la
  charla y 1 del juez. La tercera de PA-R03-07 lee lo que quedó escrito, y el inventario
  sigue en 28.
- **El modelo de mentira** de la aceptación de la 0.3 deja de escribir al cortarle, como
  hace Ollama al colgarle.
- **Mutación**: 11, y caen las 11, cada una con su caché de bytecode vacía.
- **Las suites afectadas**: 1 231 en verde, 2 omitidas y 1 `xfail`, en 13 min 30 s.
- **ruff** limpio; **mypy** sin errores en 743 ficheros; el comprobador de documentos, sin
  defectos.
- **La revisión en adversario de `01937923`**, por otra bifurcación: 193 pruebas en verde y
  sus 5 mutaciones caen. Encontró dos fallos y tres textos:
  - si le cortan mientras resume, lo nuevo espera al resumen entero;
  - si le cortan con la respuesta ya escrita, antes de mirar si toca resumir, resume igual;
  - tres docstrings seguían diciendo que la respuesta queda entera.

  Y una nota que se arregla también: una respuesta cortada antes de la primera palabra se
  enseñaba como una línea vacía. Las seis pruebas nuevas o cambiadas fallan con el código de
  antes del arreglo, y pasan con él. Caen las 8 mutaciones del arreglo, cada una con su caché
  de bytecode vacía. La que mide el tiempo: si le cortan mientras resume, lo nuevo llega al
  modelo de 0,02 a 0,03 s después de que calle, en tres pasadas con los dobles; sin cortar
  el resumen, a los 2,02 s, cuando acaba el resumen.
- **La batería entera**: la de la PR, en ADR-253.

## Consecuencias

- Lo que el modelo iba a decir después del corte se pierde: queda en la charla lo que llegó
  a escribir, con la nota de hasta dónde sonó.
- PA-R03-07 cambia con esta decisión; E-R03-03 no. Sigue pidiendo que calle en menos de
  medio segundo las 10 de 10 veces, que atienda lo nuevo y que no se conteste a sí mismo.
- Las respuestas cortadas no cuentan para la media del juez.

**Qué NO garantiza, después del código:**
- Que su Ollama deje de escribir al momento con la conexión colgada.
- Que un corte sea suyo: un corte falso, por eco que se cuela, una tos o la tele, ahora
  también deja la respuesta a medias en la charla, no solo la voz.
- Que el juez puntúe las cortadas que ya estaban escritas enteras: las deja fuera todas,
  porque no hay ningún dato para distinguirlas.

## La lección

- familia: `modelo-dentro-del-turno`
- sin esto se repetiría: al cortarle, dejar que siga dentro del turno una petición al modelo
  que ya nadie va a oír, el resto de la respuesta o el resumen de cada 18 turnos, con lo
  nuevo esperando detrás: decenas de segundos con una respuesta larga. El corte callaba la
  voz, y la petición seguía.
- lo hace cumplir: `tests/acceptance/test_robot_0_3_voz.py`

## Revisión externa

Va en la misma PR que ADR-253, y su alcance se suma al de allí, escrito antes de la primera
petición: que al cortarle deje de escribir, que lo nuevo no espere, que se guarde
exactamente lo escrito con su nota, y que el juez y el resumen no hagan esperar ni cuenten
lo cortado.

**Ronda 1**, sobre `001ede34`: nada del corte. Sus dos hallazgos son de ADR-253, y allí se
anotan.
