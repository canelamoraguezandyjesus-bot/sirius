# ADR-183 — La ausencia de run de Quality para el head se encamina, no se espera en silencio

- Estado: PROPUESTO
- Fecha: 2026-09-13
- Aprobación: la fusión de la PR por el propietario

## Contexto y problema

`relanzar_quality_si_ya_termino`, en `scripts/automation/sirius_apply_verdict.sh`,
se ejecuta al entrar la incidencia en `sirius:ci-pending` y existe por ADR-149:
si Quality ya cerró para el head antes de la transición, su `workflow_run` se
consumió con la incidencia en otro estado y hay que **relanzar** ese run para
que el avance vuelva a verlo.

La función consulta los runs de Quality del head y solo contempla dos casos:

- alguno con `status != completed` → espera («Quality sigue en curso…»);
- alguno `completed` → lo relanza con `gh api -X POST …/rerun`.

Nunca comprueba si la lista está **vacía**. Con cero runs, `activos` vale `0` y
`terminado` sale vacía, así que cae en la rama del `return 0` silencioso e
imprime «Sin run de Quality terminado para `<sha>`; su cierre llegará con la
incidencia ya en ci-pending». La incidencia se queda en `sirius:ci-pending`
esperando un evento que nadie va a emitir: no hay ningún run que pueda cerrarse.
El único camino de encaminamiento necesita el **id de un run existente** para
re-ejecutarlo; la función sabe RE-lanzar, no sabe LANZAR.

Y a diferencia de los otros tres modos de fallo de esa misma función
—`consulta-runs-fallida`, `consulta-runs-ilegible` y `relanzamiento-fallido`,
que llaman a `avisar_quality_sin_encaminar` y dejan aviso en la incidencia—,
el caso de lista vacía sale en **silencio** con `return 0`. Nadie se entera.

Reproducido el 12-09-2026 sobre la incidencia real **#594**: el corrector empujó
`1c408f86` y GitHub no creó ningún run de Quality para ese sha; el log del run
`34724754322`, paso «Aplicar el veredicto», marca de tiempo `23:34:18.0097151Z`,
imprime exactamente ese mensaje, y la incidencia se quedó en `ci-pending` hasta
que un push ajeno disparó Quality por casualidad.

Queda **fuera de alcance** averiguar por qué el push del corrector no creó el
run (ya se descartaron la regla de GitHub sobre eventos emitidos con
`GITHUB_TOKEN` y un grupo de concurrencia en `quality.yml`): ese diagnóstico
necesita su propio encargo.

## Nota de arranque (escrita ANTES de tocar el código, ADR-001)

### 1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo OBSERVAR el fallo?

El fallo vive en `relanzar_quality_si_ya_termino`, en la rama que se alcanza
cuando `activos` vale `0`: esa rama confunde «cero runs» con «runs que ya
terminaron y no hay ninguno relanzable». El arreglo va a esa misma función,
justo ahí, y **sí puede observar el fallo**: la distinción que falta —lista
vacía frente a lista con elementos— está enteramente dentro de `runs_json`, el
dato que la propia función ya tiene en la mano. No depende de un proceso que
muera, ni de un evento externo, ni de un log que alguien tenga que leer.

### 2. ¿Qué NO va a garantizar esto?

- **No garantiza que Quality llegue a ejecutarse** para ese head. `quality.yml`
  se dispara por `push` a `main` y por `pull_request`, y no tiene
  `workflow_dispatch`; el paso no dispone de ninguna herramienta para CREAR un
  run de evento `pull_request`, que es el único que
  `advance-sirius-after-quality.yml` acepta (`workflow_run.event ==
  'pull_request'`). Por eso el encargo autoriza expresamente la segunda salida:
  avisar como hacen los otros modos de fallo.
- **No explica por qué GitHub no creó el run.** Eso es otro encargo.
- **No distingue** «GitHub nunca creó el run» de «la consulta se adelantó a la
  creación del run». Los dos salen por el mismo aviso, y el aviso lo dice.
