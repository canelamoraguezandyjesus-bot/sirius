# Evidencia — implementar el descarte de ADR-098

Fecha: 2026-08-28. Nota de arranque:
`docs/audits/arranque-implementar-el-descarte.md`.

## Lo que obligó (medido)

Pasada 5 (run 33139753661): el atestado paró la pasada en 5 segundos, cero cuota
gastada, porque `gemini-3.5-flash` está en `429: You exceeded your current
quota` (visto entero en el preflight run 33138475089). La cuota se la comieron
sus dos pasadas fallidas: un descarte decidido y no implementado es una factura
recurrente, y su agotamiento bloqueaba también la medición de NVIDIA.

## Las cuatro preguntas, con su mutación

| pregunta | prueba | mutación vista caer |
|---|---|---|
| 1. una declarada y medida → MEDIDA ÚNICA, código 0, y el motivo dice «NO compara» | `test_una_sola_declarada_y_medida_es_medida_unica` (main real, hijo real) | M1 |
| 2. una declarada y NO medida → código 2 | `test_una_sola_declarada_pero_no_medida_sigue_sin_valer` | M2 (MEDIDA ÚNICA con cero medidas) |
| 3. con dos declaradas, veredicto viejo intacto | `test_con_dos_declaradas_el_veredicto_viejo_queda_intacto` | M1/M2 no la tocan: pasa en las dos |
| 4. el atestado sigue mandando | sin cambios: `modelos_sin_atestado` no mira cuántas configuraciones hay; sus pruebas existentes siguen verdes | — |

Y las guardas de coherencia entre ficheros, que son donde el descarte podía
quedarse a medias:

| guarda | mutación vista caer |
|---|---|
| el paso del atestado nombra a cada proveedor declarado | M3 (nombrar a otro) |
| workflow y configuraciones declaran las mismas claves | M4 (devolver el bloque de google) tumba TRES pruebas |

## Criterio de parada (b), cumplido

La propiedad anti-contaminación se probaba con la configuración de Google del
fichero real; quitarla no se llevó la prueba: ahora usa una configuración DE
LABORATORIO que no declara `OPENAI_BASE_URL`, y sigue ejecutando el subproceso
real con el centinela en el entorno del padre.

## La revancha, por si alguien la busca aquí

Está escrita en ADR-098. Ejecutarla es revertir el commit de esta rama que toca
`configuraciones.yml`, no reescribir nada.
