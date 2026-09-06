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
  aun así `pwsh -File scripts/check.ps1` terminaba en **0**: `scripts/check.ps1`
  encadena los cuatro comandos sin comprobar el código de salida de cada uno y
  PowerShell no propaga el de un ejecutable nativo, de modo que el código de
  salida del script es el de `pytest` y solo el de `pytest`. En Quality no hay
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

  Que `scripts/check.ps1` no propague el código de salida de sus tres primeros
  comandos queda **señalado y sin tocar**: es la validación obligatoria de
  ADR-145 y cambiarla es una decisión de ese ADR, no una de las observaciones
  de esta ronda. Mientras siga así, «código de salida 0 del script» acredita
  `pytest` y nada más, y por eso la línea de abajo transcribe además la salida
  de los otros tres comandos.

- El commit `923202f`, anterior a esta ronda, pasó `ruff format` sobre las dos
  pruebas que la corrección de la ronda 2 empujó sin formatear; no cambia
  ninguna afirmación de este ADR.
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
