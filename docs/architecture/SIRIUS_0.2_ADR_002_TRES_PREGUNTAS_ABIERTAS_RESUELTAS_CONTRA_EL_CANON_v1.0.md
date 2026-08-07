# SIRIUS 0.2 — ADR-002 · Las tres preguntas abiertas, resueltas contra el canon

**Versión:** 1.0
**Estado:** **RESUELTAS · dos contra la instanciación, una contra mi propia métrica**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** el usuario, sobre la solicitud única del §6 del contraste `v0.2`:

> «**Sí venga como creas q es mejor**»

**Fuente:** `SIRIUS_0.2_BLOQUE_04_BUSQUEDA_Y_RECUPERACION_v1.0_APROBADO.docx`,
leída directamente del `.docx` verificado por `SHA-256` contra `MANIFEST.md`. Se
cita **literal**; nada de lo que sigue es paráfrasis.

**Aviso sobre la tercera.** Una de las tres respuestas señala un defecto **de mi
propia métrica**, no de los candidatos. Las cifras publicadas de `v0.1` y `v0.2`
**no se tocan**: corregir un veredicto después de verlo es lo que el §8.1
prohíbe. Lo que se hace es publicar el reanálisis **al lado**, etiquetado, con
las dos lecturas visibles.

---

## 1. `B04-CA-05` · Qué es `M2`, literalmente

**La pregunta.** La instanciación declara **prohibida** la decisión **vigente**
`DEC-003` en una consulta `M2` que pide la versión anterior. ¿Excluye `M2` lo
vigente, o solo admite lo histórico?

**El canon, literal:**

> **`M2 · Histórico explícito`** — Finalidad: «Consultar qué era válido, qué se
> decidió o qué se sabía antes.» Elegibilidad: «**Permite** archivado,
> sustituido y finalizado con marcas temporales; separa tiempo válido de corte
> de registro **y nunca lo presenta como actual**.»

Y en el mapeo de `B02-RF-06`:

> «`M1` toma estado aplicable; `M2` **puede recuperar** versiones anteriores
> marcadas.»

**La respuesta.** `M2` **amplía** la elegibilidad; no la restringe. Lo que el
canon prohíbe de `M2` no es devolver lo vigente: es **presentar lo histórico
como actual**. La instanciación de `CA-05` pide una exclusión que el canon **no
establece**.

**Consecuencia.** La contaminación de `DEC-003` **no es un incumplimiento de los
candidatos**. Es una instanciación que sobre-restringe, y está marcada
`DERIVADO_PROPUESTO` / `PROPUESTO_NO_CONGELADO` —no es texto canónico—, de modo
que corregirla no toca ninguna referencia congelada.

**Lo que sí habría que medir y nadie mide.** «Nunca lo presenta como actual» es
una obligación real y comprobable: en `M2`, lo sustituido debe volver **marcado**
como tal. Ninguna métrica de esta ronda lo comprueba. Es una carencia del banco,
no de las arquitecturas.

---

## 2. `B04-CA-04` · Los dos distractores de ruido

**La pregunta.** `MEM-906` y `MEM-925` llevan los términos de la consulta, tienen
los ejes de un elemento legítimo, y lo único que los distingue es la etiqueta
`DISTRACTOR_RUIDO` de la adjudicación —que es **oráculo**—. ¿Puede un candidato
excluirlos sin leerla?

**El canon, literal:**

> «**Completitud crítica antes que reducción de ruido.**»

Y sobre elegibilidad en `M1`:

> «Confirmado, válido, disponible, **pertinente al ámbito** y aplicable al tiempo
> objetivo.»

**La respuesta, y es incómoda.** El canon ordena una prioridad —completitud
antes que reducción de ruido— pero **no da ningún eje** por el que un elemento
confirmado, válido, disponible, en ámbito y aplicable al tiempo objetivo pueda
excluirse por ser «ruido». La pertinencia que el canon nombra es **al ámbito**, y
los dos distractores están en ámbito.

De modo que sobre este corpus **`CA-04` no es superable por un candidato honesto**:
exige distinguir lo que el canon no da manera de distinguir sin leer el oráculo.

**Consecuencia.** No es un fallo de los cuatro candidatos. Es un caso mal
construido, y por la misma razón que el principio 3 del §3 declara mal
construido un caso que solo una arquitectura puede pasar: **un caso que ninguna
puede pasar sin el oráculo es el mismo defecto por el otro extremo.**

**Lo que no se hace.** No se retira el caso ni se reescribe su referencia. Se
declara, y su contaminación queda **atribuida al banco** en vez de a los
candidatos.

---

## 3. La etapa declarada · Un defecto **de mi métrica**

**La pregunta.** Once de los catorce casos con etapa no conforme son «resuelto en
`E1` y el caso declara `E3`/`E4`»: el candidato encuentra **antes** de lo que la
referencia esperaba. ¿Es eso incumplir `RF-14`?

**El canon, literal:**

> «`E1` exacta/estructurada; `E2` léxica/alias; `E3` semántica/relacional; `E4`
> fuentes/historial. Ninguna puntuación blanda rescata un elemento excluido.»

> «**Solo se expande cuando falta suficiencia o críticos** y el siguiente espacio
> está autorizado.»

Y el ejemplo canónico:

