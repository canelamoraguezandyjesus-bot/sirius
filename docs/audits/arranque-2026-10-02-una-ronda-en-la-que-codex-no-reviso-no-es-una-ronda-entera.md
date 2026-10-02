# Nota de arranque — una ronda en la que Codex no revisó no es una ronda entera

Rama `claude/una-ronda-sin-codex-no-es-una-ronda-entera`. Fecha: 02-10-2026,
06:15 UTC. Seguimiento de ADR-226 (PR #673): lo que la revisión independiente
de esa PR encontró después de fusionarla. Escrita antes de tocar el agregador,
la política de convergencia y el detector de familias.

## El suceso

ADR-226 (fusionado el 01-10-2026 a las 18:50 UTC) hace que, cuando Codex
declara que no revisa —cuota agotada, «Try again later»— y Claude pidió
cambios, la ronda entregue los hallazgos de Claude en vez de tirarlos. La
revisión independiente de la PR #673, leída después de la fusión, señaló lo que
ADR-226 no midió: esa ronda publica un `RONDA_HALLAZGOS` igual que una ronda
entera, y las dos piezas que leen el historial no saben que a esa ronda le
falta un revisor.

- `sirius_convergence.decide` compara conjuntos de huellas entre rondas. Una
  ronda solo de Claude tiene menos huellas que la anterior —las de Codex no
  están porque nadie las buscó—: cuenta como «progreso» falso; y cuando Codex
  vuelve, sus huellas «reaparecen»: `BLOCK` por `reaparicion` sin que nada
  haya regresado.
- `detectar_familia_repetida` cuenta rondas consecutivas por fichero: una
  ronda sin Codex en medio rompe el tramo de un fichero que Codex señala, y
  una familia real se queda sin aviso.

Ninguna ronda real ha pasado aún por este camino (desde la fusión de ADR-226
no ha habido trabajo vivo en el motor), así que la cifra de partida es la de
la bitácora: 13 paradas por cuota en septiembre (entrada 106), que desde
ADR-226 serían rondas solo de Claude; y la cuota de Codex se agotó dos veces
el 01-10 (14:07 y 19:44 UTC), así que el camino se va a usar.

## Las cuatro preguntas, con la predicción escrita antes de medir

1. **¿Reproduce una prueba el falso `BLOCK`?** Predicción: sí. Tres rondas
   sintéticas —entera, solo Claude con los mismos hallazgos de Claude, entera
   otra vez con los mismos hallazgos de Codex— dan `BLOCK` `reaparicion`
   contra el código de `main`; con el cambio, `CONTINUE`.
2. **¿Reproduce una prueba el tramo roto?** Predicción: sí. Un fichero
   señalado por Codex en las rondas 3, 5 y 6 con la 4 solo de Claude: hoy no
   hay familia; con el cambio, familia con tres apariciones.
3. **¿Qué cambia?** El veredicto agregado y el registro de ronda llevan
   `reviewers`; `decide` compara cada ronda solo con rondas que tengan al menos
   sus mismos revisores, proyectadas a esos revisores; el detector trata una
   ronda parcial como transparente para los ficheros que no aparecen en ella.
   Los registros anteriores, sin `reviewers`, se leen como enteros: nada cambia
   para el historial que ya existe.
4. **¿Qué no cambia?** La regla de ADR-226 (Claude lleva la ronda; nada se
   aprueba sin Codex), la medida de progreso contra la mejor marca histórica
   entre rondas enteras, el umbral de tres del detector, los avisos y los
   marcadores.

## Criterio de parada (escrito ANTES de ver resultados)

- Las dos pruebas de la predicción tienen que verse fallar contra `main` y
  pasar con el cambio; las baterías de convergencia, agregador, detector y
  aplicador de veredictos siguen en verde sin tocar ninguna prueba existente
  salvo para añadir `reviewers` donde haga falta.
- Mutaciones que tienen que caer: M1 el registro sin `reviewers`; M2 `decide`
  sin proyectar (compara todo con todo); M3 `decide` sin omitir las rondas
  parciales cuando la actual es entera; M4 el detector sin transparencia; M5
  el agregador manda también las observaciones de Codex en una ronda que
  Codex no revisó.
- Si para evitar el falso `BLOCK` hiciera falta cambiar la definición de
  progreso entre rondas enteras, parar: es otra decisión, sobre la política y
  no sobre las rondas parciales.
- H-231 registrada; la guarda del registro vista caer antes y pasar después.
- De paso, y sin medición propia: los defectos de prosa de ADR-226 que la
  misma revisión listó (ADR-146 citado donde tocaba ADR-060, un «presupuesto
  de rondas» que no existe, su nota de arranque sin la palabra «fecha»).
