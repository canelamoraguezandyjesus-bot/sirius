# Evidencia — siete defectos decían `abierto` con su arreglo ya fusionado

Rama `fix/cierra-los-defectos-ya-arreglados`, 14-09-2026. **No hay decisión nueva
que registrar y por eso no lleva ADR**: cerrar una entrada cuando su arreglo está
en `main` es lo que el registro ya prescribe, y el criterio para elegir el commit
de cierre lo fijó ADR-080. Esto es el hecho medido y la lista verificada.

## Nota de arranque (antes del primer commit)

**1. ¿Dónde vive el fallo y dónde va el arreglo?** El fallo vive en el dato:
`docs/audits/registro_defectos.yml` afirma `abierto` sobre siete defectos cuyo
arreglo está fusionado. El arreglo va en el mismo fichero. El sitio del arreglo
puede observar el fallo: la comprobación es `git log` sobre `origin/main`, que es
exactamente la fuente que decide si un arreglo está dentro.

**2. ¿Qué NO va a garantizar esto?** No impide que vuelva a pasar. Cerrar una
entrada sigue siendo un gesto que alguien tiene que acordarse de hacer cuando
fusiona; nada lo deriva. Esta rama no toca eso. Tampoco toca la causa de que los
identificadores choquen, que Andy ya decidió atacar por otra vía —que el `H-N`
deje de escribirse a mano— y que es trabajo aparte.

**3. Criterio de parada (decidido antes de mirar ningún resultado).**

- Una entrada solo se cierra si su commit de cierre **existe** (`git log -1`) y
  está **contenido en `origin/main`** (`git branch -r --contains`). Si alguno de
  los dos falla, esa entrada se queda abierta y se dice por qué.
- El commit de cierre es el de la fusión de la PR que trajo el arreglo, no el
  número de la PR ni una inferencia a partir del ADR.
- Si al terminar queda cualquier identificador repetido, o `MEMORIA.md` deja de
  coincidir con lo que genera `sirius-memoria conocimiento`, el trabajo no vale.
- `MEMORIA.md` se regenera **después** de tocar el registro. Nunca antes.

**4. ¿Qué haría el fallo imposible en vez de improbable?** Que el estado no se
escriba: que `cerrado` se **derive** de si el commit que cita el defecto está en
`main`, en vez de ser un campo que alguien pone a mano. Es la misma forma que
ADR-179 y ADR-182 aplicaron a sus inventarios. **No se hace aquí** porque cambia
el formato del registro y su guarda, y eso es una decisión con su propio ADR.
Queda escrito como lo que cerraría la familia de verdad.

## La afirmación

Sobre `origin/main` en `0f54bc28`, siete entradas dicen `estado: abierto` y las
siete tienen su arreglo fusionado:

| Defecto | ADR | Incidencia | Cerrado por | En `origin/main` |
|---|---|---|---|---|
| H-33 | 182 | #597 | `f4a201f` | sí |
| H-37 | 183 | #599 | `8912e1d` | sí |
| H-38 | 185 | #603 | `e36fc55` | sí |
| H-39 | 184 | #601 | `1b8dd40` | sí |
| H-40 | 187 | #608 | `b8ecb2d` | sí |
| H-41 | 188 | #612 | `67f336e` | sí |
| H-42 | 189 | #615 | `0f54bc2` | sí |

Tras el cambio el registro queda en **42 cerrado, 0 abierto**.

## Por qué esta rama y no la anterior

La PR #617 nació hace unas horas para arreglar que `main` tuviera **dos H-39**:
#602 (ADR-184) y #611 (ADR-187) dieron de alta el mismo identificador cada una en
su rama, las dos estaban verdes por separado, y la colisión solo apareció al
fusionar las dos. Mientras esa PR esperaba, **otra sesión renumeró el duplicado en
`main`**, así que su premisa dejó de ser cierta y su rama entró en conflicto con
la base. Se cierra y se rehace desde el `main` vigente, conservando lo único que
sigue haciendo falta: los cierres. Es, otra vez, el coste que mide la incidencia
#608.

## Comprobación

La afirmación, entrada por entrada, antes de tocar nada (salida abreviada):

```
$ for s in f4a201f 8912e1d e36fc55 1b8dd40 b8ecb2d 67f336e 0f54bc2; do
    git log -1 --format='%h %s' $s; git branch -r --contains $s | grep -c origin/main; done
f4a201f3 ADR-182: la guarda del registro de defectos deriva de los ADR que declaran lección (#598)   1
8912e1d6 ADR-183: la ausencia de run de Quality para el head se encamina, no se espera en silencio (#600)   1
e36fc551 ADR-185: la puerta de la memoria se parte en tres interruptores antes de abrirla (#604)   1
1b8dd409 ADR-184: una prohibición no es una petición — el detector de sensibilidad… (#602)   1
b8ecb2d6 ADR-187: una revisión sobrevive a ponerse al día con main si el trabajo propio no cambia (#611)   1
67f336e0 ADR-188: el alcance que el motor no puede escribir para la puerta antes de crear la incidencia (#614)   1
0f54bc28 ADR-189: sirius-decidir, la salida que a una parada de la puerta le faltaba (#616)   1
```

La cadena completa con el cambio queda al pie de esta nota, en el mensaje del
commit que la acompaña (no hay `pwsh` en esta sesión, así que el equivalente a
`scripts/check.ps1` se ejecuta a mano y se declara).

## Lo que NO queda demostrado

- **No se ha comprobado que estos siete sean todos.** Se comprobaron los que el
  registro marca `abierto` hoy; si alguna entrada quedó marcada `cerrado` con un
  commit equivocado, esta nota no lo detecta y no lo buscó.
- **No se ha medido cuánto tarda de media una entrada en cerrarse.** Las siete
  llevaban entre unas horas y dos días, pero eso es una observación de paso, no
  una medida: no se ha recorrido la historia del registro para calcularlo.
- **Nada impide que vuelva a ocurrir**, como dice la pregunta 2 de la nota de
  arranque.
