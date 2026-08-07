# SIRIUS 0.2 — ADR-002 · Cierre

**Versión:** 1.0
**Estado:** **NINGUNA ALTERNATIVA ES CONFORME · `ADR-002` no puede cerrarse eligiendo**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** el usuario, con permiso expreso para todo lo necesario:
«**elige tú, y solo para y entrégame el resultado final bueno**».

**Artefacto:** `artifacts/adr002_round/cierre_adr002_v0.1.json`.

---

## 1. El resultado, en una frase

Los cuatro candidatos incumplen **las mismas dos obligaciones**, y las incumplen
**por igual**:

| | contamin. | ámbito | polaridad | **etapa** | borrado | **`B04-M01`** | marcado `M2` |
|---|---|---|---|---|---|---|---|
| `ADR002-A` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ **16** | ✅ |
| `ADR002-B` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ **16** | ✅ |
| `ADR002-C` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ **16** | ✅ |
| `ADR002-D` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ **16** | ✅ |
| `T0-control` | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ 21 | n/m |

Que las dos rojas sean **idénticas en los cuatro** es el dato que decide el
cierre: una obligación que todos incumplen igual **no separa alternativas**. No
es un defecto que elegir otra evitaría. Es una condición de `ADR-002` que
cualquiera que se elija arrastra.

**Por eso `ADR-002` no puede cerrarse eligiendo una alternativa.** Elegir no
arregla lo que falla.

---

## 2. La obligación que nadie había juzgado

`B04-M01 · Recall crítico` — «Críticos recuperados / críticos elegibles», umbral
**«100 % por caso»**.

`§14 · R1 · Cobertura crítica` — «Puerta: **una omisión crítica reproducible
elimina la alternativa**.»

`§11 · G12` — «Todos los críticos elegibles se preservan o se declara
desbordamiento bajo límite duro; **nunca se ocultan**.»

**Esa cifra se publicó en todas las corridas y nadie dijo nunca si pasaba.** Las
cinco puertas booleanas que se adjudicaban son contaminación, fuga de ámbito,
fusión de polaridad, conformidad de etapa y borrado y regeneración. El recall
crítico salía como `criticos_pendientes_total`, un número al lado de los demás,
sin veredicto.

Vale **16** para los cuatro candidatos, en seis casos: `N1-02`, `N1-30`, `N1-31`,
`N1-33`, `N1-34` y `N1-44`.

**No hay nada que recalcular ni interpretar.** `metrics.criticos_pendientes` ya
descontaba los críticos que el límite duro deja pendientes —el canon los permite
**si se declaran**— y solo contaba los que **la referencia misma esperaba** y no
se entregaron. Lo único que faltaba era compararlos con su umbral.

Es exactamente el mismo hueco que tenía el marcado de `M2`: una obligación
canónica medida, publicada y sin juzgar. Los dos quedan cerrados.

---

## 3. Cómo se llegó aquí: la verificación me refutó a mí

Antes de tocar nada congelado se lanzó una verificación adversarial que intentaba
**tumbar** cinco conclusiones que yo había defendido. **Tumbó las cinco.**

| Lo que yo afirmé | Lo que la verificación encontró |
|---|---|
| «`CA-25` no caza nada: los tres devueltos están en ámbito» | **Sí caza**: `T0` devolvió `MEM-018`, fuera de ámbito. El caso funciona; lo suspende el control, que es su papel |
| «El motor hace bien en expandir hasta entregar los críticos, por `B01-D04`» | `B01-D04` declara precedencia **solo sobre precisión y tamaño**. La obligación viene de `§11 G12` y `§15.2`, no de donde yo la ponía |
| «`CA-33` cumple su parte canónica» | **No la cumple**: el veredicto congelado registra `criticos_pendientes: ["DECISION:3"]`, y `DEC-003` es **crítico** |
| «La etapa está roja contra una instanciación modificable» | La parte **canónica** también falla, por lo anterior |
| «El incumplimiento de `M2.3` es real» | Ya no: lo había corregido yo mismo dos commits antes |

La tercera es la que importa, y es la que corrige un informe anterior mío: dije
que `CA-25` y `CA-33` cumplían su obligación congelada y que la puerta roja era
un artefacto. **Era falso.** Las dos rojas son legítimas, y la de `CA-33` es una
omisión crítica.

---

## 4. Lo que sí se arregló, y se comprobó que no movió nada

### 4.1 El marcado de `M2`, medido y luego corregido

`B04 M2` pide que el histórico «permita archivado, sustituido y finalizado» y
«nunca lo presente como actual». Se midió **antes** de tocar nada: dos de las tres
partes en verde, la tercera roja —la respuesta decía «no vigente» sin decir cuál—.

**Después**, con el defecto ya publicado, se corrigió `trace.py` para nombrar el
estado. El orden importa: la medición no se diseñó alrededor del arreglo; el
arreglo se hizo sabiendo la medición. Las dos lecturas se conservan.

Y `M2.1` no pasa en el vacío: los tres estados se ejercitaron de verdad —dos
sustituidas, una finalizada, una archivada—, con una prueba que retira el verde si
el banco dejara de ejercitarlos.

