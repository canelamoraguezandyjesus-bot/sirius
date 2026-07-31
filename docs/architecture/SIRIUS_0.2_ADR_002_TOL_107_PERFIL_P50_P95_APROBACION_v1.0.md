# SIRIUS 0.2 — ADR-002 · Acto de gobierno · Separación de P50 y P95 en TOL-107

**Versión:** 1.0
**Estado:** **APROBADO · MODIFICA LA FILA `ADR002-TOL-107` Y EL §3.3 / §6 DEL PROTOCOLO**
**Rama:** `evidence/adr001-spikes`
**Autoridad:** Usuario / Proyecto Sirius
**Commit auditado previo:** `561b47c9084122efad4fe256242caaced34e7518`
**Alcance:** la **regla de evaluación** de `ADR002-TOL-107` y las reglas de sesiones y variación del protocolo común

## 0. Objeto

Este acto no aprueba ninguna puerta. Modifica la regla con la que
`ADR002-TOL-107` evalúa la variación entre ejecuciones equivalentes:
**P50 y P95 dejan de compartir vara.**

`ADR002-TOL-209` sigue **NO SATISFECHA**. `ADR002-TOL-107` conserva su estado
`PROPUESTA` para objetivos y umbral, y `REGLA_CONFIRMADA_VALOR_ENTORNO` para
el límite duro.

**No se autoriza ninguna medición nueva.** El perfil vigente se deriva de la
evidencia ya publicada.

## 1. Por qué se modifica la regla

El paquete 07 aplicó a los dos percentiles el mismo objetivo relativo del
20 % y devolvió `NO_EVALUABLE`: ningún escalón de la escalera sostenía la
condición. Su propia evidencia —dieciséis escalas, once sesiones— explica por
qué, y la explicación es asimétrica:

| Estadístico | Peor `D(s)/s` sobre las 32 filas | Peor por escala: el mínimo |
| --- | ---: | ---: |
| **P50** | **0,158** | 0,049 |
| **P95** | 1,347 | **0,252** |

**El centro de la distribución cabe holgadamente en el 20 % a las dieciséis
escalas. La cola no cabe en ninguna.** Exigir lo mismo a ambos hacía
inalcanzable una puerta que el P50 sí cumple.

La propia fila `ADR002-TOL-107` ya registraba el síntoma —*«Para FTS5 no se
propone objetivo relativo»*, con variación P95 del 32,9–36,4 %— sin extraer
la consecuencia. Este acto la extrae.

## 2. Decisión aprobada

### 2.1 P50

- conserva el **objetivo relativo `≤ 20 %`**;
- se deriva `D50(s)` y su **envolvente monótona** `E50(s) = máx(D50(s_1), …, D50(s_i))`;
- por debajo de su cruce `U50` se aplica `B50(M) = E50(s_j)`, con `s_j` el
  **menor escalón `≥ M`** (dirección conservadora);
- por encima de `U50` se aplica el **20 % relativo**;
- **por debajo de `SM` no se emite afirmación de latencia.**

`U50` es el cruce **exacto** `B50(M) = 0,20 · M`, es decir `U50 = 5 · E50(s_k)`
sobre el menor escalón `k` que sostiene `5·E50(s_k) ≤ s_k` **y todos los
superiores**. De ahí `m · B50(U50) = U50/5`: la continuidad es **exacta y
derivada**, y `m = 1` deja de ser una elección.

### 2.2 P95

- **deja de estar sujeto al objetivo relativo del 20 %**;
- se evalúa **en todo el rango cubierto** contra `B95(M) = E95(s_j)`, derivada
  de la **envolvente monótona** `E95(s)`, usando el **escalón superior**;
- **no se crea un umbral relativo para P95**;
- por debajo de `SM` o por encima de la **mayor escala medida**,
  **`NO_EVALUABLE`**.

### 2.3 Consulta de la banda

Para consultar `B50(M)` o `B95(M)`, **`M` es el mínimo entre sesiones del
mismo percentil evaluado**: `B50` en `mín_s P50` y `B95` en `mín_s P95`.
Nunca se mezcla el mínimo de un percentil con la banda del otro.

### 2.4 Exactamente once sesiones

`TOL-107` usa **exactamente 11** sesiones completas independientes, tanto
para **construir** las bandas como para **evaluar** candidatos. **No se
comparan rangos obtenidos con números distintos de sesiones.**

La razón es aritmética, no de conveniencia: el §6.1 mide un **rango**
`(máx − mín)`, y la esperanza de un rango **crece con el tamaño de la
muestra**. Comparar un rango de cinco contra una banda construida con once
no compara estabilidad: compara tamaños de muestra.

Una magnitud medida con otro número de sesiones se declara
**`NO_COMPARABLE`** y **no recibe veredicto**. Esta guarda alcanza también a
la línea base histórica, medida con cinco sesiones.

