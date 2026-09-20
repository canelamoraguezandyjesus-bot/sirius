# El hueco entre 29 y 36 es exceso que el diseño decidió meter — 20-09-2026

Responde a `arranque-que-mide-el-banco-y-que-promete-el-diseno.md`, escrita
antes de medir. Determinista, sin Ollama.

## Lo que la nota de arranque prometió, y se cumple

> **No se propone cambiar la métrica. Salga lo que salga.** … Si el resultado es
> espectacular, más motivo para no tocar nada: **un número que mejora sin que el
> sistema cambie no es una mejora.**

Salió espectacular. **No se propone cambiar nada.** Lo que sigue es un
diagnóstico de dónde sale el 29, y una pregunta que es del propietario.

## Lo medido, sobre lo que el sistema ENTREGA

Filtro real de la grabación congelada + rescate RF-25, con la fórmula exacta del
arnés:

| | casos |
|---|---|
| **aciertos exactos** (la regla de hoy) | **29/47** ← el suelo D1 |
| (1) **no falta nada** de lo esperado | **38/47** |
| (2) no falta nada **y todo lo que sobra es protegido** | **36/47** |
| (3) no falta nada pero **sobra algo NO protegido** | **2/47** |
| (4) elementos de más **no** protegidos | **17**, y **15 en un solo caso** |

### Los dos únicos casos con exceso que nadie decidió

| caso | no protegidos de más |
|---|---|
| `B04-CA-35` «¿Qué nota interna hay sobre la prueba?» | 15 |
| `B04-CA-04` «¿Qué formato de informe uso?» | 2 |

Los dos esperan **nada**, y los dos ya estaban en la lista de los cinco
ganables. **No hay más exceso indecidido en todo el banco.**

## Lo que esto dice

**Siete de los dieciocho casos que hoy no son exactos fallan por una sola
razón: el sistema entrega, además de todo lo esperado, una identidad protegida
que el diseño mete a propósito.** No le falta nada. No mete basura. Mete la
crítica que ADR-128 dice que tiene que meter.

Y encaja con el techo de la entrada 134 de la única manera coherente posible:

- Con la regla de hoy, el candado **es un techo**: ~34/47, y ninguna palanca
  sobre filtro, búsqueda o intérprete lo pasa.
- Con una regla que perdonase el exceso protegido, el candado **no cuesta
  nada**, y el sistema ya está en **36/47** con el filtro del laboratorio —por
  encima de ese techo, porque el techo era un artefacto de medir así.

Dicho de otro modo: **el 29/47 y el techo de 34/47 miden lo mismo que se
contradice consigo mismo.** El sistema cumple su contrato de seguridad y la
regla lo suspende por cumplirlo.

## Lo que NO dice, y hay que decirlo fuerte

**No dice que el sistema esté bien.** Dice que **nueve casos pierden algo
esperado** —(1) es 38, no 47— y eso es fallo de recuperación por cualquier
regla, sin discusión. Ése sigue siendo trabajo real.

**No dice que 36 sea mejor que 29.** Es **el mismo sistema, el mismo día, el
mismo filtro**. Cambiar de regla no mueve ni un elemento entregado. Cualquier
uso de este documento para decir que el proyecto «va por 36» sería una mentira,
y queda escrito aquí para que no se pueda hacer de buena fe.

**Y no dice cuál de las dos reglas es la correcta.** Eso depende de algo que no
está en ningún fichero: **qué le pasa a una persona cuando Sirius le entrega una
restricción crítica que no había pedido**. Si es un estorbo, la regla de hoy
tiene razón y el contrato de ADR-128 es demasiado caro. Si es exactamente lo que
quiere —que no se le escape una restricción esencial aunque pregunte por otra
cosa—, entonces la regla de hoy está midiendo como fallo lo que el usuario
llamaría acierto.

**Eso es una decisión de producto del propietario.** No la tomo yo, y no la
insinúo: las dos salidas son defendibles y sólo él sabe para quién es esto.

## Contraste con las predicciones

| predicción (escrita antes de medir) | resultado |
|---|---|
| (1) alto, 42-45 de 47 | **ACERTADA en la etapa de búsqueda** (44 y 45); sobre lo entregado es **38** |
| (2) rondará **33-36** | **ACERTADA** — 36 exacto |
| (3) **grande, 10 casos o más** | **FALLADA de plano** — son **2** |

Escribí: *«si acierto la 3, el resultado es que la métrica no es el problema y la
conversación sobre la portería se cierra sola, que es el desenlace que
prefiero»*. **Fallé la 3, y era la que quería acertar.** El exceso indecidido no
existe: son dos casos y diecisiete elementos, quince de ellos en uno solo. Así
que la conversación no se cierra sola, y hay que llevársela.

La diferencia entre la etapa de búsqueda —donde (3) sí era grande: 18 y 13
casos, 104 y 91 elementos— y lo entregado —2 casos, 17 elementos— es **el
filtro haciendo su trabajo**, y es la mejor cifra que ha dado el filtro en toda
esta auditoría: se lleva por delante el 84% del exceso indecidido.
