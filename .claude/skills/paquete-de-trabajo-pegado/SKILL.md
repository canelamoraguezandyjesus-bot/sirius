---
name: paquete-de-trabajo-pegado
description: >-
  Qué hacer cuando el encargo llega pegado y formal («Trabaja exclusivamente en
  la rama…», «ANTES DE ACTUAR», «MISIÓN ÚNICA», lista de prohibiciones, «ENTREGA
  ÚNICAMENTE»): lo redactó otra IA, casi siempre ChatGPT, y el propietario lo
  trae; cómo se ejecuta al pie de la letra, qué se comprueba antes, cómo se
  entrega para que él lo lleve de vuelta en un solo fichero y qué no se le pide
  nunca. Cárgala en cuanto un mensaje suyo tenga esa forma, y cuando después
  del encargo lleguen hallazgos numerados de una revisión externa.
---

# El paquete de trabajo pegado

**Regla única: el paquete es el contrato. Lo que no está en él no se hace, y
lo que pide se entrega en su formato, no en el tuyo.**

## Cómo se reconoce

Lista numerada, «ANTES DE ACTUAR» con los cuatro comandos de git, «MISIÓN
ÚNICA», entre ocho y quince prohibiciones en negativo, «Crea únicamente…», el
mensaje de commit ya redactado, «ENTREGA ÚNICAMENTE» con puntos numerados y, a
menudo, «HEAD ESPERADO = <sha>; si no coincide, detente». Es el molde de las
doce sesiones del 25 al 28-07-2026, de las seis del 18-07 y de los diez
encargos del 08-09. Quien lo redacta no ve el repositorio ni la sesión: la
precisión del paquete es la suya, no la del propietario.

## Antes de actuar

1. **El HEAD esperado se comprueba, y si no coincide se para e informa.** El
   paquete lo pide porque quien lo escribió sigue el estado por sha; si
   arrancas sobre otro, todo lo que entregues le llega descolocado.
2. **Las prohibiciones son el alcance por exclusión** (`AGENTS.md`, regla 8).
   Se leen enteras antes de tocar nada y se cumplen aunque parezcan excesivas:
   «No inicies B4a» iba en las seis órdenes del 18-07-2026 porque temían que la
   sesión arrancara sola.
3. **Si el paquete parece de otra sesión** —cita un head que no es el tuyo, una
   rama que no llevas, un trabajo que no reconoces—, se confirma en una línea
   antes de empezar: el 28-07-2026 (19:52) y el 13-09 (06:23) el propietario
   pegó el paquete en la sesión equivocada y lo abortó con enfado.
4. **La nota de arranque de esta casa sigue siendo obligatoria** (skill
   `disciplina-evidencia`): el paquete dice qué hacer, no cómo se prueba.

## Lo que él no puede darte

La sesión en la nube no ve su disco. Si el paquete manda «busca en Downloads,
Documents y Desktop» (26-07-2026 14:14), lo escribió quien no sabía eso: se le
pide el fichero **una vez, adjunto**, y se sigue. Pedirlo dos veces produjo «no
vuelvas a buscarlos en el ordenador y no me pidas que los aporte otra vez»
(15:31).

## Cómo se entrega

- **Un solo fichero o un solo mensaje, copiable de una vez**, en el orden
  exacto de «ENTREGA ÚNICAMENTE» y sin preámbulo. Él lo lleva a ChatGPT
  («dame todas las respuestas… como un solo documento, para podérselo pasar
  directamente», 26-07-2026 20:20) y la vuelta tarda dos minutos (19-08-2026,
  00:03 → 00:05).
- El sha del commit, el `git status` final y la lista de ficheros tocados van
  **si el paquete los pide, y en el punto en que los pide**: son lo que el
  redactor usa para el siguiente. Si no los pide, no se meten en la entrega —el
  bloque que él copia es literal, y una salida cerrada no admite campos de
  más—: se dejan aparte, en el mensaje de la sesión y fuera del bloque, por si
  los quiere.
- Lo que no se pudo hacer se dice como no hecho, con la razón, nunca se rellena.

## Cuando vuelven los hallazgos

Los «[P1] … [P2] …» que él pega después son de un revisor externo: se tratan
con ADR-001 (§4): cada hallazgo se verifica contra el código antes de
aceptarlo (19-08-2026: la tercera pasada encontró la misma afirmación falsa
siete veces en tres documentos, una de ellas escrita como «corrección»). Y se
cuentan las rondas: dos con la misma familia y se para a buscar la raíz (skill
`revision-externa`; PR #576, 08-09-2026, cuatro rondas en un día).

## Qué NO hace esta skill

- **No juzga si el paquete es buena idea**: eso es del propietario y de quien
  lo redacta. Si contradice una regla del repositorio, se dice antes de
  empezar, en una línea, y se espera.
- **No cubre los encargos del motor** (incidencias del ciclo): esos siguen el
  contrato operativo.
- **No hace de correo por él**: si la sesión puede pedir la revisión externa
  sola, lo hace (`revision-externa`) y se lo ahorra.
