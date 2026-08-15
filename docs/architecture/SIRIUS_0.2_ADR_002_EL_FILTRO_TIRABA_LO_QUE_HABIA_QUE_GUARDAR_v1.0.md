# Sirius 0.2 · ADR-002 · El filtro tiraba lo que había que guardar

> **SUPERADO por `SIRIUS_0.2_ADR_002_EL_QUE_ELIGE_SE_QUEDA_CON_UNO_v1.0.md`.** La correccion de polaridad que propone es correcta y sigue en el codigo, pero **no era la causa principal**: al aplicarla, las omisiones criticas subieron de doce a diecisiete. La causa real esta en el documento sucesor.


**Estado:** evidencia dentro de ADR-002. No abre ADR nuevo. PR #117 sigue abierta y sin fusionar.

**Corrige** el defecto que dejó a la vista la primera medición del modelo local
(`resultado_modelo_local.json`, congelada, commit `e93d4e0`).

---

## Qué pasó

La primera medición del modelo local **pasó el listón** que estaba puesto por escrito antes de
medir: los aciertos exactos subieron de 24 a 30 sobre 47, y la basura bajó de 29 elementos de más a
5. Pero traía una mancha, y era la peor posible:

> el filtro se llevó por delante **14 elementos correctos**, y dejó **una omisión crítica más** que
> la búsqueda de siempre —12 contra 11—.

Perder un dato crítico en silencio es exactamente lo que `B04-RF-24` prohíbe. Así que la pregunta
no era si el filtro servía, sino **por qué tiraba lo que no debía**.

---

## Por qué pasó

No fue el modelo portándose mal. Fue **una regla mía, mal escrita**, que el modelo obedeció bien.

La instrucción del filtro decía, literalmente:

> *«una frase que niega o prohíbe algo no responde a una pregunta sobre lo que sí se hace o se
> permite, y al revés»*

Eso es **falso**, y el propio banco lo dice. En `round/metrics.py`, la función que puntúa la
polaridad cita el §6.1:

> *«Fundir ambas es fallo; recuperarlas **marcadas y distinguidas** es correcto»*

La polaridad es un requisito de **marcar**, no de **excluir**. Lo que `RF-19` prohíbe es entregar
una prohibición como si fuera un permiso. No prohíbe entregarla.

### Y el banco lo pide a la cara

Cinco casos con contenido esperan que salga al menos una prohibición. Dos de ellos son, palabra por
palabra, preguntas de permiso cuya respuesta correcta es una prohibición:

| pregunta del banco | lo que el banco espera | ¿crítico? |
|---|---|---|
| ¿Puedo usar vuelos con escala? | No uses opciones de vuelo con escala. | sí |
| ¿Usar PostgreSQL? | No usar PostgreSQL en este proyecto. | sí |
| ¿Qué restricciones de transporte tengo? | En este viaje no se alquila coche. | sí |

**Los tres elementos negativos en juego están marcados como críticos por el canon.** De ahí la
omisión crítica de más: la regla mandaba tirar justo lo que hay que entregar, y encima lo importante.

El mismo error estaba puesto dos veces. También en el examen que la ingesta le pasa a sus propias
preguntas, y ahí se le ve actuar en los datos guardados: para «En este viaje no se alquila coche» el
modelo escribió «¿se puede llevar auto por el viaje?» y «¿hay límite en el uso de coche?» —las dos
buenas— y el examen **las tiró las dos**, dejando indexadas dos frases que el dato no dice.

---

## Qué se ha cambiado

1. **La regla, en los dos sitios.** Ahora dice lo contrario y lo dice con ejemplo: una prohibición
   sí responde a la pregunta de si eso se puede hacer, y si hay dos frases opuestas sobre lo mismo,
   se devuelven **las dos**. La regla del tiempo —lo derogado no responde a lo vigente y al revés—
   se queda, porque esa sí es correcta.

2. **El arnés publica el daño junto al beneficio.** Cada corrida guarda ahora, caso por caso, qué
   entró al filtro, qué se quitó, y cuánto de lo quitado era correcto o crítico. Este defecto se
   encontró leyendo el banco a mano porque el artefacto solo publicaba totales, y eso no puede
   volver a pasar: con totales no se diagnostica nada.

3. **Falta una corrida y ahora se hace.** La ampliación cuesta dos llamadas al modelo por cada dato
   guardado —194 para este canon— y a solas salió **peor** que no hacer nada (23 contra 24). Se
   añade una cuarta corrida, **el filtro sin la ampliación**, para saber si esa mitad cara se gana
   su sitio o sobra.

4. **La huella del modelo.** Salía «desconocida» porque la pedía donde no está. El identificador de
   los pesos vive en el catálogo del servidor, no en la ficha del modelo. Sin él no se puede
   regenerar un derivado, que es lo que `TOL-207` exige.

5. **Los artefactos medidos ya no se pisan.** La medición se niega a escribir encima de un resultado
   que ya existe, y lo comprueba **antes** de medir, no después de gastar diez minutos de gráfica.

---

## Lo que esto no cambia

El banco, las métricas, el denominador —47 adjudicables— y el listón preinscrito son **los mismos**.
El §8.1 prohíbe cambiar la medición después de ver los resultados; aquí no se ha cambiado, se ha
ampliado con una corrida más y con detalle por caso. Las cifras de las corridas 1 a 3 se comparan
con las publicadas.

La corrida v0.1 **se conserva entera**. Esto no la sustituye: la explica.

---

## Lo que falta por saber

Si la regla corregida recupera los elementos correctos sin devolver la basura. Eso **no se puede
medir sin ejecutar el modelo**, y el modelo corre en la máquina del responsable, no aquí.

Hasta que esa corrida exista, lo escrito arriba es un defecto identificado y corregido en el
código, no un resultado.
