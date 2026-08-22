# Sirius 0.2 · ADR-002 · De once a cinco, y por qué paro ahí

> **SUPERADO por `SIRIUS_0.2_ADR_002_DE_ONCE_A_UNA_v1.0.md`.** **Su recomendacion era parar en cinco omisiones criticas, y estaba equivocada.** Faltaba una via que no se habia mirado: la peticion declara su propio proposito. Con ella quedan en una. El analisis de las tres salidas que aqui se examinan sigue siendo valido.


**Estado:** evidencia dentro de ADR-002. No abre ADR nuevo. PR #117 sigue abierta y sin fusionar.

**Cierra** la línea de las once omisiones críticas que dejó abierta
`SIRIUS_0.2_ADR_002_LA_REGLA_CONFIRMADA_v1.0.md`.

---

## Lo medido (corrida v0.5)

| | aciertos | completas | trozos | de más | **críticos perdidos** |
|---|---|---|---|---|---|
| búsqueda sola | 24/47 | 24/31 | 64/81 | 29 | **11** |
| filtro + regla | **30/47** | 20/31 | 53/81 | 10 | **11** |
| **categoría + filtro + regla** | 29/47 | **22/31** | **59/81** | 13 | **5** |

La pregunta abierta era si la categoría y la regla se estorbarían: la categoría trae
**más** elementos críticos a propósito, y la regla los conserva **todos**. Podían pelearse.

**No se pelean.** La combinación cuesta **un** acierto exacto y devuelve **seis datos críticos**
que antes se perdían. También sube las respuestas completas (20 → 22) y los trozos hallados
(53 → 59). El ruido sube de 10 a 13, no a los 37 que daba la categoría sin filtro: el filtro
absorbe casi todo lo que la categoría añade.

Un acierto exacto a cambio de seis datos críticos no es una decisión difícil.

---

## Las cinco que quedan, y qué son

| caso | faltan | causa |
|---|---|---|
| `N1-33` | `DECISION:3` | la pregunta dice **«límite de gasto»**, el dato dice **«presupuesto máximo»** |
| `N1-30` | `MEMORIA:1` | la pregunta dice **«preferencia de redacción»**, el dato **«prefiere que redactes»** |
| `N1-34` | 3 elementos | «Prepara el contexto de planificación de Alfa» no comparte palabra con ninguno |

No son el mismo agujero que las seis anteriores. Aquellas eran de **indexación** —la palabra
buscada no estaba escrita en ninguna parte y se podía escribir—. Estas son de **vocabulario**:
la palabra existe, pero es otra.

---

## Las tres salidas, examinadas

### 1. Devolver todas las críticas del proyecto en consultas amplias — **refutada por el banco**

Parecía razonable, y `RF-24` casi la respalda. Pero en **los tres casos** las críticas esperadas
son un subconjunto estricto de las críticas del proyecto: la regla metería `DECISION:10` y
`MEMORIA:25` donde no se esperan — dos elementos de más en `N1-34`, dos en `N1-30`, cuatro en
`N1-33`.

Y hay un problema peor: distinguir «consulta amplia» de «consulta estrecha» exige un umbral, y ese
umbral solo se puede elegir mirando estos casos. Eso es fijar la medida sobre el resultado.

### 2. La ampliación escrita por el modelo — **recupera una de las cinco**

Medido en la corrida v0.2: para `DECISION:3` el modelo escribió *«¿Cuál es el límite de gasto para
este proyecto?»*, que es exactamente el sinónimo que falta, y `N1-33` pasa de 0/1 a 1/1. `N1-30` y
`N1-34` no se mueven.

Cuesta **dos llamadas al modelo por cada dato guardado** —194 para este canon— y metió 11 elementos
de basura en ese mismo caso. Una omisión menos por ese precio.

### 3. Una lista de sinónimos escrita a mano — **no se hace**

Escribir «presupuesto = límite de gasto» ahora, sabiendo que ese es justo el caso que falla, es
ajustar el sistema al banco. Funcionaría aquí y no fuera de aquí, y además dejaría de poder medirse.

---

## Recomendación: parar aquí

De once se cerraron seis con una pieza **determinista, sin modelo y sin coste**, que se regenera
sola desde el canon. Las cinco que quedan valen, entre las opciones examinadas, o una omisión menos
a cambio de 194 llamadas por guardado, o un ajuste al banco que no sobrevive fuera de él.

Lo honesto es dejarlas escritas, con su causa y su precio, y decidirlas cuando haya un motivo que no
sea «quedan cinco».

---

## Lo que queda hecho

- **Datos críticos perdidos: de 11 a 5.**
- Aciertos exactos: de 24 a 29 de 47.
- Ruido: de 29 elementos de más a 13.
- Y una garantía por construcción: el filtro no puede dejar la cobertura crítica peor que la
  búsqueda.

Adoptarlo en Sirius sigue exigiendo que Ollama esté arrancado, y esa decisión es del responsable.
La parte de la categoría, en cambio, **no necesita modelo**: funciona sola.
