# ADR-173 — El cierre de la incidencia es un desenlace, y el reflector mira todas las clases que el despachador despacha

- Estado: PROPUESTO
- Fecha: 2026-09-12
- Aprobación: la fusión de la PR por el propietario

## Nota de arranque (escrita ANTES de tocar una línea de código)

### El fallo, medido antes de escribir esta nota

`DESENLACES.md` de la rama `estado-del-motor` (commit `9c573a8`, 451 sucesos)
cuenta **21 encargos en `active`**. El más nuevo es del 31-08-2026; el más
viejo, del 25-08. Doce días después siguen ahí, y la pasada del reflector de
esta madrugada —[run 34671426587](https://github.com/canelamoraguezandyjesus-bot/sirius/actions/runs/34671426587),
12-09-2026 03:50 UTC— imprimió exactamente una línea: `Pasos aplicados en
total: 0.` Ni un paso, ni una divergencia, ni un aviso. Silencio.

**Las 21 incidencias están CERRADAS en GitHub.** No una parte: las 21. Medido
listando las incidencias abiertas del repositorio (18 en total: #582, #581,
#506, #503, #341, #267, #134, #127, #126, #25, #15, #14, #13, #12, #11, #10,
#9, #8) y comprobando que ninguna de las 21 está en esa lista.

| Encargo | Clase | Estado del motor | Incidencia | Etiquetas vigentes |
|---|---|---|---|---|
| WI-20260831-163257 | documentacion | active / preparar | #493 | `sirius:completed` |
| WI-20260831-131457 | investigacion | active / preparar | #483 | `sirius:completed` |
| WI-20260831-130914 | auditoria | active / preparar | #482 | `auditoria:solicitada` |
| WI-20260831-130547 | investigacion | active / preparar | #481 | `sirius:failed-safely` |
| WI-20260831-104900 | documentacion | active / preparar | #478 | `sirius:completed` |
| WI-20260830-170933 | documentacion | active / preparar | #459 | `sirius:blocked-decision` |
| WI-20260829-190812 | documentacion | active / preparar | #439 | `sirius:completed` |
| WI-20260829-134753 | documentacion | active / preparar | #435 | `sirius:blocked-decision` |
| WI-20260829-123248 | documentacion | active / preparar | #429 | `sirius:completed` |
| WI-20260829-020954 | documentacion | active / preparar | #419 | `sirius:completed` |
| WI-20260829-012209 | documentacion | active / preparar | #415 | `sirius:completed` |
| WI-20260828-223739 | documentacion | active / preparar | #412 | `sirius:completed` |
| WI-20260828-205339 | documentacion | active / preparar | #409 | `sirius:completed` |
| WI-20260828-122242 | investigacion | active / preparar | #392 | `sirius:failed-safely` + `sirius:completed` |
| WI-20260828-112416 | investigacion | active / preparar | #389 | `sirius:ready-for-merge` |
| WI-20260828-054330 | investigacion | active / preparar | #386 | `sirius:completed` |
| WI-20260831-154100 | programacion | active / comprobar | #489 | `sirius:ci-pending` |
| WI-20260831-141905 | programacion | active / comprobar | #485 | `sirius:ci-pending` |
| WI-20260829-120253 | programacion | active / entregar | #424 | `sirius:ready-for-merge` |
| WI-20260825-210756 | programacion | active / preparar | #349 | ninguna |
| WI-20260825-144242 | programacion | active / preparar | #333 | ninguna |

### Las DOS causas, separadas y medidas

**Causa A — el reflector no mira las clases que el despachador sí despacha.**
`reflect_cli.py:141` descarta todo encargo cuya clase no tenga autoridad
`INCIDENCIA` en la tabla de ADR-041 (`domain/authority.py:60-67`:
`PROGRAMACION` y `AUDITORIA` sí, `DOCUMENTACION` e `INVESTIGACION` no). Pero
`TABLA_ACTIVACION` del despachador (`dispatcher.py:105-128`) sí las despacha:
la fila `DOCUMENTACION` la autorizó **ADR-088** y la fila `INVESTIGACION`
**ADR-099**, las dos con el mismo criterio escrito en el propio código —
«mismo ciclo que `programacion`, sin etiquetas de activación nuevas». Una
tabla de agosto-ADR-041 sigue cerrando una puerta que ADR-088 y ADR-099
abrieron después.

Medido sobre el diario: de los 74 encargos despachados a GitHub, **15 son de
clase `documentacion` (10) o `investigacion` (5)**, despachados entre el
28-08 y el 31-08-2026. **Los 15 siguen `active`. Quince de quince, sin una
sola excepción.** Ninguno alcanzó jamás un estado terminal, y ninguno podía:
el reflector no los mira, y nadie más vuelve a tocar el almacén tras el
despacho (lo dice el propio encabezado de `reflect.py:5-10`).

**Causa B — el reflector nunca mira si la incidencia está cerrada.**
`MirroredWorkItem` **ya trae el dato**: el campo `cerrada: bool`
(`domain/mirror.py:249`), que `mirror_projection.py:926` calcula de
`estado_gh == "closed"`. Y no lo lee nadie:

```
$ grep -rn "cerrada" src/sirius_engine/reflect.py   → sin coincidencias
$ grep -rln "\.cerrada\b" src/ scripts/             → sin coincidencias
```

Es la séptima vez que aparece en este repositorio una pieza correcta a la que
no llama nadie —el aviso que `AGENTS.md` lleva escrito desde el 25-08—. Sin
ese dato, los 6 encargos que el reflector **sí** mira se quedan igual de
muertos, cada uno por su rama: `sirius:ci-pending` y `sirius:ready-for-merge`
proyectan el mismo `(ACTIVE, fase)` en el que el encargo ya está, así que la
regla 5 (idempotencia) devuelve el plan vacío; `auditoria:solicitada` y la
ausencia de etiquetas no están en el mapa, así que la regla 2 devuelve el plan
vacío **y sin motivo, a propósito**. Las cuatro salidas son silenciosas, y por
eso el run no imprimió nada.

### 1. ¿Dónde vive el fallo y dónde va el arreglo? ¿Puede el sitio del arreglo OBSERVAR el fallo?

El fallo vive en dos sitios y el arreglo va a los dos mismos:

- La puerta de clase, en `reflect_cli.py:141`. Pasa a derivarse de
  `TABLA_ACTIVACION` —la tabla que decide qué se despacha— en vez de la de
  autoridad. No es una segunda lista que mantener: se deriva, igual que
  `_CLASES_CONMUTABLES` se deriva de `_TABLA_AUTORIDAD`.
- El cálculo del plan, en `reflect.py`. Gana una regla 7 que lee
  `espejo.cerrada`.

**Sí puede observar el fallo**, y esa es la parte importante: el dato que
falta no hay que ir a buscarlo a ninguna parte nueva. `espejo.cerrada` ya
viaja hasta la puerta misma del cálculo en cada pasada; el arreglo consiste
en dejar de tirarlo. No hay lectura nueva de GitHub, ni un proceso que deba
informar de su propia muerte.

### 2. ¿Qué NO va a garantizar esto?

- **No inventa una entrega.** Un encargo cuya incidencia se cerró sin que las
  etiquetas proyecten `DELIVERED` no pasa a `delivered`: pasa a `cancelled`.
  El motor no puede afirmar una fusión que nunca observó.
- **No toca las etiquetas contradictorias.** #392 lleva `sirius:failed-safely`
  y `sirius:completed` a la vez; la regla 1 gana y seguirá dando divergencia
  cada pasada, ahora impresa en el log. Se queda `active` a propósito: es el
  único de los 21 que un humano tiene que mirar.
- **No arregla el hueco de origen.** Que el despachador despache y nadie
  vuelva a tocar el almacén salvo el reflector sigue igual; esto cierra el
  desenlace, no adelanta el ciclo.
- **No decide nada sobre la tabla de autoridad de ADR-041.** No se toca. Lo
  que cambia es de qué tabla lee el reflector para saber a quién mirar.
- **No promete que no vuelvan a aparecer encargos varados** por una causa
  distinta a estas dos.

### 3. Criterio de parada (decidido ANTES de ver ningún resultado)

- **(a)** Si tras el cambio la pasada del reflector deja **0 encargos
  `active` cuya incidencia esté cerrada**, salvo los de etiquetas
  contradictorias, se entrega.
- **(b)** Si para cerrar un encargo hiciera falta un puerto del almacén que
  hoy no existe, o una transición que el dominio no admita, **se para**: sería
  inventar vocabulario, que es exactamente lo que la regla 4 del reflector
  prohíbe. Se registra qué falta y se le lleva la decisión al propietario.
- **(c)** Si al derivar la puerta de clase de `TABLA_ACTIVACION` alguna prueba
  existente cambia de resultado, **se para y se mira la raíz**: sería señal de
  que la puerta de autoridad sostenía algo que esta nota no ha visto.
- **(d)** Ninguna prueba nueva se da por buena sin haberla visto fallar contra
  una versión rota a propósito (ADR-001 §3).

### 4. ¿Qué haría el fallo IMPOSIBLE en vez de improbable?

Las dos causas comparten una forma: **el motor calla cuando no sabe qué
hacer**. La regla 2 devuelve plan vacío «sin motivo, es el estado normal de
una incidencia recién despachada», y la puerta de clase descarta sin
imprimir. Las dos suposiciones son ciertas el primer día y falsas para
siempre a partir del segundo.

Lo que lo haría imposible, y entra en este cambio: **una prueba que recorra
el diario real y falle si algún encargo lleva más de N días en un estado no
terminal con la incidencia cerrada** no se puede escribir aquí —el diario
vive en otra rama y la prueba miraría el reloj, que es justo lo que
`test_memoria.py` prohíbe—. Lo que sí entra, y es lo más fuerte que este
cambio admite: el reflector **deja de tener salidas silenciosas**. Toda rama
que decida no tocar un encargo imprime por qué. Un encargo varado deja de ser
invisible aunque la regla que lo vara sea una que hoy no conocemos.

## Contexto y problema

El motor despacha por la vía GitHub y desde ahí no vuelve a tocar su propio
almacén: lo dice el encabezado de `reflect.py` desde que se escribió. El
reflector (C1, ADR-147) es la costura que faltaba, y funciona —46 encargos
entregados lo demuestran—, pero tiene dos huecos por los que un encargo se
cae y no vuelve a salir nunca. Los dos estaban a la vista y ninguno hacía
ruido, que es exactamente por lo que duraron tres semanas.

## Opciones consideradas

1. **Limpiar el diario a mano.** Escribir los sucesos que faltan en
   `estado-del-motor` y seguir. Descartada: no es una corrección, es tapar la
   medida. Mañana hay otros veintiuno.
2. **Que el reflector mire el cierre y la tabla de despacho** (la elegida).
3. **Caducar por tiempo**: cerrar todo encargo que lleve N días sin moverse.
   Descartada: el tiempo no es el hecho. Un encargo puede llevar un mes
   legítimamente parado esperando una decisión del propietario con su
   incidencia abierta, y otro estar muerto a las dos horas. El hecho es el
   cierre de la incidencia, no el calendario.
4. **Enmendar la tabla de autoridad de ADR-041** para que `DOCUMENTACION` e
   `INVESTIGACION` pasen a autoridad `INCIDENCIA`. Descartada: es una
   decisión de contrato mucho más ancha que este defecto —la autoridad
   gobierna quién manda sobre el estado, no solo a quién mira el reflector—, y
   no hace falta para cerrar este hueco.

## Decisión

**Uno. La puerta de clase del reflector se deriva de `TABLA_ACTIVACION`, la
tabla que decide qué se despacha.** Leía la tabla de autoridad de ADR-041, que
es de agosto y anterior a ADR-088 (`documentacion`) y ADR-099
(`investigacion`), las dos decisiones que metieron esas clases en el ciclo de
GitHub «con el mismo ciclo y las mismas etiquetas que `programacion`». La
misma tabla que abre la puerta de ida se lee ahora también a la vuelta: no es
una segunda lista que mantener. La tabla de autoridad **no se toca**.

**Dos. Regla 7: una incidencia CERRADA no puede producir ningún desenlace
más.** El cierre no compite con las etiquetas; llega después. Primero se
aplica el plan que las etiquetas dictan —si dicen `sirius:completed`, el
encargo se entrega y aquí no queda nada—, y solo si tras ese plan el
`WorkItem` sigue en un estado no terminal, el cierre lo termina como
`CANCELLED` por las transiciones que el dominio ya admitía. Ni un puerto
nuevo, ni una arista nueva: `escalate` + `resolve_decision(continuar=False)`
desde `ACTIVE`, `resolve_decision(continuar=False)` desde `NEEDS_DECISION`,
`cancel` desde `FAILED_SAFELY` y desde `PLANNED`. Desde `WAITING` no hay ruta
legal, y ahí el reflector **no inventa una**: lo dice y no toca nada.

**Tres. Ninguna rama del reflector se va en silencio.** Las cuatro salidas sin
plan —idempotencia, etiqueta no reconocida, ninguna etiqueta, divergencia—
dejaban al encargo igual y no imprimían nada. Ahora cada pasada dice, de cada
encargo, dónde está el motor, si su incidencia está abierta o cerrada y qué
proyectan sus etiquetas. Eso es lo que convierte «no pasa nada» en «esto lleva
doce días sin moverse».

## Comprobación que la sostiene

**La simulación de la próxima pasada sobre el diario real.** Con el diario de
`estado-del-motor` (451 sucesos) copiado a un temporal, el espejo alimentado
con las etiquetas y el estado de cierre REALES de las 28 incidencias
implicadas, y el comando entero corriendo —`reflect_cli.main` con los
adaptadores durables—, el recuento de `DESENLACES.md` pasa de esto a esto:

| Estado | Hoy | Tras el cambio |
|---|---|---|
| active | 21 | **1** |
| delivered | 46 | 56 |
| cancelled | 0 | 17 |
| failed_safely | 5 | 0 |
| needs_decision | 4 | 2 |

El único encargo que sigue `active` es **WI-20260828-122242 / #392**, el de
las etiquetas contradictorias, que es exactamente el que la regla 7 se niega a
tocar y el único que un humano tiene que mirar. Los 10 que pasan a
`delivered` son los de `documentacion` e `investigacion` que llevaban
`sirius:completed` desde agosto y a los que la puerta de clase no dejaba
llegar. Criterio de parada (a): **cumplido**.

Dos límites de esa simulación, dichos: los hilos de comentarios van vacíos, así
que no hay historial acreditado ni permisos de reanudación —la pasada real
puede hacer MÁS, nunca menos— y los diagnósticos de parada reales no aparecen.
Y no se escribió nada en `estado-del-motor`: la copia es de un directorio
temporal.

**Las cinco mutaciones, vistas caer** (ADR-001 §3, criterio de parada (d)).
Cada una se sembró en el código de producción, se corrieron las 85 pruebas de
`test_reflect.py` y `test_reflect_cli.py`, y se restauró:

| Mutación | Pruebas que caen |
|---|---|
| La regla 7 no hace nada (`if True: return plan`) | las 4 de cancelación + la de «no inventa» |
| El cierre no respeta que el plan ya termine (sin la guardia `TERMINAL_STATES`) | 7, entre ellas la entrega con SHA de fusión y las 4 clases |
| El cierre se aplica también sobre un resultado con divergencia | las 2 de «no pisa» + la del permiso del propietario |
| El cierre inventa una salida desde `WAITING` | la de «no inventa una transición» |
| La puerta de clase vuelve a la tabla de autoridad de ADR-041 | `documentacion` e `investigacion` |

Con el código restaurado, 85 en verde.

**Criterio de parada (c), cumplido con un matiz que hay que decir.** Revertir
la puerta de clase solo tumba las dos pruebas nuevas: ninguna prueba existente
dependía de la tabla de autoridad. Lo que sí cambió de resultado fue
`test_espejo_sin_etiqueta_de_estado_no_dice_nada`, que fijaba que la pasada
**no dijera nada**. No es un daño colateral: es la decisión tres de este ADR,
que revierte a propósito una propiedad anterior, y la prueba se reescribió
diciéndolo —conserva intacta la parte que importa (el almacén no se toca) y
cambia la que escondía el fallo.

## Consecuencias

- **17 encargos pasan a `cancelled`**, y `cancelled` es terminal: el reflector
  deja de mirarlos en cada pasada. Entre ellos los 5 `failed_safely` y 2 de
  los 4 `needs_decision`, cuyo alcance va más allá de los 21 `active` con los
  que empezó este trabajo. Es deliberado y la razón es la misma: una parada
  cuya incidencia está cerrada no se puede reanudar, porque reanudar se hace
  sobre la incidencia.
- **`cancelled` no dice «no se hizo», dice «el motor no observó que se
  hiciera».** Un encargo cuyo PR se fusionó a mano sin que el ciclo aplicara
  `sirius:completed` —el caso de #424 y #389— queda cancelado, no entregado.
  El motor no puede afirmar una fusión que no vio; el enlace a la incidencia
  queda en el diario para quien quiera comprobarlo.
- **La pasada pasa de una línea a unas treinta**, y bajará según los encargos
  vivos bajen. Es el precio de que un encargo varado se vea.
- **Sigue sin arreglarse el hueco de origen**: el despachador despacha y nadie
  vuelve a tocar el almacén salvo el reflector. Esto cierra desenlaces, no
  adelanta el ciclo.
- **#392 queda vivo a propósito**, con su divergencia impresa en cada pasada.

## Alternativas descartadas y por qué

Las cuatro de arriba. Y una quinta que se consideró y no entró: **leer el
`state_reason` de GitHub** (`completed` frente a `not_planned`) para
distinguir un cierre por trabajo hecho de uno por abandono. Hoy el espejo no
lo lee —`mirror_projection.py:926` solo mira `estado_gh`— y traerlo obliga a
tocar el puerto, el adaptador y las fixtures. No hace falta para esta
decisión: con o sin ese dato, el motor no observó la entrega, y `cancelled` es
lo que puede afirmar. Si algún día hiciera falta distinguirlos, ese es el
sitio.