### 4.2 `AB-4`, la ablación que el banco llama la más informativa

Estaba declarada no ejecutable, y lo estaba. El paquete añadió el interruptor que
faltaba al lector base que los cuatro comparten.

Lo que dice es lo más útil de todo el nivel 3:

| | resultados | aciertos exactos | **fusiones de polaridad** |
|---|---|---|---|
| con validación | 149 | 23/47 | **0** |
| sin validación | **149** | **23/47** | **51** |

**La validación no cambia ni un resultado y sostiene una puerta de fallo duro.**
Medir solo aciertos habría concluido que no aporta nada.

### 4.3 La comprobación que hace creíble todo lo anterior

La ronda se repitió entera —`v0.4`, once sesiones, 100 repeticiones— y
**la conformidad salió idéntica a la de `v0.2`, cifra por cifra**. Eso demuestra
que el paquete cambió solo **lo que se publica**, no lo que se recupera. Si una
sola cifra se hubiera movido, la corrida previa habría dejado de servir como
término de comparación, y se dice en el artefacto.

---

## 5. Estado del banco: ejecutado en sus cuatro niveles

| Nivel | Qué | Estado |
|---|---|---|
| 1 | 50 casos canónicos | ejecutado tres veces (`v0.1`, `v0.2`, `v0.4`) |
| 2 | 5 casos arquitectónicos | **ejecutado**: puertas 4, 5 y 7 en verde |
| 3 | 7 ablaciones | **5 ejecutadas**; `AB-2` y `AB-5` declaradas con su motivo |
| 4 | 1 discriminante relacional | **ejecutado**: solo `C` y `D` lo pasan |

`AB-2` no se ejecuta porque **la norma prohíbe la ablación que el banco pide**:
saltar `E1→E3` es lo que `RF-14` veta, y solo un motor que lo incumpliese podría
correrla. `AB-5` necesita una máscara de puertas que el motor no tiene. Las dos
están fijadas por pruebas que fallarían si dejaran de ser ciertas.

---

## 6. Si hubiera que elegir, sería `ADR002-C` — pero no hay que elegir

| | Nivel 1 | Etapa | Discriminante | `AB-3` | `P50` | Almacenamiento |
|---|---|---|---|---|---|---|
| **`ADR002-C`** | **23/47** | **32/46** | **pasa** | sin cambio | **198–210 ms** | **0 B** |
| `ADR002-A` | **23/47** | **32/46** | falla | sin cambio | 204–210 ms | 1 462 272 B |
| `ADR002-D` | 21/47 | 30/46 | **pasa** | **+2 al apagarla** | 212–228 ms | 35 016 704 B |
| `ADR002-B` | 21/47 | 30/46 | falla | **+2 al apagarla** | 220–233 ms | 35 016 704 B |

`C` empata con `A` en todo lo de nivel 1, **pasa el discriminante que `A` falla**,
es la más rápida y no consume almacenamiento adicional. `D` es `C` más una señal
vectorial que, medida por ablación sobre el propio candidato, **solo resta**.

Pero esto es una **preferencia sobre alternativas no conformes**. `ADR-002` se
cierra por cumplimiento, no por comparación, y ninguna cumple.

---

## 7. Lo que hay que hacer para poder cerrar

Las dos rojas son de la **capa compartida y del banco**, no de ningún candidato:

1. **`B04-M01`.** Seis casos dejan críticos sin entregar. `N1-33` es el caso
   claro: `DEC-003` es crítico y sus palabras identificatorias —«límite de
   gasto»— viven en su **razón de criticidad**, no en su texto, de modo que
   ninguna etapa léxica, vectorial ni relacional puede alcanzarlo. Alcanzarlo
   exige que la criticidad sea recuperable, y eso es una decisión de diseño que
   `ADR-002` no tiene mandato para tomar.
2. **La conformidad de etapa.** `CA-25` y `CA-33` resuelven después de la etapa
   declarada. `AB-1` mostró que restringir a `E1` corrige `CA-25`, lo que apunta
   a la política de expansión, no al candidato.

Ninguna de las dos se arregla eligiendo alternativa, y ninguna se arregla sin
tocar decisiones que están fuera del alcance de `ADR-002`.

---

## 8. Lo que queda sin medir, dicho por última vez

- **`AB-5`** —las puertas `G1-G12` de una en una— sigue sin ejecutarse: exigiría
  una máscara en el motor común.
- **La densidad relacional del banco** es la que es: diez relaciones. El
  discriminante de nivel 4 separa a `C` y `D` de `A` y `B`, pero un banco con
  densidad realista podría separar más, o menos.

---

## 9. Solicitud única

> **¿Se aprueba este cierre —ninguna alternativa conforme, `ADR002-C` como
> preferida, y las dos obligaciones incumplidas elevadas a condiciones de cierre
> de `ADR-002`— y se abre la decisión de diseño que `B04-M01` exige?**

No se elige alternativa en firme, no se declara conforme a nadie y no se fusiona
el PR #117.
