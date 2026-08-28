# Informe de la banda envolvente v0.3 — `LAB-LINUX` — ADR002-TOL-209

| Campo | Valor |
| --- | --- |
| **Estado** | `PROPUESTO · BANDA ENVOLVENTE MEDIDA — NO APRUEBA TOL-209` |
| **Resultado del método** | **`NO_EVALUABLE`** · motivo `sin_cruce_sostenido` |
| **Puerta** | `ADR002-TOL-209` · **NO SATISFECHA** |
| **Artefacto** | `artifacts/adr002_tolerances/suelo_medicion_v0.3.json` (blob `72732648…`) |
| **Paquete** | `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_07_TOL209_BANDA_ENVOLVENTE_v0.1` |
| **Acto de gobierno** | `SIRIUS_0.2_ADR_002_TOL_107_BANDA_DEPENDIENTE_APROBACION_v1.0.md` |
| **Registro** | fila `ADR002-TOL-107` **v0.5** (blob `b499b573…`) |
| **Commit de preinscripción** | `aa41bfab99bbbfd3542208a548063fdc013b9b82` |

---

## 1. Resultado

**No existe cruce.** Ningún escalón de la escalera sostiene
`5 · E(s) ≤ s`, ni siquiera de forma aislada. El método devuelve
`NO_EVALUABLE` y **no publica `U` ni banda alguna**.

| Magnitud | Valor |
| --- | --- |
| `SM` | **17 405 ns** |
| `U` | **no se publica** |
| `B(M)` | **no se publica** |
| Motivo | `sin_cruce_sostenido`: fallan **los dieciséis** escalones |

Veintidós de los veintitrés controles bloqueantes pasaron. El único en
`False` es `continuidad_exacta_en_u`, que presupone un umbral resuelto: el
esquema **exige** que sea `False` cuando no hay cruce, de modo que su estado
es correcto y no un fallo. Cero incidencias. Once procesos independientes,
24 640 muestras crudas publicadas íntegras.

---

## 2. La curva medida y su envolvente

| Escala | `D(s)` | `E(s)` | `E(s)/s` | ¿`5·E ≤ s`? |
| --- | ---: | ---: | ---: | --- |
| 10 µs | 11 000 ns | 11 000 ns | 1,100 | no |
| 20 µs | 26 939 ns | 26 939 ns | 1,346 | no |
| 50 µs | 30 558 ns | 30 558 ns | 0,611 | no |
| 100 µs | 95 953 ns | 95 953 ns | 0,959 | no |
| 200 µs | 155 066 ns | 155 066 ns | 0,775 | no |
| 500 µs | 332 895 ns | 332 895 ns | 0,665 | no |
| 1 ms | 971 628 ns | 971 628 ns | 0,971 | no |
| 2 ms | 1 497 366 ns | 1 497 366 ns | 0,748 | no |
| 5 ms | 2 195 694 ns | 2 195 694 ns | 0,439 | no |
| 10 ms | 3 973 044 ns | 3 973 044 ns | 0,397 | no |
| 20 ms | 8 894 142 ns | 8 894 142 ns | 0,444 | no |
| 50 ms | 22 662 076 ns | 22 662 076 ns | 0,453 | no |
| **100 ms** | 25 197 279 ns | 25 197 279 ns | **0,251** | no |
| 200 ms | **187 831 392 ns** | 187 831 392 ns | 0,939 | no |
| 500 ms | 165 166 235 ns | *187 831 392 ns* | 0,375 | no |
| **1 s** | 256 936 311 ns | 256 936 311 ns | **0,256** | no |

El mínimo alcanzado es **0,251** en 100 ms. El objetivo es 0,200. La curva
**nunca cruza**.

La envolvente hizo su trabajo: en 500 ms la dispersión medida bajó a
165,2 ms, pero `E` mantuvo 187,8 ms arrastrado desde 200 ms. Es la dirección
conservadora preinscrita y es lo que impide que la banda se estreche al
crecer la magnitud.

---

## 3. Qué falla exactamente: el P95, no el P50

Esta es la lectura más importante del artefacto.

Sobre las 32 filas `(escala, familia)`:

