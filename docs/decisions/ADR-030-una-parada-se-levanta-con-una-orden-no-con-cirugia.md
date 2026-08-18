# ADR-030 — Todo estado de parada declara la orden que lo levanta

- Estado: PROPUESTO
- Fecha: 2026-08-18
- Aprobación: la fusión de la PR de esta rama por el propietario.

## Contexto y problema

El ciclo de A2 (incidencia #186, PR #189) llegó a su destino: 7 rondas de revisión doble, 7 de
corrección, 9 pasadas de Quality, y una implementación correcta al final. Pero **se detuvo tres
veces y las tres hizo falta una persona**:

1. **Un fallo de CI ajeno.** Quality falló por una prueba de GUI inestable
   (`test_streaming_message_grows_without_overlapping_neighbours`) que no tiene relación con A2:
   el corrector había pasado la suite entera en verde minutos antes (2529 passed). El corrector
   hizo **lo correcto** —no tocó una prueba ajena— y emitió `FIXED` sin empujar nada. Pero
   `FIXED` presupone un push.
2. **`ci-pending` sin motor.** Sin push no hay evento `pull_request`, sin evento no hay Quality,
   y `ci-pending` no es terminal: nadie avisa. 45 minutos parada hasta que una persona pulsó
   «Re-run failed jobs»; el run pasó a la primera sobre el mismo commit.
3. **`blocked-decision` irreversible.** Tras tres rondas en el par (1, 2) saltó `sin-progreso`,
   correctamente. El propietario autorizó una ronda más — y **no había forma de dársela a la
   máquina**: `decide()` mide sobre todo el historial publicado, así que reponer
   `sirius:repair-requested` habría vuelto a bloquear en el acto. La ronda se hizo a mano, fuera
   del ciclo.

Las tres paradas eran **correctas**. El defecto no está en pararse: está en que **la máquina sabe
pararse pero no sabe recibir una decisión**. Un estado que exige intervención humana y no declara
cómo recibirla es, en la práctica, irreversible — y convierte cada parada legítima en cirugía.

`reconcile-sirius-states.yml` cubre parcialmente el caso 2 (Caso B, cada 6 h), pero cuando
Quality está en rojo **solo avisa**, deliberadamente, para no recetar una corrección sin causa
demostrada. Latencia de 3 h y aun así manual.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque
([#190](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/190)), antes del primer
commit. Alcance: `sirius_convergence.py`, un ejecutor de orden nuevo, sus pruebas y este ADR; el
workflow disparador se entrega para pegar (ADR-002). **Parar si el arreglo exigiera relajar la
política** —bajar el listón, tolerar más rondas planas, o aplicar el reset sin orden explícita del
propietario—: eso sería quitar la salvaguarda en vez de darle una entrada. Pruebas verificadas por
mutación antes de darlas por buenas.

## Opciones consideradas

1. **Que `blocked-decision` se reanude solo tras un tiempo**: descartada, y es la tentación
   obvia. Si se reanudara, el ciclo de A2 habría seguido dando vueltas indefinidamente al
   problema de las claves de idempotencia. Ese estado existe para preguntar; un temporizador
   contesta por el humano, que es exactamente lo que no debe pasar.
2. **Relajar la política de convergencia** (más rondas planas toleradas): descartada. La política
   acertó las tres veces que bloqueó. El problema nunca fue su umbral.
3. **Que el humano edite la incidencia a mano** (lo que se hizo): descartada como solución. Exige
   conocer el formato interno de los marcadores y no deja rastro de quién autorizó qué.
4. **Una orden por comentario del propietario, con marcador de frontera**: elegida.

## Decisión

1. **`sirius_resume_on_command.sh`**: el propietario escribe la orden exacta `continua` en una
   incidencia en `sirius:blocked-decision`. El guion **reverifica todo por REST** —el evento
   describe el pasado, la decisión se toma sobre el presente—, publica el marcador
   `<!-- sirius-convergence-reset:<head> -->` y solo **después** repone la etiqueta disparadora.
   Es el patrón de `sirius_merge_on_command.sh`, adaptado: no se inventa nada.
2. **`history_after_last_resume()`** en `sirius_convergence.py`: la medida de convergencia empieza
   después del último marcador. **Corta el texto, no lo filtra**, y por eso reinicia los DOS
   motores del ciclo —rondas de revisión y racha de Quality en rojo— con una sola regla.
   Reiniciar solo uno dejaría al otro condenando el trabajo recién autorizado.
3. **El historial no se borra.** Las rondas anteriores siguen publicadas y auditables; solo dejan
   de servir de listón. Una parada por `sin-progreso` vuelve a saltar en cuanto haya dos rondas
   planas *posteriores* al marcador, con el mismo criterio.
4. **El orden de las escrituras es parte de la decisión**: primero el marcador, luego la etiqueta.
   Al revés, el corrector podría arrancar, leer un historial todavía sin marcador y volver a
   bloquear — y el propietario vería su orden rechazada por la misma parada que acababa de
   levantar.
5. **Regla general que este caso deja escrita**: *todo estado que exige una decisión humana
   declara la orden que lo levanta*, y una prueba lo exige recorriendo la lista de estados de
   parada. Un estado nuevo no puede nacer sin salida.

## Comprobación que la sostiene

- **Prueba por mutación (ADR-001 §3)**, en las dos direcciones:

  | Mutación | Resultado |
  |---|---|
  | el corte no corta (devuelve el texto entero) | **fallan 3**: la orden deja de tener efecto |
  | el corte borra siempre todo el historial | **fallan 3**: la política dejaría de bloquear nunca |
  | cuenta la primera orden en vez de la última | **falla 1**: `test_solo_cuenta_la_ultima_orden` |
  | cambiar la orden exacta en el guion | **falla** el invariante de estados de parada |
  | quitar la reverificación por REST | **falla** la prueba de reverificación |

  La segunda es la que importa de verdad: demuestra que las pruebas defienden **la salvaguarda**,
  no solo la funcionalidad nueva. Sin ella, `history_after_last_resume` sería una forma elegante
  de desactivar la política de convergencia.
- Diagnóstico de las tres paradas tomado del ciclo real de #186, con sus horas y sus runs, no
  reconstruido.

## Consecuencias

- Levantar una parada pasa de media hora de cirugía a **una palabra**, con rastro de quién la
  autorizó y sobre qué head.
- **`blocked-decision` sigue sin reanudarse solo, y es deliberado.** El objetivo no era «cero
  humanos»: era que la decisión que el sistema pide tenga por dónde entrar.
- **Lo que esto NO cubre**: los casos 1 y 2 siguen abiertos. Necesitan un veredicto nuevo del
  corrector —«las comprobaciones fallaron por algo que no es mío, reejecútalas»— para que un
  `FIXED` sin push no deje la incidencia esperando un evento que nadie va a emitir. Va en una
  entrega posterior; queda registrado como decisión pendiente, no como defecto olvidado.
- **Debilidad conocida y declarada**: la orden repone `sirius:repair-requested`, que es la
  etiqueta que retira esta parada concreta. Un estado de parada futuro con otra etiqueta
  disparadora necesitará su propia rama en el ejecutor; la prueba de invariante obligará a
  añadirla, pero no la escribe sola.

## Alternativas descartadas y por qué

Las cuatro de arriba. Además: **borrar los registros de ronda anteriores** en vez de cortar el
historial — descartada, porque destruye la auditoría justo del ciclo que hizo falta revisar, y
porque un marcador de frontera dice lo mismo sin perder nada.
