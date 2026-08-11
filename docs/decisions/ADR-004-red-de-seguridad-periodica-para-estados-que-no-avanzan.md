# ADR-004 — Una red de seguridad periódica, porque un run muerto no puede avisar

- Estado: PROPUESTO
- Fecha: 2026-08-10
- Aprobación: la fusión de la PR que introduce este ADR, por el propietario

## Contexto y problema

La incidencia #138 registró una raíz, no un defecto: **un proceso que muere no
puede informar de su propia muerte**. La PR #136 intentó siete correcciones
seguidas para que el corrector siempre dejara veredicto, y las siete fallaron
por lo mismo —cada una vivía dentro del run que puede morir—:

| Corrección | Dónde vivía | Cómo se la saltó el fallo |
|---|---|---|
| Paso de diagnóstico medido | dentro del job | podía tumbar el job que observaba |
| «Veredicto como última acción» | dentro del corrector | `--max-turns` lo corta antes |
| Veredicto provisional al empezar | dentro del corrector | el tope del job lo corta antes |
| Topes de paso al corrector | dentro del job | la puerta quedaba sin acotar |
| Todos los pasos acotados | dentro del job | el corte externo no produce desenlace |
| Plazo interno de la puerta | dentro del paso | un `gh` colgado no se interrumpe |
| Encaminar todo por `_sirius_gh` | dentro del proceso | el checkout puede morir antes |

La octava tendría el mismo destino. **La lista es infinita porque el observador
está dentro de lo observado.**

Cuando un run muere, la incidencia queda con su etiqueta de estado puesta, y
`issues: labeled` **no vuelve a dispararse con una etiqueta ya aplicada**. El
flujo por eventos, por construcción, no puede notarlo.

La pieza que lo notaría ya existía y estaba probada —`sirius_reconcile.sh` tras
`reconcile-sirius-states.yml`— pero solo arrancaba con `workflow_dispatch`, y su
propia cabecera explicaba por qué: *el contrato prohíbe la vigilancia horaria
como motor del flujo*. Verificado: de trece workflows, **ninguno** tenía
`schedule:`. Es decir, la única pieza capaz de detectar un run muerto dependía de
que una persona detectara primero que había un run muerto.

## Criterio de parada (escrito ANTES de decidir)

- Si para detectar hiciera falta que el reconciliador **repare algo nuevo**, no
  se hace: eso es otra decisión.
- Si el coste de programarlo no se puede acotar con un número concreto, se
  pregunta en vez de estimar por encima.
- El umbral no se escribe a mano y ya está: se ata por prueba a los
  `timeout-minutes` reales (ADR-003).

## Opciones consideradas

1. **Programar el reconciliador** con una excepción acotada al contrato.
2. **Dejarlo abierto y documentado**, que era el estado vigente: defensas
   internas *best-effort* y desatasco manual.
3. **Un observador externo fuera de GitHub** (otro servicio que vigile).

## Decisión

**Opción 1**, con la frontera escrita en el contrato v1.6 §9.1.

La prohibición del contrato decía «vigilancia horaria como **motor** del flujo».
Esa palabra es la que hace el trabajo: lo prohibido es que el ciclo lo dirija una
tarea que sondea. Una red de seguridad que **no** inicia trabajo, **no** avanza
un ciclo sano, **no** fusiona, y ante la duda informa en vez de tocar, no es el
motor de nada. Ampliar la prohibición a «ninguna tarea programada jamás» era leer
en ella más de lo que dice, y el precio de esa lectura era quedarse sin la única
detección posible.

La opción 3 se descarta: introduce un servicio nuevo, y por tanto coste y
superficie, para hacer lo que GitHub ya puede hacer gratis.

**Cadencia: seis horas.** No es comodidad, es el coste: el job dura menos de un
minuto y GitHub factura por minuto empezado, así que 4 ejecuciones al día son
~120 min/mes de los 2000 gratuitos del repositorio privado; cada hora serían
~720. La latencia de detección de un repositorio de una sola persona no vale esa
diferencia.

**Qué se detecta.** No la muerte del run —eso solo lo sabe el run— sino que un
estado que solo la máquina puede mover lleva más de `STUCK_MINUTES` sin avanzar.
Es lo único observable desde fuera, y es suficiente.

**Qué se hace al detectarlo.** Se publica **un** comentario en la incidencia,
deduplicado por aplicación de etiqueta. No se repara. Un resumen de job que nadie
abre no es una detección; un comentario en la incidencia sí llega a una persona.

