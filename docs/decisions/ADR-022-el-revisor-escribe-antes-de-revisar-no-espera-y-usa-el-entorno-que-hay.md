# ADR-022 — Endurecer el prompt del revisor: veredicto provisional, prohibición de esperar nada (subagentes incluidos) y revisión con el entorno acotado que hay

- Estado: PROPUESTO
- Fecha: 2026-08-16
- Aprobación: la fusión de la PR #180 por el propietario.

## Contexto y problema

ADR-021 corrigió en `corrector.md` una forma concreta de terminar sin veredicto
—cerrar el turno esperando trabajo en segundo plano— y dejó escrito, en sus
Consecuencias, que la misma regla para los otros dos roles quedaba **pendiente**,
y en su Criterio de parada, por qué no se hacía entonces: «parchear sin caso
delante es la familia de defecto que este repositorio lleva corrigiendo. Si
aparece, se corrige entonces, con su run».

Apareció, con su run. La siguiente ronda de revisión de la incidencia #177
(run 31963233730, job 95204301715, sobre la PR #178) terminó sin escribir
`sirius_verdict.json`. El volcado del modelo lo deja literal: último mensaje
«Standing by for the three background review agents to report back before writing
the final verdict», `subtype: success`, `terminal_reason: completed`, 106 s de los
30 min del paso. La agregación registró el archivo ausente y la incidencia se
detuvo. Misma familia que el corte del corrector, con otro disfraz: allí un
`pytest` en segundo plano, aquí tres subagentes.

El mismo run mostró un segundo desperdicio, distinto y menor: tres órdenes
denegadas. El revisor intentó instalarse `uv` con `curl` y perdió dos bloques
enteros de comparación de la PR. `reviewer.md` no le decía nada sobre la
superficie real en la que corre.

`reviewer.md` tampoco tenía la protección más antigua del repositorio en este
terreno: el veredicto provisional que nació de la incidencia #135 y que
`corrector.md` lleva desde entonces. Un corte del revisor —por turnos, por
tiempo o por creerse en una conversación— no dejaba diagnóstico ninguno.

## Criterio de parada (escrito ANTES de decidir)

Publicado en la nota de arranque
([#177, comentario 5309140535](https://github.com/canelamoraguezandyjesus-bot/sirius/issues/177#issuecomment-5309140535)),
**antes del primer commit de la rama**, con sus cuatro preguntas. Lo que ata:

- Alcance limitado a `scripts/automation/prompts/reviewer.md` y
  `tests/automation/test_sirius_review_workflow.py`.
- Si el arreglo exigiera cambiar permisos, workflows o el contrato de salida del
  rol más allá de escribir antes el `FAILED_SAFELY` que ya está en su
  vocabulario, **parar y consultar**.
- Lo que NO se garantiza, dicho de antemano: no impide todas las formas de
  terminar sin veredicto, solo la demostrada; no amplía ningún permiso; no
  arregla la respuesta-por-comentario de Codex; no toca la política de
  convergencia, por decisión expresa del propietario.

Ninguno de los tres límites se rozó: el diff son esos dos archivos y nada más.

## Opciones consideradas

1. **Ensanchar `.claude/settings.json`** para que el revisor pueda instalarse lo
   que le falte: descartada por decisión expresa del propietario en esta misma
   conversación, y por el fondo: el perímetro es la garantía de que un revisor de
   solo lectura no escribe. El problema no era que le faltara herramienta —el
   diff se leía con `gh pr diff`—, era que no se lo habíamos dicho.
2. **Subir topes** (turnos o tiempo del paso): descartada — no se agotó ninguno
   (106 s de 30 min). Habría enmascarado la causa, igual que en ADR-021.
3. **Detectarlo desde el arnés** (fallar el paso si quedan procesos huérfanos):
   descartada por ahora — más mecanismo del que el problema pide y toca
   `.github/workflows/`, con la frontera de ADR-002.
4. **Decírselo en el prompt, con la evidencia dentro, y fijarlo con pruebas
   estructurales**: elegida.

## Decisión

Tres secciones nuevas en `scripts/automation/prompts/reviewer.md`:

1. **Veredicto provisional.** `FAILED_SAFELY` como PRIMERA acción, en la ruta de
   `SIRIUS_VERDICT_FILE`, sustituido por el definitivo como ÚLTIMA. Lo escribe el
   revisor, no el workflow: un veredicto sembrado por el envoltorio se publicaría
   como suyo sin que lo hubiera emitido. El provisional no lleva
   `reviewed_head_sha` ni `observations` a propósito — `FAILED_SAFELY` es el
   único veredicto que no afirma nada sobre ninguna versión.
2. **Anti-espera, con los subagentes nombrados.** Nada en segundo plano; si usa
   algún subagente permitido, recoge su resultado **dentro del mismo turno**
   antes de escribir el veredicto, y si no puede garantizarlo, no los usa. Lo que
   no cabe en el turno es un `FAILED_SAFELY` con diagnóstico, no una espera. La
   diferencia con ADR-021 es esta cláusula: allí el vehículo del fallo fue un
   comando, aquí fueron agentes, y una regla que solo hable de comandos no cubre
   el caso observado.
3. **Entorno acotado.** `Quality` ya llegó verde antes de esta fase, así que el
   revisor no reconstruye el entorno de CI: no instala herramientas ni
   dependencias y no usa `curl` ni `wget`. Compara con `gh pr diff`, `gh pr
   view`, `gh api` y las lecturas permitidas. Si falta una herramienta hay dos
   salidas y ninguna más —adaptar la revisión o emitir `FAILED_SAFELY`—;
   improvisar una instalación no es una tercera.

Y cuatro pruebas estructurales en `tests/automation/test_sirius_review_workflow.py`
que **atan el texto a hechos verificables, no a su redacción**: los topes que el
prompt cita existen de verdad en el workflow, y lo que el prompt prohíbe o
recomienda coincide con la lista real de `.claude/settings.json`. Una instrucción
de entorno que mienta gastaría el turno en denegaciones, que es el fallo que la
sección viene a evitar.

## Comprobación que la sostiene

- **Frase literal y desenlace** del run 31963233730 leídos del volcado del job
  95204301715: `result` «Standing by for the three background review agents…»,
  `terminal_reason: completed`, `duration_ms: 105915`, y tres
  `permission_denials`.
- **Corrección de un diagnóstico propio.** La nota de arranque describía dos de
  esas denegaciones como «comparaciones `git` contra `origin/main`». Al releer el
  log para redactar el prompt, la causa real resultó ser otra: ambos bloques
  incluían **`git merge-base`**, que la lista de denegación captura con el patrón
  `git merge*`, y ambos eran órdenes compuestas con `;`, así que una sola
  denegada se llevó el bloque entero. El prompt cita la causa verificada, no la
  supuesta.
- **El provisional no rompe nada aguas abajo**, comprobado en el código antes de
  escribirlo: `require_reviewed_head` (`sirius_apply_verdict.sh`) solo se exige
  para `REVIEW_APPROVED`/`CHANGES_REQUESTED`, y la regla 3 de
  `sirius_aggregate_reviews.py` acepta un `FAILED_SAFELY` de Claude y arrastra su
  `summary` al comentario de parada.
- **Las pruebas discriminan**: las once cadenas que exigen están AUSENTES del
  `reviewer.md` anterior (contrastado contra `git show HEAD:...`), así que los
  tres tests de contenido fallan sobre la versión previa. El cuarto es un ancla:
  comprueba que el workflow sigue insertando `reviewer.md`, para que los otros
  tres no puedan pasar en verde sobre un archivo muerto.
- **Validaciones obligatorias en verde** sobre `4192111`: `ruff format --check .`
  (322 archivos), `ruff check .`, `mypy src tests` (316 archivos),
  `pytest tests/automation/` (391 pruebas), `git diff --check` limpio.

## Consecuencias

- El revisor deja de perder rondas por esta causa concreta y, si lo cortan por
  cualquier otra, deja diagnóstico en vez de silencio. **No se afirma que cierre
  todas las formas de terminar sin veredicto**: cierra la demostrada.
- Los tres roles quedan desparejos a propósito: `implementer.md` sigue sin la
  regla anti-espera, porque no hay run que demuestre que le ocurra. Se corregirá
  cuando aparezca, con su run, como se hizo aquí.
- La deriva documental de ADR-021 —`Estado: PROPUESTO` pese a que su propia
  cabecera declara aprobado por la fusión de #179, ya en `main`— queda
  **señalada y sin tocar**: corregirla aquí ensancharía el alcance que este mismo
  ADR se fijó. Es la misma familia que E0 saneó para ADR-019.
- La respuesta-por-comentario de Codex del mismo run sigue abierta y es otra
  frontera.

## Alternativas descartadas y por qué

Las opciones 1–3 de arriba. Además: extender la regla a los tres prompts de una
vez (sería el parcheo sin caso delante que ADR-021 rechazó explícitamente); y
convertir el veredicto provisional en algo que escriba el workflow antes de
arrancar al modelo (publicaría como suyo un veredicto que nunca emitió, que es
justo el defecto que esta automatización lleva trece hallazgos corrigiendo).
