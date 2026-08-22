# ADR-069 — Fusionar exige que la rama esté al día con su base

- Estado: PROPUESTO
- Fecha: 2026-08-22
- Aprobación: la fusión de la PR de esta rama por el propietario
- Nota de arranque de esta rama: este ADR. Publicado antes del primer commit.

## Contexto y problema

`sirius_merge_on_command.sh` comprueba seis cosas antes de fusionar, y una de
ellas es que la PR no tenga conflictos:

```sh
if [ "$mergeable_state" = "dirty" ]; then …
```

**`dirty` solo cubre el conflicto de git.** Una rama atrasada respecto a su base,
sin conflicto textual, sale `clean` — y entonces se fusiona algo cuyo Quality se
calculó contra un `main` que ya no existe. Verde contra su propia base, y sin
que nadie haya comprobado cómo queda la base al juntarlas.

### No es hipotético: pasó, y estuvo a punto de repetirse

**Pasó.** `main` se puso roja tras una tanda de nueve fusiones porque dos ramas,
verdes por separado, usaban campos incompatibles: una renombró un campo de
configuración y otra seguía usándolo. Cada PR era correcta contra su base.

**Estuvo a punto de repetirse tres veces el 22-08-2026**, con números de ADR. Las
PR #252, #253 y #254 escogieron el mismo número en ventanas solapadas. El detalle
que lo hace grave: **git no daba conflicto**, porque los nombres de fichero son
distintos, así que `main` habría quedado con dos ADR del mismo número — el
patrón que ya produjo los dos ADR-016 que hoy conviven en el registro. Lo cazó un
revisor leyendo el diff, no una herramienta.

### Lo que sí existía, y por qué no bastó

`tests/automation/test_registro_de_decisiones.py::test_no_new_number_is_ever_reused`
**ya falla** si hay dos ADR con el mismo número, con el par ADR-016 como única
excepción declarada. Y Quality valida el **merge ref** —la mezcla de la PR con su
base—, así que esa prueba sí habría cazado la colisión… **si Quality hubiera
vuelto a correr después de que la otra PR se fusionara.**

Ahí está el hueco, y es de temporización, no de cobertura: el último Quality
verde de una PR puede haberse calculado contra una base anterior, y nada exige
recalcularlo antes de fusionar.

## Criterio de parada (escrito ANTES de decidir)

Si cerrar esto exigiera bloquear una fusión legítima ante un fallo de lectura
—tratar «no pude comprobarlo» como «está atrasada»— se para: dejar la orden del
propietario tirada por un 503 es el callejón mudo que el resto de este guion
existe para eliminar.

## Decisión

Una comprobación más, entre el estado de la PR y la del head aprobado: se pide a
GitHub `compare/<base>...<head>` y se lee **`behind_by`**, que es exactamente
«cuántos commits de la base le faltan a la rama». Si es mayor que cero, no se
fusiona: se publica el número concreto y se pide actualizar la rama, esperar a
Quality y repetir la orden.

**Ante una lectura que falla, se sigue.** Es la aplicación del criterio de
parada: un `behind_by` ausente o ilegible no bloquea, porque las otras seis
comprobaciones siguen puestas y ninguna de ellas depende de esta. El error cae
del lado de fusionar algo que quizá estaba al día, no del de ignorar una orden
del propietario por un fallo de red.

## Consecuencias

- Aceptada: alguna fusión legítima pedirá un «Update branch» y una espera de
  Quality. Es el coste, y es el que se quiere pagar.
- **Esto cubre el camino `fusiona`, no el botón de GitHub.** Quien fusione desde
  la interfaz sigue pudiendo hacerlo con la rama atrasada. Cerrar también ese
  camino es un ajuste de protección de rama —«Require branches to be up to date
  before merging»— y es una decisión del propietario sobre la configuración del
  repositorio, no código de este repositorio.

## Lo que esto NO garantiza

- **No garantiza que la mezcla sea correcta**, solo que Quality se calculó sobre
  ella. Dos cambios compatibles a ojos de las pruebas pueden seguir siendo un
  error de diseño.
- **No detecta recursos compartidos invisibles.** El número de ADR fue el que
  avisó esta vez porque hay una prueba que lo mira; otro recurso repartido sin
  guarda seguiría colándose. Está apuntado como trabajo aparte en la incidencia
  #251.

## Comprobación que la sostiene

- Prueba por mutación, vista fallar: quitada la guarda, `test_una_rama_atrasada_no_se_fusiona` cae; restaurada, verde.
- Control positivo: una rama al día **sí** se fusiona — sin él, la prueba anterior pasaría con el merge roto entero.
- Control de lectura caída: con `behind_by` ilegible, la fusión sigue adelante.
