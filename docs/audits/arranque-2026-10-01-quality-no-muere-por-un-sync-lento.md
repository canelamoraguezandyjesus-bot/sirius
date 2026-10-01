# Nota de arranque — Quality no muere por un `uv sync` sin caché

Rama `claude/quality-no-muere-por-un-sync-lento`, fecha 01-10-2026, la hora del
commit que la publica. Publicada **antes del primer commit de arreglo**, como
exige ADR-001; las cifras «con el arreglo» de abajo son predicciones, y el ADR
que salga dirá cuánto se desviaron.

## El suceso

Tres ejecuciones de Quality canceladas esta mañana por el tope de 20 minutos
del job, sobre dos PR distintas, con el paso «Sync environment» entre 11 y 16,5
minutos. Leído de la API de Actions (pasos de cada job):

| Hora (UTC) | Rama (PR) | Sync environment | Pytest | Desenlace |
|---|---|---|---|---|
| 07:52 | `claude/el-motor-dice-lo-que-hace` (#666) | 15 m 46 s | cancelado a los 3 m 57 s | cancelled |
| 08:10 | `claude/la-cola-regenera-la-memoria` (#667) | 16 m 30 s | cancelado a los 3 m 12 s | cancelled |
| 08:15 | `claude/el-motor-dice-lo-que-hace` (#666) | 11 m 47 s | cancelado a los 7 m 54 s | cancelled |
| 08:01 | `claude/mina-de-septiembre-entero` (#665) | 8 m 0 s | 10 m 28 s | success, 19 min en total |

Con la caché de `setup-uv` restaurada, el mismo paso tarda **2-4 s** (las otras
ocho ejecuciones de hoy). El registro de la ejecución de las 08:29 (PR #668,
también sin caché) dice qué hace el paso cuando no la tiene: descarga 58
paquetes, 243 MiB solo de PySide6 (`pyside6-addons` 167 MiB,
`pyside6-essentials` 76 MiB), «Prepared 58 packages in 8m 26s». A menos de
1 MB/s desde PyPI, el presupuesto entero del job se va en descargar.

## Las cuatro preguntas, con la predicción escrita antes de medir

1. **¿Por qué se cancela?** Predicción: no es la batería (hoy 9-10,5 min) sino
   el `uv sync` sin caché; con 20 min de tope, descarga + ruff + mypy + pytest
   no caben. Medido arriba: 3 de 3 canceladas tienen el `sync` por encima de
   11 min, y la única que terminó sin caché (08:01) tardó 19 min.
2. **¿Por qué estas ramas no tienen caché si `main` la tenía a las 07:24?**
   Predicción: la caché de GitHub Actions solo se restaura desde la misma rama
   o desde `main`, y `setup-uv` solo la **guarda** si el job termina bien
   (`post-if: success()` en la versión fijada `v8.3.2`): una rama cuya primera
   ejecución se cancela por tiempo no tendrá caché propia nunca y se cancelará
   siempre. Y la entrada de `main` ha dejado de restaurarse de forma fiable
   hoy: a las 08:28 una ejecución la restauró en 3 s y a las 08:29 otra, en
   la misma rama, no. Comprobable: la segunda ejecución de #666 (08:15) falló
   la caché igual que la primera, como predice el punto.
3. **¿Cuánto cuesta?** 3 × 20 = **60 minutos de runner tirados hoy** y dos PR
   paradas (la fusión del motor exige Quality verde, ADR-205). Desde el 01-09
   hay 12 cancelaciones de Quality: 6 del 13-09 son de otra familia (`sync` de
   3 s y `pytest` cortado entre 0 y 4 min: canceladas por un push nuevo o a
   mano) y 3 (08-09 en `main`, 20-09, 21-09) son la batería sola rozando el
   tope (19 m 20 s a 19 m 37 s en Pytest).
4. **¿Qué compra el cambio?** Plazo propio al paso `Sync environment` (20 min:
   falla ruidosamente, como ya hace el paso de apt) y al paso `Pytest` (25
   min), y el job a 50. Predicción: una ejecución sin caché **termina** en
   25-30 min en vez de morir a los 20; al terminar bien guarda la caché de su
   rama y la siguiente vuelve a 3 s. Coste: solo pagan las ejecuciones lentas,
   y un run de 30 min que termina vale más que uno de 20 que no.

## Criterio de parada (escrito ANTES de ver resultados)

- El cambio se queda si la primera ejecución de Quality de **esta misma rama**,
  que no tiene caché propia, termina (verde, o roja por algo que no sea el
  tiempo) y la siguiente restaura la caché en menos de 10 s.
- Si con los topes nuevos vuelve a cancelarse, la causa es otra y se para a
  buscarla en vez de subir más el número.
- No se toca la lista de dependencias ni la batería: eso sería otra decisión,
  con su propia nota.
