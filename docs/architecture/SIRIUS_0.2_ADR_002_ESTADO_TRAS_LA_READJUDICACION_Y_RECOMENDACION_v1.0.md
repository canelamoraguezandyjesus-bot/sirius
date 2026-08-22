# SIRIUS 0.2 — ADR-002 · Estado tras la readjudicación y recomendación

**Versión:** 1.0
**Estado:** **CUATRO PUERTAS EN VERDE · una roja · ninguna alternativa elegida**
**Fecha:** 7 de agosto de 2026
**Rama:** `evidence/adr001-spikes` · **PR:** #117, **abierto y sin fusionar**

**Autoridad:** el usuario, sobre la solicitud única del §7 de las tres
resoluciones: «**Venga adelante**».

**Artefacto:** `artifacts/adr002_round/ronda_primaria_v0.3_readjudicada.json`.

---

## 1. Lo que se hizo, y lo que deliberadamente no

Se **readjudicaron** los veredictos congelados de la corrida `v0.2` con la
lectura que el canon respalda. **No se ejecutó una sola consulta.** La
conformidad es determinista: una tercera corrida habría devuelto exactamente los
mismos conjuntos, y llamarla «medición nueva» habría sido llamar cifra nueva a
la misma cifra.

**Las mediciones publicadas no se tocaron.** `v0.1` y `v0.2` siguen donde
estaban, con sus números, y `metrics.etapa_conforme` —la función que los
produjo— sigue intacta y comprobable. Reescribirla habría dejado el repositorio
sin forma de recomputar lo que publicó.

---

## 2. Las tres lecturas, una al lado de otra

| | `v0.1` (antes de corregir) | `v0.2` (tras corregir la capa común) | `v0.3` (readjudicada contra el canon) |
|---|---|---|---|
| **Contaminación** | 5 | 3 | **0** ✅ |
| **Fuga de ámbito** | 0 ✅ | 0 ✅ | **0** ✅ |
| **Fusión de polaridad** | 38 | **0** ✅ | **0** ✅ |
| **Borrado y regeneración** | ✅ | ✅ | **✅** |
| **Conformidad de etapa** | 30/46 | 32/46 | **43/45** ❌ |

(cifras de `ADR002-A`; `C` idéntica, `B` y `D` una o dos por debajo en etapa)

**Cuatro de las cinco puertas están en verde para los cuatro candidatos.** La
quinta sigue roja, y sigue siendo de cumplimiento obligatorio.

### 2.1 Por qué cada casilla se movió

- **La fusión de polaridad** cayó porque se **corrigió el código**: el detector
  pasó a leer el alcance de la negación. Eso es mérito de la corrección.
- **La contaminación** cayó porque los dos casos que la producían **estaban mal
  construidos**, y el canon lo dice. Eso no es mérito de nadie: es que se estaba
  midiendo mal.
- **La conformidad de etapa** subió porque **mi métrica era más estricta que la
  norma**. Tampoco es mérito de los candidatos.

Distinguir las tres cosas importa más que el número final.

---

## 3. Lo único que sigue rojo, y es legítimo

Dos casos —cuatro en `B` y `D`— en los que el candidato **expandió más allá** de
donde la referencia sitúa la respuesta **y devolvió el conjunto equivocado**:

| Caso | Qué pasó |
|---|---|
| `B04-CA-25` | el caso declara `E1`; se resolvió en `E3`, y no exacto |
| `B04-CA-33` | el caso declara `E1`; se resolvió en `E2`, y no exacto |

La cota es cota: resolver **antes** de lo declarado es obedecer la política
escalonada, resolver **después** es haberla forzado. Estos dos no admiten
reinterpretación, y por eso la puerta sigue roja.

---

## 4. `T0` sigue falsado, y ahora se ve mejor

La readjudicación **no absuelve al control**:

- su contaminación baja de 16 a 13 —los mismos dos casos retirados que a todos—
  pero **sigue contaminando**;
