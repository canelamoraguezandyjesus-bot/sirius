# SIRIUS 0.2 — ADR-002 · Fe de erratas 06: base vigente de `B v7` y aritmética de `E3` en `C v2`

**Versión:** 1.0
**Estado:** **ERRATA RECONOCIDA · APPEND-ONLY**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Cómo se encontró:** por la auditoría dirigida que la emisión de la ficha de
`ADR002-D` obliga a hacer sobre las fichas de las que hereda. No procede de
una auditoría general de ADR-002, y no abre ninguna.

**Ámbito exclusivo:** dos frases de dos fichas congeladas. **Este documento no
modifica ningún fichero, no emite ninguna ficha sucesora y no altera ninguna
huella.**

---

## 0. Qué declara esta errata

Dos fichas `CONGELADA` contienen, cada una, **una afirmación explicativa
inexacta**. En los dos casos:

- **los números, los árboles y las huellas son correctos**;
- lo inexacto es el **texto que los explica**;
- ninguna de las dos afecta a la identidad de su candidato, a su
  implementación, a su comportamiento ni a su aptitud para el benchmark.

**Las fichas no se reescriben.** Se conservan íntegras, con su contenido y su
huella, y esta fe de erratas registra la verdad observada **junto a** ellas,
en régimen append-only, que es el mecanismo que la regla 7 de custodia fija
para la evidencia ya publicada.

**Por qué no se emiten sucesoras.** La reaprobación conjunta de `A v5` y
`B v7` dispuso expresamente que **no se emiten `A v6` ni `B v8`**. Y emitir
una `C v3` para corregir una sola frase invalidaría la aprobación de `C v2`
—recién concedida sobre esta misma implementación— y obligaría a repetir las
ejecuciones hechas bajo ella, todo por un texto que no cambia ni un número.
La fe de erratas es el instrumento proporcionado, y es el que el repositorio
ya usó cinco veces.

---

## 1. Errata E-1 · `ficha_ADR002-B_v7.json` nombra como vigente una versión sustituida

### 1.1 Lo publicado

En `componentes[]`, entrada **«base funcional lexico-estructurada»**:

> **nombre:** `ADR002-A vigente (v3), por composicion`
> **version:** `arbol ceb4247c9fee913ae86d5203f199b19341f1c833 de adr002_a (sin cambios desde la v2 de A); ficha vigente A v3 con huella 427905a06f6c12666a09c73b8720e229f17eeef3`

### 1.2 Lo cierto

| Hecho | Comprobación |
|---|---|
| La ficha vigente de `ADR002-A` es la **v5** | `verify_cards --check`: `ADR002-A v5 · CONGELADA`; `v1`–`v4` constan `SUSTITUIDA` |
| Su huella canónica es `b5549a5a8e0f2fa4e791f64fbdb1c769938949be` | recomputada por el verificador |
| `A v3` quedó `SUSTITUIDA` | acta de reaprobación conjunta de `A v5` y `B v7` |
| La huella `427905a0…` es la que `A v3` tuvo **mientras estuvo `CONGELADA`** | el estado forma parte de la forma canónica: marcarla sustituida la recomputó a `5660dc4c7023bed6be1c7a87354efc5c45e478f1` |
| **El árbol citado es correcto y no cambia**: `ceb4247c9fee913ae86d5203f199b19341f1c833` | es el mismo subárbol `adr002_a` que declara `A v5` |

### 1.3 Por qué no afecta a la identidad de `B v7`

Lo que ata `ADR002-B` a su base **es el árbol**, no la etiqueta de versión. El
árbol citado es exactamente el de `A v5`, byte a byte, y por eso la
composición que `B v7` declara es la que realmente ejecuta. La cláusula de la
propia ficha —«si la base cambiara, cambiaría la huella de esta ficha»— sigue
cumpliéndose: la base **no** cambió.

Lo inexacto es la **etiqueta**: `B v7` se congeló en el mismo acto que
convirtió `A v5` en vigente, y su texto se quedó nombrando la versión anterior.

