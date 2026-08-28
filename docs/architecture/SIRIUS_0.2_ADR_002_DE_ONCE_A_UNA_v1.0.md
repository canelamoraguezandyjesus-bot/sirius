# Sirius 0.2 · ADR-002 · De once datos críticos perdidos a uno

**Estado:** evidencia dentro de ADR-002. No abre ADR nuevo. PR #117 sigue abierta y sin fusionar.

**Cierra** la línea de las omisiones críticas. Sustituye la recomendación de
`SIRIUS_0.2_ADR_002_DE_ONCE_A_CINCO_v1.0.md`, que decía parar en cinco: paraba antes de tiempo.

---

## El recorrido, medido

| | exactas | completas | trozos | de más | **críticos perdidos** |
|---|---|---|---|---|---|
| la búsqueda tal cual | 24/47 | 24/31 | 64/81 | 29 | **11** |
| + el filtro con la regla de las críticas | **30/47** | 20/31 | 53/81 | 10 | **11** |
| + la categoría buscable | 29/47 | 22/31 | 59/81 | 14 | **5** |
| **+ la siembra al ensamblar contexto** | 29/47 | **23/31** | 63/81 | 21 | **1** |

Contra la búsqueda con la que se empezó: **cinco respuestas exactas más, ocho elementos de basura
menos y diez datos críticos que ya no se pierden**, con prácticamente la misma cobertura —63 trozos
frente a 64—.

---

## Las tres piezas, y qué vale cada una

### 1. La regla de las críticas — **medida**

> Si el modelo se queda con algunas, no puede tirar una crítica. Si dice que ninguna responde, se
> respeta entero.

Se predijo antes de escribirla y salió clavada: 30/47 con las once omisiones de la línea base en vez
de quince. Está en el código, no en una instrucción, y por eso se cumple siempre.

### 2. La categoría buscable — **medida, y sin modelo**

La pregunta nombra la categoría del dato —«restricciones esenciales»— y la categoría no está en el
texto: está en la criticidad que el canon ya declara. Indexarla cierra `N1-02` y `N1-31` enteros.

Es determinista, se regenera sola desde el canon y **no necesita Ollama**. Se reproduce con
`python -m experiments.adr002.lateral.medir_categoria`.

### 3. La siembra al ensamblar contexto — **no validable con este banco**

Si la petición **declara** que ensambla el contexto de un proyecto, entran las restricciones
críticas de ese proyecto. Preparar un contexto sin sus restricciones es exactamente el fallo que
`B04-RF-24` prohíbe.

**Y aquí toca el aviso.** Esto se escribió *después* de ver qué casos fallaban, y los dos únicos
casos del banco con ese propósito son justo esos dos. El banco **ya no puede confirmarla de forma
independiente**: la confirmaría por construcción. Se sostiene por diseño —cualquiera escribiría esta
regla para una memoria de verdad— y no por medida. Hay una prueba que deja escrito ese hecho para
que nadie lea las cifras como una validación.

---

## Lo que costó

El ruido sube de 14 a 21 elementos de más, aunque sigue por debajo de los 29 de la búsqueda sola. La
causa está en la última línea de la corrida: **la regla devolvió 22 críticas que el modelo tiraba**.
El modelo intenta descartar las restricciones sembradas y la regla se las devuelve a la fuerza. Es
la regla funcionando, y cuesta precisión.

---

## Lo único que sigue faltando

**`N1-30`**, un elemento: `MEMORIA:1`, «El usuario prefiere que redactes en tono directo y sin
adornos». La pregunta dice «preferencia de **redacción**» y el dato dice «prefiere que
**redactes**». Sustantivo contra verbo: el recorte de sufijos no los une.

Haría falta un diccionario, y escribirlo ahora sabiendo cuál es el caso que falla es ajustar el
sistema al banco. Queda escrito, no escondido.

---

## Lo que hace falta para meterlo en Sirius

**Ollama arrancado**, para la mitad del filtro. `AGENTS.md` obliga a detenerse antes de introducir
otro proceso, y esto lo es: la decisión es del responsable del proyecto.

**La categoría buscable no necesita modelo.** Va sola, y ya lleva las omisiones críticas de once a
cinco por sí misma.
