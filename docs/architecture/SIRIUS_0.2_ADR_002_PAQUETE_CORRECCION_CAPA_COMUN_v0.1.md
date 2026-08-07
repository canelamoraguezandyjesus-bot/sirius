# SIRIUS 0.2 — ADR-002 · Paquete de corrección de la capa común

**Versión:** 0.1
**Estado:** **PREINSCRITO · antes de tocar una línea de código**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** `SIRIUS_0.2_ADR_002_RONDA_PRIMARIA_APROBACION_EVIDENCIA_v1.0.md`
§4, sobre la elección del usuario «aprobar y corregir la capa común».

**Se preinscribe antes de implementar** por el mismo motivo que se preinscribió
el arnés: describir la corrección después de escribirla permitiría que la
descripción se ajustara al código en vez de al revés.

---

## 1. Lo que la ronda midió, y lo que de eso es corregible

La ronda dejó cinco contaminaciones y 38 fusiones idénticas en los cuatro
candidatos. Al diagnosticarlas una por una **no todas son defectos suyos**, y la
diferencia decide qué se corrige aquí y qué se te devuelve como pregunta.

| # | Síntoma medido | Dónde vive | ¿Corregible aquí? |
|---|---|---|---|
| **D1** | 66 lecturas de polaridad invertidas → 38 fusiones | `adr002_a/lexical.py` | **Sí** |
| **D2** | `B04-CA-26` devuelve un elemento **aún no vigente** | `common/gates.py` | **Sí** |
| **D3a** | `B04-CA-04` devuelve un elemento `ARCHIVADA` | `common/gates.py` | **Sí** |
| **D3b** | `B04-CA-04` devuelve dos `DISTRACTOR_RUIDO` | el corpus | **No** — §4 |
| **D3c** | `B04-CA-05` devuelve la decisión **vigente** en una consulta `M2` | sin regla canónica | **No** — §4 |

---

## 2. D1 · El alcance de la negación, no su presencia

**Lo medido.** `polaridad_negativa()` declara negativa cualquier frase que
**contenga** un marcador (`no`, `ni`, `sin`, `nunca`…), esté donde esté. Sobre
la familia v0.6 eso invierte **66** lecturas, todas de afirmativa a negativa, y
de ahí salen las 38 fusiones: en cuanto una respuesta lleva a la vez una
afirmación mal marcada y una negación real, las dos llegan con la misma marca y
dejan de distinguirse.

Dos ejemplos del corpus, los dos declarados `AFIRMATIVA`:

| Texto | Por qué es afirmativo |
|---|---|
| «El usuario prefiere que redactes en tono directo y **sin** adornos.» | `sin adornos` modifica *cómo*, no niega la preferencia |
| «El contrato de mantenimiento se renovó, pero **no** consta desde cuándo.» | el `no` niega una subordinada sobre la fecha, no la renovación |

**Lo que se corrige.** El detector pasa a mirar **qué** niega el marcador en vez
de si aparece:

1. un marcador dentro de un **complemento introducido por preposición** —`sin
   adornos`— modifica, no niega la afirmación principal;
2. un marcador tras una **conjunción adversativa o subordinante** —`pero no
   consta`, `aunque no…`— niega la subordinada, no la principal;
3. un marcador en la **oración principal y antes de su verbo** —`No uses
   opciones de vuelo con escala.`— sí la niega.

**Cómo se comprobará que está bien y no solo que cambió.** Con los tres
elementos que el canon declara `NEGATIVA` —`MEM-002`, `MEM-014` y `DEC-010`—
como positivos obligados, y con los textos que producen los 66 falsos como
negativos obligados. La corrección es correcta si y solo si las 66 caen a **cero
sin perder ninguno de los tres**.

**Alcance.** `ADR002-A` y, por composición, `B`, `C` y `D`. **Las cuatro fichas
tendrán que emitir versión nueva**: la ficha describe el candidato y el
candidato cambia.

---

## 3. D2 y D3a · Dos puertas que no miran lo que tienen delante

### 3.1 El dato ya está; nadie lo usa

`ejes_p2` materializa `valid_from`, `valid_to`, `occurred_at` y `recorded_at`
para cada elemento. El puerto **no los lee** —su `SELECT` pide nueve columnas y
ninguna es temporal— y `EjesDeclarados` **no tiene dónde guardarlos**. `G8` solo
compara el corte de registro contra `created_at`.

Consecuencia medida: `B04-CA-26` consulta el 2026-04-01 y recibe `MEM-112`, que
**entra en vigor el 2026-05-01**. No es un problema de relevancia; es que nadie
pregunta si el elemento ya existía.

