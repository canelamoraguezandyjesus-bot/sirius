# Nota de arranque — `continua` sobre una parada anterior a la PR no anuncia en verde lo que la puerta va a rechazar

Rama `claude/continua-sin-planned-no-anuncia-en-verde`, fecha 01-10-2026 (la
hora es la del commit que la publica, y la lleva el ADR). Publicada **antes del
primer commit de arreglo**, como exige ADR-001.

## El suceso

Cuando una incidencia se para **antes de producir rama ni PR**, `continua`
repone la etiqueta de la fase que se paró (`sirius:implement-requested`) y
publica «🟢 Reinicio autorizado por el propietario». La activación exige
**dos** etiquetas, `sirius:planned` e `implement-requested`, y `planned` se
consumió en la primera activación: la puerta rechaza nueve segundos después
(«⛔ Activación rechazada (`sin-planned`)… ninguna automatización puede
añadirla por ti»), retira `implement-requested`, y la incidencia queda **sin
ninguna etiqueta**, inerte y muda (bitácora del ciclo, entrada 126; deuda 36;
mina del 30-09, §6.4).

Medido en el volcado de septiembre: **9 reinicios sin PR**, y **3** de ellos
seguidos de un rechazo `sin-planned` (#545 el 05-09, #581 el 11-09, #653 el
20-09). Uno de cada tres reinicios anunció en verde una reanudación que se
rechazó sola.

## Las cuatro preguntas y la predicción

1. ¿Puede el reinicio saber antes de anunciar si la puerta lo va a rechazar?
   Predicción: sí, mirando las mismas etiquetas que ya lee para decidir la
   parada: si la fase de destino es la activación y `sirius:planned` no está,
   la puerta va a rechazar, siempre.
2. ¿Qué hace entonces? Predicción: no repone nada ni consume la parada;
   publica una vez, con marcador, que no reanuda y por qué, y qué gesto hace
   falta (`sirius:planned`, que solo pone una persona) antes de volver a
   escribir `continua`. No empieza por «continua».
3. ¿Añade `planned` el propio reinicio? Predicción: no. Que `planned` sea un
   gesto humano es deliberado (puerta de activación, #60) y esta rama no lo
   cambia: si el propietario quiere que su `continua` valga como `planned`,
   es una decisión suya y va a la hoja de decisiones.
4. ¿Cuánto cuesta? Predicción: una comprobación en el camino `sin_pr` del
   guion de reanudación y tres pruebas que lo ejecutan de verdad con el doble
   de `gh`; los casos existentes de reinicio sin PR pasan a sembrar `planned`,
   porque sin él nunca pudieron funcionar de verdad.

## Criterio de parada (antes de medir)

- El reinicio **no añade `sirius:planned`** ni ninguna etiqueta que la puerta
  reserve a una persona.
- Con `planned` presente, el reinicio sin PR se comporta exactamente como hoy.
- El aviso de «no reanudo» no puede empezar por «continua» (el bot publica como
  `OWNER` y el workflow volvería a leerlo).
- Tres mutaciones tienen que caer: M1 el reinicio deja de mirar `planned`;
  M2 el aviso consume la parada; M3 con `planned` presente el reinicio deja
  de reponer la fase.
