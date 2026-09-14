# ADR-191 — La revision es una cola: una rama entra a revision solo si main ya esta dentro de ella

- Estado: PROPUESTO
- Fecha: 2026-09-14
- Aprobación: el propietario, fusionando la PR de esta rama. La decisión de
  fondo —que la revisión sea una cola— la tomó él el 14-09-2026 de madrugada;
  este ADR fija la forma y deja escrito lo que todavía no se hace.

## Contexto y problema

Una pull request se valida contra el `main` que tenía cuando corrió Quality. Si
otra se fusiona en medio, **la combinación que aterriza en `main` no la ha
probado nadie**, y ninguna de las dos ramas puede verlo desde dentro: cada una
está verde y cada una tiene razón. El fallo no vive dentro de una rama, vive
entre dos.

El propietario lo dijo antes de que lo midiéramos, y corrigiendo una propuesta
mía que no servía:

> «En el momento que haya tres trabajos al mismo tiempo va a salir en rojo,
> aunque tú tengas el poder de fusionar. Puedes mandar quince trabajos seguidos,
> pero que cada uno tenga su cola. Cada trabajo puede llegar hasta
> implementación, pero que solo pase a revisión cuando esté actualizado con
> `main`.»

Tenía razón en lo de fondo: **quién pulsa el botón de fusionar no cambia nada**.

**La medida** (criterio declarado antes de contar: una fusión está «probada
contra su `main` real» si el commit de `main` inmediatamente anterior es
ancestro del head de su PR). Sobre las 14 últimas fusiones, del 12-09 16:28 al
14-09 02:20:

