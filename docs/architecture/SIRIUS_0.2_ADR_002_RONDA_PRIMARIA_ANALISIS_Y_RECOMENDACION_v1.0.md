# SIRIUS 0.2 — ADR-002 · Ronda primaria: resultados, análisis y recomendación

**Versión:** 1.0
**Estado:** **EJECUTADA · resultados publicados · ninguna alternativa elegida**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**
**HEAD que ejecutó:** `1f89edb35621324f76ddd210c399355daacd9d3a`

**Autoridad:** `SIRIUS_0.2_ADR_002_AUTORIZACION_RONDA_PRIMARIA_v1.0.md`, sobre la
autorización expresa del usuario.

**Artefactos:** `artifacts/adr002_round/ronda_primaria_v0.1.json` (normativo) y
`ronda_primaria_v0.1_evidencia.json` (caso a caso y muestra a muestra).

**La ronda no elige.** Este documento contiene una **recomendación razonada**;
la decisión es un acto del usuario y se pide al final.

---

## 1. Lo que se ejecutó, exactamente lo preinscrito

| | |
|---|---|
| Participantes | los cinco, **sin reducción** |
| Sesiones | **11**, cada una un proceso independiente |
| Repeticiones | **100** por sesión, tras **10** de warm-up descartadas íntegras |
| Una repetición | una **pasada completa** por los 50 casos |
| Muestras por participante | **1 100** |
| Orden | intercalado y rotado por `(sesión + repetición) mod 5` |
| Semilla · reloj | `20260726` · `time.perf_counter_ns` |
| Sustrato | `entrada.sqlite3` — **el mismo fichero** para los cinco |
| Repetición única del §6.8 | **no fue necesaria**: la corrida fue válida a la primera |

Los diez controles internos salieron todos en verde: autorización presente,
familia de conformidad intacta, corpus intacto, perfil y suelo congelados, capa
común neutral, ronda sin reducción, once sesiones completas, los cinco sobre el
mismo fichero, warm-up descartado y percentiles por rango más cercano.

**Casos:** 50 ejecutables. **47 adjudicables**; tres —`B04-CA-37`, `CA-39` y
`CA-48`— no puntúan porque el canon los declara no adjudicables mientras
`RED-032` y `RED-033` sigan sin congelar (especificación v0.3 §12).

---

## 2. Resultado: **ninguno de los cinco pasa las puertas**

Las cinco puertas del §9 son booleanas y de cumplimiento obligatorio. Ninguna
está en verde para nadie salvo la de borrado y regeneración.

| Participante | Contaminación | Fuga de ámbito | Fusión de polaridad | Conformidad de etapa | Borrado/regeneración | **Pasa** |
|---|---|---|---|---|---|---|
| `T0-control` | **16** | **1 289** | **2 480** | 0/46 | ✔ | **no** |
| `ADR002-A` | **5** | 0 | **38** | 30/46 | ✔ | **no** |
| `ADR002-B` | **5** | 0 | **38** | 29/46 | ✔ | **no** |
| `ADR002-C` | **5** | 0 | **38** | 30/46 | ✔ | **no** |
| `ADR002-D` | **5** | 0 | **38** | 29/46 | ✔ | **no** |

El §9 lo anticipaba: el benchmark **puede descartar** aunque no pueda elegir. Lo
que no anticipaba nadie es que descartase a todos.

### 2.1 El control queda falsado, que es su oficio

`T0` no es un candidato: es el control de falsación. Su papel es exhibir la
distancia entre Sirius 0.1 y el contrato `B04`, y la exhibe sin ambigüedad:

- **1 289 fugas de ámbito**: `RF-06` no está implementado; la búsqueda usa el
  proyecto activo global.
- **2 480 pares fundidos**: `T0` no marca polaridad, de modo que no distingue
  ninguna afirmación de ninguna negación.
- **0/46 conformidad de etapa**: `rank()` recorre **todo el canon vigente** para
  responder, que es el barrido completo que `RF-14` prohíbe. No hay etapas que
  comprobar porque no hay etapas.
- **2 192 resultados devueltos** en 47 casos, frente a **159** de `ADR002-A`
  sobre los mismos casos: casi catorce veces más, y **1/47 exactos**.
- **Cero explicaciones completas** de 2 192 resultados: no hay `RF-28`. Los
  cuatro candidatos explican **el 100 %** de los suyos.
- **~7 veces más lento** que cualquier candidato.

Los tres incumplimientos ya estaban **declarados en su ficha congelada**. La
ronda no los descubre: los mide.

---

## 3. Un solo defecto raíz explica las 38 fusiones