> **Léase, en `ficha_ADR002-B_v7.json`, «base funcional lexico-estructurada»:**
> **`ADR002-A` vigente = `v5`, huella `b5549a5a8e0f2fa4e791f64fbdb1c769938949be`, árbol `ceb4247c9fee913ae86d5203f199b19341f1c833` — el mismo árbol que la ficha ya declara.**

---

## 2. Errata E-2 · `ficha_ADR002-C_v2.json` explica mal una aritmética que declara bien

### 2.1 Lo publicado

En `extremo_a_extremo.fundamento`:

> «Cinco etapas conservan el limite de la base por composicion porque su camino
> es el suyo sin cambio; **`E3` sube de 3 ms a 8 ms**…»

### 2.2 Lo cierto

**`E3` no sube.** El límite local de `E3` en `ADR002-A` es **8 ms desde la
`v2`**, y `ADR002-C` declara exactamente ese mismo 8 ms.

| Ficha | Límite local de `E3` | Límite duro extremo a extremo |
|---|---|---|
| `A v1` | 5 000 000 ns | 20 050 000 ns |
| `A v2` … `A v5` | **8 000 000 ns** | 23 050 000 ns |
| **`C v2`** | **8 000 000 ns** | **23 050 000 ns** |

La aritmética declarada por `C v2` lo dice ya sin ambigüedad: su límite duro
es **idéntico** al de `A v5`. Si `E3` hubiera subido 5 ms, el total tendría que
haber subido 5 ms, y no sube. **Los números están bien; la frase que los
explica, no.** El valor `3 ms` no corresponde a ninguna versión de `ADR002-A`:
es un residuo de la derivación de la ficha, y esta errata lo declara como tal.

### 2.3 La explicación correcta

`ADR002-C` **absorbe su consulta relacional dentro del presupuesto de `E3` que
la base ya tenía**, y esa es una afirmación más exigente que la publicada, no
más laxa. Se sostiene sobre el trabajo declarado:

- `A` ejecuta en `E3` hasta **13 sentencias dirigidas** (una `MATCH` de FTS5 con
  los términos puente y hasta cuatro prefijos de sujeto × 2 `SELECT` acotados
  a 64 filas, más sus materializaciones);
- `C` añade **una** consulta de aristas salientes, acotada a 16 semillas y 64
  aristas, **más una** materialización por identidad que el puerto ya acota;
- son **dos sentencias dirigidas sobre catorce**, del mismo orden que las que
  la base ya paga, y por eso caben en los mismos 8 ms.

> **Léase, en `ficha_ADR002-C_v2.json`, `extremo_a_extremo.fundamento`:**
> **«las seis etapas conservan el límite de la base por composición; `E3` se mantiene en 8 ms porque `ADR002-C` añade dos sentencias dirigidas y acotadas sobre las hasta trece que la base ya ejecuta en esa etapa, y las absorbe dentro de su presupuesto.»**

Todo procede de **análisis estático y de ninguna medición**, porque no existe
ninguna. Esa afirmación de la ficha sigue siendo cierta.

---

## 3. Alcance: lo que esta errata NO dice

- **No** declara defectuosa ninguna implementación. `adr002_b` y `adr002_c`
  siguen byte a byte donde sus fichas los sitúan.
- **No** altera ningún límite, ningún objetivo, ningún árbol ni ninguna huella.
- **No** retira ni suspende la aprobación de `ADR002-B v7` ni la de
  `ADR002-C v2`.
- **No** emite ficha sucesora de ninguna de las dos, por las razones del §0.
- **No** reabre ADR-002 ni ninguna auditoría general.
- **No** autoriza el benchmark, ni ninguna medición, ni la fusión del PR #117.

---

## 4. Efecto sobre `ADR002-D`

`ADR002-D` hereda de las dos fichas: el ciclo del índice vectorial y su purga
de `B v7`, y la fuente relacional de `C v2`. Su ficha **declara ya la verdad
corregida**, no la errata:

1. cita `ADR002-A` **v5** con su huella vigente;
2. cita `ADR002-B` **v7** y `ADR002-C` **v2** como las versiones vigentes de
   las que toma cada señal;
3. explica su aritmética de `E3` y `E4` sin arrastrar el «sube de 3 ms».

Es exactamente el motivo por el que esta errata se emite **antes** de congelar
`ficha_ADR002-D_v1.json` y no después.
