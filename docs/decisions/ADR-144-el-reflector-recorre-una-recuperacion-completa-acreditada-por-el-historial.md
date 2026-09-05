# ADR-144 — El reflector recorre una recuperacion completa acreditada por el historial

- Estado: PROPUESTO
- Fecha: 2026-09-05
- Aprobación: la fusión de la PR de la incidencia #539 por el propietario.
- **Este ADR es además la nota de arranque de la rama**
  `feature/reflejo-recorrido-acreditado`: las cuatro preguntas y el criterio de
  parada de abajo se publicaron ANTES del primer commit de código (ADR-001,
  skill `disciplina-evidencia`).

## Contexto y problema

C1/C1b (ADR-136/ADR-137) reflejan el desenlace de GitHub en el almacén del
motor avanzando por la **foto actual** del espejo: `reflejar_desenlace` compara
el `WorkItem` guardado con lo que las etiquetas vigentes de la incidencia
proyectan, y calcula el camino mínimo hacia ese único objetivo.

El 05-09-2026, tras el ciclo de la incidencia #537, el run de reflejo de las
07:09 (33951766681) declaró la primera divergencia real, con estas palabras:

> «WI-20260905-034826: el motor está en estado=failed_safely fase=reparar y la
> incidencia proyecta estado=delivered fase=entregar; no hay camino hacia
> delante, no se toca nada» — «Pasos aplicados en total: 0».

Qué pasó de verdad, leído en el historial de la incidencia #537
(`gh issue view 537 --json comments`, 05-09-2026):

| hora (UTC) | marcador publicado | qué significa |
|---|---|---|
| 04:36:55 | `sirius-verdict:corrector:blocked:33944464077-1` | primera parada |
| 04:46:18 | `sirius-resume-stop:1c934781…` | PRIMERA reanudación, con permiso escrito |
| 05:17:04 | `sirius-verdict:corrector:FAILED_SAFELY:33945456417-1` | segunda parada |
| 05:17:10 | `sirius-notification:sirius:failed-safely:1c934781…` | etiqueta de la parada |
| 05:29:04 | `continua` (OWNER) | SEGUNDA orden de reanudación |
| 06:06:43 | `sirius-notification:sirius:repair-requested:786c82dc…` | el ciclo vivo otra vez |
| 06:49:29 | `sirius-notification:sirius:ready-for-merge:92e5b9f4…` | revisión aprobada |
| 07:00:51 | `sirius-notification:sirius:completed:92e5b9f4…` | cerrada y fusionada |

El motor recuerda ese WI hasta su parada de las 05:17. La incidencia siguió sin
él. Y la segunda reanudación **no dejó marcador nuevo**: el permiso escrito de
`sirius_resume_on_command.sh` se publica con `sirius_comment_once`, cuya clave
de idempotencia es el texto del marcador —`<!-- sirius-resume-stop:1c934781… -->`,
el mismo head que la primera reanudación—, así que el comentario no se duplicó.
Consecuencia exacta: `_interpretar_reanudacion_publicada` compara la posición
del último marcador de reanudación (04:46) con la de la última parada (05:17),
la parada es posterior, y devuelve `False`. Sin reanudación acreditada, la rama
`DELIVERED` de `reflejar_desenlace` ve un motor en `FAILED_SAFELY` y responde
lo correcto para lo que sabe: no hay camino hacia delante, no se toca nada
(fail-open, exit 0, memoria desactualizada como consecuencia).

El problema no es que el reflector se negara: es que **comparó dos fotos y no
miró el camino**. El historial de confianza de la incidencia sí acredita el
camino completo, marcador a marcador y en orden cronológico.

## Nota de arranque (disciplina de evidencia, ADR-001)

1. **¿Qué se construye?** Que `reflejar_desenlace` sepa AVANZAR el estado
   guardado hasta la foto actual cuando el historial de confianza acredita una
   secuencia de saltos **ya legales** que conecta ambos: anclando en el estado
   guardado, aplicando solo lo que falta, y anotando cada transición intermedia
   acreditada como suceso propio del diario, en orden. Ningún puerto nuevo,
   ninguna arista nueva del dominio, ninguna escritura en GitHub.
2. **¿Qué prueba lo falsifica?** Una prueba sobre un doble del espejo que
   reproduce el historial real de la #537 (motor en `failed_safely`/`reparar`,
   foto `sirius:completed`, notificaciones intermedias `repair-requested` →
   `ready-for-merge` → `completed`) y exige los cinco pasos del recorrido, más
   su segunda pasada a cero; y la prueba adversaria del contraejemplo: el mismo
   motor y la misma foto **sin** acreditación intermedia deben seguir
   declarando divergencia y no tocar nada. Las dos deben verse FALLAR contra el
   reflector de `main` antes del cambio.
