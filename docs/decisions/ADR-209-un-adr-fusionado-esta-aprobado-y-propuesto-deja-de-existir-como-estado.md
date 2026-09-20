# ADR-209 — Un ADR fusionado está aprobado, y PROPUESTO deja de existir como estado

- Estado: APROBADO
- Fecha: 2026-09-20
- Aprobación: la fusión de la PR por el propietario. La decisión la toma esta
  sesión: el propietario delegó la decisión 5 de la auditoría con estas
  palabras, «no tengo ni puta idea», que es exactamente el caso que ADR-204
  acaba de repartir.
- Nota de arranque: la de ADR-204, que cubre esta tanda entera.

## Contexto y problema

Todo ADR de este repositorio declara dos líneas seguidas:

```
- Estado: PROPUESTO
- Aprobación: la fusión de la PR por el propietario
```

Y **150 de los 203 ADR decían eso estando fusionados en `main`**. La fusión ya
había ocurrido —es lo que los puso ahí—, así que la línea de estado
contradecía a la de aprobación en el 74 % del registro.

Un campo que dice lo mismo en tres de cada cuatro filas, y además es falso, no
informa de nada: quien lee `MEMORIA.md` no puede distinguir una decisión en
vigor de una propuesta pendiente, que es justo para lo que existe ese campo.

El propietario lo resumió en una frase el 20-09-2026, sobre otra línea con el
mismo defecto: *«que ponga lo que es. Si está hecho, ponga hecho, es pura
lógica»*.

## Criterio de parada (escrito ANTES de decidir)

Si al mirarlos resultara que algunos de esos 150 son propuestas de verdad —ADR
escritos y fusionados **sin** que su decisión se aplicara—, no se pueden voltear
en bloque: habría que separarlos uno a uno. Se comprueba leyendo qué declara su
línea de aprobación antes de tocar nada.

## Decisión

**Un ADR que está en el árbol está aprobado**, porque lo que lo aprueba, según
él mismo, es la fusión de su PR. `PROPUESTO` deja de existir como estado.

Quedan tres:

| Estado | Cuándo |
|---|---|
| `APROBADO` | El normal. Qué lo aprueba lo dice la línea `Aprobación` |
| `RECHAZADO` | Se escribió, se estudió y no se hace. Con la razón |
| `SUPERADO por ADR-NNN` | Otro ADR lo reemplazó |

Los 150 pasan a `APROBADO`. La plantilla deja de ofrecer `PROPUESTO`, así que el
siguiente ADR nace ya diciendo lo que es. Y uno que decía `ACEPTADO` —sinónimo
suelto— se normaliza, para que el campo se pueda contar.

## Comprobación que la sostiene

**El criterio de parada, comprobado antes de tocar nada:** se leyó la línea de
aprobación de los ADR en `PROPUESTO` y **todas** dicen la misma variante de «la
fusión de la PR por el propietario» —38 con esa redacción exacta, 21 con «la PR
que introduce este ADR», 20 con «fusión de la PR», y el resto variantes de la
misma frase—. Ninguno declara una aprobación pendiente de otra cosa. El
criterio no se dispara y el volteo en bloque es legítimo.

**Después del cambio:** 194 ADR en `APROBADO` limpio, 5 en `APROBADO` con
matiz, 1 `RECHAZADO`. Ninguno en `PROPUESTO`.

**La guarda**, `tests/automation/test_estado_de_los_adr.py`, 404 pruebas —una
por ADR y por comprobación—, verificada por mutación sobre el árbol confirmado:

| Mutación | Resultado |
|---|---|
| un ADR vuelve a decir `PROPUESTO` | fallan 2 pruebas |
| un ADR declara un estado inventado | falla 1 |
| la plantilla vuelve a ofrecer `PROPUESTO` | falla 1 |

La tercera es la que impide que el defecto vuelva con el ADR siguiente, que es
por donde volvería.

## Consecuencias

- `MEMORIA.md` deja de mostrar 150 decisiones vigentes marcadas como propuestas.
- El campo vuelve a informar: si un ADR dice `RECHAZADO` o `SUPERADO`, es que
  algo pasó.
- **El coste, declarado:** el estado de un ADR nuevo se escribe `APROBADO`
  mientras aún está en una rama, es decir, antes de que la fusión que lo aprueba
  ocurra. Es la misma anticipación que ya hacía la línea `Aprobación` desde el
  primer ADR del repositorio, y el único momento en que el fichero existe sin
  estar aprobado es mientras su PR está abierta. Se acepta a propósito: la
  alternativa —que alguien se acuerde de voltear la línea justo después de cada
  fusión— es la familia `regla-que-depende-de-que-alguien-se-acuerde`, que esta
  casa lleva cerrando desde ADR-174.

## Alternativas descartadas y por qué

- **Que el estado lo derive `MEMORIA.md` en vez de vivir en el fichero.** Es más
  correcto y esconde el dato: quien abre el ADR suelto —que es como se leen—
  seguiría viendo `PROPUESTO`.
- **Voltearlo automáticamente al fusionar.** Exige que un workflow escriba en
  `main` después de cada merge, con el riesgo que eso trae, para ahorrar una
  palabra que ya se escribe al crear el ADR.
- **Dejarlo como estaba y documentar que PROPUESTO significa aprobado.** Es
  pedirle a cada lector que recuerde que el campo miente.

## La lección

- familia: `pieza-sin-lector`
- sin esto se repetiría: el campo de estado seguiría siendo ruido, y cada ADR
  nuevo nacería contradiciendo su propia línea de aprobación.
- lo hace cumplir: `tests/automation/test_estado_de_los_adr.py`
