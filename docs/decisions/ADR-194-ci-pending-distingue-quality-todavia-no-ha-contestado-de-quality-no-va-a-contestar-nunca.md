# ADR-194 — `ci-pending` distingue «Quality todavía no ha contestado» de «Quality no va a contestar nunca»

- Estado: APROBADO
- Fecha: 2026-09-14
- Aprobación: el propietario, fusionando la PR de esta rama.

## Contexto y problema

`sirius:ci-pending` es un estado que **solo mueve la máquina**: se sale de él
cuando Quality termina y `advance-sirius-after-quality.yml` lo transiciona. La
red de seguridad, `scripts/automation/sirius_reconcile.sh`, cubre el caso de que
ese suceso se pierda: mira si Quality ya concluyó y, si concluyó, reintenta la
transición o avisa.

Lo que no cubría es el caso en que **Quality no va a concluir jamás**.

Una pull request en conflicto con su base no tiene combinación que construir.
GitHub no crea la referencia de fusión que el suceso `pull_request` necesita, y
`quality.yml` —que se dispara con `pull_request`— **no produce ni un solo run**.
La incidencia se queda en `ci-pending` esperando indefinidamente, y el
reconciliador, al leer que no hay resultado, informa en el resumen del run que
«no hay nada que reconciliar»: correcto cuando el resultado está por llegar,
falso cuando no va a llegar.

Es el patrón de ADR-183 con otra causa. Allí el push del corrector no disparaba
Quality; aquí es la PR la que no puede tener ninguno.

## La medida

Comparación natural con el contenido controlado —la misma rama, el mismo árbol,
el mismo actor, el mismo workflow—; lo único que cambia es el conflicto:

| | PR #620 (en conflicto) | PR #624 (mismo contenido, sin conflicto) |
|---|---|---|
| Abierta | 14-09 01:42:35 | 14-09 07:02 |
| Empujones al head | 3 | 2 |
| Runs de `quality.yml` para su rama | **0** | **1**, arrancado a los ~40 s |
| Tiempo observado | 5 h 20 min | — |
| Su incidencia (#619) | `sirius:ci-pending`, sin un solo aviso | completada |

El run 132 del reconciliador, a las 04:55:51, cae dentro de esa ventana. No
publicó nada —por el defecto que cierra ADR-193, no por este—, así que en cinco
horas no hubo aviso por ninguna de las dos causas.

**Lo que la medida NO dice:** un caso no es una tasa. No se ha contado cuántas
PR en conflicto ha habido en la historia del repositorio, porque la
mergeabilidad pasada no es recuperable de la API. Lo que sostiene esta decisión
no es la frecuencia, es que el estado final es **silencioso y permanente**.

## Criterio de parada (escrito ANTES de decidir)

En `docs/audits/arranque-ci-pending-no-espera-un-suceso-que-no-va-a-llegar.md`,
publicado en el primer commit de esta rama, con las cuatro preguntas. En
resumen: no vale si avisa de una PR que simplemente va lenta; no vale si el
aviso no dice qué hacer; no vale si se repite cada seis horas sobre el mismo
hecho; no inventa ninguna transición; y cada regla nueva trae su mutación.

Esa nota lleva además **la corrección de su propia premisa**: nació creyendo que
este camino causaba el silencio de la #619, y la medida enseñó que el
reconciliador ni llegaba a él. Se corrige en la nota en vez de reescribirla.

## Decisión

**El caso «sin resultado» se parte en dos, y solo lo parte un hecho explícito.**

`reconcile-sirius-states.yml` ya declara `pull-requests: read` y el guion ya lee
la PR para saber su estado, su head y si es borrador. Se le añade un campo que
ya tiene delante:

```bash
--jq '{state: .state, head: .head.sha, draft: (.draft // false), mergeable: .mergeable}'
```

Y en la rama de «Quality sin resultado»:

- `mergeable == "false"` → **atasco**: Quality no va a correr para ese head. Se
  publica un aviso en la incidencia con el marcador
  `<!-- sirius-stuck:ci-pending-en-conflicto:<head> -->`.
- cualquier otra cosa —`"true"`, `"null"` mientras GitHub lo calcula, o la
  lectura fallida— → se mantiene el comportamiento de hoy. **Fallo cerrado**:
  sin el hecho explícito no se afirma nada.

**El aviso dice qué hacer**, que es la lección de ADR-183: traer `main` a la
rama, o rehacerla sobre el `main` vigente y dejar escrito cuál PR la sustituye.
Y dice lo que el reconciliador **no** ha hecho: no repara, porque poner una rama
al día es un cambio en la rama y eso no lo decide una red de seguridad.

**El marcador va por head**, no por incidencia. Si se empuja un head nuevo y
sigue en conflicto, eso es un hecho nuevo y merece aviso nuevo; mientras el head
no cambie, `sirius_comment_once` impide que cada pasada del cron repita el
mismo comentario.

## Comprobación que la sostiene

Tres pruebas, una por rama de la decisión:

- `test_recon_conflicto_001_una_pr_en_conflicto_sin_quality_recibe_aviso` — el
  aviso sale, con marcador por head, dice la causa, **dice qué hacer** y no
  toca ninguna etiqueta.
- `test_recon_conflicto_002_mergeable_desconocida_no_afirma_nada` — con `null`
  no se avisa. Es la prueba que impide convertir esto en ruido sobre cada PR
  recién abierta.
- `test_recon_conflicto_003_una_pr_sana_sin_resultado_sigue_sin_ser_un_atasco` —
  el caso corriente no cambia.

Y la siembra pasa a modelar `mergeable` como lo que es en la API real:
**tri-estado**, no booleano. Sembrarla como booleano habría dejado sin medir
justo el caso que hay que distinguir — la misma familia que ADR-193 acaba de
cerrar en el doble de `gh`.

**Tres mutaciones, las tres vistas caer:**

| | Mutación | Resultado |
|---|---|---|
| MA | `= "false"` → `!= "true"` (tratar `null` como conflicto) | cae `conflicto_002` |
| MB | dejar de pedir `mergeable` en el filtro | cae `conflicto_001` |
| MC | el aviso deja de decir qué hacer | cae `conflicto_001` |

MC es la que vigila la lección de ADR-183: un aviso que solo constata deja el
atasco igual de atascado, así que la prueba mira el texto del remedio y no solo
el del diagnóstico.

## Consecuencias

- Una incidencia en `ci-pending` con la PR en conflicto pasa a recibir, a la
  siguiente pasada del cron, un aviso que nombra la causa y el remedio.
- Ninguna transición cambia. El reconciliador sigue sin reparar nada por esta
  causa.
- Un campo más por PR leída. No hay petición nueva: es el mismo `gh api` que ya
  se hacía.

## Lo que este ADR NO hace, y por qué

- **No pone la rama al día.** Eso exige `contents: write` en un workflow, es
  decisión del propietario y es de la familia que ADR-002 resolvió en contra. Es
  lo mismo que ADR-191 dejó escrito que no cableaba, y sigue sin cablearse.
- **No impide el conflicto**, que es lo que de verdad lo haría imposible en vez
  de visible. Eso lo atacan ADR-191 y ADR-192 por su lado.
- **No caza otras formas de «nunca».** Cierra la que está medida.

## La lección

- familia: `espera-sin-fin-por-un-suceso-que-nadie-va-a-emitir`
- sin esto se repetiría: una incidencia en un estado que solo mueve la máquina,
  esperando en silencio un suceso que ya es imposible —una PR en conflicto no
  recibe ningún run de Quality—, porque quien vigila los atascos leía «no hay
  resultado» y concluía «todavía no»; la #619 estuvo así cinco horas y veinte
  minutos sin que se publicara un solo aviso.
- lo hace cumplir: `tests/automation/test_sirius_reconcile.py`