3. **¿Qué NO cubre esto?** No toca `.github/**` ni ningún workflow; no toca
   `racha_siete_dias` ni el contador; no declara nada en
   `CLASES_CON_ESTADO_PROPIO` (C2 sigue apagado, ADR-101, va en su propia ficha
   DESPUÉS de este encargo); no arregla en código las incidencias con etiquetas
   de estado contradictorias (su limpieza fue operativa y ya está hecha); no
   corrige la deduplicación de `sirius_comment_once` que dejó la segunda
   reanudación sin marcador —eso es `scripts/automation`, fuera del alcance
   permitido de esta incidencia.
4. **Criterio de parada.** Si recorrer el camino acreditado exigiera aflojar la
   máquina de estados del `WorkItem` —una arista nueva, un `_require` relajado,
   un salto «puente» `failed_safely → delivered`— parar con
   `BLOCKED_BY_DECISION` en vez de hacerlo. Y si la única forma de acreditar la
   salida de una parada fuera aceptar la foto a secas (lo que reabriría
   CODEX-001, ronda 4, PR #530), parar igual.

**Predicción, escrita antes de correr nada:** el recorrido del caso vivo
produce entre 4 y 6 sucesos —reactivación más el camino de fase desde
`REPARAR` hasta la entrega— y cero en la segunda pasada.
**Resultado (medido después de correr las pruebas):** exactamente 5 —
`work_item_reactivated`, `work_item_repair_resumed`, `work_item_review_started`,
`work_item_review_approved`, `work_item_delivered`—, y cero en la segunda
pasada. Dentro del rango predicho, en su extremo bajo: el recorrido reproduce
los estados que el historial acredita, no cada vuelta del bucle
revisar-reparar que la incidencia dio de verdad (las dos vueltas de Quality no
dejaron notificación propia, porque `sirius:ci-pending` no es una de las seis
etiquetas que `notify-sirius-state.yml` vigila).

## Opciones consideradas

1. **Legalizar el salto `failed_safely → delivered`** en el reflector cuando la
   foto lo pide. Descartada: es exactamente la arista puente que el criterio de
   parada prohíbe, y borraría del diario las transiciones intermedias que sí
   ocurrieron.
2. **Aceptar la foto como acreditación suficiente para salir de una parada**
   (quitar el gate `reanudacion_publicada`). Descartada: reabre el defecto
   CODEX-001 de la ronda 4 de la PR #530 —una etiqueta de parada sustituida a
   mano se leería como orden del propietario.
3. **Recorrer los estados que el historial de confianza acredita**, anclando en
   el estado guardado y exigiendo al menos un estado acreditado estrictamente
   entre el ancla y el destino que el historial alcanza. Elegida.

## Decisión

El espejo de solo lectura (A3) publica un campo nuevo,
`MirroredWorkItem.historial_estados`: la secuencia cronológica de
`EstadoAcreditado` que los marcadores
`<!-- sirius-notification:sirius:<etiqueta>:<head> -->` del historial **de
confianza** prueban. Es la misma interpretación de etiqueta → (estado, fase)
que ya usa la proyección (`_LABEL_STATE`), aplicada al marcador que
`notify-sirius-state.yml` publica en cada cambio de etiqueta, con el mismo
filtro `es_autor_de_confianza` que el resto de la proyección. No hay marcador
nuevo ni escritura nueva: el reflector sigue solo leyendo.

`reflejar_desenlace` conserva intacto su cálculo por foto. Cuando —y solo
cuando— ese cálculo devuelve divergencia, intenta el **recorrido acreditado**:

1. **Ancla.** Busca en `historial_estados` la ÚLTIMA observación que coincide
   con el estado guardado del motor (mismo `estado`; misma `fase` cuando el
   marcador la trae). Sin ancla no hay recorrido.
2. **Acreditación intermedia.** Tiene que haber al menos una observación
   ESTRICTAMENTE ENTRE el ancla y el destino que el historial alcanza —su
   última observación—, y esa intermedia tiene que decir algo que la foto no
   dijera ya. Lo que se mide es el SALTO —¿hay algo entre el ancla y el
   destino?—, no la coincidencia con la foto. La primera redacción de este
   punto sí medía la coincidencia («de las observaciones posteriores al ancla,
   al menos una distinta de la foto») y eso NO filtraba nada cuando la foto
   vigente no es expresable como marcador: `notify-sirius-state.yml` solo
   vigila seis etiquetas, así que los tres pares `sirius:ci-pending` →
   (ACTIVE, COMPROBAR) y `sirius:review-requested`/`sirius:reviewing` →
   (ACTIVE, REVISAR) no aparecen nunca en el historial, la comparación era
   falsa por construcción y una sola observación posterior al ancla bastaba
   para recorrer. Y son justo las fotos que la pasada ve más a menudo, porque
   `reflejar-desenlace.yml` se dispara por `workflow_run`
   (corrección CLAUDE-REV-001, ronda 1, PR #540). Con la forma corregida, un
   historial que no acredita nada intermedio no acredita ninguna secuencia y
   se conserva el comportamiento de hoy: declarar y no tocar nada. Este
   requisito es lo que preserva CODEX-001: una etiqueta de parada sustituida a
   mano por la etiqueta activa es un salto de una sola observación, sin nada
   intermedio, y sigue rechazándose —ahora también cuando la foto ya se movió
   a `ci-pending` o `reviewing`.
3. **Saltos ya legales, uno a uno.** Cada observación posterior al ancla es un
   objetivo intermedio, y el plan de cada tramo lo calcula **la misma función**
   `reflejar_desenlace` sobre un espejo derivado del real con `estado`/`fase`
   sustituidos. Entre tramo y tramo, el `WorkItem` se avanza llamando a los
   métodos REALES del dominio (`WorkItem.reactivate`, `resume_after_repair`,
   `begin_review`…): si un tramo no fuera legal, el dominio levanta
   `IllegalTransitionError` y el recorrido entero se abandona. La máquina de
   estados es el juez, no una tabla paralela.
4. **Todo o nada.** Si cualquier tramo diverge o resulta ilegal, no se aplica
   ninguno: se devuelve la divergencia original, con su texto de hoy.

La acreditación de la salida de una parada dentro del recorrido es la
observación intermedia misma —un marcador que el bot publicó, fechado y
posterior a la parada—, no la foto. Y es **por tramo**, no una vez por
recorrido: un recorrido puede contener más de una parada (el historial real de
la #537 tiene dos), y la salida de la SEGUNDA la tiene que acreditar una
observación posterior a ELLA, distinta de la foto. La primera implementación
pasaba `reanudacion_acreditada=True` a todos los tramos, así que con un
historial `failed-safely → repair-requested → blocked-decision → completed` el
reflector resolvía solo el `NEEDS_DECISION` intermedio apoyándose en la foto
final: exactamente la salvaguarda que este párrafo declara
(corrección CODEX-001, ronda 1, PR #540). Con la acreditación por tramo, ese
recorrido se abandona entero; y si el historial sí acredita algo después de la
segunda parada, se recorre completo. El último tramo —el que va contra el
espejo real— no tiene por construcción ninguna observación posterior, así que
solo el marcador real (`espejo.reanudacion_publicada`) puede autorizarlo.
Fuera del recorrido, el gate `reanudacion_publicada` sigue exactamente como
estaba.

## Comprobación que la sostiene

- Historial real de la #537 leído con
  `gh issue view 537 --repo canelamoraguezandyjesus-bot/sirius --json comments`
  (tabla de arriba): confirma que la segunda reanudación no publicó marcador y
  que las tres notificaciones intermedias sí existen.
- `tests/engine/test_reflect.py`, sección G: siete pruebas -el caso
  vivo con sus cinco pasos y su segunda pasada a cero, el contraejemplo sin
  acreditación intermedia, la foto repetida, el ancla, el historial sin ancla,
  el tramo ilegal, y la garantía de que el recorrido no altera un plan que la
  foto ya resolvía.
- `tests/engine/test_reflect.py`, sección G bis (correcciones de la ronda 1 de
  la PR #540): seis pruebas más -la traza literal de CLAUDE-REV-001 (foto
  `sirius:reviewing`, una sola observación posterior al ancla); su gemela con
  foto `sirius:ci-pending`; la cara positiva de las dos, en la que el mismo
  motor y la misma foto no notificada SÍ recorren cuando el historial acredita
  algo intermedio; la misma medida del salto sin ninguna parada de por medio;
  la segunda parada que la foto final no acredita (CODEX-001); y su cara
  positiva, la segunda parada que sí sale cuando una observación posterior la
  acredita, con sus siete pasos aplicados.
- `tests/engine/test_reflect_cli.py::test_una_pasada_real_recorre_la_recuperacion_de_la_537`:
  la pasada ENTERA de `sirius-reflejar` -comentarios crudos, proyección real,
  plan y almacén- sobre un doble del espejo con los 22 comentarios de la #537.
  Comprueba los cinco sucesos en `store.list_events()` y la segunda pasada a
  cero. Su hermana
  `::test_sin_las_notificaciones_intermedias_la_misma_pasada_declara_y_no_toca_nada`
  es el contraejemplo sobre la misma pasada.
- Rojo previo, visto fallar: con el recorrido desactivado en
  `reflejar_desenlace` (una línea: `return por_foto`), caen exactamente tres
  pruebas —las dos del caso vivo y la del ancla— con el texto literal del run
  real: «no hay camino hacia delante, no se toca nada».
- Rojo previo de las dos correcciones de la ronda 1 de la PR #540, visto
  fallar: con `src/sirius_engine/reflect.py` restaurado al commit `d2b50384`
  (el head auditado) y las cinco pruebas nuevas puestas, `uv run pytest
  tests/engine/test_reflect.py -q` da «4 failed, 39 passed», incluida la traza
  literal de la revisión.
- Prueba por mutación (cinco sembradas, una prueba distinta cae con cada una):
  anclar en la PRIMERA coincidencia en vez de la última →
  `test_el_recorrido_ancla_en_la_ULTIMA_coincidencia_con_el_estado_guardado`;
  quitar la exigencia de acreditación intermedia →
  `test_la_foto_repetida_en_el_historial_no_es_acreditacion_intermedia`;
  aplicar el trozo bueno de un recorrido ilegal en vez de abandonarlo entero →
  `test_un_tramo_ilegal_abandona_el_recorrido_entero`; medir la acreditación
  contra la foto en vez del salto (`intermedias = posteriores` en vez de
  `posteriores[:-1]`) →
  `test_una_sola_observacion_posterior_tampoco_acredita_sin_ninguna_parada_de_por_medio`;
  y volver a acreditar todos los tramos de golpe
  (`reanudacion_acreditada=True`) →
  `test_la_segunda_parada_del_recorrido_no_sale_acreditada_por_la_foto_final`.
- Validaciones obligatorias completas, sobre el árbol de la ronda 1 de
  correcciones de la PR #540: `uv run ruff format --check .` («602 files
  already formatted»), `uv run ruff check .` («All checks passed!»),
  `uv run mypy src tests` («Success: no issues found in 570 source files») y
  `uv run pytest` («4951 passed, 15 skipped, 2 xfailed in 837.22s», exit 0).
  Más `git diff --check`, limpio. La cifra anterior de este ADR —«4945
  passed», con `scripts/check.ps1`— era la del commit `d2b50384`: las seis que
  la separan de 4951 son exactamente las seis pruebas nuevas de la sección G
  bis (`pytest --collect-only -q` da 4962 en `d2b50384` y 4968 aquí).

## Consecuencias

- El diario del motor recupera las transiciones que se perdió mientras no
  miraba: un WI parado y luego recuperado deja de quedarse desactualizado para
  siempre.
- El espejo gana un campo (`historial_estados`) y una interpretación
  (`sirius-notification`). Cualquier consumidor del espejo puede usarla; hoy
  solo la usa el reflector.
- La deduplicación de `sirius_comment_once` sigue dejando sin marcador la
  segunda reanudación sobre el mismo head. Este ADR no la arregla: la rodea
  leyendo otra evidencia. Si alguna vez se corrige, el recorrido acreditado
  sigue siendo correcto —solo dejará de ser el único camino.

## Alternativas descartadas y por qué

- **Interpretar también `sirius-quality:<head>:…` y `sirius-verdict:<rol>:…`
  como estados acreditados** (un veredicto del corrector probaría fase
  `REPARAR`, un evento Quality probaría `COMPROBAR`). No hizo falta: las
  notificaciones de etiqueta bastan para el caso vivo, y `_camino_de_fase` ya
  rellena las fases intermedias sin inventarse nada. Añadir tres tablas de
  interpretación más habría ampliado la superficie sin comprar ninguna prueba.
- **Anclar en la primera coincidencia en vez de la última.** Reproduciría
  transiciones que el motor ya tenía anotadas: el ancla correcta es la más
  reciente, que es donde el motor se quedó.
