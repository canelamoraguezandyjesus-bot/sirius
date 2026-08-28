# Evidencia — H-30: la admisión es una reserva atómica

Nota de arranque: `docs/audits/arranque-h30-presupuesto-atomico.md`. Auditoría #396.

## Las preguntas, con su comprobación

| pregunta | comprobación | mutación vista caer |
|---|---|---|
| 1. dos al borde no pasan las dos | `test_h30_dos_reservas_que_juntas_exceden_no_pasan_las_dos`, vista FALLAR antes (`reservar` no existía) | M1 (ignorar lo en vuelo) |
| 2. la reserva nunca queda colgada y el coste real queda | `..._al_salir_del_with_...` y `..._reserva_abandonada_...` (con excepción a mitad) | M2 (el with deja de soltar): 2 caen |
| (b) una petición sola conserva el pacto | `..._una_peticion_sola_se_admite_con_la_regla_de_siempre` | M3 (endurecerla): cae |
| 3. los tres carriles, la misma primitiva | `..._los_tres_carriles_usan_la_misma_primitiva` (líneas de CÓDIGO de los call sites de producción) | M1 la tumba también |
| 4. mes y reinicio como antes | el total persistido no cambió de forma; las baterías de repositorio y estado siguen en verde |

## La regla de admisión, escrita para que no se malinterprete

- Sin nada en vuelo: `spent < limit` — EXACTAMENTE la de siempre (DR-018).
- Con reservas vivas: `spent + en_vuelo + estimado <= limit` — quien llega con
  otras en vuelo demuestra que CABE JUNTA.

Estimados por carril: transcripción = techo de la captura (`maximum_seconds`,
cota superior conocida ANTES); síntesis = caracteres exactos; texto = longitud
del prompt (~4 car./token) + `max_output_tokens` configurado. El coste REAL lo
apuntan los `record_*` de siempre DENTRO del `with`: una sola forma, sin
segunda API de asiento que pueda divergir.

`has_remaining_budget` queda como AVISO (la cortesía antes de abrir el
micrófono y los indicadores), nunca como puerta.

## Alcance declarado (criterio (a))

La atomicidad cubre EL PROCESO: la aplicación de escritorio es uno, y texto y
voz conviven ahí — que es el escenario del hallazgo. Cubrir varios procesos
sería una reserva en el repositorio: queda como límite declarado, no fingido.

## La familia vacua, cuarta mordedura del día

El guardián de los carriles contó una aparición del docstring del propio
ayudante como si fuera un tercer carril. Receta de siempre: contar LÍNEAS de
código, no subcadenas. Queda anotado con las otras tres de hoy.
