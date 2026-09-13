# ADR-184 — La prohibicion no es una peticion: el detector de sensibilidad exige que el marcador no vaya negado

- Estado: PROPUESTO
- Fecha: 2026-09-13
- Aprobación: [quién y cómo; en este repositorio, la fusión de la PR por el propietario]

> **Este ADR es también la nota de arranque de la rama** (ADR-001, skill
> `disciplina-evidencia`). Las secciones «Nota de arranque» y «Criterio de
> parada» se escribieron y se empujaron **antes** de tocar una línea de
> `src/`, y antes de medir nada: el commit que las trae no contiene ningún
> cambio de código.

## Contexto y problema

`_detectar_sensibilidad` (`src/sirius_engine/intent_interpreter.py`) decide si
una orden del propietario tiene que parar y pedir su decisión. Compara cuatro
tuplas de marcadores léxicos contra el texto normalizado de la orden. La
comparación —hoy `_marcador_presente`, una frontera de palabra sobre el texto
entero— responde a una sola pregunta: **¿aparece el marcador?** No a la que
importa: **¿la orden PIDE esa operación?**

Una frase que **prohíbe** la operación contiene exactamente el mismo marcador
que una que la pide. El detector no las distingue, así que el despachador
clasifica la orden como `operacion_destructiva_o_irreversible`, crea el trabajo
en `NEEDS_DECISION` y sale con código 3 sin despachar
(`dispatch_cli.main`, rama `CREAR_Y_ESCALAR`).

Reproducido el 12-09-2026. El run 34726666071 de `despachar-orden.yml` paró con
esa causa sobre una orden cuya única frase sensible era una salvaguarda. El
trabajo quedó anotado en el diario `estado-del-motor` como
`WI-20260912-235558` (commit `e51072e`), sin incidencia detrás. La última frase
de esa orden, literal del diario:

> «No borres ni reescribas ninguna entrada historica del registro: un defecto
> nunca **se borra**, y las cifras fechadas de ADR-174 son evidencia y no se
> tocan.»

El marcador que disparó la puerta es `borra`, dentro de «un defecto nunca se
borra» — una frase que dice justo lo contrario de pedirlo. Comprobado sobre el
árbol de `main` (673b2f4) con el texto literal del diario:

    (<CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE>,
     "el mensaje contiene 'borra': causa operacion_destructiva_o_irreversible")

La misma orden, con la salvaguarda reescrita en términos afirmativos y sin
cambiar su significado, pasó sin tocar el detector y creó la incidencia #597.

