# Evidencia — atestar al buscador antes de gastar en medirlo

Fecha: 2026-08-28. Nota de arranque:
`docs/audits/arranque-atestar-al-buscador.md`.

## Lo que motiva (medido)

Pasada 4 del banco (run 33135502242): `TAVILY_API_KEY: ***` visible en el `env:`
del paso —la clave existe y llega— y las fuentes idénticas a la pasada sin
clave (0,3 de media, 5 de 7 preguntas a cero). El buscador nuevo no aportó nada
y ningún instrumento decía por qué.

## Las cuatro preguntas, contestadas ejecutando

| pregunta | prueba | mutación vista caer |
|---|---|---|
| 1. 200 con resultados → USABLE | `test_el_buscador_con_resultados_es_usable` | M1 (401 pasa a usable) |
| 2. transitorio → OCUPADO, nunca muerto | `test_un_transitorio_del_buscador_es_ocupado_y_no_muerto` | M2 |
| 3. rechazo → NO RESPONDE con el cuerpo visible | `test_un_rechazo_del_buscador_ensena_la_respuesta_del_servidor` | M1 |
| 3b. 200 con CERO resultados no es usable | `test_un_200_sin_resultados_no_es_usable` | M1 |
| 4. main escucha al buscador en su código de salida | `test_el_veredicto_del_preflight_escucha_al_buscador` (ejecuta `main` real) | M3 |
| (forma) la llamada reproduce a la 0.15.1 | el arnés común comprueba cabecera="" y `api_key` en el cuerpo | M4 (mandar `Authorization: Bearer` tumba 4 pruebas) |

M4 es la que protege el sentido del atestado: si la petición llevara la cabecera
que la herramienta NO manda, estaríamos atestando otra llamada distinta de la
que falla.

`sin_clave` no pone rojo nada (criterio de parada (b)): comprobado ejecutando
`main` real con proveedores en verde fingido y el buscador sin clave → código 0.

## Dónde queda cableado

- `medir-investigador.yml`, paso de atestado: ahora recibe `TAVILY_API_KEY` y
  su mensaje de error nombra también al buscador. Buscador caído = el banco no
  gasta sus 25 minutos.
- `preflight-investigador.yml`: el preflight a mano también lo atesta, que es la
  vía barata para obtener la respuesta del servidor sin correr el banco.
