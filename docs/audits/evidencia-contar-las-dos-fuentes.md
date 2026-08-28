# Evidencia — contar las dos fuentes

Fecha: 2026-08-28. Nota de arranque:
`docs/audits/arranque-contar-las-dos-fuentes.md`.

## La cadena que refuta el conteo viejo

| eslabón | evidencia |
|---|---|
| la clave llega | pasada 4 (run 33135502242): `TAVILY_API_KEY: ***` en el `env:` |
| el servidor contesta | atestado (run 33138475089): `buscador USABLE — 3 resultados`, misma llamada que la herramienta |
| y aun así fuentes=0 | desglose de la pasada 4: 5 de 7 a cero, idéntico a sin clave |
| por qué | `_search_relevant_source_urls` (0.15.1): resultado con contenido >100 chars → `research_sources`, nunca `visited_urls`; el medidor contaba solo `get_source_urls()` = `visited_urls` |

## Las cuatro preguntas, con su mutación

| pregunta | prueba | mutación vista caer |
|---|---|---|
| 1. lo pre-traído cuenta | `test_las_fuentes_pretraidas_cuentan_aunque_no_se_visitaran` | M1 (volver al conteo viejo) |
| 2. la unión deduplica | `test_una_url_en_los_dos_registros_cuenta_una_vez` | M2 (contar sin deduplicar) |
| 3. formas raras no cuentan ni revientan | `test_origenes_sin_url_no_cuentan_ni_revientan` | M3 |
| 4. todo vacío sigue siendo 0 | `test_con_todo_vacio_sigue_siendo_cero_y_la_regla_intacta` | M3 (fuente fantasma) |

M3 es el criterio de parada (a) hecho prueba: la corrección no desarma
`fuentes > 0` — con los dos registros vacíos la medición sigue sin ser fiable.

## La familia, nombrada (regla de las dos rondas)

Tres rojos-que-mienten en tres días, misma raíz: **el instrumento lee un
registro que no es el que habla**.

1. El preflight leyó un 503 como «muerto» (PR #374).
2. El verificador leyó una contradicción de etiquetas como «divergencia del
   motor» (PR #377, ADR-096).
3. El medidor leyó «fuentes=0» donde la herramienta tenía las fuentes en el
   otro registro (esto).

Queda dicho en la nota de arranque: al cuarto caso de esta familia no se
parchea — se rediseña la medición entera.