## Comprobación que la sostiene

- La fecha del estado la da GitHub (`/issues/{n}/events`, último evento
  `labeled` con esa etiqueta). Deducirla de `updated_at` de la incidencia sería
  reconstruir desde fuera un hecho ajeno —cualquier comentario la mueve— que es
  el mismo error que abrió todo esto. **RECON-STUCK-001** siembra ruido a
  propósito (eventos que no son `labeled`, otras etiquetas, dos aplicaciones de
  la misma) y falla si se fecha por la primera.
- **RECON-STUCK-002**: un estado de 10 minutos no se denuncia.
- **RECON-STUCK-003**: si el historial no se puede leer, **no se afirma nada**.
  Interpretar una lectura fallida como «lleva mucho» publicaría una acusación
  falsa en la incidencia.
- **RECON-STUCK-004**: dos pasadas, un solo comentario.
- **RECON-STUCK-005**: `blocked-decision`, `failed-safely` y `ready-for-merge`
  esperan a una persona por diseño; llevar semanas ahí es lo correcto.
- **RECON-STUCK-006**: el umbral se compara con los `timeout-minutes` **reales**
  de todos los workflows. Subir el revisor de 85 a 200 minutos rompe la prueba.
- **RECON-STUCK-007**: el `schedule:` existe, el disparo manual sigue, y el
  workflow conserva `contents: read` —no puede empujar nada—.
- El `gh` simulado aplica el `--jq` **real** con `jq`: si lo ignorara, el filtro
  —que es donde puede estar el defecto— no quedaría medido. Verificado por
  mutación: con el simulado devolviendo la línea ya filtrada, RECON-STUCK-001
  deja de fallar ante un filtro roto.
- Diez mutaciones en las dos direcciones, todas con el resultado predicho antes
  de ejecutarlas.

## Revisión: tres defectos que la primera versión sí tenía

Codex encontró tres, y los tres eran ciertos. Vale la pena que queden escritos
porque **dos son el mismo error**: dar por supuesto el comportamiento de otro
sistema en vez de comprobarlo.

1. **P1 — `gh api` pasaba a POST.** `label_applied_at` llamaba a
   `/issues/{n}/events` con `-f per_page=100` y sin `-X GET`. `gh` usa GET por
   defecto pero cambia a POST en cuanto hay un `-f`, y ese endpoint solo existe
   en GET: **toda** lectura fallaba, el estado nunca se podía fechar y la rama
   de fallo seguro impedía publicar un solo aviso. La red de seguridad habría
   estado muerta en producción sin que nada lo delatara. La otra llamada
   paginada del mismo script ya usaba `-X GET`: la regla estaba escrita al lado.
2. **P2 — `--paginate` emite un documento por página.** El `--jq` con `last` se
   aplicaba a cada página por separado, así que con más de 100 eventos salía una
   línea por página y el llamador tomaba la fecha de una y el id de otra.
   Corregido con `--slurp` y `add`.
3. **P1 — el caso B podía adelantar a un ciclo sano.** Descrito arriba.

**La raíz de (1) y (2) no está en el script, está en las pruebas**: el `gh`
simulado no modelaba `gh`. Devolvía datos a peticiones que en producción habrían
dado 404, e ignoraba la diferencia entre `--paginate` y `--slurp`. Con un
simulado permisivo, cualquier suposición sobre `gh` pasaba sin verificar.

El arreglo de fondo es ese: el simulado **falla ahora igual que `gh`** ante una
lectura convertida en POST, y reproduce las dos formas en que entrega páginas.
Verificado por mutación: con el simulado permisivo, la prueba que fija el
`-X GET` vuelve a pasar aunque se quite el `-X GET` —es decir, se vuelve vacua—,
que es exactamente lo que ocurría antes de esta revisión.

Una prueba propia también salió vacua y hubo que rehacerla: comprobaba que el
marcador de deduplicación saliera del último evento, pero no la **fecha**, que
es lo que de verdad se mezclaba entre páginas. Pasaba con la mutación puesta.

## Consecuencias

- El **caso B** del reconciliador (`ci-pending` con Quality en verde) pasa a
  repararse **sin supervisión**, y esa reparación despierta al revisor. No es
  trabajo nuevo —es lo que el flujo por eventos habría hecho de no perderse la
  transición— pero antes solo ocurría a petición y ahora puede ocurrir de
  madrugada. Para no adelantarse al productor del evento, solo repara si
  `ci-pending` lleva más de `STUCK_MINUTES` puesto; ver la revisión de abajo.