> «Consulta `EXACTA`; **`E1` resuelve objetivos** y el control de críticos
> pendientes da cero.»

**La respuesta.** El canon autoriza expandir **solo por insuficiencia**. Resolver
en `E1` cuando `E1` basta **no es un incumplimiento: es la obediencia**. Lo que
`RF-14` prohíbe es el **salto** —resolver saltándose etapas— y el **barrido**, no
la parada temprana.

**Mi métrica exigía `origen == etapa declarada`, y eso es más estricto que el
canon.** El campo 12 de la ficha del caso dice dónde el autor de la referencia
**esperaba** que se resolviera; el canon dice dónde **puede** resolverse: allí
donde primero se alcanza suficiencia.

### 3.1 Las dos lecturas, lado a lado

| Participante | **Publicada** (origen `==` declarada) | **Canónica** (sin salto + resuelto en o antes) |
|---|---|---|
| `T0-control` | 0/46 | **0/46** |
| `ADR002-A` | 32/46 | **44/46** |
| `ADR002-C` | 32/46 | **44/46** |
| `ADR002-B` | 30/46 | **42/46** |
| `ADR002-D` | 30/46 | **42/46** |

**El orden entre los cuatro no cambia**, y esto importa: `A` y `C` siguen por
delante de `B` y `D` por la misma diferencia. La recomendación no depende de
cuál de las dos lecturas se use.

### 3.2 El agujero que el reanálisis tuvo primero, y cómo se cerró

La primera versión de este reanálisis daba a `T0` **46/46**. Es absurdo: `T0` no
recorre `E0-E5` en absoluto, de modo que «sin saltos» se cumplía **por vacío** y
«resuelto en o antes» no tenía nada que comprobar. Un participante sin política
escalonada no conforma temprano: **no conforma**.

Corregido, `T0` conserva su `0/46` y su incumplimiento declarado —barrido
completo del canon vigente para responder—, que es exactamente lo que su ficha
congelada dice y lo que el control existe para exhibir.

Lo dejo escrito porque el agujero es instructivo: una métrica que premia no
tener el mecanismo es peor que una que lo mide mal.

### 3.3 Lo que **no** se hace con esto

Las cifras publicadas de `v0.1` y `v0.2` **no se corrigen**. El §8.1 prohíbe
cambiar la medición después de observar resultados, y una métrica reescrita para
que suban los números es el caso central de esa prohibición —aunque la reescritura
sea correcta—. La lectura canónica se publica **al lado**, etiquetada, y quien
decida verá las dos.

---

## 4. Lo que queda, después de las tres

| Puerta | Estado | A quién es atribuible |
|---|---|---|
| Fuga de ámbito cero | **verde** para los cuatro | — |
| Confusión de polaridad cero | **verde** para los cuatro | corregida en la capa común |
| Borrado y regeneración | **verde** para los cinco | — |
| Contaminación cero | **roja**: 3 | **al banco**: 2 por `CA-04` (no superable sin el oráculo) y 1 por `CA-05` (instanciación que sobre-restringe) |
| Conformidad de etapa | **roja** en la lectura publicada | **a la métrica**: la canónica da 44/46 a `A` y `C` |

**Ninguna de las dos puertas rojas es atribuible a la arquitectura de ningún
candidato.** Eso no las pone en verde —siguen rojas y siguen siendo de
cumplimiento obligatorio—, pero cambia de quién es el trabajo pendiente.

---

## 5. Lo que esto no cambia

- **La recomendación sigue siendo `ADR002-A`**, y por las mismas razones: iguala
  o supera a las otras tres en todo, con la menor maquinaria, y las dos señales
  tardías siguen sin pagar su coste en dos corridas seguidas.
- **La cautela sigue en pie**: este corpus tiene **diez relaciones**, y que `C`
  no cambie ni un resultado describe el banco tanto como al candidato.
- **`ADR-002` sigue sin poder cerrarse por cumplimiento**: dos puertas están
  rojas, aunque ahora se sepa de quién es cada una.

---

## 6. El siguiente movimiento único que se recomienda

**Corregir el banco, no las arquitecturas.** En concreto, y en este orden:

1. **`CA-05`**: retirar `DEC-003` de los prohibidos —el canon no autoriza esa
   exclusión— y añadir la comprobación que sí exige: que `M2` devuelva lo
   sustituido **marcado** y nunca como actual.
2. **`CA-04`**: declarar el caso **no adjudicable** mientras no exista un eje
   canónico por el que un candidato pueda excluir ruido en ámbito, igual que ya
   se hizo con `CA-37`, `CA-39` y `CA-48`.
3. **El campo 12**: instanciarlo como **cota** —«no más tarde de `Ex`»— en vez de
   como igualdad, que es lo que el canon dice.

Los tres son cambios de **instanciación**, marcada `PROPUESTO_NO_CONGELADO`.
Ninguno toca texto canónico ni una referencia congelada.

---

## 7. Solicitud única

> **¿Se aprueban estas tres resoluciones contra el canon, y se autoriza el
> paquete de corrección del banco con los tres cambios de instanciación del §6,
> antes de volver a plantear el cierre de `ADR-002`?**

No se elige alternativa en firme, no se cierra `ADR-002`, no se repite la ronda
—una tercera corrida sobre el banco sin corregir daría las mismas cifras— y no
se fusiona el PR #117.
