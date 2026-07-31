# SIRIUS 0.2 — ADR-002 · Aprobación de TOL-209

**Versión:** 1.0  
**Estado:** **APROBADO · ADR002-TOL-209 SATISFECHA**  
**Fecha:** 31 de julio de 2026  
**Rama:** `evidence/adr001-spikes`  
**Autoridad:** Usuario / Proyecto Sirius  
**Commit auditado:** `6a1f6ae7c8c8b35328f85f1503bf66b77f6c114e`  
**Commit de preinscripción del paquete 08:** `7fc028fef243babeeb524fce94b7de724942a057`  
**Autorización explícita del usuario:** «Materializa la aprobación explícita de ADR002-TOL-209 desde el HEAD actual»

## 0. Objeto

Esta acta materializa la aprobación explícita de `ADR002-TOL-209` —**protocolo
común de medición**— tras cuatro paquetes de trabajo encadenados:

1. **paquete 05**: primera preinscripción del suelo de medición y su corrida;
2. **paquete 06**: método multiescala de punto fijo, tras constatar que el
   método v0.1 producía un `U` que colocaba operaciones submilisegundo en
   régimen relativo, contra la intención explícita de TOL-107;
3. **paquete 07**: banda dependiente de la magnitud derivada de la envolvente
   monótona, con once sesiones y escalera hasta 1 s. Devolvió `NO_EVALUABLE`
   con vara única, y **ese resultado se publicó tal cual**;
4. **paquete 08**: separación de P50 y P95 en TOL-107 y derivación del perfil
   de tolerancias desde la evidencia congelada del paquete 07, **sin medición
   nueva**.

Desde esta acta, `ADR002-TOL-209` queda **SATISFECHA** dentro del alcance
exacto definido aquí.

Los documentos y artefactos conservan sus nombres y etiquetas históricas
`PROPUESTO`. Esta acta prevalece sobre esas etiquetas sin reescribirlos,
preservando las identidades exactas auditadas.

## 1. Decisión aprobada

Se aprueba como **protocolo único de medición de ADR-002**, congelado antes
del benchmark y vinculante para T0 y T1–T4 por igual:

> `docs/architecture/SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md`

La v0.1 se conserva **sin modificar** y sigue siendo la que citan las
evidencias `suelo_medicion_v0.1`, `v0.2` y `v0.3` ya publicadas. La v0.2 la
sustituye como norma vigente sin reescribirla.

Se aprueba con él el Registro que lo exige:

> `docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.5_PROPUESTO.md`

en lo que respecta **exclusivamente** a las filas `ADR002-TOL-209` y
`ADR002-TOL-107`. El resto del Registro conserva su estado `PROPUESTO` y esta
acta **no lo aprueba**.

### 1.1 Contenido normativo del protocolo

| Bloque | Regla vinculante |
|---|---|
| **Instrumentación** | Reloj monotónico · fixtures fuera del cronómetro · warm-up declarado y descartado · sin red ni modelos externos no declarados · DDL recuperado del propio motor |
| **Repeticiones** | Mínimo 30 por escenario y magnitud; 100 cuando el coste sea bajo |
| **Sesiones** | **Exactamente 11** sesiones independientes para toda medida sujeta a TOL-107; mínimo 5 para las que no la alimentan |
| **Percentiles** | **Nearest-rank, nunca interpolado**; se publican P50, P95, P99, mínimo, máximo, media y n; trato uniforme de las colas de n=30 |
| **Comparación** | Misma máquina y proceso en comparaciones pareadas · orden intercalado · semilla fija · mismo corpus y commit · mismo puerto de acceso · registro de carga e incidencias |
| **Variación** | Dispersión `(máx − mín)` sobre el mismo percentil en las 11 sesiones, **P50 y P95 por separado**; envolvente monótona y banda por escalón superior; repetición única y `NO EVALUABLE` tras el segundo fallo |
| **Registro** | Once campos obligatorios por medición, legibles por máquina |
| **Prohibiciones** | Ocho, encabezadas por **prohibido cambiar el protocolo después de observar resultados** |

### 1.2 Perfil de tolerancias derivado

Se aprueban como **instanciación LAB-LINUX** del §6 del protocolo los valores
del artefacto derivado, en aritmética entera de nanosegundos:

