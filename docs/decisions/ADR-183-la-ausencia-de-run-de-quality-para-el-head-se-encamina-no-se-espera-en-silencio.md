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

## Decisión

## Comprobación que la sostiene

## Consecuencias

## Alternativas descartadas y por qué

## La lección