### 3.2 La regla, dicha antes de escribirla

| Situación | `M1` y modos ordinarios | Modo que admite no vigentes (`M2`) |
|---|---|---|
| `valid_from > t_obj` — **todavía no está en vigor** | **excluido** | **excluido** |
| `valid_to <= t_obj` — **ya expiró** | excluido | **admitido** |
| en vigor | admitido | admitido |

La primera fila es la que importa y **no se relaja ni en `M2`**: consultar el
pasado no permite recuperar algo que **aún no había empezado**. `RF-07` y
`RF-08` separan tiempo objetivo de corte de registro precisamente para esto.

Comprobación sobre los datos ya medidos: `MEM-112` (desde 2026-05-01, consulta
2026-04-01) queda fuera; `DEC-002` (01-01 → 04-01, consulta 06-15, modo `M2`)
sigue dentro, que es lo que `CA-05` espera.

### 3.3 D3a · El eje de disponibilidad tampoco se mira

`MEM-004` es `ARCHIVADA`. La proyección colapsa ese eje a `archived`, y
`disponible` solo se pone a falso para `deleted`/`purged`, de modo que ninguna
puerta lo excluye. El eje real viaja intacto en `ejes_p2` —por eso existe ese
plano— y basta con leerlo: **`ARCHIVADA` no entra en modos ordinarios**.

---

## 4. Lo que **no** se corrige, y por qué se te devuelve como pregunta

Los dos casos siguientes se midieron como contaminación de los cuatro
candidatos. Al diagnosticarlos **no encuentro regla que un candidato pueda
aplicar sin leer el oráculo o sin que yo me invente el canon**, y por eso no los
corrijo: inventar una regla para que la métrica mejore es exactamente lo que un
benchmark no puede permitirse.

### 4.1 D3b · Los dos distractores de ruido de `B04-CA-04`

`MEM-906` y `MEM-925` son «Nota ordinaria N sobre formato de informes sin valor
crítico». **Contienen los términos de la consulta** y su disponibilidad,
confirmación y validez son las mismas que las de un elemento legítimo. Lo único
que los distingue es la etiqueta `DISTRACTOR_RUIDO` de la adjudicación, que es
**oráculo**: ningún candidato puede leerla, y ninguno debe.

Dicho de otro modo: sobre este corpus, `CA-04` **no parece superable por
construcción** para un candidato léxico honesto. El principio 3 del §3 de la
especificación prohíbe los casos que solo una arquitectura puede pasar; un caso
que **ninguna** puede pasar sin el oráculo es el mismo defecto por el otro
extremo.

### 4.2 D3c · La decisión vigente en una consulta `M2`

`CA-05` pregunta «¿Qué decisión de presupuesto usábamos **antes**?» en modo
`M2`, espera `DEC-002` —la sustituida— y declara prohibida `DEC-003`, la
vigente. La justificación de la adjudicación dice «la consulta pide expresamente
la versión anterior: el dominio es lo sustituido».

`M2` está definido como el modo que **admite** elementos no vigentes. Que además
**excluya** los vigentes es una lectura distinta y más fuerte, y **no la
encuentro escrita** en lo que tengo delante. Puede que esté en `B04` y no la haya
localizado, o puede que la instanciación esté pidiendo algo que el modo no
implica. Las dos posibilidades tienen arreglo, pero son arreglos distintos, y no
voy a elegir uno para que la cifra mejore.

---

## 5. Lo que este paquete no hace

- **No toca el arnés de la ronda.** Repetir con un arnés modificado después de
  ver los resultados es lo que el §8.1 del protocolo prohíbe.
- **No toca el corpus ni las referencias.** Una referencia de nivel 1 no cambia
  desde que se congela.
- **No elige alternativa** ni reordena a nadie.
- **No toca** Sirius 0.1 productivo ni fusiona el PR #117.

---

## 6. Plan, en orden

1. `D2` + `D3a`: ejes temporales y de disponibilidad en el puerto y en las
   puertas, con sus pruebas.
2. `D1`: alcance de la negación, con sus pruebas.
3. Fichas nuevas de `A`, `B`, `C` y `D`, que sustituyen a las vigentes.
4. **Repetición de la ronda** con el arnés congelado, sobre el mismo sustrato.
5. Contraste `v0.1` frente a `v0.2` y recomendación final.

El resultado esperado, dicho **antes** de medir para que no pueda ajustarse
después: contaminación de 5 a **2** —quedan `D3b` y `D3c`, que no se
corrigen—, fusiones de 38 a **0**, y conformidad de etapa sin cambio, porque
ninguna de las tres correcciones la toca.
