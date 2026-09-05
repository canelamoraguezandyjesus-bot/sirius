# ADR-141 — Una parada de infraestructura del revisor rearma una ronda, una sola vez

- Estado: PROPUESTO
- Fecha: 2026-09-05
- Aprobación: la fusión de la PR que introduce este ADR, por el
  propietario — autorizada explícitamente esta noche («o lo haces tú…
  fusiónalas tú»), la ejecuto yo con Quality y mi revisión en verde.
  No toca `.github/**`: vive en dos guiones de scripts/automation.

## Contexto y problema

Deuda 12 de la bitácora. El 04-09, tres vueltas del ciclo murieron sin
veredicto por fallos del ARNÉS de la revisión, no del contenido: Codex
no entregó dentro de su plazo absoluto de 1200 s (G3, 15:35 UTC), y el
revisor Claude terminó sin `reviewed_head_sha` demostrable (C1, ronda 6,
21:42 UTC). Cada una detuvo la incidencia en `failed-safely` y exigió
revivirla a mano (`continua` + relanzar el run verde): tres
intervenciones humanas por fallos que un reintento habría absorbido.

La trampa que un parche ingenuo pisaría, descubierta en el
reconocimiento nocturno: el disparador de Codex deduplica por (head,
ronda) («no se publica un segundo disparador para el mismo head y
ronda», sirius_codex_review.py), así que reintentar DENTRO del mismo run
esperaría 1200 s a un disparo que nunca llegará. El reintento correcto
re-arma una RONDA nueva — y `ROUND_ID` es `github.run_id`
(review-sirius-work.yml:226,325), así que un run nuevo trae ronda nueva
y el anti-bucle no lo bloquea. Verificado antes de escribir una línea.

## Criterio de parada (escrito ANTES de decidir)

- Cero lógica nueva en YAML: si el diseño exigiera tocar
  `review-sirius-work.yml`, parar — la clasificación va en el agregador
  (Python puro, testeable) y la decisión en el aplicador determinista.
- Tope duro de UN reintento por head, con candado material (marcador en
  la incidencia), no con memoria de proceso: dos fallos persistentes del
  arnés deben detener, no columpiarse.
- La bandera nunca en paradas de contenido: un `FAILED_SAFELY` que un
  revisor DECIDIÓ emitir lleva un diagnóstico que un reintento taparía.

## Opciones consideradas

1. Clasificar en `sirius_aggregate_reviews.py` (`infra_retryable`) y
   decidir en `sirius_apply_verdict.sh` (reponer `review-requested` con
   marcador-candado `sirius-reintento-ronda:<head>`).
2. Reintentar dentro del propio recolector de Codex (segunda espera).
3. Dejarlo como está (revivir a mano).

## Decisión

**Opción 1.** Dos piezas:

- `sirius_aggregate_reviews.py`: `_failed()` acepta `infra_retryable` y
  lo ponen exactamente tres sitios — head de Claude no demostrado, head
  de Codex no demostrado, y el fallo seguro cuya ÚNICA causa es el
  timeout del recolector de Codex (`reason == "timeout"` y Claude sin
  FAILED_SAFELY). Nada más lo lleva: ni el resultado de Codex ausente o
  fuera de contrato (puede ser un defecto real del recolector que
  conviene mirar), ni ninguna parada de contenido.
- `sirius_apply_verdict.sh` (caso FAILED_SAFELY, solo rol `reviewer`):
  con la bandera y sin marcador previo para el head vigente, publica
  `<!-- sirius-reintento-ronda:<head>:<run> -->` y repone
  `sirius:review-requested` (mismo trío etiqueta/color/descripción que
  usan la ruta de avance y el reconciliador); con marcador ya presente,
  o sin PR verificable (se usa `locate_verified_pr` directamente porque
  `resolve_pr` detiene el guion), o en cualquier otro rol, detiene como
  siempre.

Por qué no la 2: solo cubre el timeout de Codex (no el head no
demostrado de Claude), y una segunda espera completa no cabe en el
presupuesto del paso (30 min para esperas de 20).

## Comprobación que la sostiene

- Rojos previos, vistos fallar (ADR-001): las 4 pruebas de clasificación
  del agregador fallaron contra el agregador sin bandera («4 failed, 30
  passed» con las 3 adversarias en verde), y
  `test_reviewer_parada_de_infra_rearma_una_ronda_nueva` falló contra el
  guion sin la rama («1 failed, 3 passed» con tope y adversarias en
  verde por comportamiento vigente).
- Después: `test_sirius_aggregate_reviews.py` 34/34;
  `test_sirius_apply_verdict.py` 49/49 (las 45 previas intactas).
- Las adversarias son las mutaciones en las dos direcciones: parada de
  contenido de Claude sin bandera; razón de Codex distinta de timeout
  sin bandera; APPROVED/CHANGES sin bandera jamás; corrector con bandera
  ignorada; segundo reintento detenido por el candado.
- Censo de lectores del marcador nuevo: `sirius-reintento-ronda:` no es
  `sirius-verdict:` — ni `_STOP_MARKER_RE` (mirror_projection) ni el
  reanudador (`sirius_resume_on_command.sh`) pueden confundirlo.
- Validaciones obligatorias completas, códigos de salida verificados,
  citadas en la PR.

## Consecuencias

- Los tres casos del 04-09 se habrían absorbido solos: la ronda se
  re-arma en ~1 minuto y el reintento corre con ronda nueva.
- Una parada de infraestructura PERSISTENTE cuesta ahora una ronda extra
  antes de detenerse (el reintento fallido) — coste aceptado a cambio de
  eliminar la intervención humana del caso transitorio, que es el
  común.
- La deuda 12 de la bitácora queda saldada; la 10 (ready-for-merge)
  sigue abierta y va en su propio ADR.

## Alternativas descartadas y por qué

- **Reintentar en el recolector (opción 2):** cobertura parcial y
  presupuesto imposible, arriba.
- **Tope por contador en vez de por marcador:** un contador vive en el
  proceso; el marcador vive en la incidencia y sobrevive a cualquier
  reinicio — el candado debe ser material.
- **Incluir «resultado de Codex ausente/fuera de contrato» como
  reintentable:** puede ser un defecto real y repetible del recolector;
  reintentarlo taparía la señal. Si la práctica enseña que suele ser
  transitorio, se amplía con su medición. La medición llegó el mismo
  05-09 (#541: fallo declarado «Try again later», reintento manual que
  aprobó a la primera) y ADR-146 amplió exactamente el subtipo
  transitorio — el persistente sigue excluido, como aquí se pedía.
