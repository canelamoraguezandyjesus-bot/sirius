# Evidencia — `ci-pending` no espera un suceso que no va a llegar

Acompaña a ADR-194 y a
`docs/audits/arranque-ci-pending-no-espera-un-suceso-que-no-va-a-llegar.md`.
Salidas y datos tal cual, para poder comprobar la decisión sin creerle nada a la
prosa.

## 1. La comparación con el contenido controlado

Las dos PR llevan **el mismo trabajo** —el ADR-190 y su prueba, byte a byte— y
las abrió el mismo actor con el mismo token. La única diferencia es que la
primera nació en conflicto con su base.

```
actions_list(quality.yml, branch="feature/medir-ampliacion-guarda-citas-docs")
  -> {"total_count": 0, "workflow_runs": []}     [consultado a las 06:46 UTC]

pull_request_read(#624, get_check_runs)          [consultado a las 07:04 UTC]
  -> quality, status "in_progress", started_at "2026-09-14T07:03:42Z"
```

| | #620 (en conflicto) | #624 (sin conflicto) |
|---|---|---|
| Abierta | 01:42:35 | 07:02:53 |
| Empujones al head | 3 (01:42, 03:5x, 06:43) | 2 |
| Runs de `quality.yml` | **0** en 5 h 20 min | **1**, a los ~40 s de abrirla |
| `update_pull_request_branch` | `merge conflict between base and head` | no hizo falta |

## 2. El reconciliador pasó por en medio

El run 132 de «Reconciliar estados de Sirius» arrancó a las **04:55:51** del
14-09, dentro de la ventana. No publicó ningún aviso sobre la #619. **Pero no
por este defecto:** por el de ADR-193, que le impedía fechar el estado. Se dice
así de claro porque, si se contara al revés, esta evidencia estaría atribuyendo
a esta decisión un silencio que causó otra cosa.

Lo que este ADR arregla es lo que se ve **después** de aquel arreglo: con la
fecha ya legible, el camino de «Quality sin resultado» sigue sin publicar nada,
porque el aviso de atasco exige una conclusión de Quality y aquí no la hay
nunca.

## 3. Las tres pruebas y las tres mutaciones

```
uv run pytest tests/automation/test_sirius_reconcile.py -q
  -> 46 passed
```

| | Mutación | Salida |
|---|---|---|
| MA | `[ "$open_mergeable" = "false" ]` → `!= "true"` | `1 failed, 45 passed` — cae `test_recon_conflicto_002_mergeable_desconocida_no_afirma_nada` |
| MB | quitar `mergeable: .mergeable` del filtro | `1 failed, 45 passed` — cae `test_recon_conflicto_001_una_pr_en_conflicto_sin_quality_recibe_aviso` |
| MC | vaciar las dos líneas del «qué hacer» del aviso | `1 failed, 45 passed` — cae `test_recon_conflicto_001`, en la aserción del remedio |

MC existe porque la lección de ADR-183 era exactamente esa: un aviso que solo
constata deja el atasco igual de atascado. La prueba mira el texto del remedio,
no solo el del diagnóstico.

## 4. Lo que NO se midió, dicho

- **No hay tasa.** Un caso no es una frecuencia. No se ha contado cuántas PR en
  conflicto ha habido en la historia del repositorio: la mergeabilidad pasada no
  es recuperable de la API de GitHub, que solo contesta por el estado de ahora.
  La decisión no se apoya en la frecuencia, sino en que el estado final es
  silencioso y permanente.
- **No se ha reproducido el mecanismo dentro de GitHub.** Lo que consta es el
  efecto —cero runs con conflicto, un run en 40 segundos sin él, mismo
  contenido—, no una lectura del código de GitHub. La explicación de por qué
  —sin combinación no hay referencia de fusión que construir— es la razón
  conocida del comportamiento, y se presenta como explicación, no como medida.
- **No se ha comprobado qué hace `mergeable` en una PR cerrada o en borrador.**
  Este camino solo se recorre con una PR abierta y ya declarada no borrador, que
  es una rama anterior del mismo bloque.