| | |
|---|---|
| Fusiones comprobadas | 14 |
| Sin probar contra su `main` real | **1** (#611, ADR-187) |

Esa única es exactamente la que dejó `main` en rojo con dos `H-39`: entró 13
minutos después de #602 y ninguna de las dos vio a la otra.

**La segunda mitad del dato, sin la cual esto se lee mal:** las otras 13 salen
«sí» **porque se pagó una reconciliación manual por cada una**. Ese coste es el
que mide #608. Así que la cola no evita un sangrado constante: evita un suceso
raro y caro, y automatiza el trabajo manual que hoy evita los demás.

**Por qué ahora y no antes.** ADR-187 hizo gratis ponerse al día con `main`: una
revisión sobrevive si el trabajo propio de la rama no cambia. Antes, una cola que
obliga a actualizarse habría cambiado un coste por otro y no debía hacerse.

## Criterio de parada (escrito ANTES de decidir)

Publicado en `docs/audits/arranque-la-revision-es-una-cola.md`, commit
`cfd5662c`, antes del primer commit de código.

- Si la medida dijera que esto no ha pasado nunca, se dice con esas palabras y se
  decide igualmente —una puerta que depende de que nadie se despiste es la
  familia que este repositorio lleva cerrando desde ADR-174—, pero entonces la
  forma tiene que ser la más barata que funcione.
- **La cola no vale si puede quedarse pillada.** Si existe cualquier estado del
  que nadie salga sin que una persona lo desatasque, el diseño está mal y se
  tira. Esto es lo que descarta un cerrojo.
- La cola no vale si deja a una rama esperando para siempre.
- No debilita nada: que solo se revise un head con Quality en verde sigue en pie
  (contrato), y las cinco causas de la puerta de sensibilidad quedan intactas.
- Cada regla nueva trae una mutación sembrada y vista caer.

## Opciones consideradas

1. **Un cerrojo**: un turno que una rama coge y suelta. Descartado; ver abajo.
2. **Una etiqueta nueva, `sirius:en-cola`.** Superficie nueva: transiciones
   nuevas, guardas nuevas, y un estado más del que se puede uno quedar colgado.
3. **Una condición derivada, sin estado nuevo.** Elegida.

## Decisión

**Uno. La condición es una sola pregunta:** ¿es la punta de `main` ancestro del
head de la rama? Si lo es, lo que se revise es lo que aterrizará. Si no, la
combinación que aterrizaría no la ha probado nadie y la rama espera.

Vive en `scripts/automation/sirius_cola.py`, recibe el JSON de
`compare/MAIN...HEAD` y no llama a nadie: la lectura la hace el workflow con su
reintento y su token. Así la decisión se prueba de verdad
(`tests/automation/test_cola.py`) en vez de quedarse pegada en un YAML que nadie
ejecuta —la lección de H-14, incidencia #282—.

**Dos. De esa sola condición sale la cola entera.** Si A y B están las dos al día
y A se fusiona, B **deja de estarlo sola** y tiene que ponerse al día para
seguir. Una a una, que es lo que el propietario pidió. No hace falta llevar la
cuenta de nada.

**Tres. Esperar NO es pararse, y esa distinción es la clave.** `stop_gate`, la
única forma que tiene `review-sirius-work.yml` de decir que no, aplica
`sirius:failed-safely`, que es **terminal**. Una cola que dijera «todavía no» por
ahí mataría a cada rama que hiciera cola: cuanto mejor funcionara, más trabajo
muerto dejaría —la forma exacta del defecto que la #613 acaba de cerrar—. Por eso
esperar es una **no-transición**: no se aplica `sirius:review-requested` todavía
y la incidencia se queda en `sirius:ci-pending`, que no es terminal.

Eso mueve la puerta: no va en `review-sirius-work.yml` sino en
`advance-sirius-after-quality.yml`, que es quien decide aplicar la etiqueta de
revisión cuando Quality da verde.

**Cuatro. Fail-closed, y aquí se puede.** Cualquier cosa que impida AFIRMAR que
la rama está al día hace esperar. Se puede ser estricto **precisamente porque
esperar es recuperable**; dejar pasar de más mete en `main` algo que nadie probó.

**Cinco. Pero esperar en silencio sí es un defecto** (ADR-183). El veredicto trae
el motivo para que quien llame lo escriba en la incidencia.

**Seis. Lo que este ADR NO hace todavía, y por qué.** La puerta **no se cablea
aquí**. `advance-sirius-after-quality.yml` tiene `contents: read` y
`pull-requests: read`: no puede poner al día una rama. Cablear la puerta sin que
exista quien actualice la rama que espera **crearía un atasco nuevo** —la rama se
quedaría esperando a alguien que no existe—, que es exactamente el defecto que
ADR-183 cerró y el criterio de parada de arriba prohíbe. Ampliar esos permisos es
una decisión del propietario, de la misma familia que ADR-002 resolvió en contra
para la credencial del motor, y no se toma en su ausencia.

Queda, por tanto, **la condición construida y probada, y el cableado pendiente**,
con lo que falta nombrado: quién pone al día la rama que espera, y con qué
permiso.

## Comprobación que la sostiene

La medida, con los heads traídos de `refs/pull/<n>/head` y comprobando la
ancestría con `git rev-list` —no con `git merge-base`, denegado en este entorno—:
14 comprobadas, 1 sin probar. La tabla completa, fusión por fusión, está en
`docs/audits/evidencia-mejora-la-revision-es-una-cola.md`.

**Cinco mutaciones sembradas, y una sobrevivió a la primera pasada:**

| | Mutación | Resultado |
|---|---|---|
| M1 | meter `behind` y `diverged` entre los estados al día | 6 pruebas caen |
| M2 | fail-open al no poder leer la comparación | 6 pruebas caen |
| M3 | quitar la comprobación de que `status` es texto | **21 pasan** |
| M4 | decir siempre «commits», también con uno | 1 prueba cae |
| M5 | un motivo fijo, sin cuánto le falta | 3 pruebas caen |

M3 es el caso de ADR-184: la garantía estaba en la prosa del módulo y en ninguna
aserción. Sin esa comprobación, una comparación rota con `behind_by` presente
responde «vas 2 commits por detrás» —afirmar lo que el dato no sostiene, y mandar
a quien lo lea a ponerse al día de algo que quizá ya tiene—. Se añadió
`test_una_comparacion_rota_no_afirma_que_la_rama_va_por_detras` y M3 cae.

**Dos defectos propios, cazados y escritos:**

- El ayudante de las pruebas escribía todas las comparaciones en el mismo
  fichero, así que dos dentro de la misma prueba se pisaban. Lo cazó la única
  prueba que usa dos a la vez.
- **`ruff format` rompió el módulo dos veces.** Con `target py314` quita los
  paréntesis de `except (OSError, ValueError):` —PEP 758— y el `python3` del
  runner no llega a esa versión: el fichero deja de compilar allí. Es el defecto
  que #267 ya tenía apuntado («el formateador del proyecto mete sintaxis que mata
  al runner»). El arreglo no es acordarse de no formatear: son dos cláusulas
  `except` separadas, sin nada que el formateador pueda colapsar. La guarda que
  existe para esto (`test_sirius_runner_python_compat.py`) no lo cazó **y hace
  bien**: su mitad derivada solo exige que esté en la lista lo que algún workflow
  o `.sh` invoca de verdad, y a este módulo todavía no lo invoca nadie. Al
  cablearlo hay que añadirlo a `SCRIPTS_RUN_ON_THE_RUNNER`.

