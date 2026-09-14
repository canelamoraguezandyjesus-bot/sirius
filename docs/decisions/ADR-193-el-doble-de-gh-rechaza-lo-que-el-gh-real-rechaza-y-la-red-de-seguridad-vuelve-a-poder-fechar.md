# ADR-193 — El doble de `gh` rechaza lo que el `gh` real rechaza, y la red de seguridad vuelve a poder fechar

- Estado: PROPUESTO
- Fecha: 2026-09-14
- Aprobación: el propietario, fusionando la PR de esta rama.

## Contexto y problema

`scripts/automation/sirius_reconcile.sh` es la red de seguridad de estados
atascados del motor: cada seis horas mira las incidencias con etiqueta
`sirius:*`, repara lo inequívoco y **avisa en la incidencia cuando un estado que
solo la máquina puede mover lleva demasiado tiempo puesto**. Todo lo segundo
depende de una sola función, `label_applied_at`, que pregunta a GitHub cuándo se
aplicó una etiqueta.

Esa función lleva **35 días sin poder responder**.

En el run 132 del reconciliador —14-09-2026, 04:56:13 UTC, leyendo la
incidencia #619— el log dice esto:

```
the `--slurp` option is not supported with `--jq` or `--template`
sirius_retry: fallo tras 4 intento(s): gh api -X GET repos/.../issues/619/events
  -f per_page=100 --paginate --slurp --jq (add // []) | ...
[AVISO] #619: ci-pending; no pude fechar el estado, así que no reparo a ciegas.
```

No es un 503 ni un límite de cuota: es la **validación de argumentos del propio
`gh`**, que rechaza la combinación antes de hacer ninguna petición. Falla
siempre, en los cuatro intentos y en todas las pasadas, para todas las
incidencias. Y como `stale_minutes` se apoya en `label_applied_at`, los tres
sitios del guion que dependen de la antigüedad de un estado —líneas 284, 399 y
472— caen al camino de fallo seguro: *no puedo fechar, no afirmo nada*.

Ese fallo seguro es correcto, y es exactamente por lo que nadie se enteró.

### Lo que lo convierte en un defecto de método y no en una errata

La invocación entró el **10-08-2026 a las 17:04 UTC**, en `f95b8d08`
(«Corregir tres defectos de la revisión de Codex»), como corrección del hallazgo
**P2**: sin `--slurp`, `--jq` se aplica a cada página por separado y el llamador
podía coger la fecha de una página y el id de otra.

Dos líneas más arriba, en la misma función, ya estaba escrito el aviso del
hallazgo **P1**:

> `-X GET` es OBLIGATORIO… sin esto TODA lectura fallaba, `marca` salía vacía y
> la rama de fallo seguro impedía publicar un solo aviso. **La detección entera
> habría estado muerta en producción sin que ninguna prueba lo notara.**

La corrección de P2 volvió a matar la detección **exactamente igual que P1**, en
la misma función, y las pruebas siguieron en verde. Dos rondas de la misma
familia: ADR-001 manda dejar de parchear y buscar la raíz.

**La raíz no es `--slurp`.** Es que el doble de `gh` de
`tests/automation/test_sirius_reconcile.py` modela lo que `gh` **hace** —cómo
pagina, qué devuelve— pero no lo que `gh` **rechaza**. Un doble más permisivo
que la herramienta que dobla convierte la suite en una comprobación de que el
código le gusta al doble.

## Criterio de parada (escrito ANTES de decidir)

Está en `docs/audits/arranque-el-doble-de-gh-rechaza-lo-que-el-real-rechaza.md`,
publicado en el primer commit de esta rama. En resumen: el arreglo tiene que
poder verse fallar por la razón exacta; la propiedad que P2 defendía —fecha e id
del MISMO suceso, aunque los sucesos vengan repartidos en páginas— tiene que
sobrevivir; lectura y transformación separadas, para no depender de las opciones
de shell del llamador; fallo cerrado intacto; nada de lo demás se debilita; y
cada regla nueva con una mutación sembrada y vista caer.

## Decisión

**Dos mitades, y ninguna vale sola.**

### 1. La llamada usa la forma que esta casa ya tenía escrita

No hay que inventar nada: `scripts/automation/sirius_issue.sh` documenta, desde
antes, que **no** usa `--slurp` y por qué —con `--paginate --jq` el filtro se
aplica por página y las salidas se **concatenan en orden**—. El reconciliador se
salió de esa regla y se rompió; vuelve a ella:

```bash
lineas="$(sirius_retry gh api -X GET "repos/${1}/issues/${2}/events" -f per_page=100 \
  --paginate \
  --jq "[.[] | select(.event == \"labeled\" and .label.name == \"${3}\")] \
        | .[] | \"\(.created_at) \(.id)\"")" || return 1
printf '%s' "$lineas" | tail -n 1
```

Cada suceso que casa sale en **su propia línea con su fecha y su id juntos**
—que es lo que P2 pedía, que no se mezclen los de sucesos distintos—, y la
última línea es la última aplicación de la etiqueta, venga de la página que
venga. Lectura y transformación van **separadas**: en una tubería el estado de
salida sería el de `tail`, que siempre acierta, y un 503 se convertiría en «esta
etiqueta no se ha puesto nunca».