| Percentil | Peor `D/s` | Mejor `D/s` | Peor por escala: el mínimo |
| --- | ---: | ---: | ---: |
| **P50** | **0,158** | 0,038 | 0,049 |
| **P95** | 1,347 | 0,132 | **0,252** |

**El P50 cumple el objetivo del 20 % en las dieciséis escalas y en las dos
familias**, con holgura: su peor caso sobre las 32 filas es 15,8 %.

El **P95** es el que falla. Como `D(s)` es el peor caso sobre familias y
percentiles, lo que decide es la última columna: el peor P95 de cada escala
**nunca baja del 25,2 %**, y por eso ningún escalón sostiene la condición.

Dicho de otro modo: en este entorno el *centro* de la distribución es
estable a todas las escalas, y lo que no cabe en un 20 % es la **cola**.

El caso extremo está en el escalón de 200 ms:

| 200 ms | mín | máx | `D` |
| --- | ---: | ---: | ---: |
| `cpu` P50 | 199 811 362 | 210 477 003 | 10 665 641 (5,3 %) |
| `cpu` **P95** | 207 955 776 | **395 787 168** | **187 831 392 (93,9 %)** |
| `canon` P50 | 217 846 713 | 229 171 665 | 11 324 952 (5,7 %) |
| `canon` P95 | 235 450 314 | 276 702 133 | 41 251 819 (20,6 %) |

Un proceso de los once alcanzó, en su percentil 95, casi el doble del tiempo
nominal. Su P50 fue normal. Es una expropiación prolongada, no una máquina
más lenta.

**Pero el pico no es la única causa.** Aun ignorándolo, los dos mejores
escalones —100 ms con 0,251 y 1 s con 0,256— siguen por encima de 0,20.

---

## 4. Por qué el paquete 06 sí resolvió y éste no

Tres causas, todas verificables en los artefactos, ninguna de ellas un
defecto del método:

### 4.1 El estimador se volvió más estricto por decisión de diseño

`máx − mín` es un **rango**, y la esperanza de un rango **crece con el número
de observaciones**. Pasar de cinco a once sesiones lo ensancha
mecánicamente, con independencia de que el entorno mejore o empeore.

Es la consecuencia aritmética de la decisión de gobierno de subir a once
sesiones, y no invalida esa decisión: **un rango sobre once observaciones es
una cota más honesta de la cola que un rango sobre cinco**. Lo que sí implica
es que el `U = 100 ms` del paquete 06 era optimista por construcción y que
**los dos resultados no son comparables como iguales**.

Este efecto es normativo, no elegible: el §6.1 del protocolo y la fila
TOL-107 fijan `(máx − mín)` como métrica. No se toca aquí.

### 4.2 El entorno se degradó

Misma máquina, unas seis horas después:

| Indicador | Paquete 06 | Paquete 07 |
| --- | ---: | ---: |
| Coste de la unidad de referencia `cpu` | 345 052 ns | **454 186 ns** (+32 %) |
| Coste de la unidad de referencia `canon` | 52 491 ns | **70 126 ns** (+34 %) |
| Carga (1 min) al empezar | 0,43 | 0,51 |
| Carga (1 min) al terminar | 0,84 | **1,01** |

La corrida es más larga —once procesos de ~2 min frente a cinco de ~15 s— y
mantiene la máquina de 4 CPU cerca de la unidad durante todo el recorrido.

### 4.3 La envolvente propaga el peor escalón hacia arriba

Es su propósito —cierra M-03 impidiendo que la banda se estreche— y su
coste: un único escalón anómalo bloquea el cruce en **todos** los escalones
mayores. Aquí, el pico de 200 ms dejó a 500 ms sin posibilidad de sostener la
condición aunque su propia dispersión hubiese bastado.

---

## 5. Comprobaciones que sí quedaron acreditadas

Aunque no haya umbral, la corrida acredita todo lo demás:

| Propiedad | Estado |
| --- | --- |
| Envolvente **monótona no decreciente** | ✔ verificada |
| Envolvente **cubre `D(s)`** en los dieciséis escalones | ✔ verificada |
| **Banda no decreciente** con la magnitud (cierra M-03) | ✔ verificada |
| Once procesos distintos en cada `(familia, escala)` | ✔ 11 |
| Calibración en banda `[s/2, 2s]` en los 352 P50 | ✔ |
| Progresión exigible entre escalones consecutivos | ✔ |
| Sin deriva ni *throttling* intraproceso | ✔ |
| Sondas neutrales heredadas sin tocar | ✔ blobs verificados |
| Evidencias v0.1 y v0.2 intactas | ✔ los cuatro blobs |
| Registro v0.5, protocolo y línea base intactos | ✔ |

La **asimetría** declarada en la limitación 1 del paquete —banda más estricta
que el 20 % en algún escalón bajo— **no se materializó**: el diagnóstico
`holgura_de_banda` la publica escalón a escalón y la lista de escalones
afectados está vacía.

---

## 6. Qué queda abierto

El acto de gobierno daba por supuesto que el cruce existía y que sólo hacía
falta confirmarlo por encima de 100 ms. La medición dice que, **con once
sesiones y en esta máquina, no existe hasta 1 s**. Eso no se resuelve
midiendo otra vez: se resuelve decidiendo. Las tres salidas que la evidencia
permite plantear —**ninguna de ellas se aplica aquí**— son:

1. **Ampliar la escalera por encima de 1 s.** La evidencia no la respalda: la
   razón en 1 s es 0,256 y en 100 ms era 0,251, es decir el descenso se ha
   aplanado. Además 1 s ya está muy por encima de cualquier operación de
   recuperación plausible.
2. **Revisar el estimador.** `máx − mín` depende del número de sesiones, lo
   que hace incomparables corridas con distinta `n` (§4.1). Un estadístico
   independiente de `n` haría comparables los paquetes 05, 06 y 07. Cambiarlo
   toca el §6.1 del protocolo y la fila TOL-107: es un acto de gobierno.
3. **Revisar a qué percentil se aplica el objetivo relativo.** El P50 cumple
   el 20 % en las dieciséis escalas; sólo el P95 no. La propia fila TOL-107
   registra que la variación P95 de FTS5 fue del 32,9–36,4 % y por eso no le
   propuso objetivo relativo. Aplicar el 20 % al P95 en un entorno compartido
   puede ser, sencillamente, inalcanzable con independencia del candidato.

**No se ha repetido la corrida.** Repetir hasta que salga un cruce sería
exactamente el ajuste tras ver resultados que el paquete prohíbe. La
repetición controlada no está preinscrita en el paquete 07 y no se ha
ejercido.

---

## 7. Custodia

| Elemento | Valor |
| --- | --- |
| Commit de preinscripción | `aa41bfab99bbbfd3542208a548063fdc013b9b82` |
| `HEAD` durante la corrida | idéntico |
| Árbol de trabajo | limpio antes y después |
| Custodia reverificada tras medir | sí, antes de publicar |

Blobs preinscritos, verificados contra el árbol **y** contra lo que el commit
registra (`git rev-parse <sha>:<ruta>`):

| Blob | Fichero |
| --- | --- |
| `9c60d84b…` | `docs/architecture/…PAQUETE_TRABAJO_07_TOL209_BANDA_ENVOLVENTE_v0.1.md` |
| `03e49b02…` | `docs/architecture/…TOL_107_BANDA_DEPENDIENTE_APROBACION_v1.0.md` |
| `afa4a7fe…` | `experiments/adr002/tolerances/envelope_protocol.py` |
| `ad49f810…` | `experiments/adr002/tolerances/run_envelope.py` |
| `23e214ed…` | `experiments/adr002/tolerances/schema_envelope_v0_1.py` |
| `37559620…` | `experiments/adr002/tolerances/test_adr002_envelope.py` |

Documentos de referencia fijados por constante: Registro v0.5 `b499b573…`,
protocolo aprobado `c298a6b8…`, línea base `f9f05133…`. Módulos heredados
congelados: `corpus.py` `90c5118e…`, `floor_scale_probes.py` `07408093…`,
`floor_scale_protocol.py` `aa6e6492…`.

**Evidencias anteriores, verificadas intactas byte a byte:**