### 2.5 Agregación de los dos percentiles

Un percentil `NO_EVALUABLE` **no emite afirmación**. La consecuencia se toma
en la dirección conservadora:

- **basta un fallo** para que la magnitud falle: una afirmación **negativa**
  se sostiene con un solo percentil que la respalde;
- **hacen falta los dos**, evaluables y válidos, para que la magnitud sea
  válida. Si alguno es `NO_EVALUABLE`, la magnitud lo es.

Lo segundo no es simetría estética. El punto 3 ordena declarar
`NO_EVALUABLE` el P95 de una magnitud **por encima de la mayor escala
medida**; si la agregación heredase entonces el veredicto del P50, el perfil
emitiría una afirmación **positiva** de estabilidad sobre una magnitud cuya
cola está demostrablemente fuera del rango calibrado. La separación
**reparte** la exigencia entre dos estadísticos que miden cosas distintas;
**no la relaja**.

## 3. Lo que este acto NO cambia

- el **objetivo relativo del 20 %** para P50;
- el objetivo de **orden y conjunto: 0 variación, sin margen**;
- el **límite duro**, que sigue siendo `REGLA_CONFIRMADA_VALOR_ENTORNO`;
- la regla de salida del bucle: repetición única y `NO EVALUABLE` en
  rendimiento si vuelve a fallar;
- los percentiles por **rango más cercano**, jamás interpolados;
- la escalera, las familias neutrales ni las sondas;
- la **evidencia** de los paquetes 05, 06 y 07, que se conserva íntegra y se
  cita por su blob exacto.

## 4. Por qué se versionan el protocolo y el Registro en vez de editarlos

El blob de `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md` está
citado dentro de las evidencias `suelo_medicion_v0.1`, `v0.2` y `v0.3`, y el
de `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md` dentro de la `v0.3`
—que es donde entró en la cadena de custodia—. **Todas ellas están ya
publicadas**, y sus corridas verifican esos blobs byte a byte.

Editarlos en el sitio haría **incomprobable la custodia de esa evidencia**:
un auditor que reejecutase las comprobaciones encontraría un blob distinto
del registrado y no podría distinguir una actualización legítima de una
manipulación.

Por eso este acto materializa el cambio en **versiones nuevas** —protocolo
**v0.2** y Registro **v0.5**—, siguiendo la convención que el propio
repositorio ya usa para el Registro (v0.1 → v0.2 → v0.3 → v0.4). Los
documentos anteriores se conservan **sin modificar** y su intangibilidad es
un **control bloqueante** del paquete 08.

## 5. Lo que este acto NO autoriza

- **No aprueba `ADR002-TOL-209`**, que sigue NO SATISFECHA;
- **no autoriza ninguna medición nueva**: el perfil se deriva de
  `suelo_medicion_v0.3.json`, congelado por blob;
- no fija el **límite duro** de TOL-107;
- no avanza a **T0**, no implementa ni ejecuta **candidatos**, no ejecuta el
  **benchmark**;
- no fusiona el **PR #117**;
- no convierte en normativo ningún valor concreto de `U50`, `B50(M)` ni
  `B95(M)`: los que produzca la derivación del paquete 08 son **propuestos**
  hasta el acta que los apruebe.

## 6. Materialización

| Artefacto | Efecto |
| --- | --- |
| `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.5_PROPUESTO.md` | Registro **nuevo**; cambia la fila `ADR002-TOL-107` y, por consecuencia forzosa, los dos campos de `ADR002-TOL-209` que quedarían contradiciéndola: el protocolo congelado (v0.1 → **v0.2**) y las sesiones exigidas para estabilidad («al menos 5» → **exactamente 11**) |
| `SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md` | Protocolo **nuevo**; cambian §3.3 y §6 y, por la renumeración del §6, las referencias cruzadas del §7.10 y del §8.8, la mención del §9 al «umbral de conmutación» y el Registro de la línea de cierre |
| `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_08_TOL209_PERFIL_TOLERANCIAS_v0.1.md` | preinscripción de la derivación |
| `experiments/adr002/tolerances/profile_protocol.py` | reglas vinculantes y propiedades comprobadas |
| `experiments/adr002/tolerances/derive_profile.py` | derivación determinista; no mide |
| `experiments/adr002/tolerances/schema_profile_v0_1.py` | contrato del perfil; recomputa todo |
| `experiments/adr002/tolerances/test_adr002_profile.py` | pruebas de las reglas y del recorrido |

Los documentos anteriores conservan sus nombres, sus blobs y sus etiquetas.
Este acto prevalece sobre la redacción anterior de las reglas que enumera,
sin reescribir ningún artefacto ya auditado.
