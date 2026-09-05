# ADR-147 — La salida de una parada la acredita el permiso escrito del propietario

- Estado: PROPUESTO
- Fecha: 2026-09-05
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario o
  por su operador bajo la autorización vigente del 05-09. No toca `.github/**`
  ni ningún workflow: vive entero en `src/sirius_engine/` y sus pruebas.

## Contexto y problema

El reflector (`sirius-reflejar`, ADR-136/ADR-137) compara DOS FOTOS: el estado
guardado en el almacén del motor y lo que las etiquetas vigentes de la
incidencia proyectan. Cuando entre esas dos fotos ocurrió una recuperación
entera sin que ninguna pasada la observara, no hay salto legal entre ellas y
el reflector declara divergencia para siempre — fail-open correcto, memoria
desactualizada.

El caso vivo es WI-20260905-034826 (incidencia #537): el almacén recuerda
`failed_safely/reparar` (parada de las 05:17 del 05-09) mientras GitHub dice
`completed` desde las 07:00; el run de reflejo 33951766681 declaró «no hay
camino hacia delante, no se toca nada».

El encargo #539 intentó cerrarlo y **paró por el freno de convergencia**: tres
rondas encontraron la MISMA familia de defecto —el criterio de acreditación se
apoyaba, por una puerta u otra, en la foto vigente— y una premisa rota. La
rama `feature/reflejo-recorrido-acreditado` y la PR #540 quedan sin fusionar
como material de partida: su recorrido acreditado y sus pruebas valen; su
criterio de acreditación, no.

El encargo #545 fija el criterio de antemano, y su primera ronda **midió falsa
una premisa del despacho** antes de escribir una línea de código: el historial
de #537 NO contiene ningún marcador de reanudación posterior a la parada de
las 05:17. Contiene la ORDEN `continua` del propietario de las 05:29:04Z. El
mecanismo está confirmado: `sirius_resume_on_command.sh` publica su marcador
con `sirius_comment_once`, que deduplica por el TEXTO COMPLETO del marcador
(`scripts/automation/sirius_issue.sh`), y el marcador de `sirius-resume-stop`
lleva solo el head; como el corrector había fallado sin empujar nada, el head
no se movió y el segundo recibo era byte a byte idéntico al primero, así que
no se publicó. **Consecuencia general, no anecdótica: siempre que el
propietario reanuda dos veces sobre el mismo head, el historial de confianza
es estructuralmente incapaz de contener un marcador posterior a la segunda
parada.**

El propietario registró la decisión que resuelve esa contradicción
(comentario «Decisión del propietario registrada», #545): se amplía lo que
acredita la salida de una parada a las DOS formas del permiso escrito del
propietario, y se corrige —no se elimina— el caso de aceptación del caso vivo.

## Nota de arranque (cuatro preguntas, ANTES del primer commit de código)

**1. ¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en
`sirius_engine.reflect.reflejar_desenlace`, que solo sabe comparar dos fotos, y
en `sirius_engine.mirror_projection`, que solo expone de la reanudación un
booleano vigente (`reanudacion_publicada`) y ningún orden. El arreglo va a los
mismos dos sitios: la proyección expone la CRONOLOGÍA de los permisos escritos
(y el historial de estados notificados), y el reflector recorre tramo a tramo
lo que esa cronología acredita. El sitio del arreglo SÍ puede observar el
fallo: el historial de confianza de la incidencia contiene, fechados y por
escrito, tanto la parada como el permiso que la levanta — es exactamente el
dato que faltaba, no una inferencia sobre él.

**2. ¿Qué NO va a garantizar esto?**

- No garantiza que toda recuperación real se recorra. Una parada levantada sin
  ninguna palabra escrita del propietario (una revivificación de etiqueta a
  mano) queda como divergencia declarada hasta que una persona la mire. Es
  deliberado: es honesto y no inventa permisos.
- No garantiza que el historial sea exhaustivo. Solo SEIS de las trece
  etiquetas se notifican (`notify-sirius-state.yml`), y el notificador no
  serializa entre etiquetas (su grupo de concurrencia incluye el nombre de la
  etiqueta), así que el orden de publicación de los avisos no acredita el
  orden real de aplicación. El historial es un esqueleto: lo que dice ocurrió,
  pero no dice todo lo que ocurrió.
- No garantiza que un `continua` sobrante no se consuma de más. Riesgo
  aceptado y declarado por el propietario: un `continua` publicado dos veces
  por impaciencia es igualmente palabra escrita suya en ESA incidencia y solo
  puede desbloquear la SIGUIENTE parada de la misma, en orden. Pre-C2 el
  almacén no gobierna nada y una consumición de más se corrige con la verdad
  de GitHub a la vista. Se documenta como limitación; no se «arregla» con
  heurísticas.
- No arregla la deduplicación de `sirius_resume_on_command.sh`. Endurecer el
  marcador para que lleve run/intento (patrón de ADR-140) es ficha aparte del
  operador, expresamente fuera de los límites de este encargo.

**3. Criterio de parada (escrito ANTES de ver ningún resultado).**

- Si acreditar la salida de una parada exigiera mirar la FOTO vigente, la
  posición de un aviso de estado, o cualquier heurística que no sea un permiso
  escrito del propietario POSTERIOR a esa parada: parar. Es la familia de
  defecto que tumbó las tres rondas de #539 y la razón de que el criterio se
  fije de antemano.
- Si el arreglo exigiera tocar `.github/**`, cualquier workflow, o
  `sirius_resume_on_command.sh`: parar. Está fuera de los límites.
- Si la máquina de estados del dominio necesitara una arista nueva o perder
  una guarda: parar. El recorrido solo puede encadenar saltos YA legales.
- Si el caso vivo (#537) y el contraejemplo 1 volvieran a ser contradictorios
  sobre el mismo historial: parar y escalar, como hizo la primera ronda.

**4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Dos cosas, y las
dos se hacen:

- La acreditación de salir de una parada se calcula en UNA sola función que
  recibe la cronología de permisos y la posición de la parada, y **no recibe
  la foto**: no es que no la mire, es que no la tiene. La familia de defecto
  de #539 —colarse la foto por una puerta de atrás— deja de ser expresable.
- El consumo es un puntero que solo avanza. Un permiso no puede acreditar dos
  salidas porque, una vez consumido, ya no está en la lista para nadie.

Lo que NO se hace imposible: que el historial sea incompleto. No depende de
este módulo — depende de qué publiquen los workflows, y esos no se tocan.

## Opciones consideradas

1. Mantener el criterio literal del encargo (solo marcador de reanudación) y
   declarar el caso vivo como divergencia hasta que una persona lo mire.
2. Ampliar lo que acredita una salida de parada a las dos formas del permiso
   escrito del propietario presentes en el historial de confianza —el marcador
   de reanudación y la orden exacta `continua`—, consumidas en orden.
3. Arreglar la deduplicación de `sirius_resume_on_command.sh` para que el
   marcador nunca se repita, y quedarse con el criterio literal.

## Decisión

**Opción 2**, en la variante acotada que el propietario registró en #545.

**Criterio, y es el único:** la salida de una parada (`failed_safely` o
`needs_decision`) dentro del recorrido la acredita únicamente un PERMISO
ESCRITO DEL PROPIETARIO del historial de confianza posterior a esa parada,
consumido en orden: la k-ésima salida de parada del recorrido consume el
primer permiso aún no consumido que sea posterior a esa parada en el orden del
historial. Ni la foto vigente, ni la posición de un aviso de estado, ni
ninguna otra heurística acreditan una salida de parada.

**Las dos formas del permiso**, con el mismo peso y en la misma cronología:

1. un **marcador de reanudación** de los tres que
   `sirius_resume_on_command.sh` publica ANTES de reponer la etiqueta
   (`sirius-resume-stop`, `sirius-convergence-reset`, `sirius-restart-sin-pr`),
   de un autor de confianza — el recibo de la máquina;
2. la **orden exacta `continua` publicada por el propietario**, con la MISMA
   semántica de aceptación que usa ese guion (la palabra sola, tolerando
   únicamente el bloque de atribución tras `---`; cualquier otro texto no es la
   orden) — el permiso mismo.

El recibo puede faltar estructuralmente; el permiso, no. Por eso el marcador
no basta como única forma. La orden exige `author_association == "OWNER"`, no
el filtro de confianza general: `continua` es palabra del propietario, no del
bot.

**Lo demás del recorrido** se conserva del material de la PR #540: la
proyección expone el historial de estados notificados
(`sirius-notification`, las seis etiquetas de `notify-sirius-state.yml`); el
recorrido ancla en la ÚLTIMA coincidencia con el estado guardado; cada tramo
se calcula con el MISMO cálculo por foto de siempre y avanza llamando a los
métodos REALES del dominio, así que ninguna arista es nueva; y es TODO O NADA
—si un tramo diverge o resulta ilegal, no se aplica ninguno—. Lo que
desaparece es toda comparación con la foto dentro de la acreditación: la
exigencia de «acreditación intermedia distinta de la foto» de la PR #540 se
retira entera, porque el criterio de salida de parada es estrictamente más
fuerte que ella y no depende de qué etiqueta esté puesta en el instante de la
pasada.

## Comprobación que la sostiene

- El historial real de la #537, barrido completo con
  `gh api repos/.../issues/537/comments --paginate`: un solo marcador de
  reanudación, `sirius-resume-stop:1c934781…` a las 04:46:18Z, ANTERIOR a la
  parada `sirius-notification:sirius:failed-safely` de las 05:17:10Z; la orden
  `continua` del propietario a las 05:29:04Z, POSTERIOR a ella. Es la medición
  de la primera ronda de #545, reproducida aquí.
- Prueba del caso vivo sobre un doble del espejo que reproduce ese historial
  literal (`test_recorrido_acreditado_avanza_el_caso_vivo_de_la_537`), vista
  FALLAR contra el reflector de `main` antes del cambio y pasar después.
- Los dos contraejemplos del encargo, cada uno con su prueba: sin permiso
  posterior a la parada no se toca nada; dos paradas y un solo permiso
  posterior a la primera acreditan la primera salida y no la segunda.
- La proyección se prueba contra los textos literales de los marcadores y de
  la orden, incluida la forma con el bloque de atribución tras `---` que el
  propietario publica de verdad.
- **La pasada real, sobre el diario real y el GitHub real.** Con el diario de
  `origin/estado-del-motor` copiado a `/tmp` y el lector `gh` de producción:

      # con el reflector de main
      WI-20260905-034826: el motor está en estado=failed_safely fase=reparar y la
      incidencia proyecta estado=delivered fase=entregar; no hay camino hacia
      delante, no se toca nada

      # con este cambio (--ensayo, y después aplicado sobre la copia)
      WI-20260905-034826: aplicados 5 paso(s): work_item_reactivated,
      work_item_repair_resumed, work_item_review_started,
      work_item_review_approved, work_item_delivered
      Pasos aplicados en total: 5.

      # segunda pasada
      Pasos aplicados en total: 0.

      # agregado resultante
      delivered entregar {'merge_sha': '78e81fc7...', 'numero_incidencia': 537}

  Solo se escribió sobre la copia en `/tmp`: la rama `estado-del-motor` no se
  toca desde aquí, eso lo hace el workflow del motor.
- **Pruebas por mutación, las nueve vistas caer** (ADR-001, regla 3). En el
  reflector: quitar el recorrido (= el reflector de `main`) tumba las seis
  pruebas del caso vivo y sus gemelas, incluida la de punta a punta del CLI;
  no gastar el permiso al consumirlo tumba
  `test_un_permiso_no_puede_acreditar_dos_salidas_de_parada`; aceptar un
  permiso anterior a la parada tumba `test_un_permiso_anterior_a_la_parada...`;
  acreditar toda salida de parada tumba las cinco pruebas de contraejemplo;
  anclar en la primera coincidencia tumba la prueba del ancla. En la
  proyección: aceptar la orden del bot, usar `str.lower()`, aceptar la palabra
  contenida en un texto mayor y quitar el filtro de confianza tumban cada una
  su prueba.
- Validaciones obligatorias completas con una sola invocación de
  `scripts/check.ps1` (ADR-145): `4983 passed, 16 skipped, 2 xfailed`, código de
  salida 0.
- **Corrección de la ronda 1 (#545), disparada por `CI_FAILURE` sobre el head
  `c618f10`.** Quality (run 33994967331) paró en `Ruff lint` con dos defectos,
  ambos en pruebas nuevas de este cambio y ninguno en el código del reflector ni
  de la proyección: `I001` en `tests/engine/test_mirror_projection.py` —
  `FormaDePermiso` llegaba en un segundo `from sirius_engine.domain.mirror`
  colocado tras el import de `work_item`— y `SIM201` en
  `tests/engine/test_reflect_cli.py:490` — `not (entrada[:2] == (5, 29))`—. Se
  fusiona el import duplicado en uno solo ordenado y se escribe la comparación
  como `entrada[:2] != (5, 29)`; ninguna de las dos toca lo que las pruebas
  afirman. Las dos líneas siguen fijadas por una prueba, vistas caer:
  quitar `FormaDePermiso` del import tumba
  `test_los_permisos_de_reanudacion_llevan_las_dos_formas_en_orden` y
  `test_el_booleano_vigente_de_reanudacion_no_cambia_con_los_permisos`
  (`NameError: name 'FormaDePermiso' is not defined`); cambiar la tupla a
  `(9, 99)` tumba
  `test_sin_la_orden_del_propietario_la_misma_pasada_declara_y_no_toca_nada`
  (`AssertionError: assert 25 == (25 - 1)`), que es la guarda de que ese filtro
  quita exactamente el `continua` de las 05:29.

## Consecuencias

- El caso vivo avanza: WI-20260905-034826 llega a `delivered/entregar` y la
  pasada siguiente no añade nada.
- Las recuperaciones sin ninguna palabra escrita del propietario quedan como
  divergencia declarada. Es la consecuencia aceptada y deliberada del encargo.
- Un `NEEDS_DECISION` jamás se resuelve en el almacén sin su permiso.
- El almacén gana memoria de tramos intermedios que ninguna pasada observó:
  el diario registra las transiciones reales, no un salto.
- Queda pendiente, como ficha del operador, endurecer
  `sirius_resume_on_command.sh` para que su marcador lleve run/intento y nunca
  se deduplique. Mientras no se haga, la orden `continua` es la única forma de
  permiso disponible para la segunda reanudación sobre un mismo head.

## Alternativas descartadas y por qué

- **Opción 1** (criterio literal, caso vivo sin resolver): deja el encargo sin
  su caso vivo y, peor, deja sin cubrir toda una familia estructural de casos
  —dos reanudaciones sobre el mismo head— para la que el recibo nunca existirá.
- **Opción 3** (arreglar la deduplicación): correcta y necesaria, pero toca
  `scripts/automation/sirius_resume_on_command.sh`, expresamente fuera de los
  límites de este encargo, y además solo arreglaría el futuro: los historiales
  ya escritos —incluido el del caso vivo— seguirían sin recibo.
- **Acreditar por la foto vigente o por la posición de un aviso** (las tres
  rondas de #539): es la familia de defecto que el freno de convergencia paró.
  El mismo historial recorría o no según qué etiqueta estuviera puesta en el
  instante de la pasada.