| Blob | Fichero |
| --- | --- |
| `899ecee8…` | `suelo_medicion_v0.1.json` |
| `e2b07549…` | `INFORME_SUELO_MEDICION_v0.1_PROPUESTO.md` |
| `1d73fa36…` | `suelo_medicion_v0.2.json` |
| `33f312dd…` | `INFORME_SUELO_MEDICION_v0.2_PROPUESTO.md` |

No se ha modificado, retirado ni reescrito ni un byte de ninguna de ellas.

---

## 8. Entorno

| Campo | Valor |
| --- | --- |
| Sistema | Ubuntu 24.04.4 LTS · kernel 6.18.5 |
| CPU | 4 × Intel(R) Xeon(R) @ 2,80 GHz |
| `boot_id` | `83975066-1ea2-40f9-8c52-6b88d31784c4` (estable inicio→fin) |
| Procesos | 11, secuenciales, PIDs distintos |
| Carga (1 min) | 0,51 al empezar → 1,01 al terminar |
| Duración | ≈ 25 min (11 × ~2 min) |

---

## 9. Reproducción y verificación independiente

```bash
git checkout aa41bfab99bbbfd3542208a548063fdc013b9b82
uv run python -m experiments.adr002.tolerances.run_envelope \
    --execute \
    --preinscription-commit aa41bfab99bbbfd3542208a548063fdc013b9b82 \
    --output <ruta_nueva>.json
```

Los valores **no** se reproducirán idénticos: son mediciones. Lo que sí es
reproducible es todo lo derivado. La recomputación se hizo **desde cero**,
sin usar el código del paquete, partiendo sólo de los `muestras_ns`
publicados, y coincidió en todo:

- 0 entradas con percentiles divergentes sobre 352 + 33 entradas;
- `D(s)` y `E(s)` idénticas en los dieciséis escalones;
- envolvente monótona ✔ y cubriendo `D(s)` ✔;
- banda no decreciente ✔;
- `SM = 17 405` idéntica;
- ausencia de cruce recomputada de forma independiente.

El validador `schema_envelope_v0_1` rechaza cualquier artefacto cuya
derivación no salga de sus propios vectores. Se sometió a un barrido
adversarial sobre las 399 rutas del documento —cada campo borrado y
sustituido, en un artefacto resuelto y en uno `NO_EVALUABLE`—: quedaron 69
mutaciones indetectadas, todas ellas prosa libre, muestras de calibración
distintas de la mediana o carga ambiental. Están declaradas en la limitación
9 del paquete.

---

## 10. Limitaciones

Se mantienen las diez del paquete 07. Estas **se materializaron**:

1. **Once procesos siguen siendo pocos para una cola** (limitación 4). Se
   materializó de lleno: un solo proceso fijó `D` en el escalón de 200 ms.
   Con la salvedad de que el sesgo del rango va hacia bandas **más anchas**,
   es decir hacia el `NO_EVALUABLE`, no hacia una tolerancia falsamente
   permisiva.
2. **La corrida carga la máquina** (limitación 7). Se materializó: la carga
   subió de 0,51 a 1,01 y el coste unitario calibrado es un 32 % superior al
   del paquete 06.
3. **`n = 30` por encima de 1 ms** (limitación 5). En las nueve escalas caras
   el P99 coincide con el máximo observado. Cada entrada publica su
   `resolucion_percentil`.
4. **La coherencia con la fila TOL-107 no estaba garantizada** (limitación
   10). El método se congeló antes de medir y el resultado es el que es. No
   se ha ajustado ninguna fórmula, constante ni escalera tras observarlo.

---

## 11. Qué NO hace este informe

- **No aprueba `ADR002-TOL-209`**, que sigue **NO SATISFECHA**.
- **No propone ningún `U` ni ninguna `B(M)`**: no hay cruce, y no se inventa.
- **No revierte el acto de gobierno.** La banda dependiente de la magnitud
  sigue siendo la regla vigente de TOL-107 v0.5; lo que falta es la medición
  que la instancie con números.
- **No fija el límite duro** de TOL-107.
- **No sustituye ni retira** las evidencias v0.1 y v0.2.
- **No autoriza** avanzar a T0, implementar o ejecutar candidatos, ejecutar el
  *benchmark* ni fusionar el PR #117.
- **No decide** ninguna de las tres salidas del §6: son actos de gobierno.
