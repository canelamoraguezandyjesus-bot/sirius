# ADR-230 — Registrar qué revisores tuvo cada ronda y medir la convergencia y las familias solo entre rondas comparables

- Estado: APROBADO
- Fecha: 2026-10-02
- Aprobación: la fusión de la PR #678 por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-02-una-ronda-en-la-que-codex-no-reviso-no-es-una-ronda-entera.md`,
  confirmada en `3fd6776a` antes del primer commit de arreglo, con las cuatro
  preguntas, las dos predicciones y el criterio de parada.

## Contexto y problema

ADR-226 (PR #673, fusionada el 01-10-2026) hace que, cuando Codex declara que
no revisa —cuota agotada, «Try again later»— y Claude pidió cambios, la ronda
entregue los hallazgos de Claude al corrector en vez de tirarlos. La revisión
independiente de esa PR, leída después de la fusión, señaló lo que ADR-226 no
midió: esa ronda publica un `RONDA_HALLAZGOS` igual que una ronda entera, y las
dos piezas que leen el historial no saben que a esa ronda le falta un revisor.

- `sirius_convergence.decide` compara conjuntos de huellas entre rondas. Una
  ronda solo de Claude tiene menos huellas que la anterior —las de Codex no
  están porque nadie las buscó—: cuenta como progreso falso; y cuando Codex
  vuelve, sus huellas «reaparecen» y la puerta bloquea por `reaparicion` sin
  que nada haya regresado.
- `detectar_familia_repetida` cuenta rondas consecutivas por fichero: una
  ronda sin Codex en medio rompe el tramo de un fichero que Codex señala, y
  una familia real se queda sin aviso.

Ninguna ronda real ha pasado aún por este camino (desde la fusión de ADR-226
no ha habido trabajo vivo en el motor). La cifra de partida es la de la
bitácora: 13 paradas por cuota en septiembre (entrada 106), que desde ADR-226
son rondas solo de Claude; y la cuota de Codex se agotó dos veces el 01-10
(14:07 y 19:44 UTC). El camino se va a usar.

## Criterio de parada (escrito ANTES de decidir)

El de la nota de arranque, publicado antes de tocar código:

- Las dos pruebas de las predicciones tienen que verse fallar contra el
  comportamiento de `main` y pasar con el cambio; las baterías de
  convergencia, agregador, detector y aplicador de veredictos siguen en verde
  sin tocar ninguna prueba existente salvo para añadir `reviewers` donde haga
  falta.
- Mutaciones que tienen que caer: M1 el registro sin `reviewers`; M2 `decide`
  sin proyectar; M3 `decide` sin omitir las rondas parciales cuando la actual
  es entera; M4 el detector sin transparencia; M5 el agregador manda también
  las observaciones de Codex en una ronda que Codex no revisó.
- Si para evitar el falso `BLOCK` hiciera falta cambiar la definición de
  progreso entre rondas enteras, parar: es otra decisión, sobre la política y
  no sobre las rondas parciales. No hizo falta.
- H-230 registrada; la guarda del registro vista caer antes y pasar después.

## Opciones consideradas

1. **Dejarlo como está** y que el propietario levante con `continua` los
   bloqueos falsos. Rechazada: es exactamente el trabajo que ADR-226 vino a
   ahorrarle, y el detector de familias no bloquea, calla; nadie vería lo que
   deja de avisar.
2. **No publicar `RONDA_HALLAZGOS` en las rondas parciales.** Rechazada: la
   puerta del corrector necesita el registro para medir, y el detector
   perdería las apariciones que Claude sí vio.
3. **Arrastrar los hallazgos anteriores de Codex como pendientes** en la ronda
   parcial. Rechazada: inventa observaciones sobre un head que nadie revisó, y
   es lo que ADR-226 prohíbe (nada se afirma de Codex sin Codex).
4. **Decir en el registro qué revisores tuvo la ronda y que cada lector haga
   con eso lo suyo**: la convergencia compara solo entre rondas comparables y
   el detector trata la ronda parcial como transparente para lo que nadie
   buscó en ella. Elegida.

## Decisión

1. **El veredicto agregado dice qué revisores tuvo la ronda.** La regla 5 de
   `sirius_aggregate_reviews.py` añade `reviewers`: `["CLAUDE", "CODEX"]` en
   la revisión dual con los dos revisando, `["CLAUDE"]` sin revisión dual o
   cuando Codex declaró que no revisaba (ADR-226). En ese último caso la ronda
   lleva **solo** las observaciones de Claude: nada de Codex entra, ni como
   observación ni como revisor, porque nadie lo buscó en ese head.
2. **El registro de ronda lo lleva.** `round_record(..., reviewers=)` escribe
   `reviewers` en el `RONDA_HALLAZGOS`; `sirius_apply_verdict.sh` lo copia del
   veredicto al construir el registro, y `cmd_record` lo lee.
   `parse_round_records` lo normaliza (`revisores_declarados`: lista de
   nombres en mayúsculas, o `None`). **Un registro sin el campo es una ronda
   entera**: los anteriores a esta decisión no cambian de significado.
3. **La convergencia compara solo entre rondas comparables.** Antes de medir,
   `decide` proyecta el historial sobre los revisores de la ronda actual
   (`_proyectar_sobre_la_ultima_ronda`): con la actual entera, las parciales
   no cuentan; con la actual parcial, de las enteras solo cuentan los
   hallazgos de los revisores que sí revisaron ahora, con las huellas, los
   pendientes y la gravedad pegajosa recalculados sobre lo que queda. Los
   registros sin `reviewers` cuentan como el conjunto conocido (enteros); un
   historial en el que nadie declara nada se mide tal cual. La definición de
   progreso entre rondas enteras no cambia. El campo `rounds` de la decisión
   es el número de rondas comparables.
4. **El detector de familias trata la ronda parcial como transparente** para
   los ficheros que no aparecen en ella (`rondas_parciales`,
   `_tramos_consecutivos(..., transparentes)`): un fichero señalado en las
   rondas 3, 5 y 6 con la 4 solo de Claude es un tramo de tres. Si el fichero
   sí aparece en la parcial, cuenta como una aparición más. El `detalle`
   publicado conserva la cabecera «recibe hallazgos en N rondas consecutivas
   (rondas a-b)» que leen quienes lo reproducen (la mina) y nombra la ronda
   saltada.
5. **Lo que no cambia**: la regla de ADR-226 (Claude lleva la ronda; nada se
   aprueba sin Codex), la medida de progreso contra la mejor marca histórica,
   el umbral de tres del detector, los marcadores y los avisos.
6. **De paso, sin medición propia**: los defectos de prosa de ADR-226 que la
   misma revisión listó —citaba ADR-146 donde tocaba ADR-060, hablaba de un
   «presupuesto de rondas» que no existe, su nota de arranque no decía
   «Fecha»— y la ficha `_codex_sin_cuota` de las pruebas del agregador, que
   dejaba `reviewed_head_sha` a `None` cuando el recolector escribe el head.

## Comprobación que la sostiene

- Nota de arranque en `3fd6776a`, antes del primer commit de arreglo.
- **Predicción 1** (`test_una_ronda_solo_de_claude_no_hace_reaparecer_los_hallazgos_de_codex`):
  entera → solo Claude → entera. Con el código de `main` para esa decisión
  (mutación M3, que es exactamente no omitir las parciales) la puerta da
  `BLOCK` `reaparicion`; con el cambio, `CONTINUE` `sin-progreso-aislado` y dos
  rondas comparables. Confirmada.
- **Predicción 2** (`test_una_ronda_en_la_que_codex_no_reviso_no_rompe_el_tramo_de_un_fichero_que_codex_senala`):
  fichero en las rondas 3, 5 y 6 con la 4 solo de Claude. Con el código de
  `main` (mutación M4, sin transparencia) no hay familia; con el cambio,
  familia `(3, 5, 6)` y el detalle nombra la ronda 4. Confirmada.
- Además: `test_una_ronda_solo_de_claude_se_mide_contra_lo_que_claude_veia_en_las_enteras`
  (dos rondas parciales seguidas sin que Claude vea avance: `BLOCK`
  `sin-progreso`, que es lo que pasó; sin proyectar era un progreso falso y
  un aislado), `test_un_historial_anterior_a_adr_230_se_lee_como_rondas_enteras`
  (historial mixto; y el historial sin declaraciones sigue dando `reaparicion`
  como siempre), `test_el_registro_lleva_los_revisores_de_la_ronda_y_sin_ellos_no_inventa_nada`,
  `test_los_revisores_declarados_se_leen_y_sin_ellos_la_ronda_es_entera`,
  `test_el_veredicto_de_cambios_dice_que_revisores_tuvo_la_ronda`,
  `test_una_ronda_que_codex_no_reviso_no_lleva_nada_de_codex`, el `record` del
  CLI y el registro publicado por `sirius_apply_verdict.sh` con `reviewers`.
- Mutaciones, cada una aplicada y vista caer con los ficheros restaurados
  después (`cmp` contra la copia):

| Mutación | Qué se rompe | Resultado |
|---|---|---|
| M1 | el registro no escribe `reviewers` | caen 5 (registro, CLI, las dos predicciones de convergencia, el historial mixto) |
| M2 | `decide` no proyecta las enteras a los revisores actuales | cae `se_mide_contra_lo_que_claude_veia_en_las_enteras` |
| M3 | `decide` no omite las parciales cuando la actual es entera (el código de `main`) | caen 2 (predicción 1 y el historial mixto) |
| M4 | el detector sin transparencia (el código de `main`) | cae la predicción 2 |
| M5 | el agregador manda también lo de Codex en una ronda que Codex no revisó | cae `una_ronda_que_codex_no_reviso_no_lleva_nada_de_codex` |

- Baterías: `test_round_history.py`, `test_round_family_detector.py`,
  `test_round_family_detector_cli.py`, `test_sirius_convergence.py`,
  `test_sirius_aggregate_reviews.py` (129 en verde), `test_sirius_apply_verdict.py`
  entera; `mypy src` y `ruff` sin avisos; comprobador de documentos sin avisos.
- La medida que no se puede tomar aquí: la primera ronda real en la que Codex
  no revise. Queda para la bitácora y la mina de octubre: el `RONDA_HALLAZGOS`
  llevará `["CLAUDE"]` y la ronda siguiente con Codex no debe bloquear por
  `reaparicion`.

## Consecuencias

- Una ronda sin Codex ya no se compara con las enteras: ni progreso falso ni
  reaparición falsa; y dos rondas parciales seguidas sin avance bloquean por
  `sin-progreso`, que es la señal correcta.
- Una familia que Codex señala sobrevive a una ronda en la que Codex no miró.
- El registro de ronda gana un campo opcional; lo que ya está publicado no
  cambia de lectura. El contrato de operación lo documenta (§ del registro de
  ronda).
- Los guiones de la mina de septiembre (PR #665) leen la cabecera «(rondas
  a-b)» del detalle, que se conserva; la ronda saltada va después, fuera del
  paréntesis. Viven en la PR #665, rama `claude/mina-de-septiembre-entero`.

## Alternativas descartadas y por qué

Las opciones 1 a 3 de arriba: dejar que el propietario pague los bloqueos
falsos, callar el registro de la ronda parcial o inventar hallazgos de Codex
sobre un head que no revisó.

## La lección

- familia: `registro-sin-decir-quien-lo-hizo`
- sin esto se repetiría: comparar una ronda a la que le falta un revisor con rondas enteras y leer la ausencia de sus hallazgos como progreso, y su vuelta como reaparición
- lo hace cumplir: tests/automation/test_sirius_convergence.py
