# Evidencia — el interruptor de profundidad

Fecha: 2026-08-28. Nota de arranque:
`docs/audits/arranque-interruptor-de-profundidad.md`. Orden del propietario:
poder acotar la investigación a lo que pide («una investigación normal de
veinte o treinta fuentes» cuando no haga falta la profunda).

## Cómo queda

- «Investiga …» a secas → `research_report` (normal: 20-30 fuentes, ~5-10
  créditos del buscador, ~7 min).
- «Investiga **a fondo** / **en profundidad** / investigación **profunda** o
  **exhaustiva** …» → `deep` (~200 fuentes, ~40-60 créditos, ~25 min).
- El workflow pasa `--tipo auto` y el texto decide; un `--tipo` explícito
  sigue mandando. Ante la duda, NORMAL: equivocarse hacia barato se corrige
  repitiendo con «a fondo»; hacia caro, no.

## Las cuatro preguntas, con su mutación

| pregunta | prueba | mutación vista caer |
|---|---|---|
| 1a. a secas → normal | `test_una_orden_a_secas_va_en_normal` (argv del hijo real) | M2 (auto siempre profunda) |
| 1b. a fondo → profunda | `test_una_orden_a_fondo_va_en_profundo` | M1 (marcas vacías) |
| 2. sin tildes y en mayúsculas | `test_las_marcas_funcionan_sin_tildes_y_en_mayusculas` | M1 y M2 |
| 3. el documento dice el tipo REAL | el aserto de `…_el_veredicto_es_ready_…` — que además cazó un fallo de verdad: el documento recibía `args.tipo` («auto») en vez del calculado | — (cazado en rojo antes del commit) |
| 4. el workflow pasa `auto` | `test_el_ejecutor_deja_que_el_texto_decida_la_profundidad` | M3 |

## La familia vacua mordió DOS veces en esta rama, y queda contada

1. La mutación M3 reemplazó el «--tipo auto» del COMENTARIO del paso, no el
   del comando: mutación vacua, verde falso.
2. Corregida la mutación, el GUARDIÁN siguió verde: su aserto encontraba la
   cadena en ese mismo comentario, que vive dentro del bloque `run:`.

Es la tercera aparición de la familia en el día (el aserto del cambio de
modelo, el selector del veredicto, y esta). La receta aplicada es la ya
escrita en esta casa: **mirar solo el código, nunca los comentarios** — el
guardián filtra las líneas `#` del bloque antes de buscar, y la mutación
sustituye la línea exacta del comando con `count == 1` comprobado.

## Criterio de parada, revisado

- (a) Ante la duda, normal: cumplido por construcción (la lista de marcas es
  cerrada e intencional).
- (b) Dos rondas: las dos mordeduras de arriba son la MISMA familia en la misma
  rama → se aplicó la raíz (filtrar comentarios) en vez de un tercer parche, y
  la familia queda nombrada aquí para el día que pida un guardián general.
