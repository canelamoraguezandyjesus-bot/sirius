# ADR-226 — Cuando Codex declara que no revisa y Claude pidió cambios, la ronda entrega los hallazgos de Claude en vez de tirarlos

- Estado: APROBADO
- Fecha: 2026-10-01
- Aprobación: la fusión de la PR #673 por el motor con aprobación dual (ADR-205).
- Nota de arranque:
  `docs/audits/arranque-2026-10-01-la-ronda-no-tira-la-revision-de-claude-cuando-codex-declara-que-no-revisa.md`,
  confirmada en `ae46aa09` antes del primer commit de arreglo, con las cuatro
  preguntas, las predicciones y el criterio de parada.

## Contexto y problema

La revisión dual (contrato §4.1) combina el veredicto de Claude y el de Codex
con un agregador determinista, `scripts/automation/sirius_aggregate_reviews.py`,
cuya regla 3 dice «`FAILED_SAFELY` de cualquiera → `FAILED_SAFELY`» y va antes
que la 5 («`CHANGES_REQUESTED` de cualquiera → `CHANGES_REQUESTED`»). Cuando el
conector de Codex contesta que **no va a revisar** —«You have reached your
Codex usage limits for code reviews», «To use Codex here,», «Codex Review:
Something went wrong»—, el recolector lo reconoce desde ADR-060 (un error del
conector no es silencio; el subtipo transitorio, desde ADR-146) y termina su
parte en `FAILED_SAFELY` (`codex-fallo-declarado`, o el subtipo transitorio) sin
agotar el plazo. Bien. Pero el agregador corre **después** del revisor de Claude,
y la regla 3 tira lo que Claude ya entregó.