- **No toca** los otros tres caminos: run en curso sigue esperando, run
  terminado sigue relanzándose una sola vez con su marcador, y las guardias de
  consulta fallida e ilegible quedan como están.

### 3. Criterio de parada (decidido ANTES de medir y de ver ningún resultado)

- Si la medida enseña que la lista vacía es el caso **normal** de un run sano
  —es decir, que la consulta se adelanta habitualmente a la creación del run y
  la incidencia avanza después por sí sola—, entonces convertirla en paso rojo
  con aviso sería peor que el fallo que arregla: en ese caso **paro**, no
  entrego el aviso y escalo al propietario, porque el arreglo correcto sería
  esperar/reconsultar y eso es otra decisión.
- Si el aviso no puede publicarse una sola vez por head (idempotencia), paro:
  repetir avisos en cada reejecución del paso es la deuda que ADR-149 ya cerró.
- Si alguna de las validaciones obligatorias no queda en verde, no se entrega.
- La prueba nueva tiene que verse **fallar** contra el guion sin cambiar
  (ADR-001, §3) y las viejas del bloque ADR-149 tienen que seguir en verde.

### Criterio de conteo (declarado ANTES de contar)

El encargo pide medir cuántas veces aparece una parada en `ci-pending` sin run
para el head. Cuento así, y solo así:

- **Universo**: los runs de los dos workflows que ejecutan el paso «Aplicar el
  veredicto» —`implement-sirius-work.yml` y `repair-sirius-work.yml`—, los 40
  últimos de cada uno según `gh run list`.
- **Una aparición** = un run de ese universo cuyo log contenga la línea literal
  `Sin run de Quality terminado para`. Es la **única** huella que deja este modo
  de fallo, y ese es justamente el hallazgo: no publica nada en la incidencia,
  así que no puede contarse desde el historial de incidencias.
- **Contraste, en el mismo universo**: apariciones del marcador
  `sirius-quality-sin-encaminar` en los comentarios de las incidencias del ciclo
  (`gh`), que son los modos de fallo que **sí** avisan. Un modo que avisa se
  puede contar desde fuera; uno que calla, no.
- Lo que **no** cuento: paradas en `ci-pending` por otras causas (Quality en
  rojo, revisión pendiente, PR cerrada). No son este fallo.

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

Que el paso pudiera **lanzar** Quality para ese head: un `workflow_dispatch` en
`quality.yml` más un avance que aceptase ese evento. Eso cambia dos workflows
—`quality.yml` y el filtro de `advance-sirius-after-quality.yml`—, está fuera
del alcance permitido de este encargo y choca además con ADR-002 (no ampliar la
credencial de la automatización sobre sus propios workflows). Así que aquí el
fallo no se hace imposible: se hace **imposible de silenciar**. La parada deja
de ser un `return 0` mudo y pasa a ser un paso rojo reintentable con su aviso en
la incidencia, que es exactamente lo que el encargo autoriza como segunda
salida. Hacerlo imposible necesita su propio encargo, y depende del diagnóstico
de por qué GitHub no creó el run.

## Opciones consideradas

1. **Lanzar Quality para ese head desde el paso.** Es lo que de verdad
   encaminaría la incidencia. Necesita `workflow_dispatch` en `quality.yml` y
   que `advance-sirius-after-quality.yml` acepte un `workflow_run` de evento
   distinto de `pull_request`: dos workflows fuera del alcance de este encargo,
   y ADR-002 en contra de ampliar la credencial de la automatización sobre sus
   propios workflows.
2. **Esperar y reconsultar** unos segundos por si el run aún no existía. Solo
   tiene sentido si la lista vacía fuera una carrera con la creación del run.
   La medida dice que no lo es (abajo).
3. **Avisar en la incidencia y dejar el paso rojo y reintentable**, igual que
   los otros tres modos de fallo de la misma función. Es la segunda salida que
   el encargo autoriza expresamente.
4. **Dejarlo como está** —el `return 0` mudo—. Es el fallo.

## Decisión

