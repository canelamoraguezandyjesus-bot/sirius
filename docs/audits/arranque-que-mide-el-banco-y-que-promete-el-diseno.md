# Nota de arranque — ¿Qué mide el banco y qué promete el diseño?

Escrita **antes de medir**, 20-09-2026, 19:20 UTC. ADR-001.

## El riesgo de esta investigación, dicho primero

Esta pregunta puede degenerar en **mover la portería**: medir con otra regla
hasta que el número salga bonito. Si llega ahí, no vale nada y hace daño.

Así que queda escrito **antes** de ver ningún resultado:

> **No se propone cambiar la métrica. Salga lo que salga.** Lo que se mide aquí
> es un **diagnóstico** —de dónde sale el hueco entre 29 y 34— y quien decide si
> la regla o el diseño es lo que está mal **es el propietario**, con los dos
> números delante. Si el resultado es espectacular, más motivo para no tocar
> nada: un número que mejora sin que el sistema cambie **no es una mejora**.

## Por qué la pregunta existe

La entrada 135 estableció que el sistema, a propósito, **entrega de más**: el
motor inyecta toda no-ordinaria del ámbito y el rescate la protege, para que no
se pierda ninguna crítica. Lo consigue: **cero omisiones críticas** en las cuatro
configuraciones, desde el 05-09.

Pero el banco puntúa `aciertos_exactos`: **el conjunto entregado tiene que ser
idéntico al esperado**. Un solo protegido de más mata el caso.

Es decir: **la regla penaliza al sistema exactamente por cumplir su contrato de
seguridad**. Eso no significa que la regla esté mal —puede ser que el contrato
esté mal, o que entregar de más sí sea un fallo real de cara al usuario—. Pero
significa que los dos números no miden lo mismo, y hasta hoy solo hay uno.

## Las cuatro preguntas

1. ¿En cuántos de los 47 casos **no falta nada** de lo esperado? (recuperación
   completa, sin mirar lo que sobra).
2. ¿En cuántos no falta nada **y todo lo que sobra es protegido**? Es decir:
   ningún fallo de recuperación, y el exceso es exactamente el que el diseño
   dice que va a meter a propósito.
3. ¿En cuántos no falta nada pero sobra algo **no** protegido? Ése es el exceso
   que **nadie ha decidido** y que sí es un defecto por cualquier regla.
4. ¿Cuánto vale ese exceso no decidido: cuántos elementos, en cuántos casos?

## Criterio de parada

- Si (2) es **mucho mayor** que `aciertos_exactos` y (3) es **pequeño**: el hueco
  entre 29 y 34 es sobre todo **exceso decidido**, y la pregunta que hay que
  llevarle al propietario es si su contrato de seguridad y su regla de medida se
  contradicen. **Se le lleva como pregunta, no como propuesta.**
- Si (3) es **grande**: hay exceso que nadie decidió, es defecto por cualquier
  regla, y **ése** es el trabajo — no la métrica.
- Si (1) ya es bajo: el sistema falla recuperando, la discusión sobre el exceso
  es secundaria y esta investigación no lleva a ningún lado.

**Regla dura**: no se toca el banco, ni `resultado_esperado`, ni el corpus, ni el
fixture, ni ninguna métrica del arnés. Esto **lee y cuenta**. No se lee
`criticidad.razon_segura`. Y ninguna cifra de aquí se publica sin la frase «no se
propone cambiar la métrica» al lado.

## Predicción, escrita antes de medir

1. **(1) será alto**: 42-45 de 47 en `--ejes --peticion`. Razón: ya está medido
   que la búsqueda trae el esperado entero en 45/47.
2. **(2) rondará 33-36**, o sea **no muy por encima del techo real ya conocido**.
   Razón: el techo real se calculó con un filtro perfecto que conserva justo lo
   esperado, y la diferencia entre eso y (2) es solo el exceso **no** protegido
   que el filtro perfecto sí habría tirado. Le doy un **60%**.
3. **(3) será grande, no pequeño**: predigo que en **10 casos o más** sobra algo
   no protegido, porque el motor mete 146 elementos de más en
   `--ejes --peticion` y solo 19 identidades del corpus son protegidas.

**Si acierto la 3, el resultado de esta nota es que la métrica no es el
problema** y la conversación sobre la portería se cierra sola, que es el
desenlace que prefiero. Si fallo la 3 y el exceso es casi todo protegido,
entonces sí hay una contradicción real entre el contrato y la regla, y es suya.