- su conformidad de etapa sigue en **0/45**, y una prueba fija por qué: sin la
  guarda de «quien no recorre `E0-E5` no conforma», el control habría pasado de
  cero a pleno por cumplir «sin saltos» en el vacío.

Que el criterio se afloje para todos y `T0` siga suspendiendo las mismas puertas
es la mejor confirmación de que el aflojamiento no fue una barra bajada.

---

## 5. Lo que el canon exige y **nadie mide**

> `M2` «separa tiempo válido de corte de registro **y nunca lo presenta como
> actual**».

Ninguna métrica de esta ronda comprueba que lo sustituido vuelva **marcado**. Es
una obligación canónica sin control, y queda declarada en el artefacto en vez de
quedarse como un hueco que nadie ve. Cerrar `ADR-002` sin medirla sería cerrar
sobre una puerta que nunca se abrió.

---

## 6. Recomendación

**`ADR002-A`**, y **`ADR-002` sigue sin poder cerrarse por cumplimiento.**

### 6.1 Por qué `A`

| | Exactos | Etapa | `P50` | Almacenamiento |
|---|---|---|---|---|
| `ADR002-A` | **23/47** | **43/45** | 221–262 ms | 1 462 272 B |
| `ADR002-C` | **23/47** | **43/45** | 222–259 ms | **0 B** |
| `ADR002-B` | 21/47 | 41/45 | 241–290 ms | 35 016 704 B |
| `ADR002-D` | 21/47 | 41/45 | 235–293 ms | 35 016 704 B |

- **Iguala o supera a las otras tres en todas las métricas**, con la menor
  maquinaria.
- **Las dos señales tardías no pagan su coste**, y esto se ha medido **dos
  veces**, sobre dos bases distintas, y en la segunda más claramente: la
  relacional no cambia **ni un resultado** en cincuenta casos; la vectorial
  cambia tres, **no mejora ninguno** y rompe dos que `A` acierta exactos.
- `C` empata con `A` y consume menos, pero **no aporta nada** que `A` no tenga.
  Entre dos que hacen exactamente lo mismo, la que tiene menos partes.

### 6.2 Por qué no cerrar

Queda una puerta roja, es de cumplimiento obligatorio, y sus dos casos son
incumplimientos reales. Y queda una obligación canónica —el marcado de `M2`— sin
métrica. **Recomendar no es declarar conforme**, y `ADR-002` se cierra por
cumplimiento, no por comparación.

### 6.3 La cautela, por tercera vez

Este corpus tiene **diez relaciones**. Que `ADR002-C` no cambie ni un resultado
describe la superficie relacional del banco tanto como al candidato. Lo demostrado
es que **sobre este banco** ninguna señal tardía paga su coste; no que no lo
pagaría sobre uno con densidad relacional realista, que este benchmark no tiene.

---

## 7. El siguiente movimiento único que se recomienda

Dos cosas, y ninguna es medir otra vez:

1. **Instrumentar el marcado de `M2`** —lo sustituido vuelve marcado y nunca como
   actual— y adjudicar `CA-25` y `CA-33` con esa evidencia delante.
2. **Decidir sobre la densidad relacional del banco**: o se acepta que `ADR-002`
   se cierra sobre un corpus que apenas ejercita la señal relacional, y se
   declara, o se amplía el banco antes de cerrar.

La segunda es la que de verdad decide si esta comparación puede cerrar `ADR-002`,
y no es una cuestión técnica: es de alcance.

---

## 8. Solicitud única

> **¿Se aprueba la readjudicación como evidencia, se acepta `ADR002-A` como
> alternativa preferida —sin declararla conforme—, y cuál de las dos vías del §7
> se toma: cerrar `ADR-002` declarando la limitación del banco, o ampliar el
> banco antes de cerrar?**

No se elige alternativa en firme, no se cierra `ADR-002`, no se repite la ronda y
no se fusiona el PR #117.
