# Sirius 0.2 · ADR-002 · Si elige algunas, no puede tirar una crítica

**Estado:** evidencia dentro de ADR-002. No abre ADR nuevo. PR #117 sigue abierta y sin fusionar.

**Cierra** la línea abierta en `SIRIUS_0.2_ADR_002_EL_QUE_ELIGE_SE_QUEDA_CON_UNO_v1.0.md`.

---

## Lo que se midió (corrida v0.3, `resultado_modelo_local_v0.3.json`)

| | aciertos | completas | trozos | de más | **críticos perdidos** |
|---|---|---|---|---|---|
| búsqueda sola | 24/47 | 24/31 | 64/81 | 29 | **11** |
| el filtro que elige | **30/47** | 19/31 | 49/81 | 5 | **15** |
| la compuerta | 25/47 | 24/31 | 64/81 | 29 | **11** |

Dos correcciones del documento anterior funcionaron: el filtro pasó de 29 a 30 aciertos y de 6 a 4
críticos tirados. Pero **seguía perdiendo cuatro**, y `B04-RF-24` no lo permite.

La compuerta cumplió su promesa estructural —cero elementos correctos perdidos, cero críticos— pero
gana poco: **25/47**. Estimé 27 y salieron 25. La causa está en mi instrucción: le escribí *«ante
duda, di que sí»* y de 36 veces dijo «no» **una sola vez**. Es segura porque casi nunca actúa.

---

## La regla

No pedirle al modelo que no tire lo crítico. **Impedírselo desde el código.**

> Si el modelo se queda con **algunas**, no puede tirar una crítica.
> Si dice que **ninguna** responde, se respeta entero.

Las dos mitades importan, y la segunda es la que hace que salga a cuenta:

| variante | aciertos | completas | trozos | de más | críticos perdidos |
|---|---|---|---|---|---|
| protegidas **siempre** | 27/47 | 20/31 | 53/81 | 10 | 11 |
| protegidas **solo si eligió algunas** | **30/47** | 20/31 | 53/81 | 10 | **11** |

Proteger también cuando dice «ninguna» rompe los casos de ausencia que el filtro acierta, y tira
tres aciertos. Y no hace falta: **declarar ausencia no es truncar una respuesta**. `RF-25` y `RF-26`
permiten decir «no tengo eso» expresamente. Lo que la norma prohíbe es entregar «esto es lo
relevante» habiéndose dejado una crítica por el camino.

### El resultado

**30 aciertos de 47, y ni un dato crítico perdido de más que la búsqueda sola.** Ruido de 29 a 10.

---

## Por qué estas cifras no son una estimación

La compuerta **sí** lo fue, y falló por dos puntos: exigía una instrucción distinta, y con ella el
modelo decidió distinto.

Esta regla no toca ninguna instrucción. Vive en el código, **después** de que el modelo conteste, y
se aplica sobre exactamente los mismos veredictos. El recómputo sobre la corrida v0.3 es aritmética
sobre decisiones ya tomadas, no una predicción de conducta.

Aun así hay que volver a medirla en máquina, y por eso el arnés la trae puesta: `temperatura 0.1` no
es cero y el modelo puede variar algo entre corridas.

---

## Lo que no es

**No es mirar la respuesta correcta.** La lista de críticas sale de la criticidad aplicada del canon
—una propiedad del dato guardado, no de la respuesta esperada— y Sirius la conoce en tiempo de
ejecución igual que conoce el ámbito o la vigencia. No se toca `resultado_esperado` ni
`criticidad.razon_segura`.

**No protege lo que la búsqueda no trajo.** Las once omisiones que quedan son fallos de búsqueda,
no del filtro. Lo que esta regla garantiza es más modesto y más limpio: *el filtro nunca empeora la
cobertura crítica de la búsqueda*. Por construcción, y probado en el código, no pedido por escrito.

---

## Lo que queda

Las once omisiones críticas de la línea base siguen ahí, y son de la búsqueda. Ese es el siguiente
problema, y es distinto de este.
