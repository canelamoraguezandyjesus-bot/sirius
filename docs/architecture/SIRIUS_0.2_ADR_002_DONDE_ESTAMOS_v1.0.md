# Sirius 0.2 · ADR-002 · Dónde estamos

**Este es el documento de entrada.** Hay más de ciento treinta en esta carpeta; con leer este y los
cuatro que enlaza al final se sabe todo lo que hay que saber.

**Estado:** PR #117 abierta y sin fusionar. Sirius 0.1 productivo, intacto.

---

## Qué se estaba resolviendo

Sirius guarda todo lo que le dices. Eso nunca ha estado en duda y sigue sin estarlo.

Lo que ADR-002 tenía que resolver es otra cosa: **si lo guardado te llega a la mano cuando
preguntas**. La diferencia entre haber perdido el papel y tenerlo sin encontrarlo en el cajón.

Para medirlo hay un banco de 47 preguntas con respuesta conocida, con las reglas de puntuación
fijadas **antes** de medir nada.

---

## Dónde ha quedado

| | al empezar | ahora |
|---|---|---|
| **datos importantes que se pierden** | **11** | **1** |
| respuestas que salen clavadas | 24 de 47 | 29 de 47 |
| elementos de más («basura») | 29 | 21 |
| trozos de respuesta encontrados | 64 de 81 | 63 de 81 |

Lo que hay que leer de esa tabla: **encuentra prácticamente lo mismo que antes, con menos ruido, y
ha dejado de perder lo importante.**

### Y qué significa eso cuando lo usas

- **No se pierde nada de lo guardado.** Nunca. Lo que se mide es si sale al preguntar.
- **«Basura» no es información falsa.** Es que junto a lo que pides llega alguna nota de más:
  repartido entre 31 preguntas, menos de una por pregunta.
- **De todo lo que no encuentra, solo uno es algo marcado como importante.** El resto son notas
  corrientes.
- Cuando falla, falla **dándote de más**, no callándose algo. Está garantizado en el código.

---

## Las tres piezas construidas, y qué vale cada una

No valen lo mismo y no se mezclan en un número único a propósito.

### 1. La regla de las críticas — **medida y confirmada**

> Si el modelo se queda con algunas, no puede tirar una crítica. Si dice que ninguna responde, se
> respeta entero.

Está en el código, no en una instrucción al modelo. Se le pidió por escrito dos veces y las dos
falló; puesta en el código se cumple siempre. Se predijo antes de escribirla y salió clavada.

**Necesita Ollama arrancado.**

### 2. La categoría buscable — **medida, y sin modelo**

Las preguntas nombran la categoría del dato —«restricciones esenciales»— y la categoría no está en
el texto: está en la criticidad que el canon ya declara. Indexarla cierra dos casos enteros.

Determinista, se regenera sola, **no necesita Ollama**. Ella sola lleva las pérdidas de 11 a 5.

### 3. La siembra al ensamblar contexto — **no validable con este banco**

Si la petición declara que ensambla el contexto de un proyecto, entran las restricciones críticas de
ese proyecto.

**Aviso:** se escribió después de ver qué casos fallaban, y los dos únicos casos del banco con ese
propósito son justo esos dos. El banco ya no puede confirmarla por su cuenta. Se sostiene por diseño
—cualquiera la escribiría para una memoria de verdad— y no por medida.

---

## Lo que se probó y se descartó, con datos

| idea | veredicto |
|---|---|
| fusión híbrida de listas (RRF) | **inerte**: cifras idénticas en todos los puntos de operación |
| señal semántica con vectores | **no supera** la búsqueda por palabras, ni con un modelo de pago |
| ampliación escrita por el modelo al guardar | **no aporta**, y cuesta 194 llamadas por reconstrucción |
| compuerta de sí/no en vez de elegir | segura pero **casi inerte**: 25 y 26 de 47 |
| devolver todas las críticas del proyecto | **refutada por el propio banco** |

Tres de cada cuatro ideas se cayeron. Eso es lo normal y lo sano: una idea descartada en dos días
con datos no está dentro de Sirius fallando dentro de seis meses.

---

## Lo único que sigue faltando

**Un elemento.** Guardaste «prefiere que **redactes** en tono directo» y preguntas por «preferencia
de **redacción**». Sustantivo contra verbo.

Haría falta un diccionario de sinónimos, y escribirlo ahora sabiendo cuál es el caso que falla sería
ajustar el sistema al examen: funcionaría aquí y en ningún sitio más. Queda escrito, no escondido.

---

## Lo que queda por decidir, y es del responsable

Meter esto en Sirius. Son **dos decisiones**, no una:

- **La categoría buscable** no necesita nada. Se puede adoptar ya.
- **El filtro** exige que **Ollama esté arrancado** siempre. `AGENTS.md` obliga a detenerse antes de
  introducir otro proceso en el sistema, y esto lo es.

---

## Los cuatro documentos que hay que leer

1. `SIRIUS_0.2_ADR_002_DE_ONCE_A_UNA_v1.0.md` — el recorrido completo y qué vale cada pieza.
2. `SIRIUS_0.2_ADR_002_LA_REGLA_CONFIRMADA_v1.0.md` — la garantía que protege lo importante.
3. `SIRIUS_0.2_POR_QUE_SIEMPRE_FALLA_ALGO_v1.0.md` — qué se ha roto de verdad y qué no era un fallo.
4. `SIRIUS_0.2_ADR_002_LA_SEMANTICA_CERRADA_v1.0.md` — por qué los vectores no eran la respuesta.

Las seis mediciones están enteras en la raíz del repositorio, `resultado_modelo_local*.json`, y
ninguna se ha pisado. La evidencia que las analiza vive en `artifacts/adr002_round/`.

---

## Cómo se repite todo esto

```
.\scripts\medir_memoria.ps1
```

Comprueba Ollama, comprueba el entorno y mide. Y la parte que no necesita modelo:

```
uv run python -m experiments.adr002.lateral.medir_categoria
```
