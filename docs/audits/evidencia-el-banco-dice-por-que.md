# Evidencia — que el banco diga por qué no midió

Fecha: 2026-08-27. Nota de arranque:
`docs/audits/arranque-el-banco-dice-por-que.md` (cuatro preguntas y criterio de
parada, escritos antes de tocar código).

## Criterio de parada, y qué pasó con cada uno

| | criterio | resultado |
|---|---|---|
| (a) | si al distinguir el código 3 un porcentaje no fiable acabara publicado como medida, se para | **no ocurrió**. `test_un_tres_no_se_convierte_en_una_medida` lanza un hijo cuyo JSON trae `porcentaje: 100.0` y exige `fallo` sin porcentaje copiado |
| (b) | si una configuración con TODAS las preguntas cortadas se presentara como medida, se para | **no ocurrió**. `test_si_se_cortan_todas_la_medicion_no_es_fiable` |
| (c) | si hiciera falta subir el tope del trabajo por encima de 85 min, se para | **no hizo falta**. El tope sigue en 80 y el plazo por configuración en 1500 s: lo que cambia es cómo se reparte por dentro |
| (d) | dos rondas de la misma familia → buscar la raíz | **se aplicó dentro de esta rama**: ver «lo que cazó una prueba propia» |

## Afirmación 1 — había una rama inalcanzable

**Lo que se afirma.** `comparar_investigadores.medir_configuracion` nunca
ejecutaba el bloque que lee `motivo_no_fiable`.

**Cómo se comprueba.** `medir_investigador.main` devuelve `3` **si y solo si**
`medicion_fiable` es falso, y lo hace después de escribir el JSON. La guarda
`if proceso.returncode != 0 …: return base` estaba antes. Por tanto todo `3`
salía por la guarda genérica y el bloque de abajo era código muerto.

**Consecuencia medida, no supuesta.** En la ejecución 33079519839 el informe dijo
de NVIDIA: *«el subproceso terminó con código 3. Final de su salida: new images
from 0 total images INFO: 🌐 Scraping complete…»*. El motivo se había escrito y se
tiró; no se pudo saber por qué esa medición no valía.

**Mutación.** Devolver la guarda a su forma anterior →
`test_un_tres_con_json_publica_el_motivo_y_no_la_cola_del_buscador` **cae**.

## Afirmación 2 — el plazo no cabía en el banco

**Lo que se afirma.** Con plazo solo por configuración, una pregunta colgada tira
las demás, ya contestadas.

**Cómo se comprueba.** Medido en la misma ejecución: NVIDIA hizo las siete
preguntas en 5 min 21 s (~46 s cada una); Google no terminó en 1500 s y no dejó
ni una respuesta legible. El plazo pasa a repartirse: cada pregunta dispone de
`presupuesto × 0,9 ÷ nº de preguntas`, con suelo de 60 s. Con 1500 s y siete
preguntas son 192 s cada una, y `192 × 7 = 1344 ≤ 1500`, así que el hijo termina
y escribe su informe **antes** de que el padre lo mate.

**Mutación.** Quitar el `wait_for` → caen las dos pruebas del corte.

## Afirmación 3 — el hijo tiene que saber de cuánto dispone

**Lo que se afirma.** Que el medidor sepa repartir no demuestra que el padre le
dé el número.

**Cómo se comprueba.** La primera vez que se corrió la mutación «el padre deja de
pasar `--presupuesto`», **las 40 pruebas siguieron en verde**. La pieza estaba y
el cable no se vigilaba: la enfermedad de siempre, esta vez en código escrito
hoy. Se añadió `test_el_padre_le_dice_al_hijo_de_cuanto_tiempo_dispone`, que
retrata el `argv` real del hijo y exige el MISMO número, no solo la bandera.

**Mutación.** Quitar `--presupuesto` → esa prueba **cae**.

## Lo que cazó una prueba propia, y por qué se cuenta aquí

Al escribir `test_si_se_cortan_todas_la_medicion_no_es_fiable` salió esto:

```
AssertionError: ninguna pregunta trajo ni una sola fuente: el buscador no
funciono … Comprueba que `ddgs` este instalado
```

Si se cortan todas las preguntas, `fuentes_totales` también vale cero, y el
motivo de las fuentes se disparaba primero: el instrumento mandaba a instalar
`ddgs` con el buscador perfectamente sano. **Otro rojo que miente**, dentro del
trabajo que venía a corregir un rojo que miente. Corregido poniendo el motivo del
corte antes; mutación M5 lo vigila.

## Una prueba retirada, y por qué no es un recorte

`test_una_medicion_que_el_hijo_declara_no_fiable_no_se_cuenta_como_medida` leía
el TEXTO del comparador y comprobaba que `ESTADO_FALLO` apareciera cerca de
`medicion_fiable`.

**Estuvo en verde todo el tiempo que esa rama fue inalcanzable.** No podía ser de
otra manera: un guardián que lee el código fuente ve que la rama está escrita,
nunca que se ejecute. La sustituye
`test_un_tres_no_se_convierte_en_una_medida`, que ejecuta el camino real y se ve
caer con la mutación M2.

## Las cinco mutaciones

| mutación | prueba que cae |
|---|---|
| M1 la guarda genérica vuelve a atrapar el 3 | `…publica_el_motivo_y_no_la_cola_del_buscador` |
| M2 creerse el 3 y copiar su porcentaje | `test_un_tres_no_se_convierte_en_una_medida` |
| M3 el padre no pasa `--presupuesto` | `test_el_padre_le_dice_al_hijo_de_cuanto_tiempo_dispone` |
| M4 se quita el plazo por pregunta | las dos del corte |
| M5 el motivo de las fuentes vuelve a ir primero | `test_si_se_cortan_todas_la_medicion_no_es_fiable` |

## Lo que este trabajo NO demuestra

No demuestra que Google o NVIDIA sirvan: **sigue sin haber número**. Arregla el
instrumento para que la próxima pasada, si vuelve a no medir, diga por qué. La
comparación real es la pasada siguiente, y su resultado irá aparte.
