# Nota de arranque — el motor dice lo que hace: tres textos que mentían o callaban

Rama `claude/el-motor-dice-lo-que-hace`, fecha 01-10-2026 (la hora es la del
commit que la publica, y la lleva el ADR). El arreglo lleva escrito en una copia de trabajo desde
la madrugada, con sus pruebas en verde, y no se ha confirmado: lo que esta nota
fija antes de medir es qué se considera arreglado, con qué cifra, y qué haría
parar.

## Las tres piezas, con su cifra de partida

Las tres salen de la bitácora del ciclo (entradas 29, 100 y 146) y las midió la
mina de septiembre (`SIRIUS_MINA_APRENDIZAJE_OPERATIVO_2026-09-30.md`, §6.4)
sobre el volcado de la API de GitHub del mes:

1. **La línea `- PR:` del veredicto `CHANGES_REQUESTED` no se publicó ni una
   vez**: 0 de 128 veredictos en septiembre, 0 de 240 desde que existe. La
   causa, reproducida en bash: `printf '- PR: %s\n'` empieza por guion y bash
   lo lee como opción (`printf: - : invalid option`). El corrector que lee el
   veredicto no sabe en qué PR trabaja.
2. **El aviso de «listo para fusionar» pide una autorización que el motor ya no
   necesita**: desde ADR-205 (fusionado el 20-09 a las 18:09 UTC) el motor
   fusiona por aprobación dual. Antes de esa hora el texto era verdad (38 avisos
   en septiembre); después, 1 aviso (#653, 21-09 14:24) pidió «escribe
   **fusiona**» para algo que iba a pasar solo, y cada «listo» futuro lo
   repetiría.
3. **Una orden `continua` casi exacta sale en silencio** (`exit 0`, sin
   comentario): en septiembre pasó **1 vez** (#523, 04-09 15:57: «continua
   Decisión registrada: …»). Es un caso: demasiado pequeño para sostener una
   tasa, y se dice con esas palabras. Se arregla porque el coste de callar ante
   una orden del propietario no se mide en frecuencia: la parada queda sin
   explicación hasta que alguien mira el log del run.

## Las cuatro preguntas y la predicción

1. ¿La línea `- PR:` aparece en un veredicto generado por el guion arreglado?
   Predicción: sí, en la primera línea tras la cabecera, en los dos caminos
   (con y sin familia repetida).
2. ¿El aviso de «listo» deja de pedir autorización y dice lo que va a pasar?
   Predicción: sí, y conserva la salida de emergencia («si en una hora sigue
   sin fusionarse, escribe **fusiona**»).
3. ¿Una casi-orden recibe un comentario que diga por qué no se reanuda, y un
   comentario que no es una orden sigue sin respuesta? Predicción: sí a las dos;
   la segunda importa tanto como la primera, porque el bot publica como OWNER y
   un aviso que empezara por «continua» se dispararía a sí mismo.
4. ¿Cuánto cuesta? Predicción: tres ficheros de producción y cuatro pruebas;
   ningún workflow nuevo, ningún permiso nuevo.

## Criterio de parada (antes de medir)

- Si el cambio de texto del aviso de «listo» exigiera tocar la máquina de
  estados (etiquetas, transiciones) y no solo el texto, parar: eso es otra
  decisión.
- Si el aviso de casi-orden pudiera dispararse con un comentario del propio
  bot, no se entrega: el guion de reanudación solo escucha a `OWNER` y el bot
  publica como `OWNER`.
- Tres mutaciones tienen que caer: M1 el `printf` original de vuelta; M2 el
  texto de «autorización» de vuelta en el workflow; M3 la casi-orden sin aviso.
- Dos rondas de revisión externa con defectos de la misma familia → raíz.
