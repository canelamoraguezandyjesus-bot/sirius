# SIRIUS 0.2 — ADR-002 · Protocolo común de medición

**Versión:** 0.1
**Estado:** **PROPUESTO** · **no está aprobado** y no autoriza nada por sí mismo
**Fecha:** 26 de julio de 2026
**Paquete ejecutado:** `SIRIUS_0.2_ADR_002_PAQUETE_TRABAJO_02D_CORRECCION_AUDITORIA_v0.1.md` §5.4
**Exigido por:** `ADR002-TOL-209` del `SIRIUS_0.2_REGISTRO_TOLERANCIAS_v0.4_PROPUESTO.md`
**Origen del método:** §1.2 del `INFORME_MEDICION_TOLERANCIAS_v0.2_PROPUESTO.md`, generalizado a todos los candidatos
**No autoriza:** benchmark T1–T4, ejecución de T0, remedición de la línea base, implementación ni merge.

---

## 0. Por qué existe este artefacto

La línea base declaró su método con rigor: reloj monotónico, warm-up descartado, percentiles por rango más cercano nunca interpolados, fixtures fuera del cronómetro, cinco sesiones independientes, fórmula de variación explícita.

**Lo declaró para sí misma. Ningún texto lo imponía a T1–T4.**

Sin n mínimo, warm-up, método de percentil, número de sesiones y control del entorno comunes, las cifras de dos candidatos **no son comparables entre sí**, y `ADR002-TOL-107` —que mide variación entre ejecuciones equivalentes— no tiene sobre qué operar. Este documento cierra esa laguna. Es la generalización del método ya usado, no un método nuevo.

**Se congela antes del benchmark y rige por igual para la rederivación de T0 y para T1–T4.**

---

## 1. Alcance

**Cubre** toda medición de latencia, tiempo de ciclo, tamaño, estabilidad y variación que se use para comparar candidatos o para verificar una tolerancia con cifra.

**No cubre** las comprobaciones booleanas —restitución idéntica, `integrity-check`, desaparición completa, purga física, estabilidad de orden y conjunto, contaminación cero, fuga de ámbito cero, confusión de polaridad cero, conformidad de etapa—, que son propiedades de comportamiento y no dependen del protocolo de cronometraje. Sí les aplica, en cambio, la regla de repeticiones del §3.

**No modifica** el método con el que se midió la línea base ni ninguna cifra ya publicada. Las cifras existentes se conservan tal cual, con su alcance `LAB-LINUX`.

---

## 2. Instrumentación

| # | Regla | Fundamento |
|---|---|---|
| 2.1 | **Reloj monotónico.** `time.perf_counter_ns` o equivalente. Nunca reloj de pared ni tiempo de CPU | Método de la línea base |
| 2.2 | **Fixtures fuera del cronómetro.** Copia de la base, apertura de conexión, lectura de DDL, preparación del corpus y **todas** las verificaciones quedan fuera de la ventana medida | Método de la línea base |
| 2.3 | **Warm-up declarado y descartado.** Se declara su número y se descarta íntegro. Nunca se mezcla con las muestras | Método de la línea base |
| 2.4 | **Sin red, sin datos reales, sin modelos externos no declarados.** Cualquier coste externo se declara **aparte** y nunca se suma al local | TOL-202 |
| 2.5 | **DDL y esquema recuperados del propio motor**, nunca escritos a mano | Método de la remedición 02B |

---

## 3. Repeticiones y sesiones

| # | Regla |
|---|---|
| 3.1 | **Mínimo 30 repeticiones** por escenario y magnitud |
| 3.2 | **100 repeticiones cuando el coste sea bajo** — operaciones de sub-milisegundo o de coste despreciable frente a la preparación |
| 3.3 | **Al menos 5 sesiones independientes** para toda medida de estabilidad o variación. Cada sesión con fichero, motor, caché y warm-up propios |
| 3.4 | Las **tasas de éxito del 100 %** —restitución, integridad, borrado, purga— se calculan sobre **≥30 repeticiones**, cuando la operación sea ejecutable |
| 3.5 | **Cada repetición del ciclo del índice**, sobre una **copia limpia e independiente** preparada fuera del cronómetro |
| 3.6 | La **no ejecutabilidad** de una operación 30 veces se declara y justifica **en la ficha de candidato, antes de ejecutar**. Nunca después |

---

## 4. Percentiles y su lectura

| # | Regla |
|---|---|
| 4.1 | **Nearest-rank, nunca interpolado.** Método único para todas las cifras de todos los candidatos |
| 4.2 | Se publican siempre **P50, P95, P99, mínimo, máximo, media y n**. Publicar un percentil sin su n es inadmisible |
| 4.3 | **Con n=30, el P99 coincide con el máximo observado: acota la cola, no la caracteriza.** El P95 con n=30 es la segunda peor muestra |
| 4.4 | **Con n=100, el P99 es la peor muestra observada** |
| 4.5 | **Regla de trato uniforme.** Una cola de n=30 no puede invocarse en una fila y descartarse en otra según convenga. **O las colas de n=30 son evidencia utilizable para todas las filas que las publiquen, o para ninguna** |

La regla 4.5 no es teórica: su incumplimiento es lo que produjo el hallazgo B-02 de la auditoría, donde un límite duro se anclaba en un P99 de n=30 mientras el «peor P95 observado» excluía los P95 de n=30 de otro escenario.