- **Lo que esto NO hace**, y conviene que no se lea de más:
  - no repara los estados atascados: avisa a una persona;
  - no detecta un run muerto, sino un estado que no avanza;
  - no cubre el hueco entre el atasco y la siguiente pasada: hasta seis horas;
  - no cubre una incidencia CERRADA que quedara mal, porque solo recorre las
    abiertas;
  - no notifica fuera de GitHub.
- Reversible por completo: quitar el `schedule:` devuelve el comportamiento
  anterior sin tocar nada más.
- Si en el futuro se quisiera que **repare** los estados atascados (tier 2), eso
  es otra decisión y otro ADR: exige distinguir «el run murió» de «el run sigue
  vivo», que desde fuera no es decidible sin consultar Actions.

## Alternativas descartadas y por qué

- **Cadencia horaria**: seis veces el coste para una latencia que aquí no vale
  esa diferencia. Un número, cambiable si la evidencia lo pide.
- **Avisar solo en el resumen del job**: es lo que ya había, y es la razón de que
  el problema llevara desde el 7 de agosto sin que nadie lo viera.
- **Que el reconciliador reintente la etiqueta por su cuenta** (quitar y volver a
  poner para redisparar el evento): reintentaría también sobre runs vivos, porque
  desde fuera no puede saber si lo están. Sustituiría un fallo silencioso por
  ejecuciones duplicadas.

## Segunda ronda de revisión: el aviso mandaba a hacer algo que no funciona

Codex revisó `c4e0a25` —el commit ya fusionado en `main`— y encontró un cuarto
defecto, esta vez en el propio aviso.

El texto decía: *«quitar `sirius:repairing` y volver a ponerla: eso vuelve a
disparar el evento»*. Y es verdad que dispara `issues: labeled`. Lo que no dice
es que `repair-sirius-work.yml` arranca con
`if: github.event.label.name == 'sirius:repair-requested'`, así que el job se
salta y la incidencia queda igual de atascada. Lo mismo con `implementing` y
`reviewing`: para los **tres** estados en curso, el aviso ofrecía como única
salida una acción que no hace nada.

Es la forma más incómoda de este defecto: la detección funcionaba, avisaba a
tiempo, y después daba una salida falsa. Quien la siguiera no habría visto ningún
error —solo que no pasa nada—.

**Arreglo:** `reactivation_label` traduce cada estado a la etiqueta que de verdad
arranca su workflow. La tabla es explícita; derivarla quitando el sufijo «ing»
funcionaría hoy por coincidencia de las tres palabras, y eso es reconstruir desde
fuera una correspondencia ajena, que es el patrón que ya costó dos hallazgos en
la primera ronda.

**RECON-STUCK-010** lee los `if:` reales de los tres workflows que hacen el
trabajo y exige que la etiqueta propuesta esté entre ellos, ejecutando la función
extraída del script. Cuatro mutaciones, todas con el resultado predicho.

Dos pruebas propias salieron defectuosas y se rehicieron:

- La primera versión de RECON-STUCK-010 miraba «etiquetas que disparan **algún**
  workflow». Ese conjunto incluye `sirius:implementing`, que dispara
  notificaciones, así que **pasaba con el defecto puesto**.
- RECON-STUCK-007 afirmaba que el reconciliador no inicia bloques comprobando que
  cierta cadena no apareciera en el archivo. Eso es una prueba de grafía: rompía
  porque el aviso *nombra* la etiqueta que debe aplicar el usuario, y a cambio no
  habría notado un `--add-label` escrito de otra forma.

### Nota de método, para que conste

**Este trabajo no llevó nota de arranque.** Salió directamente de un hallazgo de
revisión y me puse a corregir sin escribir antes la afirmación ni el criterio de
parada, que es lo que ADR-001 exige. No la escribo ahora a posteriori: un
criterio redactado después de ver los resultados no es un criterio, y fingir lo
contrario vacía de sentido la propia disciplina.

Lo que sí hay, y sostiene el cambio, es lo de siempre: el mecanismo verificado
contra los workflows reales antes de aceptar el hallazgo, pruebas que fallan al
revertir el arreglo, y las dos pruebas vacuas propias detectadas y corregidas
antes de subir nada.

