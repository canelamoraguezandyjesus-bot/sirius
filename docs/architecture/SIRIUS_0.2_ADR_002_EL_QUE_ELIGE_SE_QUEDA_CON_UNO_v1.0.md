# Sirius 0.2 · ADR-002 · El que elige se queda con uno

**Estado:** evidencia dentro de ADR-002. No abre ADR nuevo. PR #117 sigue abierta y sin fusionar.

**Continúa** `SIRIUS_0.2_ADR_002_EL_FILTRO_TIRABA_LO_QUE_HABIA_QUE_GUARDAR_v1.0.md`, cuya corrección
**empeoró** las cifras. Esto explica por qué y qué se hace en su lugar.

---

## Lo que salió mal

Arreglé la regla de polaridad y las omisiones críticas subieron de 12 a 17. La corrección de la
polaridad era correcta —el banco la respalda— pero **no era la causa principal**. La causa se ve
ahora porque la medición guarda el detalle caso por caso.

---

## La causa, en tres casos

| caso | lo que pide | entró al filtro | quedó |
|---|---|---|---|
| **N1-44** | Restricciones esenciales, máximo duro 5 | **las 5 correctas** | **1** |
| **N1-34** | Contexto de planificación de Alfa (10 elementos) | 10 | 3 |
| **N1-23** | La decisión de presupuesto actual **y cuál reemplazó** | las 2 | 1 (y la equivocada) |

En `N1-44` la búsqueda hizo su trabajo perfectamente: entregó exactamente los cinco elementos
correctos. El filtro se quedó con uno.

Los cinco textos son «Restricción esencial dispersa número 1 del expediente Gamma», número 2,
número 3… El modelo los ve casi idénticos y devuelve uno, como si fueran repeticiones.

**Once de los dieciséis elementos correctos perdidos salen de esos dos casos.** El daño crece con
el tamaño de la respuesta: el modelo trata una petición de lista como una pregunta de una sola cosa
y se queda con el candidato que más se parece.

Y en `N1-23` hay un fallo mío gemelo del de la polaridad: mi regla del tiempo decía «si preguntan
por lo vigente, lo derogado no responde». Pero esa pregunta pide **las dos**. Otra vez había escrito
una exclusión donde el banco pide las dos cosas.

---

## Y el beneficio no estaba donde yo creía

Separando los 47 casos entre los que esperan contenido y los que esperan que no salga nada:

| corrida | aciertos con contenido | aciertos de ausencia |
|---|---|---|
| búsqueda sola | 16/31 | 8/16 |
| el filtro que elige | 17/31 | **12/16** |

De los cinco aciertos que gana el filtro, **cuatro son casos en los que lo correcto era no devolver
nada**. Elegir cuáles aporta **uno**, y cuesta dieciséis elementos correctos y seis omisiones
críticas.

Es decir: el filtro no busca mejor. Sabe callarse. Y para eso no hace falta que elija.

---

## Lo que se hace en su lugar: la compuerta

Se le hace **una sola pregunta**: *¿hay aquí algo que sirva para responder?* Sí o no.

- Si dice **no**, no se devuelve nada. Ahí está toda la ganancia.
- Si dice **sí**, se devuelve la lista entera.

**No puede truncar una respuesta**, porque no decide elemento a elemento. Es una propiedad del
diseño, no una esperanza sobre el modelo, y está probada en el código: cinco restricciones entran,
cinco salen.

Recomputando sobre los veredictos que el modelo **ya dio** en la corrida v0.2:

| | exactos | respuestas completas | trozos | **críticos perdidos** |
|---|---|---|---|---|
| búsqueda sola | 24/47 | 24/31 | 64/81 | **11** |
| el filtro que elige *(medido)* | 29/47 | 19/31 | 48/81 | **17** |
| la compuerta *(estimado)* | 27/47 | 23/31 | 63/81 | **11** |

Dos aciertos exactos menos, a cambio de **seis datos críticos que no se pierden** y quince trozos de
respuesta que no se tiran. Para una memoria atada a `B04-RF-24`, no hay duda.

**Aviso importante:** la fila de la compuerta **no es una medición**. Es un recálculo sobre las
decisiones que el modelo tomó con la instrucción del otro. Con su propia instrucción puede decidir
distinto. Hay que medirla, y por eso las dos siguen en el código y se miden juntas.

---

## La ampliación se apaga

Medida dos veces, las dos por debajo de la línea base a solas —23 y 22 contra 24—. Y la corrida que
la aislaba lo zanjó: con ampliación 29 aciertos y 17 omisiones; sin ella, 29 y 17. **Idéntico.**

Cuesta dos llamadas al modelo por cada dato guardado, 194 para este canon. Deja de medirse por
defecto. Sigue entera detrás de `--con-ampliacion` para quien quiera reproducir aquello.

---

## Lo que esto no cambia

El banco, las métricas, el denominador —47 adjudicables— y el listón preinscrito son los mismos, y
la línea base se comprueba contra la publicada en cada corrida. Lo que cambia es **qué
configuraciones se ponen a prueba**, que es justo lo que un resultado debe cambiar.

Las corridas v0.1 y v0.2 se conservan enteras.