| Concepto | Valor vinculante |
|---|---:|
| `SM` — suelo del instrumento | `17.405 ns` |
| `U50` — cruce `B50(M) = 0,20 · M` | `2.685 ns` |
| `B50(U50)` | `537 ns` |
| Escalón del cruce | `10.000 ns`, intervalo `(0, 10.000]` |
| Rango cubierto por `B95` | `[17.405, 1.000.000.000] ns` |
| Sesiones exigidas | `11`, exactamente |

Las curvas completas `E50(s)` y `E95(s)` sobre los dieciséis escalones son
normativas y se fijan por el blob del artefacto en el §2.3. **Los valores
normativos son los enteros en nanosegundos**; las expresiones en µs y ms son
únicamente informativas.

### 1.3 Las dos reglas por percentil

**P50** conserva el objetivo relativo `≤ 20 %` por encima de `U50`, aplica
`B50(M) = E50(escalón superior)` por debajo, y **no emite afirmación de
latencia por debajo de `SM`**.

**P95** deja de estar sujeto al objetivo relativo. Se evalúa **en todo el
rango cubierto** contra `B95(M) = E95(escalón superior)`. **No se crea umbral
relativo para P95.** Por debajo de `SM` o por encima de la mayor escala
medida, `NO_EVALUABLE`.

`M` es el **mínimo entre sesiones del mismo percentil que se evalúa**. Nunca
se mezcla el mínimo de un percentil con la banda del otro.

**Agregación:** basta un fallo para que la magnitud falle; hacen falta los
**dos** percentiles evaluables y válidos para que sea válida.

### 1.4 `U50` queda por debajo de `SM`, y se aprueba sabiéndolo

`U50 = 2.685 ns` cae más de seis veces por debajo de `SM = 17.405 ns`. El
intervalo donde `B50(M)` decidiría algo está enteramente dentro de la zona
donde no se emite afirmación de latencia: **`B50(M)` no llega a vincular**.

Para P50, este perfil equivale al objetivo relativo del 20 % aplicado en todo
el rango medible. Se aprueba con esa lectura explícita, no a pesar de ella.
La banda dependiente de la magnitud **sí es el único criterio operativo en
P95**, que es donde la evidencia demostró que el objetivo relativo era
inalcanzable en las dieciséis escalas.

### 1.5 Regla de comparabilidad por número de sesiones

Una magnitud medida con un número de sesiones distinto de **11** se declara
`NO_COMPARABLE` y **no recibe veredicto**. La razón es aritmética: `(máx −
mín)` es un rango y la esperanza de un rango crece con el tamaño de la
muestra.

Esta guarda alcanza a la **línea base histórica**, medida con cinco sesiones,
que entra en el perfil como contraste declarado no comparable y **jamás como
veredicto**. En consecuencia, **el perfil aprobado no puede pronunciarse
sobre las magnitudes históricas de FTS5 ni de `rank()`**. Esta acta aprueba
esa consecuencia; no la elude.

## 2. Identidad vinculante de la familia aprobada

La identidad de los contenidos aprobados y de su evidencia se fija mediante
sus blobs Git en el commit auditado `6a1f6ae`.

### 2.1 Documentación normativa y actos de gobierno

| Artefacto | Blob Git |
|---|---|
| `docs/architecture/SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.2_PROPUESTO.md` | `cf65d67458b616d1f095a307c01ee1b6a590e0e2` |
| `docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.5_PROPUESTO.md` | `a3dd91ffc74d2fb518998b89996e0d4c221f6394` |
| `docs/architecture/SIRIUS_0.2_ADR_002_TOL_107_PERFIL_P50_P95_APROBACION_v1.0.md` | `e681debc741afbdddfdbc55e41b4c238c1bf80f6` |
| `docs/architecture/SIRIUS_0.2_ADR_002_TOL_107_BANDA_DEPENDIENTE_APROBACION_v1.0.md` | `03e49b0239eb8c57db93be7c4c20e66f348046ed` |
| `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_08_TOL209_PERFIL_TOLERANCIAS_v0.1.md` | `c66fe5f6784c3e198206adede2bc7e2393d02499` |
| `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_07_TOL209_BANDA_ENVOLVENTE_v0.1.md` | `9c60d84b50df0f888520023845f787e9423ddd18` |
| `docs/architecture/SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_06_TOL209_SUELO_MULTIESCALA_v0.1.md` | `c0326b253342713a01421891d406211fec4d0a19` |

### 2.2 Contrato ejecutable y verificación

