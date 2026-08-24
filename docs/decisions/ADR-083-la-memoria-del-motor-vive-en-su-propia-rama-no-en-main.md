# ADR-083 — La memoria del motor vive en su propia rama, no en `main`

- Estado: PROPUESTO
- Fecha: 2026-08-24
- Aprobación: fusión de la PR por el propietario
- Contexto: D2, incidencia #296. Afina **ADR-082**, que fijó que la memoria del
  motor vive «dentro del repositorio» sin decir dónde
- Relacionadas: ADR-082 (I4, el motor dentro de Actions), ADR-026 (el diario),
  ADR-002 (la automatización no edita `.github/**`), ADR-001

## Contexto y problema

ADR-082 decidió que el diario del motor sería «un fichero versionado del
repositorio». D2 lo cableó a `estado-del-motor/` en `main` (#298).

**Ese mismo día el propietario activó un ruleset sobre `main`** que exige pull
request. Un `git push` directo desde el workflow del motor queda rechazado.

Y las dos primeras ejecuciones en el servidor **salieron en verde sin que eso se
notara**. El log del turno real dice:

```
El motor no anotó nada en este turno.
```

El paso que confirma la memoria sale antes de empujar cuando no hay nada que
anotar, y el diario estaba vacío. Así que **el `git push origin HEAD:main` nunca
llegó a ejecutarse**: la única línea que podía fallar no se probó.

Es la clase de verde que no dice «funciona» sino «no llegó a intentarlo», y por
eso el defecto habría esperado al primer turno con trabajo dentro — que es
justo el turno en que perder la anotación duele.

## Criterio de parada (escrito ANTES de decidir)

**(a)** Si la solución **abre un permiso permanente** sobre `main`, se para. La
protección se levantó ese mismo día; abrirle una puerta el mismo día la
convierte en decorado.

**(b)** Si exige **tocar el código del motor**, se para. La ubicación del diario
ya es configurable (`SIRIUS_MOTOR_DIARIO`); si hiciera falta cambiar `src/`,
sería señal de que la abstracción estaba mal y eso es otro bloque.

**(c)** Si el arreglo **no se puede cerrar en la misma PR que abre el permiso
para hacerlo**, se para. La vez anterior el permiso quedó abierto varios días y
el propietario tuvo que reclamarlo.

## Opciones consideradas

1. **Meter al motor en la lista de excepciones del ruleset.** Descartada por el
   criterio (a): es un permiso permanente para empujar a `main`, para esto y
   para cualquier otra cosa. Y su coste no lo paga este bloque, lo paga el
   repositorio para siempre.
2. **Que el diario viaje por pull request.** Descartada por una razón que la
   tumba entera: el motor **lee su diario del checkout** en la invocación
   siguiente. Si la anotación se queda en una PR sin fusionar, el turno
   siguiente lee memoria vieja y repite trabajo ya hecho. No es lento: es
   incorrecto.
3. **Una rama propia para la memoria.** Es la elegida.

## Decisión

**Opción 3.** El diario del motor vive en la rama **`estado-del-motor`**,
huérfana a propósito —no comparte historia con `main` y no la arrastra—, y el
workflow la trae a un árbol de trabajo **fuera del espacio de trabajo** para no
ensuciar el estado de `main`.

Esto **afina ADR-082, no lo contradice**: aquel dijo «dentro del repositorio», y
una rama lo está. Lo que se concreta es dónde.

No hace falta tocar el motor: `SIRIUS_MOTOR_DIARIO` ya mandaba sobre el
defecto, así que el cambio vive entero en el workflow (criterio de parada b,
respetado).

## Comprobación que la sostiene

**El defecto, leído en el log real** —no razonado—: ejecución `32745432192`,
paso «Confirmar la memoria del motor», salida `El motor no anotó nada en este
turno.` y salto directo al final. El `git push` no aparece en el log porque no
se ejecutó.

**El ruleset no alcanza a esta rama**: apunta a la rama por defecto, y
`estado-del-motor` no lo es. Es la misma propiedad en la que se apoya la
decisión, así que si algún día el ruleset se amplía a todas las ramas, esto hay
que releerlo.

**La guarda de serialización sigue mordiendo** tras el cambio: reconoce
`motor-sirius.yml:turno` con grupo constante `motor-sirius` y
`cancel-in-progress: false`. El paso que empuja cambió de destino, no de
naturaleza, y sigue dentro de su alcance.

```
uv run ruff check .              → OK
uv run pytest tests/automation   → 706 passed, 5 skipped
```

## Comprobación posterior: el camino de escritura ya no está sin probar

Esta decisión se tomó sin haber visto nunca ejecutarse el `git push`, y este
mismo documento lo dejó dicho: «una ejecución que pasa por no tener trabajo que
hacer no prueba que sepa hacerlo». **Eso ya está cerrado, y por ejecución.**

Se extrajeron los tres bloques `run:` del workflow —`diff` confirma que dos son
idénticos byte a byte y que en el tercero la única diferencia es la expansión
que GitHub hace de `inputs.ensayo` antes de que bash vea nada— y se ejecutaron
con `bash -e`, el shell del runner, contra un remoto de juguete.

Con la memoria vacía: el turno sale en verde, `git status --porcelain` sale
vacío y la rama no se crea. Con **una sola línea** dentro del diario y el mismo
script sin tocar un carácter:

```
git add -A
git commit           -> root-commit, «Motor: turno del ...»
git push origin HEAD:refs/heads/estado-del-motor
                     -> * [new branch]  HEAD -> estado-del-motor   (exit 0)
```

El camino de escritura **está intacto y es alcanzable en cuanto haya un byte
que anotar**. No estaba roto: estaba ocioso. Decirlo importa porque lo contrario
—«no puede recorrerse nunca»— se llegó a escribir aquí, y era falso.

Se buscaron además, ejecutando, cuatro familias de fallo alrededor de este
camino: el primer turno, el segundo con carrera contra el remoto, la basura que
podría colarse en el árbol huérfano, y el turno que muere a mitad. Ninguno
sobrevivió a la refutación. Los dos que más lo parecían se caen por lo mismo:
el turno que muere sale en **rojo**, no en verde, porque `Dar el turno` no tiene
`continue-on-error` y `set -uo pipefail` no desactiva el `-e` del runner.

**Lo que esta comprobación NO dice.** Que el motor tenga algo que anotar. El
diario solo se llena por el despachador, y su cableado sigue siendo la frontera
declarada del bloque anterior: hoy `sirius-despachar` no lo invoca ningún
workflow ni ningún script. El motor supervisa correctamente un mundo vacío.

## Consecuencias

**El historial de `main` deja de llenarse de contabilidad.** El motor anota en
cada turno. Eso es estado, no código, y no tiene por qué vivir en el historial
del código. Es un beneficio que no se buscaba y conviene decir que llegó de
regalo, no como justificación de la elección.

**La memoria deja de verse en el árbol de `main`.** Es el precio. Se mitiga con
un cartel —`estado-del-motor/LEEME.md`— que dice dónde está y cómo leerla,
porque buscarla en su sitio antiguo es lo primero que hará cualquiera.

**Lo que esto NO resuelve, y no hay que leerlo aquí:** que dos invocaciones
simultáneas se pisen. Eso lo impide el grupo de concurrencia, y está medido en
`tests/engine/test_exclusion_entre_invocaciones.py`. Cambiar de rama no cambia
nada de eso.

**Y queda una lección más general que el caso.** El primer turno en el servidor
dio verde sobre un camino que no se recorrió. Una ejecución que pasa por no
tener trabajo que hacer no prueba que sepa hacerlo: hay que mirar **qué pasos se
ejecutaron de verdad**, no el color del resultado.

## Alternativas descartadas y por qué

- **Excepción en el ruleset**: criterio de parada (a). Permiso permanente a
  cambio de una comodidad puntual.
- **El diario por pull request**: rompe la lectura del turno siguiente. Una
  anotación sin fusionar es memoria perdida, no memoria en tránsito.
- **Volver a poner el diario fuera del repositorio**: sería deshacer I4, que el
  propietario decidió con su evidencia delante. No se reabre una decisión suya
  para esquivar un problema de fontanería.
