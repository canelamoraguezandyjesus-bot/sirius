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
(`sirius-notification`, las seis etiquetas de `notify-sirius-state.yml`); cada
tramo se calcula con el MISMO cálculo por foto de siempre y avanza llamando a
los métodos REALES del dominio, así que ninguna arista es nueva; y es TODO O
NADA —o el recorrido llega hasta la foto, o no se aplica ninguno—. Lo que
desaparece es toda comparación con la foto dentro de la acreditación: la
exigencia de «acreditación intermedia distinta de la foto» de la PR #540 se
retira entera, porque el criterio de salida de parada es estrictamente más
fuerte que ella y no depende de qué etiqueta esté puesta en el instante de la
pasada.

**El orden de publicación de los avisos no es el orden de aplicación** (ronda
2 de la PR #546, CODEX-001). Es lo que esta misma nota de arranque ya decía en
su pregunta 2 —el notificador no serializa entre etiquetas, su grupo de
concurrencia lleva el nombre de la etiqueta—, pero el recorrido exigía que
TODOS los marcadores posteriores al ancla formaran una secuencia legal en ese
orden, así que un solo aviso retrasado lo tumbaba entero y para siempre. Lo que
se reconstruye es una SUBSECUENCIA legal hasta la foto: un aviso que no encaja
donde está publicado no mueve el recorrido y tampoco lo tumba. Con dos
excepciones que no se saltan nunca, porque saltarlas sí cambiaría lo que el
recorrido afirma: un aviso de PARADA —saltárselo sería pasar por encima de una
parada real sin exigir su permiso— y el tramo final contra la foto. Y una
salida de parada sin permiso sigue abandonando el recorrido entero: eso no es
un aviso a destiempo, es el criterio.

La primera de esas dos excepciones se entrega **incompleta a sabiendas**: un
aviso de PARADA publicado tarde —después del permiso que la levantó— sigue
tumbando el recorrido, porque la parada y su permiso se correlacionan por
posición y no por identidad. Es CLAUDE-R4-001, y está en «Consecuencias» con
su vía de raíz. Su hermano CLAUDE-R4-002 —el diagnóstico atribuido por
posición— sí quedó corregido en la ronda 4, también en «Consecuencias».

**Cada ocurrencia del historial se lleva su propia evidencia** (misma ronda,
CODEX-002 y CODEX-003). La posición ordena, pero no identifica: el mismo
`(estado, fase)` aparece varias veces en un ciclo con dos vueltas de
reparación. Así que cada `EstadoAcreditado` lleva ahora el INSTANTE del
comentario que lo publicó y, si acredita una parada, el DIAGNÓSTICO que el
historial le atribuye —el último publicado hasta su posición, que es donde
`sirius_apply_verdict.sh` lo escribe: el comentario del veredicto va antes de
aplicar la etiqueta, y la etiqueta es lo que dispara el marcador—. Con eso:

- el recorrido **ancla en la ocurrencia que el almacén pudo guardar**, no en la
  última por costumbre: se descartan las publicadas DESPUÉS de la última
  escritura del almacén (`updated_at`); si el diagnóstico guardado señala
  exactamente una de las que quedan, esa; y solo si ninguna de las dos
  discrimina, la más reciente de las que la evidencia no descartó. Anclar
  siempre en la última hacía que un motor detenido en la PRIMERA parada se
  saltara entero el tramo intermedio —la primera recuperación y la segunda
  parada—, que es justo el salto que este ADR viene a evitar;
- cada parada que el recorrido recrea **conserva SU diagnóstico**, y si no hay
  ninguno atribuible hasta ella no se recrea ninguno. El de la FOTO vigente no
  cambia: lo sigue poniendo el espejo real, contra el que va el tramo final.

## Comprobación que la sostiene

- El historial real de la #537, barrido completo con
  `gh api repos/.../issues/537/comments --paginate`: un solo marcador de
  reanudación, `sirius-resume-stop:1c934781…` a las 04:46:18Z, ANTERIOR a la
  parada `sirius-notification:sirius:failed-safely` de las 05:17:10Z; la orden
  `continua` del propietario a las 05:29:04Z, POSTERIOR a ella. Es la medición
  de la primera ronda de #545, reproducida aquí.
- Prueba del caso vivo sobre un doble del espejo que reproduce ese historial
  literal (`test_recorrido_acreditado_avanza_el_caso_vivo_de_la_537`), vista
  FALLAR contra el reflector de `main` antes del cambio y pasar después. Sigue
  en verde tras la corrección de la ronda 2, con el mismo plan de cinco pasos.
- **Un ancla que el diagnóstico guardado contradice se rechaza** (CODEX-002,
  ronda 3). `notify-sirius-state.yml` deduplica su marcador por estado y head,
  así que una segunda parada `failed-safely` sobre el mismo head puede no dejar
  marcador propio. `_ancla_del_recorrido` descarta ahora las ocurrencias cuyo
  diagnóstico difiere del que el almacén guarda -una ocurrencia SIN diagnóstico
  no contradice nada y se conserva, que es lo que mantiene vivo el respaldo
  cuando no hay diagnóstico discriminante-, y si el descarte se las lleva todas
  no hay recorrido. Prueba:
  `test_un_marcador_con_otro_diagnostico_no_ancla_la_parada_guardada`, vista
  fallar con la mutación que quita el filtro (`... in (None,
  work_item.diagnostico)` → `True`): devuelve cinco pasos empezando por
  `work_item_reactivated` en vez de `()`.
- Los dos contraejemplos del encargo, cada uno con su prueba: sin permiso
  posterior a la parada no se toca nada; dos paradas y un solo permiso
  posterior a la primera acreditan la primera salida y no la segunda.
- La proyección se prueba contra los textos literales de los marcadores y de
  la orden, incluida la forma con el bloque de atribución tras `---` que el
  propietario publica de verdad.
- **La paridad con la guarda 1 del guion es línea a línea, no `strip()`**
  (CLAUDE-A1-001, ronda 3). El `sed` del guion recorta cada línea por separado
  y por eso no borra una línea en blanco delante de la palabra; `str.strip()`
  sí, y aceptaba como orden un `"\ncontinua"` que el guion rechaza. Prueba:
  `test_una_linea_en_blanco_delante_de_la_palabra_no_es_la_orden`, vista fallar
  con la mutación que vuelve a `sin_firma.strip()` (proyecta dos permisos de
  forma ORDEN en vez de `()`). Contrastado además ejecutando en el runner el
  `sed`/`tr` literales del guion sobre los cinco cuerpos de la prueba: los
  cinco veredictos coinciden con los de `_es_orden_de_continuar`.
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
- **Corrección de la ronda 2 (#545), disparada por la revisión** (CODEX-001
  P1, CODEX-002 y CODEX-003 P2 sobre el head `f877ec7`). Las tres son la misma
  familia: el recorrido daba valor de evidencia a la POSICIÓN de un marcador
  —como orden de aplicación, como identidad de la ocurrencia y como
  atribución del diagnóstico— cuando la posición solo ordena. La corrección
  está descrita en la sección «Decisión»; su comprobación, aquí:

  - `_interpretar_historial_estados` le pone a cada `EstadoAcreditado` el
    `creado_en` de su comentario (`None` si el marcador viene del cuerpo, que
    no tiene instante propio) y, a las paradas, el diagnóstico atribuible hasta
    su posición. `_interpretar_diagnostico_fallo` —el de la foto vigente— pasa
    a ser el último elemento de esa misma cronología, no un segundo recorrido:
    la foto y las paradas históricas no pueden discrepar sobre qué es un
    diagnóstico.
  - Pruebas: **8 nuevas** en `tests/engine/test_reflect.py` y **3** en
    `tests/engine/test_mirror_projection.py`. Dos pruebas se REESCRIBEN porque
    fijaban lo corregido: `test_el_recorrido_ancla_en_la_ULTIMA_coincidencia…`
    (su enunciado —«anclar en la primera abandonaría el recorrido entero»— deja
    de ser cierto en cuanto un aviso a destiempo no tumba el recorrido) da paso
    a las tres pruebas del ancla correlacionada, y
    `test_un_tramo_ilegal_abandona_el_recorrido_entero` (su tramo ilegal era un
    `sirius:implementing` publicado tarde, es decir, el caso que CODEX-001 pide
    tolerar) da paso a las dos que fijan las excepciones que NO se saltan: el
    aviso de parada y el tramo final contra la foto.

  **Las siete mutaciones de esta ronda, vistas caer** (ADR-001, regla 3), con
  la primera línea del fallo de `pytest`:

  1. `if acreditado is None or espejo_del_tramo.estado in _PARADAS:` →
     `if True:` (el aviso a destiempo vuelve a tumbar el recorrido) tumba
     `test_un_aviso_publicado_fuera_de_orden_no_envenena_el_recorrido`:
     `AssertionError: assert 'WI-20260902-174417: … no hay camino hacia
     delante, no se toca nada' is None` —literalmente el defecto que CODEX-001
     describe—.
  2. La misma línea → `if acreditado is None:` (se permite saltarse también un
     aviso de parada) tumba
     `test_un_aviso_de_PARADA_que_no_encaja_abandona_el_recorrido_entero`:
     `AssertionError: assert (PasoReflejo(…)) == ()`.
  3. `return anteriores[-1] if anteriores else candidatos[0]` →
     `return candidatos[-1]` (el ancla vuelve a ser «la última coincidencia»)
     tumba `test_el_recorrido_ancla_en_la_ocurrencia_que_el_almacen_pudo_guardar`:
     `AssertionError: At index 1 diff: 'work_item_repair_resumed' !=
     'work_item_failed_safely'` —el salto que se come la segunda parada—.
  4. `if len(por_identidad) == 1:` → `if False:` (se quita la correlación por
     identidad del diagnóstico) tumba
     `test_el_diagnostico_guardado_identifica_la_parada_cuando_el_tiempo_no_discrimina`,
     con el mismo primer diff.
  5. Quitar `diagnostico_fallo=acreditado.diagnostico` del espejo de cada tramo
     (el tramo histórico vuelve a heredar el diagnóstico de la foto) tumba
     `test_cada_parada_del_recorrido_conserva_SU_diagnostico`:
     `AssertionError: cada parada se escribe con su propia evidencia, no con la
     de la última`.
  6. `if posicion > orden: break` → `if False: break` en `_diagnostico_hasta`
     (la proyección atribuye a toda parada el último diagnóstico) tumba
     `test_cada_parada_acreditada_lleva_el_diagnostico_publicado_hasta_ella`:
     `AssertionError: At index 0 diff: ('sirius:failed-safely', 'la ronda 2
     agotó el tiempo del job') != ('sirius:failed-safely', 'la ronda 1 se quedó
     sin turnos')`.
  7. `publicado_en=instantes.get(orden)` → `publicado_en=None` tumba
     `test_cada_estado_acreditado_lleva_el_instante_de_su_comentario`:
     `AssertionError: At index 1 diff: ('sirius:failed-safely', None) !=
     ('sirius:failed-safely', datetime.datetime(2026, 9, 5, 3, 0, …))`.

- **Ronda siguiente (#545): los tres hallazgos vuelven por goteo, y con ellos
  aparece un error de tipos que la corrección anterior dejó.** El revisor
  volvió a entregar CODEX-001, CODEX-002 y CODEX-003 sobre el head `f877ec7`
  —el ANTERIOR a su corrección—, así que lo primero fue comprobar si seguían
  vivos sobre el head vigente. No lo estaban; y no se da por bueno porque lo
  diga un commit: cada uno se volvió a ver caer con su mutación sobre el árbol
  de esta ronda, con la primera línea del fallo de `pytest`:

  1. CODEX-001 — `if acreditado is None or espejo_del_tramo.estado in _PARADAS:`
     → `if True:` tumba
     `test_un_aviso_publicado_fuera_de_orden_no_envenena_el_recorrido`:
     `AssertionError: assert 'WI-20260902-174417: el motor está en
     estado=failed_safely fase=reparar y la incidencia proyecta
     estado=delivered fase=entregar; no hay camino hacia delante, no se toca
     nada' is None`.
  2. CODEX-002 — `return anteriores[-1] if anteriores else candidatos[0]` →
     `return candidatos[-1]` tumba
     `test_el_recorrido_ancla_en_la_ocurrencia_que_el_almacen_pudo_guardar`:
     `AssertionError: At index 1 diff: 'work_item_repair_resumed' !=
     'work_item_failed_safely'`.
  3. CODEX-003 — quitar `diagnostico_fallo=acreditado.diagnostico` del espejo
     de cada tramo tumba `test_cada_parada_del_recorrido_conserva_SU_diagnostico`:
     `AssertionError: cada parada se escribe con su propia evidencia, no con la
     de la última`.
  4. En la proyección, `if posicion > orden: break` → `if False: break` tumba
     `test_cada_parada_acreditada_lleva_el_diagnostico_publicado_hasta_ella`:
     `AssertionError: At index 0 diff: ('sirius:failed-safely', 'la ronda 2
     agotó el tiempo del job') != ('sirius:failed-safely', 'la ronda 1 se quedó
     sin turnos')`.
  5. En la proyección, `publicado_en=instantes.get(orden)` →
     `publicado_en=None` tumba
     `test_cada_estado_acreditado_lleva_el_instante_de_su_comentario`:
     `AssertionError: At index 1 diff: ('sirius:failed-safely', None) !=
     ('sirius:failed-safely', datetime.datetime(2026, 9, 5, 3, 0, …))`.

  Lo que sí seguía vivo era un **error de tipos que introdujo esa misma
  corrección** y que la validación obligatoria no delata. Sobre el head
  `923202f`, `uv run mypy src tests` termina en 1 con
  `src/sirius_engine/reflect.py:484: error: Unsupported operand types for >=
  ("datetime" and "None")`: en la comprensión del ancla, `mypy` no estrecha
  `historial[indice].publicado_en` a través del `or` —un subíndice no es un
  nombre—, así que la comparación queda `datetime | None` contra `datetime`. Y
  aun así `pwsh -File scripts/check.ps1` terminaba en **0**: en aquel árbol
  —el head `923202f`, anterior a la actualización de esta rama con `main`—
  `scripts/check.ps1` encadenaba los cuatro comandos sin comprobar el código de
  salida de cada uno y PowerShell no propaga el de un ejecutable nativo, de
  modo que el código de salida del script era el de `pytest` y solo el de
  `pytest`. **Eso dejó de ser cierto dentro de esta misma ronda**: ADR-153,
  fusionado en `main` el 06-09-2026 y entrado en esta rama con la
  actualización, añadió `if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }` tras
  cada uno de los tres primeros comandos, así que en el árbol que se fusiona el
  guion se detiene en el primer rojo. En Quality no hay
  ese amortiguador: `.github/workflows/quality.yml:111` ejecuta `uv run mypy
  src tests` como paso propio, así que ese error es un rojo determinista.

  El arreglo estrecha el instante en una función con nombre,
  `_el_almacen_pudo_guardarla`, sin tocar el criterio: la ocurrencia sin
  instante sigue sin descartarse y la publicada después de `updated_at` sigue
  descartada. **Mutación vista caer:** `return publicado_en is None or
  publicado_en <= work_item.updated_at` → `return True` tumba
  `test_el_recorrido_ancla_en_la_ocurrencia_que_el_almacen_pudo_guardar`:
  `AssertionError: At index 1 diff: 'work_item_repair_resumed' !=
  'work_item_failed_safely'`. Tras el arreglo, `uv run mypy src tests` termina
  en 0 (`Success: no issues found in 570 source files`).

  Que `scripts/check.ps1` no propagara el código de salida de sus tres primeros
  comandos quedó **señalado y sin tocar** en su momento: era la validación
  obligatoria de ADR-145 y cambiarla era una decisión de ese ADR, no una de las
  observaciones de esta ronda. **Lo cerró ADR-153**, no este trabajo. Mientras
  siguió así —hasta la actualización de esta rama con `main`—, «código de salida
  0 del script» acreditaba `pytest` y nada más, y por eso las líneas de abajo
  transcriben además la salida de los otros tres comandos; sobre el árbol
  vigente el código de salida del guion ya acredita los cuatro.

- El commit `923202f`, anterior a esta ronda, pasó `ruff format` sobre las dos
  pruebas que la corrección de la ronda 2 empujó sin formatear; no cambia
  ninguna afirmación de este ADR.

- **Ronda 4, CLAUDE-R4-002** (el diagnóstico por identidad y no por posición).
  La prueba que lo fija es
  `test_un_aviso_de_parada_retrasado_no_le_roba_el_diagnostico_a_la_otra`
  (`tests/engine/test_mirror_projection.py`): proyecta los comentarios reales
  en el orden `[veredicto «fallo 1», veredicto «fallo 2», notification
  failed-safely head 1c934781, notification failed-safely head 786c82dc]` y
  exige `['fallo 1', 'fallo 2']`. **Mutación vista caer:** sustituir el cuerpo
  de `_atribuir_diagnosticos` por la atribución posicional anterior —«el último
  diagnóstico publicado hasta `acreditado.orden`»— la tumba con
  `AssertionError: el aviso retrasado de la primera parada no hereda el
  diagnóstico de la segunda` / `assert ['fallo 2', 'fallo 2'] == ['fallo 1',
  'fallo 2']`. Las dos pruebas hermanas siguen en verde sin tocarlas:
  `test_cada_parada_acreditada_lleva_el_diagnostico_publicado_hasta_ella` y
  `test_una_parada_sin_diagnostico_publicado_hasta_ella_no_hereda_el_siguiente`.

- **Ronda 4, CLAUDE-R4-003 y CLAUDE-R4-004** (texto). Lo que las sostiene no es
  una prueba sino el propio guion: `grep -c 'if ($LASTEXITCODE -ne 0) { exit
  $LASTEXITCODE }' scripts/check.ps1` devuelve **3** sobre el árbol de esta
  rama, que es lo que hace falsa en presente la afirmación que este ADR y el
  docstring de `_el_almacen_pudo_guardarla` hacían, y cierta solo en pasado
  sobre el head `923202f`.
- Validaciones obligatorias completas con una sola invocación de
  `scripts/check.ps1` (ADR-145): `4992 passed, 16 skipped, 2 xfailed` en
  439.75 s, código de salida 0, sobre el árbol final de esta
  ronda; y dentro de esa misma invocación, `ruff format --check` («602 files
  already formatted»), `ruff check` («All checks passed!») y `mypy src tests`
  («Success: no issues found in 570 source files»), leídos en su salida y no
  en el código de salida del script. La cifra de pruebas no se mueve respecto
  de la ronda anterior —el arreglo de tipos no añade ni quita ninguna—; la
  anterior a la ronda 2, `4983 passed`, era la del head `f877ec7` y subió en 9
  por las 11 pruebas nuevas menos las 2 reescritas. Lo único que cambia en el
  árbol después de esta captura es la transcripción de estas mismas cifras y el
  cuerpo de la PR.
- **Ronda 4.** Validaciones obligatorias completas con una sola invocación de
  `pwsh -File scripts/check.ps1` (ADR-145) **sobre el árbol de `91dac47`**:
  `5071 passed, 17 skipped, 2 xfailed` en 461.44 s (0:07:41), código de salida
  **0**. Sobre este árbol ese 0 acredita los cuatro comandos y no solo `pytest`:
  es exactamente lo que ADR-153 cambió y lo que CLAUDE-R4-003 obligaba a dejar
  de negar. La cifra sube en 3 respecto de la de la ronda 3 (`5068`, head
  `4d9eb70`): 1 es la prueba nueva de esta ronda
  —`test_un_aviso_de_parada_retrasado_no_le_roba_el_diagnostico_a_la_otra`— y
  las otras 2 entran con la actualización de la rama con `main` (#559). Lo
  único que cambia en el árbol después de esta captura es la transcripción de
  estas mismas cifras y el cuerpo de la PR.
- **Ronda 3.** Validaciones obligatorias completas con una sola invocación de
  `pwsh -File scripts/check.ps1` (ADR-145) **sobre el árbol de `4d9eb70`**:
  `5068 passed, 17 skipped, 2 xfailed` en 479.96 s (0:07:59), código de salida
  **0**. La cifra sube en 76 respecto de la de la ronda 2 (`4992`) porque esta
  rama se actualizó con `main` entre medias; de esas, 2 son las pruebas nuevas
  de esta ronda —`test_un_marcador_con_otro_diagnostico_no_ancla_la_parada_guardada`
  y `test_una_linea_en_blanco_delante_de_la_palabra_no_es_la_orden`—. Lo único
  que cambia en el árbol después de esta captura es la transcripción de estas
  mismas cifras.
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

- **Ronda 6, sobre el árbol de `44bcdc3`**: una sola invocación de
  `pwsh -File scripts/check.ps1` (Ruff format, Ruff lint, mypy, pytest), código
  de salida **0**, `5086 passed, 17 skipped, 2 xfailed in 480.30s (0:08:00)`.
  Las dos mutaciones de la ronda están descritas en «Consecuencias», cada una
  con la prueba que vio caer.

- **Ronda 6, segunda corrección (CLAUDE-R5-003), sobre el árbol de
  `6b4a452`**: una sola invocación de `pwsh -File scripts/check.ps1` (Ruff
  format, Ruff lint, mypy, pytest), código de salida **0**, `5089 passed, 17
  skipped, 2 xfailed in 502.49s (0:08:22)`. Las tres pruebas nuevas y la
  reescrita por la decisión del propietario, con su mutación vista caer, están
  descritas en «Consecuencias».

- **Ronda 7 (CLAUDE-R7-001, CLAUDE-R7-002 y CLAUDE-R7-003), sobre el árbol de
  `b1af8fd`**: una sola invocación de `pwsh -File scripts/check.ps1` (Ruff
  format, Ruff lint, mypy, pytest), código de salida **0**, `5091 passed, 17
  skipped, 2 xfailed in 460.95s (0:07:40)`. Las tres pruebas nuevas o ampliadas
  de la ronda, con su mutación vista caer, están descritas en «Consecuencias».

- **Ronda 8 (CLAUDE-R8-001 y CLAUDE-R8-002), sobre el árbol de `d8553d7`**:
  una sola invocación de `pwsh -File scripts/check.ps1` (Ruff format, Ruff
  lint, mypy, pytest), código de salida **0**, `5093 passed, 17 skipped, 2
  xfailed in 397.58s (0:06:37)`. La cifra sube en 2 respecto de la ronda 7
  (`5091`): son las dos pruebas nuevas de CLAUDE-R8-001
  (`test_historial_estados_lee_el_marcador_con_run_sin_pegarlo_al_head` y
  `test_historial_estados_sigue_leyendo_el_marcador_sin_run`). CLAUDE-R8-002 es
  solo texto y no añade ninguna. Mutación vista caer: con
  `_NOTIFICATION_MARKER_RE` en su forma anterior —`([^\s>]*)` para el head, sin
  el tramo opcional del run—, la primera de esas dos pruebas falla con
  `AssertionError: assert '1c934781:33951766681' == '1c934781'`. Lo único que
  cambia en el árbol después de esta captura es la transcripción de estas
  mismas cifras.

- **Ronda 9 (CLAUDE-R9-001), sobre el árbol de `28c60e3`**: una sola
  invocación de `pwsh -File scripts/check.ps1` (Ruff format, Ruff lint, mypy,
  pytest), código de salida **0**, `5094 passed, 17 skipped, 2 xfailed in
  409.48s (0:06:49)`. La cifra sube en 1 respecto de la ronda 8 (`5093`): es la
  prueba nueva
  `test_la_abstencion_tambien_alcanza_a_la_parada_posterior_con_aviso_propio`
  (`tests/engine/test_reflect.py`), que fija el comportamiento REAL de
  `_hay_una_parada_posterior_sin_aviso` sobre un historial posterior a ADR-157
  -segunda parada con aviso propio y `continua` detrás de cada parada, ancla
  `blocked-decision`: `pasos == ()` y divergencia-. La corrección de
  CLAUDE-R9-001 no cambia ni una línea de lógica: solo el docstring de esa
  función y el punto 2 de la entrada de ADR-157 en «Consecuencias». Mutación
  vista caer: con la abstención desactivada (`return any(` → `return False and
  any(` en `_hay_una_parada_posterior_sin_aviso`), la prueba nueva falla con
  `E AssertionError: assert (PasoReflejo(...co=None), ...) == ()`. Lo único
  que cambia en el árbol después de esta captura es la transcripción de estas
  mismas cifras.

- **Ronda 10 (CLAUDE-R10-001), sobre el árbol de `cbcd068`**: una sola
  invocación de `pwsh -File scripts/check.ps1` (Ruff format, Ruff lint, mypy,
  pytest), código de salida **0**, `5096 passed, 17 skipped, 2 xfailed in
  460.37s (0:07:40)`. La cifra sube en 2 respecto de la ronda 9 (`5094`): son
  las dos pruebas nuevas de `tests/engine/test_reflect.py`,
  `test_una_parada_que_ningun_tramo_recrea_abandona_el_recorrido` y
  `test_una_parada_con_su_tramo_en_el_recorrido_se_sigue_recorriendo_entera`.
  Mutación vista caer: con la abstención nueva desactivada
  (`if paradas_por_recrear:` → `if False and paradas_por_recrear:` al cerrar el
  bucle de tramos de `_recorrer_historial_acreditado`), la primera de esas dos
  falla con `E AssertionError: assert (PasoReflejo(...ostico=None),) == ()` y
  ninguna otra prueba del árbol se mueve (`1 failed, 1281 passed, 1 skipped`
  sobre `tests/engine`). Lo único que cambia en el árbol después de esta
  captura es la transcripción de estas mismas cifras.

- **Ronda 11 (CLAUDE-R11-001 y CLAUDE-R11-002), sobre el árbol de `0ee3d5a`**:
  una sola invocación de `pwsh -File scripts/check.ps1` (Ruff format, Ruff
  lint, mypy, pytest), código de salida **0**,
  `5097 passed, 17 skipped, 2 xfailed in 466.54s (0:07:46)`. La cifra sube en 1
  respecto de la ronda 10 (`5096`): es la prueba nueva
  `test_una_parada_fechada_que_ningun_tramo_recrea_abandona_el_recorrido`
  (`tests/engine/test_reflect.py`), la gemela FECHADA de la roja de la ronda
  10. Mutaciones vistas caer, sobre el árbol anterior a la corrección
  (`266a46c`):

  1. CLAUDE-R11-001, con el filtro de la ronda 10 en su sitio
     (`and (parada.publicado_en is None or parada.publicado_en <=
     work_item.updated_at)` en `_paradas_que_el_recorrido_debe_recrear`), la
     prueba nueva falla con
     `E AssertionError: assert (PasoReflejo(...ostico=None),) == ()` -el
     recorrido reactiva con el único `continua`, el de la primera parada-.
     La corrección, que es quitar ese filtro, no mueve ninguna otra prueba:
     `62 passed` en `tests/engine/test_reflect.py` y `1283 passed, 1 skipped`
     en `tests/engine`.
  2. CLAUDE-R11-002, devolviendo la llamada del doble a su forma anterior
     (`_paradas(*entradas, desde=_AHORA)` → `_paradas(*entradas)` en
     `test_el_doble_de_cronologia_proyecta_lo_mismo_que_la_proyeccion_real`),
     la comparación nueva de instantes falla con
     `E assert (None, None, None, None) == (datetime.dat...timezone.utc))`.

  Lo único que cambia en el árbol después de esta captura es la transcripción
  de estas mismas cifras.

- **Ronda 12 (CLAUDE-R12-001 y CLAUDE-R12-002), sobre el árbol de `8248592`**:
  una sola invocación de `pwsh -File scripts/check.ps1` (Ruff format, Ruff
  lint, mypy, pytest), código de salida **0**,
  `5098 passed, 17 skipped, 2 xfailed in 462.36s (0:07:42)`. La cifra sube en 1
  respecto de la ronda 11 (`5097`): es la prueba nueva
  `test_una_parada_posterior_a_la_ultima_escritura_no_abstiene_el_ancla`
  (`tests/engine/test_reflect.py`), la gemela de
  `test_la_abstencion_tambien_alcanza_a_la_parada_posterior_con_aviso_propio`
  en el tramo que el recorrido reproduce. Mutaciones vistas caer:

  1. CLAUDE-R12-001, sobre el árbol anterior a la corrección (`ddbc958`),
     fechando la entrada de la prueba de la ronda 9 con instantes del tramo
     recorrido (`_paradas(*entradas)` →
     `_paradas(*entradas, desde=datetime(2026, 9, 5, 5, 0, tzinfo=UTC))`):
     `E AssertionError: assert resultado.pasos == ()`, contra un plan de ocho
     pasos que termina en `work_item_delivered`. Es la demostración de que el
     texto del ADR y del docstring afirmaban una limitación que producción no
     tiene sobre ese tramo.
  2. La prueba nueva, mutando el predicado de producción -quitando
     `and (parada.publicado_en is None or parada.publicado_en <=
     work_item.updated_at)` de `_hay_una_parada_posterior_sin_aviso`-, falla
     con `E AssertionError: assert 'WI-20260902-174417: el motor está en
     estado=needs_decision ... no se toca nada' is None`. La corrección deja
     ese filtro intacto: esta ronda no toca ni una línea de lógica.

  Lo único que cambia en el árbol después de esta captura es la transcripción
  de estas mismas cifras.

- **Ronda 13 (CODEX-001): fuera del alcance de esta PR por decisión del
  propietario (07-09-2026, 21:15 UTC), atendida en #563.** La revisión levantó
  como P1 que `.github/workflows/notify-sirius-state.yml:76` deduplica por
  `incidencia-estado-head-run` mientras el §7 de
  `docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` sigue describiendo la
  clave `incidencia-estado-head`. La contradicción es real, pero **no nace de
  este trabajo**: ese fichero llegó a la rama con el merge de `main` y su
  autoría es `07a51b1` (ADR-157, PR #562, ya fusionada). Comprobado sobre el
  árbol de `287d4b5`: `git diff --quiet main HEAD -- .github/` sale en **0**,
  es decir, #546 no cambia ni una línea de `.github/**`. El marcador con el run
  es la decisión deliberada de ADR-157, con su coste aceptado por escrito allí;
  lo que faltaba era el otro lado del contrato, y eso se corrige en su propia
  ficha (#563, solo documentación, que además pasa ADR-157 a ACEPTADO).

  Lo que sí toca a este encargo ya estaba hecho y sigue verde: la proyección
  lee el marcador con y sin sufijo de run
  (`mirror_projection.py`, `r"<!--\s*sirius-notification:(sirius:[a-z-]+):([^\s>:]*)(?::[^\s>]*)?\s*-->"`),
  de modo que el cambio de clave de ADR-157 no rompe la acreditación por
  marcadores. Esta ronda, por tanto, **no cambia código ni pruebas**: registra
  la decisión y su comprobación.

- **Comprobación de la ronda 13, sobre el árbol de `1f77b6a`**: una sola
  invocación de `pwsh -File scripts/check.ps1` (Ruff format, Ruff lint, mypy,
  pytest), código de salida **0**,
  `5102 passed, 17 skipped, 2 xfailed in 446.40s (0:07:26)`. La cifra sube en 4
  respecto de la ronda 12 (`5098`) y ninguna de las cuatro es de este trabajo:
  entran con el merge de `main` (`287d4b5`), que trae ADR-157 y sus pruebas del
  marcador por parada (`07a51b1`, PR #562). Esta ronda no cambia código ni
  pruebas -es documental-, así que no hay mutación que enseñar: lo que verifica
  el texto corregido es `git diff --quiet main HEAD -- .github/`, que sale en
  **0** y demuestra que #546 no toca el fichero que CODEX-001 señala.

  Lo único que cambia en el árbol después de esta captura es la transcripción
  de estas mismas cifras.

- **Ronda 14 (CODEX-001): el defecto del canal es real, su corrección está
  fuera del alcance de esta PR, y lo que sí toca a este trabajo es dejar de
  prometerlo.** La revisión levantó como P1 que el §7 del contrato
  (`docs/implementation/AUTOMATION_OPERATING_CONTRACT.md:363`) promete un aviso
  «por EVENTO de etiqueta» que la cola puede descartar: el grupo de
  concurrencia de `.github/workflows/notify-sirius-state.yml:11-13` es
  `notify-sirius-<incidencia>-<etiqueta>` y GitHub Actions conserva como mucho
  UNA ejecución en espera por grupo, así que un tercer evento de la misma
  etiqueta desplaza al segundo antes de que publique su marcador. El
  diagnóstico es correcto. Su corrección, tal como el propio hallazgo la
  acota -«impedir que eventos distintos compartan una ranura pendiente
  descartable»-, es un cambio del grupo de concurrencia: vive entero en
  `.github/**`, que la decisión del propietario del 07-09-2026 (21:15 UTC)
  deja fuera de #546 **sin excepción**, y el otro fichero señalado es el
  contrato, cuya §7 el propietario asignó a su propia ficha (#563). Comprobado
  sobre el árbol de esta ronda: `git diff --quiet main HEAD -- .github/` sale
  en **0** y `git diff --quiet main HEAD --
  docs/implementation/AUTOMATION_OPERATING_CONTRACT.md` también, es decir,
  ninguno de los dos ficheros que el hallazgo señala lleva una línea de #546;
  su autoría es `07a51b1` y `f2085db` (ADR-157, PR #562 y #563, ya
  fusionadas).

  Lo que sí nace de este trabajo, y por eso se corrige aquí, es que cinco
  pasajes de #546 daban por incondicional lo que el canal no garantiza
  («desde ADR-157 cada evento de etiqueta deja su propio aviso», y sus
  variantes en `mirror_projection.py`, `reflect.py` y `domain/mirror.py`).
  Quedan acotados al caso en que el evento llega a ejecutarse, con la nota que
  explica el límite junto a `_NOTIFICATION_MARKER_RE`, y con la consecuencia
  que importa al motor: los respaldos que este código mantiene para los
  historiales anteriores a ADR-157 son también la red del hueco que la cola
  puede dejar en un historial posterior. La abstención por «más diagnósticos
  que marcadores» de `_atribuir_diagnosticos` y el abandono del recorrido de
  `_hay_una_parada_posterior_sin_aviso` ya cubren ese hueco sin cambio de
  lógica: por eso esta ronda **no cambia ni una línea de comportamiento ni
  ninguna prueba**, y no hay mutación que enseñar. Lo que verifica el texto
  corregido son las dos comprobaciones `git diff --quiet` de arriba y la
  invocación de `scripts/check.ps1` que sigue.

- **Comprobación de la ronda 14, sobre el árbol de `2678e87`**: una sola
  invocación de `pwsh -File scripts/check.ps1` (Ruff format, Ruff lint, mypy,
  pytest), código de salida **0**,
  `5102 passed, 17 skipped, 2 xfailed in 441.80s (0:07:21)`. La terna es la
  misma de la ronda 13 (`5102 passed, 17 skipped, 2 xfailed`) porque esta ronda
  es documental: no añade ni quita ninguna prueba, y por eso tampoco hay
  mutación que enseñar.

  Lo único que cambia en el árbol después de esta captura es la transcripción
  de estas mismas cifras.

- **Ronda 15 (CODEX-001, la misma revisión): la observación llegó otra vez y ya
  estaba resuelta; lo que faltaba era dejar escrito el límite que el
  propietario aceptó.** La revisión que abre esta ronda es la MISMA que abrió
  la 14 -`pullrequestreview-5135487058`, publicada el 07-09-2026 a las
  22:11:28Z sobre el árbol de `a538cdd`-, es decir, sobre el head ANTERIOR a
  la corrección de la ronda 14 (`2678e87`, 22:29:28Z). Comprobado con
  `gh api repos/.../pulls/546/reviews --jq '.[] | select(.id==5135487058) |
  {submitted_at, commit_id}'`, que devuelve
  `{"commit_id":"a538cdde...","submitted_at":"2026-09-07T22:11:28Z"}`. Por eso
  esta ronda no reabre el hallazgo: sobre el head vigente, los cinco pasajes
  que lo motivaban ya están acotados.

  Lo que sí quedaba pendiente de registrar es la decisión del propietario del
  07-09-2026 (22:36 UTC), posterior a `2678e87` y por tanto ausente de la
  entrada de la ronda 14, que ratifica el reparto y añade una frase que el
  propietario pidió expresamente dejar por escrito «para que la próxima
  revisión no lo levante como nuevo»: **hasta que entre la ficha del operador
  que cambia el grupo de concurrencia del notificador -una ranura por evento,
  conservando la idempotencia por run que protege los reintentos-, el canal
  puede perder un evento intermedio de la misma etiqueta**, y el reflector lo
  trata como lo que es, un hueco del historial, con los respaldos que ya
  tiene. Esa limitación **no la introduce #546: la hereda de `main`** (autoría
  `07a51b1` y `f2085db`), y el §7 del contrato promete de más mientras esa
  ficha no entre. La decisión del propietario del 07-09-2026 (22:22 UTC) es la
  que asigna esa corrección a la ficha propia del operador, con su guardián y
  con el §7 acotado a lo que la cola garantiza de verdad.

  Esta ronda, por tanto, **no cambia ni una línea de código ni ninguna
  prueba**: no hay mutación que enseñar. Lo que verifica su texto son la
  consulta a la API de arriba, `git diff --quiet main HEAD -- .github/` -que
  sigue saliendo en **0**- y la invocación de `scripts/check.ps1` que sigue.

- **Comprobación de la ronda 15, sobre el árbol de `535f7ff`**: una sola
  invocación de `pwsh -File scripts/check.ps1` (Ruff format, Ruff lint, mypy,
  pytest), código de salida **0**,
  `5102 passed, 17 skipped, 2 xfailed in 443.32s (0:07:23)`. La terna es la
  misma de las rondas 13 y 14 (`5102 passed, 17 skipped, 2 xfailed`) porque
  esta ronda es documental: no añade ni quita ninguna prueba, y por eso
  tampoco hay mutación que enseñar.

  Lo único que cambia en el árbol después de esta captura es la transcripción
  de estas mismas cifras.

## Consecuencias

- **Ronda 6, CLAUDE-R6-001 y CLAUDE-R6-002 (misma raíz): la cota de la parada
  nunca se adelanta a la parada real.** El emparejamiento «cada parada toma el
  diagnóstico no consumido más antiguo publicado antes de ella» descansaba en
  un hecho que solo vale DENTRO de una serie `(etiqueta, head)`: la
  deduplicación de `notify-sirius-state.yml` suprime los avisos posteriores del
  MISMO head, pero una parada sobre un head NUEVO vuelve a publicar marcador.
  Con dos paradas sobre H1 y una tercera sobre H2, el marcador de H2 heredaba
  el veredicto de la segunda parada de H1: el diario escribía una parada con el
  texto de otra (R6-002) y, peor, `_orden_de_la_parada` devolvía una posición
  ADELANTADA con la que `_consumir_permiso` aceptaba un `continua` escrito
  ANTES de la parada real (R6-001) -inventar un permiso que el propietario no
  dio, que es la familia de defecto que el encargo prohíbe-. `_atribuir_diagnosticos`
  añade ahora la tercera condición: todo diagnóstico pendiente publicado antes
  de un marcador y que no sea el suyo tiene que pertenecer a un marcador
  POSTERIOR, porque los que la deduplicación deja sin marcador son siempre
  posteriores al superviviente de su serie; cuando no caben, la evidencia no
  discrimina y la proyección se ABSTIENE (`None`, sin `orden_del_veredicto`),
  con lo que la cota vuelve a la posición del aviso, posterior a todos ellos y
  por tanto segura. Pruebas, las dos vistas fallar sobre f62f238:
  `test_el_marcador_de_otra_serie_no_hereda_el_diagnostico_de_la_serie_anterior`
  (`tests/engine/test_mirror_projection.py`), con la mutación que anula la
  condición nueva (`if candidatos - 1 > len(paradas) - posicion - 1:` →
  `if False:`), que atribuye «B» y cota 4 al marcador de la serie nueva; y
  `test_una_parada_de_otra_serie_no_se_levanta_con_un_permiso_anterior_a_ella`
  (`tests/engine/test_reflect.py`), con la mutación gemela en el doble
  `_cronologia` (`if not pendientes or len(pendientes) - 1 > …:` →
  `if not pendientes:`), que devuelve el plan completo de siete pasos hasta
  `delivered/entregar` en vez de `()`. Ninguna prueba existente se tocó: siguen
  verdes `test_un_aviso_de_parada_retrasado_no_niega_el_permiso_que_si_se_escribio`,
  `test_un_permiso_anterior_a_la_parada_no_la_levanta`,
  `test_el_marcador_deduplicado_conserva_el_diagnostico_de_la_primera_parada`,
  `test_tres_diagnosticos_y_un_marcador_no_atribuyen_el_ultimo`,
  `test_una_parada_sin_diagnostico_publicado_hasta_ella_no_hereda_el_siguiente`
  y `test_un_aviso_de_parada_retrasado_no_le_roba_el_diagnostico_a_la_otra`.
- **La correlación por identidad cubre solo `failed-safely` (CLAUDE-R6-003,
  ronda 6), y desde la ronda 7 eso ya no acredita de más.** La identidad que se
  transporta es el diagnóstico del veredicto, y `sirius:blocked-decision` no
  publica ninguno: `_atribuir_diagnosticos` solo rellena `orden_del_veredicto`
  para los acreditados `FAILED_SAFELY`, así que un marcador `blocked-decision`
  -parada de pleno derecho en `_PARADAS`- llega siempre con
  `orden_del_veredicto is None` y se correlaciona por la posición de su AVISO.
  Lo que la ronda 6 escribió aquí -«es el lado conservador del defecto, nunca
  acredita de más»- **era falso por el flanco contrario, y se retira**: con dos
  `blocked-decision` sobre el MISMO head, el notificador deduplica el aviso de
  la segunda, el filtro de identidad no discrimina (no hay diagnóstico que
  comparar) y el recorrido anclaba en el aviso de la PRIMERA, cuya cota deja
  pasar el `continua` escrito para ella: un `NEEDS_DECISION` se resolvía sin su
  permiso (CLAUDE-R7-001, ronda 7). El mismo hueco por el otro lado: un
  acreditado con `diagnostico is None` por la ABSTENCIÓN de CLAUDE-R6-002
  tampoco lo descarta el filtro, así que servía de ancla aunque el almacén
  guardara un veredicto de parada POSTERIOR a ese aviso (CLAUDE-R7-002).

  **Corrección de la ronda 7 (07-09-2026), la misma para los dos y por
  abstenerse, nunca por acreditar más.** La proyección publica ahora la
  cronología de los VEREDICTOS de parada (`ParadaPublicada`,
  `mirror_projection._interpretar_paradas_publicadas`, `_STOP_MARKER_RE`), que
  existen aunque `sirius_comment_once` haya deduplicado su aviso. Cuando el
  motor está parado y el ancla no quedó identificada por su propio diagnóstico,
  `reflect._ancla_del_recorrido` **abandona el recorrido** si hay un veredicto
  de parada publicado después de la cota del ancla que el almacén pudo guardar
  (`publicado_en <= work_item.updated_at`): la evidencia no dice en cuál de las
  dos paradas se quedó el motor, así que se conserva la divergencia declarada.
  Lo fijan `test_una_segunda_parada_sin_aviso_propio_no_se_resuelve_con_el_permiso_de_la_primera`
  y `test_un_acreditado_sin_diagnostico_no_ancla_si_queda_una_parada_posterior`
  (`tests/engine/test_reflect.py`), vistas caer con la mutación
  `parada.orden > cota` → `parada.orden > cota + 10_000` en
  `reflect._hay_una_parada_posterior_sin_aviso`: las dos devuelven el plan
  completo hasta `delivered/entregar` en vez de `()`
  (`AssertionError: assert (PasoReflejo(...)) == ()`).

- **CLAUDE-R7-003 (P2, ronda 7): el doble de las pruebas vuelve a estar atado a
  producción también en los PERMISOS.** La ronda 6 le copió al doble
  `_cronologia` el colapso del recibo con su orden sin extender la prueba de
  acoplamiento que CLAUDE-R5-002 exigió, y las dos copias ya divergían:
  producción limpia la orden pendiente con cualquier veredicto de parada
  (`_STOP_MARKER_RE`) y el doble solo con la entrada `diagnostico`.
  `test_el_doble_de_cronologia_proyecta_lo_mismo_que_la_proyeccion_real` compara
  ahora, además de los acreditados, la tupla de `permisos_reanudacion` y la de
  `paradas_publicadas` (forma y posición relativa), con entradas que traen la
  orden con su recibo colapsado, la orden con un veredicto de parada entre
  medias y el recibo que entonces cuenta solo. El doble gana la entrada
  `("parada", …)` -un veredicto de parada sin diagnóstico ni aviso propio- que
  limpia la orden pendiente igual que producción. Vista caer con la mutación
  `orden_sin_recibo = None` → `pass` en esa rama del doble:
  `AssertionError: assert ((<FormaDePer... 'orden'>, 6)) == ((<FormaDePer...arcador'>, 8))`,
  «Right contains one more item». La referencia sigue siendo producción: no se
  tocó `mirror_projection._interpretar_permisos_reanudacion`.

- El caso vivo avanza: WI-20260905-034826 llega a `delivered/entregar` y la
  pasada siguiente no añade nada.
- Las recuperaciones sin ninguna palabra escrita del propietario quedan como
  divergencia declarada. Es la consecuencia aceptada y deliberada del encargo.
- Un `NEEDS_DECISION` jamás se resuelve en el almacén sin su permiso: desde
  la ronda 7 también cuando la segunda parada sobre el mismo head se quedó
  sin aviso propio, porque entonces no hay ancla (CLAUDE-R7-001).
- El almacén gana memoria de tramos intermedios que ninguna pasada observó:
  el diario registra las transiciones reales, no un salto.
- El defecto que la ronda 4 aplazó por plazo (ADR-155) queda **corregido en la
  ronda 5**, por la vía de raíz que el propietario registró el 06-09-2026:

  - **CLAUDE-R4-001** (P1, `reflect.py`), **corregido en la ronda 5**. El
    orden de una parada era la posición de su marcador `sirius-notification`, y
    `_consumir_permiso` exige un permiso posterior a ese orden. Como
    `notify-sirius-state.yml` mete el nombre de la etiqueta en su grupo de
    concurrencia, los avisos de etiquetas distintas no se serializan entre sí:
    el aviso de una parada puede publicarse DESPUÉS del permiso que la levantó,
    y entonces no quedaba ningún permiso posterior y una recuperación que el
    propietario sí autorizó por escrito quedaba como divergencia declarada para
    siempre.

    Se corrige **transportando la identidad del suceso**, que es la vía de raíz
    que el propietario registró: `EstadoAcreditado` lleva ahora
    `orden_del_veredicto` —la posición del comentario de veredicto que causó la
    parada, el mismo que le dio su `diagnostico`—, `_atribuir_diagnosticos` la
    rellena al emparejar, y `reflect._orden_de_la_parada` la usa como posición
    de la parada, volviendo a la del aviso solo cuando no hay ningún veredicto
    atribuible. El veredicto es síncrono, lo publica el propio rol y
    `sirius_apply_verdict.sh` lo escribe SIEMPRE antes de aplicar la etiqueta,
    así que la correlación parada-permiso deja de depender de dónde cayó el
    aviso. El criterio de ADR-147 no se toca: el permiso escrito sigue siendo
    la única acreditación, sigue teniendo que ser estrictamente posterior a la
    parada y se sigue consumiendo en orden.

    El obstáculo que la ronda 4 midió —el doble `_cronologia` da el mismo
    `head` a todas las ocurrencias, así que correlacionar por head desnudo
    haría pasar `test_un_permiso_anterior_a_la_parada_no_la_levanta`— queda
    resuelto sin tocar el head: el discriminante es la posición del veredicto,
    no el head. Esa prueba sigue verde sin cambiarla, porque un historial sin
    veredicto atribuible conserva la referencia de siempre. Lo fija
    `test_un_aviso_de_parada_retrasado_no_niega_el_permiso_que_si_se_escribio`
    (`tests/engine/test_reflect.py`), vista fallar con
    `_orden_de_la_parada` devolviendo siempre `acreditado.orden`.

  Y uno **corregido en la ronda 4**, que se registra aquí porque cambia el
  criterio de atribución:

  - **CLAUDE-R4-002** (P2, `mirror_projection.py`), **corregido en la ronda 4**;
    su corrección se **rehízo en la ronda 5** (CLAUDE-R5-001 y CODEX-001).
    `_diagnostico_hasta` atribuía a cada marcador de parada el último
    diagnóstico publicado ANTES de su posición; con el aviso de la primera
    parada retrasado tras el veredicto de la segunda, las dos ocurrencias se
    proyectaban con el diagnóstico de la SEGUNDA. La ronda 4 lo sustituyó por
    `_atribuir_diagnosticos` emparejando por rango **alineado desde el final**,
    razonando que así se respetaba la deduplicación por estado y head. Ese
    razonamiento estaba invertido: `sirius_comment_once` lee el historial y, si
    el marcador ya está presente, devuelve sin publicar, o sea **conserva el
    primero y suprime los posteriores**. Con más diagnósticos que marcadores
    —el caso central del encargo, dos paradas sobre un mismo head— el único
    marcador es el de la PRIMERA parada y la alineación desde el final le daba
    el diagnóstico de la ÚLTIMA. Vía el filtro del ancla de `reflect`, un
    diagnóstico ajeno no solo copia mal el diario: descarta la ocurrencia y
    abandona el recorrido entero.

    La regla vigente sale de dos hechos del sistema real: (1) un diagnóstico
    publicado DESPUÉS de un marcador no puede ser suyo, porque
    `sirius_apply_verdict.sh` publica el diagnóstico y solo después aplica la
    etiqueta que dispara el aviso; y (2) el marcador que sobrevive a la
    deduplicación es el de la primera parada de su serie. De ahí el
    emparejamiento actual: **cada parada notificada, de la más antigua a la más
    reciente, toma el diagnóstico no consumido más antiguo publicado ANTES de
    ella, y `None` si no hay ninguno**; los diagnósticos se consumen, así que
    ninguno acredita dos paradas. Sigue cubierto lo que la ronda 4 sí midió
    bien —el aviso retrasado no le roba el diagnóstico a la otra parada—,
    porque el consumo va en orden y no es «el último publicado hasta aquí».

    Lo fijan `test_el_marcador_deduplicado_conserva_el_diagnostico_de_la_primera_parada`
    y `test_tres_diagnosticos_y_un_marcador_no_atribuyen_el_ultimo`
    (`tests/engine/test_mirror_projection.py`), vistas fallar contra la
    alineación desde el final antes de corregir, y sin relajar
    `test_una_parada_sin_diagnostico_publicado_hasta_ella_no_hereda_el_siguiente`
    ni `test_un_aviso_de_parada_retrasado_no_le_roba_el_diagnostico_a_la_otra`.

    **CLAUDE-R5-002, cerrado en la misma ronda.** El doble de pruebas
    `_cronologia` de `tests/engine/test_reflect.py` seguía con la atribución
    posicional antigua, así que fabricaba `EstadoAcreditado` que la proyección
    no puede producir. Ahora aplica exactamente el mismo consumo en orden, y lo
    fija una prueba de acoplamiento —
    `test_el_doble_de_cronologia_proyecta_lo_mismo_que_la_proyeccion_real`—
    que pasa el MISMO historial por los dos caminos y exige que coincidan en
    etiqueta, estado, fase, diagnóstico y en la distancia entre el marcador y
    el veredicto que lo explica. Ni
    `test_una_parada_sin_diagnostico_atribuible_no_recrea_ninguno` ni
    `test_un_marcador_con_otro_diagnostico_no_ancla_la_parada_guardada` han
    tenido que tocarse: la temida caída era de la alineación por rango, no de
    esta regla.

  R4-001, R4-002 y R5-001 eran la misma familia —acreditar, negar o explicar la
  salida de una parada por la POSICIÓN de un aviso asíncrono— y se cierran por
  la misma vía de raíz: **transportar la identidad del suceso** desde
  `mirror_projection` a través de `EstadoAcreditado` (`orden_del_veredicto`)
  hasta `reflect`, para correlacionar parada, diagnóstico y permiso por
  identidad y no por posición.

- **CLAUDE-R5-003 resuelto por decisión del propietario (07-09-2026, 14:55
  UTC), lectura (b): la orden y su recibo son el MISMO acto.** El problema
  medido en la ronda 5 era real: una sola autorización del propietario deja
  sistemáticamente DOS rastros -la orden `continua` y el recibo que
  `sirius_resume_on_command.sh` publica al procesarla; en el historial real de
  la #537, las 04:45 y las 04:46-, y `_interpretar_permisos_reanudacion` los
  contaba como dos elementos de `permisos_reanudacion`. Con dos avisos de
  parada consecutivos y una sola palabra escrita después, esa autorización
  levantaba las DOS paradas, en contra de lo que afirma el docstring de
  `_consumir_permiso` («un permiso no puede acreditar dos salidas»).

  El propietario decidió la lectura (b) y autorizó reescribir la prueba que
  fijaba lo contrario. Desde la ronda 6, `_interpretar_permisos_reanudacion`
  COLAPSA el recibo con la orden a la que responde: un marcador de reanudación
  que sigue a una orden `continua` todavía sin recibo, y sin ninguna PARADA
  publicada entre medias (`_STOP_MARKER_RE`, que es la que abre un suceso
  nuevo), no añade un segundo permiso. Las dos formas siguen valiendo una cada
  una cuando llegan solas, que es para lo que existen: un recibo sin orden
  previa legible -otra automatización reanuda- y una orden sin recibo -el
  recibo deduplicado por `sirius_comment_once` sobre el mismo head-. El
  docstring de `_consumir_permiso` conserva su afirmación, que con este cambio
  pasa a ser verdad.

  Lo fijan tres pruebas de `tests/engine/test_mirror_projection.py`
  -`test_los_permisos_de_reanudacion_llevan_las_dos_formas_en_orden`,
  reescrita por la decisión; `test_una_parada_entre_la_orden_y_su_recibo_deja_los_dos_permisos`;
  `test_un_recibo_sin_orden_previa_sigue_siendo_un_permiso`- y
  `test_una_sola_autorizacion_no_levanta_dos_paradas_consecutivas`
  (`tests/engine/test_reflect.py`), que sobre dos paradas seguidas y una sola
  autorización exige `pasos == ()` y divergencia declarada. Vistas fallar con
  la mutación que devuelve el conteo por separado (`if orden_sin_recibo is not
  None:` → `if False:` en `mirror_projection`, y el mismo colapso desactivado
  en el doble `_cronologia`): «AssertionError: el recibo de la posición 4 es el
  mismo acto que la orden de la 3» y el diff de los cinco permisos de la
  prueba reescrita. El doble `_cronologia` de `tests/engine/test_reflect.py`
  colapsa igual que la proyección, para no fabricar permisos que producción no
  produce (CLAUDE-R5-002).

- Queda pendiente, como ficha del operador, endurecer
  `sirius_resume_on_command.sh` para que su marcador lleve run/intento y nunca
  se deduplique. Mientras no se haga, la orden `continua` es la única forma de
  permiso disponible para la segunda reanudación sobre un mismo head.

- **ADR-157 cambia el emisor: desde el 07-09-2026 cada parada deja su propio
  aviso (CLAUDE-R8-001 y CLAUDE-R8-002, ronda 8).** Toda la maquinaria
  heurística de las rondas 6 y 7 —la abstención de `_atribuir_diagnosticos`,
  `ParadaPublicada` y `_hay_una_parada_posterior_sin_aviso`— se justificaba en
  una premisa sobre el emisor: `notify-sirius-state.yml` publicaba el marcador
  `<!-- sirius-notification:<etiqueta>:<head> -->` y `sirius_comment_once` lo
  deduplicaba por marcador completo, así que una segunda parada sobre el mismo
  head no dejaba rastro propio. ADR-157 (PR #562, fusionado en `main` el
  07-09-2026 a las 17:07:32Z, once minutos después del head `8f884b8b` de esta
  rama) arregla eso en el origen: el marcador es ahora
  `<!-- sirius-notification:<etiqueta>:<head>:<run> -->` y cada evento de
  etiqueta deja el suyo.

  Dos consecuencias, ambas de esta ronda:

  1. **El patrón de la proyección leía mal el marcador nuevo.**
     `_NOTIFICATION_MARKER_RE` capturaba el head con `[^\s>]*`, que incluye los
     dos puntos, así que sobre el marcador vigente `EstadoAcreditado.head`
     guardaba `1c934781:33951766681` en vez de `1c934781`. Hoy `src/` no lee
     ese campo, así que no había regresión de comportamiento, pero es un campo
     público cuyo docstring promete el head y solo el head. El patrón lee ahora
     el head hasta el primer `:` y DESCARTA el tramo del run si lo hay, de modo
     que las dos formas conviven: los historiales publicados antes de ADR-157
     —las incidencias ya vividas, que ADR-157 declara que «conservan sus
     huecos»— siguen leyéndose igual. Lo fijan dos pruebas nuevas de
     `tests/engine/test_mirror_projection.py`,
     `test_historial_estados_lee_el_marcador_con_run_sin_pegarlo_al_head` y
     `test_historial_estados_sigue_leyendo_el_marcador_sin_run`.
  2. **La heurística de las rondas 6 y 7 permanece, pero como RESPALDO de los
     historiales antiguos, y así queda declarado aquí** —que es exactamente lo
     que ADR-157 pide en sus «Consecuencias»—. No se retira ni una línea: las
     incidencias ya vividas conservan sus huecos y siguen necesitándola. Lo que
     cambia es el texto: las siete afirmaciones que la describían EN PRESENTE
     («el guion deduplica por marcador completo», «el marcador que sobrevive a
     la deduplicación es el de la primera parada de su serie», los puntos 2 y 4
     de `_ancla_del_recorrido`, `ParadaPublicada`,
     `_hay_una_parada_posterior_sin_aviso`, `_interpretar_paradas_publicadas` y
     el cierre de `_orden_de_la_parada`) quedan acotadas al árbol en que fueron
     ciertas y citando ADR-157, igual que la ronda 4 hizo con `check.ps1` y
     ADR-153.

     La ronda 8 escribió aquí, y en el docstring de
     `_hay_una_parada_posterior_sin_aviso`, que «sobre un historial publicado
     después de ADR-157 esa función sencillamente no encuentra ninguna parada
     sin aviso y no se abstiene». **Era falso y la ronda 9 lo corrige**
     (CLAUDE-R9-001): la función recorre `paradas_publicadas` -los VEREDICTOS
     de parada- y no consulta `historial_estados` en ningún momento, así que no
     puede saber si la parada posterior dejó aviso propio. Se abstiene ante
     CUALQUIER veredicto de parada posterior a la cota que el almacén pudo
     guardar, también sobre historiales posteriores a ADR-157. La limitación
     viva, entonces, es más ancha que la de CLAUDE-R6-003 -que la acotaba a los
     avisos RETRASADOS-: con el motor anclado en un `sirius:blocked-decision`
     -que llega sin diagnóstico, porque `escalate` no escribe ninguno, y por
     tanto no discrimina por identidad- cualquier veredicto de parada posterior
     **que el almacén pudo guardar** (`publicado_en <= updated_at`) abandona el
     recorrido y declara divergencia, aunque cada parada traiga su aviso y su
     `continua`. Es conservador -no acredita ninguna salida que nadie
     autorizase- y queda declarado aquí en vez de retirado, porque retirarlo
     tocaría la lógica de la abstención, fuera de los límites de
     CLAUDE-R9-001. Lo fija la prueba
     `test_la_abstencion_tambien_alcanza_a_la_parada_posterior_con_aviso_propio`
     de `tests/engine/test_reflect.py`, que declara el comportamiento tal y
     como está escrito.

     El **alcance** de esa limitación lo acota la ronda 12 (CLAUDE-R12-001):
     llega solo hasta el veredicto que el almacén PUDO guardar, que es el caso
     en que la evidencia no dice en cuál de las dos paradas se quedó el motor
     -el de CLAUDE-R7-001 y CLAUDE-R7-002-. El veredicto publicado DESPUÉS de
     la última escritura del almacén -el caso normal, porque el tramo que el
     recorrido reproduce es por definición posterior a esa escritura- no
     abstiene nada: ahí el recorrido recrea la parada y le exige su permiso
     escrito, y lo fija la prueba nueva
     `test_una_parada_posterior_a_la_ultima_escritura_no_abstiene_el_ancla`.
     Hasta la ronda 12 este punto y el docstring de la función dejaban caer ese
     calificador en la frase que describe el efecto, y la prueba que lo fijaba
     alimentaba al reflector un `ParadaPublicada` con `publicado_en=None`, una
     forma que `mirror_projection._interpretar_paradas_publicadas` no emite
     -todo veredicto de parada se publica como comentario y llega con su
     `creado_en`-: el ADR afirmaba una limitación más ancha que la de
     producción y la prueba la sostenía con una entrada imposible.

  El criterio de acreditación de ADR-147 no cambia: un permiso escrito por
  salida, consumido en orden, y la foto nunca acredita.

- **Ronda 10, CLAUDE-R10-001: el recorrido tampoco pasa por encima de un
  veredicto de parada que ningún tramo suyo recrea.** La abstención de la
  ronda 7 (`_hay_una_parada_posterior_sin_aviso`) pregunta por el ANCLA, y
  `_ancla_del_recorrido` no llega siempre a esa guarda: cuando exactamente una
  ocurrencia lleva el diagnóstico que el almacén guardó, el punto 3 -la
  identidad del suceso- devuelve esa ocurrencia ANTES de evaluarla. Con el
  ancla identificada así, un veredicto de parada POSTERIOR sin aviso propio
  -en los historiales anteriores a ADR-157 `sirius_comment_once` deduplicaba
  el marcador por `(etiqueta, head)`, y también falta si el workflow del
  notificador falló- no recreaba ningún tramo de parada en el recorrido, y el
  bucle solo exige permiso cuando el `WorkItem` simulado ENTRA en una parada:
  esa segunda salida se acreditaba con CERO permisos escritos.

  La corrección no proyecta ningún dato nuevo -`espejo.paradas_publicadas` ya
  llega a la función- ni relaja `_consumir_permiso`: al empezar el recorrido,
  `_paradas_que_el_recorrido_debe_recrear` lista los veredictos posteriores a
  la cota del ancla (`_orden_de_la_parada`) -la ronda 10 los filtraba además
  por su instante de publicación, y ese filtro dejaba la lista siempre vacía;
  lo corrige la ronda 11, CLAUDE-R11-001, más abajo-; el bucle salda
  uno por cada parada que recrea, en orden, igual que se consumen los
  permisos; y si al terminar queda alguno sin saldar, el recorrido se abandona
  entero (`return None`) y el llamador conserva la divergencia de siempre. Un
  veredicto que SÍ tiene su tramo se comporta exactamente como antes:
  consume su permiso y el recorrido llega hasta la foto. Lo fijan dos pruebas
  nuevas de `tests/engine/test_reflect.py`:
  `test_una_parada_que_ningun_tramo_recrea_abandona_el_recorrido` -la roja, con
  el ancla identificada por su diagnóstico y un segundo veredicto sin aviso- y
  su gemela en verde
  `test_una_parada_con_su_tramo_en_el_recorrido_se_sigue_recorriendo_entera`.

  **Lo que la observación describía y NO se pudo reproducir tal cual.**
  CLAUDE-R10-001 proponía el escenario con el motor en `ACTIVE/EJECUTAR` y la
  foto `sirius:completed`. Sobre ese par, `reflejar_desenlace` ni siquiera
  consulta el recorrido acreditado: `_reflejar_por_foto` encuentra camino de
  fase hacia delante -`EJECUTAR -> COMPROBAR -> REVISAR -> ENTREGAR` y
  `work_item_delivered`- y devuelve ese plan (regla 6: el recorrido solo
  contesta si la foto declaró divergencia). Que el reflejo por foto avance sin
  mirar `paradas_publicadas` cuando el motor NUNCA estuvo parado es otra
  cuestión, y su corrección viviría en `_reflejar_por_foto`, expresamente
  fuera de los límites de CLAUDE-R10-001. El defecto que sí es del recorrido
  -atravesar un veredicto de parada sin recrearlo ni pagar su permiso- es el
  que fija la prueba roja de arriba, por la puerta que de verdad lo alcanza.

- **Ronda 11, CLAUDE-R11-001 y CLAUDE-R11-002 (misma raíz): el tramo que el
  recorrido reproduce lo delimita la cota del ancla, no `updated_at`.** La
  abstención que la ronda 10 acaba de describir era INERTE.
  `_paradas_que_el_recorrido_debe_recrear` filtraba su lista con
  `parada.publicado_en is None or parada.publicado_en <= work_item.updated_at`,
  que es el predicado de `_el_almacen_pudo_guardarla` y responde a la pregunta
  del ANCLA -«¿en cuál de las ocurrencias se quedó el almacén?»-, donde sigue
  siendo correcto. La pregunta de esta función es otra: «¿qué veredictos de
  parada caen dentro del tramo que el recorrido reproduce?». Y ese tramo es,
  por definición del recorrido acreditado, lo que ocurrió DESPUÉS de la última
  escritura del almacén, así que todo veredicto suyo tiene
  `publicado_en > updated_at` y quedaba excluido: la lista salía siempre vacía
  y el recorrido volvía a atravesar la parada sin recrearla y sin consumir
  ningún permiso, que es exactamente CLAUDE-R10-001. La corrección quita ese
  filtro: la cota del ancla es la única que delimita el tramo, porque el
  historial de confianza termina en la foto y todo veredicto por detrás del
  ancla cae dentro de lo que el recorrido reproduce. Con ello desaparece
  también la segunda forma del fallo que la observación describía -un veredicto
  excluido conviviendo con otro incluido hacía que `paradas_por_recrear.pop(0)`
  saldara el veredicto equivocado-, porque ya no hay exclusiones. Lo fija la
  prueba nueva
  `test_una_parada_fechada_que_ningun_tramo_recrea_abandona_el_recorrido`
  (`tests/engine/test_reflect.py`), gemela FECHADA de la roja de la ronda 10:
  mismas cinco entradas, almacén parado a las 05:01 y segundo veredicto de
  parada publicado a las 05:04, `pasos == ()` y divergencia.

  Por qué no se detectó en la ronda 10 -CLAUDE-R11-002-: el doble `_paradas`
  construye `ParadaPublicada` con `publicado_en=None` salvo que se le pase
  `desde`, y ninguna prueba de recorrido se lo pasaba; con `None` el filtro
  dejaba pasar todo. La proyección real
  (`mirror_projection._interpretar_paradas_publicadas`) NO produce esa forma:
  todo veredicto de parada se publica como comentario -el cuerpo del encargo no
  lleva ninguno- y llega siempre con su `creado_en`. La referencia sigue siendo
  producción: no se toca la proyección ni `ParadaPublicada`, sino el doble y
  su prueba de acoplamiento, que ahora compara también los INSTANTES
  (`test_el_doble_de_cronologia_proyecta_lo_mismo_que_la_proyeccion_real`,
  tercera repetición de la familia CLAUDE-R5-002 / CLAUDE-R7-003), y la prueba
  nueva del P1 corre con instantes reales.

- **Ronda 12, CLAUDE-R12-001 y CLAUDE-R12-002 (misma raíz): el doble ya no
  puede emitir una forma que la proyección no emite, y el alcance de la
  abstención queda escrito.** La aserción que la ronda 11 añadió a
  `test_el_doble_de_cronologia_proyecta_lo_mismo_que_la_proyeccion_real`
  -`all(parada.publicado_en is not None ...)` sobre la proyección REAL- dejó a
  la vista que el resto del árbol seguía contradiciéndola: `_paradas` conservaba
  `desde: datetime | None = None` y seis llamadas de las pruebas de recorrido lo
  usaban así, de modo que `_hay_una_parada_posterior_sin_aviso` y
  `_el_almacen_pudo_guardarla` se ejercitaban por el atajo `publicado_en is
  None` sin llegar nunca a la comparación de instantes que producción sí
  ejecuta (CLAUDE-R12-002). La corrección hace `desde` OBLIGATORIO en `_paradas`
  y fecha las seis llamadas con el instante que corresponde al motor que cada
  prueba construye: `_ANTES_DEL_ALMACEN` (11:00 del 4-09, anterior al
  `updated_at`) cuando lo que se prueba es el veredicto que el almacén PUDO
  guardar, y `_TRAS_EL_ALMACEN` (05:00 del 5-09) cuando lo que se prueba es el
  tramo que el recorrido reproduce. Las pruebas de las rondas 7 y 10 añaden
  además la aserción que dice POR QUÉ siguen verdes -el instante del último
  veredicto contra `updated_at`-, para que el resultado no se atribuya al
  mecanismo equivocado. `_cronologia` conserva `desde` opcional porque su
  `None` sí tiene fuente real: el marcador que viene del cuerpo de la
  incidencia, que no trae `creado_en`.

  Con las entradas fechadas quedó demostrado lo que la ronda 9 había escrito de
  más (CLAUDE-R12-001): tanto este ADR como el docstring de
  `_hay_una_parada_posterior_sin_aviso` describían el efecto observable sin el
  calificador que el código sí tiene -`publicado_en <= updated_at`-, y
  `test_la_abstencion_tambien_alcanza_a_la_parada_posterior_con_aviso_propio`
  fijaba ese `pasos == ()` alimentando `publicado_en=None`. Fechada con
  instantes del tramo recorrido, esa prueba se pone en ROJO
  (`E AssertionError: assert resultado.pasos == ()`, contra un plan de ocho
  pasos que llega a `work_item_delivered`), que es el comportamiento CORRECTO:
  un permiso escrito por salida, el `continua` de la posición 1 para la primera
  parada y el de la posición 5 para la segunda. La corrección refunda la prueba
  sobre instantes ANTERIORES a la última escritura del almacén -donde la
  limitación existe de verdad- y añade su gemela
  `test_una_parada_posterior_a_la_ultima_escritura_no_abstiene_el_ancla`, que
  fija el otro lado. Ninguna línea de lógica cambia: el filtro por `updated_at`
  de la abstención sigue siendo el correcto para el escenario de CLAUDE-R7-001
  y CLAUDE-R7-002.

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