### 2. El doble deja de ser más permisivo que el real

El simulado de `gh` pasa a rechazar `--slurp` junto con `--jq` o `--template`,
con el mensaje y el código de salida del `gh` real, **antes de hacer nada** —al
lado de la regla del método que ya modelaba desde P1—. `--slurp` a solas sigue
siendo legal, porque en `gh` lo es: rechazarlo también sería modelar otra
herramienta distinta.

Esta es la mitad que hace que no vuelva a pasar. Con ella, **la llamada de hoy
pone 20 pruebas en rojo**.

### 3. Y, de propina, el doble pasa a modelar `--paginate`

No estaba planeado: lo pidió una mutación que **sobrevivió** (M4, abajo).
Quitar `--paginate` de la llamada dejaba las 43 pruebas en verde, porque el
simulado entregaba todas las páginas hubiera o no `--paginate`. En producción
eso significa leer solo la primera página y fechar por el suceso más viejo. Es
la misma familia que este ADR arregla —una opción que el doble no modela es una
opción que ninguna prueba mide—, así que se cierra aquí en vez de dejarla
anotada.

## Comprobación que la sostiene

La tabla que importa no es «pasan las pruebas», sino **qué pasa con el código de
hoy**:

| | doble permisivo (antes) | doble fiel (esta PR) |
|---|---|---|
| llamada con `--slurp --jq` (el código que está en producción) | **41 passed** | **20 failed** |
| llamada con `--paginate --jq` (el arreglo) | 41 passed | 43 passed |

Esa celda de arriba a la izquierda es el defecto entero: la suite en verde sobre
una llamada que en producción falla el 100 % de las veces.

**Dos guardas nuevas:**

- `test_recon_slurp_001_el_doble_de_gh_rechaza_slurp_con_jq_como_el_real`
  sostiene la fidelidad del doble en las dos direcciones: rechaza `--slurp` con
  `--jq` y con `--template`, y **acepta** `--slurp` a solas.
- `test_recon_slurp_002_ningun_guion_de_automatizacion_combina_slurp_con_un_filtro`
  lee todos los `scripts/automation/*.sh` —pegando antes las líneas continuadas,
  o una llamada partida en dos se escaparía— para que la regla valga también
  donde ninguna prueba pasa hoy.

**Cuatro mutaciones, y una sobrevivió:**

| | Mutación | Resultado |
|---|---|---|
| M1 | la llamada vuelve a `--slurp --jq`, tal cual está en producción | **20 caen**, y `slurp_002` las nombra |
| M2 | el doble vuelve a aceptar la combinación | `slurp_001` cae; y con M1 puesta a la vez, las 41 vuelven a pasar |
| M3 | `tail -n 1` → `head -n 1` | 2 caen (`stuck_001`, `stuck_008`) |
| M4 | quitar `--paginate` de la llamada | **43 passed: SOBREVIVIÓ.** Con el doble modelando `--paginate`, cae `stuck_008` |

M2 es la que demuestra la raíz: con la llamada rota puesta **y** el doble
permisivo, la suite vuelve a los 41 en verde. No es que faltara una prueba; es
que el doble absolvía.

## Consecuencias

- El reconciliador vuelve a poder fechar estados, así que los avisos de atasco
  que lleva 35 días sin publicar empiezan a publicarse. **Puede aparecer un
  goteo de avisos atrasados** en incidencias viejas la primera vez que corra:
  no es un fallo nuevo, es lo que no se dijo.
- Se dejan de gastar cuatro intentos con espera por incidencia y por pasada en
  una llamada que no podía funcionar.
- No se recupera nada de lo no avisado: el reconciliador no guarda lo que no
  dijo.
- Ninguna transición cambia.

## Lo que este ADR NO hace, y por qué

- **No arregla el otro defecto de la #619.** Con la fecha ya legible, una
  incidencia en `ci-pending` cuya PR está en conflicto sigue sin recibir aviso,
  porque el camino del aviso exige que Quality haya **concluido** y en una PR en
  conflicto no concluye nunca. Es otra decisión, con su propia medida.
- **No hace fiel al doble en todo lo demás.** Fija dos reglas de `gh` que ya nos
  han costado rondas —el método y `--slurp`— y modela `--paginate`. Otras
  incompatibilidades siguen sin estar cubiertas, y eso se dice aquí.
- **No centraliza las llamadas a `gh`.** La vía que lo haría imposible del todo
  —que ninguna llamada se escriba suelta, sino a través de una función única que
  valide sus propios argumentos— convertiría «acordarse de la regla» en «no
  poder saltársela», que es la forma de ADR-174. Toca todas las llamadas del
  guion a la vez y es una PR entera aparte. Queda declarada, sin hacerse.

## La lección

- familia: `doble-mas-permisivo-que-la-herramienta-que-dobla`
- sin esto se repetiría: una prueba en verde sobre una invocación que la
  herramienta real rechaza siempre, porque el doble modela lo que la herramienta
  hace y no lo que rechaza; pasó dos veces seguidas en la misma función
  —hallazgos P1 y P2— y la segunda dejó la red de seguridad de estados atascados
  ciega durante 35 días sin que ninguna prueba lo notara.
- lo hace cumplir: `tests/automation/test_sirius_reconcile.py`