El defecto se protege a sí mismo de ser reportado: describirlo en lenguaje
natural obliga a nombrar sus marcadores, y eso vuelve a disparar la puerta. Por
eso la orden que pidió este trabajo (#601) está escrita con rodeos.

## Nota de arranque (ADR-001, antes del primer cambio de código)

1. **¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en la
   comparación: `_marcador_presente` recibe el marcador y el texto, y devuelve
   un booleano que **no puede** depender del contexto porque la función no
   mira más que la presencia. El arreglo va una capa por encima, en
   `_detectar_sensibilidad`, que sí tiene delante el texto normalizado entero y
   por tanto **puede observar la negación que precede al marcador**. Esa es la
   razón de que el arreglo funcione ahí y no dentro de la comparación: el sitio
   del arreglo ve lo que el sitio del fallo no puede ver.
2. **¿Qué NO va a garantizar esto?** No va a entender la frase. Sigue siendo el
   apaño léxico v0 que ADR-043 declara provisional a la espera del intérprete
   con modelo que pide arquitectura §11. La lista de lo que el criterio nuevo
   **no** detecta se escribe en «Lo que este criterio NO detecta», y se escribe
   entera aunque incomode.
3. **Criterio de parada, decidido ANTES de medir y de ver ningún resultado:**
   - Mido sobre las órdenes que guarda el diario `estado-del-motor` cuántas
     cambian de clasificación con el criterio nuevo, y **reviso a mano, una a
     una, TODAS las que cambien**.
   - **Si alguna de las que dejan de parar pedía de verdad la operación**, el
     criterio queda descartado entero: no se ajusta la ventana ni se parchea la
     lista de negadores. Se para y se escala al propietario con
     `BLOCKED_BY_DECISION`.
   - **Si el criterio nuevo no cambia la clasificación de `WI-20260912-235558`**
     —el caso reproducido—, el criterio no sirve para lo que se pide y se
     descarta.
   - Regla de las dos rondas: dos rondas seguidas con defectos de la misma
     familia → se para y se busca la raíz, no se sigue parcheando.
4. **¿Qué haría el fallo IMPOSIBLE en vez de improbable?** Un intérprete con
   modelo que entienda la oración; es el [M] de arquitectura §11 y está fuera
   del alcance de esta incidencia. Lo que sí se puede hacer imposible **en el
   nivel léxico** es que el texto que PROHÍBE y el que PIDE produzcan la misma
   clasificación: lo fija una prueba con el texto **literal** de
   `WI-20260912-235558` tomado del diario, no con una paráfrasis cómoda.

## Criterio de parada (escrito ANTES de decidir)

El del punto 3 de la nota de arranque, íntegro. Se publicó en este mismo
fichero, en el commit que abre la rama, antes de medir y antes de escribir
código.

## Medición (criterio declarado ANTES de contar)

Sobre `diario.jsonl` de la rama `estado-del-motor` (585 registros, traída con
`git fetch origin estado-del-motor`), comparando el criterio viejo —presencia
con frontera de palabra— contra el nuevo, orden por orden:

| Medida | Cifra |
|---|---|
| Órdenes distintas que guarda el diario | 82 |
| Clasificadas `SENSIBLE_O_MATERIAL` con el criterio VIEJO | 3 |
| Clasificadas `SENSIBLE_O_MATERIAL` con el criterio NUEVO | 1 |
| **Cambian de clasificación** | **2** |
| Paradas registradas (`work_item_created_needing_decision`) | 3 |
| De ellas, por `operacion_destructiva_o_irreversible` | 3 |

Las tres paradas que el diario guarda son `WI-20260903-030529`,
`WI-20260903-095428` y `WI-20260912-235558`, y las tres por esta causa. **Dos de
las tres eran falsos positivos**: el diario no registra ni una sola parada por
esta causa que fuera una petición real.

Las dos que cambian, revisadas a mano una a una como exigía el criterio de
parada, con su texto literal del diario:

- `WI-20260912-235558` — «…un defecto nunca **se borra**…». Prohibición.
- `WI-20260903-030529` — «…(dos o tres frases, sin reescribir ni **borrar** el
  bloque)…». Prohibición.

**Ninguna de las dos pedía la operación**, así que el criterio de parada no se
disparó y el trabajo siguió. La tercera, `WI-20260903-095428`, **sigue
parando**, y es el caso más instructivo: es la orden que denunciaba este mismo
defecto, y su marcador aparece NOMBRADO, no usado —«su lista de marcadores
contiene la palabra «borrar»»—, sin negación delante. Ver «Lo que este criterio
NO detecta».

## Decisión

`_detectar_sensibilidad` deja de preguntar **¿aparece el marcador?** y pregunta
**¿la orden lo PIDE?**. Una aparición cuenta solo si **no va negada**, y basta
**una** aparición sin negar —de cualquier marcador— para que la puerta pare.

El criterio mira la **negación gramatical local**, no la forma imperativa:

- La oración se corta por la puntuación: lo que hay al otro lado no gobierna al
  marcador.
- Dentro de su oración se miran las **cuatro palabras anteriores** al marcador,
  de atrás hacia delante.
- Si en esa ventana aparece un **negador** de una lista cerrada (`no`, `ni`,
  `nunca`, `jamas`, `sin`, `ningun…`, `prohibido…`, `prohibe`, `evita`,
  `impide`… ), esa aparición prohíbe en vez de pedir y no cuenta.
- La mirada se detiene antes en un **corte de oración** (`y`, `e`, `o`, `u`,
  `pero`, `sino`, `aunque`, `mas`, `embargo`, `solo`, `solamente`, `duda`,
  `olvides…`, `dudes…`, `dejes…`): si eso está entre el negador y el
  marcador, el negador gobierna otra cosa.
- `falta` corta **solo pegado a su `sin`** (`_CORTES_TRAS_SIN`). Como corte
  incondicional dejaba sin ver el `no` de «no hace falta borrar la tabla», que
  es una prohibición, y la puerta volvía a parar sobre ella: el corte de más
  NO es gratis, resucita el falso positivo que este ADR cierra (ronda 3 de
  #601). `duda` sí corta en cualquier posición, porque fuera de la locución es
  la forma verbal de «no duda en borrar», que también **pide** el marcador.
- Los verbos de doble negación (`_VERBOS_DE_DOBLE_NEGACION`: `olvides…`,
  `dudes…`, `dejes…`) además **anulan** al negador que quede entre ellos y el
  marcador: «no dejes ninguna fila **sin** borrar» pide borrarlas todas, y sin
  esa anulación la mirada se paraba en ese `sin` antes de llegar al corte
  `dejes` (ronda 3 de #601). Solo anulan si ellos mismos van precedidos de un
  negador: es la estructura «no + verbo + … + negador + marcador» y ninguna
  otra, para que «sin duda no hay que borrar» siga siendo una prohibición.

Las dos listas son **cerradas y están escritas**, y sus dos modos de fallo NO
son simétricos:

- lo que **falte** en la lista de negadores hace que la puerta **pare de más**:
  fail-closed, el mismo criterio que el propietario fijó en #324 (H-19);
- lo que **sobre** —una palabra que aparece delante del marcador sin negarlo—
  hace lo contrario: **calla una petición de verdad**. Eso es fail-OPEN, y por
  eso la lista de negadores no admite formas ambiguas. Los infinitivos `evitar`
  e `impedir` estuvieron en ella y se retiraron (ronda 2 de #601): en castellano
  encabezan la subordinada final «para evitar/impedir X, borra Y», donde la
  negación gobierna el propósito y el verbo principal **sí** se está pidiendo.
  En la ronda 3 salieron por el mismo motivo las formas de **subjuntivo**
  —`evites`, `eviten`, `impidas`, `impidan`—: son las que selecciona «para
  que», y «para que impidan que crezca borra los logs» es el MISMO giro final
  con otro sujeto. `impidan` se había añadido en la ronda 2 sin medirlo, junto
  a la frase —hoy corregida— de que «las formas personales no encabezan ese
  giro»: era falsa para el subjuntivo. Se quedan solo las formas que de verdad
  no lo encabezan: el imperativo y el presente de indicativo «evita borrar»,
  «impide que se borre». Por motivo análogo cortan `duda` y `falta` («sin duda
  borra», «sin falta borra»: ahí `sin` gobierna al sustantivo) y los verbos de
  doble negación `olvides`/`dudes`/`dejes` («no olvides borrar» **pide** borrar).

Mantener esa asimetría a la vista es lo que impide volver a escribir que el modo
de fallo del criterio es «siempre parar de más»: solo lo es por el lado de la
lista incompleta.

### Alcanza a las cuatro tuplas, y esa es la razón de ponerlo donde se pone

Las cuatro tuplas —destructiva, gasto, credenciales, privacidad— comparten un
único detector, así que el arreglo las cubre a las cuatro sin una línea extra.
No es un efecto colateral: **el defecto no vive en ninguna tupla, vive en la
comparación**, y arreglarlo solo para la tupla que lo destapó habría dejado las
otras tres esperando su turno con el mismo agujero. «No uses una clave real de
pago», «esto no toca ninguna credencial» y «sin publicar ningún dato personal»
son prohibiciones exactamente igual que «no borres nada», y las cuatro tienen
su pareja de prueba —prohibición que calla, petición que para— en
`tests/engine/test_intent_interpreter.py`.

### Los trabajos que quedan anotados sin incidencia

Cuando la puerta para, `dispatch_cli` crea el trabajo en `needs_decision` y sale
con 3 sin despachar. El trabajo queda en el diario **sin incidencia detrás**.

**Decisión: no se borra, no se cancela y no se despacha solo. Se hace visible.**

- No se borra: el diario es append-only con checksum por registro (ADR-026).
- No se cancela: cancelar es una decisión del propietario —es *exactamente* la
  decisión que la parada está pidiendo—, y que el comando la tomara por él
  vaciaría de sentido la parada.
- `needs_decision` **es** su situación real. El trabajo no estaba huérfano por
  estar en mal estado: estaba huérfano **por invisible**. El mensaje de la
  parada daba el `work_id` y la causa, y callaba dónde quedaba el trabajo y por
  dónde volver a él.

Así que el mensaje de la parada ahora lo dice: en qué estado queda, que no se
borra ni se cancela solo, y que la sesión `sirius-motor --diario <ruta>` lo
lista con `/trabajos` junto a todo lo demás que espera decisión. **La ruta va
en la instrucción, y es la efectiva**: `sirius-motor` sin argumentos resuelve
el diario que le toque a él —el de `SIRIUS_MOTOR_DIARIO`, o el de por defecto
(`cli.resolver_diario`)—, que no tiene por qué ser aquel en el que acaba de
quedar el trabajo. Lo fija
`test_una_parada_dice_donde_queda_el_trabajo_y_como_volver_a_el`, que además
comprueba que el trabajo está de verdad en el diario en ese estado: el mensaje
no promete un sitio vacío.

**Y solo lo dice cuando es verdad.** Esta rama se alcanza también en ENSAYO,
que es el modo POR DEFECTO (sin `--ejecutar`), y allí el almacén y el diario
del despachador son los de memoria: no se escribe nada y el trabajo muere con
el proceso. El texto durable prometía ahí, sin condición, un sitio vacío —el
fallo exacto del que este apartado dice cuidarse—, y encima el aviso «ENSAYO:
no se ha escrito nada en GitHub» vive **después** del `return 3` de esta rama,
así que quien paraba en ensayo ni siquiera sabía que lo era. Ahora el ensayo
dice que es un ensayo, que el trabajo NO queda anotado y que la orden se repita
con `--ejecutar` si se quiere que quede. El código de salida sigue siendo 3 en
los dos modos. Lo fija la gemela
`test_una_parada_en_ensayo_no_promete_un_sitio_donde_no_hay_nada`, que además
comprueba que el diario no llega a existir.

Y la otra mitad del problema la arregla el criterio nuevo: de las tres paradas
registradas, dos no habrían ocurrido. Los huérfanos se dejan de fabricar por
donde más se fabricaban.

## Lo que este criterio NO detecta

Escrito antes de que nadie lo descubra por su cuenta, y escrito entero:

1. **La prohibición pospuesta.** «Eliminar esto queda prohibido» sigue parando:
   solo se mira hacia atrás. Es deliberado —mirar hacia delante abre la puerta a
   silenciar «borra la cola, esto no es opcional»— y el error cae del lado de
   parar.
2. **La mención frente al uso.** Nombrar el marcador entre comillas para hablar
   de él —«su lista contiene la palabra «borrar»»— sigue parando, porque no hay
   negación delante. Es `WI-20260903-095428`, medido arriba, y es la razón de
   que **este encargo (#601) siga sin poder redactarse en lenguaje natural
   directo**: el criterio nuevo hace mucho menos ruidosa la puerta, pero **no
   cura que el defecto se proteja de ser reportado**. Distinguir mención de uso
   necesita entender la frase, y eso es el intérprete con modelo de
   arquitectura §11, no este apaño.
3. **La negación a más de cuatro palabras**, o al otro lado de un signo de
   puntuación, o de una conjunción coordinante.
4. **La negación implícita**, la ironía y el condicional: «si hiciera falta,
   borra la tabla» para, y debe parar.
5. **Cualquier marcador que no esté en las cuatro tuplas.** Esto no lo toca
   ADR-184 y sigue igual que antes: lo que no está en la lista no lo ve nadie.
6. **Entender la orden.** Sigue siendo el marcador de posición v0 que ADR-043
   declara provisional. Este ADR lo hace menos tonto, no inteligente.
7. **El negador que no gobierna al marcador, y este SÍ es un falso negativo.**
   Los seis puntos anteriores caen del lado de parar de más; este no. Un giro
   que lleva dentro una palabra de `_NEGADORES` sin negar al marcador **calla la
   puerta**: la orden sale `ORDEN_INEQUIVOCA` y `dispatch_cli` la despacha sola.
   Los giros medidos en las rondas 2 y 3 de #601 —«para evitar/impedir X, borra
   Y», **«para que eviten/impidan X, borra Y»** (el mismo giro final con sujeto
   distinto, que el castellano construye con «para que + subjuntivo»), «sin
   duda/sin falta borra Y», «no olvides borrar Y» y **«no dejes X sin borrar»**—
   están cubiertos con prueba, pero **la familia no está cerrada**: cerrar «qué
   palabra niega de verdad a cuál» es análisis sintáctico, y eso es el
   intérprete con modelo de arquitectura §11, no este apaño. Lo que sí queda
   fijado es la regla de mantenimiento: **antes de añadir un negador hay que
   comprobar que no encabeza un giro final o adverbial** —y el subjuntivo
   cuenta—, porque añadirlo a la ligera abre este agujero, no lo cierra.
8. **El corte de oración tampoco es gratis, y falla al revés.** Un corte de más
   no «solo hace parar»: hace que una PROHIBICIÓN vuelva a parar, que es el
   falso positivo que este ADR viene a cerrar. Pasó con `falta` en la ronda 2
   —«no hace falta borrar la tabla» paraba porque el corte tapaba el `no`— y se
   arregló en la ronda 3 estrechando el corte a su locución (`_CORTES_TRAS_SIN`).
   La regla de mantenimiento simétrica a la del punto 7: **antes de añadir un
   corte hay que comprobar que la palabra no aparece también dentro de una
   negación real**. La tabla de «Medición» no se rehízo por esto, y está
   comprobado que no hace falta: ninguno de los tres textos del diario
   atraviesa un corte —`WI-20260912-235558` se silencia por `nunca` y
   `WI-20260903-030529` por `ni`—, así que las cifras siguen siendo las suyas.

## Comprobación que la sostiene

- **Reproducción del fallo**, sobre `main` en 673b2f4 y con el texto literal de
  `WI-20260912-235558` leído del diario:
  `(<CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE>, "el mensaje contiene 'borra': …")`.
- **Las pruebas nuevas, vistas FALLAR antes del cambio**: con
  `src/sirius_engine/intent_interpreter.py` revertido,
  `uv run pytest tests/engine/test_intent_interpreter.py` da **6 failed, 54
  passed**; con el cambio, **61 passed**. La de `dispatch_cli` falla antes con
  `AssertionError: quien lee tiene que saber en qué estado quedó`. Las dos
  cifras son las del árbol de `1972d8a2`, el head de la ronda 1; la ronda 2
  añadió pruebas y las recuenta en su propia tabla, más abajo.
- **Seis mutaciones sembradas y vistas caer** (`uv run pytest
  tests/engine/test_intent_interpreter.py` tras cada una, sobre el árbol de
  `1972d8a2`):

  | Mutación | Resultado |
  |---|---|
  | sin mutar (control) | 61 passed |
  | M1 — sin cortes de oración | 2 failed |
  | M2 — ventana de 1 palabra en vez de 4 | 2 failed |
  | M3 — sin separador de oración | 2 failed |
  | M4 — se ignora la negación (el defecto original) | 6 failed |
  | M5 — se mira hacia delante en vez de hacia atrás | 6 failed |
  | M6 — decide la PRIMERA aparición en vez de cualquiera | 1 failed |

### Ronda 2: el negador que no gobierna, y la parada en ensayo

Cuatro mutaciones más, sembradas sobre el árbol de la ronda 2 y vistas caer
con `PYTHONDONTWRITEBYTECODE=1 uv run pytest <fichero> -q`:

| Mutación | Fichero de prueba | Resultado |
|---|---|---|
| sin mutar (control) | `test_intent_interpreter.py` | 69 passed |
| sin mutar (control) | `test_dispatch_cli.py` | 15 passed |
| M7 — `evitar` vuelve a `_NEGADORES` | `test_intent_interpreter.py` | 2 failed, 67 passed |
| M8 — se quitan los cortes `duda`, `falta` y `olvides` | `test_intent_interpreter.py` | 3 failed, 66 passed |
| M9 — la parada vuelve a dar el texto durable también en ensayo | `test_dispatch_cli.py` | 1 failed, 14 passed |
| M10 — la instrucción de recuperación pierde `--diario <ruta>` | `test_dispatch_cli.py` | 1 failed, 14 passed |

La primera línea de cada fallo:

- M7 — `AssertionError: assert <TipoIntencion.AMBIGUA: 'ambigua'> is
  <TipoIntencion.SENSIBLE_O_MATERIAL: 'sensible_o_material'>` sobre «para
  evitar duplicados elimina la tabla de origen».
- M8 — `AssertionError: assert <TipoIntencion.ORDEN_INEQUIVOCA:
  'orden_inequivoca'> is <TipoIntencion.SENSIBLE_O_MATERIAL:
  'sensible_o_material'>` sobre «implementa la limpieza sin falta borra la
  tabla de origen».
- M9 — `AssertionError: quien para en ensayo tiene que saber que es un ensayo`.
- M10 — `AssertionError: el paso indicado tiene que abrir ESTE diario, no el
  que resuelva por defecto`.

  **M6 sobrevivió en la primera pasada** y por eso está aquí: las pruebas
  fijaban «basta una aparición sin negar» en la prosa y no en ninguna
  aserción. Se añadió el caso que la distingue —el mismo marcador negado en una
  frase y pedido en la siguiente— y la mutación cayó. Sin la mutación, esa
  garantía habría quedado escrita y sin sostener.
- **Medición sobre el diario real**: la tabla de «Medición», reproducible
  releyendo `git show origin/estado-del-motor:diario.jsonl` y pasando cada
  `peticion_original` por los dos criterios.
- Las cuatro validaciones obligatorias, en verde, sobre el árbol de la rama:
  `pwsh -File scripts/check.ps1` sobre el árbol de `3ed94aa5` —el head de la
  ronda 3 con todo el código y todas las pruebas ya dentro— da **6426 passed,
  17 skipped, 2 xfailed** en 509.73 s y **código de salida 0**. La misma cadena
  sobre `4b71b0eb`, que llevaba ese mismo `src/` y ese mismo `tests/`, dio las
  mismas 6426 en 520.01 s. La **verificación de cierre** de la ronda volvió a
  encadenarla entera sobre el árbol de `6c978ae1`: **6426 passed, 17 skipped,
  2 xfailed** en 583.62 s y **código de salida 0**. Lo único que cambia después
  de esa medición es la prosa de este ADR. Las cifras de las rondas anteriores quedan ancladas a su
  propio árbol, arriba.

### Ronda 3: el subjuntivo, el corte incondicional, la doble negación y la ruta

Cuatro mutaciones más, sembradas sobre el árbol de la rama en la ronda 3 y
vistas caer con `PYTHONDONTWRITEBYTECODE=1 uv run pytest <fichero> -q`. Cada
una se sembró sobre el árbol que ya llevaba las correcciones anteriores, y por
eso su control crece:

| Mutación | Fichero de prueba | Resultado |
|---|---|---|
| sin mutar (control, árbol final) | `test_intent_interpreter.py` | 75 passed |
| sin mutar (control, árbol final) | `test_dispatch_cli.py` | 16 passed |
| M11 — `_va_negado` vuelve a `return True` sin consultar `_negacion_anulada` | `test_intent_interpreter.py` | 2 failed, 69 passed |
| M12 — `falta` vuelve a ser corte incondicional (`_CORTES_TRAS_SIN` vacío) | `test_intent_interpreter.py` | 2 failed, 71 passed |
| M13 — `evites`, `eviten`, `impidas` e `impidan` vuelven a `_NEGADORES` | `test_intent_interpreter.py` | 2 failed, 73 passed |
| M14 — la ruta del diario vuelve a salir sin `shlex.quote` | `test_dispatch_cli.py` | 1 failed, 15 passed |

La primera línea de cada fallo:

- M11 — `AssertionError: assert <TipoIntencion.ORDEN_INEQUIVOCA:
  'orden_inequivoca'> is <TipoIntencion.SENSIBLE_O_MATERIAL:
  'sensible_o_material'>` sobre «implementa esto: no dejes ninguna fila sin
  borrar».
- M12 — `assert <CausaEscalado.OPERACION_DESTRUCTIVA_O_IRREVERSIBLE:
  'operacion_destructiva_o_irreversible'> is None` sobre «implementa esto: no
  hace falta borrar ninguna fila».
- M13 — `AssertionError: assert <TipoIntencion.ORDEN_INEQUIVOCA:
  'orden_inequivoca'> is <TipoIntencion.SENSIBLE_O_MATERIAL:
  'sensible_o_material'>` sobre «implementa el purgador: para que impidan que
  crezca borra los logs».
- M14 — `AssertionError: la ruta tiene que llegar entera como valor de
  --diario, no partida en dos`.

Las cuatro se **resembraron una a una sobre el árbol final** —el head
`6c978ae1`, que ya lleva todas las correcciones y todas las pruebas de la
ronda— en la verificación independiente que la cierra, para que ninguna fila
dependa de un árbol intermedio. Los fallos son los mismos, con la misma primera
línea; lo que cambia es el control, que ahí ya es el completo:

| Mutación resembrada sobre `6c978ae1` | Fichero de prueba | Resultado |
|---|---|---|
| sin mutar (control) | `test_intent_interpreter.py` | 75 passed |
| sin mutar (control) | `test_dispatch_cli.py` | 16 passed |
| M11 | `test_intent_interpreter.py` | 2 failed, 73 passed |
| M12 | `test_intent_interpreter.py` | 2 failed, 73 passed |
| M13 | `test_intent_interpreter.py` | 2 failed, 73 passed |
| M14 | `test_dispatch_cli.py` | 1 failed, 15 passed |

M12 pide sus **dos** mitades a la vez —`falta` de vuelta en
`_CORTES_DE_ORACION` **y** `_CORTES_TRAS_SIN` vacío—, y al resembrarla se vio
por qué: `_va_negado` consulta `_CORTES_TRAS_SIN` **antes** que
`_CORTES_DE_ORACION`, así que una palabra que esté en las dos listas nunca
llega a cortar de forma incondicional. Vaciar solo `_CORTES_TRAS_SIN` no
reproduce el defecto de CODEX-003: quita también el corte de «sin falta borra»
y lo que cae es esa otra prueba (1 failed, 74 passed).

### Un aviso sobre el método, porque costó una medición falsa

Durante el ciclo de mutaciones, restaurar el fichero original con `cp` dejó al
código fuente y a su `.pyc` **dentro del mismo segundo** de `mtime`. Python
valida la caché por `mtime` en segundos, así que la suite siguió ejecutando el
bytecode de la última mutación y dio ocho fallos sobre un árbol correcto. La
medición se repitió entera con `PYTHONDONTWRITEBYTECODE=1` y las cifras de
arriba son las de esa segunda pasada. Quien siembre mutaciones en este
repositorio con ciclos de menos de un segundo, que lo haga con esa variable
puesta: si no, no está midiendo lo que cree.

## Opciones consideradas

1. **Exigir forma imperativa** al marcador. Descartada: la mitad de los
   marcadores son infinitivos (`borrar`, `eliminar`) y aparecen en peticiones
   perfectamente reales —«hay que eliminar la tabla»—, así que exigir
   imperativo habría dejado pasar órdenes destructivas de verdad. Fail-open en
   una puerta fail-closed: exactamente el fallo del que este repositorio ya
   tiene una lección (H-19).
2. **Negación gramatical local.** La elegida. Solo calla cuando hay evidencia
   POSITIVA de negación, así que todo lo que no entiende lo sigue parando.
3. **Análisis sintáctico de verdad** (una dependencia de PLN). Descartada: mete
   una dependencia nueva en el módulo que ADR-043 declara explícitamente
   provisional, para una precisión que el intérprete con modelo va a sustituir
   entera.
4. **Quitar los marcadores conflictivos de la tupla.** Descartada sin discutir:
   es debilitar la puerta, que es lo que la incidencia prohíbe.

## Consecuencias

- La puerta avisa menos y sigue siendo fail-closed: el silencio exige evidencia
  positiva de negación, y su ausencia siempre se resuelve parando.
- Las cuatro causas léxicas cambian de comportamiento a la vez. Quien lea el
  campo `motivo_sensibilidad` verá ahora «el mensaje **pide** 'borra'» donde
  antes leía «contiene»: la frase dice lo que la comprobación comprueba.
- Una orden que prohíbe algo en una frase y lo pide en otra sigue parando.
- Las dos listas —negadores y cortes— son ahora superficie que mantener. Están
  cerradas, escritas y probadas. Su modo de fallo por **omisión** es parar de
  más; el de **exceso** es callar una petición real (punto 7 de «Lo que este
  criterio NO detecta»), así que ampliar `_NEGADORES` no es una operación
  inocua y hay que medirla como tal. Los **cortes** tienen su propio modo de
  fallo, y es el contrario del que sugiere el comentario del código: un corte
  de más hace parar, sí, pero parar **sobre una prohibición**, que es el
  defecto que este ADR cierra (punto 8). Ninguna de las dos listas se amplía
  sin medir.
- El encargo #601 sigue sin poder escribirse en lenguaje natural directo (punto
  2 de «Lo que este criterio NO detecta»). Este ADR no cierra eso y no finge
  cerrarlo.

## Alternativas descartadas y por qué

Las de «Opciones consideradas», 1, 3 y 4. La 4 merece una línea aparte: era la
más barata y la única que la incidencia prohibía por escrito. Está anotada
justamente para que nadie la vuelva a proponer como simplificación.

## La lección

- familia: `medir-lo-que-se-tiene-en-vez-de-lo-que-hay`
- sin esto se repetiría: poner una guarda a responder la pregunta que sabe
  contestar barata —«¿aparece la palabra?»— en lugar de la que tiene que
  contestar —«¿la orden lo pide?»—, y no notarlo porque el sustituto acierta
  casi siempre: aquí acertó en 1 de 3 paradas reales y paró sobre las
  salvaguardas que prohibían justo la operación.
- lo hace cumplir: `tests/engine/test_intent_interpreter.py`
