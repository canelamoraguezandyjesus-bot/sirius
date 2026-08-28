# Nota de arranque — H-26: LOST no libera la cancelación sin confirmar

Fecha: 2026-08-28. ANTES del primer cambio (ADR-001). Corrección autorizada.

## Afirmación a corregir (verificada en #396)

`mark_lost` conserva `cancellation_status=UNCONFIRMED` pero
`has_unconfirmed_cancellation` exige estado vivo, y esa propiedad es la ÚNICA
exclusión del recurso mutable en los dos stores. Un Worker quizá vivo deja de
bloquear al sustituto en cuanto el Run cae a LOST por plazo.

## Lo que se decide construir

1. La propiedad deja de exigir estado vivo: peligro = `UNCONFIRMED`, punto. El
   estado del ciclo y el estado del peligro son ortogonales (la misma lección
   que `mark_scope_invalidated` dejó escrita en este fichero).
2. La única liberación es EXPLÍCITA: `release_unconfirmed_cancellation`, legal
   solo desde FINISHED(LOST) con UNCONFIRMED, que limpia el peligro SIN tocar
   estado ni desenlace (no resucita Runs, no debilita CANCELLED). Quien la
   llame tiene que traer la prueba (terminal remoto o aislamiento), que es
   exactamente lo que dice la arquitectura §3.3.
3. `confirm_cancelled` no cambia: sigue siendo el camino de los Runs vivos.

## Las preguntas

1. ¿La prueba nueva se ve FALLAR: LOST+UNCONFIRMED ya no bloquea hoy el
   despacho de un sustituto sobre el mismo recurso? (memoria Y durable)
2. ¿La liberación explícita desbloquea, y solo desde LOST+UNCONFIRMED?
3. ¿`retry`/`substitute_worker` arrastran `recurso_mutable` (leído: sí), de
   modo que el bloqueo muerde en el `dispatch_run` del sustituto?
4. ¿El camino del supervisor queda cubierto: su sustitución sobre el mismo
   recurso falla con `MutableResourceConflictError` y el barrido no revienta?

## Criterio de parada

- (a) Si la liberación pudiera ocurrir sola (por tiempo, por barrido), se
  para: sería el mismo defecto con más pasos.
- (b) Si algún camino legítimo de HOY dependiera de que LOST libere (alguna
  prueba existente en verde lo diría), se para y se trae aquí antes de romperlo.
- (c) Dos rondas (ADR-001).
