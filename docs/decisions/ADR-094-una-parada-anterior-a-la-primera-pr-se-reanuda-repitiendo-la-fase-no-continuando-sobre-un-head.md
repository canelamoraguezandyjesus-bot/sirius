# ADR-094 — Una parada anterior a la primera PR se reanuda repitiendo la fase, no continuando sobre un head

- Estado: PROPUESTO
- Fecha: 2026-08-25
- Aprobación: la fusión de la PR por el propietario
- Contexto: H-23, incidencia #337. Cierra el defecto medido sobre la #333
- Relacionadas: ADR-030 (reanudar sin cirugía manual), ADR-035 (la orden
  `continua`), ADR-002 (la automatización no edita `.github/**`), ADR-001

## Contexto y problema

Un bloque que se detiene **antes de crear ninguna rama ni PR** quedaba muerto.
Las dos vías de reanudación fallaban, cada una por su motivo, y las dos están
medidas sobre la incidencia **#333** del 25-08-2026:

**Vía 1 — reponer la etiqueta de activación.** Vuelve a bloquear en el acto:

```
Implementar bloque Sirius · run 32877801973 · conclusion: failure
  paso 7  «Consumir el evento y marcar en curso»  -> failure
```

**Vía 2 — la orden `continua`.**

```
🛑 No he podido reanudar el ciclo
No he encontrado ninguna PR asociada a esta incidencia, así que no puedo
saber sobre qué head autorizas continuar.
```

**Y la #333 se había detenido bien.** Vio que completar su encargo exigía tocar
`.github/**`, que ADR-002 le prohíbe, y en vez de entregar la mitad fácil —«una
vuelta completa falsa», sus palabras— no escribió una línea.

Ahí está el daño de fondo, y no es la incomodidad: **si la única salida de la
parada temprana es que la incidencia muera, el sistema castiga exactamente la
conducta que quiere.** Con el tiempo eso enseña a no pararse, que es lo contrario
de lo que todo este repositorio persigue.

`continua` no estaba mal escrita. Está diseñada para reanudar un ciclo
revisión–corrección **que ya tiene PR**: necesita un head sobre el que el
propietario autorice continuar, y eso es coherente con ADR-035. Lo que nadie
previó es una parada anterior a la primera PR, porque hasta ese día ninguna
incidencia se había detenido tan pronto.

## Criterio de parada (escrito ANTES de decidir)

**(a)** Si el arreglo obliga a **inventar un head** —vacío, un cero, el de la
rama base— se para. El head existe para dejar escrito SOBRE QUÉ se autorizó
continuar; uno falso convierte el historial, que es lo único que después dice
qué se permitió, en algo que miente.

**(b)** Si el arreglo hace que una reanudación **perdone rondas que sí contaban**,
se para. `sirius-convergence-reset` mueve el listón de la convergencia, y un
ciclo de verdad estancado podría correr para siempre.

**(c)** Si el arreglo **abre la puerta a reanudar a ciegas** —sin saber qué fase
repetir— se para. Reanudar la fase equivocada es peor que no reanudar.

## Decisión

Sin PR, `continua` deja de morir y pasa a autorizar un **reinicio**: se repite
desde cero la fase que se detuvo.

Tres piezas, y las tres salen de los criterios de arriba:

1. **Ningún head, y un marcador propio.** Se publica
   `<!-- sirius-restart-sin-pr:<issue>:<run> -->`, que no lleva head porque no
   hay versión sobre la que continuar (criterio a). No se reutiliza
   `sirius-convergence-reset` ni `sirius-resume-stop`: los dos llevan head, y los
   dos autorizan otra cosa.

2. **No se perdona ninguna ronda** (criterio b). Sin PR no hubo rondas que
   contar, así que el listón de convergencia no se toca.

3. **La fase se LEE del historial, nunca se supone.** Y ésta es la mitad que no
   se ve leyendo el código: hoy `sirius:blocked-decision` vuelve **siempre** a
   `sirius:repair-requested`, porque esa parada la emite la política de
   convergencia y ésa siempre para al corrector. **Sin PR, eso manda el trabajo
   al corrector, que se detiene en el acto por «sin-pr»**: sería cambiar una
   parada muda por otra, y encima con aspecto de haber funcionado. Sin PR la
   fase se lee del marcador de veredicto publicado, igual que ya se hacía para
   `failed-safely`; y si no hay marcador, se bloquea y se dice (criterio c).

## Comprobación que la sostiene

Las pruebas **ejecutan el guion de verdad** contra un `gh` simulado y miran qué
etiquetas quedan puestas. No se lee el fichero: ese techo ya lo documentó
`test_reanudar_ejecutando_el_guion.py` en su cabecera, cuando una mutación de
control pasó en verde **dos veces** porque el nombre buscado seguía apareciendo,
primero en un comentario y luego en un mensaje de error.

**Vistas FALLAR contra el guion sin el arreglo**, con el mensaje original:

```
FAILED test_una_parada_sin_pr_reactiva_la_fase_que_se_paro
FAILED test_una_parada_sin_pr_publica_un_permiso_QUE_NO_MIENTE
FAILED test_una_parada_sin_pr_NO_manda_el_trabajo_al_corrector
3 failed, 14 passed
  -> 'No he encontrado ninguna PR asociada a esta incidencia, así que no
      puedo saber sobre qué head autorizas continuar.'
```

Una cuarta prueba —`test_sin_pr_y_sin_saber_que_fase_se_paro_no_se_inventa_ninguna`—
**pasa con las dos versiones a propósito**, y conviene decirlo para que nadie la
lea como vacua: no fija comportamiento nuevo, protege contra la sobrecorrección
de abrir tanto la puerta que se reanude a ciegas.

## Consecuencias

**La parada temprana deja de ser una condena.** Un bloque que se detiene al ver
un límite de permisos, o cualquier otra cosa que no puede resolver, ya se puede
devolver al ciclo con una orden.

**Un reinicio y una continuación dejan de parecerse en el historial**, que es
donde importa: llevan marcadores distintos y dicen cosas distintas. Quien audite
después puede separar «se autorizó continuar sobre este commit» de «se autorizó
empezar de nuevo».

**Lo que esto NO hace, y hay que decirlo:** no reduce las paradas tempranas ni
las hace menos probables. Solo deja de castigarlas. La causa de la #333 —un
encargo que pedía tocar ficheros prohibidos— sigue existiendo, y su arreglo es
otro: repartir mejor el trabajo, que es de lo que habla ADR-089.

**Y queda un hueco conocido**: si la parada temprana no publicó ningún marcador
de veredicto con su rol, sigue haciendo falta aplicar la etiqueta a mano. Se
prefiere eso a adivinar (criterio c), pero es cirugía manual, que es justo lo que
ADR-030 vino a eliminar.

## Alternativas descartadas y por qué

- **Reutilizar `sirius-resume-stop` con el head vacío.** Criterio (a).
- **Reutilizar `sirius-convergence-reset`.** Criterio (b): borraría el listón sin
  que nadie lo hubiera pedido.
- **Una orden nueva, distinta de `continua`.** Descartada por coste de uso: son
  dos palabras que el propietario tendría que recordar y distinguir, para una
  diferencia que el propio sistema puede deducir mirando si hay PR. La orden
  sigue siendo una, y el guion decide qué significa.