**Opción 3.** En `relanzar_quality_si_ya_termino`, la rama que hoy sale con
`return 0` cuando no hay ningún run relanzable pasa a llamar a
`avisar_quality_sin_encaminar` y a terminar en rojo, exactamente como
`consulta-runs-fallida`, `consulta-runs-ilegible` y `relanzamiento-fallido`.

Se distinguen las dos formas de llegar ahí, con fase propia en el marcador:

- `sin-runs-para-el-head`: la lista vino **vacía**. No hay ningún run que pueda
  cerrarse, así que no hay nada que esperar.
- `runs-sin-id-relanzable`: hay runs terminados, pero ninguno con `id` con el
  que relanzar.

Y **cada una de las dos fases lleva su propio texto**, porque ninguna de las
dos es «no se pudo consultar»: en ambas la consulta de Actions funcionó, y el
aviso genérico —pensado para las lecturas caídas— afirmaría lo contrario.

- `sin-runs-para-el-head`: decirle al operador «relanza a mano el run de este
  head (Actions → Re-run all jobs)» cuando no se encontró ninguno lo manda a un
  sitio vacío. Dice en su lugar qué hace correr Quality, **distinguiendo los
  dos gestos en vez de igualarlos**: cerrar y reabrir la PR lo hace correr
  sobre ESTE mismo head (`quality.yml` declara `on: pull_request` sin lista de
  `types`, así que los tipos por defecto incluyen `reopened`), mientras que un
  push emite `synchronize` y por definición mueve el head, de modo que su run
  es el de un head NUEVO —encamina la incidencia igual, pero no cumple la
  promesa «para este head»—. En ambos casos, cuando ese run termine,
  su `workflow_run` despierta a `advance-sirius-after-quality.yml` y la
  incidencia avanza sola; y **lo mismo, pero solo**, si el run ya existía y
  AÚN NO había terminado cuando se consultó. Si ya existía y ya había
  TERMINADO antes de la consulta, su `workflow_run` se emitió y se consumió con
  la incidencia todavía en `implementing`/`repairing` —que es justo la deuda 3
  de ADR-149 que esta función existe para reparar—, no vuelve a emitirse y la
  incidencia **no** avanza sola: hace falta igualmente uno de los dos gestos.
  El aviso distingue los dos subcasos en vez de tranquilizar al operador
  precisamente en el que no debe. **No** pide reejecutar este job: `transition` ya dejó
  la incidencia en `ci-pending` y retiró la etiqueta consumible, así que la
  puerta del workflow ya no daría `valid=true`
  (`implement-sirius-work.yml:239-247`, `repair-sirius-work.yml:593-599`) y el
  paso que publica el aviso no volvería a ejecutarse. Además, el texto describe
  la **observación** y no un hecho sobre GitHub: una lista vacía no distingue
  «GitHub no creó el run» de «la consulta se adelantó a su creación o
  indexación», y el aviso nombra las dos posibilidades en vez de afirmar la
  primera.
- `runs-sin-id-relanzable`: dice que la consulta funcionó y que hay runs
  terminados para el head pero ninguno con `id` con el que relanzar. Aquí sí
  existe un run que el operador puede relanzar a mano, así que conserva ese
  gesto —Actions → Re-run all jobs—, pero **no** el «o reejecutar este paso»
  del texto genérico: esta rama se alcanza después de `transition`, igual que
  la anterior, así que la etiqueta consumible ya se retiró y el paso que
  publica el aviso no volvería a ejecutarse. Por eso lleva su propio
  `desbloquea` en vez del genérico.

Y, por la misma razón, **ninguna de las dos fases llama reintentable a ESTE
paso**: sería la promesa contraria a la que el propio aviso hace seis líneas más
abajo («Reejecutar este job NO sirve»), y la verdadera es la segunda —la puerta
de los dos workflows exige la etiqueta consumible que «Consumir el evento y
marcar en curso» ya retiró, y «Aplicar el veredicto» está condicionado a
`always() && steps.gate.outputs.valid == 'true'`, así que un «Re-run failed
jobs» lo salta—. Lo que sigue vivo y recuperable es la **incidencia**, en
`sirius:ci-pending`, por el gesto que cada fase describe; y eso es lo que dicen
ahora las dos cadenas `que_pasa` y el `::error::` de esa rama.