| Artefacto | Blob Git |
|---|---|
| `experiments/adr002/tolerances/profile_protocol.py` | `6b0ca8a32021065b98fc0561ec495ff302180640` |
| `experiments/adr002/tolerances/derive_profile.py` | `dd80885224a9055423e35d4e8588c37aadd7f431` |
| `experiments/adr002/tolerances/schema_profile_v0_1.py` | `b8b406cba1efc31ec761c52536eca3161f423768` |
| `experiments/adr002/tolerances/test_adr002_profile.py` | `e5b8ab8c3acf2e046a3280d98be9d5d055768d2d` |
| `experiments/adr002/tolerances/envelope_protocol.py` | `afa4a7fe0191c9bc20e283d9f3ab297869c8faad` |
| `experiments/adr002/tolerances/run_envelope.py` | `ad49f810c6a3314997530276b19deed6f5797174` |
| `experiments/adr002/tolerances/schema_envelope_v0_1.py` | `23e214ed5404329864ac907bbe4e4ca84a84748c` |
| `experiments/adr002/tolerances/test_adr002_envelope.py` | `375596209c1d8fb441138d0cb68632c3b557f4c8` |
| `experiments/adr002/tolerances/floor_scale_protocol.py` | `aa6e6492e73608f496feda252f18436d8e80802e` |
| `experiments/adr002/tolerances/floor_scale_probes.py` | `07408093b7b0fb12837ec03abdfa9f4a6c384f70` |

### 2.3 Evidencia versionada

| Artefacto | Blob Git |
|---|---|
| `artifacts/adr002_tolerances/perfil_tolerancias_v0.1.json` | `41003495620aaf9cd37404b45bf359410c4e7504` |
| `artifacts/adr002_tolerances/INFORME_PERFIL_TOLERANCIAS_v0.1_PROPUESTO.md` | `75809e83b218f352b3e2d25ed1df4b8820d90217` |
| `artifacts/adr002_tolerances/suelo_medicion_v0.3.json` | `7273264879ec0d45861160066555c1f08b5882bc` |
| `artifacts/adr002_tolerances/INFORME_SUELO_MEDICION_v0.3_PROPUESTO.md` | `2c4da11a2254db923c307f3449988892643d7d9e` |
| `artifacts/adr002_tolerances/suelo_medicion_v0.2.json` | `1d73fa363d6ca8e612e55adb270fbbf3e7540147` |
| `artifacts/adr002_tolerances/INFORME_SUELO_MEDICION_v0.2_PROPUESTO.md` | `33f312dda5ba4e8dfea5d24acf5f0158ad7b4a64` |
| `artifacts/adr002_tolerances/suelo_medicion_v0.1.json` | `899ecee82bf0c62408b43c732fbbb49304eea119` |
| `artifacts/adr002_tolerances/INFORME_SUELO_MEDICION_v0.1_PROPUESTO.md` | `e2b075499f89f71a49c33325298ae9f4bc1f7076` |
| `artifacts/adr002_tolerances/mediciones_linea_base_v0.2.json` | `f9f051332d9833fb7e10b27f4820849f00b6fe6c` |

### 2.4 Documentos anteriores, intangibles

Estos dos documentos **no se editan** porque sus blobs los citan las
evidencias ya publicadas. Su intangibilidad es un control bloqueante del
paquete 08 y se conserva tras esta acta:

| Artefacto | Blob Git |
|---|---|
| `docs/architecture/SIRIUS_0.2_ADR_002_PROTOCOLO_MEDICION_v0.1_PROPUESTO.md` | `c298a6b804309a78062f79b6341adfea2374ce56` |
| `docs/architecture/SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md` | `b499b573e2bb9918961248b05d6faa1b342c552b` |

Cualquier modificación posterior de estos contenidos requiere revisión
explícita y un acto sucesor. No se reescriben para retirar sus etiquetas
históricas.

### 2.5 Cadena de commits auditada

| Commit | Contenido |
|---|---|
| `a23dbcf` | preinscripción del suelo multiescala (paquete 06) |
| `940cb9c` | corrida del suelo multiescala |
| `aa41bfa` | acto de gobierno: banda dependiente de la magnitud (paquete 07) |
| `561b47c` | corrida de la envolvente · resultado `NO_EVALUABLE` publicado tal cual |
| `7fc028f` | acto de gobierno: separación P50/P95, protocolo v0.2, Registro v0.5 (paquete 08) |
| `6a1f6ae` | perfil derivado e informe · **commit auditado por esta acta** |