---

## 5. Comparación entre candidatos

| # | Regla |
|---|---|
| 5.1 | **Misma máquina y mismo proceso** en toda comparación pareada. Comparar entre máquinas o procesos exige declararlo y degrada la conclusión |
| 5.2 | **Orden intercalado de candidatos** —A, B, A, B…— para anular la deriva del entorno. Nunca todos los bloques de A seguidos de todos los de B |
| 5.3 | **Semilla fija** en todo lo que dependa de aleatoriedad. Sin aleatoriedad no sembrada, sin dependencia de reloj |
| 5.4 | **Mismo corpus, misma versión, mismo commit** para todos los candidatos comparados (TOL-208) |
| 5.5 | **Mismo puerto de acceso** equivalente al `KnowledgeSearchRepository` actual, para que se mida la arquitectura y no la biblioteca (RF-31, puerta 6, Especificación §8) |
| 5.6 | **Registro de carga e incidencias** del entorno durante la ventana de medición: carga de la máquina, procesos concurrentes, throttling, cualquier anomalía observada |

---

## 6. Variación y validez de la comparación

| # | Regla |
|---|---|
| 6.1 | **Fórmula de variación:** `(máx − mín) / mín` sobre el **mismo percentil** en todas las sesiones. Es el peor par posible e independiente del orden |
| 6.2 | **Régimen relativo** por encima del umbral de conmutación congelado: se evalúa la variación relativa contra el objetivo de TOL-107 |
| 6.3 | **Régimen absoluto** por debajo del umbral: se evalúa **en valor absoluto** contra la banda absoluta congelada. **La variación relativa no se usa en este régimen** |
| 6.4 | **El umbral de conmutación y la banda absoluta se congelan con este protocolo y con el entorno, antes del benchmark**, y su fundamento debe ser el **suelo de medición medido del entorno**, no una preferencia. **Este documento no fija ese número: la evidencia disponible no basta y no se inventa** |
| 6.5 | Si la comparación resulta **inválida** por variación, **se repite una única vez** en condiciones controladas conforme a este protocolo |
| 6.6 | **Si vuelve a fallar, el candidato queda `NO EVALUABLE` en rendimiento** y así se registra. No se descarta por inestabilidad del entorno, pero **no se abre un bucle ilimitado de repeticiones**. Un candidato `NO EVALUABLE` en rendimiento no puede ser recomendado apoyándose en cifras de rendimiento |

La regla 6.4 existe porque el propio Registro constata que, con magnitudes de 0,14–1,0 ms, una variación del 36 % son 0,27 ms absolutos: **el suelo de medición, no inestabilidad del sistema**. Un objetivo relativo único penalizaría a los candidatos más rápidos por serlo.

---

## 7. Registro obligatorio de cada medición

Legible por máquina y auditable. Toda medición registra:

1. **Ficha de candidato**: ID, versión y huella (TOL-210).
2. **Corpus**: versión, volúmenes, longitud media, commit (TOL-208).
3. **Entorno**: máquina, SO, versiones de biblioteca, head de esquema, carga observada.
4. **Protocolo**: versión de este documento y **toda desviación**, declarada de antemano.
5. **Escenario y magnitud** medidos, con su n y su warm-up.
6. **Distribución completa**: P50, P95, P99, mínimo, máximo, media, n.
7. **Resolución del percentil**: qué muestra es cada percentil con ese n (§4.3, §4.4).
8. **Sesiones**: identificador de cada una y variación calculada con la fórmula 6.1.
9. **Régimen aplicado**: relativo o absoluto, y el umbral en vigor.
10. **Veredicto de validez** de la comparación, y si se ejercitó la repetición única de 6.5.
11. **Incidencias** del entorno durante la ventana.

---

## 8. Prohibiciones

1. **Prohibido cambiar el protocolo después de observar resultados.** Cualquier cambio obliga a nueva versión y a repetir las comparaciones ya ejecutadas bajo la anterior.
2. **Prohibido comparar cifras obtenidas bajo protocolos distintos.**
3. **Prohibido aplicar cifras `LAB-LINUX` a un corpus distinto** del que las produjo sin rederivarlas (TOL-208).
4. **Prohibido presentar cifras de Linux como aceptación del producto Windows** (TOL-205).
5. **Prohibido interpolar percentiles.**
6. **Prohibido publicar un percentil sin su n.**
7. **Prohibido sumar coste local y coste externo** en una sola cifra (TOL-202).
8. **Prohibido repetir una comparación inválida más de una vez** para «conseguir» un resultado válido (§6.6).

---

## 9. Lo que este protocolo no hace

- No ejecuta ninguna medición. **Este paquete no mide nada.**
- No modifica el método ni las cifras de la línea base ya publicadas.
- No fija el umbral de conmutación ni la banda absoluta de TOL-107: los congela el entorno, antes del benchmark.
- No fija el tamaño del corpus del benchmark: eso es TOL-208.
- No fija ningún umbral de rendimiento: eso es el Registro de Tolerancias.
- No modifica `src/`, `tests/`, `migrations/`, `experiments/`, `artifacts/` ni configuración productiva.

---

**Siguiente movimiento único:** que el usuario apruebe o corrija este protocolo junto al Registro v0.4. Hasta que esté congelado, ninguna cifra de candidato es comparable con ninguna otra, y el benchmark no puede arrancar (`ADR002-TOL-209`).