Lo que **no** cambia: el run en curso sigue esperando y sigue terminando en
verde; el run terminado sigue relanzándose una sola vez con su marcador; las
guardias de consulta fallida e ilegible quedan intactas.

## Comprobación que la sostiene

### La medida, con el criterio de conteo declarado antes (arriba)

Universo: los 40 últimos runs de `implement-sirius-work.yml` (2 no saltados) y
de `repair-sirius-work.yml` (5 no saltados) el 13-09-2026. De esos **7 runs con
veredicto aplicado, 3 imprimieron la línea** `Sin run de Quality terminado
para`:

| run | head | ¿hay hoy algún run de Quality para ese head? |
|---|---|---|
| [34726776261](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/34726776261) | `a8bb7b64…` | **no**, `[]` |
| [34724754322](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/34724754322) | `1c408f86…` (el caso del encargo, #594) | **no**, `[]` |
| [34724720944](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/34724720944) | `7ab8fb64…` | **no**, `[]` |

Comandos: `gh run list --workflow … --limit 40`, `gh run view <id> --log | grep
-c "Sin run de Quality terminado para"` y, para la tercera columna, `gh api
"repos/…/actions/workflows/quality.yml/runs?head_sha=<head>&per_page=20"`, que
devuelve `[]` en los tres.

Dos lecturas de esa tabla:

- **No es raro: es 3 de 7** en las dos horas de ciclo que cabían en el universo
  declarado.
- **No es una carrera.** El criterio de parada decía que si la lista vacía fuera
  el caso normal de un run sano —la consulta adelantándose a la creación del
  run— había que parar y escalar, porque el arreglo sería esperar y no avisar.
  No lo es: un día después, los tres heads siguen sin ningún run de Quality. El
  run no llegó tarde, no llegó nunca. El criterio no se dispara y se sigue.

**Contraste que da la vuelta al argumento:** buscando en las incidencias del
repositorio el aviso de los modos que **sí** hablan (`gh search issues …
"QUALITY_SIN_ENCAMINAR"`) aparece **1** incidencia, la #545. Tres paradas del
modo mudo no dejaron ni una. Un modo de fallo que avisa se puede contar desde
fuera; uno que calla solo se puede contar bajando a los logs, que es
exactamente lo que nadie hace.

### Las pruebas, vistas fallar antes del cambio (ADR-001 §3)

En `tests/automation/test_sirius_apply_verdict.py`, contra el guion **sin**
modificar (`git stash push scripts/automation/sirius_apply_verdict.sh`), las
cuatro nuevas caen:

```
FAILED …::test_sin_ningun_run_de_quality_la_incidencia_se_encamina_y_no_espera
FAILED …::test_un_run_en_curso_se_distingue_de_no_haber_ninguno
FAILED …::test_el_aviso_de_que_no_hay_ningun_run_se_publica_una_sola_vez
FAILED …::test_unos_runs_terminados_sin_id_tampoco_salen_en_silencio
```

todas por lo mismo —`assert 0 != 0`: el paso terminaba en verde—, y con el
cambio aplicado el fichero entero queda en verde (65 pruebas).

**Ronda 2 de corrección: el CUERPO del aviso, no solo su código de salida.** Las
cuatro pruebas de arriba no miraban el texto publicado, así que dos avisos
falsos pasaban en verde. Se amplían dos de ellas con afirmaciones sobre el
cuerpo (no se añade ninguna prueba nueva: el fichero sigue en 65) y se ven caer
contra el guion **sin** la corrección de los textos:

```
FAILED …::test_sin_ningun_run_de_quality_la_incidencia_se_encamina_y_no_espera
E       AssertionError: una lista vacía no prueba que GitHub no lo creara
E       'GitHub no creó' is contained here: NINGUNO. GitHub no creó ninguno.
FAILED …::test_unos_runs_terminados_sin_id_tampoco_salen_en_silencio
E       assert 'no se pudo consultar' not in …
E       'no se pudo consultar' is contained here:  Quality: no se pudo consultar.
```

`test_sin_runs_de_quality_no_se_relanza_nada` **fijaba el fallo**: afirmaba
`returncode == 0` para cero runs. Se sustituye por la primera de las cuatro, que
afirma lo contrario sobre la misma entrada. Otras cinco pruebas de forma del
marcador (`…ready_for_review_with_pr`, las tres de la firma de ADR-140 y su
adversaria) no sembraban runs y caían de rebote: se les siembra el caso
ordinario —Quality corriendo para el head—, sin tocar ninguna de sus
afirmaciones.

**Ronda 3 de corrección: los dos textos que seguían prometiendo de más.** Se
amplían otra vez las mismas dos pruebas (el fichero sigue **sin** ninguna
prueba nueva) y se ven caer contra el guion **sin** la corrección de esta
ronda:

```
FAILED …::test_unos_runs_terminados_sin_id_tampoco_salen_en_silencio
E       assert 'reejecutar este paso' not in …
E       'reejecutar este paso' is contained here: l jobs) o reejecutar este paso.
FAILED …::test_sin_ningun_run_de_quality_la_incidencia_se_encamina_y_no_espera
E       AssertionError: el push encamina, pero sobre un head nuevo
E       assert 'mueve el head' in …
```

La primera fija que `runs-sin-id-relanzable` deja de ofrecer «reejecutar este
paso»; la segunda, que `sin-runs-para-el-head` deja de prometer que un push
hace correr Quality «para este head».

### La cadena completa, anclada a su árbol

Una sola invocación de `pwsh -File scripts/check.ps1` (Ruff format, Ruff lint,
mypy, pytest) sobre el árbol de `2277a48a`, el commit que cierra los tres
hallazgos de la ronda 3 (los dos textos y el comentario del `case`):

```
=========== 6392 passed, 17 skipped, 2 xfailed in 461.46s (0:07:41) ============
EXITCODE=0
```

La cifra anterior, sobre el árbol de `9bb54ea3` (ronda 2), era
`6392 passed, 17 skipped, 2 xfailed in 548.44s`: el recuento no cambia porque
esta ronda no añadió pruebas, solo afirmaciones a dos ya existentes.

## Consecuencias

- Una parada por ausencia de run deja de ser silenciosa: comentario en la
  incidencia con la causa y el gesto, paso rojo y reintentable. La incidencia
  sigue en `sirius:ci-pending`, como en los otros tres modos.
- El paso **fallará en rojo** en un caso en que antes pasaba en verde. Es el
  cambio que se pide: el verde anterior era falso, porque lo que declaraba
  —«su cierre llegará»— no podía ocurrir.
- Quien reciba el aviso todavía tiene que hacer algo a mano. Encaminarlo solo
  necesita poder lanzar Quality, y eso es otro encargo, que además depende del
  diagnóstico —también pendiente— de por qué GitHub no crea el run.

## Alternativas descartadas y por qué

- **Lanzar Quality (opción 1):** fuera del alcance del encargo, toca dos
  workflows y choca con ADR-002. Es lo único que haría el fallo imposible, y se
  deja escrito arriba como tal.
- **Esperar y reconsultar (opción 2):** la medida lo descarta. Los tres heads
  medidos siguen sin run un día después; esperar solo retrasaría la misma
  parada, ahora con un plazo inventado.
- **Avisar pero salir en verde:** el aviso llegaría a la incidencia, pero el run
  saldría verde y el tablero diría que el paso hizo su trabajo. Los otros tres
  modos de fallo salen en rojo por la misma razón, y ADR-149 lo dejó escrito:
  una lectura caída no es «no hay nada que relanzar».

## La lección

- familia: `pieza-sin-lector`
- sin esto se repetiría: escribir la rama «no hay nada que hacer» de un encaminador como un `return 0` con un `echo`, de modo que la única prueba de que el ciclo se ha parado viva en un log que nadie lee.
- lo hace cumplir: `tests/automation/test_sirius_apply_verdict.py`