## 3. Evidencia y resultado de auditoría

### 3.1 Método

La derivación del perfil es una **función pura** de la evidencia congelada
`suelo_medicion_v0.3.json`. **No se ejecutó ninguna medición nueva.** La
fuente se lee una sola vez, de modo que los bytes que se verifican contra el
blob son exactamente los que producen las cifras, y los percentiles se
**recomputan** desde los vectores crudos en vez de aceptarse los publicados.

El determinismo se **comprueba**: la corrida deriva dos veces desde la misma
fuente, compara los bytes serializados y publica el resultado de esa
comparación como control. Una prueba lo repite a través de la interfaz
completa.

### 3.2 Controles bloqueantes

**Quince de quince en `True`, y los quince recomputados.** Ninguno se publica
como constante. Entre ellos: envolventes monótonas y que cubren su
dispersión, bandas no decrecientes —lo que cierra el riesgo **M-03**—,
continuidad exacta `1 · 537 = 2.685 / 5`, `E95(s) ≥ E50(s)` en los dieciséis
escalones, y ausencia operativa de umbral relativo para P95, comprobada
interrogando al evaluador en todo el rango cubierto.

### 3.3 Auditoría adversarial

La propuesta se sometió a una auditoría adversarial de siete dimensiones que
emitió **28 hallazgos**. Todos se verificaron contra los ficheros y los
reales se corrigieron **antes de la entrega**. Los dos bloqueantes eran
contradicciones internas del Registro v0.5:

1. la fila `ADR002-TOL-209` seguía congelando el **protocolo v0.1** mientras
   el mismo commit publicaba la v0.2;
2. su «contenido mínimo» seguía exigiendo «**al menos 5** sesiones
   independientes» para estabilidad, la fórmula que la decisión prohíbe.

Ambas quedaron cerradas en el commit auditado. Se corrigieron además, entre
otros: una regla de agregación que habría permitido afirmar estabilidad sobre
una magnitud cuya cola no se evaluó; una guarda de sesiones que obedecía a un
campo del perfil en vez de al número exigido; dos controles que se publicaban
como constantes en vez de recomputarse; listas negras del esquema
sustituidas por **conjuntos cerrados**; y la lectura única de la fuente.

### 3.4 Verificación independiente

Las cifras publicadas se recomputaron desde la fuente congelada con una
implementación **independiente**, sin importar los módulos del paquete:
`SM`, `D50`, `D95`, `E50`, `E95`, el cruce `U50` y `B50(U50)` coinciden todos.

### 3.5 Suites del repositorio en el commit auditado

- paquete 08: `82 passed`;
- `experiments/`: `947 passed`;
- repositorio completo: `1195 passed`;
- Ruff format y Ruff lint: conformes;
- mypy sobre `src` y `tests`: sin errores;
- Quality en CI: **verde** sobre `6a1f6ae`;
- evidencias v0.1, v0.2 y v0.3, protocolo v0.1 y Registro v0.4: **intactos
  byte a byte**.

## 4. Correcciones no bloqueantes registradas

Estas correcciones no invalidan la aprobación y no autorizan modificar ahora
la familia aprobada:

1. La auditoría adversarial de las **correcciones mismas** no llegó a
   ejecutarse; las correcciones se verificaron una a una contra los ficheros
   y por la suite completa, pero no por un segundo pase adversarial.
2. El cruce cabecera/entrada del contraste se ancla en el campo `fuente`; una
   entrada que declarase otra fuente no se cruzaría con la cabecera.
3. `_fallos_entrada_comparable` recompone el vector de sesiones a partir del
   mínimo y el máximo publicados. Es fiel para `(máx − mín)`, pero no
   reconstruye la distribución interna.
4. El esquema no recibe la fuente v0.3: la correspondencia entre perfil y
   fuente la garantiza la custodia por blob, no el validador.
5. El escalón de 200 ms contiene un valor atípico que `E95` propaga hasta
   500 ms. Es el precio de la monotonía y no se corrige.

## 5. Limitaciones conocidas registradas

1. **`U50 < SM`**: el régimen absoluto de P50 no llega a vincular (§1.4).
2. **La fuente es una sola corrida.** Once sesiones siguen siendo pocas para
   caracterizar una cola, y la carga de la máquina no estaba controlada.