Las 38 fusiones de polaridad de los cuatro candidatos **no son un defecto
independiente**. Se concentran en dos casos —`N1-15` y `N1-28`— y en **ninguno**
de ellos hay fusión sin que antes haya una lectura de polaridad equivocada:

| | fusiones | lecturas erróneas |
|---|---|---|
| `N1-15` | 4 | 2 |
| `N1-28` | 34 | 17 |
| casos con fusión y **sin** lectura errónea | **0** | — |

La causa está en el detector léxico de negación que los cuatro heredan de la
base de `ADR002-A`: dispara con los marcadores `no`, `sin`, `ni`… **estén donde
estén** en la frase. Dos ejemplos del corpus, los dos declarados `AFIRMATIVA`:

- «El usuario prefiere que redactes en tono directo y **sin** adornos.» —
  `sin adornos` es un modificador, no una negación de la afirmación.
- «El contrato de mantenimiento se renovó, pero **no** consta desde cuándo.» —
  el `no` niega una subordinada sobre la fecha, no la renovación.

Son **66 lecturas invertidas** en total, idénticas en los cuatro. Marcar una
afirmación como negación no es fundirla —el §6.1 distingue las dos cosas y este
informe también—, pero **produce** la fusión en cuanto la respuesta contiene a
la vez una afirmación mal marcada y una negación real: las dos llegan con la
misma marca y ya no se distinguen.

**Consecuencia:** una sola corrección en la capa común —detectar el alcance de
la negación en vez de su presencia— cerraría la puerta de polaridad para los
cuatro a la vez.

---

## 4. Las cinco contaminaciones son de la base, no de las señales

Los cuatro candidatos contaminan **exactamente lo mismo**, en tres casos:

| Caso | Qué apareció | Por qué no debía |
|---|---|---|
| `B04-CA-04` | `MEMORIA:4`, `MEMORIA:906`, `MEMORIA:925` | el caso espera **conjunto vacío** y devuelve tres |
| `B04-CA-05` | `DECISION:3` | prohibido declarado; llega junto al esperado `DECISION:2` |
| `B04-CA-26` | `MEMORIA:112` | **vigente desde 2026-05-01** y el tiempo objetivo es 2026-04-01 |

`CA-26` es el más informativo: no es un problema de relevancia sino de
**tiempo**. La puerta temporal deja pasar un elemento que todavía no está en
vigor. Es un defecto concreto, localizado y corregible de la capa común.

Ninguna de las cinco contaminaciones procede de una señal tardía: `A`, que no
tiene ninguna, contamina lo mismo que `D`, que tiene dos.

---

## 5. Lo que aportan las señales tardías: nada, y una de ellas resta

Es la pregunta que `ARQ-00 §23` puso a prueba, y la ronda la responde con
números.

### 5.1 La señal relacional no cambia **ni un solo resultado**

`ADR002-C` devuelve **exactamente lo mismo que `ADR002-A`** en los cincuenta
casos. Cero diferencias. Su latencia es indistinguible —`C` 225,5–246,7 ms
frente a `A` 226,5–251,4 ms— y su consumo de almacenamiento es **cero**.

### 5.2 La señal vectorial cambia tres casos y **no mejora ninguno**

`ADR002-B` difiere de `ADR002-A` en tres casos, y en el balance pierde:

| Caso | `A` | `B` | Efecto |
|---|---|---|---|
| `B04-CA-08` | **exacto** | añade `DECISION:13` | **rompe** un caso que `A` acertaba |
| `B04-CA-27` | no exacto | añade `DECISION:13` | sin cambio de veredicto |
| `B04-CA-34` | no exacto | añade `MEMORIA:25` y `DECISION:16` | sin cambio de veredicto |

**Ninguna adición del vector está en el conjunto esperado.** Su aportación
medida es un falso positivo en tres casos y una pérdida en uno.

### 5.3 Y cuesta

| Participante | Exactos | Latencia `P50` | `P95` | Almacenamiento |
|---|---|---|---|---|
| `ADR002-A` | **20/47** | 226,5–251,4 ms | 368–395 ms | 1 462 272 B |
| `ADR002-C` | **20/47** | **225,5–246,7 ms** | **365–384 ms** | **0 B** |
| `ADR002-B` | 19/47 | 245,3–273,4 ms | 398–432 ms | 35 016 704 B |
| `ADR002-D` | 19/47 | 238,6–268,3 ms | 389–407 ms | 35 016 704 B |
| `T0-control` | 1/47 | 1 570–1 734 ms | 1 803–2 006 ms | no declarado |

El sidecar vectorial cuesta **24 veces** el almacenamiento de la base léxica y
alrededor de un **8 %** de latencia, y a cambio empeora la exactitud.