## Tercera ronda: dos veces el mismo defecto, así que cambia el enfoque

Codex volvió sobre el arreglo anterior y encontró que **seguía sin funcionar**,
un nivel más abajo. Para `sirius:implementing`, aplicar solo
`sirius:implement-requested` dispara el workflow pero
`sirius_validate_activation.sh` lo **rechaza** por falta de `sirius:planned` —que
el paso «Consumir el evento» había retirado— y vuelve a quitar la etiqueta.

Verificado: `implement-sirius-work.yml` retira `implement-requested` **y**
`planned`; la puerta exige `planned` y sin ella rechaza. `reviewing` y
`repairing` no tienen ese problema: su consumo solo retira la disparadora.

Dos rondas con defectos de la misma familia —«el aviso manda a hacer algo que no
funciona»— son la señal de parar de parchear (ADR-001). **La raíz es la misma
que la de los otros tres hallazgos de esta PR**: el reconciliador reconstruía
desde fuera las condiciones de admisión de otro sistema. Añadir `planned` a la
tabla habría sido el tercer parche de la misma forma, y el cuarto habría llegado
con la siguiente precondición.

Dos cambios de enfoque, y hacen falta los dos:

1. **La regla se deriva de los workflows, no se escribe a mano.** Lo que hay que
   reponer es *exactamente lo que el paso de consumo retiró*, con la etiqueta
   disparadora en último lugar para que la puerta encuentre el resto ya puesto.
   **RECON-STUCK-010** lee ese paso del YAML real y compara; si un workflow
   empieza a consumir otra etiqueta, la prueba falla sin que nadie se acuerde.
2. **El aviso deja de presentarse como una receta completa.** Añade una tercera
   línea: si faltara alguna condición más, la puerta lo dirá en un comentario y
   retirará la etiqueta —no se queda en silencio—. **RECON-STUCK-011** comprueba
   que esa promesa es cierta contra la puerta real, no solo que esté escrita.

Seis mutaciones, todas con el resultado predicho: olvidar `planned`, volver a
proponer la etiqueta en curso, invertir el orden, cambiar lo que consume el
workflow sin tocar la tabla, dejar muda a la puerta, y quitar la salvedad.

Lo que esto sigue **sin** garantizar, dicho para que no se lea de más: que la
secuencia prescrita baste siempre. Garantiza que reponga lo que el consumo
retiró y que, si no basta, quien lo sepa lo diga. Prometer más sería repetir el
error tres veces.

## Cuarta ronda: la promesa era falsa, y el patrón es mío

El aviso decía que la puerta «no se queda en silencio». Codex demostró que sí
puede: `reject()` registraba el fallo de `sirius_comment_once` y **retiraba la
etiqueta igualmente**. La incidencia quedaba solo en `sirius:planned`, sin
comentario y sin ningún evento que la reviva — y encima **invisible para este
mismo reconciliador**, porque `planned` es un estado de reposo legítimo y no
está en `MACHINE_LABELS`.

Es la clase exacta de fallo que esta incidencia vino a eliminar, un callejón
mudo, reintroducida por la puerta que debía protegerla.

**Arreglo:** sin diagnóstico publicado no se retira la etiqueta. Conservándola
se pierde tiempo, no la incidencia: el estado queda como estaba y el próximo
intento vuelve a rechazar. No hay bucle, porque `issues: labeled` solo dispara
al aplicar la etiqueta.

### El patrón, que no está en el código

Tres veces en esta misma PR una prueba de **grafía** se hizo pasar por una de
**comportamiento**:

| Prueba | Qué afirmaba | Qué medía |
|---|---|---|
| RECON-STUCK-007 | «el reconciliador no inicia bloques» | que cierta cadena no apareciera en el archivo |
| RECON-STUCK-010 (1ª versión) | «la etiqueta propuesta arranca el trabajo» | que estuviera en un conjunto demasiado amplio |
| RECON-STUCK-011 (1ª versión) | «la puerta no se queda en silencio» | que dos cadenas existieran en la puerta |

Las tres pasaban con el defecto puesto. Y la tercera se escribió **justo
después** de corregir la primera, que era el mismo error.

Un `grep` puede fijar que un patrón concreto no reaparezca por inercia —para eso
sirve— pero no puede sostener una afirmación sobre lo que el sistema hace. Para
eso hay que ejecutarlo. La regla que sale de aquí, y que las tres pruebas
cumplen ya: **si la frase empieza por «el sistema hace X», la prueba tiene que
hacer que lo haga.**

