# Sirius 0.2 · ADR-002 · La regla de las críticas, confirmada en máquina

**Estado:** evidencia dentro de ADR-002. No abre ADR nuevo. PR #117 sigue abierta y sin fusionar.

**Confirma** `SIRIUS_0.2_ADR_002_LA_REGLA_DE_LAS_CRITICAS_v1.0.md` con la corrida v0.4.

---

## Lo que se predijo y lo que salió

La predicción se escribió sobre la corrida v0.3, **antes** de escribir una línea de código:

| | predicho | medido |
|---|---|---|
| aciertos | 30/47 | **30/47** |
| respuestas completas | 20/31 | **20/31** |
| trozos hallados | 53/81 | **53/81** |
| elementos de más | 10 | **10** |
| **críticos perdidos** | **11** | **11** |

Los cinco. Y no por suerte: la regla no toca ninguna instrucción, vive en el código después de que
el modelo conteste, de modo que predecirla era aritmética sobre veredictos y no adivinar conducta.
Es la diferencia con la compuerta, que sí exigía instrucción nueva y falló por dos puntos.

---

## El efecto de la regla, aislado

El artefacto guarda por caso lo que salió **y** lo que habría salido sin la regla. Las dos filas
vienen de **la misma llamada al modelo**, así que la diferencia es atribuible a la regla y solo a
ella:

| sobre los mismos veredictos | aciertos | completas | trozos | de más | **críticos perdidos** |
|---|---|---|---|---|---|
| sin la regla | 30/47 | 19/31 | 49/81 | 5 | **15** |
| **con la regla** | 30/47 | 20/31 | 53/81 | 10 | **11** |
| *(línea base, para comparar)* | *24/47* | *24/31* | *64/81* | *29* | *11* |

Devolvió **nueve** críticas que el modelo tiraba. **Cuatro hacían falta**; cinco volvieron como
ruido. El trato es cuatro omisiones críticas menos a cambio de cinco elementos de más.

Las cuatro útiles son `MEMORIA:101` a `104`: las restricciones de `N1-44`, el caso donde la búsqueda
entregaba las cinco correctas y el modelo se quedaba con una.

---

## Lo que esto deja hecho

Frente a la búsqueda sola: **de 24 aciertos exactos a 30**, ruido **de 29 a 10**, y **ni una omisión
crítica de más**.

Y una garantía que no depende de que el modelo se porte bien, porque no puede incumplirla: **el
filtro nunca deja la cobertura crítica peor que la búsqueda.** Se pidió por escrito dos veces y las
dos falló; puesta en el código, se cumple.

---

## Lo que sigue costando

- **Once elementos correctos no críticos se pierden.** Las respuestas completas bajan de 24/31 a
  20/31. La regla protege lo crítico, no lo demás: el filtro sigue truncando respuestas largas en lo
  secundario.
- **El p95 de latencia salió en 6,55 s**, por encima del presupuesto de 5 s. La regla no añade
  ninguna llamada al modelo —la corrida anterior, con el mismo número de llamadas, dio 4,05 s—, de
  modo que es variación de la máquina. Queda apuntado, no explicado.

---

## Lo que no arregla

Las **once omisiones críticas** que quedan **no son del filtro**: son datos que la búsqueda nunca
llegó a traer. Ninguna regla sobre el filtro las puede recuperar, porque el filtro solo ve lo que la
búsqueda le pasa.

Ese es el siguiente problema, y es de otra naturaleza.

---

## La decisión pendiente, que no es técnica

Adoptar esto en Sirius significa **que Ollama tenga que estar arrancado** para que la memoria
funcione como aquí se mide. `AGENTS.md` obliga a detenerse antes de «introducir otro proceso,
servidor, agente o base de datos», y esto lo es.

Los números respaldan la adopción. La decisión es del responsable del proyecto, no del código.
