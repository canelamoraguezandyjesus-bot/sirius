# Nota de arranque — el detector de familia repetida detiene el ciclo

- Fecha: 2026-09-14
- Rama: `mejora/el-detector-de-familia-detiene-el-ciclo`
- ADR previsto: ADR-199
- Decisión que la autoriza: el propietario, el 14-09-2026, con la cifra de
  ADR-197 delante (**14 aciertos y 2 falsos sobre 16**). El criterio que la
  incidencia #267 fijó —medir la tasa real antes de dar autoridad— queda
  cumplido por ADR-078 (4/0 sobre 14) y ADR-197 (14/2 sobre 16).

Publicada ANTES del primer commit de código, según ADR-001.

## 1. ¿Dónde vive el fallo y dónde va el arreglo?

El fallo vive en la puerta del veredicto,
`scripts/automation/sirius_apply_verdict.sh`, rama `CHANGES_REQUESTED`: el
detector se ejecuta, su resultado se publica como `## AVISO_FAMILIA_REPETIDA`,
y acto seguido se aplica `sirius:repair-requested` **exactamente igual que si
no hubiera avisado**. El ciclo da otra vuelta de parche sobre la misma familia.
El arreglo va justo ahí, en la transición, que es donde el dato ya está
calculado: `$family_notice` se construye unas líneas antes.

¿Puede el sitio del arreglo OBSERVAR el fallo que arregla? Sí. El veredicto
tiene el resultado del detector en la mano cuando elige la etiqueta.

**Y hay un segundo sitio que hoy NO puede observarlo, y esa es la parte
delicada.** Reanudar una parada (`continua`) lo resuelve
`scripts/automation/sirius_resume_on_command.sh`, que para
`sirius:blocked-decision` **lee el rol del marcador publicado** y devuelve el
trabajo a la fase de ese rol. Como esta parada la emite el **revisor**, el
marcador diría `reviewer` y `continua` repondría `sirius:review-requested`:
vuelta a revisión, misma familia, misma parada. Un rebote.

**Predicción escrita antes de tocar nada:** si solo cambio la puerta del
veredicto, una prueba de reanudación sobre esta parada devolverá
`sirius:review-requested`. Es literalmente la familia del defecto **H-33**
(incidencias #453 y #471), que este repositorio ya pagó cuando
`blocked-decision` devolvía siempre al corrector y el corrector arrancaba sin
nada que corregir. Por eso el arreglo son **dos** guiones, no uno.

## 2. ¿Qué NO va a garantizar esto?

- **No diagnostica la raíz ni propone la salida.** Eso sigue siendo la
  incidencia #251. Esto para y se lo pone delante a una persona; no adivina.
- **No elimina los falsos positivos.** Están medidos: 2 de cada 16. Cada uno
  cuesta que el propietario escriba `continua`. Ese es el precio aceptado, y
  se acepta porque el coste del otro lado también está medido: 7 rondas en la
  #501 y 15 en la #545.
- **No toca el umbral del detector** (3 rondas consecutivas sobre el mismo
  archivo) ni el agrupamiento que ADR-197 acaba de fijar.
- **No toca la política de convergencia** ni ninguno de sus umbrales. Son dos
  guardas distintas y siguen siéndolo.
- **No perdona rondas.** El reset del listón de convergencia se reserva a los
  bloqueos que emite la propia política; esta parada no lo lleva.
- **No toca `.github/**`** (ADR-002).

## 3. Criterio de parada — decidido ahora, antes de ver ningún resultado

El trabajo está terminado cuando las cuatro se cumplen:

1. Con familia repetida detectada, la puerta publica `sirius:blocked-decision`
   en vez de `sirius:repair-requested`, **sin perder nada de lo que ya
   publicaba**: las observaciones estructuradas y el `## RONDA_HALLAZGOS` de
   la ronda siguen en el comentario. Si se perdiera el registro de ronda, la
   política de convergencia dejaría de poder medir progreso: eso sería
   cambiar un defecto por otro peor.
2. `continua` sobre esa parada repone `sirius:repair-requested` —al corrector,
   que es quien tiene trabajo que hacer—, no `sirius:review-requested`.
3. Las dos propiedades tienen una prueba que se ha visto **FALLAR** antes del
   cambio (mutación en las dos direcciones, ADR-001 §3).
4. La cadena entera en verde: `ruff format --check`, `ruff check`, `mypy src
   tests`, `pytest`, `git diff --check`.

**Y me detengo, sin terminar, si ocurre cualquiera de estas dos:**

- Si para enrutar bien la vuelta hiciera falta **mentir sobre el rol** en el
  marcador —publicar `corrector` cuando quien paró fue el revisor—, paro y lo
  pregunto. El historial publicado es la única fuente que tiene el guion de
  reanudación para saber qué se paró; falsearlo rompería también las otras dos
  paradas que lo leen.
- Si el arreglo exigiera tocar `.github/**`, paro y lo dejo escrito: ninguna
  sesión del motor puede empujar ahí (ADR-002), y la #607 ya costó una hora de
  trabajo verde perdida por intentarlo.

## 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

Arreglar estos dos guiones deja el rebote arreglado **en este caso**. Lo que
lo haría imposible como clase es una prueba que **enumere todos los emisores
de `sirius:blocked-decision`** en `sirius_apply_verdict.sh` y exija que cada
uno tenga una vuelta declarada en `sirius_resume_on_command.sh`. Hoy no existe
nada así: H-33 se descubrió en producción, sobre dos incidencias reales, y
esta parada nueva es el tercer emisor que se añade a mano.

**Lo voy a intentar en este mismo trabajo.** Si resulta que no se puede
escribir de forma fiable —porque reconocer un emisor desde el texto del guion
exigiera un intérprete de shell, que es exactamente la razón por la que
ADR-001 retiró la puerta de `git push`—, lo diré aquí y en el ADR con esa
razón, en vez de dejar la pregunta sin contestar.
