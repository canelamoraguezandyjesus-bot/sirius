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
