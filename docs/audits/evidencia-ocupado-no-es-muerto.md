# Evidencia — «Ocupado» no es «muerto», y confundirlos cuesta lo mismo

Rama `ocupado-no-es-muerto`, 27-08-2026. Sin ADR: corrige un defecto del
instrumento que ADR-095 ya gobierna.

## Cómo se encontró: el propio guardián, en su primera pasada real

La primera vez que el banco se ejecutó de verdad, se paró antes de gastar cuota.
Correcto. Pero el motivo era éste:

```
===== RESUMEN =====
google   OK     50 modelos
         NO RESPONDE gemini-3.5-flash  ->  HTTP 503:
             "This model is currently experiencing high demand."
         USABLE     models/gemini-embedding-001
nvidia   OK     84 modelos
         USABLE     nvidia/llama-nemotron-embed-vl-1b-v2
         USABLE     nvidia/nemotron-3-nano-30b-a3b
```

**503 es «ocupado», no «muerto».** Y el guardián lo etiquetó `NO RESPONDE`, que
en este repositorio significa *cambia el modelo*.

Es el defecto de siempre **visto del revés**: en vez de un verde que miente, un
**rojo que miente**. Y cuesta exactamente lo mismo, porque manda a buscar un
sustituto que no hacía falta — que es como se perdió una noche entera.

## El arreglo

Tres estados en vez de dos:

| estado | qué significa | qué hacer |
|---|---|---|
| `USABLE` | contestó | medir |
| `OCUPADO` | 429, 500, 502, 503, 504… | **esperar**. No cambies el modelo |
| `NO RESPONDE` | 400, 401, 403, 404 | ese modelo no sirve para esta cuenta |

Y lo transitorio se reintenta tres veces con espera creciente y corta: si el
proveedor está saturado de verdad, insistir más no lo desatasca.

El aviso lo dice con todas las letras —*«transitorio: NO cambies el modelo,
vuelve a probar»*— porque sin esa frase quien lea el rojo hará lo de siempre.

## Mutación

| mutación | prueba que cae |
|---|---|
| el 503 vuelve a ser definitivo | `test_un_503_no_se_confunde_con_un_modelo_muerto` |
| se reintenta todo, incluido un 404 | `test_lo_transitorio_se_reintenta_y_lo_definitivo_no` |
| el aviso deja de decir «no cambies el modelo» | `test_el_informe_distingue_tres_estados_y_no_dos` |

La segunda prueba **cuenta las llamadas** en vez de leer la constante: comprobar
que 503 está en una lista no demuestra que se reintente.

## Lo que NO cambia

Un `OCUPADO` **sigue impidiendo medir**. Ante la duda se para, igual que antes.
Lo único que cambia es que ahora dice la verdad sobre por qué.

## Validaciones

```
ruff format --check .    -> 0
ruff check .             -> 0
mypy src tests           -> 0
pytest tests/automation  -> ver PR
git diff --check         -> 0
```
