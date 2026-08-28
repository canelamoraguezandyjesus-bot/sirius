# Evidencia — H-26: LOST no libera la cancelación sin confirmar

Nota de arranque: `docs/audits/arranque-h26-lost-no-libera.md`. Auditoría #396.

| pregunta | comprobación | mutación vista caer |
|---|---|---|
| 1. LOST+UNCONFIRMED bloquea al sustituto | `test_h26_un_run_perdido_..._sigue_bloqueando`, vista FALLAR antes (6 rojas: 3 pruebas × memoria/durable) | M1 (la propiedad vuelve a exigir vivo): 4 caen |
| 2. la liberación explícita desbloquea, y solo desde LOST | `..._la_liberacion_explicita_desbloquea_sin_reescribir` y `..._no_es_legal_desde_un_run_vivo` | M2 (legal desde vivo): 2 caen |
| — no reescribe la historia | el mismo par: desenlace sigue LOST | M3 (resucita a CANCELLED): 2 caen |
| 3. el reintento hereda el recurso | aserto dentro del camino del supervisor | — (leído y asertado) |
| 4. el camino del supervisor | `..._el_camino_del_supervisor_queda_bloqueado_en_el_despacho`: `retry_run` deja PREPARED y `dispatch_run` -el momento en que un Worker arrancaría- muerde; tras liberar, despacha | cubierto por M1 |

Criterio de parada (a): nada libera solo —la liberación es un método que exige
LOST+UNCONFIRMED y ningún camino automático lo llama; el almacén ni siquiera
puede comprobar la prueba (§3.3) y por eso no lo intenta—. Criterio (b): la
batería completa del motor (956) en verde: ningún camino legítimo dependía de
que LOST liberase.

Suceso nuevo `run_cancellation_released` añadido al vocabulario de eventos; el
diario guarda instantáneas, así que el replay no necesita lógica nueva
(comprobado con la batería durable en verde).