La bitácora del ciclo lo midió (entrada 106, 13-09-2026, #581, ronda 11): el
revisor de Claude corrió entero —44 turnos, `total_cost_usd` 3,31 según la
línea `result` de su log— y escribió su veredicto; Codex contestó la cuota; la
ronda terminó en `FAILED_SAFELY` y el veredicto de Claude se descartó sin
publicarse. Sobre el volcado de septiembre de la mina (30 incidencias):
**13 paradas** así, en 6 incidencias (#541; #545 ×5; #566 ×3; #581 ×2; #592;
#599). En todas el revisor de Claude ya había terminado. Una tiene coste
medido; las otras doce no dejaron cifra porque el veredicto se tiró. Y el
01-10-2026 a las 13:58 UTC la cuota volvió a agotarse, con 30 peticiones de
revisión en el día.

Cada una de esas paradas cuesta, además de la revisión pagada, un `continua`
del propietario y una ronda nueva que vuelve a pagar a Claude para que diga lo
mismo. La mitad del veredicto que sí llegó —los hallazgos de Claude— es justo
lo que el corrector necesita para seguir trabajando mientras Codex no tiene
cuota.

## Criterio de parada (escrito ANTES de decidir)

Copiado de la nota de arranque:

- Si entregar la mitad del veredicto exigiera un campo nuevo que
  `sirius_apply_verdict.sh` no sabe publicar, parar: el aplicador no se toca.
- Si el contrato §4.1 o un ADR vigente prohibiera expresamente que un
  `CHANGES_REQUESTED` salga sin Codex (y no solo la aprobación), parar y
  llevarlo a la lista de decisiones del propietario.
- Cuatro mutaciones tienen que caer: M1 la excepción desactivada; M2 el
  timeout dentro de la excepción; M3 la excepción abierta a `REVIEW_APPROVED`
  de Claude; M4 el resumen sin la constancia de que Codex no revisó.
- Dos rondas de revisión externa con defectos de la misma familia → raíz.

Ninguna de las dos primeras paró: el resumen agregado es el campo que el
aplicador ya publica, y el contrato prohíbe aprobar y degradar, no entregar
hallazgos.

## Opciones consideradas

1. Dejarlo como está: la regla 3 protege la revisión dual, y cada parada
   cuesta una revisión pagada, un `continua` y una ronda repetida.
2. **Una excepción acotada a la regla 3** (la elegida): si Codex *declaró* que
   no revisa y Claude pidió cambios con observaciones válidas sobre el head
   esperado, la ronda sigue a la regla 5 con las observaciones de Claude y deja
   escrito que Codex no revisó. Aprobar sigue exigiendo a los dos.
3. La misma excepción también para el `timeout` de Codex. Descartada: un
   timeout no es una declaración, Codex puede estar revisando todavía, y su
   parada reintentable (ADR-141) ya re-arma la ronda una vez.
4. Leer la cuota antes de disparar (la deuda 12 tal como la bitácora la
   enuncia). No hay llamada que la exponga; lo único observable es la última
   respuesta del conector en el repositorio, y una heurística sobre ella
   saltaría rondas después de que la cuota vuelva. Con la opción 2 un disparo
   «de más» no tira nada, así que la heurística pierde su razón.
5. Aprobar solo con Claude cuando Codex no tiene cuota. Descartada: es la
   degradación silenciosa que el contrato §4.1 prohíbe, y la única de las dos
   asimetrías que no se puede deshacer.

## Decisión

En `scripts/automation/sirius_aggregate_reviews.py`:

1. Las razones con las que el recolector dice que el conector **declaró** que
   no revisa quedan nombradas: `RAZONES_CON_LAS_QUE_CODEX_DECLARA_QUE_NO_REVISA`
   = {`codex-fallo-declarado`, `codex-fallo-declarado-transitorio`}. El
   `timeout` no está, a propósito.
2. La regla 3 deja pasar a la 5 el caso en que Codex declaró que no revisa
   **y** Claude está en `CHANGES_REQUESTED` con observaciones válidas sobre el
   head esperado (las reglas 1 y 2 ya pasaron). El veredicto agregado es
   `CHANGES_REQUESTED` con las observaciones de Claude; `sources.codex` lleva
   `status` y `reason`; y el resumen dice que Codex no revisó este head, cita
   lo que dijo el conector, y que se le volverá a pedir sobre el head corregido
   sin que nada se apruebe sin él.
3. Todo lo demás sigue igual: con Claude en `REVIEW_APPROVED` o en
   `BLOCKED_BY_DECISION` la declaración de Codex para como hoy; el timeout
   para y re-arma como ADR-141; el fallo transitorio con Claude aprobando
   re-arma como ADR-146 (y con Claude pidiendo cambios, entrega los hallazgos:
   no hay nada que re-armar); ni el recolector ni `sirius_apply_verdict.sh`
   cambian de comportamiento.

Prosa que lo acompaña: la precedencia del contrato §4.1 y su regla «Codex es
obligatorio», la cabecera de `review-sirius-work.yml`, el docstring de
`_declara_fallo_del_conector` y una nota en ADR-146.

## Comprobación que la sostiene

- `tests/automation/test_sirius_aggregate_reviews.py`, siete pruebas nuevas:
  el caso de la entrada 106 termina en `CHANGES_REQUESTED` con las
  observaciones `CLAUDE-` y la constancia en el resumen; con Claude aprobando
  sigue parando; el timeout no entrega nada y sigue siendo reintentable; el
  fallo transitorio con hallazgos los entrega; un `CHANGES_REQUESTED` sobre
  otro head sigue parando por la regla 2; `BLOCKED_BY_DECISION` no cambia; una
  razón desconocida del recolector no entrega nada. La primera, vista fallar
  contra el agregador anterior (`FAILED_SAFELY`, `observations: []`).
- Mutaciones sobre el agregador, con las cinco pruebas de la excepción
  ejecutadas y el fichero restaurado (`diff -q` limpio):

| | Mutación | Resultado |
|---|---|---|
| M1 | la excepción desactivada (`claude_lleva_la_ronda = False`) | caen 2 (el caso de la entrada 106 y el fallo transitorio con hallazgos) |
| M2 | `timeout` dentro de las razones que declaran | cae `el_timeout_de_codex_no_entrega_los_hallazgos_de_claude` |
| M3 | la excepción abierta también a `REVIEW_APPROVED` de Claude | cae `con_claude_aprobando_el_fallo_declarado_de_codex_sigue_parando` (la ronda aprobaría sin Codex) |
| M4 | el resumen sin «Codex no revisó este head» | cae el caso de la entrada 106 |

- Baterías: `test_sirius_aggregate_reviews.py` (43), `test_sirius_review_workflow.py`
  y `test_automatizacion_congelada_de_main.py` (84 en conjunto),
  `test_sirius_codex_review.py` (81): en verde. `ruff format`, `ruff check` y
  `mypy` sobre los tres ficheros de Python tocados, sin avisos; el comprobador
  de documentos sobre la nota, el contrato, ADR-146 y este ADR.
- La línea base de 13 paradas sale de contar, en el volcado de la mina, los
  comentarios del bot que llevan `FAILED_SAFELY` y `codex-fallo-declarado`
  (6 incidencias); el coste de 3,31 $ es la línea `result` del log del run
  34733643021 citada en la entrada 106.

## Consecuencias

- Mientras Codex no tenga cuota, el corrector sigue trabajando con los
  hallazgos de Claude; la aprobación final espera a Codex, como siempre. Una
  parada por cuota deja de costar una revisión pagada y un `continua`.
- Puede haber varias rondas seguidas solo con hallazgos de Claude; las acotan
  la medida de progreso entre rondas (`sirius_convergence`) y el detector de
  familia repetida, y cada una deja
  escrito que Codex no revisó. Cuando Claude apruebe, la ronda para como hoy.
- La mitad de la mejora 9 de la mina que es el reloj del implementador
  (entradas 92 y 94) sigue pendiente: es otro mecanismo y lleva su propia nota.
- H-226 en el registro de defectos.

## Alternativas descartadas y por qué

Las opciones 1, 3, 4 y 5 de arriba: la 1 porque paga tres veces lo mismo; la 3
porque un timeout no demuestra que Codex no vaya a revisar; la 4 porque no hay
dato que leer y la heurística tendría falsos saltos; la 5 porque es la
degradación que el contrato prohíbe.

## La lección

- familia: `parada-segura-que-tira-lo-ya-pagado`
- sin esto se repetiría: tratar toda parada de un revisor como pérdida del veredicto del otro, aunque el que para haya declarado que no va a revisar y el otro ya haya entregado hallazgos pagados; la asimetría que protege (no aprobar sin los dos) se conserva sin tirar el trabajo hecho.
- lo hace cumplir: `tests/automation/test_sirius_aggregate_reviews.py`