`test_a_rejection_without_diagnosis_keeps_the_label` corre la puerta con la
publicación rota y comprueba que la etiqueta sobrevive. Cuatro mutaciones, todas
con el resultado predicho, incluida la que rompe el simulado para confirmar que
la prueba no pasa por vacuidad.

## Quinta ronda: se retira la promesa en vez de parchear el tercer camino

Codex encontró un camino **más** en el que la salvedad del aviso era falsa: en
`reviewing` y `repairing` una precondición inválida no pasa por `reject()` sino
por `sirius_transition`, que aplica el estado terminal y retira la etiqueta
**antes** de publicar; y los llamadores se tragan el error con `|| echo`.

Arreglar ese tercer camino habría sido el cuarto parche de la misma forma. **La
afirmación se retira.** El reconciliador sabe lo que el paso de consumo retiró
—eso lo lee del YAML— pero no las garantías de publicación de tres puertas
distintas, y prometerlas era hablar por ellas. Lo que sí puede decir sin mentir
es dónde consta siempre el motivo: el registro de Actions.

Es la misma lección que el resto de esta PR, aplicada a una frase en vez de a un
cálculo: **no afirmes por otro sistema.**

### Y la tercera versión de la misma prueba de grafía

RECON-STUCK-007 seguía siendo textual: solo detectaba una escritura si el nombre
de la función y la etiqueta caían en la **misma línea**. Pero el estilo del
propio repositorio parte estas llamadas en dos:

```bash
sirius_set_issue_labels "$GH_REPO" "$ISSUE_NUMBER" \
  "sirius:implementing" "sirius:implement-requested" "sirius:planned"
```

Una llamada así habría iniciado un bloque con la prueba en verde, y una etiqueta
pasada por variable también. Van **tres** versiones de esta aserción y las tres
medían texto.

Ahora ejecuta: siembra una incidencia por cada estado de `MACHINE_LABELS`, corre
el reconciliador y comprueba qué etiquetas quedaron escritas. Verificado por
mutación con una llamada partida en dos líneas —el caso exacto que la versión
anterior no veía—: falla.

Esa es la forma definitiva de la regla, y el motivo de que hicieran falta tres
intentos para llegar a ella: un `grep` no puede sostener una afirmación sobre lo
que un sistema hace, ni siquiera cuando parece que sí.

## Sexta ronda: la prueba copiaba una afirmación del contrato que ya era falsa

Codex encontró que RECON-STUCK-007 —cuarta versión— seguía sin sostener lo que
decía: miraba el **estado final** y solo prohibía `sirius:implement-requested`.
Un «retirar y volver a poner» deja el estado idéntico y sin embargo dispara
`issues: labeled`, que es arrancar trabajo. Y aplicar `review-requested` o
`repair-requested` desde cualquier otro caso también pasaba en verde.

Al verificarlo apareció la causa de por qué la prueba miraba una sola etiqueta:
**el §9.1 decía algo falso**. Su límite 1 afirmaba «no aplica
`sirius:implement-requested` ni ninguna otra etiqueta que arranque un bloque»,
pero el caso B aplica `sirius:review-requested`. La prueba no estaba mal por
descuido: copiaba fielmente una afirmación que ya estaba mal.

Corregido el texto para que diga lo que de verdad ocurre —nunca
`implement-requested`; la única disparadora que escribe es `review-requested`, y
solo desde `ci-pending`, bajo el límite 2— y las pruebas lo fijan **ejecutando**:

- El `gh` simulado registra **cada** adición de etiqueta, no el estado final.
- **RECON-STUCK-007**: desde un estado atascado no se escribe ninguna de las
  tres disparadoras.
- **RECON-STUCK-013**: desde `ci-pending` con Quality verde se escribe
  `review-requested` y ninguna otra.

Tres mutaciones, todas con el resultado predicho: reaplicar la etiqueta en curso,
aplicar otra disparadora distinta, y que el caso B deje de aplicar la suya.

### Cuatro versiones de la misma aserción

| Versión | Qué medía | Cómo se la saltaba el defecto |
|---|---|---|
| 1ª | que una cadena no estuviera en el archivo | el aviso nombra la etiqueta que aplica el usuario |
| 2ª | que no cayera en la misma línea | el repositorio parte esas llamadas en dos |
| 3ª | el estado final tras ejecutar | «retirar y volver a poner» no cambia el estado |
| 4ª | cada escritura, contra las tres disparadoras | — |

