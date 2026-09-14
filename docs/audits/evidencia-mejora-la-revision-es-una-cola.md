# Evidencia — la revisión es una cola

Rama `mejora/la-revision-es-una-cola`, 14-09-2026. **Las cuatro preguntas y el
criterio de parada están en `docs/audits/arranque-la-revision-es-una-cola.md`**,
publicadas y confirmadas en `cfd5662c`, antes del primer commit de código. Este
documento recoge lo medido y lo irá recogiendo a medida que el trabajo avance;
la decisión, cuando esté, va a su ADR.

## La afirmación

Una PR se valida contra el `main` que tenía cuando corrió Quality. Si otra PR se
fusiona en medio, la combinación que aterriza en `main` **no la ha probado
nadie**, y ninguna de las dos ramas puede verlo desde dentro: las dos están
verdes y las dos tienen razón.

## Criterio de la medida, declarado antes de contar

Una fusión está **probada contra su `main` real** si el commit de `main`
inmediatamente anterior a ella es ancestro del head de su PR. Si no lo es, la
combinación que aterrizó no la probó ningún run de Quality.

Se comprueba con `git rev-list <head-de-la-PR>` y se busca el sha del padre en
`main`. No se usa `git merge-base`: está denegado en este entorno, y además la
pregunta no es dónde divergen sino si ese commit concreto está dentro.

## La comprobación

Sobre las **14 últimas fusiones** de `origin/main` (12-09 16:28 → 14-09 02:20),
con los heads traídos de `refs/pull/<n>/head`:

| Fusión | PR | Hora | ¿Probada contra su `main` real? |
|---|---|---|---|
| `0f54bc28` | #616 | 14-09 02:20 | sí |
| `67f336e0` | #614 | 13-09 22:08 | sí |
| `b8ecb2d6` | #611 | 13-09 16:28 | **NO** |
| `1b8dd409` | #602 | 13-09 16:15 | sí |
| `e36fc551` | #604 | 13-09 10:27 | sí |
| `8912e1d6` | #600 | 13-09 09:52 | sí |
| `f4a201f3` | #598 | 13-09 09:33 | sí |
| `c64f4164` | #596 | 13-09 08:57 | sí |
| `f5295bec` | #591 | 13-09 08:42 | sí |
| `7aae33cd` | #590 | 13-09 08:17 | sí |
| `673b2f4f` | #593 | 13-09 01:48 | sí |
| `f6fa1e68` | #595 | 13-09 01:16 | sí |
| `9efaa3c2` | #589 | 12-09 16:38 | sí |
| `66d9fffc` | #588 | 12-09 16:28 | sí |

**14 comprobadas, 1 sin probar.** Y esa única —#611, trece minutos después de
#602— es exactamente la que dejó `main` en rojo con dos `H-39`.

## La segunda mitad del dato

Las otras 13 salen «sí» **porque se pagó una reconciliación manual por cada una**:
traer `main` a la rama antes de fusionar. Ese coste es el que mide la incidencia
#608. Decidir con la primera cifra sola sería decidir sobre medio hecho: la cola
no evita un sangrado constante, **evita un suceso raro y caro y automatiza el
trabajo manual que hoy evita los demás**.

## Lo que NO queda demostrado

- **La ventana es de 14 fusiones, no de la historia entera.** Elegida por ser el
  tramo de actividad continua más reciente; una ventana mayor podría dar otra
  proporción. No se ha recorrido el resto.
- **No se ha medido el coste de las 13 reconciliaciones**, solo se afirma que
  existieron. Cuántas rondas costaron exactamente está en #608, medido allí sobre
  cinco fusiones, no sobre estas catorce.
- **No se ha comprobado si alguna de las 13 se reconcilió sola** (porque su rama
  ya estaba al día por casualidad) en vez de a mano. La cifra de trabajo manual
  evitado es, por tanto, un techo, no un valor exacto.

## Un hallazgo de paso: el gancho de parada no reconoce la nota de arranque

Al cerrar el turno con la nota de arranque ya escrita y confirmada, el gancho
`recordar_parada.py` la dio por ausente y pidió escribirla. El motivo está en
`_es_evidencia`: acepta `docs/decisions/ADR-*.md` y `docs/audits/evidencia-*.md`,
y **no** `docs/audits/arranque-*.md`, que es como este repositorio nombra
exactamente lo que el gancho exige —hay una quincena de ficheros con ese prefijo
en `docs/audits/`, y ADR-001 llama a eso «nota de arranque»—.

Es la misma forma que H-18 (#311): un comprobador que pide algo y no reconoce el
sitio donde eso vive de verdad enseña a saltárselo. No se arregla en esta rama
—`.claude/**` está en la lista `deny` y el arreglo es de otro alcance—; queda
anotado aquí para que no se pierda.
