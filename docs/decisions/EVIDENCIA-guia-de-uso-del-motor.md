# Nota de arranque — rama `guia-de-uso-del-motor`

> No es un ADR: no decide nada. Es la evidencia de un trabajo, y vive aquí
> porque `.claude/evidencia/` está en la lista de denegados permanentes y no
> puedo escribir en ella.

- Fecha: 2026-08-25
- Trabajo: `docs/operations/MOTOR_DE_SIRIUS.md`, la guía de uso del motor:
  cómo se le da una orden, cómo da un turno y dónde vive su memoria.

## Lo primero, porque es lo que ata: esta nota NO se publicó antes

ADR-001 no exige tener un criterio de parada, exige **haberlo publicado antes de
ver resultados**. Aquí no se hizo: no hubo cuatro preguntas ni criterio de
parada antes de empezar a escribir. Lo avisó el hook al terminar, no yo al
empezar. Se escribe después y por eso **vale menos**. Queda dicho en vez de
disimulado, que es la única forma de que el registro siga sirviendo de algo.

Y no había aquí ningún sustituto: a diferencia de `claude/donde-estamos`, no
existía un guion con el método comprometido por adelantado. No lo hubo.

## Criterio de parada (retroactivo, y por tanto débil)

El que de hecho se aplicó, dicho tal cual fue: **ninguna afirmación entra en el
documento sin haberla visto ejecutarse en esta sesión.** Se paró al cubrir las
tres preguntas del encargo —cómo se ordena, cómo se da un turno, dónde está la
memoria— con esa condición cumplida en cada frase.

Un criterio decidido después no puede sorprenderte, y ése es exactamente su
defecto: no hubo ningún resultado que pudiera contradecirlo.

## Las afirmaciones, y lo que sostiene a cada una

| Afirmación del documento | Comprobación |
|---|---|
| `sirius-supervisar` no aparecía en ningún documento; `sirius-despachar` solo en ADRs | `grep -rln` sobre `docs/`: para el primero, cero resultados |
| El ensayo es el modo por defecto y atraviesa el mismo despachador que la ejecución | `dispatch_cli.py`, `_EscritorDeEnsayo` y su comentario sobre H-12 |
| El intérprete solo entiende «corrige» o «implementa» al principio | rechazo real: una orden que empezaba por «Amplía» salió como «intención ambigua» |
| Solo despacha `programacion` y `auditoria` | `ClaseNoDespachableError` real al despachar un encargo de documentación |
| `--ejecutar` falla primero por `SIRIUS_BOT_TOKEN`, y solo después necesitaría `gh` | construcción real de `GitHubCliWriter` → `MissingCredentialError` |
| Un turno sin trabajo no anota nada y eso es correcto | el log del motor y la comprobación posterior de ADR-083 |
| La rama de memoria no existe hasta la primera anotación | `git ls-remote --exit-code`, código 2 |

## La afirmación que salió mal, que es la que da valor a esto

La primera versión del documento decía que `--ejecutar` se bloquea por **no
tener `gh`**. Es falso: el escritor **no llega ni a construirse** sin
`SIRIUS_BOT_TOKEN`, y falla con mensaje claro y código 4, antes de tocar nada.

Se descubrió al ejecutar el constructor de verdad **después** de haberlo escrito
mal. Era una deducción razonable —el adaptador se llama `GitHubCliWriter` y sí
lanza `gh`— y era incorrecta. Mismo patrón que ha costado el día entero: lo
razonable no es lo comprobado.

## Lo que NO pude comprobar

- **Que `--ejecutar` funcione** con el token y `gh` presentes. Aquí no hay
  ninguno de los dos, así que el camino de escritura del despachador está
  descrito por su código, no visto correr. El documento no afirma que funcione:
  dice qué le falta.
- **Que el documento sirva** a alguien que no sea su autor. Eso solo lo dice
  usarlo, y nadie lo ha usado todavía.
