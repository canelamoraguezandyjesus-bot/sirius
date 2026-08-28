# Evidencia — H-29: la intención durable antes del efecto externo

Nota de arranque: `docs/audits/arranque-h29-intencion-antes-del-efecto.md`.
Auditoría #396.

## Las preguntas, con su comprobación

| pregunta | comprobación | mutación vista caer |
|---|---|---|
| 1. la reproducción del informe | `test_h29_una_caida_tras_crear_no_duplica_al_reintentar`, vista FALLAR ANTES con el mensaje exacto «el reintento creó OTRA incidencia (total 2)». El «reinicio» es real: el diario durable se recarga desde su fichero | M1 (la intención se graba después del efecto): 3 caen |
| 2. las tres ventanas convergen | caída tras crear → adopta la 101; caída antes de crear → busca, no encuentra, crea UNA; todo contado por ESCRITURAS del escritor falso | M2 (crear sin buscar): 3 caen |
| 3. la adopción exige el work_id | el escritor falso solo devuelve la incidencia cuyo cuerpo lleva `## Work ID\n\n<work_id>`; el adapter real busca ese literal en el listado REST (no en el buscador, que indexa con retraso y fallaría justo tras crear) | — |
| 4. el camino feliz no cambia | los verbos registrados del doble enumerado siguen iguales; el doble ahora registra también `buscar…` y las pruebas C2/C3/C4/B1 sin tocar salvo el doble | M3 (la adopción no re-etiqueta): caen las 2 de H-29 Y las 10 del camino feliz — la etiqueta es compartida, quitarla rompe todo, como debe |
| (a) búsqueda rota → nada nuevo | `test_h29_si_la_busqueda_de_adopcion_falla_no_se_crea_nada` | M2 también la tumba |

## El puerto y sus guardianes, tratados como mandan

`GitHubWriterPort` tiene una prueba estructural que existe para OBLIGAR a
justificar un verbo nuevo. Se cumplió: `buscar_incidencia_por_work_id` entra
como LA lectura de adopción, con la justificación en su docstring, y los dos
guardianes (puerto y adapter real) se actualizan nombrando H-29. Sigue sin
haber tercer verbo de escritura.

## Criterio de parada, revisado

- (a) cumplido y probado: búsqueda rota → excepción → ninguna incidencia.
- (b) la intención NO sustituye a la reserva ni a la concurrencia del workflow:
  `test_dos_hilos_concurrentes_…` sigue en verde con la envoltura delegando.

Batería del motor completa: 951 en verde.
