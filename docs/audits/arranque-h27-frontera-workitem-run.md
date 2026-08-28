# Nota de arranque — H-27: la frontera WorkItem–Run

Fecha: 2026-08-28. ANTES del primer cambio (ADR-001). Corrección autorizada.

## Afirmación a corregir (verificada en #396)

Las dos máquinas locales son estrictas, pero la frontera no: `prepare_run` no
exige que el WorkItem padre exista ni que no sea terminal, y
`deliver_work_item` no mira si quedan Runs vivos. Estados individualmente
válidos combinan en un estado global inválido (padre entregado con intentos
vivos; hijos de un padre cancelado).

## Lo que se decide construir (los criterios del informe, tal cual)

1. `prepare_run` (y por transitividad `dispatch_run`) rechaza `work_id`
   inexistente o padre en estado terminal, en LOS DOS stores.
2. `deliver_work_item` rechaza la entrega si existe cualquier Run vivo del
   WorkItem, o uno con peligro de cancelación pendiente (la propiedad de
   H-26 ya cuenta LOST+UNCONFIRMED).
3. La fixture de `test_journal_replay` que legalizaba la combinación inválida
   pasa a una secuencia válida; el replay CONSERVA la capacidad de leer
   historia (los diarios existentes no traen esa combinación: lo que hay en
   producción son planned/active sin Runs).

## Las preguntas

1. ¿Las pruebas nuevas se ven FALLAR hoy, en memoria Y durable, en las DOS
   direcciones (padre terminal con hijo nuevo; entrega con hijo vivo)?
2. ¿Un padre PAUSADO admite preparar? El contrato del informe dice «padre
   valido y en curso»: se toma ESTADOS_EN_CURSO como criterio (ACTIVE, WAITING
   y PAUSED cuentan como en curso; los terminales y NEEDS_DECISION... hay que
   LEER la definición del dominio y decidir con ella delante, no de memoria).
3. ¿La entrega con el peligro de H-26 activo (LOST sin confirmar) se rechaza?
4. ¿El replay de historia existente sigue funcionando?

## Criterio de parada

- (a) Si alguna prueba existente en verde dependiera de crear Runs sin padre
  (más allá de la fixture señalada por el informe), se trae aquí ANTES de
  romperla y se decide con ella delante.
- (b) Dos rondas (ADR-001).