3. **El cruce descansa sobre un solo escalón**, el primero, sin escalas
   medidas por debajo que confirmen su posición.
4. **El perfil no puede juzgar la línea base** ni ninguna magnitud medida con
   un número de sesiones distinto de once (§1.5).
5. **Por encima de 1 s no hay veredicto**, ni positivo ni negativo: `B95` no
   está definida allí, y la agregación impide declarar válida una magnitud
   con un percentil no evaluable.
6. **Un solo entorno.** Todo es `LAB-LINUX`. `ACEPTACIÓN-WINDOWS` sigue
   pendiente y `TOL-205` no se toca.
7. **El límite duro de TOL-107 no se fija.** Conserva
   `REGLA_CONFIRMADA_VALOR_ENTORNO`.

Estas limitaciones son conocidas, visibles y no permiten modificar
retrospectivamente los valores después de observar candidatos.

## 6. Estado de las puertas tras esta acta

| Puerta | Estado |
|---|---|
| `SRC-ADR002-01` | **SATISFECHA** |
| `ADR002-TOL-207` | **SATISFECHA** |
| `ADR002-TOL-208` · paso 1 | **COMPLETADO** — corpus v0.4 congelado |
| `ADR002-TOL-209` | **SATISFECHA** — por esta acta |
| `ADR002-TOL-208` · global | **NO SATISFECHA** — faltan los pasos 2 y 3 |
| `ADR002-TOL-210` | **NO SATISFECHA** |

**El benchmark continúa bloqueado.** Satisfacer TOL-209 no satisface TOL-208
global ni TOL-210.

`ADR002-TOL-107` conserva `PROPUESTA` para objetivos y umbral —ahora
instanciados por el perfil aprobado en el §1.2— y
`REGLA_CONFIRMADA_VALOR_ENTORNO` para el límite duro.

## 7. Lo que esta acta no autoriza

- No ejecutar **T0**.
- No ejecutar los pasos 2 y 3 de `ADR002-TOL-208`.
- No implementar ni ejecutar `ADR002-A`, `ADR002-B`, `ADR002-C` ni
  `ADR002-D`.
- No iniciar el **benchmark**.
- No fijar el **límite duro** de TOL-107.
- No autorizar **ninguna medición nueva** ni remedir la línea base.
- No aprobar el resto del Registro v0.5, que sigue `PROPUESTO` fuera de las
  filas TOL-209 y TOL-107.
- No modificar los siete artefactos del corpus congelado ni la proyección T0.
- No modificar Sirius 0.1 (`src/`, `tests/`, `migrations/` o configuración
  productiva).
- No abrir otro PR.
- **No fusionar el PR #117.**

## 8. Reglas de custodia

1. El protocolo y el perfil quedan fijados **antes** de observar resultados
   de candidatos. Un valor congelado tarde no es tolerancia: es
   justificación a posteriori.
2. Toda medición de todo candidato se ejecuta bajo el protocolo v0.2. Una
   cifra obtenida fuera de él **no es utilizable** para comparar candidatos.
3. Toda magnitud sujeta a TOL-107 se mide con **exactamente once** sesiones.
   Un rango de otro tamaño de muestra es `NO_COMPARABLE` y no recibe
   veredicto.
4. Cualquier cambio de los contenidos vinculados en §2 exige revisión y un
   **acto sucesor**. Cambiar cualquier valor obliga a **repetir** las
   comparaciones ya ejecutadas bajo el valor anterior.
5. Las etiquetas internas `PROPUESTO` permanecen como historia auditada y no
   disminuyen la autoridad de esta acta.
6. Las correcciones no bloqueantes y las limitaciones registradas no
   autorizan cambios implícitos ni reabren TOL-209.
7. Las evidencias `suelo_medicion_v0.1`, `v0.2` y `v0.3`, sus informes, el
   protocolo v0.1 y el Registro v0.4 **se conservan intactos**. Ninguna se
   sustituye, se retira ni se reescribe.

---

**Decisión final:** `ADR002-TOL-209` queda **APROBADA y SATISFECHA**. El
siguiente trabajo debe limitarse a las puertas aún pendientes —`TOL-210` y
los pasos 2 y 3 de `TOL-208`— y requiere autorización expresa independiente
para todo lo que implique ejecución. T0, los candidatos, el benchmark y la
fusión del PR #117 continúan no autorizados.
