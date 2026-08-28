# Nota de arranque — H-30: comprobar y gastar en una sola operación

Fecha: 2026-08-28. ANTES del primer cambio (ADR-001). Corrección autorizada.

## Afirmación a corregir (verificada en #396)

`has_remaining_budget()` (lectura) y `record_*` (escritura) son operaciones
separadas: dos peticiones concurrentes al borde del tope leen las dos el mismo
saldo, se envían las dos, y el límite mensual deja de ser una cota.

## Lo que se decide construir

Una RESERVA atómica en el tracker: `reservar(estimado_usd)` decide la admisión
bajo el candado contando gastado + reservas vivas; `liquidar(reserva)` la
suelta y apunta el coste real. La misma primitiva para los tres carriles:

- **Transcripción**: el estimado es casi exacto (los segundos de audio se
  conocen ANTES de llamar).
- **Síntesis**: igual (los caracteres se conocen antes).
- **Texto**: entrada estimada por longitud del prompt (~4 caracteres/token) y
  salida por el `max_output_tokens` ya configurado (4096): una cota superior
  honesta, no un número mágico.

`has_remaining_budget()` se conserva para el aviso previo (`is_near_limit` y
compañía), pero la ADMISIÓN pasa a la reserva.

## Las preguntas

1. ¿La prueba se ve FALLAR hoy: dos admisiones cuyo estimado conjunto excede
   el remanente NO pueden pasar las dos? (hoy el método no existe / el doble
   con el API viejo las deja pasar)
2. ¿La liquidación ajusta al coste real (mayor o menor que el estimado) y la
   reserva nunca queda colgada, ni siquiera si la petición revienta?
3. ¿Los tres carriles usan la MISMA primitiva? (se comprueba en los call sites
   con un tracker falso que registra reservar/liquidar)
4. ¿Sobrevive al mes y al reinicio igual que antes? (el total persistido no
   cambia de forma; las reservas viven en el proceso)

## Criterio de parada

- (a) Alcance honesto declarado: la atomicidad cubre EL PROCESO (la app de
  escritorio es un proceso; texto y voz conviven ahí). Si hiciera falta
  cubrir varios procesos, es otra pieza (reserva en el repositorio) y se
  declara como límite, no se finge.
- (b) La reserva no puede convertir el tope en más restrictivo de lo pactado
  para UNA petición sola: con presupuesto virgen, una petición cuyo estimado
  exceda el remanente entero se admite si el remanente es > 0… NO: se admite
  exactamente con la regla de siempre (`spent < limit`), y la reserva solo
  añade el conteo de lo EN VUELO. Una petición sola se comporta como hoy.
- (c) Dos rondas (ADR-001).