### 5.4 Lo que esto significa, y lo que **no**

El §8 de la especificación escribió por adelantado la condición de `AB-3`:

> «Si desactivar la señal tardía no degrada materialmente ninguna métrica de
> puerta, `ADR002-A` no es un control degradado: **es la respuesta**.»

Sobre este corpus, desactivar cualquiera de las dos señales tardías **no degrada
ninguna métrica de puerta**, y desactivar la vectorial además **mejora** la
exactitud. La puerta 7 —«el coste adicional no produce mejora material»— actúa
**a favor de `A`**, exactamente como el §9 previó.

**Y ahora la cautela, que es igual de importante.** Este resultado se obtuvo
sobre la familia de conformidad v0.6, con **97 elementos y 10 relaciones**. Ese
corpus **apenas ejercita la señal relacional**: que `C` no cambie ni un
resultado dice tanto de la superficie relacional del corpus como del candidato.
Las pruebas funcionales de `C` y de `D` sí exhiben el discriminante relacional,
sobre un fixture construido para exhibirlo. De modo que lo demostrado es:

- **demostrado**: sobre el corpus de conformidad vigente, ninguna señal tardía
  paga su coste;
- **no demostrado**: que no lo pagaría sobre un corpus con densidad relacional
  realista, que este benchmark no tiene.

---

## 6. Lo que la ronda **no** puede decidir

- **No elige alternativa.** Ninguna pasa las puertas; elegir entre no-aprobados
  sería elegir el menos malo sin que el contrato lo autorice.
- **No descarta definitivamente a nadie.** Los tres defectos que bloquean a los
  cuatro son de la **capa común**, no de sus arquitecturas, y una corrección los
  levanta a los cuatro a la vez.
- **No cierra la escala.** Las cifras comparan a los cinco entre sí; no son
  comparables con los valores absolutos de la línea base rederivada de `T0`,
  medida a otra escala. Es la incertidumbre 4 del §12, que sigue abierta.
- **No abre `EJE-1` ni `EJE-2`.**

---

## 7. Tres defectos que la ronda encontró en el corpus

No son de los participantes y se declaran porque callarlos los perdería:

1. **`B04-CA-14`** declara resolverse en `E0` —que no expande— y a la vez espera
   dos resultados. Su métrica de etapa no puntúa para nadie.
2. **Siete casos** nombran documentos o mensajes en sus listas de elegibles o
   prohibidos. No son elementos del canon y no pueden ser resultados: quedan
   apartados del recuento y declarados.
3. **`CA-37`, `CA-39` y `CA-48`** siguen sin ser adjudicables, como el §12
   anticipaba. `CA-39` ni siquiera declara cardinalidad.

---

## 8. Recomendación

**No elegir alternativa todavía, y corregir la capa común.**

El razonamiento, en tres pasos:

1. **Nadie pasa las puertas**, así que no hay ganador que declarar.
2. **Los tres defectos que bloquean a los cuatro son compartidos** —alcance de
   la negación, puerta temporal y sobre-recuperación—, viven en la capa común y
   ninguno es atribuible a una arquitectura. Elegir ahora mediría los defectos
   comunes, no las alternativas.
3. **Con los defectos corregidos, la comparación vuelve a tener sentido**, y
   entonces la evidencia ya recogida apunta a `ADR002-A`: iguala a los demás en
   todas las métricas de puerta, empata en exactitud con `C`, supera a `B` y a
   `D`, y lo hace con la menor maquinaria. Pero **eso hay que volver a medirlo**,
   no darlo por hecho.

**El siguiente movimiento único que se recomienda** es un paquete de corrección
de la capa común con esos tres defectos, sus pruebas, y la re-ejecución de esta
misma ronda —cuyo arnés queda congelado y reutilizable— sobre el mismo sustrato.

**Alternativa que no se recomienda pero es legítima**: declarar `ADR002-A`
ganadora provisional por la puerta 7 y aplazar las correcciones. Se descarta
porque las cinco puertas son de cumplimiento **obligatorio** y ninguna
recomendación puede saltárselas.

---

## 9. Solicitud única

> **¿Se aprueba el resultado de la ronda primaria como evidencia de `ADR-002`,
> se acepta que ninguna alternativa puede elegirse todavía, y se autoriza abrir
> un paquete de corrección de la capa común con los tres defectos medidos
> —alcance de la negación, puerta temporal y sobre-recuperación— antes de
> repetir la ronda?**

Hasta que eso se decida no se elige alternativa, no se corrige nada, no se
empieza otro ADR y no se fusiona el PR #117.
