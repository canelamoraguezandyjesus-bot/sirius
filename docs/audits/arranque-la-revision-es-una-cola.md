# Nota de arranque — la revisión es una cola

Rama `mejora/la-revision-es-una-cola`, 14-09-2026. Publicada **antes del primer
commit de código**, como exige ADR-001. Idea y decisión del propietario, esa
misma madrugada, con estas palabras:

> «Puedes mandar quince trabajos seguidos, pero que cada uno tenga su cola. Cada
> trabajo puede llegar hasta implementación, pero que solo pase a revisión cuando
> esté actualizado con main. Si se están haciendo tres trabajos, primero tendrá
> que hacerse uno, luego otro, luego otro.»

Y la corrección que la motiva, suya también: **dar permiso de fusionar no arregla
nada.** Con tres trabajos vivos `main` sale en rojo igual, porque el problema no
está en quién pulsa el botón.

## 1. ¿Dónde vive el fallo y dónde va el arreglo?

El fallo vive **entre dos ramas**, no dentro de ninguna. Cada PR se valida contra
el `main` que tenía cuando corrió Quality; si otra PR se fusiona en medio, la
combinación que de verdad aterriza en `main` **no la ha probado nadie**. Ninguna
de las dos ramas puede observarlo desde dentro: cada una está verde y tiene
razón.

Por eso el arreglo **no puede vivir en la rama**: tiene que vivir en la puerta que
decide cuándo una rama entra a revisión, que es lo único que ve a las dos. Va en
el encaminamiento del ciclo, junto a las puertas que ya existen.

*¿Puede el sitio del arreglo observar el fallo que arregla?* Sí: la puerta compara
la base de la rama con el `main` del momento, y las dos cosas las tiene delante.

## 2. ¿Qué NO va a garantizar esto?

- **No serializa la implementación.** Quince trabajos siguen implementando a la
  vez; lo que se pone en fila es de revisión en adelante. Si la cola acabara
  frenando la implementación, estaría resolviendo otro problema.
- **No arregla las colisiones de identificador** (el `H-N` escrito a mano). Las
  hace visibles antes —en la rama, donde son baratas— pero la colisión sigue
  siendo posible. Eso lo cierra otra decisión ya tomada, y es trabajo aparte.
- **No promete que `main` no pueda ponerse en rojo nunca.** Promete que la
  combinación que aterriza es la que se probó. Un fallo que solo aparece al
  ejecutar en el runner, o algo que entre por fuera del ciclo, se le escapa.
- **No decide por el propietario.** Fusionar sigue siendo gesto suyo (contrato §8).

## 3. Criterio de parada, decidido ANTES de mirar ningún resultado

La medida está tomada y escrita abajo; el criterio se fijó antes de contarla.

- **Si la medida dijera que esto no ha pasado nunca**, se dice con esas palabras y
  se decide igualmente: una puerta que depende de que nadie se despiste es la
  familia que este repositorio lleva cerrando desde ADR-174. Pero entonces la
  forma tiene que ser la más barata que funcione, no la más completa.
- **La cola no vale si puede quedarse pillada.** Si existe cualquier estado en el
  que ninguna rama pueda entrar y haga falta que alguien la desatasque a mano, el
  diseño está mal y se tira. Esto es lo que descarta un cerrojo.
- **La cola no vale si deja a una rama esperando para siempre.** El orden lo
  decidió el propietario: FIFO, la que lleve más tiempo esperando.
- **No debilita nada de lo que ya hay.** Que solo se revise un head con Quality en
  verde sigue en pie: es del contrato. Las cinco causas de la puerta de
  sensibilidad (ADR-184, ADR-188) siguen exactamente igual y sus pruebas pasan sin
  retocarse.
- Cada regla nueva trae **una mutación sembrada y vista caer**.

## 4. ¿Qué haría el fallo imposible en vez de improbable?

**Que la condición se derive en vez de recordarse.** «Mi base es el `main` de
ahora» es una pregunta que se calcula con los dos datos delante, no un turno que
alguien coge y tiene que acordarse de soltar. Un cerrojo se queda pillado cuando
el proceso que lo tenía muere —y aquí los procesos mueren: un runner se cae, una
sesión se corta—; una condición derivada no puede quedarse pillada porque no
guarda nada.

Es la misma forma que ADR-174, ADR-179 y ADR-182 aplicaron a sus inventarios, y
es la razón de que este diseño sea una condición y no una cola con tickets.

**Lo que la haría imposible del todo** sería que el ciclo no pudiera siquiera
*intentar* revisar una rama desactualizada: que la petición de revisión no exista
como etiqueta hasta que la condición se cumpla. Eso es más caro y toca más
piezas; queda declarado aquí y se decide en el ADR con la medida delante.

## La medida (criterio declarado antes de contar)

Una fusión está **probada contra su `main` real** si el commit de `main`
inmediatamente anterior a ella es ancestro del head de su PR. Si no lo es, la
combinación que aterrizó no la probó ningún run de Quality.

Sobre las **14 últimas fusiones** de `origin/main` (12-09 16:28 → 14-09 02:20):

| | |
|---|---|
| Fusiones comprobadas | **14** |
| Sin probar contra su `main` real | **1** (#611, ADR-187) |

Esa única es exactamente la que dejó `main` en rojo con dos `H-39`: entró **13
minutos** después de #602 y ninguna de las dos vio a la otra.

**La segunda mitad del dato, que no hay que callar:** las otras 13 salen «sí»
porque se pagó una reconciliación manual por cada una —traer `main` a la rama
antes de fusionar—. Ese coste es el que mide la incidencia #608. Así que la cola
no evita un sangrado constante: **evita un suceso raro y caro, y automatiza el
trabajo manual que hoy evita los demás**. Decidir con la primera cifra sola sería
decidir sobre la mitad del hecho.

## Qué hace posible esto hoy y no la semana pasada

**ADR-187**, fusionado el 13-09: una revisión sobrevive a ponerse al día con
`main` si el trabajo propio de la rama no cambia. Antes, actualizar una rama
costaba una ronda de revisión entera, así que una cola que obliga a actualizarse
habría sido carísima —habría cambiado un coste por otro—. Con esa pieza dentro,
actualizarse es gratis y la cola sale a cuenta. Sin ella, este trabajo no debería
hacerse.
