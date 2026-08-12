# ADR-003 — Un plazo es un mínimo contra una cota absoluta, nunca una ventana propia

- Estado: PROPUESTO
- Fecha: 2026-08-10
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario

## Contexto y problema

Tres defectos seguidos en el mismo sitio, con la misma forma:

1. **#135** — el paso moría por su `timeout-minutes` sin publicar veredicto.
   Se le puso un plazo interno de lectura (`ahora + 300`).
2. **#140** — la parada segura hacía `unset SIRIUS_GH_DEADLINE` para no heredar
   un plazo agotado, y sin cota podía colgarse hasta que el tope externo matara
   la shell. Se le puso un plazo propio (`ahora + 120`).
3. **Hallazgo P2 de Codex en la PR #142** — ese plazo propio se concedía 120s
   *desde ahora* sin mirar cuánto quedaba del paso. Entre agotarse la lectura y
   llamar a la parada corre proceso local (`sirius_next_round_number`,
   `sirius_convergence.py`, varios `jq`) que no consulta `SIRIUS_GH_DEADLINE` y
   al que no acota nadie. El máximo real era `300 + proceso local + 120`, no
   420: con más de 60s de proceso local, Actions vuelve a matar el paso a mitad
   de la transición.

En la misma PR, y antes de que llegara Codex, ya se había corregido el mismo
defecto una capa más abajo: `_sirius_comment_once_bounded` se daba `ahora + 90`
ignorando el plazo heredado, hasta 210s cuando el llamador había reservado 120.

Cuatro instancias, un solo error: **un plazo relativo (`ahora + N`) no puede
proteger de un tope absoluto**, porque «ahora» ya se ha corrido. Cada capa se
concedía su ventana sin mirar el techo, y cada arreglo movía el agujero una capa
más arriba en vez de cerrarlo. Es la regla de las dos rondas de ADR-001: dos
rondas con defectos de la misma familia, parar de parchear y buscar la raíz.

## Criterio de parada (escrito ANTES de decidir)

Si el arreglo consiste en ajustar otro número de segundos, **no es el arreglo**.
Solo cuenta como raíz algo que haga imposible reintroducir la misma forma sin
romper una prueba.

## Decisión

**Todo plazo de esta automatización es un mínimo contra una cota absoluta.**

1. El instante de arranque del paso se guarda **una vez** (`arranque`), y de él
   se derivan tanto el plazo de lectura como el tope del paso
   (`PRESUPUESTO_PASO - MARGEN_PASO`).
2. Ninguna capa se concede una ventana: calcula la que querría y toma el
   **mínimo** con la cota que ya rige. Vale igual hacia abajo
   (`_sirius_comment_once_bounded` con el plazo heredado) que hacia arriba
   (`parada()` con el tope del paso).
3. Si al llegar no queda margen, el plazo sale **vencido**, no ausente:
   `_sirius_gh` devuelve 124 sin lanzar la llamada. La parada queda **muda**
   pero viva para escribir `valid=false` y salir. Muda es peor que a tiempo y
   mejor que **colgada**, que es lo que deja un plazo ausente.
4. El presupuesto escrito (`PRESUPUESTO_PASO`) queda **atado por prueba** al
   `timeout-minutes` real del paso. Es un número copiado a mano, y un número
   copiado se queda viejo solo.

## Comprobación que la sostiene

- GATE-005 ejecuta la `parada()` **extraída del YAML** con un reloj que salta
  casi el paso entero antes de la publicación, y mide el instante absoluto que
  ve `gh`. Quitar el mínimo la hace fallar.
- GATE-006 fija el caso normal: sin desbordar, el plazo es el propio de
  publicación, no el tope. Un mínimo incondicional la hace fallar. Sin ella,
  «acotar por arriba» podía degenerar en «acotar siempre».
- GATE-003 compara `PRESUPUESTO_PASO` con `timeout-minutes` leído del YAML.
  Falla tanto si se falsea el número como si se baja el tope real sin tocarlo.
- Nueve mutaciones en las dos direcciones, todas con el resultado predicho
  antes de ejecutarlas.

## Consecuencias

- Lo que esto **sí** impide: que una capa nueva se conceda tiempo por su cuenta
  sin que una prueba lo note, y que los comentarios sigan afirmando una
  aritmética que el YAML ya no respalda.
- Lo que **no** hace: no acota el proceso **local** (Python, `jq`, `grep`). Ese
  sigue sin cota propia; lo único garantizado es que consumirlo no permite ya
  desbordar el paso, porque la publicación se recorta contra el tope. Acotar el
  proceso local sería otro cambio y no está hecho.
- Tampoco alcanza a los demás workflows: la regla se aplica en
  `repair-sirius-work.yml` y en `sirius_issue.sh`, que son los dos sitios donde
  hoy hay plazos. Extenderla al resto queda como trabajo pendiente, no como
  algo ya hecho.
- El patrón —«una cota que otra capa puede ampliar no es una cota»— pertenece al
  catálogo de la disciplina de evidencia. Anotarlo allí queda pendiente.

## Alternativas descartadas y por qué

- **Subir `timeout-minutes`**: mueve el borde sin quitar la forma. Con el
  siguiente proceso local más lento vuelve el mismo fallo.
- **Acotar el proceso local con `timeout`**: acota otra cosa, no cierra el
  agujero. Y un `timeout` que mata a `sirius_convergence.py` deja la decisión
  sin leer, que es peor que llegar tarde.
- **Dejar la parada sin plazo (volver al `unset`)**: es exactamente la #140.
  Sin cota, colgada; y colgada no escribe `valid=false`.