Cadena sobre el árbol de esta rama, ejecutada **después** de pasar el formateador,
que es lo que fallaba antes (no hay `pwsh` en esta sesión):

```
uv run ruff format --check .        -> 636 files already formatted
uv run ruff check .                 -> All checks passed!
uv run mypy src tests               -> Success: no issues found in 599 source files
uv run pytest tests/automation/ -q  -> 2418 passed, 12 skipped
git diff --check                    -> sin salida
```

## Consecuencias

- Mientras la puerta no se cablee, **la cola la ejecuta una persona**: fusionar de
  una en una y poner la siguiente al día antes de tocarla. Es lo que el
  propietario autorizó para esta noche, y es además la mejor prueba del diseño
  antes de automatizarlo.
- Cuando se cablee, cada fusión costará a las demás ramas un `update-branch` y
  una vuelta de Quality —no una ronda de revisión, que era la cara—.
- El orden FIFO que el propietario eligió no necesita registro: sale de ordenar
  por cuándo entró en espera, un dato que ya existe.

## Alternativas descartadas y por qué

- **Un cerrojo.** Hay que acordarse de soltarlo, y aquí los procesos mueren: un
  runner se cae, una sesión se corta. Entonces el turno se queda cogido y hace
  falta que alguien lo libere a mano. Es `regla-que-depende-de-que-alguien-se-acuerde`,
  la familia más repetida de este repositorio, y el criterio de parada la prohíbe
  explícitamente.
- **Una etiqueta `sirius:en-cola`.** Un estado más del que quedarse colgado, y
  transiciones nuevas que mantener, para expresar algo que ya se puede calcular.
- **Poner la puerta en `review-sirius-work.yml`.** Solo sabe decir que no de forma
  terminal. Ver el punto tres de la decisión.
- **Reconstruir la ancestría a mano** en vez de leer el `status` que GitHub ya
  calcula. Sería otra copia del mismo hecho, la familia que ADR-178 cerró.

## La lección

- familia: `regla-que-depende-de-que-alguien-se-acuerde`
- sin esto se repetiría: fusionar una rama cuya combinación con `main` no ha
  probado ningún run, porque cada pull request solo puede mirarse a sí misma y la
  única defensa era que quien fusiona se acordara de poner las demás al día
  primero; el 13-09 no se acordó nadie y `main` quedó en rojo con dos `H-39`.
- lo hace cumplir: `tests/automation/test_cola.py`