La lección no es «ejecuta en vez de leer», que ya estaba escrita en la ronda
anterior. Es que **una prueba no puede ser más correcta que la afirmación que
copia**: mientras el contrato dijo una cosa falsa, cada versión de la prueba
heredó el error aunque cambiara de técnica. Antes de medir hay que comprobar que
lo que se va a medir es cierto.

## Séptima ronda: auditoría adversarial en paralelo, ocho defectos más

Tras ocho hallazgos externos consecutivos, la revisión dejó de ser suficiente
como único filtro: cada ronda encontraba uno, se corregía, y aparecía otro. Se
montó una **auditoría adversarial de seis lentes independientes** sobre el
cambio —afirmaciones contra realidad, vacuidad de pruebas, corrección del shell,
semántica de `gh`, coherencia con la máquina de estados, y el aviso tal como lo
lee una persona— con cada hallazgo pasando por un refutador cuyo trabajo era
tumbarlo ejecutándolo.

Once hallazgos en bruto → **ocho defectos distintos**, todos confirmados
ejecutando. Dos de gravedad alta, y uno era una **regresión introducida en la
ronda anterior**.

| | Defecto | Por qué importaba |
|---|---|---|
| D1 | `mapfile < <(...)` descartaba el fallo del listado | un 503 apagaba las cuatro pasadas diarias **con aspecto de éxito**: resumen vacío, `rc=0`, idéntico a un repositorio sano |
| D2 | `planned` + `implement-requested` caía en CONTRADICCION | es el **único** estado en que `implement-requested` existe en producción sana; una activación muerta no recibía aviso nunca, y encima se la acusaba de incoherente en cada pasada |
| D3 | `2>/dev/null` sobre la llamada entera | un 403 por límite de tasa salía **idéntico** a «no hay evento»: la detección podía estar apagada del todo sin una sola señal |
| D4 | el caso B no miraba `draft` | `advance-…` se niega a mover una PR en borrador y `quality.yml` sí corre en ella: el reconciliador arrancaba 85 min de revisión sobre algo que una persona aparcó a propósito |
| D5 | `ci-pending` nunca recibía aviso | su motor es `on: workflow_run`, un evento de un solo uso: con Quality en rojo y ese run muerto, callejón cerrado — y la cabecera afirmaba que **todos** los estados de máquina reciben aviso |
| D6 | §9.1 citaba RECON-STUCK-007 para más de lo que cubre | una escritura insertada en el caso A pasaba **25/25** del fichero |
| D7 | RECON-STUCK-011 hacía `grep` sobre el guion | su aserción positiva quedaba satisfecha por un **comentario de shell** mientras el aviso publicado ya no contenía la frase |
| D8 | `printf` con seis `%s` y siete argumentos | `printf` reutiliza el formato: la última línea salía pegada al punto 2 —en Markdown, dentro del ítem— con diez líneas en blanco detrás |

Y dos defectos más aparecieron **al arreglar los anteriores**, los dos por la
misma causa que ya había producido tres: **un simulado más permisivo que la
herramienta real**. El `gh` simulado no aplicaba el `--jq` a `/pulls/`, así que
devolvía `draft` aunque el guion dejara de pedirlo —la prueba pasaba con el
defecto puesto— y aceptaba una siembra con `head` como cadena cuando la API
devuelve un objeto con `sha`. Corregido el simulado, la siembra irreal falló
sola.

**Once mutaciones**, todas con el resultado predicho antes de ejecutarlas.

### Lo que esta ronda enseña, y no es «revisar más»

Los ocho hallazgos externos anteriores salieron de un revisor que miraba **con
otra cabeza**. Estos ocho salieron de seis cabezas mirando **a la vez, con
lentes distintas y con la lista de patrones ya conocidos por delante**. La
diferencia no es cantidad de repasos: es que un solo revisor —humano, modelo o
yo— comparte sesgo consigo mismo entre rondas, y por eso las rondas encuentran
de una en una.

La regla operativa que sale: **cuando una pieza acumula dos rondas de hallazgos,
deja de revisarse en serie y se audita en paralelo con lentes explícitas**. Y la
lente que más rinde es siempre la misma: coger cada frase declarativa y
preguntar qué comprobación la sostiene.
