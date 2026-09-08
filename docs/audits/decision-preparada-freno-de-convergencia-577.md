DECISIÓN — El ciclo de H1 continúa: la ronda 2 no midió una regresión del trabajo, midió un ensanchamiento de la revisión.

**Criterio escrito ANTES de saber si el freno salta y antes de ver la ronda 3.**

## Los hechos

| ronda | pendientes | gravedad |
|---|---|---|
| 1 | 2 | 4 |
| 2 | 3 | 4 |

El par empeora, así que formalmente no hay progreso. Pero **los tres hallazgos
de la ronda 2 estaban íntegros en el head de la ronda 1**: la propia revisión
los marca uno a uno con «LLEGA TARDE POR GOTEO DE LA REVISIÓN DE LA RONDA 1» y
activa su guardián de goteo. El código y las pruebas implicadas son idénticos a
los de `2c21f59`.

Es decir: entre la ronda 1 y la ronda 2 **el trabajo no empeoró en nada**. Lo
que cambió es cuánto se miró.

## Por qué eso justifica continuar, y qué NO justifica

Continuar **no** es indulgencia con el trabajo: los tres hallazgos son reales y
se corrigen enteros, sin rebajar ninguno. Es que la magnitud que el freno mide
—pendientes por ronda— no es, en esta ronda concreta, una medida del estado del
trabajo.

Lo que esta decisión **no** autoriza:

- No autoriza una ronda 4 sin progreso. Si la ronda 3 vuelve a no progresar
  **por hallazgos nuevos de verdad** —no marcados como goteo—, eso sí es
  divergencia y el trabajo se para y se replantea, no se vuelve a reanudar.
- No autoriza relajar, renombrar ni aplazar ninguno de los tres hallazgos.
- No autoriza tocar nada fuera de los límites que cada hallazgo declara.

## Por qué mi propia regla de «solo prosa de la ficha» NO se aplica aquí

Escribí en la ronda 5 de #574 que **si el freno para el ciclo y la ronda trae
solo prosa de la ficha, no autorizo otra ronda**. Dos de los tres hallazgos de
esta ronda son de ficha, así que hay que decir por qué no dispara — y la
respuesta ya está escrita por mí en la entrada 63, no la invento ahora:

> «El criterio se refiere a **defectos de PROSA introducidos por la
> corrección**» — y allí mismo, sobre un hallazgo documental: «no es prosa: es
> un agujero de cobertura».

Los dos motivos, independientes:

1. **Ninguno de los tres lo introdujo una corrección.** Los tres estaban
   íntegros en el head de la ronda 1; son goteo, no prosa generada al parchear.
   El criterio se escribió contra el bucle «cada corrección añade prosa nueva
   que nadie verifica», y aquí no hay tal bucle: el código de la ronda 1 se
   corrigió una vez y la ronda 2 miró sitios que nadie había mirado.
2. **No son prosa.** `CLAUDE-R2-001` dice que el titular afirma más de lo que
   el dato sostiene —el banco no distingue registro de vigencia—, y eso cambia
   **qué significan las cifras**, no cómo están redactadas; tanto, que lo he
   subido a deuda 27 y alcanza a H2, que ya está fusionado. `CLAUDE-R2-003`
   dice que la ficha afirma «E3 se comporta exactamente como antes» y existe un
   tercer caso donde no. Las dos son afirmaciones falsas, no estilo.

## Criterio de parada, decidido ahora

Si tras la corrección de la ronda 2 la ronda 3 trae **hallazgos no marcados
como goteo** que dejen el par sin mejorar `(2, 4)`, **se para** y se registra el
estado para decisión del propietario. No se reanuda por segunda vez apelando al
mismo argumento: un argumento que sirve dos veces deja de ser un argumento y
pasa a ser una costumbre.
