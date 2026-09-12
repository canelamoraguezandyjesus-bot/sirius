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

(se completa al cerrar el trabajo)

## Decisión

(se completa al cerrar el trabajo)

## Comprobación que la sostiene

(se completa al cerrar el trabajo)

## Consecuencias

(se completa al cerrar el trabajo)
